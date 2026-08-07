from __future__ import annotations

import yaml

from bctc_ai.core.hashing import sha256_file


def test_e0035_control_freezes_all_rows_without_reference_inputs(project_root):
    path = project_root / "config/experiments/e0035-mbb-cdkt-logical-row-label-crops.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert payload["experiment_id"] == "E-0035"
    assert payload["selection_policy"] == (
        "ALL_E0033_CDKT_ROWS_SELECTED_BEFORE_ANY_SEMANTIC_READER_OUTPUT"
    )
    assert payload["statement"]["exact_rows_by_page"] == {3: 39, 4: 25}
    assert payload["statement"]["exact_row_count"] == 64
    assert payload["authority"]["reader_receives_crop_pixels_only"] is True
    assert payload["authority"]["human_review_is_available_to_crop_builder"] is False
    assert payload["authority"]["template_or_history_is_available_to_crop_builder"] is False
    assert payload["crop_policy"]["resize"] is False
    assert payload["crop_policy"]["threshold"] is False
    assert payload["crop_policy"]["deskew"] is False
    assert "numeric_cell_text_value_sign_or_status" in payload["forbidden_inputs"]
    algorithm = payload["candidate"]["crop_algorithm"]
    assert sha256_file(project_root / algorithm["path"]) == algorithm["sha256"]
    assert (project_root / algorithm["path"]).stat().st_size == algorithm["size_bytes"]
