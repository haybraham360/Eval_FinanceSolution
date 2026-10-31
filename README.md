# ledger-eval: where AI models get money wrong in Nigerian fintech

## Short description

**Domain:** Nigerian fintech: payment backends, ledgers, PostgreSQL behaviour, and the Nigeria Tax Act 2025 rules those systems must apply.

**Gap:** models follow money-handling rules well when the rules are written in the prompt. They do worse when the rule has to come from a local statute, especially where one provision overrides another. Sonnet-class models scored 98.4% on the engineering tasks but 88.6% on Nigerian tax law, with no full pass in 6 trials.

**Eval:** 12 tasks graded by deterministic code, with no LLM judge. PostgreSQL answers are observed on a real server, and Nigerian answers are tied to sections of the gazetted Act.

**Key findings:** across 108 trials, Claude Opus 5.5 scored 100%, Sonnet 5.5 scored 97.2% and Haiku 5.5 scored 93.0%. The eval therefore shows a limitation below the top model, not in it: Opus had no failures in the final run. Sonnet and Haiku repeatedly missed rules such as the prior-year premium deduction and the ₦50 million compensation limit.

## Video walkthrough

PENDING: add the public link here and in the submission form.

## Domain and expertise

Nigerian fintech engineering and compliance: double-entry bookkeeping, idempotency, PSP integrations, settlement, PostgreSQL transaction behaviour, stamp duty on electronic transfers, payroll income tax, VAT, company tax and chargeable gains.

## What it tests and why it matters

The eval measures whether a model can produce money-handling logic that holds up when rules interact, failures happen at the worst moment, or the governing rule is a local statute rather than a global engineering pattern. It is for teams deciding how far to trust AI-written code and AI compliance answers in payments, and for model builders who want a test beyond globally documented engineering.

The cost of failure is real and often quiet. Charging ₦50 duty on salary transfers overcharges every employee on a payroll run. Exempting all intra-bank transfers under-collects duty, because the Act exempts only self-transfers. Taxing a minimum-wage earner breaks payroll for the lowest-paid staff. A double payout is money that may not come back. A wrong belief about isolation levels gives a lost update that passes every single-threaded test and appears months later as an unexplained balance.

| Task | What the model must do | Why it's hard before any model is run |
|---|---|---|
| `t1_payout_executor` | Execute a payout across a non-transactional provider | A timeout is an unknown outcome, lookups lag by 15 minutes, and provider idempotency expires after 24 hours, so an intent must be recorded before sending. |
| `t2_webhook_convergence` | Project out-of-order webhooks into a position and an append-only journal | The position must depend only on the set of facts, yet the journal can't be rewritten. A late refund changes an already-reserved dispute. |
| `t3_fx_refund` | Journal a cross-currency refund on dealer quotes | The side of a two-way quote depends on trade direction and base currency. It also needs ISO 4217 units, cumulative rounding and exact arithmetic. |
| `t4_interest_backvalue` | Run monthly interest with back-valued transactions | A back-valued posting replays through a corrected history while actual postings stay immutable, with ACT/ACT ISDA and marginal tiers. |
| `t5_wallet_repair` | Repair a module from one reported symptom | There are seven defects and one reported symptom, so it needs an audit, not a spot fix. |
| `t6_settlement_recon` | Reconcile a processor file with the ledger | Daylight-saving cut-offs, corrected batches, accounting negatives and conditional chargeback netting all apply. |
| `t7_pg_concurrency` | Predict 13 PostgreSQL 14 schedules | Depends on what a blocked statement re-evaluates, which locks foreign keys conflict with, and when `COMMIT` silently rolls back. |
| `t8_pg_locks` | Predict 19 locking scenarios | Covers queues, triggers under concurrency, savepoints, `ON CONFLICT` locks and CTEs that never run. |
| `t9_pg_isolation` | Predict 17 isolation scenarios | Covers when a snapshot is taken, why a savepoint retry can't escape a serialization failure, and constraint timing. |
| `t10_pg_money_time` | Give exact results of 58 expressions | Numeric versus float rounding, month-end drift, daylight-saving gaps and ISO weeks all change money and billing dates. |
| `t11_ng_tax_rules` | Apply stamp duty, income tax, company tax, VAT and gains rules | The rule text isn't supplied. Old-law habits and news summaries give wrong answers, for example on who pays duty and which transfers are exempt. |
| `t12_ng_tax_interactions` | Solve cases that combine provisions | Needs caps, prior-year timing, ring-fenced crypto losses, the minimum effective tax rate, and exemptions that defer to another Part of the Act. |

## Setup and run

Requires Python 3.10+ on macOS or Linux. No Docker is needed.

```sh
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

python validate_graders.py   # prove the graders: free, no key, about 10 seconds
python run_eval.py regrade   # re-grade the included raw outputs: free, no key, reproduces results/final/summary.md
```

To run models yourself, use either route:

