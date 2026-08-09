from __future__ import annotations

import copy
import inspect
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import fitz
import pytest
import yaml

from bctc_ai.core.hashing import sha256_bytes, sha256_file, stable_records_hash
from bctc_ai.document_phase import native_tm_document_artifact as native


def _run_git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _rehash_discovery_runtime_ledger(payload: dict[str, Any]) -> None:
    ledger = payload["inputs"]["runtime_read_ledger"]
    payload["inputs"]["runtime_read_ledger_sha256"] = stable_records_hash(
        json.dumps(record, ensure_ascii=False, sort_keys=True) for record in ledger
    )


def _right_text(page: fitz.Page, text: str, right: float, y: float) -> None:
    width = fitz.get_text_length(text, fontname="helv", fontsize=10)
    page.insert_text((right - width, y), text, fontname="helv", fontsize=10)


def _table_page(
    page: fitz.Page,
    *,
    top_text: str | None,
    heading: str,
) -> None:
    if top_text:
        page.insert_text((40, 35), top_text, fontname="helv", fontsize=10)
    page.insert_text((45, 60), heading, fontname="helv", fontsize=10)
    _right_text(page, "31/03/2026", 550, 82)
    _right_text(page, "Trieu dong", 550, 102)
    for ordinal, (label, value) in enumerate(
        (("Khoan muc mot", "1.000"), ("Khoan muc hai", "-"), ("Khoan muc ba", "0"))
    ):
        y = 132 + ordinal * 22
        page.insert_text((50, y), label, fontname="helv", fontsize=10)
        _right_text(page, value, 550, y)


def _make_pdf(path: Path, *, last_page_header: bool) -> None:
    document = fitz.open()
    page = document.new_page(width=600, height=800)
    _table_page(
        page,
        top_text="BANG CAN DOI KE TOAN",
        heading="Tai san va no phai tra",
    )
    page = document.new_page(width=600, height=800)
    _table_page(
        page,
        top_text="THUYET MINH BAO CAO TAI CHINH",
        heading="1 Tien mat va tuong duong tien",
    )
    page = document.new_page(width=600, height=800)
    _table_page(
        page,
        top_text="TIEP THEO",
        heading="2 Cho vay khach hang",
    )
    page = document.new_page(width=600, height=800)
    _table_page(
        page,
        top_text=("THUYET MINH BAO CAO TAI CHINH" if last_page_header else None),
        heading="3 Tai san khac",
    )
    document.save(path)
    document.close()


def _copy(root: Path, repository_root: Path, relative: str) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(repository_root / relative, target)


def _commit_identity(root: Path, commit: str, relative: str) -> dict[str, Any]:
    payload = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=root,
        capture_output=True,
        check=True,
    ).stdout
    return {
        "path": relative,
        "sha256": sha256_bytes(payload),
        "size_bytes": len(payload),
    }


