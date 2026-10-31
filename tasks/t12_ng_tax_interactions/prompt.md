# Compliance review: Nigeria Tax Act cases that combine several provisions

We are testing our payroll, lending and treasury systems against the **Nigeria Tax Act, 2025 as in force on 1 October 2026**. No rule text is supplied, so apply the Act itself. Amounts are naira unless stated. Every person is a Nigerian-resident individual and every company is Nigerian. All claims are made and documented as the Act requires, and each item is independent.

## Individuals: give `tax`, the annual income tax for the 2026 year of assessment

- M1: Employment income, excluding any rental value, is ₦10,000,000. The employer provides premises rent-free, and their annual rental value is ₦3,000,000. There are no deductions.
- M2: Salary ₦6,000,000. The employee has the full use of a car the employer bought for ₦20,000,000, and the employee pays the employer ₦300,000 a year towards it. There are no deductions.
- M3: Salary ₦5,000,000. A qualifying life insurance premium of ₦60,000 was paid in 2025, and another of ₦100,000 was paid in 2026. There are no other deductions.
- M4: Salary ₦20,000,000. Pension Reform Act contribution ₦1,600,000. National Housing Fund contribution ₦125,000. Interest of ₦1,000,000 paid on a loan to develop the owner-occupied house the person lives in, so no rent is paid.
- M5: Salary ₦9,000,000. Annual rent paid ₦2,400,000. No other deductions.
- M6: Salary ₦6,000,000. A loss of ₦2,000,000 on digital asset disposals. No other digital asset activity.
- M7: Salary ₦6,000,000. Digital asset profits of ₦3,000,000 and digital asset losses of ₦2,000,000 in the same year.

## Companies

- E1: A company that is not in an MNE group has aggregate turnover ₦25,000,000,000. Its audited net profit before tax is ₦1,000,000,000, depreciation ₦100,000,000, personnel cost ₦400,000,000, and covered tax paid ₦100,000,000. Give `topup`, the additional tax to reach the minimum effective tax rate.
- E2: The same figures, but aggregate turnover is ₦15,000,000,000. Give `topup`.
- E3: A company incurs a deductible business expense of US$10,000 and buys the dollars at ₦1,800 per dollar. The CBN official rate on that date is ₦1,500 per dollar. Give `deductible`, the amount deductible in naira.

## VAT: give `vat`

- V3: A lender charges ₦10,000 of interest on a loan of money.
- V4: The same lender charges a ₦10,000 loan processing fee, exclusive of VAT.

## Chargeable gains: give `chargeable_gain`

- G5: An individual sells US dollars held as an investment, for a gain of ₦2,000,000.
- G6: An individual sells a personal chattel, a painting, for ₦4,900,000 at a gain of ₦900,000. It is the person's only chattel sale in the period.
- G7: An angel investor sells assets in a labelled startup after holding them in Nigeria for 30 months, for a gain of ₦5,000,000.
- G8: The same sale as G7, after 20 months.
- G9: An employee receives a ₦30,000,000 redundancy lump sum of a capital nature.
- G10: An employee receives a ₦65,000,000 redundancy lump sum of a capital nature.

Return one ```json block holding one object with one key per item, for example `{"M1": {"tax": 0}, "E1": {"topup": 0}, "E3": {"deductible": 0}, "V3": {"vat": 0}, "G5": {"chargeable_gain": 0}}`. Use plain numbers.
