#!/usr/bin/env python3
"""Writes tasks/t8, t9 and t10 prompts from pg_scenarios.py."""
from pathlib import Path

import pg_scenarios as P

ROOT = Path(__file__).resolve().parent
DESCRIBE = {
    "rowcount": lambda r, n: f"the row count reported for the step marked [{n[r]}]",
    "sqlstate": lambda r, n: f"the SQLSTATE raised by the step marked [{n[r]}], or null if it raised no error",
    "tag": lambda r, n: f"the command tag returned for the step marked [{n[r]}], or null if it raised an error",
    "blocked": lambda r, n: f"true if the step marked [{n[r]}] had to wait on another session, else false",
    "nrows": lambda r, n: f"the number of rows returned by the step marked [{n[r]}]",
    "value": lambda r, n: f"the first column of the first row returned by the step marked [{n[r]}], as a string, or null if no row came back",
    "final": lambda r, n: f"the first column of the first row of `{r}` run after everything else, as a string",
}
HEAD = """# Design review: what does PostgreSQL actually do?

Our payments service runs on **PostgreSQL 14.18** with default settings. Each scenario below comes from a bug class we have seen or fear. Predict the exact behaviour. Your answers will be compared with a real server, so answer for what the engine does, not for what would be sensible.

Before every scenario the database is reset to this schema. Tables hold only the rows the scenario lists, and no ANALYZE has run.

```sql
{schema}
```

`A`, `B` and `C` are separate connections with the default READ COMMITTED level. Anything outside `BEGIN ... COMMIT` autocommits. Steps run strictly in order. "starts" means the statement is sent and the next step runs without waiting for it, about 100ms later or as soon as the statement has clearly blocked. "finishes" means that session's started statement has returned. A step after a failed statement still runs. Steps marked with a number in brackets are the ones asked about.
"""


def render(s):
    marks, n = {}, 0
    for kind, who, sql, cap in s["steps"]:
        if cap:
            n += 1
            marks[cap] = n
    out = [f"**{s['name']}.**"]
    if s["rows"] != P.ADA:
        rows = ", ".join(f"`{r}`" for r in s["rows"]) or "none"
        out.append(f"Rows in `accounts`: {rows}.")
    else:
        out.append("Rows in `accounts`: `(1, 'ada', 100)`.")
    if s["extra"]:
        out.append(f"Extra setup:\n```sql\n{s['extra']}\n```")
    if s["note"]:
        out.append(s["note"])
    out.append("")
    for i, (kind, who, sql, cap) in enumerate(s["steps"], 1):
        tag = f" [{marks[cap]}]" if cap else ""
        if kind == "start":
            out.append(f"{i}. {who} starts{tag}: `{sql}`")
        elif kind == "finish":
            out.append(f"{i}. {who} finishes.")
        elif kind == "settle":
            out.append(f"{i}. 300ms later, {who}{tag}: `{sql}`")
        else:
            out.append(f"{i}. {who}{tag}: `{sql}`")
    out.append("\nReport:")
    for field, (kind, ref) in s["report"].items():
        out.append(f"- `{field}`: {DESCRIBE[kind](ref, marks)}")
    return "\n".join(out)


TAIL = "\nReturn one ```json block holding one object with one key per scenario, each an object with exactly the fields requested. Use JSON `true`, `false` and `null`, plain integers for row counts, SQLSTATEs as five-character strings, and strings where a string is asked for.\n"
for task, scenarios in (("t8_pg_locks", P.LOCKS), ("t9_pg_isolation", P.ISOLATION)):
    body = HEAD.format(schema=P.SCHEMA) + "\n" + "\n\n".join(render(s) for s in scenarios) + "\n" + TAIL
    (ROOT / "tasks" / task / "prompt.md").write_text(body)

lines = """# Design review: PostgreSQL money and calendar arithmetic

Our payments service computes amounts and billing dates in SQL on **PostgreSQL 14.18** with default settings and `timezone = 'America/New_York'`. The `accounts` table holds exactly one row.

For each id, give the exact text of `SELECT (<expression>)::text`. If the statement raises an error, give `ERROR <sqlstate>`, for example `ERROR 12345`. Answers are compared character for character with a real server, so answer for what the engine does.

""".splitlines()
lines += [f"- {name}: `{expr}`" for name, expr in P.EXPRESSIONS]
lines += ["", 'Return one ```json block holding one object mapping every id to its answer as a string, for example `{"E1": "...", "E2": "..."}`.', ""]
(ROOT / "tasks" / "t10_pg_money_time" / "prompt.md").write_text("\n".join(lines))
