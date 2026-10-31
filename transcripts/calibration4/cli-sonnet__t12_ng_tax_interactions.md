# cli-sonnet / t12_ng_tax_interactions / trial 1

- Requested: `sonnet`, resolved: `claude-haiku-5-5,claude-sonnet-5-5`, provider: claude-cli
- Run at 2026-10-31T15:13:49+00:00 with params `{}`
- Score 89%, full pass: False, finish: stop, error: None

## Failed checks

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
AssertionError: E1.topup: expected 46250000.0, got 0
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t12_ng_tax_interactions.py", line 19, in check
    raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
AssertionError: E1.topup: expected 46250000.0, got 0

```

## Prompt

See `tasks/t12_ng_tax_interactions/prompt.md`.

## Model output

```json
{
  "M1": {"tax": 1950000},
  "M2": {"tax": 996000},
  "M3": {"tax": 672000},
  "M4": {"tax": 3057750},
  "M5": {"tax": 1323600},
  "M6": {"tax": 870000},
  "M7": {"tax": 1050000},
  "E1": {"topup": 0},
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

These figures come from my recollection of the Act's provisions, as no rule text was supplied. I could not check them against the Act itself, and several rest on specific recalled thresholds.

**Rate bands.** I used the Act's rate bands, which are cumulative:

| Band | Rate | Cumulative tax at top of band |
|---|---|---|
| First ₦800,000 | 0% | ₦0 |
| Next ₦2.2m | 15% | ₦330,000 |
| Next ₦9m | 18% | ₦1,950,000 |
| Next ₦13m | 21% | ₦4,680,000 |
| Next ₦25m | 23% | ₦10,430,000 |
| Above ₦50m | 25% | — |

**Individuals**
- **M1:** The rent-free premises benefit is capped at 20% of the ₦10m income, which is ₦2m, because the ₦3m rental value is higher. Taxable income is ₦12m.
- **M2:** The car benefit is 5% of the ₦20m cost, which is ₦1m. Less the ₦300k the employee pays, that is ₦700k, so taxable income is ₦6.7m.
- **M3:** Only the ₦100k premium paid in 2026 is deductible, so taxable income is ₦4.9m.
- **M4:** The deductions are pension ₦1.6m, NHF ₦125k and house-loan interest ₦1m, which total ₦2.725m. Taxable income is ₦17.275m.
- **M5:** Rent relief is 20% of ₦2.4m, which is ₦480k and under the ₦500k cap. Taxable income is ₦8.52m.
- **M6:** The digital asset loss cannot be set against salary, so tax is on ₦6m.
- **M7:** The net digital asset gain of ₦1m is added to the salary, so taxable income is ₦7m.

**Companies**
- **E1 and E2:** The 15% minimum effective tax rate applies only to MNE group members or companies with turnover of ₦50bn or more. Neither company reaches that, so the top-up is 0.
- **E3:** Foreign-currency expenses are deductible at the CBN official rate. That is US$10,000 × ₦1,500 = ₦15m, and the ₦3m paid above that rate is not deductible.

**VAT**
- **V3:** I treated interest on a loan as exempt, so VAT is 0.
- **V4:** I treated the processing fee as a taxable service. VAT is 7.5% of ₦10,000, which is ₦750.

**Chargeable gains**
- **G5:** I treated foreign currency held as an investment as a chargeable asset, so the full ₦2m gain is chargeable.
- **G6:** I treated a personal chattel sold for ₦5m or less as exempt. The ₦4.9m sale qualifies.
- **G7 and G8:** I treated labelled-startup gains as exempt only after at least 24 months' holding. Thirty months qualifies and 20 months does not.
- **G9 and G10:** I treated capital redundancy compensation as exempt up to ₦50m. ₦30m is fully exempt, and ₦65m leaves ₦15m chargeable.
