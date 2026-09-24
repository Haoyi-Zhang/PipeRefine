# Sources and provenance

## Project-created material

All Python source, deterministic generators, JSON control families, retained
result files, proof notes, tests, CSV ledgers, and documentation in this
repository were created for this project and are distributed under `LICENSE`
(MIT). The generated families are diagnostic mathematical fixtures, not
measurements of deployed hardware and not derived from private RTL.

The timeline corpus contains 12 handwritten controls, 52 fixed-seed generated
families, and three source-shaped paired families. The general corpus contains 41
finite-game controls. The independent micro-model exhaustively enumerates its
small declared universe. No generated case is removed after observing its
outcome.

## Consumed scholarly source facts

The only paper-specific data encoded as executable artifact input are six
manually normalized timing declarations from:

- Rachit Nigam, Ethan Gabizon, Edmund Lam, Carolyn Zech, Jonathan Balkind, and
  Adrian Sampson, *Parameterized Hardware Design with Latency-Abstract
  Interfaces*, DOI `10.1145/3779212.3790199`.

`anchor-inputs/` records only normalized declaration facts and source locators:

| Record | Locator | Artifact treatment |
|---|---|---|
| FPAdd | p. 5, Fig. 4 | reusable example; seven latency valuations accepted |
| initial FPU | p. 5, Fig. 5(a) | source labels it erroneous; retained boundary because one input spans ages 0 and 1 at gap 1 |
| Shift | p. 6, Fig. 6(a) | reusable example; seven latency valuations accepted |
| Mult | p. 9, Sec. 6.1 | reusable example; seven latency valuations accepted |
| LutMult | p. 10, Fig. 9(a) | reusable example; singleton output at age 8 accepted |
| HighRad | p. 10, Fig. 9(c) | reusable example; seven gap/latency valuations accepted |

The source paper identifies itself as CC BY-NC-ND 4.0. The paper is not
redistributed. The artifact retains only attributed factual normalizations needed
to test the model boundary. No component body, parser, where-clause
implementation, bit width, RTL, figure image, or paper text is copied.

The FPU boundary is not presented as a newly discovered defect. The source itself
calls Figure 5(a) the initial erroneous implementation and reports that Lilac
rejects it. The artifact asks a narrower question: whether that declared timing
shape belongs to the unqueued port-separated substitution model.

## Citation-only literature

The manuscript bibliography contains 69 scholarly entries and cites all 69.
`literature/references.bib` is the standalone retained copy used by the audit.
`literature/bibliography-audit.csv` records title, year, venue, stable identifier,
verification URL, verification basis, and technical role for every entry.
`literature/citation-counts.csv` and `literature/manuscript-citations.txt` retain
the exact citation inventory.

The deterministic bibliography check reports 65 DOI records and four records
with stable scholarly URLs, for 69 unique locators. It enforces a minimum of 55
references, complete in-text use, locator uniqueness, audit/BibTeX agreement,
and nine high-risk metadata invariants, including current published records for
Lilac, Anvil, and Spade. This structural and retained-metadata check is evidence
against padding, stale identifiers, and silent metadata drift; it is not live
resolver evidence or independent validation of every cited claim.

`external_resources.csv` mirrors all 69 entries with their scholarly or official
URLs, access basis, integration mode, and supported claim family. No external
paper PDF, codebase, benchmark, or proprietary dataset is bundled. The closest
lines cover static timing languages, interface and contract refinement,
parametric timed verification, family-based verification, counterexample
methods, Presburger foundations, and symbolic/sequential hardware verification.

## External software and template assets

The executable artifact has no third-party runtime dependency. The surrounding
paper package contains the supplied `IEEEtran.cls` and `IEEEtran.bst`; they are
unmodified and are not part of the standalone repository archive. TeX and
BibTeX are document build tools rather than scientific baselines.

## Trust boundary

The timeline producer, independent timeline checker, exhaustive contextual
micro-model, general reverse-game checker, and bibliography checker use distinct
code paths, but they still run in Python and implement the stated mathematical
or metadata specifications. The six source records are manual, locator-bound
normalizations from one paper. The artifact establishes repeatable finite checks
of the supplied contracts and retained bibliography; it does not establish
source extraction, industrial representativeness, mechanized theorem
correctness, independent literature review, or independent peer review.
