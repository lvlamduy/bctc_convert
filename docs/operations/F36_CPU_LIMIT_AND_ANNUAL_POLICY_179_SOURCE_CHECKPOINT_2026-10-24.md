# F36 CPU-limit failure and the annual-policy 179/source checkpoint

This follows main `4cd8cef9fa97027b7b9ded39bcdc1e00438cfd4b` and the prior
notes88 delta/live-FULL checkpoint. Main production source is unchanged. Notes
remains experimental and unintegrated; F39/F36 are unsealed, legacy F37 remains
unclaimed/unmodified, and F41 is locked. No provider calls or source writes.
The corpus remains the current2025 reports, retaining their printed comparatives.

## Legacy FULL271 V4 stopped at its CPU limit

`/srv/bctc-receipts/f36-full271-empty-suffix-v4-20261024T083500Z/`
is terminal, not LIVE. Wrapper exit1; producer exit152/signal24 (SIGXCPU),
user6585.19s/system174.29s, wall1:58:15, peakRSS2308888KiB. No diagnostic.json
was produced, so no new READY/U/mapping counts or corruption finding exists.
Execution result1160873bytes:
`c5fe05a23f31e18bcc59921d5c5fbe9950cce8646ed076207a21a6ab799b29e1`.
Code-before/after PASS; source-before/after PASS_FILE_PINS_NOT_SQL_INTEGRITY;
both file barriers exited0. The only recorded error was producer nonzero exit.
All recorded owned groups/PIDs were verified absent at10:37:17UTC; no restart,
cap increase or legacy COMMON run was authorized. The small six-case matcher
gain did not establish that this whole producer would finish within its budget.

The proposed concurrent unit exception was NOT activated: actual Windows host
PhysicalAvailable569901056bytes failed the1536MiB gate. The inactive draft
`restore-tools/drafts/run_notes_unit179_bounded_parallel_v1.py` is UNRUN,
NOT REVIEWED/NOT GO; never use it as a scheduling authorization. Serial unit
execution began only after the legacy producer and its owned children stopped.

## Actual failed V14, then corrected V16 PASS

V14 at3ba84e2d in `/home/bctc/notes-pytest/20261024T103847Z/` is retained FAILED:
179 collected/JUnit cases,178PASS/1FAIL/0errors/0skips. All new30 passed;
old149 yielded148PASS/1FAIL. The old shadow-invariance test failed because a new
ANNUAL_POLICY_NOT_APPLIED reason changed default annual_policy=None output.
Do not weaken or filter that old equality assertion. Launcher stopped atJUnit;
the independent late49-pin check is separate evidence, not a launcher PASS.
Root verification11542bytes:
`D:/bctc_bank/restore-receipts/NOTES_ANNUAL_3BA84E2D_ACTUAL_179_FAILED_UNIT_VERIFICATION_20261024_V1.json`,
SHA `98ac1a3edc0f5dae918a20189dff9806ffc8aa70bcdde45ec3ef54689c7dee1a`.
HEAD/origins/clean Git and all49 source hashes were independently unchanged.

The additive correction uses `document.annual_policy is not None`: absentNone
preserves the old complete output; present malformed captures still undergo
verification. The five new absent/untrusted-policy cases remain, with theNone
case asserting the exact old lane and the direct helper's explicit absent reason.
No old149 test was changed to make the correction pass.

Corrected06e53b6a86e9b1c759fc30084e323bc0020f9597 V16 actually PASSED179/179,
0failures/errors/skips in `/home/bctc/notes-pytest/20261024T105528Z/`.
All old149 and new30 passed; all49 before/after source pins were byte-identical.
Root verification11103bytes:
`D:/bctc_bank/restore-receipts/NOTES_ANNUAL_06E53B6A_ACTUAL_179_UNIT_VERIFICATION_20261024_V1.json`,
SHA `89d25d257668cf61091b82a4945476658784c991c6fb861821fba75a7bf4c816`.
Terminal209bytes `467eebeb870b6408e14fdb0852141a62af7c40abd1044805401f6cc4a3d5afe8`;
JUnit28833bytes `bbe614d500c5b7b4c3f1748b45824c6003c62e633eac94bab6ae89fbf1d98624`;
pins5305bytes `58717aa6d94e2ffc3d621b72efa5ea05e8027d703b913142e3962dedf7b8729b`.
This is a unit gate, not financial or corpus acceptance. Earlier snapshots remain.

