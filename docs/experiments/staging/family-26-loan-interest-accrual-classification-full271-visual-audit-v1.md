# Family 26 — loan interest accrual classification full271 visual audit v1

This ledger seals Family 26 (`LOAN_INTEREST_ACCRUAL_CLASSIFICATION`) on the
immutable 2025–2026 corpus. No provider was called. Source PDFs and selected
page JSON were read only. The result is an experimental schema-mapping
proposal, not canonical/export authority.

## Authenticated inputs and ownership

- Full271 index:
  `/dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts/current-corpus-manifest-indexes/8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a.json`
  (422,971 bytes; SHA-256
  `969ff5f80732c39e4b7543ca1f5c1e5b5b827260f19981ed02945fe0c7379219`).
- Common204 index:
  `/dev/shm/bctc-ai-27-bank-family-live-v1/current-corpus-manifest-indexes/32c474f657f9484244e9675a0ca4801cb49b4923971dfb7bea17081904154747.json`
  (317,566 bytes; SHA-256
  `acc1d08e45e5a05925c434ae1c96fd6bc481a0e6ca61fc9f78e155efca7365b1`).
- Source PDFs are rooted at `/workspace/bctc-ai`; every conclusion source is
  authenticated by SHA-256 and byte size against its immutable index.

Family 26 exclusively emits report-normalization IDs 982–986. ID 966
(`Tài sản Có khác`) is structural context and is never emitted. Family 22
retains ID 982 only as an unbound, validation-only query bridge and emits none
of IDs 982–986. A matching-corpus cross-family receipt fails closed if Family
22 emits any legacy-owned ID or if the exact
`(source,page,section,table,row,RNID)` axes overlap.

The shared multitable evaluator and generic runner were consumed read-only at
these frozen SHA-256 values:

- evaluator: `bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2`;
- runner: `d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5`.

Historical old-corpus artifacts are authenticated only as disjoint safety
oracles. They have zero source-SHA overlap with full271 and are excluded from
the current-corpus conclusion. Comparator: `DISJOINT_EXPANSION`.

## Family-local evaluation contract

The adapter requires an exact Family 26 aggregate or detail context and owns
only RNID 982–986. It handles continuation/detail tables, source-label
variants, exact VND versus rounded million-VND duplicate presentations,
row-local label loss, and the two observed alternate source representations
(an OCB split-label duplicate and an LPB primary TEXT cell). Both alternates
require exact same-source hierarchy, unit, and value corroboration;
bank/ordinal alone can never authorize a mapping.

Candidate totals are controls, not extra mappings. A visible adjacent detail
total is accepted only when every observed lane closes to an existing
source-observed primary mapping. A later total additionally requires an
intervening structural boundary or hierarchy-root transition. Structural
`Tài sản Có khác` totals and preceding/following totals from other note
populations are explicitly classified outside the family. A target-like raw
row is scanned in the row label, terminal hierarchy label, and explicit TEXT
cells; every hit must be accounted for or evaluation fails closed.

## Terminal corpus results on frozen shared SHA `bb319076…`

| Corpus | Documents | READY | NOT_OBSERVED | UNRESOLVED | Mappings |
|---|---:|---:|---:|---:|---:|
| full271 | 271 | 271 | 0 | 0 | 561 |
| common204 | 204 | 204 | 0 | 0 | 402 |
| full-only expansion | 67 | 67 | 0 | 0 | 159 |

Full271 mapping counts by RNID are 982=271, 983=74, 984=74, 985=68,
986=74. Common204 counts are 982=204, 983=51, 984=51, 985=45, 986=51.

The source-row coverage axes have zero violations:

| Axis | full271 | common204 |
|---|---:|---:|
| classified source rows | 875 | 637 |
| candidate table totals | 267 | 211 |
| raw target-like rows | 1,561 | 1,192 |

The 875 full classified rows comprise 631 exact mappings, 128 duplicate note
totals, 11 duplicate primary presentations, 71 visible detail-total controls,
three blank structural headings, 18 nonlocal aggregate controls, nine
nonlocal row populations, and four typed controls. The candidate-total axis
classifies all 267 rows: 71 closing detail controls, 153 following-other-note
totals with an explicit boundary, 39 preceding-other-subtree totals, and four
structural `Tài sản Có khác` parent totals.

The raw full axis classifies every 1,561 target-like row: 804 already-accounted
source rows, one adjacent split-label duplicate, one TEXT-cell primary
presentation, four credit-risk/financial-instrument controls, 16
expense/reversal rows, 54 general-receivables interest-support rows, three
narrative policy/risk text rows, 388 off-balance uncollected-interest rows,
and 290 related-party rows. None remains silently unclassified.

## PDF-visible no-left-behind gate

