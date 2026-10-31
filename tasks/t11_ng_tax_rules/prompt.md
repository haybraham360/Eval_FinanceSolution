# Compliance review: Nigerian tax rules in our payment and payroll systems

We run a Nigerian fintech with wallets, transfers, lending and payroll. Before an audit, confirm what our systems must do under the **Nigeria Tax Act, 2025 as in force on 1 October 2026**. No rule text is supplied, so apply the law itself, not earlier statutes or levies.

All amounts are naira unless stated. Answer every item. Each item is independent.

## Stamp duty on electronic transfers

For each transfer, give `duty` (naira) and `payer` (`"transferor"`, `"transferee"` or `"none"`, using `"none"` when no duty is due).

- ST1: ₦10,000.00 sent by Ada to Bola's account at a different bank.
- ST2: ₦9,999.99 sent by Ada to Bola's account at a different bank.
- ST3: ₦50,000.00 sent by Ada to Bola's account at the same bank as Ada.
- ST4: ₦1,000,000.00 moved by Ada between two accounts she owns at the same bank.
- ST5: ₦250,000.00 monthly salary paid by an employer to an employee's account at a different bank.
- ST6: US$5.00 electronically transferred from Ada to Bola when US$1 = ₦1,600.

## Personal income tax

Each person is a Nigerian resident individual, and all claims are made and documented as the Act requires. Give `tax`, the annual income tax in naira for the 2026 year of assessment. "Total income" means total income under section 28.

- P1: Total income ₦5,000,000. Pension Reform Act contribution ₦400,000. National Housing Fund contribution ₦62,500. Annual rent paid ₦1,000,000.
- P2: Total income ₦12,000,000. Pension Reform Act contribution ₦960,000. Annual rent paid ₦3,000,000.
- P3: Chargeable income ₦60,000,000, after all deductions.
- P4: Chargeable income ₦800,000, after all deductions.
- P5: An employee earning exactly the national minimum wage of ₦70,000 a month for all 12 months, with no deductions and no other income.

## Company income tax

Each company has assessable profits and total profits of ₦10,000,000 and is Nigerian, not part of an MNE group, with turnover below ₦20 billion. Give `cit` and `levy`, the company income tax and development levy in naira.

- C1: A retailer with gross turnover ₦45,000,000 and total fixed assets ₦100,000,000.
- C2: A law firm company with gross turnover ₦30,000,000 and total fixed assets ₦5,000,000.
- C3: A retailer with gross turnover ₦150,000,000 and total fixed assets ₦100,000,000.
- C4: A retailer with gross turnover exactly ₦50,000,000 and total fixed assets exactly ₦250,000,000.

## VAT

Give `vat` in naira.

- V1: A fee of ₦100.00 exclusive of VAT on a taxable supply.
- V2: A taxable supply for a total money consideration of ₦107.50, with no separate VAT stated.

## Chargeable gains

Give `chargeable_gain` in naira. Disposals are by a Nigerian-resident individual, and all figures are the totals for the relevant 12 months and year of assessment.

- G1: Shares in Nigerian companies sold for ₦120,000,000 with a gain of ₦8,000,000. Nothing reinvested.
- G2: Shares in Nigerian companies sold for ₦120,000,000 with a gain of ₦12,000,000. Nothing reinvested.
- G3: Shares in Nigerian companies sold for ₦200,000,000 with a gain of ₦5,000,000. ₦150,000,000 of the proceeds is reinvested in shares of other Nigerian companies in the same year of assessment.
- G4: ₦70,000,000 received as compensation for loss of employment.

Return one ```json block holding one object with one key per item, for example `{"ST1": {"duty": 0, "payer": "none"}, "P1": {"tax": 0}, "C1": {"cit": 0, "levy": 0}, "V1": {"vat": 0}, "G1": {"chargeable_gain": 0}}`. Use plain numbers.
