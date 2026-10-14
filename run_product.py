#!/usr/bin/env python3
"""Exact shared-launch product workflow; owned contracts, not source/RTL wiring.

SPDX-License-Identifier: MIT
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from timeline_product import product_cells
from timeline_product_check import check_product_partition
from timeline import translate_case,canonical_counterexample
from timeline_check import validate_timeline,direct_refines,check_client_record,check_history_translation
from solve import solve
from check import check_certificate,certificate_ranks,make_witness,check_witness
from runtime_limits import configure,check_cpu,peak_rss_kib,scientific_equal


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('left',type=Path);parser.add_argument('right',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--portable',action='store_true')
    parser.add_argument('--check-only',action='store_true',help='replay stored product cases/certificates/clients without constructors')
    args=parser.parse_args()
    output=args.output.resolve()
    if not args.check_only and (output.is_relative_to(ROOT) or output.exists()):
        raise ValueError('fresh external output required')
    limits=configure(args.portable);cpu,wall=time.process_time(),time.perf_counter()
    left,right=[json.loads(p.read_text(encoding='utf-8')) for p in (args.left,args.right)]
    if args.check_only:
        if not scientific_equal(json.loads((output/'inputs.json').read_text()),{'left':left,'right':right}):
            raise ValueError('trusted product input binding differs')
        cells=[]
        for path in sorted(output.glob('*.case.json')):
            cell=json.loads(path.read_text())
            if type(cell.get('id')) is not str or cell['id']+'.case.json'!=path.name:
                raise ValueError('stored product case basename binding differs')
            cells.append(cell)
    else:
        cells=product_cells(left,right,'compound')
    values=check_product_partition(left,right,cells)
    if not args.check_only: output.mkdir(parents=True,exist_ok=False)
    def dump(name,data):
        (output/name).write_text(json.dumps(data,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
    if not args.check_only: dump('inputs.json',{'left':left,'right':right})
    rows=[];accepted=[]
    for cell in cells:
        check_cpu()
        vals=validate_timeline(cell);game=translate_case(cell)
        if game['translation_mode']=='history':
            for env in vals:
                for side in ('implementation','specification'): check_history_translation(cell,side,game[side],env)
        if args.check_only:
            cert=json.loads((output/(cell['id']+'.certificate.json')).read_text())
            witness=json.loads((output/(cell['id']+'.witness.json')).read_text())
        else:
            cert=solve(game)
            witness=make_witness(game,cert)
        check_certificate(game,cert);check_witness(game,cert,witness)
        ranks=certificate_ranks(game,cert,vals)
        q0=game['implementation']['initial']*game['specification']['states']+game['specification']['initial']
        safe=[i for i,v in enumerate(vals) if direct_refines(cell,v)]
        if safe!=cert['safe_valuation_ids']: raise RuntimeError('product criterion/game disagreement')
        record=json.loads((output/(cell['id']+'.clients.json')).read_text()) if args.check_only else {
            'case_id':cell['id'],'valuations':vals,'safe_valuation_ids':safe,'counterexamples':[
            {'valuation_id':i,'valuation':v,'game_rank':ranks[i][q0],'client':canonical_counterexample(cell,v)}
            for i,v in enumerate(vals) if i not in safe]}
        check_client_record(cell,vals,safe,record,ranks,q0)
        if not args.check_only:
            for suffix,data in (('case',cell),('certificate',cert),('witness',witness),('clients',record)):
                dump(cell['id']+'.'+suffix+'.json',data)
        accepted.extend(vals[i] for i in safe)
        rows.append({'cell':cell['id'],'valuations':len(vals),'safe':len(safe)})
    factor_intersection=[v for v in values if direct_refines(left,v) and direct_refines(right,v)]
    summary={'scope':'one owned synchronous disjoint-port example; not a new benchmark denominator or wiring theorem',
             'valuations':values,'safe_valuations':[v for v in values if v in accepted],
             'factor_intersection_sufficient_control':factor_intersection,
             'recovered_valuations':[v for v in values if v in accepted and v not in factor_intersection],
             'cells':rows,'same_guarantee_note':'factor intersection is sufficient only, not the exact baseline',
             'source_sha256':{p.relative_to(ROOT).as_posix():sha256(p.read_bytes()).hexdigest() for p in
                [Path(__file__),*(ROOT/'src'/name for name in ('timeline_product.py','timeline_product_check.py','timeline.py',
                 'timeline_check.py','domain.py','solve.py','check.py','runtime_limits.py'))]},
             'input_sha256':{key:sha256(p.read_bytes()).hexdigest() for key,p in (('left',args.left),('right',args.right))}}
    if args.check_only:
        retained=json.loads((output/'summary.json').read_text())
        fields=('valuations','safe_valuations','factor_intersection_sufficient_control','recovered_valuations','cells')
        if not scientific_equal({k:retained[k] for k in fields},{k:summary[k] for k in fields}):
            raise ValueError('product semantic summary differs')
    else:
        dump('summary.json',summary)
        dump('measurements.json',{'cpu_seconds':time.process_time()-cpu,'wall_seconds':time.perf_counter()-wall,
                            'peak_rss_kib':peak_rss_kib(),'runtime_limits':limits})
    print(json.dumps(summary,indent=2))


if __name__=='__main__': main()
