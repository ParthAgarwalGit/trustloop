import { useEffect, useMemo, useRef, useState } from "react";
import { STREAM_CHARS_PER_SEC, TOOL_SPEED } from "../config";
import type { AgentBlock, Citation, ToolCall } from "../types";
import { telemetry } from "../lib/telemetry";

// -----------------------------------------------------------------------------
// Making the agent look like it is working.
//
// A response that appears instantly and complete reads as a lookup. Real agents
// announce what they are doing, take visible time doing it, and then produce text
// progressively. Reproducing that is not decoration -- if participants suspect the
// output is canned, they stop treating it as an AI's judgement and the construct
// under study evaporates.
//
// Three things carry the illusion:
//   1. tool calls that resolve one at a time, with plausible durations
//   2. text that streams in rather than appearing whole
//   3. a caret that blinks while streaming and disappears when done
//
// Everything is deterministic content underneath; only the PRESENTATION is timed.
// -----------------------------------------------------------------------------

const TOOL_ICON: Record<string, string> = {
  search: "🔍",
  filter: "⚙",
  read: "📄",
  compare: "⚖",
};

export function AgentStream({
  toolCalls,
  blocks,
  citations,
  onCitationClick,
  onComplete,
}: {
  toolCalls: ToolCall[];
  blocks: AgentBlock[];
  citations: Citation[];
  onCitationClick: (c: Citation) => void;
  onComplete: () => void;
}) {
  const [toolIndex, setToolIndex] = useState(0);
  const [streaming, setStreaming] = useState(false);
  const [revealed, setRevealed] = useState(0);
  const doneRef = useRef(false);

  const totalChars = useMemo(
    () => blocks.reduce((n, b) => n + (b.text?.length ?? 0), 0),
    [blocks],
  );

  // --- phase 1: tool calls ---------------------------------------------------
  useEffect(() => {
    if (toolIndex >= toolCalls.length) {
      setStreaming(true);
      return;
    }
    const d = Math.max(220, toolCalls[toolIndex].durationMs * TOOL_SPEED);
    const timer = window.setTimeout(() => setToolIndex((i) => i + 1), d);
    return () => window.clearTimeout(timer);
  }, [toolIndex, toolCalls]);

  // --- phase 2: text streaming ----------------------------------------------
  useEffect(() => {
    if (!streaming || revealed >= totalChars) return;
    const tick = 40;
    const step = Math.max(1, Math.round((STREAM_CHARS_PER_SEC * tick) / 1000));
    const timer = window.setTimeout(
      () => setRevealed((r) => Math.min(totalChars, r + step)),
      tick,
    );
    return () => window.clearTimeout(timer);
  }, [streaming, revealed, totalChars]);

  useEffect(() => {
    if (streaming && revealed >= totalChars && !doneRef.current) {
      doneRef.current = true;
      onComplete();
    }
  }, [streaming, revealed, totalChars, onComplete]);

  const finished = streaming && revealed >= totalChars;

  return (
    <div className="stream">
      <ol className="tools" aria-label="Assistant activity">
        {toolCalls.slice(0, toolIndex + 1).map((tc, i) => {
          const done = i < toolIndex;
          return (
            <li key={i} className={`tool${done ? " tool--done" : " tool--active"}`}>
              <span className="tool__icon" aria-hidden="true">
                {done ? "✓" : (TOOL_ICON[tc.kind] ?? "•")}
              </span>
              <span className="tool__label">{tc.label}</span>
              {done && tc.detail && (
                <span className="tool__detail">{tc.detail}</span>
              )}
              {!done && <span className="tool__spinner" aria-hidden="true" />}
            </li>
          );
        })}
      </ol>

      {streaming && (
        <div className="answer" data-tid="agent-answer">
          {renderBlocks(blocks, revealed, citations, onCitationClick, finished)}
        </div>
      )}

      {finished && citations.length > 0 && (
        <div className="sources" data-tid="agent-sources">
          <h4 className="sources__heading">Sources</h4>
          <ol className="sources__list">
            {citations.map((c) => (
              <li key={c.n}>
                <button
                  type="button"
                  className="source-link"
                  data-tid={`source-link-${c.n}`}
                  onClick={() => {
                    telemetry.citationClicked(c.n, c.url);
                    onCitationClick(c);
                  }}
                >
                  {c.url}
                </button>
                <span className="sources__label">{c.label}</span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

/** Reveal blocks up to `revealed` characters, streaming the last partial one. */
function renderBlocks(
  blocks: AgentBlock[],
  revealed: number,
  citations: Citation[],
  onCitationClick: (c: Citation) => void,
  finished: boolean,
) {
  const out: React.ReactNode[] = [];
  let budget = revealed;

  for (let i = 0; i < blocks.length; i++) {
    if (budget <= 0) break;
    const b = blocks[i];
    const text = b.text ?? "";
    const shown = text.slice(0, budget);
    const isLast = budget < text.length;
    budget -= text.length;

    const inline = (
      <Inline
        text={shown}
        citations={citations}
        onCitationClick={onCitationClick}
        caret={isLast && !finished}
      />
    );

    if (b.type === "h") {
      out.push(<h3 key={i} className="answer__h">{inline}</h3>);
    } else if (b.type === "candidate") {
      out.push(
        <div key={i} className="answer__candidate">
          <div className="answer__candidate-head">
            <strong>{b.name}</strong>
            <span className="answer__price">{b.price}</span>
            {b.cite !== undefined && (
              <CiteMark
                n={b.cite}
                citations={citations}
                onCitationClick={onCitationClick}
              />
            )}
          </div>
          <p>{inline}</p>
        </div>,
      );
    } else {
      out.push(<p key={i} className="answer__p">{inline}</p>);
    }
  }
  return out;
}

/** Render **bold** and [n] citation markers inside a streamed string. */
function Inline({
  text, citations, onCitationClick, caret,
}: {
  text: string;
  citations: Citation[];
  onCitationClick: (c: Citation) => void;
  caret: boolean;
}) {
  const parts: React.ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|\[\d+\])/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let key = 0;

  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith("**")) {
      parts.push(<strong key={key++}>{tok.slice(2, -2)}</strong>);
    } else {
      const n = Number(tok.slice(1, -1));
      parts.push(
        <CiteMark
          key={key++}
          n={n}
          citations={citations}
          onCitationClick={onCitationClick}
        />,
      );
    }
    last = m.index + tok.length;
  }
  if (last < text.length) parts.push(text.slice(last));

  return (
    <>
      {parts}
      {caret && <span className="caret" aria-hidden="true" />}
    </>
  );
}

function CiteMark({
  n, citations, onCitationClick,
}: {
  n: number;
  citations: Citation[];
  onCitationClick: (c: Citation) => void;
}) {
  const c = citations.find((x) => x.n === n);
  if (!c) return <sup className="cite cite--dead">[{n}]</sup>;
  return (
    <button
      type="button"
      className="cite"
      data-tid={`cite-${n}`}
      title={c.label}
      onClick={() => {
        telemetry.citationClicked(c.n, c.url);
        onCitationClick(c);
      }}
    >
      [{n}]
    </button>
  );
}
