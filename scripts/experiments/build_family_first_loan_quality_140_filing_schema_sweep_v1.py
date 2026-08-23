#!/usr/bin/env python3
"""Build/replay the fixed 140-filing customer-loan quality schema sweep."""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import re
import secrets
import stat
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))
sys.path.insert(0, os.fspath(PROJECT_ROOT / "src"))

from bctc_ai.evaluation import family_first_document_evidence_store_v1 as store_v1  # noqa: E402
from bctc_ai.evaluation import (  # noqa: E402
    loan_quality_numeric_row_reconciliation_v1 as numeric_v1,
)
from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (  # noqa: E402
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import (  # noqa: E402
    _authority_snapshot,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from scripts.experiments import loan_quality_variant_graph_v2 as graph_v2  # noqa: E402
from scripts.experiments.loan_type_missing_cell_evidence_v1 import (  # noqa: E402
    _matcher_pages,
)

FORMAT_VERSION = "FAMILY_FIRST_LOAN_QUALITY_140_FILING_SCHEMA_SWEEP_V1"
CLAIM_BOUNDARY = (
    "FIXED_140_FILING_AUTHENTICATED_COMPLETE_DOCUMENT_UNIQUE_LOAN_QUALITY_"
    "VARIANT_GRAPH_OBSERVED_PPOCRV6_VIETOCR_EXACT_ACCOUNTING_HOSTED_GEMMA4_"
    "CHALLENGER_BOUNDED_MARGIN_NORMALIZATION_AND_LIVE_TM_SCHEMA_MAPPING_ONLY_"
    "NO_ABSENCE_EXPORT_CANONICALIZATION_OR_PRODUCTION_AUTHORITY"
)
OUTPUT_PATH = Path(
    "output/calibration/family-first-loan-quality-140-filing-schema-sweep-v1/result.json"
)
MARGIN_CONTEXT_PATH = Path("config/schemas/loan-quality-margin-context-140-v2.json")
CHALLENGER_PATH = Path(
    "docs/experiments/E-0167-family-first-loan-quality-hosted-gemma4-numeric-challenger-v1.json"
)
EXCLUDED_FOOTNOTE_CHALLENGER_PATH = Path(
    "docs/experiments/E-0168-family-first-loan-quality-excluded-footnote-hosted-"
    "gemma4-challenger-v1.json"
)

_AUTHORITY = {
    "accounting_equation_can_backsolve_or_invent_a_value": False,
    "accounting_equation_is_corroboration_or_veto_only": True,
    "bank_filename_note_page_or_document_ordinal_used_as_mapping_rule": False,
    "blank_or_missing_cell_imputed_as_zero": False,
    "canonicalization_or_export_authority": False,
    "complete_document_unique_structural_region_required": True,
    "fresh_vietocr_used_for_semantic_labels": True,
    "gemma4_used_as_sole_numeric_authority": False,
    "hosted_gemma4_bound_to_exact_tracked_crops": True,
    "percentage_lanes_preserved_as_corroboration": True,
    "public_exact_live_replay_required": True,
    "schema_mapping_authority_bounded_to_this_family": True,
    "whole_document_family_absence_expected_or_accepted": False,
}
_ROLES = ("STANDARD", "SPECIAL_MENTION", "SUBSTANDARD", "DOUBTFUL", "LOSS")
_ROLE_TO_SCHEMA_ID = {
    "STANDARD": 747,
    "SPECIAL_MENTION": 748,
    "SUBSTANDARD": 749,
    "DOUBTFUL": 750,
    "LOSS": 751,
}
_TARGET_DOCUMENT_COUNT = 140
_TARGET_GRADE_MAPPING_COUNT = 700
_TARGET_MARGIN_MAPPING_COUNT = 27
_TARGET_MAPPING_COUNT = 727
_TARGET_MARGIN_MODE_COUNTS = {
    "STANDALONE_AFTER_FIVE_GRADES": 17,
    "INCLUDED_IN_747_VIA_5746": 6,
    "EXPLICITLY_EXCLUDED_FROM_CORE_VIA_FOOTNOTE": 4,
    "NOT_OBSERVED_DO_NOT_SYNTHESIZE": 113,
}
_TARGET_LAYOUT_COUNTS = {
    "HORIZONTAL_TYPED_PERIOD_LANES": 122,
    "STACKED_PERIOD_BLOCKS_MULTI_ASSET_COLUMNS": 18,
}
_TARGET_LANE_AXIS_COUNTS = {
    "MONEY,MONEY": 136,
    "MONEY,PERCENT,MONEY,PERCENT": 4,
}
_IMPLEMENTATION_PATHS = (
    Path("scripts/experiments/loan_quality_variant_graph_v2.py"),
    Path("src/bctc_ai/evaluation/loan_quality_numeric_row_reconciliation_v1.py"),
    Path("scripts/experiments/build_family_first_loan_quality_140_filing_schema_sweep_v1.py"),
)
_EXPECTED_CHALLENGER_EVALUATION_ID = (
    "qualitygemma4v1:evaluation:6237058c4af26a26a1cd9376533464364c7bc9ba2f9728abdf62e1b1d56d7621"
)
_EXPECTED_CHALLENGER_OBSERVATIONS = {
    "sample-000384932": {
        "accounting_status": "EXACT_ONLY_WITH_PIXEL_VIETOCR_AND_GEMMA4_CANDIDATE",
        "crop_ref": {
            "path": (
                "output/calibration/family-first-semantic-label-cache-v1/documents/"
                "document-0081/page-0021/crops/line-0031.png"
            ),
            "sha256": "fb458d8edcc0b75bc3951a527d87a55f86a3b5fe1ec9df36e103a472e2eddb61",
            "size_bytes": 4639,
        },
        "ppocrv6_original_surface": "1,99,589,394",
        "selected_surface": "1,992,589,394",
    },
    "sample-000655203": {
        "accounting_status": "EXACT_ONLY_WITH_PIXEL_VIETOCR_AND_GEMMA4_CANDIDATE",
        "crop_ref": {
            "path": (
                "output/calibration/family-first-semantic-label-cache-v1/documents/"
                "document-0138/page-0063/crops/line-0089.png"
            ),
            "sha256": "572805237f181bb3bf875eef5ca1f3eae382e96ec4b0d533157fcef22bfa1c89",
            "size_bytes": 845,
        },
        "ppocrv6_original_surface": "6.361.2988",
        "selected_surface": "6.361.298",
    },
}
_EXPECTED_FOOTNOTE_EVALUATION_ID = (
    "qualityfootnotegemma4v1:evaluation:"
    "c335636954de02bca9796ab45ceafb16e90797edc3a166abde9d8af830fef44f"
)
_EXPECTED_FOOTNOTE_OBSERVATIONS = {
    "sample-000028509": {
        "accounting": ([589382442, 571996489], [9423424, 8689759], [598805866, 580686248]),
        "crop_ref": {
            "path": (
                "output/calibration/family-first-semantic-label-cache-v1/documents/"
                "document-0005/page-0017/crops/line-0026.png"
            ),
            "sha256": "b2ad635e9ed807e206ba0e3c92cd5e65ef4a87fe6b219f08614fdb0e219746e1",
            "size_bytes": 58953,
        },
        "ppocrv6_surface": "(Khôngbaom9.423.424đng(31.12.2024:8.689.759đng)ya",
        "surfaces": ["9.423.424", "8.689.759"],
        "vietocr_surface": (
            "(') Không bao gồm 9.423.424 triệu đồng (31.12.2024: 8.689.759 triệu đồng) cho vay giao"
        ),
    },
    "sample-000033191": {
        "accounting": ([622241052, 571996489], [11507631, 8689759], [633748683, 580686248]),
        "crop_ref": {
            "path": (
                "output/calibration/family-first-semantic-label-cache-v1/documents/"
                "document-0007/page-0018/crops/line-0026.png"
            ),
            "sha256": "d0704ed848afbc73eefef79d632a0f842469c716c87c5a8f653dca08354a2624",
            "size_bytes": 59530,
        },
        "ppocrv6_surface": "(Khôngba507đ(31122024:9.75đ)",
        "surfaces": ["11.507.631", "8.689.759"],
        "vietocr_surface": (
            "(?) Không bao gồm 11.507.631 triệu đồng (31.12.2024: 8.689.759 "
            "triệu đồng) cho vay giao"
        ),
    },
    "sample-000038000": {
        "accounting": ([652921773, 571996489], [16266352, 8689759], [669188125, 580686248]),
        "crop_ref": {
            "path": (
                "output/calibration/family-first-semantic-label-cache-v1/documents/"
                "document-0009/page-0018/crops/line-0026.png"
            ),
            "sha256": "14c71e75ae86a3c138a4921193635cd36e97e7a5dbaaeb16b89f902bbc36dfb0",
            "size_bytes": 59880,
        },
        "ppocrv6_surface": "(Khnba16.352đng(31.12.2024:8.69.759đ)a",
        "surfaces": ["16.266.352", "8.689.759"],
        "vietocr_surface": (
            "(') Không bao gồm 16.266.352 triệu đồng (31.12.2024: 8.689,759 "
            "triệu đồng) cho vay giao"
        ),
    },
    "sample-000042889": {
        "accounting": ([669436647, 571996489], [17340705, 8689759], [686777352, 580686248]),
        "crop_ref": {
            "path": (
                "output/calibration/family-first-semantic-label-cache-v1/documents/"
                "document-0011/page-0018/crops/line-0026.png"
            ),
            "sha256": "d9284258e97865843df5f5f78caa4f3c0713eaf70bb7af000e3ada8933f63ea7",
            "size_bytes": 69386,
        },
        "ppocrv6_surface": "h170705d(122029.759)]",
        "surfaces": ["17.340.705", "8.689.759"],
        "vietocr_surface": (
            "(?) Không bao gồm 17.340.705 triệu đồng (31.12.2024: 8.689.759 "
            "triệu đồng) cho vay giao"
        ),
    },
}


class FamilyFirstLoanQuality140FilingSchemaSweepV1Error(ValueError):
    """The live store, evidence, graph, schema, or replay drifted."""


class LoanQualityTrialUnresolvedV1Error(ValueError):
    """One filing lacks observed evidence required for a verified mapping."""


def _error(message: str) -> FamilyFirstLoanQuality140FilingSchemaSweepV1Error:
    return FamilyFirstLoanQuality140FilingSchemaSweepV1Error(message)


def _unresolved(message: str) -> LoanQualityTrialUnresolvedV1Error:
    return LoanQualityTrialUnresolvedV1Error(message)


def _stable_ref(root: Path, relative: Path) -> dict[str, Any]:
    path = root / relative
    try:
        before = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(before.st_mode):
            raise _error(f"input is not one regular nofollow file: {relative}")
        payload = path.read_bytes()
        after = path.lstat()
    except OSError as exc:
        raise _error(f"cannot read stable input: {relative}") from exc

    def identity(item: os.stat_result) -> tuple[int, int, int, int, int]:
        return (item.st_dev, item.st_ino, item.st_mode, item.st_size, item.st_mtime_ns)

    if identity(before) != identity(after) or len(payload) != before.st_size:
        raise _error(f"input changed during read: {relative}")
    return {
        "path": relative.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _strict_object(root: Path, relative: Path, label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    reference = _stable_ref(root, relative)
    try:
        payload = (root / relative).read_bytes()
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON token: {token}")
            ),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise _error(f"{label} is not strict UTF-8 JSON") from exc
    if (
        type(value) is not dict
        or len(payload) != reference["size_bytes"]
        or hashlib.sha256(payload).hexdigest() != reference["sha256"]
        or not same_typed_json_v1(_stable_ref(root, relative), reference)
    ):
        raise _error(f"{label} changed during strict read")
    return value, reference


def _validate_challenger(value: Any, root: Path) -> dict[str, Any]:
    if (
        type(value) is not dict
        or value.get("format_version")
        != "FAMILY_FIRST_LOAN_QUALITY_HOSTED_GEMMA4_NUMERIC_CHALLENGER_EVALUATION_V1"
        or value.get("state") != "COMPLETE"
        or value.get("evaluation_id") != _EXPECTED_CHALLENGER_EVALUATION_ID
        or value.get("model", {}).get("name") != "gemma-4-26b-a4b-it"
        or value.get("model", {}).get("version") != "001"
        or value.get("prompt", {}).get("sha256")
        != "8c6431ce2ae9651a1363ee90ccc4a9570030c6adf119020e249ea022adae5083"
        or value.get("decision")
        != {
            "accounting_equation_is_corroboration_and_veto": True,
            "gemma4_may_act_as_sole_numeric_reader": False,
            "gemma4_used_only_after_ppocrv6_vietocr_conflict": True,
            "independent_pixel_vietocr_and_gemma4_agree_exactly": True,
            "ppocrv6_observation_overwritten": False,
        }
        or value.get("authority")
        != {
            "accounting_authority": False,
            "canonicalization_authority": False,
            "crop_pixel_review_bound": True,
            "geometry_authority": False,
            "mapping_authority": False,
            "numeric_authority": False,
            "raw_api_response_self_authenticating": False,
            "schema_authority": False,
            "tracked_response_digest_and_extracted_surface_only": True,
        }
    ):
        raise _error("E-0167 hosted Gemma 4 challenger identity or authority drifted")
    observations = value.get("observations")
    if type(observations) is not list or len(observations) != 2:
        raise _error("E-0167 must retain exactly two challenger observations")
    seen: set[str] = set()
    for observation in observations:
        if type(observation) is not dict:
            raise _error("E-0167 challenger observation is not one object")
        sample_id = observation.get("sample_id")
        expected = _EXPECTED_CHALLENGER_OBSERVATIONS.get(sample_id)
        if expected is None or sample_id in seen:
            raise _error("E-0167 challenger sample identity drifted or repeated")
        seen.add(sample_id)
        selected = expected["selected_surface"]
        inference = observation.get("inference", {})
        response_ref = observation.get("response_content_ref", {})
        if (
            observation.get("format_version")
            != "HOSTED_GEMMA4_CROP_NUMERIC_CHALLENGER_OBSERVATION_V1"
            or observation.get("state") != "COMPLETED_STATELESS_CROP_JSON_CHALLENGE"
            or not same_typed_json_v1(observation.get("crop_ref"), expected["crop_ref"])
            or observation.get("extracted_numeric_surface") != selected
            or observation.get("independent_pixel_transcription") != selected
            or observation.get("vietocr_transformer_surface") != selected
            or observation.get("ppocrv6_original_surface") != expected["ppocrv6_original_surface"]
            or observation.get("accounting_effect", {}).get("candidate") != selected
            or observation.get("accounting_effect", {}).get("status")
            != expected["accounting_status"]
            or inference.get("fresh_context") is not True
            or inference.get("thinking_level") != "MINIMAL"
            or type(inference.get("temperature")) is not int
            or inference.get("temperature") != 0
            or type(inference.get("max_output_tokens")) is not int
            or inference.get("max_output_tokens") != 128
            or type(response_ref.get("sha256")) is not str
            or not re.fullmatch(r"[0-9a-f]{64}", response_ref["sha256"])
        ):
            raise _error(f"E-0167 challenger observation drifted: {sample_id}")
        actual_crop = _stable_ref(root, Path(expected["crop_ref"]["path"]))
        if not same_typed_json_v1(actual_crop, expected["crop_ref"]):
            raise _error(f"E-0167 exact crop reference drifted: {sample_id}")
    if seen != set(_EXPECTED_CHALLENGER_OBSERVATIONS):
        raise _error("E-0167 challenger observation set drifted")
    identity_material = canonical_clone_v1(value)
    identity = identity_material.pop("evaluation_id")
    if identity != "qualitygemma4v1:evaluation:" + canonical_json_sha256_v1(identity_material):
        raise _error("E-0167 hosted Gemma 4 challenger self-identity drifted")
    return canonical_clone_v1(value)


def _strict_challenger(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    value, reference = _strict_object(root, CHALLENGER_PATH, "E-0167 challenger")
    return _validate_challenger(value, root), reference


def _validate_footnote_challenger(value: Any, root: Path) -> dict[str, Any]:
    expected_authority = {
        "accounting_authority": False,
        "canonicalization_authority": False,
        "crop_pixel_review_bound": True,
        "geometry_authority": False,
        "mapping_authority": False,
        "numeric_authority": False,
        "raw_api_response_self_authenticating": False,
        "schema_authority": False,
        "tracked_response_digest_and_extracted_surface_only": True,
    }
    expected_decision = {
        "accounting_equation_is_corroboration_and_veto": True,
        "fresh_request_count": 8,
        "gemma4_may_act_as_sole_numeric_reader": False,
        "independent_pixel_vietocr_and_gemma4_agree_exactly": True,
        "ppocrv6_observation_overwritten": False,
        "two_independent_credentials_used": True,
        "two_requests_per_crop_agree_exactly": True,
    }
    if (
        type(value) is not dict
        or value.get("format_version")
        != "FAMILY_FIRST_LOAN_QUALITY_EXCLUDED_FOOTNOTE_HOSTED_GEMMA4_CHALLENGER_EVALUATION_V1"
        or value.get("state") != "COMPLETE"
        or value.get("evaluation_id") != _EXPECTED_FOOTNOTE_EVALUATION_ID
        or value.get("model", {}).get("name") != "gemma-4-26b-a4b-it"
        or value.get("model", {}).get("version") != "001"
        or value.get("prompt", {}).get("sha256")
        != "4dffa1721c95c2b45a69f60877d5ff919c4b4db09ae2fd5c7ea7c2acea6cefe4"
        or not same_typed_json_v1(value.get("authority"), expected_authority)
        or not same_typed_json_v1(value.get("decision"), expected_decision)
    ):
        raise _error("E-0168 excluded-footnote challenger identity or authority drifted")
    observations = value.get("observations")
    if type(observations) is not list or len(observations) != 4:
        raise _error("E-0168 must retain exactly four footnote crop observations")
    seen: set[str] = set()
    for observation in observations:
        if type(observation) is not dict:
            raise _error("E-0168 footnote observation is not one object")
        sample_id = observation.get("sample_id")
        expected = _EXPECTED_FOOTNOTE_OBSERVATIONS.get(sample_id)
        if expected is None or sample_id in seen:
            raise _error("E-0168 footnote sample identity drifted or repeated")
        seen.add(sample_id)
        core, margin, parent = expected["accounting"]
        accounting = observation.get("accounting_effect", {})
        requests = observation.get("requests")
        if (
            observation.get("format_version")
            != "HOSTED_GEMMA4_FOOTNOTE_MULTI_NUMBER_CHALLENGER_OBSERVATION_V1"
            or observation.get("state") != "COMPLETED_TWO_FRESH_STATELESS_CROP_JSON_CHALLENGES"
            or not same_typed_json_v1(observation.get("crop_ref"), expected["crop_ref"])
            or observation.get("extracted_monetary_surfaces") != expected["surfaces"]
            or observation.get("independent_pixel_transcriptions") != expected["surfaces"]
            or observation.get("vietocr_transformer_surface") != expected["vietocr_surface"]
            or observation.get("ppocrv6_original_surface") != expected["ppocrv6_surface"]
            or accounting.get("printed_quality_totals") != core
            or accounting.get("observed_excluded_margin_values") != margin
            or accounting.get("independently_observed_customer_loan_parent_totals") != parent
            or accounting.get("status")
            != "EXACT_CORE_PLUS_OBSERVED_EXCLUDED_MARGIN_EQUALS_OBSERVED_PARENT_BOTH_LANES"
            or any(core[lane] + margin[lane] != parent[lane] for lane in range(2))
            or type(requests) is not list
            or len(requests) != 2
        ):
            raise _error(f"E-0168 footnote observation drifted: {sample_id}")
        response_digests = []
        for request_ordinal, request in enumerate(requests, 1):
            if type(request) is not dict:
                raise _error(f"E-0168 stateless request evidence drifted: {sample_id}")
            response = request.get("response_content_ref", {})
            if (
                type(request.get("fresh_request_ordinal")) is not int
                or request.get("fresh_request_ordinal") != request_ordinal
                or type(request.get("credential_slot")) is not int
                or request.get("credential_slot") != request_ordinal
                or request.get("thinking_level") != "MINIMAL"
                or type(request.get("temperature")) is not int
                or request.get("temperature") != 0
                or type(request.get("max_output_tokens")) is not int
                or request.get("max_output_tokens") != 128
                or type(response.get("sha256")) is not str
                or not re.fullmatch(r"[0-9a-f]{64}", response["sha256"])
                or type(response.get("character_count")) is not int
                or response["character_count"] <= 0
            ):
                raise _error(f"E-0168 stateless request evidence drifted: {sample_id}")
            response_digests.append(response["sha256"])
        if len(set(response_digests)) != 1:
            raise _error(f"E-0168 two responses no longer agree exactly: {sample_id}")
        actual_crop = _stable_ref(root, Path(expected["crop_ref"]["path"]))
        if not same_typed_json_v1(actual_crop, expected["crop_ref"]):
            raise _error(f"E-0168 exact crop reference drifted: {sample_id}")
    if seen != set(_EXPECTED_FOOTNOTE_OBSERVATIONS):
        raise _error("E-0168 footnote observation set drifted")
    identity_material = canonical_clone_v1(value)
    identity = identity_material.pop("evaluation_id")
    if identity != "qualityfootnotegemma4v1:evaluation:" + canonical_json_sha256_v1(
        identity_material
    ):
        raise _error("E-0168 excluded-footnote challenger self-identity drifted")
    return canonical_clone_v1(value)


def _strict_footnote_challenger(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    value, reference = _strict_object(
        root, EXCLUDED_FOOTNOTE_CHALLENGER_PATH, "E-0168 footnote challenger"
    )
    return _validate_footnote_challenger(value, root), reference


def _source_line_lookup(
    joined_pages: Sequence[Mapping[str, Any]],
) -> dict[tuple[int, int], dict[str, Any]]:
    lookup: dict[tuple[int, int], dict[str, Any]] = {}
    for page in joined_pages:
        page_sequence = page.get("page_sequence")
        lines = page.get("lines")
        if type(page_sequence) is not int or page_sequence <= 0 or type(lines) is not list:
            raise _error("authenticated joined page axis drifted")
        for line in lines:
            line_ordinal = line.get("line_ordinal")
            key = (page_sequence, line_ordinal)
            if type(line_ordinal) is not int or line_ordinal < 0 or key in lookup:
                raise _error("authenticated joined line locator drifted or repeated")
            lookup[key] = line
    return lookup


def _input_cell(
    raw: Mapping[str, Any],
    lookup: Mapping[tuple[int, int], Mapping[str, Any]],
    *,
    page_hint: int | None,
) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise _unresolved("graph numeric cell is not one observed record")
    lane = raw.get("lane_index")
    page = raw.get("page_sequence", page_hint)
    line_index = raw.get("source_line_index")
    if (
        type(lane) is not int
        or lane < 0
        or type(page) is not int
        or page <= 0
        or type(line_index) is not int
        or line_index < 0
    ):
        raise _unresolved("graph numeric cell has no exact page/line/lane locator")
    joined = lookup.get((page, line_index))
    if joined is None:
        raise _unresolved("graph numeric cell locator is absent from authenticated snapshot")
    # Horizontal and embedded-footnote graphs retain token-level surfaces.
    # Sparse stacked graphs may intentionally retain only the exact line
    # locator; in that case recover both bound reader surfaces from the same
    # authenticated joined line, never from geometry or a neighbouring row.
    raw_pp = raw.get("source_surface")
    raw_viet = raw.get("vietocr_surface")
    if "source_surface" in raw and raw_pp is not None and type(raw_pp) is not str:
        raise _error("graph PP-OCRv6 observed surface type drifted")
    if "vietocr_surface" in raw and raw_viet is not None and type(raw_viet) is not str:
        raise _error("graph VietOCR observed surface type drifted")
    pp = (
        raw_pp
        if type(raw_pp) is str
        else joined.get("numeric_recognition", {}).get("raw_prediction")
    )
    viet = raw_viet if type(raw_viet) is str else joined.get("vietocr_text")
    if pp is not None and type(pp) is not str:
        raise _error("graph PP-OCRv6 observed surface type drifted")
    if viet is not None and type(viet) is not str:
        raise _error("graph VietOCR observed surface type drifted")
    if pp is None and viet is None:
        raise _unresolved("graph numeric cell retains no observed reader surface")
    return {
        "lane_index": lane,
        "page_sequence": page,
        "ppocrv6_surface": pp,
        "source_line_index": line_index,
        "vietocr_surface": viet,
    }


def _input_cells(
    values: Any,
    lookup: Mapping[tuple[int, int], Mapping[str, Any]],
    *,
    page_hint: int | None,
) -> list[dict[str, Any]]:
    if type(values) is not list or not values:
        raise _unresolved("graph row retains no observed numeric value vector")
    result = [_input_cell(value, lookup, page_hint=page_hint) for value in values]
    result.sort(key=lambda item: item["lane_index"])
    if len({item["lane_index"] for item in result}) != len(result):
        raise _unresolved("graph numeric vector repeats one lane")
    return result


def _margin_alias(surface: Any) -> bool:
    if type(surface) is not str:
        return False
    normalized = normalize_vietnamese_anchor_v1(surface)
    return any(
        token in normalized
        for token in (
            "giao dich ky quy",
            "ky quy",
            "margin",
            "ung truoc tien ban chung khoan",
            "cho vay tai mbs",
        )
    )


def _horizontal_margin(graph: Mapping[str, Any]) -> tuple[str, Mapping[str, Any] | None]:
    additive = graph.get("optional_additive_row")
    nonadditive = graph.get("nonadditive_rows")
    if nonadditive is None:
        nonadditive = []
    if type(nonadditive) is not list:
        raise _error("loan-quality graph nonadditive row list drifted")
    included = [
        row
        for row in nonadditive
        if isinstance(row, Mapping)
        and row.get("classification") == "NONADDITIVE_INCLUDED_DISCLOSURE"
        and row.get("parent_role") == "STANDARD"
        and _margin_alias(row.get("label_surface"))
    ]
    excluded = [
        row
        for row in nonadditive
        if isinstance(row, Mapping)
        and row.get("classification") == "NONADDITIVE_EXCLUDED_DISCLOSURE"
        and row.get("context_disposition")
        == "EXPLICIT_EXCLUDED_FOOTNOTE_RECONCILES_CORE_TO_CUSTOMER_LOAN_PARENT"
    ]
    candidates = int(additive is not None) + len(included) + len(excluded)
    if candidates > 1:
        raise _unresolved("multiple margin presentation modes remain in one graph")
    if excluded:
        return "EXPLICITLY_EXCLUDED_FROM_CORE_VIA_FOOTNOTE", excluded[0]
    if additive is not None:
        if not isinstance(additive, Mapping) or additive.get("classification") != (
            "ADDITIVE_MARGIN_OR_ADVANCE_CHILD"
        ):
            raise _error("loan-quality additive margin classification drifted")
        return "STANDALONE_AFTER_FIVE_GRADES", additive
    if included:
        return "INCLUDED_IN_747_VIA_5746", included[0]
    return "NOT_OBSERVED_DO_NOT_SYNTHESIZE", None


def _bind_excluded_footnote_challenger(
    graph: Mapping[str, Any],
    joined_pages: Sequence[Mapping[str, Any]],
    evaluation: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Bind vetted E-0168 token values only through exact graph/store locators."""

    cloned = canonical_clone_v1(graph)
    lookup = _source_line_lookup(joined_pages)
    sample_lines: dict[str, tuple[tuple[int, int], Mapping[str, Any]]] = {}
    for locator, line in lookup.items():
        sample_id = line.get("sample_id")
        if sample_id not in _EXPECTED_FOOTNOTE_OBSERVATIONS:
            continue
        if sample_id in sample_lines:
            raise _error("E-0168 sample repeats in one authenticated document")
        sample_lines[sample_id] = (locator, line)
    nonadditive = cloned.get("nonadditive_rows", [])
    excluded = [
        row
        for row in nonadditive
        if isinstance(row, Mapping)
        and row.get("classification") == "NONADDITIVE_EXCLUDED_DISCLOSURE"
        and row.get("context_disposition")
        == "EXPLICIT_EXCLUDED_FOOTNOTE_RECONCILES_CORE_TO_CUSTOMER_LOAN_PARENT"
    ]
    if not sample_lines:
        if excluded:
            raise _unresolved("excluded footnote graph has no exact E-0168 authenticated crop")
        return cloned, []
    if len(sample_lines) != 1 or len(excluded) != 1:
        raise _unresolved("E-0168 crop does not bind one unique excluded footnote graph row")
    sample_id, (locator, line) = next(iter(sample_lines.items()))
    observation = next(
        item for item in evaluation["observations"] if item["sample_id"] == sample_id
    )
    expected = _EXPECTED_FOOTNOTE_OBSERVATIONS[sample_id]
    row = excluded[0]
    values = row.get("values")
    label_indices = row.get("label_source_line_indices")
    parent_values = cloned.get("totals", {}).get("customer_loan_parent")
    if (
        not same_typed_json_v1(line.get("crop_ref"), expected["crop_ref"])
        or line.get("numeric_recognition", {}).get("raw_prediction")
        != observation["ppocrv6_original_surface"]
        or line.get("vietocr_text") != observation["vietocr_transformer_surface"]
        or type(label_indices) is not list
        or locator[1] not in label_indices
        or type(values) is not list
        or len(values) != 2
        or type(parent_values) is not list
        or len(parent_values) != 2
    ):
        raise _unresolved("E-0168 crop, graph footnote, or parent locator does not bind exactly")
    parent_pages = {item.get("page_sequence") for item in parent_values}
    if (
        any(type(page) is not int for page in parent_pages)
        or not parent_pages
        or max(parent_pages) >= locator[0]
    ):
        raise _unresolved("excluded footnote parent is not independently observed on a prior page")
    money_lanes = [
        lane for lane, lane_type in enumerate(cloned.get("lane_types", [])) if lane_type == "MONEY"
    ]
    if len(money_lanes) != 2:
        raise _unresolved("E-0168 excluded footnote does not expose exactly two money lanes")
    ordered = sorted(values, key=lambda item: item.get("lane_index", -1))
    for token_ordinal, (lane, value, surface) in enumerate(
        zip(money_lanes, ordered, observation["extracted_monetary_surfaces"], strict=True)
    ):
        if (
            value.get("page_sequence") != locator[0]
            or value.get("source_line_index") != locator[1]
            or value.get("embedded_token_ordinal") != token_ordinal
            or value.get("lane_index") != lane
            or value.get("lane_type") != "MONEY"
            or value.get("role") != "NONADDITIVE_EXCLUDED_DISCLOSURE"
            or value.get("source_line_surface")
            not in {None, observation["ppocrv6_original_surface"]}
            or value.get("vietocr_line_surface") != observation["vietocr_transformer_surface"]
        ):
            raise _unresolved("E-0168 embedded token graph provenance drifted")
        # E-0168 is corroboration, never a replacement reader.  Both raw
        # reader surfaces remain unchanged; the tracked pixel/Gemma token must
        # already parse to the same integer as the observed VietOCR token.
        raw_vietocr_surface = value.get("vietocr_surface")
        if type(raw_vietocr_surface) is not str or _integer_surface(
            raw_vietocr_surface
        ) != _integer_surface(surface):
            raise _unresolved("E-0168 and raw VietOCR footnote token disagree")
    return cloned, [
        {
            "crop_ref": canonical_clone_v1(line["crop_ref"]),
            "observed_values": [_integer_surface(item) for item in expected["surfaces"]],
            "sample_id": sample_id,
            "status": "BOUND_GRAPH_PIXEL_VIETOCR_TWO_GEMMA_REQUESTS_PENDING_PARENT_EQUATION",
        }
    ]


def _validate_excluded_footnote_accounting_hits(
    evidence: Mapping[str, Any], hits: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    if not hits:
        if evidence.get("margin_mode") == "EXPLICITLY_EXCLUDED_FROM_CORE_VIA_FOOTNOTE":
            raise _unresolved("excluded footnote reconciliation has no E-0168 crop binding")
        return []
    if len(hits) != 1 or evidence.get("margin_mode") != (
        "EXPLICITLY_EXCLUDED_FROM_CORE_VIA_FOOTNOTE"
    ):
        raise _unresolved("E-0168 crop acquired another margin presentation mode")
    hit = hits[0]
    expected = _EXPECTED_FOOTNOTE_OBSERVATIONS[hit["sample_id"]]
    core, margin, parent = expected["accounting"]
    money_lanes = [
        lane for lane, lane_type in enumerate(evidence["lane_types"]) if lane_type == "MONEY"
    ]
    observed_core = _selected_money(evidence["total"]["cells"], money_lanes)
    observed_margin = _selected_money(evidence["margin"]["cells"], money_lanes)
    observed_parent = _selected_money(evidence["parent_total"]["cells"], money_lanes)
    if observed_core != core or observed_margin != margin or observed_parent != parent:
        raise _unresolved("E-0168 accounting populations differ from reconciled graph evidence")
    return [
        {
            **canonical_clone_v1(hit),
            "observed_core_totals": core,
            "observed_parent_totals": parent,
            "status": "EXACT_CORE_PLUS_EXCLUDED_1944_EQUALS_OBSERVED_PARENT_BOTH_LANES",
        }
    ]


def _graph_to_numeric_input(
    graph: Mapping[str, Any],
    graph_result_id: str,
    joined_pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    lookup = _source_line_lookup(joined_pages)
    page = graph.get("page_sequence")
    layout = graph.get("layout_mode")
    if layout == "HORIZONTAL_TYPED_PERIOD_LANES":
        lane_types = graph.get("lane_types")
        rows = graph.get("rows")
        if type(lane_types) is not list or type(rows) is not list or len(rows) != 5:
            raise _unresolved("horizontal graph row or typed-lane axis is incomplete")
        source_rows = []
        for role, row in zip(_ROLES, rows, strict=True):
            if not isinstance(row, Mapping) or row.get("role") != role:
                raise _unresolved("horizontal graph five-grade role order drifted")
            label = row.get("label", {}).get("surface")
            if type(label) is not str or not label.strip():
                raise _unresolved("horizontal graph grade label is unresolved")
            source_rows.append(
                {
                    "cells": _input_cells(row.get("values"), lookup, page_hint=page),
                    "label_surface": label,
                    "role": role,
                }
            )
        mode, margin_row = _horizontal_margin(graph)
        totals = graph.get("totals")
        if not isinstance(totals, Mapping):
            raise _unresolved("horizontal graph total population is absent")
        total_values = (
            totals.get("grand") if mode == "STANDALONE_AFTER_FIVE_GRADES" else totals.get("core")
        )
        total = {
            "cells": _input_cells(total_values, lookup, page_hint=page),
            "label_surface": "PRINTED_LOAN_QUALITY_TOTAL",
        }
        margin = None
        if margin_row is not None:
            margin = {
                "cells": _input_cells(margin_row.get("values"), lookup, page_hint=page),
                "label_surface": margin_row.get("label_surface"),
            }
            if type(margin["label_surface"]) is not str or not margin["label_surface"].strip():
                raise _unresolved("observed margin row label is unresolved")
        parent = None
        if mode == "EXPLICITLY_EXCLUDED_FROM_CORE_VIA_FOOTNOTE":
            parent = {
                "cells": _input_cells(totals.get("customer_loan_parent"), lookup, page_hint=page),
                "label_surface": "INDEPENDENTLY_OBSERVED_CUSTOMER_LOAN_PARENT_TOTAL",
            }
        source = {
            "format_version": numeric_v1.INPUT_FORMAT_VERSION,
            "lane_types": lane_types,
            "layout_mode": layout,
            "margin": margin,
            "margin_mode": mode,
            "parent_total": parent,
            "rows": source_rows,
            "source_id": graph_result_id,
            "sparse_blocks": [],
            "total": total,
        }
    elif layout == "STACKED_PERIOD_BLOCKS_MULTI_ASSET_COLUMNS":
        blocks = graph.get("blocks")
        centers = graph.get("column_centers_x2")
        target = graph.get("customer_loan_column", {}).get("column_index")
        companion = graph.get("total_column", {}).get("column_index")
        if (
            type(blocks) is not list
            or len(blocks) != 2
            or type(centers) is not list
            or len(centers) < 2
            or type(target) is not int
            or type(companion) is not int
        ):
            raise _unresolved("stacked graph block or column axis is incomplete")
        sparse_blocks = []
        for block_ordinal, block in enumerate(blocks):
            if not isinstance(block, Mapping) or block.get("block_ordinal") != block_ordinal:
                raise _unresolved("stacked graph block order drifted")
            if type(block.get("rows")) is not list or len(block["rows"]) != 5:
                raise _unresolved("stacked graph does not retain five rows per period")
            block_rows = []
            for role, row in zip(_ROLES, block["rows"], strict=True):
                if not isinstance(row, Mapping) or row.get("role") != role:
                    raise _unresolved("stacked graph five-grade role order drifted")
                label = row.get("label", {}).get("surface")
                if type(label) is not str or not label.strip():
                    raise _unresolved("stacked graph grade label is unresolved")
                block_rows.append(
                    {
                        "cells": _input_cells(row.get("values"), lookup, page_hint=page),
                        "label_surface": label,
                        "role": role,
                    }
                )
            if len(block_rows) != 5:
                raise _unresolved("stacked graph does not retain five rows per period")
            sparse_blocks.append(
                {
                    "block_ordinal": block_ordinal,
                    "column_count": len(centers),
                    "rows": block_rows,
                    "target_column_index": target,
                    "total": {
                        "cells": _input_cells(block.get("total"), lookup, page_hint=page),
                        "label_surface": "PRINTED_STACKED_BLOCK_TOTAL",
                    },
                    "total_column_index": companion,
                }
            )
        source = {
            "format_version": numeric_v1.INPUT_FORMAT_VERSION,
            "lane_types": ["MONEY", "MONEY"],
            "layout_mode": layout,
            "margin": None,
            "margin_mode": "NOT_OBSERVED_DO_NOT_SYNTHESIZE",
            "parent_total": None,
            "rows": [],
            "source_id": graph_result_id,
            "sparse_blocks": sparse_blocks,
            "total": None,
        }
    else:
        raise _unresolved("loan-quality graph layout mode is unresolved")
    return numeric_v1.validate_loan_quality_numeric_row_reconciliation_input_v1(source)


def _period_axis(graph: Mapping[str, Any], money_lanes: Sequence[int]) -> list[dict[str, Any]]:
    if graph.get("layout_mode") == "STACKED_PERIOD_BLOCKS_MULTI_ASSET_COLUMNS":
        axes = graph.get("axes")
        if type(axes) is not list or len(axes) != len(money_lanes):
            raise _unresolved("stacked graph period axis is incomplete")
        return canonical_clone_v1(axes)
    axes = graph.get("axes")
    centers = graph.get("lane_centers_x2")
    if type(axes) is not list or type(centers) is not list or not axes:
        raise _unresolved("horizontal graph period axis is incomplete")
    periods = []
    for lane in money_lanes:
        if not 0 <= lane < len(centers):
            raise _unresolved("horizontal money lane has no geometric center")
        candidates = sorted(
            axes,
            key=lambda item: (
                abs(item["x_center_x2"] - centers[lane]),
                item["x_center_x2"],
            ),
        )
        periods.append(canonical_clone_v1(candidates[0]))
    return periods


def _selected_money(cells: Sequence[Mapping[str, Any]], money_lanes: Sequence[int]) -> list[int]:
    by_lane = {cell.get("lane_index"): cell.get("selected_value") for cell in cells}
    values = [by_lane.get(lane) for lane in money_lanes]
    if any(type(value) is not int for value in values):
        raise _unresolved("verified mapping retains an unresolved money value")
    return values  # type: ignore[return-value]


def _schema_nodes(schema: Mapping[str, Any]) -> dict[int, dict[str, Any]]:
    validated = numeric_v1.validate_loan_quality_closed_schema_projection_v1(schema)
    return {node["report_norm_id"]: node for node in validated["nodes"]}


def _mapping_rows(
    evidence: Mapping[str, Any],
    graph: Mapping[str, Any],
    closed_schema: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    if evidence.get("status") != "EXACT_OBSERVED_NUMERIC_RECONCILIATION":
        raise _unresolved("numeric reconciliation is not exact")
    nodes = _schema_nodes(closed_schema)
    money_lanes = [
        lane for lane, lane_type in enumerate(evidence["lane_types"]) if lane_type == "MONEY"
    ]
    if len(money_lanes) != 2:
        raise _unresolved("loan-quality mapping requires exactly two observed money periods")
    periods = _period_axis(graph, money_lanes)
    rows = evidence.get("rows")
    if type(rows) is not list or [row.get("role") for row in rows] != list(_ROLES):
        raise _error("numeric reconciliation five-grade axis drifted")
    emitted_values: dict[str, list[int]] = {
        row["role"]: _selected_money(row["cells"], money_lanes) for row in rows
    }
    source_values = canonical_clone_v1(emitted_values)
    mode = evidence.get("margin_mode")
    margin = evidence.get("margin")
    margin_values: list[int] | None = None
    if mode == "NOT_OBSERVED_DO_NOT_SYNTHESIZE":
        if margin is not None:
            raise _error("unobserved margin mode acquired a mapping row")
    else:
        if not isinstance(margin, Mapping):
            raise _unresolved("observed margin mode has no reconciled row")
        margin_values = _selected_money(margin["cells"], money_lanes)
    if mode == "INCLUDED_IN_747_VIA_5746":
        if margin_values is None:
            raise _unresolved("included margin mode has no observed margin values")
        normalized = [
            source_values["STANDARD"][lane] - margin_values[lane]
            for lane in range(len(money_lanes))
        ]
        if any(value < 0 for value in normalized):
            raise _unresolved("included margin exceeds its observed standard-loan population")
        emitted_values["STANDARD"] = normalized

    mappings = []
    for role in _ROLES:
        schema_id = _ROLE_TO_SCHEMA_ID[role]
        mappings.append(
            {
                **canonical_clone_v1(nodes[schema_id]),
                "normalization": (
                    {
                        "observed_inclusive_values": source_values[role],
                        "operation": "SUBTRACT_EXACT_OBSERVED_5746_AND_EMIT_1944",
                    }
                    if role == "STANDARD" and mode == "INCLUDED_IN_747_VIA_5746"
                    else {"operation": "KEEP_OBSERVED_CORE_VALUE_UNCHANGED"}
                ),
                "period_axis": canonical_clone_v1(periods),
                "source_label_surfaces": canonical_clone_v1(
                    next(row["label_surfaces"] for row in rows if row["role"] == role)
                ),
                "source_role": role,
                "status": "VERIFIED_BY_CODEX",
                "values": emitted_values[role],
            }
        )
    if margin_values is not None:
        mappings.append(
            {
                **canonical_clone_v1(nodes[1944]),
                "normalization": {
                    "operation": {
                        "STANDALONE_AFTER_FIVE_GRADES": "EMIT_OBSERVED_STANDALONE_1944",
                        "INCLUDED_IN_747_VIA_5746": "EMIT_OBSERVED_1944_VIA_SOURCE_ONLY_5746_BRIDGE",
                        "EXPLICITLY_EXCLUDED_FROM_CORE_VIA_FOOTNOTE": (
                            "EMIT_OBSERVED_1944_KEEP_CORE_UNCHANGED"
                        ),
                    }[mode],
                    "source_bridge_report_norm_id": (
                        5746 if mode == "INCLUDED_IN_747_VIA_5746" else None
                    ),
                },
                "period_axis": canonical_clone_v1(periods),
                "source_label_surfaces": canonical_clone_v1(margin["label_surfaces"]),
                "source_role": "MARGIN_AND_SECURITIES_ADVANCE",
                "status": "VERIFIED_BY_CODEX",
                "values": margin_values,
            }
        )

    total = evidence.get("total")
    if not isinstance(total, Mapping):
        raise _unresolved("numeric reconciliation has no printed quality total")
    core_total = _selected_money(total["cells"], money_lanes)
    parent_source = (
        evidence.get("parent_total")
        if mode == "EXPLICITLY_EXCLUDED_FROM_CORE_VIA_FOOTNOTE"
        else total
    )
    if not isinstance(parent_source, Mapping):
        raise _unresolved("excluded footnote has no independently observed customer-loan parent")
    parent_values = _selected_money(parent_source["cells"], money_lanes)
    checks = []
    for lane in range(len(money_lanes)):
        observed_grade_sum = sum(source_values[role][lane] for role in _ROLES)
        expected_core = (
            core_total[lane] - margin_values[lane]
            if mode == "STANDALONE_AFTER_FIVE_GRADES" and margin_values is not None
            else core_total[lane]
        )
        if observed_grade_sum != expected_core:
            raise _unresolved("five observed grade rows do not close to their printed core")
        mapped_sum = sum(mapping["values"][lane] for mapping in mappings)
        if mapped_sum != parent_values[lane]:
            raise _unresolved("bounded normalized mappings do not close to observed family parent")
        checks.append(
            {
                "mapped_child_sum": mapped_sum,
                "money_lane_index": money_lanes[lane],
                "observed_core_total": core_total[lane],
                "observed_parent_total": parent_values[lane],
                "presentation_mode": mode,
                "status": "EXACT_BOUNDED_MAPPING_TO_OBSERVED_PARENT",
            }
        )
    parent = {
        **canonical_clone_v1(nodes[746]),
        "period_axis": canonical_clone_v1(periods),
        "source_owner": canonical_clone_v1(graph.get("owner_context")),
        "status": "VERIFIED_BY_CODEX",
        "values": parent_values,
    }
    return parent, mappings, checks


def _integer_surface(surface: str) -> int:
    if not re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+|\d+", surface):
        raise _error("challenger selected surface is not one visible integer token")
    return int(re.sub(r"[.,]", "", surface))


def _reconciled_cells(evidence: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    cells = [cell for row in evidence.get("rows", []) for cell in row.get("cells", [])]
    for record_name in ("total", "parent_total", "margin"):
        record = evidence.get(record_name)
        if isinstance(record, Mapping):
            cells.extend(record.get("cells", []))
    return cells


def _challenger_hits(
    evidence: Mapping[str, Any],
    joined_pages: Sequence[Mapping[str, Any]],
    challenger: Mapping[str, Any],
) -> list[dict[str, Any]]:
    lookup = _source_line_lookup(joined_pages)
    sample_lines: dict[str, tuple[tuple[int, int], Mapping[str, Any]]] = {}
    for locator, line in lookup.items():
        sample_id = line.get("sample_id")
        if sample_id not in _EXPECTED_CHALLENGER_OBSERVATIONS:
            continue
        if sample_id in sample_lines:
            raise _error("challenger sample repeats in one authenticated document")
        sample_lines[sample_id] = (locator, line)
    cells = {
        (cell.get("page_sequence"), cell.get("source_line_index")): cell
        for cell in _reconciled_cells(evidence)
    }
    observations = {item["sample_id"]: item for item in challenger["observations"]}
    required_checks = [
        check
        for check in evidence.get("accounting_checks", [])
        if isinstance(check, Mapping) and check.get("required_for_acceptance") is True
    ]
    if (
        evidence.get("status") != "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
        or not required_checks
        or any(
            check.get("status")
            not in {
                "EXACT_OBSERVED_EQUATION",
                "EXACT_EQUATION_UNIQUELY_SELECTED_OBSERVED_CONFLICT",
            }
            for check in required_checks
        )
    ):
        raise _unresolved("E-0167 challenger has no complete required accounting corroboration")
    hits = []
    for sample_id, (locator, line) in sorted(sample_lines.items()):
        expected = _EXPECTED_CHALLENGER_OBSERVATIONS[sample_id]
        observation = observations[sample_id]
        if not same_typed_json_v1(line.get("crop_ref"), expected["crop_ref"]):
            raise _error("challenger sample locator points to another authenticated crop")
        cell = cells.get(locator)
        expected_value = _integer_surface(expected["selected_surface"])
        status = cell.get("status") if cell is not None else None
        singleton_vietocr = (
            cell is not None
            and status == "SELECTED_SINGLE_PARSEABLE_OBSERVATION"
            and cell.get("selected_readers") == ["VIETOCR"]
        )
        equation_selected_conflict = status == "SELECTED_UNIQUE_OBSERVED_VALUE_BY_EXACT_EQUATION"
        if (
            cell is None
            or cell.get("selected_value") != expected_value
            or cell.get("vietocr_surface") != observation["vietocr_transformer_surface"]
            or cell.get("ppocrv6_surface") != observation["ppocrv6_original_surface"]
            or not (singleton_vietocr or equation_selected_conflict)
        ):
            raise _unresolved("E-0167 crop is not one exact corroborated observed value")
        hits.append(
            {
                "crop_ref": canonical_clone_v1(line["crop_ref"]),
                "sample_id": sample_id,
                "selected_value": expected_value,
                "status": "PIXEL_VIETOCR_GEMMA4_AND_REQUIRED_EXACT_ACCOUNTING_CORROBORATED",
            }
        )
    return hits


def _unresolved_trial(
    packet: Mapping[str, Any],
    graph_result: Mapping[str, Any],
    reasons: Sequence[str],
) -> dict[str, Any]:
    return {
        "accounting_mapping_checks": [],
        "challenger_hits": [],
        "document": canonical_clone_v1(packet),
        "excluded_footnote_challenger_hits": [],
        "graph": None,
        "graph_result_id": graph_result.get("result_id"),
        "mapped_children": [],
        "mapped_parent": None,
        "numeric_evidence": None,
        "numeric_input": None,
        "page_sequence": None,
        "status": "UNRESOLVED_FAIL_CLOSED",
        "unresolved_reasons": sorted(set(reasons)),
    }


def _trial(
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    ordinal: int,
    closed_schema: Mapping[str, Any],
    challenger: Mapping[str, Any],
    footnote_challenger: Mapping[str, Any],
) -> dict[str, Any]:
    packet = store_v1.read_authenticated_family_first_document_packet_v1(
        capability, document_ordinal=ordinal
    )
    snapshot = store_v1.read_authenticated_family_first_document_evidence_snapshot_v1(
        capability,
        document_ordinal=ordinal,
        selected_pages=tuple(range(1, packet["page_count"] + 1)),
    )
    matcher_pages = _matcher_pages(snapshot["joined_pages"])
    graph_result = graph_v2.build_loan_quality_variant_graph_document_v2(
        matcher_pages, enable_extended_annual_variants=True
    )
    candidates = [
        graph
        for graph in graph_result["graphs"]
        if graph.get("status")
        in {"ACCEPTED_VARIANT_GRAPH", "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"}
    ]
    if len(candidates) != 1 or graph_result["uniqueness"]["full_match_count"] != 1:
        return _unresolved_trial(
            packet,
            graph_result,
            [
                "NO_UNIQUE_STRUCTURALLY_RESOLVED_LOAN_QUALITY_GRAPH",
                graph_result["status"],
            ],
        )
    graph = candidates[0]
    try:
        numeric_graph, footnote_hits = _bind_excluded_footnote_challenger(
            graph, snapshot["joined_pages"], footnote_challenger
        )
        source = _graph_to_numeric_input(
            numeric_graph, graph_result["result_id"], snapshot["joined_pages"]
        )
        evidence = numeric_v1.build_loan_quality_numeric_row_reconciliation_v1(source)
        numeric_v1.validate_loan_quality_numeric_row_reconciliation_replay_v1(evidence, source)
        if evidence["status"] != "EXACT_OBSERVED_NUMERIC_RECONCILIATION":
            return _unresolved_trial(
                packet,
                graph_result,
                [evidence["status"], *evidence["unresolved_reasons"]],
            )
        footnote_hits = _validate_excluded_footnote_accounting_hits(evidence, footnote_hits)
        parent, mappings, checks = _mapping_rows(evidence, graph, closed_schema)
        hits = _challenger_hits(evidence, snapshot["joined_pages"], challenger)
    except LoanQualityTrialUnresolvedV1Error as exc:
        return _unresolved_trial(packet, graph_result, [str(exc)])
    return {
        "accounting_mapping_checks": checks,
        "challenger_hits": hits,
        "document": canonical_clone_v1(packet),
        "excluded_footnote_challenger_hits": footnote_hits,
        "graph": canonical_clone_v1(graph),
        "graph_result_id": graph_result["result_id"],
        "mapped_children": mappings,
        "mapped_parent": parent,
        "numeric_evidence": canonical_clone_v1(evidence),
        "numeric_input": canonical_clone_v1(source),
        "page_sequence": graph["page_sequence"],
        "status": "VERIFIED_BY_CODEX",
        "unresolved_reasons": [],
    }


def _terminal_material(
    trials: Sequence[Mapping[str, Any]], inputs: Mapping[str, Any]
) -> dict[str, Any]:
    if type(trials) not in {list, tuple} or len(trials) != _TARGET_DOCUMENT_COUNT:
        raise _error("loan-quality terminal sweep requires exactly 140 trials")
    unresolved = [trial for trial in trials if trial.get("status") != "VERIFIED_BY_CODEX"]
    grade_count = sum(
        mapping.get("report_norm_id") in set(_ROLE_TO_SCHEMA_ID.values())
        for trial in trials
        for mapping in trial.get("mapped_children", [])
    )
    margin_count = sum(
        mapping.get("report_norm_id") == 1944
        for trial in trials
        for mapping in trial.get("mapped_children", [])
    )
    mapping_count = sum(len(trial.get("mapped_children", [])) for trial in trials)
    challenger_hits = sum(len(trial.get("challenger_hits", [])) for trial in trials)
    footnote_hits = sum(len(trial.get("excluded_footnote_challenger_hits", [])) for trial in trials)
    if unresolved:
        raise _error("loan-quality sweep retains one or more fail-closed unresolved trials")
    if (
        grade_count != _TARGET_GRADE_MAPPING_COUNT
        or margin_count != _TARGET_MARGIN_MAPPING_COUNT
        or mapping_count != _TARGET_MAPPING_COUNT
    ):
        raise _error("loan-quality terminal mapping counts are not exactly 700 + 27 = 727")
    if challenger_hits != len(_EXPECTED_CHALLENGER_OBSERVATIONS):
        raise _error("E-0167 challenger crops are not each bound exactly once")
    modes = {mode: 0 for mode in numeric_v1.MARGIN_PRESENTATION_MODES}
    layouts = {layout: 0 for layout in _TARGET_LAYOUT_COUNTS}
    lane_axes = {axis: 0 for axis in _TARGET_LANE_AXIS_COUNTS}
    challenger_samples: list[str] = []
    footnote_samples: list[str] = []
    for trial in trials:
        evidence = trial.get("numeric_evidence")
        if (
            not isinstance(evidence, Mapping)
            or evidence.get("status") != "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
        ):
            raise _error("verified loan-quality trial lacks exact numeric reconciliation")
        mode = evidence["margin_mode"]
        if mode not in modes:
            raise _error("loan-quality trial margin presentation mode drifted")
        modes[mode] += 1
        layout = evidence.get("layout_mode")
        if layout not in layouts:
            raise _error("loan-quality trial layout mode drifted")
        layouts[layout] += 1
        lane_types = evidence.get("lane_types")
        if type(lane_types) is not list or any(
            type(lane_type) is not str for lane_type in lane_types
        ):
            raise _error("loan-quality trial typed lane axis drifted")
        lane_axis = ",".join(lane_types)
        if lane_axis not in lane_axes:
            raise _error("loan-quality trial typed lane axis drifted")
        lane_axes[lane_axis] += 1
        expected_ids = [747, 748, 749, 750, 751]
        if mode != "NOT_OBSERVED_DO_NOT_SYNTHESIZE":
            expected_ids.append(1944)
        if [item.get("report_norm_id") for item in trial["mapped_children"]] != expected_ids:
            raise _error("verified loan-quality trial mapping identity/order drifted")
        mapped_parent = trial.get("mapped_parent")
        if not isinstance(mapped_parent, Mapping) or mapped_parent.get("report_norm_id") != 746:
            raise _error("verified loan-quality trial family parent mapping drifted")
        for hit in trial.get("challenger_hits", []):
            if not isinstance(hit, Mapping) or type(hit.get("sample_id")) is not str:
                raise _error("E-0167 challenger hit shape drifted")
            challenger_samples.append(hit["sample_id"])
        for hit in trial.get("excluded_footnote_challenger_hits", []):
            if not isinstance(hit, Mapping) or type(hit.get("sample_id")) is not str:
                raise _error("E-0168 footnote challenger hit shape drifted")
            footnote_samples.append(hit["sample_id"])
    if modes != _TARGET_MARGIN_MODE_COUNTS:
        raise _error("loan-quality terminal margin presentation distribution drifted")
    if layouts != _TARGET_LAYOUT_COUNTS:
        raise _error("loan-quality terminal layout distribution drifted")
    if lane_axes != _TARGET_LANE_AXIS_COUNTS:
        raise _error("loan-quality terminal typed-lane distribution drifted")
    if sorted(challenger_samples) != sorted(_EXPECTED_CHALLENGER_OBSERVATIONS):
        raise _error("E-0167 challenger sample set is not exact")
    if footnote_hits != len(_EXPECTED_FOOTNOTE_OBSERVATIONS) or sorted(footnote_samples) != sorted(
        _EXPECTED_FOOTNOTE_OBSERVATIONS
    ):
        raise _error("E-0168 excluded-footnote crops are not each bound exactly once")
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "inputs": canonical_clone_v1(inputs),
        "metrics": {
            "document_count": _TARGET_DOCUMENT_COUNT,
            "excluded_footnote_hosted_gemma4_bound_crop_count": footnote_hits,
            "hosted_gemma4_consensus_challenger_hit_count": challenger_hits,
            "layout_mode_trial_counts": layouts,
            "mapped_core_grade_record_count": grade_count,
            "mapped_margin_record_count": margin_count,
            "mapped_record_count": mapping_count,
            "margin_presentation_mode_trial_counts": modes,
            "numeric_exact_trial_count": _TARGET_DOCUMENT_COUNT,
            "structure_unique_trial_count": _TARGET_DOCUMENT_COUNT,
            "typed_lane_axis_trial_counts": lane_axes,
            "unresolved_trial_count": 0,
            "verified_trial_count": _TARGET_DOCUMENT_COUNT,
        },
        "state": "COMPLETE",
        "trials": canonical_clone_v1(trials),
    }
    return {**material, "sweep_id": "lq140v1:sweep:" + canonical_json_sha256_v1(material)}


def build_authenticated_family_first_loan_quality_140_filing_schema_sweep_v1(
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    project_root: Path,
) -> dict[str, Any]:
    """Build all 140 trials from the exact live authenticated evidence store."""

    if not isinstance(project_root, Path):
        raise _error("loan-quality sweep project root must be one pathlib Path")
    root = project_root.resolve()
    store_projection = store_v1.project_authenticated_family_first_document_evidence_store_v1(
        capability
    )
    if store_projection["metrics"]["document_count"] != _TARGET_DOCUMENT_COUNT:
        raise _error("loan-quality sweep requires the fixed 140-filing denominator")
    challenger, challenger_ref = _strict_challenger(root)
    footnote_challenger, footnote_challenger_ref = _strict_footnote_challenger(root)
    context_ref = _stable_ref(root, MARGIN_CONTEXT_PATH)
    context = numeric_v1.load_loan_quality_margin_context_140_v2(root / MARGIN_CONTEXT_PATH)
    if not same_typed_json_v1(_stable_ref(root, MARGIN_CONTEXT_PATH), context_ref):
        raise _error("loan-quality margin context changed during validated read")
    schema_authority, schema_by_id = _authority_snapshot(root)
    closed_schema = numeric_v1.project_loan_quality_closed_schema_v1(schema_by_id, context)
    trials = [
        _trial(capability, ordinal, closed_schema, challenger, footnote_challenger)
        for ordinal in range(1, _TARGET_DOCUMENT_COUNT + 1)
    ]
    implementation_refs = {path.name: _stable_ref(root, path) for path in _IMPLEMENTATION_PATHS}
    inputs = {
        "document_evidence_store": store_projection,
        "excluded_footnote_hosted_gemma4_challenger": footnote_challenger_ref,
        "excluded_footnote_hosted_gemma4_challenger_evaluation_id": footnote_challenger[
            "evaluation_id"
        ],
        "hosted_gemma4_numeric_challenger": challenger_ref,
        "hosted_gemma4_numeric_challenger_evaluation_id": challenger["evaluation_id"],
        "implementation_refs": implementation_refs,
        "margin_context": context_ref,
        "margin_context_id": context["context_id"],
        "schema_authority": schema_authority,
        "schema_projection": closed_schema,
    }
    return _terminal_material(trials, inputs)


def validate_authenticated_family_first_loan_quality_140_filing_schema_sweep_replay_v1(
    value: Any,
    capability: store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    project_root: Path,
) -> dict[str, Any]:
    expected = build_authenticated_family_first_loan_quality_140_filing_schema_sweep_v1(
        capability, project_root
    )
    if not same_typed_json_v1(value, expected):
        raise _error("loan-quality 140-filing schema sweep does not replay exactly")
    return expected


def _strict_result(path: Path) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON token: {token}")
            ),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise _error("persisted loan-quality sweep is not strict JSON") from exc
    if type(value) is not dict or payload != canonical_json_bytes_v1(value) + b"\n":
        raise _error("persisted loan-quality sweep is not canonical JSON plus LF")
    return value


def _write_exclusive(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    directory = os.open(
        path.parent,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
    )
    temporary_name = f".{path.name}.stage-{secrets.token_hex(16)}"
    temporary_created = False
    try:
        descriptor = os.open(
            temporary_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            0o444,
            dir_fd=directory,
        )
        temporary_created = True
        try:
            view = memoryview(payload)
            while view:
                count = os.write(descriptor, view)
                if count <= 0:
                    raise _error("loan-quality sweep write made no progress")
                view = view[count:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        try:
            os.link(
                temporary_name,
                path.name,
                src_dir_fd=directory,
                dst_dir_fd=directory,
                follow_symlinks=False,
            )
        except OSError as exc:
            if exc.errno == errno.EEXIST:
                raise _error("loan-quality sweep destination already exists") from exc
            raise
        os.fsync(directory)
        os.unlink(temporary_name, dir_fd=directory)
        temporary_created = False
        os.fsync(directory)
    finally:
        if temporary_created:
            try:
                os.unlink(temporary_name, dir_fd=directory)
                os.fsync(directory)
            except FileNotFoundError:
                pass
        os.close(directory)


def run_family_first_loan_quality_140_filing_schema_sweep_v1(
    project_root: Path, *, command: str
) -> dict[str, Any]:
    if command not in {"build", "verify"}:
        raise _error("loan-quality sweep command drifted")
    root = project_root.resolve()
    output = root / OUTPUT_PATH
    if command == "build" and output.exists():
        raise _error("loan-quality sweep destination already exists")
    persisted = _strict_result(output) if command == "verify" else None
    capability = store_v1.authenticate_family_first_document_evidence_store_v1(root)
    result = build_authenticated_family_first_loan_quality_140_filing_schema_sweep_v1(
        capability, root
    )
    if command == "build":
        _write_exclusive(output, canonical_json_bytes_v1(result) + b"\n")
    elif not same_typed_json_v1(persisted, result):
        raise _error("persisted loan-quality sweep differs from live exact replay")
    return {
        "metrics": result["metrics"],
        "output_path": OUTPUT_PATH.as_posix(),
        "sweep_id": result["sweep_id"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    args = parser.parse_args()
    print(
        json.dumps(
            run_family_first_loan_quality_140_filing_schema_sweep_v1(
                PROJECT_ROOT, command=args.command
            ),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
