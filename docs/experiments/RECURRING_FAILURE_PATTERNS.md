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
  `accounting_additive_table_closure_v1` requires complete recognized
  additive-child lanes and exactly one visible trailing row equal to every
  lane sum; a mismatch, missing crop, or second equal candidate remains
  unresolved and never back-solves a digit.
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
  families remain explicit. The shared declarative topology scan now carries a
  document-wide line ordinal and a family-configured continuation-page budget,
  so parent/child anchors may cross a page boundary without joining label text
  across pages. A structural reset terminates that proposal; period, unit and
  column compatibility remain mandatory in the later evaluation gate.
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
- **Examples:** BID million-VND notes; relative `Số cuối kỳ/Số đầu kỳ` or
  `Số cuối năm/Số đầu năm` headers; annual vs interim periods; a
  following central-bank-deposit heading adding a second pair of dates to the
  candidate window when the structural reset wording has a qualifier.
- **Cause:** nearest text is used without repeated document-level consensus and
  continuation scope.
- **Do not:** hard-code 2025/2026 or inherit across a structural reset.
- **Generic primitive/fix:** dominant repeated document-period context, typed
  balance/roll-forward semantics, scoped unit inheritance and visible reset
  boundaries. The shared local-period extractor treats the `kỳ` and `năm`
  end/start surfaces as the same relative roles; family specs enumerate
  semantic next-family headings, including qualified central-bank variants,
  so a later table cannot contaminate the local axis. Explicit document units
  now retain currency and decimal magnitude; inheritance is allowed only when
  all explicit document-unit evidence agrees. Local exact, split, two-year or
  relative period headers are projected onto body-derived numeric columns and
  checked against repeated document dates without reading a filename or fixed
  year.
- **Status:** `MITIGATED`; the shared period/unit column gate exists, while
  cross-page axis inheritance and full-matrix coverage remain incomplete.

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
- **Examples:** rotated risk tables and merged multi-level headers. On CTG
  annual cash p39, full-page Gemma copied the comparative `17` into the
  current-period cell whose source pixel is a dash, and also changed visible
  `22.581` to `22.561`; a row-only request omitted the dash entirely.
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
- **Additional falsifier:** CTG annual cash/non-monetary-gold has a visible dash
  in the current-period lane but the detector emits no box at all for that
  cell; line-crop recognition alone therefore cannot distinguish it from a
  blank.
- **Cause:** absence of an OCR token is interpreted numerically.
- **Do not:** turn an undetected or blank cell into zero.
- **Generic primitive/fix:** typed `BLANK`, `DASH`, `PRINTED_ZERO` states; only a
  pixel-bound dash may normalize to numeric zero under the family policy. The
  shared numeric-cell evidence primitive now emits `BLANK_UNRESOLVED`,
  `DASH_ZERO`, or a conservative signed-number parse from the immutable crop.
  Shared geometry treats a visible dash as a cell candidate but never treats
  an empty OCR surface as zero; a row candidate whose baseline displacement
  exceeds the adaptive row scale is rejected even when adjacent OCR boxes
  touch, so a missing lane cannot borrow a value from the following row.
  The row-binding projection retains each visible cell's body-derived
  `column_ordinal`; a lone right-hand value therefore remains comparative/right
  rather than being shifted into the first lane. When the table grid proves a
  lane is present but the detector has no box, the downstream authenticated
  page-region primitive re-renders the exact sealed source page and crops the
  proposed row-band × column-domain cell. The crop is still only evidence
  input: either the recognizer must independently see the dash or the narrowly
  bounded pixel-glyph classifier must prove one centered horizontal mark before
  zero is admitted. The family row-axis now replays that proposed region and
  glyph evidence before completing the missing lane; a blank or non-dash crop
  leaves the row incomplete.
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

## RFP-017 — Detector geometry is mistaken for numeric recognition authority

- **Pattern:** PP-OCR detection boxes are treated as though they already prove
  the digits inside a financial cell, or a semantic line proposal is reused as
  the final numeric value.
