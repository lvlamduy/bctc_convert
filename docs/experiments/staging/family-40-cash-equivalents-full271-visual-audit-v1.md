# Family 40 — cash equivalents full271 visual audit v1

This ledger seals Family 40 (`CASH_EQUIVALENTS`, root RNID 1248) on the
immutable 2025–2026 selected-JSON corpora. No provider was called. Source
PDFs, selected page JSON, and page stores were read only. Results remain
experimental schema-mapping proposals, not canonical or export authority.

The governing rule is direct and fail closed: a mapping must come from a
source-visible two-period cash-and-cash-equivalents table, use an accepted
integer `MILLION_VND` presentation, and retain exact row/cell provenance.
Blank cells are never zeroed or backsolved. A visible dash may be repaired
only by an authenticated, registered PDF observation bound to the exact
source, physical page, selected page JSON, table, row, column, full-page
render, and crop.

## Authenticated inputs and frozen dependencies

- Full271 index:
  `/dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts/current-corpus-manifest-indexes/8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a.json`
  (422,971 bytes; SHA-256
  `969ff5f80732c39e4b7543ca1f5c1e5b5b827260f19981ed02945fe0c7379219`).
  It binds 271 documents / 14,945 selected pages and a 573,145,088-byte
  page-store input with SHA-256
  `ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7`.
- Common204 index:
  `/dev/shm/bctc-ai-27-bank-family-live-v1/current-corpus-manifest-indexes/32c474f657f9484244e9675a0ca4801cb49b4923971dfb7bea17081904154747.json`
  (317,566 bytes; SHA-256
  `acc1d08e45e5a05925c434ae1c96fd6bc481a0e6ca61fc9f78e155efca7365b1`).
  It binds the exact 204-source common subset / 11,454 selected pages and a
  553,984,000-byte page-store input with SHA-256
  `a14904a492e6beae165b81f7aa1738352a9824e113f1b163a46ee277d37e0220`.
- The shared multitable evaluator and generic runner were used read only at
  SHA-256
  `bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2`
  and
  `d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5`
  respectively.

## Baseline and bounded family-local recovery

The full271 census evolved as the family vocabulary and structural receipts
were added:

| Checkpoint | READY | NOT_OBSERVED | UNRESOLVED | Mappings |
|---|---:|---:|---:|---:|
| Frozen-shared read-only baseline | 15 | 105 | 151 | 82 |
| Direct source-label inventory | 62 | 105 | 104 | 316 |
| Evaluation/topology configuration | 130 | 105 | 36 | 622 |
| Root/owner configuration | 139 | 103 | 29 | 672 |
| Family adapter v5 | 169 | 82 | 20 | 819 |
| Pre-final v6 | 195 | 65 | 11 | 969 |
| Final family-local algorithm | 200 | 65 | 6 | 995 |

The final adapter's query, recovery, and projection decisions are
value-independent structural operations; the nine source repairs described in
the next section are separately authenticated observations:

- exact owner recovery inside a unique cash-equivalents section/table;
- an exact KLB period-header projection with compatible two-period lanes;
- typed partial-root omission: a visible sibling lane remains mapped while a
  blank lane is retained as `coefficient=null` / `BLANK_SOURCE_CELL` and is
  excluded from equations;
- an exact VBB primary supplemental projection requiring one unique earlier
  same-page primary cash-flow closing-balance anchor. Only a missing unit may
  be inherited, and then only from the immediately preceding selected page
  when it has a `PRIMARY_STATEMENT` / `CASH_FLOW` table marked
  `CONTINUES_ON_NEXT_PAGE`, compatible periods, and an accepted unit; and
- a narrow narrative-owner receipt used only when the section contains one
  unique complete Family-40 table with one terminal total/control row.
  Ambiguous, mismatched-owner, nonadjacent, reset, nonterminal, and
  untyped-control shapes fail closed.

Generic `SECTION_NARRATIVE` ownership is intentionally disabled. Enabling it
globally regressed five genuine PGB/SHB direct tables by binding unrelated
narrative text. The family-local receipt recovers only EIB/SGB shapes that
satisfy the complete structural proof; it does not use bank, document, page,
row values, or expected totals as acceptance conditions.

## Blank safety and authenticated source repairs

The registered source-repair artifact contains nine exact visible-dash
observations. Its repair axis SHA-256 is
`29ac47c544b0ff49acb3dec1986f2dcc0ae7c6a6a2cf5ff54b56753fa36fee48`.
The observations bind full271 ordinals/pages 49/39, 50/40, 70/54, 71/58,
72/54, 76/55, 81/44, 86/47, and 117/47. Each receipt authenticates source
bytes, physical page, full-page RGB render, selected page JSON version,
section/table/row/column identity, before-null state, render/crop bytes, the
manually reviewed visible-dash observation, and after-dash state. The machine
authenticates the registered pixels and declared `observed_pdf_glyph: "-"`;
it does not infer a glyph class from pixels.

