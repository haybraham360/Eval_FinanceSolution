# Ticket: savings interest capitalisation with back-valued postings

Write the monthly interest run for a savings account. Regulators can ask us to prove any month's posting, so the rules below are exact.

Implement in one Python 3.10+ module, standard library only:

```python
def capitalisations(opening_minor: int, start: str, end: str, transactions: list[dict], rates: list[dict]) -> list[dict]: ...
```

- `opening_minor`: the balance at the close of the day before `start`.
- `start`, `end`: inclusive `YYYY-MM-DD` dates. Accrual begins on `start`.
- `transactions`: `{"value_date": date, "post_date": date, "amount_minor": int}`, in no particular order. `value_date` is never before `start`, and `post_date` is never before `value_date`. Deposits are positive and withdrawals negative.
- `rates`: `{"from": date, "tier1": "<decimal>", "tier2": "<decimal>"}`, sorted by `from`, where the first `from` is on or before `start`. Each entry applies from its `from` date inclusive until the next entry. Rates are annual fractions, for example `"0.0200"` is 2%.

Return one `{"date": "YYYY-MM-DD", "amount_minor": int}` for every calendar month-end `M` with `start <= M <= end`, oldest first, including months where the amount is 0 or negative. If `end` is not a month-end, the partial month produces no row.

## Daily accrual

For each calendar day `d`, take the account's closing value-dated balance `B(d)`, which is:

`opening_minor` + every transaction with `value_date <= d` + every interest capitalisation with date `< d`

So capitalised interest starts earning on the day after it is capitalised, and a transaction earns from its value date.

Interest for day `d` uses marginal tiers: the first 1,000,000 minor units of the balance earn `tier1`, and only the part above 1,000,000 earns `tier2`, at the rates in force on `d`. A balance at or below zero earns nothing.

Day count is ACT/ACT ISDA: the day's interest is `annual interest / 365`, or `/ 366` if `d` falls in a leap year.

Daily interest is exact and is never rounded.

## Month-end posting, including back-valued transactions

A transaction with a `post_date` later than a month-end `M` is not yet known at `M`, even if its `value_date` is before `M`. At each month-end `M`, the run knows exactly the transactions with `post_date <= M`.

At month-end `M`:

1. Build the **corrected history**: recompute from `start` through `M` as if all transactions known at `M` had always been known, including what the capitalisations at every earlier month-end would have been in that history. Within the corrected history, the capitalisation at month-end `m` is `R(E(m)) - R(E(p))`, where `E(x)` is the exact cumulative interest accrued from `start` through `x` in the corrected history, `p` is the previous month-end (with `R(E(p)) = 0` for the first), and `R` rounds to a whole minor unit, ROUND_HALF_EVEN. These corrected capitalisations feed `B(d)` inside the corrected history.
2. The amount actually posted on `M` is `R(E(M))` minus the total of everything actually posted at earlier month-ends.

Earlier postings are never edited. A correction appears only as part of a later month's amount, which can be negative. Floats are not acceptable: results must be exact.

Return the complete module in one ```python block.
