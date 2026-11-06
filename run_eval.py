#!/usr/bin/env python3
"""ledger-eval harness.

  python run_eval.py run      call the models, save raw outputs, grade them, write the summary
  python run_eval.py regrade  re-grade the saved raw outputs (no API key, no cost)

Trials that already have a saved output are skipped, so an interrupted run can be resumed.
"""
import argparse
import concurrent.futures as cf
import json
import os
import random
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import certifi

import evalcore
from evalcore import ROOT, TASKS

URL = "https://openrouter.ai/api/v1/chat/completions"
DAILY_LIMIT_HIT = threading.Event()  # OpenRouter's free daily quota: retrying only burns more of it
COST_SEEN = threading.Event()  # --free-only: set if any response reports a non-zero cost, which stops the run
TLS = ssl.create_default_context(cafile=certifi.where())  # python.org builds on macOS ship with no CA bundle
MAX_TOKENS = 40000
SYSTEM = (
    "You are a senior backend engineer at a regulated payments company. "
    "Follow the task exactly. Your final answer must be in one fenced code block, "
    "in the language the task asks for, and it must be complete."
)


def load_env():
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


def call_model(model, prompt, api_key):
    body = {
        "model": model["id"],
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
        "max_tokens": MAX_TOKENS,
        "usage": {"include": True},
        **model.get("params", {}),
    }
    request = urllib.request.Request(
        URL,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "X-Title": "ledger-eval"},
    )
    last_error = None
    rate_limited = 0
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=900, context=TLS) as resp:
                payload = json.load(resp)
            choice = (payload.get("choices") or [{}])[0]
            if "error" in payload or not (choice.get("message") or {}).get("content"):
                last_error = json.dumps(payload)[:500]
            else:
                return payload
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code}: {exc.read()[:300]!r}"
            if exc.code in (400, 401, 402, 403, 404):
                break
            if exc.code == 429 and "per-day" in last_error:
                DAILY_LIMIT_HIT.set()
                break
            if exc.code == 429:  # upstream rate limit: pause, and give up after two, so free quota is not burned
                rate_limited += 1
                if rate_limited >= 2:
                    break
                time.sleep(60)
                continue
        except Exception as exc:  # network failures and read timeouts are provider faults, so retry
            last_error = repr(exc)
        time.sleep(2**attempt + random.random())
    raise RuntimeError(last_error)


def call_cli(model, prompt):
    """Runs one trial through a logged-in `claude` CLI, with no tools, project, settings or history.
    The payload is reshaped to match OpenRouter's, so grading and reporting need no special case."""
    cmd = ["claude", "-p", "--model", model["id"], "--output-format", "json", "--system-prompt", SYSTEM, "--tools", "",
           "--setting-sources", "", "--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence"]
    if model.get("effort"):
        cmd += ["--effort", model["effort"]]
    last_error = None
    for attempt in range(3):
        with tempfile.TemporaryDirectory() as cwd:
            proc = subprocess.run(cmd, input=prompt, cwd=cwd, capture_output=True, text=True, timeout=1500)
        try:
            out = json.loads(proc.stdout)
        except ValueError:
            out = {"is_error": True, "result": (proc.stdout + proc.stderr)[-400:]}
        if not out.get("is_error") and out.get("result"):
            usage = out.get("usage") or {}
            resolved = ",".join(out.get("modelUsage") or [model["id"]])
            return {
                "model": resolved,
                "provider": "claude-cli",
                "model_usage": out.get("modelUsage"),
                "choices": [{"finish_reason": "stop", "message": {"content": out["result"]}}],
                "usage": {"cost": 0, "notional_cost_usd": out.get("total_cost_usd"), "prompt_tokens": usage.get("input_tokens"), "completion_tokens": usage.get("output_tokens")},
            }
        last_error = str(out.get("result"))[:300]
        time.sleep(20 * (attempt + 1))
    raise RuntimeError(last_error)


def trial_path(run_dir, model, task, trial):
    return run_dir / "raw" / model["label"] / task / f"trial_{trial}.json"


