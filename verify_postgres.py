#!/usr/bin/env python3
"""Runs every t7 schedule on a real PostgreSQL server with separate sessions and compares the
observed behaviour with reference/t7_pg_concurrency.json. The reference answers therefore come
from the engine, not from anyone's memory of it.

Needs a local server you may create a database on: pip install -r requirements.txt; python verify_postgres.py
Honours the usual PG* environment variables. It creates and drops one database, ledger_eval_verify.
"""
import json
import sys
import threading
import time
from pathlib import Path

import psycopg
from psycopg import errors  # noqa: F401

ROOT = Path(__file__).resolve().parent
DB = "ledger_eval_verify"
DDL = """
DROP TABLE IF EXISTS entries, idem, accounts;
DROP SEQUENCE IF EXISTS doc_no;
CREATE TABLE accounts (id int PRIMARY KEY, owner text NOT NULL UNIQUE, balance int NOT NULL);
CREATE TABLE entries (id serial PRIMARY KEY, account_id int NOT NULL REFERENCES accounts(id), amount int NOT NULL);
CREATE TABLE idem (key text PRIMARY KEY, result text NOT NULL);
"""


class S:
    def __init__(self, name=""):
        self.conn = psycopg.connect(dbname=DB, autocommit=True)
        self.pid = self.conn.info.backend_pid
        self.thread = None
        self.result = None

    def q(self, sql):
        """Run one statement. Returns dict(rows, rowcount, status, sqlstate)."""
        try:
            cur = self.conn.execute(sql)
            rows = cur.fetchall() if cur.description else []
            return {"rows": rows, "rowcount": cur.rowcount, "status": cur.statusmessage, "sqlstate": None}
        except psycopg.Error as exc:
            return {"rows": [], "rowcount": None, "status": None, "sqlstate": exc.sqlstate}

    def start(self, sql):
        def run():
            self.result = self.q(sql)
        self.thread = threading.Thread(target=run)
        self.thread.start()

    def finish(self):
        self.thread.join(15)
        assert not self.thread.is_alive(), "statement never finished"
        return self.result

    def close(self):
        self.conn.close()


def blocked(mon, s, wait=2.0):
    """True once the session is waiting on a heavyweight lock; False if its statement ended first."""
    deadline = time.time() + wait
    while time.time() < deadline:
        if s.thread and not s.thread.is_alive():
            return False
        rows = mon.q(f"select wait_event_type from pg_stat_activity where pid={s.pid}")["rows"]
        if rows and rows[0][0] == "Lock":
            return True
        time.sleep(0.02)
    return False


def fresh(mon, rows=((1, "ada", 100),), extra=""):
    mon.q("DROP TABLE IF EXISTS entries, idem, accounts")
    with psycopg.connect(dbname=DB, autocommit=True) as c:
        c.execute(DDL)
        for r in rows:
            c.execute("insert into accounts values (%s,%s,%s)", r)
        if extra:
            c.execute(extra)


def bal(mon, i=1):
    return mon.q(f"select balance from accounts where id={i}")["rows"][0][0]


def s1(mon, a, b):
    fresh(mon)
    a.q("BEGIN")
    a.q("UPDATE accounts SET balance = balance - 80 WHERE id = 1 AND balance >= 80")
    b.start("UPDATE accounts SET balance = balance - 80 WHERE id = 1 AND balance >= 80")
    was = blocked(mon, b)
    a.q("COMMIT")
    r = b.finish()
    return {"b_blocked": was, "b_rowcount": r["rowcount"], "final_balance": bal(mon)}


def s2(mon, a, b):
    fresh(mon)
    a.q("BEGIN")
    a.q("UPDATE accounts SET balance = balance + 10 WHERE id = 1")
    b.start("UPDATE accounts SET balance = (SELECT balance FROM accounts WHERE id = 1) + 10 WHERE id = 1")
    blocked(mon, b)
    a.q("COMMIT")
    r = b.finish()
    return {"b_rowcount": r["rowcount"], "final_balance": bal(mon)}


