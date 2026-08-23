from __future__ import annotations

import copy
import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/loan_industry_numeric_conflict_evidence_v1.py"
_SPEC = importlib.util.spec_from_file_location("loan_industry_numeric_conflict_test", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
conflict_v1 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = conflict_v1
_SPEC.loader.exec_module(conflict_v1)


def _challenge(crop_ref: dict[str, object]) -> dict[str, object]:
    prompt = "Chuyển bảng thành JSON."
    material: dict[str, object] = {
        "authority": {
            "accounting_authority": False,
            "canonicalization_authority": False,
            "export_authority": False,
            "geometry_authority": False,
            "mapping_authority": False,
            "numeric_authority": False,
            "raw_api_response_self_authenticating": False,
            "schema_authority": False,
            "tracked_response_digest_and_extracted_surface_only": True,
        },
        "claim_boundary": "bounded",
        "decision": {
            "accounting_equation_is_final_corroboration_and_veto": True,
            "gemma4_may_act_as_sole_numeric_reader": False,
            "gemma4_used_only_after_ppocrv6_vietocr_conflict": True,
            "independent_pixel_vietocr_and_gemma4_agree_exactly": True,
            "ppocrv6_observation_overwritten": False,
        },
        "format_version": conflict_v1.CHALLENGER_FORMAT_VERSION,
        "observation": {
            "accounting_effect": {},
            "crop_ref": crop_ref,
            "extracted_numeric_surface": "10",
            "extraction_json_path": ["Khác", "Số cuối kỳ"],
            "format_version": "HOSTED_GEMMA4_FULL_PAGE_NUMERIC_CHALLENGER_OBSERVATION_V1",
            "full_page_render_ref": {},
            "independent_pixel_transcription": "10",
            "inference": {},
            "model": "gemma-4-26b-a4b-it",
            "ppocrv6_original_score": 0.9,
            "ppocrv6_original_surface": "8",
            "ppocrv6_repeated_scale_surfaces": ["8", "8"],
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "response_ref": {},
            "sample_id": "sample-1",
            "state": "COMPLETED_STATELESS_FULL_PAGE_JSON_CHALLENGE",
            "vietocr_transformer_surface": "10",
        },
        "prompt": {"sha256": hashlib.sha256(prompt.encode()).hexdigest(), "text": prompt},
        "state": "COMPLETE",
    }
    return {
        **material,
        "evaluation_id": "industrygemma4v1:evaluation:"
        + conflict_v1.canonical_json_sha256_v1(material),
    }


def _base() -> dict[str, object]:
    material: dict[str, object] = {
        "accounting_checks": [
            {
                "lane_index": 0,
                "missing_cell_count": 0,
                "observed_additive_sum": 8,
                "residual": -2,
                "rounding_tolerance_units": 1,
                "status": "UNRESOLVED_PP_NUMERIC_EQUATION",
                "target_total": 10,
            }
        ],
        "authority": copy.deepcopy(conflict_v1.numeric_v1._AUTHORITY),
        "claim_boundary": conflict_v1.numeric_v1.CLAIM_BOUNDARY,
        "family_id": "LOAN_INDUSTRY_CLASSIFICATION",
        "format_version": conflict_v1.numeric_v1.FORMAT_VERSION,
        "graph_result_id": "livgv1:result:" + "1" * 64,
        "intermediate_subtotals": [],
        "lane_types": ["MONEY"],
        "page_sequence": 1,
        "rows": [
            {
                "cells": [
                    {
                        "lane_index": 0,
                        "lane_type": "MONEY",
                        "parsed_value": 8,
                        "ppocrv6_surface": "8",
                        "semantic_surface": "10",
                        "source_line_index": 0,
                        "status": "PP_OCRV6_NUMERIC_PROPOSAL",
                    }
                ],
                "label": {"surface": "Khác"},
                "role": "OTHER_INDUSTRIES",
            }
        ],
        "status": "UNRESOLVED_PP_NUMERIC_RECONCILIATION",
        "total": [
            {
                "lane_index": 0,
                "lane_type": "MONEY",
                "parsed_value": 10,
                "ppocrv6_surface": "10",
                "semantic_surface": "10",
                "source_line_index": 1,
                "status": "PP_OCRV6_NUMERIC_PROPOSAL",
            }
        ],
        "total_candidate_count": 1,
        "total_selection": "UNRESOLVED_NO_ACCOUNTING_CLOSED_TOTAL_CANDIDATE",
        "unmodelled_additive_rows": [],
    }
    return {
        **material,
        "result_id": "linrrv1:result:" + conflict_v1.canonical_json_sha256_v1(material),
    }


def _inputs(tmp_path: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    crop = tmp_path / "crops/cell.png"
    crop.parent.mkdir()
    crop.write_bytes(b"pixels")
    ref = {
        "path": "crops/cell.png",
        "sha256": hashlib.sha256(b"pixels").hexdigest(),
        "size_bytes": 6,
    }
    pages = [
        {
            "lines": [
                {
                    "crop_ref": ref,
                    "line_ordinal": 0,
                    "numeric_recognition": {"raw_prediction": "8", "reader_score": 0.9},
                    "sample_id": "sample-1",
                    "vietocr_text": "10",
                }
            ],
            "page_sequence": 1,
        }
    ]
    return pages, _challenge(ref)


def test_three_reader_consensus_and_unique_equation_resolve_one_existing_crop(
    tmp_path: Path,
) -> None:
    pages, challenge = _inputs(tmp_path)
    result = conflict_v1.build_loan_industry_numeric_conflict_evidence_v1(
        _base(), pages, challenge, tmp_path
    )
    assert result["status"] == "NUMERIC_EXACT_WITH_PIXEL_VIETOCR_GEMMA4_CONSENSUS_RESCUE"
    assert result["rows"][0]["cells"][0]["parsed_value"] == 10
    assert result["conflict_resolution"]["previous_cell"]["parsed_value"] == 8
    assert result["accounting_checks"][0]["status"] == "EXACT_PP_NUMERIC_EQUATION"


def test_gemma_cannot_override_without_pixel_and_vietocr_agreement(tmp_path: Path) -> None:
    pages, challenge = _inputs(tmp_path)
    challenge["observation"]["independent_pixel_transcription"] = "9"
    material = copy.deepcopy(challenge)
    material.pop("evaluation_id")
    challenge["evaluation_id"] = (
        "industrygemma4v1:evaluation:" + conflict_v1.canonical_json_sha256_v1(material)
    )
    with pytest.raises(conflict_v1.LoanIndustryNumericConflictEvidenceV1Error):
        conflict_v1.build_loan_industry_numeric_conflict_evidence_v1(
            _base(), pages, challenge, tmp_path
        )


def test_public_replay_rejects_coordinated_resolved_digit_mutation(tmp_path: Path) -> None:
    pages, challenge = _inputs(tmp_path)
    result = conflict_v1.build_loan_industry_numeric_conflict_evidence_v1(
        _base(), pages, challenge, tmp_path
    )
    forged = copy.deepcopy(result)
    forged["rows"][0]["cells"][0]["parsed_value"] = 11
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "lincerv1:result:" + conflict_v1.canonical_json_sha256_v1(material)
    with pytest.raises(conflict_v1.LoanIndustryNumericConflictEvidenceV1Error):
        conflict_v1.validate_loan_industry_numeric_conflict_evidence_replay_v1(
            forged, _base(), pages, challenge, tmp_path
        )
