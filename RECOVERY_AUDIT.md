# Recovery audit

Captured: 2026-08-05T18:33:51.243118+00:00

## Authoritative starting state

- The old server/GPU state is treated as unrecoverable and was not searched.
- Existing repository history contains only the newly supplied input workbooks; no prior Python implementation or OCR artifacts were present.
- Inputs found: **2567 PDFs** (17761344114 bytes), four schema workbooks, four supporting hierarchy workbooks, and one bank-list workbook.
- PDF registry hash: `c243bf88668eeba67ab14eebf11aba37e31f9c1bf80e180f72643f8491035c84`.
- SchemaGraph hash: `22cbcc6fe8bbddf787a43c588c9b5f445bb2b75dd6a4b02c5e9f81f7d0418368`.
- Supporting hierarchy status: `VALIDATED_SUPPORTING_REFERENCE` with 1535 validated edges/items; LCTT coverage is explicitly direct-branch-only.
- Source files were read and hashed only; none were overwritten.
- Inventory stable across registration: **True** (attempts: 1).

## Material discrepancies

- Actual schema counts are CDKT=77, KQKD=24, LCTT=107, TM=1384 (total 1592), not the historical 1,773-item count.
- The supplied TM workbook does not contain ID 1944. It remains a proposal in `proposed_schema_additions.jsonl`.
- LCTT membership is now based on contiguous workbook positions, not numeric ID ranges. The latest semantic wording conflicts with the visible anchors/endpoints, so semantic high-confidence acceptance remains fail-closed.
- The uploaded MongoDB archive is hash-registered. The allowlisted financial template audit contains 1851 documents and found no ReportNormID 1944 collision; historical value collections are not indexed yet.
- A local control-plane backup restored successfully: `True`. Per the user's development policy, development backup status is **PASS**. It is not off-machine and does not protect against total VPS loss; production status remains `FAIL`.

## Recovery posture

Generated artifacts use atomic write, fsync, rename, and post-write hash verification. Source identity is recorded in `data/registered/source_registry.jsonl`; content-addressed artifact materialization and off-machine versioning remain required before production.
