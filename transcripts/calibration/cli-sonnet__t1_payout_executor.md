# cli-sonnet / t1_payout_executor / trial 1

- Requested: `sonnet`, resolved: `claude-haiku-5-5,claude-sonnet-5-5`, provider: claude-cli
- Run at 2026-10-31T14:42:35+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t1_payout_executor/prompt.md`.

## Model output

```python
"""Payout executor.

Design (state machine, every transition a durable compare-and-swap):

    (no row) --reserve--> RESERVED --claim--> SENDING --finish--> PAID | FAILED

* The claim (RESERVED -> SENDING, saving ``sent_at``) is committed BEFORE the
  provider is called. Exactly one invocation can win it, so exactly one
  invocation ever calls ``provider.send`` for a payout. A killed worker can
  therefore never cause a second send, and the provider's 24-hour
  idempotency window never matters because we never repeat a send.
* Everything after the claim is read-only against the provider (``lookup``),
  which is authoritative and has no expiry.
* FAILED is written only when the provider rejected the transfer, or when
  ``lookup`` returns None at least 900 s after ``sent_at`` (a landed transfer
  must be visible by then). ``sent_at`` is written once and never moved.
* Provider timeouts are absorbed and reported as PENDING; funds stay held.
* The return value is always derived from a fresh read of the stored row
  whenever this invocation's own write may have lost a race.

Known residual risk: ``sent_at`` is the caller's ``now`` at claim time. If a
claiming worker stalls for more than 900 s between the claim commit and the
``send`` call, a later invocation could fail the payout before the send lands.
Closing that gap would need a provider-side or store-side fence, which the
interfaces do not offer.
"""

ProviderTimeout = TimeoutError

_TERMINAL = ("PAID", "FAILED")
_VISIBILITY_WINDOW = 900  # seconds a landed transfer may take to show in lookup


def _stored(store, payout_id):
    """Return the true stored status, mapped to the public vocabulary."""
    row = store.get_payout(payout_id)
    if row is None:
        # Should be impossible once a row has been reserved.
        raise RuntimeError("payout row vanished: %r" % (payout_id,))
    status = row["status"]
    return status if status in _TERMINAL else "PENDING"


def _apply_provider_result(store, payout_id, result):
    """Finish the payout from a provider response dict, if it is conclusive."""
    outcome = result.get("status")
    provider_id = result.get("provider_id")
    if outcome == "accepted":
        store.finish(payout_id, "SENDING", "PAID", provider_id=provider_id)
    elif outcome == "rejected":
        store.finish(
            payout_id, "SENDING", "FAILED",
            provider_id=provider_id, fail_reason="rejected",
        )
    # Unknown status: leave SENDING, stay PENDING.
    # If finish lost a race, _stored() reports whatever won.
    return _stored(store, payout_id)


def _send_once(store, provider, payout_id, dest, amount_minor):
    """Called only by the invocation that won the RESERVED -> SENDING claim."""
    try:
        result = provider.send(payout_id, dest, amount_minor)
    except ProviderTimeout:
        # May or may not have landed. Never resend; resolve via lookup later.
        return _stored(store, payout_id)
    if not isinstance(result, dict):
        return _stored(store, payout_id)
    return _apply_provider_result(store, payout_id, result)


def _resolve_sending(store, provider, payout_id, row, now):
    """Payout is SENDING: find out what happened without sending anything."""
    try:
        found = provider.lookup(payout_id)
    except ProviderTimeout:
        return _stored(store, payout_id)

    if found is not None:
        if isinstance(found, dict):
            return _apply_provider_result(store, payout_id, found)
        return _stored(store, payout_id)

    sent_at = row.get("sent_at")
    if sent_at is not None and now - sent_at >= _VISIBILITY_WINDOW:
        # Unknown to the provider and any landed transfer would be visible by
        # now: nothing left. Release the held funds.
        store.finish(
            payout_id, "SENDING", "FAILED",
            fail_reason="not_found_after_visibility_window",
        )
    return _stored(store, payout_id)


def execute_payout(store, provider, payout_id, account, amount_minor, dest, now) -> str:
    """Returns the payout's current status: "PAID", "FAILED", "PENDING" or "INSUFFICIENT"."""
    row = store.get_payout(payout_id)

    if row is None:
        reserved = store.reserve(payout_id, account, amount_minor, dest)
        if reserved == "INSUFFICIENT":
            return "INSUFFICIENT"
        # "CREATED" or "EXISTS" (a concurrent invocation created it first).
        row = store.get_payout(payout_id)
        if row is None:
            raise RuntimeError("payout row missing after reserve: %r" % (payout_id,))

    status = row["status"]

    if status in _TERMINAL:
        return status

    if status == "RESERVED":
        # Durably record the attempt before calling the provider. Only the
        # winner of this CAS may ever call send().
        if not store.update(payout_id, "RESERVED", "SENDING", sent_at=now):
            return _stored(store, payout_id)
        # Use the stored row's values so every attempt agrees with the reservation.
        return _send_once(
            store, provider, payout_id, row["dest"], row["amount_minor"]
        )

    if status == "SENDING":
        return _resolve_sending(store, provider, payout_id, row, now)

    # Unknown status: do not touch money.
    return "PENDING"
```
