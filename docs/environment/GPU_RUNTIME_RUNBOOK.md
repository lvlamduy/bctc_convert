# GPU and PaddleOCR-VL runtime runbook

## Scope and current approval

This runbook reconstructs the isolated RTX 5070 Ti (`sm_120`) runtime and the exact E-0007 model stack. The runtime and one logic-development inference have passed. Production approval remains blocked until frozen multi-institution, scan/distortion, cross-page, and holdout accuracy gates pass.

## Capacity and host prerequisites

- Ubuntu 22.04 x86-64 and Python 3.11.
- NVIDIA Linux driver at least 580.65.06; verified host driver 595.80.
- At least 7 GiB free on the filesystem holding `.gpu-venv`.
- At least 8 GiB free for the uv wheel cache during installation.
- At least 3 GiB free for the two document models.
- A cache filesystem may be `noexec`; the virtual environment filesystem must allow executable mappings.

The measured footprints on 2026-08-05 were 5,663,276,925 bytes for `.gpu-venv`, 5,585,681,842 bytes for the warm uv cache, and 2,074,691,105 bytes for the model cache.

After the runtime was installed beside the 17 GiB PDF corpus, the 40 GiB workspace filesystem had about 6.70 GiB free. That is enough to run the accepted environment but below the builder's 7 GiB preflight for a second environment. Before an upgrade, use `df -h /workspace /dev/shm`; increase/relocate storage rather than attempting a side-by-side rebuild without the required headroom. Routine control-plane backups exclude `.gpu-venv` and measured only about 2.9 MiB in aggregate during bootstrap.

## Rebuild

From a clean repository checkout with the control-plane `.venv` already synced:

```bash
sudo bash scripts/bootstrap/install_gpu_system_deps.sh
BCTC_GPU_UV_CACHE_DIR=/dev/shm/bctc-ai-uv-cache \
  bash scripts/bootstrap/create_gpu_runtime.sh
.gpu-venv/bin/python scripts/diagnostics/gpu_model_runtime_smoke.py
.venv/bin/uv pip check --python .gpu-venv/bin/python
```

The runtime builder refuses to overwrite an existing environment, checks both required shared libraries and disk capacity, installs the official CUDA 13.0 PyTorch/TorchVision pair, constrains the remaining dependency closure, diffs all 122 installed versions against the freeze, and runs the GPU smoke.

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
```

Run a single image without overwriting prior output:

```bash
BCTC_MODEL_CACHE_DIR=/dev/shm/bctc-paddlex \
  bash scripts/models/run_paddleocr_vl.sh INPUT.png OUTPUT_DIRECTORY
```

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

The three measured failures and final pass remain in `docs/experiments/E-0007-paddleocr-vl-runtime.json`. Do not delete failed attempts from the experimental record.

## Known warnings and gates

- Transformers 5.14.1 emits an image-processor deprecation warning and warns about `mrope_section` under the default rope type. The fixture passed despite them, but any model/Transformers upgrade must rerun exact cell and label regression.
- Generated HTML/Markdown is a proposal. E-0007 split one long row and misspelled two labels while reading all 50 numeric cells exactly.
- Values and note references are excluded from the ordered alignment path score. They are compared only after structural alignment so model agreement cannot circularly select a row mapping.
- Model downloads must use the pinned revision helper; PaddleX's convenient auto-download follows the current upstream state and is not sufficient for a reproducible production build.

## Rollback and cleanup

Preserve an old runtime for diagnosis by renaming it before building another version:

```bash
mv .gpu-venv .gpu-venv.retired-YYYYMMDD
```

Disposable benchmark caches may be removed only after their revision and weight hashes have been recorded. `.gpu-venv`, model weights, uv caches, rendered pages, and generated output are excluded from Git; the manifests, scripts, metrics summary, and reconstruction logic are versioned.
