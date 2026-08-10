from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import stat
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import fitz
import pytest
import yaml

from bctc_ai.corpus import wave1_role_b_line_only_supplement_v1 as line_only
from bctc_ai.corpus.wave1_role_b_word_box_normalization import (
    WORD_BOX_NORMALIZATION_POLICY,
    normalization_policy_sha256,
)
from bctc_ai.rendering.page_reader import (
    coordinate_authority,
    public_coordinate_authority,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_CACHE = Path("/synthetic/model-cache")


@pytest.fixture(autouse=True)
def _forbid_real_v2_authentication(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("unit tests must not authenticate or read the active V2 run")

    monkeypatch.setattr(line_only.full_v2, "verify_authenticated_full_reader", forbidden)


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _write_immutable(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    path.chmod(0o444)


def _put_upstream_json(root: Path, value: dict[str, Any]) -> dict[str, Any]:
    payload = line_only._canonical_bytes(value)
    digest = hashlib.sha256(payload).hexdigest()
    relative = f"objects/sha256/{digest[:2]}/{digest}.json"
    _write_immutable(root / line_only.UPSTREAM_OUTPUT_RELATIVE_ROOT / relative, payload)
    return {"path": relative, "sha256": digest, "size_bytes": len(payload)}


def _policy() -> dict[str, Any]:
    return yaml.safe_load(
        (
            PROJECT_ROOT / "config/corpus/bank-corpus-wave-1-role-b-line-only-supplement-v1.yaml"
        ).read_text(encoding="utf-8")
    )


def _public_authority(rotation: int) -> dict[str, Any]:
    pdf = fitz.open()
    try:
        page = pdf.new_page(width=100, height=200)
        page.set_rotation(rotation)
        width = int(page.rect.width * 2)
        height = int(page.rect.height * 2)
        return public_coordinate_authority(
            coordinate_authority(page, pixel_width=width, pixel_height=height)
        )
    finally:
        pdf.close()


def _fixture(
    root: Path,
    *,
    rotation: int = 0,
    line_text: str = "Tổng tài sản",
    subdivision_count: int = 2,
) -> tuple[
    line_only.FinalizedV2Authority,
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    coordinates = _public_authority(rotation)
    width, height = coordinates["pixel_dimensions"]
    line_box = [10, 10, width - 5, min(height - 5, 50)]
    polygon = [
        [line_box[0], line_box[1]],
        [line_box[2], line_box[1]],
        [line_box[2], line_box[3]],
        [line_box[0], line_box[3]],
    ]
    subdivision_texts = [f"hidden-{index}" for index in range(subdivision_count)]
    subdivision_boxes = []
    for index in range(subdivision_count):
        if index == subdivision_count - 1:
            subdivision_boxes.append([width - 10, 15, width + 2, 35])
        else:
            subdivision_boxes.append([15 + index * 10, 15, 24 + index * 10, 35])
    raw = {
        "return_word_box": True,
        "rec_texts": [line_text],
        "rec_scores": [0.875],
        "rec_polys": [polygon],
        "rec_boxes": [line_box],
        "text_word_boxes": [subdivision_boxes],
        "text_word": [subdivision_texts],
    }
    control_id = "5f4f00d40900be2765b6f873b268cd09c28026245157d2bdb0b293eb24a64be1"
    producer_ledger = _digest("upstream-normalization-ledger")
    normalization = {
        "policy": deepcopy(WORD_BOX_NORMALIZATION_POLICY),
        "policy_sha256": normalization_policy_sha256(WORD_BOX_NORMALIZATION_POLICY),
        "control_identity_sha256": control_id,
        "normalization_producer_implementation_ledger_sha256": producer_ledger,
    }
    request = {
        "provider_identity_sha256": _digest("provider"),
        "render_runtime_identity_sha256": _digest("render-runtime"),
        "synthetic_fixture_identity_sha256": _digest(
            f"terminal-request-{rotation}-{line_text}-{subdivision_count}"
        ),
    }
    request_sha = line_only._canonical_sha256(request)
    render_ref = {
        "path": f"objects/sha256/{_digest('render')[:2]}/{_digest('render')}.png",
        "sha256": _digest("render"),
        "size_bytes": 123,
    }
    failure = {
        "format_version": "BANK_CORPUS_WAVE_1_PPOCRV6_NORMALIZATION_FAILURE_V1",
        "status": "UNRESOLVED_OCR_WORD_BOX_GEOMETRY",
        "reason": "BOUNDED_WORD_BOX_NORMALIZATION_INVARIANT_FAILED",
        "policy_sha256": normalization["policy_sha256"],
        "control_identity_sha256": control_id,
        "normalization_producer_implementation_ledger_sha256": producer_ledger,
        "pixel_dimensions": [width, height],
        "raw_payload_sha256": line_only._canonical_sha256(raw),
    }
    backend = {
        "format_version": "BANK_CORPUS_WAVE_1_PPOCRV6_BACKEND_PAYLOAD_V3",
        "claim_boundary": (
            "RAW_PINNED_PROVIDER_PAYLOAD_WITH_TERMINAL_BOUNDED_WORD_BOX_GEOMETRY_FAILURE"
        ),
        "request_sha256": request_sha,
        "request": request,
        "provider_identity_sha256": request["provider_identity_sha256"],
        "render_ref": render_ref,
        "raw_provider_payload": raw,
        "word_box_normalization_ledger": None,
        "normalization_failure": failure,
    }
    backend_ref = _put_upstream_json(root, backend)
    result = {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V3",
        "status": "UNRESOLVED_OCR_WORD_BOX_GEOMETRY",
        "claim_boundary": "SOURCE_VISIBLE_PAGE_RAW_OCR_EVIDENCE_WITH_UNRESOLVED_GEOMETRY",
        "request_sha256": request_sha,
        "request": request,
        "source_sha256": _digest("source"),
        "source_size_bytes": 456,
        "physical_page": 7,
        "route": "DOMINANT_RASTER_OCR",
        "provider_identity_sha256": request["provider_identity_sha256"],
        "render_runtime_identity_sha256": request["render_runtime_identity_sha256"],
        "input_render_ref": render_ref,
        "backend_payload_ref": backend_ref,
        "normalization_failure": failure,
        "coordinate_authority": coordinates,
        "lines": [],
        "words": [],
        "metrics": {"line_count": 0, "word_token_count": 0},
        "ocr_fallback_used": False,
        "source_blank_claimed": False,
        "safety": line_only._upstream_result_safety(),
    }
    result_ref = _put_upstream_json(root, result)
    terminal = {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_FULL_PAGE_RECORD_V1",
        "request_ordinal": 7,
        "request_sha256": request_sha,
        "request": request,
        "document_id": f"sha256:{result['source_sha256']}",
        "physical_page": 7,
        "source_sha256": result["source_sha256"],
        "source_size_bytes": result["source_size_bytes"],
        "route": "DOMINANT_RASTER_OCR",
        "status": "UNRESOLVED_OCR_WORD_BOX_GEOMETRY",
        "unresolved": True,
        "origin": "PINNED_PPOCRV6_FULL_READER",
        "render_ref": render_ref,
        "backend_payload_ref": backend_ref,
        "result_ref": result_ref,
        "line_count": 0,
        "word_token_count": 0,
        "quarantined_span_count": 0,
        "word_box_correction_count": 0,
        "word_box_corrected_edge_count": 0,
        "statement_classification_count": 0,
        "table_classification_count": 0,
        "row_reconstruction_count": 0,
        "cell_interpretation_count": 0,
        "absence_declaration_count": 0,
    }
    page_records = []
    for ordinal in range(1, 1_450):
        if ordinal == terminal["request_ordinal"]:
            page_records.append(terminal)
        else:
            page_records.append(
                {
                    "request_sha256": _digest(f"nonterminal-{ordinal}"),
                    "status": "OCR_WORD_BOX_READ_COMPLETE",
                }
            )
    aggregate = {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READS_V1",
        "status": "COMPLETE_WAVE_1_PAGE_REQUEST_ACCOUNTING_WITH_UNRESOLVED_READS",
        "aggregate_identity_sha256": _digest("aggregate-identity"),
        "sealed_plan": {
            "sha256": line_only.full_v2.SEALED_PLAN_SHA256,
            "size_bytes": line_only.full_v2.SEALED_PLAN_SIZE_BYTES,
        },
        "executor_git": {"commit": _digest("upstream-commit")[:40]},
        "executor_implementation_ledger": {"sha256": _digest("upstream-ledger")},
        "page_records": page_records,
        "accounting": {
            "request_count": 1_449,
            "outcome_counts": {"UNRESOLVED_OCR_WORD_BOX_GEOMETRY": 1},
        },
        "word_box_normalization_accounting": {"unresolved_geometry_page_count": 1},
    }
    upstream_control = {
        "control_identity_sha256": control_id,
        "word_box_normalization": normalization,
    }
    aggregate_payload = line_only._canonical_bytes(aggregate)
    control_payload = line_only._canonical_bytes(upstream_control)
    terminal_object_identities = []
    for reference in (backend_ref, result_ref):
        identity = (root / line_only.UPSTREAM_OUTPUT_RELATIVE_ROOT / reference["path"]).stat(
            follow_symlinks=False
        )
        terminal_object_identities.append((reference["path"], line_only._stat_identity(identity)))
    authority = line_only.FinalizedV2Authority(
        aggregate=aggregate,
        control=upstream_control,
        aggregate_payload=aggregate_payload,
        control_payload=control_payload,
        aggregate_identity=(1, 2, len(aggregate_payload), 3, 0o444, 1),
        control_identity=(1, 4, len(control_payload), 5, 0o444, 1),
        terminal_object_identities=tuple(terminal_object_identities),
    )
    supplement_control = {"control_identity_sha256": _digest("supplement-control")}
    return authority, terminal, supplement_control, raw


def _mutate_backend(
    root: Path,
    record: dict[str, Any],
    mutation: Any,
) -> None:
    path = root / line_only.UPSTREAM_OUTPUT_RELATIVE_ROOT / record["backend_payload_ref"]["path"]
    backend = json.loads(path.read_text(encoding="utf-8"))
    mutation(backend)
    path.chmod(0o600)
    path.unlink()
    record["backend_payload_ref"] = _put_upstream_json(root, backend)
    result_path = root / line_only.UPSTREAM_OUTPUT_RELATIVE_ROOT / record["result_ref"]["path"]
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["backend_payload_ref"] = deepcopy(record["backend_payload_ref"])
    result["normalization_failure"] = deepcopy(backend["normalization_failure"])
    result_path.chmod(0o600)
    result_path.unlink()
    record["result_ref"] = _put_upstream_json(root, result)


def _replace_raw_axes(
    root: Path,
    record: dict[str, Any],
    *,
    texts: list[str],
) -> None:
    def replace(backend: dict[str, Any]) -> None:
        raw = backend["raw_provider_payload"]
        raw["rec_texts"] = texts
        raw["rec_scores"] = [0.9 - index / 100 for index in range(len(texts))]
        raw["rec_boxes"] = [
            [10, 10 + 40 * index, 190, 40 + 40 * index] for index in range(len(texts))
        ]
        raw["rec_polys"] = [
            [[box[0], box[1]], [box[2], box[1]], [box[2], box[3]], [box[0], box[3]]]
            for box in raw["rec_boxes"]
        ]
        raw["text_word"] = [[f"hidden-{index}"] for index in range(len(texts))]
        raw["text_word_boxes"] = [[[15, box[1] + 2, 202, box[3] - 2]] for box in raw["rec_boxes"]]
        backend["normalization_failure"]["raw_payload_sha256"] = line_only._canonical_sha256(raw)

    _mutate_backend(root, record, replace)


def _set_zero_score_and_origin_geometry(
    root: Path, record: dict[str, Any], *, signed: bool
) -> None:
    zero = -0.0 if signed else 0.0

    def replace(backend: dict[str, Any]) -> None:
        raw = backend["raw_provider_payload"]
        raw["rec_scores"] = [zero]
        raw["rec_boxes"] = [[zero, zero, 195, 50]]
        raw["rec_polys"] = [[[zero, zero], [195, zero], [195, 50], [zero, 50]]]
        backend["normalization_failure"]["raw_payload_sha256"] = line_only._canonical_sha256(raw)

    _mutate_backend(root, record, replace)


def _rewrite_checkpoint_evidence(
    root: Path, mutation: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    output = root / line_only.OUTPUT_RELATIVE_ROOT
    checkpoint_path = next((output / "checkpoints").glob("*.json"))
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    evidence_path = output / checkpoint["evidence_ref"]["path"]
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    mutation(evidence)
    checkpoint["evidence_ref"] = line_only._put_object(root, line_only._canonical_bytes(evidence))
    checkpoint_path.chmod(0o600)
    checkpoint_path.unlink()
    _write_immutable(checkpoint_path, line_only._canonical_bytes(checkpoint))
    return checkpoint, evidence


def _fake_executor() -> dict[str, Any]:
    records = [
        {
            "phase": "READ",
            "kind": "IMPLEMENTATION",
            "path": path.as_posix(),
            "sha256": _digest(path.as_posix()),
            "size_bytes": 1,
        }
        for path in line_only.LINE_ONLY_IMPLEMENTATION_RELATIVE_PATHS
    ]
    return {
        "git": {
            "commit": _digest("line-only-commit")[:40],
            "tree": _digest("line-only-tree")[:40],
            "branch": "synthetic",
            "dirty": False,
        },
        "implementation_ledger": {
            "records": records,
            "sha256": line_only._canonical_sha256(records),
        },
    }


def _authority_with_aggregate(
    authority: line_only.FinalizedV2Authority, aggregate: dict[str, Any]
) -> line_only.FinalizedV2Authority:
    payload = line_only._canonical_bytes(aggregate)
    return line_only.FinalizedV2Authority(
        aggregate=aggregate,
        control=authority.control,
        aggregate_payload=payload,
        control_payload=authority.control_payload,
        aggregate_identity=(1, 2, len(payload), 3, 0o444, 1),
        control_identity=authority.control_identity,
        terminal_object_identities=authority.terminal_object_identities,
    )


def _publish_synthetic_upstream_authority(
    root: Path, authority: line_only.FinalizedV2Authority
) -> line_only.FinalizedV2Authority:
    aggregate_path = root / line_only.UPSTREAM_OUTPUT_RELATIVE_ROOT / "full-reader-aggregate.json"
    control_path = (
        root / line_only.UPSTREAM_OUTPUT_RELATIVE_ROOT / "full-reader-execution-control.json"
    )
    _write_immutable(aggregate_path, authority.aggregate_payload)
    _write_immutable(control_path, authority.control_payload)
    aggregate_stat = aggregate_path.stat(follow_symlinks=False)
    control_stat = control_path.stat(follow_symlinks=False)
    return line_only.FinalizedV2Authority(
        aggregate=authority.aggregate,
        control=authority.control,
        aggregate_payload=authority.aggregate_payload,
        control_payload=authority.control_payload,
        aggregate_identity=line_only._stat_identity(aggregate_stat),
        control_identity=line_only._stat_identity(control_stat),
        terminal_object_identities=authority.terminal_object_identities,
    )


def _patch_runtime(
    monkeypatch: pytest.MonkeyPatch,
    authority: line_only.FinalizedV2Authority,
) -> None:
    monkeypatch.setattr(line_only, "_authenticate_finalized_v2", lambda *_args, **_kw: authority)
    monkeypatch.setattr(line_only, "_load_policy", lambda _root: deepcopy(_policy()))
    monkeypatch.setattr(line_only, "_executor_identity", lambda *_args, **_kw: _fake_executor())
    monkeypatch.setattr(line_only, "_validate_published_executor", lambda *_args, **_kw: None)
    monkeypatch.setattr(line_only, "_recheck_upstream_authority", lambda *_args, **_kw: None)


def _tree_snapshot(root: Path) -> list[tuple[Any, ...]]:
    if not root.exists():
        return []
    records = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        identity = path.stat(follow_symlinks=False)
        if stat.S_ISDIR(identity.st_mode):
            records.append(("d", relative, stat.S_IMODE(identity.st_mode), identity.st_nlink))
        elif stat.S_ISLNK(identity.st_mode):
            records.append(("l", relative, os.readlink(path)))
        else:
            payload = path.read_bytes()
            records.append(
                (
                    "f",
                    relative,
                    stat.S_IMODE(identity.st_mode),
                    identity.st_nlink,
                    identity.st_size,
                    identity.st_mtime_ns,
                    hashlib.sha256(payload).hexdigest(),
                )
            )
    return records


def _publication_temp(final: Path, nonce: str = "1" * 32) -> Path:
    temporary = final.with_name(f".{final.name}.{nonce}.tmp")
    os.link(final, temporary)
    return temporary


def _local_import_closure(relative_paths: set[Path]) -> set[Path]:
    imported: set[Path] = set()
    for relative in relative_paths:
        if relative.suffix != ".py":
            continue
        tree = ast.parse((PROJECT_ROOT / relative).read_text(encoding="utf-8"))
        package = list(relative.with_suffix("").parts[:-1])
        for node in ast.walk(tree):
            module_names: list[str] = []
            if isinstance(node, ast.Import):
                module_names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base = package[: len(package) - node.level + 1]
                    if node.module:
                        base.extend(node.module.split("."))
                    module = ".".join(base)
                else:
                    module = node.module or ""
                module_names.append(module)
                module_names.extend(f"{module}.{alias.name}" for alias in node.names if module)
            for module in module_names:
                parts = module.split(".")
                if parts[0] == "bctc_ai":
                    candidate = Path("src", *parts)
                elif parts[0] == "scripts":
                    candidate = Path(*parts)
                else:
                    continue
                module_file = candidate.with_suffix(".py")
                package_file = candidate / "__init__.py"
                if (PROJECT_ROOT / module_file).is_file():
                    imported.add(module_file)
                elif (PROJECT_ROOT / package_file).is_file():
                    imported.add(package_file)
    return imported


def test_policy_and_implementation_ledger_are_add_only_and_closed() -> None:
    policy = line_only._load_policy(PROJECT_ROOT)
    assert policy["execution"]["output_root"] == line_only.OUTPUT_RELATIVE_ROOT.as_posix()
    assert policy["projection"]["line_eligibility_rule"] == (
        "EXACT_STRING_LENGTH_GREATER_THAN_ZERO_NO_TRIM"
    )
    assert policy["projection"]["line_accounting_identity"] == (
        "VALIDATED_EQUALS_ACCEPTED_PLUS_EXCLUDED_EMPTY"
    )
    assert policy["forbidden_inputs"] == [
        "ROLE_A_ARTIFACTS",
        "CANONICAL_SCHEMA",
        "BASE_SCHEMA",
        "BANK_REGISTRY_METADATA",
        "BANK_IDENTITY",
        "SOURCE_FILENAME",
        "SOURCE_PATH_ROUTING",
        "HISTORICAL_VALUES",
        "PRIOR_MAPPING_OUTPUTS",
    ]
    assert set(policy["safety"].values()) <= {False, True}
    assert all(
        value is False
        for key, value in policy["safety"].items()
        if key != "upstream_terminal_status_preserved"
    )
    assert len(line_only.LINE_ONLY_IMPLEMENTATION_RELATIVE_PATHS) == len(
        set(line_only.LINE_ONLY_IMPLEMENTATION_RELATIVE_PATHS)
    )
    assert line_only.POLICY_RELATIVE_PATH in line_only.LINE_ONLY_IMPLEMENTATION_RELATIVE_PATHS
    assert line_only.MODULE_RELATIVE_PATH in line_only.LINE_ONLY_IMPLEMENTATION_RELATIVE_PATHS
    assert line_only.CLI_RELATIVE_PATH in line_only.LINE_ONLY_IMPLEMENTATION_RELATIVE_PATHS
    assert set(line_only.full_v2.FULL_READER_IMPLEMENTATION_RELATIVE_PATHS) < set(
        line_only.LINE_ONLY_IMPLEMENTATION_RELATIVE_PATHS
    )
    production = {line_only.MODULE_RELATIVE_PATH, line_only.CLI_RELATIVE_PATH}
    implementation = set(line_only.LINE_ONLY_IMPLEMENTATION_RELATIVE_PATHS)
    imported_local = _local_import_closure(implementation)
    assert imported_local <= implementation
    assert Path("src/bctc_ai/corpus/wave1_role_b_full_reader_v2.py") in imported_local
    forbidden_modules = ("role_a", "schema", "mapping", "export", "bank_registry")
    assert all(
        not any(token in path.as_posix() for token in forbidden_modules) for path in production
    )


def test_typed_json_equality_preserves_signed_zero_and_rejects_nonfinite() -> None:
    assert line_only._same_typed_json(0.0, 0.0)
    assert line_only._same_typed_json(-0.0, -0.0)
    assert not line_only._same_typed_json(0.0, -0.0)
    assert not line_only._same_typed_json(-0.0, 0.0)
    assert not line_only._same_typed_json(float("nan"), float("nan"))
    assert not line_only._same_typed_json(float("inf"), float("inf"))
    assert not line_only._same_typed_json(0, 0.0)


def test_ready_control_has_only_planned_accounting_and_writes_nothing(
    tmp_path: Path,
) -> None:
    authority, _record, _control, _raw = _fixture(tmp_path)
    before = _tree_snapshot(tmp_path / line_only.OUTPUT_RELATIVE_ROOT)
    control = line_only._build_control_from_authority(_policy(), _fake_executor(), authority)
    assert _tree_snapshot(tmp_path / line_only.OUTPUT_RELATIVE_ROOT) == before == []
    assert control["accounting"] == {
        "upstream_request_count": 1_449,
        "terminal_denominator_count": 1,
        "required_supplemental_disposition_count": 1,
        "expected_missing_terminal_count": 0,
        "expected_duplicate_terminal_count": 0,
        "expected_foreign_terminal_count": 0,
    }
    assert "supplemental_disposition_count" not in control["accounting"]


def test_valid_zero_terminal_denominator_builds_zero_claim_aggregate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, _record, _control, _raw = _fixture(tmp_path)
    aggregate = deepcopy(authority.aggregate)
    aggregate["page_records"][6]["status"] = "OCR_WORD_BOX_READ_COMPLETE"
    aggregate["accounting"]["outcome_counts"].pop("UNRESOLVED_OCR_WORD_BOX_GEOMETRY")
    aggregate["word_box_normalization_accounting"]["unresolved_geometry_page_count"] = 0
    zero_authority = _authority_with_aggregate(authority, aggregate)
    assert line_only._terminal_records(aggregate) == []
    control = line_only._build_control_from_authority(_policy(), _fake_executor(), zero_authority)
    candidate = line_only._build_aggregate(zero_authority, control, [], [], [])
    assert candidate["page_records"] == []
    assert candidate["accounting"]["terminal_denominator_count"] == 0
    assert candidate["accounting"]["accepted_plus_rejected_count"] == 0
    assert candidate["accounting"]["missing_terminal_count"] == 0
    assert candidate["accounting"]["validated_line_axis_count"] == 0
    assert candidate["accounting"]["supplemental_disposition_counts"] == {
        line_only._ACCEPTED_DISPOSITION: 0,
        line_only._REJECTED_DISPOSITION: 0,
    }
    _patch_runtime(monkeypatch, zero_authority)
    summary = line_only.run_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)
    assert summary["status"] == "COMPLETE_LINE_ONLY_RUN_WITH_ZERO_REQUIRED_PROJECTIONS"
    assert summary["terminal_denominator_count"] == 0
    assert summary["checkpoint_count"] == 0
    assert summary["new_projection_count"] == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("commit", "--help"),
        ("commit", False),
        ("tree", "not-a-tree"),
        ("tree", 1.0),
        ("branch", False),
        ("branch", ""),
    ],
)
def test_published_executor_rejects_typed_and_option_like_git_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: Any,
) -> None:
    executor = _fake_executor()
    control = {
        "executor_git": deepcopy(executor["git"]),
        "executor_implementation_ledger": deepcopy(executor["implementation_ledger"]),
    }
    control["executor_git"][field] = value
    called = False

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        nonlocal called
        called = True
        raise AssertionError("invalid git identity reached git plumbing")

    monkeypatch.setattr(line_only.subprocess, "run", forbidden)
    with pytest.raises(line_only.WaveOneRoleBLineOnlySupplementError):
        line_only._validate_published_executor(tmp_path, control)
    assert called is False


def test_published_executor_binds_recorded_tree_to_producer_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = b"x"
    records = [
        {
            "phase": "READ",
            "kind": "IMPLEMENTATION",
            "path": path.as_posix(),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }
        for path in line_only.LINE_ONLY_IMPLEMENTATION_RELATIVE_PATHS
    ]
    control = {
        "executor_git": {
            "commit": "a" * 40,
            "tree": "b" * 40,
            "branch": "main",
            "dirty": False,
        },
        "executor_implementation_ledger": {
            "records": records,
            "sha256": line_only._canonical_sha256(records),
        },
    }
    monkeypatch.setattr(line_only, "_git_output", lambda *_args, **_kwargs: "c" * 40)
    with pytest.raises(
        line_only.WaveOneRoleBLineOnlySupplementError,
        match="producer tree",
    ):
        line_only._validate_published_executor(tmp_path, control)


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_projection_is_line_only_rotation_safe_and_word_nonleaking(
    tmp_path: Path, rotation: int
) -> None:
    authority, record, control, raw = _fixture(tmp_path, rotation=rotation)
    evidence = line_only._project_terminal_page(tmp_path, authority, control, record)
    assert line_only.OUTPUT_RELATIVE_ROOT != line_only.UPSTREAM_OUTPUT_RELATIVE_ROOT
    assert "full-v2" not in line_only.OUTPUT_RELATIVE_ROOT.parts
    assert evidence["supplemental_disposition"] == line_only._ACCEPTED_DISPOSITION
    assert evidence["upstream"]["status"] == "UNRESOLVED_OCR_WORD_BOX_GEOMETRY"
    assert evidence["upstream"]["status_preserved"] is True
    assert evidence["words"] == []
    assert len(evidence["lines"]) == 1
    assert evidence["lines"][0]["text"] == raw["rec_texts"][0]
    assert evidence["coordinate_authority"]["pdf_rotation_degrees"] == rotation
    expected_geometry = {
        0: (
            [5000, 5000, 97500, 25000],
            [[5000, 5000], [97500, 5000], [97500, 25000], [5000, 25000]],
        ),
        90: (
            [5000, 2500, 25000, 195000],
            [[5000, 195000], [5000, 2500], [25000, 2500], [25000, 195000]],
        ),
        180: (
            [2500, 175000, 95000, 195000],
            [[95000, 195000], [2500, 195000], [2500, 175000], [95000, 175000]],
        ),
        270: (
            [75000, 5000, 95000, 197500],
            [[95000, 5000], [95000, 197500], [75000, 197500], [75000, 5000]],
        ),
    }
    assert evidence["lines"][0]["canonical_rec_box_mpt"] == expected_geometry[rotation][0]
    assert evidence["lines"][0]["canonical_rec_polygon_mpt"] == expected_geometry[rotation][1]
    assert evidence["metrics"] == {
        "validated_line_axis_count": 1,
        "excluded_empty_line_axis_count": 0,
        "accepted_line_count": 1,
        "accepted_word_count": 0,
        "quarantined_subdivision_count": 2,
    }
    quarantine = evidence["quarantine"]
    assert quarantine["ordered_subdivision_counts_by_line"] == [2]
    assert quarantine["total_subdivision_count"] == 2
    assert quarantine["accepted_word_count"] == 0
    encoded = line_only._canonical_bytes(evidence).decode("utf-8")
    assert "hidden-0" not in encoded
    assert "hidden-1" not in encoded
    assert '"text_word"' not in encoded
    assert '"text_word_boxes"' not in encoded
    assert set(evidence["safety"].values()) == {False}


def test_valid_but_nonempty_line_gate_rejection_is_still_dispositioned(
    tmp_path: Path,
) -> None:
    authority, record, control, _raw = _fixture(tmp_path, line_text="")
    evidence = line_only._project_terminal_page(tmp_path, authority, control, record)
    assert evidence["supplemental_disposition"] == line_only._REJECTED_DISPOSITION
    assert evidence["lines"] == []
    assert evidence["metrics"]["validated_line_axis_count"] == 1
    assert evidence["metrics"]["excluded_empty_line_axis_count"] == 1
    assert evidence["metrics"]["accepted_line_count"] == 0
    assert evidence["quarantine"]["total_subdivision_count"] == 2
    assert evidence["upstream"]["status_preserved"] is True


def test_mixed_empty_line_axes_are_validated_but_never_emitted(
    tmp_path: Path,
) -> None:
    authority, record, control, _raw = _fixture(tmp_path)
    _replace_raw_axes(tmp_path, record, texts=["Tài sản", "", "Nguồn vốn"])
    evidence = line_only._project_terminal_page(tmp_path, authority, control, record)
    assert evidence["supplemental_disposition"] == line_only._ACCEPTED_DISPOSITION
    assert [line["line_index"] for line in evidence["lines"]] == [0, 2]
    assert [line["text"] for line in evidence["lines"]] == ["Tài sản", "Nguồn vốn"]
    assert evidence["metrics"] == {
        "validated_line_axis_count": 3,
        "excluded_empty_line_axis_count": 1,
        "accepted_line_count": 2,
        "accepted_word_count": 0,
        "quarantined_subdivision_count": 3,
    }
    assert evidence["quarantine"]["ordered_subdivision_counts_by_line"] == [1, 1, 1]
    encoded = line_only._canonical_bytes(evidence).decode("utf-8")
    assert "hidden-0" not in encoded
    assert "hidden-1" not in encoded
    assert "hidden-2" not in encoded


@pytest.mark.parametrize("text", [" ", "\t", "\n", "\u00a0", "\u200b"])
def test_exact_nonempty_line_rule_does_not_trim_whitespace_codepoints(
    tmp_path: Path, text: str
) -> None:
    authority, record, control, _raw = _fixture(tmp_path, line_text=text)
    evidence = line_only._project_terminal_page(tmp_path, authority, control, record)
    assert evidence["supplemental_disposition"] == line_only._ACCEPTED_DISPOSITION
    assert evidence["lines"][0]["text"] == text
    assert evidence["metrics"]["accepted_line_count"] == 1
    assert evidence["metrics"]["excluded_empty_line_axis_count"] == 0


def test_projection_rejects_polygon_that_collapses_after_canonical_rounding(
    tmp_path: Path,
) -> None:
    authority, record, control, _raw = _fixture(tmp_path)

    def collapse(backend: dict[str, Any]) -> None:
        raw = backend["raw_provider_payload"]
        raw["rec_polys"] = [[[10.0, 10.0], [10.0001, 10.0], [10.0001, 10.0001], [10.0, 10.0001]]]
        backend["normalization_failure"]["raw_payload_sha256"] = line_only._canonical_sha256(raw)

    _mutate_backend(tmp_path, record, collapse)
    with pytest.raises(
        line_only.WaveOneRoleBLineOnlySupplementError,
        match="canonical line geometry",
    ):
        line_only._project_terminal_page(tmp_path, authority, control, record)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda backend: backend["raw_provider_payload"]["rec_scores"].__setitem__(0, 1.5),
        lambda backend: backend["raw_provider_payload"]["rec_boxes"].__setitem__(
            0, [-1, 10, 30, 40]
        ),
        lambda backend: backend["raw_provider_payload"]["rec_polys"].__setitem__(
            0, [[1, 1], [1, 1], [1, 1], [1, 1]]
        ),
        lambda backend: backend["raw_provider_payload"]["rec_texts"].append("drift"),
        lambda backend: backend["normalization_failure"].__setitem__(
            "raw_payload_sha256", _digest("wrong")
        ),
    ],
)
def test_projection_fails_closed_on_non_word_or_failure_tamper(
    tmp_path: Path, mutation: Any
) -> None:
    authority, record, control, _raw = _fixture(tmp_path)
    _mutate_backend(tmp_path, record, mutation)
    with pytest.raises(line_only.WaveOneRoleBLineOnlySupplementError):
        line_only._project_terminal_page(tmp_path, authority, control, record)


