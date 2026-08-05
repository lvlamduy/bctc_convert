# Test and accuracy strategy

## Test layers

1. Pure unit tests cover text/number/date/unit parsing, atomic writes, evidence status gates, schema and hierarchy import, workbook-order cash-flow segmentation, row wrapping, cross-page continuation, period derivation, arithmetic, and export integrity.
2. Property and mutation tests will inject digit swaps, lost minus signs, dash/zero changes, duplicated labels, shuffled rows, moved columns, broken headers, and page-boundary splits. A mutation passes only when the system detects/downgrades it rather than accepting the wrong value.
3. Golden page tests retain PDF/image hash, expected word/cell boxes, row/column axes, labels, values, signs, units, periods, notes, and schema IDs. Searchable and scanned versions of the same filing are paired where available.
4. Document tests cover phase sequence, statement boundaries, direct/indirect method, separate/consolidated scope, cross-page tables, long wrapped labels, and exclusion of off-balance sections.
5. Frozen Role A holdout establishes the independent machine denominator. Role B is scored without seeing Role A artifacts.
6. Restore/replay tests rebuild from manifests, replay mapping/validation without OCR, export Excel atomically, reopen it, and verify sheet/schema order plus provenance links.

The first real-PDF geometry regression is `E-0006`: a registered, hash-locked VPB logic-development document covering CDKT, off-balance disclosures, KQKD, and direct LCTT across pages 5–10. The fixture asserts row/value/note counts, section boundaries, multiline labels, period/unit bindings, direct-method anchors, and fail-closed retention of an unlabeled numeric total. Because the PDF is an external source artifact, the integration test skips only when that exact file is absent; a hash mismatch fails rather than accepting a substitute.

`E-0007` is the first full GPU document-model cross-reader experiment. Ordered dynamic programming aligns native-PDF rows and VLM rows using only order and labels. It may propose two adjacent candidate rows as one logical wrapped row only when exactly one carries financial evidence. Numeric values and note references do not affect the alignment path; they are compared afterward. Diacritic-sensitive exact text and accent-stripped semantic keys are separate metrics, preventing normalization from hiding OCR spelling errors. Unit tests inject wrong values to prove they do not shift structural alignment and retain missing/extra rows explicitly.

`E-0008` selects and indexes the uploaded historical bank source. Tests reject non-bank documents, unknown period types, misaligned series lengths, unknown numeric keys, and policy changes that weaken safety gates. DuckDB constraints and routine verification require zero duplicate identities, zero ID 1944 rows, and zero rows permitted to map or promote PDF evidence. NAN, NULL, and negative zero have separate preservation checks. The source evaluator proves that generic `report_yearly`/`report_quaterly` have no registered banks and that allowlisted `data_chart` covers all 27 banks with annual and quarterly documents.

`E-0009` starts the frozen multi-document calibration layer. Four PDFs were assigned the immutable `CALIBRATION` role before content inspection: a TCB 2024 separate scan/searchable pair and image-heavy MBB/VCB 2025 consolidated filings. Page correspondence is inferred with ordered dynamic programming over Otsu-ink, low-resolution layout, and row/column projection fingerprints. It does not read text or numeric values. Low-similarity or ambiguous pairs remain explicit but cannot enter the benchmark. The first run paired all six TCB main-statement target pages, including the off-balance exclusion and two-page direct LCTT. Evidence-manifest tests prohibit Role B from reading Role A inputs/results and prohibit historical values during mapping; history is admitted only in post-mapping validation after a resolved ID.

The E-0010 runner seals Role B before comparison. Unit tests cover dirty-start rejection, overwrite refusal, and successful verification of render/result/metrics/package/model hashes. Reader-output tests preserve a VLM cell containing two visible numbers as `INVALID`, prove numeric disagreement cannot alter ordered alignment, and require all rows under an off-balance page heading to remain ineligible for CDKT. Ordered alignment can identify both a logical row split across two candidate rows (`MERGE_CANDIDATE`) and two reference rows collapsed into one candidate (`MERGE_REFERENCE`) using labels/order only. The latter is never numerically repaired; it enters table reconstruction review.

E-0010 reports coverage and agreement separately so missing/merged evidence cannot disappear from the denominator. On the six-page TCB calibration block, reference financial row/cell coverage is 94.70%; conditional agreement on aligned evidence is 96.80% rows and 97.60% cells, while strict whole-reference agreement is 91.67% rows and 92.42% cells. These are cross-reader machine-reference results, not human-gold, schema, full-tuple, holdout, or production accuracy. The integration test locks the exact metrics, algorithm/config hashes, zero confidence promotion, zero off-balance eligibility, direct-LCTT fail-closed semantic state, accepted page continuation, four row collapses, and the explicit multi-number-cell reason.