def s3(mon, a, b):
    fresh(mon, ((1, "ada", 100), (2, "bo", 90)))
    a.q("BEGIN")
    a.q("UPDATE accounts SET balance = 50 WHERE id = 1")
    b.start("SELECT id, balance FROM accounts ORDER BY balance DESC LIMIT 1 FOR UPDATE")
    blocked(mon, b)
    a.q("COMMIT")
    r = b.finish()
    return {"b_id": r["rows"][0][0], "b_balance": r["rows"][0][1]}


def s4(mon, a, b):
    fresh(mon)
    a.q("BEGIN ISOLATION LEVEL REPEATABLE READ")
    a.q("SELECT balance FROM accounts WHERE id = 1")
    b.q("UPDATE accounts SET balance = balance - 30 WHERE id = 1")
    r = a.q("UPDATE accounts SET balance = balance - 30 WHERE id = 1")
    a.q("ROLLBACK")
    return {"a_update_sqlstate": r["sqlstate"], "final_balance": bal(mon)}


def s5(mon, a, b):
    fresh(mon)
    r = a.q("WITH u AS (UPDATE accounts SET balance = balance - 30 WHERE id = 1 RETURNING balance) "
            "SELECT (SELECT balance FROM u) AS from_u, (SELECT balance FROM accounts WHERE id = 1) AS from_table")
    return {"from_u": r["rows"][0][0], "from_table": r["rows"][0][1], "final_balance": bal(mon)}


def s6(mon, a, b):
    fresh(mon)
    a.q("BEGIN")
    a.q("INSERT INTO idem VALUES ('k', 'a')")
    b.start("INSERT INTO idem VALUES ('k', 'b') ON CONFLICT (key) DO NOTHING RETURNING result")
    was = blocked(mon, b)
    a.q("COMMIT")
    r = b.finish()
    return {"b_blocked": was, "b_returned_rows": len(r["rows"]), "stored_result": mon.q("select result from idem where key='k'")["rows"][0][0]}


def s7(mon, a, b):
    fresh(mon)
    b.q("BEGIN ISOLATION LEVEL REPEATABLE READ")
    b.q("SELECT count(*) FROM idem")
    a.q("INSERT INTO idem VALUES ('k', 'a')")
    seen = b.q("SELECT result FROM idem WHERE key = 'k'")
    r = b.q("INSERT INTO idem VALUES ('k', 'b') ON CONFLICT (key) DO NOTHING RETURNING result")
    b.q("ROLLBACK")
    return {"b_select_rows": len(seen["rows"]), "b_insert_sqlstate": r["sqlstate"], "b_insert_returned_rows": len(r["rows"])}


def s8(mon, a, b):
    fresh(mon, ((1, "ada", 60), (2, "bo", 60)))
    for s in (a, b):
        s.q("BEGIN ISOLATION LEVEL SERIALIZABLE")
        s.q("SELECT sum(balance) FROM accounts")
    r1 = a.q("UPDATE accounts SET balance = balance - 100 WHERE id = 1")
    r2 = b.q("UPDATE accounts SET balance = balance - 100 WHERE id = 2")
    c1 = a.q("COMMIT")
    c2 = b.q("COMMIT")
    b.q("ROLLBACK")
    return {"a_update_sqlstate": r1["sqlstate"], "b_update_sqlstate": r2["sqlstate"], "a_commit_sqlstate": c1["sqlstate"], "b_commit_sqlstate": c2["sqlstate"], "sum_after": bal(mon, 1) + bal(mon, 2)}


def s9(mon, a, b):
    out = {}
    cases = {
        "balance_update": "UPDATE accounts SET balance = balance - 1 WHERE id = 1",
        "for_update": "SELECT * FROM accounts WHERE id = 1 FOR UPDATE",
        "for_no_key_update": "SELECT * FROM accounts WHERE id = 1 FOR NO KEY UPDATE",
        "owner_changed": "UPDATE accounts SET owner = 'ada2' WHERE id = 1",
        "owner_unchanged": "UPDATE accounts SET owner = owner WHERE id = 1",
    }
    for name, sql in cases.items():
        fresh(mon)
        a.q("BEGIN")
        a.q(sql)
        b.start("INSERT INTO entries (account_id, amount) VALUES (1, 5)")
        out[name] = blocked(mon, b)
        a.q("ROLLBACK")
        b.finish()
    return out


