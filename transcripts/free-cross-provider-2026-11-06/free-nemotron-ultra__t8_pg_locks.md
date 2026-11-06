# free-nemotron-ultra / t8_pg_locks / trial 1

- Requested: `nvidia/nemotron-3-ultra-550b-a55b:free`, resolved: `nvidia/nemotron-3-ultra-550b-a55b:free`, provider: Nvidia
- Run at 2026-11-06T20:33:32+00:00 with params `{}`
- Score 58%, full pass: False, finish: stop, error: None

## Failed checks

### `L5`

```
AssertionError: L5.balance_seen_by_c_before_a_commits: expected '1', got '100'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 25, in check
    same(got[field], value, f"{name}.{field}")
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 13, in same
    eq(text.strip(), str(want), label)
    ~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: L5.balance_seen_by_c_before_a_commits: expected '1', got '100'

```

### `L6`

```
AssertionError: L6.a_sqlstate: expected '40P01', got 'None'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 25, in check
    same(got[field], value, f"{name}.{field}")
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 13, in same
    eq(text.strip(), str(want), label)
    ~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: L6.a_sqlstate: expected '40P01', got 'None'

```

### `L9`

```
AssertionError: L9.b_sqlstate: expected '40001', got 'None'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 25, in check
    same(got[field], value, f"{name}.{field}")
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 13, in same
    eq(text.strip(), str(want), label)
    ~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: L9.b_sqlstate: expected '40001', got 'None'

```

### `L12`

```
AssertionError: L12.do_update_sqlstate: expected '21000', got '23505'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 25, in check
    same(got[field], value, f"{name}.{field}")
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 13, in same
    eq(text.strip(), str(want), label)
    ~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: L12.do_update_sqlstate: expected '21000', got '23505'

```

### `L13`

```
AssertionError: L13.id_of_y: expected '4', got '2'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 25, in check
    same(got[field], value, f"{name}.{field}")
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 13, in same
    eq(text.strip(), str(want), label)
    ~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: L13.id_of_y: expected '4', got '2'

```

### `L15`

```
AssertionError: L15.b_first_sqlstate: expected None, got '55P03'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 25, in check
    same(got[field], value, f"{name}.{field}")
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 10, in same
    eq(got, want, label)
    ~~^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: L15.b_first_sqlstate: expected None, got '55P03'

```

### `L16`

```
AssertionError: L16.final_balance: expected '101', got '111'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 25, in check
    same(got[field], value, f"{name}.{field}")
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 13, in same
    eq(text.strip(), str(want), label)
    ~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: L16.final_balance: expected '101', got '111'

```

### `L19`

```
AssertionError: L19.fetched: expected '100', got '5'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 25, in check
    same(got[field], value, f"{name}.{field}")
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 13, in same
    eq(text.strip(), str(want), label)
    ~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: L19.fetched: expected '100', got '5'

```

## Prompt

See `tasks/t8_pg_locks/prompt.md`.

## Model output

```json
{
  "L1": {
    "b_blocked": true,
    "b_rows": 1
  },
  "L2": {
    "b_blocked": false,
    "b_rows": 1,
    "b_id": "2"
  },
  "L3": {
    "b_rowcount": 1,
    "balance_1": "5",
    "balance_2": "90"
  },
  "L4": {
    "audit_rows": "3",
    "audit_old_values": "100,20,100"
  },
  "L5": {
    "b_blocked": true,
    "balance_seen_by_c_before_a_commits": "100"
  },
  "L6": {
    "a_sqlstate": null,
    "b_sqlstate": "40P01",
    "final_balance": "100"
  },
  "L7": {
    "balance_update_blocked": false,
    "id_update_blocked": true
  },
  "L8": {
    "b_blocked": true,
    "b_sqlstate": "23503"
  },
  "L9": {
    "b_sqlstate": null
  },
  "L10": {
    "b_returned": "a+b",
    "stored": "a+b"
  },
  "L11": {
    "a_returned_rows": 0,
    "b_sqlstate": "55P03"
  },
  "L12": {
    "do_update_sqlstate": "23505",
    "do_nothing_sqlstate": "23505",
    "do_nothing_rowcount": 0,
    "stored_j": null
  },
  "L13": {
    "id_of_y": "2"
  },
  "L14": {
    "join_sqlstate": "0A000",
    "distinct_sqlstate": "0A000",
    "join_of_a_sqlstate": null
  },
  "L15": {
    "b_first_sqlstate": "55P03",
    "b_second_sqlstate": "55P03",
    "final_balance": "7"
  },
  "L16": {
    "final_balance": "111",
    "statement_sqlstate": null
  },
  "L17": {
    "rowcount": 1,
    "entries_applied": "1"
  },
  "L18": {
    "a_count": "0"
  },
  "L19": {
    "fetched": "5",
    "selected": "5"
  }
}
```
