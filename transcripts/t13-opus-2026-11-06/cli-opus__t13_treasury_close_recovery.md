# cli-opus / t13_treasury_close_recovery / trial 1

- Requested: `opus`, resolved: `claude-haiku-5-5,claude-opus-5-5`, provider: claude-cli
- Run at 2026-11-06T19:15:11+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t13_treasury_close_recovery/prompt.md`.

## Model output

**How the final position follows from the log**

*Pay-ins and reversals*
- **P1** (r02) credits C1 with 10,000,000. The repeat delivery of r02 and the re-issue in r07 change nothing.
- **P3** is `PENDING` after r09. **X1** (r12) is an orphan until r13 credits P3 with 4,000,000. X1 then counts its full 1,000,000.
- **P2** (r18) is USD 2503 at S-A = 1525.50. That is 3,818,326.5, which rounds half-to-even to **3,818,326** for C2.
- **r14** tries to re-rate S-A. The rate stays 1525.50 and `FX_SNAPSHOT_CONFLICT S-A` is raised.
- **P4** (r15) stays `PENDING`, so `PAYIN_OUTCOME_UNKNOWN P4` is open.

*Payouts*
- **O1**: r03 holds 8,000,000 and sends. r04 times out, so the window runs from 10-30 12:00:05Z to 10-31 12:00:05Z.
  - r05 is inside the window, so it sends again. r06 times out.
  - r10 is past the window, so it returns a lookup. r11 `accepted` makes O1 `PAID`.
  - The later O1 `PAYOUT` lines and r31 are ignored.
- **O3** (r16/r17) holds 1,000,000 and times out. r32 at 11-01 11:00Z is still inside the window, so it returns a re-send. The status stays `UNKNOWN`, so `PAYOUT_OUTCOME_UNKNOWN O3` is open.
- **O2** (r19/r20) holds 2,000,000. r21 is before sent_at + 900 s, so nothing changes. r22 is after it, so O2 becomes `FAILED` and the hold is released.

*Settlement batch B-1031*
- **seq 1**: fees post, and the P2 FX difference posts as 3,826,000 − 3,818,326 = +7,674. P9 has no item, so it is unmatched.
- **seq 2**: fees are posted as differences.
  - FEE P1 drops by 5,000.
  - The P2 FX difference becomes 7,174, a change of −500.
  - FEE_REFUND X1 becomes 16,000. The contract refund is ⌊60,000×1M/4M⌋ = 15,000, so `FEE_REFUND_MISMATCH X1` opens.
- **r25** (seq 1 again) is void because seq 2 is current.

*After the October close (r26)* — every late line for October is dated 2026-11-01.
- **X3**: 2,000,000 counted against P1.
- **X2**: USD 1001 at P2's own snapshot S-A, not S-B. 1,527,025.5 rounds half-to-even to 1,527,026.
- **seq 3**: FEE P3 rises by 2,000 and FEE_REFUND X1 falls by 500. The contract refund is now ⌊62,000/4⌋ = 15,500, so the mismatch clears.
- **X4** (r30) is capped at the 3,000,000 left of P3, so `REVERSAL_EXCEEDS_PAYIN X4` opens. C1 goes to −1,000,000, so `NEGATIVE_BALANCE C1` opens.

*Totals*
- **C1 available**: 10M − 8M + 4M − 1M − 1M − 2M − 3M = −1,000,000. **C1 held**: O3's 1,000,000.
- **C2 available**: 3,818,326 − 2M + 2M − 1,527,026 = 2,291,300. **C2 held**: 0.
- **ledger_receivable** = 2,049,974. **provider_net** (seq 3) = 9,354,700.
- **Breaks**: P9 +777,700, X2 +1,527,026, X3 +2,000,000, X4 +3,000,000. They sum to 7,304,726, which equals provider_net − ledger_receivable.
- **fee_expense** = 145,000 + 57,000 + 62,000 − 15,500 = 248,500. **fx_gain_loss** = −7,174.
- **Open exceptions**: `ORPHAN_REVERSAL X1` and `FEE_REFUND_MISMATCH X1` have cleared. Six remain open: `FX_SNAPSHOT_CONFLICT S-A`, `NEGATIVE_BALANCE C1`, `PAYIN_OUTCOME_UNKNOWN P4`, `PAYOUT_OUTCOME_UNKNOWN O3`, `REVERSAL_EXCEEDS_PAYIN X4` and `UNMATCHED_SETTLEMENT_LINE P9`.

*Design*
- Each effect's target postings are recomputed from facts, per natural accounting date.
- Only the difference against what was already posted is appended. This keeps the journal append-only, balanced per `apply`, and independent of arrival order.

```python
"""Event-sourced PayRail treasury ledger for Ilu Wallet (October 2026 close).

Python 3.10+, standard library only.

Design
------
* ``state`` holds only JSON types (str / int / bool / None / list / dict with str keys),
  so it round-trips exactly through json.dumps / json.loads after every apply().
* Facts (pay-ins, reversals, payouts, current settlement lines) are stored as received.
* Every ledger *effect* (pay-in credit, reversal, payout hold / paid / failed, fee,
  fee refund, FX difference) has a target posting set, keyed by natural accounting
  date. After each record, the target postings of the affected effects are recomputed
  from the facts and compared with what was already posted for that effect. Only the
  difference is appended to the journal. The journal is therefore append-only, every
  apply() is balanced, and before any period close the final journal depends only on
  the set of facts, not on their arrival order.
* Money is integer minor units. USD->NGN uses decimal.Decimal and ROUND_HALF_EVEN.
* Malformed records raise ValueError before any mutation of state.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation, localcontext

# --------------------------------------------------------------------------- constants

RECEIVABLE = "payrail:receivable"
FEE_EXPENSE = "fee_expense"
FX_GAIN_LOSS = "fx_gain_loss"

SENDING, UNKNOWN, PAID, FAILED, REJECTED = "SENDING", "UNKNOWN", "PAID", "FAILED", "REJECTED"
_OPEN_PAYOUT = (SENDING, UNKNOWN)

_IDEMPOTENCY_US = 24 * 3600 * 1_000_000
_VISIBILITY_US = 900 * 1_000_000
_LAGOS_OFFSET = timedelta(hours=1)  # WAT, fixed UTC+01:00
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)

_LINE_TYPES = ("PAYIN", "PAYIN_REVERSAL", "PAYOUT", "FEE", "FEE_REFUND")
_LINE_SIGN = {"PAYIN": 1, "FEE_REFUND": 1, "PAYIN_REVERSAL": -1, "PAYOUT": -1, "FEE": -1}
_ITEM_LINE_TYPES = ("PAYIN", "PAYIN_REVERSAL", "PAYOUT")
_CURRENCIES = ("NGN", "USD")

_TS_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,9}))?(Z|[+-]\d{2}:\d{2})$"
)
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

# Final position expected after the whole October close sample log.
SAMPLE_RESULT = {
    "balances": {
        "C1": {"available": -1000000, "held": 1000000},
        "C2": {"available": 2291300, "held": 0},
    },
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

# --------------------------------------------------------------------------- validation


def _req_str(rec: dict, key: str) -> str:
    v = rec.get(key)
    if not isinstance(v, str) or v == "":
        raise ValueError(f"field {key!r} must be a non-empty string")
    return v


def _req_int(rec: dict, key: str) -> int:
    v = rec.get(key)
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise ValueError(f"field {key!r} must be a non-negative integer")
    return v


def _req_choice(rec: dict, key: str, choices) -> str:
    v = rec.get(key)
    if v not in choices:
        raise ValueError(f"field {key!r} must be one of {choices}")
    return v


def _req_rate(rec: dict, key: str) -> str:
    v = rec.get(key)
    if not isinstance(v, str):
        raise ValueError(f"field {key!r} must be a decimal string")
    try:
        d = Decimal(v)
    except InvalidOperation as exc:
        raise ValueError(f"field {key!r} is not a decimal") from exc
    if not d.is_finite() or d <= 0:
        raise ValueError(f"field {key!r} must be a positive finite decimal")
    return v


def _parse_ts(value, key: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"field {key!r} must be an ISO-8601 string")
    m = _TS_RE.match(value)
    if not m:
        raise ValueError(f"field {key!r} is not an ISO-8601 UTC timestamp: {value!r}")
    y, mo, d, h, mi, s = (int(m.group(i)) for i in range(1, 7))
    us = int(((m.group(7) or "") + "000000")[:6])
    try:
        dt = datetime(y, mo, d, h, mi, s, us, tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError(f"field {key!r} is not a valid timestamp") from exc
    tz = m.group(8)
    if tz != "Z":
        sign = 1 if tz[0] == "+" else -1
        dt -= sign * timedelta(hours=int(tz[1:3]), minutes=int(tz[4:6]))
    return dt


def _req_ts(rec: dict, key: str) -> datetime:
    return _parse_ts(rec.get(key), key)


def _req_date(rec: dict, key: str) -> str:
    v = rec.get(key)
    if not isinstance(v, str) or not _DATE_RE.match(v):
        raise ValueError(f"field {key!r} must be YYYY-MM-DD")
    try:
        date.fromisoformat(v)
    except ValueError as exc:
        raise ValueError(f"field {key!r} is not a valid date") from exc
    return v


def _us(dt: datetime) -> int:
    return (dt - _EPOCH) // timedelta(microseconds=1)


def _lagos_date(dt: datetime) -> str:
    return (dt + _LAGOS_OFFSET).date().isoformat()


# --------------------------------------------------------------------------- helpers


def _avail(customer_id: str) -> str:
    return f"customer:{customer_id}:available"


def _held(customer_id: str) -> str:
    return f"customer:{customer_id}:held"


def _reference(payout_id: str) -> str:
    # Injective in payout_id: unique per payout, identical for every command of a payout.
    return f"ILW-PO-{payout_id}"


def _to_ngn(minor: int, currency: str, rate: str | None) -> int:
    if currency == "NGN":
        return minor
    if rate is None:
        raise ValueError("USD amount without an FX rate")
    with localcontext() as ctx:
        ctx.prec = 100
        value = (Decimal(minor) * Decimal(rate)).quantize(Decimal(1), rounding=ROUND_HALF_EVEN)
    return int(value)


def _init(state: dict) -> None:
    state.setdefault("version", 1)
    state.setdefault("seen", {})
    state.setdefault("fx", {})
    state.setdefault("fx_conflicts", {})
    state.setdefault("payins", {})
    state.setdefault("reversals", {})
    state.setdefault("payin_revs", {})
    state.setdefault("payouts", {})
    state.setdefault("payout_conflicts", {})
    state.setdefault("batches", {})
    state.setdefault("lines", {})
    state.setdefault("posted", {})
    state.setdefault("journal", [])
    state.setdefault("acct", {})
    state.setdefault("ptotals", {})
    state.setdefault("closed", None)
    state.setdefault("seq", 0)


def _cur_line(state: dict, line_type: str, ref: str) -> dict | None:
    return state["lines"].get(line_type, {}).get(ref)


def _agrees(line: dict, currency: str, amount: int) -> bool:
    return line["currency"] == currency and line["amount"] == amount


def _post_date(state: dict, natural: str) -> str:
    closed = state["closed"]
    if closed is not None and natural[:7] <= closed:
        y, m = int(closed[:4]), int(closed[5:7]) + 1
        if m == 13:
            y, m = y + 1, 1
        return f"{y:04d}-{m:02d}-01"
    return natural


def _dirty(ctx: dict, key: tuple) -> None:
    if key not in ctx["dirty_set"]:
        ctx["dirty_set"].add(key)
        ctx["dirty"].append(key)


def _payout_conflict(state: dict, payout_id: str) -> None:
    state["payout_conflicts"][payout_id] = True


def _resolve_payout(state: dict, po: dict, payout_id: str, status: str, natural_date: str) -> None:
    po["status"] = status
    po["resolved_date"] = natural_date
    if status == FAILED and _cur_line(state, "PAYOUT", payout_id) is not None:
        # A current PAYOUT line is evidence that money left.
        _payout_conflict(state, payout_id)


# --------------------------------------------------------------------------- derived pay-in maths


def _payin_calc(state: dict, payin_id: str) -> dict:
    pi = state["payins"].get(payin_id)
    revs = state["reversals"]
    ids = sorted(state["payin_revs"].get(payin_id, []), key=lambda x: (revs[x]["at_us"], x))
    credited = bool(pi and pi.get("credited"))
    rows = []
    ngn_amount = 0
    if credited:
        amount, cur, rate = pi["amount"], pi["currency"], pi.get("rate")
        ngn_amount = _to_ngn(amount, cur, rate)
        remaining, cum, prev_ngn = amount, 0, 0
        for x in ids:
            counted = min(revs[x]["amount"], remaining)
            remaining -= counted
            before = cum
            cum += counted
            ngn_cum = _to_ngn(cum, cur, rate)
            rows.append({"id": x, "counted": counted, "ngn": ngn_cum - prev_ngn,
                         "before": before, "after": cum})
            prev_ngn = ngn_cum
    else:
        rows = [{"id": x, "counted": 0, "ngn": 0, "before": 0, "after": 0} for x in ids]
    return {"credited": credited, "pi": pi, "ngn_amount": ngn_amount, "rows": rows}


def _all_reversal_rows(state: dict) -> dict:
    out = {}
    for pid in state["payin_revs"]:
        calc = _payin_calc(state, pid)
        for row in calc["rows"]:
            out[row["id"]] = (pid, calc["credited"], row)
    return out


# --------------------------------------------------------------------------- target effects


def _effects_payin(state: dict, payin_id: str) -> list:
    calc = _payin_calc(state, payin_id)
    pi = calc["pi"]
    out = []
    credit, fx_credit = [], []
    if calc["credited"]:
        cust, d, ngn = pi["customer_id"], pi["date"], calc["ngn_amount"]
        credit = [(RECEIVABLE, d, ngn), (_avail(cust), d, -ngn)]
        line = _cur_line(state, "PAYIN", payin_id)
        if line is not None and pi["currency"] == "USD" and _agrees(line, "USD", pi["amount"]):
            diff, vd = line["settled"] - ngn, line["value_date"]
            fx_credit = [(RECEIVABLE, vd, diff), (FX_GAIN_LOSS, vd, -diff)]
    out.append(("CREDIT", payin_id, credit))
    out.append(("FXPAYIN", payin_id, fx_credit))
    for row in calc["rows"]:
        x = row["id"]
        rev, fx_rev = [], []
        if calc["credited"] and row["counted"] > 0:
            cust, d, ngn = pi["customer_id"], state["reversals"][x]["date"], row["ngn"]
            rev = [(_avail(cust), d, ngn), (RECEIVABLE, d, -ngn)]
            line = _cur_line(state, "PAYIN_REVERSAL", x)
            if line is not None and pi["currency"] == "USD" and _agrees(line, "USD", row["counted"]):
                # PayRail signed (-settled) minus ours (-ngn).
                diff, vd = ngn - line["settled"], line["value_date"]
                fx_rev = [(RECEIVABLE, vd, diff), (FX_GAIN_LOSS, vd, -diff)]
        out.append(("REV", x, rev))
        out.append(("FXREV", x, fx_rev))
    return out


def _effects_payout(state: dict, payout_id: str) -> list:
    po = state["payouts"].get(payout_id)
    hold, paid, failed = [], [], []
    if po is not None and po["status"] != REJECTED:
        c, a, d = po["customer_id"], po["amount"], po["hold_date"]
        hold = [(_avail(c), d, a), (_held(c), d, -a)]
        if po["status"] == PAID:
            rd = po["resolved_date"]
            paid = [(_held(c), rd, a), (RECEIVABLE, rd, -a)]
        elif po["status"] == FAILED:
            rd = po["resolved_date"]
            failed = [(_held(c), rd, a), (_avail(c), rd, -a)]
    return [("HOLD", payout_id, hold), ("PAID", payout_id, paid), ("FAILED", payout_id, failed)]


def _effects_fee(state: dict, line_type: str, ref: str) -> list:
    line = _cur_line(state, line_type, ref)
    entries = []
    if line is not None:
        s, vd = line["settled"], line["value_date"]
        if line_type == "FEE":
            entries = [(FEE_EXPENSE, vd, s), (RECEIVABLE, vd, -s)]
        else:
            entries = [(RECEIVABLE, vd, s), (FEE_EXPENSE, vd, -s)]
    return [(line_type, ref, entries)]


# --------------------------------------------------------------------------- posting


def _post_line(state: dict, record_id: str, account: str, amount: int, posting_date: str) -> None:
    state["seq"] += 1
    state["journal"].append({
        "line_id": f"JL-{state['seq']:08d}",
        "record_id": record_id,
        "account": account,
        "amount_minor": amount,
        "accounting_date": posting_date,
    })
    acct = state["acct"]
    acct[account] = acct.get(account, 0) + amount
    period = state["ptotals"].setdefault(posting_date[:7], {})
    period[account] = period.get(account, 0) + amount


def _sync(state: dict, record_id: str, kind: str, ref: str, entries: list) -> None:
    desired: dict = {}
    for account, natural, amount in entries:
        if amount:
            per = desired.setdefault(account, {})
            per[natural] = per.get(natural, 0) + amount
    by_kind = state["posted"].setdefault(kind, {})
    posted = by_kind.get(ref, {})
    accounts = list(desired) + sorted(a for a in posted if a not in desired)
    emit: dict = {}
    for account in accounts:
        want = desired.get(account, {})
        have = dict(posted.get(account, {}))
        dates = list(want) + sorted(d for d in have if d not in want)
        for natural in dates:
            diff = want.get(natural, 0) - have.get(natural, 0)
            if diff == 0:
                continue
            new_total = have.get(natural, 0) + diff
            slot = posted.setdefault(account, {})
            if new_total:
                slot[natural] = new_total
            else:
                slot.pop(natural, None)
            if not slot:
                posted.pop(account, None)
            key = (account, _post_date(state, natural))
            emit[key] = emit.get(key, 0) + diff
    if posted:
        by_kind[ref] = posted
    else:
        by_kind.pop(ref, None)
    if not by_kind:
        state["posted"].pop(kind, None)
    for (account, posting_date), amount in emit.items():
        if amount:
            _post_line(state, record_id, account, amount, posting_date)


def _flush(state: dict, record_id: str, ctx: dict) -> None:
    for key in ctx["dirty"]:
        if key[0] == "payin":
            effects = _effects_payin(state, key[1])
        elif key[0] == "payout":
            effects = _effects_payout(state, key[1])
        else:
            effects = _effects_fee(state, key[1], key[2])
        for kind, ref, entries in effects:
            _sync(state, record_id, kind, ref, entries)


# --------------------------------------------------------------------------- handlers


def _h_fx_snapshot(state: dict, rec: dict, ctx: dict) -> None:
    sid = _req_str(rec, "snapshot_id")
    rate = _req_rate(rec, "rate")
    fx = state["fx"]
    if sid not in fx:
        fx[sid] = rate
    elif Decimal(fx[sid]) != Decimal(rate):
        state["fx_conflicts"][sid] = True  # first rate stays in force


def _h_payin_api_result(state: dict, rec: dict, ctx: dict) -> None:
    pid = _req_str(rec, "payin_id")
    cid = _req_str(rec, "customer_id")
    _req_choice(rec, "result", ("timeout",))
    _req_ts(rec, "at")
    pi = state["payins"].get(pid)
    if pi is None:
        state["payins"][pid] = {"customer_id": cid, "credited": False, "timeout": True}
    else:
        pi["timeout"] = True


def _h_payin_succeeded(state: dict, rec: dict, ctx: dict) -> None:
    pid = _req_str(rec, "payin_id")
    cid = _req_str(rec, "customer_id")
    cur = _req_choice(rec, "currency", _CURRENCIES)
    amount = _req_int(rec, "amount_minor")
    occurred = _req_ts(rec, "occurred_at")
    sid, rate = None, None
    if cur == "USD":
        sid = _req_str(rec, "fx_snapshot_id")
        if sid not in state["fx"]:
            raise ValueError(f"unknown fx snapshot {sid!r}")
        rate = state["fx"][sid]
    pi = state["payins"].get(pid)
    if pi is not None and pi.get("credited"):
        return  # credits once per payin_id
    state["payins"][pid] = {
        "customer_id": cid, "credited": True,
        "timeout": bool(pi.get("timeout")) if pi else False,
        "currency": cur, "amount": amount,
        "occurred_at": rec["occurred_at"], "date": _lagos_date(occurred),
        "snapshot_id": sid, "rate": rate,
    }
    _dirty(ctx, ("payin", pid))


def _h_payin_reversed(state: dict, rec: dict, ctx: dict) -> None:
    xid = _req_str(rec, "reversal_id")
    pid = _req_str(rec, "payin_id")
    cur = _req_choice(rec, "currency", _CURRENCIES)
    amount = _req_int(rec, "amount_minor")
    occurred = _req_ts(rec, "occurred_at")
    if xid in state["reversals"]:
        return
    state["reversals"][xid] = {
        "payin_id": pid, "currency": cur, "amount": amount,
        "occurred_at": rec["occurred_at"], "at_us": _us(occurred), "date": _lagos_date(occurred),
    }
    state["payin_revs"].setdefault(pid, []).append(xid)
    _dirty(ctx, ("payin", pid))


def _h_payout_requested(state: dict, rec: dict, ctx: dict) -> None:
    oid = _req_str(rec, "payout_id")
    cid = _req_str(rec, "customer_id")
    amount = _req_int(rec, "amount_minor")
    occurred = _req_ts(rec, "occurred_at")
    if oid in state["payouts"]:
        return
    available = -state["acct"].get(_avail(cid), 0)
    po = {
        "customer_id": cid, "amount": amount, "occurred_at": rec["occurred_at"],
        "hold_date": _lagos_date(occurred), "reference": _reference(oid),
        "status": SENDING if available >= amount else REJECTED,
        "first_sent_us": None, "last_sent_us": None, "resolved_date": None,
    }
    state["payouts"][oid] = po
    if po["status"] == SENDING:
        ctx["cmds"].append({"command": "send", "payout_id": oid, "reference": po["reference"]})
    elif _cur_line(state, "PAYOUT", oid) is not None:
        _payout_conflict(state, oid)
    _dirty(ctx, ("payout", oid))


def _h_payout_send_result(state: dict, rec: dict, ctx: dict) -> None:
    oid = _req_str(rec, "payout_id")
    result = _req_choice(rec, "result", ("accepted", "rejected", "timeout"))
    sent = _req_ts(rec, "sent_at")
    po = state["payouts"].get(oid)
    if po is None:
        return
    us = _us(sent)
    po["first_sent_us"] = us if po["first_sent_us"] is None else min(po["first_sent_us"], us)
    po["last_sent_us"] = us if po["last_sent_us"] is None else max(po["last_sent_us"], us)
    status = po["status"]
    if status in _OPEN_PAYOUT:
        if result == "accepted":
            _resolve_payout(state, po, oid, PAID, _lagos_date(sent))
        elif result == "rejected":
            _resolve_payout(state, po, oid, FAILED, _lagos_date(sent))
        else:
            po["status"] = UNKNOWN
    elif status == PAID:
        if result == "rejected":
            _payout_conflict(state, oid)
    elif result == "accepted":  # FAILED or REJECTED
        _payout_conflict(state, oid)
    _dirty(ctx, ("payout", oid))


def _h_payout_retry(state: dict, rec: dict, ctx: dict) -> None:
    oid = _req_str(rec, "payout_id")
    at = _req_ts(rec, "at")
    po = state["payouts"].get(oid)
    if po is None or po["status"] != UNKNOWN:
        return
    first = po["first_sent_us"]
    if first is not None and _us(at) < first + _IDEMPOTENCY_US:
        command = "send"
    else:
        command = "lookup"  # past the idempotency window a send could pay twice
    ctx["cmds"].append({"command": command, "payout_id": oid, "reference": po["reference"]})


def _h_payout_lookup(state: dict, rec: dict, ctx: dict) -> None:
    oid = _req_str(rec, "payout_id")
    result = _req_choice(rec, "result", ("accepted", "rejected", "not_found"))
    at = _req_ts(rec, "at")
    po = state["payouts"].get(oid)
    if po is None:
        return
    status = po["status"]
    if status in _OPEN_PAYOUT:
        if result == "accepted":
            _resolve_payout(state, po, oid, PAID, _lagos_date(at))
        elif result == "rejected":
            _resolve_payout(state, po, oid, FAILED, _lagos_date(at))
        elif po["last_sent_us"] is not None and _us(at) >= po["last_sent_us"] + _VISIBILITY_US:
            _resolve_payout(state, po, oid, FAILED, _lagos_date(at))
    elif status == PAID:
        if result == "rejected":
            _payout_conflict(state, oid)
    elif result == "accepted":
        _payout_conflict(state, oid)
    _dirty(ctx, ("payout", oid))


def _h_settlement_file(state: dict, rec: dict, ctx: dict) -> None:
    bid = _req_str(rec, "batch_id")
    seq = rec.get("file_seq")
    if isinstance(seq, bool) or not isinstance(seq, int):
        raise ValueError("field 'file_seq' must be an integer")
    vd = _req_date(rec, "value_date")
    lines = rec.get("lines")
    if not isinstance(lines, list):
        raise ValueError("field 'lines' must be a list")
    agg: dict = {}
    for ln in lines:
        if not isinstance(ln, dict):
            raise ValueError("settlement line must be an object")
        lt = _req_choice(ln, "line_type", _LINE_TYPES)
        ref = _req_str(ln, "ref")
        cur = _req_choice(ln, "currency", _CURRENCIES)
        amount = _req_int(ln, "amount_minor")
        settled = _req_int(ln, "settled_ngn_minor")
        _req_str(ln, "line_id")
        key = (lt, ref)
        entry = agg.get(key)
        if entry is None:
            agg[key] = {"batch": bid, "currency": cur, "amount": amount,
                        "settled": settled, "value_date": vd}
        else:
            if entry["currency"] != cur:
                entry["currency"] = "MIXED"  # can never agree with an item
            entry["amount"] += amount
            entry["settled"] += settled

    batch = state["batches"].get(bid)
    if batch is not None and seq <= batch["file_seq"]:
        return  # void (lower) or ignored (equal) file

    index = state["lines"]
    old_keys = [tuple(k) for k in batch["keys"]] if batch is not None else []
    for lt, ref in old_keys:
        per = index.get(lt, {})
        if ref in per and per[ref]["batch"] == bid:
            del per[ref]
            if not per:
                index.pop(lt, None)
    for (lt, ref), entry in agg.items():
        index.setdefault(lt, {})[ref] = entry
    state["batches"][bid] = {"file_seq": seq, "value_date": vd,
                             "keys": [[lt, ref] for (lt, ref) in agg]}

    for lt, ref in old_keys + list(agg):
        if lt == "PAYIN":
            _dirty(ctx, ("payin", ref))
        elif lt == "PAYIN_REVERSAL":
            rv = state["reversals"].get(ref)
            if rv is not None:
                _dirty(ctx, ("payin", rv["payin_id"]))
        elif lt == "PAYOUT":
            _dirty(ctx, ("payout", ref))
        else:
            _dirty(ctx, ("fee", lt, ref))

    for lt, ref in agg:
        if lt != "PAYOUT":
            continue
        po = state["payouts"].get(ref)
        if po is None:
            continue  # stays an unmatched line
        if po["status"] in _OPEN_PAYOUT:
            _resolve_payout(state, po, ref, PAID, vd)
        elif po["status"] in (FAILED, REJECTED):
            _payout_conflict(state, ref)


def _h_period_closed(state: dict, rec: dict, ctx: dict) -> None:
    period = rec.get("period")
    if not isinstance(period, str) or not _PERIOD_RE.match(period):
        raise ValueError("field 'period' must be YYYY-MM")
    if state["closed"] is None or period > state["closed"]:
        state["closed"] = period


_HANDLERS = {
    "fx.snapshot": _h_fx_snapshot,
    "payin.api_result": _h_payin_api_result,
    "payin.succeeded": _h_payin_succeeded,
    "payin.reversed": _h_payin_reversed,
    "payout.requested": _h_payout_requested,
    "payout.send_result": _h_payout_send_result,
    "payout.retry_requested": _h_payout_retry,
    "payout.lookup_result": _h_payout_lookup,
    "settlement.file": _h_settlement_file,
    "period.closed": _h_period_closed,
}

# --------------------------------------------------------------------------- public API


def apply(state: dict, record: dict) -> list[dict]:
    """Apply one record. Mutates state (starting from {}) and returns provider commands."""
    if not isinstance(record, dict):
        raise ValueError("record must be an object")
    _init(state)
    record_id = _req_str(record, "record_id")
    if record_id in state["seen"]:
        return []
    handler = _HANDLERS.get(record.get("type"))
    if handler is None:
        raise ValueError(f"unknown record type {record.get('type')!r}")
    ctx = {"dirty": [], "dirty_set": set(), "cmds": []}
    handler(state, record, ctx)  # handlers validate fully before mutating
    state["seen"][record_id] = True
    _flush(state, record_id, ctx)
    return [dict(c) for c in ctx["cmds"]]


def balances(state: dict) -> dict:
    _init(state)
    out: dict = {}
    for account, total in state["acct"].items():
        if not account.startswith("customer:"):
            continue
        cust, _, bucket = account[len("customer:"):].rpartition(":")
        if bucket not in ("available", "held"):
            continue
        entry = out.setdefault(cust, {"available": 0, "held": 0})
        entry[bucket] = -total
    return out


def payin_status(state: dict, payin_id: str) -> str | None:
    _init(state)
    pi = state["payins"].get(payin_id)
    if pi is None:
        return None
    if not pi.get("credited"):
        return "PENDING" if pi.get("timeout") else None
    calc = _payin_calc(state, payin_id)
    counted = sum(r["counted"] for r in calc["rows"])
    if counted == 0:
        return "SUCCEEDED"
    if counted >= pi["amount"]:
        return "REVERSED"
    return "PARTIALLY_REVERSED"


def payout_status(state: dict, payout_id: str) -> str | None:
    _init(state)
    po = state["payouts"].get(payout_id)
    return None if po is None else po["status"]


def journal(state: dict) -> list[dict]:
    _init(state)
    return [dict(line) for line in state["journal"]]


def period_totals(state: dict, period: str) -> dict:
    _init(state)
    return {a: v for a, v in state["ptotals"].get(period, {}).items() if v != 0}


def _posted_receivable(state: dict, kind: str, ref: str) -> int:
    return sum(state["posted"].get(kind, {}).get(ref, {}).get(RECEIVABLE, {}).values())


def reconciliation(state: dict) -> dict:
    _init(state)
    index = state["lines"]
    provider_net = 0
    for lt, per in index.items():
        for entry in per.values():
            provider_net += _LINE_SIGN[lt] * entry["settled"]
    kinds = {"PAYIN": ("CREDIT", "FXPAYIN"), "PAYIN_REVERSAL": ("REV", "FXREV"), "PAYOUT": ("PAID",)}
    keys = set()
    for lt in _ITEM_LINE_TYPES:
        keys.update((lt, ref) for ref in index.get(lt, {}))
        for kind in kinds[lt]:
            keys.update((lt, ref) for ref in state["posted"].get(kind, {}))
    breaks = []
    for lt, ref in sorted(keys):
        line = index.get(lt, {}).get(ref)
        provider = _LINE_SIGN[lt] * line["settled"] if line is not None else 0
        ours = sum(_posted_receivable(state, kind, ref) for kind in kinds[lt])
        delta = provider - ours
        if delta != 0:
            breaks.append({"line_type": lt, "ref": ref, "delta_minor": delta})
    return {"ledger_receivable": state["acct"].get(RECEIVABLE, 0),
            "provider_net": provider_net,
            "breaks": breaks}


def exceptions(state: dict) -> list[dict]:
    _init(state)
    found: set = set()
    for sid in state["fx_conflicts"]:
        found.add(("FX_SNAPSHOT_CONFLICT", sid))
    for pid, pi in state["payins"].items():
        if not pi.get("credited") and pi.get("timeout"):
            found.add(("PAYIN_OUTCOME_UNKNOWN", pid))
    rev_rows = _all_reversal_rows(state)
    for xid, (pid, credited, row) in rev_rows.items():
        if not credited:
            found.add(("ORPHAN_REVERSAL", xid))
        elif row["counted"] < state["reversals"][xid]["amount"]:
            found.add(("REVERSAL_EXCEEDS_PAYIN", xid))
    for cust, bal in balances(state).items():
        if bal["available"] < 0:
            found.add(("NEGATIVE_BALANCE", cust))
    for oid, po in state["payouts"].items():
        if po["status"] == UNKNOWN:
            found.add(("PAYOUT_OUTCOME_UNKNOWN", oid))
    for oid in state["payout_conflicts"]:
        found.add(("PAYOUT_CONFLICT", oid))

    index = state["lines"]
    for ref, line in index.get("PAYIN", {}).items():
        pi = state["payins"].get(ref)
        if pi is None or not pi.get("credited"):
            found.add(("UNMATCHED_SETTLEMENT_LINE", ref))
        elif not _agrees(line, pi["currency"], pi["amount"]):
            found.add(("SETTLEMENT_AMOUNT_MISMATCH", ref))
    for ref, line in index.get("PAYIN_REVERSAL", {}).items():
        info = rev_rows.get(ref)
        if info is None or not info[1] or info[2]["counted"] <= 0:
            found.add(("UNMATCHED_SETTLEMENT_LINE", ref))
        else:
            pi = state["payins"][info[0]]
            if not _agrees(line, pi["currency"], info[2]["counted"]):
                found.add(("SETTLEMENT_AMOUNT_MISMATCH", ref))
    for ref, line in index.get("PAYOUT", {}).items():
        po = state["payouts"].get(ref)
        if po is not None and po["status"] in (FAILED, REJECTED):
            found.add(("PAYOUT_CONFLICT", ref))
        elif po is None or po["status"] != PAID:
            found.add(("UNMATCHED_SETTLEMENT_LINE", ref))
        elif not _agrees(line, "NGN", po["amount"]):
            found.add(("SETTLEMENT_AMOUNT_MISMATCH", ref))
    for ref, line in index.get("FEE_REFUND", {}).items():
        contractual = 0
        info = rev_rows.get(ref)
        if info is not None and info[1] and info[2]["counted"] > 0:
            pi = state["payins"][info[0]]
            a = pi["amount"]
            fee_line = index.get("FEE", {}).get(info[0])
            f = fee_line["amount"] if fee_line is not None else 0
            if a > 0:
                contractual = (f * info[2]["after"]) // a - (f * info[2]["before"]) // a
        if line["amount"] != contractual:
            found.add(("FEE_REFUND_MISMATCH", ref))
    return [{"code": c, "ref": r} for c, r in sorted(found)]
```
