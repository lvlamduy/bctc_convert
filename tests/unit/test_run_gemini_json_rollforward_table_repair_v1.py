from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sqlite3
import sys
import time
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import fitz
import pytest
from test_gemini_json_rollforward_table_repair_v1 import _response

from bctc_ai.evaluation.gemini_json_first_provider_v1 import ProviderResultV1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.storage import gemini_accounting_family_store_v1 as family_store_subject
from bctc_ai.storage.gemini_accounting_family_store_v1 import (
    initialize_gemini_accounting_family_store_v1,
    resolved_gemini_family_region_repair_overlay_v1,
)
from bctc_ai.storage.gemini_family_effective_page_frontier_v1 import (
    apply_gemini_family_effective_page_frontier_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (
    page_json_region_repair_lineages_v1,
)

pytest_plugins = ("test_gemini_json_rollforward_table_repair_v1",)

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "scripts/experiments/run_gemini_json_rollforward_table_repair_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "run_gemini_json_rollforward_table_repair_v1",
    _SCRIPT,
)
assert _SPEC is not None and _SPEC.loader is not None
target = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = target
_SPEC.loader.exec_module(target)


def _write_json(path: Path, value: object) -> str:
    payload = canonical_json_bytes_v1(value) + b"\n"
    path.write_bytes(payload)
    return sha256(payload).hexdigest()


def _family_results_store(
    path: Path,
    *,
    corpus: dict,
    sweep: dict,
    family_run_id: str,
) -> None:
    initialize_gemini_accounting_family_store_v1(path)
    sweep_bytes = canonical_json_bytes_v1(sweep) + b"\n"
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            "INSERT INTO family_run VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                family_run_id,
                sweep["sweep_id"],
                sweep["family_id"],
                "GEMINI_JSON_FLAT_ACCOUNTING_FAMILY_SWEEP_V1",
                sweep["corpus_manifest_index_id"],
                "1" * 64,
                "2" * 64,
                "3" * 64,
                "4" * 64,
                "5" * 64,
                b"[]",
                sha256(sweep_bytes).hexdigest(),
                sweep_bytes,
                len(corpus["plans"]),
                0,
                0,
                len(corpus["plans"]),
                0,
            ),
        )
        for plan in corpus["plans"]:
            trial = {
                "document_ordinal": plan["document_ordinal"],
                "status": "UNRESOLVED_GEMINI_JSON_FAMILY",
            }
            trial_bytes = canonical_json_bytes_v1(trial) + b"\n"
            connection.execute(
                "INSERT INTO family_trial VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    family_run_id,
                    plan["document_ordinal"],
                    plan["source_logical_name"],
                    plan["source_sha256"],
                    "UNRESOLVED_GEMINI_JSON_FAMILY",
                    1,
                    None,
                    0,
                    b"[]",
                    sha256(trial_bytes).hexdigest(),
                    trial_bytes,
                ),
            )
            candidate = {
                "candidate_id": plan["candidate_id"],
                "page_json_version_id": plan["base_page_json_version_id"],
            }
            candidate_bytes = canonical_json_bytes_v1(candidate) + b"\n"
            connection.execute(
                "INSERT INTO family_candidate VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    family_run_id,
                    plan["document_ordinal"],
                    plan["candidate_id"],
                    plan["base_page_json_version_id"],
                    plan["physical_page"],
                    plan["section_id"],
                    plan["table_id"],
                    "UNRESOLVED_GEMINI_JSON_FAMILY",
                    0,
                    0,
                    sha256(candidate_bytes).hexdigest(),
                    candidate_bytes,
                ),
            )
        connection.commit()


