# Accuracy requirements and operating notes

This file is the durable checklist for every design, experiment, review, and production run. It incorporates the master directive and subsequent user clarifications. New accuracy instructions must be appended or reconciled here rather than left only in chat history.

## 1. Authority and non-generation

- The visible source PDF is the final authority for label, value, sign, unit, period, scope, section, table, row, cell, hierarchy, and order.
- OCR, document models, LLM/VLM output, MongoDB history, historical filings, and accounting equations are supporting evidence only.
- Never invent a value, fill an unverified OCR blank, repair a total by synthesis, or let historical data overwrite legible PDF evidence. A visible dash in a verified numeric cell is preserved as `DASH` with no numeric value; it is never normalized to zero.
- Query historical values only after PDF structure has independently resolved a ReportNormID. Historical label/value similarity cannot generate or choose mapping candidates.
- Treat historical unit and separate/consolidated scope as UNKNOWN unless the historical source itself proves them. A historical mismatch triggers rereading/review only; agreement cannot promote confidence.
- Keep upstream raw-quarter and YTD series distinct. Upstream YTD values cannot serve as operands for PDF derivation; only two visible compatible PDF cells may do so.
- Preserve raw and normalized text and every image/preprocessing variant used to reach a decision.
- A high-DPI reread must be rendered directly from the registered PDF or original image. Never upscale a lower-DPI OCR render and treat interpolation as new source detail.
- Distinguish VALUE, ZERO, BLANK, DASH, NOT_APPLICABLE, NOT_OBSERVED, and invalid/unreadable evidence.

## 2. Ordered and hierarchical mapping

- Financial-statement item order is first-class evidence because labels can repeat.
- Never map a row by label alone when multiple schema candidates exist.
- Combine exact/normalized/accent-insensitive label evidence with statement, section, parent, child, sibling, preceding item, following item, schema order, physical proximity, scope, period, unit, sign, and accounting context.
- Prefer ordered block/subtree alignment and global assignment over independent row classification.
- Use several stable anchor rows around a candidate. A duplicate name is resolved by its containing block and neighbors, not by arbitrary candidate order.
- Treat note-reference columns on CDKT/KQKD/LCTT as foreign keys into TM, not as financial values.
- Preserve every accepted ReportNormId and its accounting meaning. Additions become stable identities only through the audited append-only schema-evolution path. ReportNormId magnitude has no ordering meaning; `DisplayOrder` and `ParentId` independently preserve the financial-statement presentation.
- The `vst_level`/`vsl_level` reference folder must be inventoried and hashed when populated; imported hierarchy is supporting structure and must retain source provenance.

### Universal schema evolution

- Treat the original 1,593-item supplied template as `BASE_SCHEMA`, not as a closed target universe. The active `UNIVERSAL_BANK_BCTC_SCHEMA` is the base plus evidence-backed, append-only additions observed in real bank PDFs.
- For every legitimate visible accounting row, choose exactly one terminal treatment: reuse an equivalent canonical item, add a genuine missing item, retain an explicit ambiguity/unresolved decision, or classify a non-item measure/axis/validation record as provenance. Never force-map a row merely because no exact base item exists.
- Before adding an ID, distinguish wording/OCR/punctuation/bank-phrasing variants from a materially different accounting concept. Prefer one canonical identity plus evidence-backed aliases.
- Every accepted new item must retain statement, section, canonical name, stable ReportNormId, true parent, hierarchy level, explicit display order/neighbor anchors, source document/page/row evidence, and the reason existing items are insufficient.
- The universal schema is a superset. A valid item may be observed at only one bank. Its absence elsewhere is normally `NOT_OBSERVED` or `NOT_APPLICABLE`, never an extraction failure or zero.
- Report both universal-schema coverage and per-document source coverage. A growing universal denominator must not hide whether every legitimate visible source row was accounted for.
- Schema evolution is part of PDF digitization, not a separate ontology exercise. Add only concepts supported by real source evidence, and continue processing unrelated rows while genuine questions await review.

## 3. Statement and scope boundaries

