# Test and accuracy strategy

## Test layers

1. Pure unit tests cover text/number/date/unit parsing, atomic writes, evidence status gates, schema and hierarchy import, workbook-order cash-flow segmentation, row wrapping, cross-page continuation, period derivation, arithmetic, and export integrity.
2. Property and mutation tests will inject digit swaps, lost minus signs, dash/zero changes, duplicated labels, shuffled rows, moved columns, broken headers, and page-boundary splits. A mutation passes only when the system detects/downgrades it rather than accepting the wrong value.
3. Golden page tests retain PDF/image hash, expected word/cell boxes, row/column axes, labels, values, signs, units, periods, notes, and schema IDs. Searchable and scanned versions of the same filing are paired where available.
4. Document tests cover phase sequence, statement boundaries, direct/indirect method, separate/consolidated scope, cross-page tables, long wrapped labels, and exclusion of off-balance sections.
5. Frozen Role A holdout establishes the independent machine denominator. Role B is scored without seeing Role A artifacts.
6. Restore/replay tests rebuild from manifests, replay mapping/validation without OCR, export Excel atomically, reopen it, and verify sheet/schema order plus provenance links.

The first real-PDF geometry regression is `E-0006`: a registered, hash-locked VPB logic-development document covering CDKT, off-balance disclosures, KQKD, and direct LCTT across pages 5–10. The fixture asserts row/value/note counts, section boundaries, multiline labels, period/unit bindings, direct-method anchors, and fail-closed retention of an unlabeled numeric total. Because the PDF is an external source artifact, the integration test skips only when that exact file is absent; a hash mismatch fails rather than accepting a substitute.

`E-0007` is the first full GPU document-model cross-reader experiment. Ordered dynamic programming aligns native-PDF rows and VLM rows using only order and labels. It may propose two adjacent candidate rows as one logical wrapped row only when exactly one carries financial evidence. Numeric values and note references do not affect the alignment path; they are compared afterward. Diacritic-sensitive exact text and accent-stripped semantic keys are separate metrics, preventing normalization from hiding OCR spelling errors. Unit tests inject wrong values to prove they do not shift structural alignment and retain missing/extra rows explicitly.

`E-0008` selects and indexes the uploaded historical bank source. Tests reject non-bank documents, unknown period types, misaligned series lengths, unknown numeric keys, and policy changes that weaken safety gates. DuckDB constraints and routine verification require zero duplicate identities, zero historical value rows for newly registered schema ID 1944 in this fixed source snapshot, and zero rows permitted to map or promote PDF evidence. NAN, NULL, and negative zero have separate preservation checks. The source evaluator proves that generic `report_yearly`/`report_quaterly` have no registered banks and that allowlisted `data_chart` covers all 27 banks with annual and quarterly documents.

The Q-BOOT-004 regression binds the original and appended TM workbook hashes,
rechecks all 1,384 prior ID/name/order mappings, and requires 1944 as the last
target in Role A, Role B, Excel output, evaluation, and mandatory search. A
document-level search is complete only when each independent role records exactly
one terminal outcome for every template ID; absence is never silently changed to
zero.

`E-0009` starts the frozen multi-document calibration layer. Four PDFs were assigned the immutable `CALIBRATION` role before content inspection: a TCB 2024 separate scan/searchable pair and image-heavy MBB/VCB 2025 consolidated filings. Page correspondence is inferred with ordered dynamic programming over Otsu-ink, low-resolution layout, and row/column projection fingerprints. It does not read text or numeric values. Low-similarity or ambiguous pairs remain explicit but cannot enter the benchmark. The first run paired all six TCB main-statement target pages, including the off-balance exclusion and two-page direct LCTT. Evidence-manifest tests prohibit Role B from reading Role A inputs/results and prohibit historical values during mapping; history is admitted only in post-mapping validation after a resolved ID.

The E-0010 runner seals Role B before comparison. Unit tests cover dirty-start rejection, overwrite refusal, and successful verification of render/result/metrics/package/model hashes. Reader-output tests preserve a VLM cell containing two visible numbers as `INVALID`, prove numeric disagreement cannot alter ordered alignment, and require all rows under an off-balance page heading to remain ineligible for CDKT. Ordered alignment can identify both a logical row split across two candidate rows (`MERGE_CANDIDATE`) and two reference rows collapsed into one candidate (`MERGE_REFERENCE`) using labels/order only. The latter is never numerically repaired; it enters table reconstruction review.

