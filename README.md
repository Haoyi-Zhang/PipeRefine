# Parametric refinement for pipelined latency-abstract interfaces

This standalone artifact implements and checks the bounded finite-state fragment
described in the accompanying paper. It uses only the Python standard library,
requires no network access, and does not call an external solver or model API.
The code is distributed under `LICENSE` (MIT).

The complete reproduction workflow below requires a POSIX system
providing Python's `resource` module (for example Linux). Python 3.12 is used by
the supplied Ubuntu 24.04 scientific-check workflow. Unit tests and the core
finite algorithms also run natively on Windows; that path does not execute the
POSIX resource-limited drivers.

## Scientific scope

A timing profile has a minimum launch gap, finite input read-age sets, finite
output guarantee-age sets, and a finite horizon. Transactions may overlap. The
profile is admitted only when, on every physical port, the span of its declared
ages is strictly smaller than the launch gap. The analyzer checks whether an
implementation safely replaces a specification for every admitted valuation of
a bounded integer parameter family.

For admitted profiles, the direct criterion is:

- the implementation launch gap is no larger than the specification gap;
- every implementation input-read age is required by the specification;
- every specification output-guarantee age is provided by the implementation.

Failed clauses produce a transaction-tagged old-client counterexample. The
persisted record contains its actual nonnegative launches, every drive and
sample tag, and failure metadata. An independent checker enforces global
port/cycle injectivity across all tags, replays the first absolute violation,
and binds it to a separately checked game rank. The artifact also translates
profiles to launch-history interface games and validates enabled actions for
older overlapping transactions as well as tick/drop boundaries.

## Retained evidence

### Timeline contracts

`timeline-inputs/` contains 12 handwritten semantic controls, 52 fixed-seed
generated families, and three source-shaped overlapping families. The retained
campaign covers 67 families, 961 valuations, and 66,688 valuation/state-pair
obligations: 270 valuations are safe and 691 fail. Every failure has a replayed
old client. Direct criteria, independent profile evaluation, two-launch physical
collision search, persisted-event replay, translated games, action-level edge
checks, and absolute-client-time/game-rank checks have zero retained
disagreement.

### Independent exhaustive contextual micro-model

`src/exhaustive_context.py` deliberately imports neither `timeline.py` nor
`timeline_check.py`. It enumerates all port-separated profiles with one input,
one output, ages 0 through 2, and gaps 1 or 2. It then enumerates the complete
distinguishing client universe for that domain rather than constructing only
the theorem's canonical witnesses.

The retained result contains 52 profiles, 3,665 collision-free clients, and all
2,704 ordered profile pairs. Explicit legal-client-set inclusion and the direct
gap/read/write criterion each accept exactly 365 pairs and disagree zero times.

`client_legal` checks ownership, nonnegative ordered launches, integer tags, and
optional-event collisions independently of the client's origin. Hand-written
clients do not bypass the domain checks used by the enumerator.

### Lilac declaration normalization

`anchor-inputs/` records six manual timing-declaration normalizations from the
published Lilac paper, each bound to its DOI, page, and figure or section
locator. Five reusable source examples are inside the fragment over 29 bounded
valuations. The sixth is Figure 5(a), which the source explicitly labels an
initial erroneous FPU implementation; its gap-one input spans ages zero and one
and is retained as a close same-port collision boundary.

This layer is source grounding only. It is not a parser, source/body theorem,
where-clause extractor, bit-width analysis, or RTL validation.

### General interface-game controls

`inputs/` contains 41 finite-game families for broader semantic, schema,
certificate, and branching-witness controls. The valuation-bitset producer and
a separately implemented reverse AND/OR attractor agree across 520 valuations
and 9,076 valuation/state-pair obligations (186 safe, 334 failing). The
same-finite-language control demonstrates why a general simulation failure may
require a branching spoiler DAG rather than one separating word.

### Bibliography integrity

`literature/` retains the 69-entry scholarly bibliography used by the paper, the
manuscript citation-key inventory, citation counts, and a row-by-row metadata
audit. `run_bibliography.py` enforces at least 55 entries, requires every entry
to be cited, rejects duplicate or missing stable locators, cross-checks the audit
catalog, and guards nine high-risk published metadata records. The current
result has 69 cited entries, 175 citation occurrences, 65 DOI records, four
stable scholarly URL records, and 69 unique locators.

This is a deterministic structural and retained-metadata audit. It does not
replace reading the cited work, live DOI resolution, or independent novelty
review.

## Reproduction

Run from this directory:

```bash
python -m unittest discover -s tests -v
python -B tests/reply_index_regression.py
python -B -O tests/reply_index_regression.py
python run.py --check-only
python run_timeline.py --check-only
python run_anchor.py --check-only
python run_exhaustive.py --check-only
python run_bibliography.py --check-only
python reproduce.py
```

