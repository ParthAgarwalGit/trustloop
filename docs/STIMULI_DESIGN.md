# Stimulus Design Rationale

Why the trials are built the way they are. Read before editing
`stimuli/spec/trials_spec.py` — several choices that look arbitrary are load-bearing,
and the validator will reject changes that break them.

---

## The central design problem

The study needs an agent that is **wrong in a known, controlled way**. Three things
have to be true at once:

1. **The error must be real** — the recommendation genuinely fails a stated requirement.
2. **The error must be detectable** — a diligent participant *can* find it.
3. **Detectability must not vary with condition for the wrong reasons** — the
   manipulation should change *whether people look*, not *whether looking is possible*.

Point 3 is the subtle one, and it drives most of what follows.

---

## Why the spec card is shown in every condition

A tempting design: opaque participants see only "I recommend the Valta Book 14," with
no specifications at all.

**This would break the study.** Those participants could not detect an error even in
principle. Detection would floor at zero, the Disclosure main effect would be
guaranteed, and it would measure *information availability*, not vigilance. Worse, the
H4 interaction would be uninterpretable — you cannot moderate an effect that is
structurally pinned at zero.

So the product spec card — price, RAM, weight, rating — is visible in **all four
cells**, exactly as it would be on any shopping site. What the Disclosure manipulation
varies is the agent's **process and evidence**:

| | Opaque | Full |
|---|---|---|
| Product specs | ✅ shown | ✅ shown |
| Agent's step-by-step trace | ❌ | ✅ |
| Per-requirement claims | ❌ | ✅ |
| Claim → catalogue comparison | ❌ | ✅ |
| Other candidates considered | ❌ | ✅ |
| Can override | ✅ | ✅ |

A participant in the opaque condition who carefully reads the spec card against the
three stated requirements **will** catch the error. Most won't bother. That gap is the
psychological effect the study is about.

---

## Why ground truth is computed, never declared

`trials_spec.py` names which item the agent recommends. It does **not** assert whether
that recommendation is correct. `build_trials.py` evaluates every constraint against
the catalogue and derives:

- `violatedConstraintIds` — which requirements the pick actually fails
- `isErrorTrial` — whether it fails any
- `compliantCandidateIds` — which alternatives genuinely satisfy everything

If the spec declares a trial clean but the pick violates a constraint (or vice versa),
**the build fails**. This makes an entire category of silent error impossible: you
cannot ship a trial whose label disagrees with its content, and you cannot break the
labelling by editing a single number in the catalogue.

---

## The three error types

Using one failure mode would make the results specific to that mode. Three are seeded:

| Type | Slot | What the agent does | How it's caught |
|---|---|---|---|
| `dropped_constraint` | 4 | Silently omits a requirement from its filter; the pick violates it | Notice a requirement is never mentioned; check it yourself |
| `arithmetic` | 7 | States a total price that is wrong; the true total exceeds budget | Recompute flight + hotel × nights |
| `false_claim` | 9 | States a specification that contradicts the catalogue (says 16 GB, actually 8 GB) | Compare the claim against the catalogue record |

`false_claim` and `arithmetic` are directly checkable in the full condition (the
evidence panel puts "ShopBot reported" next to "Catalogue record"). `dropped_constraint`
is different in kind — nothing is *falsified*, something is *absent* — which is why
having all three matters. `run_models.py` reports detection by error type as an
exploratory breakdown.

---

## Why the agent's trace stays internally consistent

Early on, the `Compare` step reported the *true* number of compliant options. On error
trials this contradicted the agent's own recommendation ("2 options passed" followed by
recommending a third), giving an inconsistency cue **present only on error trials** —
an unintended detection signal confounded with the thing being measured.

`agent_view_pass_ids()` now computes the pass count *as the agent believes it applied
its own filter*, including its own mistake. The validator enforces that the recommended
item always passes the agent's own filter, so the trace never visibly contradicts
itself.

**Rule: the agent must look self-consistent on every trial. It is wrong about the
world, never wrong about itself.**

---

## Why error positions are fixed but content is shuffled

Errors sit at slots **4, 7, 9**:

- **Not 1–3.** Early errors land while participants are still learning the interface,
  confounding detection with task familiarity.
- **Not 10.** End-of-task fatigue and finish-line effects.
- **Fixed across conditions.** Serial position is identical for every participant in
  every cell, so it cannot confound the between-subjects comparison.

Meanwhile `RANDOMISE_WITHIN_BLOCKS` shuffles *which* trial content appears at each
position — clean trials among clean slots, error trials among error slots. Position
effects stay controlled; no single trial's quirks drive the result.

---

## Why tone is structurally blind to correctness

The single greatest threat to H3/H4 would be tone that varies with correctness. If the
honest agent hedged *more* when it was actually wrong, it would be flagging its own
errors, and "honest tone improves detection" would be circular.

`lib/tone.ts` therefore receives **only** the item's display name and the number of
claims. It cannot see `isErrorTrial`, `violatedConstraintIds`, or anything else.
`validate_trials.py` greps the file for every ground-truth identifier and fails the
build if one appears.

Both registers apply on **every** trial. The honest agent's hedging is a constant
stylistic register, not a correctness signal.

---

## Tuning error difficulty

The most likely reason for a failed study is detection at floor or ceiling. Target
**25–85%** in the `full` condition.

**Too few detections?** Widen the violation — a 1.9 kg laptop against a 1.5 kg limit is
more visible than 1.55 kg. Use rounder, more salient numbers.

**Too many?** Narrow it. Put the violated field lower in the spec card. Prefer
`dropped_constraint` (absence) over `false_claim` (contradiction), which is harder to
notice.

After any edit:

```bash
python stimuli/build_trials.py && python stimuli/validate_trials.py
```

---

## Invariants the validator enforces

| ID | Invariant | Why |
|---|---|---|
| I1 | Ground truth computed, never asserted | Prevents mislabelled trials |
| I2 | Tone module cannot reference ground truth | Prevents tone leaking correctness |
| I3 | Every claim maps to a real catalogue field | Makes verification possible |
| I4 | Every trial has ≥1 compliant alternative | Override must always be rational |
| — | Errors never in slots 1–3 or the final slot | Learning / fatigue confounds |
| — | ≥2 distinct error types | Generalisability beyond one failure mode |
| — | Agent's claims satisfy its own constraints | No self-contradictory traces |
| — | Dropped constraints are genuinely absent from claims | Error type does what it says |

194 checks total. **Run the validator after every stimulus edit.** It is the difference
between a study that measures what you think it measures and one that doesn't.
