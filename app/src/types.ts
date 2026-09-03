// Shared types for the TrustLoop experiment app.
// Ground-truth fields (isErrorTrial, violatedConstraintIds, ...) are present in the
// bundled stimuli but MUST NOT influence anything the participant sees except via
// the scripted agent output. See stimuli/validate_trials.py invariant I2.

export type Disclosure = "opaque" | "full";
export type Tone = "honest" | "sycophantic";

export interface Condition {
  disclosure: Disclosure;
  tone: Tone;
}

export type Op = "lt" | "lte" | "gt" | "gte" | "eq" | "neq";

export interface Constraint {
  id: string;
  field: string;
  op: Op;
  value: number | boolean;
  label: string;
}

export interface FieldMeta {
  label: string;
  unit: string;
  kind: "number" | "currency" | "bool";
}

export interface CatalogItem {
  id: string;
  domain: "laptop" | "trip";
  name: string;
  [field: string]: string | number | boolean;
}

export interface Catalog {
  fieldMeta: Record<string, FieldMeta>;
  specCardFields: Record<string, string[]>;
  items: Record<string, CatalogItem>;
}

export interface ToolCall {
  kind: "search" | "filter" | "read" | "compare";
  label: string;
  detail?: string;
  url?: string;
  durationMs: number;
}

export interface Citation {
  n: number;
  url: string;
  itemId: string;
  sourceType: "shop" | "review" | "forum";
  anchor: string | null;
  label: string;
}

export interface AgentBlock {
  type: "h" | "p" | "candidate";
  text?: string;
  /** candidate blocks only */
  name?: string;
  price?: string;
  cite?: number;
}

export interface AgentResponse {
  blocks: AgentBlock[];
  citations: Citation[];
}

/** What the agent asserted about the recommended item. Scoring only, never rendered. */
export interface StatedFact {
  itemId: string;
  field: string;
  statedValue: number | boolean;
  statedValueText: string;
  catalogValue: number | boolean;
  catalogValueText: string;
  isFalse: boolean;
  constraintId: string | null;
  sourceUrl: string;
}

/** The single fact that determines the trial's correctness, and where truth lives. */
export interface DisputedFact {
  kind: "omission" | "contradiction";
  field: string;
  constraintId: string | null;
  statedValue?: number | boolean;
  statedValueText?: string;
  catalogValue: number | boolean;
  catalogValueText: string;
  sourceUrl: string;
}

export interface Trial {
  id: string;
  slot: number;
  domain: "laptop" | "trip";
  prompt: string;
  constraints: Constraint[];
  candidateIds: string[];
  recommendedId: string;
  specCardFields: string[];
  // --- ground truth: scoring only, never rendered ---
  isErrorTrial: boolean;
  errorType: "dropped_constraint" | "false_claim" | "arithmetic" | null;
  violatedConstraintIds: string[];
  compliantCandidateIds: string[];
  statedFacts: StatedFact[];
  disputedFact: DisputedFact | null;
  // --- agent output ---
  toolCalls: ToolCall[];
  response: AgentResponse;
}

/** One source visit during a trial. */
export interface SourceVisit {
  url: string;
  itemId: string;
  sourceType: string;
  /** ms since the trial was first rendered */
  tMs: number;
  dwellMs: number;
  maxScrollPct: number;
  /** spec-table rows that were on screen long enough to read, and for how long */
  specRowsSeen: Record<string, number>;
}

export interface TrialResponse {
  trialId: string;
  slot: number;
  /** 1-7; confidence that the agent's recommendation meets all requirements */
  confidence: number;
  decision: "accept" | "override";
  /** item chosen by the participant (equals recommendedId when accepted) */
  chosenId: string;
  /** ms from first render to submitting the decision */
  rtMs: number;
  /** every source page opened during this trial, in order */
  sourceVisits: SourceVisit[];
  /** ms from render to the agent finishing its response (waiting time) */
  agentDoneMs: number;
  /** did the participant open the page carrying the disputed fact? */
  visitedDisputedSource: boolean;
  /** did the disputed spec row actually spend time on screen? */
  sawDisputedRowMs: number;
}

export type SurveyResponses = Record<string, number | string>;

export type Phase =
  | "consent"
  | "instructions"
  | "comprehension"
  | "trials"
  | "survey"
  | "debrief"
  | "done"
  | "excluded";

export interface SessionMeta {
  participantId: string;
  /** platform-supplied ids, when present in the URL */
  prolificPid: string | null;
  studyId: string | null;
  sessionId: string | null;
  condition: Condition;
  /** presentation order of trial slots actually shown */
  slotOrder: number[];
  startedAt: string;
  userAgent: string;
  screen: { w: number; h: number };
  appVersion: string;
  /** true when the run was launched with ?preview=1 (piloting, excluded from analysis) */
  isPreview: boolean;
}

export interface SessionPayload {
  meta: SessionMeta;
  trials: TrialResponse[];
  survey: SurveyResponses;
  comprehensionAttempts: number;
  completedAt: string | null;
  /** durable event log: every state transition and interaction */
  events: LoggedEvent[];
  /** behavioural telemetry: source visits, cursor traces, attention proxies */
  telemetry?: { events: unknown[]; traces: unknown[] };
}

export interface LoggedEvent {
  t: string;
  kind: string;
  payload?: Record<string, unknown>;
}
