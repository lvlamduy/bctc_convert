from __future__ import annotations

import copy
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from bctc_ai.evaluation import e0039_review_packet as packet
from bctc_ai.evaluation.e0039_review_packet import (
    E0039ReviewPacketError,
    capture_e0039_review_packet,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
HEAD = "a" * 40
FIXTURE_FILES = tuple(
    sorted(
        {
            packet.CONTROL_RELATIVE_PATH,
            *packet._FROZEN_PATHS.values(),
            *packet._IMPLEMENTATION_PATHS.values(),
        },
        key=Path.as_posix,
    )
)


def _copy_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    for relative in FIXTURE_FILES:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPOSITORY_ROOT / relative, destination)
    return root


def _allow_fixture_git(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    bindings: list[str] = []
    monkeypatch.setattr(packet, "_clean_git_commit", lambda _root: HEAD)

    def record_binding(
        _root: Path,
        _record: object,
        *,
        name: str,
        path: Path,
        reader: object,
    ) -> None:
        del path, reader
        bindings.append(name)

    monkeypatch.setattr(packet, "_head_bind", record_binding)
    return bindings


def _capture_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, dict[str, object]]:
    root = _copy_fixture(tmp_path)
    _allow_fixture_git(monkeypatch)
    result = capture_e0039_review_packet(root)
    return root, result


