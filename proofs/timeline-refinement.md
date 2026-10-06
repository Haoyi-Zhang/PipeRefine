# Complete refinement results for port-separated timeline contracts

This note records the mathematical claims implemented and checked by the
artifact. It is a readable proof companion, not a mechanized proof. The
executable campaign checks every retained bounded valuation and is evidence for
the implementation; it does not replace the quantified arguments below.

## 1. Profiles, port separation, and launch-indexed clients

After fixing one admitted compile-time valuation, a profile `P` consists of:

- a positive initiation gap `g_P`;
- for every input port `x`, a finite read-age set `R_P(x)`;
- for every output port `y`, a finite guarantee-age set `W_P(y)`.

For a nonempty finite set `A`, write `span(A) = max(A) - min(A)`; the empty and
singleton cases have span zero. A profile is **port-separated** when

```
span(R_P(x)) < g_P  for every input port x,
span(W_P(y)) < g_P  for every output port y.
```

Unlike the former quiescent restriction, an event age may exceed `g_P`. Thus a
fully pipelined component with gap one and one output event at age eight is in
the fragment.

A finite launch-indexed client `C=(L,D,M)` has a finite strictly increasing
set of actual launch times `L subseteq N`, input-drive tags `(t,x,a)`, and
output-sample tags `(t,y,a)`. Every tag must have an actual nonnegative owner
`t in L` and a nonnegative age `a`; its physical projection is port `x` or `y`
at absolute cycle `t+a`. It is legal for `P` exactly when:

1. consecutive launches are separated by at least `g_P` cycles;
2. for every actual launch `t`, input port `x`, and `a in R_P(x)`, the drive tag
   `(t,x,a)` is present;
3. every sample tag `(t,y,a)` has `a in W_P(y)`;
4. the projection is injective on **all** tags in `D union M`, so no two tagged
   events use the same physical port/cycle slot.

Extra tagged input drives are permitted, but they obey the same ownership and
global collision rule. For example, let `g=1`, `R(x)={0}`, and `L={0,1}`. The
two required drives `(0,x,0)` and `(1,x,0)` are collision free. Adding
`(0,x,1)` is illegal because it collides with `(1,x,0)` at physical cycle one;
adding `(0,x,2)` is collision free for this finite launch set. Tags therefore
matter even though data values are not modeled: a value at one physical cycle
for one transaction cannot silently serve another transaction.

**Lemma 1 (relevant-client normalization).** To decide `I <= S`, it suffices to
consider clients whose drives are exactly the tags required by `S` for their
actual launches and whose samples are a finite subset of `S` guarantees.

**Proof.** From any `S`-legal client, delete each drive not required by `S` for
its owning launch. Deletion preserves actual launch ownership and cannot create
a physical collision. All `S`-required drives and all samples remain, so the
normalized client is still `S`-legal. If the original client is `I`-illegal,
its gap or sample violation is unchanged; a missing implementation-required
drive cannot be supplied by deleting other drives. Its all-tag projection was
already injective. Thus every counterexample normalizes to a counterexample.
Conversely, every normalized client is already in the original domain. The
restricted and original quantifiers therefore give the same decision. QED.

Implementation `I` **contextually refines** specification `S`, written `I <= S`,
when every finite launch-indexed client legal for `S` is legal for `I`.

## 2. Exact physicalizability of a port-age set

**Theorem 1 (port-separation criterion).** Let `A` be the age set used by one
physical port and let legal launch sequences have adjacent distance at least
`g > 0`. Every such launch sequence has an injective projection
`(j,a) -> t_j+a` on that port if and only if `span(A) < g`.

**Proof.** For sufficiency, suppose two distinct launches `t_i < t_j` and ages
`a,b in A` project to the same cycle. Then

```
a - b = t_j - t_i >= g.
```

Hence `span(A) >= |a-b| >= g`, contradicting `span(A) < g`.

For necessity, if `span(A) >= g`, choose `a=max(A)`, `b=min(A)`, and two launches
at zero and `a-b`. Their distance is legal and the events collide because
`0+a = (a-b)+b`. QED.

The theorem is per port. Events on different ports may share a cycle. It also
explains the fragment boundary: a multi-cycle availability interval whose span
is at least the initiation gap requires a richer holding, replication, or
transaction-multiplexing semantics and is rejected rather than silently
misinterpreted. In particular, `g=1` and an implementation guarantee
`W_I(o)={p,...,q}` with `p<q` is outside the fragment. For `p=1,q=2`, launches
at cycles zero and one map the old transaction's age-two event and the new
transaction's age-one event to output `o` at cycle two. A general window can
refine a singleton-`q` specification only when `q-p<g_I<=g_S` and the input
clauses also hold. Gap-one source-shaped examples therefore use only genuine
singleton guarantees `{q}`; this artifact does not invent or synthesize a
value-holding adapter.

