"""Semantic controls and certificate mutation tests. SPDX-License-Identifier: MIT."""
import copy
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from solve import solve
from check import (Invalid,validate_case,check_certificate,check_witness,make_witness,
                   predicate,arena,exact_oracle)
from generate import all_cases


CASES={c['id']:c for c in all_cases()}


def checked(name):
    c=CASES[name];cert=solve(c);check_certificate(c,cert);w=make_witness(c,cert);check_witness(c,cert,w)
    return c,cert,w


def acyclic_output_language(a):
    result=set();stack=[(a['initial'],(),frozenset())]
    while stack:
        q,word,path=stack.pop()
        if q in path:raise ValueError('not acyclic')
        result.add(word)
        for e in a['edges']:
            if e['from']==q:
                if e['kind']!='out' or e['guard'] is not True:raise ValueError('outside finite trace fixture')
                stack.append((e['to'],word+(e['label'],),path|{q}))
    return result


class SemanticControls(unittest.TestCase):
    def test_input_files_exact_rebuild(self):
        files={p.stem:p for p in (ROOT/'inputs').glob('*.json')}
        self.assertEqual(set(files),set(CASES))
        for name,c in CASES.items():
            self.assertEqual(files[name].read_text(),json.dumps(c,indent=2,sort_keys=True)+'\n')

    def test_branching_requires_strategy_not_word(self):
        c,cert,w=checked('branching')
        self.assertEqual(cert['safe_valuation_ids'],[])
        self.assertEqual(w['depth'],2)
        self.assertEqual(len(w['nodes'][str(w['root'])]['replies']),2)
        I,S=(acyclic_output_language(c[a]) for a in ('implementation','specification'))
        self.assertEqual(I,S)
        self.assertEqual(I,{(),('a',),('a','b'),('a','c')})

    def test_pointwise_quantifier(self):
        c,cert,_=checked('pointwise-choice')
        self.assertEqual(len(cert['safe_valuation_ids']),4)
        # No one specification edge is enabled throughout the family.
        self.assertFalse(any(all(predicate(e['guard'],p) for p in cert['valuations'])
                             for e in c['specification']['edges']))

    def test_interior_is_not_determined_by_corners(self):
        _,cert,w=checked('interior-hole')
        self.assertEqual(cert['safe_valuation_ids'],[0,1,2,4,5,6,7])
        self.assertEqual(w['valuation'],{'p':3})

    def test_parity_not_monotone(self):
        _,cert,_=checked('parity')
        self.assertEqual(cert['safe_valuation_ids'],[0,2,4,6])

    def test_correlation_not_a_bounding_box(self):
        _,cert,_=checked('correlated')
        safe=[cert['valuations'][i] for i in cert['safe_valuation_ids']]
        self.assertEqual(safe,[{'x':i,'y':i} for i in range(4)])

    def test_input_contravariance(self):
        _,cert,_=checked('input-variance')
        self.assertEqual(cert['safe_valuation_ids'],[0,2,4,6])

    def test_environment_input_restriction(self):
        _,cert,_=checked('input-assumption')
        self.assertEqual(cert['safe_valuation_ids'],[1,2,3])

    def test_empty_domain_is_vacuous(self):
        _,cert,w=checked('empty-domain')
        self.assertEqual(cert['valuations'],[])
        self.assertEqual(cert['cells'],[]);self.assertIsNone(w)

    def test_no_progress_claim(self):
        _,cert,w=checked('quiescence-not-progress')
        self.assertEqual(len(cert['safe_valuation_ids']),4);self.assertIsNone(w)

    def test_global_shortest_order(self):
        _,cert,w=checked('shortest-order')
        self.assertEqual(w['valuation'],{'p':1});self.assertEqual(w['depth'],1)

    def test_window_closed_form(self):
        _,cert,_=checked('availability-window')
        expected=[k for k,p in enumerate(cert['valuations']) if p['new']<=p['old']<=p['new']+1]
        self.assertEqual(cert['safe_valuation_ids'],expected)

    def test_gap_closed_form(self):
        _,cert,_=checked('initiation-gap')
        self.assertEqual(cert['safe_valuation_ids'],[k for k,p in enumerate(cert['valuations']) if p['new']<=p['old']])

    def test_phase_closed_form(self):
        _,cert,_=checked('phase-alignment')
        self.assertEqual(cert['safe_valuation_ids'],[k for k,p in enumerate(cert['valuations']) if (p['latency']+p['phase'])%2==0])

    def test_boolean_safe_index_rejected(self):
        c,cert,_=checked('reflexive')
        cert['safe_valuation_ids'][0]=False
        with self.assertRaises(Invalid):check_certificate(c,cert)

    def test_reflexivity(self):
        _,cert,w=checked('reflexive')
        self.assertEqual(len(cert['safe_valuation_ids']),4);self.assertIsNone(w)