def s10(mon, a, b):
    fresh(mon)
    a.q("BEGIN")
    a.q("SELECT pg_advisory_lock(42)")
    a.q("SELECT pg_advisory_xact_lock(43)")
    a.q("ROLLBACK")
    r42 = b.q("SELECT pg_try_advisory_lock(42)")["rows"][0][0]
    r43 = b.q("SELECT pg_try_advisory_lock(43)")["rows"][0][0]
    a.q("SELECT pg_advisory_unlock_all()")
    b.q("SELECT pg_advisory_unlock_all()")
    return {"b_gets_42": r42, "b_gets_43": r43}


def s11(mon, a, b):
    fresh(mon)
    a.q("BEGIN")
    a.q("UPDATE accounts SET balance = balance - 10 WHERE id = 1")
    r1 = a.q("INSERT INTO accounts VALUES (1, 'dup', 0)")
    r2 = a.q("UPDATE accounts SET balance = balance - 10 WHERE id = 1")
    r3 = a.q("COMMIT")
    return {"insert_sqlstate": r1["sqlstate"], "second_update_sqlstate": r2["sqlstate"], "commit_sqlstate": r3["sqlstate"], "commit_tag": r3["status"], "final_balance": bal(mon)}


def s12(mon, a, b):
    fresh(mon, ((1, "ada", 90), (2, "bo", 150)))
    a.q("BEGIN")
    a.q("UPDATE accounts SET balance = 120 WHERE id = 1")
    a.q("UPDATE accounts SET balance = 50 WHERE id = 2")
    b.start("UPDATE accounts SET balance = balance - 10 WHERE balance >= 100")
    was = blocked(mon, b)
    a.q("COMMIT")
    r = b.finish()
    return {"b_blocked": was, "b_rowcount": r["rowcount"], "balance_1": bal(mon, 1), "balance_2": bal(mon, 2)}


def s13(mon, a, b):
    fresh(mon)
    a.q("BEGIN")
    a.q("DELETE FROM accounts WHERE id = 1")
    a.q("INSERT INTO accounts VALUES (1, 'ada', 5)")
    b.start("UPDATE accounts SET balance = balance + 7 WHERE id = 1")
    was = blocked(mon, b)
    a.q("COMMIT")
    r = b.finish()
    return {"b_blocked": was, "b_rowcount": r["rowcount"], "final_balance": bal(mon)}


SCENARIOS = {f"S{i}": fn for i, fn in enumerate([s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12, s13], 1)}


def main():
    admin = psycopg.connect(dbname="postgres", autocommit=True)
    version = admin.execute("show server_version").fetchone()[0]
    admin.execute(f"DROP DATABASE IF EXISTS {DB}")
    admin.execute(f"CREATE DATABASE {DB}")
    observed = {}
    try:
        for _ in range(3):  # three passes, so a timing-dependent result would show up as a mismatch
            mon = S()
            for name, fn in SCENARIOS.items():
                a, b = S(), S()
                got = fn(mon, a, b)
                if name in observed and observed[name] != got:
                    sys.exit(f"{name} is not stable: {observed[name]} vs {got}")
                observed[name] = got
                a.close()
                b.close()
            mon.close()
    finally:
        admin.execute(f"DROP DATABASE IF EXISTS {DB} WITH (FORCE)")
    path = ROOT / "reference" / "t7_pg_concurrency.json"
    if "--write" in sys.argv:
        path.write_text(json.dumps(observed, indent=1) + "\n")
    expected = json.loads(path.read_text())
    bad = [k for k in SCENARIOS if expected.get(k) != observed[k]]
    print(f"PostgreSQL {version}: {len(SCENARIOS) - len(bad)}/{len(SCENARIOS)} scenarios match the reference answers (3 passes each)")
    for k in bad:
        print(f"  MISMATCH {k}: reference {expected.get(k)} observed {observed[k]}")
    if "--show" in sys.argv:
        print(json.dumps(observed, indent=1))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
