# F36 full-axis profile and notes strategy checkpoint — 2026-10-23

This is a nonterminal checkpoint. F39 remains explicitly unsealed at
`11380ed935a84b64d72c4e7d367f0451ce0e62e0`; the user's additive workflow amendment
permits F36 work after that saved checkpoint. It does not waive remaining gates.
F37 remains unclaimed and F41 remains locked. Scope is reports from 2025 onward;
printed comparative lanes in those reports are retained as source observations.

## Production boundary

The scoped-payroll production checkpoint is unchanged: algorithm commit
`7d059e263e109caf4340842728954a0b8315113b`, with744 focused tests passing and
actual FULL193 source proof. See the scoped-payroll ledger. The main branch at
the start of this review was clean at
`e4fda20a4e442c5c34f638e23f18fe4b8df6645f` on
`codex/f36-operating-expense-laptop`.

No provider, original database/PDF mutation, source-value backsolve, blank-to-zero
conversion, magnitude-based unit assignment or frozen shared-file change occurred.
The isolated performance and PRIMARY-witness candidates remain unpromoted.

## Actual full-axis measurement: failed, with a useful partial profile

One untrimmed FULL271 measurement selected271documents/14,945page JSON IDs and
ran against the private tested payroll checkout
`90a2b45f05768c212b5c01d14fa8a305e339b168`.
Helper SHA `b7079b718bc232c9374c5679df093dbdaa7f53ac460640c4e79ad7d342a2a0ac`.
Session77959 is terminal exit1. Its receipt is:

`/srv/bctc-receipts/f36-full271-query-phases-20261023T152000Z/F36_FULL271_QUERY_HYDRATION_INDEXED_PHASE_MEASUREMENT_V1.json`

SHA `41a9250b70fbfecb16b5969bd487d6ee14e060cc0fd1e479de87519134275f63`,
1,272,135B, status `FAIL_NOT_MEASURED`.

The CPU600soft limit interrupted `public_query_profiled` after586.796CPU seconds.
Hydration, original-versus-hydrated verification and F36 indexed-builder phases
were not reached. Snapshot entry had passed in8.568wall seconds and SQLite
integrity in1.159wall seconds. Peak RSS was229,164KiB, with no MemoryError.

The partial instrumented profile records93,712,819 `_matches` calls and
107,666,908 `_without_leading_ordinal` calls. Shared classifier/alias-role matching
dominates the observed query work. Inclusive profile timings overlap; they cannot
be summed or extrapolated into an unprofiled FULL271 runtime or speedup claim.
Only100 coalescence calls were entered; this is not100 proven completed documents.

CPU-limit interruptions also prevented normal snapshot-exit/final verification.
The initialized false authority flags therefore mean unproven closure, not an
identified corrupted file. Retain the failed receipt without relabeling it PASS.

A separate bounded post-abort hash barrier then passed for the current database,
index and all542document references, with no sidecars:

`/srv/bctc-receipts/F36_POST_ABORT_FULL271_AUTHORITY_HASH_BARRIER_20261023T154000Z.json`

SHA `dd59da7d1a8acebb990a6e24ba9946199751e88ef3bf61cf6b6d938c159be433`,807B.
This proves current pinned bytes; it does not retroactively complete the failed
measurement. There was no automatic retry or cap increase.

## Source-visible PRIMARY witness preparation remains inactive

The exact original FULL243/p6 row metadata was authenticated separately; receipt
SHA `508b5bb1c3058881f1395a97d7fc63926c29c5eefb750709bb6e89bef1b7543a`.
The original page/section/table/row one-LF hashes remain distinct from the stored
two-LF BLOB hash. Original JSON was not edited.

Actual manual crop review is recorded outside the repository:

`D:/bctc_bank/restore-receipts/F36_VAB243_PRIMARY_THREE_CROP_MANUAL_APPROVAL_20261023_V1.json`

SHA `576591c64d1df59fe6d1c93eec29a1f558fad3c106f6357c3c02f6bceb9fb93c`.
It approves three declarations only, with exact source, coordinate, before-image,
full-render and crop-pixel bindings. It grants no production/unit/mapping authority.

The declare-only builder ran once, exit0, against the independently tested5096
primitive. Build receipt:

`/srv/bctc-receipts/f36-vab243-inactive-spec-20261023T153600Z/F36_VAB243_INACTIVE_PRIMARY_WITNESS_BUILD_V1.json`

SHA `6cf7b595d90b103b6e3f6bd1b9f13f9e58bac4f6b3cd54ed5b212f46ef5377e2`,422,610B.
Inactive spec SHA
`e4f350b5de4caef7516a9f62cc109b54eaf161b6ad8c833425ab70c00de0dc4a`,6,319B.
All three declarations validate; input closure passed. This execution accessed
neither PDF/PNG nor database, and performed no projection or registry activation.
Public admission integration remains private and unpromoted. Its reviewed optional
API uses an operation-bound live capability created only after fresh PDF/render/
crop verification. JSON metadata, approval booleans and self-sealed receipts are
not admission. Trials, coverage and cold replay recompute from original pages;
default-None retains the earlier route. No actual243 registry was activated.

Private candidate `72914747d14d7950b7b27b8d53342e500ddeb858` passed the coherent
15-module832-case gate (744existing +62primitive +26public protocol), zero
failures/errors/skips, Ruff, actual imports and final source/Git barriers:

`/srv/bctc-receipts/f36-primary-witness-full-focused-20261023T160800Z/F36_PRIMARY_WITNESS_FULL_FOCUSED_V4.json`

