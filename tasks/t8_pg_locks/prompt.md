# Design review: what does PostgreSQL actually do?

Our payments service runs on **PostgreSQL 14.18** with default settings. Each scenario below comes from a bug class we have seen or fear. Predict the exact behaviour. Your answers will be compared with a real server, so answer for what the engine does, not for what would be sensible.

Before every scenario the database is reset to this schema. Tables hold only the rows the scenario lists, and no ANALYZE has run.

```sql
CREATE TABLE accounts (id int PRIMARY KEY, owner text NOT NULL UNIQUE, balance int NOT NULL);
CREATE TABLE entries (id serial PRIMARY KEY, account_id int NOT NULL REFERENCES accounts(id), amount int NOT NULL);
CREATE TABLE idem (key text PRIMARY KEY, result text NOT NULL);
```

`A`, `B` and `C` are separate connections with the default READ COMMITTED level. Anything outside `BEGIN ... COMMIT` autocommits. Steps run strictly in order. "starts" means the statement is sent and the next step runs without waiting for it, about 100ms later or as soon as the statement has clearly blocked. "finishes" means that session's started statement has returned. A step after a failed statement still runs. Steps marked with a number in brackets are the ones asked about.

**L1.**
Rows in `accounts`: `(1, 'ada', 100)`, `(2, 'bo', 100)`.

1. A: `BEGIN`
2. A: `UPDATE accounts SET balance = 0 WHERE id = 1`
3. B starts [1]: `SELECT id FROM accounts WHERE balance >= 100 ORDER BY id LIMIT 1 FOR UPDATE`
4. A: `COMMIT`
5. B finishes.

Report:
- `b_blocked`: true if the step marked [1] had to wait on another session, else false
- `b_rows`: the number of rows returned by the step marked [1]

**L2.**
Rows in `accounts`: `(1, 'ada', 100)`, `(2, 'bo', 100)`.

1. A: `BEGIN`
2. A: `UPDATE accounts SET balance = 0 WHERE id = 1`
3. B starts [1]: `SELECT id FROM accounts WHERE balance >= 100 ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED`
4. B finishes.
5. A: `COMMIT`

Report:
- `b_blocked`: true if the step marked [1] had to wait on another session, else false
- `b_rows`: the number of rows returned by the step marked [1]
- `b_id`: the first column of the first row returned by the step marked [1], as a string, or null if no row came back

**L3.**
Rows in `accounts`: `(1, 'ada', 100)`, `(2, 'bo', 90)`.

1. A: `BEGIN`
2. A: `UPDATE accounts SET balance = 10 WHERE id = 1`
3. B starts [1]: `UPDATE accounts SET balance = balance - 5 WHERE id = (SELECT id FROM accounts ORDER BY balance DESC LIMIT 1)`
4. A: `COMMIT`
5. B finishes.

Report:
- `b_rowcount`: the row count reported for the step marked [1]
- `balance_1`: the first column of the first row of `SELECT balance FROM accounts WHERE id = 1` run after everything else, as a string
- `balance_2`: the first column of the first row of `SELECT balance FROM accounts WHERE id = 2` run after everything else, as a string

**L4.**
Rows in `accounts`: `(1, 'ada', 100)`.
Extra setup:
```sql
CREATE TABLE audit (id serial PRIMARY KEY, old_balance int);
CREATE FUNCTION log_old() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN INSERT INTO audit (old_balance) VALUES (OLD.balance); RETURN NEW; END $$;
CREATE TRIGGER t BEFORE UPDATE ON accounts FOR EACH ROW EXECUTE FUNCTION log_old();
```

1. A: `BEGIN`
2. A: `UPDATE accounts SET balance = balance - 80 WHERE id = 1`
3. B starts [1]: `UPDATE accounts SET balance = balance - 80 WHERE id = 1 AND balance >= 80`
4. A: `COMMIT`
5. B finishes.
6. A: `BEGIN`
7. A: `UPDATE accounts SET balance = balance + 80 WHERE id = 1`
8. B starts [2]: `UPDATE accounts SET balance = balance + 1 WHERE id = 1`
9. A: `COMMIT`
10. B finishes.

Report:
- `audit_rows`: the first column of the first row of `SELECT count(*) FROM audit` run after everything else, as a string
- `audit_old_values`: the first column of the first row of `SELECT string_agg(old_balance::text, ',' ORDER BY id) FROM audit` run after everything else, as a string

**L5.**
Rows in `accounts`: `(1, 'ada', 100)`.

1. A: `BEGIN`
2. A: `SAVEPOINT s`
3. A: `SELECT * FROM accounts WHERE id = 1 FOR UPDATE`
4. B starts [1]: `UPDATE accounts SET balance = 1 WHERE id = 1`
5. A: `ROLLBACK TO SAVEPOINT s`
6. 300ms later, C [2]: `SELECT balance FROM accounts WHERE id = 1`
7. A: `COMMIT`
8. B finishes.