def run_trial(run_dir, model, task, trial, api_key, free_only=False):
    path = trial_path(run_dir, model, task, trial)
    if path.exists():
        return "skipped"
    if COST_SEEN.is_set():
        return "not run: a response reported a non-zero cost, so the --free-only run stopped"
    if DAILY_LIMIT_HIT.is_set() and model.get("backend") != "cli":
        return "not run: OpenRouter daily limit reached, rerun the same --run-id later"
    started = time.time()
    prompt = evalcore.task_prompt(task)
    payload = call_cli(model, prompt) if model.get("backend") == "cli" else call_model(model, prompt, api_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "model_label": model["label"],
        "requested_model": model["id"],
        "params": model.get("params", {}),
        "task": task,
        "trial": trial,
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "latency_s": round(time.time() - started, 1),
        "system": SYSTEM,
        "response": payload,
    }
    path.write_text(json.dumps(record, indent=1))
    if free_only and (payload.get("usage") or {}).get("cost"):
        COST_SEEN.set()
        raise RuntimeError(f"response reported cost {payload['usage']['cost']}; stopping the --free-only run")
    return "ok"


def grade_record(path):
    record = json.loads(path.read_text())
    choice = record["response"]["choices"][0]
    text = choice["message"]["content"]
    kind = evalcore.task_kind(record["task"])
    answer = evalcore.extract_answer(text, kind)
    usage = record["response"].get("usage") or {}
    row = {
        "model": record["model_label"],
        "resolved_model": record["response"].get("model"),
        "provider": record["response"].get("provider"),
        "task": record["task"],
        "trial": record["trial"],
        "utc": record["utc"],
        "finish_reason": choice.get("finish_reason"),
        "cost_usd": usage.get("cost") or 0,
        "tokens_in": usage.get("prompt_tokens"),
        "tokens_out": usage.get("completion_tokens"),
    }
    if answer is None:
        return {**row, "score": 0.0, "passed": False, "checks": [], "error": "no fenced code block in output"}
    return {**row, **evalcore.grade_text(record["task"], answer)}


def summarize(run_dir, tiers):
    paths = sorted((run_dir / "raw").glob("*/*/trial_*.json"))
    if not paths:
        sys.exit(f"No saved trials in {run_dir}.")
    with cf.ThreadPoolExecutor(max_workers=os.cpu_count()) as pool:
        rows = list(pool.map(grade_record, paths))
    (run_dir / "scores.json").write_text(json.dumps(rows, indent=1))

    by_model = defaultdict(list)
    by_task_model = defaultdict(list)
    fails = defaultdict(lambda: defaultdict(int))
    for row in rows:
        by_model[row["model"]].append(row)
        by_task_model[(row["task"], row["model"])].append(row)
        for check in row["checks"]:
            if not check["passed"]:
                fails[row["task"]][check["check"]] += 1

    models = sorted(by_model, key=lambda m: -sum(r["score"] for r in by_model[m]) / len(by_model[m]))
    lines = [f"# Results for run `{run_dir.name}`", ""]
    lines += ["| Model | Tier | Trials | Full pass rate | pass^k (tasks passed every trial) | pass@k (tasks passed once) | Mean score | Trial score SD (per task, mean) | Cost |", "|---|---|---|---|---|---|---|---|---|"]
    tasks = sorted({r["task"] for r in rows})
    for model in models:
        mine = by_model[model]
        groups = [by_task_model[(t, model)] for t in tasks if by_task_model[(t, model)]]
        allpass = sum(all(r["passed"] for r in g) for g in groups)
        anypass = sum(any(r["passed"] for r in g) for g in groups)
        sds = [_sd([r["score"] for r in g]) for g in groups]
        lines.append(
            f"| {model} | {tiers.get(model, '?')} | {len(mine)} | {sum(r['passed'] for r in mine) / len(mine):.0%} "
            f"| {allpass}/{len(groups)} | {anypass}/{len(groups)} | {sum(r['score'] for r in mine) / len(mine):.1%} "
            f"| {sum(sds) / len(sds):.3f} | ${sum(r['cost_usd'] for r in mine):.2f} |"
        )
    lines += ["", "## Mean score by task (full passes / trials)", "", "| Task | " + " | ".join(models) + " |", "|---" * (len(models) + 1) + "|"]
    for task in tasks:
        cells = []
        for model in models:
            g = by_task_model[(task, model)]
            cells.append(f"{sum(r['score'] for r in g) / len(g):.0%} ({sum(r['passed'] for r in g)}/{len(g)})" if g else "-")
        lines.append(f"| {task} | " + " | ".join(cells) + " |")
    lines += ["", "## Failing checks, across all models and trials", ""]
    for task in tasks:
        lines.append(f"- **{task}**: " + (", ".join(f"`{c}` x{n}" for c, n in sorted(fails[task].items(), key=lambda kv: -kv[1])) or "none"))
    resolved = sorted({f"{r['model']} -> {r['resolved_model']} via {r['provider']}" for r in rows})
    errors = [r for r in rows if r["error"] or r["finish_reason"] not in ("stop", "end_turn", "tool_calls")]
    lines += ["", "## Resolved models", ""] + [f"- {x}" for x in resolved]
    lines += ["", f"## Trials with no gradable code or an unusual stop ({len(errors)})", ""]
    lines += [f"- {r['model']} / {r['task']} / trial {r['trial']}: finish={r['finish_reason']} error={str(r['error'])[:160]}" for r in errors]
    (run_dir / "summary.md").write_text("\n".join(lines) + "\n")
    export_transcripts(run_dir, rows)
    print("\n".join(lines))


