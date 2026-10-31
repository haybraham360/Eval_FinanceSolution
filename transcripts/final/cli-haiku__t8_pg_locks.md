# cli-haiku / t8_pg_locks / trial 1

- Requested: `haiku`, resolved: `claude-haiku-5-5`, provider: claude-cli
- Run at 2026-10-31T20:54:06+00:00 with params `{}`
- Score 89%, full pass: False, finish: stop, error: None

## Failed checks

### `L4`

```
AssertionError: L4.audit_rows: expected '3', got '4'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 25, in check
    same(got[field], value, f"{name}.{field}")
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 13, in same
    eq(text.strip(), str(want), label)
    ~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: L4.audit_rows: expected '3', got '4'

```

### `L9`

```
AssertionError: L9.b_sqlstate: expected '40001', got '23503'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 25, in check
    same(got[field], value, f"{name}.{field}")
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 13, in same
    eq(text.strip(), str(want), label)
    ~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: L9.b_sqlstate: expected '40001', got '23503'

```

## Prompt

See `tasks/t8_pg_locks/prompt.md`.

## Model output

```json
{
  "L1": {"b_blocked": true, "b_rows": 1},
  "L2": {"b_blocked": false, "b_rows": 1, "b_id": "2"},
  "L3": {"b_rowcount": 1, "balance_1": "5", "balance_2": "90"},
  "L4": {"audit_rows": "4", "audit_old_values": "100,100,20,20"},
  "L5": {"b_blocked": true, "balance_seen_by_c_before_a_commits": "1"},
  "L6": {"a_sqlstate": "40P01", "b_sqlstate": null, "final_balance": "98"},
  "L7": {"balance_update_blocked": false, "id_update_blocked": true},
  "L8": {"b_blocked": true, "b_sqlstate": "23503"},
  "L9": {"b_sqlstate": "23503"},
  "L10": {"b_returned": "a+b", "stored": "a+b"},
  "L11": {"a_returned_rows": 0, "b_sqlstate": "55P03"},
  "L12": {"do_update_sqlstate": "21000", "do_nothing_sqlstate": null, "do_nothing_rowcount": 1, "stored_j": "1"},
  "L13": {"id_of_y": "4"},
  "L14": {"join_sqlstate": "0A000", "distinct_sqlstate": "0A000", "join_of_a_sqlstate": null},
  "L15": {"b_first_sqlstate": null, "b_second_sqlstate": "55P03", "final_balance": "7"},
  "L16": {"final_balance": "101", "statement_sqlstate": null},
  "L17": {"rowcount": 1, "entries_applied": "1"},
  "L18": {"a_count": "0"},
  "L19": {"fetched": "100", "selected": "5"}
}
```
