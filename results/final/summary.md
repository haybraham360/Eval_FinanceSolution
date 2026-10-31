# Results for run `final`

| Model | Tier | Trials | Full pass rate | pass^k (tasks passed every trial) | pass@k (tasks passed once) | Mean score | Trial score SD (per task, mean) | Cost |
|---|---|---|---|---|---|---|---|---|
| cli-opus | frontier | 36 | 100% | 12/12 | 12/12 | 100.0% | 0.000 | $0.00 |
| cli-sonnet | frontier | 36 | 75% | 8/12 | 10/12 | 97.2% | 0.016 | $0.00 |
| cli-haiku | small | 36 | 50% | 5/12 | 7/12 | 93.0% | 0.026 | $0.00 |

## Mean score by task (full passes / trials)

| Task | cli-opus | cli-sonnet | cli-haiku |
|---|---|---|---|
| t10_pg_money_time | 100% (3/3) | 99% (1/3) | 97% (0/3) |
| t11_ng_tax_rules | 100% (3/3) | 92% (0/3) | 78% (0/3) |
| t12_ng_tax_interactions | 100% (3/3) | 85% (0/3) | 81% (0/3) |
| t1_payout_executor | 100% (3/3) | 90% (2/3) | 100% (3/3) |
| t2_webhook_convergence | 100% (3/3) | 100% (3/3) | 92% (2/3) |
| t3_fx_refund | 100% (3/3) | 100% (3/3) | 100% (3/3) |
| t4_interest_backvalue | 100% (3/3) | 100% (3/3) | 100% (3/3) |
| t5_wallet_repair | 100% (3/3) | 100% (3/3) | 100% (3/3) |
| t6_settlement_recon | 100% (3/3) | 100% (3/3) | 100% (3/3) |
| t7_pg_concurrency | 100% (3/3) | 100% (3/3) | 92% (1/3) |
| t8_pg_locks | 100% (3/3) | 100% (3/3) | 93% (0/3) |
| t9_pg_isolation | 100% (3/3) | 100% (3/3) | 82% (0/3) |

## Failing checks, across all models and trials

- **t10_pg_money_time**: `E55` x2, `E37` x1, `E14` x1, `E15` x1, `E42` x1, `E46` x1
- **t11_ng_tax_rules**: `G4` x6, `ST5` x3, `P5` x3, `G2` x3, `ST3` x2, `C2` x1, `ST4` x1
- **t12_ng_tax_interactions**: `M3` x6, `E1` x6, `M1` x5, `G7` x1
- **t1_payout_executor**: `timeout_keeps_funds_held` x1, `lookup_timeout_is_pending` x1, `lagging_landed_transfer_is_not_failed` x1, `never_landed_fails_after_window_and_releases` x1
- **t2_webhook_convergence**: `decision_before_open_has_no_effect` x1, `arbitration_flip_restores_fee_position` x1, `big_mixed_scenario_random_orders` x1
- **t3_fx_refund**: none
- **t4_interest_backvalue**: none
- **t5_wallet_repair**: none
- **t6_settlement_recon**: none
- **t7_pg_concurrency**: `S7` x2, `S8` x1
- **t8_pg_locks**: `L9` x2, `L4` x1, `L7` x1
- **t9_pg_isolation**: `I13` x3, `I15` x3, `I8` x2, `I3` x1

## Resolved models

- cli-haiku -> claude-haiku-5-5 via claude-cli
- cli-opus -> claude-haiku-5-5,claude-opus-5-5 via claude-cli
- cli-sonnet -> claude-haiku-5-5,claude-sonnet-5-5 via claude-cli

## Trials with no gradable code or an unusual stop (0)

