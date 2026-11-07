import { useState } from "react";
import type { ExplorerData, ModelResult, Run } from "../types";
import site from "../content/site.json";
import { bucket, bucketWord, families, familyAverages, familyScore, figure, nameOf, sharedMistakes, topMistakes } from "../lib/insights";
import { day, pct, plural } from "../lib/format";
import { sourceUrl } from "../lib/links";
import { Icon } from "./Icons";

function Gh({ data, path, children, dir = false }: { data: ExplorerData; path: string; children: React.ReactNode; dir?: boolean }) {
  const url = sourceUrl(data, path, dir);
  return url ? <a href={url} target="_blank" rel="noreferrer">{children}<span className="visually-hidden"> (opens GitHub)</span></a> : <>{children}</>;
}

const crossRuns = (data: ExplorerData) => data.runs.filter((r) => r.role === "cross-provider");
const advancedRuns = (data: ExplorerData) => data.runs.filter((r) => r.role === "advanced");
const listNames = (xs: string[]) => (xs.length < 2 ? xs.join("") : `${xs.slice(0, -1).join(", ")} and ${xs[xs.length - 1]}`);

/* ---------- hero ---------- */

export function Hero({ data, run }: { data: ExplorerData; run: Run | undefined }) {
  const core = data.tasks.filter((t) => !t.experimental).length;
  return (
    <section className="hero" id="top" aria-labelledby="headline">
      <div className="hero-copy">
        <h1 id="headline">{site.headline}</h1>
        <p className="lede">{site.description}</p>
        <a className="cta" href="#findings">Read the short version</a>
      </div>
      <aside className="receipt" aria-label="What this test covered">
        <p className="receipt-title">The test, in numbers</p>
        <dl>
          <div><dt>Real money problems</dt><dd>{core}</dd></div>
          {run ? (
            <>
              <div><dt>AI models tested</dt><dd>{run.models.length}</dd></div>
              <div><dt>Answers checked</dt><dd>{run.trials}</dd></div>
              <div><dt>Individual checks run</dt><dd>{run.checksRun.toLocaleString("en-GB")}</dd></div>
            </>
          ) : (
            <div><dt>Results</dt><dd className="small">Not published yet</dd></div>
          )}
        </dl>
        {run && <p className="receipt-foot">From the test run of {day(run.lastTrialUtc)}</p>}
      </aside>
    </section>
  );
}

/* ---------- the short version: three findings, each computed from the data ---------- */

type Finding = { key: string; tone: "good" | "bad"; title: string; body: React.ReactNode; href: string; link: string };

function findings(data: ExplorerData, run: Run | undefined): Finding[] {
  if (!run) return [];
  const out: Finding[] = [];
  const fams = families(data);
  const avgs = familyAverages(run, fams);
  if (avgs.length > 1) {
    const lo = avgs.reduce((a, b) => (b.mean < a.mean ? b : a));
    const hi = avgs.reduce((a, b) => (b.mean > a.mean ? b : a));
    if (lo.family.key !== hi.family.key)
      out.push({
        key: "hardest-area", tone: "bad", title: `Hardest area: ${lo.family.name}`,
        body: <>The models averaged <strong>{pct(hi.mean, 0)}</strong> on “{hi.family.name}”, but only <strong>{pct(lo.mean, 0)}</strong> on “{lo.family.name}”.</>,
        href: "#results", link: "See the scores",
      });
  }
  const cross = crossRuns(data);
  const shared = cross.flatMap((r) => sharedMistakes(run, r));
  if (shared.length > 0) {
    const newNames = [...new Set(cross.flatMap((r) => r.models.map(nameOf)))];
    out.push({
      key: "not-one-company", tone: "bad", title: "Not just one company's AI",
      body: <>{listNames(newNames)}, from another company, made <strong>{plural(shared.length, "of the same mistakes", "of the same mistakes")}</strong>.</>,
      href: "#others", link: "See which ones",
    });
  }
  const best = [...run.models].sort((a, b) => b.meanScore - a.meanScore)[0];
  if (best) {
    const adv = advancedRuns(data);
    const tasks = data.tasks.filter((t) => t.experimental);
    const results = tasks.flatMap((t) =>
      adv.flatMap((r) => r.models.filter((m) => nameOf(m) === nameOf(best)).map((m) => ({ t, res: m.byTask.find((x) => x.task === t.id) }))).filter((x) => x.res),
    );
    const failed = results.find((x) => x.res!.fullPasses === 0);
    if (failed)
      out.push({
        key: "best-has-limit", tone: "bad", title: "Even the best model has a limit",
        body: <>{nameOf(best)} scored <strong>{pct(best.meanScore, 0)}</strong> on the main test, but failed a harder one, “{failed.t.tests ?? failed.t.title}”, in <strong>{failed.res!.trials} of {plural(failed.res!.trials, "attempt")}</strong>.</>,
        href: "#hardest", link: "See the harder tests",
      });
    else if (results.length > 0 && results.every((x) => x.res!.fullPasses === x.res!.trials))
      out.push({
        key: "best-passes", tone: "good", title: "The best model passed the harder tests too",
        body: <>{nameOf(best)} got every check right on {plural(results.length, "harder test")}.</>,
        href: "#hardest", link: "See the harder tests",
      });
  }
  return out;
}

