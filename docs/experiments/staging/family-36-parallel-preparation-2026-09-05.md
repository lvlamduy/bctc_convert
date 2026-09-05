# F36 parallel preparation checkpoint — NOT a release

Date: 2026-09-05. Scope remains 27 banks, reporting years 2025 through present.
Architecture remains PDF → Gemini JSON → authenticated validation → SQLite.
No provider was called; no authority corpus/database or frozen shared file changed.
This document is a WIP handoff, not a full271 ledger or canonical export authority.

## Ownership and runtime

VPS owns F36 preparation on `codex/f36-operating-expense-vps`; laptop reserved
F39 and explicitly acknowledged no F36 writes. User renewed parallel execution
after the original pause. The documented local preparation gate applies;
formal laptop join remains pending, not silently granted by its informal ACK.
F37 remains read-only. No shared-branch push is authorized by role metadata.

Latest laptop event at 06:43 UTC supersedes the earlier reboot/distro blocker:
Ubuntu 24.04 on dedicated ext4 and Python 3.12.3 are installed, and isolated
frozen snapshot/binary/symlink/identity runtime probes PASS. Archive, database
and corpus restore/preflight remain pending; there is still no formal join or
F39 claim. This does not authorize bypassing its user gates or claiming laptop
acceptance from a VPS run.

VPS now has an isolated minimal Python 3.12.13 environment:
`/tmp/f36-python312-runtime.GGDE2m/venv/bin/python`.
Pinned pytest 9.1.1, Pillow 12.3.0, PyMuPDF 1.28.0 and PyYAML 6.0.3 match the
previous diagnostic dependency versions. No full project/dev install occurred.
Runtime/venv use about 200 MB; overlay retains about 152 MiB. Keep at least
128 MiB overlay reserve. All test caches/tmp/SQLite scratch belong on `/dev/shm`.
This is focused-test runtime evidence, not complete project-environment acceptance.

Environment recipe on S3 (all keys here use bucket `test-s3-duylv`):
`bctc-ai/coordination/2025-current/v1/artifacts/vps/20260905-python312-checks-v1/environment/ENVIRONMENT_RECEIPT.md`,
VersionId `j_QR7f0y8UCKxh.rFDfWrA9i33bLfy6q`, SHA
`39958e338dc97e97e9911418ea7f96d96e24c066666efb8f426b004f715f5028`.

## Prepared changes

1. Runner tests use current authentication arguments and properly sealed
   subordinate synthetic audit receipts. Tamper tests isolate outer identity,
   sweep-reference consistency and nested receipt identity. Runtime runner
   remains pinned. This first change was pushed at
   `bf7dac4703a09750186c85e9a0308b95ba770163`.
2. Continuation guard distinguishes truly absent units from unsupported,
   conflicting or mixed unit evidence on both fragments, including captions,
   MONEY headers and Unicode currency symbols. It preserves Vietnamese country
   suffixes and the existing blank-unit inheritance policy; it never infers scale.
3. Primary corroborating roots and shared evaluation input are ordered by
   authenticated selected-page ordinals, with frontier/order-consistency gates.
4. New portable coverage-only builder binds active worktree/import/code hashes,
   explicit inputs/temporary/output paths, unchanged frozen SQLite snapshot,
   input/code stability and exclusive output creation. It does not certify
   manual PDF review, family replay or release. The original archived helper
   remains unchanged. Two PDF auditor helpers are NOT ported blindly.

Owned implementation pins at this checkpoint:

| File | SHA-256 |
| --- | --- |
| F36 evaluator | `7d159e0c14a49b9007ffd6d758ea1d4d2d28674a8b69cb76c4e1ccbcef038744` |
| F36 evaluator tests | `9c2fc79646160ad00865eb655acb8ee14143972f7b41dc5424ac5d6d2495f26a` |
| F36 runner tests | `798f23201bed7de23b977c09d50a6b815254e180ce7d855a7e3d3dd9ae81d8fa` |
| Portable coverage builder | `08570d6109dee9d678c820862066666a6efeb5e9d7b4cc9e9602191b46b5760d` |
| Portable builder tests | `b7a858a84f9e13b8e569b7d2c2f44865165b057f037557aa00c3e61f90a7d41c` |

## Verification actually performed

One combined Python 3.12 run: **373 passed in 24.29 seconds** across 10 modules:
F36 evaluator 153, F36 runner 12, portable builder 18, coordination 29,
migration §9 five shared modules 148, and frozen generic-runner module 13.
Do not add the independent duplicate runs to this count. Ruff/compile and
shared byte pins were checked independently. No full-corpus replay was run.

Use the active source checkout explicitly; the old environment's editable
installation otherwise points at the old `/workspace/bctc-ai` checkout:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts/experiments \
TMPDIR=/dev/shm/f36-python312-stage.UMIpIa \
SQLITE_TMPDIR=/dev/shm/f36-python312-stage.UMIpIa \
/tmp/f36-python312-runtime.GGDE2m/venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/unit/test_gemini_json_operating_expense_family_v1.py \
  tests/unit/test_run_gemini_json_operating_expense_accounting_family_v1.py \
  tests/unit/test_build_f36_source_row_coverage_from_sweep_v1.py \
  tests/unit/test_coordinate_family_workers_v1.py \
  tests/unit/test_gemini_json_multitable_hierarchical_family_v1.py \
  tests/unit/test_gemini_json_multitable_hierarchical_indexed_wiring_v1.py \
  tests/unit/test_gemini_json_multitable_hierarchical_repair_v1.py \
  tests/unit/test_source_observation_mapping_contract_v1.py \
  tests/unit/test_source_observation_lane_math_v1.py \
  tests/unit/test_run_gemini_json_multitable_hierarchical_accounting_family_v1.py
