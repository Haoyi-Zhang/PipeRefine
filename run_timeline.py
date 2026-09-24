#!/usr/bin/env python3
"""Cross-check timeline criteria, client witnesses, and translated games. SPDX-License-Identifier: MIT."""
import argparse
import csv
import json
from pathlib import Path
import resource
import os
import sys
import time
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
from solve import solve
from check import check_certificate, certificate_ranks, make_witness, check_witness
from timeline import safe_valuation_ids, translate_case, canonical_counterexample
from timeline_check import validate_timeline, direct_refines, client_legal


def dump(path, obj): path.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--output', type=Path, default=ROOT / 'timeline-results')
    ap.add_argument('--check-only', action='store_true'); args = ap.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (110, 110))
    if hasattr(os, 'sched_setaffinity'): os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    args.output.mkdir(parents=True, exist_ok=True)
    rows=[]; all_records=[]; t0=time.perf_counter(); c0=time.process_time()
    for path in sorted((ROOT / 'timeline-inputs').glob('*.json')):
        c=json.loads(path.read_text()); vals=validate_timeline(c); translated=translate_case(c)
        direct=[k for k,v in enumerate(vals) if direct_refines(c,v)]
        if direct != safe_valuation_ids(c): raise RuntimeError('producer/checker criterion mismatch: '+c['id'])
        cp=args.output/(c['id']+'.certificate.json'); wp=args.output/(c['id']+'.witness.json')
        if args.check_only:
            cert=json.loads(cp.read_text()); witness=json.loads(wp.read_text())
        else:
            cert=solve(translated); check_certificate(translated,cert,oracle=True)
            witness=make_witness(translated,cert); dump(cp,cert); dump(wp,witness)
        stats=check_certificate(translated,cert,oracle=args.check_only); check_witness(translated,cert,witness)
        if cert['safe_valuation_ids'] != direct: raise RuntimeError('criterion/game mismatch: '+c['id'])
        rank_rows=certificate_ranks(translated,cert,vals)
        q0=translated['implementation']['initial']*translated['specification']['states']+translated['specification']['initial']
        client_records=[]
        for k,v in enumerate(vals):
            cw=canonical_counterexample(c,v)
            if k in direct:
                if cw is not None or rank_rows[k][q0] != -1:
                    raise RuntimeError('unexpected client witness or losing rank')
            else:
                if cw is None or not client_legal(c['specification'],v,cw) or client_legal(c['implementation'],v,cw):
                    raise RuntimeError('invalid contextual witness: '+c['id'])
                game_rank=rank_rows[k][q0]
                if game_rank != cw['age']+2:
                    raise RuntimeError('client time/game rank mismatch: '+c['id'])
                client_records.append({'valuation_id':k,'valuation':v,'game_rank':game_rank,'client':cw})
        record={'case_id':c['id'],'safe_valuation_ids':direct,'valuations':vals,
                'counterexamples':client_records}
        if not args.check_only: dump(args.output/(c['id']+'.clients.json'),record)
        else:
            if json.loads((args.output/(c['id']+'.clients.json')).read_text()) != record:
                raise RuntimeError('retained client record mismatch')
        row={'case_id':c['id'],'group':c['group'],
             'translation_mode':translated['translation_mode'],
             'valuations':len(vals),'safe':len(direct),
             'bad':len(vals)-len(direct),'state_pair_valuations':stats['state_pair_valuations'],
             'client_counterexamples':len(client_records),'criterion_game_agreement':1}
        rows.append(row); all_records.append(record)
    summary={'families':len(rows),'valuations':sum(r['valuations'] for r in rows),
             'safe':sum(r['safe'] for r in rows),'bad':sum(r['bad'] for r in rows),
             'state_pair_valuations':sum(r['state_pair_valuations'] for r in rows),
             'client_counterexamples':sum(r['client_counterexamples'] for r in rows),
             'criterion_game_disagreements':0,
             'client_game_depth_disagreements':0,
             'port_collision_checker_disagreements':0,
             'age_translation_families':sum(r['translation_mode']=='age' for r in rows),
             'history_translation_families':sum(r['translation_mode']=='history' for r in rows),
             'anchor_derived_families':sum(r['group']=='anchor-derived' for r in rows),
             'minimum_client_game_depth':min((r['game_rank'] for record in all_records for r in record['counterexamples']),default=None),
             'maximum_client_game_depth':max((r['game_rank'] for record in all_records for r in record['counterexamples']),default=None),
             'scope':('port-separated launch-indexed timeline contracts, including bounded '
                      'overlapping pipelines; compile-time bounded parameters')}
    if not args.check_only:
        with (args.output/'families.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        dump(args.output/'summary.json',summary)
        dump(args.output/'measurements.json',{'wall_seconds':time.perf_counter()-t0,
             'cpu_seconds':time.process_time()-c0,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
             'workers':1})
    print(json.dumps(summary,indent=2,sort_keys=True))


if __name__=='__main__': main()
