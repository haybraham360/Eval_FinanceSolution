# expect-fail: rounding_is_cumulative_not_per_refund
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

MINOR_UNITS = {"JPY": 0, "KRW": 0, "VND": 0, "CLP": 0, "ISK": 0, "KWD": 3, "BHD": 3, "OMR": 3, "JOD": 3, "TND": 3}


def _round(value):
    return int(value.to_integral_value(rounding=ROUND_HALF_EVEN))


def _major(amount_minor, currency):
    return Decimal(amount_minor).scaleb(-MINOR_UNITS.get(currency, 2))


def _sell_local(amount, currency, quote):
    """We sell local for USD: the dealer buys its base at the bid and sells its base at the ask."""
    base = quote["pair"].split("/")[0]
    return amount * Decimal(quote["bid"]) if base == currency else amount / Decimal(quote["ask"])


def _buy_local(amount, currency, quote):
    base = quote["pair"].split("/")[0]
    return amount * Decimal(quote["ask"]) if base == currency else amount / Decimal(quote["bid"])


def post_refund(payment, prior_refunds_minor, refund_minor, quote):
    total = payment["amount_minor"]
    currency = payment["currency"]
    c0 = sum(prior_refunds_minor)
    c1 = c0 + refund_minor
    if refund_minor <= 0 or c1 > total:
        raise ValueError("refund out of range")
    with localcontext() as ctx:
        ctx.prec = 80
        proceeds = _round(_sell_local(_major(total, currency), currency, payment["capture_quote"]) * 100)
        fee = _round(Decimal(proceeds * payment["fee_bps"]) / 10000)
        net = proceeds - fee

        def share(amount, cumulative):
            return _round(Decimal(amount * cumulative) / total)

        d_merchant = _round(Decimal(net * refund_minor) / total)
        d_fee = _round(Decimal(fee * refund_minor) / total)
        cost = _round(_buy_local(_major(refund_minor, currency), currency, quote) * 100)
    lines = [
        ("merchant_payable", "USD", d_merchant),
        ("fee_revenue", "USD", d_fee),
        ("cash", "USD", -cost),
        ("fx_gain_loss", "USD", cost - d_merchant - d_fee),
        ("fx_position", currency, refund_minor),
        ("customer_refunds", currency, -refund_minor),
    ]
    return [{"account": a, "currency": c, "amount_minor": v} for a, c, v in lines if v]
