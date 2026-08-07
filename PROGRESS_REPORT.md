# Progress report

- Updated: 2026-08-07T15:11:21+00:00
- Branch: `codex/rebuild-bootstrap`
- Latest clean semantic-evaluation mechanism checkpoint:
  `e1d3f6bbd5c7c23f7c9bd48bf7292d975abdbcc7`. Formal post-seal E-0036 Qwen
  reviewed-evaluation artifact SHA-256 is
  `d0be37a35d43091f8bd9575893e713b603877f3ea517597a3c0f6a5481e0382d`:
  zero of 64 outputs are valid semantic proposals, all 64 exhaust the token
  budget, mapping is not run, and the exact pinned configuration is rejected.
  This does not establish a conclusion about the Qwen model family.
- Latest clean numeric capture base: `278e1ed`; corrected row-grid seal:
  `198c5d8`; E-0021 clean evaluation base:
  `c32741a217ca16e7224d416b2c14245f580e610d`
- Hardware: NVIDIA GeForce RTX 4090 (24,564 MiB, compute capability 8.9); 62 GiB RAM
- Runtime state: `LOGIC_DEVELOPMENT_INFERENCE_PASS_NOT_PRODUCTION_APPROVED`
- Registered schema rows: 1,593 (CDKT 77; KQKD 24; LCTT 107; TM 1,385)
- Registered PDFs: 2,567
- Latest full regression including multi-signal discovery v4, fixed-grid
  semantic fusion, E-0029/E-0030 controls, immutable V4 note-row splitting,
  corrected-grid E-0034 numeric verification, R-0001 recovery verification and
  the hardened E-0036 Qwen reviewed-evaluation/session-backup controls: 558
  passed, 2 intentionally skipped historical/external replays in 99.60
  seconds; Ruff
  check, targeted format checks and `git diff --check` passed.
- New-VPS recovery: the historical E-0027 batch manifest was not present in the
  2026-08-06 S3 snapshot and could not be found in Git, S3 versions or GitHub
  artifacts. R-0001 transparently reproduces the exact source/render/OCR and V3
  discovery evidence while retaining the original manifest as `NOT_RECOVERED`.
  The exact 125-package runtime and two PP-OCRv6 weights were rebuilt; stable
  nine-page OCR metrics are identical, and pages 3–4 become byte-identical to
  their historical OCR hashes after changing only the seven-byte-longer
  `input_path` provenance. Three historical Codex-session archives restore by
  hash but are security-quarantined because session content captured a GitHub
  credential; V2 now scans and locally verifies before any S3 call. All 61
  R-0001 generated artifacts are now protected by a
  parent-linked bounded S3 artifact snapshot with a complete download/restore
  pass and a successful no-overwrite hydration probe. See `RECOVERY_AUDIT.md` and
  `docs/recovery/R-0001-e0027-functional-reproduction.json`.

## Accuracy focus and measurable state

- Main baseline error class was `STRUCTURAL_ROW_CELL_RECONSTRUCTION`: E-0017 had
  42 direct impact units from 7 non-`MATCH` units, 14 missing cells and 21
  structurally damaged compared cells. E-0019 reduces that class to zero on its
  two-page target; the six-page E-0010 v2 replay also reduces structural and
  numeric/sign impact to zero. E-0021 removes all four retrieval-key semantic
  disagreements on the six-page E-0010 replay. Its remaining measurable class
  is source-exact Vietnamese orthography/wording: 32/140 labels still differ
  after casefolding, without numeric or structural impact.
- Baseline before the current change remains E-0010: 140 Role A rows versus 139
  Role B rows; financial-row/cell coverage 94.70%; conditional exact row/cell
  agreement 96.80%/97.60%; strict exact row/cell agreement 91.67%/92.42%.
- Current logic being improved: canonical row/cell reconstruction on the newly
  located MBB CDKT pages, followed by semantic labels, inherited continuation-
  page period axes and localized numeric rereading only for unresolved cells.
- New before-result from E-0017: 147 Role A versus 146 Role B rows; row/cell
  coverage 94.964%; conditional exact row/cell agreement 90.9091%/91.2879%;
  strict exact row/cell agreement 86.3309%/86.6906%. The first four pages have
  206/206 exact financial cells; all material loss is localized to the first
  dense LCTT page; these figures remain the frozen whole-suite before-result.
- New bounded after-result from E-0018 on that predeclared dense LCTT page:
  DeepSeek-OCR-2 plus one explicit adjacent label-only/value-only fragment merge
  reconstructs 33/33 rows, covers 58/58 financial cells, and exactly agrees
  with all 58/58 machine-reference numeric/sign cells. Strict exact cell
  agreement rises from 36.2069% to 100%; strict exact financial-row agreement
  rises from 34.4828% to 100%; invalid cells fall from 12 to zero, and measured
  structural impact falls from 41 to zero. This is target-page calibration
  against a native machine reference, not human-gold or end-to-end accuracy.
- New formal E-0019 result for fixed-grid fusion on E-0017 pages 13→14:
  independent PP-OCRv6 reconstructs 41/41 Role A rows and exactly agrees on
  72/72 financial cells with zero invalid cells. DeepSeek proposes 42 semantic
  rows because one wrapped label on page 14 is split and the next value is
  shifted upward. A fail-closed dynamic program now resolves the verified
  3-semantic-row→2-geometry-row pattern to 41 canonical rows. All final cells,
  notes, geometry source IDs and row count remain object-identical to PP-OCR;
  DeepSeek supplies only Vietnamese labels and reading-order evidence. This is
  still calibration against machine Role A, not human gold. Across both pages,
  financial row/cell coverage improves from 80.5556%/80.5556% to 100%/100%,
  strict exact row/cell agreement improves from 47.2222%/48.6111% to 100%/100%,
  invalid cells fall from 12 to zero, and structural impact falls from 42 to
  zero. The remaining main class is one Vietnamese label disagreement.
- New formal E-0020 six-page generalization result on E-0010: ordered label segmentation v2
  handles the reverse failure mode where one semantic row contains two accounting
  labels. It expands four 1→2 collapsed labels, contracts one 2→1 wrapped-label
  pair, accepts two label-empty displaced-value rows only after exact numeric
  fingerprint checks, and trims one duplicated edge fragment with a decisive
  score margin. Against the unchanged 140-row Role A denominator, row/cell
  coverage rises from 94.6970% to 100%, strict exact financial row/cell agreement
  rises from 91.6667%/92.4242% to 100%/100%, and invalid cells fall from one to
  zero. Semantic-key labels are 136/140; the four remaining disagreements are
  Vietnamese OCR substitutions, not table or numeric errors. E-0020 is bound to
  the unchanged E-0010/E-0011 Role A/B/C seals and was evaluated from clean
  commit `21d39cc5fbcb0d0411e08d8d61cd0b8df5aecaf3`.
- Formal E-0021 Vietnamese correction replay: a statement-scoped, proposal-only
  layer uses append-only template vocabulary, Damerau edit distance, decisive
  full-label margins, repeated evidence from other document rows, candidate
  support dominance, protected Vietnamese function words and immutable row
  order. It proposes changes for exactly the four E-0020 semantic-key residuals
  and no other row. All four proposals agree with Role A, raising semantic-key
  label agreement from 136/140 to 140/140 and case-insensitive source-exact
  label agreement from 104/140 to 108/140. Raw labels remain separately retained;
  the layer contains no numeric/note fields and has no output, mapping, period,
  scope or confidence authority. This is still a calibration replay, not
  human-gold or holdout evidence. The artifact SHA-256 is
  `accefa38db2131ebf5b0aa9fa37394d382fe0c98cbcfa6358ef304c0d626ba9a`
  and binds the run to clean commit
  `c32741a217ca16e7224d416b2c14245f580e610d`.
