# Progress report

- Updated: 2026-08-06T07:38:01+00:00
- Branch: `codex/rebuild-bootstrap`
- Latest pushed algorithm checkpoint: `6caafad`; E-0019 clean evaluation base: `1a23b7b437e7d95a652c69e8748a037ad6d2224a`
- Hardware: NVIDIA GeForce RTX 5070 Ti (16,303 MiB, compute capability 12.0); 125.71 GiB RAM
- Runtime state: `LOGIC_DEVELOPMENT_INFERENCE_PASS_NOT_PRODUCTION_APPROVED`
- Registered schema rows: 1,593 (CDKT 77; KQKD 24; LCTT 107; TM 1,385)
- Registered PDFs: 2,567
- Latest full regression: 246 passed, 2 intentionally skipped historical replays; Ruff and `git diff --check` passed

## Accuracy focus and measurable state

- Main measured error class: `STRUCTURAL_ROW_CELL_RECONSTRUCTION`. E-0017 adds
  42 direct impact units: 7 non-`MATCH` alignment units, 14 missing reference
  cells, and 21 structurally damaged compared cells. Twelve of those cells
  contain multiple financial numbers collapsed into one generated cell. Only 2
  disagreements remain attributable to numeric/sign OCR itself; label and note
  disagreements contribute 3 and 1 units respectively.
- Baseline before the current change remains E-0010: 140 Role A rows versus 139
  Role B rows; financial-row/cell coverage 94.70%; conditional exact row/cell
  agreement 96.80%/97.60%; strict exact row/cell agreement 91.67%/92.42%.
- Current logic being improved: replace a generative table's row grid with an
  independently reconstructed geometry grid, retain the semantic reader for
  labels/context, inherit verified period axes across continuation pages, and
  send unresolved merges or multi-number cells to localized rereading.
- New before-result from E-0017: 147 Role A versus 146 Role B rows; row/cell
  coverage 94.964%; conditional exact row/cell agreement 90.9091%/91.2879%;
  strict exact row/cell agreement 86.3309%/86.6906%. The first four pages have
  206/206 exact financial cells; all material loss is localized to the first
  dense LCTT page; these figures remain the frozen whole-suite before-result.
- New bounded after-result from E-0018 on that predeclared dense LCTT page:
  DeepSeek-OCR-2 plus one explicit adjacent label-only/value-only fragment merge
  reconstructs 33/33 rows, covers 58/58 financial cells, and exactly agrees
  with all 58/58 machine-reference numeric/sign cells. Strict exact cell
  agreement rises from 36.2069% to 100%; strict exact financial-row agreement
  rises from 34.4828% to 100%; invalid cells fall from 12 to zero, and measured
  structural impact falls from 41 to zero. This is target-page calibration
  against a native machine reference, not human-gold or end-to-end accuracy.
- New formal E-0019 result for fixed-grid fusion on E-0017 pages 13→14:
  independent PP-OCRv6 reconstructs 41/41 Role A rows and exactly agrees on
  72/72 financial cells with zero invalid cells. DeepSeek proposes 42 semantic
  rows because one wrapped label on page 14 is split and the next value is
  shifted upward. A fail-closed dynamic program now resolves the verified
  3-semantic-row→2-geometry-row pattern to 41 canonical rows. All final cells,
  notes, geometry source IDs and row count remain object-identical to PP-OCR;
  DeepSeek supplies only Vietnamese labels and reading-order evidence. This is
  still calibration against machine Role A, not human gold. Across both pages,
  financial row/cell coverage improves from 80.5556%/80.5556% to 100%/100%,
  strict exact row/cell agreement improves from 47.2222%/48.6111% to 100%/100%,
  invalid cells fall from 12 to zero, and structural impact falls from 42 to
  zero. The remaining main class is one Vietnamese label disagreement.
- Next bounded action: seal the two-page fusion as E-0019, measure its semantic
  label and direct-LCTT recovery against frozen Role A, then apply the same
  algorithm to the existing E-0010 structural failures.

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
- Completed and sealed E-0017 Role A and Role B at clean commit `932a481`.
  Role B processed six image-only pages sequentially in 109.336706 seconds at
  3,243 MiB peak GPU memory. The formal comparison is tied to clean correction
  commit `a7306c9`, where multi-number cells are attributed to their structural
  root cause instead of double-counted as digit OCR failures.
