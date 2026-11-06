# expect-fail: sample_result_stated_correctly
# States the sample position with a half-up FX credit.
"""Reference for t13. Facts are stored once per business key; the order-independent part of the ledger
(pay-ins, reversals, fees, FX) is derived from the fact set as target amounts per component, and only the
difference from what is already posted is appended. Payouts are a state machine and post as they move."""
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_EVEN, Decimal

WAT = timezone(timedelta(hours=1))
REC = "payrail:receivable"
SIGN = {"PAYIN": 1, "FEE_REFUND": 1, "PAYIN_REVERSAL": -1, "PAYOUT": -1, "FEE": -1}
ITEM_TYPES = ("PAYIN", "PAYIN_REVERSAL", "PAYOUT")
TERMINAL = ("PAID", "FAILED", "REJECTED")


def _init(state):
    if not state:
        state.update(seen={}, snapshots={}, fx_conflicts=[], timeouts={}, payins={}, reversals={}, payouts={},
                     payout_conflicts=[], files={}, closed=None, posted={}, journal=[], next_line=1)


def _instant(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _lagos(ts):
    return _instant(ts).astimezone(WAT).date().isoformat()


def _dated(state, natural):
    closed = state["closed"]
    if closed and natural[:7] <= closed:
        y, m = int(closed[:4]), int(closed[5:7])
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        return date(y, m, 1).isoformat()
    return natural


def _post(state, record_id, pairs, natural):
    when = _dated(state, natural)
    for account, amount in pairs:
        if amount:
            state["journal"].append({"line_id": f"J{state['next_line']}", "record_id": record_id, "account": account,
                                     "amount_minor": amount, "accounting_date": when})
            state["next_line"] += 1


def _ngn(state, payin, minor):
    if payin["currency"] == "NGN":
        return minor
    rate = Decimal(state["snapshots"][payin["snapshot"]])
    return int((Decimal(minor) * rate).quantize(Decimal(1), rounding=ROUND_HALF_EVEN))


def _counted(state):
    """reversal_id -> (counted, ngn, cum_before, cum_after) for reversals whose pay-in is credited."""
    out = {}
    by_payin = {}
    for rid, r in state["reversals"].items():
        if r["payin_id"] in state["payins"]:
            by_payin.setdefault(r["payin_id"], []).append(rid)
    for pid, rids in by_payin.items():
        p = state["payins"][pid]
        cum = 0
        for rid in sorted(rids, key=lambda x: (_instant(state["reversals"][x]["occurred_at"]), x)):
            amt = state["reversals"][rid]["amount"]
            counted = min(amt, p["amount"] - cum)
            out[rid] = (counted, _ngn(state, p, cum + counted) - _ngn(state, p, cum), cum, cum + counted)
            cum += counted
    return out


def _current_lines(state):
    """(line_type, ref) -> {"amount", "settled", "currency", "value_date"} summed over current files."""
    keys = {}
    for f in state["files"].values():
        for ln in f["lines"]:
            k = (ln["line_type"], ln["ref"])
            agg = keys.setdefault(k, {"amount": 0, "settled": 0, "currencies": set(), "value_date": f["value_date"]})
            agg["amount"] += ln["amount_minor"]
            agg["settled"] += ln["settled_ngn_minor"]
            agg["currencies"].add(ln["currency"])
    return keys


def _items(state, counted):
    """(line_type, ref) -> (currency, amount in that currency, signed NGN effect before FX)."""
    items = {}
    for pid, p in state["payins"].items():
        items[("PAYIN", pid)] = (p["currency"], p["amount"], _ngn(state, p, p["amount"]))
    for rid, (c, ngn, _, _) in counted.items():
        if c > 0:
            items[("PAYIN_REVERSAL", rid)] = (state["payins"][state["reversals"][rid]["payin_id"]]["currency"], c, -ngn)
    for oid, o in state["payouts"].items():
        if o["status"] == "PAID":
            items[("PAYOUT", oid)] = ("NGN", o["amount"], -o["amount"])
    return items


def _agrees(item, line):
    return line["currencies"] == {item[0]} and line["amount"] == item[1]


def _targets(state):
    """component key -> (debit account, credit account, natural date, amount)."""
    counted = _counted(state)
    lines = _current_lines(state)
    items = _items(state, counted)
    t = {}
    for pid, p in state["payins"].items():
        t[f"payin|{pid}"] = (REC, f"customer:{p['customer']}:available", _lagos(p["occurred_at"]), _ngn(state, p, p["amount"]))
    for rid, (c, ngn, _, _) in counted.items():
        r = state["reversals"][rid]
        cust = state["payins"][r["payin_id"]]["customer"]
        t[f"rev|{rid}"] = (f"customer:{cust}:available", REC, _lagos(r["occurred_at"]), ngn)
    for (lt, ref), ln in lines.items():
        if lt == "FEE":
            t[f"fee|{ref}"] = ("fee_expense", REC, ln["value_date"], ln["settled"])
        elif lt == "FEE_REFUND":
            t[f"feeref|{ref}"] = (REC, "fee_expense", ln["value_date"], ln["settled"])
        elif (lt, ref) in items and items[(lt, ref)][0] == "USD" and _agrees(items[(lt, ref)], ln):
            t[f"fx|{lt}|{ref}"] = (REC, "fx_gain_loss", ln["value_date"], SIGN[lt] * ln["settled"] - items[(lt, ref)][2])
    return t


def _settle_derived(state, record_id):
    """Append the difference between each derived component's target and what is already posted.
    A component that no longer exists (e.g. a corrected file dropped a fee line) has target 0."""
    targets = _targets(state)
    for key in sorted(set(targets) | set(state["posted"])):
        if key in targets:
            debit, credit, natural, amount = targets[key]
        else:
            debit, credit, natural, amount = state["posted"][key]["debit"], state["posted"][key]["credit"], state["posted"][key]["natural"], 0
        delta = amount - state["posted"].get(key, {"amount": 0})["amount"]
        if delta:
            _post(state, record_id, [(debit, delta), (credit, -delta)], natural)
        state["posted"][key] = {"amount": amount, "debit": debit, "credit": credit, "natural": natural}


def _available(state, cust):
    return -sum(l["amount_minor"] for l in state["journal"] if l["account"] == f"customer:{cust}:available")


def _conflict(state, oid):
    if oid not in state["payout_conflicts"]:
        state["payout_conflicts"].append(oid)


def _resolve(state, record_id, oid, outcome, when):
    o = state["payouts"][oid]
    if o["status"] in TERMINAL:
        if (outcome == "PAID" and o["status"] in ("FAILED", "REJECTED")) or (outcome == "FAILED" and o["status"] == "PAID"):
            _conflict(state, oid)
        return
    held, avail = f"customer:{o['customer']}:held", f"customer:{o['customer']}:available"
    if outcome == "PAID":
        _post(state, record_id, [(held, o["amount"]), (REC, -o["amount"])], when)
    else:
        _post(state, record_id, [(held, o["amount"]), (avail, -o["amount"])], when)
    o["status"] = outcome


def apply(state, record):
    _init(state)
    rid = record["record_id"]
    if rid in state["seen"]:
        return []
    state["seen"][rid] = 1
    t = record["type"]
    commands = []
    if t == "fx.snapshot":
        sid = record["snapshot_id"]
        if sid not in state["snapshots"]:
            state["snapshots"][sid] = record["rate"]
        elif Decimal(state["snapshots"][sid]) != Decimal(record["rate"]) and sid not in state["fx_conflicts"]:
            state["fx_conflicts"].append(sid)
    elif t == "payin.api_result":
        state["timeouts"].setdefault(record["payin_id"], record["customer_id"])
    elif t == "payin.succeeded":
        pid = record["payin_id"]
        if pid not in state["payins"]:
            state["payins"][pid] = {"customer": record["customer_id"], "currency": record["currency"], "amount": record["amount_minor"],
                                    "occurred_at": record["occurred_at"], "snapshot": record.get("fx_snapshot_id")}
    elif t == "payin.reversed":
        state["reversals"].setdefault(record["reversal_id"], {"payin_id": record["payin_id"], "amount": record["amount_minor"],
                                                              "occurred_at": record["occurred_at"]})
    elif t == "payout.requested":
        oid = record["payout_id"]
        if oid not in state["payouts"]:
            cust, amt = record["customer_id"], record["amount_minor"]
            o = {"customer": cust, "amount": amt, "status": "REJECTED", "ref": f"ilu-{oid}", "first_sent": None, "last_sent": None}
            state["payouts"][oid] = o
            if _available(state, cust) >= amt:
                o["status"] = "SENDING"
                _post(state, rid, [(f"customer:{cust}:available", amt), (f"customer:{cust}:held", -amt)], _lagos(record["occurred_at"]))
                commands.append({"command": "send", "payout_id": oid, "reference": o["ref"]})
    elif t == "payout.send_result":
        o = state["payouts"].get(record["payout_id"])
        if o and o["status"] != "REJECTED":
            ts = record["sent_at"]
            if o["first_sent"] is None or _instant(ts) < _instant(o["first_sent"]):
                o["first_sent"] = ts
            if o["last_sent"] is None or _instant(ts) > _instant(o["last_sent"]):
                o["last_sent"] = ts
            res = record["result"]
            if res == "accepted":
                _resolve(state, rid, record["payout_id"], "PAID", _lagos(ts))
            elif res == "rejected":
                _resolve(state, rid, record["payout_id"], "FAILED", _lagos(ts))
            elif o["status"] in ("SENDING", "UNKNOWN"):
                o["status"] = "UNKNOWN"
        elif o and record["result"] == "accepted":
            _conflict(state, record["payout_id"])
    elif t == "payout.lookup_result":
        oid = record["payout_id"]
        o = state["payouts"].get(oid)
        if o:
            res, at = record["result"], record["at"]
            if res == "accepted":
                _resolve(state, rid, oid, "PAID", _lagos(at))
            elif res == "rejected":
                _resolve(state, rid, oid, "FAILED", _lagos(at))
            elif (o["status"] in ("SENDING", "UNKNOWN") and o["last_sent"]
                  and (_instant(at) - _instant(o["last_sent"])).total_seconds() >= 900):
                _resolve(state, rid, oid, "FAILED", _lagos(at))
    elif t == "payout.retry_requested":
        o = state["payouts"].get(record["payout_id"])
        if o and o["status"] == "UNKNOWN":
            expiry = _instant(o["first_sent"]) + timedelta(hours=24)
            kind = "send" if _instant(record["at"]) < expiry else "lookup"
            commands.append({"command": kind, "payout_id": record["payout_id"], "reference": o["ref"]})
    elif t == "settlement.file":
        b = record["batch_id"]
        cur = state["files"].get(b)
        if cur is None or record["file_seq"] > cur["seq"]:
            state["files"][b] = {"seq": record["file_seq"], "value_date": record["value_date"],
                                 "lines": [dict(x) for x in record["lines"]]}
    elif t == "period.closed":
        if state["closed"] is None or record["period"] > state["closed"]:
            state["closed"] = record["period"]

    for (lt, ref), ln in sorted(_current_lines(state).items()):
        if lt == "PAYOUT" and ref in state["payouts"]:
            o = state["payouts"][ref]
            if o["status"] in ("SENDING", "UNKNOWN"):
                _resolve(state, rid, ref, "PAID", ln["value_date"])
            elif o["status"] in ("FAILED", "REJECTED"):
                _conflict(state, ref)
    _settle_derived(state, rid)
    return commands


def balances(state):
    _init(state)
    out = {}
    for l in state["journal"]:
        parts = l["account"].split(":")
        if parts[0] == "customer":
            out.setdefault(parts[1], {"available": 0, "held": 0})[parts[2]] -= l["amount_minor"]
    return out


def payin_status(state, payin_id):
    _init(state)
    if payin_id in state["payins"]:
        p = state["payins"][payin_id]
        rev = sum(c for rid, (c, _, _, _) in _counted(state).items() if state["reversals"][rid]["payin_id"] == payin_id)
        return "SUCCEEDED" if rev == 0 else "REVERSED" if rev == p["amount"] else "PARTIALLY_REVERSED"
    return "PENDING" if payin_id in state["timeouts"] else None


def payout_status(state, payout_id):
    _init(state)
    o = state["payouts"].get(payout_id)
    return o["status"] if o else None


def journal(state):
    _init(state)
    return [dict(l) for l in state["journal"]]


def period_totals(state, period):
    _init(state)
    out = {}
    for l in state["journal"]:
        if l["accounting_date"][:7] == period:
            out[l["account"]] = out.get(l["account"], 0) + l["amount_minor"]
    return {k: v for k, v in out.items() if v}


def reconciliation(state):
    _init(state)
    counted = _counted(state)
    lines = _current_lines(state)
    items = _items(state, counted)
    targets = _targets(state)
    provider_net = sum(SIGN[lt] * ln["settled"] for (lt, _), ln in lines.items())
    ledger = sum(l["amount_minor"] for l in state["journal"] if l["account"] == REC)
    breaks = []
    for key in sorted(set(items) | {k for k in lines if k[0] in ITEM_TYPES}):
        lt, ref = key
        provider = SIGN[lt] * lines[key]["settled"] if key in lines else 0
        ours = items[key][2] + targets.get(f"fx|{lt}|{ref}", (0, 0, 0, 0))[3] if key in items else 0
        if provider != ours:
            breaks.append({"line_type": lt, "ref": ref, "delta_minor": provider - ours})
    return {"ledger_receivable": ledger, "provider_net": provider_net, "breaks": breaks}


def exceptions(state):
    _init(state)
    counted = _counted(state)
    lines = _current_lines(state)
    items = _items(state, counted)
    out = set()
    out |= {("FX_SNAPSHOT_CONFLICT", s) for s in state["fx_conflicts"]}
    out |= {("PAYIN_OUTCOME_UNKNOWN", p) for p in state["timeouts"] if p not in state["payins"]}
    for rid, r in state["reversals"].items():
        if r["payin_id"] not in state["payins"]:
            out.add(("ORPHAN_REVERSAL", rid))
        elif counted[rid][0] < r["amount"]:
            out.add(("REVERSAL_EXCEEDS_PAYIN", rid))
    out |= {("NEGATIVE_BALANCE", c) for c, b in balances(state).items() if b["available"] < 0}
    out |= {("PAYOUT_OUTCOME_UNKNOWN", o) for o, v in state["payouts"].items() if v["status"] == "UNKNOWN"}
    out |= {("PAYOUT_CONFLICT", o) for o in state["payout_conflicts"]}
    for (lt, ref), ln in lines.items():
        if lt in ITEM_TYPES:
            if (lt, ref) not in items:
                if not (lt == "PAYOUT" and ref in state["payouts"] and state["payouts"][ref]["status"] in ("FAILED", "REJECTED")):
                    out.add(("UNMATCHED_SETTLEMENT_LINE", ref))
            elif not _agrees(items[(lt, ref)], ln):
                out.add(("SETTLEMENT_AMOUNT_MISMATCH", ref))
        elif lt == "FEE_REFUND":
            if ln["settled"] != _contract_refund(state, counted, lines, ref):
                out.add(("FEE_REFUND_MISMATCH", ref))
    return [{"code": c, "ref": r} for c, r in sorted(out)]


def _contract_refund(state, counted, lines, rid):
    if rid not in counted or counted[rid][0] == 0:
        return 0
    pid = state["reversals"][rid]["payin_id"]
    a = state["payins"][pid]["amount"]
    fee = lines.get(("FEE", pid), {"settled": 0})["settled"]
    _, _, before, after = counted[rid]
    return fee * after // a - fee * before // a


SAMPLE_RESULT = {
    "balances": {"C1": {"available": -1000000, "held": 1000000}, "C2": {"available": 2291301, "held": 0}},
    "ledger_receivable": 2049974,
    "provider_net": 9354700,
    "fee_expense": 248500,
    "fx_gain_loss": -7174,
    "exceptions": [["FX_SNAPSHOT_CONFLICT", "S-A"], ["NEGATIVE_BALANCE", "C1"], ["PAYIN_OUTCOME_UNKNOWN", "P4"],
                   ["PAYOUT_OUTCOME_UNKNOWN", "O3"], ["REVERSAL_EXCEEDS_PAYIN", "X4"], ["UNMATCHED_SETTLEMENT_LINE", "P9"]],
}
