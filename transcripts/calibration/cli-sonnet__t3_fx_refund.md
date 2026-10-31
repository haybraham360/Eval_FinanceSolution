# cli-sonnet / t3_fx_refund / trial 1

- Requested: `sonnet`, resolved: `claude-haiku-5-5,claude-sonnet-5-5`, provider: claude-cli
- Run at 2026-10-31T14:43:01+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t3_fx_refund/prompt.md`.

## Model output

```python
"""Cross-currency refund journal.

Merchants settle in USD; customers pay in a local currency. At capture we sold
the local currency for USD. A refund requires buying the local currency back at
today's quote. The merchant bears no FX risk, so the difference lands in
``fx_gain_loss``.

Standard library only. All arithmetic is exact (Fraction); rounding is
ROUND_HALF_EVEN, applied only at the points the ticket specifies.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from fractions import Fraction

# ISO 4217 minor-unit exponents that differ from the default of 2.
_ZERO_DECIMAL = frozenset({
    "BIF", "CLP", "DJF", "GNF", "ISK", "JPY", "KMF", "KRW", "PYG", "RWF",
    "UGX", "UYI", "VND", "VUV", "XAF", "XOF", "XPF",
})
_THREE_DECIMAL = frozenset({"BHD", "IQD", "JOD", "KWD", "LYD", "OMR", "TND"})
_FOUR_DECIMAL = frozenset({"CLF", "UYW"})

_USD = "USD"
_USD_EXP = 2


def _exponent(ccy: str) -> int:
    if ccy in _ZERO_DECIMAL:
        return 0
    if ccy in _THREE_DECIMAL:
        return 3
    if ccy in _FOUR_DECIMAL:
        return 4
    return 2


def _is_code(s: object) -> bool:
    return isinstance(s, str) and len(s) == 3 and s.isascii() and s.isalpha() and s.isupper()


def _require_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def _round_half_even(x: Fraction) -> int:
    """Round an exact Fraction to an integer, ties to even."""
    q, r = divmod(x.numerator, x.denominator)  # floor division, 0 <= r < den
    twice = 2 * r
    if twice > x.denominator:
        return q + 1
    if twice < x.denominator:
        return q
    return q if q % 2 == 0 else q + 1


def _parse_rate(value: object, name: str) -> Fraction:
    if isinstance(value, (float, bool)) or not isinstance(value, (str, Decimal, int)):
        raise ValueError(f"{name} must be a decimal string")
    try:
        d = Decimal(value) if not isinstance(value, Decimal) else value
    except InvalidOperation:
        raise ValueError(f"{name} is not a valid decimal") from None
    if not d.is_finite() or d <= 0:
        raise ValueError(f"{name} must be a finite positive number")
    return Fraction(d)


def _parse_quote(quote: object, local: str, label: str):
    """Return (local_is_base, bid, ask) after validating the quote."""
    if not isinstance(quote, dict):
        raise ValueError(f"{label} must be a dict")
    pair = quote.get("pair")
    if not isinstance(pair, str):
        raise ValueError(f"{label}.pair must be a string")
    parts = pair.split("/")
    if len(parts) != 2 or not (_is_code(parts[0]) and _is_code(parts[1])):
        raise ValueError(f"{label}.pair is malformed: {pair!r}")
    base, term = parts
    if base == local and term == _USD:
        local_is_base = True
    elif base == _USD and term == local:
        local_is_base = False
    else:
        raise ValueError(f"{label}.pair {pair!r} does not match {local}/USD or USD/{local}")
    bid = _parse_rate(quote.get("bid"), f"{label}.bid")
    ask = _parse_rate(quote.get("ask"), f"{label}.ask")
    if bid > ask:
        raise ValueError(f"{label} is crossed (bid > ask)")
    return local_is_base, bid, ask


def _usd_cents(local_minor: int, local: str, local_is_base: bool, rate: Fraction) -> Fraction:
    """Exact USD cents equivalent of local_minor at a given quoted rate.

    LOCAL/USD: rate is USD per 1 local  -> usd = local * rate
    USD/LOCAL: rate is local per 1 USD  -> usd = local / rate
    """
    local_major = Fraction(local_minor, 10 ** _exponent(local))
    usd_major = local_major * rate if local_is_base else local_major / rate
    return usd_major * (10 ** _USD_EXP)


def post_refund(payment: dict, prior_refunds_minor: list[int], refund_minor: int, quote: dict) -> list[dict]:
    # ---- validation -------------------------------------------------------
    refund_minor = _require_int(refund_minor, "refund_minor")
    if refund_minor <= 0:
        raise ValueError("refund_minor must be positive")

    if not isinstance(payment, dict):
        raise ValueError("payment must be a dict")
    local = payment.get("currency")
    if not _is_code(local):
        raise ValueError("payment.currency must be an ISO 4217 code")
    if local == _USD:
        raise ValueError("payment.currency must not be USD")

    total = _require_int(payment.get("amount_minor"), "payment.amount_minor")
    if total <= 0:
        raise ValueError("payment.amount_minor must be positive")

    fee_bps = payment.get("fee_bps")
    if isinstance(fee_bps, (float, bool)) or not isinstance(fee_bps, (int, str, Decimal)):
        raise ValueError("payment.fee_bps must be an integer or decimal string")
    try:
        fee_bps_frac = Fraction(Decimal(fee_bps) if not isinstance(fee_bps, Decimal) else fee_bps)
    except (InvalidOperation, ValueError):
        raise ValueError("payment.fee_bps is not a valid number") from None
    if fee_bps_frac < 0 or fee_bps_frac > 10000:
        raise ValueError("payment.fee_bps must be between 0 and 10000")

    if isinstance(prior_refunds_minor, (str, bytes)) or prior_refunds_minor is None:
        raise ValueError("prior_refunds_minor must be a list of integers")
    c0 = 0
    for p in prior_refunds_minor:
        p = _require_int(p, "prior refund")
        if p < 0:
            raise ValueError("prior refunds must not be negative")
        c0 += p
    c1 = c0 + refund_minor
    if c1 > total:
        raise ValueError("cumulative refunds would exceed the captured amount")

    cap_is_base, cap_bid, cap_ask = _parse_quote(payment.get("capture_quote"), local, "capture_quote")
    now_is_base, now_bid, now_ask = _parse_quote(quote, local, "quote")

    # ---- capture: we SOLD local currency for USD ---------------------------
    # LOCAL/USD: we sell base, dealer buys base at bid.
    # USD/LOCAL: we buy USD (base), dealer sells base at ask.
    cap_rate = cap_bid if cap_is_base else cap_ask
    proceeds = _round_half_even(_usd_cents(total, local, cap_is_base, cap_rate))  # P, cents
    fee = _round_half_even(Fraction(proceeds) * fee_bps_frac / 10000)             # F, cents
    net = proceeds - fee                                                           # N, cents

    # ---- cumulative clawback / fee returned --------------------------------
    def m(c: int) -> int:
        return _round_half_even(Fraction(net * c, total))

    def g(c: int) -> int:
        return _round_half_even(Fraction(fee * c, total))

    d_m = m(c1) - m(c0)
    d_g = g(c1) - g(c0)

    # ---- refund: we BUY local currency with USD ----------------------------
    # LOCAL/USD: we buy base, dealer sells base at ask.
    # USD/LOCAL: we sell USD (base), dealer buys base at bid.
    now_rate = now_ask if now_is_base else now_bid
    cost = _round_half_even(_usd_cents(refund_minor, local, now_is_base, now_rate))  # K, cents

    fx = cost - d_m - d_g  # debit (positive) is a loss; USD lines sum to zero

    lines = [
        {"account": "merchant_payable", "currency": _USD, "amount_minor": d_m},
        {"account": "fee_revenue", "currency": _USD, "amount_minor": d_g},
        {"account": "cash", "currency": _USD, "amount_minor": -cost},
        {"account": "fx_gain_loss", "currency": _USD, "amount_minor": fx},
        {"account": "fx_position", "currency": local, "amount_minor": refund_minor},
        {"account": "customer_refunds", "currency": local, "amount_minor": -refund_minor},
    ]
    return [ln for ln in lines if ln["amount_minor"] != 0]
```
