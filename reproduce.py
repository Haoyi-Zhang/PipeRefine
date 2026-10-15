#!/usr/bin/env python3
"""Clean temporary reproduction with deterministic scientific comparison.

SPDX-License-Identifier: MIT
No network access or third-party dependency; does not overwrite retained results.
"""
import argparse
from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from src.runtime_limits import configure,check_cpu,resource,CPU_SECONDS,ADDRESS_BYTES

ROOT = Path(__file__).resolve().parent
EXPECTED_TEST_METHODS=123


def bounded_child():
    resource.setrlimit(resource.RLIMIT_AS, (ADDRESS_BYTES, ADDRESS_BYTES))
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_SECONDS, CPU_SECONDS))
    if hasattr(os, 'sched_setaffinity'):
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})


def python_command(arguments):
    flags=['-B']
    if sys.flags.no_site: flags.append('-S')
    if sys.flags.optimize: flags.append('-'+'O'*sys.flags.optimize)
    return [sys.executable,*flags,*arguments]


def run(arguments,*,portable=False,logs=None):
    check_cpu()
    argv=python_command(arguments)
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0'}
    started=time.perf_counter()
    record={'argv':argv,'cwd':str(ROOT),'timeout_seconds':120}
    options={} if portable else {'preexec_fn':bounded_child}
    try:
        result = subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=120,env=env,**options)
        record.update(exit_code=result.returncode,stdout=result.stdout.decode('utf-8',errors='replace'),
                      stderr=result.stderr.decode('utf-8',errors='replace'))
    except subprocess.TimeoutExpired as error:
        record.update(exit_code=None,status='timeout',stdout=(error.stdout or b'').decode('utf-8',errors='replace'),
                      stderr=(error.stderr or b'').decode('utf-8',errors='replace'))
        raise
    finally:
        record['wall_seconds']=time.perf_counter()-started
        if logs is not None:
            logs.mkdir(exist_ok=True)
            path=logs/(str(len(list(logs.glob('*.json')))).zfill(2)+'.json')
            with path.open('x',encoding='utf-8') as handle: json.dump(record,handle,indent=2)
    if result.returncode:
        print(record['stdout'], end='')
        print(record['stderr'], end='', file=sys.stderr)
        raise RuntimeError(f'command failed with exit {result.returncode}: {arguments}')
    check_cpu()
    return subprocess.CompletedProcess(argv,result.returncode,record['stdout'],record['stderr'])


def compare_tree(generated, retained, patterns):
    names=[]
    for pattern in patterns:
        names += [p.name for p in sorted(generated.glob(pattern))]
    names=sorted(set(names))
    expected=sorted({p.name for pattern in patterns for p in retained.glob(pattern)})
    if names!=expected:
        raise RuntimeError('scientific file set differs: missing='+str(sorted(set(expected)-set(names)))+
                           '; extra='+str(sorted(set(names)-set(expected))))
    for name in names:
        target=retained/name
        if not target.is_file() or (generated/name).read_bytes()!=target.read_bytes():
            raise RuntimeError(f'scientific reproduction differs: {name}')
    return len(names)


@contextmanager
def workspace(scratch,keep):
    if keep:
        yield Path(tempfile.mkdtemp(prefix='interface-refinement-',dir=scratch))
    else:
        with tempfile.TemporaryDirectory(prefix='interface-refinement-',dir=scratch) as tmp: yield Path(tmp)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--portable',action='store_true')
    parser.add_argument('--scratch',type=Path)
    parser.add_argument('--keep-work',action='store_true')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.output and args.output.resolve().is_relative_to(ROOT):
        raise ValueError('write a fresh reproduction report outside retained artifact')
    if args.scratch:
        if args.scratch.resolve().is_relative_to(ROOT): raise ValueError('scratch must be external')
        args.scratch.mkdir(parents=True,exist_ok=True)
    limits=configure(args.portable)
    started=time.perf_counter()
    with workspace(args.scratch,args.keep_work) as temporary:
        print('Raw reproduction workspace: '+str(temporary),flush=True)
        os.environ.update(TEMP=str(temporary),TMP=str(temporary),TMPDIR=str(temporary),PYTHONDONTWRITEBYTECODE='1')
        commands=temporary/'commands'
        portable=['--portable'] if args.portable else []
        def child(arguments): return run(arguments,portable=args.portable,logs=commands)
        report=campaign(temporary,child,portable)
        report.update(runtime_limits=limits,raw_workspace=str(temporary) if args.keep_work else None,
                      wall_seconds_descriptive=time.perf_counter()-started,
                      source_sha256={p.relative_to(ROOT).as_posix():sha256(p.read_bytes()).hexdigest()
                                     for p in sorted(ROOT.rglob('*.py')) if '__pycache__' not in p.parts},
                      source_scope='launch inventory, not assertion that every source/function executed',
                      child_commands=[json.loads(p.read_text()) for p in sorted(commands.glob('*.json'))])
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            with args.output.open('x',encoding='utf-8') as handle: json.dump(report,handle,indent=2)
        print(json.dumps(report,indent=2))


