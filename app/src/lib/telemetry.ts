// -----------------------------------------------------------------------------
// Behavioural telemetry.
//
// The headline dependent variable is a single bit per trial (did they override?).
// Everything interesting about *how* they got there lives here: which sources they
// opened, how long they read, how far they scrolled, whether their eyes -- or at
// least their cursor and their viewport -- ever reached the row of the spec table
// that would have exposed the agent's error.
//
// This is only possible because we serve the source pages ourselves. A link to a
// real external retailer would give us a click event and nothing after it.
//
// VOLUME CONTROL
// Mouse movement at 60 Hz for 20 minutes is ~72k points per participant, which is
// both wasteful and slow to ship. We throttle to ~20 Hz and drop points that are
// collinear with the previous two within a tolerance, which preserves the shape of
// the trace (hesitations, direction changes, reading sweeps) at roughly a tenth of
// the size.
//
// PRIVACY
// No keystroke content is recorded -- only that typing occurred, and where. Text
// selection records the length and the element, never the selected string, so a
// participant cannot accidentally leak something they typed or highlighted.
// -----------------------------------------------------------------------------

export type TelemetryEvent =
  | { t: number; k: "source_open"; url: string; itemId: string; sourceType: string; trialId: string }
  | { t: number; k: "source_close"; url: string; dwellMs: number; maxScrollPct: number }
  | { t: number; k: "section_view"; url: string; section: string; msVisible: number }
  | { t: number; k: "spec_row_view"; url: string; field: string; msVisible: number }
  | { t: number; k: "citation_click"; n: number; url: string; trialId: string }
  | { t: number; k: "click"; x: number; y: number; target: string; trialId: string }
  | { t: number; k: "selection"; chars: number; target: string }
  | { t: number; k: "copy"; chars: number }
  | { t: number; k: "tab_hidden" }
  | { t: number; k: "tab_visible"; awayMs: number }
  | { t: number; k: "idle"; ms: number }
  | { t: number; k: "scroll"; url: string; pct: number };

/** A compressed cursor trace: [dt_ms, x, y] triples, relative to trace start. */
export interface CursorTrace {
  trialId: string;
  surface: string;
  t0: number;
  points: [number, number, number][];
}

const MOUSE_MIN_INTERVAL_MS = 50; // ~20 Hz
const COLLINEAR_TOL_PX = 3;
const IDLE_THRESHOLD_MS = 30_000;

export class Telemetry {
  private events: TelemetryEvent[] = [];
  private traces: CursorTrace[] = [];
  private current: CursorTrace | null = null;
  private lastMouseAt = 0;
  private lastInputAt = Date.now();
  private hiddenAt: number | null = null;
  private idleTimer: number | null = null;
  private detach: Array<() => void> = [];

  trialId = "";
  surface = "agent";

  start(): void {
    const onMove = (e: MouseEvent) => this.recordMouse(e.clientX, e.clientY);
    const onClick = (e: MouseEvent) => {
      this.markInput();
      this.push({
        t: Date.now(), k: "click", x: e.clientX, y: e.clientY,
        target: describeTarget(e.target), trialId: this.trialId,
      });
    };
    const onSelect = () => {
      const sel = window.getSelection();
      const text = sel?.toString() ?? "";
      // Length only -- never the content. See PRIVACY above.
      if (text.length > 3) {
        this.push({
          t: Date.now(), k: "selection", chars: text.length,
          target: describeTarget(sel?.anchorNode?.parentElement ?? null),
        });
      }
    };
    const onCopy = () => {
      const chars = (window.getSelection()?.toString() ?? "").length;
      this.push({ t: Date.now(), k: "copy", chars });
    };
    const onVisibility = () => {
      if (document.hidden) {
        this.hiddenAt = Date.now();
        this.push({ t: Date.now(), k: "tab_hidden" });
      } else {
        const awayMs = this.hiddenAt ? Date.now() - this.hiddenAt : 0;
        this.hiddenAt = null;
        this.push({ t: Date.now(), k: "tab_visible", awayMs });
      }
    };
    const onKey = () => this.markInput();

    window.addEventListener("mousemove", onMove, { passive: true });
    window.addEventListener("click", onClick, true);
    document.addEventListener("selectionchange", onSelect);
    document.addEventListener("copy", onCopy);
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("keydown", onKey, { passive: true });

    this.detach = [
      () => window.removeEventListener("mousemove", onMove),
      () => window.removeEventListener("click", onClick, true),
      () => document.removeEventListener("selectionchange", onSelect),
      () => document.removeEventListener("copy", onCopy),
      () => document.removeEventListener("visibilitychange", onVisibility),
      () => window.removeEventListener("keydown", onKey),
    ];

    this.scheduleIdleCheck();
  }