## 3. Complete contextual criterion

**Theorem 2 (substitutive refinement).** For port-separated profiles, `I <= S`
if and only if all three clauses hold:

1. `g_I <= g_S`;
2. `R_I(x) subseteq R_S(x)` for every input port `x`;
3. `W_S(y) subseteq W_I(y)` for every output port `y`.

### Sufficiency

Take any client legal for `S`. Every adjacent launch pair is separated by at
least `g_S` and therefore by at least `g_I`. For every launch and input port, the
client contains every tag required by `R_S(x)`, hence every tag in the subset
`R_I(x)`. Every sample tag has an age in `W_S(y)` and therefore in `W_I(y)`.
The client's projection on all of its persisted drive and sample tags is already
injective by `S`-legality; this is a profile-independent property of the client.
The same tagged client is therefore legal for `I`.

### Necessity

- If `g_I > g_S`, launch at cycles zero and `g_S`, provide every
  specification-required tagged input, and take no samples. The client is legal
  for `S` and violates `I` at the second launch.
- If some `a` belongs to `R_I(x) \ R_S(x)`, launch once and provide exactly the
  tags required by `S`. The implementation-only tag `(0,x,a)` is absent.
- If some `a` belongs to `W_S(y) \ W_I(y)`, launch once, meet the specification
  input requirements, and sample `(0,y,a)`. The sample is promised by `S` but
  not by `I`.

Specification port separation makes the required same-port tags collision
free across launches. Input and output port names have disjoint directions, and
the write construction adds only its selected specification-guaranteed sample.
Thus every constructed client has an injective all-tag projection, is `S`-legal,
and is `I`-illegal. QED.

**Corollary 1.** Contextual refinement is a preorder.

**Proof.** Reflexivity is equality in the three clauses. Transitivity follows
from transitivity of integer order and set inclusion, followed by Theorem 2.
QED.

## 4. Synchronous products and compact witnesses

For profiles on disjoint directed ports, define the synchronous product `P x Q`
to share one launch stream, use gap `max(g_P,g_Q)`, take the disjoint unions of
read and guarantee maps, and use the larger horizon. This models one atomic
request implemented by independently named subcomponents; it is not an
asynchronous wiring composition.

**Proposition 1 (product congruence).** If `I1 <= S1` and `I2 <= S2`, then
`I1 x I2 <= S1 x S2`.

**Proof.** Every product port comes from one factor, so its span is below that
factor's gap and therefore below the product gap. Theorem 2 gives both factor gap
inequalities; monotonicity of `max` gives the product gap inequality. Disjoint
union preserves every read and guarantee inclusion. Apply Theorem 2 to the
products. QED.

The converse need not hold: a second factor with a larger shared gap can mask a
throughput mismatch in the first. Wiring an output to an input also requires a
value-association and timing-shift theorem outside this product rule.

**Corollary 2 (compact client).** Let `r_S` be the total number of declared
specification input ages. Every failed refinement has a counterexample with at
most two launches, at most `2*r_S` tagged input facts, and at most one output
sample. One launch suffices unless the gap clause is selected.

**Proof.** The gap construction uses launches zero and `g_S` and supplies the
`r_S` required facts for both transactions. A read failure uses one launch with
exactly the specification facts. A write failure adds one sample at the missing
specification age. These are the three necessity constructions of Theorem 2.
QED.

The producer persists the complete compact client record: the launch list,
every tagged drive, every sample, and the claimed kind, port, age, and first
absolute violation cycle. The independent checker parses and replays exactly
those stored events. It neither calls the producer's canonical-client routine
nor reconstructs drives from the profile. Corollary 2 still bounds the record by
the interface declaration rather than by the history arena.

## 5. Shortest first-violation clients

Define a client's first-violation time as the earliest cycle at which it is
illegal for `I` while remaining legal for `S`. If `I` does not refine `S`, let

```
T = { g_S                     if g_I > g_S }
    union all (R_I(x) \ R_S(x))
    union all (W_S(y) \ W_I(y)).
```

**Proposition 2.** The minimum possible first-violation time is `min(T)`.

**Proof.** A gap violation cannot occur before a second launch, whose earliest
specification-legal cycle is `g_S`. A tagged read or sample mismatch at age `a`
cannot be observed before cycle `a` after its launch. The three constructions in
Theorem 2 attain exactly those lower bounds using one launch, except for the gap
case, which uses two. QED.

