# Exact bounded interface simulation and ranked failure

## 1. Declared model

Fix a finite parameter domain D contained in the product of one to three integer
intervals [lo_j,hi_j], each inside [0,7], restricted by a Boolean Presburger
assumption. Parameters are immutable and visible at instantiation. Two finite
components I and S have fixed control-state sets Q_I and Q_S, initial states,
and guarded transitions with globally consistent input/output label polarity.
For a fixed p in D, evaluating guards gives concrete automata. Each input label
has at most one successor at each state (duplicate edges to that same successor
are harmless). Output successors can be nondeterministic. There are no hidden
actions, implicit quiescence outputs, fairness, or progress requirements.

An environment annotation E_p is a fixed set of allowed input labels for that
valuation. Labels omitted from the annotation are allowed. It cannot suppress
outputs. History-dependent environment state is outside this implementation.

Write Q = Q_I x Q_S, N = |Q|, and q0 for the initial pair. At q=(i,s), challenges
C_p(q) are (a) each enabled S input edge whose label is in E_p and (b) each
enabled I output edge. A challenge identifies an edge, not only a label. Its
response set T_p(q,c) consists of product successors obtained with an enabled
edge of the same label and polarity in the other component. Thus input matching
is contravariant and output matching covariant. Input determinism removes any
ambiguity about adversarial versus existential input-successor selection.

A relation R is an alternating simulation for this model when q in R implies
that every challenge at q has at least one response in R. Write I_p <= S_p when
some such R contains q0. This is a definition of the finite interface relation,
not a theorem that this definition captures all legal Lilac hardware contexts.

## 2. Greatest fixed point (standard finite-game result)

Define F_p(R) = {q : for all c in C_p(q), T_p(q,c) intersects R}.
Let R_p^0=Q and R_p^(k+1)=F_p(R_p^k).

**Lemma 1.** F_p is monotone, the sequence descends, and it stabilizes after at
most N strict descents. Its limit R_p^* is the greatest post-fixed relation.

