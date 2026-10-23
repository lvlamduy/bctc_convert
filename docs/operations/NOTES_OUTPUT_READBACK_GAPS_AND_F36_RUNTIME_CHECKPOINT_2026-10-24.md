# Notes output verification gaps and F36 runtime checkpoint

F36 remains unsealed; F39 saved/unsealed, F37 unclaimed, F41 locked.
The user's amendment permits F36 after the unsealed F39 checkpoint. Scope is
2025-current with printed comparatives retained. No provider was called.
This documentation follows da0890d7c074bc145a619323844df4371923db7d.

## Current runtime owner

One root-owned legacy F36 FULL271 producer remains live in tool session25267,
started2026-10-23T22:15:42UTC. Actual process metadata at23:29UTC confirmed
wrapper366733/producer366756 and producer CPU70minutes. No terminal outcome
exists yet. Output directory:
`/srv/bctc-receipts/f36-full271-existing-producer-v3-20261023T221542Z/`.
Poll the actual session/process and inspect `execution-result.json` before
another project DB/PDF/test/evaluation job. Never restart from an observation
timeout or from this document's age. The pinned feaee5ae runtime is unchanged.

The before/after file hash/reference/no-sidecar checks do not establish fresh
SQL integrity. Static review confirmed that the producer's snapshot helper does
not run PRAGMA quick_check/integrity_check/foreign_key_check. Separate fresh
read-only SQL checks are still required for full/common source and final stores;
earlier wording about producer-owned integrity must not be read as that proof.

## Concrete prototype output-checking gaps

Root and an independent reviewer read exact notes510be514e81de114156de6502ca37fff5ea2bc5d
Git blobs of export_v1.py/store_v1.py and their tests. No source evaluation or
financial acceptance change was made. No generated-source corruption was shown.

The workbook verifier compares only DIMENSIONAL columns2,4,6,8,11,13,17,18.
It misses observation_state/raw and other basis/identity fields. TM data fields
are checked but period headers and complete sheet/README identity axes are not.
The SQLite reload compares only value_text/acceptance/period_key/member to
cell_json; other normalized columns can differ undetected. The generator and
exporter currently retain correct canonical cells, so these are exact-readback
coverage gaps. Existing PASS_EXACT_READBACK must not be presented as proof of
every workbook/normalized SQL field.

Claude is implementing a separate finite verifier/tamper-test fix on the owned
notes next branch, per exchange0222/0223. Root's private510 clone, old helpers,
receipts and the live legacy F36 runtime must remain unchanged. No financial
role/period/unit/blank acceptance policy is authorized by the verifier fix.

## Finite next execution batch

The private510141-unit launcher and notes FULL271V9/COMMON204V2 launchers were
reviewed but remain unrun. If the concrete verifier fix is ready before runtime
release, test the stronger fixed private snapshot once, including all old141
nodes plus the added tamper controls, then measure its fresh notes full/common
outputs. Preserve the unrun older preparations; do not call them failed tests
or measured coverage. Do not execute tests from a moving peer worktree.

The source inspection V2 is separately reviewed for13locators/12VID/10docs:
helper39c54b1ea1455b1daba4c95fe2f04a0540352a7ae5fe3f23f5e50d5c613f0a84,
launcherb1becee30b88ed6d5d684b96c218666c495cd14a39d1776b3cdfeda8e5a78522.
It uses private510, original source loader and late whole DB/PRIMARY hashes;
its stability proof is NOT_HELD_FD and it grants no column crosswalk or period.
It remains unrun and requires release of the current runtime owner.

The completed-FULL inventory V2 is reviewed but unrun:
`D:/bctc_bank/restore-tools/drafts/read_completed_f36_full_diagnostic_inventory_v2.py`,
SHA38353c9cceca31e74fbd2cccea5d5bbb2787df071dc10905458c2f3a31b4d5d2.
It needs actual terminal/diagnostic hashes, binds the successful terminal and
both source receipts, streams271trials under384MiB/55-60CPU limits and groups
distinct unresolved documents. It opens no database/PDF and grants no acceptance.

The six prototype plugins declare99possible Excel RNIDs, not achieved coverage.
After actual runs, count accepted numeric cells with RNIDs separately from proved
dashes, blanks, semantic-unproven observations, HOLD and NOT_EVALUATED. FOUND
tables or nonnull RNIDs alone do not establish accepted Excel coverage. The
older notes full/common stores prove their older code only.

Before this Git documentation mutation, AWS identity/versioning and185exact event
versions passed without a competing F36 owner or S3 writes. Receipt:
`D:/bctc_bank/restore-receipts/f36-pre-promotion-coordination-20261023T233101448636Z-c841cfb366624fd8826cf20fbf11ee73/F36_PRE_PROMOTION_COORDINATION_REVIEW_V1.json`,
SHA6ba79c9093a6fb278ae97282e647dbfb5ab0436998c8db07752a7babf5806ed1.

Fresh COMMON204, applicable full/common PDF/row declarations, official result
stores, cold replay, independent SQL/projection checks and terminal ledger remain
required. Do not relabel algorithmic uncertainty as a genuine source finding or
infer missing amounts merely to close a family.
