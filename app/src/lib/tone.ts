// -----------------------------------------------------------------------------
// The Tone manipulation (calibrated-honest vs sycophantic).
//
// INVARIANT I2 -- THIS MODULE MUST NOT SEE GROUND TRUTH.
//
// The only inputs are the recommended item's display name and the number of
// requirements the agent addressed. Nothing here can depend on whether a trial is
// seeded with an error. If tone varied with correctness, the honest agent would
// effectively be flagging its own mistakes and H3/H4 would be uninterpretable.
//
// `stimuli/validate_trials.py` greps this file for ground-truth identifiers and
// fails the build if any appear. Keep it that way.
//
// Both registers are applied on EVERY trial, including clean ones. The honest
// agent's hedging is a constant stylistic register, not a correctness signal.
// -----------------------------------------------------------------------------

import type { Tone } from "../types";
import type { Rng } from "./rng";
import { pick } from "./rng";

export interface ToneContext {
  itemName: string;
  /** how many of the participant's requirements the agent reported on */
  nClaims: number;
}

export interface ToneCopy {
  opener: string;
  verdict: string;
  closer: string;
}

const HONEST_OPENERS = [
  "Here's what I found.",
  "I've gone through the catalogue for this one.",
  "Here are the results of my search.",
  "I've had a look at the available options.",
  "This is what my search returned.",
];

const HONEST_VERDICTS = [
  (c: ToneContext) =>
    `Based on the ${c.nClaims} requirement${c.nClaims === 1 ? "" : "s"} I checked, ${c.itemName} is the closest match I found.`,
  (c: ToneContext) =>
    `${c.itemName} is my best candidate against the ${c.nClaims} requirement${c.nClaims === 1 ? "" : "s"} I was able to check.`,
  (c: ToneContext) =>
    `Of the options I compared, ${c.itemName} came out ahead on the criteria I checked.`,
];

const HONEST_CLOSERS = [
  "My catalogue data can be incomplete or out of date, so it's worth confirming anything that matters to you before committing.",
  "I may have missed something — please check the details that matter most to you before deciding.",
  "I can't guarantee I've got every detail right, so do verify the specifics that are important to you.",
  "Treat this as a starting point rather than a final answer; the details are worth a second look.",
];

const SYCO_OPENERS = [
  "Great news — I found exactly what you're after!",
  "Excellent choice of requirements — you clearly know what you want!",
  "You're going to love this one!",
  "Perfect — this was a really smart set of criteria to search on.",
  "Wonderful request! I found something great for you.",
];

const SYCO_VERDICTS = [
  (c: ToneContext) => `${c.itemName} ticks every single box on your list.`,
  (c: ToneContext) => `${c.itemName} is a flawless match for what you asked for.`,
  (c: ToneContext) => `${c.itemName} nails all ${c.nClaims} of your requirements.`,
];

const SYCO_CLOSERS = [
  "You really can't go wrong with this one — it's an excellent pick.",
  "I'm completely confident this is the right choice for you.",
  "This is exactly the kind of option someone with your priorities should go for.",
  "Honestly, this is the standout choice here — great instincts on your part.",
];

/**
 * Build the tone-styled wrapper around a trial's factual agent output.
 *
 * Variants are drawn from the participant-seeded RNG, so the specific phrasing is
 * random with respect to trial position and therefore cannot become correlated
 * with the fixed error slots.
 */
export function toneCopy(tone: Tone, ctx: ToneContext, rng: Rng): ToneCopy {
  if (tone === "honest") {
    return {
      opener: pick(HONEST_OPENERS, rng),
      verdict: pick(HONEST_VERDICTS, rng)(ctx),
      closer: pick(HONEST_CLOSERS, rng),
    };
  }
  return {
    opener: pick(SYCO_OPENERS, rng),
    verdict: pick(SYCO_VERDICTS, rng)(ctx),
    closer: pick(SYCO_CLOSERS, rng),
  };
}

/** Label for the confidence badge the agent shows next to its pick. */
export function toneConfidenceBadge(tone: Tone): string {
  return tone === "honest" ? "Best available match" : "Perfect match";
}
