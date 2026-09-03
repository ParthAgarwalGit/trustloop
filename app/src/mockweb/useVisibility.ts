import { useEffect, useRef } from "react";
import { telemetry } from "../lib/telemetry";

/**
 * Report how long an element was actually visible in the viewport.
 *
 * Used on spec-table rows and page sections. Without an eye tracker this is the
 * best available proxy for "the participant had the opportunity to read this":
 * it distinguishes scrolling past a row at speed from resting on it. It cannot
 * tell you they looked at it -- see docs/TELEMETRY.md on what an eye-tracking
 * sub-study would add.
 */
export function useVisibleFor(
  ref: React.RefObject<HTMLElement>,
  onLeave: (msVisible: number) => void,
  threshold = 0.6,
) {
  const enteredAt = useRef<number | null>(null);
  const accumulated = useRef(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          if (enteredAt.current === null) enteredAt.current = Date.now();
        } else if (enteredAt.current !== null) {
          accumulated.current += Date.now() - enteredAt.current;
          enteredAt.current = null;
        }
      },
      { threshold },
    );
    io.observe(el);

    return () => {
      if (enteredAt.current !== null) {
        accumulated.current += Date.now() - enteredAt.current;
      }
      io.disconnect();
      if (accumulated.current > 0) onLeave(accumulated.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}

/** Track max scroll depth within a scrollable container, reported as a percentage. */
export function useScrollDepth(
  ref: React.RefObject<HTMLElement>,
  url: string,
): React.MutableRefObject<number> {
  const maxPct = useRef(0);

  useEffect(() => {
    const el = ref.current;
    if (!el || !url) return;
    maxPct.current = 0;

    // Time-based throttle rather than requestAnimationFrame. rAF is suspended
    // whenever the page is not visible, so an rAF-gated handler silently stops
    // recording for any participant whose tab is backgrounded -- and scroll depth
    // is a measure we rely on. A timestamp check keeps working regardless.
    let lastRun = 0;
    const measure = () => {
      const scrollable = el.scrollHeight - el.clientHeight;
      const pct = scrollable <= 0 ? 100 : (el.scrollTop / scrollable) * 100;
      if (pct > maxPct.current + 5) {
        maxPct.current = Math.min(100, pct);
        telemetry.scrolled(url, Math.round(maxPct.current));
      }
    };
    const onScroll = () => {
      const now = Date.now();
      if (now - lastRun < 120) return;
      lastRun = now;
      measure();
    };

    el.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      el.removeEventListener("scroll", onScroll);
      // Capture the final position: a participant who scrolls and immediately
      // closes would otherwise be recorded at their last throttled sample.
      measure();
    };
  }, [ref, url]);

  return maxPct;
}
