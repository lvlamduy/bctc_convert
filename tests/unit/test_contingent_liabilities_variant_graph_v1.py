from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/contingent_liabilities_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("contingent_liabilities_variant_graph_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
matcher = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = matcher
_SPEC.loader.exec_module(matcher)


def _page(texts: list[str], page: int = 1) -> dict[str, object]:
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
    return {"lines": lines, "page_sequence": page, "primary_numeric_authority": True}


def _deep_core(*, reverse: bool = False) -> list[str]:
    rows = [
        "Cam kết giao dịch hối đoái",
        "100",
        "90",
        "Cam kết mua ngoại tệ",
        "20",
        "10",
        "Cam kết bán ngoại tệ",
        "30",
        "20",
        "Cam kết trong nghiệp vụ L/C",
        "40",
        "35",
        "Bảo lãnh khác",
        "50",
        "45",
        "Các cam kết khác",
        "60",
        "55",
    ]
    if reverse:
        rows = rows[9:] + rows[:9]
    return [
        "Nghĩa vụ nợ tiềm ẩn và các cam kết đưa ra",
        "30/06/2026",
        "31/12/2025",
        "Triệu đồng",
        *rows,
    ]


def test_deep_child_variant_is_unique_and_order_flexible() -> None:
    for reverse in (False, True):
        result = matcher.build_contingent_liabilities_variant_graph_document_v1(
            [_page(_deep_core(reverse=reverse))]
        )
        assert result["uniqueness"] == {
            "complete_region_count": 1,
            "status": "UNIQUE_FULL_MATCH",
        }
        assert result["regions"][0]["layout"]["child_depth_observed"] is True


def test_two_group_ctg_variant_does_not_require_granular_children() -> None:
    texts = [
        "Các hoạt động ngoại bảng khác mà TCTD phải chịu rủi ro đáng",
        "kể (trọng yếu)",
        "30/06/2026",
        "31/12/2025",
        "Triệu đồng",
        "Nghĩa vụ nợ tiềm ẩn",
        "100",
        "90",
        "Bảo lãnh vay vốn",
        "10",
        "9",
        "Cam kết trong nghiệp vụ L/C",
        "20",
        "18",
        "Bảo lãnh khác",
        "70",
        "63",
        "Các cam kết đưa ra",
        "200",
        "180",
        "Cam kết giao dịch hối đoái",
        "150",
        "140",
        "Cam kết khác",
        "50",
        "40",
    ]
    result = matcher.build_contingent_liabilities_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["two_group_variant_observed"] is True


def test_annual_current_and_comparative_years_are_derived_from_the_page() -> None:
    texts = _deep_core()
    texts[1:3] = ["31/12/2025", "31/12/2024"]

    result = matcher.build_contingent_liabilities_variant_graph_document_v1([_page(texts)])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"


def test_relative_year_axes_and_ocr_noisy_lc_are_generic() -> None:
    texts = [
        "Các hoạt động ngoại bảng mà Ngân hàng phải chịu rủi ro đáng",
        "kể (trọng yếu)",
        "Số cuối năm",
        "Số đầu năm",
        "Triệu VND",
        "Nghĩa vụ tiềm ẩn",
        "100",
        "90",
        "Bảo lãnh vay vốn",
        "10",
        "9",
        "Cam kết trong nghiệp vụ Lực",
        "20",
        "18",
        "Bảo lãnh khác",
        "70",
        "63",
        "Các cam kết đưa ra",
        "200",
        "180",
        "Cam kết giao dịch hối đoái",
        "150",
        "140",
        "Các cam kết khác",
        "50",
        "40",
    ]
    result = matcher.build_contingent_liabilities_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    roles = result["regions"][0]["layout"]["observed_source_roles"]
    assert "CONTINGENT_GROUP" in roles
    assert "LETTER_OF_CREDIT" in roles


def test_truncated_owner_and_grouped_payment_commitments_are_generic() -> None:
    texts = [
        "NGHĨA VỤ NỢ TIỀM ẨN VÀ CÁC CAM KẾT",
        "31.12.2025",
        "31.12.2024",
        "Triệu đồng",
        "1. Các khoản bảo lãnh",
        "100",
        "90",
        "Bảo lãnh vay vốn",
        "10",
        "9",
        "Bảo lãnh khác",
        "90",
        "81",
        "2. Cam kết thanh toán",
        "80",
        "70",
        "Thư tín dụng trả ngay",
        "30",
        "20",
        "Thư tín dụng trả chậm",
        "50",
        "50",
        "3. Các cam kết khác",
        "20",
        "10",
    ]
    result = matcher.build_contingent_liabilities_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    roles = result["regions"][0]["layout"]["observed_source_roles"]
    assert "GUARANTEE_GROUP" in roles
    assert "PAYMENT_COMMITMENT_GROUP" in roles


def test_table_can_continue_on_exactly_one_adjacent_page() -> None:
    first = _page(
        [
            "Nghĩa vụ nợ tiềm ẩn và các cam kết đưa ra",
            "Các công cụ tài chính này chủ yếu bao gồm bảo lãnh và thư tín dụng.",
        ],
        1,
    )
    second = _page(["(tiếp theo)", *_deep_core()[1:]], 2)
    result = matcher.build_contingent_liabilities_variant_graph_document_v1([first, second])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["page_span"] == [1, 2]
    assert result["regions"][0]["layout"]["single_next_page_continuation"] is True


def test_next_numbered_note_stops_cross_family_contamination() -> None:
    first = _page(
        [
            "Nghĩa vụ nợ tiềm ẩn và các cam kết đưa ra",
            "Các công cụ tài chính này chủ yếu bao gồm bảo lãnh và thư tín dụng.",
        ],
        1,
    )
    second = _page(["40.", "Giao dịch với các bên liên quan", *_deep_core()[1:]], 2)
    second["lines"][0]["bbox"] = [60, 0, 100, 20]
    result = matcher.build_contingent_liabilities_variant_graph_document_v1([first, second])
    assert result["metrics"]["complete_region_count"] == 0


def test_wrapped_vib_rows_are_joined_without_bank_rules() -> None:
    texts = [
        "Nghĩa vụ nợ tiềm ẩn và các cam kết đưa ra",
        "30/06/2026",
        "31/12/2025",
        "Triệu đồng",
        "Cam kết giao dịch",
        "hối đoái",
        "100",
        "90",
        "Cam kết mua ngoại",
        "tệ",
        "20",
        "10",
        "Cam kết giao dịch",
        "hoán đổi tiền tệ",
        "80",
        "80",
        "Cam kết trong",
        "nghiệp vụ thư tín",
        "dụng",
        "40",
        "35",
        "Bảo lãnh khác",
        "50",
        "45",
        "Các cam kết khác",
        "60",
        "55",
    ]
    result = matcher.build_contingent_liabilities_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert "FX_PARENT" in result["regions"][0]["layout"]["observed_source_roles"]


def test_primary_statement_summary_is_a_negative_control() -> None:
    result = matcher.build_contingent_liabilities_variant_graph_document_v1(
        [_page(["CÁC CHỈ TIÊU NGOÀI BÁO CÁO TÌNH HÌNH TÀI CHÍNH", *_deep_core()])]
    )
    assert result["metrics"]["complete_region_count"] == 0


def test_geographic_concentration_table_is_a_negative_control() -> None:
    result = matcher.build_contingent_liabilities_variant_graph_document_v1(
        [_page(["Mức độ tập trung theo khu vực địa lý", *_deep_core()])]
    )
    assert result["metrics"]["complete_region_count"] == 0


def test_pair_first_graph_rejects_two_full_regions_as_nonunique() -> None:
    result = matcher.build_contingent_liabilities_variant_graph_document_v1(
        [_page(_deep_core(), 1), _page(_deep_core(reverse=True), 2)]
    )
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"
    assert result["uniqueness"] == {
        "complete_region_count": 2,
        "status": "MULTIPLE_FULL_MATCHES",
    }
