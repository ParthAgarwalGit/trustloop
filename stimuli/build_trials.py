#!/usr/bin/env python3
"""
Build the app's stimulus JSON from the spec modules.

Ground truth is COMPUTED here, never copied from the spec. If the spec claims a
trial is clean but the recommended item actually violates a constraint (or vice
versa), the build fails loudly rather than shipping a mislabelled trial.

Usage:
    python stimuli/build_trials.py
Outputs:
    app/src/data/catalog.json   the item catalogue
    app/src/data/sources.json   the simulated web (retailer, review site, forum)
    app/src/data/trials.json    trials + long-form agent responses + ground truth
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "stimuli" / "spec"))

import response_spec  # noqa: E402
import sources_spec as src  # noqa: E402
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

# Fields the agent may mention as colour beyond the participant's stated
# requirements. Real agents volunteer information you did not ask for, and that
# noise is what stops the disputed figure standing out.
NOISE_FIELDS = {
    "laptop": ["screen_in", "rating", "storage_gb", "battery_hours"],
    "trip": ["hotel_rating", "stops", "refundable", "nights"],
}
PRICE_FIELD = {"laptop": "price", "trip": "total_price"}


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


def build_trial(trial: dict) -> dict:
    item = spec.CATALOG[trial["recommend"]]
    constraints = trial["constraints"]
    domain = trial["domain"]
    err = trial.get("error_spec")
    etype = err["type"] if err else None

    # --- ground truth, computed ------------------------------------------------
    violated = violated_constraints(item, constraints)
    is_error_actual = len(violated) > 0

    if (err is not None) != is_error_actual:
        raise BuildError(
            f"trial {trial['id']} (slot {trial['slot']}): spec declares "
            f"error_spec={etype!r} but the recommended item {item['id']} "
            f"{'violates' if is_error_actual else 'satisfies'} all constraints "
            f"(violated={violated}). Fix the catalogue, the constraints, or the pick."
        )

    candidates = [spec.CATALOG[cid] for cid in trial["candidates"]]
    compliant = [ci["id"] for ci in candidates if not violated_constraints(ci, constraints)]

    if trial["recommend"] not in trial["candidates"]:
        raise BuildError(f"trial {trial['id']}: recommended item not in candidate set")
    if not compliant:
        raise BuildError(
            f"trial {trial['id']}: no fully compliant option exists in the candidate "
            f"set, so 'override' can never be correct (violates invariant I4)"
        )
    if err and trial["recommend"] in compliant:
        raise BuildError(f"trial {trial['id']}: error trial but the pick is compliant")
    if not err and trial["recommend"] not in compliant:
        raise BuildError(f"trial {trial['id']}: clean trial but the pick is non-compliant")

    # --- what the agent asserts -------------------------------------------------
    dropped_fields: set[str] = set()
    if etype == "dropped_constraint":
        dropped_fields = {
            c["field"] for c in constraints if c["id"] in violated
        }

    def stated_value_for(item_id: str, field: str):
        """(value, is_false) -- what the agent asserts about this item's field."""
        truth = spec.CATALOG[item_id][field]
        if item_id != trial["recommend"] or not err:
            return truth, False
        if etype == "false_claim" and field == err["field"]:
            return err["stated"], True
        if etype == "arithmetic" and field == "total_price":
            return err["stated_total"], True
        return truth, False

    def mentioned_fields_for(item_id: str) -> list[str]:
        """
        Which fields the agent talks about for this item.

        Constraint fields come first (that is what the participant cares about),
        then noise. A dropped constraint's field is absent entirely -- that absence
        IS the error, and it has to be genuinely absent everywhere in the response.
        """
        price_field = PRICE_FIELD[domain]
        fields = [price_field]
        for c in constraints:
            if c["field"] in dropped_fields:
                continue
            if c["field"] not in fields:
                fields.append(c["field"])
        for nf in NOISE_FIELDS[domain]:
            if len(fields) >= 5:
                break
            if nf not in fields and nf not in dropped_fields and nf in spec.CATALOG[item_id]:
                fields.append(nf)
        return fields

    cited_items = [trial["recommend"]] + [c for c in trial["candidates"] if c != trial["recommend"]]
    tool_calls = response_spec.build_tool_calls(trial, spec.CATALOG, cited_items)
    response = response_spec.build_response(
        trial, spec.CATALOG, fmt_value, stated_value_for, mentioned_fields_for
    )

    # --- machine-readable record of every assertion -----------------------------
    # Not rendered to participants. Analysis needs to know which fact was disputed
    # and which page carries the truth, so it can ask whether a participant ever
    # opened the page that would have exposed the error.
    stated_facts = []
    for field in mentioned_fields_for(trial["recommend"]):
        value, is_false = stated_value_for(trial["recommend"], field)
        truth = item[field]
        constraint_id = next((c["id"] for c in constraints if c["field"] == field), None)
        stated_facts.append({
            "itemId": item["id"],
            "field": field,
            "statedValue": value,
            "statedValueText": fmt_value(field, value),
            "catalogValue": truth,
            "catalogValueText": fmt_value(field, truth),
            "isFalse": is_false,
            "constraintId": constraint_id,
            "sourceUrl": src.shop_url(item),
        })

    # The single fact that determines the trial's correctness, and where it lives.
    disputed = None
    if err:
        if etype == "dropped_constraint":
            vc = next(c for c in constraints if c["id"] in violated)
            disputed = {
                "kind": "omission",
                "field": vc["field"],
                "constraintId": vc["id"],
                "catalogValue": item[vc["field"]],
                "catalogValueText": fmt_value(vc["field"], item[vc["field"]]),
                "sourceUrl": src.shop_url(item),
            }
        else:
            field = err["field"] if etype == "false_claim" else "total_price"
            value, _ = stated_value_for(trial["recommend"], field)
            disputed = {
                "kind": "contradiction",
                "field": field,
                "constraintId": next(
                    (c["id"] for c in constraints if c["field"] == field), None
                ),
                "statedValue": value,
                "statedValueText": fmt_value(field, value),
                "catalogValue": item[field],
                "catalogValueText": fmt_value(field, item[field]),
                "sourceUrl": src.shop_url(item),
            }

    # --- self-consistency guard -------------------------------------------------
    # Whatever the agent states must, on its own numbers, appear to satisfy every
    # requirement it addresses. An agent that visibly contradicts itself would be
    # caught for the wrong reason.
    for fact in stated_facts:
        if fact["constraintId"] is None:
            continue
        con = next(c for c in constraints if c["id"] == fact["constraintId"])
        if not OPS[con["op"]](fact["statedValue"], con["value"]):
            raise BuildError(
                f"trial {trial['id']}: agent states {fact['field']}="
                f"{fact['statedValueText']} which fails its own constraint "
                f"{con['id']} ({con['label']}) -- self-contradictory response"
            )

    addressed = {f["constraintId"] for f in stated_facts if f["constraintId"]}
    expected = {c["id"] for c in constraints}
    if etype == "dropped_constraint":
        if addressed != expected - set(violated):
            raise BuildError(
                f"trial {trial['id']}: dropped-constraint trial addresses {addressed}, "
                f"expected {expected - set(violated)}"
            )
    elif addressed != expected:
        raise BuildError(
            f"trial {trial['id']}: response addresses {addressed} but the "
            f"requirements are {expected}"
        )

    return {
        "id": trial["id"],
        "slot": trial["slot"],
        "domain": domain,
        "prompt": trial["prompt"],
        "constraints": constraints,
        "candidateIds": trial["candidates"],
        "recommendedId": trial["recommend"],
        "specCardFields": spec.SPEC_CARD_FIELDS[domain],
        # --- ground truth (never rendered; scoring only) ----------------------
        "isErrorTrial": is_error_actual,
        "errorType": etype,
        "violatedConstraintIds": violated,
        "compliantCandidateIds": compliant,
        "statedFacts": stated_facts,
        "disputedFact": disputed,
        # --- agent output ------------------------------------------------------
        "toolCalls": tool_calls,
        "response": response,
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

    (OUT_DIR / "catalog.json").write_text(
        json.dumps({
            "fieldMeta": spec.FIELD_META,
            "specCardFields": spec.SPEC_CARD_FIELDS,
            "items": spec.CATALOG,
        }, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (OUT_DIR / "sources.json").write_text(
        json.dumps({
            "domains": {
                "shop": src.SHOP_DOMAIN, "review": src.REVIEW_DOMAIN,
                "forum": src.FORUM_DOMAIN,
            },
            "siteNames": {
                "shop": src.SHOP_NAME, "review": src.REVIEW_NAME,
                "forum": src.FORUM_NAME,
            },
            "pages": src.build_sources(spec.CATALOG),
        }, indent=2),
        encoding="utf-8",
    )
    (OUT_DIR / "trials.json").write_text(
        json.dumps({"errorSlots": spec.ERROR_SLOTS, "trials": trials}, indent=2),
        encoding="utf-8",
    )

    total_words = sum(
        len(b.get("text", "").split()) for t in trials for b in t["response"]["blocks"]
    )
    print(f"Built {len(trials)} trials -> {OUT_DIR}")
    print(f"  catalog items:    {len(spec.CATALOG)}")
    print(f"  source pages:     {len(spec.CATALOG) * 3}")
    print(f"  error slots:      {actual_error_slots}")
    print(f"  mean response:    {total_words // len(trials)} words")
    for t in trials:
        flag = f"ERROR[{t['errorType']}]" if t["isErrorTrial"] else "clean"
        words = sum(len(b.get("text", "").split()) for b in t["response"]["blocks"])
        print(
            f"  slot {t['slot']:>2}  {t['id']}  {t['domain']:<6} "
            f"rec={t['recommendedId']:<4} {flag:<26} "
            f"{words:>3}w  {len(t['response']['citations'])} cites"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
