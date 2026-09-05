# Cross-family coverage and performance audit — 2026-09-05

## Verdict

This is a read-only audit of the Gemini-JSON/database mapping pipeline for the
2025-current corpus. No provider was called and no repository, Git, S3, PDF or
SQLite state was changed.

The highest-value next moves are:

1. fix the systemic duplicate-`source_ref` provenance invariant before treating
   F36 as terminal;
2. finish the bounded F36 mapping-max release, which has a measured net gain of
   136 mappings in 103 READY documents but is still `HOLD`;
3. add the three already-existing F30 schema leaves that are visibly printed in
   45 documents;
4. replace all-or-nothing rollforward closure with a fail-closed, row-level
   strict-subset gate for exact rows, initially in F18;
5. turn origin-bound continuation and complete-disjoint aggregation into shared
   reusable primitives only after full cross-family replay.

The data supports algorithmic generalization, not bank/page-specific routing.
Every proposed positive requires unique owner, period, unit, semantic lane and
immutable original source provenance. Blank-as-zero, arithmetic backsolve,
overlapping aggregation and broad `Other` are explicitly excluded.

## Authority and freshness

Audit anchor is Git commit
`c6f3cdbc4a5730b1c3a340a8a837307f93d982b8`.

| Authority | Role | SHA-256 / Git blob |
|---|---|---|
| `docs/operations/MACHINE_MIGRATION_CHECKPOINT_2026-09-05.md` | machine migration, queue and release order | `7c0bbbb5ad266d8391793db3c831bf11260974366a84f2beca5b5d1be432b3f7` / `20eb554340ab3d4fab1d1b845e828feeb79da738` |
| `docs/experiments/COMPLETED_TM_FAMILIES.md` | historical 55-concept catalogue | `3931dc3793d97aaba8985b88a7bb0fcc940fb4a7b564b7d59b2c79e39f73c5aa` / `e14c8737ca7b0ff99c51e495368d255b4d6115d0` |
| `docs/experiments/UNRESOLVED_MAPPING_LEDGER.md` | unresolved/terminal ledger | `5df7708b0cb17f928e2635347daa759fd6c1061bb765edf7d8fc5b8f6a745311` / `a354824bd36a583545a45b54f35dff91579eb819` |
| `docs/experiments/GEMINI_JSON_FIRST_OFFICIAL_FAMILY_SELECTIONS.md` | official family-selection contract | `20c3ec3eb56f958b57b8705dbd95d9a6e93903bd32fc9dc3107a9aba136963d2` / `2ca7cddce2f69a331a40a6ef6b56b48fa07c3935` |
| `reference/schemas/schema_graph.jsonl` | RNID/schema graph | `3fea408082263c171e98d1edc9b61608261b8a66b83706a5d7d029f9b0655403` / `0a5d03432fe92f276598890e5dc23263233a29f0` |
| `PROJECT_GOAL.md` | current 2025-current scope | `daafd4bb9f0009e567b1f5e0da59e68876e353300192b95507d61bcf722f1ac0` / `2243bb59e6b076e7e5b76eb6e63652880e8938f4` |

Current full271 authority:

- manifest: `/dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts/current-corpus-manifest-indexes/8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a.json`
  (file SHA-256 `969ff5f80732c39e4b7543ca1f5c1e5b5b827260f19981ed02945fe0c7379219`),
  271 documents / 14,945 pages;
- immutable page store:
  `/dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts/current-corpus-freeze-inputs/store-ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7.sqlite3`,
  SHA-256 `ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7`,
  573,145,088 bytes.

Common204 is a compatibility/replay authority, not the source for current gain
estimates:

- manifest:
  `/dev/shm/bctc-ai-27-bank-family-live-v1/current-corpus-manifest-indexes/32c474f657f9484244e9675a0ca4801cb49b4923971dfb7bea17081904154747.json`,
  file SHA-256 `acc1d08e45e5a05925c434ae1c96fd6bc481a0e6ca61fc9f78e155efca7365b1`,
  204 documents / 11,454 pages;
- store:
  `/dev/shm/bctc-ai-27-bank-family-live-v1/current-corpus-freeze-inputs/store-a14904a492e6beae165b81f7aa1738352a9824e113f1b163a46ee277d37e0220.sqlite3`,
  SHA-256 `a14904a492e6beae165b81f7aa1738352a9824e113f1b163a46ee277d37e0220`,
  553,984,000 bytes.

