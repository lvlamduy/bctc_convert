# Research notes and accuracy hypotheses

This is a decision-oriented paper log, not a list of model claims. A paper contributes an experiment hypothesis; only Vietnamese financial-report fixtures can approve it.

## Adopt into the design

- [PaddleOCR-VL-1.6](https://arxiv.org/abs/2606.03264) concentrates training/refinement on unstable, under-covered regions. Apply the same operational idea without retraining first: mine disagreement/error regions, create targeted crops/variants, and measure recovery by error class instead of running more full-page passes indiscriminately.
- [MinerU2.5](https://arxiv.org/abs/2509.22186) uses coarse global layout followed by native-resolution local recognition. This supports the planned two-stage pipeline: low-resolution page structure, then high-DPI original-coordinate crops for small numeric cells and dark headers.
- [MinerU2.5-Pro](https://arxiv.org/abs/2604.04771) reports heterogeneous-model consistency checks and render-then-verify refinement for hard samples. Adopt independent-family disagreement and rendered reconstruction checks as evidence gates; do not use model agreement as truth when models share a failure.
- [Real5-OmniDocBench](https://arxiv.org/abs/2603.04205) isolates scan, warp, screen-photo, lighting, and skew degradation. Mirror its factor-wise evaluation with Vietnamese bank pages so preprocessing choices have attributable effects.
- [LingDT-VL-OCR / FinDocBench](https://arxiv.org/abs/2603.11044) targets long financial PDFs, cross-page consolidation, heading hierarchy, and decoder-derived cell boxes; FinDocBench measures cross-page table structure and cell IoU. Compare its consolidation and localization ideas with our continuation graph, but retain stricter visible-PDF authority and Role A/Role B separation. The earlier project note called this paper “Agentar-Fin-OCR”; the primary arXiv title was rechecked and corrected on 2026-08-05.
- [PubTables-1M](https://arxiv.org/abs/2110.00061) emphasizes canonical, non-oversegmented table truth and functional headers. Use canonical logical cells/rows and explicit header roles in golden annotations rather than accepting parser-specific HTML as truth.
- [Uncertainty-Aware Complex Scientific Table Data Extraction](https://arxiv.org/abs/2507.02009) applies conformal prediction to table-extraction uncertainty. Evaluate split-conformal thresholds on the frozen Vietnamese holdout for review routing; do not claim calibrated coverage before exchangeability and subgroup behavior are measured.
- [Document dewarping by grid regularization](https://arxiv.org/abs/2203.16850) combines boundaries and text lines. Test a geometry-constrained dewarp candidate only on pages where perspective/curvature is detected, and select it by exact OCR/cell geometry rather than visual smoothness.
- [DeepSeek-OCR 2](https://arxiv.org/abs/2601.20552) explicitly models semantic visual reading order. Benchmark it only as an independent difficult-region/layout reader; generative output cannot directly establish numeric truth.
- [RT-DocLayout / PP-DocLayoutV3](https://arxiv.org/abs/2606.23344) predicts polygonal layout regions and reading order for non-planar documents. Benchmark its claimed robustness on controlled skew, curve, and screen-photo variants; E-0007 only establishes execution on one flat born-digital page.

## Measured implementation findings

- The official full PaddleOCR-VL-1.6 path is layout detection plus regional VLM recognition; testing the 0.9B recognizer alone would not test the document pipeline used in practice.
- A single global BF16 setting is invalid for the tested Transformers path because PP-DocLayoutV3 post-processing converts tensors to NumPy. Per-module FP32 layout and BF16 VLM completed inference with low VRAM.
- On E-0007, generative recognition preserved every numeric value/sign/state but introduced two Vietnamese diacritic errors and split one long row. This directly supports independent geometry, ordered row fusion, and source-exact string disagreement gates.
- Model recency and benchmark leadership do not eliminate packaging gaps: TorchVision and python-docx had to be explicitly pinned after official extras omitted them from the exercised paths.
- E-0008 shows why source selection must precede historical retrieval: collections named yearly/quarterly contained no registered banks, while `data_chart` had exact 27-bank coverage and explicit ReportNormID-like keys. Collection names or similar labels are not sufficient provenance.
- The archive exposes quarter-only and upstream YTD series separately for mapped IDs. Preserve both representations and their source keys, but keep them outside PDF derivation because historical scope, unit, filing revision, and transformation provenance are incomplete.
- E-0010 shows a generative-table failure that aggregate numeric accuracy would hide. On scan page 14, PaddleOCR-VL generated four rows whose labels each collapse two source rows; subsequent values were shifted into plausible neighboring labels. On page 15 it placed `198.242` and `(5.140.484)` in one cell and left the next current-period cell blank. The parser retained the first cell as `INVALID`; no split, arithmetic repair, or historical substitution was allowed.
- The E-0010 failure supports PubTables-1M's canonical logical-structure principle: evaluation must distinguish a wrapped label from two accounting rows collapsed together. It also makes the LingDT/FinDocBench cell-localization hypothesis directly testable: an independent cell-box reader should recover row ownership before any value can be accepted.
- The MinerU2.5 coarse-to-fine idea now has a concrete trigger policy: use low-resolution layout for the page, then reread only the original-resolution cells/row bands implicated by `MERGE_REFERENCE`, extra numeric rows, invalid cells, note mismatch, or numeric disagreement. More full-page generative passes are not the default response.
- E-0011 validates the independent-localization hypothesis on the targeted TCB failures. PP-OCRv6 right-edge/y geometry restored all four page-14 row pairs and localized `198.242` and `(5.140.484)` to separate page-15 rows without splitting a VLM string. Coverage rose from 94.70% to 100% and strict cell agreement from 92.42% to 100% against the same machine reference.
- Geometry and language quality are separable: the E-0011 reader matched 264/264 cells but only 3/140 labels exactly. The operational design must fuse a label reader with independently boxed numeric evidence, retain disagreements, and avoid interpreting any single model's full-page serialization as truth.
- Small punctuation needs a non-language fallback. Three source-visible dashes omitted by OCR were recovered only after a constrained pixel-component check; one more was recognized as `一`. The detector uses relative text-height/axis gates and rejects empty crops, digits, long rules, and multiple components. This is source-image evidence, not arithmetic repair.
- The MBB/VCB coarse document pass exposed a general fuzzy-matching failure: token-set similarity treated an audit sentence containing “báo cáo tài chính” as a statement heading, and treated a normal CDKT title as a subset of the longer off-balance heading. Statement-location v1 now uses full edit similarity for headings, a separately fuzzy discriminative phrase, numeric-line density for title-only main statements, and an ordered global block. The same unchanged rules then found both calibration blocks and excluded both off-balance pages. This is development evidence for structure-first localization, not a production accuracy estimate.
- Direct/indirect titles cannot be evaluated independently because “phương pháp trực tiếp” and “phương pháp gián tiếp” share most tokens. Competitive title margin plus ordered method-specific row anchors removed that conflict on both coarse MBB/VCB runs. The resulting PDF method remains deliberately disconnected from workbook-branch assignment while Q-BOOT-001 is open.

## Planned controlled experiments

1. Compare original versus coarse-to-fine crops at 300/450/600 DPI by exact digit/sign, cell IoU, and latency.
2. Compare PaddleOCR-VL-1.6, MinerU2.5-Pro/available MinerU release, DeepSeek-OCR 2, and a non-generative OCR/geometry stack on the same frozen pages.
3. Measure correlated errors; require independent architecture/decoding paths for “two-reader” evidence.
4. Evaluate word-geometry reconstruction against VLM/table-model proposals on borderless, merged, transposed, and cross-page tables.
5. Fit confidence/review thresholds on development/calibration data, then measure unchanged rules on frozen holdout and by distortion/report subgroup.
6. Completed in E-0011 on page 14: the independent word/cell geometry path recovered all four collapsed row pairs, both value columns, notes, and source boxes. Repeat unchanged on other banks and distortions.
7. Completed in E-0011 on page 15: `198.242` and `(5.140.484)` were independently localized to separate rows without splitting the VLM output. The next test varies DPI/contrast on frozen distortion fixtures.
8. Coarse stage completed in E-0013: the clean 120-DPI PP-OCRv6 pass located and scope-separated both MBB/VCB statement blocks under one unchanged rule set. Next, rerender/reread only the selected eligible plus exclusion-boundary pages at 200 DPI and compare page/scope/method stability before row-level Role B/Role C evaluation.

## Rejection rules

- Benchmark leaderboard scores do not substitute for Vietnamese financial exactness.
- Generated Markdown/HTML without stable source boxes is not acceptable high-confidence evidence.
- Model size, recency, or a plausible arithmetic total cannot repair an unreadable source cell.
