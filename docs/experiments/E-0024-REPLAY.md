# E-0024 replay: Vietnamese line recognizer

## Claim boundary

This calibration experiment asks whether an independent Vietnamese single-line
reader improves fixed financial-statement headings and labels. It does not test
numeric extraction, geometry, schema mapping, production accuracy or E-0022.
The challenger receives crop pixels and four allowlisted request fields only;
references and the PP-OCRv6 baseline are unavailable during decoding.

## Immutable identities

- Crop-selection commit: `1d466260463135a8d4b6389c4d5e6323aeae6008`
- Pre-inference mechanism commit: `c351c70c9353a0a927d3935d16bb276a4d8f6b88`
- Config SHA-256: `ee0a18b4e96cd42d74a35e016d8ed2a20a68fae261f9b8ee4ddcc056ffd7d013`
- Crop-manifest SHA-256: `c8cece50c8e22a24bdc391ace3836c6735e82f8f1183f33533a3315b7c7b7cfd`
- Reference-blind request SHA-256: `4f94bd2e7898595721b8b56ef7f07944430ef8901936314ddce093b2cc7cc11f`
- VietOCR result SHA-256: `db3c34c8b866922c47dc863a2a14965db16f84918392c4d6293b23d1f613563a`
- VietOCR run-manifest SHA-256: `ac1f3c924e41c8077776129b6e5abad16e13e3e3c5a1092fad98255c20eb6611`
- Evaluation artifact SHA-256: `18b896f7174992dd16a4372a5c24ec46df967e763223b9c85b25919ca5e89289`

The run root is
`output/calibration/e0024-vietnamese-line-recognizer/ee0a18b4e96cd42d74a3`.
Large crops, requests and inference outputs remain outside Git; their hashes
bind this replay to their exact contents.

## Runtime reconstruction

The official wheel, configs and weight are pinned by URL, size and SHA-256 in
`config/models/vietocr-0.3.13.toml`.

```bash
PYTHONPATH=src .venv/bin/python scripts/bootstrap/install_vietocr_line_runtime.py \
  --runtime-root /workspace/bctc-ai-runtime/vietocr-0.3.13
```

The runner disables socket/DNS access, prevents CNN pretrained downloads and
loads only local weights. It does not alter the base environments.

## Replay commands

```bash
PYTHONPATH=src .venv/bin/python \
  scripts/experiments/build_e0024_line_crop_registry.py

RUN_ROOT=output/calibration/e0024-vietnamese-line-recognizer/ee0a18b4e96cd42d74a3

PYTHONPATH=src .venv/bin/python \
  scripts/experiments/prepare_e0024_line_reader_request.py \
  --crop-manifest "$RUN_ROOT/crop_manifest.json" \
  --output "$RUN_ROOT/vietocr_inference_request.json"

PYTHONPATH=src .gpu-venv/bin/python \
  scripts/models/run_vietocr_line_reader.py \
  --request "$RUN_ROOT/vietocr_inference_request.json" \
  --output-directory "$RUN_ROOT/vietocr-reader" \
  --runtime-root /workspace/bctc-ai-runtime/vietocr-0.3.13 \
  --config config/models/vietocr-0.3.13.toml

PYTHONPATH=src .venv/bin/python \
  scripts/experiments/capture_e0024_line_recognizer.py \
  --crop-manifest "$RUN_ROOT/crop_manifest.json" \
  --inference-directory "$RUN_ROOT/vietocr-reader" \
  --output docs/experiments/E-0024-vietnamese-line-recognizer.json
```

## Result and decision

On 37 frozen lines, PP-OCRv6 versus VietOCR produced:

- exact lines: 0/37 versus 30/37;
- exact titles: 0/10 versus 6/10;
- CER: 14.9518% versus 0.6431%;
- WER: 55.2448% versus 2.7972%;
- empty or suffix-truncated lines: 0 versus 0.

All three predeclared bounded gates pass. VietOCR's seven non-exact lines contain
eight substitutions: seven diacritic-only and one capitalization edit, with no
base-character edit, insertion, deletion or truncation. One incorrect
`VỐN`→`VÓN` output has higher decoded confidence than some exact outputs, so
confidence alone is not an acceptance gate.

The accepted scope is a semantic proposal for headings and labels on an
immutable PP-OCRv6 source box. PP-OCRv6 remains the geometry and numeric reader;
raw text, crop, disagreement and provenance must be retained. The result grants
no automatic correction, period, unit, sign, value, mapping, holdout or
production authority.
