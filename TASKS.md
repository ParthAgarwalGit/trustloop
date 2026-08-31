# TrustLoop — Executable Task List

Every task is a concrete, checkable action. Work top to bottom; the phases are
ordered by dependency. Boxes marked **[DONE]** are already implemented in this
repository — verify them rather than rebuild them.

Legend: ⏱ = rough effort · 🔒 = blocks everything after it · 👤 = only you can do it

---

## Phase 0 — Setup (⏱ 30 min)

- [x] **[DONE]** Repository scaffolded (`app/`, `stimuli/`, `analysis/`, `docs/`, `server/`)
- [x] **[DONE]** `.gitignore` excludes participant data and `.env`
- [ ] **0.1** Install Node dependencies
  ```bash
  cd trustloop/app && npm install
  ```
- [ ] **0.2** Install Python dependencies
  ```bash
  cd trustloop && python -m pip install -r analysis/requirements.txt
  ```
- [ ] **0.3** Verify the toolchain end-to-end
  ```bash
  cd trustloop && python stimuli/build_trials.py && python stimuli/validate_trials.py && cd app && npm run build
  ```
  Expect: `VALIDATION PASSED (194 checks)` and a successful Vite build.

---

## Phase 1 — Stimuli (⏱ 2–4 h) 🔒

The experiment's internal validity lives here. Nothing downstream is meaningful if
the stimuli are wrong.

- [x] **[DONE]** Catalogue of 18 laptops + 12 travel packages (`stimuli/spec/trials_spec.py`)
- [x] **[DONE]** 10 trials, 3 seeded errors at fixed slots 4/7/9
- [x] **[DONE]** Three distinct error types: dropped constraint, false claim, arithmetic
- [x] **[DONE]** Ground truth *computed* from the catalogue, never hand-asserted
- [x] **[DONE]** Validator enforcing 8 classes of design invariant (194 checks)
- [ ] **1.1** 👤 Read every trial prompt aloud and check it sounds like something a
      real person would ask. Edit `TRIALS` in `stimuli/spec/trials_spec.py`, then
      rebuild and re-validate.
- [ ] **1.2** 👤 Sanity-check error *difficulty*. A seeded error must be findable but
      not glaring. If pilot detection in the `full` condition exceeds ~85% or falls
      below ~25%, adjust: make violations narrower (e.g. 1.71 kg against a 1.5 kg
      limit) to harden, wider to soften.
- [ ] **1.3** Decide whether 10 trials / 3 errors is right for your session length.
      More error trials = a more stable per-participant detection rate. If you change
      the count, update `ERROR_SLOTS` and re-run the validator — it will reject
      errors in slots 1–3 or in the final slot.

---

## Phase 2 — Application (⏱ 4–8 h)

- [x] **[DONE]** React + TypeScript app, builds clean
- [x] **[DONE]** Consent → instructions → comprehension gate → 10 trials → survey → debrief
- [x] **[DONE]** Disclosure manipulation (`opaque` vs `full`) in `AgentTrace.tsx`
- [x] **[DONE]** Tone manipulation (`honest` vs `sycophantic`) in `lib/tone.ts`,
      structurally prevented from seeing ground truth
- [x] **[DONE]** Per-trial logging: decision, confidence, RT, verification events
- [x] **[DONE]** Within-block trial randomisation preserving fixed error positions
- [x] **[DONE]** localStorage mirroring + JSON download fallback + retry on submit failure
- [ ] **2.1** 👤 Fill in `app/.env` from `app/.env.example` — researcher name, email,
      institution, ethics reference. These render on the consent and debrief screens.
- [ ] **2.2** 👤 Replace the placeholder scale items in `app/src/data/survey.ts`
      (blocks `trust`, `authenticity`, `reliance`) with the validated instruments you
      intend to cite. Check each scale's licence. Keep the item `id`s unchanged or
      update `analysis/compute_dvs.py` to match.
- [ ] **2.3** Walk all four cells yourself and screenshot each for the paper:
  ```bash
  npm run dev
  ```
  - `http://localhost:5173/?cond=opaque-honest&preview=1`
  - `http://localhost:5173/?cond=opaque-sycophantic&preview=1`
  - `http://localhost:5173/?cond=full-honest&preview=1`
  - `http://localhost:5173/?cond=full-sycophantic&preview=1`
