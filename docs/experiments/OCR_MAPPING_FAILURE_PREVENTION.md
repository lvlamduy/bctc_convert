# OCR and mapping failure-prevention ledger

This file records mistakes that have already occurred, their root causes, the
accepted correction, and the regression gate that must prevent recurrence. It
is an operational checklist, not an experiment result or a mapping authority.

When a new failure is fixed, append an entry here before closing the affected
family. Do not silently replace an old conclusion: preserve the failure and
record the new gate.

## Mandatory rules before accepting a mapped cell

1. Derive the reporting period, page orientation, table axes, owner, branch,
   children, totals, units, and scope from the document. Never select by bank,
   page number, note number, filename, or a hard-coded year.
2. Search the whole PDF. Start with the smallest distinctive two-anchor
   combination, expand to three or more anchors only when the smaller
   combination is not unique, and retain every near match as a negative
   control.
3. Use fresh VietOCR Transformer text as the main label proposal. Match both
   Vietnamese and accentless normalized text; bounded edit matching may locate
   an anchor but may not decide a ReportNormId by itself.
4. Reconstruct values from independently authenticated source-pixel geometry.
   VietOCR or Gemma text is not numeric authority. Preserve a visible dash as
   `DASH`; when the accounting/table contract permits it, record a separate
   derived numeric value of zero without erasing the source token.
5. Mapping requires the combined evidence of text, owner/parent, children,
   siblings, order, geometry, period axes, units, report scope, totals, and
   accounting equations. Confidence or string similarity alone is never a
   promotion gate.
6. A generative model may propose spelling or table topology. It may not repair
   source digits, invent a missing row, split a combined source amount, or
   promote a mapping without independent replay.
7. Keep difficult variants `UNRESOLVED`, but continue to the next family once
   the reusable core works for the reliable subset. Do not accumulate
   unexecuted candidates.

## OCR, orientation, and table geometry

### F-001 — Treating a merged header as one semantic column

- Observed failure: on CTG's interest-rate-risk table, PP-OCR merged the nearby
  headers `Quá hạn` and `Không chịu lãi` into one text line even though the
  values below remained in two distinct columns.
- Root cause: semantic axes were inferred from OCR line count/text rather than
  the repeated numeric x-axis geometry.
- Correction: reconstruct numeric column centres first, partition the header
  band at the midpoints, and allow one OCR line to project onto multiple
  physical axes. CTG now exposes separate `OVERDUE` and `NO_INTEREST` axes.
- Regression gate: a fixture must contain a merged header box over two separate
  value columns and require two axes with independent values/equations.

### F-002 — Assuming portrait/upright coordinates for rotated pages

- Observed failure: landscape/rotated risk tables were not parsed reliably by
  the ordinary page geometry.
- Root cause: OCR was run against the displayed rotation without a canonical
  upright coordinate space and reversible transform.
- Correction: detect orientation, render/OCR the upright page, perform table
  reconstruction in upright coordinates, and retain the exact inverse
  transform to cite the original PDF. Downstream logic may use upright
  coordinates, but the source citation must remain reversible.
- Regression gate: test 0/90/180/270-degree versions of the same table and
  require identical logical rows, axes, values, and source-pixel round trips.

### F-003 — Relying on one OCR line axis for every provider output

- Observed failure: five terminal VCB pages had valid line polygons but a
  recognition token could be empty, causing the original hydration adapter to
  reject the entire page.
- Root cause: geometry authority was incorrectly coupled to nonempty provider
  transcript text.
- Correction: use a terminal, experiment-local geometry-only supplement that
  validates exact ordered boxes/polygons and quarantines all recognition text
  and word geometry. Terminal/unresolved status is preserved.
- Regression gate: empty or poisoned recognition text must not change the line
  geometry hash; malformed, reordered, out-of-bounds, or non-integer geometry
  must fail.

### F-004 — Using label OCR as numeric truth

- Observed failure: VietOCR dropped digits in numeric-looking crops, and Gemma
  produced convincing table JSON while changing several numbers.
