# Current status — scalable bank-PDF BCTC digitization

Updated: 2026-08-09

## 1. Breadth-first corpus strategy and generalization KPI

The project has switched from bank-by-bank depth-first completion to breadth-first corpus learning. The objective is one scalable system for `PDF → visible source structure → accounting identity or evidenced schema extension → validation → structured data/Excel`. The supplied schema is formally `BASE_SCHEMA`: a valuable initial ontology, not a closed answer set. Source PDFs are surveyed before schema comparison, and genuine source items are never forced into an existing ID merely because the current schema lacks them.

MBB and VPB outputs are frozen as development/regression evidence. Exhaustive VPB TM identity-by-identity completion is explicitly **paused** at the current safe checkpoint. Its 30 unresolved inter-table contexts and remaining mappings stay in the regression corpus, but they no longer define the project queue.

The first breadth-first inventory is now reproducible:

- Registered corpus: **27 banks**, **2,567 registered PDF paths**, **2,435 unique PDF contents**, **17,761,344,114 bytes**. The 132 extra paths are duplicate-content registrations. These paths include language/revision companions and supporting disclosures, so they are not claimed as 2,567 independent filings.
- Metadata inventory: `output/development/bank-corpus-survey-v1/corpus-inventory.json` (SHA-256 `fff64ca4d25de646cd2f4661d99fc9623e6edc8c7c6b0cd321c0d2f9af9cebd8`, 2,181,864 bytes).
- Wave 1: exactly one source-first representative per bank, selected before inspecting PDF source type. The locked filename-derived, non-authoritative composition is 23 comparable Vietnamese consolidated Q2/2026 documents, one Vietnamese separate Q2/2026 fallback, two Vietnamese Q2/2026 filings whose filename does not encode scope, and the preserved VPB development input after all preferred metadata tie. No `UNTOUCHED_HOLDOUT`, schema, mapping answer, historical value, or PDF-ease signal participates in selection.
- Page/source-route profile: `output/development/bank-corpus-survey-v1/wave-1-source-profile.json` (SHA-256 `28fb3485b9424e2052ae981942476e681d8fbdcbf1131467a1d65778a20cb19b`, 857,274 bytes). It accounts **1,449/1,449 pages** and recommends 11 scan routes, 14 mixed/page-hybrid routes, one searchable-over-image route requiring ghost-text validation, and one native/searchable route. These are extraction-route candidates, not accounting identities or completed structural surveys.

| Corpus/generalization KPI | Current evidence |
| ------------------------- | ---------------- |
| Banks registered | 27 |
| Banks selected / source-route profiled | 27 / 27 |
| Banks structurally surveyed under the new pass | 0 / 27; this is the next active phase |
| Documents selected / source-route profiled | 27 / 27 |
| Period coverage in the locked filename metadata | 26 Q2/2026; 1 filename-unknown preserved VPB input (known from its existing source receipt as Q1/2026) |
| Reporting periods source-verified by the new structural pass | 0; the 26 Q2/2026 + 1 unknown split above is filename metadata only |
| Scope hints | 24 consolidated; 1 separate; 2 unknown; filename-derived and non-authoritative |
| Source route candidates | 11 scan; 14 mixed/hybrid; 1 searchable-over-image; 1 native/searchable |
| Wave-1 PDF pages profiled | 1,449; 1,356 have a raster covering at least 50% of the page |
| Extractable text-layer evidence | 156 substantive pages; 111 have substantive nonzero-alpha text and 46 have substantive zero-alpha text; the latter sets overlap on one page and visibility/render validation is still `NOT_RUN` |
| Statement blocks / visible rows / visible cells source-accounted by the new survey | 0 / 0 / 0; source-route profiling is not mislabeled as structural extraction |
| Universal schema items | 1,935 |
| New identities / aliases this wave | 0 / 0; schema comparison has not begun for Wave 1 |
| Unresolved schema gaps | Not yet measured for Wave 1 |
| Structural archetypes discovered / handled generically | 0 / 0 formally registered in Wave 1; discovery is pending the structural pass |
| Wave-1 documents reaching source-complete extraction / canonical mapping / mapped Excel | 0 / 0 / 0; MBB and VPB below are carry-in regression evidence, not new Wave-1 coverage |
| Unresolved source rows / mapping rows | Not yet measured for Wave 1; never represented as zero |
| Role A references | 3 existing hash-bound references: CTG Q2/2026, ACB Q2/2026, MBB Q1/2026; corpus-level human-review/holdout coverage is not yet sufficient |
| Human-reviewed document benchmarks | Not yet measured; no corpus-level review registry exists, and Role A or user schema decisions are not relabeled as human-reviewed document gold |
| Independent holdout coverage | 1 registered ACB Q1/2026 paired holdout suite / 2 immutable `UNTOUCHED_HOLDOUT` source paths; same-filing linkage is filename-derived, both paths are excluded from Wave 1, and the Role-A diagnosis is machine reference rather than human gold |