`/dev/shm/bctc-ai-27-bank-family-live-v1/family-results.sqlite3` is explicitly
stale, preterminal diagnostic evidence only: SHA-256
`844e6319...7ea0`, 149,434,368 bytes, 19 runs x 204 documents,
`family_current_selection=0`, and no `family_candidate_region` table. Its high U
counts must not be reported as current release gaps. `quick_check` was `ok` and
the foreign-key check returned no rows.

The old140 tables and the historical 522-row frontier are excluded from every
gain estimate below. They are useful only as regression/history evidence.

## Canonical family inventory: why both 55 and 54 appear

The historical catalogue has 55 conceptual rows. The executable current
Gemini family axis has 54 families because it:

- drops the statement-only net-interest concept historically numbered 30;
- retires legacy F26 `OTHER_PAYABLES_LIABILITIES`;
- adds current F26 `LOAN_INTEREST_ACCRUAL_CLASSIFICATION`.

Therefore **55 is the conceptual catalogue count; 54 is the canonical current
operational count**. The operational order/status is:

| # | Family ID | Cluster | Current status |
|---:|---|---|---|
| 1 | `CASH_PRECIOUS_METALS` | classification/balance-sheet | terminal |
| 2 | `CENTRAL_BANK_DEPOSITS` | classification/balance-sheet | terminal |
| 3 | `INTERBANK_DEPOSITS_AND_LOANS` | classification/balance-sheet | terminal |
| 4 | `TRADING_SECURITIES` | classification/balance-sheet | terminal |
| 5 | `DERIVATIVE_FINANCIAL_INSTRUMENTS` | classification/balance-sheet | terminal |
| 6 | `LOAN_TYPE_CLASSIFICATION` | classification/balance-sheet | terminal |
| 7 | `LOAN_INDUSTRY_CLASSIFICATION` | classification/balance-sheet | terminal |
| 8 | `LOAN_QUALITY_CLASSIFICATION` | classification/balance-sheet | terminal |
| 9 | `LOAN_MATURITY_BUCKETS` | classification/balance-sheet | terminal |
| 10 | `LOAN_CURRENCY_CLASSIFICATION` | classification/balance-sheet | terminal |
| 11 | `LOAN_GEOGRAPHIC_CLASSIFICATION` | classification/balance-sheet | terminal |
| 12 | `LOAN_ENTERPRISE_FAMILY12` | classification/balance-sheet | terminal |
| 13 | `PROVISION_MOVEMENT_ROLLFORWARD` | rollforward | terminal |
| 14 | `PURCHASED_DEBT_ACTIVITY` | rollforward | terminal |
| 15 | `CUSTOMER_DEPOSIT_CLASSIFICATION` | classification/balance-sheet | terminal |
| 16 | `INVESTMENT_SECURITIES` | classification/balance-sheet | terminal |
| 17 | `OTHER_LONG_TERM_INVESTMENTS` | classification/balance-sheet | terminal |
| 18 | `TANGIBLE_FIXED_ASSETS_ROLLFORWARD` | rollforward | terminal, 3 typed U |
| 19 | `LEASED_FIXED_ASSETS_ROLLFORWARD` | rollforward | terminal |
| 20 | `INTANGIBLE_FIXED_ASSETS_ROLLFORWARD` | rollforward | terminal |
| 21 | `INVESTMENT_PROPERTY_ROLLFORWARD` | rollforward | terminal |
| 22 | `OTHER_ASSETS` | classification/balance-sheet | terminal |
| 23 | `GOVERNMENT_SBV_LIABILITIES` | classification/balance-sheet | terminal |
| 24 | `ENTRUSTED_INVESTMENT_RISK_CAPITAL` | classification/balance-sheet | terminal |
| 25 | `ISSUED_VALUABLE_PAPERS` | classification/balance-sheet | terminal, 1 typed U |
| 26 | `LOAN_INTEREST_ACCRUAL_CLASSIFICATION` | classification/balance-sheet | terminal |
| 27 | `CAPITAL_AND_FUNDS` | rollforward | terminal |
| 28 | `INTEREST_INCOME` | income/expense | terminal |
| 29 | `INTEREST_EXPENSE` | income/expense | terminal |
| 30 | `SERVICE_ACTIVITY` | income/expense | terminal, 1 typed U |
| 31 | `FX_GOLD_ACTIVITY` | income/expense | terminal |
| 32 | `TRADING_SECURITIES_ACTIVITY` | income/expense | terminal, 1 typed U |
| 33 | `INVESTMENT_SECURITIES_ACTIVITY` | income/expense | terminal |
| 34 | `COMBINED_SECURITIES_NET` | income/expense | terminal |
| 35 | `CAPITAL_CONTRIBUTION_DIVIDEND_INCOME` | income/expense | terminal, 2 typed U |
| 36 | `OPERATING_EXPENSE` | income/expense | active, terminal `HOLD` |
| 37 | `CREDIT_RISK_PROVISION_EXPENSE` | income/expense | active |
| 38 | `OTHER_ACTIVITY` | income/expense | terminal, 1 typed U |
| 39 | `INCOME_TAX` | income/expense | active |
| 40 | `CASH_EQUIVALENTS` | classification/balance-sheet | terminal, 6 typed U |
| 41 | `SUBSIDIARY_ACQUISITION_DISPOSAL` | rollforward | pending full271 |
| 42 | `EMPLOYEE_INCOME` | income/expense | pending full271 |
| 43 | `STATE_BUDGET_OBLIGATIONS` | rollforward | pending full271 |
| 44 | `CUSTOMER_COLLATERAL_HELD` | classification/balance-sheet | pending full271 |
| 45 | `BANK_PLEDGED_OR_DISCOUNTED_ASSETS` | classification/balance-sheet | pending full271 |
| 46 | `CONTINGENT_LIABILITIES_AND_COMMITMENTS` | risk | pending full271 |
| 47 | `FINANCIAL_INSTRUMENTS` | risk | pending full271 |
| 48 | `CURRENCY_RISK` | risk | pending full271 |
| 49 | `INTEREST_RATE_RISK` | risk | pending full271 |
| 50 | `LIQUIDITY_RISK` | risk | pending full271 |
| 51 | `EXCHANGE_RATE` | risk | pending full271 |
| 52 | `INTERBANK_FUNDING` | classification/balance-sheet | pending full271 |
| 53 | `SECURITIES_GEOGRAPHY` | classification/balance-sheet | pending full271 |
| 54 | `CONSOLIDATED_SEGMENT_REPORT` | other/presentation | pending full271 |

