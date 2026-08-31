#!/usr/bin/env python3
"""
Validate the built stimuli against the study's design invariants.

Run this after ANY edit to `stimuli/spec/trials_spec.py`, and in CI. A failure here
means the experiment would produce uninterpretable data -- these are not style
checks, they are internal-validity checks.

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


def main() -> int:
    trials_doc = json.loads((DATA / "trials.json").read_text(encoding="utf-8"))
    catalog = json.loads((DATA / "catalog.json").read_text(encoding="utf-8"))
    trials = trials_doc["trials"]
    items = catalog["items"]

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
            t["recommendedId"] in t["candidateIds"],
            f"{sid}: recommended item is not among the candidates",
        )
        # I4: override must always be a rational option
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
    check(
        error_slots == trials_doc["errorSlots"],
        f"error slots {error_slots} != declared {trials_doc['errorSlots']}",
    )
    check(
        all(s > 3 for s in error_slots),
        f"an error trial appears in the first 3 slots ({error_slots}); "
        "early errors contaminate the learning phase",
    )
    check(
        max(error_slots) < len(trials),
        "an error trial is in the final slot; end-of-task effects confound it",
    )
    check(
        len(error_slots) >= 3,
        f"only {len(error_slots)} error trials: too few for a stable per-participant "
        "detection rate",
    )

    # -- error types are varied ----------------------------------------------
    etypes = {t["errorType"] for t in trials if t["isErrorTrial"]}
    check(
        len(etypes) >= 2,
        f"all seeded errors are the same type ({etypes}); results would not "
        "generalise beyond that single failure mode",
    )

    # -- I3: every claim is checkable against the catalog ---------------------
    for t in trials:
        sid = f"{t['id']} (slot {t['slot']})"
        rec = items[t["recommendedId"]]
        for cl in t["agentClaims"]:
            check(
                cl["field"] in rec,
                f"{sid}: claim references field '{cl['field']}' absent from the item",
            )
            check(
                cl["catalogValue"] == rec[cl["field"]],
                f"{sid}: claim catalogValue for '{cl['field']}' does not match the catalog",
            )
            check(
                cl["isFalseClaim"] == (cl["statedValue"] != cl["catalogValue"]),
                f"{sid}: isFalseClaim flag disagrees with stated vs catalog value",
            )

    # -- the agent must always look self-consistent ---------------------------
    # Every claim the agent actually makes must, on its own stated numbers, appear
    # to satisfy its constraint. An agent that visibly contradicts itself would be
    # detected for the wrong reason.
    for t in trials:
        sid = f"{t['id']} (slot {t['slot']})"
        for cl in t["agentClaims"]:
            check(
                cl["statedSatisfies"],
                f"{sid}: agent makes a claim that fails its own constraint "
                f"({cl['constraintId']}) -- self-contradictory trace",
            )

    # -- dropped-constraint errors must actually drop the violated constraint --
    for t in trials:
        sid = f"{t['id']} (slot {t['slot']})"
        claimed = {c["constraintId"] for c in t["agentClaims"]}
        if t["errorType"] == "dropped_constraint":
            check(
                set(t["omittedConstraintIds"]) == set(t["violatedConstraintIds"]),
                f"{sid}: omitted constraints != violated constraints",
            )
            check(
                not (claimed & set(t["violatedConstraintIds"])),
                f"{sid}: agent claims a constraint it supposedly dropped",
            )
        else:
            check(
                t["omittedConstraintIds"] == [],
                f"{sid}: non-dropped-constraint trial omits a constraint anyway",
            )
            check(
                claimed == {c["id"] for c in t["constraints"]},
                f"{sid}: agent does not address every constraint",
            )

    # -- I2: tone must not depend on ground truth -----------------------------
    # The tone layer is the single place the honest/sycophantic manipulation is
    # applied. If it can see trial correctness, tone leaks ground truth and H3/H4
    # become uninterpretable. We enforce this structurally: the tone module must
    # not reference any ground-truth field.
    if TONE_TS.exists():
        tone_src = TONE_TS.read_text(encoding="utf-8")
        code = "\n".join(
            line for line in tone_src.splitlines()
            if not line.strip().startswith(("//", "*", "/*"))
        )
        forbidden = [
            "isErrorTrial", "errorType", "violatedConstraintIds",
            "compliantCandidateIds", "isFalseClaim", "trulySatisfies",
            "omittedConstraintIds",
        ]
        for token in forbidden:
            check(
                not re.search(rf"\b{token}\b", code),
                f"tone.ts references ground-truth field '{token}': tone would leak "
                "correctness and confound the Tone manipulation (invariant I2)",
            )
    else:
        check(False, f"expected tone module at {TONE_TS} (invariant I2 unenforced)")

    # -- report ---------------------------------------------------------------
    if failures:
        print(f"VALIDATION FAILED ({len(failures)} of {checks_run} checks)\n", file=sys.stderr)
        for f in failures:
            print(f"  x {f}", file=sys.stderr)
        return 1

    n_err = len(error_slots)
    print(f"VALIDATION PASSED ({checks_run} checks)")
    print(f"  {len(trials)} trials, {n_err} seeded errors at slots {error_slots}")
    print(f"  error types: {sorted(e for e in etypes)}")
    print(f"  base error rate: {n_err}/{len(trials)} = {n_err / len(trials):.0%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