def test_projection_rejects_unexpectedly_normalizable_word_geometry(tmp_path: Path) -> None:
    authority, record, control, _raw = _fixture(tmp_path)

    def make_normalizable(backend: dict[str, Any]) -> None:
        raw = backend["raw_provider_payload"]
        raw["text_word_boxes"] = [[[15, 15, 25, 35], [30, 15, 40, 35]]]
        backend["normalization_failure"]["raw_payload_sha256"] = line_only._canonical_sha256(raw)

    _mutate_backend(tmp_path, record, make_normalizable)
    with pytest.raises(
        line_only.WaveOneRoleBLineOnlySupplementError,
        match="unexpectedly word-box normalizable",
    ):
        line_only._project_terminal_page(tmp_path, authority, control, record)


def test_projection_rejects_coordinate_authority_typed_drift(tmp_path: Path) -> None:
    authority, record, control, _raw = _fixture(tmp_path)
    result_path = tmp_path / line_only.UPSTREAM_OUTPUT_RELATIVE_ROOT / record["result_ref"]["path"]
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["coordinate_authority"]["pdf_rotation_degrees"] = 0.0
    result_path.chmod(0o600)
    result_path.unlink()
    record["result_ref"] = _put_upstream_json(tmp_path, result)
    with pytest.raises(line_only.WaveOneRoleBLineOnlySupplementError):
        line_only._project_terminal_page(tmp_path, authority, control, record)