```sh
# Route 1, as used for the reported results: a logged-in `claude` CLI, no API key
python run_eval.py run --run-id my-run --models cli-opus,cli-sonnet,cli-haiku

# Route 2: OpenRouter. Copy .env.example to .env and set OPENROUTER_API_KEY
python run_eval.py run --run-id my-run --models claude-opus-5.5,gpt-6.1-sol,gemini-4-argon,grok-4.7
```

`OPENROUTER_API_KEY` is the only key, read from `.env` or the environment. `--tasks` and `--trials` narrow a run, and interrupted runs resume with the same `--run-id`. The `free-*` entries in `models.json` use OpenRouter's free tier with the same key.

To reproduce the PostgreSQL answers on a local server, run `python verify_postgres.py` and `python verify_scenarios.py`. They create and drop one database, `ledger_eval_verify`.

**Runtime and cost:** the 108-trial run took about an hour of active time with 3 parallel workers, split across two sessions because the first was interrupted. Saved trials were kept and the rest resumed. It cost $0 on top of a Claude Pro plan and used that plan's limits. The CLI reported about $11.63 as the equivalent API price: Opus $8.70, Sonnet $2.61, Haiku $0.32.

## Scoring

Every task is graded by code, with no LLM judge. Outcomes are graded, not methods, so any design that behaves correctly passes.

- A task score is the fraction of its named checks passed, which gives partial credit. A full pass means every check passed.
- Checks run independently, so one crash or hang fails only that check.
- `t1` kills the worker before and after every operation, and injects a duplicate invocation at every operation. `t2` replays every event permutation, or 720+ random ones for large sets, with duplicates and a JSON restart after each event.
- `t7` to `t10` compare exactly with behaviour observed on PostgreSQL 14.18 across three passes each.
- `t11` and `t12` compare with answers derived from the Act. Numbers must match within one kobo. Every item is cited in `reference/t11_sources.md`.
- Model code comes from the last fenced block and runs in a child process with no API keys in its environment, CPU and file-size limits, and network sockets disabled. On macOS it also runs under `sandbox-exec`.

**Grader validation** (`python validate_graders.py`):

- All 12 reference solutions score 100%.
- Two alternative `t1` designs also score 100%, one of them a model's valid design that an earlier grader wrongly failed. It stays as a regression test.
- 84 deliberately wrong answers in `mutants/` each fail the specific check they target.

**Errors found and fixed during the build:**

- A kill hook in the `t1` grader leaked into retries.
- Two hand-worked `t4` anchors were off by a factor of ten.
- A `t3` rounding check was too weak to catch per-refund rounding.
- A `t1` check stopped retrying too early and failed a valid design. This was found by reading the transcript.
- `t11` item C3 first tested turnover just above ₦50 million. The enacted Act says ₦50 million, but later reported guidance says ₦100 million, so two experts could disagree. It now uses ₦150 million, above both limits.

## Models tested and results

**Run date:** 31 October 2026, with 3 trials per task and the same tasks and graders for every model.

**Settings:** called through Claude Code CLI 2.1.294 with no tools, no project files, a fixed system prompt and no history between trials. Temperature was the default, because the CLI doesn't expose it. Effort was `high` for Opus and Sonnet and the default for Haiku.

| Model (exact ID) | Trials | Full pass rate | pass^k | pass@k | Mean score | Mean per-task SD | Equivalent API cost |
|---|---|---:|---:|---:|---:|---:|---:|
| `claude-opus-5-5` | 36 | 100% | 12/12 | 12/12 | 100.0% | 0.000 | $8.70 |
| `claude-sonnet-5-5` | 36 | 75% | 8/12 | 10/12 | 97.2% | 0.016 | $2.61 |
| `claude-haiku-5-5` | 36 | 50% | 5/12 | 7/12 | 93.0% | 0.026 | $0.32 |

pass^k counts tasks passed in all 3 trials, and pass@k counts tasks passed at least once.

| Task family | Opus | Sonnet | Haiku |
|---|---:|---:|---:|
| Engineering (`t1`-`t6`), rules stated | 100.0% (18/18) | 98.4% (17/18) | 98.7% (17/18) |
| PostgreSQL behaviour (`t7`-`t10`) | 100.0% (12/12) | 99.7% (10/12) | 91.2% (1/12) |
| Nigerian tax law (`t11`-`t12`) | 100.0% (6/6) | 88.6% (0/6) | 79.6% (0/6) |

Each cell is the mean score, with full passes out of trials in brackets. Per-task scores are in `results/final/summary.md`, raw outputs in `results/final/raw/`, and the lowest-scoring trial for each model and task in `transcripts/final/`.

**Limits of this evidence:**

- Only Claude models were tested. No non-Claude model has been run, so this says nothing about how other vendors compare.
- The CLI's usage report listed Haiku alongside Opus and Sonnet on those runs. A test call to Opus showed only Opus, and each answer is requested from the named model, but the saved raw files don't record the token split. The harness now saves it for future runs.
- The Nigerian tasks were added after earlier tasks showed no gap for Opus and Sonnet. All 12 tasks are reported and none was dropped. Early results are in `results/calibration*/`. In a run of an earlier `t11` draft, whose files were not kept, Opus gave one wrong number on item P3 with no working shown. It got P3 right in all 6 later trials.

