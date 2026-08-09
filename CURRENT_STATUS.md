# Current status — PDF BCTC to mapped template Excel

Updated: 2026-08-09

## 1. Universal schema and per-document coverage

The original supplied 1,593-item reference is frozen as `BASE_SCHEMA` (`77 CDKT + 24 KQKD + 107 LCTT + 1,385 TM`). The active source-evidenced superset is `UNIVERSAL_BANK_BCTC_SCHEMA@6054`: `1,933 = 97 CDKT + 25 KQKD + 110 LCTT + 1,701 TM`. It contains the base identities plus exactly 340 audited, append-only additions; ReportNormId never defines display order. The ordered universal projection is `691cfc99…d7bb` and the content-addressed graph/schema hash is `ecab3003…c8d5`.

| Statement | Universal items | Visible MBB source | Base identities mapped | Post-base additions (mapped / NO) | Source ambiguity | Source rows accounted |
| --------- | --------------: | -----------------: | ---------------------: | --------------------------------: | ---------------: | --------------------: |
| CDKT | 97 | 75 rows / 150 cells | 59 | 20 (14 / 6) | 0 | 75/75 |
| KQKD | 25 | 22 rows / 88 cells | 21 | 1 (1 / 0) | 0 | 22/22 |
| LCTT | 110 | 43 rows / 86 cells | 41 | 3 (2 / 1) | 0 | 43/43 |
| TM | 1,701 | 553 logical source rows / 1,659 visible value-status slots | 583 | 316 (306 / 10) | 0 | 553/553 |

The ten post-base TM identities classified `NOT_OBSERVED` are preserved accepted identities in structurally completed universal branches; they are not claimed as visible MBB rows and are not treated as extraction failures.

Exact reconciliations:

- CDKT: `97 = 73 MAPPED + 24 NOT_OBSERVED + 0 UNRESOLVED`. Main-statement provision rows are owned by the broader, source-exact identities `6035` and `6036`, while the older narrower `4347` and `4352` remain distinct and are not observed. MBB page 5 independently maps the consolidated off-balance branch `6038`–`6048`; `6049`–`6053` are genuinely absent. Quantitative-note links remain explicit provenance and never silently backfill main-statement observations.
- KQKD: `25 = 22 MAPPED + 3 NOT_OBSERVED_IN_THIS_PDF`.
- LCTT: `110 = 43 MAPPED + 10 NOT_OBSERVED_IN_THIS_PDF + 57 SCHEMA_ITEM_NOT_APPLICABLE`.
- TM quantitative pages 30–54 and 57–61: `1,701 = 889 MAPPED + 789 NOT_OBSERVED_IN_THIS_PDF + 23 NOT_APPLICABLE + 0 AMBIGUOUS/UNRESOLVED/UNASSESSED`. Pages 55–56 and 59 are narrative-only. The complete TM schema has one explicit, pairwise-disjoint disposition per ID; visible class/measure axes remain provenance rather than false row identities.

The next-bank development baseline is now source-captured independently of schema matching:

| VPB Q1/2026 source block | Pages | Visible rows | Visible cells | Current extraction status |
| ------------------------ | ----: | -----------: | ------------: | ------------------------- |
| CDKT main statement | 5–6 | 59 | 110 | 110 `OBSERVED_VALUE` |
| CDKT off-balance statement | 7 | 16 | 32 | 32 `OBSERVED_VALUE`; retained in a separate universal `OFF_BALANCE_SHEET` branch and excluded from main-statement totals |
| KQKD main statement | 8 | 25 | 50 | 49 `OBSERVED_VALUE` + 1 `DASH` |
| LCTT main statement | 9–10 | 34 | 60 | 58 `OBSERVED_VALUE` + 2 `DASH` |
| **Total** | **5–10** | **134** | **252** | **249 values + 3 dashes; 134/134 rows source-accounted** |

The source-driven VPB canonical pass accounts for all `134/134` visible rows: `127` map to the current universal schema, including the 20 accepted source-evidenced additions `6035`–`6054`; three broader TCTC+TCTD rows remain unallocated `NEW_ITEM_PROPOSAL`; three rows are structural; and one visible unlabeled grand total remains `UNRESOLVED`/validation-only. There is no force-mapping, ambiguity, or dropped source row. The proposal rows have no ReportNormId until the accounting decisions in `Q074` are resolved.

VPB's quantitative-TM table-region denominator is now bounded independently of schema mapping. Across the core report-period notes on PDF pages 38–91, 45 pages contain 91 accepted local native-text table regions with `694` value-bearing logical rows and `2,163` visible observations: `2,149` numeric/zero/dash observations (2,145 table cells plus four row-local scalar disclosures) plus 14 explicit `(*)` unavailable-fair-value markers. Narrative/qualitative pages, row-local scalar disclosures, rows outside the financial span, inter-table contexts and unassigned source runs remain explicit. All 91 PDF pages are classified, but 30 inter-table contexts still have unresolved ownership, so the registered full-document artifact is `PARTIAL` and cannot authorize document-wide absence claims. The visible-text gate excludes exactly 51 non-authoritative native spans (50 hidden white ghosts plus the page-78 ToUnicode/render mismatch) without changing the 694/2,163 denominator.

