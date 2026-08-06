# Document-model runtime runbook

## Scope and current approval

This runbook reconstructs the isolated RTX 5070 Ti (`sm_120`) runtime, the exact E-0007 PaddleOCR-VL stack, the E-0011 PP-OCRv6 word-box stack, and the calibration-only TATR structure reader. Runtime kernels have passed, but production approval remains blocked until frozen multi-institution, scan/distortion, cross-page, and holdout accuracy gates pass.

## Capacity and host prerequisites

- Ubuntu 22.04 x86-64 and Python 3.11.
- NVIDIA Linux driver at least 580.65.06; verified host driver 595.80.
- At least 7 GiB free on the filesystem holding `.gpu-venv`.
- At least 8 GiB free for the uv wheel cache during installation.
- At least 3 GiB free for the four document models.
- Add 116 MiB for the pinned TATR checkpoint when the structure-reader
  calibration is enabled.
- A cache filesystem may be `noexec`; the virtual environment filesystem must allow executable mappings.

After adding the pinned Paddle 3.3.0 CPU backend, the measured footprints on 2026-08-05 were 6,383,286,857 bytes for `.gpu-venv`, 7,213,410,166 bytes for the warm uv cache (including the retained 193,703,893-byte verified Paddle wheel), and 2,213,856,016 bytes for the four-model cache.

After the Paddle backend was added beside the 17 GiB PDF corpus, the 40 GiB workspace filesystem had about 6.0 GiB free. That is enough to run the accepted environment but below the builder's 7 GiB preflight for a second environment. Before an upgrade, use `df -h /workspace /dev/shm`; increase/relocate storage rather than attempting a side-by-side rebuild without the required headroom. Routine control-plane backups exclude `.gpu-venv` and measured only about 2.9 MiB in aggregate during bootstrap.

## Rebuild

From a clean repository checkout with the control-plane `.venv` already synced:

```bash
sudo bash scripts/bootstrap/install_gpu_system_deps.sh
BCTC_GPU_UV_CACHE_DIR=/dev/shm/bctc-ai-uv-cache \
  bash scripts/bootstrap/create_gpu_runtime.sh
.gpu-venv/bin/python scripts/diagnostics/gpu_model_runtime_smoke.py
.venv/bin/uv pip check --python .gpu-venv/bin/python
```

The runtime builder refuses to overwrite an existing environment, checks both required shared libraries and disk capacity, installs the official CUDA 13.0 PyTorch/TorchVision pair, downloads and verifies the official PaddlePaddle 3.3.0 CPU wheel, constrains the remaining dependency closure, diffs all 125 installed versions against the freeze, and runs both the CUDA and Paddle CPU kernel smoke.

After reconstruction, run `.venv/bin/bctc-ai audit`. In addition to the explicit commands above, the audit records the current smoke payload, package compatibility, tracked freeze hash, exact installed-freeze match, and local acceptance in `BOOTSTRAP_MANIFEST.json`. `PASS` approves only the runtime mechanism for model experiments; it does not approve model accuracy for production.

Select a model cache. Use persistent storage for service deployment; `/dev/shm` is acceptable for a disposable benchmark and avoids filling the 40 GiB workspace filesystem:

```bash
export BCTC_MODEL_CACHE_DIR=/dev/shm/bctc-paddlex
export HF_HOME=/dev/shm/bctc-huggingface
.gpu-venv/bin/python scripts/bootstrap/download_paddleocr_vl_models.py \
  --cache-root "$BCTC_MODEL_CACHE_DIR"
.gpu-venv/bin/python scripts/bootstrap/download_paddleocr_vl_models.py \
  --cache-root "$BCTC_MODEL_CACHE_DIR" \
  --verify-only
.gpu-venv/bin/python scripts/bootstrap/download_tatr_model.py \
  --cache-root "$BCTC_MODEL_CACHE_DIR"
.gpu-venv/bin/python scripts/bootstrap/download_tatr_model.py \
  --cache-root "$BCTC_MODEL_CACHE_DIR" \
  --verify-only
```

The TATR downloader verifies the full revision plus the exact config,
preprocessor, and safetensors hashes from `config/models/tatr-v1.1-all.toml`.
It does not change the historical four-model downloader or the base runtime
manifest hashes bound into E-0010 through E-0016.

Run a single image without overwriting prior output:

```bash
BCTC_MODEL_CACHE_DIR=/dev/shm/bctc-paddlex \
  bash scripts/models/run_paddleocr_vl.sh INPUT.png OUTPUT_DIRECTORY
```

Run PP-OCRv6 on an image that has already passed the page-quality/preprocessing gate:

