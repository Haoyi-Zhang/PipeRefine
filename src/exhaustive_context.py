"""Independent exhaustive micro-model for launch-indexed clients.

This module deliberately does not import ``timeline.py`` or
``timeline_check.py``.  It enumerates every port-separated profile with one
input port, one output port, ages 0..2, and gap 1 or 2; then it enumerates the
finite client universe needed to distinguish every ordered profile pair in
that bounded model.

SPDX-License-Identifier: MIT
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product
from typing import FrozenSet, Iterable, Sequence, Tuple

AgeSet = FrozenSet[int]
Tag = Tuple[int, int]  # (launch index, age)


@dataclass(frozen=True, order=True)
class Profile:
    gap: int
    reads: AgeSet
    writes: AgeSet

    @property
    def identifier(self) -> str:
        r = "-".join(map(str, sorted(self.reads))) or "none"
        w = "-".join(map(str, sorted(self.writes))) or "none"
        return f"g{self.gap}-r{r}-w{w}"


@dataclass(frozen=True)
class Client:
    launches: Tuple[int, ...]
    drives: FrozenSet[Tag]
    samples: FrozenSet[Tag]

    @property
    def identifier(self) -> str:
        def show(tags: Iterable[Tag]) -> str:
            ordered = sorted(tags)
            return ";".join(f"{j}@{a}" for j, a in ordered) or "none"
        ls = "-".join(map(str, self.launches)) or "none"
        return f"L={ls}|D={show(self.drives)}|S={show(self.samples)}"


def _powerset(items: Sequence[Tag]) -> Iterable[FrozenSet[Tag]]:
    for size in range(len(items) + 1):
        for chosen in combinations(items, size):
            yield frozenset(chosen)


def _collision_free(tags: Iterable[Tag], launches: Sequence[int]) -> bool:
    physical = set()
    for launch_index, age in tags:
        slot = launches[launch_index] + age
        if slot in physical:
            return False
        physical.add(slot)
    return True


def admissible_age_sets(gap: int, horizon: int = 2) -> Tuple[AgeSet, ...]:
    """All sets whose span is strictly smaller than ``gap``."""
    ages = tuple(range(horizon + 1))
    sets = []
    for mask in range(1 << len(ages)):
        selected = frozenset(age for bit, age in enumerate(ages) if mask & (1 << bit))
        if not selected or max(selected) - min(selected) < gap:
            sets.append(selected)
    return tuple(sorted(sets, key=lambda values: (len(values), tuple(sorted(values)))))


def enumerate_profiles() -> Tuple[Profile, ...]:
    profiles = []
    for gap in (1, 2):
        sets = admissible_age_sets(gap)
        profiles.extend(Profile(gap, reads, writes) for reads, writes in product(sets, repeat=2))
    return tuple(sorted(profiles))


def enumerate_clients(horizon: int = 2) -> Tuple[Client, ...]:
    """Enumerate a complete distinguishing universe for this micro-model.

    One launch exposes read/write variance.  Two launches at distances one and
    two expose the only possible gap mismatch.  All collision-free drive and
    sample subsets are retained rather than using the theorem's canonical
    witness construction.
    """
    clients = [Client((), frozenset(), frozenset())]
    for launches in ((0,), (0, 1), (0, 2)):
        tags = tuple((j, age) for j in range(len(launches)) for age in range(horizon + 1))
        subsets = tuple(values for values in _powerset(tags) if _collision_free(values, launches))
        clients.extend(Client(tuple(launches), drives, samples)
                       for drives, samples in product(subsets, repeat=2))
    return tuple(clients)


def client_legal(profile: Profile, client: Client) -> bool:
    if any(right - left < profile.gap
           for left, right in zip(client.launches, client.launches[1:])):
        return False
    required = frozenset((j, age)
                         for j in range(len(client.launches))
                         for age in profile.reads)
    if not required <= client.drives:
        return False
    if any(age not in profile.writes for _, age in client.samples):
        return False
    return True


def direct_criterion(implementation: Profile, specification: Profile) -> bool:
    return (implementation.gap <= specification.gap
            and implementation.reads <= specification.reads
            and specification.writes <= implementation.writes)


def legal_client_mask(profile: Profile, clients: Sequence[Client]) -> int:
    mask = 0
    for index, client in enumerate(clients):
        if client_legal(profile, client):
            mask |= 1 << index
    return mask


def exhaustive_campaign():
    profiles = enumerate_profiles()
    clients = enumerate_clients()
    masks = {profile: legal_client_mask(profile, clients) for profile in profiles}
    rows = []
    disagreements = []
    for implementation in profiles:
        for specification in profiles:
            criterion = direct_criterion(implementation, specification)
            # Every S-legal client must be I-legal.
            violating = masks[specification] & ~masks[implementation]
            semantic = violating == 0
            witness_index = None if semantic else (violating & -violating).bit_length() - 1
            row = {
                "implementation": implementation.identifier,
                "specification": specification.identifier,
                "criterion": int(criterion),
                "contextual_refinement": int(semantic),
                "witness_client": "" if witness_index is None else clients[witness_index].identifier,
            }
            rows.append(row)
            if criterion != semantic:
                disagreements.append(row)
    return profiles, clients, rows, disagreements
