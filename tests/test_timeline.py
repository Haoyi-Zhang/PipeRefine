"""Timeline correspondence, contextual witnesses, and schema controls. SPDX-License-Identifier: MIT."""
import copy
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from generate_timeline import all_timeline_cases
from timeline import (translate_case, safe_valuation_ids, canonical_counterexample,
                      profile_sets, translation_mode)
from timeline_check import (validate_timeline, direct_refines, client_legal,
                            port_separated, collision_free)
from solve import solve
from check import Invalid, check_certificate, certificate_ranks, make_witness, check_witness

CASES={c['id']:c for c in all_timeline_cases()}


class TimelineCorrespondence(unittest.TestCase):
    def test_input_files_exact_rebuild(self):
        files={p.stem:p for p in (ROOT/'timeline-inputs').glob('*.json')}
        self.assertEqual(set(files),set(CASES))
        for name,c in CASES.items():
            self.assertEqual(files[name].read_text(),json.dumps(c,indent=2,sort_keys=True)+'\n')

    def test_all_families_criterion_equals_game(self):
        for c in CASES.values():
            vals=validate_timeline(c); cert=solve(translate_case(c)); check_certificate(translate_case(c),cert)
            self.assertEqual(cert['safe_valuation_ids'],[k for k,v in enumerate(vals) if direct_refines(c,v)])
            self.assertEqual(cert['safe_valuation_ids'],safe_valuation_ids(c))

    def test_all_failures_have_contextual_counterexample(self):
        for c in CASES.values():
            for v in validate_timeline(c):
                w=canonical_counterexample(c,v)
                if direct_refines(c,v): self.assertIsNone(w)
                else:
                    self.assertIsNotNone(w)
                    self.assertTrue(client_legal(c['specification'],v,w))
                    self.assertFalse(client_legal(c['implementation'],v,w))

    def test_client_time_matches_game_rank(self):
        for c in CASES.values():
            translated=translate_case(c)
            cert=solve(translated)
            vals=validate_timeline(c)
            rows=certificate_ranks(translated,cert,vals)
            q0=translated['implementation']['initial']*translated['specification']['states']+translated['specification']['initial']
            for k,v in enumerate(vals):
                w=canonical_counterexample(c,v)
                if w is None:
                    self.assertEqual(rows[k][q0],-1)
                else:
                    self.assertEqual(rows[k][q0],w['age']+2)


    def test_anchor_shapes_use_history_translation(self):
        for name in ('timeline-anchor-fpadd', 'timeline-anchor-shift',
                     'timeline-anchor-highrad'):
            case = CASES[name]
            translated = translate_case(case)
            self.assertEqual(translation_mode(case), 'history')
            self.assertEqual(translated['implementation']['encoding'], 'launch-history')
            self.assertLessEqual(translated['implementation']['states'], 48)
            self.assertEqual(safe_valuation_ids(case),
                             [k for k, value in enumerate(validate_timeline(case))
                              if value['p'] == value['q']])

    def test_history_translation_represents_overlapping_launches(self):
        translated = translate_case(CASES['timeline-anchor-fpadd'])['implementation']
        states = [tuple(state) for state in translated['history_states']]
        index = {state: k for k, state in enumerate(states)}
        self.assertEqual(states[translated['initial']], ())
        launch0 = [edge for edge in translated['edges']
                   if edge['from'] == translated['initial'] and edge['label'] == 'launch'][0]
        self.assertEqual(states[launch0['to']], (0,))
        tick = [edge for edge in translated['edges']
                if edge['from'] == index[(0,)] and edge['label'] == 'tick'][0]
        self.assertEqual(states[tick['to']], (1,))
        launch1 = [edge for edge in translated['edges']
                   if edge['from'] == index[(1,)] and edge['label'] == 'launch'][0]
        self.assertEqual(states[launch1['to']], (0, 1))

    def test_port_span_matches_exhaustive_collision_check(self):
        for case in CASES.values():
            for value in validate_timeline(case):
                for side in ('implementation', 'specification'):
                    self.assertEqual(port_separated(case[side], value),
                                     collision_free(case[side], value))

    def test_transaction_tags_prevent_cross_launch_borrowing(self):
        spec = {'gap': 1, 'reads': {'x': [[2, 3]]}, 'writes': {}}
        impl = {'gap': 1, 'reads': {'x': [[1, 2]]}, 'writes': {}}
        client = {
            'launches': [0, 1],
            'drives': [
                {'port': 'x', 'launch': 0, 'age': 2, 'time': 2},
                {'port': 'x', 'launch': 1, 'age': 2, 'time': 3},
            ],
            'samples': [],
        }
        self.assertTrue(client_legal(spec, {}, client))
        # The physical event at cycle 2 is tagged for launch 0 and cannot satisfy
        # the replacement's launch-1/age-1 obligation.
        self.assertFalse(client_legal(impl, {}, client))

    def test_translated_witnesses_check(self):
        for name in ('timeline-gap','timeline-read-window','timeline-write-window','timeline-combined'):
            c=translate_case(CASES[name]); cert=solve(c); w=make_witness(c,cert)
            check_certificate(c,cert); check_witness(c,cert,w)

    def test_gap_direction(self):
        c=CASES['timeline-gap']; vals=validate_timeline(c)
        self.assertEqual(safe_valuation_ids(c),[k for k,v in enumerate(vals)
                         if profile_sets(c['implementation'],v)['gap']<=profile_sets(c['specification'],v)['gap']])

    def test_read_is_contravariant(self):
        c=CASES['timeline-read-window']; vals=validate_timeline(c)
        for k,v in enumerate(vals):
            i=profile_sets(c['implementation'],v)['reads']['x']; s=profile_sets(c['specification'],v)['reads']['x']
            self.assertEqual(k in safe_valuation_ids(c),i<=s)

    def test_write_is_covariant(self):
        c=CASES['timeline-write-window']; vals=validate_timeline(c)
        for k,v in enumerate(vals):
            i=profile_sets(c['implementation'],v)['writes']['y']; s=profile_sets(c['specification'],v)['writes']['y']
            self.assertEqual(k in safe_valuation_ids(c),s<=i)

    def test_extra_read_port_fails(self):
        c=CASES['timeline-extra-read-port']; self.assertEqual(safe_valuation_ids(c),[])
        w=canonical_counterexample(c,validate_timeline(c)[0]); self.assertEqual(w['kind'],'read'); self.assertEqual(w['port'],'coef')

    def test_missing_write_port_fails(self):
        c=CASES['timeline-missing-write-port']; self.assertEqual(safe_valuation_ids(c),[])
        w=canonical_counterexample(c,validate_timeline(c)[0]); self.assertEqual(w['kind'],'write'); self.assertEqual(w['port'],'flag')

    def test_extra_write_port_is_allowed(self):
        # Both sides declare the extra guarantee identically in this control.
        c=CASES['timeline-extra-write-port']; self.assertEqual(len(safe_valuation_ids(c)),4)

    def test_disjoint_intervals(self):
        self.assertEqual(len(safe_valuation_ids(CASES['timeline-disjoint-read'])),4)
        self.assertEqual(len(safe_valuation_ids(CASES['timeline-disjoint-write'])),4)

    def test_assumption_filters_domain(self):
        c=CASES['timeline-correlated-assumption']; vals=validate_timeline(c)
        self.assertEqual(len(vals),10); self.assertTrue(all(v['p']<=v['q'] for v in vals))

    def test_reflexive_generated_controls(self):
        for n in range(9,53,9):
            c=CASES['timeline-generated-'+str(n).zfill(2)]
            self.assertEqual(len(safe_valuation_ids(c)),len(validate_timeline(c)))

    def test_initial_state_is_quiescent(self):
        c=translate_case(CASES['timeline-identical']); h=CASES['timeline-identical']['horizon']
        self.assertEqual(c['implementation']['initial'],h)
        launch=[e for e in c['implementation']['edges'] if e['from']==h and e['label']=='launch']
        self.assertEqual(len(launch),1); self.assertEqual(launch[0]['to'],0)

    def test_tick_saturates(self):
        c=translate_case(CASES['timeline-identical']); h=CASES['timeline-identical']['horizon']
        tick=[e for e in c['implementation']['edges'] if e['from']==h and e['label']=='tick'][0]
        self.assertEqual(tick['to'],h)

    def test_counterexample_canonical_priority(self):
        c=CASES['timeline-combined']
        for v in validate_timeline(c):
            w=canonical_counterexample(c,v)
            if w:
                self.assertIn(w['kind'],('gap','read','write'))
                self.assertEqual(w['launches'][0],0)


