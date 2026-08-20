# Recurring failure patterns — family-first TM digitization

Updated: 2026-08-20 (UTC)

This ledger is a mandatory pre-change check for shared table/OCR logic. It keeps
only recurring or high-impact patterns. A family wrapper may declare semantic
roles and accounting relations, but a layout failure listed here must be fixed
in a shared primitive unless evidence proves it is genuinely family-specific.

Status meanings:

- `OPEN`: no reusable mitigation yet covers the observed variants;
- `MITIGATED`: a reusable guard exists, but cross-filing coverage is incomplete;
- `RESOLVED`: the generic rule and its regression evidence cover the known class.

## RFP-001 — VietOCR loses, inserts, or substitutes a character/digit

- **Pattern:** Vietnamese labels lose/add characters; numeric strings lose or
  substitute a digit even at high confidence.
- **Examples:** MBB `Nợ trùng hạn`; VIB `97.043.85`; HDB
  `6.960.904/6.980.904`; CTG `(6.341.026)/(5.341.026)`.
- **Cause:** sequence recognition confidence is not character-level truth.
- **Do not:** correct text/numbers from an expected schema value or merely to
  close an equation.
- **Generic primitive/fix:** accentless anchor matching with bounded edit
  distance; pixel/source numeric challenger; accounting closure only
  corroborates or vetoes. Gemma 4 may independently reread a bound crop without
  seeing expected values. `family_first_numeric_cell_evidence_v1` rejects
  malformed groupings such as a dropped final digit instead of repairing them.
- **Status:** `MITIGATED`.

## RFP-002 — Adjacent or merged column headers collapse into one header

- **Pattern:** two nearby headers such as `Quá hạn` and `Không chịu lãi` are
  emitted as one OCR line although value columns below remain separate.
- **Examples:** CTG interest-rate table and multi-currency/money-percentage
  tables with closely spaced header cells.
- **Cause:** recognition line grouping is wider than the table's column grid.
- **Do not:** treat one OCR header line as proof of one data column or split it
  at a bank/page-specific pixel coordinate.
- **Generic primitive/fix:** infer leaf columns from repeated value centres and
  child rows; bind a spanning header to multiple leaf columns; use Gemma
  full-page JSON only as a second structure proposal.
- **Status:** `MITIGATED`; body-derived column and spanning-header primitives
  exist, but family-first cross-filing coverage is still incomplete.

## RFP-003 — Multi-level or wrapped headers are flattened

- **Pattern:** period, unit, group, and leaf headers occupy several rows or one
  label wraps across lines; flat OCR order loses the hierarchy.
- **Examples:** ACB customer-deposit vertical period blocks; risk tables with
  group headers over currency or repricing lanes.
- **Cause:** text order is used without geometry and span relationships.
- **Do not:** require a single-line exact header or hand-author a bank-specific
  header tree.
- **Generic primitive/fix:** reconstruct header bands, span containment,
  repeated column centres and wrapped-line unions before assigning axis roles.
- **Status:** `MITIGATED`; the shared header-band/span graph exists, but the
  family evaluators have not yet exercised it across the full filing matrix.

## RFP-004 — Percentage lanes are mistaken for monetary lanes

- **Pattern:** money and percentage values interleave under repeated periods;
  a first-two-numbers rule silently selects the wrong population.
- **Examples:** VIB maturity and customer-deposit presentations with four
  monetary/percentage lanes.
- **Cause:** numeric surfaces are typed only by appearance or horizontal order.
- **Do not:** project monetary-only columns before proving the header-to-leaf
  column binding.
- **Generic primitive/fix:** typed `MONEY`/`PERCENT` axes, unit/header evidence,
  repeated row centres and separate equations for each population.
- **Status:** `MITIGATED`.

## RFP-005 — Continuation pages merge with an unrelated table

- **Pattern:** a page starts with rows but no repeated owner/header, or a nearby
  page contains a similar family; adjacency alone merges them.
