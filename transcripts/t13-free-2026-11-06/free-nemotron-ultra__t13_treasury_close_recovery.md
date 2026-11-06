# free-nemotron-ultra / t13_treasury_close_recovery / trial 1

- Requested: `nvidia/nemotron-3-ultra-550b-a55b:free`, resolved: `nvidia/nemotron-3-ultra-550b-a55b:free`, provider: Nvidia
- Run at 2026-11-06T20:55:15+00:00 with params `{}`
- Score 0%, full pass: False, finish: length, error: no fenced code block in output

## Failed checks

None.

## Prompt

See `tasks/t13_treasury_close_recovery/prompt.md`.

## Model output

The solution implements an event-sourced treasury ledger for the October 2026 close. The module processes records idempotently, maintains a JSON-serializable state, and derives all required views (balances, statuses, journal, period totals, reconciliation, exceptions). The final position after the sample log is computed by simulating the record flow: pay-ins P1, P2, P3 are credited; reversals X1, X2, X3, X4 are counted; payouts O1 (PAID), O2 (FAILED), O3 (UNKNOWN) are processed; settlement files correct fees and FX differences; period 2026-10 is closed, moving later journal lines to 2026-11-01. The open exceptions are: FX conflict on snapshot S-A, pending pay-in P4, reversal X4 exceeds its pay-in, negative balance for C1, unknown payout O3, and unmatched settlement line for P9.

```python
import json
from decimal import Decimal, ROUND_HALF_EVEN
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any, Optional, Tuple, Set

# ----- Helper functions -----

def _convert_usd_to_ngn(usd_minor: int, rate_str: str) -> int:
    rate = Decimal(rate_str)
    usd = Decimal(usd_minor)
    ngn = (usd * rate).quantize(Decimal('1'), rounding=ROUND_HALF_EVEN)
    return int(ngn)

def _to_lagos_date(iso_str: str) -> str:
    dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
    dt_lagos = dt + timedelta(hours=1)
    return dt_lagos.date().isoformat()

def _period_key(date_str: str) -> str:
    return date_str[:7]  # YYYY-MM

def _first_day_of_month(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}-01"

def _next_month_first_day(period: str) -> str:
    y, m = map(int, period.split('-'))
    if m == 12:
        return _first_day_of_month(y+1, 1)
    return _first_day_of_month(y, m+1)

def _posted_accounting_date(natural_date: str, state: dict) -> str:
    closed = state.get('latest_closed_period')
    if not closed:
        return natural_date
    nat_period = _period_key(natural_date)
    if nat_period <= closed:
        return _next_month_first_day(closed)
    return natural_date

def _new_line_id(state: dict) -> str:
    state['line_counter'] = state.get('line_counter', 0) + 1
    return f"J{state['line_counter']}"

def _post_journal_lines(state: dict, record_id: str, lines: List[Tuple[str, int, str]]) -> None:
    for account, amount, nat_date in lines:
        if amount == 0:
            continue
        adj_date = _posted_accounting_date(nat_date, state)
        state['journal_lines'].append({
            'line_id': _new_line_id(state),
            'record_id': record_id,
            'account': account,
            'amount_minor': amount,
            'accounting_date': adj_date
        })

def _get_fx_rate(state: dict, snapshot_id: str) -> Optional[str]:
    snap = state['fx_snapshots'].get(snapshot_id)
    return snap['rate'] if snap else None

def _recompute_payin_reversals(state: dict, payin_id: str, record_id: str) -> None:
    payin = state['payins'][payin_id]
    rev_ids = payin.get('reversal_ids', [])
    if not rev_ids:
        return
    currency = payin['currency']
    amount = payin['amount_minor']
    rate = _get_fx_rate(state, payin['fx_snapshot_id']) if currency == 'USD' else None
    remaining = amount
    cumulative = 0
    for rev_id in rev_ids:
        rev = state['reversals'][rev_id]
        counted = min(rev['amount_minor'], remaining)
        remaining -= counted
        rev['counted_minor'] = counted
        if currency == 'NGN':
            counted_ngn = counted
        else:
            prev_ngn = _convert_usd_to_ngn(cumulative, rate) if cumulative else 0
            cumulative += counted
            new_ngn = _convert_usd_to_ngn(cumulative, rate)
            counted_ngn = new_ngn - prev_ngn
        rev['counted_ngn'] = counted_ngn
        delta = counted_ngn - rev.get('posted_counted_ngn', 0)
        if delta != 0:
            rev['posted_counted_ngn'] = counted_ngn
            nat_date = _to_lagos_date(rev['occurred_at'])
            _post_journal_lines(state, record_id, [
                (f"customer:{payin['customer_id']}:available", delta, nat_date),
                ("payrail:receivable", -delta, nat_date)
            ])
    total_counted = sum(r['counted_minor'] for r in (state['reversals'][rid] for rid in rev_ids))
    if total_counted == 0:
        payin['status'] = 'SUCCEEDED'
    elif total_counted == amount:
        payin['status'] = 'REVERSED'
    else:
        payin['status'] = 'PARTIALLY_REVERSED'

def _process_settlement_file(state: dict, record: dict) -> None:
    batch_id = record['batch_id']
    file_seq = record['file_seq']
    value_date = record['value_date']
    lines = record['lines']
    batches = state.setdefault('settlement_batches', {})
    batch = batches.setdefault(batch_id, {'current_file_seq': -1, 'files': {}})
    if file_seq <= batch['current_file_seq']:
        return
    old_seq = batch['current_file_seq']
    old_lines = batch['files'].get(old_seq, {}).get('aggregated', {}) if old_seq != -1 else {}
    batch['files'][file_seq] = {'value_date': value_date, 'lines': lines}
    aggregated = defaultdict(lambda: {'currency': '', 'amount_minor': 0, 'settled_ngn_minor': 0})
    for line in lines:
        key = (line['line_type'], line['ref'])
        agg = aggregated[key]
        agg['currency'] = line['currency']
        agg['amount_minor'] += line['amount_minor']
        agg['settled_ngn_minor'] += line['settled_ngn_minor']
    batch['files'][file_seq]['aggregated'] = dict(aggregated)
    batch['current_file_seq'] = file_seq
    record_id = record['record_id']
    nat_date = value_date
    posted_fees = state.setdefault('posted_fee_amounts', {})
    posted_fx = state.setdefault('posted_fx_diff', {})
    all_current = state.setdefault('aggregated_current_lines', {})
    for key, old_agg in old_lines.items():
        if key in aggregated:
            continue
        line_type, ref = key
        if line_type in ('FEE', 'FEE_REFUND'):
            old_amt = old_agg['settled_ngn_minor']
            if old_amt:
                delta = -old_amt
                posted_fees[key] = posted_fees.get(key, 0) + delta
                if line_type == 'FEE':
                    _post_journal_lines(state, record_id, [
                        ('fee_expense', delta, nat_date),
                        ('payrail:receivable', -delta, nat_date)
                    ])
               
