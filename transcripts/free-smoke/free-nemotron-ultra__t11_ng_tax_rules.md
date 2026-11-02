# free-nemotron-ultra / t11_ng_tax_rules / trial 1

- Requested: `nvidia/nemotron-3-ultra-550b-a55b:free`, resolved: `nvidia/nemotron-3-ultra-550b-a55b:free`, provider: Nvidia
- Run at 2026-11-02T07:26:31+00:00 with params `{}`
- Score 52%, full pass: False, finish: stop, error: None

## Failed checks

### `P1`

```
AssertionError: P1.tax: expected 570750, got 378875
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t11_ng_tax_rules.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: P1.tax: expected 570750, got 378875

```

### `P2`

```
AssertionError: P2.tax: expected 1687200, got 1097600
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t11_ng_tax_rules.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: P2.tax: expected 1687200, got 1097600

```

### `P3`

```
AssertionError: P3.tax: expected 12930000, got 14192000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t11_ng_tax_rules.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: P3.tax: expected 12930000, got 14192000

```

### `P4`

```
AssertionError: P4.tax: expected 0, got 84000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t11_ng_tax_rules.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: P4.tax: expected 0, got 84000

```

### `C1`

```
AssertionError: C1.cit: expected 0, got 2000000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t11_ng_tax_rules.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: C1.cit: expected 0, got 2000000

```

### `C2`

```
AssertionError: C2.cit: expected 3000000, got 2000000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t11_ng_tax_rules.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: C2.cit: expected 3000000, got 2000000

```

### `C3`

```
AssertionError: C3.levy: expected 400000, got 100000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t11_ng_tax_rules.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: C3.levy: expected 400000, got 100000

```

### `C4`

```
AssertionError: C4.cit: expected 0, got 2000000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t11_ng_tax_rules.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: C4.cit: expected 0, got 2000000

```

### `G1`

```
AssertionError: G1.chargeable_gain: expected 0, got 8000000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t11_ng_tax_rules.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: G1.chargeable_gain: expected 0, got 8000000

```

### `G4`

```
AssertionError: G4.chargeable_gain: expected 20000000, got 60000000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t11_ng_tax_rules.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: G4.chargeable_gain: expected 20000000, got 60000000

```

## Prompt

See `tasks/t11_ng_tax_rules/prompt.md`.

## Model output

```json
{
  "ST1": {"duty": 50, "payer": "transferor"},
  "ST2": {"duty": 0, "payer": "none"},
  "ST3": {"duty": 50, "payer": "transferor"},
  "ST4": {"duty": 0, "payer": "none"},
  "ST5": {"duty": 0, "payer": "none"},
  "ST6": {"duty": 0, "payer": "none"},
  "P1": {"tax": 378875},
  "P2": {"tax": 1097600},
  "P3": {"tax": 14192000},
  "P4": {"tax": 84000},
  "P5": {"tax": 0},
  "C1": {"cit": 2000000, "levy": 0},
  "C2": {"cit": 2000000, "levy": 0},
  "C3": {"cit": 3000000, "levy": 100000},
  "C4": {"cit": 2000000, "levy": 0},
  "V1": {"vat": 7.5},
  "V2": {"vat": 7.5},
  "G1": {"chargeable_gain": 8000000},
  "G2": {"chargeable_gain": 12000000},
  "G3": {"chargeable_gain": 1250000},
  "G4": {"chargeable_gain": 60000000}
}
```