- New mapping-development result targets
  `ROW_WISE_FORCED_DUPLICATE_MAPPING`. On the bounded six-visible-row/
  three-applicable-schema fixture, independent label top-1 at the same 0.35
  retrieval gate assigns all six rows, producing 3 correct pairs, 3 false
  positive extra-row mappings, 50% precision and three duplicate schema
  assignments. Ordered SchemaGraph v1 selects exactly the expected 3/3 pairs,
  retains all three extra PDF rows, produces no duplicate assignment, and has a
  best/runner-up path score of 6.09/4.66 (margin 1.43). This is deterministic
  logic-development evidence, not a real-document or human-gold accuracy claim.
  E-0023 now seals this result from clean commit `48043d0`; artifact SHA-256 is
  `87121a2eee5e29213e06c43bcd92db14d62291fbf79afced7f5c9eec90ae5bd1`.
- New untouched E-0022 Role B result: preprocessing covered 33/33 pages at 300
  DPI and hash-verified 70 render/variant artifacts. Full-document PP-OCRv6
  completed 33/33 pages with 2,477 lines, 24,299 word tokens, mean line score
  0.950141, 214 lines below 0.8 and 1,420.994 seconds of page inference. The
  frozen locator correctly abstained with zero candidates and zero
  mapping-eligible pages. Main observed error class is
  `STATEMENT_DISCOVERY_TITLE_ANCHOR_VARIANT`: title scores on the apparent main
  statement starts are just below the frozen 0.74 gate (approximately
  0.720/0.696/0.722), while OCR emits form variants `B02a/B03a/B04a` that do not
  exactly match the frozen `B02/B03/B04` anchors. This is diagnosis only; no
  threshold or page selection was changed and no semantic reader was invoked.
- E-0022 Role A was hydrated only after the Role B seal was committed and
  pushed. The exact 33-page searchable PDF has native text on all 33 pages and
  pairs visually one-to-one with Role B on all five target main-statement pages
  (Role A/Role B pages 3/3, 4/4, 6/6, 7/7 and 8/8; visual similarities
  0.935386–0.973479 with margins 0.534691–0.695877). A post-seal page-scope
  machine diagnosis identifies two independent losses: the frozen matcher finds
  only 2/5 target pages even on exact native titles, and scan OCR removes those
  remaining two, so Role B has 0/5 correct mapping-eligible statement pages.
  Three pages are matcher/header-family failures and two additional pages are
  OCR-title degradation failures. This classifier was created after Role A
  access and is diagnostic evidence only, not human gold, an after-result or
  permission to retune E-0022. The Role A page-reference and one-shot comparison
  artifact SHA-256 values are respectively
  `e9c14d49ba30451aaebdfb8f8632bc342f58517c6bf1e4ba29d892366706fcba`
  and `f47036761c4d00c5d4b7734a9e1183f9146be5fead604b9e08e9de0c4efd3234`.
- Preliminary header-candidate/text-quality v2 development is isolated from
  E-0022. It is not the final page classifier: form/title matches now serve only
  as candidates for the multi-signal document classifier being built. A
  synthetic optional-suffix/long-title mutation moves from v1 `UNRESOLVED` to a
  v2 ordered block with 5/5 expected eligible pages and the one off-balance page
  still excluded; malformed/conflicting forms, narrative title mentions and
  wrong order still abstain. On the unchanged real E-0013 MBB/VCB calibration
  OCR, v2 reproduces all 11 eligible pages, both off-balance exclusions, both TM
  boundaries and both DIRECT decisions exactly. Across the three registered
  ACB/MBB/CTG human-review calibration PDFs (155 total pages; six with native
  words), v1 marks two legitimate cover pages corrupt while missing a different
  truly corrupt page; v2 removes both the ACB and MBB cover false positives
  caused by legitimate `Â`/`Ã`, and detects the separate MBB page containing ten
  real U+0086–U+008C controls. This is calibration/mechanism
  evidence, not holdout or end-to-end accuracy.
- New multi-signal discovery v3 development result: 12/12 focused tests pass.
  A lone CDKT title, a lone TM title, semantic text without PP-OCRv6 numeric
  geometry, incompatible neighbor axes, mismatched neighbor periods and two
  equal complete document paths all abstain. Multi-line headings, a complete
  five-signal statement page, and one-page forward/backward inference with
  visible accounting rows plus aligned axes/table edges pass. Inference is
  sourced only from a locally accepted adjacent page and cannot chain.
- On the unchanged E-0013 MBB/VCB calibration batches, v3 exactly reproduces all
  11 mapping-eligible statement pages, both off-balance exclusions, both TM
  boundaries and both DIRECT decisions. MBB is CDKT 10–11, excluded 12, KQKD
  13, LCTT 14–15, TM 16; VCB is CDKT 8–9, excluded 10, KQKD 11–12, LCTT 13–14,
  TM 15. Both best/runner-up document-path margins are 8.5. The period matcher
  pairs reporting axes to nearby unit lines, retaining 2025/2024 and excluding
  the form-boilerplate 2014 date. This is calibration, not holdout evidence.
- E-0024 input selection is now fixed before challenger inference: 37 visible
  single-line crops from MBB/VCB cover statement/notes titles, section/method
  headings, ordinary and duplicate labels, and off-balance title/label controls.
  The registry binds both source PDFs, 14 renders, 14 PP-OCRv6 JSON files, every
  line index/bbox/raw prediction, and source-visible transcription by SHA-256.
  Its three focused tests pass and an independent real-artifact audit reports
  zero source/render/OCR/bbox/text drift. The pre-inference registry was pushed
  at `1d46626`; 37 crops were then built and representative title/long-label/
  off-balance crops were visually checked for clipping or neighbor leakage.
- The official VietOCR 0.3.13 wheel, two upstream configs and
  VGG-Transformer weight are now installed in an isolated exact-hash overlay.
  The 151,815,373-byte weight SHA-256 is
  `380512193a8b6cbf6fad80deacdc9b6939d10d473d199892fc6408d13775ea59`;
  no base environment changed. Seventeen focused tests lock reference-blind
  request fields, artifact/safety policy, CER/WER/edit categories, suffix
  truncation and the adoption gate. These pre-inference mechanisms were pushed
  at `c351c70` after the full regression passed.
- Formal E-0024 reference-blind inference is complete on the unchanged 37-line
  crop set. PP-OCRv6 baseline: 0/37 source-exact lines, 186 character edits,
  CER 14.9518%, WER 55.2448%, and 0/10 exact titles. VietOCR: 30/37
  source-exact lines, 8 character edits, CER 0.6431%, WER 2.7972%, and 6/10
  exact titles. Both have zero empty/suffix-truncated lines, so all three
  predeclared adoption gates pass. A diagnostic accent-insensitive retrieval
  key comparison is 11/37 for PP-OCRv6 versus 37/37 for VietOCR; it did not
  participate in the adoption gate.
- E-0024's remaining class is narrow: 8 substitutions across 7 lines, comprising
  7 diacritic-only differences and one capitalization difference, with zero
  base-character substitutions, insertions, deletions or truncations. Confidence
  overlaps correct lines, so raw output cannot be auto-promoted from probability.
  The artifact SHA-256 is
  `18b896f7174992dd16a4372a5c24ec46df967e763223b9c85b25919ca5e89289`.
- The reader decision is now explicit: PP-OCRv6 detection is source-space
  geometry authority; DeepSeek-OCR-2 is the primary Vietnamese recognizer on
  bounded title/line/logical-row crops; numeric/sign/dash cells follow an
  independent verification path. VietOCR remains a frozen-crop benchmark
  challenger only, not a planned production component. `PP-OCRv6-VI-BCTC`
  fine-tuning is deferred behind an end-to-end material-error gate.
- A model-neutral fixed-grid semantic adapter and a reference-blind batched
  DeepSeek line runner are implemented pre-inference. The adapter accepts at
  most four exact PP source lines, derives only their union box, preserves raw
  text/crop/reader output, rejects numeric/period/unit/sign fields, accepts only
  source-verified form-code families, rejects truncation/layout serialization,
  and ignores reader probability for promotion. Its 14 tests plus 14 DeepSeek
  request/parser/config tests pass. The mechanism was frozen and pushed at
  `a44b08b` before the first DeepSeek line output.
- E-0025 rejects the first direct-resize DeepSeek line configuration. On the
  unchanged 37 crops it produced 0/37 exact lines, 0/10 exact titles, CER
  123.7138%, WER 125.8741%, seven structural rejections, and seven empty
  evaluation predictions versus PP-OCRv6 CER 14.9518% and VietOCR-challenger
  CER 0.6431%. Wall time was 263.6341 seconds and peak allocated VRAM
  7,121.935 MiB; one 30-pixel-high crop generated 36,314 characters and consumed
  199.871 seconds. No proposal is integrated into locator or mapping.
