"""Grader for t13. Every expected value below is a literal worked by hand in
reference/t13_expected_results.md, not derived from the reference module. Every scenario is
replayed through `replay`, which checks the journal invariants after every single record."""
import itertools
import json
import random

from common import Checks, eq

CHECKS = Checks()
REC = "payrail:receivable"


# ---------- record builders ----------

def snap(rid, sid, rate):
    return {"record_id": rid, "type": "fx.snapshot", "snapshot_id": sid, "rate": rate}


def pin(rid, pid, cust, cur, amt, at, sid=None):
    r = {"record_id": rid, "type": "payin.succeeded", "payin_id": pid, "customer_id": cust, "currency": cur, "amount_minor": amt, "occurred_at": at}
    if sid:
        r["fx_snapshot_id"] = sid
    return r


def ptimeout(rid, pid, cust, at):
    return {"record_id": rid, "type": "payin.api_result", "payin_id": pid, "customer_id": cust, "result": "timeout", "at": at}


def rev(rid, xid, pid, cur, amt, at, sid=None):
    r = {"record_id": rid, "type": "payin.reversed", "reversal_id": xid, "payin_id": pid, "currency": cur, "amount_minor": amt, "occurred_at": at}
    if sid:
        r["fx_snapshot_id"] = sid
    return r


def preq(rid, oid, cust, amt, at):
    return {"record_id": rid, "type": "payout.requested", "payout_id": oid, "customer_id": cust, "amount_minor": amt, "occurred_at": at}


def psend(rid, oid, result, at):
    return {"record_id": rid, "type": "payout.send_result", "payout_id": oid, "result": result, "sent_at": at}


def pretry(rid, oid, at):
    return {"record_id": rid, "type": "payout.retry_requested", "payout_id": oid, "at": at}


def plook(rid, oid, result, at):
    return {"record_id": rid, "type": "payout.lookup_result", "payout_id": oid, "result": result, "at": at}


def line(lid, lt, ref, amt, cur="NGN", settled=None, desc=""):
    return {"line_id": lid, "line_type": lt, "ref": ref, "currency": cur, "amount_minor": amt,
            "settled_ngn_minor": amt if settled is None else settled, "description": desc}


def sfile(rid, batch, seq, value_date, lines):
    return {"record_id": rid, "type": "settlement.file", "batch_id": batch, "file_seq": seq, "value_date": value_date, "lines": lines}


def close(rid, period):
    return {"record_id": rid, "type": "period.closed", "period": period}


# ---------- the sample log from the prompt ----------

def _seq1_lines():
    return [line("L1", "PAYIN", "P1", 10_000_000, desc="transfer"), line("L2", "FEE", "P1", 150_000, desc="fee"),
            line("L3", "PAYIN", "P2", 2503, "USD", 3_826_000, "card"), line("L4", "FEE", "P2", 57_000, desc="fee"),
            line("L5", "PAYIN", "P3", 4_000_000, desc="transfer"), line("L6", "FEE", "P3", 60_000, desc="fee"),
            line("L7", "PAYIN_REVERSAL", "X1", 1_000_000, desc="chargeback"), line("L8", "FEE_REFUND", "X1", 15_000, desc="fee refund"),
            line("L9", "PAYOUT", "O1", 8_000_000, desc="payout"), line("L10", "PAYIN", "P9", 777_700, desc="transfer")]


def _seq2_lines(prefix="M", fee_p3=60_000, refund_x1=16_000):
    return [line(f"{prefix}1", "PAYOUT", "O1", 8_000_000, desc="payout"), line(f"{prefix}2", "PAYIN", "P1", 10_000_000, desc="transfer"),
            line(f"{prefix}3", "FEE", "P1", 145_000, desc="fee"), line(f"{prefix}4", "PAYIN", "P2", 2503, "USD", 3_825_500, "card"),
            line(f"{prefix}5", "FEE", "P2", 57_000, desc="fee"), line(f"{prefix}6", "PAYIN", "P3", 4_000_000, desc="bank transfer (corrected narration)"),
            line(f"{prefix}7", "FEE", "P3", fee_p3, desc="fee"), line(f"{prefix}8", "PAYIN_REVERSAL", "X1", 1_000_000, desc="chargeback"),
            line(f"{prefix}9", "FEE_REFUND", "X1", refund_x1, desc="fee refund"), line(f"{prefix}10", "PAYIN", "P9", 777_700, desc="transfer")]


