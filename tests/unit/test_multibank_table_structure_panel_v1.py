from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from bctc_ai.core.hashing import sha256_file


def _module():
    path = (
        Path(__file__).resolve().parents[2]
        / "scripts/experiments/build_multibank_table_structure_panel_v1.py"
    )
    specification = importlib.util.spec_from_file_location(
        "build_multibank_table_structure_panel_v1", path
    )
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _ref(root: Path, path: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _source_inputs(root: Path, module) -> tuple[Path, Path]:
    render = root / "source/render.png"
    render.parent.mkdir(parents=True)
    image = Image.new("RGB", (100, 80), "white")
    boxes = [
        [10, 5, 90, 12],
        [10, 20, 35, 28],
        [50, 20, 65, 28],
        [75, 20, 90, 28],
        [10, 50, 35, 58],
        [50, 50, 65, 58],
        [75, 50, 90, 70],
    ]
    for ordinal, (x0, y0, x1, y1) in enumerate(boxes):
        for x in range(x0, x1):
            for y in range(y0, y1):
                image.putpixel((x, y), (20 + ordinal, 40 + ordinal, 60 + ordinal))
    image.save(render, format="PNG", optimize=False, compress_level=6)
    render_ref = _ref(root, render)

    result = root / "source/result.json"
    _write_json(
        result,
        {
            "format_version": module.RESULT_FORMAT,
            "input_render_ref": render_ref,
            "lines": [
                {
                    "raw_pixel_bbox": box,
                    "raw_text": f"FORBIDDEN-TRANSCRIPT-{ordinal}",
                }
                for ordinal, box in enumerate(boxes)
            ],
        },
    )
    result_ref = _ref(root, result)
    checkpoint = "1" * 40
    source = root / "config/source.json"
    _write_json(
        source,
        {
            "dataset_role": "CALIBRATION",
            "design_checkpoint_git_commit": checkpoint,
            "format_version": module.SOURCE_FORMAT,
            "padding_pixels": 4,
            "samples": [
                {
                    "expected_source_line_count": 7,
                    "line_index_range_inclusive": [0, 6],
                    "render_ref": render_ref,
                    "result_ref": result_ref,
                    "sample_id": "table-0001",
                }
            ],
            "state": "FROZEN_SOURCE_SELECTION_BEFORE_STRUCTURE_MODEL_ACCESS",
        },
    )
    gold = root / "config/gold.json"
    _write_json(
        gold,
        {
            "design_checkpoint_git_commit": checkpoint,
            "format_version": module.GOLD_INPUT_FORMAT,
            "samples": [
                {
                    "bank": "FIXTURE_BANK",
                    "column_anchor_line_groups": [[1, 4], [2, 5], [3, 6]],
                    "column_excluded_line_indices": [0],
                    "control_kind": "POSITIVE",
                    "expected_control_disposition": "ACCEPT",
                    "expected_structural_family_merge": True,
                    "family": "FIXTURE_FAMILY",
                    "header_line_groups": [[0], [1, 2, 3]],
                    "ignored_noncontent_line_indices": [],
                    "ignored_noncontent_reason": "NONE",
                    "logical_rows": [
                        {
                            "line_indices": [4, 5, 6],
                            "value_line_indices_by_numeric_lane": [[5], [6]],
                        },
                    ],
                    "nested_row_required": False,
                    "numeric_lane_count": 2,
                    "optional_row_behavior": "FIXTURE_TOTAL_REQUIRED",
                    "physical_page": 1,
                    "projected_row_header_line_groups": [],
                    "sample_id": "table-0001",
                    "spanning_cells": [],
                    "visible_unscored_dash_cells": [],
                }
            ],
            "state": "FROZEN_HUMAN_SOURCE_GOLD_BEFORE_STRUCTURE_MODEL_ACCESS",
        },
    )
    return source, gold


def _clean_git(*args: str) -> str:
    if args == ("status", "--porcelain", "--untracked-files=normal"):
        return ""
    if args == ("rev-parse", "HEAD"):
        return "2" * 40
    raise AssertionError(args)


def _current_blob(root: Path):
    def read(_commit: str, relative_path: str) -> bytes:
        return (root / relative_path).read_bytes()

    return read


def test_builds_deterministic_source_bound_crop_blind_request_and_separate_gold(
    tmp_path, monkeypatch
):
    module = _module()
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(module, "_git", _clean_git)
    monkeypatch.setattr(module, "_git_blob", _current_blob(tmp_path))
    source, gold = _source_inputs(tmp_path, module)

    summary = module.build_panel(
        source_spec_path=source.relative_to(tmp_path),
        gold_input_path=gold.relative_to(tmp_path),
        output_root=Path("generated/panel"),
        gold_output_path=Path("generated/source-gold.json"),
    )

    assert summary == {
        "crop_manifest": "generated/panel/frozen/crop_manifest.json",
        "model_request": "generated/panel/frozen/model_request.json",
        "sample_count": 1,
        "selected_source_line_count": 7,
        "source_gold": "generated/source-gold.json",
    }
    manifest = json.loads((tmp_path / summary["crop_manifest"]).read_bytes())
    request = json.loads((tmp_path / summary["model_request"]).read_bytes())
    truth = json.loads((tmp_path / summary["source_gold"]).read_bytes())
    sample = manifest["samples"][0]
    assert manifest["format_version"] == module.MANIFEST_FORMAT
    assert manifest["state"] == "FROZEN_BEFORE_ANY_STRUCTURE_MODEL_INFERENCE"
    assert manifest["selected_source_line_count"] == 7
    assert manifest["source_spec_ref"] == _ref(tmp_path, source)
    assert not Path(manifest["source_spec_ref"]["path"]).is_absolute()
    assert sample["source_line_indices"] == list(range(7))
    assert sample["table_source_bbox_raw_pixels"] == [10, 5, 90, 70]
    assert sample["crop_source_bbox_raw_pixels"] == [6, 1, 94, 74]
    assert sample["padding_pixels"] == 4
    assert (tmp_path / sample["crop_path"]).read_bytes()

    assert request["format_version"] == module.REQUEST_FORMAT
    assert request["reference_text_available_to_reader"] is False
    assert request["expected_structure_available_to_reader"] is False
    assert set(request["samples"][0]) == {
        "category",
        "crop_path",
        "crop_sha256",
        "sample_id",
    }
    serialized_request = json.dumps(request, ensure_ascii=False)
    for forbidden in (
        "FIXTURE_BANK",
        "FIXTURE_FAMILY",
        "physical_page",
        "logical_row_count",
        "FORBIDDEN-TRANSCRIPT",
    ):
        assert forbidden not in serialized_request

    assert truth["crop_manifest"] == request["crop_manifest"]
    assert set(truth) == {
        "crop_manifest",
        "design_checkpoint_git_commit",
        "format_version",
        "gold_input_ref",
        "sample_count",
        "samples",
        "state",
    }
    assert truth["gold_input_ref"] == _ref(tmp_path, gold)
    assert not Path(truth["gold_input_ref"]["path"]).is_absolute()
    assert truth["samples"][0]["crop_ref"]["sha256"] == sample["crop_sha256"]
    assert truth["samples"][0]["logical_row_count"] == 1
    assert truth["samples"][0]["numeric_lane_count"] == 2
    assert truth["samples"][0]["header_row_count"] == 2
    assert truth["samples"][0]["ignored_noncontent_line_count"] == 0
    assert truth["samples"][0]["ignored_noncontent_line_indices"] == []
    assert truth["samples"][0]["ignored_noncontent_reason"] == "NONE"
    assert truth["samples"][0]["spanning_cell_required"] is False
    assert truth["samples"][0]["visible_unscored_dash_cells"] == []
    assert truth["samples"][0]["value_cell_coverage_summary"] == {
        "cell_slot_count": 2,
        "other_unanchored_cell_count": 0,
        "source_anchored_value_cell_count": 2,
        "visible_unscored_dash_cell_count": 0,
    }
    assert len(truth["samples"][0]["value_anchors"]) == 2
    assert [
        (anchor["logical_row_ordinal"], anchor["numeric_lane_ordinal"])
        for anchor in truth["samples"][0]["value_anchors"]
    ] == [(1, 1), (1, 2)]
    assert set(truth["samples"][0]["class_coverage"]) == set(module.TATR_LABELS)

    objects = truth["samples"][0]["gold_objects"]
    by_id = {item["object_id"]: item for item in objects}
    assert by_id["table-001"]["bbox_crop_pixels_xyxy"] == [4, 4, 84, 69]
    assert by_id["header-row-001"]["bbox_crop_pixels_xyxy"] == [4, 4, 84, 15.0]
    assert by_id["header-row-002"]["bbox_crop_pixels_xyxy"] == [4, 15.0, 84, 38.0]
    assert by_id["row-001"]["bbox_crop_pixels_xyxy"] == [4, 38.0, 84, 69]
    assert by_id["column-001"]["bbox_crop_pixels_xyxy"] == [4, 4, 36.5, 69]
    assert by_id["column-002"]["bbox_crop_pixels_xyxy"] == [36.5, 4, 64.0, 69]
    assert by_id["column-003"]["bbox_crop_pixels_xyxy"] == [64.0, 4, 84, 69]
    header_objects = [item for item in objects if item["label"] == "table column header"]
    assert header_objects == [
        {
            "bbox_crop_pixels_xyxy": [4, 4, 84, 38.0],
            "label": "table column header",
            "object_id": "column-header-001",
        }
    ]


def test_line_geometry_projection_cannot_consult_ocr_transcript():
    module = _module()

    class GeometryOnlyLine(dict):
        def get(self, key, default=None):
            if key != "raw_pixel_bbox":
                raise AssertionError(f"forbidden transcript access: {key}")
            return super().get(key, default)

    lines = [
        GeometryOnlyLine(raw_pixel_bbox=[1, 2, 3, 4], raw_text="không được đọc"),
        GeometryOnlyLine(raw_pixel_bbox=[5, 6, 8, 9], raw_text="cũng không được đọc"),
    ]
    assert module._line_boxes(lines, width=10, height=10) == [
        (1, 2, 3, 4),
        (5, 6, 8, 9),
    ]


def test_formal_freeze_rejects_dirty_tree_before_reading_inputs(tmp_path, monkeypatch):
    module = _module()
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(module, "_git", lambda *_args: "?? untracked")

    with pytest.raises(module.TableStructurePanelError, match="clean Git worktree"):
        module.build_panel(
            source_spec_path=Path("missing-source.json"),
            gold_input_path=Path("missing-gold.json"),
            output_root=Path("generated/panel"),
            gold_output_path=Path("generated/gold.json"),
        )


def test_rejects_padding_above_tatr_tight_crop_bound(tmp_path, monkeypatch):
    module = _module()
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    source, _gold = _source_inputs(tmp_path, module)
    value = json.loads(source.read_bytes())
    value["padding_pixels"] = 6
    _write_json(source, value)

    with pytest.raises(module.TableStructurePanelError, match="freeze policy"):
        module._validate_sources(json.loads(source.read_bytes()))


def test_rejects_semantic_sample_id_that_would_leak_into_model_request(tmp_path, monkeypatch):
    module = _module()
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    source, _gold = _source_inputs(tmp_path, module)
    value = json.loads(source.read_bytes())
    value["samples"][0]["sample_id"] = "table-BAB-loan-quality"
    _write_json(source, value)

    with pytest.raises(module.TableStructurePanelError, match="selection is invalid"):
        module._validate_sources(json.loads(source.read_bytes()))


def test_rejects_incomplete_full_content_column_assignment(tmp_path, monkeypatch):
    module = _module()
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(module, "_git", _clean_git)
    monkeypatch.setattr(module, "_git_blob", _current_blob(tmp_path))
    source, gold = _source_inputs(tmp_path, module)
    value = json.loads(gold.read_bytes())
    value["samples"][0]["column_anchor_line_groups"][0].remove(4)
    _write_json(gold, value)

    with pytest.raises(module.TableStructurePanelError, match="do not cover selected"):
        module.build_panel(
            source_spec_path=source.relative_to(tmp_path),
            gold_input_path=gold.relative_to(tmp_path),
            output_root=Path("generated/panel"),
            gold_output_path=Path("generated/source-gold.json"),
        )


def test_column_axis_exclusions_are_limited_to_header_or_span_content(tmp_path, monkeypatch):
    module = _module()
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(module, "_git", _clean_git)
    monkeypatch.setattr(module, "_git_blob", _current_blob(tmp_path))
    source, gold = _source_inputs(tmp_path, module)
    value = json.loads(gold.read_bytes())
    value["samples"][0]["column_anchor_line_groups"][0].remove(4)
    value["samples"][0]["column_excluded_line_indices"].append(4)
    _write_json(gold, value)

    with pytest.raises(module.TableStructurePanelError, match="limited to fused headers"):
        module.build_panel(
            source_spec_path=source.relative_to(tmp_path),
            gold_input_path=gold.relative_to(tmp_path),
            output_root=Path("generated/panel"),
            gold_output_path=Path("generated/source-gold.json"),
        )


def test_formal_freeze_requires_exact_tracked_source_and_gold_blobs(tmp_path, monkeypatch):
    module = _module()
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(module, "_git", _clean_git)
    monkeypatch.setattr(module, "_git_blob", lambda _commit, _relative: b"older bytes\n")
    source, gold = _source_inputs(tmp_path, module)

    with pytest.raises(module.TableStructurePanelError, match="exact tracked Git blob"):
        module.build_panel(
            source_spec_path=source.relative_to(tmp_path),
            gold_input_path=gold.relative_to(tmp_path),
            output_root=Path("generated/panel"),
            gold_output_path=Path("generated/source-gold.json"),
        )


def test_ignored_noncontent_is_evidence_only_and_cannot_enter_gold_geometry(tmp_path, monkeypatch):
    module = _module()
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(module, "_git", _clean_git)
    monkeypatch.setattr(module, "_git_blob", _current_blob(tmp_path))
    source, gold = _source_inputs(tmp_path, module)
    value = json.loads(gold.read_bytes())
    sample = value["samples"][0]
    sample["ignored_noncontent_line_indices"] = [6]
    sample["ignored_noncontent_reason"] = "PIXEL_AUDITED_HORIZONTAL_RULE_FALSE_DETECTION"
    sample["logical_rows"][0]["line_indices"].remove(6)
    sample["logical_rows"][0]["value_line_indices_by_numeric_lane"][1].remove(6)
    sample["column_anchor_line_groups"][2].remove(6)
    _write_json(gold, value)

    summary = module.build_panel(
        source_spec_path=source.relative_to(tmp_path),
        gold_input_path=gold.relative_to(tmp_path),
        output_root=Path("generated/panel"),
        gold_output_path=Path("generated/source-gold.json"),
    )
    manifest = json.loads((tmp_path / summary["crop_manifest"]).read_bytes())
    truth = json.loads((tmp_path / summary["source_gold"]).read_bytes())["samples"][0]

    assert manifest["samples"][0]["source_line_indices"] == list(range(7))
    assert manifest["samples"][0]["selected_line_count"] == 7
    assert truth["ignored_noncontent_line_indices"] == [6]
    assert truth["ignored_noncontent_line_count"] == 1
    assert truth["ignored_noncontent_reason"] == ("PIXEL_AUDITED_HORIZONTAL_RULE_FALSE_DETECTION")
    assert truth["gold_content_table_source_bbox_raw_pixels"] == [10, 5, 90, 58]
    assert all(anchor["source_line_index"] != 6 for anchor in truth["value_anchors"])


def test_rejects_ignored_noncontent_reason_without_ignored_lines(tmp_path, monkeypatch):
    module = _module()
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    source, gold = _source_inputs(tmp_path, module)
    value = json.loads(gold.read_bytes())
    value["samples"][0]["ignored_noncontent_reason"] = (
        "PIXEL_AUDITED_HORIZONTAL_RULE_FALSE_DETECTION"
    )
    _write_json(gold, value)

    with pytest.raises(module.TableStructurePanelError, match="policy is invalid"):
        module._validate_gold_input(json.loads(gold.read_bytes()), ["table-0001"])


def test_visible_dash_without_source_line_has_explicit_unscorable_cell_denominator(
    tmp_path, monkeypatch
):
    module = _module()
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(module, "_git", _clean_git)
    monkeypatch.setattr(module, "_git_blob", _current_blob(tmp_path))
    source, gold = _source_inputs(tmp_path, module)
    value = json.loads(gold.read_bytes())
    sample = value["samples"][0]
    sample["logical_rows"][0]["value_line_indices_by_numeric_lane"][0] = []
    sample["visible_unscored_dash_cells"] = [
        {
            "logical_row_ordinal": 1,
            "numeric_lane_ordinal": 1,
            "reason": "VISIBLE_DASH_NO_AUTHENTICATED_SOURCE_LINE",
        }
    ]
    _write_json(gold, value)

    summary = module.build_panel(
        source_spec_path=source.relative_to(tmp_path),
        gold_input_path=gold.relative_to(tmp_path),
        output_root=Path("generated/panel"),
        gold_output_path=Path("generated/source-gold.json"),
    )
    truth = json.loads((tmp_path / summary["source_gold"]).read_bytes())["samples"][0]

    assert len(truth["value_anchors"]) == 1
    assert truth["visible_unscored_dash_cells"] == sample["visible_unscored_dash_cells"]
    assert truth["value_cell_coverage_summary"] == {
        "cell_slot_count": 2,
        "other_unanchored_cell_count": 0,
        "source_anchored_value_cell_count": 1,
        "visible_unscored_dash_cell_count": 1,
    }


def test_rejects_visible_dash_that_also_has_source_anchor(tmp_path, monkeypatch):
    module = _module()
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(module, "_git", _clean_git)
    monkeypatch.setattr(module, "_git_blob", _current_blob(tmp_path))
    source, gold = _source_inputs(tmp_path, module)
    value = json.loads(gold.read_bytes())
    value["samples"][0]["visible_unscored_dash_cells"] = [
        {
            "logical_row_ordinal": 1,
            "numeric_lane_ordinal": 1,
            "reason": "VISIBLE_DASH_NO_AUTHENTICATED_SOURCE_LINE",
        }
    ]
    _write_json(gold, value)

    with pytest.raises(module.TableStructurePanelError, match="dash cell is invalid"):
        module.build_panel(
            source_spec_path=source.relative_to(tmp_path),
            gold_input_path=gold.relative_to(tmp_path),
            output_root=Path("generated/panel"),
            gold_output_path=Path("generated/source-gold.json"),
        )
