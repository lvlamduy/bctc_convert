#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$project_root"

if [[ $# -ne 2 ]]; then
  echo "usage: BCTC_MODEL_CACHE_DIR=/path BCTC_DATASET_ROLE=CALIBRATION $0 PREPROCESSED_IMAGE OUTPUT_DIRECTORY" >&2
  exit 2
fi
: "${BCTC_MODEL_CACHE_DIR:?set BCTC_MODEL_CACHE_DIR to the verified model cache}"
: "${BCTC_DATASET_ROLE:?set BCTC_DATASET_ROLE to CALIBRATION or HOLDOUT}"

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

detector_directory="$BCTC_MODEL_CACHE_DIR/official_models/PP-OCRv6_medium_det"
recognizer_directory="$BCTC_MODEL_CACHE_DIR/official_models/PP-OCRv6_medium_rec"
for model_directory in "$detector_directory" "$recognizer_directory"; do
  if [[ ! -f "$model_directory/inference.pdiparams" ]]; then
    echo "verified PP-OCRv6 model is absent: $model_directory" >&2
    exit 5
  fi
done

export PADDLE_PDX_CACHE_HOME="$BCTC_MODEL_CACHE_DIR"
export PADDLE_PDX_MODEL_SOURCE=huggingface
export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
export FLAGS_allocator_strategy=auto_growth
export OMP_NUM_THREADS="${BCTC_PADDLE_CPU_THREADS:-8}"
export PYTHONHASHSEED=0
export XDG_CACHE_HOME="${BCTC_XDG_CACHE_DIR:-$BCTC_MODEL_CACHE_DIR/xdg}"
export TMPDIR="${BCTC_MODEL_TMP_DIR:-$BCTC_MODEL_CACHE_DIR/tmp}"
mkdir -p "$XDG_CACHE_HOME" "$TMPDIR"

extra_arguments=()
if [[ "${BCTC_ALLOW_DIRTY_OCR_SMOKE:-false}" == "true" ]]; then
  extra_arguments+=(--allow-dirty)
fi

.gpu-venv/bin/python scripts/models/run_ppocrv6_word_boxes.py \
  --input "$input_image" \
  --output-directory "$output_directory" \
  --model-cache "$BCTC_MODEL_CACHE_DIR" \
  --config config/models/pp-ocrv6-word-box.yaml \
  --dataset-role "$BCTC_DATASET_ROLE" \
  --cpu-threads "$OMP_NUM_THREADS" \
  "${extra_arguments[@]}"
