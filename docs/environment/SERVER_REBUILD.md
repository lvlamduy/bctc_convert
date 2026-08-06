# Server rebuild procedure

1. Clone the repository and check out the required tagged/committed version.
2. Copy source PDFs and large local artifacts separately; verify them against `data/registered/*.json*` hashes.
3. Create the Python environment exactly from `uv.lock` using the commands in `SOFTWARE_INVENTORY.md`.
4. Run `.venv/bin/ruff check src tests scripts` and `.venv/bin/pytest` before processing data.
5. Install the local MongoDB runtime with `scripts/bootstrap/install_mongodb_runtime.sh`.
6. Verify the uploaded dump SHA-256 against `data/registered/mongodb_dump_registry.json`, then start and selectively restore the financial reference namespaces.
7. Restore only `data_chart` with `scripts/mongodb/restore_financial_reference.sh financial_20_02_2022.gz bank-weak-reference`; never restore user/chat namespaces.
8. Set `BCTC_HISTORY_MONGO_URI` to the loopback/read-only URI and build `data/local/historical_weak_reference.duckdb`. Verify its registry and safety constraints using `bctc-ai audit`.
9. Build the isolated document-model environment only from the pinned model-runtime manifest. Run both the real CUDA kernel smoke and Paddle CPU kernel smoke before downloading model weights.
10. Install the two Ubuntu GPU image libraries with `scripts/bootstrap/install_gpu_system_deps.sh`; compare the resulting package set with `config/system/ubuntu-22.04-gpu-apt-observed.tsv`.
11. Set `BCTC_GPU_UV_CACHE_DIR` to a filesystem with at least 8 GiB free and run `scripts/bootstrap/create_gpu_runtime.sh`. It must verify the pinned Paddle wheel before installation; its freeze diff, dependency check, import check, `sm_120` check, CUDA kernel, and Paddle CPU kernel must all pass.
12. Choose a model cache with at least 3 GiB free. Download all four exact revisions using `scripts/bootstrap/download_paddleocr_vl_models.py`, then run it again with `--verify-only`.
13. Re-register source PDFs after transfer. Dataset roles are append-only; never silently reuse development files as holdout.
14. Run a final `bctc-ai audit`; it must remain fail-closed if Mongo, historical index, GPU, schema, source hashes, or backup evidence differ.
15. Run golden fixtures, verify immutable E-0006, replay pinned E-0007, verify E-0008, and replay E-0009/E-0010 from `docs/experiments/E-0010-REPLAY.md` before any production batch. Generated output is never a substitute for the registered source hashes.
16. Verify both geometry configurations. `config/tables/geometry.yaml` is historical v1 and must retain its registered hash; current calibration uses `config/tables/geometry-v2.yaml`. Never edit v1 to make a newer fixture pass.
17. Rebuild/verify the two PP-OCRv6 models, transfer the three exact external evidence directories, and replay E-0011 with `docs/experiments/E-0011-REPLAY.md`. Verify `config/tables/word-box-reconstruction.yaml`, all three seals, and the tracked result hash. A fresh OCR run must use a new experiment identity.
18. Replay the clean E-0012 batch-equivalence mechanism with `docs/experiments/E-0012-REPLAY.md`. Before any later multi-page PP-OCRv6 run or resume, follow `BATCH_OCR_RUNBOOK.md`. Resume must use the same inference commit, manifest, page set, role, thread count, config, runtime, and model hashes; otherwise start a new output/experiment identity.
19. Before row extraction, replay the statement-boundary gate using `STATEMENT_LOCATION_RUNBOOK.md` and the exact E-0013 contract in `../experiments/E-0013-REPLAY.md`. It must verify the complete preprocess/batch/render/OCR identity chain, find a contiguous CDKT→KQKD→LCTT→TM block, keep off-balance pages mapping-ineligible, and retain Q-BOOT-001 as fail-closed.

Recovery is accepted only when file hashes, schema order/count, test suite, local Mongo reference audit, and generated-workbook integrity all pass. A copied directory without these checks is not a valid rebuild.

GPU-specific commands, disk budgets, precision settings, cache variables, failure history, and rollback are in `GPU_RUNTIME_RUNBOOK.md`; multi-page checkpoint/recovery is in `BATCH_OCR_RUNBOOK.md`. Historical-reference source selection, rebuild, constraints, and query rules are in `HISTORICAL_REFERENCE_RUNBOOK.md`. Model weights, virtual environments, Mongo data, and the local DuckDB file are reconstructed rather than committed to Git.
