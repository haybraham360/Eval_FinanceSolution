# Additional evaluation report

These experiments extend Ledger-Eval without changing it. The original 12 tasks, their graders and the 108 original trials are untouched. `results/final/` re-grades identically, and the baseline is recorded in [`baseline_summary.md`](baseline_summary.md). Every new result is stored in a separately named run.

There are three kinds of evidence here, with different strengths. Keep them apart.

## Summary

| Model | Provider | Evidence | Tasks | Trials | Mean score | Perfect answers | Cost classification |
|---|---|---|---|---|---|---|---|
| Claude Opus 5.5 | Anthropic | Original benchmark | 12 | 36 | 100.0% | 36/36 | $0 on top of a Claude Pro subscription (CLI) |
| Claude Sonnet 5.5 | Anthropic | Original benchmark | 12 | 36 | 97.2% | 27/36 | $0 on top of a Claude Pro subscription (CLI) |
| Claude Haiku 5.5 | Anthropic | Original benchmark | 12 | 36 | 93.0% | 18/36 | $0 on top of a Claude Pro subscription (CLI) |
| Nemotron 3 Ultra | NVIDIA via OpenRouter | Cross-provider (exploratory) | 12 | 12 | 70.2% | 5/12 | Free: `:free` model priced at $0, OpenRouter-reported cost $0 |
| Claude Opus 5.5 | Anthropic | Advanced scenario t13 | 1 | 1 | 100% | 1/1 | Included subscription usage: no API key, no extra charge |
| Nemotron 3 Ultra | NVIDIA via OpenRouter | Advanced scenario t13 | 1 | 1 | 0% (no answer within the output limit) | 0/1 | Free, cost $0 |
| Gemma 4 31B | Google via OpenRouter | Not run | | 0 | | | Free endpoint rate-limited (HTTP 429) |

**Nothing was paid for.** No paid OpenRouter model was called: the `--free-only` guard checks live pricing and stops on any reported cost. The OpenRouter key's lifetime usage was $0 before and after. No Anthropic API key was used, and no credits or subscription changes were bought.

## 1. Original benchmark

These results are unchanged: 12 tasks, 3 Claude models, 3 trials each, 108 trials in all, run on 31 October 2026. See [`results/final/summary.md`](../final/summary.md) and the main [README](../../README.md). Since then:

- `python validate_graders.py` still passes for the original tasks (84 mutants).
- The new `scripts/verify_committed_results.py` re-grades all 155 committed historical trials in memory and finds every outcome identical.

## 2. Cross-provider check

This was one free model from NVIDIA, one trial per task, on the same 12 prompts and graders. The full write-up is in [`free_cross_provider_report.md`](free_cross_provider_report.md).

| Family | Nemotron 3 Ultra (1 trial each) | Opus / Sonnet / Haiku (3 trials each) |
|---|---|---|
| Financial engineering | 83.3% | 100 / 98.4 / 98.7% |
| PostgreSQL | 63.9% | 100 / 99.7 / 91.2% |
| Nigerian tax | 43.3% | 100 / 88.6 / 79.6% |

- The difficulty order matched Claude's: tax law was hardest.
- The model repeated Sonnet's and Haiku's signature tax mistakes: the ₦50m compensation limit (t11 G4), the accommodation cap (t12 M1) and the preceding-year insurance premium (t12 M3).
- This is **exploratory**: one trial, one other model, and different inference settings.

**A grader defect was found.** Nemotron's 0% on t1 came from the t1 grader's fake store, whose parameter names differ from the ones the prompt documents. A correctly named keyword call crashed every check.

- The original Claude results are unaffected: they passed arguments by position.
- A fix has been **proposed but not applied**, pending the author's approval. Until then, Nemotron's t1 result should be read as "not measured".

## 3. Advanced scenario t13

`t13_treasury_close_recovery` is a new, experimental month-end close task. It combines timeouts, duplicate and out-of-order events, reversals, FX snapshots, fee refunds, corrected settlement files and a period close in one ledger. See [`t13_validation_report.md`](t13_validation_report.md).

- **Grader validated:**
  - the reference and an independent blind solution both score 34/34;
  - all 33 deliberately wrong variants fail the check they target;
  - every expected value comes from hand arithmetic in `reference/t13_expected_results.md`, and an independent review confirmed it.
- **Opus passed** its single trial with 34/34, including stating the correct final position for the sample log. The task did not expose a limitation in Opus in this trial. One trial cannot measure how reliably it passes.
- **Nemotron 3 Ultra did not finish** within the 40,000-token output limit, so there was no answer to grade.
- t13 is **experimental**. It is not part of any headline score.

## Changes made to the project

- **New and unchanged:**
  - New task t13: prompt, grader, reference, hand arithmetic, a blind alternative solution and 33 mutants.
  - No existing task prompt or grader was changed.
- **Runner** (`run_eval.py`, `evalcore.py`; existing commands behave as before):
  - `--free-only` (live pricing check) and `--dry-run`;
  - a stop on any reported cost;
  - two-strike handling of rate limits (HTTP 429);
  - experimental tasks excluded from the default task list.
- **Validation:** `validate_graders.py` now validates all 13 tasks: 117 mutants, ALL GOOD.
- **Results and explorer:**
  - New runs: `free-cross-provider-2026-11-06`, `t13-opus-2026-11-06`, `t13-free-2026-11-06`.
  - `results/runs.json` labels which run is the headline and which are additional, so the explorer never mixes them.
  - A read-only explorer website (`frontend/`, `scripts/export_explorer_data.py`), rebuilt on every push by `.github/workflows/deploy-explorer.yml`.

## Not done

- **Gemma 4 was not run** (upstream rate limit). It can be resumed with the same run IDs once the free endpoint has capacity.
- **The t1 grader fix** is waiting for approval.
- **Only one trial per model** was run on t13. Three trials, as in the original benchmark, would be needed for a pass^k comparison.
- **An earlier local free-model run** (`results/free/`, from 2 to 5 November) was found in the working tree. It was not made in this session and has not been committed.
