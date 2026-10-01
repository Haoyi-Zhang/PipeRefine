#!/usr/bin/env python3
"""Clean temporary reproduction with deterministic scientific comparison.

SPDX-License-Identifier: MIT
No network access or third-party dependency; does not overwrite retained results.
"""
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent


def bounded_child():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (110, 110))
    if hasattr(os, 'sched_setaffinity'):
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})


def run(arguments):
    result = subprocess.run([sys.executable, *arguments], cwd=ROOT,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, timeout=120, preexec_fn=bounded_child)
    if result.returncode:
        print(result.stdout, end='')
        print(result.stderr, end='', file=sys.stderr)
        raise RuntimeError(f'command failed with exit {result.returncode}: {arguments}')
    return result


def compare_tree(generated, retained, patterns):
    names=[]
    for pattern in patterns:
        names += [p.name for p in sorted(generated.glob(pattern))]
    names=sorted(set(names))
    for name in names:
        target=retained/name
        if not target.is_file() or (generated/name).read_bytes()!=target.read_bytes():
            raise RuntimeError(f'scientific reproduction differs: {name}')
    return len(names)


def main():
    tests=run(['-m', 'unittest', 'discover', '-s', 'tests', '-v'])
    passed=[]
    for line in tests.stderr.splitlines():
        if line.rstrip().endswith('... ok') and '(' in line and ')' in line:
            passed.append(line.split('(',1)[1].split(')',1)[0])
    test_count=len(passed)
    test_record={'count':test_count,'errors':0,'failures':0,
                 'tests':[{'status':'pass','test':name} for name in passed]}
    retained_test_record=json.loads((ROOT/'results/test-results.json').read_text())
    if test_record != retained_test_record:
        raise RuntimeError('retained unit-test inventory differs')
    with tempfile.TemporaryDirectory(prefix='interface-refinement-') as tmp:
        temporary = Path(tmp)
        generated = temporary / 'inputs'
        run(['src/generate.py', str(generated)])
        expected = sorted(p.name for p in (ROOT / 'inputs').glob('*.json'))
        actual = sorted(p.name for p in generated.glob('*.json'))
        if actual != expected: raise RuntimeError('generic input collection differs')
        for name in expected:
            if (generated/name).read_bytes() != (ROOT/'inputs'/name).read_bytes():
                raise RuntimeError(f'generic input regeneration differs: {name}')
        timeline_generated=temporary/'timeline-inputs'
        run(['src/generate_timeline.py',str(timeline_generated)])
        timeline_expected=sorted(p.name for p in (ROOT/'timeline-inputs').glob('*.json'))
        if sorted(p.name for p in timeline_generated.glob('*.json')) != timeline_expected:
            raise RuntimeError('timeline input collection differs')
        for name in timeline_expected:
            if (timeline_generated/name).read_bytes() != (ROOT/'timeline-inputs'/name).read_bytes():
                raise RuntimeError(f'timeline input regeneration differs: {name}')
        anchor_generated=temporary/'anchor-inputs'
        run(['src/generate_anchor.py',str(anchor_generated)])
        anchor_expected=sorted(p.name for p in (ROOT/'anchor-inputs').glob('*.json'))
        if sorted(p.name for p in anchor_generated.glob('*.json')) != anchor_expected:
            raise RuntimeError('anchor input collection differs')
        for name in anchor_expected:
            if (anchor_generated/name).read_bytes() != (ROOT/'anchor-inputs'/name).read_bytes():
                raise RuntimeError(f'anchor input regeneration differs: {name}')
        output = temporary / 'results'
        run(['run.py', '--output', str(output)])
        run(['run.py', '--output', str(output), '--check-only'])
        generic_files=compare_tree(output,ROOT/'results',
            ['families.csv','summary.json','*.certificate.json','*.witness.json'])
        timeline_output=temporary/'timeline-results'
        run(['run_timeline.py','--output',str(timeline_output)])
        run(['run_timeline.py','--output',str(timeline_output),'--check-only'])
        timeline_files=compare_tree(timeline_output,ROOT/'timeline-results',
            ['families.csv','summary.json','*.certificate.json','*.witness.json','*.clients.json'])
        anchor_output=temporary/'anchor-results'
        run(['run_anchor.py','--output',str(anchor_output)])
        run(['run_anchor.py','--output',str(anchor_output),'--check-only'])
        anchor_files=compare_tree(anchor_output,ROOT/'anchor-results',
                                  ['profiles.csv','summary.json'])
        micro_output=temporary/'micro-results'
        run(['run_exhaustive.py','--output',str(micro_output)])
        run(['run_exhaustive.py','--output',str(micro_output),'--check-only'])
        micro_files=compare_tree(micro_output,ROOT/'micro-results',
                                 ['profiles.csv','pairs.csv','summary.json'])
        bibliography_output=temporary/'bibliography-results'
        run(['run_bibliography.py','--output',str(bibliography_output)])
        run(['run_bibliography.py','--output',str(bibliography_output),'--check-only'])
        bibliography_files=compare_tree(bibliography_output,ROOT/'bibliography-results',
                                        ['entries.csv','summary.json'])
        print(json.dumps({'status':'pass','unit_tests':test_count,
                          'regenerated_inputs':len(expected),
                          'regenerated_timeline_inputs':len(timeline_expected),
                          'regenerated_anchor_inputs':len(anchor_expected),
                          'exhaustive_micro_profiles':52,
                          'exhaustive_micro_profile_pairs':2704,
                          'exhaustive_micro_clients':3665,
                          'bibliography_entries':69,
                          'compared_scientific_files':generic_files+timeline_files+anchor_files+micro_files+bibliography_files,
                          'checks':['unit tests','exact input regeneration','bitset solving',
                                    'local rank equations','reverse AND/OR oracle',
                                    'spoiler DAG replay','port-separation/collision equivalence',
                                    'all-tag client ownership/collision checks',
                                    'persisted absolute-time client replay and tie/rank binding',
                                    'history action/drop translation checks',
                                    'history-game correspondence',
                                    'independent exhaustive client-set inclusion oracle',
                                    'published-declaration normalization boundary',
                                    'bibliography coverage and high-risk metadata mutations',
                                    'scientific result equality'],
                          'timing_equality_required':False},indent=2))


if __name__ == '__main__':
    try: main()
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr); raise SystemExit(1)
