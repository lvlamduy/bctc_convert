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
        _page(11, _table_lines()[1:]),
    ]
    expected = build_accounting_semantic_region_graph_v1(pages, _spec())
    reordered = copy.deepcopy(list(reversed(pages)))
    for page in reordered:
        page["lines"].reverse()

    assert build_accounting_semantic_region_graph_v1(reordered, _spec()) == expected


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
    assert region["promotion_eligible"] is False
    assert region["status"] == "SEMANTIC_REGION_PROPOSAL_FAIL_CLOSED"


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