def _inputs(tmp_path: Path, corpus: dict) -> dict:
    sweep = tmp_path / "sweep.json"
    selected = tmp_path / "selected.json"
    config = tmp_path / "repair-config.json"
    results = tmp_path / "results.sqlite3"
    family_run_id = "gjfafstorev1:run:" + "a" * 64
    corpus_index_id = "gjfccmiv1:index:" + "b" * 64
    pinned_sweep = deepcopy(corpus["sweep"])
    pinned_sweep["corpus_manifest_index_id"] = corpus_index_id
    _family_results_store(
        results,
        corpus=corpus,
        sweep=pinned_sweep,
        family_run_id=family_run_id,
    )
    selected_ids = [item["base_page_json_version_id"] for item in corpus["evidence"]]
    repair_config = {
        "authority_kind": "PINNED_CONFIG",
        "authority_ref": "config://tests/rollforward-table-repairs-v1",
        "base_corpus_manifest_index_id": corpus_index_id,
        "expected_plan_count": 6,
        "expected_selected_page_count": 6,
        "expected_selected_page_frontier_sha256": canonical_json_sha256_v1(selected_ids),
        "format_version": target.CONFIG_FORMAT_VERSION,
        "repair_source_family_run_id": family_run_id,
        "source_image_resolver_implementation_path": (
            "src/bctc_ai/evaluation/gemini_json_first_page_render_v1.py"
        ),
        "source_image_runtime": {
            "mupdf_version": fitz.mupdf_version,
            "pymupdf_version": fitz.__version__,
        },
        "table_repair_specs": corpus["specs"],
        "writable_page_store_ref_path": "writable.sqlite3",
        "writable_results_database_ref_path": "writable-results.sqlite3",
    }
    return {
        "family_sweep_path": sweep,
        "family_sweep_sha256": _write_json(sweep, pinned_sweep),
        "selected_page_ids_path": selected,
        "selected_page_ids_sha256": _write_json(selected, selected_ids),
        "source_page_store": corpus["store"],
        "source_page_store_sha256": sha256(corpus["store"].read_bytes()).hexdigest(),
        "source_results_database": results,
        "source_results_database_sha256": sha256(results.read_bytes()).hexdigest(),
        "repair_spec_config_path": config,
        "repair_spec_config_sha256": _write_json(config, repair_config),
        "workspace_root": _ROOT,
        "runner_implementation_sha256": sha256(_SCRIPT.read_bytes()).hexdigest(),
        "artifact_root": tmp_path,
    }


def _bind_fixture_images(monkeypatch: pytest.MonkeyPatch, corpus: dict) -> None:
    def resolve(_workspace_root, *, plan, **_kwargs):
        image = corpus["images"][plan["base_page_json_version_id"]]
        return image, {
            "format_version": "TEST_SOURCE_IMAGE_RESOLUTION_V1",
            "image_sha256": sha256(image).hexdigest(),
            "repair_job_id": plan["repair_job_id"],
        }

    monkeypatch.setattr(target, "resolve_rollforward_table_source_image_v1", resolve)
    monkeypatch.setattr(
        target,
        "compile_gemini_json_flat_family_specs_v1",
        lambda _topology, _evaluation, _schema: corpus["compiled"],
    )
    monkeypatch.setattr(
        family_store_subject,
        "validate_gemini_json_flat_family_sweep_v1",
        lambda value: value,
    )


def _rewrite_config(inputs: dict, mutate) -> None:
    value = json.loads(inputs["repair_spec_config_path"].read_bytes())
    mutate(value)
    inputs["repair_spec_config_sha256"] = _write_json(inputs["repair_spec_config_path"], value)


def test_dry_run_builds_exact_six_immutable_requests_without_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    corpus: dict,
) -> None:
    inputs = _inputs(tmp_path, corpus)
    output = tmp_path / "dry-run"
    _bind_fixture_images(monkeypatch, corpus)
    source_before = corpus["store"].read_bytes()

    result = target.run_rollforward_table_repair_v1(
        **inputs,
        artifact_dir=output,
        dry_run=True,
        provider_call=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("dry-run must never call a provider")
        ),
    )

    assert result == {
        "disposition": "DRY_RUN_PREPARED",
        "format_version": target.FORMAT_VERSION,
        "job_count": 6,
        "mode": "DRY_RUN",
        "official_selection": "NOT_PERFORMED",
        "plan_axis_sha256": result["plan_axis_sha256"],
        "run_contract_sha256": result["run_contract_sha256"],
        "selected_page_count": 6,
        "source_page_store_sha256": sha256(source_before).hexdigest(),
    }
    assert len(list((output / "jobs").glob("job-*/plan.json"))) == 6
    assert len(list((output / "jobs").glob("job-*/crop-image.png"))) == 6
    assert len(list((output / "jobs").glob("job-*/prompt.txt"))) == 6
    assert len(list((output / "jobs").glob("job-*/response-schema.json"))) == 6
    assert not list((output / "jobs").glob("job-*/attempt-*"))
    run_contract = json.loads((output / "run-contract.json").read_bytes())
    assert run_contract["runner_implementation_ref"] == {
        "path": target.RUNNER_IMPLEMENTATION_PATH,
        "sha256": inputs["runner_implementation_sha256"],
        "size_bytes": _SCRIPT.stat().st_size,
    }
    assert run_contract["effective_page_frontier_artifact_root"] == str(tmp_path)
    repair_authority = json.loads((output / "authority/repair-spec-authority.json").read_bytes())
    assert repair_authority["source_image_resolver"]["mupdf_version"] == fitz.mupdf_version
    assert repair_authority["source_image_resolver"]["pymupdf_version"] == fitz.__version__
    assert corpus["store"].read_bytes() == source_before
    assert all(path.stat().st_mode & 0o777 == 0o444 for path in output.rglob("*") if path.is_file())

    with pytest.raises(
        target.RunGeminiJsonRollforwardTableRepairV1Error,
        match="not empty",
    ):
        target.run_rollforward_table_repair_v1(
            **inputs,
            artifact_dir=output,
            dry_run=True,
        )


