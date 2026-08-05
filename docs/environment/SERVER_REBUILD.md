# Server rebuild procedure

1. Clone the repository and check out the required tagged/committed version.
2. Copy source PDFs and large local artifacts separately; verify them against `data/registered/*.json*` hashes.
3. Create the Python environment exactly from `uv.lock` using the commands in `SOFTWARE_INVENTORY.md`.
4. Run `.venv/bin/ruff check src tests scripts` and `.venv/bin/pytest` before processing data.
5. Install the local MongoDB runtime with `scripts/bootstrap/install_mongodb_runtime.sh`.
6. Verify the uploaded dump SHA-256 against `data/registered/mongodb_dump_registry.json`, then start and selectively restore the financial reference namespaces.
7. Run `bctc-ai audit`; it must remain fail-closed if Mongo, GPU, schema, source hashes, or backup evidence differ.
8. Build the isolated GPU environment only from the pinned model-runtime manifest. Run a real CUDA kernel smoke test before downloading model weights.
9. Re-register source PDFs after transfer. Dataset roles are append-only; never silently reuse development files as holdout.
10. Run golden fixtures and a frozen end-to-end sample before any production batch.

Recovery is accepted only when file hashes, schema order/count, test suite, local Mongo reference audit, and generated-workbook integrity all pass. A copied directory without these checks is not a valid rebuild.
