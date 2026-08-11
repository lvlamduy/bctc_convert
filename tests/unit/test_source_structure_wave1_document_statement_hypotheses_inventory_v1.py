from __future__ import annotations

import ast
import os
import stat
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from test_source_structure_document_statement_hypotheses_v1 import (
    _complete_block,
    _ocr_terminal_projection,
    _policy,
)

from bctc_ai.source_structure import (
    wave1_document_statement_hypotheses_inventory_v1 as inventory_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.source_structure.document_statement_hypotheses_v1 import (
    build_document_statement_block_hypotheses_v1 as _real_build_document_hypotheses,
)
from bctc_ai.source_structure.finalized_v3_survey_stream_v1 import (
    AuthenticatedV3SurveyPage,
    FinalizedV3SurveyAuthority,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    PROJECT_ROOT / "src/bctc_ai/source_structure/"
    "wave1_document_statement_hypotheses_inventory_v1.py"
)


def _authority(projections: list[dict[str, Any]]) -> FinalizedV3SurveyAuthority:
    source_sha256 = projections[0]["source_locator"]["source_sha256"]
    return FinalizedV3SurveyAuthority(
        aggregate_artifact_sha256="1" * 64,
        aggregate_size_bytes=101,
        aggregate_identity_sha256="2" * 64,
        control_artifact_sha256="3" * 64,
        control_size_bytes=202,
        control_identity_sha256="4" * 64,
        sealed_plan_sha256="5" * 64,
        document_ids=(f"sha256:{source_sha256}",),
        document_count=1,
        request_count=len(projections),
        referenced_object_count=2 * len(projections),
    )


def _authority_payload(authority: FinalizedV3SurveyAuthority) -> dict[str, Any]:
    return {
        "aggregate_artifact_sha256": authority.aggregate_artifact_sha256,
        "aggregate_size_bytes": authority.aggregate_size_bytes,
        "aggregate_identity_sha256": authority.aggregate_identity_sha256,
        "control_artifact_sha256": authority.control_artifact_sha256,
        "control_size_bytes": authority.control_size_bytes,
        "control_identity_sha256": authority.control_identity_sha256,
        "sealed_plan_sha256": authority.sealed_plan_sha256,
        "document_ids": list(authority.document_ids),
        "document_count": authority.document_count,
        "request_count": authority.request_count,
        "referenced_object_count": authority.referenced_object_count,
    }


def _source_inventory(
    projections: list[dict[str, Any]],
    authority: FinalizedV3SurveyAuthority,
) -> dict[str, Any]:
    document_id = authority.document_ids[0]
    pages = []
    for ordinal, projection in enumerate(projections, start=1):
        pages.append(
            {
                "request_ordinal": ordinal,
                "document_id": document_id,
                "physical_page": projection["source_locator"]["physical_page"],
                "route": projection["route"],
                "status": projection["upstream_status"],
                "terminal": projection["terminal"],
                "projection_identity": projection["source_local_page_id"],
                "projection_sha256": canonical_json_sha256_v1(projection),
            }
        )
    return {
        "authority": _authority_payload(authority),
        "documents": [{"document_id": document_id, "page_count": len(pages)}],
        "pages": pages,
        "corpus_metrics": {
            "page_count": len(pages),
            "terminal_page_count": sum(page["terminal"] for page in pages),
        },
    }


def _producer() -> dict[str, Any]:
    records = [
        {
            "phase": "READ",
            "kind": "IMPLEMENTATION",
            "path": path.as_posix(),
            "sha256": f"{index + 1:x}"[-1] * 64,
            "size_bytes": index + 1,
        }
        for index, path in enumerate(sorted(set(inventory_v1._IMPLEMENTATION_PATHS)))
    ]
    return {
        "git": {"commit": "f" * 40, "dirty": False},
        "implementation_ledger": {
            "records": records,
            "sha256": canonical_json_sha256_v1(records),
        },
    }


class _FakeStream:
    def __init__(
        self,
        authority: FinalizedV3SurveyAuthority,
        pages: list[AuthenticatedV3SurveyPage],
    ) -> None:
        self.authority = authority
        self._pages = pages

    def __iter__(self):
        return iter(self._pages)


def _patch_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    projections: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, int]]:
    authority = _authority(projections)
    source_inventory = _source_inventory(projections, authority)
    producer = _producer()
    calls = {"projection": 0, "document": 0}
    pages = [
        AuthenticatedV3SurveyPage(
            page_record={
                "request_ordinal": ordinal,
                "document_id": authority.document_ids[0],
                "physical_page": projection["source_locator"]["physical_page"],
            },
            page_result={"synthetic": ordinal},
        )
        for ordinal, projection in enumerate(projections, start=1)
    ]

    @contextmanager
    def open_stream(_project_root: Path):
        yield _FakeStream(authority, pages)

    def project(*, page_record: dict[str, Any], page_result: dict[str, Any]):
        assert page_result == {"synthetic": page_record["request_ordinal"]}
        calls["projection"] += 1
        return deepcopy(projections[page_record["request_ordinal"] - 1])

    def build_document(page_projections, *, locator_policy):
        calls["document"] += 1
        return _real_build_document_hypotheses(
            page_projections,
            locator_policy=locator_policy,
        )

    monkeypatch.setattr(inventory_v1, "FINALIZED_V3_SURVEY_AUTHORITY_V1", authority)
    monkeypatch.setattr(inventory_v1, "open_finalized_v3_survey_stream_v1", open_stream)
    monkeypatch.setattr(inventory_v1, "project_authenticated_page_v2", project)
    monkeypatch.setattr(
        inventory_v1,
        "build_document_statement_block_hypotheses_v1",
        build_document,
    )
    monkeypatch.setattr(
        inventory_v1,
        "validate_wave1_source_inventory_v1",
        lambda value: deepcopy(value),
    )
    monkeypatch.setattr(
        inventory_v1,
        "_load_source_inventory",
        lambda _project_root: deepcopy(source_inventory),
    )
    monkeypatch.setattr(
        inventory_v1,
        "_load_locator_policy",
        lambda _project_root: deepcopy(_policy()),
    )
    monkeypatch.setattr(
        inventory_v1,
        "_producer_receipt",
        lambda _project_root: deepcopy(producer),
    )
    monkeypatch.setattr(
        inventory_v1.sentinel,
        "_implementation_ledger",
        lambda _project_root, _commit, _paths: deepcopy(producer["implementation_ledger"]),
    )
    return source_inventory, producer, calls


