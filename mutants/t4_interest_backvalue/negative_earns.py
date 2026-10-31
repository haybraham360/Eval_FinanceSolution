# expect-fail: overdrawn_days_earn_nothing
import calendar
from datetime import date, timedelta
from fractions import Fraction


def _rate(rates, day):
    current = None
    for entry in rates:
        if date.fromisoformat(entry["from"]) <= day:
            current = entry
    return current


def _round(x):
    return round(x)  # int rounding of a Fraction is half-even


def _month_ends(first, last):
    out = []
    day = first
    while day <= last:
        end = day.replace(day=calendar.monthrange(day.year, day.month)[1])
        if end <= last:
            out.append(end)
        day = end + timedelta(days=1)
    return out


def _cumulative(opening, first, month_end, known, rates, month_ends):
    """E(month_end), rounded, in the history where exactly `known` was always known."""
    by_day = {}
    for t in known:
        by_day[t["value_date"]] = by_day.get(t["value_date"], 0) + t["amount_minor"]
    balance = opening
    exact = Fraction(0)
    capitalised = 0
    pending = 0
    day = first
    while day <= month_end:
        balance += pending + by_day.get(day.isoformat(), 0)
        pending = 0
        if True:
            r = _rate(rates, day)
            low = min(balance, 1_000_000)
            annual = low * Fraction(r["tier1"]) + (balance - low) * Fraction(r["tier2"])
            exact += annual / (366 if calendar.isleap(day.year) else 365)
        if day in month_ends:
            pending = _round(exact) - capitalised
            capitalised += pending
        day += timedelta(days=1)
    return capitalised


def capitalisations(opening_minor, start, end, transactions, rates):
    first = date.fromisoformat(start)
    ends = _month_ends(first, date.fromisoformat(end))
    results = []
    posted = 0
    for month_end in ends:
        known = [t for t in transactions if date.fromisoformat(t["post_date"]) <= month_end]
        amount = _cumulative(opening_minor, first, month_end, known, rates, set(ends)) - posted
        posted += amount
        results.append({"date": month_end.isoformat(), "amount_minor": amount})
    return results
