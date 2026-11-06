#!/usr/bin/env python3
"""Proves that every committed results/<run>/scores.json still matches what the current graders give
for the committed raw outputs. It re-grades in memory and writes nothing, makes no model call, and needs
no API key.

    python scripts/verify_committed_results.py [run_id ...]

Outcomes are compared (score, pass, error and each check's pass/fail), not bytes: the check detail text
contains tracebacks with machine-specific absolute paths. Exits 1 on any difference.
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import run_eval  # noqa: E402  (reuses the harness's own grading path)


def outcome(row):
    return (round(row["score"], 9), row["passed"], (row["error"] or "")[:60], [(c["check"], c["passed"]) for c in row["checks"]])


def verify(run_dir):
    scores = json.loads((run_dir / "scores.json").read_text())
    committed = {(r["model"], r["task"], r["trial"]): r for r in scores}
    paths = sorted((run_dir / "raw").glob("*/*/trial_*.json"))
    with ThreadPoolExecutor() as pool:
        fresh = list(pool.map(run_eval.grade_record, paths))
    problems = []
    for row in fresh:
        key = (row["model"], row["task"], row["trial"])
        old = committed.pop(key, None)
        if old is None:
            problems.append(f"{key}: raw output has no row in scores.json")
        elif outcome(old) != outcome(row):
            problems.append(f"{key}: committed {outcome(old)[:3]} but the current graders give {outcome(row)[:3]}")
    problems += [f"{k}: row in scores.json has no raw output" for k in committed]
    return len(paths), problems


def main():
    runs = sys.argv[1:] or sorted(p.name for p in (ROOT / "results").iterdir() if (p / "scores.json").exists() and (p / "raw").is_dir())
    bad = 0
    for run in runs:
        n, problems = verify(ROOT / "results" / run)
        print(f"{'OK  ' if not problems else 'FAIL'} {run}: {n} trials re-graded" + ("" if not problems else f", {len(problems)} differ"))
        for p in problems[:20]:
            print(f"     {p}")
        bad += len(problems)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
