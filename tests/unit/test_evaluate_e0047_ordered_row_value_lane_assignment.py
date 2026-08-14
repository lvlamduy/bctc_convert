from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_ROOT = Path(__file__).resolve().parents[2]
_ARTIFACT = (
    _ROOT / "docs/experiments/E-0047-loan-maturity-ordered-row-value-lane-mechanism-evaluation.json"
)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


if "vietocr_semantic_page_binding_v3" not in sys.modules:
    _load(
        "vietocr_semantic_page_binding_v3",
        _ROOT / "scripts/experiments/vietocr_semantic_page_binding_v3.py",
    )
if "build_loan_maturity_8bank_v3_provisional_sweep" not in sys.modules:
    _load(
        "build_loan_maturity_8bank_v3_provisional_sweep",
        _ROOT / "scripts/experiments/build_loan_maturity_8bank_v3_provisional_sweep.py",
    )
lane_v1 = _load(
    "ordered_row_value_lane_assignment_v1",
    _ROOT / "scripts/experiments/ordered_row_value_lane_assignment_v1.py",
)
e0047 = _load(
    "evaluate_e0047_ordered_row_value_lane_assignment",
    _ROOT / "scripts/experiments/evaluate_e0047_ordered_row_value_lane_assignment.py",
)


def _sample(index: int, text: str, bbox: list[int]) -> dict[str, object]:
    return {
        "normalized_prediction": text,
        "source_line_index": index,
        "source_bbox_raw_pixels": bbox,
        "source_atom": {
            "source_atom_id": "ssv1:atom:" + f"{index + 1:064x}",
            "canonical_bbox_mpt": [item * 1_000 for item in bbox],
        },
    }


def _synthetic_observation_inputs(*, percentage_companions: bool = False):
    entries: list[tuple[str, str, list[int]]] = []

    def add(text: str, raw: str, bbox: list[int]) -> None:
        entries.append((text, raw, bbox))

    add("Cho vay khách hàng", "owner", [0, 0, 180, 20])
    add("Phân tích dư nợ theo thời hạn", "branch", [0, 30, 260, 50])
    add("30/06/2026", "30/06/2026", [100, 70, 150, 90])
    add("31/12/2025", "31/12/2025", [300, 70, 350, 90])
    add("Triệu đồng", "unit", [100, 95, 150, 115])
    if percentage_companions:
        add("%", "%", [200, 95, 230, 115])
    add("Triệu đồng", "unit", [300, 95, 350, 115])
    if percentage_companions:
        add("%", "%", [400, 95, 430, 115])

    rows = (
        ("Nợ ngắn hạn", 130, ("10", "11"), ("40,52", "41,59")),
        ("Nợ trung hạn", 170, ("20", "21"), ("14,54", "11,47")),
        ("Nợ dài hạn", 210, ("30", "31"), ("44,94", "46,94")),
    )
    for label, y, monetary, percentages in rows:
        add(label, label, [0, y, 90, y + 30])
        add(monetary[0], monetary[0], [100, y - 2, 150, y + 20])
        if percentage_companions:
            add(percentages[0], percentages[0], [200, y - 2, 250, y + 20])
        add(monetary[1], monetary[1], [300, y - 2, 350, y + 20])
        if percentage_companions:
            add(percentages[1], percentages[1], [400, y - 2, 450, y + 20])

    add("60", "60", [100, 260, 150, 282])
    if percentage_companions:
        add("100,00", "100,00", [200, 260, 250, 282])
    add("63", "63", [300, 260, 350, 282])
    if percentage_companions:
        add("100,00", "100,00", [400, 260, 450, 282])

    source = {
        "source_local_page_id": "ssv2:page:" + "1" * 64,
        "page_result": {"lines": [{"raw_text": raw} for _text, raw, _bbox in entries]},
    }
    binding = {
        "samples": [_sample(index, text, bbox) for index, (text, _raw, bbox) in enumerate(entries)]
    }
    return source, binding


def test_ordered_assignment_rebuilds_overlap_case_into_accepted_graph():
    source, binding = _synthetic_observation_inputs()
    alias_index = e0047.compile_vietnamese_family_alias_index_v1(e0047._FAMILY_SPECS)

    observation, assignment = e0047._candidate_payload_with_ordered_lanes(
        source, binding, alias_index
    )
    assert assignment is not None
    assert assignment["status"] == lane_v1.RESOLVED_STATUS
    assert [row["value_source_line_indices"] for row in assignment["rows"]] == [
        [7, 8],
        [10, 11],
        [13, 14],
    ]
    assert observation["status"] == "READY_FOR_GRAPH_V2"
    graph = e0047.graph_v2._build_from_observation(
        observation,
        e0047.LOAN_MATURITY_BUCKETS_SPEC_V1,
        e0047._FAMILY_SPECS,
    )
    assert graph["status"] == "ACCEPTED_WITHIN_SUPPLIED_FAMILY_COLLISION_SCOPE"


