# Questions for the user

Only material ambiguities that cannot be safely resolved from current evidence are listed.
Answers should be recorded in the CSV or JSONL `user_response` field; IDs remain stable.

## Q-BOOT-001 — CRITICAL

Which contiguous workbook-order blocks define the semantic INDIRECT and DIRECT cash-flow branches?

Recommended safe default: Use contiguous workbook positions, never increasing numeric ranges: positions 1-57 with endpoints 4155→4168 are INDIRECT; positions 58-107 with endpoints 4104→4116 are DIRECT.

Recorded response: Q-BOOT-001 confirmed on 2026-08-06: 4155→4168 in template order is INDIRECT; 4104→4116 in template order is DIRECT.

Status: RESOLVED

## Q-BOOT-002 — HIGH

Please provide the MongoDB URI (or secret name), database and collection names, and a read-only account for historical weak-reference indexing.

Recommended safe default: Continue PDF-only; do not use historical values until read-only access is verified.

Recorded response: Uploaded financial_20_02_2022.gz. Registered SHA-256 0456df4aebb93b58c433b0d2a8c13bbb9402e1511d07758716976b94989204b9.

Status: RESOLVED

## Q-BOOT-003 — CRITICAL

Which versioned off-machine target should receive source PDFs, schemas, OCR, references, workbooks, experiments, database dumps, and model manifests?

Recommended safe default: Use a versioned S3-compatible bucket with object lock and a dedicated prefix.

Recorded response: During model development, keep artifacts on the VPS and commit every working version to Git.

Status: RESOLVED_FOR_DEVELOPMENT

## Q-BOOT-004 — HIGH

The supplied TM schema ends at ID 1943. Should proposed TM ID 1944 be appended with the name stated in the directive?

Recommended safe default: Keep it as a pending append-only proposal; do not alter the supplied workbook yet.

Recorded response: Check that ReportNormID 1944 does not collide before adding it.

Status: COLLISION_CHECK_PASSED_APPEND_DECISION_OPEN