No raw null cell is changed merely because an equation balances. The final
full271 sweep has 10 unique blank value lanes, all with null coefficients;
none enters a sum or equation. The global contract reports 20 blank-cell
occurrences because it audits both the trial-level and candidate-level copies
of each mapping. The old 140-trial sweep is a diagnostic safety baseline only,
not a runner oracle or implementation reference: it contains four unsafe
`INFERRED_BLANK_ZERO_IF_EQUATION_EXACT` cells and is never used to promote a
current result. The current global source-observation gate reports zero
derived cells and zero violations.

## Complete PDF and selected-JSON residual gate

Every final N/U document was inspected in its bound PDF at deterministic
200-DPI render resolution, and every selected-JSON target surface was
inventoried. The registered machine gate independently re-authenticates PDF
bytes, scans every physical PDF page for the fixed normalized target terms,
recomputes the complete selected frontier across section titles, section
narratives, table titles, and row labels, and verifies RGB/alpha-false
PyMuPDF 1x PNG render hashes for every review page.

The exhaustive full271 residual axis contains 71 documents:

- 65 NOT_OBSERVED documents have primary cash-flow opening/closing-balance
  surfaces and policy-only note disclosure, but no direct two-period
  component table: ABB 3–12; NAB
  94–96 and 99–107; OCB 126–129 and 132–139; STB 195–198 and 201–208;
  VAB 243–244, 246–248, and 250–255; VBB 263 and 265–271. Their selected
  target surfaces contain no direct two-period component table.
- Six UNRESOLVED documents have a direct, visible three-component table and
  terminal total, but the source unit is VND and every one of the eight
  values per document has a nonzero remainder modulo 1,000,000: OCB 124 p72,
  125 p70, 130 p73, 131 p72; VAB 241 p44 and 242 p44. Inexact scaling to the
  schema's integer `MILLION_VND` unit is forbidden.

The manual visual evidence is content addressed:

- review-axis JSON: 38,644 bytes; file SHA-256
  `088b05ac73631e87313b10a14a444b48ddc2def430fcf2f2632d697efa23a24b`;
  canonical 71-page/source/render axis SHA-256
  `454288fc495409fcc2d411660997dfc1adf1fd725c7762061e692168bd70b632`;
- findings JSON SHA-256
  `9fa7cce93b2237e9850dff881f8e70b7ef9d1ab7d33bf3384253efc25583860f`;
  and
- raw render evidence JSON SHA-256
  `59ddae5b3143833654a633c0a511e67b0540b18674dd24ee8a3a1903759801a6`.

The registered full271 residual axis has SHA-256
`19bbd83af42830e57488b2a05e300ba035b52cd8016c6d24f6e10d8509b86441`.
The independently reordinaled common204 axis contains 50 N / 4 U and has
SHA-256
`64354a4d2e278829be494edea20411050dfaaf6ed121c4644bb78661681b3f25`.
No visible, exactly representable Family-40 table is left behind.

## Terminal results and source-only inventory

Authoritative terminal values come only from the clean specialized runner. It
authenticates its inputs and the PDF residual spec, ingests through the exact
registered source-replay callback while the store byte-checks that callback,
then reloads the stored sweep and requires typed/canonical equality.

| Corpus | Documents | READY | NOT_OBSERVED | UNRESOLVED | Mappings | Equations |
|---|---:|---:|---:|---:|---:|---:|
| full271 | 271 | 200 | 65 | 6 | 995 | 213 |
| common204 | 204 | 150 | 50 | 4 | 760 | 165 |

The full271 mapping-role census is CASH 200, CENTRAL_BANK 200,
INTERBANK_GENERAL 109, INTERBANK_DEMAND 89, FAMILY_ROOT_TOTAL 192,
INTERBANK_TERM 122, and SECURITIES 83. All 995 mappings use
`MILLION_VND`. Cell states are 1,928 `RAW_SIGNED_INTEGER`, 10
`BLANK_SOURCE_CELL`, and 52 `DASH_ZERO`: 43 native selected-JSON dashes plus
nine registered PDF repairs.

The common204 mapping-role census is CASH 150, CENTRAL_BANK 150,
INTERBANK_GENERAL 80, INTERBANK_DEMAND 73, FAMILY_ROOT_TOTAL 146,
INTERBANK_TERM 94, and SECURITIES 67. Its cell states are 1,473 raw integers,
four typed blanks, and 43 dashes: 34 native plus nine registered repairs.

