# Codex continuation instructions

Before changing this repository after a machine migration, read
`docs/operations/MACHINE_MIGRATION_CHECKPOINT_2026-09-05.md` in full and verify
the Git commit and restored S3 manifests named there.

For laptop continuation, also read
`docs/operations/F39_PERIOD_BATCH_UNSEALED_CHECKPOINT_AND_F36_HANDOFF_2026-10-23.md`.
The user's 2026-10-23 amendment permits moving to F36 after saving/pushing an
explicitly unsealed F39 checkpoint. It does not close F39 or waive any financial,
source, replay, integrity or ledger gate. F41 remains prohibited until the three
unfinished families are terminal. Honor the assigned task-owned branch; do not
push directly to the integration branch without the required review.

The reviewed F36 integration checkpoint and its active diagnostic job are recorded
in `docs/operations/F36_REVIEWED_WORKER_INTEGRATION_CHECKPOINT_2026-10-23.md`.
That checkpoint is not a family seal; check the job's terminal receipt before
starting another runtime job or changing its pinned runtime checkout.

The original diagnostic pair is now terminal. The reviewed printed-root recovery
and687-test/source-backed checkpoint is recorded in
`docs/operations/F36_PRINTED_ROOT_SOURCE_PROVEN_CHECKPOINT_2026-10-23.md`.
F36 remains unsealed; distinguish its promoted algorithm from isolated
title/payroll/performance drafts and the older full/common baseline.

The finite continuation-title improvement is now promoted separately; read
`docs/operations/F36_OWNED_CONTINUATION_TITLE_CHECKPOINT_2026-10-23.md` for its
721-test gate and actual FULL149 source proof. Payroll/performance and numeric
PRIMARY-witness repair remain isolated drafts. Neither checkpoint seals F36.

One bounded scheduling exception was agreed in exchange messages 0066/0067:
root may inventory the exact completed FULL271 diagnostic JSON while COMMON204
runs, using a reviewed read-only streaming reader capped at 384 MiB address
space and 60 CPU seconds, nice 19, with immediate memory-headroom checks and
held-FD SHA/identity barriers. It grants no source-DB/PDF/test/profiler/provider
access, peer execution, acceptance waiver or automatic retry. Other runtime jobs
still require the explicit lease; never change the live pinned checkout.

Messages 0072/0073 agree a second root-only bounded reader: at most 16 selected
original page-JSON IDs for the named F36 cases, stdlib only, no evaluation or
PDF. Exact original index/database FD hashes, identities and no-sidecar checks
are required before/after. Cap 192 MiB AS and 45/50 CPU seconds, nice 19,
MemAvailable at least 1.5 GiB and active swap at least 4 GiB before/every page;
fresh exclusive output, no retry/cap increase. Independently review the exact
helper first. This grants no peer/test/profiler/provider execution or acceptance.

The authoritative worktree is this repository on branch
`codex/27-bank-2025-current`. Preserve all committed family code, tests,
registered evidence, and staging ledgers. Do not restart provider calls or
create a new family until the unfinished Family 36, Family 37, and Family 39
checkpoints have been closed according to the migration document.

The shared multitable evaluator and generic runner are frozen at the SHA-256
pins recorded in the migration document. Treat them as read-only unless a new,
explicitly reviewed shared change is required. Keep all recovery logic
family-local, source-visible, fail-closed, and receipt-authenticated. Never turn
a blank cell into numeric zero, infer a unit from magnitude, or backsolve a
source value from an equation.

The active extraction architecture is PDF -> Gemini JSON -> authenticated
validation/evaluation -> SQLite/database. PPOCR6, VietOCR, geometry-based OCR,
DeepSeek OCR, Gemma, PaddleOCR, and their model/cache artifacts are obsolete and
must not be restored, uploaded, or reintroduced into the production path.

Do not restore or commit credentials. Authenticate again on the new machine.
Large corpus, audit, and Codex-session material belongs in the private,
versioned S3 migration prefix recorded in the migration document.
