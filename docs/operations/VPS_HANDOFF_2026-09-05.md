# VPS handoff — 2026-09-05

This is the restart authority for the 2025-through-current Gemini-JSON plus
SQLite mapping project. It was written before VPS deletion. Read this file
first on the next machine, then read `MACHINE_MIGRATION_CHECKPOINT_2026-09-05.md`
and the linked handoff artifacts in this directory.

## Scope and non-negotiable policy

- Production scope is 2025 through current only. Do not add 2024 to the
  production queue.
- There are 55 conceptual/display families and 54 operational source
  evaluators; net interest income is derived and is not an evaluator.
- Use existing Gemini JSON and the authenticated SQLite stores. Do not call a
  provider for the work described here. Do not reintroduce PPOCR/PaddleOCR,
  VietOCR, geometry, DeepSeek OCR or Gemma.
- Map clear source rows with owner, hierarchy, sibling, neighbor, period,
  unit and continuation evidence. Preserve typed `U`/source-only for ambiguity.
- Never repair duplicate source references generically at seal time. Normalize
  only at a proven producer origin; let the shared contract reject survivors.

## Restore order

1. Clone `https://github.com/lvlamduy/bctc_convert.git`, run `git fetch --all --prune`,
   then `git switch codex/vps-handoff-20260905`.
2. Verify `git status --porcelain` is empty and read this file plus the four
   files in `docs/operations/handoff-artifacts/`.
3. Restore the immutable corpus/database only from the migration checkpoint:
   `s3://test-s3-duylv/bctc-ai/machine-migrations/20260905T014806Z-family40-checkpoint/`.
   Follow the exact VersionId/SHA checks in `MACHINE_MIGRATION_CHECKPOINT_2026-09-05.md`.
4. Do not use any local `/dev/shm` or `/tmp` path as authority. Those paths
   were transient VPS workspaces; every necessary source change is on Git and
   relevant bounded run evidence is in the S3 prefixes below.
5. Keep `codex-session.passphrase` outside Git, S3 and shell history. It is
   not required for ordinary Git restore; it is only needed if the encrypted
   migration archive must be decrypted.

## Git branches preserved

| Branch | Commit | State |
|---|---|---|
| `codex/f36-operating-expense-vps` | `9a01a391dc097283ba436ef01e76ce56d42f4a5b` | Provenance-dedup correction committed; F36 terminal HOLD pending governed full replay. |
| `codex/f36-owner-axis-partition-speed` | `fc9b6218c0c23e6053a2c199c69ca5234d712af8` | Reviewed speed patch; actual 14,945-page microbenchmark 29.065x, not an end-to-end claim. |
| `codex/f37-credit-risk-provision-vps` | `6feb29895c0bee541286b9059d63ebf488b07c60` | Two independent bounded reviews PASS; F37 terminal HOLD pending full corpus/final store. |
| `codex/f30-service-leaves-vps` | `6a620717e18dbf366d10ae7771be523a8fadb4fe` | WIP/HOLD, not merge-ready: exact leaves add +44 mappings but expose 47 duplicate refs until shared fix is reviewed and rebased. |
| `codex/shared-source-ref-unique-vps` | `b6cfdc53a21b36bf03503d02e67f30e810152261` | WIP/HOLD, tests and bounded replay green but **independent review is still required**. |
| `codex/f18-row-level-strict-subset-vps` | `d063e8ffe6fe45b572ac4947f5342cb503c98728` | WIP prototype only; do not merge or claim test status before a fresh review. |
| `codex/cross-family-audit-vps` | `3f4aa28f4b617a7adc2f6edb279a0b9c17309ccf` | Cross-family and shared provenance audits. |
| `codex/vps-handoff-20260905` | this commit | Current restart map. |

## Current measured results and blockers

- F30 `SERVICE_ACTIVITY`: full271 is `202 READY / 68 NOT_OBSERVED / 1 U`,
  mappings `2,150 -> 2,194` (+44 across 44 READY documents); 226 control
  documents are semantically unchanged and NAB92 remains U. It must rebase the
  shared provenance repair and rerun before a release because 47 new mapping
  source-ref duplicates were detected.
- Shared provenance Stage 1 changes only F17 `_global_records`, F16
  `_corroborate_identical`, and a global reject-only contract. Its bounded
  common204 replay changed 87 redundant refs to 0 across 188 mappings without
  semantic-axis change. It needs two independent reviews, then complete 54
  evaluator replay and additive old-to-new identity receipts.
