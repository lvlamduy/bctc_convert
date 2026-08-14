from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _ROOT / "scripts/experiments/loan_maturity_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("loan_maturity_variant_graph_v1", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
matcher = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = matcher
_SPEC.loader.exec_module(matcher)


def _line(
    text: str,
    ordinal: int,
    *,
    x: int = 0,
    source_text: str | None = None,
) -> dict[str, object]:
    return {
        "bbox": [x, ordinal * 20, x + 80, ordinal * 20 + 14],
        "qwen35_challenger_text": None,
        "source_line_index": ordinal,
        "source_text": text if source_text is None else source_text,
        "vietocr_text": text,
    }


def _semantic_page(
    surfaces: list[tuple[str, int]],
    *,
    page_sequence: int = 2,
    primary_numeric_authority: bool = True,
    null_source: bool = False,
) -> dict[str, object]:
    return {
        "lines": [
            _line(text, ordinal, x=x, source_text=None if not null_source else "")
            | ({"source_text": None} if null_source else {})
            for ordinal, (text, x) in enumerate(surfaces)
        ],
        "page_sequence": page_sequence,
        "primary_numeric_authority": primary_numeric_authority,
    }


def _document_pages(
    semantic: dict[str, object],
    *,
    previous_lines: list[str] | None = None,
    duplicate_page: bool = False,
) -> list[dict[str, object]]:
    page_sequence = semantic["page_sequence"]
    assert isinstance(page_sequence, int)
    pages: list[dict[str, object]] = []
    if previous_lines is not None:
        pages.append(
            {
                "lines": [
                    {
                        "qwen35_challenger_text": None,
                        "source_line_index": index,
                        "vietocr_text": text,
                    }
                    for index, text in enumerate(previous_lines)
                ],
                "page_sequence": page_sequence - 1,
            }
        )
    pages.append(
        {
            "lines": [
                {
                    "qwen35_challenger_text": line["qwen35_challenger_text"],
                    "source_line_index": line["source_line_index"],
                    "vietocr_text": line["vietocr_text"],
                }
                for line in semantic["lines"]
            ],
            "page_sequence": page_sequence,
        }
    )
    if duplicate_page:
        pages.append(
            {
                "lines": [
                    {
                        "qwen35_challenger_text": line["qwen35_challenger_text"],
                        "source_line_index": line["source_line_index"],
                        "vietocr_text": line["vietocr_text"],
                    }
                    for line in semantic["lines"]
                ],
                "page_sequence": page_sequence + 1,
            }
        )
    return pages


def _semantic_pages_for_document(
    document_pages: list[dict[str, object]], target: dict[str, object]
) -> list[dict[str, object]]:
    target_sequence = target["page_sequence"]
    assert isinstance(target_sequence, int)
    result: list[dict[str, object]] = []
    for page in document_pages:
        page_sequence = page["page_sequence"]
        assert isinstance(page_sequence, int)
        if page_sequence == target_sequence:
            result.append(copy.deepcopy(target))
            continue
        page_lines = page["lines"]
        assert isinstance(page_lines, list)
        result.append(
            {
                "lines": [
                    _line(line["vietocr_text"], index) for index, line in enumerate(page_lines)
                ],
                "page_sequence": page_sequence,
                "primary_numeric_authority": True,
            }
        )
    return result


def _simple_surfaces(
    *,
    branch: str = "Phân tích dư nợ theo thời gian",
    short: str = "Nợ ngắn hạn",
    medium: str = "Nợ trung hạn",
    long: str = "Nợ dài hạn",
    owner: bool = True,
    local_units: bool = True,
) -> list[tuple[str, int]]:
    result: list[tuple[str, int]] = []
    if owner:
        result.append(("5. Cho vay khách hàng", 0))
    result.extend([(branch, 0), ("30/06/2026", 100), ("31/12/2025", 300)])
    if local_units:
        result.extend([("Triệu đồng", 100), ("Triệu đồng", 300)])
    result.extend(
        [
            (short, 0),
            ("10", 100),
            ("11", 300),
            (medium, 0),
            ("20", 100),
            ("21", 300),
            (long, 0),
            ("30", 100),
            ("31", 300),
            ("60", 100),
            ("63", 300),
        ]
    )
    return result


