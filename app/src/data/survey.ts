// Post-session questionnaire specification.
//
// IMPORTANT -- SCALE PROVENANCE
// The multi-item blocks below are PLACEHOLDER items written for this codebase. They
// are face-valid and analysable as-is, but they are NOT the validated instruments
// named in the proposal. Before running the real study you should replace the items
// in TRUST, AUTHENTICITY and RELIANCE with the published scale you intend to cite,
// after checking that scale's licence and reproducing its exact wording and anchors.
// Swapping the `text` strings is sufficient -- ids feed straight into the analysis,
// so keep them stable (or update analysis/compute_dvs.py to match).
//
// NASA-TLX is a US Government (NASA) instrument and is free to use. We administer
// the unweighted "Raw TLX", which is standard and does not require the pairwise
// weighting procedure.

export type ItemKind = "likert7" | "likert5" | "tlx" | "select" | "text" | "number";

export interface SurveyItem {
  id: string;
  text: string;
  kind: ItemKind;
  /** reverse-scored: analysis flips this before averaging */
  reverse?: boolean;
  options?: string[];
  /** endpoint labels for slider/likert kinds */
  anchors?: [string, string];
  required?: boolean;
  /** an attention check; `expected` is the required response value */
  attentionCheck?: { expected: number };
}

export interface SurveyBlock {
  id: string;
  title: string;
  intro?: string;
  items: SurveyItem[];
}

const AGREE7: [string, string] = ["Strongly disagree", "Strongly agree"];

export const SURVEY: SurveyBlock[] = [
  {
    id: "trust",
    title: "Your view of ShopBot",
    intro: "Thinking about the assistant you just used, how much do you agree with each statement?",
    items: [
      { id: "trust_1", text: "I would trust ShopBot to shop on my behalf.", kind: "likert7", anchors: AGREE7, required: true },
      { id: "trust_2", text: "ShopBot's recommendations were dependable.", kind: "likert7", anchors: AGREE7, required: true },
      { id: "trust_3", text: "I was wary of relying on ShopBot.", kind: "likert7", anchors: AGREE7, reverse: true, required: true },
      { id: "attn_1", text: "For this item, please select \"Somewhat disagree\" (option 3).", kind: "likert7", anchors: AGREE7, required: true, attentionCheck: { expected: 3 } },
      { id: "trust_4", text: "ShopBot acted in my interest rather than its own.", kind: "likert7", anchors: AGREE7, required: true },
    ],
  },
  {
    id: "authenticity",
    title: "How ShopBot came across",
    items: [
      { id: "auth_1", text: "ShopBot came across as genuine.", kind: "likert7", anchors: AGREE7, required: true },
      { id: "auth_2", text: "ShopBot was telling me what I wanted to hear.", kind: "likert7", anchors: AGREE7, reverse: true, required: true },
      { id: "auth_3", text: "ShopBot's enthusiasm felt warranted.", kind: "likert7", anchors: AGREE7, required: true },
    ],
  },
  {
    id: "transparency",
    title: "What ShopBot showed you",
    items: [
      { id: "trans_suff_1", text: "I was given enough information to judge whether ShopBot's recommendations were correct.", kind: "likert7", anchors: AGREE7, required: true },
      { id: "trans_suff_2", text: "Checking ShopBot's work would have taken more effort than it was worth.", kind: "likert7", anchors: AGREE7, reverse: true, required: true },
      {
        id: "accept_1",
        text: "How acceptable do you find the way ShopBot arrived at and presented its recommendations?",
        kind: "likert5",
        anchors: ["Completely unacceptable", "Completely acceptable"],
        required: true,
      },
    ],
  },
  {
    id: "reliance",
    title: "Using an assistant like this again",
    items: [
      { id: "rely_1", text: "I would let an assistant like ShopBot make this kind of choice without reviewing it.", kind: "likert7", anchors: AGREE7, required: true },
      { id: "rely_2", text: "I would want to check an assistant like ShopBot's work every time.", kind: "likert7", anchors: AGREE7, reverse: true, required: true },
    ],
  },
  {
    id: "tlx",
    title: "How the task felt",
    intro: "Rate each dimension of the task you just completed, from 0 to 100.",
    items: [
      { id: "tlx_mental", text: "Mental demand -- how mentally demanding was the task?", kind: "tlx", anchors: ["Very low", "Very high"], required: true },
      { id: "tlx_temporal", text: "Temporal demand -- how hurried or rushed did you feel?", kind: "tlx", anchors: ["Very low", "Very high"], required: true },
      { id: "tlx_performance", text: "Performance -- how successful were you in doing what you were asked to do?", kind: "tlx", anchors: ["Perfect", "Failure"], required: true },
      { id: "tlx_effort", text: "Effort -- how hard did you have to work to reach your level of performance?", kind: "tlx", anchors: ["Very low", "Very high"], required: true },
      { id: "tlx_frustration", text: "Frustration -- how insecure, discouraged, irritated or annoyed were you?", kind: "tlx", anchors: ["Very low", "Very high"], required: true },
      { id: "tlx_physical", text: "Physical demand -- how physically demanding was the task?", kind: "tlx", anchors: ["Very low", "Very high"], required: true },
    ],
  },
  {
    id: "checks",
    title: "A few last impressions",
    intro: "These help us confirm the assistant behaved as intended.",
    items: [
      // Manipulation check -- Tone
      { id: "mc_tone_warm", text: "ShopBot was complimentary and enthusiastic.", kind: "likert7", anchors: AGREE7, required: true },
      { id: "mc_tone_hedge", text: "ShopBot acknowledged that it might be wrong.", kind: "likert7", anchors: AGREE7, required: true },
      // Manipulation check -- Disclosure
      { id: "mc_disc_steps", text: "ShopBot showed me the steps it took to reach its recommendation.", kind: "likert7", anchors: AGREE7, required: true },
      { id: "mc_disc_verify", text: "I could check ShopBot's claims against an underlying record.", kind: "likert7", anchors: AGREE7, required: true },
      { id: "attn_2", text: "For this item, please select \"Strongly agree\" (option 7).", kind: "likert7", anchors: AGREE7, required: true, attentionCheck: { expected: 7 } },
    ],
  },
  {
    id: "about",
    title: "About you",
    items: [
      { id: "age", text: "What is your age?", kind: "number", required: true },
      {
        id: "gender",
        text: "How do you describe your gender?",
        kind: "select",
        options: ["Woman", "Man", "Non-binary", "Prefer to self-describe", "Prefer not to say"],
        required: true,
      },
      {
        id: "ai_familiarity",
        text: "How familiar are you with AI assistants such as ChatGPT, Copilot or Gemini?",
        kind: "likert7",
        anchors: ["Not at all familiar", "Extremely familiar"],
        required: true,
      },
      {
        id: "ai_shopping_use",
        text: "Before today, had you used an AI assistant to help you shop or plan travel?",
        kind: "select",
        options: ["Never", "Once or twice", "Occasionally", "Regularly"],
        required: true,
      },
    ],
  },
  {
    id: "open",
    title: "Anything else",
    items: [
      {
        id: "open_noticed",
        text: "Did you notice anything unusual about ShopBot or about this study? (Optional)",
        kind: "text",
      },
      {
        id: "open_strategy",
        text: "How did you decide whether to accept or change a recommendation? (Optional)",
        kind: "text",
      },
    ],
  },
];

export const ATTENTION_CHECK_IDS = SURVEY.flatMap((b) =>
  b.items.filter((i) => i.attentionCheck).map((i) => i.id),
);
