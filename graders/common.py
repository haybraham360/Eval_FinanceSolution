"""Shared check registry for the deterministic graders."""
import signal
import traceback


class CheckTimeout(BaseException):
    pass


class Checks:
    def __init__(self):
        self.items = []

    def __call__(self, fn):
        self.items.append(fn)
        return fn

    def run(self, target, seconds=20):
        """Run every check independently; a crash or hang fails only that check."""

        def on_alarm(signum, frame):
            raise CheckTimeout()

        signal.signal(signal.SIGALRM, on_alarm)
        results = []
        for fn in self.items:
            signal.alarm(seconds)
            try:
                fn(target)
                results.append({"check": fn.__name__, "passed": True, "detail": ""})
            except CheckTimeout:
                results.append({"check": fn.__name__, "passed": False, "detail": f"timeout after {seconds}s"})
            except BaseException as exc:  # model code may raise anything, including our simulated Crash
                tail = traceback.format_exc(limit=-3)
                results.append({"check": fn.__name__, "passed": False, "detail": f"{type(exc).__name__}: {exc}\n{tail}"[:1200]})
            finally:
                signal.alarm(0)
        return results


def eq(actual, expected, label=""):
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
