# Period/admission checks and retained bounded runtime failures

This follows owned F36 checkpoint aeb353f50e5e57650c0d3f9724839f2839cd66ca.
F39 and F36 remain unsealed, F37 unclaimed, F41 locked. The user permits F36
after the saved unsealed F39 checkpoint. Scope remains2025-current, including
printed comparatives. No providers, new extraction or original data changes.
All drafts below remain separate from the owned production branch.

## Actual notes tests, including the composed candidate

Claude's R1 branch57c862f08586ce6dfe3e2f222dabb1b8f283757c passed145/145;
admission branchc44a7579b9e8d4d9d64c8dda75132ea8aaefac03 passed147/147;
their exact reviewed union88f517c4986ccdcfaf447d3ba9e8d4452595a100 passed149/149.
Every run retained all143 old nodes, had zero failures/errors/skips, the exact
JUnit case denominator, correct immutable private source origins and equal
pre/post code/config/test pins. Unit runs used Python3.12 and were serialized
with one another under their reviewed limits.

| Candidate | Run under /home/bctc/notes-pytest | Wall | Peak KiB |
|---|---|---:|---:|
| R1 |20261024T012833Z|17.56s|93400|
| Admission |20261024T013410Z|14.84s|94516|
| Composed |20261024T014433Z|13.11s|94168|

Terminal SHAs respectively:
- 8c0046179a9e64651a19de66757276ebbdb5db2b64b2a2a33e379a5b34cc12a0;
- b6a9a2534789d0820add3d1f052519dfcb1c3b8db7501194519156dae28f3fc3;
- 456de8c084cf758ec3ec2d508e91e31163b1200311359c4fcb099dbf327510db.

Composed JUnit SHA244ea5247fc6f3fcfa1bf7f0b0d0ee30c8817d2245d8b6889da5abb48d84dc07;
pins-before/after SHA540170bd9a68668657ea4d652df53648c48c8fbdb8f83cc2d40e43ae49aba647.
Independent closed-output verification receipts under D:/bctc_bank/restore-receipts:
- NOTES_R1_57C862F0_ACTUAL_145_UNIT_VERIFICATION_20261024.json,
  SHA5eb999c3257605fa57a8c6420dda218c1b57e147c924faadcc5d31eefbf7567c;
- NOTES_ADMISSION_C44A7579_ACTUAL_147_UNIT_VERIFICATION_20261024.json,
  SHA0d94c4a557ab74ce7cf23bad479d621f8655933c829e329503109b996089ac7c;
- NOTES_COMPOSED_88F517C4_ACTUAL_149_UNIT_VERIFICATION_20261024.json,
  SHAa2a627e6ecc3469568e1e9ff81745eb818ed37c10d168bf6671af0f692bdc521.

R1 records only raw-header YEAR_ENDED shadow evidence. It does not change
period key/basis/candidates, clear HOLD or let an agreeing PRIMARY amount grant
a period. Admission separates own investment-position schedules from expense
flows, and related-party transaction/subset tables from gross deposits. A real
review defect in536b2e5 was corrected additively: an own-section narrative that
merely points to another note no longer grants related-party ownership. Only
own headings qualify. Mixed stock-MONEY plus flow-MONEY and gross-deposit
cross-reference controls pass. No financial family is closed by these tests.
Fresh composed FULL/COMMON runs and their old/new source-disposition comparison
remain separate gates; the earlier404 corpus results do not prove88 results.

## Three authenticated original tables and the incomplete ADMIN comparison

Raw reader completed exactly40p42/98p61/261p60, binding whole original BLOBs,
selection/manifest/frontier, held database/index/metadata SHA and identities,
SQLite quick/FK checks and no-sidecar barriers before/after. It performs no
classification, repair or PDF review. Receipt:
`/srv/bctc-receipts/f36-admin-original3-20261024T012900Z/F36_ADMIN_ORIGINAL_THREE_TABLE_EXTRACTION_V1.json`,
SHA8ea7d21a7a0de8de92038183002802565592427ad2b571017e2ee4498c405293.
CPU8.047758991s, wall8.098202580004s, peak26624KiB, errors[].

The ORIGINAL JSON for40 records the ADMIN-labelled parent atrow12 and contiguous
ITEM children13..17.
98 and261 are descendants of OTHER expense, not ADMIN;98 also has a hierarchy
gap atrow9. They must not be relabelled to obtain a positive result. These raw
facts alone establish neither mapped-parent/root replay nor PDF acceptance.

The separate six-original source-effect pair40/98/193/243/253/261 is FAIL at
pairwall360, not a passing A/B. Parent receipt:
`/srv/bctc-receipts/f36-owned-admin-original6-effect-v1-20261024T014000Z/F36_OWNED_ADMIN_ORIGINAL6_SOURCE_EFFECT_V1.json`,
SHA4d6b13bd2ff165ada0d811717f54cb20e38b8f67bd321611abeedb3cd56f5f5e,
72266bytes. Baseline completed PASS with23 coverage violations, CPU180.258481119s,
wall189.307652530988s and fresh source/admission closure; its receipt SHA is
7fbf5a219db454c1bdd1a5a329dd68c8da6209ec1322ee89874615a1505c8b86.
Candidate was terminated with exit-15 after the remaining165.82s and has no
terminal child receipt. Seven-axis comparison and coverage delta are therefore
NOT_PERFORMED. Keep all partials; no retry/cap increase or ADMIN promotion.