def sample_log():
    p1 = pin("r02", "P1", "C1", "NGN", 10_000_000, "2026-10-30T09:00:00Z")
    seq1 = sfile("r23", "B-1031", 1, "2026-10-31", _seq1_lines())
    return [
        snap("r01", "S-A", "1525.50"), p1, dict(p1),
        preq("r03", "O1", "C1", 8_000_000, "2026-10-30T12:00:00Z"),
        psend("r04", "O1", "timeout", "2026-10-30T12:00:05Z"),
        pretry("r05", "O1", "2026-10-30T13:00:00Z"),
        psend("r06", "O1", "timeout", "2026-10-30T13:00:03Z"),
        dict(p1, record_id="r07"),
        snap("r08", "S-B", "1531.00"),
        ptimeout("r09", "P3", "C1", "2026-10-31T10:00:00Z"),
        pretry("r10", "O1", "2026-10-31T12:30:00Z"),
        plook("r11", "O1", "accepted", "2026-10-31T12:30:10Z"),
        rev("r12", "X1", "P3", "NGN", 1_000_000, "2026-10-31T15:00:00Z"),
        pin("r13", "P3", "C1", "NGN", 4_000_000, "2026-10-31T10:00:01Z"),
        snap("r14", "S-A", "1540.00"),
        ptimeout("r15", "P4", "C2", "2026-10-31T21:00:00Z"),
        preq("r16", "O3", "C1", 1_000_000, "2026-10-31T22:00:00Z"),
        psend("r17", "O3", "timeout", "2026-10-31T22:00:04Z"),
        pin("r18", "P2", "C2", "USD", 2503, "2026-10-31T23:30:00Z", "S-A"),
        preq("r19", "O2", "C2", 2_000_000, "2026-10-31T23:40:00Z"),
        psend("r20", "O2", "timeout", "2026-10-31T23:40:02Z"),
        plook("r21", "O2", "not_found", "2026-10-31T23:50:00Z"),
        plook("r22", "O2", "not_found", "2026-11-01T00:00:00Z"),
        seq1, json.loads(json.dumps(seq1)),
        sfile("r24", "B-1031", 2, "2026-10-31", _seq2_lines()),
        sfile("r25", "B-1031", 1, "2026-10-31", _seq1_lines()),
        close("r26", "2026-10"),
        rev("r27", "X3", "P1", "NGN", 2_000_000, "2026-10-31T20:00:00Z"),
        rev("r28", "X2", "P2", "USD", 1001, "2026-11-01T09:00:00Z", "S-B"),
        sfile("r29", "B-1031", 3, "2026-10-31", _seq2_lines("N", 62_000, 15_500)),
        rev("r30", "X4", "P3", "NGN", 3_500_000, "2026-11-01T10:00:00Z"),
        pretry("r31", "O1", "2026-11-01T11:00:00Z"),
        pretry("r32", "O3", "2026-11-01T11:00:00Z"),
    ]


SAMPLE_BALANCES = {"C1": {"available": -1_000_000, "held": 1_000_000}, "C2": {"available": 2_291_300, "held": 0}}
SAMPLE_EXCEPTIONS = {("FX_SNAPSHOT_CONFLICT", "S-A"), ("NEGATIVE_BALANCE", "C1"), ("PAYIN_OUTCOME_UNKNOWN", "P4"),
                     ("PAYOUT_OUTCOME_UNKNOWN", "O3"), ("REVERSAL_EXCEEDS_PAYIN", "X4"), ("UNMATCHED_SETTLEMENT_LINE", "P9")}
SAMPLE_OCT = {REC: 4_761_174, "customer:C1:available": -4_000_000, "customer:C1:held": -1_000_000, "fee_expense": 246_000, "fx_gain_loss": -7_174}
SAMPLE_NOV = {REC: -2_711_200, "customer:C1:available": 5_000_000, "customer:C2:available": -2_291_300, "fee_expense": 2_500}


# ---------- harness ----------

def replay(mod, records, state=None, seen=None):
    """Applies records one by one, round-tripping state through JSON, and checks the journal
    invariants after every record. Returns (state, commands per record)."""
    state = {} if state is None else state
    seen = set() if seen is None else seen
    prior = [dict(x) for x in mod.journal(state)] if state else []
    out = []
    for rec in records:
        dup = rec["record_id"] in seen
        cmds = mod.apply(state, json.loads(json.dumps(rec)))
        cmds = list(cmds or [])
        state = json.loads(json.dumps(state))
        lines = [dict(x) for x in mod.journal(state)]
        eq(lines[: len(prior)], prior, f"journal rewrote earlier lines at {rec['record_id']}")
        new = lines[len(prior):]
        if dup:
            eq((cmds, new), ([], []), f"repeat delivery of {rec['record_id']} had an effect")
        eq(sum(x["amount_minor"] for x in new), 0, f"lines added by {rec['record_id']} do not balance")
        for x in new:
            eq(x["record_id"], rec["record_id"], "line attributed to the wrong record")
            eq(type(x["amount_minor"]) is int and x["amount_minor"] != 0, True, f"bad amount {x['amount_minor']!r}")
            eq(len(x["accounting_date"]) == 10 and x["accounting_date"][4] == "-", True, "accounting_date format")
        ids = [x["line_id"] for x in lines]
        eq(len(ids), len(set(ids)), "duplicate line_id")
        bal = mod.balances(state)
        custs = {x["account"].split(":")[1] for x in lines if x["account"].startswith("customer:")}
        for c in custs:
            for kind in ("available", "held"):
                want = -sum(x["amount_minor"] for x in lines if x["account"] == f"customer:{c}:{kind}")
                eq(bal.get(c, {}).get(kind, 0), want, f"balances vs journal for {c} {kind} after {rec['record_id']}")
        seen.add(rec["record_id"])
        prior = lines
        out.append(cmds)
    return state, out


def norm_bal(b):
    return {c: {"available": v.get("available", 0), "held": v.get("held", 0)} for c, v in b.items() if v.get("available", 0) or v.get("held", 0)}


def exc(mod, state):
    return {(e["code"], e["ref"]) for e in mod.exceptions(state)}


def recon(mod, state):
    r = mod.reconciliation(state)
    breaks = {(b["line_type"], b["ref"], b["delta_minor"]) for b in r["breaks"]}
    eq(sum(b[2] for b in breaks), r["provider_net"] - r["ledger_receivable"], "breaks do not explain provider_net - ledger_receivable")
    return r["ledger_receivable"], r["provider_net"], breaks


def totals(mod, state, period):
    return {k: v for k, v in mod.period_totals(state, period).items() if v}


def acct(mod, state, account):
    return sum(x["amount_minor"] for x in mod.journal(state) if x["account"] == account)


def view(mod, state, payins=(), payouts=()):
    return {"bal": norm_bal(mod.balances(state)), "exc": exc(mod, state), "recon": recon(mod, state),
            "oct": totals(mod, state, "2026-10"), "nov": totals(mod, state, "2026-11"),
            "payin": {p: mod.payin_status(state, p) for p in payins}, "payout": {o: mod.payout_status(state, o) for o in payouts}}


