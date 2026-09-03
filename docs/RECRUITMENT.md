# Recruiting Without Telling Them What You're Measuring

The study only works if participants behave as they would with a real assistant. Every
word of recruitment copy, instructions and interface text is a chance to accidentally
tell them to be vigilant — and a participant who has been told to check will check,
in every condition, flattening exactly the effect you are trying to measure.

---

## The one-sentence rule

> **Never mention trust, accuracy, errors, checking, verifying, reliability,
> transparency, or AI safety — anywhere a participant can see, at any point before
> the debrief.**

Not in the study title. Not in the consent form. Not in the instructions. Not in the
interface. Not in the Prolific listing.

### Words that are poison

| Banned | Why | Say instead |
|---|---|---|
| "trust", "trustworthy" | Names the DV | — (omit entirely) |
| "accurate", "errors", "mistakes" | Announces that errors exist | — |
| "verify", "check", "confirm" | Instructs the behaviour you're measuring | "decide", "choose" |
| "AI safety", "reliability" | Frames the whole task | "shopping assistant" |
| "evaluate the assistant" | Makes the assistant the object of judgement | "use the assistant to shop" |
| "carefully", "pay attention" | Raises vigilance uniformly | — |

Note the last one. "Please read carefully" feels like good practice and is actively
harmful here: it inflates vigilance in all four cells and compresses the interaction
you are testing.

---

## The cover story

**Frame: a product-feedback study for a shopping assistant that is about to launch.**

This is a good cover because it is *true in structure* (you genuinely want their
reactions to an assistant), it explains why there are 10 repetitive requests, and it
gives them a plausible reason for the questionnaire at the end — without hinting that
the assistant might be wrong.

### Prolific listing

> **Title:** Try out a new AI shopping assistant (15–20 min)
>
> **Description:** We're testing a shopping assistant that finds products and travel
> packages based on requirements you give it. You'll work through 10 short shopping
> requests, decide what you'd go with each time, and then answer some questions about
> what the experience was like. Requires a desktop or laptop.
>
> **Requirements:** 18+, fluent English, previous experience shopping online.

Neutral, accurate, and gives nothing away.

---

## The incentive — the part most designs get wrong

Without stakes, participants have no reason to care whether the recommendation is
correct, and detection rates floor out for reasons of apathy rather than psychology.
That is a real threat to the study: you would be measuring boredom.

**Add a performance bonus.**

> "You'll receive a bonus of £0.50 for each request where your final choice meets all
> the stated requirements. Most people earn between £2 and £4."

Why this works:

- It creates a genuine reason to get it right, which is what makes the task
  ecologically comparable to real shopping (where a bad choice costs you money).
- It **never mentions the assistant's reliability.** It says "your choice must meet the
  requirements", not "the assistant may be wrong". A participant can satisfy that by
  trusting a good assistant — the incentive does not imply distrust.
- It is **constant across all four cells**, so it cannot produce the interaction. It
  raises the floor everywhere, which is what you want: it moves detection away from
  zero and into the range where an interaction can actually be observed.

Budget it: 10 trials × £0.50 × 200 participants is a worst-case £1,000 if everyone is
perfect. Realistically expect 60–75% correct, so ~£600–750. If that is too much, use
£0.25 and say "up to £2.50 in bonuses" — the psychological function is the incentive
existing, not its size.

Pay every bonus that is earned, including to participants whose data you later
exclude.

---

## Instruction wording

What the app currently says, and why each choice is deliberate:

> "For each request, **ShopBot** searches a product catalogue and recommends one
> option. Your job is to decide whether that recommendation is a good one."

- "decide whether it's a good one" gives them a task without telling them to audit.
- No mention that ShopBot might be wrong.
- No mention of checking sources — the citations are simply *there*, and whether they
  use them is the measurement.

> "There is no time limit. Please treat each request as though you were shopping for
> yourself."

- "as though you were shopping for yourself" recruits their normal shopping standards
  rather than an experimental-subject standard.
- "no time limit" prevents speed pressure from suppressing verification, which would
  interact with condition (the full condition has more to read).

**Do not add** "take your time and check the details" — that is the instruction-to-be-
vigilant failure mode.

---

## Detecting who saw through it

Deception studies must report how many participants guessed. Two funnel-debrief items
sit at the very end of the questionnaire, after everything else, in this order:

1. *"Did you notice anything unusual about ShopBot or about this study?"* (open text)
2. *"How did you decide whether to accept or change a recommendation?"* (open text)

Order matters — asking the specific question first would plant the idea.

**Coding scheme** (two coders, report Cohen's κ):

| Code | Criterion |
|---|---|
| 0 — no suspicion | No mention of errors or of the assistant being wrong |
| 1 — vague | Notes something "off" but not that recommendations were incorrect |
| 2 — partial | Suspected some recommendations were wrong |
| 3 — full | Identified that errors were deliberately planted |

Preregister the rule: **report the counts, and run the confirmatory analysis both with
and without codes 2–3.** If the effect only exists among the unsuspicious, that is a
finding about demand characteristics and should be said out loud, not buried.

---

## Pilot check specifically for the cover story

During the pilot (Phase 5), ask each participant afterwards, in this order:

1. "What do you think this study was about?"
2. "Did anything seem odd?"
3. *Only then:* "Did you think the assistant was always right?"

If more than about 2 in 10 spontaneously reach code 2+ at question 1 or 2, the errors
are too blatant — widen the gap between the agent's claim and the source only where
detection is at floor, and otherwise make the violations narrower. See
`docs/STIMULI_DESIGN.md` on tuning difficulty.

---

## What you must disclose even while concealing the hypothesis

Concealing the purpose is not the same as concealing the procedure. The consent screen
must still say, plainly:

- that some information about the study's purpose is withheld until the end
- that interaction data is recorded (pages opened, dwell, scrolling, cursor, clicks)
- that a full explanation follows and they may withdraw their data afterwards

None of that reveals the hypothesis. All of it is required for the deception to be
*authorised* rather than simply undisclosed — which is the distinction your ethics
board will care about most.