Initial corpus-level risk/pending-failure queue (no extraction-failure frequencies have been measured yet; row/table counts will replace these route counts after structural survey):

| Failure class | Current affected documents | Risk / next generic mechanism |
| ------------- | -------------------------: | ----------------------------- |
| Raster-dominant scan extraction | 11 | High financial-cell risk; use page-level OCR/detection plus source accounting |
| Mixed native/image routing | 14 | Prevent cover-page text or partial text layers from selecting the wrong reader |
| Searchable-over-image / ghost text | 1 primary case (HDB), with additional zero-alpha evidence retained elsewhere | Validate render visibility before trusting hidden text |
| Statement/table/archetype discovery across new layouts | 27 pending | Build source-driven fingerprints, then cluster common and new structures |
| Duplicate TM labels and unresolved boundary ownership | Carry-in VPB regression | Solve by note/table/subtree context after cross-bank archetypes are known; do not global-match labels |

**Current highest-impact generic blocker:** reliable statement/table/row/cell source accounting for the 26 raster-dominant or hybrid Wave-1 documents. **Next generic improvement:** apply page-level native/scan/mixed routing, detect financial-statement blocks source-first, emit document structure fingerprints, and aggregate failure classes across all 27 banks before changing mapping logic.

## 2. Universal schema and per-document coverage

The original supplied 1,593-item reference is frozen as `BASE_SCHEMA` (`77 CDKT + 24 KQKD + 107 LCTT + 1,385 TM`). The active source-evidenced superset is `UNIVERSAL_BANK_BCTC_SCHEMA@6056`: `1,935 = 99 CDKT + 25 KQKD + 110 LCTT + 1,701 TM`. It contains the base identities plus exactly 342 audited, append-only additions; ReportNormId never defines display order. The ordered universal projection is `7c11a91b…e95b9` and the content-addressed graph/schema hash is `2262c4c0…e770`.

| Statement | Universal items | Visible MBB source | Base identities mapped | Post-base additions (mapped / NO) | Source ambiguity | Source rows accounted |
| --------- | --------------: | -----------------: | ---------------------: | --------------------------------: | ---------------: | --------------------: |
| CDKT | 99 | 75 rows / 150 cells | 59 | 22 (14 / 8) | 0 | 75/75 |
| KQKD | 25 | 22 rows / 88 cells | 21 | 1 (1 / 0) | 0 | 22/22 |
| LCTT | 110 | 43 rows / 86 cells | 41 | 3 (2 / 1) | 0 | 43/43 |
| TM | 1,701 | 553 logical source rows / 1,659 visible value-status slots | 583 | 316 (306 / 10) | 0 | 553/553 |

The ten post-base TM identities classified `NOT_OBSERVED` are preserved accepted identities in structurally completed universal branches; they are not claimed as visible MBB rows and are not treated as extraction failures.

Exact reconciliations:

