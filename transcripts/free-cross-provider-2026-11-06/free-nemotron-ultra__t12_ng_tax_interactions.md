# free-nemotron-ultra / t12_ng_tax_interactions / trial 1

- Requested: `nvidia/nemotron-3-ultra-550b-a55b:free`, resolved: `nvidia/nemotron-3-ultra-550b-a55b:free`, provider: Nvidia
- Run at 2026-11-06T19:43:45+00:00 with params `{}`
- Score 39%, full pass: False, finish: stop, error: None

## Failed checks

### `M1`

```
AssertionError: M1.tax: expected 1950000.0, got 2230000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t12_ng_tax_interactions.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: M1.tax: expected 1950000.0, got 2230000

```

### `M2`

```
AssertionError: M2.tax: expected 996000.0, got 1020400
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t12_ng_tax_interactions.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: M2.tax: expected 996000.0, got 1020400

```

### `M3`

```
AssertionError: M3.tax: expected 679200.0, got 670000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t12_ng_tax_interactions.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: M3.tax: expected 679200.0, got 670000

```

### `M4`

```
AssertionError: M4.tax: expected 3057750.0, got 2920000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t12_ng_tax_interactions.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: M4.tax: expected 3057750.0, got 2920000

```

### `M5`

```
AssertionError: M5.tax: expected 1323600.0, got 1462000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t12_ng_tax_interactions.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: M5.tax: expected 1323600.0, got 1462000

```

### `M6`

```
AssertionError: M6.tax: expected 870000.0, got 886000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t12_ng_tax_interactions.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: M6.tax: expected 870000.0, got 886000

```

### `M7`

```
AssertionError: M7.tax: expected 1050000.0, got 1078000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t12_ng_tax_interactions.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: M7.tax: expected 1050000.0, got 1078000

```

### `G5`

```
AssertionError: G5.chargeable_gain: expected 2000000, got 1000000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t12_ng_tax_interactions.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: G5.chargeable_gain: expected 2000000, got 1000000

```

### `G8`

```
AssertionError: G8.chargeable_gain: expected 5000000, got 4000000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t12_ng_tax_interactions.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: G8.chargeable_gain: expected 5000000, got 4000000

```

### `G9`

```
AssertionError: G9.chargeable_gain: expected 0, got 19000000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t12_ng_tax_interactions.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: G9.chargeable_gain: expected 0, got 19000000

```

### `G10`

```
AssertionError: G10.chargeable_gain: expected 15000000, got 54000000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t12_ng_tax_interactions.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: G10.chargeable_gain: expected 15000000, got 54000000

```

## Prompt

See `tasks/t12_ng_tax_interactions/prompt.md`.

## Model output

```json
{
  "M1": {"tax": 2230000},
  "M2": {"tax": 1020400},
  "M3": {"tax": 670000},
  "M4": {"tax": 2920000},
  "M5": {"tax": 1462000},
  "M6": {"tax": 886000},
  "M7": {"tax": 1078000},
  "E1": {"topup": 46250000},
  "E2": {"topup": 0},
  "E3": {"deductible": 15000000},
  "V3": {"vat": 0},
  "V4": {"vat": 750},
  "G5": {"chargeable_gain": 1000000},
  "G6": {"chargeable_gain": 0},
  "G7": {"chargeable_gain": 0},
  "G8": {"chargeable_gain": 4000000},
  "G9": {"chargeable_gain": 19000000},
  "G10": {"chargeable_gain": 54000000}
}
```
