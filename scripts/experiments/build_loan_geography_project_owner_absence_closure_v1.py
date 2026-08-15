"""Close fixed-report customer-loan geography absences by owner adjudication.

The E-0065 base remains immutable.  Broad total-loan geography tables are
retained exactly as negative controls and are never narrowed into the customer-
loan family.  Bank/page fields are evidence locators, not decision rules.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import stat
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = Path("docs/experiments/E-0067D-loan-geography-project-owner-absence-closure-v1.json")
BASE_RESULT_PATH = Path(
    "docs/experiments/E-0065-loan-geography-8bank-codex-verified-mapping-v1.json"
)
BASE_RESULT_SHA256 = "f043d29ae10164c46835b2e9a2b055124c92511b84149011824aed51aa54b046"
BASE_RESULT_ID = "e0065:result:5b786304eb31399ccff5d1826b2af7b2bf24db0b461335fa40e9107e43610e67"
FORMAT_VERSION = "LOAN_GEOGRAPHY_PROJECT_OWNER_ABSENCE_CLOSURE_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_BOUND_REPORT_PROJECT_OWNER_CLASSIFICATION_OF_EXACT_CUSTOMER_"
    "LOAN_GEOGRAPHY_PRESERVING_BROADER_TOTAL_LOAN_AND_SEGMENT_TABLES_AS_"
    "NEGATIVE_CONTROLS_NO_OTHER_REPORT_ABSENCE_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_ABSENT_ORDER = ("ACB", "VPB", "HDB", "VCB", "CTG", "BID")
_VERIFIED_ORDER = ("MBB", "VIB")
_EXPECTED_REASONS = {
    "ACB": "UNRESOLVED_BROAD_TOTAL_LOANS_SCOPE",
    "VPB": "UNRESOLVED_BROAD_MIXED_LOAN_POPULATION_SCOPE",
    "HDB": "UNRESOLVED_BROAD_TOTAL_LOANS_SCOPE",
    "VCB": "UNRESOLVED_SEGMENT_REPORT_NEGATIVE_CONTROL_NO_LOAN_GEOGRAPHY",
    "CTG": "UNRESOLVED_BROAD_TOTAL_LOANS_SCOPE",
    "BID": "UNRESOLVED_BROAD_TOTAL_LOANS_SCOPE",
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "broader_total_loan_geography_relabelled_or_narrowed": False,
    "canonicalization_or_export_authority": False,
    "confirmed_absence_bounded_to_supplied_reports": True,
    "other_report_or_broad_corpus_absence_authority": False,
    "persisted_result_self_authenticating": False,
    "project_owner_decision_required": True,
    "public_exact_replay_required": True,
    "segment_report_promoted_to_customer_loan_geography": False,
    "source_scope_equations_preserved": True,
}


class LoanGeographyProjectOwnerAbsenceClosureV1Error(ValueError):
    """The base result, exact scope, decision, or identity drifted."""


def _error(message: str) -> LoanGeographyProjectOwnerAbsenceClosureV1Error:
    return LoanGeographyProjectOwnerAbsenceClosureV1Error(message)


def _load_module() -> ModuleType:
    path = (
        PROJECT_ROOT / "scripts/experiments/build_loan_geography_8bank_codex_verified_mapping_v1.py"
    )
    spec = importlib.util.spec_from_file_location(
        "loan_geography_base_for_owner_absence_closure_v1", path
    )
    if spec is None or spec.loader is None:
        raise _error("cannot load exact E-0065 replay dependency")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


base = _load_module()


def _stable_bytes(relative: Path) -> bytes:
    if (
        relative.is_absolute()
        or not relative.parts
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise _error("fixed base path escaped the project root")
    directory_fd = os.open(PROJECT_ROOT, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in relative.parts[:-1]:
            child_fd = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = child_fd
        descriptor = os.open(
            relative.parts[-1],
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=directory_fd,
        )
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise _error("fixed base is not one single-link regular file")
            chunks: list[bytes] = []
            while chunk := os.read(descriptor, 1 << 20):
                chunks.append(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
    finally:
        os.close(directory_fd)
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_nlink,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_nlink,
    ):
        raise _error("fixed base changed while being read")
    return b"".join(chunks)


def _strict_json(payload: bytes) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise _error(f"non-finite JSON constant: {value}")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise _error(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("invalid base JSON") from exc
    if type(value) is not dict:
        raise _error("base JSON root must be one object")
    return value


def _base_result() -> tuple[dict[str, Any], dict[str, Any]]:
    payload = _stable_bytes(BASE_RESULT_PATH)
    if hashlib.sha256(payload).hexdigest() != BASE_RESULT_SHA256:
        raise _error("E-0065 base digest drifted")
    value = _strict_json(payload)
    if value.get("result_id") != BASE_RESULT_ID:
        raise _error("E-0065 base identity drifted")
    replayed = base.validate_loan_geography_8bank_codex_verified_mapping_replay_v1(value)
    return replayed, {
        "path": BASE_RESULT_PATH.as_posix(),
        "result_id": BASE_RESULT_ID,
        "sha256": BASE_RESULT_SHA256,
        "size_bytes": len(payload),
    }


def _build() -> dict[str, Any]:
    replayed, base_ref = _base_result()
    by_bank = {trial["bank_provenance"]: trial for trial in replayed["trials"]}
    if set(by_bank) != set(_ABSENT_ORDER + _VERIFIED_ORDER):
        raise _error("E-0065 bank denominator drifted")
    for bank in _VERIFIED_ORDER:
        trial = by_bank[bank]
        if trial["status"] != "VERIFIED_BY_CODEX" or not trial["verified_mappings"]:
            raise _error(f"verified geography bank drifted: {bank}")

    decisions: list[dict[str, Any]] = []
    for bank in _ABSENT_ORDER:
        trial = by_bank[bank]
        reason = _EXPECTED_REASONS[bank]
        if (
            trial["status"] != "UNRESOLVED"
            or trial["unresolved_reason"] != reason
            or trial["verified_mappings"]
        ):
            raise _error(f"negative geography control drifted: {bank}")
        if bank == "VCB":
            if trial["scope_equations"]:
                raise _error("VCB segment control unexpectedly gained a loan equation")
            source_surface = "GEOGRAPHIC_SEGMENT_REPORT_NOT_CUSTOMER_LOAN_GEOGRAPHY"
        else:
            if (
                len(trial["scope_equations"]) != 1
                or trial["scope_equations"][0].get("relation") != "BROADER"
                or type(trial["scope_equations"][0].get("difference")) is not int
                or trial["scope_equations"][0]["difference"] <= 0
            ):
                raise _error(f"broader-loan population proof drifted: {bank}")
            source_surface = "BROADER_TOTAL_LOAN_GEOGRAPHY_NOT_CUSTOMER_LOAN_GEOGRAPHY"
        decisions.append(
            {
                "bank_provenance": bank,
                "base_unresolved_reason": reason,
                "decision": "NOT_PRESENT_IN_BOUND_REPORT_AS_CUSTOMER_LOAN_GEOGRAPHY",
                "source_scope_equations": canonical_clone_v1(trial["scope_equations"]),
                "source_surface_disposition": source_surface,
                "status": "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT",
                "whole_document_absence_claim": True,
            }
        )

    material = {
        "authority": _AUTHORITY,
        "claim_boundary": CLAIM_BOUNDARY,
        "decisions": decisions,
        "family": {
            "canonical_name": "Phân tích dư nợ cho vay theo khu vực địa lý",
            "report_norm_id": 759,
        },
        "format_version": FORMAT_VERSION,
        "input_ref": base_ref,
        "metrics": {
            "confirmed_absence_count": 6,
            "open_geography_review_count": 0,
            "verified_document_count": 2,
            "verified_mapping_count": 4,
        },
        "state": "PROJECT_OWNER_LOAN_GEOGRAPHY_BOUND_REPORT_ABSENCE_CLOSURE_VERIFIED",
        "verified_present_banks": list(_VERIFIED_ORDER),
    }
    return _validate(
        {**material, "result_id": "e0067d:result:" + canonical_json_sha256_v1(material)}
    )


def _validate(value: Any) -> dict[str, Any]:
    fields = {
        "authority",
        "claim_boundary",
        "decisions",
        "family",
        "format_version",
        "input_ref",
        "metrics",
        "result_id",
        "state",
        "verified_present_banks",
    }
    metrics = {
        "confirmed_absence_count": 6,
        "open_geography_review_count": 0,
        "verified_document_count": 2,
        "verified_mapping_count": 4,
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "PROJECT_OWNER_LOAN_GEOGRAPHY_BOUND_REPORT_ABSENCE_CLOSURE_VERIFIED"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or not same_typed_json_v1(value["metrics"], metrics)
        or not same_typed_json_v1(value["verified_present_banks"], list(_VERIFIED_ORDER))
        or [decision.get("bank_provenance") for decision in value["decisions"]]
        != list(_ABSENT_ORDER)
    ):
        raise _error("geography closure shape, authority, order, or metrics drifted")
    material = canonical_clone_v1(value)
    result_id = material.pop("result_id")
    if result_id != "e0067d:result:" + canonical_json_sha256_v1(material):
        raise _error("geography closure content identity drifted")
    return canonical_clone_v1(value)


def build_live_loan_geography_project_owner_absence_closure_v1() -> dict[str, Any]:
    """Build from the exact E-0065 live replay and owner decision."""

    return _build()


def validate_loan_geography_project_owner_absence_closure_replay_v1(
    value: Any,
) -> dict[str, Any]:
    """Reject a raw/self-rehashed closure unless all live inputs rebuild it."""

    persisted = _validate(value)
    rebuilt = _build()
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("geography closure does not exact-replay")
    return rebuilt


def main() -> None:
    OUTPUT_PATH.write_bytes(
        canonical_json_bytes_v1(build_live_loan_geography_project_owner_absence_closure_v1())
    )


if __name__ == "__main__":
    main()