def test_unchanged_signed_zero_source_evidence_replays_deterministically(
    tmp_path: Path,
) -> None:
    authority, record, control, _raw = _fixture(tmp_path)
    _set_zero_score_and_origin_geometry(tmp_path, record, signed=True)
    first = line_only._project_terminal_page(tmp_path, authority, control, record)
    second = line_only._project_terminal_page(tmp_path, authority, control, record)
    assert line_only._same_typed_json(first, second)
    assert first["lines"][0]["score"].hex() == "-0x0.0p+0"
    assert first["lines"][0]["pixel_rec_box"][0].hex() == "-0x0.0p+0"
    assert first["lines"][0]["pixel_rec_polygon"][0][0].hex() == "-0x0.0p+0"


@pytest.mark.parametrize(
    "field",
    ["score", "box_x", "box_y", "polygon_x", "polygon_y"],
)
def test_checkpoint_replay_rejects_signed_zero_swap_in_score_or_geometry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    authority, record, _control, _raw = _fixture(tmp_path)
    _set_zero_score_and_origin_geometry(tmp_path, record, signed=False)
    _patch_runtime(monkeypatch, authority)
    line_only.run_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)

    def swap(evidence: dict[str, Any]) -> None:
        line = evidence["lines"][0]
        if field == "score":
            line["score"] = -0.0
        elif field == "box_x":
            line["pixel_rec_box"][0] = -0.0
        elif field == "box_y":
            line["pixel_rec_box"][1] = -0.0
        elif field == "polygon_x":
            line["pixel_rec_polygon"][0][0] = -0.0
        else:
            line["pixel_rec_polygon"][0][1] = -0.0

    _rewrite_checkpoint_evidence(tmp_path, swap)
    before = _tree_snapshot(tmp_path / line_only.OUTPUT_RELATIVE_ROOT)
    with pytest.raises(
        line_only.WaveOneRoleBLineOnlySupplementError,
        match="deterministic replay drifted",
    ):
        line_only.verify_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)
    assert _tree_snapshot(tmp_path / line_only.OUTPUT_RELATIVE_ROOT) == before


