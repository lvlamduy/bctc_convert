from __future__ import annotations

import yaml

from bctc_ai.core.hashing import sha256_file


def test_e0032_control_uses_geometry_only_and_hashes_candidate(project_root):
    path = project_root / "config/experiments/e0032-mbb-cdkt-note-row-split.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert payload["experiment_id"] == "E-0032"
    assert payload["status"] == "SUPERSEDED_BY_E0033_IMMUTABLE_V3_CORRECTION"
    assert payload["source"]["target_pages"] == [3, 4]
    assert payload["candidate"]["git_commit"] == (
        "44afda2231db8728ff1be548fb06c7e00f0319bd"
    )
    for record in payload["frozen_inputs"].values():
        assert sha256_file(project_root / record["path"]) == record["sha256"]
    assert payload["candidate"]["algorithm"]["sha256"] != sha256_file(
        project_root / payload["candidate"]["algorithm"]["path"]
    )
    assert payload["candidate"]["inherited_v3_algorithm"]["sha256"] != sha256_file(
        project_root / payload["candidate"]["inherited_v3_algorithm"]["path"]
    )
    assert "label_text_or_accounting_semantics_as_split_feature" in payload[
        "forbidden_inputs"
    ]
    assert "numeric_value_or_magnitude_as_split_feature" in payload["forbidden_inputs"]


def test_e0033_control_restores_v3_and_hashes_isolated_v4(project_root):
    path = (
        project_root
        / "config/experiments/e0033-mbb-cdkt-note-row-split-immutable.yaml"
    )
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert payload["experiment_id"] == "E-0033"
    assert payload["candidate"]["git_commit"] == (
        "dbba296de95638750286e898e82536d35c466bcc"
    )
    for record in payload["frozen_inputs"].values():
        assert sha256_file(project_root / record["path"]) == record["sha256"]
    for key in ("config", "algorithm", "inherited_v3_algorithm"):
        record = payload["candidate"][key]
        assert sha256_file(project_root / record["path"]) == record["sha256"]
    assert payload["candidate"]["inherited_v3_algorithm"]["sha256"] == (
        "e5650bd48866340cec32ed41e8b131cdf8289c25479be43a11c29763ea153663"
    )
