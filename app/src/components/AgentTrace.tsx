import { useState } from "react";
import type { AgentClaim, Catalog, Trial } from "../types";
import { formatValue } from "./SpecCard";

/**
 * The Disclosure manipulation.
 *
 *  opaque -> nothing from this component renders; the participant sees only the
 *            agent's tone-styled message and the product spec card.
 *  full   -> the agent's process trace, plus a per-requirement claim list where
 *            each claim can be expanded to show the catalogue record side by side
 *            with what the agent asserted (this is the *verifiability* half of the
 *            manipulation, per DG2).
 *
 * Every expansion is reported upward via `onVerify` and lands in the event log, so
 * verification behaviour is itself a dependent measure -- not just an affordance we
 * hope was used.
 */
export function AgentTrace({
  trial,
  catalog,
  onVerify,
  onOpenAlternatives,
}: {
  trial: Trial;
  catalog: Catalog;
  onVerify: (constraintId: string) => void;
  onOpenAlternatives: () => void;
}) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [showAlternatives, setShowAlternatives] = useState(false);

  // Functional updates: reading `expanded` directly drops rapid successive toggles
  // (each handler would see the same stale set).
  const toggle = (claim: AgentClaim) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(claim.constraintId)) next.delete(claim.constraintId);
      else next.add(claim.constraintId);
      return next;
    });
    if (!expanded.has(claim.constraintId)) onVerify(claim.constraintId);
  };

  const openAlternatives = () => {
    if (!showAlternatives) onOpenAlternatives();
    setShowAlternatives((v) => !v);
  };

  const others = trial.candidateIds.filter((id) => id !== trial.recommendedId);

  return (
    <div className="trace">
      <section className="trace__section">
        <h4 className="trace__heading">How I worked this out</h4>
        <ol className="trace__steps">
          {trial.agentSteps.map((s) => (
            <li key={s.n}>
              <span className="trace__action">{s.action}</span>
              <span className="trace__detail">{s.detail}</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="trace__section">
        <h4 className="trace__heading">What I checked</h4>
        <ul className="claims">
          {trial.agentClaims.map((claim) => {
            const isOpen = expanded.has(claim.constraintId);
            return (
              <li key={claim.constraintId} className="claim">
                <button
                  type="button"
                  className="claim__button"
                  aria-expanded={isOpen}
                  onClick={() => toggle(claim)}
                >
                  <span className="claim__label">{claim.constraintLabel}</span>
                  <span className="claim__stated">
                    {claim.fieldLabel}: {claim.statedValueText}
                  </span>
                  <span className="claim__chevron">{isOpen ? "Hide" : "Check source"}</span>
                </button>
                {isOpen && (
                  <div className="claim__evidence">
                    <div className="claim__evidence-row">
                      <span>ShopBot reported</span>
                      <strong>{claim.statedValueText}</strong>
                    </div>
                    <div className="claim__evidence-row">
                      <span>Catalogue record</span>
                      <strong>{claim.catalogValueText}</strong>
                    </div>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      </section>

      <section className="trace__section">
        <button type="button" className="link-button" onClick={openAlternatives}>
          {showAlternatives ? "Hide" : "Show"} the other {others.length} options I
          considered
        </button>
        {showAlternatives && (
          <table className="alt-table">
            <thead>
              <tr>
                <th>Option</th>
                {trial.specCardFields.map((f) => (
                  <th key={f}>{catalog.fieldMeta[f]?.label ?? f}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {others.map((id) => {
                const item = catalog.items[id];
                return (
                  <tr key={id}>
                    <td>{item.name}</td>
                    {trial.specCardFields.map((f) => {
                      const meta = catalog.fieldMeta[f];
                      return (
                        <td key={f}>
                          {meta ? formatValue(item[f], meta.kind, meta.unit) : "-"}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
