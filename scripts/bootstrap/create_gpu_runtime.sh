#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$project_root"

runtime_dir="${BCTC_GPU_RUNTIME_DIR:-.gpu-venv}"
if [[ -n "${BCTC_GPU_UV_CACHE_DIR:-}" ]]; then
  gpu_uv_cache_dir="$BCTC_GPU_UV_CACHE_DIR"
elif [[ -d /dev/shm && -w /dev/shm ]]; then
  gpu_uv_cache_dir=/dev/shm/bctc-ai-uv-cache
else
  gpu_uv_cache_dir=.cache/uv-gpu
fi

require_free_kib() {
  local target=$1
  local required_kib=$2
  local description=$3
  local available_kib
  available_kib=$(df -Pk "$target" | awk 'NR == 2 {print $4}')
  if [[ -z "$available_kib" || "$available_kib" -lt "$required_kib" ]]; then
    echo "$description requires at least $((required_kib / 1024 / 1024)) GiB free at $target" >&2
    exit 3
  fi
}

if [[ -e "$runtime_dir" ]]; then
  echo "$runtime_dir already exists; refusing to overwrite" >&2
  exit 2
fi

if ! ldconfig -p | grep -q 'libGL\.so\.1'; then
  echo "missing libGL.so.1; run scripts/bootstrap/install_gpu_system_deps.sh" >&2
  exit 4
fi
if ! ldconfig -p | grep -q 'libgthread-2\.0\.so\.0'; then
  echo "missing libgthread-2.0.so.0; run scripts/bootstrap/install_gpu_system_deps.sh" >&2
  exit 4
fi

mkdir -p "$gpu_uv_cache_dir"
require_free_kib "$project_root" $((7 * 1024 * 1024)) "GPU runtime"
require_free_kib "$gpu_uv_cache_dir" $((8 * 1024 * 1024)) "GPU wheel cache"

export UV_CACHE_DIR="$gpu_uv_cache_dir"
.venv/bin/uv venv --python 3.11 "$runtime_dir"
.venv/bin/uv pip install \
  --python "$runtime_dir/bin/python" \
  --index-url https://download.pytorch.org/whl/cu130 \
  "torch==2.12.0" \
  "torchvision==0.27.0"
.venv/bin/uv pip install \
  --python "$runtime_dir/bin/python" \
  --constraint config/models/gpu-requirements.freeze.txt \
  "paddleocr[doc-parser]==3.7.0" \
  "python-docx==1.2.0" \
  "transformers==5.14.1"
.venv/bin/uv pip check --python "$runtime_dir/bin/python"

actual_freeze=$(mktemp)
trap 'rm -f "$actual_freeze"' EXIT
.venv/bin/uv pip freeze --python "$runtime_dir/bin/python" >"$actual_freeze"
diff -u config/models/gpu-requirements.freeze.txt "$actual_freeze"

"$runtime_dir/bin/python" scripts/diagnostics/gpu_model_runtime_smoke.py
