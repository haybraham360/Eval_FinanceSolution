# cli-opus / t2_webhook_convergence / trial 1

- Requested: `opus`, resolved: `claude-haiku-5-5,claude-opus-5-5`, provider: claude-cli
- Run at 2026-10-31T14:39:47+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t2_webhook_convergence/prompt.md`.

## Model output

```python
"""Projection of one payment's merchant position from PSP webhooks.

Design
------
* ``state`` holds the distinct business facts received, keyed by business
  id: captures, refunds, failed refunds, the dispute, and dispute decisions.
* The position is a pure function of that fact set. Arrival order and
  repeats therefore cannot change the result.
* The journal is append-only. After each delivery we compute the new
  position and diff it against the last posted position. Each nonzero
  difference becomes a line, and one balancing ``psp_clearing`` line makes
  the delivery sum to zero. Corrections, such as a refund later failing or a
  dispute decision being overturned, are posted as further lines.
* All state is plain JSON: string keys, ints, strings, ``None``, dicts and
  lists. It round-trips exactly through ``json.dumps``/``json.loads``.
* A malformed event, or a re-issued fact that contradicts the fact already
  recorded (for example the same ``capture_id`` with a different amount),
  raises ``EventError`` before any part of ``state`` is changed. Contradictory
  money facts are surfaced rather than silently resolved.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

__all__ = ["apply_event", "balances", "journal", "EventError", "DISPUTE_FEE_MINOR"]

DISPUTE_FEE_MINOR = 1500
POSITION_ACCOUNTS = (
    "available",
    "reserved",
    "chargeback_loss",
    "dispute_fee",
    "unapplied_refund",
)
CONTRA_ACCOUNT = "psp_clearing"

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_TS_RE = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})[Tt ](\d{2}):(\d{2}):(\d{2})"
    r"(?:[.,](\d+))?"
    r"(?:([Zz])|([+-])(\d{2}):?(\d{2}))"
)


class EventError(ValueError):
    """The event is malformed or contradicts facts already recorded."""


# --------------------------------------------------------------------------- #
# Validation / parsing
# --------------------------------------------------------------------------- #

def _req_str(event: dict, key: str) -> str:
    value = event.get(key)
    if not isinstance(value, str) or not value:
        raise EventError(f"{key!r} must be a non-empty string")
    return value


def _req_amount(event: dict, key: str = "amount_minor") -> int:
    value = event.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise EventError(f"{key!r} must be an integer (minor units)")
    if value < 0:
        raise EventError(f"{key!r} must not be negative")
    return value


def _instant_ns(text: str) -> int:
    """Parse ISO-8601 with an explicit UTC offset and return epoch nanoseconds.

    The result is an exact integer, so instants compare exactly regardless
    of the offset used in each delivery.
    """
    if not isinstance(text, str):
        raise EventError("'decided_at' must be a string")
    m = _TS_RE.fullmatch(text.strip())
    if not m:
        raise EventError(f"'decided_at' is not ISO-8601 with a UTC offset: {text!r}")
    year, month, day, hour, minute, second = (int(m.group(i)) for i in range(1, 7))
    frac = m.group(7) or ""
    if len(frac) > 9:
        if frac[9:].strip("0"):
            raise EventError("'decided_at' precision finer than nanoseconds")
        frac = frac[:9]
    frac_ns = int(frac.ljust(9, "0")) if frac else 0

    if m.group(8):
        offset = timedelta(0)
    else:
        off_h, off_m = int(m.group(10)), int(m.group(11))
        if off_h > 23 or off_m > 59:
            raise EventError(f"invalid UTC offset in 'decided_at': {text!r}")
        offset = timedelta(hours=off_h, minutes=off_m)
        if m.group(9) == "-":
            offset = -offset
    try:
        dt = datetime(year, month, day, hour, minute, second, tzinfo=timezone(offset))
    except ValueError as exc:
        raise EventError(f"invalid 'decided_at': {text!r}") from exc
    seconds = (dt - _EPOCH) // timedelta(seconds=1)  # exact: dt has no sub-seconds
    return seconds * 1_000_000_000 + frac_ns


def _parse(event: dict) -> dict:
    if not isinstance(event, dict):
        raise EventError("event must be a dict")
    parsed = {"event_id": _req_str(event, "event_id"), "type": _req_str(event, "type")}
    etype = parsed["type"]
    if etype == "capture.succeeded":
        parsed["capture_id"] = _req_str(event, "capture_id")
        parsed["amount"] = _req_amount(event)
    elif etype == "refund.succeeded":
        parsed["refund_id"] = _req_str(event, "refund_id")
        parsed["amount"] = _req_amount(event)
    elif etype == "refund.failed":
        parsed["refund_id"] = _req_str(event, "refund_id")
    elif etype == "dispute.opened":
        parsed["dispute_id"] = _req_str(event, "dispute_id")
        parsed["amount"] = _req_amount(event)
    elif etype == "dispute.decided":
        parsed["dispute_id"] = _req_str(event, "dispute_id")
        outcome = event.get("outcome")
        if outcome not in ("won", "lost"):
            raise EventError("'outcome' must be 'won' or 'lost'")
        parsed["outcome"] = outcome
        parsed["instant"] = str(_instant_ns(event.get("decided_at")))
    else:
        raise EventError(f"unknown event type: {etype!r}")
    return parsed


# --------------------------------------------------------------------------- #
# State handling
# --------------------------------------------------------------------------- #

def _ensure_initialised(state: dict) -> None:
    state.setdefault("seen_event_ids", {})   # event_id -> True
    state.setdefault("captures", {})         # capture_id -> amount
    state.setdefault("refunds", {})          # refund_id -> amount (succeeded)
    state.setdefault("failed_refunds", {})   # refund_id -> True (terminal)
    state.setdefault("dispute", None)        # {"dispute_id", "amount"} or None
    state.setdefault("decisions", {})        # dispute_id -> {instant_ns_str: outcome}
    state.setdefault("posted", {a: 0 for a in POSITION_ACCOUNTS})
    state.setdefault("journal", [])
    state.setdefault("next_line_seq", 1)


def _check_conflicts(state: dict, ev: dict) -> None:
    """Reject a re-issued fact whose content contradicts the recorded fact."""
    etype = ev["type"]
    if etype == "capture.succeeded":
        known = state["captures"].get(ev["capture_id"])
        if known is not None and known != ev["amount"]:
            raise EventError(
                f"capture {ev['capture_id']!r} re-issued with a different amount "
                f"({ev['amount']} vs recorded {known})"
            )
    elif etype == "refund.succeeded":
        known = state["refunds"].get(ev["refund_id"])
        if known is not None and known != ev["amount"]:
            raise EventError(
                f"refund {ev['refund_id']!r} re-issued with a different amount "
                f"({ev['amount']} vs recorded {known})"
            )
    elif etype == "dispute.opened":
        dispute = state["dispute"]
        if dispute is not None:
            if dispute["dispute_id"] != ev["dispute_id"]:
                raise EventError("payment already has a different dispute")
            if dispute["amount"] != ev["amount"]:
                raise EventError(
                    f"dispute {ev['dispute_id']!r} re-issued with a different amount"
                )
        other = [d for d in state["decisions"] if d != ev["dispute_id"]]
        if other:
            raise EventError(f"decisions already received for other dispute(s): {other}")
    elif etype == "dispute.decided":
        dispute = state["dispute"]
        if dispute is not None and dispute["dispute_id"] != ev["dispute_id"]:
            raise EventError("decision references a dispute other than the open one")
        known = state["decisions"].get(ev["dispute_id"], {}).get(ev["instant"])
        if known is not None and known != ev["outcome"]:
            raise EventError("two different decisions share the same instant")


def _record_fact(state: dict, ev: dict) -> None:
    etype = ev["type"]
    if etype == "capture.succeeded":
        state["captures"].setdefault(ev["capture_id"], ev["amount"])
    elif etype == "refund.succeeded":
        state["refunds"].setdefault(ev["refund_id"], ev["amount"])
    elif etype == "refund.failed":
        state["failed_refunds"][ev["refund_id"]] = True
    elif etype == "dispute.opened":
        if state["dispute"] is None:
            state["dispute"] = {"dispute_id": ev["dispute_id"], "amount": ev["amount"]}
    elif etype == "dispute.decided":
        state["decisions"].setdefault(ev["dispute_id"], {}).setdefault(
            ev["instant"], ev["outcome"]
        )


def _compute(state: dict) -> dict:
    """Position as a pure function of the recorded fact set."""
    captured = sum(state.get("captures", {}).values())
    failed = state.get("failed_refunds", {})
    refunded = sum(
        amount for rid, amount in state.get("refunds", {}).items() if rid not in failed
    )
    applied_refund = min(refunded, captured)
    unapplied_refund = refunded - applied_refund
    with_merchant = captured - applied_refund

    available = with_merchant
    reserved = 0
    chargeback_loss = 0
    dispute_fee = 0

    dispute = state.get("dispute")
    if dispute is not None:
        disputed = min(dispute["amount"], with_merchant)
        decisions = state.get("decisions", {}).get(dispute["dispute_id"], {})
        outcome = decisions[max(decisions, key=int)] if decisions else None
        if outcome == "won":
            pass  # money back in available, no fee
        elif outcome == "lost":
            available -= disputed
            chargeback_loss = disputed
            dispute_fee = DISPUTE_FEE_MINOR
        else:  # open, undecided
            available -= disputed
            reserved = disputed
            dispute_fee = DISPUTE_FEE_MINOR

    return {
        "available": available,
        "reserved": reserved,
        "chargeback_loss": chargeback_loss,
        "dispute_fee": dispute_fee,
        "unapplied_refund": unapplied_refund,
    }


def _post(state: dict, event_id: str, new_position: dict) -> None:
    posted = state["posted"]
    lines = []
    for account in POSITION_ACCOUNTS:
        diff = new_position[account] - posted[account]
        if diff:
            lines.append((account, diff))
    total = sum(amount for _, amount in lines)
    if total:
        lines.append((CONTRA_ACCOUNT, -total))

    seq = state["next_line_seq"]
    for account, amount in lines:
        state["journal"].append(
            {
                "line_id": f"ln-{seq:012d}",
                "event_id": event_id,
                "account": account,
                "amount_minor": amount,
            }
        )
        seq += 1
    state["next_line_seq"] = seq
    state["posted"] = {a: new_position[a] for a in POSITION_ACCOUNTS}


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def apply_event(state: dict, event: dict) -> None:
    """Apply one webhook delivery to ``state`` in place.

    Repeat deliveries and re-issued facts have no effect. Malformed or
    contradictory events raise ``EventError`` and leave ``state`` untouched.
    """
    if not isinstance(state, dict):
        raise TypeError("state must be a dict")
    ev = _parse(event)
    _ensure_initialised(state)

    if ev["event_id"] in state["seen_event_ids"]:
        return  # same delivery again

    _check_conflicts(state, ev)  # raises before any mutation

    _record_fact(state, ev)
    state["seen_event_ids"][ev["event_id"]] = True
    _post(state, ev["event_id"], _compute(state))


def balances(state: dict) -> dict:
    """Current position: five integer keys in minor units."""
    return _compute(state)


def journal(state: dict) -> list[dict]:
    """Append-only accounting lines in posting order (defensive copies)."""
    return [dict(line) for line in state.get("journal", [])]
```
