"""Independent schema and dual-certificate checker, plus an AND/OR exact oracle.

SPDX-License-Identifier: MIT
No imports from the bitset solver or its arithmetic/guard interpretation.
Trust boundary: Python, this source, and the exact supplied input JSON.
"""
import heapq
import itertools


class Invalid(ValueError):
    pass


def need(condition, reason):
    if not condition:
        raise Invalid(reason)


def integer(term, env):
    if isinstance(term, bool):
        raise Invalid('Boolean used as integer')
    if isinstance(term, int): return term
    if isinstance(term, str): return env[term]
    op, *xs = term
    if op == '+':
        total = 0
        for t in xs: total += integer(t,env)
        return total
    a,b = integer(xs[0],env), integer(xs[1],env)
    if op == '-': return a-b
    if op == '*': return a*b
    if op == '%':
        need(b>0, 'nonpositive modulus')
        return a % b
    raise Invalid('unknown integer operator')


def predicate(term, env):
    if term is True: return True
    if term is False: return False
    op,*xs = term
    if op == 'not': return not predicate(xs[0],env)
    if op == 'and':
        for x in xs:
            if not predicate(x,env): return False
        return True
    if op == 'or':
        for x in xs:
            if predicate(x,env): return True
        return False
    left,right = integer(xs[0],env),integer(xs[1],env)
    if op == '==': return left==right
    if op == '<': return left<right
    if op == '<=': return left<=right
    raise Invalid('unknown predicate operator')


def validate_expression(x, names):
    if type(x) is int: return
    if type(x) is str:
        need(x in names,'unknown parameter'); return
    need(type(x) is list and len(x)>=2,'malformed expression')
    op,*args=x
    need(op in ('+','-','*','%'),'non-Presburger expression')
    if op=='+': need(len(args)>=1,'empty sum')
    else: need(len(args)==2,'binary arity')
    if op=='*': need(type(args[0]) is int or type(args[1]) is int,'variable product')
    if op=='%': need(type(args[1]) is int and args[1]>0,'nonconstant positive modulus required')
    for y in args: validate_expression(y,names)


def validate_predicate(x,names):
    if type(x) is bool:return
    need(type(x) is list and len(x)>=2,'malformed predicate')
    op,*args=x
    if op in ('and','or'):
        need(len(args)>=1,'empty connective')
        for a in args:validate_predicate(a,names)
    elif op=='not':
        need(len(args)==1,'negation arity');validate_predicate(args[0],names)
    else:
        need(op in ('==','<','<=') and len(args)==2,'comparison arity')
        for a in args:validate_expression(a,names)


def validate_case(c):
    need(type(c) is dict,'case must be object')
    need(type(c['id']) is str and bool(c['id']),'case identifier')
    ps=c['parameters'];need(1<=len(ps)<=3,'parameter dimension')
    names=[x['name'] for x in ps];need(len(set(names))==len(names),'duplicate parameter')
    for p in ps:
        need(type(p['name']) is str,'parameter name type')
        need(type(p['lo']) is int and type(p['hi']) is int and 0<=p['lo']<=p['hi']<=7,'parameter bound')
    validate_predicate(c['assumption'],names)
    for label,p in c['environment_inputs'].items():
        need(type(label) is str,'environment label');validate_predicate(p,names)
    polarities={}
    for key in ('implementation','specification'):
        a=c[key]
        need(type(a['states']) is int and 1<=a['states']<=48,'state count')
        need(type(a['initial']) is int and 0<=a['initial']<a['states'],'initial state')
        need(type(a['edges']) is list,'edge list')
        for e in a['edges']:
            need(type(e['from']) is int and type(e['to']) is int and 0<=e['from']<a['states'] and 0<=e['to']<a['states'],'edge endpoint')
            need(e['kind'] in ('in','out'),'edge polarity')
            need(type(e['label']) is str and bool(e['label']),'edge label')
            if e['label'] in polarities:need(polarities[e['label']]==e['kind'],'polarity collision')
            polarities[e['label']]=e['kind'];validate_predicate(e['guard'],names)
    need(len(polarities)<=64,'action-label bound')
    need(set(c['environment_inputs'])<=set(k for k,v in polarities.items() if v=='in'),'unknown environment input')
    raw=itertools.product(*(range(p['lo'],p['hi']+1) for p in ps))
    values=[]
    for xs in raw:
        env=dict(zip(names,xs))
        if predicate(c['assumption'],env):values.append(env)
    # Input determinism is checked on the entire requested family, not a sample.
    for env in values:
        for key in ('implementation','specification'):
            seen={}
            for e in c[key]['edges']:
                if e['kind']=='in' and predicate(e['guard'],env):
                    k=e['from'],e['label']
                    need(k not in seen or seen[k]==e['to'],'input nondeterminism')
                    seen[k]=e['to']
    return values


