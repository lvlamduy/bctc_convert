from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _ROOT / "scripts/experiments/loan_type_numeric_row_reconciliation_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "loan_type_numeric_row_reconciliation_v1_test", _MODULE_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
reconciliation = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = reconciliation
_SPEC.loader.exec_module(reconciliation)


def _page(lines: list[tuple[str, str | None, int, int]]) -> dict[str, Any]:
    return {
        "lines": [
            {
                "bbox": [x, y, x + 160, y + 24],
                "source_line_index": index,
                "source_text": ppocr,
                "vietocr_text": semantic,
            }
            for index, (semantic, ppocr, x, y) in enumerate(lines)
        ],
        "page_sequence": 1,
        "primary_numeric_authority": True,
    }


def _unknown_rows(*, missing_current: bool = False) -> dict[str, Any]:
    lines = [
        ("CHO VAY KHÁCH HÀNG", "CHO VAY KHÁCH HÀNG", 0, 0),
        ("31/12/2025", "31/12/2025", 500, 40),
        ("31/12/2024", "31/12/2024", 800, 40),
        ("Triệu đồng", "Triệu đồng", 500, 70),
        ("Triệu đồng", "Triệu đồng", 800, 70),
        ("Cho vay các tổ chức kinh tế, cá nhân trong nước", "label", 0, 120),
        ("100", "100", 500, 120),
        ("90", "90", 800, 120),
        ("Cho vay thấu chi và thẻ tín dụng", "label", 0, 160),
    ]
    if not missing_current:
        lines.append(("5", "5", 500, 160))
    lines.extend(
        [
            ("4", "4", 800, 160),
            ("Các khoản trả thay khách hàng", "label", 0, 200),
            ("3", "3", 500, 200),
            ("2", "2", 800, 200),
            (
                ("103" if missing_current else "108"),
                ("103" if missing_current else "108"),
                500,
                240,
            ),
            ("96", "96", 800, 240),
            ("Cho vay vốn đặc biệt", "label", 0, 280),
            ("2", "2", 500, 280),
            ("1", "1", 800, 280),
            ("Tổng", "Tổng", 0, 320),
            (
                ("105" if missing_current else "110"),
                ("105" if missing_current else "110"),
                500,
                320,
            ),
            ("97", "97", 800, 320),
        ]
    )
    return _page(lines)


def test_unmodelled_labeled_rows_reconcile_while_unlabeled_subtotal_stays_source_only() -> None:
    result = reconciliation.build_loan_type_numeric_row_reconciliation_v1([_unknown_rows()])

    assert result["status"] == "PP_NUMERIC_EXACT"
    assert [row["label"]["surface"] for row in result["unmodelled_additive_rows"]] == [
        "Cho vay thấu chi và thẻ tín dụng",
        "Cho vay vốn đặc biệt",
    ]
    assert len(result["intermediate_subtotals"]) == 1
    assert result["accounting_checks"] == [
        {
            "lane_index": 0,
            "missing_cell_count": 0,
            "observed_additive_sum": 110,
            "status": "EXACT_PP_NUMERIC_EQUATION",
            "target_total": 110,
        },
        {
            "lane_index": 1,
            "missing_cell_count": 0,
            "observed_additive_sum": 97,
            "status": "EXACT_PP_NUMERIC_EQUATION",
            "target_total": 97,
        },
    ]


def test_missing_cell_is_not_zero_without_visible_dash_evidence() -> None:
    result = reconciliation.build_loan_type_numeric_row_reconciliation_v1(
        [_unknown_rows(missing_current=True)]
    )

    assert result["status"] == "PP_NUMERIC_EXACT_PENDING_VISIBLE_DASH_EVIDENCE"
    assert result["accounting_checks"][0]["status"] == (
        "EXACT_IF_MISSING_CELLS_ARE_VISIBLE_DASH_ZERO"
    )
    assert result["unmodelled_additive_rows"][0]["cells"][0]["status"] == (
        "MISSING_CELL_REQUIRES_VISIBLE_DASH_OR_NUMERIC_RESCUE"
    )


def test_numeric_reconciliation_replay_rejects_coordinated_rehash() -> None:
    pages = [_unknown_rows()]
    exact = reconciliation.build_loan_type_numeric_row_reconciliation_v1(pages)
    forged = copy.deepcopy(exact)
    forged["unmodelled_additive_rows"][0]["cells"][0]["parsed_value"] = 6
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "ltnrrv1:result:" + reconciliation.canonical_json_sha256_v1(material)

    with pytest.raises(
        reconciliation.LoanTypeNumericRowReconciliationV1Error,
        match="does not replay exactly",
    ):
        reconciliation.validate_loan_type_numeric_row_reconciliation_replay_v1(forged, pages)