```bash
BCTC_MODEL_CACHE_DIR=/dev/shm/bctc-paddlex \
BCTC_DATASET_ROLE=CALIBRATION \
  bash scripts/models/run_ppocrv6_word_boxes.sh PREPROCESSED.png OUTPUT_DIRECTORY
```

The PP-OCRv6 runner refuses an existing output directory and a dirty Git worktree, verifies both local model hashes, blocks all process socket connections, disables implicit orientation/unwarp, and writes only `ocr_result.json` plus an atomic `run_manifest.json`. It does not render an image or download a font. `BCTC_ALLOW_DIRTY_OCR_SMOKE=true` exists only for non-evidence development smoke tests and is recorded as `code.dirty=true`; such output cannot be sealed or promoted.

Run TATR only on a tightly bounded table crop whose source and transform are
already registered:

```bash
PYTHONPATH=src .gpu-venv/bin/python scripts/models/run_tatr_structure.py \
  --input TABLE_CROP.png \
  --output-directory output/calibration/TATR_RUN \
  --model-cache "$BCTC_MODEL_CACHE_DIR" \
  --dataset-role CALIBRATION
```

The runner refuses dirty Git or output replacement, verifies the model/runtime
hashes, disables network access, keeps the checkpoint-native 800-pixel
longest-edge preprocessing, and records all object-query probabilities and
source-coordinate boxes. It has structure-proposal authority only; it cannot
read or replace a financial value, bind periods, map IDs, or promote confidence.
Transformers 5.14.1 strictly rejects the official checkpoint's legacy
top-level `dilation=null`. The versioned runner leaves the model artifact
unchanged and resolves only that exact field to the model default `false` in
memory. Any changed value, additional compatibility field, or Transformers
version fails closed.
The same checkpoint's processor stores only `longest_edge=800`; the current
processor requires a shortest/longest pair. The runner resolves it in memory to
`shortest_edge=800,longest_edge=800`, retaining aspect ratio and an 800-pixel
maximum edge. It records both representations and refuses any source-key drift.

For many pages, use the checkpointed runner so the detector and recognizer load
once per process:

```bash
BCTC_MODEL_CACHE_DIR=/dev/shm/bctc-paddlex-e0007 \
BCTC_DATASET_ROLE=CALIBRATION \
  bash scripts/models/run_ppocrv6_word_boxes_batch.sh \
  output/calibration/RUN/DOCUMENT/manifest.json \
  output/calibration/ROLE_C_BATCH \
  10-15
```

The input must be the top-level preprocessing manifest. Set
`BCTC_BATCH_RESUME=true` with the identical command after interruption. The
runner verifies the immutable dataset role, source/render/config/code/model
hashes, and every completed page before continuing. Full input/output,
parameter, checkpoint, transfer, and recovery rules are in
`BATCH_OCR_RUNBOOK.md`.

Measure the same run:

```bash
.venv/bin/python scripts/diagnostics/run_gpu_benchmark.py \
  --output output/METRICS.json \
  --interval-ms 250 \
  -- env BCTC_MODEL_CACHE_DIR=/dev/shm/bctc-paddlex \
  bash scripts/models/run_paddleocr_vl.sh INPUT.png OUTPUT_DIRECTORY
```

For a clean born-digital page, E-0007 explicitly disabled orientation classification and unwarping. Production code must enable them only after the page-quality gate detects rotation/warp; the benchmark setting is not a global preprocessing rule.

## Failure history retained from bootstrap