def test_fake_openrouter_escalates_one_sibling_and_records_exact_overlay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    corpus: dict,
) -> None:
    inputs = _inputs(tmp_path, corpus)
    output = tmp_path / "provider-run"
    writable = tmp_path / "writable.sqlite3"
    writable_results = tmp_path / "writable-results.sqlite3"
    shutil.copyfile(corpus["store"], writable)
    shutil.copyfile(inputs["source_results_database"], writable_results)
    _bind_fixture_images(monkeypatch, corpus)
    plans_by_version = {plan["base_page_json_version_id"]: plan for plan in corpus["plans"]}
    retry_version_id = corpus["plans"][0]["base_page_json_version_id"]
    calls = []
    writable_before_capture = writable.read_bytes()
    writable_results_before_capture = writable_results.read_bytes()

    def provider(**kwargs) -> ProviderResultV1:
        assert writable.read_bytes() == writable_before_capture
        assert writable_results.read_bytes() == writable_results_before_capture
        calls.append(kwargs["thinking_level"])
        version_id = next(
            line.split("=", 1)[1]
            for line in kwargs["prompt"].splitlines()
            if line.startswith("base_page_json_version_id=")
        )
        plan = plans_by_version[version_id]
        if version_id == retry_version_id and kwargs["thinking_level"] == "low":
            raise RuntimeError("fake undeclared provider failure")
        if version_id == retry_version_id and kwargs["thinking_level"] == "medium":
            raise target.GeminiJsonFirstProviderV1Error("fake retryable provider failure")
        response = _response(corpus["pages"][version_id], plan)
        usage = {
            "actual_cost_usd": "0.000100000000",
            "billing_disposition": "BILLED_ACTUAL",
            "cached_input_tokens": 0,
            "input_tokens": 10,
            "output_tokens": 5,
            "thought_tokens": 1,
            "total_tokens": 15,
        }
        return ProviderResultV1(
            output_text=canonical_json_bytes_v1(response).decode("utf-8"),
            raw_response_bytes=(
                canonical_json_bytes_v1({"fake_provider_response_for": version_id}) + b"\n"
            ),
            provider_name="Google",
            provider_model="google/gemini-3.7-flash-test",
            service_tier="flex",
            attempts=(
                {
                    "attempt_ordinal": 1,
                    "credential_slot": "OPENROUTER_SLOT_1",
                    "elapsed_seconds": "0.001",
                    "http_status": 200,
                    "outcome": "COMPLETED",
                    "provider": "OPENROUTER",
                    "usage": usage,
                },
            ),
            usage=usage,
            response_id_sha256=sha256(version_id.encode("utf-8")).hexdigest(),
        )

    source_before = corpus["store"].read_bytes()
    source_results_before = inputs["source_results_database"].read_bytes()
    result = target.run_rollforward_table_repair_v1(
        **inputs,
        artifact_dir=output,
        dry_run=False,
        writable_page_store=writable,
        writable_results_database=writable_results,
        openrouter_api_key="x" * 32,
        workers=6,
        provider_call=provider,
    )

    assert result["disposition"] == "REPAIR_FRONTIER_COMPLETE"
    assert result["attempt_count"] == 8
    assert result["job_status_counts"] == {"ABSTAINED": 0, "RESOLVED": 6}
    assert result["official_selection"] == "NOT_PERFORMED"
    assert (
        result["run_contract_sha256"]
        == sha256((output / "run-contract.json").read_bytes()).hexdigest()
    )
    assert calls == ["low"] * 6 + ["medium", "high"]
    overlay = json.loads((output / "repair-overlay.json").read_bytes())
    effective_frontier = json.loads((output / "effective-page-frontier.json").read_bytes())
    assert len(overlay["replacements"]) == 6
    assert effective_frontier["format_version"] == "GEMINI_FAMILY_EFFECTIVE_PAGE_FRONTIER_V1"
    assert effective_frontier["database_ref"]["path"] == "writable.sqlite3"
    assert effective_frontier["results_database_ref"]["path"] == "writable-results.sqlite3"
    checked_frontier, effective_ids = apply_gemini_family_effective_page_frontier_v1(
        effective_frontier,
        base_page_json_version_ids=json.loads(inputs["selected_page_ids_path"].read_bytes()),
    )
    assert checked_frontier == effective_frontier
    assert len(effective_ids) == 6
    standard_overlay = resolved_gemini_family_region_repair_overlay_v1(
        writable_results,
        family_run_id="gjfafstorev1:run:" + "a" * 64,
    )
    assert standard_overlay["job_status_counts"] == {"ABSTAINED": 0, "RESOLVED": 6}
    assert len(standard_overlay["replacements"]) == 6
    assert (
        len(
            page_json_region_repair_lineages_v1(
                writable,
                observed_page_json_version_ids=[
                    item["selected_page_json_version_id"] for item in overlay["replacements"]
                ],
            )
        )
        == 6
    )
    assert len(list((output / "jobs").glob("job-*/attempt-01-low/attempt.json"))) == 6
    request = json.loads(
        next((output / "jobs").glob("job-*/attempt-01-low/request.json")).read_bytes()
    )
    assert request["requested_model"] == "google/gemini-3.7-flash"
    assert request["requested_provider"] == "google-vertex/global/flex"
    assert request["allow_fallbacks"] is False
    assert len(list((output / "jobs").glob("job-*/attempt-02-medium/attempt.json"))) == 1
    assert len(list((output / "jobs").glob("job-*/attempt-03-high/attempt.json"))) == 1
    assert corpus["store"].read_bytes() == source_before
    assert inputs["source_results_database"].read_bytes() == source_results_before
    attempt_axis = json.loads((output / "attempt-artifact-axis.json").read_bytes())
    assert attempt_axis["manifest_axis_sha256"] == canonical_json_sha256_v1(
        attempt_axis["manifests"]
    )
    checkpoint = json.loads((output / result["capture_checkpoint"]["path"]).read_bytes())
    assert target._validate_capture_checkpoint(output, checkpoint) == checkpoint
    assert checkpoint["checkpoint_ordinal"] == 8
    manifest_ref = next(
        item["attempt_artifact_manifest_ref"]
        for item in attempt_axis["manifests"]
        if "provider-envelope.bin"
        in json.loads((output / item["attempt_artifact_manifest_ref"]["path"]).read_bytes())[
            "artifacts"
        ]
    )
    manifest = json.loads((output / manifest_ref["path"]).read_bytes())
    envelope_path = output / manifest["artifacts"]["provider-envelope.bin"]["path"]
    envelope = envelope_path.read_bytes()
    envelope_path.chmod(0o644)
    envelope_path.write_bytes(bytes([envelope[0] ^ 1]) + envelope[1:])
    with pytest.raises(
        target.RunGeminiJsonRollforwardTableRepairV1Error,
        match="does not authenticate",
    ):
        target._validate_attempt_artifact_manifest(output, manifest)


