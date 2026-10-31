# cli-haiku / t5_wallet_repair / trial 1

- Requested: `haiku`, resolved: `claude-haiku-5-5`, provider: claude-cli
- Run at 2026-10-31T20:50:57+00:00 with params `{}`
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
    """Return numerator / denominator (denominator > 0) rounded to the nearest
    integer, with ties rounded to the even neighbour (ROUND_HALF_EVEN).
    Uses exact integer arithmetic, so there is no float error."""
    q, r = divmod(numerator, denominator)
    twice = 2 * r
    if twice > denominator or (twice == denominator and q % 2 == 1):
        q += 1
    return q


def fee_for(amount):
    # amount * 250 / 10000, rounded half-even, with a minimum fee of MIN_FEE.
    return max(MIN_FEE, _div_half_even(amount * FEE_BPS, 10000))


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
        # Release only the part of the hold that has not been captured.
        remaining = hold["amount"] - hold["captured"]
        self.held[hold["account"]] -= remaining

    def capture(self, capture_id, hold_id, amount, now, final=False):
        # Replay check is keyed by capture_id and comes before any state checks,
        # so a replay returns the original record even if the hold has closed.
        if capture_id in self.captures:
            return self.captures[capture_id]
        hold = self.holds[hold_id]
        if hold["status"] != "OPEN":
            raise WalletError("hold not open")
        if now > hold["expires_at"]:  # expires_at is inclusive
            raise WalletError("hold expired")
        if amount <= 0:
            raise WalletError("invalid amount")
        if hold["captured"] + amount > hold["amount"]:
            raise WalletError("over capture")
        fee = fee_for(amount)
        account = hold["account"]
        hold["captured"] += amount
        self.held[account] -= amount
        self.ledger[account] -= amount
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
        # Stored only by capture_id: a hold can have several partial captures.
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
            # A hold is still valid at exactly expires_at, so expire only after it.
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
        # Cap is cumulative across all refunds on this capture.
        if capture["refunded"] + amount > capture["amount"]:
            raise WalletError("over refund")
        capture["refunded"] += amount
        # Cumulative fee owed back, so the total equals
        # fee * total_refunded / captured_amount (half-even) after any sequence.
        total_fee_back = _div_half_even(
            capture["fee"] * capture["refunded"], capture["amount"]
        )
        fee_back = total_fee_back - capture["fee_refunded"]
        capture["fee_refunded"] = total_fee_back
        account = self.holds[capture["hold_id"]]["account"]
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
