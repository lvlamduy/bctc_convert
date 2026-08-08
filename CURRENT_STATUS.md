# Current status — PDF BCTC to mapped template Excel

Updated: 2026-08-08

## 1. Current schema/item coverage

| Statement | Schema total | Status reconciled | Observed | Mapped | Unresolved | Fully verified |
| --------- | -----------: | ----------------: | -------: | -----: | ---------: | -------------: |
| CDKT | 78 | 78/78 | 64 PDF rows / 128 cells | 62/78 | 0 mapping items; 1 cross-statement scope question | 0/78 |
| KQKD | 25 | 25/25 | 22 PDF rows / 88 cells | 22/25 | 0 | 0/25 |
| LCTT | 108 | 108/108 | 43 PDF rows / 86 cells | 43/108 | 0 | 0/108 |
| TM | 1,417 | 740/1,417 | 438 financial PDF rows / 1,099 value-status slots | 293/1,417 | 85 reconciled; 677 not yet assessed | 0/1,417 |

Exact reconciliations:

- CDKT: `78 = 62 MAPPED + 16 NOT_OBSERVED_IN_THIS_PDF`.
- KQKD: `25 = 22 MAPPED + 3 NOT_OBSERVED_IN_THIS_PDF`.
- LCTT: `108 = 43 MAPPED + 8 NOT_OBSERVED_IN_THIS_PDF + 57 SCHEMA_ITEM_NOT_APPLICABLE`.
- TM implemented pages 30–44 and 46–52: `1,417 = 293 MAPPED + 85 AMBIGUOUS/UNRESOLVED + 339 NOT_OBSERVED_IN_THIS_PDF + 23 NOT_APPLICABLE + 677 UNASSESSED`. Page 52 also exposes 12 clear schema-addition proposals; these are not counted as mapped until allocated into the versioned schema.

“Observed” means physically identified PDF rows/cells. “Mapped” means assigned to a ReportNormId. “Fully verified” requires the complete item, value/status, period, unit, scope, mapping and Excel tuple to have independent authority; provisional or inferred results are not counted.

## 2. Current technology/logic pipeline

```text
PDF
→ deterministic PyMuPDF page rendering / embedded-text evidence where present
→ statement and page discovery
→ PP-OCRv6 word boxes
→ statement-specific fixed-grid, wrapped-row and continuation reconstruction
→ DeepSeek-OCR-2 / VietOCR label corroboration where configured
→ signed numeric parsing + independent PDF-text or render-pixel DASH evidence
→ visible-header period, unit and consolidated/separate-scope binding
→ ordered SchemaGraph/subgraph mapping
→ accounting equations without repairing source values
→ deterministic supplied-template Excel + provenance
```

CDKT, KQKD and LCTT now use the versioned business schema. TM uses note-specific geometry because its tables vary materially by page; percentage, class/geography and other auxiliary axes stay in provenance unless the schema explicitly supports them. Qwen is not in the active path.

## 3. Role A / Role B status

- **Role A:** hash-bound references exist for CTG Q2/2026, ACB Q2/2026 and MBB Q1/2026. The active registry has 1,628 unique schema items: CDKT 78, KQKD 25, LCTT 108 and TM 1,417.
- **Role B:** MBB Q1/2026 reaches development Excel for CDKT, KQKD and LCTT. TM reaches item-level parsing/mapping for pages 30–44 and 46–51; page 52 is fully parsed, maps its two unique existing-schema items and records external-owner totals only as validation. A single consolidated TM workbook is not yet built.
- **Latest measurable result:** CDKT exports 114 observed plus 2 derived values; KQKD has 88/88 numeric cells independently matched and 32/32 accounting checks passed; LCTT exports 71 values, 9 dashes and 6 blanks; TM has 293 mapped schema items across 438 financial source rows and 1,099 value/status slots. Page 52 adds 12 clear, hierarchy-aware schema proposals without creating user-review questions.

## 4. Current development position

- **Bank/report/period:** MBB consolidated Q1/2026; snapshot statements compare 31/03/2026 with 31/12/2025, duration statements compare Q1/2026 with Q1/2025; reported unit is generally VND × 1,000,000.
- **Latest sealed version:** E-0041 CDKT workbook/provenance pair. No new E-version is planned for ordinary coverage expansion.
- **Regression status:** final unit regression passes `1,172/1,172`; deterministic schema replay, changed-file Ruff/format and diff checks also pass. Historical frozen consumers remain bound to exact Git snapshots without rewriting sealed artifacts.
- **Biggest remaining blocker:** 677 TM schema items are still unassessed. `QUESTION_FOR_USER.md` now separates 21 genuine TM review questions from 17 clear schema additions that Codex will execute without waiting for an answer.
- **Exact next end-to-end step:** add the 12 clear page-52 items and 44 clear page-53 items, implement item-level page 53, continue pages 54–61, then emit one TM development workbook.

## 5. Overall status

```text
Current end-to-end status:
PDF → page → row/cell → OCR → mapping → validation → Excel

Completed through: CDKT, KQKD and LCTT development Excel; TM item parsing/mapping for pages 30–44 and 46–52
Currently working on: automatic page 52–53 schema additions and page 53 item-level implementation
Not yet completed: full TM coverage/Excel; 85 reconciled TM ambiguities; 677 unassessed TM items; multi-bank/period verification
Production approved: NO
```
