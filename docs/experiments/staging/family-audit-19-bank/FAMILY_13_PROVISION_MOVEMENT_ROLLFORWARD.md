# Family 13 — Provision movement roll-forward

## 2026-09-04 source-observation remediation release

This release supersedes the v19 mapping count below.  The current 271-document
corpus remains **240 READY / 31 NOT_OBSERVED / 0 UNRESOLVED**, but mapping
output is reduced from 1,976 to **1,955**.  Exactly 21 mappings whose numbers
came only from blank-cell equations were removed.  Eight other flagged cells
were visibly printed accounting dashes in the PDF; those were restored through
exact authenticated source-repair receipts rather than inferred as zero.

Release artifacts:

- `/dev/shm/family13-full271-remediation-v1.json` — SHA-256
  `0e3179550aa552549368bbd3d434cf8a1276500c93c89cfc0f82b7ac66b94298`,
  36,549,154 bytes; sweep
  `gjfafsv1:sweep:3a2d9aae30d3f1c4cbdf2c88542bc0914408fb848c71bfd668daedd37379ad17`.
- `/dev/shm/family13-full271-remediation-v1.sqlite3` — SHA-256
  `76f45ebf726714926b5d9e06022dae9ce9cdf431bc9f73e87952c811f7cbd756`.
- `/dev/shm/family13-common204-remediation-v1.json` — SHA-256
  `8f8125aa8669dc6adfa0ba279c56e7a8509707ef8a38431c2e0124599829ab81`,
  27,403,403 bytes; **180 READY / 24 NOT_OBSERVED / 0 UNRESOLVED**,
  1,477 mappings.
- `/dev/shm/family13-common204-remediation-v1.sqlite3` — SHA-256
  `074bbae962078a84915065c31da56f651682af8b3aa05f5d160b7dda7beaa978`.
- `/dev/shm/f13-source-observation-audit/final-audit-v1.json` — SHA-256
  `efd70e627cdc38ef2f4e2cb00f832a5bd2bba0409078773236eed9634032206b`,
  42,341 bytes; audit ID
  `f13sorav1:audit:43ac6e9608c5d7dfc6c78a133f0fc1a71627ece2ff9b53425d20400d8c0b8232`.
- Working PDF inventory:
  `/dev/shm/f13-source-observation-audit/inventory.json`, SHA-256
  `75b82689b0a8b7dfdb1ebcc9e62a8057de9b8ec7c7c8afa4e40992e8c1d56536`,
  52,494 bytes.

### Mapping contract and generic rule

Equations may still recover a one-unknown value or a horizontal-total zero in
the closure receipt.  Such values are corroboration only and are never emitted
as schema mappings.  Mapping output is restricted to cells with an integer
coefficient, string source text, and one of these source-supported states:
`RAW_SIGNED_INTEGER`, `DASH_ZERO`, `AGGREGATED_EXACT_SOURCE_ROWS`, or
`NORMALIZED_DIRECTIONAL_DEDUCTION`.  Candidate replay independently rebuilds
the same filtered projection.

The global `SOURCE_OBSERVATION_MAPPING_CONTRACT_AUDIT_V1` result is PASS for
both full271 and common204.  Full271 contains 3,910 recursively observed
candidate/trial mapping copies, zero blank cells, zero numeric cells without
source text, and **zero violations**.  The 1,955 selected mappings comprise
1,668 raw integers, 219 visible-dash zeroes, 66 exact source-row aggregates,
and 2 exact directional deductions.

All 271 statuses are stable against v19: 240 READY→READY and 31
NOT_OBSERVED→NOT_OBSERVED.  The 31 NOT_OBSERVED sources retain the prior
whole-document PDF recall disposition described below; no evaluator error was
reclassified as absence.  There are no unresolved documents and no remaining
PDF-visible schema-mappable F13 cells left behind by this remediation audit.

### Exhaustive 29-cell PDF disposition

The initial contract gate reported 58 nested occurrences representing 29
unique selected mappings: 22 `INFERRED_ONE_UNKNOWN_FULL_RANK` and 7
`HORIZONTAL_TOTAL_PROVEN_ZERO`.  Exact-page review classified all 29 as 21
genuinely blank cells and 8 visible dashes omitted by selected JSON.

