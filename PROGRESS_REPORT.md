# Progress report

- Updated: 2026-08-06T06:16:00+00:00
- Branch: `codex/rebuild-bootstrap`
- Latest clean, tested, pushed checkpoint: `4a469fab2334e479ebd5117a4e130986e36cb6c9`
- Hardware: NVIDIA GeForce RTX 5070 Ti (16,303 MiB, compute capability 12.0); 125.71 GiB RAM
- Runtime state: `LOGIC_DEVELOPMENT_INFERENCE_PASS_NOT_PRODUCTION_APPROVED`
- Registered schema rows: 1,593 (CDKT 77; KQKD 24; LCTT 107; TM 1,385)
- Registered PDFs: 2,567
- Latest full regression: 229 passed, 2 intentionally skipped historical replays; Ruff and `git diff --check` passed

## Accuracy focus and measurable state

- Main measured error class: `STRUCTURAL_ROW_CELL_RECONSTRUCTION`. Replaying
  the E-0010 Role A/Role B baseline with the new common taxonomy gives 21 direct
  impact units: 7 non-`MATCH` alignment units plus 14 missing reference cells.
  The other measured classes are 6 aligned numeric/sign disagreements, 4
  semantic-label disagreements, and 1 note-reference disagreement.
- Baseline before the current change remains E-0010: 140 Role A rows versus 139
  Role B rows; financial-row/cell coverage 94.70%; conditional exact row/cell
  agreement 96.80%/97.60%; strict exact row/cell agreement 91.67%/92.42%.
- Current logic being improved: replace a generative table's row grid with an
  independently reconstructed geometry grid, retain the semantic reader for
  labels/context, inherit verified period axes across continuation pages, and
  send unresolved merges or multi-number cells to localized rereading.
- Measurable after-result: pending the clean E-0017 acquisition and comparison;
  no improvement is claimed from parser refactoring alone. The v2 parser replay
  on E-0010 is deliberately byte-for-metric identical to the existing baseline.
- Next bounded action: run the newly frozen six-page TCB 2024 consolidated pair,
  build its native Role A reference, seal image-only Role B output, and publish
  row/cell coverage plus the same error taxonomy before changing fusion logic.

## Completed tasks

- Built reproducible bootstrap, GPU runtime, package/model hashes, source registry,
  dataset-role registry, backup/restore checks, and server rebuild documentation.
- Restored and audited `financial_20_02_2022.gz` as a read-only MongoDB historical
  weak reference: 112,147 cells across 27 banks. History is never permitted to
  override visible PDF evidence, table periods, hierarchy, or scope.
- Preserved all supplied template workbooks and built a schema graph. A
  `ReportNormId` is an identity only: ordering is always the row/display order in
  the relevant workbook. Numeric magnitude or numeric sorting is prohibited.
- Resolved Q-BOOT-001 by workbook position: template-order block 4155→4168 is
  INDIRECT and 4104→4116 is DIRECT. These are not numeric ranges.
- Implemented ordered statement location, off-balance-sheet exclusion,
  continuation boundaries, two-reader structural comparison, independent word-box
  geometry, strict financial-cell parsing, visible-dash recovery, and targeted
  source-PDF rereading at 450/600 DPI.
- Completed and hash-locked E-0010 through E-0015 calibration regressions. E-0015
  keeps page boundaries hard, excludes the two off-balance pages, and retains all
  reader disagreements instead of converting agreement into truth.
- Ingested the authoritative 2026-08-06 CTG/ACB/MBB human review as a hash-bound
  30-decision calibration registry. Added table-level period propagation,
  `OBSERVED_VALUE`/`OBSERVED_ZERO`/`NOT_OBSERVED`/scope/ambiguity statuses,
  raw-plus-normalized values, hierarchy-first mapping, and display-order sequence
  validation.
- Verified that external off-balance IDs 5701–5711 do not collide with or belong
  to the current target balance-sheet templates. ID 4337 is `NOT_OBSERVED` in the
  cited CTG section; the visible XDCB row maps only to 4373.
- Committed and pushed the latest correctness checkpoint as
  `8c2f7fb feat: seal targeted reread reader evidence`.
- Generated the formal E-0016 artifact from clean commit `8c2f7fb`. It verifies
  15/15 original-crop reader runs and a 52-file output set while retaining one
  unresolved table, one no-table crop, 14 invalid VLM cells, both full-table row
  count disagreements, and all no-selection/no-mapping safety flags.
- Committed and pushed the E-0016 replay/integration checkpoint as `70fefa9`;
  the full suite is 208 passed with 2 intentionally skipped historical replays.
