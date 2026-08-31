import { useMemo, useState } from "react";
import { SURVEY, type SurveyItem } from "../data/survey";
import type { SurveyResponses } from "../types";

/**
 * The post-session questionnaire, rendered one block per page.
 *
 * Block order is fixed rather than randomised: the manipulation checks and the
 * "did you notice anything" probe sit at the end on purpose, so that asking about
 * transparency or tone cannot prime the trust and authenticity ratings that precede
 * them (funnel debriefing order).
 */
export function Survey({ onDone }: { onDone: (r: SurveyResponses) => void }) {
  const [blockIndex, setBlockIndex] = useState(0);
  const [responses, setResponses] = useState<SurveyResponses>({});
  const [showErrors, setShowErrors] = useState(false);

  const block = SURVEY[blockIndex];
  const isLast = blockIndex === SURVEY.length - 1;

  const missing = useMemo(
    () => block.items.filter((i) => i.required && responses[i.id] === undefined),
    [block, responses],
  );

  const set = (id: string, value: number | string) =>
    setResponses((prev) => ({ ...prev, [id]: value }));

  const next = () => {
    if (missing.length > 0) {
      setShowErrors(true);
      return;
    }
    setShowErrors(false);
    if (isLast) {
      onDone(responses);
    } else {
      setBlockIndex((i) => i + 1);
      window.scrollTo({ top: 0 });
    }
  };

  return (
    <div className="screen">
      <div className="progress">
        <div
          className="progress__bar"
          style={{ width: `${(blockIndex / SURVEY.length) * 100}%` }}
        />
      </div>
      <p className="progress__label">
        Questionnaire {blockIndex + 1} of {SURVEY.length}
      </p>

      <section className="card">
        <h2 className="card__title">{block.title}</h2>
        {block.intro && <p className="hint">{block.intro}</p>}

        <div className="survey">
          {block.items.map((item) => (
            <Item
              key={item.id}
              item={item}
              value={responses[item.id]}
              invalid={
                showErrors && !!item.required && responses[item.id] === undefined
              }
              onChange={(v) => set(item.id, v)}
            />
          ))}
        </div>

        {showErrors && missing.length > 0 && (
          <p className="error">
            Please answer {missing.length} remaining{" "}
            {missing.length === 1 ? "question" : "questions"} before continuing.
          </p>
        )}

        <div className="actions">
          <button type="button" className="btn btn--primary" onClick={next}>
            {isLast ? "Finish" : "Continue"}
          </button>
        </div>
      </section>
    </div>
  );
}

function Item({
  item,
  value,
  invalid,
  onChange,
}: {
  item: SurveyItem;
  value: number | string | undefined;
  invalid: boolean;
  onChange: (v: number | string) => void;
}) {
  return (
    <div className={`survey__item${invalid ? " is-invalid" : ""}`}>
      <p className="survey__text">{item.text}</p>
      {renderControl(item, value, onChange)}
    </div>
  );
}

function renderControl(
  item: SurveyItem,
  value: number | string | undefined,
  onChange: (v: number | string) => void,
) {
  switch (item.kind) {
    case "likert7":
    case "likert5": {
      const n = item.kind === "likert7" ? 7 : 5;
      return (
        <div className="scale">
          {item.anchors && <span className="scale__anchor">{item.anchors[0]}</span>}
          <div className="scale__options" role="radiogroup" aria-label={item.text}>
            {Array.from({ length: n }, (_, i) => i + 1).map((v) => (
              <button
                key={v}
                type="button"
                role="radio"
                aria-checked={value === v}
                className={`scale__option${value === v ? " is-selected" : ""}`}
                onClick={() => onChange(v)}
              >
                {v}
              </button>
            ))}
          </div>
          {item.anchors && <span className="scale__anchor">{item.anchors[1]}</span>}
        </div>
      );
    }

    case "tlx":
      return (
        <div className="tlx">
          <span className="scale__anchor">{item.anchors?.[0]}</span>
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={typeof value === "number" ? value : 50}
            onChange={(e) => onChange(Number(e.target.value))}
            className="tlx__slider"
          />
          <span className="scale__anchor">{item.anchors?.[1]}</span>
          <output className="tlx__value">
            {typeof value === "number" ? value : "--"}
          </output>
        </div>
      );

    case "select":
      return (
        <select
          className="input"
          value={typeof value === "string" ? value : ""}
          onChange={(e) => onChange(e.target.value)}
        >
          <option value="" disabled>
            Select an option
          </option>
          {item.options?.map((o) => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
        </select>
      );

    case "number":
      return (
        <input
          type="number"
          className="input input--narrow"
          min={18}
          max={120}
          value={typeof value === "number" ? value : ""}
          onChange={(e) =>
            onChange(e.target.value === "" ? "" : Number(e.target.value))
          }
        />
      );

    case "text":
      return (
        <textarea
          className="input"
          rows={3}
          value={typeof value === "string" ? value : ""}
          onChange={(e) => onChange(e.target.value)}
        />
      );
  }
}
