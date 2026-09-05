# Codex continuation instructions

Before changing this repository after a machine migration, read
`docs/operations/MACHINE_MIGRATION_CHECKPOINT_2026-09-05.md` in full and verify
the Git commit and restored S3 manifests named there.

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
