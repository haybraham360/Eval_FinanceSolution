import type { ExplorerData } from "../types";

/** A link to a file at the exact commit this site was built from, never the moving branch head. */
export function sourceUrl(data: ExplorerData, path: string, isDir = false): string | null {
  if (!data.repository) return null;
  return `https://github.com/${data.repository}/${isDir ? "tree" : "blob"}/${data.commitSha}/${path}`;
}

export function commitUrl(data: ExplorerData): string | null {
  return data.repository ? `https://github.com/${data.repository}/commit/${data.commitSha}` : null;
}