- CDKT: `99 = 73 MAPPED + 26 NOT_OBSERVED + 0 UNRESOLVED`. Main-statement provision rows are owned by the broader, source-exact identities `6035` and `6036`, while the older narrower `4347` and `4352` remain distinct and are not observed. MBB page 5 independently maps the consolidated off-balance branch `6038`–`6048`; `6037`, `6049`–`6053`, and the source-absent subtotals `6055`/`6056` are not observed. Quantitative-note links remain explicit provenance and never silently backfill main-statement observations.
- KQKD: `25 = 22 MAPPED + 3 NOT_OBSERVED_IN_THIS_PDF`.
- LCTT: `110 = 43 MAPPED + 10 NOT_OBSERVED_IN_THIS_PDF + 57 SCHEMA_ITEM_NOT_APPLICABLE`.
- TM quantitative pages 30–54 and 57–61: `1,701 = 889 MAPPED + 789 NOT_OBSERVED_IN_THIS_PDF + 23 NOT_APPLICABLE + 0 AMBIGUOUS/UNRESOLVED/UNASSESSED`. Pages 55–56 and 59 are narrative-only. The complete TM schema has one explicit, pairwise-disjoint disposition per ID; visible class/measure axes remain provenance rather than false row identities.

The preserved VPB regression baseline is source-captured independently of schema matching:

| VPB Q1/2026 source block | Pages | Visible rows | Visible cells | Current extraction status |
| ------------------------ | ----: | -----------: | ------------: | ------------------------- |
| CDKT main statement | 5–6 | 59 | 110 | 110 `OBSERVED_VALUE` |
| CDKT off-balance statement | 7 | 16 | 32 | 32 `OBSERVED_VALUE`; retained in a separate universal `OFF_BALANCE_SHEET` branch and excluded from main-statement totals |
| KQKD main statement | 8 | 25 | 50 | 49 `OBSERVED_VALUE` + 1 `DASH` |
| LCTT main statement | 9–10 | 34 | 60 | 58 `OBSERVED_VALUE` + 2 `DASH` |
| **Total** | **5–10** | **134** | **252** | **249 values + 3 dashes; 134/134 rows source-accounted** |

The current `@6056` VPB main-statement mapping logic accounts for all `134/134` visible rows as `131 EXISTING_ITEM + 3 STRUCTURAL + 0 NEW_ITEM_PROPOSAL + 0 UNRESOLVED`. Q074/Q077/Q078 broaden the existing names of `4360`, `4319` and `4136` to include TCTC and retain their narrower TCTD-only aliases. Q075 adds `6055 Tổng chỉ tiêu ngoại bảng`, mapped to the terminal unlabeled VPB total only after unique topology plus exact every-axis equations establish `6055 = 6039 + 6050`. Q076 adds `6056 Cam kết giao dịch hoán đổi` below `6041`, after `6043`, with `6044`/`6045` as its children. The previously published VPB main-statement JSON/Excel pair remains a byte-frozen historical `@6054` result and has not been republished as an `@6056` artifact.

VPB's quantitative-TM table-region denominator is now bounded independently of schema mapping. Across the core report-period notes on PDF pages 38–91, 45 pages contain 91 accepted local native-text table regions with `694` value-bearing logical rows and `2,163` visible observations: `2,149` numeric/zero/dash observations (2,145 table cells plus four row-local scalar disclosures) plus 14 explicit `(*)` unavailable-fair-value markers. Narrative/qualitative pages, row-local scalar disclosures, rows outside the financial span, inter-table contexts and unassigned source runs remain explicit. All 91 PDF pages are classified, but 30 inter-table contexts still have unresolved ownership, so the registered full-document artifact remains `PARTIAL` and cannot authorize document-wide absence claims. The visible-text gate excludes exactly 51 non-authoritative native spans (50 hidden white ghosts plus the page-78 ToUnicode/render mismatch) without changing the 694/2,163 denominator.

The receipt-bound observation layer exhaustively flattens that artifact into 91 pages, 97 contexts, 934 rows, 265 dimensions and 2,523 observation positions, while giving exactly one disposition to each of 11,032 source objects. Its `COMPLETE_NATIVE_TM_SOURCE_OBJECT_ACCOUNTING` status means complete accounting of the inherited source inventory; it does not upgrade the upstream document beyond `PARTIAL`. The first conservative canonical pass accepts one independently complete bounded subtree rooted at TM ID `561`: eight canonical observations resolve four IDs as `OBSERVED_VALUE`, four sibling IDs are `NOT_OBSERVED`, and the other 1,693 TM identities remain explicitly `UNRESOLVED`. Exact disposition accounting is complete for all 1,701 TM IDs and all 11,032 source objects, but document-wide mapping is not.

