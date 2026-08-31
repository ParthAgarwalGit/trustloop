import { useState } from "react";
import { COMPLETION_CODE, COMPLETION_URL, STUDY_CONTACT } from "../config";
import type { SessionPayload, Trial, TrialResponse } from "../types";
import { scoreSession } from "../lib/scoring";
import { downloadJson, submit, type SubmitResult } from "../lib/logging";

/**
 * Debrief.
 *
 * Three things have to happen here for the deception to be ethically defensible:
 *   1. the concealment is named plainly, before anything else;
 *   2. the participant is told they personally were not being judged;
 *   3. withdrawal is offered *after* the reveal, and is honoured -- the flag is
 *      recorded on the submitted record and `analysis/prepare_data.py` drops those
 *      sessions.
 * Payment is never made conditional on any of it.
 */
export function Debrief({
  payload,
  trials,
  responses,
}: {
  payload: SessionPayload;
  trials: Trial[];
  responses: TrialResponse[];
}) {
  const [result, setResult] = useState<SubmitResult | null>(null);
  const [sending, setSending] = useState(false);
  const [withdrawn, setWithdrawn] = useState(false);

  const score = scoreSession(trials, responses);

  const send = async (withdraw: boolean) => {
    setSending(true);
    const finalPayload: SessionPayload = {
      ...payload,
      completedAt: new Date().toISOString(),
      survey: { ...payload.survey, withdrawn: withdraw ? 1 : 0 },
    };
    const r = await submit(finalPayload);
    setResult(r);
    setSending(false);
    if (withdraw) setWithdrawn(true);
  };

  return (
    <div className="screen">
      <section className="card">
        <h1 className="card__title">Thank you &mdash; here is what this study was about</h1>

        <h3>What we did not tell you beforehand</h3>
        <p>
          <strong>
            {score.nErrorTrials} of the {score.nTrials} recommendations you saw were
            deliberately wrong.
          </strong>{" "}
          In those cases the option ShopBot recommended did not actually meet one of
          your stated requirements &mdash; because it quietly ignored a requirement,
          misreported a specification, or miscalculated a total price. We planted
          these errors on purpose, and every participant saw the same number of them.
        </p>
        <p>
          ShopBot was not a real AI system. It was a scripted assistant, so that we
          could control exactly how often it was wrong. Its recommendations had
          nothing to do with your choices &mdash; nothing you did caused the errors.
        </p>

        <h3>What we were actually studying</h3>
        <p>
          People are increasingly handing tasks to AI assistants that act on their
          behalf. We want to know what helps people notice when such an assistant is
          wrong. Different participants saw different versions of ShopBot: some saw
          its working and could check its claims against the catalogue, others saw
          only its final answer. Separately, some saw a version that was confident
          and complimentary, others a version that hedged. We are testing whether
          being able to check an assistant&rsquo;s work protects people from being
          swayed by a confident-sounding one.
        </p>

        <h3>How you did</h3>
        <p className="hint">
          For your interest only &mdash; we are studying differences between groups,
          not individuals. Missing planted errors is extremely common and is exactly
          the effect we are investigating.
        </p>
        <ul className="requirements">
          <li>
            You spotted <strong>{score.hits}</strong> of the{" "}
            <strong>{score.nErrorTrials}</strong> flawed recommendations.
          </li>
          <li>
            You changed <strong>{score.falseAlarms}</strong> of the{" "}
            <strong>{score.nTrials - score.nErrorTrials}</strong> recommendations that
            were in fact correct.
          </li>
        </ul>

        <h3>Your data</h3>
        <p>
          Now that you know what was withheld, you can ask us not to use your
          responses. Your payment is not affected either way, and you do not need to
          give a reason.
        </p>

        <h3>Questions</h3>
        <p>
          {STUDY_CONTACT.researcher}, {STUDY_CONTACT.institution} &mdash;{" "}
          {STUDY_CONTACT.email} (ethics reference {STUDY_CONTACT.ethicsRef}).
        </p>

        {!result && (
          <div className="actions">
            <button
              type="button"
              className="btn btn--primary"
              disabled={sending}
              onClick={() => send(false)}
            >
              {sending ? "Submitting..." : "Submit my responses"}
            </button>
            <button
              type="button"
              className="btn btn--ghost"
              disabled={sending}
              onClick={() => send(true)}
            >
              Withdraw my data
            </button>
          </div>
        )}

        {result?.ok && (
          <div className="notice notice--ok">
            <p>
              {withdrawn
                ? "Your data has been marked for deletion and will not be analysed."
                : "Your responses have been recorded. Thank you for taking part."}
            </p>
            {COMPLETION_CODE && (
              <p>
                Your completion code is <strong>{COMPLETION_CODE}</strong>.
              </p>
            )}
            {COMPLETION_URL && (
              <p>
                <a className="btn btn--primary" href={COMPLETION_URL}>
                  Return to Prolific
                </a>
              </p>
            )}
          </div>
        )}

        {result && !result.ok && (
          <div className="notice notice--error">
            <p>
              We could not reach the server ({result.error}). Your responses are saved
              in this browser. Please press retry, or download the file below and send
              it to {STUDY_CONTACT.email} so your participation still counts.
            </p>
            <div className="actions">
              <button
                type="button"
                className="btn btn--primary"
                onClick={() => send(withdrawn)}
              >
                Retry
              </button>
              <button
                type="button"
                className="btn btn--secondary"
                onClick={() => downloadJson(payload)}
              >
                Download my responses
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

export function Excluded() {
  return (
    <div className="screen">
      <section className="card">
        <h1 className="card__title">Thank you for your time</h1>
        <p>
          Unfortunately you are not eligible to continue with this study. You have not
          done anything wrong, and no data from this session will be analysed.
        </p>
        <p>
          If you were recruited through a research platform, please return the study
          there so you are not charged an incomplete submission.
        </p>
      </section>
    </div>
  );
}
