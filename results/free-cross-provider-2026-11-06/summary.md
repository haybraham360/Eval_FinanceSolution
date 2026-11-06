# Results for run `free-cross-provider-2026-11-06`

| Model | Tier | Trials | Full pass rate | pass^k (tasks passed every trial) | pass@k (tasks passed once) | Mean score | Trial score SD (per task, mean) | Cost |
|---|---|---|---|---|---|---|---|---|
| free-nemotron-ultra | free | 12 | 42% | 5/12 | 5/12 | 70.2% | 0.000 | $0.00 |

## Mean score by task (full passes / trials)

| Task | free-nemotron-ultra |
|---|---|
| t10_pg_money_time | 66% (0/1) |
| t11_ng_tax_rules | 48% (0/1) |
| t12_ng_tax_interactions | 39% (0/1) |
| t1_payout_executor | 0% (0/1) |
| t2_webhook_convergence | 100% (1/1) |
| t3_fx_refund | 100% (1/1) |
| t4_interest_backvalue | 100% (1/1) |
| t5_wallet_repair | 100% (1/1) |
| t6_settlement_recon | 100% (1/1) |
| t7_pg_concurrency | 62% (0/1) |
| t8_pg_locks | 58% (0/1) |
| t9_pg_isolation | 71% (0/1) |

## Failing checks, across all models and trials

- **t10_pg_money_time**: `E5` x1, `E7` x1, `E13` x1, `E18` x1, `E19` x1, `E21` x1, `E26` x1, `E29` x1, `E30` x1, `E31` x1, `E32` x1, `E33` x1, `E37` x1, `E38` x1, `E42` x1, `E44` x1, `E45` x1, `E55` x1, `E56` x1, `E57` x1
- **t11_ng_tax_rules**: `P1` x1, `P2` x1, `P3` x1, `P4` x1, `C1` x1, `C2` x1, `C3` x1, `C4` x1, `G2` x1, `G3` x1, `G4` x1
- **t12_ng_tax_interactions**: `M1` x1, `M2` x1, `M3` x1, `M4` x1, `M5` x1, `M6` x1, `M7` x1, `G5` x1, `G8` x1, `G9` x1, `G10` x1
- **t1_payout_executor**: `happy_path` x1, `insufficient_sends_nothing_and_is_not_sticky` x1, `rejected_releases_funds_and_stays_failed` x1, `finished_payout_makes_no_money_moving_calls` x1, `timeout_keeps_funds_held` x1, `lookup_timeout_is_pending` x1, `lagging_landed_transfer_is_not_failed` x1, `never_landed_fails_after_window_and_releases` x1, `window_runs_from_most_recent_send` x1, `landed_then_retry_after_provider_forgot` x1, `kill_at_every_operation_retry_soon` x1, `kill_at_every_operation_retry_after_24h` x1, `duplicate_invocation_at_every_operation` x1, `returns_stored_truth_when_another_worker_wins` x1
- **t2_webhook_convergence**: none
- **t3_fx_refund**: none
- **t4_interest_backvalue**: none
- **t5_wallet_repair**: none
- **t6_settlement_recon**: none
- **t7_pg_concurrency**: `S2` x1, `S5` x1, `S8` x1, `S9` x1, `S11` x1
- **t8_pg_locks**: `L5` x1, `L6` x1, `L9` x1, `L12` x1, `L13` x1, `L15` x1, `L16` x1, `L19` x1
- **t9_pg_isolation**: `I2` x1, `I6` x1, `I9` x1, `I10` x1, `I11` x1

## Resolved models

- free-nemotron-ultra -> nvidia/nemotron-3-ultra-550b-a55b:free via Nvidia

## Trials with no gradable code or an unusual stop (0)