def test_published_aggregate_signed_zero_swap_is_not_exact(
    tmp_path: Path,
) -> None:
    expected = {"synthetic_float": 0.0}
    published = {"synthetic_float": -0.0}
    _write_immutable(
        tmp_path / line_only.OUTPUT_RELATIVE_ROOT / line_only.AGGREGATE_FILENAME,
        line_only._canonical_bytes(published),
    )
    with pytest.raises(
        line_only.WaveOneRoleBLineOnlySupplementError,
        match="aggregate replay drifted",
    ):
        line_only.authenticated_line_only_aggregate_is_published(tmp_path, expected)


def test_upstream_authority_recheck_rejects_aggregate_and_cas_replacement(
    tmp_path: Path,
) -> None:
    authority, record, _control, _raw = _fixture(tmp_path)
    authority = _publish_synthetic_upstream_authority(tmp_path, authority)
    line_only._recheck_upstream_authority(tmp_path, authority)

    aggregate_path = (
        tmp_path / line_only.UPSTREAM_OUTPUT_RELATIVE_ROOT / "full-reader-aggregate.json"
    )
    payload = aggregate_path.read_bytes()
    aggregate_path.chmod(0o600)
    aggregate_path.unlink()
    _write_immutable(aggregate_path, payload)
    with pytest.raises(
        line_only.WaveOneRoleBLineOnlySupplementError,
        match="authority changed",
    ):
        line_only._recheck_upstream_authority(tmp_path, authority)

    authority, record, _control, _raw = _fixture(tmp_path / "cas")
    authority = _publish_synthetic_upstream_authority(tmp_path / "cas", authority)
    backend_path = (
        tmp_path
        / "cas"
        / line_only.UPSTREAM_OUTPUT_RELATIVE_ROOT
        / record["backend_payload_ref"]["path"]
    )
    backend_payload = backend_path.read_bytes()
    backend_path.chmod(0o600)
    backend_path.unlink()
    _write_immutable(backend_path, backend_payload)
    with pytest.raises(
        line_only.WaveOneRoleBLineOnlySupplementError,
        match="object topology changed",
    ):
        line_only._recheck_upstream_authority(tmp_path / "cas", authority)