class CertificateMutations(unittest.TestCase):
    def setUp(self):self.case,self.cert,self.witness=checked('branching')
    def reject_cert(self,mutate):
        c=copy.deepcopy(self.cert);mutate(c)
        with self.assertRaises(Invalid):check_certificate(self.case,c)
    def reject_witness(self,mutate):
        w=copy.deepcopy(self.witness);mutate(w)
        with self.assertRaises(Invalid):check_witness(self.case,self.cert,w)

    def test_coverage(self):self.reject_cert(lambda c:c['cells'].clear())
    def test_overlap(self):self.reject_cert(lambda c:c['cells'].append(copy.deepcopy(c['cells'][0])))
    def test_valuation_binding(self):self.reject_cert(lambda c:c['valuations'][0].update(p=1))
    def test_valuation_outside_domain(self):self.reject_cert(lambda c:c['cells'][0]['valuation_ids'].append(1))
    def test_boolean_valuation_id(self):self.reject_cert(lambda c:c['cells'][0].update(valuation_ids=[False]))
    def test_boolean_parameter_value(self):self.reject_cert(lambda c:c['valuations'][0].update(p=False))
    def test_boolean_global_selection(self):self.reject_cert(lambda c:c.update(shortest_bad_valuation_id=False))
    def test_round_counter(self):self.reject_cert(lambda c:c.update(rounds=99))
    def test_visit_counter(self):self.reject_cert(lambda c:c.update(equation_visits=0))
    def test_boolean_witness_parameter(self):self.reject_witness(lambda w:w['valuation'].update(p=False))
    def test_boolean_witness_edge(self):self.reject_witness(lambda w:w['nodes'][str(w['root'])].update(edge=False))
    def test_rank_dimension(self):self.reject_cert(lambda c:c['cells'][0]['ranks'].pop())
    def test_false_safe(self):self.reject_cert(lambda c:c['cells'][0]['ranks'].__setitem__(0,-1))
    def test_nonminimal_rank(self):self.reject_cert(lambda c:c['cells'][0]['ranks'].__setitem__(0,3))
    def test_safe_region_omission_or_addition(self):self.reject_cert(lambda c:c.update(safe_valuation_ids=[0]))
    def test_global_selection(self):self.reject_cert(lambda c:c.update(shortest_bad_valuation_id=None))
    def test_branch_omission(self):self.reject_witness(lambda w:w['nodes'][str(w['root'])]['replies'].pop())
    def test_missing_leaf(self):self.reject_witness(lambda w:w['nodes'].pop(str(w['nodes'][str(w['root'])]['replies'][0])))
    def test_nonminimal_witness_depth(self):self.reject_witness(lambda w:w.update(depth=3))
    def test_wrong_challenge(self):self.reject_witness(lambda w:w['nodes'][str(w['root'])].update(label='b'))
    def test_extraneous_node(self):self.reject_witness(lambda w:w['nodes'].update({'99':copy.deepcopy(w['nodes'][str(w['root'])])}))


class SchemaControls(unittest.TestCase):
    def reject_case(self,mutate):
        c=copy.deepcopy(CASES['input-variance']);mutate(c)
        with self.assertRaises(Invalid):validate_case(c)
    def test_variable_multiplication(self):
        self.reject_case(lambda c:c.update(assumption=['==',['*','p','p'],0]))
    def test_nonpositive_modulus(self):
        self.reject_case(lambda c:c.update(assumption=['==',['%','p',0],0]))
    def test_parameter_out_of_range(self):self.reject_case(lambda c:c['parameters'][0].update(hi=8))
    def test_input_nondeterminism(self):
        def mutate(c):
            a=c['implementation'];a['states']=2;a['edges'].append({'from':0,'to':1,'label':'launch','kind':'in','guard':True})
        self.reject_case(mutate)
    def test_polarity_collision(self):
        self.reject_case(lambda c:c['implementation']['edges'][0].update(kind='out'))


if __name__=='__main__':unittest.main()
