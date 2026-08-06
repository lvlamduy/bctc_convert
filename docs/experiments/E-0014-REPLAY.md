# E-0014 replay — MBB/VCB 200-DPI reader acquisition

## Claim boundary

E-0014 locks quality-gated 200-DPI inputs and four independent reader seals for
two calibration filings. It proves input/output identity and reader completion,
not row/cell accuracy, schema mapping, human gold, holdout performance,
confidence calibration, or production readiness. The visible failures retained
in the artifact are escalation examples, not a scored denominator.

## Frozen implementation and runtime

- Inference/preprocessing commit:
  `116c1879cef7f3f63b2bf1e7d71561d8c7ef78c8` (clean).
- Runtime manifest SHA-256:
  `9141e0a4177f66f152bdb9eecbbfdbdd3add566dbabb81b43207a018c1ba18d8`.
- Package freeze SHA-256:
  `c0e8c43f84360a8eb0ebeff1ef5de43969bdd291eb2c7cee363c35ef2c78437b`.
- Role B config SHA-256:
  `e6e60f949e31c8d6afc58fb4dc28acf55da8b569a6d608cab319c6a7f2793042`.
- Role C config SHA-256:
  `a200fbbc8ba85460c9233875a7a025e8d08d892172d353ed820f69fd258e997b`.

All algorithm and model revision/weight hashes are in
`E-0014-mbb-vcb-200dpi-reader-seals.json`. E-0014 installed no package, model,
driver, or operating-system component.

## Preconditions

1. Rebuild `.venv`, `.gpu-venv`, and the pinned model cache using
   `../environment/SERVER_REBUILD.md` and `../environment/GPU_RUNTIME_RUNBOOK.md`.
2. Transfer and hash-verify the registered MBB/VCB PDFs. Their append-only role
   must already be `CALIBRATION`.
3. Check out the exact inference commit and require an empty
   `git status --porcelain` before preprocessing and inference.
4. Use new run/output paths. Never overwrite or edit an E-0014 artifact.

## Render and quality-gate only the selected pages

```bash
git checkout 116c1879cef7f3f63b2bf1e7d71561d8c7ef78c8
git status --porcelain

.venv/bin/bctc-ai preprocess \
  --pdf 'vietstock_bctc/MBB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf' \
  --run-id e0014-mbb-selected-200dpi-replay \
  --dataset-role CALIBRATION \
  --dpi 200 \
  --pages 10-15

.venv/bin/bctc-ai preprocess \
  --pdf 'vietstock_bctc/VCB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf' \
  --run-id e0014-vcb-selected-200dpi-replay \
  --dataset-role CALIBRATION \
  --dpi 200 \
  --pages 8-14
```

The original run classified all 13 pages `CLEAN`, found zero difficult regions
and zero perspective candidates, and selected the original renders. A replay
must not force CLAHE, deskew, dewarp, or a region variant. If a current quality
result differs, retain it as a new experiment instead of impersonating E-0014.

## Run Role C with atomic checkpoints

Set the content-addressed roots printed by preprocessing, then run one process
per document. The two CPU processes may run concurrently when host resources
allow it; neither may share an output directory.

```bash
export BCTC_E0014_MODEL_CACHE=/dev/shm/bctc-paddlex-e0007
export BCTC_DATASET_ROLE=CALIBRATION
export BCTC_PADDLE_CPU_THREADS=8
export BCTC_E0014_MBB_ROOT=output/calibration/e0014-mbb-selected-200dpi-replay/9853cc4909dc73ddea99
export BCTC_E0014_VCB_ROOT=output/calibration/e0014-vcb-selected-200dpi-replay/295f397de287f84c26da

bash scripts/models/run_ppocrv6_word_boxes_batch.sh \
  "$BCTC_E0014_MBB_ROOT/manifest.json" \
  output/calibration/e0014-mbb-selected-200dpi-replay-role-c \
  10-15

bash scripts/models/run_ppocrv6_word_boxes_batch.sh \
  "$BCTC_E0014_VCB_ROOT/manifest.json" \
  output/calibration/e0014-vcb-selected-200dpi-replay-role-c \
  8-14
```

