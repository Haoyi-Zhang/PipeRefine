"""Bitset greatest fixed point and rank-stable certificate partitions.

SPDX-License-Identifier: MIT
This is an exact bounded reference prototype, not a new featured-game algorithm.
"""
from domain import valuations, masks, guard


def solve(case):
    values = valuations(case)
    m, n = case['implementation']['states'], case['specification']['states']
    all_values = (1 << len(values)) - 1
    I, S = masks(case, values)
    environment = {label: sum(1 << k for k,p in enumerate(values) if guard(pred,p))
                   for label,pred in case['environment_inputs'].items()}
    # Each challenge has an enabling mask and alternative response masks/targets.
    obligations = [[] for _ in range(m*n)]
    for i in range(m):
        for s in range(n):
            q = i*n+s
            for eid,kind,label,target,enabled in S[s]:
                if kind != 'in': continue
                allowed = environment.get(label, all_values)
                replies = [(j*n+target,g) for _,k,l,j,g in I[i] if k=='in' and l==label]
                obligations[q].append((enabled & allowed, replies))
            for eid,kind,label,target,enabled in I[i]:
                if kind != 'out': continue
                replies = [(target*n+t,g) for _,k,l,t,g in S[s] if k=='out' and l==label]
                obligations[q].append((enabled,replies))
    winning = [all_values]*(m*n)
    ranks = [[-1]*(m*n) for _ in values]
    rounds = 0
    equation_visits = 0
    while True:
        new = []
        for q, challenges in enumerate(obligations):
            keep = all_values
            for enabled, replies in challenges:
                matched = 0
                for target, enabled_reply in replies:
                    matched |= enabled_reply & winning[target]
                keep &= (all_values ^ enabled) | matched
            new.append(keep)
        equation_visits += m*n
        if new == winning:
            break
        rounds += 1
        if rounds > m*n:
            raise AssertionError('finite-state rank bound violated')
        for q, (old, now) in enumerate(zip(winning,new)):
            if now & ~old:
                raise AssertionError('non-monotone descent')
            removed = old ^ now
            while removed:
                bit = removed & -removed
                ranks[bit.bit_length()-1][q] = rounds
                removed ^= bit
        winning = new
    # Cells may cross guard-signature boundaries; no compactness claim is made.
    grouped = {}
    for vid, vector in enumerate(ranks):
        grouped.setdefault(tuple(vector), []).append(vid)
    cells = [{'valuation_ids': ids, 'ranks': list(vector)} for vector, ids in grouped.items()]
    q0 = case['implementation']['initial']*n + case['specification']['initial']
    safe_ids = [k for k,row in enumerate(ranks) if row[q0] == -1]
    bad = [(row[q0],tuple(values[k][p['name']] for p in case['parameters']),k)
           for k,row in enumerate(ranks) if row[q0] != -1]
    shortest = None if not bad else min(bad)[2]
    return {'case_id':case['id'], 'valuations':values, 'cells':cells,
            'safe_valuation_ids':safe_ids, 'shortest_bad_valuation_id':shortest,
            'rounds':rounds, 'equation_visits':equation_visits}
