"""Explicit owned finite regression, separate from the frozen 108-test inventory.

SPDX-License-Identifier: MIT
No historical code, private paths, clocks, compiler or external targets.
"""
import copy
import itertools
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from solve import solve
from check import Invalid,validate_case,arena,check_certificate,make_witness,check_witness


def literal_integer(x,p):
    if type(x) is int: return x
    if type(x) is str: return p[x]
    op,*xs=x; v=[literal_integer(y,p) for y in xs]
    if op=='+': return sum(v)
    if op=='-': return v[0]-v[1]
    if op=='*': return v[0]*v[1]
    if op=='%': return v[0]%v[1]
    raise ValueError(op)


def literal_guard(x,p):
    if type(x) is bool: return x
    op,*xs=x
    if op=='and': return all(literal_guard(y,p) for y in xs)
    if op=='or': return any(literal_guard(y,p) for y in xs)
    if op=='not': return not literal_guard(xs[0],p)
    a,b=[literal_integer(y,p) for y in xs]
    return {'==':a==b,'<':a<b,'<=':a<=b}[op]


def edge(start,target,label,kind='out',guard=True):
    return {'from':start,'to':target,'label':label,'kind':kind,'guard':guard}


def tiny_cases():
    descriptions=[[],[edge(0,0,'a')],[edge(0,1,'a')],[edge(1,1,'b')],
        [edge(0,0,'a',guard=False),edge(0,1,'a')],
        [edge(0,0,'a'),edge(0,1,'a')],
        [edge(0,1,'a'),edge(0,1,'a')],
        [edge(0,1,'a',guard=['==',['%','p',2],0]),edge(1,1,'b')],
        [edge(0,1,'a',guard=['not',['==','p',1]]),edge(1,0,'b')],
        [edge(0,1,'tick','in')],[edge(0,1,'tick','in'),edge(0,1,'tick','in')],
        [edge(0,1,'tick','in',guard=['<','p',2]),edge(1,0,'tick','in'),edge(1,1,'a')]]
    for index,(I,S) in enumerate(itertools.product(descriptions,repeat=2)):
        for environment in ({},{'tick':['==',['%','p',2],0]}):
            if environment and not any(e['label']=='tick' for e in I+S): continue
            yield dict(id='owned-'+str(index),parameters=[dict(name='p',lo=0,hi=3)],
                assumption=True,environment_inputs=copy.deepcopy(environment),
                implementation=dict(states=2,initial=0,edges=copy.deepcopy(I)),
                specification=dict(states=2,initial=0,edges=copy.deepcopy(S)))
    for dimension in (1,2,3):
        ps=[dict(name=name,lo=0,hi=2) for name in ('p','q','r')[:dimension]]
        guarded=['and',['<=',['+',ps[0]['name'],1],3],['==',['%',['*',2,ps[-1]['name']],2],0]]
        yield dict(id='dimension-'+str(dimension),parameters=ps,assumption=guarded,
            environment_inputs={},implementation=dict(states=2,initial=0,
                edges=[edge(0,1,'α|a'),edge(1,1,'a|α',guard=['<',['-',ps[0]['name'],1],1])]),
            specification=dict(states=2,initial=0,
                edges=[edge(0,1,'a|α',guard=False),edge(0,1,'α|a'),edge(0,1,'α|a'),edge(1,1,'a|α')]))
    yield dict(id='empty',parameters=[dict(name='p',lo=0,hi=0)],assumption=False,
        environment_inputs={},implementation=dict(states=1,initial=0,edges=[]),
        specification=dict(states=1,initial=0,edges=[]))


def literal_arena(c,p):
    """Raw edge scans with separately interpreted predicates, no masks/index."""
    I,S=c['implementation'],c['specification']; n=S['states']; game=[]
    for i,s in itertools.product(range(I['states']),range(n)):
        moves=[]
        for kind,challenger,reply,at,other in [('in',S,I,s,i),('out',I,S,i,s)]:
            for position,e in enumerate(challenger['edges']):
                if e['from']!=at or e['kind']!=kind or not literal_guard(e['guard'],p): continue
                if kind=='in' and not literal_guard(c['environment_inputs'].get(e['label'],True),p): continue
                targets=[]
                for r in reply['edges']:
                    if r['from']==other and r['kind']==kind and r['label']==e['label'] and literal_guard(r['guard'],p):
                        targets.append(r['to']*n+e['to'] if kind=='in' else e['to']*n+r['to'])
                moves.append(dict(kind=kind,edge=position,label=e['label'],replies=sorted(set(targets))))
        game.append(moves)
    return game


