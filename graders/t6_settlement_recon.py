"""Grader for t6. Every expected list is written by hand from the ticket's rules."""
from common import Checks, eq

CHECKS = Checks()


def line(ref, kind, amount, when="2026-03-04T15:00:00Z", ccy="USD", batch="b1", seq="1"):
    return {"batch_id": batch, "file_seq": seq, "line_type": kind, "psp_ref": ref, "currency": ccy, "amount": amount, "event_time": when}


def led(ref, kind, minor, day="2026-03-04", ccy="USD"):
    return {"psp_ref": ref, "type": kind, "currency": ccy, "amount_minor": minor, "business_date": day}


def brk(ref, kind, name, delta, ccy="USD"):
    return {"psp_ref": ref, "type": kind, "currency": ccy, "break": name, "delta_minor": delta}


def run(mod, ledger, lines, holidays=()):
    rows = mod.reconcile(ledger, lines, list(holidays))
    return [{k: r[k] for k in ("psp_ref", "type", "currency", "break", "delta_minor")} for r in rows]


@CHECKS
def clean_match_is_silent(mod):
    eq(run(mod, [led("a", "SALE", 1000)], [line("a", "SALE", "10.00")]), [], "breaks")


@CHECKS
def amount_formats(mod):
    ledger = [led("a", "SALE", 123456), led("b", "REFUND", -1234), led("c", "SALE", 1200, ccy="JPY"), led("d", "SALE", 12345, ccy="KWD"), led("e", "SALE", 1234567, ccy="KRW")]
    lines = [line("a", "SALE", "1,234.56"), line("b", "REFUND", "(12.34)"), line("c", "SALE", "1,200", ccy="JPY"), line("d", "SALE", "12.345", ccy="KWD"), line("e", "SALE", "1,234,567", ccy="KRW")]
    eq(run(mod, ledger, lines), [], "breaks")


@CHECKS
def amount_precision_is_exact(mod):
    # 1.15 and 4.35 are classic float truncation cases.
    eq(run(mod, [led("a", "SALE", 115), led("b", "SALE", 435), led("c", "SALE", 1001)], [line("a", "SALE", "1.15"), line("b", "SALE", "4.35"), line("c", "SALE", "10.01")]), [], "breaks")


@CHECKS
def corrected_file_replaces_whole_batch(mod):
    lines = [line("a", "SALE", "10.00", seq="1"), line("gone", "SALE", "5.00", seq="1"), line("a", "SALE", "12.00", seq="2")]
    eq(run(mod, [led("a", "SALE", 1200)], lines), [], "breaks")


@CHECKS
def file_seq_compares_as_number(mod):
    lines = [line("a", "SALE", "10.00", seq="9"), line("a", "SALE", "12.00", seq="10")]
    eq(run(mod, [led("a", "SALE", 1200)], lines), [], "breaks")


@CHECKS
def seq_is_per_batch(mod):
    lines = [line("a", "SALE", "10.00", batch="b1", seq="7"), line("b", "SALE", "20.00", batch="b2", seq="2")]
    eq(run(mod, [led("a", "SALE", 1000), led("b", "SALE", 2000)], lines), [], "breaks")


@CHECKS
def cutoff_before_and_at_17_est(mod):
    # Winter: New York is UTC-5. Wed 4 March 21:59:59Z is 16:59:59 local; 22:00:00Z is exactly 17:00.
    eq(run(mod, [led("a", "SALE", 100, "2026-03-04")], [line("a", "SALE", "1.00", "2026-03-04T21:59:59Z")]), [], "before cutoff")
    eq(run(mod, [led("a", "SALE", 100, "2026-03-05")], [line("a", "SALE", "1.00", "2026-03-04T22:00:00Z")]), [], "at cutoff")


@CHECKS
def cutoff_during_daylight_time(mod):
    # After 8 March 2026 New York is UTC-4: Tue 10 March 21:30Z is 17:30 local, so the 11th.
    eq(run(mod, [led("a", "SALE", 100, "2026-03-11")], [line("a", "SALE", "1.00", "2026-03-10T21:30:00Z")]), [], "summer")


