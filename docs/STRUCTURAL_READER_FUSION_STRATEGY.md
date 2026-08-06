# Structural reader fusion v2

## Purpose and claim boundary

This version turns independently sealed Role B table serialization and Role C
word boxes into traceable row proposals. It solves structure before schema
mapping. It does not declare either reader to be truth, add a ReportNormId,
choose a cash-flow schema branch, repair a number arithmetically, or promote
confidence because two models agree.

Production routing must receive page type and scope from the ordered statement
locator. Explicit document/page lists in an experiment configuration are frozen
fixture data, not bank-specific routing code.

## Role B: all-block, variable-column parsing

`reader_outputs_v2.py` processes every generated HTML table block in document
reading order. It expands `rowspan` and `colspan` into a rectangular grid while
placing cell text only at its origin; it never duplicates a colspan string into
financial columns or splits a multi-number string into guessed cells.

Column roles are inferred in this order:

1. Scan a bounded number of leading rows for at least two concise period cells.
2. Identify optional index, label, and note columns from versioned header aliases.
3. When a label header is absent, select the non-financial column before the
   period axes with the strongest body text evidence.
4. A header-only table may lend its exact roles to the immediately following
   compatible-width table. The inheritance is consumed once and is not carried
   across another table.
5. Without a header, a body-only fallback requires a consecutive rightmost run
   of financial columns above a configured density. Otherwise the entire block
   remains `UNRESOLVED_COLUMN_ROLES` rather than being discarded or guessed.

This covers label–note–period, `STT`–label–note–period, `STT`–label–period, and
label–period layouts under the same code. Heading-only and unresolved blocks
remain visible in the output. Period-like cells with long report titles are
rejected, and grouped numbers with inconsistent three-digit groups are
`INVALID`; this prevents concatenated row values such as
`3.645.303941.493` from becoming a plausible integer.

## Role C: geometry, row codes, notes, and values

`word_box_rows_v2.py` depends on the frozen v1 geometry primitives but uses a
new versioned policy. It:

- accepts concise headers such as `31/12/2025`, `2025`, and `Năm 2025`;
- selects the most compact horizontally separated period-axis group, preventing
  a report date plus regulatory-form date from masquerading as two periods;
- infers note references by header/right-edge geometry, including references
  such as `15(d)` and `33(a)`;
- detects a leading row-code band only from repeated narrow codes paired with
  text on the same visual row, not from a fixed x-coordinate;
- uses the detected band to remove `STT`, Roman numerals, letters, and sequence
  numbers from item labels, including safe prefix separation when OCR joins a
  code and label into one line;
- forms row anchors from value cells plus structural code/note evidence, so a
  row remains present when one or both period cells are OCR-blank;
- joins wrapped label lines only through relative y-neighborhood and intervening
  row anchors;
- assigns numeric tokens by right edge with a strict right-overrun limit, so
  page-number/seal noise outside the value axes is retained as unassigned
  evidence rather than contaminating a financial cell; and
- invokes the existing constrained pixel-component detector only for an
  OCR-blank cell at an already evidenced row/axis. A dash is never inferred from
  arithmetic or from absence alone.

Every row retains source line IDs, optional row code, label/note/value line
indices, parsed VALUE/ZERO/BLANK/DASH/INVALID states, visual dash evidence, and
warnings. Unassigned numeric lines and trailing context are explicit outputs.

## Order-only cross-reader comparison

`structural_fusion_v2.py` aligns Role B and Role C with document order and
normalized label text only. Values, signs, notes, row codes, history, schema
IDs, and arithmetic are excluded from the dynamic-programming path. They are
compared only after the path is fixed.

The comparison retains five structural outcomes:

- `MATCH`;
- `MERGE_CANDIDATE` for two Role C fragments against one Role B row;
- `MERGE_REFERENCE` for two Role B rows collapsed into one Role C row;
- `MISSING_CANDIDATE` when Role C lacks Role B evidence; and
- `EXTRA_CANDIDATE` when Role B is missing or truncated relative to Role C.

Each outcome receives a reread/reconstruction escalation. Even an exact pair is
reported as `CROSS_READER_AGREEMENT_NO_CONFIDENCE_PROMOTION`.

## Scope and cross-page rules

The upstream page contract is applied before any row can become
mapping-eligible. An off-balance page remains excluded even if both readers
produce perfect-looking names and numbers. The configured row/section scope
policy is an additional gate, never a way to re-enable an excluded page.

Rows from pages classified as the same statement may be concatenated in page
order for a second alignment pass. A continuation edge is permitted only when
the statement type and report scope agree, page order is monotonic, and no
excluded/unknown page lies between them. Headers repeated on a continuation
page are context, not financial rows. A row split across a page boundary may be
proposed as a structural merge, but numeric cells are never shifted across rows
to make it fit.

## Mapping and validation boundary

Only after structural review can the mapper generate schema candidates from
label aliases, parent/child hierarchy, preceding/following clusters, section,
indentation, and schema workbook order. Duplicate labels require positional and
neighborhood evidence. Values do not select a ReportNormId.

Arithmetic checks run after period/unit/scope binding and mapping. Horizontal,
vertical, parent/child, and cash roll-forward equations can trigger a targeted
reread or downgrade; they cannot create, overwrite, change the sign/state of,
or move an observed value. Quarterly YTD subtraction remains a separately
provenanced derived-value stage.

Q-BOOT-001 remains fail-closed. No PDF direct/indirect observation in this
version assigns the workbook LCTT branch. Q-BOOT-004 remains mandatory before
any future ReportNormId proposal is appended.

## Versioned configuration and tests

- Role B policy: `config/tables/vlm-table-parser-v2.yaml`.
- Role C policy: `config/tables/word-box-reconstruction-v2.yaml`, which binds
  the existing v1 base policy by path/hash in formal experiments.
- Unit regressions cover multi-table/header inheritance, optional `STT` and
  note columns, row/column spans, title-versus-period disambiguation, worded
  periods, wrapped index/value alignment, two OCR-blank dash cells, margin
  numeric noise, concatenated grouped values, value-independent alignment,
  missing rows, and upstream off-balance exclusion.

No new package, system library, driver, model, or weight is required. Rebuild
the existing locked environments, verify both v2 configurations and source
hashes, then run the complete suite before creating a clean formal experiment.

