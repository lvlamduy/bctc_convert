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
