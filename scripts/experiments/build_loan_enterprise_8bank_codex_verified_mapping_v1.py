"""Verify generic loan-enterprise mappings against pixels, accounting, and schema.

The production-facing matcher never receives bank, filename, page, review, or
schema answers.  This Role-A verifier runs only after the complete-PDF fresh
VietOCR structure result is frozen.  It binds that result to an independent
visible-pixel review, replays flat/grouped accounting equations, checks the
live workbook-order schema graph, maps only exact family roles, and preserves
source-only group nodes plus all OCR/pixel disagreements.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from types import ModuleType
from typing import Any

from PIL import Image

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    match_vietnamese_anchor_alias_v1,
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.full_document_vietocr_accounting_axis_v1 import (
    EXPECTED_DOCUMENT_ORDER,
    project_full_document_vietocr_accounting_axis_v1,
)
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import (
    _authority_snapshot,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "LoanEnterprise8BankCodexVerifiedMappingV1Error",
    "build_live_loan_enterprise_8bank_codex_verified_mapping_v1",
    "build_loan_enterprise_8bank_codex_verified_mapping_v1",
    "validate_loan_enterprise_8bank_codex_verified_mapping_replay_v1",
]


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "LOAN_ENTERPRISE_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT_VERSION = "LOAN_ENTERPRISE_8BANK_CODEX_PIXEL_REVIEW_V1"
REVIEW_STATE = "CODEX_PIXEL_REVIEW_COMPLETE"
RESULT_ID_PREFIX = "le8bcv1:result:"
RESULT_STATE = "LOAN_ENTERPRISE_8BANK_BOUNDED_CODEX_VERIFICATION_COMPLETE"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_GENERIC_LOAN_ENTERPRISE_"
    "STRUCTURE_PLUS_INDEPENDENT_VISIBLE_PIXEL_DASH_ACCOUNTING_AND_LIVE_TM_SCHEMA_"
    "ONLY_NO_BROAD_ABSENCE_CANONICALIZATION_EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0056-loan-enterprise-8bank-codex-pixel-review-v1.json")
REVIEW_SHA256 = "ecfd6cdc7df2734caa8fbb1fbd5fb146f3c01fdf40663f1fb109cc7cc070ff4d"
SEMANTIC_INDEX_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/verified-index/semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_CROP_MANIFEST_SHA256 = "a9f80cf9104af1177ba43d8a85de00b28c735223a91b663a5a79401bb038d94e"
EXPECTED_AXIS_SHA256 = "e99873cd16a7234702d0ee6e5fa9eb37637a1a75621228381e3dbcd7c5cfdcca"

_ROLE_BINDINGS: dict[str, tuple[int, str]] = {
    "STATE_ENTERPRISE": (767, "- Doanh nghiệp nhà nước"),
    "STATE_OWNED_SINGLE_MEMBER_LLC": (769, "+ Công ty TNHH MTV vốn nhà nước 100%"),
    "STATE_CONTROLLED_MULTI_MEMBER_LLC": (
        770,
        "Công ty TNHH MTV (hoặc trên MTV) vốn nhà nước trên 50%",
    ),
    "OTHER_LLC": (771, "+ Công ty TNHH khác"),
    "STATE_CONTROLLED_JOINT_STOCK": (772, "- Công ty cổ phần có vốn nhà nước trên 50%"),
    "OTHER_JOINT_STOCK": (773, "- Công ty cổ phần khác"),
    "PRIVATE_ENTERPRISE": (774, "- Doanh nghiệp tư nhân"),
    "COOPERATIVE": (776, "- Hợp tác xã và liên hợp tác xã"),
    "PARTNERSHIP": (778, "- Công ty hợp danh"),
    "FOREIGN_INVESTED_ENTERPRISE": (779, "- Công ty vốn nước ngoài"),
    "HOUSEHOLD_INDIVIDUAL": (780, "- Hộ kinh doanh, cá nhân"),
    "ADMIN_PUBLIC_ASSOCIATION": (
        781,
        "- Dịch vụ hành chính sự nghiệp, Đảng, đoàn thể, hiệp hội",
    ),
    "OTHER": (782, "- Khác"),
    "MARGIN_AND_SECURITIES_ADVANCE": (
        5748,
        "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
    ),
    # This is not a legal-form child of 766.  The exact source concept already
    # exists once in the universal schema as 6058; reusing it avoids creating
    # two ReportNormIds for the same visible population merely because it is
    # repeated in another source table.
    "FOREIGN_BRANCH_LOANS_SOURCE_ONLY": (
        6058,
        "+ Cho vay tại Chi nhánh và ngân hàng con nước ngoài",
    ),
}
_UNRESOLVED_ROLES: dict[str, tuple[int | None, str]] = {}
_ROLE_SCHEMA_PARENTS = {"FOREIGN_BRANCH_LOANS_SOURCE_ONLY": 727}
_SOURCE_GROUP_SCHEMA_EQUIVALENCE = {
    "Cho vay cá nhân": 780,
    "Cho vay khác": 782,
    "Cho vay tại Chi nhánh và ngân hàng con nước ngoài": 6058,
}
_NEGATIVE_FAMILIES = (
    (717, "Phân tích theo loại hình cho vay"),
    (727, "Phân tích theo ngành nghề kinh doanh"),
    (746, "Phân tích chất lượng nợ cho vay"),
    (752, "Phân tích dư nợ theo thời gian đáo hạn"),
)
_REVIEW_CHECKS = [
    "COMPLETE_PDF_REGION_ENUMERATION",
    "VISIBLE_CONSOLIDATED_REPORT_SCOPE",
    "CUSTOMER_LOAN_OWNER",
    "ENTERPRISE_OR_CUSTOMER_TYPE_BRANCH",
    "FLAT_OR_GROUPED_VISIBLE_ROW_GRAPH",
    "PERIOD_AXIS",
    "UNIT_SCOPE",
    "ROW_LABEL_AND_ROLE",
    "VALUE_GEOMETRY",
    "EXACT_DIGITS_SIGN_DASH_AND_MISSING_CELL",
    "SOURCE_GROUP_PARENT_CHILD_EQUATIONS",
    "OPTIONAL_MARGIN_AND_CORE_GRAND_TOTAL_BOUNDARY",
    "FINAL_TOTAL_ACCOUNTING_CLOSURE",
    "PERCENTAGE_DISPLAY_ROUNDING_WHEN_PRESENT",
    "SCHEMA_PARENT_CHILD_AND_DISPLAY_ORDER",
    "NEGATIVE_DEPOSIT_FAMILY_CONTROL",
]
_REVIEW_SAFETY = {
    "all_visible_cells_independently_reviewed": True,
    "all_visible_row_labels_independently_reviewed": True,
    "bank_or_page_used_as_matching_rule": False,
    "dash_blank_missing_and_zero_kept_distinct": True,
    "fresh_vietocr_used_as_pixel_truth": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": "VISIBLE_PDF_PIXELS",
    "old_ocr_used_as_semantic_text": False,
    "review_can_assert_document_wide_family_absence": False,
    "source_only_group_nodes_mapped_to_schema": False,
    "unchanged_semantic_surfaces_attested_equal_to_pixels_except_recorded_disagreements": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "broad_corpus_or_family_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "dash_blank_missing_and_zero_preserved": True,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_pdf_pixel_transcription_used_for_numeric_truth": True,
    "live_tm_schema_hierarchy_and_negative_families_checked": True,
    "mapping_authority_is_bounded_to_reviewed_source_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_group_nodes_exported_additively": False,
    "source_population_role_6058_mapped_once_without_double_count": True,
    "text_similarity_alone_used_for_mapping": False,
    "unmatched_or_non_equivalent_roles_preserved_unresolved": True,
}
_RESULT_FIELDS = {
    "authority",
    "claim_boundary",
    "format_version",
    "input_refs",
    "metrics",
    "result_id",
    "state",
    "trials",
}
_HEX = set("0123456789abcdef")


class LoanEnterprise8BankCodexVerifiedMappingV1Error(ValueError):
    """The review, graph, pixels, accounting, or live schema drifted."""


def _error(message: str) -> LoanEnterprise8BankCodexVerifiedMappingV1Error:
    return LoanEnterprise8BankCodexVerifiedMappingV1Error(message)


def _sha256(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 64 or any(char not in _HEX for char in value):
        raise _error(f"{label} SHA-256 drifted")
    return value


def _text(value: Any, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise _error(f"{label} must be one non-empty string")
    return value


def _relative_parts(path: Path) -> tuple[str, ...]:
    if not isinstance(path, Path) or path.is_absolute() or not path.parts:
        raise _error(f"fixed artifact path is not safe: {path}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise _error(f"fixed artifact path escapes project root: {path}")
    return tuple(path.parts)


def _stable_root_bytes(path: Path) -> bytes:
    parts = _relative_parts(path)
    directory_fd = os.open(
        PROJECT_ROOT,
        os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0),
    )
    try:
        for component in parts[:-1]:
            next_fd = os.open(
                component,
                os.O_RDONLY
                | os.O_DIRECTORY
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = next_fd
        descriptor = os.open(
            parts[-1],
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=directory_fd,
        )
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                raise _error(f"fixed artifact is not one regular file: {path}")
            chunks: list[bytes] = []
            while chunk := os.read(descriptor, 1024 * 1024):
                chunks.append(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
    finally:
        os.close(directory_fd)

    def identity(item: os.stat_result) -> tuple[int, int, int, int, int]:
        return (item.st_dev, item.st_ino, item.st_mode, item.st_size, item.st_mtime_ns)

    if identity(before) != identity(after):
        raise _error(f"fixed artifact changed while reading: {path}")
    payload = b"".join(chunks)
    if len(payload) != before.st_size:
        raise _error(f"fixed artifact read was incomplete: {path}")
    return payload


def _fixed_bytes(path: Path, expected_sha256: str) -> bytes:
    payload = _stable_root_bytes(path)
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise _error(f"fixed artifact content identity drifted: {path}")
    return payload


def _json_bytes(payload: bytes, label: str) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in items:
            if key in result:
                raise _error(f"{label} contains duplicate JSON key: {key}")
            result[key] = item
        return result

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                _error(f"{label} contains non-finite JSON: {token}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"{label} is not strict UTF-8 JSON") from exc
    if type(value) is not dict:
        raise _error(f"{label} must be one JSON object")
    return value


def _scanner() -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments/scan_loan_enterprise_full_document_vietocr_v1.py"
    spec = importlib.util.spec_from_file_location("loan_enterprise_scan_for_codex_mapping", path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load loan-enterprise scanner: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _matcher() -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments/loan_enterprise_variant_graph_v1.py"
    spec = importlib.util.spec_from_file_location("loan_enterprise_matcher_for_codex_mapping", path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load loan-enterprise matcher: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _string_list(value: Any, label: str) -> list[str]:
    if type(value) is not list:
        raise _error(f"{label} must be one list")
    return [_text(item, f"{label} item") for item in value]


def _typed_dash_cells(value: Any, roles: Sequence[str], lane_count: int) -> list[dict[str, Any]]:
    if type(value) is not list:
        raise _error("typed dash-cell ledger drifted")
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for item in value:
        if (
            type(item) is not dict
            or set(item) != {"lane_index", "role", "status"}
            or item["role"] not in roles
            or type(item["lane_index"]) is not int
            or not 0 <= item["lane_index"] < lane_count
            or item["status"] != "DASH"
            or (item["role"], item["lane_index"]) in seen
        ):
            raise _error("typed dash-cell identity drifted")
        seen.add((item["role"], item["lane_index"]))
        output.append(canonical_clone_v1(item))
    return output


def _accounting_review(
    value: Any, *, lane_count: int, row_count: int, roles: Sequence[str]
) -> dict[str, Any]:
    fields = {
        "intermediate_core_money_totals",
        "maximum_percentage_rounding_residual",
        "money_lane_sums",
        "percentage_lane_sums",
        "printed_money_totals",
        "printed_percentage_totals",
        "row_count",
        "typed_dash_cells",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error("pixel accounting fields drifted")
    if type(value["row_count"]) is not int or value["row_count"] != row_count:
        raise _error("pixel accounting row denominator drifted")
    percent_count = lane_count - 2
    for key, length in (
        ("money_lane_sums", 2),
        ("printed_money_totals", 2),
        ("percentage_lane_sums", percent_count),
        ("printed_percentage_totals", percent_count),
    ):
        if len(_string_list(value[key], f"pixel accounting {key}")) != length:
            raise _error(f"pixel accounting {key} denominator drifted")
    _text(value["maximum_percentage_rounding_residual"], "percentage tolerance")
    if type(value["intermediate_core_money_totals"]) is not list:
        raise _error("pixel accounting intermediate-core totals drifted")
    for item in value["intermediate_core_money_totals"]:
        if len(_string_list(item, "intermediate-core total")) != 2:
            raise _error("intermediate-core money denominator drifted")
    _typed_dash_cells(value["typed_dash_cells"], roles, lane_count)
    return canonical_clone_v1(value)


def _pixel_binding(value: Any, *, required: bool) -> dict[str, Any] | None:
    if value is None:
        if required:
            raise _error("pixel-only value lacks exact pixel binding")
        return None
    if (
        type(value) is not dict
        or set(value) != {"bbox_raw_pixels", "rgb_sha256"}
        or type(value["bbox_raw_pixels"]) is not list
        or len(value["bbox_raw_pixels"]) != 4
        or any(type(item) is not int for item in value["bbox_raw_pixels"])
        or value["bbox_raw_pixels"][0] < 0
        or value["bbox_raw_pixels"][1] < 0
        or value["bbox_raw_pixels"][0] >= value["bbox_raw_pixels"][2]
        or value["bbox_raw_pixels"][1] >= value["bbox_raw_pixels"][3]
    ):
        raise _error("pixel-only value binding shape drifted")
    _sha256(value["rgb_sha256"], "pixel-only RGB crop")
    return canonical_clone_v1(value)


def _disagreements(value: Any, *, roles: Sequence[str], lane_count: int) -> list[dict[str, Any]]:
    if type(value) is not list:
        raise _error("review Transformer disagreement ledger drifted")
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int | None]] = set()
    fields = {
        "disposition",
        "field",
        "lane_index",
        "pixel_binding",
        "pixel_transcription",
        "role",
        "semantic_proposal",
        "source_line_index",
    }
    for item in value:
        if type(item) is not dict or set(item) != fields:
            raise _error("review Transformer disagreement fields drifted")
        field = item["field"]
        role = item["role"]
        lane = item["lane_index"]
        if (
            field not in {"ROW_LABEL", "ROW_VALUE"}
            or role not in roles
            or (field == "ROW_LABEL" and lane is not None)
            or (field == "ROW_VALUE" and (type(lane) is not int or not 0 <= lane < lane_count))
            or (field, role, lane) in seen
        ):
            raise _error("review Transformer disagreement identity drifted")
        seen.add((field, role, lane))
        _text(item["pixel_transcription"], "review pixel disagreement")
        _text(item["disposition"], "review disagreement disposition")
        pixel_only = item["source_line_index"] is None
        if pixel_only:
            if (
                field != "ROW_VALUE"
                or item["semantic_proposal"] is not None
                or item["pixel_transcription"] != "-"
            ):
                raise _error("only one exact pixel-bound dash may lack semantic geometry")
        elif (
            type(item["source_line_index"]) is not int
            or item["source_line_index"] < 0
            or type(item["semantic_proposal"]) is not str
        ):
            raise _error("review disagreement semantic identity drifted")
        _pixel_binding(item["pixel_binding"], required=pixel_only)
        output.append(canonical_clone_v1(item))
    return output


def _source_group_equations(
    value: Any, roles: Sequence[str], lane_count: int
) -> list[dict[str, Any]]:
    if type(value) is not list:
        raise _error("source-group equation ledger drifted")
    fields = {
        "child_roles",
        "child_source_labels",
        "kind",
        "schema_equivalence_report_norm_id",
        "source_label",
        "source_only_child_values",
        "status",
        "visible_values",
    }
    allowed_kinds = {
        "PARENT_EQUALS_GRAPH_CHILD_ROLES",
        "PARENT_EQUALS_SOURCE_ONLY_CHILDREN",
        "CORE_SUBTOTAL_EQUALS_POPULATION_BRANCHES",
        "GRAND_TOTAL_EQUALS_CORE_PLUS_MARGIN",
    }
    output: list[dict[str, Any]] = []
    seen_labels: set[str] = set()
    for item in value:
        if (
            type(item) is not dict
            or set(item) != fields
            or item["kind"] not in allowed_kinds
            or item["status"] != "CORROBORATED_VISIBLE_PARENT_CHILD_EQUATION"
        ):
            raise _error("source-group equation fields/status drifted")
        label = _text(item["source_label"], "source-group label")
        if label in seen_labels:
            raise _error("source-group equation label is duplicated")
        seen_labels.add(label)
        expected_schema_id = _SOURCE_GROUP_SCHEMA_EQUIVALENCE.get(label)
        if item["schema_equivalence_report_norm_id"] != expected_schema_id:
            raise _error("source-group schema equivalence drifted")
        child_roles = _string_list(item["child_roles"], "source-group child roles")
        child_labels = _string_list(item["child_source_labels"], "source-group child source labels")
        if len(child_roles) != len(set(child_roles)) or any(
            role not in roles for role in child_roles
        ):
            raise _error("source-group child-role axis drifted")
        if len(_string_list(item["visible_values"], "source-group visible values")) != lane_count:
            raise _error("source-group visible-value denominator drifted")
        raw_children = item["source_only_child_values"]
        if type(raw_children) is not list:
            raise _error("source-only child value axis drifted")
        for child in raw_children:
            if len(_string_list(child, "source-only child values")) != lane_count:
                raise _error("source-only child value denominator drifted")
        if (
            (item["kind"] == "PARENT_EQUALS_GRAPH_CHILD_ROLES")
            and (not child_roles or child_labels or raw_children)
        ) or (
            item["kind"] == "PARENT_EQUALS_SOURCE_ONLY_CHILDREN"
            and (child_roles or not child_labels or len(child_labels) != len(raw_children))
        ):
            raise _error("source-group equation child-mode drifted")
        output.append(canonical_clone_v1(item))
    return output


def _review(value: Any) -> dict[str, Any]:
    top_fields = {
        "claim_boundary",
        "documents",
        "format_version",
        "review_checks",
        "reviewer",
        "safety",
        "semantic_axis_sha256",
        "semantic_index_sha256",
        "state",
    }
    if type(value) is not dict or set(value) != top_fields:
        raise _error("Codex enterprise review top-level fields drifted")
    if (
        value["format_version"] != REVIEW_FORMAT_VERSION
        or value["state"] != REVIEW_STATE
        or value["semantic_index_sha256"] != EXPECTED_INDEX_SHA256
        or value["semantic_axis_sha256"] != EXPECTED_AXIS_SHA256
        or not same_typed_json_v1(value["review_checks"], _REVIEW_CHECKS)
        or not same_typed_json_v1(value["safety"], _REVIEW_SAFETY)
        or type(value["reviewer"]) is not dict
        or set(value["reviewer"]) != {"kind", "review_run_id"}
        or value["reviewer"]["kind"] != "CODEX_INDEPENDENT_PDF_PIXEL_REVIEW"
        or type(value["documents"]) is not list
        or len(value["documents"]) != len(EXPECTED_DOCUMENT_ORDER)
    ):
        raise _error("Codex enterprise review identity, denominator, or safety drifted")
    _text(value["claim_boundary"], "review claim boundary")
    _text(value["reviewer"]["review_run_id"], "review run ID")
    document_fields = {
        "branch_pixel_transcription",
        "disposition",
        "document_provenance",
        "matcher_graph_sha256",
        "owner_pixel_transcription",
        "period_pixel_transcriptions",
        "physical_page",
        "pixel_accounting",
        "reviewed_role_order",
        "schema_unresolved_roles",
        "source_group_equations",
        "statement_context_evidence",
        "target_render_sha256",
        "transformer_disagreements",
        "unit_pixel_transcriptions",
        "whole_document_family_absence_claim",
    }
    allowed_roles = set(_ROLE_BINDINGS) | set(_UNRESOLVED_ROLES)
    for document, expected_code in zip(value["documents"], EXPECTED_DOCUMENT_ORDER, strict=True):
        if (
            type(document) is not dict
            or set(document) != document_fields
            or document["document_provenance"] != expected_code
            or document["whole_document_family_absence_claim"] is not False
        ):
            raise _error("Codex enterprise review document fields/order drifted")
        if (
            document["disposition"]
            == "NO_COMPLETE_REGION_IN_EXACT_FULL_DOCUMENT_FRESH_VIETOCR_SCAN"
        ):
            if any(
                document[key] is not None
                for key in (
                    "branch_pixel_transcription",
                    "matcher_graph_sha256",
                    "owner_pixel_transcription",
                    "physical_page",
                    "pixel_accounting",
                    "statement_context_evidence",
                    "target_render_sha256",
                )
            ) or any(
                document[key] != []
                for key in (
                    "period_pixel_transcriptions",
                    "reviewed_role_order",
                    "schema_unresolved_roles",
                    "source_group_equations",
                    "transformer_disagreements",
                    "unit_pixel_transcriptions",
                )
            ):
                raise _error("bounded no-match review invents source evidence")
            continue
        if (
            document["disposition"] != "UNIQUE_COMPLETE_REGION_VISIBLE_PIXEL_REVIEWED"
            or type(document["physical_page"]) is not int
            or document["physical_page"] <= 0
        ):
            raise _error("Codex enterprise review disposition/page drifted")
        _sha256(document["target_render_sha256"], "review target render")
        _sha256(document["matcher_graph_sha256"], "review matcher graph")
        _text(document["owner_pixel_transcription"], "review owner")
        _text(document["branch_pixel_transcription"], "review branch")
        periods = _string_list(document["period_pixel_transcriptions"], "review periods")
        units = _string_list(document["unit_pixel_transcriptions"], "review units")
        roles = _string_list(document["reviewed_role_order"], "review role order")
        unresolved = _string_list(document["schema_unresolved_roles"], "review unresolved")
        if (
            len(periods) != 2
            or len(units) not in {2, 4}
            or len(roles) < 5
            or len(roles) != len(set(roles))
            or any(role not in allowed_roles for role in roles)
            or set(unresolved) != {role for role in roles if role in _UNRESOLVED_ROLES}
        ):
            raise _error("review period/unit/role denominator drifted")
        context = document["statement_context_evidence"]
        if (
            type(context) is not dict
            or set(context)
            != {"mode", "physical_page", "pixel_transcription", "render_sha256", "report_scope"}
            or context["mode"]
            not in {"DOCUMENT_PRECEDING_VISIBLE_HEADING", "PAGE_LOCAL_VISIBLE_HEADING"}
            or context["report_scope"] != "CONSOLIDATED"
            or type(context["physical_page"]) is not int
            or not 0 < context["physical_page"] <= document["physical_page"]
        ):
            raise _error("review consolidated statement context drifted")
        _sha256(context["render_sha256"], "review context render")
        context_text = normalize_vietnamese_anchor_v1(
            _text(context["pixel_transcription"], "review context transcription")
        )
        if "bao cao tai chinh" not in context_text or "hop nhat" not in context_text:
            raise _error("review context is not visibly consolidated")
        _disagreements(document["transformer_disagreements"], roles=roles, lane_count=len(units))
        _source_group_equations(document["source_group_equations"], roles, len(units))
        _accounting_review(
            document["pixel_accounting"], lane_count=len(units), row_count=len(roles), roles=roles
        )
    return canonical_clone_v1(value)


def _schema(
    schema_by_id: Mapping[int, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    parent = schema_by_id.get(766)
    owner = schema_by_id.get(716)
    if (
        parent is None
        or owner is None
        or parent.parent_id != 716
        or parent.canonical_name != "Phân tích theo loại hình doanh nghiệp"
        or 766 not in owner.children
    ):
        raise _error("live TM enterprise owner/parent hierarchy drifted")
    roles: dict[str, dict[str, Any]] = {}
    for role, (schema_id, expected_name) in _ROLE_BINDINGS.items():
        item = schema_by_id.get(schema_id)
        expected_parent_id = _ROLE_SCHEMA_PARENTS.get(role, 766)
        expected_parent = schema_by_id.get(expected_parent_id)
        if (
            item is None
            or item.canonical_name != expected_name
            or expected_parent is None
            or item.parent_id != expected_parent_id
            or schema_id not in expected_parent.children
            or type(item.display_order) is not int
        ):
            raise _error(f"live TM enterprise schema binding drifted for {role}")
        roles[role] = {
            "canonical_name": item.canonical_name,
            "display_order": item.display_order,
            "report_norm_id": schema_id,
            "schema_parent_report_norm_id": expected_parent_id,
        }
    display_orders = [item["display_order"] for item in roles.values()]
    if len(display_orders) != len(set(display_orders)):
        raise _error("live TM enterprise display-order axis is not unique")
    negative: list[dict[str, Any]] = []
    for schema_id, expected_name in _NEGATIVE_FAMILIES:
        item = schema_by_id.get(schema_id)
        if (
            item is None
            or item.canonical_name != expected_name
            or item.parent_id != 716
            or schema_id not in owner.children
        ):
            raise _error("live TM negative sibling-family control drifted")
        negative.append(
            {
                "canonical_name": expected_name,
                "report_norm_id": schema_id,
                "status": "EXCLUDED_DISTINCT_SIBLING_FAMILY_BY_BRANCH_CHILD_AND_TOTAL_TOPOLOGY",
                "whole_document_absence_claim": False,
            }
        )
    return roles, negative


def _money(value: str) -> int:
    compact = value.strip().replace(" ", "")
    negative = compact.startswith("(") and compact.endswith(")")
    compact = compact.strip("()")
    if compact.startswith("-"):
        negative = True
        compact = compact[1:]
    digits = compact.replace(".", "").replace(",", "")
    if not digits.isdigit():
        raise _error(f"visible money transcription is not one integer: {value}")
    result = int(digits)
    return -result if negative else result


def _percent(value: str) -> Decimal:
    compact = value.strip().replace("%", "").replace(" ", "").replace(",", ".")
    try:
        result = Decimal(compact)
    except InvalidOperation as exc:
        raise _error(f"visible percentage transcription is invalid: {value}") from exc
    if not result.is_finite():
        raise _error("visible percentage transcription is non-finite")
    return result


def _numeric(value: str, lane_type: str) -> int | Decimal:
    return _money(value) if lane_type == "MONEY" else _percent(value)


def _surface_reconciles(left: str, right: str) -> bool:
    first = normalize_vietnamese_anchor_v1(left)
    second = normalize_vietnamese_anchor_v1(right)
    return first == second or first in second or second in first


def _distinct_aliases(values: Sequence[str]) -> tuple[str, ...]:
    distinct: dict[str, str] = {}
    for value in values:
        distinct.setdefault(normalize_vietnamese_anchor_v1(value), value)
    return tuple(distinct.values())


def _page_by_physical(document: Mapping[str, Any], physical_page: int) -> dict[str, Any]:
    selected = [
        page for page in document.get("pages", []) if page.get("physical_page") == physical_page
    ]
    if len(selected) != 1:
        raise _error("crop-manifest physical-page denominator drifted")
    return selected[0]


def _document_by_code(documents: Sequence[Mapping[str, Any]], code: str) -> dict[str, Any]:
    selected = [document for document in documents if document.get("bank_code") == code]
    if len(selected) != 1:
        raise _error("crop-manifest document denominator drifted")
    return selected[0]


def _render_ref(page: Mapping[str, Any]) -> dict[str, Any]:
    value = page.get("render_binding")
    if (
        type(value) is not dict
        or type(value.get("size_bytes")) is not int
        or value["size_bytes"] <= 0
    ):
        raise _error("crop-manifest render binding drifted")
    _sha256(value["sha256"], "crop-manifest render")
    if set(value) == {"path", "sha256", "size_bytes"} and type(value["path"]) is str:
        path: str | None = value["path"]
    elif set(value) == {
        "dpi",
        "origin",
        "pixel_height",
        "pixel_width",
        "render_profile",
        "sha256",
        "size_bytes",
        "upstream_render_ref",
    }:
        if (
            type(value["dpi"]) is not int
            or value["dpi"] <= 0
            or type(value["pixel_height"]) is not int
            or value["pixel_height"] <= 0
            or type(value["pixel_width"]) is not int
            or value["pixel_width"] <= 0
            or value["upstream_render_ref"] is not None
            or value["origin"] != "DETERMINISTIC_SOURCE_REPLAY_FOR_NATIVE_GEOMETRY"
            or type(value["render_profile"]) is not dict
        ):
            raise _error("deterministic hydrated render binding drifted")
        path = None
    else:
        raise _error("crop-manifest render binding fields drifted")
    return {"path": path, "sha256": value["sha256"], "size_bytes": value["size_bytes"]}


def _axis_document(documents: Sequence[Mapping[str, Any]], code: str) -> dict[str, Any]:
    selected = [document for document in documents if document.get("document_provenance") == code]
    if len(selected) != 1:
        raise _error("semantic-axis document denominator drifted")
    return selected[0]


def _axis_page(document: Mapping[str, Any], page_sequence: int) -> dict[str, Any]:
    selected = [page for page in document["pages"] if page.get("page_sequence") == page_sequence]
    if len(selected) != 1:
        raise _error("semantic-axis page denominator drifted")
    return selected[0]


def _disagreement(
    review_document: Mapping[str, Any], field: str, role: str, lane_index: int | None
) -> dict[str, Any] | None:
    selected = [
        item
        for item in review_document["transformer_disagreements"]
        if item["field"] == field and item["role"] == role and item["lane_index"] == lane_index
    ]
    if len(selected) > 1:
        raise _error("review disagreement is not unique")
    return selected[0] if selected else None


def _verify_pixel_binding(binding: Mapping[str, Any], render_bytes: bytes) -> None:
    try:
        image = Image.open(BytesIO(render_bytes))
        image.load()
        rgb = image.convert("RGB")
    except Exception as exc:
        raise _error("target render is not one decodable image") from exc
    bbox = binding["bbox_raw_pixels"]
    if bbox[2] > rgb.width or bbox[3] > rgb.height:
        raise _error("pixel-only evidence bbox exceeds target render")
    digest = hashlib.sha256(rgb.crop(tuple(bbox)).tobytes()).hexdigest()
    if digest != binding["rgb_sha256"]:
        raise _error("pixel-only evidence crop changed")


def _pixel_label(
    row: Mapping[str, Any], review_document: Mapping[str, Any], matcher: ModuleType
) -> str:
    role = row.get("role")
    label = row.get("label")
    if type(role) is not str or type(label) is not dict or type(label.get("surface")) is not str:
        raise _error("unique enterprise graph label drifted")
    semantic = label["surface"]
    correction = _disagreement(review_document, "ROW_LABEL", role, None)
    if correction is None:
        pixel = semantic
    else:
        indices = label.get("source_line_indices")
        if (
            correction["semantic_proposal"] != semantic
            or type(indices) is not list
            or correction["source_line_index"] not in indices
            or correction["pixel_binding"] is not None
        ):
            raise _error("pixel label correction does not bind the fresh graph")
        pixel = correction["pixel_transcription"]
    aliases = tuple(matcher._ROLE_ALIASES.get(role, ())) + tuple(
        getattr(matcher, "_EXTENDED_ROLE_ALIASES", {}).get(role, ())
    )
    if not aliases or match_vietnamese_anchor_alias_v1(pixel, _distinct_aliases(aliases)) is None:
        raise _error("independent pixel label is not one family role surface")
    return pixel


def _pixel_cell(
    cell: Mapping[str, Any],
    review_document: Mapping[str, Any],
    axis_page: Mapping[str, Any],
    role: str,
    render_bytes: bytes,
) -> tuple[dict[str, Any], int | Decimal]:
    lane_index = cell.get("lane_index")
    lane_type = cell.get("lane_type")
    if type(lane_index) is not int or lane_type not in {"MONEY", "PERCENT"}:
        raise _error("unique enterprise graph typed cell drifted")
    correction = _disagreement(review_document, "ROW_VALUE", role, lane_index)
    semantic = cell.get("semantic_surface")
    source_line_index = cell.get("source_line_index")
    pixel_binding = None
    if correction is None:
        if type(semantic) is not str or type(source_line_index) is not int:
            raise _error("unreviewed missing semantic cell cannot be promoted")
        pixel = semantic
    else:
        pixel = correction["pixel_transcription"]
        pixel_binding = correction["pixel_binding"]
        if semantic is not None:
            if (
                correction["semantic_proposal"] != semantic
                or correction["source_line_index"] != source_line_index
                or pixel_binding is not None
            ):
                raise _error("pixel correction does not bind the graph cell")
        elif correction["source_line_index"] is not None:
            source_line_index = correction["source_line_index"]
            lines = axis_page["lines"]
            if not 0 <= source_line_index < len(lines):
                raise _error("corrected semantic source line is out of range")
            semantic = lines[source_line_index]["vietocr_text"]
            if semantic != correction["semantic_proposal"] or pixel_binding is not None:
                raise _error("pixel correction does not bind the semantic-axis line")
        else:
            if semantic is not None or source_line_index is not None or pixel_binding is None:
                raise _error("pixel-only dash unexpectedly has semantic geometry")
            _verify_pixel_binding(pixel_binding, render_bytes)
    if pixel == "-":
        if pixel_binding is None:
            raise _error("visible dash lacks independent pixel-only binding")
        parsed: int | Decimal = 0 if lane_type == "MONEY" else Decimal(0)
        value_status = "DASH"
        # Preserve the raw DASH status and pixel transcription, while exposing
        # the project-owner-approved numeric interpretation explicitly as zero.
        normalized_value: int | str | None = 0
        verification = "VERIFIED_VISIBLE_PIXEL_DASH"
    else:
        parsed = _numeric(pixel, lane_type)
        value_status = "OBSERVED_ZERO" if parsed == 0 else "OBSERVED_VALUE"
        normalized_value = parsed if type(parsed) is int else format(parsed, "f")
        verification = "VERIFIED_VISIBLE_PIXEL_VALUE"
    return (
        {
            "independent_pixel_transcription": pixel,
            "lane_index": lane_index,
            "lane_type": lane_type,
            "normalized_value": normalized_value,
            "pixel_binding": canonical_clone_v1(pixel_binding),
            "semantic_proposal": semantic,
            "source_line_index": source_line_index,
            "value_status": value_status,
            "verification_status": verification,
        },
        parsed,
    )


def _total_cells(cells: Any) -> tuple[list[dict[str, Any]], list[int | Decimal]]:
    if type(cells) is not list or not cells:
        raise _error("unique enterprise graph total denominator drifted")
    output: list[dict[str, Any]] = []
    parsed: list[int | Decimal] = []
    for expected_lane, cell in enumerate(cells):
        if (
            type(cell) is not dict
            or cell.get("lane_index") != expected_lane
            or cell.get("lane_type") not in {"MONEY", "PERCENT"}
            or type(cell.get("semantic_surface")) is not str
            or type(cell.get("source_line_index")) is not int
        ):
            raise _error("unique enterprise graph total cell drifted")
        value = _numeric(cell["semantic_surface"], cell["lane_type"])
        output.append(
            {
                "independent_pixel_transcription": cell["semantic_surface"],
                "lane_index": expected_lane,
                "lane_type": cell["lane_type"],
                "semantic_proposal": cell["semantic_surface"],
                "source_line_index": cell["source_line_index"],
                "verification_status": "VERIFIED_VISIBLE_PIXEL_VALUE",
            }
        )
        parsed.append(value)
    return output, parsed


def _reviewed_axes(graph: Mapping[str, Any], review_document: Mapping[str, Any]) -> None:
    periods = graph.get("period_axis")
    reviewed_periods = review_document["period_pixel_transcriptions"]
    period_mode = graph.get("period_mode")
    relative_period_mode = type(period_mode) is str and period_mode.startswith("LOCAL_RELATIVE_")
    if relative_period_mode:
        expected_periods = ["CURRENT_PERIOD_END", "COMPARATIVE_PERIOD_START"]
        normalized_periods = [normalize_vietnamese_anchor_v1(item) for item in reviewed_periods]
        if normalized_periods[0] not in {
            "cuoi ky",
            "cuoi nam",
            "so cuoi ky",
            "so cuoi nam",
        } or normalized_periods[1] not in {
            "dau ky",
            "dau nam",
            "so dau ky",
            "so dau nam",
        }:
            raise _error("review relative-period surfaces drifted")
    else:
        expected_periods = reviewed_periods
    observed_periods = [item.get("period") for item in periods] if type(periods) is list else []
    exact_period_match = observed_periods == expected_periods
    if not exact_period_match and not relative_period_mode:

        def date_key(value: Any) -> tuple[int, int, int] | None:
            if type(value) is not str:
                return None
            numbers = [int(item) for item in re.findall(r"\d+", value)]
            years = [item for item in numbers if item >= 1900]
            if len(years) != 1 or len(numbers) < 3:
                return None
            year = years[0]
            before = numbers[: numbers.index(year)]
            if len(before) < 2:
                return None
            day, month = before[-2:]
            if not (1 <= day <= 31 and 1 <= month <= 12):
                return None
            return year, month, day

        exact_period_match = [date_key(item) for item in observed_periods] == [
            date_key(item) for item in reviewed_periods
        ] and all(date_key(item) is not None for item in observed_periods + reviewed_periods)
    if not exact_period_match:
        raise _error("review and unique graph period axis disagree")
    unit_scope = graph.get("unit_scope")
    if type(unit_scope) is not dict:
        raise _error("unique graph unit scope drifted")
    expected_units = (
        [unit_scope.get("surface"), unit_scope.get("surface")]
        if unit_scope.get("mode") == "INHERITED_DOCUMENT_MONEY_UNIT"
        else unit_scope.get("surfaces")
    )
    if type(expected_units) is not list or len(expected_units) != len(
        review_document["unit_pixel_transcriptions"]
    ):
        raise _error("review and unique graph unit denominator disagree")
    if [normalize_vietnamese_anchor_v1(item) for item in expected_units] != [
        normalize_vietnamese_anchor_v1(item)
        for item in review_document["unit_pixel_transcriptions"]
    ]:
        raise _error("review and unique graph unit surfaces disagree")


def _vector(strings: Sequence[str], lane_types: Sequence[str]) -> list[int | Decimal]:
    if len(strings) != len(lane_types):
        raise _error("visible equation vector denominator drifted")
    return [_numeric(item, lane_types[index]) for index, item in enumerate(strings)]


def _sum_vectors(vectors: Sequence[Sequence[int | Decimal]]) -> list[int | Decimal]:
    if not vectors:
        raise _error("accounting equation has no addends")
    width = len(vectors[0])
    if any(len(item) != width for item in vectors):
        raise _error("accounting equation vector widths drifted")
    return [sum((item[index] for item in vectors), 0) for index in range(width)]


def _line_surface_occurs(lines: Sequence[Mapping[str, Any]], surface: str) -> bool:
    target = normalize_vietnamese_anchor_v1(surface)
    for start in range(len(lines)):
        for width in range(1, min(4, len(lines) - start) + 1):
            joined = " ".join(lines[index]["vietocr_text"] for index in range(start, start + width))
            if normalize_vietnamese_anchor_v1(joined) == target:
                return True
    return False


def _numeric_occurs(lines: Sequence[Mapping[str, Any]], value: str, lane_type: str) -> bool:
    target = _numeric(value, lane_type)
    for line in lines:
        surface = line.get("vietocr_text")
        if type(surface) is not str:
            continue
        try:
            if _numeric(surface, lane_type) == target:
                return True
        except LoanEnterprise8BankCodexVerifiedMappingV1Error:
            continue
    return False


def _verify_source_group_equations(
    equations: Sequence[Mapping[str, Any]],
    parsed_by_role: Mapping[str, Sequence[int | Decimal]],
    lane_types: Sequence[str],
    axis_page: Mapping[str, Any],
    graph: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if not equations:
        return []
    lines = axis_page["lines"]
    by_label: dict[str, list[int | Decimal]] = {}
    output: list[dict[str, Any]] = []
    for equation in equations:
        label = equation["source_label"]
        kind = equation["kind"]
        visible = _vector(equation["visible_values"], lane_types)
        if not label.startswith("UNLABELED_") and not _line_surface_occurs(lines, label):
            raise _error(f"visible source-group label is absent from semantic page: {label}")
        for lane_index, surface in enumerate(equation["visible_values"]):
            if not _numeric_occurs(lines, surface, lane_types[lane_index]):
                raise _error("visible source-group value is absent from semantic page")
        if kind == "PARENT_EQUALS_GRAPH_CHILD_ROLES":
            addends = [parsed_by_role[role] for role in equation["child_roles"]]
        elif kind == "PARENT_EQUALS_SOURCE_ONLY_CHILDREN":
            for child_label in equation["child_source_labels"]:
                if not _line_surface_occurs(lines, child_label):
                    raise _error("source-only child label is absent from semantic page")
            addends = [_vector(item, lane_types) for item in equation["source_only_child_values"]]
            for child in equation["source_only_child_values"]:
                for lane_index, surface in enumerate(child):
                    if not _numeric_occurs(lines, surface, lane_types[lane_index]):
                        raise _error("source-only child value is absent from semantic page")
        elif kind == "CORE_SUBTOTAL_EQUALS_POPULATION_BRANCHES":
            try:
                addends = [by_label[item] for item in equation["child_source_labels"]]
            except KeyError as exc:
                raise _error("core subtotal references an unverified population branch") from exc
        elif kind == "GRAND_TOTAL_EQUALS_CORE_PLUS_MARGIN":
            try:
                addends = [by_label[item] for item in equation["child_source_labels"]]
            except KeyError as exc:
                raise _error("grand total references an unverified core subtotal") from exc
            addends.extend(parsed_by_role[role] for role in equation["child_roles"])
        else:  # Closed by review validation.
            raise _error("unsupported source-group equation kind")
        if _sum_vectors(addends) != visible:
            raise _error(f"visible source-group equation does not close: {label}")
        by_label[label] = visible
        output.append(
            {
                "child_roles": canonical_clone_v1(equation["child_roles"]),
                "child_source_labels": canonical_clone_v1(equation["child_source_labels"]),
                "kind": kind,
                "mapping_status": (
                    "SOURCE_ONLY_GRAPH_NODE_RETAINED_FOR_CHECK"
                    if equation["schema_equivalence_report_norm_id"] is None
                    else "VERIFIED_NON_ADDITIVE_SCHEMA_EQUIVALENCE"
                ),
                "schema_equivalence_report_norm_id": equation["schema_equivalence_report_norm_id"],
                "source_label": label,
                "status": "VERIFIED_BY_VISIBLE_ACCOUNTING_EQUATION",
                "visible_values": canonical_clone_v1(equation["visible_values"]),
            }
        )
    core_values = [
        by_label[item["source_label"]]
        for item in equations
        if item["kind"] == "CORE_SUBTOTAL_EQUALS_POPULATION_BRANCHES"
    ]
    reviewed_core = graph.get("intermediate_totals")
    if core_values:
        if type(reviewed_core) is not list:
            raise _error("graph intermediate-total axis drifted")
        graph_money_vectors = []
        for total in reviewed_core:
            _, parsed = _total_cells(total)
            graph_money_vectors.append(
                [parsed[index] for index, lane in enumerate(lane_types) if lane == "MONEY"]
            )
        for core in core_values:
            money = [core[index] for index, lane in enumerate(lane_types) if lane == "MONEY"]
            if money not in graph_money_vectors:
                raise _error("visible core subtotal does not bind a graph intermediate total")
    return output


def build_loan_enterprise_8bank_codex_verified_mapping_v1(
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    review: Any,
    schema_authority: Any,
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
    review_sha256: str,
    enable_extended_reporting_period_variants: bool = False,
) -> dict[str, Any]:
    """Derive the bounded verified enterprise mappings from exact authorities."""

    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if axis["semantic_axis_sha256"] != EXPECTED_AXIS_SHA256:
        raise _error("full-document semantic axis identity drifted")
    scanner = _scanner()
    matcher = _matcher()
    scanner.validate_loan_enterprise_full_document_scan_replay_v1(
        structure_scan,
        semantic_index,
        enable_extended_reporting_period_variants=(enable_extended_reporting_period_variants),
    )
    reviewed = _review(review)
    if review_sha256 != REVIEW_SHA256:
        raise _error("Codex pixel review content identity drifted")
    if crop_manifest_sha256 != EXPECTED_CROP_MANIFEST_SHA256:
        raise _error("full-document crop manifest identity drifted")
    if (
        type(crop_manifest) is not dict
        or type(crop_manifest.get("documents")) is not list
        or len(crop_manifest["documents"]) != len(EXPECTED_DOCUMENT_ORDER)
    ):
        raise _error("full-document crop manifest denominator drifted")
    schema_roles, negative_controls = _schema(schema_by_id)
    scan_trials = structure_scan["trials"]
    trials: list[dict[str, Any]] = []
    for ordinal, expected_code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        scan_trial = scan_trials[ordinal - 1]
        review_document = reviewed["documents"][ordinal - 1]
        axis_document = _axis_document(axis["documents"], expected_code)
        crop_document = _document_by_code(crop_manifest["documents"], expected_code)
        source_pdf_sha256 = _sha256(scan_trial["source_pdf_sha256"], "trial source PDF")
        matcher_result = scan_trial["matcher_result"]
        if review_document["disposition"] == (
            "NO_COMPLETE_REGION_IN_EXACT_FULL_DOCUMENT_FRESH_VIETOCR_SCAN"
        ):
            if matcher_result["status"] != "UNRESOLVED_NO_COMPLETE_REGION":
                raise _error("bounded no-match review conflicts with complete-PDF scan")
            trials.append(
                {
                    "document_ordinal": ordinal,
                    "document_provenance": expected_code,
                    "negative_family_controls": canonical_clone_v1(negative_controls),
                    "physical_page": None,
                    "source_group_equations": [],
                    "source_only_total": None,
                    "source_pdf_sha256": source_pdf_sha256,
                    "status": "UNRESOLVED_NO_COMPLETE_REGION_IN_EXACT_FRESH_VIETOCR_SCAN",
                    "transformer_disagreements": [],
                    "unresolved_rows": [],
                    "verified_mappings": [],
                    "whole_document_family_absence_claim": False,
                }
            )
            continue
        graphs = matcher_result.get("graphs")
        if (
            matcher_result.get("status") != "ACCEPTED_UNIQUE_VARIANT_GRAPH"
            or type(graphs) is not list
            or len(graphs) != 1
        ):
            raise _error("pixel-reviewed document lacks one unique complete graph")
        graph = graphs[0]
        if canonical_json_sha256_v1(graph) != review_document["matcher_graph_sha256"]:
            raise _error("pixel review does not bind the unique matcher graph")
        if graph.get("page_sequence") != review_document["physical_page"]:
            raise _error("pixel review and graph page disagree")
        target_page = _page_by_physical(crop_document, review_document["physical_page"])
        target_render = _render_ref(target_page)
        if target_render["sha256"] != review_document["target_render_sha256"]:
            raise _error("pixel review target render drifted")
        render_bytes = b""
        if target_render["path"] is not None:
            render_bytes = _stable_root_bytes(Path(target_render["path"]))
            if (
                len(render_bytes) != target_render["size_bytes"]
                or hashlib.sha256(render_bytes).hexdigest() != target_render["sha256"]
            ):
                raise _error("target render bytes drifted")
        elif any(
            item["pixel_binding"] is not None
            for item in review_document["transformer_disagreements"]
        ):
            raise _error("pixel-only evidence lacks a readable authenticated render")
        context = review_document["statement_context_evidence"]
        context_page = _page_by_physical(crop_document, context["physical_page"])
        context_render = _render_ref(context_page)
        if context_render["sha256"] != context["render_sha256"]:
            raise _error("visible consolidated statement context render drifted")
        if not _surface_reconciles(
            graph["customer_loan_context"]["surface"],
            review_document["owner_pixel_transcription"],
        ) or not _surface_reconciles(
            graph["branch"]["surface"], review_document["branch_pixel_transcription"]
        ):
            raise _error("pixel owner/branch does not reconcile with unique graph")
        _reviewed_axes(graph, review_document)
        graph_rows = graph.get("rows")
        if (
            type(graph_rows) is not list
            or [row.get("role") for row in graph_rows] != review_document["reviewed_role_order"]
        ):
            raise _error("review and unique graph ordered role axis disagree")
        axis_page = _axis_page(axis_document, graph["page_sequence"])

        verified: list[dict[str, Any]] = []
        unresolved: list[dict[str, Any]] = []
        parsed_rows: list[list[int | Decimal]] = []
        parsed_by_role: dict[str, list[int | Decimal]] = {}
        output_by_role: dict[str, list[dict[str, Any]]] = {}
        for row in graph_rows:
            role = row["role"]
            pixel_label = _pixel_label(row, review_document, matcher)
            values: list[dict[str, Any]] = []
            parsed: list[int | Decimal] = []
            for cell in row["values"]:
                output_cell, numeric = _pixel_cell(
                    cell, review_document, axis_page, role, render_bytes
                )
                values.append(output_cell)
                parsed.append(numeric)
            parsed_rows.append(parsed)
            parsed_by_role[role] = parsed
            output_by_role[role] = values
            if role in schema_roles:
                binding = schema_roles[role]
                money_values: list[dict[str, Any]] = []
                percentage_values: list[dict[str, Any]] = []
                money_axis = percent_axis = 0
                for cell in values:
                    if cell["lane_type"] == "MONEY":
                        money_values.append(
                            {
                                **cell,
                                "axis_index": money_axis,
                                "period_pixel_transcription": review_document[
                                    "period_pixel_transcriptions"
                                ][money_axis],
                            }
                        )
                        money_axis += 1
                    else:
                        percentage_values.append(
                            {
                                **cell,
                                "axis_index": percent_axis,
                                "period_pixel_transcription": review_document[
                                    "period_pixel_transcriptions"
                                ][percent_axis],
                            }
                        )
                        percent_axis += 1
                if money_axis != 2 or percent_axis not in {0, 2}:
                    raise _error("mapped enterprise row typed-lane denominator drifted")
                verified.append(
                    {
                        **binding,
                        "independent_pixel_label": pixel_label,
                        "money_values": money_values,
                        "percentage_corroboration": percentage_values,
                        "role": role,
                        "semantic_proposal_label": row["label"]["surface"],
                        "status": "VERIFIED_BY_CODEX",
                    }
                )
            else:
                candidate_id, status = _UNRESOLVED_ROLES[role]
                unresolved.append(
                    {
                        "candidate_report_norm_id": candidate_id,
                        "independent_pixel_label": pixel_label,
                        "role": role,
                        "semantic_proposal_label": row["label"]["surface"],
                        "status": status,
                        "values": values,
                        "whole_document_absence_claim": False,
                    }
                )

        total_cells, parsed_total = _total_cells(graph.get("total"))
        lane_types = graph["lane_types"]
        computed = [sum(row[index] for row in parsed_rows) for index in range(len(lane_types))]
        accounting = review_document["pixel_accounting"]
        money_indices = [index for index, kind in enumerate(lane_types) if kind == "MONEY"]
        percent_indices = [index for index, kind in enumerate(lane_types) if kind == "PERCENT"]
        if [computed[index] for index in money_indices] != [
            _money(item) for item in accounting["money_lane_sums"]
        ] or [parsed_total[index] for index in money_indices] != [
            _money(item) for item in accounting["printed_money_totals"]
        ]:
            raise _error("independent visible enterprise money equation drifted")
        if any(computed[index] != parsed_total[index] for index in money_indices):
            raise _error("independent visible enterprise money total does not close")
        tolerance = _percent(accounting["maximum_percentage_rounding_residual"])
        if tolerance < 0 or tolerance > Decimal("0.01"):
            raise _error("enterprise percentage rounding tolerance drifted")
        if [computed[index] for index in percent_indices] != [
            _percent(item) for item in accounting["percentage_lane_sums"]
        ] or [parsed_total[index] for index in percent_indices] != [
            _percent(item) for item in accounting["printed_percentage_totals"]
        ]:
            raise _error("independent visible enterprise percentage equation drifted")
        if any(abs(computed[index] - parsed_total[index]) > tolerance for index in percent_indices):
            raise _error("enterprise percentage rows exceed visible rounding tolerance")
        observed_dash = [
            {
                "lane_index": cell["lane_index"],
                "role": role,
                "status": "DASH",
            }
            for role, values in output_by_role.items()
            for cell in values
            if cell["value_status"] == "DASH"
        ]
        if not same_typed_json_v1(observed_dash, accounting["typed_dash_cells"]):
            raise _error("typed visible-dash ledger does not reconcile")
        source_equations = _verify_source_group_equations(
            review_document["source_group_equations"],
            parsed_by_role,
            lane_types,
            axis_page,
            graph,
        )
        reviewed_core = accounting["intermediate_core_money_totals"]
        output_core = [
            [
                equation["visible_values"][index]
                for index, kind in enumerate(lane_types)
                if kind == "MONEY"
            ]
            for equation in source_equations
            if equation["kind"] == "CORE_SUBTOTAL_EQUALS_POPULATION_BRANCHES"
        ]
        if not same_typed_json_v1(output_core, reviewed_core):
            raise _error("reviewed core-subtotal ledger drifted")
        trials.append(
            {
                "document_ordinal": ordinal,
                "document_provenance": expected_code,
                "layout_mode": graph["layout_mode"],
                "negative_family_controls": canonical_clone_v1(negative_controls),
                "observed_role_order": canonical_clone_v1(review_document["reviewed_role_order"]),
                "physical_page": review_document["physical_page"],
                "source_group_equations": source_equations,
                "source_only_total": {
                    "report_norm_id": None,
                    "status": "VERIFIED_SOURCE_ONLY",
                    "values": total_cells,
                },
                "source_pdf_sha256": source_pdf_sha256,
                "statement_context": canonical_clone_v1(context),
                "status": "PARTIAL_SCHEMA_MAPPING_VERIFIED_BY_CODEX",
                "target_render_sha256": review_document["target_render_sha256"],
                "transformer_disagreements": canonical_clone_v1(
                    review_document["transformer_disagreements"]
                ),
                "unresolved_rows": unresolved,
                "verified_mappings": verified,
                "whole_document_family_absence_claim": False,
            }
        )

    metrics = {
        "document_count": len(EXPECTED_DOCUMENT_ORDER),
        "document_no_complete_region_count": sum(
            trial["status"] == "UNRESOLVED_NO_COMPLETE_REGION_IN_EXACT_FRESH_VIETOCR_SCAN"
            for trial in trials
        ),
        "document_unique_structure_count": sum(
            trial["status"] == "PARTIAL_SCHEMA_MAPPING_VERIFIED_BY_CODEX" for trial in trials
        ),
        "mapped_item_verified_by_codex_count": sum(
            len(trial["verified_mappings"]) for trial in trials
        ),
        "mapped_money_value_cell_count": sum(
            len(item["money_values"]) for trial in trials for item in trial["verified_mappings"]
        ),
        "mapped_percentage_corroboration_cell_count": sum(
            len(item["percentage_corroboration"])
            for trial in trials
            for item in trial["verified_mappings"]
        ),
        "negative_family_control_count": sum(
            len(trial["negative_family_controls"]) for trial in trials
        ),
        "source_group_equation_verified_count": sum(
            len(trial["source_group_equations"]) for trial in trials
        ),
        "source_only_total_verified_count": sum(
            trial["source_only_total"] is not None for trial in trials
        ),
        "transformer_disagreement_preserved_count": sum(
            len(trial["transformer_disagreements"]) for trial in trials
        ),
        "typed_dash_cell_verified_count": sum(
            cell["value_status"] == "DASH"
            for trial in trials
            for item in trial["verified_mappings"]
            for cell in item["money_values"] + item["percentage_corroboration"]
        ),
        "unresolved_schema_semantic_row_count": sum(
            len(trial["unresolved_rows"]) for trial in trials
        ),
    }
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "codex_pixel_review": {
                "path": REVIEW_PATH.as_posix(),
                "sha256": review_sha256,
            },
            "crop_manifest_sha256": crop_manifest_sha256,
            "semantic_axis_sha256": axis["semantic_axis_sha256"],
            "semantic_index_sha256": EXPECTED_INDEX_SHA256,
            "structure_scan_id": structure_scan["scan_id"],
            "tm_schema_authority": canonical_clone_v1(schema_authority),
        },
        "metrics": metrics,
        "state": RESULT_STATE,
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("verified loan-enterprise result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != RESULT_STATE
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or type(value["metrics"]) is not dict
        or type(value["input_refs"]) is not dict
    ):
        raise _error("verified loan-enterprise result identity/authority drifted")
    clone = canonical_clone_v1(value)
    result_id = clone.pop("result_id")
    if result_id != RESULT_ID_PREFIX + canonical_json_sha256_v1(clone):
        raise _error("verified loan-enterprise result identity drifted")
    positive_fields = {
        "document_ordinal",
        "document_provenance",
        "layout_mode",
        "negative_family_controls",
        "observed_role_order",
        "physical_page",
        "source_group_equations",
        "source_only_total",
        "source_pdf_sha256",
        "statement_context",
        "status",
        "target_render_sha256",
        "transformer_disagreements",
        "unresolved_rows",
        "verified_mappings",
        "whole_document_family_absence_claim",
    }
    negative_fields = {
        "document_ordinal",
        "document_provenance",
        "negative_family_controls",
        "physical_page",
        "source_group_equations",
        "source_only_total",
        "source_pdf_sha256",
        "status",
        "transformer_disagreements",
        "unresolved_rows",
        "verified_mappings",
        "whole_document_family_absence_claim",
    }
    mapped = money = percentage = unresolved = negative_controls = source_totals = 0
    equations = disagreements = dashes = unique = no_match = 0
    for ordinal, (trial, expected_code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != expected_code
            or trial.get("whole_document_family_absence_claim") is not False
            or type(trial.get("negative_family_controls")) is not list
            or len(trial["negative_family_controls"]) != len(_NEGATIVE_FAMILIES)
            or type(trial.get("transformer_disagreements")) is not list
            or type(trial.get("unresolved_rows")) is not list
            or type(trial.get("verified_mappings")) is not list
            or type(trial.get("source_group_equations")) is not list
        ):
            raise _error("verified loan-enterprise trial identity/order drifted")
        _sha256(trial.get("source_pdf_sha256"), "verified source PDF")
        negative_controls += len(trial["negative_family_controls"])
        disagreements += len(trial["transformer_disagreements"])
        unresolved += len(trial["unresolved_rows"])
        mapped += len(trial["verified_mappings"])
        equations += len(trial["source_group_equations"])
        if trial["status"] == "UNRESOLVED_NO_COMPLETE_REGION_IN_EXACT_FRESH_VIETOCR_SCAN":
            no_match += 1
            if (
                set(trial) != negative_fields
                or trial["physical_page"] is not None
                or trial["source_only_total"] is not None
                or trial["source_group_equations"] != []
                or trial["verified_mappings"] != []
                or trial["unresolved_rows"] != []
                or trial["transformer_disagreements"] != []
            ):
                raise _error("bounded no-match result trial drifted")
            continue
        if (
            trial["status"] != "PARTIAL_SCHEMA_MAPPING_VERIFIED_BY_CODEX"
            or set(trial) != positive_fields
            or type(trial["physical_page"]) is not int
            or trial["physical_page"] <= 0
            or trial["layout_mode"] not in {"TWO_MONEY_LANES", "MONEY_PERCENT_COMPANION_LANES"}
            or type(trial["observed_role_order"]) is not list
            or type(trial["source_only_total"]) is not dict
            or trial["source_only_total"].get("status") != "VERIFIED_SOURCE_ONLY"
            or trial["source_only_total"].get("report_norm_id") is not None
            or type(trial.get("statement_context")) is not dict
        ):
            raise _error("verified positive loan-enterprise trial drifted")
        _sha256(trial["target_render_sha256"], "verified target render")
        unique += 1
        source_totals += 1
        seen_ids: set[int] = set()
        for mapping in trial["verified_mappings"]:
            fields = {
                "canonical_name",
                "display_order",
                "independent_pixel_label",
                "money_values",
                "percentage_corroboration",
                "report_norm_id",
                "role",
                "schema_parent_report_norm_id",
                "semantic_proposal_label",
                "status",
            }
            if (
                type(mapping) is not dict
                or set(mapping) != fields
                or mapping["status"] != "VERIFIED_BY_CODEX"
                or mapping["role"] not in _ROLE_BINDINGS
                or mapping["schema_parent_report_norm_id"]
                != _ROLE_SCHEMA_PARENTS.get(mapping["role"], 766)
                or type(mapping["report_norm_id"]) is not int
                or mapping["report_norm_id"] in seen_ids
                or type(mapping["display_order"]) is not int
                or type(mapping["money_values"]) is not list
                or len(mapping["money_values"]) != 2
                or type(mapping["percentage_corroboration"]) is not list
                or len(mapping["percentage_corroboration"]) not in {0, 2}
            ):
                raise _error("verified loan-enterprise mapping shape/status drifted")
            seen_ids.add(mapping["report_norm_id"])
            money += len(mapping["money_values"])
            percentage += len(mapping["percentage_corroboration"])
            for cell in mapping["money_values"] + mapping["percentage_corroboration"]:
                if cell.get("value_status") == "DASH":
                    if cell.get("normalized_value") != 0:
                        raise _error("verified DASH must retain raw status and normalize to zero")
                    dashes += 1
        for item in trial["unresolved_rows"]:
            fields = {
                "candidate_report_norm_id",
                "independent_pixel_label",
                "role",
                "semantic_proposal_label",
                "status",
                "values",
                "whole_document_absence_claim",
            }
            if (
                type(item) is not dict
                or set(item) != fields
                or item["role"] not in _UNRESOLVED_ROLES
                or item["status"] != _UNRESOLVED_ROLES[item["role"]][1]
                or item["candidate_report_norm_id"] != _UNRESOLVED_ROLES[item["role"]][0]
                or item["whole_document_absence_claim"] is not False
            ):
                raise _error("unresolved loan-enterprise row shape/status drifted")
        for equation in trial["source_group_equations"]:
            if (
                type(equation) is not dict
                or set(equation)
                != {
                    "child_roles",
                    "child_source_labels",
                    "kind",
                    "mapping_status",
                    "schema_equivalence_report_norm_id",
                    "source_label",
                    "status",
                    "visible_values",
                }
                or equation["mapping_status"]
                != (
                    "SOURCE_ONLY_GRAPH_NODE_RETAINED_FOR_CHECK"
                    if equation["schema_equivalence_report_norm_id"] is None
                    else "VERIFIED_NON_ADDITIVE_SCHEMA_EQUIVALENCE"
                )
                or equation["status"] != "VERIFIED_BY_VISIBLE_ACCOUNTING_EQUATION"
            ):
                raise _error("verified source-group equation shape drifted")
    expected_metrics = {
        "document_count": len(EXPECTED_DOCUMENT_ORDER),
        "document_no_complete_region_count": no_match,
        "document_unique_structure_count": unique,
        "mapped_item_verified_by_codex_count": mapped,
        "mapped_money_value_cell_count": money,
        "mapped_percentage_corroboration_cell_count": percentage,
        "negative_family_control_count": negative_controls,
        "source_group_equation_verified_count": equations,
        "source_only_total_verified_count": source_totals,
        "transformer_disagreement_preserved_count": disagreements,
        "typed_dash_cell_verified_count": dashes,
        "unresolved_schema_semantic_row_count": unresolved,
    }
    if not same_typed_json_v1(value["metrics"], expected_metrics):
        raise _error("verified loan-enterprise result metrics drifted")
    return canonical_clone_v1(value)


def build_live_loan_enterprise_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    """Replay all fixed inputs and construct the live bounded verified result."""

    semantic_bytes = _fixed_bytes(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_bytes = _fixed_bytes(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    review_bytes = _fixed_bytes(REVIEW_PATH, REVIEW_SHA256)
    semantic_index = _json_bytes(semantic_bytes, "full-document semantic index")
    crop_manifest = _json_bytes(crop_bytes, "full-document crop manifest")
    review = _json_bytes(review_bytes, "Codex enterprise pixel review")
    scanner = _scanner()
    structure_scan = scanner.build_loan_enterprise_full_document_scan_v1(semantic_index)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return build_loan_enterprise_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=EXPECTED_CROP_MANIFEST_SHA256,
        review_sha256=REVIEW_SHA256,
    )


def validate_loan_enterprise_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    """Exact-rebuild the result from all live fixed authorities."""

    persisted = _validate_result(value)
    rebuilt = build_live_loan_enterprise_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("verified loan-enterprise result does not replay exactly")
    return rebuilt


def main() -> int:
    result = build_live_loan_enterprise_8bank_codex_verified_mapping_v1()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
