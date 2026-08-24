from __future__ import annotations

import copy

import pytest

import bctc_ai.evaluation.accounting_semantic_region_graph_v1 as semantic_region_module
from bctc_ai.evaluation.accounting_scoped_table_graph_v1 import (
    AccountingScopedTableGraphV1Error,
)
from bctc_ai.evaluation.accounting_semantic_region_graph_v1 import (
    SPEC_FORMAT_VERSION,
    AccountingSemanticRegionGraphV1Error,
    ScopedTableEnforcementV1,
    build_accounting_semantic_region_graph_v1,
    validate_accounting_semantic_region_graph_replay_v1,
)


def _line(index: int, text: str, x1: int, y1: int, x2: int, y2: int) -> dict:
    return {
        "bbox": [x1, y1, x2, y2],
        "source_line_index": index,
        "source_text": text,
        "vietocr_text": text,
    }


def _page(sequence: int, lines: list[dict]) -> dict:
    return {
        "lines": lines,
        "page_height": 1_500,
        "page_sequence": sequence,
        "page_width": 1_000,
    }


def _scoped_limits() -> dict:
    return {
        "axis_tolerance_ppm": 120_000,
        "continuation_page_budget": 0,
        "max_owner_distance_lines": 64,
        "max_role_gap_lines": 24,
        "max_wrap_lines": 3,
        "minimum_cell_row_overlap_ppm": 400_000,
        "unlabeled_total_gap_jitter_ppm": 100_000,
        "unlabeled_total_max_gap_lines": 4,
        "unlabeled_total_max_numeric_columns": 8,
        "unlabeled_total_min_numeric_columns": 2,
    }


def _spec() -> dict:
    return {
        "branch_aliases": [
            "Phân tích theo loại nguyên liệu",
            "Phân tích hàng tồn kho theo loại nguyên liệu",
            "Theo loại nguyên liệu",
        ],
        "context_classes": [
            {
                "aliases": ["Hàng tồn kho"],
                "context_id": "INVENTORY_OWNER",
                "disposition": "REQUIRED_OWNER",
            },
            {
                "aliases": ["Chi phí sản xuất kinh doanh dở dang"],
                "context_id": "WORK_IN_PROGRESS_VETO",
                "disposition": "HARD_VETO",
            },
        ],
        "family_id": "INVENTORY_BY_MATERIAL",
        "format_version": SPEC_FORMAT_VERSION,
        "limits": {
            "branch_line_span": 2,
            "context_page_budget": 2,
            "maximum_body_lines_per_page": 80,
            "row_label_line_span": 2,
        },
        "required_owner_context_id": "INVENTORY_OWNER",
        "row_axis": [
            {
                "aliases": ["Nguyên vật liệu"],
                "bounded_edit_on_exact_miss": True,
                "semantic_id": "RAW_MATERIAL",
            },
            {
                "aliases": ["Thành phẩm"],
                "bounded_edit_on_exact_miss": True,
                "semantic_id": "FINISHED_GOODS",
            },
            {
                "aliases": ["Công cụ dụng cụ"],
                "bounded_edit_on_exact_miss": True,
                "semantic_id": "TOOLS",
            },
        ],
        "scoped_table": {
            "continuation_aliases": ["Tiếp theo"],
            "hard_veto_scope_aliases": ["Chi phí sản xuất kinh doanh dở dang"],
            "layout_modes": ["ROLES_AS_ROWS"],
            "limits": _scoped_limits(),
            "require_trailing_total_for_roles_as_columns": False,
            "trailing_total_aliases": [],
        },
        "source_only_ambiguities": [
            {
                "aliases": ["Sản phẩm và hàng hóa"],
                "ambiguity_id": "MIXED_PRODUCT_ROW",
                "candidate_semantic_ids": ["FINISHED_GOODS", "RAW_MATERIAL"],
                "reason": "MIXED_SOURCE_POPULATION",
            }
        ],
        "structural_reset_aliases": ["Tài sản cố định"],
    }


def _component_spec() -> dict:
    spec = _spec()
    spec["branch_components"] = [
        {
            "aliases": ["Theo loại nguyên liệu"],
            "bounded_edit_on_exact_miss": True,
            "component_id": "MATERIAL_BRANCH_COMPONENT",
        }
    ]
    return spec


def _table_lines(
    *,
    owner: str = "Hàng tồn kho",
    branch: str = "Phân tích theo loại nguyên liệu",
    rows: list[str] | None = None,
) -> list[dict]:
    rows = rows or ["Nguyên vật liệu", "Thành phẩm"]
    lines = [
        _line(0, owner, 40, 40, 350, 70),
        _line(1, branch, 40, 110, 650, 140),
    ]
    for ordinal, row in enumerate(rows):
        y = 200 + ordinal * 50
        lines.extend(
            [
                _line(2 + ordinal * 2, row, 70, y, 500, y + 28),
                _line(3 + ordinal * 2, str((ordinal + 1) * 100), 730, y, 820, y + 28),
            ]
        )
    return lines