## Profile failure and a separate exact-predicate draft

The one-call baseline coverage profiler is terminal FAIL: its coverage operation
returned normally, then the body CPU210 guard failed. TotalCPU226.887371908s,
wall233.918241321s; profiled operationCPU103.488375043s. Witness closed, but the
overall successful-context flag remains false. No other error was recorded;
this is not acceptance or a conclusion of source corruption. Receipt:
`/srv/bctc-receipts/f36-baseline6-coverage-profile-v2-20261024T012400Z/baseline/F36_BASELINE_ORIGINAL6_COVERAGE_PROFILE_V2.json`,
SHA0e53d2f844f9b8eb2d26bc2a6512a1326d6acb9dd26f604026843eaaeaa88d2a,
818676bytes. Retained raw profile84207bytes,
SHAeef93d1b7c8e57eb473c38297d57503b758fbb4517c95d3578b027eff57da87f.
Do not repeat by increasing caps or treat instrumented timing as an A/B speedup.

The profile exposes repeated table classification and19,607,673 prepared-form
predicate calls. Draftf768cbbfd4ad3a376e29ae05d32e2f85e0e22348 changes exactly two
lines in the nonfrozen hierarchy matcher: returnFalse when the already-computed
suffix set is empty, before allocating constants/the nested helper. The old
predicate already returnedFalse in this case; all other matching/error/order
semantics are preserved. It introduces no cache, source or financial policy.

Actual38/38 focused PASS, zero failures/errors/skips, compile/Ruff/origins/full
2125-input pre/post pins and exact planned JUnit axis passed. Receipt:
`/srv/bctc-receipts/shared-hierarchy-empty-suffix-focused-v1-20261024/REVIEWED_CASE_MANIFEST_FOCUSED_V2.json`,
SHA73c3f90a57ed80f6a2837d0eca7a670548b1e05a6f432dbc7edfffd61007e7a7,
1507978bytes; case49941ea430f22db0c8da06bc61984f6f2466bb16e07e5965c9772a99c6171ed1.
Its separate original6 V7 comparison is terminal PASS for all eight exact typed
document/source/index/query/trial/coverage/observation axes, retaining22 raw
coverage violations. Receipt:
`/srv/bctc-receipts/shared-empty-suffix-original6-ab-v7-20261024T014900Z/F36_EMPTY_SUFFIX_ORIGINAL6_AB_V7.json`,
SHA22289cc0c010b50beddb5dbcbbf54d978eb168d08ff291674ad6da4609b2c820,
73313bytes. Both fresh source/PDF243/SQL/code/runtime/close barriers passed;
independent cold replay remains NOT_PERFORMED.

Observed baseline/candidate totalCPU146.908769242/123.664031946s,
wall153.092505381006/133.311743419006s and peak281132/275312KiB. This one six-
original warm panel shows a timing improvement; it does not establish a
whole-corpus speedup or financial release. Broader composed/cross-family
regressions still precede promotion. Unit tests alone do not establish speed.
The older d48 path-form draft remains unpromoted for lack of overall gain.

## Coordination and continuation

One immutable nonterminal HEARTBEAT was published with exact-Version readback,
185 to186 complete exact event refs and no competing F36 owner. Key:
`bctc-ai/coordination/2025-current/v1/events/20261024T012321931885Z-LAPTOP_INTEGRATOR-HEARTBEAT-90d1770324d24f64b8568f0dbe0271b7.json`,
VersionId d4w87Z0D_I_62e.h6LjUfyS3ncC8raym,
SHA3a45c4810f840d141b7de6044dc27a6fdf1c0f0c43c7e0004ad0b92f7c96a077,
68669bytes. Local final receipt SHA f5e2a646bff5c5424959bcbd6665fe52b033f8497aac8407f608a2bee466f24a.
It uploads no artifacts and labels its selected evidence LOCAL_ONLY. New unit,
source and failure receipts here are not a complete-project S3 backup.

The first publisher attempt failed locally before any AWS client/PUT because
Windows path.stat and fstat give different ctime meanings. V1 and its failure
are retained; reviewed V2 checks stability within each API and common identity
across them, and retains initial-read failures. The successful V2 made one
conditional AES256/checksum PUT with SDK total_max_attempts1; no unknown retry.

Next: broader matcher regressions, then fresh composed-notes corpus
checks and source-disposition review. An annual policy declaration fordoc69 has
not been inspected; do not infer a fiscal-year start or comparative window.
Reuse existing parsers only with actual owning printed RANGE/six-month evidence.
Check the current runtime lease before another source/test/evaluation job.
No family seal, canonical release or permission to openF41 is supplied here.
