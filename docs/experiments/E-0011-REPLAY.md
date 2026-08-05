# E-0011 replay and server migration runbook

## Scope and immutable identities

E-0011 is a targeted post-failure `CALIBRATION` experiment on the six TCB scan pages already frozen by E-0009/E-0010. It is not a holdout and not a production-accuracy claim. Role B supplies label/page-context proposals; independently sealed Role C supplies PP-OCRv6 word geometry and numeric-cell proposals; Role A is visible only to the final comparison.

| Artifact | Identity |
|---|---|
| Role C inference commit | `d57ceee5ce12bfeac36eaa0b7d059043f45fd16c` |
| Role C sealing implementation commit | `05aee26` |
| E-0011 comparison commit | `a0a034dc24ed67636ed5a5f564c7867cd5a61373` |
| Targeted experiment config | SHA-256 `465360217161fe5196c51934afe497abb1887840f47227041396046dd9c0e39e` |
| Word-box reconstruction config | SHA-256 `5aefee12f3ab760bcd203aa647bc76a0232897f16b11fec221eed0244cbbe5da` |
| Comparison implementation | SHA-256 `e65fb7598532763ed0dfac0d67ce7fc23c5a5841aa18c968da5433b57023ba1d` |
| Role A seal | SHA-256 `1fd1ac2979c114b5b6938ef6c4e7ea51c0d5ea82bd67edf6abc3633d13d125f8` |
| Role B seal | SHA-256 `2007b9281e0ee5eb80b12f6df069403d91186d710dcff68cb97fb085b7c32d89` |
| Role C seal | SHA-256 `0c0e3972d1d050bb24abe05019040e66b089fb0cf9a5501d0cd8a017ef560461` |
| Role C artifact set | SHA-256 `968e6bf93a5af2e6552a2820350c075415d29905df279c31c54d2b095ae6c3a2` |
| Tracked E-0011 result | SHA-256 `4df17c6b19e5121ae047c699e52f4a81662b3580c07e1b492d0ca4f1e38cf03c` |

The Role B seal records the historical sealing implementation hash. The current `sealing.py` has since gained Role C support, so it is intentionally not byte-identical. Comparison still verifies every Role B render, output, and metrics file against the immutable seal; it records the implementation mismatch instead of rewriting E-0010 history.

## What Git does and does not contain

Git contains code, configuration, model/runtime manifests, this runbook, and the 511 KiB machine-readable comparison result. Git intentionally excludes source PDFs, renders, OCR outputs, run manifests, model weights, virtual environments, and seals under `output/`.

For an exact comparison replay, transfer and hash-verify these directories in addition to the repository:

```text
output/calibration/e0010-tcb-role-a/f48ff3a87b68d7bccc72/
output/calibration/e0009-tcb-role-b/7e3f491783a9895d7716/
output/calibration/e0011-tcb-role-c/7e3f491783a9895d7716/
```

The first two are reconstructed or transferred as documented in `E-0010-REPLAY.md`. Copying only the three seal JSON files is insufficient: the comparison re-hashes every referenced render/result/metrics/manifest artifact.

## Runtime reconstruction

No new package was installed during row reconstruction or comparison. The control plane uses the OpenCV, NumPy, PyYAML, and other versions locked by `uv.lock`. Role C uses the isolated 125-package runtime and the official PaddlePaddle 3.3.0 CPU FP32 backend documented in `docs/environment/SOFTWARE_INVENTORY.md` and `docs/environment/GPU_RUNTIME_RUNBOOK.md`.

Rebuild and verify the environments and all four pinned models first:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install uv==0.12.1
.venv/bin/uv sync --frozen --extra dev
sudo bash scripts/bootstrap/install_gpu_system_deps.sh
BCTC_GPU_UV_CACHE_DIR=/dev/shm/bctc-ai-uv-cache \
  bash scripts/bootstrap/create_gpu_runtime.sh
