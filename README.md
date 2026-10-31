# ledger-eval: where frontier models lose money in payment systems

## Short description

**Domain:** fintech backend engineering (ledgers, payouts, settlement, PostgreSQL concurrency).
**Gap:** models write payment code that looks right and passes the happy path, but breaks where two rules interact, such as a retry meeting a provider's 24-hour idempotency expiry, or a late refund shrinking an open dispute. They also misstate what PostgreSQL really does under concurrency.
**Eval:** 7 expert tasks graded by deterministic hidden tests, with fault injection at every operation. Reference answers for the PostgreSQL task are observed on a real server.

**Key findings:** PENDING, filled in only from the final run.

## Video walkthrough

PENDING: add the public link here and in the submission form.

## Domain and expertise

Payment and ledger backend engineering: double-entry bookkeeping, idempotency, PSP integrations, multi-currency settlement, interest accrual, and PostgreSQL transaction semantics.

## What it tests and why it matters

The eval measures whether a model can produce money-handling logic that holds up when rules interact and failures happen at the worst moment. It is meant for teams deciding how far to trust AI-written or AI-reviewed code in payments, and for model builders who want a realistic test of this kind of reasoning.

Failures here are expensive and quiet. A double payout is real money lost, and it often can't be recovered. A wrong FX or rounding rule produces a ledger that doesn't agree with the bank, and finance may spend days tracing it. A wrong belief about isolation levels leads to a lost update that passes every single-threaded test and surfaces months later as an unexplained balance.

| Task | What the model must do | Why it's hard before any model is run |
|---|---|---|
| `t1_payout_executor` | Execute a payout across a non-transactional provider | Three facts interact: a timeout is an unknown outcome, lookups lag by 15 minutes, and provider idempotency expires after 24 hours. "Retry with the same key" is safe only until then, so an intent must be recorded before sending. |
| `t2_webhook_convergence` | Project out-of-order PSP webhooks into a position and an append-only journal | The final position must depend only on the set of facts, yet the journal can never be rewritten. A late refund changes an already-reserved dispute. Facts can be re-issued under new event ids, and timestamps can carry different offsets. |
| `t3_fx_refund` | Journal a cross-currency refund on dealer quotes | Which side of a two-way quote applies depends on the trade direction and on which currency is the base. It also needs ISO 4217 minor units, cumulative rounding, and exact arithmetic above float precision. |
| `t4_interest_backvalue` | Run monthly interest with back-valued transactions | A back-valued posting must be replayed through a corrected history in which earlier capitalisations, and their compounding, also change, while actual postings stay immutable. It also combines ACT/ACT ISDA with marginal tiers. |
| `t5_wallet_repair` | Repair a module from one reported symptom | There are seven defects and only one is reported. An engineer who fixes the symptom and stops leaves six, so the task needs a full audit against the intended behaviour. |
| `t6_settlement_recon` | Reconcile a processor file with the ledger | Daylight-saving-aware cut-offs, corrected batches, accounting-style negatives, currency precision, and conditional chargeback netting all apply. |
| `t7_pg_concurrency` | Predict 13 exact PostgreSQL 14 schedules | The answers come from engine details that are rarely spelled out, such as what a blocked statement re-evaluates, which row locks foreign keys conflict with, and when an aborted transaction's `COMMIT` is silently a rollback. Every answer is observed on a real server. |

## Setup and run

Requires Python 3.10+ on macOS or Linux. No Docker. PostgreSQL is only needed to re-verify the t7 answers.

```sh
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

python validate_graders.py                 # prove the graders: free, no key, about 2 minutes
python run_eval.py regrade                 # re-grade the included raw outputs: free, no key
cp .env.example .env                       # then set OPENROUTER_API_KEY in .env
python run_eval.py run --run-id my-run     # all models, 3 trials per task
python verify_postgres.py                  # optional: needs a local PostgreSQL server
```

`OPENROUTER_API_KEY` is the only key, and it is only needed for live runs. A live run uses `models.json`, and `--models`, `--tasks` and `--trials` narrow it. Interrupted runs resume with the same `--run-id`.

**Runtime and cost:** PENDING, measured from the final run.

## Scoring

Every task is graded by code, with no LLM judge. Outcomes are graded, not methods, so any design that behaves correctly passes.

- A task score is the fraction of its named checks passed, which gives partial credit. A full pass means every check passed.
- Checks run independently, so one crash or hang fails only that check.
- `t1` and `t2` go beyond examples. `t1` kills the worker before and after every operation it performs, and injects a duplicate invocation at every operation. `t2` replays every event permutation, or 720+ random ones for large sets, with duplicates and a JSON restart after each event.
- `t7` scores each scenario by exact match against engine-observed behaviour. Run `verify_postgres.py` to reproduce those answers.
- Model code is extracted from the last fenced block, then run in a child process with no API keys in its environment, CPU and file-size limits, and network sockets disabled. On macOS it also runs under `sandbox-exec`.
- Reporting follows the guide: pass rate, pass^k (passed every trial), pass@k (passed at least once) and spread.

**Grader validation** (`python validate_graders.py`):

- Every reference solution scores 100%.
- An independent alternative `t1` design also scores 100%, which shows the grader doesn't force one method.
- 57 deliberately wrong solutions in `mutants/` each fail the specific check they target. In `t5`, each real defect is re-injected on its own.

This process caught real errors during the build, including a kill hook leaking into retries in the `t1` grader, two hand-worked `t4` anchors off by a factor of ten, and a `t3` rounding check too weak to catch per-refund rounding. All were fixed.

## Models tested and results

PENDING. Exact model IDs, run date, settings and scores come from `results/final/summary.md`. Raw outputs are in `results/final/raw/`, and the worst trial for each model and task is in `transcripts/final/`.

## Failure analysis

PENDING, written from the transcripts of the final run.

## Main failure mode and hot take

PENDING.

## Prior work and sources

Everything here was built during the hackathon. No earlier benchmark tasks or datasets were used, and all data is synthetic. The task format and validation approach follow the micro1 participant guide, which draws on Terminal-Bench, SWE-bench Verified, τ-bench and Anthropic's *Demystifying evals for AI agents*. `t7` reference answers come from PostgreSQL 14.18 itself. Python's standard library is the only runtime dependency, apart from `psycopg` for `verify_postgres.py` and the `tzdata` package.

## AI use

I led this project: I chose the fintech domain and the shift to Nigerian tax rules, decided which evaluation directions to pursue, and take responsibility for everything in it. AI coding tools assisted by drafting the tasks, graders, reference solutions, harness and documentation. PENDING: how I reviewed each task, reference answer and grading rule.
