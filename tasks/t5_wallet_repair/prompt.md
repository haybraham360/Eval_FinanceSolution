# Incident ticket: repair `wallet.py`

`wallet.py` is our card-style wallet: holds, partial captures, refunds and fees. Its unit tests pass, but finance reports that it does not agree with the bank.

**Reported symptom:** customers complain that after a shop's final capture for less than the hold, the leftover amount stays unavailable in their wallet.

Finance also says "the totals drift in a few other places as well, we have not had time to isolate them". Assume the reported symptom is not the only defect. Audit the whole module against the intended behaviour below and fix every deviation. Keep the public class, method names, signatures, the attribute names used below, and the record dictionaries' existing keys. You may add private helpers and extra keys.

## Intended behaviour

Amounts are integer minor units. `available = ledger - held` for an account.

- **Holds.** `place_hold` reserves funds. Placing an existing `hold_id` again returns the existing hold and changes nothing. A hold is valid through its `expires_at` instant inclusive: a capture at exactly `expires_at` succeeds, and `sweep_expired(now)` must not expire a hold whose `expires_at` equals `now`.
- **Captures.** A hold can have several partial captures, each with its own `capture_id`, up to the hold amount in total. Replaying a `capture_id` returns the original record and changes nothing, even if the hold has since closed, voided or expired. `final=True` closes the hold and returns everything not captured to available.
- **Void and sweep.** Both release only what has not been captured. An expired hold cannot be captured.
- **Fees.** The fee on a capture is `amount * 250 / 10000` rounded ROUND_HALF_EVEN to a whole minor unit, with a minimum of 30. The merchant is credited `amount - fee` and revenue gets `fee`.
- **Refunds.** A capture can be refunded in several parts. The total refunded on a capture can never exceed the captured amount. Replaying a `refund_id` returns the original record and changes nothing. The refund returns `amount` to the customer's ledger and takes `amount - fee_back` from the merchant and `fee_back` from revenue.
- **Fee on refunds.** After any sequence of refunds on a capture, the total fee returned must equal `fee * total_refunded / captured_amount` rounded ROUND_HALF_EVEN, so a capture refunded in full returns its fee exactly.

## Current code

```python
class WalletError(Exception):
    pass


MIN_FEE = 30
FEE_BPS = 250


def fee_for(amount):
    return max(MIN_FEE, int(amount * FEE_BPS / 10000 + 0.5))


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
        hold = self.holds[hold_id]
        if hold_id in self.captures:
            return self.captures[hold_id]
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
        record = {"capture_id": capture_id, "hold_id": hold_id, "amount": amount, "fee": fee, "refunded": 0}
        self.captures[hold_id] = record
        self.captures[capture_id] = record
        if final:
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
            if hold["status"] == "OPEN" and now >= hold["expires_at"]:
                self.held[hold["account"]] -= hold["amount"]
                hold["status"] = "EXPIRED"
                expired.append(hold_id)
        return expired

    def refund(self, refund_id, capture_id, amount):
        if refund_id in self.refunds:
            return self.refunds[refund_id]
        capture = self.captures[capture_id]
        if amount > capture["amount"]:
            raise WalletError("over refund")
        capture["refunded"] += amount
        fee_back = round(capture["fee"] * amount / capture["amount"])
        account = self.holds[capture["hold_id"]]["account"]
        self.ledger[account] += amount
        self.merchant -= amount - fee_back
        self.revenue -= fee_back
        record = {"refund_id": refund_id, "capture_id": capture_id, "amount": amount, "fee_back": fee_back}
        self.refunds[refund_id] = record
        return record
```

Return the complete corrected module in one ```python block.
