# Family-first incremental evidence architecture

Status: implementation in progress. This note records the measured bottleneck,
the invalidation boundary, and the architecture that subsequent family work must
follow.

## Measured bottleneck

The SQLite query layer is not the current bottleneck. The 432 MB immutable base
contains 140 documents, 8,947 pages and 667,224 line observations; indexed reason
queries take about 0.009 seconds and a 140-trial sidecar refresh takes 0.477 seconds.
The old formal `INTERBANK_DEPOSITS_AND_LOANS` paired build took about 1,895 seconds
because one CPU rebuilt the graph and the old capability validator then
canonicalized the complete semantic corpus again.

| Path | Elapsed | Exactness result |
|---|---:|---|
| Old formal paired build | ~1,895 s | Formal PASS |
| SQLite evidence, sequential unchanged topology engine | 137.071 s | Baseline |
| SQLite evidence, 12 balanced document workers | 13.810 s | 140/140 typed-equal to formal topology |
| Same content/spec/engine, per-document result cache hot | 0.075 s | 140/140 typed-equal; 140 hits, 0 recomputes |

The first optimization therefore uses processes for CPU-bound independent
documents. Redis would not remove graph CPU or canonicalization work and is not
the default. SQLite remains the local read-mostly index; an in-process/result
cache is cheaper than a network cache on this single VPS.

## Layer boundaries

1. **Filing identity.** One record binds bank, reporting period, statement scope,
   assurance, source PDF content reference and page denominator. Matching logic
   may inspect the evidence but may not use bank, filename, page number or period
   as a family selector.
2. **Versioned observations.** Native PDF, detector geometry, PP-OCR numeric,
   VietOCR semantic text and Gemma rescue are separate observations bound to an
   exact document/page/crop input and an engine/model/runtime/prompt revision.
   Rescue appends a new observation; it never overwrites the prior one.
3. **Per-document feature packet.** The selected observation axis, geometry,
   period/unit evidence and filing identity produce one immutable document root.
   A changed page/crop changes only its observation and its owning document root.
4. **Disposable query index.** SQLite materializes document/page/line fields and
   FTS search from those packet roots. It is rebuildable and never creates new
   OCR or mapping authority.
5. **Family graph result.** The cache key is
   `(document evidence root, family-spec SHA-256, shared-engine trust-closure
   SHA-256)`. Independent documents run in balanced worker processes. Results
   return in the fixed source-document order and carry their own content hash.
6. **Schema mapping.** The mapping key adds the schema authority root. A schema
   edit invalidates mapping/validation only; it does not invalidate OCR,
   geometry, document packets or family graph results.
7. **Formal aggregate.** A formal family artifact must bind the exact ordered
   document-result roots and the authenticated document-packet manifest. The
   current disposable SQL cache is not yet this authority. Full corpus byte
   replay is reserved for an OCR/extraction revision or a deliberate corpus
   audit, not every family edit.

## Invalidation rules

| Change | Recompute |
|---|---|
| One OCR/Gemma crop observation | That crop selection, its page/document packet, and affected document-family results |
| One page geometry/orientation extraction | That page packet, its document root, and affected document-family results |
| Family declarative spec | Family graph results only |
| Shared graph primitive | Graph results whose engine trust-closure key changed |
| Schema/template | Mapping and mapping validation only |
| Reporting-period inference primitive | Affected document packets and downstream results, not OCR pixels/text |
| Major detector/OCR model or extraction revision | New corpus snapshot; full audit replay is appropriate |

## Query policy

Family development first queries FTS/document metadata to shortlist candidate
pages and bounded neighbouring/continuation pages. The complete-document
uniqueness claim must remain provable: until a high-recall indexed shortlist is
shown typed-equal for a family, the engine falls back to the exact parallel
document scan. A shortlist may improve speed but may never silently convert a
miss into `NOT_OBSERVED`.

The current result cache already reuses all unchanged document/spec/engine keys.
The next formal-boundary change is the authenticated per-document packet
manifest and ordered result-root aggregate; it must replace, not merely bypass,
the old whole-corpus downstream canonicalization gate.

## New-only formal DAG planner V1