def test_capture_builds_exact_answer_free_six_plus_two_packet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    bindings = _allow_fixture_git(monkeypatch)
    opened: list[str] = []
    opened_paths: list[str] = []

    def tracking_reader(
        project_root: Path,
        path: Path,
        label: str,
        **kwargs: object,
    ):
        opened.append(label)
        opened_paths.append(path.relative_to(project_root).as_posix())
        return packet._read_stable_file(project_root, path, label, **kwargs)

    result = capture_e0039_review_packet(root, _reader=tracking_reader)

    assert result["state"] == packet.PACKET_STATE
    assert result["deterministic_replay"] == {
        "evidence_assembly_invocation_count": 2,
        "exact_canonical_byte_equality": True,
        "canonical_encoding": "UTF8_JSON_SORTED_KEYS_COMPACT_NO_NAN_NO_DUPLICATE_KEYS_V1",
        "evidence_sections_sha256": result["deterministic_replay"]["evidence_sections_sha256"],
    }
    row_packet = result["row_review_packet"]
    alias_packet = result["alias_steward_packet"]
    assert row_packet["row_ids"] == list(packet.UNSELECTED_ROW_IDS)
    assert row_packet["row_count"] == 6
    assert row_packet["authority_required"] == "INDEPENDENT_ROW_ADJUDICATOR"
    assert alias_packet["candidate_ids"] == [item[0] for item in packet.ALIAS_ROW_BINDINGS]
    assert alias_packet["candidate_count"] == 2
    assert alias_packet["authority_required"] == "REVIEW_INDEPENDENT_SCHEMA_STEWARD"

    response = result["blank_response_contracts"]
    assert response["row_adjudication"]["template"] == packet.ROW_RESPONSE_TEMPLATE
    assert response["alias_stewardship"]["template"] == packet.ALIAS_RESPONSE_TEMPLATE
    assert all(value is None for value in response["row_adjudication"]["template"].values())
    assert all(value is None for value in response["alias_stewardship"]["template"].values())
    assert response["row_adjudication"]["allowed_vocabulary"] == {
        "authority_role": ["INDEPENDENT_ROW_ADJUDICATOR"],
        "decision": [
            "MAP_EXISTING_REPORT_NORM_ID",
            "OUT_OF_SCOPE_FOR_TARGET_TEMPLATE",
            "REQUIRES_SCHEMA_CHANGE",
            "SOURCE_ONLY_STRUCTURAL_ROW",
            "UNRESOLVED",
        ],
    }
    assert response["alias_stewardship"]["allowed_vocabulary"] == {
        "authority_role": ["REVIEW_INDEPENDENT_SCHEMA_STEWARD"],
        "decision": ["APPROVE_ID_SCOPED_ALIAS", "DEFER", "REJECT", "REPLACE"],
    }
    assert (
        response["alias_stewardship"]["decision_constraints"]["REPLACE_downstream_adoption_allowed"]
        is False
    )
    assert result["authority"]["automatic_mapping_adoption"] is False
    assert result["authority"]["schema_alias_approval"] is False
    assert result["authority"]["row_adjudication_completed"] is False
    assert result["authority"]["schema_steward_decision_completed"] is False

    rows = {row["row_id"]: row for row in row_packet["rows"]}
    for row_id, expected in packet._EXPECTED_UNSELECTED_DIAGNOSTICS.items():
        row = rows[row_id]
        interval = row["ordered_interval_universe"]
        expected_interval = packet._EXPECTED_TARGET_INTERVALS[expected["e0038_interval_index"]]
        assert interval["interval"]["row_ids"] == expected_interval["row_ids"]
        assert interval["interval"]["report_norm_ids"] == expected_interval["report_norm_ids"]
        assert [node["report_norm_id"] for node in interval["schema_nodes_in_workbook_order"]] == (
            expected_interval["report_norm_ids"]
        )
        assert [proposal["reader_id"] for proposal in row["sealed_reader_proposals"]] == [
            "deepseek_ocr2",
            "vietocr",
        ]
        assert row["source_visible_label_evidence"]["page_render"]["verification"] == (
            "TRANSITIVELY_HASH_BOUND_NOT_OPENED_BY_E0039"
        )

    assert rows["page-0004-row-000-label"]["alias_hypothesis_dependencies"] == [
        "CDKT_4375_TOTAL_ASSETS_BANKING_WORDING"
    ]
    assert rows["page-0004-row-023-label"]["alias_hypothesis_dependencies"] == [
        "CDKT_5699_NCI_POSSESSIVE_PARTICLE"
    ]
    for row_id in (
        "page-0004-row-000-label",
        "page-0004-row-023-label",
    ):
        previous = rows[row_id]["adjacent_selected_anchors"]["previous"]
        assert previous["alias_hypothesis_dependency"] is not None
        assert previous["authority"] == ("E0038_ALIAS_DEPENDENT_UNAPPROVED_CALIBRATION_HYPOTHESIS")
        assert previous["row_adjudicator_may_approve_schema_alias"] is False

    aliases = {row["candidate_id"]: row for row in alias_packet["rows"]}
    for candidate_id, _row_id, report_norm_id, alias_text in packet.ALIAS_ROW_BINDINGS:
        alias = aliases[candidate_id]
        assert alias["hypothesis"]["report_norm_id"] == report_norm_id
        assert alias["hypothesis"]["alias_text"] == alias_text
        assert alias["score_audit"]["after_target_score"] == "1.0"
        assert alias["collision_audit"]["collision_delta_pair_count"] == 0
        assert alias["collision_audit"]["new_collision_pairs"] == []
        assert alias["unapproved_authority"]["review_or_steward_approved"] is False
        assert alias["unapproved_authority"]["automatic_mapping_adoption"] is False

    access = result["access_contract"]
    forbidden_opened = {
        packet.PAGE_RENDER_0003_RELATIVE_PATH.as_posix(),
        packet.PAGE_RENDER_0004_RELATIVE_PATH.as_posix(),
        "docs/experiments/E-0038-mbb-cdkt-reviewed-evaluation.json",
        "docs/experiments/E-0030-mbb-cdkt-table-metadata.json",
        "docs/experiments/E-0034-mbb-cdkt-numeric-verification-v2.json",
    }
    assert forbidden_opened.isdisjoint(opened_paths)
    assert set(access["opened_input_paths"]) == set(opened_paths)
    assert access["old_human_review_rows_or_answers_extracted"] is False
    assert access["numeric_or_accounting_artifact_opened"] is False
    assert access["qwen_raw_rejected_or_token_output_opened"] is False

    first = {label: opened.index(label) for label in set(opened)}
    assert first["E-0039 e0035_seal"] < first["E-0039 crop_manifest"]
    assert first["E-0039 e0036_baseline_seal"] < first["E-0039 vietocr_result"]
    assert first["E-0039 e0037_mapping_seal"] < first["E-0039 s3_registry"]
    assert first["E-0039 s3_registry"] < first["E-0039 e0037_mapping_only"]
    assert first["E-0039 e0038_mapping_seal"] < first["E-0039 e0038_s3_registration"]
    assert first["E-0039 e0038_s3_registration"] < first["E-0039 e0038_mapping_only"]

    assert set(bindings) == {
        "control",
        *{f"implementation {name}" for name in packet._IMPLEMENTATION_PATHS},
        *{f"input {name}" for name in packet._TRACKED_FROZEN_INPUTS},
    }
    output = root / packet.OUTPUT_RELATIVE_PATH
    assert output.read_bytes() == packet._encoded_packet_json(result)
    assert not output.read_bytes().endswith(b"\n")
    assert len(output.read_bytes()) <= packet._RESOURCE_CAPS["maximum_packet_bytes"]


