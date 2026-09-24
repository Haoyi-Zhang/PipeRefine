"""Independent validation for port-separated timelines and tagged clients.

This module deliberately uses check.py's separately implemented arithmetic
rather than timeline.py/domain.py's evaluator.

SPDX-License-Identifier: MIT
"""
import itertools
from check import Invalid, need, integer, predicate, validate_expression, validate_predicate


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
                        need(0 <= lo < hi <= horizon + 1, 'invalid interval or age beyond horizon')
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
    if launch not in launches or age < 0 or time != launch + age:
        return None
    return item['port'], launch, age, time


def client_legal(profile, env, client):
    """Validate a launch-indexed client and its physical port/cycle projection."""
    p = evaluated(profile, env)
    launches = client.get('launches')
    if type(launches) is not list or any(type(t) is not int or t < 0 for t in launches):
        return False
    if launches != sorted(set(launches)):
        return False
    if any(b - a < p['gap'] for a, b in zip(launches, launches[1:])):
        return False

    drives = client.get('drives', [])
    if type(drives) is not list:
        return False
    drive_tags = set()
    drive_slots = {}
    for item in drives:
        event = _tagged_event(item, launches)
        if event is None:
            return False
        port, launch, age, time = event
        tag = port, launch, age
        slot = port, time
        if tag in drive_tags or slot in drive_slots:
            return False
        drive_tags.add(tag)
        drive_slots[slot] = tag
    for launch in launches:
        for port, ages in p['reads'].items():
            for age in ages:
                if (port, launch, age) not in drive_tags:
                    return False

    samples = client.get('samples', [])
    if type(samples) is not list:
        return False
    sample_tags = set()
    sample_slots = set()
    for item in samples:
        event = _tagged_event(item, launches)
        if event is None:
            return False
        port, launch, age, time = event
        tag = port, launch, age
        slot = port, time
        if tag in sample_tags or slot in sample_slots:
            return False
        if age not in p['writes'].get(port, set()):
            return False
        sample_tags.add(tag)
        sample_slots.add(slot)
    return True