def test_simple_two_lane_core_total_is_one_accepted_variant_graph():
    semantic = _semantic_page(_simple_surfaces())
    result = matcher.build_loan_maturity_variant_graph_v1(_document_pages(semantic), semantic)

    assert result["status"] == "ACCEPTED_VARIANT_GRAPH"
    assert result["document_candidate_count"] == 1
    graph = result["result"]["graph"]
    assert graph["owner"]["mode"] == "SAME_PAGE_NEAREST_PRECEDING"
    assert graph["branch"]["variant"] == "TIME_WORDING"
    assert [row["role"] for row in graph["rows"]] == [
        "SHORT_TERM",
        "MEDIUM_TERM",
        "LONG_TERM",
    ]
    assert graph["total"]["variant"] == "CORE_TOTAL_ONLY"
    assert graph["arithmetic_status"] == "CORROBORATED_TYPED_POPULATIONS"
    assert graph["schema_candidate_frontier_ready"] is True
    assert result["safety"]["mapping_authority"] is False


def test_wrapped_structural_anchors_use_the_same_maturity_graph():
    semantic = _semantic_page(
        [
            ("5. Cho vay", 0),
            ("khách hàng", 0),
            ("Phân tích dư nợ theo", 0),
            ("thời gian", 0),
            ("30/06/2026", 100),
            ("31/12/2025", 300),
            ("Triệu đồng", 100),
            ("Triệu đồng", 300),
            ("Dư nợ", 0),
            ("cho vay", 0),
            ("Nợ ngắn", 0),
            ("hạn", 0),
            ("10", 100),
            ("11", 300),
            ("Nợ trung", 0),
            ("hạn", 0),
            ("20", 100),
            ("21", 300),
            ("Nợ dài", 0),
            ("hạn", 0),
            ("30", 100),
            ("31", 300),
            ("60", 100),
            ("63", 300),
        ]
    )

    result = matcher.build_loan_maturity_variant_graph_v1(_document_pages(semantic), semantic)

    assert result["status"] == "ACCEPTED_VARIANT_GRAPH"
    graph = result["result"]["graph"]
    assert graph["owner"]["surface"] == "5. Cho vay khách hàng"
    assert graph["branch"]["surface"] == "Phân tích dư nợ theo thời gian"
    assert graph["branch"]["vietocr_text"] == "Phân tích dư nợ theo thời gian"
    assert graph["intermediate_header"]["surface"] == "Dư nợ cho vay"
    assert [row["vietocr_text"] for row in graph["rows"]] == [
        "Nợ ngắn hạn",
        "Nợ trung hạn",
        "Nợ dài hạn",
    ]


@pytest.mark.parametrize(
    ("surface", "variant"),
    [
        ("Phân tích dư nợ theo thời gian", "TIME_WORDING"),
        (
            "Phân tích dư nợ cho vay theo thời hạn gốc của khoản vay",
            "ORIGINAL_TERM_WORDING",
        ),
        ("Phân tích dư nợ theo thời gian cho vay ban đầu", "INITIAL_TERM_WORDING"),
        ("Phân tích dư nợ cho vay theo thời hạn vay", "TERM_WORDING"),
        ("Phân tích dư nợ theo kỳ hạn", "TENOR_WORDING"),
        ("Phân tích dư nợ theo thời gian đáo hạn", "MATURITY_TIME_WORDING"),
    ],
)
def test_branch_wording_variants_share_one_ordered_graph(surface: str, variant: str):
    semantic = _semantic_page(_simple_surfaces(branch=surface))
    result = matcher.build_loan_maturity_variant_graph_v1(_document_pages(semantic), semantic)

    assert result["status"] == "ACCEPTED_VARIANT_GRAPH"
    assert result["result"]["graph"]["branch"]["variant"] == variant
    assert result["result"]["graph"]["branch"]["match_kind"] == (
        "EXACT_ACCENTLESS_STRUCTURAL_ANCHORS"
    )