- Root cause: a text recognizer/vision-language proposal was allowed to look
  like cell-value authority.
- Correction: VietOCR supplies labels; PP-OCR/source pixel boxes plus an
  independent numeric challenger supply values. Gemma is bounded to structure
  and spelling rescue unless its digits are independently verified from the
  source crop.
- Regression gate: inject a plausible one-digit change into VietOCR/Gemma
  output and require rejection even when arithmetic could be made to close.

### F-005 — Losing hierarchy in multi-level headers

- Observed failure: flat line parsing attached values to the wrong period,
  currency, percentage, or auxiliary axis when headers spanned several rows.
- Root cause: headers were treated as a single row rather than a hierarchy of
  geometric spans.
- Correction: build a header tree from vertical containment and horizontal
  overlap, propagate parent spans to leaf columns, and validate leaf axes using
  repeated numeric columns. Gemma page-to-JSON may propose the hierarchy but
  must be reconciled with source boxes and totals.
- Regression gate: cover row/column spans, repeated period groups, VND/foreign
  currency/total, percentage lanes, blank header cells, and continuation pages.

### F-006 — Reading only a known page instead of finding the structure

- Observed failure: a correct known page appeared to validate a family while a
  second near-match elsewhere in the PDF was never falsified.
- Root cause: page/bank knowledge leaked into selection.
- Correction: scan the complete PDF using generic two-anchor combinations,
  compare all near matches, then disambiguate with owner, children, neighbours,
  axes, units, totals, and equations.
- Regression gate: a synthetic document must contain one complete structure and
  at least one text-similar negative family; only the complete structure may be
  selected.

## Text recognition and generative rescue

### F-007 — Comparing noisy Vietnamese text literally

- Observed failure: labels such as `Nợ trung hạn` were not found when VietOCR
  produced a diacritic error or one inserted/deleted character.
- Root cause: exact Vietnamese string equality was used too early.
- Correction: retain the raw proposal, also generate Unicode-normalized
  accentless tokens, and allow bounded edit/token matching only for anchor
  discovery. Final mapping still requires structural and accounting evidence.
- Regression gate: diacritic-only and one-character errors should find the same
  candidate; a semantically different near-neighbour must remain unresolved.

### F-008 — Treating aliases as bank-specific parser rules

- Observed failure: adding one alias/parser per bank improved fixtures but did
  not generalize to another year or layout.
- Root cause: variants were encoded by bank/page identity instead of semantic
  roles and optional graph branches.
- Correction: family definitions contain required core roles, optional
  intermediate branches, alternative labels, order constraints, auxiliary
  axes, continuation rules, and negative-family patterns. Bank identity is
  evidence metadata only.
- Regression gate: shuffle bank labels/pages and vary optional rows; logical
  family detection must remain unchanged.

### F-009 — Gemma local inference silently using CPU

- Observed failure: the Vulkan executable listed no GPU and ran in CPU/RAM,
  appearing hung or unexpectedly slow.
- Root cause: the wrong llama.cpp build was launched.
- Correction: use the pinned CUDA `llama-server`, CUDA library path, model and
  mmproj recorded in `GEMMA4_LOCAL_GPU_RUNBOOK.md`; confirm the CUDA device and
  model allocation before sending work.
- Regression gate: preflight must fail when no CUDA device/model allocation is
  observed.

### F-010 — Gemma thinking consumed the output budget

- Observed failure: reasoning consumed an 8,192-token budget and returned empty
  or truncated JSON content.
- Root cause: thinking was enabled for a transcription/structure task.
- Correction: use a fresh chat/request per crop/page, `--jinja`, reasoning off,
  and reasoning budget zero. Keep the prompt short and demand only JSON.
- Regression gate: response must be nonempty, parse as closed JSON, and contain
  all expected source regions before it can be used as a proposal.

### F-011 — Assuming longer or more complex prompts improve table OCR

- Observed failure: detailed instructions consumed context and encouraged the
  model to normalize or reinterpret source labels/numbers.