The full PDF audit authenticates all 271 PDFs, binds 1,828 distinct coverage
rows to 1,099 rendered PDF pages, and records 28 manually reviewed category
pages. The common audit authenticates all 204 PDFs, binds 1,404 rows to 835
rendered pages, and records 22 manually reviewed category pages. Rendering is
PyMuPDF/RGB/1x1/PNG/no-alpha and binds source SHA, physical page, selected
page-JSON ID, render SHA, and the exact source-row axis.

The manual category axis includes the BAB detail block, VAB exact VND and
rounded duplicate presentations, VBB singleton detail and credit-risk
controls, SHB and adjacent/unlabelled detail totals, TCB/BVB general
receivables controls, MSB/NAB/TPB/ABB related-party controls, KLB financial
asset controls, expense/reversal and off-balance controls, OCB split-label
duplication, LPB TEXT-cell primary presentation, and raw TEXT-cell label-loss
cases. These cases cover each exceptional acceptance/exclusion rule. The
complete machine-bound page axis covers every classified, candidate-total,
and raw-target row, not only the manual samples.

No PDF source repair is required. Every emitted value already has an exact
selected-JSON source cell. There are no N/U documents, so the residual specs
are correctly empty. PDF visibility validates semantic population and
alternate representation; it never invents a value.

## Source-observation and partial-lane controls

The family declares no equations. Blank/null is never converted to zero
because a total closes. A printed dash/zero remains source-observed; a missing
lane remains typed null with state `BLANK_SOURCE_CELL`, and an all-blank role
is omitted.

The full source-observation contract checks 1,122 mapping occurrences and
2,244 cells, including 222 safely derived aggregate cells, six partial
mappings, and six source blanks: zero violations. Common204 checks 804 mapping
occurrences and 1,608 cells, including 156 derived aggregate cells, four
partial mappings, and four source blanks: zero violations. Derived aggregates
are supported only by complete observed child lanes; no source blank produces
a numeric coefficient.

## Common204/full271 semantic expansion

The receipt
`/dev/shm/f26-bb319-common204-full271-semantic-expansion-receipt-v1.json`
(504,822 bytes; SHA-256
`ad22170dda190cf4a23a385567acac34616c9dce80702e87381802d0e05dd0da`)
proves identical schema outcomes for all 204 shared source PDFs and a
disjoint 67-document/+159-mapping current-corpus expansion.

Of the 204 shared sources, 180 have the same complete document Page-JSON
frontier, 22 have a changed document frontier but an identical Family-26
relevant page axis, and two have an authenticated different selected
Family-26 page frontier: KLB source `e6dba37a…` and EIB source `ff44a84b…`.
For both, status, reasons, candidate count, RNID, role, unit, state, source
text, and numeric coefficients are identical. They are corpus-frontier
differences, not evaluator nondeterminism. Semantic violations: zero.

## Historical strict safety, excluded from the conclusion

The two pinned eight-source historical builders were replayed independently
from their legacy semantic indexes. For both E-0073 and E-0127, the complete
`trials` and `metrics` objects are byte-equal to the pinned artifacts. Each
whole-result comparison has exactly 18 non-semantic differences: 17 fields
under `input_refs.schema_authority` caused by the live authority moving from
`UNIVERSAL_BANK_BCTC_SCHEMA@6074` to `@6076`, plus the result ID that seals
those metadata bytes. Removing only those fields makes each result exactly
equal; semantic violations are zero.

The safety receipt is
`/dev/shm/f26-bb319-historical-strict-safety-receipt-v1.json` (4,236 bytes;
SHA-256
`61f489f89052d855930b31eb3c14f30990df3ad0012f58fec58c9f7eaa0d9448`;
receipt ID
`glicahssv1:receipt:d5315e65f0639956ffc353a82c31ffeb6be3ffad1bb71d5c2f0e98bb0a1f50b0`).
This is a legacy safety projection only. It is not an alternate scope or
comparator conclusion; full271/common204 remain governed exclusively by
`DISJOINT_EXPANSION`.

## Durable diagnostic evidence

- Full sweep: `/dev/shm/f26-bb319-full271-v1/family26.json`
  (55,970,309 bytes; SHA-256
  `fd4db571ae153574e52887b605c9ef603baf7eeea791e8cd5f0377010d5ea4c1`).
- Full coverage: `/dev/shm/f26-bb319-full271-v1/source-row-coverage.json`
  (3,454,408 bytes; SHA-256
  `e1a513bde6a5801481eef745dba894de223cfcbd0478c0ec6d30520e195d2c06`).
- Full PDF-visible audit:
  `/dev/shm/f26-bb319-full271-v1/pdf-visible-source-row-audit.json`
  (2,260,616 bytes; SHA-256
  `10398f0ab0ef13d72c65adc433fabb0d60e811cd6f73f6e53bfff11b80d6face`).
