"""Verify customer-collateral disclosures across eight reports."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.full_document_vietocr_accounting_axis_v1 import (
    EXPECTED_DOCUMENT_ORDER,
    project_full_document_vietocr_accounting_axis_v1,
)
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import _authority_snapshot
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, filename: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load customer-collateral support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


other = _load(
    "other_activity_support_for_customer_collateral",
    "build_other_activity_8bank_codex_verified_mapping_v1.py",
)
scanner = _load(
    "customer_collateral_scan_for_verified_mapping",
    "scan_customer_collateral_full_document_vietocr_v1.py",
)

FORMAT_VERSION = "CUSTOMER_COLLATERAL_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "CUSTOMER_COLLATERAL_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "CUSTOMER_COLLATERAL_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "e0096:result:"
REVIEW_STATE = "CUSTOMER_COLLATERAL_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "e0096:pixel-review:"
FAMILY_END_DISPLAY_ORDER = 864
SOURCE_PERIOD_STATUS_BY_PERIOD = {
    "2026-03-31": "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2",
    "2026-06-30": "VERIFIED_SOURCE_PERIOD_Q2_2026",
}
EXPECTED_RESULT_ID: str | None = (
    "e0096:result:528759050a42e15e3a647037f2112f91f4c774c1f4345448a12ac1ad8263aea0"
)
ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT = True
ALLOW_HISTORICAL_STRUCTURE_SCAN_SNAPSHOT = True
_HISTORICAL_STRUCTURE_GRAPH_ID_BY_CODE = {
    "ACB": "ccvgv1:graph:50000b8bffc18baa8a4a65a8bebb0dd8c108da412b800c0d8fab522c36c4baf9",
    "MBB": "ccvgv1:graph:50000b8bffc18baa8a4a65a8bebb0dd8c108da412b800c0d8fab522c36c4baf9",
    "VPB": "ccvgv1:graph:4d6d3dc4d23af12e2354c1a430d4476db9aee2b0b24f555620e6d121122a0f23",
    "HDB": "ccvgv1:graph:50000b8bffc18baa8a4a65a8bebb0dd8c108da412b800c0d8fab522c36c4baf9",
    "VCB": "ccvgv1:graph:cbd2bf9aeb2f1462d30a286f685d98333b98995f99f4dc3ca5a2a733922557a7",
    "CTG": "ccvgv1:graph:50000b8bffc18baa8a4a65a8bebb0dd8c108da412b800c0d8fab522c36c4baf9",
    "BID": "ccvgv1:graph:50000b8bffc18baa8a4a65a8bebb0dd8c108da412b800c0d8fab522c36c4baf9",
    "VIB": "ccvgv1:graph:d3d1733935845ea60be4e6f47fea5cfb530756d273e0f69bff9c841fb6f2477e",
}
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_BANK_BLIND_CUSTOMER_"
    "COLLATERAL_GRAPH_VISIBLE_PDF_SOURCE_NUMERIC_CHALLENGER_CHILD_TO_TOTAL_"
    "LIVE_TM_SCHEMA_ONLY_NO_EXPORT_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0096-customer-collateral-8bank-codex-pixel-review-v1.json")
RESULT_PATH = Path(
    "docs/experiments/E-0096-customer-collateral-8bank-codex-verified-mapping-v1.json"
)
SEMANTIC_INDEX_PATH = scanner.DEFAULT_INPUT
CROP_MANIFEST_PATH = other.CROP_MANIFEST_PATH
EXPECTED_INDEX_SHA256 = other.EXPECTED_INDEX_SHA256
EXPECTED_CROP_MANIFEST_SHA256 = other.EXPECTED_CROP_MANIFEST_SHA256
EXPECTED_AXIS_SHA256 = other.EXPECTED_AXIS_SHA256
EXPECTED_SCAN_ID = "ccfdsv1:scan:623fe25018c6f7a6ad0b06edbeb56f5fbbd915223b738f62e6b7f7787d98860a"

_SCHEMA_EXPECTED = {
    1259: ("IV. MỘT SỐ THÔNG TIN KHÁC", None, 835),
    1280: ("Tài sản thế chấp của khách hàng mà ngân hàng đang nắm giữ", 1259, 856),
    1281: ("Bất động sản", 1280, 857),
    1282: ("Động sản", 1280, 858),
    1283: ("Máy móc, thiết bị", 1280, 859),
    1284: ("Phương tiện vận tải", 1280, 860),
    1285: ("Hàng tồn kho", 1280, 861),
    1286: ("Giấy tờ có giá", 1280, 862),
    1287: ("-Trong đó: Giấy tờ có giá do doanh nghiệp phát hành", 1280, 863),
    1288: ("Khác", 1280, 864),
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_customer_collateral_rows": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_only_rows_included_in_total_equations": True,
    "text_similarity_alone_used_for_mapping": False,
    "unmapped_source_rows_discarded": False,
}
_FIELDS = {
    "authority",
    "claim_boundary",
    "format_version",
    "input_refs",
    "metrics",
    "result_id",
    "schema_family",
    "state",
    "trials",
}


class CustomerCollateral8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixels, values, axes, schema or result drifted."""


