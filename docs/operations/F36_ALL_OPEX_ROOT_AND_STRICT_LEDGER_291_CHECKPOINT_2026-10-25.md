# F36 ALL_OPEX topology and strict-ledger291 checkpoint — DRAFT V2

Date: 2026-10-25. Reviewed additive integration checkpoint on the task-owned F36 branch. This records actual closed diagnostics and the pure classifier integration; it grants no financial acceptance. Both immutable outside-repo drafts remain preserved.

## Scope and code ownership

The integration parent is main `9e51eccd61326157bb6a8eb3b3572e54b6c8d74c`. The isolated, pushed worker `6ce7e1d0188d502e8a762fa9726a52dd7f5f0f90`, branch `codex/notes-strict-ledger-currentbase-draft-20261025`, contains the reviewed pure strict-ledger module/tests with the same bytes as Claude commit `adb13edaf7aedb8537dd979c1b10215bf09d1b2c`. Only the two new pure classifier/test files are integrated; existing producer, mapping, persistence, exporter and default command paths remain unchanged.

The commit containing this document records the additive integration. The actual tested/runtime worker remains `6ce7e1d0`; existing artifacts are not relabeled as produced by this integration commit.

The independent full main working-file/staged-Git source projection passed for all2168 tracked source inputs, both external case/helper refs, held identities/bytes and frozen readonly attributes. Receipt `D:/bctc_bank/restore-receipts/NOTES_STRICT_LEDGER_MAIN_STAGED_SOURCE_PROJECTION_20261025_V1.json`, SHA256 `1717fd5b033292a9c93c3c288bbb4c4563c7b1f413cf5aad3642988bf19c671f`,2027B. Root independently verified the whole2168 Git index blobs: receipt `NOTES_LEDGER6CE_TO_MAIN_SOURCE_PROJECTION_VERIFICATION_20261025_ROOT_V1.json`, SHA256 `14890b627b19a6abeed22221541fc8a15bc658c74ecf21cfe07a81a710f5689d`,596B. This is source equality to the actual291 test tree, not a claim that tests were rerun on main.

Before this mutation, exact-Version S3 coordination reviewed193 event versions and193 latest events with no F36 owner conflict: receipt `f36-pre-promotion-coordination-20261024T210658767963Z-24368ca54fbe402686891812b2c4f665/F36_PRE_PROMOTION_COORDINATION_REVIEW_V1.json`, SHA256 `0936736714f0d1d91240eb49ca51a464a604b62a92e6737516f06d2bb0908cb2`.

F36 and F39 remain unsealed. F37 is untouched/unclaimed; F41 remains locked. The user's authorization to continue F36 after the saved unsealed F39 checkpoint does not waive source, financial, replay, integrity, ledger or terminal gates.

## Actual ALL_RETRIEVED_OPEX topology results

V5 completed both profiles with `PASS_COMPATIBLE`, empty failures, all19 built-in controls passed, and source/unit/held-FD/byte barriers passed. This covers the retrieved OPEX candidate frontier, **not all ORIGINAL tables as financially relevant or irrelevant**. Unretrieved ORIGINAL tables remain unassessed. The complete neutral ORIGINAL denominator remains a separate source artifact.

| Profile | Retrieved table packets | SAME / CHANGED | Source fragments | Closure EVALUATED | Unsupported merge | REJECTED | Source-parent UNRESOLVED | ROOT_CLOSED lanes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| FULL271 | 1,638 | 1,602 /36 | 1,719 | 217 | 19 | 1,362 | 40 | 84 |
| COMMON204 | 1,208 | 1,179 /29 | 1,267 | 167 | 13 | 1,000 | 28 | 70 |

The two corpora overlap; their counts must not be added as independent financial facts. ROOT_CLOSED is a lane topology result, not financial acceptance. The predeclared FULL69 physical64 positive closed both lanes.

The retained V3 compatibility failure exposed40 FULL source-parent gaps. V5 does not repair them or select an owner: it explicitly retains40 FULL gaps (38 non-self-ended paths and2 duplicate GROUP cases) and28 COMMON gaps (26+2) as `UNRESOLVED:PARENT_EDGE_DIFFERS_FROM_ORIGINAL:r<k>`. These tables cannot enter the strict core through that unresolved closure. The V3 failure and its censuses remain evidence; they are not relabeled PASS. The earlier overwritten UNRUN V4 pin loss was acknowledged separately and is not source/S3 corruption.

Bind each actual summary, results and build receipt together. The terminal JSON alone is insufficient: its raw hash happened to equal the earlier36/29-table terminal text.

### FULL271 closed references

