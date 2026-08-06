# Ordered SchemaGraph mapping

This is the design contract for the fallback mapper used when independent
row-by-row ranking cannot safely resolve a PDF block. It is deliberately a
cluster mechanism: extra visible PDF rows may remain unmatched, schema rows may
remain unobserved, and no row is mapped merely to make the two sides rectangular.

## Research basis and design choice

- Needleman and Wunsch represent all order-preserving comparisons as paths
  through a two-dimensional array and avoid enumerating every interrupted
  sequence. That is the basis for explicit PDF-row and schema-row gap operations
  in this implementation: [original 1970 paper and DOI](https://doi.org/10.1016/0022-2836(70)90057-4).
- Zhang and Shasha formalize edit operations on ordered labelled trees. Their
  work supports representing hierarchy as structure rather than flattening it
  into labels: [SIAM Journal on Computing paper](https://doi.org/10.1137/0218082).
- Cupid combines linguistic and structural schema evidence and makes mappings
  context-dependent on ancestors and siblings. That directly motivates the
  parent, section and sibling features used here:
  [VLDB 2001 paper](https://www.vldb.org/conf/2001/P049.pdf).
- Similarity Flooding formalizes the intuition that adjacent graph nodes
  corroborate each other, while still returning candidate mappings for
  filtering/review. We use only bounded, explainable neighbor bonuses; no
  unconstrained similarity propagation can override a verified structural
  conflict: [ICDE 2002 paper](https://dbs.uni-leipzig.de/files/research/publications/2002-1/pdf/icde2002-sf.pdf).

The full graph-edit problem is unnecessary for the primary search axis here.
Financial-statement templates have an authoritative workbook order, and visible
PDF rows have a physical reading order. The implementation therefore uses a
k-best monotone dynamic program with a bounded beam at each DP cell, while
checking parent/section graph relations during match transitions. This preserves
the useful hierarchy evidence without discarding the stronger order invariant.

## SchemaGraph contract

`build_schema_graph()` creates one immutable ordered graph per statement. Each
node retains:

- canonical and normalized labels plus controlled aliases;
- statement type, permitted scope and LCTT branch;
- parent, children, hierarchy level and root-to-node section path;
- previous and next workbook nodes; and
- zero-based workbook `display_order`.

The builder rejects duplicate IDs, duplicate display positions, missing parents,
cycles and neighbor edges that disagree with workbook order. `ReportNormId` is
never sorted numerically. For example, `4337 → 4373 → 4338` remains valid because
that is its workbook order.

## Search state and operations

For a PDF prefix of length `i` and schema-cluster prefix of length `j`, each DP
cell retains at most `B` distinct mapping signatures. A transition is one of:

1. `MATCH`: map PDF row `i` to schema node `j`;
2. `SKIP_PDF_ROW`: retain an extra visible PDF row without forcing a mapping;
3. `SKIP_SCHEMA_ROW`: retain a schema node without fabricating a visible row.

Mapping signatures are deduplicated, so different interleavings of identical
gap operations do not create a false zero winner/runner-up margin. Complexity is
`O(R × S × B)` for `R` PDF rows, `S` candidate schema nodes and beam width `B`,
rather than enumerating row combinations.

Candidate clusters are always sorted internally by `display_order`, even if the
caller supplies IDs in another order. Optional previous/next anchors restrict
the permitted workbook interval. A verified statement, scope, section, parent
ID or mapped PDF-parent relation is a hard constraint; label or semantic scores
cannot compensate for a conflict.

## Evidence and scoring

Eligible match transitions may use:

- normalized/source-exact label similarity;
- an optional normalized accounting-semantic score supplied by a separate
  model component;
- verified statement, table, section and LCTT-branch context;
- parent ID, parent row or parent-label consistency;
- previous/next anchors and adjacency of already mapped neighbors;
- hierarchy level, indentation, numbering and sibling/child transitions; and
- explicit PDF/schema gap and gap-imbalance penalties.

Numeric values, arithmetic results, MongoDB history and numeric ReportNormId
order are absent from the API and forbidden by the policy file. External
accounting-semantic scores are proposals in `[0,1]`; they cannot pass a hard
structure gate.

## Fail-closed acceptance

The matcher returns the best path, a distinct runner-up, their score margin,
all score components, retained unmatched rows, unmatched schema nodes and search
statistics. A cluster is `RESOLVED` only when all configured gates pass:

- minimum candidate and mean pair score;
- minimum matched-row count and schema-cluster coverage;
- no retained structural issue;
- indentation distance within the allowed bound; and
- a decisive best-versus-runner-up path margin.

Otherwise the cluster is `AMBIGUOUS_MAPPING`; its best path remains review
evidence but has no automatic-selection authority. A skipped schema node becomes
`NOT_OBSERVED` only when the input block was explicitly declared exhaustive and
the cluster itself resolved. Otherwise it is
`UNMATCHED_SCHEMA_NODE_IN_BLOCK`. Extra visible rows are retained as
`UNMATCHED_PDF_ROW_RETAINED`, or as
`OUT_OF_SCOPE_FOR_TARGET_TEMPLATE` when the scope policy excludes them.

## Calibration boundary

The initial weights and thresholds in
`config/mapping/ordered-subgraph-v1.yaml` are logic-development parameters, not
production-calibrated confidence. They may be changed only on development or
validation fixtures. E-0022 was frozen before this mapper existed, so this code
must not be introduced into that untouched-holdout run retroactively.

The first bounded fixture contains six visible PDF rows and three applicable
schema rows. The required acceptance behavior is three ordered one-to-one
matches, three retained PDF skips, no forced duplicate assignment and a clear
path margin. Additional fixtures cover same-label/different-parent rows,
non-numeric ID order, numbering conflict, and an indistinguishable duplicate
that must abstain.