The universal TM graph also has a source-independent context projection for all 1,701 identities. `1,686` connected items have consistent section/ancestor/level context and are mapping-eligible; IDs `785`–`791` and `793`–`799` are quarantined for declared-versus-derived hierarchy-level mismatch, and orphan ID `1944` remains ineligible until its parent/identity context is resolved. This context does not map source rows by bank, page or note number.

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

The VPB TM source stage adds a generic local-region layer rather than widening the main-statement row adapter. It uses visible PyMuPDF native text, causal RGB render evidence, table-local axes, explicit grid slots, row/scalar/context ownership and full-page evidence partitioning. Callback-bound glyph paint identity separates geometry from language/schema meaning; weak-but-visible, chromatic and nonopaque text is retained, while hidden, materially occluded or overlapping text fails closed. The registered full-document wrapper trusts only the accepted statement-discovery notes boundary, classifies every PDF page, snapshots all source/config/code identities, and has no schema or historical-value input.

## 3. Role A / Role B status

- **Role A:** hash-bound references exist for CTG Q2/2026, ACB Q2/2026 and MBB Q1/2026. Role A must preserve every genuine visible row and may emit `POSSIBLE_SCHEMA_GAP`; it is not limited to BASE_SCHEMA. The active universal registry has 1,933 unique items.
- **Role B:** MBB Q1/2026 reaches development Excel for all four statements. TM parsing/mapping covers every quantitative note page through the end of the 61-page PDF; cross-page totals remain validation-only and never create duplicate ownership. The consolidated TM workbook and its paired provenance JSON are deterministic and preserve exact value, zero, dash and blank semantics.
- **Next-bank Role B development:** VPB consolidated Q1/2026 is an immutable `LOGIC_DEVELOPMENT` input, not holdout/validation evidence. Full-document native-text discovery independently selected CDKT pages 5–7, KQKD page 8, LCTT pages 9–10 and the first TM boundary at page 11. The generic main-statement row adapter reconstructed all 134 rows and 252 cells. The separate source-only TM region stage now covers the complete PDF denominator and the 694-row/2,163-observation quantitative-note core without schema, template, historical-value, Role A or prior-answer inputs.
- **Latest measurable result:** CDKT exports 132 observed plus 2 derived values from 75 rows/150 physical statuses; KQKD has 88/88 numeric cells independently matched and 32/32 accounting checks passed; LCTT exports 71 values, 9 dashes and 6 blanks. TM has 889 mapped schema identities across 553 logical source rows and 1,659 parser-declared visible value/status slots. All 553 rows are accounted (`492 MAPPED + 61 SOURCE_ONLY_VALIDATION`), with zero ambiguity/unresolved/unaccounted rows. The exporter emits 1,248 one-to-one observation/provenance records (`1,059 VALUE + 169 DASH + 20 BLANK`) and 850 validation records (`677 PASS + 1 PASS_ROUNDED + 172 NOT_TESTABLE`, zero `FAIL`). Narrative facts, quantities and records are reported separately from the 1,659-cell denominator.

## 4. Current development position

