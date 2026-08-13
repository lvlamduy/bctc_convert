#!/usr/bin/env python3
"""Capture the replay-authenticated SHB maturity numeric verification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.evaluation.semantic_graph_numeric_proposal_receipt_v1 import (
    ArtifactPinV1,
    authenticate_semantic_graph_numeric_proposals_v1,
    verify_semantic_graph_numeric_proposals_v1,
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


def _json(path: Path | str) -> dict[str, Any]:
    value = json.loads((PROJECT_ROOT / path).read_bytes())
    if type(value) is not dict:
        raise ValueError(f"expected one JSON object: {path}")
    return value


def _reconstruct_shb_maturity_graph_v1() -> tuple[
    Any, dict[str, Any], dict[str, Any], dict[str, Any]
]:
    """Rebuild the exact upstream receipt, projection, binding, and graph."""

    transformer_receipt = validate_vietocr_semantic_receipt_v2(
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
    binding = bind_vietocr_semantic_page_v2(projection, transformer_receipt)
    graph = build_semantic_local_accounting_graph_v2(
        projection,
        binding,
        transformer_receipt,
        LOAN_MATURITY_BUCKETS_SPEC_V1,
        SPECS,
    )
    return transformer_receipt, projection, binding, graph


def _output_path(path: Path) -> Path:
    root = PROJECT_ROOT.resolve(strict=True)
    candidate = path if path.is_absolute() else root / path
    resolved = candidate.resolve(strict=False)
    if resolved == root or not resolved.is_relative_to(root):
        raise ValueError("numeric verification output must remain inside the project root")
    return resolved


def _model_cache_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def capture_shb_maturity_numeric_verification_v1(
    *,
    registry_path: Path,
    registry_sha256: str,
    registry_size_bytes: int,
    predictions_path: Path,
    predictions_sha256: str,
    predictions_size_bytes: int,
    run_manifest_path: Path,
    run_manifest_sha256: str,
    run_manifest_size_bytes: int,
    selection_authority_path: Path,
    selection_authority_sha256: str,
    selection_authority_size_bytes: int,
    expected_run_commit: str,
    expected_selection_authority_commit: str,
    model_cache: Path,
    output: Path,
) -> dict[str, Any]:
    """Authenticate frozen proposal bytes and persist the module-owned result."""

    output_path = _output_path(output)
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite numeric verification: {output_path}")

    registry = ArtifactPinV1(registry_path, registry_sha256, registry_size_bytes)
    predictions = ArtifactPinV1(predictions_path, predictions_sha256, predictions_size_bytes)
    run_manifest = ArtifactPinV1(
        run_manifest_path,
        run_manifest_sha256,
        run_manifest_size_bytes,
    )
    selection_authority = ArtifactPinV1(
        selection_authority_path,
        selection_authority_sha256,
        selection_authority_size_bytes,
    )
    transformer_receipt, projection, binding, graph = _reconstruct_shb_maturity_graph_v1()
    proposal_receipt = authenticate_semantic_graph_numeric_proposals_v1(
        PROJECT_ROOT,
        registry=registry,
        predictions=predictions,
        run_manifest=run_manifest,
        selection_authority=selection_authority,
        expected_run_commit=expected_run_commit,
        expected_selection_authority_commit=expected_selection_authority_commit,
        model_cache=_model_cache_path(model_cache),
        semantic_graph_v2=graph,
        source_projection_v2=projection,
        semantic_page_binding_v2=binding,
        authenticated_transformer_receipt_v2=transformer_receipt,
        family_spec=LOAN_MATURITY_BUCKETS_SPEC_V1,
        family_specs_for_collision_scope=SPECS,
    )
    verified = verify_semantic_graph_numeric_proposals_v1(
        proposal_receipt,
        PROJECT_ROOT,
        semantic_graph_v2=graph,
        source_projection_v2=projection,
        semantic_page_binding_v2=binding,
        authenticated_transformer_receipt_v2=transformer_receipt,
        family_spec=LOAN_MATURITY_BUCKETS_SPEC_V1,
        family_specs_for_collision_scope=SPECS,
    )
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite numeric verification: {output_path}")
    atomic_write_json(output_path, verified)
    return verified


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--registry-sha256", required=True)
    parser.add_argument("--registry-size-bytes", type=int, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--predictions-sha256", required=True)
    parser.add_argument("--predictions-size-bytes", type=int, required=True)
    parser.add_argument("--run-manifest", type=Path, required=True)
    parser.add_argument("--run-manifest-sha256", required=True)
    parser.add_argument("--run-manifest-size-bytes", type=int, required=True)
    parser.add_argument("--selection-authority", type=Path, required=True)
    parser.add_argument("--selection-authority-sha256", required=True)
    parser.add_argument("--selection-authority-size-bytes", type=int, required=True)
    parser.add_argument("--expected-run-commit", required=True)
    parser.add_argument("--expected-selection-authority-commit", required=True)
    parser.add_argument("--model-cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    verified = capture_shb_maturity_numeric_verification_v1(
        registry_path=args.registry,
        registry_sha256=args.registry_sha256,
        registry_size_bytes=args.registry_size_bytes,
        predictions_path=args.predictions,
        predictions_sha256=args.predictions_sha256,
        predictions_size_bytes=args.predictions_size_bytes,
        run_manifest_path=args.run_manifest,
        run_manifest_sha256=args.run_manifest_sha256,
        run_manifest_size_bytes=args.run_manifest_size_bytes,
        selection_authority_path=args.selection_authority,
        selection_authority_sha256=args.selection_authority_sha256,
        selection_authority_size_bytes=args.selection_authority_size_bytes,
        expected_run_commit=args.expected_run_commit,
        expected_selection_authority_commit=args.expected_selection_authority_commit,
        model_cache=args.model_cache,
        output=args.output,
    )
    print(
        json.dumps(
            {
                "claim_boundary": verified["claim_boundary"],
                "status": verified["status"],
                "verification_id": verified["verification_id"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
