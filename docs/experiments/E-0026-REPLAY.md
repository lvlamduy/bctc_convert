# E-0026 replay: aspect-preserving DeepSeek line reader

## Claim boundary

This calibration experiment tests DeepSeek-OCR-2 as a bounded Vietnamese
semantic proposal reader on the unchanged 37 E-0024 source-line crops. It also
replays those source-bound proposals through fixed PP-OCRv6 geometry and
multi-signal statement discovery on the unchanged E-0013 MBB/VCB batches.

It does not test numeric recognition, period/unit/sign truth, schema mapping,
Excel output, a bank/period-disjoint split, production accuracy or E-0022.

## Immutable identities

- E-0025 mechanism commit: `a44b08bdd1378e4cd1524ee02d426ad6dbb4e2c0`
- E-0026 inference commit: `a013cb8`
- Formal evaluator commit: `3ea0fb9afc5de2dabc2a465e0e19c7019ffb37b4`
- Experiment-config SHA-256: `d9a6312db6a583aa8677e90a1e9f7a9d5a9062c7ab77b524e8315860e473d292`
- Crop-manifest SHA-256: `c8cece50c8e22a24bdc391ace3836c6735e82f8f1183f33533a3315b7c7b7cfd`
- Reference-blind request SHA-256: `4f94bd2e7898595721b8b56ef7f07944430ef8901936314ddce093b2cc7cc11f`
- E-0025 result/manifest SHA-256: `4a8ddaf5082f1401514d211d8ebc31a7fe705149277314128ad18b62aab14200` / `ce42c3247fb92283799d553b7b578a4c6a9591ab994c9f9daca949545315fc3d`
- E-0026 result/manifest SHA-256: `f490fb89a497f6c45162496da7cb1fb6286784b94a15b23dabc70d5e3b1c6579` / `68de0cbf9c9d4fe084493dc85778b398c6cdf6dd193da1b455aea56d9147ba52`
- Formal evaluation artifact SHA-256: `1753f382e141fbeb48e94cb1ef30a89ebd08cb2f1bb0836bdbf960e811eb33dd`

The inference outputs remain outside Git under `output/calibration/`. Their
hashes bind the tracked evaluation artifact to the exact model outputs.

## Runtime reconstruction

The model and compatibility overlay are hash-locked by the DeepSeek model
configuration and bootstrap records. On this host the bounded reader uses:

```bash
PYTHONPATH=/workspace/bctc-ai-runtime/deepseek-ocr2-overlay:/dev/shm/bctc-deepseek-ocr2-deps:src \
  .gpu-venv/bin/python scripts/models/run_deepseek_ocr2_line_reader.py \
  --request output/calibration/e0024-vietnamese-line-recognizer/ee0a18b4e96cd42d74a3/vietocr_inference_request.json \
  --output-directory <new-output-directory> \
  --model-root /dev/shm/bctc-deepseek-ocr2-cache/official_models/DeepSeek-OCR-2 \
  --config config/models/deepseek-ocr2-line-v2.toml
```

The v2 configuration preserves line aspect ratio with the official padded crop
path, limits generation to 128 tokens and rejects output over 512 characters.
The reader receives no reference text.

## Formal capture

```bash
PYTHONPATH=src .venv/bin/python \
  scripts/experiments/capture_e0026_deepseek_line_benchmark.py \
  --e0025-directory output/calibration/e0025-deepseek-bounded-line-recognizer/a44b08b/deepseek-reader \
  --e0026-directory output/calibration/e0026-deepseek-aspect-preserving-line/a013cb8/deepseek-reader
```

The command requires clean Git, verifies every frozen input and inference
artifact hash, refuses overwrite, and confirms that semantic fusion never reads
reference fields.

## Result and decision

DeepSeek v1 direct resize is rejected: 0/37 exact lines, 0/10 exact titles, CER
123.7138%, seven structural rejections and one 36,314-character hallucination.

Aspect-preserving DeepSeek v2 produces:

- exact lines: 27/37;
- exact titles: 5/10;
- CER/WER: 0.9646% / 3.8462%;
- character edits: 1 base-character, 10 diacritic-only, 1 insertion and 0
  deletions;
- empty, truncated or structurally rejected outputs: 0;
- maximum raw output length: 55 characters;
- wall time: 23.1651 seconds;
- peak allocated VRAM: 7,058.903 MiB.

The fixed-grid replay emits 19 MBB and 18 VCB proposals with zero fusion
rejections. Page/type/scope, off-balance exclusion, continuation, DIRECT LCTT
and both 8.5 runner-up margins remain exactly equal to the unchanged baseline.

DeepSeek v2 therefore passes only the bounded semantic-proposal gate. PP-OCRv6
remains geometry authority and a separate numeric reader remains mandatory.
VietOCR is slightly better on these same calibration crops (30/37 lines, 6/10
titles and 0.6431% CER), but stays an optional challenger because no bank- and
period-separated downstream comparison exists. Fine-tuning remains deferred.