class TimelineSchemaControls(unittest.TestCase):
    def reject(self,mutate):
        c=copy.deepcopy(CASES['timeline-identical']); mutate(c)
        with self.assertRaises(Invalid): validate_timeline(c)
    def test_horizon_too_large(self): self.reject(lambda c:c.update(horizon=9))
    def test_zero_gap(self): self.reject(lambda c:c['implementation'].update(gap=0))
    def test_gap_beyond_horizon(self): self.reject(lambda c:c['implementation'].update(gap=8))
    def test_interval_negative(self): self.reject(lambda c:c['implementation']['reads'].update(x=[[-1,1]]))
    def test_interval_empty(self): self.reject(lambda c:c['implementation']['reads'].update(x=[[1,1]]))
    def test_interval_after_gap(self): self.reject(lambda c:c['implementation']['reads'].update(x=[[0,5]]))
    def test_overlapping_intervals(self): self.reject(lambda c:c['implementation']['reads'].update(x=[[0,2],[1,3]]))
    def test_direction_collision(self): self.reject(lambda c:c['implementation']['writes'].update(x=[[2,3]]))
    def test_too_many_ports(self):
        self.reject(lambda c:c['implementation'].update(reads={str(i):[[0,1]] for i in range(7)}))

    def test_late_singletons_are_allowed(self):
        case = copy.deepcopy(CASES['timeline-identical'])
        for side in ('implementation', 'specification'):
            case[side] = {'gap': 1, 'reads': {'x': [[5, 6]]},
                          'writes': {'y': [[6, 7]]}}
        self.assertTrue(validate_timeline(case))

    def test_same_port_span_at_gap_is_rejected(self):
        self.reject(lambda c: c['implementation'].update(
            gap=2, reads={'x': [[0, 1], [2, 3]]}, writes={}))

    def test_bad_parameter_bound(self): self.reject(lambda c:c['parameters'][0].update(hi=9))
    def test_unknown_parameter(self): self.reject(lambda c:c['implementation'].update(gap='z'))
    def test_variable_product(self): self.reject(lambda c:c['implementation'].update(gap=['*','p','p']))


if __name__=='__main__': unittest.main()
