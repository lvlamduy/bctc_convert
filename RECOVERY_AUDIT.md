# Recovery audit

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
