# Results for run `free-smoke`

| Model | Tier | Trials | Full pass rate | pass^k (tasks passed every trial) | pass@k (tasks passed once) | Mean score | Trial score SD (per task, mean) | Cost |
|---|---|---|---|---|---|---|---|---|
| free-nemotron-3.5-super | free | 1 | 0% | 0/1 | 0/1 | 52.4% | 0.000 | $0.00 |
| free-nemotron-ultra | free | 1 | 0% | 0/1 | 0/1 | 52.4% | 0.000 | $0.00 |
| free-dots-3 | free | 1 | 0% | 0/1 | 0/1 | 38.1% | 0.000 | $0.00 |
| free-north-mini-code | free | 1 | 0% | 0/1 | 0/1 | 0.0% | 0.000 | $0.00 |

## Mean score by task (full passes / trials)

| Task | free-nemotron-3.5-super | free-nemotron-ultra | free-dots-3 | free-north-mini-code |
|---|---|---|---|---|
| t11_ng_tax_rules | 52% (0/1) | 52% (0/1) | 38% (0/1) | 0% (0/1) |

## Failing checks, across all models and trials

- **t11_ng_tax_rules**: `P1` x4, `P2` x4, `P3` x4, `P4` x4, `C2` x4, `C3` x4, `C4` x4, `G1` x4, `G4` x4, `C1` x3, `ST4` x2, `ST5` x2, `G2` x2, `G3` x2, `ST1` x1, `ST2` x1, `ST3` x1, `ST6` x1, `P5` x1, `V1` x1, `V2` x1

## Resolved models

- free-dots-3 -> dots-studio/dots-3-note-preview:free via AtlasCloud
- free-nemotron-3.5-super -> nvidia/nemotron-3.5-super-vl:free via Nvidia
- free-nemotron-ultra -> nvidia/nemotron-3-ultra-550b-a55b:free via Nvidia
- free-north-mini-code -> cohere/north-mini-code:free via Cohere

## Trials with no gradable code or an unusual stop (0)

