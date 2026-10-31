# cli-opus / t3_fx_refund / trial 1

- Requested: `opus`, resolved: `claude-haiku-5-5,claude-opus-5-5`, provider: claude-cli
- Run at 2026-10-31T15:27:00+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t3_fx_refund/prompt.md`.

## Model output

```python
"""Cross-currency refund journal.

All intermediate values are exact ``Fraction`` objects. Rounding happens only
in ``_round_half_even``. ``Fraction`` is used instead of ``Decimal`` because
inverting a USD/LOCAL rate has no exact decimal representation.
"""

from decimal import Decimal, InvalidOperation
from fractions import Fraction

USD = "USD"
USD_CENTS_PER_UNIT = 100

# The standard library has no ISO 4217 data. Unknown codes are rejected rather
# than assumed to have two decimals, which could misstate an amount by orders
# of magnitude. Non-monetary codes such as XAU and XDR have no minor unit and
# are deliberately absent.
_CODES_BY_MINOR_EXPONENT = {
    0: "BIF CLP DJF GNF ISK JPY KMF KRW PYG RWF UGX UYI VND VUV XAF XOF XPF",
    2: (
        "AED AFN ALL AMD AOA ARS AUD AWG AZN BAM BBD BDT BMD BND BOB BOV BRL "
        "BSD BTN BWP BYN BZD CAD CDF CHE CHF CHW CNY COP COU CRC CUP CVE CZK "
        "DKK DOP DZD EGP ERN ETB EUR FJD FKP GBP GEL GHS GIP GMD GTQ GYD HKD "
        "HNL HTG HUF IDR ILS INR IRR JMD KES KGS KHR KPW KYD KZT LAK LBP LKR "
        "LRD LSL MAD MDL MGA MKD MMK MNT MOP MRU MUR MVR MWK MXN MXV MYR MZN "
        "NAD NGN NIO NOK NPR NZD PAB PEN PGK PHP PKR PLN QAR RON RSD RUB SAR "
        "SBD SCR SDG SEK SGD SHP SLE SOS SRD SSP STN SVC SYP SZL THB TJS TMT "
        "TOP TRY TTD TWD TZS UAH USN UZS VED VES WST XCD XCG YER ZAR ZMW ZWG "
        # Withdrawn codes, retained so that older captures remain refundable.
        "ANG BGN CUC HRK SLL ZWL"
    ),
    3: "BHD IQD JOD KWD LYD OMR TND",
    4: "CLF UYW",
}

_MINOR_EXPONENTS = {
    code: exponent
    for exponent, codes in _CODES_BY_MINOR_EXPONENT.items()
    for code in codes.split()
}


def _round_half_even(value: Fraction) -> int:
    """Round to an integer, resolving ties to even."""
    return round(value)


def _require_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be an integer")
    return value


def _minor_units_per_major(currency: str) -> int:
    if currency == USD:
        raise ValueError("payment currency must not be USD")
    try:
        return 10 ** _MINOR_EXPONENTS[currency]
    except KeyError:
        raise ValueError(f"unsupported currency: {currency!r}") from None


def _parse_decimal(value: object, label: str) -> Decimal:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{label} is not a valid decimal: {value!r}") from exc
    if not parsed.is_finite():
        raise ValueError(f"{label} must be finite")
    return parsed


def _parse_rate(value: object, label: str) -> Fraction:
    parsed = _parse_decimal(value, label)
    if parsed <= 0:
        raise ValueError(f"{label} must be positive")
    return Fraction(parsed)


def _parse_fee_bps(value: object) -> Fraction:
    if isinstance(value, bool) or isinstance(value, float):
        raise ValueError("fee_bps must not be a bool or float")
    if isinstance(value, str):
        fee_bps = Fraction(_parse_decimal(value, "fee_bps"))
    elif isinstance(value, (int, Decimal, Fraction)):
        if isinstance(value, Decimal) and not value.is_finite():
            raise ValueError("fee_bps must be finite")
        fee_bps = Fraction(value)
    else:
        raise ValueError("fee_bps must be an exact number")
    if not 0 <= fee_bps <= 10000:
        raise ValueError("fee_bps must be between 0 and 10000")
    return fee_bps