- Root cause: the rescue prompt mixed transcription, mapping, arithmetic, and
  schema decisions.
- Correction: request faithful JSON transcription/structure only, preserving
  spelling and source tokens; apply mapping and accounting rules in deterministic
  code afterward.
- Regression gate: prompt fixtures forbid ReportNormIds, arithmetic repair, or
  inferred values in the model response.

## Family graphs, schema, and accounting decisions

### F-012 — Requiring one rigid row order across all banks

- Observed failure: real tables with an intermediate parent (`Dư nợ cho vay`),
  margin rows, percentage columns, or reordered children failed despite having
  the same accounting family.
- Root cause: a single full ordered sequence was mistaken for the family.
- Correction: define a small mandatory core, optional/intermediate branches,
  partial-order constraints, and accounting closure. Prefer distinctive pairs
  of parent/child or sibling anchors; expand only when uniqueness requires it.
- Regression gate: every supported variant must pass without bank-specific
  branches, while a nearby but different family must fail.

### F-013 — Accepting a grand total for a strict subset

- Observed failure: MBB's maturity table contains three maturity rows, then a
  separately labelled margin amount, then a grand total. Treating the grand
  total as the three-row subtotal creates exact residuals equal to the margin.
- Root cause: adjacency was prioritized over the accounting boundary.
- Correction: choose the immediate subtotal that closes the intended children;
  retain later margin/grand-total rows as a separate optional branch.
- Regression gate: subset and grand-total equations must both close in their
  own scopes; cross-using either total must fail.

### F-014 — Letting string similarity decide schema mapping

- Observed failure: combined or broader source labels were narrowed into one
  schema leaf, or a related but different statement concept was selected.
- Root cause: lexical similarity overrode parent scope and source population.
- Correction: require compatible owner, statement/family, population scope,
  axes, units, row role, and equations. Create/reuse a combined schema leaf when
  the source amount cannot be split; otherwise keep it unresolved.
- Regression gate: combined-source rows cannot populate narrower children
  unless an authenticated source decomposition exists.

### F-015 — Hard-coding the 2026 current/comparative dates

- Observed failure: period logic assumed fixed dates and could not safely apply
  to annual 2025 or another quarter.
- Root cause: dates were configuration constants rather than document evidence.
- Correction: infer report type and period axes from repeated document-wide
  headings/dates, supporting slash, dot, and Vietnamese prose date forms; bind
  every selected table axis to that document-level period receipt.
- Regression gate: annual, H1, and quarterly fixtures with multiple date formats
  must resolve current/opening/comparative axes without year constants.

### F-016 — Treating absence of a narrow table as extraction failure

- Observed failure: banks without an industry/geographic table, or with a table
  whose population was broader than customer loans, were left ambiguously open.
- Root cause: `NOT_OBSERVED`, `UNRESOLVED`, and broader-scope evidence were not
  separated.
- Correction: after full-PDF search, record `NOT_OBSERVED_IN_BOUND_SOURCE_SCOPE`
  when no qualifying structure exists; never silently narrow a broader
  population. Use `UNRESOLVED` only when a relevant source region exists but
  cannot be mapped safely.
- Regression gate: absence, broader-population, and OCR failure fixtures must
  produce three distinct dispositions.

### F-017 — Schema changes tightly coupled to parser code

- Observed failure: adding a legitimate new leaf required editing family logic
  and risked changing earlier accepted mappings.
- Root cause: schema identity, label variants, graph roles, and layout parser
  were mixed together.
- Correction: keep stable semantic role IDs in declarative family definitions;
  resolve them through a versioned schema projection. Parser outputs semantic
  roles, not bank-specific ReportNormIds. New schema leaves require explicit
  collision and backward-replay tests.
- Regression gate: adding an unrelated schema leaf must not change existing
  detection, equations, mappings, or artifact IDs except the explicitly
  versioned schema projection.

## Runtime, artifacts, and authority

### F-018 — Launching formal VietOCR with the wrong environment

- Observed failure: the project `.venv` lacked `torch`, producing
  `ModuleNotFoundError` before model load.
