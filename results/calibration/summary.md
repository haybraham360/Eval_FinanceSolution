# Results for run `calibration`

| Model | Tier | Trials | Full pass rate | pass^k (tasks passed every trial) | pass@k (tasks passed once) | Mean score | Trial score SD (per task, mean) | Cost |
|---|---|---|---|---|---|---|---|---|
| cli-opus | frontier | 7 | 100% | 7/7 | 7/7 | 100.0% | 0.000 | $0.00 |
| cli-sonnet | frontier | 7 | 100% | 7/7 | 7/7 | 100.0% | 0.000 | $0.00 |
| cli-haiku | small | 7 | 86% | 6/7 | 6/7 | 97.8% | 0.000 | $0.00 |

## Mean score by task (full passes / trials)

| Task | cli-opus | cli-sonnet | cli-haiku |
|---|---|---|---|
| t1_payout_executor | 100% (1/1) | 100% (1/1) | 100% (1/1) |
| t2_webhook_convergence | 100% (1/1) | 100% (1/1) | 100% (1/1) |
| t3_fx_refund | 100% (1/1) | 100% (1/1) | 100% (1/1) |
| t4_interest_backvalue | 100% (1/1) | 100% (1/1) | 100% (1/1) |
| t5_wallet_repair | 100% (1/1) | 100% (1/1) | 100% (1/1) |
| t6_settlement_recon | 100% (1/1) | 100% (1/1) | 100% (1/1) |
| t7_pg_concurrency | 100% (1/1) | 100% (1/1) | 85% (0/1) |

## Failing checks, across all models and trials

- **t1_payout_executor**: none
- **t2_webhook_convergence**: none
- **t3_fx_refund**: none
- **t4_interest_backvalue**: none
- **t5_wallet_repair**: none
- **t6_settlement_recon**: none
- **t7_pg_concurrency**: `S7` x1, `S8` x1

## Resolved models

- cli-haiku -> claude-haiku-5-5 via claude-cli
- cli-opus -> claude-haiku-5-5,claude-opus-5-5 via claude-cli
- cli-sonnet -> claude-haiku-5-5,claude-sonnet-5-5 via claude-cli

## Trials with no gradable code or an unusual stop (0)