SHA `4fd03ddae336614bee42f172bcb4448d5f17cea23846f8a4cb618308d62a3cf2`,
2,069,801B. The candidate's public protocol uses actual synthetic PDF pixels and
SQLite ingestion/replay; it does not use corpus PDF pixels or financial mocks.
The earlier V2 Ruff failure and V3 21-failure run remain intact: V3's21failures
all stopped at a schema-invalid synthetic anonymous row path before admission.
A test-only explicit legal path fix preserved its blank label and values, then
26/26public cases passed separately before the full832rerun. No validator or
acceptance assertion was weakened. Full real-source243 comparison is still a
separate required gate, not implied by these synthetic tests.

## Strategy and next acceptance evidence

The measured query hotspot has no existing F36-local prepared-alias API.
Pruning aliases/rows, monkeypatching shared helpers or changing the frozen pair
would not be a justified exact-output optimization. Keep the current production
route while comparing Claude's separate six-family notes kernel against original
source identity and financial semantics. Configurable shared shapes can reduce
repeated work across families only after actual evidence establishes correctness.

Claude's new PRIMARY branch `07eb7a508d75240b562f6560863307bb849c54c6` has an
actual FULL271 run, store reload and independent fresh-process271-result-ID
rebuild. Terminal SHA
`78409cafd6ec695800748aba316002b82aae4f5a1897fcb891c51f07ead86591`.
This is execution/provenance evidence, not blanket financial acceptance of all
cells or an integration of the branch into this checkout.

The notes source bridge at `220ea3ce9df109ecc2eb5f86b38fbbc4fa460525` passed111
unit tests, terminal SHA
`ea8a544e0ea17d3f78641fb3171f25ee9e1d8561a08c3741160eb67d21674f57`.
The source-bridge FULL271 six-family pilot completed once, without retry,
under immutable exchange grant0120, START0121 and terminal release0124.
Root independently read the actual terminal, closure, manifest, identity and
source-barrier files under `/home/bctc/notes-runs/full271-20261023T153912Z/`.
Terminal SHA
`8fc0392b26de929fa0602313308d55c3be235af4aab4b8d5456783ccd210b85a` records
`PASS_DIAGNOSTIC`, both stage exits0, unchanged code, matching helper bytes and
passing before/after source barriers. Exact PRIMARY identity covers271documents
once each, with zero corpus/document mismatches. Its receipt SHA is
`2bfccec15bb53360f1a93dcbf200d2566e900898a8bf6a31770b95fe159dce03`.

Manifest SHA
`c3d00f9841af14f918160205fb4fcdb524f249ec58a5deb7454829d5b98748aa` records
31,080cells, exact store reload and an independent fresh-process rebuild of
the same complete cell projection, SHA
`48e3d6dd83701fd72198af598d9b6938eb0c210098e2e0fe69994a111ca88a84`.
It produced271experimental workbooks. Run-stage wall4:44.75, peak RSS629,548KiB,
under1.5GiB AS per process, with277.787seconds recorded inside run_v1.
It made190SQLqueries and9,950cumulative ORIGINAL-page loads across six families.
This proves a useful batched execution path; it is not an equivalent-work
speedup comparison against the old F36 closure runner.

Static review identifies financial admission gaps in that prototype:
contradictory header/table units; unconditional payroll aliases without the F36
owner guard; and tax base-versus-effect/population ambiguity before legacy5730
export. Equal-valued write-key collisions also choose a source by table order
without independent duplicate-meaning proof; F37 parent fallback requires an
explicit ownership review. These are concrete code paths, not claims that this
pilot has falsely accepted a particular source. Review original coordinates and add adversarial
regressions before any production promotion. Preserve HOLD and every retrieved-row
disposition; accepted-cell counts alone cannot establish accuracy or completeness.

The finite prototype guards were subsequently implemented on Claude's separate
notes branch, ending at `1fc78cba51e68656117e8ba0dff5171c064eb252`.
Header-versus-table and conflicting table-owned units now veto a lane; owner/scoped
children require a coherent final unambiguous parent; equal-valued collisions stay
HOLD; ambiguous tax observations have no5729/5730legacy ID and expose their
semantic state in workbookV2. A later regression preserves fully qualified direct
F37 labels without an invented parent dependency. The known valid FULL193 NULL
wrapper shape remains an explicit conservative coverage gap in this prototype.

Its actual seven-module118-case run passed with zero failures/errors/skips:
`/home/bctc/notes-pytest/20261023T161232Z/terminal.json`, SHA
`0d2f46f523dba6ed1e97194e7b2e77d73661e96ee7855765a632815d110fecb0`.
Root verified matching before/after pins
`d6b11b0809caafd94c05e20c89efdbf2704599e1d3b4faa291249c323ca1ed53`.
This is unit evidence only. A guarded FULL271 rerun is separately granted by
exchange0137; verify its actual terminal release before another runtime job or
claiming a new corpus result. Source-coordinate comparison remains a distinct
unrun step. None of this prototype code is integrated into this checkout.

F36 still requires fresh coherent full271/common204, public and cold source replay,
observation checks, final SQLite persistence/integrity, PDF/residual audit and a
terminal ledger. Preserve all prior artifacts and failures.

Pre-mutation coordination reviewed182exact event versions, with no new F36 owner
conflict. Receipt SHA
`38c0de929c888cf219a7a6c84f01d8bb5693850b9255badf07a4cb29f8720999`.
The later coordination review again found182exact versions/no conflicting owner;
receipt SHA `b95bac538223dc56cbb6389085d9feebf339a11de114c8c2cb1ac8ad9fe6c9bd`.
