# free-nemotron-ultra / t5_wallet_repair / trial 1

- Requested: `nvidia/nemotron-3-ultra-550b-a55b:free`, resolved: `nvidia/nemotron-3-ultra-550b-a55b:free`, provider: Nvidia
- Run at 2026-11-06T20:14:55+00:00 with params `{}`
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


def _round_half_even(num, den):
    """Return num/den rounded to nearest integer, ties to even."""
    q, r = divmod(num, den)
    if 2 * r < den:
        return q
    elif 2 * r > den:
        return q + 1
    else:
        return q if q % 2 == 0 else q + 1


def fee_for(amount):
    fee = _round_half_even(amount * FEE_BPS, 10000)
    return max(MIN_FEE, fee)


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
        if self.available(account) < amount:
            raise WalletError("insufficient funds")
        hold = {"account": account, "amount": amount, "captured": 0, "status": "OPEN", "expires_at": expires_at}
        self.holds[hold_id] = hold
        self.held[account] = self.held.get(account, 0) + amount
        return hold

    def _release_rest(self, hold):
        self.held[hold["account"]] -= hold["amount"] - hold["captured"]

    def capture(self, capture_id, hold_id, amount, now, final=False):
        # Replay check
        if capture_id in self.captures:
            return self.captures[capture_id]
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
            "fee_refunded": 0
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
                self.held[hold["account"]] -= hold["amount"] - hold["captured"]
                hold["status"] = "EXPIRED"
                expired.append(hold_id)
        return expired

    def refund(self, refund_id, capture_id, amount):
        if refund_id in self.refunds:
            return self.refunds[refund_id]
        capture = self.captures[capture_id]
        if capture["refunded"] + amount > capture["amount"]:
            raise WalletError("over refund")
        total_refunded_after = capture["refunded"] + amount
        ideal_total_fee_back = _round_half_even(capture["fee"] * total_refunded_after, capture["amount"])
        fee_back = ideal_total_fee_back - capture["fee_refunded"]
        capture["refunded"] += amount
        capture["fee_refunded"] += fee_back
        account = self.holds[capture["hold_id"]]["account"]
        self.ledger[account] += amount
        self.merchant -= amount - fee_back
        self.revenue -= fee_back
        record = {"refund_id": refund_id, "capture_id": capture_id, "amount": amount, "fee_back": fee_back}
        self.refunds[refund_id] = record
        return record
```