| Ordinal | Page | JSON cell | Lane / movement | Prior value/state | PDF disposition |
|---:|---:|---|---|---|---|
| 13 | 23 | s1/t2 r4:c2 | general / use | 0 horizontal-total | blank; omitted |
| 14 | 23 | s1/t2 r4:c2 | general / use | 0 inferred | blank; omitted |
| 14 | 23 | s1/t2 r4:c1 | specific / use | 0 inferred | blank; omitted |
| 15 | 23 | s1/t2 r4:c2 | general / use | 0 inferred | blank; omitted |
| 15 | 23 | s1/t2 r4:c1 | specific / use | 0 inferred | blank; omitted |
| 18 | 23 | s1/t2 r4:c2 | general / use | 0 inferred | blank; omitted |
| 18 | 23 | s1/t2 r4:c1 | specific / use | 0 inferred | blank; omitted |
| 19 | 23 | s1/t2 r4:c2 | general / use | 0 horizontal-total | blank; omitted |
| 21 | 25 | s1/t2 r4:c2 | general / use | 0 inferred | blank; omitted |
| 21 | 25 | s1/t2 r4:c1 | specific / use | 0 inferred | blank; omitted |
| 34 | 24 | s2/t2 r3:c1 | specific / use | -79,725 inferred | visible dash; repaired |
| 62 | 28 | s2/t1 r4:c1 | general / use | 0 inferred | visible dash; repaired |
| 97 | 43 | s3/t1 r3:c2 | general / use | 0 inferred | visible dash; repaired |
| 110 | 30 | s5/t1 r3:c1 | general / use | 0 horizontal-total | visible dash; repaired |
| 113 | 30 | s3/t1 r3:c1 | general / use | 0 horizontal-total | visible dash; repaired |
| 141 | 28 | s1/t1 r4:c1 | specific / other | 0 horizontal-total | blank; omitted |
| 145 | 28 | s1/t1 r3:c2 | general / use | 0 horizontal-total | visible dash; repaired |
| 147 | 25 | s1/t1 r4:c1 | general / use | 0 inferred | blank; omitted |
| 195 | 30 | s4/t1 r3:c1 | general / use | 0 inferred | visible dash; repaired |
| 243 | 32 | s2/t1 r4:c1 | general / use | 0 inferred | blank; omitted |
| 244 | 31 | s2/t1 r3:c1 | general / use | 0 inferred | blank; omitted |
| 246 | 33 | s1/t1 r4:c1 | general / use | 0 inferred | blank; omitted |
| 247 | 32 | s5/t1 r4:c1 | general / use | -1 inferred | blank; omitted |
| 248 | 31 | s3/t1 r4:c1 | general / use | 0 inferred | blank; omitted |
| 250 | 33 | s1/t4 r4:c1 | general / use | 0 inferred | blank; omitted |
| 251 | 33 | s1/t4 r4:c1 | general / use | -1 inferred | blank; omitted |
| 252 | 31 | s2/t1 r4:c1 | general / use | 0 inferred | blank; omitted |
| 256 | 17 | s1/t2 r3:c2 | specific / use | 0 horizontal-total | visible dash; repaired |
| 270 | 31 | s2/t1 r3:c2 | specific / use | 0 inferred | blank; omitted |

### Authenticated dash repairs

The registry now binds 9 source pages and 14 exact null-to-dash cells: the six
previously registered STB consolidated-Q4 cells plus these eight newly audited
cells:

- ord34 BVB p24 s2/t2 r3:c1 — repair
  `gjfrasrv1:repair:e2f8ecc1a44147e4ae6ef8859a5b2a699e1d109efb89890a888eda0598ad237e`;
- ord62 KLB p28 s2/t1 r4:c1 —
  `gjfrasrv1:repair:1635a79c98556a022676a899ad3b608fa7f5ddf5b33e140c786549da60faa1e0`;
- ord97 NAB p43 s3/t1 r3:c2 —
  `gjfrasrv1:repair:200bfdbf06ea34980f1d7c9d1a6ba00184a3e4c89e8d586719849d238c888ee9`;
- ord110 NVB standalone p30 s5/t1 r3:c1 —
  `gjfrasrv1:repair:29937fb03fb28f230b709b06699215ec78de67b105e13f171f5cc33f53964aae`;
