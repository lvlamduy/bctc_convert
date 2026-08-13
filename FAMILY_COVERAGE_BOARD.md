# Family Coverage Board

Standing authority: [`PROJECT_OPERATING_DIRECTIVE.md`](PROJECT_OPERATING_DIRECTIVE.md),
especially §35. This is an execution ledger, not a strategy document. Research
occurrence, expected replay outcome, accepted source structure, and canonical
mapping are deliberately separate denominators.

Updated: 2026-08-13 (UTC)

## Denominator rules

- `Inspected` counts only source-visible cross-bank research cases with pixels and
  authenticated text/geometry reviewed; it is not accepted coverage.
- `Present` counts source occurrences in the reviewed denominator, not all Wave-1
  banks unless the whole 27-bank denominator was screened.
- `Accepted` is populated only by the bounded Generic Local Accounting Graph run
  over exact Source Evidence Projection V2 evidence.
- `UNRESOLVED` preserves source cases that fail the strict acceptance subset.
- `N/M` means not measured; it is not equivalent to zero.
- Schema/value columns remain zero until an accepted source graph is mapped and
  validated. Candidate counts never enter accepted columns.
- Panel-bank slots are reported when historical panels do not prove a deduplicated
  whole-Wave-1 bank denominator.

## Current board

| Family | Maturity / execution state | Banks inspected | Banks with source occurrence | Accepted banks | Unresolved banks | Accepted TABLE | Accepted LOGICAL_ROW | Accepted VALUE_POSITION | Accepted AXIS | Accepted HIERARCHY | Schema mapped rows | New-ID proposals | Aliases | Unresolved schema gaps | Validated value axes |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `LOAN_QUALITY_CLASSIFICATION` | `READY_FOR_BOUNDED_ACCEPTANCE`; typed proposals measured, exact real topology still zero | 8 exact-gate banks | 8 exact-gate banks | 0 | N/M | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | N/M | 0 |
| `LOAN_MATURITY_BUCKETS` | `CROSS_BANK_SUPPORTED`; development acceptance candidate, typed proposals measured, exact real topology still zero | 8 exact-gate banks | 5 exact-gate banks | 0 | N/M | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | N/M | 0 |
| `CUSTOMER_LOAN_BORROWER_OR_ECONOMIC_SECTOR_BREAKDOWN` | `CROSS_BANK_SUPPORTED`; family-sweep candidate | 8 whole documents / 30 locked regions | 5 banks / 9 positive regions | 0 | N/M | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | N/M | 0 |
| `PROVISION_MOVEMENT_ROLLFORWARD` | `CROSS_BANK_SUPPORTED`; likely first post-LAG sweep entry | 9 evaluated bank-panel slots | 9 positive logical slots | 0 | N/M | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | N/M | 0 |
| `LIQUIDITY_RISK_MATURITY_GAP` | `CROSS_BANK_SUPPORTED`, core continuation/topology not mature | 15 documents / 24 locked pages | 8 banks / 10 positive pages | 0 | N/M | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | N/M | 0 |
| `UNIT_SCOPE_EDGE` | `HYPOTHESIS`; value extraction supported on selected panels, ownership inheritance unresolved | 15 panel-bank slots | 36 positive region slots across two panels | 0 | N/M | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | N/M | 0 |
| `TABLE_OR_NOTE_CONTINUATION` | `HYPOTHESIS`; no generic accepted continuation edge | 7 banks / 24-page TM panel plus statement-boundary panels | not a family-presence denominator | 0 | N/M | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | N/M | 0 |

The LAG v1 core contract itself is now mechanically closed for the first two
configs: exact OCR and native V2 acceptance paths, a matched source hard control,
rotation-aware geometry, spanning-header corroboration, content identities, full
edge/evidence provenance, explicit-unresolved retention, and deterministic replay
are covered by the focused gate. This does **not** promote any real Wave-1 case;
the authenticated typed-proposal seam is implemented, and its exact 29-case replay
is now the measured blocker before bounded observation assembly.
Independent strict audit of the bounded core/output/replay contract is `PASS`.

## Current LAG v1 Tier-1 gate

The exact development/replay denominator contains 29 real regions:

| Family | Cases | OCR | Native | Expected strict ACCEPT | Expected REJECT controls | Expected UNRESOLVED variants | Authority status |
|---|---:|---:|---:|---:|---:|---:|---|
| `LOAN_QUALITY_CLASSIFICATION` | 14 | 14 | 0 | 6 | 6 | 2 | Durable prospective/development authorities available |
| `LOAN_MATURITY_BUCKETS` | 15 | 12 | 3 | 5 | 10 | 0 | Development replay; historical hard-panel lock is not independently durable enough for a prospective claim |
| **Total** | **29** | **26** | **3** | **11** | **16** | **2** | Exact core acceptance not reached; see measured builder gate below |

Expected dispositions are evaluation targets, not accepted counts. The engine must
bind every cited atom to an exact validated V2 projection and remain fail-closed on
inherited unit/scope, ambiguous axes, multiple complete regions, arithmetic
contradiction, or malformed evidence.

### Measured proposal and observation gate

The replay-authenticated typed-proposal sweep compiled the two-family registry once,
then scanned each of the 29 exact pages once. Across 2,681 authenticated primary
LINEs it emitted 33 exact semantic proposals, 41 unresolved repair proposals and
9 topology candidates. All 9 topology candidates remain unresolved; exact ordered
topology is 0. The bounded matcher made 102 edit-distance evaluations, visited
71,573 precompiled q-gram postings, retained fuzzy candidate fanout 100 in total
(maximum 41) and hit neither posting-work nor fanout overflow. There was no hidden
family×line Cartesian evaluation. Post-freeze diagnostics find a target-family
topology candidate in 4/11 expected-positive cases and 0/16 controls, but none can
authorize a LAG observation. Therefore LAG invocation and every accepted/mapped
column remain zero.

