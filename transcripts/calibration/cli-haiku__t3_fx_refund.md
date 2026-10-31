# cli-haiku / t3_fx_refund / trial 1

- Requested: `haiku`, resolved: `claude-haiku-5-5`, provider: claude-cli
- Run at 2026-10-31T14:44:26+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t3_fx_refund/prompt.md`.

## Model output

```python
from fractions import Fraction

# ISO 4217 minor-unit exponents. Only currencies listed here are accepted;
# anything else raises ValueError so an unknown exponent can't silently skew amounts.
_EXP0 = frozenset({
    "BIF", "CLP", "DJF", "GNF", "ISK", "JPY", "KMF", "KRW",
    "PYG", "RWF", "UGX", "VND", "VUV", "XAF", "XOF", "XPF",
})
_EXP2 = frozenset({
    "AED", "ARS", "AUD", "BRL", "CAD", "CHF", "CNY", "COP", "CZK", "DKK",
    "EGP", "EUR", "GBP", "HKD", "HUF", "IDR", "ILS", "INR", "KES", "MXN",
    "MYR", "NGN", "NOK", "NZD", "PEN", "PHP", "PLN", "RON", "RUB", "SAR",
    "SEK", "SGD", "THB", "TRY", "TWD", "ZAR",
})
_EXP3 = frozenset({"BHD", "IQD", "JOD", "KWD", "LYD", "OMR", "TND"})
_EXP4 = frozenset({"CLF", "UYW"})


def _minor_exponent(code: str) -> int:
    if code in _EXP0:
        return 0
    if code in _EXP2:
        return 2
    if code in _EXP3:
        return 3
    if code in _EXP4:
        return 4
    raise ValueError(f"unsupported currency {code!r}: add it to the ISO 4217 table")


def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _exact(s, name: str) -> Fraction:
    """Parse a decimal string exactly. Floats are rejected by type."""
    if not isinstance(s, str):
        raise TypeError(f"{name} must be a decimal string, not {type(s).__name__}")
    try:
        return Fraction(s)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"{name} is not a valid decimal: {s!r}") from exc


def _round_half_even(x: Fraction) -> int:
    # round() on a Fraction with no ndigits is exact and uses half-to-even.
    return round(x)


def _usd_per_local(quote: dict, local: str) -> tuple[Fraction, Fraction]:
    """
    Return (sell, buy): the USD value of one major unit of the local currency
    when we SELL local (dealer's bid side) and when we BUY local (dealer's ask side).

    Pair convention: 1 BASE = rate QUOTE.
      - local is BASE  (e.g. EUR/USD): 1 local = rate USD.
          sell local -> dealer buys local at its bid
          buy local  -> dealer sells local at its ask
      - local is QUOTE (e.g. USD/JPY): 1 USD = rate local.
          sell local -> dealer sells USD at its ask, so 1 local = 1/ask USD
          buy local  -> dealer buys USD at its bid, so 1 local = 1/bid USD
    """
    pair = quote["pair"]
    if not isinstance(pair, str):
        raise ValueError("quote pair must be a string")
    base, sep, qte = pair.partition("/")
    if sep != "/" or not base or not qte:
        raise ValueError(f"malformed pair {pair!r}")
    if base == qte:
        raise ValueError(f"pair {pair!r} has identical sides")
    if "USD" not in (base, qte):
        raise ValueError(f"pair {pair!r} must include USD")
    if local not in (base, qte):
        raise ValueError(f"pair {pair!r} does not include local currency {local!r}")

    bid = _exact(quote["bid"], "bid")
    ask = _exact(quote["ask"], "ask")
    if bid <= 0 or ask <= 0:
        raise ValueError("bid and ask must be positive")
    if bid > ask:
        raise ValueError("bid must not exceed ask")

    if base == local:
        return bid, ask
    return 1 / ask, 1 / bid


def post_refund(payment: dict, prior_refunds_minor: list[int], refund_minor: int, quote: dict) -> list[dict]:
    local = payment["currency"]
    if not isinstance(local, str) or local == "USD":
        raise ValueError("payment currency must be a non-USD ISO 4217 code")
    exp = _minor_exponent(local)

    T = payment["amount_minor"]
    if not _is_int(T) or T <= 0:
        raise ValueError("amount_minor must be a positive int")

    fee_bps = payment["fee_bps"]
    if not _is_int(fee_bps) or not (0 <= fee_bps <= 10000):
        raise ValueError("fee_bps must be an int in [0, 10000]")

    if not _is_int(refund_minor) or refund_minor <= 0:
        raise ValueError("refund_minor must be a positive int")

    prior = list(prior_refunds_minor)
    for r in prior:
        if not _is_int(r) or r <= 0:
            raise ValueError("prior refunds must be positive ints")

    c0 = sum(prior)
    c1 = c0 + refund_minor
    if c1 > T:
        raise ValueError("cumulative refund would exceed amount_minor")

    # Capture: we SOLD local to the dealer, so use the capture quote's sell rate.
    capture_sell, _ = _usd_per_local(payment["capture_quote"], local)
    # Refund: we BUY local from the dealer, so use today's buy rate.
    _, refund_buy = _usd_per_local(quote, local)

    # 1. USD proceeds P, in cents.
    capture_major = Fraction(T, 10 ** exp)
    P = _round_half_even(capture_major * capture_sell * 100)

    # 2. Fee F and merchant net N, in cents.
    F = _round_half_even(Fraction(P * fee_bps, 10000))
    N = P - F

    # 3. Cumulative clawback and fee return; this refund's deltas.
    def M(c: int) -> int:
        return _round_half_even(Fraction(N * c, T))

    def G(c: int) -> int:
        return _round_half_even(Fraction(F * c, T))

    dM = M(c1) - M(c0)
    dG = G(c1) - G(c0)

    # 4. Cost K to buy exactly refund_minor of local currency, in cents.
    refund_major = Fraction(refund_minor, 10 ** exp)
    K = _round_half_even(refund_major * refund_buy * 100)

    # FX line balances the USD side: dM + dG - K + fx = 0.
    fx = K - dM - dG

    lines: list[dict] = []

    def add(account: str, currency: str, amount: int) -> None:
        if amount != 0:
            lines.append({"account": account, "currency": currency, "amount_minor": amount})

    add("merchant_payable", "USD", dM)
    add("fee_revenue", "USD", dG)
    add("cash", "USD", -K)
    add("fx_gain_loss", "USD", fx)
    add("fx_position", local, refund_minor)
    add("customer_refunds", local, -refund_minor)

    return lines
```
