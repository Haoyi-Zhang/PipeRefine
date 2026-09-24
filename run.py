#!/usr/bin/env python3
"""Bounded one-worker reproduction. SPDX-License-Identifier: MIT."""
import argparse
import csv
import json
import os
from pathlib import Path
import resource
import sys
import time

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from solve import solve
from check import validate_case,check_certificate,make_witness,check_witness,predicate


def dump(path,obj):
    path.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'results')
    p.add_argument('--only',type=str,default=None,help='single exact case identifier')
    p.add_argument('--check-only',action='store_true',help='check retained certificates; do not solve')
    args=p.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU,(110,110))
    # Keep one CPU while leaving remaining headroom for the surrounding environment.
    if hasattr(os,'sched_setaffinity'):
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    output=args.output.resolve()
    if not args.check_only:output.mkdir(parents=True,exist_ok=True)
    paths=sorted((ROOT/'inputs').glob('*.json'))
    if args.only:paths=[x for x in paths if x.stem==args.only]
    if not paths:raise SystemExit('No matching input')
    t0=time.perf_counter();c0=time.process_time();rows=[]
    for path in paths:
        c=json.loads(path.read_text());validate_case(c)
        start=time.perf_counter()
        cert_path=output/(path.stem+'.certificate.json')
        witness_path=output/(path.stem+'.witness.json')
        if args.check_only:
            cert=json.loads(cert_path.read_text());witness=json.loads(witness_path.read_text())
        else:
            cert=solve(c)
            # Binding, full local equations and an algorithmically separate oracle.
            check_certificate(c,cert,oracle=True)
            witness=make_witness(c,cert)
            dump(cert_path,cert);dump(witness_path,witness)
        stats=check_certificate(c,cert,oracle=args.check_only)
        nodes=check_witness(c,cert,witness)
        guards=[e['guard'] for a in ('implementation','specification') for e in c[a]['edges']]
        guards+=list(c['environment_inputs'].values())
        signatures={tuple(predicate(g,v) for g in guards) for v in cert['valuations']}
        row={'case_id':c['id'],'group':c['group'],**stats,
             'guard_cells':len(signatures),'implementation_states':c['implementation']['states'],
             'specification_states':c['specification']['states'],
             'parameters':len(c['parameters']),'rounds':cert['rounds'],
             'equation_visits':cert['equation_visits'],'witness_nodes':nodes,
             'shortest_depth':0 if witness is None else witness['depth']}
        rows.append(row)
        print(c['id'],json.dumps(stats,sort_keys=True),'wall_seconds',round(time.perf_counter()-start,6),flush=True)
    summary={'families':len(rows),'totals':{key:sum(r[key] for r in rows) for key in
              ('valuations','state_pair_valuations','safe','bad','cells','guard_cells','equation_visits','witness_nodes')},
             'maximum_shortest_depth':max(r['shortest_depth'] for r in rows),
             'maximum_states':max(max(r['implementation_states'],r['specification_states']) for r in rows),
             'zero_disagreements':True,'scope':'finite inputs only; no RTL or contextual completeness claim'}
    measurement={'wall_seconds':time.perf_counter()-t0,'cpu_seconds':time.process_time()-c0,
                 'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'workers':1,
                 'cpu_limit_seconds':110,'address_space_limit_bytes':2*1024**3}
    if not args.check_only:
        with (output/'families.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        dump(output/'summary.json',summary);dump(output/'measurements.json',measurement)
    print(json.dumps({'summary':summary,'measurement':measurement},indent=2,sort_keys=True))


if __name__=='__main__':main()
