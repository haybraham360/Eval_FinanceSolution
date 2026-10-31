"""Grader for t4. A small independent model in exact rationals plus hand-worked anchors."""
import calendar
from datetime import date, timedelta
from fractions import Fraction as Q

from common import Checks, eq

CHECKS = Checks()
FLAT = [{"from": "2020-01-01", "tier1": "0.0200", "tier2": "0.0300"}]


def d(s):
    return date.fromisoformat(s)


def tx(value, post, amt):
    return {"value_date": value, "post_date": post, "amount_minor": amt}


def half_even(x):
    n = x.numerator // x.denominator
    rem = x - n
    if rem > Q(1, 2) or (rem == Q(1, 2) and n % 2):
        n += 1
    return n


def rate_on(rates, day):
    return [r for r in rates if d(r["from"]) <= day][-1]


def month_ends(s, e):
    y, m, out = s.year, s.month, []
    while True:
        last = date(y, m, calendar.monthrange(y, m)[1])
        if last > e:
            return out
        if last >= s:
            out.append(last)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def corrected_cumulative(opening, s, upto, known, rates):
    bal, exact, posted = opening, Q(0), 0
    day = s
    while day <= upto:
        bal += sum(t["amount_minor"] for t in known if d(t["value_date"]) == day)
        if bal > 0:
            r = rate_on(rates, day)
            yearly = min(bal, 1_000_000) * Q(r["tier1"]) + max(bal - 1_000_000, 0) * Q(r["tier2"])
            exact += yearly / (366 if calendar.isleap(day.year) else 365)
        if day == date(day.year, day.month, calendar.monthrange(day.year, day.month)[1]):
            cap = half_even(exact) - posted
            posted += cap
            bal += cap  # enters B(d) from the following day
        day += timedelta(days=1)
    return half_even(exact)


def expected(opening, start, end, txs, rates):
    s, e = d(start), d(end)
    out, total = [], 0
    for m in month_ends(s, e):
        known = [t for t in txs if d(t["post_date"]) <= m]
        amount = corrected_cumulative(opening, s, m, known, rates) - total
        total += amount
        out.append({"date": m.isoformat(), "amount_minor": amount})
    return out


def run(mod, *args):
    return [{"date": r["date"], "amount_minor": r["amount_minor"]} for r in mod.capitalisations(*args)]


def same(mod, *args):
    eq(run(mod, *args), expected(*args), "postings")


@CHECKS
def anchor_leap_january(mod):
    # 1,000,000 x 2% x 31 / 366 = 1693.99 rounds to 1694.
    eq(run(mod, 1_000_000, "2024-01-01", "2024-01-31", [], FLAT), [{"date": "2024-01-31", "amount_minor": 1694}], "January 2024")


@CHECKS
def anchor_common_year_march(mod):
    # 500,000 x 2% x 31 / 365 = 849.32 rounds to 849.
    eq(run(mod, 500_000, "2023-03-01", "2023-03-31", [], FLAT), [{"date": "2023-03-31", "amount_minor": 849}], "March 2023")


@CHECKS
def anchor_marginal_tier(mod):
    # (1,000,000 x 2% + 500,000 x 3%) x 30 / 365 = 2876.71 -> 2877.
    eq(run(mod, 1_500_000, "2023-04-01", "2023-04-30", [], [{"from": "2020-01-01", "tier1": "0.0200", "tier2": "0.0300"}])[0]["amount_minor"], 2877, "tier")


@CHECKS
def year_boundary_changes_denominator(mod):
    same(mod, 2_000_000, "2023-11-15", "2024-03-31", [], FLAT)


@CHECKS
def capitalised_interest_compounds_from_next_day(mod):
    same(mod, 990_000, "2023-01-01", "2023-12-31", [], FLAT)


@CHECKS
def sub_minor_residue_is_never_lost(mod):
    rows = run(mod, 100, "2023-01-01", "2024-12-31", [], FLAT)
    eq(rows, expected(100, "2023-01-01", "2024-12-31", [], FLAT), "tiny balance")
    eq(sum(r["amount_minor"] for r in rows) > 0, True, "accrual across months must eventually post")


@CHECKS
def midmonth_rate_change_and_tx(mod):
    rates = [{"from": "2023-01-01", "tier1": "0.0150", "tier2": "0.0250"}, {"from": "2023-02-14", "tier1": "0.0175", "tier2": "0.0325"}]
    same(mod, 800_000, "2023-01-10", "2023-03-20", [tx("2023-02-20", "2023-02-20", 900_000), tx("2023-03-02", "2023-03-02", -250_000)], rates)


@CHECKS
def overdrawn_days_earn_nothing(mod):
    same(mod, 100_000, "2023-05-01", "2023-07-31", [tx("2023-05-10", "2023-05-10", -300_000), tx("2023-06-20", "2023-06-20", 250_000)], FLAT)


@CHECKS
def month_end_value_date_counts_that_day(mod):
    same(mod, 0, "2023-01-01", "2023-02-28", [tx("2023-01-31", "2023-01-31", 3_000_000)], FLAT)


@CHECKS
def back_value_posts_only_in_later_month(mod):
    t = [tx("2023-01-10", "2023-02-03", 2_000_000)]
    rows = run(mod, 100_000, "2023-01-01", "2023-02-28", t, FLAT)
    eq(rows, expected(100_000, "2023-01-01", "2023-02-28", t, FLAT), "postings")
    eq(rows[0], {"date": "2023-01-31", "amount_minor": expected(100_000, "2023-01-01", "2023-01-31", [], FLAT)[0]["amount_minor"]}, "January ignores a February posting")


@CHECKS
def back_value_correction_compounds_through_corrected_history(mod):
    t = [tx("2023-01-05", "2023-06-09", 40_000_000)]
    same(mod, 2_000_000, "2023-01-01", "2023-08-31", t, FLAT)


@CHECKS
def back_value_withdrawal_gives_negative_posting(mod):
    t = [tx("2023-02-02", "2023-05-20", -1_950_000)]
    rows = run(mod, 2_000_000, "2023-01-01", "2023-05-31", t, FLAT)
    eq(rows, expected(2_000_000, "2023-01-01", "2023-05-31", t, FLAT), "postings")
    eq(rows[-1]["amount_minor"] < 0, True, "May must claw back")


@CHECKS
def posted_on_month_end_is_known_that_month(mod):
    same(mod, 500_000, "2023-01-01", "2023-03-31", [tx("2023-01-15", "2023-02-28", 700_000), tx("2023-02-15", "2023-03-01", 900_000)], FLAT)


@CHECKS
def partial_final_month_has_no_row(mod):
    eq(len(run(mod, 500_000, "2023-01-15", "2023-03-30", [], FLAT)), 2, "rows")
