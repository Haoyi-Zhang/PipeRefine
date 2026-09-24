"""Generate original, deterministic finite fixtures. SPDX-License-Identifier: MIT.

The three timing motifs are mathematical models, NOT exported Lilac/RTL designs.
All random seeds and generation rules are fixed before the campaign.
"""
import copy
import json
import random
from pathlib import Path


def edge(src,dst,label,kind='out',guard=True):
    return {'from':src,'to':dst,'label':label,'kind':kind,'guard':guard}


def auto(n,edges,initial=0):
    return {'states':n,'initial':initial,'edges':edges}


def par(name='p',lo=0,hi=3):
    return {'name':name,'lo':lo,'hi':hi}


def case(name,I,S,parameters=None,group='semantic-control',assumption=True,environment=None):
    return {'id':name,'group':group,'parameters':parameters or [par()],
            'assumption':assumption,'environment_inputs':environment or {},
            'implementation':I,'specification':S}


def all_cases():
    cases=[]
    # Branching failure with exactly equal finite port languages.
    I=auto(3,[edge(0,1,'a'),edge(1,2,'b'),edge(1,2,'c')])
    S=auto(4,[edge(0,1,'a'),edge(0,2,'a'),edge(1,3,'b'),edge(2,3,'c')])
    cases.append(case('branching',I,S,[par(hi=0)]))
    cases.append(case('reflexive',copy.deepcopy(S),copy.deepcopy(S)))
    # Parameter-dependent matching is legal; one uniform matching edge is not required.
    cases.append(case('pointwise-choice',auto(2,[edge(0,1,'a')]),
                      auto(3,[edge(0,1,'a',guard=['==','p',0]),edge(0,2,'a',guard=['<',0,'p'])])))
    cases.append(case('interior-hole',auto(1,[edge(0,0,'a')]),
                      auto(1,[edge(0,0,'a',guard=['not',['==','p',3]])]),[par(hi=7)]))
    cases.append(case('parity',auto(1,[edge(0,0,'a')]),
                      auto(1,[edge(0,0,'a',guard=['==',['%','p',2],0])]),[par(hi=7)]))
    cases.append(case('correlated',auto(1,[edge(0,0,'a')]),
                      auto(1,[edge(0,0,'a',guard=['==','x','y'])]),[par('x'),par('y')]))
    cases.append(case('input-variance',auto(1,[edge(0,0,'launch','in',['==',['%','p',2],0])]),
                      auto(1,[edge(0,0,'launch','in')]),[par(hi=7)]))
    cases.append(case('input-assumption',auto(1,[]),auto(1,[edge(0,0,'launch','in')]),
                      environment={'launch':['==','p',0]}))
    cases.append(case('empty-domain',auto(1,[]),auto(1,[]),assumption=False))
    cases.append(case('quiescence-not-progress',auto(1,[]),auto(1,[edge(0,0,'response')])))
    # Shortest order is (worst-case challenge count, valuation), NOT valuation first.
    I=auto(4,[edge(0,1,'a'),edge(1,2,'b'),edge(2,3,'c'),edge(3,3,'d')])
    S=auto(4,[edge(0,1,'a',guard=['==','p',0]),edge(1,2,'b'),edge(2,3,'c')])
    cases.append(case('shortest-order',I,S,[par(hi=1)]))
    # Equal rank vectors can cross guards, but this is only certificate storage sharing.
    I=auto(2,[edge(0,1,'a',guard=['==','p',0]),edge(0,1,'a',guard=['<',0,'p'])])
    S=auto(2,[edge(0,1,'a')])
    cases.append(case('guard-splitting',I,S))
    # Latency window: fixed initiation at time zero; sample permission encodes validity.
    def window(length,name):
        n=7
        es=[edge(t,min(t+1,n-1),'tick','in') for t in range(n)]
        es += [edge(t,t,'sample','in',['and',['<=',name,t],['<',t,['+',name,length]]])
               for t in range(n)]
        return auto(n,es)
    cases.append(case('availability-window',window(3,'new'),window(2,'old'),
                      [par('new',0,3),par('old',0,3)],group='timing-motif'))
    # Cooldown: every admissible launch resets the timer; all finite input schedules.
    def cooldown(name):
        n=5
        es=[edge(t,min(t+1,n-1),'tick','in') for t in range(n)]
        es += [edge(t,0,'launch','in',['<=',name,t]) for t in range(n)]
        return auto(n,es)
    cases.append(case('initiation-gap',cooldown('new'),cooldown('old'),
                      [par('new',1,4),par('old',1,4)],group='timing-motif'))
    # Two outputs sharing a declared input family: correlated phase guard, not hardware RTL.
    I=auto(2,[edge(0,1,'sample','in'),edge(1,0,'value')])
    S=auto(2,[edge(0,1,'sample','in'),edge(1,0,'value',guard=['==',['%',['+','latency','phase'],2],0])])
    cases.append(case('phase-alignment',I,S,[par('latency'),par('phase'),par('mode',0,1)],group='timing-motif'))
    # Pilot is a 16-step loss, with safe and unsafe valuations and all 256 pairs checked.
    def chain(n,conditional):
        es=[edge(t,t+1,'step') for t in range(n-1)]
        es.append(edge(n-1,n-1,'finish',guard=['==',['%','p',2],0] if conditional else True))
        return auto(n,es)
    cases.append(case('long-chain',chain(16,False),chain(16,True),[par(hi=7)],group='scaling-control'))
    # Largest stated control size. No assertion that 48 states model a complete circuit.
    def broad(n):
        es=[]
        for s in range(n):
            es.extend([edge(s,(s+1)%n,'tick','in'),edge(s,s,'value')])
        return auto(n,es)
    cases.append(case('wide-control',broad(48),broad(48),[par(hi=0)],group='scaling-control'))
    # Statically fixed generated families. No tuning against their outcomes.
    for seed in range(20260911,20260935):
        rng=random.Random(seed)
        def random_auto():
            n=rng.randrange(2,5);es=[]
            guards=[True,False,['<=','p',1],['<',1,'p'],['==','p','q'],
                    ['==',['%','q',2],0],['not',['==','p',2]]]
            for s in range(n):
                for label in ('request','tick'):
                    if rng.random()<0.65:
                        es.append(edge(s,rng.randrange(n),label,'in',copy.deepcopy(rng.choice(guards))))
                for label in ('value','error'):
                    for _ in range(rng.randrange(3)):
                        es.append(edge(s,rng.randrange(n),label,'out',copy.deepcopy(rng.choice(guards))))
            return auto(n,es)
        I,S=random_auto(),random_auto()
        if seed%6==0:S=copy.deepcopy(I)
        c=case('generated-'+str(seed-20260910).zfill(2),I,S,[par('p'),par('q')],group='generated')
        c['generation_seed']=seed
        cases.append(c)
    return cases


def write_inputs(directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    for c in all_cases():
        (directory/(c['id']+'.json')).write_text(json.dumps(c,indent=2,sort_keys=True)+'\n')


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path)
    args=p.parse_args();write_inputs(args.directory)