def test_percentage_companion_lanes_are_explicitly_unresolved():
    source, binding = _synthetic_observation_inputs(percentage_companions=True)
    alias_index = e0047.compile_vietnamese_family_alias_index_v1(e0047._FAMILY_SPECS)

    observation, assignment = e0047._candidate_payload_with_ordered_lanes(
        source, binding, alias_index
    )
    assert assignment is not None
    assert assignment["status"] == lane_v1.UNRESOLVED_STATUS
    assert assignment["metrics"]["companion_numeric_count"] == 6
    assert observation["status"] == "UNRESOLVED"
    assert observation["unresolved_reasons"] == [
        "ORDERED_ROW_VALUE_LANE_ASSIGNMENT_NOT_RESOLVED",
        "UNTYPED_NUMERIC_COMPANION_LANES_NOT_RESOLVED",
    ]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("160.883.061", True),
        ("40,52", True),
        ("100.00%", True),
        ("30/06/2026", False),
        ("Nợ ngắn hạn", False),
        (0, False),
    ],
)
def test_numeric_geometry_frontier_is_syntax_only(text, expected):
    assert e0047._is_numeric_observation_text(text) is expected


def _fake_projection(
    status: str,
    *,
    identifier_field: str | None = None,
    metrics: bool = False,
    reasons: list[str] | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "payload_sha256": "a" * 64,
        "status": status,
        "unresolved_reasons": reasons or [],
    }
    if identifier_field is not None:
        result[identifier_field] = identifier_field + ":value"
    if metrics:
        result["metrics"] = {"count": 0}
    return result


def _fake_schema_projection() -> dict[str, object]:
    result = _fake_projection(
        "UNRESOLVED_GRAPH_NOT_ACCEPTED",
        identifier_field="candidate_set_id",
        metrics=True,
    )
    result.update(
        {
            "candidate_report_norm_ids": [],
            "source_only_roles": [],
            "structural_context_candidate_report_norm_ids": [],
            "unassessed_report_norm_ids": [],
            "value_row_candidate_report_norm_ids": [],
        }
    )
    return result


def _fake_result() -> dict[str, object]:
    modes = (
        e0047.e0046._ORDINARY_MODE,
        e0047.e0046._ORDINARY_MODE,
        e0047.e0046._NATIVE_MODE,
        e0047.e0046._ORDINARY_MODE,
        e0047.e0046._TERMINAL_MODE,
        e0047.e0046._ORDINARY_MODE,
        e0047.e0046._ORDINARY_MODE,
        e0047.e0046._ORDINARY_MODE,
    )
    trials = []
    for ordinal, (bank, mode) in enumerate(zip(e0047.e0046.BANK_ORDER, modes, strict=True), 1):
        trials.append(
            {
                "trial_id": f"trial-{ordinal:04d}",
                "bank_provenance": bank,
                "page_ordinal": ordinal,
                "binding_mode": mode,
                "mechanism_status": "NOT_APPLICABLE_NO_EXISTING_ROW_VALUE_AXIS_BLOCKER",
                "assignment": None,
                "prior_observation": _fake_projection("UNRESOLVED", reasons=["OTHER_BLOCKER"]),
                "observation": _fake_projection("UNRESOLVED", reasons=["OTHER_BLOCKER"]),
                "semantic_graph": _fake_projection(
                    "UNRESOLVED",
                    identifier_field="graph_id",
                    metrics=True,
                    reasons=["OTHER_BLOCKER"],
                ),
                "schema_candidate": _fake_schema_projection(),
                "independent_numeric_status": "NOT_EVALUATED",
                "independent_mapping_status": "NOT_EVALUATED",
            }
        )
    refs = [
        {"path": path, "sha256": "b" * 64, "size_bytes": 1} for path in e0047._IMPLEMENTATION_PATHS
    ]
    result: dict[str, object] = {
        "format_version": e0047.FORMAT_VERSION,
        "experiment_id": e0047.EXPERIMENT_ID,
        "state": e0047.STATE,
        "claim_boundary": e0047.CLAIM_BOUNDARY,
        "family_id": e0047.LOAN_MATURITY_BUCKETS_SPEC_V1.family_id,
        "bank_order": list(e0047.e0046.BANK_ORDER),
        "input_authority": {
            "e0046_capture": {
                "path": str(e0047.E0046_CAPTURE_PATH),
                "sha256": "c" * 64,
                "size_bytes": 1,
                "sweep_id": "e0046:provisional-sweep:" + "d" * 64,
            },
            "e0046_seal": {
                "path": e0047.E0046_SEAL_PATH.as_posix(),
                "sha256": "e" * 64,
                "size_bytes": 1,
            },
            "implementation_refs": refs,
        },
        "trials": trials,
        "metrics": e0047._metrics(trials),
        "safety": copy.deepcopy(e0047._SAFETY),
    }
    result["result_id"] = "e0047:lane-evaluation:" + canonical_json_sha256_v1(result)
    return result


