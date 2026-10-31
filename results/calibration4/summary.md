# Results for run `calibration4`

| Model | Tier | Trials | Full pass rate | pass^k (tasks passed every trial) | pass@k (tasks passed once) | Mean score | Trial score SD (per task, mean) | Cost |
|---|---|---|---|---|---|---|---|---|
| cli-opus | frontier | 2 | 100% | 1/1 | 1/1 | 100.0% | 0.000 | $0.00 |
| cli-sonnet | frontier | 2 | 0% | 0/1 | 0/1 | 88.9% | 0.000 | $0.00 |

## Mean score by task (full passes / trials)

| Task | cli-opus | cli-sonnet |
|---|---|---|
| t12_ng_tax_interactions | 100% (2/2) | 89% (0/2) |

## Failing checks, across all models and trials

- **t12_ng_tax_interactions**: `M3` x2, `E1` x2

## Resolved models

- cli-opus -> claude-haiku-5-5,claude-opus-5-5 via claude-cli
- cli-sonnet -> claude-haiku-5-5,claude-sonnet-5-5 via claude-cli

## Trials with no gradable code or an unusual stop (0)

