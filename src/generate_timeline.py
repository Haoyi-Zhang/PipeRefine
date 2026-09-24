#!/usr/bin/env python3
"""Generate the fixed port-separated timeline family collection.

The final three families instantiate timing shapes transcribed from published
Lilac signatures: fully pipelined FPAdd, a parameterized Shift, and HighRad.
SPDX-License-Identifier: MIT
"""
import copy
import json
import random
from pathlib import Path


def par(name='p', lo=0, hi=3):
    return {'name': name, 'lo': lo, 'hi': hi}


def prof(gap, reads=None, writes=None):
    return {'gap': copy.deepcopy(gap), 'reads': copy.deepcopy(reads or {}),
            'writes': copy.deepcopy(writes or {})}


def case(name, impl, spec, parameters=None, group='handwritten', assumption=True, horizon=7):
    return {'id': name, 'group': group, 'horizon': horizon,
            'parameters': parameters or [par()], 'assumption': assumption,
            'implementation': impl, 'specification': spec}


def add(a, b): return ['+', copy.deepcopy(a), copy.deepcopy(b)]
def mod(a, b): return ['%', copy.deepcopy(a), b]
def singleton(a): return [[copy.deepcopy(a), add(a, 1)]]


def all_timeline_cases():
    p2, q2 = mod('p', 2), mod('q', 2)
    cases = [
        case('timeline-identical', prof(4, {'x': [[0, 2]]}, {'y': [[2, 4]]}),
             prof(4, {'x': [[0, 2]]}, {'y': [[2, 4]]})),
        case('timeline-gap', prof(add(4, p2), {'x': [[0, 1]]}, {'y': [[2, 3]]}),
             prof(add(4, q2), {'x': [[0, 1]]}, {'y': [[2, 3]]}), [par('p'), par('q')]),
        case('timeline-read-window', prof(5, {'x': [[0, add(1, p2)]]}, {'y': [[2, 4]]}),
             prof(5, {'x': [[0, add(1, q2)]]}, {'y': [[2, 4]]}), [par('p'), par('q')]),
        case('timeline-write-window', prof(5, {'x': [[0, 1]]}, {'y': [[1, add(3, p2)]]}),
             prof(5, {'x': [[0, 1]]}, {'y': [[1, add(3, q2)]]}), [par('p'), par('q')]),
        case('timeline-combined', prof(add(4, p2), {'x': [[0, add(1, q2)]]},
                                                   {'y': [[1, add(3, p2)]]}),
             prof(add(4, q2), {'x': [[0, add(1, p2)]]},
                              {'y': [[1, add(3, q2)]]}), [par('p'), par('q')]),
        case('timeline-extra-read-port', prof(5, {'x': [[0, 1]], 'coef': [[1, 2]]}, {'y': [[2, 4]]}),
             prof(5, {'x': [[0, 1]]}, {'y': [[2, 4]]})),
        case('timeline-extra-write-port', prof(5, {'x': [[0, 1]]}, {'y': [[2, 4]], 'flag': [[1, 2]]}),
             prof(5, {'x': [[0, 1]]}, {'y': [[2, 4]], 'flag': [[1, 2]]})),
        case('timeline-missing-write-port', prof(5, {'x': [[0, 1]]}, {'y': [[2, 4]]}),
             prof(5, {'x': [[0, 1]]}, {'y': [[2, 4]], 'flag': [[1, 2]]})),
        case('timeline-disjoint-read', prof(5, {'x': [[0, 1], [2, 3]]}, {'y': [[3, 4]]}),
             prof(5, {'x': [[0, 1], [2, 4]]}, {'y': [[3, 4]]})),
        case('timeline-disjoint-write', prof(5, {'x': [[0, 1]]}, {'y': [[1, 2], [3, 4]]}),
             prof(5, {'x': [[0, 1]]}, {'y': [[1, 2], [3, 4]]})),
        case('timeline-correlated-assumption', prof(add(4, p2), {'x': [[0, add(1, p2)]]}, {'y': [[2, 4]]}),
             prof(add(4, q2), {'x': [[0, add(1, q2)]]}, {'y': [[2, 4]]}),
             [par('p'), par('q')], assumption=['<=', 'p', 'q']),
        case('timeline-three-ports', prof(6, {'a': [[0, 1]], 'b': [[1, 2]]},
                                                {'sum': [[2, 4]], 'carry': [[3, 5]]}),
             prof(6, {'a': [[0, 2]], 'b': [[1, 3]]},
                     {'sum': [[3, 4]], 'carry': [[4, 5]]})),
        # Published Lilac timing shapes, bounded to latencies 1..3 so the
        # launch-history game remains inside the 48-state artifact cap.
        case('timeline-anchor-fpadd',
             prof(1, {'l': [[0, 1]], 'r': [[0, 1]]}, {'o': singleton('p')}),
             prof(1, {'l': [[0, 1]], 'r': [[0, 1]]}, {'o': singleton('q')}),
             [par('p', 1, 3), par('q', 1, 3)], group='anchor-derived', horizon=3),
        case('timeline-anchor-shift',
             prof(1, {'input': [[0, 1]]}, {'out': singleton('p')}),
             prof(1, {'input': [[0, 1]]}, {'out': singleton('q')}),
             [par('p', 1, 3), par('q', 1, 3)], group='anchor-derived', horizon=3),
        case('timeline-anchor-highrad',
             prof('p', {'n': [[0, 1]], 'd': [[0, 1]]}, {'quot': singleton('p')}),
             prof('q', {'n': [[0, 1]], 'd': [[0, 1]]}, {'quot': singleton('q')}),
             [par('p', 1, 3), par('q', 1, 3)], group='anchor-derived', horizon=3),
    ]
    gaps = [4, 5, 6, add(4, p2), add(4, q2)]
    reads = [{}, {'x': [[0, 1]]}, {'x': [[0, 2]]}, {'x': [[1, 3]]},
             {'x': [[p2, add(2, p2)]]}, {'x': [[0, 1], [2, 3]]},
             {'x': [[0, 2]], 'coef': [[2, 3]]}]
    writes = [{}, {'y': [[1, 2]]}, {'y': [[1, 3]]}, {'y': [[2, 4]]},
              {'y': [[add(1, p2), add(3, p2)]]}, {'y': [[1, 2], [3, 4]]},
              {'y': [[1, 3]], 'flag': [[3, 4]]}]
    for offset, seed in enumerate(range(20260940, 20260992), 1):
        rng = random.Random(seed)
        ip = prof(rng.choice(gaps), rng.choice(reads), rng.choice(writes))
        if offset % 9 == 0:
            sp = copy.deepcopy(ip)
        else:
            sp = prof(rng.choice(gaps), rng.choice(reads), rng.choice(writes))
        cases.append(case('timeline-generated-' + str(offset).zfill(2), ip, sp,
                          [par('p'), par('q')], group='generated'))
    return cases


def write_timeline_inputs(directory):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    for c in all_timeline_cases():
        (directory / (c['id'] + '.json')).write_text(json.dumps(c, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument('directory', type=Path)
    write_timeline_inputs(parser.parse_args().directory)
