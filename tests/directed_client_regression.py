"""Standalone directed-port client-domain regressions. SPDX-License-Identifier: MIT."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from check import Invalid
from timeline_check import (client_legal, directed_ports, check_counterexample,
                            replay_first_violation)


class DirectedClientTests(unittest.TestCase):
    def setUp(self):
        self.case = {
            'implementation': {'gap': 1, 'reads': {'x': [[1, 2]], 'optional': []},
                               'writes': {'y': [[2, 3]]}},
            'specification': {'gap': 1, 'reads': {}, 'writes': {'y': [[2, 3]]}},
        }
        self.client = {'launches': [0], 'drives': [], 'samples': [],
                       'kind': 'read', 'port': 'x', 'age': 1,
                       'first_violation_cycle': 1}

    def test_optional_input_without_required_ages_is_legal(self):
        self.client['drives'] = [{'port': 'optional', 'launch': 0, 'age': 0, 'time': 0}]
        ports = directed_ports(self.case)
        self.assertTrue(client_legal(self.case['specification'], {}, self.client, ports))
        check_counterexample(self.case, {}, self.client, 3)

    def test_output_and_unknown_drives_are_rejected(self):
        for port in ('y', 'unknown'):
            with self.subTest(port=port):
                self.client['drives'] = [{'port': port, 'launch': 0, 'age': 0, 'time': 0}]
                self.assertFalse(client_legal(self.case['specification'], {}, self.client,
                                              directed_ports(self.case)))
                with self.assertRaises(Invalid):
                    check_counterexample(self.case, {}, self.client, 3)
                with self.assertRaises(Invalid):
                    replay_first_violation(self.case, {}, self.client)

    def test_sample_direction_and_guaranteed_output(self):
        ports = directed_ports(self.case)
        for port in ('x', 'unknown'):
            self.client['samples'] = [{'port': port, 'launch': 0, 'age': 2, 'time': 2}]
            self.assertFalse(client_legal(self.case['specification'], {}, self.client, ports))
        self.client['samples'] = [{'port': 'y', 'launch': 0, 'age': 2, 'time': 2}]
        self.assertTrue(client_legal(self.case['specification'], {}, self.client, ports))

    def test_standalone_empty_age_input_key_remains_declared(self):
        profile = {'gap': 1, 'reads': {'optional': []}, 'writes': {}}
        self.client['drives'] = [{'port': 'optional', 'launch': 0, 'age': 0, 'time': 0}]
        self.assertTrue(client_legal(profile, {}, self.client))


if __name__ == '__main__':
    unittest.main()
