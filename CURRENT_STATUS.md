# Current status — PDF BCTC to mapped template Excel

Updated: 2026-08-08

## 1. Current schema/item coverage

| Statement | Schema total | Status reconciled | Observed | Mapped | Unresolved | Fully verified |
| --------- | -----------: | ----------------: | -------: | -----: | ---------: | -------------: |
| CDKT | 77 | 77/77 | 61/77 identified; 64 PDF rows | 61/77 | 1 schema item; 3 source-only rows; 1 numeric cell | 0/77 |
| KQKD | 24 | 24/24 | 21/24 identified; 22 PDF rows; 88/88 cells | 21/24 | 0 schema ambiguity; 1 source-only row | 0/24 |
| LCTT | 107 | 107/107 | 41/107 candidate-linked; 43 PDF rows; 86 cell slots | 0/107 automatic | 46 schema items; 2 source-only rows | 0/107 |
| TM | 1,385 | 18/1,385 candidate audit | 20 numeric rows + 2 headings on page 30; 40 cells | 0/1,385 | 18 candidates; 2 source-only rows; remainder unassessed | 0/1,385 |

CDKT reconciles exactly as `77 = 61 MAPPED + 15 NOT_OBSERVED_IN_THIS_PDF + 1 UNRESOLVED`; its three source-only PDF rows are outside the denominator. KQKD reconciles as `24 = 21 MAPPED + 3 NOT_OBSERVED_IN_THIS_PDF`, plus one source-only total row. Its 88/88 observed values agree with the independent PDF text layer and 32/32 accounting checks have zero residual. LCTT reconciles as `107 = 57 SCHEMA_ITEM_NOT_APPLICABLE + 41 CANDIDATE_MAPPING_NOT_AUTOMATIC + 5 AMBIGUOUS_MAPPING + 4 NOT_OBSERVED_IN_THIS_PDF`; its two net/composite rows remain source-only. TM has begun with the first quantitative-note page, not an inferred whole-note reconciliation. “Fully verified” remains zero until the complete mapping/value/period/status/Excel tuple has independent authority.

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

CDKT uses the sealed semantic-normalization/role-repair path. KQKD uses a four-axis hierarchical header parser and history-free SchemaGraph mapping. LCTT uses a two-page direct-method parser and a conservative ordered mapper that exposes candidates without auto-selecting them. TM parsing has started from quantitative-note page 30. Qwen is not in the active path.

## 3. Role A / Role B status

- **Role A:** hash-bound calibration references exist for CTG Q2/2026, ACB Q2/2026 and MBB Q1/2026; the ordered schema registry contains 1,593 items. The fixed reviewed MBB CDKT subset remains 6 rows.
- **Role B:** MBB CDKT reaches a hash-sealed, S3-restored template workbook. MBB KQKD reaches 22 rows/88 cells, four period axes, 21/24 mappings, independent numeric agreement and accounting validation; its development Excel round-trip is in progress. LCTT reaches 43 rows/86 slots and a complete 107-item status reconciliation, with 41 mappings deliberately kept provisional. TM page 30 has 22 logical rows/40 visible cells under item-level audit.
- **Latest measurable Role A/Role B result:** the fixed six reviewed CDKT rows map 6/6. KQKD has no human-reviewed mapping denominator yet, so 21/24 is machine-mapped coverage, not a production-accuracy score.

## 4. Current development position

- **Bank/report/period:** MBB consolidated Q1/2026. CDKT compares 31/03/2026 with 31/12/2025; KQKD/LCTT compare duration 01/01–31/03/2026 with 01/01–31/03/2025. Visible unit is VND × 1,000,000.
- **Latest sealed result:** E-0041 MBB CDKT workbook/provenance pair; no further E-version is planned for coverage work.
- **Regression status:** latest full parser regression: 983 passed, 2 expected skips; focused KQKD and LCTT coverage checks are green.
- **Biggest remaining blocker:** human/schema interpretation for source-only and composite rows, plus insufficient independent semantic evidence for LCTT/TM mappings—not mechanism sealing.
- **Exact next end-to-end step:** publish the deterministic KQKD development workbook, add a second independent LCTT label stream to promote safe candidates, and expand TM item parsing beyond page 30.

## 5. Overall status

```text
Current end-to-end status:
PDF → page → row/cell → OCR → mapping → validation → Excel

Completed through: sealed CDKT Excel; KQKD page/row/cell/OCR/period/mapping/numeric validation; LCTT geometry and 107-item reconciliation
Currently working on: KQKD Excel round-trip, LCTT mapping promotion, and TM quantitative-note parsing
Not yet completed: authoritative LCTT/TM mapping and Excel; broad tuple verification; multi-bank/period validation
Production approved: NO
```
