# cli-sonnet / t4_interest_backvalue / trial 1

- Requested: `sonnet`, resolved: `claude-haiku-5-5,claude-sonnet-5-5`, provider: claude-cli
- Run at 2026-10-31T20:36:26+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t4_interest_backvalue/prompt.md`.

## Model output

```python
from __future__ import annotations

import calendar
from bisect import bisect_right
from datetime import date, datetime, timedelta
from fractions import Fraction

_TIER_LIMIT = 1_000_000


def _to_date(x) -> date:
    if isinstance(x, datetime):
        return x.date()
    if isinstance(x, date):
        return x
    return date.fromisoformat(str(x))


def _round_half_even(f: Fraction) -> int:
    """Exact ROUND_HALF_EVEN of a Fraction to an integer."""
    q, r = divmod(f.numerator, f.denominator)  # floor division, 0 <= r < den
    twice = 2 * r
    if twice > f.denominator:
        return q + 1
    if twice == f.denominator:
        return q + 1 if q % 2 else q
    return q


def _month_ends(start: date, end: date) -> list[date]:
    out = []
    y, m = start.year, start.month
    while True:
        last = date(y, m, calendar.monthrange(y, m)[1])
        if last > end:
            break
        if last >= start:
            out.append(last)
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def capitalisations(opening_minor: int, start: str, end: str,
                    transactions: list[dict], rates: list[dict]) -> list[dict]:
    start_d = _to_date(start)
    end_d = _to_date(end)
    if end_d < start_d:
        return []

    # Rates: exact Fractions, never floats.
    rate_from = [_to_date(r["from"]) for r in rates]
    rate_vals = [(Fraction(str(r["tier1"])), Fraction(str(r["tier2"]))) for r in rates]

    txns = [(_to_date(t["value_date"]), _to_date(t["post_date"]), int(t["amount_minor"]))
            for t in transactions]

    month_ends = _month_ends(start_d, end_d)
    month_end_set = set(month_ends)

    def rates_on(d: date) -> tuple[Fraction, Fraction]:
        i = bisect_right(rate_from, d) - 1
        if i < 0:
            i = 0  # contract says this cannot happen; be defensive
        return rate_vals[i]

    def corrected_total(M: date) -> int:
        """R(E(M)) in the corrected history using transactions with post_date <= M."""
        delta: dict[date, int] = {}
        for vd, pd, amt in txns:
            if pd <= M and vd <= M:
                key = vd if vd > start_d else start_d
                delta[key] = delta.get(key, 0) + amt

        bal = opening_minor
        exact = Fraction(0)
        prev_rounded = 0
        d = start_d
        one = timedelta(days=1)
        while d <= M:
            bal += delta.get(d, 0)
            if bal > 0:
                t1, t2 = rates_on(d)
                b1 = bal if bal < _TIER_LIMIT else _TIER_LIMIT
                b2 = bal - _TIER_LIMIT if bal > _TIER_LIMIT else 0
                days = 366 if calendar.isleap(d.year) else 365
                exact += (b1 * t1 + b2 * t2) / days
            if d in month_end_set:
                rounded = _round_half_even(exact)
                cap = rounded - prev_rounded
                prev_rounded = rounded
                bal += cap  # earns from the following day
                if d == M:
                    return rounded
            d += one
        return _round_half_even(exact)

    result = []
    posted_total = 0
    for M in month_ends:
        target = corrected_total(M)
        amount = target - posted_total
        result.append({"date": M.isoformat(), "amount_minor": amount})
        posted_total += amount
    return result
```
