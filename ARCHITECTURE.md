# Architecture

## Evidence flow

```text
immutable PDF
  -> registration + hashes
  -> page render + quality classification
  -> controlled preprocessing variants
  -> independent document/OCR/layout adapters
  -> table, row, cell, and continuation reconstruction
  -> period/unit/sign/scope axes
  -> ordered SchemaGraph candidate alignment
  -> accounting and cross-evidence validation
  -> acceptance gate
  -> Excel + provenance/review/unresolved/question artifacts
```

No downstream component may mutate or replace upstream evidence. Corrections create new versioned artifacts with links to the artifact they supersede.

## Role isolation

Role A builds `machine_reference.jsonl` from independent PDF reading, pixel evidence, OCR/layout votes, schema context, weak MongoDB history, and accounting checks. It is a machine reference—not human gold or legal truth.

Role B executes the production PDF-to-Excel pipeline. In frozen evaluation, its process identity and allowed-evidence manifest must exclude Role A outputs. A comparison job receives both outputs only after Role B completes.

Matched scan/searchable fixtures are registered before content inspection. Page correspondence is a comparison-stage operation based on ordered pixel fingerprints; it cannot use OCR text, numeric values, filenames, or a fixed page offset. Role B receives only the scan-side PDF/render, model/config, and its own intermediate artifacts. The searchable PDF and Role A result are inaccessible until the compare stage. Historical weak reference is also excluded from mapping and becomes visible only after a schema ID is resolved for discrepancy/reread decisions.

Each Role B OCR run is sealed before Role A comparison. The seal re-hashes every render, model output, metrics file, package freeze, model configuration, pinned model weights, and the sealing implementation. It also requires preprocessing to have begun from a clean Git commit. Comparison refuses a changed or incomplete seal.

Role C is an independently sealed non-generative word-geometry reader. It consumes only the already sealed scan render, never the searchable Role A source/result. Role B remains the page-context/label proposal because E-0011 measured only 3/140 source-exact Role C labels; Role C contributes period/note axes, row ownership, cell observations, and boxes. Fusion is explicit and neither role can silently overwrite the other. The decision and limitations are recorded in `docs/decisions/0006-independent-word-geometry.md`.

Cross-reader alignment is ordered and value-independent. It may represent a wrapped logical row as two candidate rows or flag two reference rows collapsed into one generated row, but it never uses numeric agreement to choose the path. A collapsed-reference action has no automatic numeric interpretation and is routed to table reconstruction. Evaluation reports aligned-evidence coverage, conditional agreement, and strict whole-reference agreement separately; missing or merged rows therefore cannot inflate the headline denominator.

Scope exclusion is stateful within an ordered statement block. A page/section heading such as “CÁC CHỈ TIÊU NGOÀI BÁO CÁO TÌNH HÌNH TÀI CHÍNH” switches the entire following CDKT row sequence to `OFF_BALANCE_SHEET`; it is not sufficient to blacklist a few familiar item names. State resets at an explicit statement boundary.

## Core boundaries

- `ingestion`: discovery, immutable identity, document registration, dataset role.
- `rendering` / `preprocessing`: page rasterization, quality metrics, variant selection, coordinate transforms.
- `ocr`: model-neutral adapters implementing page/region/table/row/cell reads and text boxes.
- `layout`, `tables`, `rows`: reading order, table proposal ensemble, continuation graph, cell provenance.
- `document_phase`: sequence-based COVER/AUDIT/STATEMENT/POLICY/NOTES/APPENDIX classification.
- `axes`: geometry-backed period, unit, sign, and scope binding, including versioned table-level period propagation across accepted continuations.
- `schema`: append-only SchemaGraph and migration checks.
- `mapping`: candidate retrieval, hierarchy-first lexicographic ranking, template-workbook-order alignment, constrained one-to-one assignment, and optional small-context reranking.
- `reference`: read-only historical weak-reference index and hash-bound calibration review registries. History can be queried only after an ID is resolved and cannot participate in mapping or confidence promotion; reviewed fixtures cannot route production pages.
- `values`: non-destructive raw observation and normalized numeric/value-status contracts.
- `reference_builder`: isolated Role A outputs.
- `validation`: checks only; never value generation.
- `export`: template-preserving workbook and supporting sheets.
- `storage`: atomic checkpoints, manifests, backup, integrity, and resume.

