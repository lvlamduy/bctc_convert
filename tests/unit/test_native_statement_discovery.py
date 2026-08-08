from __future__ import annotations

import inspect
import json
import re
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import fitz
import pytest

import bctc_ai.document_phase.native_statement_discovery as native
from bctc_ai.cli.main import build_parser
from bctc_ai.core.contracts import BoundingBox
from bctc_ai.core.hashing import sha256_file
from bctc_ai.ocr.pdf_text import PDFTextPage, PDFWord

_PROJECT_FILES = (
    "config/document_phase/native-statement-discovery-v1.yaml",
    "config/document_phase/statement-discovery-v3.yaml",
    "config/document_phase/statement-discovery-v4.yaml",
    "config/document_phase/statement-locator-v1.yaml",
    "config/document_phase/statement-locator-v2.yaml",
    "config/ocr/native-text-quality-v2.yaml",
    "src/bctc_ai/ocr/pdf_text.py",
    "src/bctc_ai/ocr/native_text_quality_v2.py",
    "src/bctc_ai/document_phase/statement_locator.py",
    "src/bctc_ai/document_phase/statement_locator_v2.py",
    "src/bctc_ai/document_phase/multisignal_statement_discovery.py",
    "src/bctc_ai/document_phase/multisignal_statement_discovery_v4.py",
    "src/bctc_ai/document_phase/native_statement_discovery.py",
)
_CLEAN_GIT = {"commit": "a" * 40, "dirty": False}


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records
        ),
        encoding="utf-8",
    )


def _make_registered_project(
    tmp_path: Path,
    canonical_project_root: Path,
    *,
    role: str = "CALIBRATION",
) -> tuple[Path, Path, Path]:
    root = tmp_path / "project"
    for relative in _PROJECT_FILES:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(canonical_project_root / relative, destination)

    source = root / "data/incoming/unit-bank-2026.pdf"
    source.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open() as document:
        page = document.new_page(width=612, height=792)
        page.insert_text((36, 54), "REGISTERED FINANCIAL REPORT 2026")
        document.save(source)
    digest = sha256_file(source)
    source_relative = source.relative_to(root).as_posix()
    _write_jsonl(
        root / "data/registered/source_registry.jsonl",
        [
            {
                "bank": "UNIT",
                "document_id": f"sha256:{digest}",
                "hash_verified_stable": True,
                "immutable_copy": None,
                "kind": "PDF",
                "registered_at": "2026-08-08T00:00:00+00:00",
                "relative_path": source_relative,
                "sha256": digest,
                "size_bytes": source.stat().st_size,
                "source_mtime_ns": source.stat().st_mtime_ns,
                "state": "REGISTERED",
                "year": 2026,
            }
        ],
    )
    _write_jsonl(
        root / "data/registered/dataset_roles.jsonl",
        [
            {
                "assigned_at": "2026-08-08T00:00:00+00:00",
                "dataset_role": role,
                "document_id": f"sha256:{digest}",
                "immutable": True,
                "source_path": source_relative,
            }
        ],
    )
    return root, source, root / native.POLICY_RELATIVE_PATH


