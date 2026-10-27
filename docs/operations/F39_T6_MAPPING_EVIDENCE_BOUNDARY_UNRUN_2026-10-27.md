# F39 T6 mapping evidence boundary — source-only, UNRUN

Base producer: `673986d3061c3bd16070e7e9094af3aee2c56781` on the owned
combined F39 branch. Root stopped the prior full32 V2 runtime for a confirmed
source-review issue; that stopped attempt is not a PASS for this new producer.

The source-observation mapping contract recursively recognizes structured
objects containing `report_norm_id`, a role and mapping cells. The new T6
printed PRIMARY root receipt stored its prior and bound root images in that
same structured form. An audit of the entire candidate could therefore count
receipt evidence as additional active mappings, including on a typed HOLD.

Only these two new T6 evidence fields now use a lossless envelope containing
canonical UTF-8 JSON text, its SHA-256 and its byte size. Decoding recovers the
exact JSON types, raw strings, signs, nulls, source references and mapping IDs.
The bound image remains absent on HOLD; absent printed totals still acquire
no new receipt. Active mappings and financial permissions are unchanged.
The existing receipt/candidate identity algorithms reseal the changed evidence
bytes, and the existing fresh source trial replay rejects forged envelopes.
The shared walker, frozen evaluator and frozen generic runner are unchanged.

The focused T6 source tests decode both exact mapping images, audit the whole
actual binder candidate with count equal to active mappings and HOLD count
zero, preserve null source cells, and use the actual indexed adapter/trial
replay validator to reject adversarial envelopes even after their own SHA,
size, receipt and candidate IDs have been resealed. Signed-display ownership
negatives also require whole-candidate audit PASS with zero active mappings.

Root's actual focused V2 run at producer `5d08be00ea7ec5876e949ab13bb0619386fe3120`
finished with four failed and 445 passed tests in 312.40 seconds. Three new
replay tests failed before evaluation because their one-page indexed test
manifest inherited a helper's selected ordinal two. That new manifest now
explicitly starts at selected ordinal one, preserving its physical/source axes.
The fourth new test incorrectly expected the normal public whole audit count
to equal the three active mappings: its actual count was six. The unchanged
`income_tax_source_control_receipt.post_merge_root_closure.mappings` retains
three exact legacy mapping images. The corrected public test audits the
unmodified candidate, identifies those exact three images, and requires count
six, with zero additional mappings recognized in the new T6 receipt. Public
HOLD count remains exactly zero. No receipt is removed or sanitized for audit.

This test expectation correction makes no family-wide source-audit-clean
claim. Pre-existing mapping-shaped evidence in legacy receipts remains a
separate corpus-review backlog; those formats and the production adapter are
unchanged by the correction. The failed focused V2 artifacts remain retained.

These corrected tests remain **UNRUN**. No Python import, AST, compile, lint, test, WSL,
corpus/SQLite/PDF/provider job, commit or acceptance claim was performed by the
author. Root owns source capture and the subsequent guarded focused/full gates.