## Failure analysis

Transcript links show the lowest-scoring trial for that model.

| Task | Who failed | How they failed | Transcript |
|---|---|---|---|
| `t11` | Sonnet 3/3, Haiku 3/3 | All 6 trials said ₦70m compensation has no chargeable gain. The employment exemption is subject to the Part holding the ₦50m limit in s.50, so ₦20m is chargeable. Sonnet exempted all intra-bank transfers in 2 trials, but the Act exempts only self-transfers. Haiku charged duty on salary and taxed a minimum-wage earner in all 3 trials. | [Sonnet](transcripts/final/cli-sonnet__t11_ng_tax_rules.md), [Haiku](transcripts/final/cli-haiku__t11_ng_tax_rules.md) |
| `t12` | Sonnet 3/3, Haiku 3/3 | All 6 trials deducted the 2026 life premium, though the Act allows the premium paid in the preceding year. All 6 got the minimum-tax top-up wrong, and 5 missed the 20% cap on employer accommodation. | [Sonnet](transcripts/final/cli-sonnet__t12_ng_tax_interactions.md), [Haiku](transcripts/final/cli-haiku__t12_ng_tax_interactions.md) |
| `t9` | Haiku 3/3 | Expected a unique violation from a deferrable constraint at statement end, and gave the wrong SQLSTATE for `PREPARE TRANSACTION` in all 3 trials. | [Haiku](transcripts/final/cli-haiku__t9_pg_isolation.md) |
| `t8` | Haiku 3/3 | Expected a foreign-key violation where REPEATABLE READ raises a serialization failure, among other misses. | [Haiku](transcripts/final/cli-haiku__t8_pg_locks.md) |
| `t7` | Haiku 2/3 | Missed that `ON CONFLICT DO NOTHING` under REPEATABLE READ fails when the conflicting row isn't visible to its snapshot. | [Haiku](transcripts/final/cli-haiku__t7_pg_concurrency.md) |
| `t10` | Sonnet 2/3, Haiku 3/3 | Near misses, mainly exact output format and ambiguous daylight-saving times. | [Sonnet](transcripts/final/cli-sonnet__t10_pg_money_time.md), [Haiku](transcripts/final/cli-haiku__t10_pg_money_time.md) |
| `t1` | Sonnet 1/3 | **Came close.** Every money-safety check passed, including kills at every operation. It returned the internal status `SENDING` instead of `PENDING`. The ticket lists the allowed values and says to return `PENDING`, though it also asks for "the true stored status", which may have invited this. | [Sonnet](transcripts/final/cli-sonnet__t1_payout_executor.md) |
| `t2` | Haiku 1/3 | Kept the ₦1,500 dispute fee when a `won` decision was in force, which the ticket says must reset it to 0. | [Haiku](transcripts/final/cli-haiku__t2_webhook_convergence.md) |
| `t3`-`t6` | None | All 36 trials passed across the three models, so these tasks show no gap. | |

Opus passed every task in the final run, so no failing Opus transcript exists. `t3` to `t6` have no failures from any model.

Sonnet scored below Haiku on `t1`, which the guide treats as a warning sign. It was one trial's return-value slip, not a capability difference, and Sonnet beats Haiku on the overall score.

## Main failure mode and hot take

The main failure is not bad logic. Below the top tier, models apply the general rule and miss the local exception. They know the tax bands, then miss that a premium counts from the prior year, that accommodation is capped at 20%, or that an exemption defers to a limit in another Part. These misses repeat across trials, so they are knowledge gaps rather than noise.

Sonnet scored 98.4% when rules were stated in the prompt and 88.6% when it had to recall them. That suggests a practical lesson for markets with thin public material: give the model the statute rather than trusting its memory. I haven't tested that directly, because the Nigerian tasks were not re-run with the Act supplied, and the two task families differ in other ways too. Cheaper models showed the bigger gap, and they are the ones teams are likely to deploy at volume.

This eval doesn't show the best model failing. Opus 5.5 passed all 36 final trials, so showing a limit at the top would take a different kind of test, such as agentic multi-step work or law newer than its training data.

## Prior work and sources

Everything here was built during the hackathon. No earlier benchmark tasks or datasets were used, and all engineering data is synthetic. The task format and validation approach follow the micro1 participant guide, which draws on Terminal-Bench, SWE-bench Verified, τ-bench and Anthropic's *Demystifying evals for AI agents*.

- PostgreSQL answers come from PostgreSQL 14.18 itself.
- Nigerian answers come from the Nigeria Tax Act, 2025 (No. 7, Official Gazette No. 117, 26 June 2025), cited item by item in `reference/t11_sources.md`.
- Runtime dependencies are Python's standard library plus `tzdata`, and `psycopg` for the PostgreSQL verification scripts.

## AI use

I led this project: I chose the fintech domain and the shift to Nigerian tax rules, decided which evaluation directions to pursue, and take responsibility for everything in it. AI coding tools assisted by drafting the tasks, graders, reference solutions, harness and documentation. PENDING: how I reviewed each task, reference answer and grading rule.