export function Findings({ data, run }: { data: ExplorerData; run: Run | undefined }) {
  const list = findings(data, run);
  if (list.length === 0) return null;
  return (
    <section id="findings" aria-labelledby="findings-h">
      <h2 id="findings-h">The short version</h2>
      <ol className="findings">
        {list.map((f, i) => (
          <li key={f.key} className={`finding ${f.tone}`}>
            <span className="finding-n" aria-hidden="true">{i + 1}</span>
            <h3>{f.title}</h3>
            <p>{f.body}</p>
            <a href={f.href}>{f.link} ↓</a>
          </li>
        ))}
      </ol>
    </section>
  );
}

/* ---------- how it works: the three steps and the three kinds of problem ---------- */

export function HowItWorks({ data }: { data: ExplorerData }) {
  const fams = families(data);
  return (
    <section id="how" aria-labelledby="how-h">
      <h2 id="how-h">How the test works</h2>
      <ol className="flow">
        {site.steps.map((s, i) => (
          <li key={s.title}>
            <div className="flow-icon"><Icon name={s.icon} size={44} /></div>
            <p className="flow-step">Step {i + 1}</p>
            <h3>{s.title}</h3>
            <p>{s.body}</p>
          </li>
        ))}
      </ol>
      <h3 className="sub-h">Three kinds of problem, where almost right is still wrong</h3>
      <div className="families">
        {fams.map((f) => (
          <article key={f.key} className={`family family-${f.icon}`}>
            <div className="family-head">
              <Icon name={f.icon} size={34} />
              <h4>{f.name}</h4>
            </div>
            <p>{f.plain}</p>
            <details>
              <summary>{plural(f.tasks.length, "problem")}</summary>
              <ul>
                {f.tasks.map((t) => <li key={t.id}><Gh data={data} path={t.sourcePath}>{t.title}</Gh></li>)}
              </ul>
            </details>
          </article>
        ))}
      </div>
    </section>
  );
}

/* ---------- results: one table for every model, including other companies ---------- */

function ScoreCell({ v, label }: { v: number | null; label: string }) {
  if (v === null) return <td data-label={label} className="cell none">Not tested</td>;
  const b = bucket(v);
  return (
    <td data-label={label} className={`cell ${b}`}>
      <strong>{pct(v, 0)}</strong>
      <small>{bucketWord[b]}</small>
    </td>
  );
}