## Fresh original FULL/COMMON SQL integrity is now supplied

Root's serial read-only quick_check/foreign_key_check actually PASSED both
fixed original databases: quick_check=ok, FKempty, no sidecars, all5 held
helper/index/database inputs unchanged. Elapsed10.51s, process exit0. Receipt:
`/srv/bctc-receipts/full-common-source-sql-integrity-20261024T110334Z/FULL_COMMON_SOURCE_SQL_INTEGRITY_V1.json`,
2662bytes, SHA `f39ab02fa5a20302f9c73b0ae76ea676332706b4dca088364ab3f9949192df84`.
This supplies the fresh SQL gate separately from legacyV4's file-only barriers;
it does not reclassify the failed producer or grant financial/source-PDF approval.

## Annual06e FULL/COMMON diagnostics and complete V7 ledgers passed

FULL run `/home/bctc/notes-runs/full271-20261024T112514Z/` actually returned
PASS_DIAGNOSTIC/exit0 with all runtime children stopped. It produced30632
observations INCLUDING HOLD/blank/dash and271 workbooks, not30632 accepted values.
Storequick_check=ok, reloadPASS_EXACT, fresh-process rebuildPASS_EXACT_CELLS,
typed export and source-before/after PASS, code pinsUNCHANGED, helper bytes
BOUND_START_TO_END, unitBOUND. Wall334.61s, user309.37/system24.93s,
peakRSS656580KiB. Retained output pins are:

| File | Bytes | SHA256 |
|---|---:|---|
| terminal.json |596|b23a31a7559d99d4456939b5a1af67f807a68289cad064aa1eed3f2c82e7e0b9|
| out/notes-results.sqlite3 |66650112|b8d0092a80a4da170fdd914dbe336e7de5fcbb7ac74b0b29978cd4f8f4d86c7c|
| out/run-manifest.json |152074|3d5301fb172380e0d63635b59e49de1587d90b8129dc1d083408b761ebb76492|
| out/dispositions.json |18972847|76fbaf748f9ea95ad81d6f9ba7771c23618542c0f5a7ace8fa15f72634c3defa|
| closure.json |16069|3df38eeb2752452bac1c4ae2c5fe23c20c133b619a4813bbcc97b2aa744bb343|

Cells digest `11d61fc1d109611911950806ddce6a89ba8ee6c685549968020a93687548d225`.
Annual-policy253assertions resolved61VERIFIED and210UNRESOLVED DOCUMENTS;
these are not new accepted-cell counts. Reasons may overlap.

COMMON06e `/home/bctc/notes-runs/common204-20261024T113841Z/` is now actual
PASS_DIAGNOSTIC/exit0:22938 observations includingHOLD/blank/dash,204workbooks,
wall235.46s/peakRSS524492KiB. The same quick_check/reload/fresh rebuild/typed
export/source/code/helper/unit gates passed; all runtime children stopped.

| COMMON file | Bytes | SHA256 |
|---|---:|---|
| terminal.json |598|d1ec4b4a35fe9a3743783e980c736d6606d1cc6ae38b0e0f0836627402526608|
| out/notes-results.sqlite3 |49942528|0974d5c1998db167ca79de6fb47e73e83273d052787c7aa56b0204a42ba17122|
| out/run-manifest.json |120016|7074d90af2857fdec6209b6dbaab8aef5fb0e9918a2e3090df01feba6a48b30f|
| out/dispositions.json |14377042|d370e92fa87d4a082d6d210c39b006423e550f67731eed7e129d2a66674bcc42|
| closure.json |16075|07f2111e4f97a009768c6108a322b07aecd3a6af698430fd8bdcbbd817947056|

Both complete88-to06e V7 comparisons actually PASSED under unchanged limits:
FULL `/home/bctc/notes-compare/delta-ledger-v7-full271-88f5-06e5-20261024T114821Z/`,
summary5609bytes `4f1fe0163cad46166120a4bdef56917861fbe00d1507690bdc73c09ea5d94e8f`;
COMMON `/home/bctc/notes-compare/delta-ledger-v7-common204-88f5-06e5-20261024T120010Z/`,
summary5625bytes `788c4165fea7806fec9f5b017aad28b919016c6f3c52374ce8c5302243fe916d`.
Each has140CHANGED observations in7tables:20OPEX HOLD-to-ACCEPTED,120HOLD-to-HOLD.
All numeric values/unit/raw/observation states are unchanged; every old accepted
record is SAME. Zero one-side/multiple/unlocated/unkeyed groups, invalid source
identities or input drift. The corpora overlap: not40 distinct new source facts.