def test_openrouter_refuses_source_store_as_writable_target_before_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    corpus: dict,
) -> None:
    inputs = _inputs(tmp_path, corpus)
    writable_results = tmp_path / "writable-results.sqlite3"
    shutil.copyfile(inputs["source_results_database"], writable_results)
    _bind_fixture_images(monkeypatch, corpus)
    calls = []
    with pytest.raises(
        target.RunGeminiJsonRollforwardTableRepairV1Error,
        match="frozen source",
    ):
        target.run_rollforward_table_repair_v1(
            **inputs,
            artifact_dir=tmp_path / "rejected",
            dry_run=False,
            writable_page_store=corpus["store"],
            writable_results_database=writable_results,
            openrouter_api_key="x" * 32,
            provider_call=lambda **kwargs: calls.append(kwargs),
        )
    assert calls == []
    assert not (tmp_path / "rejected").exists()


def test_dry_run_rejects_family_run_swap_runner_drift_and_frontier_axis_attack(
    tmp_path: Path,
    corpus: dict,
) -> None:
    run_swap = _inputs(tmp_path / "run-swap", corpus)
    _rewrite_config(
        run_swap,
        lambda value: value.__setitem__(
            "repair_source_family_run_id", "gjfafstorev1:run:" + "f" * 64
        ),
    )
    with pytest.raises(
        target.RunGeminiJsonRollforwardTableRepairV1Error,
        match="source family run is absent",
    ):
        target.run_rollforward_table_repair_v1(
            **run_swap,
            artifact_dir=tmp_path / "run-swap-output",
            dry_run=True,
        )

    results_drift = _inputs(tmp_path / "results-drift", corpus)
    results_drift["source_results_database_sha256"] = "f" * 64
    with pytest.raises(
        target.RunGeminiJsonRollforwardTableRepairV1Error,
        match="family-results database bytes do not match",
    ):
        target.run_rollforward_table_repair_v1(
            **results_drift,
            artifact_dir=tmp_path / "results-drift-output",
            dry_run=True,
        )

    runner_drift = _inputs(tmp_path / "runner-drift", corpus)
    runner_drift["runner_implementation_sha256"] = "f" * 64
    with pytest.raises(
        target.RunGeminiJsonRollforwardTableRepairV1Error,
        match="runner bytes differ",
    ):
        target.run_rollforward_table_repair_v1(
            **runner_drift,
            artifact_dir=tmp_path / "runner-drift-output",
            dry_run=True,
        )

    frontier_drift = _inputs(tmp_path / "frontier-drift", corpus)
    reversed_ids = list(reversed(json.loads(frontier_drift["selected_page_ids_path"].read_bytes())))
    frontier_drift["selected_page_ids_sha256"] = _write_json(
        frontier_drift["selected_page_ids_path"], reversed_ids
    )
    with pytest.raises(
        target.RunGeminiJsonRollforwardTableRepairV1Error,
        match="order differs",
    ):
        target.run_rollforward_table_repair_v1(
            **frontier_drift,
            artifact_dir=tmp_path / "frontier-drift-output",
            dry_run=True,
        )


