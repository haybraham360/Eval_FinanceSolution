# Results for run `t13-free-2026-11-06`

| Model | Tier | Trials | Full pass rate | pass^k (tasks passed every trial) | pass@k (tasks passed once) | Mean score | Trial score SD (per task, mean) | Cost |
|---|---|---|---|---|---|---|---|---|
| free-nemotron-ultra | free | 1 | 0% | 0/1 | 0/1 | 0.0% | 0.000 | $0.00 |

## Mean score by task (full passes / trials)

| Task | free-nemotron-ultra |
|---|---|
| t13_treasury_close_recovery | 0% (0/1) |

## Failing checks, across all models and trials

- **t13_treasury_close_recovery**: none

## Resolved models

- free-nemotron-ultra -> nvidia/nemotron-3-ultra-550b-a55b:free via Nvidia

## Trials with no gradable code or an unusual stop (1)

- free-nemotron-ultra / t13_treasury_close_recovery / trial 1: finish=length error=no fenced code block in output
