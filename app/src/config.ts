// Central tunables. Anything a researcher might want to change without touching
// component code lives here.

export const APP_VERSION = "0.1.0";

/**
 * Randomise trial order *within* the clean and error blocks separately.
 *
 * This preserves the fixed error positions (slots 4, 7, 9) -- so serial position is
 * held constant across conditions and cannot confound the between-subjects
 * comparison -- while varying which specific content appears where, so results are
 * not tied to one particular trial's idiosyncrasies.
 *
 * Set to false for a fully fixed order (simpler, also defensible).
 */
export const RANDOMISE_WITHIN_BLOCKS = true;

/** Confidence rating scale (inclusive). */
export const CONFIDENCE_MIN = 1;
export const CONFIDENCE_MAX = 7;
export const CONFIDENCE_ANCHORS: Record<number, string> = {
  1: "Not at all confident",
  4: "Moderately confident",
  7: "Completely confident",
};

/** Max attempts at the comprehension check before the participant is screened out. */
export const MAX_COMPREHENSION_ATTEMPTS = 3;

/**
 * Where completed sessions are sent.
 *
 *   "none"     -> nothing is transmitted; the participant downloads a JSON file
 *                 (useful for local piloting and for lab sessions)
 *   "supabase" -> POST to a Supabase REST table endpoint
 *   "endpoint" -> POST to an arbitrary URL of your own
 *
 * Configured via .env (see .env.example). Data is ALSO always written to
 * localStorage as a recovery copy.
 */
export const DATA_SINK = (import.meta.env.VITE_DATA_SINK ?? "none") as
  | "none"
  | "supabase"
  | "endpoint";

export const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL ?? "";
export const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY ?? "";
export const SUPABASE_TABLE = import.meta.env.VITE_SUPABASE_TABLE ?? "sessions";
export const POST_ENDPOINT = import.meta.env.VITE_POST_ENDPOINT ?? "";

/** Shown on the debrief screen so participants can claim payment. */
export const COMPLETION_URL = import.meta.env.VITE_COMPLETION_URL ?? "";
export const COMPLETION_CODE = import.meta.env.VITE_COMPLETION_CODE ?? "";

/** Contact details shown on the consent and debrief screens. Fill these in. */
export const STUDY_CONTACT = {
  researcher: import.meta.env.VITE_RESEARCHER_NAME ?? "[Researcher name]",
  email: import.meta.env.VITE_RESEARCHER_EMAIL ?? "[contact email]",
  institution: import.meta.env.VITE_INSTITUTION ?? "[Institution]",
  ethicsRef: import.meta.env.VITE_ETHICS_REF ?? "[ethics approval number]",
};
