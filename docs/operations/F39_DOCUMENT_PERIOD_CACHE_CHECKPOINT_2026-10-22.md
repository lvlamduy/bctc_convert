# F39 document period cache checkpoint

The operation-local document-period inventory cache preserves the exact F39 results on the 34-document regression panel. A fresh independent SQLite replay with the cache disabled passes. In this single paired observation, family evaluation took 156.300327 seconds with the cache and 162.016556 seconds without it, a 3.528176 percent reduction. This is a modest bounded observation, not a general speed guarantee or family acceptance.

This checkpoint descends from `ebde8710ecea9721039cbac875810960dfd4040b` on `codex/f39-income-tax-laptop` and migration base `8efd618b6c77f0cdbb402a440e7ba3b3549184f1`. Source reports remain 2025 through current; 2024 source PDFs remain outside production and provider queues. Printed earlier-year comparatives inside eligible reports remain source evidence.

## Cache authority and lifetime

Only the source-derived document-period inventory is memoized. No candidate, READY result or caller-provided receipt is cached. The original inventory builder body is unchanged. Keys bind the complete ordered raw or repaired page records, complete compiled specifications and nine reviewed implementation dependencies. Stored outputs are immutable canonical bytes; every return is a fresh decoded object. The cache holds at most two entries, is operation-local and is cleared on successful or failed exit. Inherited thread/task contexts and closed operations are rejected.

Actual implementation bytes are pinned on first inventory use and rechecked before the owning scope exits. Every lookup still hashes the full source/specification input and checks the reviewed callable fence. A caught dependency/fence invalidation cannot be cleared by restoring the file. Results inside an explicitly caller-owned outer scope are provisional: the contract prohibits persistence, export or accepted handoff before successful owner exit. The runner obeys that ordering; this is not a storage interceptor for arbitrary callers.

The supported execution condition is a fresh, pinned Python 3.12 runtime without hot reload or arbitrary runtime-memory mutation. The focused and independent replay helpers enforce `-B` and an initially nonexistent isolated bytecode prefix; the panel was launched with the same conditions. File hashes and module paths alone do not prove loaded bytecode. The entry/exit barrier is not a monitor for transient filesystem edits restored between those barriers. Source and tests were frozen throughout all three witness jobs.

Independent replay explicitly disables the inventory cache through nested public APIs. Its metrics record actual builder calls, not an assertion that a warm result was independently rebuilt. Runner implementation pins include all nine cache dependencies and are checked before and after execution. Existing source/database/PDF and frozen-file checks remain active.

## Verified gates

| Gate | Result | SHA256 |
| --- | --- | --- |
| Focused witness | PASS, 1,448 tests in 16 suites, 46 actual project imports, no failure/error/skip, inputs unchanged | `a9c69eb350b2313c2dbaf18698767f4e3736a2b687163c77df4653a84457f7a5` |
| Bounded diagnostic | 34 documents, 18 READY review proposals, 16 UNRESOLVED, 90 final mappings; no persistence | `b9ae93450e32cbdd0e5a532c203be81162c7a1302ddec7bf8c6253e751b59853` |
| Independent cache-disabled replay | PASS exact original SQLite reconstruction and pre-cache result equality | `02150ca368f442155fa7f5a99bf274e874bae32650a35d910cf0f40090c797ca` |

Exact witness paths:

```text
/srv/bctc-receipts/f39-period-barrier-focused-1792604026189-eae7ff159660432080fd1857df81eca5/F39_IMPLEMENTATION_FOCUSED_RECEIPT.json
/srv/bctc-receipts/f39-period-barrier-panel-1792604722933-ddb9c42bc7f44e9f9ab186fd42924430/income-tax-bounded-diagnostic.json
/srv/bctc-receipts/f39-period-barrier-cold-1792605015813-163403f77d6b47f7aed265de4ffabb0e/F39_PERIOD_CACHE_INDEPENDENT_SOURCE_REPLAY.json
```

The comparison authority is the preceding pre-cache diagnostic, SHA `a27262ad7b0288761b4aa16ad92c40f1eeaebde709e103fdf718be9605005742`. Indexed query evidence, complete trials, mappings, receipts, raw observations, PDF bindings, authenticated repair IDs and immutable input references are exactly unchanged. Source observation audit remains PASS with zero violations: 487 recursively audited mappings and 974 cells, including six source blanks, six partial mappings and two derived cells. Those audit counts are not final export counts.

Both runs perform 34 selected-JSON API calls over the same 2,170 SQLite rows and 10,196,448 payload bytes. There are 2,169 exact original JSON replays and the existing single lossless redundant-TEXT-column EIB normalization; no new source correction is active. The source DB remains read-only/query-only, 573,145,088 bytes, SHA `ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7`, with quick_check ok and an empty foreign_key_check.

| Inventory measurement | Cache enabled | Independent cache disabled |
| --- | --- | --- |
| Requests | 272 | 272 |
| Actual builds | 34 | 272 |
| Hits | 238 | 0 |
| Implementation byte checks | 68 | 0 cache checks |
| Builder seconds | 2.651641 | 22.650125 |
| Key and barrier seconds | 11.561290 | 0 |
| Clone seconds | 0.697218 | 0 |
| Peak stored output entries and bytes | 1 and 146,720 | 0 and 0 |

