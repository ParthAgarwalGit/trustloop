# Understanding & Running the TrustLoop Experiment

**Read this first.** It explains what the experiment is, why each piece is built the
way it is, and exactly what *you* have to do. `TASKS.md` is the checklist; this is
the reasoning behind it.

---

## 1. The one-sentence version

> We give people an AI shopping agent that is **wrong 30% of the time in ways we
> control exactly**, and test whether letting them check its work protects them from
> being fooled by a confident, flattering tone.

---

## 2. Why this study is worth running

Three literatures point at each other but have never been joined up:

| What's established | Where | What's missing |
|---|---|---|
| People can't meaningfully oversee agentic AI | FAccT 2026 (oversight papers) | Does *giving* them oversight tools change behaviour? |
| Sycophantic AI tone raises trust but degrades decisions | CHI 2026 (3 papers) | Can anything *protect* against it? |
| Aligning perceived with actual trustworthiness needs a ground truth we don't have | Your AIES 2026 paper | A paradigm where ground truth actually exists |

**Your contribution is the join:** does verifiability *moderate* the sycophancy
effect? Nobody has crossed those two factors. That interaction is the paper.

There's a second, quieter contribution that reviewers will like: your own AIES paper
argues that "actual trustworthiness" has no measurable ground truth in practice. This
design **manufactures one** by scripting the agent. That's a methodological
contribution other trust researchers can reuse.

---

## 3. The design in one picture

```
                        TONE
                honest          sycophantic
              ┌───────────────┬───────────────┐
       opaque │  detection    │  detection    │   ← sycophancy should hurt A LOT here
              │    ~45%       │    ~25%       │
DISCLOSURE    ├───────────────┼───────────────┤
       full   │  detection    │  detection    │   ← ...and much less here
              │    ~70%       │    ~62%       │
              └───────────────┴───────────────┘
                    That difference-of-differences IS H4.
```

- **Between-subjects**, ~50 people per cell, N ≈ 200.
- Each person does **10 trials**; **3 are seeded to be wrong** (slots 4, 7, 9).
- Percentages above are *hypothesised* — they're what the simulator plants so you can
  test the analysis before collecting anything real.

### The four conditions concretely

|  | **Opaque** | **Full disclosure** |
|---|---|---|
| **Honest** | "Here's what I found. [product card] …I may have missed something; please check what matters to you." | Same + step-by-step trace + per-requirement claims you can expand to compare against the catalogue |
| **Sycophantic** | "Great news — I found exactly what you're after! [product card] …You can't go wrong with this one!" | Same + the identical trace and evidence |

**The product spec card is shown in every condition.** This matters and reviewers
will probe it: if opaque participants couldn't see the product's specs at all, they
*couldn't possibly* detect an error, detection would floor at zero, and the
Disclosure effect would be an artefact of information availability rather than a
psychological finding. What varies is the agent's **process and evidence**, not
whether the shop exists.

### Hypotheses

- **H1** Full disclosure → better detection and calibration than opaque.
- **H2** Full disclosure → higher trust *and* higher workload. A trade-off, not a free win.
- **H3** Sycophantic tone → higher self-reported trust but *worse* detection.
- **H4 (the paper)** Disclosure **moderates** H3: sycophancy hurts most when you can't check the work.

---

## 4. Why the agent is scripted, not a real LLM

Deliberate, and worth defending confidently in the paper:

1. **You need an exact error rate.** A live LLM's accuracy is unknown and drifts. Your
   whole design rests on knowing precisely which recommendations are wrong.
2. **Tone must not leak correctness.** If a real model generated the text, it might
   hedge more when less certain — tone would correlate with correctness and H3/H4
   would be uninterpretable. `stimuli/validate_trials.py` structurally forbids this:
   it greps `lib/tone.ts` for ground-truth identifiers and fails the build if any appear.
3. **Zero inference cost, zero latency, zero downtime** during data collection.
4. It's how the sycophancy literature you're building on already works.