def test_run_resume_verify_finalize_are_deterministic_and_verify_is_read_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, _record, _control, _raw = _fixture(tmp_path)
    _patch_runtime(monkeypatch, authority)
    first = line_only.run_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)
    assert first["new_projection_count"] == 1
    assert first["checkpoint_count"] == first["terminal_denominator_count"] == 1
    output = tmp_path / line_only.OUTPUT_RELATIVE_ROOT
    before_resume = _tree_snapshot(output)
    second = line_only.run_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)
    assert second["status"] == "COMPLETE_LINE_ONLY_RESUME_WITH_ZERO_NEW_PROJECTIONS"
    assert second["new_projection_count"] == 0
    assert _tree_snapshot(output) == before_resume
    before_verify = _tree_snapshot(output)
    aggregate = line_only.verify_authenticated_line_only_supplement(
        tmp_path, model_cache=MODEL_CACHE
    )
    assert _tree_snapshot(output) == before_verify
    assert aggregate["accounting"]["terminal_denominator_count"] == 1
    assert aggregate["accounting"]["accepted_page_count"] == 1
    assert aggregate["accounting"]["accepted_plus_rejected_count"] == 1
    assert aggregate["accounting"]["accepted_word_count"] == 0
    assert aggregate["accounting"]["upstream_status_change_count"] == 0
    assert aggregate["accounting"]["validated_line_axis_count"] == 1
    assert aggregate["accounting"]["excluded_empty_line_axis_count"] == 0
    assert aggregate["accounting"]["supplemental_disposition_counts"] == {
        line_only._ACCEPTED_DISPOSITION: 1,
        line_only._REJECTED_DISPOSITION: 0,
    }
    assert aggregate["page_records"][0]["validated_line_axis_count"] == 1
    assert aggregate["page_records"][0]["excluded_empty_line_axis_count"] == 0
    finalized = line_only.finalize_authenticated_line_only_supplement(
        tmp_path, model_cache=MODEL_CACHE
    )
    assert finalized == aggregate
    aggregate_path = output / line_only.AGGREGATE_FILENAME
    identity = aggregate_path.stat()
    assert stat.S_IMODE(identity.st_mode) == 0o444
    assert identity.st_nlink == 1