| Attempt | Outcome | Root cause | Durable correction |
|---|---|---|---|
| Runtime temp 0 | FAIL before import | virtual environment created in `/dev/shm`, which is mounted `noexec`; shared objects could not be mapped | environment moved to `.gpu-venv`; only caches use `/dev/shm` |
| Import 1 | FAIL | `libGL.so.1` absent | install `libgl1` |
| Import 2 | FAIL | `libgthread-2.0.so.0` absent | install `libglib2.0-0` |
| E-0007 attempt 1 | FAIL before layout inference | TorchVision absent even though the document-parser extra was installed | pin official TorchVision 0.27.0+cu130 alongside PyTorch 2.12.0+cu130 |
| E-0007 attempt 2 | FAIL after model load | global BF16 made PP-DocLayoutV3 post-process call NumPy on BF16 | layout FP32; VLM BF16 in per-module configuration |
| E-0007 attempt 3 | inference succeeded, export FAIL | CLI `save_all` imported missing `docx` | pin python-docx 1.2.0 |
| E-0007 attempt 4 | PASS | full inference and all registered exports completed | retain as the current logic-development baseline |
| E-0011 backend preflight | GPU wheel rejected before install | Paddle 3.3.0 CUDA 13.0 requires exact NVIDIA dependency versions that conflict with PyTorch 2.12 | use the official hash-pinned Paddle 3.3.0 CPU FP32 backend for PP-OCRv6; keep PyTorch CUDA unchanged |
| E-0011 runtime attempt 1 | FAIL during detection | oneDNN/MKLDNN could not convert a PP-OCRv6 PIR array attribute | disable MKLDNN; use Paddle static CPU FP32 |
| E-0011 runtime attempt 2 | core OCR PASS, export path rejected | generic CLI called its renderer and attempted an unpinned font download after inference | replace CLI export with the network-blocked JSON-only runner |
| E-0011 runtime attempt 3 | development smoke PASS | JSON-only runner returned 50 line boxes and 380 word tokens from TCB scan page 15 in 24.11 seconds | commit runner, then rerun from a clean commit for evidence |
| E-0011 sealed run | PASS | six clean TCB renders produced 586 line boxes and 4,024 word tokens in 191.635581 seconds | seal every render/result/manifest; compare only after Role C completion |
| E-0012 batch mechanism | PASS | clean batch page 15 was byte-identical to E-0011, no-op resume did not reload models, and the batch/helper-aware seal passed | use the checkpointed runner for multi-page calibration; this adds no accuracy sample |
| E-0014 MBB/VCB acquisition | PASS with retained reader failures | four seals cover 13 clean 200-DPI pages; Role B truncated dense VCB page 9 and encountered multi-table/variable-leading-column layouts | accept acquisition only; use Role C geometry plus all-block Role B parsing and explicit coverage before row comparison |
| TATR attempt 1 | FAIL before inference; no output published | official nested-backbone checkpoint stores obsolete top-level `dilation=null`, rejected by Transformers 5.14.1 strict bool validation | add an exact-version, exact-field in-memory `null→false` compatibility rule; preserve the hashed checkpoint unchanged and rerun only from a new clean commit |
| TATR dirty smoke 2 | FAIL before tensor inference; no output published | official legacy processor stores only `longest_edge=800`, while Transformers 5.14.1 requires both shortest and longest edges | resolve only this exact representation in memory to `800/800`, preserve aspect ratio and checkpoint bytes, and test source-key/version drift |
| TATR dirty smoke 3 | PASS mechanism only | one MBB full-table crop completed in 0.187929 s at 249.096680 MiB peak allocated VRAM; all 125 queries retained, with 36/30/23 row boxes at 0.5/0.7/0.9 | commit the compatibility rules, then rerun clean on both frozen crops; never choose a threshold from expected row count |

The E-0007 measured failures and final pass remain in `docs/experiments/E-0007-paddleocr-vl-runtime.json`. E-0011 retains its backend/runtime attempts and exact migration procedure in `docs/experiments/E-0011-REPLAY.md`; its tracked comparison result is `docs/experiments/E-0011-tcb-geometry-recovery.json`. E-0012 locks the clean batch/resume/seal mechanism in `docs/experiments/E-0012-REPLAY.md`. E-0014 records its four reader seals, exact settings, and retained VCB/MBB failures in `docs/experiments/E-0014-REPLAY.md`. Do not delete failed attempts from these records.

## Known warnings and gates

- Transformers 5.14.1 emits an image-processor deprecation warning and warns about `mrope_section` under the default rope type. The fixture passed despite them, but any model/Transformers upgrade must rerun exact cell and label regression.
- Generated HTML/Markdown is a proposal. E-0007 split one long row and misspelled two labels while reading all 50 numeric cells exactly.
- Values and note references are excluded from the ordered alignment path score. They are compared only after structural alignment so model agreement cannot circularly select a row mapping.
- Model downloads must use the pinned revision helper; PaddleX's convenient auto-download follows the current upstream state and is not sufficient for a reproducible production build.
- The PP-OCRv6 CPU backend is a deliberate dependency-isolation decision, not a model downgrade. Any future Paddle GPU runtime must be a separate frozen environment and must rerun exact OCR regression before adoption.

## Rollback and cleanup

Preserve an old runtime for diagnosis by renaming it before building another version:

```bash
mv .gpu-venv .gpu-venv.retired-YYYYMMDD
```

Disposable benchmark caches may be removed only after their revision and weight hashes have been recorded. `.gpu-venv`, model weights, uv caches, rendered pages, and generated output are excluded from Git; the manifests, scripts, metrics summary, and reconstruction logic are versioned.
