from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from bctc_ai.evaluation.numeric_cell_crops import (
    NumericCellCropError,
    build_numeric_cell_crop_registry,
    load_numeric_cell_crop_policy,
)


def _write_json(path: Path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _fixture(tmp_path: Path):
    render = tmp_path / "page.png"
    image = np.full((220, 400, 3), 255, dtype=np.uint8)
    cv2.putText(image, "1.234", (210, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(image, "-", (350, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    assert cv2.imwrite(str(render), image)
    ocr = _write_json(
        tmp_path / "ocr.json",
        {
            "rec_boxes": [
                [210, 85, 260, 105],
                [350, 145, 360, 165],
            ]
        },
    )
    contract = _write_json(
        tmp_path / "contract.json",
        {
            "experiment_id": "E-0029",
            "status": "PASS_REFERENCE_BLIND_ROW_RECONSTRUCTION",
            "after": [
                {
                    "page": 3,
                    "line_height": 40,
                    "note_right_edge": 100,
                    "table_bbox": [0, 60, 380, 190],
                    "axes": [
                        {"axis_id": "value-1", "right_edge": 270},
                        {"axis_id": "value-2", "right_edge": 360},
                    ],
                    "rows": [
                        {
                            "source_row_ids": ["p3:r1"],
                            "cells": [
                                {
                                    "observation": "VALUE",
                                    "raw_text": "1.234",
                                    "normalized_text": "1234",
                                    "value": "1234",
                                    "sign_evidence": None,
                                },
                                {
                                    "observation": "BLANK",
                                    "raw_text": "",
                                    "normalized_text": "",
                                    "value": None,
                                    "sign_evidence": None,
                                },
                            ],
                            "geometry": {
                                "y_anchor": 95,
                                "value_line_indices": [[0], []],
                                "visual_cell_evidence": [None, None],
                            },
                        },
                        {
                            "source_row_ids": ["p3:r2"],
                            "cells": [
                                {
                                    "observation": "BLANK",
                                    "raw_text": "",
                                    "normalized_text": "",
                                    "value": None,
                                    "sign_evidence": None,
                                },
                                {
                                    "observation": "DASH",
                                    "raw_text": "-",
                                    "normalized_text": "-",
                                    "value": None,
                                    "sign_evidence": "dash",
                                },
                            ],
                            "geometry": {
                                "y_anchor": 155,
                                "value_line_indices": [[], [1]],
                                "visual_cell_evidence": [None, None],
                            },
                        },
                    ],
                },
                {
                    "page": 4,
                    "line_height": 40,
                    "note_right_edge": 100,
                    "table_bbox": [0, 60, 380, 190],
                    "axes": [
                        {"axis_id": "value-1", "right_edge": 270},
                        {"axis_id": "value-2", "right_edge": 360},
                    ],
                    "rows": [
                        {
                            "source_row_ids": ["p4:r1"],
                            "cells": [
                                {
                                    "observation": "BLANK",
                                    "raw_text": "",
                                    "normalized_text": "",
                                    "value": None,
                                    "sign_evidence": None,
                                },
                                {
                                    "observation": "BLANK",
                                    "raw_text": "",
                                    "normalized_text": "",
                                    "value": None,
                                    "sign_evidence": None,
                                },
                            ],
                            "geometry": {
                                "y_anchor": 120,
                                "value_line_indices": [[], []],
                                "visual_cell_evidence": [None, None],
                            },
                        }
                    ],
                },
            ],
        },
    )
    render4 = tmp_path / "page4.png"
    assert cv2.imwrite(str(render4), image)
    ocr4 = _write_json(tmp_path / "ocr4.json", {"rec_boxes": []})
    return contract, {3: ocr, 4: ocr4}, {3: render, 4: render4}


def test_fixed_grid_crops_preserve_pixels_and_expose_only_crop_path(project_root, tmp_path):
    contract, ocr, renders = _fixture(tmp_path)
    output = tmp_path / "numeric-crops"
    registry = build_numeric_cell_crop_registry(
        row_contract_path=contract,
        ocr_paths_by_page=ocr,
        render_paths_by_page=renders,
        output_directory=output,
        policy=load_numeric_cell_crop_policy(
            project_root / "config/tables/numeric-cell-crops-v1.yaml"
        ),
    )

    assert registry["metrics"] == {
        "page_count": 2,
        "row_count": 3,
        "cell_count": 6,
        "primary_observation_counts": {"BLANK": 4, "DASH": 1, "VALUE": 1},
        "crop_line_clip_count": 0,
        "visual_evidence_clip_count": 0,
    }
    assert all(cell["recognizer_payload"].keys() == {"crop_path"} for cell in registry["cells"])
    assert all((output / cell["crop_path"]).is_file() for cell in registry["cells"])
    first = registry["cells"][0]
    assert first["crop_bbox"] == [175, 60, 272, 125]
    assert first["primary_raw_text"] == "1.234"
    assert (output / "crop_registry.json").is_file()


def test_fixed_grid_crop_refuses_source_line_clipping(project_root, tmp_path):
    contract, ocr, renders = _fixture(tmp_path)
    payload = json.loads(ocr[3].read_text())
    payload["rec_boxes"][0][0] = 160
    ocr[3].write_text(json.dumps(payload))

    with pytest.raises(NumericCellCropError, match="clips source line"):
        build_numeric_cell_crop_registry(
            row_contract_path=contract,
            ocr_paths_by_page=ocr,
            render_paths_by_page=renders,
            output_directory=tmp_path / "bad-crops",
            policy=load_numeric_cell_crop_policy(
                project_root / "config/tables/numeric-cell-crops-v1.yaml"
            ),
        )


def test_numeric_crop_policy_withholds_context_from_recognizer(project_root):
    policy = load_numeric_cell_crop_policy(
        project_root / "config/tables/numeric-cell-crops-v1.yaml"
    )

    assert policy.recognizer_input_fields == ("crop_path",)
    assert {
        "row_label",
        "note_reference",
        "primary_ocr_text",
        "primary_ocr_value",
        "period_or_unit",
        "schema_label_or_report_norm_id",
        "historical_or_mongodb_value",
        "human_review_value",
    } == set(policy.forbidden_recognizer_inputs)
