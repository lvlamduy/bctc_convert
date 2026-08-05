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

## Core boundaries

- `ingestion`: discovery, immutable identity, document registration, dataset role.
- `rendering` / `preprocessing`: page rasterization, quality metrics, variant selection, coordinate transforms.
- `ocr`: model-neutral adapters implementing page/region/table/row/cell reads and text boxes.
- `layout`, `tables`, `rows`: reading order, table proposal ensemble, continuation graph, cell provenance.
- `document_phase`: sequence-based COVER/AUDIT/STATEMENT/POLICY/NOTES/APPENDIX classification.
- `axes`: geometry-backed period, unit, sign, and scope binding.
- `schema`: append-only SchemaGraph and migration checks.
- `mapping`: candidate retrieval, ordered subtree alignment, constrained assignment, optional small-context reranking.
- `mongodb_reference`: read-only historical weak-reference index and conflict reporting.
- `reference_builder`: isolated Role A outputs.
- `validation`: checks only; never value generation.
- `export`: template-preserving workbook and supporting sheets.
- `storage`: atomic checkpoints, manifests, backup, integrity, and resume.

For usable native text layers, the first deterministic table path segments PDF words into runs at relative word-gap discontinuities, clusters repeated numeric right edges into value axes, identifies a distinct note-reference axis, groups y-aligned bands, and then attaches preceding wrapped label lines only when geometric/typographic continuation evidence is sufficient. Label-only rows remain ordered section context. Thresholds are relative to page or text height and live in `config/tables/geometry.yaml`; report-, bank-, page-, and absolute-coordinate rules are prohibited.

Header binding is axis-local. Dates determine current/comparative roles rather than left/right order. Snapshot dates, explicit date ranges, stated month durations, and YTD wording have separate paths, and unit evidence retains its source box. Ambiguous or absent axes fail closed instead of defaulting to a conventional column order.

## Model adapters and scheduling

Every backend sits behind `read_page`, `read_region`, `read_table`, `read_row`, `read_cell`, `return_text_boxes`, and `return_structure`. Large models run sequentially in isolated services; each batch is checkpointed and verified before the next model loads. Candidate backends from the directive are not approved merely by name: each must pass Vietnamese banking-document fixtures, GPU compatibility, throughput, VRAM, numeric exactness, and hallucination tests.

The current RTX 5070 Ti has 16,303 MiB and compute capability 12.0. The preinstalled PyTorch build lacks `sm_120`; therefore the initial architecture treats model services as isolated, replaceable runtimes rather than importing them into the bootstrap environment.

## Confidence policy

`AUTO_VERIFIED_HIGH` requires every evidence gate, including clear cell geometry, independent numeric verification, header-bound period, sourced unit, verified sign, contextual schema alignment, no PDF/history conflict, accounting pass, and sufficient candidate gap. A single model vote can never satisfy this gate.

Other terminal statuses are `AUTO_VERIFIED_MEDIUM`, `REVIEW_REQUIRED`, `UNRESOLVED`, `NOT_APPLICABLE`, and `NOT_OBSERVED`. Absence of evidence is not zero.

## Replay and frozen evaluation

Artifacts live below `output/<dataset-role>/<run-id>/<document-id>/` and carry input/model/config/output hashes. OCR replay begins at stored OCR; mapper replay begins at reconstructed rows/axes; validation replay begins at pipeline results. An artifact is skippable only after integrity verification.

Before holdout execution, code, config, model manifests, source tree, dataset role, and allowed evidence are frozen and hashed. Holdout registration is append-only; a document exposed to development cannot later be relabeled untouched.
