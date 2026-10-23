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
