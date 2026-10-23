# F36 reviewed worker integration checkpoint

Status: **DEVELOPMENT CHECKPOINT — F36 NOT TERMINAL**.

The user directly authorized moving to F36 after saving the explicitly unsealed
F39 checkpoint. F39 remains unsealed at `11380ed935a84b64d72c4e7d367f0451ce0e62e0`.
See `F39_PERIOD_BATCH_UNSEALED_CHECKPOINT_AND_F36_HANDOFF_2026-10-23.md` for that
amendment and the retained F39 failures/missing gates. F37 has not been claimed
by this checkpoint. F41 remains prohibited until the unfinished three families
are terminal with the required backup.

Scope remains banks, reports from 2025 to current. Standalone 2024 reports are
outside production/provider queues; printed comparative columns are source
evidence. No provider or obsolete OCR was used.

## Git and coordination

Owned branch: `codex/f36-operating-expense-laptop`.
Reviewed code commit: `f3d251ed9924697b523ed06f59a0d18810b16e80`, pushed and exact
`git ls-remote` verified. It descends from the unsealed F39 checkpoint and
migration base `8efd618b6c77f0cdbb402a440e7ba3b3549184f1`. No integration-branch
push or history rewrite was performed. This document is a documentation-only
descendant; the running diagnostic remains pinned to the reviewed code commit.

After independent review and a fresh worker regression, seven coherent semantic
commits were cherry-picked with provenance: `bf7dac4`, `9c84629`, `61fe0f1`,
`a715e84`, `5f6cc82`, `c6f3cdb`, `9a01a39`. The unrelated coordination/bootstrap
commits and superseded fixture patch were excluded. Changes cover F36 evaluator,
active topology/evaluation/repair configs, runner/builders, fixtures and tests.
F39/F37 production code and the frozen shared pair were not changed.

The separate `fc9b6218c0c23e6053a2c199c69ca5234d712af8` optimization was then
independently reviewed and probed before promotion. It partitions the already
validated selected-page axis by document before owner-rejection checks. The old
helper already performed that same document filter; outputs and tamper rejection
were checked equivalent. It reduces repeated global membership scans; no corpus
speedup is claimed from static complexity or incomparable test timings.

F36 claim event: `20261023T081950687521Z-LAPTOP_INTEGRATOR-CLAIMED-05b68d71209d49d4a695fda835cd851e.json`,
under `bctc-ai/coordination/2025-current/v1/events/` in `test-s3-duylv`.
VersionId `PHiDeofQMtZ.WM1xDp7ud0oXGupHmIkA`, SHA-256
`5646a7330ea90bf77350ae51addfff9db37ac6769a4a77c161a71890c5fb14e7`.
The historical inactive VPS reservation was not presented as a fabricated release;
the direct sole-laptop and F39-to-F36 user amendments provide execution authority.

## Focused gates and immutable evidence

| Gate | Result | Receipt SHA-256 |
| --- | --- | --- |
| Independent exact worker tip `9a01a39`, five F36 modules | PASS 504 tests, zero failures/errors/skips | `8a1e173b20bf3e499f16ecea41337151e1f1a5f09eb85b2eb0ba3e9b9e6264d1` |
| Separate exact perf worker tip `fc9b6218`, optimized/global output and tamper probe | PASS one test; not full regression | `51f37571853e4b5f81d0a4a1a775b0177108452f961b47e9ee5559d1119985c1` |
| Integrated `f3d251e`, eleven modules | PASS 666 tests, zero failures/errors/skips, 149.53 seconds | `6c091f762299f21d9ea9efcb3d2c806d73e94f809106b2fc93e4b9f38245cd70` |
| Nine active Python paths compiled in memory; Ruff; diff whitespace | PASS | compile evidence in integrated receipt |

The eleven modules comprise five F36 modules, the five migration-mandated shared
regression suites and the frozen generic-runner suite. Actual import/callable
origins, whole tracked source/config/test/fixture hashes, clean Git identity and
frozen hashes were stable. Python 3.12, fresh bytecode/scratch paths, no pytest
cache. These are overlapping runs: do not sum 504 + 1 + 666 as unique coverage.

Local integrated receipt:
`/srv/bctc-receipts/f36-integrated-focused-20261023T085900Z/F36_INTEGRATED_FOCUSED_REVIEW_V1.json`.
It is 1,861,385 bytes. S3 artifact prefix:
`bctc-ai/coordination/2025-current/v1/artifacts/LAPTOP_INTEGRATOR/f36-reviewed-checkpoint-20261023T091438764591Z-cc4917f6c4f349a4a148bd1dc463d8d2/`.
The integrated receipt is under `integrated/`, VersionId
`G4BgbgYBVN442fLntoJGWF94aBsHcu3L`. The worker/perf receipts and two static
reviews are preserved under their separate label directories in that prefix.

