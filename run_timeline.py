#!/usr/bin/env python3
"""Cross-check timeline criteria, persisted clients, and translated games. SPDX-License-Identifier: MIT."""
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
from timeline import safe_valuation_ids, translate_case
from timeline_check import (validate_timeline, direct_refines, check_client_record,
                            check_history_translation)


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, default=ROOT / 'timeline-results')
    ap.add_argument('--check-only', action='store_true')
    args = ap.parse_args()
    if not args.check_only:
        # Generation alone imports the producer's client constructor.  The
        # check-only path validates persisted events without that routine.
        from timeline import canonical_counterexample
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (110, 110))
    if hasattr(os, 'sched_setaffinity'):
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    args.output.mkdir(parents=True, exist_ok=True)
    rows = []
    all_records = []
    t0 = time.perf_counter()
    c0 = time.process_time()
    for path in sorted((ROOT / 'timeline-inputs').glob('*.json')):
        case = json.loads(path.read_text())
        values = validate_timeline(case)
        translated = translate_case(case)
        direct = [k for k, value in enumerate(values) if direct_refines(case, value)]
        if direct != safe_valuation_ids(case):
            raise RuntimeError('producer/checker criterion mismatch: ' + case['id'])

        if translated['translation_mode'] == 'history':
            for value in values:
                for key in ('implementation', 'specification'):
                    check_history_translation(case, key, translated[key], value)

        certificate_path = args.output / (case['id'] + '.certificate.json')
        witness_path = args.output / (case['id'] + '.witness.json')
        clients_path = args.output / (case['id'] + '.clients.json')
        if args.check_only:
            certificate = json.loads(certificate_path.read_text())
            witness = json.loads(witness_path.read_text())
            client_record = json.loads(clients_path.read_text())
        else:
            certificate = solve(translated)
            check_certificate(translated, certificate, oracle=True)
            witness = make_witness(translated, certificate)
            dump(certificate_path, certificate)
            dump(witness_path, witness)
            client_rows = []
            for valuation_id, value in enumerate(values):
                if valuation_id in direct:
                    continue
                client = canonical_counterexample(case, value)
                if client is None:
                    raise RuntimeError('missing producer client: ' + case['id'])
                client_rows.append({'valuation_id': valuation_id,
                                    'valuation': value,
                                    'game_rank': None,
                                    'client': client})
            client_record = {'case_id': case['id'],
                             'safe_valuation_ids': direct,
                             'valuations': values,
                             'counterexamples': client_rows}

        stats = check_certificate(translated, certificate, oracle=args.check_only)
        check_witness(translated, certificate, witness)
        if certificate['safe_valuation_ids'] != direct:
            raise RuntimeError('criterion/game mismatch: ' + case['id'])
        rank_rows = certificate_ranks(translated, certificate, values)
        initial_pair = (translated['implementation']['initial'] *
                        translated['specification']['states'] +
                        translated['specification']['initial'])

        if not args.check_only:
            for row in client_record['counterexamples']:
                row['game_rank'] = rank_rows[row['valuation_id']][initial_pair]
        counterexample_count = check_client_record(
            case, values, direct, client_record, rank_rows, initial_pair)
        if not args.check_only:
            dump(clients_path, client_record)

        row = {'case_id': case['id'], 'group': case['group'],
               'translation_mode': translated['translation_mode'],
               'valuations': len(values), 'safe': len(direct),
               'bad': len(values) - len(direct),
               'state_pair_valuations': stats['state_pair_valuations'],
               'client_counterexamples': counterexample_count,
               'criterion_game_agreement': 1}
        rows.append(row)
        all_records.append(client_record)

    summary = {'families': len(rows),
               'valuations': sum(row['valuations'] for row in rows),
               'safe': sum(row['safe'] for row in rows),
               'bad': sum(row['bad'] for row in rows),
               'state_pair_valuations': sum(row['state_pair_valuations'] for row in rows),
               'client_counterexamples': sum(row['client_counterexamples'] for row in rows),
               'criterion_game_disagreements': 0,
               'client_game_depth_disagreements': 0,
               'port_collision_checker_disagreements': 0,
               'age_translation_families': sum(row['translation_mode'] == 'age' for row in rows),
               'history_translation_families': sum(row['translation_mode'] == 'history'
                                                   for row in rows),
               'anchor_derived_families': sum(row['group'] == 'anchor-derived'
                                              for row in rows),
               'minimum_client_game_depth': min(
                   (row['game_rank'] for record in all_records
                    for row in record['counterexamples']), default=None),
               'maximum_client_game_depth': max(
                   (row['game_rank'] for record in all_records
                    for row in record['counterexamples']), default=None),
               'scope': ('port-separated launch-indexed timeline contracts, including bounded '
                         'overlapping pipelines; compile-time bounded parameters')}
    if not args.check_only:
        with (args.output / 'families.csv').open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        dump(args.output / 'summary.json', summary)
        dump(args.output / 'measurements.json', {
            'wall_seconds': time.perf_counter() - t0,
            'cpu_seconds': time.process_time() - c0,
            'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'workers': 1,
        })
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
