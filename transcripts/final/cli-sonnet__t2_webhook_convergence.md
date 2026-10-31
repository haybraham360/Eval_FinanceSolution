# cli-sonnet / t2_webhook_convergence / trial 1

- Requested: `sonnet`, resolved: `claude-haiku-5-5,claude-sonnet-5-5`, provider: claude-cli
- Run at 2026-10-31T20:35:29+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t2_webhook_convergence/prompt.md`.

## Model output

```python
"""Payment projection from PSP webhooks (single payment, integer minor units).

Design
------
* The state stores the set of distinct business *facts* (captures, succeeded
  refunds, failed refunds, the dispute, the latest decision per dispute).
  Every fact is keyed by its business id, so repeats and re-issued deliveries
  under new event_ids are naturally idempotent.
* The position is a pure function of those facts, so it cannot depend on
  arrival order or repeats.
* The journal is append-only. After each delivery we compute the target
  position, diff it against what has already been posted, and append
  correction lines for the difference, balanced by a psp_clearing line.
* The state contains only dicts, lists, strings and ints, so it round-trips
  through JSON exactly.
"""

import re
from datetime import datetime, timedelta

DISPUTE_FEE = 1500

POSITION_ACCOUNTS = (
    "available",
    "reserved",
    "chargeback_loss",
    "dispute_fee",
    "unapplied_refund",
)

_EPOCH = datetime(1970, 1, 1)

_TS_RE = re.compile(
    r"^\s*(\d{4})-(\d{2})-(\d{2})[Tt ](\d{2}):(\d{2})"
    r"(?::(\d{2})(?:[.,](\d+))?)?"
    r"\s*(Z|z|[+-]\d{2}(?::?\d{2})?)\s*$"
)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _parse_instant(value):
    """Parse ISO-8601 with UTC offset into an exactly comparable key.

    Returns [epoch_seconds (int), fraction_digits (str, trailing zeros
    stripped)]. Comparing as (seconds, fraction string) is numerically
    correct because the fraction is a digit string after the decimal point.
    """
    if not isinstance(value, str):
        raise ValueError("decided_at must be an ISO-8601 string")
    m = _TS_RE.match(value)
    if not m:
        raise ValueError("invalid decided_at: %r" % (value,))
    year, month, day, hour, minute, sec, frac, tz = m.groups()
    sec = int(sec) if sec is not None else 0
    try:
        naive = datetime(int(year), int(month), int(day), int(hour), int(minute), sec)
    except ValueError as exc:
        raise ValueError("invalid decided_at: %r" % (value,)) from exc

    if tz in ("Z", "z"):
        offset = timedelta(0)
    else:
        sign = -1 if tz[0] == "-" else 1
        digits = tz[1:].replace(":", "")
        oh = int(digits[:2])
        om = int(digits[2:4]) if len(digits) >= 4 else 0
        if oh > 23 or om > 59:
            raise ValueError("invalid UTC offset in decided_at: %r" % (value,))
        offset = sign * timedelta(hours=oh, minutes=om)

    utc = naive - offset
    delta = utc - _EPOCH
    secs = delta.days * 86400 + delta.seconds
    return [secs, (frac or "").rstrip("0")]


def _require_str(event, key):
    v = event.get(key)
    if not isinstance(v, str) or v == "":
        raise ValueError("%s must be a non-empty string" % key)
    return v


def _require_amount(event, key="amount_minor"):
    v = event.get(key)
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise ValueError("%s must be a non-negative integer" % key)
    return v


def _init(state):
    state.setdefault("seen", {})            # event_id -> True
    state.setdefault("captures", {})        # capture_id -> amount
    state.setdefault("refunds", {})         # refund_id -> amount (reported succeeded)
    state.setdefault("failed_refunds", {})  # refund_id -> True (terminal)
    state.setdefault("dispute", None)       # {"dispute_id", "amount_minor"}
    state.setdefault("decisions", {})       # dispute_id -> latest decision
    state.setdefault("journal", [])         # append-only lines
    state.setdefault("posted", {a: 0 for a in POSITION_ACCOUNTS})
    state.setdefault("seq", 0)


def _position(state):
    captures = state.get("captures", {})
    refunds = state.get("refunds", {})
    failed = state.get("failed_refunds", {})

    captured = sum(captures.values())
    refunded = sum(a for rid, a in refunds.items() if rid not in failed)

    applied = min(refunded, captured)
    unapplied = refunded - applied
    remaining = captured - applied

    pos = {a: 0 for a in POSITION_ACCOUNTS}
    pos["available"] = remaining
    pos["unapplied_refund"] = unapplied

    disp = state.get("dispute")
    if disp is not None:
        d = min(disp["amount_minor"], remaining)
        dec = state.get("decisions", {}).get(disp["dispute_id"])
        pos["dispute_fee"] = DISPUTE_FEE
        if dec is None:
            pos["reserved"] = d
            pos["available"] = remaining - d
        elif dec["outcome"] == "lost":
            pos["chargeback_loss"] = d
            pos["available"] = remaining - d
        else:  # won
            pos["dispute_fee"] = 0
    return pos


def _post(state, event_id):
    """Append correction lines so the journal matches the current position."""
    target = _position(state)
    posted = state["posted"]
    journal = state["journal"]

    total = 0
    new_lines = []
    for acct in POSITION_ACCOUNTS:
        delta = target[acct] - posted.get(acct, 0)
        if delta != 0:
            new_lines.append((acct, delta))
            total += delta
    if total != 0:
        new_lines.append(("psp_clearing", -total))

    for acct, amount in new_lines:
        state["seq"] += 1
        journal.append({
            "line_id": "L%d" % state["seq"],
            "event_id": event_id,
            "account": acct,
            "amount_minor": amount,
        })
    for acct in POSITION_ACCOUNTS:
        posted[acct] = target[acct]


# --------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------

def apply_event(state: dict, event: dict) -> None:
    event_id = _require_str(event, "event_id")
    etype = event.get("type")

    # Validate fully before mutating anything.
    if etype == "capture.succeeded":
        cid = _require_str(event, "capture_id")
        amount = _require_amount(event)
    elif etype == "refund.succeeded":
        rid = _require_str(event, "refund_id")
        amount = _require_amount(event)
    elif etype == "refund.failed":
        rid = _require_str(event, "refund_id")
    elif etype == "dispute.opened":
        did = _require_str(event, "dispute_id")
        amount = _require_amount(event)
    elif etype == "dispute.decided":
        did = _require_str(event, "dispute_id")
        outcome = event.get("outcome")
        if outcome not in ("won", "lost"):
            raise ValueError("outcome must be 'won' or 'lost'")
        instant = _parse_instant(event.get("decided_at"))
    else:
        return  # unknown event types carry no financial meaning

    _init(state)

    if event_id in state["seen"]:
        return  # exact redelivery
    state["seen"][event_id] = True

    if etype == "capture.succeeded":
        state["captures"].setdefault(cid, amount)
    elif etype == "refund.succeeded":
        state["refunds"].setdefault(rid, amount)
    elif etype == "refund.failed":
        state["failed_refunds"][rid] = True
    elif etype == "dispute.opened":
        if state["dispute"] is None:
            state["dispute"] = {"dispute_id": did, "amount_minor": amount}
    else:  # dispute.decided
        current = state["decisions"].get(did)
        if current is None or instant > current["at"]:
            state["decisions"][did] = {"at": instant, "outcome": outcome}

    _post(state, event_id)


def balances(state: dict) -> dict:
    return dict(_position(state))


def journal(state: dict) -> list:
    return [dict(line) for line in state.get("journal", [])]
```
