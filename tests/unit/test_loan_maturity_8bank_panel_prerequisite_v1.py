from __future__ import annotations

import copy
import hashlib
import json
import pickle
from pathlib import Path
from typing import Any, cast

import pytest

import bctc_ai.evaluation.loan_maturity_8bank_panel_prerequisite_v1 as panel_module
from bctc_ai.evaluation.loan_maturity_8bank_panel_prerequisite_v1 import (
    BANK_ORDER,
    BLOCKED,
    BLOCKED_PANEL,
    RECEIPT_CONTRACT,
    AuthenticatedLoanMaturity8BankPanelPrerequisiteV1,
    LoanMaturityPanelPrerequisiteV1Error,
    build_formal_panel_replay_envelope_v1,
    build_opaque_freezer_input_v1,
    project_authenticated_loan_maturity_8bank_panel_selection_v1,
    replay_loan_maturity_8bank_panel_prerequisite_v1,
    validate_authenticated_loan_maturity_8bank_panel_selection_v1,
    validate_loan_maturity_8bank_panel_prerequisite_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path("docs/experiments/E-0044-loan-maturity-8bank-vietocr-panel-prerequisite.json")


def _panel() -> dict[str, Any]:
    value = json.loads((PROJECT_ROOT / MANIFEST).read_text(encoding="utf-8"))
    return cast(dict[str, Any], value)


def _write_manifest(root: Path, panel: dict[str, Any]) -> Path:
    relative = Path("docs/panel.json")
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(panel, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return relative


def test_current_manifest_replays_exact_inventory_and_preserves_blockers() -> None:
    panel, capability = replay_loan_maturity_8bank_panel_prerequisite_v1(PROJECT_ROOT, MANIFEST)

    assert isinstance(capability, AuthenticatedLoanMaturity8BankPanelPrerequisiteV1)
    assert panel["state"] == BLOCKED_PANEL
    assert [slot["bank_code"] for slot in panel["slots"]] == list(BANK_ORDER)
    assert [(slot["bank_code"], slot["physical_page"]) for slot in panel["slots"]] == [
        ("ACB", 18),
        ("MBB", 31),
        ("VPB", 42),
        ("HDB", 26),
        ("VCB", 31),
        ("CTG", 39),
        ("BID", 22),
        ("VIB", 33),
    ]
    assert [
        slot["bank_code"]
        for slot in panel["slots"]
        if slot["freezer_prerequisite"]["state"] == BLOCKED
    ] == ["VPB", "VCB"]
    requirement = panel["uniform_run_requirement"]
    assert requirement["receipt_contract"] == RECEIPT_CONTRACT
    assert requirement["receipt_contract_implemented_by_this_artifact"] is False
    assert requirement["fresh_run_state"] == ("PROSPECTIVE_BLOCKED_NO_RUN_OR_RECEIPT_AUTHORITY")
    assert requirement["legacy_outputs_prohibited_as_authority_for_bank_codes"] == [
        "MBB",
        "CTG",
    ]
    assert panel["authority"]["completed_vietocr_run_authority"] is False
    assert panel["authority"]["authenticated_adapter_receipt_authority"] is False
    assert requirement["onnx_allowed"] is False
    assert requirement["fp32_inference_required"] is True
    assert requirement["pytorch_runtime_identity_required"] is True
    assert requirement["model_config_sha256_required"] is True
    assert requirement["model_weights_sha256_required"] is True

    envelope = build_formal_panel_replay_envelope_v1(capability)
    assert envelope["state"] == ("AUTHENTICATED_PREREQUISITE_REPLAY_BLOCKED_NO_FREEZER_INPUT")
    assert envelope["opaque_freezer_input"] is None
    binding = envelope["prerequisite_binding"]
    manifest_payload = (PROJECT_ROOT / MANIFEST).read_bytes()
    assert binding == {
        "experiment_id": "E-0044",
        "format_version": "LOAN_MATURITY_8BANK_VIETOCR_PANEL_PREREQUISITE_V1",
        "manifest_sha256": hashlib.sha256(manifest_payload).hexdigest(),
        "manifest_size_bytes": len(manifest_payload),
        "prospective_semantic_receipt_contract": RECEIPT_CONTRACT,
    }
    serialized = json.dumps(envelope, ensure_ascii=False)
    assert "E-0044" in serialized
    assert RECEIPT_CONTRACT in serialized


def test_partial_replayed_panel_cannot_emit_a_six_page_batch() -> None:
    _panel_value, capability = replay_loan_maturity_8bank_panel_prerequisite_v1(
        PROJECT_ROOT, MANIFEST
    )

    with pytest.raises(
        LoanMaturityPanelPrerequisiteV1Error,
        match=r"refusing a partial eight-slot freezer batch.*VPB.*VCB",
    ):
        build_opaque_freezer_input_v1(capability)


def test_live_capability_projects_only_closed_authenticated_selection_provenance() -> None:
    panel, capability = replay_loan_maturity_8bank_panel_prerequisite_v1(PROJECT_ROOT, MANIFEST)
    projection = project_authenticated_loan_maturity_8bank_panel_selection_v1(capability)
    manifest_payload = (PROJECT_ROOT / MANIFEST).read_bytes()

    assert set(projection) == {
        "authority",
        "bank_order",
        "experiment_id",
        "family_id",
        "format_version",
        "manifest_sha256",
        "manifest_size_bytes",
        "panel_state",
        "projection_id",
        "slots",
    }
    assert projection["format_version"] == (
        "LOAN_MATURITY_8BANK_AUTHENTICATED_PANEL_SELECTION_PROJECTION_V1"
    )
    assert projection["experiment_id"] == "E-0044"
    assert projection["family_id"] == "LOAN_MATURITY_BUCKETS"
    assert projection["manifest_sha256"] == hashlib.sha256(manifest_payload).hexdigest()
    assert projection["manifest_size_bytes"] == len(manifest_payload)
    assert projection["panel_state"] == BLOCKED_PANEL
    assert projection["bank_order"] == list(BANK_ORDER)
    assert projection["slots"] == [
        {
            "bank_code": slot["bank_code"],
            "physical_page": slot["physical_page"],
            "source_pdf_sha256": slot["source_pdf_sha256"],
        }
        for slot in panel["slots"]
    ]
    assert projection["authority"] == {
        "completed_vietocr_run_authority": False,
        "hydration_authority": False,
        "mapping_authority": False,
        "numeric_authority": False,
        "recognition_routing_authority": False,
        "selection_provenance_only": True,
        "semantic_authority": False,
    }
    identity_payload = copy.deepcopy(projection)
    del identity_payload["projection_id"]
    assert projection["projection_id"] == (
        "lm8bpsv1:projection:"
        f"{hashlib.sha256(canonical_json_bytes_v1(identity_payload)).hexdigest()}"
    )
    assert (
        validate_authenticated_loan_maturity_8bank_panel_selection_v1(projection, capability)
        == projection
    )
    serialized = json.dumps(projection, ensure_ascii=False)
    for excluded in (
        "freezer_prerequisite",
        "inventory_evidence",
        "render_ref",
        "result_ref",
        "authenticated_line_count",
    ):
        assert excluded not in serialized


def test_raw_forged_or_copied_state_cannot_project_authenticated_selection() -> None:
    panel, capability = replay_loan_maturity_8bank_panel_prerequisite_v1(PROJECT_ROOT, MANIFEST)
    projection = project_authenticated_loan_maturity_8bank_panel_selection_v1(capability)
    forged = object.__new__(AuthenticatedLoanMaturity8BankPanelPrerequisiteV1)

    with pytest.raises(LoanMaturityPanelPrerequisiteV1Error, match="requires one replay"):
        project_authenticated_loan_maturity_8bank_panel_selection_v1(cast(Any, panel))
    with pytest.raises(LoanMaturityPanelPrerequisiteV1Error, match="unknown or expired"):
        project_authenticated_loan_maturity_8bank_panel_selection_v1(forged)
    with pytest.raises(LoanMaturityPanelPrerequisiteV1Error):
        copy.copy(capability)
    with pytest.raises(LoanMaturityPanelPrerequisiteV1Error, match="requires one replay"):
        validate_authenticated_loan_maturity_8bank_panel_selection_v1(
            projection, cast(Any, projection)
        )


def test_coordinated_self_rehash_cannot_change_capability_bound_selection() -> None:
    _panel_value, capability = replay_loan_maturity_8bank_panel_prerequisite_v1(
        PROJECT_ROOT, MANIFEST
    )
    tampered = project_authenticated_loan_maturity_8bank_panel_selection_v1(capability)
    tampered["slots"][0]["physical_page"] += 1
    identity_payload = copy.deepcopy(tampered)
    del identity_payload["projection_id"]
    tampered["projection_id"] = (
        "lm8bpsv1:projection:"
        f"{hashlib.sha256(canonical_json_bytes_v1(identity_payload)).hexdigest()}"
    )

    with pytest.raises(
        LoanMaturityPanelPrerequisiteV1Error,
        match="does not match its replay capability",
    ):
        validate_authenticated_loan_maturity_8bank_panel_selection_v1(tampered, capability)


def test_formal_builder_requires_live_uncopyable_replay_capability() -> None:
    panel, capability = replay_loan_maturity_8bank_panel_prerequisite_v1(PROJECT_ROOT, MANIFEST)
    payload, digest, manifest_payload, manifest_digest = panel_module._AUTHENTICATED_PANELS[
        capability
    ]

    assert payload == canonical_json_bytes_v1(
        validate_loan_maturity_8bank_panel_prerequisite_v1(panel)
    )
    assert hashlib.sha256(payload).hexdigest() == digest
    assert manifest_payload == (PROJECT_ROOT / MANIFEST).read_bytes()
    assert hashlib.sha256(manifest_payload).hexdigest() == manifest_digest
    with pytest.raises(LoanMaturityPanelPrerequisiteV1Error, match="caller-constructed"):
        AuthenticatedLoanMaturity8BankPanelPrerequisiteV1(object())
    for operation in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(LoanMaturityPanelPrerequisiteV1Error):
            operation(capability)
    forged = object.__new__(AuthenticatedLoanMaturity8BankPanelPrerequisiteV1)
    with pytest.raises(LoanMaturityPanelPrerequisiteV1Error, match="unknown or expired"):
        build_opaque_freezer_input_v1(forged)
    with pytest.raises(LoanMaturityPanelPrerequisiteV1Error, match="requires one replay"):
        build_opaque_freezer_input_v1(cast(Any, panel))
    assert "_build_nonformal_opaque_freezer_input_proposal_v1" not in panel_module.__all__


def test_raw_refs_cannot_transition_hydration_slots_without_receipt_contract() -> None:
    proposed = _panel()
    opaque_ref = proposed["slots"][0]["freezer_prerequisite"]["result_ref"]
    for index in (2, 4):
        freezer = proposed["slots"][index]["freezer_prerequisite"]
        freezer.update(
            {
                "adapter_receipt_ref": None,
                "authenticated_line_count": 1,
                "blocker_codes": [],
                "render_ref": copy.deepcopy(
                    proposed["slots"][0]["freezer_prerequisite"]["render_ref"]
                ),
                "result_ref": copy.deepcopy(opaque_ref),
                "state": "READY_FOR_OPAQUE_ALL_LINE_FREEZE",
            }
        )
    proposed["state"] = "READY_FOR_SINGLE_OPAQUE_8_PAGE_FREEZE"

    with pytest.raises(LoanMaturityPanelPrerequisiteV1Error, match="cannot transition to ready"):
        validate_loan_maturity_8bank_panel_prerequisite_v1(proposed)

    proposed["slots"][2]["freezer_prerequisite"]["adapter_receipt_ref"] = copy.deepcopy(opaque_ref)
    with pytest.raises(LoanMaturityPanelPrerequisiteV1Error):
        validate_loan_maturity_8bank_panel_prerequisite_v1(proposed)


def test_raw_nonformal_proposal_cannot_impersonate_formal_replay() -> None:
    panel = _panel()
    proposal = panel_module._build_nonformal_opaque_freezer_input_proposal_v1(panel)

    assert proposal["format_version"] == "LOAN_MATURITY_8BANK_NONFORMAL_BATCH_PROPOSAL_V1"
    assert proposal["authority"]["formal_replay_authority"] is False
    assert proposal["candidate_opaque_freezer_input"] is None
    assert proposal["state"] == "NONFORMAL_BLOCKED_SHAPE_ONLY_PROPOSAL"
    assert proposal != build_formal_panel_replay_envelope_v1(
        replay_loan_maturity_8bank_panel_prerequisite_v1(PROJECT_ROOT, MANIFEST)[1]
    )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda panel: panel["slots"].__setitem__(0, copy.deepcopy(panel["slots"][1])),
        lambda panel: panel["slots"].pop(),
        lambda panel: panel.__setitem__("slot_count", 8.0),
        lambda panel: panel["slots"][0].__setitem__("physical_page", True),
        lambda panel: panel["slots"][0]["inventory_evidence"]["result_ref"].__setitem__(
            "size_bytes", True
        ),
        lambda panel: panel["slots"][0]["inventory_evidence"]["result_ref"].__setitem__(
            "path", "../outside.json"
        ),
        lambda panel: panel["uniform_run_requirement"].__setitem__(
            "receipt_contract", "GENERIC_VIETOCR_ALL_LINE_SEMANTIC_RECEIPT_V2"
        ),
        lambda panel: panel["uniform_run_requirement"].__setitem__("fresh_run_state", "COMPLETE"),
        lambda panel: panel["uniform_run_requirement"].__setitem__("onnx_allowed", True),
        lambda panel: panel["uniform_run_requirement"].__setitem__(
            "fp32_inference_required", False
        ),
        lambda panel: panel["slots"][2]["freezer_prerequisite"]["blocker_codes"].clear(),
        lambda panel: panel["slots"][4]["freezer_prerequisite"].__setitem__(
            "result_ref",
            copy.deepcopy(panel["slots"][4]["inventory_evidence"]["result_ref"]),
        ),
    ],
)
def test_closed_contract_rejects_type_path_provenance_and_policy_drift(mutation) -> None:
    panel = _panel()
    mutation(panel)

    with pytest.raises(LoanMaturityPanelPrerequisiteV1Error):
        validate_loan_maturity_8bank_panel_prerequisite_v1(panel)