- **Examples:** visible dashes without a recognition token; dropped final digits
  such as VIB `97.043.85`; closely spaced risk-table cells whose boxes are
  correct while one recognizer merges their content; a visible numeric/dash
  cell for which the detector produced no geometry at all.
- **Cause:** text detection and text recognition are separate models, but their
  outputs are collapsed into one informal “OCR result”.
- **Do not:** infer digits from bbox presence, promote an empty detector token
  to zero, or repair a recognizer result from an expected total.
- **Generic primitive/fix:** PP-OCRv6 detector supplies only the ordered geometry
  axis. After graph/table logic selects a numeric cell, its immutable pixel crop
  is consumed by the separately pinned `PP-OCRv6_medium_rec`; the raw proposal
  is parsed by `family_first_numeric_cell_evidence_v1`. A visible dash may become
  zero, a blank remains unresolved, and accounting closure only corroborates or
  vetoes. Gemma may provide a blind independent challenger on difficult crops.
  If detector geometry is absent, a proposed cell is cropped from an
  authenticated full-page render using generic table row/column geometry; this
  proposal is explicitly not numeric authority and remains replayable from the
  pinned source PDF and bbox. A wide missing-cell crop is tightened to stable
  glyph components before recognition. Because PP-OCRv6 can still read a short
  dash as a letter (real CTG result: `è`) and Gemma can copy the neighboring
  value, one centered horizontal-glyph classifier supplies a separate
  crop-hash-bound `VISIBLE_HORIZONTAL_DASH_GLYPH` observation. It never
  classifies digits, blanks, multiple components, off-center marks, or table
  rules and never sees an expected value or accounting equation. The bounded
  solid horizontal bar emitted by some embedded PDF dash fonts is supported,
  while a full-span table rule remains rejected.
- **Status:** `MITIGATED`; detector, recognizer, authenticated page-region crop,
  and conservative visible-dash pixel evidence are separated. The GPU-sharded
  family-first authenticated numeric receipt is implemented and its full-axis
  formal execution is in progress.

## RFP-018 — An OCR receipt locks unrelated family-engine source forever

- **Pattern:** replay requires the complete `src/bctc_ai` tree to remain
  byte-identical after inference, so adding a generic topology/header primitive
  for a later family invalidates an otherwise unchanged OCR cache.
- **Examples:** the first numeric-index ledger compared the whole current source
  tree with the run tree even though the recognizer, archive, runner, index and
  their imported dependencies were unchanged.
- **Cause:** a broad source-tree identity was used as a shortcut for an exact
  executable trust closure.
- **Do not:** weaken replay to untracked current code, or force an expensive OCR
  rerun merely because an unrelated family specification/engine was added.
- **Generic primitive/fix:** retain the run source-tree OID as an observation,
  but pin every statically imported local dependency plus the fixed
  orchestrator/config by path, bytes and commit. Permit only a clean descendant
  whose complete pinned trust closure is unchanged. Regression tests derive the
  local import closure from the source AST so a later import cannot be omitted
  silently.
- **Status:** `RESOLVED` for the family-first VietOCR and PP-OCRv6 numeric lanes
  before either formal all-filing inference run.

## RFP-019 — Preflight requires an unauthenticated ambient model distribution

- **Pattern:** a model runner rejects the intended clean environment before
  inference because it asks package metadata for a model package that is
  deliberately available only through its authenticated private wheel.
- **Examples:** the first family-first VietOCR launch found the exact pinned
  PyTorch/CUDA environment but raised `PackageNotFoundError: vietocr` before
  attempt creation, model import or model load.
- **Cause:** ambient dependency validation and private model-wheel validation
  were performed as though they shared one import environment.
- **Do not:** install a second ambient VietOCR copy, suppress version checks, or
  count a preflight-only launcher failure as a model inference attempt.
- **Generic primitive/fix:** preflight validates ambient dependencies excluding
  the deliberately private model distribution, authenticates the exact wheel
  and installed overlay bytes, materializes that wheel into a private 0700
  overlay, then observes and validates the complete package ledger after import
  from that overlay. No output root is staked before this preflight succeeds.
