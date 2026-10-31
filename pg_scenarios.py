"""Declarative PostgreSQL scenarios. One definition produces both the prompt text and the real-server
run, so what a model is asked and what the engine is observed doing cannot drift apart."""

SCHEMA = """CREATE TABLE accounts (id int PRIMARY KEY, owner text NOT NULL UNIQUE, balance int NOT NULL);
CREATE TABLE entries (id serial PRIMARY KEY, account_id int NOT NULL REFERENCES accounts(id), amount int NOT NULL);
CREATE TABLE idem (key text PRIMARY KEY, result text NOT NULL);"""

ADA = [(1, "ada", 100)]
TWO = [(1, "ada", 100), (2, "bo", 100)]


def run(session, sql, cap=None, settle=False):
    """settle=True waits 300ms first, so that anything just unblocked has time to finish."""
    return ("settle" if settle else "run", session, sql, cap)


def start(session, sql, cap=None):
    return ("start", session, sql, cap)


def finish(session):
    return ("finish", session, None, None)


def sc(name, steps, report, rows=ADA, extra=None, note=None):
    return dict(name=name, steps=steps, report=report, rows=rows, extra=extra, note=note)


# Report entries are field -> (kind, capture name or SQL).
# kinds: rowcount, sqlstate, tag, blocked, nrows, value (first column of first row, as text), final (SQL run after the steps).
LOCKS = [
    sc("L1", [run("A", "BEGIN"), run("A", "UPDATE accounts SET balance = 0 WHERE id = 1"),
              start("B", "SELECT id FROM accounts WHERE balance >= 100 ORDER BY id LIMIT 1 FOR UPDATE", "q"), run("A", "COMMIT"), finish("B")],
       {"b_blocked": ("blocked", "q"), "b_rows": ("nrows", "q")}, rows=TWO),
    sc("L2", [run("A", "BEGIN"), run("A", "UPDATE accounts SET balance = 0 WHERE id = 1"),
              start("B", "SELECT id FROM accounts WHERE balance >= 100 ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED", "q"), finish("B"), run("A", "COMMIT")],
       {"b_blocked": ("blocked", "q"), "b_rows": ("nrows", "q"), "b_id": ("value", "q")}, rows=TWO),
    sc("L3", [run("A", "BEGIN"), run("A", "UPDATE accounts SET balance = 10 WHERE id = 1"),
              start("B", "UPDATE accounts SET balance = balance - 5 WHERE id = (SELECT id FROM accounts ORDER BY balance DESC LIMIT 1)", "q"), run("A", "COMMIT"), finish("B")],
       {"b_rowcount": ("rowcount", "q"), "balance_1": ("final", "SELECT balance FROM accounts WHERE id = 1"), "balance_2": ("final", "SELECT balance FROM accounts WHERE id = 2")}, rows=[(1, "ada", 100), (2, "bo", 90)]),
    sc("L4", [run("A", "BEGIN"), run("A", "UPDATE accounts SET balance = balance - 80 WHERE id = 1"),
              start("B", "UPDATE accounts SET balance = balance - 80 WHERE id = 1 AND balance >= 80", "q"), run("A", "COMMIT"), finish("B"),
              run("A", "BEGIN"), run("A", "UPDATE accounts SET balance = balance + 80 WHERE id = 1"),
              start("B", "UPDATE accounts SET balance = balance + 1 WHERE id = 1", "r"), run("A", "COMMIT"), finish("B")],
       {"audit_rows": ("final", "SELECT count(*) FROM audit"), "audit_old_values": ("final", "SELECT string_agg(old_balance::text, ',' ORDER BY id) FROM audit")},
       extra="""CREATE TABLE audit (id serial PRIMARY KEY, old_balance int);
CREATE FUNCTION log_old() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN INSERT INTO audit (old_balance) VALUES (OLD.balance); RETURN NEW; END $$;
CREATE TRIGGER t BEFORE UPDATE ON accounts FOR EACH ROW EXECUTE FUNCTION log_old();"""),
    sc("L5", [run("A", "BEGIN"), run("A", "SAVEPOINT s"), run("A", "SELECT * FROM accounts WHERE id = 1 FOR UPDATE"),
              start("B", "UPDATE accounts SET balance = 1 WHERE id = 1", "q"), run("A", "ROLLBACK TO SAVEPOINT s"),
              run("C", "SELECT balance FROM accounts WHERE id = 1", "peek", settle=True), run("A", "COMMIT"), finish("B")],
       {"b_blocked": ("blocked", "q"), "balance_seen_by_c_before_a_commits": ("value", "peek")}),
    sc("L6", [run("A", "BEGIN"), run("B", "BEGIN"), run("A", "SELECT * FROM accounts WHERE id = 1 FOR SHARE"), run("B", "SELECT * FROM accounts WHERE id = 1 FOR SHARE"),
              start("A", "UPDATE accounts SET balance = balance - 1 WHERE id = 1", "x"), start("B", "UPDATE accounts SET balance = balance - 2 WHERE id = 1", "y"),
              finish("A"), finish("B"), run("A", "ROLLBACK"), run("B", "COMMIT")],
       {"a_sqlstate": ("sqlstate", "x"), "b_sqlstate": ("sqlstate", "y"), "final_balance": ("final", "SELECT balance FROM accounts WHERE id = 1")}, note="`deadlock_timeout` is the default 1s. B's UPDATE starts about 100ms after A's."),
    sc("L7", [run("A", "BEGIN"), run("A", "SELECT * FROM accounts WHERE id = 1 FOR KEY SHARE"),
              start("B", "UPDATE accounts SET balance = 5 WHERE id = 1", "x"), finish("B"),
              start("C", "UPDATE accounts SET id = 9 WHERE id = 1", "y"), run("A", "ROLLBACK"), finish("C")],
       {"balance_update_blocked": ("blocked", "x"), "id_update_blocked": ("blocked", "y")}),
    sc("L8", [run("A", "BEGIN"), run("A", "DELETE FROM accounts WHERE id = 1"), start("B", "INSERT INTO entries (account_id, amount) VALUES (1, 5)", "q"), run("A", "COMMIT"), finish("B")],
       {"b_blocked": ("blocked", "q"), "b_sqlstate": ("sqlstate", "q")}),
    sc("L9", [run("B", "BEGIN ISOLATION LEVEL REPEATABLE READ"), run("B", "SELECT count(*) FROM idem"), run("A", "DELETE FROM accounts WHERE id = 1"),
              run("B", "INSERT INTO entries (account_id, amount) VALUES (1, 5)", "q"), run("B", "ROLLBACK")],
       {"b_sqlstate": ("sqlstate", "q")}),
    sc("L10", [run("A", "BEGIN"), run("A", "INSERT INTO idem VALUES ('k', 'a')"),
               start("B", "INSERT INTO idem VALUES ('k', 'b') ON CONFLICT (key) DO UPDATE SET result = idem.result || '+' || excluded.result RETURNING result", "q"), run("A", "COMMIT"), finish("B")],
       {"b_returned": ("value", "q"), "stored": ("final", "SELECT result FROM idem WHERE key = 'k'")}),
    sc("L11", [run("A", "INSERT INTO idem VALUES ('k', 'a')"), run("A", "BEGIN"),
               run("A", "INSERT INTO idem VALUES ('k', 'z') ON CONFLICT (key) DO UPDATE SET result = 'z' WHERE idem.result = 'nope' RETURNING result", "q"),
               run("B", "SELECT * FROM idem WHERE key = 'k' FOR UPDATE NOWAIT", "r"), run("A", "ROLLBACK")],
       {"a_returned_rows": ("nrows", "q"), "b_sqlstate": ("sqlstate", "r")}),
    sc("L12", [run("A", "INSERT INTO idem VALUES ('k', '1'), ('k', '2') ON CONFLICT (key) DO UPDATE SET result = excluded.result", "x"),
               run("A", "INSERT INTO idem VALUES ('j', '1'), ('j', '2') ON CONFLICT (key) DO NOTHING", "y")],
       {"do_update_sqlstate": ("sqlstate", "x"), "do_nothing_sqlstate": ("sqlstate", "y"), "do_nothing_rowcount": ("rowcount", "y"), "stored_j": ("final", "SELECT result FROM idem WHERE key = 'j'")}),
    sc("L13", [run("A", "INSERT INTO docs (k) VALUES ('x')"), run("A", "INSERT INTO docs (k) VALUES ('x') ON CONFLICT (k) DO NOTHING"), run("A", "INSERT INTO docs (k) VALUES ('x') ON CONFLICT (k) DO NOTHING"),
               run("A", "INSERT INTO docs (k) VALUES ('y')")],
       {"id_of_y": ("final", "SELECT id FROM docs WHERE k = 'y'")}, extra="CREATE TABLE docs (id serial PRIMARY KEY, k text UNIQUE);"),
    sc("L14", [run("A", "SELECT * FROM accounts a LEFT JOIN entries e ON e.account_id = a.id FOR UPDATE", "x"), run("A", "SELECT DISTINCT balance FROM accounts FOR UPDATE", "y"),
               run("A", "SELECT * FROM accounts a LEFT JOIN entries e ON e.account_id = a.id FOR UPDATE OF a", "z")],
       {"join_sqlstate": ("sqlstate", "x"), "distinct_sqlstate": ("sqlstate", "y"), "join_of_a_sqlstate": ("sqlstate", "z")}),
    sc("L15", [run("A", "BEGIN"), run("A", "WITH x AS (SELECT id FROM accounts WHERE id = 1 FOR UPDATE) SELECT 1"), run("B", "SELECT * FROM accounts WHERE id = 1 FOR UPDATE NOWAIT", "q"), run("A", "ROLLBACK"),
               run("A", "BEGIN"), run("A", "WITH x AS (UPDATE accounts SET balance = 7 WHERE id = 1 RETURNING id) SELECT 1"), run("B", "SELECT * FROM accounts WHERE id = 1 FOR UPDATE NOWAIT", "r"), run("A", "COMMIT")],
       {"b_first_sqlstate": ("sqlstate", "q"), "b_second_sqlstate": ("sqlstate", "r"), "final_balance": ("final", "SELECT balance FROM accounts WHERE id = 1")}),
    sc("L16", [run("A", "WITH u1 AS (UPDATE accounts SET balance = balance + 1 WHERE id = 1 RETURNING 1), u2 AS (UPDATE accounts SET balance = balance + 10 WHERE id = 1 RETURNING 1) SELECT (SELECT count(*) FROM u1) AS a, (SELECT count(*) FROM u2) AS b", "q")],
       {"final_balance": ("final", "SELECT balance FROM accounts WHERE id = 1"), "statement_sqlstate": ("sqlstate", "q")}),
    sc("L17", [run("A", "INSERT INTO entries (account_id, amount) VALUES (1, 5), (1, 7)"), run("A", "UPDATE accounts a SET balance = a.balance + e.amount FROM entries e WHERE e.account_id = a.id", "q")],
       {"rowcount": ("rowcount", "q"), "entries_applied": ("final", "SELECT CASE balance WHEN 100 THEN 0 WHEN 112 THEN 2 ELSE 1 END FROM accounts WHERE id = 1")}),
    sc("L18", [run("A", "INSERT INTO entries (account_id, amount) VALUES (1, 5)"), run("A", "BEGIN ISOLATION LEVEL REPEATABLE READ"), run("A", "SELECT count(*) FROM idem"),
               run("B", "TRUNCATE entries"), run("A", "SELECT count(*) FROM entries", "q"), run("A", "ROLLBACK")],
       {"a_count": ("value", "q")}),
    sc("L19", [run("A", "BEGIN"), run("A", "DECLARE c CURSOR FOR SELECT balance FROM accounts WHERE id = 1"), run("A", "UPDATE accounts SET balance = 5 WHERE id = 1"), run("A", "FETCH c", "q"),
               run("A", "SELECT balance FROM accounts WHERE id = 1", "r"), run("A", "ROLLBACK")],
       {"fetched": ("value", "q"), "selected": ("value", "r")}),
]

