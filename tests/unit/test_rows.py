from __future__ import annotations

from bctc_ai.core.contracts import BoundingBox
from bctc_ai.rows.assembler import RowFragment, assemble_logical_rows


def test_wrapped_long_label_is_one_logical_row():
    fragments = [
        RowFragment(
            "f1",
            1,
            "t1",
            "Tiền, vàng gửi tại các tổ chức tín dụng khác và",
            BoundingBox(10, 10, 250, 20),
        ),
        RowFragment(
            "f2",
            1,
            "t1",
            "cho vay các tổ chức tín dụng khác",
            BoundingBox(10, 22, 220, 32),
            values=("1.000", "900"),
            value_bboxes=(BoundingBox(300, 22, 350, 32), BoundingBox(400, 22, 450, 32)),
        ),
    ]
    rows = assemble_logical_rows(fragments)
    assert len(rows) == 1
    assert rows[0].label.endswith("cho vay các tổ chức tín dụng khác")
    assert rows[0].values == ["1.000", "900"]
    assert len(rows[0].label_boxes) == 2


def test_two_complete_rows_are_not_merged_by_proximity():
    fragments = [
        RowFragment("f1", 1, "t1", "A", BoundingBox(10, 10, 30, 20), values=("1",)),
        RowFragment("f2", 1, "t1", "B", BoundingBox(10, 21, 30, 31), values=("2",)),
    ]
    assert len(assemble_logical_rows(fragments)) == 2


def test_explicit_cross_page_row_continuation():
    fragments = [
        RowFragment(
            "f1",
            1,
            "t1",
            "Khoản mục rất dài",
            BoundingBox(10, 790, 200, 810),
            continuation_hint=True,
        ),
        RowFragment(
            "f2",
            2,
            "t2",
            "tiếp theo",
            BoundingBox(10, 20, 100, 30),
            values=("5",),
            continuation_hint=True,
        ),
    ]
    rows = assemble_logical_rows(fragments)
    assert len(rows) == 1
    assert rows[0].crosses_page
    assert rows[0].table_ids == ["t1", "t2"]
