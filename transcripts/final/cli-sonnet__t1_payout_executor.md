# cli-sonnet / t1_payout_executor / trial 1

- Requested: `sonnet`, resolved: `claude-haiku-5-5,claude-sonnet-5-5`, provider: claude-cli
- Run at 2026-10-31T20:35:00+00:00 with params `{}`
- Score 71%, full pass: False, finish: stop, error: None

## Failed checks

### `timeout_keeps_funds_held`

```
AssertionError: status: expected 'PENDING', got 'SENDING'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 214, in timeout_keeps_funds_held
    eq(call(mod, w), "PENDING", "status")
    ~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: status: expected 'PENDING', got 'SENDING'

```

### `lookup_timeout_is_pending`

```
AssertionError: status when provider is down: expected 'PENDING', got 'SENDING'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 223, in lookup_timeout_is_pending
    eq(call(mod, w, now=T0 + 5_000), "PENDING", "status when provider is down")
    ~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: status when provider is down: expected 'PENDING', got 'SENDING'

```

### `lagging_landed_transfer_is_not_failed`

```
AssertionError: status at +14m was SENDING: expected True, got False
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 233, in lagging_landed_transfer_is_not_failed
    eq(result in ("PENDING", "PAID"), True, f"status at +14m was {result}")
    ~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: status at +14m was SENDING: expected True, got False

```

### `never_landed_fails_after_window_and_releases`

```
AssertionError: first: expected 'PENDING', got 'SENDING'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 243, in never_landed_fails_after_window_and_releases
    eq(call(mod, w), "PENDING", "first")
    ~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 43, in eq
    raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
AssertionError: first: expected 'PENDING', got 'SENDING'

```

## Prompt

See `tasks/t1_payout_executor/prompt.md`.

## Model output

```python
"""Payout executor.

Design (why it is safe):

* The payout status only moves forward: RESERVED -> SENDING -> PAID | FAILED.
  The move RESERVED -> SENDING is a compare-and-swap, so exactly one worker
  ever wins the right to call provider.send() for a payout. That worker records
  `sent_at` (the time of the send attempt) in the same atomic update, BEFORE
  calling the provider. A worker killed at any instruction therefore leaves
  either "nothing sent, status RESERVED" or "SENDING with a recorded attempt time".
* send() is called at most once per payout, so the 24h idempotency window of the
  provider can never expire underneath us and cause a second transfer. Nothing
  ever moves SENDING back to RESERVED, so there is no ABA window in which a
  FAILED decision could race with a new send attempt.
* Anyone who finds the payout in SENDING resolves it using lookup() only:
    - provider knows the reference: accepted -> PAID, rejected -> FAILED
    - unknown and now - sent_at >= 900: no transfer can have landed -> FAILED
    - unknown and < 900 seconds: PENDING (funds stay held)
* The returned status is always re-read from the store, so a concurrent
  invocation that finished first is reflected correctly.
* A finished payout is never touched and no provider call is made for it.
"""

ProviderTimeout = TimeoutError

_VISIBILITY_WINDOW = 900  # seconds a landed transfer may take to show in lookup()
_TERMINAL = ("PAID", "FAILED")


def _stored_status(store, payout_id, default="PENDING"):
    """The true stored status right now."""
    row = store.get_payout(payout_id)
    if row is None:
        return default
    return row["status"]


def _outcome_from_provider(result):
    """Map a provider dict to 'PAID', 'FAILED' or None (unknown/unrecognised)."""
    if not isinstance(result, dict):
        return None
    status = result.get("status")
    if status == "accepted":
        return "PAID"
    if status == "rejected":
        return "FAILED"
    return None


def _finish(store, payout_id, outcome, result):
    """Try to finish from SENDING; the caller re-reads the status afterwards."""
    fields = {}
    provider_id = result.get("provider_id") if isinstance(result, dict) else None
    if provider_id is not None:
        fields["provider_id"] = provider_id
    store.finish(payout_id, "SENDING", outcome, **fields)


def _send_once(store, provider, row, payout_id):
    """Called only by the single worker that won the RESERVED -> SENDING claim."""
    try:
        result = provider.send(payout_id, row["dest"], row["amount_minor"])
    except ProviderTimeout:
        # The transfer may or may not have landed. Leave it SENDING; later
        # invocations resolve it through lookup().
        return _stored_status(store, payout_id)

    outcome = _outcome_from_provider(result)
    if outcome is not None:
        _finish(store, payout_id, outcome, result)
    # Unrecognised result: outcome unknown, leave SENDING and resolve via lookup.
    return _stored_status(store, payout_id)


def _resolve_sending(store, provider, row, payout_id, now):
    """The payout is SENDING and this invocation did not make the send."""
    try:
        found = provider.lookup(payout_id)
    except ProviderTimeout:
        return _stored_status(store, payout_id)

    if found is not None:
        outcome = _outcome_from_provider(found)
        if outcome is not None:
            _finish(store, payout_id, outcome, found)
        return _stored_status(store, payout_id)

    sent_at = row.get("sent_at")
    if sent_at is not None and now - sent_at >= _VISIBILITY_WINDOW:
        # Unknown to the provider, and any transfer made by the (possibly dead)
        # sender would be visible by now. No send can happen again, so this
        # cannot race with a new attempt.
        store.finish(payout_id, "SENDING", "FAILED", failure="not_found_after_window")
    return _stored_status(store, payout_id)


def execute_payout(store, provider, payout_id, account, amount_minor, dest, now) -> str:
    """Returns the payout's current status: "PAID", "FAILED", "PENDING" or "INSUFFICIENT"."""
    row = store.get_payout(payout_id)

    if row is None:
        reserved = store.reserve(payout_id, account, amount_minor, dest)
        if reserved == "INSUFFICIENT":
            return "INSUFFICIENT"
        # "CREATED" or "EXISTS" (a concurrent invocation created it): re-read.
        row = store.get_payout(payout_id)
        if row is None:
            return "PENDING"

    status = row["status"]
    if status in _TERMINAL:
        return status

    if status == "RESERVED":
        # Claim the single send right and persist the attempt time atomically,
        # before any provider call.
        if store.update(payout_id, "RESERVED", "SENDING", sent_at=now):
            row = store.get_payout(payout_id)
            if row is None:
                return "PENDING"
            if row["status"] in _TERMINAL:
                return row["status"]
            return _send_once(store, provider, row, payout_id)
        # Lost the race: someone else claimed (or finished). Re-read.
        row = store.get_payout(payout_id)
        if row is None:
            return "PENDING"
        status = row["status"]
        if status in _TERMINAL:
            return status

    if status == "SENDING":
        return _resolve_sending(store, provider, row, payout_id, now)

    # Any other (unexpected) stored status is reported as is.
    return status
```
