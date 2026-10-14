"""Check product semantics and exact cell coverage without importing producer.

SPDX-License-Identifier: MIT
"""
from check import need
from timeline_check import validate_timeline,evaluated


def check_product_partition(left,right,cells):
    lv=validate_timeline(left);rv=validate_timeline(right)
    need(left['parameters']==right['parameters'],'product parameter domain mismatch')
    expected=[v for v in lv if v in rv]
    names=[p['name'] for p in left['parameters']]
    identity=lambda v:tuple(v[n] for n in names)
    observed=set()
    all_ports=[]
    for factor in (left,right):
        all_ports.append(set().union(*(set(factor[s].get(k,{}))
            for s in ('implementation','specification') for k in ('reads','writes'))))
    need(not(all_ports[0]&all_ports[1]),'product port alias')
    need(type(cells) is list and len(cells)<=4,'bounded product cells')
    for cell in cells:
        need(cell['parameters']==left['parameters'],'product changed parameter box')
        need(cell['horizon']==max(left['horizon'],right['horizon']),'product horizon mismatch')
        for env in validate_timeline(cell):
            key=identity(env)
            need(env in expected and key not in observed,'product cell domain loss or overlap')
            observed.add(key)
            for side in ('implementation','specification'):
                l,r=evaluated(left[side],env),evaluated(right[side],env)
                actual=evaluated(cell[side],env)
                want={'gap':max(l['gap'],r['gap']),
                      **{kind:{**l[kind],**r[kind]} for kind in ('reads','writes')}}
                need(actual==want,'product max/port-map semantics mismatch')
                owner='left' if l['gap']>=r['gap'] else 'right'
                need(cell.get('product_gap_owners',{}).get(side)==owner,'product gap-owner binding')
    need(observed=={identity(v) for v in expected},'product cell coverage incomplete')
    return expected