E-0010 reports coverage and agreement separately so missing/merged evidence cannot disappear from the denominator. On the six-page TCB calibration block, reference financial row/cell coverage is 94.70%; conditional agreement on aligned evidence is 96.80% rows and 97.60% cells, while strict whole-reference agreement is 91.67% rows and 92.42% cells. These are cross-reader machine-reference results, not human-gold, schema, full-tuple, holdout, or production accuracy. The integration test locks the exact metrics, algorithm/config hashes, zero confidence promotion, zero off-balance eligibility, direct-LCTT fail-closed semantic state, accepted page continuation, four row collapses, and the explicit multi-number-cell reason.

E-0011 is a targeted post-E-0010 failure analysis, not an untouched benchmark. A sealed PP-OCRv6 word-box reader reconstructs rows from relative period/note axes and downstream label attachment. Unit tests cover adjacent rows, wrapped labels, parent headings, multi-token invalid cells, trailing-context isolation, OCR dash-glyph normalization, visible-pixel dash recovery, and negative cases for white cells, vertical digits, and long table rules. The frozen integration result requires 140 one-to-one matches, 132/132 exact financial rows, 264/264 exact cells, 50/50 notes, zero invalid cells, zero off-balance eligibility, three pixel dashes, one glyph-normalized dash, fourteen preserved mapping-ineligible signature/footer lines, and one accepted LCTT continuation. Arithmetic contributes 11 validation passes and one explicit `NOT_TESTABLE`; it never supplies an operand for the dash. Automatic high confidence remains zero.

Role-specific label metrics are part of the gate interpretation: Role C has 3/140 source-exact labels and 14/140 semantic-key matches even though its geometry/value cells recover the targeted failures. Tests therefore prohibit treating the geometry reader as the label or schema authority.

## Distortion matrix

Each representative fixture is tested in original form and controlled variants: blur, low contrast, dark/colored header, uneven lighting, JPEG blocking, noise, rotation, skew, perspective/warp, crop loss, and small text. This follows the factor-wise idea of Real5-OmniDocBench but uses Vietnamese financial pages and exact cell truth.

## Required metrics

- Page/phase, table, row, column, and cell geometry accuracy.
- Exact numeric string/value, sign, VALUE/ZERO/BLANK/DASH state, unit, period, scope, note reference, and schema ID.
- Full-tuple exact accuracy and coverage by CDKT, KQKD, applicable LCTT branch, and each TM group.
- Cross-page continuation precision/recall; false merge rate is reported separately.
- Calibration: error rate by confidence bucket, selective accuracy versus review rate, and conformal/holdout coverage if adopted.
- Parser/OCR/model pairwise disagreement, reference-evidence coverage, conditional agreement, strict whole-reference agreement, escalation recovery rate, throughput, VRAM, and failure/hallucination rate.
- Source-exact label accuracy and semantic-key accuracy must be reported separately; semantic normalization can never count as exact OCR.

## Acceptance gates

- Values never select a schema candidate by themselves.
- A passing arithmetic identity cannot promote an otherwise incomplete evidence tuple.
- Missing geometry/config/period/unit/sign or unresolved semantic conflict fails closed.
- Derived quarter values retain both operands and formula and cannot be classified as directly observed/high confidence.
- Any regression that changes an accepted value, sign, period, scope, or ID must produce a reviewed diff before merge.
- A cross-reader match is corroboration, not ground truth. Correlated readers, shared rendering, or shared model weights must be disclosed.

## Experiment record

Every experiment is appended to `docs/experiments/EXPERIMENT_LOG.md` with hypothesis, code/config/model/data hashes, frozen fixtures, metrics, result, failure analysis, and decision. Cherry-picked examples or visual impressions are not acceptance evidence.

Historical experiment records are immutable. `E-0006` remains bound to geometry configuration v1 and its recorded algorithm hashes; a newer implementation cannot silently rewrite its expectations. When the exact historical implementation is not present, CI verifies source/config identity and skips replay rather than pretending the current code reproduced it. The same rule applies to E-0009 after later evidence stages extended its helper implementation. A versioned successor fixture must lock the current algorithm. E-0010 uses `config/tables/geometry-v2.yaml`; E-0011 separately locks `config/tables/word-box-reconstruction.yaml` and its current implementations.

