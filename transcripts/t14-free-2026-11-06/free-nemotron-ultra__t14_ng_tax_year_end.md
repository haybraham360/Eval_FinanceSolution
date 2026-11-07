# free-nemotron-ultra / t14_ng_tax_year_end / trial 1

- Requested: `nvidia/nemotron-3-ultra-550b-a55b:free`, resolved: `nvidia/nemotron-3-ultra-550b-a55b:free`, provider: Nvidia
- Run at 2026-11-06T22:01:57+00:00 with params `{}`
- Score 23%, full pass: False, finish: stop, error: None

## Failed checks

### `KR1`

```
AssertionError: KR1.donation_deduction: expected 60000000, got 53380000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t14_ng_tax_year_end.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: KR1.donation_deduction: expected 60000000, got 53380000

```

### `KR2`

```
AssertionError: KR2.assessable_profit: expected 782000000, got 727000000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t14_ng_tax_year_end.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: KR2.assessable_profit: expected 782000000, got 727000000

```

### `KR3`

```
AssertionError: KR3.capital_allowance: expected 40000000, got 93200000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t14_ng_tax_year_end.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: KR3.capital_allowance: expected 40000000, got 93200000

```

### `KR4`

```
AssertionError: KR4.total_profit: expected 642000000, got 480420000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t14_ng_tax_year_end.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: KR4.total_profit: expected 642000000, got 480420000

```

### `KR5`

```
AssertionError: KR5.company_income_tax: expected 192600000, got 144126000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t14_ng_tax_year_end.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: KR5.company_income_tax: expected 192600000, got 144126000

```

### `KR6`

```
AssertionError: KR6.development_levy: expected 31280000, got 15845000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t14_ng_tax_year_end.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: KR6.development_levy: expected 31280000, got 15845000

```

### `G1`

```
AssertionError: G1.chargeable_gain: expected 1500000, got 3000000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t14_ng_tax_year_end.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: G1.chargeable_gain: expected 1500000, got 3000000

```

### `G3`

```
AssertionError: G3.chargeable_gain: expected 2000000, got 0
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t14_ng_tax_year_end.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: G3.chargeable_gain: expected 2000000, got 0

```

### `G4`

```
AssertionError: G4.chargeable_gain: expected 25000000, got 0
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t14_ng_tax_year_end.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: G4.chargeable_gain: expected 25000000, got 0

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
  "KR1": {"donation_deduction": 53380000},
  "KR2": {"assessable_profit": 727000000},
  "KR3": {"capital_allowance": 93200000},
  "KR4": {"total_profit": 480420000},
  "KR5": {"company_income_tax": 144126000},
  "KR6": {"development_levy": 15845000},
  "D2": {"donation_deduction": 12000000},
  "G1": {"chargeable_gain": 3000000},
  "G2": {"chargeable_gain": 15000000},
  "G3": {"chargeable_gain": 0},
  "G4": {"chargeable_gain": 0},
  "G5": {"chargeable_gain": 6000000},
  "V1": {"vat_payable": 5400000}
}
```
