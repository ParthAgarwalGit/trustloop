# TrustLoop

**Does letting users verify an AI agent's work protect them from its confident tone?**

A complete, runnable research instrument for a 2×2 between-subjects experiment on
trust calibration in agentic AI — participant-facing web app, controlled stimuli with
a known ground-truth error rate, and a full analysis pipeline.

Built for submission to the **ACM CHI Student Research Competition**.

---

## The idea in 30 seconds

Autonomous AI agents increasingly act on people's behalf, and users have no reliable
way to tell whether a confident presentation reflects actual reliability. Two recent
literatures point at each other but have never been crossed:

- **Oversight** — people can't meaningfully verify what agents did (FAccT 2026)
- **Sycophancy** — agreeable AI tone raises trust while degrading decisions (CHI 2026)

TrustLoop crosses them. A scripted shopping agent is **wrong on exactly 3 of 10
trials**, and we manipulate whether users can check its work (`opaque` / `full`) and
how confident it sounds (`honest` / `sycophantic`).

**H4, the confirmatory hypothesis:** verifiability *moderates* the sycophancy effect —
a confident tone should hurt most when you can't check the work.

Because the agent is scripted, its true error rate is known exactly. That sidesteps
the "no ground truth for actual trustworthiness" problem and is a reusable paradigm in
its own right.

---

## Documentation

| Read this | For |
|---|---|
| **[EXPERIMENT_GUIDE.md](EXPERIMENT_GUIDE.md)** | **Start here.** What the experiment is, why it's built this way, and what you have to do |
| [TASKS.md](TASKS.md) | The stepwise checklist, phase by phase |
| [docs/ANALYSIS_PLAN.md](docs/ANALYSIS_PLAN.md) | Preregistration draft: hypotheses, DVs, exclusions, tests |
| [docs/STIMULI_DESIGN.md](docs/STIMULI_DESIGN.md) | Why the stimuli are built this way — read before editing them |
| [docs/IRB_MATERIALS.md](docs/IRB_MATERIALS.md) | Consent, debrief and recruitment text for ethics approval |

---

## Quickstart

```bash
# install
cd app && npm install
cd .. && python -m pip install -r analysis/requirements.txt

# build + validate stimuli (194 internal-validity checks)
python stimuli/build_trials.py && python stimuli/validate_trials.py

# run the experiment locally
cd app && npm run dev
```

Preview any cell directly:

```
http://localhost:5173/?cond=opaque-honest&preview=1
http://localhost:5173/?cond=opaque-sycophantic&preview=1
http://localhost:5173/?cond=full-honest&preview=1
http://localhost:5173/?cond=full-sycophantic&preview=1
```

### Rehearse the analysis before collecting any data

The pipeline ships with a simulator that plants a known interaction effect, so you can
verify the whole chain recovers it *before* recruiting anyone:

```bash
python analysis/simulate_data.py --n 200 --out data/raw_sim
python analysis/prepare_data.py --raw data/raw_sim --allow-simulated
python analysis/compute_dvs.py
python analysis/run_models.py
python analysis/make_figures.py
```

`prepare_data.py` refuses to mix simulated and real sessions.

---

## What's in here

```
stimuli/     catalogue + trials; ground truth is COMPUTED, and a validator
             enforces 8 classes of design invariant on every build
app/         React + TypeScript experiment: consent → comprehension gate →
             10 trials → survey → debrief, with per-trial behavioural logging
analysis/    power analysis, simulator, exclusions, DVs, ANOVA + trial-level
             GEE, publication figures
server/      Supabase schema with insert-only row-level security
docs/        analysis plan, stimulus rationale, ethics materials
```

### Design safeguards worth knowing about

- **Ground truth is computed, not declared.** The build fails if a trial's label
  disagrees with what the catalogue actually says.
- **Tone is structurally blind to correctness.** The validator greps the tone module
  for ground-truth identifiers and fails the build if any appear — otherwise tone
  could leak correctness and H3/H4 would be circular.
- **The product spec card is visible in every condition.** Hiding it would floor error
  detection in the opaque cell for information-availability reasons rather than
  psychological ones.
- **Differential-attrition check.** Time-based exclusions can bite the opaque
  condition harder (it's faster by construction); `prepare_data.py` warns when
  exclusion rates diverge across cells.

---

## Before you run this

Four things need your attention — see [TASKS.md](TASKS.md):

1. **Ethics approval.** Involves deception; start immediately, it's the long pole.
2. **`app/.env`.** Your name, email, institution and ethics reference appear on the
   consent screen.
3. **Survey scales.** `app/src/data/survey.ts` ships face-valid *placeholders*, not
   validated instruments. Swap in the scales you intend to cite and check their licences.
4. **Pilot with 8–12 people** and confirm the manipulation checks pass before spending
   money on a full sample.

---

## Data protection

`.gitignore` excludes `data/raw/`. Raw sessions contain platform participant IDs,
which are pseudonymous rather than anonymous and are personal data under GDPR. Publish
only de-identified derived tables.

---

## Status

Scaffolding complete and verified: app builds and runs, all four cells render
correctly, stimulus validator passes 194 checks, and the analysis pipeline recovers a
planted interaction from simulated data. **No real data has been collected.**