def test_foreign_checkpoint_control_identity_aborts_without_new_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, _record, _control, _raw = _fixture(tmp_path)
    _patch_runtime(monkeypatch, authority)
    line_only.run_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)
    output = tmp_path / line_only.OUTPUT_RELATIVE_ROOT
    checkpoint = next((output / "checkpoints").glob("*.json"))
    value = json.loads(checkpoint.read_text(encoding="utf-8"))
    value["control_identity_sha256"] = _digest("foreign-control")
    checkpoint.chmod(0o600)
    checkpoint.unlink()
    _write_immutable(checkpoint, line_only._canonical_bytes(value))
    before = _tree_snapshot(output)
    with pytest.raises(line_only.WaveOneRoleBLineOnlySupplementError):
        line_only.run_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)
    assert _tree_snapshot(output) == before
    assert not (output / line_only.AGGREGATE_FILENAME).exists()


def test_foreign_evidence_control_identity_aborts_without_new_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, _record, _control, _raw = _fixture(tmp_path)
    _patch_runtime(monkeypatch, authority)
    line_only.run_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)
    output = tmp_path / line_only.OUTPUT_RELATIVE_ROOT
    checkpoint = next((output / "checkpoints").glob("*.json"))
    checkpoint_value = json.loads(checkpoint.read_text(encoding="utf-8"))
    evidence_path = output / checkpoint_value["evidence_ref"]["path"]
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["control_identity_sha256"] = _digest("foreign-evidence-control")
    foreign_ref = line_only._put_object(tmp_path, line_only._canonical_bytes(evidence))
    checkpoint_value["evidence_ref"] = foreign_ref
    checkpoint.chmod(0o600)
    checkpoint.unlink()
    _write_immutable(checkpoint, line_only._canonical_bytes(checkpoint_value))
    before = _tree_snapshot(output)
    with pytest.raises(line_only.WaveOneRoleBLineOnlySupplementError):
        line_only.run_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)
    assert _tree_snapshot(output) == before
    assert not (output / line_only.AGGREGATE_FILENAME).exists()


def test_published_control_bound_to_foreign_upstream_aborts_without_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, _record, _control, _raw = _fixture(tmp_path)
    _patch_runtime(monkeypatch, authority)
    line_only.run_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)
    output = tmp_path / line_only.OUTPUT_RELATIVE_ROOT
    control_path = output / line_only.CONTROL_FILENAME
    control = json.loads(control_path.read_text(encoding="utf-8"))
    control["upstream"]["aggregate_identity_sha256"] = _digest("foreign-aggregate")
    control["control_identity_sha256"] = line_only._canonical_sha256(
        {key: value for key, value in control.items() if key != "control_identity_sha256"}
    )
    control_path.chmod(0o600)
    control_path.unlink()
    _write_immutable(control_path, line_only._canonical_bytes(control))
    before = _tree_snapshot(output)
    with pytest.raises(line_only.WaveOneRoleBLineOnlySupplementError):
        line_only.run_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)
    assert _tree_snapshot(output) == before
    assert not (output / line_only.AGGREGATE_FILENAME).exists()


def test_published_control_typed_drift_aborts_even_with_recomputed_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, _record, _control, _raw = _fixture(tmp_path)
    _patch_runtime(monkeypatch, authority)
    line_only.run_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)
    output = tmp_path / line_only.OUTPUT_RELATIVE_ROOT
    control_path = output / line_only.CONTROL_FILENAME
    control = json.loads(control_path.read_text(encoding="utf-8"))
    control["accounting"]["terminal_denominator_count"] = 1.0
    control["control_identity_sha256"] = line_only._canonical_sha256(
        {key: value for key, value in control.items() if key != "control_identity_sha256"}
    )
    control_path.chmod(0o600)
    control_path.unlink()
    _write_immutable(control_path, line_only._canonical_bytes(control))
    before = _tree_snapshot(output)
    with pytest.raises(line_only.WaveOneRoleBLineOnlySupplementError):
        line_only.run_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)
    assert _tree_snapshot(output) == before


@pytest.mark.parametrize("command", ["control", "run", "finalize"])
def test_low_space_gate_precedes_every_supplement_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command: str,
) -> None:
    authority, _record, _control, _raw = _fixture(tmp_path)
    monkeypatch.setattr(
        line_only,
        "_authenticate_finalized_v2",
        lambda *_args, **_kwargs: authority,
    )
    monkeypatch.setattr(line_only, "_load_policy", lambda _root: deepcopy(_policy()))
    monkeypatch.setattr(
        line_only,
        "_ensure_capacity",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            line_only.WaveOneRoleBLineOnlySupplementError("synthetic low space")
        ),
    )
    operation = {
        "control": line_only.publish_authenticated_line_only_control,
        "run": line_only.run_authenticated_line_only_supplement,
        "finalize": line_only.finalize_authenticated_line_only_supplement,
    }[command]
    with pytest.raises(
        line_only.WaveOneRoleBLineOnlySupplementError,
        match="synthetic low space",
    ):
        operation(tmp_path, model_cache=MODEL_CACHE)
    assert _tree_snapshot(tmp_path / line_only.OUTPUT_RELATIVE_ROOT) == []


def test_unfinalized_v2_aborts_control_before_supplement_root_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(line_only, "_load_policy", lambda _root: deepcopy(_policy()))
    monkeypatch.setattr(
        line_only.full_v2,
        "verify_authenticated_full_reader",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("unfinished V2")),
    )
    with pytest.raises(
        line_only.WaveOneRoleBLineOnlySupplementError,
        match="finalized V2 read-only verifier did not pass",
    ):
        line_only.publish_authenticated_line_only_control(tmp_path, model_cache=MODEL_CACHE)
    assert _tree_snapshot(tmp_path / line_only.OUTPUT_RELATIVE_ROOT) == []


@pytest.mark.parametrize("post_gate", ["upstream", "executor"])
def test_control_publication_never_reports_success_after_post_publish_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    post_gate: str,
) -> None:
    authority, _record, _control, _raw = _fixture(tmp_path)
    _patch_runtime(monkeypatch, authority)
    if post_gate == "upstream":
        calls = 0

        def recheck(*_args: Any, **_kwargs: Any) -> None:
            nonlocal calls
            calls += 1
            if calls == 3:
                raise line_only.WaveOneRoleBLineOnlySupplementError(
                    "synthetic upstream replacement"
                )

        monkeypatch.setattr(line_only, "_recheck_upstream_authority", recheck)
    else:
        monkeypatch.setattr(
            line_only,
            "_validate_published_executor",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                line_only.WaveOneRoleBLineOnlySupplementError("synthetic implementation drift")
            ),
        )
    with pytest.raises(line_only.WaveOneRoleBLineOnlySupplementError, match="synthetic"):
        line_only.publish_authenticated_line_only_control(tmp_path, model_cache=MODEL_CACHE)
    output = tmp_path / line_only.OUTPUT_RELATIVE_ROOT
    control_path = output / line_only.CONTROL_FILENAME
    assert control_path.is_file()
    assert stat.S_IMODE(control_path.stat().st_mode) == 0o444
    assert not (output / "checkpoints").exists()
    assert not (output / line_only.AGGREGATE_FILENAME).exists()


