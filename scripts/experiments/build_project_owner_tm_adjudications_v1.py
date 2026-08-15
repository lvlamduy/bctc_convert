"""Apply bounded project-owner TM adjudications without rewriting prior results."""

from __future__ import annotations

import hashlib
import json
import math
import os
import stat
from pathlib import Path
from typing import Any

from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import _authority_snapshot
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = Path("docs/experiments/E-0067A-project-owner-tm-adjudications-v1.json")
FORMAT_VERSION = "PROJECT_OWNER_TM_ADJUDICATIONS_V1"
CLAIM_BOUNDARY = (
    "BOUNDED_PROJECT_OWNER_DECISIONS_OVER_PINNED_E0061_E0062_E0063_E0067_"
    "RESULTS_AND_LIVE_TM_SCHEMA_NO_BANK_ROUTING_OR_UNRELATED_MAPPING_AUTHORITY"
)

_INPUTS = {
    "central_bank_deposits": (
        Path("docs/experiments/E-0061-central-bank-deposits-8bank-codex-verified-mapping-v1.json"),
        "893b37d933c24dc99fcf56ca1fe36992f1a37f809e1af36f37ae02b066cf1cea",
        "cbd8bcv1:result:62adc9eddef7e397c39314b5324df196e3103e2dbd3fc315763ef4b57ed778a3",
    ),
    "derivatives": (
        Path(
            "docs/experiments/E-0063-derivative-financial-instruments-8bank-codex-verified-mapping-v1.json"
        ),
        "084b0f1ba39867c475f6ee1ee9209e6de1c4404c60ce747a273ac79a86214565",
        "dfi8bcv1:result:2270d8928cdfca4586a740c9fdc781b88492cc9901908369e8ea58b9940eae50",
    ),
    "interbank": (
        Path(
            "docs/experiments/E-0062-interbank-deposits-loans-8bank-codex-verified-mapping-v1.json"
        ),
        "6159ed0178e2b700e471ac06700a1edf8a710c3827c5d01f10314e6b3b3faa18",
        "idl8bcv1:result:9da7002e43379477609752664b59f8466d6a987a533153176f13689ff6de28da",
    ),
    "investment_securities": (
        Path("docs/experiments/E-0067-investment-securities-8bank-codex-verified-mapping-v1.json"),
        "4ee4d7df67320537eeb6be72be7f1f365a5b7086d1be2fd72fc11e07f29760d2",
        "e0067:result:ba8a22afd96879f4cf44c5430cb880ce7f267ad83dc2a23f55c7b5c905ef1176",
    ),
}

_AUTHORITY = {
    "bank_page_or_filename_used_as_mapping_rule": False,
    "central_bank_other_deposit_mapping_authority": True,
    "confirmed_absence_bounded_to_supplied_reports": True,
    "derivative_absence_authority": True,
    "interbank_absence_authority": True,
    "investment_hierarchy_confirmation_authority": True,
    "other_family_mapping_authority": False,
    "persisted_artifact_self_authenticating": False,
    "project_owner_decisions_required": True,
    "public_exact_replay_required": True,
}


class ProjectOwnerTMAdjudicationsV1Error(ValueError):
    """A pinned result, exact decision, or live schema binding drifted."""


def _error(message: str) -> ProjectOwnerTMAdjudicationsV1Error:
    return ProjectOwnerTMAdjudicationsV1Error(message)


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise _error(f"non-finite JSON constant in {label}: {value}")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise _error(f"duplicate JSON key in {label}: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"invalid UTF-8 JSON: {label}") from exc
    if type(value) is not dict:
        raise _error(f"JSON root must be one object: {label}")
    return value


def _stable_bytes(relative: Path) -> bytes:
    if relative.is_absolute() or ".." in relative.parts:
        raise _error("fixed adjudication input path escaped project root")
    path = PROJECT_ROOT / relative
    before = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise _error(f"fixed adjudication input is not one single-link regular file: {relative}")
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1 << 20)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ) or after.st_nlink != 1:
        raise _error(f"fixed adjudication input changed during read: {relative}")
    return b"".join(chunks)


