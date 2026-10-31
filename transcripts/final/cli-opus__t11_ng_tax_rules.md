# cli-opus / t11_ng_tax_rules / trial 1

- Requested: `opus`, resolved: `claude-haiku-5-5,claude-opus-5-5`, provider: claude-cli
- Run at 2026-10-31T15:18:44+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

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
  "G4": {"chargeable_gain": 20000000}
}
```

These answers come from my recollection of the Act, not a check against its text, so confirm them before the audit. The least certain are ST3 (I treated the intra-bank exemption as covering only transfers between a person's own accounts) and G2 (I treated the ₦10,000,000 limit as a cap, not a deduction).