- Common sweep: `/dev/shm/f26-bb319-common204-v1/family26.json`
  (42,600,802 bytes; SHA-256
  `37c77d7dc824806167abf4c2058de45a1960a399576e99868db8058a67bd2218`).
- Common coverage:
  `/dev/shm/f26-bb319-common204-v1/source-row-coverage.json`
  (2,622,473 bytes; SHA-256
  `fdd2c9e662cdb5d0906811406621617fdfa77528c183459ae5a000cb673635f0`).
- Common PDF-visible audit:
  `/dev/shm/f26-bb319-common204-v1/pdf-visible-source-row-audit.json`
  (1,733,716 bytes; SHA-256
  `8513888d4d3799b7b2994397a7397d451556b9b33ecb92994ec9fd2cc08b08ac`).

## Matching-corpus Family-22 ownership handoff

The accepted Family-22 inputs are its v3 sweeps, after Family 22 integrated a
fail-closed source-role no-left-behind gate into its specialized runner:

- full271 sweep `/dev/shm/f22-bb319-full271-v3.json` (60,981,461 bytes;
  SHA-256
  `57cb2d35de68cf366427adfec1358a230304a374191b9bf49d3359c47ea24a41`)
  and audit `/dev/shm/f22-bb319-full271-v3.audit.json` (17,386,659 bytes;
  SHA-256
  `bc2f87efe23a8a959fef9ee5f36e7b12b383a90a85166995c291dc74c640ef6f`);
- common204 sweep `/dev/shm/f22-bb319-common204-v3.json` (46,996,713
  bytes; SHA-256
  `bc7c0576b2429654a34cf5656c7609a261e672894dd4a0cd5df2aa39c015dfb8`)
  and audit `/dev/shm/f22-bb319-common204-v3.audit.json` (13,642,876
  bytes; SHA-256
  `5c0605c4c1619f87214556b120e0e91292abe933a52946bb710d7e72be03d9aa`).

Family 22 is respectively 271/271 and 204/204 READY with zero residuals. Its
new coverage receipts account for 5,501 and 4,271 configured role-hit rows
with zero violations; its source-observation contracts also have zero
violations. The two Family-26 cross-family receipts are:

- full271:
  `/dev/shm/f26-bb319-full271-v1/f22-cross-family-disjointness-receipt-v3.json`
  (971 bytes; SHA-256
  `4bf24d62f5908a352253c48058ebe2f887d9f3be8608bf4217796823bf52474f`;
  receipt ID
  `glicacfdv1:receipt:1451cfece5f0b9cfda587ff8c7b9bb0fb991839bdf990656582b4e7c0930f39d`);
- common204:
  `/dev/shm/f26-bb319-common204-v1/f22-cross-family-disjointness-receipt-v3.json`
  (971 bytes; SHA-256
  `41516487757220bbacaf63110a6ceaebe911369c311d9e045003e2fabf9bc7f4`;
  receipt ID
  `glicacfdv1:receipt:a2031c7dd9e16bf229b402d3d0c64a2d973c108689b59085e344087ed83bf952`).

They bind the exact 271- and 204-source trial axes. Full source-row mapping
axes are Family 22=1,680 and Family 26=631; common axes are 1,320 and 454.
Family 22 emits none of RNIDs 982–986 and both exact
`(source,page,section,table,row,RNID)` intersections are empty.

## Specialized release and store seal

The specialized runner re-evaluated the immutable sources, authenticated the
PDF and historical receipts, enforced both cross-family gates, wrote the
sweep/audit once, replayed every trial again from the stored source-page
database, ingested the result, loaded it back with typed equality, and exited
zero for both corpora.

Full271 release:

- sweep `/dev/shm/f26-bb319-full271-release-v2/family26.json`
  (55,970,309 bytes; SHA-256
  `fd4db571ae153574e52887b605c9ef603baf7eeea791e8cd5f0377010d5ea4c1`;
  sweep ID
  `gjfafsv1:sweep:d8fdace6d5c2d96376129363a00baeefb846bcdfc43d670bc5e3a5c9537056da`);
- audit `/dev/shm/f26-bb319-full271-release-v2/family26.audit.json`
  (3,461,301 bytes; SHA-256
  `5bf281d8c55f390e2dd98b5bd6dcb03b2f09a925b79d9d6a9ee7f241f48a2902`;
  audit ID
  `glicafauditv1:audit:bd8af46fde891faf7628c5f2f082ba9bdabf7798fa916bbda94af09fc1071401`);
- database `/dev/shm/f26-bb319-full271-release-v2/family26.sqlite3`
  (101,445,632 bytes; SHA-256
  `95189d99d8062667b5e6359a0ce93689c3fc8cb79f1a8eeae9486c6d6a178159`;
  family run ID
  `gjfafstorev1:run:7184e113991328848123d11587f0b18a0b0a9b033222cfc563b9bb02f52c6b9e`).