def export_transcripts(run_dir, rows):
    """Writes the lowest-scoring trial of every model/task pair, so each task shows a failure where one exists."""
    out = ROOT / "transcripts" / run_dir.name
    worst = {}
    for row in rows:
        key = (row["model"], row["task"])
        if key not in worst or row["score"] < worst[key]["score"]:
            worst[key] = row
    for (model, task), row in worst.items():
        record = json.loads((run_dir / "raw" / model / task / f"trial_{row['trial']}.json").read_text())
        failed = [c for c in row["checks"] if not c["passed"]]
        lines = [f"# {model} / {task} / trial {row['trial']}", "", f"- Requested: `{record['requested_model']}`, resolved: `{row['resolved_model']}`, provider: {row['provider']}",
                 f"- Run at {row['utc']} with params `{json.dumps(record['params'])}`", f"- Score {row['score']:.0%}, full pass: {row['passed']}, finish: {row['finish_reason']}, error: {row['error']}", "", "## Failed checks", ""]
        lines += [f"### `{c['check']}`\n\n```\n{c['detail']}\n```\n" for c in failed] or ["None.\n"]
        lines += [f"## Prompt\n\nSee `tasks/{task}/prompt.md`.\n", "## Model output\n", record["response"]["choices"][0]["message"]["content"]]
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{model}__{task}.md").write_text("\n".join(lines) + "\n")