- **Examples:** cross-page provision and securities tables; VIB comparative
  continuations.
- **Cause:** page adjacency is mistaken for semantic continuation.
- **Do not:** merge every next page or require the owner to repeat verbatim.
- **Generic primitive/fix:** continuation requires compatible columns, period,
  unit, row topology, open boundary and no structural reset; hard negative
  families remain explicit.
- **Status:** `MITIGATED`.

## RFP-006 — Source-only parent is mapped or added twice

- **Pattern:** a visible grouping parent is mapped as a value row although its
  children already populate the accounting total.
- **Examples:** HDB UPAS-LC parent; optional margin and source group parents.
- **Cause:** every labeled row is assumed additive and schema-eligible.
- **Do not:** map both parent and children without a population equation.
- **Generic primitive/fix:** typed `SOURCE_ONLY_GROUP_PARENT`, explicit child
  population, and same-population closure before mapping.
- **Status:** `MITIGATED`.

## RFP-007 — Same wording identifies a different accounting population

- **Pattern:** labels look alike while accounting direction, gross/net basis or
  population differs.
- **Examples:** asset-side interbank lending vs liability-side borrowing;
  securities geography gross vs net after provision.
- **Cause:** text similarity overrides owner, statement side and accounting
  measure.
- **Do not:** share mapping authority merely because aliases match.
- **Generic primitive/fix:** family spec declares owner/parent, statement side,
  population and equations; text is anchor evidence only.
- **Status:** `RESOLVED` for the known interbank and securities cases.

## RFP-008 — Period or unit is inherited from the wrong scope

- **Pattern:** a table lacks a local date/unit and inherits from a document,
  section or prior page; a nearby narrative/year becomes the chosen context.
- **Examples:** BID million-VND notes; relative `Số cuối kỳ/Số đầu kỳ` headers;
  annual vs interim periods.
- **Cause:** nearest text is used without repeated document-level consensus and
  continuation scope.
- **Do not:** hard-code 2025/2026 or inherit across a structural reset.
- **Generic primitive/fix:** dominant repeated document-period context, typed
  balance/roll-forward semantics, scoped unit inheritance and visible reset
  boundaries.
- **Status:** `MITIGATED`; unit inheritance remains incomplete.

## RFP-009 — Quarter and cumulative periods are conflated

- **Pattern:** Q2/Q3 filings show both quarter-only and cumulative flows while
  balance axes use period-end snapshots.
- **Examples:** Q2 versus reviewed H1; Q3 versus reviewed nine-month filings.
- **Cause:** filename/reporting date is treated as sufficient period semantics.
- **Do not:** map every visible current-period value as the same canonical axis.
- **Generic primitive/fix:** derive document end date from repeated PDF evidence,
  then classify balance, quarter flow, cumulative flow and roll-forward axes
  from the local header topology.
- **Status:** `OPEN`.

## RFP-010 — Typography or uppercase is treated as a hard heading rule

- **Pattern:** a real family heading may be mixed case, split, or absent while
  uppercase narrative text creates false anchors.
- **Examples:** owner implied by child cluster; headings split across OCR lines.
- **Cause:** typography substitutes for structural evidence.
- **Do not:** require uppercase or accept uppercase alone.
- **Generic primitive/fix:** typography is weighted evidence alongside
  parent/children, neighbours, geometry, axes and closure.
- **Status:** `MITIGATED`.

## RFP-011 — Gemma page JSON and deterministic geometry disagree

- **Pattern:** Gemma reconstructs a plausible nested table that conflicts with
  OCR boxes, source order or accounting closure.
- **Examples:** rotated risk tables and merged multi-level headers.
- **Cause:** multimodal generation supplies semantic structure but not stable
  pixel provenance.
- **Do not:** let Gemma alone choose a mapping, value, expected schema ID or
  silently replace VietOCR.
