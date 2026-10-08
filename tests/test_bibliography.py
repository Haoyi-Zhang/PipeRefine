import copy
import csv
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.bibliography_check import (
    BibEntry, BibliographyError, citation_sequence, parse_bibtex,
    read_audit, read_counts, validate,
)


class BibliographyAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = parse_bibtex((ROOT / "literature/references.bib").read_text(encoding="utf-8"))
        cls.counts = read_counts(ROOT / "literature/citation-counts.csv")
        cls.audit = read_audit(ROOT / "literature/bibliography-audit.csv")

    def test_retained_bibliography_passes(self):
        summary = validate(self.entries, self.counts, self.audit)
        self.assertEqual(summary["entries"], 69)
        self.assertEqual(summary["cited_entries"], 69)
        self.assertGreaterEqual(summary["doi_entries"], 60)

    def test_minimum_reference_count_is_enforced(self):
        with self.assertRaises(BibliographyError):
            validate(self.entries[:54], self.counts, self.audit, expected_entries=None)

    def test_uncited_entry_is_rejected(self):
        counts = dict(self.counts)
        counts["lilac"] = 0
        with self.assertRaises(BibliographyError):
            validate(self.entries, counts, self.audit)

    def test_duplicate_stable_locator_is_rejected(self):
        entries = copy.deepcopy(self.entries)
        entries[1].fields["doi"] = entries[0].fields["doi"]
        entries[1].fields.pop("url", None)
        with self.assertRaises(BibliographyError):
            validate(entries, self.counts, self.audit)

    def test_missing_stable_locator_is_rejected(self):
        entries = copy.deepcopy(self.entries)
        entries[0].fields.pop("doi", None)
        entries[0].fields.pop("url", None)
        with self.assertRaises(BibliographyError):
            validate(entries, self.counts, self.audit)

    def test_high_risk_metadata_mutation_is_rejected(self):
        for key,field in (("anvil","author"),("cosa","author"),("omega","doi")):
            with self.subTest(key=key,field=field):
                entries = copy.deepcopy(self.entries)
                entry = next(entry for entry in entries if entry.key == key)
                entry.fields[field] = "Incorrect Metadata"
                audit=copy.deepcopy(self.audit)
                if field=="doi":
                    audit[key]["stable_identifier"]="doi:Incorrect Metadata"
                with self.assertRaises(BibliographyError):
                    validate(entries, self.counts, audit)

    def test_audit_key_mismatch_is_rejected(self):
        audit = dict(self.audit)
        audit.pop("lilac")
        with self.assertRaises(BibliographyError):
            validate(self.entries, self.counts, audit)

    def test_parser_and_citation_extraction_preserve_nested_braces(self):
        sample = r'''@article{x,
 author={A. Author}, title={{ABC}: $10^{20}$ States},
 journal={Journal}, year={2020}, doi={10.1/example}
}'''
        entries = parse_bibtex(sample)
        self.assertEqual(entries[0].fields["title"], r"{ABC}: $10^{20}$ States")
        self.assertEqual(citation_sequence(r"A~\cite{x,y}; B~\cite{x}."), ["x", "y", "x"])


if __name__ == "__main__":
    unittest.main()
