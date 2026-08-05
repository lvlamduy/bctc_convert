#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$project_root"

if [[ $# -ne 2 ]]; then
  echo "usage: BCTC_MODEL_CACHE_DIR=/path $0 INPUT_IMAGE OUTPUT_DIRECTORY" >&2
  exit 2
fi
: "${BCTC_MODEL_CACHE_DIR:?set BCTC_MODEL_CACHE_DIR to a filesystem with at least 3 GiB free}"

input_image=$1
output_directory=$2
if [[ ! -f "$input_image" ]]; then
  echo "input image does not exist: $input_image" >&2
  exit 3
fi
if [[ -e "$output_directory" ]]; then
  echo "output already exists; refusing to overwrite: $output_directory" >&2
  exit 4
fi

export PADDLE_PDX_CACHE_HOME="$BCTC_MODEL_CACHE_DIR"
export PADDLE_PDX_MODEL_SOURCE=huggingface
export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
export HF_HOME="${BCTC_HF_CACHE_DIR:-$BCTC_MODEL_CACHE_DIR/huggingface}"
export XDG_CACHE_HOME="${BCTC_XDG_CACHE_DIR:-$BCTC_MODEL_CACHE_DIR/xdg}"
export TMPDIR="${BCTC_MODEL_TMP_DIR:-$BCTC_MODEL_CACHE_DIR/tmp}"
mkdir -p "$HF_HOME" "$XDG_CACHE_HOME" "$TMPDIR"

.gpu-venv/bin/paddleocr doc_parser \
  --input "$input_image" \
  --save_path "$output_directory" \
  --pipeline_version v1.6 \
  --paddlex_config config/models/paddleocr-vl-1.6-transformers.yaml \
  --engine transformers \
  --device gpu:0 \
  --use_queues false \
  --use_doc_orientation_classify false \
  --use_doc_unwarping false \
  --max_new_tokens 8192
