from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest


def _load(project_root: Path):
    path = project_root / "scripts/experiments/build_government_issued_papers_owner_closure_v1.py"
    spec = importlib.util.spec_from_file_location("government_issued_owner_closure_v1", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def closure(project_root: Path):
    module = _load(project_root)
    value = module.build_live_government_issued_papers_owner_closure_v1()
    return module, value


def test_owner_closure_exact_mappings_and_remaining_scope(closure):
    module, value = closure
    assert value["metrics"] == {
        "adjudicated_mapping_count": 10,
        "closed_ledger_entry_count": 9,
        "government_post_closure_mapping_count": 32,
        "government_post_closure_open_source_row_count": 0,
        "issued_papers_post_closure_mapping_count": 71,
        "issued_papers_post_closure_open_source_row_count": 3,
        "remaining_targeted_unresolved_count": 3,
        "source_value_component_count": 18,
        "superseded_mapping_count": 1,
    }
    by_ledger = {row["ledger_id"]: row for row in value["mappings"]}
    assert {key: row["schema_binding"]["report_norm_id"] for key, row in by_ledger.items()} == {
        "BID-FINANCE-MINISTRY-SUPERSEDE": 6072,
        "GN-001": 6070,
        "GN-002": 6070,
        "GN-003": 6070,
        "GN-004": 6071,
        "IVP-001": 1111,
        "IVP-002": 1103,
        "IVP-003": 6010,
        "IVP-004": 6009,
        "IVP-008": 1117,
    }
    assert by_ledger["BID-FINANCE-MINISTRY-SUPERSEDE"]["supersedes_report_norm_id"] == 1039
    assert [row["ledger_id"] for row in value["remaining_unresolved"]] == [
        "IVP-005",
        "IVP-006",
        "IVP-007",
    ]
    assert module._validate(value) == value


def test_owner_closure_persisted_artifact_exact_replays(project_root: Path, closure):
    module, value = closure
    path = project_root / module.OUTPUT_PATH
    if not path.exists():
        pytest.skip("generated closure artifact is created after the first focused build")
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert module.validate_government_issued_papers_owner_closure_replay_v1(persisted) == value


def test_owner_closure_rejects_coordinated_promotion_and_typed_metric_forgery(closure):
    module, value = closure
    promoted = copy.deepcopy(value)
    promoted["remaining_unresolved"] = []
    promoted["metrics"]["remaining_targeted_unresolved_count"] = 0
    material = copy.deepcopy(promoted)
    material.pop("result_id")
    promoted["result_id"] = "e0080:result:" + module.canonical_json_sha256_v1(material)
    with pytest.raises(module.GovernmentIssuedPapersOwnerClosureV1Error):
        module._validate(promoted)

    typed = copy.deepcopy(value)
    typed["metrics"]["adjudicated_mapping_count"] = 10.0
    material = copy.deepcopy(typed)
    material.pop("result_id")
    typed["result_id"] = "e0080:result:" + module.canonical_json_sha256_v1(material)
    with pytest.raises(module.GovernmentIssuedPapersOwnerClosureV1Error):
        module._validate(typed)