def all_orders(mod, records, want_fn, limit=400, seed=13, prefix=()):
    orders = list(itertools.permutations(records)) if len(records) <= 6 else None
    if orders is None:
        rng = random.Random(seed)
        orders = [rng.sample(records, len(records)) for _ in range(limit)]
    for order in orders:
        state, _ = replay(mod, list(prefix) + list(order))
        want_fn(state, [r["record_id"] for r in order])


# ---------- the sample log ----------

def _sample(mod):
    return replay(mod, sample_log())


@CHECKS
def sample_final_balances(mod):
    state, _ = _sample(mod)
    eq(norm_bal(mod.balances(state)), norm_bal(SAMPLE_BALANCES), "balances")


@CHECKS
def sample_statuses(mod):
    state, _ = _sample(mod)
    eq({p: mod.payin_status(state, p) for p in ("P1", "P2", "P3", "P4", "P9")},
       {"P1": "PARTIALLY_REVERSED", "P2": "PARTIALLY_REVERSED", "P3": "REVERSED", "P4": "PENDING", "P9": None}, "payin statuses")
    eq({o: mod.payout_status(state, o) for o in ("O1", "O2", "O3", "O9")},
       {"O1": "PAID", "O2": "FAILED", "O3": "UNKNOWN", "O9": None}, "payout statuses")


@CHECKS
def sample_reconciliation(mod):
    state, _ = _sample(mod)
    eq(recon(mod, state), (2_049_974, 9_354_700, {("PAYIN", "P9", 777_700), ("PAYIN_REVERSAL", "X2", 1_527_026),
                                                   ("PAYIN_REVERSAL", "X3", 2_000_000), ("PAYIN_REVERSAL", "X4", 3_000_000)}), "reconciliation")


@CHECKS
def sample_fee_and_fx_totals(mod):
    state, _ = _sample(mod)
    eq((acct(mod, state, "fee_expense"), acct(mod, state, "fx_gain_loss")), (248_500, -7_174), "fee_expense, fx_gain_loss")


@CHECKS
def sample_period_totals(mod):
    state, _ = _sample(mod)
    eq(totals(mod, state, "2026-10"), SAMPLE_OCT, "October")
    eq(totals(mod, state, "2026-11"), SAMPLE_NOV, "November")


@CHECKS
def sample_exceptions(mod):
    state, _ = _sample(mod)
    eq(exc(mod, state), SAMPLE_EXCEPTIONS, "open exceptions")


@CHECKS
def sample_commands(mod):
    log = sample_log()
    _, cmds = replay(mod, log)
    got = {log[i]["record_id"]: [(c["command"], c["payout_id"]) for c in cs] for i, cs in enumerate(cmds) if cs}
    eq(got, {"r03": [("send", "O1")], "r05": [("send", "O1")], "r10": [("lookup", "O1")], "r16": [("send", "O3")],
             "r19": [("send", "O2")], "r32": [("send", "O3")]}, "commands")
    refs = {}
    for cs in cmds:
        for c in cs:
            refs.setdefault(c["payout_id"], set()).add(c["reference"])
    eq(all(len(v) == 1 for v in refs.values()), True, f"one reference per payout: {refs}")
    flat = [next(iter(v)) for v in refs.values()]
    eq(len(flat), len(set(flat)), "payouts share a reference")


@CHECKS
def sample_full_replay_is_inert(mod):
    log = sample_log()
    state, _ = replay(mod, log)
    before = view(mod, state, ("P1", "P2", "P3", "P4"), ("O1", "O2", "O3"))
    state, cmds = replay(mod, log, state, {r["record_id"] for r in log})
    eq(all(c == [] for c in cmds), True, "replay emitted commands")
    eq(view(mod, state, ("P1", "P2", "P3", "P4"), ("O1", "O2", "O3")), before, "replay changed outputs")


@CHECKS
def sample_result_stated_correctly(mod):
    s = getattr(mod, "SAMPLE_RESULT", None)
    eq(isinstance(s, dict), True, "SAMPLE_RESULT missing")
    eq(norm_bal(s["balances"]), norm_bal(SAMPLE_BALANCES), "SAMPLE_RESULT balances")
    eq((s["ledger_receivable"], s["provider_net"], s["fee_expense"], s["fx_gain_loss"]), (2_049_974, 9_354_700, 248_500, -7_174),
       "SAMPLE_RESULT ledger_receivable, provider_net, fee_expense, fx_gain_loss")
    eq({tuple(x) for x in s["exceptions"]}, SAMPLE_EXCEPTIONS, "SAMPLE_RESULT exceptions")


# ---------- pay-ins ----------

@CHECKS
def duplicate_and_reissued_facts_count_once(mod):
    once = [pin("a", "P1", "C1", "NGN", 500_000, "2026-10-10T10:00:00Z"), rev("b", "X1", "P1", "NGN", 100_000, "2026-10-11T10:00:00Z")]
    s1, _ = replay(mod, once)
    many = once + [dict(once[0]), dict(once[0], record_id="a2"), dict(once[1], record_id="b2"), dict(once[1]), dict(once[0], record_id="a3")]
    s2, _ = replay(mod, many)
    eq(norm_bal(mod.balances(s2)), {"C1": {"available": 400_000, "held": 0}}, "balance")
    eq(len(mod.journal(s2)), len(mod.journal(s1)), "re-issued facts added lines")


