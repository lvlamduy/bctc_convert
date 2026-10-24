# F36 experimental unlabeled totals and complete ORIGINAL inventories

This checkpoint follows main 9c6e15c16a022be45fb69b1c8471ca3d152c51ca. It integrates only the reviewed four-path T delta from worker 746c822a2beed9c2d3044bce0494a51c6d7f4162. The neutral inventory and pure root-closure prototypes remain isolated. This is an opt-in notes improvement, not a family seal or production acceptance ledger.

## Result and source boundary

An unlabeled printed closing total previously remained SOURCE_ONLY. OPEX now recognizes it only when its own subject is printed, exactly one ORIGINAL TOTAL is unlabeled and parentless, it is the final source row, and every preceding row is a proven top-level component or direct/exact-wrapper detail. Blank components, unknown rows, nested components, unresolved captions and any suffix refuse the route. Equations validate the selected printed values; they never select membership or backsolve amounts. Existing declared rounding is unchanged. Labeled/default/non-OPEX routes keep their previous rules.

T changes only concept_list_shape_v1.py, config_v1.py, the OPEX notes YAML and its new test. Final source SHA:
- Core: 1d04b399be1beaf455783cbad982ba76e5a67bb86dae1cf186789f76c32c68fa
- Config loader: 5fbe9d23b4c61424479dae0949516cd89e0002df2336a1f96baa7618ef9e0712
- OPEX YAML: 162e291da78e2908b1908ec76e89856712867fa7494b681263dce17b7bce79b2
- T test: 9ca7a443da85867f51411f1f361cdaa30574c9baab74942fe64b61d6cc7d7456

Stable exporter, legacy F36/F39/F37, default dispatch and both frozen shared files are unchanged.

## Actual focused gate and retained failures

214 normal tests, zero subtests/failures/errors/skips; both JUnit denominators214; compile/Ruff29, eleven actual origins and2164 source+2 control refs PASS unchanged. Receipt:
`/srv/bctc-receipts/notes-unlabeled-total-integrated214-v3-20261025/REVIEWED_CASE_MANIFEST_FOCUSED_V2.json`
SHA ef0a42940f51c332567d2db8513808a8f23aef30c0e1061cbd3c2a0cf121363f (1697200B).
The old181 assertions remain, with33 new T cases.

Retain d176 Ruff-before-collection FAIL d5c8fc88f432dd4b0e1fde8bf249df107ab589207097ebfbbfa42e2c497adea0 (1497601B). Test-only132 fixes the import. Its actual213/1 FAIL receipt9174492ca8592f82288f196f64ffda2d768b96a0ba645dd496b273b4ec4f1980 (1697502B) exposed an incorrect synthetic expectation: residual1 is inside existing million-unit rounding. Test-only746 changes222 to250, residual29, preserving every assertion and all production rules. No failed receipt is relabeled PASS.

## Actual complete corpus pair

FULL root: /home/bctc/notes-runs/full271-20261024T191148Z
COMMON root: /home/bctc/notes-runs/common204-20261024T191859Z

| Artifact | SHA256 | Bytes |
|---|---|---:|
| FULL terminal.json | 39793e08ca73c10c288b6863dc050a7bca5492fb3299a479190459b5683fd689 | 651 |
| FULL out/run-manifest.json | 9921187773d4f5ea240cfbee026c45c38a5edd8c90a5f2c3cc8d3446aaa8eb1e | 152164 |
| FULL out/notes-results.sqlite3 | 662adef485797099a45ca0da3183a0e772091456b6650a39ff0696846a7db947 | 66899968 |
| FULL out/dispositions.json | 2ec80187b94890d9b5e7b382f9c4238aa04c4d4979ac55b23fd052ca4727ec27 | 18993379 |
| COMMON terminal.json | a6afefad09c3329ea16bb34a83a5cdf5304d66f4567eb483ab458b07295ce908 | 653 |
| COMMON out/run-manifest.json | c9b8856d00acf40849cc79dba5a9ed18f7ec3a7f23856667e7ca0efb3a20036a | 120114 |
| COMMON out/notes-results.sqlite3 | e7fef94365b4feebfb386c3cb623971a46c43ff9bcac5a9d374fe4cf011f4720 | 50118656 |
| COMMON out/dispositions.json | c4f83c5124a8705cc712de051fbbf32d701bb6910baf25a85bb7984fe7c2f479 | 14393578 |

Both terminal PASS_DIAGNOSTIC with unit/source/PRIMARY/helper and complete source-axis barriers. Producer quick_check, exact typed reload, fresh-process rebuild cells and all emitted workbook cell readback passed.
FULL:30704 observations including HOLD,271 books; digest75c28b77c3b317f8614ff8ed671ccd11f3a7b9822072e487bebb881bb82d8f5c.
COMMON:22996 including HOLD,204 books; digestd049078abd350f4a741a2d92cc4d14d9f351abd201843962080309b568fe5312.
FULL total388.926s/evaluate113.636s/RSS665680KiB; COMMON249.798s/73.125s/516884KiB. Total includes a second independent evaluation and export/store work, not just retrieval.

## Actual complete typed deltas against stable7cdb

Comparator0796ef4275c46b239b2ff18fb611930bb82e7f7ad539d5fce53b9fa95c65f8dd uses bounded per-document ledgers; no ORIGINAL SQL/PDF/provider or financial grant.
FULL receipt `/srv/bctc-receipts/notes-t-746-full271-delta-20261025-v1/NOTES_STABLE_T_DELTA_V1.json`:
2a3274ede31dc5aa93df758284c726de235693699a87a40eb0b79cc156eec8e1 (601782B).
COMMON analogous `notes-t-746-common204-delta-20261025-v1/NOTES_STABLE_T_DELTA_V1.json`:
aef47d7bf98a5f947a9269100f7fc822a10e46f9c691d1562635df673eec5940 (477960B).
Both COMPLETE_DIAGNOSTIC_DELTA_REVIEW_REQUIRED/errors[]/inputs unchanged. Non-OPEX observations, dispositions and semantic summaries are exact; every paired numeric/source/state/unit/period/sign payload is exact. Only separately pinned global OPEX-config metadata changes.