def test_run_rechecks_upstream_before_first_page_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, _record, _control, _raw = _fixture(tmp_path)
    _patch_runtime(monkeypatch, authority)
    calls = 0

    def recheck(*_args: Any, **_kwargs: Any) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise line_only.WaveOneRoleBLineOnlySupplementError(
                "synthetic upstream mutation before page publication"
            )

    monkeypatch.setattr(line_only, "_recheck_upstream_authority", recheck)
    with pytest.raises(line_only.WaveOneRoleBLineOnlySupplementError, match="synthetic"):
        line_only.run_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)
    output = tmp_path / line_only.OUTPUT_RELATIVE_ROOT
    assert (output / line_only.CONTROL_FILENAME).is_file()
    assert not list((output / "checkpoints").glob("*.json"))
    assert not (output / "objects").exists()
    assert not (output / line_only.AGGREGATE_FILENAME).exists()


@pytest.mark.parametrize("post_gate", ["upstream", "executor"])
def test_finalize_never_reports_success_after_post_publish_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    post_gate: str,
) -> None:
    authority, _record, _control, _raw = _fixture(tmp_path)
    _patch_runtime(monkeypatch, authority)
    line_only.run_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)
    if post_gate == "upstream":
        calls = 0

        def recheck(*_args: Any, **_kwargs: Any) -> None:
            nonlocal calls
            calls += 1
            if calls == 3:
                raise line_only.WaveOneRoleBLineOnlySupplementError(
                    "synthetic upstream mutation after aggregate publication"
                )

        monkeypatch.setattr(line_only, "_recheck_upstream_authority", recheck)
    else:
        calls = 0

        def validate_executor(*_args: Any, **_kwargs: Any) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise line_only.WaveOneRoleBLineOnlySupplementError(
                    "synthetic implementation drift after aggregate publication"
                )

        monkeypatch.setattr(line_only, "_validate_published_executor", validate_executor)
    with pytest.raises(line_only.WaveOneRoleBLineOnlySupplementError, match="synthetic"):
        line_only.finalize_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)
    output = tmp_path / line_only.OUTPUT_RELATIVE_ROOT
    aggregate = output / line_only.AGGREGATE_FILENAME
    assert aggregate.is_file()
    identity = aggregate.stat()
    assert stat.S_IMODE(identity.st_mode) == 0o444
    assert identity.st_nlink == 1


def test_control_and_aggregate_link_window_recovery_is_mutating_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, _record, _control, _raw = _fixture(tmp_path)
    _patch_runtime(monkeypatch, authority)
    line_only.run_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)
    output = tmp_path / line_only.OUTPUT_RELATIVE_ROOT

    control = output / line_only.CONTROL_FILENAME
    control_temp = _publication_temp(control)
    before_control_verify = _tree_snapshot(output)
    with pytest.raises(line_only.WaveOneRoleBLineOnlySupplementError):
        line_only.verify_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)
    assert _tree_snapshot(output) == before_control_verify
    resumed = line_only.run_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)
    assert resumed["new_projection_count"] == 0
    assert not control_temp.exists()
    assert control.stat().st_nlink == 1

    line_only.finalize_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)
    aggregate = output / line_only.AGGREGATE_FILENAME
    aggregate_temp = _publication_temp(aggregate, "2" * 32)
    before_aggregate_verify = _tree_snapshot(output)
    with pytest.raises(line_only.WaveOneRoleBLineOnlySupplementError):
        line_only.verify_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)
    assert _tree_snapshot(output) == before_aggregate_verify
    first_payload = aggregate.read_bytes()
    replay = line_only.finalize_authenticated_line_only_supplement(
        tmp_path, model_cache=MODEL_CACHE
    )
    assert aggregate.read_bytes() == first_payload == line_only._canonical_bytes(replay)
    assert not aggregate_temp.exists()
    assert aggregate.stat().st_nlink == 1


@pytest.mark.parametrize(
    "attack", ["temp_only", "mismatched", "foreign", "nlink3", "mode", "symlink"]
)
def test_root_publication_recovery_rejects_unexplained_topology_without_mutation(
    tmp_path: Path, attack: str
) -> None:
    output = tmp_path / line_only.OUTPUT_RELATIVE_ROOT
    output.mkdir(parents=True)
    final = output / line_only.CONTROL_FILENAME
    expected_temp = output / f".{line_only.CONTROL_FILENAME}.{'a' * 32}.tmp"
    if attack != "temp_only":
        _write_immutable(final, b"control\n")
    if attack == "temp_only":
        _write_immutable(expected_temp, b"control\n")
    elif attack == "mismatched":
        _write_immutable(expected_temp, b"different\n")
    elif attack == "foreign":
        _publication_temp(final).rename(output / f".foreign.json.{'1' * 32}.tmp")
    elif attack == "nlink3":
        _publication_temp(final, "1" * 32)
        _publication_temp(final, "2" * 32)
    elif attack == "mode":
        expected_temp = _publication_temp(final, "3" * 32)
        final.chmod(0o400)
    elif attack == "symlink":
        expected_temp.symlink_to(final.name)
    before = _tree_snapshot(output)
    with (
        line_only._execution_lease(tmp_path),
        pytest.raises(line_only.WaveOneRoleBLineOnlySupplementError),
    ):
        line_only._recover_root_publication_pairs(tmp_path)
    after = _tree_snapshot(output)
    before_without_lease = [row for row in before if row[1] != line_only.LEASE_FILENAME]
    after_without_lease = [row for row in after if row[1] != line_only.LEASE_FILENAME]
    assert after_without_lease == before_without_lease


@pytest.mark.parametrize("attack", ["symlink", "hardlink", "mode", "nonempty"])
def test_execution_lease_rejects_preexisting_unsafe_identity(tmp_path: Path, attack: str) -> None:
    output = tmp_path / line_only.OUTPUT_RELATIVE_ROOT
    output.mkdir(parents=True)
    lock = output / line_only.LEASE_FILENAME
    target = tmp_path / "lease-target"
    target.write_bytes(b"" if attack != "nonempty" else b"x")
    target.chmod(0o600)
    if attack == "symlink":
        lock.symlink_to(target)
    elif attack == "hardlink":
        os.link(target, lock)
    else:
        lock.write_bytes(b"x" if attack == "nonempty" else b"")
        lock.chmod(0o644 if attack == "mode" else 0o600)
    with pytest.raises(line_only.WaveOneRoleBLineOnlySupplementError):
        with line_only._execution_lease(tmp_path):
            pytest.fail("unsafe lease reached critical section")
    assert not (output / line_only.CONTROL_FILENAME).exists()
    assert not (output / "checkpoints").exists()
    assert not (output / line_only.AGGREGATE_FILENAME).exists()


def test_execution_lease_rejects_path_replacement_at_flock_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / line_only.OUTPUT_RELATIVE_ROOT
    output.mkdir(parents=True)
    lock = output / line_only.LEASE_FILENAME
    captured_descriptor = -1
    original_flock = line_only.fcntl.flock

    def replacing_flock(descriptor: int, operation: int) -> None:
        nonlocal captured_descriptor
        captured_descriptor = descriptor
        if operation == line_only.fcntl.LOCK_EX:
            lock.unlink()
            lock.write_bytes(b"")
            lock.chmod(0o600)
            return
        original_flock(descriptor, operation)

    monkeypatch.setattr(line_only.fcntl, "flock", replacing_flock)
    with pytest.raises(line_only.WaveOneRoleBLineOnlySupplementError):
        with line_only._execution_lease(tmp_path):
            pytest.fail("replaced lease reached critical section")
    with pytest.raises(OSError):
        os.fstat(captured_descriptor)
    assert not (output / line_only.CONTROL_FILENAME).exists()


