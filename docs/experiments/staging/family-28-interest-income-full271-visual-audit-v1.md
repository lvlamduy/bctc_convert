# Family 28 interest income full271 visual-audit ledger v1

This staging ledger records the provider-free source/PDF audit and replay for
`INTEREST_INCOME`. It authorizes neither schema export nor production
publication.

## Immutable scope and baseline

- Current corpus index:
  `/dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts/current-corpus-manifest-indexes/8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a.json`.
  Its file SHA256 is
  `969ff5f80732c39e4b7543ca1f5c1e5b5b827260f19981ed02945fe0c7379219`.
- Authenticated page store:
  `/dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts/current-corpus-freeze-inputs/store-ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7.sqlite3`.
  Its SHA256 is
  `ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7`.
- Population: `271` source PDFs and `14,945` selected page JSON versions, all
  within the current reporting scope. No provider call or re-extraction was
  made.
- Baseline `/dev/shm/family28-full271-baseline-root-v1.json` was
  `187 READY / 1 NOT_OBSERVED / 83 UNRESOLVED`, with `1,056` mappings;
  SHA256
  `b116cc00e616114bf0b8a66f5ce449244248229a7dc266d365d6cdd29a9257aa`.

All 84 non-ready source PDFs were inspected at their exact candidate pages.
Every one contains a visible interest-income presentation whose observed
schema roles are mappable; therefore no baseline negative or unresolved
disposition is accepted as final. The baseline reason inventory was:

- `62` missing source-visible root proofs;
- `22` securities parent/detail representation mismatches;
- `21` locally unusable period or unit axes;
- `14` unclassified direct family money rows;
- `7` unresolved owner clusters; and
- `1` malformed visible money token.

The 84-document visual population by bank is `ABB 11, BAB 2, BVB 3, EIB 7,
KLB 14, LPB 2, OCB 16, PGB 3, STB 8, TCB 1, VAB 14, VBB 3`.
The exact 84-document selected-source table inventory is
`/dev/shm/f28-residual-source-tables-v1.json`, SHA256
`e7652d2c5fc94d009e350a061b67435394d5a45c19c4758ea2d21e87fa83e29d`;
it binds each disposition to its source/page/section/table evidence rather than
to a bank-specific routing rule.

## Evidence-bounded remediation

The remediations are structural and schema-driven, never filename/bank/page
routing:

- Declarative aliases and the schema's single securities-income leaf handle
  34 documents. A printed securities aggregate maps RNID `1146`; its visible
  trading/investment breakdown remains equation-consumed source evidence and
  is not double-mapped to the same RNID.
- Exact governed duration headers handle ordinals `61, 62`. Only the shared
  parent phrase `Luỹ kế từ đầu năm đến cuối kỳ này` is removed, and only when
  the two leaves are exactly `Năm nay` and `Năm trước`.
- Unitless note tables bind only when their visible total, or a complete
  shallow declared component frontier, equals a primary-statement
  interest-income row under exactly one canonical public unit. This produces
  replayable unit receipts; magnitude alone is never evidence.
- The explicit adjacent continuation at VBB ordinal `259`, physical pages
  `19 -> 20`, is one table population. The second page contains securities
  detail, guarantee fee, finance-lease interest, other credit income and the
  printed total; acceptance may not stop at the first-page fragment.
- STB ordinal `202`, physical pages `35 -> 36`, and VBB ordinal `259`, pages
  `19 -> 20`, both print a terminal colon-labelled securities parent followed
  by two leading same-role detail rows. In each document those details sum to
  the parent on every observed lane. The shared opt-in rule consumes the detail
  rows as proof-only evidence and emits exactly one source mapping from the
  printed parent. Its receipt binds both fragment locators, the lane and unit
  axes, parent/detail ordinals and the exact equation. A missing lane,
  mismatch, non-terminal parent or non-adjacent fragment remains unresolved.
- `Trong đó: Phí liên quan đến tín dụng` is a non-additive source-only
  disclosure below mapped other credit income. The schema has no separate
  leaf for it, so it is retained in closure evidence and never double-counted.

