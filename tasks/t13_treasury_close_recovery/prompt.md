# Ticket: month-end treasury close for the PayRail account

Ìlú Wallet (fictional) runs NGN customer wallets in Nigeria. PayRail (a fictional provider) collects pay-ins for us (NGN bank transfers and USD cards) and executes our NGN payouts. Every inbound fact reaches us as a **record**: provider webhooks, the results of our own API calls, PayRail settlement files and our own period-close marker. Records arrive at-least-once and not in time order.

Write the event-sourced module that turns records into ledger state for the October 2026 close. Implement it in one Python 3.10+ module, standard library only:

```python
def apply(state: dict, record: dict) -> list[dict]: ...    # mutates state, which starts as {}; returns provider commands
def balances(state: dict) -> dict: ...                     # {customer_id: {"available": int, "held": int}}
def payin_status(state: dict, payin_id: str) -> str | None: ...
def payout_status(state: dict, payout_id: str) -> str | None: ...
def journal(state: dict) -> list[dict]: ...
def period_totals(state: dict, period: str) -> dict: ...  # period is "YYYY-MM"
def reconciliation(state: dict) -> dict: ...
def exceptions(state: dict) -> list[dict]: ...
```

Our worker saves `state` as JSON after every record and reloads it, so after every `apply` the state must round-trip exactly through `json.dumps`/`json.loads` and keep working. All money is in integer minor units: kobo for NGN, cents for USD. Never use binary floating point for money.

## Records

Every record has a `record_id` and a `type`. A record can be delivered again with the same `record_id`. A repeated `record_id` has no effect at all: `apply` returns `[]`, and no state, line or output changes. Times are ISO-8601 strings in UTC with a `Z` suffix.

