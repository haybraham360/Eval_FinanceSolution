# cli-opus / t14_ng_tax_year_end / trial 1

- Requested: `opus`, resolved: `claude-haiku-5-5,claude-opus-5-5`, provider: claude-cli
- Run at 2026-11-06T21:42:23+00:00 with params `{}`
- Score 46%, full pass: False, finish: stop, error: None

## Failed checks

### `KR1`

```
AssertionError: KR1.donation_deduction: expected 60000000, got 70200000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t14_ng_tax_year_end.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: KR1.donation_deduction: expected 60000000, got 70200000

```

### `KR2`

```
AssertionError: KR2.assessable_profit: expected 782000000, got 771800000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t14_ng_tax_year_end.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: KR2.assessable_profit: expected 782000000, got 771800000

```

### `KR4`

```
AssertionError: KR4.total_profit: expected 642000000, got 631800000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t14_ng_tax_year_end.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: KR4.total_profit: expected 642000000, got 631800000

```

### `KR5`

```
AssertionError: KR5.company_income_tax: expected 192600000, got 189540000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t14_ng_tax_year_end.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: KR5.company_income_tax: expected 192600000, got 189540000

```

### `KR6`

```
AssertionError: KR6.development_levy: expected 31280000, got 30872000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t14_ng_tax_year_end.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: KR6.development_levy: expected 31280000, got 30872000

```

### `G1`

```
AssertionError: G1.chargeable_gain: expected 1500000, got 0
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t14_ng_tax_year_end.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: G1.chargeable_gain: expected 1500000, got 0

```

### `G5`

```
AssertionError: G5.chargeable_gain: expected 0, got 6000000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t14_ng_tax_year_end.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: G5.chargeable_gain: expected 0, got 6000000

```

## Prompt

See `tasks/t14_ng_tax_year_end/prompt.md`.

## Model output

```json
{
  "KR1": {"donation_deduction": 70200000},
  "KR2": {"assessable_profit": 771800000},
  "KR3": {"capital_allowance": 40000000},
  "KR4": {"total_profit": 631800000},
  "KR5": {"company_income_tax": 189540000},
  "KR6": {"development_levy": 30872000},
  "D2": {"donation_deduction": 12000000},
  "G1": {"chargeable_gain": 0},
  "G2": {"chargeable_gain": 15000000},
  "G3": {"chargeable_gain": 2000000},
  "G4": {"chargeable_gain": 25000000},
  "G5": {"chargeable_gain": 6000000},
  "V1": {"vat_payable": 5400000}
}
```
