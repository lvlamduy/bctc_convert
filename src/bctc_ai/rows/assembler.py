from __future__ import annotations

from dataclasses import dataclass, field

from bctc_ai.core.contracts import BoundingBox
from bctc_ai.core.text import normalize_text


@dataclass(frozen=True)
class RowFragment:
    fragment_id: str
    page: int
    table_id: str
    label_text: str
    label_bbox: BoundingBox
    values: tuple[str, ...] = ()
    value_bboxes: tuple[BoundingBox, ...] = ()
    explicit_row_boundary_after: bool = False
    continuation_hint: bool = False


@dataclass
class LogicalRow:
    row_id: str
    page_start: int
    page_end: int
    table_ids: list[str]
    label: str
    label_boxes: list[BoundingBox]
    values: list[str]
    value_boxes: list[BoundingBox]
    fragment_ids: list[str] = field(default_factory=list)
    crosses_page: bool = False


def _vertical_gap(previous: RowFragment, following: RowFragment) -> float:
    if previous.page != following.page:
        return 0.0
    return following.label_bbox.y0 - previous.label_bbox.y1


def _should_join(previous: RowFragment, following: RowFragment, maximum_gap: float) -> bool:
    if previous.explicit_row_boundary_after:
        return False
    if previous.table_id != following.table_id and previous.page == following.page:
        return False
    if previous.page == following.page:
        close = _vertical_gap(previous, following) <= maximum_gap
        aligned = abs(previous.label_bbox.x0 - following.label_bbox.x0) <= 18.0
        # At least one fragment should lack numeric cells. Two complete numeric
        # rows must never be joined merely because they are close.
        incomplete = not previous.values or not following.values
        return close and aligned and incomplete
    return (
        following.page == previous.page + 1
        and previous.continuation_hint
        and following.continuation_hint
    )


def assemble_logical_rows(
    fragments: list[RowFragment], *, maximum_line_gap: float = 8.0
) -> list[LogicalRow]:
    if not fragments:
        return []
    ordered = sorted(
        fragments, key=lambda item: (item.page, item.label_bbox.y0, item.label_bbox.x0)
    )
    groups: list[list[RowFragment]] = [[ordered[0]]]
    for fragment in ordered[1:]:
        if _should_join(groups[-1][-1], fragment, maximum_line_gap):
            groups[-1].append(fragment)
        else:
            groups.append([fragment])
    rows = []
    for index, group in enumerate(groups, start=1):
        pages = [fragment.page for fragment in group]
        rows.append(
            LogicalRow(
                row_id=f"{group[0].table_id}:row-{index:04d}",
                page_start=min(pages),
                page_end=max(pages),
                table_ids=list(dict.fromkeys(fragment.table_id for fragment in group)),
                label=normalize_text(" ".join(fragment.label_text for fragment in group)),
                label_boxes=[fragment.label_bbox for fragment in group],
                values=[value for fragment in group for value in fragment.values],
                value_boxes=[box for fragment in group for box in fragment.value_bboxes],
                fragment_ids=[fragment.fragment_id for fragment in group],
                crosses_page=len(set(pages)) > 1,
            )
        )
    return rows
