# Current status — PDF BCTC to mapped template Excel

Updated: 2026-08-08

## 1. Current schema/item coverage

| Statement | Schema total | Status reconciled | Observed | Mapped | Unresolved | Fully verified |
| --------- | -----------: | ----------------: | -------: | -----: | ---------: | -------------: |
| CDKT | 78 | 78/78 | 64 PDF rows / 128 cells | 62/78 | 0 mapping items; 1 cross-statement scope question | 0/78 |
| KQKD | 25 | 25/25 | 22 PDF rows / 88 cells | 22/25 | 0 | 0/25 |
| LCTT | 108 | 108/108 | 43 PDF rows / 86 cells | 43/108 | 0 | 0/108 |
| TM | 1,613 | 1,613/1,613 | 539 financial PDF rows / 1,635 value-status slots | 799/1,613 | 85 | 0/1,613 |

Exact reconciliations:

- CDKT: `78 = 62 MAPPED + 16 NOT_OBSERVED_IN_THIS_PDF`.
- KQKD: `25 = 22 MAPPED + 3 NOT_OBSERVED_IN_THIS_PDF`.
- LCTT: `108 = 43 MAPPED + 8 NOT_OBSERVED_IN_THIS_PDF + 57 SCHEMA_ITEM_NOT_APPLICABLE`.
- TM quantitative pages 30–54 and 57–61: `1,613 = 799 MAPPED + 85 AMBIGUOUS/UNRESOLVED + 706 NOT_OBSERVED_IN_THIS_PDF + 23 NOT_APPLICABLE + 0 UNASSESSED`. Pages 55–56 and 59 are narrative-only. The page-52–54 and page-57–61 schema gaps are allocated, hierarchy-bound and mapped rather than left as proposals; the complete current TM schema now has an explicit disposition.

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

- **Role A:** hash-bound references exist for CTG Q2/2026, ACB Q2/2026 and MBB Q1/2026. The active registry has 1,824 unique schema items: CDKT 78, KQKD 25, LCTT 108 and TM 1,613.
- **Role B:** MBB Q1/2026 reaches development Excel for CDKT, KQKD and LCTT. TM reaches item-level parsing/mapping across every quantitative note page through the end of the 61-page PDF; cross-page totals remain validation-only and never create duplicate ownership. A single consolidated TM workbook is not yet built.
- **Latest measurable result:** CDKT exports 114 observed plus 2 derived values; KQKD has 88/88 numeric cells independently matched and 32/32 accounting checks passed; LCTT exports 71 values, 9 dashes and 6 blanks; TM has 799 mapped schema items across 539 financial source rows and 1,635 value/status slots. All 1,613 current TM schema items have explicit, pairwise-disjoint dispositions, with no `UNASSESSED` item and no detected extraction miss.

## 4. Current development position

- **Bank/report/period:** MBB consolidated Q1/2026; snapshot statements compare 31/03/2026 with 31/12/2025, duration statements compare Q1/2026 with Q1/2025; reported unit is generally VND × 1,000,000.
- **Latest sealed version:** E-0041 CDKT workbook/provenance pair. No new E-version is planned for ordinary coverage expansion.
- **Regression status:** the exact final-byte unit suite passes `1,240/1,240` in 22m51s. Deterministic schema replay, complete 26-owner partition checks, focused page-52–61 mapping tests, and Ruff/scoped-format/diff checks also pass. Historical frozen consumers remain bound to exact Git snapshots without rewriting sealed artifacts.
- **Biggest remaining blocker:** 85 TM schema items remain genuinely ambiguous/unresolved, represented by 21 user-review questions. Seventeen clear missing-schema groups are separately queued for automatic addition and do not require a user answer.
- **Exact next end-to-end step:** execute the 17 automatic schema-addition groups, then emit one consolidated TM development workbook with item/value/status/period/unit/scope provenance.

## 5. Overall status

```text
Current end-to-end status:
PDF → page → row/cell → OCR → mapping → validation → Excel

Completed through: CDKT, KQKD and LCTT development Excel; all current TM schema items reconciled across every quantitative page of the MBB Q1/2026 PDF
Currently working on: automatic additions for clear missing TM concepts and consolidated TM Excel export
Not yet completed: 85 TM ambiguities; 17 automatic schema-addition groups; consolidated TM Excel; multi-bank/period verification
Production approved: NO
```