- Map only CDKT, KQKD, the applicable LCTT branch, and quantitative TM. Do not map CSTC unless scope changes.
- Preserve off-balance-sheet indicators such as “Bảo lãnh vay vốn”, “Cam kết giao dịch hối đoái”, or “Tài sản và chứng từ khác” as legitimate source-visible accounting items when the PDF reports them. They belong to an explicit `OFF_BALANCE_SHEET` section/root and must never be flattened into, or allowed to affect totals of, the main CDKT balance-sheet block.
- Narrative accounting-policy pages must not be treated as quantitative Notes.
- Separate and consolidated scope must be identified from visible document evidence.

## 4. Cash-flow method

- User-confirmed indirect ordered anchors: 4162 “Lợi nhuận trước thuế” followed by 4156 “Điều chỉnh cho các khoản”.
- User-confirmed direct ordered anchors: 4123 “Thu nhập lãi và các khoản thu nhập tương tự nhận được” followed by 4124 “Chi phí lãi và các chi phí tương tự đã trả”.
- Branch membership follows contiguous row order in `Bank_LCTT_ReportNormId.xlsx`, never integer-range comparison. The first block is workbook positions 1–57 (endpoint IDs 4155→4168; profit/adjustment anchors); the second is positions 58–107 (endpoint IDs 4104→4116; receipt/payment anchors). ID 4154 is only an interior row of the second block.
- Q-BOOT-001 was resolved by the user on 2026-08-06: the template-order block with endpoints 4155→4168 is INDIRECT and the block with endpoints 4104→4116 is DIRECT. This authorizes semantic branch selection only after the PDF method is independently established; it does not relax any cell, period, unit, sign, mapping, or confidence gate.
- Use title, opening rows, ordered anchors, parent/child structure, and historical same-bank filings together. Never cross-map branches because a label is similar.
- The coverage denominator contains only the applicable branch; the other branch is NOT_APPLICABLE.

## 5. Image quality before OCR

- Assess every page and relevant region for blur, foreground contrast, brightness, uneven background, skew, perspective distortion, compression/blocking, noise, text size, rotation, and cropping damage.
- Colored/dark table headers require local-region assessment. Generate controlled lightening, contrast, inversion, or threshold crops before rereading; do not globally alter an otherwise clean page.
- Render ordinary pages at 300 DPI, small text at 400–450 DPI, and only difficult crops at 600 DPI.
- Keep the original render. Do not indiscriminately sharpen, binarize, denoise, or super-resolve every page.
- Select a variant using OCR confidence, Vietnamese lexicon consistency, exact numeric agreement, word-box stability, table-line preservation, independent model agreement, accounting results, and hallucination rate.
- Variant generation and variant selection are separate stages. Preserve the original, hash every candidate, record every geometric inverse transform, and leave selection unresolved until a versioned evidence rule is satisfied.
- Reread a numeric cell when readers disagree, confidence is low, a final digit or sign is uncertain, history is anomalous, or an accounting check fails.

## 6. Tables, pages, rows, and cells

- A table may break mid-page, continue on the next page, or carry an unfinished row across pages.
- Build a continuation graph using repeated headers, matching column axes, unit, period, Notes number/parent, page adjacency, and row-continuation evidence. Adjacency alone is never enough.
- Long labels may wrap across multiple visual lines. Reconstruct the logical row before candidate generation and keep every contributing line box.
- Preserve label-only material after the last numeric row as unresolved trailing-page context. Do not let signatures, stamps, addresses, dates, or a possible next-page heading enter mapping until table/continuation evidence resolves their role.
- Handle borderless tables, merged cells, multi-level headers, transposed tables, movement schedules, and repeated headers.
- Every accepted value retains source page, table, logical row, column, label box, value box, header box, unit box, render hash, and coordinate transform through preprocessing.
- No cell geometry means no `AUTO_VERIFIED_HIGH`.

## 7. Period, unit, and sign

