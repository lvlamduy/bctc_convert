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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the source-first registered-bank inventory and Wave 1 selection"
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--artifact", choices=("inventory", "source-profile"), default="inventory")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    root = args.project_root.resolve()
    policy = root / POLICY_RELATIVE_PATH
    if args.verify_only:
        payload = (
            build_bank_corpus_inventory(root, policy)
            if args.artifact == "inventory"
            else build_wave_one_source_profile(root, policy)
        )
        accounting = payload["accounting"]
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "registered_bank_count": accounting.get("registered_bank_count"),
                    "registered_pdf_path_count": accounting.get("registered_pdf_path_count"),
                    "source_profiled_document_count": accounting.get(
                        "source_profiled_document_count"
                    ),
                    "wave_1_selected_document_count": (
                        payload.get("wave_1", {}).get("selected_document_count")
                    ),
                },
                sort_keys=True,
            )
        )
        return 0
    if args.artifact == "inventory":
        path, digest, size = publish_bank_corpus_inventory(
            root,
            policy_path=policy,
            output_path=root / OUTPUT_RELATIVE_PATH,
        )
        label = "BANK_CORPUS_INVENTORY"
    else:
        path, digest, size = publish_wave_one_source_profile(
            root,
            policy_path=policy,
            output_path=root / SOURCE_PROFILE_OUTPUT_RELATIVE_PATH,
        )
        label = "BANK_CORPUS_SOURCE_PROFILE"
    print(f"{label}={path.relative_to(root)}")
    print(f"{label}_SHA256={digest}")
    print(f"{label}_BYTES={size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