Source-registry tests require byte-identical repeated registration, preservation of the original first-seen time, and hard failure when registered content changes in place or a registered path disappears. A routine audit may append new paths but may not silently rewrite existing source identity.

GPU-runtime audit tests are fail-closed: a current CUDA/import smoke, dependency compatibility, tracked freeze hash, and exact installed package sequence must all pass. Unit tests cover the configured-pass path, an absent manifest, and installed-freeze drift. Runtime acceptance and production model acceptance are deliberately separate states.

The PP-OCRv6 batch runner has a separate mechanism gate. Unit tests require
normalized sorted page selection; relocation only by exact hash; immutable role
agreement across request, preprocess manifest, and registry; a bound clean
preprocess envelope; rejection of render/config/runtime drift; full-identity
orphan-page recovery; and preservation of all model-load sessions across
resume. Sealing additionally locks both the batch orchestrator and its
single-page helper and rejects either hash drifting. A real development smoke
must reproduce a known OCR artifact byte for byte before the runner is used for
new evidence. This proves batch equivalence and recovery behavior only; it does
not add an accuracy sample.

E-0012 is the clean mechanism regression: TCB page 15 remained byte-identical
to its E-0011 single-page result, no-op resume retained exactly one model-load
session, and sealing verified both batch/helper hashes. The integration test
locks these outcomes and re-hashes local artifacts when they are available.

The statement-location v1 gate tests the document boundary before row mapping.
It rejects narrative title mentions without numeric table density and a
discriminative phrase, suppresses audit/contents pages, requires the contiguous
CDKT→KQKD→LCTT→TM order, and refuses any unknown interstitial page. Candidate
start scoring is versioned and a close runner-up fails closed. Scope tests prove
that an off-balance B02 page is excluded from eligible CDKT pages and cannot be
linked as a continuation of the main CDKT table. Cash-flow tests cover ordered
direct/indirect anchors, competing shared-title text, conflict, unknown, and the
Q-BOOT-001 no-schema-assignment invariant. Evidence-loader tests reject hash
drift, path traversal, render identity drift, malformed page axes, out-of-bounds
boxes, and role/batch identity changes before classification.

E-0013 is the clean two-document calibration regression for this gate. Its
integration test locks the algorithm/config/source/preprocess/batch/output
hashes, exact eligible and excluded pages, zero interstitial/scope-crossing
pages, candidate margin, and DIRECT title-plus-ordered-anchor evidence for MBB
and VCB. Locally present external artifacts are re-hashed; an absent external
artifact does not turn a Git clone into a false failure. The regression does
not assert human-gold, row/schema/numeric, holdout, confidence, or production
accuracy, and it requires schema branch assignment to remain disabled.

The bootstrap unit gate independently reconstructs a two-document E-0013
artifact and eight local identities. It requires exact MBB/VCB contracts and
then tampers with a location output while updating that file's recorded hash;
the audit still fails because the semantic page/scope contract drifted. Unsafe
or escaping paths, tracked code/config drift, present external hash drift,
promotion flags, ReportNormId additions, and Q-BOOT-001 relaxation also fail
closed in the loader.

E-0014 is the selected-page reader-acquisition gate, not an accuracy gate. Its
integration test locks the clean inference commit, algorithm/config/runtime and
model identities, exact page/scope contracts, 13/13 quality-gated original
renders, four reader seals, Role C counts and single-load behavior, and all
no-history/no-schema/no-arithmetic/no-promotion boundaries. When external
artifacts are locally present the test re-hashes their source, preprocess,
batch, and seal files and verifies both readers cover the same exact 200-DPI
page set. An absent external artifact keeps a Git-only rebuild portable; a
present mismatch fails. The retained VCB page-9 truncation and multi-table
page-10 structure are required failure triggers for the next fusion version,
not visually sampled claims of document accuracy.