def test_replay_detects_exact_inventory_hash_drift_before_missing_later_refs(
    tmp_path: Path,
) -> None:
    panel = _panel()
    first_ref = panel["slots"][0]["inventory_evidence"]["result_ref"]
    source = PROJECT_ROOT / first_ref["path"]
    target = tmp_path / first_ref["path"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes() + b"\n")
    manifest = _write_manifest(tmp_path, panel)

    with pytest.raises(LoanMaturityPanelPrerequisiteV1Error, match="hash- or size-drifted"):
        replay_loan_maturity_8bank_panel_prerequisite_v1(tmp_path, manifest)


def test_replay_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    manifest = Path("panel.json")
    (tmp_path / manifest).write_text('{"format_version":1,"format_version":2}', encoding="utf-8")

    with pytest.raises(LoanMaturityPanelPrerequisiteV1Error, match="duplicate key"):
        replay_loan_maturity_8bank_panel_prerequisite_v1(tmp_path, manifest)


def test_replay_rejects_symlink_manifest(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_text("{}", encoding="utf-8")
    manifest = tmp_path / "panel.json"
    manifest.symlink_to(target)

    with pytest.raises(LoanMaturityPanelPrerequisiteV1Error, match="nofollow"):
        replay_loan_maturity_8bank_panel_prerequisite_v1(tmp_path, Path("panel.json"))


def test_no_self_authored_hydration_receipt_can_transition_to_ready() -> None:
    proposed = _panel()
    freezer = proposed["slots"][2]["freezer_prerequisite"]
    fake_ref = copy.deepcopy(proposed["slots"][0]["freezer_prerequisite"]["result_ref"])
    freezer.update(
        {
            "adapter_receipt_ref": fake_ref,
            "authenticated_line_count": 110,
            "blocker_codes": [],
            "render_ref": copy.deepcopy(proposed["slots"][0]["freezer_prerequisite"]["render_ref"]),
            "result_ref": fake_ref,
            "state": "READY_FOR_OPAQUE_ALL_LINE_FREEZE",
        }
    )

    with pytest.raises(LoanMaturityPanelPrerequisiteV1Error, match="cannot transition to ready"):
        validate_loan_maturity_8bank_panel_prerequisite_v1(proposed)