Cluster totals cover all 54 exactly: classification/balance-sheet 25,
rollforward 9, income/expense 13, risk 6, other/presentation 1. The migration
authority says the chain has passed F40, exactly F36/F37/F39 remain
nonterminal, and F41 must not start until those three close.

Two documentation freshness caveats do not change status: the Git F17 ledger
still points to an older 582-mapping result while the bounded source-repair
artifact has 584 mappings; F21's latest singleton artifact has 38 mappings
where an earlier ledger generation had 35.

## Systemic correctness blocker: duplicate source provenance

A read-only exact-content-identity scan of current full271 terminal artifacts
F16-F35, F38 and F40 (F27 excluded because its artifact has a different query
shape) inspected 24,011 mappings. It found:

- **12,779 mappings containing exact duplicate `source_ref` objects**;
- **13,918 redundant references**;
- **13 affected families**.

| Family | Duplicate mappings / mappings | Redundant refs | Affected docs |
|---|---:|---:|---:|
| F16 | 12 / 3,299 | 12 | 6 |
| F17 | 579 / 584 | 657 | 190 |
| F22 | 1,547 / 1,547 | 1,678 | 271 |
| F23 | 1,158 / 1,158 | 1,397 | 269 |
| F24 | 210 / 322 | 214 | 88 |
| F25 | 954 / 1,438 | 1,108 | 182 |
| F28 | 1,775 / 1,775 | 1,834 | 271 |
| F29 | 1,131 / 1,402 | 1,138 | 271 |
| F30 | 2,150 / 2,150 | 2,404 | 202 |
| F31 | 1,316 / 1,446 | 1,370 | 271 |
| F32 | 556 / 571 | 556 | 227 |
| F33 | 752 / 771 | 817 | 271 |
| F35 | 639 / 639 | 733 | 217 |

This does not currently double the coefficient, but it inflates provenance and
can destabilize mapping IDs, replay hashes and audit counts. It is therefore a
release correctness issue, not cosmetic normalization.

The direct cause is lane reconciliation extending the same record-level source
references once per period lane:

- `src/bctc_ai/evaluation/gemini_json_other_long_term_investments_family_v1.py`,
  SHA-256 `af4cbdbf3eb63eb799b2a1a475db66726b8e9d1f3a133b0d897ebdd47d567fc5`,
  `_global_records`, lines 2708-2845, especially 2802-2804;
