from __future__ import annotations

import importlib.util
import json
import sys
from hashlib import sha256
from pathlib import Path

import fitz

from bctc_ai.evaluation.gemini_json_first_page_render_v1 import render_full_pdf_page_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.storage.gemini_current_document_manifest_selection_v1 import (
    build_current_document_manifest_selection_v1,
)

_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts/experiments/build_gemini_json_first_whole_page_repair_status_v1.py"
)
_SPEC = importlib.util.spec_from_file_location("build_gemini_whole_page_repair_status", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
target = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = target
_SPEC.loader.exec_module(target)


def _cropped_pdf(path: Path) -> bytes:
    document = fitz.open()
    page = document.new_page(width=200, height=100)
    page.insert_text((70, 30), "MIDDLE", fontsize=10)
    page.set_cropbox(fitz.Rect(0, 10, 200, 90))
    document.save(path)
    document.close()
    return path.read_bytes()


def _fixture(tmp_path: Path):
    source_root = tmp_path / "source"
    artifact_root = tmp_path / "artifacts"
    source = source_root / "ACB/report.pdf"
    source.parent.mkdir(parents=True)
    raw = _cropped_pdf(source)
    document = {
        "page_count": 1,
        "relative_path": "ACB/report.pdf",
        "source_sha256": sha256(raw).hexdigest(),
        "source_size_bytes": len(raw),
    }
    planned = {
        "document": document,
        "document_plan_id": "gjfpdocv1:" + "a" * 64,
        "route": "OPENROUTER_VERTEX_FLEX",
        "tasks": [{"task_id": "task-1"}],
    }
    plan = {
        "corpus_plan_id": "gjfpcpv1:plan:" + "b" * 64,
        "documents": [planned],
        "format_version": "TEST",
        "policy": {"dpi": 300},
        "summary": {},
    }
    return source_root, artifact_root, source, document, plan


def test_status_marks_terminal_cropped_page_for_repair(monkeypatch, tmp_path) -> None:
    source_root, artifact_root, _source, _document, plan = _fixture(tmp_path)
    monkeypatch.setattr(
        target,
        "list_corpus_tasks_v1",
        lambda _ledger: [{"state": "SUCCEEDED", "task_id": "task-1"}],
    )
    status = target.build_whole_page_repair_status_v1(
        plan=plan,
        ledger=tmp_path / "ledger.sqlite3",
        source_root=source_root,
        artifact_root=artifact_root,
    )
    assert status["summary"]["affected_page_count"] == 1
    assert status["summary"]["disposition_counts"] == {"REPAIR_REQUIRED": 1}
    assert status["documents"][0]["affected_pages"] == [
        {"mode": "EXPANDED_DECLARED_MEDIA_BOX", "physical_page": 1}
    ]


def test_status_authenticates_current_image_manifest_and_writes_immutable_snapshot(
    monkeypatch, tmp_path
) -> None:
    source_root, artifact_root, source, document, plan = _fixture(tmp_path)
    monkeypatch.setattr(
        target,
        "list_corpus_tasks_v1",
        lambda _ledger: [{"state": "SUCCEEDED", "task_id": "task-1"}],
    )
    with fitz.open(source) as pdf:
        rendered = render_full_pdf_page_v1(
            pdf[0],
            physical_page=1,
            dpi=300,
            source_sha256=document["source_sha256"],
        )
    material = {
        "document": {
            "document_id": "gfpstorev1:document:" + "c" * 64,
            "source_logical_name": document["relative_path"],
            "source_sha256": document["source_sha256"],
            "source_size_bytes": document["source_size_bytes"],
        },
        "extraction_contract": {
            "page_image_sha256s": [
                {"image_sha256": rendered.page["image_sha256"], "physical_page": 1}
            ]
        },
        "format_version": "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V4",
        "page_count": 1,
        "pages": [
            {
                "image": {"sha256": rendered.page["image_sha256"]},
                "physical_page": 1,
                "status": "NO_RELEVANT_FINANCIAL_CONTENT",
            }
        ],
        "status_counts": {"NO_RELEVANT_FINANCIAL_CONTENT": 1},
        "totals": {"cost_usd": "0.001000000000"},
    }
    manifest = {
        **material,
        "document_manifest_id": "gfdmv1:manifest:" + canonical_json_sha256_v1(material),
    }
    manifest_path = artifact_root / "documents" / ("a" * 64) / "current-document-manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_bytes(canonical_json_bytes_v1(manifest) + b"\n")
    status = target.build_whole_page_repair_status_v1(
        plan=plan,
        ledger=tmp_path / "ledger.sqlite3",
        source_root=source_root,
        artifact_root=artifact_root,
    )
    assert status["summary"]["disposition_counts"] == {"COMPLETE_CURRENT_WHOLE_PAGE_MANIFEST": 1}
    assert status["documents"][0]["manifest_image_mismatch_pages"] == []
    output = target._write_snapshot(tmp_path / "status", status)
    assert output.stat().st_mode & 0o777 == 0o444
    assert output.stat().st_nlink == 1
    assert json.loads(output.read_bytes()) == status
    assert target._write_snapshot(tmp_path / "status", status) == output


def test_status_prefers_unique_append_only_manifest_selection_over_legacy(
    monkeypatch, tmp_path
) -> None:
    source_root, artifact_root, source, document, plan = _fixture(tmp_path)
    monkeypatch.setattr(
        target,
        "list_corpus_tasks_v1",
        lambda _ledger: [{"state": "SUCCEEDED", "task_id": "task-1"}],
    )
    with fitz.open(source) as pdf:
        rendered = render_full_pdf_page_v1(
            pdf[0], physical_page=1, dpi=300, source_sha256=document["source_sha256"]
        )
    material = {
        "document": {
            "document_id": "gfpstorev1:document:" + "c" * 64,
            "source_logical_name": document["relative_path"],
            "source_sha256": document["source_sha256"],
            "source_size_bytes": document["source_size_bytes"],
        },
        "extraction_contract": {
            "page_image_sha256s": [
                {"image_sha256": rendered.page["image_sha256"], "physical_page": 1}
            ]
        },
        "format_version": "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V4",
        "page_count": 1,
        "pages": [
            {
                "image": {"sha256": rendered.page["image_sha256"]},
                "physical_page": 1,
                "status": "PRIMARY_FINANCIAL_STATEMENT",
            }
        ],
        "status_counts": {"PRIMARY_FINANCIAL_STATEMENT": 1},
        "totals": {"cost_usd": "0.002000000000"},
    }
    manifest = {
        **material,
        "document_manifest_id": "gfdmv1:manifest:" + canonical_json_sha256_v1(material),
    }
    raw = canonical_json_bytes_v1(manifest) + b"\n"
    document_root = artifact_root / "documents" / ("a" * 64)
    relative = Path("current-document-manifests") / (
        manifest["document_manifest_id"].split(":", 2)[2] + ".json"
    )
    manifest_path = document_root / relative
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_bytes(raw)
    selection = build_current_document_manifest_selection_v1(
        document_plan_id=plan["documents"][0]["document_plan_id"],
        source_sha256=document["source_sha256"],
        document_manifest_id=manifest["document_manifest_id"],
        document_manifest_ref={
            "path": relative.as_posix(),
            "sha256": sha256(raw).hexdigest(),
            "size_bytes": len(raw),
        },
        page_image_frontier_sha256="d" * 64,
        page_prompt_frontier_sha256="e" * 64,
        prior_selection_ids=[],
    )
    selection_path = (
        document_root
        / "current-document-manifest-selections"
        / (selection["selection_id"].split(":", 2)[2] + ".json")
    )
    selection_path.parent.mkdir(parents=True)
    selection_path.write_bytes(canonical_json_bytes_v1(selection) + b"\n")
    status = target.build_whole_page_repair_status_v1(
        plan=plan,
        ledger=tmp_path / "ledger.sqlite3",
        source_root=source_root,
        artifact_root=artifact_root,
    )
    current = status["documents"][0]["current_manifest"]
    assert current["document_manifest_id"] == manifest["document_manifest_id"]
    assert current["selection_id"] == selection["selection_id"]
