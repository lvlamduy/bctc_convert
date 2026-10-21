# F39 original table basis checkpoint 2026-10-21

Verified implementation checkpoint, not F39 acceptance. Parent commit:
`34b77002ea55ebfcb50123c0f89f6a06e4c4620a`; branch:
`codex/f39-income-tax-laptop`; migration ancestor:
`8efd618b6c77f0cdbb402a440e7ba3b3549184f1`.
LAPTOP_INTEGRATOR continues F39 only. Production scope remains 2025 onward;
2024 source documents remain excluded. No provider calls, re-extraction,
source-database writes, artifact deletion, F36/F37/F41 edits, common-branch
pushes, or migration-manifest changes accompany this checkpoint.

## Original table evaluation

The F39 compiler now creates two separately authenticated private spec triplets:

- RATE exports only PBT5728, current tax5723 and prior adjustment5733. Other
  roles remain validation-only. Original ordered scopes remain; the
  source-only-to-income projection is disabled only for this tax-effect basis.
- INCOME exports PBT5728, non-taxable income5729, non-deductible expense5730
  and taxable income5731. Both original ordered scopes and the original
  source-only-to-non-taxable-income projection remain active.

Both have structural-only roots, with no invented tax-root mapping. Other
accounting, duplicate, query, period and unit policies are unchanged. The exact
full CURRENT label and two prior-tax labels are additional RATE-private aliases,
not changes to the base or supplemental topology. Cached raw specs must compile
back to the authoritative normalized base before private specs can be used.

`build_gemini_json_income_tax_original_basis_receipt_v1` independently evaluates
one complete original table. Cells, headers, row kinds, hierarchy, units and row
order are unchanged. The identity view binds every original row and column;
private query/classification/candidate proofs retain their private namespace.
Original document owner-fenced query membership, original section scope,
narrative reset boundaries, source periods and selected-page hashes remain
separate evidence. A neutral continuation caption is not required to repeat the
tax owner; it still needs original owner-fenced membership. Narrowing a section
cannot create sole-table narrative authority.

The receipt accounts for every raw row, including source-only, equation,
non-money, blank and unmatched subtotal rows. Retaining a numeric subtotal as
source-only is not value-level closure proof. Such an unproved subtotal stays
an explicit algorithm hold. Only complete exact-equation statuses can supply
equation proof. Metric retention binds the exact table, raw row, classification
role, source order and declared metric policy.

All schema roles get raw-cell/coefficient/source-text checks. A blank cannot
become numeric zero. Printed zero remains numeric zero. The existing operating
contract explicitly permits a visible accounting dash as zero with its exact
raw string and typed `DASH_ZERO` state retained; a layout continuation marker
does not gain this permission. This corrects an overly restrictive early
implementation that treated every dash as an unresolved numeric observation.
Entity and report-scope ancestors on validation-only rows are retained and
unproved participant scope crossings remain holds.

`validate_gemini_json_income_tax_original_basis_receipt_v1` rebuilds the entire
receipt from the supplied original records and compares typed content. Changing
values, locators, private specs, coverage, scope or acceptance flags and merely
recomputing hashes cannot authenticate a forged receipt.

## Verification

Final focused run on Python3.12.3, `-B`, fresh isolated bytecode prefix:
**612/612 PASS**, zero failures/errors/skips,42 actual checkout imports,
123.61s. Source/config/test bytes and checkout identity were unchanged during
execution. This includes59 new original-basis cases. Ruff and `git diff --check`
also pass. Earlier failed583-test development output and intermediate603/612
receipts are retained, not substituted for the final-byte evidence.

Focused receipt:
`/srv/bctc-receipts/f39-original-basis-final-focused-1792565873253-46826332e2c948/F39_IMPLEMENTATION_FOCUSED_RECEIPT.json`

SHA `cdfa4cb696ec0f266d9633047c802c30155da4d40ac8229417b0d1a65e085aba`;
604631 bytes.

Independent original-SQLite receipt rebuild covers full271 ordinals
`1,193,260,261,262,264`. Every complete receipt rebuild equals the first build;
all original JSON and source SQLite bytes/identity remain unchanged. The
immutable index SHA is
`969ff5f80732c39e4b7543ca1f5c1e5b5b827260f19981ed02945fe0c7379219`;
source database SHA is
`ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7`,
573145088 bytes.

| Original document | Private table evidence | Remaining typed gap |
| --- | --- | --- |
| ABB1 | PASS | No local coverage gap; cross-population integration still required |
| STB193 | PASS | No local coverage gap; independent YEAR population must remain |
| VBB260 | ALGORITHM_HOLD | Unproved numeric subtotal r7 |
| VBB261 | ALGORITHM_HOLD | Unproved numeric subtotals r7 and r9 |
| VBB262 | ALGORITHM_HOLD | Unproved numeric subtotal r7 |
| VBB264 | PASS | No local coverage gap; period/population integration still required |

These are private table-evidence dispositions, not new production READY counts.
All six private shared-engine candidates were READY, demonstrating why generic
READY alone cannot replace exhaustive row accounting. The extra subtotal holds
are unfinished algorithms, not genuine-source-conflict terminal seals.

Six-source receipt:
`/srv/bctc-receipts/f39-original-basis-final-panel-1792566043839-89a61f50878018/F39_ORIGINAL_BASIS_SIX_SOURCE_REPLAY.json`

SHA `564bbd832437be6f4a4326c98d7280131213e657bcc17ce4b8b78a2cdcb7586a`;
2300667 bytes. Verifier helper SHA:
`55ae8f1b3f80813e64a70325828b183c8907934b4cff5a4c2751fd3805d771cf`.

Implementation pins:

- F39 module `17643b4c4b35f4ad63cccaa88e2ccabf027f2e789ee1722ca6e6af054f9b2e52`.
- F39 family tests `86287456433946265e5c2be0424de631cfd831ea6c351593a1d3ae964eb6ba10`.
- Frozen evaluator unchanged `bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2`.
- Frozen runner unchanged `d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5`.

## Required production continuation

The original-basis receipt explicitly has `production_adapter_integrated=false`
and `family_terminal_claimed=false`. It is not yet the outer production query
adapter. The existing production route and its legacy exact-key adapter remain
unchanged. Do not promote private mappings directly to Excel or accepted storage.

Next, add the distinct strict original-note adapter/public-replay path, preserving
original outer source regions. Independently prove period/entity/basis
correspondence for RATE, genuine INCOME, YEAR/PERIOD and deferred/root populations;
merge those NOTE populations before comparison with genuine PRIMARY. Preserve
equivalent controls without adding them twice, and do not seed output from a
rejected generic candidate. Complete the business-tax/transfer-tax subtotal
mechanism rather than waiving its source-coverage holds.

Current-code full271/common204, persistence/source replay, observation contract,
SQLite integrity, PDF/residual audits and release ledger remain required before
F39 terminal status. F36 then F37 remain next; F41 is not open. Publish these
witnesses only under new immutable keys with exact VersionId readback. Report
this checkpoint with HEARTBEAT, not READY_FOR_INTEGRATION.