- The observed root cause is bounded and implementation-specific: v1 used
  `crop_mode=false`, whose official custom code stretches every 98–616 by 27–35
  pixel crop to 768×768, and the upstream decoder requested 8,192 new tokens.
  E-0026 reused identical crop pixels with the official aspect-preserving
  `ImageOps.pad` path plus a fail-closed 128-token/512-character budget.
- Formal E-0026 result: DeepSeek v2 produces 27/37 exact lines and 5/10 exact
  titles, CER 0.9646%, WER 3.8462%, zero empty/truncated/structurally rejected
  outputs, 23.1651 seconds wall time and 7,058.903 MiB peak allocated VRAM. Its
  19 MBB and 18 VCB source-bound proposals produce zero fusion rejection and
  preserve every E-0013 page/type/scope/off-balance/continuation/DIRECT decision
  plus both 8.5 runner-up margins. The configuration passes only the bounded
  semantic-proposal gate; schema mapping and Excel are not yet evaluated.
- VietOCR remains the optional challenger even though its same-crop calibration
  metrics are slightly better (30/37 lines, 6/10 titles, CER 0.6431%). There is
  no bank/period-separated downstream result that permits production adoption.
  `PP-OCRv6-VI-BCTC` fine-tuning remains gated and has not started. E-0022 was
  not read, rerun or retuned. E-0026 artifact SHA-256 is
  `1753f382e141fbeb48e94cb1ef30a89ebd08cb2f1bb0836bdbf960e811eb33dd`.
- E-0027/E-0028 isolate and resolve the next end-to-end locator error class,
  `EMBEDDED_ACCOUNTING_ANCHOR_WHOLE_LINE_DILUTION`. On the frozen MBB Q1/2026
  pages 1–9, V3 correctly accepted CDKT pages 3–5 (page 5 off-balance), KQKD
  page 6 and LCTT pages 7–8 locally, but returned `UNRESOLVED`, zero complete
  paths and zero mapping-eligible pages because notes page 9 had only 1/2
  recognized anchors. V4 adds only a bounded contiguous order-preserving token
  window for accounting-row anchors; all other header, period, geometry,
  narrative, sequence and acceptance gates are unchanged. It recognizes the
  OCR-damaged embedded phrase `thành lập và hoạt động` at 0.926829, raises page
  9 to 2 anchors, and produces the exact complete block CDKT `[3,4]`, excluded
  off-balance `[5]`, KQKD `[6]`, LCTT `[7,8]`, TM boundary `9`, with runner-up
  margin 8.5. Frozen MBB 2025 and VCB 2025 replays are structurally identical
  before/after. This is locator calibration, not table/value/mapping/Excel or
  holdout accuracy. E-0027 V3 and E-0028 artifact SHA-256 values are
  `9ccfd0faf869adee4cb885a4a87a32c86354101e82adc1d62c32e4ce7e9089c8`
  and `4c6e644f4f764d08b4c4dae580e49bfee50b3efeadedede668436e3b8d6d396a`.
- E-0029 isolates the next error class,
  `STAGGERED_HEADER_AND_NOTE_AXIS_ROW_RECONSTRUCTION`. The unchanged V2 parser
  fails closed on both accepted MBB CDKT pages because the two visible period
  headings are vertically staggered. Reference-blind V3 permits only a bounded
  1.25-line-height header stagger, excludes stacked note/unit/audit companions,
  recognizes Roman/OCR-confusable note references only at the note axis, and
  filters vertical rules before dash-component uniqueness. It reconstructs
  38 rows/76 cells on page 3 and 25 rows/50 cells on page 4; every row has two
  cells, with zero invalid cells, duplicate source-line assignments, header
  leaks or note-prefix leaks. Page 3 has 72 `VALUE`, 1 `DASH` and 3 `BLANK`
  cells; page 4 has 42 `VALUE`, 2 `DASH` and 6 `BLANK` cells. One page-4 mark
  remains explicitly unassigned within the predeclared bound. Page 5 remains
  excluded. This is geometry calibration only: period roles, unit semantics,
  numeric truth, labels, schema IDs, validation and Excel were not invoked.
  Artifact SHA-256 is
  `affe74a243e342b56c4ead2fac984f10d9a1f42378823b50ccdde8946eeed373`.
- E-0030 closes the next bounded metadata gap,
  `NO_WORD_BOX_VISIBLE_HEADER_BINDING_CONTRACT`. The before-state resolves 0/4
  word-box axes. The after-state resolves 4/4 on MBB CDKT pages 3–4 from local
  visible headers: both pages bind `31/03/2026` to `CURRENT` and `31/12/2025`
  to `COMPARATIVE`, with `SNAPSHOT` semantics. Raw OCR unit `triu đồng` is
  retained while the bounded unit proposal resolves `VND × 1,000,000` at
  similarity 0.947368 and distinct-semantics margin 0.315789 on all four axes.
  Both table maps use `LOCAL_VISIBLE_HEADERS`; propagation issues are zero and
  continuation inheritance is not invoked. Numeric cell text/magnitude,
  horizontal position, history, review, schema and page 5 are not decision
  features. Artifact SHA-256 is
  `3e0e6888802fc190879f360cf8c679f1cefb334e9188b4baec05a668fee12577`.
- E-0031 closes the next bounded verification gap,
  `SINGLE_READER_NUMERIC_CELLS_NOT_INDEPENDENTLY_VERIFIED`. The fixed E-0029
  grid yields 126 isolated source-pixel crops: 114 primary `VALUE`, three
  pixel-supported `DASH` and nine `BLANK`. The pinned digit-specific
  `en_PP-OCRv5_mobile_rec` reader processed all crops in one CPU-FP32 model
  session and 11.938103 seconds. Exact normalized value and sign agreement is
  111/114; dash plus independent pixel agreement is 3/3. Thus 114/117 observed
  cells are independently verified (97.4359%). The three disagreements retain
  both reader proposals with no selected value; all nine blanks remain
  unresolved pending row semantics. Automatic overwrite, reader-probability
  acceptance and blank-to-zero/value promotion are all zero. This is bounded
  calibration evidence, not human gold or end-to-end accuracy. Artifact SHA-256
  is `27561d0975d6e9d1e59b61f3b7dbd838ef1a91864f9f5955f87a6807033b6d9a`.
- Logical-row crop preparation exposed a structural residual before DeepSeek
  inference: one E-0029 row contained two independent label lines. The first
  label had note `III.18` one full line above the valued anchor and had its own
  two visible dashes; V3's broad structural tolerance merged it with the next
  `Cho vay khách hàng` row. E-0033 isolates a relative-geometry V4 correction:
  a note more than 0.5 median line-height from a value anchor forms an independent
  row only when label lines partition geometrically around both anchors.
  Page 3 moves from 38 rows/76 cells to 39/78; page 4 remains 25/50. Exactly one
  five-source-line composite becomes two disjoint rows, all 62 common rows are
  object-identical, all 204 source lines remain covered, the valued replacement
  preserves its old cells exactly, and the new row has 2/2 pixel-supported
  `DASH` observations. E-0032 measured the same delta but is retained as
  superseded because its first implementation modified the hash-locked V3 file.
  E-0033 restores V3 SHA-256
  `e5650bd48866340cec32ed41e8b131cdf8289c25479be43a11c29763ea153663`
  and keeps all V4 code isolated. E-0033 artifact SHA-256 is
  `d9c0ecf44f6a0f652e6c991d3ab95b7ab0e821068366764e39a3f0de7f0711fb`.
  E-0031 remains valid only for its original 126-cell denominator and cannot be
  treated as complete numeric verification of the corrected 128-cell grid.