*Proof.* If R is contained in R', a response in R is also in R', so
F_p(R) is contained in F_p(R'). The first iterate is contained in Q; monotonicity
then proves every subsequent inclusion. A strict descent removes at least one
of N pairs. At stabilization R_p^*=F_p(R_p^*). If H is any post-fixed relation,
H subseteq F_p(H), induction gives H subseteq R_p^k: the base is H subseteq Q;
the step follows H subseteq F_p(H) subseteq F_p(R_p^k). Hence H subseteq R_p^*.
The limit itself is a post-fixed relation. QED.

**Theorem 1.** I_p <= S_p iff q0 belongs to R_p^*. The bitset producer computes
this relation exactly for every p in D, with at most N strict synchronous rounds
for one family.

*Proof.* The equivalence follows from Lemma 1 and the definition. Assign one bit
to each admissible valuation. At each state pair, the implementation intersects,
for each challenge, the implication from the challenge's enabling mask to the
union of (reply enabling mask intersect previous target mask). Inspecting one
bit recovers exactly F_p. Projection therefore commutes with each iteration,
by induction from the all-valuation mask. Each concrete instance stabilizes by
round N. An instance cannot change again after its first stable round, so their
synchronous product also stabilizes by N. The final unchanged pass is counted
separately. There is no iteration over paths and no finite path-length cutoff.
QED.

## 3. Weakest sufficient bounded assumption

Let W={p in D : q0 in R_p^*}. An admissible assumption is any set A subseteq D.
Order assumptions by set inclusion; a weaker predicate admits more valuations.

**Theorem 2.** All instances admitted by A refine iff A subseteq W. W is the
greatest safe set, and its characteristic predicate is a weakest sufficient
assumption relative to D. W is semilinear.

*Proof.* The equivalence follows pointwise from Theorem 1. It proves safety of W
and containment of every safe A in W. W is finite. Each singleton {v} is a linear
set with base v and no period vectors, so their finite union is semilinear.
Equivalently, the disjunction over v in W of all equalities p_j=v_j is a Presburger
formula. If W is empty this is false, and no nonempty safe A exists. If D is empty,
universal refinement is vacuous and W remains empty. QED.

This existence proof is elementary and makes no compactness or novelty claim.
The serializer retains exact valuation membership rather than claiming minimal
Presburger syntax, convexity, monotonicity, or quantifier-elimination efficiency.
Finite parameter bounds do not bound state spaces in a richer timed model; fixed
finite control is a separate premise here.

## 4. Losing ranks and minimax depth

Let rho_p(q) be the first positive k for which q is absent from R_p^k, or infinity
if q is in R_p^*. Infinity is serialized as the integer -1. Then finite ranks lie
between 1 and N. For a challenge c define

    cost_r(c) = 1 + max { r(t) : t in T_p(q,c) },

where max(empty)=0 and 1+infinity=infinity. Define min(empty)=infinity. The
rank equations are rho_p(q)=min_{c in C_p(q)} cost_rho(c).

**Lemma 2.** These rank equations hold.

*Proof.* A pair is removed at step k exactly when some challenge has no response
remaining after step k-1. For that challenge, all responses have finite ranks
at most k-1; its earliest elimination time is one plus their largest rank, with
an immediately unmatched challenge costing one. Taking the earliest such
challenge yields the equation. If every challenge has an infinite-rank response,
no finite removal occurs. An empty challenge set is safe. QED.

**Theorem 3.** A finite rank r is the least worst-case number of challenges
needed for a spoiler to force an unmatched challenge. A spoiler DAG with at most
N pair nodes realizes that bound, and includes every possible response to the
chosen challenge. A shortest failure over D minimizes (rank at q0, lexicographic
parameter tuple), not parameter tuple first.

*Proof, upper bound.* At rank r choose a challenge attaining the minimum in
Lemma 2. All replies have ranks at most r-1. For r=1 there is no reply. Otherwise
repeat at the returned pair. Strict rank descent proves failure within r
challenges. The strategy depends only on the current pair and fixed valuation.
Merging repeated pair nodes yields an acyclic graph with at most N nodes.

*Lower bound.* At a rank r>1 pair, every challenge has at least one reply of rank
at least r-1; otherwise its cost would be less than r. The matching player can
choose such a reply. Induction prevents guaranteed failure before r challenges.
For infinity, each challenge has an infinite-rank reply; choosing it avoids all
finite failure. At rank one, failure takes one challenge, not zero. Thus the
upper bound is optimal. Enumerating all finite initial ranks and taking the
specified ordered minimum proves global selection, including ties. QED.

This is worst-case game depth, not the number of physical clock cycles, minimum
number of DAG nodes, or a shortest distinguishing word. The spoiler observes
both component states in the proof game. It need not be implementable by an
external hardware tester that only sees ports.

## 5. A complete local certificate check

A certificate contains the exact lexicographic table of admissible valuations,
a disjoint total partition of table indices, a full rank vector per cell, the
initial safe indices, and the selected failing index. Cells may cross guard
truth-signature boundaries because only equal rank vectors are grouped.

**Theorem 4.** A total labeling r_p:Q -> {1,...,N,infinity} satisfying every local
rank equation is the true losing-rank labeling. Therefore exact partition
coverage plus those equations certifies the complete safe region and rank-based
minimality, without trusting the producer or running its fixed-point loop.

*Proof.* Define H_p^k={q:r_p(q)>k}, with infinity greater than every integer.
H_p^0=Q. The rank equation implies r_p(q)>k iff every challenge has a reply
with rank greater than k-1, including the empty-set conventions. Consequently
H_p^k=F_p(H_p^(k-1)) for k>=1. By induction H_p^k=R_p^k. All finite labels are
at most N, so H_p^N is precisely the infinity-labeled region. Lemma 1 makes it
the greatest simulation. Each finite label is the exact first removal step.
Partition coverage repeats this argument for every requested valuation, neither
omitting a difficult valuation nor counting one twice. The initial state then
determines W, and Theorem 3 determines the ordered minimum. QED.

A DAG alone certifies only an upper bound: lower bounds require checking all
challenges, not only a selected move. The implementation checks all local equations
and checks the selected DAG's action identity, all replies, rank descent, and
reachable-node coverage. It rejects Boolean/integer type confusion in parameter
values, indices, ranks, counters, and witness edge identifiers. Counters are tied
to N times (largest finite rank plus one), including the stable final pass.

The checker is an executable implementation of this argument, not a proof-assistant
verification of its Python source. A separate scalar oracle uses a reverse AND/OR
attractor: unmatched challenges seed rank one; a challenge becomes losing after
all response nodes have been settled, at one plus their largest settled rank;
a min-heap settles a pair at its first minimal offered rank. Induction in heap
order establishes the same recurrence. The bitset solver and this oracle have
separate guard interpreters, but are not independently authored scientific reviews.

## 6. Why a port word is insufficient

Use only output labels a,b,c. I has i0--a-->i1, then both b and c to a terminal
state. S has s0--a-->s_b and s0--a-->s_c; s_b has only b and s_c only c, each
to a terminal state. Both finite trace sets are exactly {epsilon,a,ab,ac}.
Nevertheless, after matching a to s_b the implementation's c cannot be matched,
and after matching a to s_c its b cannot be matched. Therefore no simulation
contains the initial pair. Its rank is two. A complete spoiler has two response
branches after a; neither ab nor ac distinguishes the languages. This is a small
regression instance of the standard simulation/trace separation, not a new theorem.
See Janssen, Vaandrager, and Tretmans, arXiv:1909.13604, Section 6, Example 8.

## 7. Closed-form timing motifs, not hardware extraction

**Window containment.** An age counter takes values 0,...,6, initially zero,
advancing on tick and saturating at six. A sample input does not change age.
S permits sampling in [old,old+2), I in [new,new+3), with old,new in 0,...,3.
Then refinement holds iff new <= old <= new+1. For sufficiency, relate equal
ages; tick preserves equality and interval containment matches each permitted
sample. For necessity, when containment fails choose an integer age in S's
window but not I's, reachable by that many ticks, then sample. All endpoints
lie below the saturation value, so saturation introduces no spurious sample.
This model specifies sample permission, not a data-value correctness theorem.

**Initiation gaps.** Both components have ages 0,...,4 with tick saturation and
launch resetting age to zero. A launch is permitted iff age>=gap, where both gaps
are in 1,...,4. Refinement holds iff new<=old. Equal-age pairs form a simulation
when this inequality holds. If new>old, exactly old ticks followed by launch are
legal for S but not I. Resets preserve equal ages, so the sufficiency proof covers
all finite sequences of launches, not only the first transaction.

**Phase guard.** A sample moves from idle to a response state. I can output value
there; S can do so iff (latency+phase) modulo 2 is zero. The two parameters lie
in 0,...,3; an unused mode lies in 0,...,1. Equal states give a simulation exactly
under the parity condition; otherwise sample followed by value fails. This is a
handwritten correlated guard, not evidence of any specific generator's behavior.

## 8. Limits of these arguments

These proofs establish a bounded component relation and finite game witness
semantics. They do not establish contextual completeness for Lilac, compiler or
RTL correctness, runtime-variable latency treatment, hidden-output-parameter
uniformity, or quiescence/progress. Existing featured-game work already supplies
family solving and optimal strategies. Adding integer bounds, bitsets, or a local
checker does not by itself establish a novel TCAD contribution. The 41-family
campaign checks this implementation, not those missing claims.
