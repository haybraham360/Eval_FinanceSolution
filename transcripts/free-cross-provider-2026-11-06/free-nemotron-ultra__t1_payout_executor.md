# free-nemotron-ultra / t1_payout_executor / trial 1

- Requested: `nvidia/nemotron-3-ultra-550b-a55b:free`, resolved: `nvidia/nemotron-3-ultra-550b-a55b:free`, provider: Nvidia
- Run at 2026-11-06T19:51:45+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t1_payout_executor/prompt.md`.

## Model output

```python
ProviderTimeout = TimeoutError

def execute_payout(store, provider, payout_id, account, amount_minor, dest, now) -> str:
    while True:
        # Ensure a payout row exists and funds are reserved
        reserve_result = store.reserve(payout_id, account, amount_minor, dest)
        if reserve_result == "INSUFFICIENT":
            return "INSUFFICIENT"

        payout = store.get_payout(payout_id)
        if payout is None:
            continue  # should not happen, but retry if it does

        status = payout["status"]
        if status in ("PAID", "FAILED"):
            return status

        if status == "RESERVED":
            reference = payout_id
            # Claim the right to send by moving to SENDING
            updated = store.update(
                payout_id,
                expected_status="RESERVED",
                new_status="SENDING",
                provider_reference=reference,
                send_time=now
            )
            if not updated:
                continue  # another worker changed the status, retry

            # We are the designated sender
            try:
                send_result = provider.send(reference, dest, amount_minor)
            except ProviderTimeout:
                send_result = None

            if send_result is not None:
                # Definitive response from send
                if send_result["status"] == "accepted":
                    finished = store.finish(
                        payout_id,
                        expected_status="SENDING",
                        outcome="PAID",
                        provider_id=send_result["provider_id"]
                    )
                    if finished:
                        return "PAID"
                    else:
                        continue
                else:  # rejected
                    finished = store.finish(
                        payout_id,
                        expected_status="SENDING",
                        outcome="FAILED",
                        provider_id=send_result["provider_id"]
                    )
                    if finished:
                        return "FAILED"
                    else:
                        continue
            else:
                # Send timed out – check lookup immediately
                try:
                    lookup_result = provider.lookup(reference)
                except ProviderTimeout:
                    return "PENDING"

                if lookup_result is None:
                    return "PENDING"
                if lookup_result["status"] == "accepted":
                    finished = store.finish(
                        payout_id,
                        expected_status="SENDING",
                        outcome="PAID",
                        provider_id=lookup_result["provider_id"]
                    )
                    if finished:
                        return "PAID"
                    else:
                        continue
                else:  # rejected
                    finished = store.finish(
                        payout_id,
                        expected_status="SENDING",
                        outcome="FAILED",
                        provider_id=lookup_result["provider_id"]
                    )
                    if finished:
                        return "FAILED"
                    else:
                        continue

        elif status == "SENDING":
            reference = payout.get("provider_reference")
            send_time = payout.get("send_time")
            if reference is None or send_time is None:
                # Inconsistent state – cannot safely proceed
                return "PENDING"

            if now - send_time >= 900:
                # 900 seconds have passed since the send attempt
                try:
                    lookup_result = provider.lookup(reference)
                except ProviderTimeout:
                    return "PENDING"

                if lookup_result is None:
                    finished = store.finish(payout_id, expected_status="SENDING", outcome="FAILED")
                    if finished:
                        return "FAILED"
                    else:
                        continue
                if lookup_result["status"] == "accepted":
                    finished = store.finish(
                        payout_id,
                        expected_status="SENDING",
                        outcome="PAID",
                        provider_id=lookup_result["provider_id"]
                    )
                    if finished:
                        return "PAID"
                    else:
                        continue
                else:  # rejected
                    finished = store.finish(
                        payout_id,
                        expected_status="SENDING",
                        outcome="FAILED",
                        provider_id=lookup_result["provider_id"]
                    )
                    if finished:
                        return "FAILED"
                    else:
                        continue
            else:
                # Less than 900 seconds – check for early resolution
                try:
                    lookup_result = provider.lookup(reference)
                except ProviderTimeout:
                    return "PENDING"

                if lookup_result is None:
                    return "PENDING"
                if lookup_result["status"] == "accepted":
                    finished = store.finish(
                        payout_id,
                        expected_status="SENDING",
                        outcome="PAID",
                        provider_id=lookup_result["provider_id"]
                    )
                    if finished:
                        return "PAID"
                    else:
                        continue
                elif lookup_result["status"] == "rejected":
                    finished = store.finish(
                        payout_id,
                        expected_status="SENDING",
                        outcome="FAILED",
                        provider_id=lookup_result["provider_id"]
                    )
                    if finished:
                        return "FAILED"
                    else:
                        continue
                else:
                    return "PENDING"

        else:
            # Unknown status – should not occur
            return "PENDING"
```
