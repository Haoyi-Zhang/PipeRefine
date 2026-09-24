"""Port-separated timeline contracts and finite I/O-game translations.

A profile may pipeline transactions: an event age may be greater than the
minimum re-launch gap.  The declared fragment instead requires, independently
for every physical port, that the span between its earliest and latest event is
strictly smaller than the gap.  This makes launch-indexed events project
injectively to port/cycle events for every legal launch schedule.

The producer uses a compact age automaton when all events precede the next
launch.  Pipelined cases use a launch-history automaton whose actions retain the
transaction age.  timeline_check.py independently validates profiles, clients,
and arithmetic.

SPDX-License-Identifier: MIT
"""
from copy import deepcopy
from itertools import combinations
from domain import expression, valuations


def _or(parts):
    if not parts:
        return False
    if len(parts) == 1:
        return parts[0]
    return ['or', *parts]


def _contains(intervals, age):
    return _or([['and', ['<=', lo, age], ['<', age, hi]] for lo, hi in intervals])


def profile_sets(profile, valuation):
    """Evaluate one profile to a gap and finite relative-age sets."""
    gap = expression(profile['gap'], valuation)

    def ports(name):
        return {
            port: frozenset(
                age
                for lo, hi in ranges
                for age in range(expression(lo, valuation), expression(hi, valuation))
            )
            for port, ranges in profile.get(name, {}).items()
        }

    return {'gap': gap, 'reads': ports('reads'), 'writes': ports('writes')}


def port_separated(profile, valuation):
    """Producer-side predicate for the per-port span condition."""
    evaluated = profile_sets(profile, valuation)
    for kind in ('reads', 'writes'):
        for ages in evaluated[kind].values():
            if ages and max(ages) - min(ages) >= evaluated['gap']:
                return False
    return True


def refines_at(case, valuation):
    """Complete criterion for the declared launch-indexed timeline fragment."""
    impl = profile_sets(case['implementation'], valuation)
    spec = profile_sets(case['specification'], valuation)
    if impl['gap'] > spec['gap']:
        return False
    for port in set(impl['reads']) | set(spec['reads']):
        if not impl['reads'].get(port, frozenset()) <= spec['reads'].get(port, frozenset()):
            return False
    for port in set(impl['writes']) | set(spec['writes']):
        if not spec['writes'].get(port, frozenset()) <= impl['writes'].get(port, frozenset()):
            return False
    return True


def safe_valuation_ids(case):
    return [k for k, valuation in enumerate(valuations(case)) if refines_at(case, valuation)]


def _all_events_before_relaunch(case, key, values):
    for valuation in values:
        profile = profile_sets(case[key], valuation)
        for kind in ('reads', 'writes'):
            for ages in profile[kind].values():
                if ages and max(ages) >= profile['gap']:
                    return False
    return True


def translation_mode(case):
    """Select one label-compatible translation for both sides of a case."""
    values = valuations(case)
    if all(_all_events_before_relaunch(case, key, values)
           for key in ('implementation', 'specification')):
        return 'age'
    return 'history'


def _port_universe(case):
    reads = sorted(set(case['implementation'].get('reads', {})) |
                   set(case['specification'].get('reads', {})))
    writes = sorted(set(case['implementation'].get('writes', {})) |
                    set(case['specification'].get('writes', {})))
    return reads, writes


def _translate_age(case, key):
    """Compact quotient for profiles whose events all precede re-launch."""
    profile = case[key]
    horizon = case['horizon']
    all_reads, all_writes = _port_universe(case)
    edges = []
    for age in range(horizon + 1):
        edges.append({'from': age, 'to': min(age + 1, horizon),
                      'label': 'tick', 'kind': 'in', 'guard': True})
        edges.append({'from': age, 'to': 0, 'label': 'launch', 'kind': 'in',
                      'guard': ['<=', deepcopy(profile['gap']), age]})
        for port in all_writes:
            guard = _contains(deepcopy(profile.get('writes', {}).get(port, [])), age)
            edges.append({'from': age, 'to': age, 'label': 'sample:' + port,
                          'kind': 'in', 'guard': guard})
        for port in all_reads:
            guard = _contains(deepcopy(profile.get('reads', {}).get(port, [])), age)
            edges.append({'from': age, 'to': age, 'label': 'need:' + port,
                          'kind': 'out', 'guard': guard})
    return {'states': horizon + 1, 'initial': horizon, 'edges': edges,
            'encoding': 'quiescent-age'}


def _history_state_space(case, key):
    """Enumerate a valuation-independent superset of reachable launch histories."""
    values = valuations(case)
    gaps = [profile_sets(case[key], valuation)['gap'] for valuation in values]
    minimum_gap = min(gaps, default=1)
    horizon = case['horizon']
    states = []
    for bits in range(1 << (horizon + 1)):
        ages = tuple(age for age in range(horizon + 1) if bits & (1 << age))
        if all(b - a >= minimum_gap for a, b in combinations(ages, 2)):
            states.append(ages)
    states.sort(key=lambda ages: (len(ages), ages))
    if len(states) > 48:
        raise ValueError(
            f"history translation for {case['id']}:{key} needs {len(states)} states; "
            "the bounded artifact permits at most 48"
        )
    return states, minimum_gap


