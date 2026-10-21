# PRIMARY statements (CDKT / KQKD / LCTT) — ledger and hand-off, 2026-10-21

Owner: Claude (worker `CLAUDE_PRIMARY`, claim scope `PRIMARY_STATEMENTS`).
Branch `codex/primary-statements-claude`, worktree `D:\bctc_bank\bctc-primary-claude`.
Base `d0e9079be72e74ecddde145e7f575a9defa8c1b5` (migration base `8efd618b…` is an ancestor).
Product label of every workbook: **PRIMARY_ONLY** — the notes (TM) are not
included, the workbook is not the complete BCTC product, and no TM family is
marked NOT_OBSERVED.

## 1. What was built

Pipeline from the authenticated stored Gemini JSON selection to SQLite and
Excel, the same code for every bank (no bank/file/page/value routing):

| Stage | Module | Key rules |
| --- | --- | --- |
| Source | `source_v1` | Corpus index/DB SHA pinned; selection authenticated; page JSON read through the read-only F39 loader; census SQL + section titles |
| Classification | `assembly_v1.classify_table_v1` | Discriminative content fingerprints + statement titles; notes boundary; note tables never primary |
| Assembly | `assembly_v1` | Continuations merged only for same statement/scope/axes; restart detection; fragment merge; TEXT/code columns are not ancestry |
| Scope | `resolve_instance_scope_v1`, `resolve_document_scope_v1` | Printed title / form code (B0xa/TCTD[-HN]); document-level propagation from a proven statement; explicit absence after full title scan; contradictions veto |
| Units | `units_v1` | Only printed unit phrases (header, unit field, "Đơn vị/ĐVT" prose); never from magnitude |
| Periods | `periods_v1` | Printed dates/ranges/quarters; symbolic `PRIOR_YEAR_OF`, `END_OF_QUARTER`, `OPENING_OF_FISCAL_YEAR`; quarter vs YTD distinct; no year-minus-one; per-table header reading (a table naming one period twice is held, not voted); report-date binding only with quarter agreement |
| LCTT branch | `resolve_cash_flow_branch_v1` | Ordered RNID anchors from `config/mapping/lctt-v2.yaml`; both/neither ⇒ hold |
| Mapping | `mapping_v1` + `config/primary_statements/catalog_v1.yaml` | Registry IDs/hierarchy; constrained aliases (ancestor/section/top-level/order); order-bracketed lexical match with margin; duplicate targets ⇒ UNRESOLVED (no first/last wins); duplicate presentations retired only with a cell-level precision proof |
| Validation | `validation_v1` + `config/primary_statements/equations_v1.yaml` | Registry parent/child formulas from observed values only; declared pure/reversible deductions; rounding tolerance only for ≥ million units; incomplete frontier reported separately; declared alternative membership; checks veto, never create values |
| Result | `result_v1` | Per-cell acceptance with hold reasons; write key (document, scope, statement, period, ReportNormId); collisions held |
| Store | `store_v1` | Write-once SQLite (STRICT, FK, unique accepted write key); reload replay and tamper detection |
| Excel | `excel_v1` | Template rows in DisplayOrder; values as exact text policy where needed; PROVENANCE / SOURCE_ROWS / VALIDATION sheets; reopen and compare every value cell, type, unit, period and provenance link; no formulas |

Run: `scripts/primary_statements/run_primary_statements_v1.py --corpus full271|common204 --output-dir NEW --git-head SHA --verify-db-bytes`
(store → reload → fresh-process independent rebuild from source → workbooks with exact readback).

## 2. Gates

Evidence code: commit `9b928a6032fc434072a9bfa833d50b73c41bbd9e`, code closure
`620fef69038961181209ec90618bd24cefd25f82f7309f33e3b8fbf323ac888d`
(catalog `9d3f0848…`, equations `8002bb29…`, lctt-v2 `d07908e9…`). Later
commits on the branch add only docs, the artifact uploader and the post-commit
form of the preflight git gate; none is in the run code closure.

| Gate | full271 | common204 |
| --- | --- | --- |
| Preflight (git/base, import origin, schema/template pins, frozen SHAs, corpus index/DB SHA, SQLite quick_check/FK, PDF coverage + rehash, inventory pin, no provider job) | PASS 12/12 (`preflight-*.json`) | (same receipt) |
| Store write, `quick_check` ok, 0 FK violations | PASS, sha `4314ddc2fd33cc5d6b4530dfb6dc98cfe5946f39001038614748a8a4974ed95d` | PASS, sha `0f7e7c5541b5708dfcb8153a1aa9db8bf2e92d4c67285a0543f260f71ff41cb5` |
| Reload replay | PASS_EXACT 271/271 | PASS_EXACT 204/204 |
| Independent fresh-process rebuild from selected original JSON | PASS_EXACT_RESULT_IDS 271/271 (ids sha `871979c7…`) | PASS_EXACT_RESULT_IDS 204/204 (ids sha `d6d70726…`) |
| Workbooks reopened, exact readback | 271 PASS_EXACT_READBACK, 74,354 value cells, 0 formulas | 204 PASS_EXACT_READBACK, 0 formulas |
| Cross-corpus (204 shared PDFs) | 200 documents cell-identical; 55,797 cells identical; 11 cells differ, all in 4 documents whose two corpora select different page JSON versions (raw `-` vs ` -`, `-` vs blank) | — |
| PDF audit | 12/12 sampled accepted cells (one per bank × statement, hash-ordered) match the rendered PDF in value, sign, column, period and unit; residual OCB unit check confirmed no unit printed | — |
| Focused tests | 69 passed (`test_primary_statements_parsers.py` 48, `test_primary_statements_pipeline.py` 21) | — |
| Frozen shared files | SHAs unchanged (bb319076…, d9b1fa9f…) | — |
| Provider/OCR calls, source mutations | none (`provider_calls_performed: false`, `source_mutations_performed: false`) | — |

