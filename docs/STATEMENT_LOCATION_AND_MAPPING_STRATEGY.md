# Statement location and schema-mapping strategy

This document is the durable design record for locating and mapping Vietnamese
financial-statement evidence. The implementation must generalize across banks,
non-bank companies, separate/parent/consolidated statements, annual/quarterly
filings, and audited/reviewed reports. Bank names, known page numbers, and
institution-specific coordinates are forbidden as production routing rules.

## Authority and evidence roles

1. The visible, registered PDF is authoritative.
2. A render and OCR artifact are usable only after their source, role, config,
   model, runtime, code, dimensions, and SHA-256 chain pass verification.
3. OCR/model outputs are proposals. Independent readers may corroborate one
   another, but agreement is not truth and correlated models must be disclosed.
4. The supplied schema workbooks define allowed IDs and workbook order. The
   `vst_level` workbooks provide supporting hierarchy evidence. Neither may
   override a visibly different PDF value.
5. Mongo/DuckDB history is a weak post-mapping reference only. It cannot create
   candidates, choose an ID, fill a value, or promote confidence.
6. Arithmetic validates visible operands and triggers a reread/review. It never
   creates or overwrites a value.

## Stage 1 — quality-gated page evidence

Before OCR, measure blur, contrast, dark/colored header regions, uneven
background, orientation, skew, and perspective. Keep the original render and
create only reversible, reason-specific variants. Select a variant by measured
OCR/cell evidence on calibration data, not by visual preference. Unreadable or
cropped regions remain unresolved.

The coarse document pass may run at lower DPI to find likely report blocks.
The final numeric pass must return to the registered source and render only the
selected pages/regions at the controlled higher DPI. This is the coarse-to-fine
policy; a low-DPI value is not automatically promoted to final evidence.

## Stage 2 — ordered main-statement location

The current implementation is `statement-locator-v1.yaml` plus
`statement_locator.py`. It uses no bank or page-specific rule.

### Page emissions

Each page receives explicit evidence rather than a label-only guess:

- header form codes such as the configured B02/B03/B04/B05 family;
- full-title edit similarity, with a required discriminative phrase;
- numeric-line density for title-only CDKT/KQKD/LCTT candidates;
- audit-report and table-of-contents suppression;
- continuation markers such as “tiếp theo”/“continued”;
- off-balance heading evidence and a minimum cluster of off-balance items.

Token-subset similarity is deliberately not used for full statement headings:
a narrative sentence containing “báo cáo tài chính” otherwise looks like a
statement title. Title-only main-statement pages also require table evidence;
this blocks audit prose and covers from becoming false statement starts.

### Global sequence

Candidate blocks must contain the contiguous order:

```text
CDKT (one or more pages) -> KQKD (one or more pages)
-> LCTT (one or more pages) -> first TM boundary
```

No unknown/interstitial page may be silently skipped. A candidate cannot start
on an explicit continuation page or an off-balance page. Competing candidates
are scored from versioned weights for start-form evidence, number of form-bound
pages, and average page confidence. A small winner/runner-up margin returns
`UNRESOLVED` rather than guessing. All candidates, score components, page
decisions, and evidence are retained in the output.

### Off-balance scope

A page may carry a B02-family form code but still be entirely outside the main
balance sheet. “Bảo lãnh vay vốn”, “Cam kết giao dịch hối đoái”, “Cam kết trong
nghiệp vụ thư tín dụng”, “Tài sản và chứng từ khác”, and similar rows are
classified as `OFF_BALANCE_SHEET` and `mapping_eligible=false`.

The output separates:

- pages recognized by statement form;
- pages eligible for mapping by statement type; and
- off-balance pages excluded from mapping.

Continuation links require both the same statement type and the same scope, so
the last main CDKT page never links into an off-balance page.

### Cash-flow method

Method evidence is document order, not numeric ReportNormID order:

- direct: direct-method title and/or ordered interest-received then
  interest-paid rows;
- indirect: indirect-method title and/or ordered profit-before-tax then
  adjustment rows.

Direct and indirect title scores are compared against each other because the
shared phrase “phương pháp ... tiếp” can otherwise trigger both. Contradictory
strong evidence yields `CONFLICT`; absent evidence yields `UNKNOWN`.

`Q-BOOT-001` was resolved on 2026-08-06. Once the PDF method is independently
classified without `UNKNOWN` or `CONFLICT`, current mapping policy v2 selects
the same-named contiguous template block: 4155→4168 is INDIRECT and
4104→4116 is DIRECT. These are workbook-order endpoints, never numeric ranges.
Historical E-0013 locator output keeps `schema_branch_assignment_permitted=false`
because that experiment predates the resolution and must remain hash-replayable.

## Stage 3 — logical rows across lines and pages

Row reconstruction precedes schema mapping:

1. Infer period/value/note axes from header geometry.
2. Join wrapped label lines only when indentation, horizontal overlap, vertical
   gap, and absence/presence of financial cells support one logical row.
3. Preserve parent headings and label-only rows; they define hierarchy even
   when they carry no numeric value.
4. Link a split row/table across pages only when statement type, scope, period,
   unit, header signature, column axes, and boundary evidence agree.