def test_one_base_character_branch_error_requires_the_complete_topology():
    semantic = _semantic_page(_simple_surfaces(branch="Phân tíh dư nợ theo thời gian"))
    result = matcher.build_loan_maturity_variant_graph_v1(_document_pages(semantic), semantic)

    assert result["status"] == "ACCEPTED_VARIANT_GRAPH"
    assert result["result"]["graph"]["branch"]["match_kind"] == (
        "ONE_EDIT_STRUCTURAL_ANCHORS_IN_COMPLETE_TOPOLOGY"
    )

    unrelated = _semantic_page(_simple_surfaces(branch="Phân bổ dư nợ theo thời gian"))
    rejected = matcher.build_loan_maturity_variant_graph_v1(_document_pages(unrelated), unrelated)
    assert rejected["status"] == "UNRESOLVED"
    assert rejected["document_candidate_count"] == 0


def test_mbb_intermediate_header_core_margin_and_grand_total_are_preserved():
    surfaces = [
        ("5. Cho vay khách hàng", 0),
        ("Phân tích dư nợ theo thời gian:", 0),
        ("30/06/2026", 100),
        ("31/12/2025", 300),
        ("Triệu đồng", 100),
        ("Triệu đồng", 300),
        ("Dư nợ cho vay", 0),
        ("Nợ ngắn hạn", 0),
        ("10", 100),
        ("11", 300),
        ("Nợ trùng hạn", 0),
        ("20", 100),
        ("21", 300),
        ("Nợ dài hạn", 0),
        ("30", 100),
        ("31", 300),
        ("60", 100),
        ("63", 300),
        ("Các khoản cho vay margin chứng khoán và ứng trước khách hàng", 0),
        ("tại MBS", 0),
        ("5", 100),
        ("7", 300),
        ("65", 100),
        ("70", 300),
    ]
    semantic = _semantic_page(surfaces)
    result = matcher.build_loan_maturity_variant_graph_v1(_document_pages(semantic), semantic)

    graph = result["result"]["graph"]
    assert result["status"] == "ACCEPTED_VARIANT_GRAPH"
    assert graph["intermediate_header"]["surface"] == "Dư nợ cho vay"
    assert graph["rows"][1]["match_kind"] == "EXACT_ACCENTLESS_ALIAS"
    assert graph["optional_margin"]["report_norm_id_candidate"] == 5747
    assert graph["optional_margin"]["label_surface"].endswith("tại MBS")
    assert graph["total"]["variant"] == "CORE_SUBTOTAL_MARGIN_GRAND_TOTAL"
    assert [item["surface"] for item in graph["total"]["core_values"]] == ["60", "63"]
    assert [item["surface"] for item in graph["total"]["grand_values"]] == ["65", "70"]


def test_next_numbered_disclosure_cannot_be_misread_as_optional_margin():
    surfaces = _simple_surfaces() + [
        ("5. DỰ PHÒNG RỦI RO CHO VAY KHÁCH HÀNG", 0),
        ("Dự phòng giao dịch ký quỹ", 0),
        ("5", 100),
        ("7", 300),
    ]
    semantic = _semantic_page(surfaces)
    result = matcher.build_loan_maturity_variant_graph_v1(_document_pages(semantic), semantic)

    assert result["status"] == "ACCEPTED_VARIANT_GRAPH"
    graph = result["result"]["graph"]
    assert graph["optional_margin"] is None
    assert graph["total"]["variant"] == "CORE_TOTAL_ONLY"


def test_unnumbered_next_family_cannot_leak_a_margin_like_row_into_maturity():
    surfaces = _simple_surfaces() + [
        ("Phân tích dư nợ theo đối tượng khách hàng", 0),
        ("Cho vay giao dịch ký quỹ", 0),
        ("5", 100),
        ("7", 300),
    ]
    semantic = _semantic_page(surfaces)

    result = matcher.build_loan_maturity_variant_graph_v1(_document_pages(semantic), semantic)

    assert result["status"] == "ACCEPTED_VARIANT_GRAPH"
    graph = result["result"]["graph"]
    assert graph["optional_margin"] is None
    assert graph["total"]["variant"] == "CORE_TOTAL_ONLY"


