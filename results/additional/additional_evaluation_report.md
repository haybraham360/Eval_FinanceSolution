# Additional evaluation report

These experiments extend Ledger-Eval without changing its results. The original 12 tasks and the 108 original trials keep their scores, and `results/final/` re-grades identically. The baseline is recorded in [`baseline_summary.md`](baseline_summary.md). One grader was corrected (t1, described below), and that correction changed no original result. Every new result is stored in a separately named run.

There are four kinds of evidence here, with different strengths. Keep them apart.

## Summary

| Model | Provider | Evidence | Tasks | Trials | Mean score | Perfect answers | Cost classification |
|---|---|---|---|---|---|---|---|
| Claude Opus 5.5 | Anthropic | Original benchmark | 12 | 36 | 100.0% | 36/36 | $0 on top of a Claude Pro subscription (CLI) |
| Claude Sonnet 5.5 | Anthropic | Original benchmark | 12 | 36 | 97.2% | 27/36 | $0 on top of a Claude Pro subscription (CLI) |
| Claude Haiku 5.5 | Anthropic | Original benchmark | 12 | 36 | 93.0% | 18/36 | $0 on top of a Claude Pro subscription (CLI) |
| Nemotron 3 Ultra | NVIDIA via OpenRouter | Cross-provider (exploratory) | 12 | 12 | 78.5% | 6/12 | Free: `:free` model priced at $0, OpenRouter-reported cost $0 |
| Claude Opus 5.5 | Anthropic | t13 treasury close (experimental) | 1 | 3 | 100% | **3/3** | Included subscription usage |
| Nemotron 3 Ultra | NVIDIA via OpenRouter | t13 treasury close (experimental) | 1 | 1 | 0% (no answer within the output limit) | 0/1 | Free, cost $0 |
| Claude Opus 5.5 | Anthropic | t14 Nigerian tax year end (experimental) | 1 | 3 | 48.7% | **0/3** | Included subscription usage |
| Nemotron 3 Ultra | NVIDIA via OpenRouter | t14 Nigerian tax year end (experimental) | 1 | 1 | 23.1% | 0/1 | Free, cost $0 |
| Gemma 4 31B | Google via OpenRouter | Not run | | 0 | | | Free endpoint rate-limited (HTTP 429) |

**Nothing was paid for.** No paid OpenRouter model was called: the `--free-only` guard checks live pricing and stops on any reported cost. The OpenRouter key's lifetime usage is $0. No Anthropic API key was used, and no credits or subscription changes were bought.

## 1. Original benchmark

These results are unchanged: 12 tasks, 3 Claude models, 3 trials each, 108 trials in all, run on 31 October 2026. See [`results/final/summary.md`](../final/summary.md) and the main [README](../../README.md).

- `python validate_graders.py` passes for every task.
- `scripts/verify_committed_results.py` re-grades every committed trial in memory and finds every outcome identical to what is saved.

## 2. Cross-provider check

This was one free NVIDIA model, one trial per task, on the same 12 prompts and graders. The full write-up is in [`free_cross_provider_report.md`](free_cross_provider_report.md).

| Family | Nemotron 3 Ultra (1 trial each) | Opus / Sonnet / Haiku (3 trials each) |
|---|---|---|
| Financial engineering | 100.0% | 100 / 98.4 / 98.7% |
| PostgreSQL | 63.9% | 100 / 99.7 / 91.2% |
| Nigerian tax | 43.3% | 100 / 88.6 / 79.6% |

- Payments engineering was solved; PostgreSQL behaviour and Nigerian tax law were where the model lost marks.
- It repeated Sonnet's and Haiku's signature tax mistakes: the ₦50m compensation limit, the accommodation cap and the preceding-year insurance premium.
- This is **exploratory**: one trial, one other model.

**The t1 grader was corrected.** Its fake store named its parameters differently from the task prompt, so a correctly named keyword call crashed every check.

- The parameter names now match the prompt, and a keyword-argument solution is kept as a regression test.
- No Claude result changed, because those trials passed arguments by position.
- Nemotron's t1 went from 0% to 100%, which raised its overall score from 70.2% to 78.5%.

## 3. Advanced scenario t13: stated rules

`t13_treasury_close_recovery` is a month-end close where timeouts, duplicate and out-of-order events, reversals, FX snapshots, fee refunds, corrected settlement files and a period close all interact. **Every rule is stated in the prompt.** See [`t13_validation_report.md`](t13_validation_report.md).

- **The grader is validated:**
  - the reference and an independent blind solution score 34/34;
  - all 33 mutants fail the check they target;
  - the expected values are worked by hand and confirmed by an independent review.
- **Opus passed all three trials, 34/34 each.** With stated rules, it is reliable even across a long chain of interacting events.
- **Nemotron did not finish** within its 40,000-token output limit.

## 4. Advanced scenario t14: law the model must know

`t14_ng_tax_year_end` is a Nigerian fintech's year-end tax position, built on Nigeria Tax Act 2025 provisions that t11 and t12 do not test. It includes no rule text, and one provision limits another throughout. See [`t14_report.md`](t14_report.md).

- **The grader is validated:** the reference passes all 13 checks, and all 18 mutants fail the item they target.
- **The legal readings are not yet reviewed.** They were taken from a full-text copy of the Act that matched every provision already verified for t11 and t12. The author has not yet checked them against the gazetted Act.
- **Opus failed all three trials (46%, 46%, 54%).**
  - In every trial it capped company donations at 10% of **taxable** profit, the basis of the repealed Companies Income Tax Act, instead of 10% of profit before tax as s.164(5) of the 2025 Act requires.
  - In every trial it measured a business asset's gain without using the residue after capital allowances (s.39(a)).
  - In two trials it taxed a gift of a gift (s.54).
- **This is the first task in the benchmark that Opus fails.** It fails where the 2025 Act changed a rule and the model applies the old one.
- **Nemotron scored 23%.** It also missed provisions that Opus knew.

## Changes made to the project

- **New tasks.**
  - t13 has a prompt, grader, reference, hand arithmetic, a blind alternative solution and 33 mutants.
  - t14 has a prompt, reference answers, a sources file with workings, a grader and 18 mutants.
  - Both are experimental and excluded from default runs.
- **Grader correction.** t1's fake store now uses the parameter names the prompt documents. This changed no Claude result.
- **Runner.**
  - `--free-only` performs a live pricing check, and `--dry-run` prints the plan.
  - A run stops on any reported cost.
  - Rate limits (HTTP 429) are retried at most twice.
  - Experimental tasks are excluded from the default list.
- **Validation.** `validate_graders.py` covers every task.
- **New runs.** `free-cross-provider-2026-11-06`, `t13-opus-2026-11-06`, `t13-free-2026-11-06`, `t14-opus-2026-11-06` and `t14-free-2026-11-06`. `results/runs.json` labels the headline run and the additional ones.
- **Explorer.** The read-only explorer website (`frontend/`) is rebuilt on every push. It now includes the plain-language database explanations in `reference/plain_explanations.md`, checked on PostgreSQL 14.18.

## Not done

- **t14's legal review.** The author's review of t14's readings against the gazetted Act is outstanding. Until it is done, t14 results are provisional.
- **Gemma 4** could not be run, because its free endpoint was rate-limited.
- **An earlier local free-model run** (`results/free/`, 2–5 November) was not made in this session and has not been committed. It has been re-graded locally after the t1 fix.