5. Retain unmatched fragments and page-boundary ambiguity explicitly. Never
   drop them merely to produce a rectangular table.

### Table-level period propagation v1

A row never decides its own current/comparative period. Complete visible
headers establish a `TablePeriodMap`; a headerless page can inherit it only
through an accepted adjacent continuation edge with the same statement
instance/type/scope and compatible left-to-right value axes. Source header
text, box, page, and axis remain attached through every inheritance hop.

Partial local headers do not mix with inherited fields. A new statement, a new
non-continuation table, changed period structure, non-adjacent page, or changed
value-axis geometry leaves the table unresolved. Numeric values and MongoDB are
not inputs to `period_propagation_v1`.

## Stage 4 — contextual schema alignment

Labels generate candidates; they do not decide the mapping. For each observed
row, candidate generation is restricted to the correct statement/branch and
uses controlled aliases, exact/normalized text, and fuzzy retrieval. Final
alignment is a monotonic block/subtree optimization over these features:

- schema/workbook order and physical PDF order;
- parent/child depth and section membership;
- previous and next mapped neighbors;
- sibling clusters and expected local row blocks;
- indentation, heading status, and row geometry;
- note-reference presence/position as a foreign-key cue into TM;
- report scope, unit, period axis, and statement method;
- source-exact label evidence separately from accent-stripped semantics.

Repeated names are expected. If several candidates share a name, the system
must use the surrounding block and hierarchy. If the global winner is absent,
inconsistent, or too close to a runner-up, the row remains unresolved. Numeric
values must not select a schema candidate.

`alignment_v2` makes this priority lexicographic rather than allowing a large
name/history weight to compensate for a structural conflict: table/statement,
parent, previous/next plus workbook-order direction, indentation/numbering,
label, same-bank history, then cross-bank history. If history is the first
discriminator the result remains `AMBIGUOUS_MAPPING` and review-only.

ReportNormId is never sorted numerically. `display_order` is read from the
source workbook row order and is the sequence invariant for mapping/export.
This permits later-added large IDs to occupy their correct logical location.
The mapping-sequence gate also prohibits assigning one schema ID to two visible
rows.

Before adding any `ReportNormId`, check collisions against the supplied schema,
all hierarchy workbooks, Mongo template metadata, and known historical keys.
An unused ID clears only the collision gate; it does not establish the correct
name, parent, statement, or authority to append.

## Stage 5 — period and arithmetic gates

Every accepted cell retains statement, scope, unit, period start/end, column,
sign evidence, observation state (`VALUE`, `ZERO`, `BLANK`, `DASH`, etc.),
source box, render/source hashes, and reader provenance.

Value presence is separate from evidence confidence. A visible dash or a
verified empty numeric cell normalizes to zero with `OBSERVED_ZERO` while raw
evidence is preserved. An absent schema row is `NOT_OBSERVED` and has no cell
value. A visible off-balance row is
`OUT_OF_SCOPE_FOR_TARGET_TEMPLATE`, not a mapping error. Missing machine
reference is `REFERENCE_NOT_YET_BUILT`, not evidence against the PDF result.

For quarter-only output from cumulative/YTD reports, subtraction is permitted
only when both visible PDF operands have the same resolved schema ID, scope,
unit, accounting basis, and compatible periods. Both operand provenances and
the formula are retained. A derived quarter is never represented as directly
observed or automatically high confidence.

Horizontal totals, vertical totals, and parent-versus-child sums are validation
signals. A passing identity cannot rescue an incomplete evidence tuple; a
failure routes the affected source cells to targeted rereading/review.

## Accuracy gates and test families

- Unit: malformed config, fuzzy/duplicate headings, continuation, narrative
  false positives, off-balance separation, cash-flow conflict, noncontiguous
  input, candidate ambiguity, and immutable evidence-chain drift.
- Mutation/property: lost signs, digit swaps, dash/zero changes, shuffled rows,
  duplicated names, wrapped labels, broken page boundaries, moved columns, and
  dark/skewed/warped headers.
- Golden/calibration: exact page/type/scope, row/cell boxes, values, signs,
  notes, periods, units, hierarchy/ID, continuation, and unresolved evidence.
- Frozen holdout: unchanged rules across institution, period, scope, report
  type, and distortion subgroups; report coverage separately from conditional
  accuracy.
- Replay: re-hash source/render/model/runtime/config/code, rerun without
  overwrite, reopen exported workbooks, and verify template order/provenance.

No production confidence threshold may be inferred from the two current MBB/VCB
development observations. They validate the locator logic on calibration data,
not end-to-end row mapping or human-gold accuracy.

## Change discipline

- Configuration and algorithms are versioned; historical experiments are
  immutable and bind exact hashes.
- Generated OCR/model outputs stay outside Git but are recorded by portable
  path, hash, dataset role, and replay instructions.
- Every verified milestone is committed and pushed before the next clean
  evidence run.
- Software/model/runtime changes must be added to `SOFTWARE_INVENTORY.md` with
  exact versions, revisions/hashes, install and rollback commands. A version
  that adds no dependency records that fact explicitly.
