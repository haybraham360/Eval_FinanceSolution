# cli-haiku / t9_pg_isolation / trial 1

- Requested: `haiku`, resolved: `claude-haiku-5-5`, provider: claude-cli
- Run at 2026-10-31T14:59:33+00:00 with params `{}`
- Score 88%, full pass: False, finish: stop, error: None

## Failed checks

### `I8`

```
AssertionError: I8.b_commit_sqlstate: expected None, got '40001'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 25, in check
    same(got[field], value, f"{name}.{field}")
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 10, in same
    eq(got, want, label)
    ~~^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: I8.b_commit_sqlstate: expected None, got '40001'

```

### `I13`

```
AssertionError: I13.deferrable_unique_sqlstate: expected None, got '23505'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 25, in check
    same(got[field], value, f"{name}.{field}")
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 10, in same
    eq(got, want, label)
    ~~^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: I13.deferrable_unique_sqlstate: expected None, got '23505'

```

## Prompt

See `tasks/t9_pg_isolation/prompt.md`.

## Model output

```json
{
  "I1": {"a_saw": "7"},
  "I2": {"a_blocked": true, "a_saw": "100", "a_update_sqlstate": "40001", "final_balance": "7"},
  "I3": {"a_blocked": true, "a_saw": "7"},
  "I4": {"a_blocked": true, "a_sqlstate": null, "a_saw": "100"},
  "I5": {"first_sqlstate": "40001", "rollback_to_sqlstate": null, "retry_sqlstate": "40001"},
  "I6": {"b_blocked": true, "b_sqlstate": "40001"},
  "I7": {"b_sqlstate": "23505"},
  "I8": {"a_commit_sqlstate": null, "b_commit_sqlstate": "40001"},
  "I9": {"a_commit_sqlstate": null, "b_commit_sqlstate": null, "sum_after": "-100"},
  "I10": {"a_commit_sqlstate": null, "b_select_sqlstate": null, "b_commit_sqlstate": "40001", "b_commit_tag": null},
  "I11": {"b_commit_sqlstate": null, "c_commit_sqlstate": null, "a_insert_sqlstate": "40001", "a_commit_sqlstate": null},
  "I12": {"insert_sqlstate": null, "visible_rows": "2", "commit_sqlstate": "23505", "rows_after": "1"},
  "I13": {"plain_unique_sqlstate": "23505", "deferrable_unique_sqlstate": "23505"},
  "I14": {"insert_sqlstate": null, "set_immediate_sqlstate": "23503"},
  "I15": {"sqlstate": "55000"},
  "I16": {"first": "100", "second": "7"},
  "I17": {"lock_timeout_sqlstate": "55P03", "statement_timeout_sqlstate": "57014"}
}
```
