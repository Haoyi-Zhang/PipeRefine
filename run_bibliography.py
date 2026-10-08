#!/usr/bin/env python3
"""Run the retained bibliography audit.

SPDX-License-Identifier: MIT
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from src.bibliography_check import parse_bibtex, read_audit, read_counts, validate, venue, locator

ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "bibliography-results")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    entries = parse_bibtex((ROOT / "literature/references.bib").read_text(encoding="utf-8"))
    counts = read_counts(ROOT / "literature/citation-counts.csv")
    sequence = [line.strip() for line in (ROOT / "literature/manuscript-citations.txt").read_text(encoding="utf-8").splitlines() if line.strip()]
    if dict(Counter(sequence)) != counts:
        raise SystemExit("retained citation sequence does not reproduce citation counts")
    audit = read_audit(ROOT / "literature/bibliography-audit.csv")
    summary = validate(entries, counts, audit)
    if args.check_only:
        retained = json.loads((ROOT / "bibliography-results/summary.json").read_text(encoding="utf-8"))
        if summary != retained:
            raise SystemExit("retained bibliography summary differs")
        print(json.dumps(summary, indent=2, sort_keys=True))
        return

    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    with (args.output / "entries.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["key", "entry_type", "year", "venue", "stable_identifier", "citation_count"]
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for entry in entries:
            writer.writerow({
                "key": entry.key,
                "entry_type": entry.entry_type,
                "year": entry.fields["year"],
                "venue": venue(entry),
                "stable_identifier": locator(entry),
                "citation_count": counts[entry.key],
            })
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
