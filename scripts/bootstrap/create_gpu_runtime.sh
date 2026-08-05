#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$project_root"

if [[ -e .gpu-venv ]]; then
  echo ".gpu-venv already exists; refusing to overwrite" >&2
  exit 2
fi

.venv/bin/uv venv --python 3.11 .gpu-venv
.venv/bin/uv pip install \
  --python .gpu-venv/bin/python \
  --index-url https://download.pytorch.org/whl/cu130 \
  "torch==2.12.0"
.gpu-venv/bin/python scripts/diagnostics/gpu_smoke.py
