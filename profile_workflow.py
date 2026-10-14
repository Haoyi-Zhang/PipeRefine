#!/usr/bin/env python3
"""Whole retained timeline cohort costs under the same exact client interface.

All arms return every safe valuation and the same canonical shortest client for
each failure. Games additionally construct/check complete rank certificates and
selected spoiler DAGs. These are extra explanation objects, not a stronger query
guarantee or a justification to omit the simple criterion comparator.
SPDX-License-Identifier: MIT
"""
import argparse
from contextlib import contextmanager
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys
import time
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from timeline import translate_case,canonical_counterexample
from timeline_check import validate_timeline,direct_refines,check_counterexample,check_history_translation,canonical_failure
from domain import valuations
from solve import solve
from check import arena,exact_oracle,check_certificate,certificate_ranks,make_witness,check_witness
from runtime_limits import configure,check_cpu,peak_rss_kib


def own_memory():
    if sys.platform!='win32': return {'peak_rss_kib':peak_rss_kib()}
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[
            (name,ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage',
             'QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True);psapi=ctypes.WinDLL('psapi',use_last_error=True)
    kernel.GetCurrentProcess.restype=wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype=wintypes.BOOL
    c=Counters();c.cb=ctypes.sizeof(c)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(c),c.cb):
        raise OSError(ctypes.get_last_error(),'own-process memory query failed')
    return {'peak_rss_kib':None,'windows_peak_working_set_bytes':c.PeakWorkingSetSize,
            'windows_peak_commit_bytes':c.PeakPagefileUsage,
            'scope':'whole owned process before receipt write/exit; includes imports/input/answers, not Linux RSS or an OS cap'}


def scalar_certificate(game):
    values=valuations(game)
    rows=[exact_oracle(arena(game,v)) for v in values]
    groups={}
    for i,row in enumerate(rows): groups.setdefault(tuple(row),[]).append(i)
    q0=game['implementation']['initial']*game['specification']['states']+game['specification']['initial']
    bad=[(row[q0],tuple(v[p['name']] for p in game['parameters']),i)
         for i,(v,row) in enumerate(zip(values,rows)) if row[q0]!=-1]
    rounds=max((r for row in rows for r in row if r!=-1),default=0)
    return {'case_id':game['id'],'valuations':values,
        'cells':[{'valuation_ids':ids,'ranks':list(row)} for row,ids in groups.items()],
        'safe_valuation_ids':[i for i,row in enumerate(rows) if row[q0]==-1],
        'shortest_bad_valuation_id':min(bad)[2] if bad else None,'rounds':rounds,
        'equation_visits':game['implementation']['states']*game['specification']['states']*(rounds+1)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('method',choices=('criterion','bitset','scalar'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--portable',action='store_true')
    args=parser.parse_args();output=args.output.resolve()
    if output.is_relative_to(ROOT) or output.exists(): raise ValueError('fresh owned external output required')
    limits=configure(args.portable);stages={}
    @contextmanager
    def stage(name):
        c,w=time.process_time(),time.perf_counter()
        yield
        row=stages.setdefault(name,{'cpu_seconds':0.0,'wall_seconds':0.0})
        row['cpu_seconds']+=time.process_time()-c;row['wall_seconds']+=time.perf_counter()-w
    c,w=time.process_time(),time.perf_counter()
    paths=sorted((ROOT/'timeline-inputs').glob('*.json'))
    with stage('input_read_decode'):
        cases=[json.loads(p.read_text(encoding='utf-8')) for p in paths]
    answers=[];total=safe_count=0
    for case in cases:
        check_cpu()
        with stage('full_admission_and_collision_check'):
            values=validate_timeline(case)
        if args.method=='criterion':
            with stage('all_criterion_queries'):
                safe=[i for i,v in enumerate(values) if direct_refines(case,v)]
        else:
            with stage('translation_and_action_check'):
                game=translate_case(case)
                if game['translation_mode']=='history':
                    for v in values:
                        for side in ('implementation','specification'): check_history_translation(case,side,game[side],v)
            with stage('complete_solve'):
                cert=solve(game) if args.method=='bitset' else scalar_certificate(game)
            with stage('full_certificate_and_spoiler_consumer'):
                check_certificate(game,cert,oracle=False)
                witness=make_witness(game,cert);check_witness(game,cert,witness)
                ranks=certificate_ranks(game,cert,values)
                q0=game['implementation']['initial']*game['specification']['states']+game['specification']['initial']
                safe=cert['safe_valuation_ids']
        with stage('all_client_construction_and_replay'):
            clients=[]
            for i,v in enumerate(values):
                if i in safe: continue
                client=canonical_counterexample(case,v)
                if client is None: raise RuntimeError('missing shortest client')
                # Criterion predicts rank from the proved arithmetic correspondence;
                # game arms supply a checked rank, not an inferred game execution.
                rank=canonical_failure(case,v)['cycle']+2 if args.method=='criterion' else ranks[i][q0]
                check_counterexample(case,v,client,rank)
                clients.append({'valuation_id':i,'client':client})
            answers.append({'case_id':case['id'],'valuations':values,'safe_valuation_ids':safe,'clients':clients})
            total+=len(values);safe_count+=len(safe)
    if (len(cases),total,safe_count)!=(67,961,270): raise RuntimeError('retained timeline cohort changed')
    with stage('answer_encoding'):
        data=(''.join(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n' for row in answers)).encode('utf-8')
    output.mkdir(parents=True,exist_ok=False)
    with stage('answer_write'): (output/'answers.jsonl').write_bytes(data)
    body={'cpu_seconds':time.process_time()-c,'wall_seconds':time.perf_counter()-w}
    memory=own_memory()
    sources=[Path(__file__),*(ROOT/'src'/name for name in ('timeline.py','timeline_check.py','domain.py','solve.py','check.py','runtime_limits.py'))]
    receipt={'method':args.method,'families':67,'valuations':961,'safe':270,'failed_clients':691,
             'through_answers':body,'stages':stages,'memory':memory,'runtime_limits':limits,
             'answer_sha256':sha256(data).hexdigest(),
             'input_sha256':{p.relative_to(ROOT).as_posix():sha256(p.read_bytes()).hexdigest() for p in paths},
             'source_sha256':{p.relative_to(ROOT).as_posix():sha256(p.read_bytes()).hexdigest() for p in sources},
             'source_scope':'seven imported local files, not every function or independent authorship',
             'environment':{'python':sys.version,'platform':platform.platform()},
             'contract':'all retained timeline safe valuations and every canonical shortest client; identical inputs and semantic guarantee',
             'extra_game_work':'complete rank tables/certificates and selected branching spoiler are constructed and consumed only by game arms',
             'criterion_rank_scope':'arithmetic prediction of time+2, not native game execution in the criterion arm',
             'measurement_scope':'one fresh process per arm; body through answers; external command includes startup/imports/receipt/exit',
             'native_scope':'owned finite Python models only, no hardware/HDL/RTL/external featured-game engine'}
    with (output/'receipt.json').open('x',encoding='utf-8') as handle: json.dump(receipt,handle,indent=2)
    print(json.dumps({k:receipt[k] for k in ('method','families','valuations','through_answers','answer_sha256','memory')}))


if __name__=='__main__': main()