def test_openrouter_refuses_valid_database_ref_that_does_not_identify_writable_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    corpus: dict,
) -> None:
    inputs = _inputs(tmp_path, corpus)
    writable = tmp_path / "writable.sqlite3"
    decoy = tmp_path / "decoy.sqlite3"
    writable_results = tmp_path / "writable-results.sqlite3"
    shutil.copyfile(corpus["store"], writable)
    shutil.copyfile(corpus["store"], decoy)
    shutil.copyfile(inputs["source_results_database"], writable_results)
    _rewrite_config(
        inputs,
        lambda value: value.__setitem__("writable_page_store_ref_path", "decoy.sqlite3"),
    )
    _bind_fixture_images(monkeypatch, corpus)
    calls = []

    with pytest.raises(
        target.RunGeminiJsonRollforwardTableRepairV1Error,
        match="does not identify the writable database",
    ):
        target.run_rollforward_table_repair_v1(
            **inputs,
            artifact_dir=tmp_path / "wrong-ref-output",
            dry_run=False,
            writable_page_store=writable,
            writable_results_database=writable_results,
            openrouter_api_key="x" * 32,
            provider_call=lambda **kwargs: calls.append(kwargs),
        )
    assert calls == []
    assert not (tmp_path / "wrong-ref-output").exists()


def test_descriptor_snapshots_ignore_restored_source_path_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    corpus: dict,
) -> None:
    inputs = _inputs(tmp_path, corpus)
    _bind_fixture_images(monkeypatch, corpus)
    original_core = target._run_rollforward_table_repair_on_private_sqlite_v1
    original_sources = [corpus["store"], inputs["source_results_database"]]
    observed_private_paths = []

    def attacked_core(**kwargs):
        observed_private_paths.extend(
            [kwargs["source_page_store"], kwargs["source_results_database"]]
        )
        held_paths = []
        try:
            for ordinal, source in enumerate(original_sources):
                held = tmp_path / f"held-source-{ordinal}.sqlite3"
                os.replace(source, held)
                source.write_bytes(b"controlled non-SQLite path replacement")
                held_paths.append((source, held))
            return original_core(**kwargs)
        finally:
            for source, held in reversed(held_paths):
                source.unlink(missing_ok=True)
                os.replace(held, source)

    monkeypatch.setattr(
        target,
        "_run_rollforward_table_repair_on_private_sqlite_v1",
        attacked_core,
    )
    result = target.run_rollforward_table_repair_v1(
        **inputs,
        artifact_dir=tmp_path / "source-replacement-dry-run",
        dry_run=True,
    )

    assert result["disposition"] == "DRY_RUN_PREPARED"
    assert len(observed_private_paths) == 2
    assert all(path not in original_sources for path in observed_private_paths)
    assert (
        sha256(original_sources[0].read_bytes()).hexdigest() == inputs["source_page_store_sha256"]
    )
    assert (
        sha256(original_sources[1].read_bytes()).hexdigest()
        == inputs["source_results_database_sha256"]
    )


