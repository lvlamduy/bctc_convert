# Recovery audit

## New VPS recovery — 2026-08-07

- Git branch `codex/rebuild-bootstrap` was recovered from GitHub. The initial
  recovered tip was `3b69c9e`; recovery protection was then committed and
  pushed through `8dd3a09`. Git fetch and authenticated push both pass.
- The working host is an RTX 4090 (compute capability 8.9, 24,564 MiB), 62 GiB
  RAM, Python 3.11.10 and NVIDIA driver 580.126.09/CUDA 13.0. The exact
  125-package historical runtime was rebuilt: its installed freeze SHA-256 is
  `c0e8c43f84360a8eb0ebeff1ef5de43969bdd291eb2c7cee363c35ef2c78437b`.
  PP-OCRv6 uses the pinned Paddle 3.3.0 CPU FP32 path and reproduced the sealed
  output. The historical GPU smoke correctly rejects this host's 8.9 capability
  against the old RTX 5070 Ti `sm_120` identity; that historical manifest was
  not rewritten.
- S3 list/read/write/read-back/delete connectivity passes. Bucket versioning,
  default AES-256 encryption and all public-access blocks remain enabled. The
  newest full snapshot is `20260806T050030130746Z-4a469fab2334`, manifest
  SHA-256 `74be9ea09905f0c7842d5a0b46bfe44f3fc5f32cc2c15b5040efcc4e99e8981b`.
- The full snapshot's run record proves 4,192 catalog objects and a full stream
  restore. Four bounded PDFs needed by recovery regression were hydrated by the
  no-overwrite manifest path and verified.
- Recovery found one post-snapshot loss: E-0027 `batch_manifest.json`, expected
  SHA-256 `0d94762b…c2889`, is absent from local disk, Git objects, every S3
  object/version, GitHub Actions and releases. It has not been fabricated.
- R-0001 rebuilt pages 1–9 from the registered MBB PDF using the exact pinned
  runtime and two model revisions. Aggregate non-timing OCR metrics are exact
  (794 lines, 6,915 tokens, mean `0.9772775223108022`, minimum
  `0.4495129883289337`); pages 3–4 renders are byte-identical. After changing
  only the `input_path` provenance string to its historical path, both OCR JSON
  files are byte-identical to their historical hashes. The full V3 discovery
  JSON is exact. R-0001 explicitly remains a functional reproduction, not the
  original batch manifest or identity.
- The three dedicated `~/.codex/sessions/` S3 archive versions passed their
  original hash/restore gates but are now security-quarantined: each captured a
  GitHub credential that appeared inside session content. Integrity restoration
  did not prove secret exclusion. Session-backup V2 now scans stable content and
  paths, builds an exact-inventory archive, and locally restores/rescans it
  before any AWS call; the downloaded copy is verified again. Clean V1 archives
  require a current V2 rescan, while the contaminated versions fail closed.
  The credential must be revoked, and deleting those immutable S3 versions
  requires separate explicit approval. No scheduler was installed and no new
  session backup is permitted while the source sessions fail the scan.
- The 61 generated R-0001 files (21,754,667 bytes) are enrolled in bounded
  artifact snapshot
  `20260807T045030Z-r0001-e0027-reproduction-8a1cca495582`, child of the passing
  full snapshot. Manifest SHA-256 is
  `fbfe05928536f20043330fc0f9aab4a5d88557dad03e69ac1467917e69f353ff`;
  all 61 unique objects were downloaded and hash-verified after publication.
  A no-overwrite `s3-hydrate` probe against the child manifest also passed.
- Current control-plane regression after the recovery overlay: **452 passed,
  2 intentionally skipped**; Ruff and `git diff --check` pass. The overlay is
  allowed only for the exact missing path/hash and exposes recovery status; it
  cannot silently replace the historical hash.

Captured: 2026-08-06T00:31:18.199477+00:00

Schema/S3 posture refreshed: 2026-08-06T04:48:37+00:00

## Authoritative starting state

- The old server/GPU state is treated as unrecoverable and was not searched.
- Existing repository history contains only the newly supplied input workbooks; no prior Python implementation or OCR artifacts were present.
- Inputs found: **2567 PDFs** (17761344114 bytes), four schema workbooks, four supporting hierarchy workbooks, and one bank-list workbook.
- PDF registry hash: `c243bf88668eeba67ab14eebf11aba37e31f9c1bf80e180f72643f8491035c84`.
- SchemaGraph hash: `f14912b1a6eeb9df6c57f86deca1381cf2bddee8d626cba2143d6d3367009e88`.
- Supporting hierarchy status: `VALIDATED_SUPPORTING_REFERENCE_WITH_SCHEMA_ONLY_APPENDS` with 1535 validated edges/items; LCTT coverage is explicitly direct-branch-only and TM 1944 has no invented hierarchy parent.
- Source PDFs were read and hashed only. The sole authorized source-workbook mutation is the audited Q-BOOT-004 append of TM 1944.
- Inventory stable across registration: **True** (attempts: 1).
- Isolated GPU runtime local acceptance: **PASS**; production model approval remains separate and pending.

## Material discrepancies

- Actual schema counts are CDKT=77, KQKD=24, LCTT=107, TM=1385 (total 1593), not the historical 1,773-item count.
- Q-BOOT-004 is applied: TM 1944 is appended after 1943 with exact before/after workbook hashes and proof that all prior ID/name/order mappings are unchanged. It is enrolled in Role A, Role B, Excel, evaluation, and mandatory search.
- LCTT membership is based on contiguous workbook positions, not numeric ID ranges: 4155→4168 is INDIRECT and 4104→4116 is DIRECT.
- The uploaded MongoDB archive is hash-registered. Its pre-append audit found no ReportNormID 1944 collision. The rebuilt 1,593-item historical weak-reference registry verifies 112147 cells across 27 banks and zero historical rows for 1944; database constraints forbid mapping and confidence promotion.
- Tracked E-0010 calibration integrity is **PASS_TRACKED_AND_LOCAL_SEALS**; 2/2 locally present seals verify. It remains machine-reference calibration, not production accuracy.
- Tracked E-0011 targeted geometry-recovery integrity is **PASS_TRACKED_AND_LOCAL_SEALS**; 3/3 locally present seals verify. It remains post-failure machine-reference calibration, not production accuracy.
- Tracked E-0012 batch/checkpoint integrity is **PASS_TRACKED_AND_LOCAL_ARTIFACTS**; 9/9 locally present artifacts verify. It is a mechanism regression on an existing page, not a new accuracy sample.
- Tracked E-0013 ordered statement-location integrity is **PASS_TRACKED_AND_LOCAL_ARTIFACTS**; 8/8 locally present source/preprocess/batch/result artifacts verify. It remains page/scope calibration, not row/schema/numeric or production accuracy.
- A local control-plane backup restored successfully: `True`. S3 bucket versioning is enabled while AES-256 default encryption and all public-access blocks remain active; Object Lock is absent by instruction. The complete off-machine snapshot and real full-content restore are still pending, so production backup status remains `FAIL`.

## Recovery posture

Generated artifacts use atomic write, fsync, rename, and post-write hash verification. Source identity is recorded in `data/registered/source_registry.jsonl`; content-addressed artifact materialization and off-machine versioning remain required before production.
