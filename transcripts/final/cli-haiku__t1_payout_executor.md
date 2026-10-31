# cli-haiku / t1_payout_executor / trial 1

- Requested: `haiku`, resolved: `claude-haiku-5-5`, provider: claude-cli
- Run at 2026-10-31T20:47:53+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t1_payout_executor/prompt.md`.

## Model output

```python
"""Payout executor: at-most-once money movement across kills, retries and concurrency.

Stored statuses: RESERVED -> SENDING -> PAID | FAILED. PENDING is only ever returned.

Safety outline:
* The provider reference is payout_id. The provider deduplicates sends for 24h from
  the first time it sees the reference. All sends happen only while
  now < first_attempt + _SEND_WINDOW, where _SEND_WINDOW leaves a margin below 24h.
  Every such send is therefore a deduplicated repeat. Once the window closes, the
  executor never calls send again.
* Every send attempt is durably recorded before the provider is called. Each attempt
  gets its own uniquely named field, so concurrent writers never overwrite one another
  and max() over the fields is the true latest attempt.
* After the window, a decider writes a "decide" field, re-reads the attempts, and only
  then calls lookup. A sender re-reads after recording its attempt and aborts if it sees
  a decide field. This handshake means that any send the decider cannot see has been
  aborted, so the decider's view of the latest attempt is complete.
* The decider fails the payout only if lookup returns None and at least 900 seconds have
  passed since the latest attempt, which is the condition in the requirements.
* Stored row fields (dest, amount_minor) are used for the provider call, not the arguments
  of this invocation.
"""

import uuid

ProviderTimeout = TimeoutError

_TERMINAL = ("PAID", "FAILED")
_ATTEMPT_PREFIX = "send_attempt__"
_DECIDE_PREFIX = "decide_intent__"

_DAY_SECONDS = 24 * 60 * 60
_VISIBILITY_DELAY = 900
_SEND_WINDOW = _DAY_SECONDS - _VISIBILITY_DELAY  # margin below the provider's 24h memory
_LOOKUP_DELAY = _VISIBILITY_DELAY


def _fetch(store, payout_id):
    row = store.get_payout(payout_id)
    if row is None:
        raise RuntimeError(f"payout {payout_id!r} disappeared from the store")
    return row


def _attempt_times(row):
    return [v for k, v in row.items() if k.startswith(_ATTEMPT_PREFIX)]


def _decision_in_progress(row):
    return any(k.startswith(_DECIDE_PREFIX) for k in row)


def _record_attempt(store, payout_id, expected, now):
    # One uniquely named field per attempt. Writers never overwrite each other.
    key = _ATTEMPT_PREFIX + uuid.uuid4().hex
    return store.update(payout_id, expected, "SENDING", **{key: now})


def _decide_after_window(store, provider, payout_id, now):
    """Runs only when now >= first_attempt + _SEND_WINDOW. Never calls send.

    Returns a status to return to the caller, or None if the row changed and the
    caller must re-read and loop again.
    """
    # Step 1: announce the decision (Dekker handshake with senders).
    key = _DECIDE_PREFIX + uuid.uuid4().hex
    if not store.update(payout_id, "SENDING", "SENDING", **{key: now}):
        return None

    # Step 2: snapshot the attempts. This includes every attempt that any sender
    # recorded before our announcement, because senders check for announcements
    # after recording.
    row = _fetch(store, payout_id)
    if row["status"] in _TERMINAL:
        return row["status"]
    last_attempt = max(_attempt_times(row))  # SENDING implies at least one attempt

    # Step 3: ask the authoritative source.
    try:
        info = provider.lookup(payout_id)
    except ProviderTimeout:
        return "PENDING"

    if info is not None:
        verdict = info.get("status")
        if verdict == "accepted":
            if store.finish(payout_id, "SENDING", "PAID", provider_id=info.get("provider_id")):
                return "PAID"
            return None
        if verdict == "rejected":
            if store.finish(payout_id, "SENDING", "FAILED", provider_id=info.get("provider_id")):
                return "FAILED"
            return None
        return "PENDING"

    # Step 4: lookup says nothing landed. Fail only once a landed transfer
    # would certainly be visible, measured from the latest attempt.
    if now - last_attempt < _LOOKUP_DELAY:
        return "PENDING"
    if store.finish(payout_id, "SENDING", "FAILED"):
        return "FAILED"
    return None


def execute_payout(store, provider, payout_id, account, amount_minor, dest, now) -> str:
    """Returns the payout's current status: "PAID", "FAILED", "PENDING" or "INSUFFICIENT"."""
    row = store.get_payout(payout_id)
    if row is None:
        result = store.reserve(payout_id, account, amount_minor, dest)
        row = store.get_payout(payout_id)
        if row is None:
            if result == "INSUFFICIENT":
                return "INSUFFICIENT"
            raise RuntimeError(f"reserve returned {result!r} but no row exists")

    while True:
        status = row["status"]
        if status in _TERMINAL:
            # Requirement 5: finished payouts never change and never touch the provider.
            return status

        if status == "RESERVED":
            # First attempt. This is the moment the provider may first see the reference.
            if not _record_attempt(store, payout_id, "RESERVED", now):
                row = _fetch(store, payout_id)
                continue
        else:  # SENDING
            attempts = _attempt_times(row)
            if not attempts:
                raise RuntimeError("SENDING payout has no recorded send attempt")
            if now >= min(attempts) + _SEND_WINDOW:
                # Past the provider's idempotency window: never send again.
                outcome = _decide_after_window(store, provider, payout_id, now)
                if outcome is not None:
                    return outcome
                row = _fetch(store, payout_id)
                continue
            # Inside the window: a repeat send is safe and returns the original result.
            if not _record_attempt(store, payout_id, "SENDING", now):
                row = _fetch(store, payout_id)
                continue

        # The attempt is recorded. Abort if a decider has announced itself,
        # because it may already have taken its snapshot without seeing this attempt.
        row = _fetch(store, payout_id)
        if _decision_in_progress(row):
            return "PENDING"

        try:
            res = provider.send(payout_id, row["dest"], row["amount_minor"])
        except ProviderTimeout:
            # Outcome unknown. Funds stay held. The next invocation re-sends within
            # the window, which is idempotent.
            return "PENDING"

        verdict = res.get("status")
        if verdict == "accepted":
            if store.finish(payout_id, "SENDING", "PAID", provider_id=res.get("provider_id")):
                return "PAID"
        elif verdict == "rejected":
            if store.finish(payout_id, "SENDING", "FAILED", provider_id=res.get("provider_id")):
                return "FAILED"
        else:
            return "PENDING"

        # A concurrent invocation changed the row. Re-read the true status and loop.
        row = _fetch(store, payout_id)
```
