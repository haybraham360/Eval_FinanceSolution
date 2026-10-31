"""Grader for t1. World simulates the DB, the provider's 24h idempotency and lookup lag.
Fault injection enumerates every store/provider operation: a kill before it, a kill after it,
and a concurrent duplicate invocation at it."""
from collections import deque

from common import Checks, eq

CHECKS = Checks()
HOUR = 3600
T0 = 1_000_000


class Kill(BaseException):
    """A worker kill. BaseException, so `except Exception` cannot survive it."""


class Timeout(TimeoutError):
    pass


class World:
    def __init__(self, avail=10_000, lag=0, sends=None, lookups=None):
        self.rows, self.avail, self.held = {}, avail, 0
        self.start = avail
        self.now = T0
        self.lag = lag
        self.script = deque(sends or [])  # "ok" | "reject" | "timeout_landed" | "timeout_lost"
        self.lookup_script = deque(lookups or [])  # "timeout" | "ok"
        self.refs = {}  # reference -> {"first": t, "landed": t, "res": dict}
        self.moved = []
        self.counter = 0
        self.hook = None  # called as hook(op, phase)

    def _op(self, name, fn):
        if self.hook:
            self.hook(name, "before")
        result = fn()
        if self.hook:
            self.hook(name, "after")
        return result

    # store
    def get_payout(self, pid):
        return self._op("get", lambda: dict(self.rows[pid]) if pid in self.rows else None)

    def reserve(self, pid, account, amount, dest):
        def go():
            if pid in self.rows:
                return "EXISTS"
            if self.avail < amount:
                return "INSUFFICIENT"
            self.avail -= amount
            self.held += amount
            self.rows[pid] = dict(payout_id=pid, account=account, amount_minor=amount, dest=dest, status="RESERVED")
            return "CREATED"
        return self._op("reserve", go)

    def update(self, pid, expected, new, **fields):
        assert new in ("RESERVED", "SENDING"), f"update to illegal status {new}"
        def go():
            if self.rows.get(pid, {}).get("status") != expected:
                return False
            self.rows[pid].update(fields, status=new)
            return True
        return self._op("update", go)

    def finish(self, pid, expected, outcome, **fields):
        assert outcome in ("PAID", "FAILED"), outcome
        def go():
            row = self.rows.get(pid)
            if not row or row["status"] != expected:
                return False
            self.held -= row["amount_minor"]
            if outcome == "FAILED":
                self.avail += row["amount_minor"]
            row.update(fields, status=outcome)
            return True
        return self._op("finish", go)

    # provider
    def _land(self, ref, dest, amount, rejected=False):
        self.counter += 1
        res = {"status": "rejected" if rejected else "accepted", "provider_id": f"p{self.counter}"}
        self.refs[ref] = {"first": self.now, "landed": self.now, "res": res}
        if not rejected:
            self.moved.append((ref, dest, amount, self.now))
        return res

    def send(self, ref, dest, amount):
        def go():
            known = self.refs.get(ref)
            if known and self.now - known["first"] < 24 * HOUR:
                behaviour = self.script.popleft() if self.script else "ok"
                if behaviour.startswith("timeout"):
                    raise Timeout()
                return dict(known["res"])
            behaviour = self.script.popleft() if self.script else "ok"
            if behaviour == "timeout_lost":
                raise Timeout()
            if behaviour == "timeout_landed":
                self._land(ref, dest, amount)
                raise Timeout()
            return dict(self._land(ref, dest, amount, rejected=behaviour == "reject"))
        return self._op("send", go)

    def lookup(self, ref):
        def go():
            if self.lookup_script and self.lookup_script.popleft() == "timeout":
                raise Timeout()
            known = self.refs.get(ref)
            if known and self.now >= known["landed"] + self.lag:
                return dict(known["res"])
            return None
        return self._op("lookup", go)


def call(mod, w, pid="po1", amount=4_000, now=None):
    mod.ProviderTimeout = TimeoutError
    w.now = T0 if now is None else now
    return mod.execute_payout(w, w, pid, "acct", amount, "dest", w.now)


def settle(mod, w, start, pid="po1"):
    """Keep retrying as the real scheduler would until the result is terminal."""
    for t in [start, start + 60, start + 1000, start + 2000, start + 26 * HOUR]:
        result = call(mod, w, pid, now=t)
        if result in ("PAID", "FAILED"):
            return result
    raise AssertionError(f"payout never terminal, last={result}")


def invariants(w, final, amount=4_000):
    if len(w.moved) > 1:
        raise AssertionError(f"customer paid {len(w.moved)} times: {w.moved}")
    eq(w.held, 0, "held funds after terminal state")
    if final == "PAID":
        eq(len(w.moved), 1, "PAID needs exactly one movement")
        eq(w.avail, w.start - amount, "available after PAID")
    else:
        eq(len(w.moved), 0, "FAILED while money left")
        eq(w.avail, w.start, "available after FAILED")


def op_count(mod, make_world):
    w = make_world()
    seen = [0]
    def hook(op, phase):
        if phase == "before":
            seen[0] += 1
    w.hook = hook
    call(mod, w)
    return seen[0]


def crash_matrix(mod, make_world, rerun_at):
    for k in range(op_count(mod, make_world) + 2):
        for phase in ("before", "after"):
            w = make_world()
            seen = [0]
            def hook(op, ph):
                if ph == "before":
                    seen[0] += 1
                if ph == phase and seen[0] - 1 == k:
                    w.hook = None
                    raise Kill()
            w.hook = hook
            try:
                call(mod, w)
            except Kill:
                pass
            w.hook = None
            invariants(w, settle(mod, w, rerun_at))