def _discovery_payload(
    *,
    root: Path,
    source_relative: str,
    source_sha256: str,
    source_size: int,
    commit: str,
    page_count: int,
    boundary: int,
) -> dict[str, Any]:
    tracked_inputs = [
        ("DATASET_ROLE_REGISTRY", "data/registered/dataset_roles.jsonl"),
        ("NATIVE_TEXT_QUALITY_CONFIG", "config/ocr/native-text-quality-v2.yaml"),
        ("SOURCE_REGISTRY", "data/registered/source_registry.jsonl"),
        *(("STATEMENT_DISCOVERY_CONFIG", path) for path in native._DISCOVERY_CONFIG_PATHS),
        ("THIS_POLICY", native._DISCOVERY_PRODUCER_POLICY_PATH),
    ]
    runtime_inputs = [
        {"kind": kind, **_commit_identity(root, commit, relative)}
        for kind, relative in tracked_inputs
    ]
    runtime_inputs.append(
        {
            "kind": "SOURCE_PDF",
            "path": source_relative,
            "sha256": source_sha256,
            "size_bytes": source_size,
        }
    )
    runtime_inputs.sort(key=lambda record: (record["kind"], record["path"]))
    signals = []
    for page in range(1, page_count + 1):
        boundary_page = page == boundary
        signals.append(
            {
                "page": page,
                "notes_structure": page >= boundary and page != page_count,
                "form_types": ["TM"] if boundary_page else [],
                "candidates": (
                    [{"page_type": "TM", "locally_accepted": True}] if boundary_page else []
                ),
            }
        )
    return {
        "format_version": "REGISTERED_NATIVE_TEXT_STATEMENT_DISCOVERY_RESULT_V1",
        "policy": "REGISTERED_NATIVE_TEXT_STATEMENT_DISCOVERY_V1",
        "claim_boundary": "STATEMENT_PAGE_DISCOVERY_ONLY",
        "status": "ACCEPTED_NATIVE_TEXT_STATEMENT_DISCOVERY",
        "run_id": "synthetic-discovery-v1",
        "source": {
            "document_id": f"sha256:{source_sha256}",
            "relative_path": source_relative,
            "sha256": source_sha256,
            "size_bytes": source_size,
            "bank": None,
            "year": None,
            "dataset_role": "LOGIC_DEVELOPMENT",
            "registry_state": "REGISTERED",
            "hash_verified_stable": True,
            "immutable_role_assignment": True,
        },
        "code": {
            "commit": commit,
            "dirty": False,
            "implementation": [
                _commit_identity(root, commit, relative)
                for relative in native._DISCOVERY_IMPLEMENTATION_PATHS
            ],
        },
        "authority": {
            "geometry": "PYMUPDF_NATIVE_TEXT_WORDS",
            "base_scoring_engine": "MULTISIGNAL_STATEMENT_DISCOVERY_V4",
            "base_geometry_authority": "PP_OCRV6_WORD_BOXES",
            "evidence_source": "PYMUPDF_NATIVE_TEXT_GEOMETRY",
            "override_scope": "GEOMETRY_SOURCE_ONLY",
            "semantic_reader": None,
        },
        "isolation": {
            "prior_answer_artifacts_loaded": False,
            "historical_values_loaded": False,
            "role_a_outputs_loaded": False,
            "bank_identity_used_for_scoring": False,
            "filename_identity_used_for_scoring": False,
            "page_number_rules_used_for_scoring": False,
            "runtime_input_policy": "EXACT_DECLARED_PROJECT_INPUT_LEDGER",
        },
        "inputs": {
            "runtime_read_ledger": runtime_inputs,
            "runtime_read_ledger_sha256": stable_records_hash(
                json.dumps(record, ensure_ascii=False, sort_keys=True) for record in runtime_inputs
            ),
        },
        "native_text": {
            "page_count": page_count,
            "usable_page_count": page_count,
            "ocr_required_pages": [],
            "all_pages_usable": True,
            "pages": [{"page": page} for page in range(1, page_count + 1)],
        },
        "discovery": {
            "status": "ACCEPTED_MULTI_SIGNAL_STATEMENT_BLOCK",
            "geometry_authority": "PYMUPDF_NATIVE_TEXT_WORDS",
            "observed_pages": list(range(1, page_count + 1)),
            "page_signals": signals,
            "block": {
                "start_page": 1,
                "end_page": boundary - 1,
                "notes_boundary_page": boundary,
            },
        },
    }


def _make_registered_project(
    tmp_path: Path,
    repository_root: Path,
    *,
    role: str = "LOGIC_DEVELOPMENT",
    last_page_header: bool = False,
) -> tuple[Path, Path, Path, Path, str]:
    root = tmp_path / "registered-project"
    root.mkdir(parents=True)
    copied = {
        *native._IMPLEMENTATION_PATHS,
        *native._DISCOVERY_IMPLEMENTATION_PATHS,
        native.POLICY_RELATIVE_PATH.as_posix(),
        "config/tables/native-tm-regions-v1.yaml",
        "config/tables/geometry-v2.yaml",
        "config/ocr/native-text-quality-v2.yaml",
        native._DISCOVERY_PRODUCER_POLICY_PATH,
        *native._DISCOVERY_CONFIG_PATHS,
    }
    for relative in sorted(copied):
        _copy(root, repository_root, relative)
    (root / ".gitignore").write_text("output/\n", encoding="utf-8")
    source = root / "data/source.pdf"
    source.parent.mkdir(parents=True, exist_ok=True)
    _make_pdf(source, last_page_header=last_page_header)
    digest = sha256_file(source)
    source_record = {
        "document_id": f"sha256:{digest}",
        "relative_path": "data/source.pdf",
        "sha256": digest,
        "size_bytes": source.stat().st_size,
        "kind": "PDF",
        "state": "REGISTERED",
        "hash_verified_stable": True,
    }
    role_record = {
        "document_id": f"sha256:{digest}",
        "source_path": "data/source.pdf",
        "dataset_role": role,
        "immutable": True,
    }
    registry = root / "data/registered/source_registry.jsonl"
    roles = root / "data/registered/dataset_roles.jsonl"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(json.dumps(source_record, sort_keys=True) + "\n", encoding="utf-8")
    roles.write_text(json.dumps(role_record, sort_keys=True) + "\n", encoding="utf-8")
    _run_git(root, "init")
    _run_git(root, "config", "user.email", "native-tm@example.test")
    _run_git(root, "config", "user.name", "Native TM Test")
    _run_git(root, "add", ".")
    _run_git(root, "commit", "-m", "synthetic producer")
    commit = _run_git(root, "rev-parse", "HEAD")
    discovery = root / "output/development/discovery.json"
    discovery.parent.mkdir(parents=True, exist_ok=True)
    discovery_payload = _discovery_payload(
        root=root,
        source_relative="data/source.pdf",
        source_sha256=digest,
        source_size=source.stat().st_size,
        commit=commit,
        page_count=4,
        boundary=2,
    )
    discovery.write_bytes(_canonical_bytes(discovery_payload))
    assert _run_git(root, "status", "--porcelain", "--untracked-files=all") == ""
    return (
        root,
        source,
        discovery,
        root / native.POLICY_RELATIVE_PATH,
        sha256_file(discovery),
    )


