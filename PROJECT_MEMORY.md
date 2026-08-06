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
- On 2026-08-06 the user resolved `Q-BOOT-001`: the contiguous template-order block with endpoints 4155→4168 is INDIRECT and the block with endpoints 4104→4116 is DIRECT. These are endpoints in workbook order, not integer ranges; ID 4154 remains an interior DIRECT item. Current policy is `config/mapping/lctt-v2.yaml`; historical v1 artifacts remain unchanged for replay.
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

### 2026-08-06 — authoritative human review and schema order

- The reviewed CTG Q2/2026, ACB Q2/2026, and MBB Q1/2026 consolidated PDFs are frozen as hash-bound calibration. The decisions are authoritative only for those exact files/pages.
- CTG CDKT left/right columns are current 2026-06-30/comparative audited 2025-12-31 and this orientation continues across the same table even when a continuation page omits headers. MBB current is 2026-03-31; ACB current is 2026-06-30.
- A visible dash or verified empty numeric cell is zero while retaining its raw representation. An absent row is `NOT_OBSERVED` and must never be converted to zero.
- CTG external IDs 5701–5711 are visible off-balance rows and `OUT_OF_SCOPE_FOR_TARGET_TEMPLATE`; they are not CDKT additions or mapping failures. ID 5711 must not map to 4366.
- CTG 4337 is absent; the visible XDCB row maps once to 4373. CTG non-controlling interest maps once to 5699, not also to legacy 4306.
- Parent, neighbors, indentation, section, and physical/template position outrank names. MongoDB remains weak post-PDF evidence.
- ReportNormId magnitude is not order. Template workbook row order is authoritative because newly added indicators can receive a large ID and be inserted anywhere logically; the real sequence `4337 → 4373 → 4338` must remain intact.
- Paper research and custom local models are authorized, but adoption requires calibration, ablation, and bank/period-disjoint holdout evidence.

## General strategy

