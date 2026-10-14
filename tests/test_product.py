"""Owned shared-launch product controls, separate from the retained corpus.

SPDX-License-Identifier: MIT
"""
import copy
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from timeline_product import product_cells
from timeline_product_check import check_product_partition
from timeline_check import validate_timeline,direct_refines
from timeline import translate_case
from solve import solve
from check import Invalid,check_certificate


def examples():
    return [json.loads((ROOT/'examples'/('compound-'+name+'.json')).read_text())
            for name in ('left','right')]


class ProductControls(unittest.TestCase):
    def test_exact_shared_gap_region_not_factor_intersection(self):
        left,right=examples();cells=product_cells(left,right,'compound')
        values=check_product_partition(left,right,cells)
        accepted=[]
        for cell in cells:
            vals=validate_timeline(cell);game=translate_case(cell);cert=solve(game)
            check_certificate(game,cert)
            self.assertEqual(cert['safe_valuation_ids'],[i for i,v in enumerate(vals) if direct_refines(cell,v)])
            accepted.extend(v['p'] for v in vals if direct_refines(cell,v))
        self.assertEqual(sorted(accepted),[1,2])
        self.assertEqual([v['p'] for v in values if direct_refines(left,v) and direct_refines(right,v)],[1])

    def test_partition_is_disjoint_complete_and_ties_choose_left(self):
        left,right=examples();cells=product_cells(left,right,'compound')
        values=check_product_partition(left,right,cells)
        self.assertEqual(values,[{'p':1},{'p':2},{'p':3}])
        owners=[c for c in cells if {'p':2} in validate_timeline(c)]
        self.assertEqual(len(owners),1)
        self.assertEqual(owners[0]['product_gap_owners']['implementation'],'left')

    def test_aliased_directed_ports_are_rejected(self):
        left,right=examples()
        right['implementation']['reads']={'a':[[0,1]]}
        with self.assertRaises(ValueError): product_cells(left,right,'compound')

    def test_parameter_box_mismatch_is_not_silently_joined(self):
        left,right=examples();right['parameters'][0]['hi']=2
        with self.assertRaises(ValueError): product_cells(left,right,'compound')

    def test_independent_consumer_rejects_wrong_maximum(self):
        left,right=examples();cells=product_cells(left,right,'compound')
        changed=copy.deepcopy(cells)
        for c in changed: c['implementation']['gap']=1
        with self.assertRaises(Invalid): check_product_partition(left,right,changed)

    def test_independent_consumer_rejects_partition_loss_or_overlap(self):
        left,right=examples();cells=product_cells(left,right,'compound')
        active=[c for c in cells if validate_timeline(c)]
        for changed in (active[:-1],active+[copy.deepcopy(active[0])]):
            with self.subTest(size=len(changed)),self.assertRaises(Invalid):
                check_product_partition(left,right,changed)

    def test_empty_common_admission_remains_empty(self):
        left,right=examples();right['assumption']=False
        cells=product_cells(left,right,'compound')
        self.assertEqual(check_product_partition(left,right,cells),[])
        self.assertTrue(all(not validate_timeline(cell) for cell in cells))


if __name__=='__main__': unittest.main()
