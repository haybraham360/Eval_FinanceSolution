# cli-sonnet / t11_ng_tax_rules / trial 1

- Requested: `sonnet`, resolved: `claude-haiku-5-5,claude-sonnet-5-5`, provider: claude-cli
- Run at 2026-10-31T15:10:53+00:00 with params `{}`
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

These figures come from my recollection of the Act, not from rule text I could check here. The points I am least sure of are:

- **Stamp duty:** I took the ₦50 duty, the ₦10,000 threshold, the transferor as payer, and the exemptions for same-bank, same-owner and salary transfers from memory. ST6 is ₦8,000 at the given rate, below the threshold.
- **Personal income tax:**
  - **Bands and reliefs:** I applied the graduated bands (0% on the first ₦800,000, then 15%, 18%, 21%, 23% and 25% above ₦50m). Rent relief is 20% of rent, capped at ₦500,000. Pension and National Housing Fund contributions are deducted.
  - **P5:** I treated a minimum-wage earner as exempt, so tax is nil.
- **Company income tax:**
  - **Small-company test:** A small company has turnover of ₦100m or less, fixed assets of ₦250m or less, and is not a professional services firm. It pays no company income tax or development levy. I recalled ₦100m as the final turnover threshold; the earlier ₦50m figure was in the bill, and C4 is exempt under either.
  - **Other companies:** They pay 30% company income tax and a 4% development levy.
- **VAT:** The rate is 7.5%. Where no VAT is stated, I treated the price as VAT-inclusive.
- **Chargeable gains:**
  - **G1 and G2:** Share disposals are exempt only if proceeds are under ₦150m and the gain is ₦10m or less.
  - **G3:** I reduced the gain pro rata for the part of the proceeds not reinvested: ₦5m × 50/200 = ₦1.25m.
  - **G4:** Loss-of-employment compensation is exempt up to ₦50m, and it is not a capital gain in any case.
