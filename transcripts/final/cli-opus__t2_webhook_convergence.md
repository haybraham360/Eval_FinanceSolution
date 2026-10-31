# cli-opus / t2_webhook_convergence / trial 1

- Requested: `opus`, resolved: `claude-haiku-5-5,claude-opus-5-5`, provider: claude-cli
- Run at 2026-10-31T15:25:44+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t2_webhook_convergence/prompt.md`.

## Model output

```python
"""Payment projection built from at-least-once, unordered PSP webhooks.

State stores only the distinct facts received and the append-only journal.
The position is always recalculated from those facts, so it cannot depend on
arrival order or repeats. Each delivery posts the difference between the
position before and after it, so the journal always matches the position.

Assumption: the ticket does not define contradictory input, and first-write-wins
would make the position order-dependent. Malformed events, unknown event types,
a fact id re-issued with a different amount, a second dispute id, and two
different outcomes at one instant therefore raise ValueError. The state is left
unchanged, so the worker should quarantine the event for investigation.
"""

from __future__ import annotations

import re
from datetime import datetime
from fractions import Fraction

POSITION_ACCOUNTS = (
    "available",
    "reserved",
    "chargeback_loss",
    "dispute_fee",
    "unapplied_refund",
)
CLEARING_ACCOUNT = "psp_clearing"
DISPUTE_FEE_MINOR = 1500
DISPUTE_OUTCOMES = ("won", "lost")

# Parsed by hand because datetime.fromisoformat on Python 3.10 rejects "Z",
# "+0000" and fractions that do not have exactly 3 or 6 digits.
_TIMESTAMP = re.compile(
    r"(\d{4})-?(\d{2})-?(\d{2})[Tt ]"
    r"(\d{2}):?(\d{2})(?::?(\d{2})(?:[.,](\d+))?)?"
    r"(?:[Zz]|([+-])(\d{2})(?::?(\d{2}))?)",
    re.ASCII,
)


def apply_event(state: dict, event: dict) -> None:
    """Apply one delivery to state. Repeated deliveries are ignored."""
    event_id = _text(event, "event_id")
    if event_id in state.get("seen_event_ids", {}):
        return

    event_type = _text(event, "type")
    handler = _HANDLERS.get(event_type)
    if handler is None:
        raise ValueError(f"unknown event type: {event_type!r}")

    # Handlers validate fully before changing anything, and a new state is only
    # published on success, so a rejected event leaves the caller's state as is.
    draft = state if state else _empty_state()
    before = _position(draft)
    handler(draft, event)
    draft["seen_event_ids"][event_id] = True
    _post_changes(draft, event_id, before)
    if not state:
        state.update(draft)


def balances(state: dict) -> dict:
    """Return the merchant's position for every event applied so far."""
    return _position(state)


def journal(state: dict) -> list[dict]:
    """Return copies of the lines, so callers cannot alter the ledger."""
    return [dict(line) for line in state.get("journal", [])]


def _empty_state() -> dict:
    return {
        "seen_event_ids": {},
        "captures": {},
        "refunds": {},
        "failed_refunds": {},
        "dispute": {"id": None, "amount_minor": None, "decision": None},
        "journal": [],
    }


def _position(state: dict) -> dict:
    position = {account: 0 for account in POSITION_ACCOUNTS}
    if not state:
        return position

    captured = sum(state["captures"].values())
    refunded = sum(
        amount
        for refund_id, amount in state["refunds"].items()
        if refund_id not in state["failed_refunds"]
    )
    refund_applied = min(captured, refunded)
    merchant_money = captured - refund_applied

    position["available"] = merchant_money
    position["unapplied_refund"] = refunded - refund_applied

    dispute = state["dispute"]
    if dispute["amount_minor"] is None:
        return position  # A decision has no effect until the dispute is opened.

    decision = dispute["decision"]
    outcome = decision["outcome"] if decision is not None else None
    if outcome == "won":
        return position

    disputed = min(dispute["amount_minor"], merchant_money)
    position["available"] -= disputed
    position["dispute_fee"] = DISPUTE_FEE_MINOR
    if outcome == "lost":
        position["chargeback_loss"] = disputed
    else:
        position["reserved"] = disputed
    return position