- E-0034 completes the corrected-denominator replay. Crop V2 adds a white bottom
  canvas of 0.27 line-height only when immutable source `value_line_indices`
  exist; on these pages that is 12 pixels for exactly 114 `VALUE` cells. All
  five pixel-supported `DASH` and nine `BLANK` crops remain unpadded. The clean
  CPU-FP32 reader processed 128 crops in one model session and 12.124202 seconds.
  Exact value/sign agreement is 113/114 and dash agreement is 5/5, so 118/119
  observed cells are independently verified (99.1597%). One `2.320`/`.20`
  disagreement abstains with neither proposal selected; all nine blanks remain
  unresolved pending row semantics. Automatic overwrite, reader-score
  acceptance and blank promotion are zero. All predeclared gates pass. Artifact
  SHA-256 is
  `08ecf8823154df415cc4f5bcbe65c5697412605eadc1a41f22315990ea20cc70`.
- E-0035/E-0036 now complete the fixed-input and two-baseline semantic sequence.
  E-0035 froze 64 unresized source-pixel label crops: 39 on page 3 and 25 on
  page 4. VietOCR and DeepSeek-OCR-2 then read the identical reference-blind
  request at SHA-256
  `ad4c1a9fecf9686249a9c4eea2a5b6a2a903fc4716536e5804c481facc217781`,
  and both outputs were hash-sealed before the six reviewed rows were loaded.
  On those rows VietOCR is source-exact on 3/6 and DeepSeek on 1/6; the
  predeclared source-inexact gate therefore returns `RUN_QWEN_SAME_REQUEST`.
- The reviewed mapping result isolates the current structural blocker. Both
  readers' best ordered CDKT paths contain the reviewed ReportNormId on 6/6
  rows, but neither path has a decisive runner-up margin: VietOCR is 0.051282
  and DeepSeek is 0.008494. Both results are `AMBIGUOUS_MAPPING`, automatic
  acceptance is 0/6, and review abstention is 6/6. Qwen may strengthen label
  evidence only; it cannot assign ReportNormId or bypass structural abstention.
- Qwen pre-inference v1 was authorized by a minimal artifact derived from
  reviewed-evaluation SHA-256
  `8ea952bc008d4bf4c274c25299cadb1c624424114be9ea3a38ba9b15d1b1c133`
  while exposing no reviewed label, ID, value or period. It pins
  `Qwen/Qwen3.5-27B-GPTQ-Int4` revision
  `8f0c09f227ae570e79617c6d9172b59df9c16081`, 24 selected artifacts totaling
  30,258,477,628 bytes, official GPTQ Int4, a sealed isolated overlay, the
  unchanged 64-crop request, a 4,096-token context, at most 96 generated tokens,
  deterministic no-thinking decoding, offline inference and an explicit
  38-GPU-layer/26-CPU-layer split. The exact 24 registered artifacts were local
  and hash-verified before the formal run. The run loaded the model in
  238.391 seconds, processed the first crop in 235.437 seconds, used
  15,586.395 seconds total, and peaked at 19,723.647 MiB allocated GPU memory.
- The complete two-file Qwen output was hash-sealed before review access, then
  protected as S3 artifact snapshot
  `20260807T143806Z-e0036-qwen-semantic-reader-34cd996a97d6`; its full restore
  and no-overwrite hydration probe both passed. Every one of the 64 outputs was
  rejected as `REJECT_TOKEN_BUDGET_EXHAUSTED`: each generated token ID 163749
  96 times, producing one identical raw sequence across the full request. Raw
  rejected output was never scored as label text or passed to mapping.
- Post-seal evaluation on the same six pre-existing reviewed rows therefore has
  0/6 valid proposals and 6/6 mapping abstentions. Accepted-only label metrics
  are not scorable; fixed-denominator CER and WER are both 1.0. Mapping status
  is `NOT_RUN_NO_VALID_PROPOSALS`, with no best or runner-up path. The decision
  is `REJECT_CURRENT_PINNED_CONFIGURATION_NO_VALID_SEMANTIC_PROPOSALS`, while
  `model_family_conclusion` remains `NOT_ESTABLISHED`. Outside the formal
  artifact, a separate read-only diagnostic audit found strong evidence for a
  checkpoint/runtime GPTQ-format mismatch; this run neither measures OCR
  quality nor proves that causal diagnosis. Any retry must first pass a short,
  format-pinned canary.

## Completed tasks

- Reviewed the primary Needleman-Wunsch, Zhang-Shasha, Cupid and Similarity
  Flooding work and implemented the relevant constrained form: a hashable
  statement `SchemaGraph` plus bounded k-best monotone DP with PDF/schema gaps,
  mapped parent/sibling/neighbor transitions, optional accounting-semantic
  proposals, distinct runner-up paths and fail-closed cluster abstention. Numeric
  values, history and numeric ReportNormId order are absent from its feature API.
- Added 10 focused ordered-subgraph tests covering 6→3 selection, retained extra
  rows, duplicate labels, verified-parent dominance over a wrong semantic score,
  tie abstention, non-numeric workbook order, numbering, off-balance exclusion,
  exhaustive-only `NOT_OBSERVED`, and the real 77-node CDKT hierarchy graph.
- Captured E-0023 without reading any source document, OCR artifact, Mongo value
  or E-0022 holdout evidence. Besides the 6→3 delta, it proves zero-margin tie
  abstention, verified-parent dominance over an adversarial semantic proposal,
  exact off-balance exclusion, 77 real CDKT graph nodes, fixed-asset parents
  4328/4329/4330, TM 1944 presence and zero production-confidence promotion.
- Sealed and pushed the E-0023 artifact plus immutable integration hash gate at
  `0a14d37`; the full regression is 275 passed with 2 intentional historical
  replay skips.
- Sealed E-0022 source roles and the frozen code/config/model/schema identities
  before either ACB Q1/2026 holdout source was locally present. The pre-access
  artifact was captured from clean commit
  `d56a86a837a1e6a1d1318cd73dbba7bee888d515`, records both sources absent,
  permits only Role B hydration next, and forbids Role A access before the Role B
  result is sealed. Artifact SHA-256:
  `33c296c0cc2e0d2bd3a54a2d6835b6eea8c634a6a626f7de5ca1b0940c786b4c`.
- Hydrated only the exact E-0022 Role B scan from the immutable S3 manifest and
  verified its registered SHA-256, 8,027,105-byte size and 33-page count. The
  first five pages have no PDF text layer. Role A remains locally absent and no
  statement page has been selected from Role B content.
- Captured the pre-preprocessing execution-control artifact from clean commit
  `cf83314391e1cb94669481acc48bca2d12535579`. It proves the exact Role B source,
  full-document/300-DPI policy, absent Role A logical/immutable/output paths,
  absent Role B output root, and byte identities for 11 execution runners plus
  the 24 previously frozen pipeline/schema files. Artifact SHA-256:
  `c56721c3164c42e5ddd869778134b0196a914d04144b7a591524b0a6bc200d81`.
- Completed E-0022 Role B preprocessing and full-document PP-OCRv6 discovery.
  All 33 page checkpoints and their identity/hash chains passed a real resume
  verification. The preprocess manifest SHA-256 is
  `10bb4f544d21bcd0f633189e8b7ff715a0869453ca31d27d1446d4bcaa03272b`;
  the final batch manifest SHA-256 is
  `462e23dae7581043362dd577917e1ce10d00f56dc216b67e16fba895a08c7c64`.
- Sealed the exact E-0022 Role B unresolved outcome from clean commit
  `d8daad3f2976ae474e16ae50076aac860f43f7d8`. The seal binds 108 artifacts and
  two verified PP-OCRv6 weight files; records 33/33 OCR pages, zero candidates,
  zero mapping-eligible pages, zero semantic-reader/downstream/history use and
  absent Role A; and permits Role A hydration only after this point. Seal
  SHA-256: `41ef962361cfead7cdfa4d7b8a782e61ab3fc4a938aa4fa86ebb45cbe637660e`.
- Committed and pushed the Role B seal artifact/integration checkpoint as
  `a1b76f2`. Only then was the exact Role A searchable source hydrated; its
  registered SHA-256, 1,060,293-byte size and 33-page count verify.
- Captured the post-seal Role A statement-page reference and one-shot comparison
  from clean commit `08dec6cada1f0237109c9c4e303061c4ddab2d9b`. They bind the
  five accepted pixel-only target pairs, page 5 off-balance exclusion, DIRECT
  LCTT on pages 7–8, the unchanged frozen locator outputs and all source/config/
  implementation hashes. The comparison records 0/5 Role B versus 2/5
  exact-native frozen-locator recall, zero false-positive eligible pages, no
  Role B rerun, no threshold/page tuning and no history or mapping use.
