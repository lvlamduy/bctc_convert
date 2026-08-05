# Project memory, strategy, results, and change log

This is the durable retrieval point for project context. It summarizes user authority, design strategy, verified results, open constraints, and changes. Detailed normative checks remain in `ACCURACY_REQUIREMENTS.md`; current metrics remain in `PROGRESS_REPORT.md`; individual decisions live under `docs/decisions/`.

## Authoritative user clarifications

### 2026-08-05 — mapping context

- Item order is critical because many labels repeat.
- Resolve ambiguity using item clusters, parent/child, preceding/following rows, physical position, section, and schema order; never use a name alone when it returns several candidates.
- Main-statement note columns are references into TM, not values.
- Assess and correct blur, dark/colored table headers, skew, and perspective before OCR.
- The user supplied a hierarchy reference folder named approximately `vsl_level`; it is present as `vst_level` and now contains four hierarchy workbooks. Treat those workbooks as supporting structural evidence, preserve their hashes, and never let them override visible PDF evidence.

### 2026-08-05 — cash flow and scope

- Indirect LCTT ordered anchors: 4162 “Lợi nhuận trước thuế” then 4156 “Điều chỉnh cho các khoản”.
- Direct LCTT ordered anchors: 4123 interest received then 4124 interest paid.
- Cash-flow schema membership must be segmented by contiguous workbook position, never by numeric interval. The workbook has block 1 at positions 1–57 (endpoint IDs 4155→4168, profit/adjustment anchors) and block 2 at positions 58–107 (endpoint IDs 4104→4116, receipt/payment anchors); ID 4154 is at position 63, not a branch endpoint.
- The user's latest wording calls 4104–4154 indirect and 4155–4168 direct, which conflicts with the earlier ordered examples, visible labels, the `vst_level` direct-title workbook, and the actual endpoints. `Q-BOOT-001` is reopened; branch blocks are preserved and semantic high-confidence acceptance is fail-closed meanwhile.
- “Bảo lãnh vay vốn”, “Cam kết giao dịch hối đoái”, “Tài sản và chứng từ khác”, and similar off-balance-sheet indicators must not map to CDKT.

### 2026-08-05 — tables and validation

- Tables and even rows can break across pages.
- Long item labels can wrap across several lines and must become one logical row.
- Validate horizontal totals, vertical totals, and child sums against parents. Validation diagnoses and triggers rereads; it never invents a value.
- Models run locally on the user’s VPS with no external token charge, so use as many targeted independent passes as accuracy needs while respecting GPU VRAM.

### 2026-08-05 — scale, models, and cumulative periods

- Use current state-of-the-art model candidates, but the main reliability comes from general logic and algorithms.
- The system must generalize across thousands of banks/companies, separate/parent/consolidated scope, quarters, years, audit/review status, and layouts. Never enumerate bank/page/coordinate cases.
- Regulatory forms and semantic order are reusable; bank- and period-specific names belong in evidence-backed alias data/config, not procedural code.
- Some quarterly reports present cumulative/YTD values. When the requested output is quarter-only, derive by subtraction only from two visible PDF values with matching schema, scope, unit, accounting basis, and compatible periods. Preserve both source-cell provenances and the formula. A derived result can never be high-confidence as a directly observed cell.
- Store project notes, strategies, results, and changes durably in Markdown so they are not dependent on chat history.
- Commit every verified implementation milestone to the feature branch so code can be recovered and compared by version. Keep source PDFs, model weights, secrets, and generated run output outside Git.
- Record every installed package/model/driver, version, upstream URL/revision, SHA-256, configuration, smoke test, and rebuild command. Preserve test strategy and paper-derived hypotheses in versioned files.

## General strategy

1. Register every input by SHA-256 and freeze dataset role before inspection.
2. Classify PDF pages with a sequence decoder, retaining UNKNOWN when text/OCR evidence is absent.
3. Render at controlled DPI; assess page and local regions; create only relevant reversible variants.
4. Run a document parser plus independent word/cell geometry OCR; escalate difficult crops to another model family.
5. Reconstruct tables through proposal fusion, logical wrapped rows, and evidence-gated cross-page continuation.
6. Bind period, unit, sign, scope, and note reference by header-to-column geometry.
7. Generate candidates from schema/aliases, then use ordered dynamic-programming/subtree alignment and global constraints. Values are not standalone mapping features.
8. Validate arithmetic without value generation; reread disagreements.
9. Keep Role A and Role B evidence isolated for frozen evaluation.
10. Export accepted values plus complete provenance/review/unresolved/questions/schema-additions/run metadata.

