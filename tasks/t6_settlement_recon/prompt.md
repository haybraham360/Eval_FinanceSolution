# Ticket: daily PSP settlement reconciliation

Each morning we compare our ledger with the card processor's settlement data and hand finance a list of breaks. Write the matching engine.

Implement in one Python 3.10+ module, standard library only (`zoneinfo` is available):

```python
def reconcile(ledger_rows: list[dict], settlement_lines: list[dict], holidays: list[str]) -> list[dict]: ...
```

## Inputs

`ledger_rows`, already in canonical form:

```python
{"psp_ref": str, "type": str, "currency": str, "amount_minor": int, "business_date": "YYYY-MM-DD"}
```

`settlement_lines`, as the processor sends them, all values strings:

```python
{"batch_id": str, "file_seq": "12", "line_type": str, "psp_ref": str, "currency": str, "amount": str, "event_time": "2026-03-08T21:30:00Z"}
```

`type` and `line_type` are `SALE`, `REFUND`, `CHARGEBACK`, `CHARGEBACK_REVERSAL` or `FEE`. `holidays` lists bank-holiday dates as `YYYY-MM-DD`.

## Processor file rules

- **Amounts** are major units as text in the currency's ISO 4217 precision, with optional thousands separators. A negative is shown in accounting style, in parentheses: `"1,234.56"`, `"(12.34)"`, `"1,200"` (JPY), `"12.345"` (KWD). Convert to integer minor units exactly.
- **Corrected files.** The processor can resend a batch. For each `batch_id`, only the lines with the highest `file_seq` exist. Lines of a batch from any lower `file_seq` are void, even when the higher one has fewer lines.
- **Business date.** Convert `event_time` from UTC to `America/New_York` wall-clock time. An event at or after 17:00 local belongs to the next calendar day. Then, if the resulting date is a Saturday, a Sunday or in `holidays`, roll it forward to the next date that is none of those.
- **FEE lines** are not reconciled here. Ignore them on both sides.

## Matching

Group each side by `(psp_ref, type, currency)`, where a settlement line's `line_type` is its `type`. Sum the amounts in each group, because split tenders post several ledger rows against one settlement line and vice versa. A group's business date is the latest business date in the group.

First apply **chargeback netting**: if for one `(psp_ref, currency)` the settlement side has both a `CHARGEBACK` and a `CHARGEBACK_REVERSAL` group whose amounts sum to zero, and the ledger has neither of those groups, remove both settlement groups. Otherwise treat them normally.

Then for each group key on either side:

| situation | `break` | `delta_minor` |
|---|---|---|
| only in settlement | `MISSING_IN_LEDGER` | settlement amount |
| only in ledger | `MISSING_IN_SETTLEMENT` | minus the ledger amount |
| amounts differ | `AMOUNT_MISMATCH` | settlement amount minus ledger amount |
| amounts equal, business dates differ | `TIMING` | 0 |
| amounts and business dates equal | no output | |

## Output

Return a list of `{"psp_ref", "type", "currency", "break", "delta_minor"}` sorted by `psp_ref`, then `type`, then `currency`. Return the complete module in one ```python block.
