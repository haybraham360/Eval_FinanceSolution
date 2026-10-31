# Review: what does PostgreSQL actually do in these schedules?

Our payments service runs on **PostgreSQL 14.18** with default settings. For a design review, predict the exact behaviour of each schedule below. These are exact, not approximate, and the answers will be compared with a real server.

Schema, reset before every scenario. Unless a scenario says otherwise, it holds the single row `(1, 'ada', 100)`.

```sql
CREATE TABLE accounts (id int PRIMARY KEY, owner text NOT NULL UNIQUE, balance int NOT NULL);
CREATE TABLE entries (id serial PRIMARY KEY, account_id int NOT NULL REFERENCES accounts(id), amount int NOT NULL);
CREATE TABLE idem (key text PRIMARY KEY, result text NOT NULL);
```

`A` and `B` are separate sessions. Statements run strictly in the order listed. Anything outside `BEGIN ... COMMIT` autocommits, and plain `BEGIN` is READ COMMITTED. "B starts X" means B's statement is sent while A continues; if it blocks, A's later steps still run. `B finishes` means B's statement has returned by that point.

**S1.** A: `BEGIN`. A: `UPDATE accounts SET balance = balance - 80 WHERE id = 1 AND balance >= 80`. B starts the same UPDATE, autocommit. A: `COMMIT`. B finishes.
Report `b_blocked` (true if B had to wait on A), `b_rowcount` (row count reported by B's UPDATE), `final_balance`.

**S2.** A: `BEGIN`. A: `UPDATE accounts SET balance = balance + 10 WHERE id = 1`. B starts, autocommit: `UPDATE accounts SET balance = (SELECT balance FROM accounts WHERE id = 1) + 10 WHERE id = 1`. A: `COMMIT`. B finishes.
Report `b_rowcount`, `final_balance`.

**S3.** Rows `(1,'ada',100)` and `(2,'bo',90)`. A: `BEGIN`. A: `UPDATE accounts SET balance = 50 WHERE id = 1`. B starts, autocommit: `SELECT id, balance FROM accounts ORDER BY balance DESC LIMIT 1 FOR UPDATE`. A: `COMMIT`. B finishes.
Report `b_id` and `b_balance`, the row B's SELECT returned.

**S4.** A: `BEGIN ISOLATION LEVEL REPEATABLE READ`. A: `SELECT balance FROM accounts WHERE id = 1`. B, autocommit: `UPDATE accounts SET balance = balance - 30 WHERE id = 1`. A: `UPDATE accounts SET balance = balance - 30 WHERE id = 1`. A: `ROLLBACK`.
Report `a_update_sqlstate` (the SQLSTATE of A's UPDATE, or null if it succeeded), `final_balance`.

**S5.** One autocommit statement:
`WITH u AS (UPDATE accounts SET balance = balance - 30 WHERE id = 1 RETURNING balance) SELECT (SELECT balance FROM u) AS from_u, (SELECT balance FROM accounts WHERE id = 1) AS from_table`
Report `from_u`, `from_table`, `final_balance`.

**S6.** A: `BEGIN`. A: `INSERT INTO idem VALUES ('k', 'a')`. B starts, autocommit: `INSERT INTO idem VALUES ('k', 'b') ON CONFLICT (key) DO NOTHING RETURNING result`. A: `COMMIT`. B finishes.
Report `b_blocked`, `b_returned_rows` (number of rows returned to B), `stored_result` (the row's `result` afterwards).

**S7.** B: `BEGIN ISOLATION LEVEL REPEATABLE READ`. B: `SELECT count(*) FROM idem`. A, autocommit: `INSERT INTO idem VALUES ('k', 'a')`. B: `SELECT result FROM idem WHERE key = 'k'`. B: `INSERT INTO idem VALUES ('k', 'b') ON CONFLICT (key) DO NOTHING RETURNING result`. B: `ROLLBACK`.
Report `b_select_rows` (rows returned by B's SELECT), `b_insert_sqlstate` (or null), `b_insert_returned_rows` (0 if the statement failed).

**S8.** Rows `(1,'ada',60)` and `(2,'bo',60)`. A and B each run `BEGIN ISOLATION LEVEL SERIALIZABLE` and then `SELECT sum(balance) FROM accounts`. A: `UPDATE accounts SET balance = balance - 100 WHERE id = 1`. B: `UPDATE accounts SET balance = balance - 100 WHERE id = 2`. A: `COMMIT`. B: `COMMIT`.
Report `a_update_sqlstate`, `b_update_sqlstate`, `a_commit_sqlstate`, `b_commit_sqlstate` (each a SQLSTATE or null) and `sum_after` (sum of the balances once both are done).

**S9.** Five separate runs, each from a reset. A: `BEGIN`, then one statement from the list. B then starts, autocommit: `INSERT INTO entries (account_id, amount) VALUES (1, 5)`. For each case report true if B's INSERT blocks on A, false if it completes while A's transaction is still open.
- `balance_update`: `UPDATE accounts SET balance = balance - 1 WHERE id = 1`
- `for_update`: `SELECT * FROM accounts WHERE id = 1 FOR UPDATE`
- `for_no_key_update`: `SELECT * FROM accounts WHERE id = 1 FOR NO KEY UPDATE`
- `owner_changed`: `UPDATE accounts SET owner = 'ada2' WHERE id = 1`
- `owner_unchanged`: `UPDATE accounts SET owner = owner WHERE id = 1`

**S10.** A: `BEGIN`. A: `SELECT pg_advisory_lock(42)`. A: `SELECT pg_advisory_xact_lock(43)`. A: `ROLLBACK`. A's connection stays open. B: `SELECT pg_try_advisory_lock(42)`. B: `SELECT pg_try_advisory_lock(43)`.
Report `b_gets_42`, `b_gets_43` (the booleans returned).

**S11.** A: `BEGIN`. A: `UPDATE accounts SET balance = balance - 10 WHERE id = 1`. A: `INSERT INTO accounts VALUES (1, 'dup', 0)`. A: `UPDATE accounts SET balance = balance - 10 WHERE id = 1`. A: `COMMIT`.
Report `insert_sqlstate`, `second_update_sqlstate`, `commit_sqlstate` (each a SQLSTATE, or null if that statement raised no error), `commit_tag` (the command tag the server returned for the last statement, for example `"BEGIN"`) and `final_balance`.

**S12.** Rows `(1,'ada',90)` and `(2,'bo',150)`. A: `BEGIN`. A: `UPDATE accounts SET balance = 120 WHERE id = 1`. A: `UPDATE accounts SET balance = 50 WHERE id = 2`. B starts, autocommit: `UPDATE accounts SET balance = balance - 10 WHERE balance >= 100`. A: `COMMIT`. B finishes.
Report `b_blocked`, `b_rowcount`, `balance_1`, `balance_2`.

**S13.** A: `BEGIN`. A: `DELETE FROM accounts WHERE id = 1`. A: `INSERT INTO accounts VALUES (1, 'ada', 5)`. B starts, autocommit: `UPDATE accounts SET balance = balance + 7 WHERE id = 1`. A: `COMMIT`. B finishes.
Report `b_blocked`, `b_rowcount`, `final_balance`.

Return one ```json block holding one object with keys `S1` to `S13`, each an object with exactly the fields requested for that scenario. Use JSON `true`, `false` and `null`, plain numbers, and SQLSTATEs as five-character strings.
