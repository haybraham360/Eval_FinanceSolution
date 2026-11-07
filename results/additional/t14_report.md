# t14: a year-end Nigerian tax position where provisions cap and override each other

`t14_ng_tax_year_end` is a new **experimental** task. It is marked `"experimental": true`, so default runs still cover only the original 12 tasks, and it is not part of any headline score.

## Why it was built

Every failure recorded before t14 shared one pattern. In the original benchmark, Sonnet and Haiku failed where they had to **know Nigerian tax law themselves**, especially where one provision limits another; the free NVIDIA model failed in the same way. Opus passed every one of those tasks, and it also passed t13, where every rule is stated in the prompt, in **3 of 3 trials**.

t14 tests that weak spot more directly. It uses provisions of the Nigeria Tax Act, 2025 that t11 and t12 do not test, with no rule text in the prompt, as in t11 and t12. It asks for one chained company computation and seven independent items, 13 graded figures in all.

## Ground truth and its status

- **Source.** The provisions were read from a full-text copy of the Act. That copy was first checked against every provision already verified for t11 and t12 (tax bands, rent relief, accommodation cap, premium year, ₦50m compensation limit, ETR, chattels, stamp duty and the VAT rate), and it matched them all.
- **Sources file.** Each expected figure, its section and a short quote from the text are in [`reference/t14_sources.md`](../../reference/t14_sources.md), with step-by-step workings.
- **Not yet independently reviewed.** Unlike t11 and t12, the author has **not yet checked t14's readings against the gazetted Act**. Treat t14 results as experimental until that review is done.
- **Exclusions.** Provisions with two defensible readings were left out: the R&D cap in s.165, and assets subject to the transitional rules.

## Grader validation

`python validate_graders.py t14_ng_tax_year_end` reports that the reference answers pass all 13 checks, and that **all 18 mutants fail the item they target**. Each mutant applies one realistic misreading, carried through to the later figures. Examples are:

- capping donations at taxable profit;
- allowing depreciation or a fine;
- giving capital allowance on vehicles bought without the VAT that was due, or on an unfinished building;
- relieving the ring-fenced digital-asset loss;
- charging the levy on total profits;
- measuring a business asset's gain from cost;
- exempting all private cars;
- taxing a gift of a gift;
- refusing input VAT on fixed assets.

## Results

| Model | Route | Trials | Scores | Perfect answers |
|---|---|---|---|---|
| Claude Opus 5.5 (`claude-opus-5-5`) | Claude Code CLI, Pro subscription, `effort: high` | 3 | 46%, 46%, 54% (mean 48.7%) | **0 of 3** |
| Nemotron 3 Ultra (`nvidia/nemotron-3-ultra-550b-a55b:free`) | OpenRouter, free ($0) | 1 | 23% (3 of 13) | 0 of 1 |
| Gemma 4 31B (`google/gemma-4-31b-it:free`) | OpenRouter, free | 0 | Not run: HTTP 429, "temporarily rate-limited upstream" | |

[Opus results](../t14-opus-2026-11-06/scores.json), [free-model results](../t14-free-2026-11-06/scores.json).

### What Opus got wrong, and why it matters

Opus made the **same mistakes in every trial**, so they are not random slips.

| Item | Opus | Correct | What happened |
|---|---|---|---|
| KR1, the donation deduction | ₦70,200,000 | ₦60,000,000 | Opus capped donations at 10% of the company's **taxable** profit before the donation (₦702m). That is the basis of the **repealed** Companies Income Tax Act, s.25, which capped donations at 10% of total profits. The 2025 Act caps them at 10% of **profit before tax** (s.164(5)), and the prompt gives the audited profit before tax of ₦600m. |
| KR2, KR4, KR5, KR6 | consistent with ₦70.2m | ₦782m, ₦642m, ₦192.6m, ₦31.28m | These are knock-on effects of KR1 only. Opus's other company workings were correct: every disallowed expense, both capital-allowance traps, the ring-fenced digital-asset loss, and the levy on assessable profits. |
| G1, the gain on a business van | 0 | ₦1,500,000 | Opus treated the sale as giving no chargeable gain. That is consistent with measuring the gain from cost (₦10m) rather than from the **residue** after capital allowance (₦7.5m), which s.39(a) of the 2025 Act requires. |
| G5, a gift of a gift | ₦6,000,000 in 2 of 3 trials | 0 | Opus taxed the gift in two trials, against s.54(1). It got this right in trial 3. |

Opus answered D2, G2, G3, G4, V1 and KR3 correctly in every trial. That includes the two-car limit, the once-in-a-lifetime residence rule, the part-disposal formula, and input VAT on fixed assets.

**Finding.** t14 exposes a limitation that t1–t13 did not show: **Opus applies the repealed law where the 2025 Act changed a rule**, consistently. Because each grader check covers one figure, a single wrong rule can fail several checks. The score therefore understates how close Opus was: three distinct mistakes, two of them repeated in every trial.

Opus returned only the answer JSON, with no working. The explanations above are inferred from the numbers. The donation inference is exact: ₦70.2m is 10% of ₦702m, which is the taxable profit before the donation deduction.

## Free models

Nemotron 3 Ultra answered only D2, G2 and V1 correctly. It shared Opus's mistakes on G1 (residue) and G5 (gift of a gift). It also missed rules that Opus knew:

- the two-car limit (G3);
- the once-in-a-lifetime residence exemption (G4);
- the denial of capital allowances on unvatted and unused assets (KR3).

The ordering matches the main benchmark: Opus is clearly stronger than this model on Nigerian tax law, but t14 trips both of them.

## Limitations

- **Unreviewed readings.** The legal readings have not yet been reviewed against the gazetted Act by the author. The levy base in KR6 is flagged for review in the sources file. Opus agreed with the reading used.
- **Few trials.** Opus ran 3 trials, so pass^3 is measurable. Each free model ran 1.
- **Answers only.** The prompt asks for answers only, so the reasoning behind each mistake is inferred, not stated by the model.
