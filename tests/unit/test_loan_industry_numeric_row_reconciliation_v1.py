from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _ROOT / "scripts/experiments/loan_industry_numeric_row_reconciliation_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "loan_industry_numeric_row_reconciliation_v1_test", _MODULE_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
reconciliation = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = reconciliation
_SPEC.loader.exec_module(reconciliation)


def _pages(*, missing_dash: bool = False) -> list[dict[str, object]]:
    surfaces: list[tuple[str, str, int, int]] = [
        ("CHO VAY KHÁCH HÀNG", "CHO VAY KHÁCH HÀNG", 0, 0),
        ("Phân tích dư nợ cho vay theo ngành", "label", 0, 35),
        ("30/06/2026", "30/06/2026", 500, 75),
        ("31/12/2025", "31/12/2025", 800, 75),
        ("Triệu đồng", "Triệu đồng", 500, 105),
        ("Triệu đồng", "Triệu đồng", 800, 105),
        ("Nông nghiệp, lâm nghiệp và thủy sản", "label", 0, 150),
        ("11", "10", 500, 150),
        ("9", "9", 800, 150),
        ("Xây dựng", "label", 0, 195),
    ]
    if not missing_dash:
        surfaces.append(("20", "20", 500, 195))
    surfaces.extend(
        [
            ("18", "18", 800, 195),
            ("10" if missing_dash else "30", "10" if missing_dash else "30", 500, 240),
            ("27", "27", 800, 240),
            ("Phân tích dư nợ theo loại hình doanh nghiệp", "boundary", 0, 285),
        ]
    )
    return [
        {
            "lines": [
                {
                    "bbox": [x, y, x + 140, y + 24],
                    "source_line_index": index,
                    "source_text": source,
                    "vietocr_text": semantic,
                }
                for index, (semantic, source, x, y) in enumerate(surfaces)
            ],
            "page_sequence": 1,
            "primary_numeric_authority": True,
        }
    ]


def test_ppocrv6_repairs_a_vietocr_digit_only_through_same_line_binding() -> None:
    result = reconciliation.build_loan_industry_numeric_row_reconciliation_v1(_pages())

    assert result["status"] == "PP_NUMERIC_EXACT"
    assert result["rows"][0]["cells"][0]["semantic_surface"] == "11"
    assert result["rows"][0]["cells"][0]["ppocrv6_surface"] == "10"
    assert result["rows"][0]["cells"][0]["parsed_value"] == 10
    assert all(
        item["status"] == "EXACT_PP_NUMERIC_EQUATION" for item in result["accounting_checks"]
    )


def test_missing_cell_is_not_zero_without_pixel_dash_evidence() -> None:
    result = reconciliation.build_loan_industry_numeric_row_reconciliation_v1(
        _pages(missing_dash=True)
    )

    assert result["status"] == "PP_NUMERIC_EXACT_PENDING_VISIBLE_DASH_EVIDENCE"
    missing = result["rows"][1]["cells"][0]
    assert missing["parsed_value"] is None
    assert missing["status"] == "MISSING_CELL_REQUIRES_VISIBLE_DASH_OR_NUMERIC_RESCUE"
    assert result["authority"]["blank_or_missing_cell_imputed_as_zero"] is False


def test_numeric_replay_rejects_a_coordinated_digit_rehash() -> None:
    result = reconciliation.build_loan_industry_numeric_row_reconciliation_v1(_pages())
    forged = copy.deepcopy(result)
    forged["rows"][0]["cells"][0]["parsed_value"] = 12
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "linrrv1:result:" + reconciliation.canonical_json_sha256_v1(material)

    with pytest.raises(reconciliation.LoanIndustryNumericRowReconciliationV1Error):
        reconciliation.validate_loan_industry_numeric_row_reconciliation_replay_v1(forged, _pages())


def test_one_detector_line_is_split_only_across_the_exact_covered_lanes() -> None:
    pages = _pages()
    lines = pages[0]["lines"]
    lines[7]["bbox"] = [500, 150, 940, 174]
    lines[7]["source_text"] = "10 9"
    lines[7]["vietocr_text"] = "10 9"
    del lines[8]
    for index, line in enumerate(lines):
        line["source_line_index"] = index

    result = reconciliation.build_loan_industry_numeric_row_reconciliation_v1(pages)

    assert result["status"] == "PP_NUMERIC_EXACT"
    assert [cell["parsed_value"] for cell in result["rows"][0]["cells"]] == [10, 9]
    assert [cell["source_line_index"] for cell in result["rows"][0]["cells"]] == [7, 7]


def _rounded_four_lane_pages(*, conflicting_digit: bool = False) -> list[dict[str, object]]:
    surfaces = [
        ("CHO VAY KHÁCH HÀNG", "CHO VAY KHÁCH HÀNG", 0, 0),
        ("Phân tích dư nợ cho vay theo ngành", "label", 0, 35),
        ("30/06/2026", "30/06/2026", 500, 75),
        ("31/12/2025", "31/12/2025", 900, 75),
        ("Triệu đồng", "Triệu đồng", 500, 105),
        ("%", "%", 700, 105),
        ("Triệu đồng", "Triệu đồng", 900, 105),
        ("%", "%", 1100, 105),
        ("Xây dựng", "label", 0, 150),
        ("11" if conflicting_digit else "10", "10", 500, 150),
        ("33,33", "33,33", 700, 150),
        ("9", "9", 900, 150),
        ("33,33", "33,33", 1100, 150),
        ("Nông nghiệp, lâm nghiệp và thủy sản", "label", 0, 195),
        ("20", "20", 500, 195),
        ("66,67", "66,67", 700, 195),
        ("18", "18", 900, 195),
        ("66,67", "66,67", 1100, 195),
        ("31", "31", 500, 240),
        ("100", "100", 700, 240),
        ("27", "27", 900, 240),
        ("100", "100", 1100, 240),
    ]
    return [
        {
            "lines": [
                {
                    "bbox": [x, y, x + 140, y + 24],
                    "source_line_index": index,
                    "source_text": source,
                    "vietocr_text": semantic,
                }
                for index, (semantic, source, x, y) in enumerate(surfaces)
            ],
            "page_sequence": 1,
            "primary_numeric_authority": True,
        }
    ]


def test_one_unit_rounding_residual_is_corroborated_by_exact_percent_lanes() -> None:
    result = reconciliation.build_loan_industry_numeric_row_reconciliation_v1(
        _rounded_four_lane_pages()
    )

    assert result["status"] == "PP_NUMERIC_CORROBORATED_WITH_ROUNDING_TOLERANCE"
    assert result["accounting_checks"][0]["status"] == ("CORROBORATED_ROUNDED_SOURCE_EQUATION")
    assert result["accounting_checks"][0]["residual"] == -1


def test_rounding_tolerance_does_not_hide_a_pp_vietocr_digit_conflict() -> None:
    result = reconciliation.build_loan_industry_numeric_row_reconciliation_v1(
        _rounded_four_lane_pages(conflicting_digit=True)
    )

    assert result["status"] == "UNRESOLVED_PP_NUMERIC_RECONCILIATION"
    assert result["accounting_checks"][0]["status"] == "UNRESOLVED_PP_NUMERIC_EQUATION"
