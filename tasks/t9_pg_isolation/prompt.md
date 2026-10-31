# Design review: what does PostgreSQL actually do?

Our payments service runs on **PostgreSQL 14.18** with default settings. Each scenario below comes from a bug class we have seen or fear. Predict the exact behaviour. Your answers will be compared with a real server, so answer for what the engine does, not for what would be sensible.

Before every scenario the database is reset to this schema. Tables hold only the rows the scenario lists, and no ANALYZE has run.

```sql
CREATE TABLE accounts (id int PRIMARY KEY, owner text NOT NULL UNIQUE, balance int NOT NULL);
CREATE TABLE entries (id serial PRIMARY KEY, account_id int NOT NULL REFERENCES accounts(id), amount int NOT NULL);
CREATE TABLE idem (key text PRIMARY KEY, result text NOT NULL);
```

`A`, `B` and `C` are separate connections with the default READ COMMITTED level. Anything outside `BEGIN ... COMMIT` autocommits. Steps run strictly in order. "starts" means the statement is sent and the next step runs without waiting for it, about 100ms later or as soon as the statement has clearly blocked. "finishes" means that session's started statement has returned. A step after a failed statement still runs. Steps marked with a number in brackets are the ones asked about.

**I1.**
Rows in `accounts`: `(1, 'ada', 100)`.

1. A: `BEGIN ISOLATION LEVEL REPEATABLE READ`
2. B: `UPDATE accounts SET balance = 7 WHERE id = 1`
3. A [1]: `SELECT balance FROM accounts WHERE id = 1`
4. A: `ROLLBACK`

Report:
- `a_saw`: the first column of the first row returned by the step marked [1], as a string, or null if no row came back

**I2.**
Rows in `accounts`: `(1, 'ada', 100)`.

1. B: `BEGIN`
2. B: `SELECT pg_advisory_xact_lock(1)`
3. B: `UPDATE accounts SET balance = 7 WHERE id = 1`
4. A: `BEGIN ISOLATION LEVEL REPEATABLE READ`
5. A starts [1]: `SELECT pg_advisory_xact_lock(1)`
6. B: `COMMIT`
7. A finishes.
8. A [2]: `SELECT balance FROM accounts WHERE id = 1`
9. A [3]: `UPDATE accounts SET balance = balance + 1 WHERE id = 1`
10. A: `ROLLBACK`

Report:
- `a_blocked`: true if the step marked [1] had to wait on another session, else false
- `a_saw`: the first column of the first row returned by the step marked [2], as a string, or null if no row came back
- `a_update_sqlstate`: the SQLSTATE raised by the step marked [3], or null if it raised no error
- `final_balance`: the first column of the first row of `SELECT balance FROM accounts WHERE id = 1` run after everything else, as a string

**I3.**
Rows in `accounts`: `(1, 'ada', 100)`.

1. B: `BEGIN`
2. B: `UPDATE accounts SET balance = 7 WHERE id = 1`
3. A: `BEGIN ISOLATION LEVEL REPEATABLE READ`
4. A starts [1]: `LOCK TABLE accounts IN SHARE MODE`
5. B: `COMMIT`
6. A finishes.
7. A [2]: `SELECT balance FROM accounts WHERE id = 1`
8. A: `ROLLBACK`

Report:
- `a_blocked`: true if the step marked [1] had to wait on another session, else false
- `a_saw`: the first column of the first row returned by the step marked [2], as a string, or null if no row came back

**I4.**
Rows in `accounts`: `(1, 'ada', 100)`.

1. A: `BEGIN ISOLATION LEVEL REPEATABLE READ`
2. A: `SELECT count(*) FROM idem`
3. B: `BEGIN`
4. B: `UPDATE accounts SET balance = 7 WHERE id = 1`
5. A starts [1]: `SELECT balance FROM accounts WHERE id = 1 FOR UPDATE`
6. B: `ROLLBACK`
7. A finishes.
8. A: `ROLLBACK`

