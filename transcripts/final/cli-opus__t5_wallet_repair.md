# cli-opus / t5_wallet_repair / trial 1

- Requested: `opus`, resolved: `claude-haiku-5-5,claude-opus-5-5`, provider: claude-cli
- Run at 2026-10-31T15:29:16+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t5_wallet_repair/prompt.md`.

## Model output

```python
"""Card-style wallet: holds, partial captures, refunds and fees.

Incident fixes:
- Final capture now releases the uncaptured remainder of the hold.
- Captures are keyed only by capture_id, so several partial captures work on
  one hold. Replays are checked first and return the original record.
- sweep_expired no longer expires a hold at exactly expires_at, and it releases
  only the uncaptured remainder.
- Fees use exact integer ROUND_HALF_EVEN rounding, not float half-up.
- The refund limit is checked against the cumulative refunded amount.
- fee_back is derived from cumulative totals, tracked in the capture's new
  "fee_refunded" key, so rounding cannot drift across partial refunds.

Behaviour added beyond the written spec:
- deposit, place_hold, capture and refund raise WalletError unless the amount
  is a positive int. Negative amounts would bypass the hold and refund limits,
  and a zero capture would charge the minimum fee on nothing. Idempotent
  replays are checked before this validation.
"""


class WalletError(Exception):
    pass


MIN_FEE = 30
FEE_BPS = 250


def _div_round_half_even(numerator, denominator):
    """Divide non-negative numerator by positive denominator, half to even."""
    quotient, remainder = divmod(numerator, denominator)
    twice_remainder = remainder * 2
    if twice_remainder > denominator or (
        twice_remainder == denominator and quotient % 2 == 1
    ):
        quotient += 1
    return quotient


def _check_amount(amount):
    if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
        raise WalletError("amount must be a positive integer")


def fee_for(amount):
    return max(MIN_FEE, _div_round_half_even(amount * FEE_BPS, 10000))


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
        _check_amount(amount)
        self.ledger[account] = self.ledger.get(account, 0) + amount

    def available(self, account):
        return self.ledger.get(account, 0) - self.held.get(account, 0)

    def place_hold(self, hold_id, account, amount, expires_at):
        if hold_id in self.holds:
            return self.holds[hold_id]
        _check_amount(amount)
        if self.available(account) < amount:
            raise WalletError("insufficient funds")
        hold = {"account": account, "amount": amount, "captured": 0, "status": "OPEN", "expires_at": expires_at}
        self.holds[hold_id] = hold
        self.held[account] = self.held.get(account, 0) + amount
        return hold

    def _release_rest(self, hold):
        self.held[hold["account"]] -= hold["amount"] - hold["captured"]

    def capture(self, capture_id, hold_id, amount, now, final=False):
        if capture_id in self.captures:
            return self.captures[capture_id]
        _check_amount(amount)
        hold = self.holds[hold_id]
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
        _check_amount(amount)
        capture = self.captures[capture_id]
        total_refunded = capture["refunded"] + amount
        if total_refunded > capture["amount"]:
            raise WalletError("over refund")
        total_fee_back = _div_round_half_even(
            capture["fee"] * total_refunded, capture["amount"]
        )
        fee_back = total_fee_back - capture["fee_refunded"]
        capture["refunded"] = total_refunded
        capture["fee_refunded"] = total_fee_back
        account = self.holds[capture["hold_id"]]["account"]
        self.ledger[account] += amount
        self.merchant -= amount - fee_back
        self.revenue -= fee_back
        record = {"refund_id": refund_id, "capture_id": capture_id, "amount": amount, "fee_back": fee_back}
        self.refunds[refund_id] = record
        return record
```