The universal TM graph also has a source-independent context projection for all 1,701 identities. `1,686` connected items have consistent section/ancestor/level context and are mapping-eligible; IDs `785`–`791` and `793`–`799` are quarantined for declared-versus-derived hierarchy-level mismatch, and orphan ID `1944` remains ineligible until its parent/identity context is resolved. This context does not map source rows by bank, page or note number.

“Observed” means physically identified PDF rows/cells. “Mapped” means assigned to an existing or newly accepted canonical ReportNormId. `DASH`, `BLANK`, `OBSERVED_ZERO`, `NOT_OBSERVED`, and `NOT_APPLICABLE` remain distinct. “Fully verified” still requires independent authority for the complete item/value/status/period/unit/scope/Excel tuple; no item is promoted to that stronger claim here.

## 3. Current technology/logic pipeline

```text
PDF
→ page/document native / scan / mixed evidence routing
→ authoritative visible native text where available, otherwise OCR/detection
→ source-first statement/page/table discovery
→ logical row/cell, wrapped-label and continuation reconstruction
→ DeepSeek-OCR-2 / VietOCR label corroboration where configured
→ signed numeric parsing + independent PDF-text or render-pixel DASH evidence
→ visible-header period, unit and consolidated/separate-scope binding
→ local accounting hierarchy + reusable structural archetype
→ only then compare against the evolving universal SchemaGraph
→ reuse an equivalent canonical identity OR add an evidenced missing identity
→ accounting equations without repairing source values
→ deterministic structured canonical data + suitable Excel + provenance
```

All four statement groups use the versioned universal schema. TM uses note-specific geometry because its tables vary materially by page; percentage, class/geography and other auxiliary axes stay in provenance unless they are genuine accounting-row identities. Qwen is not in the active path.

The VPB TM source stage adds a generic local-region layer rather than widening the main-statement row adapter. It uses visible PyMuPDF native text, causal RGB render evidence, table-local axes, explicit grid slots, row/scalar/context ownership and full-page evidence partitioning. Callback-bound glyph paint identity separates geometry from language/schema meaning; weak-but-visible, chromatic and nonopaque text is retained, while hidden, materially occluded or overlapping text fails closed. The registered full-document wrapper trusts only the accepted statement-discovery notes boundary, classifies every PDF page, snapshots all source/config/code identities, and has no schema or historical-value input.

The next receipt-bound stages flatten every inherited native-TM source object, then map only families supported by globally unique exact direct-child anchors and an independently complete local table topology. Arithmetic is a post-lineage corroboration/veto, never a selector. The dedicated six-sheet exporter replays the mapping and observation producer snapshots, authenticates their transitive native-document/PDF/discovery lineage, uses the embedded producer schema snapshot, and emits no formulas, imputation or forced assignments.

The active development loop is now corpus-driven: survey many documents, fingerprint source structure, cluster archetypes and failure classes, improve the highest-impact generic mechanism, replay the affected corpus, and measure generalization. Bank names remain evidence/debug metadata and are not parser-routing conditions.

## 4. Role A / Role B status

