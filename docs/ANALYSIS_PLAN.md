# Analysis Plan (Preregistration Draft)

Fill in the bracketed fields and register on [osf.io/prereg](https://osf.io/prereg)
**after piloting and before main data collection.** Then tag the frozen commit:

```bash
git tag -a prereg -m "Analysis plan frozen at preregistration" && git push --tags
```

---

## 1. Study information

**Title.** Does Verifiability Protect Users from Sycophantic AI Agents? A 2×2
Experiment on Trust Calibration in Agentic Systems

**Authors.** [Your name], [institution]. *(CHI SRC: no faculty co-authors. Advisor in
Acknowledgements only.)*

**Research question.** When an autonomous AI agent makes errors, does giving users the
ability to verify its work reduce the over-reliance produced by a confident,
sycophantic conversational tone?

---

## 2. Hypotheses

| ID | Hypothesis | Primary test |
|---|---|---|
| **H1** | Full disclosure improves error detection and trust calibration relative to opaque | Main effect of Disclosure on `detection_rate`, `confidence_gap` |
| **H2** | Full disclosure raises trust *and* workload — a trade-off | Main effect of Disclosure on `trust` and on `tlx_raw` |
| **H3** | Sycophantic tone raises self-reported trust but worsens detection | Main effect of Tone on `trust` (positive) and `detection_rate` (negative) |
| **H4** | **Disclosure moderates the sycophancy effect**: the detection penalty from sycophantic tone is larger under opaque than under full disclosure | **Disclosure × Tone interaction on `detection_rate`** |
| H5 *(exploratory)* | Learning that disclosure was authored by the agent's provider rather than an independent auditor lowers process acceptability | Debrief item; exploratory only |

**H4 is the confirmatory test of record.** Everything else is secondary.

Directional predictions for the H4 simple effects: the sycophantic − honest
difference in `detection_rate` is negative and larger in magnitude under `opaque`
than under `full`.

---

## 3. Design

- **Type.** 2 × 2 fully between-subjects factorial.
- **Factor A — Disclosure/Verifiability:** `opaque` | `full`
- **Factor B — Tone:** `honest` | `sycophantic`
- **Assignment.** Uniform random per participant, client-side, seeded by participant
  ID (reproducible). Not block-balanced; realised cell sizes are reported and Type III
  sums of squares are used.
- **Why between-subjects.** A participant can only discover that the agent is fallible
  once. Within-subjects exposure would contaminate all subsequent trials.

**Held constant across conditions:** the trial set, the seeded error rate (3/10), the
serial position of errors (slots 4, 7, 9), the product spec card, and the ability to
override.

---

## 4. Sample

- **Target N.** 200 (50 per cell), recruited via Prolific.
- **Justification.** A priori power analysis (`analysis/power_analysis.py`):
  N = 200 gives **0.85 power** to detect a medium interaction (Cohen's *f* = 0.25,
  partial η² ≈ .06) at α = .05 for a 1-df contrast. Interactions in factorial designs
  require roughly 4× the N of a comparable main effect, so N is powered on H4, not on
  the main effects.
- **Inclusion.** 18+, fluent English, prior online shopping experience.
- **Compensation.** [rate] for an estimated 15–20 minutes, at or above the Prolific
  minimum.
- **Exclusion of pilot participants** from the main sample.

---

## 5. Exclusion criteria (applied in `analysis/prepare_data.py`)

Fixed before collection. Applied in exactly one place so they are auditable.

1. Preview/pilot runs (`?preview=1`)
2. Withdrew at debrief
3. Incomplete session (no `completedAt`, or fewer than 10 trials)
4. Failed **more than one** of two attention checks
5. Median per-trial RT < 3000 ms *(primary speeding check)*
6. Total task time < 2.0 minutes *(backstop only)*

> **On criterion 6.** The threshold is deliberately loose. The full-disclosure
> interface takes materially longer to read, so a tight aggregate floor removes
> opaque participants several times more often — differential attrition that biases
> the central comparison. `prepare_data.py` reports exclusion rate per cell and warns
> when the spread exceeds 10 percentage points. **If that warning fires, report it and
> run the analysis on the unexcluded sample as a sensitivity check.**

Exclusions are reported as a participant-flow table
(`data/derived/exclusions.csv`) with counts by reason and by cell.

---

## 6. Measures

### Independent variables
`disclosure` ∈ {opaque, full} · `tone` ∈ {honest, sycophantic}

### Primary dependent variable
**`detection_rate`** — proportion of the 3 seeded-error trials on which the
participant overrode the agent's recommendation.

### Secondary dependent variables

| Variable | Definition |
|---|---|
| `detection_minus_fa` | `detection_rate` − `false_alarm_rate`; detection corrected for response bias |
| `confidence_gap` | mean confidence on clean trials − mean on seeded trials (**primary calibration measure**) |
| `calibration_r` | within-participant point-biserial *r* between confidence and correctness (**secondary**; noisy with 3 seeded trials, undefined for constant responders) |
| `appropriate_reliance` | proportion of all trials with accept-when-clean or override-when-seeded |
| `false_alarm_rate` | overrides on clean trials (control measure) |
| `detection_rate_strict` | overrode **and** selected a genuinely compliant alternative |
| `trust` | 4-item scale, α reported |
| `authenticity` | 3-item scale |
| `transparency_suff` | 2-item scale |
| `reliance_intent` | 2-item scale |
| `process_acceptability` | single 5-point item |
| `tlx_raw` | unweighted NASA Raw TLX, mean of 6 subscales |
| `mean_verifications`, `prop_trials_verified` | process measures (full condition only) |

> **Deviation from the original proposal, stated up front.** The proposal named a
> confidence–correctness *correlation* as the calibration measure. With only 3 seeded
> trials per participant that statistic is unstable and undefined for participants who
> give constant confidence ratings. `confidence_gap` (a mean difference) is therefore
> the preregistered primary; `calibration_r` is reported as a secondary. Both are
> computed by `compute_dvs.py`.

### Manipulation checks
`mc_tone_warm`, `mc_tone_hedge` (Tone) · `mc_disc_steps`, `mc_disc_verify`
(Disclosure). **Reported before any hypothesis test.**

---

## 7. Statistical analysis

### Confirmatory

1. **Manipulation checks.** Welch's *t*-tests. If either factor fails, hypothesis
   tests are reported as uninterpretable rather than as findings.
2. **H1–H4.** 2 × 2 between-subjects ANOVA per DV, **Type III sums of squares** with
   sum (effect) coding — appropriate for unbalanced cells. Report *F*, df, exact *p*,
   and partial η² for both main effects and the interaction.
3. **H4 follow-up.** Simple effects of Tone within each Disclosure level (Welch's
   *t*, Cohen's *d*), reported whenever the interaction reaches *p* < .10.
4. **Trial-level confirmation.** GEE logistic regression of per-trial `overrode` on
   seeded-error trials, `Disclosure * Tone`, exchangeable working correlation
   clustered by participant. This uses the trial-level structure the participant-level
   ANOVA discards.

### Assumptions
Normality of residuals inspected via Q–Q plots; Levene's test for homogeneity of
variance. Because `detection_rate` is a proportion over 3 trials it is coarse and
non-normal — the trial-level GEE is the assumption-robust confirmation, and where
ANOVA and GEE disagree, **the GEE is reported as authoritative**.

### Exploratory (labelled as such)
- Detection by error type (dropped constraint / false claim / arithmetic)
- Verification behaviour as a mediator between Disclosure and detection
- Serial position effects across trial slots
- AI familiarity as a covariate
- Qualitative coding of open-text responses

---

## 8. Inference criteria

α = .05, two-tailed. No correction across DVs for the confirmatory H4 test (a single
prespecified test). Secondary DVs are explicitly labelled secondary and interpreted
with Holm correction within family.

**A null H4 will be reported as a finding**, not reframed. It would indicate that
verifiability does not protect against tone-driven over-reliance — directly relevant
to transparency-based AI governance, which assumes it does.

---

## 9. Known limitations (to state in the paper)

1. Scripted rather than live agent — control traded for ecological validity
2. Single task domain (consumer shopping/travel)
3. Single session; no longitudinal trust dynamics
4. Prolific sample skews young and tech-literate
5. 30% error rate chosen for statistical power, higher than a deployed agent's
6. Client-side randomisation is unblocked, so cell sizes drift

---

## 10. Ethics

Approved by [board] under [reference]. Involves **deception with full debriefing**:
participants are told at consent that information is withheld and that they will be
fully informed at the end; the debrief names the concealment explicitly and offers
data withdrawal after the reveal, with payment unaffected. See
`docs/IRB_MATERIALS.md`.