def _inputs() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    values: dict[str, dict[str, Any]] = {}
    refs: dict[str, dict[str, Any]] = {}
    for role, (path, expected_sha256, expected_result_id) in _INPUTS.items():
        payload = _stable_bytes(path)
        digest = hashlib.sha256(payload).hexdigest()
        if digest != expected_sha256:
            raise _error(f"pinned {role} result bytes drifted")
        value = _strict_json(payload, path.as_posix())
        if value.get("result_id") != expected_result_id:
            raise _error(f"pinned {role} result identity drifted")
        values[role] = value
        refs[role] = {
            "path": path.as_posix(),
            "result_id": expected_result_id,
            "sha256": digest,
            "size_bytes": len(payload),
        }
    return values, refs


def _trial(result: dict[str, Any], code: str) -> dict[str, Any]:
    matches = [
        trial for trial in result.get("trials", []) if trial.get("document_provenance") == code
    ]
    if len(matches) != 1:
        raise _error(f"pinned result does not contain one {code} trial")
    return matches[0]


def _central_bank_decision(result: dict[str, Any], schema_by_id: dict[int, Any]) -> dict[str, Any]:
    trial = _trial(result, "MBB")
    rows = trial.get("unmapped_source_rows")
    expected_labels = [
        "Tiền gửi tại Ngân hàng Nhà nước Lào",
        "Tiền gửi tại Ngân hàng Quốc gia Campuchia",
    ]
    expected_values = [934855, 1213504]
    if (
        trial.get("status") != "VERIFIED_BY_CODEX_WITH_UNMAPPED_SOURCE_ROWS"
        or type(rows) is not list
        or [row.get("independent_pixel_label") for row in rows] != expected_labels
        or [row.get("normalized_value") for row in rows] != expected_values
    ):
        raise _error("MBB central-bank geography source rows drifted")
    schema = schema_by_id[574]
    if (
        schema.canonical_name != "Tiền gửi khác"
        or schema.parent_id != 569
        or schema.display_order != 14
    ):
        raise _error("live ReportNormId 574 binding drifted")
    aggregate = sum(expected_values)
    total = next(
        mapping["normalized_value"]
        for mapping in trial["verified_mappings"]
        if mapping["report_norm_id"] == 569
    )
    vietnam = next(
        mapping["normalized_value"]
        for mapping in trial["verified_mappings"]
        if mapping["report_norm_id"] == 570
    )
    if vietnam + aggregate != total:
        raise _error("MBB Vietnam plus other central-bank deposits does not close to total")
    return {
        "bank_code": "MBB",
        "decision_id": "CBD-MBB-574",
        "family_report_norm_id": 569,
        "mapping": {
            "canonical_name": schema.canonical_name,
            "normalized_value": aggregate,
            "parent_report_norm_id": schema.parent_id,
            "report_norm_id": 574,
            "source_components": canonical_clone_v1(rows),
            "status": "VERIFIED_BY_PROJECT_OWNER_AND_CODEX",
        },
        "project_owner_decision": (
            "LAOS_AND_CAMBODIA_CENTRAL_BANK_DEPOSITS_AGGREGATE_TO_OTHER_DEPOSITS_574"
        ),
        "reconciliation": {
            "computed_total": vietnam + aggregate,
            "other_deposits": aggregate,
            "visible_family_total": total,
            "vietnam_deposits": vietnam,
        },
        "status": "VERIFIED_BY_PROJECT_OWNER_AND_CODEX",
    }


def _absence_decision(
    result: dict[str, Any], *, code: str, family_id: int, first_tm_page: int, decision_id: str
) -> dict[str, Any]:
    trial = _trial(result, code)
    if (
        trial.get("status") != "UNRESOLVED"
        or trial.get("whole_document_family_absence_claim") is not False
        or trial.get("verified_mappings")
        or trial.get("verified_accounting_equations")
    ):
        raise _error(f"prior unresolved no-region trial drifted: {decision_id}")
    return {
        "bank_code": code,
        "decision_id": decision_id,
        "family_report_norm_id": family_id,
        "first_tm_family_report_norm_id": 592,
        "first_tm_page_by_project_owner": first_tm_page,
        "prior_scan_disposition": trial["disposition"],
        "project_owner_decision": "NOT_PRESENT_IN_BOUND_REPORT",
        "status": "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT",
        "whole_document_family_absence_claim": True,
    }