- **Role A:** hash-bound references exist for CTG Q2/2026, ACB Q2/2026 and MBB Q1/2026. Role A must preserve every genuine visible row and may emit `POSSIBLE_SCHEMA_GAP`; it is not limited to BASE_SCHEMA. The active universal registry has 1,935 unique items.
- **Role B:** MBB Q1/2026 reaches development Excel for all four statements. TM parsing/mapping covers every quantitative note page through the end of the 61-page PDF; cross-page totals remain validation-only and never create duplicate ownership. The consolidated TM workbook and its paired provenance JSON are deterministic and preserve exact value, zero, dash and blank semantics.
- **Active breadth-first Role B development:** all 27 registered banks now have one locked Wave-1 document and a page-level source-route profile. The next pass detects source-visible statement blocks, tables, axes, rows and cells without consulting expected schema rows. Incomplete mappings are allowed; lost source evidence is not.
- **Preserved VPB regression evidence:** VPB consolidated Q1/2026 remains an immutable `LOGIC_DEVELOPMENT` input, not holdout/validation evidence. Full-document native-text discovery independently selected CDKT pages 5–7, KQKD page 8, LCTT pages 9–10 and the first TM boundary at page 11. The generic main-statement adapter reconstructed all 134 rows and 252 cells. The source-only TM stage accounts the 694-row/2,163-observation quantitative core and all 11,032 source objects; the first bounded canonical family reaches Excel with eight observations. The 30 unresolved inter-table contexts remain explicit, and further identity-by-identity VPB completion is paused until cross-bank archetypes justify generic improvements.
- **Latest corpus result:** Wave 1 profiles 27 documents and 1,449 pages without source-type cherry-picking: 11 scan, 14 mixed/hybrid, one searchable-over-image and one native/searchable route candidate. This is a page-routing-profile milestone, not a completed document-structure fingerprint or canonical coverage.
- **Carry-in measurable results:** the established MBB baseline exports 132 observed plus 2 derived CDKT values from 75 rows/150 physical statuses; KQKD has 88/88 numeric cells independently matched and 32/32 accounting checks passed; LCTT exports 71 values, 9 dashes and 6 blanks. MBB TM has 889 mapped schema identities across 553 logical source rows and 1,659 parser-declared visible value/status slots. The VPB native-TM workbook represents all `1,701` schema dispositions and `11,032` source-object dispositions: `4 OBSERVED_VALUE + 4 NOT_OBSERVED + 1,693 UNRESOLVED`, with eight canonical observation rows, 11,037 physical `SOURCE_OBJECTS` sheet rows, four validation rows, zero formulas and zero imputed values.

## 5. Current development position

