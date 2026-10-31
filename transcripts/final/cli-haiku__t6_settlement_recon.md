# cli-haiku / t6_settlement_recon / trial 1

- Requested: `haiku`, resolved: `claude-haiku-5-5`, provider: claude-cli
- Run at 2026-10-31T20:51:38+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t6_settlement_recon/prompt.md`.

## Model output

```python
from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

_NY = ZoneInfo("America/New_York")
_CUTOFF = time(17, 0)

_FEE = "FEE"
_CB = "CHARGEBACK"
_CBR = "CHARGEBACK_REVERSAL"

# ISO 4217 minor-unit exponents that differ from the default of 2.
_EXP0 = frozenset({
    "BIF", "CLP", "DJF", "GNF", "ISK", "JPY", "KMF", "KRW", "PYG",
    "RWF", "UGX", "UYI", "VND", "VUV", "XAF", "XOF", "XPF",
})
_EXP3 = frozenset({"BHD", "IQD", "JOD", "KWD", "LYD", "OMR", "TND"})
_EXP4 = frozenset({"CLF", "UYW"})

_CURRENCY_RE = re.compile(r"[A-Z]{3}")
_NUMBER_RE = re.compile(r"[+-]?(\d+\.?\d*|\.\d+)")


def _minor_exponent(currency: str) -> int:
    if not _CURRENCY_RE.fullmatch(currency):
        raise ValueError(f"invalid ISO 4217 currency code: {currency!r}")
    if currency in _EXP0:
        return 0
    if currency in _EXP3:
        return 3
    if currency in _EXP4:
        return 4
    return 2


def _parse_amount(text: str, currency: str) -> int:
    """Parse a processor amount string (major units, optional thousands
    separators, accounting-style parentheses for negatives) into exact
    integer minor units."""
    if not isinstance(text, str):
        raise ValueError(f"amount must be a string, got {type(text).__name__}")

    s = text.strip()
    negative = False
    if s.startswith("(") or s.endswith(")"):
        if not (s.startswith("(") and s.endswith(")")):
            raise ValueError(f"unbalanced parentheses in amount: {text!r}")
        negative = True
        s = s[1:-1].strip()

    s = s.replace(",", "")

    if not _NUMBER_RE.fullmatch(s):
        raise ValueError(f"malformed amount: {text!r}")
    if negative and s[0] in "+-":
        raise ValueError(f"sign combined with parentheses in amount: {text!r}")

    try:
        value = Decimal(s)
    except InvalidOperation as exc:
        raise ValueError(f"malformed amount: {text!r}") from exc
    if not value.is_finite():
        raise ValueError(f"non-finite amount: {text!r}")
    if negative:
        value = -value

    scaled = value.scaleb(_minor_exponent(currency))
    if scaled != scaled.to_integral_value():
        raise ValueError(
            f"amount {text!r} has more precision than {currency} allows"
        )
    return int(scaled)


def _business_date(event_time: str, holidays: frozenset[date]) -> date:
    """UTC event timestamp -> business date in America/New_York, with the
    17:00 cutoff and weekend/holiday roll-forward applied."""
    text = event_time.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    ts = datetime.fromisoformat(text)
    if ts.tzinfo is None:
        raise ValueError(f"event_time has no timezone: {event_time!r}")

    local = ts.astimezone(_NY)
    d = local.date()
    if local.time() >= _CUTOFF:
        d += timedelta(days=1)
    while d.weekday() >= 5 or d in holidays:
        d += timedelta(days=1)
    return d


def _accumulate(groups: dict, key: tuple, amount: int, bdate: date) -> None:
    """Sum amounts per key and keep the latest business date."""
    group = groups.get(key)
    if group is None:
        groups[key] = [amount, bdate]
    else:
        group[0] += amount
        if bdate > group[1]:
            group[1] = bdate


def reconcile(
    ledger_rows: list[dict],
    settlement_lines: list[dict],
    holidays: list[str],
) -> list[dict]:
    holiday_set = frozenset(date.fromisoformat(h) for h in holidays)

    # Ledger side: canonical rows, FEE ignored.
    ledger: dict[tuple, list] = {}
    for row in ledger_rows:
        if row["type"] == _FEE:
            continue
        key = (row["psp_ref"], row["type"], row["currency"])
        _accumulate(
            ledger,
            key,
            int(row["amount_minor"]),
            date.fromisoformat(row["business_date"]),
        )

    # Settlement side, step 1: keep only the highest file_seq per batch.
    latest_seq: dict[str, int] = {}
    for line in settlement_lines:
        seq = int(line["file_seq"])
        batch = line["batch_id"]
        if batch not in latest_seq or seq > latest_seq[batch]:
            latest_seq[batch] = seq

    # Settlement side, step 2: parse, date, and group.
    settlement: dict[tuple, list] = {}
    for line in settlement_lines:
        if line["line_type"] == _FEE:
            continue
        if int(line["file_seq"]) != latest_seq[line["batch_id"]]:
            continue
        currency = line["currency"]
        key = (line["psp_ref"], line["line_type"], currency)
        _accumulate(
            settlement,
            key,
            _parse_amount(line["amount"], currency),
            _business_date(line["event_time"], holiday_set),
        )

    # Chargeback netting.
    pairs = {
        (psp, cur)
        for (psp, typ, cur) in settlement
        if typ in (_CB, _CBR)
    }
    for psp, cur in sorted(pairs):
        k_cb = (psp, _CB, cur)
        k_cbr = (psp, _CBR, cur)
        if (
            k_cb in settlement
            and k_cbr in settlement
            and settlement[k_cb][0] + settlement[k_cbr][0] == 0
            and k_cb not in ledger
            and k_cbr not in ledger
        ):
            del settlement[k_cb]
            del settlement[k_cbr]

    # Matching.
    results: list[dict] = []
    for key in set(ledger) | set(settlement):
        psp_ref, typ, cur = key

        if key in settlement and key not in ledger:
            brk, delta = "MISSING_IN_LEDGER", settlement[key][0]
        elif key in ledger and key not in settlement:
            brk, delta = "MISSING_IN_SETTLEMENT", -ledger[key][0]
        else:
            s_amt, s_date = settlement[key]
            l_amt, l_date = ledger[key]
            if s_amt != l_amt:
                brk, delta = "AMOUNT_MISMATCH", s_amt - l_amt
            elif s_date != l_date:
                brk, delta = "TIMING", 0
            else:
                continue

        results.append({
            "psp_ref": psp_ref,
            "type": typ,
            "currency": cur,
            "break": brk,
            "delta_minor": delta,
        })

    results.sort(key=lambda r: (r["psp_ref"], r["type"], r["currency"]))
    return results
```
