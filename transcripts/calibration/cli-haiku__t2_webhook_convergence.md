# cli-haiku / t2_webhook_convergence / trial 1

- Requested: `haiku`, resolved: `claude-haiku-5-5`, provider: claude-cli
- Run at 2026-10-31T14:44:38+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t2_webhook_convergence/prompt.md`.

## Model output

```python
"""Payment position projection built from PSP webhooks.

The state holds only the distinct business facts (captures, refunds, one
dispute, dispute decisions), the set of seen delivery ids, and the append-only
journal. Position balances are recomputed from the facts, so they do not depend
on arrival order or repeats. Each delivery appends only the postings needed to
bring the journal's per-account totals in line with the recomputed position.

Facts that conflict with earlier facts (same id with a different amount, a
second dispute on one payment, or a decision with the same instant and a
different outcome) raise ValueError. The state is left unchanged in that case.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone

DISPUTE_FEE = 1500
POSITION_ACCOUNTS = (
    "available",
    "reserved",
    "chargeback_loss",
    "dispute_fee",
    "unapplied_refund",
)
CONTRA_ACCOUNT = "psp_clearing"
_OUTCOMES = ("won", "lost")


def _require_str(event: dict, key: str) -> str:
    value = event.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"event field {key!r} must be a non-empty string")
    return value


def _require_amount(event: dict, key: str) -> int:
    value = event.get(key)
    if type(value) is not int or value <= 0:
        raise ValueError(f"event field {key!r} must be a positive int in minor units")
    return value


def _canonical_instant(text) -> str:
    """Normalise an ISO-8601 instant with UTC offset to a fixed-width UTC string."""
    if not isinstance(text, str) or not text:
        raise ValueError("decided_at must be an ISO-8601 string with UTC offset")
    if text[-1:] in ("Z", "z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"invalid decided_at {text!r}") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("decided_at must include a UTC offset")
    return dt.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _dispute_for(work: dict, dispute_id: str) -> dict:
    disp = work.get("dispute")
    if disp is None:
        disp = {"id": dispute_id, "amount": None, "opened": False, "decisions": {}}
        work["dispute"] = disp
    elif disp["id"] != dispute_id:
        raise ValueError("a payment can have at most one dispute")
    return disp


def _positions(state: dict) -> dict:
    captures = state.get("captures", {})
    refunds = state.get("refunds", {})
    dispute = state.get("dispute")

    captured = sum(captures.values())
    refunded = sum(
        rec["amount"]
        for rec in refunds.values()
        if rec["succeeded"] and not rec["failed"]
    )
    taken = min(refunded, captured)
    unapplied = refunded - taken
    with_merchant = captured - taken

    reserved = 0
    chargeback = 0
    fee = 0
    removed_from_available = 0
    if dispute is not None and dispute["opened"]:
        disputed = min(dispute["amount"], with_merchant)
        decisions = dispute["decisions"]
        if decisions:
            latest = max(decisions, key=datetime.fromisoformat)
            outcome = decisions[latest]
        else:
            outcome = None
        if outcome != "won":
            fee = DISPUTE_FEE
            removed_from_available = disputed
            if outcome == "lost":
                chargeback = disputed
            else:
                reserved = disputed

    return {
        "available": with_merchant - removed_from_available,
        "reserved": reserved,
        "chargeback_loss": chargeback,
        "dispute_fee": fee,
        "unapplied_refund": unapplied,
    }


def _posted(journal: list) -> dict:
    totals = {account: 0 for account in POSITION_ACCOUNTS}
    for line in journal:
        if line["account"] in totals:
            totals[line["account"]] += line["amount_minor"]
    return totals


def apply_event(state: dict, event: dict) -> None:
    if not isinstance(event, dict):
        raise TypeError("event must be a dict")
    event_id = _require_str(event, "event_id")
    etype = event.get("type")

    # Work on a copy so that a rejected event leaves state untouched.
    work = copy.deepcopy(state)
    work.setdefault("captures", {})
    work.setdefault("refunds", {})
    work.setdefault("dispute", None)
    work.setdefault("seen_events", [])
    work.setdefault("journal", [])

    if event_id in work["seen_events"]:
        return  # same delivery again: no effect

    if etype == "capture.succeeded":
        capture_id = _require_str(event, "capture_id")
        amount = _require_amount(event, "amount_minor")
        known = work["captures"].get(capture_id)
        if known is None:
            work["captures"][capture_id] = amount
        elif known != amount:
            raise ValueError(f"capture {capture_id!r} re-issued with a different amount")

    elif etype == "refund.succeeded":
        refund_id = _require_str(event, "refund_id")
        amount = _require_amount(event, "amount_minor")
        rec = work["refunds"].setdefault(
            refund_id, {"amount": None, "succeeded": False, "failed": False}
        )
        if rec["amount"] is not None and rec["amount"] != amount:
            raise ValueError(f"refund {refund_id!r} re-issued with a different amount")
        rec["amount"] = amount
        rec["succeeded"] = True

    elif etype == "refund.failed":
        refund_id = _require_str(event, "refund_id")
        rec = work["refunds"].setdefault(
            refund_id, {"amount": None, "succeeded": False, "failed": False}
        )
        rec["failed"] = True  # terminal: this refund never counts

    elif etype == "dispute.opened":
        dispute_id = _require_str(event, "dispute_id")
        amount = _require_amount(event, "amount_minor")
        disp = _dispute_for(work, dispute_id)
        if disp["amount"] is not None and disp["amount"] != amount:
            raise ValueError(f"dispute {dispute_id!r} re-opened with a different amount")
        disp["amount"] = amount
        disp["opened"] = True

    elif etype == "dispute.decided":
        dispute_id = _require_str(event, "dispute_id")
        outcome = event.get("outcome")
        if outcome not in _OUTCOMES:
            raise ValueError("dispute outcome must be 'won' or 'lost'")
        instant = _canonical_instant(event.get("decided_at"))
        disp = _dispute_for(work, dispute_id)
        known = disp["decisions"].get(instant)
        if known is not None and known != outcome:
            raise ValueError("two different decisions share the same instant")
        disp["decisions"][instant] = outcome

    else:
        raise ValueError(f"unknown event type {etype!r}")

    target = _positions(work)
    posted = _posted(work["journal"])

    new_lines = []
    total = 0
    for account in POSITION_ACCOUNTS:
        delta = target[account] - posted[account]
        if delta != 0:
            new_lines.append(
                {
                    "line_id": f"{event_id}:{account}",
                    "event_id": event_id,
                    "account": account,
                    "amount_minor": delta,
                }
            )
            total += delta

    if total != 0:
        new_lines.append(
            {
                "line_id": f"{event_id}:{CONTRA_ACCOUNT}",
                "event_id": event_id,
                "account": CONTRA_ACCOUNT,
                "amount_minor": -total,
            }
        )

    work["seen_events"].append(event_id)
    work["journal"].extend(new_lines)

    state.clear()
    state.update(work)


def balances(state: dict) -> dict:
    return _positions(state)


def journal(state: dict) -> list[dict]:
    return [dict(line) for line in state.get("journal", [])]
```