def _investment_hierarchy_decision(
    result: dict[str, Any], schema_by_id: dict[int, Any]
) -> dict[str, Any]:
    trial = next(item for item in result.get("trials", []) if item.get("bank_provenance") == "VIB")
    root = schema_by_id[804]
    afs = schema_by_id[805]
    if (
        trial.get("status") != "VERIFIED_BY_CODEX"
        or {mapping.get("report_norm_id") for mapping in trial["verified_mappings"]} != {807, 824}
        or root.children != [805, 829, 853, 859]
        or afs.parent_id != 804
        or schema_by_id[861].next_id != 862
    ):
        raise _error("VIB AFS or live 804..861 hierarchy drifted")
    return {
        "bank_code": "VIB",
        "decision_id": "SEC-VIB-804-805",
        "family_report_norm_id": 804,
        "hierarchy": {
            "family_children": list(root.children),
            "first_child_report_norm_id": 805,
            "last_descendant_report_norm_id": 861,
            "next_family_report_norm_id": 862,
        },
        "project_owner_decision": "AFS_PAGE_36_BELONGS_TO_805_UNDER_804_NOT_TRADING_592",
        "status": "VERIFIED_HIERARCHY_CLASSIFICATION",
        "verified_direct_report_norm_ids": [807, 824],
    }


def build_live_project_owner_tm_adjudications_v1() -> dict[str, Any]:
    """Rebuild the exact owner decisions from pinned results and live schema."""

    values, refs = _inputs()
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    decisions = [
        _central_bank_decision(values["central_bank_deposits"], schema_by_id),
        _absence_decision(
            values["interbank"],
            code="HDB",
            family_id=575,
            first_tm_page=25,
            decision_id="IDL-HDB-ABSENCE",
        ),
        _absence_decision(
            values["interbank"],
            code="VCB",
            family_id=575,
            first_tm_page=30,
            decision_id="IDL-VCB-ABSENCE",
        ),
        _absence_decision(
            values["derivatives"],
            code="VCB",
            family_id=631,
            first_tm_page=30,
            decision_id="DFI-VCB-ABSENCE",
        ),
        _investment_hierarchy_decision(values["investment_securities"], schema_by_id),
    ]
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "decisions": decisions,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            **refs,
            "tm_schema_projection_sha256": schema_authority["tm_schema_projection_sha256"],
        },
        "metrics": {
            "confirmed_absence_count": 3,
            "decision_count": 5,
            "hierarchy_confirmation_count": 1,
            "new_mapping_count": 1,
            "source_component_count": 2,
        },
        "state": "PROJECT_OWNER_TM_ADJUDICATIONS_VERIFIED",
    }
    return _validate(
        {**material, "adjudication_id": "e0067a:adjudication:" + canonical_json_sha256_v1(material)}
    )


def _validate(value: Any) -> dict[str, Any]:
    expected_fields = {
        "adjudication_id",
        "authority",
        "claim_boundary",
        "decisions",
        "format_version",
        "input_refs",
        "metrics",
        "state",
    }
    if type(value) is not dict or set(value) != expected_fields:
        raise _error("project-owner adjudication fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "PROJECT_OWNER_TM_ADJUDICATIONS_VERIFIED"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or not same_typed_json_v1(
            value["metrics"],
            {
                "confirmed_absence_count": 3,
                "decision_count": 5,
                "hierarchy_confirmation_count": 1,
                "new_mapping_count": 1,
                "source_component_count": 2,
            },
        )
        or type(value["decisions"]) is not list
        or [decision.get("decision_id") for decision in value["decisions"]]
        != [
            "CBD-MBB-574",
            "IDL-HDB-ABSENCE",
            "IDL-VCB-ABSENCE",
            "DFI-VCB-ABSENCE",
            "SEC-VIB-804-805",
        ]
    ):
        raise _error("project-owner adjudication identity or metrics drifted")
    for decision in value["decisions"]:
        for scalar in decision.values():
            if type(scalar) is float and not math.isfinite(scalar):
                raise _error("project-owner adjudication contains non-finite scalar")
    material = canonical_clone_v1(value)
    identity = material.pop("adjudication_id")
    if identity != "e0067a:adjudication:" + canonical_json_sha256_v1(material):
        raise _error("project-owner adjudication content identity drifted")
    return canonical_clone_v1(value)


def validate_project_owner_tm_adjudications_replay_v1(value: Any) -> dict[str, Any]:
    """Exact-rebuild a persisted adjudication from pinned results and live schema."""

    persisted = _validate(value)
    rebuilt = build_live_project_owner_tm_adjudications_v1()
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("project-owner adjudication does not exact-replay")
    return rebuilt


def main() -> None:
    result = build_live_project_owner_tm_adjudications_v1()
    OUTPUT_PATH.write_bytes(canonical_json_bytes_v1(result))


if __name__ == "__main__":
    main()
