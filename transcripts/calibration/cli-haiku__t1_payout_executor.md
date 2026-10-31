# cli-haiku / t1_payout_executor / trial 1

- Requested: `haiku`, resolved: `claude-haiku-5-5`, provider: claude-cli
- Run at 2026-10-31T14:45:36+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t1_payout_executor/prompt.md`.

## Model output

```python
"""Single-payout executor for an at-most-once bank transfer.

Invariants this module relies on:

* Every provider call for a payout uses the same deterministic reference,
  "payout:<payout_id>". The provider treats repeats within 24h of first
  sight as the same transfer, so repeats cannot move money twice.
* first_sent_at is written before the first send, and last_sent_at is
  written before every send. A worker that dies mid-send leaves a timestamp
  that bounds when its transfer could have landed.
* No send is issued once now - first_sent_at >= SEND_CUTOFF. The cutoff is
  well before the provider forgets the reference, so the reference is never
  reused after expiry. After the cutoff only lookup() is used.
* FAILED is written only on a provider rejection, or when lookup() reports
  nothing and at least QUIET_SECONDS have passed since the most recent
  recorded send attempt.
* Terminal statuses are returned immediately with no provider calls.
* Every return value is re-read from the store, so it reflects the true
  stored status even if another invocation finished the payout first.

Known residual: the store offers no fencing token, so a sender that stalls
between recording its attempt and calling send for longer than
QUIET_SECONDS could race a concurrent FAILED decision. Deployments should
keep worker stalls well below QUIET_SECONDS.
"""

ProviderTimeout = TimeoutError

SEND_WINDOW = 24 * 3600                # provider idempotency window for a reference
SEND_CUTOFF = SEND_WINDOW - 3600       # stop sending 1h before the reference can expire
QUIET_SECONDS = 900                    # max lookup visibility delay for a landed transfer
TERMINAL = ("PAID", "FAILED")


def _reference(payout_id):
    return f"payout:{payout_id}"


def _current(store, payout_id):
    """Map the true stored state to a return value."""
    row = store.get_payout(payout_id)
    if row is not None and row["status"] in TERMINAL:
        return row["status"]
    return "PENDING"


def _send(store, provider, payout_id, ref, dest, amount, status, first, now):
    # Write-ahead: record the attempt before the provider can see it.
    if first is None:
        ok = store.update(payout_id, status, "SENDING",
                          first_sent_at=now, last_sent_at=now)
    else:
        ok = store.update(payout_id, status, "SENDING", last_sent_at=now)
    if not ok:
        # Status changed under us, so another invocation moved the payout on.
        return _current(store, payout_id)

    try:
        resp = provider.send(ref, dest, amount)
    except ProviderTimeout:
        # The transfer may or may not have landed. Keep the funds held.
        return "PENDING"

    verdict = resp.get("status")
    if verdict == "accepted":
        store.finish(payout_id, "SENDING", "PAID",
                     provider_id=resp.get("provider_id"))
    elif verdict == "rejected":
        store.finish(payout_id, "SENDING", "FAILED",
                     provider_id=resp.get("provider_id"))
    else:
        return "PENDING"
    return _current(store, payout_id)


def _lookup_only(store, provider, payout_id, ref, status, last, now):
    # Past the send cutoff: never send again, only ask the provider.
    try:
        found = provider.lookup(ref)
    except ProviderTimeout:
        return "PENDING"

    if found is not None:
        verdict = found.get("status")
        if verdict == "accepted":
            store.finish(payout_id, status, "PAID",
                         provider_id=found.get("provider_id"))
        elif verdict == "rejected":
            store.finish(payout_id, status, "FAILED",
                         provider_id=found.get("provider_id"))
        return _current(store, payout_id)

    # lookup says unknown. Only a quiet period after the most recent
    # recorded attempt proves that no transfer can still land.
    if last is not None and now - last >= QUIET_SECONDS:
        store.finish(payout_id, status, "FAILED", no_transfer_proven_at=now)
    return _current(store, payout_id)


def execute_payout(store, provider, payout_id, account, amount_minor, dest, now) -> str:
    """Returns the payout's current status: "PAID", "FAILED", "PENDING" or "INSUFFICIENT"."""
    row = store.get_payout(payout_id)
    if row is None:
        if store.reserve(payout_id, account, amount_minor, dest) == "INSUFFICIENT":
            return "INSUFFICIENT"
        row = store.get_payout(payout_id)
        if row is None:
            raise RuntimeError(f"payout {payout_id} missing after reserve")

    status = row["status"]
    if status in TERMINAL:
        return status

    # Use the stored terms, not the arguments, so every attempt is identical.
    ref = _reference(payout_id)
    amount = row["amount_minor"]
    dest_stored = row["dest"]
    first = row.get("first_sent_at")
    last = row.get("last_sent_at")

    if first is None or now - first < SEND_CUTOFF:
        return _send(store, provider, payout_id, ref, dest_stored, amount,
                     status, first, now)
    return _lookup_only(store, provider, payout_id, ref, status, last, now)
```
