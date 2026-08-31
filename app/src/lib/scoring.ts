// Client-side scoring, used ONLY to give participants honest feedback on the
// debrief screen. The authoritative dependent variables are recomputed from the
// raw logs by analysis/compute_dvs.py -- keep the two definitions in sync.

import type { Trial, TrialResponse } from "../types";

export interface SessionScore {
  nTrials: number;
  nErrorTrials: number;
  /** overrides on seeded-error trials */
  hits: number;
  /** overrides on clean trials (false alarms) */
  falseAlarms: number;
  detectionRate: number;
  falseAlarmRate: number;
  /** accept-when-clean + override-when-seeded, over all trials */
  appropriateReliance: number;
  /** mean confidence on clean minus mean confidence on seeded trials */
  confidenceGap: number;
}

function mean(xs: number[]): number {
  return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : NaN;
}

export function scoreSession(
  trials: Trial[],
  responses: TrialResponse[],
): SessionScore {
  const byId = new Map(trials.map((t) => [t.id, t]));

  let nErr = 0;
  let hits = 0;
  let falseAlarms = 0;
  let appropriate = 0;
  const confClean: number[] = [];
  const confErr: number[] = [];

  for (const r of responses) {
    const t = byId.get(r.trialId);
    if (!t) continue;
    const overrode = r.decision === "override";

    if (t.isErrorTrial) {
      nErr++;
      if (overrode) hits++;
      if (overrode) appropriate++;
      confErr.push(r.confidence);
    } else {
      if (overrode) falseAlarms++;
      if (!overrode) appropriate++;
      confClean.push(r.confidence);
    }
  }

  const nClean = responses.length - nErr;
  return {
    nTrials: responses.length,
    nErrorTrials: nErr,
    hits,
    falseAlarms,
    detectionRate: nErr ? hits / nErr : NaN,
    falseAlarmRate: nClean ? falseAlarms / nClean : NaN,
    appropriateReliance: responses.length ? appropriate / responses.length : NaN,
    confidenceGap: mean(confClean) - mean(confErr),
  };
}
