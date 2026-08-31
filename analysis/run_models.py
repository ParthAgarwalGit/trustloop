#!/usr/bin/env python3
"""
Fit the preregistered models and print results in a form you can paste into a paper.

Outputs:
    data/derived/model_results.csv   every term, F, p and partial eta^2
    stdout                           APA-formatted lines + simple-effects breakdown

Usage:
    python analysis/run_models.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.anova import anova_lm

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"

# DVs to model, in reporting order, with the hypothesis each one speaks to.
DVS = [
    ("detection_rate",       "H1/H3/H4  primary: proportion of seeded errors overridden"),
    ("detection_minus_fa",   "H1/H3/H4  detection corrected for response bias"),
    ("confidence_gap",       "H1/H4     trust calibration (confidence clean - seeded)"),
    ("appropriate_reliance", "H1/H3/H4  accept-when-clean + override-when-seeded"),
    ("false_alarm_rate",     "control    should not differ much by condition"),
    ("trust",                "H2/H3     subjective trust"),
    ("authenticity",         "H3        perceived authenticity"),
    ("tlx_raw",              "H2        oversight burden (the cost side)"),
    ("process_acceptability", "H2       process acceptability"),
    ("transparency_suff",    "H2        perceived sufficiency of what was shown"),
    ("reliance_intent",      "H2/H3     willingness to rely unsupervised"),
]


def partial_eta_sq(aov: pd.DataFrame) -> pd.Series:
    ss_resid = aov.loc["Residual", "sum_sq"]
    return aov["sum_sq"] / (aov["sum_sq"] + ss_resid)


def apa(term: str, f: float, df1: float, df2: float, p: float, eta: float) -> str:
    p_str = "p < .001" if p < 0.001 else f"p = {p:.3f}".replace("0.", ".")
    eta_str = f"{eta:.3f}".replace("0.", ".")
    return f"F({df1:.0f}, {df2:.0f}) = {f:.2f}, {p_str}, partial eta^2 = {eta_str}"


def cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    a, b = np.asarray(a, float), np.asarray(b, float)
    a, b = a[~np.isnan(a)], b[~np.isnan(b)]
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    s = np.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1))
                / (len(a) + len(b) - 2))
    return float((a.mean() - b.mean()) / s) if s else float("nan")


def manipulation_checks(df: pd.DataFrame) -> None:
    print("=" * 78)
    print("MANIPULATION CHECKS")
    print("=" * 78)
    print("If these fail, nothing downstream is interpretable -- report them first.\n")

    checks = [
        ("mc_tone_warm", "tone", "sycophantic", "honest", "Tone: perceived as complimentary"),
        ("mc_tone_hedge", "tone", "honest", "sycophantic", "Tone: perceived as hedging"),
        ("mc_disc_steps", "disclosure", "full", "opaque", "Disclosure: showed its steps"),
        ("mc_disc_verify", "disclosure", "full", "opaque", "Disclosure: claims checkable"),
    ]
    for col, factor, hi, lo, label in checks:
        if col not in df.columns:
            print(f"  {label:<42} [item not present]")
            continue
        a = df.loc[df[factor] == hi, col].dropna()
        b = df.loc[df[factor] == lo, col].dropna()
        if len(a) < 2 or len(b) < 2:
            print(f"  {label:<42} [insufficient data]")
            continue
        t, p = stats.ttest_ind(a, b, equal_var=False)
        d = cohens_d(a.values, b.values)
        ok = "PASS" if (p < 0.05 and t > 0) else "** FAIL **"
        p_str = "p < .001" if p < 0.001 else f"p = {p:.3f}"
        print(f"  {label:<42} {hi} M={a.mean():.2f} vs {lo} M={b.mean():.2f}  "
              f"t={t:.2f}, {p_str}, d={d:.2f}  {ok}")
    print()


def main() -> None:
    df = pd.read_csv(DERIVED / "dvs.csv")
    df["disclosure"] = pd.Categorical(df["disclosure"], ["opaque", "full"])
    df["tone"] = pd.Categorical(df["tone"], ["honest", "sycophantic"])

    print(f"\nN = {len(df)} after exclusions")
    print(df.groupby(["disclosure", "tone"], observed=True).size().to_string())
    print()

    manipulation_checks(df)

    rows = []
    print("=" * 78)
    print("2x2 BETWEEN-SUBJECTS ANOVA (Type III sums of squares)")
    print("=" * 78)

    for dv, note in DVS:
        if dv not in df.columns or df[dv].notna().sum() < 20:
            continue
        sub = df[[dv, "disclosure", "tone"]].dropna()
        # Sum (effect) coding is required for Type III SS to be meaningful.
        model = smf.ols(
            f"{dv} ~ C(disclosure, Sum) * C(tone, Sum)", data=sub
        ).fit()
        aov = anova_lm(model, typ=3)
        eta = partial_eta_sq(aov)
        df2 = aov.loc["Residual", "df"]

        print(f"\n--- {dv}  [{note}]")
        cells = sub.groupby(["disclosure", "tone"], observed=True)[dv].agg(["mean", "std", "count"])
        for (d, t), r in cells.iterrows():
            print(f"      {d:<7} x {t:<12} M = {r['mean']:.3f}  SD = {r['std']:.3f}  n = {int(r['count'])}")

        label_map = {
            "C(disclosure, Sum)": "Disclosure",
            "C(tone, Sum)": "Tone",
            "C(disclosure, Sum):C(tone, Sum)": "Disclosure x Tone",
        }
        for term, label in label_map.items():
            if term not in aov.index:
                continue
            f_val, p_val = aov.loc[term, "F"], aov.loc[term, "PR(>F)"]
            star = "  <-- H4" if label.startswith("Disclosure x") else ""
            print(f"      {label:<20} {apa(label, f_val, aov.loc[term, 'df'], df2, p_val, eta[term])}{star}")
            rows.append({
                "dv": dv, "term": label, "F": f_val, "df1": aov.loc[term, "df"],
                "df2": df2, "p": p_val, "partial_eta_sq": eta[term],
            })

        # Simple effects: an interaction is only interpretable once you show what it
        # looks like inside each level of the moderator.
        inter_p = aov.loc["C(disclosure, Sum):C(tone, Sum)", "PR(>F)"]
        if inter_p < 0.10:
            print("      Simple effects of Tone within each Disclosure level:")
            for lvl in ("opaque", "full"):
                s = sub[sub["disclosure"] == lvl]
                a = s.loc[s["tone"] == "sycophantic", dv]
                b = s.loc[s["tone"] == "honest", dv]
                if len(a) < 2 or len(b) < 2:
                    continue
                t_val, p_val = stats.ttest_ind(a, b, equal_var=False)
                d = cohens_d(a.values, b.values)
                p_str = "p < .001" if p_val < 0.001 else f"p = {p_val:.3f}"
                print(f"        {lvl:<7} sycophantic - honest = {a.mean() - b.mean():+.3f}  "
                      f"t = {t_val:.2f}, {p_str}, d = {d:.2f}")

    # --- trial-level model ---------------------------------------------------
    # The participant-level ANOVA throws away trial-to-trial structure. This GEE fits
    # the per-trial override decision on seeded-error trials directly, with an
    # exchangeable working correlation clustered by participant, which is the right
    # unit of analysis for a binary outcome measured repeatedly within person.
    print("\n" + "=" * 78)
    print("TRIAL-LEVEL MODEL -- P(override | seeded-error trial)")
    print("=" * 78)
    trials = pd.read_csv(DERIVED / "trials.csv")
    err = trials[trials["is_error_trial"]].copy()
    if not err.empty:
        err["disclosure"] = pd.Categorical(err["disclosure"], ["opaque", "full"])
        err["tone"] = pd.Categorical(err["tone"], ["honest", "sycophantic"])
        gee = smf.gee(
            "overrode ~ C(disclosure, Sum) * C(tone, Sum)",
            groups="participant_id", data=err,
            family=sm.families.Binomial(),
            cov_struct=sm.cov_struct.Exchangeable(),
        ).fit()
        print(gee.summary().tables[1])
        print("\n  Odds ratios:")
        for term, coef in gee.params.items():
            if term == "Intercept":
                continue
            print(f"    {term:<40} OR = {np.exp(coef):.3f}  p = {gee.pvalues[term]:.3f}")

        print("\n  Detection rate by error type (descriptive):")
        by_type = err.groupby(["error_type", "disclosure", "tone"], observed=True)["overrode"].mean()
        print(by_type.round(3).to_string())

    out = pd.DataFrame(rows)
    out.to_csv(DERIVED / "model_results.csv", index=False)
    print(f"\nWrote -> {DERIVED / 'model_results.csv'}")


if __name__ == "__main__":
    main()
