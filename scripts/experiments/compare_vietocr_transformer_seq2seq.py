from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bctc_ai.evaluation.vietocr_architecture_comparison import (  # noqa: E402
    capture_frozen_vietocr_architecture_comparison,
)

BENCHMARK_ROOT = Path("output/development/vietocr-multibank-family-ocr-benchmark-v1/frozen-run")
TRUTH_PATH = Path("docs/experiments/vietocr-transformer-seq2seq-postfreeze-truth-v1.json")
TRUTH_SHA256 = "45c129562732cb9ead9b732ef8acf71df8653ca26673f795c33299f887ee22bc"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Authenticate and compare frozen VietOCR Transformer/Seq2Seq outputs"
    )
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument(
        "--json-output",
        type=Path,
        default=BENCHMARK_ROOT / "postjoin/architecture_comparison.json",
    )
    parser.add_argument(
        "--text-output",
        type=Path,
        default=BENCHMARK_ROOT / "postjoin/architecture_comparison_utf8.txt",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = capture_frozen_vietocr_architecture_comparison(
        args.project_root,
        crop_manifest_path=BENCHMARK_ROOT / "frozen/crop_manifest.json",
        reader_request_path=BENCHMARK_ROOT / "frozen/reader_request.json",
        transformer_output_directory=BENCHMARK_ROOT / "outputs/vgg-transformer",
        transformer_result_sha256=(
            "4277307a95738975bb720f3d5cff19b4e432e741a5052002efffcac5343197d1"
        ),
        transformer_run_manifest_sha256=(
            "6e7d3a9038ba2af6c449eff4f5bfe88df6380c02b9d378f49df21b7876ab5db7"
        ),
        seq2seq_output_directory=BENCHMARK_ROOT / "outputs/vgg-seq2seq",
        seq2seq_result_sha256=("5c21ed137774262f770a8b2b28287efb88e952e6e2e640776066cc1e5031170f"),
        seq2seq_run_manifest_sha256=(
            "8c6c32a2845998d28bff47ff637105f2dc5b78dc79b7fc24b1445b4e702f60fa"
        ),
        truth_path=TRUTH_PATH,
        truth_sha256=TRUTH_SHA256,
        json_output_path=args.json_output,
        text_output_path=args.text_output,
    )
    summary = {
        "selected_architecture": payload["comparison"]["selected_architecture"],
        "selection_status": payload["comparison"]["selection_status"],
        "transformer": payload["architectures"]["transformer"]["metrics"],
        "seq2seq": payload["architectures"]["seq2seq"]["metrics"],
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