def arena(c,env):
    I,S=c['implementation'],c['specification'];n=S['states']
    iedges=[[] for _ in range(I['states'])];sedges=[[] for _ in range(n)]
    for a,out in ((I,iedges),(S,sedges)):
        for k,e in enumerate(a['edges']):
            if predicate(e['guard'],env):out[e['from']].append((k,e))
    # Only this consumer's independently evaluated enabled edges are indexed.
    indexed=[]
    for outgoing in (iedges,sedges):
        side=[]
        for rows in outgoing:
            groups=None
            if all(type(e['kind']) is str and type(e['label']) is str for _,e in rows):
                groups={}
                for entry in rows:
                    e=entry[1]; groups.setdefault((e['kind'],e['label']),[]).append(entry)
            side.append(groups)
        indexed.append(side)
    imatches,smatches=indexed
    challenges=[[] for _ in range(I['states']*n)]
    for i in range(I['states']):
        for s in range(n):
            cs=challenges[i*n+s]
            for k,e in sedges[s]:
                if e['kind']!='in' or not predicate(c['environment_inputs'].get(e['label'],True),env):continue
                bucket=iedges[i] if imatches[i] is None or type(e['label']) is not str else imatches[i].get(('in',e['label']),())
                successors=sorted({r['to']*n+e['to'] for _,r in bucket
                                   if r['kind']=='in' and r['label']==e['label']})
                cs.append({'kind':'in','edge':k,'label':e['label'],'replies':successors})
            for k,e in iedges[i]:
                if e['kind']!='out':continue
                bucket=sedges[s] if smatches[s] is None or type(e['label']) is not str else smatches[s].get(('out',e['label']),())
                successors=sorted({e['to']*n+r['to'] for _,r in bucket
                                   if r['kind']=='out' and r['label']==e['label']})
                cs.append({'kind':'out','edge':k,'label':e['label'],'replies':successors})
    return challenges


def exact_oracle(challenges):
    """Reverse AND/OR attractor. Never iterates a candidate simulation relation."""
    N=len(challenges);parents=[[] for _ in range(N)]
    pending={};largest={};queue=[]
    for q,cs in enumerate(challenges):
        for ci,ch in enumerate(cs):
            key=q,ci;pending[key]=len(ch['replies']);largest[key]=0
            for r in ch['replies']:parents[r].append(key)
            if not ch['replies']:heapq.heappush(queue,(1,q))
    ranks=[-1]*N
    while queue:
        depth,q=heapq.heappop(queue)
        if ranks[q]!=-1:continue
        ranks[q]=depth
        for key in parents[q]:
            pending[key]-=1;largest[key]=max(largest[key],depth)
            if pending[key]==0:heapq.heappush(queue,(largest[key]+1,key[0]))
    return ranks


def bellman(ch,rank):
    finite=[]
    for move in ch:
        rs=[rank[t] for t in move['replies']]
        if -1 not in rs:finite.append(1+max(rs,default=0))
    return min(finite) if finite else -1


def certificate_ranks(c,certificate,values):
    need(certificate['case_id']==c['id'],'case binding')
    table=certificate['valuations']
    need(type(table) is list and all(type(p) is dict and
         all(type(v) is int for v in p.values()) for p in table),'valuation integer types')
    need(table==values,'valuation table binding/order')
    rows=[None]*len(values);N=c['implementation']['states']*c['specification']['states']
    for cell in certificate['cells']:
        ids=cell['valuation_ids'];rank=cell['ranks']
        need(type(ids) is list and bool(ids),'empty/malformed cell')
        need(type(rank) is list and len(rank)==N,'rank vector dimension')
        need(all(type(r) is int and (r==-1 or 1<=r<=N) for r in rank),'rank domain')
        for k in ids:
            need(type(k) is int and 0<=k<len(values),'valuation index domain')
            need(rows[k] is None,'partition overlap');rows[k]=rank
    need(all(row is not None for row in rows),'partition coverage')
    return rows


