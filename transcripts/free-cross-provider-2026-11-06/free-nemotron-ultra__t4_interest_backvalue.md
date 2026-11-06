# free-nemotron-ultra / t4_interest_backvalue / trial 1

- Requested: `nvidia/nemotron-3-ultra-550b-a55b:free`, resolved: `nvidia/nemotron-3-ultra-550b-a55b:free`, provider: Nvidia
- Run at 2026-11-06T20:11:17+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t4_interest_backvalue/prompt.md`.

## Model output

```python
from datetime import date, timedelta
from fractions import Fraction
from decimal import Decimal
import calendar
from collections import defaultdict
from typing import List, Dict, Any

def capitalisations(opening_minor: int, start: str, end: str, transactions: List[Dict[str, Any]], rates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Compute monthly interest capitalisations for a savings account with back-valued transactions.

    Args:
        opening_minor: Balance at close of day before `start` (in minor units).
        start: Inclusive start date (YYYY-MM-DD). Accrual begins on this day.
        end: Inclusive end date (YYYY-MM-DD). Only month-ends <= end are returned.
        transactions: List of {"value_date": "YYYY-MM-DD", "post_date": "YYYY-MM-DD", "amount_minor": int}.
        rates: List of {"from": "YYYY-MM-DD", "tier1": "<decimal>", "tier2": "<decimal>"}, sorted by "from".

    Returns:
        List of {"date": "YYYY-MM-DD", "amount_minor": int} for each calendar month-end M with start <= M <= end.
    """
    # ---------- Helpers ----------
    def round_half_even(frac: Fraction) -> int:
        """Round a non-negative Fraction to nearest integer, ties to even."""
        n = frac.numerator // frac.denominator
        rem = frac.numerator % frac.denominator
        two_rem = rem * 2
        if two_rem < frac.denominator:
            return n
        elif two_rem > frac.denominator:
            return n + 1
        else:  # exactly half
            return n if n % 2 == 0 else n + 1

    def is_leap_year(y: int) -> bool:
        return (y % 4 == 0) and (y % 100 != 0 or y % 400 == 0)

    def month_ends_between(start_dt: date, end_dt: date) -> List[date]:
        """All month-end dates M with start_dt <= M <= end_dt."""
        res = []
        y, m = start_dt.year, start_dt.month
        while True:
            last_day = calendar.monthrange(y, m)[1]
            me = date(y, m, last_day)
            if me > end_dt:
                break
            if me >= start_dt:
                res.append(me)
            m += 1
            if m > 12:
                m = 1
                y += 1
        return res

    def simulate(
        start_dt: date,
        end_dt: date,
        opening_bal: int,
        trans_by_date: Dict[date, int],
        rates_parsed: List[tuple],
        month_ends_list: List[date]
    ) -> int:
        """
        Run daily accrual from start_dt to end_dt (inclusive) using the given transactions
        and the list of month-ends (which includes end_dt). Returns R(E(end_dt)).
        """
        balance = opening_bal
        exact_cumulative = Fraction(0, 1)
        prev_rounded = 0  # R(E(previous month-end))

        # rate index
        rate_idx = 0
        while rate_idx + 1 < len(rates_parsed) and rates_parsed[rate_idx + 1][0] <= start_dt:
            rate_idx += 1

        me_idx = 0
        next_me = month_ends_list[me_idx] if month_ends_list else None
        current = start_dt

        while current <= end_dt:
            # 1. Apply transactions valued today
            if current in trans_by_date:
                balance += trans_by_date[current]

            # 2. Update rate if a new rate period starts today
            while rate_idx + 1 < len(rates_parsed) and rates_parsed[rate_idx + 1][0] <= current:
                rate_idx += 1
            tier1, tier2 = rates_parsed[rate_idx][1], rates_parsed[rate_idx][2]

            # 3. Accrue daily interest on closing balance B(current)
            if balance > 0:
                tier1_amt = balance if balance <= 1_000_000 else 1_000_000
                tier2_amt = balance - tier1_amt
                annual_interest = tier1_amt * tier1 + tier2_amt * tier2
                day_count = 366 if is_leap_year(current.year) else 365
                daily_interest = annual_interest / day_count
                exact_cumulative += daily_interest

            # 4. Month-end processing
            if next_me is not None and current == next_me:
                rounded_cumulative = round_half_even(exact_cumulative)
                capitalisation = rounded_cumulative - prev_rounded
                prev_rounded = rounded_cumulative
                # Capitalisation dated today feeds B(d) for d > today
                if current < end_dt:
                    balance += capitalisation

                me_idx += 1
                if me_idx < len(month_ends_list):
                    next_me = month_ends_list[me_idx]
                else:
                    next_me = None

            current += timedelta(days=1)

        return prev_rounded  # this is R(E(end_dt))

    # ---------- Parse inputs ----------
    start_dt = date.fromisoformat(start)
    end_dt = date.fromisoformat(end)

    parsed_transactions = []
    for t in transactions:
        parsed_transactions.append({
            "value_date": date.fromisoformat(t["value_date"]),
            "post_date": date.fromisoformat(t["post_date"]),
            "amount_minor": t["amount_minor"]
        })

    parsed_rates = []
    for r in rates:
        from_dt = date.fromisoformat(r["from"])
        tier1 = Fraction(Decimal(r["tier1"]))
        tier2 = Fraction(Decimal(r["tier2"]))
        parsed_rates.append((from_dt, tier1, tier2))

    # ---------- Main loop over month-ends ----------
    all_month_ends = month_ends_between(start_dt, end_dt)
    if not all_month_ends:
        return []

    total_actual_posted = 0
    results = []

    for M in all_month_ends:
        # Transactions known at this month-end
        known = [t for t in parsed_transactions if t["post_date"] <= M]
        trans_by_date = defaultdict(int)
        for t in known:
            trans_by_date[t["value_date"]] += t["amount_minor"]

        # Month-ends up to and including M
        month_ends_up_to_M = [me for me in all_month_ends if me <= M]

        # Run corrected history simulation
        rounded_E_M = simulate(start_dt, M, opening_minor, trans_by_date, parsed_rates, month_ends_up_to_M)

        # Actual posting = R(E(M)) - sum of earlier actual postings
        actual_posted = rounded_E_M - total_actual_posted
        total_actual_posted += actual_posted

        results.append({"date": M.isoformat(), "amount_minor": actual_posted})

    return results
```
