import { useMemo, useRef, useState } from "react";
import { APP_VERSION } from "./config";
import catalogJson from "./data/catalog.json";
import trialsJson from "./data/trials.json";
import { orderTrials, readLaunch } from "./lib/assignment";
import { EventLog, saveLocal } from "./lib/logging";
import type {
  Catalog, Phase, SessionPayload, SurveyResponses, Trial, TrialResponse,
} from "./types";
import { Comprehension, Consent, Instructions } from "./components/Intro";
import { TrialScreen } from "./components/TrialScreen";
import { Survey } from "./components/Survey";
import { Debrief, Excluded } from "./components/Debrief";

const catalog = catalogJson as unknown as Catalog;
const allTrials = (trialsJson as unknown as { trials: Trial[] }).trials;

export default function App() {
  // Launch parameters are read once: re-reading would reroll the condition.
  const launch = useMemo(() => readLaunch(), []);
  const log = useRef(new EventLog());
  const trials = useMemo(
    () => orderTrials(allTrials, launch.rng),
    [launch],
  );

  const [phase, setPhase] = useState<Phase>("consent");
  const [trialIndex, setTrialIndex] = useState(0);
  const [responses, setResponses] = useState<TrialResponse[]>([]);
  const [survey, setSurvey] = useState<SurveyResponses>({});
  const [comprehensionAttempts, setComprehensionAttempts] = useState(0);

  const buildPayload = (
    trialResponses: TrialResponse[],
    surveyResponses: SurveyResponses,
    attempts: number,
  ): SessionPayload => ({
    meta: {
      participantId: launch.participantId,
      prolificPid: launch.prolificPid,
      studyId: launch.studyId,
      sessionId: launch.sessionId,
      condition: launch.condition,
      slotOrder: trials.map((t) => t.slot),
      startedAt: startedAt.current,
      userAgent: navigator.userAgent,
      screen: { w: window.innerWidth, h: window.innerHeight },
      appVersion: APP_VERSION,
      isPreview: launch.isPreview,
    },
    trials: trialResponses,
    survey: surveyResponses,
    comprehensionAttempts: attempts,
    completedAt: null,
    events: log.current.all(),
  });

  const startedAt = useRef(new Date().toISOString());

  const go = (next: Phase, payload?: Record<string, unknown>) => {
    log.current.add(`phase:${next}`, payload);
    setPhase(next);
    window.scrollTo({ top: 0 });
  };

  const onTrialComplete = (r: TrialResponse) => {
    const next = [...responses, r];
    setResponses(next);
    log.current.add("trial:complete", {
      trialId: r.trialId,
      slot: r.slot,
      decision: r.decision,
      confidence: r.confidence,
      rtMs: r.rtMs,
      nVerifications: r.verifications.length,
    });
    // Mirror progress after every trial so a mid-session drop-out is recoverable.
    saveLocal(buildPayload(next, survey, comprehensionAttempts));

    if (trialIndex + 1 >= trials.length) {
      go("survey");
    } else {
      setTrialIndex((i) => i + 1);
    }
  };

  switch (phase) {
    case "consent":
      return (
        <Shell>
          <Consent
            onConsent={() => {
              log.current.add("consent:given", { condition: launch.condition });
              go("instructions");
            }}
          />
        </Shell>
      );

    case "instructions":
      return (
        <Shell>
          <Instructions onNext={() => go("comprehension")} />
        </Shell>
      );

    case "comprehension":
      return (
        <Shell>
          <Comprehension
            onPass={(attempts) => {
              setComprehensionAttempts(attempts);
              go("trials", { attempts });
            }}
            onFail={(attempts) => {
              setComprehensionAttempts(attempts);
              go("excluded", { reason: "comprehension", attempts });
            }}
          />
        </Shell>
      );

    case "trials":
      return (
        <Shell>
          <TrialScreen
            trial={trials[trialIndex]}
            index={trialIndex}
            total={trials.length}
            condition={launch.condition}
            catalog={catalog}
            rng={launch.rng}
            onComplete={onTrialComplete}
          />
        </Shell>
      );

    case "survey":
      return (
        <Shell>
          <Survey
            onDone={(r) => {
              setSurvey(r);
              go("debrief");
            }}
          />
        </Shell>
      );

    case "debrief":
      return (
        <Shell>
          <Debrief
            payload={buildPayload(responses, survey, comprehensionAttempts)}
            trials={trials}
            responses={responses}
          />
        </Shell>
      );

    case "excluded":
      return (
        <Shell>
          <Excluded />
        </Shell>
      );

    default:
      return null;
  }
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="app">
      <main>{children}</main>
    </div>
  );
}