def test_vpb_split_dates_margin_and_grand_total_without_core_subtotal():
    surfaces = [
        ("Cho vay khách hàng", 0),
        ("Phân tích dư nợ theo thời gian cho vay ban đầu", 0),
        ("Ngày 30 tháng 6", 100),
        ("Ngày 31 tháng 12", 300),
        ("năm 2026", 100),
        ("năm 2025", 300),
        ("Triệu đồng", 100),
        ("Triệu đồng", 300),
        ("Nợ ngắn hạn", 0),
        ("10", 100),
        ("11", 300),
        ("Nợ trung hạn", 0),
        ("20", 100),
        ("21", 300),
        ("Nợ dài hạn", 0),
        ("30", 100),
        ("31", 300),
        ("Cho vay ký quỹ", 0),
        ("5", 100),
        ("7", 300),
        ("65", 100),
        ("70", 300),
    ]
    semantic = _semantic_page(surfaces)
    result = matcher.build_loan_maturity_variant_graph_v1(_document_pages(semantic), semantic)

    graph = result["result"]["graph"]
    assert result["status"] == "ACCEPTED_VARIANT_GRAPH"
    assert graph["branch"]["variant"] == "INITIAL_TERM_WORDING"
    assert graph["period_mode"] == "LOCAL_SPLIT_DATES"
    assert graph["total"]["variant"] == "MARGIN_GRAND_TOTAL_NO_CORE_SUBTOTAL"
    assert graph["total"]["core_values"] == []


def test_vib_four_typed_lanes_keep_percentages_and_close_each_population():
    surfaces = [
        ("Cho vay khách hàng", 0),
        ("Phân tích dư nợ theo thời gian cho vay gốc", 0),
        ("30/06/2026", 100),
        ("31/12/2025", 300),
        ("Triệu đồng", 100),
        ("%", 200),
        ("Triệu đồng", 300),
        ("%", 400),
        ("Nợ ngắn hạn", 0),
        ("10", 100),
        ("40,00", 200),
        ("11", 300),
        ("41,00", 400),
        ("Nợ trung hạn", 0),
        ("20", 100),
        ("20,00", 200),
        ("21", 300),
        ("20,00", 400),
        ("Nợ dài hạn", 0),
        ("30", 100),
        ("40,00", 200),
        ("31", 300),
        ("39,00", 400),
        ("60", 100),
        ("100,00", 200),
        ("63", 300),
        ("100,00", 400),
    ]
    semantic = _semantic_page(surfaces)
    result = matcher.build_loan_maturity_variant_graph_v1(_document_pages(semantic), semantic)

    graph = result["result"]["graph"]
    assert result["status"] == "ACCEPTED_VARIANT_GRAPH"
    assert graph["unit_scope"]["lane_types"] == [
        "MONEY",
        "PERCENT",
        "MONEY",
        "PERCENT",
    ]
    assert graph["arithmetic_status"] == "CORROBORATED_TYPED_POPULATIONS"
    assert all(len(row["values"]) == 4 for row in graph["rows"])
    assert result["safety"]["percentage_lanes_silently_discarded"] is False


def test_previous_page_owner_and_document_unit_are_generic_inheritance_variants():
    semantic = _semantic_page(_simple_surfaces(owner=False, local_units=False), page_sequence=3)
    result = matcher.build_loan_maturity_variant_graph_v1(
        _document_pages(
            semantic,
            previous_lines=["5. Cho vay khách hàng", "Đơn vị: Triệu VND"],
        ),
        semantic,
    )

    graph = result["result"]["graph"]
    assert result["status"] == "ACCEPTED_VARIANT_GRAPH"
    assert graph["owner"]["mode"] == "IMMEDIATE_PREVIOUS_PAGE"
    assert graph["unit_scope"]["mode"] == "INHERITED_NEAREST_PRECEDING_DOCUMENT_UNIT"