- E-0017 keeps all 20 off-balance rows outside target CDKT, accepts the LCTT
  page-13→14 continuation from adjacency/header/axis/unit/period/section evidence,
  and returns cash-flow method `UNKNOWN` because row collapse destroys the
  required ordered direct anchors. It does not guess the method from ID values.
- At model-download preflight, persistent workspace free space was
  5,367,824,384 bytes, which was insufficient
  for the 6,789,163,745-byte pinned DeepSeek-OCR-2 artifact set. `/dev/shm` has
  15,407,611,904 bytes free, so an ephemeral, hash-verified model load is viable
  while retaining a 4 GiB safety reserve. The official 3B BF16 revision and all
  required file hashes are now pinned; the model has no mapping/value/period/
  scope/confidence authority and may run only on failed or ambiguous regions.
- Downloaded and independently verified all 14 pinned DeepSeek-OCR-2 artifacts
  (6,789,163,745 required bytes) into `/dev/shm`; the weight SHA-256 is
  `d8ff67a424ba6f4dd077885eb9d6a05d2537e76fe5491f0e2a9b712f8c8870fa`.
  No source PDF or Mongo dump was deleted. Persistent free space is currently
  4,931,727,360 bytes and `/dev/shm` free space is 8,481,501,184 bytes.
- Confirmed the expected runtime incompatibility instead of hiding it:
  Transformers 5.14.1 cannot import the official custom model because it no
  longer exports `LlamaFlashAttention2`. A hash-locked, external overlay using
  the official Transformers 4.46.3/tokenizers 0.20.3 pair plus
  huggingface-hub 0.26.3 now loads the unchanged model with eager attention on
  the existing Torch 2.12/CUDA 13 Blackwell runtime. The successful load took
  4.255978 seconds, allocated 6,883,116,544 GPU bytes, and left 9,389,604,864
  GPU bytes free; no FlashAttention or base-runtime downgrade was used.
- Added a targeted DeepSeek runner and 11-package hash-locked overlay contract.
  It verifies a clean Git state, every model file, exact package versions, BF16
  and GPU capability, and denies DNS/socket access during inference. Its output
  is explicitly non-authoritative for geometry, values, periods, scope,
  confidence and schema mapping. Six focused downloader/runner tests pass.
- Completed the clean E-0018 inference on the E-0017 page-13 image in 32.836091
  seconds. Peak allocated/reserved VRAM was 8,189,789,184/9,137,291,264 bytes.
  The reader emitted a 35-row span-aware raw HTML grid; the canonicalizer joined
  exactly one adjacent label-only row with its immediately following value-only
  row, retained both source-row IDs, and did not alter either financial cell.
- The ordered direct cash-flow anchors are now observed at candidate positions
  1 and 2, changing the targeted reader proposal from `UNKNOWN` to `DIRECT`.
  The acceptance gate remains fail-closed: semantic high confidence is false,
  and there is no automatic value, period, scope, geometry, confidence or
  ReportNormId authority. One `cố tức`/`cổ tức` Vietnamese label disagreement
  and one note-placement disagreement remain for review.
- Ran a clean, hash-manifested PP-OCRv6 word-box batch for E-0017 scan pages
  13–14: 170 lines and 1,509 words in 56.570324 seconds. The v2 geometry parser
  recovers 33+8 canonical rows, 58+14 exact numeric/sign cells, zero invalid
  cells, and the visible 2024/2023 axes on both pages.
- Added `FIXED_GEOMETRY_GRID_SEMANTIC_LABEL_FUSION_V1`. Its dynamic program
  supports ordinary one-to-one label binding plus one explicit overflow repair:
  two consecutive semantic numeric fingerprints must exactly match two geometry
  rows, the third semantic row must have a label but blank cells, and the repaired
  Vietnamese-label score must improve by at least a configured margin. It
  abstains when row loss, fingerprint disagreement, weak similarity or ambiguous
  paths remain. Four focused tests and the full 246-test regression pass.
