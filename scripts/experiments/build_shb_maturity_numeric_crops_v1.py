#!/usr/bin/env python3
"""Build the exact replayed SHB maturity numeric crop denominator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.evaluation.semantic_graph_numeric_cell_crops_v1 import (
    build_semantic_graph_numeric_cell_crop_registry_v1,
)
from bctc_ai.source_structure.evidence_projection_v2 import project_authenticated_page_v2
from bctc_ai.source_structure.local_accounting_graph_v1 import (
    LOAN_MATURITY_BUCKETS_SPEC_V1,
    LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
)
from bctc_ai.source_structure.semantic_local_accounting_graph_v2 import (
    build_semantic_local_accounting_graph_v2,
)
from bctc_ai.source_structure.vietocr_semantic_receipt_v2 import (
    bind_vietocr_semantic_page_v2,
    validate_vietocr_semantic_receipt_v2,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_ROOT = Path("output/development/vietocr-multibank-family-ocr-benchmark-v1/frozen-run")
MANIFEST = RUN_ROOT / "frozen/crop_manifest.json"
REQUEST = RUN_ROOT / "frozen/reader_request.json"
RESULT = RUN_ROOT / "outputs/vgg-transformer/ocr_result.json"
RUN = RUN_ROOT / "outputs/vgg-transformer/run_manifest.json"
TIER1 = Path("tests/fixtures/source_structure/local_accounting_graph_v1_tier1_cases.json")
RESULT_SHA256 = "4277307a95738975bb720f3d5cff19b4e432e741a5052002efffcac5343197d1"
RUN_SHA256 = "6e7d3a9038ba2af6c449eff4f5bfe88df6380c02b9d378f49df21b7876ab5db7"
SPECS = (
    LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    LOAN_MATURITY_BUCKETS_SPEC_V1,
)


def _json(path: Path | str) -> dict:
    return json.loads((PROJECT_ROOT / path).read_bytes())


def build(output: Path) -> dict:
    receipt = validate_vietocr_semantic_receipt_v2(
        PROJECT_ROOT,
        MANIFEST,
        REQUEST,
        RESULT,
        RUN,
        expected_ocr_result_sha256=RESULT_SHA256,
        expected_run_manifest_sha256=RUN_SHA256,
    )
    page = _json(MANIFEST)["pages"][0]
    target = None
    for case in _json(TIER1)["cases"]:
        provenance = case["provenance_only_not_inference"]
        for candidate in provenance["page_inputs"]:
            reference = candidate["result_ref"]
            if reference is not None and reference["sha256"] == page["result_ref"]["sha256"]:
                target = provenance, candidate
    if target is None:
        raise RuntimeError("exact SHB page is absent from the frozen Tier-1 provenance")
    provenance, candidate = target
    document = _json(provenance["v3_document_manifest_ref"]["path"])
    record_index = int(candidate["page_record_json_pointer"].removeprefix("/page_records/"))
    projection = project_authenticated_page_v2(
        page_record=document["page_records"][record_index],
        page_result=_json(candidate["result_ref"]["path"]),
    )
    binding = bind_vietocr_semantic_page_v2(projection, receipt)
    graph = build_semantic_local_accounting_graph_v2(
        projection,
        binding,
        receipt,
        LOAN_MATURITY_BUCKETS_SPEC_V1,
        SPECS,
    )
    return build_semantic_graph_numeric_cell_crop_registry_v1(
        PROJECT_ROOT,
        output,
        graph,
        projection,
        binding,
        receipt,
        LOAN_MATURITY_BUCKETS_SPEC_V1,
        SPECS,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    registry = build(args.output_directory)
    print(
        json.dumps(
            {
                "status": "PASS",
                "registry_id": registry["registry_id"],
                "cell_count": registry["metrics"]["cell_count"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
