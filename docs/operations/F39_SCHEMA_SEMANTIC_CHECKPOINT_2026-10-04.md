# F39 schema semantics checkpoint — 2026-10-04

Non-terminal descendant of `cdf371a9b9bcbfa030a7c595668300b29704e3d5`,
on `codex/f39-income-tax-laptop`, from migration base
`8efd618b6c77f0cdbb402a440e7ba3b3549184f1`.
Scope remains bank reports 2025–current and all remaining55 families.
2024 PDFs are excluded from production; printed comparatives are retained.
Only F39 changed. No provider, re-extraction, F36/F37 mutation, frozen shared
change, database/source rewrite or existing artifact deletion occurred.

## Corrected meaning and authenticated ownership

- RNID5724 now binds `CURRENT_YEAR_TAX_EXPENSE`, the printed **Năm hiện hành**,
  not `CURRENT_TAX_AT_RATE`. Rate-based money remains unbound validation-only;
  percentage rate remains a separate non-money metric.
- YEAR is nonanchoring and scoped under the internal, unbound structural role
  `CURRENT_YEAR_EXPENSE_CONTEXT`, exact alias **Chi phí thuế hiện hành**.
  The existing CURRENT-parent remains TOTAL. The context has no RNID and is
  not an additive root component.
- A private YEAR population binds the unique original blank GROUP, exact
  descendant YEAR/prior rows and its first closing printed subtotal. Anonymous
  subtotal ownership follows the ordered source group, never the amounts.
  An exact all-observed-lane equation only validates these existing rows.
  Original labels, hierarchy, cells, signs, blanks, kinds and ordinals survive
  projection and source-reference restoration. Unknown/qualified ancestry,
  competing starts, resets and foreign parents cannot supply ownership.
- Generic period labels do not become annual YEAR or rate starts. Flat YEAR
  without this independently authenticated context remains an algorithm gap;
  a separate source-authenticated named-parent rule is still required.
- A deterministic full raw tax-population inventory is collected before
  consumed-row suppression, including role-anchored tables without an owner
  title. It retains complete original table rows, images, owner captions,
  lane/unit axes, all YEAR surfaces and both explicit monetary-rate variants.
  Empty inventory axes are authenticated too. Both query recovery and public
  replay bind and independently reconstruct it.
- YEAR coverage cannot hide an extra unscoped YEAR/period surface. Rate guards
  do not depend on exported RATE mappings. Missing/unknown GROUP closure keeps
  the following tax-effect basis ambiguous, rather than treating a reset as
  proof that income-basis exports are allowed.
- Supplemental rate tax effects remain source-only equation evidence, not
  income-basis5729/5730. A generic candidate that still exports them is held
  with explicit measurement-basis evidence; it is not silently filtered.
- Positive YEAR donation checks printed note/primary population qualifiers
  and primary raw ancestry. Equal amounts cannot prove RIÊNG/HỢP NHẤT or entity
  compatibility; missing/unknown scope is conservatively held.
- Source context and private descriptors bind complete topology, evaluation
  and schema semantics, not just a role-binding subset. Resealed inventory,
  changed policies and forged boundaries fail independent source replay.

## Exact-byte verification

| Gate | Result | SHA-256 |
| --- | --- | --- |
| Python3.12 focused suite | PASS506/506; zero failures/errors/skips;42 actual checkout imports; unchanged inputs | `e75c2563db0cf68fd5c43798810236fbea5d22bbd7e6731fe51a9da92ce35e23` |
|34-document original-source diagnostic |15 READY proposals /19 UNRESOLVED;96 mappings;2,170 original pages | `fa4c0be72f87b159dfaaa57c57b4b8b43eb9577e09aca8479485e0ead5c4c663` |
| Independent SQLite source replay | PASS exact indexed query/trials; no cache; semantic export invariants | `dda25de26d93063fa666fb9e863cd06b1a0dab6262a8edc4281d56b41f762d49` |
| Source observation | PASS zero violations | Bound in diagnostic/replay |
| Frozen shared hashes | PASS exact migration pins | No shared edits |
| Ruff / `git diff --check` | PASS owned F39 files | No lint waiver |

