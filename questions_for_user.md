# Questions for the user

Only material ambiguities that cannot be safely resolved from current evidence are listed.
Answers should be recorded in the CSV or JSONL `user_response` field; IDs remain stable.
Q-BOOT-004 and Q-BOOT-005 are approved; implementation evidence is tracked separately.

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

Recorded response: On 2026-08-06 the user supplied s3://test-s3-duylv/ and authorized backup; profile access, region, AES-256 default encryption and public-access blocking are verified.

Recorded completion: Snapshot `20260806T050030130746Z-4a469fab2334` uploaded
4,192 unique objects and passed catalog HEAD verification, manifest download,
sampled restore across all seven asset classes, Git-bundle/control-plane checks,
sample-PDF open, and a full sequential content restore. Run-record SHA-256 is
`24eb066b51443066dfd14538ef7aeb21e9b700cc6ce995c49e56ff23b6701b04`;
manifest SHA-256 is
`74be9ea09905f0c7842d5a0b46bfe44f3fc5f32cc2c15b5040efcc4e99e8981b`.
Versioning, default AES-256 encryption and all public-access blocks were verified
again after completion; Object Lock remains disabled as directed.

Status: RESOLVED

## Q-BOOT-004 — HIGH

The supplied TM schema ends at ID 1943. Should proposed TM ID 1944 be appended with the name stated in the directive?

Recommended safe default: Keep it as a pending append-only proposal; do not alter the supplied workbook yet.

Recorded response: Approved on 2026-08-06: append TM ReportNormID 1944 with the exact proposed name under the append-only policy, preserving every existing ID, name, order, and mapping; include it in Role A, Role B, Excel, evaluation, mandatory search, and PROGRESS_REPORT.md.

Status: RESOLVED

## Q-BOOT-005 — HIGH

May bucket versioning be enabled on test-s3-duylv?

Recommended safe default: Do not change retention settings without explicit approval; use unique content-addressed keys and keep the production gate failed until versioning is enabled.

Recorded response: Approved on 2026-08-06. Enable bucket versioning, retain public-access blocking and default encryption, and do not enable Object Lock.

Status: RESOLVED
