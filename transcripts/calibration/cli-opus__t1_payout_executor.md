# cli-opus / t1_payout_executor / trial 1

- Requested: `opus`, resolved: `claude-haiku-5-5,claude-opus-5-5`, provider: claude-cli
- Run at 2026-10-31T14:43:08+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t1_payout_executor/prompt.md`.

## Model output

```python
"""Execute one customer payout through the external bank-transfer provider.

Safety rests on one rule: each payout gets at most one provider.send call.

The compare-and-swap from RESERVED to SENDING durably records the attempt time
before the call, and only the invocation that wins it may send. Every other
invocation, including restarts after a kill, can only use provider.lookup. This
prevents duplicate transfers, including after the provider's 24-hour idempotency
window. It also fixes last_send_at, so the 900-second check cannot race a later
attempt.

Trade-offs:
* A send that never landed, for example because the worker died just after the
  compare-and-swap, becomes FAILED after 900 seconds and is not retried.
* The provider offers no fencing. A worker frozen for 900 seconds or more
  between the compare-and-swap and send could still land a transfer after
  another invocation has recorded FAILED. If that worker later receives the
  result, a critical log is emitted for manual reconciliation.
"""

import logging

ProviderTimeout = TimeoutError

LOOKUP_VISIBILITY_SECONDS = 900

_OUTCOME_BY_PROVIDER_STATUS = {"accepted": "PAID", "rejected": "FAILED"}
_FINAL_STATUSES = frozenset({"PAID", "FAILED"})

logger = logging.getLogger(__name__)


def _reference(payout_id):
    """Return the stable provider reference for this payout."""
    return f"payout-{payout_id}"


def _current_status(store, payout_id):
    """Return the stored status, reporting non-terminal states as PENDING."""
    status = store.get_payout(payout_id)["status"]
    return status if status in _FINAL_STATUSES else "PENDING"


def _settle(store, payout_id, result):
    """Record a definitive provider result and return the true stored status."""
    outcome = _OUTCOME_BY_PROVIDER_STATUS[result["status"]]
    store.finish(
        payout_id,
        "SENDING",
        outcome,
        provider_id=result["provider_id"],
    )

    status = _current_status(store, payout_id)
    if status != outcome:
        logger.critical(
            "Payout %s needs reconciliation: provider outcome %s, stored status %s",
            payout_id,
            outcome,
            status,
        )
    return status


def _reconcile(store, provider, payout_id, last_send_at, now):
    """Resolve a SENDING payout without making another send call."""
    try:
        result = provider.lookup(_reference(payout_id))
    except ProviderTimeout:
        return _current_status(store, payout_id)

    if result is not None:
        return _settle(store, payout_id, result)

    if now - last_send_at >= LOOKUP_VISIBILITY_SECONDS:
        store.finish(payout_id, "SENDING", "FAILED")

    return _current_status(store, payout_id)


def execute_payout(store, provider, payout_id, account, amount_minor, dest, now) -> str:
    """Returns the payout's current status: "PAID", "FAILED", "PENDING" or "INSUFFICIENT"."""
    row = store.get_payout(payout_id)

    if row is None:
        reservation = store.reserve(payout_id, account, amount_minor, dest)
        if reservation == "INSUFFICIENT":
            return "INSUFFICIENT"
        row = store.get_payout(payout_id)

    if row["status"] == "RESERVED":
        if store.update(payout_id, "RESERVED", "SENDING", last_send_at=now):
            try:
                result = provider.send(
                    _reference(payout_id),
                    row["dest"],
                    row["amount_minor"],
                )
            except ProviderTimeout:
                return _current_status(store, payout_id)
            return _settle(store, payout_id, result)

        # A concurrent invocation won the claim and may already have finished.
        row = store.get_payout(payout_id)

    if row["status"] == "SENDING":
        return _reconcile(store, provider, payout_id, row["last_send_at"], now)

    return row["status"]
```
