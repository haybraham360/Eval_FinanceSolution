"""Exact answers from the statute (reference/t11_sources.md). Numbers compare within one kobo."""
import json
from pathlib import Path

from common import Checks, eq

KIND = "json"
CHECKS = Checks()
EXPECTED = json.loads((Path(__file__).resolve().parent.parent / "reference" / "t12_ng_tax_interactions.json").read_text())


def item(name, want):
    def check(text):
        got = json.loads(text)[name]
        for field, value in want.items():
            if isinstance(value, str):
                eq(str(got[field]).strip().lower(), value, f"{name}.{field}")
            elif abs(float(str(got[field]).replace(",", "").replace("₦", "")) - value) > 0.01:
                raise AssertionError(f"{name}.{field}: expected {value}, got {got[field]!r}")
    check.__name__ = name
    return check


for key, value in EXPECTED.items():
    if not key.startswith("_"):
        CHECKS(item(key, value))