- Committed and pushed those E-0022 artifacts plus their immutable integration
  hash gate as `267bee8`; the complete suite was 288 passed with two intentional
  historical skips.
- Built reproducible bootstrap, GPU runtime, package/model hashes, source registry,
  dataset-role registry, backup/restore checks, and server rebuild documentation.
- Restored and audited `financial_20_02_2022.gz` as a read-only MongoDB historical
  weak reference: 112,147 cells across 27 banks. History is never permitted to
  override visible PDF evidence, table periods, hierarchy, or scope.
- Preserved all supplied template workbooks and built a schema graph. A
  `ReportNormId` is an identity only: ordering is always the row/display order in
  the relevant workbook. Numeric magnitude or numeric sorting is prohibited.
- Resolved Q-BOOT-001 by workbook position: template-order block 4155→4168 is
  INDIRECT and 4104→4116 is DIRECT. These are not numeric ranges.
- Implemented ordered statement location, off-balance-sheet exclusion,
  continuation boundaries, two-reader structural comparison, independent word-box
  geometry, strict financial-cell parsing, visible-dash recovery, and targeted
  source-PDF rereading at 450/600 DPI.
- Completed and hash-locked E-0010 through E-0015 calibration regressions. E-0015
  keeps page boundaries hard, excludes the two off-balance pages, and retains all
  reader disagreements instead of converting agreement into truth.
- Ingested the authoritative 2026-08-06 CTG/ACB/MBB human review as a hash-bound
  30-decision calibration registry. Added table-level period propagation,
  `OBSERVED_VALUE`/`OBSERVED_ZERO`/`NOT_OBSERVED`/scope/ambiguity statuses,
  raw-plus-normalized values, hierarchy-first mapping, and display-order sequence
  validation.
- Verified that external off-balance IDs 5701–5711 do not collide with or belong
  to the current target balance-sheet templates. ID 4337 is `NOT_OBSERVED` in the
  cited CTG section; the visible XDCB row maps only to 4373.
- Committed and pushed the latest correctness checkpoint as
  `8c2f7fb feat: seal targeted reread reader evidence`.
- Generated the formal E-0016 artifact from clean commit `8c2f7fb`. It verifies
  15/15 original-crop reader runs and a 52-file output set while retaining one
  unresolved table, one no-table crop, 14 invalid VLM cells, both full-table row
  count disagreements, and all no-selection/no-mapping safety flags.
- Committed and pushed the E-0016 replay/integration checkpoint as `70fefa9`;
  the full suite is 208 passed with 2 intentionally skipped historical replays.
- Reviewed DeepSeek-OCR-2, Microsoft TATR, IBM TableFormer, and ClusterTabNet
  against official papers/repositories, exact available weights, licenses,
  runtime compatibility, and the observed E-0016 failures. Selected TATR as the
  first structure-only addition and DeepSeek-OCR-2 as the next isolated semantic
  reader benchmark; TableFormer is the challenger and archived ClusterTabNet is
  a custom-graph research reference.
- Added a hash-pinned TATR downloader, no-network/clean-Git structure runner,
  all-query/source-box evidence representation, candidate-policy configuration,
  and 8 focused passing unit tests. The full regression is 216 passed with 2
  intentional historical skips. The mechanism commit itself preceded the model
  download so its source/config state remained independently reviewable.
- Downloaded and independently verified the 115,514,291 required TATR artifact
  bytes in the ephemeral model cache. The first clean load attempt stopped
  before inference because Transformers 5.14.1 rejects the checkpoint's legacy
  `dilation=null`; no partial result directory was published.
- The corrected dirty development smoke now completes actual GPU inference in
  0.187929 seconds with 249.096680 MiB peak allocated VRAM. It retains all 125
  queries and reports 36/30/23 row boxes at thresholds 0.5/0.7/0.9; no threshold
  is selected from these counts. This is mechanism evidence, not a formal run.
- Committed and pushed the exact-version TATR compatibility checkpoint as
  `8dd5422`; Ruff and all 216 tests passed with two intentional historical skips.
- Validated the user-supplied `s3://test-s3-duylv/` target through the existing
  `bctc-backup` AWS profile. It is in `us-east-1`, defaults to AES-256 server-side
  encryption, and blocks all public access.
- Q-BOOT-005 was approved. Enabled bucket versioning and verified `Enabled`;
  default AES-256 encryption and all four public-access blocks remain active.
  Object Lock was not enabled and the bucket reports no Object Lock configuration.
- Inventoried the off-machine snapshot scope: 2,567 registered PDFs plus source
  acquisition metadata, all generated output, the 526,178,025-byte Mongo dump,
  the 17,838,080-byte accepted DuckDB, a control-plane archive, and a Git bundle.
  The initial content-addressed snapshot will contain about 18.6 GB before
  content deduplication.
- Committed and pushed the S3 snapshot/offload/hydration mechanism as `3e07735`.
  Its regression passed 222 tests with two intentional historical skips; it
  rejects unversioned buckets and keeps offload dry-run by default.
- Q-BOOT-004 is implemented. Appended TM ReportNormID `1944 — Cho vay giao
  dịch ký quỹ và ứng trước tiền bán chứng khoán` as the final workbook-order
  row after 1943. The source workbook changed from SHA-256
  `6af23d7bf930fe6db7cbfb83df78c7c7ab876142757d1dde5707c1667b54a8a0`
  to `fa284e3af1f90c8a206308f63e6d35e77a9fbf1abcaf60abcb59877c47275140`.
- The append audit proves all 1,384 existing TM ID/name/order mappings are
  byte-semantically unchanged. Only `xl/worksheets/sheet1.xml` and
  `xl/sharedStrings.xml` changed; all eight other XLSX members retain their
  original SHA-256. No `vst_level` hierarchy workbook was modified and no
  unsupported parent was inferred for 1944.
- Added a schema-coverage contract derived from workbook display order. Role A,
  Role B, Excel output, evaluation, and mandatory search each contain all 1,593
  IDs and end with TM 1944. Mandatory search fails unless both roles record
  exactly one terminal outcome for every template ID; `NOT_OBSERVED` remains
  distinct from zero.
- Rebuilt the historical weak-reference registry against the 1,593-item graph.
  Its 112,147 cells remain unchanged in authority and contain zero historical
  rows for 1944; all no-map/no-promote gates and the current graph hash verify.
- The complete Q-BOOT-004 regression passed: 226 tests, two intentional
  immutable-historical replay skips, Ruff clean, and `git diff --check` clean.
- Committed and pushed the append-only schema checkpoint as `4a469fa`; TM 1944
  is present in Role A, Role B, Excel output, evaluation, and mandatory search.
- Selected the next Role A/Role B expansion strictly from filename metadata
  before content inspection and froze both TCB 2024 consolidated documents as
  `CALIBRATION`. The searchable file is a 90-page native-text Role A source and
  the scan is a 93-page image-only Role B source.
- Pixel-only ordered pairing accepted 76 page pairs and all six target contracts:
  Role A pages 8–13 correspond to Role B pages 9–14 and cover CDKT, the excluded
  off-balance page, KQKD, and a two-page direct LCTT continuation.
- Added reusable, experiment-independent Role A construction, Role A/Role B
  comparison, strict parser-v2 table handling, metric aggregation, and a direct
  impact error taxonomy. A focused 17-test regression passed; the pairing gate
  reports `PASS_FROZEN_PAIRING_FOUND` with 0 missing target pages. The full
  regression is 229 passed with 2 intentional immutable-history skips.
- Completed and sealed E-0017 Role A and Role B at clean commit `932a481`.
  Role B processed six image-only pages sequentially in 109.336706 seconds at
  3,243 MiB peak GPU memory. The formal comparison is tied to clean correction
  commit `a7306c9`, where multi-number cells are attributed to their structural
  root cause instead of double-counted as digit OCR failures.
