# Ethics / IRB Materials

Draft text for your ethics application. **Adapt to your institution's forms — this is
a starting point, not an approved instrument.** Nothing here has been reviewed by a
board.

Replace every `[bracketed]` field.

---

## 1. What your board will focus on

This study uses **deception**: participants are not told that 3 of the 10
recommendations are deliberately wrong. Everything else is routine. Build the
application around the standard four-part justification for authorised deception:

| Requirement | How this study meets it |
|---|---|
| **Deception is necessary** | Telling participants that some recommendations are flawed converts the task into a proofreading exercise. The dependent variable *is* spontaneous vigilance; forewarning destroys the construct. |
| **Risk is no more than minimal** | Participants evaluate fictional consumer products. No real purchase, no money at risk, no sensitive disclosure, no distressing content. |
| **Participants are forewarned that something is withheld** | The consent screen states plainly that the full purpose is not described in advance and that a complete explanation follows. This is authorised deception, not concealment. |
| **Full debriefing with the right to withdraw** | The debrief names the concealment first, explains the manipulation, and offers data withdrawal *after* the reveal — with payment explicitly unaffected. |

> ⚠️ **Your existing approval does not cover this.** If you hold approval for the
> earlier vignette study, that covered reading descriptions of a process. This study
> involves an interactive deceptive manipulation and a different risk profile. Submit
> as new or as a substantial amendment.

---

## 2. Plain-language protocol summary

> Participants complete an online task in which an automated shopping assistant
> ("ShopBot") recommends products and travel packages against stated requirements.
> Participants rate their confidence in each recommendation and choose whether to
> accept it. Unknown to participants, the assistant is scripted, and 3 of its 10
> recommendations deliberately fail one of the stated requirements. Participants are
> randomly assigned to one of four versions differing in (a) how much of the
> assistant's reasoning is shown and (b) how confident its tone is. The study measures
> whether participants notice the flawed recommendations. Session length is
> approximately 15–20 minutes. Participants are fully debriefed and may withdraw their
> data after the debrief without affecting payment.

---

## 3. Risk assessment

| Risk | Likelihood | Mitigation |
|---|---|---|
| Mild discomfort at having been deceived | Low | Debrief states plainly that missing the errors is common and expected, and that the study examines conditions, not individuals |
| Frustration at a poorly performing assistant | Low | No time limit; no performance feedback during the task; participants told there are no wrong answers |
| Perceived judgement of competence | Low | Debrief explicitly states nothing they did caused the errors |
| Re-identification from data | Very low | Only the platform's pseudonymous ID is stored; no name, email or IP. Raw data never leaves local storage / the private database |

**No vulnerable populations.** 18+, general adult online panel.

---

## 4. Consent text

Implemented in `app/src/components/Intro.tsx` (`Consent`). Current wording:

**What is this study?**
You will use an automated shopping assistant called ShopBot. It will make product and
travel recommendations based on requirements we give you, and you will decide whether
to accept each recommendation. Afterwards you will answer some questions about your
experience.

**How long will it take?** About 15–20 minutes.

**Is anything withheld?**
Yes. To keep your responses natural, we are not describing the full purpose of the
study in advance, and some details of how ShopBot behaves are not disclosed until the
end. You will receive a complete explanation on the final screen, and you will be able
to withdraw your data at that point if you would rather we did not use it.

**What data do we collect?**
Your choices, response times, confidence ratings and questionnaire answers, plus your
platform participant ID for payment. We do not collect your name, email address or IP
address. Data are stored pseudonymously and reported only in aggregate.

**Do I have to take part?**
No. Participation is voluntary and you may close the tab at any point without giving a
reason. Partial data from an abandoned session is not analysed.

**Who can I contact?**
[Researcher], [Institution] — [email]. Approved under ethics reference [reference].

☐ I am 18 or older, I have read the information above, and I agree to take part.

---

## 5. Debrief text

Implemented in `app/src/components/Debrief.tsx`. Structure — the order matters:

1. **The concealment, named first.** "3 of the 10 recommendations you saw were
   deliberately wrong." Participants learn what was hidden before anything else.
2. **The agent was not real.** Scripted, not an AI; its errors were planted and had
   nothing to do with the participant's choices.
3. **What was actually being studied.** The four versions, and the question of whether
   being able to check an assistant's work protects against a confident tone.
4. **Personal feedback, carefully framed.** How many errors they caught, prefaced with
   "we are studying differences between groups, not individuals" and "missing planted
   errors is extremely common and is exactly the effect we are investigating."
5. **Withdrawal offered.** Two buttons: *Submit my responses* / *Withdraw my data*.
   Payment explicitly unaffected; no reason required. Withdrawal sets `withdrawn = 1`
   and `analysis/prepare_data.py` drops those sessions.
6. **Contact details** for questions or later withdrawal.

---

## 6. Recruitment text (Prolific)

> **Title:** Evaluating an automated shopping assistant
>
> **Description:** You will use an online shopping assistant that recommends products
> and travel packages, and decide whether to accept its recommendations. You will then
> answer some questions about your experience. Takes about 15–20 minutes. Requires a
> desktop or laptop with a full-size screen.
>
> **Requirements:** 18+, fluent English, previous experience shopping online.

Keep the title and description neutral. Any mention of trust, errors, or AI
reliability would prime the exact vigilance the study measures.

---

## 7. Data management

| | |
|---|---|
| **Collected** | Platform participant ID, trial choices, response times, confidence ratings, questionnaire responses, user-agent string, viewport size |
| **Not collected** | Name, email, IP address, location, any free-text identifying information |
| **Storage** | [Supabase project in region X] with row-level security permitting insert only; the anonymous key cannot read, update or delete |
| **Access** | [Researcher] only, via a service-role key not stored in the repository |
| **Retention** | Raw data retained [N] years per [institution] policy, then deleted |
| **Sharing** | De-identified derived tables only. Participant IDs replaced with study-local codes. **Raw data containing platform IDs is never published** — `.gitignore` excludes `data/raw/` |
| **Legal basis (if GDPR applies)** | [consent / legitimate interest — check with your DPO] |

Platform participant IDs are pseudonymous, not anonymous: they can be linked back to a
person through the recruitment platform. Treat them as personal data.

---

## 8. Pre-submission checklist

- [ ] Deception justified using the four-part structure in §1
- [ ] Debrief text attached in full
- [ ] Post-debrief withdrawal described, with payment explicitly unaffected
- [ ] Consent text attached in full
- [ ] Recruitment advert attached
- [ ] Data management plan completed (§7)
- [ ] Compensation stated and at or above the platform minimum
- [ ] Confirmed no vulnerable populations
- [ ] Screenshots of all four experimental conditions attached
- [ ] Contact details for a complaints route independent of the researcher
