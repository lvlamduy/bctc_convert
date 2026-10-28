# F25 persisted experimental baseline, 2026-10-28

Producer `3d907507cabe85b744552ccf23544b642949b993` completed both authoritative experimental corpus runs under the 2 GiB address-space limit. This document records a recoverable baseline, not family acceptance. No provider was called. The two frozen shared files, the migration manifest and the historical base commit remain unchanged.

| Evidence | FULL271 | COMMON204 |
| --- | --- | --- |
| Run directory | `/home/bctc/claude-runs/f25-full271-3d907507-v4` | `/home/bctc/claude-runs/f25-common204-3d907507-v4` |
| Producer / postcheck / wrapper exits | 0 / 0 / 0 | 0 / 0 / 0 |
| Documents / READY / unresolved | 271 / 176 / 95 | 204 / 133 / 71 |
| Mappings | 744 | 594 |
| Elapsed | 44:46.11 | 28:35.36 |
| Maximum RSS, KiB / swaps | 1,437,452 / 0 | 1,144,276 / 0 |
| SQLite quick_check / foreign_key_check rows | ok / 0 | ok / 0 |

The focused evidence at this producer is 570 passing tests plus 129 passing tests completing the required shared-module coverage, Ruff exit 0 and explicit compilation of five files. Native/clone source and imported-origin guards were checked. Both SQLite integrity checks opened the stores read-only and verified unchanged file hashes. The final audit projection matches on all 204 shared source identities with zero differences in disposition, report norm ID, role, unit, states and typed coefficients. That projection excludes corpus-relative row locators and run/candidate/query IDs and does not replace PDF or residual judgment.

FULL run ID: `gjfafstorev1:run:5b6014ea0ac9c92b12031ede37a9ecc886800f5ff2e83bb98b9a29e15c767eec`.

COMMON run ID: `gjfafstorev1:run:44bac02562c581b0a10d249c7ae1e08f2b0f9c02dfbcb1a05c3c03389115aed2`.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| FULL results.sqlite3 | 111747072 | `3e5da24bf39d52cefd645c9dfc8b3edafcb793130a7c84f3bc3a732ae322b91b` |
| FULL family25.json | 63506264 | `c7614f82b831bad73a1c74caaeb94a5f3d880b9dc09080476eacc71997318549` |
| FULL family25.audit.json | 2608061 | `e865bb9fe9f52df3173af622090073d74fba2f802c60fbe7f88f355dfa4b8ed5` |
| COMMON results.sqlite3 | 84701184 | `d00956d5f0655faba4a0997f89232995a654a420d7b02f8a059ce42463bee3b4` |
| COMMON family25.json | 48259515 | `e4b92af431b71401df582f46658ed3c411f5777aa9d10b227fa6438c538b8f00` |
| COMMON family25.audit.json | 2128793 | `83952bc81fb049d098921eed9d52d2cab0eaa35415680af201fe653d8e1c3c8c` |

## Versioned recovery checkpoint

Bucket `test-s3-duylv`, region `us-east-1`. The FULL database, JSON, audit and runtime evidence were uploaded to new keys with conditional creation, then verified by byte count, server SHA-256 checksum and exact VersionId. No old object was overwritten or deleted and no duplicate PDF archive was created.

Prefix: `bctc-ai/checkpoints/2025-current/20261028T020823Z-f25-3d907507-full271-experimental-e053a938735941d3a65b1da5ac5da698/`.

Manifest key: prefix + `manifest.json`.

Manifest SHA-256: `1b1363b164bfda35d190815cdc35ea02e4537407364523b6f62242b5cb9fbf1c`.

Manifest VersionId: `zCPBYWdU7za5ksb.23xbUXJ9PMShDybD`.

| Key relative to prefix | Exact VersionId |
| --- | --- |
| `database/results.sqlite3` | `9ehdLn_qDj6Cf2LGKHoNw7TsfMvB9mbE` |
| `artifacts/family25.json` | `vy5jUK.8vYnPRs5O5x4z1DrQoc.AKFE.` |
| `artifacts/family25.audit.json` | `Bdg0oBIRPQh8mlgsKsly2T.sPPr_opnS` |
| `receipts/runtime-evidence.zip` | `ZuyjlCb3phw2vGoMYqPqvGtHrop5_Khu` |

The evidence ZIP is 1,190,297 bytes, SHA-256 `de9c56569185850bf48dcfd0ac12363e4a704f61471956cf2d674df61ba3129c`. Restore by exact VersionId and verify hashes before use. The immutable S3 manifest predates COMMON completion and therefore records COMMON as remaining; this additive document records the subsequent actual result. COMMON is retained at the run directory above and is not claimed to be included in the FULL backup manifest.

Local evidence under `D:\bctc_bank\restore-receipts`:

- `F25_FULL271_3D_ACTUAL_SUCCESS_20261028_V4/MIRROR_MANIFEST.json`: `220a5de61378079d297404acc93024a39b65b6e55a246b5f2b42bbe12de9741a`.
- `F25_3D_REQUIRED_SHARED_POSTFLIGHT_ACTUAL_20261028_V1_ATTEMPT2/MIRROR_MANIFEST.json`: `55ac6b1b07d4560829cf3f555a51865b90591ca9a0a6e7efb5e50cb59bd8548a`.
- `F25_FULL271_3D_SQLITE_INTEGRITY_20261028_V1/MIRROR_MANIFEST.json`: `6668d59f534d73a9d8b4cf3f45e208a79f7e53bb5ea75d087303747bf05cb122`.
- `F25_CLAUDE_COMMON204_3D907507_V4_20261028_PASS/`: actual COMMON logs, journal, before/after source and output checksums.
- `F25_3D_FULL271_COMMON204_TYPED_PROJECTION_20261028_V1/PROJECTION.json`: `57084ff5c5e051c9d916a00d14f75f0513b52eb003c3151ba8a578251a6f951c`.
- `F25_FULL271_3D_S3_CHECKPOINT_20261028_V1/CHECKPOINT_REF.json`: exact backup references above.

## Remaining work and scope

This baseline has 95 unresolved FULL documents and 209 source-only observations on 83 READY documents. These counts are not a judgment that every residual is genuinely ambiguous. Three authenticated original header presentations exposed parser gaps (SHB163/MSB77/TPB225); a separate source candidate `68ea91c90c80097ad54c905bf388ac12b88665c9` on `codex/f25-printed-header-grammar-v1` addresses only those presentations and remains focused-runtime UNRUN at this checkpoint. VAB245 page-unit transcription remains OPEN. TPB227 stays unresolved without a proven detail period.

Complete focused validation of any new producer before corpus replay. Close the per-source/PDF residual audit and final ledger before sealing. Do not require zero unresolved documents, grant units from another table, infer units from magnitude, convert blanks to zero or backsolve source values. Scope remains bank reports from 2025 to the present; current-date filing completeness is separately unverified. Family 41 remains locked until F39/F36/F37 are terminal.