- Root cause: the formal GPU executor was not pinned in the launch preflight.
- Correction: use the pinned GPU environment and require exact Python/package,
  CUDA, device, model, weights, config, and output-absence checks before model
  load. Preserve a pre-model launcher failure separately from the actual run.
- Regression gate: model-build and sample counters must remain zero after a
  failed preflight; a formal output must not exist.

### F-019 — Using hardlinks for artifacts that require unique inodes

- Observed failure: hydration replay rejected copied inputs because hardlinks
  made `st_nlink > 1`.
- Root cause: storage optimization violated the sealed artifact contract.
- Correction: use reflinks/copy-on-write with distinct inodes and verify byte
  hashes, inode inequality, and `st_nlink == 1` before replay.
- Regression gate: hardlinked input must fail; byte-identical reflink with a
  distinct inode must pass.

### F-020 — Re-reading mutable paths after verification

- Observed failure: request/config/crop/model files could be verified and then
  reopened from a changed path (TOCTOU).
- Root cause: validation and consumption used different filesystem snapshots.
- Correction: consume immutable bytes/file descriptors from one authenticated
  snapshot, or stage verified immutable copies and load only those; perform a
  final ledger reread before mint/publication.
- Regression gate: replace/tamper/delete/symlink any artifact between validation
  and use; every path must fail without publishing authority.

### F-021 — Type laundering in closed JSON contracts

- Observed failure: JSON values such as integer `0` could compare equal to
  `false`, floats to integers, or values could be coerced with `str(...)`.
- Root cause: ordinary Python equality/coercion was used for authenticated
  schemas.
- Correction: validate exact JSON types recursively (`bool` is not `int`) and
  use typed canonical equality before accepting or hashing.
- Regression gate: coordinated rehash attacks using `0/1`, integral floats,
  bytearray/subclasses, extra fields, or string coercion must reject.

### F-022 — Assuming persisted JSON is canonical when the producer did not

- Observed failure: a valid pretty-printed E0044 manifest was rejected because
  a consumer required byte equality with canonical JSON serialization.
- Root cause: decoding rules and content-identity/canonical-output rules were
  conflated.
- Correction: for inherited artifacts, validate strict UTF-8 JSON,
  duplicate-key/nonfinite rejection, closed shape, and exact byte pin; require
  canonical bytes only for formats whose producer contract promises them.
- Regression gate: the real pretty artifact must replay, while duplicate keys,
  nonfinite values, and byte/hash drift fail.

### F-023 — Requiring `type(path) is Path`

- Observed failure: normal `Path(...)` values are `PosixPath`, so exact-type
  checks rejected every real call.
- Root cause: implementation subclassing in `pathlib` was overlooked.
- Correction: use `isinstance(value, Path)` and separately validate canonical,
  root-anchored, no-symlink path semantics.
- Regression gate: real `PosixPath` passes; nested fake Git roots, traversal,
  symlink ancestors, and non-Path values fail.

### F-024 — Comparing equivalent CAS paths from different namespaces

- Observed failure: READY composition rejected valid hydration artifacts because
  one ref was project-relative and another V3-root-relative although SHA and
  size were identical.
- Root cause: full path-string equality was used across contract namespaces.
- Correction: validate each path independently within its own allowed namespace,
  then cross-bind content by exact SHA and size.
- Regression gate: valid namespace variants with identical content pass;
  mismatched content or invalid namespace paths fail.

### F-025 — Mutable capability state and incomplete live replay

- Observed failure: authenticated proposal text could be changed in a mutable
  in-memory dict after mint, and some accessors skipped Git/live-child checks.
- Root cause: capability authority depended on object identity without immutable
  payload bytes and replay on every public access boundary.
- Correction: store canonical immutable bytes plus independent digest, retain
  strong authenticated child capabilities, and revalidate Git/artifact/live
  lineage before projection or batch/crop access.
- Regression gate: mutation, copy/deepcopy/pickle, forged/subclass handles,
  wrong root, Git drift, and child replacement must all reject.

