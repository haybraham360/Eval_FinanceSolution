# cli-haiku / t4_interest_backvalue / trial 1

- Requested: `haiku`, resolved: `claude-haiku-5-5`, provider: claude-cli
- Run at 2026-10-31T20:50:47+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t4_interest_backvalue/prompt.md`.

## Model output

```python
from __future__ import annotations

import bisect
import calendar
import operator
from datetime import date, datetime, timedelta
from fractions import Fraction

_TIER_BREAK = 1_000_000
_ONE_DAY = timedelta(days=1)


def _to_date(v) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        return date.fromisoformat(v)
    raise TypeError(f"expected date or ISO date string, got {type(v).__name__}")


def _to_fraction(v) -> Fraction:
    if isinstance(v, float):
        raise TypeError("float rates are not allowed; use decimal strings")
    return Fraction(v)


def _round_half_even(x: Fraction) -> int:
    """Round a Fraction to the nearest integer, ties to even."""
    q, r = divmod(x.numerator, x.denominator)  # floor division
    twice = 2 * r
    if twice > x.denominator or (twice == x.denominator and q % 2 == 1):
        q += 1
    return q


def _is_month_end(d: date) -> bool:
    return d.day == calendar.monthrange(d.year, d.month)[1]


def _month_ends(start: date, end: date) -> list[date]:
    """Calendar month-ends M with start <= M <= end, oldest first."""
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


def _day_fraction(s: date, e: date) -> Fraction:
    """Exact sum over days d in [s, e) of 1/365, or 1/366 when d is in a leap year."""
    total = Fraction(0)
    last = e - _ONE_DAY
    for y in range(s.year, last.year + 1):
        ys = max(s, date(y, 1, 1))
        ye = min(e, date(y + 1, 1, 1))
        n = (ye - ys).days
        if n > 0:
            total += Fraction(n, 366 if calendar.isleap(y) else 365)
    return total


def _accrue_through(
    opening: int,
    start: date,
    M: date,
    txns: list[tuple[date, date, int]],
    rate_from: list[date],
    rate_t1: list[Fraction],
    rate_t2: list[Fraction],
) -> Fraction:
    """
    Corrected history through M, using only transactions with post_date <= M.
    Returns the exact cumulative interest E(M) from start through M.
    Capitalisations at each earlier month-end m are R(E(m)) - R(E(p)) and
    feed the balance from m+1 onward.
    """
    known = [(vd, amt) for vd, pd, amt in txns if pd <= M]

    bal = opening
    deltas: dict[date, int] = {}
    for vd, amt in known:
        if vd <= start:
            bal += amt
        else:
            deltas[vd] = deltas.get(vd, 0) + amt

    # Segment boundaries: balance or rate can only change at these dates.
    breakpoints = {start}
    breakpoints.update(vd for vd in deltas if vd <= M)
    breakpoints.update(r for r in rate_from if start < r <= M)
    for m in _month_ends(start, M):
        if m < M:
            breakpoints.add(m + _ONE_DAY)  # capitalisation at m applies from m+1

    starts = sorted(breakpoints)
    cum = Fraction(0)
    prev_r = 0  # R(E(p)); zero before the first month-end

    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else M + _ONE_DAY
        if s > start:
            bal += deltas.get(s, 0)

        idx = bisect.bisect_right(rate_from, s) - 1
        t1, t2 = rate_t1[idx], rate_t2[idx]

        if bal > 0:
            tier1_part = min(bal, _TIER_BREAK)
            tier2_part = max(bal - _TIER_BREAK, 0)
            annual = tier1_part * t1 + tier2_part * t2
            cum += annual * _day_fraction(s, e)

        last = e - _ONE_DAY
        if last < M and _is_month_end(last):
            r = _round_half_even(cum)
            bal += r - prev_r
            prev_r = r

    return cum


def capitalisations(
    opening_minor: int,
    start: str,
    end: str,
    transactions: list[dict],
    rates: list[dict],
) -> list[dict]:
    import operator as _op  # local alias kept explicit for clarity

    opening = operator.index(opening_minor)
    start_d = _to_date(start)
    end_d = _to_date(end)

    txns: list[tuple[date, date, int]] = []
    for t in transactions:
        vd = _to_date(t["value_date"])
        pd = _to_date(t["post_date"])
        amt = operator.index(t["amount_minor"])
        txns.append((vd, pd, amt))

    rate_rows = sorted(
        (
            (_to_date(r["from"]), _to_fraction(r["tier1"]), _to_fraction(r["tier2"]))
            for r in rates
        ),
        key=lambda row: row[0],
    )
    if not rate_rows:
        raise ValueError("at least one rate entry is required")
    rate_from = [row[0] for row in rate_rows]
    rate_t1 = [row[1] for row in rate_rows]
    rate_t2 = [row[2] for row in rate_rows]
    if rate_from[0] > start_d:
        raise ValueError("first rate entry must be on or before start")

    results: list[dict] = []
    posted_cum = 0  # total actually posted so far

    for M in _month_ends(start_d, end_d):
        cum = _accrue_through(opening, start_d, M, txns, rate_from, rate_t1, rate_t2)
        target = _round_half_even(cum)  # R(E(M)) in the history known at M
        results.append({"date": M.isoformat(), "amount_minor": target - posted_cum})
        posted_cum = target

    return results
```
