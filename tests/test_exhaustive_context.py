import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from exhaustive_context import (
    Client, Profile, client_legal, direct_criterion, enumerate_clients,
    enumerate_profiles, exhaustive_campaign,
)


class ExhaustiveContextTests(unittest.TestCase):
    def test_profile_and_pair_counts(self):
        profiles = enumerate_profiles()
        self.assertEqual(len(profiles), 52)
        self.assertEqual(len(profiles) ** 2, 2704)

    def test_client_universe_is_nontrivial(self):
        clients = enumerate_clients()
        self.assertGreater(len(clients), 1000)
        self.assertTrue(any(client.launches == (0, 1) for client in clients))
        self.assertTrue(any(client.launches == (0, 2) for client in clients))

    def test_exhaustive_context_matches_criterion(self):
        profiles, clients, rows, disagreements = exhaustive_campaign()
        self.assertEqual(len(profiles), 52)
        self.assertGreater(len(clients), 1000)
        self.assertEqual(len(rows), 2704)
        self.assertEqual(disagreements, [])

    def test_each_variance_direction_has_explicit_client(self):
        # Gap: old client launches on consecutive cycles.
        spec = Profile(1, frozenset(), frozenset())
        impl = Profile(2, frozenset(), frozenset())
        gap_client = Client((0, 1), frozenset(), frozenset())
        self.assertTrue(client_legal(spec, gap_client))
        self.assertFalse(client_legal(impl, gap_client))
        self.assertFalse(direct_criterion(impl, spec))

        # Read: replacement asks for an old client drive that was optional.
        spec = Profile(1, frozenset(), frozenset())
        impl = Profile(1, frozenset({0}), frozenset())
        read_client = Client((0,), frozenset(), frozenset())
        self.assertTrue(client_legal(spec, read_client))
        self.assertFalse(client_legal(impl, read_client))

        # Write: old client samples an age withdrawn by the replacement.
        spec = Profile(1, frozenset(), frozenset({0}))
        impl = Profile(1, frozenset(), frozenset())
        write_client = Client((0,), frozenset(), frozenset({(0, 0)}))
        self.assertTrue(client_legal(spec, write_client))
        self.assertFalse(client_legal(impl, write_client))


if __name__ == "__main__":
    unittest.main()
