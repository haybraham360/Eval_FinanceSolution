"""Proves the explorer data follows the repository: each test builds a small throwaway git repo,
changes one thing, and checks the extracted bundle changes with it.

    python -m unittest discover -s scripts/tests
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import export_explorer_data as ex  # noqa: E402

README = """# Fixture project

Intro paragraph.

## What Does It Test?

### 1. Engineering (Tasks 1–2)

| Task | What It Tests | What Makes It Challenging |
|---|---|---|
| `t1_alpha` | Alpha things | Hard alpha |
| `t2_beta` | Beta things | Hard beta |

## Limitations and Things to Keep in Mind

* Only a fixture.
* Small.
"""


def row(model, task, trial, checks, utc="2026-10-31T10:00:00+00:00"):
    done = sum(ok for _, ok in checks)
    return {"model": model, "task": task, "trial": trial, "utc": utc, "score": done / len(checks), "passed": done == len(checks),
            "checks": [{"check": c, "passed": ok, "detail": "" if ok else f"AssertionError: {c} wrong\nTraceback ..."} for c, ok in checks],
            "error": None, "resolved_model": model, "provider": "fixture", "finish_reason": "stop"}


class Repo:
    def __init__(self, tmp):
        self.root = Path(tmp)
        self.write("README.md", README)
        self.write("models.json", json.dumps([{"label": "m-a", "id": "a", "tier": "free"}, {"label": "m-b", "id": "b", "tier": "free"}]))
        for t in ("t1_alpha", "t2_beta"):
            self.task(t)
        self.rows = {"run1": [row("m-a", "t1_alpha", 1, [("c1", True), ("c2", False)]), row("m-a", "t2_beta", 1, [("c1", True)])]}
        self.save("run1")
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.commit()

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def task(self, tid, title=None):
        self.write(f"tasks/{tid}/meta.json", json.dumps({"kind": "python", "title": title or tid}))
        self.write(f"tasks/{tid}/prompt.md", f"# {tid}\n")

    def save(self, run):
        self.write(f"results/{run}/scores.json", json.dumps(self.rows[run]))
        for r in self.rows[run]:
            self.write(f"results/{run}/raw/{r['model']}/{r['task']}/trial_{r['trial']}.json",
                       json.dumps({"requested_model": r["model"], "params": {}, "system": "sys", "task": r["task"], "trial": r["trial"]}))

    def commit(self):
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid", "GIT_COMMITTER_NAME": "t",
               "GIT_COMMITTER_EMAIL": "t@example.invalid"}
        subprocess.run(["git", "-C", str(self.root), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-q", "-m", "fixture", "--allow-empty"], check=True, env=env)

    def build(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            for k in ("GITHUB_SHA", "EXPLORER_COMMIT_SHA", "GITHUB_REPOSITORY", "GITHUB_REF_NAME"):
                os.environ.pop(k, None)
            return ex.build(self.root)


class ExplorerDataFollowsRepository(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Repo(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_baseline_bundle(self):
        d = self.repo.build()
        self.assertEqual([t["id"] for t in d["tasks"]], ["t1_alpha", "t2_beta"])
        self.assertEqual(d["tasks"][0]["category"], "Engineering")
        self.assertEqual(d["tasks"][0]["tests"], "Alpha things")
        self.assertEqual(d["limitations"]["items"], ["Only a fixture.", "Small."])
        self.assertEqual(d["defaultRunId"], "run1")
        self.assertEqual(d["warnings"], [])

    def test_1_added_task_appears(self):
        self.repo.task("t3_gamma", "Gamma task")
        self.repo.commit()
        d = self.repo.build()
        self.assertIn("t3_gamma", [t["id"] for t in d["tasks"]])
        self.assertTrue(any("t3_gamma" in w and "README" in w for w in d["warnings"]), "undescribed task should be flagged")
        self.assertIsNone(d["defaultRunId"], "run1 no longer covers every core task")

    def test_2_changed_score_changes_data(self):
        before = self.repo.build()["runs"][0]["models"][0]["meanScore"]
        self.repo.rows["run1"][0] = row("m-a", "t1_alpha", 1, [("c1", True), ("c2", True)])
        self.repo.save("run1")
        self.repo.commit()
        after = self.repo.build()["runs"][0]["models"][0]
        self.assertEqual((before, after["meanScore"], after["fullPasses"]), (0.75, 1.0, 2))

    def test_3_removed_result_is_not_shown(self):
        import shutil
        shutil.rmtree(self.repo.root / "results" / "run1")
        self.repo.commit()
        d = self.repo.build()
        self.assertEqual((d["runs"], d["defaultRunId"]), ([], None))

    def test_4_new_model_appears(self):
        self.repo.rows["run1"] += [row("m-b", "t1_alpha", 1, [("c1", True), ("c2", True)]), row("m-b", "t2_beta", 1, [("c1", False)])]
        self.repo.save("run1")
        self.repo.commit()
        labels = [m["label"] for m in self.repo.build()["runs"][0]["models"]]
        self.assertEqual(labels, ["m-a", "m-b"])

    def test_5_failures_only_from_grader_output(self):
        self.repo.write("transcripts/run1/m-a__t1_alpha.md", "# m-a / t1_alpha / trial 1\n")
        self.repo.write("transcripts/run1/m-a__t2_beta.md", "# m-a / t2_beta / trial 1\n")  # a passing task
        self.repo.commit()
        f = self.repo.build()["runs"][0]["failures"]
        self.assertEqual([(x["task"], x["check"]) for x in f], [("t1_alpha", "c2")], "a transcript alone is not a failure")
        self.assertEqual(f[0]["transcriptPath"], "transcripts/run1/m-a__t1_alpha.md")
        self.assertEqual(f[0]["message"], "AssertionError: c2 wrong", "only the assertion line, never the traceback")
        self.repo.write("transcripts/run1/m-a__t1_alpha.md", "# m-a / t1_alpha / trial 2\n")  # a different trial
        self.repo.commit()
        self.assertIsNone(self.repo.build()["runs"][0]["failures"][0]["transcriptPath"])

    def test_6_malformed_data_fails_the_build(self):
        cases = {
            "invalid JSON": lambda: self.repo.write("results/run1/scores.json", "{not json"),
            "missing field": lambda: self.repo.write("results/run1/scores.json", json.dumps([{k: v for k, v in self.repo.rows["run1"][0].items() if k != "score"}])),
            "contradictory score": lambda: self.repo.write("results/run1/scores.json", json.dumps([{**self.repo.rows["run1"][0], "score": 0.9}] + self.repo.rows["run1"][1:])),
            "raw with no score row": lambda: self.repo.write("results/run1/raw/m-a/t1_alpha/trial_2.json", "{}"),
            "duplicate trial": lambda: self.repo.write("results/run1/scores.json", json.dumps(self.repo.rows["run1"] + self.repo.rows["run1"][:1])),
            "bad task meta": lambda: self.repo.write("tasks/t1_alpha/meta.json", json.dumps({"title": 3})),
        }
        for name, breakit in cases.items():
            with self.subTest(name):
                tmp = tempfile.TemporaryDirectory()
                self.repo = Repo(tmp.name)
                breakit()
                with self.assertRaises(ex.DataError):
                    self.repo.build()
                out = Path(tmp.name) / "out.json"
                proc = subprocess.run([sys.executable, str(Path(ex.__file__)), "--root", tmp.name, "--out", str(out)], capture_output=True, text=True)
                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                self.assertFalse(out.exists(), "nothing may be written for invalid data")
                tmp.cleanup()

    def test_7_commit_sha_matches_build_commit(self):
        head = subprocess.run(["git", "-C", str(self.repo.root), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        d = self.repo.build()
        self.assertEqual((d["commitSha"], d["dirtyWorkingTree"]), (head, False))
        self.assertTrue(d["commitDate"])
        with mock.patch.dict(os.environ, {"GITHUB_SHA": head, "GITHUB_REPOSITORY": "owner/repo", "GITHUB_REF_NAME": "main"}):
            d = ex.build(self.repo.root)
        self.assertEqual((d["commitSha"], d["repository"], d["branch"]), (head, "owner/repo", "main"))

    def test_run_metadata_picks_headline_and_roles(self):
        self.repo.rows["run2"] = [row("m-b", "t1_alpha", 1, [("c1", True)], utc="2026-11-06T10:00:00+00:00"),
                                  row("m-b", "t2_beta", 1, [("c1", True)], utc="2026-11-06T10:00:00+00:00")]
        self.repo.save("run2")
        self.repo.commit()
        self.assertEqual(self.repo.build()["defaultRunId"], "run2", "without metadata the latest complete run leads")
        self.repo.write("results/runs.json", json.dumps({"run1": {"role": "headline", "title": "Main"}, "run2": {"role": "cross-provider", "notes": ["one trial"]}}))
        self.repo.commit()
        d = self.repo.build()
        self.assertEqual(d["defaultRunId"], "run1")
        r2 = [r for r in d["runs"] if r["id"] == "run2"][0]
        self.assertEqual((r2["role"], r2["notes"]), ("cross-provider", ["one trial"]))
        self.repo.write("results/runs.json", json.dumps({"run1": {"role": "headline"}, "run2": {"role": "headline"}}))
        with self.assertRaises(ex.DataError):
            self.repo.build()

    def test_report_folders_are_not_runs(self):
        self.repo.write("results/additional/report.md", "# notes\n")
        self.repo.write("results/half-run/raw/m-a/t1_alpha/trial_1.json", "{}")
        self.repo.commit()
        d = self.repo.build()
        self.assertEqual([r["id"] for r in d["runs"]], ["run1"])
        self.assertFalse(any("additional" in w for w in d["warnings"]))
        self.assertTrue(any("half-run" in w for w in d["warnings"]), "a run with raw outputs but no scores is still flagged")

    def test_uncommitted_changes_are_flagged(self):
        self.repo.task("t9_draft")
        d = self.repo.build()
        self.assertTrue(d["dirtyWorkingTree"])
        self.assertTrue(any("uncommitted" in w for w in d["warnings"]))


if __name__ == "__main__":
    unittest.main()
