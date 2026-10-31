# cli-haiku / t7_pg_concurrency / trial 2

- Requested: `haiku`, resolved: `claude-haiku-5-5`, provider: claude-cli
- Run at 2026-10-31T20:52:48+00:00 with params `{}`
- Score 85%, full pass: False, finish: stop, error: None

## Failed checks

### `S7`

```
AssertionError: S7.b_insert_sqlstate: expected '40001', got 'NONE'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t7_pg_concurrency.py", line 19, in check
    eq(value, want, f"{name}.{field}")
    ~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: S7.b_insert_sqlstate: expected '40001', got 'NONE'

```

### `S8`

```
AssertionError: S8.b_update_sqlstate: expected None, got '40001'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t7_pg_concurrency.py", line 19, in check
    eq(value, want, f"{name}.{field}")
    ~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: S8.b_update_sqlstate: expected None, got '40001'

```

## Prompt

See `tasks/t7_pg_concurrency/prompt.md`.

## Model output

```json
{
  "S1": {"b_blocked": true, "b_rowcount": 0, "final_balance": 20},
  "S2": {"b_rowcount": 1, "final_balance": 110},
  "S3": {"b_id": 1, "b_balance": 50},
  "S4": {"a_update_sqlstate": "40001", "final_balance": 70},
  "S5": {"from_u": 70, "from_table": 100, "final_balance": 70},
  "S6": {"b_blocked": true, "b_returned_rows": 0, "stored_result": "a"},
  "S7": {"b_select_rows": 0, "b_insert_sqlstate": null, "b_insert_returned_rows": 0},
  "S8": {"a_update_sqlstate": null, "b_update_sqlstate": "40001", "a_commit_sqlstate": null, "b_commit_sqlstate": null, "sum_after": 20},
  "S9": {
    "balance_update": false,
    "for_update": true,
    "for_no_key_update": false,
    "owner_changed": true,
    "owner_unchanged": false
  },
  "S10": {"b_gets_42": false, "b_gets_43": true},
  "S11": {"insert_sqlstate": "23505", "second_update_sqlstate": "25P02", "commit_sqlstate": null, "commit_tag": "ROLLBACK", "final_balance": 100},
  "S12": {"b_blocked": true, "b_rowcount": 0, "balance_1": 120, "balance_2": 50},
  "S13": {"b_blocked": true, "b_rowcount": 0, "final_balance": 5}
}
```