1. Register every input by SHA-256 and freeze dataset role before inspection.
2. Classify PDF pages with a sequence decoder, retaining UNKNOWN when text/OCR evidence is absent.
3. Render at controlled DPI; assess page and local regions; preserve the original and create only relevant provenance-bound variants with inverse geometry where applicable.
4. Run a document parser plus independent word/cell geometry OCR; escalate difficult crops to another model family.
   Keep language/context and geometry/value roles separate when their measured strengths differ.
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
- Latest full test run after the human-review/period/mapping v2 checkpoint: 202 passed and 2 immutable-historical replays skipped; Ruff lint and the changed-file formatter gate passed. E-0006 and E-0009 source/config identities remain verified, but exact replay is skipped when their historical algorithm byte hashes are not the current implementation. E-0010 through E-0015 provide current hash-locked integration regressions.
- A real scanned/mixed ACB PDF page rendered and passed preprocessing checkpoint/hash verification.
- Relative word-gap segmentation, numeric right-edge clustering, note-axis separation, wrapped-row assembly, label-only section retention, and axis-local period/unit binding are implemented without institution/page coordinate rules.
- On the registered VPB logic-development fixture (pages 5–10), the native text path reconstructed 134 logical rows and 252 value cells, preserved 48 note references, and found two value axes on every page. It correctly separated snapshot dates from three-month durations, retained direct-LCTT anchors and section headings, and left one visible unlabeled off-balance total unresolved instead of inventing a label. See `docs/experiments/E-0006-vpb-native-geometry.json`.
- A local control-plane backup restored and hash-verified, but production backup is still FAIL because it is not off-machine.
- The isolated GPU environment contains 125 frozen distributions, occupies 6,383,286,857 bytes, and is reproducible from a complete freeze plus recorded critical wheel hashes. Ubuntu `libgl1` and `libglib2.0-0`, their observed dependency closure, cache variables, disk thresholds, and rebuild/rollback commands are versioned under `docs/environment/` and `config/system/`.
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
- Geometry v2 separates adjacent independent financial tokens by a tracked text-height-relative gap, preserves tightly grouped digits, attaches short parenthetical wrapped labels, and trims trailing nonnumeric signatory material without hiding malformed digit-bearing cells. Historical geometry v1 remains byte-identical for E-0006; versioned results are never rewritten to fit current code.
- E-0010 independently sealed six searchable/scan TCB pages. Role B processed pages 10–15 sequentially in 101.791746 seconds at 3,243 MiB peak GPU memory; no new software/model was installed. Comparison against 140 native machine-reference rows found 139 candidate rows, 4 two-reference-row collapses, 1 wrapped candidate merge, 2 extra numeric rows, 1 explicit multi-number invalid cell, 3 numeric disagreements, and 1 note disagreement.
- E-0010 reference row/cell coverage is 94.70%. Conditional aligned-evidence agreement is 96.80% by financial row and 97.60% by cell; strict agreement including unaligned reference evidence is 91.67% by row and 92.42% by cell. These are calibration cross-reader metrics, not human-gold, schema/full-tuple, holdout, or production accuracy. All 20 off-balance candidate rows were excluded from CDKT, LCTT pages 14→15 passed continuation, history was not invoked, and automatic high-confidence count is zero.
- E-0011 independently sealed PP-OCRv6 word geometry for the same six TCB renders: 586 lines/4,024 word tokens in 191.635581 seconds on the official Paddle 3.3.0 CPU FP32 backend. Relative period/note axes and directional label attachment recovered all four page-14 collapsed pairs and separated page-15 `198.242` from `(5.140.484)` without splitting the VLM string.
- Against the same calibration machine reference, E-0011 has 140/140 one-to-one rows, 132/132 exact financial rows, 264/264 exact financial cells, 50/50 exact note references, zero invalid cells, zero off-balance CDKT-eligible rows, and one accepted page-14→15 continuation. Three omitted dashes are backed by recorded pixel components and one by the OCR glyph `一`; 14 signature/footer lines are retained as mapping-ineligible trailing context. Arithmetic produced 11 PASS, one dash-caused NOT_TESTABLE, and zero FAIL without generating values. Automatic high-confidence count remains zero.
- Role C's exact values do not make it a label reader: only 3/140 labels match source text exactly and 14/140 match the semantic key. The accepted architecture uses Role B for label/context proposals and Role C for geometry/value proposals. E-0011 is targeted post-failure calibration, not human gold, schema mapping, holdout, or production accuracy.
- A checkpointed PP-OCRv6 batch runner now loads the frozen detector/recognizer once per process and publishes one atomic page at a time. It rejects role relabeling, dirty upstream preprocessing, source/render/envelope drift, runtime/model/config/code drift, and mismatched orphan pages. Clean E-0012 commit `3291f9d` produced the same 50 lines/380 words and byte-identical OCR JSON SHA-256 `91779b3e22fadc01eeca7605c71a356e577e56541363ac91ea2750645721c54b` as the E-0011 page-15 single runner. No-op resume kept one model-load session and the batch/helper-aware seal passed. This is mechanism evidence on an already measured page, not a new accuracy sample.
- Statement-location v1 verifies every preprocess/batch/render/OCR identity before decoding a contiguous CDKT→KQKD→LCTT→TM block. It combines form/title/discriminator/numeric-density evidence, records all candidates and margins, forbids hidden interstitial pages, separates recognized forms from mapping-eligible scope, and keeps off-balance pages disconnected from main-CDKT continuation. Formal clean E-0013 on the first 18 PP-OCRv6 pages found MBB eligible CDKT 10–11, excluded page 12, KQKD 13, LCTT 14–15, TM boundary 16; VCB eligible CDKT 8–9, excluded page 10, KQKD 11–12, LCTT 13–14, TM boundary 15. Both had two candidates with margin 2.0 and returned DIRECT from a winning title plus globally ordered received/paid anchors, while schema branch assignment remained false. This locks calibration page/scope behavior only, not row/schema/numeric or production accuracy.
- Statement-location v1 installed no package, model, weight, driver, or system dependency. Exact algorithm, mapping strategy, tests, commands, transfer rules, and rebuild steps are tracked in `docs/STATEMENT_LOCATION_AND_MAPPING_STRATEGY.md` and `docs/environment/STATEMENT_LOCATION_RUNBOOK.md`.
- Routine bootstrap now verifies the tracked E-0013 header, clean-code claim, algorithm/config/runtime identities, exact MBB/VCB page/scope/method contracts, Q-BOOT-001 and no-promotion boundaries, and every locally present source/preprocess/batch/output hash. It exposes the result under `statement_location` in `BOOTSTRAP_MANIFEST.json`; missing external artifacts are distinguished from drift, while unsafe paths and present-but-mismatched files fail closed.
- Clean E-0014 commit `116c187` rerendered only the E-0013-selected MBB/VCB statement and off-balance boundary pages at 200 DPI. All 13 pages passed the quality gate as CLEAN with original renders selected, zero perspective candidates, and zero difficult regions. Four independent seals now bind Role B and Role C to the exact sources, renders, code, configs, runtime, weights, roles, and page sets.
- E-0014 Role B processed 13 pages in 306.225279 seconds at 3,241 MiB peak GPU memory. Role C processed 1,435 lines and 10,776 words in 510.263426 seconds on CPU FP32, loading its two models once per document. No package, model, driver, setting, ReportNormId, schema mapping, historical lookup, arithmetic repair, YTD derivation, or automatic confidence promotion was added or invoked.
- Reader completion is not row coverage: Role B reduced dense VCB CDKT continuation page 9 to seven generated table rows including the header after 91.814474 seconds and emitted unrelated non-Vietnamese margin text. VCB page 10 has a heading-only table before its body, and VCB tables can begin with `STT` before label/note/value columns; MBB page 10 also shows serialized column shifts. These retained failures require a general all-table-block parser and independent Role C row/axis reconstruction before comparison.
- Structural reader fusion v2 is implemented as new versioned modules so E-0010/E-0011 byte identities remain untouched. Role B retains every HTML table block, expands spans, infers optional index/label/note/value roles, consumes header-only inheritance once, and rejects concatenated grouped values. It deliberately leaves VCB page 9 unresolved because only one period header and a truncated body survive. Role C accepts worded period headers, chooses compact period-axis pairs over metadata dates, separates repeated row codes and alphanumeric notes, anchors OCR-blank rows structurally, and quarantines right-margin numeric noise. The order-only fusion applies upstream page scope first and never uses values/notes to select alignment.
- Page boundaries are hard separators in fusion v2. Same-statement continuation edges preserve the last/first evidence from both readers, but do not automatically merge rows; this prevents an entirely truncated next page from pulling its first heading into the previous page's final total.
- Formal E-0015 from clean commit `94a2c7c` retained all 14 Role B blocks and two Role C axes on all 13 pages. It compared 244 Role B and 288 Role C rows with 235 matches, five structural merges, one Role C-missing row, and 46 Role B-missing/truncated rows. Of 454 paired observed cells, 432 agree (95.154185% conditional agreement); bilateral financial-row structural coverage is 99.565217% for Role B and 83.636364% for Role C. These are cross-reader calibration metrics, not accuracy.
- E-0015 retains eight Role B invalid cells, zero Role C invalid cells, ten source-pixel dash recoveries, three unassigned margin-number lines, 86/94 exact notes, and 97/104 exact row codes. Only 7/240 paired labels are source-exact and 50/240 semantic-key exact, so Role C remains geometry/value evidence only. Both off-balance pages have zero mapping-eligible units; five continuation edges preserve boundaries with automatic row merge false.