- Bind period headers to value columns by geometry; never assume the left column is current.
- Distinguish snapshot, duration, quarter, YTD, opening, closing, current, and comparative periods.
- Propagate a unit only across a traceable page/section/table continuation.
- Verify parentheses, leading/trailing minus, contra-asset presentation, and OCR-lost punctuation. A dash visibly located in a verified numeric cell is `DASH`; preserve the raw dash and leave its numeric value absent.
- A visibly empty numeric cell in an otherwise visible financial-statement row is `BLANK` after row presence, numeric-cell geometry, and table structure are verified. Only a visibly printed numeric zero is `OBSERVED_ZERO`. An OCR omission, unverified blank crop, digit, table rule, or ambiguous component fails closed. A schema row absent from the PDF is `NOT_OBSERVED`, never zero.

## 8. Arithmetic validation

- Check horizontal totals, vertical totals, parent versus children, Assets = Liabilities + Equity, gross plus allowance = net, opening plus movement = closing, and opening cash plus net change = closing cash where applicable.
- Arithmetic checks trigger rereading of cell, sign, period, unit, row, and branch. They never generate or overwrite a value.
- Record operands, tolerance, residual, pages/cells, result, and remediation in `validation_findings.jsonl`.
- A passing equation does not prove mapping correctness; it is one evidence gate.

## 9. Model use

- Models run locally on the user's VPS and do not incur external per-token charges. Use as many targeted passes or independent votes as needed for accuracy.
- GPU VRAM is still finite: load large models sequentially, checkpoint atomically, unload, clear cache, then load the next model.
- Benchmark on actual Vietnamese bank reports and difficult crops. Do not approve a model because it is new, large, advertised, or visually persuasive.
- Mapping models receive a small row/block context and candidates; they never read or create numeric truth.

## 10. Acceptance, review, and measurement

- High confidence requires visible cell, geometry, independent exact numeric reader, primary parser agreement, header-bound period, sourced unit, verified sign, contextual schema alignment, no PDF/history conflict, accounting pass, sufficient candidate gap, and no remaining review need.
- Group repeated ambiguities into one table-axis question rather than asking per row.
- Report candidate found, provisional mapping, machine reference, validated mapping, and accepted production value separately.
- Measure schema, exact value, period, unit, sign, page, and full tuple separately for CDKT, KQKD, applicable LCTT, and each TM group.
- Do not claim accuracy without a Role A machine-reference denominator and frozen evidence rules.

## 11. Reproducibility and recovery

- Hash input, code, config, model, render, OCR, intermediate structures, and output.
- Checkpoint per page and per stage; resume only after integrity passes. Mapper and validator replay must not rerun OCR.
- Keep feature-branch Git history and a protected remote main branch; never commit secrets.
- Commit each working, tested version. Keep a rebuild manifest for software, model, driver, binary/model hashes, install commands, smoke tests, and rollback steps.
- During model development, the user accepts VPS-local versioned artifacts plus periodic tested Git commits. Local backups still require an isolated hash-verified restore; record that this does not protect against total VPS loss. Revisit off-machine data protection before any later production policy change.

## 12. Human-reviewed correction contract

- Human answers are authoritative only for the cited PDF hash and page; freeze those PDFs as calibration before using the answers.
- Store reviewed raw text, normalized numeric value, row/status, period map, parent, neighbors, and prohibited duplicate/target IDs in a machine-validated registry.
- `OBSERVED_ZERO`, `DASH`, and `BLANK` are distinct terminal cell states. An absent schema row is `NOT_OBSERVED` and never zero.
- A visible off-balance row is `OUT_OF_SCOPE_FOR_TARGET_TEMPLATE`, not a mapping failure. It must not enter CDKT even when its label resembles an asset or liability row.
- Period orientation is inherited from visible table headers through a verified continuation graph. Amount magnitude and MongoDB are forbidden period inputs.
- Candidate ranking is structural and lexicographic. Parent and template-order context outrank label similarity; history is review-only when it is the first discriminator.
- ReportNormId magnitude has no ordering semantics. Preserve the template workbook row order through schema load, mapping, validation, and export.
- Calibration corrections cannot become institution/page hard-code or be used to claim holdout/production accuracy.