def _rows(result: dict) -> list[dict]:
    return result["regions"][0]["row_proposals"]


def test_second_synthetic_family_reuses_generic_engine_and_shared_primitives() -> None:
    result = build_accounting_semantic_region_graph_v1([_page(1, _table_lines())], _spec())

    assert result["family_id"] == "INVENTORY_BY_MATERIAL"
    assert [row["semantic_id"] for row in _rows(result)] == [
        "RAW_MATERIAL",
        "FINISHED_GOODS",
    ]
    region = result["regions"][0]
    assert region["adaptive_geometry_v2"]["format_version"] == (
        "ADAPTIVE_ACCOUNTING_TABLE_GEOMETRY_V2"
    )
    assert region["shared_scoped_table_v1"]["status"] == (
        "SHARED_SCOPED_TABLE_PROPOSAL_RETAINED_NO_MAPPING_AUTHORITY"
    )
    assert region["promotion_eligible"] is True
    assert result["safety"]["family_schema_or_report_norm_id_known"] is False


def test_owner_phrase_nested_in_branch_does_not_shadow_real_owner() -> None:
    result = build_accounting_semantic_region_graph_v1(
        [
            _page(
                1,
                _table_lines(branch="Phân tích hàng tồn kho theo loại nguyên liệu"),
            )
        ],
        _spec(),
    )

    assert len(result["regions"]) == 1
    assert result["regions"][0]["shared_scoped_table_v1"]["status"] == (
        "SHARED_SCOPED_TABLE_PROPOSAL_RETAINED_NO_MAPPING_AUTHORITY"
    )


@pytest.mark.parametrize(
    ("heading", "tier"),
    [
        ("Chi tiết được trình bày theo loại nguyên liệu như sau:", "EXACT_ACCENTED_ALIAS"),
        ("Chi tiet duoc trinh bay theo loai nguyen lieu", "EXACT_ACCENTLESS_ALIAS"),
        (
            "Chi tiết trình bày theo loại nguyên liệux",
            "ONE_BASE_CHARACTER_EDIT_AFTER_ALL_EXACT_MISSES",
        ),
    ],
)
def test_declarative_branch_component_fallback_is_token_bounded(heading: str, tier: str) -> None:
    result = build_accounting_semantic_region_graph_v1(
        [_page(1, _table_lines(branch=heading))], _component_spec()
    )

    branch = result["regions"][0]["branch"]
    assert branch["match_basis"] == "DECLARATIVE_BRANCH_COMPONENT"
    assert branch["matched_component_ids"] == ["MATERIAL_BRANCH_COMPONENT"]
    assert branch["match_tier"] == tier


def test_full_exact_branch_alias_precedes_component_and_component_precedes_full_fuzzy() -> None:
    spec = _component_spec()
    exact = build_accounting_semantic_region_graph_v1([_page(1, _table_lines())], spec)
    component = build_accounting_semantic_region_graph_v1(
        [
            _page(
                1,
                _table_lines(branch="Phân tíxh theo loại nguyên liệu"),
            )
        ],
        spec,
    )

    assert exact["regions"][0]["branch"]["match_basis"] == "FULL_BRANCH_ALIAS"
    assert component["regions"][0]["branch"]["match_basis"] == ("DECLARATIVE_BRANCH_COMPONENT")
    assert component["regions"][0]["branch"]["match_tier"] == "EXACT_ACCENTED_ALIAS"


def test_split_component_requires_cohesive_nonvalue_lines_and_does_not_swallow_first_row() -> None:
    cohesive = _table_lines(branch="Theo loại nguyên liệu")
    cohesive[1:2] = [
        _line(1, "Chi tiết theo loại", 40, 110, 500, 132),
        _line(20, "nguyên liệu", 40, 136, 300, 158),
    ]
    result = build_accounting_semantic_region_graph_v1([_page(1, cohesive)], _component_spec())

    branch = result["regions"][0]["branch"]
    assert len(branch["evidence"]) == 2
    assert [row["semantic_id"] for row in result["regions"][0]["row_proposals"]] == [
        "RAW_MATERIAL",
        "FINISHED_GOODS",
    ]

    numeric_fence = copy.deepcopy(cohesive)
    numeric_fence.insert(2, _line(21, "100", 730, 133, 820, 156))
    assert (
        build_accounting_semantic_region_graph_v1([_page(1, numeric_fence)], _component_spec())[
            "regions"
        ]
        == []
    )

    distant = copy.deepcopy(cohesive)
    distant[2]["bbox"] = [40, 180, 300, 202]
    assert (
        build_accounting_semantic_region_graph_v1([_page(1, distant)], _component_spec())["regions"]
        == []
    )


def test_component_does_not_match_inside_a_longer_token() -> None:
    result = build_accounting_semantic_region_graph_v1(
        [
            _page(
                1,
                _table_lines(branch="Chi tiết theo phânloại nguyên liệu"),
            )
        ],
        _component_spec(),
    )

    assert result["regions"] == []
    assert result["metrics"]["branch_candidate_count"] == 0


