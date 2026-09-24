"""Bounded, immutable-parameter interface syntax and its producer interpretation.

SPDX-License-Identifier: MIT
No expressions are evaluated as Python source. Integer arithmetic is unbounded.
"""
from itertools import product


def expression(node, valuation):
    if type(node) is int:
        return node
    if type(node) is str:
        return valuation[node]
    op, *args = node
    if op == '+':
        return sum(expression(x, valuation) for x in args)
    if op == '-':
        return expression(args[0], valuation) - expression(args[1], valuation)
    if op == '*':
        return expression(args[0], valuation) * expression(args[1], valuation)
    if op == '%':
        return expression(args[0], valuation) % expression(args[1], valuation)
    raise ValueError('unsupported integer operation')


def guard(node, valuation):
    if type(node) is bool:
        return node
    op, *args = node
    if op == 'and':
        return all(guard(x, valuation) for x in args)
    if op == 'or':
        return any(guard(x, valuation) for x in args)
    if op == 'not':
        return not guard(args[0], valuation)
    a, b = (expression(x, valuation) for x in args)
    if op == '<': return a < b
    if op == '<=': return a <= b
    if op == '==': return a == b
    raise ValueError('unsupported predicate')


def valuations(case):
    ps = case['parameters']
    return [dict(zip([p['name'] for p in ps], values))
            for values in product(*(range(p['lo'], p['hi']+1) for p in ps))
            if guard(case['assumption'], dict(zip([p['name'] for p in ps], values)))]


def masks(case, values):
    def encoded(automaton):
        outgoing = [[] for _ in range(automaton['states'])]
        for index, edge in enumerate(automaton['edges']):
            mask = sum(1 << k for k, p in enumerate(values) if guard(edge['guard'], p))
            outgoing[edge['from']].append((index, edge['kind'], edge['label'], edge['to'], mask))
        return outgoing
    return encoded(case['implementation']), encoded(case['specification'])