The artifact resolves equal-time ties by kind, port, and age. The checker first
computes the actual earliest absolute implementation violation from the
persisted launches, drives, and samples; it then checks the claimed cycle,
kind/port/age tuple, the independently recomputed canonical tie choice, and the
already verified initial game rank `cycle+2`. It does not substitute the stored
age for absolute time. The deterministic tie order is not part of temporal
minimality.

## 6. Exact bounded family region

For parameter valuation `p`, write `r_P(x,a,p)` for membership of age `a` in
`R_P(x)` and `w_P(y,a,p)` for membership in `W_P(y)`. With admission assumption
`A(p)` and finite horizon `H`, define

```
Phi(p) = A(p)
         and port-separated(I,p) and port-separated(S,p)
         and g_I(p) <= g_S(p)
         and for every input x and 0 <= a <= H:
               r_I(x,a,p) implies r_S(x,a,p)
         and for every output y and 0 <= a <= H:
               w_S(y,a,p) implies w_I(y,a,p).
```

The input schema rejects a family if either profile is not port-separated at an
admitted valuation. On an admitted family, Theorem 2 makes the greatest safe
subset exactly `{p | Phi(p)}`. Every included valuation refines; every excluded
valuation has a client counterexample.

**Corollary 3.** If the admission predicate, gaps, and age-membership tests are
quantifier-free Presburger formulas, then `Phi` is quantifier-free Presburger.
On the bounded domain it is the logically weakest sufficient assumption: an
assumption `Psi` is sufficient exactly when `Psi => Phi` on that domain. Its
model set is semilinear.

The implementation enumerates the declared bounded domain. It does not claim an
unbounded quantifier-elimination procedure or a minimum-size formula.

## 7. Launch-history automata and alternating simulation

For a fixed port-separated profile `P` with horizon `H`, construct a history
automaton `T(P)`. A state is the finite set `A subseteq {0,...,H}` of ages of
active launches; legal histories have pairwise age differences at least `g_P`.
The initial state is empty.

- client input `tick` increments every age and drops ages beyond `H`;
- client input `launch` is enabled in the empty state or when `min(A) >= g_P`,
  and adds age zero;
- client input `sample:y@a` is a self-loop when `a in A cap W_P(y)`;
- component output `need:x@a` is a self-loop when `a in A cap R_P(x)`.

The age suffix in an action label preserves launch identity. The artifact's game
uses a valuation-independent state superset. Histories illegal at one valuation
can retain enabled edges, but are unreachable from the empty initial history:
the gap guard preserves pairwise separation on launch, and tick preserves age
differences while only dropping old entries. The correspondence below therefore
relates reachable legal histories, not every state in that superset.

The game
challenges implementation outputs and specification inputs, so inputs are
contravariant and outputs covariant. An action-level regression follows the
`g=1`, horizon-two path `launch,tick,launch,tick` to history `{1,2}` and checks
that the older transaction's `sample:o@2` and `need:x@2` are both enabled. The
next ticks check the drop boundary `{1,2}->{2}->{}`. A mutation that retains
only actions for the newest launch is rejected by a separately written action
checker; mere state existence or solver/oracle agreement is not used as a
substitute for this edge-level test.

**Theorem 3.** `I <= S` if and only if `T(I)` alternating-simulates `T(S)` from
their initial states.

### Sufficiency

Relate equal histories that are legal for `S`. Since `g_I <= g_S`, every such
history is also legal for `I`. Ticks preserve equality. A specification launch
is accepted by the implementation because the newest launch is at least
`g_S`, hence at least `g_I`; both successors add zero. Every specification
sample is accepted because `W_S(y) subseteq W_I(y)`. Every implementation need
is matched because `R_I(x) subseteq R_S(x)`. Equal histories therefore form a
simulation containing the initial pair.

### Necessity

A gap failure is exposed by an initial launch, `g_S` ticks, and the second
specification launch. A read or write failure at age `a` is exposed by an
initial launch, `a` ticks, and the unmatched tagged need or sample. Thus a failed
criterion clause removes the initial pair from every simulation. QED.

### Quiescent quotient

When every event age is strictly below the gap, no transaction has a remaining
port action when another launch becomes legal. Uniformly erase the `@a` suffix
from need/sample labels first; the raw tagged and untagged alphabets are not
identical. Map a nonempty history to its minimum age and the empty history to
`H`. Every older age is at least the gap and has no enabled port action, so
enabled relabeled actions depend only on the newest age. Tick commutes with the
map, including `{H}->empty` mapping to the saturated `H->H` step; launch is
enabled in both mapped states because `g<=H` and resets each to zero. This gives
matching transitions in both directions, hence alternating bisimulation after
uniform label erasure. The compact saturated age automaton is used by the
artifact for 64 legacy families. An edge-level regression checks this map on
every legal history of each retained serial valuation. The three overlapping
source-shaped families use the full history encoding. Both encodings use the
same game checker and satisfy Theorem 3 on every retained valuation.

