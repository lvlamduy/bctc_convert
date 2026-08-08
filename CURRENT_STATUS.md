# Current status — PDF BCTC to mapped template Excel

Updated: 2026-08-08

## 1. Current schema/item coverage

| Statement | Schema total | Status reconciled | Observed | Mapped | Unresolved | Fully verified |
| --------- | -----------: | ----------------: | -------: | -----: | ---------: | -------------: |
| CDKT | 77 | 77/77 | 61/77 identified; 64 PDF rows | 61/77 | 1 schema item; 3 source-only rows; 1 numeric cell | 0/77 |
| KQKD | 24 | 24/24 | 21/24 identified; 22 PDF rows; 88/88 cells | 21/24 | 0 schema ambiguity; 1 source-only row | 0/24 |
| LCTT | 107 | 107/107 | 46/107 schema candidates; 43 PDF rows; 86 cell slots | 40/107 | 6 schema items; 2 source-only rows | 0/107 |
| TM | 1,385 | 111/1,385 | 69 PDF rows on pages 30, 31 and 35; 122 value/status slots | 56/1,385 | 2 ambiguous IDs; 12 source-only/validation rows; 1,274 unassessed | 0/1,385 |

CDKT reconciles exactly as `77 = 61 MAPPED + 15 NOT_OBSERVED_IN_THIS_PDF + 1 UNRESOLVED`; its three source-only PDF rows are outside the denominator. KQKD reconciles as `24 = 21 MAPPED + 3 NOT_OBSERVED_IN_THIS_PDF`, plus one source-only total row. Its 88/88 observed values agree with the independent PDF text layer and 32/32 accounting checks have zero residual. LCTT reconciles as `107 = 57 SCHEMA_ITEM_NOT_APPLICABLE + 40 MAPPED + 1 LABEL_CONFLICT_CANDIDATE_NOT_AUTOMATIC + 5 AMBIGUOUS_MAPPING + 4 NOT_OBSERVED_IN_THIS_PDF`; its two net/composite rows remain source-only. Implemented TM pages reconcile as `1,385 = 56 MAPPED + 2 AMBIGUOUS_MAPPING + 30 NOT_OBSERVED_IN_THIS_PDF + 23 SCHEMA_ITEM_NOT_APPLICABLE + 1,274 UNASSESSED`; 12 source-only/validation rows sit outside the denominator. “Fully verified” remains zero until the complete mapping/value/period/status/Excel tuple has independent authority.

## 2. Current technology/logic pipeline

```text
PDF
→ deterministic page render + embedded-text evidence when available
→ multi-signal statement/page discovery
→ PP-OCRv6 word geometry
→ statement-specific fixed-grid/wrapped-row reconstruction
→ DeepSeek-OCR-2 label proposal + PP-OCR/VietOCR cross-reader evidence
→ PP-OCR numeric parse + independent PDF-text / en_PP-OCRv5 numeric check
→ visible-header period/unit/scope binding
→ ordered SchemaGraph/subgraph dynamic programming
→ accounting equations without value repair
→ deterministic supplied-template Excel + provenance
```

CDKT uses the sealed semantic-normalization/role-repair path. KQKD uses a four-axis hierarchical header parser and history-free SchemaGraph mapping. LCTT uses a two-page direct-method parser plus ordered PP-OCR/DeepSeek corroboration; 40 one-to-one rows are auto-mapped and one visible/schema label conflict is withheld. TM pages 30, 31 and 35 use repeated-note fixed-grid geometry plus PP-OCR/DeepSeek labels; missing OCR dashes on page 35 require exact render-pixel glyph evidence and are never coerced to zero. Qwen is not in the active path.

## 3. Role A / Role B status

- **Role A:** hash-bound calibration references exist for CTG Q2/2026, ACB Q2/2026 and MBB Q1/2026; the ordered schema registry contains 1,593 items. The fixed reviewed MBB CDKT subset remains 6 rows.
- **Role B:** MBB CDKT reaches a hash-sealed, S3-restored template workbook. MBB KQKD reaches deterministic development Excel with 21/24 mappings; MBB LCTT reaches deterministic development Excel with 40/107 mappings and the conflicting 4140 row withheld. Implemented TM pages reach 69 rows/122 slots and 56 scoped mappings; repeated totals are validation-only rather than duplicated in schema targets.
- **Latest measurable Role A/Role B result:** the fixed six reviewed CDKT rows map 6/6. KQKD has no human-reviewed mapping denominator yet, so 21/24 is machine-mapped coverage, not a production-accuracy score.

## 4. Current development position

- **Bank/report/period:** MBB consolidated Q1/2026. CDKT compares 31/03/2026 with 31/12/2025; KQKD/LCTT compare duration 01/01–31/03/2026 with 01/01–31/03/2025. Visible unit is VND × 1,000,000.
- **Latest sealed result:** E-0041 MBB CDKT workbook/provenance pair; no further E-version is planned for coverage work.
- **Regression status:** cross-statement KQKD/LCTT/TM coverage regression 62/62 passed; Ruff check/format passed. Latest full parser regression: 983 passed, 2 expected skips.
- **Biggest remaining blocker:** 1,274 TM schema items remain unassessed, alongside 26 concrete TM questions exposed in `QUESTION_FOR_USER.md`; mechanism sealing is not the limiting work.
- **Exact next end-to-end step:** implement the simple two-axis page 36 notes, then the page 37–38 tangible and page 39–40 intangible roll-forward pairs.

## 5. Overall status

```text
Current end-to-end status:
PDF → page → row/cell → OCR → mapping → validation → Excel

Completed through: sealed CDKT Excel; KQKD and LCTT development Excel; TM pages 30, 31 and 35 item mapping
Currently working on: TM page 36, then fixed-asset pages 37–40 and remaining notes through 61
Not yet completed: full TM coverage/Excel; authoritative resolution of exposed ambiguities; broad tuple and multi-bank/period verification
Production approved: NO
```
