from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest
import yaml

from bctc_ai.evaluation import e0038_reviewed_evaluation as reviewed
from bctc_ai.evaluation.e0038_reviewed_evaluation import (
    E0038ReviewedEvaluationError,
    capture_e0038_reviewed_evaluation,
    evaluate_fixed_reviewed_mapping,
    extract_fixed_reviewed_identities,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
HEAD = "a" * 40
FIXTURE_FILES = (
    reviewed.CONTROL_RELATIVE_PATH,
    reviewed.MAPPING_ONLY_RELATIVE_PATH,
    reviewed.MAPPING_SEAL_RELATIVE_PATH,
    reviewed.S3_REGISTRATION_RELATIVE_PATH,
    reviewed.MAPPING_CONTROL_RELATIVE_PATH,
    reviewed.E0037_MAPPING_ONLY_RELATIVE_PATH,
    reviewed.PRIOR_REVIEW_RELATIVE_PATH,
    reviewed.EVALUATOR_RELATIVE_PATH,
    reviewed.CAPTURE_SCRIPT_RELATIVE_PATH,
)


def _copy_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    for relative in FIXTURE_FILES:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPOSITORY_ROOT / relative, destination)
    return root


def _load(root: Path, relative: Path) -> dict[str, object]:
    payload = json.loads((root / relative).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _allow_fixture_git(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    head_bindings: list[str] = []
    monkeypatch.setattr(reviewed, "_clean_git_commit", lambda _root: HEAD)

    def record_head_binding(
        _root: Path,
        _record: object,
        *,
        name: str,
        expected_path: Path,
        reader: object,
    ) -> None:
        del expected_path, reader
        head_bindings.append(name)

    monkeypatch.setattr(reviewed, "_head_bind", record_head_binding)
    return head_bindings


def test_capture_validates_seal_s3_mapping_and_e0037_before_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    head_bindings = _allow_fixture_git(monkeypatch)
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
        return reviewed._read_stable_file(project_root, path, label, **kwargs)

    result = capture_e0038_reviewed_evaluation(root, _reader=tracking_reader)

    first = {label: opened.index(label) for label in set(opened)}
    assert first["E-0038 mapping seal"] < first["E-0038 post-seal S3 registration"]
    assert first["E-0038 post-seal S3 registration"] < first["E-0038 mapping control"]
    assert first["E-0038 mapping control"] < first["E-0038 mapping-only bytes"]
    assert first["E-0038 mapping-only bytes"] < first["E-0037 diagnostic mapping-only bytes"]
    assert (
        first["E-0037 diagnostic mapping-only bytes"]
        < first["pre-existing E-0036 reviewed evaluation"]
    )
    assert result["state"] == reviewed.COMPLETE_STATE
    assert result["mechanism_calibration_gate"] == ("PASS_FIXED_SIX_AUTOMATIC_SELECTION_EXACT")
    evaluation = result["reviewed_mapping_evaluation"]
    assert evaluation["exact_report_norm_id_count"] == 6
    assert evaluation["automatically_selected_exact_count"] == 6
    assert evaluation["wrong_report_norm_id_count"] == 0
    assert evaluation["abstention_count"] == 0
    assert evaluation["row_mapping_status_counts"] == {
        "RESOLVED_ANCHOR": 5,
        "RESOLVED_PATH": 1,
    }
    assert evaluation["coverage_limits"] == {
        "all_mapping_source_row_count": 64,
        "source_row_reviewed_count": 6,
        "source_row_reviewed_rate": 0.09375,
        "all_mapping_selected_row_count": 58,
        "selected_row_reviewed_count": 6,
        "selected_row_reviewed_rate": 0.10344827586206896,
        "changed_alias_target_total_count": 2,
        "changed_alias_target_reviewed_count": 0,
        "changed_alias_target_reviewed_rate": 0.0,
        "all_mapping_unselected_row_count": 6,
        "unselected_row_reviewed_count": 0,
        "unselected_row_reviewed_rate": 0.0,
        "schema_alias_hypotheses_reviewed": False,
        "unselected_row_mechanism_reviewed": False,
    }
    parity = result["pre_review_validation"]["e0037_e0038_selected_pair_parity"]
    assert parity["selected_pairs_identical"] is True
    assert parity["same_selected_pair_count"] == 58
    assert parity["selected_pair_projection_sha256"] == (
        "8135658100d83772812aeecff4beb4378ad7163c96a286a3770d430027a87df3"
    )
    formal = result["pre_review_validation"]["formal_result_summary"]
    expected_formal = _load(root, reviewed.S3_REGISTRATION_RELATIVE_PATH)["formal_result_summary"]
    assert formal == expected_formal
    assert formal["align_invocation_count"] == 1
    assert formal["exact_status"] == "EXACT_SEARCH_COMPLETE"
    assert formal["schema_node_count"] == 77
    assert formal["sealed_e0037_interval_count"] == 40
    assert result["conclusion"]["automatic_mapping_adoption"] is False
    assert result["conclusion"]["schema_alias_approval"] is False
    assert result["conclusion"]["production"] is False
    assert result["authority"]["numeric_period_or_unit"] is False
    assert result["authority"]["history_or_mongodb"] is False
    access = result["review_access_order"]
    assert access["review_interface_contains_numeric_fields"] is True
    assert access["numeric_fields_extracted_or_used"] is False
    assert access["separate_numeric_artifact_opened"] is False
    assert access["qwen_raw_or_rejected_output_opened"] is False
    assert access["e0030_artifact_opened"] is False
    assert access["e0033_artifact_opened"] is False
    assert access["e0034_artifact_opened"] is False
    assert access["history_or_mongodb_artifact_loaded"] is False
    assert set(opened_paths) == set(access["opened_input_paths"])
    comparison = result["prior_comparison"]
    assert comparison["e0036_baseline_readers"]["vietocr"] == {
        "reader": "VIETOCR_VGG_TRANSFORMER",
        "label_exact_count": 3,
        "label_row_count": 6,
        "mapping_status": "AMBIGUOUS_MAPPING",
        "score_margin": 0.051282,
        "reviewed_best_path_exact_count": 6,
        "reviewed_automatically_selected_exact_count": 0,
        "reviewed_abstention_count": 6,
    }
    assert comparison["e0036_baseline_readers"]["deepseek_ocr2"] == {
        "reader": "DEEPSEEK_OCR_2",
        "label_exact_count": 1,
        "label_row_count": 6,
        "mapping_status": "AMBIGUOUS_MAPPING",
        "score_margin": 0.008494,
        "reviewed_best_path_exact_count": 6,
        "reviewed_automatically_selected_exact_count": 0,
        "reviewed_abstention_count": 6,
    }
    assert comparison["e0037_diagnostic_best_path"]["mapping_status"] == ("AMBIGUOUS_MAPPING")
    assert comparison["e0037_diagnostic_best_path"]["reviewed_best_path_exact_count"] == 6
    assert comparison["e0037_diagnostic_best_path"]["reviewed_abstention_count"] == 6
    assert all(
        value is False
        for key, value in result["conclusion"].items()
        if key in {"automatic_mapping_adoption", "schema_alias_approval", "production"}
    )
    assert all(
        value is False
        for key, value in result["authority"].items()
        if key
        in {
            "mapping_accuracy_beyond_fixed_six",
            "schema_authority",
            "schema_alias_approval",
            "automatic_mapping_adoption",
            "numeric_period_or_unit",
            "accounting_or_excel",
            "history_or_mongodb",
            "holdout_or_production",
        }
    )
    assert "mapping_only" not in head_bindings
    assert "e0037_mapping_only" not in head_bindings
    assert set(head_bindings) == {
        "control",
        "evaluator",
        "capture_script",
        "mapping_seal",
        "postseal_s3_registration",
        "mapping_control",
        "prior_reviewed_evaluation",
    }
    assert (root / reviewed.OUTPUT_RELATIVE_PATH).is_file()


def test_capture_never_invokes_mapping_again(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    _allow_fixture_git(monkeypatch)

    def forbidden_mapping(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("mapping rerun is forbidden")

    monkeypatch.setattr(
        "bctc_ai.mapping.ordered_subgraph_v2.align_ordered_subgraph_v2",
        forbidden_mapping,
    )
    monkeypatch.setattr(
        "bctc_ai.mapping.e0038_exact_search.run_e0038_exact_search",
        forbidden_mapping,
    )

    result = capture_e0038_reviewed_evaluation(root)

    assert result["pre_review_validation"]["mapping_rerun_invocation_count"] == 0
    assert result["pre_review_validation"]["mapping_mutation_count"] == 0


def test_capture_rejects_registration_drift_before_opening_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    _allow_fixture_git(monkeypatch)
    registration = root / reviewed.S3_REGISTRATION_RELATIVE_PATH
    registration.write_bytes(registration.read_bytes() + b"\n")
    opened: list[str] = []

    def tracking_reader(
        project_root: Path,
        path: Path,
        label: str,
        **kwargs: object,
    ):
        opened.append(label)
        return reviewed._read_stable_file(project_root, path, label, **kwargs)

    with pytest.raises(E0038ReviewedEvaluationError, match="post-seal S3 registration"):
        capture_e0038_reviewed_evaluation(root, _reader=tracking_reader)
    assert "pre-existing E-0036 reviewed evaluation" not in opened
    assert not (root / reviewed.OUTPUT_RELATIVE_PATH).exists()


def test_capture_refuses_to_overwrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    _allow_fixture_git(monkeypatch)
    destination = root / reviewed.OUTPUT_RELATIVE_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("existing\n", encoding="utf-8")

    with pytest.raises(E0038ReviewedEvaluationError, match="refusing to overwrite"):
        capture_e0038_reviewed_evaluation(root)
    assert destination.read_text(encoding="utf-8") == "existing\n"


def test_capture_rejects_symlinked_canonical_control(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    _allow_fixture_git(monkeypatch)
    control = root / reviewed.CONTROL_RELATIVE_PATH
    moved = root / "moved-review-control.yaml"
    control.replace(moved)
    control.symlink_to(moved)

    with pytest.raises(E0038ReviewedEvaluationError, match="symlink"):
        capture_e0038_reviewed_evaluation(root)


def test_capture_rejects_symlinked_canonical_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    _allow_fixture_git(monkeypatch)
    destination = root / reviewed.OUTPUT_RELATIVE_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.symlink_to(root / "missing-output-target.json")

    with pytest.raises(E0038ReviewedEvaluationError, match="path contains a symlink"):
        capture_e0038_reviewed_evaluation(root)
    assert destination.is_symlink()


def test_capture_rejects_noncanonical_config_and_output_paths(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)

    with pytest.raises(E0038ReviewedEvaluationError, match="canonical"):
        capture_e0038_reviewed_evaluation(
            root,
            config_path=root / reviewed.CONTROL_RELATIVE_PATH,
        )
    with pytest.raises(E0038ReviewedEvaluationError, match="canonical"):
        capture_e0038_reviewed_evaluation(
            root,
            output_path=Path("docs/experiments/not-canonical.json"),
        )


def test_capture_rejects_git_drift_before_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    commits = iter((HEAD, "b" * 40))
    monkeypatch.setattr(reviewed, "_clean_git_commit", lambda _root: next(commits))
    monkeypatch.setattr(reviewed, "_head_bind", lambda *_args, **_kwargs: None)

    with pytest.raises(E0038ReviewedEvaluationError, match="Git commit changed"):
        capture_e0038_reviewed_evaluation(root)
    assert not (root / reviewed.OUTPUT_RELATIVE_PATH).exists()


def test_capture_rejects_dirty_git_before_any_authority_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)

    def reject_dirty(_root: Path) -> str:
        raise reviewed.E0038ExactMappingError("publication requires a clean Git worktree")

    monkeypatch.setattr(reviewed, "_clean_git_commit", reject_dirty)

    with pytest.raises(E0038ReviewedEvaluationError, match="clean Git worktree"):
        capture_e0038_reviewed_evaluation(root)
    assert not (root / reviewed.OUTPUT_RELATIVE_PATH).exists()


def test_capture_fails_closed_on_head_binding_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    monkeypatch.setattr(reviewed, "_clean_git_commit", lambda _root: HEAD)

    def fail_head_binding(*_args: object, **_kwargs: object) -> None:
        raise E0038ReviewedEvaluationError("HEAD binding failed")

    monkeypatch.setattr(reviewed, "_head_bind", fail_head_binding)

    with pytest.raises(E0038ReviewedEvaluationError, match="HEAD binding failed"):
        capture_e0038_reviewed_evaluation(root)
    assert not (root / reviewed.OUTPUT_RELATIVE_PATH).exists()


def test_capture_fails_closed_when_input_changes_before_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    _allow_fixture_git(monkeypatch)
    original = reviewed._assert_unchanged

    def fail_mapping_recheck(
        reader: object,
        project_root: Path,
        stable: object,
        label: str,
    ) -> None:
        if label.endswith("mapping_only"):
            raise reviewed.E0038ExactMappingError("simulated mapping race")
        original(reader, project_root, stable, label)

    monkeypatch.setattr(reviewed, "_assert_unchanged", fail_mapping_recheck)

    with pytest.raises(E0038ReviewedEvaluationError, match="input changed: mapping_only"):
        capture_e0038_reviewed_evaluation(root)
    assert not (root / reviewed.OUTPUT_RELATIVE_PATH).exists()


def test_capture_exclusive_publication_loses_race_without_overwrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    _allow_fixture_git(monkeypatch)
    destination = root / reviewed.OUTPUT_RELATIVE_PATH
    original = reviewed._exclusive_publish_json

    def lose_publication_race(
        project_root: Path,
        path: Path,
        payload: object,
    ) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("competitor\n", encoding="utf-8")
        return original(project_root, path, payload)

    monkeypatch.setattr(reviewed, "_exclusive_publish_json", lose_publication_race)

    with pytest.raises(E0038ReviewedEvaluationError, match="refusing to overwrite"):
        capture_e0038_reviewed_evaluation(root)
    assert destination.read_text(encoding="utf-8") == "competitor\n"


def test_e0037_e0038_projection_comparison_rejects_pair_drift() -> None:
    e0037 = _load(REPOSITORY_ROOT, reviewed.E0037_MAPPING_ONLY_RELATIVE_PATH)
    e0038 = _load(REPOSITORY_ROOT, reviewed.MAPPING_ONLY_RELATIVE_PATH)
    mutated = copy.deepcopy(e0037)
    mutated["mapping"]["best_path"]["matches"][0]["report_norm_id"] = 999_999

    with pytest.raises(E0038ReviewedEvaluationError, match="pair parity"):
        reviewed._validate_e0037_comparison(mutated, e0038)


def test_review_extraction_preserves_full_physical_binding_and_rejects_drift() -> None:
    review = _load(REPOSITORY_ROOT, reviewed.PRIOR_REVIEW_RELATIVE_PATH)
    rows = extract_fixed_reviewed_identities(review)

    assert rows[0] == {
        "sample_id": "page-0003-row-018-label",
        "reviewed_report_norm_id": 4317,
        "visible_row_id": "mbb-p3-4317",
        "page": 3,
        "row_ordinal": 18,
    }
    assert [
        (
            row["sample_id"],
            row["reviewed_report_norm_id"],
            row["visible_row_id"],
            row["page"],
            row["row_ordinal"],
        )
        for row in rows
    ] == list(reviewed._FIXED_REVIEWED_IDENTITIES)

    mutated = copy.deepcopy(review)
    mutated["human_review"]["row_bindings"][0]["visible_row_id"] = "wrong"
    with pytest.raises(E0038ReviewedEvaluationError, match="fixed six"):
        extract_fixed_reviewed_identities(mutated)


def test_review_extractor_never_accesses_embedded_numeric_fields() -> None:
    class NumericAccessGuard(dict[str, object]):
        def get(self, key: str, default: object = None) -> object:
            if "numeric" in key or key.startswith("e0034_"):
                raise AssertionError(f"numeric field accessed: {key}")
            return super().get(key, default)

        def __getitem__(self, key: str) -> object:
            if "numeric" in key or key.startswith("e0034_"):
                raise AssertionError(f"numeric field accessed: {key}")
            return super().__getitem__(key)

    review = _load(REPOSITORY_ROOT, reviewed.PRIOR_REVIEW_RELATIVE_PATH)
    review["human_review"]["row_bindings"] = [
        NumericAccessGuard(binding) for binding in review["human_review"]["row_bindings"]
    ]

    rows = extract_fixed_reviewed_identities(review)

    assert len(rows) == 6
    assert set(rows[0]) == {
        "sample_id",
        "reviewed_report_norm_id",
        "visible_row_id",
        "page",
        "row_ordinal",
    }


def test_fixed_six_evaluation_rejects_wrong_selected_id() -> None:
    mapping = _load(REPOSITORY_ROOT, reviewed.MAPPING_ONLY_RELATIVE_PATH)
    review = _load(REPOSITORY_ROOT, reviewed.PRIOR_REVIEW_RELATIVE_PATH)
    rows = extract_fixed_reviewed_identities(review)
    mutated = copy.deepcopy(mapping)
    mappings = mutated["exact_mapping_bundle"]["exact_search"][
        "mapping_result_without_internal_alias_authority"
    ]["row_mappings"]
    target = next(item for item in mappings if item["row_id"] == rows[0]["sample_id"])
    target["selected_report_norm_id"] = 4316

    with pytest.raises(E0038ReviewedEvaluationError, match="pinned fixed-six"):
        evaluate_fixed_reviewed_mapping(mutated, rows)


def test_registration_validator_rejects_failed_restore() -> None:
    seal = _load(REPOSITORY_ROOT, reviewed.MAPPING_SEAL_RELATIVE_PATH)
    registration = _load(REPOSITORY_ROOT, reviewed.S3_REGISTRATION_RELATIVE_PATH)
    mutated = copy.deepcopy(registration)
    mutated["s3_snapshot"]["isolated_hydrate"]["status"] = "FAIL"

    with pytest.raises(E0038ReviewedEvaluationError, match="incomplete or drifted"):
        reviewed._validate_postseal_registration(mutated, seal)


@pytest.mark.parametrize(
    "key",
    [
        "e0030_opened",
        "e0033_opened",
        "e0034_opened",
        "history_opened",
        "qwen_raw_or_rejected_output_opened",
        "review_opened",
    ],
)
def test_mapping_seal_validator_rejects_forbidden_access(key: str) -> None:
    seal = _load(REPOSITORY_ROOT, reviewed.MAPPING_SEAL_RELATIVE_PATH)
    seal["access_contract"][key] = True

    with pytest.raises(E0038ReviewedEvaluationError, match="seal linkage drifted"):
        reviewed._validate_mapping_seal(seal)


@pytest.mark.parametrize(
    "key",
    [
        "e0030_opened",
        "e0033_opened",
        "e0034_opened",
        "qwen_result_or_rejected_raw_output_opened",
        "review_or_history_opened",
    ],
)
def test_e0037_validator_rejects_forbidden_access(key: str) -> None:
    e0037 = _load(REPOSITORY_ROOT, reviewed.E0037_MAPPING_ONLY_RELATIVE_PATH)
    e0038 = _load(REPOSITORY_ROOT, reviewed.MAPPING_ONLY_RELATIVE_PATH)
    e0037["access_contract"][key] = True

    with pytest.raises(E0038ReviewedEvaluationError, match="identity drifted"):
        reviewed._validate_e0037_comparison(e0037, e0038)


def test_registration_validator_rejects_formal_summary_keyset_drift() -> None:
    seal = _load(REPOSITORY_ROOT, reviewed.MAPPING_SEAL_RELATIVE_PATH)
    registration = _load(REPOSITORY_ROOT, reviewed.S3_REGISTRATION_RELATIVE_PATH)
    del registration["formal_result_summary"]["align_invocation_count"]

    with pytest.raises(E0038ReviewedEvaluationError, match="formal result summary keyset"):
        reviewed._validate_postseal_registration(registration, seal)


@pytest.mark.parametrize(
    ("key", "drifted"),
    [
        ("align_invocation_count", 2),
        ("exact_status", "ABSTAINED"),
        ("schema_node_count", 76),
        ("sealed_e0037_interval_count", 39),
    ],
)
def test_registration_validator_rejects_missing_formal_metric_values(
    key: str,
    drifted: object,
) -> None:
    seal = _load(REPOSITORY_ROOT, reviewed.MAPPING_SEAL_RELATIVE_PATH)
    registration = _load(REPOSITORY_ROOT, reviewed.S3_REGISTRATION_RELATIVE_PATH)
    registration["formal_result_summary"][key] = drifted

    with pytest.raises(E0038ReviewedEvaluationError, match="incomplete or drifted"):
        reviewed._validate_postseal_registration(registration, seal)


def test_canonical_control_pins_real_inputs_and_implementation() -> None:
    control = yaml.safe_load((REPOSITORY_ROOT / reviewed.CONTROL_RELATIVE_PATH).read_text())
    expected_frozen = {
        "mapping_only": reviewed.MAPPING_ONLY_ARTIFACT,
        "mapping_seal": reviewed.MAPPING_SEAL_ARTIFACT,
        "postseal_s3_registration": reviewed.S3_REGISTRATION_ARTIFACT,
        "mapping_control": reviewed.MAPPING_CONTROL_ARTIFACT,
        "e0037_mapping_only": reviewed.E0037_MAPPING_ONLY_ARTIFACT,
        "prior_reviewed_evaluation": reviewed.PRIOR_REVIEW_ARTIFACT,
    }
    assert control["frozen_inputs"] == expected_frozen
    for key, relative in (
        ("evaluator", reviewed.EVALUATOR_RELATIVE_PATH),
        ("capture_script", reviewed.CAPTURE_SCRIPT_RELATIVE_PATH),
    ):
        payload = (REPOSITORY_ROOT / relative).read_bytes()
        assert control["implementation"][key] == {
            "path": relative.as_posix(),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }
    assert control["review_contract"] == reviewed._REVIEW_CONTRACT
    assert control["output"] == {"path": reviewed.OUTPUT_RELATIVE_PATH.as_posix()}
