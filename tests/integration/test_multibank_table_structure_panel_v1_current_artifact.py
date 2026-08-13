from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_SPEC = Path("config/experiments/multibank-table-structure-source-panel-v1.json")
GOLD_INPUT = Path("config/experiments/multibank-table-structure-source-gold-input-v1.json")
DESIGN_CHECKPOINT = "5fd750ff986e38d81dabec21615751f845a0d832"
EXPECTED_GEOMETRY = {
    "table-0001": {
        "column_x": [4, 443.0, 963.5, 1190],
        "crop_size": [1194, 300],
        "header": [4, 4, 1190, 109.0],
        "projected": [],
        "row_y": [4, 52.0, 109.0, 156.5, 203.0, 253.5, 296],
        "spanning": [],
        "table": [4, 4, 1190, 296],
    },
    "table-0002": {
        "column_x": [4, 494.0, 905.5, 1095],
        "crop_size": [1099, 328],
        "header": [4, 4, 1095, 73.0],
        "projected": [],
        "row_y": [4, 32.5, 73.0, 120.5, 160.5, 199.5, 238.5, 286.0, 324],
        "spanning": [],
        "table": [4, 4, 1095, 324],
    },
    "table-0003": {
        "column_x": [4, 430.0, 906.5, 1097],
        "crop_size": [1101, 250],
        "header": [4, 4, 1097, 75.5],
        "projected": [],
        "row_y": [4, 33.0, 75.5, 121.0, 159.5, 207.0, 246],
        "spanning": [],
        "table": [4, 4, 1097, 246],
    },
    "table-0004": {
        "column_x": [4, 575.0, 1048.5, 1251],
        "crop_size": [1255, 217],
        "header": [4, 4, 1251, 71.5],
        "projected": [],
        "row_y": [4, 39.0, 71.5, 108.5, 141.5, 180.5, 213],
        "spanning": [],
        "table": [4, 4, 1251, 213],
    },
    "table-0005": {
        "column_x": [4, 767.5, 1045.0, 1324.5, 1609.5, 1891.0, 2175.0, 2472.0, 2751.5, 3011],
        "crop_size": [3015, 1309],
        "header": [4, 4, 3011, 124.5],
        "projected": [[4, 124.5, 3011, 173.0], [4, 740.0, 3011, 793.5]],
        "row_y": [
            4,
            57.5,
            124.5,
            173.0,
            223.5,
            266.5,
            311.0,
            352.5,
            433.0,
            482.5,
            525.5,
            567.5,
            613.5,
            669.0,
            740.0,
            793.5,
            842.0,
            885.5,
            967.5,
            1054.5,
            1103.0,
            1163.5,
            1236.5,
            1305,
        ],
        "spanning": [[767.5, 4, 1324.5, 57.5], [1324.5, 4, 2751.5, 57.5]],
        "table": [4, 4, 3011, 1305],
    },
    "table-0006": {
        "column_x": [4, 756.5, 999.5, 1186],
        "crop_size": [1190, 453],
        "header": [4, 4, 1186, 77.0],
        "projected": [],
        "row_y": [4, 37.5, 77.0, 124.5, 179.0, 231.0, 287.0, 335.5, 411.5, 449],
        "spanning": [],
        "table": [4, 4, 1186, 449],
    },
    "table-0007": {
        "column_x": [4, 842.0, 1511.5, 1844],
        "crop_size": [1848, 478],
        "header": [4, 4, 1844, 125.0],
        "projected": [],
        "row_y": [4, 62.0, 125.0, 185.5, 245.5, 305.0, 363.0, 427.5, 474],
        "spanning": [],
        "table": [4, 4, 1844, 474],
    },
}


def _module():
    path = PROJECT_ROOT / "scripts/experiments/build_multibank_table_structure_panel_v1.py"
    specification = importlib.util.spec_from_file_location(
        "build_multibank_table_structure_panel_v1_current", path
    )
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _intersection_fraction(inner, outer):
    x0 = max(inner[0], outer[0])
    y0 = max(inner[1], outer[1])
    x1 = min(inner[2], outer[2])
    y1 = min(inner[3], outer[3])
    intersection = max(0, x1 - x0) * max(0, y1 - y0)
    return intersection / ((inner[2] - inner[0]) * (inner[3] - inner[1]))