## 8. Client time equals game rank

The checker uses losing rank one for a state with an immediately unmatched
challenge and rank `1 + max(reply ranks)` for a chosen challenge whose every
reply is losing. Safe pairs have rank `-1`.

**Proposition 3.** If the minimum client first-violation time is `tau`, the
initial translated pair has losing rank exactly `tau + 2`.

**Proof.** The canonical spoiler first issues the initial launch, then `tau`
tick challenges, then the unmatched second launch, need, or sample. These are
`tau + 2` challenge layers under the checker's convention. Before cycle `tau`,
none of Theorem 2's three clause failures is observable, so no shorter spoiler
can terminate. The argument is unchanged by other active launches because the
canonical path need not issue them and action tags identify the challenged
transaction age. QED.

The campaign checks this equality for all 691 failing timeline valuations.

## 9. Published-declaration normalization boundary

The artifact manually normalizes six timing declarations from the Lilac paper,
binding each record to the paper DOI, page, and figure or section locator. Five
reusable source examples are in the fragment: FPAdd, Mult, Shift, LutMult, and
HighRad. They cover 29 bounded valuations, including gap-one outputs at ages up
to eight. The sixth declaration is Figure 5(a), which the source explicitly
labels an initial erroneous FPU implementation. It is retained as a negative
boundary because one input interval spans ages zero and one while the event
delay is one. The artifact does not claim a Lilac parser, body semantics,
where-clause extraction, bit-width reasoning, or RTL correspondence.

Three bounded paired families instantiate the FPAdd, Shift, and HighRad timing
shapes in the full game campaign. They exercise overlapping transactions and are
safe exactly when the compared latency parameters agree.

## 10. Independent exhaustive contextual oracle

A separate module that imports neither timeline implementation enumerates every
port-separated profile with one input port, one output port, ages zero through
two, and launch gap one or two. It also enumerates the complete distinguishing
client universe for that micro-domain: the empty client, every one-launch client,
and every collision-free two-launch client at the only relevant launch distances
one and two, with all drive and sample subsets.

This yields 52 profiles, 3,665 clients, and 2,704 ordered implementation/
specification pairs. For each profile it constructs the exact legal-client
bitset directly. Contextual refinement is then bitset inclusion, independently
of the direct criterion implementation. Exactly 365 pairs satisfy client-set
inclusion and exactly the same 365 satisfy the gap/read/write criterion; the
disagreement count is zero. This is an exhaustive finite cross-check of the
client quantifier within its declared universe, not a machine proof of the
general theorem.

## 11. Why general games retain branching evidence

The deterministic tagged timeline translation admits a linear old-client
schedule for every failed clause. General output-nondeterministic interfaces are
different: two systems may have the same finite trace language while simulation
fails because one challenge must be matched against all specification replies.
The retained `branching` control has exact language `{epsilon, a, ab, ac}` on
both sides but requires a branching spoiler DAG. The general checker therefore
retains every universal reply and never advertises one separating word as a
complete witness.

## 12. Executable scope

The timeline campaign checks 67 families, 961 admitted valuations, and 66,688
valuation/state-pair obligations. The direct criterion, independently written
profile evaluator, physical collision enumerator, tagged client replay, and
translated game agree everywhere. All 691 failures have a replayed old client
and satisfy Proposition 3. A further 41 general controls add 520 valuations and
9,076 pair valuations. The independent micro-domain adds 52 profiles, 3,665
clients, and 2,704 ordered pairs with zero criterion/context disagreement. The
complete retained suite has 108 tests, including hand-written micro-client domain
checks and edge-level serial-quotient checks after uniform label erasure; the bibliography audit checks 69
cited entries and 69 unique stable locators; and clean reproduction compares 294
claim-relevant scientific files exactly in the retained historical reproduction.

The current native Windows CPython 3.12.14 run passes the 108-test suite,
regenerates all 114 retained input files byte-for-byte, and matches 284 retained
JSON objects and the micro-model pair table. It does not execute the POSIX
resource-limited drivers; historical host measurements remain separate.

These finite checks support the implementation and retained data. The general
theorems rest on the arguments above. The result does not establish value or RTL
equivalence, liveness, backpressure, arbitration, runtime-variable timing,
full-language extraction, or unbounded parameter synthesis.