def _dict_nodes(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _dict_nodes(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _dict_nodes(child)


def _string_values(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _string_values(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _string_values(child)


def _assert_bound_identity(payload: dict[str, Any], relative_path: str, digest: str) -> None:
    matches = [
        node
        for node in _dict_nodes(payload)
        if node.get("path") == relative_path and node.get("sha256") == digest
    ]
    assert matches, f"payload does not bind {relative_path} to its exact byte hash"


def _word(
    text: str,
    bbox: tuple[float, float, float, float],
    *,
    block: int,
    line: int,
    word: int,
) -> PDFWord:
    return PDFWord(
        raw_text=text,
        normalized_text=text.casefold(),
        bbox_points=BoundingBox(*bbox),
        block_number=block,
        line_number=line,
        word_number=word,
    )


def _build(root: Path, source: Path, policy: Path) -> dict[str, Any]:
    return native.build_registered_native_statement_discovery(
        project_root=root,
        source_pdf=source,
        policy_path=policy,
        run_id="native-unit-001",
        git_state=dict(_CLEAN_GIT),
    )


def test_policy_and_payload_bind_exact_source_and_role_registry_bytes(
    tmp_path: Path,
    project_root: Path,
):
    root, source, policy_path = _make_registered_project(tmp_path, project_root)

    policy = native.load_native_statement_discovery_policy(policy_path, root)
    payload = _build(root, source, policy_path)

    assert policy["policy"] == "REGISTERED_NATIVE_TEXT_STATEMENT_DISCOVERY_V1"
    assert policy["source_registry"] == "data/registered/source_registry.jsonl"
    assert policy["dataset_role_registry"] == "data/registered/dataset_roles.jsonl"
    for relative in (
        "data/registered/source_registry.jsonl",
        "data/registered/dataset_roles.jsonl",
    ):
        _assert_bound_identity(payload, relative, sha256_file(root / relative))
    ledger = payload["inputs"]["runtime_read_ledger"]
    assert ledger
    assert all(set(record) == {"kind", "path", "sha256", "size_bytes"} for record in ledger)
    assert payload["run_id"] == "native-unit-001"
    assert payload["source"]["dataset_role"] == "CALIBRATION"
    assert payload["source"]["sha256"] == sha256_file(source)
    assert payload["authority"] == {
        "geometry": "PYMUPDF_NATIVE_TEXT_WORDS",
        "base_scoring_engine": "MULTISIGNAL_STATEMENT_DISCOVERY_V4",
        "base_geometry_authority": "PP_OCRV6_WORD_BOXES",
        "evidence_source": "PYMUPDF_NATIVE_TEXT_GEOMETRY",
        "override_scope": "GEOMETRY_SOURCE_ONLY",
        "semantic_reader": None,
    }


def test_registered_source_hash_mismatch_is_rejected(tmp_path: Path, project_root: Path):
    root, source, policy_path = _make_registered_project(tmp_path, project_root)
    registry = root / "data/registered/source_registry.jsonl"
    record = json.loads(registry.read_text(encoding="utf-8"))
    record["sha256"] = "0" * 64
    record["document_id"] = f"sha256:{record['sha256']}"
    _write_jsonl(registry, [record])

    with pytest.raises(
        native.NativeStatementDiscoveryError,
        match="registry identity drifted|register|hash|sha256",
    ):
        _build(root, source, policy_path)


def test_public_build_requires_the_exact_canonical_policy_path(
    tmp_path: Path,
    project_root: Path,
):
    root, source, policy_path = _make_registered_project(tmp_path, project_root)
    alternate = policy_path.with_name("native-statement-discovery-copy.yaml")
    shutil.copy2(policy_path, alternate)

    with pytest.raises(native.NativeStatementDiscoveryError, match="canonical|policy path"):
        _build(root, source, alternate)


def test_untouched_holdout_and_dirty_git_are_rejected(tmp_path: Path, project_root: Path):
    holdout_root, holdout_source, holdout_policy = _make_registered_project(
        tmp_path / "holdout",
        project_root,
        role="UNTOUCHED_HOLDOUT",
    )
    with pytest.raises(native.NativeStatementDiscoveryError, match="UNTOUCHED_HOLDOUT|holdout"):
        _build(holdout_root, holdout_source, holdout_policy)

    clean_root, clean_source, clean_policy = _make_registered_project(
        tmp_path / "dirty",
        project_root,
    )
    with pytest.raises(native.NativeStatementDiscoveryError, match="dirty|clean Git"):
        native.build_registered_native_statement_discovery(
            project_root=clean_root,
            source_pdf=clean_source,
            policy_path=clean_policy,
            run_id="native-unit-001",
            git_state={"commit": "a" * 40, "dirty": True},
        )


def test_native_words_are_grouped_and_ordered_into_lines_with_union_bbox():
    page = PDFTextPage(
        page=7,
        width_points=612,
        height_points=792,
        rotation=0,
        # Deliberately shuffled: adapter order must derive from visible native geometry.
        words=[
            _word("CÁO", (45, 10, 73, 22), block=0, line=0, word=1),
            _word("SAU", (12, 40, 36, 52), block=1, line=0, word=0),
            _word("HAI", (12, 70, 35, 82), block=0, line=1, word=0),
            _word("BÁO", (10, 9, 38, 21), block=0, line=0, word=0),
            _word("DÒNG", (42, 70, 78, 83), block=0, line=1, word=1),
        ],
        text_quality="USABLE_TEXT_LAYER",
        corruption_markers=(),
    )

    converted = native.pdf_text_page_to_ocr_page(page, usable=True)

    assert (converted.page, converted.width, converted.height) == (7, 612, 792)
    assert [(line.text, line.score) for line in converted.lines] == [
        ("BÁO CÁO", 1.0),
        ("SAU", 1.0),
        ("HAI DÒNG", 1.0),
    ]
    assert [line.bbox for line in converted.lines] == [
        (10, 9, 73, 22),
        (12, 40, 36, 52),
        (12, 70, 78, 83),
    ]


@pytest.mark.parametrize("status", ["CORRUPT_TEXT_LAYER", "NO_TEXT_LAYER"])
def test_non_usable_native_pages_contribute_no_statement_evidence(status: str):
    words = (
        []
        if status == "NO_TEXT_LAYER"
        else [_word("BÃ\u0081O CÃ\u0081O", (10, 10, 100, 25), block=0, line=0, word=0)]
    )
    page = PDFTextPage(
        page=2,
        width_points=612,
        height_points=792,
        rotation=0,
        words=words,
        text_quality=status,
        corruption_markers=() if not words else ("Ã\u0081",),
    )

    converted = native.pdf_text_page_to_ocr_page(page, usable=False)

    assert converted.page == 2
    assert converted.lines == ()


def test_build_masks_corrupt_and_no_text_pages_before_discovery(
    tmp_path: Path,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root, source, policy_path = _make_registered_project(tmp_path, project_root)
    pages = [
        PDFTextPage(
            page=1,
            width_points=612,
            height_points=792,
            rotation=0,
            words=[_word("VISIBLE", (10, 10, 60, 25), block=0, line=0, word=0)],
            text_quality="USABLE_TEXT_LAYER",
            corruption_markers=(),
        ),
        PDFTextPage(
            page=2,
            width_points=612,
            height_points=792,
            rotation=0,
            words=[_word("BÃ\u0081O", (10, 10, 80, 25), block=0, line=0, word=0)],
            text_quality="CORRUPT_TEXT_LAYER",
            corruption_markers=("�",),
        ),
        PDFTextPage(
            page=3,
            width_points=612,
            height_points=792,
            rotation=0,
            words=[],
            text_quality="NO_TEXT_LAYER",
            corruption_markers=(),
        ),
    ]
    captured = {"discovery_called": False}

    def fake_extract(*args: Any, **kwargs: Any) -> list[PDFTextPage]:
        return pages

    def fake_discover(geometry_pages: tuple[Any, ...], *args: Any, **kwargs: Any) -> dict[str, Any]:
        captured["discovery_called"] = True
        raise AssertionError("non-usable pages must be rejected before statement discovery")

    monkeypatch.setattr(native, "extract_pdf_text_v2", fake_extract)
    monkeypatch.setattr(native, "discover_statement_pages_v4", fake_discover)

    with pytest.raises(native.NativeStatementDiscoveryError, match="usable|OCR|required|text"):
        _build(root, source, policy_path)
    assert captured["discovery_called"] is False


def test_source_drift_during_extraction_is_rejected(
    tmp_path: Path,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root, source, policy_path = _make_registered_project(tmp_path, project_root)
    real_extract = native.extract_pdf_text_v2

    def extract_then_mutate(*args: Any, **kwargs: Any) -> list[PDFTextPage]:
        pages = real_extract(*args, **kwargs)
        with source.open("ab") as stream:
            stream.write(b"post-extraction-drift")
        return pages

    monkeypatch.setattr(native, "extract_pdf_text_v2", extract_then_mutate)

    with pytest.raises(native.NativeStatementDiscoveryError, match="changed during discovery"):
        _build(root, source, policy_path)


def test_payload_is_deterministic_and_input_ledger_contains_no_forbidden_paths(
    tmp_path: Path,
    project_root: Path,
):
    root, source, policy_path = _make_registered_project(tmp_path, project_root)

    first = _build(root, source, policy_path)
    second = _build(root, source, policy_path)

    assert first == second
    assert json.dumps(
        first, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ) == json.dumps(
        second,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    forbidden_fragments = (
        "/reference/",
        "/human_review/",
        "/human-review/",
        "/review/",
        "/history/",
        "/comparisons/",
        "/docs/experiments/",
        "/config/experiments/",
        "/output/holdout/",
    )
    path_values = [record["path"] for record in first["inputs"]["runtime_read_ledger"]] + [
        item["path"] for item in first["code"]["implementation"]
    ]
    path_values.append(first["source"]["relative_path"])
    for value in path_values:
        normalized = "/" + value.replace("\\", "/").casefold().lstrip("/")
        assert not Path(value).is_absolute()
        assert not re.match(r"^[a-zA-Z]:[\\/]", value)
        assert not any(fragment in normalized for fragment in forbidden_fragments)
    assert str(root.resolve()) not in json.dumps(first, ensure_ascii=False, sort_keys=True)
    assert first["isolation"]["historical_values_loaded"] is False
    assert first["isolation"]["prior_answer_artifacts_loaded"] is False
    assert first["isolation"]["role_a_outputs_loaded"] is False
    assert first["discovery"]["geometry_authority"] == "PYMUPDF_NATIVE_TEXT_WORDS"
    assert "PP_OCRV6_GEOMETRY" not in set(_string_values(first["discovery"]))


def test_publication_is_exclusive_and_never_overwrites(
    tmp_path: Path,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root, source, policy_path = _make_registered_project(tmp_path, project_root)
    output = root / "output/calibration/native-statement-discovery.json"
    monkeypatch.setattr(native, "_current_git_state", lambda _: dict(_CLEAN_GIT))

    assert (
        "git_state"
        not in inspect.signature(native.publish_registered_native_statement_discovery).parameters
    )

    forbidden_output = root / "docs/experiments/native-statement-discovery.json"
    with pytest.raises(native.NativeStatementDiscoveryError, match="must stay under"):
        native.publish_registered_native_statement_discovery(
            project_root=root,
            source_pdf=source,
            policy_path=policy_path,
            run_id="native-unit-001",
            output_path=forbidden_output,
        )
    assert not forbidden_output.exists()

    result = native.publish_registered_native_statement_discovery(
        project_root=root,
        source_pdf=source,
        policy_path=policy_path,
        run_id="native-unit-001",
        output_path=output,
    )

    assert result.path == output
    assert result.sha256 == sha256_file(output)
    assert json.loads(output.read_text(encoding="utf-8")) == result.payload
    original = output.read_bytes()
    with pytest.raises(native.NativeStatementDiscoveryError, match="exist|overwrite|exclusive"):
        native.publish_registered_native_statement_discovery(
            project_root=root,
            source_pdf=source,
            policy_path=policy_path,
            run_id="native-unit-001",
            output_path=output,
        )
    assert output.read_bytes() == original


def test_discover_statements_cli_defaults_to_canonical_policy():
    args = build_parser().parse_args(
        [
            "discover-statements",
            "--pdf",
            "data/incoming/report.pdf",
            "--output",
            "output/discovery.json",
        ]
    )

    assert args.command == "discover-statements"
    assert args.pdf == "data/incoming/report.pdf"
    assert args.output == "output/discovery.json"
    assert args.policy == str(native.POLICY_RELATIVE_PATH)
    assert args.run_id == "registered-native-statement-discovery-v1"
    assert args.handler.__name__ == "_run_discover_statements"


def test_discover_statements_cli_prints_project_relative_artifact_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    root = tmp_path.resolve()
    artifact = root / "output/development/run/result.json"

    def fake_publish(*args: Any, **kwargs: Any) -> native.NativeStatementDiscoveryPublication:
        return native.NativeStatementDiscoveryPublication(
            path=artifact,
            sha256="b" * 64,
            size_bytes=123,
            payload={"status": "ACCEPTED_NATIVE_TEXT_STATEMENT_DISCOVERY"},
        )

    monkeypatch.setattr(native, "publish_registered_native_statement_discovery", fake_publish)
    args = build_parser().parse_args(
        [
            "--project-root",
            str(root),
            "discover-statements",
            "--pdf",
            "data/report.pdf",
            "--output",
            "output/development/run/result.json",
        ]
    )

    assert args.handler(args) == 0
    output = capsys.readouterr().out
    assert "STATEMENT_DISCOVERY_ARTIFACT=output/development/run/result.json" in output
    assert str(root) not in output