def _rehash(result: dict[str, object]) -> None:
    material = copy.deepcopy(result)
    del material["result_id"]
    result["result_id"] = "e0047:lane-evaluation:" + canonical_json_sha256_v1(material)


def test_result_shape_rejects_typed_safety_and_verification_promotion():
    result = _fake_result()
    assert e0047._validate_shape(result) == result

    forged = copy.deepcopy(result)
    forged["safety"]["mapping_authority"] = 0
    _rehash(forged)
    with pytest.raises(e0047.E0047OrderedLaneEvaluationError):
        e0047._validate_shape(forged)

    forged = copy.deepcopy(result)
    forged["trials"][0]["independent_mapping_status"] = "VERIFIED_BY_CODEX"
    _rehash(forged)
    with pytest.raises(e0047.E0047OrderedLaneEvaluationError):
        e0047._validate_shape(forged)


def test_public_replay_rejects_coordinated_result_rehash(monkeypatch):
    result = _fake_result()
    monkeypatch.setattr(e0047, "_root", lambda _value: _ROOT)
    monkeypatch.setattr(e0047, "_input_authority", lambda _root: ({}, {}))
    monkeypatch.setattr(
        e0047,
        "_build_payload",
        lambda _root, _payload, _authority: copy.deepcopy(result),
    )
    assert e0047.validate_e0047_ordered_row_value_lane_evaluation(result, _ROOT) == result

    forged = copy.deepcopy(result)
    forged["trials"][0]["observation"]["status"] = "READY_FOR_GRAPH_V2"
    _rehash(forged)
    with pytest.raises(e0047.E0047OrderedLaneEvaluationError):
        e0047.validate_e0047_ordered_row_value_lane_evaluation(forged, _ROOT)


def test_tracked_e0047_artifact_preserves_candidate_verification_boundaries():
    artifact = json.loads(_ARTIFACT.read_text(encoding="utf-8"))
    assert e0047._validate_shape(artifact) == artifact
    assert artifact["metrics"] == {
        "accepted_structure_count": 1,
        "assignment_resolved_count": 2,
        "assignment_unresolved_count": 1,
        "bank_count": 8,
        "independent_mapping_evaluated_count": 0,
        "independent_numeric_evaluated_count": 0,
        "mechanism_target_count": 3,
        "schema_candidate_ready_count": 1,
        "untyped_companion_blocked_count": 1,
        "verified_mapping_count": 0,
    }

    by_bank = {trial["bank_provenance"]: trial for trial in artifact["trials"]}
    mbb = by_bank["MBB"]
    assert mbb["schema_candidate"]["structural_context_candidate_report_norm_ids"] == [
        716,
        752,
    ]
    assert mbb["schema_candidate"]["value_row_candidate_report_norm_ids"] == [
        753,
        754,
        755,
    ]
    assert mbb["schema_candidate"]["source_only_roles"] == ["TOTAL"]
    assert mbb["schema_candidate"]["unassessed_report_norm_ids"] == [5747]
    assert by_bank["BID"]["observation"]["unresolved_reasons"] == [
        "PER_AXIS_UNIT_SCOPE_NOT_RESOLVED"
    ]
    assert by_bank["VIB"]["assignment"]["metrics"]["companion_numeric_count"] == 6
    assert by_bank["CTG"]["observation"]["unresolved_reasons"] == [
        "ORDERED_CHILDREN_NOT_RESOLVED_FROM_TRANSFORMER",
        "OWNER_NOT_RESOLVED_FROM_TRANSFORMER",
    ]
    assert all(trial["independent_mapping_status"] == "NOT_EVALUATED" for trial in by_bank.values())
