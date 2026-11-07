# Plain-language explanations of selected checks

These short explanations let the Ledger-Eval Explorer show some database mistakes to non-specialists. Each one describes the behaviour behind a check's expected answer. They are not graded: the graders compare answers only with the reference files.

Each answer was confirmed on a live PostgreSQL 14.18 server on 6 November 2026. E14 and E15 were checked by running the expression directly. All of t8, t9 and t10 were checked with `verify_scenarios.py`, which reported t8 19/19, t9 17/17 and t10 58/58 matching the reference answers.

The Explorer reads the tables below. A table row whose first cell lists check ids belongs to the task named in the heading above it. Ranges such as `E14-E15` are allowed.

# Explanations for t10

Reference answers: `reference/t10_pg_money_time.json`

| Items | Topic | Explanation |
|---|---|---|
| E14 | Exact decimal arithmetic | PostgreSQL treats 1.0 as an exact decimal, not a floating-point number, so 1.0 / 3 comes out to 20 decimal places: 0.33333333333333333333. Floating-point maths would give about 16 digits. Money code that assumes floating-point behaviour will round differently from the database. |
| E15 | Exact decimal arithmetic | In exact decimal arithmetic a third is cut off after 20 decimal places, so a third multiplied by 3 is 0.99999999999999999999, not 1. An answer of 1, or a shorter number such as 0.9999999999999999, does not match how PostgreSQL's exact decimals work. |

# Explanations for t8

Reference answers: `reference/t8_pg_locks.json`

| Items | Topic | Explanation |
|---|---|---|
| L4 | A waiting update re-checks its condition | Two sessions tried to take 80 from a balance of 100 at the same time, and the second had to wait. When the first finished, the balance was 20. The waiting update then checked its condition again ("balance at least 80"), found it no longer true, and changed nothing, so its audit trigger never ran either. That makes 3 audit rows, not 4. |

# Explanations for t9

Reference answers: `reference/t9_pg_isolation.json`

| Items | Topic | Explanation |
|---|---|---|
| I3 | When a transaction takes its snapshot | A transaction at the REPEATABLE READ level freezes its view of the data at its first query, not when it begins and not when it locks a table. Here it waited on a lock until another session had changed the balance from 100 to 7 and committed, so its first query saw 7. |
