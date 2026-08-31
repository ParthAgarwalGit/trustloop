#!/usr/bin/env python3
"""
Turn raw session JSON into two tidy tables, applying the preregistered exclusions.

    data/derived/trials.csv        one row per participant x trial
    data/derived/participants.csv  one row per participant (DVs + survey scales)
    data/derived/exclusions.csv    every excluded participant and the reason

Exclusions are applied HERE and nowhere else, so the rule set is auditable in one
place and the excluded-participant table can go straight into the paper.

Usage:
    python analysis/prepare_data.py --raw data/raw
    python analysis/prepare_data.py --raw data/raw_sim --allow-simulated
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TRIALS_JSON = ROOT / "app" / "src" / "data" / "trials.json"
DERIVED = ROOT / "data" / "derived"

# --- preregistered exclusion thresholds --------------------------------------
# Changing these after seeing the data is a researcher degree of freedom. Fix them
# in docs/ANALYSIS_PLAN.md before collection and do not touch them afterwards.
#
# The two speeding rules do different jobs, and the second one is deliberately loose:
#
#   MIN_MEDIAN_RT_MS is the PRIMARY speeding check. It is per-trial, so it catches
#   participants who are clicking through without reading, and it does not encode how
#   much text a condition happens to contain.
#
#   MIN_TOTAL_MINUTES is a backstop for implausible whole sessions only. It must stay
#   well below the slowest condition's expected total, because the full-disclosure
#   interface takes materially longer to read than the opaque one: a tight aggregate
#   floor removes opaque participants several times more often than full ones, which
#   is differential attrition and biases the central comparison. prepare_data.py
#   reports exclusion rate by cell and warns when the spread exceeds 10 points --
#   if that warning fires, this constant is the first thing to check.
MIN_MEDIAN_RT_MS = 3000      # median per-trial RT below this = not reading
MIN_TOTAL_MINUTES = 2.0      # backstop only: <12 s/trial averaged over 10 trials
MAX_ATTENTION_FAILS = 1      # >1 failed attention check = excluded
ATTENTION_CHECKS = {"attn_1": 3, "attn_2": 7}


def load_sessions(raw_dir: Path, allow_simulated: bool) -> list[dict]:
    files = sorted(raw_dir.glob("*.json"))
    if not files:
        sys.exit(f"No session files found in {raw_dir}")

    sessions = []
    n_sim = 0
    for f in files:
        try:
            s = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"  ! skipping unreadable file {f.name}: {e}")
            continue
        # A Supabase CSV/JSON export nests the payload under `data`.
        if "data" in s and "meta" in s.get("data", {}):
            s = s["data"]
        if s.get("meta", {}).get("SIMULATED"):
            n_sim += 1
        sessions.append(s)

    if n_sim and not allow_simulated:
        sys.exit(
            f"{n_sim} of {len(sessions)} sessions are SIMULATED. Refusing to build a "
            "dataset that mixes simulated and real data. Pass --allow-simulated to "
            "analyse a purely simulated set."
        )
    if n_sim and n_sim != len(sessions):
        sys.exit(
            f"Mixed input: {n_sim} simulated and {len(sessions) - n_sim} real sessions "
            "in the same directory. Separate them."
        )
    return sessions


def session_exclusion(s: dict, trial_rows: pd.DataFrame) -> tuple[str, str] | None:
    """
    Return (canonical_reason, detail), or None to keep the participant.

    The reason is a fixed label so exclusions aggregate cleanly in the paper's
    participant-flow table; the varying numbers go in `detail`.
    """
    meta = s.get("meta", {})
    survey = s.get("survey", {})

    if meta.get("isPreview"):
        return ("preview run", "")
    if survey.get("withdrawn") == 1:
        return ("withdrew at debrief", "")
    if s.get("completedAt") is None:
        return ("incomplete session", "")

    expected = len(json.loads(TRIALS_JSON.read_text(encoding="utf-8"))["trials"])
    if len(trial_rows) != expected:
        return ("incomplete trials", f"{len(trial_rows)}/{expected}")

    fails = sum(
        1 for k, v in ATTENTION_CHECKS.items()
        if k in survey and survey[k] != v
    )
    if fails > MAX_ATTENTION_FAILS:
        return ("failed attention checks", f"{fails} failed")

    median_rt = trial_rows["rtMs"].median()
    if median_rt < MIN_MEDIAN_RT_MS:
        return ("median RT too fast", f"{median_rt:.0f} ms")

    total_min = trial_rows["rtMs"].sum() / 60000
    if total_min < MIN_TOTAL_MINUTES:
        return ("total task time too short", f"{total_min:.1f} min")

    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--allow-simulated", action="store_true")
    args = ap.parse_args()

    raw_dir = ROOT / args.raw
    sessions = load_sessions(raw_dir, args.allow_simulated)

    trials_meta = {
        t["id"]: t
        for t in json.loads(TRIALS_JSON.read_text(encoding="utf-8"))["trials"]
    }

    all_trials: list[dict] = []
    participants: list[dict] = []
    exclusions: list[dict] = []

    for s in sessions:
        meta = s.get("meta", {})
        pid = meta.get("participantId", "unknown")
        cond = meta.get("condition", {})

        rows = []
        for r in s.get("trials", []):
            t = trials_meta.get(r["trialId"])
            if t is None:
                continue
            overrode = r["decision"] == "override"
            rows.append({
                "participant_id": pid,
                "disclosure": cond.get("disclosure"),
                "tone": cond.get("tone"),
                "trial_id": r["trialId"],
                "slot": r["slot"],
                "position": len(rows) + 1,
                "domain": t["domain"],
                "is_error_trial": bool(t["isErrorTrial"]),
                "error_type": t["errorType"],
                "confidence": r["confidence"],
                "decision": r["decision"],
                "overrode": int(overrode),
                "chosen_id": r["chosenId"],
                # a *correct* override lands on a genuinely compliant option
                "chose_compliant": int(r["chosenId"] in t["compliantCandidateIds"]),
                "rtMs": r["rtMs"],
                "n_verifications": len(r.get("verifications", [])),
                "opened_alternatives": int(bool(r.get("openedAlternatives"))),
            })

        tdf = pd.DataFrame(rows)
        excl = session_exclusion(s, tdf) if not tdf.empty else ("no trial data", "")

        if excl:
            reason, detail = excl
            exclusions.append({
                "participant_id": pid,
                "disclosure": cond.get("disclosure"),
                "tone": cond.get("tone"),
                "reason": reason,
                "detail": detail,
            })
            continue

        all_trials.extend(rows)
        participants.append({
            "participant_id": pid,
            "disclosure": cond.get("disclosure"),
            "tone": cond.get("tone"),
            "comprehension_attempts": s.get("comprehensionAttempts"),
            "total_task_minutes": tdf["rtMs"].sum() / 60000,
            **{f"sv_{k}": v for k, v in s.get("survey", {}).items()},
        })

    DERIVED.mkdir(parents=True, exist_ok=True)
    trials_df = pd.DataFrame(all_trials)
    parts_df = pd.DataFrame(participants)
    excl_df = pd.DataFrame(exclusions)

    trials_df.to_csv(DERIVED / "trials.csv", index=False)
    parts_df.to_csv(DERIVED / "participants.csv", index=False)
    excl_df.to_csv(DERIVED / "exclusions.csv", index=False)

    print(f"Read {len(sessions)} sessions from {raw_dir}")
    print(f"  retained : {len(parts_df)}")
    print(f"  excluded : {len(excl_df)}")
    if not excl_df.empty:
        for reason, n in excl_df["reason"].value_counts().items():
            print(f"      {n:>3}  {reason}")

    if not parts_df.empty:
        print("\nRealised cell sizes:")
        cells = parts_df.groupby(["disclosure", "tone"]).size()
        for (d, t), n in cells.items():
            print(f"  {d:<7} x {t:<12} n = {n}")
        if cells.min() < 0.7 * cells.max():
            print(
                "  ! cells are noticeably unbalanced -- consider a top-up batch, and "
                "use Type II/III sums of squares (run_models.py already does)."
            )

    # --- differential attrition check ----------------------------------------
    # A time-based exclusion can bite one condition harder than another: the full
    # disclosure interface simply takes longer to work through, so a fixed floor
    # removes proportionally more opaque participants. That is differential
    # attrition, and it silently biases the very comparison the study is built on.
    if not excl_df.empty and not parts_df.empty:
        attempted = pd.concat([
            parts_df[["disclosure", "tone"]],
            excl_df[["disclosure", "tone"]],
        ])
        rate = (
            excl_df.groupby(["disclosure", "tone"]).size()
            / attempted.groupby(["disclosure", "tone"]).size()
        ).fillna(0.0)
        print("\nExclusion rate by cell:")
        for (d, t), r in rate.items():
            print(f"  {d:<7} x {t:<12} {r:.1%}")
        spread = rate.max() - rate.min()
        if spread > 0.10:
            print(
                f"\n  !! DIFFERENTIAL ATTRITION: exclusion rates differ by {spread:.1%} "
                "across cells.\n"
                "     Condition now predicts who survives exclusion, which biases the\n"
                "     between-subjects comparison. Before analysing, either (a) relax the\n"
                "     time-based thresholds, which are the usual culprit because the full\n"
                "     disclosure interface takes longer to read, or (b) report the\n"
                "     sensitivity analysis over the unexcluded sample as well."
            )

    print(f"\nWrote -> {DERIVED}")


if __name__ == "__main__":
    main()
