from __future__ import annotations

import yaml

from bctc_ai.core.hashing import sha256_file


def test_e0034_control_binds_corrected_grid_and_geometry_only_padding(project_root):
    path = (
        project_root
        / "config/experiments/e0034-mbb-cdkt-numeric-verification-v2.yaml"
    )
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert payload["experiment_id"] == "E-0034"
    assert payload["row_contract"] == {
        "frozen_input_key": "e0033_row_contract",
        "experiment_id": "E-0033",
        "status": "PASS_REFERENCE_BLIND_NOTE_ROW_ANCHOR_SPLIT",
    }
    assert payload["registry_contract"] == {
        "format_version": 2,
        "policy": "FIXED_GRID_NUMERIC_CELL_CROPS_V2",
        "geometry_authority": "E0033_PP_OCRV6_FIXED_GRID",
    }
    assert payload["acceptance_policy"]["exact_cell_count"] == 128
    assert payload["acceptance_policy"]["exact_verified_dash_count"] == 5
    for record in payload["frozen_inputs"].values():
        assert sha256_file(project_root / record["path"]) == record["sha256"]
    for key in (
        "crop_policy",
        "model_config",
        "crop_algorithm",
        "reader_algorithm",
        "verification_algorithm",
    ):
        record = payload["candidate"][key]
        assert sha256_file(project_root / record["path"]) == record["sha256"]
    assert "row_labels_or_notes_as_numeric_reader_input" in payload["forbidden_inputs"]