def test_exact_hydrated_seven_crop_panel_replays_refs_geometry_and_gold_denominator():
    module = _module()
    source = json.loads((PROJECT_ROOT / SOURCE_SPEC).read_bytes())
    gold = json.loads((PROJECT_ROOT / GOLD_INPUT).read_bytes())
    assert source["design_checkpoint_git_commit"] == DESIGN_CHECKPOINT
    assert gold["design_checkpoint_git_commit"] == DESIGN_CHECKPOINT
    assert source["padding_pixels"] == 4

    validated = module._validate_sources(source)
    gold_by_id = module._validate_gold_input(gold, [sample["sample_id"] for sample in validated])
    assert len(validated) == 7
    assert sum(sample["line_range"][1] - sample["line_range"][0] + 1 for sample in validated) == 223
    assert len({sample["result_ref"]["sha256"] for sample in validated}) == 6
    assert {item["bank"] for item in gold_by_id.values()} == {
        "BAB",
        "BVB",
        "CTG",
        "NVB",
        "SHB",
    }
    assert sum(item["control_kind"] == "HARD_CONTROL" for item in gold_by_id.values()) == 2
    assert [item["column_excluded_line_indices"] for item in gold_by_id.values()] == [
        [],
        [],
        [],
        [],
        [9, 10, 14],
        [],
        [],
    ]
    assert [item["ignored_noncontent_line_indices"] for item in gold_by_id.values()] == [
        [],
        [],
        [],
        [],
        [105],
        [],
        [],
    ]
    assert all(
        not item["expected_structural_family_merge"]
        for item in gold_by_id.values()
        if item["control_kind"] == "HARD_CONTROL"
    )

    derived = []
    crop_sizes = {}
    for sample in validated:
        with Image.open(sample["render_path"]) as opened:
            width, height = opened.size
        boxes = module._line_boxes(sample["result"]["lines"], width=width, height=height)
        first, last = sample["line_range"]
        selected = list(range(first, last + 1))
        gold_sample = gold_by_id[sample["sample_id"]]
        column_assignments = [
            index for group in gold_sample["column_anchor_line_groups"] for index in group
        ]
        column_exclusions = gold_sample["column_excluded_line_indices"]
        ignored_noncontent = gold_sample["ignored_noncontent_line_indices"]
        assert len(column_assignments) == len(set(column_assignments))
        assert set(column_assignments).isdisjoint([*column_exclusions, *ignored_noncontent])
        assert set(column_assignments) | set(column_exclusions) == set(selected) - set(
            ignored_noncontent
        )
        table_box = module._union([boxes[index] for index in selected], label="integration")
        padding = source["padding_pixels"]
        crop_box = (
            max(0, table_box[0] - padding),
            max(0, table_box[1] - padding),
            min(width, table_box[2] + padding),
            min(height, table_box[3] + padding),
        )
        crop_sizes[sample["sample_id"]] = [crop_box[2] - crop_box[0], crop_box[3] - crop_box[1]]
        derived.append(
            module._gold_sample(
                gold_sample,
                boxes=boxes,
                selected_indices=selected,
                selected_table_box=table_box,
                crop_box=crop_box,
            )
        )

    assert [item["logical_row_count"] for item in derived] == [4, 6, 4, 4, 19, 7, 6]
    assert [item["numeric_lane_count"] for item in derived] == [2, 2, 2, 2, 8, 2, 2]
    assert [item["header_row_count"] for item in derived] == [2] * 7
    assert sum(len(item["value_anchors"]) for item in derived) == 139
    assert derived[3]["visible_unscored_dash_cells"] == [
        {
            "logical_row_ordinal": 2,
            "numeric_lane_ordinal": 1,
            "reason": "VISIBLE_DASH_NO_AUTHENTICATED_SOURCE_LINE",
        },
        {
            "logical_row_ordinal": 3,
            "numeric_lane_ordinal": 2,
            "reason": "VISIBLE_DASH_NO_AUTHENTICATED_SOURCE_LINE",
        },
    ]
    assert [item["value_cell_coverage_summary"] for item in derived] == [
        {
            "cell_slot_count": 8,
            "other_unanchored_cell_count": 0,
            "source_anchored_value_cell_count": 8,
            "visible_unscored_dash_cell_count": 0,
        },
        {
            "cell_slot_count": 12,
            "other_unanchored_cell_count": 0,
            "source_anchored_value_cell_count": 12,
            "visible_unscored_dash_cell_count": 0,
        },
        {
            "cell_slot_count": 8,
            "other_unanchored_cell_count": 0,
            "source_anchored_value_cell_count": 8,
            "visible_unscored_dash_cell_count": 0,
        },
        {
            "cell_slot_count": 8,
            "other_unanchored_cell_count": 0,
            "source_anchored_value_cell_count": 6,
            "visible_unscored_dash_cell_count": 2,
        },
        {
            "cell_slot_count": 152,
            "other_unanchored_cell_count": 73,
            "source_anchored_value_cell_count": 79,
            "visible_unscored_dash_cell_count": 0,
        },
        {
            "cell_slot_count": 14,
            "other_unanchored_cell_count": 0,
            "source_anchored_value_cell_count": 14,
            "visible_unscored_dash_cell_count": 0,
        },
        {
            "cell_slot_count": 12,
            "other_unanchored_cell_count": 0,
            "source_anchored_value_cell_count": 12,
            "visible_unscored_dash_cell_count": 0,
        },
    ]
    assert all(
        item["ignored_noncontent_line_count"] == (1 if item["sample_id"] == "table-0005" else 0)
        for item in derived
    )
    assert derived[4]["nested_row_required"] is True
    assert derived[4]["spanning_cell_required"] is True
    assert all(
        item["class_coverage"]["table"] == "SCORABLE_WITH_INSTANCES"
        and item["class_coverage"]["table row"] == "SCORABLE_WITH_INSTANCES"
        and item["class_coverage"]["table column"] == "SCORABLE_WITH_INSTANCES"
        and item["class_coverage"]["table column header"] == "SCORABLE_WITH_INSTANCES"
        for item in derived
    )
    assert derived[4]["class_coverage"]["table projected row header"] == ("SCORABLE_WITH_INSTANCES")
    assert derived[4]["class_coverage"]["table spanning cell"] == ("SCORABLE_WITH_INSTANCES")
    assert all(
        item["class_coverage"]["table projected row header"] == "SCORABLE_ZERO_INSTANCE"
        and item["class_coverage"]["table spanning cell"] == "SCORABLE_ZERO_INSTANCE"
        for item in [*derived[:4], *derived[5:]]
    )

    for item in derived:
        expected = EXPECTED_GEOMETRY[item["sample_id"]]
        objects = item["gold_objects"]
        table_objects = [obj for obj in objects if obj["label"] == "table"]
        row_objects = sorted(
            (obj for obj in objects if obj["label"] == "table row"),
            key=lambda obj: obj["bbox_crop_pixels_xyxy"][1],
        )
        column_objects = sorted(
            (obj for obj in objects if obj["label"] == "table column"),
            key=lambda obj: obj["bbox_crop_pixels_xyxy"][0],
        )
        header_objects = [obj for obj in objects if obj["label"] == "table column header"]
        projected_objects = [obj for obj in objects if obj["label"] == "table projected row header"]
        spanning_objects = [obj for obj in objects if obj["label"] == "table spanning cell"]

        assert crop_sizes[item["sample_id"]] == expected["crop_size"]
        assert [obj["bbox_crop_pixels_xyxy"] for obj in table_objects] == [expected["table"]]
        assert [row_objects[0]["bbox_crop_pixels_xyxy"][1]] + [
            obj["bbox_crop_pixels_xyxy"][3] for obj in row_objects
        ] == expected["row_y"]
        assert [column_objects[0]["bbox_crop_pixels_xyxy"][0]] + [
            obj["bbox_crop_pixels_xyxy"][2] for obj in column_objects
        ] == expected["column_x"]
        assert [obj["bbox_crop_pixels_xyxy"] for obj in header_objects] == [expected["header"]]
        assert [obj["bbox_crop_pixels_xyxy"] for obj in projected_objects] == expected["projected"]
        assert [obj["bbox_crop_pixels_xyxy"] for obj in spanning_objects] == expected["spanning"]

        table_bbox = table_objects[0]["bbox_crop_pixels_xyxy"]
        crop_width, crop_height = expected["crop_size"]
        assert table_bbox == [4, 4, crop_width - 4, crop_height - 4]
        assert all(
            row["bbox_crop_pixels_xyxy"][0] == table_bbox[0]
            and row["bbox_crop_pixels_xyxy"][2] == table_bbox[2]
            for row in row_objects
        )
        assert all(
            upper["bbox_crop_pixels_xyxy"][3] == lower["bbox_crop_pixels_xyxy"][1]
            for upper, lower in zip(row_objects, row_objects[1:], strict=False)
        )
        assert all(
            column["bbox_crop_pixels_xyxy"][1] == table_bbox[1]
            and column["bbox_crop_pixels_xyxy"][3] == table_bbox[3]
            for column in column_objects
        )
        assert all(
            left["bbox_crop_pixels_xyxy"][2] == right["bbox_crop_pixels_xyxy"][0]
            for left, right in zip(column_objects, column_objects[1:], strict=False)
        )
        assert len(header_objects) == 1
        header_rows = sorted(
            (obj for obj in row_objects if obj["object_id"].startswith("header-row-")),
            key=lambda obj: obj["bbox_crop_pixels_xyxy"][1],
        )
        assert len(header_rows) == item["header_row_count"] == 2
        assert header_objects[0]["bbox_crop_pixels_xyxy"] == [
            table_bbox[0],
            header_rows[0]["bbox_crop_pixels_xyxy"][1],
            table_bbox[2],
            header_rows[-1]["bbox_crop_pixels_xyxy"][3],
        ]
        assert all(
            0 <= bbox[0] < bbox[2] <= crop_width and 0 <= bbox[1] < bbox[3] <= crop_height
            for bbox in (obj["bbox_crop_pixels_xyxy"] for obj in objects)
        )
        object_by_id = {obj["object_id"]: obj for obj in objects}
        anchor_axes = [
            (anchor["logical_row_ordinal"], anchor["numeric_lane_ordinal"])
            for anchor in item["value_anchors"]
        ]
        dash_axes = [
            (cell["logical_row_ordinal"], cell["numeric_lane_ordinal"])
            for cell in item["visible_unscored_dash_cells"]
        ]
        assert len(anchor_axes) == len(set(anchor_axes))
        assert set(anchor_axes).isdisjoint(dash_axes)
        assert all(
            anchor["source_line_index"] not in item["ignored_noncontent_line_indices"]
            for anchor in item["value_anchors"]
        )
        assert all(
            anchor["expected_row_object_id"] == f"row-{anchor['logical_row_ordinal']:03d}"
            and anchor["expected_column_object_id"]
            == f"column-{anchor['numeric_lane_ordinal'] + 1:03d}"
            for anchor in item["value_anchors"]
        )
        assert len(row_objects) == (
            item["header_row_count"] + item["logical_row_count"] + len(projected_objects)
        )
        assert all(
            _intersection_fraction(
                anchor["bbox_crop_pixels_xyxy"],
                object_by_id[anchor[owner]]["bbox_crop_pixels_xyxy"],
            )
            >= 0.8
            for anchor in item["value_anchors"]
            for owner in ("expected_row_object_id", "expected_column_object_id")
        )