## 3. Coverage (full271; common204 in brackets)

| | CDKT | KQKD | LCTT |
| --- | --- | --- | --- |
| Documents with statement | 271 [204] | 271 [204] | 271 [204] |
| Cells ACCEPTED | 32,798 [24,686] | 17,481 [12,985] | 18,068 [13,506] |
| Cells ACCEPTED_BLANK (printed blank kept blank) | 1,013 [747] | 238 [175] | 608 [428] |
| Cells HOLD | 661 [477] | 2,051 [1,632] | 1,436 [1,172] |
| Source rows MAPPED | 17,236 | 5,650 | 10,056 |
| Source rows SOURCE_ONLY (schema gap, see gaps doc) | 2,308 | 52 | 81 |
| Source rows UNRESOLVED | 186 | 31 | 227 |
| Equation PASS (+rounding/alt. sign/alt. membership) | 9,409 | 6,617 | 2,639 |
| Equation FAIL (cells held) | 15 | 17 | 13 |
| Equation MISMATCH_WITH_INCOMPLETE_FRONTIER | 96 | 36 | 347 |

All 271 LCTT instances resolve to the direct method; all scopes resolve.

## 4. HOLD list (full271, by first reason)

| Statement | Reason | Cells | Explanation |
| --- | --- | --- | --- |
| KQKD | UNIT_UNRESOLVED | 1,092 | Statement pages print no unit (OCB family confirmed by PDF render); no unit from magnitude |
| LCTT | UNIT_UNRESOLVED | 796 | Same (OCB and others) |
| KQKD | PERIOD_UNRESOLVED | 778 | SSB quarter reports print no year anywhere on KQKD pages nor a reporting date in other statements' titles; KLB title "QUÝ II NĂM 2020" vs 2026 conflict |
| LCTT | PERIOD_UNRESOLVED | 469 | NAB/SHB titles print 2023 vs 2025 (source conflict); TPB continuation page prints another range; headers with two dates |
| CDKT | PERIOD_UNRESOLVED | 328 | Continuation headers disagree (VAB), closing/opening labels without a unique printed reporting date |
| CDKT/LCTT/KQKD | CELL_UNRESOLVED_CELL | 211 / 157 / 33 | Tables naming one period twice (PERIOD_AMBIGUOUS), malformed or ambiguous-separator cells |
| CDKT | INSTANCE_UNRESOLVED | 110 | Inconsistent value lanes in one instance (doc 48 misaligned table) |
| all | VALIDATION_FAIL | 44 / 51 / 99 | Printed arithmetic does not close (e.g. 50,000 VND, 500, 3,000 residuals); never corrected |
| KQKD | UNIT_UNRESOLVED_PER_SHARE_UNIT | 90 | EPS without printed per-share unit |
| all | CELL_DASH | 39 | Dash contradicted by valued components; not a zero |
| all | CROSS_PRESENTATION_CONFLICT | 15 | VND vs million presentations disagree beyond one unit |

## 5. Benchmark (full271, cold run, WSL 3 GB RAM)

44 SQL queries, 194,231 rows, 30.96 MB JSON, 5,213 pages authenticated and loaded.
Stage seconds: DB byte authentication 1.6, selection authentication 3.2,
census SQL 2.4, census fingerprint 1.8, page load 10.7, assemble/map/validate
25.9, document results 11.4, store write 11.7, reload 26.0, independent
rebuild 104.3, Excel export + readback 137.6. common204: 32 queries,
148,098 rows, 23.47 MB, 3,960 pages. No cache is used, so there is no
stale-cache path; every run re-authenticates its inputs.

## 6. Receipts and artifacts

Local (WSL): `/home/bctc/primary-runs/full271-20261021T163936Z/`,
`/home/bctc/primary-runs/common204-20261021T164639Z/`,
`/home/bctc/primary-receipts/` (preflight, pytest junit, PDF audit,
cross-corpus comparison). S3 keys and VersionIds (uploaded, exact-version verified): see
`ARTIFACTS_2026-10-21.md` in this folder.

## 7. Not accepted / next steps

1. Schema gaps for Codex review (`SCHEMA_GAPS_FOR_CODEX.md`), largest: off-balance
   items 6038–6056 registered consolidated-only while separate statements print them.
2. Unit-less pages (OCB) and year-less pages (SSB): need a reviewed source
   correction or a reviewed document-level rule; currently HOLD.
3. 15/17/13 equation FAILs and 444 UNRESOLVED rows remain for review with PDF.
4. TM is out of scope (Codex). Codex reviews diff, focused regression and
   source proofs before cherry-pick; Claude does not integrate into Codex worktrees.