def test_overlapping_exact_branch_suppresses_start_earlier_one_edit_candidate() -> None:
    spec = _spec()
    spec["branch_aliases"] = ["Alpha beta", "betx gamma"]
    spec["limits"]["branch_line_span"] = 2
    lines = [
        _line(0, "Hàng tồn kho", 40, 40, 350, 70),
        _line(1, "Alpha", 40, 110, 220, 132),
        _line(2, "betx", 40, 136, 220, 158),
        _line(3, "gamma", 40, 162, 240, 184),
        _line(4, "Nguyên vật liệu", 70, 230, 500, 258),
        _line(5, "100", 730, 230, 820, 258),
        _line(6, "Thành phẩm", 70, 280, 500, 308),
        _line(7, "200", 730, 280, 820, 308),
    ]

    result = build_accounting_semantic_region_graph_v1([_page(1, lines)], spec)

    assert result["metrics"]["branch_enumerated_candidate_count"] == 2
    assert result["metrics"]["branch_overlap_suppressed_candidate_count"] == 1
    assert result["regions"][0]["branch"]["surface"] == "betx gamma"
    assert result["regions"][0]["branch"]["match_tier"] == "EXACT_ACCENTED_ALIAS"
    assert (
        result["safety"]["branch_lower_tier_can_override_overlapping_higher_tier_candidate"]
        is False
    )


def test_spatially_distinct_exact_and_one_edit_branches_both_remain_candidates() -> None:
    spec = _spec()
    spec["branch_aliases"] = ["Alpha beta", "Delta epsilon"]
    lines = [
        *_table_lines(branch="Alpha beta"),
        _line(20, "Hàng tồn kho", 40, 380, 350, 410),
        _line(21, "Delta epsilox", 40, 450, 500, 480),
        _line(22, "Nguyên vật liệu", 70, 540, 500, 568),
        _line(23, "300", 730, 540, 820, 568),
        _line(24, "Thành phẩm", 70, 590, 500, 618),
        _line(25, "400", 730, 590, 820, 618),
    ]

    result = build_accounting_semantic_region_graph_v1([_page(1, lines)], spec)

    assert result["metrics"]["branch_candidate_count"] == 2
    assert [region["branch"]["match_tier"] for region in result["regions"]] == [
        "EXACT_ACCENTED_ALIAS",
        "ONE_BASE_CHARACTER_EDIT_AFTER_ALL_EXACT_MISSES",
    ]
    assert result["safety"]["spatially_distinct_lower_tier_branch_candidates_are_retained"] is True


def test_priority_interval_selector_reserves_suppressed_higher_tier_coverage() -> None:
    candidates = [
        {"candidate_id": "high-a", "priority": 0, "start": 0, "stop": 2},
        {"candidate_id": "high-b", "priority": 0, "start": 1, "stop": 3},
        {"candidate_id": "low", "priority": 1, "start": 2, "stop": 3},
    ]

    selected, coverage, suppressed = semantic_region_module._select_priority_intervals(
        candidates,
        priority_key=lambda item: item["priority"],
        same_priority_key=lambda item: (item["start"], item["candidate_id"]),
        is_fail_closed_blocker=lambda _item: False,
    )

    assert [item["candidate_id"] for item in selected] == ["high-a"]
    assert coverage == {0, 1}
    assert suppressed == 2


def test_branch_priority_reservation_blocks_transitive_lower_tier_leak() -> None:
    spec = _spec()
    spec["branch_aliases"] = ["Alpha Beta", "Beta Gamma", "Gammb"]
    spec["limits"]["branch_line_span"] = 2
    lines = [
        _line(0, "Hàng tồn kho", 40, 40, 350, 70),
        _line(1, "Alpha", 40, 110, 220, 132),
        _line(2, "Beta", 40, 136, 220, 158),
        _line(3, "Gamma", 40, 162, 240, 184),
        _line(4, "Nguyên vật liệu", 70, 230, 500, 258),
        _line(5, "100", 730, 230, 820, 258),
        _line(6, "Thành phẩm", 70, 280, 500, 308),
        _line(7, "200", 730, 280, 820, 308),
    ]

    result = build_accounting_semantic_region_graph_v1([_page(1, lines)], spec)

    assert result["regions"] == []
    assert result["metrics"]["branch_enumerated_candidate_count"] == 3
    assert result["metrics"]["branch_candidate_count"] == 1
    assert result["metrics"]["branch_overlap_suppressed_candidate_count"] == 2
    assert result["near_regions"][0]["branch"]["surface"] == "Alpha Beta"


def test_short_hard_veto_does_not_gain_undeclared_subsequence_authority() -> None:
    spec = _component_spec()
    spec["context_classes"][1]["aliases"] = ["Khác"]
    narrative = _table_lines(branch="Theo loại nguyên liệu")
    narrative.insert(1, _line(20, "Nội dung khác", 40, 80, 350, 105))

    accepted = build_accounting_semantic_region_graph_v1([_page(1, narrative)], spec)
    assert len(accepted["regions"]) == 1

    exact = copy.deepcopy(narrative)
    exact[1]["source_text"] = exact[1]["vietocr_text"] = "Khác"
    vetoed = build_accounting_semantic_region_graph_v1([_page(1, exact)], spec)
    assert vetoed["regions"] == []
    assert vetoed["near_regions"][0]["reason"] == (
        "CLOSEST_CONTEXT_IS_HARD_VETO_OR_STRUCTURAL_RESET"
    )


