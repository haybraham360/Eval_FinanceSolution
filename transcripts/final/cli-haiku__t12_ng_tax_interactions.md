# cli-haiku / t12_ng_tax_interactions / trial 2

- Requested: `haiku`, resolved: `claude-haiku-5-5`, provider: claude-cli
- Run at 2026-10-31T20:45:55+00:00 with params `{}`
- Score 78%, full pass: False, finish: stop, error: None

## Failed checks

### `M1`

```
AssertionError: M1.tax: expected 1950000.0, got 2160000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t12_ng_tax_interactions.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: M1.tax: expected 1950000.0, got 2160000

```

### `M3`

```
AssertionError: M3.tax: expected 679200.0, got 672000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t12_ng_tax_interactions.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: M3.tax: expected 679200.0, got 672000

```

### `E1`

```
AssertionError: E1.topup: expected 46250000.0, got 49000000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t12_ng_tax_interactions.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: E1.topup: expected 46250000.0, got 49000000

```

### `G7`

```
AssertionError: G7.chargeable_gain: expected 0, got 5000000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t12_ng_tax_interactions.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: G7.chargeable_gain: expected 0, got 5000000

```

## Prompt

See `tasks/t12_ng_tax_interactions/prompt.md`.

## Model output

```json
{
  "M1": {"tax": 2160000},
  "M2": {"tax": 996000},
  "M3": {"tax": 672000},
  "M4": {"tax": 3057750},
  "M5": {"tax": 1323600},
  "M6": {"tax": 870000},
  "M7": {"tax": 1050000},
  "E1": {"topup": 49000000},
  "E2": {"topup": 0},
  "E3": {"deductible": 15000000},
  "V3": {"vat": 0},
  "V4": {"vat": 750},
  "G5": {"chargeable_gain": 2000000},
  "G6": {"chargeable_gain": 0},
  "G7": {"chargeable_gain": 5000000},
  "G8": {"chargeable_gain": 5000000},
  "G9": {"chargeable_gain": 0},
  "G10": {"chargeable_gain": 15000000}
}
```
