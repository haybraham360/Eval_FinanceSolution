# Ticket: cross-currency refund journal

Merchants settle with us in USD. Customers pay in local currency. At capture we sold the customer's local currency for USD and credited the merchant. A refund pays the customer back the local amount, so we must buy that local currency at today's price. The merchant carries no FX risk, so whatever the rate did between capture and refund lands in our FX gain/loss account.

Implement in one Python 3.10+ module, standard library only:

```python
def post_refund(payment: dict, prior_refunds_minor: list[int], refund_minor: int, quote: dict) -> list[dict]: ...
```

## Inputs

`payment` has:

- `currency`: ISO 4217 code of the local currency. Never USD.
- `amount_minor`: captured amount in that currency's ISO 4217 minor units, for example 1500 JPY is `1500`, 12.500 KWD is `12500`.
- `capture_quote`: the dealer quote at capture.
- `fee_bps`: our fee in basis points of the USD proceeds.

`prior_refunds_minor` holds the local-currency amounts of earlier refunds, oldest first. `refund_minor` is this refund, in local minor units. `quote` is the dealer quote today.

A quote is `{"pair": "BASE/QUOTE", "bid": "<decimal string>", "ask": "<decimal string>"}`, using the market's normal convention: 1 unit of BASE is worth that many units of QUOTE. It is a dealer's two-way price and we are the dealer's customer, so we always trade on the side that the dealer quotes to its customers. One side of every pair is USD, and either side can be the local currency, for example `EUR/USD` or `USD/JPY`.

## Calculation

All amounts are exact until rounded. Every rounding below is to whole USD cents (or the stated currency's minor unit), ROUND_HALF_EVEN. Floats are not acceptable anywhere: amounts can exceed 15 significant digits.

1. **USD proceeds** `P`: what we received for selling the full `amount_minor` at `capture_quote`, rounded to cents.
2. **Fee** `F`: `P * fee_bps / 10000`, rounded to cents. **Merchant net** `N = P - F`.
3. Let `T = amount_minor` and let `c0` and `c1` be the cumulative local amount refunded before and after this refund. Cumulative merchant clawback at any point is `M(c) = N * c / T` rounded to cents, and cumulative fee returned is `G(c) = F * c / T` rounded to cents. This refund's amounts are `dM = M(c1) - M(c0)` and `dG = G(c1) - G(c0)`.
4. **Cost** `K`: the USD we pay to buy exactly `refund_minor` of local currency at `quote`, rounded to cents.

## Output

Return a list of journal lines `{"account": str, "currency": str, "amount_minor": int}`, where debits are positive and credits negative. `amount_minor` is in that line's own currency's minor units. Omit any line whose amount is 0. Use one line per account and currency.

| account | currency | amount |
|---|---|---|
| `merchant_payable` | USD | `+dM` |
| `fee_revenue` | USD | `+dG` |
| `cash` | USD | `-K` |
| `fx_gain_loss` | USD | whatever makes the USD lines sum to 0 (a debit is a loss) |
| `fx_position` | local | `+refund_minor` |
| `customer_refunds` | local | `-refund_minor` |

Raise `ValueError` if `refund_minor <= 0` or if the cumulative refund would exceed `amount_minor`.

Return the complete module in one ```python block.