Report:
- `a_blocked`: true if the step marked [1] had to wait on another session, else false
- `a_sqlstate`: the SQLSTATE raised by the step marked [1], or null if it raised no error
- `a_saw`: the first column of the first row returned by the step marked [1], as a string, or null if no row came back

**I5.**
Rows in `accounts`: `(1, 'ada', 100)`.

1. A: `BEGIN ISOLATION LEVEL REPEATABLE READ`
2. A: `SELECT count(*) FROM idem`
3. A: `SAVEPOINT s`
4. B: `UPDATE accounts SET balance = 7 WHERE id = 1`
5. A [1]: `UPDATE accounts SET balance = balance + 1 WHERE id = 1`
6. A [2]: `ROLLBACK TO SAVEPOINT s`
7. A [3]: `UPDATE accounts SET balance = balance + 1 WHERE id = 1`
8. A: `ROLLBACK`

Report:
- `first_sqlstate`: the SQLSTATE raised by the step marked [1], or null if it raised no error
- `rollback_to_sqlstate`: the SQLSTATE raised by the step marked [2], or null if it raised no error
- `retry_sqlstate`: the SQLSTATE raised by the step marked [3], or null if it raised no error

**I6.**
Rows in `accounts`: `(1, 'ada', 100)`.

1. A: `BEGIN ISOLATION LEVEL SERIALIZABLE`
2. B: `BEGIN ISOLATION LEVEL SERIALIZABLE`
3. A: `SELECT * FROM idem WHERE key = 'k'`
4. B: `SELECT * FROM idem WHERE key = 'k'`
5. A: `INSERT INTO idem VALUES ('k', 'a')`
6. B starts [1]: `INSERT INTO idem VALUES ('k', 'b')`
7. A: `COMMIT`
8. B finishes.
9. B: `ROLLBACK`

Report:
- `b_blocked`: true if the step marked [1] had to wait on another session, else false
- `b_sqlstate`: the SQLSTATE raised by the step marked [1], or null if it raised no error

**I7.**
Rows in `accounts`: `(1, 'ada', 100)`.

1. A: `BEGIN ISOLATION LEVEL SERIALIZABLE`
2. B: `BEGIN ISOLATION LEVEL SERIALIZABLE`
3. A: `SELECT count(*) FROM accounts`
4. B: `SELECT count(*) FROM accounts`
5. A: `INSERT INTO idem VALUES ('k', 'a')`
6. B starts [1]: `INSERT INTO idem VALUES ('k', 'b')`
7. A: `COMMIT`
8. B finishes.
9. B: `ROLLBACK`

Report:
- `b_sqlstate`: the SQLSTATE raised by the step marked [1], or null if it raised no error

**I8.**
Rows in `accounts`: `(1, 'ada', 100)`, `(2, 'bo', 100)`.
Each transaction reads and writes only its own account. The table was just created and has not been analyzed.

1. A: `BEGIN ISOLATION LEVEL SERIALIZABLE`
2. B: `BEGIN ISOLATION LEVEL SERIALIZABLE`
3. A: `SELECT balance FROM accounts WHERE id = 1`
4. B: `SELECT balance FROM accounts WHERE id = 2`
5. A: `UPDATE accounts SET balance = 1 WHERE id = 1`
6. B: `UPDATE accounts SET balance = 2 WHERE id = 2`
7. A [1]: `COMMIT`
8. B [2]: `COMMIT`
9. B: `ROLLBACK`

Report:
- `a_commit_sqlstate`: the SQLSTATE raised by the step marked [1], or null if it raised no error
- `b_commit_sqlstate`: the SQLSTATE raised by the step marked [2], or null if it raised no error

**I9.**
Rows in `accounts`: `(1, 'ada', 100)`, `(2, 'bo', 100)`.