Structural fusion v2 has isolated unit gates before it can consume E-0014.
Role B tests require all HTML table blocks to remain observable, safe
rowspan/colspan grid expansion, one-use header-only role inheritance, variable
optional index/note columns, concise-period discrimination, strict rejection of
concatenated grouped values, and fail-closed unresolved roles. Role C tests
require worded period headers, rejection of report/regulatory metadata as value
axes, repeated geometry-derived index bands, correct index ownership when a
wrapped label's values sit lower than its code, alphanumeric note references,
two visibly supported OCR-blank dashes, and quarantine of right-margin numbers.
Fusion tests mutate values without changing the label/order path, retain a
reader-truncated row, and prove an upstream off-balance page has zero eligible
alignment units. Page boundaries remain hard alignment separators; table
continuation records preserve both readers' boundary rows but cannot
automatically merge them. Agreement always has confidence effect `NONE`.

E-0015 is the clean two-document integration regression for structural fusion
v2. It hash-locks the evaluator, every direct/transitive algorithm, four table
policies, E-0014 artifact, source/seal/result identities, and the 2.1 MiB
evidence artifact. It requires 14 retained Role B blocks with exactly one
fail-closed unresolved VCB page-9 block, 13 two-axis Role C pages, exact row and
action counts, observed-cell/note/code/label metrics, eight retained Role B
invalid cells, zero Role C invalid cells, ten pixel dashes, three quarantined
margin numbers, zero off-balance eligibility, and five hard page boundaries.
Locally present external inputs are re-hashed. The 95.154185% paired-observed
cell agreement is conditional machine-reader agreement, not human-gold or
production accuracy; missing/truncated rows remain outside that numerator and
are reported separately through bilateral financial-row coverage.

Targeted reread v1 has a separate fail-closed gate. Unit tests require relative
line-height localization, one header-bound full-table crop for dense failures,
one 600-DPI strip for adjacent numeric disagreements, context around wrapped or
missing rows, and order-bracket localization when only Role B observes a row.
An upstream mapping-ineligible page must yield zero regions; a new escalation,
bad line index, unsafe path, dirty formal Git state, source/upstream hash drift,
or output overwrite must stop the run. Renders must come from the registered
PDF, preserve the original image, record variant-to-PDF/baseline transforms,
and leave value replacement and confidence promotion false. The E-0016
integration gate will hash-lock the exact 2-document/13-page/8-region input
contract; it is an acquisition/localization regression, not an OCR-accuracy or
production gate.

The E-0016 original-crop OCR evidence gate additionally requires 15/15 requested
reader runs (eight PP-OCRv6 and seven PaddleOCR-VL), exact input/output/runtime
bindings, and zero schema mapping, variant selection, value replacement, or
confidence promotion. Full-table comparisons align on order and normalized
labels only. Headerless crops cannot invoke the period-axis parser. Tests must
retain no-table, unresolved-table, invalid-cell, and reader-count disagreement
outcomes even when every inference process exited successfully. The formal
artifact is generated only from a clean mechanism commit and is then protected
by a separate hash-locked integration regression.

The reader-candidate policy adds a structure-only TATR gate before any new
model can enter fusion. Unit tests lock its official revision and artifact
hashes, checkpoint-native preprocessing, complete all-query retention, source-
coordinate box conversion, and zero mapping/value/period/scope/confidence
authority. The first real run is calibration on only E-0016's two original
full-table crops. It may compare row/column boxes with independent word
geometry, but values and history cannot influence box matching and the result
cannot establish human-gold accuracy. DeepSeek-OCR-2 requires a separately
frozen Blackwell runtime and exact Vietnamese digit/sign/hallucination metrics;
IBM TableFormer is a later structure challenger and ClusterTabNet remains a
research graph baseline.

Explicit page numbers in a golden/calibration fixture are expected test data, not production routing rules. Production page pairing must continue to use document-order and visual evidence; no bank, page offset, or coordinate constant may enter the algorithm.

The hash-bound human-review registry `HR-2026-08-06-CTG-ACB-MBB` adds a calibration truth layer above machine-reader agreement. Its tests verify 3 exact PDF identities, 30 decisions, 58 visible period values, 12 `OBSERVED_VALUE` rows, 6 `OBSERVED_ZERO` rows, 1 `NOT_OBSERVED` row, and 11 `OUT_OF_SCOPE_FOR_TARGET_TEMPLATE` rows. They also assert that external IDs 5701–5711 do not collide with any current template. This is fixture truth only; production code cannot inspect its bank/page entries.

Period propagation v1 is tested independently of all values and history. A complete visible table header binds the axes; a headerless adjacent continuation inherits by column ordinal only after continuation/context/geometry gates. New statements/tables, changed period structures, non-adjacent pages, incompatible axes, and partial local headers remain unresolved.