Implementation checks consume 3.962991 seconds already included in key/barrier time; do not add that time twice. The bytes metric measures stored canonical outputs, not process RSS or total allocations. The observed cold/warm family-time ratio is 1.0365720867259551. Loading and generic evaluation are separate stages; historical faster or slower runs are not the comparison denominator.

## Rejected first experiment

The first cache version hashed all nine implementation files on every lookup. It passed 1,425 focused tests and preserved the exact panel and independent replay results, but was about 1.5 percent slower than its own uncached comparison. It was not adopted as an optimization. Its witnesses remain intact:

| Witness | SHA256 |
| --- | --- |
| First focused receipt | `27a691b32c8e99c1a148cea802780ef7ec19f9b4d3a86cf0f98c1af447269026` |
| First panel | `54df51f4213e83353530b3ada98732d1875d0c26d1282ed7ed98ef297d933183` |
| First independent replay | `329403d07dfc54838f2539e1b63d0e65ebfbcca1c772d67a1396f544f2ad5e3c` |

The rejected typed-snapshot shortcut was not implemented: its measured comparison cost was not better and its object-key type assumptions were insufficient. A first CLI attempt also failed the contained-results-database gate before source evaluation; its failed directory was not reused. No live job was restarted for an observation timeout, and no old artifact was deleted.

## Source reviews and next accuracy work

An additional original SQLite audit authenticates LPB74 physical page 7 and SSB187 physical page 13: `/srv/bctc-receipts/f39-lpb74-ssb187-original-1792603413771-6bfc142fd3a04a8e9c6dbf958f767c27/F39_LPB74_P7_SSB187_P13_ORIGINAL_SOURCE_AUDIT.json`, SHA `85718495063ce60ff4e483758c38d4a7925df000d6d3d0f5c21755af30d3c2a6`. It grants no algorithm or repair permission.

The inactive manual review `D:/bctc_bank/restore-receipts/F39_SSB_187_PRINTED_COMPARABILITY_POLICY_VISUAL_REVIEW_2026-10-22.json`, SHA `fe8761f911f55a8ca97a5a96faba949c7ad548de4335e2bf6da464833a069f93`, binds a whole-page Poppler render and original section hashes. Its next implementation target is finite written-six-month comparative policy recognition with genuine section-local financial-narrative ownership. A sibling subsidiary table is not policy ownership. The independent printed-row-code blocker remains separate. The external implementation patch is only a draft, not applied or tested code.

LPB74 still needs a reviewed basis-qualified distinction between recognized tax expense and rate-reconciliation effects, plus a source-bound cross-page PBT/tax/PAT bridge. It must retain the two different printed prior-adjustment amounts and blank total labels. PRIMARY page 6 and continuation page 7 have different column ordinals, so lane semantics must be matched independently rather than copied by position.

Read-only review of the 12 signed-display umbrella holds found six first blocked by relative-period proof, four by unproven report population, one by contradictory JSON caption years and one by printed-row-code ancestry. These are not 12 proven monetary conflicts. One relative-period case also has a separately known caption transcription conflict. The saved diagnostic does not persist the exact signed-proof early-return branch, so these cohorts guide investigation rather than establish final dispositions.

Next priorities are those source-local accuracy fixes, an independent all-status original-row/all-MONEY-column census, authoritative full271/common204 evaluation, persisted readback and independent replay, observation/integrity checks, PDF/residual audit and the final F39 ledger. Existing row-set or selected-two-lane coverage does not prove that every original money cell has a disposition. Algorithm holds cannot be relabelled genuine source absence. F36 then F37 follow only after F39 is terminal; F41 remains closed.

## Code and coordination pins

| Owned file | SHA256 |
| --- | --- |
| F39 evaluator | `2bac5c9e36ec53f7c7808d42b2b7e3a721938a701b3814ebf8e4a0e1617eddf2` |
| F39 runner | `71ec0b9ccb757b4a0ab87b6c23c072efe18f1360cb6f3e08c5f926799586c3c4` |
| New 115-case cache test module | `dd0951c08c374a8510064295da4271e894346375c09779917c18edad90d352c9` |

Frozen shared evaluator remains `bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2`; frozen generic runner remains `d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5`. Ruff and diff whitespace checks pass. No provider, original PDF/JSON/database write, F36/F37/shared-file edit, Claude PRIMARY edit or obsolete OCR route is introduced.

Before the checkpoint mutation, all 101 existing coordination events were read and the precommit HEARTBEAT was exact-VersionId verified:

```text
key: bctc-ai/coordination/2025-current/v1/events/20261021T175632520425Z-LAPTOP_INTEGRATOR-HEARTBEAT-48dad3b268624b8488225227a2a6eadd.json
VersionId: O8EmpVYHKWjZnCwOpsCytw9OikS7XE7h
SHA256: adf99f8e41011e615de98564aff96cf392ca0e654259b9256f00b09301378821
```

After the owned-branch commit is pushed, the three current witnesses are backed up append-only with exact-VersionId byte/checksum readback. Their keys and versions belong to external publication receipts and the following HEARTBEAT. This checkpoint does not claim full backup/seal, READY_FOR_INTEGRATION, family terminal status, accepted Excel output or full BCTC completion.
