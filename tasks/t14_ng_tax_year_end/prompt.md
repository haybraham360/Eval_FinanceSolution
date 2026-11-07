# Year-end tax review: Nigeria Tax Act cases where one provision limits another

We are closing the books of a Nigerian fintech group and checking its tax workings against the **Nigeria Tax Act, 2025, as enacted, with no later amendments**. No rule text is supplied, so apply the Act itself. Amounts are naira. Every person is a Nigerian-resident individual and every company is a Nigerian company. Every claim is made in time and documented as the Act requires, and every item is independent of the others unless it says otherwise.

## Kudi Rails Ltd, year of assessment 2027

Kudi Rails Ltd is a payments company. It is not a small company, it is not part of a multinational group, and its turnover is below the threshold for the minimum effective tax rate. It is assessed for 2027 on its accounts for the full year ended 31 December 2027.

- Turnover: ₦3,000,000,000.
- Audited profit before tax: ₦600,000,000. This figure is after deducting every expense listed below at the amount shown.
- Depreciation of fixed assets: ₦90,000,000.
- An unrealised exchange loss from revaluing a US dollar loan at year end: ₦25,000,000.
- A fine imposed by a regulator for filing a return late: ₦12,000,000.
- A consultancy fee of ₦40,000,000 paid to a Nigerian firm. The service was subject to VAT, and the firm was required to charge VAT on it, but it did not, and Kudi Rails paid no VAT on the fee.
- Cash donations to registered educational and charitable institutions established in Nigeria: ₦75,000,000.
- All other expenses in the accounts are wholly, reasonably, exclusively and necessarily incurred for the business, and no other adjustment is needed.

Losses brought forward from 2026, the company's first year, which have not been relieved:

- A trading loss of ₦100,000,000 from its payments business.
- A loss of ₦30,000,000 from trading digital assets. The company closed its digital asset desk at the end of 2026 and has had no digital asset business since.

Capital expenditure, all incurred on 2 January 2027:

- Payment-processing software: ₦120,000,000, VAT charged and paid. In use from January 2027.
- Office furniture: ₦50,000,000, VAT charged and paid. In use from January 2027.
- Two delivery motor vehicles, bought locally: ₦80,000,000. The seller was required to charge VAT on the sale but did not, and Kudi Rails paid no VAT on them.
- A new office building: ₦300,000,000, VAT charged and paid. It was still under construction on 31 December 2027 and was first used in February 2028.

No capital allowance has ever been made on any of these assets before 2027. The company has no income that is exempt from tax and no chargeable gains in 2027.

Give, for 2027:

- KR1: `donation_deduction`, the deduction allowed for the donations.
- KR2: `assessable_profit`, the assessable profits before any loss relief or capital allowance.
- KR3: `capital_allowance`, the capital allowances deducted.
- KR4: `total_profit`, the total profits on which company income tax is charged.
- KR5: `company_income_tax`.
- KR6: `development_levy`.

## Other companies

- D2: A company with an audited profit before tax of ₦500,000,000 donates computers to a federal university in Nigeria. It paid ₦18,000,000 for the computers, and their market value on the day of the donation is ₦12,000,000. It makes no other donation in the year. Give `donation_deduction`.

## Chargeable gains: give `chargeable_gain`

- G1: A sole trader bought a van on 3 January 2026 for ₦10,000,000 and used it only in the business. Capital allowance was made on it for the 2026 year of assessment. On 10 January 2027 the trader sold it to an unconnected buyer for ₦9,000,000. Give the chargeable gain on this sale.
- G2: An individual bought a plot of land in 2026 for ₦40,000,000 as an investment. In 2027 the individual sells part of the plot for ₦30,000,000. The market value of the part kept is ₦50,000,000 at the time of the sale. There are no other costs.
- G3: In 2027 an individual sells three cars, each used only privately, to three unconnected buyers. Each car is sold for ₦12,000,000 at a gain of ₦2,000,000. The individual disposes of no other asset in 2027.
- G4: In March 2026 an individual sold the house that was then the individual's only home, and claimed the exemption for that sale. In November 2027 the individual sells the next house, which has been the individual's only home since March 2026, on half an acre, with no business use, at a gain of ₦25,000,000.
- G5: In 2026 an individual's aunt, who is alive, gave her a plot of land with no consideration. In 2027 she gives the plot to her niece, also with no consideration. The plot's market value rose by ₦6,000,000 while she held it.

## VAT: give `vat_payable`

- V1: A VAT-registered fintech's figures for one month are as follows. Output VAT charged on its fees: ₦7,500,000. Input VAT on cloud services used only to earn those fees: ₦1,200,000. Input VAT on a new server, a fixed asset, used only to earn those fees: ₦900,000. Input VAT on legal services used only for its lending business, which earns interest on loans of money: ₦300,000. It has no credit brought forward. Give the VAT it must pay for the month.

Return one ```json block holding one object with one key per item, for example `{"KR1": {"donation_deduction": 0}, "D2": {"donation_deduction": 0}, "G1": {"chargeable_gain": 0}, "V1": {"vat_payable": 0}}`. Use plain numbers.
