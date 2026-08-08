# Current status — PDF BCTC to mapped template Excel

Updated: 2026-08-08

## 1. Universal schema and per-document coverage

The original supplied 1,593-item reference is frozen as `BASE_SCHEMA` (`77 CDKT + 24 KQKD + 107 LCTT + 1,385 TM`). The active source-evidenced superset is `UNIVERSAL_BANK_BCTC_SCHEMA@6034`: `1,913 = 78 CDKT + 25 KQKD + 109 LCTT + 1,701 TM`. It contains the base identities plus exactly 320 audited, append-only additions; ReportNormId never defines display order. The ordered universal projection is `ad21aafd…ab03` and the content-addressed graph/schema hash is `b1529c4b…40d5`.

| Statement | Universal items | Visible MBB source | Base identities mapped | Post-base additions (mapped / NO) | Source ambiguity | Source rows accounted |
| --------- | --------------: | -----------------: | ---------------------: | --------------------------------: | ---------------: | --------------------: |
| CDKT | 78 | 64 rows / 128 cells | 61 | 1 (1 / 0) | 0 | 64/64 |
| KQKD | 25 | 22 rows / 88 cells | 21 | 1 (1 / 0) | 0 | 22/22 |
| LCTT | 109 | 43 rows / 86 cells | 41 | 2 (2 / 0) | 0 | 43/43 |
| TM | 1,701 | 553 logical source rows / 1,659 visible value-status slots | 583 | 316 (306 / 10) | 0 | 553/553 |

The ten post-base TM identities classified `NOT_OBSERVED` are preserved accepted identities in structurally completed universal branches; they are not claimed as visible MBB rows and are not treated as extraction failures.

Exact reconciliations:

- CDKT: `78 = 62 MAPPED + 16 NOT_OBSERVED_ON_TARGET_STATEMENT_PAGES`. Quantitative-note links are explicit provenance and do not silently backfill main-statement observations.
- KQKD: `25 = 22 MAPPED + 3 NOT_OBSERVED_IN_THIS_PDF`.
- LCTT: `109 = 43 MAPPED + 9 NOT_OBSERVED_IN_THIS_PDF + 57 SCHEMA_ITEM_NOT_APPLICABLE`.
- TM quantitative pages 30–54 and 57–61: `1,701 = 889 MAPPED + 789 NOT_OBSERVED_IN_THIS_PDF + 23 NOT_APPLICABLE + 0 AMBIGUOUS/UNRESOLVED/UNASSESSED`. Pages 55–56 and 59 are narrative-only. The complete TM schema has one explicit, pairwise-disjoint disposition per ID; visible class/measure axes remain provenance rather than false row identities.

“Observed” means physically identified PDF rows/cells. “Mapped” means assigned to an existing or newly accepted canonical ReportNormId. `DASH`, `BLANK`, `OBSERVED_ZERO`, `NOT_OBSERVED`, and `NOT_APPLICABLE` remain distinct. “Fully verified” still requires independent authority for the complete item/value/status/period/unit/scope/Excel tuple; no item is promoted to that stronger claim here.

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
→ search the evolving universal SchemaGraph
→ reuse an equivalent canonical identity OR add an evidenced missing identity
→ accounting equations without repairing source values
→ deterministic supplied-template Excel + provenance
```

All four statement groups use the versioned universal schema. TM uses note-specific geometry because its tables vary materially by page; percentage, class/geography and other auxiliary axes stay in provenance unless they are genuine accounting-row identities. Qwen is not in the active path.

## 3. Role A / Role B status

- **Role A:** hash-bound references exist for CTG Q2/2026, ACB Q2/2026 and MBB Q1/2026. Role A must preserve every genuine visible row and may emit `POSSIBLE_SCHEMA_GAP`; it is not limited to BASE_SCHEMA. The active universal registry has 1,913 unique items.
- **Role B:** MBB Q1/2026 reaches development Excel for all four statements. TM parsing/mapping covers every quantitative note page through the end of the 61-page PDF; cross-page totals remain validation-only and never create duplicate ownership. The consolidated TM workbook and its paired provenance JSON are deterministic and preserve exact value, zero, dash and blank semantics.
- **Latest measurable result:** CDKT exports 114 observed plus 2 derived values; KQKD has 88/88 numeric cells independently matched and 32/32 accounting checks passed; LCTT exports 71 values, 9 dashes and 6 blanks. TM has 889 mapped schema identities across 553 logical source rows and 1,659 parser-declared visible value/status slots. All 553 rows are accounted (`492 MAPPED + 61 SOURCE_ONLY_VALIDATION`), with zero ambiguity/unresolved/unaccounted rows. The exporter emits 1,248 one-to-one observation/provenance records (`1,059 VALUE + 169 DASH + 20 BLANK`) and 850 validation records (`677 PASS + 1 PASS_ROUNDED + 172 NOT_TESTABLE`, zero `FAIL`). Narrative facts, quantities and records are reported separately from the 1,659-cell denominator.

## 4. Current development position

- **Bank/report/period:** MBB consolidated Q1/2026; snapshot statements compare 31/03/2026 with 31/12/2025, duration statements compare Q1/2026 with Q1/2025; reported unit is generally VND × 1,000,000.
- **Latest sealed version:** E-0041 CDKT workbook/provenance pair. No new E-version is planned for ordinary coverage expansion.
- **TM development artifacts:** `output/development/mbb-q1-2026-tm-consolidated-v2/mbb-q1-2026-consolidated-tm-development.xlsx` (SHA-256 `f41d4179ff1142537d624076eb1771c4454842ef740b42e6723ae910143ada20`) and paired provenance JSON (SHA-256 `ebf605b6b9d992b0465d6d7234ae3bf8877824be3147f023d455455a4fba1339`). Three builds using independent verified cache paths are byte-identical. The prior v1 artifact remains preserved and is not overwritten.
- **Regression status:** the exact final-byte unit suite passes **1,285/1,285** in **4,154.04 seconds (1:09:14)**. Deterministic schema replay, the complete 27-owner partition, focused mapping/export tests, cross-directory export determinism, Ruff/scoped-format and diff checks also pass; historical frozen consumers remain bound to exact Git snapshots without rewriting sealed artifacts.
- **Publication status:** implementation commit `064107af36ab5610d9e695414e18e59d63f8ce8b` is pushed to `codex/rebuild-bootstrap`. Bounded S3 checkpoint `20260808T195617499042Z-064107af36ab` passed full incremental restore; manifest SHA-256 is `bb3d7ba9e71c5e2223aad1c4527d84c383c5c017e383b4dcc8c1a1f0911051a2` and run-record SHA-256 is `0b94d251f6bb3ae196ebbbf9f0d4b07b18ed36a1e7db2cc2b9081a2779ebf847`.
- **Biggest remaining blocker:** no current MBB item-level schema ambiguity remains. The next accuracy boundary is independent multi-bank/period evidence and continued source-driven schema growth, not forcing universal rows to appear at every bank.
- **Exact next end-to-end step:** process the next independent bank/report while allowing evidence-backed schema expansion, then compare cross-bank aliases, hierarchy and extraction behavior.

## 5. Overall status

```text
Current end-to-end status:
PDF → page → row/cell → OCR → mapping → validation → Excel

Completed through: source-complete MBB item reconstruction; universal schema 1,913; deterministic development Excel for CDKT/KQKD/LCTT; all 1,701 TM identities reconciled across every quantitative page
Currently working on: selecting and processing the next independent bank/report for cross-bank universal-schema validation
Not yet completed: broad independent multi-bank/period verification and continued universal-schema discovery from new reports
Production approved: NO
```
