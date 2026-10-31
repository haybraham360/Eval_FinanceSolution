# Results for run `calibration2`

| Model | Tier | Trials | Full pass rate | pass^k (tasks passed every trial) | pass@k (tasks passed once) | Mean score | Trial score SD (per task, mean) | Cost |
|---|---|---|---|---|---|---|---|---|
| cli-opus | frontier | 3 | 100% | 3/3 | 3/3 | 100.0% | 0.000 | $0.00 |
| cli-sonnet | frontier | 3 | 67% | 2/3 | 2/3 | 99.4% | 0.000 | $0.00 |
| cli-haiku | small | 3 | 33% | 1/3 | 1/3 | 94.4% | 0.000 | $0.00 |

## Mean score by task (full passes / trials)

| Task | cli-opus | cli-sonnet | cli-haiku |
|---|---|---|---|
| t10_pg_money_time | 100% (1/1) | 98% (0/1) | 95% (0/1) |
| t8_pg_locks | 100% (1/1) | 100% (1/1) | 100% (1/1) |
| t9_pg_isolation | 100% (1/1) | 100% (1/1) | 88% (0/1) |

## Failing checks, across all models and trials

- **t10_pg_money_time**: `E37` x2, `E46` x1, `E55` x1
- **t8_pg_locks**: none
- **t9_pg_isolation**: `I8` x1, `I13` x1

## Resolved models

- cli-haiku -> claude-haiku-5-5 via claude-cli
- cli-opus -> claude-haiku-5-5,claude-opus-5-5 via claude-cli
- cli-sonnet -> claude-haiku-5-5,claude-sonnet-5-5 via claude-cli

## Trials with no gradable code or an unusual stop (0)