The first source-only compatibility audit produced **29/29 `NO_OBSERVATION` and
0/29 core invocations**. These are builder/proposal gaps, not graph dispositions:
the role groups in the compact fixture bind real V2 atom IDs, but they do not have
an authenticated proposal-set envelope, generator/config identity, family-spec
binding, candidate-completeness scope, typed structural relations, or an ambiguity
receipt. In the 11 nominal positive cases, exact OCR text supplies a complete set
of core-recognized row labels in 0/11 and a core-recognized branch in only 1/11.
No expected label was used to repair source text or create an accepted graph.

Overlapping diagnostic gap archetypes are: ordered-row/core-semantic evidence 29,
owner proposal 7, branch proposal 5, dated-axis proposal 1, value proposal 1, and
total/adjacency proposal 1. The generic source-bound typed proposal contract is now
implemented; its measured remaining blocker is exact semantic/topology recall from
real OCR evidence, not a reason to add case aliases or one parser per family.

## Reusable primitive ledger

| Primitive | Current evidence state | Production action |
|---|---|---|
| `OWNER_RESOLUTION` | Repeats across quality, maturity, borrower/sector, provision, liquidity controls | LAG v1 core; exact local owner only in first accepted subset |
| `PARENT_CHILD_EDGE` | Repeats across all mature families | LAG v1 core |
| `ORDERED_SIBLING_SET` | Strong quality and maturity support | LAG v1 core |
| `AXIS_ROLE` / `COMPARATIVE_PERIOD_AXIS` | Strong for two-period monetary tables; percent/maturity axes are hard controls | LAG v1 core, fail closed on ambiguous headers |
| `UNIT_SCOPE_EDGE` | Local explicit units supported; inherited defaults not mature | Accept local exact unit only; preserve inheritance as unresolved |
| `TOTAL_SUBTOTAL` / internal additive closure | Strong across quality, maturity, borrower/sector; arithmetic corroborates or vetoes | LAG v1 core; never select structure by arithmetic |
| `SAME_POPULATION_CLOSURE` | Research evidence is strong, but current observations do not bind the external owner/population balance | Not claimed by LAG v1; require typed owner-value anchors on the same axes/unit before promotion |
| `OPTIONAL_CHILD` | Margin/advance variants observed in customer-loan quality | LAG v1 configuration, included in internal additive closure when present; no same-population claim |
| `MOVEMENT_ROLLFORWARD` | Provision panels support it across banks/layouts | Candidate primitive for first breadth-sweep entry |
| `NEIGHBOR_RELATION` | Repeats across mature panels | Evidence/configuration support; not a standalone acceptance authority |
| `TABLE_CONTINUATION` / `ROW_FRONTIER` / `STRUCTURAL_RESET` | Useful but not yet generic-acceptance mature | Keep unresolved; do not reopen Reader V3 |

## Queue governed by this board

1. Keep the independently audited bounded LAG v1 graph/output contract closed.
2. Close the measured exact-topology gap using source-bound semantic evidence;
   preserve all OCR repairs as unresolved and do not tune from expected labels.
3. Assemble and replay only exact, authenticated observations; then record actual
   accepted/unresolved structural counts and control deltas.
4. Map the strict accepted subset immediately; leave inherited context unresolved.
5. Select the first breadth-sweep family by prevalence × importance × evidence ×
   primitive reuse × expected coverage gain; current evidence favors provision
   movement or borrower/sector, subject to a short source review.
6. Move to the next family once the strict subset is accepted and mapped; cluster
   residual variants after a meaningful breadth sweep.

## Scaling envelope for many TM clusters

- Project exact source atoms and local geometry once per page; do not rebuild the
  page for every accounting family.
- Generate one authenticated typed proposal set with explicit completeness and
  ambiguity accounting, then shortlist family specs using source-visible anchors.
- Run the same graph primitives over shortlisted, versioned family configs. Do not
  evaluate every family against every page and do not add bank/page routing.
- Keep rare or weak variants unresolved. A new family should normally add config;
  engine code changes only when cross-family evidence proves a missing primitive.
- The proposal compiler accepts a versioned multi-family registry payload with
  collision accounting, compiles it once per sweep and uses a bounded q-gram index.
  Common exact labels are compact until a source-order local owner/branch frontier
  exists; a corroborated owner+branch transition resets the frontier, while owner
  text alone does not. Exact/fuzzy/contextual match work is literally bounded and
  cross-family identical visible traces remain unresolved.
- An ephemeral read-only independent scale audit (not yet a durable repository
  benchmark receipt) is `PASS/TRUST`: a 1,000-family registry with 100 complete
  local blocks produced 100 exact topology candidates, 400 materialized match claims
  and 600 topology visits. Common-only pages caused zero contextual expansion. This
  is candidate-generation evidence, not accepted coverage.
  The LAG acceptance authority remains intentionally frozen to two specs. Before
  breadth grows, persist proposal specs in an authenticated/versioned data registry
  rather than adding hundreds of constants or family-specific parser branches.

Family sweep status: **NOT STARTED**. Contract reuse and candidate scaling are proven
on two configs; real-source acceptance is not. The immediate instruction requires
real accepted structure before moving on.
