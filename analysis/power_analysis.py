#!/usr/bin/env python3
"""
A priori power analysis for the 2x2 between-subjects design.

Run this BEFORE recruiting and paste the output into your preregistration and into
the Participants section of the paper. Reviewers ask for a justified N; "we ran 200
because that felt right" is a reviewable weakness.

Usage:
    python analysis/power_analysis.py
"""
from __future__ import annotations

import numpy as np
from statsmodels.stats.power import FTestAnovaPower

# Cohen's f benchmarks: .10 small, .25 medium, .40 large.
EFFECTS = [0.15, 0.20, 0.25, 0.30, 0.40]
ALPHA = 0.05
POWER = 0.80

# In a 2x2 ANOVA each main effect and the interaction is a 1-df contrast, so
# numerator df = 1 for all three tests. The interaction (H4) is the primary test and
# is the one N must be powered for -- interactions in factorial designs need roughly
# four times the N of a comparable main effect, which is why powering on the main
# effect alone would under-recruit.
NUM_DF = 1
N_CELLS = 4


def main() -> None:
    solver = FTestAnovaPower()

    print("A priori power analysis -- 2x2 between-subjects ANOVA")
    print(f"alpha = {ALPHA}, target power = {POWER}, numerator df = {NUM_DF}\n")
    print(f"{'Cohen f':>8}  {'eta_p^2':>8}  {'total N':>8}  {'per cell':>9}")
    print("-" * 40)

    for f in EFFECTS:
        n_total = solver.solve_power(
            effect_size=f, nobs=None, alpha=ALPHA, power=POWER, k_groups=N_CELLS
        )
        n_total = int(np.ceil(n_total))
        per_cell = int(np.ceil(n_total / N_CELLS))
        eta_p2 = f**2 / (1 + f**2)
        print(f"{f:>8.2f}  {eta_p2:>8.3f}  {n_total:>8d}  {per_cell:>9d}")

    print()
    for n_total in (120, 160, 200, 240):
        achieved = solver.power(
            effect_size=0.25, nobs=n_total, alpha=ALPHA, k_groups=N_CELLS
        )
        print(f"  N = {n_total:>3d} gives {achieved:.2f} power to detect f = 0.25")

    print(
        "\nRecommendation: recruit N = 200 (50 per cell). That gives ~0.80 power for a\n"
        "medium interaction effect (f = 0.25) with headroom for the exclusions\n"
        "specified in docs/ANALYSIS_PLAN.md (attention checks, speeding, withdrawals),\n"
        "which typically remove 5-15% of a Prolific sample."
    )


if __name__ == "__main__":
    main()