`bctc_ai.evaluation.incremental_formal_dag_v1` now implements the pure planning
boundary for
`source -> normalized spans -> retrieval -> graph -> numeric/pixel -> mapping -> seal`.
Gemma is a conditional side branch after the deterministic graph, so changing
its exact model or short structure-prompt ref invalidates Gemma and the cheap
mapping/seal descendants, but not source, normalization, retrieval, graph, or
numeric/pixel evidence.

The three execution modes have deliberately different authority:

| Mode | Denominator | Release seal |
|---|---|---|
| `DEV_FAST` | Explicit document subset | Never |
| `CORPUS_INCREMENTAL` | Every current document | Never |
| `RELEASE_SEAL` | Every current document | Required |

The planner is read-only: it neither authenticates bytes nor writes a cache.
The runner must project per-document packet, source-PDF and page-set refs from
the live authenticated store, authenticate any loaded output bytes, and pass
exact code/spec/model/prompt content refs. It then executes only `plan.runnable`,
adds immutable receipts for those outputs, and replans. An internally coherent
receipt is still a miss when any caller-current ref differs. A zero-hit
retrieval receipt must prove full-document fallback, and a `NOT_OBSERVED` graph
receipt must bind complete-document coverage against the exact current page-set
root and page count.

Synthetic bookkeeping benchmark on the 2026-08-23 development container (50
samples, 140 documents, 980 cached per-document receipts): a hot
`CORPUS_INCREMENTAL` plan had median 75.880 ms and p95 81.350 ms, with 840 active
hits and no runnable work. Changing one document page root had median 76.038 ms
and p95 80.990 ms; 139 documents retained all six active hits and the only
runnable node was that document's `SOURCE` stage. These figures measure planner
overhead only, not OCR, graph, model, or artifact I/O.

## Repeat/runtime circuit breaker

The planner accepts an optional tuple of exact `StageAttemptObservationV1`
records; the default empty tuple preserves the prior API and cache behavior.
Each record content-binds family, document/page denominator, stage dependencies,
the document-specific current `stage_key`, attempt ordinal, failure class/reason
or predeclared runtime budget, and its own identity. It also carries a separate
`algorithm_revision_key` derived only from the stage's exact code, spec, model
and prompt pins. The generic failure signature uses family, stage, algorithm
revision, attempt kind, failure class and reason; it deliberately contains no
bank, page number, filing ordinal or expected accounting value.

These observations remain bookkeeping, not execution authority: the caller
must authenticate the attempt evidence before passing it to the planner.
Within one algorithm revision the first failure forces only that document-stage
to a targeted recompute. A second identical signature across the same or a
different document blocks every node for that family/stage/revision with
`ALGORITHM_REVIEW_REQUIRED_REPEAT_FAILURE`; two predeclared runtime-budget
breaches similarly yield `ALGORITHM_REVIEW_REQUIRED_RUNTIME_BUDGET`. Three
ordinary failures cannot evade review by changing caller metadata and yield
`ALGORITHM_REVIEW_REQUIRED_FAILURE_ATTEMPT_LIMIT`. A code/spec/model/prompt
revision clears the old revision's block, but a document with prior stage
history must execute one targeted falsifier under the new key even when an exact
new-key receipt is present. Algorithm-review blocks propagate through dependent
nodes, and `RELEASE_SEAL` cannot treat them as cache hits or release authority.

Synthetic planner-only measurements on the 2026-08-24 development container
(50 samples, 140 documents, 980 receipts) were: empty history median 97.733 ms,
p95 99.124 ms; one targeted graph failure median 98.039 ms, p95 101.728 ms; and
a cross-document repeated-signature block median 81.188 ms, p95 82.295 ms. The
first-failure history gate therefore added about 0.306 ms at the median in this
run; the blocked plan is faster because it does not construct downstream stage
keys. No OCR, PDF, graph, model or authenticated corpus replay occurs in this
planner benchmark.

Integration order is therefore: wire existing authenticated document-store
projections into `CurrentDocumentRefsV1`; pin each stage's actual implementation
trust closure and declarative spec; store authenticated output refs beside the
pure receipts; run `DEV_FAST` during bbox/row/column debugging;
run `CORPUS_INCREMENTAL` after a family change; and invoke `RELEASE_SEAL` only at
the publication boundary. The release aggregator must bind the ordered current
document denominator and per-document seal refs; the planner itself adds no
mapping, absence, numeric, or release authority.
