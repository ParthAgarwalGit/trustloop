// Participant identification, condition assignment, and trial ordering.

import { RANDOMISE_WITHIN_BLOCKS } from "../config";
import type { Condition, Disclosure, Tone, Trial } from "../types";
import { rngFromString, shuffle, type Rng } from "./rng";

const DISCLOSURES: Disclosure[] = ["opaque", "full"];
const TONES: Tone[] = ["honest", "sycophantic"];

export interface Launch {
  participantId: string;
  prolificPid: string | null;
  studyId: string | null;
  sessionId: string | null;
  condition: Condition;
  isPreview: boolean;
  rng: Rng;
}

function randomId(): string {
  const bytes = new Uint8Array(9);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Parse `?cond=` overrides used for piloting and for screenshotting each cell.
 * Accepts e.g. `full-sycophantic`, `opaque-honest`.
 */
function parseCondOverride(raw: string | null): Condition | null {
  if (!raw) return null;
  const [d, t] = raw.toLowerCase().split("-");
  if (DISCLOSURES.includes(d as Disclosure) && TONES.includes(t as Tone)) {
    return { disclosure: d as Disclosure, tone: t as Tone };
  }
  return null;
}

/**
 * Assign a condition.
 *
 * Simple uniform randomisation over the four cells. With N around 200 this lands
 * close to balanced; exact balancing would need server-side counters, which is
 * deliberately out of scope so the app can be hosted as a static site. Realised
 * cell sizes are reported by `analysis/prepare_data.py` -- check them before
 * analysing, and top up any short cell with a follow-up recruitment batch.
 */
export function readLaunch(): Launch {
  const params = new URLSearchParams(window.location.search);

  const prolificPid = params.get("PROLIFIC_PID");
  const studyId = params.get("STUDY_ID");
  const sessionId = params.get("SESSION_ID");
  const participantId = prolificPid ?? params.get("pid") ?? randomId();

  const rng = rngFromString(participantId);
  const override = parseCondOverride(params.get("cond"));
  const condition: Condition = override ?? {
    disclosure: rng() < 0.5 ? "opaque" : "full",
    tone: rng() < 0.5 ? "honest" : "sycophantic",
  };

  return {
    participantId,
    prolificPid,
    studyId,
    sessionId,
    condition,
    isPreview: params.get("preview") === "1",
    rng,
  };
}

/**
 * Order the trials for presentation.
 *
 * Error trials keep their fixed slots (4, 7, 9). Only the *content* is permuted,
 * and only within blocks: clean trials shuffle among clean positions, error trials
 * among error positions. Serial position of errors is therefore identical for every
 * participant in every condition, so it cannot confound the between-subjects
 * comparison, while no single trial's quirks drive the result.
 */
export function orderTrials(all: Trial[], rng: Rng): Trial[] {
  const bySlot = [...all].sort((a, b) => a.slot - b.slot);
  if (!RANDOMISE_WITHIN_BLOCKS) return bySlot;

  const errorPositions: number[] = [];
  const cleanPositions: number[] = [];
  bySlot.forEach((t, i) => (t.isErrorTrial ? errorPositions : cleanPositions).push(i));

  const shuffledErrors = shuffle(errorPositions.map((i) => bySlot[i]), rng);
  const shuffledClean = shuffle(cleanPositions.map((i) => bySlot[i]), rng);

  const out = new Array<Trial>(bySlot.length);
  errorPositions.forEach((pos, k) => (out[pos] = shuffledErrors[k]));
  cleanPositions.forEach((pos, k) => (out[pos] = shuffledClean[k]));
  return out;
}
