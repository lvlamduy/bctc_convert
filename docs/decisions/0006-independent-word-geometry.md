# ADR 0006: independent word geometry is a separate evidence role

- Status: accepted for targeted calibration; production approval pending
- Date: 2026-08-05

## Context

E-0010 showed that a generative table reader can retain plausible numbers while collapsing two accounting rows into one and shifting later cells. Its page-14 output collapsed four row pairs; its page-15 output joined `198.242` and `(5.140.484)` in one cell. Aggregate numeric similarity could not prove row ownership.

The PP-OCRv6 reader returns independent line/word boxes but reads Vietnamese labels less accurately than Role B. Treating either reader as the whole answer would discard useful evidence or hide a known weakness.

## Decision

Use distinct evidence roles:

- Role B proposes page context and labels from a document-layout/VLM path.
- Role C proposes period/note axes, row ownership, numeric observations, and source boxes from a non-generative detection/recognition path.
- Ordered fusion may compare the roles, but neither reader may overwrite the other silently or promote confidence merely because values agree.

Role C reconstructs a table by relative evidence rather than bank/page constants:

1. infer at least two period headers and their right-aligned value axes;
2. infer a separate note-reference axis;
3. cluster numeric boxes into y anchors;
4. attach label lines directionally to the next compatible anchor, allowing wrapped labels while retaining parent/section rows;
5. preserve label-only material after the final numeric anchor as unresolved trailing context, excluded from mapping until a continuation gate corroborates it;
6. keep multiple substantive numbers in one cell `INVALID` rather than splitting them;
7. normalize an OCR dash-like glyph only when it is the sole token on a value axis;
8. for an OCR-empty cell, classify `DASH` only when a constrained source-image crop contains exactly one high-contrast horizontal component satisfying text-height-relative width, height, fill, aspect, axis, and row-center gates.

All thresholds are versioned in `config/tables/word-box-reconstruction.yaml`. Pixel recovery retains crop/component boxes and measurements. A blank crop, vertical digit, long table rule, multiple components, or low-contrast ambiguity remains blank/unresolved. Arithmetic and the Role A reference are not inputs to dash detection.

## Consequences

E-0011 recovered all four VLM row collapses, separated the two page-15 cells, removed signature/footer rows from mapping while retaining their evidence, and matched 264/264 financial cells in this targeted calibration. Three missing dash observations came from constrained pixels and one from the OCR glyph `一`.

Role C matched only 3/140 labels byte-for-byte and 14/140 semantic keys. It is therefore accepted as geometry/value proposal evidence, not as a standalone label reader. E-0011 remains post-failure TCB calibration, sets `AUTO_VERIFIED_HIGH=0`, performs no schema/ReportNormID assignment, and cannot establish multi-bank or production accuracy.

Rows whose both period cells are absent or missed still lack a numeric anchor and require fusion with another structure reader. Distortion, multi-bank, consolidated, quarterly, cross-page-row, and untouched-holdout gates remain open.
