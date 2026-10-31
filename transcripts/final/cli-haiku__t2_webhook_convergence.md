# cli-haiku / t2_webhook_convergence / trial 2

- Requested: `haiku`, resolved: `claude-haiku-5-5`, provider: claude-cli
- Run at 2026-10-31T20:48:59+00:00 with params `{}`
- Score 77%, full pass: False, finish: stop, error: None

## Failed checks

### `decision_before_open_has_no_effect`

```
AssertionError: order ['e-c1', 'e-dd-2026-03-01T10:00:00+00:00', 'e-do']: expected {'available': 700, 'reserved': 0, 'chargeback_loss': 0, 'dispute_fee': 0, 'unapplied_refund': 0}, got {'available': 700, 'reserved': 0, 'chargeback_loss': 0, 'dispute_fee': 1500, 'unapplied_refund': 0}
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t2_webhook_convergence.py", line 158, in decision_before_open_has_no_effect
    all_orders(mod, [cap("c1", 700), ddec("won", "2026-03-01T10:00:00+00:00"), dopen(700)])
    ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t2_webhook_convergence.py", line 95, in all_orders
    raise AssertionError(f"order {[e['event_id'] for e in order]}: expected {want}, got {got}")
AssertionError: order ['e-c1', 'e-dd-2026-03-01T10:00:00+00:00', 'e-do']: expected {'available': 700, 'reserved': 0, 'chargeback_loss': 0, 'dispute_fee': 0, 'unapplied_refund': 0}, got {'available': 700, '
```

### `arbitration_flip_restores_fee_position`

```
AssertionError: order ['e-c1', 'e-do', 'e-dd-2026-03-01T10:00:00+00:00', 'e-dd-2026-03-02T10:00:00+00:00']: expected {'available': 700, 'reserved': 0, 'chargeback_loss': 0, 'dispute_fee': 0, 'unapplied_refund': 0}, got {'available': 700, 'reserved': 0, 'chargeback_loss': 0, 'dispute_fee': 1500, 'unapplied_refund': 0}
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t2_webhook_convergence.py", line 173, in arbitration_flip_restores_fee_position
    all_orders(mod, [cap("c1", 700), dopen(300), ddec("lost", "2026-03-01T10:00:00+00:00"), ddec("won", "2026-03-02T10:00:00+00:00")])
    ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t2_webhook_convergence.py", line 95, in all_orders
    raise AssertionError(f"order {[e['event_id'] for e in order]}: expected {want}, got {got}")
AssertionError: order ['e-c1', 'e-do', 'e-dd-2026-03-01T10:00:00+00:00', 'e-dd-20
```

### `big_mixed_scenario_random_orders`

```
AssertionError: order ['e-r3', 'e-r1', 'e-do', 'e-c2-again', 'e-c1', 'e-dd-2026-03-01T10:00:00-05:00', 'e-r2-f', 'e-c2', 'e-r2', 'e-dd-2026-03-01T14:00:00+00:00']: expected {'available': 0, 'reserved': 0, 'chargeback_loss': 0, 'dispute_fee': 0, 'unapplied_refund': 500}, got {'available': 0, 'reserved': 0, 'chargeback_loss': 0, 'dispute_fee': 1500, 'unapplied_refund': 500}
Traceback (most recent call last):
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/common.py", line 29, in run
    fn(target)
    ~~^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t2_webhook_convergence.py", line 180, in big_mixed_scenario_random_orders
    all_orders(mod, events, limit=1500)
    ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/macbookm1/Desktop/micro_hackerthon/ledger-eval/graders/t2_webhook_convergence.py", line 95, in all_orders
    raise AssertionError(f"order {[e['event_id'] for e in order]}: expected {want}, got {got}")
AssertionError: order ['e-r3', 'e-r1', 'e-do', 'e-c2-again', 'e-c1', 'e-dd-2026-03-01T10:00:00-05:00', 'e-r2-f', 'e-c2', 'e-r2', 'e-dd-2026-03-01T14:00:00+00:00']: expected {'available': 0, 'reserved': 0, 'chargeback_loss
```

## Prompt

See `tasks/t2_webhook_convergence/prompt.md`.

## Model output

