from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_EXPERIMENTS = _ROOT / "scripts/experiments"
if str(_EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENTS))


def _load():
    name = "capture_e0048_mbb_maturity_numeric_verification_test"
    path = _EXPERIMENTS / "capture_e0048_mbb_maturity_numeric_verification.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


subject = _load()


def _result() -> dict:
    roles = ("SHORT_TERM", "MEDIUM_TERM", "LONG_TERM", "TOTAL")
    lines = subject._EXPECTED_SOURCE_LINES
    cells = []
    for index, line in enumerate(lines):
        row, axis = divmod(index, 2)
        value = str((index + 1) * 1000)
        cells.append(
            {
                "axis_id": f"axis-{axis}",
                "axis_ordinal": axis,
                "cell_id": f"page-0002-row-{row:03d}-axis-{axis + 1}",
                "challenger": {"raw_text": value},
                "crop_sha256": f"{index + 1:064x}",
                "decision": "ACCEPT_EXACT_VALUE_AND_SIGN_AGREEMENT",
                "final_value_status": "OBSERVED_VALUE",
                "normalized_numeric_value": value,
                "page_ordinal": 2,
                "primary": {"raw_text": value},
                "row_ordinal": row,
                "row_role": roles[row],
                "selected_raw_value": value,
                "source_atom_id": f"atom-{index}",
                "source_evidence_node_id": f"evidence-{index}",
                "source_graph_node_id": f"value-{index}",
                "source_line_index": line,
                "verification_status": "VERIFIED_OBSERVED_VALUE",
            }
        )
    value = {
        "cells": cells,
        "claim_boundary": subject.CLAIM_BOUNDARY,
        "closure_equations": [
            {
                "addends": [1000, 3000, 5000],
                "axis_ordinal": 0,
                "observed_total": 7000,
                "residual": -2000,
                "status": "UNRESOLVED",
            },
            {
                "addends": [2000, 4000, 6000],
                "axis_ordinal": 1,
                "observed_total": 8000,
                "residual": -4000,
                "status": "UNRESOLVED",
            },
        ],
        "experiment_id": subject.EXPERIMENT_ID,
        "format_version": subject.FORMAT_VERSION,
        "inputs": {"opaque": "test"},
        "metrics": {
            "cell_count": 8,
            "closure_axis_count": 2,
            "corroborated_closure_axis_count": 0,
            "mapped_cell_count": 0,
            "reader_score_decision_use_count": 0,
            "unresolved_cell_count": 0,
            "verified_cell_count": 8,
        },
        "safety": copy.deepcopy(subject._SAFETY),
        "state": subject.STATE,
        "status": "COMPLETE_WITH_UNRESOLVED_NUMERIC_CANDIDATES",
        "verification_id": "",
    }
    value["verification_id"] = subject._verification_id(value)
    return value


def test_result_shape_preserves_numeric_only_boundary() -> None:
    value = _result()

    assert subject._validate_result_shape(value) == value
    assert value["metrics"]["mapped_cell_count"] == 0
    assert value["safety"]["mapping_or_verified_by_codex_authority"] is False
    assert value["safety"]["source_only_total_mapped_to_schema"] is False


def test_verified_by_codex_token_is_forbidden_even_after_rehash() -> None:
    value = _result()
    value["inputs"]["forged_status"] = "VERIFIED_BY_CODEX"
    value["verification_id"] = subject._verification_id(value)

    with pytest.raises(
        subject.E0048MBBMaturityNumericVerificationError,
        match="identity or safety boundary",
    ):
        subject._validate_result_shape(value)


def test_metric_bool_is_not_accepted_as_integer() -> None:
    value = _result()
    value["metrics"]["mapped_cell_count"] = False
    value["verification_id"] = subject._verification_id(value)

    with pytest.raises(
        subject.E0048MBBMaturityNumericVerificationError,
        match="metrics drifted",
    ):
        subject._validate_result_shape(value)


def test_public_validator_rejects_coordinated_cell_rehash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = _result()
    monkeypatch.setattr(
        subject,
        "build_e0048_mbb_maturity_numeric_verification_v1",
        lambda _root: copy.deepcopy(expected),
    )
    forged = copy.deepcopy(expected)
    forged["cells"][4]["crop_sha256"] = "f" * 64
    forged["verification_id"] = subject._verification_id(forged)

    with pytest.raises(
        subject.E0048MBBMaturityNumericVerificationError,
        match="differs from exact live replay",
    ):
        subject.validate_e0048_mbb_maturity_numeric_verification_v1(forged, _ROOT)