- [ ] **2.4** Test on a phone. A meaningful share of Prolific participants are on
      mobile; if the interface is unusable there you must either fix it or screen
      mobile out in Prolific (and say so in Limitations).
- [ ] **2.5** Confirm the tone manipulation reads as intended to someone who is not
      you. Ask two people which version sounds "more confident" without telling them
      what you are manipulating.

---

## Phase 3 — Data collection infrastructure (⏱ 2–3 h)

- [x] **[DONE]** Pluggable data sink: `none` / `supabase` / `endpoint`
- [x] **[DONE]** Supabase schema with insert-only row-level security
- [x] **[DONE]** Export helper that splits a Supabase dump into per-session files
- [ ] **3.1** 👤 Create a Supabase project (free tier) and run
      `server/supabase_schema.sql` in its SQL editor.
- [ ] **3.2** 👤 Put the project URL and **anon** key in `app/.env`, set
      `VITE_DATA_SINK=supabase`. Never use the service-role key here.
- [ ] **3.3** Verify a submission actually lands:
  ```bash
  npm run build && npm run preview
  ```
  Complete one run, then check the `sessions` table in the dashboard.
- [ ] **3.4** 🔒 Verify the security model holds. With the anon key, a `SELECT` must
      be refused:
  ```bash
  curl "$SUPABASE_URL/rest/v1/sessions?select=*" -H "apikey: $ANON_KEY"
  ```
  Expect an empty array or a permission error — **never** participant rows. If rows
  come back, your RLS policy is wrong and participant data is world-readable.
- [ ] **3.5** Deploy. Any static host works; the build output is `app/dist`.
      Vercel: import the repo, root directory `app`, framework Vite, add the same
      env vars in the dashboard.
- [ ] **3.6** Test the deployed URL exactly as a participant will receive it,
      including the `?PROLIFIC_PID=...` parameters.

---

## Phase 4 — Ethics approval (⏱ 1–4 weeks wall clock) 🔒 👤

**Start this in parallel with Phase 2 — the wait, not the work, is the bottleneck.**

- [x] **[DONE]** Draft consent text (authorised-deception pattern), debrief text with
      the reveal, and post-debrief withdrawal — see `docs/IRB_MATERIALS.md`
- [ ] **4.1** 👤 Adapt `docs/IRB_MATERIALS.md` to your institution's forms.
- [ ] **4.2** 👤 Submit. Flag prominently that the study involves **deception with
      full debriefing** — that is the part your board will scrutinise. Your existing
      approval for the vignette study does **not** cover this; the manipulation and
      the risk profile are different.
- [ ] **4.3** 👤 On approval, put the reference number in `app/.env`
      (`VITE_ETHICS_REF`). Do not recruit before this exists.

---

## Phase 5 — Pilot (⏱ 1 week) 🔒

- [ ] **5.1** Recruit 8–12 people you can talk to afterwards (classmates are fine).
- [ ] **5.2** Watch at least three of them complete it, in silence. Note every point
      of hesitation. Do not explain anything.
- [ ] **5.3** Run the pipeline on pilot data:
  ```bash
  python analysis/prepare_data.py --raw data/raw
  python analysis/compute_dvs.py
  ```
- [ ] **5.4** 🔒 **Check the manipulation checks pass.**
  ```bash
  python analysis/run_models.py
  ```
  `mc_tone_warm` must be higher for sycophantic; `mc_disc_steps` and
  `mc_disc_verify` must be higher for full. **If these fail, stop.** A failed
  manipulation check means you are not manipulating what you think you are, and the
  full sample would be wasted.
- [ ] **5.5** Check detection rate lands between ~25% and ~85% in the `full`
      condition. Outside that band you have a floor or ceiling effect and cannot
      detect an interaction. Retune error difficulty (task 1.2) and re-pilot.
- [ ] **5.6** Check median trial RT against the exclusion thresholds in
      `analysis/prepare_data.py`, and confirm the differential-attrition warning does
      **not** fire.
- [ ] **5.7** Ask pilot participants directly: "did anything about the study seem
      off?" Anyone who guessed the deception is a hypothesis-guessing risk; if that
      is common, make the errors subtler.

---

## Phase 6 — Preregistration (⏱ 2–3 h) 👤

