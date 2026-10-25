# F37 credit-risk provision expense: Claude-root FULL271 proposal checkpoint

After the user handed full authority to Claude on 2026-10-25, F37 was resumed from Codex's reviewed
worker `6feb2989` (static review `F37_WORKER_6FEB298_STATIC_SEMANTIC_REVIEW_20261023_V1.json`:
NO_GO as-is, three bounded period corrections required). Work is on the Claude branch
`claude/f37-credit-risk-provision-v1`; Codex branches and the integration branch are untouched.
The shared multitable evaluator and generic runner are not modified: every change is in the
Family-37 module, its topology config, a new export module, and tests. Everything below is an
EXPERIMENTAL proposal, not financial acceptance.

## Commit chain

| Commit | Change | Focused gate |
|---|---|---|
| `315d1ca8` | the three reviewed period corrections (full-year bounds, annual layout, separate-role windows) | 295 PASS |
| `99332f8a` | full-year window judged by boundary dates and parsed range (doc 198 false hold) | 298 PASS |
| `b050bb77` | per-document fail-closed: candidate / authority disagreement and UNRESOLVED-trial coverage no longer stop the corpus | 301 PASS |
| `8d3e8b0b` | relative "Kỳ này / Kỳ trước" lanes inherit only an annual root window (`14ed4c25`, comparative-only, superseded) | 302 PASS |
| `08953dd3` | topology aliases: NAB debt-sale reversal, TPB purchased-debt and L/C general provision rows | 304 PASS |
| `40ddaa7c`, `53809c3a` | TM workbook module for READY trials | 8 / 14 PASS |

Baseline at `6feb2989`: 272 PASS on the same nine modules. Receipts:
`restore-receipts/F37_CLAUDE_*_TEST_RECEIPT_20261025_V1.json`.

## Corpus findings that drove the fixes

The diagnostic driver runs the runner's evaluation chain per batch of the 21-batch FULL271 plan
(`96698e9f`): region query, page decode, indexed evidence, trials, mandatory replay validation,
flat sweep validation, source-observation contract, source-row coverage.

- At `6feb2989` and `315d1ca8`, 7 of 21 batches raised on 9 documents.
- The scoped PDF review of the READY output found wrong-period exports:
  - doc 4 (ABB Q1): the prior full year exported as Q1 2024;
  - docs 37 / 38 (EIB Q4): quarter movements exported on the year-to-date lane.
- It also found wrong roles in docs 92, 225 and 231. Printed numbers matched on every reviewed page.

## Result at `08953dd3`

- 271 documents: 120 READY, 151 UNRESOLVED, 0 NOT_OBSERVED.
- 534 mappings / 1,068 values; coverage violations 0 in every batch.
- UNRESOLVED reasons: 76 transposed presentation not unique, 65 detail / primary duration
  conflict, 8 source continuation not closed, 4 candidate / authority coverage not exact.
- 120 TM workbooks in `restore-receipts/F37_CANONICAL_PROPOSAL_WORKBOOKS_FULL271_53809C3A_20261025_V1`.
  An independent stdlib audit checked 413,040 lane cells with 0 violations.
- Printed dashes are written as "-", never 0; unobserved lanes stay empty.

## Update 2026-10-26: whole-corpus store and gated audits at `9fc73ce4`

`9fc73ce4` treats a first-quarter movement ("Quý 1/2025") as the three-month year-to-date root
window (322 PASS). One whole-corpus sweep (peak 1.8 GB, 4 h 44 min) gave:

- 127 READY / 144 UNRESOLVED, 562 mappings, coverage violations 0.
- 7 documents recovered (MSB 84/88/90, OCB 126/132/136/138); each was checked against its PDF page.

All gates were run with the runner's own functions on that sweep:

- Registered source repairs: 9 of 9 authenticated against their PDFs.
- PDF-visible source-row audit: 271 PDFs, 1,719 page renders, 3,275 source rows, 0 uncovered.
  The 18 review categories were read by hand.
- PDF residual audit: 144 held documents, every page re-rendered and matched.
- EXPERIMENTAL store: `bcae2a01`, written after a mandatory full source replay; exact reload;
  562 mappings / 271 trials; 0 selections.

127 TM workbooks were exported; an independent stdlib audit checked 437,134 lane cells with 0
violations. Receipt: `restore-receipts/F37_CLAUDE_FULL271_STORE_AND_GATED_AUDITS_9FC73CE4_20261026_V1.json`.

## OFFICIAL selection (Claude-owned store)

The same sha256-pinned sweep was ingested with `run_kind=OFFICIAL` into a new Claude-owned
store. The mandatory full source replay passed, the reload was exact, and the store records one
`family_current_selection` for CREDIT_RISK_PROVISION_EXPENSE (run `fa4d8705…`, store `156a52b4`).
No shared or Codex store was written, and the integration branch is untouched.
Receipt: `restore-receipts/F37_CLAUDE_OFFICIAL_SELECTION_9FC73CE4_20261026_V1.json`.
- Dated opening / closing balance rows were investigated as a coverage lever and rejected
  (`restore-receipts/F37_CLAUDE_DATED_ROW_LEVER_INVESTIGATION_20261025_V1.json`):
  - EIB's dated rows prove "Kỳ này / Kỳ trước" are the current and previous QUARTER, not the
    report's year-to-date and prior-year lanes.
  - VAB's windows match, but VAB prints the allowance roll-forward in parentheses, so the
    charge would be exported with the wrong sign; correcting it would need sign flipping.
  - The 65 duration-conflict holds stand.
