from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from bctc_ai.evaluation import accounting_family_column_context_multilevel_v2 as v2
from bctc_ai.evaluation import accounting_family_row_axis_v1 as row_axis_v1
from bctc_ai.evaluation.accounting_family_column_context_multilevel_v2 import (
    AccountingFamilyColumnContextMultilevelV2Error,
    build_accounting_family_column_context_multilevel_v2,
    validate_accounting_family_column_context_multilevel_replay_v2,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_KINDS = ["MONEY", "PERCENT", "MONEY", "PERCENT"]
_ROOT = Path(__file__).resolve().parents[2]


def _spec() -> dict[str, object]:
    return {
        "children": [
            {
                "aliases": ["Doanh nghiệp nhà nước"],
                "presence": "REQUIRED",
                "role": "STATE_ENTERPRISE",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "aliases": ["Công ty TNHH"],
                "presence": "REQUIRED",
                "role": "LIMITED_COMPANY",
                "role_kind": "ADDITIVE_CHILD",
            },
        ],
        "family_id": "GENERIC_ENTERPRISE_TYPE",
        "format_version": "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V1",
        "hard_negative_aliases": ["Tiền gửi của khách hàng"],
        "limits": {
            "max_cluster_span_lines": 40,
            "max_continuation_pages": 1,
            "max_label_line_span": 2,
        },
        "parent": {
            "aliases": ["Theo loại hình doanh nghiệp"],
            "resolution_mode": "EXPLICIT_ONLY",
            "role": "ENTERPRISE_TYPE",
        },
        "structural_reset_aliases": ["Phân tích theo ngành nghề"],
    }


def _line(
    ordinal: int,
    text: str,
    numeric: str,
    bbox: list[int],
    *,
    page: int,
) -> dict[str, object]:
    sample = page * 100 + ordinal + 1
    return {
        "bbox": bbox,
        "crop_ref": {
            "path": f"opaque/multilevel-v2-{sample:04d}.png",
            "sha256": f"{sample:064x}",
            "size_bytes": sample + 100,
        },
        "line_ordinal": ordinal,
        "numeric_recognition": {"raw_prediction": numeric, "reader_score": 0.95},
        "sample_id": f"multilevel-v2-sample-{sample:06d}",
        "vietocr_text": text,
    }


def _pages(*, prior_header: bool = False) -> list[dict[str, object]]:
    active = [
        ("Theo loại hình doanh nghiệp", "", [20, 20, 430, 42]),
        ("Đơn vị: Triệu đồng", "", [480, 48, 920, 66]),
        ("31/12/2025", "", [480, 70, 680, 92]),
        ("31/12/2024", "", [720, 70, 920, 92]),
        ("Giá trị", "", [480, 98, 560, 120]),
        ("%", "", [600, 98, 680, 120]),
        ("Giá trị", "", [720, 98, 800, 120]),
        ("%", "", [840, 98, 920, 120]),
        ("Doanh nghiệp nhà nước", "", [40, 145, 360, 167]),
        ("100", "100", [480, 145, 560, 167]),
        ("60", "60", [600, 145, 680, 167]),
        ("90", "90", [720, 145, 800, 167]),
        ("55", "55", [840, 145, 920, 167]),
        ("Công ty TNHH", "", [40, 190, 360, 212]),
        ("200", "200", [480, 190, 560, 212]),
        ("40", "40", [600, 190, 680, 212]),
        ("180", "180", [720, 190, 800, 212]),
        ("45", "45", [840, 190, 920, 212]),
    ]
    if prior_header:
        active = [
            ("Đơn vị: Triệu đồng", "", [480, 5, 920, 23]),
            ("31/12/2025", "", [480, 27, 680, 47]),
            ("31/12/2024", "", [720, 27, 920, 47]),
            ("Theo loại hình doanh nghiệp", "", [20, 70, 430, 92]),
            ("Giá trị", "", [480, 100, 560, 122]),
            ("%", "", [600, 100, 680, 122]),
            ("Giá trị", "", [720, 100, 800, 122]),
            ("%", "", [840, 100, 920, 122]),
            *[
                (text, numeric, [bbox[0], bbox[1] + 5, bbox[2], bbox[3] + 5])
                for text, numeric, bbox in active[8:]
            ],
        ]
    second = [
        ("31/12/2025", "", [480, 20, 680, 42]),
        ("31/12/2024", "", [720, 20, 920, 42]),
        ("Đơn vị: Triệu đồng", "", [480, 48, 920, 70]),
        ("Phân tích theo ngành nghề", "", [20, 100, 430, 122]),
    ]
    return [
        {
            "lines": [
                _line(ordinal, text, numeric, bbox, page=1)
                for ordinal, (text, numeric, bbox) in enumerate(active)
            ],
            "page_sequence": 1,
            "page_width": 1000,
        },
        {
            "lines": [
                _line(ordinal, text, numeric, bbox, page=2)
                for ordinal, (text, numeric, bbox) in enumerate(second)
            ],
            "page_sequence": 2,
            "page_width": 1000,
        },
    ]


def _conflicting_continuation_pages() -> list[dict[str, object]]:
    pages = _pages()
    pages[0]["lines"] = pages[0]["lines"][:13]
    continuation = [
        ("31/12/2025", "", [480, 20, 680, 42]),
        ("31/12/2023", "", [720, 20, 920, 42]),
        ("Đơn vị: Triệu đồng", "", [480, 48, 920, 70]),
        ("Giá trị", "", [480, 76, 560, 98]),
        ("%", "", [600, 76, 680, 98]),
        ("Giá trị", "", [720, 76, 800, 98]),
        ("%", "", [840, 76, 920, 98]),
        ("Công ty TNHH", "", [40, 120, 360, 142]),
        ("200", "200", [480, 120, 560, 142]),
        ("40", "40", [600, 120, 680, 142]),
        ("180", "180", [720, 120, 800, 142]),
        ("45", "45", [840, 120, 920, 142]),
    ]
    reset = [("Phân tích theo ngành nghề", "", [20, 30, 430, 52])]
    pages[1] = {
        "lines": [
            _line(ordinal, text, numeric, bbox, page=2)
            for ordinal, (text, numeric, bbox) in enumerate(continuation)
        ],
        "page_sequence": 2,
        "page_width": 1000,
    }
    pages.append(
        {
            "lines": [
                _line(ordinal, text, numeric, bbox, page=3)
                for ordinal, (text, numeric, bbox) in enumerate(reset)
            ],
            "page_sequence": 3,
            "page_width": 1000,
        }
    )
    return pages


def _prior_unit_pages() -> list[dict[str, object]]:
    first = [
        ("Triệu đồng", "", [480, 5, 560, 23]),
        ("%", "", [600, 5, 680, 23]),
        ("Triệu đồng", "", [720, 5, 800, 23]),
        ("%", "", [840, 5, 920, 23]),
        ("Theo loại hình doanh nghiệp", "", [20, 38, 430, 60]),
        ("31/12/2025", "", [480, 70, 680, 92]),
        ("31/12/2024", "", [720, 70, 920, 92]),
        ("Giá trị", "", [480, 98, 560, 120]),
        ("Tỷ lệ", "", [600, 98, 680, 120]),
        ("Giá trị", "", [720, 98, 800, 120]),
        ("Tỷ lệ", "", [840, 98, 920, 120]),
        ("Doanh nghiệp nhà nước", "", [40, 145, 360, 167]),
        ("100", "100", [480, 145, 560, 167]),
        ("60", "60", [600, 145, 680, 167]),
        ("90", "90", [720, 145, 800, 167]),
        ("55", "55", [840, 145, 920, 167]),
        ("Công ty TNHH", "", [40, 190, 360, 212]),
        ("200", "200", [480, 190, 560, 212]),
        ("40", "40", [600, 190, 680, 212]),
        ("180", "180", [720, 190, 800, 212]),
        ("45", "45", [840, 190, 920, 212]),
    ]
    pages = _pages()
    pages[0]["lines"] = [
        _line(ordinal, text, numeric, bbox, page=1)
        for ordinal, (text, numeric, bbox) in enumerate(first)
    ]
    return pages


def _axis(pages: list[dict[str, object]]) -> dict[str, object]:
    return row_axis_v1.build_accounting_family_row_axis_v1(pages, _spec())


def _build(pages: list[dict[str, object]]) -> dict[str, object]:
    return build_accounting_family_column_context_multilevel_v2(
        _axis(pages),
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=_KINDS,
    )


def test_authenticated_row_axis_handoff_uses_same_multilevel_projection_without_public_replay(
    monkeypatch,
) -> None:
    pages = _pages()
    axis = _axis(pages)
    expected = _build(pages)
    monkeypatch.setattr(
        v2.column_v1,
        "build_accounting_family_column_context_v1",
        lambda *_args, **_kwargs: pytest.fail("trusted handoff replayed the public row axis"),
    )

    observed = v2._build_accounting_family_column_context_multilevel_from_authenticated_row_axis_v2(
        axis,
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=_KINDS,
    )

    assert observed == expected


def test_pinned_v1_and_leaf_implementation_refs_match_disk() -> None:
    for reference in v2.PINNED_IMPLEMENTATION_REFS.values():
        payload = (_ROOT / reference["path"]).read_bytes()
        assert len(payload) == reference["size_bytes"]
        assert hashlib.sha256(payload).hexdigest() == reference["sha256"]


def test_mixed_balance_fallback_returns_v1_compatible_closed_v2_context() -> None:
    result = _build(_pages())

    assert result["format_version"] == v2.FORMAT_VERSION
    assert result["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
    assert [item["resolved_period"] for item in result["period_axis"]] == [
        "31/12/2025",
        "31/12/2025",
        "31/12/2024",
        "31/12/2024",
    ]
    assert [item["unit_kind"] for item in result["unit_axis"]] == _KINDS
    assert [item["magnitude_power10"] for item in result["unit_axis"]] == [6, None, 6, None]
    assert result["column_context_id"].startswith("afccmlv2:context:")


def test_prior_table_header_cannot_cross_the_active_parent_fence() -> None:
    pages = _pages(prior_header=True)
    result = _build(pages)

    assert result["format_version"] == v2.column_v1.FORMAT_VERSION
    assert result["status"] == "UNRESOLVED_PERIOD_UNIT_COLUMN_CONTEXT"
    assert result["period_axis"] == []
    parent_end = _axis(pages)["topology_region"]["parent_match"]["end_document_line_ordinal"]
    assert parent_end == 3


def test_prior_table_unit_axis_cannot_cross_the_active_parent_fence() -> None:
    pages = _prior_unit_pages()
    axis = _axis(pages)
    baseline = v2.column_v1.build_accounting_family_column_context_v1(
        axis,
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=_KINDS,
    )

    result = build_accounting_family_column_context_multilevel_v2(
        axis,
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=_KINDS,
    )

    assert axis["topology_region"]["parent_match"]["end_document_line_ordinal"] == 4
    assert baseline["status"] == "UNRESOLVED_PERIOD_UNIT_COLUMN_CONTEXT"
    assert len(baseline["unit_axis"]) == 4
    assert {
        location["source_line_index"]
        for record in baseline["unit_axis"]
        for location in record["evidence_locations"]
    } == {0, 1, 2, 3}
    assert result == baseline


def test_reset_surface_inside_candidate_header_is_a_hard_fence() -> None:
    pages = _pages()
    axis = _axis(pages)
    parsed = row_axis_v1._pages(pages)
    parsed[0]["lines"][1]["vietocr_text"] = "Phân tích theo ngành nghề"
    centers = v2.column_v1._lane_centers(axis)

    assert centers is not None
    assert v2._fenced_header_lines(axis, parsed, _spec(), centers) is None


def test_current_rollforward_returns_v1_without_invoking_leaf_projector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pages = _pages()
    axis = _axis(pages)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("CURRENT_ROLLFORWARD must never invoke the multilevel projector")

    monkeypatch.setattr(
        v2.leaf_axis_v1, "build_accounting_multilevel_header_leaf_axis_v1", forbidden
    )
    result = build_accounting_family_column_context_multilevel_v2(
        axis,
        pages,
        _spec(),
        period_semantics="CURRENT_ROLLFORWARD",
        expected_lane_unit_kinds=_KINDS,
    )

    assert result["format_version"] == v2.column_v1.FORMAT_VERSION
    assert result["status"] == "UNRESOLVED_PERIOD_UNIT_COLUMN_CONTEXT"


def test_conflicting_cross_page_continuation_stays_exact_v1_unresolved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pages = _conflicting_continuation_pages()
    axis = _axis(pages)
    baseline = v2.column_v1.build_accounting_family_column_context_v1(
        axis,
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=_KINDS,
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("cross-page continuation must never invoke the V2 projector")

    monkeypatch.setattr(
        v2.leaf_axis_v1, "build_accounting_multilevel_header_leaf_axis_v1", forbidden
    )
    result = build_accounting_family_column_context_multilevel_v2(
        axis,
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=_KINDS,
    )

    assert axis["topology_region"]["continuation_page_count"] == 1
    assert baseline["status"] == "UNRESOLVED_PERIOD_UNIT_COLUMN_CONTEXT"
    assert "CROSS_PAGE_PERIOD_UNIT_INHERITANCE_NOT_PROVEN" in baseline["unresolved_reasons"]
    assert result == baseline


def test_v2_exact_replay_rejects_self_rehashed_period_mutation() -> None:
    pages = _pages()
    axis = _axis(pages)
    result = build_accounting_family_column_context_multilevel_v2(
        axis,
        pages,
        _spec(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=_KINDS,
    )
    forged = copy.deepcopy(result)
    forged["period_axis"][0]["resolved_period"] = "31/12/2099"
    material = copy.deepcopy(forged)
    material.pop("column_context_id")
    forged["column_context_id"] = "afccmlv2:context:" + canonical_json_sha256_v1(material)

    with pytest.raises(AccountingFamilyColumnContextMultilevelV2Error, match="replay exactly"):
        validate_accounting_family_column_context_multilevel_replay_v2(
            forged,
            axis,
            pages,
            _spec(),
            period_semantics="BALANCE_COMPARATIVE",
            expected_lane_unit_kinds=_KINDS,
        )
