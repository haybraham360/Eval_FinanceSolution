# cli-haiku / t4_interest_backvalue / trial 1

- Requested: `haiku`, resolved: `claude-haiku-5-5`, provider: claude-cli
- Run at 2026-10-31T14:45:10+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t4_interest_backvalue/prompt.md`.

## Model output

```python
"""Monthly savings interest capitalisation with back-valued postings.

All money and rate arithmetic is exact (fractions.Fraction built from
decimal.Decimal). Floats are never used. The only rounding is R(E(M)) for
cumulative interest, to a whole minor unit, ROUND_HALF_EVEN.
"""

from __future__ import annotations

import calendar
from bisect import bisect_right
from datetime import date, datetime, timedelta
from decimal import Decimal
from fractions import Fraction
from typing import Any

_TIER_BOUNDARY = 1_000_000


def _to_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise TypeError(f"expected date or 'YYYY-MM-DD' string, got {type(value).__name__}")


def _to_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"expected int minor units, got {type(value).__name__}")
    return value


def _to_fraction(value: Any) -> Fraction:
    if isinstance(value, bool):
        raise TypeError("expected decimal rate, got bool")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, (str, Decimal)):
        return Fraction(Decimal(value))
    raise TypeError(f"expected decimal string for rate, got {type(value).__name__}")


def _prepare_rates(rates: list[dict]) -> list[tuple[date, Fraction, Fraction]]:
    entries = [
        (_to_date(r["from"]), _to_fraction(r["tier1"]), _to_fraction(r["tier2"]))
        for r in rates
    ]
    entries.sort(key=lambda e: e[0])  # stable; later duplicate 'from' wins
    return entries


def _month_ends(start: date, end: date) -> list[date]:
    out: list[date] = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        last = date(y, m, calendar.monthrange(y, m)[1])
        if start <= last <= end:
            out.append(last)
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def _corrected_rounded_cumulative(
    opening: int,
    start: date,
    month_end: date,
    known: list[tuple[date, int]],
    rate_froms: list[date],
    rate_entries: list[tuple[date, Fraction, Fraction]],
) -> int:
    """Return R(E(month_end)) in the corrected history built from `known`.

    `known` holds (value_date, amount_minor) for every transaction with
    post_date <= month_end. Capitalisation at each earlier month-end m is
    R(E(m)) - R(E(previous month-end)) within this same history.
    """
    running = opening
    by_value_date: dict[date, int] = {}
    for vdate, amount in known:
        if vdate < start:
            running += amount
        else:
            by_value_date[vdate] = by_value_date.get(vdate, 0) + amount

    cum_interest = Fraction(0)  # E(d): exact cumulative interest from start
    cap_total = 0               # sum of capitalisations dated < d
    prev_rounded = 0            # R(E(previous month-end))
    one_day = timedelta(days=1)
    d = start

    while True:
        # Transactions with value_date <= d are included in B(d).
        running += by_value_date.get(d, 0)
        balance = running + cap_total

        if balance > 0:
            idx = bisect_right(rate_froms, d) - 1
            _, tier1_rate, tier2_rate = rate_entries[idx]
            tier1_amt = min(balance, _TIER_BOUNDARY)
            tier2_amt = max(balance - _TIER_BOUNDARY, 0)
            annual = tier1_amt * tier1_rate + tier2_amt * tier2_rate
            days_in_year = 366 if calendar.isleap(d.year) else 365
            cum_interest += annual / days_in_year

        last_day = calendar.monthrange(d.year, d.month)[1]
        if d.day == last_day:
            rounded = round(cum_interest)  # Fraction rounding is ROUND_HALF_EVEN
            if d == month_end:
                return rounded
            cap_total += rounded - prev_rounded
            prev_rounded = rounded

        d += one_day


def capitalisations(
    opening_minor: int,
    start: str,
    end: str,
    transactions: list[dict],
    rates: list[dict],
) -> list[dict]:
    opening = _to_int(opening_minor)
    start_d = _to_date(start)
    end_d = _to_date(end)
    if end_d < start_d:
        return []

    txns = [
        (_to_date(t["value_date"]), _to_date(t["post_date"]), _to_int(t["amount_minor"]))
        for t in transactions
    ]

    entries = _prepare_rates(rates)
    if not entries or entries[0][0] > start_d:
        raise ValueError("no rate in force on start date")
    rate_froms = [e[0] for e in entries]

    rows: list[dict] = []
    posted_total = 0  # total of everything actually posted at earlier month-ends

    for month_end in _month_ends(start_d, end_d):
        known = [(vdate, amount) for vdate, pdate, amount in txns if pdate <= month_end]
        target = _corrected_rounded_cumulative(
            opening, start_d, month_end, known, rate_froms, entries
        )
        amount_posted = target - posted_total
        posted_total += amount_posted
        rows.append({"date": month_end.isoformat(), "amount_minor": amount_posted})

    return rows
```