- Reviewed DeepSeek-OCR-2, Microsoft TATR, IBM TableFormer, and ClusterTabNet
  against official papers/repositories, exact available weights, licenses,
  runtime compatibility, and the observed E-0016 failures. Selected TATR as the
  first structure-only addition and DeepSeek-OCR-2 as the next isolated semantic
  reader benchmark; TableFormer is the challenger and archived ClusterTabNet is
  a custom-graph research reference.
- Added a hash-pinned TATR downloader, no-network/clean-Git structure runner,
  all-query/source-box evidence representation, candidate-policy configuration,
  and 8 focused passing unit tests. The full regression is 216 passed with 2
  intentional historical skips. The mechanism commit itself preceded the model
  download so its source/config state remained independently reviewable.
- Downloaded and independently verified the 115,514,291 required TATR artifact
  bytes in the ephemeral model cache. The first clean load attempt stopped
  before inference because Transformers 5.14.1 rejects the checkpoint's legacy
  `dilation=null`; no partial result directory was published.
- The corrected dirty development smoke now completes actual GPU inference in
  0.187929 seconds with 249.096680 MiB peak allocated VRAM. It retains all 125
  queries and reports 36/30/23 row boxes at thresholds 0.5/0.7/0.9; no threshold
  is selected from these counts. This is mechanism evidence, not a formal run.
- Committed and pushed the exact-version TATR compatibility checkpoint as
  `8dd5422`; Ruff and all 216 tests passed with two intentional historical skips.
- Validated the user-supplied `s3://test-s3-duylv/` target through the existing
  `bctc-backup` AWS profile. It is in `us-east-1`, defaults to AES-256 server-side
  encryption, and blocks all public access.
- Q-BOOT-005 was approved. Enabled bucket versioning and verified `Enabled`;
  default AES-256 encryption and all four public-access blocks remain active.
  Object Lock was not enabled and the bucket reports no Object Lock configuration.
- Inventoried the off-machine snapshot scope: 2,567 registered PDFs plus source
  acquisition metadata, all generated output, the 526,178,025-byte Mongo dump,
  the 17,838,080-byte accepted DuckDB, a control-plane archive, and a Git bundle.
  The initial content-addressed snapshot will contain about 18.6 GB before
  content deduplication.
- Committed and pushed the S3 snapshot/offload/hydration mechanism as `3e07735`.
  Its regression passed 222 tests with two intentional historical skips; it
  rejects unversioned buckets and keeps offload dry-run by default.
- Q-BOOT-004 is implemented. Appended TM ReportNormID `1944 — Cho vay giao
  dịch ký quỹ và ứng trước tiền bán chứng khoán` as the final workbook-order
  row after 1943. The source workbook changed from SHA-256
  `6af23d7bf930fe6db7cbfb83df78c7c7ab876142757d1dde5707c1667b54a8a0`
  to `fa284e3af1f90c8a206308f63e6d35e77a9fbf1abcaf60abcb59877c47275140`.
- The append audit proves all 1,384 existing TM ID/name/order mappings are
  byte-semantically unchanged. Only `xl/worksheets/sheet1.xml` and
  `xl/sharedStrings.xml` changed; all eight other XLSX members retain their
  original SHA-256. No `vst_level` hierarchy workbook was modified and no
  unsupported parent was inferred for 1944.
- Added a schema-coverage contract derived from workbook display order. Role A,
  Role B, Excel output, evaluation, and mandatory search each contain all 1,593
  IDs and end with TM 1944. Mandatory search fails unless both roles record
  exactly one terminal outcome for every template ID; `NOT_OBSERVED` remains
  distinct from zero.
- Rebuilt the historical weak-reference registry against the 1,593-item graph.
  Its 112,147 cells remain unchanged in authority and contain zero historical
  rows for 1944; all no-map/no-promote gates and the current graph hash verify.
- The complete Q-BOOT-004 regression passed: 226 tests, two intentional
  immutable-historical replay skips, Ruff clean, and `git diff --check` clean.
- Committed and pushed the append-only schema checkpoint as `4a469fa`; TM 1944
  is present in Role A, Role B, Excel output, evaluation, and mandatory search.
- Selected the next Role A/Role B expansion strictly from filename metadata
  before content inspection and froze both TCB 2024 consolidated documents as
  `CALIBRATION`. The searchable file is a 90-page native-text Role A source and
  the scan is a 93-page image-only Role B source.
- Pixel-only ordered pairing accepted 76 page pairs and all six target contracts:
  Role A pages 8–13 correspond to Role B pages 9–14 and cover CDKT, the excluded
  off-balance page, KQKD, and a two-page direct LCTT continuation.
- Added reusable, experiment-independent Role A construction, Role A/Role B
  comparison, strict parser-v2 table handling, metric aggregation, and a direct
  impact error taxonomy. A focused 17-test regression passed; the pairing gate
  reports `PASS_FROZEN_PAIRING_FOUND` with 0 missing target pages. The full
  regression is 229 passed with 2 intentional immutable-history skips.

