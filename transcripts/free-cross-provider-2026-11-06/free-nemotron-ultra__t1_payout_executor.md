# free-nemotron-ultra / t1_payout_executor / trial 1

- Requested: `nvidia/nemotron-3-ultra-550b-a55b:free`, resolved: `nvidia/nemotron-3-ultra-550b-a55b:free`, provider: Nvidia
- Run at 2026-11-06T19:51:45+00:00 with params `{}`
- Score 0%, full pass: False, finish: stop, error: None

## Failed checks

### `happy_path`

```
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 178, in happy_path
    eq(call(mod, w), "PAID", "status")
       ~~~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 120, in call
    return mod.execute_payout(w, w, pid, "acct", amount, "dest", w.now)
           ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/var/folders/wt/_mv5vhb14bb8t2fdrh0lqm6r0000gn/T/tmpysc4v1pr.py", line 21, in execute_payout
    updated = store.update(
        payout_id,
    ...<3 lines>...
        send_time=now
    )
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'

```

### `insufficient_sends_nothing_and_is_not_sticky`

```
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 189, in insufficient_sends_nothing_and_is_not_sticky
    eq(call(mod, w), "PAID", "after funds arrive")
       ~~~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 120, in call
    return mod.execute_payout(w, w, pid, "acct", amount, "dest", w.now)
           ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/var/folders/wt/_mv5vhb14bb8t2fdrh0lqm6r0000gn/T/tmpysc4v1pr.py", line 21, in execute_payout
    updated = store.update(
        payout_id,
    ...<3 lines>...
        send_time=now
    )
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'

```

### `rejected_releases_funds_and_stays_failed`

```
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 195, in rejected_releases_funds_and_stays_failed
    eq(call(mod, w), "FAILED", "status")
       ~~~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 120, in call
    return mod.execute_payout(w, w, pid, "acct", amount, "dest", w.now)
           ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/var/folders/wt/_mv5vhb14bb8t2fdrh0lqm6r0000gn/T/tmpysc4v1pr.py", line 21, in execute_payout
    updated = store.update(
        payout_id,
    ...<3 lines>...
        send_time=now
    )
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'

```

### `finished_payout_makes_no_money_moving_calls`

```
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 204, in finished_payout_makes_no_money_moving_calls
    call(mod, w)
    ~~~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 120, in call
    return mod.execute_payout(w, w, pid, "acct", amount, "dest", w.now)
           ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/var/folders/wt/_mv5vhb14bb8t2fdrh0lqm6r0000gn/T/tmpysc4v1pr.py", line 21, in execute_payout
    updated = store.update(
        payout_id,
    ...<3 lines>...
        send_time=now
    )
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'

```

### `timeout_keeps_funds_held`

```
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 214, in timeout_keeps_funds_held
    eq(call(mod, w), "PENDING", "status")
       ~~~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 120, in call
    return mod.execute_payout(w, w, pid, "acct", amount, "dest", w.now)
           ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/var/folders/wt/_mv5vhb14bb8t2fdrh0lqm6r0000gn/T/tmpysc4v1pr.py", line 21, in execute_payout
    updated = store.update(
        payout_id,
    ...<3 lines>...
        send_time=now
    )
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'

```

### `lookup_timeout_is_pending`

```
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 221, in lookup_timeout_is_pending
    call(mod, w)
    ~~~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 120, in call
    return mod.execute_payout(w, w, pid, "acct", amount, "dest", w.now)
           ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/var/folders/wt/_mv5vhb14bb8t2fdrh0lqm6r0000gn/T/tmpysc4v1pr.py", line 21, in execute_payout
    updated = store.update(
        payout_id,
    ...<3 lines>...
        send_time=now
    )
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'

```

### `lagging_landed_transfer_is_not_failed`

