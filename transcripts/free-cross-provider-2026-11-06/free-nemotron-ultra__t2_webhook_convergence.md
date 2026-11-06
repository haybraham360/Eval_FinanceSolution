# free-nemotron-ultra / t2_webhook_convergence / trial 1

- Requested: `nvidia/nemotron-3-ultra-550b-a55b:free`, resolved: `nvidia/nemotron-3-ultra-550b-a55b:free`, provider: Nvidia
- Run at 2026-11-06T20:00:46+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t2_webhook_convergence/prompt.md`.

## Model output

```python
from datetime import datetime
from typing import Dict, List, Any, Optional


def _parse_iso(s: str) -> datetime:
    """Parse ISO-8601 string with UTC offset to an aware datetime."""
    return datetime.fromisoformat(s)


def _ensure_state(state: Dict[str, Any]) -> None:
    """Initialize missing keys in the state dict."""
    if 'processed_event_ids' not in state:
        state['processed_event_ids'] = {}
    if 'captures' not in state:
        state['captures'] = {}
    if 'refunds' not in state:
        state['refunds'] = {}
    if 'dispute' not in state:
        state['dispute'] = {
            'opened': False,
            'amount': 0,
            'dispute_id': None,
            'latest_decision': None
        }
    else:
        d = state['dispute']
        d.setdefault('opened', False)
        d.setdefault('amount', 0)
        d.setdefault('dispute_id', None)
        d.setdefault('latest_decision', None)
    if 'journal' not in state:
        state['journal'] = []
    if 'next_line_id' not in state:
        state['next_line_id'] = 1


def _compute_balances(state: Dict[str, Any]) -> Dict[str, int]:
    """Calculate the five position balances from the current facts."""
    captures = state.get('captures', {})
    refunds = state.get('refunds', {})
    dispute = state.get('dispute', {'opened': False, 'amount': 0, 'latest_decision': None})

    total_captured = sum(captures.values())
    total_refunded = 0
    for r in refunds.values():
        if not r['failed'] and r['amount'] is not None:
            total_refunded += r['amount']

    net = total_captured - total_refunded
    if net < 0:
        net = 0
    unapplied_refund = total_refunded - total_captured
    if unapplied_refund < 0:
        unapplied_refund = 0

    if not dispute['opened']:
        return {
            'available': net,
            'reserved': 0,
            'chargeback_loss': 0,
            'dispute_fee': 0,
            'unapplied_refund': unapplied_refund
        }

    disputed = min(dispute['amount'], net)
    latest_decision = dispute.get('latest_decision')

    if latest_decision and latest_decision['outcome'] == 'won':
        return {
            'available': net,
            'reserved': 0,
            'chargeback_loss': 0,
            'dispute_fee': 0,
            'unapplied_refund': unapplied_refund
        }
    elif latest_decision and latest_decision['outcome'] == 'lost':
        return {
            'available': net - disputed,
            'reserved': 0,
            'chargeback_loss': disputed,
            'dispute_fee': 1500,
            'unapplied_refund': unapplied_refund
        }
    else:  # undecided
        return {
            'available': net - disputed,
            'reserved': disputed,
            'chargeback_loss': 0,
            'dispute_fee': 1500,
            'unapplied_refund': unapplied_refund
        }


def apply_event(state: Dict[str, Any], event: Dict[str, Any]) -> None:
    """
    Mutate state by applying a single webhook event.
    Idempotent on event_id and on business facts (capture_id, refund_id, dispute_id).
    """
    _ensure_state(state)

    event_id = event['event_id']
    if event_id in state['processed_event_ids']:
        return  # duplicate delivery
    state['processed_event_ids'][event_id] = True

    event_type = event['type']
    old_balances = _compute_balances(state)
    changed = False

    if event_type == 'capture.succeeded':
        capture_id = event['capture_id']
        amount = event['amount_minor']
        if capture_id not in state['captures']:
            state['captures'][capture_id] = amount
            changed = True

    elif event_type == 'refund.succeeded':
        refund_id = event['refund_id']
        amount = event['amount_minor']
        refund = state['refunds'].get(refund_id)
        if refund is None:
            state['refunds'][refund_id] = {'amount': amount, 'failed': False}
            changed = True
        elif not refund['failed']:
            # already recorded as succeeded – duplicate fact
            pass
        # if failed, terminal – ignore

    elif event_type == 'refund.failed':
        refund_id = event['refund_id']
        refund = state['refunds'].get(refund_id)
        if refund is None:
            state['refunds'][refund_id] = {'amount': None, 'failed': True}
            changed = True
        elif not refund['failed']:
            refund['failed'] = True
            changed = True
        # else already failed – duplicate fact

    elif event_type == 'dispute.opened':
        dispute_id = event['dispute_id']
        amount = event['amount_minor']
        dispute = state['dispute']
        if not dispute['opened']:
            dispute['opened'] = True
            dispute['amount'] = amount
            dispute['dispute_id'] = dispute_id
            changed = True
        # else already opened – duplicate fact

    elif event_type == 'dispute.decided':
        dispute_id = event['dispute_id']
        outcome = event['outcome']
        decided_at = event['decided_at']
        dispute = state['dispute']
        current = dispute['latest_decision']
        new_dt = _parse_iso(decided_at)
        if current is None:
            dispute['latest_decision'] = {'decided_at': decided_at, 'outcome': outcome}
            changed = True
        else:
            current_dt = _parse_iso(current['decided_at'])
            if new_dt > current_dt:
                dispute['latest_decision'] = {'decided_at': decided_at, 'outcome': outcome}
                changed = True
        # older decisions are ignored

    # If the event didn't change any facts, balances remain the same → no journal lines.
    if not changed:
        return

    new_balances = _compute_balances(state)

    # Compute deltas for the five position accounts
    deltas = {}
    for key in ('available', 'reserved', 'chargeback_loss', 'dispute_fee', 'unapplied_refund'):
        old = old_balances[key]
        new = new_balances[key]
        if old != new:
            deltas[key] = new - old

    if not deltas:
        return  # no financial effect

    lines = []
    for account, amount in deltas.items():
        line_id = str(state['next_line_id'])
        state['next_line_id'] += 1
        lines.append({
            'line_id': line_id,
            'event_id': event_id,
            'account': account,
            'amount_minor': amount
        })

    total_delta = sum(deltas.values())
    if total_delta != 0:
        line_id = str(state['next_line_id'])
        state['next_line_id'] += 1
        lines.append({
            'line_id': line_id,
            'event_id': event_id,
            'account': 'psp_clearing',
            'amount_minor': -total_delta
        })

    state['journal'].extend(lines)


def balances(state: Dict[str, Any]) -> Dict[str, int]:
    """Return the current position balances."""
    return _compute_balances(state)


def journal(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return the immutable accounting journal."""
    return state.get('journal', [])
```
