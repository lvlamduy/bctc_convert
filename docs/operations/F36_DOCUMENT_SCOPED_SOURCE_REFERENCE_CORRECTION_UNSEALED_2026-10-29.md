# F36 document-scoped source test reference correction — unsealed

The private `codex/f36-document-scoped-source-v1` checkpoint `9fc0392e` narrows
candidate/title SQL membership to each complete original document. Its first
complete 15-module gate actually collected395, passed393 and failed2. Compile9,
Ruff, all372 prior cases, source/Git barriers and the other21 new cases passed.
Retain that FAIL: receipt `eb62393192c2e1a138e1fa21a8d856c248d3bb44a53a2733b90cb114d8cf78ae`
in `F36_9FC_REQUIRED15_ACTUAL_TWO_PARITY_FAILURES_20261029_V1`.

The new two-document test incorrectly compared the per-document iterator with the
whole-list monolith. The authenticated loader includes the position in its
request (`selection_ordinal`) in the provenance hashed into `replay_receipt_id`.
A request for both documents gives document2 position2; a request for document2
alone gives position1. The parent83e iterator already loaded per document.

The unchanged three-mode diagnostic at9fc actually captured only4/3 differing
leaves in the two failed modes: document2 bridge replay IDs, dependent candidate
IDs, and its selected candidate ID when READY. No financial value, period, unit,
status, scope or HOLD leaf differed between iterator and monolith. Full diff:
`01b06455d5eb45dfe8f708b6e35e6f1a7effff7cd37edf10fb5e5418454ba2de` (145219bytes),
mirror `F36_9FC_PARITY_TYPED_DIFF_ACTUAL_CAPTURE_20261029_V1`.

An independent parent83e clone then ran the same unchanged test body, with only
that explicitly pinned untracked test added. All2749 parent tracked files matched
the authenticated source matrix before/after. It reproduced the same two failed
modes and exact4/3 leaf paths. Parent result `7dcaa477c35b0b72b22c755d1b89aeb93143b5a44383e4c428e3d94020ee619a`
(144711bytes), native mirror `ad8b0d8c8a64bac4fea7d3d28cba48c7cc9f23a928e28b653acf6748d867a992` in
`F36_PARENT83E_PARITY_TYPED_DIFF_ACTUAL_CAPTURE_20261029_V2`.
Both diagnostics preserve actual pytest/outer/time/unit exit1 and publish only
`CAPTURE_INTEGRITY_ONLY`; neither is a passing test gate or financial acceptance.

This test-only correction uses the genuine full-query `NotesSource` in the
parent's per-document iterator request shape as its reference. Its temporary
constructor substitution is scoped to that reference call, restored before the
candidate, and checked by the existing producer-binding guard. Every trial byte,
receipt ID, candidate ID, three modes and other21 tests remain compared unchanged.
No passing financial/source validator is mocked and no ID is stripped.

The stable per-document shape is the reference for this opt-in strict-CORE
producer, not a global change to legacy/default production. Historical monolith
artifacts keep their distinct IDs. No old receipt, store, official selection or
manifest is rewritten or re-sealed; request-independent shared provenance would
require a separate reviewed change.

Corrected-tree compile/Ruff/full15 tests and original cohort metadata order,
financial parity/performance, SQL/cold/source/PDF/residual/Excel/legacy/ledger
gates are still PENDING at this source checkpoint. No speed/fit claim, production
rule change, family seal or integration is granted. F39/F36/F37 remain unsealed,
F41 locked; no provider, frozen-file change or artifact cleanup.