E-0011 is a targeted post-E-0010 failure analysis, not an untouched benchmark. A sealed PP-OCRv6 word-box reader reconstructs rows from relative period/note axes and downstream label attachment. Unit tests cover adjacent rows, wrapped labels, parent headings, multi-token invalid cells, trailing-context isolation, OCR dash-glyph normalization, visible-pixel dash recovery, and negative cases for white cells, vertical digits, and long table rules. The frozen integration result requires 140 one-to-one matches, 132/132 exact financial rows, 264/264 exact cells, 50/50 notes, zero invalid cells, zero off-balance eligibility, three pixel dashes, one glyph-normalized dash, fourteen preserved mapping-ineligible signature/footer lines, and one accepted LCTT continuation. Arithmetic contributes 11 validation passes and one explicit `NOT_TESTABLE`; it never supplies an operand for the dash. Automatic high confidence remains zero.

Role-specific label metrics are part of the gate interpretation: Role C has 3/140 source-exact labels and 14/140 semantic-key matches even though its geometry/value cells recover the targeted failures. Tests therefore prohibit treating the geometry reader as the label or schema authority.

## Distortion matrix

Each representative fixture is tested in original form and controlled variants: blur, low contrast, dark/colored header, uneven lighting, JPEG blocking, noise, rotation, skew, perspective/warp, crop loss, and small text. This follows the factor-wise idea of Real5-OmniDocBench but uses Vietnamese financial pages and exact cell truth.

## Required metrics

- Page/phase, table, row, column, and cell geometry accuracy.
- Exact numeric string/value, sign, VALUE/ZERO/BLANK/DASH state, unit, period, scope, note reference, and schema ID.
- Full-tuple exact accuracy and coverage by CDKT, KQKD, applicable LCTT branch, and each TM group.
- Cross-page continuation precision/recall; false merge rate is reported separately.
- Calibration: error rate by confidence bucket, selective accuracy versus review rate, and conformal/holdout coverage if adopted.
- Parser/OCR/model pairwise disagreement, reference-evidence coverage, conditional agreement, strict whole-reference agreement, escalation recovery rate, throughput, VRAM, and failure/hallucination rate.
- Source-exact label accuracy and semantic-key accuracy must be reported separately; semantic normalization can never count as exact OCR.

## Acceptance gates

- Values never select a schema candidate by themselves.
- A passing arithmetic identity cannot promote an otherwise incomplete evidence tuple.
- Missing geometry/config/period/unit/sign or unresolved semantic conflict fails closed.
- Derived quarter values retain both operands and formula and cannot be classified as directly observed/high confidence.
- Any regression that changes an accepted value, sign, period, scope, or ID must produce a reviewed diff before merge.
- A cross-reader match is corroboration, not ground truth. Correlated readers, shared rendering, or shared model weights must be disclosed.

## Experiment record

Every experiment is appended to `docs/experiments/EXPERIMENT_LOG.md` with hypothesis, code/config/model/data hashes, frozen fixtures, metrics, result, failure analysis, and decision. Cherry-picked examples or visual impressions are not acceptance evidence.

Historical experiment records are immutable. `E-0006` remains bound to geometry configuration v1 and its recorded algorithm hashes; a newer implementation cannot silently rewrite its expectations. When the exact historical implementation is not present, CI verifies source/config identity and skips replay rather than pretending the current code reproduced it. The same rule applies to E-0009 after later evidence stages extended its helper implementation. A versioned successor fixture must lock the current algorithm. E-0010 uses `config/tables/geometry-v2.yaml`; E-0011 separately locks `config/tables/word-box-reconstruction.yaml` and its current implementations.

Source-registry tests require byte-identical repeated registration, preservation of the original first-seen time, and hard failure when registered content changes in place or a registered path disappears. A routine audit may append new paths but may not silently rewrite existing source identity.

GPU-runtime audit tests are fail-closed: a current CUDA/import smoke, dependency compatibility, tracked freeze hash, and exact installed package sequence must all pass. Unit tests cover the configured-pass path, an absent manifest, and installed-freeze drift. Runtime acceptance and production model acceptance are deliberately separate states.

The PP-OCRv6 batch runner has a separate mechanism gate. Unit tests require
normalized sorted page selection; relocation only by exact hash; immutable role
agreement across request, preprocess manifest, and registry; a bound clean
preprocess envelope; rejection of render/config/runtime drift; full-identity
orphan-page recovery; and preservation of all model-load sessions across
resume. Sealing additionally locks both the batch orchestrator and its
single-page helper and rejects either hash drifting. A real development smoke
must reproduce a known OCR artifact byte for byte before the runner is used for
new evidence. This proves batch equivalence
and recovery behavior only; it does not add an accuracy sample.

Explicit page numbers in a golden/calibration fixture are expected test data, not production routing rules. Production page pairing must continue to use document-order and visual evidence; no bank, page offset, or coordinate constant may enter the algorithm.