ISOLATION = [
    sc("I1", [run("A", "BEGIN ISOLATION LEVEL REPEATABLE READ"), run("B", "UPDATE accounts SET balance = 7 WHERE id = 1"), run("A", "SELECT balance FROM accounts WHERE id = 1", "q"), run("A", "ROLLBACK")],
       {"a_saw": ("value", "q")}),
    sc("I2", [run("B", "BEGIN"), run("B", "SELECT pg_advisory_xact_lock(1)"), run("B", "UPDATE accounts SET balance = 7 WHERE id = 1"),
              run("A", "BEGIN ISOLATION LEVEL REPEATABLE READ"), start("A", "SELECT pg_advisory_xact_lock(1)", "w"), run("B", "COMMIT"), finish("A"),
              run("A", "SELECT balance FROM accounts WHERE id = 1", "q"), run("A", "UPDATE accounts SET balance = balance + 1 WHERE id = 1", "r"), run("A", "ROLLBACK")],
       {"a_blocked": ("blocked", "w"), "a_saw": ("value", "q"), "a_update_sqlstate": ("sqlstate", "r"), "final_balance": ("final", "SELECT balance FROM accounts WHERE id = 1")}),
    sc("I3", [run("B", "BEGIN"), run("B", "UPDATE accounts SET balance = 7 WHERE id = 1"),
              run("A", "BEGIN ISOLATION LEVEL REPEATABLE READ"), start("A", "LOCK TABLE accounts IN SHARE MODE", "w"), run("B", "COMMIT"), finish("A"),
              run("A", "SELECT balance FROM accounts WHERE id = 1", "q"), run("A", "ROLLBACK")],
       {"a_blocked": ("blocked", "w"), "a_saw": ("value", "q")}),
    sc("I4", [run("A", "BEGIN ISOLATION LEVEL REPEATABLE READ"), run("A", "SELECT count(*) FROM idem"), run("B", "BEGIN"), run("B", "UPDATE accounts SET balance = 7 WHERE id = 1"),
              start("A", "SELECT balance FROM accounts WHERE id = 1 FOR UPDATE", "q"), run("B", "ROLLBACK"), finish("A"), run("A", "ROLLBACK")],
       {"a_blocked": ("blocked", "q"), "a_sqlstate": ("sqlstate", "q"), "a_saw": ("value", "q")}),
    sc("I5", [run("A", "BEGIN ISOLATION LEVEL REPEATABLE READ"), run("A", "SELECT count(*) FROM idem"), run("A", "SAVEPOINT s"), run("B", "UPDATE accounts SET balance = 7 WHERE id = 1"),
              run("A", "UPDATE accounts SET balance = balance + 1 WHERE id = 1", "x"), run("A", "ROLLBACK TO SAVEPOINT s", "y"), run("A", "UPDATE accounts SET balance = balance + 1 WHERE id = 1", "z"), run("A", "ROLLBACK")],
       {"first_sqlstate": ("sqlstate", "x"), "rollback_to_sqlstate": ("sqlstate", "y"), "retry_sqlstate": ("sqlstate", "z")}),
    sc("I6", [run("A", "BEGIN ISOLATION LEVEL SERIALIZABLE"), run("B", "BEGIN ISOLATION LEVEL SERIALIZABLE"), run("A", "SELECT * FROM idem WHERE key = 'k'"), run("B", "SELECT * FROM idem WHERE key = 'k'"),
              run("A", "INSERT INTO idem VALUES ('k', 'a')"), start("B", "INSERT INTO idem VALUES ('k', 'b')", "q"), run("A", "COMMIT"), finish("B"), run("B", "ROLLBACK")],
       {"b_blocked": ("blocked", "q"), "b_sqlstate": ("sqlstate", "q")}),
    sc("I7", [run("A", "BEGIN ISOLATION LEVEL SERIALIZABLE"), run("B", "BEGIN ISOLATION LEVEL SERIALIZABLE"), run("A", "SELECT count(*) FROM accounts"), run("B", "SELECT count(*) FROM accounts"),
              run("A", "INSERT INTO idem VALUES ('k', 'a')"), start("B", "INSERT INTO idem VALUES ('k', 'b')", "q"), run("A", "COMMIT"), finish("B"), run("B", "ROLLBACK")],
       {"b_sqlstate": ("sqlstate", "q")}),
    sc("I8", [run("A", "BEGIN ISOLATION LEVEL SERIALIZABLE"), run("B", "BEGIN ISOLATION LEVEL SERIALIZABLE"), run("A", "SELECT balance FROM accounts WHERE id = 1"), run("B", "SELECT balance FROM accounts WHERE id = 2"),
              run("A", "UPDATE accounts SET balance = 1 WHERE id = 1"), run("B", "UPDATE accounts SET balance = 2 WHERE id = 2"), run("A", "COMMIT", "x"), run("B", "COMMIT", "y"), run("B", "ROLLBACK")],
       {"a_commit_sqlstate": ("sqlstate", "x"), "b_commit_sqlstate": ("sqlstate", "y")}, rows=TWO, note="Each transaction reads and writes only its own account. The table was just created and has not been analyzed."),
    sc("I9", [run("A", "BEGIN ISOLATION LEVEL SERIALIZABLE"), run("B", "BEGIN"), run("A", "SELECT sum(balance) FROM accounts"), run("B", "SELECT sum(balance) FROM accounts"),
              run("A", "UPDATE accounts SET balance = balance - 150 WHERE id = 1"), run("B", "UPDATE accounts SET balance = balance - 150 WHERE id = 2"), run("A", "COMMIT", "x"), run("B", "COMMIT", "y")],
       {"a_commit_sqlstate": ("sqlstate", "x"), "b_commit_sqlstate": ("sqlstate", "y"), "sum_after": ("final", "SELECT sum(balance) FROM accounts")}, rows=TWO),
    sc("I10", [run("A", "BEGIN ISOLATION LEVEL SERIALIZABLE"), run("B", "BEGIN ISOLATION LEVEL SERIALIZABLE"), run("A", "SELECT sum(balance) FROM accounts"), run("B", "SELECT sum(balance) FROM accounts"),
               run("A", "UPDATE accounts SET balance = balance - 150 WHERE id = 1"), run("B", "UPDATE accounts SET balance = balance - 150 WHERE id = 2"), run("A", "COMMIT", "x"),
               run("B", "SELECT 1", "y"), run("B", "COMMIT", "z"), run("B", "ROLLBACK")],
       {"a_commit_sqlstate": ("sqlstate", "x"), "b_select_sqlstate": ("sqlstate", "y"), "b_commit_sqlstate": ("sqlstate", "z"), "b_commit_tag": ("tag", "z")}, rows=TWO),
    sc("I11", [run("A", "BEGIN ISOLATION LEVEL SERIALIZABLE"), run("A", "SELECT batch FROM control"), run("B", "BEGIN ISOLATION LEVEL SERIALIZABLE"), run("B", "UPDATE control SET batch = batch + 1"), run("B", "COMMIT", "x"),
               run("C", "BEGIN ISOLATION LEVEL SERIALIZABLE READ ONLY"), run("C", "SELECT batch FROM control"), run("C", "SELECT count(*) FROM receipts WHERE batch = 1", "c"), run("C", "COMMIT", "y"),
               run("A", "INSERT INTO receipts VALUES (1, 100)", "i"), run("A", "COMMIT", "z"), run("A", "ROLLBACK")],
       {"b_commit_sqlstate": ("sqlstate", "x"), "c_commit_sqlstate": ("sqlstate", "y"), "a_insert_sqlstate": ("sqlstate", "i"), "a_commit_sqlstate": ("sqlstate", "z")}, rows=[],
       extra="CREATE TABLE control (batch int); INSERT INTO control VALUES (1); CREATE TABLE receipts (batch int, amount int);"),
    sc("I12", [run("A", "BEGIN"), run("A", "INSERT INTO d VALUES (1)", "x"), run("A", "SELECT count(*) FROM d", "y"), run("A", "COMMIT", "z")],
       {"insert_sqlstate": ("sqlstate", "x"), "visible_rows": ("value", "y"), "commit_sqlstate": ("sqlstate", "z"), "rows_after": ("final", "SELECT count(*) FROM d")}, rows=[],
       extra="CREATE TABLE d (k int UNIQUE DEFERRABLE INITIALLY DEFERRED); INSERT INTO d VALUES (1);"),
    sc("I13", [run("A", "UPDATE d1 SET k = k + 1", "x"), run("A", "UPDATE d2 SET k = k + 1", "y")],
       {"plain_unique_sqlstate": ("sqlstate", "x"), "deferrable_unique_sqlstate": ("sqlstate", "y")}, rows=[],
       extra="CREATE TABLE d1 (k int UNIQUE); INSERT INTO d1 VALUES (1), (2); CREATE TABLE d2 (k int UNIQUE DEFERRABLE INITIALLY IMMEDIATE); INSERT INTO d2 VALUES (1), (2);"),
    sc("I14", [run("A", "BEGIN"), run("A", "SET CONSTRAINTS ALL DEFERRED"), run("A", "INSERT INTO e2 VALUES (99)", "x"), run("A", "SET CONSTRAINTS ALL IMMEDIATE", "y"), run("A", "ROLLBACK")],
       {"insert_sqlstate": ("sqlstate", "x"), "set_immediate_sqlstate": ("sqlstate", "y")},
       extra="CREATE TABLE e2 (account_id int REFERENCES accounts(id) DEFERRABLE);"),
    sc("I15", [run("A", "BEGIN"), run("A", "PREPARE TRANSACTION 'p1'", "x"), run("A", "ROLLBACK")], {"sqlstate": ("sqlstate", "x")}, note="Default `max_prepared_transactions`."),
    sc("I16", [run("A", "BEGIN ISOLATION LEVEL READ COMMITTED"), run("A", "SELECT sum(balance) FROM accounts", "x"), run("B", "UPDATE accounts SET balance = 7 WHERE id = 1"),
               run("A", "SELECT sum(balance) FROM accounts", "y"), run("A", "SELECT stable_sum(), sum(balance) FROM accounts", "z"), run("A", "COMMIT")],
       {"first": ("value", "x"), "second": ("value", "y")}, extra="CREATE FUNCTION stable_sum() RETURNS bigint LANGUAGE sql STABLE AS 'SELECT sum(balance) FROM accounts';"),
    sc("I17", [run("A", "BEGIN"), run("A", "UPDATE accounts SET balance = 7 WHERE id = 1"), run("A", "SET LOCAL lock_timeout = '50ms'"), run("B", "SET lock_timeout = '50ms'"),
               run("B", "SELECT * FROM accounts WHERE id = 1 FOR UPDATE", "x"), run("B", "SET lock_timeout = 0"), run("B", "SET statement_timeout = '50ms'"), run("B", "SELECT * FROM accounts WHERE id = 1 FOR UPDATE", "y"), run("B", "SET statement_timeout = 0"), run("A", "ROLLBACK")],
       {"lock_timeout_sqlstate": ("sqlstate", "x"), "statement_timeout_sqlstate": ("sqlstate", "y")}),
]