def test_subsequence_fence_policy_is_hard_veto_only_and_reset_alias_bounded() -> None:
    owner_policy = _component_spec()
    owner_policy["context_classes"][0]["allow_token_subsequence_fence"] = True
    with pytest.raises(
        AccountingSemanticRegionGraphV1Error, match="disposition repeats or drifted"
    ):
        build_accounting_semantic_region_graph_v1([_page(1, _table_lines())], owner_policy)

    undeclared_reset = _component_spec()
    undeclared_reset["structural_reset_component_aliases"] = ["Khoản mục không khai báo"]
    with pytest.raises(
        AccountingSemanticRegionGraphV1Error,
        match="component aliases must be declared reset aliases",
    ):
        build_accounting_semantic_region_graph_v1([_page(1, _table_lines())], undeclared_reset)


def test_branch_heading_containing_owner_phrase_is_not_owner_by_itself() -> None:
    lines = _table_lines(branch="Phân tích hàng tồn kho theo loại nguyên liệu")[1:]

    result = build_accounting_semantic_region_graph_v1([_page(1, lines)], _spec())

    assert result["regions"] == []
    assert result["near_regions"][0]["reason"] == (
        "EXPLICIT_OWNER_NOT_FOUND_INSIDE_CONTEXT_PAGE_BUDGET"
    )


@pytest.mark.parametrize(
    ("surface", "tier"),
    [
        ("Nguyen vat lieu", "EXACT_ACCENTLESS_ALIAS"),
        ("Nguyên vật liệux", "ONE_BASE_CHARACTER_EDIT_AFTER_ALL_EXACT_MISSES"),
    ],
)
def test_accentless_and_bounded_edit_are_semantic_proposals(surface: str, tier: str) -> None:
    result = build_accounting_semantic_region_graph_v1(
        [_page(1, _table_lines(rows=[surface, "Thành phẩm"]))], _spec()
    )

    row = _rows(result)[0]
    assert row["semantic_id"] == "RAW_MATERIAL"
    assert row["match_tier"] == tier


def test_one_edit_is_not_consulted_when_any_exact_candidate_exists() -> None:
    spec = _spec()
    spec["row_axis"].append(
        {
            "aliases": ["Nguyên vật liệux"],
            "bounded_edit_on_exact_miss": True,
            "semantic_id": "NEAR_RAW_MATERIAL",
        }
    )
    result = build_accounting_semantic_region_graph_v1([_page(1, _table_lines())], spec)

    row = _rows(result)[0]
    assert row["semantic_id"] == "RAW_MATERIAL"
    assert row["candidate_semantic_ids"] == ["RAW_MATERIAL"]
    assert row["match_tier"] == "EXACT_ACCENTED_ALIAS"


def test_exact_semantic_and_source_only_alias_collision_fails_closed() -> None:
    spec = _spec()
    spec["source_only_ambiguities"].append(
        {
            "aliases": ["Nguyên vật liệu"],
            "ambiguity_id": "RAW_MATERIAL_COLLISION",
            "candidate_semantic_ids": ["FINISHED_GOODS", "RAW_MATERIAL"],
            "reason": "EXACT_SOURCE_SCOPE_COLLISION",
        }
    )
    result = build_accounting_semantic_region_graph_v1([_page(1, _table_lines())], spec)

    row = _rows(result)[0]
    assert row["semantic_id"] is None
    assert row["status"] == "SOURCE_ONLY_AMBIGUOUS"
    assert row["candidate_semantic_ids"] == ["FINISHED_GOODS", "RAW_MATERIAL"]
    assert row["match_tier"] == "EXACT_ACCENTED_ALIAS"


def test_declared_source_only_ambiguity_is_retained_without_promotion() -> None:
    result = build_accounting_semantic_region_graph_v1(
        [_page(1, _table_lines(rows=["Nguyên vật liệu", "Sản phẩm và hàng hóa"]))],
        _spec(),
    )

    row = _rows(result)[1]
    assert row["semantic_id"] is None
    assert row["status"] == "SOURCE_ONLY_AMBIGUOUS"
    assert row["candidate_semantic_ids"] == ["FINISHED_GOODS", "RAW_MATERIAL"]


def test_closest_reset_vetoes_an_earlier_owner() -> None:
    lines = _table_lines()
    lines.insert(1, _line(20, "Tài sản cố định", 40, 80, 400, 105))

    result = build_accounting_semantic_region_graph_v1([_page(1, lines)], _spec())

    assert result["regions"] == []
    assert (
        result["near_regions"][0]["owner_context"]["closest_context_event"]["context_id"]
        == "STRUCTURAL_RESET"
    )


