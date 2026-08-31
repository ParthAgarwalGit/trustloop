import { useState } from "react";
import { MAX_COMPREHENSION_ATTEMPTS, STUDY_CONTACT } from "../config";

/**
 * Consent.
 *
 * This is an AUTHORISED-DECEPTION consent: participants are told up front that some
 * information about the study's purpose is withheld and that they will get a full
 * explanation at the end. Most ethics boards require exactly this wording pattern
 * for a study with a concealed manipulation. Have your board approve the final text
 * -- treat what follows as a starting draft, not an approved instrument.
 */
export function Consent({ onConsent }: { onConsent: () => void }) {
  const [checked, setChecked] = useState(false);

  return (
    <div className="screen">
      <section className="card">
        <h1 className="card__title">Information and consent</h1>

        <h3>What is this study?</h3>
        <p>
          You will use an automated shopping assistant called ShopBot. It will make
          product and travel recommendations based on requirements we give you, and
          you will decide whether to accept each recommendation. Afterwards you will
          answer some questions about your experience.
        </p>

        <h3>How long will it take?</h3>
        <p>About 15&ndash;20 minutes.</p>

        <h3>Is anything withheld?</h3>
        <p>
          Yes. To keep your responses natural, we are not describing the full purpose
          of the study in advance, and some details of how ShopBot behaves are not
          disclosed until the end. You will receive a complete explanation on the
          final screen, and you will be able to withdraw your data at that point if
          you would rather we did not use it.
        </p>

        <h3>What data do we collect?</h3>
        <p>
          Your choices, response times, confidence ratings and questionnaire answers,
          plus your platform participant ID for payment. We do not collect your name,
          email address or IP address. Data are stored pseudonymously and reported
          only in aggregate.
        </p>

        <h3>Do I have to take part?</h3>
        <p>
          No. Participation is voluntary and you may close the tab at any point
          without giving a reason. Partial data from an abandoned session is not
          analysed.
        </p>

        <h3>Who can I contact?</h3>
        <p>
          {STUDY_CONTACT.researcher}, {STUDY_CONTACT.institution} &mdash;{" "}
          {STUDY_CONTACT.email}. This study was approved under ethics reference{" "}
          {STUDY_CONTACT.ethicsRef}.
        </p>

        <label className="consent-check">
          <input
            type="checkbox"
            checked={checked}
            onChange={(e) => setChecked(e.target.checked)}
          />
          <span>
            I am 18 or older, I have read the information above, and I agree to take
            part.
          </span>
        </label>

        <div className="actions">
          <button
            type="button"
            className="btn btn--primary"
            disabled={!checked}
            onClick={onConsent}
          >
            Begin
          </button>
        </div>
      </section>
    </div>
  );
}

export function Instructions({ onNext }: { onNext: () => void }) {
  return (
    <div className="screen">
      <section className="card">
        <h1 className="card__title">How this works</h1>
        <p>
          You will see <strong>10 shopping requests</strong>. Each one lists a few
          requirements &mdash; a budget, a minimum rating, a maximum weight, and so
          on.
        </p>
        <p>
          For each request, <strong>ShopBot</strong> searches a product catalogue and
          recommends one option. Your job is to decide whether that recommendation is
          a good one.
        </p>
        <ul className="requirements">
          <li>Read the requirements carefully.</li>
          <li>Look at what ShopBot recommends.</li>
          <li>Rate how confident you are that it meets all the requirements.</li>
          <li>
            Then either <strong>accept</strong> ShopBot&rsquo;s recommendation, or{" "}
            <strong>choose a different option</strong> from the ones it considered.
          </li>
        </ul>
        <p className="hint">
          There is no time limit. Please treat each request as though you were
          shopping for yourself.
        </p>
        <div className="actions">
          <button type="button" className="btn btn--primary" onClick={onNext}>
            Continue
          </button>
        </div>
      </section>
    </div>
  );
}

interface CompQuestion {
  id: string;
  text: string;
  options: string[];
  correct: number;
}

const COMP_QUESTIONS: CompQuestion[] = [
  {
    id: "q1",
    text: "What are you being asked to do on each request?",
    options: [
      "Decide whether ShopBot's recommendation meets the listed requirements",
      "Rate how attractive the product photographs are",
      "Type in your own product search from scratch",
    ],
    correct: 0,
  },
  {
    id: "q2",
    text: "If you think ShopBot's recommendation is not the best option, what can you do?",
    options: [
      "Nothing &mdash; you must accept whatever it recommends",
      "Choose a different option from the ones it considered",
      "Skip the request entirely",
    ],
    correct: 1,
  },
];

/**
 * Comprehension gate. Participants who cannot state the task after
 * MAX_COMPREHENSION_ATTEMPTS tries are screened out rather than contributing noise;
 * the attempt count is logged so the exclusion is auditable.
 */
export function Comprehension({
  onPass,
  onFail,
}: {
  onPass: (attempts: number) => void;
  onFail: (attempts: number) => void;
}) {
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [attempts, setAttempts] = useState(0);
  const [feedback, setFeedback] = useState<string | null>(null);

  const submit = () => {
    const n = attempts + 1;
    setAttempts(n);
    const allCorrect = COMP_QUESTIONS.every((q) => answers[q.id] === q.correct);
    if (allCorrect) {
      onPass(n);
    } else if (n >= MAX_COMPREHENSION_ATTEMPTS) {
      onFail(n);
    } else {
      setFeedback(
        `Not quite. Please re-read the instructions above and try again. ` +
          `Attempt ${n} of ${MAX_COMPREHENSION_ATTEMPTS}.`,
      );
    }
  };

  const complete = COMP_QUESTIONS.every((q) => answers[q.id] !== undefined);

  return (
    <div className="screen">
      <section className="card">
        <h1 className="card__title">Quick check</h1>
        <p className="hint">
          Two short questions to confirm the instructions were clear.
        </p>
        <div className="survey">
          {COMP_QUESTIONS.map((q) => (
            <div key={q.id} className="survey__item">
              <p className="survey__text">{q.text}</p>
              <div className="choices">
                {q.options.map((opt, i) => (
                  <button
                    key={i}
                    type="button"
                    className={`choice${answers[q.id] === i ? " is-selected" : ""}`}
                    onClick={() => setAnswers((a) => ({ ...a, [q.id]: i }))}
                    dangerouslySetInnerHTML={{ __html: opt }}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
        {feedback && <p className="error">{feedback}</p>}
        <div className="actions">
          <button
            type="button"
            className="btn btn--primary"
            disabled={!complete}
            onClick={submit}
          >
            Check my answers
          </button>
        </div>
      </section>
    </div>
  );
}
