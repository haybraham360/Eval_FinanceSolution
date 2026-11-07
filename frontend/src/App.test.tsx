import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Explorer } from "./App";
import { families, figure, topMistakes } from "./lib/insights";
import type { ExplorerData, ModelResult, Run } from "./types";

const settings = { requested: [], resolved: [], providers: [], params: ["{}"], systemPrompt: "sys", backend: null, effort: null, configPath: null };

function model(label: string, mean: number): ModelResult {
  return {
    label, displayName: label === "brand-new-model" ? "Brand New Model 1" : label, tier: "free", trials: 1, meanScore: mean, fullPasses: mean === 1 ? 1 : 0, fullPassRate: mean === 1 ? 1 : 0,
    tasksPassedEveryTrial: mean === 1 ? 1 : 0, tasksPassedOnce: mean === 1 ? 1 : 0, tasksAttempted: 1, trialsPerTask: [1],
    coversAllCoreTasks: true, complete: true, byTask: [{ task: "t1_alpha", trials: 1, fullPasses: mean === 1 ? 1 : 0, meanScore: mean }],
    byCategory: [{ category: "Engineering", trials: 1, meanScore: mean }], settings, sourcePath: "results/r1/scores.json",
  };
}

function fixture(models: ModelResult[], over: Partial<ExplorerData> = {}): ExplorerData {
  const run: Run = {
    id: "r1", sourcePath: "results/r1/scores.json", summaryPath: null, firstTrialUtc: "2026-10-31T10:00:00+00:00",
    lastTrialUtc: "2026-10-31T11:00:00+00:00", trials: models.length, checksRun: models.length * 2, tasks: ["t1_alpha"], complete: true, models,
    failures: [{ model: "m-a", task: "t1_alpha", check: "c2", message: "AssertionError: c2.total: expected 1950000, got 2160000",
      failedTrials: [1], trialsRun: 1, transcriptPath: null, transcriptTrial: null, rawPath: null, reference: null, sourcePath: "results/r1/scores.json" }],
    errors: [], role: "headline", title: null, notes: [], metaPath: null,
  };
  return {
    schemaVersion: 1, generatedAt: "2026-11-06T12:00:00+00:00", commitSha: "abcdef1234567890", commitDate: "2026-11-06T11:00:00+00:00",
    dirtyWorkingTree: false, repository: "owner/repo", branch: "main", project: { title: "P", intro: [], sourcePath: "README.md" },
    limitations: { title: "Limitations", items: ["Only a fixture."], sourcePath: "README.md" },
    tasks: [{ id: "t1_alpha", title: "Alpha task", kind: "python", experimental: false, category: "Engineering", tests: "Alpha things", challenge: null,
      prompt: "# prompt", sourcePath: "tasks/t1_alpha/prompt.md", metaPath: "tasks/t1_alpha/meta.json", describedIn: "README.md",
      graderPath: null, referencePaths: [], alternativePaths: [], mutantCount: 0 }],
    runs: [run], defaultRunId: "r1", defaultRunRule: "rule", warnings: [], ...over,
  };
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));
  vi.stubGlobal("ResizeObserver", class { observe() {} unobserve() {} disconnect() {} });
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("the page follows the data bundle", () => {
  it("shows a model that only exists in the data, with no component change", () => {
    render(<Explorer data={fixture([model("m-a", 0.5), model("brand-new-model", 1)])} />);
    const table = screen.getByRole("table", { name: "Scores by model" });
    expect(within(table).getByText("Brand New Model 1")).toBeTruthy();
    expect(within(table).getByText("100.0%")).toBeTruthy();
  });

  it("shows when the site was last updated and links the exact commit", () => {
    render(<Explorer data={fixture([model("m-a", 0.5)])} />);
    const link = screen.getByRole("link", { name: "abcdef1" });
    expect(link.getAttribute("href")).toBe("https://github.com/owner/repo/commit/abcdef1234567890");
  });

  it("builds mistake cards from the grader's own message", () => {
    const d = fixture([model("m-a", 0.5)]);
    expect(topMistakes(d.runs[0], ["t1_alpha"])[0]).toMatchObject({ expected: "1950000", got: "2160000", check: "c2", models: ["m-a"] });
    render(<Explorer data={d} />);
    expect(screen.getByText("2,160,000")).toBeTruthy();
    expect(screen.getByText("1,950,000")).toBeTruthy();
  });

  it("groups problems by the README family", () => {
    expect(families(fixture([model("m-a", 0.5)])).map((f) => [f.key, f.tasks.length])).toEqual([["Engineering", 1]]);
  });

  it("says results are not published when there are no runs", () => {
    render(<Explorer data={fixture([], { runs: [], defaultRunId: null })} />);
    expect(screen.getAllByText(/not published yet/i).length).toBeGreaterThan(0);
  });

  it("derives the short-version findings from the scores, not from copy", () => {
    const d = fixture([model("m-a", 0.5)]);
    d.tasks.push({ ...d.tasks[0], id: "t2_beta", title: "Beta task", category: "Operations" });
    d.runs[0].models[0].byTask.push({ task: "t2_beta", trials: 1, fullPasses: 0, meanScore: 0.2 });
    render(<Explorer data={d} />);
    expect(screen.getByText("Hardest area: Operations")).toBeTruthy();
    cleanup();
    d.runs[0].models[0].byTask[1].meanScore = 0.9;
    render(<Explorer data={d} />);
    expect(screen.getByText("Hardest area: Engineering")).toBeTruthy();
  });

  it("flags a local build from uncommitted files", () => {
    render(<Explorer data={fixture([model("m-a", 0.5)], { dirtyWorkingTree: true })} />);
    expect(screen.getByText(/Local preview: built from uncommitted files/)).toBeTruthy();
  });
});

