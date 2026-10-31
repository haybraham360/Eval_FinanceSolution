# cli-opus / t1_payout_executor / trial 1

- Requested: `opus`, resolved: `claude-haiku-5-5,claude-opus-5-5`, provider: claude-cli
- Run at 2026-10-31T15:24:34+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t1_payout_executor/prompt.md`.

## Model output

```python
"""Payout executor.

Protocol (the only statuses are RESERVED, SENDING, PAID and FAILED):

1. reserve() creates the row and holds the funds.
2. RESERVED -> SENDING durably records first_send_at before anything can reach
   the provider. Only one worker can win this transition, so first_send_at is
   never rewritten and is never later than the provider's first sighting of the
   reference. The provider's idempotency window therefore cannot end before
   first_send_at + 24h.
3. Before the send cutoff, every invocation records its attempt and then calls
   send() with the same reference. This is safe because a repeat moves no money
   and returns the original result, and it does not have to wait for lookup().
4. From the send cutoff onwards, send() is never called again, because a call
   that reached the provider after its 24 hours would be a new transfer. The
   outcome then comes only from lookup().

Sending and timing out as FAILED are separated in time. A send needs
now < cutoff, while a timeout failure needs now >= cutoff + 900. The compare-
and-swap only covers status, so a worker failing a payout could otherwise miss
an attempt recorded just after it read the row. This separation means that
cannot happen: any such attempt is already at least 900 seconds old.

Consequence: if the provider stays unreachable or nothing lands, the funds stay
held until about 23h45m after the first attempt, then the payout becomes FAILED.

Known limit: `now` is read once per invocation and the provider has no fencing
token. A worker that freezes between recording an attempt and calling send()
cannot be stopped from outside. The safety margin covers such stalls and clock
skew up to 30 minutes against the 24-hour limit. Separately, a stall of more
than 900 seconds that crosses the cutoff could land a transfer after FAILED was
written. Worker execution time limits should be well below 900 seconds.
"""

ProviderTimeout = TimeoutError

_IDEMPOTENCY_WINDOW_SECONDS = 24 * 60 * 60
_VISIBILITY_DELAY_SECONDS = 900
_SEND_SAFETY_MARGIN_SECONDS = 30 * 60

_TERMINAL_STATUSES = ("PAID", "FAILED")
_OUTCOME_BY_PROVIDER_STATUS = {"accepted": "PAID", "rejected": "FAILED"}


def execute_payout(store, provider, payout_id, account, amount_minor, dest, now) -> str:
    """Returns the payout's current status: "PAID", "FAILED", "PENDING" or "INSUFFICIENT"."""
    row = store.get_payout(payout_id)
    if row is None:
        store.reserve(payout_id, account, amount_minor, dest)
        # Rows are never deleted, so None here means reserve() declined and no
        # concurrent invocation has created the row either.
        row = store.get_payout(payout_id)
        if row is None:
            return "INSUFFICIENT"

    if row["status"] == "RESERVED":
        # If this loses the race, the winner has already recorded the timestamps.
        store.update(
            payout_id,
            "RESERVED",
            "SENDING",
            first_send_at=now,
            last_send_at=now,
        )
        row = store.get_payout(payout_id)

    if row["status"] in _TERMINAL_STATUSES:
        return row["status"]

    # The reference must be the same on every attempt by every worker.
    reference = str(payout_id)
    send_cutoff = (
        row["first_send_at"]
        + _IDEMPOTENCY_WINDOW_SECONDS
        - _SEND_SAFETY_MARGIN_SECONDS
    )

    if now < send_cutoff:
        # Write ahead of the send, so a worker that dies during the call still
        # leaves its attempt on record. max() stops an older `now` moving the
        # timestamp backwards. A failed swap means the payout has finished, so
        # no send may happen.
        recorded = store.update(
            payout_id,
            "SENDING",
            "SENDING",
            last_send_at=max(row["last_send_at"], now),
        )
        if not recorded:
            return _current_status(store, payout_id)
        try:
            result = provider.send(reference, row["dest"], row["amount_minor"])
        except ProviderTimeout:
            return _current_status(store, payout_id)
        return _settle(store, payout_id, result)

    try:
        result = provider.lookup(reference)
    except ProviderTimeout:
        return _current_status(store, payout_id)

    if result is not None:
        return _settle(store, payout_id, result)

    # send_cutoff also covers an attempt recorded after `row` was read. See the
    # module docstring.
    fail_at = max(row["last_send_at"], send_cutoff) + _VISIBILITY_DELAY_SECONDS
    if now >= fail_at:
        store.finish(
            payout_id,
            "SENDING",
            "FAILED",
            failure_reason="no_transfer_landed",
        )
    return _current_status(store, payout_id)


def _settle(store, payout_id, result) -> str:
    """Records a provider result and returns the true stored status."""
    outcome = _OUTCOME_BY_PROVIDER_STATUS.get(result["status"])
    if outcome is not None:
        # If this loses the race, a concurrent invocation has already finished
        # the payout, and the stored status is what gets returned.
        store.finish(
            payout_id,
            "SENDING",
            outcome,
            provider_id=result["provider_id"],
        )
    return _current_status(store, payout_id)


def _current_status(store, payout_id) -> str:
    """Reads the stored status, reporting non-terminal statuses as PENDING."""
    status = store.get_payout(payout_id)["status"]
    return status if status in _TERMINAL_STATUSES else "PENDING"
```
