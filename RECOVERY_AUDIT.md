# Recovery audit

Captured: 2026-08-06T00:31:18.199477+00:00

## Authoritative starting state

- The old server/GPU state is treated as unrecoverable and was not searched.
- Existing repository history contains only the newly supplied input workbooks; no prior Python implementation or OCR artifacts were present.
- Inputs found: **2567 PDFs** (17761344114 bytes), four schema workbooks, four supporting hierarchy workbooks, and one bank-list workbook.
- PDF registry hash: `c243bf88668eeba67ab14eebf11aba37e31f9c1bf80e180f72643f8491035c84`.
- SchemaGraph hash: `22cbcc6fe8bbddf787a43c588c9b5f445bb2b75dd6a4b02c5e9f81f7d0418368`.
- Supporting hierarchy status: `VALIDATED_SUPPORTING_REFERENCE` with 1535 validated edges/items; LCTT coverage is explicitly direct-branch-only.
- Source files were read and hashed only; none were overwritten.
- Inventory stable across registration: **True** (attempts: 1).
- Isolated GPU runtime local acceptance: **PASS**; production model approval remains separate and pending.

## Material discrepancies

- Actual schema counts are CDKT=77, KQKD=24, LCTT=107, TM=1384 (total 1592), not the historical 1,773-item count.
- The supplied TM workbook does not contain ID 1944. It remains a proposal in `proposed_schema_additions.jsonl`.
- LCTT membership is now based on contiguous workbook positions, not numeric ID ranges. The latest semantic wording conflicts with the visible anchors/endpoints, so semantic high-confidence acceptance remains fail-closed.
- The uploaded MongoDB archive is hash-registered. The allowlisted financial template audit contains 1851 documents and found no ReportNormID 1944 collision. The local historical weak-reference index was revalidated at 112147 cells across 27 banks. Its database constraints forbid mapping and confidence promotion.
- Tracked E-0010 calibration integrity is **PASS_TRACKED_AND_LOCAL_SEALS**; 2/2 locally present seals verify. It remains machine-reference calibration, not production accuracy.
- Tracked E-0011 targeted geometry-recovery integrity is **PASS_TRACKED_AND_LOCAL_SEALS**; 3/3 locally present seals verify. It remains post-failure machine-reference calibration, not production accuracy.
- Tracked E-0012 batch/checkpoint integrity is **PASS_TRACKED_AND_LOCAL_ARTIFACTS**; 9/9 locally present artifacts verify. It is a mechanism regression on an existing page, not a new accuracy sample.
- Tracked E-0013 ordered statement-location integrity is **PASS_TRACKED_AND_LOCAL_ARTIFACTS**; 8/8 locally present source/preprocess/batch/result artifacts verify. It remains page/scope calibration, not row/schema/numeric or production accuracy.
- A local control-plane backup restored successfully: `True`. Per the user's development policy, development backup status is **PASS**. It is not off-machine and does not protect against total VPS loss; production status remains `FAIL`.

## Recovery posture

Generated artifacts use atomic write, fsync, rename, and post-write hash verification. Source identity is recorded in `data/registered/source_registry.jsonl`; content-addressed artifact materialization and off-machine versioning remain required before production.