@pytest.mark.parametrize(
    ("first", "second", "context_id"),
    [
        ("Tài sản", "cố định", "STRUCTURAL_RESET"),
        (
            "Chi phí sản xuất kinh doanh",
            "dở dang",
            "WORK_IN_PROGRESS_VETO",
        ),
    ],
)
def test_wrapped_context_event_plan_fences_reset_and_hard_veto(
    first: str,
    second: str,
    context_id: str,
) -> None:
    spec = _spec()
    spec["limits"]["context_line_span"] = 2
    lines = [
        _line(0, "Hàng tồn kho", 40, 40, 350, 70),
        _line(1, first, 40, 90, 600, 112),
        _line(2, second, 40, 116, 350, 138),
        _line(3, "Theo loại nguyên liệu", 40, 190, 650, 218),
        _line(4, "Nguyên vật liệu", 70, 260, 500, 288),
        _line(5, "100", 730, 260, 820, 288),
        _line(6, "Thành phẩm", 70, 310, 500, 338),
        _line(7, "200", 730, 310, 820, 338),
    ]

    result = build_accounting_semantic_region_graph_v1([_page(1, lines)], spec)

    assert result["regions"] == []
    event = result["near_regions"][0]["owner_context"]["closest_context_event"]
    assert event["context_id"] == context_id
    assert len(event["evidence"]) == 2
    assert result["metrics"]["context_event_wrapped_count"] == 1
    assert result["safety"]["context_event_plan_is_reused_for_branch_body_and_owner_scans"] is True


@pytest.mark.parametrize(
    ("hard_suffix", "match_tier"),
    [
        ("của khách hàng", "EXACT_ACCENTED_ALIAS"),
        ("cua khach hang", "EXACT_ACCENTLESS_ALIAS"),
        ("củ khách hàng", "ONE_BASE_CHARACTER_EDIT_AFTER_ALL_EXACT_MISSES"),
    ],
)
def test_overlapping_hard_veto_precedes_exact_owner_across_all_text_tiers(
    hard_suffix: str,
    match_tier: str,
) -> None:
    spec = _spec()
    spec["context_classes"][0]["aliases"] = ["Tiền gửi"]
    spec["context_classes"][1]["aliases"] = ["Tiền gửi của khách hàng"]
    spec["limits"]["context_line_span"] = 2
    lines = [
        _line(0, "Tiền gửi", 40, 40, 350, 62),
        _line(1, hard_suffix, 40, 66, 400, 88),
        _line(2, "Theo loại nguyên liệu", 40, 150, 650, 178),
        _line(3, "Nguyên vật liệu", 70, 220, 500, 248),
        _line(4, "100", 730, 220, 820, 248),
        _line(5, "Thành phẩm", 70, 270, 500, 298),
        _line(6, "200", 730, 270, 820, 298),
    ]

    result = build_accounting_semantic_region_graph_v1([_page(1, lines)], spec)

    assert result["regions"] == []
    closest = result["near_regions"][0]["owner_context"]["closest_context_event"]
    assert closest["context_id"] == "WORK_IN_PROGRESS_VETO"
    assert closest["match_tier"] == match_tier
    assert len(closest["evidence"]) == 2


@pytest.mark.parametrize("second_hard_alias", ["Beta Gamma", "Betx Gamma"])
def test_all_hard_interval_coverage_blocks_transitive_owner_leak(
    second_hard_alias: str,
) -> None:
    spec = _spec()
    spec["context_classes"][0]["aliases"] = ["Gamma"]
    spec["context_classes"][1]["aliases"] = ["Alpha Beta", second_hard_alias]
    spec["limits"]["context_line_span"] = 2
    lines = [
        _line(0, "Alpha", 40, 40, 220, 62),
        _line(1, "Beta", 40, 66, 220, 88),
        _line(2, "Gamma", 40, 92, 240, 114),
        _line(3, "Theo loại nguyên liệu", 40, 170, 650, 198),
        _line(4, "Nguyên vật liệu", 70, 240, 500, 268),
        _line(5, "100", 730, 240, 820, 268),
        _line(6, "Thành phẩm", 70, 290, 500, 318),
        _line(7, "200", 730, 290, 820, 318),
    ]

    result = build_accounting_semantic_region_graph_v1([_page(1, lines)], spec)

    assert result["regions"] == []
    assert len(result["near_regions"]) == 1
    closest = result["near_regions"][0]["owner_context"]["closest_context_event"]
    assert closest["context_id"] == "WORK_IN_PROGRESS_VETO"
    assert closest["surface"] == "Beta Gamma"
    assert result["metrics"]["context_event_count"] == 2