| type | fields |
|---|---|
| `fx.snapshot` | `snapshot_id`, `rate`: a decimal string, NGN per 1 USD |
| `payin.api_result` | `payin_id`, `customer_id`, `result` (always `"timeout"`), `at` |
| `payin.succeeded` | `payin_id`, `customer_id`, `currency` (`NGN` or `USD`), `amount_minor`, `occurred_at`, and `fx_snapshot_id` when `currency` is `USD` |
| `payin.reversed` | `reversal_id`, `payin_id`, `currency` (the pay-in's currency), `amount_minor`, `occurred_at`. Some carry an `fx_snapshot_id`. Ignore it. |
| `payout.requested` | `payout_id`, `customer_id`, `amount_minor` (NGN), `occurred_at` |
| `payout.send_result` | `payout_id`, `result` (`accepted`, `rejected` or `timeout`), `sent_at` |
| `payout.retry_requested` | `payout_id`, `at` |
| `payout.lookup_result` | `payout_id`, `result` (`accepted`, `rejected` or `not_found`), `at` |
| `settlement.file` | `batch_id`, `file_seq` (int), `value_date` (`YYYY-MM-DD`), `lines` (see Settlement) |
| `period.closed` | `period` (`YYYY-MM`) |

## Pay-ins

- `fx.snapshot` records are immutable. A snapshot always arrives before any record that names it. If a snapshot is delivered again with the same rate, nothing happens. If it is delivered again with a **different** rate, the first rate stays in force and the snapshot raises `FX_SNAPSHOT_CONFLICT`.
- A USD pay-in credits the customer in NGN at the rate of the snapshot named in its own `payin.succeeded`. Convert with `NGN minor = USD minor × rate`, rounded to a whole kobo **half to even**. Never use a later or different snapshot.
- Only a `payin.succeeded` webhook credits a customer, and it credits once per `payin_id`. PayRail re-issues a fact under a new `record_id`. If a later `payin.succeeded` arrives for a known `payin_id`, it has no effect.
- `payin.api_result` with `timeout` means our charge request timed out. The payment may or may not have happened. Until its webhook arrives, the pay-in is `PENDING`. It is not credited, and it is not failed. A timeout that arrives after the webhook changes nothing.
- A reversal (chargeback) belongs to its `payin_id`. A reversal that arrives before its pay-in's webhook has no financial effect until that webhook arrives, and then it applies.
- The reversals of one pay-in count in order of (`occurred_at` instant, `reversal_id`), whatever order they arrive in. Each one counts up to what remains of the pay-in after the reversals ordered before it. Any amount beyond that is ignored. The **counted** amount of a reversal is what remains after this cap.
- A reversal's NGN amount uses the pay-in's own snapshot, cumulatively: `NGN(cumulative counted up to and including this reversal) − NGN(cumulative counted before it)`, where `NGN(x)` is the half-to-even conversion above. For NGN pay-ins, the NGN amount is the counted amount.
- Reversals debit the customer's `available` balance, which may go negative.

`payin_status` returns `None` for a pay-in with neither a `payin.succeeded` nor a `payin.api_result`. Otherwise it returns `"PENDING"` (timeout, no webhook yet), `"SUCCEEDED"` (nothing counted reversed), `"PARTIALLY_REVERSED"` or `"REVERSED"` (counted reversals equal the pay-in amount).

## Payouts

- `payout.requested`: if the customer's `available` is at least the amount, move the amount from `available` to `held`, set the status to `SENDING`, and return one `send` command. Otherwise set the status to `REJECTED`, move nothing and return `[]`. A second request for a known `payout_id` has no effect.
- A command is `{"command": "send" | "lookup", "payout_id": str, "reference": str}`. Our executor carries it out and reports back with later records. Every command for one payout must carry the same `reference`, and no two payouts may share a reference.
- PayRail's `send` is idempotent per reference for **24 hours**. Within that window, a repeat send returns the original result and moves no money. After the window, PayRail has forgotten the reference, and a send creates a brand-new transfer. Treat the window as `[earliest sent_at for the payout, earliest sent_at + 24h)`.
- PayRail's lookup is authoritative and never expires, but a transfer that landed can take up to **900 seconds** after the send that created it to become visible.
- `payout.send_result`: `accepted` makes the payout `PAID`. `rejected` makes it `FAILED` and returns the held money to `available`. `timeout` leaves the outcome unknown: the status becomes `UNKNOWN` and the money stays held.
- `payout.lookup_result`: `accepted` → `PAID`, `rejected` → `FAILED`. `not_found` → `FAILED` only if at least one `send_result` has been received for the payout and `at` is at least 900 seconds after the latest `sent_at`. Otherwise nothing changes.
- `payout.retry_requested` does nothing and returns `[]` unless the status is `UNKNOWN`. If the status is `UNKNOWN` and `at` is inside the idempotency window, it returns a `send` command. If `at` is at or past the end of the window, sending could pay twice, so it returns a `lookup` command instead. A retry never changes the status.
- A `PAYOUT` settlement line in a batch's current file proves that the payout was paid, even if its amount disagrees. A payout in `SENDING` or `UNKNOWN` becomes `PAID` when such a line is received.
- `PAID`, `FAILED` and `REJECTED` are terminal. Evidence that money left (`accepted` from a send or lookup, or a current `PAYOUT` line) for a `FAILED` or `REJECTED` payout, or a `rejected` result for a `PAID` payout, changes nothing and raises `PAYOUT_CONFLICT`. Other repeat evidence for a terminal payout is ignored.

`payout_status` returns `None` for an unknown id, else `"SENDING"`, `"UNKNOWN"`, `"PAID"`, `"FAILED"` or `"REJECTED"`.

## Settlement

A settlement file line is:

```python
{"line_id": str, "line_type": "PAYIN" | "PAYIN_REVERSAL" | "PAYOUT" | "FEE" | "FEE_REFUND",
 "ref": str, "currency": "NGN" | "USD", "amount_minor": int, "settled_ngn_minor": int, "description": str}
```

`ref` is the `payin_id` for `PAYIN` and `FEE` lines, the `reversal_id` for `PAYIN_REVERSAL` and `FEE_REFUND` lines, and the `payout_id` for `PAYOUT` lines. `amount_minor` is in the line's `currency`. `settled_ngn_minor` is what PayRail actually settled in NGN at its own rate. Both are unsigned. `FEE` and `FEE_REFUND` lines are always NGN. For an NGN line, `settled_ngn_minor` equals `amount_minor`.

- **Corrected files.** PayRail can resend a batch. For each `batch_id`, only the file with the highest `file_seq` received so far is current. Every line of a lower `file_seq` is void, even if it arrives later. A file whose `file_seq` equals the current one's is ignored. Lines are matched to our items by (`line_type`, `ref`). PayRail renumbers `line_id` between files.
- Each (`line_type`, `ref`) appears in at most one batch. If it appears on several lines of one file, sum them.
- Signed from our side, PayRail's position is `+settled_ngn_minor` for `PAYIN` and `FEE_REFUND` lines, and `−settled_ngn_minor` for `PAYIN_REVERSAL`, `PAYOUT` and `FEE` lines. `provider_net` is the signed sum over every line of every current file.
- **Items** are our ledger facts that PayRail should settle: a credited pay-in (key `PAYIN`, `payin_id`), a reversal with a counted amount above 0 (key `PAYIN_REVERSAL`, `reversal_id`) and a `PAID` payout (key `PAYOUT`, `payout_id`).
- A current `PAYIN`, `PAYIN_REVERSAL` or `PAYOUT` line **matches** when its item exists. It agrees when the line's currency is the item's currency and the line's `amount_minor` equals the item's amount: the pay-in amount, the counted reversal amount, or the payout amount.
  - A line whose item does not exist raises `UNMATCHED_SETTLEMENT_LINE` (ref = the line's `ref`). The exception is a `PAYOUT` line for a `FAILED` or `REJECTED` payout, which raises `PAYOUT_CONFLICT` instead.
  - A line that matches but does not agree raises `SETTLEMENT_AMOUNT_MISMATCH` (ref = `ref`) and has no FX difference. If one was posted for that item earlier, it is reversed.
  - A matched, agreeing USD line posts the **FX difference**: the item's effect on `payrail:receivable` is brought to exactly PayRail's signed NGN, and the opposite side goes to `fx_gain_loss`.
- **Fees** are PayRail's charges, and the current file is the source of truth for them. Post every current `FEE` and `FEE_REFUND` line as stated, matched or not. Fees never create breaks.
- **Fee refund check.** For a reversal of a pay-in with amount `A` and current fee `F` (the pay-in's `FEE` line total, or 0 if there is none), the contractual refund is `floor(F × C / A) − floor(F × P / A)`. Here `C` is the cumulative counted reversed amount up to and including this reversal, and `P` is the amount before it, in the pay-in's currency and order. A reversal that is not counted (unknown, still orphaned, or counted as 0) has a contractual refund of 0. If a current `FEE_REFUND` line exists for a reversal and differs from this refund, raise `FEE_REFUND_MISMATCH` (ref = `reversal_id`). The line is still posted as stated. The fee that remains with us is the current fee minus the posted refunds.

## Journal

`journal(state)` returns our accounting record as a list of lines in posting order:

```python
{"line_id": str, "record_id": str, "account": str, "amount_minor": int, "accounting_date": "YYYY-MM-DD"}
```

All lines are NGN. A positive amount is a debit and a negative amount is a credit. Accounts:

| effect | debit (+) | credit (−) | natural accounting date |
|---|---|---|---|
| pay-in credited (NGN amount) | `payrail:receivable` | `customer:{customer_id}:available` | pay-in `occurred_at` |
| reversal counted (NGN amount) | `customer:{customer_id}:available` | `payrail:receivable` | reversal `occurred_at` |
| payout hold | `customer:{customer_id}:available` | `customer:{customer_id}:held` | payout `occurred_at` |
| payout `PAID` | `customer:{customer_id}:held` | `payrail:receivable` | the `sent_at`/`at` of the record that proved it, or the file's `value_date` |
| payout `FAILED` | `customer:{customer_id}:held` | `customer:{customer_id}:available` | the `sent_at`/`at` of the record that proved it |
| fee | `fee_expense` | `payrail:receivable` | file `value_date` |
| fee refund | `payrail:receivable` | `fee_expense` | file `value_date` |
| FX difference (PayRail's NGN − ours) | `payrail:receivable` | `fx_gain_loss` | file `value_date` |

- A timestamp's accounting date is its calendar date in Lagos time (WAT, fixed UTC+01:00, no daylight saving).
- The journal is **append-only**. Once returned, a line is never edited, removed or reordered. When a later record changes what an effect should be, for example a corrected file or a late webhook that changes a cap, post only the difference as new lines. The difference keeps the natural accounting date of the effect it corrects (in the table above), subject to the period-close rule.
- `line_id` is unique. `record_id` is the record whose `apply` call added the line. The lines added by one `apply` call sum to 0. A record that changes no account adds no lines, and no line has amount 0.
- After every record, `balances(state)[c]["available"]` equals minus the journal sum of `customer:{c}:available`, and likewise for `held`. Include every customer that appears in the journal.
- **Period close.** `period.closed` closes that month and every earlier month. From then on, a line whose natural accounting date falls in a closed month is dated the first day of the month after the latest closed month. Lines already posted keep their dates.
- `period_totals(state, "YYYY-MM")` returns `{account: sum of amount_minor}` over the lines dated in that month. Leave out accounts that sum to 0.

## Reconciliation and exceptions

`reconciliation(state)` returns:

```python
{"ledger_receivable": int,   # journal sum of payrail:receivable
 "provider_net": int,        # as defined under Settlement
 "breaks": [{"line_type": str, "ref": str, "delta_minor": int}, ...]}
```

For every key (`line_type`, `ref`) of type `PAYIN`, `PAYIN_REVERSAL` or `PAYOUT` that is an item or appears in a current file, `delta_minor` is PayRail's signed NGN minus the item's signed effect on `payrail:receivable`, including any FX difference posted for it. List only keys whose delta is not 0, sorted by `line_type` and then `ref`. The breaks must fully explain the difference: `sum(delta_minor) == provider_net − ledger_receivable`. Never post a line just to make the ledger agree with PayRail.

`exceptions(state)` returns the currently open exceptions as `[{"code": str, "ref": str}, ...]`, one per (code, ref), sorted by code and then ref. An exception is open while its condition holds, so it clears when a later record resolves it.

| code | ref | open while |
|---|---|---|
| `FX_SNAPSHOT_CONFLICT` | `snapshot_id` | always, once raised |
| `PAYIN_OUTCOME_UNKNOWN` | `payin_id` | the pay-in is `PENDING` |
| `ORPHAN_REVERSAL` | `reversal_id` | the reversal's pay-in has not been credited |
| `REVERSAL_EXCEEDS_PAYIN` | `reversal_id` | its pay-in has been credited and its counted amount is below its `amount_minor` |
| `NEGATIVE_BALANCE` | `customer_id` | the customer's `available` is below 0 |
| `PAYOUT_OUTCOME_UNKNOWN` | `payout_id` | the payout is `UNKNOWN` |
| `PAYOUT_CONFLICT` | `payout_id` | always, once raised |
| `UNMATCHED_SETTLEMENT_LINE` | line `ref` | as defined under Settlement, for current files |
| `SETTLEMENT_AMOUNT_MISMATCH` | line `ref` | as defined under Settlement, for current files |
| `FEE_REFUND_MISMATCH` | `reversal_id` | as defined under Settlement, for current files |

**Except for `fx.snapshot` conflicts, payout records and `PAYOUT` settlement lines, which are order-dependent by nature, the final balances, statuses, period totals, reconciliation and exceptions must depend only on the set of distinct records received before any `period.closed`, never on their arrival order or on repeats.**

## Sample: the October close log

This is the log for the October close, in arrival order. Your module must handle it and any other log that follows these rules.

```json
[
 {"record_id": "r01", "type": "fx.snapshot", "snapshot_id": "S-A", "rate": "1525.50"},
 {"record_id": "r02", "type": "payin.succeeded", "payin_id": "P1", "customer_id": "C1", "currency": "NGN", "amount_minor": 10000000, "occurred_at": "2026-10-30T09:00:00Z"},
 {"record_id": "r02", "type": "payin.succeeded", "payin_id": "P1", "customer_id": "C1", "currency": "NGN", "amount_minor": 10000000, "occurred_at": "2026-10-30T09:00:00Z"},
 {"record_id": "r03", "type": "payout.requested", "payout_id": "O1", "customer_id": "C1", "amount_minor": 8000000, "occurred_at": "2026-10-30T12:00:00Z"},
 {"record_id": "r04", "type": "payout.send_result", "payout_id": "O1", "result": "timeout", "sent_at": "2026-10-30T12:00:05Z"},
 {"record_id": "r05", "type": "payout.retry_requested", "payout_id": "O1", "at": "2026-10-30T13:00:00Z"},
 {"record_id": "r06", "type": "payout.send_result", "payout_id": "O1", "result": "timeout", "sent_at": "2026-10-30T13:00:03Z"},
 {"record_id": "r07", "type": "payin.succeeded", "payin_id": "P1", "customer_id": "C1", "currency": "NGN", "amount_minor": 10000000, "occurred_at": "2026-10-30T09:00:00Z"},
 {"record_id": "r08", "type": "fx.snapshot", "snapshot_id": "S-B", "rate": "1531.00"},
 {"record_id": "r09", "type": "payin.api_result", "payin_id": "P3", "customer_id": "C1", "result": "timeout", "at": "2026-10-31T10:00:00Z"},
 {"record_id": "r10", "type": "payout.retry_requested", "payout_id": "O1", "at": "2026-10-31T12:30:00Z"},
 {"record_id": "r11", "type": "payout.lookup_result", "payout_id": "O1", "result": "accepted", "at": "2026-10-31T12:30:10Z"},
 {"record_id": "r12", "type": "payin.reversed", "reversal_id": "X1", "payin_id": "P3", "currency": "NGN", "amount_minor": 1000000, "occurred_at": "2026-10-31T15:00:00Z"},
 {"record_id": "r13", "type": "payin.succeeded", "payin_id": "P3", "customer_id": "C1", "currency": "NGN", "amount_minor": 4000000, "occurred_at": "2026-10-31T10:00:01Z"},
 {"record_id": "r14", "type": "fx.snapshot", "snapshot_id": "S-A", "rate": "1540.00"},
 {"record_id": "r15", "type": "payin.api_result", "payin_id": "P4", "customer_id": "C2", "result": "timeout", "at": "2026-10-31T21:00:00Z"},
 {"record_id": "r16", "type": "payout.requested", "payout_id": "O3", "customer_id": "C1", "amount_minor": 1000000, "occurred_at": "2026-10-31T22:00:00Z"},
 {"record_id": "r17", "type": "payout.send_result", "payout_id": "O3", "result": "timeout", "sent_at": "2026-10-31T22:00:04Z"},
 {"record_id": "r18", "type": "payin.succeeded", "payin_id": "P2", "customer_id": "C2", "currency": "USD", "amount_minor": 2503, "occurred_at": "2026-10-31T23:30:00Z", "fx_snapshot_id": "S-A"},
 {"record_id": "r19", "type": "payout.requested", "payout_id": "O2", "customer_id": "C2", "amount_minor": 2000000, "occurred_at": "2026-10-31T23:40:00Z"},
 {"record_id": "r20", "type": "payout.send_result", "payout_id": "O2", "result": "timeout", "sent_at": "2026-10-31T23:40:02Z"},
 {"record_id": "r21", "type": "payout.lookup_result", "payout_id": "O2", "result": "not_found", "at": "2026-10-31T23:50:00Z"},
 {"record_id": "r22", "type": "payout.lookup_result", "payout_id": "O2", "result": "not_found", "at": "2026-11-01T00:00:00Z"},
 {"record_id": "r23", "type": "settlement.file", "batch_id": "B-1031", "file_seq": 1, "value_date": "2026-10-31", "lines": [
  {"line_id": "L1", "line_type": "PAYIN", "ref": "P1", "currency": "NGN", "amount_minor": 10000000, "settled_ngn_minor": 10000000, "description": "transfer"},
  {"line_id": "L2", "line_type": "FEE", "ref": "P1", "currency": "NGN", "amount_minor": 150000, "settled_ngn_minor": 150000, "description": "fee"},
  {"line_id": "L3", "line_type": "PAYIN", "ref": "P2", "currency": "USD", "amount_minor": 2503, "settled_ngn_minor": 3826000, "description": "card"},
  {"line_id": "L4", "line_type": "FEE", "ref": "P2", "currency": "NGN", "amount_minor": 57000, "settled_ngn_minor": 57000, "description": "fee"},
  {"line_id": "L5", "line_type": "PAYIN", "ref": "P3", "currency": "NGN", "amount_minor": 4000000, "settled_ngn_minor": 4000000, "description": "transfer"},
  {"line_id": "L6", "line_type": "FEE", "ref": "P3", "currency": "NGN", "amount_minor": 60000, "settled_ngn_minor": 60000, "description": "fee"},
  {"line_id": "L7", "line_type": "PAYIN_REVERSAL", "ref": "X1", "currency": "NGN", "amount_minor": 1000000, "settled_ngn_minor": 1000000, "description": "chargeback"},
  {"line_id": "L8", "line_type": "FEE_REFUND", "ref": "X1", "currency": "NGN", "amount_minor": 15000, "settled_ngn_minor": 15000, "description": "fee refund"},
  {"line_id": "L9", "line_type": "PAYOUT", "ref": "O1", "currency": "NGN", "amount_minor": 8000000, "settled_ngn_minor": 8000000, "description": "payout"},
  {"line_id": "L10", "line_type": "PAYIN", "ref": "P9", "currency": "NGN", "amount_minor": 777700, "settled_ngn_minor": 777700, "description": "transfer"}]},
 {"record_id": "r23", "type": "settlement.file", "batch_id": "B-1031", "file_seq": 1, "value_date": "2026-10-31", "lines": "(identical repeat delivery of r23)"},
 {"record_id": "r24", "type": "settlement.file", "batch_id": "B-1031", "file_seq": 2, "value_date": "2026-10-31", "lines": [
  {"line_id": "M1", "line_type": "PAYOUT", "ref": "O1", "currency": "NGN", "amount_minor": 8000000, "settled_ngn_minor": 8000000, "description": "payout"},
  {"line_id": "M2", "line_type": "PAYIN", "ref": "P1", "currency": "NGN", "amount_minor": 10000000, "settled_ngn_minor": 10000000, "description": "transfer"},
  {"line_id": "M3", "line_type": "FEE", "ref": "P1", "currency": "NGN", "amount_minor": 145000, "settled_ngn_minor": 145000, "description": "fee"},
  {"line_id": "M4", "line_type": "PAYIN", "ref": "P2", "currency": "USD", "amount_minor": 2503, "settled_ngn_minor": 3825500, "description": "card"},
  {"line_id": "M5", "line_type": "FEE", "ref": "P2", "currency": "NGN", "amount_minor": 57000, "settled_ngn_minor": 57000, "description": "fee"},
  {"line_id": "M6", "line_type": "PAYIN", "ref": "P3", "currency": "NGN", "amount_minor": 4000000, "settled_ngn_minor": 4000000, "description": "bank transfer (corrected narration)"},
  {"line_id": "M7", "line_type": "FEE", "ref": "P3", "currency": "NGN", "amount_minor": 60000, "settled_ngn_minor": 60000, "description": "fee"},
  {"line_id": "M8", "line_type": "PAYIN_REVERSAL", "ref": "X1", "currency": "NGN", "amount_minor": 1000000, "settled_ngn_minor": 1000000, "description": "chargeback"},
  {"line_id": "M9", "line_type": "FEE_REFUND", "ref": "X1", "currency": "NGN", "amount_minor": 16000, "settled_ngn_minor": 16000, "description": "fee refund"},
  {"line_id": "M10", "line_type": "PAYIN", "ref": "P9", "currency": "NGN", "amount_minor": 777700, "settled_ngn_minor": 777700, "description": "transfer"}]},
 {"record_id": "r25", "type": "settlement.file", "batch_id": "B-1031", "file_seq": 1, "value_date": "2026-10-31", "lines": "(the same ten lines as r23)"},
 {"record_id": "r26", "type": "period.closed", "period": "2026-10"},
 {"record_id": "r27", "type": "payin.reversed", "reversal_id": "X3", "payin_id": "P1", "currency": "NGN", "amount_minor": 2000000, "occurred_at": "2026-10-31T20:00:00Z"},
 {"record_id": "r28", "type": "payin.reversed", "reversal_id": "X2", "payin_id": "P2", "currency": "USD", "amount_minor": 1001, "occurred_at": "2026-11-01T09:00:00Z", "fx_snapshot_id": "S-B"},
 {"record_id": "r29", "type": "settlement.file", "batch_id": "B-1031", "file_seq": 3, "value_date": "2026-10-31", "lines": "(the same ten lines as r24, with line_ids N1-N10, except: FEE P3 is 62000 and FEE_REFUND X1 is 15500)"},
 {"record_id": "r30", "type": "payin.reversed", "reversal_id": "X4", "payin_id": "P3", "currency": "NGN", "amount_minor": 3500000, "occurred_at": "2026-11-01T10:00:00Z"},
 {"record_id": "r31", "type": "payout.retry_requested", "payout_id": "O1", "at": "2026-11-01T11:00:00Z"},
 {"record_id": "r32", "type": "payout.retry_requested", "payout_id": "O3", "at": "2026-11-01T11:00:00Z"}
]
```

The three `"lines"` strings above abbreviate full line lists, to keep this ticket short. The real records carry the full lists.

## Deliverable

Return the complete module in one ```python block. It must also define a module-level constant with the final position you expect after the whole sample log, worked out from the rules:

```python
SAMPLE_RESULT = {
    "balances": {"C1": {"available": int, "held": int}, "C2": {"available": int, "held": int}},
    "ledger_receivable": int,
    "provider_net": int,
    "fee_expense": int,      # journal sum of fee_expense
    "fx_gain_loss": int,     # journal sum of fx_gain_loss
    "exceptions": [[code, ref], ...],
}
```

Before the code block, briefly explain how you derived the final position: which records changed what, and why each open exception is open.
