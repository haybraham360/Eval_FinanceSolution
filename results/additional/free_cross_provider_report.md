# Cross-provider check on free models

This is an **exploratory run with one attempt per task**. The original benchmark ran three attempts per task, so the numbers below are not as statistically strong as the original 108-trial results and should not be read as a ranking.

## What was run

| Item | Value |
|---|---|
| Provider | OpenRouter, served by NVIDIA |
| Exact model ID | `nvidia/nemotron-3-ultra-550b-a55b:free` (label `free-nemotron-ultra` in `models.json`) |
| Run ID | `free-cross-provider-2026-11-06` |
| Date | 6 November 2026, trials from 19:36 to 20:39 UTC |
| Tasks | The same 12 tasks, prompts and graders as the original benchmark |
| Trials | 1 per task, 12 in all |
| Settings | The same as every OpenRouter run in this harness: the same system prompt, `max_tokens` 40,000, no extra parameters, temperature left at the provider default. The prompts carried no hints or task-specific instructions. |
| Concurrency | 1 worker, sequential |
| Command | `python run_eval.py run --run-id free-cross-provider-2026-11-06 --models free-nemotron-ultra --trials 1 --workers 1 --free-only` |

## Evidence that the run was free

- Before any call, `--free-only` checked OpenRouter's public model listing. Both the configured free models were priced `prompt: 0`, `completion: 0`, and `--free-only` refuses anything else. The same check rejected a paid model and a CLI model in a dry run.
- OpenRouter reported a cost of **$0** on every one of the 12 responses (`usage.cost` in each raw file). The run stops itself if any response reports a cost.
- The API key is on OpenRouter's free tier (`is_free_tier: true`), and its lifetime usage was **$0** before and after the run.
- The free-tier daily limit is 50 requests, and this run used 12.

## Results

**Overall:** mean score **78.5%**, with **6 of 12** tasks passed perfectly. These are the figures after the t1 grader fix described below; before the fix they were 70.2% and 5 of 12.

| Task family | Mean score | Tasks |
|---|---|---|
| Financial engineering | 100.0% | t1 100%, t2 100%, t3 100%, t4 100%, t5 100%, t6 100% |
| PostgreSQL | 63.9% | t7 61.5%, t8 57.9%, t9 70.6%, t10 65.5% |
| Nigerian tax | 43.3% | t11 47.6%, t12 38.9% |

The failed checks for every task are in [`results/free-cross-provider-2026-11-06/summary.md`](../free-cross-provider-2026-11-06/summary.md). The lowest-scoring answer for each task is in [`transcripts/free-cross-provider-2026-11-06/`](../../transcripts/free-cross-provider-2026-11-06/), for example:

- [t11 Nigerian tax rules](../../transcripts/free-cross-provider-2026-11-06/free-nemotron-ultra__t11_ng_tax_rules.md): personal income tax P1–P4, company tax C1–C4, and capital gains G2–G4
- [t12 interacting tax provisions](../../transcripts/free-cross-provider-2026-11-06/free-nemotron-ultra__t12_ng_tax_interactions.md): M1–M7, G5, G8, G9, G10
- [t10 PostgreSQL money and time](../../transcripts/free-cross-provider-2026-11-06/free-nemotron-ultra__t10_pg_money_time.md): 20 of 58 checks
- [t8 PostgreSQL locks](../../transcripts/free-cross-provider-2026-11-06/free-nemotron-ultra__t8_pg_locks.md): L5, L6, L9, L12, L13, L15, L16, L19

### The most important failure

The model repeated the same Nigerian tax mistakes that Claude Sonnet and Claude Haiku made in every trial of the original run:

| Check | Rule (from `reference/t11_sources.md`) | Also failed by |
|---|---|---|
| t11 G4 | s.50: compensation for loss of employment is exempt only up to ₦50m, and the excess is chargeable | Sonnet, Haiku |
| t12 M1 | s.14(6): rent-free accommodation is capped at 20% of employment income | Sonnet, Haiku |
| t12 M3 | s.30(2)(a)(v): the life-insurance deduction uses the premium paid in the *preceding* year | Sonnet, Haiku |

Ten of the model's failed checks match a check that a Claude model also failed in the original run.

### A grader defect found by this run, now fixed (t1)

Nemotron first scored 0% on t1, but that was **not a model failure**.

- **The defect.** The task prompt documents the store and provider methods as `update(payout_id, expected_status, new_status, **fields)`, `send(reference, dest, amount_minor)` and so on. The grader's fake store named the same parameters differently (`pid`, `expected`, `new`, `amount`, `ref`). Nemotron called the methods by the documented keyword names, so every call crashed with `TypeError: World.update() missing 2 required positional arguments`, and all 14 checks failed on that one crash.
- **The fix.** The fake's parameters now use exactly the names the prompt documents. No grading logic changed. `reference_alt/t1_payout_executor_keyword_args.py` calls every method by keyword and is kept as a regression test: it passes all 14 checks, and all 6 t1 mutants still fail the checks they target.
- **Effect.** All 155 trials of the main benchmark and calibration runs re-grade identically, because every Claude trial passed these values by position. Only three free-model trials changed, all from 0 to their real scores:
  - this run's Nemotron t1, which became **100%**;
  - two t1 trials in an earlier, uncommitted local run.

## Comparison with the original Claude results

| Model | Provider | Trials | Mean score | Engineering | PostgreSQL | Nigerian tax |
|---|---|---|---|---|---|---|
| Claude Opus 5.5 | Anthropic (CLI) | 36 | 100.0% | 100.0% | 100.0% | 100.0% |
| Claude Sonnet 5.5 | Anthropic (CLI) | 36 | 97.2% | 98.4% | 99.7% | 88.6% |
| Claude Haiku 5.5 | Anthropic (CLI) | 36 | 93.0% | 98.7% | 91.2% | 79.6% |
| Nemotron 3 Ultra (free) | NVIDIA (OpenRouter) | **12** | 78.5% | 100.0% | 63.9% | 43.3% |

The ordering of difficulty matches across providers: payment engineering is largely solved, PostgreSQL behaviour is harder, and Nigerian tax law is hardest. The specific tax mistakes recur across providers. This supports the original README's observation that the tax gap is not specific to Claude models. It is one trial, on one other model, so treat it as an indication, not a conclusion.

## Models that could not be run

| Model | Reason |
|---|---|
| `google/gemma-4-31b-it:free` | Selected as a second, different-vendor model. The free endpoint returned **HTTP 429 "temporarily rate-limited upstream"**. The harness paused, tried once more and gave up. The 12-task run was then stopped before making any request, to protect the free quota. No Gemma result exists. |

## Limitations

- **One trial per task.** The variance between trials is unknown. In an earlier local three-trial run, this model's score on some tasks changed between trials.
- **Free models can change.** Free endpoints can be withdrawn, re-routed, rate-limited or quietly updated. The same ID may not behave the same later.
- **Inference settings differ from the Claude runs.** The Claude models ran through the Claude Code CLI at `effort: high` (Haiku at default). Nemotron ran through OpenRouter with no reasoning-effort parameter, and the provider chose the defaults. Neither route records temperature.
- **The output caps differ.** OpenRouter runs are capped at 40,000 output tokens by the harness. The CLI route does not enforce that cap.
- **Latency.** Free inference was slow: up to 31 minutes for one trial, and about 93 minutes in total.