## Open constraints and next decisions

- Preserve the current stable corpus denominator and rerun drift-aware registration whenever new files arrive.
- Expand frozen native-geometry fixtures across institutions, years, scopes, scans, borderless layouts, broken pages, and multi-page rows before assigning production confidence.
- The user accepts VPS-local artifacts during development and requires periodic working Git commits. Local restore remains required; document the single-server-loss risk rather than silently claiming off-machine protection.
- Calibrate how historical discrepancies trigger targeted rereads/review on frozen fixtures without ever feeding history into candidate generation, PDF derivation, value overwrite, or confidence promotion.
- Broaden the now-working Blackwell model benchmark across institutions, years, scans, distortions, cross-page tables, and frozen holdout roles; E-0007 is logic-development evidence only.
- Target E-0015's explicit escalations at native source resolution: VCB page 9 truncation, MBB page 14 concatenation, two Role B collapses on MBB CDKT, the MBB KQKD missing/collapse cases, eight invalid cells, six numeric disagreements, four invalid-cell paired escalations, and five structural merges. Canonical fusion must remain general and must not repair from history/arithmetic.
- Apply the clean E-0013 eligible-page contracts and off-balance exclusions before row mapping. The E-0014 pages and reader outputs are calibration evidence, not row-level truth; follow with controlled distortions and an untouched holdout.
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
- 2026-08-05: Ran and sealed the six-page E-0010 TCB cross-reader calibration, added geometry v2 for close financial columns and parenthetical wraps, detected bidirectional row splits/collapses without values, separated strict coverage from conditional agreement, preserved multi-number cells as invalid, and locked the result with a portable replay runbook and integration test.
- 2026-08-05: Added the sealed E-0011 PP-OCRv6 word-box role, relative row/axis reconstruction, trailing-context isolation, visible dash-component recovery with negative tests, configured cross-page arithmetic checks, a targeted 140-row/264-cell result, and a migration-safe replay/decision record. No schema ID, historical value, YTD value, or confidence status was generated.
- 2026-08-05: Added immutable-role/hash-gated multi-page PP-OCRv6 execution with atomic per-page checkpoints, exact resume/orphan recovery, a server-transfer runbook, and mechanism tests; no dependency or model changed.
- 2026-08-05: Ran clean E-0012 batch equivalence on TCB page 15, verified byte-identical OCR, no model reload on resume, and batch/helper-aware sealing; retained the result as mechanism-only evidence.
- 2026-08-05: Integrated E-0012 into bootstrap so routine audits re-hash its algorithms, runtime/config, and every locally present batch/checkpoint/seal artifact and expose the mechanism status in recovery/progress reports.
- 2026-08-06: Added evidence-chain-verified, order-constrained statement location; numeric/discriminator gates for OCR title false positives; explicit off-balance scope separation; competitive direct/indirect method evidence; MBB/VCB development smoke; rebuild/mapping strategy documentation; and 16 new fail-closed tests without adding software or models.
- 2026-08-06: Reran the unchanged locator from clean commit `b165c60`, hash-locked the MBB/VCB results as E-0013, added an exact replay contract and integration regression, and retained the page-level/calibration-only claim boundary.
- 2026-08-06: Added automatic bootstrap/recovery verification for E-0013, including exact local artifact checks and a tamper regression that rejects a hash-updated but contract-drifted location output.
- 2026-08-06: Rerendered the selected MBB/VCB blocks at 200 DPI, quality-gated 13 clean pages, independently ran and sealed Role B/Role C, retained generative truncation/multi-table/column-shift failures, and locked the acquisition as E-0014 without mapping or accuracy claims.
- 2026-08-06: Added structural fusion v2 with all-block/span-aware variable-column parsing, worded-period and geometry-derived index/note/value reconstruction, strict grouped-number and margin-noise gates, upstream scope exclusion, order-only comparison, and focused regressions; no dependency/model/ReportNormId changed.
- 2026-08-06: Ran clean E-0015 on the four E-0014 seals, hash-locked 13-page structural/conditional-agreement evidence, retained one unresolved table and all missing/collapse/invalid/noise outcomes, prohibited automatic cross-page row merges, and added exact replay/integration gates without schema or confidence promotion.
- 2026-08-06: Resolved Q-BOOT-001 by contiguous template order: 4155→4168 is INDIRECT and 4104→4116 is DIRECT; current policy v2 applies only after an independently resolved PDF method, while historical artifacts remain immutable.
- 2026-08-06: Added targeted reread v1: relative failure localization, source-PDF 450/600-DPI rerendering, quality-gated photometric/deskew/perspective/dark-region candidates, inverse geometry, complete evidence-chain checks, and an exact E-0016 13-page/8-region calibration contract with no value selection.
- 2026-08-06: Added the 3-document/30-decision human-review registry, exact PDF/schema/role audit, table-level period propagation v1, raw-versus-normalized value statuses, hierarchy-first structural ranking v2, template-display-order/one-to-one sequence gates, reviewed digit corrections, and external-ID collision tests. No package, model, or ReportNormId was added.
- 2026-08-06: Added the E-0016 original-crop evidence sealer and fail-closed tests. It verifies the complete targeted input/runtime/reader chain, compares only header-bearing full-table crops, preserves headerless and malformed-table outcomes, rejects extra/missing variant reads, and keeps all selection/value/schema/confidence permissions false. No package or model was added; a clean formal evidence run remains the next gate.
