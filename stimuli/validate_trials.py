#!/usr/bin/env python3
"""
Validate the built stimuli against the study's design invariants.

Run after ANY edit to the spec modules, and in CI. A failure here means the
experiment would produce uninterpretable data -- these are internal-validity
checks, not style checks.

Usage:
    python stimuli/build_trials.py && python stimuli/validate_trials.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "app" / "src" / "data"
TONE_TS = ROOT / "app" / "src" / "lib" / "tone.ts"

failures: list[str] = []
checks_run = 0


def check(condition: bool, message: str) -> None:
    global checks_run
    checks_run += 1
    if not condition:
        failures.append(message)


def response_text(trial: dict) -> str:
    return " ".join(b.get("text", "") for b in trial["response"]["blocks"])


def main() -> int:
    trials_doc = json.loads((DATA / "trials.json").read_text(encoding="utf-8"))
    catalog = json.loads((DATA / "catalog.json").read_text(encoding="utf-8"))
    sources = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    trials = trials_doc["trials"]
    items = catalog["items"]
    pages = sources["pages"]

    # -- I1: ground truth present and coherent -------------------------------
    for t in trials:
        sid = f"{t['id']} (slot {t['slot']})"
        check(
            t["isErrorTrial"] == (len(t["violatedConstraintIds"]) > 0),
            f"{sid}: isErrorTrial disagrees with violatedConstraintIds",
        )
        check(
            (t["errorType"] is not None) == t["isErrorTrial"],
            f"{sid}: errorType and isErrorTrial disagree",
        )
        check(
            (t["disputedFact"] is not None) == t["isErrorTrial"],
            f"{sid}: disputedFact present iff isErrorTrial must hold",
        )
        check(
            t["recommendedId"] in t["candidateIds"],
            f"{sid}: recommended item is not among the candidates",
        )
        check(
            len(t["compliantCandidateIds"]) > 0,
            f"{sid}: no compliant alternative exists (invariant I4)",
        )
        if t["isErrorTrial"]:
            check(
                t["recommendedId"] not in t["compliantCandidateIds"],
                f"{sid}: error trial but recommendation is compliant",
            )
        else:
            check(
                t["recommendedId"] in t["compliantCandidateIds"],
                f"{sid}: clean trial but recommendation is non-compliant",
            )

    # -- error count / placement ---------------------------------------------
    error_slots = [t["slot"] for t in trials if t["isErrorTrial"]]
    check(error_slots == trials_doc["errorSlots"],
          f"error slots {error_slots} != declared {trials_doc['errorSlots']}")
    check(all(s > 3 for s in error_slots),
          f"an error trial appears in the first 3 slots ({error_slots})")
    check(max(error_slots) < len(trials),
          "an error trial is in the final slot; end-of-task effects confound it")
    check(len(error_slots) >= 3,
          f"only {len(error_slots)} error trials: too few for a stable rate")

    etypes = {t["errorType"] for t in trials if t["isErrorTrial"]}
    check(len(etypes) >= 2,
          f"all seeded errors are the same type ({etypes})")

    # -- I3: every asserted fact is checkable against a real source page ------
    for t in trials:
        sid = f"{t['id']} (slot {t['slot']})"
        rec = items[t["recommendedId"]]
        for f in t["statedFacts"]:
            check(f["field"] in rec,
                  f"{sid}: stated fact references field '{f['field']}' absent from the item")
            check(f["catalogValue"] == rec[f["field"]],
                  f"{sid}: stated fact catalogValue for '{f['field']}' != the catalogue")
            check(f["isFalse"] == (f["statedValue"] != f["catalogValue"]),
                  f"{sid}: isFalse flag disagrees with stated vs catalogue value")

    # -- the agent must always look self-consistent ---------------------------
    for t in trials:
        sid = f"{t['id']} (slot {t['slot']})"
        by_id = {c["id"]: c for c in t["constraints"]}
        for f in t["statedFacts"]:
            if not f["constraintId"]:
                continue
            con = by_id[f["constraintId"]]
            ops = {
                "lt": lambda a, b: a < b, "lte": lambda a, b: a <= b,
                "gt": lambda a, b: a > b, "gte": lambda a, b: a >= b,
                "eq": lambda a, b: a == b, "neq": lambda a, b: a != b,
            }
            check(ops[con["op"]](f["statedValue"], con["value"]),
                  f"{sid}: agent states {f['field']}={f['statedValueText']} which "
                  f"fails its own constraint {con['id']} -- self-contradictory")

    # -- the disputed fact must be REACHABLE ----------------------------------
    # If the agent never links to the page carrying the truth, verifying would mean
    # guessing a URL. The full-disclosure condition must always offer a route to it.
    for t in trials:
        if not t["isErrorTrial"]:
            continue
        sid = f"{t['id']} (slot {t['slot']})"
        d = t["disputedFact"]
        cited = {c["url"].split("#")[0] for c in t["response"]["citations"]}
        check(d["sourceUrl"].split("#")[0] in cited,
              f"{sid}: the page carrying the disputed fact ({d['sourceUrl']}) is "
              "never cited, so the error cannot be verified from the response")

    # -- a dropped constraint must be dropped EVERYWHERE ----------------------
    # The whole error is an absence. If the field resurfaces anywhere in the prose
    # -- even as colour about another candidate -- the omission is no longer the
    # thing being detected.
    for t in trials:
        if t["errorType"] != "dropped_constraint":
            continue
        sid = f"{t['id']} (slot {t['slot']})"
        d = t["disputedFact"]
        meta = catalog["fieldMeta"].get(d["field"], {})
        label = meta.get("label", d["field"])
        text = response_text(t).lower()
        check(label.lower() not in text,
              f"{sid}: dropped constraint's field label '{label}' still appears in "
              "the response text; the omission is not clean")
        check(not any(f["field"] == d["field"] for f in t["statedFacts"]),
              f"{sid}: dropped constraint's field is still in statedFacts")

    # -- a false claim must not be contradicted by the agent itself -----------
    # Scoped to the text that describes the RECOMMENDED item. The same figure
    # appearing for a different product is not a contradiction -- an agent saying
    # "the Kestrel has 16 GB" and "the Nimbus has 8 GB" is perfectly coherent, and
    # rejecting that would forbid ever mentioning a competing spec.
    for t in trials:
        if t["errorType"] not in ("false_claim", "arithmetic"):
            continue
        sid = f"{t['id']} (slot {t['slot']})"
        d = t["disputedFact"]
        rec_name = items[t["recommendedId"]]["name"]
        own_text = " ".join(
            b.get("text", "")
            for b in t["response"]["blocks"]
            if b["type"] != "candidate" or b.get("name") == rec_name
        )
        truth = d["catalogValueText"]
        check(truth not in own_text,
              f"{sid}: the text describing {rec_name} states the TRUE value ({truth}) "
              f"as well as the false one ({d['statedValueText']}) -- self-contradictory")

    # -- citations resolve to real pages --------------------------------------
    for t in trials:
        sid = f"{t['id']} (slot {t['slot']})"
        for c in t["response"]["citations"]:
            check(c["itemId"] in pages,
                  f"{sid}: citation [{c['n']}] references unknown item {c['itemId']}")
            if c["itemId"] in pages:
                check(c["sourceType"] in pages[c["itemId"]],
                      f"{sid}: citation [{c['n']}] references missing source type "
                      f"'{c['sourceType']}'")
        markers = {int(m) for m in re.findall(r"\[(\d+)\]", response_text(t))}
        declared = {c["n"] for c in t["response"]["citations"]}
        check(markers <= declared,
              f"{sid}: response text cites {sorted(markers - declared)} which are "
              "not in the citation list")

    # -- responses must be long enough to require real effort -----------------
    for t in trials:
        sid = f"{t['id']} (slot {t['slot']})"
        words = len(response_text(t).split())
        check(words >= 200,
              f"{sid}: response is only {words} words; too short to be realistic "
              "or to make verification a real choice")

    # -- every source page exists for every catalogue item --------------------
    for iid in items:
        for stype in ("shop", "review", "forum"):
            check(stype in pages.get(iid, {}),
                  f"catalogue item {iid} has no '{stype}' source page")

    # -- I2: tone must not depend on ground truth -----------------------------
    if TONE_TS.exists():
        tone_src = TONE_TS.read_text(encoding="utf-8")
        code = "\n".join(
            line for line in tone_src.splitlines()
            if not line.strip().startswith(("//", "*", "/*"))
        )
        forbidden = [
            "isErrorTrial", "errorType", "violatedConstraintIds",
            "compliantCandidateIds", "isFalse", "disputedFact", "statedFacts",
        ]
        for token in forbidden:
            check(not re.search(rf"\b{token}\b", code),
                  f"tone.ts references ground-truth field '{token}': tone would leak "
                  "correctness and confound the Tone manipulation (invariant I2)")
    else:
        check(False, f"expected tone module at {TONE_TS} (invariant I2 unenforced)")

    # -- report ---------------------------------------------------------------
    if failures:
        print(f"VALIDATION FAILED ({len(failures)} of {checks_run} checks)\n",
              file=sys.stderr)
        for f in failures:
            print(f"  x {f}", file=sys.stderr)
        return 1

    n_err = len(error_slots)
    words = [len(response_text(t).split()) for t in trials]
    print(f"VALIDATION PASSED ({checks_run} checks)")
    print(f"  {len(trials)} trials, {n_err} seeded errors at slots {error_slots}")
    print(f"  error types:   {sorted(e for e in etypes)}")
    print(f"  base rate:     {n_err}/{len(trials)} = {n_err / len(trials):.0%}")
    print(f"  response len:  {min(words)}-{max(words)} words "
          f"(mean {sum(words) // len(words)})")
    print(f"  source pages:  {len(items) * 3}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
