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

export interface AgentStep {
  n: number;
  action: string;
  detail: string;
}

export interface AgentClaim {
  constraintId: string;
  field: string;
  fieldLabel: string;
  constraintLabel: string;
  statedValue: number | boolean;
  statedValueText: string;
  catalogValue: number | boolean;
  catalogValueText: string;
  statedSatisfies: boolean;
  trulySatisfies: boolean;
  isFalseClaim: boolean;
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
  // --- agent output ---
  agentSteps: AgentStep[];
  agentClaims: AgentClaim[];
  omittedConstraintIds: string[];
}

/** One verification action: the participant opened the evidence for a claim. */
export interface VerificationEvent {
  constraintId: string;
  /** ms since the trial was first rendered */
  tMs: number;
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
  /** which claims the participant expanded, in order (full condition only) */
  verifications: VerificationEvent[];
  /** whether the participant opened the "other options considered" list */
  openedAlternatives: boolean;
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
}

export interface LoggedEvent {
  t: string;
  kind: string;
  payload?: Record<string, unknown>;
}
