import { useEffect, useState } from "react";
import type { ExplorerData } from "../types";

export type Freshness =
  | { state: "checking" }
  | { state: "current" }
  | { state: "behind"; latestSha: string; latestDate: string | null }
  | { state: "unknown"; reason: string };

/** Compares the commit this site was built from with the branch's current head on GitHub.
 *  If a newer commit exists, its build either is still running or failed, and this page may be out of date.
 *  Uses GitHub's public API without a key; a failure here only means the check could not run. */
export function useFreshness(data: ExplorerData): Freshness {
  const [f, setF] = useState<Freshness>({ state: "checking" });
  useEffect(() => {
    if (!data.repository || !data.branch) {
      setF({ state: "unknown", reason: "This build does not record its repository and branch." });
      return;
    }
    const ctrl = new AbortController();
    fetch(`https://api.github.com/repos/${data.repository}/commits/${encodeURIComponent(data.branch)}`, {
      signal: ctrl.signal,
      headers: { Accept: "application/vnd.github+json" },
    })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`GitHub answered ${r.status}`))))
      .then((c: { sha: string; commit?: { committer?: { date?: string } } }) =>
        setF(c.sha === data.commitSha ? { state: "current" } : { state: "behind", latestSha: c.sha, latestDate: c.commit?.committer?.date ?? null }),
      )
      .catch((e: Error) => {
        if (e.name !== "AbortError") setF({ state: "unknown", reason: e.message });
      });
    return () => ctrl.abort();
  }, [data.repository, data.branch, data.commitSha]);
  return f;
}