1. A: `BEGIN ISOLATION LEVEL SERIALIZABLE`
2. B: `BEGIN`
3. A: `SELECT sum(balance) FROM accounts`
4. B: `SELECT sum(balance) FROM accounts`
5. A: `UPDATE accounts SET balance = balance - 150 WHERE id = 1`
6. B: `UPDATE accounts SET balance = balance - 150 WHERE id = 2`
7. A [1]: `COMMIT`
8. B [2]: `COMMIT`

Report:
- `a_commit_sqlstate`: the SQLSTATE raised by the step marked [1], or null if it raised no error
- `b_commit_sqlstate`: the SQLSTATE raised by the step marked [2], or null if it raised no error
- `sum_after`: the first column of the first row of `SELECT sum(balance) FROM accounts` run after everything else, as a string

**I10.**
Rows in `accounts`: `(1, 'ada', 100)`, `(2, 'bo', 100)`.

1. A: `BEGIN ISOLATION LEVEL SERIALIZABLE`
2. B: `BEGIN ISOLATION LEVEL SERIALIZABLE`
3. A: `SELECT sum(balance) FROM accounts`
4. B: `SELECT sum(balance) FROM accounts`
5. A: `UPDATE accounts SET balance = balance - 150 WHERE id = 1`
6. B: `UPDATE accounts SET balance = balance - 150 WHERE id = 2`
7. A [1]: `COMMIT`
8. B [2]: `SELECT 1`
9. B [3]: `COMMIT`
10. B: `ROLLBACK`

Report:
- `a_commit_sqlstate`: the SQLSTATE raised by the step marked [1], or null if it raised no error
- `b_select_sqlstate`: the SQLSTATE raised by the step marked [2], or null if it raised no error
- `b_commit_sqlstate`: the SQLSTATE raised by the step marked [3], or null if it raised no error
- `b_commit_tag`: the command tag returned for the step marked [3], or null if it raised an error

**I11.**
Rows in `accounts`: none.
Extra setup:
```sql
CREATE TABLE control (batch int); INSERT INTO control VALUES (1); CREATE TABLE receipts (batch int, amount int);
```

1. A: `BEGIN ISOLATION LEVEL SERIALIZABLE`
2. A: `SELECT batch FROM control`
3. B: `BEGIN ISOLATION LEVEL SERIALIZABLE`
4. B: `UPDATE control SET batch = batch + 1`
5. B [1]: `COMMIT`
6. C: `BEGIN ISOLATION LEVEL SERIALIZABLE READ ONLY`
7. C: `SELECT batch FROM control`
8. C [2]: `SELECT count(*) FROM receipts WHERE batch = 1`
9. C [3]: `COMMIT`
10. A [4]: `INSERT INTO receipts VALUES (1, 100)`
11. A [5]: `COMMIT`
12. A: `ROLLBACK`

Report:
- `b_commit_sqlstate`: the SQLSTATE raised by the step marked [1], or null if it raised no error
- `c_commit_sqlstate`: the SQLSTATE raised by the step marked [3], or null if it raised no error
- `a_insert_sqlstate`: the SQLSTATE raised by the step marked [4], or null if it raised no error
- `a_commit_sqlstate`: the SQLSTATE raised by the step marked [5], or null if it raised no error

**I12.**
Rows in `accounts`: none.
Extra setup:
```sql
CREATE TABLE d (k int UNIQUE DEFERRABLE INITIALLY DEFERRED); INSERT INTO d VALUES (1);
```

1. A: `BEGIN`
2. A [1]: `INSERT INTO d VALUES (1)`
3. A [2]: `SELECT count(*) FROM d`
4. A [3]: `COMMIT`

Report:
- `insert_sqlstate`: the SQLSTATE raised by the step marked [1], or null if it raised no error
- `visible_rows`: the first column of the first row returned by the step marked [2], as a string, or null if no row came back
- `commit_sqlstate`: the SQLSTATE raised by the step marked [3], or null if it raised no error
- `rows_after`: the first column of the first row of `SELECT count(*) FROM d` run after everything else, as a string