The two explicit reply-index checks each run four additional finite regression
groups; they are also explicit steps in scientific CI. They are separate from
the frozen 108-test discovery inventory checked by `reproduce.py`. Their
test-local reference enumerates raw-edge arenas, spoiler trees and all tiny
postfixed relations, not an earlier implementation. The producer builds local
ordered reply buckets after mask evaluation; the independent checker builds
its own buckets after guard evaluation. Parallel edges, disabled masks,
canonical reply sets, rank cells and all reported semantic/visit counts retain
their meanings. This is an implementation-only change with no measured
speedup claim.

`reproduce.py` creates fresh temporary directories; regenerates all 41 general,
67 timeline, and six source records; reruns the general, timeline, source,
exhaustive-micro, and bibliography campaigns; checks certificates, spoiler DAGs,
tagged clients, source bounds, collision oracles, and bibliography mutations;
and byte-compares 294 claim-relevant scientific files. A successful run reports
`status: pass` and the current unit-test count. Timing measurements are intentionally
excluded from deterministic byte equality. The retained `results/reproduction.json`
records a historical 102-test reproduction and historical paper-build checks;
it is not evidence that the edited manuscript was rebuilt. The current native
Windows CPython 3.12.14 run passes 108 tests and replays the finite core results,
with 114 byte-identical input regenerations, 284 matching JSON objects, and an
unchanged 2,704-row micro-pair table. It does not execute the POSIX drivers.

To rebuild retained outputs into separate directories without overwriting them:

```bash
python run.py --output /tmp/general-results
python run.py --output /tmp/general-results --check-only
python run_timeline.py --output /tmp/timeline-results
python run_timeline.py --output /tmp/timeline-results --check-only
python run_anchor.py --output /tmp/anchor-results
python run_anchor.py --output /tmp/anchor-results --check-only
python run_exhaustive.py --output /tmp/micro-results
python run_exhaustive.py --output /tmp/micro-results --check-only
python run_bibliography.py --output /tmp/bibliography-results
python run_bibliography.py --output /tmp/bibliography-results --check-only
```

To regenerate deterministic inputs:

```bash
python src/generate.py /tmp/general-inputs
python src/generate_timeline.py /tmp/timeline-inputs
python src/generate_anchor.py /tmp/anchor-inputs
```

## Repository map

- `src/domain.py`, `src/solve.py`: general-family interpretation and bitset producer.
- `src/check.py`: independent parser, local-rank checker, reverse AND/OR oracle,
  and spoiler-DAG checker.
- `src/timeline.py`: profiles, direct criterion, launch-history translation, age
  quotient after uniform need/sample age-label erasure, and canonical clients.
- `src/timeline_check.py`: separately written evaluator, physical collision
  enumerator, persisted-event client replay, canonical tie/rank binding, and
  launch-history action/drop checker.
- `src/exhaustive_context.py`: independent exhaustive one-input/one-output
  contextual micro-model.
- `src/bibliography_check.py`: BibTeX/citation/audit validator and mutation target.
- `src/generate_anchor.py`: exact rebuild of six locator-bound source records.
- `inputs/`, `timeline-inputs/`, `anchor-inputs/`: retained JSON inputs.
- `results/`, `timeline-results/`, `anchor-results/`, `micro-results/`,
  `bibliography-results/`: retained deterministic scientific outputs.
- `literature/`: bibliography copy, citation inventory, and metadata audit.
- `tests/`: semantic, schema, mutation, source, exhaustive, and bibliography tests; the exact discovery inventory is recorded by `results/test-results.json`. `reply_index_regression.py` is the separately executed finite suite above.
- `proofs/`: readable proof notes and explicit scope boundaries.
- `claim_evidence_ledger.csv`: material claims mapped to proof and evidence.
- `external_resources.csv`, `SOURCES.md`: scholarly-source inventory and provenance.

## Trust boundary and non-claims

The producer is never accepted as its own checker. In check-only mode the
timeline runner does not import or call the producer's canonical-client
constructor: it parses the retained launches, drives, samples, and metadata.
The timeline checker also does not import the producer's profile evaluator or
criterion; the collision oracle enumerates launch/age pairs rather than calling
the span test; its action checker derives expected enabled edges independently;
the micro-model imports neither timeline implementation; and the general checker
does not import the bitset solver. All executable paths still share Python, the
supplied schemas, and the declared mathematics. These are independent
implementation checks, not proof-assistant verification or independent human
review.

The artifact does not establish automatic extraction from Lilac or another
language, functional/data equivalence, RTL equivalence, reset semantics,
backpressure, queues, arbitration, reordering, fairness, liveness, runtime-varying
timepoints, unbounded parameter synthesis, or industrial workload prevalence.