@CHECKS
def payin_timeout_is_pending_not_failed(mod):
    state, _ = replay(mod, [ptimeout("t", "P5", "C1", "2026-10-20T10:00:00Z")])
    eq(mod.payin_status(state, "P5"), "PENDING", "status after timeout")
    eq(norm_bal(mod.balances(state)), {}, "credited without a webhook")
    eq(exc(mod, state), {("PAYIN_OUTCOME_UNKNOWN", "P5")}, "exceptions after timeout")
    state, _ = replay(mod, [pin("w", "P5", "C1", "NGN", 300_000, "2026-10-20T10:00:01Z")], state, {"t"})
    eq((mod.payin_status(state, "P5"), norm_bal(mod.balances(state)), exc(mod, state)),
       ("SUCCEEDED", {"C1": {"available": 300_000, "held": 0}}, set()), "after the webhook")
    late, _ = replay(mod, [pin("w", "P5", "C1", "NGN", 300_000, "2026-10-20T10:00:01Z"), ptimeout("t", "P5", "C1", "2026-10-20T10:00:00Z")])
    eq((mod.payin_status(late, "P5"), exc(mod, late)), ("SUCCEEDED", set()), "timeout after the webhook")


@CHECKS
def unmatched_settlement_line_never_credits(mod):
    f = sfile("f", "B1", 1, "2026-10-20", [line("1", "PAYIN", "P5", 300_000)])
    state, _ = replay(mod, [ptimeout("t", "P5", "C1", "2026-10-20T10:00:00Z"), f])
    eq(norm_bal(mod.balances(state)), {}, "a settlement line credited the customer")
    eq(exc(mod, state), {("PAYIN_OUTCOME_UNKNOWN", "P5"), ("UNMATCHED_SETTLEMENT_LINE", "P5")}, "exceptions")
    eq(recon(mod, state), (0, 300_000, {("PAYIN", "P5", 300_000)}), "reconciliation")
    state, _ = replay(mod, [pin("w", "P5", "C1", "NGN", 300_000, "2026-10-20T10:00:01Z")], state, {"t", "f"})
    eq((exc(mod, state), recon(mod, state)), (set(), (300_000, 300_000, set())), "after the webhook")


@CHECKS
def orphan_reversal_links_when_payin_arrives(mod):
    records = [pin("p", "P1", "C1", "NGN", 900_000, "2026-10-10T10:00:00Z"), rev("x", "X1", "P1", "NGN", 400_000, "2026-10-12T10:00:00Z"),
               sfile("f", "B1", 1, "2026-10-15", [line("1", "PAYIN", "P1", 900_000), line("2", "PAYIN_REVERSAL", "X1", 400_000)])]
    orphan, _ = replay(mod, [records[1], records[2]])
    eq(exc(mod, orphan), {("ORPHAN_REVERSAL", "X1"), ("UNMATCHED_SETTLEMENT_LINE", "P1"), ("UNMATCHED_SETTLEMENT_LINE", "X1")}, "while orphaned")
    eq(norm_bal(mod.balances(orphan)), {}, "orphan reversal moved money")

    def want(state, order):
        eq(norm_bal(mod.balances(state)), {"C1": {"available": 500_000, "held": 0}}, f"balance for order {order}")
        eq((mod.payin_status(state, "P1"), exc(mod, state), recon(mod, state)), ("PARTIALLY_REVERSED", set(), (500_000, 500_000, set())), f"order {order}")

    all_orders(mod, records, want)


@CHECKS
def reversals_cap_in_occurrence_order(mod):
    records = [pin("p", "P1", "C1", "NGN", 5_000, "2026-10-01T10:00:00Z"),
               rev("a", "Xa", "P1", "NGN", 3_000, "2026-10-03T10:00:00Z"),
               rev("b", "Xb", "P1", "NGN", 3_000, "2026-10-02T10:00:00Z"),
               sfile("f", "B1", 1, "2026-10-05", [line("1", "PAYIN", "P1", 5_000), line("2", "PAYIN_REVERSAL", "Xb", 3_000), line("3", "PAYIN_REVERSAL", "Xa", 2_000)])]

    def want(state, order):
        eq(norm_bal(mod.balances(state)), {}, f"balance for order {order}")
        eq((mod.payin_status(state, "P1"), exc(mod, state)), ("REVERSED", {("REVERSAL_EXCEEDS_PAYIN", "Xa")}), f"order {order}")
        eq(recon(mod, state), (0, 0, set()), f"reconciliation for order {order}")

    all_orders(mod, records, want)
    # same instant: reversal_id breaks the tie
    tie = [pin("p", "P1", "C1", "NGN", 5_000, "2026-10-01T10:00:00Z"), rev("a", "Xb", "P1", "NGN", 3_000, "2026-10-02T10:00:00Z"),
           rev("b", "Xa", "P1", "NGN", 3_000, "2026-10-02T10:00:00Z")]
    all_orders(mod, tie, lambda s, o: eq(exc(mod, s), {("REVERSAL_EXCEEDS_PAYIN", "Xb")}, f"tie order {o}"))


@CHECKS
def negative_balance_reported_and_blocks_payouts(mod):
    state, cmds = replay(mod, [pin("p", "P1", "C1", "NGN", 1_000_000, "2026-10-01T10:00:00Z"),
                               preq("o", "O1", "C1", 800_000, "2026-10-01T11:00:00Z"), psend("s", "O1", "accepted", "2026-10-01T11:00:01Z"),
                               rev("x", "X1", "P1", "NGN", 600_000, "2026-10-02T10:00:00Z"),
                               preq("o2", "O2", "C1", 1, "2026-10-02T11:00:00Z")])
    eq(norm_bal(mod.balances(state)), {"C1": {"available": -400_000, "held": 0}}, "balance")
    eq(exc(mod, state), {("NEGATIVE_BALANCE", "C1")}, "exceptions")
    eq((mod.payout_status(state, "O2"), cmds[-1]), ("REJECTED", []), "payout while negative")


# ---------- FX ----------

