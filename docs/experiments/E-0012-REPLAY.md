# E-0012 PP-OCRv6 batch mechanism replay

## Claim boundary

E-0012 is a clean-commit mechanism regression on TCB page 15, which was already
measured in E-0011. It proves that the batch runner produces the same OCR JSON,
verifies a completed checkpoint without reloading the models, and can be sealed
with both batch/helper hashes. It does not add an accuracy sample or approve
production use.

## Frozen identities

- Inference commit: `3291f9dca0843b5d67858b44019a7b2319f69057`.
- Source SHA-256: `7e3f491783a9895d7716199c3981cddebfc060ef7fa125724f421b7b646faafa`.
- Preprocess manifest SHA-256: `2cff09cf46ed8cba2eb02a76768f39bb756a57f267965c913454b4dc9564b058`.
- Page-15 render SHA-256: `2e18b2b90fb265734471b0f0ad5aabf9fe25375224fd020132e6d78a0c141048`.
- Batch runner SHA-256: `7a716b0aa47dacc0b95454a46371721cc0af613892767f6e58e97035602322cb`.
- Single-page helper SHA-256: `bbbf2f101cec88ae99727393397df463623d47c2b31ef888e565fbe42c05d4b9`.
- Sealer SHA-256: `52e689730029f0317ceea4ea2aecc3e5bb662356c6d0ebc1b6096c496fadb2ad`.
- PP-OCRv6 config SHA-256: `a200fbbc8ba85460c9233875a7a025e8d08d892172d353ed820f69fd258e997b`.
- Runtime manifest SHA-256: `9141e0a4177f66f152bdb9eecbbfdbdd3add566dbabb81b43207a018c1ba18d8`.

## Preconditions

Rebuild and verify `.gpu-venv` plus both models with
`docs/environment/GPU_RUNTIME_RUNBOOK.md`. The worktree must be clean at the
inference commit. The source and E-0009 preprocess/Role B artifacts must be
present and hash-identical. Generated E-0012 output is ignored by Git; use a
new output directory if replaying under any different code or setting.

Before inference:

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q
git status --porcelain
sha256sum \
  output/calibration/e0009-tcb-role-b/7e3f491783a9895d7716/manifest.json \
  output/calibration/e0009-tcb-role-b/7e3f491783a9895d7716/renders/page-0015.png \
  scripts/models/run_ppocrv6_word_boxes_batch.py \
  scripts/models/run_ppocrv6_word_boxes.py \
  config/models/pp-ocrv6-word-box.yaml \
  config/models/gpu-runtime.toml
```

The recorded pre-inference suite was 125 passed and two immutable historical
replays skipped, with Ruff passing.

## Batch inference and no-op resume

```bash
BCTC_MODEL_CACHE_DIR=/dev/shm/bctc-paddlex-e0007 \
BCTC_DATASET_ROLE=CALIBRATION \
BCTC_PADDLE_CPU_THREADS=8 \
  bash scripts/models/run_ppocrv6_word_boxes_batch.sh \
  output/calibration/e0009-tcb-role-b/7e3f491783a9895d7716/manifest.json \
  output/calibration/e0012-batch-mechanism-tcb15 \
  15

BCTC_MODEL_CACHE_DIR=/dev/shm/bctc-paddlex-e0007 \
BCTC_DATASET_ROLE=CALIBRATION \
BCTC_PADDLE_CPU_THREADS=8 \
BCTC_BATCH_RESUME=true \
  bash scripts/models/run_ppocrv6_word_boxes_batch.sh \
  output/calibration/e0009-tcb-role-b/7e3f491783a9895d7716/manifest.json \
  output/calibration/e0012-batch-mechanism-tcb15 \
  15
```

The first command must report one completed page, 50 lines, 380 word tokens,
and one model-load session. The second must report `PASS_ALREADY_COMPLETE` and
leave the model-load session count at one.

Verify byte equivalence with the earlier single-page runner:

```bash
sha256sum \
  output/calibration/e0012-batch-mechanism-tcb15/ppocrv6-page-0015/ocr_result.json \
  output/calibration/e0011-tcb-role-c/7e3f491783a9895d7716/ppocrv6-page-0015/ocr_result.json
```

Both hashes must be
`91779b3e22fadc01eeca7605c71a356e577e56541363ac91ea2750645721c54b`.

## Seal

```bash
.venv/bin/python scripts/experiments/seal_independent_geometry_run.py \
  --run-root output/calibration/e0012-batch-mechanism-tcb15 \
  --pages 15 \
  --role-b-seal output/calibration/e0009-tcb-role-b/7e3f491783a9895d7716/role_b_ocr_seal.json \
  --model-cache-root /dev/shm/bctc-paddlex-e0007
```

The retained 2026-08-05 seal SHA-256 is
`c45dba46013f7ec4cba3bfdf0d531da5caa1d08772e50c5e6ed71d4ff2990da3`;
artifact-set SHA-256 is
`9f379dad2b85a99e89fc081c0d8d19823029483d2d02fdb1b430a9a1dbd2fe04`.
The seal must name the batch runner and single-page helper with their exact
hashes and keep every automatic promotion flag false.

Those two hashes verify a transferred copy of the retained run. A fresh replay
has new timestamps and measured durations, so its batch/page/seal manifest
hashes will differ and must be recorded under a new output identity. The OCR
JSON byte hash and all structural safety gates must remain exact.

The authoritative compact result is
`docs/experiments/E-0012-ppocrv6-batch-mechanism.json`. Timings and manifest
timestamps may change on a new server; OCR output identity and safety gates may
not.