- E-0017 keeps all 20 off-balance rows outside target CDKT, accepts the LCTT
  page-13→14 continuation from adjacency/header/axis/unit/period/section evidence,
  and returns cash-flow method `UNKNOWN` because row collapse destroys the
  required ordered direct anchors. It does not guess the method from ID values.
- At model-download preflight, persistent workspace free space was
  5,367,824,384 bytes, which was insufficient
  for the 6,789,163,745-byte pinned DeepSeek-OCR-2 artifact set. `/dev/shm` has
  15,407,611,904 bytes free, so an ephemeral, hash-verified model load is viable
  while retaining a 4 GiB safety reserve. The official 3B BF16 revision and all
  required file hashes are now pinned; the model has no mapping/value/period/
  scope/confidence authority and may run only on failed or ambiguous regions.
- Downloaded and independently verified all 14 pinned DeepSeek-OCR-2 artifacts
  (6,789,163,745 required bytes) into `/dev/shm`; the weight SHA-256 is
  `d8ff67a424ba6f4dd077885eb9d6a05d2537e76fe5491f0e2a9b712f8c8870fa`.
  No source PDF or Mongo dump was deleted. Persistent free space is currently
  4,931,727,360 bytes and `/dev/shm` free space is 8,481,501,184 bytes.
- Confirmed the expected runtime incompatibility instead of hiding it:
  Transformers 5.14.1 cannot import the official custom model because it no
  longer exports `LlamaFlashAttention2`. A hash-locked, external overlay using
  the official Transformers 4.46.3/tokenizers 0.20.3 pair plus
  huggingface-hub 0.26.3 now loads the unchanged model with eager attention on
  the existing Torch 2.12/CUDA 13 Blackwell runtime. The successful load took
  4.255978 seconds, allocated 6,883,116,544 GPU bytes, and left 9,389,604,864
  GPU bytes free; no FlashAttention or base-runtime downgrade was used.
- Added a targeted DeepSeek runner and 11-package hash-locked overlay contract.
  It verifies a clean Git state, every model file, exact package versions, BF16
  and GPU capability, and denies DNS/socket access during inference. Its output
  is explicitly non-authoritative for geometry, values, periods, scope,
  confidence and schema mapping. Six focused downloader/runner tests pass.
- Completed the clean E-0018 inference on the E-0017 page-13 image in 32.836091
  seconds. Peak allocated/reserved VRAM was 8,189,789,184/9,137,291,264 bytes.
  The reader emitted a 35-row span-aware raw HTML grid; the canonicalizer joined
  exactly one adjacent label-only row with its immediately following value-only
  row, retained both source-row IDs, and did not alter either financial cell.
- The ordered direct cash-flow anchors are now observed at candidate positions
  1 and 2, changing the targeted reader proposal from `UNKNOWN` to `DIRECT`.
  The acceptance gate remains fail-closed: semantic high confidence is false,
  and there is no automatic value, period, scope, geometry, confidence or
  ReportNormId authority. One `cố tức`/`cổ tức` Vietnamese label disagreement
  and one note-placement disagreement remain for review.
- Ran a clean, hash-manifested PP-OCRv6 word-box batch for E-0017 scan pages
  13–14: 170 lines and 1,509 words in 56.570324 seconds. The v2 geometry parser
  recovers 33+8 canonical rows, 58+14 exact numeric/sign cells, zero invalid
  cells, and the visible 2024/2023 axes on both pages.
- Added `FIXED_GEOMETRY_GRID_SEMANTIC_LABEL_FUSION_V1`. Its dynamic program
  supports ordinary one-to-one label binding plus one explicit overflow repair:
  two consecutive semantic numeric fingerprints must exactly match two geometry
  rows, the third semantic row must have a label but blank cells, and the repaired
  Vietnamese-label score must improve by at least a configured margin. It
  abstains when row loss, fingerprint disagreement, weak similarity or ambiguous
  paths remain. Four focused tests and the full 246-test regression pass.
- Completed formal E-0019 from clean commit `1a23b7b`. It binds the two clean
  DeepSeek runs and the 170-line/1,509-word PP-OCRv6 batch by SHA-256, preserves
  41/41 geometry cell tuples, verifies 41/41 supporting semantic numeric
  fingerprints, performs one 3→2 overflow repair, and recovers the configured
  DIRECT cash-flow anchors at positions 1 and 2. Confidence, periods, scope,
  schema mapping and ReportNormId authority all remain disabled.
- Added ordered label-segmentation fusion v2 without modifying the hash-locked
  E-0019 v1 algorithm. It uses the existing values-excluded ordered aligner,
  splits a collapsed semantic label only when both geometry-row segments exceed
  configured similarity and runner-up-margin gates, merges adjacent semantic
  label fragments, and removes duplicate leading/trailing tokens only under a
  separate gain/fraction/margin contract. Extra semantic rows are ignored only
  when their label is empty and their observed numeric fingerprint (and note,
  when present) matches geometry. Five focused tests pass; all final cell tuples,
  notes and geometry source IDs remain unchanged.
- Completed and hash-locked E-0020 over all six frozen TCB pages. It produces
  140 rows from 139 semantic rows and 140 geometry rows, preserves all 264
  financial cells, retains all 20 off-balance rows as mapping-ineligible, and
  keeps DIRECT LCTT evidence at positions 1 and 2 with semantic confidence false.
  The formal action record contains four collapsed-label splits, one adjacent
  fragment merge, one duplicate-edge trim, and two ignored blank-label displaced
  value rows. Only 130/140 rows have a supporting semantic numeric fingerprint;
  this is recorded rather than fabricated, while geometry cells stay unchanged.
- Completed and hash-locked E-0021 over all 140 E-0020 rows. It emits exactly
  four correction proposals with five one-edit replacements; every proposed row
  becomes Role A casefold-exact, proposal precision is 1.0 on this calibration
  set, semantic-key regressions are zero, and 136 rows remain untouched. Role A
  labels are withheld from proposal generation and used only for scoring.
- Completed the immutable S3 snapshot and real restore gate. Snapshot
  `20260806T050030130746Z-4a469fab2334` contains 4,361 logical files,
  4,192 unique objects and 18,388,413,612 unique bytes. Upload and 4,192 HEAD
  checks passed; the downloaded manifest, control plane, Git bundle, sample PDF,
  all seven asset classes and a full 4,184-content-object sequential restore
  passed. The run record is SHA-256
  `24eb066b51443066dfd14538ef7aeb21e9b700cc6ce995c49e56ff23b6701b04`;
  the manifest is SHA-256
  `74be9ea09905f0c7842d5a0b46bfe44f3fc5f32cc2c15b5040efcc4e99e8981b`.
  A final live check confirms bucket versioning `Enabled`, AES-256 default
  encryption, all public-access blocks enabled, and versioned encrypted manifest
  and run-record objects. Object Lock remains disabled.
- Completed the guarded local offload only after those gates passed. The command
  re-verified all 2,568 selected remote objects, fsynced journal SHA-256
  `8a41318512d58ce8842c318852f573980b00be953c07809259ed9b70e9d9b813`,
  then removed 2,567 registered PDFs plus the MongoDB source dump totaling
  18,287,522,139 bytes. Offload record SHA-256
  `2c285d831129b577e8dbba3490167c4b36011b73580682aaae17cda93078a913`
  was uploaded as a versioned AES-256 object and downloaded back hash-exact.
  A source PDF was also restored after offload and matched its expected SHA-256;
  immediately after offload all 2,568 selected logical paths were absent and
  recoverable through the immutable manifest. Free disk increased from 4.6 GiB
  to 22 GiB (46% used).
- Hydrated only the three CTG/ACB/MBB human-review fixtures (18,681,844 bytes)
  after the full regression correctly reported their absence. Their manifest
  hashes, sizes and PDF page counts pass; the other 2,565 offloaded logical paths
  remain absent locally. This preserves strict review tests without restoring
  the full 18.3 GB corpus.
- Implemented and hash-bound the generic fixed-grid semantic adapter, the
  reference-blind DeepSeek line reader, frozen-proposal replay and formal
  character/downstream evaluator. The adapter can bind semantic text only to
  exact PP-OCRv6 source line identities or their verified union and rejects
  numeric/period/unit/sign authority, truncation and layout serialization.