def test_execution_lease_rejects_replacement_during_critical_section(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / line_only.OUTPUT_RELATIVE_ROOT
    captured_descriptor = -1
    original_flock = line_only.fcntl.flock

    def capturing_flock(descriptor: int, operation: int) -> None:
        nonlocal captured_descriptor
        if operation == line_only.fcntl.LOCK_EX:
            captured_descriptor = descriptor
        original_flock(descriptor, operation)

    monkeypatch.setattr(line_only.fcntl, "flock", capturing_flock)
    with pytest.raises(line_only.WaveOneRoleBLineOnlySupplementError):
        with line_only._execution_lease(tmp_path):
            lock = output / line_only.LEASE_FILENAME
            lock.unlink()
            lock.write_bytes(b"")
            lock.chmod(0o600)
    with pytest.raises(OSError):
        os.fstat(captured_descriptor)
    assert not (output / line_only.CONTROL_FILENAME).exists()
    assert not (output / "checkpoints").exists()
    assert not (output / line_only.AGGREGATE_FILENAME).exists()


def test_checkpoint_link_window_is_read_only_failure_then_exact_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, _record, _control, _raw = _fixture(tmp_path)
    _patch_runtime(monkeypatch, authority)
    line_only.run_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)
    checkpoint = next((tmp_path / line_only.OUTPUT_RELATIVE_ROOT / "checkpoints").glob("*.json"))
    temporary = _publication_temp(checkpoint, "4" * 32)
    output = tmp_path / line_only.OUTPUT_RELATIVE_ROOT
    before = _tree_snapshot(output)
    with pytest.raises(line_only.WaveOneRoleBLineOnlySupplementError):
        line_only.verify_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)
    assert _tree_snapshot(output) == before
    resumed = line_only.run_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)
    assert resumed["new_projection_count"] == 0
    assert not temporary.exists()
    assert checkpoint.stat().st_nlink == 1


def test_crash_after_cas_before_checkpoint_resumes_exact_chain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority, _record, _control, _raw = _fixture(tmp_path)
    _patch_runtime(monkeypatch, authority)
    original = line_only._publish_exclusive
    failed = False

    def interrupt_checkpoint(
        project_root: Path, directory: Path, filename: str, payload: bytes
    ) -> Path:
        nonlocal failed
        if directory.name == "checkpoints" and not failed:
            failed = True
            raise line_only.WaveOneRoleBLineOnlySupplementError("synthetic crash")
        return original(project_root, directory, filename, payload)

    monkeypatch.setattr(line_only, "_publish_exclusive", interrupt_checkpoint)
    with pytest.raises(line_only.WaveOneRoleBLineOnlySupplementError, match="synthetic crash"):
        line_only.run_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)
    assert not list((tmp_path / line_only.OUTPUT_RELATIVE_ROOT / "checkpoints").glob("*.json"))
    assert list((tmp_path / line_only.OUTPUT_RELATIVE_ROOT / "objects" / "sha256").glob("*/*.json"))
    monkeypatch.setattr(line_only, "_publish_exclusive", original)
    resumed = line_only.run_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)
    assert resumed["new_projection_count"] == 1
    checkpoint_path = next(
        (tmp_path / line_only.OUTPUT_RELATIVE_ROOT / "checkpoints").glob("*.json")
    )
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert checkpoint["generation"] == 1
    assert checkpoint["previous_checkpoint_sha256"] is None


@pytest.mark.parametrize("attack", ["symlink", "hardlink", "typed"])
def test_verify_rejects_checkpoint_path_or_typed_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, attack: str
) -> None:
    authority, _record, _control, _raw = _fixture(tmp_path)
    _patch_runtime(monkeypatch, authority)
    line_only.run_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)
    checkpoint = next((tmp_path / line_only.OUTPUT_RELATIVE_ROOT / "checkpoints").glob("*.json"))
    if attack == "symlink":
        target = checkpoint.with_suffix(".target")
        target.write_bytes(checkpoint.read_bytes())
        target.chmod(0o444)
        checkpoint.chmod(0o600)
        checkpoint.unlink()
        checkpoint.symlink_to(target.name)
    elif attack == "hardlink":
        os.link(checkpoint, checkpoint.parent.parent / "checkpoint-hardlink")
    else:
        payload = json.loads(checkpoint.read_text(encoding="utf-8"))
        payload["generation"] = 1.0
        checkpoint.chmod(0o600)
        checkpoint.unlink()
        _write_immutable(checkpoint, line_only._canonical_bytes(payload))
    with pytest.raises(line_only.WaveOneRoleBLineOnlySupplementError):
        line_only.verify_authenticated_line_only_supplement(tmp_path, model_cache=MODEL_CACHE)


def test_terminal_denominator_rejects_missing_duplicate_and_foreign(
    tmp_path: Path,
) -> None:
    authority, _record, _control, _raw = _fixture(tmp_path)
    aggregate = deepcopy(authority.aggregate)
    aggregate["page_records"].pop()
    with pytest.raises(line_only.WaveOneRoleBLineOnlySupplementError):
        line_only._terminal_records(aggregate)
    aggregate = deepcopy(authority.aggregate)
    aggregate["page_records"][1]["request_sha256"] = aggregate["page_records"][0]["request_sha256"]
    with pytest.raises(line_only.WaveOneRoleBLineOnlySupplementError):
        line_only._terminal_records(aggregate)
    aggregate = deepcopy(authority.aggregate)
    aggregate["accounting"]["outcome_counts"]["UNRESOLVED_OCR_WORD_BOX_GEOMETRY"] = 2
    with pytest.raises(line_only.WaveOneRoleBLineOnlySupplementError):
        line_only._terminal_records(aggregate)


def test_cli_verify_and_finalize_report_publication_truth_without_overclaim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli_path = PROJECT_ROOT / "scripts/corpus/run_wave1_role_b_line_only_supplement_v1.py"
    spec = importlib.util.spec_from_file_location("synthetic_line_only_cli", cli_path)
    assert spec is not None and spec.loader is not None
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    aggregate = {
        "status": "COMPLETE_AUTHENTICATED_LINE_ONLY_SUPPLEMENT_FOR_TERMINAL_WORD_BOX_GEOMETRY",
        "aggregate_identity_sha256": _digest("aggregate"),
        "accounting": {"terminal_denominator_count": 2},
    }
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        cli,
        "verify_authenticated_line_only_supplement",
        lambda *_args, **_kwargs: deepcopy(aggregate),
    )
    monkeypatch.setattr(
        cli,
        "finalize_authenticated_line_only_supplement",
        lambda *_args, **_kwargs: deepcopy(aggregate),
    )

    published = False
    monkeypatch.setattr(
        cli,
        "authenticated_line_only_aggregate_is_published",
        lambda *_args, **_kwargs: published,
    )
    monkeypatch.setattr(
        cli,
        "parse_args",
        lambda: SimpleNamespace(command="verify", model_cache=MODEL_CACHE),
    )
    assert cli.main() == 0
    pre = json.loads(capsys.readouterr().out)
    assert pre["authenticated_published_aggregate_present"] is False
    assert pre["publication_command_invoked"] is False

    published = True
    monkeypatch.setattr(
        cli,
        "parse_args",
        lambda: SimpleNamespace(command="finalize", model_cache=MODEL_CACHE),
    )
    assert cli.main() == 0
    first_finalize = json.loads(capsys.readouterr().out)
    assert first_finalize["authenticated_published_aggregate_present"] is True
    assert first_finalize["publication_command_invoked"] is True
    assert cli.main() == 0
    idempotent_finalize = json.loads(capsys.readouterr().out)
    assert idempotent_finalize == first_finalize