@CHECKS
def fx_uses_payin_snapshot_half_even(mod):
    state, _ = replay(mod, [snap("s1", "S-A", "1525.50"), snap("s2", "S-B", "1531.00"),
                            pin("p", "P2", "C2", "USD", 2503, "2026-10-20T10:00:00Z", "S-A"),
                            snap("s3", "S-A", "1540.00"), snap("s4", "S-B", "1531.00")])
    # 2503 x 1525.50 = 3,818,326.5 -> half to even 3,818,326 (half-up would give 3,818,327)
    eq(norm_bal(mod.balances(state)), {"C2": {"available": 3_818_326, "held": 0}}, "credit at S-A, half to even")
    eq(exc(mod, state), {("FX_SNAPSHOT_CONFLICT", "S-A")}, "conflict on S-A only")
    state, _ = replay(mod, [rev("x", "X2", "P2", "USD", 1001, "2026-10-21T10:00:00Z", "S-B")], state, {"s1", "s2", "p", "s3", "s4"})
    # 1001 x 1525.50 = 1,527,025.5 -> 1,527,026; at S-B it would be 1,532,531
    eq(norm_bal(mod.balances(state)), {"C2": {"available": 2_291_300, "held": 0}}, "reversal at the pay-in's snapshot")


@CHECKS
def fx_reversals_round_cumulatively(mod):
    records = [rev("a", "Xa", "P2", "USD", 1, "2026-10-21T10:00:00Z"), rev("b", "Xb", "P2", "USD", 1, "2026-10-22T10:00:00Z"),
               rev("c", "Xc", "P2", "USD", 1, "2026-10-23T10:00:00Z"), rev("d", "Xd", "P2", "USD", 2500, "2026-10-24T10:00:00Z"),
               pin("p", "P2", "C2", "USD", 2503, "2026-10-20T10:00:00Z", "S-A")]

    def want(state, order):
        eq(norm_bal(mod.balances(state)), {}, f"fully reversed pay-in must leave exactly 0, order {order}")
        eq(mod.payin_status(state, "P2"), "REVERSED", f"status, order {order}")
        # cumulative NGN: 1526, 3051, 4576 (1525.5 -> 1526, 4576.5 -> 4576), then 3,818,326 - 4,576
        eq(-acct(mod, state, REC), 0, f"receivable, order {order}")

    all_orders(mod, records, want, limit=120, prefix=[snap("s", "S-A", "1525.50")])
    state, _ = replay(mod, [snap("s", "S-A", "1525.50")] + records[4:] + records[:2])
    eq(norm_bal(mod.balances(state)), {"C2": {"available": 3_818_326 - 3_051, "held": 0}}, "after two one-cent reversals")


@CHECKS
def fx_difference_posted_from_settlement(mod):
    base = [snap("s", "S-A", "1525.50"), pin("p", "P2", "C2", "USD", 2503, "2026-10-20T10:00:00Z", "S-A")]
    state, _ = replay(mod, base + [sfile("f1", "B1", 1, "2026-10-21", [line("1", "PAYIN", "P2", 2503, "USD", 3_826_000)])])
    eq((acct(mod, state, "fx_gain_loss"), recon(mod, state)), (-7_674, (3_826_000, 3_826_000, set())), "FX gain on settlement")
    state, _ = replay(mod, [sfile("f2", "B1", 2, "2026-10-21", [line("1", "PAYIN", "P2", 2503, "USD", 3_825_500)])], state, {"s", "p", "f1"})
    eq((acct(mod, state, "fx_gain_loss"), recon(mod, state)), (-7_174, (3_825_500, 3_825_500, set())), "FX after corrected file")
    bad, _ = replay(mod, base + [sfile("f1", "B1", 1, "2026-10-21", [line("1", "PAYIN", "P2", 2500, "USD", 3_826_000)])])
    eq((acct(mod, bad, "fx_gain_loss"), exc(mod, bad)), (0, {("SETTLEMENT_AMOUNT_MISMATCH", "P2")}), "USD amount mismatch posts no FX")
    eq(recon(mod, bad), (3_818_326, 3_826_000, {("PAYIN", "P2", 7_674)}), "USD amount mismatch is a break")


# ---------- fees ----------

@CHECKS
def fee_refund_is_cumulative_floor(mod):
    base = [pin("p", "P1", "C1", "NGN", 3_000_000, "2026-10-01T10:00:00Z"), rev("a", "Xa", "P1", "NGN", 1_000_000, "2026-10-02T10:00:00Z"),
            rev("b", "Xb", "P1", "NGN", 2_000_000, "2026-10-03T10:00:00Z")]

    def f(rid, ra, rb):
        return sfile(rid, "B1", 1, "2026-10-05", [line("1", "FEE", "P1", 50_000), line("2", "FEE_REFUND", "Xa", ra), line("3", "FEE_REFUND", "Xb", rb)])

    # Xa: floor(50,000 x 1/3) = 16,666. Xb: 50,000 - 16,666 = 33,334 (a per-reversal floor would say 33,333).
    state, _ = replay(mod, base + [f("f", 16_666, 33_334)])
    eq((exc(mod, state), acct(mod, state, "fee_expense")), (set(), 0), "contractual refunds")
    state, _ = replay(mod, base + [f("f", 16_666, 33_333)])
    eq((exc(mod, state), acct(mod, state, "fee_expense")), ({("FEE_REFUND_MISMATCH", "Xb")}, 1), "short refund flagged, posted as stated")
    state, _ = replay(mod, base + [f("f", 16_667, 33_334)])
    eq(exc(mod, state), {("FEE_REFUND_MISMATCH", "Xa")}, "rounded-up refund flagged")