Report:
- `b_blocked`: true if the step marked [1] had to wait on another session, else false
- `balance_seen_by_c_before_a_commits`: the first column of the first row returned by the step marked [2], as a string, or null if no row came back

**L6.**
Rows in `accounts`: `(1, 'ada', 100)`.
`deadlock_timeout` is the default 1s. B's UPDATE starts about 100ms after A's.

1. A: `BEGIN`
2. B: `BEGIN`
3. A: `SELECT * FROM accounts WHERE id = 1 FOR SHARE`
4. B: `SELECT * FROM accounts WHERE id = 1 FOR SHARE`
5. A starts [1]: `UPDATE accounts SET balance = balance - 1 WHERE id = 1`
6. B starts [2]: `UPDATE accounts SET balance = balance - 2 WHERE id = 1`
7. A finishes.
8. B finishes.
9. A: `ROLLBACK`
10. B: `COMMIT`

Report:
- `a_sqlstate`: the SQLSTATE raised by the step marked [1], or null if it raised no error
- `b_sqlstate`: the SQLSTATE raised by the step marked [2], or null if it raised no error
- `final_balance`: the first column of the first row of `SELECT balance FROM accounts WHERE id = 1` run after everything else, as a string

**L7.**
Rows in `accounts`: `(1, 'ada', 100)`.

1. A: `BEGIN`
2. A: `SELECT * FROM accounts WHERE id = 1 FOR KEY SHARE`
3. B starts [1]: `UPDATE accounts SET balance = 5 WHERE id = 1`
4. B finishes.
5. C starts [2]: `UPDATE accounts SET id = 9 WHERE id = 1`
6. A: `ROLLBACK`
7. C finishes.

Report:
- `balance_update_blocked`: true if the step marked [1] had to wait on another session, else false
- `id_update_blocked`: true if the step marked [2] had to wait on another session, else false

**L8.**
Rows in `accounts`: `(1, 'ada', 100)`.

1. A: `BEGIN`
2. A: `DELETE FROM accounts WHERE id = 1`
3. B starts [1]: `INSERT INTO entries (account_id, amount) VALUES (1, 5)`
4. A: `COMMIT`
5. B finishes.

Report:
- `b_blocked`: true if the step marked [1] had to wait on another session, else false
- `b_sqlstate`: the SQLSTATE raised by the step marked [1], or null if it raised no error

**L9.**
Rows in `accounts`: `(1, 'ada', 100)`.

1. B: `BEGIN ISOLATION LEVEL REPEATABLE READ`
2. B: `SELECT count(*) FROM idem`
3. A: `DELETE FROM accounts WHERE id = 1`
4. B [1]: `INSERT INTO entries (account_id, amount) VALUES (1, 5)`
5. B: `ROLLBACK`

Report:
- `b_sqlstate`: the SQLSTATE raised by the step marked [1], or null if it raised no error

**L10.**
Rows in `accounts`: `(1, 'ada', 100)`.

1. A: `BEGIN`
2. A: `INSERT INTO idem VALUES ('k', 'a')`
3. B starts [1]: `INSERT INTO idem VALUES ('k', 'b') ON CONFLICT (key) DO UPDATE SET result = idem.result || '+' || excluded.result RETURNING result`
4. A: `COMMIT`
5. B finishes.

Report:
- `b_returned`: the first column of the first row returned by the step marked [1], as a string, or null if no row came back
- `stored`: the first column of the first row of `SELECT result FROM idem WHERE key = 'k'` run after everything else, as a string

**L11.**
Rows in `accounts`: `(1, 'ada', 100)`.

1. A: `INSERT INTO idem VALUES ('k', 'a')`
2. A: `BEGIN`
3. A [1]: `INSERT INTO idem VALUES ('k', 'z') ON CONFLICT (key) DO UPDATE SET result = 'z' WHERE idem.result = 'nope' RETURNING result`
4. B [2]: `SELECT * FROM idem WHERE key = 'k' FOR UPDATE NOWAIT`
5. A: `ROLLBACK`

Report:
- `a_returned_rows`: the number of rows returned by the step marked [1]
- `b_sqlstate`: the SQLSTATE raised by the step marked [2], or null if it raised no error

**L12.**
Rows in `accounts`: `(1, 'ada', 100)`.

1. A [1]: `INSERT INTO idem VALUES ('k', '1'), ('k', '2') ON CONFLICT (key) DO UPDATE SET result = excluded.result`
2. A [2]: `INSERT INTO idem VALUES ('j', '1'), ('j', '2') ON CONFLICT (key) DO NOTHING`

Report:
- `do_update_sqlstate`: the SQLSTATE raised by the step marked [1], or null if it raised no error
- `do_nothing_sqlstate`: the SQLSTATE raised by the step marked [2], or null if it raised no error
- `do_nothing_rowcount`: the row count reported for the step marked [2]
- `stored_j`: the first column of the first row of `SELECT result FROM idem WHERE key = 'j'` run after everything else, as a string

