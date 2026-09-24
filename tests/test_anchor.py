"""Published-declaration normalization and boundary controls. SPDX-License-Identifier: MIT."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from check import Invalid
from generate_anchor import all_anchor_records
from timeline_check import validate_timeline, direct_refines


RECORDS = {record['id']: record for record in all_anchor_records()}


class AnchorNormalization(unittest.TestCase):
    def test_input_files_exact_rebuild(self):
        files = {path.stem: path for path in (ROOT / 'anchor-inputs').glob('*.json')}
        self.assertEqual(set(files), set(RECORDS))
        for name, record in RECORDS.items():
            self.assertEqual(files[name].read_text(),
                             json.dumps(record, indent=2, sort_keys=True) + '\n')

    def test_five_reusable_declarations_inside_fragment(self):
        supported = [record for record in RECORDS.values()
                     if record['expected_supported']]
        self.assertEqual(len(supported), 5)
        self.assertEqual(sum(len(validate_timeline(record)) for record in supported), 29)
        for record in supported:
            self.assertTrue(all(direct_refines(record, env)
                                for env in validate_timeline(record)))

    def test_wide_input_is_explicit_boundary(self):
        record = RECORDS['lilac-fpu-wide-input-boundary']
        self.assertFalse(record['expected_supported'])
        with self.assertRaises(Invalid):
            validate_timeline(record)

    def test_source_identity_is_bound(self):
        for record in RECORDS.values():
            self.assertEqual(record['source']['doi'], '10.1145/3779212.3790199')
            self.assertTrue(record['source']['locator'])
            self.assertGreaterEqual(record['source']['page'], 1)


if __name__ == '__main__':
    unittest.main()