**I13.**
Rows in `accounts`: none.
Extra setup:
```sql
CREATE TABLE d1 (k int UNIQUE); INSERT INTO d1 VALUES (1), (2); CREATE TABLE d2 (k int UNIQUE DEFERRABLE INITIALLY IMMEDIATE); INSERT INTO d2 VALUES (1), (2);
```

1. A [1]: `UPDATE d1 SET k = k + 1`
2. A [2]: `UPDATE d2 SET k = k + 1`

Report:
- `plain_unique_sqlstate`: the SQLSTATE raised by the step marked [1], or null if it raised no error
- `deferrable_unique_sqlstate`: the SQLSTATE raised by the step marked [2], or null if it raised no error

**I14.**
Rows in `accounts`: `(1, 'ada', 100)`.
Extra setup:
```sql
CREATE TABLE e2 (account_id int REFERENCES accounts(id) DEFERRABLE);
```

1. A: `BEGIN`
2. A: `SET CONSTRAINTS ALL DEFERRED`
3. A [1]: `INSERT INTO e2 VALUES (99)`
4. A [2]: `SET CONSTRAINTS ALL IMMEDIATE`
5. A: `ROLLBACK`

Report:
- `insert_sqlstate`: the SQLSTATE raised by the step marked [1], or null if it raised no error
- `set_immediate_sqlstate`: the SQLSTATE raised by the step marked [2], or null if it raised no error

**I15.**
Rows in `accounts`: `(1, 'ada', 100)`.
Default `max_prepared_transactions`.

1. A: `BEGIN`
2. A [1]: `PREPARE TRANSACTION 'p1'`
3. A: `ROLLBACK`

Report:
- `sqlstate`: the SQLSTATE raised by the step marked [1], or null if it raised no error

**I16.**
Rows in `accounts`: `(1, 'ada', 100)`.
Extra setup:
```sql
CREATE FUNCTION stable_sum() RETURNS bigint LANGUAGE sql STABLE AS 'SELECT sum(balance) FROM accounts';
```

1. A: `BEGIN ISOLATION LEVEL READ COMMITTED`
2. A [1]: `SELECT sum(balance) FROM accounts`
3. B: `UPDATE accounts SET balance = 7 WHERE id = 1`
4. A [2]: `SELECT sum(balance) FROM accounts`
5. A [3]: `SELECT stable_sum(), sum(balance) FROM accounts`
6. A: `COMMIT`

Report:
- `first`: the first column of the first row returned by the step marked [1], as a string, or null if no row came back
- `second`: the first column of the first row returned by the step marked [2], as a string, or null if no row came back

**I17.**
Rows in `accounts`: `(1, 'ada', 100)`.

1. A: `BEGIN`
2. A: `UPDATE accounts SET balance = 7 WHERE id = 1`
3. A: `SET LOCAL lock_timeout = '50ms'`
4. B: `SET lock_timeout = '50ms'`
5. B [1]: `SELECT * FROM accounts WHERE id = 1 FOR UPDATE`
6. B: `SET lock_timeout = 0`
7. B: `SET statement_timeout = '50ms'`
8. B [2]: `SELECT * FROM accounts WHERE id = 1 FOR UPDATE`
9. B: `SET statement_timeout = 0`
10. A: `ROLLBACK`

Report:
- `lock_timeout_sqlstate`: the SQLSTATE raised by the step marked [1], or null if it raised no error
- `statement_timeout_sqlstate`: the SQLSTATE raised by the step marked [2], or null if it raised no error

Return one ```json block holding one object with one key per scenario, each an object with exactly the fields requested. Use JSON `true`, `false` and `null`, plain integers for row counts, SQLSTATEs as five-character strings, and strings where a string is asked for.
