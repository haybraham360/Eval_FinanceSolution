import { useEffect, useState } from "react";
import type { ExplorerData } from "./types";
import { Masthead } from "./components/Masthead";
import { Advanced, CrossProvider, Details, Fairness, Hero, HowItWorks, Mistakes, Scoreboard, WhatWeTest } from "./components/Story";

export function Explorer({ data }: { data: ExplorerData }) {
  const run = data.runs.find((r) => r.id === data.defaultRunId);
  return (
    <>
      <a className="skip" href="#results">Skip to results</a>
      <Masthead data={data} />
      <main>
        <Hero data={data} run={run} />
        <WhatWeTest data={data} />
        <HowItWorks />
        <Scoreboard data={data} run={run} />
        <Mistakes data={data} run={run} />
        <CrossProvider data={data} headline={run} />
        <Advanced data={data} />
        <Fairness data={data} />
        <Details data={data} />
      </main>
      <footer>
        <p>
          This page reads the {data.repository ? <a href={`https://github.com/${data.repository}`}>Ledger-Eval repository</a> : "repository"} and
          updates itself after every change. It makes no AI calls, and nothing you do here changes a result.
        </p>
      </footer>
    </>
  );
}

type Load = { state: "loading" } | { state: "ready"; data: ExplorerData } | { state: "error"; message: string };

export default function App() {
  const [load, setLoad] = useState<Load>({ state: "loading" });
  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}explorer-data.json`, { cache: "no-cache" })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`the data file answered ${r.status}`))))
      .then((d: ExplorerData) => {
        if (d.schemaVersion !== 1) throw new Error(`unsupported data schema ${String(d.schemaVersion)}`);
        setLoad({ state: "ready", data: d });
      })
      .catch((e: Error) => setLoad({ state: "error", message: e.message }));
  }, []);
  if (load.state === "loading") return <p className="state" role="status">Loading the latest results…</p>;
  if (load.state === "error")
    return (
      <div className="state" role="alert">
        <h1>The results could not be loaded</h1>
        <p>Reason: {load.message}. For a local preview, run <code>npm run data</code> in frontend/ first.</p>
      </div>
    );
  return <Explorer data={load.data} />;
}
