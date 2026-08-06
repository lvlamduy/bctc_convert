from __future__ import annotations

import copy

import pytest

from bctc_ai.preprocessing.targeted_reread import (
    TargetedRereadError,
    load_targeted_reread_policy,
    plan_page_targeted_rereads,
)


def _policy(project_root):
    return load_targeted_reread_policy(
        project_root / "config/preprocessing/targeted-reread-v1.yaml"
    )


def _row(index, y, *, label=True, values=True):
    return {
        "geometry": {
            "y_anchor": y,
            "index_line_indices": [],
            "label_line_indices": [index] if label else [],
            "note_line_indices": [],
            "value_line_indices": [[index + 1], [index + 2]] if values else [[], []],
        }
    }


def _page(escalations, *, eligible=True, unresolved=False):
    rows = [_row(2 + index * 3, 100 + index * 40) for index in range(10)]
    alignment = []
    for index, escalation in enumerate(escalations):
        alignment.append(
            {
                "escalation": escalation,
                "role_b_indices": [index],
                "role_c_indices": [index],
            }
        )
    for index in range(len(escalations), len(rows)):
        alignment.append(
            {
                "escalation": "CROSS_READER_AGREEMENT_NO_CONFIDENCE_PROMOTION",
                "role_b_indices": [index],
                "role_c_indices": [index],
            }
        )
    return {
        "page": 7,
        "statement_type": "CDKT",
        "mapping_eligible": eligible,
        "role_b": {"tables": [{"status": "UNRESOLVED_COLUMN_ROLES" if unresolved else "PARSED"}]},
        "role_c": {
            "line_height": 20,
            "table_bbox": [40, 80, 760, 500],
            "axes": [
                {"header_line_index": 0},
                {"header_line_index": 1},
            ],
            "rows": rows,
        },
        "comparison": {"alignment": alignment},
    }


def _ocr():
    boxes = [[500, 45, 600, 65], [660, 45, 760, 65]]
    for index in range(10):
        y = 90 + index * 40
        boxes.extend(
            [
                [50, y, 350, y + 20],
                [520, y, 600, y + 20],
                [680, y, 760, y + 20],
            ]
        )
    return {"input_path": "baseline.png", "rec_boxes": boxes}


def test_dense_structural_failures_become_one_header_bound_full_table_crop(project_root):
    escalations = ["ROLE_B_MISSING_OR_TRUNCATED_ROW_REREAD"] * 6

    result = plan_page_targeted_rereads(
        _page(escalations),
        _ocr(),
        baseline_width=800,
        baseline_height=600,
        policy=_policy(project_root),
    )

    assert result["status"] == "PLANNED"
    assert result["dense_structural_recovery"] is True
    assert len(result["regions"]) == 1
    region = result["regions"][0]
    assert region["region_kind"] == "FULL_TABLE_STRUCTURAL_RECOVERY"
    assert region["target_dpi"] == 450
    assert region["readers"] == ("PADDLEOCR_VL_1_6", "PP_OCRV6_MEDIUM")
    assert region["includes_period_header_pixels"] is True
    assert region["period_binding_from_reread_allowed"] is True
    assert region["bbox_in_baseline_render"][1] < 45
    assert region["automatic_value_replacement"] is False
    assert region["automatic_confidence_promotion"] is False


def test_unresolved_role_b_table_forces_full_table_crop_even_below_density(project_root):
    page = _page(["TARGETED_NUMERIC_DISAGREEMENT_REREAD"], unresolved=True)

    result = plan_page_targeted_rereads(
        page,
        _ocr(),
        baseline_width=800,
        baseline_height=600,
        policy=_policy(project_root),
    )

    assert result["unresolved_role_b_table_present"] is True
    assert result["dense_structural_recovery"] is False
    assert [region["region_kind"] for region in result["regions"]] == [
        "FULL_TABLE_STRUCTURAL_RECOVERY"
    ]


def test_numeric_disagreements_group_by_relative_gap_and_use_600_dpi(project_root):
    page = _page(
        [
            "TARGETED_NUMERIC_DISAGREEMENT_REREAD",
            "TARGETED_NUMERIC_DISAGREEMENT_REREAD",
        ]
    )

    result = plan_page_targeted_rereads(
        page,
        _ocr(),
        baseline_width=800,
        baseline_height=600,
        policy=_policy(project_root),
    )

    assert len(result["regions"]) == 1
    region = result["regions"][0]
    assert region["region_kind"] == "NUMERIC_CELL_STRIP_REREAD"
    assert region["target_dpi"] == 600
    assert region["readers"] == ("PP_OCRV6_MEDIUM",)
    assert region["role_c_indices"] == (0, 1)
    assert region["includes_period_header_pixels"] is False
    assert region["period_binding_from_reread_allowed"] is False
    assert region["bbox_in_baseline_render"][1] <= 75
    assert region["bbox_in_baseline_render"][3] >= 190


def test_role_b_only_missing_candidate_is_localized_by_order_gap(project_root):
    page = _page([])
    page["comparison"]["alignment"].insert(
        5,
        {
            "escalation": "ROLE_C_MISSING_ROW_RECONSTRUCTION_OR_REREAD",
            "role_b_indices": [5],
            "role_c_indices": [],
        },
    )

    result = plan_page_targeted_rereads(
        page,
        _ocr(),
        baseline_width=800,
        baseline_height=600,
        policy=_policy(project_root),
    )

    assert len(result["regions"]) == 1
    region = result["regions"][0]
    assert region["region_kind"] == "ROW_BAND_STRUCTURAL_RECOVERY"
    assert region["localization_methods"] == ("ORDER_GAP_BRACKETED_BY_ROLE_C_ROWS",)
    assert region["role_b_indices"] == (5,)
    assert region["role_c_indices"] == ()


def test_mapping_ineligible_page_never_gets_a_crop(project_root):
    page = _page(["ROLE_B_MISSING_OR_TRUNCATED_ROW_REREAD"], eligible=False)

    result = plan_page_targeted_rereads(
        page,
        _ocr(),
        baseline_width=800,
        baseline_height=600,
        policy=_policy(project_root),
    )

    assert result["status"] == "SKIPPED_UPSTREAM_MAPPING_INELIGIBLE"
    assert result["regions"] == []


def test_unknown_escalation_is_retained_unresolved_not_silently_ignored(project_root):
    page = _page([])
    page["comparison"]["alignment"][0]["escalation"] = "NEW_UNKNOWN_FAILURE"

    result = plan_page_targeted_rereads(
        page,
        _ocr(),
        baseline_width=800,
        baseline_height=600,
        policy=_policy(project_root),
    )

    assert result["status"] == "UNRESOLVED_UNSUPPORTED_ESCALATION"
    assert result["regions"] == []
    assert result["unsupported_escalations"] == [
        {
            "alignment_index": 0,
            "escalation": "NEW_UNKNOWN_FAILURE",
            "status": "UNRESOLVED_UNSUPPORTED_ESCALATION",
        }
    ]


def test_invalid_line_index_fails_closed(project_root):
    page = _page(["TARGETED_INVALID_CELL_REREAD"])
    broken = copy.deepcopy(page)
    broken["role_c"]["rows"][0]["geometry"]["label_line_indices"] = [999]

    with pytest.raises(TargetedRereadError, match="exceeds baseline OCR axes"):
        plan_page_targeted_rereads(
            broken,
            _ocr(),
            baseline_width=800,
            baseline_height=600,
            policy=_policy(project_root),
        )