## Model/runtime strategy

- Primary benchmark candidate: PaddleOCR-VL-1.6 (0.9B) for document structure.
- Independent geometry/numeric candidate: the current PP-OCR generation and PP-StructureV3.
- Independent document candidate: MinerU2.5-Pro or the newest reproducibly available MinerU release.
- Difficult-region candidate: DeepSeek-OCR-2.
- Mapping reranker candidate: Qwen3.6-27B quantized, with small row/block prompts only. Its fit on 16 GB VRAM must be measured; it is not the numeric reader.
- Model names do not grant approval. Each must pass Vietnamese bank fixtures, exact-number/sign tests, table geometry, throughput, VRAM, and hallucination measurements.
- The RTX 5070 Ti is Blackwell `sm_120`. Preinstalled PyTorch 2.5.1+cu124 fails a real CUDA kernel smoke test. The isolated PyTorch 2.12.0+cu130/TorchVision 0.27.0+cu130 runtime now passes imports, dependency consistency, a real CUDA kernel, and the first full document-model inference; it remains separate from the control plane.

## Verified current results

- Git remote exists and is reachable; work is on feature branch `codex/rebuild-bootstrap`.
- Hardware audit: RTX 5070 Ti 16,303 MiB, Ryzen 9 5950X, about 125.7 GiB RAM, Ubuntu 22.04, NVIDIA driver 595.80.
- Supplied schema contains 1,592 unique IDs: CDKT 77, KQKD 24, LCTT 107, TM 1,384. TM ID 1944 is absent and remains an append-only proposal.
- CPU environment is locked in `uv.lock`; bootstrap, atomic storage, source identity registry, role freezing, content-addressed materialization, render/preprocess, local difficult-region variants, perspective correction, ordered alignment, continuation graph, row wrapping, arithmetic validation, and workbook export have executable tests.
- Latest full test run before this entry: 79 passed in 34.31 seconds, including the hash-locked VPB native-geometry fixture, source-registry drift/idempotence, order-only cross-reader alignment, current-host GPU audit, control-plane backup boundary, and historical policy/extraction/constraint/verifier/CLI tests; Ruff lint passed.
- A real scanned/mixed ACB PDF page rendered and passed preprocessing checkpoint/hash verification.
- Relative word-gap segmentation, numeric right-edge clustering, note-axis separation, wrapped-row assembly, label-only section retention, and axis-local period/unit binding are implemented without institution/page coordinate rules.
- On the registered VPB logic-development fixture (pages 5–10), the native text path reconstructed 134 logical rows and 252 value cells, preserved 48 note references, and found two value axes on every page. It correctly separated snapshot dates from three-month durations, retained direct-LCTT anchors and section headings, and left one visible unlabeled off-balance total unresolved instead of inventing a label. See `docs/experiments/E-0006-vpb-native-geometry.json`.
- A local control-plane backup restored and hash-verified, but production backup is still FAIL because it is not off-machine.
- The isolated GPU environment contains 122 frozen distributions, occupies 5,663,276,925 bytes, and is reproducible from a complete freeze plus recorded critical wheel hashes. Ubuntu `libgl1` and `libglib2.0-0`, their observed dependency closure, cache variables, disk thresholds, and rebuild/rollback commands are versioned under `docs/environment/` and `config/system/`.
- Pinned PaddleOCR-VL-1.6 and PP-DocLayoutV3 weights were verified against their recorded sizes, revisions, and SHA-256 hashes. A revision-pinned downloader refuses mismatches; benchmark caches remain outside Git.
- E-0007 completed the full PP-DocLayoutV3 FP32 + PaddleOCR-VL-1.6 BF16 Transformers pipeline on VPB KQKD page 8 in 19.52 seconds with 3,239 MiB peak total GPU memory. Independent ordered alignment found 25/25 logical rows, 50/50 exact value/state cells, 12/12 exact note references, one two-row wrapped-label proposal, and only 23/25 source-exact labels. The two diacritic errors prove the VLM cannot be standalone truth even when numbers agree.
- Routine bootstrap audit now revalidates the isolated runtime on the current host: real CUDA/import smoke, `uv pip check`, tracked-freeze SHA-256, and exact installed-versus-tracked package sequence. Runtime acceptance is recorded separately from production model approval and fails closed on absence or drift.
- Post-install disk observation: the 40 GiB workspace filesystem holds about 17 GiB of source PDFs and 5.4 GiB of isolated runtime, leaving about 6.70 GiB free. Local control-plane backups total only about 2.9 MiB and explicitly exclude `.gpu-venv`, source PDFs, local Mongo data/tools, model caches, and generated output; a regression test protects that scope.
- The source inventory is currently stable at 2,567 PDFs and 17,761,344,114 bytes; later additions must trigger a new drift-aware registration rather than silently changing the denominator.
- `vst_level` contains four workbooks: balance sheet (77 populated IDs), income statement (24), direct cash flow (50 plus one title row without an ID), and detailed notes (1,384). IDs are unique within every file and all referenced parent IDs exist. The balance workbook contains 47 trailing blank rows; these must be ignored rather than interpreted as data. Cash-flow hierarchy coverage is direct-only and must not be treated as a complete LCTT hierarchy.
- LCTT ordered blocks/anchors and CDKT scope exclusions are loaded from versioned YAML. Missing policy fails closed; branch assignment follows workbook positions and the algorithm contains no bank/page/coordinate-specific branch list.
- Uploaded `financial_20_02_2022.gz` is a MongoDB gzip archive: 526,178,025 bytes, SHA-256 `0456df4aebb93b58c433b0d2a8c13bbb9402e1511d07758716976b94989204b9`, source server 7.0.28, Database Tools 100.14.0, database `financial_20_02_2022`.
- Official Database Tools dry-run found 25 namespaces. Only `financial_report_templates` was restored locally for the first audit: 1,851 documents total, 1,571 bank documents. `user` and `chat_sessions` are explicitly out of scope.
- ReportNormID 1944 has no collision in the 1,592 supplied schema IDs, 1,535 validated hierarchy records, 1,851 Mongo template documents, all raw/YTD keys in the 54 selected bank `data_chart` documents, or the 112,147-cell guarded DuckDB. This clears the ID-collision gate only; semantic name/parent and append authority remain separate gates.
- Local Mongo reference runtime is pinned to Database Tools 100.14.0 and patched server 7.0.34, loopback-only on port 27018. Versions, official URLs, archive hashes, setup scripts, and rebuild procedure are under `docs/environment/`.
- E-0008 rejected `report_yearly` (5,723 documents) and `report_quaterly` (2,581) as bank references because both cover 0/27 registered banks. Allowlisted `data_chart` covers all 27 banks with one annual and one quarterly document each. Its selected 54-document BSON hash is `fe07234c123a9bb80da414d0d98ec38f0b114b3784500cec053fcf239c9f13de`.
- The local historical DuckDB contains 112,147 weak-reference cells: 99,619 upstream numeric and 12,528 separately marked upstream-derived YTD cells, spanning 79 supplied ReportNormIDs. It preserves VALUE/ZERO/NAN and negative zero, records unit/scope UNKNOWN, accepts lookup only by resolved ID, and enforces zero rows allowed to map/promote PDF evidence.
- Transactional CSV bulk COPY wrote the 17,838,080-byte index in 1.84–3.54 seconds across accepted builds. Two Python row-wise attempts were intentionally discarded after exceeding 216 and 194 seconds; no incomplete file was published.
- E-0009 froze four calibration sources before content inspection: a TCB 2024 separate scan/searchable pair plus MBB and VCB 2025 consolidated scans. Ordered dynamic programming over pixel-only page fingerprints aligned 83 TCB pages, accepted 71, and accepted all six target main-statement pairs at similarity 0.834–0.948. The suite records stage-specific evidence permissions: Role B cannot read the searchable source/Role A answer, and historical values are forbidden until post-mapping validation of an already-resolved ID.