@CHECKS
def fee_refund_follows_corrected_fee(mod):
    records = [pin("p", "P3", "C1", "NGN", 4_000_000, "2026-10-01T10:00:00Z"), rev("x", "X1", "P3", "NGN", 1_000_000, "2026-10-02T10:00:00Z"),
               sfile("f1", "B1", 1, "2026-10-05", [line("1", "FEE", "P3", 60_000), line("2", "FEE_REFUND", "X1", 15_500)]),
               sfile("f2", "B1", 2, "2026-10-05", [line("1", "FEE", "P3", 62_000), line("2", "FEE_REFUND", "X1", 15_500)])]
    state, _ = replay(mod, records[:3])
    eq(exc(mod, state), {("FEE_REFUND_MISMATCH", "X1")}, "15,500 against a 60,000 fee")

    def want(state, order):
        eq((exc(mod, state), acct(mod, state, "fee_expense")), (set(), 46_500), f"order {order}")

    all_orders(mod, records, want)


# ---------- corrected files ----------

@CHECKS
def corrected_file_posts_only_the_difference(mod):
    p1 = pin("p", "P1", "C1", "NGN", 10_000_000, "2026-10-30T09:00:00Z")
    f1 = sfile("f1", "B1", 1, "2026-10-31", [line("L1", "PAYIN", "P1", 10_000_000), line("L2", "FEE", "P1", 150_000)])
    f2 = sfile("f2", "B1", 2, "2026-10-31", [line("M1", "FEE", "P1", 145_000), line("M2", "PAYIN", "P1", 10_000_000, desc="renamed")])
    state, _ = replay(mod, [p1, f1])
    n = len(mod.journal(state))
    state, _ = replay(mod, [f2], state, {"p", "f1"})
    new = mod.journal(state)[n:]
    net = {}
    for x in new:
        net[x["account"]] = net.get(x["account"], 0) + x["amount_minor"]
    eq({k: v for k, v in net.items() if v}, {"fee_expense": -5_000, REC: 5_000}, "net effect of the correction")
    eq(acct(mod, state, "fee_expense"), 145_000, "fee after correction")
    dropped, _ = replay(mod, [sfile("f3", "B1", 3, "2026-10-31", [line("N1", "PAYIN", "P1", 10_000_000)])], state, {"p", "f1", "f2"})
    eq((acct(mod, dropped, "fee_expense"), acct(mod, dropped, REC)), (0, 10_000_000), "a fee line dropped by a correction is unwound")


@CHECKS
def operational_correction_posts_nothing(mod):
    p1 = pin("p", "P1", "C1", "NGN", 10_000_000, "2026-10-30T09:00:00Z")
    f1 = sfile("f1", "B1", 1, "2026-10-31", [line("L1", "PAYIN", "P1", 10_000_000, desc="transfer"), line("L2", "FEE", "P1", 150_000)])
    f2 = sfile("f2", "B1", 2, "2026-10-31", [line("Z9", "FEE", "P1", 150_000, desc="fee (renamed)"), line("Z8", "PAYIN", "P1", 10_000_000, desc="narration fixed")])
    state, _ = replay(mod, [p1, f1])
    n = len(mod.journal(state))
    state, cmds = replay(mod, [f2, sfile("f1b", "B1", 1, "2026-10-31", f1["lines"])], state, {"p", "f1"})
    eq(mod.journal(state)[n:], [], "description and line_id changes posted lines")
    eq(cmds, [[], []], "commands")


@CHECKS
def stale_file_seq_is_ignored_in_any_order(mod):
    records = [pin("p", "P1", "C1", "NGN", 10_000_000, "2026-10-30T09:00:00Z"),
               sfile("f1", "B1", 1, "2026-10-31", [line("L1", "PAYIN", "P1", 10_000_000), line("L2", "FEE", "P1", 150_000), line("L3", "PAYIN", "P9", 5)]),
               sfile("f2", "B1", 2, "2026-10-31", [line("M1", "PAYIN", "P1", 10_000_000), line("M2", "FEE", "P1", 145_000)]),
               sfile("g1", "B2", 1, "2026-10-31", [line("K1", "FEE", "P7", 1_000)])]

    def want(state, order):
        eq((acct(mod, state, "fee_expense"), exc(mod, state)), (146_000, set()), f"order {order}")
        eq(recon(mod, state), (10_000_000 - 146_000, 10_000_000 - 146_000, set()), f"reconciliation, order {order}")

    all_orders(mod, records, want)


# ---------- payouts ----------

def _funded(amount=10_000_000):
    return [pin("p", "P1", "C1", "NGN", amount, "2026-10-30T09:00:00Z")]


@CHECKS
def payout_timeout_keeps_funds_held(mod):
    state, cmds = replay(mod, _funded() + [preq("o", "O1", "C1", 8_000_000, "2026-10-30T12:00:00Z"), psend("s", "O1", "timeout", "2026-10-30T12:00:05Z")])
    eq([c["command"] for c in cmds[1]], ["send"], "request sends once")
    eq((mod.payout_status(state, "O1"), norm_bal(mod.balances(state))), ("UNKNOWN", {"C1": {"available": 2_000_000, "held": 8_000_000}}), "after timeout")
    eq(exc(mod, state), {("PAYOUT_OUTCOME_UNKNOWN", "O1")}, "exceptions")


@CHECKS
def retry_inside_window_resends_same_reference(mod):
    log = _funded() + [preq("o", "O1", "C1", 8_000_000, "2026-10-30T12:00:00Z"), psend("s1", "O1", "timeout", "2026-10-30T12:00:05Z"),
                       pretry("t1", "O1", "2026-10-30T13:00:00Z"), psend("s2", "O1", "timeout", "2026-10-30T13:00:03Z"),
                       pretry("t2", "O1", "2026-10-31T12:00:04Z")]
    _, cmds = replay(mod, log)
    eq([[c["command"] for c in cs] for cs in cmds], [[], ["send"], [], ["send"], [], ["send"]], "commands")
    eq(len({c["reference"] for cs in cmds for c in cs}), 1, "references")