def literal_ranks(game):
    """Enumerate spoiler trees and every postfixed relation on N<=4 pairs."""
    N=len(game)
    def bad(q,height):
        return height>0 and any(all(bad(r,height-1) for r in ch['replies']) for ch in game[q])
    ranks=[next((h for h in range(1,N+1) if bad(q,h)),-1) for q in range(N)]
    winning=set()
    for mask in range(1<<N):
        relation={q for q in range(N) if mask//(2**q)%2}
        if all(all(any(r in relation for r in ch['replies']) for ch in game[q]) for q in relation):
            winning.update(relation)
    if winning!={q for q,r in enumerate(ranks) if r==-1}: raise AssertionError('literal witnesses disagree')
    return ranks


def literal_certificate(c):
    ps=c['parameters']; values=[]
    for xs in itertools.product(*(range(p['lo'],p['hi']+1) for p in ps)):
        p=dict(zip([a['name'] for a in ps],xs))
        if literal_guard(c['assumption'],p): values.append(p)
    rows=[literal_ranks(literal_arena(c,p)) for p in values]
    groups={}
    for i,row in enumerate(rows): groups.setdefault(tuple(row),[]).append(i)
    n=c['specification']['states']; initial=c['implementation']['initial']*n+c['specification']['initial']
    bad=[(row[initial],tuple(p[a['name']] for a in ps),i) for i,(p,row) in enumerate(zip(values,rows)) if row[initial]!=-1]
    rounds=max((r for row in rows for r in row if r!=-1),default=0)
    return dict(case_id=c['id'],valuations=values,
        cells=[dict(valuation_ids=ids,ranks=list(row)) for row,ids in groups.items()],
        safe_valuation_ids=[i for i,row in enumerate(rows) if row[initial]==-1],
        shortest_bad_valuation_id=min(bad)[2] if bad else None,rounds=rounds,
        equation_visits=c['implementation']['states']*n*(rounds+1))


def mutations(c,p,w):
    certs=[]; witnesses=[]
    for key,value in [('case_id','wrong'),('rounds',True),('equation_visits',0),
                      ('safe_valuation_ids',[False]),('shortest_bad_valuation_id',False)]:
        q=copy.deepcopy(p); q[key]=value; certs.append(q)
    if p['cells']:
        q=copy.deepcopy(p); q['cells'].pop(); certs.append(q)
        q=copy.deepcopy(p); q['cells'].append(copy.deepcopy(q['cells'][0])); certs.append(q)
    if w is not None:
        for key,value in [('depth',True),('root',True),('valuation_id',True)]:
            q=copy.deepcopy(w); q[key]=value; witnesses.append(q)
        for key,value in [('edge',True),('replies',[]),('label','missing')]:
            q=copy.deepcopy(w); q['nodes'][str(w['root'])][key]=value; witnesses.append(q)
    return certs,witnesses


class ReplyRegression(unittest.TestCase):
    def test_tiny_full_packets_ranks_and_arenas(self):
        for c in tiny_cases():
            values=validate_case(c); expected=literal_certificate(c)
            self.assertEqual(solve(c),expected); check_certificate(c,expected)
            for p in values: self.assertEqual(arena(c,p),literal_arena(c,p))
            w=make_witness(c,expected); check_witness(c,expected,w)

    def test_branching_and_omitted_universal_reply(self):
        c=dict(id='branch',parameters=[dict(name='p',lo=0,hi=0)],assumption=True,environment_inputs={},
            implementation=dict(states=3,initial=0,edges=[edge(0,1,'a'),edge(1,2,'b'),edge(1,2,'c')]),
            specification=dict(states=4,initial=0,edges=[edge(0,1,'a'),edge(0,2,'a'),edge(1,3,'b'),edge(2,3,'c')]))
        p=solve(c); w=make_witness(c,p); self.assertEqual(w['depth'],2)
        self.assertEqual(len(w['nodes'][str(w['root'])]['replies']),2)
        w['nodes'][str(w['root'])]['replies'].pop()
        with self.assertRaises(Invalid): check_witness(c,p,w)

    def test_admission_and_nonstandard_string_fallback(self):
        c=next(tiny_cases())
        for bad in (True,-1,49):
            q=copy.deepcopy(c); q['implementation']['states']=bad
            with self.assertRaises(Invalid): check_certificate(q,{})
        class Polarity(str):
            __hash__=None
        c=list(tiny_cases())[2]; c['specification']['edges'][0]['kind']=Polarity('out')
        expected=literal_certificate(c)
        self.assertEqual(solve(c),expected); check_certificate(c,expected)

    def test_fresh_after_mutation_between_calls(self):
        c=list(tiny_cases())[2]; p=solve(c); check_certificate(c,p)
        c['specification']['edges'][0]['label']='different'
        current=solve(c); self.assertEqual(current,literal_certificate(c)); check_certificate(c,current)
        c['specification']['edges'][0]['label']='a'
        self.assertEqual(solve(c),p)


if __name__=='__main__': unittest.main()
