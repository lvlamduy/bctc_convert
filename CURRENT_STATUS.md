# Current status — PDF BCTC to mapped template Excel

Updated: 2026-08-08

## 1. Current schema/item coverage

| Statement | Schema total | Status reconciled | Observed | Mapped | Unresolved | Fully verified |
| --------- | -----------: | ----------------: | -------: | -----: | ---------: | -------------: |
| CDKT | 77 | 77/77 | 61/77 schema items; 64 PDF rows | 61/77 | 4/77 | 0/77 |
| KQKD | 24 | 0/24 | 0/24 item-level | 0/24 | 0 enumerated; 24 unassessed | 0/24 |
| LCTT | 107 | 0/107 | 0/107 item-level | 0/107 | 0 enumerated; 107 unassessed | 0/107 |
| TM | 1,385 | 0/1,385 | 0/1,385 item-level | 0/1,385 | 0 enumerated; 1,385 unassessed | 0/1,385 |

CDKT reconciles exactly as `77 = 61 MAPPED + 12 NOT_OBSERVED_IN_THIS_PDF + 3 AMBIGUOUS_MAPPING + 1 UNRESOLVED`; there are no classified extraction misses or not-applicable items yet. Three additional PDF rows remain source-only outside the 77-item denominator. Across the 122 mapped period cells, 111 are numeric, 5 dash, 5 blank and 1 numeric-reader disagreement. “Fully verified” requires the complete tuple and is not inferred from a machine mapping; the fixed reviewed subset is only 6/6 mapping IDs.

## 2. Current technology/logic pipeline

```text
PDF
→ deterministic rendering/preprocessing
→ PP-OCRv6 word geometry + multi-signal ordered statement discovery v4
→ fixed-grid row/cell reconstruction + wrapped-row/continuation dynamic programming
→ DeepSeek-OCR-2 Vietnamese label proposals (VietOCR is the sealed independent challenger)
→ PP-OCR numeric proposal + independent en_PP-OCRv5_mobile_rec exact-agreement check
→ local visible-header period/unit/scope binding
→ ordered SchemaGraph/subgraph dynamic programming with exhaustive zero-pruning search
→ E-0040 statement-scoped semantic normalization and bounded role repair
→ physical-row accounting diagnostics, with no value repair
→ deterministic openpyxl clone of the supplied template + provenance
→ Excel
```

Current rules preserve visible dash, blank, disagreement and source-only states; they do not convert them to zero or force a ReportNormId. Qwen is not in the active pipeline after its pinned run was rejected.

## 3. Role A / Role B status

- **Role A:** hash-bound calibration references exist for the reviewed CTG Q2/2026, ACB Q2/2026 and MBB Q1/2026 documents; searchable/native TCB pages provide a separate machine-reference calibration set. The schema registry contains 1,593 ordered items, and the current MBB CDKT mapping-review interface contains six pre-existing reviewed rows.
- **Role B:** the production-side path reaches MBB CDKT statement discovery, 64-row/128-cell reconstruction, semantic/numeric reading, 61-row mapping, diagnostic accounting checks and a formally hash-sealed template workbook/provenance pair. The pair is backed up as exactly two immutable S3 objects and passed two-pass no-overwrite hydrate verification.
- **Latest measurable comparison:** the fixed six MBB CDKT reviewed rows are mapped 6/6 to the reviewed ReportNormId. This covers only 6/61 selected rows and is not a production-accuracy result.

## 4. Current development position

- **Bank/report/period:** MBB, CDKT, current 31/03/2026 versus comparative 31/12/2025; visible unit bound to VND × 1,000,000; scope remains `UNKNOWN`.
- **Latest sealed result:** E-0041 MBB CDKT workbook/provenance pair, replayed byte-for-byte and hash-sealed at commit `8d837ee`; the seal is pushed at `dc570c3` and the two output files passed S3 restore/reuse verification.
- **Regression status:** 977 tests passed with 2 expected skips; independent pair/seal audit found no blocker.
- **Biggest remaining blocker:** item coverage, not mechanism sealing—3 CDKT schema items remain ambiguous, 1 schema identity remains unresolved, 3 PDF rows are source-only, 1 numeric cell is unresolved, and KQKD/LCTT/TM have not yet been processed item-by-item.
- **Exact next end-to-end step:** resolve the exposed CDKT issues while applying the reusable pipeline to all 24 KQKD schema items; then proceed to LCTT and quantitative TM.

## 5. Overall status

```text
Current end-to-end status:
PDF → page → row/cell → OCR → mapping → validation → Excel

Completed through: formal MBB CDKT template Excel + provenance + replay seal + restore verification
Currently working on: CDKT unresolved items and 24-item KQKD coverage
Not yet completed: KQKD/LCTT/TM item pipelines; broad tuple verification; bank/period-disjoint validation
Production approved: NO
```
