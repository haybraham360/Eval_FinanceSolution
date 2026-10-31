# cli-sonnet / t4_interest_backvalue / trial 1

- Requested: `sonnet`, resolved: `claude-haiku-5-5,claude-sonnet-5-5`, provider: claude-cli
- Run at 2026-10-31T14:43:01+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t4_interest_backvalue/prompt.md`.

## Model output

```python
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from fractions import Fraction
from bisect import bisect_right

TIER1_LIMIT = 1_000_000


def _to_date(x) -> date:
    if isinstance(x, datetime):
        return x.date()
    if isinstance(x, date):
        return x
    return date.fromisoformat(str(x))


def _is_leap(y: int) -> bool:
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def _is_month_end(d: date) -> bool:
    return (d + timedelta(days=1)).day == 1


def _round_half_even(q: Fraction) -> int:
    """Exact ROUND_HALF_EVEN of a Fraction to an int."""
    n, den = q.numerator, q.denominator  # den > 0
    whole, rem = divmod(n, den)          # floor division, 0 <= rem < den
    twice = rem * 2
    if twice > den:
        return whole + 1
    if twice < den:
        return whole
    return whole if whole % 2 == 0 else whole + 1


def capitalisations(opening_minor: int, start: str, end: str,
                    transactions: list[dict], rates: list[dict]) -> list[dict]:
    s = _to_date(start)
    e = _to_date(end)
    if s > e:
        return []

    # Calendar days from start through end.
    ndays = (e - s).days + 1
    days = [s + timedelta(days=i) for i in range(ndays)]

    # Rate schedule (exact), looked up per day, pre-divided by the day count.
    rate_rows = sorted(
        ((_to_date(r["from"]),
          Fraction(Decimal(str(r["tier1"]))),
          Fraction(Decimal(str(r["tier2"])))) for r in rates),
        key=lambda t: t[0],
    )
    froms = [r[0] for r in rate_rows]
    day_rates = []  # (tier1/denominator, tier2/denominator) per day
    for d in days:
        idx = bisect_right(froms, d) - 1
        if idx < 0:
            idx = 0  # spec guarantees first 'from' <= start
        _, r1, r2 = rate_rows[idx]
        den = 366 if _is_leap(d.year) else 365
        day_rates.append((r1 / den, r2 / den))

    # Normalise transactions.
    txns = []
    for t in transactions:
        vd = max(_to_date(t["value_date"]), s)  # value before start counts from day 0
        pd = _to_date(t["post_date"])
        txns.append((vd, pd, int(t["amount_minor"])))

    month_end_idx = [i for i, d in enumerate(days) if _is_month_end(d)]

    results = []
    total_posted = 0

    for m_idx in month_end_idx:
        # Transactions known at M, bucketed by value-date index (only those within history).
        m_date = days[m_idx]
        delta = {}
        for vd, pd, amt in txns:
            if pd <= m_date:
                i = (vd - s).days
                if i <= m_idx:
                    delta[i] = delta.get(i, 0) + amt

        # Corrected history from start through M.
        cum_exact = Fraction(0)
        txn_cum = 0
        cap_total = 0  # sum of corrected capitalisations so far == R(E(last month-end))
        for i in range(m_idx + 1):
            txn_cum += delta.get(i, 0)
            bal = opening_minor + txn_cum + cap_total
            if bal > 0:
                t1, t2 = day_rates[i]
                low = bal if bal < TIER1_LIMIT else TIER1_LIMIT
                high = bal - TIER1_LIMIT if bal > TIER1_LIMIT else 0
                cum_exact += low * t1 + high * t2
            if i != m_idx and _is_month_end(days[i]):
                # Capitalisations telescope: sum equals R(E(m)).
                cap_total = _round_half_even(cum_exact)

        amount = _round_half_even(cum_exact) - total_posted
        total_posted += amount
        results.append({"date": m_date.isoformat(), "amount_minor": amount})

    return results
```
