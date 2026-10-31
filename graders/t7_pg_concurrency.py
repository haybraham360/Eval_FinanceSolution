"""Exact match per scenario. Answers are observed from a real server by verify_postgres.py."""
import json
from pathlib import Path

from common import Checks, eq

KIND = "json"
CHECKS = Checks()
EXPECTED = json.loads((Path(__file__).resolve().parent.parent / "reference" / "t7_pg_concurrency.json").read_text())


def scenario(name):
    def check(text):
        got = json.loads(text)[name]
        for field, want in EXPECTED[name].items():
            value = got[field]
            if isinstance(want, str):
                value = str(value).strip().upper() if want.isupper() or want[:2].isdigit() else str(value).strip()
            eq(value, want, f"{name}.{field}")
    check.__name__ = name
    return check


for key in EXPECTED:
    CHECKS(scenario(key))
