# cli-sonnet / t12_ng_tax_interactions / trial 1

- Requested: `sonnet`, resolved: `claude-haiku-5-5,claude-sonnet-5-5`, provider: claude-cli
- Run at 2026-10-31T20:33:43+00:00 with params `{}`
- Score 83%, full pass: False, finish: stop, error: None

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
AssertionError: E1.topup: expected 46250000.0, got 50000000
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t12_ng_tax_interactions.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: E1.topup: expected 46250000.0, got 50000000

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
  "E1": {"topup": 50000000},
  "E2": {"topup": 0},
  "E3": {"deductible": 15000000},
  "V3": {"vat": 0},
  "V4": {"vat": 750},
  "G5": {"chargeable_gain": 2000000},
  "G6": {"chargeable_gain": 0},
  "G7": {"chargeable_gain": 0},
  "G8": {"chargeable_gain": 5000000},
  "G9": {"chargeable_gain": 0},
  "G10": {"chargeable_gain": 15000000}
}
```

These figures come from my recollection of the Act. No rule text was supplied and I did not check it against the statute. These points are the least certain:

- **Rate bands:** 0% on the first ₦800,000, then 15%, 18%, 21%, 23% and 25% above ₦50,000,000.
- **M1:** I added the full ₦3,000,000 rental value to income. I am not sure whether the Act caps this amount.
- **M2:** I valued the car benefit at 5% of cost (₦1,000,000), less the ₦300,000 the employee pays.
- **M3:** Only the 2026 premium of ₦100,000 is deductible. The 2025 premium is not.
- **M4:** I deducted pension, NHF and the owner-occupied house loan interest.
- **M5:** Rent relief is 20% of rent, capped at ₦500,000, so it is ₦480,000 here.
- **M6/M7:** Digital asset losses can only offset digital asset gains, not salary. In M7 the net ₦1,000,000 gain is added to income.
- **E1/E2:** I applied the minimum effective tax rate of 15% to companies with turnover of ₦20 billion or more. E1 is above that and E2 is below it. I am not sure whether the threshold is ₦20 billion or ₦50 billion; at ₦50 billion both would be 0. E1's effective rate is 10%, so the top-up is 5% of ₦1 billion. I did not use depreciation or personnel cost.
- **E3:** The deduction is limited to the CBN official rate of ₦1,500 per dollar, so US$10,000 gives ₦15,000,000.
- **V3/V4:** I treated loan interest as VAT-exempt and the processing fee as standard-rated at 7.5%.
- **G5:** Foreign currency held as an investment is a chargeable asset.
- **G6:** I treated the painting as an exempt personal chattel because the ₦4,900,000 proceeds are under what I recall as a ₦5,000,000 limit.
- **G7/G8:** Labelled-startup gains are exempt after 24 months of holding, so the 30-month sale is exempt and the 20-month sale is not.
- **G9/G10:** A capital redundancy payment is exempt up to ₦50,000,000, so the ₦65,000,000 payment leaves ₦15,000,000 chargeable.