def campaign(temporary,run,portable):
    tests=run(['-m', 'unittest', 'discover', '-s', 'tests', '-v'])
    passed=[]
    for line in tests.stderr.splitlines():
        if line.rstrip().endswith('... ok') and '(' in line and ')' in line:
            passed.append(line.split('(',1)[1].split(')',1)[0])
    test_count=len(passed)
    test_record={'count':test_count,'errors':0,'failures':0,
                 'tests':[{'status':'pass','test':name} for name in passed]}
    retained_test_record=json.loads((ROOT/'results/test-results.json').read_text())
    old_names={row['test'] for row in retained_test_record['tests']}
    if test_count!=EXPECTED_TEST_METHODS or not old_names<=set(passed) or len(passed)!=len(set(passed)):
        raise RuntimeError('current unit-test inventory or retained-test preservation differs')
    # Explicit suites are not added to the discovery-method or scientific-case counts.
    for script in ('tests/reply_index_regression.py','tests/directed_client_regression.py'):
        run([script,'-v'])
    (temporary/'tests.json').write_text(json.dumps(test_record,indent=2)+'\n',encoding='utf-8',newline='\n')
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
    run(['run.py', '--output', str(output),*portable])
    run(['run.py', '--output', str(output), '--check-only',*portable])
    generic_files=compare_tree(output,ROOT/'results',
        ['families.csv','summary.json','*.certificate.json','*.witness.json'])
    timeline_output=temporary/'timeline-results'
    run(['run_timeline.py','--output',str(timeline_output),*portable])
    run(['run_timeline.py','--output',str(timeline_output),'--check-only',*portable])
    timeline_files=compare_tree(timeline_output,ROOT/'timeline-results',
        ['families.csv','summary.json','*.certificate.json','*.witness.json','*.clients.json'])
    anchor_output=temporary/'anchor-results'
    run(['run_anchor.py','--output',str(anchor_output),*portable])
    run(['run_anchor.py','--output',str(anchor_output),'--check-only',*portable])
    anchor_files=compare_tree(anchor_output,ROOT/'anchor-results',
                              ['profiles.csv','summary.json'])
    micro_output=temporary/'micro-results'
    run(['run_exhaustive.py','--output',str(micro_output),*portable])
    run(['run_exhaustive.py','--output',str(micro_output),'--check-only',*portable])
    micro_files=compare_tree(micro_output,ROOT/'micro-results',
                             ['profiles.csv','pairs.csv','summary.json'])
    bibliography_output=temporary/'bibliography-results'
    run(['run_bibliography.py','--output',str(bibliography_output)])
    run(['run_bibliography.py','--output',str(bibliography_output),'--check-only'])
    bibliography_files=compare_tree(bibliography_output,ROOT/'bibliography-results',
                                    ['entries.csv','summary.json'])
    compound=temporary/'compound'
    compound_args=['run_product.py',str(ROOT/'examples/compound-left.json'),str(ROOT/'examples/compound-right.json'),
                   '--output',str(compound),*portable]
    run(compound_args);run([*compound_args,'--check-only'])
    if (generic_files,timeline_files,anchor_files,micro_files,bibliography_files)!=(84,203,2,3,2):
        raise RuntimeError('whole scientific campaign inventory changed')
    return {'status':'pass','unit_tests':test_count,'test_report':test_record,
                          'separate_regression_suites':{'reply_index':4,'directed_client':4},
                          'compound_example':json.loads((compound/'summary.json').read_text()),
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
                      'timing_equality_required':False}


if __name__ == '__main__':
    try: main()
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr); raise SystemExit(1)