def _sd(values):
    mean = sum(values) / len(values)
    return (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5


def verify_free(models, tasks, trials, api_key):
    """--free-only: abort unless every selected model is an OpenRouter `:free` entry that OpenRouter
    prices at exactly 0 right now. Uses only the free metadata endpoints, which make no model call."""
    print(f"Free-only plan, checked {datetime.now(timezone.utc).isoformat(timespec='seconds')}:")
    with urllib.request.urlopen("https://openrouter.ai/api/v1/models", timeout=60, context=TLS) as resp:
        listed = {m["id"]: m for m in json.load(resp)["data"]}
    problems = []
    for m in models:
        entry = listed.get(m["id"])
        prices = (entry or {}).get("pricing") or {}
        paid = {k: v for k, v in prices.items() if Decimal(str(v)) != 0}
        if m.get("backend") == "cli":
            problems.append(f"{m['label']} is a CLI model, not an OpenRouter free model")
        elif m.get("tier") != "free" or not m["id"].endswith(":free"):
            problems.append(f"{m['label']} ({m['id']}) is not a :free entry")
        elif entry is None:
            problems.append(f"{m['label']} ({m['id']}) is not listed by OpenRouter today")
        elif not prices or paid:
            problems.append(f"{m['label']} ({m['id']}) has non-zero pricing {paid or prices}")
        print(f"  {m['label']}: {m['id']} pricing={prices or 'missing'}")
    request = urllib.request.Request("https://openrouter.ai/api/v1/key", headers={"Authorization": f"Bearer {api_key}"})
    with urllib.request.urlopen(request, timeout=60, context=TLS) as resp:
        key = json.load(resp).get("data", {})
    daily = key.get("free_model_daily_requests") or {}
    jobs = len(models) * len(tasks) * trials
    print(f"  tasks: {len(tasks)}, trials per task: {trials}, model calls: {jobs}")
    print(f"  key: free tier={key.get('is_free_tier')}, lifetime usage=${key.get('usage')}, free requests left today={daily.get('remaining')}/{daily.get('limit')}")
    if daily.get("remaining") is not None and daily["remaining"] < jobs:
        print(f"  warning: only {daily['remaining']} free requests left today; the rest will stop at the daily limit and can resume later")
    if daily.get("remaining") == 0:
        problems.append("no free requests left today")
    if problems:
        sys.exit("Aborting, nothing was called:\n  " + "\n  ".join(problems))
    print("  cost classification: FREE (OpenRouter :free models priced at 0; any response reporting a cost stops the run)")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["run", "regrade"])
    parser.add_argument("--run-id", default=None, help="folder under results/ (default: today's date for run, final for regrade)")
    parser.add_argument("--models", default=None, help="comma-separated labels from models.json (default: all)")
    parser.add_argument("--tasks", default=None, help="comma-separated task ids (default: all)")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--free-only", action="store_true", help="abort unless every model is an OpenRouter :free model priced at 0 today")
    parser.add_argument("--dry-run", action="store_true", help="print the plan (and the --free-only check) without calling any model")
    args = parser.parse_args()

    models = json.loads((ROOT / "models.json").read_text())
    tiers = {m["label"]: m["tier"] for m in models}
    default_id = "final" if args.command == "regrade" else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    run_dir = ROOT / "results" / (args.run_id or default_id)

    if args.command == "run":
        load_env()
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if args.models:
            wanted = set(args.models.split(","))
            models = [m for m in models if m["label"] in wanted]
        if not api_key:
            models = [m for m in models if m.get("backend") == "cli"]
            print("OPENROUTER_API_KEY is not set, so only CLI models will run.")
        if not models:
            sys.exit("No models to run. Set OPENROUTER_API_KEY in .env or choose CLI models.")
        tasks = args.tasks.split(",") if args.tasks else TASKS
        unknown = [t for t in tasks if t not in evalcore.ALL_TASKS]
        if unknown:
            sys.exit(f"Unknown task ids: {unknown}")
        if args.free_only:
            if not api_key:
                sys.exit("--free-only needs OPENROUTER_API_KEY.")
            verify_free(models, tasks, args.trials, api_key)
        if args.dry_run:
            print(f"Dry run: {[m['label'] for m in models]} x {len(tasks)} tasks x {args.trials} trials -> {run_dir}. Nothing was called.")
            return
        jobs = [(m, t, n) for m in models for t in tasks for n in range(1, args.trials + 1)]
        print(f"{len(jobs)} trials -> {run_dir}", flush=True)
        failed = 0
        with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(run_trial, run_dir, m, t, n, api_key, args.free_only): (m["label"], t, n) for m, t, n in jobs}
            for i, future in enumerate(cf.as_completed(futures), 1):
                try:
                    status = future.result()
                except Exception as exc:
                    failed += 1
                    status = f"ERROR {str(exc)[:200]}"
                print(f"[{i}/{len(jobs)}] {futures[future]} {status}", flush=True)
        if failed:
            print(f"{failed} trials hit provider errors and were not recorded. Rerun with the same --run-id to retry them.")
    summarize(run_dir, tiers)


if __name__ == "__main__":
    main()
