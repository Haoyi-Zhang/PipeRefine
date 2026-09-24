#!/usr/bin/env python3
"""Check normalized published-declaration timing slices and fragment boundaries.

SPDX-License-Identifier: MIT
"""
import argparse
import csv
import json
from pathlib import Path
import resource
import os
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
from check import Invalid
from timeline_check import (validate_timeline, direct_refines, port_separated,
                            collision_free, evaluated)


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'anchor-results')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (110, 110))
    if hasattr(os, 'sched_setaffinity'):
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    args.output.mkdir(parents=True, exist_ok=True)

    rows = []
    supported_valuations = 0
    span_collision_disagreements = 0
    reflexivity_disagreements = 0
    for path in sorted((ROOT / 'anchor-inputs').glob('*.json')):
        case = json.loads(path.read_text())
        expected = case['expected_supported']
        try:
            values = validate_timeline(case)
            supported = True
            reason = ''
        except Invalid as error:
            values = []
            supported = False
            reason = str(error)
        if supported != expected:
            raise RuntimeError(f"unexpected fragment classification: {case['id']}: {reason}")
        maximum_age = None
        if supported:
            supported_valuations += len(values)
            for env in values:
                if not direct_refines(case, env):
                    reflexivity_disagreements += 1
                for side in ('implementation', 'specification'):
                    if port_separated(case[side], env) != collision_free(case[side], env):
                        span_collision_disagreements += 1
                    p = evaluated(case[side], env)
                    ages = [age for kind in ('reads', 'writes')
                            for aset in p[kind].values() for age in aset]
                    if ages:
                        maximum_age = max(maximum_age if maximum_age is not None else 0,
                                          max(ages))
        rows.append({
            'record': case['id'],
            'supported': int(supported),
            'valuations': len(values),
            'maximum_age': '' if maximum_age is None else maximum_age,
            'source_page': case['source']['page'],
            'source_locator': case['source']['locator'],
            'classification_note': case['boundary_reason'] if not supported else 'accepted',
        })

    summary = {
        'records': len(rows),
        'supported_records': sum(row['supported'] for row in rows),
        'rejected_boundary_records': sum(1 - row['supported'] for row in rows),
        'supported_valuations': supported_valuations,
        'span_collision_disagreements': span_collision_disagreements,
        'reflexivity_disagreements': reflexivity_disagreements,
        'scope': ('manual normalization of published Lilac timing declarations; '
                  'no source parser, body semantics, bit widths, where-clause functions, or RTL'),
    }
    if span_collision_disagreements or reflexivity_disagreements:
        raise RuntimeError('anchor cross-check disagreement')

    if args.check_only:
        if json.loads((args.output / 'summary.json').read_text()) != summary:
            raise RuntimeError('retained anchor summary mismatch')
        with (args.output / 'profiles.csv').open(newline='') as handle:
            retained = list(csv.DictReader(handle))
        normalized = [{key: str(value) for key, value in row.items()} for row in rows]
        if retained != normalized:
            raise RuntimeError('retained anchor profile table mismatch')
    else:
        dump(args.output / 'summary.json', summary)
        with (args.output / 'profiles.csv').open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
