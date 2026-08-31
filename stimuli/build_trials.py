#!/usr/bin/env python3
"""
Build the app's stimulus JSON from `stimuli/spec/trials_spec.py`.

Ground truth is COMPUTED here, never copied from the spec. If the spec claims a
trial is clean but the recommended item actually violates a constraint (or vice
versa), the build fails loudly rather than shipping a mislabelled trial.

Usage:
    python stimuli/build_trials.py
Outputs:
    app/src/data/catalog.json
    app/src/data/trials.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "stimuli" / "spec"))

import trials_spec as spec  # noqa: E402

OUT_DIR = ROOT / "app" / "src" / "data"

OPS = {
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "eq": lambda a, b: a == b,
    "neq": lambda a, b: a != b,
}

OP_TEXT = {
    "lt": "under", "lte": "at most", "gt": "over",
    "gte": "at least", "eq": "exactly", "neq": "not",
}


class BuildError(Exception):
    pass


def fmt_value(field: str, value) -> str:
    meta = spec.FIELD_META.get(field, {"unit": "", "kind": "number"})
    if meta["kind"] == "bool":
        return "Yes" if value else "No"
    if meta["kind"] == "currency":
        return f"${value:,.0f}"
    unit = meta["unit"]
    if isinstance(value, float) and value != int(value):
        return f"{value:g}{unit}"
    return f"{int(value) if isinstance(value, (int, float)) else value}{unit}"


def satisfies(item: dict, constraint: dict) -> bool:
    field = constraint["field"]
    if field not in item:
        raise BuildError(
            f"item {item['id']} ({item['domain']}) has no field '{field}' "
            f"required by constraint {constraint['id']}"
        )
    return OPS[constraint["op"]](item[field], constraint["value"])


def violated_constraints(item: dict, constraints: list[dict]) -> list[str]:
    return [c["id"] for c in constraints if not satisfies(item, c)]


def build_claims(trial: dict, item: dict) -> list[dict]:
    """
    One claim per constraint, describing what the agent ASSERTS about the item.

    `catalogValue` is always the truth. `statedValue` is what the agent says.
    They diverge only for a `false_claim` / `arithmetic` error. A
    `dropped_constraint` error instead omits the claim entirely (`omitted` list).
    """
    err = trial.get("error_spec") or {}
    etype = err.get("type")
    claims = []

    for con in trial["constraints"]:
        field = con["field"]
        truth = item[field]
        stated = truth
        is_false = False

        if etype == "false_claim" and field == err["field"]:
            stated = err["stated"]
            is_false = True
        elif etype == "arithmetic" and field == "total_price":
            stated = err["stated_total"]
            is_false = True

        # Whether the agent's ASSERTION would satisfy the constraint (what a
        # participant who trusts the agent's numbers would conclude)...
        stated_satisfies = OPS[con["op"]](stated, con["value"])
        # ...versus whether the item ACTUALLY satisfies it.
        truly_satisfies = OPS[con["op"]](truth, con["value"])

        claims.append({
            "constraintId": con["id"],
            "field": field,
            "fieldLabel": spec.FIELD_META[field]["label"],
            "constraintLabel": con["label"],
            "statedValue": stated,
            "statedValueText": fmt_value(field, stated),
            "catalogValue": truth,
            "catalogValueText": fmt_value(field, truth),
            "statedSatisfies": stated_satisfies,
            "trulySatisfies": truly_satisfies,
            "isFalseClaim": is_false,
        })

    return claims


def agent_view_pass_ids(trial: dict, shown_constraints: list[dict]) -> list[str]:
    """
    Which candidates pass the filter *as the agent believes it applied it*.

    This is deliberately NOT the true compliant set. On an error trial the agent's
    trace must be internally consistent with its own mistake, otherwise the
    inconsistency (e.g. "3 options passed" followed by recommending a 4th) becomes
    an unintended detection cue that differs between clean and error trials.

    The agent's view differs from reality only for the recommended item, and only
    on the falsified field.
    """
    err = trial.get("error_spec") or {}
    etype = err.get("type")
    rec_id = trial["recommend"]

    passing = []
    for cid in trial["candidates"]:
        item = dict(spec.CATALOG[cid])
        if cid == rec_id:
            if etype == "false_claim":
                item[err["field"]] = err["stated"]
            elif etype == "arithmetic":
                item["total_price"] = err["stated_total"]
        if all(satisfies(item, con) for con in shown_constraints):
            passing.append(cid)
    return passing


def build_steps(trial: dict, item: dict, pool_size: int) -> list[dict]:
    """
    The agent's process trace. Shown ONLY in the `full` disclosure condition.
    Purely factual: tone is applied client-side (see app/src/lib/tone.ts) so that
    the honest/sycophantic manipulation cannot leak ground truth.
    """
    err = trial.get("error_spec") or {}
    shown = [c for c in trial["constraints"]]
    if err.get("type") == "dropped_constraint":
        dropped = set(violated_constraints(item, trial["constraints"]))
        shown = [c for c in trial["constraints"] if c["id"] not in dropped]

    n_pass = len(agent_view_pass_ids(trial, shown))
    if trial["recommend"] not in agent_view_pass_ids(trial, shown):
        raise BuildError(
            f"trial {trial['id']}: the agent recommends {trial['recommend']} but that "
            f"item does not pass even the agent's own (possibly erroneous) filter, so "
            f"the process trace would be self-contradictory"
        )

    # Labels are used verbatim: lowercasing mangles acronyms ("512 GB+" -> "512 gb+").
    filter_text = ", ".join(c["label"] for c in shown)
    return [
        {"n": 1, "action": "Search",
         "detail": f"Retrieved {pool_size} candidate options from the catalog."},
        {"n": 2, "action": "Filter",
         "detail": f"Applied your requirements: {filter_text}."},
        {"n": 3, "action": "Compare",
         "detail": f"{n_pass} option(s) passed the filter; compared them on price and rating."},
        {"n": 4, "action": "Recommend",
         "detail": f"Selected {item['name']} as the best overall match."},
    ]


def build_trial(trial: dict) -> dict:
    item = spec.CATALOG[trial["recommend"]]
    constraints = trial["constraints"]

    # --- ground truth, computed ------------------------------------------------
    violated = violated_constraints(item, constraints)
    is_error_actual = len(violated) > 0

    err = trial.get("error_spec")
    etype = err["type"] if err else None

    # An arithmetic error can make a pick non-compliant on total_price; a false_claim
    # likewise. Both are already captured by `violated`. Cross-check against the spec.
    declared_error = err is not None
    if declared_error != is_error_actual:
        raise BuildError(
            f"trial {trial['id']} (slot {trial['slot']}): spec declares "
            f"error_spec={etype!r} but the recommended item {item['id']} "
            f"{'violates' if is_error_actual else 'satisfies'} all constraints "
            f"(violated={violated}). Fix the catalog, the constraints, or the pick."
        )

    # --- candidate set ---------------------------------------------------------
    candidates = [spec.CATALOG[cid] for cid in trial["candidates"]]
    compliant = [ci["id"] for ci in candidates if not violated_constraints(ci, constraints)]

    if trial["recommend"] not in trial["candidates"]:
        raise BuildError(f"trial {trial['id']}: recommended item not in candidate set")
    if not compliant:
        raise BuildError(
            f"trial {trial['id']}: no fully compliant option exists in the candidate "
            f"set, so 'override' can never be correct (violates invariant I4)"
        )
    if declared_error and trial["recommend"] in compliant:
        raise BuildError(f"trial {trial['id']}: error trial but the pick is compliant")
    if not declared_error and trial["recommend"] not in compliant:
        raise BuildError(f"trial {trial['id']}: clean trial but the pick is non-compliant")

    claims = build_claims(trial, item)
    steps = build_steps(trial, item, len(candidates))

    omitted = []
    if etype == "dropped_constraint":
        omitted = violated
        claims = [c for c in claims if c["constraintId"] not in omitted]

    return {
        "id": trial["id"],
        "slot": trial["slot"],
        "domain": trial["domain"],
        "prompt": trial["prompt"],
        "constraints": constraints,
        "candidateIds": trial["candidates"],
        "recommendedId": trial["recommend"],
        "specCardFields": spec.SPEC_CARD_FIELDS[trial["domain"]],
        # --- ground truth (never shown to participants; used for scoring) ------
        "isErrorTrial": is_error_actual,
        "errorType": etype,
        "violatedConstraintIds": violated,
        "compliantCandidateIds": compliant,
        # --- agent output ------------------------------------------------------
        "agentSteps": steps,
        "agentClaims": claims,
        "omittedConstraintIds": omitted,
    }


def main() -> int:
    try:
        trials = [build_trial(t) for t in sorted(spec.TRIALS, key=lambda t: t["slot"])]
    except BuildError as e:
        print(f"BUILD FAILED: {e}", file=sys.stderr)
        return 1

    slots = [t["slot"] for t in trials]
    if slots != list(range(1, len(trials) + 1)):
        print(f"BUILD FAILED: slots must be 1..N with no gaps, got {slots}", file=sys.stderr)
        return 1

    actual_error_slots = [t["slot"] for t in trials if t["isErrorTrial"]]
    if actual_error_slots != spec.ERROR_SLOTS:
        print(
            f"BUILD FAILED: computed error slots {actual_error_slots} != "
            f"declared ERROR_SLOTS {spec.ERROR_SLOTS}",
            file=sys.stderr,
        )
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    catalog_out = {
        "fieldMeta": spec.FIELD_META,
        "specCardFields": spec.SPEC_CARD_FIELDS,
        "items": spec.CATALOG,
    }
    (OUT_DIR / "catalog.json").write_text(
        json.dumps(catalog_out, indent=2, sort_keys=True), encoding="utf-8"
    )
    (OUT_DIR / "trials.json").write_text(
        json.dumps({"errorSlots": spec.ERROR_SLOTS, "trials": trials}, indent=2),
        encoding="utf-8",
    )

    print(f"Built {len(trials)} trials -> {OUT_DIR}")
    print(f"  catalog items: {len(spec.CATALOG)}")
    print(f"  error slots:   {actual_error_slots}")
    for t in trials:
        flag = f"ERROR[{t['errorType']}]" if t["isErrorTrial"] else "clean"
        print(
            f"  slot {t['slot']:>2}  {t['id']}  {t['domain']:<6} "
            f"rec={t['recommendedId']:<4} {flag:<26} "
            f"compliant={t['compliantCandidateIds']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
