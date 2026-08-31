#!/usr/bin/env python3
"""
Compute the dependent variables from the tidy tables.

    data/derived/dvs.csv   one row per participant, every DV plus condition factors

DV definitions live here and ONLY here, so the paper's Measures section can be
written directly from this file. They mirror app/src/lib/scoring.ts -- if you change
one, change both.

Usage:
    python analysis/compute_dvs.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"

# Survey scales: (column stems, items reverse-scored, scale max)
SCALES = {
    "trust":            (["sv_trust_1", "sv_trust_2", "sv_trust_3", "sv_trust_4"], ["sv_trust_3"], 7),
    "authenticity":     (["sv_auth_1", "sv_auth_2", "sv_auth_3"], ["sv_auth_2"], 7),
    "transparency_suff": (["sv_trans_suff_1", "sv_trans_suff_2"], ["sv_trans_suff_2"], 7),
    "reliance_intent":  (["sv_rely_1", "sv_rely_2"], ["sv_rely_2"], 7),
}
TLX_ITEMS = [
    "sv_tlx_mental", "sv_tlx_temporal", "sv_tlx_performance",
    "sv_tlx_effort", "sv_tlx_frustration", "sv_tlx_physical",
]


def score_scale(df: pd.DataFrame, items: list[str], reverse: list[str], smax: int) -> pd.Series:
    present = [c for c in items if c in df.columns]
    if not present:
        return pd.Series(np.nan, index=df.index)
    block = df[present].astype(float).copy()
    for c in reverse:
        if c in block.columns:
            block[c] = (smax + 1) - block[c]
    return block.mean(axis=1)


def cronbach_alpha(df: pd.DataFrame, items: list[str], reverse: list[str], smax: int) -> float:
    present = [c for c in items if c in df.columns]
    if len(present) < 2:
        return float("nan")
    block = df[present].astype(float).copy()
    for c in reverse:
        if c in block.columns:
            block[c] = (smax + 1) - block[c]
    block = block.dropna()
    k = block.shape[1]
    item_var = block.var(axis=0, ddof=1).sum()
    total_var = block.sum(axis=1).var(ddof=1)
    if total_var == 0:
        return float("nan")
    return (k / (k - 1)) * (1 - item_var / total_var)


def main() -> None:
    trials = pd.read_csv(DERIVED / "trials.csv")
    parts = pd.read_csv(DERIVED / "participants.csv")

    err = trials[trials["is_error_trial"] == True]   # noqa: E712
    clean = trials[trials["is_error_trial"] == False]  # noqa: E712

    g_err = err.groupby("participant_id")
    g_clean = clean.groupby("participant_id")
    g_all = trials.groupby("participant_id")

    dv = pd.DataFrame(index=parts.set_index("participant_id").index)

    # --- behavioural DVs -----------------------------------------------------
    # H1/H3/H4 primary: proportion of seeded-error trials the participant overrode.
    dv["detection_rate"] = g_err["overrode"].mean()
    # Stricter variant: overrode AND landed on a genuinely compliant option.
    dv["detection_rate_strict"] = g_err.apply(
        lambda d: float((d["overrode"] & d["chose_compliant"]).mean()), include_groups=False
    )
    # Needed to interpret detection: someone who overrides everything is not vigilant.
    dv["false_alarm_rate"] = g_clean["overrode"].mean()
    # Signal-detection style discrimination, robust to response bias.
    dv["detection_minus_fa"] = dv["detection_rate"] - dv["false_alarm_rate"]

    dv["appropriate_reliance"] = g_all.apply(
        lambda d: float(
            ((d["is_error_trial"] & (d["overrode"] == 1))
             | (~d["is_error_trial"] & (d["overrode"] == 0))).mean()
        ),
        include_groups=False,
    )

    # --- trust calibration ---------------------------------------------------
    # PRIMARY calibration measure: mean confidence on clean minus on seeded trials.
    # With only 3 seeded trials per participant a within-person point-biserial
    # correlation is very noisy (and undefined when a participant gives constant
    # confidence), so the mean difference is the preregistered primary and the
    # correlation is reported as a secondary.
    dv["confidence_clean"] = g_clean["confidence"].mean()
    dv["confidence_error"] = g_err["confidence"].mean()
    dv["confidence_gap"] = dv["confidence_clean"] - dv["confidence_error"]

    def point_biserial(d: pd.DataFrame) -> float:
        # correlation between confidence and trial correctness (1 = clean)
        correct = (~d["is_error_trial"]).astype(float)
        if d["confidence"].nunique() < 2 or correct.nunique() < 2:
            return np.nan
        return float(np.corrcoef(d["confidence"], correct)[0, 1])

    dv["calibration_r"] = g_all.apply(point_biserial, include_groups=False)

    # --- process measures ----------------------------------------------------
    dv["mean_verifications"] = g_all["n_verifications"].mean()
    dv["prop_trials_verified"] = g_all.apply(
        lambda d: float((d["n_verifications"] > 0).mean()), include_groups=False
    )
    dv["prop_opened_alternatives"] = g_all["opened_alternatives"].mean()
    dv["median_rt_ms"] = g_all["rtMs"].median()

    # --- survey scales -------------------------------------------------------
    parts_idx = parts.set_index("participant_id")
    for name, (items, reverse, smax) in SCALES.items():
        dv[name] = score_scale(parts_idx, items, reverse, smax)

    if "sv_accept_1" in parts_idx.columns:
        dv["process_acceptability"] = parts_idx["sv_accept_1"].astype(float)

    tlx_present = [c for c in TLX_ITEMS if c in parts_idx.columns]
    if tlx_present:
        dv["tlx_raw"] = parts_idx[tlx_present].astype(float).mean(axis=1)

    # --- manipulation checks -------------------------------------------------
    for col, out in [
        ("sv_mc_tone_warm", "mc_tone_warm"),
        ("sv_mc_tone_hedge", "mc_tone_hedge"),
        ("sv_mc_disc_steps", "mc_disc_steps"),
        ("sv_mc_disc_verify", "mc_disc_verify"),
    ]:
        if col in parts_idx.columns:
            dv[out] = parts_idx[col].astype(float)

    # --- factors + covariates ------------------------------------------------
    dv["disclosure"] = parts_idx["disclosure"]
    dv["tone"] = parts_idx["tone"]
    for c in ("sv_age", "sv_ai_familiarity", "sv_gender", "sv_ai_shopping_use"):
        if c in parts_idx.columns:
            dv[c.replace("sv_", "")] = parts_idx[c]

    dv = dv.reset_index()
    dv.to_csv(DERIVED / "dvs.csv", index=False)

    print(f"Computed DVs for {len(dv)} participants -> {DERIVED / 'dvs.csv'}\n")

    print("Scale reliability (Cronbach's alpha):")
    for name, (items, reverse, smax) in SCALES.items():
        a = cronbach_alpha(parts_idx, items, reverse, smax)
        flag = "" if (np.isnan(a) or a >= 0.70) else "   <- below .70, report and interpret with caution"
        print(f"  {name:<20} alpha = {a:.2f}{flag}")
    if tlx_present:
        print(f"  {'tlx_raw':<20} (index, alpha not applicable)")

    print("\nCell means (primary DVs):")
    primary = [
        "detection_rate", "false_alarm_rate", "confidence_gap",
        "appropriate_reliance", "trust", "tlx_raw",
    ]
    have = [c for c in primary if c in dv.columns]
    summary = dv.groupby(["disclosure", "tone"])[have].mean().round(3)
    print(summary.to_string())


if __name__ == "__main__":
    main()
