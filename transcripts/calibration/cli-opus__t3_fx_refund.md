# cli-opus / t3_fx_refund / trial 1

- Requested: `opus`, resolved: `claude-haiku-5-5,claude-opus-5-5`, provider: claude-cli
- Run at 2026-10-31T14:39:29+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t3_fx_refund/prompt.md`.

## Model output

```python
"""Cross-currency refund journal.

Merchants settle in USD and customers pay in local currency. At capture we
sold the customer's local currency for USD. A refund buys the local currency
back at today's dealer price. The merchant is clawed back pro rata at the
capture economics, and any difference between that clawback and today's
cost lands in fx_gain_loss.

All arithmetic is exact rational arithmetic (fractions.Fraction built from
decimal.Decimal). Floats are rejected everywhere. Every rounding is
ROUND_HALF_EVEN to the minor unit of the relevant currency.
"""

from __future__ import annotations

import re
from decimal import Decimal
from fractions import Fraction

__all__ = ["post_refund", "MINOR_UNITS"]

USD = "USD"

# ISO 4217 minor-unit exponents for currencies with a defined minor unit.
# Codes with no minor unit ("N.A.", such as XAU or XDR) are deliberately
# absent. An unknown code is rejected rather than guessed.
_ZERO_DECIMAL = {
    "BIF", "CLP", "DJF", "GNF", "ISK", "JPY", "KMF", "KRW", "PYG", "RWF",
    "UGX", "UYI", "VND", "VUV", "XAF", "XOF", "XPF",
}
_THREE_DECIMAL = {"BHD", "IQD", "JOD", "KWD", "LYD", "OMR", "TND"}
_FOUR_DECIMAL = {"CLF", "UYW"}
_TWO_DECIMAL = {
    "AED", "AFN", "ALL", "AMD", "ANG", "AOA", "ARS", "AUD", "AWG", "AZN",
    "BAM", "BBD", "BDT", "BGN", "BMD", "BND", "BOB", "BOV", "BRL", "BSD",
    "BTN", "BWP", "BYN", "BZD", "CAD", "CDF", "CHE", "CHF", "CHW", "CNY",
    "COP", "COU", "CRC", "CUP", "CVE", "CZK", "DKK", "DOP", "DZD", "EGP",
    "ERN", "ETB", "EUR", "FJD", "FKP", "GBP", "GEL", "GHS", "GIP", "GMD",
    "GTQ", "GYD", "HKD", "HNL", "HTG", "HUF", "IDR", "ILS", "INR", "IRR",
    "JMD", "KES", "KGS", "KHR", "KPW", "KYD", "KZT", "LAK", "LBP", "LKR",
    "LRD", "LSL", "MAD", "MDL", "MGA", "MKD", "MMK", "MNT", "MOP", "MRU",
    "MUR", "MVR", "MWK", "MXN", "MXV", "MYR", "MZN", "NAD", "NGN", "NIO",
    "NOK", "NPR", "NZD", "PAB", "PEN", "PGK", "PHP", "PKR", "PLN", "QAR",
    "RON", "RSD", "RUB", "SAR", "SBD", "SCR", "SDG", "SEK", "SGD", "SHP",
    "SLE", "SOS", "SRD", "SSP", "STN", "SVC", "SYP", "SZL", "THB", "TJS",
    "TMT", "TOP", "TRY", "TTD", "TWD", "TZS", "UAH", "USD", "USN", "UYU",
    "UZS", "VED", "VES", "WST", "XCD", "XCG", "YER", "ZAR", "ZMW", "ZWG",
}

MINOR_UNITS: dict[str, int] = {}
for _codes, _exp in (
    (_ZERO_DECIMAL, 0),
    (_TWO_DECIMAL, 2),
    (_THREE_DECIMAL, 3),
    (_FOUR_DECIMAL, 4),
):
    for _code in _codes:
        MINOR_UNITS[_code] = _exp

_DECIMAL_RE = re.compile(r"^[0-9]+(\.[0-9]+)?$")
_PAIR_RE = re.compile(r"^([A-Z]{3})/([A-Z]{3})$")


# --------------------------------------------------------------------------
# Validation helpers
# --------------------------------------------------------------------------

def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _exponent(currency: object) -> int:
    if not isinstance(currency, str) or currency not in MINOR_UNITS:
        raise ValueError(f"unknown or unsupported ISO 4217 currency: {currency!r}")
    return MINOR_UNITS[currency]


def _parse_decimal_str(value: object, what: str) -> Fraction:
    """Parse a plain, non-negative decimal string exactly. Floats are refused."""
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError(f"{what} must be finite")
        return Fraction(value)
    if not isinstance(value, str) or not _DECIMAL_RE.match(value):
        raise ValueError(f"{what} must be a plain decimal string, got {value!r}")
    return Fraction(Decimal(value))


def _parse_fee_bps(value: object) -> Fraction:
    if _is_int(value):
        bps = Fraction(value)
    else:
        bps = _parse_decimal_str(value, "fee_bps")
    if bps < 0 or bps > 10000:
        raise ValueError(f"fee_bps out of range: {value!r}")
    return bps


def _round_half_even(x: Fraction) -> int:
    """Round an exact rational to the nearest integer, ties to even."""
    floor = x.numerator // x.denominator
    remainder = x - floor
    half = Fraction(1, 2)
    if remainder > half:
        return floor + 1
    if remainder < half:
        return floor
    return floor if floor % 2 == 0 else floor + 1


