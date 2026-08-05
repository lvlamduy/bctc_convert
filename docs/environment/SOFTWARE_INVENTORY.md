# Software and runtime inventory

This is the rebuild manifest for the development VPS. Binary archives, model weights, virtual environments, MongoDB data files, source PDFs, and generated output are intentionally excluded from Git; their exact versions, download locations, hashes, and rebuild commands belong here or in machine-readable manifests.

## Host baseline captured 2026-08-05

- Ubuntu 22.04.5 LTS, x86_64; kernel 6.6.0-hiveos.
- AMD Ryzen 9 5950X, 32 logical CPUs; approximately 125.7 GiB RAM.
- NVIDIA GeForce RTX 5070 Ti, 16,303 MiB, compute capability 12.0; driver 595.80 reports CUDA 13.2.
- The preinstalled PyTorch 2.5.1+cu124 does not contain `sm_120` kernels and failed an actual CUDA operation. It is not an approved model runtime.

## Python control-plane environment

- Python 3.11.10.
- uv 0.12.1; dependency resolution is frozen in `uv.lock`.
- Current resolved core versions: PyMuPDF 1.28.0, OpenCV headless 4.14.0.94, OpenPyXL 3.1.5, NumPy 2.4.6, DuckDB 1.5.5, PyMongo 4.17.0, RapidFuzz 3.14.5, PyYAML 6.0.3, Pillow 12.3.0.
- Test tools: Ruff 0.16.1 and pytest 9.1.1.

Rebuild:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install uv==0.12.1
.venv/bin/uv sync --frozen --extra dev
```

## Local MongoDB reference runtime

The uploaded archive reports MongoDB server 7.0.28 and Database Tools 100.14.0. For read-only development restoration, the local server is patched MongoDB 7.0.34 from the same 7.0 major line; Database Tools matches archive tool version 100.14.0.

| Component | Official archive | SHA-256 | Local directory |
|---|---|---|---|
| Database Tools 100.14.0 | `https://fastdl.mongodb.org/tools/db/mongodb-database-tools-ubuntu2204-x86_64-100.14.0.tgz` | `4104998bda784a0cb16fc2e06d9c21645516d72c4fb481c9b103f1e0a8458fc0` | `.tools/mongodb-database-tools-ubuntu2204-x86_64-100.14.0/` |
| MongoDB Community 7.0.34 | `https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-ubuntu2204-7.0.34.tgz` | `ca1ff8067a219b1dccb50a95305c7bba412c8a98787e4e51dbd3d2222817c8b8` | `.tools/mongodb-linux-x86_64-ubuntu2204-7.0.34/` |

Install and verify:

```bash
bash scripts/bootstrap/install_mongodb_runtime.sh
bash scripts/mongodb/start_local_reference.sh
bash scripts/mongodb/restore_financial_reference.sh financial_20_02_2022.gz templates-only
PYTHONPATH=src .venv/bin/python scripts/mongodb/audit_reference_dump.py \
  --archive financial_20_02_2022.gz \
  --mongo-uri mongodb://127.0.0.1:27018
```

The server binds only to `127.0.0.1:27018`; diagnostic data collection is disabled. Restoration is namespace-allowlisted. `user` and `chat_sessions` are out of scope and must not be restored. `.local-mongodb/` and `.tools/` are excluded from Git.

## GPU model runtime

The control plane remains CPU-only and stable. The proposed GPU environment is isolated as `.gpu-venv` and documented in `config/models/gpu-runtime.toml` plus `docs/decisions/0003-blackwell-gpu-runtime.md`. No GPU runtime or model is approved until the `sm_120` smoke test, exact-number fixtures, VRAM, throughput, and hallucination gates pass.

## Maintenance rule

Every software/model change must record version, upstream URL, archive or model revision/hash, license, install command, CUDA/runtime compatibility, measured VRAM, smoke result, and rollback command before the related code commit.