```

Separately, Python 3.12 reproduced the existing four BAB F37 rendered pages'
exact hashes, both PDF hashes, 88 selected-page bindings and four JSON hashes.
This is bounded cross-runtime evidence, not F37 release or a full PDF audit.

## Superseding checkpoint 07:20 UTC — source-visible rejection and strategy

The internal-owner invalid-unit disposition blocker listed in the previous
checkpoint below is now fixed, not merely suppressed. Family-local typed
rejection receipts bind selected source/owner/unit frontiers; indexed query and
trial replay independently reconstruct them. Removing/resealing receipts as
NOT_OBSERVED fails. Unsupported units remain UNRESOLVED without mappings;
genuine absence remains NOT_OBSERVED. Frozen shared files are unchanged.

New evaluator SHA: `696200815d0d5e8e50587a9d5f77e0b9caa3f9a5e703dad5c992d1eaf6ddc79e`.
New evaluator-test SHA: `d134f0e90901ee1066e6f7634c870ddad5ef3527900d4d3c8514b997360ffb36`.
The same ten-module command above now passes **385 tests in 28.28 seconds** on
Python 3.12.13. Root JUnit SHA:
`bc6d5e0fdfd781de4704db725abe47be9b2830675e921c800750117576e64f69`.
An independent reviewer separately ran 165 focused tests and nine extra
tamper/control probes, accepted this preparation checkpoint, and explicitly did
not certify family release. Do not add overlapping test runs to the 385 count.

Six sub-agents are assigned disjoint algorithm/review/diagnostic/schema/PDF/
continuation work. Two PDF triage packages contain 20 personally viewed pages
across 11 documents; their bounded/stale diagnostic comparisons are not new
full271/common204 results. Fresh diagnostic producer and source-repair designs
are preparation work; no full replay or authority DB write has occurred.

The user's new maximum clear-source mapping, semantic Other, parent/child,
derived-sum provenance and page/layout requirements are fully recorded in
`family-36-source-first-mapping-strategy-2026-09-05.md` and sent to laptop:

- Event: `bctc-ai/coordination/2025-current/v1/events/20260905T071529Z-vps-user-requirements-and-strategy.json`;
  VersionId `gljG.U8FvljFCUikaKp0M7PTNKLBefhJ`; SHA
  `cbfb30484c967abd93cfbd3c475d83ad774b358eed145707ab57c78aaa1cfbd3`.
- Strategy S3 object: `bctc-ai/coordination/2025-current/v1/artifacts/vps/20260905-source-first-strategy-v1/STRATEGY.md`;
  VersionId `zn_08JlDaSqWbVp4FH856i3OF21Eh33W`; SHA
  `3c4660ad3202256d10b535dcedfc95e33e5079469e0c2112cd819fa1ce86e592`.

Both exact versions were downloaded and matched. Laptop ACK for this strategy
is still pending. Its latest 07:06 event reports an archive exclusion-policy
failure involving a nested legacy GEMMA document, not a byte-hash corruption.
VPS is independently reviewing evidence only; no migration/object rewrite,
restore exception, F39 takeover or formal join is inferred.

Overlay free space has fallen to about 111 MiB, below the earlier 128 MiB
planning reserve. No additional dependency installation or large overlay
outputs are permitted in this preparation batch; test/evidence files remain
on `/dev/shm`. Capacity must be reassessed before any heavy diagnostic/replay.

## Previous blockers and remaining acceptance requirements

- **Resolved by the 07:20 checkpoint above.** Internal-owner continuation with invalid units previously became NOT_OBSERVED
  rather than UNRESOLVED despite a visible family owner. The committed negative
  tests only establish no incorrect READY mappings there. A separate six-case
  failing reproduction is preserved on S3, SHA
  `0fc10043b619d096f9972b7d80094cf229dd0182de870a2f3059ffc5c9bff61e`.
  The six-case reproduction is now green; the new typed rejection/disposition
  receipt and its adversarial tests resolve this bounded defect. Neither the old
  373 nor current 385 passing tests establish full semantic acceptance.
- Broader non-continuation/primary mixed-unit handling was not certified by
  this bounded patch. Conservative header grammar needs real full271/common204
  differential review; count changes must be explained from selected source.
- Fresh independent full/common diagnostics, coverage, residual and PDF-visible
  audit, private result DBs, replay/projection/integrity and final ledger are pending.
- Old residual helper can derive target statuses from another corpus; old
  PDF-visible helper auto-generates manual-review prose. Neither behavior can
  certify source review. Portable successors need independent corpus inputs and
  explicit actual review evidence. Designs are saved separately, not implemented.

## Product boundary

The current family store/runner exports its JSON sweep, and sealed F40 results
are explicitly experimental proposals, not canonical/export authority. Existing
Excel components do not by themselves prove current Gemini sealed runs assemble
into a complete report workbook. Whole-report coverage, selected canonical runs,
cross-family ownership and cell-level output/provenance verification remain
separate project requirements. Family progress and green tests must not replace
the actual financial-report digitization outcome in `PROJECT_GOAL.md`.

All new report/repro/runtime-test evidence uses immutable coordination S3
prefixes with exact VersionId download-and-rehash verification. No existing
PDF/source DB/image was reuploaded. The final S3 preparation checkpoint receipt
binds the pushed Git commit and all new artifact refs without altering migration.