- Completed E-0026 from clean inference commit `a013cb8` and clean evaluator
  commit `3ea0fb9`; its formal statement-discovery replay has zero regression.
  Artifact, replay and immutable regression were pushed at `471fe75`.
- Completed the reference-blind E-0027 PP-OCRv6 prefix run: 9/9 pages, 794
  lines, 6,915 word tokens, mean line score 0.977278 and one clean model-load
  session. The unresolved V3 result was sealed before the V4 candidate replay;
  no human review, history, E-0022, semantic reader, mapping, numeric extraction
  or Excel output was invoked.
- Completed and sealed E-0028 at `2a0426a`. Every target gate passes, including
  exact off-balance exclusion, complete-page sequence, 8.5 path margin and exact
  structural no-regression on both frozen E-0013 documents. The full project
  regression now passes 383 tests with 2 intentional skips.
- Completed and sealed E-0029 at `9e4c208`. The artifact is hash-locked by an
  integration test; 9 focused reconstruction/control tests, Ruff and
  `git diff --check` pass. The run consumed only the E-0028 page contract,
  immutable PP-OCRv6 boxes/pixels and frozen V2/V3 reconstruction code. It did
  not load human review, template labels/IDs, MongoDB/history, E-0022, semantic
  proposals, period roles, validation or Excel.
- Completed and sealed E-0030 at `1ed17a5`. Its integration seal and 13 focused
  metadata/control tests pass. The reusable adapter deliberately supports only
  explicit CDKT snapshot semantics in V1; unsupported duration statements,
  duplicate dates, missing units and insufficient fuzzy margins fail closed.
- Completed and sealed E-0031 at `8fc483d`. Its crop/model/verifier controls,
  126-cell artifact and integration hash gate pass. Model input contains only
  `crop_path`; labels, notes, periods, units, schema IDs, history and human
  review are withheld. The checkpoint pins the official model revision and all
  six file hashes and records the exact rebuild/verify commands in the software
  inventory.
- Completed the corrected V4 row reconstruction and sealed its immutable replay
  as E-0033 at `198c5d8`. E-0032 remains in Git as an explicit superseded audit
  artifact; no evidence was deleted or overwritten. The hash gate proves the
  historical V3 implementation is byte-identical while V4 reproduces the
  one-row split and two newly recovered dashes.

## Currently in progress

- E-0022 is complete and immutable at statement-page diagnosis scope. Its Role B
  result and all 108 evidence files were sealed before Role A access; the two
  post-seal diagnostic artifacts were then hash-locked and pushed at `267bee8`.
  It cannot be rerun or used for threshold selection.
- Header-candidate/text-quality v2 and multi-signal discovery v4 are now frozen
  on separate calibration data. A form code, statement title or one accounting
  phrase can create evidence only; none can make a page mapping-eligible by
  itself. The bounded token-window matcher is restricted to 4+ token accounting
  anchors, at most 18 source tokens, contiguous order and 0.78 window similarity.
- Multi-signal discovery v3/v4, E-0024, E-0025, E-0026 and E-0028 are complete
  at their bounded calibration scopes. DeepSeek-OCR-2 is now eligible only to
  propose Vietnamese text on immutable PP-OCRv6 line/row boxes; VietOCR remains a
  challenger and the independent numeric path remains authoritative for values,
  signs and dashes.
- The active end-to-end task is E-0037 hierarchy- and anchor-aware ordered
  SchemaGraph mapping. It will map the sealed E-0036 baseline semantic
  proposals without numeric evidence, seal that decision, and only then join
  the immutable E-0034 numeric grid for accounting validation and
  provenance-bearing Excel.
  Measurement will use Role A versus Role B row coverage, schema assignment,
  full `(ReportNormId, period, raw value, normalized value, status)` tuples and
  workbook-cell agreement; no character-only metric can complete this stage.
- E-0027 page discovery, E-0028 locator V4, E-0030 table metadata and E-0033
  corrected row reconstruction and E-0034 numeric verification are the active
  upstream seals. E-0029 remains the before-contract and E-0031 is a
  superseded-denominator numeric result.
  Any semantic-reader stage may consume only the active page/row/axis contracts
  plus source pixels. Reader disagreements and unresolved blanks cannot silently
  enter a mapped output. Human-reviewed
  pages/IDs/values remain evaluation-only until the value/mapping/Excel output
  itself is sealed.
- Ordered SchemaGraph v1 and E-0023 are sealed. The mapper remains intentionally
  excluded from the
  already-frozen E-0022 pipeline and will next be evaluated on separate real-PDF
  development/validation blocks.
- Raw-PDF-dependent experiments now hydrate only their bounded registered inputs
  from the immutable S3 manifest and must not overwrite a mismatched local file.

## Major challenges and obstacles

- E-0022 exposes a statement-discovery recall failure before table extraction.
  PP-OCRv6 recognizes visibly structured header variants such as
  `BÁO CÁO TINH HìNH ... HP NHÁT` and form codes `B02a/TCTD-HN`, but the frozen
  title scores remain narrowly below 0.74 and the form-anchor token differs by
  the suffix `a`. The holdout must remain unresolved; normalization/form-anchor
  improvements can only be developed later on separate data.
- Exact Role A text isolates the mechanism failure: long, valid Vietnamese
  headings such as `BÁO CÁO TÌNH HÌNH TÀI CHÍNH HỢP NHẤT GIỮA NIÊN ĐỘ` are
  scored with a whole-string ratio against much shorter title cores, and form
  families such as `B02a/B03a/B04a` are not normalized to `B02/B03/B04`.
  Separately, v1 native-text quality produces legitimate-letter false positives
  and can miss control bytes. V2 fixes those general Unicode defects on separate
  calibration data. The remaining discovery risk is broader: even a perfect
  title/form line can occur in an audit narrative or notes page, while a true
  continuation can lose its title. Therefore final acceptance must combine
  independent period, unit, accounting-anchor, numeric-geometry and sequence
  evidence; it cannot be remeasured or tuned on E-0022 after reference access.
- Vietnamese OCR errors are context-sensitive: missing/misplaced diacritics,
  visually confusable base characters, dark header fills, blur and wrapped lines
  can damage labels while leaving numeric geometry intact. Research review is
  now bounded to methods that preserve raw OCR and propose corrections only:
  independent Vietnamese line recognition, dictionary/schema-constrained
  decoding, and confidence/margin-gated post-correction. No language model may
  rewrite digits, periods, signs, geometry or source-visible values.
- VietOCR's published aggregate score is not directly transferable: the fixed
  financial-line crops contain all-uppercase headings, long labels and small
  120-DPI accents. The official package also downloads mutable config/weights at
  runtime unless intercepted. E-0024 therefore pins the wheel hash, will vendor
  the exact downloaded config/weight hashes outside Git, disables ground-truth
  input to decoding, and decides adoption only from the predeclared crop set.
- E-0024 also proves decoded probability is not a source-exact gate: one wrong
  `VỐN`→`VÓN` line scored about 0.9324, overlapping exact lines whose observed
  range starts near 0.9175. The adapter must retain reader disagreement/raw crops
  and use semantic/structural evidence with abstention instead of trusting one
  probability threshold.
- E-0025 proves that a bounded source crop is not sufficient unless the model's
  internal image path preserves its aspect ratio and the decoder is bounded.
  DeepSeek v1 stretched low-height lines to a square, hallucinated Cyrillic/
  English content, and allowed one 36,314-character generation. This entire
  reader configuration is rejected. E-0026 fixes that packaging failure, but
  its remaining 12 edits are dominated by ten Vietnamese diacritic-only errors;
  it therefore supplies semantic proposals rather than source truth.
- E-0027 showed that whole-line similarity dilutes a valid short accounting core;
  E-0028 resolves that locator class, and E-0029 resolves the observed staggered-
  header/row-grid failure without consulting schema or review. E-0030 binds both
  repeated MBB period/unit header sets locally. E-0034 now verifies 118/119
  observed cells on the corrected grid and reduces the numeric residual to one
  dropped-digit disagreement. That cell must remain unresolved or receive
  localized pixel evidence;
  the nine `BLANK` cells still require row semantics to distinguish headings,
  visible empty cells and obscured evidence. E-0033 then found the missing
  note-bearing row and raised the denominator from 126 to 128 cells; E-0034 has
  now replayed that denominator. Later headerless pages
  may inherit only a verified table-level map and are outside the current
  local-header result.
