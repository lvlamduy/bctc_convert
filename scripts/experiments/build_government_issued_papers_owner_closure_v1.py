"""Close owner-adjudicated government-liability and issued-paper gaps.

The byte-frozen E-0074/E-0076 results remain immutable.  This overlay pins
those exact bytes, binds the current live TM schema, and records the ten source
rows adjudicated by the project owner.  Three VPB whole-family tenor rows stay
open because the source does not allocate them to an instrument.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import SchemaItem, load_all
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = Path("docs/experiments/E-0080-government-issued-papers-owner-closure-v1.json")
GOVERNMENT_RESULT_PATH = Path(
    "docs/experiments/E-0074-government-nhnn-liabilities-8bank-codex-verified-mapping-v1.json"
)
GOVERNMENT_RESULT_SHA256 = "0ccfc5b9d9c10ed288de065f0194668df47f51674d9034423559dd06c0ad5de6"
GOVERNMENT_RESULT_ID = (
    "e0074:result:dbdaea017840adae9c66a8b7fdc69099e0ec591c7f6b351aa4d4a56fad65565e"
)
ISSUED_RESULT_PATH = Path(
    "docs/experiments/E-0076-issued-valuable-papers-8bank-codex-verified-mapping-v1.json"
)
ISSUED_RESULT_SHA256 = "d2c9a85c2d5a0a4fbdfb47321a27054a85ed2bdf81db022ae0ec1015d16117af"
ISSUED_RESULT_ID = "e0076:result:3f2e52c32b3e7a0dcbe2206354f20b3dc0e409bb9b27ee716fe6d1c85065d355"
TM_WORKBOOK_SHA256 = "d5a422d436d46170f2b6bc8758c547c410044a142b4833573a2e2c0c4efc2003"
HIERARCHY_CONFIG_SHA256 = "ed12038bfe6c550562bfb4f5119f70d10fd27a35e3d516a89bc4db48f515b3a5"

FORMAT_VERSION = "GOVERNMENT_ISSUED_PAPERS_PROJECT_OWNER_CLOSURE_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_BOUND_REPORT_PROJECT_OWNER_CLOSURE_OF_GN_001_TO_GN_004_"
    "IVP_001_TO_IVP_004_AND_IVP_008_PLUS_FINANCE_MINISTRY_RECLASSIFICATION_"
    "EXACT_BASE_BYTES_LIVE_TM_SCHEMA_VISIBLE_SOURCE_VALUES_ONLY_NO_VPB_"
    "WHOLE_FAMILY_TENOR_ALLOCATION_NO_CANONICAL_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_mapping_rule": False,
    "base_artifacts_rewritten_or_relabelled": False,
    "canonicalization_or_export_authority": False,
    "live_tm_schema_checked": True,
    "persisted_result_self_authenticating": False,
    "project_owner_adjudication_authority": True,
    "public_exact_replay_required": True,
    "source_locator_fields_are_evidence_only": True,
    "text_similarity_alone_used_for_mapping": False,
    "vp_bank_whole_family_tenors_allocated_to_instruments": False,
}


class GovernmentIssuedPapersOwnerClosureV1Error(ValueError):
    """A pinned base, schema binding, source row, or adjudication drifted."""


def _error(message: str) -> GovernmentIssuedPapersOwnerClosureV1Error:
    return GovernmentIssuedPapersOwnerClosureV1Error(message)


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
    if (
        relative.is_absolute()
        or not relative.parts
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise _error(f"fixed path escaped project root: {relative}")
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
                raise _error(f"fixed input is not a single-link regular file: {relative}")
            chunks: list[bytes] = []
            while chunk := os.read(descriptor, 1 << 20):
                chunks.append(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
    finally:
        os.close(directory_fd)
    before_identity = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_nlink,
    )
    after_identity = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_nlink,
    )
    if before_identity != after_identity:
        raise _error(f"fixed input changed during read: {relative}")
    return b"".join(chunks)


def _fixed_json(
    relative: Path, expected_sha256: str, expected_result_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = _stable_bytes(relative)
    digest = hashlib.sha256(payload).hexdigest()
    value = _strict_json(payload, relative.as_posix())
    if digest != expected_sha256 or value.get("result_id") != expected_result_id:
        raise _error(f"pinned base result drifted: {relative}")
    return value, {
        "path": relative.as_posix(),
        "result_id": expected_result_id,
        "sha256": digest,
        "size_bytes": len(payload),
    }


def _one_trial(base: Mapping[str, Any], bank: str) -> Mapping[str, Any]:
    trials = base.get("trials")
    if type(trials) is not list:
        raise _error("base trial denominator drifted")
    matches = [trial for trial in trials if trial.get("document_provenance") == bank]
    if len(matches) != 1:
        raise _error(f"base result does not contain one {bank} trial")
    return matches[0]


def _one_unmapped(trial: Mapping[str, Any], source_item_id: str) -> Mapping[str, Any]:
    rows = trial.get("unmapped_source_rows")
    if type(rows) is not list:
        raise _error("base unresolved row denominator drifted")
    matches = [row for row in rows if row.get("item_id") == source_item_id]
    if len(matches) != 1:
        raise _error(f"base result does not contain one {source_item_id}")
    return matches[0]


def _one_mapping(trial: Mapping[str, Any], role: str) -> Mapping[str, Any]:
    rows = trial.get("verified_mappings")
    if type(rows) is not list:
        raise _error("base mapping denominator drifted")
    matches = [row for row in rows if row.get("role") == role]
    if len(matches) != 1:
        raise _error(f"base result does not contain one {role}")
    return matches[0]


def _schema_binding(
    item: SchemaItem,
    report_norm_id: int,
    canonical_name: str,
    parent_id: int,
    display_order: int,
) -> dict[str, Any]:
    if (
        item.schema_id != report_norm_id
        or item.canonical_name != canonical_name
        or item.parent_id != parent_id
        or item.display_order != display_order
    ):
        raise _error(f"live TM schema item {report_norm_id} drifted")
    return {
        "canonical_name": canonical_name,
        "display_order": display_order,
        "parent_report_norm_id": parent_id,
        "report_norm_id": report_norm_id,
    }


def _live_schema() -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    workbooks, items = load_all(PROJECT_ROOT / "template", PROJECT_ROOT)
    _, hierarchy = load_hierarchy_reference(
        PROJECT_ROOT / "config/schemas/hierarchy_reference.yaml", PROJECT_ROOT, items
    )
    apply_hierarchy_reference(items, hierarchy)
    by_id = {item.schema_id: item for item in items}
    specs = {
        6070: ("Vay Ngân hàng Nhà nước", 1024, 527),
        6071: ("Tiền gửi có kỳ hạn của Kho bạc Nhà nước", 1024, 541),
        6072: ("Tiền gửi của Bộ Tài chính", 1024, 543),
        6009: ("Trên 12 tháng", 1101, 614),
        1103: ("Từ 12 tháng đến 5 năm", 1101, 616),
        6010: ("Dưới 5 năm", 1109, 625),
        1111: ("Từ 12 tháng đến 5 năm", 1109, 627),
        1117: ("Các loại giấy tờ có giá khác (bao gồm trái phiếu tăng vốn)", 1100, 633),
    }
    bindings = {
        report_norm_id: _schema_binding(by_id[report_norm_id], report_norm_id, name, parent, order)
        for report_norm_id, (name, parent, order) in specs.items()
    }
    tm_workbooks = [workbook for workbook in workbooks if workbook.statement_type == "TM"]
    if (
        len(tm_workbooks) != 1
        or tm_workbooks[0].sha256 != TM_WORKBOOK_SHA256
        or tm_workbooks[0].item_count != 1717
        or tm_workbooks[0].maximum_id != 6072
    ):
        raise _error("live TM workbook authority drifted")
    hierarchy_bytes = _stable_bytes(Path("config/schemas/hierarchy_reference.yaml"))
    if hashlib.sha256(hierarchy_bytes).hexdigest() != HIERARCHY_CONFIG_SHA256:
        raise _error("live hierarchy config drifted")
    return bindings, {
        "hierarchy_config": {
            "path": "config/schemas/hierarchy_reference.yaml",
            "sha256": HIERARCHY_CONFIG_SHA256,
            "size_bytes": len(hierarchy_bytes),
        },
        "schema_revision": "UNIVERSAL_BANK_BCTC_SCHEMA@6072",
        "tm_item_count": 1717,
        "tm_workbook": {
            "path": tm_workbooks[0].path,
            "sha256": TM_WORKBOOK_SHA256,
        },
    }


def _mapping(
    *,
    bank: str,
    page: int,
    ledger_id: str,
    source_item_id: str,
    source: Mapping[str, Any],
    schema: Mapping[str, Any],
    rationale: str,
    supersedes_report_norm_id: int | None = None,
) -> dict[str, Any]:
    values = source.get("values")
    if type(values) is not list or not values:
        raise _error(f"source values drifted for {ledger_id}")
    record: dict[str, Any] = {
        "bank_provenance": bank,
        "ledger_id": ledger_id,
        "physical_page": page,
        "project_owner_decision": rationale,
        "schema_binding": canonical_clone_v1(schema),
        "source_item_id": source_item_id,
        "source_label_evidence": canonical_clone_v1(source.get("label_evidence")),
        "source_values": canonical_clone_v1(values),
        "status": "VERIFIED_BY_PROJECT_OWNER_AND_CODEX",
    }
    if supersedes_report_norm_id is not None:
        record["supersedes_report_norm_id"] = supersedes_report_norm_id
    return record


def _government_mappings(
    base: Mapping[str, Any], schemas: Mapping[int, Mapping[str, Any]]
) -> list[dict[str, Any]]:
    specs = (
        ("ACB", 20, "GN-001", "GN-001", 6070, "Vay Ngân hàng Nhà nước"),
        ("CTG", 41, "GN-002", "GN-002", 6070, "Vay NHNN"),
        ("BID", 24, "GN-003", "GN-003", 6070, "Vay Ngân hàng Trung ương"),
        ("BID", 24, "GN-004", "GN-004", 6071, "Tiền gửi có kỳ hạn của KBNN"),
    )
    mappings = []
    for bank, page, ledger_id, source_item_id, schema_id, source_label in specs:
        source = _one_unmapped(_one_trial(base, bank), source_item_id)
        pixel = source.get("label_evidence", {}).get("pixel_transcription")
        if pixel != source_label:
            raise _error(f"source label drifted for {ledger_id}")
        mappings.append(
            _mapping(
                bank=bank,
                page=page,
                ledger_id=ledger_id,
                source_item_id=source_item_id,
                source=source,
                schema=schemas[schema_id],
                rationale=(
                    "The three central-bank wording variants share the dedicated broad "
                    "central-bank-loan row; the Treasury term deposit uses its dedicated "
                    "sibling and is not narrowed to a payment deposit."
                ),
            )
        )
    finance = _one_mapping(
        _one_trial(base, "BID"), "OTHER_GOVERNMENT_LIABILITY_FINANCE_MINISTRY_DEPOSIT"
    )
    if finance.get("schema_binding", {}).get("report_norm_id") != 1039:
        raise _error("historical Finance Ministry mapping drifted")
    mappings.append(
        _mapping(
            bank="BID",
            page=24,
            ledger_id="BID-FINANCE-MINISTRY-SUPERSEDE",
            source_item_id="OTHER_GOVERNMENT_LIABILITY_FINANCE_MINISTRY_DEPOSIT",
            source=finance,
            schema=schemas[6072],
            rationale=(
                "The explicit Finance Ministry deposit now maps to its dedicated sibling, "
                "superseding the historical catch-all 1039 mapping."
            ),
            supersedes_report_norm_id=1039,
        )
    )
    return mappings


def _issued_mappings(
    base: Mapping[str, Any], schemas: Mapping[int, Mapping[str, Any]]
) -> list[dict[str, Any]]:
    specs = (
        ("ACB", 21, "IVP-001", "ACB-BOND-EXACT-5Y", 1111),
        ("ACB", 21, "IVP-002", "ACB-CD-EXACT-5Y", 1103),
        ("MBB", 44, "IVP-003", "MBB-BOND-BELOW-5Y", 6010),
        ("MBB", 44, "IVP-004", "MBB-CD-OVER-12M", 6009),
        ("BID", 25, "IVP-008", "BID-CAPITAL-INCREASE-BOND", 1117),
    )
    rationales = {
        "IVP-001": "The inclusive schema boundary now admits the source tenor exactly at five years.",
        "IVP-002": "The inclusive schema boundary now admits the source tenor exactly at five years.",
        "IVP-003": (
            "The printed row is itself the broad bond tenor Dưới 5 năm and maps directly "
            "to broad schema row 6010; no shorter sub-tenor allocation is invented."
        ),
        "IVP-004": (
            "The printed row is itself the broad certificate tenor Trên 12 tháng and maps "
            "directly to broad schema row 6009; no medium/long split is invented."
        ),
        "IVP-008": (
            "The visible capital-increase bond maps to the expanded other-issued-paper "
            "leaf 1117 and remains a non-additive detail of the verified bond parent."
        ),
    }
    return [
        _mapping(
            bank=bank,
            page=page,
            ledger_id=ledger_id,
            source_item_id=source_item_id,
            source=_one_unmapped(_one_trial(base, bank), source_item_id),
            schema=schemas[schema_id],
            rationale=rationales[ledger_id],
        )
        for bank, page, ledger_id, source_item_id, schema_id in specs
    ]


def build_live_government_issued_papers_owner_closure_v1() -> dict[str, Any]:
    """Exact-rebuild the owner closure from pinned results and live schema."""

    government, government_ref = _fixed_json(
        GOVERNMENT_RESULT_PATH, GOVERNMENT_RESULT_SHA256, GOVERNMENT_RESULT_ID
    )
    issued, issued_ref = _fixed_json(ISSUED_RESULT_PATH, ISSUED_RESULT_SHA256, ISSUED_RESULT_ID)
    if government.get("metrics", {}).get("open_source_row_count") != 4:
        raise _error("government base open denominator drifted")
    if issued.get("metrics", {}).get("open_source_row_count") != 8:
        raise _error("issued-paper base open denominator drifted")
    schemas, schema_authority = _live_schema()
    mappings = _government_mappings(government, schemas) + _issued_mappings(issued, schemas)
    value_count = sum(len(mapping["source_values"]) for mapping in mappings)
    if len(mappings) != 10 or value_count != 18:
        raise _error("owner closure mapping/value denominator drifted")
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "government_result": government_ref,
            "issued_papers_result": issued_ref,
            "live_schema": schema_authority,
        },
        "mappings": mappings,
        "metrics": {
            "adjudicated_mapping_count": 10,
            "closed_ledger_entry_count": 9,
            "government_post_closure_mapping_count": 32,
            "government_post_closure_open_source_row_count": 0,
            "issued_papers_post_closure_mapping_count": 71,
            "issued_papers_post_closure_open_source_row_count": 3,
            "remaining_targeted_unresolved_count": 3,
            "source_value_component_count": 18,
            "superseded_mapping_count": 1,
        },
        "remaining_unresolved": [
            {
                "bank_provenance": "VPB",
                "ledger_id": ledger_id,
                "physical_page": 56,
                "reason": (
                    "The tenor is printed for the whole issued-paper family and is not "
                    "allocated to a certificate, promissory-note, or bond instrument."
                ),
                "source_item_id": source_item_id,
                "status": "UNRESOLVED_SOURCE_SCOPE",
            }
            for ledger_id, source_item_id in (
                ("IVP-005", "VPB-WHOLE-FAMILY-SHORT"),
                ("IVP-006", "VPB-WHOLE-FAMILY-MEDIUM"),
                ("IVP-007", "VPB-WHOLE-FAMILY-LONG"),
            )
        ],
        "state": "PROJECT_OWNER_GOVERNMENT_ISSUED_PAPERS_CLOSURE_VERIFIED",
    }
    return _validate(
        {**material, "result_id": "e0080:result:" + canonical_json_sha256_v1(material)}
    )


def _validate(value: Any) -> dict[str, Any]:
    fields = {
        "authority",
        "claim_boundary",
        "format_version",
        "input_refs",
        "mappings",
        "metrics",
        "remaining_unresolved",
        "result_id",
        "state",
    }
    expected_metrics = {
        "adjudicated_mapping_count": 10,
        "closed_ledger_entry_count": 9,
        "government_post_closure_mapping_count": 32,
        "government_post_closure_open_source_row_count": 0,
        "issued_papers_post_closure_mapping_count": 71,
        "issued_papers_post_closure_open_source_row_count": 3,
        "remaining_targeted_unresolved_count": 3,
        "source_value_component_count": 18,
        "superseded_mapping_count": 1,
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value.get("format_version") != FORMAT_VERSION
        or value.get("claim_boundary") != CLAIM_BOUNDARY
        or value.get("state") != "PROJECT_OWNER_GOVERNMENT_ISSUED_PAPERS_CLOSURE_VERIFIED"
        or not same_typed_json_v1(value.get("authority"), _AUTHORITY)
        or not same_typed_json_v1(value.get("metrics"), expected_metrics)
        or type(value.get("mappings")) is not list
        or len(value["mappings"]) != 10
        or type(value.get("remaining_unresolved")) is not list
        or [row.get("ledger_id") for row in value["remaining_unresolved"]]
        != ["IVP-005", "IVP-006", "IVP-007"]
    ):
        raise _error("owner closure result shape, authority, or denominator drifted")
    material = canonical_clone_v1(value)
    result_id = material.pop("result_id")
    if result_id != "e0080:result:" + canonical_json_sha256_v1(material):
        raise _error("owner closure content identity drifted")
    return canonical_clone_v1(value)


def validate_government_issued_papers_owner_closure_replay_v1(
    value: Any,
) -> dict[str, Any]:
    """Exact-rebuild a persisted closure from all pinned live inputs."""

    persisted = _validate(value)
    rebuilt = build_live_government_issued_papers_owner_closure_v1()
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("owner closure does not exact-replay")
    return rebuilt


def main() -> None:
    OUTPUT_PATH.write_bytes(
        canonical_json_bytes_v1(build_live_government_issued_papers_owner_closure_v1())
    )


if __name__ == "__main__":
    main()
