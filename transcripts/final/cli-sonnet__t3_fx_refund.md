# cli-sonnet / t3_fx_refund / trial 1

- Requested: `sonnet`, resolved: `claude-haiku-5-5,claude-sonnet-5-5`, provider: claude-cli
- Run at 2026-10-31T20:36:10+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t3_fx_refund/prompt.md`.

## Model output

```python
"""Cross-currency refund journal.

Standard library only. All arithmetic is exact (fractions.Fraction); the only
rounding is to whole minor units with ROUND_HALF_EVEN (Python's round() on a
Fraction returns an int and rounds exact halves to the even neighbour).
"""

from decimal import Decimal, InvalidOperation
from fractions import Fraction

# ISO 4217 minor-unit exponents.
_EXP0 = frozenset(
    "BIF CLP DJF GNF ISK JPY KMF KRW PYG RWF UGX UYI VND VUV XAF XOF XPF".split()
)
_EXP3 = frozenset("BHD IQD JOD KWD LYD OMR TND".split())
_EXP4 = frozenset("CLF UYW".split())
_EXP2 = frozenset(
    """AED AFN ALL AMD ANG AOA ARS AUD AWG AZN BAM BBD BDT BGN BMD BND BOB BOV
    BRL BSD BTN BWP BYN BZD CAD CDF CHE CHF CHW CNY COP COU CRC CUP CVE CZK
    DKK DOP DZD EGP ERN ETB EUR FJD FKP GBP GEL GHS GIP GMD GTQ GYD HKD HNL
    HTG HUF IDR ILS INR IRR JMD KES KGS KHR KPW KYD KZT LAK LBP LKR LRD LSL
    MAD MDL MGA MKD MMK MNT MOP MRU MUR MVR MWK MXN MXV MYR MZN NAD NGN NIO
    NOK NPR NZD PAB PEN PGK PHP PKR PLN QAR RON RSD RUB SAR SBD SCR SDG SEK
    SGD SHP SLE SOS SRD SSP STN SVC SYP SZL THB TJS TMT TOP TRY TTD TWD TZS
    UAH USD USN UYU UZS VED VES WST XCD YER ZAR ZMW ZWG""".split()
)


def _exponent(ccy: str) -> int:
    if ccy in _EXP0:
        return 0
    if ccy in _EXP2:
        return 2
    if ccy in _EXP3:
        return 3
    if ccy in _EXP4:
        return 4
    raise ValueError(f"unsupported or unknown currency: {ccy!r}")


def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _parse_rate(value, name: str) -> Fraction:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a decimal string")
    try:
        d = Decimal(value)
    except InvalidOperation:
        raise ValueError(f"{name} is not a valid decimal: {value!r}")
    if not d.is_finite() or d <= 0:
        raise ValueError(f"{name} must be a finite positive number")
    return Fraction(d)  # exact


def _parse_quote(quote: dict, ccy: str):
    """Return (local_is_base, bid, ask) after validating the quote."""
    try:
        pair = quote["pair"]
        bid = _parse_rate(quote["bid"], "bid")
        ask = _parse_rate(quote["ask"], "ask")
    except (KeyError, TypeError):
        raise ValueError("quote must contain pair, bid and ask")
    if not isinstance(pair, str):
        raise ValueError("quote pair must be a string")
    parts = pair.split("/")
    if len(parts) != 2:
        raise ValueError(f"malformed pair: {pair!r}")
    base, term = parts
    if base == "USD" and term == ccy:
        local_is_base = False
    elif term == "USD" and base == ccy:
        local_is_base = True
    else:
        raise ValueError(f"pair {pair!r} does not match USD and {ccy}")
    if bid > ask:
        raise ValueError("crossed quote: bid > ask")
    return local_is_base, bid, ask


def _usd_cents(minor: int, exp: int, quote: dict, ccy: str, selling_local: bool) -> int:
    """USD cents for trading `minor` local minor units against the dealer.

    We are the dealer's customer, so:
      * the dealer buys BASE at bid and sells BASE at ask.
      * selling local with local=BASE -> hit bid; local=USD-quoted -> we buy USD
        (the base) at ask, so USD = local / ask.
      * buying local with local=BASE -> pay ask; otherwise we sell USD (base)
        at bid, so USD = local / bid.
    """
    local_is_base, bid, ask = _parse_quote(quote, ccy)
    major = Fraction(minor, 10 ** exp)
    if local_is_base:
        rate = bid if selling_local else ask
        usd = major * rate
    else:
        rate = ask if selling_local else bid
        usd = major / rate
    return round(usd * 100)


def post_refund(
    payment: dict, prior_refunds_minor: list[int], refund_minor: int, quote: dict
) -> list[dict]:
    if not _is_int(refund_minor) or refund_minor <= 0:
        raise ValueError("refund_minor must be a positive integer")

    try:
        ccy = payment["currency"]
        T = payment["amount_minor"]
        capture_quote = payment["capture_quote"]
        fee_bps = payment["fee_bps"]
    except (KeyError, TypeError):
        raise ValueError("payment is missing required fields")

    if not isinstance(ccy, str) or ccy == "USD":
        raise ValueError("payment currency must be a non-USD ISO 4217 code")
    if not _is_int(T) or T <= 0:
        raise ValueError("amount_minor must be a positive integer")
    if not _is_int(fee_bps) or not (0 <= fee_bps <= 10000):
        raise ValueError("fee_bps must be an integer between 0 and 10000")
    exp = _exponent(ccy)

    for r in prior_refunds_minor:
        if not _is_int(r) or r < 0:
            raise ValueError("prior refunds must be non-negative integers")
    c0 = sum(prior_refunds_minor)
    c1 = c0 + refund_minor
    if c1 > T:
        raise ValueError("cumulative refund exceeds captured amount")

    # 1-2. Proceeds, fee, merchant net (USD cents).
    P = _usd_cents(T, exp, capture_quote, ccy, selling_local=True)
    F = round(Fraction(P * fee_bps, 10000))
    N = P - F

    # 3. Cumulative clawback / fee return, then this refund's increments.
    def M(c: int) -> int:
        return round(Fraction(N * c, T))

    def G(c: int) -> int:
        return round(Fraction(F * c, T))

    dM = M(c1) - M(c0)
    dG = G(c1) - G(c0)

    # 4. Cost to buy the refunded local amount today.
    K = _usd_cents(refund_minor, exp, quote, ccy, selling_local=False)

    # USD lines must sum to zero: dM + dG - K + fx = 0 (debit positive = loss).
    fx = K - dM - dG

    lines = [
        {"account": "merchant_payable", "currency": "USD", "amount_minor": dM},
        {"account": "fee_revenue", "currency": "USD", "amount_minor": dG},
        {"account": "cash", "currency": "USD", "amount_minor": -K},
        {"account": "fx_gain_loss", "currency": "USD", "amount_minor": fx},
        {"account": "fx_position", "currency": ccy, "amount_minor": refund_minor},
        {"account": "customer_refunds", "currency": ccy, "amount_minor": -refund_minor},
    ]
    return [line for line in lines if line["amount_minor"] != 0]
```
