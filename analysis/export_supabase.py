#!/usr/bin/env python3
"""
Split a Supabase export into the per-session JSON files prepare_data.py expects.

Accepts either the dashboard's CSV export (a `data` column holding JSON) or a raw
JSON array from the REST API.

Usage:
    python analysis/export_supabase.py --csv sessions_rows.csv --out data/raw
    python analysis/export_supabase.py --json sessions.json     --out data/raw
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def unwrap(row: dict) -> dict | None:
    """Supabase rows nest the payload under `data`; accept a bare payload too."""
    if isinstance(row.get("data"), dict) and "meta" in row["data"]:
        return row["data"]
    if isinstance(row.get("data"), str):
        try:
            inner = json.loads(row["data"])
        except json.JSONDecodeError:
            return None
        return inner if "meta" in inner else None
    return row if "meta" in row else None


def main() -> None:
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv")
    src.add_argument("--json")
    ap.add_argument("--out", default="data/raw")
    ap.add_argument(
        "--keep-incomplete", action="store_true",
        help="also write sessions with no completed_at (default: skip them)",
    )
    args = ap.parse_args()

    if args.csv:
        df = pd.read_csv(args.csv)
        rows = df.to_dict("records")
    else:
        rows = json.loads(Path(args.json).read_text(encoding="utf-8"))
        if isinstance(rows, dict):
            rows = [rows]

    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    written, skipped, dupes = 0, 0, 0
    seen: dict[str, int] = {}

    for row in rows:
        payload = unwrap(row)
        if payload is None:
            skipped += 1
            continue
        if not args.keep_incomplete and not payload.get("completedAt"):
            skipped += 1
            continue

        pid = payload.get("meta", {}).get("participantId", f"unknown{written}")
        seen[pid] = seen.get(pid, 0) + 1
        # A participant can submit twice (browser refresh, Prolific return-and-retake).
        # Keep every copy under a distinct filename rather than silently overwriting,
        # and report it -- you must decide which submission counts, not the filesystem.
        name = pid if seen[pid] == 1 else f"{pid}__dup{seen[pid]}"
        if seen[pid] > 1:
            dupes += 1

        (out_dir / f"{name}.json").write_text(
            json.dumps(payload, indent=1), encoding="utf-8"
        )
        written += 1

    print(f"Wrote {written} sessions -> {out_dir}")
    if skipped:
        print(f"Skipped {skipped} rows (incomplete or unparseable)")
    if dupes:
        print(
            f"\n!! {dupes} duplicate submission(s) detected. Files are suffixed __dupN.\n"
            "   Decide explicitly which submission to keep (normally the first "
            "completed one) and delete the rest BEFORE running prepare_data.py:"
        )
        for pid, n in seen.items():
            if n > 1:
                print(f"     {pid}: {n} submissions")
    if written == 0:
        sys.exit("No sessions written -- check the input file format.")


if __name__ == "__main__":
    main()
