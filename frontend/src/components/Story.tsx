import type { ExplorerData, Run } from "../types";
import site from "../content/site.json";
import { bucket, bucketWord, families, familyAverages, familyScore, figure, nameOf, sharedMistakes, topMistakes } from "../lib/insights";
import { day, pct, plural } from "../lib/format";
import { sourceUrl } from "../lib/links";
import { Icon } from "./Icons";

function Gh({ data, path, children, dir = false }: { data: ExplorerData; path: string; children: React.ReactNode; dir?: boolean }) {
  const url = sourceUrl(data, path, dir);
  return url ? <a href={url} target="_blank" rel="noreferrer">{children}<span className="visually-hidden"> (opens GitHub)</span></a> : <>{children}</>;
}

export function Hero({ data, run }: { data: ExplorerData; run: Run | undefined }) {
  const core = data.tasks.filter((t) => !t.experimental).length;
  return (
    <section className="hero" id="top" aria-labelledby="headline">
      <div className="hero-copy">
        <h1 id="headline">{site.headline}</h1>
        <p className="lede">{site.description}</p>
        <a className="cta" href="#results">See how the AI models did</a>
      </div>
      <aside className="receipt" aria-label="What this test covered">
        <p className="receipt-title">The test, in numbers</p>
        <dl>
          <div><dt>Real money problems</dt><dd>{core}</dd></div>
          {run ? (
            <>
              <div><dt>AI models tested</dt><dd>{run.models.length}</dd></div>
              <div><dt>Answers checked</dt><dd>{run.trials}</dd></div>
              <div><dt>Individual checks run on those answers</dt><dd>{run.checksRun.toLocaleString("en-GB")}</dd></div>
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

export function WhatWeTest({ data }: { data: ExplorerData }) {
  const fams = families(data);
  return (
    <section id="what" aria-labelledby="what-h">
      <h2 id="what-h">What we test</h2>
      <p className="section-lede">Three kinds of problems where being almost right is still wrong.</p>
      <div className="families">
        {fams.map((f) => (
          <article key={f.key} className={`family family-${f.icon}`}>
            <div className="family-icon"><Icon name={f.icon} size={56} /></div>
            <h3>{f.name}</h3>
            <p>{f.plain}</p>
            <details>
              <summary>{plural(f.tasks.length, "problem")} in this group</summary>
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

export function HowItWorks() {
  return (
    <section id="how" aria-labelledby="how-h">
      <h2 id="how-h">How it works</h2>
      <ol className="flow">
        {site.steps.map((s, i) => (
          <li key={s.title}>
            <div className="flow-icon"><Icon name={s.icon} size={52} /></div>
            <p className="flow-step">Step {i + 1}</p>
            <h3>{s.title}</h3>
            <p>{s.body}</p>
          </li>
        ))}
      </ol>
    </section>
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
  const models = [...run.models].sort((a, b) => b.meanScore - a.meanScore);
  const avgs = familyAverages(run, fams);
  const lo = avgs.length > 1 ? avgs.reduce((a, b) => (b.mean < a.mean ? b : a)) : null;
  const hi = avgs.length > 1 ? avgs.reduce((a, b) => (b.mean > a.mean ? b : a)) : null;
  return (
    <section id="results" aria-labelledby="results-h">
      <h2 id="results-h">How the AI models did</h2>
      <p className="section-lede">
        Each model tried every problem {plural(models[0]?.trialsPerTask[0] ?? 1, "time")}. A score is the share of checks the answer got right; a perfect answer gets every check right.
      </p>

      <ul className="bars" aria-label="Average score by model">
        {models.map((m) => (
          <li key={m.label}>
            <div className="bar-head">
              <span className="bar-name">{nameOf(m)}</span>
              <span className="bar-value">{pct(m.meanScore)}</span>
            </div>
            <div className="bar-track" aria-hidden="true">
              <div className={`bar-fill ${bucket(m.meanScore)}`} style={{ width: `${m.meanScore * 100}%` }} />
            </div>
            <p className="bar-note">
              Perfect answers: <strong>{m.fullPasses} of {m.trials}</strong>
            </p>
          </li>
        ))}
      </ul>

      {fams.length > 1 && (
        <>
          <h3 className="grid-title">By kind of problem</h3>
          <div className="heat" role="table" aria-label="Average score by model and kind of problem" style={{ gridTemplateColumns: `minmax(130px, 1.2fr) repeat(${fams.length}, minmax(96px, 1fr))` }}>
            <div role="row" className="heat-row heat-head">
              <span role="columnheader" />
              {fams.map((f) => (
                <span role="columnheader" key={f.key}><Icon name={f.icon} size={26} /> {f.name}</span>
              ))}
            </div>
            {models.map((m) => (
              <div role="row" className="heat-row" key={m.label}>
                <span role="rowheader" className="heat-model">{nameOf(m)}</span>
                {fams.map((f) => {
                  const rs = m.byTask.filter((r) => f.tasks.some((t) => t.id === r.task));
                  const n = rs.reduce((a, r) => a + r.trials, 0);
                  if (!n) return <span role="cell" key={f.key} className="heat-cell none">Not tested</span>;
                  const v = rs.reduce((a, r) => a + r.meanScore * r.trials, 0) / n;
                  const b = bucket(v);
                  return (
                    <span role="cell" key={f.key} className={`heat-cell ${b}`}>
                      <strong>{pct(v, 0)}</strong>
                      <small>{bucketWord[b]}</small>
                    </span>
                  );
                })}
              </div>
            ))}
          </div>
        </>
      )}

      {lo && hi && lo.family.key !== hi.family.key && (
        <p className="takeaway">
          <span className="takeaway-mark" aria-hidden="true">!</span>
          <span>
            On average, the models scored <strong>{pct(hi.mean)}</strong> on “{hi.family.name}”, but <strong>{pct(lo.mean)}</strong> on “{lo.family.name}”.
          </span>
        </p>
      )}
      <p className="fine">
        Every score here comes from <Gh data={data} path={run.sourcePath}>the saved results on GitHub</Gh>, run{" "}
        <code>{run.id}</code>.
      </p>
    </section>
  );
}

export function Mistakes({ data, run }: { data: ExplorerData; run: Run | undefined }) {
  const order = data.tasks.map((t) => t.id);
  const list = topMistakes(run, order);
  if (!run) return null;
  const names = Object.fromEntries(run.models.map((m) => [m.label, nameOf(m)]));
  const fams = families(data);
  return (
    <section id="mistakes" aria-labelledby="mistakes-h">
      <h2 id="mistakes-h">Where the AI slipped</h2>
      {list.length === 0 ? (
        <p className="empty">No model made a checkable mistake in this run.</p>
      ) : (
        <>
          <p className="section-lede">Real mistakes from this run, picked automatically: mistakes we can explain in plain words, and that the most models made.</p>
          <div className="mistakes">
            {list.map((m) => {
              const task = data.tasks.find((t) => t.id === m.task);
              const fam = fams.find((f) => f.tasks.some((t) => t.id === m.task));
              const rule = m.example.reference;
              return (
                <article key={`${m.task}/${m.check}`} className="mistake">
                  <p className="mistake-topic"><Icon name={fam?.icon ?? "ticket"} size={22} /> {fam?.name ?? task?.category}</p>
                  <h3>{task?.title ?? m.task}</h3>
                  <div className="answer">
                    <div className="answer-wrong">
                      <span className="answer-label">AI answered</span>
                      <span className="answer-value"><s>{figure(m.got)}</s></span>
                    </div>
                    <div className="answer-right">
                      <span className="answer-label">Correct answer</span>
                      <span className="answer-value">{figure(m.expected)}</span>
                    </div>
                  </div>
                  {rule?.rule && <p className="mistake-rule"><strong>The rule:</strong> {rule.rule}</p>}
                  <p className="mistake-who">
                    {m.models.map((x) => names[x] ?? x).join(" and ")} got this wrong in {m.failedTrials} of {plural(m.trialsRun, "attempt")}.
                  </p>
                  <p className="mistake-link">
                    <Gh data={data} path={m.example.transcriptPath ?? m.example.sourcePath}>Read the AI's full answer</Gh>
                  </p>
                </article>
              );
            })}
          </div>
          <p className="fine">
            See all {plural(run.failures.length, "recorded mistake")} in <Gh data={data} path={run.summaryPath ?? run.sourcePath}>the full results on GitHub</Gh>.
          </p>
        </>
      )}
    </section>
  );
}

export function Fairness({ data }: { data: ExplorerData }) {
  const wrong = data.tasks.reduce((n, t) => n + t.mutantCount, 0);
  return (
    <section id="fair" aria-labelledby="fair-h">
      <h2 id="fair-h">Why you can trust these scores</h2>
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
      {data.limitations.items.length > 0 && (
        <p className="fine">
          What this test does not show is listed under <Gh data={data} path={data.limitations.sourcePath}>limitations in the README</Gh>.
        </p>
      )}
    </section>
  );
}

export function Details({ data }: { data: ExplorerData }) {
  const links: [string, string, boolean][] = [
    ["Every problem, word for word", "tasks", true],
    ["The checkers that mark each answer", "graders", true],
    ["Every AI answer and score", "results", true],
    ["The AI answers that went wrong", "transcripts", true],
    ["Full write-up and limitations", "README.md", false],
  ];
  return (
    <section id="details" aria-labelledby="details-h" className="details">
      <h2 id="details-h">Want the details?</h2>
      <p className="section-lede">Everything behind this page is public on GitHub.</p>
      <ul className="detail-links">
        {links.map(([label, path, dir]) => (
          <li key={path}><Gh data={data} path={path} dir={dir}>{label}</Gh></li>
        ))}
      </ul>
    </section>
  );
}

export function CrossProvider({ data, headline }: { data: ExplorerData; headline: Run | undefined }) {
  const runs = data.runs.filter((r) => r.role === "cross-provider");
  if (!headline || runs.length === 0) return null;
  const fams = families(data);
  const rows = [
    ...headline.models.map((m) => ({ m, attempts: m.trialsPerTask[0] ?? 1, run: headline })),
    ...runs.flatMap((r) => r.models.map((m) => ({ m, attempts: m.trialsPerTask[0] ?? 1, run: r }))),
  ];
  const names = Object.fromEntries(rows.map(({ m }) => [m.label, nameOf(m)]));
  const shared = runs.flatMap((r) => sharedMistakes(headline, r)).slice(0, 3);
  return (
    <section id="others" aria-labelledby="others-h">
      <h2 id="others-h">Does this only happen with Claude?</h2>
      <p className="section-lede">We gave the same problems to a free model from another company, NVIDIA, to see whether the same weak spots appear.</p>
      <div className="heat" role="table" aria-label="Average score by model and kind of problem, across companies" style={{ gridTemplateColumns: `minmax(150px, 1.3fr) repeat(${fams.length}, minmax(96px, 1fr))` }}>
        <div role="row" className="heat-row heat-head">
          <span role="columnheader" />
          {fams.map((f) => <span role="columnheader" key={f.key}><Icon name={f.icon} size={26} /> {f.name}</span>)}
        </div>
        {rows.map(({ m, attempts, run }) => (
          <div role="row" className={`heat-row ${run.role === "cross-provider" ? "heat-new" : ""}`} key={`${run.id}/${m.label}`}>
            <span role="rowheader" className="heat-model">
              <span>{nameOf(m)}<small className="heat-sub">{plural(attempts, "attempt")} per problem</small></span>
            </span>
            {fams.map((f) => {
              const v = familyScore(m, f);
              if (v === null) return <span role="cell" key={f.key} className="heat-cell none">Not tested</span>;
              const b = bucket(v);
              return <span role="cell" key={f.key} className={`heat-cell ${b}`}><strong>{pct(v, 0)}</strong><small>{bucketWord[b]}</small></span>;
            })}
          </div>
        ))}
      </div>
      {shared.length > 0 && (
        <div className="shared">
          <h3>The same mistakes, from a different company</h3>
          <ul>
            {shared.map((x) => (
              <li key={`${x.task}/${x.check}`}>
                <span className="shared-x" aria-hidden="true">✗</span>
                <span>
                  <strong>{x.rule}</strong>
                  <small>Missed by {[...x.newModels, ...x.others].map((l) => names[l] ?? l).join(", ")}.</small>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {runs.flatMap((r) => r.notes).length > 0 && (
        <ul className="notes">
          {runs.flatMap((r) => r.notes.map((n) => <li key={n}>{n}</li>))}
        </ul>
      )}
      <p className="fine">
        {runs.map((r) => <span key={r.id}>Results: <Gh data={data} path={r.sourcePath}>{r.id}</Gh>. </span>)}
        One attempt per problem is a quick check, not as strong as the three attempts in the main test.
      </p>
    </section>
  );
}

export function Advanced({ data }: { data: ExplorerData }) {
  const runs = data.runs.filter((r) => r.role === "advanced");
  const tasks = data.tasks.filter((t) => t.experimental && runs.some((r) => r.tasks.includes(t.id)));
  if (tasks.length === 0) return null;
  return (
    <section id="hardest" aria-labelledby="hardest-h">
      <h2 id="hardest-h">The hardest test</h2>
      {tasks.map((t) => {
        const results = runs.flatMap((r) => r.models.map((m) => ({ r, m, res: m.byTask.find((x) => x.task === t.id) })).filter((x) => x.res));
        return (
          <div key={t.id}>
            <p className="section-lede">{t.challenge ?? t.tests ?? t.title}</p>
            <div className="verdicts">
              {results.map(({ r, m, res }) => {
                const err = r.errors.find((e) => e.model === m.label && e.task === t.id);
                const failures = r.failures.filter((f) => f.model === m.label && f.task === t.id).length;
                const passed = res!.fullPasses === res!.trials;
                return (
                  <article key={`${r.id}/${m.label}`} className={`verdict ${passed ? "ok" : "no"}`}>
                    <span className="verdict-mark" aria-hidden="true">{passed ? "✓" : "✗"}</span>
                    <h3>{nameOf(m)}</h3>
                    <p className="verdict-line">
                      {passed
                        ? "Passed every check"
                        : err?.finishReason === "length"
                          ? "Ran out of space before finishing its answer"
                          : err
                            ? "Gave no answer that could be checked"
                            : `Got ${failures} check${failures === 1 ? "" : "s"} wrong`}
                    </p>
                    <p className="verdict-sub">{plural(res!.trials, "attempt")}, score {pct(res!.meanScore, 0)}</p>
                    <p className="verdict-link"><Gh data={data} path={r.sourcePath}>Result on GitHub</Gh></p>
                  </article>
                );
              })}
            </div>
            <p className="fine">
              A new, experimental problem: a month-end close for a Nigerian wallet company, with timeouts, duplicates, reversals, corrected
              bank files and currency rates all interacting. It is not part of the main scores. <Gh data={data} path={t.sourcePath}>Read the problem</Gh>
            </p>
          </div>
        );
      })}
    </section>
  );
}