```
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 231, in lagging_landed_transfer_is_not_failed
    call(mod, w)
    ~~~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 120, in call
    return mod.execute_payout(w, w, pid, "acct", amount, "dest", w.now)
           ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/var/folders/wt/_mv5vhb14bb8t2fdrh0lqm6r0000gn/T/tmpysc4v1pr.py", line 21, in execute_payout
    updated = store.update(
        payout_id,
    ...<3 lines>...
        send_time=now
    )
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'

```

### `never_landed_fails_after_window_and_releases`

```
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 243, in never_landed_fails_after_window_and_releases
    eq(call(mod, w), "PENDING", "first")
       ~~~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 120, in call
    return mod.execute_payout(w, w, pid, "acct", amount, "dest", w.now)
           ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/var/folders/wt/_mv5vhb14bb8t2fdrh0lqm6r0000gn/T/tmpysc4v1pr.py", line 21, in execute_payout
    updated = store.update(
        payout_id,
    ...<3 lines>...
        send_time=now
    )
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'

```

### `window_runs_from_most_recent_send`

```
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 257, in window_runs_from_most_recent_send
    call(mod, w)
    ~~~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 120, in call
    return mod.execute_payout(w, w, pid, "acct", amount, "dest", w.now)
           ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/var/folders/wt/_mv5vhb14bb8t2fdrh0lqm6r0000gn/T/tmpysc4v1pr.py", line 21, in execute_payout
    updated = store.update(
        payout_id,
    ...<3 lines>...
        send_time=now
    )
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'

```

### `landed_then_retry_after_provider_forgot`

```
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 269, in landed_then_retry_after_provider_forgot
    call(mod, w)
    ~~~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 120, in call
    return mod.execute_payout(w, w, pid, "acct", amount, "dest", w.now)
           ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/var/folders/wt/_mv5vhb14bb8t2fdrh0lqm6r0000gn/T/tmpysc4v1pr.py", line 21, in execute_payout
    updated = store.update(
        payout_id,
    ...<3 lines>...
        send_time=now
    )
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'

```

### `kill_at_every_operation_retry_soon`

```
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 151, in op_count
    call(mod, w)
    ~~~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 120, in call
    return mod.execute_payout(w, w, pid, "acct", amount, "dest", w.now)
           ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/var/folders/wt/_mv5vhb14bb8t2fdrh0lqm6r0000gn/T/tmpysc4v1pr.py", line 21, in execute_payout
    updated = store.update(
        payout_id,
    ...<3 lines>...
        send_time=now
    )
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'

```

### `kill_at_every_operation_retry_after_24h`

```
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 151, in op_count
    call(mod, w)
    ~~~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 120, in call
    return mod.execute_payout(w, w, pid, "acct", amount, "dest", w.now)
           ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/var/folders/wt/_mv5vhb14bb8t2fdrh0lqm6r0000gn/T/tmpysc4v1pr.py", line 21, in execute_payout
    updated = store.update(
        payout_id,
    ...<3 lines>...
        send_time=now
    )
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'

```

### `duplicate_invocation_at_every_operation`

```
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 151, in op_count
    call(mod, w)
    ~~~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 120, in call
    return mod.execute_payout(w, w, pid, "acct", amount, "dest", w.now)
           ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/var/folders/wt/_mv5vhb14bb8t2fdrh0lqm6r0000gn/T/tmpysc4v1pr.py", line 21, in execute_payout
    updated = store.update(
        payout_id,
    ...<3 lines>...
        send_time=now
    )
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'

```

### `returns_stored_truth_when_another_worker_wins`

```
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 316, in returns_stored_truth_when_another_worker_wins
    eq(call(mod, w), "FAILED", "returned status")
       ~~~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t1_payout_executor.py", line 120, in call
    return mod.execute_payout(w, w, pid, "acct", amount, "dest", w.now)
           ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/var/folders/wt/_mv5vhb14bb8t2fdrh0lqm6r0000gn/T/tmpysc4v1pr.py", line 21, in execute_payout
    updated = store.update(
        payout_id,
    ...<3 lines>...
        send_time=now
    )
TypeError: World.update() missing 2 required positional arguments: 'expected' and 'new'

```

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