def test_one_transformer_edit_is_tolerated_only_inside_complete_ordered_topology():
    semantic = _semantic_page(_simple_surfaces(short="Nợi ngắn hạn"))
    result = matcher.build_loan_maturity_variant_graph_v1(_document_pages(semantic), semantic)
    assert result["status"] == "ACCEPTED_VARIANT_GRAPH"
    assert result["result"]["graph"]["rows"][0]["match_kind"] == (
        "ONE_EDIT_ALIAS_IN_COMPLETE_ORDERED_TOPOLOGY"
    )
    assert result["result"]["graph"]["rows"][0]["semantic_source"] == "VIETOCR_TRANSFORMER"
    assert result["metrics"]["qwen_semantic_match_use_count"] == 0

    # A diagnostic Qwen value must not change the semantic decision.
    semantic["lines"][6]["qwen35_challenger_text"] = "Nợ dài hạn"
    with_diagnostic = matcher.build_loan_maturity_variant_graph_v1(
        _document_pages(semantic), semantic
    )
    assert with_diagnostic["status"] == "ACCEPTED_VARIANT_GRAPH"
    assert with_diagnostic["result"]["graph"]["rows"][0]["label_surface"] == "Nợi ngắn hạn"
    assert with_diagnostic["metrics"]["qwen_semantic_match_use_count"] == 0

    twice = _semantic_page(_simple_surfaces(short="Nợi ngắn hạn", medium="Nợi trung hạn"))
    unresolved = matcher.build_loan_maturity_variant_graph_v1(_document_pages(twice), twice)
    assert unresolved["status"] == "UNRESOLVED"
    assert unresolved["document_candidate_count"] == 0


@pytest.mark.parametrize("surface", ["Nợ trungg hạn", "Nợ trng hạn", "Nợ trung hạ"])
def test_one_inserted_or_deleted_base_character_is_bounded_by_ordered_roles(surface: str):
    semantic = _semantic_page(_simple_surfaces(medium=surface))
    result = matcher.build_loan_maturity_variant_graph_v1(_document_pages(semantic), semantic)

    assert result["status"] == "ACCEPTED_VARIANT_GRAPH"
    assert result["result"]["graph"]["rows"][1]["match_kind"] == (
        "ONE_EDIT_ALIAS_IN_COMPLETE_ORDERED_TOPOLOGY"
    )


def test_whole_document_near_neighbours_do_not_inflate_complete_graph_denominator():
    semantic = _semantic_page(_simple_surfaces(), page_sequence=4)
    document = [
        {
            "page_sequence": 1,
            "lines": [
                {
                    "qwen35_challenger_text": None,
                    "source_line_index": index,
                    "vietocr_text": text,
                }
                for index, text in enumerate(
                    ["Nợ ngắn hạn", "1", "2", "Nợ trung hạn", "3", "4", "Nợ dài hạn"]
                )
            ],
        },
        {
            "page_sequence": 2,
            "lines": [
                {
                    "qwen35_challenger_text": None,
                    "source_line_index": index,
                    "vietocr_text": text,
                }
                for index, text in enumerate(
                    [
                        "Phân tích chất lượng nợ cho vay",
                        "Nợ ngắn hạn",
                        "Nợ trung hạn",
                        "Nợ dài hạn",
                    ]
                )
            ],
        },
        {
            "page_sequence": 3,
            "lines": [
                {
                    "qwen35_challenger_text": None,
                    "source_line_index": index,
                    "vietocr_text": text,
                }
                for index, text in enumerate(
                    [
                        "Phân tích dư nợ theo thời gian",
                        "Nợ dài hạn",
                        "1",
                        "2",
                        "Nợ trung hạn",
                        "3",
                        "4",
                        "Nợ ngắn hạn",
                        "5",
                        "6",
                    ]
                )
            ],
        },
        *_document_pages(semantic),
    ]
    result = matcher.build_loan_maturity_variant_graph_v1(document, semantic)

    assert result["status"] == "ACCEPTED_VARIANT_GRAPH"
    assert result["document_candidate_count"] == 1
    assert result["result"]["graph"]["branch"]["source_line_index"] == 1


