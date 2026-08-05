# Server rebuild procedure

1. Clone the repository and check out the required tagged/committed version.
2. Copy source PDFs and large local artifacts separately; verify them against `data/registered/*.json*` hashes.
3. Create the Python environment exactly from `uv.lock` using the commands in `SOFTWARE_INVENTORY.md`.
4. Run `.venv/bin/ruff check src tests scripts` and `.venv/bin/pytest` before processing data.
5. Install the local MongoDB runtime with `scripts/bootstrap/install_mongodb_runtime.sh`.
6. Verify the uploaded dump SHA-256 against `data/registered/mongodb_dump_registry.json`, then start and selectively restore the financial reference namespaces.
7. Run `bctc-ai audit`; it must remain fail-closed if Mongo, GPU, schema, source hashes, or backup evidence differ.
8. Build the isolated GPU environment only from the pinned model-runtime manifest. Run a real CUDA kernel smoke test before downloading model weights.
9. Install the two Ubuntu GPU image libraries with `scripts/bootstrap/install_gpu_system_deps.sh`; compare the resulting package set with `config/system/ubuntu-22.04-gpu-apt-observed.tsv`.
10. Set `BCTC_GPU_UV_CACHE_DIR` to a filesystem with at least 8 GiB free and run `scripts/bootstrap/create_gpu_runtime.sh`. Its freeze diff, dependency check, import check, `sm_120` check, and real CUDA kernel must all pass.
11. Choose a model cache with at least 3 GiB free. Download the exact revisions using `scripts/bootstrap/download_paddleocr_vl_models.py`, then run it again with `--verify-only`.
12. Re-register source PDFs after transfer. Dataset roles are append-only; never silently reuse development files as holdout.
13. Run golden fixtures, E-0006, a pinned E-0007 replay, and a frozen end-to-end sample before any production batch. Generated output is never a substitute for the registered source hashes.

Recovery is accepted only when file hashes, schema order/count, test suite, local Mongo reference audit, and generated-workbook integrity all pass. A copied directory without these checks is not a valid rebuild.

GPU-specific commands, disk budgets, precision settings, cache variables, failure history, and rollback are in `GPU_RUNTIME_RUNBOOK.md`. Model weights and virtual environments are intentionally reconstructed rather than committed to Git.