@CHECKS
def retry_after_window_looks_up_never_sends(mod):
    head = _funded() + [preq("o", "O1", "C1", 8_000_000, "2026-10-30T12:00:00Z"), psend("s1", "O1", "timeout", "2026-10-30T12:00:05Z"),
                        pretry("t1", "O1", "2026-10-30T13:00:00Z"), psend("s2", "O1", "timeout", "2026-10-30T13:00:03Z")]
    for at in ("2026-10-31T12:00:05Z", "2026-10-31T12:30:00Z", "2026-10-31T13:00:02Z", "2026-11-03T09:00:00Z"):
        _, cmds = replay(mod, head + [pretry("t2", "O1", at)])
        eq([c["command"] for c in cmds[-1]], ["lookup"], f"retry at {at}, 24h after the first send at 12:00:05")
    # send results can arrive out of order: the window still runs from the earliest sent_at
    swapped = head[:2] + [head[4], head[2], pretry("t2", "O1", "2026-10-31T12:30:00Z")]
    _, cmds = replay(mod, swapped)
    eq([c["command"] for c in cmds[-1]], ["lookup"], "earliest sent_at when results arrive out of order")
    state, cmds = replay(mod, head + [pretry("t2", "O1", "2026-10-31T12:30:00Z"), plook("l", "O1", "accepted", "2026-10-31T12:30:10Z"),
                                      pretry("t3", "O1", "2026-11-01T11:00:00Z")])
    eq((mod.payout_status(state, "O1"), cmds[-1]), ("PAID", []), "paid payout ignores retries")
    eq(norm_bal(mod.balances(state)), {"C1": {"available": 2_000_000, "held": 0}}, "balance")


@CHECKS
def lookup_respects_visibility_delay(mod):
    head = _funded() + [preq("o", "O2", "C1", 2_000_000, "2026-10-31T23:40:00Z"), psend("s", "O2", "timeout", "2026-10-31T23:40:02Z")]
    state, _ = replay(mod, head + [plook("l1", "O2", "not_found", "2026-10-31T23:55:01Z")])
    eq((mod.payout_status(state, "O2"), norm_bal(mod.balances(state))["C1"]["held"]), ("UNKNOWN", 2_000_000), "899 s after the send")
    state, _ = replay(mod, [plook("l2", "O2", "not_found", "2026-10-31T23:55:02Z")], state, {r["record_id"] for r in head} | {"l1"})
    eq((mod.payout_status(state, "O2"), norm_bal(mod.balances(state))), ("FAILED", {"C1": {"available": 10_000_000, "held": 0}}), "900 s after the send")
    eq(exc(mod, state), set(), "exceptions")
    nosend, _ = replay(mod, _funded() + [preq("o", "O2", "C1", 2_000_000, "2026-10-31T23:40:00Z"), plook("l", "O2", "not_found", "2026-11-02T00:00:00Z")])
    eq(mod.payout_status(nosend, "O2"), "SENDING", "not_found with no send result")
    resent = head + [pretry("t", "O2", "2026-10-31T23:50:00Z"), psend("s2", "O2", "timeout", "2026-10-31T23:50:01Z"),
                     plook("l", "O2", "not_found", "2026-11-01T00:00:00Z")]
    state, _ = replay(mod, resent)
    eq(mod.payout_status(state, "O2"), "UNKNOWN", "delay runs from the latest send")


@CHECKS
def settlement_line_resolves_unknown_payout(mod):
    state, _ = replay(mod, _funded() + [preq("o", "O1", "C1", 8_000_000, "2026-10-30T12:00:00Z"), psend("s", "O1", "timeout", "2026-10-30T12:00:05Z"),
                                        sfile("f", "B1", 1, "2026-10-31", [line("1", "PAYIN", "P1", 10_000_000), line("2", "PAYOUT", "O1", 8_000_000)]),
                                        pretry("t", "O1", "2026-10-30T13:00:00Z")])
    eq((mod.payout_status(state, "O1"), norm_bal(mod.balances(state)), exc(mod, state)),
       ("PAID", {"C1": {"available": 2_000_000, "held": 0}}, set()), "after the PAYOUT line")
    eq(recon(mod, state), (2_000_000, 2_000_000, set()), "reconciliation")
    paid = [x for x in mod.journal(state) if x["account"] == REC and x["amount_minor"] == -8_000_000]
    eq([x["accounting_date"] for x in paid], ["2026-10-31"], "PAID dated by the file's value_date")


@CHECKS
def contradictory_payout_evidence_is_a_conflict(mod):
    failed = _funded() + [preq("o", "O2", "C1", 2_000_000, "2026-10-31T23:40:00Z"), psend("s", "O2", "rejected", "2026-10-31T23:40:02Z"),
                          sfile("f", "B1", 1, "2026-11-01", [line("1", "PAYOUT", "O2", 2_000_000)]), plook("l", "O2", "accepted", "2026-11-01T10:00:00Z")]
    state, _ = replay(mod, failed)
    eq((mod.payout_status(state, "O2"), norm_bal(mod.balances(state))), ("FAILED", {"C1": {"available": 10_000_000, "held": 0}}), "failed payout")
    eq(exc(mod, state), {("PAYOUT_CONFLICT", "O2")}, "exceptions for a failed payout PayRail says it paid")
    paid = _funded() + [preq("o", "O1", "C1", 2_000_000, "2026-10-31T23:40:00Z"), psend("s", "O1", "accepted", "2026-10-31T23:40:02Z"),
                        plook("l", "O1", "rejected", "2026-11-01T10:00:00Z")]
    state, _ = replay(mod, paid)
    eq((mod.payout_status(state, "O1"), exc(mod, state)), ("PAID", {("PAYOUT_CONFLICT", "O1")}), "paid payout then rejected")