- A higher-resolution crop is not sufficient by itself. On MBB LCTT page 14,
  PaddleOCR-VL still concatenates rows and numeric cells at 450 DPI; its current
  HTML proposal has 18 rows and 14 invalid multi-number cells, while independent
  PP-OCRv6 geometry proposes 27 rows with zero invalid cells.
- Headerless row-band crops cannot safely infer period axes independently. They
  must inherit a previously verified table-level period map and remain in review
  when the crop lacks that context.
- One MBB row-band crop was classified as text/image rather than a table, and one
  other row-band table still has unresolved column roles. These failures are being
  preserved as explicit evidence, not hidden or repaired from history.
- After fixed-grid fusion, the current measurable residual class is Vietnamese
  label semantics. E-0010 has four substitutions such as `LUỞU`/`LƯU`,
  `HOẶT`/`HOẠT`, `tính`/`tín`, and `TCDT`/`TCTD`; these require constrained
  language/schema correction with abstention, not changes to cell geometry.
- There is still no human-gold, bank-disjoint and period-disjoint end-to-end
  benchmark large enough to support a production accuracy threshold.
- DeepSeek-OCR-2's official tested stack differs from this Blackwell host, so its
  exact Transformers/tokenizers API pair remains isolated in a hash-locked
  external overlay. Two real document inferences now complete with about 8.19 GB
  peak allocated VRAM; the remaining obstacle is structural fallibility, not
  runtime capacity: page 14 emitted one wrapped-label/value-shift error.
- E-0018 is one selected calibration page from one bank/year. Its perfect
  numeric/sign agreement must be tested against E-0010 and bank/period-disjoint
  holdouts. DeepSeek's table bounding box is model-normalized proposal geometry,
  not source-pixel authority; independent word boxes are still required.
- The S3 backup/restore obstacle is resolved. Because local source offload is
  complete, tests that require raw PDFs must explicitly hydrate required paths;
  control-plane checks must never claim local source-byte verification while
  those files are absent.
- Independent row-wise mapping can select locally plausible but globally
  incompatible duplicate labels, and can force extra PDF rows into a smaller
  schema cluster. The next mapping change must therefore score one monotone
  cluster path, distinguish PDF skips from absent schema rows, and expose the
  runner-up path and score margin instead of hiding ambiguity.

## Current strategy

1. Treat the visible PDF and inherited table structure as source authority.
2. Locate statement/table/page scope before row mapping; exclude off-balance
   sections before candidate generation. Header v2 normalizes form-code families
   (`B02a` to `B02`, etc.) and long title cores, but supplies candidate evidence
   only. The final classifier groups independent signals: title/form identity,
   period axis, unit, accounting-row anchors, numeric/table geometry,
   continuation, and narrative penalties. For accounting labels only, V4 may
   also compare a 4+ token anchor against a bounded contiguous ordered token
   window inside a logical line; it preserves all V3 matches and disables that
   path for long prose. Decode the whole document in expected
   workbook statement order with a best/runner-up margin. A missing-title page
   may inherit the neighboring state across at most one page only when visible
   row labels, normalized numeric axes, period/unit signatures and continuation
   geometry corroborate it; otherwise abstain. Freeze on separate calibration
   documents before choosing a new holdout.
3. Reconstruct logical rows across wrapped text and page continuations while
   retaining hard page-boundary provenance. The current V3 grid permits only
   bounded header staggering, axis-local note references and shape-verified dash
   components; it keeps `VALUE`, `DASH`, `BLANK` and `INVALID` distinct.
4. Rank schema candidates lexicographically by statement/table context, parent,
   previous/next template rows, indentation/numbering, then normalized label.
   Same-bank and cross-bank history are lower-priority weak evidence only.
5. When independent row candidates are insufficient, align the whole local
   block against the ordered `SchemaGraph`. Use workbook `display_order` rather
   than numeric ReportNormId order; allow explicit PDF-row and schema-row skips;
   score label/accounting meaning, statement/section, parent/level, indentation,
   previous/next order and mapped neighbor anchors. Accept only a structurally
   valid best path with a clear runner-up margin; otherwise return
   `AMBIGUOUS_MAPPING` with ranked evidence for review.
6. Validate period bindings, raw/normalized numeric semantics, signs, horizontal
   and vertical arithmetic, parent-child totals, and template display order.
   The numeric layer accepts only exact value/sign agreement between the primary
   fixed-grid reader and an isolated digit reader. A dash additionally requires
   constrained pixel evidence. Reader confidence cannot select truth; mismatch
   abstains; a blank cannot become zero before row/table semantics verify it.
7. Escalate only localized failures to high-resolution rereads and independent
   readers. Reader agreement is supporting evidence, never automatic truth.
8. Fuse specialized readers on a fixed source-space row grid: PP-OCRv6 preserves
   row/cell pixels and values; DeepSeek proposes Vietnamese labels and order.
   Numeric fingerprints may gate a structural overflow hypothesis but never
   replace output values. Require a score margin and abstain on ambiguity. None
   of the readers can independently map IDs or establish numeric truth.
   For Vietnamese line recognition, report NFC source-exact accuracy, CER/WER,
   deletions/truncations and separate base-character versus diacritic-only
   errors. Schema/dictionary text may generate later correction candidates but
   must be reconciled with the source crop and structural margin; nearest edit
   distance alone is insufficient.
9. Segment semantic text over that fixed grid when row counts differ: allow only
   explicit 1→2 collapsed-label splits, 2→1 adjacent label fragments, or
   duplicate edge trimming with per-segment thresholds and runner-up margins.
   Label-empty extra rows require an exact observed numeric fingerprint before
   they can be treated as displaced evidence.
10. Develop custom learned components only behind frozen baselines: graph-based
   row/cell relation modeling, Vietnamese label encoders trained with
   same-label/different-parent hard negatives, specialized digit/sign recognition,
   and conditional dewarping. Evaluate on bank- and period-disjoint holdouts.
11. Keep model experiments bounded to a specific observed pipeline failure; do
   not accumulate reader benchmarks without a measurable extraction objective.
12. Protect large inputs with immutable S3 content keys and a manifest-first
   restore contract. Reclaim local space only after remote HEAD/checksum,
   manifest validation, and a real full-content sequential restore pass; hydrate
   exact logical paths without overwriting a mismatched local file.

## Planned next steps

1. Preserve the sealed E-0036 rejection. Before any Qwen retry, verify and pin
   the checkpoint/runtime GPTQ format interpretation and static zero-point
   checks, then run only a one- or two-crop, eight-token canary with
   same-token-run and finite/top-k-logit gates. Do not rerun all 64 crops unless
   that canary passes.
2. Make E-0037 the primary path: combine the sealed E-0036 baseline semantic
   proposals with structural anchors, parent/section context and workbook order,
   without review, history, values or numeric ReportNormId ordering as hints.
   Retain PDF-row/schema-row skips and require the existing decisive margin or
   abstain.
3. After the E-0037 mapping-only result is sealed, join immutable E-0033
   geometry, E-0030 period/unit bindings and E-0034 numeric/status evidence.
   Preserve the one numeric disagreement and nine blanks as unresolved unless
   new source-pixel evidence resolves them. Bind consolidated scope from visible
   source evidence, run accounting validation, and produce the provenance-bearing
   development Excel without fabricating unresolved values.
4. Seal the combined mechanism before selecting a new untouched holdout.
   VietOCR stays challenger-only; domain fine-tuning stays deferred unless the
   frozen downstream evaluation proves a material recognition blocker.
5. Build a human-gold evaluation split separated by bank and reporting period,
   including skew, warp, dark headers, blurred digits, wrapped rows, continuation
   pages, direct/indirect LCTT, separate/consolidated scope, and quarterly/YTD
   derivation cases.
6. Define calibrated abstention thresholds only after the human-gold benchmark;
   unresolved evidence must continue to produce review statuses rather than
   guessed output.

## Questions requiring user feedback

- Q-BOOT-004 and Q-BOOT-005 are resolved. No open question currently requires
  user feedback.
