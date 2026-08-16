from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/employee_income_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("employee_income_variant_graph_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
matcher = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = matcher
_SPEC.loader.exec_module(matcher)


def _page(texts: list[str]) -> dict[str, object]:
    lines = []
    for index, text in enumerate(texts):
        numeric = re.fullmatch(r"\(?[0-9][0-9.,]*\)?", text) is not None
        lines.append(
            {
                "bbox": [750 if numeric else 60, index * 25, 920, index * 25 + 20],
                "semantic_text": text,
                "semantic_text_source": "FULL_DOCUMENT_FRESH_VIETOCR_TRANSFORMER",
                "source_line_index": index,
                "source_text": None,
                "vietocr_text": text,
            }
        )
    return {"lines": lines, "page_sequence": 1, "primary_numeric_authority": True}


def test_component_variant_is_accepted() -> None:
    result = matcher.build_employee_income_variant_graph_document_v1(
        [
            _page(
                [
                    "Tình hình thu nhập của nhân viên",
                    "Kỳ này",
                    "Kỳ trước",
                    "Triệu đồng",
                    "Số lượng nhân viên bình quân (người)",
                    "100",
                    "90",
                    "Tiền lương",
                    "3.000",
                    "2.700",
                    "Thu nhập khác",
                    "300",
                    "270",
                    "Tổng thu nhập",
                    "3.300",
                    "2.970",
                    "Thu nhập bình quân tháng",
                    "11",
                    "11",
                ]
            )
        ]
    )
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["salary_components_present"] is True


def test_direct_income_variant_is_accepted() -> None:
    result = matcher.build_employee_income_variant_graph_document_v1(
        [
            _page(
                [
                    "Tình hình thu nhập của cán bộ nhân viên",
                    "6 tháng đầu năm 2026",
                    "6 tháng đầu năm 2025",
                    "triệu đồng",
                    "Bình quân số cán bộ, nhân viên (người)",
                    "100",
                    "90",
                    "Thu nhập của cán bộ, nhân viên",
                    "3.300",
                    "2.970",
                    "Thu nhập bình quân/tháng",
                    "5,50",
                    "5,50",
                ]
            )
        ]
    )
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["direct_employee_income_present"] is True


@pytest.mark.parametrize(
    "texts",
    [
        ["Mức lương bình quân của sáu tháng trước thời điểm thôi việc"],
        ["Số lượng nhân viên", "10.000"],
        ["Thu nhập của nhân viên", "3.000"],
    ],
)
def test_policy_or_orphan_rows_do_not_accept(texts: list[str]) -> None:
    result = matcher.build_employee_income_variant_graph_document_v1([_page(texts)])
    assert result["metrics"]["complete_region_count"] == 0


def test_missing_average_income_fails_closed() -> None:
    result = matcher.build_employee_income_variant_graph_document_v1(
        [
            _page(
                [
                    "Tình hình thu nhập của nhân viên",
                    "Kỳ này",
                    "Kỳ trước",
                    "Triệu đồng",
                    "Số lượng nhân viên bình quân (người)",
                    "100",
                    "90",
                    "Tổng thu nhập",
                    "3.300",
                    "2.970",
                ]
            )
        ]
    )
    assert result["metrics"]["complete_region_count"] == 0
