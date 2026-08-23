from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts/experiments/build_family_first_derivative_140_filing_schema_sweep_v1.py"
)
_SPEC = importlib.util.spec_from_file_location("build_derivative_140_sweep_v1", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
subject = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(subject)


RESULT = {
    "metrics": {
        "bounded_not_observed_count": 1,
        "document_count": 2,
        "numeric_challenger_rescue_count": 1,
        "unresolved_document_count": 0,
        "verified_document_count": 1,
        "verified_mapping_count": 4,
    },
    "sweep_id": "sweep-1",
}


def _install(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subject,
        "_inputs",
        lambda _root: (
            {"family_id": "DERIVATIVE_FINANCIAL_INSTRUMENTS"},
            {"layout": "test"},
            {"binding": "test"},
            [{"schema_id": 1}],
            {"challenger": "test"},
        ),
    )
    monkeypatch.setattr(
        subject.document_store_v1,
        "authenticate_family_first_document_evidence_store_v1",
        lambda _root: object(),
    )
    monkeypatch.setattr(
        subject.sweep_v1,
        "build_authenticated_family_first_stacked_period_schema_sweep_v1",
        lambda *_args, jobs: RESULT,
    )


def test_build_then_verify_uses_one_fixed_noclobber_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install(monkeypatch)
    built = subject.run_family_first_derivative_140_filing_schema_sweep_v1(
        tmp_path, command="build", jobs=2
    )
    output = tmp_path / subject.OUTPUT_PATH
    assert json.loads(output.read_text(encoding="utf-8")) == RESULT
    assert built["metrics"] == RESULT["metrics"]

    verified = subject.run_family_first_derivative_140_filing_schema_sweep_v1(
        tmp_path, command="verify", jobs=2
    )
    assert verified == built

    with pytest.raises(ValueError, match="already exists"):
        subject.run_family_first_derivative_140_filing_schema_sweep_v1(
            tmp_path, command="build", jobs=2
        )