def test_writable_path_replacement_is_rejected_before_provider_or_publish(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    corpus: dict,
) -> None:
    inputs = _inputs(tmp_path, corpus)
    writable = tmp_path / "writable.sqlite3"
    writable_results = tmp_path / "writable-results.sqlite3"
    shutil.copyfile(corpus["store"], writable)
    shutil.copyfile(inputs["source_results_database"], writable_results)
    writable_before = writable.read_bytes()
    writable_results_before = writable_results.read_bytes()
    _bind_fixture_images(monkeypatch, corpus)
    original_core = target._run_rollforward_table_repair_on_private_sqlite_v1

    def attacked_core(**kwargs):
        assert kwargs["writable_page_store"] != writable
        assert kwargs["writable_results_database"] != writable_results
        held_writable = tmp_path / "held-writable.sqlite3"
        held_results = tmp_path / "held-writable-results.sqlite3"
        os.replace(writable, held_writable)
        os.replace(writable_results, held_results)
        writable.write_bytes(writable_before)
        writable_results.write_bytes(writable_results_before)
        try:
            return original_core(**kwargs)
        finally:
            writable.unlink(missing_ok=True)
            writable_results.unlink(missing_ok=True)
            os.replace(held_writable, writable)
            os.replace(held_results, writable_results)

    monkeypatch.setattr(
        target,
        "_run_rollforward_table_repair_on_private_sqlite_v1",
        attacked_core,
    )
    calls = []
    with pytest.raises(
        target.RunGeminiJsonRollforwardTableRepairV1Error,
        match="reference does not identify the writable database",
    ):
        target.run_rollforward_table_repair_v1(
            **inputs,
            artifact_dir=tmp_path / "writable-replacement-output",
            dry_run=False,
            writable_page_store=writable,
            writable_results_database=writable_results,
            openrouter_api_key="x" * 32,
            provider_call=lambda **kwargs: calls.append(kwargs),
        )
    assert calls == []
    assert writable.read_bytes() == writable_before
    assert writable_results.read_bytes() == writable_results_before
    assert not (tmp_path / "writable-replacement-output").exists()


def test_writable_path_replacement_after_apply_is_rejected_before_publish(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    corpus: dict,
) -> None:
    inputs = _inputs(tmp_path, corpus)
    writable = tmp_path / "writable.sqlite3"
    writable_results = tmp_path / "writable-results.sqlite3"
    held_writable = tmp_path / "held-writable.sqlite3"
    held_results = tmp_path / "held-writable-results.sqlite3"
    shutil.copyfile(corpus["store"], writable)
    shutil.copyfile(inputs["source_results_database"], writable_results)
    writable_before = writable.read_bytes()
    writable_results_before = writable_results.read_bytes()
    _bind_fixture_images(monkeypatch, corpus)
    plans_by_version = {plan["base_page_json_version_id"]: plan for plan in corpus["plans"]}
    calls = []

    def provider(**kwargs) -> ProviderResultV1:
        calls.append(kwargs["thinking_level"])
        version_id = next(
            line.split("=", 1)[1]
            for line in kwargs["prompt"].splitlines()
            if line.startswith("base_page_json_version_id=")
        )
        usage = {
            "actual_cost_usd": "0.000100000000",
            "billing_disposition": "BILLED_ACTUAL",
            "cached_input_tokens": 0,
            "input_tokens": 10,
            "output_tokens": 5,
            "thought_tokens": 1,
            "total_tokens": 15,
        }
        return ProviderResultV1(
            output_text=canonical_json_bytes_v1(
                _response(corpus["pages"][version_id], plans_by_version[version_id])
            ).decode("utf-8"),
            raw_response_bytes=canonical_json_bytes_v1({"fake": version_id}) + b"\n",
            provider_name="Google",
            provider_model="google/gemini-3.7-flash",
            service_tier="flex",
            attempts=(),
            usage=usage,
            response_id_sha256=sha256(version_id.encode()).hexdigest(),
        )

    original_core = target._run_rollforward_table_repair_on_private_sqlite_v1

    def attacked_core(**kwargs):
        result = original_core(**kwargs)
        assert result["disposition"] == "REPAIR_FRONTIER_COMPLETE"
        os.replace(writable, held_writable)
        os.replace(writable_results, held_results)
        writable.write_bytes(writable_before)
        writable_results.write_bytes(writable_results_before)
        return result

    monkeypatch.setattr(
        target,
        "_run_rollforward_table_repair_on_private_sqlite_v1",
        attacked_core,
    )
    try:
        with pytest.raises(
            target.RunGeminiJsonRollforwardTableRepairV1Error,
            match="path, inode, or bytes changed across the stable boundary",
        ):
            target.run_rollforward_table_repair_v1(
                **inputs,
                artifact_dir=tmp_path / "pre-publish-replacement-output",
                dry_run=False,
                writable_page_store=writable,
                writable_results_database=writable_results,
                openrouter_api_key="x" * 32,
                workers=6,
                provider_call=provider,
            )
        assert held_writable.read_bytes() == writable_before
        assert held_results.read_bytes() == writable_results_before
        assert writable.read_bytes() == writable_before
        assert writable_results.read_bytes() == writable_results_before
        assert calls == ["low"] * 6
    finally:
        writable.unlink(missing_ok=True)
        writable_results.unlink(missing_ok=True)
        if held_writable.exists():
            os.replace(held_writable, writable)
        if held_results.exists():
            os.replace(held_results, writable_results)


