"""Exact comparison of predicted PostgreSQL behaviour with answers observed on a real server."""
import json
from pathlib import Path

from common import Checks, eq


def same(got, want, label):
    if want is None or isinstance(want, bool):
        eq(got, want, label)
    else:
        text = str(got).lower() if isinstance(got, bool) else str(got)
        eq(text.strip(), str(want), label)


def build(task):
    expected = json.loads((Path(__file__).resolve().parent.parent / "reference" / f"{task}.json").read_text())
    checks = Checks()

    def scenario(name, want):
        def check(text):
            got = json.loads(text)[name]
            if isinstance(want, dict):
                for field, value in want.items():
                    same(got[field], value, f"{name}.{field}")
            else:
                same(got, want, name)
        check.__name__ = name
        return check

    for name, want in expected.items():
        if not name.startswith("_"):
            checks(scenario(name, want))
    return checks