- F18 audit proved a conservative +29 candidate set: NVB117=10, NVB120=8,
  SHB175=11. The F18 branch is unreviewed prototype code. Keep the other 11
  upper-bound cases unresolved until source repair/endpoint review.
- Cross-page audit found 35 terminal continuation documents. Build the shared
  continuation primitive only after provenance repair; it must require
  sender-last/receiver-first MONEY, reciprocal adjacency, owner/reset,
  period/unit/frontier lineage and inverse source-ref restoration. It alone
  does not solve F36 terminal-root cases.
- Laptop coordination: common204 has a harmless metadata-contract transition
  (184 `prompt_variant` frontiers, 20 legacy `prompt_sha256` frontiers; all
  11,454 page/version/run tuples match full271). Preserve both forms; do not
  repin or call a provider. F39 remains unclaimed until a successor-selection
  compatibility authority is reviewed.

## S3 preservation map

All objects are in private bucket `test-s3-duylv`, SSE AES256 and bucket
versioning enabled. Never overwrite/delete these prefixes.

| Prefix | Content/state |
|---|---|
| `bctc-ai/machine-migrations/20260905T014806Z-family40-checkpoint/` | Full restore authority: Git bundle, corpus/PDF/database archives and migration manifest. |
| `bctc-ai/coordination/2025-current/v1/artifacts/vps/20260905-f36-provenance-dedup-9a01a391-v1/` | F36 correction checkpoint complete, terminal HOLD. `CHECKPOINT.json` VersionId `XUxqwxbs1_80c2u5k52zvZJ2x5KI4TxR`, SHA `b1cb1de1ef9a5142cf582392e2fb29ca85c5e3cd26d85cb0acddafe2f35e73f3`. |
| `bctc-ai/coordination/2025-current/v1/artifacts/vps/20260905-f36-owner-axis-partition-fc9b6218-v1/` | Reviewed F36 speed patch payload/manfiest; publish/verify only a nonterminal checkpoint after reading the audit. |
| `bctc-ai/coordination/2025-current/v1/artifacts/vps/20260905-f37-credit-risk-provision-6feb298-v1/` | F37 code/review payload + additive historical self-containment evidence; no terminal claim. Run re-audit before sentinel/checkpoint. |
| `bctc-ai/coordination/2025-current/v1/artifacts/vps/20260905-f30-service-leaves-6a62071-wip-hold-v1/` | F30 WIP freeze, full271 sweep, audit and `results.sqlite3` snapshot. Not release authority. |
| `bctc-ai/coordination/2025-current/v1/artifacts/vps/20260905-cross-family-coverage-speed-audit-v1/` | 54-evaluator audit. |
| `bctc-ai/coordination/2025-current/v1/artifacts/vps/20260905-shared-source-ref-provenance-audit-v1/` | Shared duplicate-source-ref audit and reproducible scanner. |

## First tasks on the new machine

1. Verify S3 version/hash manifests and the migration restore before any edit.
2. Independently review `codex/shared-source-ref-unique-vps`; if accepted,
   run staged common204 then full271 54-evaluator provenance replay, with
   translation receipts and no historical overwrite.
3. Rebase `codex/f30-service-leaves-vps` onto that accepted shared commit;
   make the 3 expected uniqueness tests green, rerun full271 and only then
   request F30 release review.
4. Review F18 WIP from scratch against its PDF/JSON evidence; do not assume
   its 1,195-line prototype passed a suite.
5. Complete the common204 prompt-frontier compatibility authority before F39.
6. F41 stays locked until F36, F37 and F39 reach terminal acceptance.

## Exact local evidence copied into this branch

- `handoff-artifacts/F30_SERVICE_ACTIVITY_FINAL_FREEZE.md`
- `handoff-artifacts/SHARED_SOURCE_REFERENCE_STAGE1_FREEZE.md`
- `handoff-artifacts/CONTINUATION_PRIMITIVE_AUDIT_2026-09-05.md`
- `handoff-artifacts/continuation-primitive-audit-v1.json`

The audit reports retain their hashes in the Git history and S3. If a claim in
this handoff conflicts with an immutable S3 manifest, the manifest wins.
