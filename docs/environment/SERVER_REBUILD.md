# Server rebuild procedure

1. Clone the repository and check out the required tagged/committed version.
2. Restore source PDFs and large local artifacts from the immutable S3 snapshot
   recorded in `PROGRESS_REPORT.md`/the backup run record. Use `bctc-ai
   s3-hydrate` for exact logical paths or asset classes; it must reject local
   conflicts and verify the manifest, S3 checksum, size, and SHA-256. If S3 is
   unavailable, copy them separately and verify against `data/registered/*.json*`.
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
13. Re-register or audit hydrated source PDFs after transfer. Dataset roles are
    append-only; never silently reuse development files as holdout. A Git-only or
    offloaded workspace may use `review-audit --allow-missing-sources` only for
    control-plane checks and may not claim source bytes were locally verified.
14. Run a final `bctc-ai audit`; it must remain fail-closed if Mongo, historical index, GPU, schema, source hashes, or backup evidence differ.
15. Run golden fixtures, verify immutable E-0006, replay pinned E-0007, verify E-0008, and replay E-0009/E-0010 from `docs/experiments/E-0010-REPLAY.md` before any production batch. Generated output is never a substitute for the registered source hashes.
16. Verify both geometry configurations. `config/tables/geometry.yaml` is historical v1 and must retain its registered hash; current calibration uses `config/tables/geometry-v2.yaml`. Never edit v1 to make a newer fixture pass.
17. Rebuild/verify the two PP-OCRv6 models, transfer the three exact external evidence directories, and replay E-0011 with `docs/experiments/E-0011-REPLAY.md`. Verify `config/tables/word-box-reconstruction.yaml`, all three seals, and the tracked result hash. A fresh OCR run must use a new experiment identity.
18. Replay the clean E-0012 batch-equivalence mechanism with `docs/experiments/E-0012-REPLAY.md`. Before any later multi-page PP-OCRv6 run or resume, follow `BATCH_OCR_RUNBOOK.md`. Resume must use the same inference commit, manifest, page set, role, thread count, config, runtime, and model hashes; otherwise start a new output/experiment identity.
19. Before row extraction, replay the statement-boundary gate using `STATEMENT_LOCATION_RUNBOOK.md` and the exact E-0013 contract in `../experiments/E-0013-REPLAY.md`. It must verify the complete preprocess/batch/render/OCR identity chain, find a contiguous CDKT→KQKD→LCTT→TM block, and keep off-balance pages mapping-ineligible. Preserve E-0013's historical Q-BOOT-001 fail-closed flag, then verify current `config/mapping/lctt-v2.yaml`: template-order block 4155→4168 is INDIRECT and 4104→4116 is DIRECT. The final audit's `statement_location` status must pass, with every transferred local artifact reported as verified.
20. Rebuild or transfer the E-0014 selected-page evidence using `../experiments/E-0014-REPLAY.md`. Require 200-DPI source/render identity, exact MBB/VCB page contracts, a sealed Role B and Role C output for each document, and all no-map/no-promote flags. Wall times may differ, but changed OCR bytes or model/code/config identities require a new experiment; never edit an old seal. Keep the off-balance pages as exclusion evidence, not CDKT mapping input.
21. Before structural fusion, verify `../STRUCTURAL_READER_FUSION_STRATEGY.md`, `../../config/tables/vlm-table-parser-v2.yaml`, and `../../config/tables/word-box-reconstruction-v2.yaml`. Run the focused v2 parser/geometry/fusion tests and then the full suite. Any unresolved table block, unassigned numeric evidence, invalid cell, missing reader row, or off-balance eligibility must remain explicit; do not edit an E-0014 OCR artifact to make the new parser pass.
22. Replay formal E-0015 with `../experiments/E-0015-REPLAY.md`. Require clean commit/config/algorithm hashes, the exact E-0014 artifact and four local reader seals, 14 retained table blocks including the one expected unresolved VCB page-9 block, zero off-balance eligibility, and five continuation records with automatic cross-page row merge disabled. Conditional agreement is not a production-accuracy gate.
23. Verify `../TARGETED_REREAD_STRATEGY.md` and follow `../experiments/E-0016-REPLAY.md`. The input builder must re-hash E-0015, both source PDFs, Role C seals/results/renders, and the targeted policy before it rerenders eight regions directly from the PDFs. Require two skipped off-balance pages, 2/5/1 full-table/row-band/numeric regions, no unsupported escalation, original preservation, and recorded inverse geometry. Transfer and verify the formal 52-file reader-output set, or run all 15 requested original-crop reads as a new experiment. The evidence sealer must preserve the unresolved/no-table/invalid-cell outcomes and leave variant/value/schema/ReportNormId/confidence selection disabled. E-0016 adds no package or model.
24. Verify the human-reviewed calibration registry with `.venv/bin/bctc-ai review-audit`. It must report 3 documents and 30 decisions, validate the current CDKT template hash, confirm all three immutable `CALIBRATION` roles, and re-hash each locally restored PDF. In a Git-only control-plane check, `--allow-missing-sources` may validate tracked identities without claiming the absent PDFs were verified.
25. Verify `config/tables/period-propagation-v1.yaml` and `config/mapping/structural-ranking-v2.yaml`. Run the focused period/value/mapping/human-review tests before a full suite. Do not change template rows into numeric ReportNormId order; source-workbook `display_order` is authoritative.
26. For the optional TATR calibration reader, read `../MODEL_READER_DECISION.md`, download and verify the exact checkpoint with `scripts/bootstrap/download_tatr_model.py`, and run only against source/hash-bound tight table crops. Its output is geometry proposal evidence and must not alter value, period, scope, schema, confidence, or template order. DeepSeek-OCR-2, IBM TableFormer, and ClusterTabNet are not part of the base rebuild until separate runtime/model manifests and clean experiments approve them.
27. Verify the S3 run record, manifest SHA-256, catalog HEAD count, sampled/full
    restore level, and local-offload journal. Bucket versioning must be enabled
    before the backup is reported as production PASS; immutable object names on
    an unversioned bucket are useful disaster recovery but do not satisfy that
    stricter gate.

Recovery is accepted only when file hashes, schema order/count, test suite, local Mongo reference audit, and generated-workbook integrity all pass. A copied directory without these checks is not a valid rebuild.

GPU-specific commands, disk budgets, precision settings, cache variables, failure history, and rollback are in `GPU_RUNTIME_RUNBOOK.md`; multi-page checkpoint/recovery is in `BATCH_OCR_RUNBOOK.md`. Historical-reference source selection, rebuild, constraints, and query rules are in `HISTORICAL_REFERENCE_RUNBOOK.md`. Model weights, virtual environments, Mongo data, and the local DuckDB file are reconstructed rather than committed to Git.