- Completed formal E-0019 from clean commit `1a23b7b`. It binds the two clean
  DeepSeek runs and the 170-line/1,509-word PP-OCRv6 batch by SHA-256, preserves
  41/41 geometry cell tuples, verifies 41/41 supporting semantic numeric
  fingerprints, performs one 3→2 overflow repair, and recovers the configured
  DIRECT cash-flow anchors at positions 1 and 2. Confidence, periods, scope,
  schema mapping and ReportNormId authority all remain disabled.
- Completed the immutable S3 snapshot and real restore gate. Snapshot
  `20260806T050030130746Z-4a469fab2334` contains 4,361 logical files,
  4,192 unique objects and 18,388,413,612 unique bytes. Upload and 4,192 HEAD
  checks passed; the downloaded manifest, control plane, Git bundle, sample PDF,
  all seven asset classes and a full 4,184-content-object sequential restore
  passed. The run record is SHA-256
  `24eb066b51443066dfd14538ef7aeb21e9b700cc6ce995c49e56ff23b6701b04`;
  the manifest is SHA-256
  `74be9ea09905f0c7842d5a0b46bfe44f3fc5f32cc2c15b5040efcc4e99e8981b`.
  A final live check confirms bucket versioning `Enabled`, AES-256 default
  encryption, all public-access blocks enabled, and versioned encrypted manifest
  and run-record objects. Object Lock remains disabled.

## Currently in progress

- Applying the sealed fixed-grid fusion to the existing E-0010 failures to test
  whether the improvement generalizes beyond the selected TCB pages.
- Preparing the verified local offload of only `source_pdf` and `mongodb_dump`
  assets. No local source has yet been removed; the immutable manifest, remote
  object catalog and real restore prerequisites now all pass.

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
- DeepSeek-OCR-2's official tested stack differs from this Blackwell host, so its
  exact Transformers/tokenizers API pair remains isolated in a hash-locked
  external overlay. Two real document inferences now complete with about 8.19 GB
  peak allocated VRAM; the remaining obstacle is structural fallibility, not
  runtime capacity: page 14 emitted one wrapped-label/value-shift error.
- E-0018 is one selected calibration page from one bank/year. Its perfect
  numeric/sign agreement must be tested against E-0010 and bank/period-disjoint
  holdouts. DeepSeek's table bounding box is model-normalized proposal geometry,
  not source-pixel authority; independent word boxes are still required.
- The S3 backup/restore obstacle is resolved. After local source offload, tests
  that require raw PDFs must explicitly hydrate the required logical paths;
  control-plane checks must never claim local source-byte verification while
  those files are absent.

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
7. Fuse specialized readers on a fixed source-space row grid: PP-OCRv6 preserves
   row/cell pixels and values; DeepSeek proposes Vietnamese labels and order.
   Numeric fingerprints may gate a structural overflow hypothesis but never
   replace output values. Require a score margin and abstain on ambiguity. None
   of the readers can independently map IDs or establish numeric truth.
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

1. Seal E-0019 from the completed E-0017 pages 13→14 PP-OCRv6 and DeepSeek runs;
   report row/cell/label/method before-and-after against the frozen reference.
2. Apply the same fixed-grid overflow fusion to the existing E-0010 failures,
   then rerun E-0010 and the full six-page E-0017 denominators for before/after.
3. Execute the already-verified offload plan for the 2,567 registered PDFs and
   Mongo dump to reclaim about 18.3 GB. Preserve the fsynced local journal and
   remote offload record; do not delete generated output, runtimes or tools.
4. Record the exact offload record, removed count/bytes and post-offload free
   space here; hydrate only the bounded PDFs needed by the next accuracy run.
5. Expand Role A next to a different bank and period after E-0017, using the
   same pre-inspection role freeze and common metrics rather than a new one-off
   experiment script.
6. Build a human-gold evaluation split separated by bank and reporting period,
   including skew, warp, dark headers, blurred digits, wrapped rows, continuation
   pages, direct/indirect LCTT, separate/consolidated scope, and quarterly/YTD
   derivation cases.
7. Define calibrated abstention thresholds only after the human-gold benchmark;
   unresolved evidence must continue to produce review statuses rather than
   guessed output.

## Questions requiring user feedback

- Q-BOOT-004 and Q-BOOT-005 are resolved. No open question currently requires
  user feedback.
