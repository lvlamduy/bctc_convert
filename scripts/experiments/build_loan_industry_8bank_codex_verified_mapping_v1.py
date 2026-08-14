"""Derive bounded loan-industry mappings from fresh VietOCR and visible pixels.

The complete-PDF matcher is bank-blind and variable-row.  This verifier binds
its five unique regions to a fixed independent PDF-pixel review, replays every
money/percentage equation, and checks the live TM schema.  Roles whose source
meaning is broader, narrower, or differently aggregated remain unresolved.
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
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
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
    "LoanIndustry8BankCodexVerifiedMappingV1Error",
    "build_live_loan_industry_8bank_codex_verified_mapping_v1",
    "build_loan_industry_8bank_codex_verified_mapping_v1",
    "validate_loan_industry_8bank_codex_verified_mapping_replay_v1",
]


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "LOAN_INDUSTRY_8BANK_CODEX_VERIFIED_MAPPING_V2"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_VARIABLE_LOAN_INDUSTRY_STRUCTURE_"
    "PLUS_INDEPENDENT_CODEX_VISIBLE_PIXEL_ACCOUNTING_PROJECT_OWNER_SCHEMA_ADJUDICATION_"
    "AND_LIVE_TM_SCHEMA_ONLY_NO_BROAD_CORPUS_ABSENCE_CANONICALIZATION_EXPORT_OR_"
    "PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0055-loan-industry-8bank-codex-pixel-review-v1.json")
REVIEW_SHA256 = "a9bf502c0797fc848a2a34a7edf4fe4d1b22cbb8457718ddb00fb5fab365a11d"
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
    "AGRICULTURE_FORESTRY_FISHERY": (728, "+ Nông, lâm, thủy hải sản"),
    "MINING": (729, "+ Khai khoáng"),
    "UTILITIES": (730, "+ Tiện ích: Sản xuất, phân phối điện, khí đốt, nước"),
    "WATER_WASTE": (731, "+ Cung cấp nước, quản lý và xử lý rác thải, nước thải"),
    "CONSTRUCTION": (732, "+ Xây dựng"),
    "MANUFACTURING": (733, "+ Sản xuất công nghiệp và gia công chế biến"),
    "TRADE_REPAIR": (734, "+ Thương mại: bán buôn, bán lẻ"),
    "REAL_ESTATE": (735, "+ Hoạt động kinh doanh bất động sản"),
    "EDUCATION": (737, "Giáo dục & Đào tạo"),
    "HEALTH_SOCIAL_WORK": (5719, "Y tế & hoạt động trợ giúp xã hội"),
    "ACCOMMODATION_FOOD": (738, "+ Dịch vụ lưu trú, nhà hàng, khách sạn, ăn uống"),
    "INFORMATION_COMMUNICATION": (740, "+ Thông tin và truyền thông"),
    "FINANCE_BANKING_INSURANCE": (741, "+ Hoạt động tài chính, ngân hàng, bảo hiểm"),
    "PROFESSIONAL_SCIENCE_TECHNOLOGY": (742, "+ Chuyên môn, khoa học và công nghệ"),
    "ADMIN_SUPPORT": (743, "+ Hoạt động hành chính và dịch vụ hỗ trợ"),
    "ARTS_ENTERTAINMENT": (5720, "Ngành nghệ thuật vui chơi giải trí"),
    "OTHER_SERVICES": (5721, "Ngành hoạt động dịch vụ khác"),
    "HOUSEHOLD_EMPLOYMENT_SELF_USE": (
        5722,
        "Ngành hoạt động làm thuê các công việc trong các hộ gia đình, sản xuất sản phẩm "
        "vật chất và dịch vụ tự tiêu dùng của hộ gia đình",
    ),
    "OTHER_INDUSTRIES": (745, "+ Các ngành nghề khác"),
    "MARGIN_AND_SECURITIES_ADVANCE": (
        5749,
        "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
    ),
    "TRANSPORT_STORAGE": (736, "+ Vận tải kho bãi và thông tin liên lạc"),
    "PUBLIC_ADMIN_DEFENCE_SOCIAL_SECURITY": (745, "+ Các ngành nghề khác"),
    "PERSONAL_HOUSING_LOANS": (
        6059,
        "+ Cho vay cá nhân để mua nhà ở, nhận quyền sử dụng đất để xây nhà ở",
    ),
    "FOREIGN_BRANCH_LOANS": (
        6058,
        "+ Cho vay tại Chi nhánh và ngân hàng con nước ngoài",
    ),
    "BROAD_SERVICES": (6060, "+ Dịch vụ"),
}
_REVIEW_UNRESOLVED_ROLES: dict[str, tuple[int | None, str]] = {
    "TRANSPORT_STORAGE": (
        736,
        "UNRESOLVED_SOURCE_TRANSPORT_ROW_NOT_EQUIVALENT_TO_COMBINED_TRANSPORT_AND_INFORMATION_SCHEMA_ROW",
    ),
    "PUBLIC_ADMIN_DEFENCE_SOCIAL_SECURITY": (
        744,
        "UNRESOLVED_PUBLIC_ADMINISTRATION_NOT_EQUIVALENT_TO_INTERNATIONAL_ORGANIZATIONS",
    ),
    "PERSONAL_HOUSING_LOANS": (
        None,
        "UNRESOLVED_NO_EXACT_INDUSTRY_CHILD_FOR_PERSONAL_HOUSING_LOAN_POPULATION",
    ),
    "FOREIGN_BRANCH_LOANS": (
        None,
        "UNRESOLVED_GEOGRAPHIC_BRANCH_POPULATION_NOT_ONE_INDUSTRY_SCHEMA_CHILD",
    ),
    "BROAD_SERVICES": (
        739,
        "UNRESOLVED_BROAD_SERVICES_NOT_EQUIVALENT_TO_PERSONAL_AND_COMMUNITY_SERVICES",
    ),
}
_UNRESOLVED_ROLES: dict[str, tuple[int | None, str]] = {}
_NEGATIVE_FAMILIES = (
    (717, "Phân tích theo loại hình cho vay"),
    (746, "Phân tích chất lượng nợ cho vay"),
    (752, "Phân tích dư nợ theo thời gian đáo hạn"),
    (766, "Phân tích theo loại hình doanh nghiệp"),
)
_REVIEW_CHECKS = [
    "COMPLETE_PDF_REGION_ENUMERATION",
    "VISIBLE_CONSOLIDATED_REPORT_SCOPE",
    "CUSTOMER_LOAN_OWNER",
    "INDUSTRY_BRANCH",
    "VARIABLE_COMPLETE_VISIBLE_ROW_BLOCK",
    "PERIOD_AXIS",
    "UNIT_SCOPE",
    "ROW_LABEL_AND_ROLE",
    "VALUE_GEOMETRY",
    "EXACT_DIGITS_SIGN_AND_MISSING_CELL",
    "OPTIONAL_SUBTOTAL_AND_MARGIN_BOUNDARY",
    "FINAL_TOTAL_ACCOUNTING_CLOSURE",
    "PERCENTAGE_DISPLAY_ROUNDING_WHEN_PRESENT",
    "SCHEMA_PARENT_CHILD_AND_DISPLAY_ORDER",
    "NEGATIVE_SIBLING_FAMILY_CONTROL",
]
_REVIEW_SAFETY = {
    "all_visible_cells_independently_reviewed": True,
    "all_visible_row_labels_independently_reviewed": True,
    "bank_or_page_used_as_matching_rule": False,
    "decimal_separator_normalization_changed_digits": False,
    "fresh_vietocr_used_as_pixel_truth": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": "VISIBLE_PDF_PIXELS",
    "old_ocr_used_as_semantic_text": False,
    "review_can_assert_document_wide_family_absence": False,
    "unchanged_semantic_cell_surfaces_attested_equal_to_pixels": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "broad_corpus_or_family_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_pdf_pixel_transcription_used_for_numeric_truth": True,
    "live_tm_schema_hierarchy_and_negative_families_checked": True,
    "mapping_authority_is_bounded_to_reviewed_source_rows": True,
    "persisted_result_self_authenticating": False,
    "project_owner_schema_adjudication_applied": True,
    "public_exact_replay_required": True,
    "text_similarity_alone_used_for_mapping": False,
    "unmatched_or_non_equivalent_roles_preserved_unresolved": False,
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


class LoanIndustry8BankCodexVerifiedMappingV1Error(ValueError):
    """The review, graph, visible arithmetic, or live TM schema drifted."""


def _error(message: str) -> LoanIndustry8BankCodexVerifiedMappingV1Error:
    return LoanIndustry8BankCodexVerifiedMappingV1Error(message)


def _sha256(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 64 or any(char not in _HEX for char in value):
        raise _error(f"{label} SHA-256 drifted")
    return value


def _text(value: Any, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise _error(f"{label} must be one non-empty string")
    return value


def _fixed_bytes(path: Path, expected_sha256: str) -> bytes:
    full = PROJECT_ROOT / path
    descriptor = os.open(
        full, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
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
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise _error(f"fixed artifact changed while reading: {path}")
    payload = b"".join(chunks)
    if len(payload) != before.st_size or hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise _error(f"fixed artifact content identity drifted: {path}")
    return payload


def _json_bytes(payload: bytes, label: str) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in items:
            if key in result:
                raise _error(f"{label} contains a duplicate JSON key")
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
    path = PROJECT_ROOT / "scripts/experiments/scan_loan_industry_full_document_vietocr_v1.py"
    spec = importlib.util.spec_from_file_location("loan_industry_scan_for_codex_mapping", path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load loan-industry scanner: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _string_list(value: Any, label: str) -> list[str]:
    if type(value) is not list:
        raise _error(f"{label} must be one list")
    return [_text(item, f"{label} item") for item in value]


def _optional_sha(value: Any, label: str) -> str | None:
    return None if value is None else _sha256(value, label)


def _accounting_review(value: Any, *, lane_count: int, row_count: int) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "intermediate_money_totals",
        "maximum_percentage_rounding_residual",
        "money_lane_sums",
        "percentage_lane_sums",
        "printed_money_totals",
        "printed_percentage_totals",
        "row_count",
    }:
        raise _error("pixel accounting fields drifted")
    if type(value["row_count"]) is not int or value["row_count"] != row_count:
        raise _error("pixel accounting row denominator drifted")
    money_count = 2
    percent_count = lane_count - money_count
    for key, length in (
        ("money_lane_sums", money_count),
        ("printed_money_totals", money_count),
        ("percentage_lane_sums", percent_count),
        ("printed_percentage_totals", percent_count),
    ):
        items = _string_list(value[key], f"pixel accounting {key}")
        if len(items) != length:
            raise _error(f"pixel accounting {key} denominator drifted")
    _text(
        value["maximum_percentage_rounding_residual"],
        "pixel accounting percentage tolerance",
    )
    if type(value["intermediate_money_totals"]) is not list:
        raise _error("pixel accounting intermediate totals drifted")
    for total in value["intermediate_money_totals"]:
        if len(_string_list(total, "pixel accounting intermediate total")) != 2:
            raise _error("pixel accounting intermediate money denominator drifted")
    return canonical_clone_v1(value)


def _review(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "claim_boundary",
        "documents",
        "format_version",
        "review_checks",
        "reviewer",
        "safety",
        "semantic_axis_sha256",
        "semantic_index_sha256",
        "state",
    }:
        raise _error("Codex industry review top-level fields drifted")
    if (
        value["format_version"] != "LOAN_INDUSTRY_8BANK_CODEX_PIXEL_REVIEW_V1"
        or value["state"] != "CODEX_PIXEL_REVIEW_COMPLETE"
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
        raise _error("Codex industry review identity, denominator, or safety drifted")
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
        "statement_context_evidence",
        "target_render_sha256",
        "transformer_disagreements",
        "unit_pixel_transcriptions",
        "whole_document_family_absence_claim",
    }
    # The E-0055 pixel review predates the project-owner schema adjudication.
    # Preserve its exact unresolved ledger while deriving the V2 mapping from
    # the live @6060 schema below.
    allowed_roles = set(_ROLE_BINDINGS) | set(_REVIEW_UNRESOLVED_ROLES)
    for document, expected_code in zip(value["documents"], EXPECTED_DOCUMENT_ORDER, strict=True):
        if (
            type(document) is not dict
            or set(document) != document_fields
            or document["document_provenance"] != expected_code
            or type(document["whole_document_family_absence_claim"]) is not bool
            or document["whole_document_family_absence_claim"] is not False
        ):
            raise _error("Codex industry review document fields/order drifted")
        disposition = document["disposition"]
        if disposition == "NO_COMPLETE_REGION_IN_EXACT_FULL_DOCUMENT_FRESH_VIETOCR_SCAN":
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
                    "transformer_disagreements",
                    "unit_pixel_transcriptions",
                )
            ):
                raise _error("bounded no-match review must not invent source evidence")
            continue
        if disposition != "UNIQUE_COMPLETE_REGION_VISIBLE_PIXEL_REVIEWED":
            raise _error("Codex industry review disposition drifted")
        if type(document["physical_page"]) is not int or document["physical_page"] <= 0:
            raise _error("review target physical page drifted")
        _sha256(document["target_render_sha256"], "review target render")
        _sha256(document["matcher_graph_sha256"], "review matcher graph")
        _text(document["owner_pixel_transcription"], "review owner")
        _text(document["branch_pixel_transcription"], "review branch")
        periods = _string_list(document["period_pixel_transcriptions"], "review periods")
        units = _string_list(document["unit_pixel_transcriptions"], "review units")
        roles = _string_list(document["reviewed_role_order"], "review role order")
        unresolved = _string_list(document["schema_unresolved_roles"], "review unresolved roles")
        if (
            len(periods) != 2
            or len(units) not in {2, 4}
            or len(roles) < 5
            or len(roles) != len(set(roles))
            or any(role not in allowed_roles for role in roles)
            or set(unresolved) != {role for role in roles if role in _REVIEW_UNRESOLVED_ROLES}
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
            or context["physical_page"] <= 0
            or context["physical_page"] > document["physical_page"]
        ):
            raise _error("review consolidated statement context drifted")
        _sha256(context["render_sha256"], "review context render")
        _text(context["pixel_transcription"], "review context transcription")
        if "bao cao tai chinh" not in normalize_vietnamese_anchor_v1(
            context["pixel_transcription"]
        ) or "hop nhat" not in normalize_vietnamese_anchor_v1(context["pixel_transcription"]):
            raise _error("review context is not visibly consolidated")
        _accounting_review(
            document["pixel_accounting"], lane_count=len(units), row_count=len(roles)
        )
        disagreements = document["transformer_disagreements"]
        if type(disagreements) is not list:
            raise _error("review Transformer disagreement ledger drifted")
        seen: set[tuple[str, str, int | None]] = set()
        for item in disagreements:
            if type(item) is not dict or set(item) != {
                "disposition",
                "field",
                "lane_index",
                "pixel_transcription",
                "role",
                "semantic_proposal",
                "source_line_index",
            }:
                raise _error("review Transformer disagreement fields drifted")
            if (
                item["field"] not in {"ROW_LABEL", "ROW_VALUE"}
                or item["role"] not in roles
                or type(item["source_line_index"]) is not int
                or item["source_line_index"] < 0
                or (item["field"] == "ROW_LABEL" and item["lane_index"] is not None)
                or (
                    item["field"] == "ROW_VALUE"
                    and (
                        type(item["lane_index"]) is not int
                        or not 0 <= item["lane_index"] < len(units)
                    )
                )
            ):
                raise _error("review Transformer disagreement identity drifted")
            _text(item["semantic_proposal"], "review semantic disagreement")
            _text(item["pixel_transcription"], "review pixel disagreement")
            _text(item["disposition"], "review disagreement disposition")
            key = (item["field"], item["role"], item["lane_index"])
            if key in seen:
                raise _error("duplicate review Transformer disagreement")
            seen.add(key)
    return canonical_clone_v1(value)


def _schema(
    schema_by_id: Mapping[int, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    parent = schema_by_id.get(727)
    owner = schema_by_id.get(716)
    if (
        parent is None
        or owner is None
        or parent.parent_id != 716
        or parent.canonical_name != "Phân tích theo ngành nghề kinh doanh"
        or 727 not in owner.children
    ):
        raise _error("live TM loan-industry owner/parent hierarchy drifted")
    roles: dict[str, dict[str, Any]] = {}
    for role, (schema_id, expected_name) in _ROLE_BINDINGS.items():
        item = schema_by_id.get(schema_id)
        if (
            item is None
            or item.canonical_name != expected_name
            or item.parent_id != 727
            or schema_id not in parent.children
            or type(item.display_order) is not int
        ):
            raise _error(f"live TM industry schema binding drifted for {role}")
        roles[role] = {
            "canonical_name": item.canonical_name,
            "display_order": item.display_order,
            "report_norm_id": schema_id,
            "schema_parent_report_norm_id": 727,
        }
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


def _surface_key(value: str) -> str:
    return re.sub(r"^(?:\d+(?:\s+\d+)*\s+)+", "", normalize_vietnamese_anchor_v1(value))


def _surface_reconciles(semantic: str, pixel: str) -> bool:
    left = _surface_key(semantic).replace(" 8 ", " ")
    right = _surface_key(pixel).replace(" & ", " ")
    return left == right or left in right or right in left


def _page_by_physical(document: Mapping[str, Any], physical_page: int) -> dict[str, Any]:
    pages = [
        page for page in document.get("pages", []) if page.get("physical_page") == physical_page
    ]
    if len(pages) != 1:
        raise _error("crop manifest physical-page denominator drifted")
    return pages[0]


def _render_sha(page: Mapping[str, Any]) -> str:
    binding = page.get("render_binding")
    if type(binding) is not dict:
        raise _error("crop manifest render binding drifted")
    return _sha256(binding.get("sha256"), "crop manifest render")


def _document_by_code(documents: Sequence[Mapping[str, Any]], code: str) -> dict[str, Any]:
    selected = [document for document in documents if document.get("bank_code") == code]
    if len(selected) != 1:
        raise _error("crop manifest document denominator drifted")
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


def _axis_page(axis_document: Mapping[str, Any], page_sequence: int) -> dict[str, Any]:
    selected = [page for page in axis_document["pages"] if page["page_sequence"] == page_sequence]
    if len(selected) != 1:
        raise _error("semantic-axis page denominator drifted")
    return selected[0]


def _pixel_cell(
    graph_cell: Mapping[str, Any],
    review_document: Mapping[str, Any],
    axis_page: Mapping[str, Any],
    role: str,
) -> tuple[dict[str, Any], int | Decimal]:
    lane_index = graph_cell.get("lane_index")
    lane_type = graph_cell.get("lane_type")
    if type(lane_index) is not int or lane_type not in {"MONEY", "PERCENT"}:
        raise _error("unique industry graph typed cell drifted")
    correction = _disagreement(review_document, "ROW_VALUE", role, lane_index)
    semantic = graph_cell.get("semantic_surface")
    source_line_index = graph_cell.get("source_line_index")
    if correction is None:
        if type(semantic) is not str or type(source_line_index) is not int:
            raise _error("unreviewed missing semantic cell cannot be promoted")
        pixel = semantic
    else:
        if semantic is None:
            source_line_index = correction["source_line_index"]
            lines = axis_page["lines"]
            if not 0 <= source_line_index < len(lines):
                raise _error("corrected semantic source line is out of range")
            semantic = lines[source_line_index]["vietocr_text"]
        if (
            semantic != correction["semantic_proposal"]
            or source_line_index != correction["source_line_index"]
        ):
            raise _error("pixel correction does not bind the fresh semantic proposal")
        pixel = correction["pixel_transcription"]
    parsed = _numeric(pixel, lane_type)
    return (
        {
            "independent_pixel_transcription": pixel,
            "lane_index": lane_index,
            "lane_type": lane_type,
            "semantic_proposal": semantic,
            "source_line_index": source_line_index,
            "status": "VERIFIED_VISIBLE_PIXEL_VALUE",
        },
        parsed,
    )


def _pixel_label(graph_row: Mapping[str, Any], review_document: Mapping[str, Any]) -> str:
    role = graph_row.get("role")
    label = graph_row.get("label")
    if type(role) is not str or type(label) is not dict or type(label.get("surface")) is not str:
        raise _error("unique industry graph label drifted")
    semantic = label["surface"]
    correction = _disagreement(review_document, "ROW_LABEL", role, None)
    if correction is None:
        return semantic
    indices = label.get("source_line_indices")
    if (
        correction["semantic_proposal"] != semantic
        or type(indices) is not list
        or correction["source_line_index"] not in indices
    ):
        raise _error("pixel label correction does not bind the fresh graph")
    return correction["pixel_transcription"]


def _total_cells(graph_cells: Any) -> tuple[list[dict[str, Any]], list[int | Decimal]]:
    if type(graph_cells) is not list or not graph_cells:
        raise _error("unique industry graph total denominator drifted")
    output: list[dict[str, Any]] = []
    parsed: list[int | Decimal] = []
    for expected_lane, cell in enumerate(graph_cells):
        if (
            type(cell) is not dict
            or cell.get("lane_index") != expected_lane
            or cell.get("lane_type") not in {"MONEY", "PERCENT"}
            or type(cell.get("semantic_surface")) is not str
            or type(cell.get("source_line_index")) is not int
        ):
            raise _error("unique industry graph total cell drifted")
        value = _numeric(cell["semantic_surface"], cell["lane_type"])
        output.append(
            {
                "independent_pixel_transcription": cell["semantic_surface"],
                "lane_index": expected_lane,
                "lane_type": cell["lane_type"],
                "semantic_proposal": cell["semantic_surface"],
                "source_line_index": cell["source_line_index"],
                "status": "VERIFIED_VISIBLE_PIXEL_VALUE",
            }
        )
        parsed.append(value)
    return output, parsed


def _reviewed_axes(graph: Mapping[str, Any], review_document: Mapping[str, Any]) -> None:
    periods = graph.get("period_axis")
    reviewed_periods = review_document["period_pixel_transcriptions"]
    if graph.get("period_mode") == "LOCAL_RELATIVE_PERIOD_ROLES":
        expected_periods = ["CURRENT_PERIOD_END", "COMPARATIVE_PERIOD_START"]
        if [normalize_vietnamese_anchor_v1(item) for item in reviewed_periods] != [
            "so cuoi ky",
            "so dau ky",
        ]:
            raise _error("review relative-period surfaces drifted")
    else:
        expected_periods = reviewed_periods
    if type(periods) is not list or [item.get("period") for item in periods] != expected_periods:
        raise _error("review and unique graph period axis disagree")
    unit_scope = graph.get("unit_scope")
    if type(unit_scope) is not dict:
        raise _error("unique graph unit scope drifted")
    if unit_scope.get("mode") == "INHERITED_DOCUMENT_MONEY_UNIT":
        expected_units = [unit_scope.get("surface"), unit_scope.get("surface")]
    else:
        expected_units = unit_scope.get("surfaces")
    if type(expected_units) is not list or len(expected_units) != len(
        review_document["unit_pixel_transcriptions"]
    ):
        raise _error("review and unique graph unit denominator disagree")
    if [normalize_vietnamese_anchor_v1(item) for item in expected_units] != [
        normalize_vietnamese_anchor_v1(item)
        for item in review_document["unit_pixel_transcriptions"]
    ]:
        raise _error("review and unique graph unit surfaces disagree")


def build_loan_industry_8bank_codex_verified_mapping_v1(
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    review: Any,
    schema_authority: Any,
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
    review_sha256: str,
) -> dict[str, Any]:
    """Derive bounded verified row mappings from exact live inputs and review."""

    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if axis["semantic_axis_sha256"] != EXPECTED_AXIS_SHA256:
        raise _error("full-document semantic axis identity drifted")
    scanner = _scanner()
    scanner.validate_loan_industry_full_document_scan_replay_v1(structure_scan, semantic_index)
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
    if type(schema_authority) is not dict:
        raise _error("live TM schema authority projection drifted")
    schema_roles, negative_controls = _schema(schema_by_id)

    trials: list[dict[str, Any]] = []
    for ordinal, expected_code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        review_document = reviewed["documents"][ordinal - 1]
        scan_trial = structure_scan["trials"][ordinal - 1]
        axis_document = axis["documents"][ordinal - 1]
        manifest_document = _document_by_code(crop_manifest["documents"], expected_code)
        if (
            scan_trial.get("document_provenance") != expected_code
            or axis_document.get("document_provenance") != expected_code
            or axis_document.get("document_ordinal") != ordinal
        ):
            raise _error("industry scan/axis document order drifted")
        matcher = scan_trial.get("matcher_result")
        if type(matcher) is not dict:
            raise _error("industry matcher result drifted")
        if (
            review_document["disposition"]
            == "NO_COMPLETE_REGION_IN_EXACT_FULL_DOCUMENT_FRESH_VIETOCR_SCAN"
        ):
            if (
                matcher.get("status") != "UNRESOLVED_NO_COMPLETE_REGION"
                or matcher.get("graphs") != []
                or matcher.get("uniqueness") != {"full_match_count": 0, "status": "NO_FULL_MATCH"}
            ):
                raise _error("bounded no-match review disagrees with exact full-document scan")
            trials.append(
                {
                    "document_ordinal": ordinal,
                    "document_provenance": expected_code,
                    "negative_family_controls": canonical_clone_v1(negative_controls),
                    "physical_page": None,
                    "source_only_total": None,
                    "status": "UNRESOLVED_NO_COMPLETE_REGION_IN_EXACT_FRESH_VIETOCR_SCAN",
                    "transformer_disagreements": [],
                    "unresolved_rows": [],
                    "verified_mappings": [],
                    "whole_document_family_absence_claim": False,
                }
            )
            continue

        graphs = matcher.get("graphs")
        if (
            matcher.get("status") != "ACCEPTED_UNIQUE_VARIANT_GRAPH"
            or type(graphs) is not list
            or len(graphs) != 1
        ):
            raise _error("review target is not one unique complete-PDF industry graph")
        graph = graphs[0]
        if (
            canonical_json_sha256_v1(graph) != review_document["matcher_graph_sha256"]
            or graph.get("page_sequence") != review_document["physical_page"]
            or graph.get("status") != "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"
            or graph.get("context_complete") is not True
            or graph.get("unresolved_reasons") != []
        ):
            raise _error("review target does not bind the unique industry graph")
        target_page = _page_by_physical(manifest_document, review_document["physical_page"])
        if _render_sha(target_page) != review_document["target_render_sha256"]:
            raise _error("review target render does not bind the crop manifest")
        context = review_document["statement_context_evidence"]
        context_page = _page_by_physical(manifest_document, context["physical_page"])
        if _render_sha(context_page) != context["render_sha256"]:
            raise _error("review statement-context render does not bind the crop manifest")
        if not _surface_reconciles(
            graph["customer_loan_context"]["surface"],
            review_document["owner_pixel_transcription"],
        ) or not _surface_reconciles(
            graph["branch"]["surface"], review_document["branch_pixel_transcription"]
        ):
            raise _error("review owner/branch does not reconcile with the unique graph")
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
        for graph_row in graph_rows:
            role = graph_row["role"]
            pixel_label = _pixel_label(graph_row, review_document)
            values: list[dict[str, Any]] = []
            parsed: list[int | Decimal] = []
            for graph_cell in graph_row["values"]:
                output_cell, numeric = _pixel_cell(graph_cell, review_document, axis_page, role)
                values.append(output_cell)
                parsed.append(numeric)
            parsed_rows.append(parsed)
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
                    raise _error("mapped industry row typed-lane denominator drifted")
                verified.append(
                    {
                        **binding,
                        "independent_pixel_label": pixel_label,
                        "money_values": money_values,
                        "percentage_corroboration": percentage_values,
                        "role": role,
                        "semantic_proposal_label": graph_row["label"]["surface"],
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
                        "semantic_proposal_label": graph_row["label"]["surface"],
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
            raise _error("independent visible industry money equation drifted")
        if any(computed[index] != parsed_total[index] for index in money_indices):
            raise _error("independent visible industry money total does not close")
        tolerance = _percent(accounting["maximum_percentage_rounding_residual"])
        if tolerance < 0 or tolerance > Decimal("0.01"):
            raise _error("industry percentage display-rounding tolerance drifted")
        if [computed[index] for index in percent_indices] != [
            _percent(item) for item in accounting["percentage_lane_sums"]
        ] or [parsed_total[index] for index in percent_indices] != [
            _percent(item) for item in accounting["printed_percentage_totals"]
        ]:
            raise _error("independent visible industry percentage equation drifted")
        if any(abs(computed[index] - parsed_total[index]) > tolerance for index in percent_indices):
            raise _error("industry percentage rows exceed visible rounding tolerance")

        intermediate_output: list[dict[str, Any]] = []
        graph_intermediate = graph.get("intermediate_totals")
        review_intermediate = accounting["intermediate_money_totals"]
        if type(graph_intermediate) is not list or len(graph_intermediate) != len(
            review_intermediate
        ):
            raise _error("industry intermediate-total denominator drifted")
        margin_positions = [
            index
            for index, row in enumerate(graph_rows)
            if row["role"] == "MARGIN_AND_SECURITIES_ADVANCE"
        ]
        for graph_total, reviewed_money in zip(
            graph_intermediate, review_intermediate, strict=True
        ):
            cells, parsed = _total_cells(graph_total)
            if len(margin_positions) != 1:
                raise _error("industry core subtotal lacks one following margin population")
            margin = margin_positions[0]
            expected_money = [
                sum(parsed_rows[row][lane] for row in range(margin)) for lane in money_indices
            ]
            if expected_money != [_money(item) for item in reviewed_money] or expected_money != [
                parsed[lane] for lane in money_indices
            ]:
                raise _error("independent visible industry core subtotal does not close")
            intermediate_output.append(
                {"status": "VERIFIED_SOURCE_ONLY_CORE_SUBTOTAL", "values": cells}
            )

        trials.append(
            {
                "document_ordinal": ordinal,
                "document_provenance": expected_code,
                "intermediate_totals": intermediate_output,
                "layout_mode": graph["layout_mode"],
                "negative_family_controls": canonical_clone_v1(negative_controls),
                "observed_role_order": canonical_clone_v1(review_document["reviewed_role_order"]),
                "physical_page": review_document["physical_page"],
                "source_only_total": {
                    "report_norm_id": None,
                    "status": "VERIFIED_SOURCE_ONLY",
                    "values": total_cells,
                },
                "statement_context": canonical_clone_v1(context),
                "status": "SCHEMA_MAPPING_VERIFIED_BY_CODEX",
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
            trial["status"] == "SCHEMA_MAPPING_VERIFIED_BY_CODEX" for trial in trials
        ),
        "intermediate_source_only_total_verified_count": sum(
            len(trial.get("intermediate_totals", [])) for trial in trials
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
        "source_only_total_verified_count": sum(
            trial["source_only_total"] is not None for trial in trials
        ),
        "transformer_disagreement_preserved_count": sum(
            len(trial["transformer_disagreements"]) for trial in trials
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
        "state": "LOAN_INDUSTRY_8BANK_BOUNDED_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "li8bcv2:result:" + canonical_json_sha256_v1(material)}
    )


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("verified loan-industry result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "LOAN_INDUSTRY_8BANK_BOUNDED_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or type(value["metrics"]) is not dict
        or type(value["input_refs"]) is not dict
    ):
        raise _error("verified loan-industry result identity/authority drifted")
    clone = canonical_clone_v1(value)
    result_id = clone.pop("result_id")
    if result_id != "li8bcv2:result:" + canonical_json_sha256_v1(clone):
        raise _error("verified loan-industry result identity drifted")
    positive_fields = {
        "document_ordinal",
        "document_provenance",
        "intermediate_totals",
        "layout_mode",
        "negative_family_controls",
        "observed_role_order",
        "physical_page",
        "source_only_total",
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
        "source_only_total",
        "status",
        "transformer_disagreements",
        "unresolved_rows",
        "verified_mappings",
        "whole_document_family_absence_claim",
    }
    mapped = money = percentage = unresolved = negative_controls = source_totals = 0
    intermediate = disagreements = unique = no_match = 0
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
        ):
            raise _error("verified loan-industry trial identity/order drifted")
        negative_controls += len(trial["negative_family_controls"])
        disagreements += len(trial["transformer_disagreements"])
        unresolved += len(trial["unresolved_rows"])
        mapped += len(trial["verified_mappings"])
        if trial["status"] == "UNRESOLVED_NO_COMPLETE_REGION_IN_EXACT_FRESH_VIETOCR_SCAN":
            no_match += 1
            if (
                set(trial) != negative_fields
                or trial["physical_page"] is not None
                or trial["source_only_total"] is not None
                or trial["verified_mappings"] != []
                or trial["unresolved_rows"] != []
                or trial["transformer_disagreements"] != []
            ):
                raise _error("bounded no-match result trial drifted")
            continue
        if (
            trial["status"] != "SCHEMA_MAPPING_VERIFIED_BY_CODEX"
            or set(trial) != positive_fields
            or type(trial["physical_page"]) is not int
            or trial["physical_page"] <= 0
            or trial["layout_mode"] not in {"TWO_MONEY_LANES", "MONEY_PERCENT_COMPANION_LANES"}
            or type(trial["intermediate_totals"]) is not list
            or type(trial["observed_role_order"]) is not list
            or type(trial["source_only_total"]) is not dict
            or trial["source_only_total"].get("status") != "VERIFIED_SOURCE_ONLY"
            or trial["source_only_total"].get("report_norm_id") is not None
            or type(trial.get("statement_context")) is not dict
        ):
            raise _error("verified positive loan-industry trial drifted")
        _sha256(trial["target_render_sha256"], "verified target render")
        unique += 1
        source_totals += 1
        intermediate += len(trial["intermediate_totals"])
        seen_ids: set[int] = set()
        for mapping in trial["verified_mappings"]:
            if (
                type(mapping) is not dict
                or set(mapping)
                != {
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
                or mapping["status"] != "VERIFIED_BY_CODEX"
                or mapping["schema_parent_report_norm_id"] != 727
                or type(mapping["report_norm_id"]) is not int
                or mapping["report_norm_id"] in seen_ids
                or type(mapping["display_order"]) is not int
                or type(mapping["money_values"]) is not list
                or len(mapping["money_values"]) != 2
                or type(mapping["percentage_corroboration"]) is not list
                or len(mapping["percentage_corroboration"]) not in {0, 2}
            ):
                raise _error("verified loan-industry mapping shape/status drifted")
            seen_ids.add(mapping["report_norm_id"])
            money += len(mapping["money_values"])
            percentage += len(mapping["percentage_corroboration"])
        for item in trial["unresolved_rows"]:
            if (
                type(item) is not dict
                or set(item)
                != {
                    "candidate_report_norm_id",
                    "independent_pixel_label",
                    "role",
                    "semantic_proposal_label",
                    "status",
                    "values",
                    "whole_document_absence_claim",
                }
                or item["role"] not in _UNRESOLVED_ROLES
                or item["status"] != _UNRESOLVED_ROLES[item["role"]][1]
                or item["candidate_report_norm_id"] != _UNRESOLVED_ROLES[item["role"]][0]
                or item["whole_document_absence_claim"] is not False
            ):
                raise _error("unresolved loan-industry row shape/status drifted")
    expected_metrics = {
        "document_count": len(EXPECTED_DOCUMENT_ORDER),
        "document_no_complete_region_count": no_match,
        "document_unique_structure_count": unique,
        "intermediate_source_only_total_verified_count": intermediate,
        "mapped_item_verified_by_codex_count": mapped,
        "mapped_money_value_cell_count": money,
        "mapped_percentage_corroboration_cell_count": percentage,
        "negative_family_control_count": negative_controls,
        "source_only_total_verified_count": source_totals,
        "transformer_disagreement_preserved_count": disagreements,
        "unresolved_schema_semantic_row_count": unresolved,
    }
    if not same_typed_json_v1(value["metrics"], expected_metrics):
        raise _error("verified loan-industry result metrics drifted")
    return canonical_clone_v1(value)


def build_live_loan_industry_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    """Replay all fixed inputs and build the live bounded verified result."""

    semantic_bytes = _fixed_bytes(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_bytes = _fixed_bytes(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    review_bytes = _fixed_bytes(REVIEW_PATH, REVIEW_SHA256)
    semantic_index = _json_bytes(semantic_bytes, "full-document semantic index")
    crop_manifest = _json_bytes(crop_bytes, "full-document crop manifest")
    review = _json_bytes(review_bytes, "Codex industry pixel review")
    scanner = _scanner()
    structure_scan = scanner.build_loan_industry_full_document_scan_v1(semantic_index)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return build_loan_industry_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=EXPECTED_CROP_MANIFEST_SHA256,
        review_sha256=REVIEW_SHA256,
    )


def validate_loan_industry_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    """Exact-rebuild the persisted result from all live fixed authorities."""

    persisted = _validate_result(value)
    rebuilt = build_live_loan_industry_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("verified loan-industry result does not replay exactly")
    return rebuilt


def main() -> int:
    result = build_live_loan_industry_8bank_codex_verified_mapping_v1()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