@CHECKS
def utc_date_differs_from_local_date(mod):
    # Thu 5 March 02:00Z is Wed 21:00 local: after cutoff on the 4th, so the 5th. 
    eq(run(mod, [led("a", "SALE", 100, "2026-03-05")], [line("a", "SALE", "1.00", "2026-03-05T02:00:00Z")]), [], "evening local")
    # Fri 6 March 01:00Z is Thu 20:00 local: the 6th, a Friday.
    eq(run(mod, [led("b", "SALE", 100, "2026-03-06")], [line("b", "SALE", "1.00", "2026-03-06T01:00:00Z")]), [], "evening local 2")


@CHECKS
def weekend_and_holiday_roll(mod):
    # Fri 6 March 23:00Z is 18:00 local: Saturday 7th rolls to Monday 9th, a holiday, so Tuesday 10th.
    eq(run(mod, [led("a", "SALE", 100, "2026-03-10")], [line("a", "SALE", "1.00", "2026-03-06T23:00:00Z")], ["2026-03-09"]), [], "rolled twice")


@CHECKS
def fee_lines_ignored_on_both_sides(mod):
    eq(run(mod, [led("x", "FEE", -30)], [line("a", "FEE", "(0.45)")]), [], "breaks")


@CHECKS
def split_tender_sums_both_sides(mod):
    ledger = [led("a", "SALE", 600), led("a", "SALE", 400), led("b", "SALE", 1000)]
    lines = [line("a", "SALE", "10.00"), line("b", "SALE", "7.00"), line("b", "SALE", "3.00")]
    eq(run(mod, ledger, lines), [], "breaks")


@CHECKS
def group_date_is_latest(mod):
    ledger = [led("a", "SALE", 600, "2026-03-03"), led("a", "SALE", 400, "2026-03-04")]
    eq(run(mod, ledger, [line("a", "SALE", "10.00")]), [], "breaks")


@CHECKS
def chargeback_pair_nets_out(mod):
    eq(run(mod, [], [line("a", "CHARGEBACK", "(10.00)"), line("a", "CHARGEBACK_REVERSAL", "10.00")]), [], "breaks")


@CHECKS
def chargeback_pair_not_netted_if_ledger_has_one(mod):
    eq(run(mod, [led("a", "CHARGEBACK", -1000)], [line("a", "CHARGEBACK", "(10.00)"), line("a", "CHARGEBACK_REVERSAL", "10.00")]),
       [brk("a", "CHARGEBACK_REVERSAL", "MISSING_IN_LEDGER", 1000)], "breaks")


@CHECKS
def chargeback_pair_not_netted_if_amounts_differ(mod):
    eq(run(mod, [], [line("a", "CHARGEBACK", "(10.00)"), line("a", "CHARGEBACK_REVERSAL", "9.00")]),
       [brk("a", "CHARGEBACK", "MISSING_IN_LEDGER", -1000), brk("a", "CHARGEBACK_REVERSAL", "MISSING_IN_LEDGER", 900)], "breaks")


@CHECKS
def every_break_type_sorted(mod):
    ledger = [led("c", "SALE", 500), led("b", "SALE", 1000), led("d", "SALE", 700, "2026-03-05"), led("b", "REFUND", -100)]
    lines = [line("a", "SALE", "3.00"), line("b", "SALE", "9.75"), line("d", "SALE", "7.00"), line("b", "REFUND", "(1.00)", ccy="EUR")]
    eq(run(mod, ledger, lines), [
        brk("a", "SALE", "MISSING_IN_LEDGER", 300),
        brk("b", "REFUND", "MISSING_IN_LEDGER", -100, ccy="EUR"),
        brk("b", "REFUND", "MISSING_IN_SETTLEMENT", 100),
        brk("b", "SALE", "AMOUNT_MISMATCH", -25),
        brk("c", "SALE", "MISSING_IN_SETTLEMENT", -500),
        brk("d", "SALE", "TIMING", 0),
    ], "breaks")
