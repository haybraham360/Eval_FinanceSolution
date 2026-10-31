# cli-haiku / t6_settlement_recon / trial 1

- Requested: `haiku`, resolved: `claude-haiku-5-5`, provider: claude-cli
- Run at 2026-10-31T14:45:56+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t6_settlement_recon/prompt.md`.

## Model output

```python
"""Daily PSP settlement reconciliation matching engine.

Standard library only. Requires Python 3.10+ (zoneinfo).
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

_NY = ZoneInfo("America/New_York")
_CUTOFF = time(17, 0)

# ISO 4217 minor-unit exponents that differ from the default of 2.
# Currencies not listed here use 2 decimal places.
_EXPONENT_OVERRIDES: dict[str, int] = {
    # 0 decimals
    **{c: 0 for c in (
        "BIF", "CLP", "DJF", "GNF", "ISK", "JPY", "KMF", "KRW",
        "PYG", "RWF", "UGX", "UYI", "VND", "VUV", "XAF", "XOF", "XPF",
    )},
    # 3 decimals
    **{c: 3 for c in ("BHD", "IQD", "JOD", "KWD", "LYD", "OMR", "TND")},
    # 4 decimals
    **{c: 4 for c in ("CLF", "UYW")},
}

# Digits with optional thousands separators in groups of three, or plain digits,
# with an optional fractional part.
_NUMBER_RE = re.compile(r"(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?")

_CB = "CHARGEBACK"
_CBR = "CHARGEBACK_REVERSAL"


def _exponent(currency: str) -> int:
    return _EXPONENT_OVERRIDES.get(currency, 2)


def _parse_amount(text: str, currency: str) -> int:
    """Convert a processor amount string to integer minor units exactly.

    Accepts accounting-style negatives in parentheses, or a leading '-'.
    Raises ValueError if the text is malformed or has non-zero digits
    beyond the currency's minor-unit precision.
    """
    s = text.strip()
    negative = False

    if s.startswith("(") or s.endswith(")"):
        if not (s.startswith("(") and s.endswith(")")):
            raise ValueError(f"unbalanced parentheses in amount {text!r}")
        negative = True
        s = s[1:-1].strip()
    elif s.startswith("-"):
        negative = True
        s = s[1:].strip()

    m = _NUMBER_RE.fullmatch(s)
    if m is None:
        raise ValueError(f"malformed amount {text!r}")

    int_part, frac_part = m.group(1).replace(",", ""), m.group(2) or ""
    exp = _exponent(currency)

    if len(frac_part) > exp:
        if frac_part[exp:].strip("0"):
            raise ValueError(
                f"amount {text!r} has more precision than {currency} allows ({exp} decimals)"
            )
        frac_part = frac_part[:exp]
    frac_part = frac_part.ljust(exp, "0")

    value = int(int_part + frac_part)
    return -value if negative else value


def _business_date(event_time: str, holidays: set[date]) -> date:
    """UTC event time -> America/New_York business date.

    At or after 17:00 local rolls to the next calendar day. Then any
    Saturday, Sunday or holiday rolls forward to the next business day.
    """
    s = event_time.strip()
    if s[-1:] in ("Z", "z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        raise ValueError(f"event_time has no timezone: {event_time!r}")

    local = dt.astimezone(_NY)
    d = local.date()
    if local.time() >= _CUTOFF:
        d += timedelta(days=1)
    while d.weekday() >= 5 or d in holidays:
        d += timedelta(days=1)
    return d


def _accumulate(groups: dict, key: tuple, amount: int, bdate: date) -> None:
    """Add an amount to a group and keep the latest business date."""
    if key in groups:
        groups[key][0] += amount
        groups[key][1] = max(groups[key][1], bdate)
    else:
        groups[key] = [amount, bdate]


def reconcile(
    ledger_rows: list[dict],
    settlement_lines: list[dict],
    holidays: list[str],
) -> list[dict]:
    hol = {date.fromisoformat(h) for h in holidays}

    # 1. Corrected files: keep only the highest file_seq per batch.
    best_seq: dict[str, int] = {}
    for line in settlement_lines:
        seq = int(line["file_seq"])
        batch = line["batch_id"]
        if batch not in best_seq or seq > best_seq[batch]:
            best_seq[batch] = seq
    current_lines = [
        line for line in settlement_lines
        if int(line["file_seq"]) == best_seq[line["batch_id"]]
    ]

    # 2. Group the ledger side. FEE rows are ignored.
    ledger: dict[tuple, list] = {}
    for row in ledger_rows:
        if row["type"] == "FEE":
            continue
        key = (row["psp_ref"], row["type"], row["currency"])
        _accumulate(
            ledger, key, int(row["amount_minor"]),
            date.fromisoformat(row["business_date"]),
        )

    # 3. Group the settlement side. FEE lines are ignored.
    settlement: dict[tuple, list] = {}
    for line in current_lines:
        if line["line_type"] == "FEE":
            continue
        key = (line["psp_ref"], line["line_type"], line["currency"])
        amount = _parse_amount(line["amount"], line["currency"])
        bdate = _business_date(line["event_time"], hol)
        _accumulate(settlement, key, amount, bdate)

    # 4. Chargeback netting, per (psp_ref, currency).
    for key in list(settlement):
        psp, typ, cur = key
        if typ != _CB:
            continue
        cb_key = (psp, _CB, cur)
        cbr_key = (psp, _CBR, cur)
        if (
            cbr_key in settlement
            and cb_key not in ledger
            and cbr_key not in ledger
            and settlement[cb_key][0] + settlement[cbr_key][0] == 0
        ):
            del settlement[cb_key]
            del settlement[cbr_key]

    # 5. Compare each group key present on either side.
    results: list[dict] = []
    for key in sorted(set(settlement) | set(ledger)):
        psp_ref, typ, cur = key

        if key in settlement and key in ledger:
            s_amt, s_date = settlement[key]
            l_amt, l_date = ledger[key]
            if s_amt != l_amt:
                brk, delta = "AMOUNT_MISMATCH", s_amt - l_amt
            elif s_date != l_date:
                brk, delta = "TIMING", 0
            else:
                continue
        elif key in settlement:
            brk, delta = "MISSING_IN_LEDGER", settlement[key][0]
        else:
            brk, delta = "MISSING_IN_SETTLEMENT", -ledger[key][0]

        results.append({
            "psp_ref": psp_ref,
            "type": typ,
            "currency": cur,
            "break": brk,
            "delta_minor": delta,
        })

    return results
```
