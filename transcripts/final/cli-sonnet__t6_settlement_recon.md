# cli-sonnet / t6_settlement_recon / trial 1

- Requested: `sonnet`, resolved: `claude-haiku-5-5,claude-sonnet-5-5`, provider: claude-cli
- Run at 2026-10-31T20:37:43+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t6_settlement_recon/prompt.md`.

## Model output

```python
"""Daily PSP settlement reconciliation engine (standard library only)."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

_NY = ZoneInfo("America/New_York")

# ISO 4217 minor-unit exponents that differ from the default of 2.
_ZERO_DECIMAL = {
    "BIF", "CLP", "DJF", "GNF", "ISK", "JPY", "KMF", "KRW", "PYG",
    "RWF", "UGX", "UYI", "VND", "VUV", "XAF", "XOF", "XPF",
}
_THREE_DECIMAL = {"BHD", "IQD", "JOD", "KWD", "LYD", "OMR", "TND"}
_FOUR_DECIMAL = {"CLF", "UYW"}

_AMOUNT_RE = re.compile(r"^(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.([0-9]+))?$")

_RECONCILED_TYPES = {"SALE", "REFUND", "CHARGEBACK", "CHARGEBACK_REVERSAL"}


def _exponent(currency: str) -> int:
    cur = currency.strip().upper()
    if cur in _ZERO_DECIMAL:
        return 0
    if cur in _THREE_DECIMAL:
        return 3
    if cur in _FOUR_DECIMAL:
        return 4
    return 2


def _parse_amount(text: str, currency: str) -> int:
    """Convert a processor major-unit string to exact integer minor units."""
    s = text.strip()
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1].strip()
    elif s.startswith("-"):
        negative = True
        s = s[1:].strip()

    m = _AMOUNT_RE.match(s)
    if not m:
        raise ValueError(f"invalid amount {text!r}")

    exp = _exponent(currency)
    frac = m.group(1) or ""
    if len(frac) > exp:
        raise ValueError(
            f"amount {text!r} has more than {exp} decimal places for {currency}"
        )

    int_part = s.split(".")[0].replace(",", "")
    minor = int(int_part) * (10 ** exp) + (int(frac.ljust(exp, "0")) if exp else 0)
    return -minor if negative else minor


def _parse_event_time(text: str) -> datetime:
    t = text.strip()
    if t.endswith(("Z", "z")):
        t = t[:-1] + "+00:00"
    dt = datetime.fromisoformat(t)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _business_date(event_time: str, holidays: set[date]) -> date:
    local = _parse_event_time(event_time).astimezone(_NY)
    d = local.date()
    if local.hour >= 17:  # at or after 17:00 local -> next calendar day
        d += timedelta(days=1)
    while d.weekday() >= 5 or d in holidays:
        d += timedelta(days=1)
    return d


def _add(groups: dict, key: tuple, amount: int, bdate: date) -> None:
    entry = groups.get(key)
    if entry is None:
        groups[key] = [amount, bdate]
    else:
        entry[0] += amount
        if bdate > entry[1]:
            entry[1] = bdate


def reconcile(
    ledger_rows: list[dict],
    settlement_lines: list[dict],
    holidays: list[str],
) -> list[dict]:
    holiday_set = {date.fromisoformat(h.strip()) for h in holidays}

    # ---- Settlement side: keep only the highest file_seq per batch_id ----
    # (determined over all lines of the batch, before any other filtering)
    max_seq: dict[str, int] = {}
    for line in settlement_lines:
        seq = int(str(line["file_seq"]).strip())
        batch = line["batch_id"]
        if batch not in max_seq or seq > max_seq[batch]:
            max_seq[batch] = seq

    settlement: dict[tuple, list] = {}
    for line in settlement_lines:
        if int(str(line["file_seq"]).strip()) != max_seq[line["batch_id"]]:
            continue
        ltype = line["line_type"].strip()
        if ltype not in _RECONCILED_TYPES:  # FEE (and anything non-reconciled)
            continue
        currency = line["currency"].strip().upper()
        amount = _parse_amount(line["amount"], currency)
        bdate = _business_date(line["event_time"], holiday_set)
        _add(settlement, (line["psp_ref"], ltype, currency), amount, bdate)

    # ---- Ledger side ----
    ledger: dict[tuple, list] = {}
    for row in ledger_rows:
        rtype = row["type"]
        if rtype not in _RECONCILED_TYPES:
            continue
        currency = row["currency"].strip().upper()
        bdate = date.fromisoformat(row["business_date"])
        _add(ledger, (row["psp_ref"], rtype, currency), int(row["amount_minor"]), bdate)

    # ---- Chargeback netting ----
    to_remove = []
    for (ref, ltype, cur) in list(settlement):
        if ltype != "CHARGEBACK":
            continue
        cb_key = (ref, "CHARGEBACK", cur)
        rev_key = (ref, "CHARGEBACK_REVERSAL", cur)
        if rev_key not in settlement:
            continue
        if cb_key in ledger or rev_key in ledger:
            continue
        if settlement[cb_key][0] + settlement[rev_key][0] == 0:
            to_remove.extend((cb_key, rev_key))
    for key in to_remove:
        settlement.pop(key, None)

    # ---- Matching ----
    results = []
    for key in set(settlement) | set(ledger):
        s = settlement.get(key)
        l = ledger.get(key)
        if s is not None and l is None:
            brk, delta = "MISSING_IN_LEDGER", s[0]
        elif l is not None and s is None:
            brk, delta = "MISSING_IN_SETTLEMENT", -l[0]
        elif s[0] != l[0]:
            brk, delta = "AMOUNT_MISMATCH", s[0] - l[0]
        elif s[1] != l[1]:
            brk, delta = "TIMING", 0
        else:
            continue
        results.append(
            {
                "psp_ref": key[0],
                "type": key[1],
                "currency": key[2],
                "break": brk,
                "delta_minor": delta,
            }
        )

    results.sort(key=lambda r: (r["psp_ref"], r["type"], r["currency"]))
    return results
```
