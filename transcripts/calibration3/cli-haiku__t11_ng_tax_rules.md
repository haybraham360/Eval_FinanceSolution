# cli-haiku / t11_ng_tax_rules / trial 3

- Requested: `haiku`, resolved: `claude-haiku-5-5`, provider: claude-cli
- Run at 2026-10-31T15:11:47+00:00 with params `{}`
- Score 71%, full pass: False, finish: stop, error: None

## Failed checks

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
AssertionError: P1.tax: expected 570750, got 390750
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t11_ng_tax_rules.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: P1.tax: expected 570750, got 390750

```

### `P2`

```
AssertionError: P2.tax: expected 1687200, got 1309200
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t11_ng_tax_rules.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: P2.tax: expected 1687200, got 1309200

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
{"ST1": {"duty": 50, "payer": "transferor"}, "ST2": {"duty": 0, "payer": "none"}, "ST3": {"duty": 50, "payer": "transferor"}, "ST4": {"duty": 0, "payer": "none"}, "ST5": {"duty": 50, "payer": "transferor"}, "ST6": {"duty": 0, "payer": "none"}, "P1": {"tax": 390750}, "P2": {"tax": 1309200}, "P3": {"tax": 12930000}, "P4": {"tax": 0}, "P5": {"tax": 0}, "C1": {"cit": 0, "levy": 0}, "C2": {"cit": 0, "levy": 0}, "C3": {"cit": 3000000, "levy": 400000}, "C4": {"cit": 0, "levy": 0}, "V1": {"vat": 7.5}, "V2": {"vat": 7.5}, "G1": {"chargeable_gain": 8000000}, "G2": {"chargeable_gain": 12000000}, "G3": {"chargeable_gain": 1250000}, "G4": {"chargeable_gain": 0}}
```
