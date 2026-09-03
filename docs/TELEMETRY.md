# Behavioural Tracking: What to Measure and What It's Worth

The headline dependent variable is one bit per trial — did they override? Everything
interesting about *how* they got there is process data. This document covers what is
implemented, what to add, and an honest assessment of eye tracking.

---

## Why self-hosting the sources is the enabling decision

If the agent cited real external pages, the *only* thing you could record is that a
link was clicked. Everything after that — did they read it, how far did they scroll,
did they reach the row that exposes the error — happens in someone else's origin and
is invisible to you.

Because the retailer, review site and forum are pages we serve, every one of those
questions is answerable. **The realism goal and the measurement goal are the same
decision.**

---

## Tier 1 — implemented, zero extra hardware

| Measure | Where | Why it earns its place |
|---|---|---|
| **Source visits** | `sourceVisits[]` per trial | Which pages, in what order, from which citation |
| **Dwell per source** | `dwellMs` | Opening a page and bouncing ≠ reading it |
| **Max scroll depth** | `maxScrollPct` | Did they get to the spec table at all? |
| **Per-spec-row visibility** | `specRowsSeen{field: ms}` | **The sharpest measure in the design** — was the disputed figure on screen, and for how long? |
| **Visited the disputed source** | `visitedDisputedSource` | Had the opportunity to catch it |
| **Saw the disputed row** | `sawDisputedRowMs` | Had the opportunity *and* the row was in view |
| **Citation clicks** | `citation_click` events | Which sources they trusted enough to check |
| **Cursor trace** | `traces[]` | Compressed polyline; hesitation, direction changes, reading sweeps |
| **Clicks** | `click` events with coords + target | Heatmaps, rage-click detection |
| **Text selection / copy** | `selection`, `copy` (length only) | Strong signal of close reading |
| **Tab blur/focus** | `tab_hidden`, `tab_visible` + `awayMs` | Did they leave? Checking elsewhere, or distracted? |
| **Idle detection** | `idle` events (>30 s no input) | Protects RT validity — away ≠ thinking |
| **Agent wait time** | `agentDoneMs` | How long they watched it "work" before engaging |

### The analysis this unlocks

The single most valuable contrast this buys you, which a click-only design cannot ask:

> Among participants who **opened the page carrying the disputed fact**, and among
> those who **had that specific row on screen for >2 s**, what fraction still
> accepted the recommendation?

That separates three very different people who all look identical on a binary
accept/override measure:

1. never looked (inattentive)
2. looked at the page but not the relevant row (searched badly)
3. read the row and accepted anyway (**deference despite evidence** — the most
   theoretically interesting group, and the one sycophancy should inflate)

Group 3 is arguably the finding. It is unavailable without per-row instrumentation.

### One semantic caveat worth stating in the paper

Row-visibility accrues only while the document is visible — `IntersectionObserver` is
suspended for a hidden tab. This is the *correct* semantics (a backgrounded tab is not
being read) but it means `specRowsSeen` is time-in-view, not time-since-scrolled-past.
Say so in the Measures section.

---

## Tier 2 — worth adding, moderate effort

- **Reading-time ratio.** Expected reading time for a section (words ÷ ~250 wpm)
  versus actual dwell. Ratios far below 1 indicate skimming. Cheap to compute from
  data you already have.
- **Verification path reconstruction.** Order of sources visited per trial, as a
  sequence. Do people go retailer → review → forum, or straight to the spec table?
  Does the sycophantic condition shorten the path?
- **Re-visits.** Returning to a source after starting to answer is a strong signal of
  genuine doubt.
- **Hover dwell on the disputed clause** in the agent's own text (not just the source
  page) — did they linger on the sentence containing the false figure?
- **Scroll-back events.** Scrolling up to re-read is a classic comprehension-difficulty
  signal.

---

## Tier 3 — eye tracking, honestly assessed

You asked about adding an eye tracker for heatmaps. My recommendation: **do not put it
in the main online study; run it as a small separate lab sub-study.**

### Why not in the main study

| Problem | Consequence |
|---|---|
| Webcam gaze estimation (WebGazer.js and similar) has ~4–5° of visual angle error | At typical viewing distance that is 3–5 cm on screen — larger than a spec-table row. It **cannot** resolve which row was fixated, which is precisely the question you want it for. |
| Requires per-participant calibration, and drifts with head movement | Calibration takes 1–3 minutes and degrades continuously through a 20-minute session |
| Requires camera permission | Expect a substantial drop in Prolific uptake and completion, and it is a much heavier ethics conversation (biometric data, video from participants' homes) |
| Uncontrolled lighting, glasses, head pose | Data loss rates of 30–40% are commonly reported, and loss is **not random** — it correlates with glasses, skin tone and lighting, which introduces sampling bias |

Adding it to the N=200 arm would cost you power and add bias to buy a measure too
coarse to answer the question.

### What to do instead

Run a **companion lab study, N ≈ 16–24**, on the same protocol with a real remote
eye tracker (Tobii Pro / EyeLink class, ~0.5° accuracy):

- Define AOIs on the agent's disputed clause and on each spec-table row.
- Report: fixation count and dwell on the disputed row, time-to-first-fixation,
  scanpath from agent text → citation → spec table.
- **Deliverable: a genuine heatmap.** For a CHI SRC poster this is disproportionately
  valuable — judges stop at a good heatmap, and it makes the mechanism visible in a way
  a bar chart cannot.

Frame it in the paper as a **mixed-methods complement**, not a second confirmatory
test. N≈20 is not powered for a 2×2 interaction, and claiming otherwise invites a
methods objection. Its job is to show *how* people look at the evidence, while the
online study establishes *whether* disclosure changes what they do.

If a lab tracker is unavailable, the `specRowsSeen` measure is a defensible proxy and
you should say plainly that it indexes opportunity-to-read rather than gaze.

---

## Ethics implications of this much tracking

Detailed behavioural logging is not covered by a generic "we collect your responses"
consent. Update `docs/IRB_MATERIALS.md` and the consent screen to state:

> We record how you interact with the study interface — which pages you open, how long
> you spend on them, where you scroll and move your cursor, and what you click.

This can be disclosed in full **without** revealing the hypothesis. Nothing in that
sentence tips participants off that errors are planted, so it costs you no validity.

**Do not record:** keystroke content, selected/copied text (we store length only),
clipboard contents, or anything from outside the study origin. The current
implementation already respects this — keep it that way.

Note in the paper that cursor and dwell data are behavioural biometrics of a mild
kind; do not publish raw traces alongside demographics, since combined they raise
re-identification risk.

---

## Data volume

Rough per-participant budget at current settings:

| Stream | Size |
|---|---|
| Trial records | ~15 KB |
| Telemetry events | ~20–40 KB |
| Cursor traces (20 Hz, collinear-pruned) | ~60–120 KB |
| **Total** | **~100–180 KB** |

At N=200 that is roughly 20–35 MB — comfortably inside Supabase's free tier. If you add
raw 60 Hz cursor sampling without pruning, expect ~10× that; don't.
