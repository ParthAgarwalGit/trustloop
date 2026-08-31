import { useEffect, useMemo, useRef, useState } from "react";
import { CONFIDENCE_ANCHORS, CONFIDENCE_MAX, CONFIDENCE_MIN } from "../config";
import type { Catalog, Condition, Trial, TrialResponse, VerificationEvent } from "../types";
import type { Rng } from "../lib/rng";
import { toneConfidenceBadge, toneCopy } from "../lib/tone";
import { AgentTrace } from "./AgentTrace";
import { SpecCard, formatValue } from "./SpecCard";

export function TrialScreen({
  trial,
  index,
  total,
  condition,
  catalog,
  rng,
  onComplete,
}: {
  trial: Trial;
  index: number;
  total: number;
  condition: Condition;
  catalog: Catalog;
  rng: Rng;
  onComplete: (r: TrialResponse) => void;
}) {
  const [confidence, setConfidence] = useState<number | null>(null);
  const [picking, setPicking] = useState(false);
  const [chosenId, setChosenId] = useState<string | null>(null);
  const verifications = useRef<VerificationEvent[]>([]);
  const openedAlternatives = useRef(false);
  const startedAt = useRef<number>(Date.now());

  // Reset per-trial state whenever the trial changes.
  useEffect(() => {
    setConfidence(null);
    setPicking(false);
    setChosenId(null);
    verifications.current = [];
    openedAlternatives.current = false;
    startedAt.current = Date.now();
    window.scrollTo({ top: 0 });
  }, [trial.id]);

  const recommended = catalog.items[trial.recommendedId];

  // Tone copy is memoised per trial so re-renders don't reroll the phrasing.
  const copy = useMemo(
    () => toneCopy(condition.tone, {
      itemName: recommended.name,
      nClaims: trial.agentClaims.length,
    }, rng),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [trial.id],
  );

  const submit = (decision: "accept" | "override", itemId: string) => {
    if (confidence == null) return;
    onComplete({
      trialId: trial.id,
      slot: trial.slot,
      confidence,
      decision,
      chosenId: itemId,
      rtMs: Date.now() - startedAt.current,
      verifications: verifications.current.slice(),
      openedAlternatives: openedAlternatives.current,
    });
  };

  const alternatives = trial.candidateIds.filter((id) => id !== trial.recommendedId);

  return (
    <div className="screen">
      <div className="progress">
        <div className="progress__bar" style={{ width: `${(index / total) * 100}%` }} />
      </div>
      <p className="progress__label">
        Request {index + 1} of {total}
      </p>

      <section className="card">
        <h2 className="card__title">Your request</h2>
        <p className="request">{trial.prompt}</p>
        <ul className="requirements">
          {trial.constraints.map((c) => (
            <li key={c.id}>{c.label}</li>
          ))}
        </ul>
      </section>

      <section className="card card--agent">
        <div className="agent__header">
          <span className="agent__avatar" aria-hidden="true">SB</span>
          <div>
            <div className="agent__name">ShopBot</div>
            <div className="agent__sub">Automated shopping assistant</div>
          </div>
        </div>

        <p className="agent__message">{copy.opener}</p>

        <div className="recommendation">
          <span className="badge">{toneConfidenceBadge(condition.tone)}</span>
          <SpecCard
            item={recommended}
            fields={trial.specCardFields}
            catalog={catalog}
            highlight
          />
        </div>

        <p className="agent__message">{copy.verdict}</p>

        {condition.disclosure === "full" && (
          // `key` forces a remount per trial. Without it React reuses the instance
          // and its expand/alternatives state leaks across trials, so a click
          // collapses a previously-opened claim instead of opening a new one and no
          // verification event is recorded -- silently corrupting the primary
          // process measure. Do not remove.
          <AgentTrace
            key={trial.id}
            trial={trial}
            catalog={catalog}
            onVerify={(constraintId) =>
              verifications.current.push({
                constraintId,
                tMs: Date.now() - startedAt.current,
              })
            }
            onOpenAlternatives={() => {
              openedAlternatives.current = true;
            }}
          />
        )}

        <p className="agent__message agent__message--closer">{copy.closer}</p>
      </section>

      <section className="card">
        <h2 className="card__title">
          How confident are you that ShopBot&rsquo;s recommendation meets all of your
          requirements?
        </h2>
        <div className="likert" role="radiogroup" aria-label="Confidence">
          {Array.from(
            { length: CONFIDENCE_MAX - CONFIDENCE_MIN + 1 },
            (_, i) => CONFIDENCE_MIN + i,
          ).map((v) => (
            <button
              key={v}
              type="button"
              role="radio"
              aria-checked={confidence === v}
              className={`likert__option${confidence === v ? " is-selected" : ""}`}
              onClick={() => setConfidence(v)}
            >
              <span className="likert__value">{v}</span>
              {CONFIDENCE_ANCHORS[v] && (
                <span className="likert__anchor">{CONFIDENCE_ANCHORS[v]}</span>
              )}
            </button>
          ))}
        </div>
      </section>

      <section className="card">
        <h2 className="card__title">What would you like to do?</h2>
        {confidence == null && (
          <p className="hint">Please answer the question above first.</p>
        )}

        {!picking ? (
          <div className="actions">
            <button
              type="button"
              className="btn btn--primary"
              disabled={confidence == null}
              onClick={() => submit("accept", trial.recommendedId)}
            >
              Accept ShopBot&rsquo;s recommendation
            </button>
            <button
              type="button"
              className="btn btn--secondary"
              disabled={confidence == null}
              onClick={() => setPicking(true)}
            >
              Choose a different option
            </button>
          </div>
        ) : (
          <div className="picker">
            <p className="hint">Select the option you would rather have.</p>
            <table className="alt-table">
              <thead>
                <tr>
                  <th>Option</th>
                  {trial.specCardFields.map((f) => (
                    <th key={f}>{catalog.fieldMeta[f]?.label ?? f}</th>
                  ))}
                  <th />
                </tr>
              </thead>
              <tbody>
                {alternatives.map((id) => {
                  const item = catalog.items[id];
                  return (
                    <tr key={id} className={chosenId === id ? "is-selected" : ""}>
                      <td>{item.name}</td>
                      {trial.specCardFields.map((f) => {
                        const meta = catalog.fieldMeta[f];
                        return (
                          <td key={f}>
                            {meta ? formatValue(item[f], meta.kind, meta.unit) : "-"}
                          </td>
                        );
                      })}
                      <td>
                        <button
                          type="button"
                          className="btn btn--small"
                          onClick={() => setChosenId(id)}
                        >
                          {chosenId === id ? "Selected" : "Select"}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <div className="actions">
              <button
                type="button"
                className="btn btn--primary"
                disabled={!chosenId}
                onClick={() => chosenId && submit("override", chosenId)}
              >
                Confirm this choice
              </button>
              <button
                type="button"
                className="btn btn--ghost"
                onClick={() => {
                  setPicking(false);
                  setChosenId(null);
                }}
              >
                Back
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
