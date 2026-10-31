# cli-sonnet / t10_pg_money_time / trial 1

- Requested: `sonnet`, resolved: `claude-haiku-5-5,claude-sonnet-5-5`, provider: claude-cli
- Run at 2026-10-31T14:57:38+00:00 with params `{}`
- Score 98%, full pass: False, finish: stop, error: None

## Failed checks

### `E37`

```
AssertionError: E37: expected '2592000.000000', got '2629800.000000'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 27, in check
    same(got, want, name)
    ~~~~^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/pg_answers.py", line 13, in same
    eq(text.strip(), str(want), label)
    ~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: E37: expected '2592000.000000', got '2629800.000000'

```

## Prompt

See `tasks/t10_pg_money_time/prompt.md`.

## Model output

```json
{
  "E1": "3",
  "E2": "2",
  "E3": "-3",
  "E4": "4",
  "E5": "2.68",
  "E6": "2.68",
  "E7": "1.01",
  "E8": "-3",
  "E9": "-1",
  "E10": "-3",
  "E11": "-4",
  "E12": "6.0",
  "E13": "7.0000000000000000",
  "E14": "0.33333333333333333333",
  "E15": "0.99999999999999999999",
  "E16": "0.9999999999999999",
  "E17": "1.0",
  "E18": "1.5000000000000000",
  "E19": "3",
  "E20": "2",
  "E21": "4",
  "E22": "ERROR 22P02",
  "E23": "ERROR 22003",
  "E24": "ERROR 22003",
  "E25": "999.99",
  "E26": "true",
  "E27": "NaN",
  "E28": "0",
  "E29": "2024-02-29 00:00:00",
  "E30": "2024-03-29 00:00:00",
  "E31": "2024-03-31 00:00:00",
  "E32": "2024-02-29 00:00:00",
  "E33": "2024-01-31 2024-02-29 2024-03-29 2024-04-29 2024-05-29",
  "E34": "29",
  "E35": "1 mon 2 days",
  "E36": "1 mon 1 day",
  "E37": "2629800.000000",
  "E38": "true",
  "E39": "2026-03-08 12:00:00-04",
  "E40": "2026-03-08 13:00:00-04",
  "E41": "2026-03-08 03:30:00-04",
  "E42": "2026-11-01 01:30:00-05",
  "E43": "2026-03-08 03:30:00-04",
  "E44": "2026-03-08 00:00:00-05",
  "E45": "2026-03-09 01:00:00-04",
  "E46": "1 day 01:00:00",
  "E47": "2026-02-28",
  "E48": "2026-03-01",
  "E49": "53",
  "E50": "2020",
  "E51": "2021",
  "E52": "2021-01",
  "E53": "3",
  "E54": "1,234.50",
  "E55": "###.##",
  "E56": "2025-02-28 00:00:00",
  "E57": "2024-02-29 00:00:00",
  "E58": "ERROR 22008"
}
```