- **Completed mapped baseline:** MBB consolidated Q1/2026; snapshot statements compare 31/03/2026 with 31/12/2025, duration statements compare Q1/2026 with Q1/2025; reported unit is generally VND × 1,000,000.
- **Active corpus-survey input:** the exact 27-document Wave-1 selection is bound by selection receipt SHA-256 `832cea1bee22f0bb08c422490dd2afe4e23bc91c56cdee6db382b1bfdc744d28` (7,665 bytes; 248,588,591 selected PDF bytes). The inventory/source-profile implementation is pushed at commit `81bec8431f3db00d4f92b2bb452367d17b954d9b`; both published JSON artifacts rebuild byte-for-byte.
- **Preserved VPB input:** consolidated Q1/2026, source SHA-256 `614be887…dcde`, immutable role `LOGIC_DEVELOPMENT`. Discovery artifact SHA-256 is `ddeaabd0…aaa9`; registered row artifact SHA-256 is `fa1c5d1c…521f` (572,962 bytes).
- **VPB source-row Excel:** `output/development/vpb-q1-2026-native-rows-v1/vpb-q1-2026-native-rows.xlsx` (SHA-256 `a304040c32238d22d485fe97723d147fb935817a2ed2e5ad6d74eb19c78ddb04`, 81,988 bytes) and paired provenance JSON (SHA-256 `d9cdc9653ec357903b27dc0fa2ef3eceb56a8b02fe4480d7a9035e064c27775e`, 7,301 bytes). Both rebuild byte-identically; the workbook contains `PAGES`, `ROWS`, `CELLS`, `HEADERS` and `RUN_METADATA`, with zero formulas and no schema projection.
- **VPB main-statement canonical mapping (historical `@6054` artifact):** `output/development/vpb-q1-2026-native-canonical-v1/canonical-mapping.json` (SHA-256 `94d24bdc307101f0024a18e72cd94100fecb937e525dfbca37baa622d7475597`, 5,050,201 bytes). Its post-publication strict replay accounts for `134/134 = 127 EXISTING_ITEM + 3 NEW_ITEM_PROPOSAL + 3 STRUCTURAL + 1 UNRESOLVED`. Those dispositions truthfully describe the frozen producer snapshot; current `@6056` logic resolves Q074–Q078, but this old artifact was not relabeled or republished.
- **VPB main-statement mapped Excel (historical `@6054` artifact):** `output/development/vpb-q1-2026-native-canonical-v1/vpb-q1-2026-canonical-mapped.xlsx` (SHA-256 `ae1430a5550d7166cbbd1fd213f3e15d3b9d7d35abafb070d2e09fd545c5503c`, 764,014 bytes) and paired provenance JSON (SHA-256 `a3b39fec85d6d57154d9c180f88fb8f7b694e8819e7db638e26119baa418e412`, 10,470 bytes). The strict completed-pair loader reloaded both trusted hashes, revalidated the producer mapping/row artifacts and rebuilt the pair byte-for-byte. Its six sheets are `SOURCE_ROWS`, `CELLS`, `SCHEMA_COVERAGE`, `NEW_ITEM_PROPOSALS`, `VALIDATION` and `RUN_METADATA`; the full 1,933-item producer schema is represented with zero formulas, imputation or automatic ID allocation. It remains preserved as historical evidence, not a current `@6056` publication.
- **VPB quantitative-TM source inventory:** local-region policy SHA-256 `be1b87ca…689c`, implementation SHA-256 `d8cb5b7a…3142`; TM-context policy SHA-256 `9c7989fa…98f`, projection SHA-256 `f2874a66…ef6f`. The registered source-only artifact is `output/development/vpb-q1-2026-native-tm-document-v1/native-tm-document.json` (SHA-256 `ab6f9e2c622c0801ef31c4fc630d183ba940bf06e6379be11e8adafc7d60b21a`, 11,893,305 bytes), built and strict-replayed from producer commit `7927bac5f24335ba9c1a373b89f326f196ad64bf`. It is correctly `PARTIAL`: all 91 pages are classified and all 91 quantitative regions are assessed, with zero unresolved tables, but 30 inter-table contexts remain unresolved. Downstream artifacts may make bounded claims; they do not change this source-inventory status or authorize document-wide absence.
- **VPB native-TM observations:** `output/development/vpb-q1-2026-native-tm-observations-v1/native-tm-observations.json` (SHA-256 `0ca14b8c1851e6910a482f8bbc9530119f0789d3c7c90d4945d8220850f2bb95`, 24,339,561 bytes). Strict loading and producer replay account for 91 pages, 97 contexts, 934 rows, 265 dimensions, 2,523 observations and exactly 11,032 source dispositions. `COMPLETE_NATIVE_TM_SOURCE_OBJECT_ACCOUNTING` is an exhaustive flattening/accounting claim over the accepted upstream inventory, not a full-document context-completion claim.
- **VPB native-TM canonical mapping:** `output/development/vpb-q1-2026-native-tm-canonical-v1/native-tm-canonical-mapping.json` (SHA-256 `52c641042fac8ec6a827d0e09b86fdd00fc4e7709f906626a0733af2a3fdf307`, 11,763,806 bytes). Its clean producer is `53ac4367ff1b2cff24f23df1bdf7e804ed60bdfa`. The strict result has 8 canonical observations, all 1,701 schema dispositions and all 11,032 source dispositions. Schema outcomes are `4 OBSERVED_VALUE + 4 NOT_OBSERVED + 1,693 UNRESOLVED`; source dispositions are `12 MAPPED_EXISTING_ITEM + 18 ASSESSED_BOUNDED_SUBTREE + 2 ASSESSED_SUPPORTING_DIMENSION + 11,000 UNRESOLVED`. `COMPLETE_NATIVE_TM_CANONICAL_DISPOSITION_ACCOUNTING` means every denominator member has a disposition, not that every member is mapped.
- **VPB native-TM mapped Excel:** `output/development/vpb-q1-2026-native-tm-canonical-excel-v1/native-tm-canonical.xlsx` (SHA-256 `3cf28353be6777caa5ce6643622e18747f75cb51757a4f817edf629d0e5ca87c`, 5,476,052 bytes) and paired `provenance.json` (SHA-256 `ab929a4122e5f2192fce0ba45b4781dfcdaadddd05246791740f7344c62b063a`, 20,687 bytes). Its six sheets are `CANONICAL_OBSERVATIONS`, `SCHEMA_DISPOSITIONS`, `SOURCE_DISPOSITIONS`, `SOURCE_OBJECTS`, `VALIDATION` and `RUN_METADATA`. The receipt-bound exporter represents 8 canonical observations, 1,701 schema dispositions, 11,032 logical source objects across 11,037 sheet rows, and 4 validation records, with zero formulas and zero imputed values; strict loading replays the mapping and observation producers and authenticates the native-document/PDF/discovery lineage.
- **Latest sealed version:** E-0041 CDKT workbook/provenance pair. No new E-version is planned for ordinary coverage expansion.
- **TM development artifacts:** `output/development/mbb-q1-2026-tm-consolidated-v2/mbb-q1-2026-consolidated-tm-development.xlsx` (SHA-256 `f41d4179ff1142537d624076eb1771c4454842ef740b42e6723ae910143ada20`) and paired provenance JSON (SHA-256 `ebf605b6b9d992b0465d6d7234ae3bf8877824be3147f023d455455a4fba1339`). Three builds using independent verified cache paths are byte-identical. The prior v1 artifact remains preserved and is not overwritten.
- **Regression status:** the breadth-first inventory/profile suite passes **8/8** on the hydrated 27-document set, including exact 1,449-page accounting, source-route partition and ghost/inline-image sentinels; both JSON artifacts rebuild byte-for-byte. The latest recorded pre-6054 full milestone suite passes **1,285/1,285** in **4,154.04 seconds (1:09:14)**. On final 6054 bytes, the independently rerun schema/page-5/consumer suite passes **32/32** and the native row/mapper/exporter/CLI suite passes **68/68**; these figures remain historical milestones. For the current native-TM chain, the canonical mapper suite passes **92/92**, its related suite passes **81/81**, and the native-region suite passes **89/89** against the real 91-page VPB source. The receipt-bound Excel exporter passes **43/43**, and its independent related canonical-XLSX/native-document/observations/mapper run passes **152/152**; the published pair also passes an independent producer-commit strict load and direct workbook/receipt audit. Deterministic schema migration checks, clean producer-commit replays, strict post-publication loads, byte-identical rebuilds, Ruff/scoped-format, compile and diff checks pass. Historical frozen consumers remain bound to their exact Git snapshots and are not rewritten merely to absorb later schema, CLI or algorithm hashes.
- **Publication status:** breadth-first corpus inventory/profile implementation `81bec84`, Q074–Q078 schema update `88367a2`, native-TM observation implementation `e94286f`, canonical mapper `53ac436`, and receipt-bound Excel exporter `e3f356a` are pushed on `codex/rebuild-bootstrap`; the earlier source-inventory producer `7927bac` also remains in their ancestry. The two corpus JSONs and the native-TM document, observations, canonical mapping and Excel/provenance pair above were produced from clean commits and accepted by byte-exact rebuild or their strict post-publication loaders. The historical `@6054` main-statement pair remains preserved and was not republished.
- **Highest-impact generic blocker:** 26/27 Wave-1 PDFs require scan, hybrid, or searchable-over-image handling, while no new Wave-1 statement block/table/row/cell has yet been source-accounted. The priority is reliable source reconstruction across these layout families, not the remaining identity count of one bank.
- **Exact next corpus step:** run source-driven statement detection and structural fingerprinting across all 27 Wave-1 documents; emit statement sequence, scope/period/unit evidence, LCTT method, table/axis/topology signatures and source row/cell counts; then cluster table archetypes and failure classes. Only afterward should generic extraction/mapping changes be prioritized and replayed across affected banks. The VPB 30-context issue remains a regression case rather than the active queue head.

## 6. Overall status

```text
Current end-to-end status:
PDF → page → row/cell → OCR → mapping → validation → Excel

Completed through: preserved source-complete MBB development baseline; universal schema 1,935 at @6056 with Q074–Q078 resolved; preserved VPB main-statement and bounded native-TM source/mapping/Excel evidence; exact registered inventory of 27 banks / 2,567 PDF paths; locked 27-document Wave 1; reproducible page-level source-route profiles for all 1,449 Wave-1 pages
Currently working on: source-first structural survey across all 27 banks—statement blocks, table regions, axes, logical rows/cells, hierarchy signatures, document fingerprints, archetype clustering and corpus-level failure classes
Paused regression work: exhaustive VPB TM identity-by-identity completion; the 30 unresolved contexts and partial canonical coverage remain preserved for later corpus-driven replay
Not yet completed: Wave-1 source-accounted statement/table/row/cell inventories; cross-bank archetype registry; corpus failure/schema-gap/alias registries; generic replay metrics; broad bank/period/scope holdout verification; scalable unseen-filing canonicalization
Production approved: NO
```
