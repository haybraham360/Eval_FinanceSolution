"""Grader for t5. One check per defect, plus conservation. Only public behaviour is touched."""
import random

from common import Checks, eq

CHECKS = Checks()


def setup(mod, funds=100_000):
    w = mod.Wallet()
    w.deposit("a", funds)
    return w


def conserved(w, funds=100_000):
    eq(w.ledger["a"] + w.merchant + w.revenue, funds, "money conservation")


@CHECKS
def happy_path_fee_and_balances(mod):
    w = setup(mod)
    w.place_hold("h", "a", 10_000, 100)
    w.capture("c", "h", 10_000, 50, final=True)
    eq((w.ledger["a"], w.available("a"), w.merchant, w.revenue), (90_000, 90_000, 9_750, 250), "balances")


@CHECKS
def minimum_fee(mod):
    w = setup(mod)
    w.place_hold("h", "a", 1_000, 100)
    eq(w.capture("c", "h", 1_000, 50)["fee"], 30, "fee")


@CHECKS
def final_capture_releases_the_rest(mod):
    w = setup(mod)
    w.place_hold("h", "a", 10_000, 100)
    w.capture("c", "h", 6_000, 50, final=True)
    eq(w.available("a"), 94_000, "available")
    eq(w.held["a"], 0, "held")


@CHECKS
def second_partial_capture_is_not_a_replay(mod):
    w = setup(mod)
    w.place_hold("h", "a", 10_000, 100)
    w.capture("c1", "h", 3_000, 50)
    w.capture("c2", "h", 4_000, 51)
    eq(w.ledger["a"], 93_000, "ledger after two captures")
    eq(w.held["a"], 3_000, "held after two captures")


@CHECKS
def capture_replay_is_inert_even_after_close(mod):
    w = setup(mod)
    w.place_hold("h", "a", 10_000, 100)
    first = dict(w.capture("c1", "h", 3_000, 50, final=True))
    again = w.capture("c1", "h", 3_000, 500, final=True)
    eq(again["amount"], first["amount"], "replayed record")
    eq((w.ledger["a"], w.held["a"]), (97_000, 0), "state after replay")


@CHECKS
def sweep_after_partial_capture(mod):
    w = setup(mod)
    w.place_hold("h", "a", 10_000, 100)
    w.capture("c", "h", 4_000, 50)
    eq(w.sweep_expired(200), ["h"], "swept")
    eq((w.held["a"], w.available("a")), (0, 96_000), "after sweep")


@CHECKS
def void_after_partial_capture(mod):
    w = setup(mod)
    w.place_hold("h", "a", 10_000, 100)
    w.capture("c", "h", 4_000, 50)
    w.void("h")
    eq((w.held["a"], w.available("a")), (0, 96_000), "after void")


@CHECKS
def hold_valid_through_expiry_instant(mod):
    w = setup(mod)
    w.place_hold("h", "a", 10_000, 100)
    eq(w.sweep_expired(100), [], "sweep at the exact instant")
    w.capture("c", "h", 10_000, 100)
    eq(w.ledger["a"], 90_000, "capture at the exact instant")


@CHECKS
def expired_hold_rejects_capture(mod):
    w = setup(mod)
    w.place_hold("h", "a", 10_000, 100)
    try:
        w.capture("c", "h", 1_000, 101)
    except mod.WalletError:
        return
    raise AssertionError("capture after expiry succeeded")


@CHECKS
def fee_ties_round_half_even(mod):
    w = setup(mod)
    w.place_hold("h", "a", 40_000, 100)
    # 20100 * 2.5% = 502.5 -> 502; 20300 * 2.5% = 507.5 -> 508
    eq(w.capture("c1", "h", 20_100, 50)["fee"], 502, "tie down to even")
    w2 = setup(mod)
    w2.place_hold("h", "a", 40_000, 100)
    eq(w2.capture("c1", "h", 20_300, 50)["fee"], 508, "tie up to even")


@CHECKS
def cumulative_refund_limit(mod):
    w = setup(mod)
    w.place_hold("h", "a", 10_000, 100)
    w.capture("c", "h", 10_000, 50, final=True)
    w.refund("r1", "c", 7_000)
    try:
        w.refund("r2", "c", 7_000)
    except mod.WalletError:
        eq(w.ledger["a"], 97_000, "ledger after rejected refund")
        return
    raise AssertionError("refunds exceeded the captured amount")


@CHECKS
def refund_replay_is_inert(mod):
    w = setup(mod)
    w.place_hold("h", "a", 10_000, 100)
    w.capture("c", "h", 10_000, 50, final=True)
    w.refund("r1", "c", 2_000)
    before = (w.ledger["a"], w.merchant, w.revenue)
    w.refund("r1", "c", 2_000)
    eq((w.ledger["a"], w.merchant, w.revenue), before, "state after replay")


@CHECKS
def fee_returned_cumulatively(mod):
    w = setup(mod)
    w.place_hold("h", "a", 1_300, 100)
    fee = w.capture("c", "h", 1_300, 50, final=True)["fee"]
    eq(fee, 32, "fee")  # 32.5 rounds to the even 32
    for i in range(13):
        w.refund(f"r{i}", "c", 100)
    eq((w.revenue, w.merchant, w.ledger["a"]), (0, 0, 100_000), "after refunding everything in thirteen parts")


@CHECKS
def fee_return_matches_formula_at_every_step(mod):
    w = setup(mod)
    w.place_hold("h", "a", 3_700, 100)
    fee = w.capture("c", "h", 3_700, 50, final=True)["fee"]
    total, refunded = 0, 0
    for i, part in enumerate([11, 900, 1, 1_500, 77, 1_211]):
        total += w.refund(f"r{i}", "c", part)["fee_back"]
        refunded += part
        exact_times_2 = 2 * fee * refunded
        q, r = divmod(exact_times_2, 2 * 3_700)
        want = q + (1 if r * 2 > 2 * 3_700 or (r * 2 == 2 * 3_700 and q % 2) else 0)
        eq(total, want, f"fee returned after {refunded}")


@CHECKS
def random_operations_conserve_money(mod):
    for seed in range(40):
        rng = random.Random(seed)
        w = setup(mod)
        captures = []
        for i in range(60):
            op = rng.choice(["hold", "cap", "cap", "refund", "void", "sweep"])
            try:
                if op == "hold":
                    w.place_hold(f"h{i}", "a", rng.randint(50, 9_000), rng.randint(0, 100))
                elif op == "cap" and w.holds:
                    h = rng.choice(list(w.holds))
                    w.capture(f"c{i}", h, rng.randint(1, 3_000), rng.randint(0, 100), final=rng.random() < 0.4)
                    captures.append(f"c{i}")
                elif op == "refund" and captures:
                    w.refund(f"r{i}", rng.choice(captures), rng.randint(1, 1_000))
                elif op == "void" and w.holds:
                    w.void(rng.choice(list(w.holds)))
                elif op == "sweep":
                    w.sweep_expired(rng.randint(0, 110))
            except mod.WalletError:
                pass
            conserved(w)
            want_held = sum(h["amount"] - h["captured"] for h in w.holds.values() if h["status"] == "OPEN")
            eq(w.held.get("a", 0), want_held, f"held, seed {seed}")