Nonterminal heartbeat in the events prefix:
`20261023T091438764591Z-LAPTOP_INTEGRATOR-HEARTBEAT-49ee8a4715c141788712d295060e2c7c.json`,
VersionId `SYyGVzcfQz6WesD3KixbE07Tk_pel96z`, SHA-256
`6ee4137540ff3fc24e8475c434d7af4e7fbcd9fbdf8c92ec4d859fae8318e2d1`.
Five artifacts and this heartbeat passed exact-VersionId byte readback after
conditional encrypted writes. No existing S3 object was overwritten/deleted.
Local publication directory:
`D:/bctc_bank/restore-receipts/f36-reviewed-checkpoint-20261023T091438764591Z-cc4917f6c4f349a4a148bd1dc463d8d2/`.
Its `final.json` SHA-256 is
`b3fc338b6198a9ff07bc2cb21ee05e4cbc5e8394b6a637d35c3984794183eab4`.

## Active runtime and remaining gates

As of 2026-10-23 09:16 UTC, ONE diagnostic invocation is active at
`/srv/bctc-receipts/f36-full-common-diagnostics-20261023T090700Z`.
Wrapper PID 3418; FULL271 first-stage time/group PID 3439, producer PID 3440.
Check actual process/receipt state when continuing; this is a dated observation.
Resume the same job; do not start another because a process list is temporarily
empty. The wrapper's terminal record is `execution-result.json`; each completed
stage writes `outcome.json`. COMMON204 follows FULL271 independently and serially.

Runtime source is a clean exact Git clone at
`/srv/bctc-receipts/f36-runtime-checkout-f3d251e-20261023T085800Z/repo`.
Both frozen files are read-only there. Source databases stay immutable; private
snapshot/outputs are on ext4. Before launch the existing 4-GiB swap file was
metadata-verified and activated, restoring 5 GiB total swap capacity. Its contents
were never read, hashed, copied or uploaded. No environment changes or companion
data-analysis/test/profiling jobs while this invocation lives.

This diagnostic uses the existing Gemini database and authenticates registered
PDF repairs. It retains coverage violations explicitly. Exit zero alone is not
financial acceptance: inspect coverage gates/violations and exact replay results.
It does not perform manual PDF residual/visible-row review or final results-store
acceptance. Fresh authoritative FULL271/COMMON204, projection/observation/source
replay, SQLite integrity, actual PDF/residual review and a truthful terminal
ledger remain pending. Never turn generated audit prose into actual visual review
or label algorithm gaps/proven absence as genuine source ambiguity to pass a gate.

The frozen shared SHA-256 pins remain:

- evaluator: `bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2`;
- generic runner: `d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5`.

Blank is not numeric zero; unit is not inferred from magnitude; source values
are not backsolved. All remaining fixes must preserve original source coordinates,
owner/period/unit/basis evidence and deterministic authenticated replay.

## Completed FULL stage and narrowly bounded result inventory

The FULL271 diagnostic finished at 2026-10-23 10:10:32 UTC: 250 READY,
0 NOT_OBSERVED, 21 UNRESOLVED and 2,975 mappings. These remain proposals:
source-row coverage **FAILS with 307 violations**. Independent source replay and
registered PDF-repair authentication passed; manual/residual/final-store gates
remain not performed. The migration's anticipated 269/2 counts are not proved.
`full271/diagnostic.json` is 81,278,595 bytes, SHA-256
`2fecaf5f4876b1f8592c1430f8620f1821a3b3d30b4bb48f4c4658441ca1e2d9`.
Its stage `outcome.json` SHA-256 is
`3b708d32d0a334aeb6c7a7fb9b5db3f5f642896e56f00792ef5aac31cc1e6f88`.
Wall time was 1:04:29, maximum RSS 1,953,268 KiB, zero swaps, exit zero.
COMMON204 then started under time/group PID 7609 and the original wrapper 3418;
the pair is still not a completed/accepted family.

Messages `0066-codex-to-claude-full271-result-and-bounded-analysis-proposal.md`
and `0067-claude-to-codex-ack-bounded-root-reader.md` explicitly amend only the
earlier blanket scheduling rule for one root-owned, finished-output inventory.
The reader must be reviewed, read-only, streaming, Python 3.12, capped at
384 MiB address space/60 CPU seconds, nice 19, with sufficient actual available
memory checked before launch and between records. Hold the original file FD and
verify its identity/size/SHA before and after. Output only fresh exclusive
inventory evidence; no project imports, original database/PDF, tests, profiler
or providers. No automatic retry/cap increase. This is not permission for peer
jobs or retroactive approval of previously unleased analysis. Live code/source
remain immutable, and no financial or source gate is waived.

