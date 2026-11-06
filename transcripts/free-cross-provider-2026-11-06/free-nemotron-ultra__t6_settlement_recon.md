# free-nemotron-ultra / t6_settlement_recon / trial 1

- Requested: `nvidia/nemotron-3-ultra-550b-a55b:free`, resolved: `nvidia/nemotron-3-ultra-550b-a55b:free`, provider: Nvidia
- Run at 2026-11-06T20:17:01+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t6_settlement_recon/prompt.md`.

## Model output

```python
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict
from typing import List, Dict, Tuple, Set


def reconcile(
    ledger_rows: List[Dict],
    settlement_lines: List[Dict],
    holidays: List[str]
) -> List[Dict]:
    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def parse_amount(amount_str: str) -> int:
        """Convert processor amount string to integer minor units."""
        s = amount_str.replace(",", "")
        negative = False
        if s.startswith("(") and s.endswith(")"):
            negative = True
            s = s[1:-1]
        if "." in s:
            whole, frac = s.split(".")
            minor = int(whole + frac)
        else:
            minor = int(s)
        return -minor if negative else minor

    ny_tz = ZoneInfo("America/New_York")
    holiday_set: Set[str] = set(holidays)

    def business_date_from_event(event_time: str) -> str:
        """UTC ISO string -> business date (YYYY-MM-DD) in America/New_York."""
        # Python 3.10: fromisoformat doesn't accept 'Z', replace with +00:00
        dt_utc = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
        dt_ny = dt_utc.astimezone(ny_tz)
        d = dt_ny.date()
        if dt_ny.hour >= 17:
            d += timedelta(days=1)
        while d.weekday() >= 5 or d.isoformat() in holiday_set:
            d += timedelta(days=1)
        return d.isoformat()

    # ------------------------------------------------------------------
    # 1. Process settlement lines
    # ------------------------------------------------------------------
    # Filter FEE
    non_fee_lines = [ln for ln in settlement_lines if ln["line_type"] != "FEE"]

    # Corrected files: keep only highest file_seq per batch_id
    batch_max_seq: Dict[str, int] = {}
    for ln in non_fee_lines:
        bid = ln["batch_id"]
        seq = int(ln["file_seq"])
        if seq > batch_max_seq.get(bid, -1):
            batch_max_seq[bid] = seq

    valid_lines = [
        ln for ln in non_fee_lines
        if int(ln["file_seq"]) == batch_max_seq[ln["batch_id"]]
    ]

    # Enrich each line with amount_minor and business_date
    enriched = []
    for ln in valid_lines:
        amt_minor = parse_amount(ln["amount"])
        bdate = business_date_from_event(ln["event_time"])
        enriched.append({
            "psp_ref": ln["psp_ref"],
            "type": ln["line_type"],
            "currency": ln["currency"],
            "amount_minor": amt_minor,
            "business_date": bdate,
        })

    # Group settlement by (psp_ref, type, currency)
    sett_groups: Dict[Tuple[str, str, str], Tuple[int, str]] = defaultdict(lambda: (0, ""))
    for row in enriched:
        key = (row["psp_ref"], row["type"], row["currency"])
        total, latest = sett_groups[key]
        total += row["amount_minor"]
        if row["business_date"] > latest:
            latest = row["business_date"]
        sett_groups[key] = (total, latest)

    # ------------------------------------------------------------------
    # 2. Process ledger rows
    # ------------------------------------------------------------------
    ledger_groups: Dict[Tuple[str, str, str], Tuple[int, str]] = defaultdict(lambda: (0, ""))
    for row in ledger_rows:
        if row["type"] == "FEE":
            continue
        key = (row["psp_ref"], row["type"], row["currency"])
        total, latest = ledger_groups[key]
        total += row["amount_minor"]
        if row["business_date"] > latest:
            latest = row["business_date"]
        ledger_groups[key] = (total, latest)

    # ------------------------------------------------------------------
    # 3. Chargeback netting on settlement side
    # ------------------------------------------------------------------
    # Build index by (psp_ref, currency) -> list of types present
    sett_by_ref_ccy: Dict[Tuple[str, str], Dict[str, Tuple[int, str]]] = defaultdict(dict)
    for (psp, typ, ccy), (amt, bdate) in sett_groups.items():
        sett_by_ref_ccy[(psp, ccy)][typ] = (amt, bdate)

    ledger_by_ref_ccy: Dict[Tuple[str, str], Set[str]] = defaultdict(set)
    for (psp, typ, ccy) in ledger_groups:
        ledger_by_ref_ccy[(psp, ccy)].add(typ)

    to_remove = set()
    for (psp, ccy), type_map in sett_by_ref_ccy.items():
        cb_amt, cb_date = type_map.get("CHARGEBACK", (0, ""))
        cbr_amt, cbr_date = type_map.get("CHARGEBACK_REVERSAL", (0, ""))
        if "CHARGEBACK" in type_map and "CHARGEBACK_REVERSAL" in type_map:
            if cb_amt + cbr_amt == 0:
                # Ledger must have neither
                if "CHARGEBACK" not in ledger_by_ref_ccy[(psp, ccy)] and \
                   "CHARGEBACK_REVERSAL" not in ledger_by_ref_ccy[(psp, ccy)]:
                    to_remove.add((psp, "CHARGEBACK", ccy))
                    to_remove.add((psp, "CHARGEBACK_REVERSAL", ccy))

    for key in to_remove:
        sett_groups.pop(key, None)

    # ------------------------------------------------------------------
    # 4. Match groups
    # ------------------------------------------------------------------
    all_keys = set(sett_groups.keys()) | set(ledger_groups.keys())
    breaks = []

    for key in all_keys:
        psp, typ, ccy = key
        s_amt, s_date = sett_groups.get(key, (0, ""))
        l_amt, l_date = ledger_groups.get(key, (0, ""))

        if key not in sett_groups:
            breaks.append({
                "psp_ref": psp,
                "type": typ,
                "currency": ccy,
                "break": "MISSING_IN_SETTLEMENT",
                "delta_minor": -l_amt,
            })
        elif key not in ledger_groups:
            breaks.append({
                "psp_ref": psp,
                "type": typ,
                "currency": ccy,
                "break": "MISSING_IN_LEDGER",
                "delta_minor": s_amt,
            })
        else:
            if s_amt != l_amt:
                breaks.append({
                    "psp_ref": psp,
                    "type": typ,
                    "currency": ccy,
                    "break": "AMOUNT_MISMATCH",
                    "delta_minor": s_amt - l_amt,
                })
            elif s_date != l_date:
                breaks.append({
                    "psp_ref": psp,
                    "type": typ,
                    "currency": ccy,
                    "break": "TIMING",
                    "delta_minor": 0,
                })
            # else: match – no break

    # ------------------------------------------------------------------
    # 5. Sort output
    # ------------------------------------------------------------------
    breaks.sort(key=lambda x: (x["psp_ref"], x["type"], x["currency"]))
    return breaks
```
