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

The full271 accounting run has now completed as **EXPERIMENTAL**, with 200 READY /
0 NOT_OBSERVED / 71 UNRESOLVED and 720 exported mappings. Exact independent cold
source replay, fresh SQLite persistence, exact reload, quick_check (`ok`) and
foreign_key_check (no rows) pass. The source-observation contract reports zero
violations. All 13 registered pixel repairs replay. These results are not family
acceptance: the full source/PDF residual audit, independent common204 accounting
run, projection and release ledger still require completion.

The six-document panel on the preceding 364-test bytes gave 3 READY / 3 UNRESOLVED.
It is not full-corpus acceptance. SSB's opposite expense sign presentation and
VBB's full current-tax phrase/source-context handling remain algorithm gaps to
resolve, not genuine conflicts that can simply be marked terminal. LPB's PDF
visibly prints different prior-year adjustments, 8.966 versus 9.035, in two
presentations; retain and authenticate that source conflict without changing
either amount. Its current early semantic rejection is not yet a sealed conflict
disposition. No family completion or Excel completion is claimed here.

## Completed experimental full271 accounting result

Run directory:
`/srv/bctc-receipts/f39-full271-sourcefix-d4c7b792d4334a01b518618f414d3147/`.

| Artifact | SHA-256 |
| --- | --- |
| `income-tax-sweep.json` (49,082,721 bytes) | `a574d9f5803fd0bb77c1b47c007307427ce94c7ecd06dd3ceeee18eae7eead9c` |
| `income-tax-audit.json` (411,562 bytes) | `55baf2ff213aedfcbb08101116e13eee727c133b972529b6a790c5c7ef9f23e8` |
| `f39-results.sqlite3` (82,530,304 bytes) | `707cb0a91440230cf473eceb2465252b998cb180f338f2c4ab225c0a4173de28` |

Run ID: `gjfafstorev1:run:07118535579e1bbc6f4dd6ad99a854eff0ad9265e419bcfb9d41d45df75a1477`.
Sweep ID: `gjfafsv1:sweep:174592230190ff87854ea4a5642dd97a49e83f59f46d0a0c37a8bb4989334478`.

Post-run gate report:
`/srv/bctc-receipts/f39-full271-sourcefix-gate-report-d876c3980b7f44b18bc184606715e382/F39_FULL271_SOURCEFIX_EXPERIMENTAL_GATE_REPORT.json`,
SHA-256 `e655432ff69dac5f7f1623addc21405ca1d4850a124a33876bf2eba98b7171fa`.
It independently verifies artifact hashes, the fresh SQLite checks, the 13
registered repair receipts, and every source/config/test byte from the focused
witness. Its state is explicitly `PASS_EXPERIMENTAL_WORKFLOW_FAMILY_ACCEPTANCE_INCOMPLETE`.

The 71 held documents are an investigation frontier, **not** 71 authenticated
genuine source conflicts. The new controls reveal these groups:

| Current reason | Documents | Next investigation |
| --- | ---: | --- |
| Opposite direct note / primary signs | 29 | Prove source-visible expense presentation, periods and units; retain original numeric values |
| Other direct note / primary mismatch | 17 | Compare actual role, period, unit and population evidence |
| Current-tax parent semantic guard | 9 | Exact aliases and explicit source hierarchy; known other subtotals remain vetoed |
| Supplemental root control mismatch | 7 | Root/source periods and independently authenticated presentation controls |
| Multiple supplemental roots | 6 | Determine distinct source populations/periods versus genuine duplicates |
| Invalid primary money cell | 2 | Inspect exact PDF-visible transcription; no provider retry or inferred digit |
| Incomplete current-tax frontier | 1 | Inspect every source-visible component and blank independently |

Timing, without any base cache: selected JSON loading 24.33 seconds (271 batched
API calls, 14,945 rows, 70,266,089 bytes); shared base clustering 306.49 seconds;
family evaluation 130.77 seconds; independent cold replay and persistence 540.12
seconds. These identify clustering/replay, not Gemini ingestion, as the dominant
work. Preserve cold replay as an acceptance gate; target immutable evidence reuse
and bounded retrieval rather than rerunning providers or weakening checks.

An external prospective exact-alias probe compiled a private topology copy,
without touching repository configs, code or source JSON. Adding the full phrase
`Chi phí thuế thu nhập doanh nghiệp hiện hành` makes VBB ordinal 259 READY with
seven mappings and keeps four wrong-semantic-parent probes UNRESOLVED. However,
it also makes ABB ordinal 1 enter the direct-note branch and hit the existing
opposite-sign rejection. **The alias-only proposal was not adopted.** It needs a
generic, source-authenticated presentation/context treatment with regression for
the existing ABB success before production implementation.

Prospective probe:
`/srv/bctc-receipts/f39-exact-current-tax-alias-probe-a966aa84b9f747e088a54bbfe6e51cef/F39_EXACT_CURRENT_TAX_ALIAS_PROSPECTIVE_PROBE.json`,
SHA-256 `7d1824c186482a1d86590259048adea6231a4d45d931bf3a014e4f989e17f308`.

The five earlier witness receipts were published under fresh, non-overwriting
S3 keys at
`bctc-ai/coordination/2025-current/v1/artifacts/F39/20261004T011943248786Z-012b43b626a448b580ccc293c8b3c856/`.
Each exact VersionId was downloaded and compared byte-for-byte. Publication
receipt SHA-256:
`a3bdb3b70ad0922987720bf82d4d87c1b732736c6f3dfc3646c83470633a64b5`.
This backup and the successful workflow do not authorize READY_FOR_INTEGRATION,
F39 terminal, changes to frozen shared files, or opening F41.
