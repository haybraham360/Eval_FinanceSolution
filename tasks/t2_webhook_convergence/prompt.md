# Ticket: payment projection from PSP webhooks

Our payment service provider (PSP) notifies us by webhook. Delivery is at-least-once and arrival order is arbitrary. Build the projection that keeps the merchant's position for **one payment** in integer minor units of one currency.

Implement in one Python 3.10+ module, standard library only:

```python
def apply_event(state: dict, event: dict) -> None: ...   # mutates state; state starts as {}
def balances(state: dict) -> dict: ...                   # see "Position"
def journal(state: dict) -> list[dict]: ...              # see "Journal"
```

Our worker saves `state` as JSON between events and reloads it, so after every `apply_event` the state must round-trip exactly through `json.dumps`/`json.loads` and keep working.

## Events

Every event has a unique delivery id, `event_id`, and a `type`.

| type | extra fields |
|---|---|
| `capture.succeeded` | `capture_id`, `amount_minor` |
| `refund.succeeded` | `refund_id`, `amount_minor` |
| `refund.failed` | `refund_id` |
| `dispute.opened` | `dispute_id`, `amount_minor` |
| `dispute.decided` | `dispute_id`, `outcome` (`won` or `lost`), `decided_at` (ISO-8601 with UTC offset) |

Delivery facts:

- The same delivery can arrive repeatedly with the same `event_id`.
- The PSP's retry system also re-issues the same business fact under a **new** `event_id`. A capture, refund or dispute is identified by its `capture_id`, `refund_id` or `dispute_id`, and a fact must count once.
- A payment can have several partial captures and several partial refunds, and at most one dispute.
- A refund can fail after being reported as succeeded. `refund.failed` is terminal. That refund never counts, whichever of its two events arrives first.
- A dispute can be decided more than once as it moves through arbitration. The decision with the latest `decided_at` instant is the one in force. Offsets vary between deliveries, and no two decisions share an instant.
- A `dispute.decided` can arrive before `dispute.opened`. Until `dispute.opened` has arrived, the decision has no financial effect.

## Position

`balances(state)` returns exactly these keys, all integers: `available`, `reserved`, `chargeback_loss`, `dispute_fee`, `unapplied_refund`. They must reflect every event applied so far, by these business rules:

- Captures add to the merchant's money.
- Refunds that count take money back from the merchant, but never more than has been captured so far. Any refund amount beyond that sits in `unapplied_refund` and is not taken from the merchant unless more captures arrive.
- A dispute can only touch money still with the merchant after refunds. If a dispute is for more than that, the excess is ignored. If a later-arriving refund reduces what is left, the disputed money must shrink to match.
- An open or undecided dispute moves the disputed money from `available` to `reserved`.
- A lost dispute moves the disputed money out of `available`, with nothing left in `reserved`, into `chargeback_loss`.
- A won dispute returns the disputed money to `available`.
- A fixed fee of 1500 sits in `dispute_fee` from the moment the dispute is opened, and is 0 while the decision in force is `won`. The fee is reported in its own key and does not reduce `available`.

**The final position must depend only on the set of distinct facts received, never on arrival order or repeats.**

## Journal

`journal(state)` returns our accounting record, a list of lines in posting order:

```python
{"line_id": str, "event_id": str, "account": str, "amount_minor": int}
```

- `account` is one of `available`, `reserved`, `chargeback_loss`, `dispute_fee`, `unapplied_refund`, `psp_clearing`.
- The journal is **append-only**: once returned, a line is never edited, removed or reordered. Corrections are made with further lines.
- `line_id` is unique across the journal. `event_id` is the delivery that caused the line.
- Lines caused by one delivery sum to zero, using `psp_clearing` as the contra account. An event that changes nothing adds no lines, and no line has amount 0.
- After every event, the sum of the journal's lines for each of the five position accounts must equal that key in `balances(state)`.

Return the complete module in one ```python block.