- `src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py`,
  SHA-256 `bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2`,
  `_multitable_global_records`, lines 13077-13115; the shared path knows the
  imported reconciler duplicates refs but only deduplicates an opt-in root case.

The fix should be stable, canonical content-identity deduplication before
mapping-ID sealing, preserving first authoritative source order. It requires
full replay of every affected family because mapping IDs/hashes change. Do not
dedupe by label/value alone and do not collapse distinct physical source cells.

F36's independent delta scan is
`/dev/shm/f36-post-c6f3-common204-independent.mXnK4O/duplicate-source-ref-scan.json`,
SHA-256 `0dec60b680fd67a9a23e2cc831393eee0bcb40ead957ea7b0f31bffd7867a7a7`.
It finds common204 65 -> 66 duplicate mappings and full271 121 -> 121, with
119 retained, two newly introduced and two removed. Thus F36's corrected S3
checkpoint is mechanically resumable but **terminal status remains HOLD and no
laptop coordination event should claim terminal acceptance**.

## Top five mapping opportunities

Ranking combines observed prevalence, financial importance, expected mapping
gain and risk. Counts are current full271 unless explicitly labelled.

### 1. Finish F36 mapping-max behind the provenance invariant

The bounded F36 parent/child/sibling/`Other` implementation at c6 measured a
net +136 mappings across 103 READY documents, with status distribution still
250R/21U. It covers 150 clear source occurrences and complete-disjoint flat
parent frontiers without broad-`Other`, backsolve or blank-zero. It must not be
released until the 121 duplicate mappings and 307 coverage violations are
explicitly handled/replayed.

- measured reach: 103 documents, +136 mappings;
- reusable mechanism: exact scoped leaves plus parent projection only from a
  complete, disjoint, arithmetic-closing frontier; printed parent wins;
- safety: veto a candidate `Other` that is an ancestor/equation result; bind
  continuation receipts to original sender/receiver locators;
- authority: `/dev/shm/f36-mapping-max-readonly.rGRKx4/PROPOSAL.md`, SHA-256
  `cc69143b747157c40fc5de5bacd1434dcab7eab1f98673c98d950bc80c056c24`;
  post-c6 report
  `/dev/shm/f36-post-c6f3-independent-validation.8hscI9/REPORT.md`, SHA-256
  `27b20d9ae18206567ff31ec3b8564899180e0c97d40abf53e552800be49e2480`.

### 2. F30 exact leaves already present in the schema

F30 currently omits three exact schema nodes from its binding:

- RNID1161 `Dịch vụ quản lý quỹ`;
- RNID1162 `Dịch vụ cho thuê và quản lý kho, định giá tài sản`;
- RNID1165 `Thu về chi trả kiều hối`.

The full271 sweep shows 49 clear rows in 45 distinct documents. Thirty-nine
custody/rent rows occur in 35 documents; 37 are equation-consumed and two belong
to the existing NAB U. Eight TCB documents print fund management as a separate
sibling but it is currently folded into RNID1163. Two STB documents print
remittance as a separate sibling but it is folded into RNID1158.

Expected bounded result is about +45 exact leaf mappings plus correction of 10
existing aggregate memberships. Combined labels remain unsplittable without
source evidence. Authority:
`/dev/shm/family30-authoritative-bb319-v3.tXqkaT/sweep.json`, SHA-256
`7fc304d66a286dde79a1eca140abef13af7b02bf040de228e5f85cbd9f153f93`.

### 3. Row-level strict-subset closure for rollforwards, starting with F18

The current all-or-nothing table/document gate suppresses individually exact
rows when one unrelated equation fails. F18 is terminal with 3 typed U:

- NVB117: right-edge total is cropped on one page, but 10 roles and five
  complete-disjoint asset columns are visible across the closed presentation;
- NVB120: 10 roles have printed total cells; at least 8 pass a conservative
  independent row-level closure now, while two endpoints need resolution of a
  horizontal-component versus vertical-rollforward conflict;
- SHB175: 20 roles are clear in the PDF; 11 direct total rows are usable now and
  nine more require an authenticated bounded source repair because selected JSON
  shifted detail cells after dash markers.

A fail-closed strict-subset gate can conservatively add at least 29 mappings;
the upper bound is about 40 only after source repair/policy review. It must emit
per-row equation receipts, leave failed/ambiguous aggregates U, prefer printed
totals, and never infer missing cells. Because the nine-family rollforward
cluster shares this presentation shape, the primitive is broadly reusable even
though the measured current positives are three F18 documents.

