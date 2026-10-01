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
                            port_separated, collision_free, check_counterexample,
                            replay_first_violation, check_client_record,
                            check_history_translation)
from solve import solve
from check import (Invalid, check_certificate, certificate_ranks, make_witness,
                   check_witness, predicate)

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
                    self.assertEqual(rows[k][q0],w['first_violation_cycle']+2)


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

    def test_retained_client_records_replay_without_producer_reconstruction(self):
        for case in CASES.values():
            translated = translate_case(case)
            certificate = json.loads((ROOT/'timeline-results'/
                                      (case['id']+'.certificate.json')).read_text())
            check_certificate(translated, certificate)
            values = validate_timeline(case)
            ranks = certificate_ranks(translated, certificate, values)
            initial = (translated['implementation']['initial'] *
                       translated['specification']['states'] +
                       translated['specification']['initial'])
            record = json.loads((ROOT/'timeline-results'/
                                 (case['id']+'.clients.json')).read_text())
            count = check_client_record(case, values, certificate['safe_valuation_ids'],
                                        record, ranks, initial)
            self.assertEqual(count, len(values)-len(certificate['safe_valuation_ids']))

    def test_shifted_persisted_client_requires_absolute_time_replay(self):
        case = CASES['timeline-extra-read-port']
        value = validate_timeline(case)[0]
        row = json.loads((ROOT/'timeline-results'/
                          'timeline-extra-read-port.clients.json').read_text())['counterexamples'][0]
        shifted = copy.deepcopy(row['client'])
        shifted['launches'] = [launch + 1 for launch in shifted['launches']]
        for field in ('drives', 'samples'):
            for event in shifted[field]:
                event['launch'] += 1
                event['time'] += 1
        # The shifted fixture preserves specification/implementation legality and
        # the superficial rank == age + 2 relation, but its real violation is at cycle 2.
        self.assertTrue(client_legal(case['specification'], value, shifted))
        self.assertFalse(client_legal(case['implementation'], value, shifted))
        self.assertEqual(row['game_rank'], shifted['age'] + 2)
        self.assertEqual(replay_first_violation(case, value, shifted)['cycle'], 2)
        self.assertEqual(shifted['first_violation_cycle'], 1)
        with self.assertRaises(Invalid):
            check_counterexample(case, value, shifted, row['game_rank'])

    def test_counterexample_metadata_and_rank_mutations_are_rejected(self):
        case = CASES['timeline-extra-read-port']
        value = validate_timeline(case)[0]
        row = json.loads((ROOT/'timeline-results'/
                          'timeline-extra-read-port.clients.json').read_text())['counterexamples'][0]
        check_counterexample(case, value, row['client'], row['game_rank'])
        mutations = [
            ('first cycle', lambda c: c.update(first_violation_cycle=0), row['game_rank']),
            ('kind', lambda c: c.update(kind='write'), row['game_rank']),
            ('port', lambda c: c.update(port='x'), row['game_rank']),
            ('age', lambda c: c.update(age=0), row['game_rank']),
            ('rank', lambda c: None, row['game_rank'] + 1),
        ]
        for name, mutate, rank in mutations:
            with self.subTest(name=name):
                client = copy.deepcopy(row['client'])
                mutate(client)
                with self.assertRaises(Invalid):
                    check_counterexample(case, value, client, rank)

    def test_equal_time_failure_tie_mutation_is_rejected(self):
        case = {
            'id': 'timeline-equal-time-tie', 'group': 'unit', 'horizon': 2,
            'parameters': [{'name': 'p', 'lo': 0, 'hi': 0}], 'assumption': True,
            'implementation': {
                'gap': 2, 'reads': {'x': [[1, 2]]}, 'writes': {}},
            'specification': {
                'gap': 1, 'reads': {}, 'writes': {'y': [[1, 2]]}},
        }
        value = validate_timeline(case)[0]
        translated = translate_case(case)
        certificate = solve(translated)
        check_certificate(translated, certificate)
        ranks = certificate_ranks(translated, certificate, [value])
        initial = (translated['implementation']['initial'] *
                   translated['specification']['states'] +
                   translated['specification']['initial'])
        rank = ranks[0][initial]
        client = canonical_counterexample(case, value)
        self.assertEqual((client['kind'], client['first_violation_cycle']), ('gap', 1))
        check_counterexample(case, value, client, rank)
        client.update(kind='read', port='x', age=1)
        with self.assertRaises(Invalid):
            check_counterexample(case, value, client, rank)

    def test_all_tags_share_one_physical_collision_domain(self):
        profile = {'gap': 1, 'reads': {'x': [[0, 1]]}, 'writes': {}}
        colliding = {
            'launches': [0, 1],
            'drives': [
                {'port': 'x', 'launch': 0, 'age': 0, 'time': 0},
                {'port': 'x', 'launch': 1, 'age': 0, 'time': 1},
                {'port': 'x', 'launch': 0, 'age': 1, 'time': 1},
            ],
            'samples': [],
        }
        self.assertFalse(client_legal(profile, {}, colliding))

    def test_noncolliding_optional_drive_is_legal_and_removable(self):
        profile = {'gap': 1, 'reads': {'x': [[0, 1]]}, 'writes': {}}
        client = {
            'launches': [0, 1],
            'drives': [
                {'port': 'x', 'launch': 0, 'age': 0, 'time': 0},
                {'port': 'x', 'launch': 1, 'age': 0, 'time': 1},
                {'port': 'x', 'launch': 0, 'age': 2, 'time': 2},
            ],
            'samples': [],
        }
        self.assertTrue(client_legal(profile, {}, client))
        normalized = copy.deepcopy(client)
        normalized['drives'] = normalized['drives'][:2]
        self.assertTrue(client_legal(profile, {}, normalized))

    def test_client_tags_require_actual_nonnegative_launch_owners(self):
        profile = {'gap': 1, 'reads': {'x': [[0, 1]]}, 'writes': {}}
        legal = {
            'launches': [0],
            'drives': [{'port': 'x', 'launch': 0, 'age': 0, 'time': 0}],
            'samples': [],
        }
        self.assertTrue(client_legal(profile, {}, legal))
        orphan = copy.deepcopy(legal)
        orphan['drives'][0].update(launch=1, time=1)
        self.assertFalse(client_legal(profile, {}, orphan))
        negative = {'launches': [-1], 'drives': [], 'samples': []}
        self.assertFalse(client_legal({'gap': 1, 'reads': {}, 'writes': {}}, {}, negative))

    def test_history_actions_preserve_old_transaction_and_drop_boundary(self):
        case = {
            'id': 'timeline-action-regression', 'group': 'unit', 'horizon': 2,
            'parameters': [{'name': 'p', 'lo': 0, 'hi': 0}], 'assumption': True,
            'implementation': {
                'gap': 1, 'reads': {'x': [[2, 3]]}, 'writes': {'o': [[2, 3]]}},
            'specification': {
                'gap': 1, 'reads': {'x': [[2, 3]]}, 'writes': {'o': [[2, 3]]}},
        }
        value = validate_timeline(case)[0]
        translated = translate_case(case)['implementation']
        check_history_translation(case, 'implementation', translated, value)
        states = [tuple(state) for state in translated['history_states']]
        index = {state: sid for sid, state in enumerate(states)}

        def target(state, label):
            matches = [edge for edge in translated['edges']
                       if edge['from'] == index[state] and edge['label'] == label
                       and predicate(edge['guard'], value)]
            self.assertEqual(len(matches), 1)
            return states[matches[0]['to']]

        self.assertEqual(target((), 'launch'), (0,))
        self.assertEqual(target((0,), 'tick'), (1,))
        self.assertEqual(target((1,), 'launch'), (0, 1))
        self.assertEqual(target((0, 1), 'tick'), (1, 2))
        enabled = {edge['label'] for edge in translated['edges']
                   if edge['from'] == index[(1, 2)] and predicate(edge['guard'], value)}
        self.assertIn('sample:o@2', enabled)
        self.assertIn('need:x@2', enabled)
        self.assertEqual(target((1, 2), 'tick'), (2,))
        self.assertEqual(target((2,), 'tick'), ())

    def test_latest_launch_only_action_mutation_is_rejected(self):
        case = {
            'id': 'timeline-action-mutation', 'group': 'unit', 'horizon': 2,
            'parameters': [{'name': 'p', 'lo': 0, 'hi': 0}], 'assumption': True,
            'implementation': {
                'gap': 1, 'reads': {'x': [[2, 3]]}, 'writes': {'o': [[2, 3]]}},
            'specification': {
                'gap': 1, 'reads': {'x': [[2, 3]]}, 'writes': {'o': [[2, 3]]}},
        }
        value = validate_timeline(case)[0]
        translated = translate_case(case)['implementation']
        states = [tuple(state) for state in translated['history_states']]
        mutated = copy.deepcopy(translated)
        retained = []
        for edge in mutated['edges']:
            state = states[edge['from']]
            if len(state) > 1 and (edge['label'].startswith('sample:') or
                                   edge['label'].startswith('need:')):
                action_age = int(edge['label'].rsplit('@', 1)[1])
                # Faulty quotient: keep only the newest launch, whose age is min(state).
                if action_age != min(state):
                    continue
            retained.append(edge)
        mutated['edges'] = retained
        with self.assertRaises(Invalid):
            check_history_translation(case, 'implementation', mutated, value)


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
