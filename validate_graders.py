#!/usr/bin/env python3
"""Proves the graders before any model is judged by them.

1. Every reference solution scores 100%.
2. Every independent alternative solution in reference_alt/ scores 100% (no false fails).
3. Every deliberately wrong solution in mutants/ fails, and fails the specific check it targets (no false passes).
"""
import sys
from pathlib import Path

import evalcore
from evalcore import ROOT, TASKS

bad = 0
only = sys.argv[1:] or TASKS
mutant_total = 0


def show(label, ok, detail=""):
    global bad
    bad += 0 if ok else 1
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")


for task in only:
    print(f"\n== {task}")
    ext = "py" if evalcore.task_kind(task) == "python" else "json"
    for path in [ROOT / "reference" / f"{task}.{ext}"] + sorted((ROOT / "reference_alt").glob(f"{task}*.{ext}")):
        res = evalcore.grade_file(task, path)
        missed = [f"{c['check']}: {c['detail'][:500]}" for c in res["checks"] if not c["passed"]]
        show(f"{path.parent.name}/{path.stem}", res["passed"], f"{len(res['checks'])} checks {res['error'] or ''} {missed or ''}")
    mutants = sorted((ROOT / "mutants" / task).glob(f"*.{ext}"))
    for path in mutants:
        text = path.read_text()
        if ext == "py":
            expected = text.splitlines()[0].split("expect-fail:")[1].strip()
        else:
            expected = __import__("json").loads(text)["_expect_fail"]
        res = evalcore.grade_file(task, path)
        failed = {c["check"] for c in res["checks"] if not c["passed"]}
        mutant_total += 1
        show(f"mutant {path.stem}", not res["passed"] and expected in failed, f"score {res['score']:.0%}; failed: {sorted(failed)}{' ' + res['error'] if res['error'] else ''}")

print(f"\n{'ALL GOOD' if not bad else str(bad) + ' PROBLEMS'}: {mutant_total} mutants across {len(only)} tasks")
sys.exit(1 if bad else 0)