# --------------------------------------------------------------------------
# Quote handling
# --------------------------------------------------------------------------

def _parse_quote(quote: object, local: str, what: str) -> tuple[str, Fraction, Fraction]:
    """Return (base, bid, ask) after validating the quote against the local currency."""
    if not isinstance(quote, dict):
        raise ValueError(f"{what} must be a dict")
    pair = quote.get("pair")
    if not isinstance(pair, str):
        raise ValueError(f"{what}.pair must be a string")
    m = _PAIR_RE.match(pair)
    if not m:
        raise ValueError(f"{what}.pair must look like 'BASE/QUOTE', got {pair!r}")
    base, quote_ccy = m.group(1), m.group(2)
    if {base, quote_ccy} != {local, USD}:
        raise ValueError(f"{what}.pair {pair!r} must be between {local} and USD")
    bid = _parse_decimal_str(quote.get("bid"), f"{what}.bid")
    ask = _parse_decimal_str(quote.get("ask"), f"{what}.ask")
    if bid <= 0 or ask <= 0:
        raise ValueError(f"{what} bid and ask must be positive")
    if bid > ask:
        raise ValueError(f"{what} is crossed (bid > ask)")
    return base, bid, ask


def _usd_per_local_selling_local(quote: dict, local: str, what: str) -> Fraction:
    """Rate we receive, in USD per 1 local unit, when we sell local for USD."""
    base, bid, ask = _parse_quote(quote, local, what)
    if base == local:
        # LOCAL/USD: we sell BASE, so the dealer buys it at its bid.
        return bid
    # USD/LOCAL: we buy BASE (USD), so the dealer sells it at its ask.
    return 1 / ask


def _usd_per_local_buying_local(quote: dict, local: str, what: str) -> Fraction:
    """Rate we pay, in USD per 1 local unit, when we buy local with USD."""
    base, bid, ask = _parse_quote(quote, local, what)
    if base == local:
        # LOCAL/USD: we buy BASE, so the dealer sells it at its ask.
        return ask
    # USD/LOCAL: we sell BASE (USD), so the dealer buys it at its bid.
    return 1 / bid


def _local_minor_to_usd_cents(local_minor: int, local_exp: int, usd_per_local: Fraction) -> int:
    usd_exp = MINOR_UNITS[USD]
    exact_cents = (
        Fraction(local_minor, 10 ** local_exp) * usd_per_local * (10 ** usd_exp)
    )
    return _round_half_even(exact_cents)


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def post_refund(
    payment: dict,
    prior_refunds_minor: list[int],
    refund_minor: int,
    quote: dict,
) -> list[dict]:
    # ---- validate inputs -------------------------------------------------
    if not isinstance(payment, dict):
        raise ValueError("payment must be a dict")
    local = payment.get("currency")
    local_exp = _exponent(local)
    if local == USD:
        raise ValueError("payment currency must not be USD")

    total = payment.get("amount_minor")
    if not _is_int(total) or total <= 0:
        raise ValueError("payment.amount_minor must be a positive int")

    fee_bps = _parse_fee_bps(payment.get("fee_bps"))

    if not _is_int(refund_minor) or refund_minor <= 0:
        raise ValueError("refund_minor must be a positive int")

    if not isinstance(prior_refunds_minor, (list, tuple)):
        raise ValueError("prior_refunds_minor must be a list of ints")
    for prior in prior_refunds_minor:
        if not _is_int(prior) or prior <= 0:
            raise ValueError("each prior refund must be a positive int")

    c0 = sum(prior_refunds_minor)
    c1 = c0 + refund_minor
    if c0 > total or c1 > total:
        raise ValueError("cumulative refunds would exceed the captured amount")

    # ---- 1. USD proceeds at capture -------------------------------------
    capture_rate = _usd_per_local_selling_local(
        payment.get("capture_quote"), local, "capture_quote"
    )
    proceeds = _local_minor_to_usd_cents(total, local_exp, capture_rate)

    # ---- 2. fee and merchant net ----------------------------------------
    fee = _round_half_even(Fraction(proceeds) * fee_bps / 10000)
    net = proceeds - fee

    # ---- 3. cumulative pro-rata clawback --------------------------------
    def merchant_cum(c: int) -> int:
        return _round_half_even(Fraction(net * c, total))

    def fee_cum(c: int) -> int:
        return _round_half_even(Fraction(fee * c, total))

    d_merchant = merchant_cum(c1) - merchant_cum(c0)
    d_fee = fee_cum(c1) - fee_cum(c0)

    # ---- 4. cost to buy the local currency today ------------------------
    refund_rate = _usd_per_local_buying_local(quote, local, "quote")
    cost = _local_minor_to_usd_cents(refund_minor, local_exp, refund_rate)

    # ---- journal --------------------------------------------------------
    fx = cost - d_merchant - d_fee  # positive (debit) is a loss

    candidates = [
        ("merchant_payable", USD, d_merchant),
        ("fee_revenue", USD, d_fee),
        ("cash", USD, -cost),
        ("fx_gain_loss", USD, fx),
        ("fx_position", local, refund_minor),
        ("customer_refunds", local, -refund_minor),
    ]
    lines = [
        {"account": account, "currency": currency, "amount_minor": amount}
        for account, currency, amount in candidates
        if amount != 0
    ]

    # Each currency must net to zero.
    for ccy in {line["currency"] for line in lines}:
        if sum(l["amount_minor"] for l in lines if l["currency"] == ccy) != 0:
            raise AssertionError(f"journal does not balance in {ccy}")

    return lines
```