A separate inactive performance candidate is prepared locally at
`/srv/bctc-receipts/f36-performance-candidate-20261023T100700Z/repo`, commit
`5806cea2c227dd4d86a0d9b4ff00d4d0233481b2`, parent `6f158cc7aef4675a3cbe6b34b1e09815e6bd1c81`.
It contains reviewed coverage-copy/export-byte changes plus proposed regressions.
It is not promoted or pushed and has not been compiled, linted or tested.
It does not fix the 307 coverage findings; exact baseline coverage comparison
and focused regression are required before promotion. The active runtime remains
the original `f3d251e` clone.

The bounded reader then completed once with status
`PASS_COMPLETED_DIAGNOSTIC_METADATA_INVENTORY_NOT_FINANCIAL_ACCEPTANCE`.
It used 4.231328 CPU seconds, about 4.65 seconds wall and maximum RSS
103,136 KiB, nice 19; all held-file identity/SHA barriers passed. Its output is
`/srv/bctc-receipts/f36-full-inventory-20261023T102800Z/F36_COMPLETED_FULL_METADATA_INVENTORY_V1.json`,
371,220 bytes, SHA-256
`729714cba133d1c2d3351d653f4e1507fc409d00e1d37fd741b2b65193f9883c`.
No source database, PDF, project import, test or provider was accessed by it.

The 307 violations comprise 176 unmapped selected-schema-role rows, 113
unclassified visible rows, 14 unmapped terminal totals and four selected-root
rows. There are 219 violations on the 21 unresolved documents and 88 on 30
READY documents. READY therefore does not establish complete source coverage.
Nineteen unresolved candidates were rejected because their required printed
root was only derived; ten also retain an open-continuation reason. A late
veto versus earlier retry scheduling gap is under static review, but the retry's
admitted reasons also differ. Metadata alone proves neither a usable printed
total/frontier nor a safe fix. Original source probes and meaningful regressions
remain required; no source guard or coverage obligation is waived.

## Bounded original-table evidence and isolated accuracy draft

Exchange0072/0073 and DECISIONS13 permit one additional root-only original raw
table reader while COMMON runs. Its independently reviewed helper SHA-256 is
`86bc871986094ee52e57304bbf6ffaa16b872ae19a0e77a75bf653b25ff0b55a`.
The actual reader completed EXIT0: 12 original selected pages, 14 tables and
10 exact source documents. Index/manifest/selection/VID/raw two-LF BLOB hashes,
held-file identities, code/helper and source SQLite before/after barriers,
quick_check and foreign_key_check passed. No evaluator, PDF, repair replay or
provider was run. CPU through final barriers was 10.204974 seconds; external
wall11.47 seconds, peak RSS27,272KiB, zero swaps. The agreed192MiB AS,
45/50 CPU seconds, nice19, MemAvailable1.5GiB and active-swap4GiB guards held.

Receipt:
`/srv/bctc-receipts/f36-bounded-original-tables-20261023T105500Z/F36_BOUNDED_ORIGINAL_TABLE_EXTRACTION_V1.json`,
75,672 bytes, SHA-256
`72d1504c013262c2b1b39491b865cb4aaf61e5e4232c37e7616a5fd2b3e6fece`.
This proves raw extraction only, not semantic or financial approval. An earlier
shell prelaunch failed before time/Python started because the Windows/WSL shell
consumed a variable; the first actual reader used direct `wsl --exec` arguments.
No data-reader retry or raised resource cap occurred.

Concrete source findings now guide the next bounded probes:

- FULL57 has a terminal printed Cộng and local unit. FULL237 has terminal Tổng
  and local unit. The new printed-root route is not yet tested on either.
- FULL149's receiver SECTION explicitly says `28. Chi phí hoạt động (tiếp theo)`;
  the current complete-owner continuation gate accepts only a generic report
  heading there. This is a definite gate mismatch, not proof all later gates pass.
- FULL92/98 have `Chi phí quản lý chung` as an actual child of
  `Chi phí hoạt động khác`, so a literal root alias alone is insufficient.
  FULL98 also retains a malformed raw hierarchy segment; never silently repair it.
- FULL193's exact payroll-contribution wording is source-owned by EMPLOYEE.
  Its publication/advertising row belongs to OTHER, so do not map it as ADMIN.
- FULL243/253 both have Kỳ này/Kỳ trước and no local unit. Do not infer unit
  or invent a new period grammar; actual document-context/unit receipts are needed.
  FULL157's selected table has no terminal TOTAL; do not manufacture one.

An isolated accuracy draft is clean at
`/srv/bctc-receipts/f36-printed-root-candidate-20261023T105700Z/repo`, HEAD
`6f0c39e3dfffa03670ea9093267b5c485a28c011`, descendant of this checkpoint's
prior6698b26. It contains the early printed-root proof route and20 proposed
regression cases. It is not tested, promoted or pushed; the performance5806
candidate remains separate. Initial local commit80ead6df was followed by a
test-file mode correction; frozen content remains unchanged/read-only with
its original tracked execute bit preserved. The active diagnostic still uses
exactf3d. No new code is covered by the earlier666-test PASS.