def test_runner_rejects_unbound_source_and_writable_sqlite_sidecars(
    tmp_path: Path,
    corpus: dict,
) -> None:
    for ordinal, field in enumerate(("source_page_store", "source_results_database")):
        inputs = _inputs(tmp_path / f"source-sidecar-{ordinal}", corpus)
        sidecar = Path(str(inputs[field]) + "-wal")
        sidecar.write_bytes(b"unbound")
        with pytest.raises(
            target.RunGeminiJsonRollforwardTableRepairV1Error,
            match="unbound SQLite sidecar",
        ):
            target.run_rollforward_table_repair_v1(
                **inputs,
                artifact_dir=tmp_path / f"source-sidecar-output-{ordinal}",
                dry_run=True,
            )

    inputs = _inputs(tmp_path / "writable-sidecar", corpus)
    writable = inputs["artifact_root"] / "writable.sqlite3"
    writable_results = inputs["artifact_root"] / "writable-results.sqlite3"
    shutil.copyfile(corpus["store"], writable)
    shutil.copyfile(inputs["source_results_database"], writable_results)
    Path(str(writable_results) + "-journal").write_bytes(b"unbound")
    with pytest.raises(
        target.RunGeminiJsonRollforwardTableRepairV1Error,
        match="unbound SQLite sidecar",
    ):
        target.run_rollforward_table_repair_v1(
            **inputs,
            artifact_dir=tmp_path / "writable-sidecar-output",
            dry_run=False,
            writable_page_store=writable,
            writable_results_database=writable_results,
            openrouter_api_key="x" * 32,
        )


