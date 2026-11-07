import type { ExplorerData } from "../types";
import { commitUrl } from "../lib/links";
import { stamp } from "../lib/format";
import { useFreshness } from "../lib/freshness";

const SECTIONS = [
  ["findings", "Summary"],
  ["how", "How it works"],
  ["results", "Results"],
  ["mistakes", "Mistakes"],
  ["hardest", "Harder tests"],
  ["trust", "Trust"],
] as const;

export function Masthead({ data }: { data: ExplorerData }) {
  const f = useFreshness(data);
  const short = data.commitSha.slice(0, 7);
  const url = commitUrl(data);
  return (
    <>
      <header className="masthead">
        <a className="wordmark" href="#top">Ledger-Eval</a>
        <nav aria-label="Sections">
          {SECTIONS.map(([id, label]) => (
            <a key={id} href={`#${id}`}>{label}</a>
          ))}
        </nav>
        <p className="sync" title={`Site data built ${stamp(data.generatedAt)}`}>
          Updated from GitHub {stamp(data.commitDate)}{" "}
          <span className="sync-detail">
            (commit {url ? <a href={url} target="_blank" rel="noreferrer"><code>{short}</code></a> : <code>{short}</code>})
          </span>
        </p>
      </header>
      {data.dirtyWorkingTree && (
        <p className="banner warn" role="status">
          Local preview: built from uncommitted files. The published site shows only what is committed.
        </p>
      )}
      {f.state === "behind" && (
        <p className="banner warn" role="status">
          This page may be out of date. It was built from <code>{short}</code>, but <code>{data.branch}</code> is now at{" "}
          <code>{f.latestSha.slice(0, 7)}</code>
          {f.latestDate ? ` (committed ${stamp(f.latestDate)})` : ""}. That commit's build is still running or failed.
        </p>
      )}
    </>
  );
}
