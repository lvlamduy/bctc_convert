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


def _nested_spec() -> dict[str, object]:
    return {
        "children": [
            {
                "matchers": [{"aliases": ["Theo loại hình doanh nghiệp"], "within_role": None}],
                "presence": "OPTIONAL",
                "role": "ENTERPRISE_TYPE_BRANCH",
                "role_kind": "STRUCTURAL_GROUP",
            },
            {
                "matchers": [
                    {
                        "aliases": ["Doanh nghiệp nhà nước"],
                        "within_role": "ENTERPRISE_TYPE_BRANCH",
                    }
                ],
                "presence": "OPTIONAL",
                "role": "STATE_ENTERPRISE",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "matchers": [
                    {
                        "aliases": ["Công ty TNHH"],
                        "within_role": "ENTERPRISE_TYPE_BRANCH",
                    }
                ],
                "presence": "OPTIONAL",
                "role": "LIMITED_COMPANY",
                "role_kind": "ADDITIVE_CHILD",
            },
        ],
        "family_id": "GENERIC_NESTED_ENTERPRISE_TYPE",
        "format_version": "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V3",
        "hard_negative_aliases": ["Tiền gửi của khách hàng"],
        "limits": {
            "max_cluster_span_lines": 40,
            "max_continuation_pages": 0,
            "max_label_line_span": 2,
        },
        "parent": {
            "aliases": ["Cho vay khách hàng"],
            "resolution_mode": "EXPLICIT_ONLY",
            "role": "CUSTOMER_LOANS_NOTE",
        },
        "presence_evidence_mode": "WITHIN_EXPLICIT_PARENT_CLUSTER",
        "required_role_combinations": [
            ["ENTERPRISE_TYPE_BRANCH", "STATE_ENTERPRISE", "LIMITED_COMPANY"]
        ],
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


def _complete_header_before_parent_pages() -> list[dict[str, object]]:
    pages = _pages()
    lines = pages[0]["lines"]
    reordered = [*lines[1:8], lines[0], *lines[8:]]
    bands = {
        0: (10, 30),
        1: (38, 58),
        2: (38, 58),
        3: (66, 86),
        4: (66, 86),
        5: (66, 86),
        6: (66, 86),
        7: (100, 122),
    }
    for ordinal, line in enumerate(reordered):
        line["line_ordinal"] = ordinal
        if ordinal in bands:
            top, bottom = bands[ordinal]
            line["bbox"][1] = top
            line["bbox"][3] = bottom
    pages[0]["lines"] = reordered
    return pages


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


def _nested_owner_pages() -> list[dict[str, object]]:
    lines = [
        ("Cho vay khách hàng", "", [20, 20, 430, 42]),
        ("Lãi suất cho vay", "", [20, 50, 430, 72]),
        ("30/06/2025", "", [480, 78, 680, 100]),
        ("31/12/2023", "", [720, 78, 920, 100]),
        ("Lãi suất bình quân", "", [20, 108, 430, 130]),
        ("Theo loại hình doanh nghiệp", "", [20, 150, 430, 172]),
        ("Đơn vị: Triệu đồng", "", [480, 178, 920, 198]),
        ("31/12/2025", "", [480, 204, 680, 226]),
        ("31/12/2024", "", [720, 204, 920, 226]),
        ("Giá trị", "", [480, 232, 560, 254]),
        ("%", "", [600, 232, 680, 254]),
        ("Giá trị", "", [720, 232, 800, 254]),
        ("%", "", [840, 232, 920, 254]),
        ("Doanh nghiệp nhà nước", "", [40, 280, 360, 302]),
        ("100", "100", [480, 280, 560, 302]),
        ("60", "60", [600, 280, 680, 302]),
        ("90", "90", [720, 280, 800, 302]),
        ("55", "55", [840, 280, 920, 302]),
        ("Công ty TNHH", "", [40, 325, 360, 347]),
        ("200", "200", [480, 325, 560, 347]),
        ("40", "40", [600, 325, 680, 347]),
        ("180", "180", [720, 325, 800, 347]),
        ("45", "45", [840, 325, 920, 347]),
    ]
    repeated_document_context = [
        ("31/12/2025", "", [480, 20, 680, 42]),
        ("31/12/2024", "", [720, 20, 920, 42]),
        ("Phân tích theo ngành nghề", "", [20, 70, 430, 92]),
    ]
    return [
        {
            "lines": [
                _line(ordinal, text, numeric, bbox, page=1)
                for ordinal, (text, numeric, bbox) in enumerate(lines)
            ],
            "page_sequence": 1,
            "page_width": 1000,
        },
        {
            "lines": [
                _line(ordinal, text, numeric, bbox, page=2)
                for ordinal, (text, numeric, bbox) in enumerate(repeated_document_context)
            ],
            "page_sequence": 2,
            "page_width": 1000,
        },
    ]


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


def _nested_axis(pages: list[dict[str, object]]) -> dict[str, object]:
    return row_axis_v1.build_accounting_family_row_axis_v1(pages, _nested_spec())


def _nested_build(pages: list[dict[str, object]]) -> dict[str, object]:
    return build_accounting_family_column_context_multilevel_v2(
        _nested_axis(pages),
        pages,
        _nested_spec(),
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


def test_complete_multilevel_header_immediately_before_explicit_parent_resolves() -> None:
    result = _build(_complete_header_before_parent_pages())

    assert result["format_version"] == v2.FORMAT_VERSION
    assert result["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
    assert [item["resolved_period"] for item in result["period_axis"]] == [
        "31/12/2025",
        "31/12/2025",
        "31/12/2024",
        "31/12/2024",
    ]
    assert [item["unit_kind"] for item in result["unit_axis"]] == _KINDS


def test_explicit_money_leaves_do_not_leak_document_unit_locations() -> None:
    pages = _complete_header_before_parent_pages()
    pages[0]["lines"].pop(0)
    for ordinal, line in enumerate(pages[0]["lines"]):
        line["line_ordinal"] = ordinal
    for ordinal in (2, 4):
        pages[0]["lines"][ordinal]["vietocr_text"] = "Triệu đồng"
        pages[0]["lines"][ordinal]["numeric_recognition"]["raw_prediction"] = "Triệu đồng"

    result = _build(pages)

    assert result["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
    money = [record for record in result["unit_axis"] if record["unit_kind"] == "MONEY"]
    assert len(money) == 2
    assert {
        location["page_sequence"] for record in money for location in record["evidence_locations"]
    } == {1}
    assert all(
        record["projection_status"].startswith("LOCAL_EXPLICIT_MULTILEVEL_MONEY_LEAF_UNIT")
        for record in money
    )


def test_complete_explicit_money_leaves_override_ambiguous_document_unit_context() -> None:
    pages = _complete_header_before_parent_pages()
    pages[0]["lines"].pop(0)
    for ordinal, line in enumerate(pages[0]["lines"]):
        line["line_ordinal"] = ordinal
    for ordinal in (2, 4):
        pages[0]["lines"][ordinal]["vietocr_text"] = "Triệu đồng"
        pages[0]["lines"][ordinal]["numeric_recognition"]["raw_prediction"] = "Triệu đồng"
    conflicting_unit = _line(99, "Đơn vị: nghìn VND", "", [480, 900, 920, 922], page=1)
    conflicting_unit["line_ordinal"] = len(pages[0]["lines"])
    pages[0]["lines"].append(conflicting_unit)

    result = _build(pages)

    assert result["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
    assert (
        result["document_unit_context"]["resolution"]
        == "UNRESOLVED_CONFLICTING_EXPLICIT_DOCUMENT_UNITS"
    )
    money = [record for record in result["unit_axis"] if record["unit_kind"] == "MONEY"]
    assert [(record["currency"], record["magnitude_power10"]) for record in money] == [
        ("VND", 6),
        ("VND", 6),
    ]
    assert all(
        record["evidence_locations"]
        == [
            {
                "page_sequence": 1,
                "source_line_index": record["column_ordinal"] + 2,
            }
        ]
        for record in money
    )


def test_partial_explicit_money_leaf_axis_cannot_override_ambiguous_document_unit() -> None:
    pages = _complete_header_before_parent_pages()
    pages[0]["lines"].pop(0)
    for ordinal, line in enumerate(pages[0]["lines"]):
        line["line_ordinal"] = ordinal
    pages[0]["lines"][2]["vietocr_text"] = "Triệu đồng"
    pages[0]["lines"][2]["numeric_recognition"]["raw_prediction"] = "Triệu đồng"
    conflicting_unit = _line(99, "Đơn vị: nghìn VND", "", [480, 900, 920, 922], page=1)
    conflicting_unit["line_ordinal"] = len(pages[0]["lines"])
    pages[0]["lines"].append(conflicting_unit)

    result = _build(pages)

    assert result["status"] == "UNRESOLVED_PERIOD_UNIT_COLUMN_CONTEXT"
    assert (
        result["document_unit_context"]["resolution"]
        == "UNRESOLVED_CONFLICTING_EXPLICIT_DOCUMENT_UNITS"
    )
    assert result["period_axis"] == []
    assert result["unit_axis"] == []


def test_explicit_money_leaves_cannot_override_conflicting_local_unit() -> None:
    pages = _complete_header_before_parent_pages()
    pages[0]["lines"][0]["vietocr_text"] = "Đơn vị tính: nghìn VND"
    pages[0]["lines"][0]["numeric_recognition"]["raw_prediction"] = "Đơn vị tính: nghìn VND"
    for ordinal in (3, 5):
        pages[0]["lines"][ordinal]["vietocr_text"] = "Triệu đồng"
        pages[0]["lines"][ordinal]["numeric_recognition"]["raw_prediction"] = "Triệu đồng"

    result = _build(pages)

    assert result["status"] == "UNRESOLVED_PERIOD_UNIT_COLUMN_CONTEXT"
    assert result["period_axis"] == []
    assert result["unit_axis"] == []


def test_prior_table_header_cannot_cross_the_active_parent_fence() -> None:
    pages = _pages(prior_header=True)
    result = _build(pages)

    assert result["format_version"] == v2.column_v1.FORMAT_VERSION
    assert result["status"] == "UNRESOLVED_PERIOD_UNIT_COLUMN_CONTEXT"
    assert result["period_axis"] == []
    parent_end = _axis(pages)["topology_region"]["parent_match"]["end_document_line_ordinal"]
    assert parent_end == 3


def test_contextual_structural_owner_fences_out_preceding_sibling_table_header() -> None:
    pages = _nested_owner_pages()
    axis = _nested_axis(pages)
    parsed = row_axis_v1._pages(pages)
    centers = v2.column_v1._lane_centers(axis)

    assert centers is not None
    fenced = v2._fenced_header_lines(axis, parsed, _nested_spec(), centers)
    assert fenced is not None
    assert [line["source_line_index"] for line in fenced[0]] == list(range(6, 13))
    result = _nested_build(pages)
    assert result["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
    assert [item["resolved_period"] for item in result["period_axis"]] == [
        "31/12/2025",
        "31/12/2025",
        "31/12/2024",
        "31/12/2024",
    ]


@pytest.mark.parametrize("mutation", ["duplicate", "wrong_page", "nonexact", "owner_mismatch"])
def test_contextual_structural_header_owner_must_replay_uniquely_and_exactly(
    mutation: str,
) -> None:
    pages = _nested_owner_pages()
    axis = _nested_axis(pages)
    owner = next(
        match
        for match in axis["topology_region"]["child_matches"]
        if match["role"] == "ENTERPRISE_TYPE_BRANCH"
    )
    first_body = next(row for row in axis["rows"] if row["values"])["label_match"]
    if mutation == "duplicate":
        axis["topology_region"]["child_matches"].append(copy.deepcopy(owner))
    elif mutation == "wrong_page":
        owner["page_sequence"] = 2
    elif mutation == "nonexact":
        owner["match_kind"] = "ONE_EDIT_ALIAS_REQUIRES_COMPLETE_TOPOLOGY"
    else:
        owner["occurrence_id"] = "aforav2:occurrence:" + "1" * 64
        first_body["scope_owner_occurrence_id"] = "aforav2:occurrence:" + "2" * 64
    parsed = row_axis_v1._pages(pages)
    centers = v2.column_v1._lane_centers(axis)

    assert centers is not None
    assert v2._fenced_header_lines(axis, parsed, _nested_spec(), centers) is None


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


def test_v2_authenticated_row_axis_handoff_replays_exact_context() -> None:
    pages = _complete_header_before_parent_pages()
    axis = _axis(pages)
    result = _build(pages)

    assert (
        v2._validate_accounting_family_column_context_multilevel_from_authenticated_row_axis_v2(
            result,
            axis,
            pages,
            _spec(),
            period_semantics="BALANCE_COMPARATIVE",
            expected_lane_unit_kinds=_KINDS,
        )
        == result
    )

    forged = copy.deepcopy(result)
    forged["unit_axis"][0]["currency"] = "USD"
    material = copy.deepcopy(forged)
    material.pop("column_context_id")
    forged["column_context_id"] = "afccmlv2:context:" + canonical_json_sha256_v1(material)
    with pytest.raises(AccountingFamilyColumnContextMultilevelV2Error, match="replay exactly"):
        v2._validate_accounting_family_column_context_multilevel_from_authenticated_row_axis_v2(
            forged,
            axis,
            pages,
            _spec(),
            period_semantics="BALANCE_COMPARATIVE",
            expected_lane_unit_kinds=_KINDS,
        )
