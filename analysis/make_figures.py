#!/usr/bin/env python3
"""
Produce publication-ready figures.

Outputs (PDF for the paper, PNG for slides/posters) into figures/:
    fig1_interaction.{pdf,png}   the H4 interaction plot -- the paper's money figure
    fig2_dv_panel.{pdf,png}      condition means across the main DVs
    fig3_calibration.{pdf,png}   confidence on clean vs seeded trials
    fig4_verification.{pdf,png}  verification behaviour (full condition only)

Design choices that matter for CHI:
  * colourblind-safe palette (Okabe-Ito), and the two conditions also differ by
    marker and line style, so the figures survive greyscale printing;
  * error bars are 95% CIs, stated in every caption;
  * no chartjunk, no 3D, axis ranges start at a sensible baseline and are labelled.

Usage:
    python analysis/make_figures.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
FIGS = ROOT / "figures"

# Okabe-Ito: safe for all common colour vision deficiencies.
BLUE = "#0072B2"
ORANGE = "#E69F00"
STYLE = {
    "opaque": dict(color=ORANGE, marker="s", linestyle="--", label="Opaque"),
    "full": dict(color=BLUE, marker="o", linestyle="-", label="Full disclosure"),
}
TONE_ORDER = ["honest", "sycophantic"]
TONE_LABELS = ["Calibrated-honest", "Sycophantic"]

plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "font.size": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linewidth": 0.5,
    "legend.frameon": False,
})


def ci95(x: pd.Series) -> float:
    x = x.dropna()
    n = len(x)
    if n < 2:
        return 0.0
    return 1.96 * x.std(ddof=1) / np.sqrt(n)


def save(fig: plt.Figure, name: str) -> None:
    FIGS.mkdir(exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(FIGS / f"{name}.{ext}", bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote figures/{name}.pdf and .png")


def interaction_plot(ax: plt.Axes, df: pd.DataFrame, dv: str, ylabel: str) -> None:
    x = np.arange(len(TONE_ORDER))
    for disc in ("opaque", "full"):
        sub = df[df["disclosure"] == disc]
        means = [sub.loc[sub["tone"] == t, dv].mean() for t in TONE_ORDER]
        errs = [ci95(sub.loc[sub["tone"] == t, dv]) for t in TONE_ORDER]
        ax.errorbar(
            x, means, yerr=errs, capsize=4, linewidth=1.8, markersize=7,
            **STYLE[disc],
        )
    ax.set_xticks(x)
    ax.set_xticklabels(TONE_LABELS)
    ax.set_xlabel("Agent tone")
    ax.set_ylabel(ylabel)
    ax.set_xlim(-0.3, len(TONE_ORDER) - 0.7)


def main() -> None:
    df = pd.read_csv(DERIVED / "dvs.csv")
    trials = pd.read_csv(DERIVED / "trials.csv")
    print("Writing figures...")

    # --- Fig 1: the H4 interaction -------------------------------------------
    fig, ax = plt.subplots(figsize=(4.2, 3.2))
    interaction_plot(ax, df, "detection_rate", "Error detection rate")
    ax.set_ylim(0, 1)
    ax.legend(title=None, loc="lower left")
    ax.set_title("Does verifiability blunt the cost of a confident tone?", fontsize=9.5)
    save(fig, "fig1_interaction")

    # --- Fig 2: DV panel ------------------------------------------------------
    panel = [
        ("detection_rate", "Error detection rate"),
        ("confidence_gap", "Confidence gap (clean - seeded)"),
        ("trust", "Trust in agent (1-7)"),
        ("tlx_raw", "Oversight burden (Raw TLX)"),
    ]
    panel = [(d, l) for d, l in panel if d in df.columns]
    fig, axes = plt.subplots(1, len(panel), figsize=(3.1 * len(panel), 3.0))
    if len(panel) == 1:
        axes = [axes]
    for ax, (dv, label) in zip(axes, panel):
        interaction_plot(ax, df, dv, label)
    axes[0].legend(loc="best")
    fig.suptitle(
        "Condition means with 95% CIs. Disclosure improves detection and calibration "
        "but raises oversight burden.",
        fontsize=8.5, y=1.04,
    )
    fig.tight_layout()
    save(fig, "fig2_dv_panel")

    # --- Fig 3: calibration ---------------------------------------------------
    fig, ax = plt.subplots(figsize=(5.0, 3.2))
    cells, means, errs, colors = [], [], [], []
    for disc in ("opaque", "full"):
        for tone in TONE_ORDER:
            sub = df[(df["disclosure"] == disc) & (df["tone"] == tone)]
            for kind, col in (("clean", "confidence_clean"), ("seeded", "confidence_error")):
                cells.append(f"{disc[:4]}/{tone[:3]}\n{kind}")
                means.append(sub[col].mean())
                errs.append(ci95(sub[col]))
                colors.append(BLUE if disc == "full" else ORANGE)
    xpos = np.arange(len(cells))
    bars = ax.bar(xpos, means, yerr=errs, capsize=3, color=colors, edgecolor="white")
    # hatch the seeded-trial bars so the pairing survives greyscale
    for i, b in enumerate(bars):
        if i % 2 == 1:
            b.set_hatch("///")
            b.set_alpha(0.75)
    ax.set_xticks(xpos)
    ax.set_xticklabels(cells, fontsize=6.5)
    ax.set_ylabel("Mean confidence (1-7)")
    ax.set_ylim(1, 7)
    ax.set_title(
        "Confidence on correct vs deliberately flawed recommendations\n"
        "(a wider gap = better calibration; hatched = flawed trials)",
        fontsize=9,
    )
    save(fig, "fig3_calibration")

    # --- Fig 4: verification behaviour ---------------------------------------
    full_trials = trials[trials["disclosure"] == "full"]
    if not full_trials.empty:
        fig, ax = plt.subplots(figsize=(4.6, 3.2))
        g = (
            full_trials.groupby(["tone", "is_error_trial"])["n_verifications"]
            .agg(["mean", ci95])
            .reset_index()
        )
        width = 0.35
        x = np.arange(2)
        for i, is_err in enumerate([False, True]):
            sub = g[g["is_error_trial"] == is_err]
            vals = [
                sub.loc[sub["tone"] == t, "mean"].squeeze() if (sub["tone"] == t).any() else np.nan
                for t in TONE_ORDER
            ]
            errs = [
                sub.loc[sub["tone"] == t, "ci95"].squeeze() if (sub["tone"] == t).any() else 0
                for t in TONE_ORDER
            ]
            ax.bar(
                x + (i - 0.5) * width, vals, width, yerr=errs, capsize=3,
                color=BLUE if not is_err else ORANGE,
                hatch="" if not is_err else "///",
                edgecolor="white",
                label="Correct trials" if not is_err else "Flawed trials",
            )
        ax.set_xticks(x)
        ax.set_xticklabels(TONE_LABELS)
        ax.set_xlabel("Agent tone")
        ax.set_ylabel("Claims checked per trial")
        ax.legend()
        ax.set_title("Do people actually use the evidence they are given?", fontsize=9.5)
        save(fig, "fig4_verification")

    print(f"\nAll figures -> {FIGS}")


if __name__ == "__main__":
    main()
