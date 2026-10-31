"""Grader for t3. Exact rational arithmetic, independent of the reference's Decimal code.
The three anchors are hand-worked."""
from fractions import Fraction as Q

from common import Checks, eq

CHECKS = Checks()
EXP = {"JPY": 0, "KRW": 0, "KWD": 3, "BHD": 3, "EUR": 2, "GBP": 2}


def half_even(x):
    n = x.numerator // x.denominator
    rem = x - n
    if rem > Q(1, 2) or (rem == Q(1, 2) and n % 2):
        n += 1
    return n


def sell_local(ccy, major, q):
    base, _ = q["pair"].split("/")
    return major * Q(q["bid"]) if base == ccy else major / Q(q["ask"])


def buy_local(ccy, major, q):
    base, _ = q["pair"].split("/")
    return major * Q(q["ask"]) if base == ccy else major / Q(q["bid"])


def expected(p, prior, r, q):
    ccy = p["currency"]
    unit = Q(10) ** EXP[ccy]
    T = p["amount_minor"]
    P = half_even(sell_local(ccy, Q(T) / unit, p["capture_quote"]) * 100)
    F = half_even(Q(P * p["fee_bps"], 10000))
    N = P - F
    c0, c1 = sum(prior), sum(prior) + r
    dM = half_even(Q(N * c1, T)) - half_even(Q(N * c0, T))
    dG = half_even(Q(F * c1, T)) - half_even(Q(F * c0, T))
    K = half_even(buy_local(ccy, Q(r) / unit, q) * 100)
    lines = {("merchant_payable", "USD"): dM, ("fee_revenue", "USD"): dG, ("cash", "USD"): -K, ("fx_gain_loss", "USD"): K - dM - dG, ("fx_position", ccy): r, ("customer_refunds", ccy): -r}
    return {k: v for k, v in lines.items() if v}


def got(mod, p, prior, r, q):
    out = {}
    for line in mod.post_refund(dict(p), list(prior), r, dict(q)):
        key = (line["account"], line["currency"])
        eq(key in out, False, f"duplicate line {key}")
        eq(type(line["amount_minor"]), int, "amount type")
        out[key] = line["amount_minor"]
    return out


def same(mod, p, prior, r, q):
    eq(got(mod, p, prior, r, q), expected(p, prior, r, q), f"{p['currency']} refund {r} after {prior}")


EUR = {"currency": "EUR", "amount_minor": 10000, "capture_quote": {"pair": "EUR/USD", "bid": "1.0800", "ask": "1.0810"}, "fee_bps": 290}
JPY = {"currency": "JPY", "amount_minor": 150000, "capture_quote": {"pair": "USD/JPY", "bid": "149.50", "ask": "150.00"}, "fee_bps": 290}
KWD = {"currency": "KWD", "amount_minor": 100000, "capture_quote": {"pair": "KWD/USD", "bid": "3.25", "ask": "3.26"}, "fee_bps": 290}


@CHECKS
def anchor_eur_base_pair(mod):
    # Proceeds 100.00 x 1.0800 = 10800c, fee 313c, net 10487c. Buying back at the ask costs 11010c, a 210c loss.
    eq(got(mod, EUR, [], 10000, {"pair": "EUR/USD", "bid": "1.1000", "ask": "1.1010"}),
       {("merchant_payable", "USD"): 10487, ("fee_revenue", "USD"): 313, ("cash", "USD"): -11010, ("fx_gain_loss", "USD"): 210, ("fx_position", "EUR"): 10000, ("customer_refunds", "EUR"): -10000}, "EUR")


@CHECKS
def anchor_jpy_inverted_pair_zero_decimals(mod):
    # 150000 JPY / 150.00 ask = 100000c, fee 2900c. Buying JPY sells USD at the bid: 150000 / 160 = 93750c, a 6250c gain.
    eq(got(mod, JPY, [], 150000, {"pair": "USD/JPY", "bid": "160.00", "ask": "160.50"}),
       {("merchant_payable", "USD"): 97100, ("fee_revenue", "USD"): 2900, ("cash", "USD"): -93750, ("fx_gain_loss", "USD"): -6250, ("fx_position", "JPY"): 150000, ("customer_refunds", "JPY"): -150000}, "JPY")


