# cli-sonnet / t11_ng_tax_rules / trial 2

- Requested: `sonnet`, resolved: `claude-haiku-5-5,claude-sonnet-5-5`, provider: claude-cli
- Run at 2026-10-31T20:33:11+00:00 with params `{}`
- Score 90%, full pass: False, finish: stop, error: None

## Failed checks

### `ST3`

```
AssertionError: ST3.duty: expected 50, got 0
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t11_ng_tax_rules.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: ST3.duty: expected 50, got 0

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
  "ST3": {"duty": 0, "payer": "none"},
  "ST4": {"duty": 0, "payer": "none"},
  "ST5": {"duty": 0, "payer": "none"},
  "ST6": {"duty": 0, "payer": "none"},
  "P1": {"tax": 570750},
  "P2": {"tax": 1687200},
  "P3": {"tax": 12930000},
  "P4": {"tax": 0},
  "P5": {"tax": 0},
  "C1": {"cit": 0, "levy": 0},
  "C2": {"cit": 3000000, "levy": 400000},
  "C3": {"cit": 3000000, "levy": 400000},
  "C4": {"cit": 0, "levy": 0},
  "V1": {"vat": 7.5},
  "V2": {"vat": 7.5},
  "G1": {"chargeable_gain": 0},
  "G2": {"chargeable_gain": 12000000},
  "G3": {"chargeable_gain": 1250000},
  "G4": {"chargeable_gain": 0}
}
```

These answers rest on my recall of the Act, since no rule text was supplied. I am least sure of the following:
- **ST3 and ST5:** I treated same-bank transfers between different people and salary payments as exempt from stamp duty.
- **G3:** I apportioned the gain by the share of proceeds reinvested (₦150m of ₦200m), which leaves 25% of the ₦5m gain chargeable. Treating the unreinvested proceeds as the cap would give ₦5m instead.
- **G4:** I treated the ₦20m above the ₦50m exemption as employment income, not a chargeable gain.

Please check these against the section text before the audit.