- Build: `/srv/bctc-receipts/f36-all-opex-real-table-packets-full271-20261025-v1/F36_T_CHANGED_TABLE_PACKET_BUILD_V1.json`; SHA256 `a6a094ee09d58eff93463bc47af87329720717248ac8811494570cef64a96adb`; 347041B.
- Summary: `/home/bctc/notes-compare/root-closure-actual-full271-69fe05d0-20261024T205313Z/out/summary.json`; SHA256 `d72f0bddf2ea79b074ca2b4c8ae6b6e3ac6c40c88fbd307adca5f9c6e28d2533`; 3237B.
- Results: same `out/` directory, `results.jsonl`; SHA256 `86f3746cadce30227fc414da3248ddc3433ad77234181a45a46a8249d81501dc`; 995006B.
- Held inputs in the closure check:1639, comprising the build receipt and all1638 packet files.

### COMMON204 closed references

- Build: `/srv/bctc-receipts/f36-all-opex-real-table-packets-common204-20261025-v1/F36_T_CHANGED_TABLE_PACKET_BUILD_V1.json`; SHA256 `d5f1efea3e613114ba1ccf18010e3a9adde0073cb457c07fb7ce3d5a4d7f4664`; 258757B.
- Summary: `/home/bctc/notes-compare/root-closure-actual-common204-69fe05d0-20261024T205331Z/out/summary.json`; SHA256 `c5f9c88a110004aad4499207d4bf0f92d4425f930cb6704edaccb1ef01a94358`; 3206B.
- Results: same `out/` directory, `results.jsonl`; SHA256 `91118411092cabbfa9b202ccde56dd9ac33816dc7072ddf63c140417ae114833`; 731632B.
- Held inputs in the closure check:1209, comprising the build receipt and all1208 packet files.

## Actual integrated291 unit gate

The strict-ledger prototype adds37 tests to the unchanged254-test baseline:291 normal tests over11 modules. This is an actual PASS, not a planned count.

- Receipt: `/srv/bctc-receipts/notes-strict-ledger-integrated291-v1-20261025/REVIEWED_CASE_MANIFEST_FOCUSED_V2.json`.
- SHA256 `f572cb46ff5468c42b9e4b41118fb3e959e918bc7d4df1d2706f11452ad9624a`; 1767054B.
- Actual291 normal calls,0 subtests,291 JUnit declared tests and291 testcase elements;0 failures/errors/skips. Compile/Ruff passed, `inputs_unchanged=true`; reported peakRSS100616KiB.
- Case: `NOTES_STRICT_LEDGER_INTEGRATED_291_CASE_20261025_V1`, `/mnt/d/bctc_bank/restore-receipts/NOTES_STRICT_LEDGER_INTEGRATED_291_CASE_20261025_V1.json`; SHA256 `8c251092a6575e0f99b54d5503d83be50fdb1282a31c322e1093ab95dfa26a3e`; 296336B.
- Reviewed worker module: `src/bctc_ai/notes/f36_strict_ledger_v1.py`, SHA256 `f2e3cdb33ab6d7fbf20abd9ad91aca7e94e6514af5a7c44acc442494754fd044`,17303B; tests `tests/unit/test_notes_f36_strict_ledger.py`, SHA256 `50e66168ddedae79658a855c83edee4b68aace37f1ed87a822ac919ade9ccbcf`,12842B.

The API is a classification join over authenticated producer observations, actual topology results and ORIGINAL inventory references. It does not rerun the financial algorithm or grant source/unit/period semantics from a flag. `CORE_CANDIDATE` is not `ACCEPTED_CORE`. Blank/dash/control states remain separate; missing or malformed direct legacy axes cannot create an agreement or contradiction.

## Actual strict-ledger diagnostic pair

Both serialized profiles completed with native exit0 and `PASS_LEDGER_CANDIDATES_NOT_ACCEPTANCE_LEGACY_NOT_SUPPLIED`, failures empty, and all source/code/held-input gates passed. These are actual candidate/backlog classifications, not a family seal or financial admission. The runner reused actual topology results and authenticated notes/neutral artifacts; it did not access ORIGINAL SQLite/PDF, re-extract, call a provider or re-evaluate financial algorithms.

| Profile | All notes cells | OPEX cells | Targets /fragments | All ORIGINAL tables | CORE_CANDIDATE | ACCEPTED_SOURCE_ONLY | Printed blank/dash | Final held inputs | CPU /wall seconds | PeakRSS KiB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| FULL271 | 30,704 | 6,894 | 1,638 /1,719 | 19,465 | 685 | 175 | 22 | 1,645 | 19.17 /19.27 | 453,444 |
| COMMON204 | 22,996 | 5,124 | 1,208 /1,267 | 14,847 | 544 | 128 | 14 | 1,213 | 13.99 /14.05 | 345,188 |

Counts are classifications in overlapping corpora, not additive unique financial facts. Parent-edge gaps remain unresolved; unassessed source is not absence. Period/unit/row gaps and all other backlog classifications remain retained in the observations/row/table ledgers. The printed blank/dash label does not assign a numeric zero.

### Actual FULL271 ledger artifacts

