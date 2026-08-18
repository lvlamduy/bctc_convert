"""Verify annual-2025 net-interest income across the fixed eight banks.

The mapped row is derived from the two immediately preceding interest rows on
the consolidated income statement and is independently reconciled to the
already verified annual TM interest-income and interest-expense families.  The
statement graph scans every page and is bank/page blind: a candidate needs the
consolidated-income-statement heading, two period axes, a monetary unit, the
ordered income/expense/net rows, two geometry-aligned values per row, and the
exact accounting equation.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import re
import sys
from collections.abc import Mapping, Sequence
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
from bctc_ai.schema.business_update import BUSINESS_UPDATE_AUDIT, verify_business_schema_update
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "ANNUAL_2025_NET_INTEREST_INCOME_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_NET_INTEREST_INCOME_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_NET_INTEREST_INCOME_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025nii8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_NET_INTEREST_INCOME_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025nii8bcv1:pixel-review:"
REVIEW_RUN_ID = "E-0136"
REVIEW_PATH = Path(
    "docs/experiments/E-0136-annual-2025-net-interest-income-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0136-annual-2025-net-interest-income-8bank-codex-verified-mapping-v1.json"
)
SEMANTIC_INDEX_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/"
    "semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/crop_manifest.json"
)
INCOME_RESULT_PATH = Path(
    "docs/experiments/E-0134-annual-2025-interest-income-8bank-codex-verified-mapping-v1.json"
)
EXPENSE_RESULT_PATH = Path(
    "docs/experiments/E-0135-annual-2025-interest-expense-8bank-codex-verified-mapping-v1.json"
)
EXPECTED_INDEX_SHA256 = "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d"
EXPECTED_CROP_MANIFEST_SHA256 = "17d12a4d6b1dfaf0e243300757fd225b8c9cca80810a2d856efdb55a5b4ac000"
EXPECTED_AXIS_SHA256 = "aa81f553fda69315e84b7adbda13347c25a4490b016fc9660ff4f2cd49795ce7"
EXPECTED_INCOME_RESULT_SHA256 = "09b63070d3aec7af65787eb05e2bb35c7519a380d97695a103091f0b5c4613f3"
EXPECTED_EXPENSE_RESULT_SHA256 = "52fe4c56b2d0dd1d4528752301eca771414f132f30ff3e7ef11a44189bf77774"

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_VIETOCR_"
    "BANK_BLIND_CONSOLIDATED_INCOME_STATEMENT_GRAPH_VISIBLE_PDF_UPSTREAM_"
    "PPOCRV6_NUMERIC_CHALLENGER_EXACT_TM_1143_1151_AND_LIVE_TM_5985_FORMULA_"
    "ONLY_NO_CANONICALIZATION_EXPORT_OR_PRODUCTION_AUTHORITY"
)
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_and_formula_checked": True,
    "mapping_authority_bounded_to_reviewed_net_interest_row": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "statement_and_tm_component_values_reconciled": True,
    "text_similarity_alone_used_for_mapping": False,
    "whole_pdf_uniqueness_replayed": True,
}
_REVIEW_SAFETY = {
    "bank_page_or_filename_used_as_graph_rule": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "gemma_json_used_as_mapping_or_numeric_authority": False,
    "mapping_decided_by_text_similarity_alone": False,
    "statement_expense_sign_silently_inferred_from_tm_presentation": False,
    "whole_pdf_uniqueness_replayed": True,
}
_SCHEMA_EXPECTED = {
    1142: (
        "II. THÔNG TIN BỔ SUNG CHO CÁC KHOẢN MỤC TRÌNH BÀY TRONG BẢNG KẾT QUẢ KINH DOANH",
        None,
        686,
    ),
    1143: ("Thu nhập lãi và các khoản thu nhập tương tự", 1142, 687),
    1151: ("Chi phí lãi và các khoản tương tự chi phí lãi", 1142, 697),
    5985: ("Thu nhập từ lãi thuần", 1142, 703),
}
_RESULT_FIELDS = {
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
_MONEY_TEXT = re.compile(r"^\(?\s*\d{1,3}(?:[.,]\d{3})+\s*\)?$")


class Annual2025NetInterestIncome8BankError(ValueError):
    """Annual net-interest source, formula, schema, or replay drifted."""


def _error(message: str) -> Annual2025NetInterestIncome8BankError:
    return Annual2025NetInterestIncome8BankError(message)


def _load_module(name: str, filename: str) -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual family support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _label(page: int, line: int, text: str) -> dict[str, Any]:
    return {"line_index": line, "page_sequence": page, "pixel_transcription": text}


def _value(page: int, line: int, text: str) -> dict[str, Any]:
    return {"line_index": line, "page_sequence": page, "pixel_transcription": text}


def _review_specifications() -> list[dict[str, Any]]:
    specifications = [
        (
            "ACB",
            10,
            (2, "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG HỢP NHẤT"),
            [(4, "Năm 2025"), (5, "Năm 2024")],
            [(7, "Triệu VND"), (8, "Triệu VND")],
            (10, "Thu nhập lãi và các khoản thu nhập tương tự", 12, "58.755.829", 13, "50.902.749"),
            (15, "Chi phí lãi và các chi phí tương tự", 17, "(31.850.134)", 18, "(23.108.047)"),
            (20, "Thu nhập lãi thuần", 21, "26.905.695", 22, "27.794.702"),
            "GEOMETRY_ORDERED_THREE_ROW_STATEMENT_BLOCK",
        ),
        (
            "MBB",
            13,
            (3, "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG HỢP NHẤT"),
            [(9, "Năm 2025"), (10, "Năm 2024")],
            [(12, "triệu đồng"), (13, "triệu đồng")],
            (14, "Thu nhập lãi và các khoản thu nhập tương tự", 15, "89.088.116", 16, "69.061.893"),
            (17, "Chi phí lãi và các chi phí tương tự", 18, "(37.477.999)", 19, "(27.909.674)"),
            (20, "Thu nhập lãi thuần", 22, "51.610.117", 23, "41.152.219"),
            "GEOMETRY_ORDERED_THREE_ROW_STATEMENT_BLOCK_WITH_NOTE_COLUMN",
        ),
        (
            "VPB",
            12,
            (2, "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG HỢP NHẤT"),
            [(4, "Năm 2025"), (5, "Năm 2024")],
            [(9, "Triệu đồng"), (10, "Triệu đồng")],
            (
                12,
                "Thu nhập lãi và các khoản thu nhập tương tự",
                14,
                "101.258.954",
                15,
                "81.033.640",
            ),
            (16, "Chi phí lãi và các chi phí tương tự", 18, "(42.596.241)", 19, "(31.031.238)"),
            (20, "Thu nhập lãi thuần", 21, "58.662.713", 22, "50.002.402"),
            "GEOMETRY_ORDERED_THREE_ROW_STATEMENT_BLOCK_WITH_RESTATED_COMPARATIVE",
        ),
        (
            "HDB",
            10,
            (6, "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG HỢP NHẤT"),
            [(13, "Năm nay"), (10, "Năm trước")],
            [(8, "Đơn vị: Triệu VND")],
            (16, "Thu nhập lãi và các khoản thu nhập tương tự", 18, "67.992.416", 19, "57.995.528"),
            (21, "Chi phí lãi và các chi phí tương tự", 23, "(33.246.226)", 24, "(27.138.452)"),
            (26, "Thu nhập lãi thuần", 27, "34.746.190", 28, "30.857.076"),
            "GEOMETRY_ORDERED_THREE_ROW_STATEMENT_BLOCK_WITH_PAGE_LEVEL_UNIT",
        ),
        (
            "VCB",
            11,
            (4, "Báo cáo kết quả hoạt động hợp nhất"),
            [(11, "2025"), (12, "2024")],
            [(14, "Triệu VND"), (15, "Triệu VND")],
            (
                18,
                "Thu nhập lãi và các khoản thu nhập tương tự",
                20,
                "105.216.484",
                21,
                "93.654.841",
            ),
            (23, "Chi phí lãi và các chi phí tương tự", 25, "(46.445.074)", 26, "(38.249.106)"),
            (29, "Thu nhập lãi thuần", 30, "58.771.410", 31, "55.405.735"),
            "GEOMETRY_ORDERED_THREE_ROW_STATEMENT_BLOCK",
        ),
        (
            "CTG",
            11,
            (2, "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG HỢP NHẤT"),
            [(6, "2025"), (7, "2024")],
            [(9, "Triệu đồng"), (10, "Triệu đồng")],
            (
                12,
                "Thu nhập lãi và các khoản thu nhập tương tự",
                14,
                "143.142.328",
                15,
                "124.460.685",
            ),
            (17, "Chi phí lãi và các chi phí tương tự", 19, "(76.689.083)", 20, "(62.057.891)"),
            (22, "Thu nhập lãi thuần", 23, "66.453.245", 24, "62.402.794"),
            "GEOMETRY_ORDERED_THREE_ROW_STATEMENT_BLOCK",
        ),
        (
            "BID",
            12,
            (6, "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG HỢP NHẤT"),
            [(14, "Năm nay"), (10, "Năm trước")],
            [(8, "Đơn vị: Triệu VND")],
            (
                17,
                "Thu nhập lãi và các khoản thu nhập tương tự",
                19,
                "154.992.934",
                20,
                "138.283.813",
            ),
            (22, "Chi phí lãi và các chi phí tương tự", 24, "(91.697.828)", 25, "(80.280.835)"),
            (27, "Thu nhập lãi thuần", 28, "63.295.106", 29, "58.002.978"),
            "GEOMETRY_ORDERED_THREE_ROW_STATEMENT_BLOCK_WITH_PAGE_LEVEL_UNIT",
        ),
        (
            "VIB",
            11,
            (2, "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG HỢP NHẤT"),
            [(5, "2025"), (6, "2024")],
            [(8, "triệu đồng"), (9, "triệu đồng")],
            (12, "Thu nhập lãi và các khoản thu nhập tương tự", 10, "36.324.009", 11, "32.442.938"),
            (15, "Chi phí lãi và các chi phí tương tự", 13, "(20.231.849)", 14, "(15.692.526)"),
            (16, "Thu nhập lãi thuần", 18, "16.092.160", 19, "16.750.412"),
            "GEOMETRY_ROW_BINDING_WITH_PROVIDER_VALUE_BEFORE_LABEL_ORDER",
        ),
    ]
    documents = []
    for ordinal, item in enumerate(specifications, 1):
        code, page, heading, periods, units, income, expense, net, presentation = item

        def row(
            role: str,
            source: tuple[int, str, int, str, int, str],
            page_sequence: int = page,
        ) -> dict[str, Any]:
            label_line, label_text, current_line, current_text, prior_line, prior_text = source
            return {
                "label": _label(page_sequence, label_line, label_text),
                "role": role,
                "values": {
                    "COMPARATIVE_PERIOD": _value(page_sequence, prior_line, prior_text),
                    "CURRENT_PERIOD": _value(page_sequence, current_line, current_text),
                },
            }

        documents.append(
            {
                "document_ordinal": ordinal,
                "document_provenance": code,
                "page_sequence": page,
                "period_axis": [_label(page, line, text) for line, text in periods],
                "presentation": presentation,
                "rows": [
                    row("STATEMENT_INTEREST_INCOME", income),
                    row("STATEMENT_INTEREST_EXPENSE", expense),
                    row("NET_INTEREST_INCOME", net),
                ],
                "source_period": "2025-12-31",
                "statement_heading": _label(page, heading[0], heading[1]),
                "unit_evidence": [_label(page, line, text) for line, text in units],
            }
        )
    return documents


def build_annual_2025_net_interest_income_pixel_review_blueprint_v1() -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_specifications(),
        "format_version": REVIEW_FORMAT,
        "reviewer": {
            "kind": "CODEX_INDEPENDENT_VISIBLE_PDF_REVIEW",
            "review_run_id": REVIEW_RUN_ID,
        },
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "state": REVIEW_STATE,
    }
    return {**material, "review_id": REVIEW_ID_PREFIX + canonical_json_sha256_v1(material)}


def _bbox(line: Mapping[str, Any]) -> tuple[int, int, int, int]:
    value = line.get("source_bbox_raw_pixels")
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or value[0] < 0
        or value[1] < 0
        or value[2] <= value[0]
        or value[3] <= value[1]
    ):
        raise _error("semantic statement bbox drifted")
    return value[0], value[1], value[2], value[3]


def _center_y(line: Mapping[str, Any]) -> float:
    bbox = _bbox(line)
    return (bbox[1] + bbox[3]) / 2


def _row_values(
    lines: Sequence[Mapping[str, Any]], label: Mapping[str, Any]
) -> list[Mapping[str, Any]]:
    label_bbox = _bbox(label)
    values = [
        line
        for line in lines
        if line is not label
        and abs(_center_y(line) - _center_y(label)) <= 18
        and _bbox(line)[0] > label_bbox[2] + 80
        and type(line.get("vietocr_text")) is str
        and _MONEY_TEXT.fullmatch(line["vietocr_text"].strip()) is not None
    ]
    return sorted(values, key=lambda line: _bbox(line)[0])


def _normalized(line: Mapping[str, Any]) -> str:
    value = line.get("vietocr_text")
    if type(value) is not str:
        raise _error("semantic statement text drifted")
    return normalize_vietnamese_anchor_v1(value)


def _statement_heading(text: str) -> bool:
    return all(token in text for token in ("bao cao", "ket qua", "hoat dong", "hop nhat"))


def _income_label(text: str) -> bool:
    return text.startswith("thu nhap lai") and "tuong tu" in text


def _expense_label(text: str) -> bool:
    return text.startswith("chi phi lai") and "tuong tu" in text


def _net_label(text: str) -> bool:
    return text in {"thu nhap lai thuan", "thu nhap tu lai thuan"}


def _period_axis_present(lines: Sequence[Mapping[str, Any]]) -> bool:
    normalized = {_normalized(line) for line in lines}
    current = bool(normalized & {"nam 2025", "2025", "nam nay"})
    comparative = bool(normalized & {"nam 2024", "2024", "nam truoc"})
    return current and comparative


def _monetary_unit_present(lines: Sequence[Mapping[str, Any]]) -> bool:
    return any(
        "trieu vnd" in _normalized(line) or "trieu dong" in _normalized(line) for line in lines
    )


def _candidate(page: Mapping[str, Any]) -> list[dict[str, Any]]:
    lines = page.get("lines")
    if type(lines) is not list:
        raise _error("semantic statement page line axis drifted")
    if (
        not any(_statement_heading(_normalized(line)) for line in lines)
        or not _period_axis_present(lines)
        or not _monetary_unit_present(lines)
    ):
        return []
    candidates = []
    for net in lines:
        net_values = _row_values(lines, net)
        if not _net_label(_normalized(net)) or len(net_values) != 2:
            continue
        preceding = [
            line
            for line in lines
            if _center_y(line) < _center_y(net) and _center_y(net) - _center_y(line) < 170
        ]
        income = [
            line
            for line in preceding
            if _income_label(_normalized(line)) and len(_row_values(lines, line)) == 2
        ]
        expense = [
            line
            for line in preceding
            if _expense_label(_normalized(line)) and len(_row_values(lines, line)) == 2
        ]
        if (
            len(income) != 1
            or len(expense) != 1
            or not _center_y(income[0]) < _center_y(expense[0]) < _center_y(net)
        ):
            continue
        headings = [line for line in lines if _statement_heading(_normalized(line))]
        if len(headings) != 1:
            continue
        candidates.append(
            {
                "component_label_line_indices": [
                    income[0]["source_line_index"],
                    expense[0]["source_line_index"],
                ],
                "component_value_line_indices": [
                    [line["source_line_index"] for line in _row_values(lines, income[0])],
                    [line["source_line_index"] for line in _row_values(lines, expense[0])],
                ],
                "net_label_line_index": net["source_line_index"],
                "net_value_line_indices": [line["source_line_index"] for line in net_values],
                "page_sequence": page["physical_page"],
                "statement_heading_line_index": headings[0]["source_line_index"],
            }
        )
    return candidates


def build_annual_2025_net_interest_statement_scan_v1(
    semantic_index: Any,
) -> dict[str, Any]:
    if type(semantic_index) is not dict or type(semantic_index.get("documents")) is not list:
        raise _error("semantic index shape drifted")
    trials = []
    for ordinal, (document, code) in enumerate(
        zip(semantic_index["documents"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if document.get("bank_code") != code or type(document.get("pages")) is not list:
            raise _error("semantic document order drifted")
        regions = [region for page in document["pages"] for region in _candidate(page)]
        uniqueness = {
            "complete_region_count": len(regions),
            "status": "UNIQUE_FULL_MATCH" if len(regions) == 1 else "UNRESOLVED_NOT_UNIQUE",
        }
        trials.append(
            {
                "document_ordinal": ordinal,
                "document_provenance": code,
                "page_count_scanned": len(document["pages"]),
                "regions": regions,
                "uniqueness": uniqueness,
            }
        )
    material = {
        "format_version": "ANNUAL_2025_NET_INTEREST_STATEMENT_FULL_DOCUMENT_SCAN_V1",
        "metrics": {
            "document_count": len(trials),
            "document_unique_region_count": sum(
                trial["uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for trial in trials
            ),
            "page_count_scanned": sum(trial["page_count_scanned"] for trial in trials),
        },
        "state": "ANNUAL_2025_NET_INTEREST_STATEMENT_FULL_DOCUMENT_SCAN_COMPLETE",
        "trials": trials,
    }
    return {
        **material,
        "scan_id": "annual2025nisv1:scan:" + canonical_json_sha256_v1(material),
    }


def _document(items: Any, code: str, label: str) -> dict[str, Any]:
    if type(items) is not list:
        raise _error(f"{label} document axis drifted")
    matches = [
        item
        for item in items
        if type(item) is dict and item.get("document_provenance", item.get("bank_code")) == code
    ]
    if len(matches) != 1:
        raise _error(f"{label} does not contain one exact document {code}")
    return matches[0]


def _page(document: Mapping[str, Any], page_sequence: int, label: str) -> dict[str, Any]:
    pages = document.get("pages")
    if type(pages) is not list:
        raise _error(f"{label} page axis drifted")
    matches = [
        page
        for page in pages
        if page.get("page_sequence", page.get("physical_page")) == page_sequence
    ]
    if len(matches) != 1:
        raise _error(f"{label} does not contain one exact page {page_sequence}")
    return matches[0]


def _schema_binding(item: Any, report_norm_id: int) -> dict[str, Any]:
    expected = _SCHEMA_EXPECTED.get(report_norm_id)
    if (
        expected is None
        or item is None
        or item.statement_type != "TM"
        or item.schema_id != report_norm_id
        or item.canonical_name != expected[0]
        or item.parent_id != expected[1]
        or item.display_order != expected[2]
    ):
        raise _error(f"mapping does not bind exact live TM schema row {report_norm_id}")
    return {
        "canonical_name": item.canonical_name,
        "display_order": item.display_order,
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def _total_mapping(trial: Mapping[str, Any], report_norm_id: int) -> dict[str, Any]:
    mappings = trial.get("verified_mappings")
    if type(mappings) is not list:
        raise _error("upstream verified mapping axis drifted")
    matches = [
        mapping
        for mapping in mappings
        if mapping.get("schema_binding", {}).get("report_norm_id") == report_norm_id
    ]
    if len(matches) != 1 or matches[0].get("status") != "VERIFIED_BY_CODEX":
        raise _error(f"upstream total {report_norm_id} is not exactly verified")
    return canonical_clone_v1(matches[0])


def _axis_value(mapping: Mapping[str, Any], axis_role: str) -> dict[str, Any]:
    values = mapping.get("values")
    if type(values) is not list:
        raise _error("mapping value axis drifted")
    matches = [value for value in values if value.get("axis_role") == axis_role]
    if len(matches) != 1 or type(matches[0].get("normalized_value")) is not int:
        raise _error("mapping does not contain one exact typed axis value")
    return matches[0]


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]["status"] == "UNIQUE_FULL_MATCH" for trial in trials
        ),
        "fresh_vietocr_numeric_disagreement_count": sum(
            value["fresh_vietocr_numeric_status"] == "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
            for trial in trials
            for value in trial["verified_mapping"]["values"]
        ),
        "mapping_verified_count": len(trials),
        "open_source_row_count": 0,
        "verified_value_cell_count": sum(
            len(trial["verified_mapping"]["values"]) for trial in trials
        ),
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("annual net-interest result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != RESULT_STATE
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("annual net-interest result identity or metrics drifted")
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or trial.get("status") != "VERIFIED_BY_CODEX"
            or trial.get("verified_mapping", {}).get("status") != "VERIFIED_BY_CODEX"
            or trial.get("verified_mapping", {}).get("schema_binding", {}).get("report_norm_id")
            != 5985
            or trial.get("whole_document_uniqueness")
            != {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
        ):
            raise _error("annual net-interest trial shape or status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != RESULT_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("annual net-interest result identity drifted")
    return canonical_clone_v1(value)


def _formula_components() -> tuple[tuple[int, ...], str]:
    audit_path = PROJECT_ROOT / BUSINESS_UPDATE_AUDIT
    audit_bytes = audit_path.read_bytes()
    audit = verify_business_schema_update(PROJECT_ROOT, audit_path)
    matches = [
        formula for formula in audit["business_formulas"] if formula.get("schema_id") == 5985
    ]
    if len(matches) != 1:
        raise _error("live schema does not contain one exact 5985 formula")
    components = matches[0].get("component_schema_ids")
    if components != [1143, 1151]:
        raise _error("live 5985 formula components drifted")
    return (1143, 1151), hashlib.sha256(audit_bytes).hexdigest()


def _load_live_inputs() -> tuple[
    ModuleType,
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    str,
    str,
    str,
]:
    income_module = _load_module(
        "annual_2025_interest_income_for_net_interest",
        "build_annual_2025_interest_income_8bank_codex_verified_mapping_v1.py",
    )
    expense_module = _load_module(
        "annual_2025_interest_expense_for_net_interest",
        "build_annual_2025_interest_expense_8bank_codex_verified_mapping_v1.py",
    )
    base = income_module._load_base()
    income_module._configure(base)
    semantic_index, _ = base._stable_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_sha = base._stable_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    stored_income, income_sha = base._stable_json(INCOME_RESULT_PATH, EXPECTED_INCOME_RESULT_SHA256)
    stored_expense, expense_sha = base._stable_json(
        EXPENSE_RESULT_PATH, EXPECTED_EXPENSE_RESULT_SHA256
    )
    live_income = (
        income_module.build_live_annual_2025_interest_income_8bank_codex_verified_mapping_v1()
    )
    live_expense = (
        expense_module.build_live_annual_2025_interest_expense_8bank_codex_verified_mapping_v1()
    )
    if not same_typed_json_v1(stored_income, live_income):
        raise _error("stored annual interest-income result does not live-replay")
    if not same_typed_json_v1(stored_expense, live_expense):
        raise _error("stored annual interest-expense result does not live-replay")
    return (
        base,
        semantic_index,
        crop_manifest,
        live_income,
        live_expense,
        crop_sha,
        income_sha,
        expense_sha,
    )


def build_annual_2025_net_interest_income_8bank_codex_verified_mapping_v1(
    base: ModuleType,
    semantic_index: Any,
    crop_manifest: Any,
    income_result: Any,
    expense_result: Any,
    review: Any,
    structure_scan: Any,
    schema_authority: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
    review_sha256: str,
    income_result_sha256: str,
    expense_result_sha256: str,
    business_update_audit_sha256: str,
) -> dict[str, Any]:
    if not same_typed_json_v1(
        review, build_annual_2025_net_interest_income_pixel_review_blueprint_v1()
    ):
        raise _error("annual net-interest pixel review differs from fixed ledger")
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if (
        axis.get("semantic_axis_sha256") != EXPECTED_AXIS_SHA256
        or structure_scan.get("state")
        != "ANNUAL_2025_NET_INTEREST_STATEMENT_FULL_DOCUMENT_SCAN_COMPLETE"
        or structure_scan.get("metrics", {}).get("document_unique_region_count") != 8
        or type(crop_manifest) is not dict
    ):
        raise _error("annual semantic axis, crop manifest, or statement scan drifted")
    formula_components, live_audit_sha = _formula_components()
    if live_audit_sha != business_update_audit_sha256:
        raise _error("business-update audit bytes changed during net-interest build")
    trials = []
    reviewed_documents = review["documents"]
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        reviewed = _document(reviewed_documents, code, "pixel review")
        scan_trial = _document(structure_scan["trials"], code, "statement scan")
        income_trial = _document(income_result["trials"], code, "interest-income result")
        expense_trial = _document(expense_result["trials"], code, "interest-expense result")
        axis_document = _document(axis["documents"], code, "accounting axis")
        semantic_document = _document(semantic_index["documents"], code, "semantic index")
        crop_document = _document(crop_manifest["documents"], code, "crop manifest")
        if scan_trial["uniqueness"] != {
            "complete_region_count": 1,
            "status": "UNIQUE_FULL_MATCH",
        }:
            raise _error(f"statement net-interest graph is not unique for {code}")
        candidate = scan_trial["regions"][0]
        page_number = reviewed["page_sequence"]
        expected_lines = {
            "component_label_line_indices": [
                reviewed["rows"][0]["label"]["line_index"],
                reviewed["rows"][1]["label"]["line_index"],
            ],
            "component_value_line_indices": [
                sorted(value["line_index"] for value in reviewed["rows"][0]["values"].values()),
                sorted(value["line_index"] for value in reviewed["rows"][1]["values"].values()),
            ],
            "net_label_line_index": reviewed["rows"][2]["label"]["line_index"],
            "net_value_line_indices": sorted(
                value["line_index"] for value in reviewed["rows"][2]["values"].values()
            ),
            "page_sequence": page_number,
            "statement_heading_line_index": reviewed["statement_heading"]["line_index"],
        }
        if not same_typed_json_v1(candidate, expected_lines):
            raise _error(f"pixel-reviewed statement graph differs from whole-PDF scan for {code}")
        axis_page = _page(axis_document, page_number, "accounting axis")
        semantic_page = _page(semantic_document, page_number, "semantic index")
        crop_page = _page(crop_document, page_number, "crop manifest")
        source_texts = base.foundation.support._source_line_axis(crop_page)

        def semantic_evidence(
            item: Mapping[str, Any],
            bound_axis_page: Mapping[str, Any] = axis_page,
            bound_semantic_page: Mapping[str, Any] = semantic_page,
        ) -> dict[str, Any]:
            return base._semantic_evidence(bound_axis_page, bound_semantic_page, item)

        def verified_value(
            ref: Mapping[str, Any],
            bound_axis_page: Mapping[str, Any] = axis_page,
            bound_semantic_page: Mapping[str, Any] = semantic_page,
            bound_crop_page: Mapping[str, Any] = crop_page,
            bound_source_texts: Sequence[str] = source_texts,
            bound_page_number: int = page_number,
        ) -> dict[str, Any]:
            evidence = base.foundation.support._source_value(
                bound_axis_page,
                bound_semantic_page,
                bound_crop_page,
                bound_source_texts,
                {
                    "line_index": ref["line_index"],
                    "pixel_transcription": ref["pixel_transcription"],
                },
            )
            try:
                proposal_value = base.foundation.support._money(
                    evidence["fresh_vietocr_numeric_proposal"]
                )
            except ValueError:
                proposal_value = None
            return {
                **evidence,
                "fresh_vietocr_numeric_status": (
                    "MATCHES_SOURCE_NUMERIC_CHALLENGER"
                    if proposal_value == evidence["normalized_value"]
                    else "DISAGREES_WITH_SOURCE_NUMERIC_CHALLENGER"
                ),
                "page_sequence": bound_page_number,
            }

        statement_rows: dict[str, dict[str, Any]] = {}
        for row in reviewed["rows"]:
            statement_rows[row["role"]] = {
                "label_evidence": semantic_evidence(row["label"]),
                "role": row["role"],
                "values": [
                    {"axis_role": axis_role, **verified_value(ref)}
                    for axis_role, ref in row["values"].items()
                ],
            }
        income_total = _total_mapping(income_trial, 1143)
        expense_total = _total_mapping(expense_trial, 1151)
        net_mapping = {
            "label_evidence": statement_rows["NET_INTEREST_INCOME"]["label_evidence"],
            "role": "NET_INTEREST_INCOME",
            "schema_binding": _schema_binding(schema_by_id.get(5985), 5985),
            "status": "VERIFIED_BY_CODEX",
            "topology": reviewed["presentation"],
            "values": statement_rows["NET_INTEREST_INCOME"]["values"],
        }
        equations = []
        for axis_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"):
            statement_income = _axis_value(statement_rows["STATEMENT_INTEREST_INCOME"], axis_role)
            statement_expense = _axis_value(statement_rows["STATEMENT_INTEREST_EXPENSE"], axis_role)
            statement_net = _axis_value(statement_rows["NET_INTEREST_INCOME"], axis_role)
            tm_income = _axis_value(income_total, axis_role)
            tm_expense = _axis_value(expense_total, axis_role)
            if statement_income["normalized_value"] != tm_income["normalized_value"]:
                raise _error(f"statement/TM interest income differs for {code}/{axis_role}")
            if abs(statement_expense["normalized_value"]) != abs(tm_expense["normalized_value"]):
                raise _error(f"statement/TM interest expense differs for {code}/{axis_role}")
            computed = statement_income["normalized_value"] + statement_expense["normalized_value"]
            if statement_expense["normalized_value"] >= 0:
                raise _error(
                    f"statement interest expense lost its visible sign for {code}/{axis_role}"
                )
            if computed != statement_net["normalized_value"]:
                raise _error(f"net-interest equation does not close for {code}/{axis_role}")
            equations.extend(
                [
                    {
                        "axis_role": axis_role,
                        "computed_value": statement_income["normalized_value"],
                        "name": "STATEMENT_INTEREST_INCOME_EQUALS_VERIFIED_TM_1143",
                        "status": "VERIFIED_EXACT",
                        "visible_total": tm_income["normalized_value"],
                    },
                    {
                        "axis_role": axis_role,
                        "computed_value": abs(statement_expense["normalized_value"]),
                        "name": "STATEMENT_INTEREST_EXPENSE_MAGNITUDE_EQUALS_VERIFIED_TM_1151",
                        "status": "VERIFIED_EXACT",
                        "visible_total": abs(tm_expense["normalized_value"]),
                    },
                    {
                        "axis_role": axis_role,
                        "computed_value": computed,
                        "formula_component_report_norm_ids": list(formula_components),
                        "name": "TM_5985_EQUALS_1143_PLUS_VISIBLE_SIGNED_1151",
                        "status": "VERIFIED_EXACT",
                        "visible_total": statement_net["normalized_value"],
                    },
                ]
            )
        trials.append(
            {
                "component_bindings": {
                    "interest_expense": {
                        "mapping": expense_total,
                        "upstream_result_id": expense_result["result_id"],
                    },
                    "interest_income": {
                        "mapping": income_total,
                        "upstream_result_id": income_result["result_id"],
                    },
                },
                "document_ordinal": ordinal,
                "document_provenance": code,
                "page_sequence": page_number,
                "period_axis_evidence": [
                    semantic_evidence(item) for item in reviewed["period_axis"]
                ],
                "render_ref": canonical_clone_v1(crop_page["render_binding"]),
                "source_geometry_mode": semantic_page["geometry_mode"],
                "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                "source_period": reviewed["source_period"],
                "source_period_status": (
                    "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
                ),
                "statement_component_evidence": {
                    "interest_expense": statement_rows["STATEMENT_INTEREST_EXPENSE"],
                    "interest_income": statement_rows["STATEMENT_INTEREST_INCOME"],
                },
                "statement_heading_evidence": semantic_evidence(reviewed["statement_heading"]),
                "status": "VERIFIED_BY_CODEX",
                "unit_evidence": [semantic_evidence(item) for item in reviewed["unit_evidence"]],
                "verified_accounting_equations": equations,
                "verified_mapping": net_mapping,
                "whole_document_uniqueness": canonical_clone_v1(scan_trial["uniqueness"]),
            }
        )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "business_update_audit": {
                "path": Path(BUSINESS_UPDATE_AUDIT).as_posix(),
                "sha256": business_update_audit_sha256,
            },
            "crop_manifest": {
                "path": CROP_MANIFEST_PATH.as_posix(),
                "sha256": crop_manifest_sha256,
            },
            "interest_expense_result": {
                "path": EXPENSE_RESULT_PATH.as_posix(),
                "result_id": expense_result["result_id"],
                "sha256": expense_result_sha256,
            },
            "interest_income_result": {
                "path": INCOME_RESULT_PATH.as_posix(),
                "result_id": income_result["result_id"],
                "sha256": income_result_sha256,
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
            "structure_scan_id": structure_scan["scan_id"],
        },
        "metrics": _metrics(trials),
        "schema_family": {
            "family_end_display_order": 703,
            "formula_component_report_norm_ids": list(formula_components),
            "family_root": _schema_binding(schema_by_id.get(5985), 5985),
            "mapped_report_norm_ids": [5985],
            "section_root": _schema_binding(schema_by_id.get(1142), 1142),
        },
        "state": RESULT_STATE,
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def build_live_annual_2025_net_interest_income_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    (
        base,
        semantic_index,
        crop_manifest,
        income_result,
        expense_result,
        crop_sha,
        income_sha,
        expense_sha,
    ) = _load_live_inputs()
    review = build_annual_2025_net_interest_income_pixel_review_blueprint_v1()
    review_sha = hashlib.sha256(canonical_json_bytes_v1(review)).hexdigest()
    structure_scan = build_annual_2025_net_interest_statement_scan_v1(semantic_index)
    schema_authority, schema_by_id = base._authority_snapshot(PROJECT_ROOT)
    _, business_update_audit_sha = _formula_components()
    result = build_annual_2025_net_interest_income_8bank_codex_verified_mapping_v1(
        base,
        semantic_index,
        crop_manifest,
        income_result,
        expense_result,
        review,
        structure_scan,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
        income_result_sha256=income_sha,
        expense_result_sha256=expense_sha,
        business_update_audit_sha256=business_update_audit_sha,
    )
    replayed = build_annual_2025_net_interest_income_8bank_codex_verified_mapping_v1(
        base,
        semantic_index,
        crop_manifest,
        income_result,
        expense_result,
        review,
        structure_scan,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=crop_sha,
        review_sha256=review_sha,
        income_result_sha256=income_sha,
        expense_result_sha256=expense_sha,
        business_update_audit_sha256=business_update_audit_sha,
    )
    if not same_typed_json_v1(result, replayed):
        raise _error("annual net-interest result does not replay exactly")
    return result


def validate_live_annual_2025_net_interest_income_8bank_codex_verified_mapping_v1(
    value: Any,
) -> dict[str, Any]:
    rebuilt = build_live_annual_2025_net_interest_income_8bank_codex_verified_mapping_v1()
    supplied = _validate_result(value)
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("persisted annual net-interest result does not replay exactly")
    return supplied


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-result", action="store_true")
    args = parser.parse_args()
    if args.validate_result:
        base = _load_module(
            "annual_2025_interest_income_for_net_interest_validation",
            "build_annual_2025_interest_income_8bank_codex_verified_mapping_v1.py",
        )._load_base()
        value, _ = base._stable_json(RESULT_PATH)
        validate_live_annual_2025_net_interest_income_8bank_codex_verified_mapping_v1(value)
        return 0
    output = args.output or (REVIEW_PATH if args.write_review else RESULT_PATH)
    value = (
        build_annual_2025_net_interest_income_pixel_review_blueprint_v1()
        if args.write_review
        else build_live_annual_2025_net_interest_income_8bank_codex_verified_mapping_v1()
    )
    output.write_bytes(canonical_json_bytes_v1(value))
    if not args.write_review:
        print(value["result_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