## Currently in progress

- Preparing a clean checkpoint for the reusable Role A/Role B evaluator and
  E-0017 frozen pair, then acquiring the six Role B pages and measuring the new
  cross-reader baseline.
- The already-started S3 snapshot has uploaded and HEAD-verified all 4,192 unique
  objects and is performing the required full sequential content restore.
  No local deletion has started; this background safety gate is not delaying
  the accuracy work.

## Major challenges and obstacles

- A higher-resolution crop is not sufficient by itself. On MBB LCTT page 14,
  PaddleOCR-VL still concatenates rows and numeric cells at 450 DPI; its current
  HTML proposal has 18 rows and 14 invalid multi-number cells, while independent
  PP-OCRv6 geometry proposes 27 rows with zero invalid cells.
- Headerless row-band crops cannot safely infer period axes independently. They
  must inherit a previously verified table-level period map and remain in review
  when the crop lacks that context.
- One MBB row-band crop was classified as text/image rather than a table, and one
  other row-band table still has unresolved column roles. These failures are being
  preserved as explicit evidence, not hidden or repaired from history.
- There is still no human-gold, bank-disjoint and period-disjoint end-to-end
  benchmark large enough to support a production accuracy threshold.
- The S3 bucket is reachable, encrypted, publicly blocked, and versioned. The
  remaining backup obstacle is operational: complete the ~18.6 GB upload and a
  full sequential content restore before any local source is removed. Object
  Lock is deliberately disabled per user instruction.

## Current strategy

1. Treat the visible PDF and inherited table structure as source authority.
2. Locate statement/table/page scope before row mapping; exclude off-balance
   sections before candidate generation.
3. Reconstruct logical rows across wrapped text and page continuations while
   retaining hard page-boundary provenance.
4. Rank schema candidates lexicographically by statement/table context, parent,
   previous/next template rows, indentation/numbering, then normalized label.
   Same-bank and cross-bank history are lower-priority weak evidence only.
5. Validate period bindings, raw/normalized numeric semantics, signs, horizontal
   and vertical arithmetic, parent-child totals, and template display order.
6. Escalate only localized failures to high-resolution rereads and independent
   readers. Reader agreement is supporting evidence, never automatic truth.
7. Fuse specialized readers by role only when they improve the end-to-end frozen
   baseline: a structure reader proposes table geometry, PP-OCRv6 proposes
   word/cell pixels, and a semantic reader proposes labels/context. None can
   independently map IDs or establish numeric truth.
8. Develop custom learned components only behind frozen baselines: graph-based
   row/cell relation modeling, Vietnamese label encoders trained with
   same-label/different-parent hard negatives, specialized digit/sign recognition,
   and conditional dewarping. Evaluate on bank- and period-disjoint holdouts.
9. Keep model experiments bounded to a specific observed pipeline failure; do
   not accumulate reader benchmarks without a measurable extraction objective.
10. Protect large inputs with immutable S3 content keys and a manifest-first
   restore contract. Reclaim local space only after remote HEAD/checksum,
   manifest validation, and a real full-content sequential restore pass; hydrate
   exact logical paths without overwriting a mismatched local file.

## Planned next steps

1. Commit and push the reusable Role A/Role B evaluator and frozen E-0017 pair.
2. Build E-0017 Role A, run and seal Role B on its six scan pages, then publish
   coverage, strict/conditional agreement, and the main error class.
3. Use the E-0017 failures plus the existing E-0010 failures to implement one
   bounded canonical-row-grid change, then rerun both baselines for before/after.
4. Finish the full-content restore-test of the immutable snapshot, then offload the 2,567
   registered PDFs and Mongo dump to reclaim about 18.3 GB. Preserve the local
   eviction journal and remote record; do not delete output/runtime/tool assets.
5. Record remote object/version/checksum, manifest, restore and disk-reclamation
   evidence in this report; mark Q-BOOT-003 resolved only after all gates pass.
6. Expand Role A next to a different bank and period after E-0017, using the
   same pre-inspection role freeze and common metrics rather than a new one-off
   experiment script.
6. Build an isolated Blackwell-compatible DeepSeek-OCR-2 benchmark without
   modifying the approved base runtime, then score Vietnamese labels and exact
   digits/signs against the same source-bound crops.
7. Build a human-gold evaluation split separated by bank and reporting period,
   including skew, warp, dark headers, blurred digits, wrapped rows, continuation
   pages, direct/indirect LCTT, separate/consolidated scope, and quarterly/YTD
   derivation cases.
8. Define calibrated abstention thresholds only after the human-gold benchmark;
   unresolved evidence must continue to produce review statuses rather than
   guessed output.

## Questions requiring user feedback

- Q-BOOT-004 and Q-BOOT-005 are resolved. No open question currently requires
  user feedback.