For usable native text layers, the first deterministic table path segments PDF words into runs at relative word-gap discontinuities, clusters repeated numeric right edges into value axes, identifies a distinct note-reference axis, groups y-aligned bands, and then attaches preceding wrapped label lines only when geometric/typographic continuation evidence is sufficient. Geometry v2 additionally separates adjacent financial tokens when both tokens are independently valid and their gap exceeds a configured fraction of text height; tightly spaced digit groups remain one value. Short parenthetical continuation lines may attach to the preceding label. Trailing axis-assigned text without numeric evidence is excluded from the table span, while malformed digit-bearing cells remain visible for reread. Label-only rows remain ordered section context. Historical v1 thresholds remain in `config/tables/geometry.yaml`; the current calibration thresholds are versioned in `config/tables/geometry-v2.yaml`. Report-, bank-, page-, and absolute-coordinate rules are prohibited.

For scan word boxes, `word_box_rows.py` infers period axes from header geometry, uses right edges for right-aligned values, clusters y anchors, and attaches label lines toward the next compatible downstream anchor. It preserves internal parent/section labels but moves label-only material below the final numeric anchor into a separate trailing-context collection that is mapping-ineligible until continuation evidence resolves it. OCR-empty cells are never filled from neighbors or arithmetic. A visibly empty cell can normalize to zero only after the row, numeric-cell geometry, and table structure are verified. A dash may be recovered only from a dash-like token on the correct axis or from one constrained, high-contrast horizontal image component passing normalized shape/position gates; the crop and component measurements become provenance. Multiple substantive numbers in one cell remain `INVALID`.

Header binding is axis-local. Dates determine current/comparative roles rather than left/right order. Snapshot dates, explicit date ranges, stated month durations, and YTD wording have separate paths, and unit evidence retains its source box. A complete table map can propagate to a headerless continuation only through versioned adjacency/context/axis gates while retaining the original header page and box. Ambiguous, partial, or changed axes fail closed instead of defaulting to a conventional column order.

## Model adapters and scheduling

Every backend sits behind `read_page`, `read_region`, `read_table`, `read_row`, `read_cell`, `return_text_boxes`, and `return_structure`. Large models run sequentially in isolated services; each batch is checkpointed and verified before the next model loads. Candidate backends from the directive are not approved merely by name: each must pass Vietnamese banking-document fixtures, GPU compatibility, throughput, VRAM, numeric exactness, and hallucination tests.

Generated Markdown/HTML is not a cell-geometry interface. E-0010 demonstrated that a VLM may preserve many visible numbers while collapsing neighboring rows and shifting later value pairs. High-confidence acceptance therefore requires an independently verified cell axis/bounding-box reader and targeted original-image rereads for every structural or numeric disagreement.

E-0011 demonstrates the value of this separation on a targeted calibration only: Role C restored 140/140 one-to-one rows and 264/264 machine-reference cells, including three pixel-supported dashes and one OCR dash-glyph normalization. It does not establish human-gold, schema, multi-bank holdout, or production accuracy, and it promotes zero rows to high confidence.

The current RTX 5070 Ti has 16,303 MiB and compute capability 12.0. The preinstalled PyTorch build lacks `sm_120`; therefore the initial architecture treats model services as isolated, replaceable runtimes rather than importing them into the bootstrap environment.

## Confidence policy

`AUTO_VERIFIED_HIGH` requires every evidence gate, including clear cell geometry, independent numeric verification, header-bound period, sourced unit, verified sign, contextual schema alignment, no PDF/history conflict, accounting pass, and sufficient candidate gap. A single model vote can never satisfy this gate.

Other terminal statuses are `AUTO_VERIFIED_MEDIUM`, `REVIEW_REQUIRED`, `UNRESOLVED`, `NOT_APPLICABLE`, and `NOT_OBSERVED`. Absence of evidence is not zero.

Confidence status is separate from value disposition. The latter is one of `OBSERVED_VALUE`, `OBSERVED_ZERO`, `NOT_OBSERVED`, `OUT_OF_SCOPE_FOR_TARGET_TEMPLATE`, `AMBIGUOUS_MAPPING`, or `REFERENCE_NOT_YET_BUILT`. A visible dash or verified empty numeric cell is zero while retaining its raw observation; a row absent from the PDF has no cell value.

## Replay and frozen evaluation

Artifacts live below `output/<dataset-role>/<run-id>/<document-id>/` and carry input/model/config/output hashes. OCR replay begins at stored OCR; mapper replay begins at reconstructed rows/axes; validation replay begins at pipeline results. An artifact is skippable only after integrity verification.

Before holdout execution, code, config, model manifests, source tree, dataset role, and allowed evidence are frozen and hashed. Holdout registration is append-only; a document exposed to development cannot later be relabeled untouched.
