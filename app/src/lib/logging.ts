// Event logging and data submission.
//
// Two guarantees matter here:
//   1. Nothing is ever lost to a failed network call -- every session is mirrored
//      into localStorage as it progresses, and the debrief screen always offers a
//      manual JSON download.
//   2. Submission failures are surfaced to the participant with a retry, not
//      silently swallowed, so a dropped session can be recovered during the run.

import {
  DATA_SINK, POST_ENDPOINT, SUPABASE_ANON_KEY, SUPABASE_TABLE, SUPABASE_URL,
} from "../config";
import type { LoggedEvent, SessionPayload } from "../types";

const STORAGE_PREFIX = "trustloop:session:";

export class EventLog {
  private events: LoggedEvent[] = [];

  add(kind: string, payload?: Record<string, unknown>): void {
    this.events.push({ t: new Date().toISOString(), kind, payload });
  }

  all(): LoggedEvent[] {
    return this.events.slice();
  }
}

/** Mirror the in-progress session locally. Never throws. */
export function saveLocal(payload: SessionPayload): void {
  try {
    localStorage.setItem(
      STORAGE_PREFIX + payload.meta.participantId,
      JSON.stringify(payload),
    );
  } catch {
    // Storage can be unavailable (private mode, quota). Losing the mirror is
    // acceptable; the download fallback still works.
  }
}

/** Every locally mirrored session, for recovery during lab runs. */
export function listLocalSessions(): SessionPayload[] {
  const out: SessionPayload[] = [];
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (!key?.startsWith(STORAGE_PREFIX)) continue;
      const raw = localStorage.getItem(key);
      if (raw) out.push(JSON.parse(raw) as SessionPayload);
    }
  } catch {
    /* ignore */
  }
  return out;
}

export function downloadJson(payload: SessionPayload): void {
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `trustloop_${payload.meta.participantId}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export type SubmitResult =
  | { ok: true; sink: string }
  | { ok: false; sink: string; error: string };

async function postJson(
  url: string,
  body: unknown,
  headers: Record<string, string>,
): Promise<void> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} ${res.statusText} ${text}`.trim());
  }
}

/**
 * Send a completed session to the configured sink.
 *
 * The row shape for Supabase is flattened slightly (participant_id / condition
 * columns alongside the full JSON blob) so you can filter in the dashboard without
 * unpacking JSON. See server/supabase_schema.sql.
 */
export async function submit(payload: SessionPayload): Promise<SubmitResult> {
  saveLocal(payload);

  if (DATA_SINK === "none") {
    return { ok: true, sink: "local" };
  }

  try {
    if (DATA_SINK === "supabase") {
      if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
        throw new Error("VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY are not set");
      }
      await postJson(
        `${SUPABASE_URL.replace(/\/$/, "")}/rest/v1/${SUPABASE_TABLE}`,
        {
          participant_id: payload.meta.participantId,
          prolific_pid: payload.meta.prolificPid,
          disclosure: payload.meta.condition.disclosure,
          tone: payload.meta.condition.tone,
          is_preview: payload.meta.isPreview,
          app_version: payload.meta.appVersion,
          completed_at: payload.completedAt,
          data: payload,
        },
        {
          apikey: SUPABASE_ANON_KEY,
          Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
          Prefer: "return=minimal",
        },
      );
      return { ok: true, sink: "supabase" };
    }

    if (DATA_SINK === "endpoint") {
      if (!POST_ENDPOINT) throw new Error("VITE_POST_ENDPOINT is not set");
      await postJson(POST_ENDPOINT, payload, {});
      return { ok: true, sink: "endpoint" };
    }

    throw new Error(`unknown VITE_DATA_SINK: ${DATA_SINK}`);
  } catch (e) {
    return {
      ok: false,
      sink: DATA_SINK,
      error: e instanceof Error ? e.message : String(e),
    };
  }
}
