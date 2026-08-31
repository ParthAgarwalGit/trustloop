#!/usr/bin/env python3
"""
Generate synthetic sessions in EXACTLY the shape the app produces.

Why this exists: it lets you build, debug and lock down the entire analysis pipeline
-- and write the Results section's code -- before recruiting a single participant.
Run the full pipeline on simulated data, confirm it recovers the effects you planted,
and only then collect real data. If the pipeline cannot recover a known effect, the
bug is in your analysis, not in your participants.

The planted effects below are HYPOTHESISED values used to test the machinery. They
are not predictions to be reported, and you must never present simulated output as a
result. `analysis/prepare_data.py` refuses to mix simulated and real sessions.

Usage:
    python analysis/simulate_data.py --n 200 --out data/raw_sim
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TRIALS_JSON = ROOT / "app" / "src" / "data" / "trials.json"

# --- planted ground truth -----------------------------------------------------
# P(override | seeded-error trial), by cell. The pattern encodes H1 (full > opaque),
# H3 (sycophantic < honest) and H4 (the sycophancy penalty is much larger when the
# participant cannot check the work).
P_DETECT = {
    ("opaque", "honest"): 0.45,
    ("opaque", "sycophantic"): 0.24,   # -0.21
    ("full", "honest"): 0.70,
    ("full", "sycophantic"): 0.62,     # -0.08  -> interaction
}
# P(override | clean trial) -- false alarms, deliberately near-constant so detection
# differences are not just a response-bias shift.
P_FALSE_ALARM = {
    ("opaque", "honest"): 0.07,
    ("opaque", "sycophantic"): 0.05,
    ("full", "honest"): 0.10,
    ("full", "sycophantic"): 0.08,
}
# Mean confidence (1-7) on clean and seeded trials.
CONF_CLEAN = {"honest": 5.2, "sycophantic": 5.8}
CONF_ERROR_PENALTY = {"opaque": 0.25, "full": 0.95}  # discrimination, i.e. calibration

# Survey block means (1-7) and TLX (0-100).
TRUST_BASE = {"honest": 4.6, "sycophantic": 5.1}
TRUST_DISCLOSURE_BONUS = {"opaque": 0.0, "full": 0.45}
AUTH_BASE = {"honest": 5.3, "sycophantic": 4.2}
TLX_BASE = {"opaque": 38.0, "full": 51.0}   # H2: disclosure costs effort


def make_session(pid: str, trials: list[dict], rng: random.Random) -> dict:
    disclosure = rng.choice(["opaque", "full"])
    tone = rng.choice(["honest", "sycophantic"])
    cell = (disclosure, tone)

    order = list(trials)
    trial_rows = []
    for t in order:
        if t["isErrorTrial"]:
            p_override = P_DETECT[cell]
            conf_mu = CONF_CLEAN[tone] - CONF_ERROR_PENALTY[disclosure]
        else:
            p_override = P_FALSE_ALARM[cell]
            conf_mu = CONF_CLEAN[tone]

        override = rng.random() < p_override
        conf = int(np.clip(round(rng.gauss(conf_mu, 1.1)), 1, 7))
        # people who override tend to have been less confident
        if override:
            conf = int(np.clip(conf - rng.randint(0, 2), 1, 7))

        chosen = (
            rng.choice(t["compliantCandidateIds"])
            if override
            else t["recommendedId"]
        )
        n_ver = (
            rng.randint(0, len(t["agentClaims"])) if disclosure == "full" else 0
        )
        trial_rows.append({
            "trialId": t["id"],
            "slot": t["slot"],
            "confidence": conf,
            "decision": "override" if override else "accept",
            "chosenId": chosen,
            # Realistic per-trial reading + deciding time. The full condition is
            # slower by construction (more to read), which is exactly why the
            # time-based exclusions in prepare_data.py must be checked for
            # differential attrition rather than assumed harmless.
            "rtMs": int(max(2500, rng.gauss(46000 if disclosure == "full" else 29000, 14000))),
            "verifications": [
                {"constraintId": t["agentClaims"][i]["constraintId"], "tMs": 3000 + i * 1500}
                for i in range(n_ver)
            ],
            "openedAlternatives": disclosure == "full" and rng.random() < 0.4,
        })

    # Per-participant latent offsets. Without these, items within a scale are
    # independent, inter-item correlations are ~0 and Cronbach's alpha comes out near
    # zero -- which would hide a genuine bug in the reliability code behind an
    # artefact of the simulation. Real respondents have a stable individual level on
    # each construct, so model that.
    u = {k: rng.gauss(0, 0.75) for k in ("trust", "auth", "trans", "rely")}

    def lik(mu: float, sd: float = 0.7, latent: str | None = None, sign: int = 1) -> int:
        # `sign=-1` for reverse-WORDED items: someone high on the construct answers
        # low on them. Applying the offset with the same sign as the positive items
        # would make the offset flip once analysis reverse-scores the item, turning a
        # positive correlation into a negative one and collapsing alpha.
        offset = sign * u[latent] if latent else 0.0
        return int(np.clip(round(rng.gauss(mu + offset, sd)), 1, 7))

    trust_mu = TRUST_BASE[tone] + TRUST_DISCLOSURE_BONUS[disclosure]
    auth_mu = AUTH_BASE[tone]
    tlx_mu = TLX_BASE[disclosure]

    # ~6% of simulated participants fail an attention check, mirroring a realistic
    # Prolific sample, so the exclusion logic gets exercised.
    inattentive = rng.random() < 0.06

    survey = {
        "trust_1": lik(trust_mu, latent="trust"),
        "trust_2": lik(trust_mu, latent="trust"),
        "trust_3": lik(8 - trust_mu, latent="trust", sign=-1),   # reverse-worded
        "trust_4": lik(trust_mu, latent="trust"),
        "auth_1": lik(auth_mu, latent="auth"),
        "auth_2": lik(8 - auth_mu, latent="auth", sign=-1),
        "auth_3": lik(auth_mu, latent="auth"),
        "trans_suff_1": lik(5.6 if disclosure == "full" else 3.2, latent="trans"),
        "trans_suff_2": lik(3.4 if disclosure == "full" else 4.6, latent="trans", sign=-1),
        "accept_1": int(np.clip(round(rng.gauss(3.6 if disclosure == "full" else 2.9, 0.9)), 1, 5)),
        "rely_1": lik(trust_mu - 0.4, latent="rely"),
        "rely_2": lik(8 - trust_mu + 0.4, latent="rely", sign=-1),
        "tlx_mental": int(np.clip(rng.gauss(tlx_mu, 16), 0, 100)),
        "tlx_temporal": int(np.clip(rng.gauss(tlx_mu - 8, 16), 0, 100)),
        "tlx_performance": int(np.clip(rng.gauss(40, 18), 0, 100)),
        "tlx_effort": int(np.clip(rng.gauss(tlx_mu + 4, 16), 0, 100)),
        "tlx_frustration": int(np.clip(rng.gauss(tlx_mu - 12, 16), 0, 100)),
        "tlx_physical": int(np.clip(rng.gauss(12, 10), 0, 100)),
        # manipulation checks -- these should separate cleanly by cell
        "mc_tone_warm": lik(6.0 if tone == "sycophantic" else 2.8),
        "mc_tone_hedge": lik(5.7 if tone == "honest" else 2.4),
        "mc_disc_steps": lik(6.1 if disclosure == "full" else 2.2),
        "mc_disc_verify": lik(5.9 if disclosure == "full" else 2.0),
        "attn_1": rng.randint(1, 7) if inattentive else 3,
        "attn_2": rng.randint(1, 7) if inattentive else 7,
        "age": rng.randint(19, 62),
        "gender": rng.choice(["Woman", "Man", "Non-binary", "Prefer not to say"]),
        "ai_familiarity": lik(5.0, 1.4),
        "ai_shopping_use": rng.choice(["Never", "Once or twice", "Occasionally", "Regularly"]),
        "open_noticed": "",
        "open_strategy": "",
        "withdrawn": 1 if rng.random() < 0.02 else 0,
    }

    return {
        "meta": {
            "participantId": pid,
            "prolificPid": pid,
            "studyId": "SIM",
            "sessionId": pid,
            "condition": {"disclosure": disclosure, "tone": tone},
            "slotOrder": [t["slot"] for t in order],
            "startedAt": "2026-01-01T00:00:00.000Z",
            "userAgent": "simulated",
            "screen": {"w": 1440, "h": 900},
            "appVersion": "0.1.0",
            "isPreview": False,
            "SIMULATED": True,
        },
        "trials": trial_rows,
        "survey": survey,
        "comprehensionAttempts": 1,
        "completedAt": "2026-01-01T00:18:00.000Z",
        "events": [],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--out", default="data/raw_sim")
    ap.add_argument("--seed", type=int, default=20260901)
    args = ap.parse_args()

    trials = json.loads(TRIALS_JSON.read_text(encoding="utf-8"))["trials"]
    rng = random.Random(args.seed)
    np.random.seed(args.seed)

    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob("*.json"):
        f.unlink()

    for i in range(args.n):
        pid = f"sim{i:04d}"
        session = make_session(pid, trials, rng)
        (out_dir / f"{pid}.json").write_text(
            json.dumps(session, indent=1), encoding="utf-8"
        )

    print(f"Wrote {args.n} simulated sessions to {out_dir}")
    print("These are SIMULATED. Never report them as results.")


if __name__ == "__main__":
    main()