export function Scoreboard({ data, run }: { data: ExplorerData; run: Run | undefined }) {
  if (!run) {
    return (
      <section id="results" aria-labelledby="results-h">
        <h2 id="results-h">How the AI models did</h2>
        <p className="empty">Results are not published yet.</p>
      </section>
    );
  }
  const fams = families(data);
  const cross = crossRuns(data);
  const groups: { title: string | null; run: Run; models: ModelResult[] }[] = [
    { title: null, run, models: [...run.models].sort((a, b) => b.meanScore - a.meanScore) },
    ...cross.map((r) => ({ title: "Another company’s model, for comparison", run: r, models: [...r.models].sort((a, b) => b.meanScore - a.meanScore) })),
  ];
  const shared = cross.flatMap((r) => sharedMistakes(run, r)).slice(0, 3);
  const names = Object.fromEntries(groups.flatMap((g) => g.models.map((m) => [m.label, nameOf(m)])));
  const attempts = run.models[0]?.trialsPerTask[0] ?? 1;
  return (
    <section id="results" aria-labelledby="results-h">
      <h2 id="results-h">How the AI models did</h2>
      <p className="section-lede">
        A score is the share of checks an answer got right. Each Claude model tried every problem {plural(attempts, "time")}.
      </p>

      <div className="table-wrap">
        <table className="scores" aria-label="Scores by model">
          <thead>
            <tr>
              <th scope="col">Model</th>
              <th scope="col">Overall</th>
              {fams.map((f) => (
                <th scope="col" key={f.key}><span className="th-icon"><Icon name={f.icon} size={20} /></span>{f.name}</th>
              ))}
            </tr>
          </thead>
          {groups.map((g) => (
            <tbody key={g.run.id} className={g.title ? "group-other" : undefined}>
              {g.title && (
                <tr className="group-row">
                  <th colSpan={2 + fams.length} scope="rowgroup">
                    {g.title} · {plural(g.models[0]?.trialsPerTask[0] ?? 1, "attempt")} per problem, a quick check
                  </th>
                </tr>
              )}
              {g.models.map((m) => (
                <tr key={`${g.run.id}/${m.label}`}>
                  <th scope="row" className="model">
                    {nameOf(m)}
                    <small>Perfect answers: {m.fullPasses} of {m.trials}</small>
                  </th>
                  <td data-label="Overall" className="overall">
                    <span className="overall-num">{pct(m.meanScore)}</span>
                    <span className="meter" aria-hidden="true"><span className={bucket(m.meanScore)} style={{ width: `${m.meanScore * 100}%` }} /></span>
                  </td>
                  {fams.map((f) => <ScoreCell key={f.key} v={familyScore(m, f)} label={f.name} />)}
                </tr>
              ))}
            </tbody>
          ))}
        </table>
      </div>
      <p className="legend" aria-label="Colour key">
        <span><i className="sw strong" /> Strong: 95% or more</span>
        <span><i className="sw mixed" /> Some slips: 85–95%</span>
        <span><i className="sw weak" /> Struggled: under 85%</span>
      </p>

      {shared.length > 0 && (
        <div className="callout" id="others">
          <h3>Does this only happen with Claude?</h3>
          <p>No. The model from another company missed the same rules the Claude models did:</p>
          <ul className="xlist">
            {shared.map((x) => (
              <li key={`${x.task}/${x.check}`}>
                <span className="x" aria-hidden="true">✗</span>
                <span>
                  {x.rule}
                  <small>Missed by {[...x.newModels, ...x.others].map((l) => names[l] ?? l).join(", ")}</small>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <details className="more">
        <summary>Where these numbers come from</summary>
        <ul className="notes">
          <li>Main test: <Gh data={data} path={run.sourcePath}>saved results on GitHub</Gh> (run <code>{run.id}</code>).</li>
          {cross.map((r) => (
            <li key={r.id}>Comparison: <Gh data={data} path={r.sourcePath}>saved results</Gh> (run <code>{r.id}</code>). One attempt per problem is weaker evidence than the main test.</li>
          ))}
          {cross.flatMap((r) => r.notes).map((n) => <li key={n}>{n}</li>)}
        </ul>
      </details>
    </section>
  );
}

/* ---------- mistakes ---------- */

function Explain({ label, text }: { label: string; text: string }) {
  const [open, setOpen] = useState(false);
  const long = text.length > 170;
  return (
    <div className="explain">
      <p className={long && !open ? "clamp" : undefined}><strong>{label}</strong> {text}</p>
      {long && <button type="button" className="linkish" aria-expanded={open} onClick={() => setOpen(!open)}>{open ? "Show less" : "Read more"}</button>}
    </div>
  );
}

export function Mistakes({ data, run }: { data: ExplorerData; run: Run | undefined }) {
  const [all, setAll] = useState(false);
  if (!run) return null;
  const list = topMistakes(run, data.tasks.map((t) => t.id));
  const names = Object.fromEntries(run.models.map((m) => [m.label, nameOf(m)]));
  const fams = families(data);
  const shown = all ? list : list.slice(0, 3);
  return (
    <section id="mistakes" aria-labelledby="mistakes-h">
      <h2 id="mistakes-h">Where the AI slipped</h2>
      {list.length === 0 ? (
        <p className="empty">No model made a checkable mistake in this run.</p>
      ) : (
        <>
          <p className="section-lede">Real mistakes from the main test, each with the rule it broke.</p>
          <div className="mistakes">
            {shown.map((m) => {
              const task = data.tasks.find((t) => t.id === m.task);
              const fam = fams.find((f) => f.tasks.some((t) => t.id === m.task));
              const ref = m.example.reference;
              const long = figure(m.got).length > 12 || figure(m.expected).length > 12;
              return (
                <article key={`${m.task}/${m.check}`} className="mistake">
                  <p className="mistake-topic"><Icon name={fam?.icon ?? "ticket"} size={18} /> {fam?.name ?? task?.category}</p>
                  <h3>{task?.title ?? m.task}</h3>
                  <div className={`answer ${long ? "stack" : ""}`}>
                    <div className="answer-wrong">
                      <span className="answer-label">AI answered</span>
                      <span className={`answer-value ${long ? "long" : ""}`}><s>{figure(m.got)}</s></span>
                    </div>
                    <div className="answer-right">
                      <span className="answer-label">Correct</span>
                      <span className={`answer-value ${long ? "long" : ""}`}>{figure(m.expected)}</span>
                    </div>
                  </div>
                  {ref?.rule && <Explain label={ref.kind === "explanation" ? "Why:" : "The rule:"} text={ref.rule} />}
                  <p className="mistake-who">
                    {m.models.map((x) => names[x] ?? x).join(" and ")} · wrong in {m.failedTrials} of {plural(m.trialsRun, "attempt")}
                  </p>
                  <p className="mistake-link"><Gh data={data} path={m.example.transcriptPath ?? m.example.sourcePath}>Read the AI's answer</Gh></p>
                </article>
              );
            })}
          </div>
          <div className="mistakes-foot">
            {list.length > 3 && (
              <button type="button" className="ghost" aria-expanded={all} onClick={() => setAll(!all)}>
                {all ? "Show fewer" : `Show ${list.length - 3} more`}
              </button>
            )}
            <p className="fine">
              All {plural(run.failures.length, "recorded mistake")} are in <Gh data={data} path={run.summaryPath ?? run.sourcePath}>the full results</Gh>.
            </p>
          </div>
        </>
      )}
    </section>
  );
}

/* ---------- harder tests: one pass/fail grid ---------- */

export function Advanced({ data, run }: { data: ExplorerData; run: Run | undefined }) {
  const runs = advancedRuns(data);
  const tasks = data.tasks.filter((t) => t.experimental && runs.some((r) => r.tasks.includes(t.id)));
  if (tasks.length === 0) return null;
  // Strongest model of the main test first, then the rest in the order their runs appear.
  const ranked = run ? [...run.models].sort((a, b) => b.meanScore - a.meanScore).map(nameOf) : [];
  const seen = new Set(runs.flatMap((r) => r.models.map(nameOf)));
  const modelNames = [...ranked.filter((n) => seen.has(n)), ...[...seen].filter((n) => !ranked.includes(n))];
  const cell = (taskId: string, name: string) => {
    for (const r of runs) {
      const m = r.models.find((x) => nameOf(x) === name);
      const res = m?.byTask.find((x) => x.task === taskId);
      if (m && res) return { r, m, res, err: r.errors.find((e) => e.model === m.label && e.task === taskId) };
    }
    return null;
  };
  return (
    <section id="hardest" aria-labelledby="hardest-h">
      <h2 id="hardest-h">The harder tests</h2>
      <p className="section-lede">Two extra problems built to find the limits of the strongest model. They are experimental and not part of the scores above.</p>
      <div className="table-wrap">
        <table className="hard" aria-label="Harder tests: pass or fail by model">
          <thead>
            <tr>
              <th scope="col">Problem</th>
              {modelNames.map((n) => <th scope="col" key={n}>{n}</th>)}
            </tr>
          </thead>
          <tbody>
            {tasks.map((t) => (
              <tr key={t.id}>
                <th scope="row" className="hard-task">
                  <Gh data={data} path={t.sourcePath}>{t.tests ?? t.title}</Gh>
                  {t.challenge && <small>{t.challenge}</small>}
                </th>
                {modelNames.map((n) => {
                  const c = cell(t.id, n);
                  if (!c) return <td key={n} data-label={n} className="verdict none">Not tried</td>;
                  const passed = c.res.fullPasses === c.res.trials;
                  const line = passed
                    ? `Passed ${c.res.fullPasses} of ${c.res.trials}`
                    : c.err?.finishReason === "length"
                      ? "Ran out of space"
                      : c.err
                        ? "No checkable answer"
                        : `Failed ${c.res.trials - c.res.fullPasses} of ${c.res.trials}`;
                  return (
                    <td key={n} data-label={n} className={`verdict ${passed ? "ok" : "no"}`}>
                      <span className="mark" aria-hidden="true">{passed ? "✓" : "✗"}</span>
                      <span>
                        <strong>{line}</strong>
                        <small>{c.err?.finishReason === "length" ? "before finishing its answer" : `score ${pct(c.res.meanScore, 0)}`}</small>
                      </span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {tasks.map((t) => {
        const pool = runs.flatMap((r) => r.failures.filter((f) => f.task === t.id));
        const slips = topMistakes({ failures: pool } as Run, [t.id], 3, 3);
        if (slips.length === 0) return null;
        const names = Object.fromEntries(runs.flatMap((r) => r.models.map((m) => [m.label, nameOf(m)])));
        return (
          <details key={t.id} className="more">
            <summary>Where the models slipped on “{t.tests ?? t.title}”</summary>
            <ul className="xlist">
              {slips.map((x) => (
                <li key={x.check}>
                  <span className="x" aria-hidden="true">✗</span>
                  <span>
                    {x.example.reference?.rule ?? x.check}
                    <small>
                      Answered {figure(x.got)} instead of {figure(x.expected)} · {x.models.map((l) => names[l] ?? l).join(", ")}, {x.failedTrials} of {plural(x.trialsRun, "attempt")}
                    </small>
                  </span>
                </li>
              ))}
            </ul>
          </details>
        );
      })}
      {runs.some((r) => r.notes.length > 0) && (
        <details className="more">
          <summary>Notes on these runs</summary>
          <ul className="notes">
            {runs.flatMap((r) => r.notes.map((n) => (
              <li key={`${r.id}/${n}`}><strong>{r.title ?? r.id}:</strong> {n} <Gh data={data} path={r.sourcePath}>Results</Gh></li>
            )))}
          </ul>
        </details>
      )}
    </section>
  );
}

/* ---------- trust and sources ---------- */

export function Trust({ data }: { data: ExplorerData }) {
  const wrong = data.tasks.reduce((n, t) => n + t.mutantCount, 0);
  const links: [string, string, boolean][] = [
    ["Every problem, word for word", "tasks", true],
    ["The checkers that mark each answer", "graders", true],
    ["Every AI answer and score", "results", true],
    ["The AI answers that went wrong", "transcripts", true],
    ["Full write-up and limitations", "README.md", false],
  ];
  return (
    <section id="trust" aria-labelledby="trust-h">
      <h2 id="trust-h">Why you can trust these scores</h2>
      <div className="trust">
        <ul className="fair">
          {site.fairness.map((f, i) => (
            <li key={f}>
              <span className="fair-tick" aria-hidden="true">✓</span>
              <span>
                {f}
                {i === 1 && wrong > 0 && <> Right now they reject all {wrong} deliberately wrong answers kept in the repository.</>}
              </span>
            </li>
          ))}
        </ul>
        <nav className="detail-links" aria-label="Sources on GitHub">
          <p className="detail-title">Check it yourself on GitHub</p>
          {links.map(([label, path, dir]) => <Gh key={path} data={data} path={path} dir={dir}>{label} →</Gh>)}
        </nav>
      </div>
    </section>
  );
}
