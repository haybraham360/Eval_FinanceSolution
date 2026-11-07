# Sources for t14, all from the Nigeria Tax Act, 2025 (Act No. 7)

The operative text was read from a full-text copy of the Act, "FINAL COPY NIGERIA TAX ACT 2025", published by TheNigeriaLawyer. Before relying on it, the copy was checked against every provision already verified for t11 and t12, and it matched all of them: the Fourth Schedule bands, s.30(2)(a)(v) and (vi), s.14(6), s.50, s.52, s.57 and the Eighth Schedule stamp duty. **The section references below must be checked against the gazetted Act before t14 is run on any model.**

| Items | Provision | Rule |
|---|---|---|
| KR1, D2 | s.164(5), (6) | Donations to qualifying Nigerian bodies are deductible, but the total "shall not exceed an amount equal to 10% of the profit before tax of that company for that year". A donation other than cash is valued at "the lower of the market value at the time of the donation or the consideration paid for the item when it was acquired" |
| KR2 | s.21(g), (l), (p) | No deduction for "depreciation or impairment of any fixed asset ... or an unrealised exchange difference", for a "penalty or fine imposed under any law", or for "any expense on which Value Added Tax is due under this Act but was not charged" |
| KR3 | s.27(2) proviso; First Schedule Part I, paras 6, 7 and Table I | Where VAT is due but not charged on an asset, "the relevant expenditure shall not be eligible as a qualifying capital expenditure". An allowance is made only if, at the end of the basis period, the person owns the asset and "used the asset for the purposes of its trade or business". The rates are software 25% (Class 3) and furniture and fittings 20% (Class 2) |
| KR4 | s.27(1), (5), (6) | Total profits are assessable profits less losses and capital allowances. A loss is deducted from later years' assessable profits until it is recouped. A loss from digital assets "shall only be deductible in determining the profits from the business relating to digital or virtual assets" |
| KR5 | s.56(b) | Companies other than small companies pay tax on total profits at 30% |
| KR6 | s.59(1) | "A development levy of 4% is imposed on the assessable profits of all companies ... other than small companies and non-resident companies". The base is assessable profits, the figure before losses and capital allowances in s.27(1), not total profits |
| G1 | s.39(a) | For an asset on which capital allowance has been made, "only the residue of that asset shall be deducted from the disposal proceeds". The residue is cost less allowances made (First Schedule para 8(1)) |
| G2 | s.41(2), (3) | In a part disposal, the cost is apportioned by A/(A+B), where A is the consideration for the part disposed of and B is the market value of the part kept |
| G3 | s.53 | A private motor vehicle is not a chargeable asset, but "the exemption ... shall be limited to not more than two motor vehicles by an individual in any year of assessment". Each car is sold to a different unconnected buyer for more than ₦5,000,000, so the chattels relief in s.52 does not apply |
| G4 | s.51(2) | The principal private residence exemption "shall be enjoyed once in the lifetime of an individual" |
| G5 | s.54(1) | Where a person disposes by way of gift of an asset acquired by way of gift, not on a devolution on death, "the gains accruing from the disposal shall not be chargeable gains" |
| V1 | s.156(5) and proviso (a); s.186 | Input tax on taxable supplies, "including services and fixed assets", is deductible only to the extent it is incurred in making taxable supplies. Interest on loans of money is exempt (verified for t12 V3), so input VAT used only for lending is not deductible |

## Workings

**Kudi Rails Ltd, year of assessment 2027**

- **KR1.** The cap is 10% × ₦600,000,000 profit before tax = ₦60,000,000. The donations are ₦75,000,000, so the deduction is ₦60,000,000.
- **KR2.** Start from profit before tax of ₦600,000,000. Add back the depreciation (₦90,000,000), the unrealised exchange loss (₦25,000,000), the fine (₦12,000,000), the fee on which VAT was not charged (₦40,000,000) and the donations as recorded (₦75,000,000). Then deduct the allowed donations of ₦60,000,000. That gives ₦782,000,000.
- **KR3.** Software is 25% × ₦120,000,000 = ₦30,000,000, and furniture is 20% × ₦50,000,000 = ₦10,000,000. The vehicles get nothing, because VAT was due but not charged. The building gets nothing, because it was not in use at the end of the basis period. The total is ₦40,000,000.
- **KR4.** ₦782,000,000 − ₦100,000,000 trading loss − ₦40,000,000 capital allowances = ₦642,000,000. The ₦30,000,000 digital-asset loss cannot be deducted, because the company has no digital-asset business.
- **KR5.** 30% × ₦642,000,000 = ₦192,600,000.
- **KR6.** 4% × ₦782,000,000 assessable profits = ₦31,280,000.

**The other items**

- **D2.** The value is the lower of ₦12,000,000 market value and ₦18,000,000 cost, which is ₦12,000,000. The cap is ₦50,000,000, so it does not bite.
- **G1.** The residue is ₦10,000,000 − 25% capital allowance of ₦2,500,000 = ₦7,500,000. The van gets no 2027 allowance, because it was not in use at the end of 2027. The gain is ₦9,000,000 − ₦7,500,000 = ₦1,500,000.
- **G2.** The cost of the part sold is ₦40,000,000 × 30/(30 + 50) = ₦15,000,000. The gain is ₦30,000,000 − ₦15,000,000 = ₦15,000,000.
- **G3.** Two cars are exempt. The gains are equal, so it does not matter which two. The third car's gain of ₦2,000,000 is chargeable.
- **G4.** The once-in-a-lifetime exemption was used in March 2026, so the full ₦25,000,000 gain is chargeable.
- **G5.** The land was acquired by gift and disposed of by gift, so the chargeable gain is 0.
- **V1.** ₦7,500,000 − ₦1,200,000 − ₦900,000 = ₦5,400,000. The ₦300,000 for lending is not deductible.

## Readings flagged for the author's review

- **KR6 levy base.** s.59 taxes "assessable profits". s.27(1) separates assessable profits from total profits, which come after losses and capital allowances, so the levy is computed on ₦782,000,000. Confirm this reading before any model is run.
- **Excluded as ambiguous.** The R&D cap in s.165(2) was left out, because it is arguable whether it limits ordinary R&D expenditure that s.20 allows anyway. Assets with allowances before 2026 were also avoided, because they raise the transitional rules in First Schedule para 23.
