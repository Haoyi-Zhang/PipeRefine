#!/usr/bin/env python3
"""Generate normalized timing slices from published Lilac declarations.

The records transcribe only event delay and port availability intervals.  They
do not parse Lilac source, bit widths, bodies, where-clause functions, or RTL.
SPDX-License-Identifier: MIT
"""
import copy
import json
from pathlib import Path

SOURCE = {
    'title': 'Parameterized Hardware Design with Latency-Abstract Interfaces',
    'doi': '10.1145/3779212.3790199',
    'url': 'https://people.csail.mit.edu/rachit/files/pubs/lilac.pdf',
    'license': 'CC BY-NC-ND 4.0 (paper); normalized facts only, paper not redistributed',
}


def par(name, lo, hi):
    return {'name': name, 'lo': lo, 'hi': hi}


def add(a, b):
    return ['+', copy.deepcopy(a), b]


def singleton(a):
    return [[copy.deepcopy(a), add(a, 1)]]


def profile(gap, reads, writes):
    return {'gap': copy.deepcopy(gap), 'reads': copy.deepcopy(reads),
            'writes': copy.deepcopy(writes)}


def record(identifier, locator, page, horizon, parameters, timing,
           expected_supported=True, boundary_reason=''):
    return {
        'id': identifier,
        'group': 'published-declaration',
        'horizon': horizon,
        'parameters': parameters,
        'assumption': True,
        'implementation': copy.deepcopy(timing),
        'specification': copy.deepcopy(timing),
        'expected_supported': expected_supported,
        'boundary_reason': boundary_reason,
        'normalization': ('event delay becomes gap; half-open input intervals become read ages; '
                          'half-open output intervals become guarantee ages'),
        'source': {**SOURCE, 'page': page, 'locator': locator},
    }


def all_anchor_records():
    return [
        record('lilac-fpadd', 'Figure 4, FPAdd signature', 5, 7,
               [par('L', 1, 7)],
               profile(1, {'l': [[0, 1]], 'r': [[0, 1]]}, {'o': singleton('L')})),
        record('lilac-mult', 'Section 6.1, Mult signature', 9, 7,
               [par('L', 1, 7)],
               profile(1, {'a': [[0, 1]], 'b': [[0, 1]]}, {'o': singleton('L')})),
        record('lilac-shift', 'Figure 6(a), Shift signature', 6, 7,
               [par('N', 1, 7)],
               profile(1, {'input': [[0, 1]]}, {'out': singleton('N')})),
        record('lilac-lutmult', 'Figure 9(a), LutMult signature', 10, 8,
               [par('z', 0, 0)],
               profile(1, {'n': [[0, 1]], 'd': [[0, 1]]}, {'q': [[8, 9]]})),
        record('lilac-highrad', 'Figure 9(c), HighRad signature', 10, 7,
               [par('L', 1, 7)],
               profile('L', {'n': [[0, 1]], 'd': [[0, 1]]}, {'q': singleton('L')})),
        record('lilac-fpu-wide-input-boundary', 'Figure 5(a), initial erroneous FPU declaration', 5, 1,
               [par('z', 0, 0)],
               profile(1, {'op': [[0, 1]], 'l': [[0, 1]], 'r': [[0, 2]]},
                       {'o': [[0, 1]]}),
               expected_supported=False,
               boundary_reason=('the source labels this FPU implementation erroneous; input r spans ages 0 and 1 '
                                'while the launch gap is 1, so the port-separated fragment rejects this shape')),
    ]


def write_anchor_inputs(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for item in all_anchor_records():
        (directory / (item['id'] + '.json')).write_text(
            json.dumps(item, indent=2, sort_keys=True) + '\n'
        )


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    write_anchor_inputs(parser.parse_args().directory)