Authority: `/dev/shm/family18-full271-final-v4.json`, SHA-256
`d1eb7a27f4d34dcc38eb418bf9c492ccba780838a6f7a29cd346e4f41438dbb1`.
Historical BVB common204 doc13 was once U for this reason but is already
READY13 in current full271, so it is a regression control, not counted gain.

### 4. Origin-bound cross-page continuation primitive

Continuation handling recurs in at least seven terminal families and at least
25 full271 documents (F16 >=4, F22 15, F28 2, F29 1, F30 >=1, F31 >=1,
F38 1). The F36 baseline additionally had 10 unclosed continuation U. Existing
family adapters already solve many of the terminal cases, so 35 must not be
claimed as new mappings; it is the measured reusable reach and regression set.

The safe shared contract is reciprocal page adjacency, same document/owner,
closed continuation marker, compatible unit and period lanes, section reset
fences, and inverse restoration of every emitted mapping and guard/aggregation
receipt to the immutable original sender/receiver cell. Never seal projected
synthetic row coordinates.

### 5. Printed terminal-root retry before derived-root veto

A bounded F36 counterfactual proves two safe positives: NAB92 and TPB237. A
retry may bind a printed final total before the derived-root veto only when the
same table/region is closed, the period/unit frontier is unique, the total is a
terminal printed row, and every component is complete and disjoint. KLB57 must
remain U because the printed comparative total 931,733 differs from the five
direct parents' sum 906,647 by 25,086; SGB149, VAB243 and VAB253 also remain U.

Expected gain is exactly +2 proven documents; no blanket root promotion.
Authority: `/dev/shm/f36-next-root-closure-design.3qOvgc/PROPOSAL.md`, SHA-256
`9c7153283b694f5a575e3b39b683c2854af1b040c31b16189d489a0ceb4926b3`.

## Top five speed improvements

These preserve mandatory independent cold replay and immutable input hashing.
The measurements come from
`/dev/shm/f36-post-c6f3-independent-validation.8hscI9/STATIC_SPEED_OPPORTUNITIES.md`,
SHA-256 `768ba0554d23bec25bc44e197180a60637d5f413b1b3cbad5cda85d177f901a7`.

| Rank | Improvement | Measured lower bound / expected effect | Safety constraint |
|---:|---|---|---|
| 1 | Prepartition pages by `document_id` once | F36 owner-axis filtering is about 5 x 271 x 14,945 = 20,250,475 comparisons; a document index reduces lookup work to about 74,725 plus five linear passes | index must preserve manifest/document/page order and immutable page identity |
| 2 | Remove the redundant same-memory middle trial build | Current F36 path builds three trials; use one working build plus one mandatory cold independent replay | never remove the final cold replay or compare a result with itself |
| 3 | Add an additive query-and-pages API | Current path performs at least four full SQLite JSON-decode passes = 59,780 page decodes; one joined streaming pass can reduce this to three, saving 14,945 decodes | independent replay still reopens the exact immutable store |
| 4 | Content-addressed authenticated snapshot/hash lease | Current path copies one 573,145,088-byte DB snapshot and performs six DB-sized hash/read passes (3,438,870,528 bytes read for hashing plus the copy write) | key by exact SHA/inode/size/config; validate entry and exit; never reuse across mutation or process trust boundary |
| 5 | Normalize candidate regions and cache document/spec deltas | Add `family_candidate_region`, populate `family_current_selection`, and cache candidates/trials by content identity so only changed documents/specs replay | terminal release still performs full271/common204 cold replay; cache is acceleration, never authority |

The stale common store confirms the schema gap for rank 5: it has 2,755
`family_candidate` rows and 7,409 mappings but zero current selections and no
candidate-region table. Relevant code authorities at c6 are:

- `src/bctc_ai/storage/gemini_accounting_family_store_v1.py`, SHA-256
  `6c6638bde3a1eea25c5382321a0a256323ea737bd691014c6e04d2308c8e8a17`;
- `src/bctc_ai/storage/gemini_financial_page_store_v1.py`, SHA-256
  `dbcf3381f526b3abf7cf234148cd7be17b758cc5cb43268feece74a5ba53e27c`;
- `scripts/experiments/build_f36_diagnostic_from_corpus_v1.py`, SHA-256
  `3f2e6e599cb8a951eecb065f4a5be5708b5a85a3d07b062325a41f2f30413b63`.