FULL:36 changed OPEX tables,72 new observations (51ACCEPTED/21HOLD),272 HOLD-to-ACCEPTED. All14278 previously accepted observations retain their acceptance; no loss.
COMMON:29 changed tables,58 new (41ACCEPTED/17HOLD),226 HOLD-to-ACCEPTED. All10783 previous accepted remain.
The corpora overlap: these are not additive counts of distinct facts. Gains are experimental local notes results; new-only cells still require independent source/root review. Ledgers retain every before/after occurrence, including unchanged accepted cells and all remaining HOLDs.

## Complete neutral ORIGINAL denominator: isolated906

Candidate906731fad74465d676b1b0dc5ece458285f33d90 is not integrated. Actual18 real-SQLite tests passed with compile/Ruff2,7 origins and2165+2 refs unchanged; receiptff2eabf9f06e0ebfdbc6c0eaa6bcca07723fa103e4134d3aa6be3d47b4958b23 (1507679B).
Controlled launcher d675991d85cc73e931ee50e5440516d1d18c732e37de8a2947c0c46e6f317ba2; case dd9a2ea0762a1950c7485c9adbfad944f2b974ab36689bae36599a8f74bf9065. Both complete profiles actually PASS, no status or family filtering. All manifest/selection/image/prompt/provenance and same-held-FD source checks, source-context exit, SQL quick_check/foreign_key_check before+after and final code/control barriers passed.

FULL controlled receipt:
`/srv/bctc-receipts/f36-neutral-original-inventory-full271-20261025-v1/F36_CONTROLLED_NEUTRAL_ORIGINAL_INVENTORY_RUN_V1.json`
98a0677d48d6d52fba37a0cde4b2dc83df064ba65a26537c5b6e98df1457511c (1097083B).
271docs/14945pages/19465tables/171311rows/581227value positions; CPU67.074936s/wall68.511870s/RSS149432KiB.
JSONL56167838f53dfd967c4d91ed7ae269350dd465ecfb19d8c1f529aafb77e99fe5 (228533818B).

COMMON controlled receipt:
`/srv/bctc-receipts/f36-neutral-original-inventory-common204-20261025-v1/F36_CONTROLLED_NEUTRAL_ORIGINAL_INVENTORY_RUN_V1.json`
b76f007f85402ecac51eb7b1c4d9ecd5cf726e3eccfd751aa0deca323ced21e2 (1097091B).
204docs/11454pages/14847tables/130623rows/442892positions; CPU83.397010s/wall91.889721s/RSS128684KiB.
JSONL6eac9435b205e8c2b335c301adc8fabb3f550f99aa7fca544b45d3c8a475d8fa (174352725B).
These inventories are neutral source structure, not financial relevance, ownership, report absence or acceptance. Preserve explicit stored-BLOB2LF, canonical-object1LF and notes-table0LF hash domains.

## Historical legacy mapping fields and remaining acceptance

Both bounded historical field inventories passed exit0/inputs unchanged: FULL8dd542ffaf4f6c36bdf5d5010b22905dd7281c8b217172e1dd6369395941a920 (89059B), COMMON2df65d7694ec1af019a0fa231b7ab984c49c64ca71afa38736557d0e2ec336ac (68566B).
They inventory2975/2204 final proposal mappings. Source refs contain VID/page/section/table/row/money-column coordinates; values contain source_text/coefficient/state. Some mappings have multiple refs; no arbitrary first-ref match is permitted. Mapping records have no period key: outer period evidence is still unjoined. Historical proposals are not canonical accepted stores.

F36 WHOLE_TABLE/REQUIRED_SOURCE_VISIBLE_EXACT_ROOT remains binding. The isolated pure closure8befe was rejected statically for reading real presence/value envelopes as flat fields; its synthetic fixtures masked that schema mismatch. It is unrun/unpromoted, pending one bounded correction and actual packet compatibility. Complete source/frontier/canonical legacy joins, all-status cold evidence, residual/PDF audit, canonical export and terminal ledger remain separate. Notes-accepted flags cannot waive them or imply a family seal. F39 has its own optional-root policy and is not automatically subject to F36 closure rules.

For development, use existing affected-family/explicit-document CLI first, then complete affected-family replay. Shared source/kernel/export changes require broader regressions; terminal full/common gates remain. Reuse stored Gemini/index/PRIMARY and immutable denominator artifacts; do not cache financial acceptance or relabel old artifacts with a new head/config.

Fresh192-version S3 coordination review before main mutation passed: f37dbc89cf5968b4410bfb4cc1f8dffd077aaf297e8b7a1eadecd1f3f63d06b6. No competing owner. New artifacts are LOCAL_ONLY until separately backed up.
F36/F39 remain UNSEALED; legacyF37 unclaimed/unmodified, F41 locked. Scope2025-current with printed comparatives; standalone2024 excluded. Provider calls0; no re-extraction, immutable S3 rewrite, old artifact cleanup or integration-branch push.

All2164 integrated source-file SHA/size pairs equal the actual214 worker receipt; frozen hashes and Windows read-only attributes passed. External source-projection verification receipt228a3de2c062391a367f469e2d171607f6087797d98499ffda3a47ce7345de8b (437B). This establishes source equivalence, not a counterfeit main-HEAD test receipt.
