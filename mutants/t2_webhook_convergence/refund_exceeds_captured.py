# expect-fail: unapplied_refund_reported_then_absorbed
"""Facts are the source of truth. The position is a pure function of them; the journal posts the diff."""
from datetime import datetime

POSITION = ("available", "reserved", "chargeback_loss", "dispute_fee", "unapplied_refund")


def _empty(state):
    if not state:
        state.update(captures={}, refunds={}, failed=[], dispute=None, decisions={}, seen=[], lines=[], posted={k: 0 for k in POSITION})


def _instant(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _target(state):
    captured = sum(state["captures"].values())
    wanted = sum(a for r, a in state["refunds"].items() if r not in state["failed"])
    refunded = wanted
    left = captured - refunded
    pos = dict(available=left, reserved=0, chargeback_loss=0, dispute_fee=0, unapplied_refund=wanted - refunded)
    if state["dispute"] is None:
        return pos
    disputed = min(state["dispute"], left)
    outcome = None
    if state["decisions"]:
        outcome = state["decisions"][max(state["decisions"], key=_instant)]
    if outcome == "won":
        return pos
    pos["available"] = left - disputed
    pos["dispute_fee"] = 1500
    if outcome == "lost":
        pos["chargeback_loss"] = disputed
    else:
        pos["reserved"] = disputed
    return pos


def apply_event(state, event):
    _empty(state)
    if event["event_id"] in state["seen"]:
        return
    state["seen"].append(event["event_id"])
    kind = event["type"]
    if kind == "capture.succeeded":
        state["captures"].setdefault(event["capture_id"], event["amount_minor"])
    elif kind == "refund.succeeded":
        state["refunds"].setdefault(event["refund_id"], event["amount_minor"])
    elif kind == "refund.failed":
        if event["refund_id"] not in state["failed"]:
            state["failed"].append(event["refund_id"])
    elif kind == "dispute.opened":
        if state["dispute"] is None:
            state["dispute"] = event["amount_minor"]
    elif kind == "dispute.decided":
        state["decisions"][event["decided_at"]] = event["outcome"]

    target = _target(state)
    total = 0
    for account in POSITION:
        delta = target[account] - state["posted"][account]
        if delta:
            state["lines"].append({"line_id": f"L{len(state['lines'])}", "event_id": event["event_id"], "account": account, "amount_minor": delta})
            state["posted"][account] = target[account]
            total += delta
    if total:
        state["lines"].append({"line_id": f"L{len(state['lines'])}", "event_id": event["event_id"], "account": "psp_clearing", "amount_minor": -total})


def balances(state):
    _empty(state)
    return dict(state["posted"])


def journal(state):
    _empty(state)
    return [dict(line) for line in state["lines"]]
