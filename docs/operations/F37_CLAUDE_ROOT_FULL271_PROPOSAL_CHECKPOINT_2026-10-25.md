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

## Open

- Store persistence: the replay-gated store ingest needs the whole-corpus page frontier in one
  Family-37 sweep (about 3-4 GB on this host); a streaming ingest is needed first.
- The gated runner's PDF-visible source-row audit and per-document residual audit
  (builder draft: `scratchpad f39new/build_f37_pdf_visible_audit_v1.py`).
- Coverage lever not implemented: roll-forwards that print dated opening / closing rows
  (e.g. "Tại ngày 01.10.2025") state their own window.
