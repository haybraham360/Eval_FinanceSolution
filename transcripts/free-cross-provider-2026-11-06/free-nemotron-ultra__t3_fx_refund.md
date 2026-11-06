# free-nemotron-ultra / t3_fx_refund / trial 1

- Requested: `nvidia/nemotron-3-ultra-550b-a55b:free`, resolved: `nvidia/nemotron-3-ultra-550b-a55b:free`, provider: Nvidia
- Run at 2026-11-06T20:04:23+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t3_fx_refund/prompt.md`.

## Model output

```python
from decimal import Decimal, ROUND_HALF_EVEN

# ISO 4217 minor units for common currencies.
# In a production system this would be a complete, maintained table.
CURRENCY_DECIMALS = {
    "USD": 2, "EUR": 2, "GBP": 2, "JPY": 0, "KWD": 3,
    "BHD": 3, "OMR": 3, "JOD": 3, "TND": 3, "LYD": 3,
    "IQD": 3, "CHF": 2, "CAD": 2, "AUD": 2, "NZD": 2,
    "SGD": 2, "HKD": 2, "CNY": 2, "SEK": 2, "NOK": 2,
    "DKK": 2, "PLN": 2, "CZK": 2, "HUF": 2, "RON": 2,
    "BGN": 2, "HRK": 2, "RUB": 2, "TRY": 2, "ZAR": 2,
    "MXN": 2, "BRL": 2, "INR": 2, "KRW": 0, "VND": 0,
    "IDR": 0, "CLP": 0, "COP": 2, "PEN": 2, "ARS": 2,
    "THB": 2, "MYR": 2, "PHP": 2, "TWD": 2, "ILS": 2,
}

def _decimals(ccy: str) -> int:
    """Return the number of minor units for an ISO currency code."""
    try:
        return CURRENCY_DECIMALS[ccy]
    except KeyError:
        raise ValueError(f"Unsupported currency: {ccy}")

def post_refund(payment: dict, prior_refunds_minor: list[int], refund_minor: int, quote: dict) -> list[dict]:
    """
    Generate journal lines for a cross-currency refund.

    Args:
        payment: Dict with keys 'currency', 'amount_minor', 'capture_quote', 'fee_bps'.
        prior_refunds_minor: List of earlier refund amounts in local minor units (oldest first).
        refund_minor: This refund amount in local minor units.
        quote: Current dealer quote {'pair', 'bid', 'ask'}.

    Returns:
        List of journal line dicts: {'account', 'currency', 'amount_minor'}.
        Debits are positive, credits negative. Zero lines omitted.

    Raises:
        ValueError: If refund_minor <= 0 or cumulative refund exceeds captured amount.
    """
    if refund_minor <= 0:
        raise ValueError("refund_minor must be positive")
    total_refunded = sum(prior_refunds_minor) + refund_minor
    if total_refunded > payment["amount_minor"]:
        raise ValueError("Cumulative refund exceeds captured amount")

    local_ccy = payment["currency"]
    amount_minor = payment["amount_minor"]
    capture_quote = payment["capture_quote"]
    fee_bps = payment["fee_bps"]
    local_dp = _decimals(local_ccy)

    def _local_to_usd_cents(local_amount_minor: int, q: dict, direction: str) -> int:
        """
        Convert a local-currency amount (in minor units) to USD cents using quote q.
        direction: 'sell_local' (we sell local, receive USD) or 'buy_local' (we buy local, pay USD).
        """
        pair = q["pair"]
        base, quote_ccy = pair.split("/")
        bid = Decimal(q["bid"])
        ask = Decimal(q["ask"])
        local_major = Decimal(local_amount_minor) / (Decimal(10) ** local_dp)

        if local_ccy == base:
            if direction == "sell_local":
                rate = bid          # we sell base -> receive quote at bid
                usd_major = local_major * rate
            elif direction == "buy_local":
                rate = ask          # we buy base -> pay quote at ask
                usd_major = local_major * rate
            else:
                raise ValueError("Invalid direction")
        elif local_ccy == quote_ccy:
            if direction == "sell_local":
                rate = ask          # we sell quote -> buy base at ask
                usd_major = local_major / rate
            elif direction == "buy_local":
                rate = bid          # we buy quote -> sell base at bid
                usd_major = local_major / rate
            else:
                raise ValueError("Invalid direction")
        else:
            raise ValueError(f"Local currency {local_ccy} not found in pair {pair}")

        usd_cents = (usd_major * Decimal(100)).quantize(Decimal('1'), rounding=ROUND_HALF_EVEN)
        return int(usd_cents)

    # 1. USD proceeds at capture (sell local for USD)
    P = _local_to_usd_cents(amount_minor, capture_quote, "sell_local")

    # 2. Fee and merchant net
    F = (Decimal(P) * Decimal(fee_bps) / Decimal(10000)).quantize(Decimal('1'), rounding=ROUND_HALF_EVEN)
    F = int(F)
    N = P - F

    # 3. Cumulative refund mechanics
    c0 = sum(prior_refunds_minor)
    c1 = c0 + refund_minor
    T = amount_minor

    def _rounded_share(numerator: int, c: int) -> int:
        """Return round(numerator * c / T) to nearest cent (half-even)."""
        if c == 0:
            return 0
        val = (Decimal(numerator) * Decimal(c) / Decimal(T)).quantize(Decimal('1'), rounding=ROUND_HALF_EVEN)
        return int(val)

    dM = _rounded_share(N, c1) - _rounded_share(N, c0)
    dG = _rounded_share(F, c1) - _rounded_share(F, c0)

    # 4. Cost to buy back local currency today
    K = _local_to_usd_cents(refund_minor, quote, "buy_local")

    # Build journal lines
    lines = []
    if dM != 0:
        lines.append({"account": "merchant_payable", "currency": "USD", "amount_minor": dM})
    if dG != 0:
        lines.append({"account": "fee_revenue", "currency": "USD", "amount_minor": dG})
    if K != 0:
        lines.append({"account": "cash", "currency": "USD", "amount_minor": -K})

    usd_sum = dM + dG - K
    fx_gl = -usd_sum
    if fx_gl != 0:
        lines.append({"account": "fx_gain_loss", "currency": "USD", "amount_minor": fx_gl})

    if refund_minor != 0:
        lines.append({"account": "fx_position", "currency": local_ccy, "amount_minor": refund_minor})
        lines.append({"account": "customer_refunds", "currency": local_ccy, "amount_minor": -refund_minor})

    return lines
```