@CHECKS
def insufficient_payout_is_rejected(mod):
    state, cmds = replay(mod, _funded(1_000) + [preq("o", "O1", "C1", 1_001, "2026-10-30T12:00:00Z"), pretry("t", "O1", "2026-10-30T13:00:00Z")])
    eq((mod.payout_status(state, "O1"), cmds[1:], norm_bal(mod.balances(state))), ("REJECTED", [[], []], {"C1": {"available": 1_000, "held": 0}}), "rejected")


# ---------- dates and close ----------

@CHECKS
def accounting_date_is_lagos_time(mod):
    state, _ = replay(mod, [pin("a", "P1", "C1", "NGN", 100, "2026-10-31T23:30:00Z"), pin("b", "P2", "C1", "NGN", 7, "2026-10-31T22:59:59Z"),
                            pin("c", "P3", "C1", "NGN", 50, "2026-09-30T23:00:00Z")])
    eq((totals(mod, state, "2026-09"), totals(mod, state, "2026-10"), totals(mod, state, "2026-11")),
       ({}, {REC: 57, "customer:C1:available": -57}, {REC: 100, "customer:C1:available": -100}), "Lagos dates")


@CHECKS
def period_close_moves_late_lines_forward(mod):
    head = [pin("p", "P1", "C1", "NGN", 1_000_000, "2026-10-30T09:00:00Z"),
            sfile("f1", "B1", 1, "2026-10-31", [line("1", "PAYIN", "P1", 1_000_000), line("2", "FEE", "P1", 15_000)])]
    state, _ = replay(mod, head)
    october = totals(mod, state, "2026-10")
    n = len(mod.journal(state))
    state, _ = replay(mod, [close("c", "2026-10"), rev("x", "X1", "P1", "NGN", 200_000, "2026-10-31T20:00:00Z"),
                            sfile("f2", "B1", 2, "2026-10-31", [line("1", "PAYIN", "P1", 1_000_000), line("2", "FEE", "P1", 14_000)]),
                            pin("q", "P2", "C2", "NGN", 300, "2026-10-15T09:00:00Z")], state, {"p", "f1"})
    eq(totals(mod, state, "2026-10"), october, "a closed month changed")
    eq({x["accounting_date"] for x in mod.journal(state)[n:]}, {"2026-11-01"}, "late lines")
    eq(totals(mod, state, "2026-11"), {REC: -200_000 + 1_000 + 300, "customer:C1:available": 200_000, "fee_expense": -1_000,
                                       "customer:C2:available": -300}, "November")
    state, _ = replay(mod, [close("c2", "2026-11"), pin("z", "P3", "C1", "NGN", 9, "2026-10-01T09:00:00Z")], state, {"p", "f1", "c", "x", "f2", "q"})
    eq([x["accounting_date"] for x in mod.journal(state) if x["record_id"] == "z"], ["2026-12-01", "2026-12-01"], "after closing November")


# ---------- reconciliation ----------

@CHECKS
def ngn_mismatch_is_reported_not_forced(mod):
    state, _ = replay(mod, [pin("p", "P1", "C1", "NGN", 1_000_000, "2026-10-01T10:00:00Z"),
                            sfile("f", "B1", 1, "2026-10-02", [line("1", "PAYIN", "P1", 999_000)])])
    eq(exc(mod, state), {("SETTLEMENT_AMOUNT_MISMATCH", "P1")}, "exceptions")
    eq(recon(mod, state), (1_000_000, 999_000, {("PAYIN", "P1", -1_000)}), "reconciliation")
    eq(acct(mod, state, "fx_gain_loss"), 0, "NGN difference posted as FX")


@CHECKS
def random_orders_converge(mod):
    log = {r["record_id"]: r for r in sample_log()}
    pool = [log[k] for k in ("r02", "r07", "r09", "r12", "r13", "r15", "r18", "r23", "r24", "r25", "r27", "r28", "r29", "r30")]
    pool += [dict(log["r02"]), dict(log["r24"]), dict(log["r28"])]
    want_recon = (10_049_974, 9_354_700, {("PAYIN", "P9", 777_700), ("PAYIN_REVERSAL", "X2", 1_527_026), ("PAYIN_REVERSAL", "X3", 2_000_000),
                                         ("PAYIN_REVERSAL", "X4", 3_000_000), ("PAYOUT", "O1", -8_000_000)})
    want_exc = {("PAYIN_OUTCOME_UNKNOWN", "P4"), ("REVERSAL_EXCEEDS_PAYIN", "X4"), ("UNMATCHED_SETTLEMENT_LINE", "P9"), ("UNMATCHED_SETTLEMENT_LINE", "O1")}
    want_oct = {REC: 10_758_674, "customer:C1:available": -11_000_000, "fee_expense": 248_500, "fx_gain_loss": -7_174}
    want_nov = {REC: -708_700, "customer:C1:available": 3_000_000, "customer:C2:available": -2_291_300}

    def want(state, order):
        got = (norm_bal(mod.balances(state)), recon(mod, state), exc(mod, state), totals(mod, state, "2026-10"), totals(mod, state, "2026-11"))
        eq(got, ({"C1": {"available": 8_000_000, "held": 0}, "C2": {"available": 2_291_300, "held": 0}}, want_recon, want_exc, want_oct, want_nov),
           f"order {order}")

    all_orders(mod, pool, want, limit=60, prefix=[log["r01"], log["r08"]])
