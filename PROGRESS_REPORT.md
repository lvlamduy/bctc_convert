# Progress report

- Updated: 2026-08-06T04:28:00+00:00
- Branch: `codex/rebuild-bootstrap`
- Latest clean, tested, pushed checkpoint: `8dd54226d7c889d68ad88489132a01a348418408`
- Hardware: NVIDIA GeForce RTX 5070 Ti (16,303 MiB, compute capability 12.0); 125.71 GiB RAM
- Runtime state: `LOGIC_DEVELOPMENT_INFERENCE_PASS_NOT_PRODUCTION_APPROVED`
- Registered schema rows: 1,592 (CDKT 77; KQKD 24; LCTT 107; TM 1,384)
- Registered PDFs: 2,567
- Latest full regression: 222 passed, 2 intentionally skipped historical replays; Ruff and `git diff --check` passed

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

## Currently in progress

- Implementing and testing the S3 snapshot/offload/hydration checkpoint before
  uploading large files. Every object is content-addressed by SHA-256, written
  with `If-None-Match: *`, checked by S3 SHA-256 plus HEAD metadata, and published
  through a final immutable manifest. Offload remains dry-run by default and is
  limited to exact `source_pdf` and `mongodb_dump` manifest records.
- Q-BOOT-004 is approved and queued as the next isolated checkpoint: append TM
  ID 1944 with its exact authorized name, preserving every existing workbook
  row, ID, name, order, and mapping, then extend Role A, Role B, Excel,
  evaluation, and mandatory-search contracts.

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
- DeepSeek-OCR-2's 6.78 GB weight is larger than the current 5.7 GB persistent
  workspace headroom, and its official CUDA 11.8/PyTorch 2.6 stack is not native
  to the Blackwell GPU. The first run needs an isolated Blackwell-compatible
  runtime and ephemeral `/dev/shm` cache or expanded persistent storage.
- Current Transformers strict configuration validation exposes a legacy-null
  field in TATR's official 2023 checkpoint. Compatibility must remain narrowly
  version-bound; a generic config rewrite would hide upstream drift.
- The legacy processor's one-key size representation is also rejected by the
  current runtime. Its explicit 800/800 resolution must retain aspect ratio and
  be recorded separately from an experimental high-resolution override.
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
7. Fuse specialized readers by role: TATR/TableFormer propose table geometry;
   PP-OCRv6 proposes word/cell pixels; DeepSeek/Paddle VLMs propose language and
   reading order. None can independently map IDs or establish numeric truth.
8. Develop custom learned components only behind frozen baselines: graph-based
   row/cell relation modeling, Vietnamese label encoders trained with
   same-label/different-parent hard negatives, specialized digit/sign recognition,
   and conditional dewarping. Evaluate on bank- and period-disjoint holdouts.
9. Protect large inputs with immutable S3 content keys and a manifest-first
   restore contract. Reclaim local space only after remote HEAD/checksum and
   sampled download/semantic restore checks pass; hydrate exact logical paths
   without overwriting a mismatched local file.

## Planned next steps

1. Finish the S3 snapshot/offload/hydration regression, update the recovery
   documentation, then commit and push the mechanism from a clean worktree.
2. Append and fully propagate TM ID 1944 under the approved append-only policy;
   verify workbook preservation/collision/order and commit/push separately.
3. Publish and full-content restore-test the immutable snapshot, then offload the 2,567
   registered PDFs and Mongo dump to reclaim about 18.3 GB. Preserve the local
   eviction journal and remote record; do not delete output/runtime/tool assets.
4. Run TATR v1.1 All on the two frozen E-0016 full-table
   originals; seal row/column/header coverage and retained failure evidence.
5. Implement canonical logical-row fusion for headerless row bands and full-table
   disagreement cases without using values, ReportNormId magnitude, history, or
   arithmetic to force alignment.
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

- Q-BOOT-004 and Q-BOOT-005 are approved. Their implementation/verification is
  in progress; neither requires further user feedback.