# Single-session expressions: (id, SQL). The answer is exactly what psql would print, or ERROR <sqlstate>.
EXPRESSIONS = [
    ("E1", "round(2.5::numeric)"), ("E2", "round(2.5::float8)"), ("E3", "round(-2.5::numeric)"), ("E4", "round(3.5::float8)"),
    ("E5", "round(2.675::float8::numeric, 2)"), ("E6", "2.675::numeric(10,2)"), ("E7", "round(1.005::float8::numeric, 2)"),
    ("E8", "(-7) / 2"), ("E9", "(-7) % 2"), ("E10", "div(-7.0, 2)"), ("E11", "floor(-7 / 2.0)"), ("E12", "7 / 2 * 2.0"), ("E13", "2.0 * 7 / 2"),
    ("E14", "1.0 / 3"), ("E15", "1 / 3.0 * 3"), ("E16", "(SELECT sum(x) FROM (SELECT 0.1::float8 AS x FROM generate_series(1, 10)) s)"), ("E17", "(SELECT sum(x) FROM (SELECT 0.1 AS x FROM generate_series(1, 10)) s)"),
    ("E18", "(SELECT avg(x) FROM (VALUES (1), (2)) t(x))"), ("E19", "2.5::int"), ("E20", "2.5::float8::int"), ("E21", "3.5::float8::int"), ("E22", "'1.5'::int"), ("E23", "2147483647 + 1"),
    ("E24", "999.995::numeric(5,2)"), ("E25", "999.994::numeric(5,2)"), ("E26", "'NaN'::numeric > 1e300"), ("E27", "(SELECT sum(x) FROM (VALUES (1.0), ('NaN'::numeric)) t(x))"), ("E28", "(SELECT count(*) FROM accounts WHERE 1 NOT IN (2, NULL))"),
    ("E29", "'2024-01-31'::date + interval '1 month'"), ("E30", "'2024-01-31'::date + interval '1 month' + interval '1 month'"), ("E31", "'2024-01-31'::date + interval '2 months'"), ("E32", "'2024-03-31'::date - interval '1 month'"),
    ("E33", "(SELECT string_agg(d::date::text, ' ') FROM generate_series('2024-01-31'::date, '2024-05-31'::date, interval '1 month') d)"),
    ("E34", "'2024-03-01'::date - '2024-02-01'::date"), ("E35", "age('2024-03-31'::timestamp, '2024-02-29'::timestamp)"), ("E36", "age('2024-03-01'::timestamp, '2024-01-31'::timestamp)"), ("E37", "extract(epoch from interval '1 month')"), ("E38", "interval '30 days' = interval '1 month'"),
    ("E39", "'2026-03-07 12:00'::timestamptz + interval '1 day'"), ("E40", "'2026-03-07 12:00'::timestamptz + interval '24 hours'"), ("E41", "'2026-03-08 02:30'::timestamp AT TIME ZONE 'America/New_York'"), ("E42", "'2026-11-01 01:30'::timestamp AT TIME ZONE 'America/New_York'"),
    ("E43", "'2026-03-08 02:30'::timestamptz"), ("E44", "date_trunc('day', '2026-03-08 12:00'::timestamptz)"), ("E45", "date_trunc('day', '2026-03-08 12:00'::timestamptz) + interval '24 hours'"), ("E46", "'2026-11-01 00:00'::timestamptz + interval '1 day' - '2026-11-01 00:00'::timestamptz"),
    ("E47", "'2026-03-01 03:00+00'::timestamptz::date"), ("E48", "('2026-03-01 03:00+00'::timestamptz AT TIME ZONE 'UTC')::date"), ("E49", "extract(week from '2021-01-03'::date)"), ("E50", "extract(isoyear from '2021-01-03'::date)"), ("E51", "extract(year from '2021-01-03'::date)"), ("E52", "to_char('2021-01-03'::date, 'YYYY-WW')"), ("E53", "to_char(2.5, 'FM9')"), ("E54", "to_char(1234.5, 'FM9,999.00')"), ("E55", "to_char(12345.678, 'FM999.00')"), ("E56", "'2024-02-29'::date + interval '1 year'"), ("E57", "'2024-02-29'::date - interval '4 years' + interval '4 years'"), ("E58", "make_date(2024, 2, 30)"),
]
