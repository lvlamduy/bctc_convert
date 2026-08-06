from __future__ import annotations

import yaml

from bctc_ai.core.hashing import sha256_file


def test_e0032_control_uses_geometry_only_and_hashes_candidate(project_root):
    path = project_root / "config/experiments/e0032-mbb-cdkt-note-row-split.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert payload["experiment_id"] == "E-0032"
    assert payload["source"]["target_pages"] == [3, 4]
    assert payload["candidate"]["git_commit"] == (
        "44afda2231db8728ff1be548fb06c7e00f0319bd"
    )
    for record in payload["frozen_inputs"].values():
        assert sha256_file(project_root / record["path"]) == record["sha256"]
    for key in ("config", "algorithm", "inherited_v3_algorithm"):
        record = payload["candidate"][key]
        assert sha256_file(project_root / record["path"]) == record["sha256"]
    assert "label_text_or_accounting_semantics_as_split_feature" in payload[
        "forbidden_inputs"
    ]
    assert "numeric_value_or_magnitude_as_split_feature" in payload["forbidden_inputs"]
