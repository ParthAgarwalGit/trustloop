#!/usr/bin/env python3
"""
Publish the study to GitHub Pages from a SEPARATE, neutrally named repository.

Why a separate repo: the source repo is named `trustloop` and its README explains
that 3 of 10 recommendations are planted. Hosting at `.../trustloop/` would put
"trust" in the link participants receive (banned by docs/RECRUITMENT.md) and point
the curious straight at the reveal. The hosting repo contains only the built,
minified site -- no source, no docs, no sourcemaps.

Usage (from the trustloop repo root):
    python deploy/pages/publish.py              # real publish; requires app/.env
    python deploy/pages/publish.py --preview    # allow no data sink / no contact
                                                # details (testing only -- do not
                                                # send this link to participants)
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "app"
SITE = Path(__file__).resolve().parent / ".site"  # gitignored checkout of the host repo
OWNER = "ParthAgarwalGit"

REQUIRED_FOR_REAL = [
    "VITE_DATA_SINK", "VITE_RESEARCHER_NAME", "VITE_RESEARCHER_EMAIL",
    "VITE_INSTITUTION",
]


def run(cmd: list[str], cwd: Path | None = None, env: dict | None = None,
        check: bool = True) -> subprocess.CompletedProcess:
    print("  $ " + " ".join(cmd))
    return subprocess.run(cmd, cwd=cwd, env=env, check=check, text=True,
                          capture_output=False, shell=(os.name == "nt"))


def read_env() -> dict[str, str]:
    path = APP / ".env"
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="shop-assistant-study")
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()

    env_vals = read_env()
    if not args.preview:
        missing = [k for k in REQUIRED_FOR_REAL if not env_vals.get(k)]
        if env_vals.get("VITE_DATA_SINK", "none") == "none":
            missing.append("VITE_DATA_SINK (must not be 'none': responses would "
                           "never reach you)")
        if missing:
            sys.exit("Refusing a real publish. Set these in app/.env:\n  - "
                     + "\n  - ".join(missing)
                     + "\nOr pass --preview for a test link you will not share.")

    print("1/4 Building...")
    build_env = {**os.environ, "BASE_PATH": f"/{args.repo}/", "SOURCEMAP": "false"}
    run(["npm", "run", "build"], cwd=APP, env=build_env)
    dist = APP / "dist"
    if list(dist.rglob("*.map")):
        sys.exit("Build still contains sourcemaps; refusing to publish them.")

    print("2/4 Preparing the hosting repo...")
    exists = subprocess.run(
        ["gh", "repo", "view", f"{OWNER}/{args.repo}"],
        capture_output=True, text=True, shell=(os.name == "nt"),
    ).returncode == 0
    if not exists:
        run(["gh", "repo", "create", f"{OWNER}/{args.repo}", "--public",
             "--description", "Shopping assistant study"])
    if not (SITE / ".git").exists():
        if SITE.exists():
            shutil.rmtree(SITE)
        run(["git", "clone", f"https://github.com/{OWNER}/{args.repo}.git",
             str(SITE)], check=False)
        if not (SITE / ".git").exists():  # brand-new empty repo
            SITE.mkdir(parents=True, exist_ok=True)
            run(["git", "init", "-b", "main"], cwd=SITE)
            run(["git", "remote", "add", "origin",
                 f"https://github.com/{OWNER}/{args.repo}.git"], cwd=SITE)

    print("3/4 Copying the build...")
    for child in SITE.iterdir():
        if child.name == ".git":
            continue
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    shutil.copytree(dist, SITE, dirs_exist_ok=True)
    (SITE / ".nojekyll").write_text("", encoding="utf-8")

    run(["git", "add", "-A"], cwd=SITE)
    changed = subprocess.run(["git", "diff", "--cached", "--quiet"],
                             cwd=SITE).returncode != 0
    if changed:
        run(["git", "-c", "user.name=Parth Agarwal",
             "-c", "user.email=noreply@github.com",
             "commit", "-q", "-m", "Publish site"], cwd=SITE)
        run(["git", "push", "-u", "origin", "main"], cwd=SITE)
    else:
        print("  (no changes since last publish)")

    print("4/4 Enabling GitHub Pages...")
    subprocess.run(
        ["gh", "api", "-X", "POST", f"repos/{OWNER}/{args.repo}/pages",
         "-f", "source[branch]=main", "-f", "source[path]=/"],
        capture_output=True, text=True, shell=(os.name == "nt"),
    )  # 409 if already enabled; that's fine

    url = f"https://{OWNER.lower()}.github.io/{args.repo}/"
    print(f"\nURL: {url}")
    if args.preview:
        print("PREVIEW build: do not send this link to participants until a data "
              "sink and contact details are configured and you republish.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