def _build(
    root: Path,
    source: Path,
    discovery: Path,
    policy: Path,
    discovery_sha256: str,
) -> dict[str, Any]:
    return native.build_registered_native_tm_document_artifact(
        root,
        source,
        discovery,
        discovery_sha256,
        policy,
        "synthetic-native-tm-v1",
    )


def test_policy_is_canonical_source_only_and_hash_pinned(project_root: Path, tmp_path: Path):
    policy_path = project_root / native.POLICY_RELATIVE_PATH
    policy = native.load_native_tm_document_artifact_policy(policy_path, project_root)

    assert policy["required_dataset_role"] == "LOGIC_DEVELOPMENT"
    assert policy["completeness"]["page_denominator"] == "ALL_PDF_PAGES"
    assert policy["accepted_statement_discovery"]["runtime_input_kind_counts"] == {
        "DATASET_ROLE_REGISTRY": 1,
        "NATIVE_TEXT_QUALITY_CONFIG": 1,
        "SOURCE_PDF": 1,
        "SOURCE_REGISTRY": 1,
        "STATEMENT_DISCOVERY_CONFIG": 4,
        "THIS_POLICY": 1,
    }
    assert {
        "/role-a/",
        "/role_a/",
        "/schema/",
        "/schemas/",
        "/history/",
        "/review/",
        "/holdout/",
    } <= set(policy["role_isolation"]["forbidden_path_fragments"])
    assert set(policy["role_isolation"]["runtime_input_allowlist"]) == {
        "SOURCE_PDF",
        "SOURCE_REGISTRY",
        "DATASET_ROLE_REGISTRY",
        "ACCEPTED_STATEMENT_DISCOVERY",
        "THIS_POLICY",
        "NATIVE_TM_REGION_POLICY",
        "GEOMETRY_CONFIG",
        "NATIVE_TEXT_QUALITY_CONFIG",
    }
    assert all(
        "schema" not in kind.casefold()
        for kind in policy["role_isolation"]["runtime_input_allowlist"]
    )
    alternate = tmp_path / "policy.yaml"
    shutil.copy2(policy_path, alternate)
    with pytest.raises(native.NativeTMDocumentArtifactError, match="canonical policy"):
        native.load_native_tm_document_artifact_policy(alternate, project_root)

    drifted = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    drifted["configuration"]["geometry_config"]["sha256"] = "0" * 64
    canonical_copy = tmp_path / "project" / native.POLICY_RELATIVE_PATH
    canonical_copy.parent.mkdir(parents=True)
    canonical_copy.write_text(yaml.safe_dump(drifted), encoding="utf-8")
    for identity in drifted["configuration"].values():
        source = project_root / identity["path"]
        target = tmp_path / "project" / identity["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    with pytest.raises(native.NativeTMDocumentArtifactError, match="hash drifted"):
        native.load_native_tm_document_artifact_policy(canonical_copy, tmp_path / "project")


def test_public_build_has_no_claimed_git_state_and_rejects_non_development_role(
    project_root: Path,
    tmp_path: Path,
):
    assert (
        "git_state"
        not in inspect.signature(native.build_registered_native_tm_document_artifact).parameters
    )
    root, source, discovery, policy, discovery_sha = _make_registered_project(
        tmp_path, project_root, role="CALIBRATION"
    )
    with pytest.raises(native.NativeTMDocumentArtifactError, match="LOGIC_DEVELOPMENT"):
        _build(root, source, discovery, policy, discovery_sha)


def test_full_pdf_boundary_classification_and_region_preservation(
    project_root: Path,
    tmp_path: Path,
):
    root, source, discovery, policy, discovery_sha = _make_registered_project(
        tmp_path, project_root, last_page_header=False
    )
    payload = _build(root, source, discovery, policy, discovery_sha)

    assert [page["page"] for page in payload["pages"]] == [1, 2, 3, 4]
    assert [page["classification"] for page in payload["pages"]] == [
        "NON_TM",
        "QUANTITATIVE_TM",
        "QUANTITATIVE_TM",
        "UNASSESSED",
    ]
    # A valid monetary region before the accepted notes boundary stays NON_TM.
    assert payload["pages"][0]["native_tm_regions"]["regions"]
    # A region alone cannot authorize a post-boundary TM classification.
    assert payload["pages"][3]["native_tm_regions"]["regions"]
    assert (
        payload["pages"][3]["classification_evidence"][-1]["region_is_not_tm_routing_authority"]
        is True
    )
    assert payload["pages"][2]["source_visible_continuation_runs"]
    assert payload["completeness"] == {
        **payload["completeness"],
        "pdf_page_count": 4,
        "page_classification_record_count": 4,
        "assessed_classification_count": 3,
        "unassessed_pages": [4],
        "every_page_classified": False,
        "full_document_complete": False,
    }
    assert payload["status"] == "PARTIAL_NATIVE_TM_FULL_DOCUMENT_ARTIFACT"
    assert any(
        table["page"] == 1 and table["ownership_status"] == "BOUNDED_NON_TM_TABLE_REGION"
        for table in payload["table_inventory"]["records"]
    )
    assert any(
        table["page"] == 4 and table["ownership_status"] == "UNRESOLVED_PAGE_CLASSIFICATION"
        for table in payload["table_inventory"]["records"]
    )

    partial_output = root / "output/development/partial-native-tm-artifact.json"
    partial_publication = native.publish_registered_native_tm_document_artifact(
        root,
        source,
        discovery,
        discovery_sha,
        policy,
        "synthetic-native-tm-v1",
        partial_output,
    )
    assert partial_publication.payload["status"] == ("PARTIAL_NATIVE_TM_FULL_DOCUMENT_ARTIFACT")
    assert (
        native.load_registered_native_tm_document_artifact(
            partial_output,
            project_root=root,
            expected_sha256=partial_publication.sha256,
        )
        == partial_publication.payload
    )

    page_region_keys = {
        "page",
        "assessment_status",
        "regions",
        "inter_table_contexts",
        "unit_group_diagnostics",
        "excluded_spans",
        "unassigned_page_runs",
        "error",
    }
    region_keys = {
        "table_id",
        "header_runs",
        "geometry",
        "header_bindings",
        "rows",
        "grid_slots",
        "scalar_disclosures",
        "outside_financial_span_rows",
        "detached_margin_runs",
        "unassigned_runs",
    }
    for page in payload["pages"]:
        assert page_region_keys <= set(page["native_tm_regions"])
        for region in page["native_tm_regions"]["regions"]:
            assert region_keys <= set(region)
            assert all(
                isinstance(binding["evidence"], list) for binding in region["header_bindings"]
            )
            for row in region["rows"]:
                for cell in row["cells"]:
                    assert cell["parsed"]["observation"] in {
                        "VALUE",
                        "ZERO",
                        "DASH",
                        "INVALID",
                    }


def test_complete_status_requires_every_page_and_bounded_ownership(
    project_root: Path,
    tmp_path: Path,
):
    root, source, discovery, policy, discovery_sha = _make_registered_project(
        tmp_path, project_root, last_page_header=True
    )
    payload = _build(root, source, discovery, policy, discovery_sha)

    assert all(page["classification"] != "UNASSESSED" for page in payload["pages"])
    assert payload["table_inventory"]["all_table_ownership_bounded"] is True
    assert payload["completeness"]["full_document_complete"] is True
    assert payload["status"] == "COMPLETE_NATIVE_TM_FULL_DOCUMENT_ARTIFACT"
    assert payload["note_inventory"]["status"] == ("COMPLETE_SOURCE_VISIBLE_NOTE_HEADING_INVENTORY")
    assert all(
        record["number_used_for_routing"] is False and record["accounting_identity"] is None
        for record in payload["note_inventory"]["records"]
    )


def test_discovery_is_trusted_digest_source_and_boundary_bound(
    project_root: Path,
    tmp_path: Path,
):
    root, source, discovery, policy, discovery_sha = _make_registered_project(
        tmp_path, project_root, last_page_header=True
    )
    with pytest.raises(native.NativeTMDocumentArtifactError, match="trusted SHA-256"):
        _build(root, source, discovery, policy, "0" * 64)

    payload = json.loads(discovery.read_text(encoding="utf-8"))
    payload["source"]["relative_path"] = "data/different.pdf"
    discovery.write_bytes(_canonical_bytes(payload))
    with pytest.raises(native.NativeTMDocumentArtifactError, match="source identity differs"):
        _build(root, source, discovery, policy, sha256_file(discovery))

    payload["source"]["relative_path"] = "data/source.pdf"
    payload["discovery"]["page_signals"][1]["candidates"] = []
    discovery.write_bytes(_canonical_bytes(payload))
    with pytest.raises(native.NativeTMDocumentArtifactError, match="notes boundary"):
        _build(root, source, discovery, policy, sha256_file(discovery))


@pytest.mark.parametrize(
    "forbidden_path",
    [
        "config/schemas/tm-context-v1.yaml",
        "output/development/role-a/answer.json",
        "output/development/role_a/answer.json",
        "output/development/history/prior.json",
        "output/development/review/approved.json",
        "output/holdout/answer.json",
    ],
)
def test_discovery_runtime_ledger_rejects_forbidden_authority_paths_before_build(
    project_root: Path,
    tmp_path: Path,
    forbidden_path: str,
    monkeypatch: pytest.MonkeyPatch,
):
    root, source, discovery, policy, _discovery_sha = _make_registered_project(
        tmp_path, project_root, last_page_header=True
    )
    payload = json.loads(discovery.read_text(encoding="utf-8"))
    payload["inputs"]["runtime_read_ledger"].append(
        {
            "kind": "SCHEMA_INPUT",
            "path": forbidden_path,
            "sha256": "0" * 64,
            "size_bytes": 0,
        }
    )
    payload["inputs"]["runtime_read_ledger"].sort(
        key=lambda record: (record["kind"], record["path"])
    )
    _rehash_discovery_runtime_ledger(payload)
    discovery.write_bytes(_canonical_bytes(payload))

    def forbidden_late_read(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("runtime source/config reads started before path isolation")

    monkeypatch.setattr(native, "_runtime_inputs_current", forbidden_late_read)

    with pytest.raises(native.NativeTMDocumentArtifactError, match="runtime path is forbidden"):
        _build(root, source, discovery, policy, sha256_file(discovery))


def test_discovery_runtime_ledger_requires_exact_order_inventory_hash_and_identities(
    project_root: Path,
    tmp_path: Path,
):
    root, source, discovery, policy, _discovery_sha = _make_registered_project(
        tmp_path, project_root, last_page_header=True
    )
    original = json.loads(discovery.read_text(encoding="utf-8"))

    mutations: list[tuple[str, Any]] = []

    reordered = copy.deepcopy(original)
    reordered["inputs"]["runtime_read_ledger"][0:2] = reversed(
        reordered["inputs"]["runtime_read_ledger"][0:2]
    )
    _rehash_discovery_runtime_ledger(reordered)
    mutations.append(("order", reordered))

    wrong_identity = copy.deepcopy(original)
    wrong_identity["inputs"]["runtime_read_ledger"][0]["sha256"] = "f" * 64
    _rehash_discovery_runtime_ledger(wrong_identity)
    mutations.append(("producer inputs", wrong_identity))

    missing = copy.deepcopy(original)
    missing["inputs"]["runtime_read_ledger"].pop()
    _rehash_discovery_runtime_ledger(missing)
    mutations.append(("inventory", missing))

    extra_kind = copy.deepcopy(original)
    extra_kind["inputs"]["runtime_read_ledger"].append(
        {
            "kind": "UNDECLARED_INPUT",
            "path": "output/development/undeclared.json",
            "sha256": "0" * 64,
            "size_bytes": 0,
        }
    )
    extra_kind["inputs"]["runtime_read_ledger"].sort(
        key=lambda record: (record["kind"], record["path"])
    )
    _rehash_discovery_runtime_ledger(extra_kind)
    mutations.append(("inventory", extra_kind))

    bad_hash = copy.deepcopy(original)
    bad_hash["inputs"]["runtime_read_ledger_sha256"] = "0" * 64
    mutations.append(("hash", bad_hash))

    for expected_message, mutation in mutations:
        discovery.write_bytes(_canonical_bytes(mutation))
        with pytest.raises(native.NativeTMDocumentArtifactError, match=expected_message):
            _build(root, source, discovery, policy, sha256_file(discovery))


def test_discovery_source_identity_is_exact_including_registry_metadata(
    project_root: Path,
    tmp_path: Path,
):
    root, source, discovery, policy, _discovery_sha = _make_registered_project(
        tmp_path, project_root, last_page_header=True
    )
    payload = json.loads(discovery.read_text(encoding="utf-8"))
    payload["source"]["bank"] = "untrusted-metadata"
    discovery.write_bytes(_canonical_bytes(payload))

    with pytest.raises(native.NativeTMDocumentArtifactError, match="source identity differs"):
        _build(root, source, discovery, policy, sha256_file(discovery))


def test_build_is_deterministic_and_ledgers_have_no_external_authority(
    project_root: Path,
    tmp_path: Path,
):
    root, source, discovery, policy, discovery_sha = _make_registered_project(
        tmp_path, project_root, last_page_header=True
    )
    first = _build(root, source, discovery, policy, discovery_sha)
    second = _build(root, source, discovery, policy, discovery_sha)

    assert first == second
    assert _canonical_bytes(first) == _canonical_bytes(second)
    encoded = _canonical_bytes(first).decode("utf-8")
    assert str(root.resolve()) not in encoded
    ledger = first["inputs"]["runtime_read_ledger"]
    assert ledger == sorted(ledger, key=lambda item: (item["kind"], item["path"]))
    assert {item["kind"] for item in ledger} == set(
        first["producer_snapshots"]["policy"]["payload"]["role_isolation"][
            "runtime_input_allowlist"
        ]
    )
    assert not any(
        forbidden in item["path"].casefold()
        for item in ledger
        for forbidden in ("history", "reference", "schema", "role-a", "role_a")
    )
    assert first["isolation"]["schema_inputs_loaded"] is False
    assert first["isolation"]["historical_values_loaded"] is False
    assert first["isolation"]["role_a_outputs_loaded"] is False


def test_publish_strict_load_and_replay_survive_future_config_change(
    project_root: Path,
    tmp_path: Path,
):
    root, source, discovery, policy, discovery_sha = _make_registered_project(
        tmp_path, project_root, last_page_header=True
    )
    output = root / "output/development/native-tm-artifact.json"
    published = native.publish_registered_native_tm_document_artifact(
        root,
        source,
        discovery,
        discovery_sha,
        policy,
        "synthetic-native-tm-v1",
        output,
    )
    assert published.sha256 == sha256_file(output)
    assert (
        native.load_registered_native_tm_document_artifact(
            output, project_root=root, expected_sha256=published.sha256
        )
        == published.payload
    )


def test_strict_loader_executes_producer_code_not_current_build_semantics(
    project_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root, source, discovery, policy, discovery_sha = _make_registered_project(
        tmp_path, project_root, last_page_header=True
    )
    output = root / "output/development/native-tm-artifact.json"
    published = native.publish_registered_native_tm_document_artifact(
        root,
        source,
        discovery,
        discovery_sha,
        policy,
        "synthetic-native-tm-v1",
        output,
    )

    def future_incompatible_build(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("current build semantics must not execute old-artifact replay")

    monkeypatch.setattr(native, "_build_core", future_incompatible_build)
    assert (
        native.load_registered_native_tm_document_artifact(
            output,
            project_root=root,
            expected_sha256=published.sha256,
        )
        == published.payload
    )

    # The loader must use commit-A producer bytes, not a later current config.
    geometry = root / "config/tables/geometry-v2.yaml"
    geometry.write_text("future: incompatible\n", encoding="utf-8")
    _run_git(root, "add", geometry.relative_to(root).as_posix())
    _run_git(root, "commit", "-m", "future config revision")
    assert (
        native.load_registered_native_tm_document_artifact(
            output, project_root=root, expected_sha256=published.sha256
        )
        == published.payload
    )


def test_strict_loader_rejects_semantic_tamper_even_with_new_trusted_hash(
    project_root: Path,
    tmp_path: Path,
):
    root, source, discovery, policy, discovery_sha = _make_registered_project(
        tmp_path, project_root, last_page_header=True
    )
    output = root / "output/development/native-tm-artifact.json"
    published = native.publish_registered_native_tm_document_artifact(
        root,
        source,
        discovery,
        discovery_sha,
        policy,
        "synthetic-native-tm-v1",
        output,
    )
    tampered = json.loads(output.read_text(encoding="utf-8"))
    tampered["pages"][0]["classification"] = "QUANTITATIVE_TM"
    output.write_bytes(_canonical_bytes(tampered))

    with pytest.raises(native.NativeTMDocumentArtifactError, match="deterministic replay"):
        native.load_registered_native_tm_document_artifact(
            output,
            project_root=root,
            expected_sha256=sha256_file(output),
        )
    assert published.payload["pages"][0]["classification"] == "NON_TM"


def test_unresolved_inter_table_context_blocks_full_completion():
    page = {
        "classification": "QUANTITATIVE_TM",
        "native_tm_regions": {
            "assessment_status": "ASSESSED",
            "regions": [
                {
                    "table_id": "table-1",
                    "page": 1,
                    "table_order": 0,
                    "region_bbox": {"x0": 0.0, "y0": 1.0, "x1": 10.0, "y1": 20.0},
                    "header_bindings": [],
                    "rows": [],
                    "grid_slots": [],
                    "scalar_disclosures": [],
                    "outside_financial_span_rows": [],
                    "unassigned_runs": [],
                },
                {
                    "table_id": "table-2",
                    "page": 1,
                    "table_order": 1,
                    "region_bbox": {"x0": 0.0, "y0": 30.0, "x1": 10.0, "y1": 40.0},
                    "header_bindings": [],
                    "rows": [],
                    "grid_slots": [],
                    "scalar_disclosures": [],
                    "outside_financial_span_rows": [],
                    "unassigned_runs": [],
                },
            ],
            "inter_table_contexts": [
                {
                    "page": 1,
                    "preceding_table_id": "table-1",
                    "following_table_id": "table-2",
                    "ownership_status": "UNRESOLVED_INTER_TABLE_OWNERSHIP",
                    "runs": [{"run_id": "context-run", "raw_text": "visible context"}],
                }
            ],
        },
    }
    inventory = native._table_inventory([page])

    assert inventory["table_count"] == 2
    assert inventory["unresolved_inter_table_context_count"] == 1
    assert inventory["all_table_ownership_bounded"] is False
    assert inventory["status"] == "PARTIAL_OR_UNRESOLVED_TABLE_INVENTORY"


def test_publication_is_exclusive_and_failed_postpublication_replay_rolls_back(
    project_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root, source, discovery, policy, discovery_sha = _make_registered_project(
        tmp_path, project_root, last_page_header=True
    )
    output = root / "output/development/native-tm-artifact.json"
    published = native.publish_registered_native_tm_document_artifact(
        root,
        source,
        discovery,
        discovery_sha,
        policy,
        "synthetic-native-tm-v1",
        output,
    )
    original = output.read_bytes()
    with pytest.raises(native.NativeTMDocumentArtifactError, match="overwrite"):
        native.publish_registered_native_tm_document_artifact(
            root,
            source,
            discovery,
            discovery_sha,
            policy,
            "synthetic-native-tm-v1",
            output,
        )
    assert output.read_bytes() == original
    assert published.size_bytes == len(original)

    rollback_output = root / "output/development/rollback.json"

    def reject_replay(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise native.NativeTMDocumentArtifactError("synthetic strict replay failure")

    monkeypatch.setattr(native, "load_registered_native_tm_document_artifact", reject_replay)
    with pytest.raises(native.NativeTMDocumentArtifactError, match="synthetic strict replay"):
        native.publish_registered_native_tm_document_artifact(
            root,
            source,
            discovery,
            discovery_sha,
            policy,
            "synthetic-native-tm-v1",
            rollback_output,
        )
    assert not rollback_output.exists()


def test_publication_creates_final_name_with_o_excl_and_rejects_final_symlink(
    project_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root, source, discovery, policy, discovery_sha = _make_registered_project(
        tmp_path, project_root, last_page_header=True
    )
    output = root / "output/development/direct-exclusive.json"
    original_open = native.os.open
    original_link = native.os.link
    final_flags: list[int] = []

    def recording_open(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        if path == output.name and kwargs.get("dir_fd") is not None:
            if flags & os.O_CREAT:
                final_flags.append(flags)
        return original_open(path, flags, *args, **kwargs)

    def forbidden_link(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("successful publication must not hard-link the final name")

    monkeypatch.setattr(native.os, "open", recording_open)
    monkeypatch.setattr(native.os, "link", forbidden_link)
    published = native.publish_registered_native_tm_document_artifact(
        root,
        source,
        discovery,
        discovery_sha,
        policy,
        "synthetic-native-tm-v1",
        output,
    )
    assert published.sha256 == sha256_file(output)
    assert len(final_flags) == 1
    assert final_flags[0] & os.O_CREAT
    assert final_flags[0] & os.O_EXCL

    monkeypatch.setattr(native.os, "open", original_open)
    monkeypatch.setattr(native.os, "link", original_link)
    symlink_output = root / "output/development/final-symlink.json"
    target = root / "output/development/symlink-target.json"
    target.write_bytes(b"foreign-target")
    symlink_output.symlink_to(target.name)
    with pytest.raises(native.NativeTMDocumentArtifactError, match="overwrite"):
        native.publish_registered_native_tm_document_artifact(
            root,
            source,
            discovery,
            discovery_sha,
            policy,
            "synthetic-native-tm-v1",
            symlink_output,
        )
    assert symlink_output.is_symlink()
    assert target.read_bytes() == b"foreign-target"


def test_postpublication_replay_race_preserves_foreign_replacement(
    project_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root, source, discovery, policy, discovery_sha = _make_registered_project(
        tmp_path, project_root, last_page_header=True
    )
    output = root / "output/development/replacement-race.json"
    replacement = b"foreign replacement survives rollback\n"

    def replace_then_reject(path: Path, **_kwargs: Any) -> dict[str, Any]:
        os.unlink(path)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        try:
            assert os.write(descriptor, replacement) == len(replacement)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        raise native.NativeTMDocumentArtifactError("synthetic replacement race")

    monkeypatch.setattr(native, "load_registered_native_tm_document_artifact", replace_then_reject)
    with pytest.raises(native.NativeTMDocumentArtifactError, match="replacement restored"):
        native.publish_registered_native_tm_document_artifact(
            root,
            source,
            discovery,
            discovery_sha,
            policy,
            "synthetic-native-tm-v1",
            output,
        )
    assert output.read_bytes() == replacement
    assert not list(output.parent.glob(f".{output.name}.rollback-*"))


def test_replay_temp_cleanup_failure_is_best_effort_after_success(
    project_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root, source, discovery, policy, discovery_sha = _make_registered_project(
        tmp_path, project_root, last_page_header=True
    )
    output = root / "output/development/cleanup-failure.json"
    original_rmtree = native.shutil.rmtree
    leaked: list[Path] = []

    def fail_cleanup(path: Any, *_args: Any, **_kwargs: Any) -> None:
        leaked.append(Path(path))
        raise OSError("synthetic cleanup failure")

    monkeypatch.setattr(native.shutil, "rmtree", fail_cleanup)
    try:
        published = native.publish_registered_native_tm_document_artifact(
            root,
            source,
            discovery,
            discovery_sha,
            policy,
            "synthetic-native-tm-v1",
            output,
        )
    finally:
        monkeypatch.setattr(native.shutil, "rmtree", original_rmtree)
        for path in leaked:
            original_rmtree(path, ignore_errors=True)
    assert output.is_file()
    assert published.sha256 == sha256_file(output)


def test_publication_rejects_output_outside_development_directory(
    project_root: Path,
    tmp_path: Path,
):
    root, source, discovery, policy, discovery_sha = _make_registered_project(
        tmp_path, project_root, last_page_header=True
    )
    forbidden = root / "output/calibration/native-tm-artifact.json"
    with pytest.raises(native.NativeTMDocumentArtifactError, match="output/development"):
        native.publish_registered_native_tm_document_artifact(
            root,
            source,
            discovery,
            discovery_sha,
            policy,
            "synthetic-native-tm-v1",
            forbidden,
        )
    assert not forbidden.exists()


@pytest.mark.parametrize(
    "forbidden_directory",
    ["role-a", "role_a", "schema", "review", "history", "reference", "holdout"],
)
def test_strict_loader_rejects_forbidden_artifact_relocation_before_subprocess(
    project_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    forbidden_directory: str,
):
    root, source, discovery, policy, discovery_sha = _make_registered_project(
        tmp_path, project_root, last_page_header=True
    )
    payload = _build(root, source, discovery, policy, discovery_sha)
    relocated = root / "output/development" / forbidden_directory / "native-tm-artifact.json"
    relocated.parent.mkdir(parents=True, exist_ok=True)
    relocated.write_bytes(_canonical_bytes(payload))

    def forbidden_subprocess(*_args: Any, **_kwargs: Any) -> bytes:
        raise AssertionError("forbidden artifact path reached producer replay")

    monkeypatch.setattr(native, "_producer_commit_replay", forbidden_subprocess)
    with pytest.raises(native.NativeTMDocumentArtifactError, match="path is forbidden"):
        native.load_registered_native_tm_document_artifact(
            relocated,
            project_root=root,
            expected_sha256=sha256_file(relocated),
        )


def test_strict_loader_allows_benign_canonical_development_relocation(
    project_root: Path,
    tmp_path: Path,
):
    root, source, discovery, policy, discovery_sha = _make_registered_project(
        tmp_path, project_root, last_page_header=True
    )
    payload = _build(root, source, discovery, policy, discovery_sha)
    relocated = root / "output/development/archive/native-tm-artifact.json"
    relocated.parent.mkdir(parents=True, exist_ok=True)
    relocated.write_bytes(_canonical_bytes(payload))

    assert (
        native.load_registered_native_tm_document_artifact(
            relocated,
            project_root=root,
            expected_sha256=sha256_file(relocated),
        )
        == payload
    )


def test_strict_loader_rejects_parent_symlink_alias(
    project_root: Path,
    tmp_path: Path,
):
    root, source, discovery, policy, discovery_sha = _make_registered_project(
        tmp_path, project_root, last_page_header=True
    )
    payload = _build(root, source, discovery, policy, discovery_sha)
    real_directory = root / "output/development/role-a"
    real_directory.mkdir(parents=True)
    real_artifact = real_directory / "native-tm-artifact.json"
    real_artifact.write_bytes(_canonical_bytes(payload))
    alias = root / "output/development/archive"
    alias.symlink_to(real_directory.name, target_is_directory=True)

    with pytest.raises(native.NativeTMDocumentArtifactError, match="symlink"):
        native.load_registered_native_tm_document_artifact(
            alias / real_artifact.name,
            project_root=root,
            expected_sha256=sha256_file(real_artifact),
        )


def test_strict_loader_rejects_final_symlink(
    project_root: Path,
    tmp_path: Path,
):
    root, source, discovery, policy, discovery_sha = _make_registered_project(
        tmp_path, project_root, last_page_header=True
    )
    payload = _build(root, source, discovery, policy, discovery_sha)
    storage = root / "output/development/storage"
    storage.mkdir(parents=True)
    real_artifact = storage / "native-tm-artifact.json"
    real_artifact.write_bytes(_canonical_bytes(payload))
    alias_directory = root / "output/development/archive"
    alias_directory.mkdir()
    alias = alias_directory / "native-tm-artifact.json"
    alias.symlink_to(Path("../storage") / real_artifact.name)

    with pytest.raises(native.NativeTMDocumentArtifactError, match="symlink"):
        native.load_registered_native_tm_document_artifact(
            alias,
            project_root=root,
            expected_sha256=sha256_file(real_artifact),
        )


def test_strict_loader_detects_name_replacement_during_replay(
    project_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root, source, discovery, policy, discovery_sha = _make_registered_project(
        tmp_path, project_root, last_page_header=True
    )
    payload = _build(root, source, discovery, policy, discovery_sha)
    artifact = root / "output/development/archive/native-tm-artifact.json"
    artifact.parent.mkdir(parents=True)
    encoded = _canonical_bytes(payload)
    artifact.write_bytes(encoded)
    replacement = b"foreign replacement during replay\n"

    def replace_name_during_replay(**_kwargs: Any) -> bytes:
        artifact.unlink()
        descriptor = os.open(artifact, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        try:
            assert os.write(descriptor, replacement) == len(replacement)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return encoded

    monkeypatch.setattr(native, "_producer_commit_replay", replace_name_during_replay)
    with pytest.raises(native.NativeTMDocumentArtifactError, match="changed during strict replay"):
        native.load_registered_native_tm_document_artifact(
            artifact,
            project_root=root,
            expected_sha256=sha256_bytes(encoded),
        )
    assert artifact.read_bytes() == replacement