Structural ranking v2 uses a lexicographic evidence order. Mutation tests deliberately give a wrong-parent candidate stronger same-bank history and require the correct parent candidate to remain first. A history-only difference must remain `AMBIGUOUS_MAPPING`. Sequence tests use the real non-monotonic `4337 → 4373 → 4338` template block to prove that workbook `display_order`, not numeric ID, controls order and that a schema ID cannot be assigned to two visible rows.

Ordered SchemaGraph mapping v1 is the block-level fallback above that row-wise
ranker. Its focused tests cover a six-PDF-row/three-schema-row ordered
subsequence, retained extra PDF rows, same-label/different-parent clusters,
mapped parent and neighbor consistency, external semantic evidence that cannot
override a verified parent, numbering conflict, exact off-balance labels that
remain excluded, and tied path alternatives that must abstain. The real CDKT
template test asserts the graph retains 77 workbook-ordered nodes, the
`4337 → 4373 → 4338` non-numeric sequence, and the three distinct fixed-asset
parents. A skipped schema node becomes `NOT_OBSERVED` only in a resolved block
declared exhaustive; otherwise it remains unmatched-in-block evidence.

Statement-header/text-quality v2 has a separate regression family. Mutation
tests cover optional form suffixes, long valid title suffixes, a damaged title
rescued only by an independent form family, off-balance scope, direct LCTT,
conflicting and malformed form codes, wrong statement order, and an exact title
inside narrative text without numeric table evidence. Unicode tests must retain
real mojibake/control-byte/replacement markers while accepting legitimate
Vietnamese `Â`/`Ã` tokens including word-final punctuation. Real calibration
replay must reproduce the E-0013 MBB/VCB page/type/scope/method contracts exactly
before the v2 mechanism can be frozen; E-0022 is excluded from tuning and replay.

Final statement discovery v3 treats those header matches as candidates only.
Its focused tests require: multi-line heading joins; rejection of a lone
balance-sheet title in narrative prose; rejection of a lone TM title after an
otherwise complete statement block; full multi-signal acceptance; exact
off-balance exclusion; semantic-reader text that cannot manufacture PP-OCRv6
numeric geometry; one-page forward and backward inference with visible rows,
aligned numeric axes and table-edge continuity; abstention for incompatible
axes or mismatched period axes; and document-level abstention when two complete
paths tie. Inference tests must prove that only a locally accepted neighbor can
support the missing page, so inferred pages can never form a propagation chain.

The real calibration gate uses the pre-existing E-0013 MBB/VCB batches only. It
must reproduce MBB eligible pages CDKT 10–11, KQKD 13, LCTT 14–15, excluded page
12 and TM boundary 16; and VCB eligible pages CDKT 8–9, KQKD 11–12, LCTT 13–14,
excluded page 10 and TM boundary 15. Both LCTT blocks must remain DIRECT. These
are calibration page/scope contracts, not human-gold accuracy. E-0022 is never
rerun, replayed or used to choose v3 thresholds.

E-0024 freezes its input before challenger inference. The 37 single-line
MBB/VCB samples bind source-PDF, render and PP-OCRv6 JSON hashes plus line index,
bbox, raw prediction and source-visible transcription. Tests reject unsafe
semantic-reader authority and any PP-OCR anchor drift. The challenger never
receives reference text. Required comparison metrics are NFC exact/casefold
line accuracy, CER, WER, insertions, deletions, substitutions, base-character
errors and diacritic-only errors, stratified at least by title versus non-title.
Adoption requires strictly lower aggregate CER, no title-exactness regression
and no increase in empty/truncated lines. Regardless of result, PP-OCRv6 retains
all geometry/numeric authority and E-0022 remains excluded.

The first formal E-0024 run passes those three bounded gates: PP-OCRv6 versus
VietOCR is 0/37 versus 30/37 exact lines, 14.9518% versus 0.6431% CER, 55.2448%
versus 2.7972% WER, and 0/10 versus 6/10 exact titles, with zero empty or
suffix-truncated predictions for either reader. Seven lines remain non-exact:
eight substitutions comprising seven accent-only edits and one capitalization
edit. The integration gate must preserve every raw disagreement and source crop,
must reject probability-only promotion, and remains calibration-only.
