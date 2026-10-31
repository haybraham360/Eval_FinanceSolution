# Design review: PostgreSQL money and calendar arithmetic

Our payments service computes amounts and billing dates in SQL on **PostgreSQL 14.18** with default settings and `timezone = 'America/New_York'`. The `accounts` table holds exactly one row.

For each id, give the exact text of `SELECT (<expression>)::text`. If the statement raises an error, give `ERROR <sqlstate>`, for example `ERROR 12345`. Answers are compared character for character with a real server, so answer for what the engine does.

- E1: `round(2.5::numeric)`
- E2: `round(2.5::float8)`
- E3: `round(-2.5::numeric)`
- E4: `round(3.5::float8)`
- E5: `round(2.675::float8::numeric, 2)`
- E6: `2.675::numeric(10,2)`
- E7: `round(1.005::float8::numeric, 2)`
- E8: `(-7) / 2`
- E9: `(-7) % 2`
- E10: `div(-7.0, 2)`
- E11: `floor(-7 / 2.0)`
- E12: `7 / 2 * 2.0`
- E13: `2.0 * 7 / 2`
- E14: `1.0 / 3`
- E15: `1 / 3.0 * 3`
- E16: `(SELECT sum(x) FROM (SELECT 0.1::float8 AS x FROM generate_series(1, 10)) s)`
- E17: `(SELECT sum(x) FROM (SELECT 0.1 AS x FROM generate_series(1, 10)) s)`
- E18: `(SELECT avg(x) FROM (VALUES (1), (2)) t(x))`
- E19: `2.5::int`
- E20: `2.5::float8::int`
- E21: `3.5::float8::int`
- E22: `'1.5'::int`
- E23: `2147483647 + 1`
- E24: `999.995::numeric(5,2)`
- E25: `999.994::numeric(5,2)`
- E26: `'NaN'::numeric > 1e300`
- E27: `(SELECT sum(x) FROM (VALUES (1.0), ('NaN'::numeric)) t(x))`
- E28: `(SELECT count(*) FROM accounts WHERE 1 NOT IN (2, NULL))`
- E29: `'2024-01-31'::date + interval '1 month'`
- E30: `'2024-01-31'::date + interval '1 month' + interval '1 month'`
- E31: `'2024-01-31'::date + interval '2 months'`
- E32: `'2024-03-31'::date - interval '1 month'`
- E33: `(SELECT string_agg(d::date::text, ' ') FROM generate_series('2024-01-31'::date, '2024-05-31'::date, interval '1 month') d)`
- E34: `'2024-03-01'::date - '2024-02-01'::date`
- E35: `age('2024-03-31'::timestamp, '2024-02-29'::timestamp)`
- E36: `age('2024-03-01'::timestamp, '2024-01-31'::timestamp)`
- E37: `extract(epoch from interval '1 month')`
- E38: `interval '30 days' = interval '1 month'`
- E39: `'2026-03-07 12:00'::timestamptz + interval '1 day'`
- E40: `'2026-03-07 12:00'::timestamptz + interval '24 hours'`
- E41: `'2026-03-08 02:30'::timestamp AT TIME ZONE 'America/New_York'`
- E42: `'2026-11-01 01:30'::timestamp AT TIME ZONE 'America/New_York'`
- E43: `'2026-03-08 02:30'::timestamptz`
- E44: `date_trunc('day', '2026-03-08 12:00'::timestamptz)`
- E45: `date_trunc('day', '2026-03-08 12:00'::timestamptz) + interval '24 hours'`
- E46: `'2026-11-01 00:00'::timestamptz + interval '1 day' - '2026-11-01 00:00'::timestamptz`
- E47: `'2026-03-01 03:00+00'::timestamptz::date`
- E48: `('2026-03-01 03:00+00'::timestamptz AT TIME ZONE 'UTC')::date`
- E49: `extract(week from '2021-01-03'::date)`
- E50: `extract(isoyear from '2021-01-03'::date)`
- E51: `extract(year from '2021-01-03'::date)`
- E52: `to_char('2021-01-03'::date, 'YYYY-WW')`
- E53: `to_char(2.5, 'FM9')`
- E54: `to_char(1234.5, 'FM9,999.00')`
- E55: `to_char(12345.678, 'FM999.00')`
- E56: `'2024-02-29'::date + interval '1 year'`
- E57: `'2024-02-29'::date - interval '4 years' + interval '4 years'`
- E58: `make_date(2024, 2, 30)`

Return one ```json block holding one object mapping every id to its answer as a string, for example `{"E1": "...", "E2": "..."}`.
