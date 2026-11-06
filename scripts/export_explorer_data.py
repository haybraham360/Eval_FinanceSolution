#!/usr/bin/env python3
"""Builds the Ledger-Eval Explorer data bundle from the files committed in this repository.

    python scripts/export_explorer_data.py [--root DIR] [--out FILE]

Everything the website shows comes from here, and every value records the repository file it came from.
Nothing is typed in by hand: tasks come from tasks/*, results from results/<run>/scores.json (cross-checked
against results/<run>/raw), task descriptions and limitations from README.md, statutory references from
reference/t11_sources.md, and the commit from git or the GitHub Actions environment.

Exits with status 1, writing nothing, if the data is malformed or contradictory, so a broken push can
never replace the last good deployment with misleading figures. Standard library only.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
ROW_FIELDS = {"model": str, "task": str, "trial": int, "utc": str, "score": (int, float), "passed": bool, "checks": list}


class DataError(Exception):
    pass


# ---------- git and provenance ----------

def _git(root, *args):
    try:
        out = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def repo_identity(root):
    """(owner/repo, branch) from GitHub Actions, else from the git remote."""
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        remote = _git(root, "remote", "get-url", "origin") or ""
        m = re.search(r"github\.com[:/]([^/]+/[^/.]+?)(?:\.git)?$", remote)
        repo = m.group(1) if m else None
    branch = os.environ.get("GITHUB_REF_NAME") or _git(root, "rev-parse", "--abbrev-ref", "HEAD") or None
    if branch == "HEAD":  # detached checkout
        branch = None
    return repo, branch


def commit_info(root, warnings):
    sha = os.environ.get("EXPLORER_COMMIT_SHA") or os.environ.get("GITHUB_SHA") or _git(root, "rev-parse", "HEAD")
    if not sha:
        raise DataError("cannot determine the commit SHA: not a git checkout and GITHUB_SHA is not set")
    date = _git(root, "log", "-1", "--format=%cI", sha)
    if not date:
        warnings.append(f"Commit date for {sha[:7]} is not available in this checkout.")
    dirty = _git(root, "status", "--porcelain", "--", "tasks", "results", "transcripts", "reference", "README.md", "models.json")
    if dirty:
        warnings.append("Built from a working tree with uncommitted changes, so this is a local preview, not a published snapshot.")
    return sha, date, bool(dirty)


# ---------- README ----------

def _md_cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def readme_tasks(readme):
    """Task rows from README tables, keyed by task id, with the category heading they sit under.
    A row counts when its first cell is a backticked id: | `t1_payout_executor` | What | Why |."""
    out = {}
    category = None
    header = None
    for line in readme.splitlines():
        h = re.match(r"^###\s+(?:\d+\.\s*)?(.+?)\s*(?:\(.*\))?\s*$", line)
        if h:
            category, header = h.group(1).strip(), None
            continue
        if line.startswith("## "):
            category, header = None, None
            continue
        if not line.strip().startswith("|"):
            header = None if not line.strip() else header
            continue
        cells = _md_cells(line)
        if header is None:
            header = cells
            continue
        m = re.fullmatch(r"`([A-Za-z0-9_]+)`", cells[0]) if cells else None
        if m and category:
            row = dict(zip(header[1:], cells[1:]))
            out[m.group(1)] = {"category": category, "tests": row.get("What It Tests"), "challenge": row.get("What Makes It Challenging")}
    return out


def readme_section_bullets(readme, title_pattern):
    lines = readme.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("## ") and re.search(title_pattern, line, re.I):
            bullets = []
            for nxt in lines[i + 1:]:
                if nxt.startswith("## "):
                    break
                if re.match(r"^\s*[*-]\s+", nxt):
                    bullets.append(re.sub(r"^\s*[*-]\s+", "", nxt).strip())
            return line[3:].strip(), bullets
    return None, []


def readme_intro(readme):
    """The first prose paragraphs after the title, up to the first rule or heading."""
    paras, buf = [], []
    for line in readme.splitlines()[1:]:
        if line.startswith("#") or line.strip() == "---":
            if paras or buf:
                break
            continue
        if line.strip():
            buf.append(line.strip())
        elif buf:
            paras.append(" ".join(buf))
            buf = []
    if buf:
        paras.append(" ".join(buf))
    return paras[:3]


# ---------- statutory sources ----------

def _expand_items(text):
    items = []
    for part in re.split(r",|\band\b", text):
        part = part.strip()
        m = re.fullmatch(r"([A-Z]+)(\d+)\s*-\s*([A-Z]*)(\d+)", part)
        if m:
            items += [f"{m.group(1)}{n}" for n in range(int(m.group(2)), int(m.group(4)) + 1)]
        elif re.fullmatch(r"[A-Z]+\d+", part):
            items.append(part)
    return items


def statutory_sources(path):
    """{task_id: {check_id: {"provision", "rule"}}} from the tables in reference/t11_sources.md."""
    out = {}
    if not path.exists():
        return out
    task = None
    header = None
    for line in path.read_text().splitlines():
        m = re.match(r"^#\s+Sources for (t\d+)", line)
        if m:
            task, header = m.group(1), None
            continue
        if not line.strip().startswith("|") or task is None:
            header = None
            continue
        cells = _md_cells(line)
        if header is None:
            header = cells
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        row = dict(zip(header, cells))
        for item in _expand_items(row.get("Items", "")):
            out.setdefault(task, {})[item] = {"provision": row.get("Provision"), "rule": row.get("Rule")}
    return out


# ---------- tasks ----------

def task_order(p):
    name = getattr(p, "name", p)
    m = re.match(r"t(\d+)_", name)
    return (int(m.group(1)) if m else 10**9, name)


def load_tasks(root, readme_rows, warnings):
    tasks = []
    tdir = root / "tasks"
    if not tdir.is_dir():
        raise DataError("tasks/ is missing")
    for d in sorted((p for p in tdir.iterdir() if p.is_dir()), key=task_order):
        meta_path, prompt_path = d / "meta.json", d / "prompt.md"
        if not meta_path.exists() or not prompt_path.exists():
            raise DataError(f"{d.relative_to(root)} needs both meta.json and prompt.md")
        try:
            meta = json.loads(meta_path.read_text())
        except ValueError as exc:
            raise DataError(f"{meta_path.relative_to(root)} is not valid JSON: {exc}")
        if not isinstance(meta.get("title"), str) or meta.get("kind") not in ("python", "json"):
            raise DataError(f"{meta_path.relative_to(root)} needs a string title and kind python or json")
        rd = readme_rows.get(d.name)
        if rd is None:
            warnings.append(f"Task {d.name} is not described in README.md, so it has no category or plain-language summary.")
        grader = root / "graders" / f"{d.name}.py"
        refs = sorted(str(p.relative_to(root)) for p in (root / "reference").glob(f"{d.name}*")) if (root / "reference").is_dir() else []
        mutants = sorted((root / "mutants" / d.name).glob("*")) if (root / "mutants" / d.name).is_dir() else []
        tasks.append({
            "id": d.name,
            "title": meta["title"],
            "kind": meta["kind"],
            "experimental": bool(meta.get("experimental")),
            "category": rd["category"] if rd else None,
            "tests": rd["tests"] if rd else None,
            "challenge": rd["challenge"] if rd else None,
            "prompt": prompt_path.read_text(),
            "sourcePath": str(prompt_path.relative_to(root)),
            "metaPath": str(meta_path.relative_to(root)),
            "describedIn": "README.md" if rd else None,
            "graderPath": str(grader.relative_to(root)) if grader.exists() else None,
            "referencePaths": refs,
            "mutantCount": len([m for m in mutants if m.is_file()]),
            "alternativePaths": sorted(str(p.relative_to(root)) for p in (root / "reference_alt").glob(f"{d.name}*")) if (root / "reference_alt").is_dir() else [],
        })
    if not tasks:
        raise DataError("no tasks found under tasks/")
    return tasks


# ---------- results ----------

def _first_line(text, limit=300):
    line = (text or "").strip().splitlines()[0] if (text or "").strip() else ""
    return line[:limit]


def _check_rows(rows, rel):
    seen = set()
    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            raise DataError(f"{rel} row {i} is not an object")
        for k, t in ROW_FIELDS.items():
            if k not in r:
                raise DataError(f"{rel} row {i} is missing '{k}'")
            if not isinstance(r[k], t) or (t is int and isinstance(r[k], bool)):
                raise DataError(f"{rel} row {i} field '{k}' has the wrong type ({type(r[k]).__name__})")
        if not 0 <= r["score"] <= 1:
            raise DataError(f"{rel} row {i} score {r['score']} is outside 0..1")
        key = (r["model"], r["task"], r["trial"])
        if key in seen:
            raise DataError(f"{rel} lists {key} twice")
        seen.add(key)
        for c in r["checks"]:
            if not isinstance(c, dict) or not isinstance(c.get("check"), str) or not isinstance(c.get("passed"), bool):
                raise DataError(f"{rel} row {i} has a malformed check entry")
        if r["checks"]:
            done = sum(c["passed"] for c in r["checks"])
            if abs(done / len(r["checks"]) - r["score"]) > 1e-9:
                raise DataError(f"{rel} {key}: score {r['score']} contradicts {done}/{len(r['checks'])} passed checks")
            if r["passed"] != (done == len(r["checks"])):
                raise DataError(f"{rel} {key}: 'passed' contradicts its checks")
        elif r["passed"] or r["score"] != 0:
            raise DataError(f"{rel} {key}: a trial with no checks must score 0 and not pass")
        try:
            datetime.fromisoformat(r["utc"].replace("Z", "+00:00"))
        except ValueError:
            raise DataError(f"{rel} {key}: utc '{r['utc']}' is not ISO-8601")


def _transcript_trial(path):
    head = path.read_text().splitlines()[0] if path.exists() else ""
    m = re.search(r"/ trial (\d+)\s*$", head)
    return int(m.group(1)) if m else None


def load_runs(root, tasks, models_cfg, sources, warnings):
    rdir = root / "results"
    task_ids = {t["id"] for t in tasks}
    core = sorted(t["id"] for t in tasks if not t["experimental"])
    cats = {t["id"]: t["category"] for t in tasks}
    cfg = {m["label"]: m for m in models_cfg}
    runs = []
    if not rdir.is_dir():
        return runs
    for d in sorted(p for p in rdir.iterdir() if p.is_dir()):
        scores = d / "scores.json"
        rel = str(scores.relative_to(root))
        if not scores.exists():
            warnings.append(f"results/{d.name} has no scores.json, so it is not shown. Run `python run_eval.py regrade --run-id {d.name}`.")
            continue
        try:
            rows = json.loads(scores.read_text())
        except ValueError as exc:
            raise DataError(f"{rel} is not valid JSON: {exc}")
        if not isinstance(rows, list) or not rows:
            raise DataError(f"{rel} must be a non-empty list of trial rows")
        _check_rows(rows, rel)

        raw_dir = d / "raw"
        raw_files = {}
        if raw_dir.is_dir():
            for p in raw_dir.glob("*/*/trial_*.json"):
                raw_files[(p.parts[-3], p.parts[-2], int(p.stem.split("_")[1]))] = p
            keys = {(r["model"], r["task"], r["trial"]) for r in rows}
            missing = sorted(keys - set(raw_files))
            extra = sorted(set(raw_files) - keys)
            if missing:
                raise DataError(f"{rel} grades trials with no raw output: {missing[:5]}")
            if extra:
                raise DataError(f"{d.relative_to(root)}/raw has trials that {rel} does not grade: {extra[:5]}. Re-run regrade.")
        else:
            warnings.append(f"results/{d.name} has no raw/ outputs, so its scores cannot be cross-checked.")

        unknown_tasks = sorted({r["task"] for r in rows} - task_ids)
        if unknown_tasks:
            warnings.append(f"Run {d.name} has results for tasks that no longer exist in tasks/: {unknown_tasks}.")

        by_model = defaultdict(list)
        for r in rows:
            by_model[r["model"]].append(r)

        models = []
        for label in sorted(by_model):
            mine = by_model[label]
            if label not in cfg:
                warnings.append(f"Run {d.name}: model '{label}' is not in models.json.")
            per_task = defaultdict(list)
            for r in mine:
                per_task[r["task"]].append(r)
            settings = _settings(root, raw_files, label, mine, cfg.get(label))
            task_rows = []
            for task, rs in sorted(per_task.items(), key=lambda kv: task_order(kv[0])):
                task_rows.append({"task": task, "trials": len(rs), "fullPasses": sum(r["passed"] for r in rs),
                                  "meanScore": sum(r["score"] for r in rs) / len(rs)})
            by_cat = defaultdict(list)
            for r in mine:
                by_cat[cats.get(r["task"]) or "Uncategorised"].append(r["score"])
            trial_counts = {len(rs) for rs in per_task.values()}
            complete = set(per_task) >= set(core) and len(trial_counts) == 1
            models.append({
                "label": label,
                "displayName": display_name(label, settings),
                "tier": (cfg.get(label) or {}).get("tier"),
                "trials": len(mine),
                "meanScore": sum(r["score"] for r in mine) / len(mine),
                "fullPasses": sum(r["passed"] for r in mine),
                "fullPassRate": sum(r["passed"] for r in mine) / len(mine),
                "tasksPassedEveryTrial": sum(all(r["passed"] for r in rs) for rs in per_task.values()),
                "tasksPassedOnce": sum(any(r["passed"] for r in rs) for rs in per_task.values()),
                "tasksAttempted": len(per_task),
                "trialsPerTask": sorted(trial_counts),
                "coversAllCoreTasks": set(per_task) >= set(core),
                "complete": complete,
                "byTask": task_rows,
                "byCategory": [{"category": c, "trials": len(v), "meanScore": sum(v) / len(v)} for c, v in sorted(by_cat.items())],
                "settings": settings,
                "sourcePath": rel,
            })

        failures = _failures(root, d, rows, raw_files, sources)
        utcs = sorted(r["utc"] for r in rows)
        complete_run = all(m["complete"] for m in models) and len({tuple(m["trialsPerTask"]) for m in models}) == 1
        runs.append({
            "id": d.name,
            "sourcePath": rel,
            "summaryPath": str((d / "summary.md").relative_to(root)) if (d / "summary.md").exists() else None,
            "firstTrialUtc": utcs[0],
            "lastTrialUtc": utcs[-1],
            "trials": len(rows),
            "checksRun": sum(len(r["checks"]) for r in rows),
            "tasks": sorted({r["task"] for r in rows}, key=task_order),
            "complete": complete_run,
            "models": models,
            "failures": failures,
            "errors": [{"model": r["model"], "task": r["task"], "trial": r["trial"], "error": _first_line(r.get("error")),
                        "finishReason": r.get("finish_reason")} for r in rows if r.get("error")],
        })
    return runs


def display_name(label, settings):
    """A readable model name derived from the recorded model IDs, never typed by hand.
    Picks the resolved ID that contains the requested ID (the CLI also reports a helper model), strips the
    vendor prefix, and turns 'claude-opus-5-5' into 'Claude Opus 5.5'. Falls back to the label."""
    requested = [r for r in settings["requested"] if r]
    resolved = settings["resolved"] or requested
    pick = next((x for x in resolved for q in requested if q.split("/")[-1].split(":")[0] in x), resolved[0] if resolved else label)
    free = pick.endswith(":free")
    base = pick.split("/")[-1].split(":")[0]
    words = []
    for part in base.split("-"):
        if re.fullmatch(r"a?\d+b|it|instruct|vl|preview", part, re.I):  # size and build tags: kept in the exact ID only
            continue
        if part.isdigit() and words and re.fullmatch(r"\d+(\.\d+)*", words[-1]):
            words[-1] += "." + part
        else:
            words.append(part if any(ch.isdigit() for ch in part) and not part.isdigit() else part.capitalize())
    name = " ".join(words) or label
    return f"{name} (free tier)" if free else name


def _settings(root, raw_files, label, rows, cfg):
    """Recorded settings for a model in one run, read from its raw outputs and models.json."""
    requested, resolved, providers, params, systems = set(), set(), set(), set(), set()
    for r in rows:
        if r.get("resolved_model"):
            resolved.update(x.strip() for x in str(r["resolved_model"]).split(",") if x.strip())
        if r.get("provider"):
            providers.add(r["provider"])
        p = raw_files.get((label, r["task"], r["trial"]))
        if p:
            rec = json.loads(p.read_text())
            requested.add(rec.get("requested_model"))
            params.add(json.dumps(rec.get("params", {}), sort_keys=True))
            if rec.get("system"):
                systems.add(rec["system"])
    return {
        "requested": sorted(x for x in requested if x),
        "resolved": sorted(resolved),
        "providers": sorted(providers),
        "params": sorted(params),
        "systemPrompt": sorted(systems)[0] if len(systems) == 1 else None,
        "backend": (cfg or {}).get("backend", "openrouter" if cfg else None),
        "effort": (cfg or {}).get("effort") or ((cfg or {}).get("params", {}).get("reasoning") or {}).get("effort"),
        "configPath": "models.json" if cfg else None,
    }


def _failures(root, run_dir, rows, raw_files, sources):
    """One entry per (model, task, check) that failed in at least one trial, with the grader's own message."""
    groups = {}
    trials = defaultdict(int)
    for r in rows:
        trials[(r["model"], r["task"])] += 1
    for r in rows:
        for c in r["checks"]:
            if c["passed"]:
                continue
            key = (r["model"], r["task"], c["check"])
            g = groups.setdefault(key, {"model": r["model"], "task": r["task"], "check": c["check"], "failedTrials": [],
                                        "message": _first_line(c.get("detail"))})
            g["failedTrials"].append(r["trial"])
    out = []
    for (model, task, check), g in sorted(groups.items()):
        tpath = root / "transcripts" / run_dir.name / f"{model}__{task}.md"
        ttrial = _transcript_trial(tpath)
        short = task.split("_")[0]
        ref = sources.get(short, {}).get(check)
        raw = raw_files.get((model, task, g["failedTrials"][0]))
        out.append({**g, "failedTrials": sorted(g["failedTrials"]), "trialsRun": trials[(model, task)],
                    "transcriptPath": str(tpath.relative_to(root)) if ttrial in g["failedTrials"] else None,
                    "transcriptTrial": ttrial if ttrial in g["failedTrials"] else None,
                    "rawPath": str(raw.relative_to(root)) if raw else None,
                    "reference": {**ref, "sourcePath": "reference/t11_sources.md"} if ref else None,
                    "sourcePath": str((run_dir / "scores.json").relative_to(root))})
    return out


