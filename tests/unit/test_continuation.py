from __future__ import annotations

from bctc_ai.tables.continuation import TableFragment, build_continuation_graph


def _fragment(identifier: str, page: int, **overrides) -> TableFragment:
    values = {
        "table_id": identifier,
        "page": page,
        "header_labels": ("Khoản mục", "30/06/2026", "31/12/2025"),
        "column_centers": (0.2, 0.7, 0.9),
        "unit": "triệu đồng",
        "period_labels": ("30/06/2026", "31/12/2025"),
        "notes_section": "12",
        "parent_section": "Cho vay khách hàng",
    }
    values.update(overrides)
    return TableFragment(**values)


def test_continuation_requires_more_than_page_adjacency():
    first = _fragment("p1-t1", 1)
    unrelated = _fragment(
        "p2-t1",
        2,
        header_labels=("Nội dung khác",),
        column_centers=(0.5,),
        unit=None,
        period_labels=(),
        notes_section="99",
        parent_section="Khác",
    )
    graph = build_continuation_graph([first, unrelated])
    assert not graph.edges[0].accepted


def test_repeated_axes_unit_period_and_section_accept_continuation():
    first = _fragment("p1-t1", 1)
    second = _fragment("p2-t1", 2, starts_with_repeated_header=True)
    graph = build_continuation_graph([first, second])
    assert graph.edges[0].accepted
    assert graph.accepted_successor("p1-t1") == "p2-t1"


def test_unfinished_row_can_continue_across_page():
    first = _fragment("p1-t1", 1, previous_row_incomplete=True)
    second = _fragment("p2-t1", 2, first_row_continuation_hint=True)
    graph = build_continuation_graph([first, second])
    assert graph.edges[0].evidence.row_continuation
