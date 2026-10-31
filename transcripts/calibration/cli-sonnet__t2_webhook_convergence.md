# cli-sonnet / t2_webhook_convergence / trial 1

- Requested: `sonnet`, resolved: `claude-haiku-5-5,claude-sonnet-5-5`, provider: claude-cli
- Run at 2026-10-31T14:42:25+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t2_webhook_convergence/prompt.md`.

## Model output

```python
"""Payment projection from PSP webhooks (single payment, integer minor units).

Design:
  * `state` stores only de-duplicated business facts (keyed by capture_id,
    refund_id, dispute_id and decision instant), plus the append-only journal
    and the running per-account totals already posted to it.
  * After each event the target position is recomputed from the facts alone,
    so it cannot depend on arrival order or repeats. The difference between
    the target and what is already posted is appended as correction lines,
    balanced by a `psp_clearing` contra line.
  * Everything in `state` is JSON-native (str keys, ints, lists, dicts).
"""

import re
from datetime import datetime, timedelta

ACCOUNTS = ("available", "reserved", "chargeback_loss", "dispute_fee", "unapplied_refund")
DISPUTE_FEE = 1500

_TS_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})[Tt ](\d{2}):(\d{2})"
    r"(?::(\d{2})(?:[.,](\d+))?)?"
    r"(Z|z|[+-]\d{2}(?::?\d{2})?)$"
)
_EPOCH = datetime(1970, 1, 1)


def _instant_ns(text):
    """ISO-8601 timestamp with UTC offset -> exact integer nanoseconds since epoch (UTC)."""
    if not isinstance(text, str):
        raise ValueError("decided_at must be a string")
    m = _TS_RE.match(text.strip())
    if not m:
        raise ValueError("invalid decided_at: %r" % (text,))
    y, mo, d, hh, mi, ss, frac, off = m.groups()
    naive = datetime(int(y), int(mo), int(d), int(hh), int(mi), int(ss or 0))
    delta = naive - _EPOCH
    seconds = delta.days * 86400 + delta.seconds
    if off in ("Z", "z"):
        off_s = 0
    else:
        sign = -1 if off[0] == "-" else 1
        digits = off[1:].replace(":", "")
        oh = int(digits[:2])
        om = int(digits[2:4]) if len(digits) >= 4 else 0
        off_s = sign * (oh * 3600 + om * 60)
    ns = int(((frac or "") + "000000000")[:9])
    return (seconds - off_s) * 1_000_000_000 + ns


def _init(state):
    state.setdefault("captures", {})
    state.setdefault("refunds", {})
    state.setdefault("failed_refunds", {})
    state.setdefault("dispute", None)
    state.setdefault("decisions", {})
    state.setdefault("journal", [])
    state.setdefault("posted", {a: 0 for a in ACCOUNTS})
    for a in ACCOUNTS:
        state["posted"].setdefault(a, 0)


def _is_amount(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def _target(state):
    captured = sum(state.get("captures", {}).values())
    failed = state.get("failed_refunds", {})
    refunds = sum(a for rid, a in state.get("refunds", {}).items() if rid not in failed)
    applied = min(refunds, captured)
    unapplied = refunds - applied
    money = captured - applied  # money still with the merchant after refunds

    res = {a: 0 for a in ACCOUNTS}
    res["unapplied_refund"] = unapplied
    res["available"] = money

    dispute = state.get("dispute")
    if dispute:
        disputed = min(dispute["amount"], money)
        decisions = state.get("decisions", {}).get(dispute["id"], {})
        outcome = None
        if decisions:
            outcome = decisions[max(decisions, key=int)]
        res["dispute_fee"] = DISPUTE_FEE
        if outcome == "won":
            res["dispute_fee"] = 0
        elif outcome == "lost":
            res["available"] = money - disputed
            res["chargeback_loss"] = disputed
        else:
            res["available"] = money - disputed
            res["reserved"] = disputed
    return res


def apply_event(state: dict, event: dict) -> None:
    # Validate / parse first so a bad event leaves the state untouched.
    etype = event.get("type")
    event_id = event.get("event_id")
    _init(state)

    if etype == "capture.succeeded":
        if not _is_amount(event.get("amount_minor")):
            return
        state["captures"].setdefault(str(event["capture_id"]), event["amount_minor"])
    elif etype == "refund.succeeded":
        if not _is_amount(event.get("amount_minor")):
            return
        state["refunds"].setdefault(str(event["refund_id"]), event["amount_minor"])
    elif etype == "refund.failed":
        state["failed_refunds"][str(event["refund_id"])] = True
    elif etype == "dispute.opened":
        if not _is_amount(event.get("amount_minor")):
            return
        if state["dispute"] is None:
            state["dispute"] = {"id": str(event["dispute_id"]), "amount": event["amount_minor"]}
    elif etype == "dispute.decided":
        outcome = event.get("outcome")
        if outcome not in ("won", "lost"):
            return
        ns = _instant_ns(event.get("decided_at"))
        state["decisions"].setdefault(str(event["dispute_id"]), {}).setdefault(str(ns), outcome)
    else:
        return

    target = _target(state)
    posted = state["posted"]
    journal = state["journal"]
    total = 0
    new_lines = []
    for acct in ACCOUNTS:
        delta = target[acct] - posted[acct]
        if delta:
            new_lines.append((acct, delta))
            total += delta
    if total:
        new_lines.append(("psp_clearing", -total))
    for acct, amt in new_lines:
        journal.append({
            "line_id": "L%d" % (len(journal) + 1),
            "event_id": event_id,
            "account": acct,
            "amount_minor": amt,
        })
        if acct != "psp_clearing":
            posted[acct] += amt


def balances(state: dict) -> dict:
    return _target(state)


def journal(state: dict) -> list:
    return [dict(line) for line in state.get("journal", [])]
```