**L13.**
Rows in `accounts`: `(1, 'ada', 100)`.
Extra setup:
```sql
CREATE TABLE docs (id serial PRIMARY KEY, k text UNIQUE);
```

1. A: `INSERT INTO docs (k) VALUES ('x')`
2. A: `INSERT INTO docs (k) VALUES ('x') ON CONFLICT (k) DO NOTHING`
3. A: `INSERT INTO docs (k) VALUES ('x') ON CONFLICT (k) DO NOTHING`
4. A: `INSERT INTO docs (k) VALUES ('y')`

Report:
- `id_of_y`: the first column of the first row of `SELECT id FROM docs WHERE k = 'y'` run after everything else, as a string

**L14.**
Rows in `accounts`: `(1, 'ada', 100)`.

1. A [1]: `SELECT * FROM accounts a LEFT JOIN entries e ON e.account_id = a.id FOR UPDATE`
2. A [2]: `SELECT DISTINCT balance FROM accounts FOR UPDATE`
3. A [3]: `SELECT * FROM accounts a LEFT JOIN entries e ON e.account_id = a.id FOR UPDATE OF a`

Report:
- `join_sqlstate`: the SQLSTATE raised by the step marked [1], or null if it raised no error
- `distinct_sqlstate`: the SQLSTATE raised by the step marked [2], or null if it raised no error
- `join_of_a_sqlstate`: the SQLSTATE raised by the step marked [3], or null if it raised no error

**L15.**
Rows in `accounts`: `(1, 'ada', 100)`.

1. A: `BEGIN`
2. A: `WITH x AS (SELECT id FROM accounts WHERE id = 1 FOR UPDATE) SELECT 1`
3. B [1]: `SELECT * FROM accounts WHERE id = 1 FOR UPDATE NOWAIT`
4. A: `ROLLBACK`
5. A: `BEGIN`
6. A: `WITH x AS (UPDATE accounts SET balance = 7 WHERE id = 1 RETURNING id) SELECT 1`
7. B [2]: `SELECT * FROM accounts WHERE id = 1 FOR UPDATE NOWAIT`
8. A: `COMMIT`

Report:
- `b_first_sqlstate`: the SQLSTATE raised by the step marked [1], or null if it raised no error
- `b_second_sqlstate`: the SQLSTATE raised by the step marked [2], or null if it raised no error
- `final_balance`: the first column of the first row of `SELECT balance FROM accounts WHERE id = 1` run after everything else, as a string

**L16.**
Rows in `accounts`: `(1, 'ada', 100)`.

1. A [1]: `WITH u1 AS (UPDATE accounts SET balance = balance + 1 WHERE id = 1 RETURNING 1), u2 AS (UPDATE accounts SET balance = balance + 10 WHERE id = 1 RETURNING 1) SELECT (SELECT count(*) FROM u1) AS a, (SELECT count(*) FROM u2) AS b`

Report:
- `final_balance`: the first column of the first row of `SELECT balance FROM accounts WHERE id = 1` run after everything else, as a string
- `statement_sqlstate`: the SQLSTATE raised by the step marked [1], or null if it raised no error

**L17.**
Rows in `accounts`: `(1, 'ada', 100)`.

1. A: `INSERT INTO entries (account_id, amount) VALUES (1, 5), (1, 7)`
2. A [1]: `UPDATE accounts a SET balance = a.balance + e.amount FROM entries e WHERE e.account_id = a.id`

Report:
- `rowcount`: the row count reported for the step marked [1]
- `entries_applied`: the first column of the first row of `SELECT CASE balance WHEN 100 THEN 0 WHEN 112 THEN 2 ELSE 1 END FROM accounts WHERE id = 1` run after everything else, as a string

**L18.**
Rows in `accounts`: `(1, 'ada', 100)`.

1. A: `INSERT INTO entries (account_id, amount) VALUES (1, 5)`
2. A: `BEGIN ISOLATION LEVEL REPEATABLE READ`
3. A: `SELECT count(*) FROM idem`
4. B: `TRUNCATE entries`
5. A [1]: `SELECT count(*) FROM entries`
6. A: `ROLLBACK`

Report:
- `a_count`: the first column of the first row returned by the step marked [1], as a string, or null if no row came back

**L19.**
Rows in `accounts`: `(1, 'ada', 100)`.

1. A: `BEGIN`
2. A: `DECLARE c CURSOR FOR SELECT balance FROM accounts WHERE id = 1`
3. A: `UPDATE accounts SET balance = 5 WHERE id = 1`
4. A [1]: `FETCH c`
5. A [2]: `SELECT balance FROM accounts WHERE id = 1`
6. A: `ROLLBACK`

Report:
- `fetched`: the first column of the first row returned by the step marked [1], as a string, or null if no row came back
- `selected`: the first column of the first row returned by the step marked [2], as a string, or null if no row came back

Return one ```json block holding one object with one key per scenario, each an object with exactly the fields requested. Use JSON `true`, `false` and `null`, plain integers for row counts, SQLSTATEs as five-character strings, and strings where a string is asked for.
