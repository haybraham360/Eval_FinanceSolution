# free-nemotron-ultra / t7_pg_concurrency / trial 1

- Requested: `nvidia/nemotron-3-ultra-550b-a55b:free`, resolved: `nvidia/nemotron-3-ultra-550b-a55b:free`, provider: Nvidia
- Run at 2026-11-06T20:22:34+00:00 with params `{}`
- Score 62%, full pass: False, finish: stop, error: None

## Failed checks

### `S2`

```
AssertionError: S2.final_balance: expected 110, got 120
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t7_pg_concurrency.py", line 19, in check
    eq(value, want, f"{name}.{field}")
    ~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: S2.final_balance: expected 110, got 120

```

### `S5`

```
AssertionError: S5.from_table: expected 100, got 70
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t7_pg_concurrency.py", line 19, in check
    eq(value, want, f"{name}.{field}")
    ~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: S5.from_table: expected 100, got 70

```

### `S8`

```
AssertionError: S8.a_commit_sqlstate: expected None, got '40001'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t7_pg_concurrency.py", line 19, in check
    eq(value, want, f"{name}.{field}")
    ~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: S8.a_commit_sqlstate: expected None, got '40001'

```

### `S9`

```
AssertionError: S9.balance_update: expected False, got True
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t7_pg_concurrency.py", line 19, in check
    eq(value, want, f"{name}.{field}")
    ~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: S9.balance_update: expected False, got True

```

### `S11`

```
AssertionError: S11.commit_sqlstate: expected None, got '25P02'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t7_pg_concurrency.py", line 19, in check
    eq(value, want, f"{name}.{field}")
    ~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: S11.commit_sqlstate: expected None, got '25P02'

```

## Prompt

See `tasks/t7_pg_concurrency/prompt.md`.

## Model output

```json
{
  "S1": {
    "b_blocked": true,
    "b_rowcount": 0,
    "final_balance": 20
  },
  "S2": {
    "b_rowcount": 1,
    "final_balance": 120
  },
  "S3": {
    "b_id": 1,
    "b_balance": 50
  },
  "S4": {
    "a_update_sqlstate": "40001",
    "final_balance": 70
  },
  "S5": {
    "from_u": 70,
    "from_table": 70,
    "final_balance": 70
  },
  "S6": {
    "b_blocked": true,
    "b_returned_rows": 0,
    "stored_result": "a"
  },
  "S7": {
    "b_select_rows": 0,
    "b_insert_sqlstate": "40001",
    "b_insert_returned_rows": 0
  },
  "S8": {
    "a_update_sqlstate": null,
    "b_update_sqlstate": null,
    "a_commit_sqlstate": "40001",
    "b_commit_sqlstate": null,
    "sum_after": 20
  },
  "S9": {
    "balance_update": true,
    "for_update": true,
    "for_no_key_update": true,
    "owner_changed": true,
    "owner_unchanged": true
  },
  "S10": {
    "b_gets_42": false,
    "b_gets_43": true
  },
  "S11": {
    "insert_sqlstate": "23505",
    "second_update_sqlstate": "25P02",
    "commit_sqlstate": "25P02",
    "commit_tag": null,
    "final_balance": 100
  },
  "S12": {
    "b_blocked": true,
    "b_rowcount": 0,
    "balance_1": 120,
    "balance_2": 50
  },
  "S13": {
    "b_blocked": true,
    "b_rowcount": 0,
    "final_balance": 5
  }
}
```