def test_complete_document_scan_selects_once_and_rejects_semantic_axis_drift():
    semantic = _semantic_page(_simple_surfaces(owner=False, local_units=False), page_sequence=3)
    document = [
        {"lines": [], "page_sequence": 1},
        *_document_pages(
            semantic,
            previous_lines=["5. Cho vay khách hàng", "Đơn vị: Triệu VND"],
        ),
    ]
    semantic_pages = _semantic_pages_for_document(document, semantic)

    result = matcher.scan_loan_maturity_variant_graph_document_v1(document, semantic_pages)
    assert result["status"] == "ACCEPTED_VARIANT_GRAPH"
    assert result["document_candidate_count"] == 1
    assert result["result"]["graph"]["owner"]["mode"] == "IMMEDIATE_PREVIOUS_PAGE"

    drifted = copy.deepcopy(semantic_pages)
    drifted[1]["lines"][0]["vietocr_text"] = "Tài sản khác"
    with pytest.raises(matcher.LoanMaturityVariantGraphV1Error):
        matcher.scan_loan_maturity_variant_graph_document_v1(document, drifted)


def test_whole_document_duplicate_complete_graph_fails_closed():
    semantic = _semantic_page(_simple_surfaces())
    result = matcher.build_loan_maturity_variant_graph_v1(
        _document_pages(semantic, duplicate_page=True), semantic
    )
    assert result["status"] == "UNRESOLVED"
    assert result["document_candidate_count"] == 2
    assert result["unresolved_reasons"] == ["DOCUMENT_COMPLETE_GRAPH_NOT_UNIQUE"]


def test_transformer_only_terminal_page_can_resolve_structure_but_not_numeric_truth():
    semantic = _semantic_page(_simple_surfaces(), primary_numeric_authority=False, null_source=True)
    result = matcher.build_loan_maturity_variant_graph_v1(_document_pages(semantic), semantic)
    graph = result["result"]["graph"]
    assert result["status"] == "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"
    assert graph["arithmetic_status"] == "NOT_EVALUATED_NO_PRIMARY_NUMERIC_AUTHORITY"
    assert graph["schema_candidate_frontier_ready"] is False
    assert all(
        item["numeric_source_authoritative"] is False
        for row in graph["rows"]
        for item in row["values"]
    )


def test_total_lane_presence_is_required_even_without_numeric_authority():
    surfaces = _simple_surfaces()[:-2]
    semantic = _semantic_page(
        surfaces,
        primary_numeric_authority=False,
        null_source=True,
    )

    result = matcher.build_loan_maturity_variant_graph_v1(_document_pages(semantic), semantic)

    assert result["status"] == "UNRESOLVED"
    assert "CORE_TOTAL_VALUE_LANES_NOT_RESOLVED" in result["unresolved_reasons"]


def test_margin_variant_requires_a_grand_total_even_without_numeric_authority():
    surfaces = [
        ("Cho vay khách hàng", 0),
        ("Phân tích dư nợ theo thời gian cho vay ban đầu", 0),
        ("30/06/2026", 100),
        ("31/12/2025", 300),
        ("Triệu đồng", 100),
        ("Triệu đồng", 300),
        ("Nợ ngắn hạn", 0),
        ("10", 100),
        ("11", 300),
        ("Nợ trung hạn", 0),
        ("20", 100),
        ("21", 300),
        ("Nợ dài hạn", 0),
        ("30", 100),
        ("31", 300),
        ("Cho vay ký quỹ", 0),
        ("5", 100),
        ("7", 300),
    ]
    semantic = _semantic_page(
        surfaces,
        primary_numeric_authority=False,
        null_source=True,
    )

    result = matcher.build_loan_maturity_variant_graph_v1(_document_pages(semantic), semantic)

    assert result["status"] == "UNRESOLVED"
    assert "GRAND_TOTAL_VALUE_LANES_NOT_RESOLVED" in result["unresolved_reasons"]


def test_arithmetic_population_mismatch_and_replay_tamper_fail_closed():
    surfaces = _simple_surfaces()
    surfaces[-1] = ("64", 300)
    semantic = _semantic_page(surfaces)
    result = matcher.build_loan_maturity_variant_graph_v1(_document_pages(semantic), semantic)
    assert result["status"] == "UNRESOLVED"
    assert result["unresolved_reasons"] == ["ARITHMETIC_POPULATION_VETO"]

    tampered = copy.deepcopy(result)
    tampered["status"] = "ACCEPTED_VARIANT_GRAPH"
    with pytest.raises(matcher.LoanMaturityVariantGraphV1Error):
        matcher.validate_loan_maturity_variant_graph_replay_v1(
            tampered, _document_pages(semantic), semantic
        )