def _usd_per_local(quote: dict, local: str) -> tuple[Fraction, Fraction]:
    """Return ``(rate when we sell local, rate when we buy local)``.

    The dealer buys BASE from us at the bid and sells BASE to us at the ask.

    LOCAL/USD: selling local sells BASE (bid); buying local buys BASE (ask).
    USD/LOCAL: selling local buys USD, the BASE (1 / ask); buying local sells
    USD, the BASE (1 / bid).
    """
    bid = _parse_rate(quote["bid"], "bid")
    ask = _parse_rate(quote["ask"], "ask")
    if bid > ask:
        raise ValueError("quote is crossed: bid exceeds ask")

    parts = quote["pair"].split("/")
    if len(parts) != 2:
        raise ValueError(f"malformed pair: {quote['pair']!r}")
    base, counter = parts

    if base == local and counter == USD:
        return bid, ask
    if base == USD and counter == local:
        return 1 / ask, 1 / bid
    raise ValueError(f"pair {quote['pair']!r} does not match USD and {local}")


def _usd_cents(
    local_minor: int, minor_per_major: int, usd_per_local: Fraction
) -> int:
    local_major = Fraction(local_minor, minor_per_major)
    return _round_half_even(local_major * usd_per_local * USD_CENTS_PER_UNIT)


def _cumulative_share(total: int, refunded: int, captured: int) -> int:
    return _round_half_even(Fraction(total * refunded, captured))


def post_refund(
    payment: dict,
    prior_refunds_minor: list[int],
    refund_minor: int,
    quote: dict,
) -> list[dict]:
    """Build the journal lines for one refund. Debits are positive."""
    _require_int(refund_minor, "refund_minor")
    if refund_minor <= 0:
        raise ValueError("refund_minor must be positive")

    captured = _require_int(payment["amount_minor"], "amount_minor")

    refunded_before = 0
    for prior in prior_refunds_minor:
        _require_int(prior, "prior refund")
        if prior < 0:
            raise ValueError("prior refunds must not be negative")
        refunded_before += prior

    refunded_after = refunded_before + refund_minor
    if refunded_after > captured:
        raise ValueError("cumulative refunds would exceed the captured amount")

    local = payment["currency"]
    minor_per_major = _minor_units_per_major(local)
    fee_bps = _parse_fee_bps(payment["fee_bps"])

    capture_sell_rate, _ = _usd_per_local(payment["capture_quote"], local)
    _, refund_buy_rate = _usd_per_local(quote, local)

    proceeds = _usd_cents(captured, minor_per_major, capture_sell_rate)
    fee = _round_half_even(proceeds * fee_bps / 10000)
    merchant_net = proceeds - fee

    merchant_clawback = _cumulative_share(
        merchant_net, refunded_after, captured
    ) - _cumulative_share(merchant_net, refunded_before, captured)
    fee_returned = _cumulative_share(
        fee, refunded_after, captured
    ) - _cumulative_share(fee, refunded_before, captured)

    cost = _usd_cents(refund_minor, minor_per_major, refund_buy_rate)
    fx_gain_loss = cost - merchant_clawback - fee_returned

    lines = [
        ("merchant_payable", USD, merchant_clawback),
        ("fee_revenue", USD, fee_returned),
        ("cash", USD, -cost),
        ("fx_gain_loss", USD, fx_gain_loss),
        ("fx_position", local, refund_minor),
        ("customer_refunds", local, -refund_minor),
    ]
    return [
        {"account": account, "currency": currency, "amount_minor": amount}
        for account, currency, amount in lines
        if amount != 0
    ]
```
