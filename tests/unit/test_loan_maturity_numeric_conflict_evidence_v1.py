from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _ROOT / "scripts/experiments/loan_maturity_numeric_conflict_evidence_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "loan_maturity_numeric_conflict_evidence_v1", _MODULE_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
conflict = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = conflict
_SPEC.loader.exec_module(conflict)

_ARTIFACT = (
    _ROOT / "docs/experiments/"
    "E-0170-family-first-loan-maturity-hosted-gemma4-numeric-challenger-v1.json"
)
_STORE = _ROOT / "data/registered/family_first_document_evidence_store_v1.json"


def _artifact() -> dict[str, Any]:
    return json.loads(_ARTIFACT.read_text())


def _packet() -> dict[str, Any]:
    store = json.loads(_STORE.read_text())
    return next(item for item in store["documents"] if item["document_ordinal"] == 17)


def _cell(lane: int, y: int, source_line: int) -> dict[str, Any]:
    left = 1017 if lane == 0 else 1275
    return {
        "bbox": [left, y, left + 162, y + 34],
        "lane_index": lane,
        "source_line_index": source_line,
    }


def _graph_with_provider_reordering() -> dict[str, Any]:
    return {
        "margin": {
            "values": [_cell(0, 2000, 4), _cell(1, 1995, 88)],
        },
        "rows": [
            {
                "role": "SHORT_TERM",
                "values": [_cell(0, 1825, 97), _cell(1, 1818, 2)],
            },
            {
                "role": "MEDIUM_TERM",
                "values": [_cell(0, 1857, 1), _cell(1, 1846, 71)],
            },
            {
                "role": "LONG_TERM",
                "values": [_cell(0, 1888, 60), _cell(1, 1883, 3)],
            },
        ],
    }


def test_e0170_live_bytes_raw_json_and_authenticated_packet_replay() -> None:
    value = _artifact()

    assert (
        conflict.validate_loan_maturity_hosted_gemma4_challenger_v1(value, _ROOT, _packet())
        == value
    )


def test_e0170_metadata_and_packet_tampering_fail_closed() -> None:
    value = _artifact()
    value["requests"][1]["response_id"] = value["requests"][0]["response_id"]
    with pytest.raises(conflict.LoanMaturityNumericConflictEvidenceV1Error):
        conflict.validate_loan_maturity_hosted_gemma4_challenger_v1(value)

    packet = _packet()
    packet["document_evidence_root_sha256"] = "0" * 64
    with pytest.raises(conflict.LoanMaturityNumericConflictEvidenceV1Error):
        conflict.validate_loan_maturity_hosted_gemma4_challenger_v1(_artifact(), _ROOT, packet)


@pytest.mark.parametrize(
    "payload",
    [
        '{"responseId":"first","responseId":"second"}',
        '{"value":NaN}',
        '{"value":Infinity}',
    ],
)
def test_hosted_json_rejects_duplicate_keys_and_non_finite_numbers(payload: str) -> None:
    with pytest.raises(conflict.LoanMaturityNumericConflictEvidenceV1Error):
        conflict._strict_json_loads(payload, "test response")


def test_total_binding_uses_geometry_not_provider_order() -> None:
    controls = _artifact()["accounting_effect"]["printed_control_cells"]

    conflict._bind_controls_to_graph_geometry(_graph_with_provider_reordering(), controls)

    wrong_lane = copy.deepcopy(controls)
    wrong_lane[0]["source_bbox_cached_200dpi"] = [1272, 1939, 1435, 1974]
    with pytest.raises(conflict.LoanMaturityNumericConflictEvidenceV1Error):
        conflict._bind_controls_to_graph_geometry(_graph_with_provider_reordering(), wrong_lane)

    wrong_row = copy.deepcopy(controls)
    wrong_row[3]["source_bbox_cached_200dpi"] = [1275, 2151, 1437, 2185]
    with pytest.raises(conflict.LoanMaturityNumericConflictEvidenceV1Error):
        conflict._bind_controls_to_graph_geometry(_graph_with_provider_reordering(), wrong_row)
