#!/usr/bin/env python3
"""Run the independent exhaustive one-port micro-model. SPDX-License-Identifier: MIT."""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import resource
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from exhaustive_context import exhaustive_campaign


def dump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "micro-results")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (110, 110))
    if hasattr(os, "sched_setaffinity"):
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})

    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    profiles, clients, rows, disagreements = exhaustive_campaign()
    summary = {
        "profiles": len(profiles),
        "ordered_profile_pairs": len(rows),
        "enumerated_clients": len(clients),
        "criterion_true_pairs": sum(row["criterion"] for row in rows),
        "contextual_refinement_pairs": sum(row["contextual_refinement"] for row in rows),
        "disagreements": len(disagreements),
        "scope": "one input port, one output port, ages 0..2, gaps 1..2",
        "independence": "does not import timeline.py or timeline_check.py",
    }
    args.output.mkdir(parents=True, exist_ok=True)
    profiles_rows = [{
        "profile": profile.identifier,
        "gap": profile.gap,
        "reads": " ".join(map(str, sorted(profile.reads))),
        "writes": " ".join(map(str, sorted(profile.writes))),
    } for profile in profiles]

    if args.check_only:
        retained_summary = json.loads((args.output / "summary.json").read_text())
        # Measured timing is intentionally not in summary.json.
        if retained_summary != summary:
            raise RuntimeError("retained exhaustive summary differs")
        with (args.output / "profiles.csv").open(newline="") as handle:
            retained_profiles = list(csv.DictReader(handle))
        expected_profiles = [{key: str(value) for key, value in row.items()} for row in profiles_rows]
        if retained_profiles != expected_profiles:
            raise RuntimeError("retained exhaustive profile catalog differs")
        with (args.output / "pairs.csv").open(newline="") as handle:
            retained_pairs = list(csv.DictReader(handle))
        expected_pairs = [{key: str(value) for key, value in row.items()} for row in rows]
        if retained_pairs != expected_pairs:
            raise RuntimeError("retained exhaustive pair table differs")
    else:
        with (args.output / "profiles.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(profiles_rows[0]))
            writer.writeheader(); writer.writerows(profiles_rows)
        with (args.output / "pairs.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)
        dump(args.output / "summary.json", summary)
        dump(args.output / "measurements.json", {
            "wall_seconds": time.perf_counter() - started_wall,
            "cpu_seconds": time.process_time() - started_cpu,
            "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "workers": 1,
        })
    if disagreements:
        raise RuntimeError(f"criterion/context disagreement: {disagreements[0]}")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
