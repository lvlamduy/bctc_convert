"""Verify eight loan-quality graphs from fresh VietOCR and independent pixels.

The bank-blind matcher scans each complete PDF and must find one unique graph.
This module then binds that graph to a fixed Codex review of the actual PDF
pixels, recomputes the five-grade accounting closure, and checks the live TM
schema hierarchy.  Final statuses are derived here; the review cannot supply
them.  VietOCR text is anchor evidence only and never numeric truth.
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
    "LoanQuality8BankCodexVerifiedMappingV1Error",
    "build_live_loan_quality_8bank_codex_verified_mapping_v1",
    "build_loan_quality_8bank_codex_verified_mapping_v1",
    "validate_loan_quality_8bank_codex_verified_mapping_replay_v1",
]


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "LOAN_QUALITY_8BANK_CODEX_VERIFIED_MAPPING_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_UNIQUE_FULL_PDF_VIETOCR_STRUCTURE_PLUS_PINNED_CODEX_"
    "PIXEL_REVIEW_FIVE_GRADE_ACCOUNTING_CLOSURE_AND_LIVE_TM_SCHEMA_ONLY_NO_"
    "BROAD_CORPUS_CANONICALIZATION_EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0052-loan-quality-8bank-codex-pixel-review-v1.json")
REVIEW_SHA256 = "8be7b1d229449fef4f9c26e12169313b2746a60968f5038e8377ee8609e91c81"
SEMANTIC_INDEX_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/verified-index/semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_AXIS_SHA256 = "e99873cd16a7234702d0ee6e5fa9eb37637a1a75621228381e3dbcd7c5cfdcca"
_ROLE_BINDINGS = (
    ("STANDARD", 747, "+ Nhóm 1: Nợ đủ tiêu chuẩn"),
    ("SPECIAL_MENTION", 748, "+ Nhóm 2: Nợ cần chú ý"),
    ("SUBSTANDARD", 749, "+ Nhóm 3: Nợ dưới tiêu chuẩn"),
    ("DOUBTFUL", 750, "+ Nhóm 4: Nợ nghi ngờ"),
    ("LOSS", 751, "+ Nhóm 5: Nợ có khả năng mất vốn"),
)
_ROLE_ALIASES = {
    "STANDARD": ("Nợ đủ tiêu chuẩn", "Nhóm 1 Nợ đủ tiêu chuẩn", "Nợ nhóm 1"),
    "SPECIAL_MENTION": ("Nợ cần chú ý", "Nhóm 2 Nợ cần chú ý", "Nợ nhóm 2"),
    "SUBSTANDARD": ("Nợ dưới tiêu chuẩn", "Nhóm 3 Nợ dưới tiêu chuẩn", "Nợ nhóm 3"),
    "DOUBTFUL": ("Nợ nghi ngờ", "Nhóm 4 Nợ nghi ngờ", "Nợ nhóm 4"),
    "LOSS": (
        "Nợ có khả năng mất vốn",
        "Nhóm 5 Nợ có khả năng mất vốn",
        "Nợ nhóm 5",
    ),
}
_BRANCH_ALIASES = (
    "Phân tích chất lượng nợ cho vay",
    "Phân tích chất lượng dư nợ cho vay khách hàng",
    "Phân tích dư nợ cho vay theo chất lượng nợ",
    "Phân loại chất lượng tài sản có rủi ro tín dụng",
)
_OWNER_ALIASES = (
    "Cho vay khách hàng",
    "Dư nợ cho vay khách hàng",
    "Các khoản cho vay khách hàng",
    "Rủi ro tín dụng",
)
_EXPECTED_REVIEW_CHECKS = {
    "all_eight_complete_pdfs_scanned_and_unique_full_region_confirmed": True,
    "branch_owner_children_order_and_geometry_visually_confirmed": True,
    "five_grade_accounting_equations_independently_recomputed": True,
    "optional_additive_and_nonadditive_population_boundaries_confirmed": True,
    "period_unit_and_consolidated_scope_visually_confirmed": True,
    "source_pdf_and_bound_render_opened": True,
    "stacked_sparse_customer_loan_column_and_totals_confirmed": True,
    "wrong_owner_securities_and_other_asset_families_checked_as_negative_controls": True,
}
_EXPECTED_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_mapping_rule": False,
    "blank_sparse_cells_imputed_as_zero": False,
    "broad_corpus_authority": False,
    "canonicalization_or_export_authority": False,
    "legacy_ocr_text_used_for_semantic_matching": False,
    "reviewer_final_status_supplied": False,
    "semantic_similarity_alone_used_for_mapping": False,
    "transformer_numeric_proposal_used_as_pixel_truth": False,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_mapping_rule": False,
    "broad_corpus_authority": False,
    "canonicalization_or_export_authority": False,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_pdf_pixel_transcription_used_for_numeric_truth": True,
    "live_tm_schema_hierarchy_and_negative_families_checked": True,
    "mapping_authority_is_bounded_to_reviewed_source_rows": True,
    "old_ocr_transcript_used_for_semantic_matching": False,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "sparse_blank_cells_imputed_as_zero": False,
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


class LoanQuality8BankCodexVerifiedMappingV1Error(ValueError):
    """The review, graph, accounting equation, or TM schema drifted."""


def _error(message: str) -> LoanQuality8BankCodexVerifiedMappingV1Error:
    return LoanQuality8BankCodexVerifiedMappingV1Error(message)


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
        raise _error(f"{label} list denominator drifted")
    return [_text(item, f"{label} item") for item in value]


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
        raise _error("Codex quality review top-level fields drifted")
    if (
        value["format_version"] != "LOAN_QUALITY_8BANK_CODEX_PIXEL_REVIEW_V1"
        or value["state"] != "CODEX_PIXEL_REVIEW_COMPLETE"
        or value["semantic_index_sha256"] != EXPECTED_INDEX_SHA256
        or value["semantic_axis_sha256"] != EXPECTED_AXIS_SHA256
        or not same_typed_json_v1(value["review_checks"], _EXPECTED_REVIEW_CHECKS)
        or not same_typed_json_v1(value["safety"], _EXPECTED_REVIEW_SAFETY)
        or type(value["banks"]) is not list
        or len(value["banks"]) != len(EXPECTED_DOCUMENT_ORDER)
        or type(value["reviewer"]) is not dict
        or set(value["reviewer"]) != {"kind", "review_run_id"}
        or value["reviewer"]["kind"] != "CODEX_INDEPENDENT_PDF_PIXEL_AND_ACCOUNTING_REVIEW"
    ):
        raise _error("Codex quality review identity, denominator, or safety drifted")
    _text(value["claim_boundary"], "review claim boundary")
    _text(value["reviewer"]["review_run_id"], "review run ID")
    bank_fields = {
        "bank_code",
        "branch_pixel_transcription",
        "nonadditive_standard_child",
        "optional_additive_population",
        "owner_evidence",
        "period_pixel_transcriptions",
        "physical_page",
        "rows",
        "selected_population",
        "source_only_total",
        "statement_context_evidence",
        "target_render_sha256",
        "transformer_disagreements",
        "unit_pixel_transcriptions",
    }
    for offset, (bank, expected_bank) in enumerate(
        zip(value["banks"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if type(bank) is not dict or set(bank) != bank_fields or bank["bank_code"] != expected_bank:
            raise _error(f"review bank {offset} fields/order drifted")
        _positive_int(bank["physical_page"], "review physical page")
        _sha256(bank["target_render_sha256"], "review target render")
        _text(bank["branch_pixel_transcription"], "review branch pixel text")
        _string_list(bank["period_pixel_transcriptions"], "review periods", length=2)
        _string_list(bank["unit_pixel_transcriptions"], "review units", length=2)
        _string_list(bank["source_only_total"], "review source total", length=2)
        for evidence_key in ("owner_evidence", "statement_context_evidence"):
            evidence = bank[evidence_key]
            expected = {"physical_page", "pixel_transcription", "render_sha256"}
            if evidence_key == "statement_context_evidence":
                expected |= {"mode", "report_scope"}
            if type(evidence) is not dict or set(evidence) != expected:
                raise _error(f"review {evidence_key} fields drifted")
            _positive_int(evidence["physical_page"], f"review {evidence_key} page")
            _sha256(evidence["render_sha256"], f"review {evidence_key} render")
            _text(evidence["pixel_transcription"], f"review {evidence_key} text")
        context = bank["statement_context_evidence"]
        if (
            context["mode"]
            not in {"PAGE_LOCAL_VISIBLE_HEADING", "DOCUMENT_PRECEDING_VISIBLE_HEADING"}
            or context["report_scope"] != "CONSOLIDATED"
            or context["physical_page"] > bank["physical_page"]
        ):
            raise _error("review statement scope/order drifted")
        population = bank["selected_population"]
        if type(population) is not dict or set(population) != {
            "customer_loan_column_index",
            "mapping_owner_pixel",
            "mode",
            "total_column_index",
        }:
            raise _error("review selected population fields drifted")
        if population["mode"] not in {
            "HORIZONTAL_TYPED_PERIOD_LANES",
            "STACKED_PERIOD_BLOCKS_MULTI_ASSET_COLUMNS",
        }:
            raise _error("review layout mode drifted")
        _text(population["mapping_owner_pixel"], "review mapping owner")
        if population["mode"] == "HORIZONTAL_TYPED_PERIOD_LANES":
            if (
                population["customer_loan_column_index"] is not None
                or population["total_column_index"] is not None
            ):
                raise _error("horizontal review unexpectedly pins stacked columns")
        elif (
            type(population["customer_loan_column_index"]) is not int
            or type(population["total_column_index"]) is not int
            or population["customer_loan_column_index"] < 0
            or population["total_column_index"] <= population["customer_loan_column_index"]
        ):
            raise _error("stacked review column indices drifted")
        if type(bank["rows"]) is not list or len(bank["rows"]) != len(_ROLE_BINDINGS):
            raise _error("review five-grade denominator drifted")
        for row, (role, _schema_id, _name) in zip(bank["rows"], _ROLE_BINDINGS, strict=True):
            if (
                type(row) is not dict
                or set(row) != {"pixel_label", "role", "values"}
                or row["role"] != role
            ):
                raise _error("review row fields/order drifted")
            _text(row["pixel_label"], "review row pixel label")
            _string_list(row["values"], "review row values", length=2)
        for optional_key in ("optional_additive_population", "nonadditive_standard_child"):
            optional = bank[optional_key]
            if optional is not None:
                if type(optional) is not dict or set(optional) != {"pixel_label", "values"}:
                    raise _error(f"review {optional_key} fields drifted")
                _text(optional["pixel_label"], f"review {optional_key} label")
                _string_list(optional["values"], f"review {optional_key} values", length=2)
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
                _text(item, f"review disagreement {key}")
    return canonical_clone_v1(value)


def _money(surface: str) -> int:
    compact = surface.strip().replace(" ", "")
    negative = compact.startswith("(") and compact.endswith(")")
    compact = compact.strip("()").lstrip("+")
    if compact.startswith("-"):
        negative = True
        compact = compact[1:]
    digits = compact.replace(".", "").replace(",", "")
    if not digits.isdigit():
        raise _error(f"pixel money transcription is not one integer: {surface}")
    value = int(digits)
    return -value if negative else value


def _has_disagreement(
    disagreements: Sequence[Mapping[str, Any]], semantic: str, pixel: str
) -> bool:
    return any(
        item.get("semantic_proposal") == semantic and item.get("pixel_transcription") == pixel
        for item in disagreements
    )


def _without_enumeration(value: str) -> str:
    return re.sub(r"^(?:[0-9]+\s+)+", "", normalize_vietnamese_anchor_v1(value))


def _surface_compatible(
    semantic: str,
    pixel: str,
    aliases: Sequence[str],
    disagreements: Sequence[Mapping[str, Any]],
) -> bool:
    semantic_key = _without_enumeration(semantic)
    pixel_key = _without_enumeration(pixel)
    alias_keys = [_without_enumeration(alias) for alias in aliases]
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


def _value(semantic: str, pixel: str, disagreements: Sequence[Mapping[str, Any]]) -> int:
    semantic_value = _money(semantic)
    pixel_value = _money(pixel)
    if semantic_value != pixel_value and not _has_disagreement(disagreements, semantic, pixel):
        raise _error("VietOCR/pixel numeric conflict lacks explicit review disposition")
    return pixel_value


def _date_key(value: str) -> tuple[int, int, int] | None:
    match = re.search(r"\b(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})\b", value)
    if match is None:
        normalized = normalize_vietnamese_anchor_v1(value)
        match = re.search(
            r"\bngay\s+(\d{1,2})\s+thang\s+(\d{1,2})\s+nam\s+(\d{4})\b",
            normalized,
        )
    if match is None:
        return None
    return tuple(int(item) for item in match.groups())  # type: ignore[return-value]


def _verify_axes_and_units(graph: Mapping[str, Any], review: Mapping[str, Any]) -> None:
    axes = graph.get("axes")
    if type(axes) is not list or len(axes) != 2:
        raise _error("unique quality graph period denominator drifted")
    for axis, pixel in zip(axes, review["period_pixel_transcriptions"], strict=True):
        semantic_period = axis.get("period") if type(axis) is dict else None
        if type(semantic_period) is not str:
            raise _error("unique quality graph period identity drifted")
        semantic_date = _date_key(semantic_period)
        pixel_date = _date_key(pixel)
        if semantic_date is not None or pixel_date is not None:
            if semantic_date is None or semantic_date != pixel_date:
                raise _error("review and unique graph exact periods disagree")
            continue
        normalized_pixel = normalize_vietnamese_anchor_v1(pixel)
        expected_relative = {
            "CURRENT_PERIOD_END": "so cuoi ky",
            "COMPARATIVE_PERIOD_START": "so dau ky",
        }.get(semantic_period)
        if expected_relative is None or expected_relative not in normalized_pixel:
            raise _error("review and unique graph relative periods disagree")

    review_units = review["unit_pixel_transcriptions"]
    if any(
        "trieu" not in normalize_vietnamese_anchor_v1(unit)
        or not any(token in normalize_vietnamese_anchor_v1(unit) for token in ("dong", "vnd"))
        for unit in review_units
    ):
        raise _error("review unit pixels are not two monetary million-unit axes")
    unit_scope = graph.get("unit_scope")
    if type(unit_scope) is not dict or unit_scope.get("mode") not in {
        "INHERITED_DOCUMENT_MONEY_UNIT",
        "LOCAL_PER_LANE",
        "LOCAL_SHARED_MONEY_UNIT",
    }:
        raise _error("unique quality graph unit scope drifted")
    semantic_units = unit_scope.get("surfaces")
    if semantic_units is not None:
        if type(semantic_units) is not list or len(semantic_units) != 2:
            raise _error("unique quality graph local unit denominator drifted")
        if any(
            "trieu" not in normalize_vietnamese_anchor_v1(unit)
            for unit in semantic_units
            if type(unit) is str
        ):
            raise _error("unique quality graph local unit semantics drifted")
    inherited_unit = unit_scope.get("surface")
    if inherited_unit is not None and (
        type(inherited_unit) is not str
        or "trieu" not in normalize_vietnamese_anchor_v1(inherited_unit)
    ):
        raise _error("unique quality graph inherited unit semantics drifted")


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
    required = {
        716,
        746,
        747,
        748,
        749,
        750,
        751,
        5746,
        804,
        853,
        854,
        855,
        856,
        857,
        858,
        966,
        1018,
        1019,
        1020,
        1021,
        1022,
        1023,
    }
    if any(schema_id not in schema_by_id for schema_id in required):
        raise _error("live TM schema is missing the quality hierarchy or negative controls")
    owner = schema_by_id[716]
    parent = schema_by_id[746]
    if (
        owner.canonical_name != "Cho vay khách hàng"
        or 746 not in owner.children
        or parent.canonical_name != "Phân tích chất lượng nợ cho vay"
        or parent.parent_id != 716
        or list(parent.children) != [747, 748, 749, 750, 751]
    ):
        raise _error("live customer-loan quality hierarchy drifted")
    mapped: list[dict[str, Any]] = []
    expected_orders = {747: 194, 748: 196, 749: 197, 750: 198, 751: 199}
    for role, schema_id, canonical_name in _ROLE_BINDINGS:
        item = schema_by_id[schema_id]
        if (
            item.canonical_name != canonical_name
            or item.parent_id != 746
            or item.display_order != expected_orders[schema_id]
            or item.statement_type != "TM"
            or "CONSOLIDATED" not in item.scope
        ):
            raise _error(f"live TM loan-quality role {schema_id} drifted")
        mapped.append({"canonical_name": canonical_name, "report_norm_id": schema_id, "role": role})
    child = schema_by_id[5746]
    if (
        child.parent_id != 747
        or child.display_order != 195
        or child.canonical_name
        != "Trong đó: Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán"
    ):
        raise _error("live TM standard-grade nonadditive child drifted")
    negative_families: list[dict[str, Any]] = []
    for parent_id, owner_id, children in (
        (853, 804, [854, 855, 856, 857, 858]),
        (1018, 966, [1019, 1020, 1021, 1022, 1023]),
    ):
        item = schema_by_id[parent_id]
        if item.parent_id != owner_id or list(item.children) != children:
            raise _error("live negative-control quality family drifted")
        negative_families.append(
            {
                "candidate_parent_report_norm_id": parent_id,
                "owner_report_norm_id": owner_id,
                "role_report_norm_ids": children,
            }
        )
    return {
        "mapped_roles": mapped,
        "nonadditive_standard_child": {
            "canonical_name": child.canonical_name,
            "report_norm_id": 5746,
        },
        "negative_families": negative_families,
    }


def _graph_rows(
    graph: Mapping[str, Any], population: Mapping[str, Any]
) -> tuple[list[tuple[Mapping[str, Any], list[Mapping[str, Any]]]], list[Mapping[str, Any]]]:
    if graph.get("layout_mode") != population["mode"]:
        raise _error("review and unique graph layout modes disagree")
    if population["mode"] == "HORIZONTAL_TYPED_PERIOD_LANES":
        rows = graph.get("rows")
        totals = graph.get("totals")
        if type(rows) is not list or type(totals) is not dict:
            raise _error("horizontal quality graph shape drifted")
        total = totals.get("core") or totals.get("grand")
        if type(total) is not list or len(total) != 2:
            raise _error("horizontal quality total denominator drifted")
        return [(row, row["values"]) for row in rows], total

    customer = graph.get("customer_loan_column")
    total_column = graph.get("total_column")
    blocks = graph.get("blocks")
    if (
        type(customer) is not dict
        or type(total_column) is not dict
        or customer.get("column_index") != population["customer_loan_column_index"]
        or total_column.get("column_index") != population["total_column_index"]
        or type(blocks) is not list
        or len(blocks) != 2
        or not _surface_compatible(
            customer["header"]["surface"],
            population["mapping_owner_pixel"],
            ("Cho vay khách hàng",),
            (),
        )
    ):
        raise _error("stacked customer-loan/total column binding drifted")
    by_role: dict[str, tuple[Mapping[str, Any], list[Mapping[str, Any]]]] = {}
    selected_totals: list[Mapping[str, Any]] = []
    target = population["customer_loan_column_index"]
    total_lane = population["total_column_index"]
    for block_offset, block in enumerate(blocks):
        if block.get("block_ordinal") != block_offset or type(block.get("rows")) is not list:
            raise _error("stacked period block identity drifted")
        total_values = block.get("total")
        if type(total_values) is not list:
            raise _error("stacked total vector drifted")
        selected = [value for value in total_values if value.get("lane_index") == target]
        if len(selected) != 1:
            raise _error("stacked customer-loan total is not unique")
        selected_totals.append(selected[0])
        for row in block["rows"]:
            selected_values = [
                value for value in row["values"] if value.get("lane_index") == target
            ]
            total_values_for_row = [
                value for value in row["values"] if value.get("lane_index") == total_lane
            ]
            if len(selected_values) != 1 or len(total_values_for_row) != 1:
                raise _error("stacked sparse row lacks the selected and total populations")
            if block_offset == 0:
                by_role[row["role"]] = (row, [selected_values[0]])
            else:
                if row["role"] not in by_role:
                    raise _error("stacked period roles drifted")
                by_role[row["role"]][1].append(selected_values[0])
    return [by_role[role] for role, _id, _name in _ROLE_BINDINGS], selected_totals


def build_loan_quality_8bank_codex_verified_mapping_v1(
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    review: Any,
    schema_by_id: Mapping[int, Any],
    *,
    review_sha256: str,
) -> dict[str, Any]:
    """Derive bounded verified mappings from exact live inputs and pixel review."""

    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if axis["semantic_axis_sha256"] != EXPECTED_AXIS_SHA256:
        raise _error("full-document semantic axis identity drifted")
    reviewed = _review(review)
    _sha256(review_sha256, "Codex pixel review")
    if type(crop_manifest) is not dict or type(crop_manifest.get("documents")) is not list:
        raise _error("full-document crop manifest shape drifted")
    expected_scan_metrics = {
        "accepted_numeric_graph_count": 0,
        "document_count": 8,
        "document_unique_structural_match_count": 8,
        "mapping_verified_count": 0,
        "near_region_count": 358,
        "ordered_anchor_region_count": 8,
        "structure_resolved_numeric_unresolved_count": 8,
        "unresolved_document_count": 0,
    }
    if (
        type(structure_scan) is not dict
        or type(structure_scan.get("trials")) is not list
        or not same_typed_json_v1(structure_scan.get("metrics"), expected_scan_metrics)
    ):
        raise _error("full-document quality scan denominator drifted")
    schema = _schema(schema_by_id)
    raw_documents = semantic_index.get("documents")
    manifest_documents = crop_manifest["documents"]
    if type(raw_documents) is not list or len(raw_documents) != 8 or len(manifest_documents) != 8:
        raise _error("full-document input denominator drifted")

    trials: list[dict[str, Any]] = []
    for ordinal, (bank_review, expected_bank) in enumerate(
        zip(reviewed["banks"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        _document_by_bank(raw_documents, expected_bank)
        manifest_document = _document_by_bank(manifest_documents, expected_bank)
        target_page = _page_by_physical(manifest_document, bank_review["physical_page"])
        if _render_sha(target_page) != bank_review["target_render_sha256"]:
            raise _error("review target render does not bind the full-document manifest")
        for evidence_key in ("owner_evidence", "statement_context_evidence"):
            evidence = bank_review[evidence_key]
            evidence_page = _page_by_physical(manifest_document, evidence["physical_page"])
            if _render_sha(evidence_page) != evidence["render_sha256"]:
                raise _error(f"review {evidence_key} render does not bind the manifest")
        context_key = normalize_vietnamese_anchor_v1(
            bank_review["statement_context_evidence"]["pixel_transcription"]
        )
        if "bao cao tai chinh" not in context_key or "hop nhat" not in context_key:
            raise _error("review statement context is not visibly consolidated")

        scan_trials = [
            trial
            for trial in structure_scan["trials"]
            if trial.get("document_provenance") == expected_bank
        ]
        if len(scan_trials) != 1:
            raise _error("structure scan bank trial denominator drifted")
        matcher = scan_trials[0]["matcher_result"]
        graphs = matcher.get("graphs")
        if (
            matcher.get("uniqueness", {}).get("status") != "UNIQUE_FULL_MATCH"
            or type(graphs) is not list
            or len(graphs) != 1
        ):
            raise _error("review target is not the unique complete-PDF quality graph")
        graph = graphs[0]
        disagreements = bank_review["transformer_disagreements"]
        if (
            graph.get("page_sequence") != bank_review["physical_page"]
            or graph.get("status") != "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"
            or graph.get("arithmetic_status") != "NOT_EVALUATED_NO_PRIMARY_NUMERIC_AUTHORITY"
            or graph.get("unresolved_reasons") != []
            or not _surface_compatible(
                graph["owner_context"]["surface"],
                bank_review["owner_evidence"]["pixel_transcription"],
                _OWNER_ALIASES,
                disagreements,
            )
            or not _surface_compatible(
                graph["branch"]["surface"],
                bank_review["branch_pixel_transcription"],
                _BRANCH_ALIASES,
                disagreements,
            )
        ):
            raise _error("review context/branch does not reconcile with the unique graph")
        _verify_axes_and_units(graph, bank_review)
        if not _surface_compatible(
            bank_review["selected_population"]["mapping_owner_pixel"],
            bank_review["selected_population"]["mapping_owner_pixel"],
            ("Cho vay khách hàng",),
            (),
        ):
            raise _error("review selected mapping population is not customer loans")

        graph_rows, graph_total = _graph_rows(graph, bank_review["selected_population"])
        if len(graph_rows) != len(_ROLE_BINDINGS):
            raise _error("unique graph five-grade denominator drifted")
        verified_rows: list[dict[str, Any]] = []
        parsed_rows: list[list[int]] = []
        for (graph_row, graph_values), review_row, (role, schema_id, canonical_name) in zip(
            graph_rows, bank_review["rows"], _ROLE_BINDINGS, strict=True
        ):
            semantic_label = graph_row["label"].get("surface") or graph_row["label"].get(
                "label_surface"
            )
            if graph_row["role"] != role or not _surface_compatible(
                semantic_label,
                review_row["pixel_label"],
                _ROLE_ALIASES[role],
                disagreements,
            ):
                raise _error(f"review row label does not reconcile for {expected_bank} {role}")
            if len(graph_values) != 2:
                raise _error("selected graph row period denominator drifted")
            parsed: list[int] = []
            values: list[dict[str, Any]] = []
            for axis_index, (graph_value, pixel_value, period) in enumerate(
                zip(
                    graph_values,
                    review_row["values"],
                    bank_review["period_pixel_transcriptions"],
                    strict=True,
                )
            ):
                parsed.append(_value(graph_value["surface"], pixel_value, disagreements))
                values.append(
                    {
                        "axis_index": axis_index,
                        "independent_pixel_transcription": pixel_value,
                        "lane_type": "MONEY",
                        "period_pixel_transcription": period,
                        "semantic_proposal": graph_value["surface"],
                        "source_line_index": graph_value["source_line_index"],
                    }
                )
            parsed_rows.append(parsed)
            verified_rows.append(
                {
                    "canonical_name": canonical_name,
                    "independent_pixel_label": review_row["pixel_label"],
                    "report_norm_id": schema_id,
                    "role": role,
                    "semantic_proposal_label": semantic_label,
                    "status": "VERIFIED_BY_CODEX",
                    "values": values,
                }
            )

        sums = [sum(row[axis_index] for row in parsed_rows) for axis_index in range(2)]
        parsed_total: list[int] = []
        source_total_values: list[dict[str, Any]] = []
        for axis_index, (graph_value, pixel_value) in enumerate(
            zip(graph_total, bank_review["source_only_total"], strict=True)
        ):
            parsed_total.append(_value(graph_value["surface"], pixel_value, disagreements))
            source_total_values.append(
                {
                    "axis_index": axis_index,
                    "independent_pixel_transcription": pixel_value,
                    "semantic_proposal": graph_value["surface"],
                    "source_line_index": graph_value["source_line_index"],
                }
            )

        accounting_scope: list[dict[str, Any]] = []
        additive_review = bank_review["optional_additive_population"]
        additive_graph = graph.get("optional_additive_row")
        if additive_review is None:
            if additive_graph is not None or parsed_total != sums:
                raise _error("five-grade total or optional additive boundary drifted")
        else:
            if type(additive_graph) is not dict or len(additive_graph.get("values", [])) != 2:
                raise _error("reviewed additive population is absent from the unique graph")
            additive_values = [
                _value(graph_value["surface"], pixel_value, disagreements)
                for graph_value, pixel_value in zip(
                    additive_graph["values"], additive_review["values"], strict=True
                )
            ]
            if any(
                parsed_total[index] != sums[index] + additive_values[index] for index in range(2)
            ):
                raise _error("source total does not close five grades plus additive population")
            accounting_scope.append(
                {
                    "independent_pixel_label": additive_review["pixel_label"],
                    "independent_pixel_values": additive_review["values"],
                    "report_norm_id": None,
                    "status": "VERIFIED_SOURCE_ONLY_OUTSIDE_FIVE_GRADE_CORE",
                }
            )

        child_review = bank_review["nonadditive_standard_child"]
        child_graph = graph.get("nonadditive_rows", [])
        verified_child: dict[str, Any] | None = None
        if child_review is None:
            if child_graph != []:
                raise _error("unique graph exposes an unreviewed nonadditive child")
        else:
            if type(child_graph) is not list or len(child_graph) != 1:
                raise _error("reviewed nonadditive standard child is absent from the graph")
            child = child_graph[0]
            if child.get("parent_role") != "STANDARD" or len(child.get("values", [])) != 2:
                raise _error("nonadditive child parent/lane binding drifted")
            child_values: list[dict[str, Any]] = []
            parsed_child: list[int] = []
            for axis_index, (graph_value, pixel_value) in enumerate(
                zip(child["values"], child_review["values"], strict=True)
            ):
                parsed_child.append(_value(graph_value["surface"], pixel_value, disagreements))
                child_values.append(
                    {
                        "axis_index": axis_index,
                        "independent_pixel_transcription": pixel_value,
                        "lane_type": "MONEY",
                        "semantic_proposal": graph_value["surface"],
                        "source_line_index": graph_value["source_line_index"],
                    }
                )
            if any(parsed_child[index] > parsed_rows[0][index] for index in range(2)):
                raise _error("nonadditive standard child exceeds its parent population")
            verified_child = {
                "canonical_name": schema["nonadditive_standard_child"]["canonical_name"],
                "independent_pixel_label": child_review["pixel_label"],
                "report_norm_id": 5746,
                "role": "STANDARD_INCLUDED_DISCLOSURE",
                "semantic_proposal_label": child["label_surface"],
                "status": "VERIFIED_BY_CODEX",
                "values": child_values,
            }

        near_child: list[dict[str, Any]] = []
        if verified_child is None:
            near_child.append(
                {
                    "report_norm_id": 5746,
                    "status": (
                        "OBSERVED_OUTSIDE_STANDARD_ROW_NOT_MAPPED_TO_QUALITY_CHILD"
                        if additive_review is not None
                        else "NOT_OBSERVED_IN_BOUND_QUALITY_TABLE"
                    ),
                    "whole_document_absence_claim": False,
                }
            )
        negative_controls = [
            {
                **control,
                "status": "EXCLUDED_WRONG_OR_UNSELECTED_OWNER_POPULATION",
                "whole_document_absence_claim": False,
            }
            for control in schema["negative_families"]
        ]
        trials.append(
            {
                "accounting_scope_populations": accounting_scope,
                "bank_provenance": expected_bank,
                "document_ordinal": ordinal,
                "layout_mode": graph["layout_mode"],
                "negative_family_controls": negative_controls,
                "near_neighbour_dispositions": near_child,
                "physical_page": bank_review["physical_page"],
                "source_only_total": {
                    "report_norm_id": None,
                    "status": "VERIFIED_SOURCE_ONLY",
                    "values": source_total_values,
                },
                "statement_context": canonical_clone_v1(bank_review["statement_context_evidence"]),
                "status": "VERIFIED_BY_CODEX",
                "target_render_sha256": bank_review["target_render_sha256"],
                "transformer_disagreements": canonical_clone_v1(disagreements),
                "verified_mappings": [
                    *verified_rows,
                    *([] if verified_child is None else [verified_child]),
                ],
            }
        )

    verified_core = sum(
        mapping["report_norm_id"] in {747, 748, 749, 750, 751}
        for trial in trials
        for mapping in trial["verified_mappings"]
    )
    verified_child = sum(
        mapping["report_norm_id"] == 5746
        for trial in trials
        for mapping in trial["verified_mappings"]
    )
    metrics = {
        "additive_source_only_population_count": sum(
            len(trial["accounting_scope_populations"]) for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_structure_count": len(trials),
        "mapped_item_verified_by_codex_count": verified_core + verified_child,
        "negative_family_control_count": sum(
            len(trial["negative_family_controls"]) for trial in trials
        ),
        "nonadditive_standard_child_verified_by_codex_count": verified_child,
        "source_only_total_verified_count": len(trials),
        "transformer_disagreement_preserved_count": sum(
            len(trial["transformer_disagreements"]) for trial in trials
        ),
        "unresolved_near_neighbour_count": sum(
            len(trial["near_neighbour_dispositions"]) for trial in trials
        ),
        "verified_by_codex_core_row_count": verified_core,
    }
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "codex_pixel_review": {"path": REVIEW_PATH.as_posix(), "sha256": review_sha256},
            "semantic_axis_sha256": axis["semantic_axis_sha256"],
            "semantic_index_sha256": EXPECTED_INDEX_SHA256,
            "structure_scan_id": structure_scan["scan_id"],
        },
        "metrics": metrics,
        "state": "LOAN_QUALITY_8BANK_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "lq8bcv1:result:" + canonical_json_sha256_v1(material)}
    )


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("verified quality result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "LOAN_QUALITY_8BANK_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or type(value["metrics"]) is not dict
        or type(value["input_refs"]) is not dict
    ):
        raise _error("verified quality result identity/authority drifted")
    clone = canonical_clone_v1(value)
    result_id = clone.pop("result_id")
    if result_id != "lq8bcv1:result:" + canonical_json_sha256_v1(clone):
        raise _error("verified quality result identity drifted")
    trial_fields = {
        "accounting_scope_populations",
        "bank_provenance",
        "document_ordinal",
        "layout_mode",
        "near_neighbour_dispositions",
        "negative_family_controls",
        "physical_page",
        "source_only_total",
        "statement_context",
        "status",
        "target_render_sha256",
        "transformer_disagreements",
        "verified_mappings",
    }
    mapping_fields = {
        "canonical_name",
        "independent_pixel_label",
        "report_norm_id",
        "role",
        "semantic_proposal_label",
        "status",
        "values",
    }
    core = child = negative = unresolved = disagreements = additive = 0
    for ordinal, (trial, expected_bank) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or set(trial) != trial_fields
            or trial.get("bank_provenance") != expected_bank
            or trial.get("document_ordinal") != ordinal
            or trial.get("status") != "VERIFIED_BY_CODEX"
            or trial.get("layout_mode")
            not in {
                "HORIZONTAL_TYPED_PERIOD_LANES",
                "STACKED_PERIOD_BLOCKS_MULTI_ASSET_COLUMNS",
            }
            or type(trial.get("physical_page")) is not int
            or trial["physical_page"] <= 0
            or type(trial.get("target_render_sha256")) is not str
            or type(trial.get("verified_mappings")) is not list
            or type(trial.get("negative_family_controls")) is not list
            or type(trial.get("near_neighbour_dispositions")) is not list
            or type(trial.get("accounting_scope_populations")) is not list
            or type(trial.get("transformer_disagreements")) is not list
            or type(trial.get("source_only_total")) is not dict
            or set(trial["source_only_total"]) != {"report_norm_id", "status", "values"}
            or trial["source_only_total"]["report_norm_id"] is not None
            or trial.get("source_only_total", {}).get("status") != "VERIFIED_SOURCE_ONLY"
            or type(trial["source_only_total"]["values"]) is not list
            or len(trial["source_only_total"]["values"]) != 2
        ):
            raise _error("verified quality trial shape/status drifted")
        _sha256(trial["target_render_sha256"], "verified trial target render")
        if any(
            type(mapping) is not dict
            or set(mapping) != mapping_fields
            or type(mapping["values"]) is not list
            or len(mapping["values"]) != 2
            for mapping in trial["verified_mappings"]
        ):
            raise _error("verified quality mapping shape/value denominator drifted")
        core_ids = [
            mapping["report_norm_id"]
            for mapping in trial["verified_mappings"]
            if mapping["report_norm_id"] in {747, 748, 749, 750, 751}
        ]
        if core_ids != [747, 748, 749, 750, 751] or any(
            mapping.get("status") != "VERIFIED_BY_CODEX" for mapping in trial["verified_mappings"]
        ):
            raise _error("verified quality mapping row order/status drifted")
        controls = trial["negative_family_controls"]
        if len(controls) != 2 or not same_typed_json_v1(
            controls,
            [
                {
                    "candidate_parent_report_norm_id": 853,
                    "owner_report_norm_id": 804,
                    "role_report_norm_ids": [854, 855, 856, 857, 858],
                    "status": "EXCLUDED_WRONG_OR_UNSELECTED_OWNER_POPULATION",
                    "whole_document_absence_claim": False,
                },
                {
                    "candidate_parent_report_norm_id": 1018,
                    "owner_report_norm_id": 966,
                    "role_report_norm_ids": [1019, 1020, 1021, 1022, 1023],
                    "status": "EXCLUDED_WRONG_OR_UNSELECTED_OWNER_POPULATION",
                    "whole_document_absence_claim": False,
                },
            ],
        ):
            raise _error("verified quality negative-family controls drifted")
        core += len(core_ids)
        child += sum(mapping["report_norm_id"] == 5746 for mapping in trial["verified_mappings"])
        negative += len(trial["negative_family_controls"])
        unresolved += len(trial["near_neighbour_dispositions"])
        disagreements += len(trial["transformer_disagreements"])
        additive += len(trial["accounting_scope_populations"])
    expected_metrics = {
        "additive_source_only_population_count": additive,
        "document_count": 8,
        "document_unique_structure_count": 8,
        "mapped_item_verified_by_codex_count": core + child,
        "negative_family_control_count": negative,
        "nonadditive_standard_child_verified_by_codex_count": child,
        "source_only_total_verified_count": 8,
        "transformer_disagreement_preserved_count": disagreements,
        "unresolved_near_neighbour_count": unresolved,
        "verified_by_codex_core_row_count": core,
    }
    if not same_typed_json_v1(value["metrics"], expected_metrics):
        raise _error("verified quality metrics drifted")
    return canonical_clone_v1(value)


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load required experiment module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _live_inputs() -> tuple[Any, Any, Any, Any, Mapping[int, Any]]:
    builder = _load_module(
        PROJECT_ROOT
        / "scripts/experiments/build_loan_maturity_full_document_vietocr_request_v1.py",
        "full_document_vietocr_builder_for_quality_codex_mapping_v1",
    )
    semantic_index = builder.read_verified_vietocr_proposals_v1()
    index_raw = _fixed_bytes(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    if not same_typed_json_v1(_json_bytes(index_raw, "semantic index"), semantic_index):
        raise _error("semantic index bytes and authenticated projection disagree")
    manifest = _json_bytes(
        _fixed_bytes(
            CROP_MANIFEST_PATH,
            builder.verify_full_document_freeze_v1(replay_geometry=False)["manifest_sha256"],
        ),
        "crop manifest",
    )
    scanner = _load_module(
        PROJECT_ROOT / "scripts/experiments/scan_loan_quality_full_document_vietocr_v1.py",
        "full_document_quality_scan_for_codex_mapping_v1",
    )
    structure_scan = scanner.build_loan_quality_full_document_scan_v1(semantic_index)
    review = _review(_json_bytes(_fixed_bytes(REVIEW_PATH, REVIEW_SHA256), "Codex pixel review"))
    _schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return semantic_index, manifest, structure_scan, review, schema_by_id


def build_live_loan_quality_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    """Replay all fixed sources and derive the bounded eight-bank verification."""

    semantic_index, manifest, structure_scan, review, schema_by_id = _live_inputs()
    return build_loan_quality_8bank_codex_verified_mapping_v1(
        semantic_index,
        manifest,
        structure_scan,
        review,
        schema_by_id,
        review_sha256=REVIEW_SHA256,
    )


def validate_loan_quality_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    """Exact-rebuild a persisted result from every fixed live input."""

    persisted = _validate_result(value)
    rebuilt = build_live_loan_quality_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("verified quality result does not replay exactly")
    return rebuilt


def main() -> int:
    print(
        json.dumps(
            build_live_loan_quality_8bank_codex_verified_mapping_v1(),
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
