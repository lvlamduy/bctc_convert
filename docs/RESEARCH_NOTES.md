# Research notes and accuracy hypotheses

This is a decision-oriented paper log, not a list of model claims. A paper contributes an experiment hypothesis; only Vietnamese financial-report fixtures can approve it.

## Adopt into the design

- [PaddleOCR-VL-1.6](https://arxiv.org/abs/2606.03264) concentrates training/refinement on unstable, under-covered regions. Apply the same operational idea without retraining first: mine disagreement/error regions, create targeted crops/variants, and measure recovery by error class instead of running more full-page passes indiscriminately.
- [MinerU2.5](https://arxiv.org/abs/2509.22186) uses coarse global layout followed by native-resolution local recognition. This supports the planned two-stage pipeline: low-resolution page structure, then high-DPI original-coordinate crops for small numeric cells and dark headers.
- [MinerU2.5-Pro](https://arxiv.org/abs/2604.04771) reports heterogeneous-model consistency checks and render-then-verify refinement for hard samples. Adopt independent-family disagreement and rendered reconstruction checks as evidence gates; do not use model agreement as truth when models share a failure.
- [Real5-OmniDocBench](https://arxiv.org/abs/2603.04205) isolates scan, warp, screen-photo, lighting, and skew degradation. Mirror its factor-wise evaluation with Vietnamese bank pages so preprocessing choices have attributable effects.
- [Agentar-Fin-OCR / FinDocBench](https://arxiv.org/abs/2603.11044) targets cross-page financial structures and cell-level provenance. Compare its cross-page consolidation and cell-localization ideas with our continuation graph, but retain stricter visible-PDF authority and Role A/Role B separation.
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

## Planned controlled experiments

1. Compare original versus coarse-to-fine crops at 300/450/600 DPI by exact digit/sign, cell IoU, and latency.
2. Compare PaddleOCR-VL-1.6, MinerU2.5-Pro/available MinerU release, DeepSeek-OCR 2, and a non-generative OCR/geometry stack on the same frozen pages.
3. Measure correlated errors; require independent architecture/decoding paths for “two-reader” evidence.
4. Evaluate word-geometry reconstruction against VLM/table-model proposals on borderless, merged, transposed, and cross-page tables.
5. Fit confidence/review thresholds on development/calibration data, then measure unchanged rules on frozen holdout and by distortion/report subgroup.

## Rejection rules

- Benchmark leaderboard scores do not substitute for Vietnamese financial exactness.
- Generated Markdown/HTML without stable source boxes is not acceptable high-confidence evidence.
- Model size, recency, or a plausible arithmetic total cannot repair an unreadable source cell.