def load_run_meta(root, warnings):
    """Optional explicit run metadata in results/runs.json: {run_id: {"role", "title", "notes"}}.
    role is "headline" (the run the page leads with), "cross-provider" or "advanced"; anything else is ignored."""
    path = root / "results" / "runs.json"
    if not path.exists():
        return {}
    try:
        meta = json.loads(path.read_text())
    except ValueError as exc:
        raise DataError(f"results/runs.json is not valid JSON: {exc}")
    if not isinstance(meta, dict) or not all(isinstance(v, dict) for v in meta.values()):
        raise DataError("results/runs.json must map run ids to objects")
    if sum(1 for v in meta.values() if v.get("role") == "headline") > 1:
        raise DataError("results/runs.json names more than one headline run")
    return meta


def pick_default_run(runs):
    """The documented rule: the complete run whose last trial is most recent. A run is complete when every
    model in it covers every non-experimental task with the same number of trials per task."""
    declared = [r for r in runs if r.get("role") == "headline"]
    if declared:
        return declared[0]["id"]
    complete = [r for r in runs if r["complete"]]
    return max(complete, key=lambda r: r["lastTrialUtc"])["id"] if complete else None


# ---------- main ----------

def build(root):
    root = Path(root).resolve()
    warnings = []
    readme_path = root / "README.md"
    readme = readme_path.read_text() if readme_path.exists() else ""
    if not readme:
        warnings.append("README.md is missing, so task descriptions and limitations are not shown.")
    models_path = root / "models.json"
    try:
        models_cfg = json.loads(models_path.read_text()) if models_path.exists() else []
    except ValueError as exc:
        raise DataError(f"models.json is not valid JSON: {exc}")
    sources = statutory_sources(root / "reference" / "t11_sources.md")
    tasks = load_tasks(root, readme_tasks(readme), warnings)
    runs = load_runs(root, tasks, models_cfg, sources, warnings)
    meta = load_run_meta(root, warnings)
    for r in runs:
        m = meta.get(r["id"], {})
        r["role"] = m.get("role")
        r["title"] = m.get("title")
        r["notes"] = [str(n) for n in m.get("notes", [])]
        r["metaPath"] = "results/runs.json" if m else None
    for missing in sorted(set(meta) - {r["id"] for r in runs}):
        warnings.append(f"results/runs.json describes run '{missing}', which has no committed scores.json.")
    sha, date, dirty = commit_info(root, warnings)
    repo, branch = repo_identity(root)
    lim_title, limitations = readme_section_bullets(readme, r"limitation")
    default_run = pick_default_run(runs)
    if runs and default_run is None:
        warnings.append("No committed run is complete (every model on every core task with equal trials), so no run is shown as the headline.")
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commitSha": sha,
        "commitDate": date,
        "dirtyWorkingTree": dirty,
        "repository": repo,
        "branch": branch,
        "project": {"title": (readme.splitlines()[0].lstrip("# ").strip() if readme else None), "intro": readme_intro(readme),
                    "sourcePath": "README.md"},
        "limitations": {"title": lim_title, "items": limitations, "sourcePath": "README.md"},
        "tasks": tasks,
        "runs": runs,
        "defaultRunId": default_run,
        "defaultRunRule": "The run marked \"headline\" in results/runs.json; without one, the complete run whose most recent trial is latest. A run is complete when every model in it covers every non-experimental task with the same number of trials per task.",
        "warnings": warnings,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    here = Path(__file__).resolve().parent.parent
    ap.add_argument("--root", default=str(here))
    ap.add_argument("--out", default=str(here / "frontend" / "src" / "generated" / "explorer-data.json"))
    args = ap.parse_args()
    try:
        data = build(args.root)
    except DataError as exc:
        print(f"explorer data is invalid, nothing was written: {exc}", file=sys.stderr)
        sys.exit(1)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=1))
    print(f"wrote {out} from commit {data['commitSha'][:7]}: {len(data['tasks'])} tasks, {len(data['runs'])} runs, "
          f"default run {data['defaultRunId']}, {len(data['warnings'])} warnings")
    for w in data["warnings"]:
        print(f"  warning: {w}")


if __name__ == "__main__":
    main()
