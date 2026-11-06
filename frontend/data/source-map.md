# Ledger-Eval Explorer: source map

Every value on the site is derived by `scripts/export_explorer_data.py` from files committed in this repository, at build time, for the exact commit being deployed. No score, count, date, model name or failure is typed into the frontend. The only hand-written content is the plain-language copy in `frontend/src/content/site.json`: the headline, the description, a friendly name and one-line explanation for each task family, the three "How it works" steps, and the three "Why you can trust these scores" statements. That copy describes the project and the code, never a result.

The page is deliberately simple. The technical detail (every prompt, grader, transcript and full result table) is linked on GitHub rather than reproduced.

| Website data | Repository source | Extraction rule |
|---|---|---|
| Commit SHA, commit date | GitHub Actions `GITHUB_SHA`, `git log -1 --format=%cI` | Taken from the checkout being built. Every "View source" link is pinned to this SHA. |
| "Site data built" time | Extraction time | `generatedAt`, set when the bundle is written |
| Repository and branch | `GITHUB_REPOSITORY`, `GITHUB_REF_NAME` (locally: `git remote`) | Used for links and for the freshness check |
| "May be out of date" notice | GitHub public API at view time | Compares the build SHA with the branch head. A mismatch means a newer commit's build is running or failed. |
| Task list, titles, kind, experimental flag | `tasks/<id>/meta.json` | Every directory under `tasks/` that has `meta.json` and `prompt.md` |
| Task prompt | `tasks/<id>/prompt.md` | Shown verbatim. These prompts are already public in the repository. |
| Task family, "What it tests", "What makes it hard" | `README.md` task tables | A table row whose first cell is a backticked task id, under the `###` heading it sits in. A task missing from the README is shown without them, with a build warning. |
| Grader, alternative solutions, mutant count | `graders/<id>.py`, `reference_alt/<id>*`, `mutants/<id>/` | Shown when the file exists. Counts are file counts. |
| Runs | `results/<run>/scores.json` | One run per folder with a `scores.json`. Each row is cross-checked against `results/<run>/raw/` (a mismatch fails the build). |
| Mean score, full-pass rate, passed every trial, passed at least once, trials | `results/<run>/scores.json` | Computed from trial rows: mean of `score`; `passed` count over trials; per task, all or any `passed`. A full-pass rate is never derived from mean scores. |
| Mean score by task family | `scores.json` plus README families | Mean of trial scores per family. Reproduces the README's category table for run `final`. |
| Run shown on the page | All runs | The complete run whose last trial is latest. Complete means every model covers every non-experimental task with the same number of trials per task. |
| Readable model names | `resolved_model` and `requested_model` in the run | The resolved ID containing the requested one, with the vendor prefix and size or build tags dropped. "claude-opus-5-5" becomes "Claude Opus 5.5". Exact IDs stay on GitHub. |
| "The test, in numbers" receipt | Tasks and the shown run | Core task count; models, attempts and total individual checks (`len(checks)` summed) in the shown run |
| Score bars and "perfect answers" | `results/<run>/scores.json` | Mean of trial scores per model, and trials with every check passed |
| "By kind of problem" grid | `scores.json` plus README families | Attempt-weighted mean score per model per family. Labels: Strong ≥ 95%, Some slips ≥ 85%, Struggled below 85%. |
| Takeaway sentence | Same | The family with the highest and the lowest average across all models in the run, generated from the numbers |
| "Where the AI slipped" cards | The shown run's failures plus `reference/t11_sources.md` | Grader messages "expected X, got Y" where both are plain numbers. Ranked: mistakes with a written rule first (only those, if any exist), then the most models, then the most attempts. At most one per task, three in all. |
| Failures and transcripts | `scores.json`, `transcripts/` | Counted on the page and linked on GitHub, not listed |
| Project limitations | `README.md` | Bullets under the `##` heading containing "Limitation" |
| Build warnings | Extractor | Shown in the Methodology section, for example undescribed tasks or results for removed tasks |

## Validation that fails the build

The extractor exits non-zero and writes nothing in these cases:

- `scores.json` is not valid JSON, or a row lacks a field or has the wrong type
- a score lies outside 0..1
- the same model, task and trial appears twice
- a `score` or `passed` value contradicts the row's own checks
- a raw output has no scores row, or a scores row has no raw output
- a task folder has a malformed `meta.json`

Separately, `scripts/verify_committed_results.py` re-grades every committed raw output in memory and fails if any outcome differs from the committed `scores.json`.

## Data not shown, and why

- **Runs that exist only on a local disk** (not committed) are never shown on the published site. A local preview built from uncommitted files carries a visible "Local preview" banner.
- **Token usage and notional API cost** are recorded inconsistently across backends. CLI runs report a notional cost, and OpenRouter runs report a real cost. They are not shown, to avoid implying a price.
- **Model temperature** is not recorded in the raw files, so it is not shown.
