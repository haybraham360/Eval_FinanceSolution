"""Independent blind implementation of t13, written from prompt.md alone without seeing the reference or grader. Kept as a regression test against false fails."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_EVEN, localcontext

RECV = "payrail:receivable"
FEE_ACC = "fee_expense"
FX_ACC = "fx_gain_loss"
WAT = timezone(timedelta(hours=1))
TERMINAL = ("PAID", "FAILED", "REJECTED")

SAMPLE_RESULT = {
    "balances": {"C1": {"available": -1000000, "held": 1000000},
                 "C2": {"available": 2291300, "held": 0}},
    "ledger_receivable": 2049974,
    "provider_net": 9354700,
    "fee_expense": 248500,
    "fx_gain_loss": -7174,
    "exceptions": [
        ["FX_SNAPSHOT_CONFLICT", "S-A"],
        ["NEGATIVE_BALANCE", "C1"],
        ["PAYIN_OUTCOME_UNKNOWN", "P4"],
        ["PAYOUT_OUTCOME_UNKNOWN", "O3"],
        ["REVERSAL_EXCEEDS_PAYIN", "X4"],
        ["UNMATCHED_SETTLEMENT_LINE", "P9"],
    ],
}


# ---------------------------------------------------------------- helpers
def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _lagos_date(s: str) -> str:
    return _ts(s).astimezone(WAT).date().isoformat()


def _to_ngn(state, snapshot_id, minor: int) -> int:
    with localcontext() as ctx:
        ctx.prec = 60
        v = Decimal(minor) * Decimal(state["snapshots"][snapshot_id])
        return int(v.quantize(Decimal(1), rounding=ROUND_HALF_EVEN))


def _init(state):
    if "seen" in state:
        return
    state.update({
        "seen": {}, "snapshots": {}, "fx_conflicts": {},
        "payins": {}, "api_timeouts": {}, "reversals": {},
        "payouts": {}, "payout_conflicts": {},
        "batches": {}, "closed_through": None,
        "journal": [], "sums": {}, "posted": {}, "recv_by_item": {},
        "next_line": 1,
    })


def _date_for(state, natural: str) -> str:
    ct = state["closed_through"]
    if ct is not None and natural[:7] <= ct:
        y, m = int(ct[:4]), int(ct[5:7])
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        return f"{y:04d}-{m:02d}-01"
    return natural


def _post(state, record_id, account, amount, natural, item_key=None):
    if amount == 0:
        return
    state["journal"].append({
        "line_id": f"J{state['next_line']:06d}", "record_id": record_id,
        "account": account, "amount_minor": amount,
        "accounting_date": _date_for(state, natural)})
    state["next_line"] += 1
    state["sums"][account] = state["sums"].get(account, 0) + amount
    if item_key is not None and account == RECV:
        state["recv_by_item"][item_key] = state["recv_by_item"].get(item_key, 0) + amount


def _ik(line_type, ref):
    return f"{line_type}|{ref}"


# ---------------------------------------------------------------- derived views
def _current_lines(state):
    """{(line_type|ref): {type, ref, currency, amount, settled, value_date}}"""
    out = {}
    for b in state["batches"].values():
        for ln in b["lines"]:
            k = _ik(ln["line_type"], ln["ref"])
            e = out.setdefault(k, {"type": ln["line_type"], "ref": ln["ref"],
                                   "currency": ln["currency"], "amount": 0,
                                   "settled": 0, "value_date": b["value_date"]})
            e["amount"] += ln["amount_minor"]
            e["settled"] += ln["settled_ngn_minor"]
    return out


def _signed(line):
    s = line["settled"]
    return s if line["type"] in ("PAYIN", "FEE_REFUND") else -s


def _reversal_calc(state):
    """reversal_id -> {payin_id, counted, C, P, ngn}; only for credited pay-ins."""
    by_payin = {}
    for rid, r in state["reversals"].items():
        by_payin.setdefault(r["payin_id"], []).append(rid)
    out = {}
    for pid, rids in by_payin.items():
        p = state["payins"].get(pid)
        if p is None:
            continue
        rids.sort(key=lambda x: (_ts(state["reversals"][x]["occurred_at"]), x))
        cum = 0
        for rid in rids:
            r = state["reversals"][rid]
            counted = max(0, min(r["amount_minor"], p["amount_minor"] - cum))
            before, cum = cum, cum + counted
            if p["currency"] == "USD":
                ngn = _to_ngn(state, p["snapshot"], cum) - _to_ngn(state, p["snapshot"], before)
            else:
                ngn = counted
            out[rid] = {"payin_id": pid, "counted": counted, "P": before, "C": cum, "ngn": ngn}
    return out


def _items(state, rc):
    """item key -> {currency, amount}"""
    items = {}
    for pid, p in state["payins"].items():
        items[_ik("PAYIN", pid)] = {"currency": p["currency"], "amount": p["amount_minor"]}
    for rid, c in rc.items():
        if c["counted"] > 0:
            cur = state["payins"][c["payin_id"]]["currency"]
            items[_ik("PAYIN_REVERSAL", rid)] = {"currency": cur, "amount": c["counted"]}
    for oid, o in state["payouts"].items():
        if o["status"] == "PAID":
            items[_ik("PAYOUT", oid)] = {"currency": "NGN", "amount": o["amount_minor"]}
    return items


# ---------------------------------------------------------------- recompute
def _recompute(state, record_id):
    rc = _reversal_calc(state)
    cur = _current_lines(state)
    items = _items(state, rc)
    desired = {}   # effect key -> (natural date, item_key, {account: amount})

    for pid, p in state["payins"].items():
        n = p["ngn"]
        desired["a_payin|" + pid] = (_lagos_date(p["occurred_at"]), _ik("PAYIN", pid),
                                     {RECV: n, f"customer:{p['customer_id']}:available": -n})
    for rid, c in rc.items():
        cust = state["payins"][c["payin_id"]]["customer_id"]
        n = c["ngn"]
        desired["b_rev|" + rid] = (_lagos_date(state["reversals"][rid]["occurred_at"]),
                                   _ik("PAYIN_REVERSAL", rid),
                                   {f"customer:{cust}:available": n, RECV: -n})
    for k, ln in cur.items():
        if ln["type"] == "FEE":
            desired["c_fee|" + k] = (ln["value_date"], None, {FEE_ACC: ln["settled"], RECV: -ln["settled"]})
        elif ln["type"] == "FEE_REFUND":
            desired["c_fee|" + k] = (ln["value_date"], None, {RECV: ln["settled"], FEE_ACC: -ln["settled"]})
        elif ln["type"] in ("PAYIN", "PAYIN_REVERSAL"):
            it = items.get(k)
            if it and it["currency"] == ln["currency"] and it["amount"] == ln["amount"] \
                    and ln["currency"] == "USD":
                if ln["type"] == "PAYIN":
                    ours = state["payins"][ln["ref"]]["ngn"]
                else:
                    ours = -rc[ln["ref"]]["ngn"]
                d = _signed(ln) - ours
                desired["d_fx|" + k] = (ln["value_date"], k, {RECV: d, FX_ACC: -d})

    posted = state["posted"]
    for ek in sorted(set(desired) | set(posted)):
        if ek in desired:
            natural, item_key, accs = desired[ek]
        else:
            natural, item_key, accs = posted[ek]["natural"], posted[ek]["item"], {}
        prev = posted.get(ek, {"natural": natural, "item": item_key, "accs": {}})
        for acc in sorted(set(accs) | set(prev["accs"])):
            delta = accs.get(acc, 0) - prev["accs"].get(acc, 0)
            _post(state, record_id, acc, delta, natural, item_key)
        posted[ek] = {"natural": natural, "item": item_key,
                      "accs": {a: v for a, v in accs.items() if v}}

    # sticky payout conflicts from current PAYOUT lines
    for k, ln in cur.items():
        if ln["type"] == "PAYOUT":
            o = state["payouts"].get(ln["ref"])
            if o and o["status"] in ("FAILED", "REJECTED"):
                state["payout_conflicts"][ln["ref"]] = True


# ---------------------------------------------------------------- payouts
def _payout_paid(state, rid, oid, natural):
    o = state["payouts"][oid]
    o["status"] = "PAID"
    c = o["customer_id"]
    _post(state, rid, f"customer:{c}:held", o["amount_minor"], natural, None)
    _post(state, rid, RECV, -o["amount_minor"], natural, _ik("PAYOUT", oid))


def _payout_failed(state, rid, oid, natural):
    o = state["payouts"][oid]
    o["status"] = "FAILED"
    c = o["customer_id"]
    _post(state, rid, f"customer:{c}:held", o["amount_minor"], natural)
    _post(state, rid, f"customer:{c}:available", -o["amount_minor"], natural)


def _payout_evidence(state, rid, oid, kind, natural):
    """kind: 'paid' or 'failed'."""
    o = state["payouts"][oid]
    st = o["status"]
    if st in TERMINAL:
        if (kind == "paid" and st in ("FAILED", "REJECTED")) or (kind == "failed" and st == "PAID"):
            state["payout_conflicts"][oid] = True
        return
    if kind == "paid":
        _payout_paid(state, rid, oid, natural)
    else:
        _payout_failed(state, rid, oid, natural)


def _cmd(kind, oid, o):
    return [{"command": kind, "payout_id": oid, "reference": o["reference"]}]


# ---------------------------------------------------------------- apply
def apply(state: dict, record: dict) -> list[dict]:
    _init(state)
    rid = record["record_id"]
    if rid in state["seen"]:
        return []
    state["seen"][rid] = True
    t = record["type"]
    cmds: list[dict] = []

    if t == "fx.snapshot":
        sid = record["snapshot_id"]
        if sid not in state["snapshots"]:
            state["snapshots"][sid] = record["rate"]
        elif Decimal(state["snapshots"][sid]) != Decimal(record["rate"]):
            state["fx_conflicts"][sid] = True
    elif t == "payin.api_result":
        state["api_timeouts"].setdefault(record["payin_id"], record["customer_id"])
    elif t == "payin.succeeded":
        pid = record["payin_id"]
        if pid not in state["payins"]:
            p = {k: record[k] for k in ("customer_id", "currency", "amount_minor", "occurred_at")}
            if p["currency"] == "USD":
                p["snapshot"] = record["fx_snapshot_id"]
                p["ngn"] = _to_ngn(state, p["snapshot"], p["amount_minor"])
            else:
                p["snapshot"] = None
                p["ngn"] = p["amount_minor"]
            state["payins"][pid] = p
    elif t == "payin.reversed":
        xid = record["reversal_id"]
        if xid not in state["reversals"]:
            state["reversals"][xid] = {k: record[k] for k in
                                       ("payin_id", "currency", "amount_minor", "occurred_at")}
    elif t == "payout.requested":
        oid = record["payout_id"]
        if oid not in state["payouts"]:
            c, amt = record["customer_id"], record["amount_minor"]
            o = {"customer_id": c, "amount_minor": amt, "occurred_at": record["occurred_at"],
                 "reference": f"ILU-PO-{oid}", "earliest_sent": None, "latest_sent": None,
                 "has_send_result": False}
            state["payouts"][oid] = o
            avail = -state["sums"].get(f"customer:{c}:available", 0)
            if avail >= amt:
                o["status"] = "SENDING"
                d = _lagos_date(record["occurred_at"])
                _post(state, rid, f"customer:{c}:available", amt, d)
                _post(state, rid, f"customer:{c}:held", -amt, d)
                cmds = _cmd("send", oid, o)
            else:
                o["status"] = "REJECTED"
    elif t == "payout.send_result":
        oid = record["payout_id"]
        o = state["payouts"].get(oid)
        if o is not None:
            sa = record["sent_at"]
            o["has_send_result"] = True
            if o["earliest_sent"] is None or _ts(sa) < _ts(o["earliest_sent"]):
                o["earliest_sent"] = sa
            if o["latest_sent"] is None or _ts(sa) > _ts(o["latest_sent"]):
                o["latest_sent"] = sa
            res = record["result"]
            if res == "accepted":
                _payout_evidence(state, rid, oid, "paid", _lagos_date(sa))
            elif res == "rejected":
                _payout_evidence(state, rid, oid, "failed", _lagos_date(sa))
            elif o["status"] == "SENDING":
                o["status"] = "UNKNOWN"
    elif t == "payout.retry_requested":
        oid = record["payout_id"]
        o = state["payouts"].get(oid)
        if o is not None and o["status"] == "UNKNOWN":
            end = _ts(o["earliest_sent"]) + timedelta(hours=24)
            cmds = _cmd("send" if _ts(record["at"]) < end else "lookup", oid, o)
    elif t == "payout.lookup_result":
        oid = record["payout_id"]
        o = state["payouts"].get(oid)
        if o is not None:
            at, res = record["at"], record["result"]
            if res == "accepted":
                _payout_evidence(state, rid, oid, "paid", _lagos_date(at))
            elif res == "rejected":
                _payout_evidence(state, rid, oid, "failed", _lagos_date(at))
            elif (o["status"] not in TERMINAL and o["has_send_result"]
                  and _ts(at) >= _ts(o["latest_sent"]) + timedelta(seconds=900)):
                _payout_failed(state, rid, oid, _lagos_date(at))
    elif t == "settlement.file":
        bid, seq = record["batch_id"], record["file_seq"]
        b = state["batches"].get(bid)
        if b is None or seq > b["seq"]:
            state["batches"][bid] = {"seq": seq, "value_date": record["value_date"],
                                     "lines": [dict(l) for l in record["lines"]]}
            for ref in sorted({l["ref"] for l in record["lines"] if l["line_type"] == "PAYOUT"}):
                if ref in state["payouts"]:
                    _payout_evidence(state, rid, ref, "paid", record["value_date"])
    elif t == "period.closed":
        p = record["period"]
        if state["closed_through"] is None or p > state["closed_through"]:
            state["closed_through"] = p

    _recompute(state, rid)
    return cmds


# ---------------------------------------------------------------- queries
def balances(state: dict) -> dict:
    _init(state)
    out = {}
    for acc, v in state["sums"].items():
        if acc.startswith("customer:"):
            c, kind = acc.split(":")[1], acc.split(":")[-1]
            out.setdefault(c, {"available": 0, "held": 0})[kind] = -v
    for line in state["journal"]:
        a = line["account"]
        if a.startswith("customer:"):
            out.setdefault(a.split(":")[1], {"available": 0, "held": 0})
    return out


def payin_status(state: dict, payin_id: str) -> str | None:
    _init(state)
    p = state["payins"].get(payin_id)
    if p is None:
        return "PENDING" if payin_id in state["api_timeouts"] else None
    rc = _reversal_calc(state)
    tot = sum(c["counted"] for c in rc.values() if c["payin_id"] == payin_id)
    if tot == 0:
        return "SUCCEEDED"
    return "REVERSED" if tot == p["amount_minor"] else "PARTIALLY_REVERSED"


def payout_status(state: dict, payout_id: str) -> str | None:
    _init(state)
    o = state["payouts"].get(payout_id)
    return None if o is None else o["status"]


def journal(state: dict) -> list[dict]:
    _init(state)
    return [dict(l) for l in state["journal"]]


def period_totals(state: dict, period: str) -> dict:
    _init(state)
    out = {}
    for l in state["journal"]:
        if l["accounting_date"][:7] == period:
            out[l["account"]] = out.get(l["account"], 0) + l["amount_minor"]
    return {k: v for k, v in out.items() if v != 0}


def reconciliation(state: dict) -> dict:
    _init(state)
    cur = _current_lines(state)
    rc = _reversal_calc(state)
    items = _items(state, rc)
    keys = set(items) | {k for k, l in cur.items() if l["type"] in ("PAYIN", "PAYIN_REVERSAL", "PAYOUT")}
    breaks = []
    for k in keys:
        lt, ref = k.split("|", 1)
        theirs = _signed(cur[k]) if k in cur else 0
        delta = theirs - state["recv_by_item"].get(k, 0)
        if delta:
            breaks.append({"line_type": lt, "ref": ref, "delta_minor": delta})
    breaks.sort(key=lambda b: (b["line_type"], b["ref"]))
    return {"ledger_receivable": state["sums"].get(RECV, 0),
            "provider_net": sum(_signed(l) for l in cur.values()),
            "breaks": breaks}


def exceptions(state: dict) -> list[dict]:
    _init(state)
    ex = set()
    for s in state["fx_conflicts"]:
        ex.add(("FX_SNAPSHOT_CONFLICT", s))
    for pid in state["api_timeouts"]:
        if pid not in state["payins"]:
            ex.add(("PAYIN_OUTCOME_UNKNOWN", pid))
    rc = _reversal_calc(state)
    for xid, r in state["reversals"].items():
        if r["payin_id"] not in state["payins"]:
            ex.add(("ORPHAN_REVERSAL", xid))
        elif rc[xid]["counted"] < r["amount_minor"]:
            ex.add(("REVERSAL_EXCEEDS_PAYIN", xid))
    for c, b in balances(state).items():
        if b["available"] < 0:
            ex.add(("NEGATIVE_BALANCE", c))
    for oid, o in state["payouts"].items():
        if o["status"] == "UNKNOWN":
            ex.add(("PAYOUT_OUTCOME_UNKNOWN", oid))
    for oid in state["payout_conflicts"]:
        ex.add(("PAYOUT_CONFLICT", oid))
    cur = _current_lines(state)
    items = _items(state, rc)
    for k, ln in cur.items():
        if ln["type"] in ("PAYIN", "PAYIN_REVERSAL", "PAYOUT"):
            it = items.get(k)
            if it is None:
                o = state["payouts"].get(ln["ref"]) if ln["type"] == "PAYOUT" else None
                if not (o and o["status"] in ("FAILED", "REJECTED")):
                    ex.add(("UNMATCHED_SETTLEMENT_LINE", ln["ref"]))
            elif it["currency"] != ln["currency"] or it["amount"] != ln["amount"]:
                ex.add(("SETTLEMENT_AMOUNT_MISMATCH", ln["ref"]))
        elif ln["type"] == "FEE_REFUND":
            xid = ln["ref"]
            contractual = 0
            c = rc.get(xid)
            if c is not None and c["counted"] > 0:
                p = state["payins"][c["payin_id"]]
                fl = cur.get(_ik("FEE", c["payin_id"]))
                F = fl["amount"] if fl else 0
                A = p["amount_minor"]
                contractual = F * c["C"] // A - F * c["P"] // A
            if ln["amount"] != contractual:
                ex.add(("FEE_REFUND_MISMATCH", xid))
    return [{"code": c, "ref": r} for c, r in sorted(ex)]
