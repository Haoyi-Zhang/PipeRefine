"""Independent validation for port-separated timelines and persisted tagged clients.

This module deliberately uses check.py's separately implemented arithmetic
rather than timeline.py/domain.py's evaluator.  It validates the complete
persisted launch/drive/sample record, replays the first absolute violation, and
checks launch-history actions without importing the producer translation.

SPDX-License-Identifier: MIT
"""
import itertools
from check import (Invalid, need, integer, predicate, validate_expression,
                   validate_predicate)


_KIND_ORDER = {'gap': 0, 'read': 1, 'write': 2}


def evaluated(profile, env):
    def ports(kind):
        out = {}
        for port, ranges in profile.get(kind, {}).items():
            ages = set()
            for lo, hi in ranges:
                ages.update(range(integer(lo, env), integer(hi, env)))
            out[port] = ages
        return out

    return {'gap': integer(profile['gap'], env),
            'reads': ports('reads'), 'writes': ports('writes')}


def port_separated(profile, env):
    """Check the declared per-port span inequality."""
    p = evaluated(profile, env)
    for kind in ('reads', 'writes'):
        for ages in p[kind].values():
            if ages and max(ages) - min(ages) >= p['gap']:
                return False
    return True


def collision_free(profile, env):
    """Exhaustively check two-launch physical collisions on each port.

    Any collision among a longer legal launch sequence has a colliding pair, so
    two launches suffice.  The loop is intentionally different from the span
    formula used by port_separated.
    """
    p = evaluated(profile, env)
    for kind in ('reads', 'writes'):
        for ages in p[kind].values():
            if not ages:
                continue
            for distance in range(p['gap'], max(ages) - min(ages) + 1):
                occupied = set()
                for launch in (0, distance):
                    for age in ages:
                        cycle = launch + age
                        if cycle in occupied:
                            return False
                        occupied.add(cycle)
    return True


def validate_timeline(case):
    need(type(case) is dict and type(case.get('id')) is str and case['id'], 'timeline id')
    horizon = case.get('horizon')
    need(type(horizon) is int and 1 <= horizon <= 8, 'timeline horizon')
    parameters = case.get('parameters')
    need(type(parameters) is list and 1 <= len(parameters) <= 3, 'timeline parameters')
    names = [p.get('name') for p in parameters]
    need(all(type(x) is str and x for x in names) and len(set(names)) == len(names),
         'parameter names')
    for p in parameters:
        need(type(p.get('lo')) is int and type(p.get('hi')) is int and
             0 <= p['lo'] <= p['hi'] <= 7, 'parameter bounds')
    validate_predicate(case.get('assumption'), names)

    port_kinds = {}
    for side in ('implementation', 'specification'):
        profile = case.get(side)
        need(type(profile) is dict, 'profile object')
        validate_expression(profile.get('gap'), names)
        for kind in ('reads', 'writes'):
            ports = profile.get(kind, {})
            need(type(ports) is dict, 'port map')
            for port, ranges in ports.items():
                need(type(port) is str and port and ':' not in port and '@' not in port,
                     'port name')
                need(port_kinds.get(port, kind) == kind, 'port direction collision')
                port_kinds[port] = kind
                need(type(ranges) is list, 'interval list')
                for pair in ranges:
                    need(type(pair) is list and len(pair) == 2, 'interval pair')
                    validate_expression(pair[0], names)
                    validate_expression(pair[1], names)
    need(2 + len(port_kinds) <= 8, 'port bound')

    values = []
    for xs in itertools.product(*(range(p['lo'], p['hi'] + 1) for p in parameters)):
        env = dict(zip(names, xs))
        if not predicate(case['assumption'], env):
            continue
        values.append(env)
        for side in ('implementation', 'specification'):
            profile = case[side]
            gap = integer(profile['gap'], env)
            need(1 <= gap <= horizon, 'evaluated gap outside horizon')
            for kind in ('reads', 'writes'):
                for ranges in profile.get(kind, {}).values():
                    seen = set()
                    for lo_term, hi_term in ranges:
                        lo, hi = integer(lo_term, env), integer(hi_term, env)
                        need(0 <= lo < hi <= horizon + 1,
                             'invalid interval or age beyond horizon')
                        ages = set(range(lo, hi))
                        need(not (seen & ages), 'overlapping intervals')
                        seen |= ages
                    if seen:
                        need(max(seen) - min(seen) < gap,
                             'same-port transaction events can collide across legal launches')
            need(port_separated(profile, env) == collision_free(profile, env),
                 'span/collision checker disagreement')
    return values


def direct_refines(case, env):
    impl = evaluated(case['implementation'], env)
    spec = evaluated(case['specification'], env)
    return (impl['gap'] <= spec['gap'] and
            all(impl['reads'].get(port, set()) <= spec['reads'].get(port, set())
                for port in set(impl['reads']) | set(spec['reads'])) and
            all(spec['writes'].get(port, set()) <= impl['writes'].get(port, set())
                for port in set(impl['writes']) | set(spec['writes'])))


