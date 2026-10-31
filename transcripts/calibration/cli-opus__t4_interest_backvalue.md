# cli-opus / t4_interest_backvalue / trial 1

- Requested: `opus`, resolved: `claude-haiku-5-5,claude-opus-5-5`, provider: claude-cli
- Run at 2026-10-31T14:40:26+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t4_interest_backvalue/prompt.md`.

## Model output

```python
"""Monthly savings interest capitalisation with back-valued postings.

All interest arithmetic uses exact rationals (fractions.Fraction); floats are
never used. Each month-end's history is replayed in full from `start`, so any
posting can be reproduced from the transactions known on that date.
"""

from bisect import bisect_right
from calendar import isleap, monthrange
from datetime import date, timedelta
from fractions import Fraction

TIER1_LIMIT_MINOR = 1_000_000


def _parse_date(value) -> date:
    """Return a date from a YYYY-MM-DD string or an existing date."""
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _month_ends(start: date, end: date) -> list[date]:
    """Return every calendar month-end M with start <= M <= end, oldest first."""
    result = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        month_end = date(year, month, monthrange(year, month)[1])
        if month_end <= end:
            result.append(month_end)
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return result


def _daily_schedule(
    start: date, last_day: date, rates: list[dict]
) -> list[tuple[date, Fraction, Fraction, int]]:
    """Return (day, tier1 rate, tier2 rate, day-count basis) for each day."""
    rate_dates = [_parse_date(rate["from"]) for rate in rates]
    rate_values = [
        (Fraction(rate["tier1"]), Fraction(rate["tier2"])) for rate in rates
    ]

    schedule = []
    day = start
    while True:
        tier1, tier2 = rate_values[bisect_right(rate_dates, day) - 1]
        basis = 366 if isleap(day.year) else 365
        schedule.append((day, tier1, tier2, basis))
        if day == last_day:
            return schedule
        day += timedelta(days=1)


def _daily_interest(
    balance: int, tier1: Fraction, tier2: Fraction, basis: int
) -> Fraction:
    """Return one day's exact interest using marginal tiers."""
    if balance <= 0:
        return Fraction(0)
    tier1_balance = min(balance, TIER1_LIMIT_MINOR)
    tier2_balance = balance - tier1_balance
    return (tier1_balance * tier1 + tier2_balance * tier2) / basis


def _corrected_cumulative_interest(
    opening_minor: int,
    through: date,
    known: list[tuple[date, int]],
    schedule: list[tuple[date, Fraction, Fraction, int]],
    month_end_dates: set[date],
) -> Fraction:
    """Return E(through) in the corrected history for the known transactions.

    Corrected capitalisations are applied after the month-end day's accrual,
    so they first affect B(d) on the following day. They are independent of
    the amounts actually posted.
    """
    movements: dict[date, int] = {}
    for value_date, amount_minor in known:
        movements[value_date] = movements.get(value_date, 0) + amount_minor

    balance = opening_minor
    exact_interest = Fraction(0)
    rounded_at_previous_month_end = 0

    for day, tier1, tier2, basis in schedule:
        if day > through:
            break

        balance += movements.get(day, 0)
        exact_interest += _daily_interest(balance, tier1, tier2, basis)

        if day in month_end_dates:
            # round() on a Fraction is exact and uses ROUND_HALF_EVEN.
            rounded = round(exact_interest)
            balance += rounded - rounded_at_previous_month_end
            rounded_at_previous_month_end = rounded

    return exact_interest


def capitalisations(
    opening_minor: int,
    start: str,
    end: str,
    transactions: list[dict],
    rates: list[dict],
) -> list[dict]:
    """Return the amount actually posted at each month-end in [start, end]."""
    start_date = _parse_date(start)
    end_date = _parse_date(end)

    month_ends = _month_ends(start_date, end_date)
    if not month_ends:
        return []

    parsed_transactions = [
        (
            _parse_date(transaction["value_date"]),
            _parse_date(transaction["post_date"]),
            transaction["amount_minor"],
        )
        for transaction in transactions
    ]
    schedule = _daily_schedule(start_date, month_ends[-1], rates)
    month_end_dates = set(month_ends)

    rows = []
    total_posted = 0

    for month_end in month_ends:
        known = [
            (value_date, amount_minor)
            for value_date, post_date, amount_minor in parsed_transactions
            if post_date <= month_end
        ]
        exact_interest = _corrected_cumulative_interest(
            opening_minor, month_end, known, schedule, month_end_dates
        )
        amount_minor = round(exact_interest) - total_posted
        total_posted += amount_minor
        rows.append(
            {"date": month_end.isoformat(), "amount_minor": amount_minor}
        )

    return rows
```