- ord113 NVB consolidated p30 s3/t1 r3:c1 —
  `gjfrasrv1:repair:07ac84e5225fa7ad19376ee9ba7f86db94f44af750128051843ecef90fa4554e`;
- ord145 PGB p28 s1/t1 r3:c2 —
  `gjfrasrv1:repair:90a107e3e71e710cc526c6fe8a26f94f77b296c598a3ee6445182045142786ee`;
- ord195 STB standalone p30 s4/t1 r3:c1 —
  `gjfrasrv1:repair:6fe6a7bbfd71689e8f6fe4d05a05715b2bb49d0471807349009d341602f4f91d`;
- ord256 VBB p17 s1/t2 r3:c2 —
  `gjfrasrv1:repair:a9682494c8f362cf5aabf6f49cbd674051028897bed536940eef9fb54cb7940d`.

Every repair binds source SHA/size, document/page/image identity, selected JSON
version and extraction run, base/effective page and table hashes, exact
row/column/cell, 300-DPI render metadata, and table/cell RGB crop hashes.  All
9 page receipts and all 14 repaired cells replay in full271.  Registered
evidence SHA-256:
`77a5447aef7f881d51af2caaca2aff0aefadc70a3a3ada4bc2da9d6135eaa280`
(21,884 bytes); overlay ID:
`gjfrasrv1:overlay:95a021481f24a415a25708e5c09fd3711242768854e5ef2600eab8e861f847ec`.

### Comparator and verification

- Historical policy: `DISJOINT_EXPANSION`.  Both pinned 8-document oracle
  artifacts authenticated byte-for-byte; their 16 source SHAs have zero
  intersection with all 271 current sources.  Trial, candidate, replay, and
  all 14,945 selected-page axes replay exactly.  Historical values are not
  used in the current-corpus conclusion.
- 162 focused F13 evaluator/indexed-wiring/sweep/runner tests passed.
- 16 global source-observation contract/store-ingest tests passed.
- Ruff and `git diff --check` passed on the owned implementation/test paths.
- The legacy live-builder safety suite is excluded from the conclusion and
  currently fails closed because it pins schema revision `@6072` / 1,717 TM
  items while the live schema is `@6076` / 1,721 TM items.  Its persisted
  oracle bytes still authenticate under the disjoint comparator receipt.
- Final owned hashes: evaluator
  `de0bb87ce773a042b03dbb5971c64491e9c7a65a7f81d19f8ebf99d120fe7ce0`;
  evaluation config
  `685fb76faba977ff3d61e893b6f8ceaa055ae6c9090e674c869a27c62864974b`;
  source-repair evidence
  `77a5447aef7f881d51af2caaca2aff0aefadc70a3a3ada4bc2da9d6135eaa280`;
  F13 unit test
  `56a1867a572017c769801dfb4e7f0a96e95780240ac967438c102682c8b479ee`.

## Prior v19 release context

## Scope and final result

- Family ID: `PROVISION_MOVEMENT_ROLLFORWARD`.
- Immutable current corpus: 271 PDFs, 14,945 selected pages, 19 banks, reporting documents from 2025 onward.
- Final full-corpus result: **240 READY / 31 NOT_OBSERVED / 0 UNRESOLVED**, 1,976 mappings.
- Common 204-PDF frontier: **174 READY / 30 NOT_OBSERVED / 0 UNRESOLVED**, 1,460 mappings.
- Added 67-PDF frontier: **66 READY / 1 NOT_OBSERVED / 0 UNRESOLVED**, 516 mappings.
- Earliest validated full-corpus checkpoint was 73 READY / 31 NOT_OBSERVED / 167 UNRESOLVED. All 167 algorithm/source-representation gaps are now resolved; all 73 existing READY and all 31 NOT_OBSERVED statuses remain stable.

Final artifacts:

- `/dev/shm/family13-full271-v19.json` — SHA-256 `f162fe04a8b4dc428f033f0b1acf292a439a30c160398bc70e06449a7796bd0d`, 36,583,167 bytes.
- `/dev/shm/family13-full271-v19.sqlite3` — SHA-256 `7365930e4e2986b286e5be63b592eef50d035b67f3a539ee17edd49b70402b43`, 93,999,104 bytes.
- Sweep ID: `gjfafsv1:sweep:bdb44f3c1307d16756aa8236ca4fa89aa13c737212cacc9ce66beea23e180fff`.
- Pending repair jobs: 0.