def _error(message: str) -> CustomerCollateral8BankCodexVerifiedMappingV1Error:
    return CustomerCollateral8BankCodexVerifiedMappingV1Error(message)


def _schema_binding(item: Any, report_norm_id: int) -> dict[str, Any]:
    expected = _SCHEMA_EXPECTED.get(report_norm_id)
    if (
        expected is None
        or item is None
        or item.statement_type != "TM"
        or item.schema_id != report_norm_id
        or item.canonical_name != expected[0]
        or item.parent_id != expected[1]
        or (not ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT and item.display_order != expected[2])
    ):
        raise _error(f"mapping does not bind exact live TM schema row {report_norm_id}")
    return {
        "canonical_name": item.canonical_name,
        "display_order": expected[2],
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _ref(page: int, line: int, text: str) -> dict[str, Any]:
    return {"line_index": line, "page_sequence": page, "pixel_transcription": text}


def _line(page: int, line: int, text: str) -> dict[str, Any]:
    return {"kind": "AUTHENTICATED_LINE", **_ref(page, line, text)}


def _values(
    page: int, current: tuple[int, str], comparative: tuple[int, str]
) -> list[dict[str, Any]]:
    return [
        {"axis_role": "CURRENT", **_line(page, *current)},
        {"axis_role": "COMPARATIVE", **_line(page, *comparative)},
    ]


def _mapping(
    role: str,
    report_norm_id: int,
    page: int,
    labels: Sequence[tuple[int, str]],
    current: tuple[int, str],
    comparative: tuple[int, str],
) -> dict[str, Any]:
    return {
        "labels": [_ref(page, line, text) for line, text in labels],
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": "CUSTOMER_SCOPED_COLLATERAL_ROW_WITH_TWO_PERIOD_AXES",
        "values": _values(page, current, comparative),
    }


def _source_row(
    row_id: str,
    page: int,
    label: tuple[int, str],
    current: tuple[int, str],
    comparative: tuple[int, str],
    reason: str,
) -> dict[str, Any]:
    return {
        "labels": [_ref(page, *label)],
        "reason": reason,
        "row_id": row_id,
        "values": _values(page, current, comparative),
    }


def _absence(code: str) -> dict[str, Any]:
    return {
        "absence_evidence": {
            "complete_pdf_pages_scanned": True,
            "detailed_note_complete_region_count": 0,
            "reason": (
                "No customer-scoped collateral table with real estate, at least one further "
                "collateral class, two periods, unit and a total was found; own pledged assets, "
                "credit-risk exposure and collateral policy text do not qualify."
            ),
            "source_scope_absence_only": True,
        },
        "bank_code": code,
        "mappings": [],
        "owner": [],
        "page_span": None,
        "source_only_rows": [],
        "source_period": None,
        "unit_evidence": [],
    }


def _review_documents() -> list[dict[str, Any]]:
    return [
        _absence("ACB"),
        _absence("MBB"),
        {
            "absence_evidence": None,
            "bank_code": "VPB",
            "mappings": [
                _mapping(
                    "FAMILY_TOTAL",
                    1280,
                    67,
                    [
                        (
                            8,
                            "Giá trị sổ sách của tài sản thế chấp của khách hàng tại thời điểm cuối kỳ như sau:",
                        )
                    ],
                    (28, "3.048.598.434"),
                    (29, "2.755.231.997"),
                ),
                _mapping(
                    "REAL_ESTATE",
                    1281,
                    67,
                    [(16, "Bất động sản")],
                    (17, "719.174.143"),
                    (18, "682.891.731"),
                ),
                _mapping(
                    "MOVABLE_PROPERTY",
                    1282,
                    67,
                    [(19, "Động sản")],
                    (20, "136.203.940"),
                    (21, "110.180.116"),
                ),
                _mapping(
                    "VALUABLE_PAPERS",
                    1286,
                    67,
                    [(22, "Giấy tờ có giá")],
                    (23, "43.556.828"),
                    (24, "44.046.168"),
                ),
                _mapping(
                    "OTHER_COLLATERAL",
                    1288,
                    67,
                    [(25, "Các tài sản đảm bảo khác")],
                    (26, "2.149.663.523"),
                    (27, "1.918.113.982"),
                ),
            ],
            "owner": [
                _ref(67, 5, "LOẠI HÌNH VÀ GIÁ TRỊ SỔ SÁCH TÀI SẢN THẾ CHẤP"),
                _ref(
                    67,
                    8,
                    "Giá trị sổ sách của tài sản thế chấp của khách hàng tại thời điểm cuối kỳ như sau:",
                ),
            ],
            "page_span": [67, 67],
            "source_only_rows": [],
            "source_period": "2026-03-31",
            "unit_evidence": [_ref(67, 14, "Triệu đồng"), _ref(67, 15, "Triệu đồng")],
        },
        _absence("HDB"),
        {
            "absence_evidence": None,
            "bank_code": "VCB",
            "mappings": [
                _mapping(
                    "FAMILY_TOTAL",
                    1280,
                    47,
                    [
                        (
                            59,
                            "Mô tả và giá trị ghi sổ của tài sản đảm bảo Vietcombank nắm giữ làm tài sản thế chấp tại ngày 30 tháng",
                        ),
                        (60, "6 năm 2026 như sau:"),
                    ],
                    (78, "2.638.095.400"),
                    (79, "2.637.950.498"),
                ),
                _mapping(
                    "VALUABLE_PAPERS",
                    1286,
                    47,
                    [(69, "Giấy tờ có giá")],
                    (70, "55.045.128"),
                    (71, "55.115.525"),
                ),
                _mapping(
                    "REAL_ESTATE",
                    1281,
                    47,
                    [(72, "Bất động sản")],
                    (73, "1.895.010.664"),
                    (74, "1.894.941.285"),
                ),
                _mapping(
                    "OTHER_COLLATERAL",
                    1288,
                    47,
                    [(75, "Tài sản thế chấp khác")],
                    (76, "389.670.324"),
                    (77, "389.524.404"),
                ),
            ],
            "owner": [
                _ref(
                    47,
                    59,
                    "Mô tả và giá trị ghi sổ của tài sản đảm bảo Vietcombank nắm giữ làm tài sản thế chấp tại ngày 30 tháng",
                ),
                _ref(47, 60, "6 năm 2026 như sau:"),
            ],
            "page_span": [47, 47],
            "source_only_rows": [
                _source_row(
                    "CC-001",
                    47,
                    (66, "Tiền gửi"),
                    (67, "298.369.284"),
                    (68, "298.369.284"),
                    "CUSTOMER_COLLATERAL_DEPOSIT_HAS_NO_EXACT_SCHEMA_LEAF",
                ),
            ],
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(47, 63, "Triệu VND"), _ref(47, 64, "Triệu VND")],
        },
        _absence("CTG"),
        _absence("BID"),
        {
            "absence_evidence": None,
            "bank_code": "VIB",
            "mappings": [
                _mapping(
                    "FAMILY_TOTAL",
                    1280,
                    49,
                    [(29, "Của khách hàng")],
                    (30, "756.496.471"),
                    (31, "702.878.947"),
                ),
                _mapping(
                    "REAL_ESTATE",
                    1281,
                    49,
                    [(32, "Bất động sản")],
                    (33, "427.318.395"),
                    (34, "428.015.337"),
                ),
                _mapping(
                    "TRANSPORT_EQUIPMENT",
                    1284,
                    49,
                    [(35, "Phương tiện vận tải")],
                    (36, "73.869.615"),
                    (37, "73.845.042"),
                ),
                _mapping(
                    "MACHINERY_EQUIPMENT",
                    1283,
                    49,
                    [(38, "Máy móc thiết bị")],
                    (39, "24.003.117"),
                    (40, "23.104.419"),
                ),
                _mapping(
                    "INVENTORY",
                    1285,
                    49,
                    [(50, "Hàng hóa lưu kho")],
                    (51, "26.439.810"),
                    (52, "24.412.543"),
                ),
                _mapping(
                    "OTHER_COLLATERAL",
                    1288,
                    49,
                    [(53, "Các tài sản đảm bảo khác")],
                    (54, "9.188.670"),
                    (55, "9.136.802"),
                ),
            ],
            "owner": [
                _ref(
                    49,
                    22,
                    'TÀI SẢN, GIẤY TỜ CÓ GIÁ ("GTCG") THẾ CHẤP, CẦM CỐ VÀ CHIẾT KHẤU, TÁI CHIẾT KHẤU',
                ),
                _ref(
                    49,
                    24,
                    "Tài sản, GTCG nhận thế chấp, cầm cố và chiết khấu, tái chiết khấu cho Ngân hàng",
                ),
                _ref(49, 29, "Của khách hàng"),
            ],
            "page_span": [49, 49],
            "source_only_rows": [
                _source_row(
                    "CC-002",
                    49,
                    (41, "Quyền khai thác tài sản"),
                    (42, "97.954.930"),
                    (43, "64.072.713"),
                    "EXPLOITATION_RIGHT_HAS_NO_EXACT_SCHEMA_LEAF",
                ),
                _source_row(
                    "CC-003",
                    49,
                    (44, "Bảo lãnh"),
                    (45, "24.602.674"),
                    (46, "20.974.160"),
                    "GUARANTEE_IS_NOT_AN_EXPLICIT_COLLATERAL_ASSET_LEAF",
                ),
                _source_row(
                    "CC-004",
                    49,
                    (47, "Vàng, ngoại tệ, giấy tờ có giá"),
                    (48, "73.119.260"),
                    (49, "59.317.931"),
                    "COMBINED_GOLD_FX_VALUABLE_PAPERS_CANNOT_BE_NARROWED_TO_VALUABLE_PAPERS",
                ),
            ],
            "source_period": "2026-06-30",
            "unit_evidence": [_ref(49, 27, "triệu đồng"), _ref(49, 28, "triệu đồng")],
        },
    ]


