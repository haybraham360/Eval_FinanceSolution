# Results for run `calibration3`

| Model | Tier | Trials | Full pass rate | pass^k (tasks passed every trial) | pass@k (tasks passed once) | Mean score | Trial score SD (per task, mean) | Cost |
|---|---|---|---|---|---|---|---|---|
| cli-opus | frontier | 3 | 100% | 1/1 | 1/1 | 100.0% | 0.000 | $0.00 |
| cli-sonnet | frontier | 3 | 0% | 0/1 | 0/1 | 92.1% | 0.022 | $0.00 |
| cli-haiku | small | 3 | 0% | 0/1 | 0/1 | 79.4% | 0.059 | $0.00 |

## Mean score by task (full passes / trials)

| Task | cli-opus | cli-sonnet | cli-haiku |
|---|---|---|---|
| t11_ng_tax_rules | 100% (3/3) | 92% (0/3) | 79% (0/3) |

## Failing checks, across all models and trials

- **t11_ng_tax_rules**: `G4` x6, `ST5` x3, `G1` x3, `ST3` x2, `P5` x1, `P1` x1, `P2` x1, `C2` x1

## Resolved models

- cli-haiku -> claude-haiku-5-5 via claude-cli
- cli-opus -> claude-haiku-5-5,claude-opus-5-5 via claude-cli
- cli-sonnet -> claude-haiku-5-5,claude-sonnet-5-5 via claude-cli

## Trials with no gradable code or an unusual stop (0)