The exhaustive source-only inventory is empty. Across all 206 full271 and 154
common204 candidates, `source_only_unmapped_rows`, table `source_only_rows`,
and `unmapped_direct_family_rows` contain zero entries. All residuals have one
of the two exact dispositions above; neither policy text nor inexact VND
scaling is silently mapped.

### IDs and durable artifacts

Full271 IDs:

- sweep
  `gjfafsv1:sweep:a0608b259f1946dfbd770f24f40b37453d4ef3d6b390c1b4530a8a05c00f3c87`;
- audit
  `gjceauditv1:audit:c85392b120068dcd43ad443a1608e3514fd37769309051159f37759f9cc1f857`;
  and
- store run
  `gjfafstorev1:run:55dcd80af014c112be265a4e47836423ad3de1ff0055d3074cb94b922c522e43`.

The full271 audit binds 18 query-recovery receipts, two header projections,
eight partial-root omissions, four primary-supplemental projections, nine
source repairs, 213 equations, and all 71 PDF residuals. Its query-recovery,
mapping, and residual-axis SHA-256 values are respectively
`55e5651c4afbb273db20b06574f3d9283763e7fffc4ccf3388a09dd30e346fb6`,
`803decdb5e93fd7b037e1afac586d1c685ef868926e69a8260705cd1143eb9dd`,
and
`19bbd83af42830e57488b2a05e300ba035b52cd8016c6d24f6e10d8509b86441`.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `/dev/shm/f40-authoritative-full271-bb319-final-v2/family40.json` | 41,459,566 | `40db99d60eeb2249b3f744aedb23d7a35195bca40c7a5dac4253b4a7fcdc74f0` |
| `/dev/shm/f40-authoritative-full271-bb319-final-v2/family40.audit.json` | 10,923,207 | `e848ebccc3e1ec0204b22f94edacda9c8214d3e7178b8aff25858d1f8883ba5f` |
| `/dev/shm/f40-authoritative-full271-bb319-final-v2/results.sqlite3` | 60,329,984 | `8524288105d1fc54ec76f87b98997038b7c9c6b1c18570d625b603ad81b26dab` |

Common204 IDs:

- sweep
  `gjfafsv1:sweep:26328146dbcaa0136dc7f1311a5ffd3ef1b368540bcbf0d1a5e988c7f8c6f678`;
- audit
  `gjceauditv1:audit:187024ae51acb173246cdfd27f63bee9fa6c8cda28dd8ac320e6f980342098d3`;
  and
- store run
  `gjfafstorev1:run:f2e884a7a1c1527ac4cb959b0b851247faccdaa097699d1dd23c1a845d6bc714`.

The common204 audit binds 12 query-recovery receipts, one header projection,
four partial-root omissions, two primary-supplemental projections, nine source
repairs, 165 equations, and all 54 PDF residuals.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `/dev/shm/f40-authoritative-common204-bb319-final-v1/family40.json` | 31,594,910 | `d376b6100b1775fb0da993697f006a7cd15e25c7f33bd04b3fa3d81547c9cf8e` |
| `/dev/shm/f40-authoritative-common204-bb319-final-v1/family40.audit.json` | 8,348,130 | `369e485bd94a320e0d769dced9fb4276231b2f0b9e0a6d0547eb05e1bb5535a4` |
| `/dev/shm/f40-authoritative-common204-bb319-final-v1/results.sqlite3` | 46,039,040 | `6321bc36f04f7a6d8320e4080960bef4f7e46414611de9a5ca51bed1e6d51a6f` |

## Historical comparator boundary

The enforced comparator policy is `DISJOINT_EXPANSION`. The runner
authenticates E-0092 (101,733 bytes; SHA-256
`b6dc3e68842ce4441bde2edf76003a3018ba00678833fd04636e64c8159624d8`)
and E-0147 (125,341 bytes; SHA-256
`a84a8ce746dd114fe015587ed645fe15d0a94f32605bf0be47e94ce8ff6c4275`),
eight trials each. Their 16 source identities have zero overlap with the
current 271/204 corpora; the receipt has an empty comparison axis and cannot
promote a current trial.

The separate old-140 sweep at
`/tmp/gemini-json-first-corpus-production-v2/artifacts/current-family-results/family40-cash-equivalents/sweep.json`
(23,107,906 bytes; SHA-256
`8293f0faa5bcf12beba76196b439c2f4f5d2c56b032c252501728bf64b345369`)
was inspected only as a diagnostic safety baseline. Its four
null-to-`INFERRED_BLANK_ZERO_IF_EQUATION_EXACT` cells are explicitly rejected
by the current adapter tests and global source-observation contract; this file
is neither a runner oracle nor an implementation reference.

## Cross-corpus projection