def test_all_enumerated_context_intervals_fence_suppressed_owner_tail() -> None:
    spec = _spec()
    spec["context_classes"][0]["aliases"] = ["Alpha Beta", "Beta Gamma"]
    spec["branch_aliases"] = ["Gammb"]
    spec["limits"]["context_line_span"] = 2
    lines = [
        _line(0, "Alpha", 40, 40, 220, 62),
        _line(1, "Beta", 40, 66, 220, 88),
        _line(2, "Gamma", 40, 92, 240, 114),
        _line(3, "Nguyên vật liệu", 70, 170, 500, 198),
        _line(4, "100", 730, 170, 820, 198),
        _line(5, "Thành phẩm", 70, 220, 500, 248),
        _line(6, "200", 730, 220, 820, 248),
    ]

    result = build_accounting_semantic_region_graph_v1([_page(1, lines)], spec)

    assert result["regions"] == []
    assert result["near_regions"] == []
    assert result["metrics"]["branch_enumerated_candidate_count"] == 0
    assert result["metrics"]["context_event_enumerated_count"] == 2
    assert result["metrics"]["context_event_overlap_suppressed_count"] == 1


def test_redundant_hard_containment_superset_does_not_swallow_later_owner() -> None:
    spec = _spec()
    spec["context_classes"][1]["allow_token_subsequence_fence"] = True
    spec["limits"]["context_line_span"] = 2
    lines = [
        _line(0, "Chi phí sản xuất kinh doanh dở dang", 40, 40, 650, 62),
        _line(1, "Hàng tồn kho", 40, 66, 350, 88),
        _line(2, "Theo loại nguyên liệu", 40, 150, 650, 178),
        _line(3, "Nguyên vật liệu", 70, 220, 500, 248),
        _line(4, "100", 730, 220, 820, 248),
        _line(5, "Thành phẩm", 70, 270, 500, 298),
        _line(6, "200", 730, 270, 820, 298),
    ]

    result = build_accounting_semantic_region_graph_v1([_page(1, lines)], spec)

    assert len(result["regions"]) == 1
    owner = result["regions"][0]["owner_context"]
    assert owner["context_id"] == "INVENTORY_OWNER"
    assert owner["surface"] == "Hàng tồn kho"
    assert len(owner["event_evidence"]) == 1
    assert result["metrics"]["context_event_count"] == 2


@pytest.mark.parametrize(
    (
        "owner_alias",
        "hard_alias",
        "surface",
        "containment",
        "expected_context_id",
        "expected_tier",
    ),
    [
        (
            "Nội dung khác",
            "Khác",
            "Nội dung khác",
            True,
            "WORK_IN_PROGRESS_VETO",
            "EXACT_ACCENTED_ALIAS",
        ),
        (
            "Hàng tồn kho",
            "Hang ton kho",
            "Hàng tồn kho",
            False,
            "WORK_IN_PROGRESS_VETO",
            "EXACT_ACCENTLESS_ALIAS",
        ),
        (
            "Hàng tồn kho",
            "Hàng tồn khx",
            "Hàng tồn kho",
            False,
            "WORK_IN_PROGRESS_VETO",
            "ONE_BASE_CHARACTER_EDIT_AFTER_ALL_EXACT_MISSES",
        ),
    ],
)
def test_same_surface_hard_context_precedes_exact_owner(
    owner_alias: str,
    hard_alias: str,
    surface: str,
    containment: bool,
    expected_context_id: str,
    expected_tier: str,
) -> None:
    spec = _spec()
    spec["context_classes"][0]["aliases"] = [owner_alias]
    spec["context_classes"][1]["aliases"] = [hard_alias]
    spec["context_classes"][1]["allow_token_subsequence_fence"] = containment

    result = build_accounting_semantic_region_graph_v1(
        [_page(1, _table_lines(owner=surface))], spec
    )

    assert result["regions"] == []
    closest = result["near_regions"][0]["owner_context"]["closest_context_event"]
    assert closest["context_id"] == expected_context_id
    assert closest["disposition"] == "HARD_VETO"
    assert closest["match_tier"] == expected_tier


def test_same_surface_reset_component_precedes_longer_exact_owner() -> None:
    spec = _spec()
    spec["context_classes"][0]["aliases"] = ["Tài sản cố định hữu hình"]
    spec["structural_reset_component_aliases"] = ["Tài sản cố định"]

    result = build_accounting_semantic_region_graph_v1(
        [_page(1, _table_lines(owner="Tài sản cố định hữu hình"))], spec
    )

    assert result["regions"] == []
    closest = result["near_regions"][0]["owner_context"]["closest_context_event"]
    assert closest["context_id"] == "STRUCTURAL_RESET"
    assert closest["disposition"] == "HARD_VETO"


