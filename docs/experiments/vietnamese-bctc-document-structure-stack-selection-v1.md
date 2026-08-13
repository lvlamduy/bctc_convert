# Vietnamese BCTC document-structure stack selection v1

Date: 2026-08-13

## Decision

Use specialized, source-bound readers. Do not ensemble every available document model on every page.

1. **VietOCR 0.3.13 VGG Transformer** is the only Vietnamese semantic-text reader.
2. **PP-OCRv6** remains the source locator and the reader for dates, numeric values, signs and dashes. Its Vietnamese transcript is retained only as raw provenance and must not identify an accounting label or family.
3. **PP-DocLayoutV3 and PaddleOCR-VL-1.6 are excluded from the production router.** Existing sealed experiments show cell-coordinate/ownership drift, row collapses, shifted values and severe truncation. Their historical artifacts are retained as exclusion evidence only; neither model may delimit a canonical table, row or cell.
4. **TATR-v1.1-All** is the first and only new table-structure challenger. It may propose rows, columns, headers and spanning cells on a tightly bounded table crop derived from authenticated source geometry. It has no text, value, period, schema or family authority.
5. **IBM TableFormer is deferred.** It overlaps TATR's role and adds a second competing topology plus a larger dependency/post-processing surface. It is evaluated only if TATR fails a predeclared structural error class that TableFormer plausibly addresses.

There is no separate official Paddle model named `P-DocLayoutV3` in the reviewed sources. This document treats it as a typo for `PP-DocLayoutV3` unless a concrete, independently identified artifact is supplied.

## Why language support means different things by role

Vietnamese training and evaluation are mandatory for the semantic-text reader. The local frozen comparison selected VietOCR VGG Transformer over VietOCR VGG Seq2Seq: 42/52 versus 38/52 exact transcripts, 32/41 versus 27/41 exact core semantic roles, and 2.030% versus 3.205% CER. Accentless Vietnamese keys remain shortlist-only and cannot establish identity.

Table-structure models predict visual regions and relations, so the absence of Vietnamese training is not an automatic disqualification. It is still a domain risk: Vietnamese labels are often longer, wrap differently, and appear in borderless financial tables. Therefore no published Chinese/English or aggregate multilingual score promotes a model. Promotion requires a frozen Vietnamese bank-report evaluation.

- PaddleOCR-VL-1.6 officially lists Vietnamese among 109 languages, but does not publish a Vietnamese-only BCTC CER, cell-accuracy or table-topology result. Its aggregate multilingual score cannot override the observed local cell-coordinate and row-ownership failures.
- PP-DocLayoutV3 training includes financial reports, but public material does not state a Vietnamese share or a Vietnamese BCTC benchmark. More importantly, its region output does not supply trustworthy canonical cell coordinates in the failed local cases.
- TATR-v1.1-All is trained on PubTables-1M plus corrected FinTabNet. It is deliberately independent of OCR text; official inference requires separate OCR/PDF words for cell content.
- TableFormer is designed to match externally supplied PDF/OCR content to predicted cells and lists PubTabNet, FinTabNet and TableBank in its maintained implementation. That supports a language-neutral structural hypothesis, not Vietnamese accuracy proof.

## Conditional router

```text
page render / native source
  -> PP-OCRv6 source polygons, lines, words, dates and numeric tokens
  -> deterministic source geometry proposes table/row/value lanes

tightly bounded table region
  -> deterministic PP word/line row-lane reconstruction
  -> if exact structural gates pass: stop; do not call another structure model
  -> if an observed structural trigger fires:
       TATR-v1.1-All proposes row/column/header/span geometry
  -> if TATR remains unresolved: retain the region unresolved

every Vietnamese label crop -> VietOCR VGG Transformer
every date/numeric/sign/dash -> PP-OCRv6 plus strict parser/pixel verification
accepted family graph -> deterministic topology, source binding and arithmetic corroboration
```

Allowed structural triggers are observable failures, not model confidence alone: missing row coverage, multi-number cell, row merge/split, ambiguous header-to-axis alignment, truncation, or disagreement between independent source geometry and proposed structure.

## Existing local evidence

The exact `PP-DocLayoutV3 + PaddleOCR-VL-1.6` pipeline is already pinned and measured. Do not rerun or overwrite these experiments.

- E-0007: 25/25 logical rows and 50/50 values on one page, but two label errors and a wrapped-row issue.
- E-0010: four two-row collapses, shifted plausible values and an invalid multi-number cell; strict paired-cell agreement was 92.42%.
- E-0014: a clean VCB page was catastrophically truncated to seven generated table rows and included unrelated margin text.
- E-0016: targeted escalation recovered 26/27 rows and 48/48 paired cells on one VCB region, but only 18/27 rows with 14 invalid cells and 18/36 paired agreement on an MBB region.

These results exclude both Paddle models from the production router. A generated table can look plausible while omitting rows, merging cells or moving a valid number into the wrong accounting row; rebinding after generation cannot reliably recover the lost ownership.

TATR is code/config integrated and its official 115,437,156-byte checkpoint is pinned by SHA-256 `9df416575a3a36ebd0129342d4f597f14d6e5170268f3d52d28584ab4466a501`. Its published benchmark is not an acceptance result for this project. The subsequent frozen, source-blind multi-bank calibration found only 1/5 positive tables with exact topology at IoU 0.50 and 0/5 at IoU 0.75, so TATR remains a shadow challenger and has not been promoted. See `multibank-tatr-structure-calibration-result-v1.md`.

## Evaluation and promotion gate

The calibration panel must be separated by bank and contain clean/borderless, merged or nested, multiline, dense, continuation, scan/native and matched negative-control regions. Crop selection and gold structure are frozen before model access; the inference request contains opaque crop identities and pixels only.

Report at least:

- table-region IoU at 0.50 and 0.75;
- row, column, column-header, projected-row-header and spanning-cell precision/recall/F1;
- exact logical row count and exact two-value-lane topology;
- wrapped-label ownership, nested-detail exclusion and unlabeled-total placement;
- source-bound VietOCR-label-to-row and PP-number/date-to-cell assignment;
- false row merge/split and hard-control false family merge;
- downstream accepted graph delta, unresolved delta, latency and peak RAM/VRAM.

TATR is promoted only when it improves exact downstream topology across at least three banks, retains zero hard-control false merges, does not degrade date/number ownership, and stays within the declared runtime budget. Thresholds must be fixed from calibration without selecting the value that merely reproduces an expected row count.

PP-DocLayoutV3 and PaddleOCR-VL are not promotion candidates for this stack. TableFormer is opened only after a recorded TATR failure and uses the same frozen crop/gold panel; it is never fused merely because it disagrees.

## Primary sources

- PaddleOCR-VL-1.6 paper and official usage: https://arxiv.org/abs/2606.03264 and https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/PaddleOCR-VL.en.md
- PP-DocLayoutV3 / RT-DocLayout: https://arxiv.org/abs/2606.23344 and https://huggingface.co/PaddlePaddle/PP-DocLayoutV3
- Microsoft TATR and PubTables-1M: https://github.com/microsoft/table-transformer and https://arxiv.org/abs/2303.00716
- IBM TableFormer: https://research.ibm.com/publications/tableformer-table-structure-understanding-with-transformers and https://github.com/docling-project/docling-ibm-models

## Claim boundary

This is an engineering selection and bounded evaluation contract. It does not claim that PaddleOCR-VL, PP-DocLayoutV3, TATR or TableFormer has been trained or validated specifically on Vietnamese bank financial statements. It grants no model schema mapping, family identity, numeric replacement, arithmetic repair, canonicalization or export authority.