## Open constraints and next decisions

- Preserve the current stable corpus denominator and rerun drift-aware registration whenever new files arrive.
- Expand frozen native-geometry fixtures across institutions, years, scopes, scans, borderless layouts, broken pages, and multi-page rows before assigning production confidence.
- The user accepts VPS-local artifacts during development and requires periodic working Git commits. Local restore remains required; document the single-server-loss risk rather than silently claiming off-machine protection.
- Calibrate how historical discrepancies trigger targeted rereads/review on frozen fixtures without ever feeding history into candidate generation, PDF derivation, value overwrite, or confidence promotion.
- Broaden the now-working Blackwell model benchmark across institutions, years, scans, distortions, cross-page tables, and frozen holdout roles; E-0007 is logic-development evidence only.
- Capture matched scan/searchable PDF pairs as golden fixtures, then measure parser/OCR disagreement.
- Confirm the exact output-period expectations per template/run so PDF-only YTD-to-quarter derivation is applied only where required.

## Change log

- 2026-08-05: Created greenfield repository architecture, bootstrap documents, schema/source registries, atomic writes, local backup/restore verification, and fail-closed status contracts.
- 2026-08-05: Recorded actual schema counts and proposed missing TM 1944 without mutating the workbook.
- 2026-08-05: Added image quality, controlled variants, local dark-header crops, deskew/perspective handling, and real-PDF smoke run.
- 2026-08-05: Added ordered contextual alignment, user-confirmed LCTT branch anchors, CDKT off-balance exclusions, continuation graph, wrapped-row assembly, arithmetic validation, and template-preserving workbook export.
- 2026-08-05: Added dataset-role freeze, content-addressed immutable materialization for holdout/production, sequence phase decoder, and born-digital text evidence extraction.
- 2026-08-05: Configured LCTT ordered anchors and CDKT off-balance exclusions as versioned data with fail-closed loading; full suite reached 48 passing tests.
- 2026-08-05: Inventoried the newly populated `vst_level` hierarchy workbooks and recorded their partial/direct-only LCTT coverage.
- 2026-08-05: Registered and allowlist-audited the uploaded MongoDB archive; verified ReportNormID 1944 has no collision in schema, hierarchy, or Mongo template documents.
- 2026-08-05: Reopened the LCTT semantic decision after directly inspecting all 107 workbook rows; replaced numeric-range reasoning with contiguous workbook-order blocks.
- 2026-08-05: Added pinned MongoDB install/start/restore/audit scripts, server rebuild documentation, test strategy, experiment log, and paper-to-experiment research notes.
- 2026-08-05: Added relative word-run segmentation, value/note column inference, wrapped and section-row reconstruction, explicit snapshot/duration/YTD header binding, and a hash-locked six-page VPB integration fixture; suite reached 59 tests.
- 2026-08-05: Made source registration idempotent, preserved first-seen timestamps, and changed disappeared or content-mutated registered paths into hard audit conflicts; suite reached 62 tests.
- 2026-08-05: Built and froze the isolated Blackwell runtime, pinned exact model revisions/hashes, retained three failed PaddleOCR-VL bootstrap attempts, completed full inference, and added order-only cross-reader alignment that exposes wrapped rows and diacritic disagreements without using values to choose the path.
- 2026-08-05: Added current-host GPU runtime revalidation to bootstrap and separated runtime-mechanism acceptance from production model accuracy approval in machine-readable and Markdown audits.
- 2026-08-05: Verified the local backup did not cause the workspace capacity drop, documented current disk headroom, and added an allowlist-boundary regression preventing large local assets from entering routine control-plane backups.
- 2026-08-05: Rejected misleading non-bank historical collections, built the 27-bank E-0008 DuckDB weak-reference index from allowlisted `data_chart`, enforced resolved-ID-only/no-map/no-promote gates, extended the ID 1944 collision audit, and integrated current-host verification into bootstrap.
- 2026-08-05: Froze the first pre-inspection multi-document calibration suite, added value/text-independent scan/searchable page alignment and stage-level Role A/Role B evidence isolation, and captured the TCB CDKT/KQKD/off-balance/two-page-direct-LCTT block for independent OCR comparison.
