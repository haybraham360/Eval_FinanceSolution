# cli-opus / t6_settlement_recon / trial 1

- Requested: `opus`, resolved: `claude-haiku-5-5,claude-opus-5-5`, provider: claude-cli
- Run at 2026-10-31T20:25:02+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t6_settlement_recon/prompt.md`.

## Model output

```python
"""Daily PSP settlement reconciliation: matches ledger rows to processor lines.

Malformed input raises ValueError rather than producing a wrong break list.
This covers unknown currency codes, unparseable amounts and amounts with more
significant decimals than the currency allows. Amounts with fewer decimals
than the currency's precision, or with extra trailing zeros, are exact and
are accepted. Void lines and FEE lines are never parsed, so bad values in
them cannot fail the run.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from datetime import date, datetime, timedelta, timezone
from typing import NamedTuple
from zoneinfo import ZoneInfo

_NEW_YORK = ZoneInfo("America/New_York")
_CUTOFF_HOUR = 17

_FEE = "FEE"
_CHARGEBACK = "CHARGEBACK"
_CHARGEBACK_REVERSAL = "CHARGEBACK_REVERSAL"

_AMOUNT_RE = re.compile(r"(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?")

_CURRENCIES_BY_EXPONENT = {
    0: "BIF CLP DJF GNF ISK JPY KMF KRW PYG RWF UGX UYI VND VUV XAF XOF XPF",
    2: (
        "AED AFN ALL AMD ANG AOA ARS AUD AWG AZN BAM BBD BDT BGN BMD BND BOB "
        "BOV BRL BSD BTN BWP BYN BZD CAD CDF CHE CHF CHW CNY COP COU CRC CUP "
        "CVE CZK DKK DOP DZD EGP ERN ETB EUR FJD FKP GBP GEL GHS GIP GMD GTQ "
        "GYD HKD HNL HRK HTG HUF IDR ILS INR IRR JMD KES KGS KHR KPW KYD KZT "
        "LAK LBP LKR LRD LSL MAD MDL MGA MKD MMK MNT MOP MRU MUR MVR MWK MXN "
        "MXV MYR MZN NAD NGN NIO NOK NPR NZD PAB PEN PGK PHP PKR PLN QAR RON "
        "RSD RUB SAR SBD SCR SDG SEK SGD SHP SLE SLL SOS SRD SSP STN SVC SYP "
        "SZL THB TJS TMT TOP TRY TTD TWD TZS UAH USD USN UYU UZS VED VES WST "
        "XCD XCG YER ZAR ZMW ZWG ZWL"
    ),
    3: "BHD IQD JOD KWD LYD OMR TND",
    4: "CLF UYW",
}

_MINOR_UNIT_EXPONENT = {
    code: exponent
    for exponent, codes in _CURRENCIES_BY_EXPONENT.items()
    for code in codes.split()
}


class _Group(NamedTuple):
    amount_minor: int
    business_date: date


_Key = tuple[str, str, str]
_Entry = tuple[_Key, int, date]


def _parse_amount_minor(text: str, currency: str) -> int:
    """Convert processor amount text to integer minor units, without floats."""
    try:
        exponent = _MINOR_UNIT_EXPONENT[currency]
    except KeyError:
        raise ValueError(f"unknown currency: {currency!r}") from None

    stripped = text.strip()
    negative = stripped.startswith("(") and stripped.endswith(")")
    body = stripped[1:-1].strip() if negative else stripped
    if _AMOUNT_RE.fullmatch(body) is None:
        raise ValueError(f"malformed amount: {text!r}")

    whole, _, fraction = body.replace(",", "").partition(".")
    if len(fraction.rstrip("0")) > exponent:
        raise ValueError(f"amount {text!r} exceeds {currency} precision")

    minor = int(whole + fraction[:exponent].ljust(exponent, "0"))
    return -minor if negative else minor


def _parse_event_time(event_time: str) -> datetime:
    # datetime.fromisoformat does not accept a "Z" suffix before Python 3.11.
    text = event_time.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _business_date(event_time: str, holidays: set[date]) -> date:
    local = _parse_event_time(event_time).astimezone(_NEW_YORK)
    day = local.date()
    if local.hour >= _CUTOFF_HOUR:
        day += timedelta(days=1)
    while day.weekday() >= 5 or day in holidays:
        day += timedelta(days=1)
    return day


def _live_lines(settlement_lines: list[dict]) -> Iterator[dict]:
    """Yield only lines from each batch's highest file_seq.

    FEE lines count here: a resend containing only fees still voids every
    lower file_seq of that batch.
    """
    highest: dict[str, int] = {}
    for line in settlement_lines:
        batch_id = line["batch_id"]
        seq = int(line["file_seq"])
        highest[batch_id] = max(seq, highest.get(batch_id, seq))

    for line in settlement_lines:
        if int(line["file_seq"]) == highest[line["batch_id"]]:
            yield line


def _settlement_entries(
    settlement_lines: list[dict], holidays: set[date]
) -> Iterator[_Entry]:
    for line in _live_lines(settlement_lines):
        if line["line_type"] == _FEE:
            continue
        key = (line["psp_ref"], line["line_type"], line["currency"])
        amount = _parse_amount_minor(line["amount"], line["currency"])
        yield key, amount, _business_date(line["event_time"], holidays)


def _ledger_entries(ledger_rows: list[dict]) -> Iterator[_Entry]:
    for row in ledger_rows:
        if row["type"] == _FEE:
            continue
        key = (row["psp_ref"], row["type"], row["currency"])
        yield key, row["amount_minor"], date.fromisoformat(row["business_date"])


def _group(entries: Iterable[_Entry]) -> dict[_Key, _Group]:
    groups: dict[_Key, _Group] = {}
    for key, amount, business_date in entries:
        existing = groups.get(key)
        if existing is None:
            groups[key] = _Group(amount, business_date)
        else:
            groups[key] = _Group(
                existing.amount_minor + amount,
                max(existing.business_date, business_date),
            )
    return groups


def _net_chargebacks(
    settlement: dict[_Key, _Group], ledger: dict[_Key, _Group]
) -> None:
    """Remove offsetting chargeback pairs the ledger never booked, in place."""
    for psp_ref, group_type, currency in list(settlement):
        if group_type != _CHARGEBACK:
            continue
        chargeback = (psp_ref, _CHARGEBACK, currency)
        reversal = (psp_ref, _CHARGEBACK_REVERSAL, currency)
        if reversal not in settlement:
            continue
        if chargeback in ledger or reversal in ledger:
            continue
        net = settlement[chargeback].amount_minor + settlement[reversal].amount_minor
        if net == 0:
            del settlement[chargeback]
            del settlement[reversal]


def _classify(
    settled: _Group | None, booked: _Group | None
) -> tuple[str, int] | None:
    """Return (break, delta_minor) for a group key, or None if it matches."""
    if booked is None:
        return "MISSING_IN_LEDGER", settled.amount_minor
    if settled is None:
        return "MISSING_IN_SETTLEMENT", -booked.amount_minor
    if settled.amount_minor != booked.amount_minor:
        return "AMOUNT_MISMATCH", settled.amount_minor - booked.amount_minor
    if settled.business_date != booked.business_date:
        return "TIMING", 0
    return None


def reconcile(
    ledger_rows: list[dict], settlement_lines: list[dict], holidays: list[str]
) -> list[dict]:
    """Return breaks sorted by psp_ref, then type, then currency."""
    holiday_dates = {date.fromisoformat(holiday) for holiday in holidays}

    settlement = _group(_settlement_entries(settlement_lines, holiday_dates))
    ledger = _group(_ledger_entries(ledger_rows))
    _net_chargebacks(settlement, ledger)

    breaks: list[dict] = []
    for key in sorted(settlement.keys() | ledger.keys()):
        outcome = _classify(settlement.get(key), ledger.get(key))
        if outcome is None:
            continue
        psp_ref, group_type, currency = key
        break_type, delta_minor = outcome
        breaks.append(
            {
                "psp_ref": psp_ref,
                "type": group_type,
                "currency": currency,
                "break": break_type,
                "delta_minor": delta_minor,
            }
        )
    return breaks
```
