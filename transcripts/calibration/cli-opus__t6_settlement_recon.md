# cli-opus / t6_settlement_recon / trial 1

- Requested: `opus`, resolved: `claude-haiku-5-5,claude-opus-5-5`, provider: claude-cli
- Run at 2026-10-31T14:41:36+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t6_settlement_recon/prompt.md`.

## Model output

```python
"""Daily PSP settlement reconciliation: ledger versus processor settlement data.

Behaviour worth knowing when reading the output:

* Voiding happens before FEE filtering. A corrected file containing only FEE
  lines therefore still voids every lower file_seq of that batch.
* file_seq is compared numerically, so "12" is higher than "9".
* Only live, non-FEE lines are parsed for amount and event_time.
* Malformed input raises ValueError instead of producing a wrong break list.
  This includes an amount with more non-zero decimals than the currency
  allows, and a negative shown any way other than in parentheses.
* Currencies not listed in _NON_TWO_DECIMAL_EXPONENTS are treated as having
  two decimal places, as nearly all ISO 4217 currencies do.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

_FEE = "FEE"
_CHARGEBACK = "CHARGEBACK"
_CHARGEBACK_REVERSAL = "CHARGEBACK_REVERSAL"

_BUSINESS_TZ = ZoneInfo("America/New_York")
_CUTOFF_HOUR = 17

_DEFAULT_EXPONENT = 2
_NON_TWO_DECIMAL_EXPONENTS = {
    **dict.fromkeys(
        (
            "BIF", "CLP", "DJF", "GNF", "ISK", "JPY", "KMF", "KRW", "PYG",
            "RWF", "UGX", "UYI", "VND", "VUV", "XAF", "XOF", "XPF",
        ),
        0,
    ),
    **dict.fromkeys(("BHD", "IQD", "JOD", "KWD", "LYD", "OMR", "TND"), 3),
    **dict.fromkeys(("CLF", "UYW"), 4),
}

_AMOUNT_RE = re.compile(
    r"(?P<whole>[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.(?P<frac>[0-9]+))?"
)

GroupKey = tuple[str, str, str]  # (psp_ref, type, currency)
Group = tuple[int, date]  # (amount_minor, latest business date)


def _to_minor_units(amount: str, currency: str) -> int:
    """Convert processor amount text to integer minor units exactly."""
    text = amount.strip()
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1].strip()

    match = _AMOUNT_RE.fullmatch(text)
    if match is None:
        raise ValueError(f"Malformed settlement amount: {amount!r}")

    exponent = _NON_TWO_DECIMAL_EXPONENTS.get(currency, _DEFAULT_EXPONENT)
    whole = match.group("whole").replace(",", "")
    fraction = match.group("frac") or ""
    kept, excess = fraction[:exponent], fraction[exponent:]
    if excess.strip("0"):
        raise ValueError(
            f"Amount {amount!r} exceeds the precision of {currency} "
            f"({exponent} decimal places)"
        )

    minor = int(whole + kept.ljust(exponent, "0"))
    return -minor if negative else minor


def _business_date(event_time: str, holidays: set[date]) -> date:
    """Derive the business date of a UTC event timestamp."""
    # datetime.fromisoformat does not accept a "Z" suffix before Python 3.11.
    moment = datetime.fromisoformat(event_time.strip().replace("Z", "+00:00"))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)

    local = moment.astimezone(_BUSINESS_TZ)
    result = local.date()
    if local.hour >= _CUTOFF_HOUR:
        result += timedelta(days=1)
    while result.weekday() >= 5 or result in holidays:
        result += timedelta(days=1)
    return result


def _live_lines(settlement_lines: list[dict]) -> list[dict]:
    """Keep only the lines in the highest file_seq of each batch."""
    latest: dict[str, int] = {}
    for line in settlement_lines:
        batch_id = line["batch_id"]
        seq = int(line["file_seq"])
        if batch_id not in latest or seq > latest[batch_id]:
            latest[batch_id] = seq
    return [
        line
        for line in settlement_lines
        if int(line["file_seq"]) == latest[line["batch_id"]]
    ]


def _add_to_group(
    groups: dict[GroupKey, Group],
    key: GroupKey,
    amount_minor: int,
    business_date: date,
) -> None:
    existing = groups.get(key)
    if existing is None:
        groups[key] = (amount_minor, business_date)
    else:
        groups[key] = (
            existing[0] + amount_minor,
            max(existing[1], business_date),
        )


def _group_ledger(ledger_rows: list[dict]) -> dict[GroupKey, Group]:
    groups: dict[GroupKey, Group] = {}
    for row in ledger_rows:
        if row["type"] == _FEE:
            continue
        key = (row["psp_ref"], row["type"], row["currency"])
        _add_to_group(
            groups,
            key,
            row["amount_minor"],
            date.fromisoformat(row["business_date"]),
        )
    return groups


def _group_settlement(
    settlement_lines: list[dict], holidays: set[date]
) -> dict[GroupKey, Group]:
    groups: dict[GroupKey, Group] = {}
    for line in _live_lines(settlement_lines):
        if line["line_type"] == _FEE:
            continue
        currency = line["currency"]
        key = (line["psp_ref"], line["line_type"], currency)
        _add_to_group(
            groups,
            key,
            _to_minor_units(line["amount"], currency),
            _business_date(line["event_time"], holidays),
        )
    return groups


def _net_chargebacks(
    settlement: dict[GroupKey, Group], ledger: dict[GroupKey, Group]
) -> None:
    """Remove settlement chargeback pairs that net to zero, in place."""
    candidates = [
        (psp_ref, currency)
        for psp_ref, type_, currency in settlement
        if type_ == _CHARGEBACK
    ]
    for psp_ref, currency in candidates:
        chargeback = (psp_ref, _CHARGEBACK, currency)
        reversal = (psp_ref, _CHARGEBACK_REVERSAL, currency)
        if reversal not in settlement:
            continue
        if chargeback in ledger or reversal in ledger:
            continue
        if settlement[chargeback][0] + settlement[reversal][0] == 0:
            del settlement[chargeback]
            del settlement[reversal]


def _classify(
    settlement_group: Group | None, ledger_group: Group | None
) -> tuple[str, int] | None:
    """Return (break, delta_minor) for a group key, or None if it matches."""
    if ledger_group is None:
        return "MISSING_IN_LEDGER", settlement_group[0]
    if settlement_group is None:
        return "MISSING_IN_SETTLEMENT", -ledger_group[0]

    settlement_amount, settlement_date = settlement_group
    ledger_amount, ledger_date = ledger_group
    if settlement_amount != ledger_amount:
        return "AMOUNT_MISMATCH", settlement_amount - ledger_amount
    if settlement_date != ledger_date:
        return "TIMING", 0
    return None


def reconcile(
    ledger_rows: list[dict],
    settlement_lines: list[dict],
    holidays: list[str],
) -> list[dict]:
    """Compare ledger and settlement data and return the sorted break list."""
    holiday_dates = {date.fromisoformat(holiday) for holiday in holidays}

    ledger = _group_ledger(ledger_rows)
    settlement = _group_settlement(settlement_lines, holiday_dates)
    _net_chargebacks(settlement, ledger)

    breaks: list[dict] = []
    for key in sorted(settlement.keys() | ledger.keys()):
        outcome = _classify(settlement.get(key), ledger.get(key))
        if outcome is None:
            continue
        psp_ref, type_, currency = key
        break_type, delta_minor = outcome
        breaks.append(
            {
                "psp_ref": psp_ref,
                "type": type_,
                "currency": currency,
                "break": break_type,
                "delta_minor": delta_minor,
            }
        )
    return breaks
```