- **Generic primitive/fix:** bind each Gemma proposal to the exact page/crop;
  compare it with geometry, VietOCR and accounting evidence; fail closed on an
  unresolved conflict. Use a fresh context per rescue request.
- **Status:** `MITIGATED`.

## RFP-012 — Rotated pages are parsed in the wrong frame

- **Pattern:** landscape/rotated tables merge headers, reverse reading order or
  drop numeric lanes.
- **Examples:** CTG/BID/VIB fixed-assets and risk tables.
- **Cause:** PDF rotation metadata is assumed to equal visual content angle.
- **Do not:** tune coordinates for one rotated page or mix upright and original
  coordinate frames without an explicit transform.
- **Generic primitive/fix:** estimate content orientation, rotate to an upright
  processing frame, rerun geometry/OCR, and retain the reversible transform for
  source-pixel evidence.
- **Status:** `MITIGATED`.

## RFP-013 — Blank, dash, and zero are collapsed

- **Pattern:** an empty cell, a visible dash and a printed zero are treated as
  the same value.
- **Examples:** VIB segment fixed-assets blank; HDB/VCB risk-table dashes.
- **Cause:** absence of an OCR token is interpreted numerically.
- **Do not:** turn an undetected or blank cell into zero.
- **Generic primitive/fix:** typed `BLANK`, `DASH`, `PRINTED_ZERO` states; only a
  pixel-bound dash may normalize to numeric zero under the family policy. The
  shared numeric-cell evidence primitive now emits `BLANK_UNRESOLVED`,
  `DASH_ZERO`, or a conservative signed-number parse from the immutable crop.
- **Status:** `MITIGATED`.

## RFP-014 — A table row absorbs page furniture or an audit stamp

- **Pattern:** stamps/signatures contribute number-like tokens on the same
  horizontal band as genuine values.
- **Examples:** HDB `1500` audit-stamp fragment beside a two-period row.
- **Cause:** y-overlap alone defines row membership.
- **Do not:** keep every number on the band or hard-code a page-edge cutoff.
- **Generic primitive/fix:** bind values to authenticated leaf-column centres;
  unmatched number-like tokens remain outside the table.
- **Status:** `RESOLVED` for the two-period column-centre primitive.

## RFP-015 — Bank/page/period-specific fixes masquerade as variants

- **Pattern:** a failing fixture is repaired with a bank, note number, page or
  fixed-year branch inside layout logic.
- **Examples:** historical per-page TM parsers and fixed 8-document cache
  profiles.
- **Cause:** evidence locators leak into inference and prevent unseen-filing
  generalization.
- **Do not:** route by bank/file/page/note/year or duplicate a layout fix in
  multiple family wrappers.
- **Generic primitive/fix:** inference receives anonymous page/line geometry;
  family behavior is declarative; provenance is joined only after validation.
- **Status:** `MITIGATED`; legacy fixed consumers remain preserved, while new
  family-first work must not extend their fixed-denominator design.

## RFP-016 — A rigid parent and complete ordered-child list rejects real variants

- **Pattern:** a valid cluster omits its visible family heading, reorders
  siblings, or contains only a filing-relevant subset of optional children.
- **Examples:** loan-type rows directly under `Cho vay khách hàng`; maturity and
  deposit tables whose optional margin/currency rows move or disappear.
- **Cause:** one canonical presentation is encoded as a mandatory ordered list
  instead of separating semantic requirements from source presentation.
- **Do not:** add a bank-specific parser, require every schema child to appear,
  or accept a parentless cluster from text similarity alone.
- **Generic primitive/fix:** declarative required/optional roles, flexible
  sibling order, explicit-or-structurally-implied parent policy, reset and
  hard-negative boundaries, followed by whole-document minimal-anchor
  uniqueness with all pairs exhausted before triples. Period, unit, geometry,
  population and accounting checks remain independent mandatory gates.
- **Status:** `MITIGATED`; `accounting_family_topology_v1` covers the semantic
  topology class, while all-filing family coverage is still in progress.