def _translate_history(case, key):
    """Translate overlapping pipelines while preserving transaction ages in labels."""
    profile = case[key]
    horizon = case['horizon']
    all_reads, all_writes = _port_universe(case)
    states, minimum_gap = _history_state_space(case, key)
    index = {state: k for k, state in enumerate(states)}
    edges = []
    for sid, state in enumerate(states):
        tick_target = tuple(age + 1 for age in state if age + 1 <= horizon)
        edges.append({'from': sid, 'to': index[tick_target],
                      'label': 'tick', 'kind': 'in', 'guard': True})

        # If the newest active transaction is younger than the family-wide
        # minimum gap, the launch guard is false for every retained valuation;
        # omit the unreachable target rather than adding a dead edge.
        if not state or min(state) >= minimum_gap:
            launch_target = tuple(sorted((0, *state)))
            guard = True if not state else ['<=', deepcopy(profile['gap']), min(state)]
            edges.append({'from': sid, 'to': index[launch_target],
                          'label': 'launch', 'kind': 'in', 'guard': guard})

        for age in state:
            for port in all_writes:
                guard = _contains(deepcopy(profile.get('writes', {}).get(port, [])), age)
                edges.append({'from': sid, 'to': sid,
                              'label': f'sample:{port}@{age}',
                              'kind': 'in', 'guard': guard})
            for port in all_reads:
                guard = _contains(deepcopy(profile.get('reads', {}).get(port, [])), age)
                edges.append({'from': sid, 'to': sid,
                              'label': f'need:{port}@{age}',
                              'kind': 'out', 'guard': guard})
    return {'states': len(states), 'initial': index[()], 'edges': edges,
            'encoding': 'launch-history',
            'history_states': [list(state) for state in states]}


def translate_profile(case, key, mode=None):
    mode = translation_mode(case) if mode is None else mode
    if mode == 'age':
        return _translate_age(case, key)
    if mode == 'history':
        return _translate_history(case, key)
    raise ValueError('unknown timeline translation mode')


def translate_case(case):
    mode = translation_mode(case)
    return {
        'id': case['id'],
        'group': 'timeline-' + case['group'],
        'parameters': deepcopy(case['parameters']),
        'assumption': deepcopy(case['assumption']),
        'environment_inputs': {},
        'implementation': translate_profile(case, 'implementation', mode),
        'specification': translate_profile(case, 'specification', mode),
        'translation_mode': mode,
    }


def _tagged_drives(spec, launches):
    drives = []
    for launch in launches:
        for port, ages in spec['reads'].items():
            for age in sorted(ages):
                drives.append({'port': port, 'launch': launch, 'age': age,
                               'time': launch + age})
    return sorted(drives, key=lambda item: (item['time'], item['port'],
                                            item['launch'], item['age']))


def canonical_counterexample(case, valuation):
    """Return a shortest launch-indexed client for a failed criterion.

    Tags prevent an implementation from borrowing a same-cycle value belonging
    to another transaction.  Port separation guarantees that the specification's
    tagged events have an injective physical port/cycle projection.
    """
    impl = profile_sets(case['implementation'], valuation)
    spec = profile_sets(case['specification'], valuation)
    candidates = []
    if impl['gap'] > spec['gap']:
        candidates.append((spec['gap'], 0, 'gap', '', spec['gap']))
    for port in sorted(set(impl['reads']) | set(spec['reads'])):
        for age in sorted(impl['reads'].get(port, frozenset()) -
                          spec['reads'].get(port, frozenset())):
            candidates.append((age, 1, 'read', port, age))
    for port in sorted(set(impl['writes']) | set(spec['writes'])):
        for age in sorted(spec['writes'].get(port, frozenset()) -
                          impl['writes'].get(port, frozenset())):
            candidates.append((age, 2, 'write', port, age))
    if not candidates:
        return None
    first_cycle, _, kind, port, age = min(candidates)
    launches = [0, spec['gap']] if kind == 'gap' else [0]
    samples = []
    if kind == 'write':
        samples.append({'port': port, 'launch': 0, 'age': age, 'time': age})
    return {
        'kind': kind,
        'port': port or None,
        'age': age,
        'first_violation_cycle': first_cycle,
        'launches': launches,
        'drives': _tagged_drives(spec, launches),
        'samples': samples,
        'explanation': {
            'gap': 'the second specification-legal launch is too early for the replacement',
            'read': 'the replacement requires a transaction-tagged input age absent from the specification',
            'write': 'the client samples a specification-guaranteed transaction age absent from the replacement',
        }[kind],
    }