def test_deepseek_structural_rejections_do_not_leak_raw_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _root, result = _capture_fixture(tmp_path, monkeypatch)
    rows = {row["row_id"]: row for row in result["row_review_packet"]["rows"]}

    for row_id in ("page-0004-row-013-label", "page-0004-row-023-label"):
        proposal = rows[row_id]["sealed_reader_proposals"][0]
        assert proposal == {
            "reader_id": "deepseek_ocr2",
            "reader": "DEEPSEEK_OCR_2",
            "sample_status": "REJECT_DOCUMENT_OR_LAYOUT_SERIALIZATION",
            "proposal_available": False,
            "proposal_text": None,
            "raw_rejected_output_included": False,
        }
        assert "raw_output" not in proposal


def test_capture_invokes_evidence_assembly_exactly_twice(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    _allow_fixture_git(monkeypatch)
    row_calls = 0
    alias_calls = 0
    original_rows = packet._build_unselected_rows
    original_aliases = packet._build_alias_rows

    def count_rows(*args: object, **kwargs: object):
        nonlocal row_calls
        row_calls += 1
        return original_rows(*args, **kwargs)

    def count_aliases(*args: object, **kwargs: object):
        nonlocal alias_calls
        alias_calls += 1
        return original_aliases(*args, **kwargs)

    monkeypatch.setattr(packet, "_build_unselected_rows", count_rows)
    monkeypatch.setattr(packet, "_build_alias_rows", count_aliases)

    result = capture_e0039_review_packet(root)

    assert row_calls == 2
    assert alias_calls == 2
    assert result["deterministic_replay"]["exact_canonical_byte_equality"] is True


def test_capture_never_invokes_mapping_or_opens_forbidden_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    _allow_fixture_git(monkeypatch)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("mapping/review execution is forbidden")

    monkeypatch.setattr(
        "bctc_ai.mapping.ordered_subgraph_v2.align_ordered_subgraph_v2",
        forbidden,
    )
    monkeypatch.setattr(
        "bctc_ai.mapping.e0038_exact_search.run_e0038_exact_search",
        forbidden,
    )
    opened_paths: list[str] = []

    def guarding_reader(
        project_root: Path,
        path: Path,
        label: str,
        **kwargs: object,
    ):
        lowered = path.as_posix().casefold()
        opened_paths.append(path.relative_to(project_root).as_posix())
        forbidden_fragments = (
            "e-0030",
            "e-0033",
            "e-0034",
            "postjoin",
            "numeric",
            "history",
            "mongodb",
            "duckdb",
            "qwen",
            "holdout",
            "/acb/",
            "human-review",
            "human_review",
            "review-registry",
            "review_registry",
            "reviewed-evaluation.json",
            "reviewed_evaluation.json",
        )
        assert all(fragment not in lowered for fragment in forbidden_fragments)
        assert path not in {
            project_root / packet.PAGE_RENDER_0003_RELATIVE_PATH,
            project_root / packet.PAGE_RENDER_0004_RELATIVE_PATH,
        }
        return packet._read_stable_file(project_root, path, label, **kwargs)

    result = capture_e0039_review_packet(root, _reader=guarding_reader)

    assert result["access_contract"]["mapping_rerun_invocation_count"] == 0
    assert result["access_contract"]["adjudication_or_steward_decision_invocation_count"] == 0
    expected_crops = {
        packet._FROZEN_PATHS[name].as_posix() for name in packet._TARGET_CROP_INPUT_NAMES
    }
    opened_crop_paths = {path for path in opened_paths if path.casefold().endswith(".png")}
    assert opened_crop_paths == expected_crops
    assert len(opened_crop_paths) == 8


def test_capture_refuses_to_overwrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    _allow_fixture_git(monkeypatch)
    destination = root / packet.OUTPUT_RELATIVE_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("existing\n", encoding="utf-8")

    with pytest.raises(E0039ReviewPacketError, match="refusing to overwrite"):
        capture_e0039_review_packet(root)
    assert destination.read_text(encoding="utf-8") == "existing\n"


def test_capture_rejects_symlinked_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    _allow_fixture_git(monkeypatch)
    destination = root / packet.OUTPUT_RELATIVE_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.symlink_to(root / "missing.json")

    with pytest.raises(E0039ReviewPacketError, match="symlink"):
        capture_e0039_review_packet(root)
    assert destination.is_symlink()


def test_local_publisher_rolls_back_if_parent_is_renamed_after_link(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "out/evidence_packet.json"
    original_link = packet.os.link

    def racing_link(*args: object, **kwargs: object) -> None:
        original_link(*args, **kwargs)
        (tmp_path / "out").rename(tmp_path / "detached")
        (tmp_path / "out").mkdir()

    monkeypatch.setattr(packet.os, "link", racing_link)
    with pytest.raises(E0039ReviewPacketError, match="publish"):
        packet._exclusive_publish_compact_json(
            tmp_path,
            target,
            {"fixture": True},
            exclusive_parent_inventory=("evidence_packet.json",),
        )

    assert not target.exists()
    assert not (tmp_path / "detached/evidence_packet.json").exists()


def test_capture_requires_clean_git_before_any_evidence_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    read_called = False

    def dirty_git(_root: Path) -> str:
        raise packet.E0038ExactMappingError("dirty or untracked worktree")

    def forbidden_reader(*_args: object, **_kwargs: object):
        nonlocal read_called
        read_called = True
        raise AssertionError("evidence must not be read before the clean-Git gate")

    monkeypatch.setattr(packet, "_clean_git_commit", dirty_git)
    with pytest.raises(E0039ReviewPacketError, match="dirty or untracked"):
        capture_e0039_review_packet(root, _reader=forbidden_reader)

    assert read_called is False
    assert not (root / packet.OUTPUT_RELATIVE_PATH).exists()


def test_capture_fails_before_publication_on_head_binding_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    monkeypatch.setattr(packet, "_clean_git_commit", lambda _root: HEAD)

    def reject_binding(*_args: object, **kwargs: object) -> None:
        raise E0039ReviewPacketError(f"simulated HEAD mismatch: {kwargs['name']}")

    monkeypatch.setattr(packet, "_head_bind", reject_binding)
    with pytest.raises(E0039ReviewPacketError, match="HEAD mismatch"):
        capture_e0039_review_packet(root)

    assert not (root / packet.OUTPUT_RELATIVE_PATH).exists()


def test_capture_rejects_noncanonical_paths(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)

    with pytest.raises(E0039ReviewPacketError, match="canonical"):
        capture_e0039_review_packet(root, config_path=root / packet.CONTROL_RELATIVE_PATH)
    with pytest.raises(E0039ReviewPacketError, match="canonical"):
        capture_e0039_review_packet(root, output_path=Path("output/wrong.json"))


def test_capture_fails_closed_when_input_changes_before_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    _allow_fixture_git(monkeypatch)
    original = packet._assert_unchanged

    def fail_recheck(reader: object, project_root: Path, stable: object, label: str) -> None:
        if label.endswith("e0038_mapping_only"):
            raise packet.E0038ExactMappingError("simulated race")
        original(reader, project_root, stable, label)

    monkeypatch.setattr(packet, "_assert_unchanged", fail_recheck)

    with pytest.raises(E0039ReviewPacketError, match="input changed before publication"):
        capture_e0039_review_packet(root)
    assert not (root / packet.OUTPUT_RELATIVE_PATH).exists()


def test_strict_json_rejects_whitespace_duplicate_and_nonfinite_drift() -> None:
    def stable(payload: bytes):
        return packet._StableFile(
            path=Path("fixture.json"),
            payload=payload,
            identity=(0, 0, 0, len(payload), 0, 0),
            artifact={
                "path": "fixture.json",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            },
        )

    assert packet._strict_json(stable(b'{"a":1}'), "fixture") == {"a": 1}
    assert packet._strict_json(stable(b'{\n  "a": 1\n}\n'), "fixture") == {"a": 1}
    for payload in (b'{ "a": 1 }', b'{"a":1,"a":2}', b'{"a":NaN}'):
        with pytest.raises(E0039ReviewPacketError, match="cannot decode"):
            packet._strict_json(stable(payload), "fixture")


@pytest.mark.parametrize(
    "mutation",
    [
        "truncate_interval_nodes",
        "reorder_interval_schema",
        "remove_alias_dependency",
        "inject_suggested_answer",
        "mutate_visible_label",
        "mutate_reader_proposal",
        "mutate_schema_display_name",
        "mutate_row_crop_hash",
        "mutate_alias_score",
        "mutate_collision_count",
        "mutate_unapproved_authority",
        "fill_row_response",
        "flip_row_authority_constraint",
        "flip_replace_adoption_constraint",
        "approve_alias_in_evidence",
        "open_old_human_review",
        "open_history",
        "mutate_input_crop_hash",
        "mutate_input_mapping_hash",
        "mutate_evidence_crop_hash",
        "mutate_s3_snapshot_id",
        "mutate_evidence_mapping_hash",
        "mutate_render_verification",
        "mutate_workbook_hash",
        "mutate_control_identity",
        "mutate_implementation_identity",
        "mutate_capture_commit",
    ],
)
def test_packet_self_validator_rejects_evidence_or_response_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    _root, result = _capture_fixture(tmp_path, monkeypatch)
    drifted = copy.deepcopy(result)
    row = drifted["row_review_packet"]["rows"][0]
    if mutation == "truncate_interval_nodes":
        row["ordered_interval_universe"]["schema_nodes_in_workbook_order"].pop()
    elif mutation == "reorder_interval_schema":
        row["ordered_interval_universe"]["schema_nodes_in_workbook_order"].reverse()
    elif mutation == "remove_alias_dependency":
        drifted["row_review_packet"]["rows"][2]["alias_hypothesis_dependencies"] = []
    elif mutation == "inject_suggested_answer":
        row["current_mapping_diagnostics"]["suggested_answer"] = 4311
    elif mutation == "mutate_visible_label":
        row["source_visible_label_evidence"]["raw_visible_ppocr_label"] = "forged"
    elif mutation == "mutate_reader_proposal":
        row["sealed_reader_proposals"][0]["proposal_text"] = "forged"
    elif mutation == "mutate_schema_display_name":
        row["ordered_interval_universe"]["schema_nodes_in_workbook_order"][0]["display_name"] = (
            "forged"
        )
    elif mutation == "mutate_row_crop_hash":
        row["source_visible_label_evidence"]["source_crop"]["sha256"] = "0" * 64
    elif mutation == "mutate_alias_score":
        drifted["alias_steward_packet"]["rows"][0]["score_audit"]["after_target_score"] = "0.0"
    elif mutation == "mutate_collision_count":
        drifted["alias_steward_packet"]["rows"][0]["collision_audit"][
            "collision_delta_pair_count"
        ] = 1
    elif mutation == "mutate_unapproved_authority":
        drifted["alias_steward_packet"]["rows"][0]["unapproved_authority"][
            "numeric_period_or_value_features_allowed"
        ] = True
    elif mutation == "fill_row_response":
        drifted["blank_response_contracts"]["row_adjudication"]["template"]["decision"] = (
            "UNRESOLVED"
        )
    elif mutation == "flip_row_authority_constraint":
        drifted["blank_response_contracts"]["row_adjudication"]["decision_constraints"][
            "row_adjudicator_may_not_approve_schema_alias"
        ] = False
    elif mutation == "flip_replace_adoption_constraint":
        drifted["blank_response_contracts"]["alias_stewardship"]["decision_constraints"][
            "REPLACE_downstream_adoption_allowed"
        ] = True
    elif mutation == "approve_alias_in_evidence":
        drifted["alias_steward_packet"]["rows"][0]["unapproved_authority"][
            "review_or_steward_approved"
        ] = True
    elif mutation == "open_old_human_review":
        drifted["access_contract"]["old_human_review_rows_or_answers_extracted"] = True
    elif mutation == "open_history":
        drifted["access_contract"]["history_or_mongodb_artifact_opened"] = True
    elif mutation == "mutate_input_crop_hash":
        drifted["input_artifacts"]["crop_page_0003_row_002"]["sha256"] = "0" * 64
    elif mutation == "mutate_input_mapping_hash":
        drifted["input_artifacts"]["e0038_mapping_only"]["sha256"] = "0" * 64
    elif mutation == "mutate_evidence_crop_hash":
        drifted["evidence_identity"]["source_pixel_evidence"]["target_source_crops"][0][
            "sha256"
        ] = "0" * 64
    elif mutation == "mutate_s3_snapshot_id":
        drifted["evidence_identity"]["mapping_chain"]["e0037_s3_snapshot"][
            "artifact_snapshot_id"
        ] = "forged"
    elif mutation == "mutate_evidence_mapping_hash":
        drifted["evidence_identity"]["mapping_chain"]["e0038_mapping_only"]["sha256"] = "0" * 64
    elif mutation == "mutate_render_verification":
        drifted["evidence_identity"]["source_pixel_evidence"]["page_renders"][0]["verification"] = (
            "OPENED_NUMERIC_PAGE"
        )
    elif mutation == "mutate_workbook_hash":
        drifted["evidence_identity"]["workbook_and_projections"]["workbook"]["sha256"] = "0" * 64
    elif mutation == "mutate_control_identity":
        drifted["identity"]["control"]["sha256"] = "0" * 64
    elif mutation == "mutate_implementation_identity":
        drifted["identity"]["implementation"]["packet_builder"]["sha256"] = "0" * 64
    elif mutation == "mutate_capture_commit":
        drifted["identity"]["capture_git_commit"] = "b" * 40

    drifted["deterministic_replay"]["evidence_sections_sha256"] = packet._canonical_sha256(
        {
            "row_review_rows": drifted["row_review_packet"]["rows"],
            "alias_steward_rows": drifted["alias_steward_packet"]["rows"],
        }
    )

    with pytest.raises(E0039ReviewPacketError):
        packet._validate_packet_payload(
            drifted,
            expected_control_artifact=result["identity"]["control"],
            expected_implementation_artifacts=result["identity"]["implementation"],
            expected_git_commit=result["identity"]["capture_git_commit"],
        )


def test_canonical_control_pins_every_direct_input_and_implementation() -> None:
    control = yaml.safe_load((REPOSITORY_ROOT / packet.CONTROL_RELATIVE_PATH).read_text())

    assert control["frozen_inputs"] == packet._EXPECTED_FROZEN_INPUTS
    assert set(control["frozen_inputs"]) == set(packet._FROZEN_PATHS)
    assert "e0038_reviewed_coverage" not in control["frozen_inputs"]
    assert "page_render_0003" not in control["frozen_inputs"]
    assert "page_render_0004" not in control["frozen_inputs"]
    assert all(
        "e0038_reviewed_evaluation" not in relative.as_posix()
        for relative in packet._IMPLEMENTATION_PATHS.values()
    )
    for name, relative in packet._IMPLEMENTATION_PATHS.items():
        payload = (REPOSITORY_ROOT / relative).read_bytes()
        assert control["implementation"][name] == {
            "path": relative.as_posix(),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }
    assert control["packet_contract"] == packet._PACKET_CONTRACT
    assert control["access_contract"] == packet._ACCESS_CONTRACT
    assert control["resource_caps"] == packet._RESOURCE_CAPS
    assert control["publication"] == packet._PUBLICATION_CONTRACT
    assert control["output"] == {"path": packet.OUTPUT_RELATIVE_PATH.as_posix()}


def test_fresh_import_never_materializes_e0038_review_answer_module() -> None:
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import importlib,sys;"
                "module=importlib.import_module('bctc_ai.evaluation.e0039_review_packet');"
                "assert 'bctc_ai.evaluation.e0038_reviewed_evaluation' not in sys.modules;"
                "assert all('e0038_reviewed_evaluation' not in p.as_posix() "
                "for p in module._IMPLEMENTATION_PATHS.values())"
            ),
        ],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert probe.returncode == 0, probe.stderr
