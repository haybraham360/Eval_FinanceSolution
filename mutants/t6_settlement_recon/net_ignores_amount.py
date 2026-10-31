# expect-fail: chargeback_pair_not_netted_if_amounts_differ
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

NEW_YORK = ZoneInfo("America/New_York")
EXPONENT = {"JPY": 0, "KRW": 0, "VND": 0, "CLP": 0, "ISK": 0, "KWD": 3, "BHD": 3, "OMR": 3, "JOD": 3, "TND": 3}


def _minor(text, currency):
    text = text.replace(",", "").strip()
    negative = text.startswith("(")
    value = Decimal(text.strip("()"))
    result = int(value.scaleb(EXPONENT.get(currency, 2)))
    return -result if negative else result


def _business_date(event_time, holidays):
    local = datetime.fromisoformat(event_time.replace("Z", "+00:00")).astimezone(NEW_YORK)
    day = local.date()
    if local.hour >= 17:
        day += timedelta(days=1)
    while day.weekday() >= 5 or day.isoformat() in holidays:
        day += timedelta(days=1)
    return day


def reconcile(ledger_rows, settlement_lines, holidays):
    holidays = set(holidays)
    latest = {}
    for line in settlement_lines:
        latest[line["batch_id"]] = max(latest.get(line["batch_id"], 0), int(line["file_seq"]))

    ledger = defaultdict(lambda: [0, date.min])
    for row in ledger_rows:
        if row["type"] == "FEE":
            continue
        group = ledger[(row["psp_ref"], row["type"], row["currency"])]
        group[0] += row["amount_minor"]
        group[1] = max(group[1], date.fromisoformat(row["business_date"]))

    settled = defaultdict(lambda: [0, date.min])
    for line in settlement_lines:
        if line["line_type"] == "FEE" or int(line["file_seq"]) != latest[line["batch_id"]]:
            continue
        group = settled[(line["psp_ref"], line["line_type"], line["currency"])]
        group[0] += _minor(line["amount"], line["currency"])
        group[1] = max(group[1], _business_date(line["event_time"], holidays))

    for key in list(settled):
        ref, kind, currency = key
        if kind != "CHARGEBACK":
            continue
        partner = (ref, "CHARGEBACK_REVERSAL", currency)
        if partner in settled and key not in ledger and partner not in ledger:
            del settled[key], settled[partner]

    breaks = []
    for key in sorted(set(ledger) | set(settled)):
        ref, kind, currency = key
        record = None
        if key not in ledger:
            record = ("MISSING_IN_LEDGER", settled[key][0])
        elif key not in settled:
            record = ("MISSING_IN_SETTLEMENT", -ledger[key][0])
        elif settled[key][0] != ledger[key][0]:
            record = ("AMOUNT_MISMATCH", settled[key][0] - ledger[key][0])
        elif settled[key][1] != ledger[key][1]:
            record = ("TIMING", 0)
        if record:
            breaks.append({"psp_ref": ref, "type": kind, "currency": currency, "break": record[0], "delta_minor": record[1]})
    return breaks
