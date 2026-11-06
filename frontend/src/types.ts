// The data contract produced by scripts/export_explorer_data.py (schemaVersion 1).
// Every metric carries the repository path it was derived from (sourcePath), so the UI can link to it.

export interface Task {
  id: string;
  title: string;
  kind: "python" | "json";
  experimental: boolean;
  category: string | null; // from the README task tables; null if the README does not describe the task
  tests: string | null;
  challenge: string | null;
  prompt: string;
  sourcePath: string; // tasks/<id>/prompt.md
  metaPath: string;
  describedIn: string | null;
  graderPath: string | null;
  referencePaths: string[];
  alternativePaths: string[];
  mutantCount: number;
}

export interface TaskResult {
  task: string;
  trials: number;
  fullPasses: number;
  meanScore: number;
}

export interface CategoryResult {
  category: string;
  trials: number;
  meanScore: number;
}

export interface ModelSettings {
  requested: string[];
  resolved: string[];
  providers: string[];
  params: string[];
  systemPrompt: string | null;
  backend: string | null;
  effort: string | null;
  configPath: string | null;
}

export interface ModelResult {
  label: string;
  displayName: string; // derived from the recorded model IDs
  tier: string | null;
  trials: number;
  meanScore: number; // mean of trial scores (partial credit)
  fullPasses: number; // trials where every check passed
  fullPassRate: number; // fullPasses / trials, never derived from meanScore
  tasksPassedEveryTrial: number;
  tasksPassedOnce: number;
  tasksAttempted: number;
  trialsPerTask: number[];
  coversAllCoreTasks: boolean;
  complete: boolean;
  byTask: TaskResult[];
  byCategory: CategoryResult[];
  settings: ModelSettings;
  sourcePath: string; // results/<run>/scores.json
}

export interface StatutoryReference {
  provision: string | null;
  rule: string | null;
  sourcePath: string;
}

export interface Failure {
  model: string;
  task: string;
  check: string;
  message: string; // the grader's assertion line, verbatim
  failedTrials: number[];
  trialsRun: number;
  transcriptPath: string | null; // only when the committed transcript is of a failing trial
  transcriptTrial: number | null;
  rawPath: string | null;
  reference: StatutoryReference | null;
  sourcePath: string;
}

export interface TrialError {
  model: string;
  task: string;
  trial: number;
  error: string;
  finishReason: string | null;
}

export interface Run {
  id: string;
  sourcePath: string;
  summaryPath: string | null;
  firstTrialUtc: string;
  lastTrialUtc: string;
  trials: number;
  checksRun: number; // individual checks across all attempts
  tasks: string[];
  complete: boolean;
  models: ModelResult[];
  failures: Failure[];
  errors: TrialError[];
  role: "headline" | "cross-provider" | "advanced" | string | null; // from results/runs.json
  title: string | null;
  notes: string[];
  metaPath: string | null;
}

export interface ExplorerData {
  schemaVersion: 1;
  generatedAt: string;
  commitSha: string;
  commitDate: string | null;
  dirtyWorkingTree: boolean;
  repository: string | null; // "owner/repo"
  branch: string | null;
  project: { title: string | null; intro: string[]; sourcePath: string };
  limitations: { title: string | null; items: string[]; sourcePath: string };
  tasks: Task[];
  runs: Run[];
  defaultRunId: string | null;
  defaultRunRule: string;
  warnings: string[];
}