- **Status:** `RESOLVED` for the family-first VietOCR runner; regression and real
  RTX 4090 preflight both pass.

## RFP-020 — Right-aligned short values create a false numeric column

- **Pattern:** a short value such as `17` has a bbox center far to the right of
  longer values in the same column, so center-only clustering invents an extra
  lane and proposes a missing cell in the real comparative column.
- **Examples:** CTG annual cash/non-monetary-gold: `17` shares the comparative
  right edge with `22.581` and `18.440`, but its bbox center differs by about one
  full glyph width.
- **Cause:** numeric columns are inferred only from bbox centers although
  financial values may be right-, center-, or left-aligned.
- **Do not:** add a coordinate tolerance for one page, drop short values, or
  assume every table is right-aligned.
- **Generic primitive/fix:** cluster the same body values independently by
  left, center, and right anchors; select the alignment with the smallest
  coherent repeated lane set, then project the cluster's median visual center
  to headers and rows. This remains page-scale adaptive and bank/family blind.
- **Status:** `MITIGATED`; synthetic scale tests and the exact CTG source-page
  dash replay pass, while the 140-filing family sweep remains pending.

## RFP-021 — One monolithic OCR process makes completed work non-durable

- **Pattern:** a complete-corpus recognizer keeps every proposal in an
  `.incomplete` artifact until the final sample, so one external termination
  discards hours or days of otherwise ordered output.
- **Examples:** the first all-filing PP-OCRv6 numeric attempt was externally
  sent `SIGTERM` after 6,528 of 667,224 crops; Paddle, the model and the crop
  axis had not failed.
- **Cause:** atomicity was applied only to the full corpus instead of to bounded
  deterministic units of work.
- **Do not:** relabel the partial JSONL as complete, resume inside an unverified
  partial shard, or claim that no physical retry occurred.
- **Generic primitive/fix:** partition the immutable anonymous archive axis
  into fixed contiguous shards. Each shard starts from a fresh or reset sealed
  reader position, retains global sample IDs, validates every crop/result and
  is published atomically only after complete readback. Hidden interrupted
  stages have no authority and are never resumed. A later aggregate is
  published only after all shard ranges replay gap-free in order. Receipts
  explicitly set physical-attempt and retry-absence attestations to false. A
  real CPU shard measured only about 1.5 crops/second, while the exact same
  pinned recognizer on the RTX 4090 measured about 26.3 crops/second. The GPU
  lane therefore has a separate V3 cache, execution policy and receipt that
  pin `paddlepaddle-gpu`, `gpu:0`, FP32, the device name and compute capability;
  CPU and GPU shards are never mixed in one aggregate.
- **Status:** `MITIGATED`; CPU V2 and GPU V3 shard/aggregate/index contracts pass
  focused tests, the first CPU shard is retained only as a cross-backend
  challenger, and the formal GPU all-axis execution is pending.

## RFP-022 — No semantic anchor is confused with a partial family match

- **Pattern:** a complete filing with none of a family's parent/child anchors is
  reported as the same unresolved state as a filing that contains a partial or
  ambiguous family structure.
- **Examples:** a filing whose notes begin after the cash family versus a filing
  that contains the cash heading but loses one required row or column.
- **Cause:** all zero-region topology outcomes were collapsed into one
  `UNRESOLVED_NO_COMPLETE_REGION` status.
- **Do not:** claim authoritative absence from string search alone, or keep a
  genuinely partial structure in the no-anchor bucket.
- **Generic primitive/fix:** the complete-document topology scan counts blind
  semantic anchors before region assembly. Zero parent/child anchors yields
  `NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY`; any partial anchor evidence
  remains `UNRESOLVED_NO_COMPLETE_REGION`. Exact live replay is still required,
  and `NOT_OBSERVED` remains proposal-only rather than source-wide absence
  authority.
- **Status:** `MITIGATED`; shared topology and both topology/evidence sweep
  metrics now preserve the distinction, while the first 140-filing formal
  sweep remains pending completion of the OCR indices.
