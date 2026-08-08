# Current status — PDF BCTC to mapped template Excel

Updated: 2026-08-08

## 1. Current schema/item coverage

| Statement | Total schema items | Located/identified in PDF | ReportNormId mapped | Values/period extracted | Fully verified |
| --------- | -----------------: | ------------------------: | ------------------: | ----------------------: | -------------: |
| CDKT | 77 | 64 source rows observed | 61/77; 3 additional rows retained as source-only | 111/122 mapped period cells are numeric; 5 dash, 5 blank, 1 unresolved | 0/77 end-to-end |
| KQKD | 24 | Statement page located; 0/24 item-level | 0/24 | 0/24 end-to-end | 0/24 |
| LCTT | 107 | Statement pages located; 0/107 item-level | 0/107 | 0/107 end-to-end | 0/107 |
| TM | 1,385 | Notes boundary located; 0/1,385 item-level | 0/1,385 | 0/1,385 end-to-end | 0/1,385 |

“Observed” means visible PDF evidence was reconstructed. “Mapped” means the current machine mechanism selected a schema ID. “Value extracted” means a mapped physical period cell has numeric evidence; dash/blank remain distinct states. “Fully verified” requires the whole item tuple and is not inferred from a machine mapping. The fixed reviewed subset is 6/6 exact for mapping only, so it is not counted as full-item verification.

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
- **Role B:** the production-side path currently reaches MBB CDKT statement discovery, 64-row/128-cell reconstruction, semantic/numeric reading, 61-row mapping, diagnostic accounting checks and deterministic in-memory workbook/provenance generation. The final workbook pair is not yet formally captured and sealed.
- **Latest measurable comparison:** the fixed six MBB CDKT reviewed rows are mapped 6/6 to the reviewed ReportNormId. This covers only 6/61 selected rows and is not a production-accuracy result.

## 4. Current development position

- **Bank/report/period:** MBB, CDKT, current 31/03/2026 versus comparative 31/12/2025; visible unit bound to VND × 1,000,000; scope remains `UNKNOWN`.
- **Latest sealed experiment:** E-0040 formal mapping, including one-file S3 durability and two-pass restore verification. E-0041 is the current formal Excel/provenance stage.
- **Regression status:** E-0041 mechanism checkpoint `cdcdc57` passed 977 tests with 2 expected skips; its formal export/seal mechanism also passed independent race, authority and deterministic-replay audit.
- **Biggest remaining blocker:** the deterministic two-file E-0041 workbook/provenance pair still needs its clean-commit formal capture, exact replay and separate hash seal. Broader bank/period-disjoint validation has not started.
- **Exact next end-to-end step:** from a clean pushed commit, dry-run and capture the workbook plus provenance in a fresh process, replay them byte-for-byte, and publish the separate two-file seal.

## 5. Overall status

```text
Current end-to-end status:
PDF → page → row/cell → OCR → mapping → validation → Excel

Completed through: sealed MBB CDKT mapping and deterministic in-memory Excel build
Currently working on: formal Excel/provenance capture and replay seal
Not yet completed: sealed final Excel artifact; KQKD/LCTT/TM item pipelines; bank/period-disjoint validation
Production approved: NO
```