def _tagged_event(item, launches):
    if (type(item) is not dict or type(item.get('port')) is not str or
            type(item.get('launch')) is not int or type(item.get('age')) is not int or
            type(item.get('time')) is not int):
        return None
    launch, age, time = item['launch'], item['age'], item['time']
    if launch < 0 or launch not in launches or age < 0 or time < 0 or time != launch + age:
        return None
    return item['port'], launch, age, time


def directed_ports(case):
    """Fixed directed universe, including ports omitted by either profile."""
    return {kind: set().union(*(case[side].get(kind, {})
                               for side in ('implementation', 'specification')))
            for kind in ('reads', 'writes')}


def _parsed_client(client, ports):
    """Parse one persisted client and enforce ownership and global physical injectivity."""
    need(type(client) is dict, 'client object')
    launches = client.get('launches')
    need(type(launches) is list, 'client launch list')
    need(all(type(t) is int and t >= 0 for t in launches), 'nonnegative client launches')
    need(launches == sorted(set(launches)), 'strictly increasing client launches')

    parsed = {'launches': launches, 'drives': [], 'samples': []}
    occupied = {}
    per_kind_tags = {'drives': set(), 'samples': set()}
    need(not (ports['reads'] & ports['writes']), 'port direction collision')
    for field in ('drives', 'samples'):
        items = client.get(field, [])
        need(type(items) is list, f'client {field} list')
        for item in items:
            event = _tagged_event(item, launches)
            need(event is not None, f'invalid {field[:-1]} tag ownership or time')
            port, launch, age, time = event
            direction = 'reads' if field == 'drives' else 'writes'
            need(port in ports[direction], f'{field[:-1]} port direction')
            tag = port, launch, age
            slot = port, time
            need(tag not in per_kind_tags[field], f'duplicate {field[:-1]} tag')
            need(slot not in occupied, 'tagged client physical port/cycle collision')
            per_kind_tags[field].add(tag)
            occupied[slot] = (field, tag)
            parsed[field].append(event)
    parsed['drive_tags'] = per_kind_tags['drives']
    parsed['sample_tags'] = per_kind_tags['samples']
    return parsed


def client_legal(profile, env, client, ports=None):
    """Validate a launch-indexed client and every tagged physical projection.

    Optional drives are permitted, but every drive and sample must belong to an
    actual nonnegative launch and all tags together must project injectively on
    each physical port/cycle slot. ``ports`` supplies the fixed directed universe;
    for a standalone profile its declared map keys (including empty maps) are used.
    """
    try:
        if ports is None:
            ports = {kind: set(profile.get(kind, {})) for kind in ('reads', 'writes')}
        parsed = _parsed_client(client, ports)
    except Invalid:
        return False
    p = evaluated(profile, env)
    launches = parsed['launches']
    if any(b - a < p['gap'] for a, b in zip(launches, launches[1:])):
        return False
    for launch in launches:
        for port, ages in p['reads'].items():
            for age in ages:
                if (port, launch, age) not in parsed['drive_tags']:
                    return False
    for port, _launch, age, _time in parsed['samples']:
        if age not in p['writes'].get(port, set()):
            return False
    return True


def _failure_key(item):
    return (item['cycle'], _KIND_ORDER[item['kind']], item['port'] or '',
            item['age'], item.get('launch', -1))


def canonical_failure(case, env):
    """Independently select the globally earliest failed directional clause."""
    impl = evaluated(case['implementation'], env)
    spec = evaluated(case['specification'], env)
    candidates = []
    if impl['gap'] > spec['gap']:
        candidates.append({'cycle': spec['gap'], 'kind': 'gap', 'port': None,
                           'age': spec['gap']})
    for port in sorted(set(impl['reads']) | set(spec['reads'])):
        for age in sorted(impl['reads'].get(port, set()) - spec['reads'].get(port, set())):
            candidates.append({'cycle': age, 'kind': 'read', 'port': port, 'age': age})
    for port in sorted(set(impl['writes']) | set(spec['writes'])):
        for age in sorted(spec['writes'].get(port, set()) - impl['writes'].get(port, set())):
            candidates.append({'cycle': age, 'kind': 'write', 'port': port, 'age': age})
    return min(candidates, key=_failure_key) if candidates else None


def replay_first_violation(case, env, client):
    """Compute the first absolute implementation violation from persisted events."""
    parsed = _parsed_client(client, directed_ports(case))
    impl = evaluated(case['implementation'], env)
    violations = []

    for left, right in zip(parsed['launches'], parsed['launches'][1:]):
        distance = right - left
        if distance < impl['gap']:
            violations.append({'cycle': right, 'kind': 'gap', 'port': None,
                               'age': distance, 'launch': right})

    for launch in parsed['launches']:
        for port, ages in impl['reads'].items():
            for age in ages:
                if (port, launch, age) not in parsed['drive_tags']:
                    violations.append({'cycle': launch + age, 'kind': 'read',
                                       'port': port, 'age': age, 'launch': launch})

    for port, launch, age, time in parsed['samples']:
        if age not in impl['writes'].get(port, set()):
            violations.append({'cycle': time, 'kind': 'write', 'port': port,
                               'age': age, 'launch': launch})

    need(bool(violations), 'persisted client has no replayed implementation violation')
    return min(violations, key=_failure_key)