.gpu-venv/bin/python scripts/diagnostics/gpu_model_runtime_smoke.py
.venv/bin/uv pip check --python .gpu-venv/bin/python
.gpu-venv/bin/python scripts/bootstrap/download_paddleocr_vl_models.py \
  --cache-root /dev/shm/bctc-paddlex-e0007
.gpu-venv/bin/python scripts/bootstrap/download_paddleocr_vl_models.py \
  --cache-root /dev/shm/bctc-paddlex-e0007 --verify-only
```

Required PP-OCRv6 weights are:

- detector revision `8e0f56fb2ef86b461d99cfc7ac5c137738985f61`, weight SHA-256 `85218d2e3d98f5a21c58b4220627be923a97aee5db3cc71f39536ab31ac53960`;
- recognizer revision `e5a92bcbc5cc1b494628e458d267778f0704fd7c`, weight SHA-256 `1b01c79a914587933f615569e75de54f2e638ebb5d3f3b3c1b38c24ede8c7319`.

## Fresh Role C inference

Fresh inference is useful to validate a rebuilt server, but wall times, manifests, seal timestamps, and possibly model serialization bytes will differ. It must use a new run root and experiment identity; it must not overwrite or impersonate the historical E-0011 evidence.

After restoring the exact E-0010 Role B renders, start from the clean inference commit:

```bash
git checkout d57ceee5ce12bfeac36eaa0b7d059043f45fd16c
export BCTC_E0011_ROLE_B_ROOT=output/calibration/e0009-tcb-role-b/7e3f491783a9895d7716
export BCTC_E0011_ROLE_C_ROOT=output/calibration/e0011-tcb-role-c-replay/7e3f491783a9895d7716
for page in 0010 0011 0012 0013 0014 0015; do
  BCTC_MODEL_CACHE_DIR=/dev/shm/bctc-paddlex-e0007 \
  BCTC_DATASET_ROLE=CALIBRATION \
    bash scripts/models/run_ppocrv6_word_boxes.sh \
      "$BCTC_E0011_ROLE_B_ROOT/renders/page-$page.png" \
      "$BCTC_E0011_ROLE_C_ROOT/ppocrv6-page-$page"
done
```

The original six sequential CPU runs took 191.635581 seconds in total and emitted 586 lines and 4,024 word tokens. Timing is diagnostic, not a byte-identity gate.

Seal the fresh run only after switching to the clean sealing implementation:

```bash
git checkout 05aee26
.venv/bin/python scripts/experiments/seal_independent_geometry_run.py \
  --run-root "$BCTC_E0011_ROLE_C_ROOT" \
  --pages 10-15 \
  --role-b-seal "$BCTC_E0011_ROLE_B_ROOT/role_b_ocr_seal.json" \
  --model-cache-root /dev/shm/bctc-paddlex-e0007
```

## Exact comparison replay

An exact replay requires the three original output directories listed above. With those bytes restored, use the clean comparison commit and write below ignored `output/`; the runner refuses to overwrite the tracked historical result:

```bash
git checkout a0a034dc24ed67636ed5a5f564c7867cd5a61373
.venv/bin/python scripts/experiments/compare_e0011_geometry_recovery.py \
  --output output/calibration/e0011-comparison-replay.json
sha256sum output/calibration/e0011-comparison-replay.json
```

The expected comparison SHA-256 is `4df17c6b19e5121ae047c699e52f4a81662b3580c07e1b492d0ca4f1e38cf03c`. A mismatch is a new run or a drift and must receive a new experiment identity.

Expected gates are 140 one-to-one row matches, 132/132 exact financial rows, 264/264 exact cells, 50/50 note references, zero invalid cells, zero off-balance rows eligible for CDKT, three pixel-supported dash recoveries, one OCR-glyph dash normalization, one accepted page-14→15 continuation, 11 arithmetic passes, one dash-caused `NOT_TESTABLE`, and zero automatic high-confidence promotions.
