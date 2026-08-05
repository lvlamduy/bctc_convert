#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$project_root"

if [[ $# -lt 2 || $# -gt 3 ]]; then
  echo "usage: BCTC_MODEL_CACHE_DIR=/path BCTC_DATASET_ROLE=CALIBRATION $0 PREPROCESS_MANIFEST OUTPUT_DIRECTORY [PAGES]" >&2
  exit 2
fi
: "${BCTC_MODEL_CACHE_DIR:?set BCTC_MODEL_CACHE_DIR to the verified model cache}"
: "${BCTC_DATASET_ROLE:?set BCTC_DATASET_ROLE to CALIBRATION, VALIDATION, or UNTOUCHED_HOLDOUT}"

preprocess_manifest=$1
output_directory=$2
pages=${3:-}
arguments=(
  --preprocess-manifest "$preprocess_manifest"
  --output-directory "$output_directory"
  --model-cache "$BCTC_MODEL_CACHE_DIR"
  --config config/models/pp-ocrv6-word-box.yaml
  --dataset-role "$BCTC_DATASET_ROLE"
  --cpu-threads "${BCTC_PADDLE_CPU_THREADS:-8}"
)
if [[ -n "$pages" ]]; then
  arguments+=(--pages "$pages")
fi
if [[ "${BCTC_BATCH_RESUME:-false}" == "true" ]]; then
  arguments+=(--resume)
fi
if [[ "${BCTC_ALLOW_DIRTY_OCR_SMOKE:-false}" == "true" ]]; then
  arguments+=(--allow-dirty)
fi

export PADDLE_PDX_CACHE_HOME="$BCTC_MODEL_CACHE_DIR"
export PADDLE_PDX_MODEL_SOURCE=huggingface
export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
export FLAGS_allocator_strategy=auto_growth
export OMP_NUM_THREADS="${BCTC_PADDLE_CPU_THREADS:-8}"
export PYTHONHASHSEED=0
export XDG_CACHE_HOME="${BCTC_XDG_CACHE_DIR:-$BCTC_MODEL_CACHE_DIR/xdg}"
export TMPDIR="${BCTC_MODEL_TMP_DIR:-$BCTC_MODEL_CACHE_DIR/tmp}"
mkdir -p "$XDG_CACHE_HOME" "$TMPDIR"

exec .gpu-venv/bin/python scripts/models/run_ppocrv6_word_boxes_batch.py "${arguments[@]}"