def check_counterexample(case, env, client, game_rank):
    """Check one persisted shortest client against semantics and a verified game rank."""
    ports = directed_ports(case)
    need(client_legal(case['specification'], env, client, ports),
         'persisted client is not legal for the specification')
    need(not client_legal(case['implementation'], env, client, ports),
         'persisted client is legal for the implementation')

    expected = canonical_failure(case, env)
    need(expected is not None, 'counterexample supplied for a safe valuation')
    actual = replay_first_violation(case, env, client)
    need(actual['cycle'] == expected['cycle'], 'client is not temporally shortest')
    need((actual['kind'], actual['port'], actual['age']) ==
         (expected['kind'], expected['port'], expected['age']),
         'client does not realize the canonical failed-clause tie selection')

    need(type(client.get('first_violation_cycle')) is int and
         client['first_violation_cycle'] == actual['cycle'],
         'wrong first_violation_cycle metadata')
    need(client.get('kind') == actual['kind'], 'wrong counterexample kind metadata')
    need(client.get('port') == actual['port'], 'wrong counterexample port metadata')
    need(type(client.get('age')) is int and client['age'] == actual['age'],
         'wrong counterexample age metadata')
    need(type(game_rank) is int and game_rank == actual['cycle'] + 2,
         'replayed client time/game-rank mismatch')
    return actual


def check_client_record(case, values, safe_ids, record, rank_rows, initial_pair):
    """Validate one retained .clients.json file without rebuilding producer clients."""
    need(type(record) is dict, 'client record object')
    need(record.get('case_id') == case['id'], 'client record case identifier')
    need(record.get('safe_valuation_ids') == safe_ids, 'client record safe region')
    need(record.get('valuations') == values, 'client record valuation order')
    counterexamples = record.get('counterexamples')
    need(type(counterexamples) is list, 'client counterexample list')

    expected_failures = set(range(len(values))) - set(safe_ids)
    seen = set()
    for row in counterexamples:
        need(type(row) is dict, 'client counterexample row')
        valuation_id = row.get('valuation_id')
        need(type(valuation_id) is int and valuation_id in expected_failures,
             'counterexample valuation identifier')
        need(valuation_id not in seen, 'duplicate counterexample valuation')
        seen.add(valuation_id)
        need(row.get('valuation') == values[valuation_id], 'counterexample valuation binding')
        verified_rank = rank_rows[valuation_id][initial_pair]
        need(row.get('game_rank') == verified_rank, 'counterexample game-rank binding')
        check_counterexample(case, values[valuation_id], row.get('client'), verified_rank)
    need(seen == expected_failures, 'missing or extraneous counterexample valuations')
    return len(counterexamples)


def check_history_translation(case, key, translated, env):
    """Validate enabled actions and drop/launch transitions of a history translation.

    Only histories legal for this valuation are semantic states.  The producer may
    retain a valuation-independent superset, but every enabled action on a legal
    history must exactly match the evaluated profile, including actions of older
    simultaneously active transactions.
    """
    need(translated.get('encoding') == 'launch-history', 'history encoding required')
    raw_states = translated.get('history_states')
    need(type(raw_states) is list and len(raw_states) == translated.get('states'),
         'history state inventory')
    states = []
    for raw in raw_states:
        need(type(raw) is list and all(type(age) is int and 0 <= age <= case['horizon']
                                      for age in raw), 'history state ages')
        state = tuple(raw)
        need(state == tuple(sorted(set(state))), 'history state ordering')
        states.append(state)
    need(len(set(states)) == len(states), 'duplicate history state')
    index = {state: sid for sid, state in enumerate(states)}
    need(states[translated.get('initial')] == (), 'history initial state')

    p = evaluated(case[key], env)
    outgoing = [[] for _ in states]
    for edge in translated.get('edges', []):
        need(type(edge) is dict and type(edge.get('from')) is int and
             0 <= edge['from'] < len(states), 'history edge source')
        if predicate(edge.get('guard'), env):
            outgoing[edge['from']].append(edge)

    for sid, state in enumerate(states):
        if any(right - left < p['gap']
               for left, right in itertools.combinations(state, 2)):
            continue
        expected = {('in', 'tick', index[tuple(age + 1 for age in state
                                               if age + 1 <= case['horizon'])])}
        if not state or min(state) >= p['gap']:
            expected.add(('in', 'launch', index[tuple(sorted((0, *state)))]) )
        for age in state:
            for port, ages in p['writes'].items():
                if age in ages:
                    expected.add(('in', f'sample:{port}@{age}', sid))
            for port, ages in p['reads'].items():
                if age in ages:
                    expected.add(('out', f'need:{port}@{age}', sid))
        actual_list = [(edge.get('kind'), edge.get('label'), edge.get('to'))
                       for edge in outgoing[sid]]
        need(len(actual_list) == len(set(actual_list)), 'duplicate enabled history action')
        need(set(actual_list) == expected,
             f'history action mismatch for {case["id"]}:{key}:{state}')
    return True
