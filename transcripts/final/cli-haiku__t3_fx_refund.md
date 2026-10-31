# cli-haiku / t3_fx_refund / trial 1

- Requested: `haiku`, resolved: `claude-haiku-5-5`, provider: claude-cli
- Run at 2026-10-31T20:49:36+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t3_fx_refund/prompt.md`.

## Model output

```python
"""Journal lines for a cross-currency refund.

All arithmetic is exact (fractions.Fraction, built from decimal strings).
Rounding is to whole USD cents or the local currency's minor unit, using
round-half-even. Floats are never used.
"""

from decimal import Decimal, InvalidOperation
from fractions import Fraction
import re

_USD = "USD"
_CCY_RE = re.compile(r"[A-Z]{3}")

# ISO 4217 minor-unit exponents that differ from the default of 2.
# Keep in sync with the ISO 4217 list. Codes not listed here use 2.
_EXPONENT_OVERRIDES = {
    **{c: 0 for c in (
        "BIF", "CLP", "DJF", "GNF", "ISK", "JPY", "KMF", "KRW",
        "PYG", "RWF", "UGX", "UYI", "VND", "VUV", "XAF", "XOF", "XPF",
    )},
    **{c: 3 for c in ("BHD", "IQD", "JOD", "KWD", "LYD", "OMR", "TND")},
    **{c: 4 for c in ("CLF", "UYW")},
}


def _exponent(ccy: str) -> int:
    return _EXPONENT_OVERRIDES.get(ccy, 2)


def _check_ccy(ccy: object, name: str) -> str:
    if not isinstance(ccy, str) or not _CCY_RE.fullmatch(ccy):
        raise ValueError(f"{name} must be a 3-letter ISO 4217 code")
    return ccy


def _check_int(value: object, name: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an int")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _decimal_value(value: object, name: str) -> Fraction:
    """Exact value of an int or a finite decimal string."""
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number")
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, str):
        try:
            d = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError(f"{name} is not a decimal string") from exc
        if not d.is_finite():
            raise ValueError(f"{name} must be finite")
        return Fraction(d)
    raise ValueError(f"{name} must be a decimal string")


def _round_half_even(x: Fraction) -> int:
    # Fraction.__round__ with no ndigits rounds half to even and returns an int.
    return round(x)


def _to_cents(x: Fraction) -> int:
    return _round_half_even(x * 100)


def _usd_per_local(quote: dict, local: str, side: str) -> Fraction:
    """USD (major units) received or paid per 1 major unit of `local`.

    side == "sell": we sell local to the dealer (receive USD).
    side == "buy":  we buy local from the dealer (pay USD).

    The dealer's bid is the price it pays us for the base. Its ask is the
    price it charges us for the base.
    """
    if not isinstance(quote, dict):
        raise ValueError("quote must be a dict")
    pair = quote.get("pair")
    if not isinstance(pair, str):
        raise ValueError("quote.pair must be a string")
    parts = pair.split("/")
    if len(parts) != 2:
        raise ValueError(f"malformed pair {pair!r}")
    base, qc = parts
    if {base, qc} != {local, _USD}:
        raise ValueError(f"pair {pair!r} does not match {local}/USD")

    bid = _decimal_value(quote.get("bid"), "quote.bid")
    ask = _decimal_value(quote.get("ask"), "quote.ask")
    if bid <= 0 or ask <= 0:
        raise ValueError("quote prices must be positive")
    if bid > ask:
        raise ValueError("crossed quote: bid > ask")

    if base == local:
        # 1 LOCAL = rate USD. Selling local gets the bid, buying local pays the ask.
        return bid if side == "sell" else ask

    # base == USD: 1 USD = rate LOCAL.
    # Selling local means buying USD from the dealer at its ask, so
    # USD per local = 1 / ask. Buying local means selling USD to the dealer
    # at its bid, so USD per local = 1 / bid.
    return Fraction(1) / ask if side == "sell" else Fraction(1) / bid


def post_refund(
    payment: dict,
    prior_refunds_minor: list[int],
    refund_minor: int,
    quote: dict,
) -> list[dict]:
    """Return journal lines for one refund of a cross-currency payment.

    Debits are positive and credits are negative. Zero-amount lines are omitted.
    Raises ValueError on invalid input or if the cumulative refund exceeds the
    captured amount.
    """
    if not isinstance(payment, dict):
        raise ValueError("payment must be a dict")

    local = _check_ccy(payment.get("currency"), "payment.currency")
    if local == _USD:
        raise ValueError("payment.currency must not be USD")

    total = _check_int(payment.get("amount_minor"), "payment.amount_minor", 1)
    refund = _check_int(refund_minor, "refund_minor", 1)

    if not isinstance(prior_refunds_minor, list):
        raise ValueError("prior_refunds_minor must be a list")
    for i, amt in enumerate(prior_refunds_minor):
        _check_int(amt, f"prior_refunds_minor[{i}]", 0)

    fee_bps = _decimal_value(payment.get("fee_bps"), "payment.fee_bps")
    if fee_bps < 0 or fee_bps > 10000:
        raise ValueError("payment.fee_bps must be within [0, 10000]")

    c0 = sum(prior_refunds_minor)
    c1 = c0 + refund
    if c1 > total:
        raise ValueError("cumulative refund would exceed captured amount")

    unit = 10 ** _exponent(local)

    # 1. USD proceeds at capture, rounded to cents.
    captured_major = Fraction(total, unit)
    proceeds_cents = _to_cents(
        captured_major * _usd_per_local(payment.get("capture_quote"), local, "sell")
    )

    # 2. Fee and merchant net, in cents.
    fee_cents = _round_half_even(Fraction(proceeds_cents) * fee_bps / 10000)
    net_cents = proceeds_cents - fee_cents

    # 3. Cumulative clawback and fee return, then this refund's deltas.
    def clawback(c: int) -> int:
        return _round_half_even(Fraction(net_cents * c, total))

    def fee_return(c: int) -> int:
        return _round_half_even(Fraction(fee_cents * c, total))

    d_merchant = clawback(c1) - clawback(c0)
    d_fee = fee_return(c1) - fee_return(c0)

    # 4. Cost of buying the refunded local amount at today's quote, in cents.
    cost_cents = _to_cents(
        Fraction(refund, unit) * _usd_per_local(quote, local, "buy")
    )

    # The USD lines must sum to zero. A positive fx_gain_loss is a debit (loss).
    fx_cents = cost_cents - d_merchant - d_fee

    candidates = [
        {"account": "merchant_payable", "currency": _USD, "amount_minor": d_merchant},
        {"account": "fee_revenue", "currency": _USD, "amount_minor": d_fee},
        {"account": "cash", "currency": _USD, "amount_minor": -cost_cents},
        {"account": "fx_gain_loss", "currency": _USD, "amount_minor": fx_cents},
        {"account": "fx_position", "currency": local, "amount_minor": refund},
        {"account": "customer_refunds", "currency": local, "amount_minor": -refund},
    ]
    return [line for line in candidates if line["amount_minor"] != 0]
```