### F-026 — Unsafe pathname publication and cleanup races

- Observed failure: path-based rename/cleanup could publish or delete a foreign
  replacement after an ancestor/name race, and failed staging could leak file
  descriptors or directories.
- Root cause: ownership was learned by pathname after creation instead of held
  through directory file descriptors and captured inode identity.
- Correction: use validated parent dirfds, private staging containers, retained
  inode identities, no-replace publication, post-publish identity checks, and
  owned-tree cleanup only. Close every descriptor in `finally` paths.
- Regression gate: concurrent replacement, injected open/write/readback errors,
  destination races, and cleanup failures must leave no authoritative partial
  output and never delete foreign data.

### F-027 — Claiming one physical run from local evidence

- Observed failure: status prose said “one fresh run” while the tracked selection
  explicitly could not attest historical attempt/retry absence.
- Root cause: evidence-chain authority was overstated in human-readable status.
- Correction: say “one fixed selected fresh output” and explicitly state that
  physical execution/retry history is not attested unless protected by an
  append-only external mechanism.
- Regression gate: documentation tests scan for forbidden stronger claims and
  require consistency with authority flags.

### F-028 — Replaying global live roots multiplicatively

- Observed failure: the E-0046 build plus public validation took about 91 minutes
  and more than 200 GB of logical reads because each page accessor replayed the
  same global chain repeatedly.
- Root cause: per-sample/page capability access performed a full validation
  instead of sharing one immutable authenticated snapshot.
- Correction: expose a single authenticated batch snapshot/session, validate
  global lineage once at mint/project boundary, then serve immutable ordered
  page/sample bytes in O(1), while retaining one final full public replay gate.
- Regression gate: counters must bound global replay count independently of
  page/sample count; output bytes/authority must remain identical.

### F-029 — Merging two complete adjacent accounting rows

- Observed failure: VPB had separate `nội bảng` and `ngoại bảng` rows, each with
  its own numeric cells, but a multiline-label heuristic joined them and lost
  the internal row.
- Root cause: nearby vertical distance was treated as sufficient evidence of a
  wrapped label.
- Correction: before joining label fragments, detect whether the first label
  already owns one or more numeric cells on the same y-band. A complete numeric
  row is never merged with the next label; multiline joining is reserved for a
  label fragment without aligned values.
- Regression gate: adjacent complete internal/external rows must remain two
  roles, while a genuinely wrapped combined-state label without first-line
  values must still reconstruct as one role.

### F-030 — Dropping a column because one header token was misspelled

- Observed failure: VPB's nine numeric columns were visible and repeated, but
  header OCR produced `Tứt-3` and `Trần 5`; exact header parsing returned only
  seven axes and could not bind a nine-cell row.
- Root cause: the header text detector determined the denominator instead of
  the numeric table geometry.
- Correction: derive the column denominator and centres from complete numeric
  rows, project all noisy/multiline header fragments into those fixed columns,
  then use bounded accentless edit matching to name each axis.
- Regression gate: one-character header errors may not drop or merge numeric
  columns; every complete row must bind exactly the geometry-derived axis count.

### F-031 — Reading a regulatory date as the table period

- Observed failure: HDB's page header mentions `31/12/2014` as the issue date of
  an NHNN circular, while the annual-2025 interest-rate table continuation does
  not reprint its own period date.
- Root cause: every visible full date was treated as a candidate table axis,
  and a local-date requirement could not distinguish a regulation citation from
  the repeated document reporting context.
- Correction: local dates win only when they match the authenticated document
  current/comparative axes. A missing local match may inherit the document
  current period only for one unique full-PDF family region containing exactly
  one table; multi-table/comparative regions still require local disambiguation.
- Regression gate: a regulation date must never become a source period; a
  unique single current table may inherit, while two undated candidate tables
  must remain unresolved.

### F-032 — Choosing the shortest fragment of a wrapped row label

- Observed failure: VIB's external-state label spans three lines. Keeping only
  the first recognizable fragment shifted its last numeric cell into the next
  combined-state row and produced ten cells for a nine-column table.