Canonical provenance deduplication will also shrink artifacts and hashing, but
it is ranked as correctness work first, not sold as a performance shortcut.

## PDFs visually inspected

All pages were rendered from current local PDFs, without legacy OCR or provider
calls. Render directory is `/dev/shm/cross-family-audit-pdf-view`.

| Evidence | PDF/source SHA-256 | Page | What was verified | Render SHA-256 |
|---|---|---:|---|---|
| KLB doc53 F30 | `/workspace/bctc-ai/vietstock_bctc/KLB/2025/BAO CAO TAI CHINH QUY 3.2025 HOP NHAT.pdf`; `66e07ea5075283291d4abda7fb550fe4277295944c8993dfd35400e6a4878da2` | 28 | rent/valuation are visible siblings under exact service parents | `b997e591eb48975189de6fccc48c281fc14aad0875c95fac9a97e3cac9d27691` |
| TCB doc215 F30 | source SHA `553195cdc772f58a5ea34cb118cfcf98f7ea7460efc802ecc4e95269665a8527` | 72 | trust/agency and fund-management are separate printed siblings | `05f92f6f5e731ec5b1317a3360c1e368546659dc15fa69b853be780cbd32c7cb` |
| STB doc199 F30 | source SHA `522e518939e87349893073c53af75ddadb073683a21c69e799fe1be3b42241dd` | 68 | remittance is a separate printed sibling | `cdb192011849a55aa95eb867e83dcc74112d088403ababd1cee1516d9a67c959` |
| BVB historical common13/current full24 F18 | source SHA `55452f947d44bc11de79d9180c118acea4d45a674159364ad763ad5a8f712f29` | 27 | old all-or-nothing U is now READY13; regression control only | `22b4bb72ae538e3221d3e35702a4c11c09a273021314b274b3740c85a1eefa83` |
| NVB117 F18 | source SHA `92f4239c94d2880bc99d0986cc61a580dae7b4a2f52721bf4f47700aded2bb65` | 34-35 | cropped right-edge total versus complete prior table and disjoint asset columns | p34 `9fa99572e6f7eda2556cbead3d4a55df5bd6bcaa1b003fbc74ee08844739c7d4`; p35 `a3bb126518c38fffd1489f29a18562edf957a0ffd430be9b9f2aaf5a2fa3d163` |
| NVB120 F18 | `vietstock_bctc/NVB/2026/2_nvb_2026_7_30_2bf1dd5_bctc__rieng_le__tieng_viet__q2_2026_signed.pdf`; `b7eb6ab6d207dced305869e716e479b49a8f1f8bd5a50b91ca0a639773d02069` | 33 | 10 printed total-column roles; eight conservative row closures, two endpoint conflicts | `e8afd3f320eb6acb87916d635ba2b257e0b96b0b48442beedb937c953aa7b2fd` |
| SHB175 F18 | `/workspace/bctc-ai/vietstock_bctc/SHB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf`; `e43e50a17cd71ce393475b2bc53b47d6502b5b966f2d46d17da4dc1eac4cda6f` | 29 | 20 clear roles; 11 direct totals usable, nine selected-JSON shifts need source repair | `927cec24d3cb165b0dd91aad7520beffb0d342b36cbac1bdd152a0bbf1a78e60` |

Every source and render hash in this table is complete. Where the logical PDF
path is not repeated, the full source path remains bound to that SHA-256 in the
cited full271 artifact and immutable manifest.

## Recommended execution order

1. Close the duplicate-provenance invariant and replay the 13 affected terminal
   families plus F36. Keep F36 terminal `HOLD` and do not publish a terminal
   laptop event until the independent exact-ref scan is clean.
2. Re-run governed common204/full271 F36 diagnostics and close coverage receipts;
   only then accept the measured mapping-max gain.
3. Implement F30's three exact schema leaves test-first. This is the highest
   low-risk unimplemented mapping gain: about 45 documents.
4. Prototype row-level strict-subset closure in F18 with the three PDF-backed
   cases and adversarial missing/overlap/unit/period/continuation controls. If it
   passes, promote the primitive across the nine-family rollforward cluster.
5. Keep the official queue constraint: finish active F37 and F39 before opening
   F41. Among new families, F41 remains the next canonical family only after
   F36/F37/F39 are terminal.

This prioritizes clearly visible data that the schema already owns, while
retaining typed U for genuine ambiguity, incomplete equations, conflicting
units/periods and non-disjoint parent/child frontiers.
