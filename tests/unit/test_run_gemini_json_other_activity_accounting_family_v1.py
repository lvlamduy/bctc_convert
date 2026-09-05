from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = (
    ROOT
    / "scripts/experiments/"
    "run_gemini_json_other_activity_accounting_family_v1.py"
)
SPEC = importlib.util.spec_from_file_location("run_family38_v1", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
FULL271_SPEC = (
    ROOT
    / "config/families/"
    "tm-other-activity-pdf-residual-audit-full271-v1.json"
)
COMMON204_SPEC = (
    ROOT
    / "config/families/"
    "tm-other-activity-pdf-residual-audit-common204-v1.json"
)


def _json(path: Path) -> dict:
    return json.loads(path.read_bytes())


def _audit() -> dict:
    axes = {"pdf_residuals": [], "trials": []}
    material = {
        "axes": axes,
        "axis_counts": {name: len(axis) for name, axis in axes.items()},
        "axis_sha256": {
            name: canonical_json_sha256_v1(axis) for name, axis in axes.items()
        },
        "family_id": runner.FAMILY_ID,
        "format_version": runner.AUDIT_FORMAT_VERSION,
        "historical_comparator_policy_receipt": {
            "disposition": runner.NOT_APPLICABLE_DISJOINT_CORPUS,
            "policy": runner.DISJOINT_EXPANSION,
        },
        "observation_contract": {"violation_count": 0},
        "source_authentication_axis": [],
        "source_authentication_axis_sha256": canonical_json_sha256_v1([]),
        "state": "EXPERIMENTAL_AUDIT_COMPLETE",
    }
    return {
        **material,
        "audit_id": "gjoaauditv1:audit:" + canonical_json_sha256_v1(material),
    }


def _reseal_audit(value: dict) -> None:
    material = {key: item for key, item in value.items() if key != "audit_id"}
    value["audit_id"] = "gjoaauditv1:audit:" + canonical_json_sha256_v1(material)


def test_runner_pins_shared_multitable_implementation() -> None:
    runner._assert_shared_pins_v1()


def test_shared_multitable_pin_drift_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner, "_sha256", lambda _path: "0" * 64)
    with pytest.raises(
        runner.RunGeminiJsonOtherActivityV1Error,
        match="shared implementation pin drifted",
    ):
        runner._assert_shared_pins_v1()


def test_current_corpus_gate_rejects_historical_document() -> None:
    with pytest.raises(
        runner.RunGeminiJsonOtherActivityV1Error,
        match="outside the current reporting scope",
    ):
        runner._assert_current_corpus(
            {"documents": [{"relative_path": "bank/2024/report.pdf"}]}
        )


def test_source_repair_authentication_requires_real_pdf_root(tmp_path: Path) -> None:
    with pytest.raises(
        runner.RunGeminiJsonOtherActivityV1Error,
        match="source-PDF root is unavailable",
    ):
        runner._authenticate_source_repairs_v1(
            repairs=[],
            index={"documents": []},
            selected_page_axis=[],
            source_pdf_root=tmp_path / "missing",
        )


@pytest.mark.parametrize(
    ("path", "count"),
    [
        (FULL271_SPEC, 1),
        (COMMON204_SPEC, 0),
    ],
)
def test_pdf_residual_specs_seal_every_reviewed_source_region(
    path: Path,
    count: int,
) -> None:
    checked = runner._validate_pdf_residual_spec_v1(_json(path))
    assert len(checked["residuals"]) == count
    assert all(
        item["disposition"]
        == (
            "GENUINE_SOURCE_CONFLICT_DIRECT_PRIMARY_ROOT_27479_"
            "VERSUS_DIRECT_NOTE_ROOT_27478_MILLION_VND"
        )
        and item["source_page_axis"]
        for item in checked["residuals"]
    )


def test_pdf_residual_render_or_disposition_tampering_fails_closed() -> None:
    render_tamper = _json(FULL271_SPEC)
    render_tamper["residuals"][0]["source_page_axis"][0][
        "pdf_page_render_sha256"
    ] = "0" * 64
    with pytest.raises(
        runner.RunGeminiJsonOtherActivityV1Error,
        match="identity drifted",
    ):
        runner._validate_pdf_residual_spec_v1(render_tamper)

    disposition_tamper = _json(FULL271_SPEC)
    residual = disposition_tamper["residuals"][0]
    residual["disposition"] = "DERIVED_ZERO_FROM_BLANK"
    material = {
        key: copy.deepcopy(value)
        for key, value in residual.items()
        if key != "residual_audit_id"
    }
    residual["residual_audit_id"] = (
        "gjoapdfv1:residual:" + canonical_json_sha256_v1(material)
    )
    with pytest.raises(
        runner.RunGeminiJsonOtherActivityV1Error,
        match="invalid or unordered",
    ):
        runner._validate_pdf_residual_spec_v1(disposition_tamper)


def test_pdf_residual_status_disposition_pairing_rejects_resealed_conflict() -> None:
    tampered = _json(FULL271_SPEC)
    residual = tampered["residuals"][0]
    residual["status"] = runner.generic.NOT_OBSERVED
    residual["reasons"] = []
    material = {
        key: copy.deepcopy(value)
        for key, value in residual.items()
        if key != "residual_audit_id"
    }
    residual["residual_audit_id"] = (
        "gjoapdfv1:residual:" + canonical_json_sha256_v1(material)
    )
    with pytest.raises(
        runner.RunGeminiJsonOtherActivityV1Error,
        match="status/disposition pairing is invalid",
    ):
        runner._validate_pdf_residual_spec_v1(tampered)


def test_audit_rejects_observation_violation_and_identity_tamper() -> None:
    assert runner._validate_audit_v1(_audit())

    violation = copy.deepcopy(_audit())
    violation["observation_contract"]["violation_count"] = 1
    _reseal_audit(violation)
    with pytest.raises(
        runner.RunGeminiJsonOtherActivityV1Error,
        match="audit content is invalid",
    ):
        runner._validate_audit_v1(violation)

    identity = _audit()
    identity["state"] = "TAMPERED"
    with pytest.raises(
        runner.RunGeminiJsonOtherActivityV1Error,
        match="audit content is invalid|audit identity drifted",
    ):
        runner._validate_audit_v1(identity)
