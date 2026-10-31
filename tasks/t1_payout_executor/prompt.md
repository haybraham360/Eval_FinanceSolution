# Ticket: payout executor

We move customer money out through an external bank-transfer provider. Write the module that executes one payout. A database transaction cannot span the provider call, and workers can be killed at any instruction and restarted, so the same call can run again at any time, including concurrently with itself.

Implement this in one Python 3.10+ module, standard library only:

```python
def execute_payout(store, provider, payout_id, account, amount_minor, dest, now) -> str:
    """Returns the payout's current status: "PAID", "FAILED", "PENDING" or "INSUFFICIENT"."""
```

`now` is an integer number of seconds since the epoch. Callers re-invoke with identical arguments except `now`, until the result is `PAID`, `FAILED` or `INSUFFICIENT`. You cannot add background jobs, and you cannot add methods to `store` or `provider`.

Also define the exception import point exactly like this, near the top of your module, so we can inject the real class:

```python
ProviderTimeout = TimeoutError
```

## `store`: our database (already implemented)

Each method is one atomic, durable transaction.

- `get_payout(payout_id) -> dict | None`. A copy of the row. Always has `payout_id, account, amount_minor, dest, status`, plus any fields you have saved.
- `reserve(payout_id, account, amount_minor, dest) -> str`. Returns `"EXISTS"` if the row exists. Returns `"INSUFFICIENT"`, creating nothing, if available funds are short. Otherwise it inserts the row with status `RESERVED`, moves the amount from the account's available funds to held funds, and returns `"CREATED"`.
- `update(payout_id, expected_status, new_status, **fields) -> bool`. Compare-and-swap on status. On a match it saves `fields` on the row and returns True. `new_status` may equal `expected_status`, and the only statuses this method accepts are non-terminal ones: `RESERVED`, `SENDING`.
- `finish(payout_id, expected_status, outcome, **fields) -> bool`. Compare-and-swap on status. On a match it sets `status` to `outcome`, which must be `"PAID"` (held funds leave the account) or `"FAILED"` (held funds return to available), saves `fields`, and returns True.

`SENDING` is the only status name you may add to the ones listed above. A payout that `reserve` declined has no row, so a later call may succeed if funds have arrived.

## `provider`: the bank-transfer API (external)

- `send(reference, dest, amount_minor) -> dict`. Returns `{"status": "accepted" | "rejected", "provider_id": str}`. May raise `ProviderTimeout`, in which case the request may or may not have landed. Both outcomes occur in production.
- `lookup(reference) -> dict | None`. The same dict for a reference the provider knows, else `None`. Authoritative with no expiry, but a landed transfer can take up to 15 minutes (900 seconds) to become visible here. May raise `ProviderTimeout`.

`send` is idempotent per `reference` for **24 hours** from the first time the provider saw that reference. Within that time, repeats return the original result and move no money. After 24 hours the provider has forgotten the reference, and calling `send` with it creates a brand-new transfer. A `rejected` result is final for that payout and moved no money.

## Requirements

1. The customer's destination must never receive a payout more than once, whatever the sequence of kills, retries, timeouts and concurrent invocations.
2. Money that left must end as `PAID`. A payout may only become `FAILED` if the provider rejected it, or if no transfer can have landed: `lookup` returned `None` and at least 900 seconds have passed since the most recent `send` attempt for this payout, which may have been made by a worker that later died.
3. While the outcome is unknown, return `"PENDING"` and leave the funds held. A timeout from the provider must never escape `execute_payout` as an exception.
4. The returned status must be the true stored status at return, not what this invocation hoped to write. A concurrent invocation may have finished the payout first.
5. Status changes of a finished payout are forbidden: repeat calls return its final status and make no provider calls that could move money.

Return the complete module in one ```python block.
