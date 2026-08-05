# E-0010 replay and migration runbook

This runbook rebuilds the six-page TCB paired-reader calibration. It does not turn the result into human gold or production accuracy.

## Identity and version boundary

| Evidence | Identity |
|---|---|
| Searchable Role A PDF | SHA-256 `f48ff3a87b68d7bccc72a4503afa6d83c868b0d1635243e1e3106f5ff559c552` |
| Scan Role B PDF | SHA-256 `7e3f491783a9895d7716199c3981cddebfc060ef7fa125724f421b7b646faafa` |
| Pair/config | `config/experiments/e0009-frozen-paired-calibration.yaml`, SHA-256 `549d17e1569a3e4aca886261c3bd60de125aeb9dd11f3be7370e58401615c72f` |
| Role B preprocessing/inference code | commit `5e4cb033a70735deff3dc136330d078e457e0748` |
| Role B sealing implementation | commit `52469c1afaa7a89ab1771e6054e7e8d6ab33eb0e` |
| Role A geometry v2 build | commit `56af496c82bd2f2d0d2c171a41438ed683e716b4` |
| Final comparison | commit `379396200fb11e7695e341c918f313a308e6206b` |

The historical Role B seal SHA-256 is `2007b9281e0ee5eb80b12f6df069403d91186d710dcff68cb97fb085b7c32d89`; its artifact-set SHA-256 is `350ce77034a2adf1775b7117d1785588d17b905f5819fcc9e564f486a83b75d9`. The Role A seal SHA-256 is `1fd1ac2979c114b5b6938ef6c4e7ea51c0d5ea82bd67edf6abc3633d13d125f8`; its result SHA-256 is `ef61dc102845dbc9c918a92fb75683d3d82378a9774b4f3beba8936c66d6165b`.

Generated OCR, DOCX, PNG, metrics, and seals are intentionally outside Git. Copying and hash-verifying the corresponding `output/calibration/` directories is the only way to preserve those exact historical bytes. A clean inference replay can have different timestamps/export bytes and must create a new seal and experiment identity; it must never overwrite or impersonate E-0010.

## Prerequisites

1. Rebuild `.venv`, `.gpu-venv`, Ubuntu image libraries, and the pinned model cache from `docs/environment/SERVER_REBUILD.md` and `docs/environment/GPU_RUNTIME_RUNBOOK.md`.
2. Verify both PDFs through the source registry and confirm their immutable `CALIBRATION` role.
3. Verify the two pinned model revisions/weights with `scripts/bootstrap/download_paddleocr_vl_models.py --verify-only`.
4. Start every sealed stage from a clean Git worktree. Existing output is never overwritten; use a new run ID/root for replay.

No new package was installed for E-0010. The runtime is the exact frozen E-0007 stack recorded in `docs/environment/SOFTWARE_INVENTORY.md`.

## Clean replay on the current implementation

Select a persistent model cache for migration, or a disposable `/dev/shm` cache for a benchmark:

```bash
export BCTC_E0010_MODEL_CACHE=/dev/shm/bctc-paddlex-e0010-replay
.gpu-venv/bin/python scripts/bootstrap/download_paddleocr_vl_models.py \
  --cache-root "$BCTC_E0010_MODEL_CACHE"
.gpu-venv/bin/python scripts/bootstrap/download_paddleocr_vl_models.py \
  --cache-root "$BCTC_E0010_MODEL_CACHE" \
  --verify-only
```

Preprocess scan pages 10–15 at 200 DPI. The quality gate must retain the original render for a `CLEAN` page; it must not apply CLAHE, deskew, or dewarp merely because those transforms exist.

```bash
.venv/bin/bctc-ai preprocess \
  --pdf vietstock_bctc/TCB/2024/techcombank-vas-bao-cao-tai-chinh-rieng-le-ye24.pdf \
  --run-id e0010-tcb-role-b-replay \
  --dataset-role CALIBRATION \
  --dpi 200 \
  --pages 10-15
```

Resolve the content-addressed run root printed by preprocessing. Run the six pages sequentially; do not load concurrent model copies on the 16 GiB GPU. The following pattern records wall time and GPU sampling for each page:

```bash
export BCTC_E0010_ROLE_B_ROOT=output/calibration/e0010-tcb-role-b-replay/7e3f491783a9895d7716
for page in 0010 0011 0012 0013 0014 0015; do
  .venv/bin/python scripts/diagnostics/run_gpu_benchmark.py \
    --output "$BCTC_E0010_ROLE_B_ROOT/experiments/paddleocr-vl-page-${page}-metrics.json" \
    --interval-ms 250 \
    -- env BCTC_MODEL_CACHE_DIR="$BCTC_E0010_MODEL_CACHE" \
    bash scripts/models/run_paddleocr_vl.sh \
    "$BCTC_E0010_ROLE_B_ROOT/renders/page-${page}.png" \
    "$BCTC_E0010_ROLE_B_ROOT/ocr/paddleocr-vl-page-${page}"
done
```

Seal Role B only after all six metric/result/render files exist and verify:

```bash
.venv/bin/python scripts/experiments/seal_role_b_ocr_run.py \
  --run-root "$BCTC_E0010_ROLE_B_ROOT" \
  --pages 10-15 \
  --model-cache-root "$BCTC_E0010_MODEL_CACHE"
```

Build Role A into a new output root. Geometry v2 is selected by the builder and separates adjacent independent financial tokens using the tracked text-height-relative threshold.

```bash
.venv/bin/python scripts/experiments/build_e0010_role_a.py \
  --output-root output/calibration/e0010-tcb-role-a-replay
```

Compare only after both seals exist. Point `--output` below ignored generated output so the historical tracked E-0010 artifact remains immutable:

```bash
.venv/bin/python scripts/experiments/compare_e0010_paired_readers.py \
  --role-a-seal output/calibration/e0010-tcb-role-a-replay/f48ff3a87b68d7bccc72/role_a_seal.json \
  --role-b-seal "$BCTC_E0010_ROLE_B_ROOT/role_b_ocr_seal.json" \
  --output output/calibration/e0010-replay-comparison.json
```

## Acceptance checks

- Role B must never receive the searchable PDF, Role A rows/seal, a comparison artifact, or historical values.
- History remains unavailable because these rows have no resolved schema IDs; `invoked=false` and mapping/confidence effect `NONE` are required.
- All rows on the visible off-balance page must remain CDKT-ineligible.
- LCTT pages 14→15 must pass the continuation gate using multiple independent signals.
- A cell containing more than one financial number remains `INVALID`; no string split or arithmetic/history repair is allowed.
- `MERGE_REFERENCE`, extra numeric rows, note mismatch, cell-axis mismatch, and numeric disagreement all require reread/reconstruction.
- Reader agreement alone leaves `AUTO_VERIFIED_HIGH=0` because Role B has no independently verified cell geometry.
- Compare new metrics with the tracked artifact as a regression diff. Do not demand byte-identical runtime metrics or silently replace the historical artifact.