describe("figure", () => {
  it("groups plain numbers and leaves anything else verbatim", () => {
    expect([figure("20000000"), figure("1950000.0"), figure("'2592000'"), figure("12.50"), figure("None")]).toEqual(["20,000,000", "1,950,000", "2,592,000", "12.5", "None"]);
  });
});

describe("mistake cards stay readable", () => {
  it("skips grader messages whose values are not plain numbers", async () => {
    const { isPlainNumber } = await import("./lib/insights");
    expect(["20000000", "1950000.0", "'2592000'", "-12.5"].every(isPlainNumber)).toBe(true);
    expect(["None", "'23505'x", "[1, 2]", "True"].some(isPlainNumber)).toBe(false);
  });
});

describe("mistake selection", () => {
  it("caps cards per task and overall, explained mistakes first", async () => {
    const { topMistakes } = await import("./lib/insights");
    const mk = (task: string, check: string, ruled: boolean) => ({
      model: "m-a", task, check, message: `AssertionError: ${check}: expected 10, got 5`, failedTrials: [1], trialsRun: 1,
      transcriptPath: null, transcriptTrial: null, rawPath: null, sourcePath: "s",
      reference: ruled ? { provision: "s.1", rule: "A rule", sourcePath: "r" } : null,
    });
    const run = { failures: [mk("t1", "a", true), mk("t1", "b", true), mk("t1", "c", true), mk("t1", "d", true), mk("t2", "a", true), mk("t3", "a", false)] } as never;
    const got = topMistakes(run, ["t1", "t2", "t3"]).map((m) => `${m.task}/${m.check}`);
    expect(got).toEqual(["t1/a", "t2/a", "t1/b", "t1/c"]);
  });

  it("skips values that look identical once formatted", async () => {
    const { topMistakes } = await import("./lib/insights");
    const f = { model: "m", task: "t1", check: "E37", message: "AssertionError: E37: expected '2592000.000000', got '2592000'", failedTrials: [1], trialsRun: 1,
      transcriptPath: null, transcriptTrial: null, rawPath: null, sourcePath: "s", reference: { provision: "x", rule: "y", kind: "explanation" as const, sourcePath: "r" } };
    expect(topMistakes({ failures: [f] } as never, ["t1"])).toEqual([]);
  });
});
