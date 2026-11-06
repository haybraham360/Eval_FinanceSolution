# free-nemotron-ultra / t9_pg_isolation / trial 1

- Requested: `nvidia/nemotron-3-ultra-550b-a55b:free`, resolved: `nvidia/nemotron-3-ultra-550b-a55b:free`, provider: Nvidia
- Run at 2026-11-06T20:39:10+00:00 with params `{}`
- Score 71%, full pass: False, finish: stop, error: None

## Failed checks

### `I2`

```
AssertionError: I2.a_saw: expected '100', got '7'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 25, in check
    same(got[field], value, f"{name}.{field}")
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 13, in same
    eq(text.strip(), str(want), label)
    ~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: I2.a_saw: expected '100', got '7'

```

### `I6`

```
AssertionError: I6.b_sqlstate: expected '40001', got '23505'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 25, in check
    same(got[field], value, f"{name}.{field}")
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 13, in same
    eq(text.strip(), str(want), label)
    ~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: I6.b_sqlstate: expected '40001', got '23505'

```

### `I9`

```
AssertionError: I9.a_commit_sqlstate: expected None, got '40001'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 25, in check
    same(got[field], value, f"{name}.{field}")
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 10, in same
    eq(got, want, label)
    ~~^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: I9.a_commit_sqlstate: expected None, got '40001'

```

### `I10`

```
AssertionError: I10.a_commit_sqlstate: expected None, got '40001'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 25, in check
    same(got[field], value, f"{name}.{field}")
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 10, in same
    eq(got, want, label)
    ~~^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: I10.a_commit_sqlstate: expected None, got '40001'

```

### `I11`

```
AssertionError: I11.a_insert_sqlstate: expected '40001', got 'None'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 25, in check
    same(got[field], value, f"{name}.{field}")
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 13, in same
    eq(text.strip(), str(want), label)
    ~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: I11.a_insert_sqlstate: expected '40001', got 'None'

```

## Prompt

See `tasks/t9_pg_isolation/prompt.md`.

## Model output

```json
{
  "I1": {
    "a_saw": "7"
  },
  "I2": {
    "a_blocked": true,
    "a_saw": "7",
    "a_update_sqlstate": null,
    "final_balance": "7"
  },
  "I3": {
    "a_blocked": true,
    "a_saw": "7"
  },
  "I4": {
    "a_blocked": true,
    "a_sqlstate": null,
    "a_saw": "100"
  },
  "I5": {
    "first_sqlstate": "40001",
    "rollback_to_sqlstate": null,
    "retry_sqlstate": "40001"
  },
  "I6": {
    "b_blocked": true,
    "b_sqlstate": "23505"
  },
  "I7": {
    "b_sqlstate": "23505"
  },
  "I8": {
    "a_commit_sqlstate": null,
    "b_commit_sqlstate": null
  },
  "I9": {
    "a_commit_sqlstate": "40001",
    "b_commit_sqlstate": null,
    "sum_after": "50"
  },
  "I10": {
    "a_commit_sqlstate": "40001",
    "b_select_sqlstate": null,
    "b_commit_sqlstate": null,
    "b_commit_tag": "COMMIT"
  },
  "I11": {
    "b_commit_sqlstate": null,
    "c_commit_sqlstate": null,
    "a_insert_sqlstate": null,
    "a_commit_sqlstate": "40001"
  },
  "I12": {
    "insert_sqlstate": null,
    "visible_rows": "2",
    "commit_sqlstate": "23505",
    "rows_after": "1"
  },
  "I13": {
    "plain_unique_sqlstate": "23505",
    "deferrable_unique_sqlstate": null
  },
  "I14": {
    "insert_sqlstate": null,
    "set_immediate_sqlstate": "23503"
  },
  "I15": {
    "sqlstate": "55000"
  },
  "I16": {
    "first": "100",
    "second": "7"
  },
  "I17": {
    "lock_timeout_sqlstate": "55P03",
    "statement_timeout_sqlstate": "57014"
  }
}
```
