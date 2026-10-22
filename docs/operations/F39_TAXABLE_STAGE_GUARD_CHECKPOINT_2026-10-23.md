# F39 taxable-stage guard checkpoint - not a family seal

Scope remains bank reports from 2025 through current. Standalone 2024 is
excluded; printed comparative columns inside in-scope reports remain evidence.
Only F39 is claimed. F36/F37 and the shared files are unchanged; F41 is closed.
Work stays on `codex/f39-income-tax-laptop`, never the common branch.

## Finite correction

The original KLB report (FULL ordinal 66, physical page 35) prints two distinct
taxable-income stages with an explicit exempt-income adjustment between them.
Copying the first stage faithfully does not establish its ownership of schema
RNID 5731. Neither equations, equal amounts nor row order grants that ownership.

Existing review authorities, unchanged:

- Semantic hold receipt SHA:
  `24fced92a7f23193550f2090454d945b5b9ba16b54461be2cb301ef9f9e8732c`.
- Fresh original-PDF visual review receipt SHA:
  `3017e0cd13da1826fa6023da107d59ceb978efb3bf296d7cbd47a994b8667e8e`.
- Original PDF SHA:
  `91a030b2dcf82adee0ef5db4ef924f24287d08d72e9ec16ee116e5539c2c0f50`.
- The seven-table lexical inventory receipt SHA is
  `66da79c7529ea7450fbff8077b71afaf8a38a0464497e8b8ec3cb6a6cba68e0a`.
  Six have this exempt-between signature. The seventh, adjacent/equal stages,
  is outside this narrow guard; NOT_APPLICABLE does not certify semantic safety.

The family-local control inventories declared literal taxable-income aliases
before consumed-row suppression. Distinct stage labels on the same exact
printed ancestry, separated by explicit exempt/non-taxable income without a
declared reset/negative frontier, produce ALGORITHM_HOLD. Final READY sealing
returns `ALGORITHM_TAXABLE_INCOME_STAGE_BASIS_AMBIGUITY`, zero final mappings.
The final gate also covers PRIMARY fallback and merged/original-note routes.
This is algorithm/schema-basis ambiguity, not a claimed issuer/source conflict.

The control does not select the first/last stage, change values, infer units,
grant periods/scope or turn blanks into zero. Ordinals explicitly belong to
the input table, not automatically to the pre-repair original table. Existing
source-context replay retains the full source row axis. Only held controls
hash/copy their matched evidence; other tables do not gain duplicate full rows.

## Verified implementation snapshot

Python 3.12.3, `-B`, fresh isolated bytecode prefix:

`/srv/bctc-receipts/f39-taxable-stage-final-focused-1792705206007/F39_TAXABLE_STAGE_FOCUSED_RECEIPT.json`

- Receipt SHA `9cc3d087122826a385450f61de740ce5850b6fef05460838dfcec10eb2d920cd`,
  629,847 bytes; 479 collected/executed cases, all PASS, no failures/errors/skips.
- JUnit SHA `8814b6763692efb7611be0c4f1b38afc7504b8b9099bab556c0ac0958b0ef63c`,
  92,070 bytes; pytest elapsed 452.57 seconds.
- All 1,873 witnessed source/config/test/helper files and Git state stayed
  unchanged across execution. Three changed Python files passed py_compile.
- New public cases cover NOTE, merged, genuine rejected-NOTE to PRIMARY
  fallback, ownerless required-role selection, cache enabled/disabled, blank/
  dash, fresh replay of self-resealed forged controls and same-ID source drift.
- Full source-context and document-period-cache suites, related original-note/
  original-basis cases, all five shared suites required by migration section
  9.4, and runner warm/cold SQLite and forged-census regressions were executed.
- Ruff on the three changed Python files and `git diff --check` passed.

The tested HEAD was `61bc42000390207fac4eaffa3ab03656a4504dd9` plus exactly the
three owned implementation/test edits recorded in the receipt. A descendant
checkpoint commits those exact bytes plus this document; it does not rewrite
the tested parent or claim that a clean parent contained the new code.

Current SHA-256 pins:

- F39 evaluator: `177521586f3ff794e06345e2df5bd996a99d615939f0980940450b43692522e6`.
- New public tests: `7eeb5f60dfe324289dc3af16576a3018a2024705962e1ff79cbe26c7d75c69df`.
- Cache tests: `411487c7c409b083e695f7175eb7799339d52df22d7a5269d8212b72e15a1bad`.
- Frozen shared evaluator:
  `bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2`.
- Frozen generic runner:
  `d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5`.

Earlier failed fixture attempts are retained, not promoted. They exposed two
incorrect test assumptions: query READY is not final mapping usability, and
QUERY_EVIDENCE_ONLY permits missing roles. The corrected synthetic fallback
uses an explicit unreadable numeric token, executes the real shared NOTE
evaluator to prove rejection, then verifies the exact DIRECT_PRIMARY strategy.
No real source PDF/JSON/database value was edited. The earlier 2,932-case
28-suite PASS is historical evidence, not a claim that all 28 reran here.

## Interrupted old diagnostic and next bounded work

The old-code full run at
`/srv/bctc-receipts/f39-full271-caption-outline-1792700717169703922`
was deliberately interrupted because this semantic correction was required,
not because an observation timed out. Child exit 130; all owned processes were
confirmed terminal before mutation. No partial artifact was deleted/reused.

- Stop-request receipt SHA:
  `e324edcdff6825f71b37fa91e8044e21fef918906b019741223cee17b47eda89`.
- Execution-result SHA:
  `61d2bbe61597777952debbf8cb27634b8418aaf3bb4793a2af59f49c3bcec454`;
  source refs unchanged and before/after Poppler ELF runtime equal.

Next: push/verify this checkpoint, run the official corrected full271 then
common204 sequentially into fresh outputs/stores. Each already performs
independent cold source replay and exact SQLite reload; do not add a redundant
bounded cold run. Then audit actual final selected cells, all residuals and
full/common projection, authenticate the F39 closeout review, and write the
family ledger. The runner's diagnostic success is not a terminal acceptance.

Close the strictly supported core with an explicit algorithm-variant backlog,
as required by operating directive 35.2/35.6/35.7. Do not chase U=0, rename an
algorithm gap issuer conflict, certify unreviewed absence or export unsupported
values. After terminal F39 continue F36, then F37; no F41 before all three close.

No provider, credential read, source mutation, artifact cleanup or S3 overwrite
occurred. New external receipts/tools are local until separately published;
this document does not claim their S3 backup or completed corpus acceptance.
