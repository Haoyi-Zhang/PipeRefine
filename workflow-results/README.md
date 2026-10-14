# Reproducible query workflow results

This collection records native local Windows CPython 3.12.14 runs on owned finite
contracts. It contains no hardware, production, external compiler or public-CI
measurement. `environment.json` records the observed OS and CPU; no remote CPU
is inferred. The benchmark cohorts and earlier result directories are unchanged.

`reproduction-normal.json` and `reproduction-optimized.json` each contain 118
named discovery results, two separate four-test suites, literal child arguments,
stdout/stderr, resource capabilities, source hashes, 114 exact input rebuilds,
and 294 exact scientific-file comparisons across all five campaigns. Their
test identities overlap intentionally: optimized execution is a consumer-gate
check, not additional independent scientific observations. `campaigns/` retains
fresh raw summary/measurement objects, not copies of all historical outputs.
Exact compared semantic outputs already reside in the earlier five directories.

`compound/` contains the current factor inputs, four disjoint maximum-gap cells,
certificates, witnesses, clients, summary and measurement. The independent replay
checks factor-to-cell coverage and consumes persisted evidence without product
or client constructors. Safe product values are `p=1,2`; factor-safe intersection
is only `p=1`. This is one separately labeled workflow example, not an increased
old benchmark denominator. At `p=3` failure cycle is 2 and initial losing rank 4.

`profiles/answers.jsonl` is the identical encoded answer stream for criterion,
bitset and scalar paths on the same 67 families and 961 valuations, including
all 691 canonical clients. Its SHA-256 is
`0c73b2917ad84f9fc4aa9ad81d44bb039183c53775eaebda4272b4c86e5a1c59`.
Each method has a raw stage/metric receipt and whole-process launch receipt.
All arms include decode, admission/collisions, exact queries, client construction
and independent replay, encoding and answer-file writing. Game arms also
construct and consume rank certificates and selected spoilers in memory; they
do not persist every certificate in this profile. Full certificate-file replay
belongs to the complete campaign. Neither workflow includes a source front end
or RTL/hardware execution.

The direct criterion is cheapest in this one sequential fresh-process run.
Body walls are 0.0580274, 0.4663107 and 0.5621762 seconds; whole-process walls
are 0.1786620, 0.5697159 and 0.6676995 seconds. CPU quanta, peak owned Windows
working-set/commit bytes, and every stage are in receipts. Whole wall includes
startup/imports, receipt/hash I/O and exit. Peak working set is not POSIX RSS or
an OS memory cap. One sample per method does not establish statistical superiority
or a memory winner. No algorithmic novelty is inferred from these timings.

`controls/` contains named three-test recording and seven-test product receipts
in normal and optimized modes. Typed bindings, exact two-sided output coverage,
and supplied-output bibliography replay do not alter valid-domain truth. The
controls are included in the full 118-test runs, not counted again.

`source-bindings.json` inventories literal source files and all input hashes; it
does not claim every function executed or independent authorship. Reports retain
actual capability flags. In portable mode CPU checks are cooperative, the parent
has a wall watchdog, OS CPU/address-space caps are false, and unavailable RSS is
null. The default POSIX hard-limit path is preserved but not freshly run here.
`$PROJECT` and `$OWNED_OUTPUT` replace only machine-specific path prefixes in
public receipts; private raw receipts retain those absolute paths unchanged.
The original 102-test POSIX and 108-test Windows core-only records and historical
CPU/RSS values remain historical evidence, not current capability claims.