@CHECKS
def happy_path(mod):
    w = World()
    eq(call(mod, w), "PAID", "status")
    invariants(w, "PAID")


@CHECKS
def insufficient_sends_nothing_and_is_not_sticky(mod):
    w = World(avail=1_000)
    eq(call(mod, w), "INSUFFICIENT", "status")
    eq(w.moved, [], "moved")
    w.avail = 10_000
    w.start = 10_000
    eq(call(mod, w), "PAID", "after funds arrive")


@CHECKS
def rejected_releases_funds_and_stays_failed(mod):
    w = World(sends=["reject"])
    eq(call(mod, w), "FAILED", "status")
    invariants(w, "FAILED")
    eq(call(mod, w, now=T0 + 30 * HOUR), "FAILED", "repeat")
    invariants(w, "FAILED")


@CHECKS
def finished_payout_makes_no_money_moving_calls(mod):
    w = World()
    call(mod, w)
    calls = []
    w.hook = lambda op, ph: calls.append(op) if ph == "before" and op == "send" else None
    eq(call(mod, w, now=T0 + 30 * HOUR), "PAID", "repeat")
    eq(calls, [], "send calls after PAID")


@CHECKS
def timeout_keeps_funds_held(mod):
    w = World(sends=["timeout_lost"], lag=900)
    eq(call(mod, w), "PENDING", "status")
    eq((w.held, w.avail), (4_000, 6_000), "held/available")


@CHECKS
def lookup_timeout_is_pending(mod):
    w = World(sends=["timeout_lost"], lookups=["timeout", "timeout", "timeout", "timeout"], lag=900)
    call(mod, w)
    w.script.extend(["timeout_lost"] * 4)
    eq(call(mod, w, now=T0 + 5_000), "PENDING", "status when provider is down")
    eq(w.held, 4_000, "held")


@CHECKS
def lagging_landed_transfer_is_not_failed(mod):
    """Timeout, landed, invisible for 15 minutes. A retry at +14m cannot conclude anything."""
    w = World(sends=["timeout_landed", "timeout_lost"], lag=900)
    call(mod, w)
    result = call(mod, w, now=T0 + 840)
    eq(result in ("PENDING", "PAID"), True, f"status at +14m was {result}")
    invariants(w, settle(mod, w, T0 + 1000))
    eq(w.rows["po1"]["status"], "PAID", "final")


@CHECKS
def never_landed_fails_after_window_and_releases(mod):
    # Nothing ever lands. Re-sending is allowed while the reference is safe, so a design may stay
    # PENDING for hours, but it must reach FAILED once it stops sending. Retries run past 24h.
    w = World(sends=["timeout_lost"] * 500, lag=900)
    eq(call(mod, w), "PENDING", "first")
    eq(call(mod, w, now=T0 + 899), "PENDING", "still inside window")
    result, t = "PENDING", T0 + 899
    while result == "PENDING" and t < T0 + 30 * HOUR:
        t += 1800
        result = call(mod, w, now=t)
    eq(result, "FAILED", "after 30h with nothing landed")
    invariants(w, "FAILED")


@CHECKS
def window_runs_from_most_recent_send(mod):
    """A retry that re-sends at +14m lands then. Failing at +16m would strand money that left."""
    w = World(sends=["timeout_lost", "timeout_landed"], lag=900)
    call(mod, w)
    call(mod, w, now=T0 + 840)
    result = call(mod, w, now=T0 + 960)
    if w.moved:
        eq(result in ("PENDING", "PAID"), True, f"failed a transfer that landed; status {result}")
    invariants(w, settle(mod, w, T0 + 2000))


@CHECKS
def landed_then_retry_after_provider_forgot(mod):
    """Timeout that landed, retried 25h later. A blind re-send pays twice."""
    w = World(sends=["timeout_landed"], lag=900)
    call(mod, w)
    eq(call(mod, w, now=T0 + 25 * HOUR), "PAID", "status")
    invariants(w, "PAID")


@CHECKS
def kill_at_every_operation_retry_soon(mod):
    crash_matrix(mod, lambda: World(lag=600), T0 + 60)


@CHECKS
def kill_at_every_operation_retry_after_24h(mod):
    crash_matrix(mod, lambda: World(lag=600), T0 + 25 * HOUR)


@CHECKS
def duplicate_invocation_at_every_operation(mod):
    for k in range(op_count(mod, lambda: World()) + 1):
        w = World()
        seen = [0]
        results = []
        def hook(op, ph):
            if ph == "before":
                seen[0] += 1
                if seen[0] - 1 == k:
                    w.hook = None
                    results.append(call(mod, w))
        w.hook = hook
        outer = call(mod, w)
        eq(outer == w.rows["po1"]["status"] or outer == "PENDING", True, f"returned {outer}, stored {w.rows['po1']['status']}")
        invariants(w, settle(mod, w, T0 + 60))


@CHECKS
def returns_stored_truth_when_another_worker_wins(mod):
    """A rival worker finishes the payout as FAILED while this one is inside send."""
    w = World()
    w.script.extend(["ok"])
    def hook(op, ph):
        if op == "send" and ph == "after":
            w.hook = None
            row = w.rows["po1"]
            w.moved.clear()
            w.held -= row["amount_minor"]
            w.avail += row["amount_minor"]
            row["status"] = "FAILED"
    w.hook = hook
    eq(call(mod, w), "FAILED", "returned status")