def _refresh_inventory_identity(value: dict[str, Any]) -> None:
    value["inventory_identity_sha256"] = canonical_json_sha256_v1(
        {key: item for key, item in value.items() if key != "inventory_identity_sha256"}
    )


def _refresh_document_identity(document: dict[str, Any]) -> None:
    document["document_hypotheses_identity"] = "ssdv1:document:" + canonical_json_sha256_v1(
        {key: item for key, item in document.items() if key != "document_hypotheses_identity"}
    )


def test_builder_exhaustively_retains_ranked_document_hypotheses_and_no_drop(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    projections = _complete_block()
    source_inventory, _producer_value, calls = _patch_pipeline(monkeypatch, projections)

    inventory = inventory_v1.build_wave1_document_statement_hypotheses_inventory_v1(tmp_path)

    assert calls == {"projection": 4, "document": 1}
    assert (
        inventory_v1.validate_wave1_document_statement_hypotheses_inventory_v1(
            inventory,
            project_root=tmp_path,
            source_inventory=source_inventory,
        )
        == inventory
    )
    assert inventory["authority"]["source_inventory"] == {
        "path": (
            "output/development/bank-corpus-survey-v1/wave-1-role-b-source-first-inventory-v1.json"
        ),
        "sha256": inventory_v1._SOURCE_INVENTORY_SHA256,
        "size_bytes": 1_920_845,
        "inventory_identity_sha256": inventory_v1._SOURCE_INVENTORY_IDENTITY_SHA256,
    }
    assert inventory["authority"]["locator_policy"]["used_policy_sha256"] == (
        "a55cb6fb9281fff6d20d7883b0fc761111a88406e6398d3ab8af8a9aefa61fe5"
    )
    assert inventory["corpus_metrics"] == {
        "document_count": 1,
        "page_count": 4,
        "terminal_page_count": 0,
        "page_hypothesis_count": 4,
        "page_disposition_count": 4,
        "block_hypothesis_count": 1,
        "candidate_document_count": 1,
        "unresolved_document_count": 0,
        "artifact_status_counts": {
            "CANDIDATES_EMITTED": 1,
            "UNRESOLVED_NO_COMPLETE_ORDERED_HYPOTHESIS": 0,
        },
        "page_disposition_counts": {
            "SUPPORTS_STATEMENT_BLOCK_HYPOTHESIS": 4,
            "RETAINED_UNRESOLVED": 0,
            "UPSTREAM_TERMINAL_UNRESOLVED": 0,
        },
        "family_hypothesis_counts": {
            "CDKT": 1,
            "KQKD": 1,
            "LCTT": 1,
            "TM": 1,
            "AUDIT_REPORT": 0,
            "TABLE_OF_CONTENTS": 0,
            "AMBIGUOUS": 0,
            "OTHER": 0,
            "UPSTREAM_TERMINAL": 0,
        },
        "evidence_code_counts": {
            "AMBIGUOUS_FAMILY_SIGNAL_HYPOTHESIS": 0,
            "AUDIT_SUPPRESSION_SIGNAL_HYPOTHESIS": 0,
            "CONTINUATION_MARKER_SIGNAL_HYPOTHESIS": 0,
            "FORM_FAMILY_SIGNAL_HYPOTHESIS": 4,
            "NO_FAMILY_SIGNAL_RETAINED": 0,
            "NUMERIC_TOKEN_DENSITY_SIGNAL_HYPOTHESIS": 3,
            "OFF_BALANCE_SIGNAL_HYPOTHESIS": 0,
            "TITLE_DISCRIMINATOR_SIGNAL_HYPOTHESIS": 0,
            "TITLE_SIGNAL_HYPOTHESIS": 0,
            "TOC_SUPPRESSION_SIGNAL_HYPOTHESIS": 0,
            "UPSTREAM_TERMINAL_BARRIER": 0,
        },
    }
    document = inventory["documents"][0]
    assert len(document["page_projection_bindings"]) == 4
    assert len(document["page_hypotheses"]) == 4
    assert len(document["page_dispositions"]) == 4
    assert len(document["block_hypotheses"]) == 1
    block = document["block_hypotheses"][0]
    assert block["family_sequence_hypothesis"] == ["CDKT", "KQKD", "LCTT"]
    assert all(
        disposition["block_hypothesis_ids"] == [block["block_hypothesis_id"]]
        for disposition in document["page_dispositions"]
    )
    payload = canonical_json_bytes_v1(inventory)
    assert payload.endswith(b"\n") and not payload.endswith(b"\n\n")
    for forbidden in (b"M\xe1\xba\xabu B02", b"M\xe1\xba\xabu B03", b"M\xe1\xba\xabu B04"):
        assert forbidden not in payload
    assert all(
        value is False
        for key, value in inventory["safety"].items()
        if key
        not in {
            "hypothesis_only",
            "validated_projection_primary_line_evidence_used",
            "compact_source_inventory_used_for_binding_only",
            "standalone_validator_is_structural_accounting_only",
            "downstream_exact_raw_artifact_sha256_pin_required",
        }
    )


def test_validator_rejects_compact_inventory_cross_binding_and_accounting_tamper(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    projections = _complete_block()
    source_inventory, _producer_value, _calls = _patch_pipeline(monkeypatch, projections)
    inventory = inventory_v1.build_wave1_document_statement_hypotheses_inventory_v1(tmp_path)

    detached_source = deepcopy(source_inventory)
    detached_source["pages"][0]["projection_sha256"] = "0" * 64
    with pytest.raises(
        inventory_v1.Wave1DocumentStatementHypothesesInventoryV1Error,
        match="differs from compact",
    ):
        inventory_v1.validate_wave1_document_statement_hypotheses_inventory_v1(
            inventory,
            project_root=tmp_path,
            source_inventory=detached_source,
        )

    drifted = deepcopy(inventory)
    drifted["corpus_metrics"]["block_hypothesis_count"] = 0
    _refresh_inventory_identity(drifted)
    with pytest.raises(
        inventory_v1.Wave1DocumentStatementHypothesesInventoryV1Error,
        match="corpus accounting",
    ):
        inventory_v1.validate_wave1_document_statement_hypotheses_inventory_v1(
            drifted,
            project_root=tmp_path,
            source_inventory=source_inventory,
        )

    missing_disposition = deepcopy(inventory)
    missing_disposition["documents"][0]["page_dispositions"].pop()
    _refresh_inventory_identity(missing_disposition)
    with pytest.raises(
        inventory_v1.Wave1DocumentStatementHypothesesInventoryV1Error,
        match="arrays",
    ):
        inventory_v1.validate_wave1_document_statement_hypotheses_inventory_v1(
            missing_disposition,
            project_root=tmp_path,
            source_inventory=source_inventory,
        )


def test_validator_replays_committed_ledger_and_block_score_rank_invariants(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    projections = _complete_block()
    source_inventory, _producer_value, _calls = _patch_pipeline(monkeypatch, projections)
    inventory = inventory_v1.build_wave1_document_statement_hypotheses_inventory_v1(tmp_path)

    forged_score = deepcopy(inventory)
    document = forged_score["documents"][0]
    block = document["block_hypotheses"][0]
    old_block_id = block["block_hypothesis_id"]
    block["diagnostic_score_components"]["form_signal_page_count"] += 1
    block["diagnostic_score"] += 2.0
    block_payload = {
        key: item for key, item in block.items() if key not in {"block_hypothesis_id", "rank"}
    }
    block["block_hypothesis_id"] = "ssdv1:block-hypothesis:" + canonical_json_sha256_v1(
        {
            "source_sha256": document["source_sha256"],
            "used_policy_sha256": inventory_v1._USED_POLICY_SHA256,
            **block_payload,
        }
    )
    for disposition in document["page_dispositions"]:
        disposition["block_hypothesis_ids"] = [
            block["block_hypothesis_id"] if item == old_block_id else item
            for item in disposition["block_hypothesis_ids"]
        ]
    _refresh_document_identity(document)
    _refresh_inventory_identity(forged_score)
    with pytest.raises(
        inventory_v1.Wave1DocumentStatementHypothesesInventoryV1Error,
        match="score/components",
    ):
        inventory_v1.validate_wave1_document_statement_hypotheses_inventory_v1(
            forged_score,
            project_root=tmp_path,
            source_inventory=source_inventory,
        )

    forged_ledger = deepcopy(inventory)
    ledger = forged_ledger["producer"]["implementation_ledger"]
    ledger["records"][0]["sha256"] = "0" * 64
    ledger["sha256"] = canonical_json_sha256_v1(ledger["records"])
    _refresh_inventory_identity(forged_ledger)
    with pytest.raises(
        inventory_v1.Wave1DocumentStatementHypothesesInventoryV1Error,
        match="committed implementation bytes",
    ):
        inventory_v1.validate_wave1_document_statement_hypotheses_inventory_v1(
            forged_ledger,
            project_root=tmp_path,
            source_inventory=source_inventory,
        )

    repeated = [*_complete_block(first_page=1), *_complete_block(first_page=5)]
    repeated_source, _producer_value, _calls = _patch_pipeline(monkeypatch, repeated)
    ranked = inventory_v1.build_wave1_document_statement_hypotheses_inventory_v1(tmp_path)
    forged_rank = deepcopy(ranked)
    ranked_document = forged_rank["documents"][0]
    ranked_document["block_hypotheses"].reverse()
    for rank, ranked_block in enumerate(ranked_document["block_hypotheses"], start=1):
        ranked_block["rank"] = rank
    _refresh_document_identity(ranked_document)
    _refresh_inventory_identity(forged_rank)
    with pytest.raises(
        inventory_v1.Wave1DocumentStatementHypothesesInventoryV1Error,
        match="rank order",
    ):
        inventory_v1.validate_wave1_document_statement_hypotheses_inventory_v1(
            forged_rank,
            project_root=tmp_path,
            source_inventory=repeated_source,
        )


def test_multiple_ranked_candidates_and_terminal_pages_are_retained_exactly(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repeated = [*_complete_block(first_page=1), *_complete_block(first_page=5)]
    source_inventory, _producer_value, calls = _patch_pipeline(monkeypatch, repeated)

    inventory = inventory_v1.build_wave1_document_statement_hypotheses_inventory_v1(tmp_path)

    assert calls == {"projection": 8, "document": 1}
    assert [block["rank"] for block in inventory["documents"][0]["block_hypotheses"]] == [1, 2]
    assert inventory["corpus_metrics"]["block_hypothesis_count"] == 2
    assert (
        inventory_v1.validate_wave1_document_statement_hypotheses_inventory_v1(
            inventory,
            project_root=tmp_path,
            source_inventory=source_inventory,
        )
        == inventory
    )

    terminal = [_ocr_terminal_projection(1)]
    terminal_source, _producer_value, terminal_calls = _patch_pipeline(monkeypatch, terminal)
    terminal_inventory = inventory_v1.build_wave1_document_statement_hypotheses_inventory_v1(
        tmp_path
    )
    assert terminal_calls == {"projection": 1, "document": 1}
    assert terminal_inventory["corpus_metrics"]["terminal_page_count"] == 1
    assert terminal_inventory["corpus_metrics"]["block_hypothesis_count"] == 0
    assert terminal_inventory["corpus_metrics"]["page_disposition_counts"] == {
        "SUPPORTS_STATEMENT_BLOCK_HYPOTHESIS": 0,
        "RETAINED_UNRESOLVED": 0,
        "UPSTREAM_TERMINAL_UNRESOLVED": 1,
    }
    assert (
        inventory_v1.validate_wave1_document_statement_hypotheses_inventory_v1(
            terminal_inventory,
            project_root=tmp_path,
            source_inventory=terminal_source,
        )
        == terminal_inventory
    )


def _patch_publisher(
    monkeypatch: pytest.MonkeyPatch,
    inventory: dict[str, Any],
    source_inventory: dict[str, Any],
) -> None:
    monkeypatch.setattr(
        inventory_v1,
        "build_wave1_document_statement_hypotheses_inventory_v1",
        lambda _project_root: deepcopy(inventory),
    )
    monkeypatch.setattr(
        inventory_v1,
        "_load_source_inventory",
        lambda _project_root: deepcopy(source_inventory),
    )
    monkeypatch.setattr(
        inventory_v1,
        "_load_locator_policy",
        lambda _project_root: deepcopy(_policy()),
    )
    monkeypatch.setattr(
        inventory_v1,
        "_producer_receipt",
        lambda _project_root: deepcopy(inventory["producer"]),
    )


def test_publisher_seals_canonical_bytes_via_exclusive_hardlink_without_overwrite(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    projections = _complete_block()
    source_inventory, _producer_value, _calls = _patch_pipeline(monkeypatch, projections)
    inventory = inventory_v1.build_wave1_document_statement_hypotheses_inventory_v1(tmp_path)
    parent = (
        tmp_path / inventory_v1.WAVE1_DOCUMENT_STATEMENT_HYPOTHESES_OUTPUT_RELATIVE_PATH_V1.parent
    )
    parent.mkdir(parents=True)
    _patch_publisher(monkeypatch, inventory, source_inventory)

    path, digest, size, identity = (
        inventory_v1.publish_wave1_document_statement_hypotheses_inventory_v1(tmp_path)
    )

    expected = canonical_json_bytes_v1(inventory)
    assert path.read_bytes() == expected
    assert digest == canonical_json_sha256_v1(inventory)
    assert size == len(expected)
    assert identity == inventory["inventory_identity_sha256"]
    published = path.stat()
    assert stat.S_IMODE(published.st_mode) == 0o444
    assert published.st_nlink == 1
    assert [item.name for item in parent.iterdir()] == [path.name]
    with pytest.raises(
        inventory_v1.Wave1DocumentStatementHypothesesInventoryV1Error,
        match="already exists",
    ):
        inventory_v1.publish_wave1_document_statement_hypotheses_inventory_v1(tmp_path)
    assert path.read_bytes() == expected


def test_publication_race_preserves_competitor_and_cleans_owned_temporary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    parent = (
        tmp_path / inventory_v1.WAVE1_DOCUMENT_STATEMENT_HYPOTHESES_OUTPUT_RELATIVE_PATH_V1.parent
    )
    parent.mkdir(parents=True)
    filename = inventory_v1.WAVE1_DOCUMENT_STATEMENT_HYPOTHESES_OUTPUT_RELATIVE_PATH_V1.name
    competitor = b"competitor\n"
    real_link = os.link
    raced = False

    def race_link(
        src: str,
        dst: str,
        *,
        src_dir_fd: int,
        dst_dir_fd: int,
        follow_symlinks: bool,
    ) -> None:
        nonlocal raced
        if not raced:
            raced = True
            descriptor = os.open(
                dst,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o444,
                dir_fd=dst_dir_fd,
            )
            try:
                os.write(descriptor, competitor)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        real_link(
            src,
            dst,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )

    monkeypatch.setattr(inventory_v1.os, "link", race_link)
    with pytest.raises(
        inventory_v1.Wave1DocumentStatementHypothesesInventoryV1Error,
        match="exclusive race",
    ):
        inventory_v1._publish_canonical_exclusive(tmp_path, b"{}\n")

    assert raced is True
    assert (parent / filename).read_bytes() == competitor
    assert sorted(item.name for item in parent.iterdir()) == [filename]


def test_prelink_write_failure_removes_owned_temporary_and_final(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    parent = (
        tmp_path / inventory_v1.WAVE1_DOCUMENT_STATEMENT_HYPOTHESES_OUTPUT_RELATIVE_PATH_V1.parent
    )
    parent.mkdir(parents=True)

    def fail_write(_descriptor: int, _payload: bytes) -> int:
        raise OSError("injected write failure")

    monkeypatch.setattr(inventory_v1.os, "write", fail_write)
    with pytest.raises(
        inventory_v1.Wave1DocumentStatementHypothesesInventoryV1Error,
        match="publication failed",
    ):
        inventory_v1._publish_canonical_exclusive(tmp_path, b"{}\n")
    assert list(parent.iterdir()) == []


def test_postlink_precommit_fsync_failure_rolls_back_owned_names(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    parent = (
        tmp_path / inventory_v1.WAVE1_DOCUMENT_STATEMENT_HYPOTHESES_OUTPUT_RELATIVE_PATH_V1.parent
    )
    parent.mkdir(parents=True)
    real_fsync = os.fsync
    failed = False

    def fail_first_directory_fsync(descriptor: int) -> None:
        nonlocal failed
        if not failed and stat.S_ISDIR(os.fstat(descriptor).st_mode):
            failed = True
            raise OSError("injected directory fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(inventory_v1.os, "fsync", fail_first_directory_fsync)
    with pytest.raises(
        inventory_v1.Wave1DocumentStatementHypothesesInventoryV1Error,
        match="publication failed",
    ):
        inventory_v1._publish_canonical_exclusive(tmp_path, b"{}\n")
    assert failed is True
    assert list(parent.iterdir()) == []


def test_module_boundary_has_no_geometry_build_role_a_pdf_model_ocr_or_replace_calls() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    call_names = {
        node.func.id
        if isinstance(node.func, ast.Name)
        else node.func.attr
        if isinstance(node.func, ast.Attribute)
        else ""
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    assert call_names.isdisjoint(
        {
            "generate_page_geometry_proposals_v1",
            "locate_statement_pages",
            "discover_statement_pages_v4",
            "render_composited_displayed_page",
            "read_causal_native_text_page",
            "replace",
        }
    )
    imports = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not any(
        fragment in module
        for module in imports
        for fragment in ("role_a", "schema", "mapping", "multisignal")
    )
    assert source.count("build_document_statement_block_hypotheses_v1(") == 1
    assert source.count("project_authenticated_page_v2(") == 1
    assert "os.replace" not in source
    assert all((PROJECT_ROOT / path).is_file() for path in inventory_v1._IMPLEMENTATION_PATHS)

    implementation_paths = set(inventory_v1._IMPLEMENTATION_PATHS)
    package_root = Path("src/bctc_ai")

    def with_package_initializers(relative: Path) -> set[Path]:
        resolved = {relative}
        parent = relative.parent
        while parent == package_root or package_root in parent.parents:
            initializer = parent / "__init__.py"
            if (PROJECT_ROOT / initializer).is_file():
                resolved.add(initializer)
            if parent == package_root:
                break
            parent = parent.parent
        return resolved

    start = Path("src/bctc_ai/source_structure/wave1_document_statement_hypotheses_inventory_v1.py")
    closure = with_package_initializers(start)
    pending = list(closure)

    def local_module_path(module: str) -> Path | None:
        if not module.startswith("bctc_ai"):
            return None
        candidate = Path("src", *module.split(".")).with_suffix(".py")
        if (PROJECT_ROOT / candidate).is_file():
            return candidate
        initializer = Path("src", *module.split("."), "__init__.py")
        return initializer if (PROJECT_ROOT / initializer).is_file() else None

    while pending:
        relative = pending.pop()
        local_tree = ast.parse((PROJECT_ROOT / relative).read_text(encoding="utf-8"))
        for node in ast.walk(local_tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules = [
                    node.module,
                    *(f"{node.module}.{alias.name}" for alias in node.names),
                ]
            for module in modules:
                candidate = local_module_path(module)
                if candidate is None:
                    continue
                for discovered in with_package_initializers(candidate) - closure:
                    closure.add(discovered)
                    pending.append(discovered)

    sealed_support = Path("src/bctc_ai/corpus/wave1_pre_ocr_structure.py")
    closure.update(with_package_initializers(sealed_support))

    assert closure == implementation_paths
    assert len(implementation_paths) == 35
    assert inventory_v1._FINALIZED_CORPUS_METRICS["document_count"] == 27
    assert inventory_v1._FINALIZED_CORPUS_METRICS["page_count"] == 1_449
    assert inventory_v1._FINALIZED_CORPUS_METRICS["terminal_page_count"] == 59
    assert inventory_v1._FINALIZED_CORPUS_METRICS["block_hypothesis_count"] == 24