```python
"""Payment position projection built from PSP webhooks.

State is plain JSON-compatible data (dicts keyed by str, ints, bools, strs, None,
lists). Money is integer minor units. The position is always derived from the
set of distinct business facts, so arrival order and repeats cannot change it.
The journal records only the deltas between successive positions, balanced by
psp_clearing per delivery.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

DISPUTE_FEE_MINOR = 1500

_ACCOUNTS = ("available", "reserved", "chargeback_loss", "dispute_fee", "unapplied_refund")
_CONTRA = "psp_clearing"
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_ISO_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})[Tt ](\d{2}:\d{2}:\d{2})(?:[.,](\d+))?(Z|z|[+-]\d{2}(?::?\d{2})?)$"
)


def _ident(value, field):
    # Must be a str: state dict keys must survive a JSON round trip unchanged.
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _money(value, field):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative int in minor units")
    return value


def _instant_us(text):
    """Parse an ISO-8601 instant with UTC offset into integer microseconds since epoch."""
    if not isinstance(text, str):
        raise ValueError("decided_at must be an ISO-8601 string with UTC offset")
    m = _ISO_RE.match(text.strip())
    if not m:
        raise ValueError(f"invalid decided_at: {text!r}")
    day, clock, frac, off = m.groups()
    frac = (frac or "")[:6].ljust(6, "0")
    if off in ("Z", "z"):
        off = "+00:00"
    else:
        digits = off[1:].replace(":", "")
        hh, mm = digits[:2], (digits[2:] or "00")
        off = f"{off[0]}{hh}:{mm}"
    try:
        dt = datetime.fromisoformat(f"{day}T{clock}.{frac}{off}")
    except ValueError as exc:
        raise ValueError(f"invalid decided_at: {text!r}") from exc
    if dt.tzinfo is None:
        raise ValueError("decided_at must carry a UTC offset")
    return (dt - _EPOCH) // timedelta(microseconds=1)


def _init(state: dict) -> None:
    state.setdefault("captures", {})    # capture_id -> amount
    state.setdefault("refunds", {})     # refund_id -> {amount, succeeded, failed}
    state.setdefault("disputes", {})    # dispute_id -> {amount, opened, decision}
    state.setdefault("events", {})      # event_id -> True (delivery dedupe)
    state.setdefault("journal", [])
    state.setdefault("applied", {a: 0 for a in _ACCOUNTS})


def _target(state: dict) -> dict:
    """Position implied by the set of distinct facts. Independent of event order."""
    captured = sum(state.get("captures", {}).values())

    refunded = 0
    for r in state.get("refunds", {}).values():
        # refund.failed is terminal: a failed refund never counts.
        if r["succeeded"] and not r["failed"] and r["amount"] is not None:
            refunded += r["amount"]

    taken = min(refunded, captured)          # refunds never exceed captures
    unapplied = refunded - taken             # excess refund, not taken from merchant
    money = captured - taken                 # merchant money after refunds

    remaining = money                        # disputes only touch this money
    reserved = 0
    loss = 0
    fee = 0
    for did in sorted(state.get("disputes", {})):   # deterministic order
        d = state["disputes"][did]
        if not d["opened"]:
            # A decision before dispute.opened has no financial effect.
            continue
        fee += DISPUTE_FEE_MINOR
        touched = min(d["amount"], remaining)  # shrinks if refunds reduce money
        remaining -= touched
        decision = d["decision"]
        outcome = decision["outcome"] if decision else None
        if outcome == "won":
            continue                         # money stays available
        if outcome == "lost":
            loss += touched
        else:
            reserved += touched              # open or undecided

    return {
        "available": money - reserved - loss,
        "reserved": reserved,
        "chargeback_loss": loss,
        "dispute_fee": fee,
        "unapplied_refund": unapplied,
    }


def apply_event(state: dict, event: dict) -> None:
    _init(state)

    eid = _ident(event.get("event_id"), "event_id")
    if eid in state["events"]:
        return  # same delivery seen again

    kind = event.get("type")

    # Parse and validate everything before mutating, so a bad event changes nothing.
    if kind == "capture.succeeded":
        cid = _ident(event.get("capture_id"), "capture_id")
        amt = _money(event.get("amount_minor"), "amount_minor")
        # Same fact may be re-issued under a new event_id: key by capture_id, count once.
        state["captures"][cid] = max(state["captures"].get(cid, 0), amt)

    elif kind == "refund.succeeded":
        rid = _ident(event.get("refund_id"), "refund_id")
        amt = _money(event.get("amount_minor"), "amount_minor")
        r = state["refunds"].setdefault(
            rid, {"amount": None, "succeeded": False, "failed": False}
        )
        r["succeeded"] = True
        r["amount"] = amt if r["amount"] is None else max(r["amount"], amt)

    elif kind == "refund.failed":
        rid = _ident(event.get("refund_id"), "refund_id")
        r = state["refunds"].setdefault(
            rid, {"amount": None, "succeeded": False, "failed": False}
        )
        r["failed"] = True

    elif kind == "dispute.opened":
        did = _ident(event.get("dispute_id"), "dispute_id")
        amt = _money(event.get("amount_minor"), "amount_minor")
        d = state["disputes"].setdefault(
            did, {"amount": None, "opened": False, "decision": None}
        )
        d["opened"] = True
        d["amount"] = amt if d["amount"] is None else max(d["amount"], amt)

    elif kind == "dispute.decided":
        did = _ident(event.get("dispute_id"), "dispute_id")
        outcome = event.get("outcome")
        if outcome not in ("won", "lost"):
            raise ValueError(f"outcome must be 'won' or 'lost', got {outcome!r}")
        at_us = _instant_us(event.get("decided_at"))
        d = state["disputes"].setdefault(
            did, {"amount": None, "opened": False, "decision": None}
        )
        # The decision with the latest instant is in force. Equal instants are the same fact.
        cur = d["decision"]
        if cur is None or at_us > cur["at_us"]:
            d["decision"] = {"at_us": at_us, "outcome": outcome}

    else:
        raise ValueError(f"unknown event type: {kind!r}")

    state["events"][eid] = True

    # Post the change from the last applied position to the new target.
    target = _target(state)
    applied = state["applied"]
    moves = []
    for account in _ACCOUNTS:
        delta = target[account] - applied.get(account, 0)
        if delta:
            moves.append((account, delta))
    if moves:
        contra = -sum(delta for _, delta in moves)
        if contra:
            moves.append((_CONTRA, contra))
    for account, amount in moves:
        state["journal"].append({
            "line_id": f"jl-{len(state['journal']) + 1}",
            "event_id": eid,
            "account": account,
            "amount_minor": amount,
        })
    state["applied"] = dict(target)


def balances(state: dict) -> dict:
    """Current position. Derived from the facts, so it matches the journal after every event."""
    return _target(state)


def journal(state: dict) -> list[dict]:
    """Copy of the append-only journal, in posting order."""
    return [dict(line) for line in state.get("journal", [])]
```
