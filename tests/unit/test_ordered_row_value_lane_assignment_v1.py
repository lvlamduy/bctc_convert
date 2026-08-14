from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts/experiments/ordered_row_value_lane_assignment_v1.py"
)
_SPEC = importlib.util.spec_from_file_location("ordered_row_value_lane_assignment_v1", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
assignment_v1 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = assignment_v1
_SPEC.loader.exec_module(assignment_v1)

OrderedRowValueLaneAssignmentV1Error = assignment_v1.OrderedRowValueLaneAssignmentV1Error
build_ordered_row_value_lane_assignment_v1 = (
    assignment_v1.build_ordered_row_value_lane_assignment_v1
)
validate_ordered_row_value_lane_assignment_replay_v1 = (
    assignment_v1.validate_ordered_row_value_lane_assignment_replay_v1
)


def _row(role: str, line: int, y0: int, y1: int) -> dict[str, object]:
    return {"bbox": [300, y0, 480, y1], "role": role, "source_line_index": line}


def _cell(line: int, x0: int, x1: int, y0: int, y1: int) -> dict[str, object]:
    return {"bbox": [x0, y0, x1, y1], "source_line_index": line}


LANES = ([1117, 1816, 1261, 1847], [1374, 1815, 1519, 1846])


def _mbb_inputs():
    rows = [
        _row("SHORT_TERM", 91, 1936, 1971),
        _row("MEDIUM_TERM", 94, 1970, 2004),
        _row("LONG_TERM", 97, 2006, 2038),
    ]
    cells = [
        _cell(92, 1100, 1260, 1933, 1965),
        _cell(93, 1358, 1516, 1932, 1964),
        _cell(95, 1103, 1259, 1968, 1996),
        _cell(96, 1360, 1515, 1967, 1995),
        _cell(98, 1101, 1260, 2000, 2028),
        _cell(99, 1358, 1517, 1998, 2029),
        # The following subtotal is deliberately outside the last-row vertical gate.
        _cell(100, 1077, 1260, 2050, 2083),
        _cell(101, 1337, 1516, 2052, 2080),
    ]
    return rows, cells, LANES


def test_mbb_adjacent_bbox_overlap_resolves_by_source_row_order():
    rows, cells, lanes = _mbb_inputs()
    result = build_ordered_row_value_lane_assignment_v1(rows, cells, lanes)

    assert result["status"] == "RESOLVED_ORDERED_ROW_VALUE_LANES"
    assert [row["value_source_line_indices"] for row in result["rows"]] == [
        [92, 93],
        [95, 96],
        [98, 99],
    ]
    assert result["metrics"] == {
        "assigned_value_count": 6,
        "companion_numeric_count": 0,
        "lane_count": 2,
        "resolved_row_count": 3,
        "row_count": 3,
        "unresolved_row_count": 0,
    }
    assert (
        validate_ordered_row_value_lane_assignment_replay_v1(result, rows, cells, lanes) == result
    )


def test_parallel_percentage_lanes_fail_closed_instead_of_being_dropped():
    rows = [
        _row("SHORT_TERM", 31, 913, 948),
        _row("MEDIUM_TERM", 36, 950, 984),
        _row("LONG_TERM", 41, 985, 1020),
    ]
    cells = [
        _cell(32, 890, 1029, 913, 941),
        _cell(33, 1075, 1146, 911, 944),
        _cell(34, 1189, 1330, 912, 940),
        _cell(35, 1374, 1444, 910, 943),
        _cell(37, 902, 1031, 949, 977),
        _cell(38, 1075, 1146, 946, 979),
        _cell(39, 1200, 1330, 948, 976),
        _cell(40, 1375, 1444, 945, 978),
        _cell(42, 890, 1031, 982, 1010),
        _cell(43, 1076, 1145, 981, 1011),
        _cell(44, 1189, 1330, 981, 1009),
        _cell(45, 1375, 1445, 978, 1011),
    ]
    lanes = ([934, 834, 1067, 865], [1240, 833, 1372, 864])
    result = build_ordered_row_value_lane_assignment_v1(rows, cells, lanes)

    assert result["status"] == "UNRESOLVED_ORDERED_ROW_VALUE_LANES"
    assert result["metrics"]["companion_numeric_count"] == 6
    assert all(
        row["unresolved_reasons"] == ["UNTYPED_NUMERIC_COMPANION_LANES"]
        and row["value_source_line_indices"] == []
        for row in result["rows"]
    )


def test_missing_lane_cell_remains_unresolved():
    rows, cells, lanes = _mbb_inputs()
    cells.pop(1)
    result = build_ordered_row_value_lane_assignment_v1(rows, cells, lanes)
    assert result["status"] == "UNRESOLVED_ORDERED_ROW_VALUE_LANES"
    assert "MISSING_VALUE_FOR_LANE_1" in result["rows"][0]["unresolved_reasons"]


def test_duplicate_lane_cells_remain_unresolved():
    rows = [_row("SHORT_TERM", 10, 100, 130)]
    cells = [
        _cell(11, 100, 150, 100, 130),
        _cell(12, 300, 350, 100, 130),
        _cell(13, 305, 355, 101, 131),
    ]
    lanes = ([100, 50, 150, 80], [300, 50, 350, 80])
    result = build_ordered_row_value_lane_assignment_v1(rows, cells, lanes)
    assert result["status"] == "UNRESOLVED_ORDERED_ROW_VALUE_LANES"
    assert "DUPLICATE_VALUES_FOR_LANE_1" in result["rows"][0]["unresolved_reasons"]


def test_adjacent_row_numeric_cells_cannot_compete_despite_bbox_overlap():
    rows, cells, lanes = _mbb_inputs()
    # Medium values overlap the short label by one to three pixels, but their
    # source lines occur after the next ordered label and cannot enter row one.
    result = build_ordered_row_value_lane_assignment_v1(rows, cells, lanes)
    assert result["rows"][0]["value_source_line_indices"] == [92, 93]


def test_replay_rejects_coordinated_result_rehash_after_input_drift():
    rows, cells, lanes = _mbb_inputs()
    result = build_ordered_row_value_lane_assignment_v1(rows, cells, lanes)
    forged = copy.deepcopy(result)
    forged["rows"][0]["value_source_line_indices"] = [95, 96]
    material = copy.deepcopy(forged)
    del material["assignment_id"]
    forged["assignment_id"] = "orvla1:assignment:" + canonical_json_sha256_v1(material)

    with pytest.raises(OrderedRowValueLaneAssignmentV1Error):
        validate_ordered_row_value_lane_assignment_replay_v1(forged, rows, cells, lanes)


def test_result_shape_rejects_bool_integer_safety_smuggling():
    rows, cells, lanes = _mbb_inputs()
    result = build_ordered_row_value_lane_assignment_v1(rows, cells, lanes)
    forged = copy.deepcopy(result)
    forged["safety"]["semantic_text_used"] = 0
    material = copy.deepcopy(forged)
    del material["assignment_id"]
    forged["assignment_id"] = "orvla1:assignment:" + canonical_json_sha256_v1(material)

    with pytest.raises(OrderedRowValueLaneAssignmentV1Error):
        validate_ordered_row_value_lane_assignment_replay_v1(forged, rows, cells, lanes)


@pytest.mark.parametrize(
    "bad_rows",
    [
        [{"bbox": [0, 0, 1, 1], "role": "SHORT_TERM", "source_line_index": False}],
        [{"bbox": [0, 0, 1, 1], "role": "bank_MBB", "source_line_index": 1}],
        [
            {"bbox": [0, 10, 1, 11], "role": "FIRST", "source_line_index": 2},
            {"bbox": [0, 0, 1, 1], "role": "SECOND", "source_line_index": 3},
        ],
    ],
)
def test_input_contract_rejects_type_routing_and_row_order_smuggling(bad_rows):
    with pytest.raises(OrderedRowValueLaneAssignmentV1Error):
        build_ordered_row_value_lane_assignment_v1(
            bad_rows,
            [_cell(4, 10, 20, 10, 20), _cell(5, 30, 40, 10, 20)],
            ([10, 0, 20, 5], [30, 0, 40, 5]),
        )
