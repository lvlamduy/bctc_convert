# F39 original-source replay checkpoint — 2026-10-04

This is a non-terminal development checkpoint, not a family release ledger.
The active branch is `codex/f39-income-tax-laptop`, descending from base
`8efd618b6c77f0cdbb402a440e7ba3b3549184f1`. Production scope remains 2025 to
current. The sole-laptop amendment and F39 → F36 → F37 order remain binding.
No provider was called; F36/F37 and the two frozen shared files are unchanged.

## What failed, and why

The first post-implementation full271 run stopped before persistence because
the public page loader revalidated a stored page into a different table layout.
The restore database itself still matches its original byte count and SHA-256.
A finite public-API census found 15 failures across 13 of 271 documents; the
other 14,930 selected pages replayed exactly. This is a newly discovered corpus
execution failure, not a missing restore artifact or permission to re-extract.

For all 15 pages, a separate read-only audit proves:

- Original canonical bytes, canonical SHA and selected content ID are exact.
- Current validation removes exactly one redundant TEXT label column from one
  table. Each removed cell duplicates its row label, or is blank on a GROUP.
- All remaining columns, values, labels, hierarchy, rows and metadata are exact.
- No number, sign, period, unit, dash or financial blank is changed.

The store's existing two-LF canonical serialization is retained byte-for-byte;
there was no newline corruption. Original manifests, database and source PDFs
were neither modified nor resealed.

## Family-local remedy

`gemini_income_tax_source_page_loader_v1.py` performs batched read-only loading,
replays public extraction/repair provenance, and verifies original BLOB SHA,
content ID, ordering, page status and exact canonical bytes. It requires current
mechanical validation, then permits only an independently proven, unique,
lossless redundant-TEXT-column projection as the validation witness.

**The mapping input is always the original stored JSON, unchanged.** Original
column ordinals are retained. The normalized copy is never substituted into the
evaluator. Unknown changes, padding, reordered rows, other TEXT loss, financial
changes and metadata changes fail closed. The hot path and independent cold
source replay use the same original-byte authentication; cold base clusters
still come from the independent shared SQLite query, without the hot cache.
Per-page content-addressed replay receipts are re-created from actual reads;
their complete ordered-axis SHA and exceptional witnesses enter run diagnostics.
Loader, mechanical validator and canonical contracts are implementation-bound.

## Witnesses

External paths below are additive artifacts, not rewritten historical receipts.

| Gate | Result | Receipt SHA-256 |
| --- | --- | --- |
| Original public API census | FAIL_CLOSED: 15/14,945 pages | `75211cea6538cd3b0c1e85e4cceb6ec58c1ab6a3fd20c4d1951aede16dd966d2` |
| Finite 15-page structural classification | PASS, classification only | `7f9d22d969b49c9aaab159bed93a48c3f9db9f577e41ff02edb295a8d22155dc` |
| Current F39/shared focused suite | PASS: 400 tests, no failures/errors/skips | `fc4329a4d2db253f748c02f72432dd0d89c1d9b493564f9e4000a10e824eb8e6` |
| Full271 original-source read census | PASS: 271 documents / 14,945 pages; 15 lossless witnesses | `0cf607550d9417280a9431ee2e2e5695d141672edb9b47c289df3a44fa19abac` |
| Common204 independent read census | PASS: 204 documents / 11,454 pages; 11 lossless witnesses | `a62926772e4b08f20a2673b7fe56d054605e6cd9c742ac1b6e8d63737c383e1d` |
| LPB/VBB PDF review | Source-visible investigation only, not terminal | `20e78aed88fd575ece86c859e550c4e57bd5054afbb42dc8b219733389637f25` |

All read censuses verify source database and implementation bytes unchanged.
The focused witness checks unchanged source/config/test bytes and actual imports
from this checkout under Python 3.12 with isolated bytecode. Ruff and diff checks
pass for the owned changes. The new 36 tests cover historical SQLite replay,
independent cold replay, source-byte/content-ID/provenance tampering, and lossless
positive/negative cases, in addition to the preceding 364 focused tests.

Artifact roots:

- `/srv/bctc-receipts/f39-lossless-label-classification-ab53a3b9453349a6809584806c944f9f/`
- `/srv/bctc-receipts/f39-sourcefix-focused-9a2358ee8f2c48c3a7d51f75ef206d8d/`
- `/srv/bctc-receipts/f39-full271-original-source-census-95651af708a54c76a1a649a8cd40c2bc/`
- `/srv/bctc-receipts/f39-common204-original-source-census-cc5b33a05bb149edb20be661ba89e71e/`
- `D:\bctc_bank\restore-receipts\F39_LPB_VBB_PDF_REVIEW_2026-10-04.json`

## Still required

The new full271 accounting run is in progress at this checkpoint. Counts, cold
replay, fresh SQLite persistence and integrity are not yet claimed as passed.
An accounting run remains EXPERIMENTAL until its full source/PDF residual audit,
common204 independent accounting run, projection and release ledger are sealed.

The six-document panel on the preceding 364-test bytes gave 3 READY / 3 UNRESOLVED.
It is not full-corpus acceptance. SSB's opposite expense sign presentation and
VBB's full current-tax phrase/source-context handling remain algorithm gaps to
resolve, not genuine conflicts that can simply be marked terminal. LPB's PDF
visibly prints different prior-year adjustments, 8.966 versus 9.035, in two
presentations; retain and authenticate that source conflict without changing
either amount. Its current early semantic rejection is not yet a sealed conflict
disposition. No family completion or Excel completion is claimed here.