- **Completed mapped baseline:** MBB consolidated Q1/2026; snapshot statements compare 31/03/2026 with 31/12/2025, duration statements compare Q1/2026 with Q1/2025; reported unit is generally VND × 1,000,000.
- **Active next-bank development input:** VPB consolidated Q1/2026, source SHA-256 `614be887…dcde`, immutable role `LOGIC_DEVELOPMENT`. Discovery artifact SHA-256 is `ddeaabd0…aaa9`; registered row artifact SHA-256 is `fa1c5d1c…521f` (572,962 bytes).
- **VPB source-row Excel:** `output/development/vpb-q1-2026-native-rows-v1/vpb-q1-2026-native-rows.xlsx` (SHA-256 `a304040c32238d22d485fe97723d147fb935817a2ed2e5ad6d74eb19c78ddb04`, 81,988 bytes) and paired provenance JSON (SHA-256 `d9cdc9653ec357903b27dc0fa2ef3eceb56a8b02fe4480d7a9035e064c27775e`, 7,301 bytes). Both rebuild byte-identically; the workbook contains `PAGES`, `ROWS`, `CELLS`, `HEADERS` and `RUN_METADATA`, with zero formulas and no schema projection.
- **VPB canonical mapping:** `output/development/vpb-q1-2026-native-canonical-v1/canonical-mapping.json` (SHA-256 `94d24bdc307101f0024a18e72cd94100fecb937e525dfbca37baa622d7475597`, 5,050,201 bytes). Its post-publication strict replay accounts for `134/134 = 127 EXISTING_ITEM + 3 NEW_ITEM_PROPOSAL + 3 STRUCTURAL + 1 UNRESOLVED` and allocates no ReportNormId.
- **VPB mapped Excel:** `output/development/vpb-q1-2026-native-canonical-v1/vpb-q1-2026-canonical-mapped.xlsx` (SHA-256 `ae1430a5550d7166cbbd1fd213f3e15d3b9d7d35abafb070d2e09fd545c5503c`, 764,014 bytes) and paired provenance JSON (SHA-256 `a3b39fec85d6d57154d9c180f88fb8f7b694e8819e7db638e26119baa418e412`, 10,470 bytes). The strict completed-pair loader reloaded both trusted hashes, revalidated the producer mapping/row artifacts and rebuilt the pair byte-for-byte. Its six sheets are `SOURCE_ROWS`, `CELLS`, `SCHEMA_COVERAGE`, `NEW_ITEM_PROPOSALS`, `VALIDATION` and `RUN_METADATA`; the full 1,933-item producer schema is represented with zero formulas, imputation or automatic ID allocation.
- **VPB quantitative-TM mechanism:** local-region policy SHA-256 `be1b87ca…689c`, implementation SHA-256 `d8cb5b7a…3142`; TM-context policy SHA-256 `9c7989fa…98f`, projection SHA-256 `f2874a66…ef6f`. The registered source-only artifact is `output/development/vpb-q1-2026-native-tm-document-v1/native-tm-document.json` (SHA-256 `ab6f9e2c622c0801ef31c4fc630d183ba940bf06e6379be11e8adafc7d60b21a`, 11,893,305 bytes), built and strict-replayed from producer commit `7927bac5f24335ba9c1a373b89f326f196ad64bf`. It is correctly `PARTIAL`: all 91 pages are classified and all 91 quantitative regions are assessed, with zero unresolved tables, but 30 inter-table contexts remain unresolved. No canonical TM observation or mapped Excel is claimed by this source-inventory milestone.
- **Latest sealed version:** E-0041 CDKT workbook/provenance pair. No new E-version is planned for ordinary coverage expansion.
- **TM development artifacts:** `output/development/mbb-q1-2026-tm-consolidated-v2/mbb-q1-2026-consolidated-tm-development.xlsx` (SHA-256 `f41d4179ff1142537d624076eb1771c4454842ef740b42e6723ae910143ada20`) and paired provenance JSON (SHA-256 `ebf605b6b9d992b0465d6d7234ae3bf8877824be3147f023d455455a4fba1339`). Three builds using independent verified cache paths are byte-identical. The prior v1 artifact remains preserved and is not overwritten.
- **Regression status:** the latest recorded pre-6054 full milestone suite passes **1,285/1,285** in **4,154.04 seconds (1:09:14)**. On final 6054 bytes, the independently rerun schema/page-5/consumer suite passes **32/32** and the native row/mapper/exporter/CLI suite passes **68/68**; the canonical mapper itself has 24 focused checks and the paired exporter has 10. The new native-TM region suite passes **89/89** against the real 91-page VPB source; combined document-artifact, region and TM-context tests pass **139/139**, and the complete changed-file suite including core text passes **156/156**. Two independent all-page render-identity passes are byte/digest-stable with 17,935 RAW spans, 22,614 positive-area text paints owned exactly once, 36,956 retained words and 51 exclusions. Deterministic migration verify-only, strict producer-commit replays, Ruff/scoped-format, compile and diff checks pass. Historical frozen consumers remain bound to their exact Git snapshots and are not rewritten merely to absorb later CLI or algorithm hashes.
- **Publication status:** universal-schema/source-driven commit `2fdb939` and native-TM producer commit `7927bac` are pushed on `codex/rebuild-bootstrap`. The VPB canonical JSON, mapped Excel/provenance pair and source-only native-TM artifact above were produced from their clean commits and accepted by their strict post-publication loaders.
- **Biggest remaining blocker:** the VPB TM source grid is now reconstructed, but universal identity matching is unsafe without note/table/subtree context: the 1,701-item TM schema has only 640 unique normalized labels, 154 colliding keys cover 1,215 items, and one key occurs 49 times. VPB also still has the non-blocking main-statement questions `Q074`–`Q075`, while CTG's combined-swap subtotal remains `Q076`.
- **Exact next end-to-end step:** build the quantitative-TM source-row/observation contract and context-partitioned mapper. Coverage may declare `NOT_OBSERVED` only inside an independently complete table/note subtree (or a complete full-document inventory), never from selected pages or a global label match.

## 5. Overall status

```text
Current end-to-end status:
PDF → page → row/cell → OCR → mapping → validation → Excel

Completed through: source-complete MBB item reconstruction including page-5 off-balance data; universal schema 1,933; deterministic mapped MBB Excel; full-document VPB statement discovery; source-faithful main-statement Excel and 134/134 canonical dispositions; source-only VPB TM full-page classification and a bounded 694-row/2,163-observation quantitative table-region denominator, with the full-document artifact still partial on 30 inter-table contexts
Currently working on: quantitative VPB TM source-row observations and context-partitioned canonicalization
Not yet completed: mapped VPB TM observations/Excel, three pending source-driven schema decisions, broad independent multi-bank/period verification and continued universal-schema growth
Production approved: NO
```