Do this **after** the pilot and **before** the real run. Preregistration is cheap,
takes an afternoon, and is one of the clearest quality signals a student submission
can carry.

- [ ] **6.1** Run the power analysis and paste the output into the prereg:
  ```bash
  python analysis/power_analysis.py
  ```
- [ ] **6.2** Register on OSF (osf.io/prereg) with: hypotheses H1–H4, the exact DV
      definitions from `docs/ANALYSIS_PLAN.md`, the exclusion rules from
      `analysis/prepare_data.py`, and your target N.
- [ ] **6.3** Freeze the analysis code: tag the commit you preregistered against.
  ```bash
  git tag -a prereg -m "Analysis plan frozen at preregistration" && git push --tags
  ```

---

## Phase 7 — Main data collection (⏱ 1 week)

- [ ] **7.1** 👤 Create the Prolific study. Settings that matter:
      - Completion code matching `VITE_COMPLETION_CODE`
      - Pay at or above the platform minimum for a 20-minute study
      - Screeners: fluent English; consider desktop-only (see 2.4)
      - **Exclude anyone who took the pilot**
- [ ] **7.2** Launch a soft batch of ~20 first. Check the data lands correctly and
      cell assignment looks roughly balanced before releasing the rest.
- [ ] **7.3** Release the remainder to N ≈ 200.
- [ ] **7.4** Monitor daily with the SQL in `server/supabase_schema.sql`. Watch for
      duplicate submissions and cell imbalance.
- [ ] **7.5** Top up any cell that ends up short — assignment is random per
      participant, not balanced, so drift is expected.

---

## Phase 8 — Analysis (⏱ 1 week)

- [x] **[DONE]** Full pipeline, verified end-to-end against simulated data with a
      known planted interaction
- [ ] **8.1** Export and prepare:
  ```bash
  python analysis/export_supabase.py --csv sessions_rows.csv --out data/raw
  python analysis/prepare_data.py --raw data/raw
  ```
- [ ] **8.2** 👤 Resolve any duplicate submissions the exporter flags **before**
      proceeding. Keep the first completed submission per participant.
- [ ] **8.3** Compute DVs and check scale reliabilities:
  ```bash
  python analysis/compute_dvs.py
  ```
  Report every Cronbach's α; flag any below .70 in the paper.
- [ ] **8.4** Fit the models:
  ```bash
  python analysis/run_models.py
  ```
- [ ] **8.5** 🔒 Report the manipulation checks **first**, before any hypothesis test.
- [ ] **8.6** Generate figures:
  ```bash
  python analysis/make_figures.py
  ```
- [ ] **8.7** Code the open-text responses (`sv_open_noticed`, `sv_open_strategy`) for
      participants who guessed the manipulation. Report the count; run a sensitivity
      analysis excluding them.
- [ ] **8.8** 👤 Write results straight from `model_results.csv` — every test
      statistic, df, exact p and partial η² is already there in APA form.

---

## Phase 9 — Writing (⏱ 2 weeks) 👤

- [ ] **9.1** Draft against `docs/ANALYSIS_PLAN.md`, which already maps each
      hypothesis to its test.
- [ ] **9.2** Ensure the paper reports: manipulation checks, exclusions with reasons
      (`data/derived/exclusions.csv` is a ready-made participant-flow table), effect
      sizes everywhere, and the null results as plainly as the significant ones.
- [ ] **9.3** Confirm CHI SRC eligibility: **no faculty co-authors**, advisor in
      Acknowledgements only, ≤ 5 pages excluding references, single-column ACM
      template. See `CHI_Paper_and_SRC_Authoring_Guide.md`.
- [ ] **9.4** Add alt-text to every figure.
- [ ] **9.5** Publish an anonymised replication package: this repo plus
      `data/derived/` with participant IDs replaced by study-local codes. **Never
      publish `data/raw/`** — it contains Prolific IDs.
- [ ] **9.6** Include the Generative AI disclosure (required by CHI).

---

## Critical path

```
Ethics (Phase 4) ─────────────────────────┐
                                          ├──> Pilot (5) ──> Prereg (6) ──> Collect (7) ──> Analyse (8) ──> Write (9)
Stimuli (1) ──> App (2) ──> Infra (3) ────┘
```

Phase 4 is the long pole in wall-clock time and the only one you cannot compress by
working harder. Submit for ethics approval the week you start Phase 2.