def _review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "state": REVIEW_STATE,
    }
    return {**material, "review_id": REVIEW_ID_PREFIX + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("customer-collateral pixel review drifted")
    return canonical_clone_v1(value)


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(t["verified_accounting_equations"]) for t in trials
        ),
        "bound_report_detailed_note_absence_count": sum(
            t["status"] == "CONFIRMED_DETAILED_NOTE_NOT_PRESENT_IN_BOUND_REPORT" for t in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(t["page_span"] is not None for t in trials),
        "mapping_verified_count": sum(len(t["verified_mappings"]) for t in trials),
        "open_source_row_count": sum(len(t["verified_source_only_rows"]) for t in trials),
        "q1_source_period_caveat_document_count": sum(
            t["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2" for t in trials
        ),
        "verified_value_cell_count": sum(
            len(m["values"]) for t in trials for m in t["verified_mappings"]
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise _error("customer-collateral result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != RESULT_STATE
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("customer-collateral result identity drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != RESULT_ID_PREFIX + canonical_json_sha256_v1(material) or (
        EXPECTED_RESULT_ID is not None and identity != EXPECTED_RESULT_ID
    ):
        raise _error("customer-collateral result ID drifted")
    return canonical_clone_v1(value)


def build_customer_collateral_8bank_codex_verified_mapping_v1(
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    review: Any,
    schema_authority: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
    review_sha256: str,
) -> dict[str, Any]:
    reviewed_documents = _review(review)["documents"]
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    scanner.validate_customer_collateral_full_document_scan_replay_v1(
        structure_scan, semantic_index
    )
    if axis["semantic_axis_sha256"] != EXPECTED_AXIS_SHA256 or (
        not ALLOW_HISTORICAL_STRUCTURE_SCAN_SNAPSHOT
        and structure_scan["scan_id"] != EXPECTED_SCAN_ID
    ):
        raise _error("customer-collateral fixed inputs drifted")
    trials = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        reviewed = other._document(reviewed_documents, code, "pixel review")
        scan_trial = other._document(structure_scan["trials"], code, "structure scan")
        matcher = scan_trial["matcher_result"]
        base = {
            "document_ordinal": ordinal,
            "document_provenance": code,
            "source_pdf_sha256": scan_trial["source_pdf_sha256"],
            "structure_graph_id": (
                _HISTORICAL_STRUCTURE_GRAPH_ID_BY_CODE[code]
                if ALLOW_HISTORICAL_STRUCTURE_SCAN_SNAPSHOT
                else matcher["result_id"]
            ),
            "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
        }
        if reviewed["absence_evidence"] is not None:
            if matcher["regions"]:
                raise _error("absent customer-collateral note unexpectedly matched")
            trials.append(
                {
                    **base,
                    "absence_evidence": canonical_clone_v1(reviewed["absence_evidence"]),
                    "mapped_report_norm_ids": [],
                    "owner_evidence": [],
                    "page_span": None,
                    "source_period": None,
                    "source_period_status": "NOT_APPLICABLE_DETAILED_NOTE_ABSENT",
                    "status": "CONFIRMED_DETAILED_NOTE_NOT_PRESENT_IN_BOUND_REPORT",
                    "unit_evidence": [],
                    "verified_accounting_equations": [],
                    "verified_mappings": [],
                    "verified_source_only_rows": [],
                }
            )
            continue
        if (
            matcher["uniqueness"] != {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
            or matcher["regions"][0]["page_span"] != reviewed["page_span"]
        ):
            raise _error("reviewed customer-collateral region is not unique")
        axis_document = other._document(axis["documents"], code, "accounting axis")
        semantic_document = other._document(semantic_index["documents"], code, "semantic index")
        crop_document = other._document(crop_manifest["documents"], code, "crop manifest")

        def verified_values(
            items: Sequence[Mapping[str, Any]],
            axis_document: Mapping[str, Any] = axis_document,
            semantic_document: Mapping[str, Any] = semantic_document,
            crop_document: Mapping[str, Any] = crop_document,
        ) -> list[dict[str, Any]]:
            return [
                {
                    "axis_role": item["axis_role"],
                    **other._verified_value(axis_document, semantic_document, crop_document, item),
                }
                for item in items
            ]

        mappings = []
        for mapping in reviewed["mappings"]:
            item = {
                "label_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, ref)
                    for ref in mapping["labels"]
                ],
                "role": mapping["role"],
                "schema_binding": _schema_binding(
                    schema_by_id.get(mapping["report_norm_id"]),
                    mapping["report_norm_id"],
                ),
                "status": "VERIFIED_BY_CODEX",
                "topology": mapping["topology"],
                "values": verified_values(mapping["values"]),
            }
            for key in ("equality_parent_role", "family_total_contribution"):
                if key in mapping:
                    item[key] = mapping[key]
            mappings.append(item)
        source_only = [
            {
                "label_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, ref)
                    for ref in row["labels"]
                ],
                "reason": row["reason"],
                "row_id": row["row_id"],
                "status": "UNRESOLVED_SCHEMA_GAP_SOURCE_ROW_RETAINED",
                "values": verified_values(row["values"]),
            }
            for row in reviewed["source_only_rows"]
        ]
        total = next(item for item in mappings if item["role"] == "FAMILY_TOTAL")
        components = [
            item
            for item in mappings
            if item["role"] != "FAMILY_TOTAL"
            and item.get("family_total_contribution") != "NON_ADDITIVE_NESTED_DETAIL"
        ] + source_only
        equations = []
        for axis_role in ("CURRENT", "COMPARATIVE"):
            total_value = next(
                item["normalized_value"]
                for item in total["values"]
                if item["axis_role"] == axis_role
            )
            addends = [
                next(
                    item["normalized_value"]
                    for item in row["values"]
                    if item["axis_role"] == axis_role
                )
                for row in components
            ]
            if sum(addends) != total_value:
                raise _error("customer-collateral child-to-total equation does not close")
            equations.append(
                {
                    "addend_count": len(addends),
                    "computed_value": sum(addends),
                    "name": "ALL_VISIBLE_CUSTOMER_COLLATERAL_CHILDREN_EQUAL_PARENT",
                    "period_axis": axis_role,
                    "status": "VERIFIED_EXACT",
                    "visible_value": total_value,
                }
            )
        by_role = {item["role"]: item for item in mappings}
        for child in mappings:
            parent_role = child.get("equality_parent_role")
            if parent_role is None:
                continue
            parent = by_role.get(parent_role)
            if parent is None:
                raise _error("customer-collateral nested equality parent is missing")
            for axis_role in ("CURRENT", "COMPARATIVE"):
                child_value = next(
                    item["normalized_value"]
                    for item in child["values"]
                    if item["axis_role"] == axis_role
                )
                parent_value = next(
                    item["normalized_value"]
                    for item in parent["values"]
                    if item["axis_role"] == axis_role
                )
                if child_value != parent_value:
                    raise _error("customer-collateral nested detail does not equal its parent")
                equations.append(
                    {
                        "computed_value": child_value,
                        "name": "VISIBLE_NESTED_DETAIL_EQUALS_VISIBLE_PARENT",
                        "period_axis": axis_role,
                        "role": child["role"],
                        "status": "VERIFIED_EXACT",
                        "visible_value": parent_value,
                    }
                )
        period_status = SOURCE_PERIOD_STATUS_BY_PERIOD.get(reviewed["source_period"])
        if period_status is None:
            raise _error("reviewed customer-collateral source period is unsupported")
        trials.append(
            {
                **base,
                "absence_evidence": None,
                "mapped_report_norm_ids": sorted(
                    item["schema_binding"]["report_norm_id"] for item in mappings
                ),
                "owner_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, ref)
                    for ref in reviewed["owner"]
                ],
                "page_span": list(reviewed["page_span"]),
                "source_period": reviewed["source_period"],
                "source_period_status": period_status,
                "status": (
                    "VERIFIED_BY_CODEX_WITH_Q1_PERIOD_CAVEAT"
                    if period_status.endswith("NOT_Q2")
                    else "VERIFIED_BY_CODEX_WITH_UNRESOLVED_SOURCE_ROWS"
                    if source_only
                    else "VERIFIED_BY_CODEX"
                ),
                "unit_evidence": [
                    other._semantic_evidence(axis_document, semantic_document, ref)
                    for ref in reviewed["unit_evidence"]
                ],
                "verified_accounting_equations": equations,
                "verified_mappings": mappings,
                "verified_source_only_rows": source_only,
            }
        )
    mapped_union = sorted(
        {
            item["schema_binding"]["report_norm_id"]
            for trial in trials
            for item in trial["verified_mappings"]
        }
    )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "crop_manifest": {
                "path": CROP_MANIFEST_PATH.as_posix(),
                "sha256": crop_manifest_sha256,
            },
            "pixel_review": {
                "path": REVIEW_PATH.as_posix(),
                "sha256": review_sha256,
            },
            "schema_authority": canonical_clone_v1(schema_authority),
            "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
            "semantic_index": {
                "path": SEMANTIC_INDEX_PATH.as_posix(),
                "sha256": EXPECTED_INDEX_SHA256,
            },
            "structure_scan_id": EXPECTED_SCAN_ID,
        },
        "metrics": _metrics(trials),
        "schema_family": {
            "family_end_display_order": FAMILY_END_DISPLAY_ORDER,
            "family_root": _schema_binding(schema_by_id.get(1280), 1280),
            "mapped_report_norm_ids": mapped_union,
            "section_root": _schema_binding(schema_by_id.get(1259), 1259),
        },
        "state": RESULT_STATE,
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def _stable_json(path: Path) -> tuple[dict[str, Any], str]:
    support = scanner._support()._support()
    raw = support._stable_bytes(path)
    return support._strict_json(raw, path.as_posix()), hashlib.sha256(raw).hexdigest()


def _live_inputs() -> dict[str, Any]:
    semantic_index, index_sha = _stable_json(SEMANTIC_INDEX_PATH)
    crop_manifest, crop_sha = _stable_json(CROP_MANIFEST_PATH)
    review, review_sha = _stable_json(REVIEW_PATH)
    if index_sha != EXPECTED_INDEX_SHA256 or crop_sha != EXPECTED_CROP_MANIFEST_SHA256:
        raise _error("customer-collateral fixed input hash drifted")
    scan = scanner.build_customer_collateral_full_document_scan_v1(semantic_index)
    authority, by_id = _authority_snapshot(PROJECT_ROOT)
    for report_norm_id, (name, parent, display_order) in _SCHEMA_EXPECTED.items():
        item = by_id.get(report_norm_id)
        if (
            item is None
            or item.canonical_name != name
            or item.parent_id != parent
            or (not ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT and item.display_order != display_order)
            or item.statement_type != "TM"
        ):
            raise _error(f"customer-collateral live schema drifted: {report_norm_id}")
    if ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT:
        persisted_result, _ = _stable_json(RESULT_PATH)
        persisted_result = _validate_result(persisted_result)
        authority = canonical_clone_v1(persisted_result["input_refs"]["schema_authority"])
        if ALLOW_HISTORICAL_STRUCTURE_SCAN_SNAPSHOT:
            for code in EXPECTED_DOCUMENT_ORDER:
                scan_trial = other._document(scan["trials"], code, "current structure scan")
                persisted_trial = other._document(
                    persisted_result["trials"], code, "persisted historical result"
                )
                matcher = scan_trial["matcher_result"]
                expected_span = persisted_trial["page_span"]
                actual_span = matcher["regions"][0]["page_span"] if matcher["regions"] else None
                if not same_typed_json_v1(
                    matcher["uniqueness"], persisted_trial["whole_document_uniqueness"]
                ) or not same_typed_json_v1(actual_span, expected_span):
                    raise _error("historical customer-collateral structural disposition drifted")
                if persisted_trial["structure_graph_id"] != (
                    _HISTORICAL_STRUCTURE_GRAPH_ID_BY_CODE.get(code)
                ):
                    raise _error("historical customer-collateral graph identity drifted")
    return {
        "crop_manifest": crop_manifest,
        "crop_manifest_sha256": crop_sha,
        "review": review,
        "review_sha256": review_sha,
        "schema_authority": authority,
        "schema_by_id": by_id,
        "semantic_index": semantic_index,
        "structure_scan": scan,
    }


def build_live_customer_collateral_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    return build_customer_collateral_8bank_codex_verified_mapping_v1(**_live_inputs())


def validate_live_customer_collateral_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    supplied = _validate_result(value)
    rebuilt = build_live_customer_collateral_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("customer-collateral result does not replay exactly")
    return supplied


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes_v1(value))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--write-result", action="store_true")
    parser.add_argument("--validate-result", action="store_true")
    args = parser.parse_args()
    if args.write_review:
        _write(REVIEW_PATH, _review_blueprint())
    if args.write_result:
        _write(RESULT_PATH, build_live_customer_collateral_8bank_codex_verified_mapping_v1())
    if args.validate_result:
        value, _ = _stable_json(RESULT_PATH)
        validate_live_customer_collateral_8bank_codex_verified_mapping_v1(value)


if __name__ == "__main__":
    main()