- Root cause: “shortest recognized label window” was used without considering
  the numeric row boundary.
- Correction: extend label fragments until an intervening horizontal numeric
  band is encountered; that band terminates the label and prevents consuming
  the next accounting row. Bind values to the completed label y-span.
- Regression gate: a three-line label followed by a sparse numeric row and an
  adjacent two-line label must retain both rows and their exact denominators.

### F-033 — Pulling a neighbouring total into the next row by bbox tolerance

- Observed failure: on VIB's comparative page, the preceding row's rightmost
  total ended only two pixels above `Tổng tài sản`; bbox tolerance produced ten
  cells for a nine-axis total row.
- Root cause: numeric cells were assigned independently to the nearest label,
  without first reconstructing horizontal numeric bands.
- Correction: cluster candidate cells by y-centre, select one complete band per
  semantic row using label-centre proximity, then align that band to x-axis
  centres. Neighbouring bands cannot contribute isolated cells.
- Regression gate: two rows separated by only 1–2 pixels must retain their own
  denominators, including sparse rows and a rightmost total cell.

### F-034 — Requiring an accounting equation for every directly printed row

- Observed failure: 34 annual interest-rate groups were left OPEN even though
  their source role, axis, geometry, schema binding, pixels, and independent
  numeric challenger were exact; the filing merely omitted a component needed
  to form a corroborating equation.
- Root cause: arithmetic corroboration was treated as the only verification
  path rather than one member of the evidence stack.
- Correction: a directly printed core row may verify from exact semantic role,
  axis, geometry, source numeric challenger, period/unit/scope, and schema
  binding. Require an equation whenever all operands are visibly present; keep
  any nonzero residual OPEN. Never invent a missing operand or implicit zero.
- Regression gate: a direct combined-state row without a separately disclosed
  external row can map, but a row participating in a visible nonzero residual
  cannot.

### F-035 — Letting one empty page abort a complete-PDF family scan

- Observed failure: the annual-2025 semantic index contains a page with no
  authenticated line axis; liquidity-risk detection called `max()` on that
  empty page and aborted before scanning the remaining report.
- Root cause: the family matcher assumed every PDF page had at least one OCR
  line, even though blank/image-only pages are valid complete-document input.
- Correction: treat an empty page as having no row roles and no header axes.
  It contributes neither a complete nor a near candidate, while later pages in
  the same PDF remain eligible.
- Regression gate: an empty page before a unique complete table must not alter
  the table identity, page sequence, or uniqueness result.

### F-036 — Parsing each fragment of a multi-level header independently

- Observed failure: five annual liquidity tables had eight repeated numeric
  columns, but the matcher recovered only five or six axes. Header cells such
  as `Từ trên / 3 tháng / đến 12 tháng` were split vertically, while
  BID/VIB merged `Trên 3 tháng` and `Đến 3 tháng` into one OCR line.
- Root cause: each OCR fragment and bbox was treated as a complete semantic
  header cell. Fragments were misclassified as overdue axes, and a merged bbox
  was assumed to represent one physical column.
- Correction: compose the complete geometric header surface, recover every
  compatible semantic axis, and allow a merged line to nominate multiple axes.
  The mapping stage must later bind those roles to distinct repeated numeric
  x-centres; header bboxes alone never determine the denominator.
- Regression gate: all eight annual reports must expose the same eight
  accounting maturity roles, while nearby interest-rate tables remain negative
  controls and every PDF retains exactly one liquidity region.

## Maintenance checklist

- Add a new `F-xxx` entry whenever a corrected failure is discovered.
- Link the regression test or runbook in the implementing commit.
- Update `COMPLETED_TM_FAMILIES.md` and `UNRESOLVED_MAPPING_LEDGER.md` only from
  replayed family outputs, never from this ledger.
- Before changing a generic parser or schema projection, replay all previously
  accepted annual-2025 and Q2-2026/VPB-Q1-2026 fixtures to detect regressions.
- A fixed failure remains documented even after all tests pass.