@CHECKS
def anchor_kwd_three_decimals_fee_tie(mod):
    # 100.000 KWD x 3.25 = 32500c. Fee 942.5c rounds half-even to 942c, net 31558c.
    eq(got(mod, KWD, [], 100000, {"pair": "KWD/USD", "bid": "3.25", "ask": "3.25"}),
       {("merchant_payable", "USD"): 31558, ("fee_revenue", "USD"): 942, ("cash", "USD"): -32500, ("fx_position", "KWD"): 100000, ("customer_refunds", "KWD"): -100000}, "KWD")


@CHECKS
def quote_side_per_pair_direction(mod):
    gbp = {"currency": "GBP", "amount_minor": 777777, "capture_quote": {"pair": "GBP/USD", "bid": "1.2641", "ask": "1.2649"}, "fee_bps": 175}
    krw = {"currency": "KRW", "amount_minor": 987654321, "capture_quote": {"pair": "USD/KRW", "bid": "1331.10", "ask": "1332.40"}, "fee_bps": 310}
    same(mod, gbp, [], 111111, {"pair": "GBP/USD", "bid": "1.3001", "ask": "1.3009"})
    same(mod, krw, [], 123456789, {"pair": "USD/KRW", "bid": "1402.20", "ask": "1403.60"})


@CHECKS
def rounding_is_cumulative_not_per_refund(mod):
    p = {"currency": "EUR", "amount_minor": 1000, "capture_quote": {"pair": "EUR/USD", "bid": "1.00", "ask": "1.00"}, "fee_bps": 333}
    q = {"pair": "EUR/USD", "bid": "1.00", "ask": "1.00"}
    prior, merchant, fee = [], 0, 0
    for r in [100] * 10:  # 96.7c and 3.3c per refund: rounding each one would claw back 970c and 30c
        same(mod, p, prior, r, q)
        lines = got(mod, p, prior, r, q)
        merchant += lines.get(("merchant_payable", "USD"), 0)
        fee += lines.get(("fee_revenue", "USD"), 0)
        prior.append(r)
    eq((merchant, fee), (967, 33), "full clawback")


@CHECKS
def many_partials_drain_exactly(mod):
    p = {"currency": "JPY", "amount_minor": 99999, "capture_quote": {"pair": "USD/JPY", "bid": "148.13", "ask": "148.27"}, "fee_bps": 295}
    q = {"pair": "USD/JPY", "bid": "151.02", "ask": "151.20"}
    prior = []
    for r in [1, 7, 13, 1009, 50000, 48969]:
        same(mod, p, prior, r, q)
        prior.append(r)


@CHECKS
def exact_above_float_precision(mod):
    p = {"currency": "BHD", "amount_minor": 912345678901234567, "capture_quote": {"pair": "BHD/USD", "bid": "2.6525", "ask": "2.6535"}, "fee_bps": 123}
    same(mod, p, [12345678901234567], 300000000000000001, {"pair": "BHD/USD", "bid": "2.6601", "ask": "2.6611"})


@CHECKS
def ties_use_half_even(mod):
    p = {"currency": "EUR", "amount_minor": 200, "capture_quote": {"pair": "EUR/USD", "bid": "1.0125", "ask": "1.0130"}, "fee_bps": 500}
    same(mod, p, [], 50, {"pair": "EUR/USD", "bid": "1.0000", "ask": "1.0250"})
    same(mod, p, [50], 150, {"pair": "EUR/USD", "bid": "1.0000", "ask": "1.0150"})


@CHECKS
def zero_lines_are_omitted(mod):
    lines = got(mod, EUR, [], 10000, {"pair": "EUR/USD", "bid": "1.0800", "ask": "1.0800"})
    eq(("fx_gain_loss", "USD") in lines, False, "zero fx line present")


@CHECKS
def rejects_invalid_refunds(mod):
    q = EUR["capture_quote"]
    for prior, r in [([], 0), ([], -5), ([], 10001), ([6000], 4001)]:
        try:
            mod.post_refund(dict(EUR), prior, r, dict(q))
        except ValueError:
            continue
        raise AssertionError(f"no ValueError for prior={prior} refund={r}")
