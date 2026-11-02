# free-dots-3 / t11_ng_tax_rules / trial 1

- Requested: `dots-studio/dots-3-note-preview:free`, resolved: `dots-studio/dots-3-note-preview:free`, provider: AtlasCloud
- Run at 2026-11-02T07:48:51+00:00 with params `{}`
- Score 38%, full pass: False, finish: stop, error: None

## Failed checks

### `ST4`

```
AssertionError: ST4.duty: expected 0, got 50
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t11_ng_tax_rules.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: ST4.duty: expected 0, got 50

```

### `ST5`

```
AssertionError: ST5.duty: expected 0, got 50
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t11_ng_tax_rules.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: ST5.duty: expected 0, got 50

```

### `P1`

```
AssertionError: P1.tax: expected 570750, got 659375
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t11_ng_tax_rules.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: P1.tax: expected 570750, got 659375

```

### `P2`

```
AssertionError: P2.tax: expected 1687200, got 1785000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t11_ng_tax_rules.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: P2.tax: expected 1687200, got 1785000

```

### `P3`

```
AssertionError: P3.tax: expected 12930000, got 14775000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t11_ng_tax_rules.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: P3.tax: expected 12930000, got 14775000

```

### `P4`

```
AssertionError: P4.tax: expected 0, got 35000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t11_ng_tax_rules.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: P4.tax: expected 0, got 35000

```

### `C2`

```
AssertionError: C2.cit: expected 3000000, got 0
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t11_ng_tax_rules.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: C2.cit: expected 3000000, got 0

```

### `C3`

```
AssertionError: C3.levy: expected 400000, got 200000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t11_ng_tax_rules.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: C3.levy: expected 400000, got 200000

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
AssertionError: G1.chargeable_gain: expected 0, got 7900000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t11_ng_tax_rules.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: G1.chargeable_gain: expected 0, got 7900000

```

### `G2`

```
AssertionError: G2.chargeable_gain: expected 12000000, got 11900000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t11_ng_tax_rules.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: G2.chargeable_gain: expected 12000000, got 11900000

```

### `G3`

```
AssertionError: G3.chargeable_gain: expected 1250000, got 1150000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t11_ng_tax_rules.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: G3.chargeable_gain: expected 1250000, got 1150000

```

### `G4`

```
AssertionError: G4.chargeable_gain: expected 20000000, got 0
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t11_ng_tax_rules.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: G4.chargeable_gain: expected 20000000, got 0

```

## Prompt

See `tasks/t11_ng_tax_rules/prompt.md`.

## Model output



```json
{
  "ST1": {"duty": 50, "payer": "transferor"},
  "ST2": {"duty": 0, "payer": "none"},
  "ST3": {"duty": 50, "payer": "transferor"},
  "ST4": {"duty": 50, "payer": "transferor"},
  "ST5": {"duty": 50, "payer": "transferor"},
  "ST6": {"duty": 0, "payer": "none"},
  "P1": {"tax": 659375},
  "P2": {"tax": 1785000},
  "P3": {"tax": 14775000},
  "P4": {"tax": 35000},
  "P5": {"tax": 0},
  "C1": {"cit": 0, "levy": 0},
  "C2": {"cit": 0, "levy": 0},
  "C3": {"cit": 3000000, "levy": 200000},
  "C4": {"cit": 2000000, "levy": 0},
  "V1": {"vat": 7.5},
  "V2": {"vat": 7.5},
  "G1": {"chargeable_gain": 7900000},
  "G2": {"chargeable_gain": 11900000},
  "G3": {"chargeable_gain": 1150000},
  "G4": {"chargeable_gain": 0}
}
```
