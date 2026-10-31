#!/usr/bin/env python3
"""Runs the pg_scenarios.py definitions on a real server, three passes each, and records or checks
the observed answers. An outcome that differs between passes stops the run."""
import json
import sys
import time

import psycopg

import pg_scenarios as P
import verify_postgres as V

ROOT = V.ROOT
TASKS = {"t8_pg_locks": P.LOCKS, "t9_pg_isolation": P.ISOLATION}


def text(value):
    return None if value is None else str(value)


def execute(mon, s):
    mon.q("DROP SCHEMA public CASCADE")
    mon.q("CREATE SCHEMA public")
    mon.q("SELECT pg_advisory_unlock_all()")
    with psycopg.connect(dbname=V.DB, autocommit=True) as c:
        c.execute(P.SCHEMA)
        for r in s["rows"]:
            c.execute("insert into accounts values (%s,%s,%s)", r)
        if s["extra"]:
            c.execute(s["extra"])
    sessions = {n: V.S() for n in "ABC"}
    caps = {}
    for kind, name, sql, cap in s["steps"]:
        sess = sessions[name]
        if kind in ("run", "settle"):
            if kind == "settle":
                time.sleep(0.3)
            result = sess.q(sql)
            if cap:
                caps[cap] = {**result, "blocked": False}
        elif kind == "start":
            sess.start(sql)
            was = V.blocked(mon, sess)
            time.sleep(0.1)
            if cap:
                caps[cap] = {"session": name, "blocked": was}
                sess.cap = cap
        else:
            result = sess.finish()
            if getattr(sess, "cap", None):
                caps[sess.cap].update(result)
    out = {}
    for field, (kind, ref) in s["report"].items():
        if kind == "final":
            rows = mon.q(ref)["rows"]
            out[field] = text(rows[0][0]) if rows else None
        elif kind == "value":
            rows = caps[ref]["rows"]
            out[field] = text(rows[0][0]) if rows else None
        elif kind == "nrows":
            out[field] = len(caps[ref]["rows"])
        else:
            out[field] = caps[ref][{"rowcount": "rowcount", "sqlstate": "sqlstate", "tag": "status", "blocked": "blocked"}[kind]]
    for sess in sessions.values():
        sess.close()
    return out


def expressions(mon):
    out = {}
    for name, expr in P.EXPRESSIONS:
        result = mon.q(f"SELECT ({expr})::text")
        out[name] = f"ERROR {result['sqlstate']}" if result["sqlstate"] else result["rows"][0][0]
    return out


def main():
    admin = psycopg.connect(dbname="postgres", autocommit=True)
    version = admin.execute("show server_version").fetchone()[0]
    admin.execute(f"DROP DATABASE IF EXISTS {V.DB}")
    admin.execute(f"CREATE DATABASE {V.DB}")
    observed = {}
    unstable = []
    try:
        mon = V.S()
        mon.q("ALTER DATABASE ledger_eval_verify SET timezone = 'America/New_York'")
        mon.close()
        mon = V.S()
        for task, scenarios in TASKS.items():
            observed[task] = {}
            for s in scenarios:
                runs = [execute(mon, s) for _ in range(3)]
                if any(r != runs[0] for r in runs):
                    unstable.append((s["name"], runs))
                observed[task][s["name"]] = runs[0]
        mon.q("DROP SCHEMA public CASCADE")
        mon.q("CREATE SCHEMA public")
        mon.q(P.SCHEMA.splitlines()[0])
        mon.q("INSERT INTO accounts VALUES (1, 'ada', 100)")
        observed["t10_pg_money_time"] = expressions(mon)
        mon.close()
    finally:
        admin.execute(f"DROP DATABASE IF EXISTS {V.DB} WITH (FORCE)")
    for name, runs in unstable:
        print("UNSTABLE", name, runs)
    bad = 0
    for task, answers in observed.items():
        path = ROOT / "reference" / f"{task}.json"
        if "--write" in sys.argv:
            path.write_text(json.dumps(answers, indent=1) + "\n")
        expected = json.loads(path.read_text())
        wrong = [k for k in answers if expected.get(k) != answers[k]]
        bad += len(wrong)
        print(f"PostgreSQL {version} {task}: {len(answers) - len(wrong)}/{len(answers)} match the reference answers")
        for k in wrong:
            print(f"  MISMATCH {k}: reference {expected.get(k)} observed {answers[k]}")
    if "--show" in sys.argv:
        print(json.dumps(observed))
    sys.exit(1 if bad or unstable else 0)


if __name__ == "__main__":
    main()
