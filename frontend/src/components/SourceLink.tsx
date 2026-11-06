import type { ExplorerData } from "../types";
import { sourceUrl } from "../lib/links";

export function SourceLink({ data, path, label = "View source", dir = false }: { data: ExplorerData; path: string; label?: string; dir?: boolean }) {
  const url = sourceUrl(data, path, dir);
  if (!url) return <span className="src">{path}</span>;
  return (
    <a className="src" href={url} target="_blank" rel="noreferrer" title={`${path} at commit ${data.commitSha.slice(0, 7)}`}>
      {label}
      <span className="visually-hidden"> ({path}, opens GitHub)</span>
    </a>
  );
}

export function Mark({ ok, label }: { ok: boolean; label?: string }) {
  return (
    <span className={ok ? "mark pass" : "mark fail"}>
      <span aria-hidden="true">{ok ? "✓" : "✗"}</span> {label ?? (ok ? "Pass" : "Fail")}
    </span>
  );
}
