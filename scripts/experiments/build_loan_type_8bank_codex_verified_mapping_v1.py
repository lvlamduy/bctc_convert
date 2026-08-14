"""Verify eight customer-loan-type tables from fresh VietOCR and PDF pixels.

The bank-blind matcher scans every page of every document and must yield one
unique structural graph.  This module binds that graph to an immutable Codex
review of the visible PDF pixels, independently recomputes money/percentage
closures, and checks the live TM schema hierarchy.  Text remains anchor
evidence: final mappings require owner, row topology, typed lanes, periods,
units, totals, accounting closure, pixels, and schema context together.
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
    "LoanType8BankCodexVerifiedMappingV1Error",
    "build_live_loan_type_8bank_codex_verified_mapping_v1",
    "build_loan_type_8bank_codex_verified_mapping_v1",
    "validate_loan_type_8bank_codex_verified_mapping_replay_v1",
]


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "LOAN_TYPE_8BANK_CODEX_VERIFIED_MAPPING_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_UNIQUE_COMPLETE_PDF_FRESH_VIETOCR_LOAN_TYPE_STRUCTURE_"
    "PLUS_INDEPENDENT_CODEX_VISIBLE_PIXEL_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_NO_"
    "BROAD_CORPUS_CANONICALIZATION_EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0054-loan-type-8bank-codex-pixel-review-v1.json")
REVIEW_SHA256 = "90f448990c31c4ad597593ee863a1b96ab50ebee549a6cd4614d997766fbf72d"
SEMANTIC_INDEX_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/verified-index/semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_AXIS_SHA256 = "e99873cd16a7234702d0ee6e5fa9eb37637a1a75621228381e3dbcd7c5cfdcca"

_ROLE_BINDINGS: dict[str, tuple[int, str, tuple[str, ...]]] = {
    "DOMESTIC_ORGANIZATIONS_INDIVIDUALS": (
        718,
        "+ Cho vay các tổ chức kinh tế, cá nhân trong nước",
        (
            "Cho vay các tổ chức kinh tế, cá nhân trong nước",
            "Cho vay các tổ chức kinh tế và cá nhân trong nước",
            "Cho vay các TCKT, cá nhân trong nước",
            "Cho vay các tổ chức kinh tế, cá nhân",
        ),
    ),
    "FINANCIAL_LEASE": (719, "+ Cho thuê tài chính", ("Cho thuê tài chính",)),
    "FOREIGN_ORGANIZATIONS_INDIVIDUALS": (
        721,
        "+ Cho vay cá nhân và tổ chức nước ngoài",
        (
            "Cho vay cá nhân và tổ chức nước ngoài",
            "Cho vay đối với các tổ chức, cá nhân nước ngoài",
            "Cho vay các TCKT, cá nhân nước ngoài",
        ),
    ),
    "DISCOUNT_INSTRUMENTS": (
        722,
        "+ Cho vay chiết khấu thương phiếu và các giấy tờ có giá",
        (
            "Cho vay chiết khấu thương phiếu và các giấy tờ có giá",
            "Cho vay chiết khấu công cụ chuyển nhượng và các giấy tờ có giá",
        ),
    ),
    "PAYMENTS_ON_BEHALF": (
        723,
        "+ Các khoản trả thay khách hàng",
        ("Các khoản trả thay khách hàng",),
    ),
    "FROZEN_OR_PENDING_LOANS": (
        724,
        "+ Nợ cho vay được khoanh và nợ chờ xử lý",
        (
            "Nợ cho vay được khoanh và nợ chờ xử lý",
            "Nợ cho vay khoanh và nợ chờ xử lý",
        ),
    ),
    "ENTRUSTED_OR_SPONSORED_CAPITAL": (
        725,
        "+ Cho vay bằng vốn tài trợ, ủy thác đầu tư",
        ("Cho vay bằng vốn tài trợ, ủy thác đầu tư",),
    ),
    "OTHER_LOANS": (726, "+ Cho vay khác", ("Cho vay khác",)),
    "MARGIN_AND_SECURITIES_ADVANCE": (
        5745,
        "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
        (
            "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
            "Cho vay giao dịch ký quỹ, ứng trước cho khách hàng",
            "Các khoản cho vay margin chứng khoán và ứng trước khách hàng tại MBS",
            "Các khoản cho vay margin chứng khoán và ứng trước khách hàng",
        ),
    ),
}
_UNRESOLVED_ROLES = {
    "GOVERNMENT_DIRECTED_OR_FUNDED": (
        720,
        "UNRESOLVED_SOURCE_LABEL_NOT_EQUIVALENT_TO_SCHEMA_FUNDED_SOURCE",
        (
            "Cho vay từ nguồn vốn từ Chính phủ, các tổ chức quốc tế khác",
            "Cho vay theo chỉ định của Chính phủ",
        ),
    ),
    "UNMAPPED_OTHER_CREDIT": (
        726,
        "UNRESOLVED_BROADER_CREDIT_SCOPE_NOT_EQUIVALENT_TO_OTHER_LOANS",
        ("Cấp tín dụng khác",),
    ),
}
_OWNER_ALIASES = ("Cho vay khách hàng", "Các khoản cho vay khách hàng")
_EXPECTED_REVIEW_CHECKS = [
    "VISIBLE_CONSOLIDATED_REPORT_SCOPE",
    "CUSTOMER_LOAN_OWNER",
    "COMPLETE_TYPE_ROW_BLOCK",
    "PERIOD_AXIS",
    "UNIT_SCOPE",
    "ROW_LABEL_AND_ROLE",
    "VALUE_GEOMETRY",
    "EXACT_DIGITS_SIGN_AND_DASH",
    "OPTIONAL_SUBTOTAL_AND_MARGIN_BOUNDARY",
    "FINAL_TOTAL_ACCOUNTING_CLOSURE",
    "PERCENTAGE_COMPANION_CLOSURE_WHEN_PRESENT",
    "SCHEMA_PARENT_CHILD_AND_DISPLAY_ORDER",
]
_EXPECTED_REVIEW_SAFETY = {
    "bank_or_page_used_as_matching_rule": False,
    "dash_cells_transcribed_as_zero": False,
    "fresh_vietocr_used_as_pixel_truth": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": "VISIBLE_PDF_PIXELS",
    "old_ocr_used_as_semantic_text": False,
    "review_can_assert_document_wide_absence": False,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "broad_corpus_authority": False,
    "canonicalization_or_export_authority": False,
    "dash_cells_preserved_distinct_from_zero": True,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_pdf_pixel_transcription_used_for_numeric_truth": True,
    "live_tm_schema_hierarchy_and_negative_families_checked": True,
    "mapping_authority_is_bounded_to_reviewed_source_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "text_similarity_alone_used_for_mapping": False,
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


class LoanType8BankCodexVerifiedMappingV1Error(ValueError):
    """The review, graph, arithmetic, or live TM schema drifted."""


def _error(message: str) -> LoanType8BankCodexVerifiedMappingV1Error:
    return LoanType8BankCodexVerifiedMappingV1Error(message)


def _sha256(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 64 or any(char not in _HEX for char in value):
        raise _error(f"{label} SHA-256 drifted")
    return value


def _text(value: Any, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise _error(f"{label} must be one non-empty string")
    return value


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be one positive integer")
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
    identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    if identity != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise _error(f"fixed artifact changed while reading: {path}")
    payload = b"".join(chunks)
    if len(payload) != before.st_size or hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise _error(f"fixed artifact content identity drifted: {path}")
    return payload


def _json_bytes(payload: bytes, label: str) -> dict[str, Any]:
    def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in items:
            if key in result:
                raise _error(f"{label} contains a duplicate JSON key")
            result[key] = item
        return result

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                _error(f"{label} contains non-finite JSON: {token}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"{label} is not strict UTF-8 JSON") from exc
    if type(value) is not dict:
        raise _error(f"{label} must be one JSON object")
    return value


def _string_list(value: Any, label: str, *, length: int | None = None) -> list[str]:
    if type(value) is not list or (length is not None and len(value) != length):
        raise _error(f"{label} denominator drifted")
    return [_text(item, f"{label} item") for item in value]


def _review_cell(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "lane_type",
        "pixel_transcription",
        "status",
    }:
        raise _error(f"{label} fields drifted")
    if value["lane_type"] not in {"MONEY", "PERCENT"} or value["status"] not in {
        "DASH",
        "VALUE",
    }:
        raise _error(f"{label} lane/status drifted")
    surface = _text(value["pixel_transcription"], f"{label} pixel transcription")
    if (value["status"] == "DASH") != (surface.strip() in {"-", "–", "—"}):
        raise _error(f"{label} DASH/value transcription drifted")
    return canonical_clone_v1(value)


def _review(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "banks",
        "claim_boundary",
        "format_version",
        "review_checks",
        "reviewer",
        "safety",
        "semantic_axis_sha256",
        "semantic_index_sha256",
        "state",
    }:
        raise _error("Codex loan-type review top-level fields drifted")
    if (
        value["format_version"] != "LOAN_TYPE_8BANK_CODEX_PIXEL_REVIEW_V1"
        or value["state"] != "CODEX_PIXEL_REVIEW_COMPLETE"
        or value["semantic_index_sha256"] != EXPECTED_INDEX_SHA256
        or value["semantic_axis_sha256"] != EXPECTED_AXIS_SHA256
        or not same_typed_json_v1(value["review_checks"], _EXPECTED_REVIEW_CHECKS)
        or not same_typed_json_v1(value["safety"], _EXPECTED_REVIEW_SAFETY)
        or type(value["reviewer"]) is not dict
        or set(value["reviewer"]) != {"kind", "review_run_id"}
        or value["reviewer"]["kind"] != "CODEX_INDEPENDENT_PDF_PIXEL_REVIEW"
        or type(value["banks"]) is not list
        or len(value["banks"]) != 8
    ):
        raise _error("Codex loan-type review identity, denominator, or safety drifted")
    _text(value["claim_boundary"], "review claim boundary")
    _text(value["reviewer"]["review_run_id"], "review run ID")
    bank_fields = {
        "bank_code",
        "intermediate_totals",
        "owner_pixel_transcription",
        "period_pixel_transcriptions",
        "physical_page",
        "rows",
        "source_only_total",
        "statement_context_evidence",
        "target_render_sha256",
        "transformer_disagreements",
        "unit_pixel_transcriptions",
    }
    allowed_roles = set(_ROLE_BINDINGS) | set(_UNRESOLVED_ROLES)
    for ordinal, (bank, expected_bank) in enumerate(
        zip(value["banks"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if type(bank) is not dict or set(bank) != bank_fields or bank["bank_code"] != expected_bank:
            raise _error(f"review bank {ordinal} fields/order drifted")
        _positive_int(bank["physical_page"], "review physical page")
        _sha256(bank["target_render_sha256"], "review target render")
        _text(bank["owner_pixel_transcription"], "review owner pixel text")
        _string_list(bank["period_pixel_transcriptions"], "review periods", length=2)
        units = _string_list(bank["unit_pixel_transcriptions"], "review units")
        if len(units) not in {2, 4}:
            raise _error("review unit lane denominator drifted")
        context = bank["statement_context_evidence"]
        if type(context) is not dict or set(context) != {
            "mode",
            "physical_page",
            "pixel_transcription",
            "render_sha256",
            "report_scope",
        }:
            raise _error("review statement context fields drifted")
        if (
            context["mode"]
            not in {"DOCUMENT_PRECEDING_VISIBLE_HEADING", "PAGE_LOCAL_VISIBLE_HEADING"}
            or context["report_scope"] != "CONSOLIDATED"
            or _positive_int(context["physical_page"], "review context page")
            > bank["physical_page"]
        ):
            raise _error("review statement context scope/order drifted")
        _text(context["pixel_transcription"], "review statement context text")
        _sha256(context["render_sha256"], "review context render")
        if type(bank["rows"]) is not list or len(bank["rows"]) < 3:
            raise _error("review loan-type row denominator drifted")
        seen: set[str] = set()
        for row in bank["rows"]:
            if type(row) is not dict or set(row) != {
                "cells",
                "mapping_disposition",
                "pixel_label",
                "role",
            }:
                raise _error("review loan-type row fields drifted")
            role = row["role"]
            if type(role) is not str or role not in allowed_roles or role in seen:
                raise _error("review loan-type role set drifted")
            seen.add(role)
            _text(row["pixel_label"], "review row label")
            expected_disposition = (
                "MAP" if role in _ROLE_BINDINGS else "UNRESOLVED_SCHEMA_SEMANTICS"
            )
            if row["mapping_disposition"] != expected_disposition:
                raise _error("review mapping disposition drifted")
            if type(row["cells"]) is not list or len(row["cells"]) != len(units):
                raise _error("review row lane denominator drifted")
            cells = [_review_cell(cell, "review row cell") for cell in row["cells"]]
            if [cell["lane_type"] for cell in cells] != [
                "MONEY",
                "MONEY",
            ] and [cell["lane_type"] for cell in cells] != [
                "MONEY",
                "PERCENT",
                "MONEY",
                "PERCENT",
            ]:
                raise _error("review typed lane order drifted")
        if type(bank["source_only_total"]) is not list or len(bank["source_only_total"]) != len(
            units
        ):
            raise _error("review final-total lane denominator drifted")
        for cell in bank["source_only_total"]:
            if _review_cell(cell, "review source-only total")["status"] != "VALUE":
                raise _error("review source-only total cannot be DASH")
        if type(bank["intermediate_totals"]) is not list:
            raise _error("review intermediate-total ledger drifted")
        for total in bank["intermediate_totals"]:
            if type(total) is not list or len(total) != len(units):
                raise _error("review intermediate-total lane denominator drifted")
            for cell in total:
                if _review_cell(cell, "review intermediate total")["status"] != "VALUE":
                    raise _error("review intermediate total cannot be DASH")
        if type(bank["transformer_disagreements"]) is not list:
            raise _error("review Transformer disagreement ledger drifted")
        for disagreement in bank["transformer_disagreements"]:
            if type(disagreement) is not dict or set(disagreement) != {
                "disposition",
                "field",
                "pixel_transcription",
                "semantic_proposal",
            }:
                raise _error("review Transformer disagreement fields drifted")
            for key, item in disagreement.items():
                _text(item, f"review Transformer disagreement {key}")
    return canonical_clone_v1(value)


def _without_section(value: str) -> str:
    normalized = normalize_vietnamese_anchor_v1(value)
    return re.sub(r"^(?:\d+(?:\s+\d+)*\s+)+", "", normalized).strip()


def _has_disagreement(
    disagreements: Sequence[Mapping[str, Any]], semantic: str, pixel: str
) -> bool:
    return any(
        item.get("semantic_proposal") == semantic and item.get("pixel_transcription") == pixel
        for item in disagreements
    )


def _surface_compatible(
    semantic: str,
    pixel: str,
    aliases: Sequence[str],
    disagreements: Sequence[Mapping[str, Any]],
) -> bool:
    semantic_key = _without_section(semantic)
    pixel_key = _without_section(pixel)
    alias_keys = [_without_section(alias) for alias in aliases]
    pixel_is_role = match_vietnamese_anchor_alias_v1(pixel, aliases) is not None or any(
        alias in pixel_key or pixel_key in alias for alias in alias_keys
    )
    reconciled = (
        semantic_key == pixel_key
        or semantic_key in pixel_key
        or pixel_key in semantic_key
        or _has_disagreement(disagreements, semantic, pixel)
    )
    return pixel_is_role and reconciled


def _money(surface: str) -> int:
    compact = surface.strip().replace(" ", "")
    negative = compact.startswith("(") and compact.endswith(")")
    compact = compact.strip("()").lstrip("+")
    if compact.startswith("-"):
        negative = True
        compact = compact[1:]
    digits = compact.replace(".", "").replace(",", "")
    if not digits.isdigit():
        raise _error(f"visible money transcription is not one integer: {surface}")
    result = int(digits)
    return -result if negative else result


def _percent(surface: str) -> Decimal:
    compact = surface.strip().replace("%", "").replace(" ", "").replace(",", ".")
    try:
        result = Decimal(compact)
    except InvalidOperation as exc:
        raise _error(f"visible percentage transcription is invalid: {surface}") from exc
    if not result.is_finite():
        raise _error("visible percentage transcription is non-finite")
    return result


def _numeric_value(surface: str, lane_type: str) -> int | Decimal:
    return _money(surface) if lane_type == "MONEY" else _percent(surface)


def _date_key(value: str) -> tuple[int, int, int] | None:
    match = re.search(r"\b(\d{1,2})\s*[./-]\s*(\d{1,2})\s*[./-]\s*(\d{4})\b", value)
    if match is None:
        return None
    return tuple(int(item) for item in match.groups())  # type: ignore[return-value]


def _verify_axes_and_units(graph: Mapping[str, Any], review: Mapping[str, Any]) -> None:
    axes = graph.get("period_axis")
    if type(axes) is not list or len(axes) != 2:
        raise _error("unique graph period denominator drifted")
    for axis, pixel in zip(axes, review["period_pixel_transcriptions"], strict=True):
        if type(axis) is not dict or type(axis.get("period")) is not str:
            raise _error("unique graph period identity drifted")
        semantic = axis["period"]
        semantic_date = _date_key(semantic)
        pixel_date = _date_key(pixel)
        if semantic_date is not None or pixel_date is not None:
            if semantic_date is None or semantic_date != pixel_date:
                raise _error("review and unique graph exact periods disagree")
            continue
        expected = {
            "CURRENT_PERIOD_END": "so cuoi ky",
            "COMPARATIVE_PERIOD_START": "so dau ky",
        }.get(semantic)
        if expected is None or expected not in normalize_vietnamese_anchor_v1(pixel):
            raise _error("review and unique graph relative periods disagree")
    lanes = graph.get("lane_types")
    units = review["unit_pixel_transcriptions"]
    if type(lanes) is not list or len(lanes) != len(units):
        raise _error("review and unique graph unit denominator drifted")
    unit_scope = graph.get("unit_scope")
    if type(unit_scope) is not dict or unit_scope.get("mode") not in {
        "INHERITED_DOCUMENT_MONEY_UNIT",
        "LOCAL_PER_LANE",
    }:
        raise _error("unique graph unit scope drifted")
    for lane, unit in zip(lanes, units, strict=True):
        normalized = normalize_vietnamese_anchor_v1(unit)
        inherited_marker = unit == "INHERITED_DOCUMENT_MILLION_VND"
        if inherited_marker and unit_scope["mode"] != "INHERITED_DOCUMENT_MONEY_UNIT":
            raise _error("review inherited-unit marker lacks document evidence")
        if (lane == "MONEY" and "trieu" not in normalized and not inherited_marker) or (
            lane == "PERCENT" and unit.strip() != "%"
        ):
            raise _error("review and unique graph typed units disagree")
    if unit_scope["mode"] == "LOCAL_PER_LANE" and unit_scope.get("surfaces") != units:
        raise _error("review and unique graph local unit surfaces disagree")
    if unit_scope["mode"] == "INHERITED_DOCUMENT_MONEY_UNIT":
        inherited = unit_scope.get("surface")
        if type(inherited) is not str or "trieu" not in normalize_vietnamese_anchor_v1(inherited):
            raise _error("unique graph inherited million-unit evidence drifted")


def _render_sha(page: Mapping[str, Any]) -> str:
    binding = page.get("render_binding")
    if type(binding) is not dict:
        raise _error("full-document render binding drifted")
    return _sha256(binding.get("sha256"), "full-document render")


def _document_by_bank(documents: Sequence[Mapping[str, Any]], bank_code: str) -> Mapping[str, Any]:
    matches = [document for document in documents if document.get("bank_code") == bank_code]
    if len(matches) != 1:
        raise _error("full-document bank provenance denominator drifted")
    return matches[0]


def _page_by_physical(document: Mapping[str, Any], physical_page: int) -> Mapping[str, Any]:
    pages = document.get("pages")
    if type(pages) is not list:
        raise _error("full-document page inventory drifted")
    matches = [page for page in pages if page.get("physical_page") == physical_page]
    if len(matches) != 1:
        raise _error("review physical page is not unique in the bound document")
    return matches[0]


def _schema(schema_by_id: Mapping[int, Any]) -> dict[str, Any]:
    ids = {716, 717, *[binding[0] for binding in _ROLE_BINDINGS.values()], 720, 746, 752, 727, 766}
    if any(schema_id not in schema_by_id for schema_id in ids):
        raise _error("live TM schema is missing loan-type hierarchy or negative controls")
    owner = schema_by_id[716]
    parent = schema_by_id[717]
    expected_children = [718, 719, 720, 721, 722, 723, 724, 725, 726, 5745]
    if (
        owner.canonical_name != "Cho vay khách hàng"
        or list(owner.children) != [717, 727, 746, 752, 756, 759, 766]
        or parent.canonical_name != "Phân tích theo loại hình cho vay"
        or parent.parent_id != 716
        or parent.display_order != 158
        or list(parent.children) != expected_children
    ):
        raise _error("live customer-loan type hierarchy drifted")
    expected_orders = {
        718: 159,
        719: 160,
        720: 161,
        721: 162,
        722: 163,
        723: 164,
        724: 165,
        725: 166,
        726: 167,
        5745: 168,
    }
    roles: dict[str, dict[str, Any]] = {}
    for role, (schema_id, canonical_name, _aliases) in _ROLE_BINDINGS.items():
        item = schema_by_id[schema_id]
        if (
            item.canonical_name != canonical_name
            or item.parent_id != 717
            or item.display_order != expected_orders[schema_id]
            or item.statement_type != "TM"
            or "CONSOLIDATED" not in item.scope
        ):
            raise _error(f"live TM loan-type role {schema_id} drifted")
        roles[role] = {
            "canonical_name": canonical_name,
            "display_order": item.display_order,
            "report_norm_id": schema_id,
            "schema_parent_report_norm_id": 717,
        }
    if (
        schema_by_id[720].canonical_name
        != "+ Cho vay từ nguồn vốn từ Chính phủ, các tổ chức quốc tế khác"
    ):
        raise _error("live government-funded schema semantics drifted")
    negative: list[dict[str, Any]] = []
    for sibling_id in (746, 752, 727, 766):
        sibling = schema_by_id[sibling_id]
        if sibling.parent_id != 716 or not sibling.children:
            raise _error("live customer-loan negative sibling family drifted")
        negative.append(
            {
                "candidate_parent_report_norm_id": sibling_id,
                "owner_report_norm_id": 716,
                "role_report_norm_ids": list(sibling.children),
            }
        )
    return {"negative_families": negative, "roles": roles}


def _graph_cell(
    graph_cell: Mapping[str, Any],
    review_cell: Mapping[str, Any],
    disagreements: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], int | Decimal]:
    if graph_cell.get("lane_type") != review_cell["lane_type"]:
        raise _error("review and unique graph cell lane types disagree")
    lane_type = review_cell["lane_type"]
    if review_cell["status"] == "DASH":
        if (
            graph_cell.get("status") != "SEMANTIC_CELL_ABSENT_NOT_IMPUTED"
            or graph_cell.get("semantic_surface") is not None
            or graph_cell.get("source_line_index") is not None
        ):
            raise _error("visible DASH was not preserved as one absent semantic cell")
        parsed: int | Decimal = 0 if lane_type == "MONEY" else Decimal(0)
    else:
        semantic = graph_cell.get("semantic_surface")
        if (
            graph_cell.get("status") != "SEMANTIC_PROPOSAL_ONLY"
            or type(semantic) is not str
            or type(graph_cell.get("source_line_index")) is not int
        ):
            raise _error("visible value lacks one ordered fresh VietOCR proposal")
        parsed = _numeric_value(review_cell["pixel_transcription"], lane_type)
        proposal = _numeric_value(semantic, lane_type)
        if proposal != parsed and not _has_disagreement(
            disagreements, semantic, review_cell["pixel_transcription"]
        ):
            raise _error("fresh VietOCR/pixel numeric conflict lacks explicit disposition")
    output = {
        "independent_pixel_transcription": review_cell["pixel_transcription"],
        "lane_index": graph_cell["lane_index"],
        "lane_type": lane_type,
        "semantic_proposal": graph_cell.get("semantic_surface"),
        "source_cell_status": review_cell["status"],
        "source_line_index": graph_cell.get("source_line_index"),
    }
    return output, parsed


def _total_cells(
    graph_cells: Any,
    review_cells: Any,
    disagreements: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[int | Decimal]]:
    if (
        type(graph_cells) is not list
        or type(review_cells) is not list
        or len(graph_cells) != len(review_cells)
    ):
        raise _error("review and unique graph total denominator drifted")
    output: list[dict[str, Any]] = []
    parsed: list[int | Decimal] = []
    for graph_cell, review_cell in zip(graph_cells, review_cells, strict=True):
        item, value = _graph_cell(graph_cell, review_cell, disagreements)
        if item["source_cell_status"] != "VALUE":
            raise _error("visible total cannot be a DASH")
        output.append(item)
        parsed.append(value)
    return output, parsed


def build_loan_type_8bank_codex_verified_mapping_v1(
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
    """Derive bounded verified mappings from exact live inputs and pixel review."""

    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if axis["semantic_axis_sha256"] != EXPECTED_AXIS_SHA256:
        raise _error("full-document semantic axis identity drifted")
    reviewed = _review(review)
    if review_sha256 != REVIEW_SHA256:
        raise _error("Codex pixel review content identity drifted")
    _sha256(crop_manifest_sha256, "crop manifest")
    if type(crop_manifest) is not dict or type(crop_manifest.get("documents")) is not list:
        raise _error("full-document crop manifest shape drifted")
    expected_scan_metrics = {
        "accepted_numeric_graph_count": 0,
        "document_count": 8,
        "document_unique_structural_match_count": 8,
        "mapping_verified_count": 0,
        "near_region_count": 43,
        "owner_table_region_count": 8,
        "semantic_proposal_accounting_corroborated_lane_count": 14,
        "structure_resolved_numeric_unresolved_count": 8,
        "unresolved_document_count": 0,
    }
    if (
        type(structure_scan) is not dict
        or type(structure_scan.get("trials")) is not list
        or not same_typed_json_v1(structure_scan.get("metrics"), expected_scan_metrics)
    ):
        raise _error("full-document loan-type scan denominator drifted")
    if type(schema_authority) is not dict:
        raise _error("live TM schema authority projection drifted")
    schema = _schema(schema_by_id)
    documents = crop_manifest["documents"]
    if len(documents) != 8:
        raise _error("full-document crop-manifest denominator drifted")

    trials: list[dict[str, Any]] = []
    for ordinal, (bank_review, expected_bank) in enumerate(
        zip(reviewed["banks"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        manifest_document = _document_by_bank(documents, expected_bank)
        target_page = _page_by_physical(manifest_document, bank_review["physical_page"])
        if _render_sha(target_page) != bank_review["target_render_sha256"]:
            raise _error("review target render does not bind the crop manifest")
        context = bank_review["statement_context_evidence"]
        context_page = _page_by_physical(manifest_document, context["physical_page"])
        if _render_sha(context_page) != context["render_sha256"]:
            raise _error("review statement-context render does not bind the crop manifest")
        context_key = normalize_vietnamese_anchor_v1(context["pixel_transcription"])
        if "bao cao tai chinh" not in context_key or "hop nhat" not in context_key:
            raise _error("review statement context is not visibly consolidated")

        scan_trials = [
            trial
            for trial in structure_scan["trials"]
            if trial.get("document_provenance") == expected_bank
        ]
        if len(scan_trials) != 1:
            raise _error("structure scan document denominator drifted")
        matcher = scan_trials[0]["matcher_result"]
        graphs = matcher.get("graphs")
        if (
            matcher.get("uniqueness", {}).get("status") != "UNIQUE_FULL_MATCH"
            or type(graphs) is not list
            or len(graphs) != 1
        ):
            raise _error("review target is not the unique complete-PDF loan-type graph")
        graph = graphs[0]
        disagreements = bank_review["transformer_disagreements"]
        if (
            graph.get("page_sequence") != bank_review["physical_page"]
            or graph.get("status") != "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"
            or graph.get("context_complete") is not True
            or graph.get("unresolved_reasons") != []
            or graph.get("branch")
            != {
                "mode": "IMPLICIT_OWNER_IMMEDIATE_TYPED_TABLE",
                "schema_concept": "PHAN_TICH_THEO_LOAI_HINH_CHO_VAY",
            }
            or not _surface_compatible(
                graph["owner"]["surface"],
                bank_review["owner_pixel_transcription"],
                _OWNER_ALIASES,
                disagreements,
            )
        ):
            raise _error("review owner/context does not reconcile with the unique graph")
        _verify_axes_and_units(graph, bank_review)
        if graph.get("layout_mode") not in {"TWO_MONEY_LANES", "MONEY_PERCENT_COMPANION_LANES"}:
            raise _error("unique loan-type graph layout mode drifted")
        graph_rows = graph.get("rows")
        if type(graph_rows) is not list or len(graph_rows) != len(bank_review["rows"]):
            raise _error("review and unique graph row denominator drifted")

        verified: list[dict[str, Any]] = []
        unresolved: list[dict[str, Any]] = []
        parsed_rows: list[list[int | Decimal]] = []
        for graph_row, review_row in zip(graph_rows, bank_review["rows"], strict=True):
            role = review_row["role"]
            if graph_row.get("role") != role:
                raise _error("review and unique graph ordered roles disagree")
            aliases = (
                _ROLE_BINDINGS[role][2] if role in _ROLE_BINDINGS else _UNRESOLVED_ROLES[role][2]
            )
            semantic_label = graph_row.get("label", {}).get("surface")
            if type(semantic_label) is not str or not _surface_compatible(
                semantic_label, review_row["pixel_label"], aliases, disagreements
            ):
                raise _error(f"review label does not reconcile for {expected_bank} {role}")
            graph_cells = graph_row.get("values")
            if type(graph_cells) is not list or len(graph_cells) != len(review_row["cells"]):
                raise _error("review and unique graph row-cell denominator drifted")
            cells: list[dict[str, Any]] = []
            parsed: list[int | Decimal] = []
            for graph_cell, review_cell in zip(graph_cells, review_row["cells"], strict=True):
                output_cell, parsed_cell = _graph_cell(graph_cell, review_cell, disagreements)
                cells.append(output_cell)
                parsed.append(parsed_cell)
            parsed_rows.append(parsed)
            if role in _ROLE_BINDINGS:
                binding = schema["roles"][role]
                money_values: list[dict[str, Any]] = []
                percentages: list[dict[str, Any]] = []
                money_axis = percent_axis = 0
                for cell in cells:
                    if cell["lane_type"] == "MONEY":
                        money_values.append(
                            {
                                **cell,
                                "axis_index": money_axis,
                                "period_pixel_transcription": bank_review[
                                    "period_pixel_transcriptions"
                                ][money_axis],
                            }
                        )
                        money_axis += 1
                    else:
                        percentages.append(
                            {
                                **cell,
                                "axis_index": percent_axis,
                                "period_pixel_transcription": bank_review[
                                    "period_pixel_transcriptions"
                                ][percent_axis],
                            }
                        )
                        percent_axis += 1
                if money_axis != 2 or percent_axis not in {0, 2}:
                    raise _error("mapped row money/percentage axis denominator drifted")
                verified.append(
                    {
                        **binding,
                        "independent_pixel_label": review_row["pixel_label"],
                        "money_values": money_values,
                        "percentage_corroboration": percentages,
                        "role": role,
                        "semantic_proposal_label": semantic_label,
                        "status": "VERIFIED_BY_CODEX",
                    }
                )
            else:
                candidate_id, status, _aliases = _UNRESOLVED_ROLES[role]
                unresolved.append(
                    {
                        "candidate_report_norm_id": candidate_id,
                        "cells": cells,
                        "independent_pixel_label": review_row["pixel_label"],
                        "role": role,
                        "semantic_proposal_label": semantic_label,
                        "status": status,
                        "whole_document_absence_claim": False,
                    }
                )

        source_total, parsed_total = _total_cells(
            graph.get("total"), bank_review["source_only_total"], disagreements
        )
        for lane_index, lane_type in enumerate(graph["lane_types"]):
            expected = sum(row[lane_index] for row in parsed_rows)
            if expected != parsed_total[lane_index]:
                raise _error(f"independent visible {lane_type} final-total equation does not close")
        if any(
            parsed_total[index] != Decimal(100)
            for index, lane in enumerate(graph["lane_types"])
            if lane == "PERCENT"
        ):
            raise _error("independent visible percentage total is not exactly 100")

        graph_intermediate = graph.get("intermediate_totals")
        review_intermediate = bank_review["intermediate_totals"]
        if type(graph_intermediate) is not list or len(graph_intermediate) != len(
            review_intermediate
        ):
            raise _error("review and unique graph intermediate-total denominator drifted")
        intermediate: list[dict[str, Any]] = []
        for graph_total, review_total in zip(graph_intermediate, review_intermediate, strict=True):
            values, parsed = _total_cells(graph_total, review_total, disagreements)
            margin_indices = [
                index
                for index, row in enumerate(bank_review["rows"])
                if row["role"] == "MARGIN_AND_SECURITIES_ADVANCE"
            ]
            if len(margin_indices) != 1:
                raise _error("intermediate subtotal lacks one unique following margin row")
            margin_index = margin_indices[0]
            for lane_index in range(len(parsed)):
                expected = sum(row[lane_index] for row in parsed_rows[:margin_index])
                if parsed[lane_index] != expected:
                    raise _error("independent visible core subtotal equation does not close")
            intermediate.append({"status": "VERIFIED_SOURCE_ONLY_CORE_SUBTOTAL", "values": values})

        negative_controls = [
            {
                **control,
                "status": "EXCLUDED_DISTINCT_SIBLING_FAMILY_BY_CHILD_ROLE_TOTAL_TOPOLOGY",
                "whole_document_absence_claim": False,
            }
            for control in schema["negative_families"]
        ]
        trials.append(
            {
                "bank_provenance": expected_bank,
                "document_ordinal": ordinal,
                "intermediate_totals": intermediate,
                "layout_mode": graph["layout_mode"],
                "negative_family_controls": negative_controls,
                "observed_role_order": [row["role"] for row in bank_review["rows"]],
                "physical_page": bank_review["physical_page"],
                "source_only_total": {
                    "report_norm_id": None,
                    "status": "VERIFIED_SOURCE_ONLY",
                    "values": source_total,
                },
                "statement_context": canonical_clone_v1(context),
                "status": "VERIFIED_BY_CODEX",
                "target_render_sha256": bank_review["target_render_sha256"],
                "transformer_disagreements": canonical_clone_v1(disagreements),
                "unresolved_rows": unresolved,
                "verified_mappings": verified,
            }
        )

    metrics = {
        "document_count": 8,
        "document_unique_structure_count": 8,
        "intermediate_source_only_total_verified_count": sum(
            len(trial["intermediate_totals"]) for trial in trials
        ),
        "mapped_dash_cell_count": sum(
            value["source_cell_status"] == "DASH"
            for trial in trials
            for mapping in trial["verified_mappings"]
            for value in mapping["money_values"]
        ),
        "mapped_item_verified_by_codex_count": sum(
            len(trial["verified_mappings"]) for trial in trials
        ),
        "mapped_money_value_cell_count": sum(
            value["source_cell_status"] == "VALUE"
            for trial in trials
            for mapping in trial["verified_mappings"]
            for value in mapping["money_values"]
        ),
        "mapped_percentage_corroboration_cell_count": sum(
            len(mapping["percentage_corroboration"])
            for trial in trials
            for mapping in trial["verified_mappings"]
        ),
        "negative_family_control_count": sum(
            len(trial["negative_family_controls"]) for trial in trials
        ),
        "source_only_total_verified_count": 8,
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
        "state": "LOAN_TYPE_8BANK_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "lt8bcv1:result:" + canonical_json_sha256_v1(material)}
    )


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("verified loan-type result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "LOAN_TYPE_8BANK_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or type(value["metrics"]) is not dict
        or type(value["input_refs"]) is not dict
    ):
        raise _error("verified loan-type result identity/authority drifted")
    clone = canonical_clone_v1(value)
    result_id = clone.pop("result_id")
    if result_id != "lt8bcv1:result:" + canonical_json_sha256_v1(clone):
        raise _error("verified loan-type result identity drifted")
    trial_fields = {
        "bank_provenance",
        "document_ordinal",
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
    }
    mapping_fields = {
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
    mapped = money = dash = percent = negative = unresolved = intermediate = disagreements = 0
    for ordinal, (trial, expected_bank) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or set(trial) != trial_fields
            or trial["bank_provenance"] != expected_bank
            or type(trial["document_ordinal"]) is not int
            or trial["document_ordinal"] != ordinal
            or type(trial["physical_page"]) is not int
            or trial["physical_page"] <= 0
            or trial["status"] != "VERIFIED_BY_CODEX"
            or trial["layout_mode"] not in {"TWO_MONEY_LANES", "MONEY_PERCENT_COMPANION_LANES"}
            or type(trial["verified_mappings"]) is not list
            or type(trial["unresolved_rows"]) is not list
            or type(trial["negative_family_controls"]) is not list
            or len(trial["negative_family_controls"]) != 4
            or type(trial["intermediate_totals"]) is not list
            or type(trial["transformer_disagreements"]) is not list
        ):
            raise _error("verified loan-type trial shape/status drifted")
        _sha256(trial["target_render_sha256"], "verified target render")
        seen_ids: set[int] = set()
        for mapping in trial["verified_mappings"]:
            if (
                type(mapping) is not dict
                or set(mapping) != mapping_fields
                or mapping["status"] != "VERIFIED_BY_CODEX"
                or mapping["schema_parent_report_norm_id"] != 717
                or type(mapping["report_norm_id"]) is not int
                or mapping["report_norm_id"] in seen_ids
                or type(mapping["display_order"]) is not int
                or type(mapping["money_values"]) is not list
                or len(mapping["money_values"]) != 2
                or type(mapping["percentage_corroboration"]) is not list
                or len(mapping["percentage_corroboration"]) not in {0, 2}
            ):
                raise _error("verified loan-type mapping shape/status drifted")
            seen_ids.add(mapping["report_norm_id"])
            for cell in [*mapping["money_values"], *mapping["percentage_corroboration"]]:
                if type(cell) is not dict or set(cell) != {
                    "axis_index",
                    "independent_pixel_transcription",
                    "lane_index",
                    "lane_type",
                    "period_pixel_transcription",
                    "semantic_proposal",
                    "source_cell_status",
                    "source_line_index",
                }:
                    raise _error("verified loan-type mapped cell fields drifted")
                if type(cell["axis_index"]) is not int or cell["axis_index"] not in {0, 1}:
                    raise _error("verified loan-type mapped cell axis drifted")
                if cell["source_cell_status"] == "DASH":
                    if (
                        cell["semantic_proposal"] is not None
                        or cell["source_line_index"] is not None
                    ):
                        raise _error("verified DASH cell was laundered into a numeric proposal")
                    dash += 1
                elif cell["source_cell_status"] == "VALUE":
                    if (
                        type(cell["semantic_proposal"]) is not str
                        or type(cell["source_line_index"]) is not int
                    ):
                        raise _error("verified VALUE cell semantic binding drifted")
                    if cell["lane_type"] == "MONEY":
                        money += 1
                else:
                    raise _error("verified source-cell status drifted")
                if cell["lane_type"] == "PERCENT":
                    percent += 1
            mapped += 1
        for item in trial["unresolved_rows"]:
            if (
                type(item) is not dict
                or set(item)
                != {
                    "candidate_report_norm_id",
                    "cells",
                    "independent_pixel_label",
                    "role",
                    "semantic_proposal_label",
                    "status",
                    "whole_document_absence_claim",
                }
                or item["whole_document_absence_claim"] is not False
                or item["status"]
                not in {
                    "UNRESOLVED_BROADER_CREDIT_SCOPE_NOT_EQUIVALENT_TO_OTHER_LOANS",
                    "UNRESOLVED_SOURCE_LABEL_NOT_EQUIVALENT_TO_SCHEMA_FUNDED_SOURCE",
                }
            ):
                raise _error("verified loan-type unresolved row shape/status drifted")
            unresolved += 1
        negative += len(trial["negative_family_controls"])
        intermediate += len(trial["intermediate_totals"])
        disagreements += len(trial["transformer_disagreements"])
    expected_metrics = {
        "document_count": 8,
        "document_unique_structure_count": 8,
        "intermediate_source_only_total_verified_count": intermediate,
        "mapped_dash_cell_count": dash,
        "mapped_item_verified_by_codex_count": mapped,
        "mapped_money_value_cell_count": money,
        "mapped_percentage_corroboration_cell_count": percent,
        "negative_family_control_count": negative,
        "source_only_total_verified_count": 8,
        "transformer_disagreement_preserved_count": disagreements,
        "unresolved_schema_semantic_row_count": unresolved,
    }
    if not same_typed_json_v1(value["metrics"], expected_metrics):
        raise _error("verified loan-type metrics drifted")
    return canonical_clone_v1(value)


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load required experiment module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _live_inputs() -> tuple[Any, Any, Any, Any, Any, Mapping[int, Any], str]:
    builder = _load_module(
        PROJECT_ROOT
        / "scripts/experiments/build_loan_maturity_full_document_vietocr_request_v1.py",
        "full_document_vietocr_builder_for_loan_type_codex_mapping_v1",
    )
    semantic_index = builder.read_verified_vietocr_proposals_v1()
    index_raw = _fixed_bytes(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    if not same_typed_json_v1(_json_bytes(index_raw, "semantic index"), semantic_index):
        raise _error("semantic index bytes and authenticated projection disagree")
    freeze = builder.verify_full_document_freeze_v1(replay_geometry=False)
    manifest_sha256 = _sha256(freeze["manifest_sha256"], "verified crop manifest")
    manifest = _json_bytes(_fixed_bytes(CROP_MANIFEST_PATH, manifest_sha256), "crop manifest")
    scanner = _load_module(
        PROJECT_ROOT / "scripts/experiments/scan_loan_type_full_document_vietocr_v1.py",
        "full_document_loan_type_scan_for_codex_mapping_v1",
    )
    structure_scan = scanner.build_loan_type_full_document_scan_v1(semantic_index)
    review = _review(_json_bytes(_fixed_bytes(REVIEW_PATH, REVIEW_SHA256), "Codex pixel review"))
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return (
        semantic_index,
        manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        manifest_sha256,
    )


def build_live_loan_type_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    """Replay every fixed input and derive the bounded eight-bank mapping."""

    semantic_index, manifest, scan, review, authority, schema_by_id, manifest_sha = _live_inputs()
    return build_loan_type_8bank_codex_verified_mapping_v1(
        semantic_index,
        manifest,
        scan,
        review,
        authority,
        schema_by_id,
        crop_manifest_sha256=manifest_sha,
        review_sha256=REVIEW_SHA256,
    )


def validate_loan_type_8bank_codex_verified_mapping_replay_v1(value: Any) -> dict[str, Any]:
    """Exact-rebuild a persisted result from every fixed live input."""

    persisted = _validate_result(value)
    rebuilt = build_live_loan_type_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("verified loan-type result does not replay exactly")
    return rebuilt


def main() -> int:
    print(
        json.dumps(
            build_live_loan_type_8bank_codex_verified_mapping_v1(),
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
