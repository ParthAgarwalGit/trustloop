import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CONFIDENCE_ANCHORS, CONFIDENCE_MAX, CONFIDENCE_MIN } from "../config";
import type {
  AgentBlock, Catalog, Citation, Condition, SourceVisit, Trial, TrialResponse,
} from "../types";
import type { Rng } from "../lib/rng";
import { toneConfidenceBadge, toneCopy } from "../lib/tone";
import { telemetry, type TelemetryEvent } from "../lib/telemetry";
import { AgentStream } from "./AgentStream";
import { MockBrowser, type OpenSource } from "../mockweb/MockBrowser";
import type { Sources } from "../mockweb/SourcePages";
import { formatValue } from "./SpecCard";

export function TrialScreen({
  trial, index, total, condition, catalog, sources, rng, onComplete,
}: {
  trial: Trial;
  index: number;
  total: number;
  condition: Condition;
  catalog: Catalog;
  sources: Sources;
  rng: Rng;
  onComplete: (r: TrialResponse) => void;
}) {
  const [confidence, setConfidence] = useState<number | null>(null);
  const [picking, setPicking] = useState(false);
  const [chosenId, setChosenId] = useState<string | null>(null);
  const [agentDone, setAgentDone] = useState(false);
  const [openSource, setOpenSource] = useState<OpenSource | null>(null);

  const startedAt = useRef<number>(Date.now());
  const agentDoneMs = useRef(0);
  const eventMark = useRef(0);

  useEffect(() => {
    setConfidence(null);
    setPicking(false);
    setChosenId(null);
    setAgentDone(false);
    setOpenSource(null);
    startedAt.current = Date.now();
    agentDoneMs.current = 0;
    // Remember where this trial's telemetry begins, so source visits can be
    // attributed to the right trial when the response is assembled.
    eventMark.current = telemetry.export().events.length;
    telemetry.trialId = trial.id;
    telemetry.beginTrace(trial.id, "agent");
    window.scrollTo({ top: 0 });
  }, [trial.id]);

  const recommended = catalog.items[trial.recommendedId];

  const copy = useMemo(
    () => toneCopy(condition.tone, {
      itemName: recommended.name,
      nClaims: trial.constraints.length,
    }, rng),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [trial.id],
  );

  const openCitation = useCallback((c: Citation) => {
    setOpenSource({
      url: c.url,
      itemId: c.itemId,
      sourceType: c.sourceType,
      citationN: c.n,
    });
  }, []);

  /**
   * Reconstruct this trial's source visits from the telemetry stream.
   *
   * Reading them back out of telemetry rather than maintaining a parallel copy
   * means there is exactly one source of truth for what happened, and the trial
   * record cannot silently drift from the event log.
   */
  const collectVisits = (): {
    visits: SourceVisit[]; visitedDisputed: boolean; sawDisputedMs: number;
  } => {
    const events = telemetry.export().events.slice(eventMark.current);
    const visits: SourceVisit[] = [];
    let open: (SourceVisit & { _openT: number }) | null = null;

    for (const e of events as TelemetryEvent[]) {
      if (e.k === "source_open") {
        open = {
          url: e.url, itemId: e.itemId, sourceType: e.sourceType,
          tMs: e.t - startedAt.current, dwellMs: 0, maxScrollPct: 0,
          specRowsSeen: {}, _openT: e.t,
        };
      } else if (e.k === "spec_row_view" && open) {
        open.specRowsSeen[e.field] =
          (open.specRowsSeen[e.field] ?? 0) + e.msVisible;
      } else if (e.k === "source_close" && open) {
        open.dwellMs = e.dwellMs;
        open.maxScrollPct = e.maxScrollPct;
        const { _openT, ...rest } = open;
        void _openT;
        visits.push(rest);
        open = null;
      } else if (e.k === "spec_row_view" && !open && visits.length) {
        // Row visibility is reported from an unmount cleanup, which React runs
        // AFTER the parent effect that emits source_close. Without this branch
        // every spec-row dwell time arrives too late and is dropped -- the visit
        // looks like it happened but nothing appears to have been read.
        const lastVisit = visits[visits.length - 1];
        lastVisit.specRowsSeen[e.field] =
          (lastVisit.specRowsSeen[e.field] ?? 0) + e.msVisible;
      }
    }
    if (open) {
      const { _openT, ...rest } = open;
      rest.dwellMs = Date.now() - _openT;
      visits.push(rest);
    }

    const disputed = trial.disputedFact;
    if (!disputed) return { visits, visitedDisputed: false, sawDisputedMs: 0 };

    const bare = (u: string) => u.split("#")[0];
    const matching = visits.filter((v) => bare(v.url) === bare(disputed.sourceUrl));
    return {
      visits,
      visitedDisputed: matching.length > 0,
      sawDisputedMs: matching.reduce(
        (n, v) => n + (v.specRowsSeen[disputed.field] ?? 0), 0,
      ),
    };
  };

  const submit = (decision: "accept" | "override", itemId: string) => {
    if (confidence == null) return;
    const { visits, visitedDisputed, sawDisputedMs } = collectVisits();
    onComplete({
      trialId: trial.id,
      slot: trial.slot,
      confidence,
      decision,
      chosenId: itemId,
      rtMs: Date.now() - startedAt.current,
      sourceVisits: visits,
      agentDoneMs: agentDoneMs.current,
      visitedDisputedSource: visitedDisputed,
      sawDisputedRowMs: sawDisputedMs,
    });
  };

  /**
   * Canonical URL for an item's retailer page.
   *
   * Looked up from the built data, never recomputed. A TypeScript re-implementation
   * of the Python slug rule drifted (Python collapses "--" to "-", TS did not), so
   * for any item whose name contains " - " the URL the participant clicked never
   * matched the canonical one recorded against the disputed fact -- and
   * `visitedDisputedSource` was silently false for every such trial.
   */
  const shopUrlFor = (itemId: string): string =>
    sources.pages[itemId]?.shop?.url ?? "";

  const alternatives = trial.candidateIds.filter((id) => id !== trial.recommendedId);
  const priceField = trial.domain === "laptop" ? "price" : "total_price";

  return (
    <div className="screen">
      <div className="progress">
        <div className="progress__bar" style={{ width: `${(index / total) * 100}%` }} />
      </div>
      <p className="progress__label">Request {index + 1} of {total}</p>

      <section className="card">
        <h2 className="card__title">Your request</h2>
        <p className="request">{trial.prompt}</p>
        <ul className="requirements">
          {trial.constraints.map((c) => <li key={c.id}>{c.label}</li>)}
        </ul>
      </section>

      <section className="card card--agent">
        <div className="agent__header">
          <span className="agent__avatar" aria-hidden="true">SB</span>
          <div>
            <div className="agent__name">ShopBot</div>
            <div className="agent__sub">
              {agentDone ? "Automated shopping assistant" : "Working…"}
            </div>
          </div>
          {agentDone && (
            <span className="badge badge--right">
              {toneConfidenceBadge(condition.tone)}
            </span>
          )}
        </div>

        {agentDone && <p className="agent__message">{copy.opener}</p>}

        <AgentStream
          key={trial.id}
          toolCalls={trial.toolCalls}
          blocks={
            // The Disclosure manipulation. `opaque` strips the agent's reasoning
            // and its citations, leaving the summary and the recommendation --
            // the shape of a chatbot that just answers. `full` keeps the whole
            // response with every source it consulted.
            //
            // Both conditions can still reach the shop (see the footer link
            // below), so error detection is possible in either. What differs is
            // whether the path to the relevant evidence is laid out for you.
            condition.disclosure === "full"
              ? trial.response.blocks
              : opaqueBlocks(trial.response.blocks, recommended.name)
          }
          citations={condition.disclosure === "full" ? trial.response.citations : []}
          onCitationClick={openCitation}
          onComplete={() => {
            agentDoneMs.current = Date.now() - startedAt.current;
            setAgentDone(true);
          }}
        />

        {agentDone && (
          <>
            <p className="agent__message agent__message--closer">{copy.closer}</p>
            <div className="agent__footer">
              <button
                type="button"
                className="link-button"
                data-tid="open-listing"
                onClick={() =>
                  setOpenSource({
                    url: shopUrlFor(recommended.id),
                    itemId: recommended.id,
                    sourceType: "shop",
                  })
                }
              >
                View this listing on Vantage
              </button>
            </div>
          </>
        )}
      </section>

      {agentDone && (
        <>
          <section className="card">
            <h2 className="card__title">
              How confident are you that ShopBot&rsquo;s recommendation meets all of
              your requirements?
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
                  data-tid={`confidence-${v}`}
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
                  data-tid="accept"
                  disabled={confidence == null}
                  onClick={() => submit("accept", trial.recommendedId)}
                >
                  Accept ShopBot&rsquo;s recommendation
                </button>
                <button
                  type="button"
                  className="btn btn--secondary"
                  data-tid="override"
                  disabled={confidence == null}
                  onClick={() => setPicking(true)}
                >
                  Choose a different option
                </button>
              </div>
            ) : (
              <div className="picker">
                <p className="hint">
                  Select the option you would rather have. You can open any listing
                  to check its details.
                </p>
                <ul className="picker__list">
                  {alternatives.map((id) => {
                    const alt = catalog.items[id];
                    return (
                      <li
                        key={id}
                        className={`picker__item${chosenId === id ? " is-selected" : ""}`}
                      >
                        <div className="picker__main">
                          <span className="picker__name">{alt.name}</span>
                          <span className="picker__price">
                            {formatValue(alt[priceField], "currency", "$")}
                          </span>
                        </div>
                        <div className="picker__actions">
                          <button
                            type="button"
                            className="link-button"
                            onClick={() =>
                              setOpenSource({
                                url: shopUrlFor(id),
                                itemId: id,
                                sourceType: "shop",
                              })
                            }
                          >
                            View listing
                          </button>
                          <button
                            type="button"
                            className="btn btn--small"
                            data-tid={`select-${id}`}
                            onClick={() => setChosenId(id)}
                          >
                            {chosenId === id ? "Selected" : "Select"}
                          </button>
                        </div>
                      </li>
                    );
                  })}
                </ul>
                <div className="actions">
                  <button
                    type="button"
                    className="btn btn--primary"
                    data-tid="confirm-override"
                    disabled={!chosenId}
                    onClick={() => chosenId && submit("override", chosenId)}
                  >
                    Confirm this choice
                  </button>
                  <button
                    type="button"
                    className="btn btn--ghost"
                    onClick={() => { setPicking(false); setChosenId(null); }}
                  >
                    Back
                  </button>
                </div>
              </div>
            )}
          </section>
        </>
      )}

      <MockBrowser
        open={openSource}
        catalog={catalog}
        sources={sources}
        onClose={() => setOpenSource(null)}
      />
    </div>
  );
}

/**
 * The opaque condition's view of the response.
 *
 * Keeps the summary, the recommended item, and the final recommendation. Drops the
 * alternatives it weighed and the trade-offs section -- i.e. the evidence of a
 * process. Citation markers are stripped separately by passing an empty citation
 * list, so the prose reads as a plain answer rather than a sourced one.
 */
function opaqueBlocks(blocks: AgentBlock[], recommendedName: string): AgentBlock[] {
  const out: AgentBlock[] = [];
  let heading: string | undefined;
  for (const b of blocks) {
    if (b.type === "h") { heading = b.text; }
    if (heading === "Trade-offs worth knowing") continue;
    if (b.type === "candidate" && b.name !== recommendedName) continue;
    out.push(b.type === "p" || b.type === "candidate"
      ? { ...b, text: (b.text ?? "").replace(/\s*\[\d+\]/g, "") }
      : b);
  }
  return out;
}