Each ledger has50 year grants (25each printed2025/2024) for the same LPB report,
FULL69/COMMON45, allSEPARATE. Its captured policy is p12 narrative5, not a
standalone authentication: fresh collector/ORIGINAL bridge and PDF evidence
remain separate. Rule review directory:
`/srv/bctc-receipts/notes-annual-06e-delta-rule-review-20261024-v1/`;
full271.json1242bytes `a7dd04f88bcdd415f517af4dfaa434904e4a4a555e18bd636429a2f646c2e335`,
common204.json1246bytes `8b0c584ddf5f1bc9440cd6896f9ed0db9f426ed27009034fee9c473100221aaf`.
Both RULES_HOLD/0violations. Of50 granted observations,30remainHOLD:
18NO_EQUATION_OR_PRIMARY_PROOF and12unproven-line cases. The other90changes
are denied-policy diagnostic reasons only; they do not grant periods.

Root visually checked complete ORIGINALp64/printed63: all20 accepted OPEX
observations' labels/values/units/own printed years match. Source PDF SHA:
`d3cf5756961841199cb971f494d7579c05095964284b6dc82a45dafbc563fab7`.
Visual audit42359bytes:
`D:/bctc_bank/restore-receipts/LPB69_OPEX20_PAGE64_COMPLETE_VISUAL_AUDIT_20261024_V1.json`,
SHA `072e387ae27c3241d3917eed73406c9c16e17df5daef66d3a811dfd58afc0b72`.
There are16 observations withNormId and4source-only/nullNormId (Rent and
OtherAsset across two years), not20 new Excel cells. Exchanges0271–0282 retain
the exact controls/results. These diagnostics and visual checks do not seal a
family or promote the experimental notes engine into main.

## Next algorithm work remains bounded and unpromoted

F36 batch-authority draft6ee7d29fe15bf07c1baa46b9c5fc287a1c9c1df7 changes
two family modules; its targeted17 are now actualPASS/0failures/errors/skips,
0subtests and17JUnit elements. All3 changed Python files compiled in memory,
Ruff exited0, the complete17-call axis passed and2128 held refs stayed unchanged
(2126tracked source inputs plus the helper and external case).
Receipt1480680bytes:
`/srv/bctc-receipts/f36-batch-admission-target17-v1-20261024/REVIEWED_CASE_MANIFEST_FOCUSED_V2.json`,
SHA `b5ae0ae3706f8bbc29db1e982430a2d02653d6f5df08f0b799bec061d4103f96`.
Earlier944d593e test-draft issues were corrected. The draft remains unpromoted,
with no financial-result cache or actual-original-source equality claim.

Broad attempt1 is retained FAIL during initialization, before collection: root supplied
the nonexistent F36_BATCH_ADMISSION_COMPOSED_REGRESSION_CASE filename.
It collected0 nodes and executed no pytest; missing complete held-source snapshot
is incomplete initialization, not evidence of input mutation. Receipt2610bytes:
`/srv/bctc-receipts/f36-batch-admission-composed1120-v1-20261024/REVIEWED_CASE_MANIFEST_FOCUSED_V2.json`,
SHA `932a66d158bd2b815c7c3d45e34df15f8a9cff91e56c67e1a48a2e8895794f42`.
The actual case is `F36_BATCH_ADMISSION_COMPOSED_CASE_20261024_V1.json`, SHA
`dfed20718eae70ac68f9940abc386def4303426337ddcdd874a654310c5bcfd4`.
Root corrected only the control invocation, with fresh output
`/srv/bctc-receipts/f36-batch-admission-composed1120-v2-20261024/` and the same caps.
Broad V2 is root-only LIVE session54694/initialPID487621; Broad1120 remains
NOT PROVEN pending its actual result, not PASS.
The closed old six-document profile recorded classifier95.537s cumulative in a
105.037s instrumented coverage call versus authority reads1.672s. Cumulative
times overlap and profiler overhead exists; this is not a wholeFULL CPU share
or speed promise. It cannot justify an automatic legacy retry or fewer guards.
No family ledger/seal, actual held-row registration or production notes promotion
is supplied by these diagnostics. Keep all failures and original comparative lanes.
Honor the current root-only broad-gate lease and keep its pinned snapshot fixed.
