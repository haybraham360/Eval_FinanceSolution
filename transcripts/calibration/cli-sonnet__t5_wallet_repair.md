# cli-sonnet / t5_wallet_repair / trial 1

- Requested: `sonnet`, resolved: `claude-haiku-5-5,claude-sonnet-5-5`, provider: claude-cli
- Run at 2026-10-31T14:43:25+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t5_wallet_repair/prompt.md`.

## Model output

```python
class WalletError(Exception):
    pass


MIN_FEE = 30
FEE_BPS = 250


def _div_half_even(numerator, denominator):
    """Integer division of non-negative ints, rounded ROUND_HALF_EVEN."""
    q, r = divmod(numerator, denominator)
    twice = 2 * r
    if twice > denominator or (twice == denominator and q % 2 == 1):
        q += 1
    return q


def fee_for(amount):
    return max(MIN_FEE, _div_half_even(amount * FEE_BPS, 10000))


class Wallet:
    def __init__(self):
        self.ledger = {}
        self.held = {}
        self.holds = {}
        self.captures = {}   # keyed by capture_id only
        self.refunds = {}
        self.merchant = 0
        self.revenue = 0

    def deposit(self, account, amount):
        self.ledger[account] = self.ledger.get(account, 0) + amount

    def available(self, account):
        return self.ledger.get(account, 0) - self.held.get(account, 0)

    def place_hold(self, hold_id, account, amount, expires_at):
        if hold_id in self.holds:
            return self.holds[hold_id]
        if amount <= 0:
            raise WalletError("invalid amount")
        if self.available(account) < amount:
            raise WalletError("insufficient funds")
        hold = {"account": account, "amount": amount, "captured": 0, "status": "OPEN", "expires_at": expires_at}
        self.holds[hold_id] = hold
        self.held[account] = self.held.get(account, 0) + amount
        return hold

    def _release_rest(self, hold):
        # Release only what has not been captured.
        self.held[hold["account"]] -= hold["amount"] - hold["captured"]

    def capture(self, capture_id, hold_id, amount, now, final=False):
        # Replay of a capture_id returns the original record, whatever the hold's state.
        if capture_id in self.captures:
            return self.captures[capture_id]
        hold = self.holds[hold_id]
        if hold["status"] != "OPEN":
            raise WalletError("hold not open")
        if now > hold["expires_at"]:
            raise WalletError("hold expired")
        if amount <= 0:
            raise WalletError("invalid amount")
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
            "fee_returned": 0,
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
        if amount <= 0:
            raise WalletError("invalid amount")
        if capture["refunded"] + amount > capture["amount"]:
            raise WalletError("over refund")
        total_refunded = capture["refunded"] + amount
        # Cumulative fee target, so the total returned is exact after any sequence of refunds.
        target = _div_half_even(capture["fee"] * total_refunded, capture["amount"])
        fee_back = target - capture["fee_returned"]
        capture["refunded"] = total_refunded
        capture["fee_returned"] = target
        account = self.holds[capture["hold_id"]]["account"]
        self.ledger[account] = self.ledger.get(account, 0) + amount
        self.merchant -= amount - fee_back
        self.revenue -= fee_back
        record = {"refund_id": refund_id, "capture_id": capture_id, "amount": amount, "fee_back": fee_back}
        self.refunds[refund_id] = record
        return record
```