True source blanks remain `BLANK_SOURCE_CELL` with coefficient `null`; an
all-blank role is omitted. Neither equations nor source totals may fabricate
zero. A printed dash is zero only after exact PDF-authenticated transcription.

## Registered PDF-visible dash transcription

The registered artifact is
`data/registered/gemini_json_interest_income_source_repairs_v1.json`, SHA256
`f27de33d2beaba6a4842be54e10b49016b22cbacf8906e50ffeb20463de26d5d`,
overlay ID
`gjiifav1:overlay:21656d44f523f1271654aa18e59cede64babef968928529d6e4221b710a274bd`.
It binds 30 exact source PDFs/pages/tables and 64 cells: 60 selected-JSON nulls,
one malformed dash token and three values transcribed onto cells that visibly
contain a dash. Every replacement is the literal printed `-`; there is no
numeric repair or equation backsolve.

The runner byte-authenticates each source PDF and re-renders all 30 physical
pages at 300 DPI RGB. The complete page dimensions, PNG byte sizes and SHA256
values must match the registered evidence. The current independent replay of
that render axis is `30/30 PASS`, covering all `64` cells.

## Acceptance result

The terminal replay used the frozen shared evaluator
`bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2`
and generic runner
`d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5`.
It completed with `271 READY / 0 NOT_OBSERVED / 0 UNRESOLVED` and `1,775`
mappings. The output is
`/dev/shm/f28-acceptance-bb319.psXwrU/family28.json`, SHA256
`410543ade3548f22dd97d81d18041cf1b192d7ac973edcb321c80cc7816a76bd`;
its sweep ID is
`gjfafsv1:sweep:e16089681cc26291c416c14951f411efa9ff7459b357d3f01db2f86886458e6c`.

The audit is
`/dev/shm/f28-acceptance-bb319.psXwrU/family28.audit.json`, SHA256
`ce8adc9b43c753260a5f43dfd1cd47e4a19c247f63da90412fdf28debb1956e4`,
audit ID
`gjiifauditv1:audit:c2f26855e7422976c26e3eb1b37c3042da2a05888d58ae74a873a9003ea2caab`.
Its authenticated axes are `271` trials, `1,775` mappings, `351` equations,
`30` source repairs, `58` unit-corroboration receipts, `2` governed duration
normalizations, `2` cross-fragment same-role equations, `1` one-sided
continuation and `1` query recovery. All `30` expected repair IDs were applied
exactly once. The source-observation contract inspected `3,550` duplicate
mapping occurrences and `7,100` cells, including `4` partial mappings with `4`
typed source-blank cells, and reported `0` violations.

The result store is
`/dev/shm/f28-acceptance-bb319.psXwrU/results.sqlite3`, SHA256
`23dabc58e9cb40c2efb806719cb478b470e5dfa2a040af33060ed68fd55f6f00`;
`PRAGMA quick_check` returned `ok` and `foreign_key_check` returned no rows.
The stored run ID is
`gjfafstorev1:run:51a48387cfa5eb7e68ec4a2b3c3a88a59f880624b491ca3644b8930b999d0635`.
The ingest path regenerated every trial from the authenticated source page
store and required exact typed equality with the stored sweep before export.
The historical policy authenticated both 8-bank oracle artifacts (`16`
sources total) and proved their source axis disjoint from all `271` current
sources (`overlap_count=0`); no historical value was silently compared across
different source documents.

Final owned hashes are: topology `4d00e5f8...aa6a1c`, evaluation
`5db5f532...14ade`, schema binding `9d8df934...a0696`, registered repairs
`f27de33d...6d5d`, adapter `a1260264...a45f2`, runner
`e721a18f...dbbe`, evaluator tests `519fa76a...40c2` and runner tests
`91f63a16...3e99`. The final focused suite passed `26/26`; Python compilation,
JSON parsing, Ruff and scoped diff-check also passed.