## Run Role B sequentially on the GPU

Do not run concurrent Role B model copies. Every page gets an independent
benchmark record and output directory.

```bash
for page in 0010 0011 0012 0013 0014 0015; do
  .venv/bin/python scripts/diagnostics/run_gpu_benchmark.py \
    --output "$BCTC_E0014_MBB_ROOT/experiments/paddleocr-vl-page-${page}-metrics.json" \
    --interval-ms 250 \
    -- env BCTC_MODEL_CACHE_DIR="$BCTC_E0014_MODEL_CACHE" \
    bash scripts/models/run_paddleocr_vl.sh \
    "$BCTC_E0014_MBB_ROOT/renders/page-${page}.png" \
    "$BCTC_E0014_MBB_ROOT/ocr/paddleocr-vl-page-${page}"
done

for page in 0008 0009 0010 0011 0012 0013 0014; do
  .venv/bin/python scripts/diagnostics/run_gpu_benchmark.py \
    --output "$BCTC_E0014_VCB_ROOT/experiments/paddleocr-vl-page-${page}-metrics.json" \
    --interval-ms 250 \
    -- env BCTC_MODEL_CACHE_DIR="$BCTC_E0014_MODEL_CACHE" \
    bash scripts/models/run_paddleocr_vl.sh \
    "$BCTC_E0014_VCB_ROOT/renders/page-${page}.png" \
    "$BCTC_E0014_VCB_ROOT/ocr/paddleocr-vl-page-${page}"
done
```

## Seal Role B, then Role C

Role C sealing deliberately depends on the corresponding Role B seal so both
readers must point to the exact same render set.

```bash
.venv/bin/python scripts/experiments/seal_role_b_ocr_run.py \
  --run-root "$BCTC_E0014_MBB_ROOT" \
  --pages 10-15 \
  --model-cache-root "$BCTC_E0014_MODEL_CACHE"

.venv/bin/python scripts/experiments/seal_role_b_ocr_run.py \
  --run-root "$BCTC_E0014_VCB_ROOT" \
  --pages 8-14 \
  --model-cache-root "$BCTC_E0014_MODEL_CACHE"

.venv/bin/python scripts/experiments/seal_independent_geometry_run.py \
  --run-root output/calibration/e0014-mbb-selected-200dpi-replay-role-c \
  --pages 10-15 \
  --role-b-seal "$BCTC_E0014_MBB_ROOT/role_b_ocr_seal.json" \
  --model-cache-root "$BCTC_E0014_MODEL_CACHE"

.venv/bin/python scripts/experiments/seal_independent_geometry_run.py \
  --run-root output/calibration/e0014-vcb-selected-200dpi-replay-role-c \
  --pages 8-14 \
  --role-b-seal "$BCTC_E0014_VCB_ROOT/role_b_ocr_seal.json" \
  --model-cache-root "$BCTC_E0014_MODEL_CACHE"
```

## Expected completion contract

| Source | Pages | Role B | Role C lines/words | Role C loads |
|---|---:|---:|---:|---:|
| MBB | 6 | sealed, 3,241 MiB peak | 656 / 5,365 | 1 |
| VCB | 7 | sealed, 3,241 MiB peak | 779 / 5,411 | 1 |

Wall times and complete seal hashes include observational timestamps and may
differ on a rebuilt host. Compare the source/render/config/model/code identities,
page sets, completion states, and safety flags. A changed model output is a new
artifact and must not replace the original E-0014 seal.

The next stage must parse every Role B table block, reconstruct rows and axes
from Role C, exclude pages 12/10 from CDKT, retain cross-page continuations, and
report disagreements. It must not use history, schema IDs, arithmetic repair,
or Q-BOOT-001 branch assignment.