@pytest.mark.parametrize("separation", ["NUMERIC_INTERVENING_LINE", "DISTANT_GEOMETRY"])
def test_context_event_plan_does_not_join_across_numeric_or_distant_lines(
    separation: str,
) -> None:
    spec = _spec()
    spec["limits"]["context_line_span"] = 3
    if separation == "NUMERIC_INTERVENING_LINE":
        middle = [
            _line(2, "999", 730, 116, 820, 138),
            _line(3, "cố định", 40, 142, 350, 164),
        ]
        branch_index = 4
        branch_y = 210
    else:
        middle = [_line(2, "cố định", 40, 180, 350, 202)]
        branch_index = 3
        branch_y = 240
    lines = [
        _line(0, "Hàng tồn kho", 40, 40, 350, 70),
        _line(1, "Tài sản", 40, 90, 600, 112),
        *middle,
        _line(branch_index, "Theo loại nguyên liệu", 40, branch_y, 650, branch_y + 28),
        _line(branch_index + 1, "Nguyên vật liệu", 70, branch_y + 70, 500, branch_y + 98),
        _line(branch_index + 2, "100", 730, branch_y + 70, 820, branch_y + 98),
        _line(branch_index + 3, "Thành phẩm", 70, branch_y + 120, 500, branch_y + 148),
        _line(branch_index + 4, "200", 730, branch_y + 120, 820, branch_y + 148),
    ]

    result = build_accounting_semantic_region_graph_v1([_page(1, lines)], spec)

    assert len(result["regions"]) == 1
    assert result["regions"][0]["owner_context"]["context_id"] == "INVENTORY_OWNER"
    assert result["metrics"]["context_event_wrapped_count"] == 0


def test_wrapped_reset_event_from_shared_plan_closes_the_bounded_body() -> None:
    spec = _spec()
    spec["limits"]["context_line_span"] = 2
    lines = [
        _line(0, "Hàng tồn kho", 40, 40, 350, 70),
        _line(1, "Theo loại nguyên liệu", 40, 110, 650, 138),
        _line(2, "Nguyên vật liệu", 70, 200, 500, 228),
        _line(3, "100", 730, 200, 820, 228),
        _line(4, "Tài sản", 40, 270, 500, 292),
        _line(5, "cố định", 40, 296, 350, 318),
        _line(6, "Thành phẩm", 70, 370, 500, 398),
        _line(7, "900", 730, 370, 820, 398),
    ]

    result = build_accounting_semantic_region_graph_v1([_page(1, lines)], spec)

    assert len(result["regions"]) == 1
    assert [row["semantic_id"] for row in result["regions"][0]["row_proposals"]] == ["RAW_MATERIAL"]
    assert result["metrics"]["context_event_wrapped_count"] == 1


def test_zero_line_intervening_page_is_retained_and_does_not_create_reset() -> None:
    pages = [
        _page(10, [_line(0, "Hàng tồn kho", 40, 40, 350, 70)]),
        _page(11, []),
        _page(12, _table_lines()[1:]),
    ]

    result = build_accounting_semantic_region_graph_v1(pages, _spec())

    assert result["regions"][0]["owner_context"]["mode"] == ("CARRIED_FROM_PREVIOUS_PAGE_2")
    assert result["metrics"]["explicit_zero_line_page_count"] == 1
    assert result["safety"]["empty_page_creates_structural_reset"] is False


def test_truly_omitted_intervening_page_fails_owner_carry() -> None:
    pages = [
        _page(10, [_line(0, "Hàng tồn kho", 40, 40, 350, 70)]),
        _page(12, _table_lines()[1:]),
    ]

    result = build_accounting_semantic_region_graph_v1(pages, _spec())

    assert result["regions"] == []
    assert result["near_regions"][0]["reason"] == ("OWNER_CARRY_HAS_UNOBSERVED_INTERVENING_PAGE")


def test_owner_outside_declared_page_budget_fails_closed() -> None:
    pages = [
        _page(9, [_line(0, "Hàng tồn kho", 40, 40, 350, 70)]),
        _page(10, []),
        _page(11, []),
        _page(12, _table_lines()[1:]),
    ]

    result = build_accounting_semantic_region_graph_v1(pages, _spec())

    assert result["regions"] == []
    assert result["near_regions"][0]["reason"] == (
        "EXPLICIT_OWNER_NOT_FOUND_INSIDE_CONTEXT_PAGE_BUDGET"
    )


def test_provider_line_and_page_reordering_is_invariant() -> None:
    pages = [
        _page(10, [_line(0, "Hàng tồn kho", 40, 40, 350, 70)]),
        _page(
            11,
            _table_lines(branch="Chi tiết theo loại nguyên liệu như sau")[1:],
        ),
    ]
    expected = build_accounting_semantic_region_graph_v1(pages, _component_spec())
    reordered = copy.deepcopy(list(reversed(pages)))
    for page in reordered:
        page["lines"].reverse()

    assert build_accounting_semantic_region_graph_v1(reordered, _component_spec()) == expected


def test_complete_first_row_is_not_joined_to_next_label() -> None:
    result = build_accounting_semantic_region_graph_v1(
        [_page(1, _table_lines(rows=["Nguyên vật liệu", "Thành phẩm"]))], _spec()
    )

    assert [row["semantic_id"] for row in _rows(result)] == [
        "RAW_MATERIAL",
        "FINISHED_GOODS",
    ]