The honest framing for the Limitations section: *"We traded ecological validity for
experimental control; validating against a live tool-using agent is future work."*

---

## 5. What the participant actually experiences

```
Consent  →  Instructions  →  Comprehension check  →  10 trials  →  Survey  →  Debrief
 (2 min)       (1 min)          (1 min, gated)       (10-15 min)   (4 min)    (2 min)
```

Per trial:
1. Read the request + 3 requirements
2. See ShopBot's recommendation (condition-dependent presentation)
3. *(full only)* Optionally expand claims to check them against the catalogue
4. Rate confidence 1–7 **before** deciding
5. Accept, or choose a different option from the candidates

Confidence is asked before the decision on purpose: it's the calibration measure, and
it must be recorded before the act of overriding changes how they feel about it.

---

## 6. What gets measured

**Behavioural (the good stuff — ground-truth-anchored):**
- `detection_rate` — proportion of the 3 seeded errors they overrode ← **primary DV**
- `false_alarm_rate` — overrides on correct trials (someone who overrides everything isn't vigilant)
- `detection_minus_fa` — detection corrected for that response bias
- `confidence_gap` — mean confidence on clean minus seeded trials ← **calibration**
- `appropriate_reliance` — accept-when-right + override-when-wrong
- `n_verifications` — which claims they actually expanded, with timestamps

**Self-report:** trust, perceived authenticity, transparency sufficiency, process
acceptability, reliance intention, NASA-TLX (workload), plus manipulation checks.

> **On `confidence_gap` vs a correlation.** The proposal said "correlation between
> confidence and correctness." With only 3 seeded trials per person that correlation
> is extremely noisy and undefined for anyone giving constant confidence. The mean
> difference is the preregistered primary; the correlation is reported as secondary.
> Both are computed.

---

## 7. Your job, in order

### Things only you can do

| # | Task | When | Why it's yours |
|---|---|---|---|
| 1 | **Get ethics approval** | Start now | Involves deception; takes 1–4 weeks. Your existing vignette-study approval does **not** cover this. |
| 2 | **Fill in `app/.env`** | Before piloting | Your name, email, institution, ethics reference appear on the consent screen |
| 3 | **Swap in real scale items** | Before piloting | `survey.ts` ships face-valid *placeholders*, not validated instruments. Check licences. |
| 4 | **Pilot with 8–12 people** | Before the real run | Only way to catch "the errors are too obvious/too hidden" |
| 5 | **Preregister** | After pilot, before collection | Cheap, and a strong quality signal for a student submission |
| 6 | **Run Prolific recruitment** | 1 week | Needs your account and payment |

### The single most important gate

**After the pilot, check the manipulation checks pass** (`python analysis/run_models.py`).

If people in the sycophantic condition don't rate the agent as more complimentary, or
people in the full condition don't rate it as more transparent, **stop**. You're not
manipulating what you think you are, and running 200 participants would waste the
money and the time. This is the one place where pressing on regardless ruins the study.

### The second most important gate

**Detection rate in the `full` condition must land between ~25% and ~85%.**

Above 85% and everyone catches everything (ceiling); below 25% and nobody catches
anything (floor). Either way there's no room for an interaction to show up. Tune
error difficulty in `stimuli/spec/trials_spec.py` and re-pilot.

---

## 8. Running it — the commands

```bash
# one-time setup
cd trustloop/app && npm install
cd .. && python -m pip install -r analysis/requirements.txt

# build + validate stimuli (npm run dev does this automatically)
python stimuli/build_trials.py && python stimuli/validate_trials.py

# develop / preview any cell
cd app && npm run dev
#   http://localhost:5173/?cond=full-sycophantic&preview=1

# rehearse the whole analysis on fake data BEFORE collecting real data
cd .. && python analysis/simulate_data.py --n 200 --out data/raw_sim
python analysis/prepare_data.py --raw data/raw_sim --allow-simulated
python analysis/compute_dvs.py
python analysis/run_models.py
python analysis/make_figures.py

# the real thing
python analysis/export_supabase.py --csv sessions_rows.csv --out data/raw
python analysis/prepare_data.py --raw data/raw
python analysis/compute_dvs.py && python analysis/run_models.py && python analysis/make_figures.py
```

`--preview=1` marks a run as a pilot so `prepare_data.py` excludes it automatically.

---

## 9. Things that will go wrong (and what to do)

| Symptom | Cause | Fix |
|---|---|---|
| Manipulation check fails on tone | Registers too similar | Strengthen the contrast in `lib/tone.ts` — more effusive, more hedged |
| Detection ~0% everywhere | Errors too subtle | Widen the constraint violation (1.9 kg vs a 1.5 kg limit) |
| Detection ~95% everywhere | Errors too obvious | Narrow it (1.55 kg vs 1.5 kg) |
| "Differential attrition" warning | Time-based exclusion hitting opaque harder | Lower `MIN_TOTAL_MINUTES`; opaque is faster *by construction* |
| Cells badly unbalanced | Random assignment drift | Top-up batch on Prolific; Type III SS already handles mild imbalance |
| Cronbach's α < .70 | Placeholder items, or a reverse-scoring error | Check `SCALES` reverse lists in `compute_dvs.py` match your items |
| Many participants guess the deception | Errors too blatant | Report the count, run a sensitivity analysis excluding them, subtler errors next time |

---

## 10. If the result is null

**A null H4 is publishable and you should plan to write it.** "Giving people the
ability to check an AI's work does *not* protect them from a confident tone" is a
genuinely important finding — it argues that transparency requirements alone are
inadequate consumer protection, which is a direct challenge to how AI governance is
currently being written.

What you must not do is quietly drop H4 and write up whichever comparison happened to
come out significant. Preregistration (Phase 6) is what protects you here, and it is
why it's worth the afternoon.

---

## 11. Repository map

```
trustloop/
├── EXPERIMENT_GUIDE.md      ← you are here
├── TASKS.md                 ← the checklist
├── README.md                ← quickstart
├── stimuli/
│   ├── spec/trials_spec.py  ← EDIT HERE to change trials/catalogue
│   ├── build_trials.py      ← computes ground truth, emits JSON
│   └── validate_trials.py   ← 194 internal-validity checks
├── app/                     ← the participant-facing experiment
│   └── src/
│       ├── lib/tone.ts      ← the Tone manipulation (ground-truth-blind by design)
│       ├── components/AgentTrace.tsx  ← the Disclosure manipulation
│       └── data/survey.ts   ← EDIT HERE to swap in validated scales
├── analysis/
│   ├── simulate_data.py     ← fake data with known effects, to test the pipeline
│   ├── prepare_data.py      ← exclusions (auditable in one place)
│   ├── compute_dvs.py       ← DV definitions
│   ├── run_models.py        ← ANOVAs + trial-level GEE, APA-formatted
│   └── make_figures.py      ← publication figures
├── docs/
│   ├── ANALYSIS_PLAN.md     ← preregistration draft
│   ├── STIMULI_DESIGN.md    ← why the stimuli are built this way
│   └── IRB_MATERIALS.md     ← consent, debrief, recruitment text
└── server/supabase_schema.sql
```

---

## 12. Honest limitations to write up

Don't let a reviewer find these before you state them:

1. **Scripted agent** — control bought at the cost of ecological validity.
2. **One task domain** — shopping/travel; doesn't generalise to coding or clinical agents.
3. **Single session** — says nothing about how trust calibration evolves over weeks.
4. **Prolific sample** — younger and more tech-literate than the general population.
5. **30% error rate is high** — chosen for statistical power, not realism. It may make
   participants more vigilant than they'd be with a genuinely reliable agent.
6. **Placeholder scales** — unless you complete task 2.2, say so explicitly.
