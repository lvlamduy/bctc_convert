from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.corpus.bank_survey import (
    OUTPUT_RELATIVE_PATH,
    POLICY_RELATIVE_PATH,
    SOURCE_PROFILE_OUTPUT_RELATIVE_PATH,
    build_bank_corpus_inventory,
    build_wave_one_source_profile,
    publish_bank_corpus_inventory,
    publish_wave_one_source_profile,
)
from bctc_ai.corpus.wave1_pre_ocr_structure import (
    OUTPUT_RELATIVE_PATH as PRE_OCR_STRUCTURE_OUTPUT_RELATIVE_PATH,
)
from bctc_ai.corpus.wave1_pre_ocr_structure import (
    POLICY_RELATIVE_PATH as PRE_OCR_STRUCTURE_POLICY_RELATIVE_PATH,
)
from bctc_ai.corpus.wave1_pre_ocr_structure import (
    build_wave_one_pre_ocr_structure_features,
    publish_wave_one_pre_ocr_structure_features,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build the source-first registered-bank inventory, source profile, "
            "or pre-OCR structure features"
        )
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--artifact",
        choices=("inventory", "source-profile", "pre-ocr-structure"),
        default="inventory",
    )
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    root = args.project_root.resolve()
    survey_policy = root / POLICY_RELATIVE_PATH
    pre_ocr_policy = root / PRE_OCR_STRUCTURE_POLICY_RELATIVE_PATH
    if args.verify_only:
        if args.artifact == "inventory":
            payload = build_bank_corpus_inventory(root, survey_policy)
        elif args.artifact == "source-profile":
            payload = build_wave_one_source_profile(root, survey_policy)
        else:
            payload = build_wave_one_pre_ocr_structure_features(root, pre_ocr_policy)
        accounting = payload["accounting"]
        summary = {
            "status": payload["status"],
            "registered_bank_count": accounting.get("registered_bank_count"),
            "registered_pdf_path_count": accounting.get("registered_pdf_path_count"),
            "source_profiled_document_count": accounting.get("source_profiled_document_count"),
            "pre_ocr_feature_profiled_document_count": accounting.get(
                "pre_ocr_feature_profiled_document_count"
            ),
            "total_pdf_page_count": accounting.get("total_pdf_page_count"),
            "page_geometry_accounted_count": accounting.get("page_geometry_accounted_count"),
            "wave_1_selected_document_count": payload.get("wave_1", {}).get(
                "selected_document_count"
            ),
        }
        print(
            json.dumps(
                {key: value for key, value in summary.items() if value is not None},
                sort_keys=True,
            )
        )
        return 0
    if args.artifact == "inventory":
        path, digest, size = publish_bank_corpus_inventory(
            root,
            policy_path=survey_policy,
            output_path=root / OUTPUT_RELATIVE_PATH,
        )
        label = "BANK_CORPUS_INVENTORY"
    elif args.artifact == "source-profile":
        path, digest, size = publish_wave_one_source_profile(
            root,
            policy_path=survey_policy,
            output_path=root / SOURCE_PROFILE_OUTPUT_RELATIVE_PATH,
        )
        label = "BANK_CORPUS_SOURCE_PROFILE"
    else:
        path, digest, size = publish_wave_one_pre_ocr_structure_features(
            root,
            policy_path=pre_ocr_policy,
            output_path=root / PRE_OCR_STRUCTURE_OUTPUT_RELATIVE_PATH,
        )
        label = "BANK_CORPUS_WAVE_1_PRE_OCR_STRUCTURE_FEATURES"
    print(f"{label}={path.relative_to(root)}")
    print(f"{label}_SHA256={digest}")
    print(f"{label}_BYTES={size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