Common204 release:

- sweep `/dev/shm/f26-bb319-common204-release-v1/family26.json`
  (42,600,802 bytes; SHA-256
  `37c77d7dc824806167abf4c2058de45a1960a399576e99868db8058a67bd2218`;
  sweep ID
  `gjfafsv1:sweep:8def987d5575623d1d102a3e68c97671f854e2bf4b0c2cf663962e8eaaaf05e6`);
- audit `/dev/shm/f26-bb319-common204-release-v1/family26.audit.json`
  (2,629,380 bytes; SHA-256
  `3ed345ae8720058a96b6a22d2711e8b1999339746386204b66ff7353fe9965f5`;
  audit ID
  `glicafauditv1:audit:45218cfeec71b65dc58dd69656e2e2a17e4506179c9762229b22acd647b9f761`);
- database `/dev/shm/f26-bb319-common204-release-v1/family26.sqlite3`
  (77,082,624 bytes; SHA-256
  `71aef25d42b9bad1cc97fd8010ea8cb114548f6c413adf5f2195aaae83f3f468`;
  family run ID
  `gjfafstorev1:run:89b98246b36e583b606f274cb85af2c27a5b6148295204ddd6659b1574354b59`).

Both SQLite databases pass `quick_check` and `integrity_check`; both foreign
key checks are empty. Release sweeps are byte-identical to their diagnostic
sweeps. The machine-readable release manifest is
`/dev/shm/f26-bb319-release-manifest-v1.json` (10,751 bytes; SHA-256
`9da953eb3ade56f9da84e2144d63b52a8b48a049f52b854eb8f32be3dc548a4f`;
manifest ID
`glicarmv1:manifest:d64b6963ce33a84f6a7e4ef40a8209a6effb80babcec000be462140b84580d81`).

## Verification and implementation hashes

- Family-26 evaluator, specialized runner, and shared source-observation
  contract suites: 52 passed.
- Ruff on the Family-26 evaluator, runner, and both test files: pass.
- `py_compile` on the evaluator and runner: pass.
- Whitespace/diff checks over every Family-26 owned path: pass.

Terminal implementation SHA-256 values:

| Path | SHA-256 |
|---|---|
| `config/families/tm-loan-interest-accrual-classification-topology-v1.json` | `13b2684c84e0c52b87e0bc8c5661b0b8f85993dd165d06699583be37e65349c8` |
| `config/families/tm-loan-interest-accrual-classification-evaluation-v1.json` | `34d65e882950648b8b52e6e5453583ad1de307c1bfd7e94cd389d50806c74456` |
| `config/families/tm-loan-interest-accrual-classification-schema-binding-v1.json` | `dd5e902af44dcad757cdeb373fa4d6efd409a8b85dc4750d21479d972153af9f` |
| `config/families/tm-loan-interest-accrual-classification-pdf-residual-audit-v1.json` | `3324d9635e23a3a99907f9aea30990962d92feba1a1a107f3d089a7ed13b5cc0` |
| `config/families/tm-loan-interest-accrual-classification-common204-pdf-residual-audit-v1.json` | `2f9a9c6e05289d86262c3eb69168198a9a0daf2bdf1de49d0638dc1b91fdc0dd` |
| `src/bctc_ai/evaluation/gemini_json_loan_interest_accrual_classification_family_v1.py` | `85b12cbb66d66dc19f9a908adabf27c9f1ec0f47e498b51b4a1283f160c96db2` |
| `scripts/experiments/run_gemini_json_loan_interest_accrual_classification_accounting_family_v1.py` | `b5eaf8810d9cf72dc2dfa05fe79671c8eb517559031773093b53d332cec6fde6` |
| `tests/unit/test_gemini_json_loan_interest_accrual_classification_family_v1.py` | `0d75ef0a67c9ab53403c30c9f21e4200255ac9b5658b9a9fdbd7b86be05c38da` |
| `tests/unit/test_run_gemini_json_loan_interest_accrual_classification_accounting_family_v1.py` | `0e067fb16183cd8229806b5dedaec17fc8d451bfa43f1a6f15c7db0c77b0fa24` |
| shared multitable evaluator | `bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2` |
| shared generic runner | `d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5` |

## Conclusion

Every full271/common204 document is classified, every Family-26 target-like
selected-JSON row is typed, and every bound PDF-visible row is represented or
explicitly disposed. There are zero NOT_OBSERVED documents, zero UNRESOLVED
documents, zero source-observation violations, zero uncovered source rows,
zero uncovered PDF-visible rows, and zero Family-22 overlaps. No visible,
schema-mappable Family-26 row is left behind.
