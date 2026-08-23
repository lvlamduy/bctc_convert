"""Bind one loan-maturity numeric conflict to independent full-page consensus.

The base graph and both raw OCR surfaces are immutable evidence.  This overlay
admits a different selected value only when two stateless hosted Gemma reads
agree with the bound VietOCR crop and exact accounting equations close.  The
tracked raw responses are strict-parsed and their metadata, content digest,
selected JSON paths, and extracted surfaces are replayed without storing keys.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import stat
from collections.abc import Mapping, Sequence
from pathlib import Path
from statistics import median
from typing import Any

from PIL import Image

from bctc_ai.evaluation import family_first_authenticated_page_region_v1 as render_v1
from bctc_ai.evaluation.accounting_table_axes_v1 import money_integer_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from scripts.experiments import loan_maturity_variant_graph_v2 as graph_v2

__all__ = [
    "FORMAT_VERSION",
    "LoanMaturityNumericConflictEvidenceV1Error",
    "build_loan_maturity_numeric_conflict_evidence_v1",
    "validate_loan_maturity_hosted_gemma4_challenger_v1",
    "validate_loan_maturity_numeric_conflict_evidence_replay_v1",
    "validate_loan_maturity_numeric_conflict_evidence_v1",
]


FORMAT_VERSION = "LOAN_MATURITY_NUMERIC_CONFLICT_EVIDENCE_V1"
CHALLENGER_FORMAT_VERSION = (
    "FAMILY_FIRST_LOAN_MATURITY_HOSTED_GEMMA4_NUMERIC_CHALLENGER_EVALUATION_V1"
)
CLAIM_BOUNDARY = (
    "ONE_AUTHENTICATED_PPOCRV6_VIETOCR_MATURITY_CELL_CONFLICT_RESOLVED_ONLY_"
    "BY_TWO_STATELESS_HOSTED_GEMMA4_FULL_PAGE_CONSENSUS_READS_AND_EXACT_CORE_"
    "PLUS_GRAND_ACCOUNTING_CLOSURE_RAW_SURFACES_PRESERVED_NO_SOLE_MODEL_"
    "SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "accounting_is_final_corroboration_and_veto": True,
    "gemma4_is_sole_numeric_authority": False,
    "hosted_response_bytes_replayable_from_artifact": True,
    "mapping_authority": False,
    "original_ppocrv6_and_vietocr_surfaces_overwritten": False,
    "same_authenticated_crop_and_full_page_required": True,
    "schema_authority": False,
    "two_stateless_hosted_consensus_reads_required": True,
}
_FIELDS = {
    "accounting_checks",
    "authority",
    "base_result_id",
    "challenge_evaluation_id",
    "claim_boundary",
    "family_id",
    "format_version",
    "margin",
    "period_axis",
    "result_id",
    "rows",
    "source_totals",
    "status",
    "target_resolution",
}
_EXPECTED_DECISION = {
    "accounting_is_final_corroboration_and_veto": True,
    "both_hosted_responses_agree_exactly": True,
    "fresh_request_count": 2,
    "gemma4_may_act_as_sole_numeric_reader": False,
    "hosted_requests_are_stateless": True,
    "ppocrv6_and_vietocr_raw_surfaces_overwritten": False,
}
_EXPECTED_CHALLENGER_AUTHORITY = {
    "accounting_authority": False,
    "canonicalization_authority": False,
    "exact_full_page_and_crop_binding_required": True,
    "export_authority": False,
    "geometry_authority": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "persisted_raw_api_response_bytes_authenticated": True,
    "schema_authority": False,
    "strict_raw_api_json_metadata_and_selected_paths_replayed": True,
}


class LoanMaturityNumericConflictEvidenceV1Error(ValueError):
    """The challenge, authenticated evidence, or exact closure drifted."""


def _error(message: str) -> LoanMaturityNumericConflictEvidenceV1Error:
    return LoanMaturityNumericConflictEvidenceV1Error(message)


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise _error(f"{label} integer drifted")
    return value


def _digest(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise _error(f"{label} digest drifted")
    return value


def _strict_ref(value: Any, label: str, *, extended: bool = False) -> dict[str, Any]:
    required = {"path", "sha256", "size_bytes"}
    if extended:
        required |= {"pixel_height", "pixel_width", "renderer_target_dpi"}
    if type(value) is not dict or set(value) != required:
        raise _error(f"{label} reference fields drifted")
    if type(value["path"]) is not str or not value["path"]:
        raise _error(f"{label} reference path drifted")
    relative = Path(value["path"])
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise _error(f"{label} reference path is not rooted-relative")
    _digest(value["sha256"], label)
    _integer(value["size_bytes"], label, minimum=1)
    if extended:
        _integer(value["renderer_target_dpi"], label, minimum=1)
        _integer(value["pixel_height"], label, minimum=1)
        _integer(value["pixel_width"], label, minimum=1)
    return canonical_clone_v1(value)


def _stable_rooted_bytes(root: Path, reference: Mapping[str, Any]) -> bytes:
    relative = Path(reference["path"])
    descriptors: list[int] = []
    try:
        current = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        descriptors.append(current)
        for part in relative.parts[:-1]:
            current = os.open(
                part,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=current,
            )
            descriptors.append(current)
        leaf = os.open(relative.parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=current)
        descriptors.append(leaf)
        before = os.fstat(leaf)
        if not stat.S_ISREG(before.st_mode):
            raise _error("challenger evidence is not one regular file")
        chunks = []
        while chunk := os.read(leaf, 1024 * 1024):
            chunks.append(chunk)
        payload = b"".join(chunks)
        after = os.fstat(leaf)
    except OSError as exc:
        raise _error("cannot read challenger evidence through rooted nofollow path") from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
    identity = lambda item: (  # noqa: E731
        item.st_dev,
        item.st_ino,
        item.st_mode,
        item.st_size,
        item.st_mtime_ns,
    )
    if identity(before) != identity(after):
        raise _error("challenger evidence changed during read")
    if (
        len(payload) != reference["size_bytes"]
        or hashlib.sha256(payload).hexdigest() != reference["sha256"]
    ):
        raise _error("challenger evidence bytes differ from their reference")
    return payload


def _observation(value: Any, label: str, *, total: bool) -> dict[str, Any]:
    common = {
        "crop_ref",
        "hosted_gemma4_consensus_surface",
        "lane_index",
        "lane_type",
        "period_role",
        "ppocrv6_original_score",
        "ppocrv6_original_surface",
        "role",
        "sample_id",
        "selected_surface",
        "selected_value",
        "source_bbox_cached_200dpi",
        "source_line_index",
        "vietocr_transformer_surface",
    }
    expected = common | ({"hosted_json_paths"} if total else {"hosted_json_path"})
    if type(value) is not dict or set(value) != expected:
        raise _error(f"{label} observation fields drifted")
    if (
        type(value["sample_id"]) is not str
        or not value["sample_id"]
        or type(value["role"]) is not str
        or not value["role"]
        or value["lane_type"] != "MONEY"
        or value["period_role"] != "COMPARATIVE"
        or type(value["ppocrv6_original_score"]) is not float
        or not 0 <= value["ppocrv6_original_score"] <= 1
        or type(value["source_bbox_cached_200dpi"]) is not list
        or len(value["source_bbox_cached_200dpi"]) != 4
        or any(type(item) is not int or item < 0 for item in value["source_bbox_cached_200dpi"])
    ):
        raise _error(f"{label} observation identity drifted")
    _integer(value["source_line_index"], label)
    _integer(value["lane_index"], label)
    _integer(value["selected_value"], label)
    _strict_ref(value["crop_ref"], f"{label} crop")
    if money_integer_v1(value["selected_surface"]) != value["selected_value"]:
        raise _error(f"{label} selected surface/value drifted")
    paths = value["hosted_json_paths"] if total else [value["hosted_json_path"]]
    if (
        type(paths) is not list
        or not paths
        or any(type(path) is not str or not path.startswith("/") for path in paths)
    ):
        raise _error(f"{label} hosted JSON path drifted")
    return canonical_clone_v1(value)


def _printed_control_cell(value: Any) -> dict[str, Any]:
    fields = {
        "crop_ref",
        "lane_index",
        "lane_type",
        "period_role",
        "ppocrv6_original_score",
        "role",
        "sample_id",
        "source_bbox_cached_200dpi",
        "source_line_index",
        "surface",
        "value",
        "vietocr_transformer_surface",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error("printed accounting control fields drifted")
    if (
        value["role"] not in {"CORE_TOTAL", "GRAND_TOTAL"}
        or value["lane_index"] not in {0, 1}
        or value["lane_type"] != "MONEY"
        or value["period_role"] != ("CURRENT" if value["lane_index"] == 0 else "COMPARATIVE")
        or type(value["sample_id"]) is not str
        or not value["sample_id"]
        or type(value["ppocrv6_original_score"]) is not float
        or not 0 <= value["ppocrv6_original_score"] <= 1
        or type(value["vietocr_transformer_surface"]) is not str
        or not value["vietocr_transformer_surface"]
        or type(value["source_bbox_cached_200dpi"]) is not list
        or len(value["source_bbox_cached_200dpi"]) != 4
        or any(type(item) is not int or item < 0 for item in value["source_bbox_cached_200dpi"])
    ):
        raise _error("printed accounting control identity drifted")
    _integer(value["source_line_index"], "printed accounting control")
    _integer(value["value"], "printed accounting control")
    _strict_ref(value["crop_ref"], "printed accounting control crop")
    if money_integer_v1(value["surface"]) != value["value"]:
        raise _error("printed accounting control surface/value drifted")
    return canonical_clone_v1(value)


def _document_packet_binding(value: Any) -> dict[str, Any]:
    fields = {"document_evidence_root_sha256", "packet_id"}
    if type(value) is not dict or set(value) != fields:
        raise _error("authenticated document packet binding fields drifted")
    _digest(value["document_evidence_root_sha256"], "document evidence root")
    if type(value["packet_id"]) is not str or not value["packet_id"].startswith(
        "ffdesv1:document:"
    ):
        raise _error("authenticated document packet identity drifted")
    return canonical_clone_v1(value)


def _json_path_value(value: Any, path: str) -> Any:
    if type(path) is not str or not path.startswith("/"):
        raise _error("hosted JSON path is not one absolute path")
    current = value
    for segment in path[1:].split("/"):
        if type(current) is list:
            try:
                index = int(segment)
            except ValueError as exc:
                raise _error("hosted JSON list path segment drifted") from exc
            if index < 0 or index >= len(current):
                raise _error("hosted JSON list path is out of range")
            current = current[index]
        elif type(current) is dict and segment in current:
            current = current[segment]
        else:
            raise _error("hosted JSON object path does not exist")
    return current


def _strict_json_loads(payload: str | bytes, label: str) -> Any:
    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, item in pairs:
            if key in result:
                raise _error(f"{label} contains a duplicate object key")
            result[key] = item
        return result

    def reject_constant(value: str) -> None:
        raise _error(f"{label} contains non-finite JSON number {value}")

    try:
        return json.loads(
            payload,
            object_pairs_hook=object_pairs,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"{label} is not strict JSON") from exc


def _validate_raw_hosted_response(
    payload: bytes,
    request: Mapping[str, Any],
    target: Mapping[str, Any],
    control: Mapping[str, Any],
) -> None:
    raw = _strict_json_loads(payload, "persisted hosted response")
    if type(raw) is not dict or set(raw) != {
        "candidates",
        "modelVersion",
        "responseId",
        "usageMetadata",
    }:
        raise _error("persisted hosted response fields drifted")
    candidates = raw["candidates"]
    if type(candidates) is not list or len(candidates) != 1:
        raise _error("persisted hosted response candidate count drifted")
    candidate = candidates[0]
    if (
        type(candidate) is not dict
        or set(candidate) != {"content", "finishReason", "index"}
        or candidate["index"] != 0
        or candidate["finishReason"] != request["finish_reason"]
    ):
        raise _error("persisted hosted response candidate metadata drifted")
    content = candidate["content"]
    if (
        type(content) is not dict
        or set(content) != {"parts", "role"}
        or content["role"] != "model"
        or type(content["parts"]) is not list
        or len(content["parts"]) != 2
        or content["parts"][0] != {"text": "", "thought": True}
        or type(content["parts"][1]) is not dict
        or set(content["parts"][1]) != {"text"}
        or type(content["parts"][1]["text"]) is not str
    ):
        raise _error("persisted hosted response content envelope drifted")
    text_bytes = content["parts"][1]["text"].encode()
    if (
        len(text_bytes) != request["response_content_ref"]["size_bytes"]
        or hashlib.sha256(text_bytes).hexdigest() != request["response_content_ref"]["sha256"]
    ):
        raise _error("persisted hosted response content digest drifted")
    extracted = _strict_json_loads(content["parts"][1]["text"], "persisted hosted response content")
    target_value = _json_path_value(extracted, target["hosted_json_path"])
    total_values = [_json_path_value(extracted, path) for path in control["hosted_json_paths"]]
    if target_value != target["hosted_gemma4_consensus_surface"] or any(
        value != control["hosted_gemma4_consensus_surface"] for value in total_values
    ):
        raise _error("persisted hosted response selected JSON values drifted")
    usage = raw["usageMetadata"]
    if usage != {
        "candidatesTokenCount": request["candidates_token_count"],
        "promptTokenCount": request["prompt_token_count"],
        "promptTokensDetails": [
            {"modality": item["modality"], "tokenCount": item["token_count"]}
            for item in request["prompt_token_details"]
        ],
        "serviceTier": request["service_tier"],
        "totalTokenCount": request["total_token_count"],
    }:
        raise _error("persisted hosted response token/service metadata drifted")
    if (
        raw["modelVersion"] != request["model_version"]
        or raw["responseId"] != request["response_id"]
    ):
        raise _error("persisted hosted response model/response identity drifted")


def validate_loan_maturity_hosted_gemma4_challenger_v1(
    value: Any,
    project_root: Path | None = None,
    document_packet: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate E-0170's typed identity and live page/crop bytes when supplied."""

    fields = {
        "accounting_effect",
        "authority",
        "claim_boundary",
        "decision",
        "document",
        "evaluation_id",
        "format_version",
        "metrics",
        "model",
        "prompt",
        "requests",
        "state",
        "target_observation",
        "total_control_observation",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error("hosted maturity challenger fields drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("evaluation_id")
    if (
        value["format_version"] != CHALLENGER_FORMAT_VERSION
        or value["state"] != "COMPLETE"
        or type(identity) is not str
        or identity != "maturitygemma4v1:evaluation:" + canonical_json_sha256_v1(material)
        or value["decision"] != _EXPECTED_DECISION
        or value["authority"] != _EXPECTED_CHALLENGER_AUTHORITY
    ):
        raise _error("hosted maturity challenger identity/authority drifted")
    prompt = value["prompt"]
    if (
        type(prompt) is not dict
        or set(prompt) != {"sha256", "text"}
        or type(prompt["text"]) is not str
        or hashlib.sha256(prompt["text"].encode()).hexdigest() != prompt["sha256"]
    ):
        raise _error("hosted maturity challenger prompt drifted")
    model = value["model"]
    if model != {
        "max_output_tokens": 32768,
        "name": "gemma-4-26b-a4b-it",
        "temperature": 0,
        "thinking_level": "MINIMAL",
    }:
        raise _error("hosted maturity challenger model contract drifted")
    document = value["document"]
    if (
        type(document) is not dict
        or set(document)
        != {
            "document_id",
            "document_ordinal",
            "authenticated_store_packet_binding",
            "full_page_render_ref",
            "physical_page",
            "source_pdf_ref",
        }
        or type(document["document_id"]) is not str
        or not document["document_id"]
    ):
        raise _error("hosted maturity challenger document drifted")
    _integer(document["document_ordinal"], "challenger document", minimum=1)
    _integer(document["physical_page"], "challenger page", minimum=1)
    packet_binding = _document_packet_binding(document["authenticated_store_packet_binding"])
    source_ref = _strict_ref(document["source_pdf_ref"], "challenger source PDF")
    render_ref = _strict_ref(
        document["full_page_render_ref"], "challenger full page", extended=True
    )
    target = _observation(value["target_observation"], "target", total=False)
    control = _observation(value["total_control_observation"], "total control", total=True)
    if (
        target["role"] != "MEDIUM_TERM"
        or target["lane_index"] != 1
        or target["selected_surface"] != target["vietocr_transformer_surface"]
        or target["selected_surface"] != target["hosted_gemma4_consensus_surface"]
        or target["selected_surface"] == target["ppocrv6_original_surface"]
        or control["role"] != "CORE_TOTAL"
        or control["lane_index"] != 1
        or control["selected_surface"] != control["ppocrv6_original_surface"]
        or control["selected_surface"] != control["hosted_gemma4_consensus_surface"]
        or control["selected_surface"] == control["vietocr_transformer_surface"]
    ):
        raise _error("hosted maturity challenger consensus roles drifted")
    requests = value["requests"]
    if type(requests) is not list or len(requests) != 2:
        raise _error("hosted maturity challenger request count drifted")
    content_digests = set()
    raw_digests = set()
    for ordinal, request in enumerate(requests, start=1):
        if type(request) is not dict or set(request) != {
            "candidates_token_count",
            "credential_slot",
            "fresh_context",
            "finish_reason",
            "http_status",
            "model_version",
            "prompt_token_details",
            "prompt_token_count",
            "raw_response_ref",
            "request_ordinal",
            "response_id",
            "response_content_ref",
            "service_tier",
            "total_token_count",
        }:
            raise _error("hosted maturity challenger request fields drifted")
        if (
            request["request_ordinal"] != ordinal
            or request["credential_slot"] != ordinal
            or request["fresh_context"] is not True
            or request["http_status"] != 200
            or request["model_version"] != model["name"]
            or request["finish_reason"] != "STOP"
            or request["service_tier"] != "standard"
            or type(request["response_id"]) is not str
            or not request["response_id"]
            or request["prompt_token_details"]
            != [
                {"modality": "TEXT", "token_count": 88},
                {"modality": "IMAGE", "token_count": 258},
            ]
        ):
            raise _error("hosted maturity challenger request identity drifted")
        for key in ("prompt_token_count", "candidates_token_count", "total_token_count"):
            _integer(request[key], f"challenger {key}", minimum=1)
        for key in ("response_content_ref", "raw_response_ref"):
            reference = request[key]
            if key == "raw_response_ref":
                _strict_ref(reference, "persisted hosted raw response")
            else:
                if type(reference) is not dict or set(reference) != {"sha256", "size_bytes"}:
                    raise _error("hosted response digest reference drifted")
                _digest(reference["sha256"], "hosted response")
                _integer(reference["size_bytes"], "hosted response", minimum=1)
        if (
            request["prompt_token_count"] + request["candidates_token_count"]
            != request["total_token_count"]
        ):
            raise _error("hosted response token equation drifted")
        content_digests.add(request["response_content_ref"]["sha256"])
        raw_digests.add(request["raw_response_ref"]["sha256"])
    if len(content_digests) != 1 or len(raw_digests) != 2:
        raise _error("hosted response consensus/freshness digests drifted")
    if len({request["response_id"] for request in requests}) != 2:
        raise _error("hosted response IDs do not prove fresh requests")
    metrics = value["metrics"]
    if metrics != {
        "challenged_page_count": 1,
        "primary_total_control_cell_count": 1,
        "selected_conflict_cell_count": 1,
        "stateless_request_count": 2,
    }:
        raise _error("hosted maturity challenger metrics drifted")
    effect = value["accounting_effect"]
    if (
        type(effect) is not dict
        or set(effect) != {"checks", "printed_control_cells"}
        or type(effect["checks"]) is not list
        or len(effect["checks"]) != 2
        or type(effect["printed_control_cells"]) is not list
        or len(effect["printed_control_cells"]) != 4
    ):
        raise _error("hosted maturity accounting effect drifted")
    printed = [_printed_control_cell(item) for item in effect["printed_control_cells"]]
    if [(item["role"], item["lane_index"]) for item in printed] != [
        ("CORE_TOTAL", 0),
        ("CORE_TOTAL", 1),
        ("GRAND_TOTAL", 0),
        ("GRAND_TOTAL", 1),
    ]:
        raise _error("hosted maturity printed controls role/lane order drifted")
    for check in effect["checks"]:
        if (
            type(check) is not dict
            or set(check)
            != {
                "component_values",
                "computed_value",
                "name",
                "printed_value",
                "status",
            }
            or type(check["component_values"]) is not list
            or any(type(item) is not int for item in check["component_values"])
            or sum(check["component_values"]) != check["computed_value"]
            or check["computed_value"] != check["printed_value"]
            or check["status"] != "CORROBORATED_EXACT"
        ):
            raise _error("hosted maturity accounting check drifted")
    if project_root is not None:
        root = project_root.resolve()
        source_payload: bytes | None = None
        render_payload: bytes | None = None
        for reference in (
            source_ref,
            render_ref,
            target["crop_ref"],
            control["crop_ref"],
            *(item["crop_ref"] for item in printed),
        ):
            payload = _stable_rooted_bytes(root, reference)
            if reference is source_ref:
                source_payload = payload
            if reference is render_ref:
                render_payload = payload
                try:
                    with Image.open(io.BytesIO(payload)) as image:
                        image.load()
                        actual = (image.format, image.width, image.height)
                except Exception as exc:  # pragma: no cover - Pillow detail varies
                    raise _error("challenger full-page PNG cannot be decoded") from exc
                expected = (
                    "PNG",
                    render_ref["pixel_width"],
                    render_ref["pixel_height"],
                )
                if actual != expected:
                    raise _error("challenger full-page decoded dimensions drifted")
        if source_payload is None or render_payload is None:
            raise _error("challenger source/render bytes were not authenticated")
        replayed_render = render_v1._render_page(
            source_payload,
            physical_page=document["physical_page"],
            dpi=render_ref["renderer_target_dpi"],
        )
        if replayed_render != render_payload:
            raise _error("persisted full-page render is not the pinned PDF page replay")
        for request in requests:
            raw_payload = _stable_rooted_bytes(root, request["raw_response_ref"])
            _validate_raw_hosted_response(raw_payload, request, target, control)
    if document_packet is not None:
        required = {
            "document_evidence_root_sha256",
            "document_id",
            "document_ordinal",
            "packet_id",
            "page_count",
            "source_pdf_ref",
        }
        if not required <= set(document_packet):
            raise _error("authenticated document packet is incomplete")
        if (
            document_packet["document_ordinal"] != document["document_ordinal"]
            or document_packet["document_id"] != document["document_id"]
            or document_packet["page_count"] < document["physical_page"]
            or not same_typed_json_v1(document_packet["source_pdf_ref"], source_ref)
            or document_packet["packet_id"] != packet_binding["packet_id"]
            or document_packet["document_evidence_root_sha256"]
            != packet_binding["document_evidence_root_sha256"]
        ):
            raise _error("challenger does not bind the authenticated document packet")
    return canonical_clone_v1(value)


def _joined_line(
    pages: Sequence[Mapping[str, Any]], sample_id: str
) -> tuple[int, Mapping[str, Any]]:
    matches = [
        (page.get("page_sequence"), line)
        for page in pages
        for line in page.get("lines", [])
        if line.get("sample_id") == sample_id
    ]
    if len(matches) != 1 or type(matches[0][0]) is not int:
        raise _error("challenger sample is not unique in joined evidence")
    return matches[0]


def _bind_observation(
    pages: Sequence[Mapping[str, Any]],
    observation: Mapping[str, Any],
    *,
    physical_page: int,
) -> Mapping[str, Any]:
    page_sequence, line = _joined_line(pages, observation["sample_id"])
    numeric = line.get("numeric_recognition")
    if (
        page_sequence != physical_page
        or line.get("line_ordinal") != observation["source_line_index"]
        or line.get("bbox") != observation["source_bbox_cached_200dpi"]
        or not same_typed_json_v1(line.get("crop_ref"), observation["crop_ref"])
        or line.get("vietocr_text") != observation["vietocr_transformer_surface"]
        or type(numeric) is not dict
        or numeric.get("raw_prediction") != observation["ppocrv6_original_surface"]
        or numeric.get("reader_score") != observation["ppocrv6_original_score"]
    ):
        raise _error("challenger observation differs from joined authenticated evidence")
    return line


def _bind_printed_control(
    pages: Sequence[Mapping[str, Any]],
    control: Mapping[str, Any],
    *,
    physical_page: int,
) -> Mapping[str, Any]:
    page_sequence, line = _joined_line(pages, control["sample_id"])
    numeric = line.get("numeric_recognition")
    if (
        page_sequence != physical_page
        or line.get("line_ordinal") != control["source_line_index"]
        or line.get("bbox") != control["source_bbox_cached_200dpi"]
        or not same_typed_json_v1(line.get("crop_ref"), control["crop_ref"])
        or line.get("vietocr_text") != control["vietocr_transformer_surface"]
        or type(numeric) is not dict
        or numeric.get("raw_prediction") != control["surface"]
        or numeric.get("reader_score") != control["ppocrv6_original_score"]
        or money_integer_v1(control["surface"]) != control["value"]
    ):
        raise _error("printed accounting control differs from joined evidence")
    return line


def _center_x(bbox: Sequence[int]) -> float:
    return (bbox[0] + bbox[2]) / 2


def _center_y(bbox: Sequence[int]) -> float:
    return (bbox[1] + bbox[3]) / 2


def _bind_controls_to_graph_geometry(
    graph: Mapping[str, Any], controls: Sequence[Mapping[str, Any]]
) -> None:
    rows = graph["rows"]
    margin = graph["margin"]
    if (
        [row.get("role") for row in rows] != ["SHORT_TERM", "MEDIUM_TERM", "LONG_TERM"]
        or type(margin) is not dict
        or any(len(row.get("values", [])) != 2 for row in rows)
        or len(margin.get("values", [])) != 2
    ):
        raise _error("challenged graph lacks the exact two-lane core/margin geometry")
    graph_cells = [cell for row in rows for cell in row["values"]] + list(margin["values"])
    lane_centers = []
    for lane in (0, 1):
        cells = [cell for cell in graph_cells if cell.get("lane_index") == lane]
        if len(cells) != 4:
            raise _error("challenged graph lane geometry is incomplete")
        lane_centers.append(median(_center_x(cell["bbox"]) for cell in cells))
    spacing = lane_centers[1] - lane_centers[0]
    if spacing <= 0:
        raise _error("challenged graph money lanes are not ordered")
    for control in controls:
        center = _center_x(control["source_bbox_cached_200dpi"])
        distances = [abs(center - expected) for expected in lane_centers]
        if distances[control["lane_index"]] > max(12, spacing * 0.22) or distances[
            control["lane_index"]
        ] != min(distances):
            raise _error("printed total is outside its authenticated money lane")
    by_role = {
        role: [item for item in controls if item["role"] == role]
        for role in ("CORE_TOTAL", "GRAND_TOTAL")
    }
    for role, items in by_role.items():
        if [item["lane_index"] for item in items] != [0, 1]:
            raise _error(f"{role} does not bind exactly both money lanes")
        if (
            abs(
                _center_y(items[0]["source_bbox_cached_200dpi"])
                - _center_y(items[1]["source_bbox_cached_200dpi"])
            )
            > 20
        ):
            raise _error(f"{role} controls are not one physical table row")
    component_end_y = max(_center_y(cell["bbox"]) for row in rows for cell in row["values"])
    core_y = median(_center_y(item["source_bbox_cached_200dpi"]) for item in by_role["CORE_TOTAL"])
    margin_y = median(_center_y(cell["bbox"]) for cell in margin["values"])
    grand_y = median(
        _center_y(item["source_bbox_cached_200dpi"]) for item in by_role["GRAND_TOTAL"]
    )
    if not component_end_y < core_y < margin_y < grand_y:
        raise _error("printed totals do not preserve geometric core/margin/grand order")


def _selected_cell(cell: Mapping[str, Any], challenge: Mapping[str, Any]) -> dict[str, Any]:
    target = challenge["target_observation"]
    is_target = cell["source_line_index"] == target["source_line_index"]
    selected = target["selected_surface"] if is_target else cell["surface"]
    value = money_integer_v1(selected)
    if value is None:
        raise _error("maturity resolved cell is not one authoritative money value")
    return {
        "bbox": canonical_clone_v1(cell["bbox"]),
        "lane_index": cell["lane_index"],
        "lane_type": cell["lane_type"],
        "ppocrv6_surface": cell["surface"],
        "selected_surface": selected,
        "selected_value": value,
        "selection_mode": (
            "PIXEL_VIETOCR_TWO_HOSTED_GEMMA4_CONSENSUS_PLUS_EXACT_ACCOUNTING"
            if is_target
            else "BOUND_PPOCRV6_PRIMARY"
        ),
        "source_line_index": cell["source_line_index"],
        "vietocr_transformer_surface": cell["semantic_surface"],
    }


def _result_shape(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["family_id"] != graph_v2.FAMILY_ID
        or value["status"] != "NUMERIC_EXACT_WITH_TWO_HOSTED_GEMMA4_CONSENSUS_RESCUE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["rows"]) is not list
        or type(value["source_totals"]) is not list
        or type(value["accounting_checks"]) is not list
    ):
        raise _error("maturity conflict-evidence result shape drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "lmncerv1:result:" + canonical_json_sha256_v1(material):
        raise _error("maturity conflict-evidence result identity drifted")
    return canonical_clone_v1(value)


def build_loan_maturity_numeric_conflict_evidence_v1(
    base: Any,
    joined_pages: Sequence[Mapping[str, Any]],
    challenge: Any,
    project_root: Path,
    *,
    document_packet: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve the one bound conflict without mutating either raw OCR surface."""

    graph_v2.validate_loan_maturity_variant_graph_document_v2(base)
    challenger = validate_loan_maturity_hosted_gemma4_challenger_v1(
        challenge, project_root, document_packet
    )
    if (
        base["status"] != "UNRESOLVED"
        or len(base["graphs"]) != 1
        or base["graphs"][0]["unresolved_reasons"]
        != ["CORE_PLUS_MARGIN_GRAND_TOTAL_NOT_CORROBORATED"]
    ):
        raise _error("maturity conflict rescue requires the one expected base veto")
    graph = base["graphs"][0]
    document = challenger["document"]
    target = challenger["target_observation"]
    control = challenger["total_control_observation"]
    _bind_observation(joined_pages, target, physical_page=document["physical_page"])
    _bind_observation(joined_pages, control, physical_page=document["physical_page"])
    target_cells = [
        cell
        for row in graph["rows"]
        if row["role"] == target["role"]
        for cell in row["values"]
        if cell["lane_index"] == target["lane_index"]
        and cell["source_line_index"] == target["source_line_index"]
    ]
    if len(target_cells) != 1:
        raise _error("challenger target does not bind one maturity role cell")
    target_cell = target_cells[0]
    if (
        target_cell["surface"] != target["ppocrv6_original_surface"]
        or target_cell["semantic_surface"] != target["vietocr_transformer_surface"]
    ):
        raise _error("challenger target raw surfaces differ from the base graph")
    rows = []
    for row in graph["rows"]:
        rows.append(
            {
                "label": canonical_clone_v1(row["label"]),
                "role": row["role"],
                "values": [_selected_cell(cell, challenger) for cell in row["values"]],
            }
        )
    if graph["margin"] is None:
        raise _error("challenged maturity graph lost its margin population")
    margin = {
        key: canonical_clone_v1(value) for key, value in graph["margin"].items() if key != "values"
    }
    margin["values"] = [_selected_cell(cell, challenger) for cell in graph["margin"]["values"]]
    controls = challenger["accounting_effect"]["printed_control_cells"]
    source_totals = []
    for item in controls:
        _bind_printed_control(joined_pages, item, physical_page=document["physical_page"])
        source_totals.append(canonical_clone_v1(item))
    _bind_controls_to_graph_geometry(graph, source_totals)
    row_values = {row["role"]: [cell["selected_value"] for cell in row["values"]] for row in rows}
    margin_values = [cell["selected_value"] for cell in margin["values"]]
    totals = {(item["role"], item["lane_index"]): item["value"] for item in source_totals}
    checks = []
    for lane in range(2):
        core = sum(row_values[role][lane] for role in ("SHORT_TERM", "MEDIUM_TERM", "LONG_TERM"))
        printed_core = totals[("CORE_TOTAL", lane)]
        printed_grand = totals[("GRAND_TOTAL", lane)]
        for name, computed, printed in (
            ("THREE_BUCKET_CORE_EQUALS_PRINTED_CORE_TOTAL", core, printed_core),
            (
                "CORE_PLUS_MARGIN_EQUALS_PRINTED_GRAND_TOTAL",
                core + margin_values[lane],
                printed_grand,
            ),
        ):
            if computed != printed:
                raise _error("challenged maturity accounting closure is not exact")
            checks.append(
                {
                    "computed_value": computed,
                    "lane_index": lane,
                    "name": name,
                    "printed_value": printed,
                    "status": "CORROBORATED_EXACT",
                }
            )
    material = {
        "accounting_checks": checks,
        "authority": canonical_clone_v1(_AUTHORITY),
        "base_result_id": base["result_id"],
        "challenge_evaluation_id": challenger["evaluation_id"],
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": graph_v2.FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "margin": margin,
        "period_axis": canonical_clone_v1(graph["period_axis"]),
        "rows": rows,
        "source_totals": source_totals,
        "status": "NUMERIC_EXACT_WITH_TWO_HOSTED_GEMMA4_CONSENSUS_RESCUE",
        "target_resolution": {
            "lane_index": target["lane_index"],
            "ppocrv6_original_surface": target["ppocrv6_original_surface"],
            "role": target["role"],
            "sample_id": target["sample_id"],
            "selected_surface": target["selected_surface"],
            "selected_value": target["selected_value"],
            "vietocr_transformer_surface": target["vietocr_transformer_surface"],
        },
    }
    return _result_shape(
        {**material, "result_id": "lmncerv1:result:" + canonical_json_sha256_v1(material)}
    )


def validate_loan_maturity_numeric_conflict_evidence_v1(value: Any) -> dict[str, Any]:
    """Validate the content identity of one persisted resolution overlay."""

    return _result_shape(value)


def validate_loan_maturity_numeric_conflict_evidence_replay_v1(
    value: Any,
    base: Any,
    joined_pages: Sequence[Mapping[str, Any]],
    challenge: Any,
    project_root: Path,
    *,
    document_packet: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Rebuild the resolution from the same authenticated inputs."""

    persisted = _result_shape(value)
    rebuilt = build_loan_maturity_numeric_conflict_evidence_v1(
        base,
        joined_pages,
        challenge,
        project_root,
        document_packet=document_packet,
    )
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("maturity numeric-conflict evidence does not replay exactly")
    return canonical_clone_v1(rebuilt)
