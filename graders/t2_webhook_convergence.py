"""Grader for t2. `expected` derives the position from the fact set independently of the module
under test. Literal anchors below pin that derivation to hand-worked values."""
import itertools
import json
import random
from datetime import datetime

from common import Checks, eq

CHECKS = Checks()
POS = ("available", "reserved", "chargeback_loss", "dispute_fee", "unapplied_refund")


def cap(cid, amt, eid=None):
    return {"event_id": eid or f"e-{cid}", "type": "capture.succeeded", "capture_id": cid, "amount_minor": amt}


def ref(rid, amt, eid=None):
    return {"event_id": eid or f"e-{rid}", "type": "refund.succeeded", "refund_id": rid, "amount_minor": amt}


def rfail(rid):
    return {"event_id": f"e-{rid}-f", "type": "refund.failed", "refund_id": rid}


def dopen(amt, eid="e-do"):
    return {"event_id": eid, "type": "dispute.opened", "dispute_id": "d1", "amount_minor": amt}


def ddec(outcome, at, eid=None):
    return {"event_id": eid or f"e-dd-{at}", "type": "dispute.decided", "dispute_id": "d1", "outcome": outcome, "decided_at": at}


def expected(events):
    caps, refunds, failed, opened, decisions = {}, {}, set(), None, {}
    for e in events:
        t = e["type"]
        if t == "capture.succeeded":
            caps[e["capture_id"]] = e["amount_minor"]
        elif t == "refund.succeeded":
            refunds[e["refund_id"]] = e["amount_minor"]
        elif t == "refund.failed":
            failed.add(e["refund_id"])
        elif t == "dispute.opened":
            opened = e["amount_minor"]
        else:
            decisions[datetime.fromisoformat(e["decided_at"].replace("Z", "+00:00"))] = e["outcome"]
    captured = sum(caps.values())
    wanted = sum(a for r, a in refunds.items() if r not in failed)
    refunded = min(captured, wanted)
    disputed = min(opened, captured - refunded) if opened is not None else 0
    outcome = decisions[max(decisions)] if decisions and opened is not None else None
    base = captured - refunded
    pos = dict(available=base - disputed, reserved=disputed, chargeback_loss=0, dispute_fee=1500 if opened is not None else 0, unapplied_refund=wanted - refunded)
    if outcome == "won":
        pos.update(available=base, reserved=0, dispute_fee=0)
    elif outcome == "lost":
        pos.update(reserved=0, chargeback_loss=disputed)
    return pos


def replay(mod, events, roundtrip=True):
    state = {}
    prior = []
    for e in events:
        mod.apply_event(state, dict(e))
        if roundtrip:
            state = json.loads(json.dumps(state))
        lines = [dict(x) for x in mod.journal(state)]
        eq(lines[: len(prior)], prior, "journal rewrote earlier lines")
        new = lines[len(prior):]
        eq(sum(x["amount_minor"] for x in new), 0, f"lines for {e['event_id']} do not balance")
        for x in new:
            eq(x["event_id"], e["event_id"], "line attributed to wrong delivery")
            eq(x["amount_minor"] != 0, True, "zero line")
        ids = [x["line_id"] for x in lines]
        eq(len(ids), len(set(ids)), "duplicate line_id")
        pos = mod.balances(state)
        eq(set(pos), set(POS), "balance keys")
        for account in POS:
            eq(sum(x["amount_minor"] for x in lines if x["account"] == account), pos[account], f"journal vs balances for {account}")
        prior = lines
    return mod.balances(state), prior


def all_orders(mod, events, limit=720, seed=7):
    orders = list(itertools.permutations(events)) if len(events) <= 6 else None
    if orders is None:
        rng = random.Random(seed)
        orders = [rng.sample(events, len(events)) for _ in range(limit)]
    want = expected(events)
    for order in orders:
        got, _ = replay(mod, list(order))
        if got != want:
            raise AssertionError(f"order {[e['event_id'] for e in order]}: expected {want}, got {got}")


@CHECKS
def anchor_values(mod):
    got, _ = replay(mod, [cap("c1", 10_000), ref("r1", 3_000), dopen(9_000), ddec("lost", "2026-03-01T10:00:00+00:00")])
    eq(got, dict(available=0, reserved=0, chargeback_loss=7_000, dispute_fee=1500, unapplied_refund=0), "lost dispute capped by refund")


