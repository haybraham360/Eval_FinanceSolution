# cli-opus / t4_interest_backvalue / trial 1

- Requested: `opus`, resolved: `claude-haiku-5-5,claude-opus-5-5`, provider: claude-cli
- Run at 2026-10-31T15:28:15+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t4_interest_backvalue/prompt.md`.

## Model output

```python
"""Monthly savings interest capitalisation with back-valued postings.

All arithmetic is exact. Each day's interest is an integer numerator over one
common denominator (``scale``), so no daily amount is ever rounded. Rounding
happens only at month-ends, using ROUND_HALF_EVEN via ``Fraction.__round__``.
"""

from __future__ import annotations

from bisect import bisect_right
from calendar import isleap, monthrange
from datetime import date, timedelta
from fractions import Fraction
from math import lcm
from typing import NamedTuple

TIER1_LIMIT_MINOR = 1_000_000
_ONE_DAY = timedelta(days=1)


class _Day(NamedTuple):
    """A calendar day and its daily rates expressed as numerators over scale."""

    day: date
    tier1_weight: int
    tier2_weight: int
    is_month_end: bool


def _is_month_end(day: date) -> bool:
    return day.day == monthrange(day.year, day.month)[1]


def _month_ends(start: date, end: date) -> list[date]:
    """Return every calendar month-end M with start <= M <= end, oldest first."""
    result: list[date] = []
    year, month = start.year, start.month
    while True:
        month_end = date(year, month, monthrange(year, month)[1])
        if month_end > end:
            return result
        result.append(month_end)
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)


def _build_days(
    start: date, last: date, rates: list[dict]
) -> tuple[list[_Day], int]:
    """Build the daily rate calendar and its common denominator.

    For each day, tier1_weight / scale equals tier1 / day_basis exactly, and
    likewise for tier 2. day_basis is 366 in a leap year and 365 otherwise.
    """
    if not rates:
        raise ValueError("rates must not be empty")

    effective_from = [date.fromisoformat(rate["from"]) for rate in rates]
    if effective_from[0] > start:
        raise ValueError("first rate must apply on or before start")

    tier1_rates = [Fraction(rate["tier1"]) for rate in rates]
    tier2_rates = [Fraction(rate["tier2"]) for rate in rates]

    rate_denominator = lcm(
        *(rate.denominator for rate in tier1_rates + tier2_rates)
    )
    scale = rate_denominator * 365 * 366

    days: list[_Day] = []
    current = start
    while current <= last:
        basis = 366 if isleap(current.year) else 365
        scale_per_basis = Fraction(scale, basis)
        index = bisect_right(effective_from, current) - 1
        # Both products are whole numbers because scale contains every rate
        # denominator and both day-count bases.
        days.append(
            _Day(
                day=current,
                tier1_weight=(tier1_rates[index] * scale_per_basis).numerator,
                tier2_weight=(tier2_rates[index] * scale_per_basis).numerator,
                is_month_end=_is_month_end(current),
            )
        )
        current += _ONE_DAY
    return days, scale


def _rounded_cumulative_interest(
    month_end: date,
    opening_minor: int,
    known_by_value_date: dict[date, int],
    days: list[_Day],
    scale: int,
) -> int:
    """Replay the corrected history through month_end and return R(E(month_end)).

    The history is rebuilt from start using only the known transactions. Its
    own capitalisations feed the balance from the day after each month-end.
    """
    balance = opening_minor
    exact_numerator = 0  # E(d) = exact_numerator / scale
    rounded_cumulative = 0  # R(E(p)) for the latest month-end p

    for entry in days:
        if entry.day > month_end:
            break

        balance += known_by_value_date.get(entry.day, 0)

        if balance > 0:
            tier1_part = min(balance, TIER1_LIMIT_MINOR)
            tier2_part = balance - tier1_part
            exact_numerator += (
                tier1_part * entry.tier1_weight
                + tier2_part * entry.tier2_weight
            )

        if entry.is_month_end:
            new_rounded = round(Fraction(exact_numerator, scale))
            # Applied after the day's accrual, so it earns from the next day.
            balance += new_rounded - rounded_cumulative
            rounded_cumulative = new_rounded

    return rounded_cumulative


def capitalisations(
    opening_minor: int,
    start: str,
    end: str,
    transactions: list[dict],
    rates: list[dict],
) -> list[dict]:
    """Return the interest actually posted at each month-end in the period."""
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)

    month_ends = _month_ends(start_date, end_date)
    if not month_ends:
        return []

    parsed_transactions: list[tuple[date, date, int]] = []
    for transaction in transactions:
        value_date = date.fromisoformat(transaction["value_date"])
        post_date = date.fromisoformat(transaction["post_date"])
        if value_date < start_date:
            raise ValueError("value_date must not be before start")
        if post_date < value_date:
            raise ValueError("post_date must not be before value_date")
        parsed_transactions.append(
            (post_date, value_date, transaction["amount_minor"])
        )
    parsed_transactions.sort(key=lambda item: item[0])

    days, scale = _build_days(start_date, month_ends[-1], rates)

    known_by_value_date: dict[date, int] = {}
    next_transaction = 0
    posted_total = 0
    postings: list[dict] = []

    for month_end in month_ends:
        while (
            next_transaction < len(parsed_transactions)
            and parsed_transactions[next_transaction][0] <= month_end
        ):
            _, value_date, amount_minor = parsed_transactions[next_transaction]
            known_by_value_date[value_date] = (
                known_by_value_date.get(value_date, 0) + amount_minor
            )
            next_transaction += 1

        rounded_cumulative = _rounded_cumulative_interest(
            month_end, opening_minor, known_by_value_date, days, scale
        )
        amount_minor = rounded_cumulative - posted_total
        posted_total += amount_minor
        postings.append(
            {"date": month_end.isoformat(), "amount_minor": amount_minor}
        )

    return postings
```