External witnesses:

- `/srv/bctc-receipts/f39-semantic-focused-8147b550616e400caaaadb7cde9b6378/F39_IMPLEMENTATION_FOCUSED_RECEIPT.json`
- `/srv/bctc-receipts/f39-semantic-panel-3dc29f2a6e2449bb9749f18dafc4667f/income-tax-bounded-diagnostic.json`
- `/srv/bctc-receipts/f39-semantic-cold-ef5ac32f010d42528776b0e5477e2aa6/F39_SCHEMA_SEMANTIC_INDEPENDENT_SOURCE_REPLAY.json`

Implementation SHA:
`3b7e25aeefa30c220dfb3ad3ed9785874381e42b3e02f44de6486b4ae5d54e20`.
Topology SHA:
`daf9b4eb7569cb35846f330bf486a55fe690328a0873fb8975325e8ca190671d`.
Binding SHA:
`ec5765e3ea8dc3628641b71df8ea509241951e7b68d506a5c0622b6cb0bca7b8`.
Evaluation SHA:
`fefa04db828da98646365a59a3639ccf599955c7609a5ade13489222162d1cff`.
Independent bounded code review found no remaining reported bypass on these
bytes; runtime and source gates above are separate from that review.

The panel uses the same full-index34 positions as the preceding checkpoint.
Compared with20 prior proposals/128 mappings, five proposals are now held:
ABB1 needs independently authenticated flat YEAR ownership; VBB260/261/262/264
need correct tax-effect population re-evaluation. BVB23 remains a proposal with
seven mappings after its wrongly exported RATE role is removed; VAB249 retains
six. The replay receipt explicitly records all baseline disposition/export
changes. **No no-regression or whole-family acceptance claim is made.**
Legacy mapping-count nondecrease is not authority to restore wrong schema
meaning. Genuine income observations must nevertheless be preserved by the
next independently evaluated population route, not discarded to raise counts.

STB193 now reaches the YEAR source-population guard rather than exporting the
old YEAR+RATE sum. Its correct YEAR observations are independent of rate
money; document-level note/primary population correspondence is still pending.
All19 holds remain algorithm/evidence work, not terminal genuine-U seals.

An intermediate504-test witness failed five checks; it is retained externally
at `f39-semantic-focused-b66b99f6b94f4b77a2d522158187b1ed` (SHA
`8f49cdfe98d6215c61a6e85448cbe1bfde9bdb2718b05cfc7cfa91c41e15d4f3`).
The fixes restored deterministic inventory ordering and separated authentication
positives from tax-effect semantics. The original tax-effect repair scenario
remains an explicit negative; root/repair authentication positives now have an
independent printed taxable-income stage. No failed artifact was deleted or
rewritten, and the failed witness is not acceptance evidence.

## Next work and release boundary

1. Authenticate flat/named-current-parent YEAR populations and document-level
   printed population context, retaining local entity overrides.
2. Re-evaluate complete income, YEAR, RATE, deferred/root populations privately
   before consumed-row suppression. Preserve every genuine income mapping and
   assign every raw row an authenticated disposition. Do not seed a replacement
   result from a basis-conflicting generic candidate or just delete its fields.
3. Add a strict tagged note-only population route, with original outer region
   authority and independently rebuilt private proofs; do not fake PRIMARY.
4. Implement the four SSB local-duration/independent-CF correspondence proofs.
   Annual years stay symbolic; generic KLB relative periods remain ambiguous.
5. Complete remaining source/context holds, then run authoritative
   full271/common204 accounting, source replay, observation, experimental result
   SQLite persistence/reload/integrity, full PDF/residual/projection audit and
   release ledger on exact new bytes.

Current bounded run performs no result persistence or family release.
The older complete full271200/71 result is not this checkpoint's acceptance.
F39 is NOT terminal; no READY_FOR_INTEGRATION is authorized. Continue
F39 → F36 → F37, do not open F41, and do not push the common branch.