def check_certificate(c,certificate,oracle=True):
    values=validate_case(c);rows=certificate_ranks(c,certificate,values)
    N=c['implementation']['states']*c['specification']['states']
    for k,p in enumerate(values):
        game=arena(c,p)
        for q,cs in enumerate(game):
            need(bellman(cs,rows[k])==rows[k][q],'signed rank equation')
        if oracle:need(exact_oracle(game)==rows[k],'reverse oracle mismatch')
    q0=c['implementation']['initial']*c['specification']['states']+c['specification']['initial']
    safe=[k for k,row in enumerate(rows) if row[q0]==-1]
    safe_ids=certificate['safe_valuation_ids']
    need(type(safe_ids) is list and all(type(k) is int for k in safe_ids),'safe index types')
    need(safe_ids==safe,'safe region/maximality')
    bad=[(row[q0],tuple(p[x['name']] for x in c['parameters']),k)
         for k,(p,row) in enumerate(zip(values,rows)) if row[q0]!=-1]
    chosen=certificate['shortest_bad_valuation_id']
    need(chosen is None or type(chosen) is int,'chosen valuation index type')
    need(chosen==(min(bad)[2] if bad else None),'global minimality/order')
    rounds=max((r for row in rows for r in row if r!=-1),default=0)
    need(type(certificate['rounds']) is int and certificate['rounds']==rounds,'round count')
    need(type(certificate['equation_visits']) is int and
         certificate['equation_visits']==N*(rounds+1),'fixed-point visit count')
    return {'valuations':len(values),'state_pair_valuations':N*len(values),
            'safe':len(safe),'bad':len(values)-len(safe),'cells':len(certificate['cells'])}


def make_witness(c,cert):
    values=validate_case(c);rows=certificate_ranks(c,cert,values)
    k=cert['shortest_bad_valuation_id']
    if k is None:return None
    row=rows[k];game=arena(c,values[k]);q0=c['implementation']['initial']*c['specification']['states']+c['specification']['initial']
    nodes={};stack=[q0]
    while stack:
        q=stack.pop()
        if str(q) in nodes:continue
        options=[]
        for ch in game[q]:
            rs=[row[r] for r in ch['replies']]
            if -1 not in rs and 1+max(rs,default=0)==row[q]:options.append(ch)
        need(bool(options),'no optimal spoiler')
        ch=min(options,key=lambda x:(x['kind'],x['label'],x['edge']))
        nodes[str(q)]={'rank':row[q], **ch}
        stack.extend(ch['replies'])
    return {'valuation_id':k,'valuation':values[k],'root':q0,'depth':row[q0],'nodes':nodes}


def check_witness(c,cert,w):
    if cert['shortest_bad_valuation_id'] is None:
        need(w is None,'unexpected witness');return 0
    need(w is not None,'missing witness')
    values=validate_case(c);rows=certificate_ranks(c,cert,values);k=cert['shortest_bad_valuation_id']
    need(type(w['valuation']) is dict and all(type(v) is int for v in w['valuation'].values()),
         'witness valuation integer types')
    need(type(w['valuation_id']) is int and w['valuation_id']==k and w['valuation']==values[k],'witness valuation')
    q0=c['implementation']['initial']*c['specification']['states']+c['specification']['initial']
    need(type(w['root']) is int and w['root']==q0,'witness root')
    need(type(w['depth']) is int and w['depth']==rows[k][q0],'witness optimal depth')
    game=arena(c,values[k]);visited=set();todo=[q0]
    while todo:
        q=todo.pop()
        if q in visited:continue
        visited.add(q);node=w['nodes'].get(str(q));need(node is not None,'missing spoiler node')
        ch={key:node[key] for key in ('kind','edge','label','replies')}
        need(type(ch['edge']) is int and type(ch['replies']) is list and
             all(type(r) is int for r in ch['replies']),'witness edge/reply types')
        need(ch in game[q],'invalid move or omitted universal reply')
        need(type(node['rank']) is int and node['rank']==rows[k][q],'node rank')
        rs=[rows[k][r] for r in ch['replies']]
        need(-1 not in rs and 1+max(rs,default=0)==node['rank'],'rank/shortest descent')
        todo.extend(ch['replies'])
    need(set(w['nodes'])=={str(x) for x in visited},'extraneous witness nodes')
    return len(visited)
