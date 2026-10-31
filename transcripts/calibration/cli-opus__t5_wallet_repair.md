# cli-opus / t5_wallet_repair / trial 1

- Requested: `opus`, resolved: `claude-haiku-5-5,claude-opus-5-5`, provider: claude-cli
- Run at 2026-10-31T14:40:36+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t5_wallet_repair/prompt.md`.

## Model output

```python
"""Card-style wallet: holds, partial captures, refunds and fees.

Audit fixes:
- Fees and fee returns use exact integer ROUND_HALF_EVEN arithmetic, not floats.
- Captures are keyed only by capture_id, so a hold can have several partial
  captures. Replays are checked first and work after a hold has closed.
- A final capture releases the uncaptured remainder of the hold.
- sweep_expired keeps holds valid at expires_at and releases only the
  uncaptured remainder.
- Refund limits apply to the cumulative refunded total.
- fee_back is calculated from the cumulative total, so partial refunds do not
  accumulate rounding drift. Capture records track this in "fee_refunded".

Additional hardening (not specified in the ticket):
- Non-integer amounts are rejected, as are negative deposits and zero or
  negative hold, capture and refund amounts, because they could create money
  or corrupt totals. Use void, not a zero final capture, to release a hold.
"""


class WalletError(Exception):
    pass


MIN_FEE = 30
FEE_BPS = 250
BPS_DENOMINATOR = 10000


def _div_half_even(numerator, denominator):
    """Return numerator / denominator rounded ROUND_HALF_EVEN, using exact integers."""
    quotient, remainder = divmod(numerator, denominator)
    doubled_remainder = remainder * 2
    if doubled_remainder > denominator or (
        doubled_remainder == denominator and quotient % 2 == 1
    ):
        quotient += 1
    return quotient


def _require_amount(amount, minimum=1):
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise WalletError("amount must be an integer")
    if amount < minimum:
        raise WalletError("invalid amount")


def fee_for(amount):
    return max(MIN_FEE, _div_half_even(amount * FEE_BPS, BPS_DENOMINATOR))


class Wallet:
    def __init__(self):
        self.ledger = {}
        self.held = {}
        self.holds = {}
        self.captures = {}
        self.refunds = {}
        self.merchant = 0
        self.revenue = 0

    def deposit(self, account, amount):
        _require_amount(amount, minimum=0)
        self.ledger[account] = self.ledger.get(account, 0) + amount

    def available(self, account):
        return self.ledger.get(account, 0) - self.held.get(account, 0)

    def place_hold(self, hold_id, account, amount, expires_at):
        if hold_id in self.holds:
            return self.holds[hold_id]
        _require_amount(amount)
        if self.available(account) < amount:
            raise WalletError("insufficient funds")
        hold = {
            "account": account,
            "amount": amount,
            "captured": 0,
            "status": "OPEN",
            "expires_at": expires_at,
        }
        self.holds[hold_id] = hold
        self.held[account] = self.held.get(account, 0) + amount
        return hold

    def _release_rest(self, hold):
        self.held[hold["account"]] -= hold["amount"] - hold["captured"]

    def capture(self, capture_id, hold_id, amount, now, final=False):
        if capture_id in self.captures:
            return self.captures[capture_id]
        hold = self.holds[hold_id]
        _require_amount(amount)
        if hold["status"] != "OPEN":
            raise WalletError("hold not open")
        if now > hold["expires_at"]:
            raise WalletError("hold expired")
        if hold["captured"] + amount > hold["amount"]:
            raise WalletError("over capture")
        fee = fee_for(amount)
        hold["captured"] += amount
        self.held[hold["account"]] -= amount
        self.ledger[hold["account"]] -= amount
        self.merchant += amount - fee
        self.revenue += fee
        record = {
            "capture_id": capture_id,
            "hold_id": hold_id,
            "amount": amount,
            "fee": fee,
            "refunded": 0,
            "fee_refunded": 0,
        }
        self.captures[capture_id] = record
        if final:
            self._release_rest(hold)
            hold["status"] = "CLOSED"
        return record

    def void(self, hold_id):
        hold = self.holds[hold_id]
        if hold["status"] != "OPEN":
            return hold
        self._release_rest(hold)
        hold["status"] = "VOIDED"
        return hold

    def sweep_expired(self, now):
        expired = []
        for hold_id, hold in self.holds.items():
            if hold["status"] == "OPEN" and now > hold["expires_at"]:
                self._release_rest(hold)
                hold["status"] = "EXPIRED"
                expired.append(hold_id)
        return expired

    def refund(self, refund_id, capture_id, amount):
        if refund_id in self.refunds:
            return self.refunds[refund_id]
        capture = self.captures[capture_id]
        _require_amount(amount)
        total_refunded = capture["refunded"] + amount
        if total_refunded > capture["amount"]:
            raise WalletError("over refund")
        total_fee_back = _div_half_even(capture["fee"] * total_refunded, capture["amount"])
        fee_back = total_fee_back - capture["fee_refunded"]
        account = self.holds[capture["hold_id"]]["account"]
        capture["refunded"] = total_refunded
        capture["fee_refunded"] = total_fee_back
        self.ledger[account] += amount
        self.merchant -= amount - fee_back
        self.revenue -= fee_back
        record = {
            "refund_id": refund_id,
            "capture_id": capture_id,
            "amount": amount,
            "fee_back": fee_back,
        }
        self.refunds[refund_id] = record
        return record
```
