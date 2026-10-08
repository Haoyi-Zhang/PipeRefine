#!/usr/bin/env python3
"""Deterministic bibliography and manuscript-citation consistency checks.

The checker deliberately validates structure, cross-file agreement, stable
locators, citation coverage, and a set of high-risk metadata corrections.  It
does not claim to replace external scholarly review or a live DOI resolver.

SPDX-License-Identifier: MIT
"""
from __future__ import annotations

import csv
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


class BibliographyError(ValueError):
    """Raised when retained bibliographic evidence is inconsistent."""


@dataclass(frozen=True)
class BibEntry:
    entry_type: str
    key: str
    fields: dict[str, str]


def _balanced_body(text: str, start: int) -> tuple[str, int]:
    depth = 1
    i = start
    while i < len(text):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i], i + 1
        i += 1
    raise BibliographyError("unterminated BibTeX entry")


def _split_top_level(text: str) -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    quoted = False
    escaped = False
    for i, ch in enumerate(text):
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == '"' and depth == 0:
            quoted = not quoted
        elif not quoted:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            elif ch == "," and depth == 0:
                parts.append(text[start:i].strip())
                start = i + 1
    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def _strip_value(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and ((value[0] == "{" and value[-1] == "}") or
                            (value[0] == '"' and value[-1] == '"')):
        return value[1:-1].strip()
    return value


def parse_bibtex(text: str) -> list[BibEntry]:
    entries: list[BibEntry] = []
    pos = 0
    head = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", re.I)
    while True:
        match = head.search(text, pos)
        if match is None:
            break
        body, pos = _balanced_body(text, match.end())
        fields: dict[str, str] = {}
        for part in _split_top_level(body):
            if not part:
                continue
            if "=" not in part:
                raise BibliographyError(f"malformed field in {match.group(2)}: {part}")
            name, raw = part.split("=", 1)
            key = name.strip().lower()
            if key in fields:
                raise BibliographyError(f"duplicate field {key} in {match.group(2)}")
            fields[key] = _strip_value(raw)
        entries.append(BibEntry(match.group(1).lower(), match.group(2), fields))
    if not entries:
        raise BibliographyError("no BibTeX entries found")
    return entries


def citation_sequence(tex: str) -> list[str]:
    keys: list[str] = []
    for match in re.finditer(r"\\cite\s*\{([^}]*)\}", tex):
        keys.extend(key.strip() for key in match.group(1).split(",") if key.strip())
    return keys


def read_counts(path: Path) -> dict[str, int]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {"key", "count"}
    if not rows or set(rows[0]) != required:
        raise BibliographyError("citation-counts.csv must contain key,count")
    result: dict[str, int] = {}
    for row in rows:
        key = row["key"]
        if key in result:
            raise BibliographyError(f"duplicate citation count for {key}")
        try:
            result[key] = int(row["count"])
        except ValueError as exc:
            raise BibliographyError(f"non-integer citation count for {key}") from exc
    return result


def read_audit(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    expected = {
        "key", "title", "year", "venue", "stable_identifier",
        "verification_url", "verification_basis", "role"
    }
    if not rows or set(rows[0]) != expected:
        raise BibliographyError("bibliography-audit.csv has the wrong columns")
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        key = row["key"]
        if key in result:
            raise BibliographyError(f"duplicate audit row for {key}")
        result[key] = row
    return result


def locator(entry: BibEntry) -> str:
    if entry.fields.get("doi"):
        return "doi:" + entry.fields["doi"].lower()
    return "url:" + entry.fields.get("url", "")


def venue(entry: BibEntry) -> str:
    return (entry.fields.get("journal") or entry.fields.get("booktitle") or
            entry.fields.get("institution") or "")


def _require_equal(entry: BibEntry, expected: dict[str, str]) -> None:
    for field, value in expected.items():
        actual = entry.entry_type if field == "entry_type" else entry.fields.get(field, "")
        if actual != value:
            raise BibliographyError(
                f"high-risk metadata mismatch for {entry.key}.{field}: {actual!r} != {value!r}"
            )


def validate(entries: list[BibEntry], counts: dict[str, int],
             audit: dict[str, dict[str, str]], minimum_entries: int = 55,
             expected_entries: int | None = 69) -> dict[str, object]:
    if len(entries) < minimum_entries:
        raise BibliographyError(f"bibliography has {len(entries)} entries; need at least {minimum_entries}")
    if expected_entries is not None and len(entries) != expected_entries:
        raise BibliographyError(f"bibliography has {len(entries)} entries; expected {expected_entries}")

    keys = [entry.key for entry in entries]
    if len(keys) != len(set(keys)):
        raise BibliographyError("duplicate BibTeX key")
    titles = [entry.fields.get("title", "").casefold() for entry in entries]
    if len(titles) != len(set(titles)):
        raise BibliographyError("duplicate title")

    required = {"author", "title", "year"}
    locators: list[str] = []
    for entry in entries:
        missing = required - set(entry.fields)
        if missing:
            raise BibliographyError(f"{entry.key} is missing {sorted(missing)}")
        if not venue(entry):
            raise BibliographyError(f"{entry.key} has no venue")
        loc = locator(entry)
        if loc in {"url:", "doi:"}:
            raise BibliographyError(f"{entry.key} lacks DOI or stable URL")
        if "example." in loc or "placeholder" in loc.lower() or "unknown" in loc.lower():
            raise BibliographyError(f"{entry.key} contains a placeholder locator")
        locators.append(loc)
    duplicates = [item for item, count in Counter(locators).items() if count > 1]
    if duplicates:
        raise BibliographyError(f"duplicate stable locator: {duplicates[0]}")

    key_set = set(keys)
    if set(counts) != key_set:
        missing = sorted(key_set - set(counts))
        extra = sorted(set(counts) - key_set)
        raise BibliographyError(f"citation inventory mismatch; missing={missing}, extra={extra}")
    uncited = sorted(key for key, count in counts.items() if count < 1)
    if uncited:
        raise BibliographyError(f"uncited references: {uncited}")
    if set(audit) != key_set:
        missing = sorted(key_set - set(audit))
        extra = sorted(set(audit) - key_set)
        raise BibliographyError(f"audit-key mismatch; missing={missing}, extra={extra}")

    by_key = {entry.key: entry for entry in entries}
    for key, entry in by_key.items():
        row = audit[key]
        if row["title"] != entry.fields["title"]:
            raise BibliographyError(f"audit title mismatch for {key}")
        if row["year"] != entry.fields["year"]:
            raise BibliographyError(f"audit year mismatch for {key}")
        if row["venue"] != venue(entry):
            raise BibliographyError(f"audit venue mismatch for {key}")
        retained_locator = row["stable_identifier"]
        expected_locator = locator(entry)
        if expected_locator.startswith("doi:"):
            locator_matches = retained_locator.lower() == expected_locator.lower()
        else:
            locator_matches = retained_locator == expected_locator
        if not locator_matches:
            raise BibliographyError(f"audit locator mismatch for {key}")
        if not row["verification_url"].startswith("https://"):
            raise BibliographyError(f"audit URL is not HTTPS for {key}")
        if not row["verification_basis"] or not row["role"]:
            raise BibliographyError(f"incomplete audit rationale for {key}")

    known = {
        "lilac": {"year": "2026", "pages": "1382--1395", "doi": "10.1145/3779212.3790199"},
        "anvil": {
            "entry_type": "inproceedings",
            "author": "Jason Zhijingcheng Yu and Aditya Ranjan Jha and Umang Mathur and Trevor E. Carlson and Prateek Saxena",
            "year": "2026", "pages": "110--136", "doi": "10.1145/3779212.3790125"
        },
        "spade": {"entry_type": "article", "year": "2026", "doi": "10.1145/3793550"},
        "learningag": {
            "entry_type": "article", "journal": "Formal Methods in System Design",
            "volume": "32", "number": "3", "pages": "175--205", "doi": "10.1007/s10703-008-0049-6"
        },
        "behavioraltypes": {
            "entry_type": "article", "journal": "Formal Aspects of Computing",
            "volume": "16", "number": "3", "pages": "210--237", "doi": "10.1007/s00165-004-0043-8"
        },
        "relations": {
            "entry_type": "inproceedings", "booktitle": "Integrated Formal Methods",
            "year": "2019", "pages": "246--264", "doi": "10.1007/978-3-030-34968-4_14"
        },
        "interfacebased": {"doi": "10.1145/266021.266060"},
        "cleaveland": {"doi": "10.1007/BFb0023750"},
        "pixley": {"doi": "10.1109/43.180261"},
        "cosa": {
            "author": "Cristian Mattarei and Makai Mann and Clark Barrett and Ross G. Daly and Dillon Huff and Pat Hanrahan",
            "year": "2018", "doi": "10.23919/FMCAD.2018.8603014",
        },
        "omega": {
            "author": "William Pugh", "title": "A Practical Algorithm for Exact Array Dependence Analysis",
            "year": "1992", "journal": "Communications of the ACM",
            "volume": "35", "number": "8", "pages": "102--114",
            "doi": "10.1145/135226.135233",
        },
    }
    for key, expected in known.items():
        _require_equal(by_key[key], expected)
    if "arxiv" in venue(by_key["anvil"]).casefold() or "arxiv" in venue(by_key["lilac"]).casefold():
        raise BibliographyError("published Lilac/Anvil records must not remain arXiv-only")

    return {
        "status": "pass",
        "entries": len(entries),
        "minimum_required": minimum_entries,
        "cited_entries": sum(1 for count in counts.values() if count > 0),
        "citation_occurrences": sum(counts.values()),
        "unique_stable_locators": len(set(locators)),
        "doi_entries": sum(1 for entry in entries if entry.fields.get("doi")),
        "url_only_entries": sum(1 for entry in entries if not entry.fields.get("doi")),
        "high_risk_metadata_checks": len(known),
        "external_resolution_note": "structural and retained-metadata audit; not a live resolver or independent novelty review",
    }


def write_counts(keys: Iterable[str], path: Path) -> None:
    counts = Counter(keys)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["key", "count"], lineterminator="\n")
        writer.writeheader()
        for key in sorted(counts):
            writer.writerow({"key": key, "count": counts[key]})