  stop(): void {
    this.detach.forEach((fn) => fn());
    this.detach = [];
    if (this.idleTimer) window.clearTimeout(this.idleTimer);
    this.flushTrace();
  }

  /** Begin a new cursor trace, e.g. when the trial changes or a source opens. */
  beginTrace(trialId: string, surface: string): void {
    this.flushTrace();
    this.trialId = trialId;
    this.surface = surface;
    this.current = { trialId, surface, t0: Date.now(), points: [] };
  }

  private flushTrace(): void {
    if (this.current && this.current.points.length > 1) {
      this.traces.push(this.current);
    }
    this.current = null;
  }

  private markInput(): void {
    this.lastInputAt = Date.now();
  }

  private scheduleIdleCheck(): void {
    this.idleTimer = window.setTimeout(() => {
      const since = Date.now() - this.lastInputAt;
      if (since >= IDLE_THRESHOLD_MS) {
        this.push({ t: Date.now(), k: "idle", ms: since });
        this.lastInputAt = Date.now();
      }
      this.scheduleIdleCheck();
    }, IDLE_THRESHOLD_MS);
  }

  private recordMouse(x: number, y: number): void {
    const now = Date.now();
    if (now - this.lastMouseAt < MOUSE_MIN_INTERVAL_MS) return;
    this.lastMouseAt = now;
    this.markInput();
    if (!this.current) return;

    const pts = this.current.points;
    const dt = now - this.current.t0;
    // Drop a point that lies on the straight line between its neighbours: the
    // trace shape is carried by direction changes and pauses, not by samples
    // along a constant-velocity segment.
    if (pts.length >= 2) {
      const [, x1, y1] = pts[pts.length - 2];
      const [, x2, y2] = pts[pts.length - 1];
      const cross = Math.abs((x2 - x1) * (y - y1) - (y2 - y1) * (x - x1));
      const len = Math.hypot(x2 - x1, y2 - y1) || 1;
      if (cross / len < COLLINEAR_TOL_PX) {
        pts[pts.length - 1] = [dt, x, y];
        return;
      }
    }
    pts.push([dt, x, y]);
  }

  push(e: TelemetryEvent): void {
    this.events.push(e);
  }

  sourceOpened(url: string, itemId: string, sourceType: string): void {
    this.push({
      t: Date.now(), k: "source_open", url, itemId, sourceType,
      trialId: this.trialId,
    });
  }

  sourceClosed(url: string, dwellMs: number, maxScrollPct: number): void {
    this.push({ t: Date.now(), k: "source_close", url, dwellMs, maxScrollPct });
  }

  citationClicked(n: number, url: string): void {
    this.push({ t: Date.now(), k: "citation_click", n, url, trialId: this.trialId });
  }

  sectionViewed(url: string, section: string, msVisible: number): void {
    this.push({ t: Date.now(), k: "section_view", url, section, msVisible });
  }

  /**
   * A single row of a specification table came into view and stayed there.
   * This is the closest thing to an attention measure available without an eye
   * tracker: it says the disputed figure was on screen and had time to be read.
   */
  specRowViewed(url: string, field: string, msVisible: number): void {
    this.push({ t: Date.now(), k: "spec_row_view", url, field, msVisible });
  }

  scrolled(url: string, pct: number): void {
    this.push({ t: Date.now(), k: "scroll", url, pct });
  }

  export(): { events: TelemetryEvent[]; traces: CursorTrace[] } {
    this.flushTrace();
    return { events: this.events, traces: this.traces };
  }
}

function describeTarget(node: EventTarget | Element | null): string {
  const el = node instanceof Element ? node : null;
  if (!el) return "unknown";
  const parts: string[] = [el.tagName.toLowerCase()];
  const testId = el.getAttribute?.("data-tid");
  if (testId) parts.push(`#${testId}`);
  else if (el.className && typeof el.className === "string") {
    const cls = el.className.split(/\s+/).filter(Boolean)[0];
    if (cls) parts.push(`.${cls}`);
  }
  return parts.join("");
}

export const telemetry = new Telemetry();