def _post_changes(state: dict, event_id: str, before: dict) -> None:
    after = _position(state)
    changes = [
        (account, after[account] - before[account])
        for account in POSITION_ACCOUNTS
    ]
    contra = -sum(amount for _, amount in changes)
    changes.append((CLEARING_ACCOUNT, contra))

    lines = state["journal"]
    for account, amount in changes:
        if amount != 0:
            lines.append(
                {
                    "line_id": f"line-{len(lines) + 1}",
                    "event_id": event_id,
                    "account": account,
                    "amount_minor": amount,
                }
            )


def _on_capture_succeeded(state: dict, event: dict) -> None:
    capture_id = _text(event, "capture_id")
    _record_amount(state["captures"], capture_id, _amount(event))


def _on_refund_succeeded(state: dict, event: dict) -> None:
    refund_id = _text(event, "refund_id")
    _record_amount(state["refunds"], refund_id, _amount(event))


def _on_refund_failed(state: dict, event: dict) -> None:
    refund_id = _text(event, "refund_id")
    state["failed_refunds"][refund_id] = True


def _on_dispute_opened(state: dict, event: dict) -> None:
    dispute_id = _text(event, "dispute_id")
    amount = _amount(event)
    dispute = state["dispute"]
    _check_dispute_id(dispute, dispute_id)
    if dispute["amount_minor"] not in (None, amount):
        raise ValueError(f"conflicting amount for dispute {dispute_id!r}")
    dispute["id"] = dispute_id
    dispute["amount_minor"] = amount


def _on_dispute_decided(state: dict, event: dict) -> None:
    dispute_id = _text(event, "dispute_id")
    outcome = _text(event, "outcome")
    if outcome not in DISPUTE_OUTCOMES:
        raise ValueError(f"unknown dispute outcome: {outcome!r}")
    decided_at = _text(event, "decided_at")
    instant = _instant(decided_at)

    dispute = state["dispute"]
    _check_dispute_id(dispute, dispute_id)
    current = dispute["decision"]
    if current is not None:
        current_instant = _instant(current["decided_at"])
        if instant == current_instant and outcome != current["outcome"]:
            raise ValueError(f"conflicting decisions at {decided_at!r}")
        if instant <= current_instant:
            dispute["id"] = dispute_id
            return

    dispute["id"] = dispute_id
    dispute["decision"] = {"decided_at": decided_at, "outcome": outcome}


def _record_amount(facts: dict, fact_id: str, amount: int) -> None:
    if facts.setdefault(fact_id, amount) != amount:
        raise ValueError(f"conflicting amount for {fact_id!r}")


def _check_dispute_id(dispute: dict, dispute_id: str) -> None:
    if dispute["id"] not in (None, dispute_id):
        raise ValueError(
            f"payment already has dispute {dispute['id']!r}, got {dispute_id!r}"
        )


def _text(event: dict, field: str) -> str:
    value = event.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _amount(event: dict) -> int:
    value = event.get("amount_minor")
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("amount_minor must be a non-negative integer")
    return value


def _instant(text: str) -> Fraction:
    """Return exact seconds on a fixed UTC timeline, at any fractional precision."""
    match = _TIMESTAMP.fullmatch(text)
    if match is None:
        raise ValueError(f"decided_at must be ISO-8601 with an offset: {text!r}")

    year, month, day, hour, minute, second, fraction, sign, off_h, off_m = (
        match.groups()
    )
    wall = datetime(
        int(year), int(month), int(day), int(hour), int(minute), int(second or 0)
    )
    seconds = (
        wall.toordinal() * 86400
        + wall.hour * 3600
        + wall.minute * 60
        + wall.second
    )

    if sign is not None:
        offset_hours = int(off_h)
        offset_minutes = int(off_m or 0)
        if offset_hours > 23 or offset_minutes > 59:
            raise ValueError(f"invalid UTC offset in decided_at: {text!r}")
        offset = offset_hours * 3600 + offset_minutes * 60
        seconds += -offset if sign == "+" else offset

    digits = fraction or ""
    return seconds + Fraction(int(digits or 0), 10 ** len(digits))


_HANDLERS = {
    "capture.succeeded": _on_capture_succeeded,
    "refund.succeeded": _on_refund_succeeded,
    "refund.failed": _on_refund_failed,
    "dispute.opened": _on_dispute_opened,
    "dispute.decided": _on_dispute_decided,
}
```
