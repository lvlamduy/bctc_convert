# Accuracy requirements and operating notes

This file is the durable checklist for every design, experiment, review, and production run. It incorporates the master directive and subsequent user clarifications. New accuracy instructions must be appended or reconciled here rather than left only in chat history.

## 1. Authority and non-generation

- The visible source PDF is the final authority for label, value, sign, unit, period, scope, section, table, row, cell, hierarchy, and order.
- OCR, document models, LLM/VLM output, MongoDB history, historical filings, and accounting equations are supporting evidence only.
- Never invent a value, fill a blank, turn a dash into zero, repair a total by synthesis, or let historical data overwrite legible PDF evidence.
- Query historical values only after PDF structure has independently resolved a ReportNormID. Historical label/value similarity cannot generate or choose mapping candidates.
- Treat historical unit and separate/consolidated scope as UNKNOWN unless the historical source itself proves them. A historical mismatch triggers rereading/review only; agreement cannot promote confidence.
- Keep upstream raw-quarter and YTD series distinct. Upstream YTD values cannot serve as operands for PDF derivation; only two visible compatible PDF cells may do so.
- Preserve raw and normalized text and every image/preprocessing variant used to reach a decision.
- Distinguish VALUE, ZERO, BLANK, DASH, NOT_APPLICABLE, NOT_OBSERVED, and invalid/unreadable evidence.

## 2. Ordered and hierarchical mapping

- Financial-statement item order is first-class evidence because labels can repeat.
- Never map a row by label alone when multiple schema candidates exist.
- Combine exact/normalized/accent-insensitive label evidence with statement, section, parent, child, sibling, preceding item, following item, schema order, physical proximity, scope, period, unit, sign, and accounting context.
- Prefer ordered block/subtree alignment and global assignment over independent row classification.
- Use several stable anchor rows around a candidate. A duplicate name is resolved by its containing block and neighbors, not by arbitrary candidate order.
- Treat note-reference columns on CDKT/KQKD/LCTT as foreign keys into TM, not as financial values.
- Preserve the supplied schema ID and display order. Additions are proposals only until append-only authority is confirmed.
- The `vst_level`/`vsl_level` reference folder must be inventoried and hashed when populated; imported hierarchy is supporting structure and must retain source provenance.

## 3. Statement and scope boundaries

- Map only CDKT, KQKD, the applicable LCTT branch, and quantitative TM. Do not map CSTC unless scope changes.
- Do not map off-balance-sheet indicators such as “Bảo lãnh vay vốn”, “Cam kết giao dịch hối đoái”, or “Tài sản và chứng từ khác” into CDKT.
- Narrative accounting-policy pages must not be treated as quantitative Notes.
- Separate and consolidated scope must be identified from visible document evidence.

## 4. Cash-flow method

- User-confirmed indirect ordered anchors: 4162 “Lợi nhuận trước thuế” followed by 4156 “Điều chỉnh cho các khoản”.
- User-confirmed direct ordered anchors: 4123 “Thu nhập lãi và các khoản thu nhập tương tự nhận được” followed by 4124 “Chi phí lãi và các chi phí tương tự đã trả”.
- Branch membership follows contiguous row order in `Bank_LCTT_ReportNormId.xlsx`, never integer-range comparison. The first block is workbook positions 1–57 (endpoint IDs 4155→4168; profit/adjustment anchors); the second is positions 58–107 (endpoint IDs 4104→4116; receipt/payment anchors). ID 4154 is only an interior row of the second block.
- The user's latest DIRECT/INDIRECT wording conflicts with the visible anchor semantics and workbook endpoints. Until reconciled, preserve both ordered blocks but disallow semantic high-confidence acceptance.
- Use title, opening rows, ordered anchors, parent/child structure, and historical same-bank filings together. Never cross-map branches because a label is similar.
- The coverage denominator contains only the applicable branch; the other branch is NOT_APPLICABLE.

## 5. Image quality before OCR

- Assess every page and relevant region for blur, foreground contrast, brightness, uneven background, skew, perspective distortion, compression/blocking, noise, text size, rotation, and cropping damage.
- Colored/dark table headers require local-region assessment. Generate controlled lightening, contrast, inversion, or threshold crops before rereading; do not globally alter an otherwise clean page.
- Render ordinary pages at 300 DPI, small text at 400–450 DPI, and only difficult crops at 600 DPI.
- Keep the original render. Do not indiscriminately sharpen, binarize, denoise, or super-resolve every page.
- Select a variant using OCR confidence, Vietnamese lexicon consistency, exact numeric agreement, word-box stability, table-line preservation, independent model agreement, accounting results, and hallucination rate.
- Reread a numeric cell when readers disagree, confidence is low, a final digit or sign is uncertain, history is anomalous, or an accounting check fails.

## 6. Tables, pages, rows, and cells

- A table may break mid-page, continue on the next page, or carry an unfinished row across pages.
- Build a continuation graph using repeated headers, matching column axes, unit, period, Notes number/parent, page adjacency, and row-continuation evidence. Adjacency alone is never enough.
- Long labels may wrap across multiple visual lines. Reconstruct the logical row before candidate generation and keep every contributing line box.
- Handle borderless tables, merged cells, multi-level headers, transposed tables, movement schedules, and repeated headers.
- Every accepted value retains source page, table, logical row, column, label box, value box, header box, unit box, render hash, and coordinate transform through preprocessing.
- No cell geometry means no `AUTO_VERIFIED_HIGH`.

## 7. Period, unit, and sign

- Bind period headers to value columns by geometry; never assume the left column is current.
- Distinguish snapshot, duration, quarter, YTD, opening, closing, current, and comparative periods.
- Propagate a unit only across a traceable page/section/table continuation.
- Verify parentheses, leading/trailing minus, contra-asset presentation, and OCR-lost punctuation. Dash is not automatically zero.

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
