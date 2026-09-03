import { useEffect, useRef, useState } from "react";
import type { Catalog } from "../types";
import { telemetry } from "../lib/telemetry";
import { useScrollDepth } from "./useVisibility";
import { ForumPage, ReviewPage, ShopPage, type Sources } from "./SourcePages";

// -----------------------------------------------------------------------------
// A browser inside the study.
//
// Why not just open a new tab? Two reasons, one methodological and one practical.
//
// Methodological: we need to know when the participant STOPS reading a source, and
// a background tab reports that unreliably. Dwell time on the disputed spec row is
// a primary process measure, so it cannot rest on visibilitychange heuristics.
//
// Practical: participants recruited from a panel lose the study tab. Every session
// lost that way is a paid participant who produced no data.
//
// The compromise is a real browser chrome with a real, copyable URL, over a page
// that is genuinely reachable at that address. It reads as visiting a site, and it
// keeps the participant inside the study.
// -----------------------------------------------------------------------------

export interface OpenSource {
  url: string;
  itemId: string;
  sourceType: "shop" | "review" | "forum";
  citationN?: number;
}

export function MockBrowser({
  open, catalog, sources, onClose,
}: {
  open: OpenSource | null;
  catalog: Catalog;
  sources: Sources;
  onClose: () => void;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const openedAt = useRef(0);
  const [loading, setLoading] = useState(true);
  const maxScroll = useScrollDepth(
    scrollRef as React.RefObject<HTMLElement>,
    open?.url ?? "",
  );

  useEffect(() => {
    if (!open) return;
    openedAt.current = Date.now();
    setLoading(true);
    telemetry.sourceOpened(open.url, open.itemId, open.sourceType);
    telemetry.beginTrace(telemetry.trialId, `source:${open.sourceType}`);

    // A page that appears instantly reads as a local render, not a fetch. This is
    // short enough not to be tedious and long enough to feel like a network.
    const timer = window.setTimeout(() => setLoading(false), 420);

    return () => {
      window.clearTimeout(timer);
      telemetry.sourceClosed(
        open.url,
        Date.now() - openedAt.current,
        Math.round(maxScroll.current),
      );
      telemetry.beginTrace(telemetry.trialId, "agent");
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open?.url]);

  // Escape closes, as it would in a real overlay.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  // Jump to the anchor once loaded, so a "#reviews" citation lands in the right place.
  useEffect(() => {
    if (loading || !open) return;
    const hash = open.url.split("#")[1];
    if (!hash) {
      scrollRef.current?.scrollTo({ top: 0 });
      return;
    }
    const el = scrollRef.current?.querySelector(`#${hash}`);
    el?.scrollIntoView({ behavior: "auto", block: "start" });
  }, [loading, open]);

  if (!open) return null;

  const bareUrl = open.url.split("#")[0];
  const pages = sources.pages[open.itemId];
  const page = pages?.[open.sourceType];
  const item = catalog.items[open.itemId];

  return (
    <div className="browser" role="dialog" aria-label="Web browser">
      <div className="browser__chrome">
        <div className="browser__controls">
          <button
            type="button"
            className="browser__btn"
            onClick={onClose}
            aria-label="Close and return to the assistant"
            data-tid="browser-close"
          >
            ←
          </button>
          <button type="button" className="browser__btn" disabled aria-hidden="true">
            →
          </button>
          <button
            type="button"
            className="browser__btn"
            onClick={() => {
              setLoading(true);
              window.setTimeout(() => setLoading(false), 420);
            }}
            aria-label="Reload"
          >
            ⟳
          </button>
        </div>
        <div className="browser__urlbar" data-tid="browser-url">
          <span className="browser__lock" aria-hidden="true">🔒</span>
          <span className="browser__url">
            https://{bareUrl}
            {open.url.includes("#") && (
              <span className="browser__frag">#{open.url.split("#")[1]}</span>
            )}
          </span>
        </div>
        <button
          type="button"
          className="browser__close"
          onClick={onClose}
          aria-label="Close"
        >
          ✕
        </button>
      </div>

      {loading && <div className="browser__progress" />}

      <div className="browser__viewport" ref={scrollRef} data-tid="browser-viewport">
        {loading ? (
          <div className="browser__skeleton" aria-busy="true">
            <div className="sk sk--title" />
            <div className="sk sk--line" />
            <div className="sk sk--line sk--short" />
            <div className="sk sk--block" />
            <div className="sk sk--line" />
            <div className="sk sk--line sk--short" />
          </div>
        ) : !page || !item ? (
          <div className="browser__error">
            <h1>This site can’t be reached</h1>
            <p className="mw__muted">{bareUrl} took too long to respond.</p>
          </div>
        ) : open.sourceType === "shop" ? (
          <ShopPage item={item} page={page} catalog={catalog} />
        ) : open.sourceType === "review" ? (
          <ReviewPage item={item} page={page} catalog={catalog} />
        ) : (
          <ForumPage page={page} />
        )}
      </div>

      <div className="browser__hint">
        Press <kbd>Esc</kbd> or use ← to return to your assistant.
      </div>
    </div>
  );
}