def test_cross_store_failure_is_terminal_and_seals_replay_without_provider_recall(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    corpus: dict,
) -> None:
    inputs = _inputs(tmp_path, corpus)
    output = tmp_path / "incomplete-run"
    writable = tmp_path / "writable.sqlite3"
    writable_results = tmp_path / "writable-results.sqlite3"
    shutil.copyfile(corpus["store"], writable)
    shutil.copyfile(inputs["source_results_database"], writable_results)
    _bind_fixture_images(monkeypatch, corpus)
    plans_by_version = {plan["base_page_json_version_id"]: plan for plan in corpus["plans"]}
    retry_version_id = corpus["plans"][0]["base_page_json_version_id"]
    calls = []

    def provider(**kwargs) -> ProviderResultV1:
        calls.append(kwargs["thinking_level"])
        version_id = next(
            line.split("=", 1)[1]
            for line in kwargs["prompt"].splitlines()
            if line.startswith("base_page_json_version_id=")
        )
        plan = plans_by_version[version_id]
        if kwargs["thinking_level"] == "low":
            plan_ordinal = next(
                ordinal
                for ordinal, candidate in enumerate(corpus["plans"])
                if candidate["base_page_json_version_id"] == version_id
            )
            time.sleep((len(corpus["plans"]) - plan_ordinal) * 0.01)
        if version_id == retry_version_id and kwargs["thinking_level"] == "low":
            raise RuntimeError("fake undeclared provider failure")
        if version_id == retry_version_id and kwargs["thinking_level"] == "medium":
            raise target.GeminiJsonFirstProviderV1Error("fake retryable provider failure")
        usage = {
            "actual_cost_usd": "0.000100000000",
            "billing_disposition": "BILLED_ACTUAL",
            "cached_input_tokens": 0,
            "input_tokens": 10,
            "output_tokens": 5,
            "thought_tokens": 1,
            "total_tokens": 15,
        }
        return ProviderResultV1(
            output_text=canonical_json_bytes_v1(
                _response(corpus["pages"][version_id], plan)
            ).decode("utf-8"),
            raw_response_bytes=canonical_json_bytes_v1({"fake": version_id}) + b"\n",
            provider_name="Google",
            provider_model="google/gemini-3.7-flash",
            service_tier="flex",
            attempts=(),
            usage=usage,
            response_id_sha256=sha256(version_id.encode()).hexdigest(),
        )

    def fail_results_mirror(*_args, **_kwargs):
        raise sqlite3.OperationalError("fake cross-store failure")

    original_mirror = target._mirror_family_attempt
    monkeypatch.setattr(target, "_mirror_family_attempt", fail_results_mirror)
    result = target.run_rollforward_table_repair_v1(
        **inputs,
        artifact_dir=output,
        dry_run=False,
        writable_page_store=writable,
        writable_results_database=writable_results,
        openrouter_api_key="x" * 32,
        workers=6,
        provider_call=provider,
    )

    assert result["disposition"] == "REPAIR_FRONTIER_INCOMPLETE"
    assert result["provider_recall"] == "FORBIDDEN"
    assert calls == ["low"] * 6 + ["medium", "high"]
    assert len(result["failed_database_apply_jobs"]) == 8
    assert len(result["recovery_journals"]) == 6
    axis_manifests = json.loads((output / "attempt-artifact-axis.json").read_bytes())["manifests"]
    checkpoint_manifests = json.loads(
        (output / "capture-checkpoints/checkpoint-008.json").read_bytes()
    )["attempt_artifact_manifests"]
    assert len(axis_manifests) == 8
    assert checkpoint_manifests != axis_manifests
    assert sorted(checkpoint_manifests, key=lambda item: item["attempt_id"]) == sorted(
        axis_manifests, key=lambda item: item["attempt_id"]
    )
    assert not (output / "repair-overlay.json").exists()
    assert not (output / "effective-page-frontier.json").exists()
    assert writable.read_bytes() == corpus["store"].read_bytes()
    assert writable_results.read_bytes() == inputs["source_results_database"].read_bytes()

    monkeypatch.setattr(target, "_mirror_family_attempt", original_mirror)
    sealed_result_sha256 = sha256((output / "run-result.json").read_bytes()).hexdigest()
    recovered = target.replay_sealed_rollforward_table_repair_v1(
        **inputs,
        sealed_artifact_dir=output,
        sealed_run_result_sha256=sealed_result_sha256,
        replay_artifact_dir=tmp_path / "replayed-run",
        writable_page_store=writable,
        writable_results_database=writable_results,
    )

    assert recovered["disposition"] == "REPAIR_FRONTIER_RECOVERED"
    assert recovered["provider_call_count"] == 0
    assert recovered["job_status_counts"] == {"ABSTAINED": 0, "RESOLVED": 6}
    assert calls == ["low"] * 6 + ["medium", "high"]
    assert (tmp_path / "replayed-run/effective-page-frontier.json").is_file()
    with sqlite3.connect(writable_results) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT a.attempt_ordinal,a.thinking_level,a.outcome,a.usage_json "
            "FROM family_region_repair_attempt AS a "
            "JOIN family_region_repair_job AS j USING(repair_job_id) "
            "WHERE j.document_ordinal=9 ORDER BY a.attempt_ordinal"
        ).fetchall()
    assert [(row["attempt_ordinal"], row["thinking_level"], row["outcome"]) for row in rows] == [
        (1, "low", "PROVIDER_OR_VALIDATION_FAILURE"),
        (2, "medium", "PROVIDER_OR_VALIDATION_FAILURE"),
        (3, "high", "RESOLVED"),
    ]
    assert [json.loads(row["usage_json"])["actual_cost_usd"] for row in rows] == [
        "0",
        "0",
        "0.000100000000",
    ]
    recovered_frontier = json.loads(
        (tmp_path / "replayed-run/effective-page-frontier.json").read_bytes()
    )
    checked, effective_ids = apply_gemini_family_effective_page_frontier_v1(
        recovered_frontier,
        base_page_json_version_ids=json.loads(inputs["selected_page_ids_path"].read_bytes()),
    )
    assert checked == recovered_frontier
    assert len(effective_ids) == 6
