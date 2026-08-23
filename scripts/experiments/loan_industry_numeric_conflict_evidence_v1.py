"""Resolve one PP numeric conflict through independent same-crop consensus.

The resolver is bank/page agnostic.  A tracked challenge must bind one existing
sample and crop, preserve the disagreeing PP surface, and show exact agreement
between the visible-pixel transcription, VietOCR proposal and hosted Gemma 4
extraction.  The replacement is admitted only when it makes exactly one
printed total candidate close.  Gemma never acts as sole numeric authority.
"""

from __future__ import annotations

import hashlib
import os
import stat
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))
sys.path.insert(0, os.fspath(PROJECT_ROOT / "src"))

from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from scripts.experiments import (  # noqa: E402
    loan_industry_numeric_row_reconciliation_v1 as numeric_v1,
)
from scripts.experiments.loan_type_numeric_row_reconciliation_v1 import (  # noqa: E402
    _parsed_value,
)

FORMAT_VERSION = "LOAN_INDUSTRY_NUMERIC_CONFLICT_EVIDENCE_V1"
CHALLENGER_FORMAT_VERSION = (
    "FAMILY_FIRST_LOAN_INDUSTRY_HOSTED_GEMMA4_NUMERIC_CHALLENGER_EVALUATION_V1"
)
CLAIM_BOUNDARY = (
    "ONE_AUTHENTICATED_EXISTING_CROP_PPOCRV6_CONFLICT_RESOLVED_ONLY_BY_EXACT_"
    "VISIBLE_PIXEL_VIETOCR_AND_HOSTED_GEMMA4_CONSENSUS_PLUS_UNIQUE_ACCOUNTING_"
    "CLOSURE_NO_SOLE_MODEL_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "accounting_equation_is_final_corroboration_and_veto": True,
    "gemma4_is_sole_numeric_authority": False,
    "mapping_authority": False,
    "original_ppocrv6_observation_overwritten": False,
    "same_authenticated_crop_required": True,
    "schema_authority": False,
    "visible_pixel_vietocr_and_gemma4_exact_agreement_required": True,
}
_FIELDS = {
    "accounting_checks",
    "authority",
    "base_result_id",
    "challenge_evaluation_id",
    "claim_boundary",
    "conflict_resolution",
    "family_id",
    "format_version",
    "graph_result_id",
    "lane_types",
    "page_sequence",
    "result_id",
    "rows",
    "status",
    "total",
    "unmodelled_additive_rows",
}


class LoanIndustryNumericConflictEvidenceV1Error(ValueError):
    """The challenge, authenticated crop, or accounting closure drifted."""


def _error(message: str) -> LoanIndustryNumericConflictEvidenceV1Error:
    return LoanIndustryNumericConflictEvidenceV1Error(message)