## Generic algorithm changes

The implementation remains bank/file/page-route independent. The material fixes are:

1. A shared layout classifier now derives stacked-period, period-table and lane-table orientations from the authenticated component axis, eliminating query/evaluator orientation drift.
2. Duplicate movement rows are projected additively only inside the same authenticated block/lane/period, with exact source-vector receipts and replay validation.
3. Exact date grammar covers quarter ends, cumulative 3/6/9-month reporting surfaces and explicit from–to ranges; single-current-period tables are accepted only with independent fiscal-context binding.
4. Complementary adjacent-page components are clustered only with directional continuation evidence, compatible lanes/units, bounded span and a reset fence.
5. Signed deductions, visible dash runs, horizontal-total-proven zeroes and declared-display-unit rounding are handled by distinct typed receipts. Generic blank-to-zero coercion remains forbidden.
6. Missing Vietnamese movement aliases were added declaratively; repeated exact movement roles remain source-proven additive components rather than silently discarded rows.
7. Candidate replay and the flat sweep validator independently reconstruct orientation, periods, duplicates, equations, endpoint continuity and mapping output.

## Final source repair: STB consolidated Q4

The last unresolved document was:

- `vietstock_bctc/STB/2025/BCTC Hợp nhất quý 4 năm 2025.pdf`, physical page 31, section `s2`, table `t1`.
- Source SHA-256: `b0b7438ed502a175a79940e08b254789d8b766af0524d9bbb0d36171adbe0dbf`.
- Selected page JSON version: `gfpstorev1:json:72e7cdfff70ed6acd6e0cb0b1f54c09ac5e1b32d3d50c7988caf3f0fc35b9bc4`.

Pixel inspection of the exact 300-DPI page image showed six accounting dashes that the selected JSON represented as null: `r5:c2`, `r6:c1`, `r6:c2`, `r13:c2`, `r14:c1`, and `r14:c2`. The repair is not a general blank-zero rule. It is a one-source content-addressed overlay that binds:

- source/document/page/image identities;
- extraction run and selected page-JSON version;
- base page and table hashes;
- exact row hierarchy, label and column header for every cell;
- table/cell crop bounding boxes and RGB hashes;
- exact effective page and table hashes after replacing only those six nulls with visible `-` values.

Evidence: `data/registered/gemini_json_rollforward_source_repair_evidence_v1.json`, SHA-256 `ce7536707d5020eef503a4c4a4e267b619a22a0a66026b43347d1aabeff21a78`, 3,462 bytes.

Overlay ID: `gjfrasrv1:overlay:2caf77d933c8d8ac942dee8285b2a79aad3ec1cbf112a7d0a294fc6eef189f68`.

Repair ID: `gjfrasrv1:repair:ab11a95075f28460dc595ef93f19977e6d109f6757ab9792acec2a7c74b7c744`.

After the repair, all four lane-period equations close exactly, the document becomes READY with 12 mappings, and the final-patch differential is exactly 239 READY→READY, 31 NOT_OBSERVED→NOT_OBSERVED, and 1 UNRESOLVED→READY. The other 270 trials retain identical status, mappings, candidate count and reasons.

## NOT_OBSERVED recall control

The 31 NOT_OBSERVED documents remained constant through every validated full-corpus iteration. The authenticated selected-page query found no qualifying family owner plus opening/provision/closing movement frontier. A whole-document PDF text-layer scan also found no joint provision-roll-forward vocabulary in those documents. They remain in the final cross-family pixel recall audit; they were not converted from evaluator errors or unresolved candidates.

## Verification

- 187 focused roll-forward, indexed-wiring, flat-sweep and generic-runner tests passed.
- Ruff passed for all changed F13 Python/test paths.
- `git diff --check` passed.
- Registered evidence artifact hash/size and base/effective page/table hashes are replayed in tests.
- Tampered base page, region binding and effective-page hash fail closed.
- Full immutable-corpus replay completed with zero pending repair jobs.
