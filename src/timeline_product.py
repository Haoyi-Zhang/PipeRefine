"""Compile a synchronous disjoint-port product into at most four gap cells.

The existing expression grammar lacks max/ite. Disjoint Presburger guards select
each maximum, with ties assigned left, without changing that grammar or adding
asynchronous wiring/value semantics. SPDX-License-Identifier: MIT
"""
from copy import deepcopy
from itertools import product
from timeline_check import validate_timeline


def product_cells(left,right,identifier):
    validate_timeline(left);validate_timeline(right)
    if left['parameters']!=right['parameters']:
        raise ValueError('product requires the same declared parameter box and order')
    if type(identifier) is not str or not identifier:
        raise ValueError('product identifier required')
    ports=[]
    for factor in (left,right):
        ports.append(set().union(*(set(factor[side].get(kind,{}))
            for side in ('implementation','specification') for kind in ('reads','writes'))))
    if ports[0]&ports[1]: raise ValueError('product factors require disjoint physical ports')
    cells=[]
    for io,so in product((0,1),repeat=2):
        guards=[deepcopy(left['assumption']),deepcopy(right['assumption'])]
        cell={'id':identifier+'-i'+str(io)+'-s'+str(so),'group':'synchronous-product',
              'horizon':max(left['horizon'],right['horizon']),
              'parameters':deepcopy(left['parameters']),
              'product_gap_owners':{}}
        for side,owner in (('implementation',io),('specification',so)):
            l,r=left[side],right[side]
            # Disjoint and exhaustive, including ties. No new arithmetic operator.
            guards.append(['<=',deepcopy(r['gap']),deepcopy(l['gap'])] if owner==0
                          else ['<',deepcopy(l['gap']),deepcopy(r['gap'])])
            cell[side]={'gap':deepcopy((l,r)[owner]['gap']),
                **{kind:{**deepcopy(l.get(kind,{})),**deepcopy(r.get(kind,{}))}
                   for kind in ('reads','writes')}}
            cell['product_gap_owners'][side]=('left','right')[owner]
        cell['assumption']=['and',*guards]
        validate_timeline(cell)
        cells.append(cell)
    return cells