def _strict_ref(value: Any, label: str) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != {"path", "sha256", "size_bytes"}
        or type(value["path"]) is not str
        or not value["path"]
        or type(value["sha256"]) is not str
        or len(value["sha256"]) != 64
        or any(character not in "0123456789abcdef" for character in value["sha256"])
        or type(value["size_bytes"]) is not int
        or value["size_bytes"] <= 0
    ):
        raise _error(f"{label} content reference drifted")
    relative = Path(value["path"])
    if (
        relative.is_absolute()
        or not relative.parts
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise _error(f"{label} path drifted")
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
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise _error("numeric-conflict crop is not one single-link regular file")
        chunks = []
        while True:
            chunk = os.read(leaf, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        payload = b"".join(chunks)
        after = os.fstat(leaf)
    except OSError as exc:
        raise _error("cannot read numeric-conflict crop through rooted nofollow path") from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)

    def identity(item: os.stat_result) -> tuple[int, int, int, int, int]:
        return (item.st_dev, item.st_ino, item.st_mode, item.st_size, item.st_mtime_ns)

    if identity(before) != identity(after):
        raise _error("numeric-conflict crop changed during read")
    if (
        len(payload) != reference["size_bytes"]
        or hashlib.sha256(payload).hexdigest() != reference["sha256"]
    ):
        raise _error("numeric-conflict crop bytes differ from their authenticated reference")
    return payload


def validate_loan_industry_hosted_gemma4_challenger_v1(value: Any) -> dict[str, Any]:
    """Validate the tracked, bounded hosted-Gemma observation and identity."""

    if type(value) is not dict or set(value) != {
        "authority",
        "claim_boundary",
        "decision",
        "evaluation_id",
        "format_version",
        "observation",
        "prompt",
        "state",
    }:
        raise _error("hosted Gemma 4 challenge fields drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("evaluation_id")
    if (
        value["format_version"] != CHALLENGER_FORMAT_VERSION
        or value["state"] != "COMPLETE"
        or type(identity) is not str
        or identity != "industrygemma4v1:evaluation:" + canonical_json_sha256_v1(material)
    ):
        raise _error("hosted Gemma 4 challenge identity drifted")
    prompt = value["prompt"]
    observation = value["observation"]
    decision = value["decision"]
    authority = value["authority"]
    if (
        type(prompt) is not dict
        or set(prompt) != {"sha256", "text"}
        or type(prompt["text"]) is not str
        or hashlib.sha256(prompt["text"].encode()).hexdigest() != prompt["sha256"]
        or type(observation) is not dict
        or set(observation)
        != {
            "accounting_effect",
            "crop_ref",
            "extracted_numeric_surface",
            "extraction_json_path",
            "format_version",
            "full_page_render_ref",
            "independent_pixel_transcription",
            "inference",
            "model",
            "ppocrv6_original_score",
            "ppocrv6_original_surface",
            "ppocrv6_repeated_scale_surfaces",
            "prompt_sha256",
            "response_ref",
            "sample_id",
            "state",
            "vietocr_transformer_surface",
        }
        or type(decision) is not dict
        or set(decision)
        != {
            "accounting_equation_is_final_corroboration_and_veto",
            "gemma4_may_act_as_sole_numeric_reader",
            "gemma4_used_only_after_ppocrv6_vietocr_conflict",
            "independent_pixel_vietocr_and_gemma4_agree_exactly",
            "ppocrv6_observation_overwritten",
        }
        or type(authority) is not dict
        or set(authority)
        != {
            "accounting_authority",
            "canonicalization_authority",
            "export_authority",
            "geometry_authority",
            "mapping_authority",
            "numeric_authority",
            "raw_api_response_self_authenticating",
            "schema_authority",
            "tracked_response_digest_and_extracted_surface_only",
        }
    ):
        raise _error("hosted Gemma 4 challenge nested fields drifted")
    crop_ref = _strict_ref(observation["crop_ref"], "hosted Gemma 4 crop")
    consensus = observation["extracted_numeric_surface"]
    ppocr = observation["ppocrv6_original_surface"]
    if (
        observation["format_version"] != "HOSTED_GEMMA4_FULL_PAGE_NUMERIC_CHALLENGER_OBSERVATION_V1"
        or observation["state"] != "COMPLETED_STATELESS_FULL_PAGE_JSON_CHALLENGE"
        or observation["prompt_sha256"] != prompt["sha256"]
        or type(observation["sample_id"]) is not str
        or not observation["sample_id"]
        or type(consensus) is not str
        or _parsed_value(consensus, "MONEY") is None
        or consensus != observation["independent_pixel_transcription"]
        or consensus != observation["vietocr_transformer_surface"]
        or type(ppocr) is not str
        or _parsed_value(ppocr, "MONEY") is None
        or ppocr == consensus
        or type(observation["ppocrv6_original_score"]) is not float
        or not 0 <= observation["ppocrv6_original_score"] <= 1
        or type(observation["ppocrv6_repeated_scale_surfaces"]) is not list
        or not observation["ppocrv6_repeated_scale_surfaces"]
        or any(item != ppocr for item in observation["ppocrv6_repeated_scale_surfaces"])
        or type(observation["extraction_json_path"]) is not list
        or not observation["extraction_json_path"]
        or any(type(item) is not str or not item for item in observation["extraction_json_path"])
        or type(observation["model"]) is not str
        or not observation["model"].startswith("gemma-4-")
        or decision
        != {
            "accounting_equation_is_final_corroboration_and_veto": True,
            "gemma4_may_act_as_sole_numeric_reader": False,
            "gemma4_used_only_after_ppocrv6_vietocr_conflict": True,
            "independent_pixel_vietocr_and_gemma4_agree_exactly": True,
            "ppocrv6_observation_overwritten": False,
        }
        or authority
        != {
            "accounting_authority": False,
            "canonicalization_authority": False,
            "export_authority": False,
            "geometry_authority": False,
            "mapping_authority": False,
            "numeric_authority": False,
            "raw_api_response_self_authenticating": False,
            "schema_authority": False,
            "tracked_response_digest_and_extracted_surface_only": True,
        }
    ):
        raise _error("hosted Gemma 4 challenge consensus/authority drifted")
    if not same_typed_json_v1(crop_ref, observation["crop_ref"]):
        raise _error("hosted Gemma 4 crop reference drifted")
    return canonical_clone_v1(value)


def _validate_shape(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["family_id"] != "LOAN_INDUSTRY_CLASSIFICATION"
        or value["status"] != "NUMERIC_EXACT_WITH_PIXEL_VIETOCR_GEMMA4_CONSENSUS_RESCUE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["rows"]) is not list
        or type(value["unmodelled_additive_rows"]) is not list
        or type(value["lane_types"]) is not list
        or type(value["total"]) is not list
        or type(value["accounting_checks"]) is not list
        or type(value["page_sequence"]) is not int
        or value["page_sequence"] <= 0
        or type(value["conflict_resolution"]) is not dict
    ):
        raise _error("loan-industry numeric-conflict result fields drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "lincerv1:result:" + canonical_json_sha256_v1(material):
        raise _error("loan-industry numeric-conflict result identity drifted")
    return canonical_clone_v1(value)


def build_loan_industry_numeric_conflict_evidence_v1(
    base: Any,
    joined_pages: Sequence[Mapping[str, Any]],
    challenge: Any,
    project_root: Path,
) -> dict[str, Any]:
    """Apply one content-addressed conflict challenge and require unique closure."""

    persisted_base = numeric_v1._validate_shape(base)
    challenger = validate_loan_industry_hosted_gemma4_challenger_v1(challenge)
    observation = challenger["observation"]
    root = project_root.resolve()
    crop_ref = _strict_ref(observation["crop_ref"], "numeric-conflict crop")
    _stable_rooted_bytes(root, crop_ref)
    candidates = [
        (page["page_sequence"], line)
        for page in joined_pages
        for line in page["lines"]
        if line.get("sample_id") == observation["sample_id"]
    ]
    if len(candidates) != 1:
        raise _error("numeric-conflict sample is not unique in the authenticated document")
    page_sequence, source_line = candidates[0]
    if (
        page_sequence != persisted_base["page_sequence"]
        or not same_typed_json_v1(source_line.get("crop_ref"), crop_ref)
        or source_line.get("vietocr_text") != observation["vietocr_transformer_surface"]
        or source_line.get("numeric_recognition", {}).get("raw_prediction")
        != observation["ppocrv6_original_surface"]
        or source_line.get("numeric_recognition", {}).get("reader_score")
        != observation["ppocrv6_original_score"]
    ):
        raise _error("numeric-conflict challenge belongs to another authenticated source cell")
    rows = canonical_clone_v1(persisted_base["rows"])
    additive = canonical_clone_v1(persisted_base["unmodelled_additive_rows"])
    matches = []
    for row in (*rows, *additive):
        for cell in row["cells"]:
            if cell["source_line_index"] == source_line["line_ordinal"]:
                matches.append((row, cell))
    if len(matches) != 1:
        raise _error("numeric-conflict source line does not identify exactly one additive cell")
    row, cell = matches[0]
    if (
        cell["lane_type"] != "MONEY"
        or cell["ppocrv6_surface"] != observation["ppocrv6_original_surface"]
        or cell["semantic_surface"] != observation["vietocr_transformer_surface"]
    ):
        raise _error("numeric-conflict base cell differs from the challenge")
    previous = canonical_clone_v1(cell)
    cell["parsed_value"] = _parsed_value(observation["extracted_numeric_surface"], "MONEY")
    cell["status"] = "PIXEL_VIETOCR_GEMMA4_CONSENSUS_NUMERIC_RESCUE"
    printed_candidates = [
        persisted_base["total"],
        *(item["cells"] for item in persisted_base["intermediate_subtotals"]),
    ]
    evaluations = [
        (candidate, numeric_v1._checks(rows, additive, candidate, persisted_base["lane_types"]))
        for candidate in printed_candidates
    ]
    exact = [
        (candidate, checks)
        for candidate, checks in evaluations
        if checks and all(item["status"] == "EXACT_PP_NUMERIC_EQUATION" for item in checks)
    ]
    if len(exact) != 1:
        raise _error("numeric-conflict consensus does not select one exact printed total")
    total, accounting_checks = exact[0]
    conflict = {
        "crop_ref": crop_ref,
        "gemma4_surface": observation["extracted_numeric_surface"],
        "independent_pixel_surface": observation["independent_pixel_transcription"],
        "lane_index": cell["lane_index"],
        "new_cell": canonical_clone_v1(cell),
        "previous_cell": previous,
        "role": row["role"],
        "sample_id": observation["sample_id"],
        "source_line_index": source_line["line_ordinal"],
        "vietocr_surface": observation["vietocr_transformer_surface"],
    }
    material = {
        "accounting_checks": accounting_checks,
        "authority": canonical_clone_v1(_AUTHORITY),
        "base_result_id": persisted_base["result_id"],
        "challenge_evaluation_id": challenger["evaluation_id"],
        "claim_boundary": CLAIM_BOUNDARY,
        "conflict_resolution": conflict,
        "family_id": persisted_base["family_id"],
        "format_version": FORMAT_VERSION,
        "graph_result_id": persisted_base["graph_result_id"],
        "lane_types": canonical_clone_v1(persisted_base["lane_types"]),
        "page_sequence": page_sequence,
        "rows": rows,
        "status": "NUMERIC_EXACT_WITH_PIXEL_VIETOCR_GEMMA4_CONSENSUS_RESCUE",
        "total": canonical_clone_v1(total),
        "unmodelled_additive_rows": additive,
    }
    return _validate_shape(
        {**material, "result_id": "lincerv1:result:" + canonical_json_sha256_v1(material)}
    )


def validate_loan_industry_numeric_conflict_evidence_replay_v1(
    value: Any,
    base: Any,
    joined_pages: Sequence[Mapping[str, Any]],
    challenge: Any,
    project_root: Path,
) -> dict[str, Any]:
    expected = build_loan_industry_numeric_conflict_evidence_v1(
        base, joined_pages, challenge, project_root
    )
    if not same_typed_json_v1(value, expected):
        raise _error("loan-industry numeric-conflict evidence does not replay exactly")
    return expected