Full271 and common204 share exactly 204 source SHA-256 identities. A canonical
projection retaining source SHA, status/reasons, source row identity and
ordinal, physical page, labels/hierarchy, values, roles, units, and RNIDs has
zero semantic mismatches. Only content-addressed mapping IDs and
corpus/extraction-relative locator fields are removed.

Two common documents use equivalent selected page-JSON versions (EIB full40
/ common22 and KLB full64 / common41), and KLB has one equivalent
section/table segmentation difference. Their source-visible semantic mappings
remain identical. The projection receipt is
`/dev/shm/f40-common204-full271-semantic-projection-v1.json` (82,057 bytes;
SHA-256
`0ebae57a1f587945afb8cd84be9731684da2a98f466843284f0424a7a2de7bd0`);
its canonical projection axis SHA-256 is
`8bc2e47c790375934a4c091ca82bcac6b9e44d6e4ba13bd0402813f6e1bb30ad`.

## Family-local release hashes

| Path | SHA-256 |
|---|---|
| `config/families/tm-cash-equivalents-topology-v1.json` | `732e25090cf1592dc98b8e1e9b8e56ccb63a51b67c49dd1b6c04b28116469c07` |
| `config/families/tm-cash-equivalents-evaluation-v1.json` | `21a39306833729b3de3717e0bb556db5cc5b440ed89756330ba944eb6ecae7bf` |
| `config/families/tm-cash-equivalents-schema-binding-v1.json` | `885d99d559918e86f3f575bf2978685ded101b507db6a2f6b5bd3bdbb698b295` |
| `config/families/tm-cash-equivalents-pdf-residual-audit-full271-v1.json` | `9503b73c37bcb3fdd19fc8bb1106b7bad234fd4773f2761dabde699911d2aba4` |
| `config/families/tm-cash-equivalents-pdf-residual-audit-common204-v1.json` | `17a972af3c0f86d313001ba270815ae8e986b61a1e4ec44ed5cbc5c1ec534890` |
| `data/registered/gemini_json_cash_equivalents_source_repairs_v1.json` | `4217a3941e5d6dfc14938665f3878c852da485d835d37a1a637ebe92b9b6dcc6` |
| `src/bctc_ai/evaluation/gemini_json_cash_equivalents_family_v1.py` | `49ebacebed93c60c600034a203893050c92104bfe75feba084a2791a4ec4514e` |
| `scripts/experiments/run_gemini_json_cash_equivalents_accounting_family_v1.py` | `ef3f9842d4196f9393ce92395b73900f4976ed45ee2e0d9d8fb1bcdc1d4b3780` |
| `tests/unit/test_gemini_json_cash_equivalents_adapter_v1.py` | `9d9f8a8f8c837ea1bd0b66c087b8557faaf3d551d89a26b2f39052b551674506` |
| `tests/unit/test_gemini_json_cash_equivalents_family_v1.py` | `eefe3e3059134f2010f3443dabc8f02716ade357543f89d8f083864b3fd33fc8` |
| `tests/unit/test_run_gemini_json_cash_equivalents_accounting_family_v1.py` | `cc8f9a4fdc783bc01510d27e1b6d065d3a3ad1bd1001c69bd847585b29657d8e` |

## Verification and conclusion

- Focused Family-40 adapter/evaluator/runner suite: 59 passed in 0.86 seconds.
- Family-40 plus shared multitable query/evaluator/repair/runner, flat wrapper,
  result store, historical-comparator policy, and global source-observation
  suites: 297 passed in 4.86 seconds.
- Full271 and common204 specialized runs both returned `SUCCEEDED`. Their
  outputs are byte-identical to the independently generated semantic sweeps.
  Source replay, typed/canonical trial equality, stored-sweep reload, and
  export registration passed.
- Full271 source-observation audit: 1,990 duplicated mapping occurrences /
  3,980 cells / 20 typed partial occurrences / 20 duplicated blank-cell
  occurrences / zero derived cells / zero violations. Common204: 1,520 /
  3,040 / 8 / 8 / zero / zero. The duplication is the deliberate
  trial-level plus candidate-level representation described above.
- Both result databases return `quick_check=ok`, `integrity_check=ok`, and an
  empty foreign-key check. Their stored row counts are exactly 271/204
  trials, 206/154 candidates, 995/760 mappings, and one export each.
- Ruff, Python compilation, all six JSON parses, family-local diff checks, and
  final shared dependency SHA checks passed. The shared files remained at the
  frozen hashes recorded above.
- Full271 and common204 PDF/source/render authentication, exhaustive selected
  target-surface replay, exact residual-axis validation, and all nine repair
  authentications passed.

The source-visible mapping requirement is satisfied without blank arithmetic,
component backsolve, inexact unit conversion, or expected-result fitting.
Every residual PDF and selected target surface has an authenticated disposition;
there is no visible exactly mappable Family-40 value left behind.