Root: `/home/bctc/notes-compare/f36-strict-ledger-full271-adb13eda-v1`.

- `out/summary.json`: SHA256 `063239726eca3788cc9f215b5295ffb2a91a6fd5940eb7c28e67d4f607ddfe2b`,4568B.
- `out/observations.jsonl`: SHA256 `5b268ca218b5ff4fc6e659d9a33c239f968964064ac282ca781010751e69c5e5`,10927678B.
- `out/rows.jsonl`: SHA256 `c591bf928a2ba15cbe84d2a2fb1629ddeab3326ea32fd7f71272265975d5f2e3`,8138420B.
- `out/tables.jsonl`: SHA256 `6cef248fb03e6d81df6434be732e66e112a87f62c79d029e689c33a3d1b2a0be`,3284578B.
- `terminal.json`: SHA256 `0092a62ead000267869d06b1769feecaadf8351003f6a827c6b432794c884402`,488B.

### Actual COMMON204 ledger artifacts

Root: `/home/bctc/notes-compare/f36-strict-ledger-common204-adb13eda-v1`.

- `out/summary.json`: SHA256 `b2e3ed2a16cd8af5fb17ba47d641f2b993830cc7cfd69fb9c6778151e8e1203b`,4381B.
- `out/observations.jsonl`: SHA256 `1a85b47b44fedbef90fe9d906106a9af21859498821319f9b9b18bd5a28e9ff2`,8107816B.
- `out/rows.jsonl`: SHA256 `39afaa5a0a7276712006bf1bf2e0a7d62ebf1caefdb0158f38abc27ab84172cb`,6067936B.
- `out/tables.jsonl`: SHA256 `8c7bd08172405f3a2ad2b848e13a30f1ed2cd413def75b89c8fbf411566b5329`,2497060B.
- `terminal.json`: SHA256 `902ba10d89d95eb0eebe95555b27cdc46e883742c78065c56e42ded61d0cd6cc`,490B.

Each `out/legacy.jsonl` is empty (0B), consistent with NOT_SUPPLIED rather than successful legacy accounting.

### Execution authority and retained UNRUN predecessor

The external runner remained `f36_strict_ledger_run_v2.py`, SHA256 `491fd8ef7b00902fac43065bcae067ba886474fcf72872aa11d7ea2af30a5893`,19899B. Root's corrected additive controls under `/srv/bctc-receipts/notes-strict-ledger-root-path-correction-controls-20261025` received static GO and were the actual execution authority:

- `f36_strict_ledger_control_codex_v3.sh`: SHA256 `df34989a5deae6034066f33145851d85000dbc29e701fd2978db7d2394801c03`,5334B.
- `f36_strict_ledger_spec_full271_codex_v2.json`: SHA256 `4713cd1ebf47dbbce7a3e956092932c6234aab7657519b1b7f8374e773def54f`,1614B.
- `f36_strict_ledger_spec_common204_codex_v2.json`: SHA256 `fef6895a25d0469d8b7dafaae95c156d86231bcb1242bb58131ff32d268ccf15`,1630B.

Runner491fd and gateV7 `58386e66a3bf10fa5d10ab524d93a24058ebae463f08e15ef1be178a8643bf67` remained unchanged. The reviewed initial bounds were1GiB AS, CPU120 soft/180 hard, wall300+20, nice19, one serialized profile per fresh fixed output, no retry.

The original frozen v1 control/specs remain preserved UNRUN: they omitted `/out/` from four store/manifest paths. The additive root correction changed only those paths and the corresponding spec names/hash/size/control source directory. No financial predicate, source byte, schema or resource cap changed to obtain these passes.

`legacy_proofs` must remain null. The runner rejects supplied legacy proofs until a reviewed extractor authenticates every mapping/value denominator. `legacy_accounting_complete=false`, `legacy_gate_passed=false` and `terminal_financial_ledger=false` remain mandatory. No legacy completeness, financial acceptance, canonical output, family seal or complete-project backup is established here.

The next work is experimental core/backlog SQLite and Excel projection with exact source readback, keeping the40/28 source-parent unresolved cases. Canonical persistence/export, complete legacy accounting, independent source/replay/integrity and PDF/residual/terminal closure remain separate required gates; this checkpoint reports no PASS for them.

## Metadata provenance

The outside-repo metadata draft used root-authored exchange0353 (`all-opex-v5-actual-and-ledger291-prep`),0355 (`ledger291-actual-pass-controls-review`),0358 (additive path correction) and0361 (both actual ledger passes), the immutable worker/code pins supplied by root, and metadata-only existence/size/SHA checks of closed derived outputs. Row/table JSONL hashes were computed without parsing financial payloads. No test, project import, financial data parse, SQLite/PDF read, provider call or upload was performed to create this draft. Root subsequently integrated the reviewed pure module/test, this operations document and its AGENTS pointer after the actual source projection/coordination gates.