@CHECKS
def duplicate_delivery_is_inert(mod):
    e = [cap("c1", 500), cap("c1", 500), ref("r1", 100), ref("r1", 100)]
    got, lines = replay(mod, e)
    eq(got["available"], 400, "available")
    eq(len(replay(mod, [e[0], e[2]])[1]), len(lines), "duplicates added lines")


@CHECKS
def reissued_fact_under_new_event_id(mod):
    e = [cap("c1", 500), cap("c1", 500, "e-retry-1"), ref("r1", 100), ref("r1", 100, "e-retry-2"), dopen(50), dopen(50, "e-retry-3")]
    got, _ = replay(mod, e)
    eq(got, expected(e), "position")


@CHECKS
def refund_failed_either_order(mod):
    all_orders(mod, [cap("c1", 900), ref("r1", 300), rfail("r1"), ref("r2", 100)])


@CHECKS
def refund_before_capture_converges(mod):
    all_orders(mod, [cap("c1", 200), ref("r1", 500), cap("c2", 200), cap("c3", 200)])


@CHECKS
def unapplied_refund_reported_then_absorbed(mod):
    got, _ = replay(mod, [ref("r1", 500)])
    eq((got["available"], got["unapplied_refund"]), (0, 500), "before capture")
    got, _ = replay(mod, [ref("r1", 500), cap("c1", 300)])
    eq((got["available"], got["unapplied_refund"]), (0, 200), "partly absorbed")


@CHECKS
def late_refund_shrinks_open_dispute(mod):
    all_orders(mod, [cap("c1", 1_000), dopen(1_000), ref("r1", 400)])
    got, _ = replay(mod, [cap("c1", 1_000), dopen(1_000), ref("r1", 400)])
    eq((got["available"], got["reserved"]), (0, 600), "reserved after late refund")


@CHECKS
def failed_refund_regrows_dispute(mod):
    all_orders(mod, [cap("c1", 1_000), dopen(1_000), ref("r1", 400), rfail("r1")])


@CHECKS
def lost_dispute_with_late_refund(mod):
    all_orders(mod, [cap("c1", 1_000), dopen(800), ref("r1", 400), ddec("lost", "2026-03-01T10:00:00+00:00")])


@CHECKS
def decision_before_open_has_no_effect(mod):
    got, _ = replay(mod, [cap("c1", 700), ddec("won", "2026-03-01T10:00:00+00:00")])
    eq(got, dict(available=700, reserved=0, chargeback_loss=0, dispute_fee=0, unapplied_refund=0), "no dispute yet")
    all_orders(mod, [cap("c1", 700), ddec("won", "2026-03-01T10:00:00+00:00"), dopen(700)])


@CHECKS
def latest_instant_wins_across_offsets(mod):
    # 10:30+02:00 is 08:30Z and sorts after 09:00Z as text, yet it is the earlier instant.
    early_big_text = ddec("won", "2026-03-01T10:30:00+02:00")
    late_small_text = ddec("lost", "2026-03-01T09:00:00+00:00")
    all_orders(mod, [cap("c1", 700), dopen(700), early_big_text, late_small_text])
    got, _ = replay(mod, [cap("c1", 700), dopen(700), late_small_text, early_big_text])
    eq(got["chargeback_loss"], 700, "lost is the later instant")


@CHECKS
def arbitration_flip_restores_fee_position(mod):
    all_orders(mod, [cap("c1", 700), dopen(300), ddec("lost", "2026-03-01T10:00:00+00:00"), ddec("won", "2026-03-02T10:00:00+00:00")])


@CHECKS
def big_mixed_scenario_random_orders(mod):
    events = [cap("c1", 5_000), cap("c2", 2_500), ref("r1", 1_000), ref("r2", 4_000), rfail("r2"), ref("r3", 7_000), dopen(6_000),
              ddec("won", "2026-03-01T10:00:00-05:00"), ddec("lost", "2026-03-01T14:00:00+00:00"), cap("c2", 2_500, "e-c2-again")]
    all_orders(mod, events, limit=1500)
