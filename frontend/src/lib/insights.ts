// Every insight on the page is computed here from the data bundle, by a fixed, documented rule.
import site from "../content/site.json";
import type { ExplorerData, Failure, ModelResult, Run } from "../types";

export type Family = { key: string; name: string; plain: string; icon: string; tasks: { id: string; title: string; sourcePath: string }[] };

/** Groups the core tasks by their README family, with plain-language names from site.json. */
export function families(data: ExplorerData): Family[] {
  const out: Family[] = [];
  for (const t of data.tasks.filter((x) => !x.experimental)) {
    const key = t.category ?? "Other";
    let f = out.find((x) => x.key === key);
    if (!f) {
      const copy = site.families.find((c) => new RegExp(c.match, "i").test(key));
      f = { key, name: copy?.name ?? key, plain: copy?.plain ?? "", icon: copy?.icon ?? "ticket", tasks: [] };
      out.push(f);
    }
    f.tasks.push({ id: t.id, title: t.title, sourcePath: t.sourcePath });
  }
  return out;
}

export const nameOf = (m: ModelResult) => m.displayName || m.label;

/** Groups digits of a plain number from a grader message (20000000 -> 20,000,000); anything else verbatim. */
export function figure(raw: string): string {
  const t = raw.trim().replace(/^'(.*)'$/, "$1");
  const m = /^(-?)(\d+)(?:\.(\d*?)0*)?$/.exec(t);
  return m ? m[1] + Number(m[2]).toLocaleString("en-GB") + (m[3] ? `.${m[3]}` : "") : raw;
}

export interface Mistake {
  task: string;
  check: string;
  expected: string;
  got: string;
  models: string[];
  failedTrials: number;
  trialsRun: number;
  example: Failure;
}

/** True for a bare number such as 20000000, 1950000.0 or -12.5 (quotes allowed), which anyone can read. */
export const isPlainNumber = (x: string) => /^'?-?\d+(\.\d+)?'?$/.test(x.trim());

/** The mistakes shown: first those with a written rule that explains them in plain words, then checks that the
 *  most models failed, then the most failed attempts, then task order. If any mistake has a written rule, only
 *  those are shown.
 *  Only grader messages "expected X, got Y" where both X and Y are plain numbers qualify, so every card is
 *  readable without technical knowledge; at most one mistake per task. */
export function topMistakes(run: Run | undefined, taskOrder: string[], limit = 3): Mistake[] {
  if (!run) return [];
  const groups = new Map<string, Mistake>();
  for (const f of run.failures) {
    const m = /expected (.+?), got (.+)$/.exec(f.message);
    if (!m || !isPlainNumber(m[1]) || !isPlainNumber(m[2])) continue;
    const key = `${f.task}/${f.check}`;
    const g = groups.get(key) ?? { task: f.task, check: f.check, expected: m[1], got: m[2], models: [], failedTrials: 0, trialsRun: 0, example: f };
    g.models.push(f.model);
    g.failedTrials += f.failedTrials.length;
    g.trialsRun += f.trialsRun;
    groups.set(key, g);
  }
  const explained = (g: Mistake) => (g.example.reference?.rule ? 1 : 0);
  const sorted = [...groups.values()].sort(
    (a, b) => explained(b) - explained(a) || b.models.length - a.models.length || b.failedTrials - a.failedTrials || taskOrder.indexOf(a.task) - taskOrder.indexOf(b.task) || a.check.localeCompare(b.check),
  );
  // When some mistakes come with a written rule, show only those: a bare code or count means little to most readers.
  const pool = sorted.some(explained) ? sorted.filter(explained) : sorted;
  const seen = new Set<string>();
  return pool.filter((g) => !seen.has(g.task) && seen.add(g.task)).slice(0, limit);
}

/** Average score per family across all models in the run, for the one-line takeaway. */
export function familyAverages(run: Run, fams: Family[]): { family: Family; mean: number }[] {
  return fams
    .map((f) => {
      const scores = run.models.flatMap((m) => m.byTask.filter((r) => f.tasks.some((t) => t.id === r.task)).map((r) => ({ s: r.meanScore, n: r.trials })));
      const n = scores.reduce((a, x) => a + x.n, 0);
      return { family: f, mean: n ? scores.reduce((a, x) => a + x.s * x.n, 0) / n : NaN };
    })
    .filter((x) => !Number.isNaN(x.mean));
}

export const bucket = (x: number) => (x >= 0.95 ? "strong" : x >= 0.85 ? "mixed" : "weak");
export const bucketWord = { strong: "Strong", mixed: "Some slips", weak: "Struggled" } as const;

/** Attempt-weighted mean score of one model over one family's tasks, or null if it attempted none. */
export function familyScore(m: ModelResult, f: Family): number | null {
  const rs = m.byTask.filter((r) => f.tasks.some((t) => t.id === r.task));
  const n = rs.reduce((a, r) => a + r.trials, 0);
  return n ? rs.reduce((a, r) => a + r.meanScore * r.trials, 0) / n : null;
}

export interface SharedMistake { task: string; check: string; rule: string; provision: string | null; others: string[]; newModels: string[] }

/** Checks failed in another run that the headline run's models also failed, limited to those with a written
 *  rule (so each one can be explained in plain words). Sorted by how many headline models shared it. */
export function sharedMistakes(headline: Run, other: Run): SharedMistake[] {
  const out = new Map<string, SharedMistake>();
  for (const f of other.failures) {
    if (!f.reference?.rule) continue;
    const same = headline.failures.filter((h) => h.task === f.task && h.check === f.check).map((h) => h.model);
    if (!same.length) continue;
    const key = `${f.task}/${f.check}`;
    const e = out.get(key) ?? { task: f.task, check: f.check, rule: f.reference.rule, provision: f.reference.provision, others: [...new Set(same)], newModels: [] };
    e.newModels.push(f.model);
    out.set(key, e);
  }
  return [...out.values()].sort((a, b) => b.others.length - a.others.length || a.task.localeCompare(b.task) || a.check.localeCompare(b.check));
}
