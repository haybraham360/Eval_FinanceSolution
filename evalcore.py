"""Grading and extraction shared by run_eval.py and validate_graders.py."""
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALL_TASKS = sorted(p.name for p in (ROOT / "tasks").iterdir() if p.is_dir())
# Tasks marked "experimental" in meta.json run only when named with --tasks, so the default
# benchmark stays the original 12 tasks.
TASKS = [t for t in ALL_TASKS if not json.loads((ROOT / "tasks" / t / "meta.json").read_text()).get("experimental")]
FENCE = re.compile(r"```([a-zA-Z0-9_+-]*)[ \t]*\n(.*?)```", re.S)


def task_kind(task_id):
    return json.loads((ROOT / "tasks" / task_id / "meta.json").read_text())["kind"]


def task_prompt(task_id):
    return (ROOT / "tasks" / task_id / "prompt.md").read_text()


def extract_answer(text, kind):
    """Take the last fenced block in the requested language, falling back to the last block.

    The last block is used because models often sketch code before the final version.
    An unfenced answer is accepted only if the whole output is valid, so a model isn't zeroed for a
    missing fence. Returns None when no complete answer can be found."""
    blocks = FENCE.findall(text or "")
    if not blocks:
        return text.strip() if _is_complete(text or "", kind) else None
    wanted = ("python", "py", "python3") if kind == "python" else ("json",)
    matching = [body for lang, body in blocks if lang.lower() in wanted]
    return (matching or [blocks[-1][1]])[-1]


def _is_complete(text, kind):
    try:
        if kind == "json":
            json.loads(text)
        else:
            compile(text, "answer", "exec")
    except (ValueError, SyntaxError):
        return False
    return bool(text.strip())


def _sandbox_prefix():
    """macOS only: deny network and writes outside temp. Elsewhere the rlimits and socket patch apply."""
    if sys.platform != "darwin" or not Path("/usr/bin/sandbox-exec").exists():
        return []
    profile = '(version 1)(allow default)(deny network*)(deny file-write*)(allow file-write* (subpath "/private/tmp") (subpath "/private/var/folders") (subpath "/dev"))'
    prefix = ["/usr/bin/sandbox-exec", "-p", profile]
    probe = subprocess.run(prefix + ["/usr/bin/true"], capture_output=True)
    return prefix if probe.returncode == 0 else []


SANDBOX = _sandbox_prefix()


def grade_file(task_id, solution_path, timeout=300):
    """Returns {"score": 0..1, "passed": bool, "checks": [...], "error": str|None}."""
    env = {"PATH": "/usr/bin:/bin", "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1", "TZ": "UTC"}
    cmd = SANDBOX + [sys.executable, "-I", str(ROOT / "graders" / "run_one.py"), str(ROOT / "graders"), task_id, str(solution_path)]
    with tempfile.TemporaryDirectory() as cwd:
        try:
            proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"score": 0.0, "passed": False, "checks": [], "error": "grader process timed out"}
    marker = proc.stdout.rfind("@@RESULT@@")
    if marker >= 0:
        checks = json.loads(proc.stdout[marker + len("@@RESULT@@"):])["checks"]
    else:
        last = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        if last.startswith('{"load_error"'):
            return {"score": 0.0, "passed": False, "checks": [], "error": json.loads(last)["load_error"]}
        if proc.returncode == -signal.SIGXCPU:
            return {"score": 0.0, "passed": False, "checks": [], "error": "solution exceeded the CPU time limit"}
        return {"score": 0.0, "passed": False, "checks": [], "error": f"grader crashed: {proc.stderr[-800:]}"}
    done = sum(c["passed"] for c in checks)
    return {"score": done / len(checks), "passed": done == len(checks), "checks": checks, "error": None}


def grade_text(task_id, answer):
    suffix = ".py" if task_kind(task_id) == "python" else ".json"
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(answer)
        return grade_file(task_id, path)
    finally:
        os.unlink(path)