def test_scoped_table_failure_cannot_promote_semantic_region(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _reject(*_args: object, **_kwargs: object) -> dict:
        raise AccountingScopedTableGraphV1Error("synthetic scoped failure")

    monkeypatch.setattr(
        semantic_region_module,
        "build_accounting_scoped_table_graph_v1",
        _reject,
    )
    result = build_accounting_semantic_region_graph_v1([_page(1, _table_lines())], _spec())

    region = result["regions"][0]
    assert region["shared_scoped_table_v1"]["status"] == ("SHARED_SCOPED_TABLE_FAIL_CLOSED")
    assert region["shared_scoped_table_v1"]["enforcement"] == (
        ScopedTableEnforcementV1.REQUIRED_PROMOTION_GATE.value
    )
    assert region["shared_scoped_table_v1"]["reason"] == (
        "SCOPED_TABLE_V1_REJECTED_DYNAMIC_EXACT_SPEC"
    )
    assert region["shared_scoped_table_v1"]["result"] is None
    assert region["promotion_eligible"] is False
    assert region["status"] == "SEMANTIC_REGION_PROPOSAL_FAIL_CLOSED"
    assert result["metrics"]["scoped_table_required_failure_region_count"] == 1
    assert result["safety"]["scoped_table_required_failure_can_promote_region"] is False


def test_advisory_scoped_failure_is_retained_without_clearing_other_promotion_gates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _reject(*_args: object, **_kwargs: object) -> dict:
        raise AccountingScopedTableGraphV1Error("synthetic advisory failure")

    monkeypatch.setattr(
        semantic_region_module,
        "build_accounting_scoped_table_graph_v1",
        _reject,
    )
    spec = _spec()
    spec["scoped_table"]["enforcement"] = ScopedTableEnforcementV1.ADVISORY_CHALLENGER.value
    result = build_accounting_semantic_region_graph_v1([_page(1, _table_lines())], spec)

    region = result["regions"][0]
    assert region["promotion_eligible"] is True
    assert region["status"] == "SEMANTIC_REGION_PROPOSAL_REQUIRES_FAMILY_POLICY_REPLAY"
    assert region["shared_scoped_table_v1"] == {
        "enforcement": "ADVISORY_CHALLENGER",
        "reason": "SCOPED_TABLE_V1_REJECTED_DYNAMIC_EXACT_SPEC",
        "result": None,
        "status": "SHARED_SCOPED_TABLE_FAIL_CLOSED",
    }
    assert result["metrics"]["scoped_table_advisory_failure_region_count"] == 1
    assert (
        result["safety"]["scoped_table_advisory_failure_can_coexist_with_otherwise_eligible_region"]
        is True
    )
    assert result["safety"]["scoped_table_advisory_failure_is_promotion_authority"] is False
    assert result["safety"]["scoped_table_advisory_failure_bypasses_other_required_gates"] is False


def test_advisory_mode_never_bypasses_the_body_limit_gate() -> None:
    spec = _spec()
    spec["limits"]["maximum_body_lines_per_page"] = 2
    spec["scoped_table"]["enforcement"] = ScopedTableEnforcementV1.ADVISORY_CHALLENGER.value

    result = build_accounting_semantic_region_graph_v1([_page(1, _table_lines())], spec)

    region = result["regions"][0]
    assert region["body_limit_reached"] is True
    assert region["promotion_eligible"] is False
    assert region["status"] == "SEMANTIC_REGION_PROPOSAL_FAIL_CLOSED"


@pytest.mark.parametrize("enforcement", ["OPTIONAL", 1, None])
def test_scoped_enforcement_contract_rejects_unknown_or_untyped_values(
    enforcement: object,
) -> None:
    spec = _spec()
    spec["scoped_table"]["enforcement"] = enforcement

    with pytest.raises(AccountingSemanticRegionGraphV1Error, match="enforcement drifted"):
        build_accounting_semantic_region_graph_v1([_page(1, _table_lines())], spec)


def test_exact_replay_and_tamper_rejection() -> None:
    pages = [_page(1, _table_lines())]
    spec = _spec()
    result = build_accounting_semantic_region_graph_v1(pages, spec)

    assert validate_accounting_semantic_region_graph_replay_v1(result, pages, spec) == result
    tampered = copy.deepcopy(result)
    tampered["metrics"]["region_count"] = 0
    with pytest.raises(AccountingSemanticRegionGraphV1Error, match="content identity drifted"):
        validate_accounting_semantic_region_graph_replay_v1(tampered, pages, spec)


def test_zero_branch_hit_is_only_bounded_absence() -> None:
    result = build_accounting_semantic_region_graph_v1(
        [_page(1, [_line(0, "Hàng tồn kho", 40, 40, 350, 70)])], _spec()
    )

    assert result["regions"] == []
    assert result["bounded_absences"][0]["status"] == ("BOUNDED_ABSENCE_NO_GLOBAL_CORPUS_CLAIM")


def test_spec_contract_rejects_unknown_family_routing_field() -> None:
    spec = _spec()
    spec["bank_routes"] = {"SYNTHETIC_BANK": 1}

    with pytest.raises(AccountingSemanticRegionGraphV1Error, match="spec fields drifted"):
        build_accounting_semantic_region_graph_v1([_page(1, _table_lines())], spec)
