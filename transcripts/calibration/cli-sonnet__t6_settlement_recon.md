# cli-sonnet / t6_settlement_recon / trial 1

- Requested: `sonnet`, resolved: `claude-haiku-5-5,claude-sonnet-5-5`, provider: claude-cli
- Run at 2026-10-31T14:43:26+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t6_settlement_recon/prompt.md`.

## Model output

```python
"""Daily PSP settlement reconciliation engine."""

import re
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

_NY = ZoneInfo("America/New_York")

# ISO 4217 minor-unit exponents that differ from the default of 2.
_EXPONENTS = {
    # 0 decimals
    "BIF": 0, "CLP": 0, "DJF": 0, "GNF": 0, "ISK": 0, "JPY": 0, "KMF": 0,
    "KRW": 0, "PYG": 0, "RWF": 0, "UGX": 0, "UYI": 0, "VND": 0, "VUV": 0,
    "XAF": 0, "XOF": 0, "XPF": 0,
    # 3 decimals
    "BHD": 3, "IQD": 3, "JOD": 3, "KWD": 3, "LYD": 3, "OMR": 3, "TND": 3,
    # 4 decimals
    "CLF": 4, "UYW": 4,
}

_AMOUNT_RE = re.compile(r"^(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?$")

_FEE = "FEE"
_CB = "CHARGEBACK"
_CBR = "CHARGEBACK_REVERSAL"


def _exponent(currency: str) -> int:
    return _EXPONENTS.get(currency.strip().upper(), 2)


def _parse_amount(text: str, currency: str) -> int:
    """Convert a processor amount string to integer minor units, exactly."""
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
        raise ValueError(f"invalid amount: {text!r}")

    exp = _exponent(currency)
    body = s.replace(",", "")
    if "." in body:
        int_part, frac = body.split(".", 1)
    else:
        int_part, frac = body, ""

    if len(frac) > exp:
        extra = frac[exp:]
        if extra.strip("0"):
            raise ValueError(
                f"amount {text!r} exceeds {exp}-digit precision for {currency}"
            )
        frac = frac[:exp]
    frac = frac.ljust(exp, "0")

    value = int(int_part + frac) if (int_part + frac) else 0
    return -value if negative else value


def _parse_event_time(text: str) -> datetime:
    s = text.strip()
    if s.endswith(("Z", "z")):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _business_date(event_time: str, holidays: set) -> str:
    local = _parse_event_time(event_time).astimezone(_NY)
    d = local.date()
    if local.hour >= 17:
        d += timedelta(days=1)
    while d.weekday() >= 5 or d.isoformat() in holidays:
        d += timedelta(days=1)
    return d.isoformat()


def _add(groups: dict, key: tuple, amount: int, bdate: str) -> None:
    cur = groups.get(key)
    if cur is None:
        groups[key] = [amount, bdate]
    else:
        cur[0] += amount
        if bdate > cur[1]:
            cur[1] = bdate


def reconcile(ledger_rows: list, settlement_lines: list, holidays: list) -> list:
    holiday_set = {h.strip() for h in holidays}

    # ---- Ledger side ----
    ledger = {}
    for row in ledger_rows:
        if row["type"] == _FEE:
            continue
        key = (row["psp_ref"], row["type"], row["currency"])
        _add(ledger, key, int(row["amount_minor"]), row["business_date"])

    # ---- Settlement side: keep only the highest file_seq per batch ----
    max_seq = {}
    for line in settlement_lines:
        seq = int(line["file_seq"].strip())
        b = line["batch_id"]
        if b not in max_seq or seq > max_seq[b]:
            max_seq[b] = seq

    settlement = {}
    for line in settlement_lines:
        if int(line["file_seq"].strip()) != max_seq[line["batch_id"]]:
            continue
        if line["line_type"] == _FEE:
            continue
        currency = line["currency"].strip()
        amount = _parse_amount(line["amount"], currency)
        bdate = _business_date(line["event_time"], holiday_set)
        key = (line["psp_ref"], line["line_type"], currency)
        _add(settlement, key, amount, bdate)

    # ---- Chargeback netting ----
    pairs = {(k[0], k[2]) for k in settlement if k[1] in (_CB, _CBR)}
    for ref, cur in pairs:
        cb = (ref, _CB, cur)
        cbr = (ref, _CBR, cur)
        if cb not in settlement or cbr not in settlement:
            continue
        if cb in ledger or cbr in ledger:
            continue
        if settlement[cb][0] + settlement[cbr][0] == 0:
            del settlement[cb]
            del settlement[cbr]

    # ---- Matching ----
    breaks = []
    for key in set(settlement) | set(ledger):
        s = settlement.get(key)
        l = ledger.get(key)
        if l is None:
            kind, delta = "MISSING_IN_LEDGER", s[0]
        elif s is None:
            kind, delta = "MISSING_IN_SETTLEMENT", -l[0]
        elif s[0] != l[0]:
            kind, delta = "AMOUNT_MISMATCH", s[0] - l[0]
        elif s[1] != l[1]:
            kind, delta = "TIMING", 0
        else:
            continue
        breaks.append(
            {
                "psp_ref": key[0],
                "type": key[1],
                "currency": key[2],
                "break": kind,
                "delta_minor": delta,
            }
        )

    breaks.sort(key=lambda r: (r["psp_ref"], r["type"], r["currency"]))
    return breaks
```
