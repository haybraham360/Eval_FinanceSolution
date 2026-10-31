# cli-haiku / t5_wallet_repair / trial 1

- Requested: `haiku`, resolved: `claude-haiku-5-5`, provider: claude-cli
- Run at 2026-10-31T14:45:06+00:00 with params `{}`
- Score 100%, full pass: True, finish: stop, error: None

## Failed checks

None.

## Prompt

See `tasks/t5_wallet_repair/prompt.md`.

## Model output

```python
"""Card-style wallet: holds, partial captures, refunds and fees.

All amounts are integer minor units. Rounding is ROUND_HALF_EVEN, computed
with exact integer arithmetic (no floats).

Defects corrected relative to the previous revision:
  * fee_for used float arithmetic and round-half-up; now exact half-even.
  * capture replay was keyed on hold_id instead of capture_id, and the
    record was stored under hold_id, so later partial captures overwrote
    earlier ones. Replays now check capture_id first, before any status check.
  * final capture did not release the uncaptured remainder, leaving it held
    forever (the reported symptom).
  * sweep_expired expired holds at now >= expires_at instead of now > expires_at,
    and released the full hold amount even after partial captures.
  * refund over-refund check ignored previously refunded amounts.
  * refund fee_back was computed per refund with floats instead of cumulatively
    as fee * total_refunded / captured_amount, so fees did not reconcile.
  * capture and refund did not reject non-positive amounts.
"""


class WalletError(Exception):
    pass


MIN_FEE = 30
FEE_BPS = 250


def _div_half_even(num, den):
    """Return num / den rounded to an integer, ties to even. num >= 0, den > 0."""
    q, r = divmod(num, den)
    twice = 2 * r
    if twice > den or (twice == den and q % 2 == 1):
        q += 1
    return q


def fee_for(amount):
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
            raise WalletError("invalid hold amount")
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
        # Release only what has not been captured.
        self.held[hold["account"]] -= hold["amount"] - hold["captured"]

    def capture(self, capture_id, hold_id, amount, now, final=False):
        # Replay is checked first, by capture_id, and changes nothing.
        if capture_id in self.captures:
            return self.captures[capture_id]
        hold = self.holds[hold_id]
        if amount <= 0:
            raise WalletError("invalid capture amount")
        if hold["status"] != "OPEN":
            raise WalletError("hold not open")
        # A hold is valid through expires_at inclusive.
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
            hold["status"] = "CLOSED"
            self._release_rest(hold)
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
            # Expiry is exclusive: a hold whose expires_at equals now is still valid.
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
            raise WalletError("invalid refund amount")
        new_refunded = capture["refunded"] + amount
        if new_refunded > capture["amount"]:
            raise WalletError("over refund")
        # Cumulative fee return: fee * total_refunded / captured, half-even.
        target_fee_back = _div_half_even(capture["fee"] * new_refunded, capture["amount"])
        fee_back = target_fee_back - capture["fee_refunded"]
        capture["refunded"] = new_refunded
        capture["fee_refunded"] = target_fee_back
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
