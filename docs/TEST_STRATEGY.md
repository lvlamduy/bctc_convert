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

## Distortion matrix

Each representative fixture is tested in original form and controlled variants: blur, low contrast, dark/colored header, uneven lighting, JPEG blocking, noise, rotation, skew, perspective/warp, crop loss, and small text. This follows the factor-wise idea of Real5-OmniDocBench but uses Vietnamese financial pages and exact cell truth.

## Required metrics

- Page/phase, table, row, column, and cell geometry accuracy.
- Exact numeric string/value, sign, VALUE/ZERO/BLANK/DASH state, unit, period, scope, note reference, and schema ID.
- Full-tuple exact accuracy and coverage by CDKT, KQKD, applicable LCTT branch, and each TM group.
- Cross-page continuation precision/recall; false merge rate is reported separately.
- Calibration: error rate by confidence bucket, selective accuracy versus review rate, and conformal/holdout coverage if adopted.
- Parser/OCR/model pairwise disagreement, escalation recovery rate, throughput, VRAM, and failure/hallucination rate.
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

Any edit to a geometry algorithm or its threshold file invalidates the recorded implementation/config hash in `E-0006` and requires an explicit fixture rerun and reviewed expectation update.

Source-registry tests require byte-identical repeated registration, preservation of the original first-seen time, and hard failure when registered content changes in place or a registered path disappears. A routine audit may append new paths but may not silently rewrite existing source identity.

GPU-runtime audit tests are fail-closed: a current CUDA/import smoke, dependency compatibility, tracked freeze hash, and exact installed package sequence must all pass. Unit tests cover the configured-pass path, an absent manifest, and installed-freeze drift. Runtime acceptance and production model acceptance are deliberately separate states.
