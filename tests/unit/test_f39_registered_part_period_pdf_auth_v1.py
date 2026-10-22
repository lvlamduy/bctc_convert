"""Filesystem/protocol tests; real Poppler byte replay has its separate witness."""

from __future__ import annotations

import importlib.util
import json
import struct
import subprocess
import zlib
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_gemini_json_income_tax_part_period_context_v1 import _fixture, _sha


def _module():
    path = Path(__file__).resolve().parents[2] / "scripts/experiments/f39_registered_part_period_pdf_auth_v1.py"
    spec = importlib.util.spec_from_file_location("f39_part_pdf_auth_test_subject", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_ref(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {"path": path.as_posix(), "sha256": sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _json(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _png(seed):
    def chunk(kind, raw):
        return struct.pack(">I", len(raw)) + kind + raw + struct.pack(">I", zlib.crc32(kind + raw))

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress((b"\0" + bytes([seed, 1, 2]) * 2) * 2)) + chunk(b"IEND", b""))


@pytest.fixture
def auth_fixture(tmp_path, monkeypatch):
    module = _module()
    repo, evidence, tools, pdf_root = (tmp_path / name for name in ("repo", "evidence", "tools", "pdfs"))
    for directory in (repo, evidence, tools, pdf_root):
        directory.mkdir()
    monkeypatch.setattr(module, "_REPO_ROOT", repo)
    monkeypatch.setattr(module, "_EVIDENCE_ROOTS", (evidence,))
    monkeypatch.setattr(module, "_RENDERER_ROOTS", (tools,))
    records, registry = _fixture()
    context = registry["contexts"][0]
    pdf_path = pdf_root / "reports/2026/source.pdf"
    pdf_ref = _write_ref(pdf_path, b"%PDF-1.4\nSYNTHETIC_PROTOCOL_FIXTURE_NOT_A_PDF_SOURCE_AUTHORITY\n")
    source = {"source_logical_name": "reports/2026/source.pdf", "source_sha256": pdf_ref["sha256"],
              "source_size_bytes": pdf_ref["size_bytes"]}
    document_id = "gfpstorev1:document:" + _sha(source)
    context["document_id"] = document_id
    context["pdf_source"] = {"logical_name": source["source_logical_name"], "sha256": source["source_sha256"],
                             "size_bytes": source["source_size_bytes"]}
    context["review_evidence"]["manual_review_ref"] = _write_ref(
        evidence / "review.json", _json({"schema": "synthetic-manual-review-fixture", "status": "NOT_REGISTERED_NOT_ACTIVE"}))
    visual_refs, pngs, render_files, png_files = [], {}, [], []
    for physical in (4, 5):
        image = _png(physical)
        png_file, render_file = evidence / f"page-{physical}.png", evidence / f"render-{physical}.json"
        png_ref = _write_ref(png_file, image)
        render = {"schema": "bctc-ai-f39-independent-pdf-review-render-v1", "renderer": "Poppler pdftoppm",
                  "physical_page": physical, "source": context["pdf_source"], "source_bytes_unchanged": True,
                  "source_spec_sha256": module._ORIGINAL_REPAIR_SHA, "family_terminal_claimed": False,
                  "registered_PyMuPDF_repair_pixels_replaced": False, "visual_review_performed": False,
                  "repair_id": None, "image": png_ref,
                  "diagnostic_ref": {"path": "/historical/diagnostic.json", "sha256": "a" * 64},
                  "command": ["pdftoppm", "-f", str(physical), "-l", str(physical), "-singlefile", "-r", "144", "-png",
                              pdf_path.as_posix(), png_file.with_suffix("").as_posix()]}
        render_ref = _write_ref(render_file, _json(render))
        visual_refs.append({"png_ref": png_ref, "render_receipt_ref": render_ref, "physical_page": physical,
                            "renderer_version": "Poppler pdftoppm 24.02.0", "dpi": 144, "width_pixels": 2, "height_pixels": 2})
        pngs[physical] = image
        png_files.append(png_file)
        render_files.append(render_file)
    context["review_evidence"]["visual_refs"] = visual_refs
    registry_path = repo / "config/families/registry.json"
    registry_ref = _write_ref(registry_path, _json(registry))
    registry_ref["path"] = "config/families/registry.json"
    compiled = {"income_tax_part_period_registry": deepcopy(registry), "income_tax_part_period_registry_ref": deepcopy(registry_ref)}
    document = {"manifest": {"document": {"document_id": document_id, **source},
                             "pages": [{"page_json_version_id": record["page_json_version_id"],
                                        "physical_page": record["physical_page"]} for record in records]},
                "ids": [record["page_json_version_id"] for record in records]}
    loaded = []
    for record in records:
        page = record["page_json"]
        loaded.append({"page_json_version_id": record["page_json_version_id"], "physical_page": record["physical_page"],
                       "source_logical_name": source["source_logical_name"], "source_sha256": source["source_sha256"],
                       "page_json": deepcopy(page), "source_json_replay_receipt": {
                           "schema": "bctc-ai-f39-original-source-json-replay-v1", "classification": "EXACT_REPLAY",
                           "changed_tables": [], "mapping_input": "ORIGINAL_STORED_JSON_UNMODIFIED",
                           "all_original_cells_and_ordinals_retained": True, "validated_json_sha256": _sha(page),
                           "canonical_json_sha256": sha256(_json(page) + b"\n").hexdigest()}})
    tool = tools / "pdftoppm"
    tool.write_bytes(b"synthetic renderer executable bytes; subprocess protocol is mocked")
    monkeypatch.setattr(module.shutil, "which", lambda name: str(tool) if name == "pdftoppm" else None)
    state = {"commands": [], "version": b"pdftoppm version 24.02.0\n", "suffix": b"", "fail": False,
             "after_render": None, "loader_calls": 0}

    def run(command, *, capture_output, check, timeout):
        assert capture_output is True and check is True and timeout == 60
        state["commands"].append(list(command))
        if state["fail"]:
            raise subprocess.CalledProcessError(1, command)
        if command[1:] == ["-v"]:
            return subprocess.CompletedProcess(command, 0, b"", state["version"])
        physical = int(command[command.index("-f") + 1])
        if state["after_render"] is not None:
            callback = state["after_render"]
            state["after_render"] = None
            callback()
        return subprocess.CompletedProcess(command, 0, pngs[physical] + state["suffix"], b"")

    monkeypatch.setattr(module.subprocess, "run", run)

    def loader():
        state["loader_calls"] += 1
        return deepcopy(registry), deepcopy(registry_ref)

    return SimpleNamespace(module=module, document=document, loaded=loaded, compiled=compiled, registry=registry,
                           registry_ref=registry_ref, registry_path=registry_path, pdf_root=pdf_root, pdf_path=pdf_path,
                           png_files=png_files, render_files=render_files, manual_path=evidence / "review.json",
                           renderer=tool, state=state, loader=loader)


def _authenticate(fixture, root=True):
    return fixture.module.authenticate_registered_part_period_pdf_v1(
        fixture.document, fixture.loaded, fixture.compiled, fixture.pdf_root if root else None,
        registry_loader=fixture.loader)


def _reseal(receipt):
    receipt["receipt_id"] = "f39partpdfv1:" + sha256(_json({key: value for key, value in receipt.items() if key != "receipt_id"})).hexdigest()


def test_warm_and_cold_each_render_fresh_bytes_without_output_prefix(auth_fixture):
    f = auth_fixture
    before = deepcopy((f.document, f.loaded, f.compiled))
    warm, cold = _authenticate(f), _authenticate(f)
    assert warm == cold and len(warm) == 1
    renders = [command for command in f.state["commands"] if "-f" in command]
    assert len(renders) == 4
    assert [command[2] for command in renders] == ["4", "5", "4", "5"]
    assert all(len(command) == 10 and command[-1] == f.pdf_path.as_posix() for command in renders)
    assert all("-" not in command for command in renders)
    assert f.state["loader_calls"] >= 4
    assert warm[0]["complete"] is True
    assert warm[0]["manual_review_interpretation_replayed"] is False
    assert all(value is False for value in warm[0]["permission_grants"].values())
    assert (f.document, f.loaded, f.compiled) == before


def test_applicable_context_cannot_silently_skip_missing_pdf_root(auth_fixture):
    with pytest.raises(auth_fixture.module.GeminiIncomeTaxPartPeriodPdfAuthV1Error, match="requires source_pdf_root"):
        _authenticate(auth_fixture, root=False)


def test_unregistered_source_retains_legacy_no_pdf_no_renderer_behavior(auth_fixture):
    f = auth_fixture
    source = f.document["manifest"]["document"]
    source.update(source_logical_name="unregistered/source.pdf", source_sha256="f" * 64)
    source["document_id"] = "gfpstorev1:document:" + _sha({key: source[key] for key in (
        "source_logical_name", "source_sha256", "source_size_bytes")})
    assert _authenticate(f, root=False) == []
    assert f.state["commands"] == []


@pytest.mark.parametrize("target", ["registry", "pdf", "png", "render", "manual", "renderer"])
def test_every_input_byte_drift_is_rejected_at_exit_barrier(auth_fixture, target):
    f = auth_fixture
    receipts = _authenticate(f)
    path = {"registry": f.registry_path, "pdf": f.pdf_path, "png": f.png_files[0],
            "render": f.render_files[0], "manual": f.manual_path, "renderer": f.renderer}[target]
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(f.module.GeminiIncomeTaxPartPeriodPdfAuthV1Error):
        f.module.recheck_registered_part_period_pdf_v1(receipts, registry_loader=f.loader)


@pytest.mark.parametrize("target", ["pdf", "png", "manual", "registry"])
def test_drift_during_render_cannot_escape_authentication_return(auth_fixture, target):
    f = auth_fixture
    path = {"pdf": f.pdf_path, "png": f.png_files[0], "manual": f.manual_path, "registry": f.registry_path}[target]
    f.state["after_render"] = lambda: path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(f.module.GeminiIncomeTaxPartPeriodPdfAuthV1Error):
        _authenticate(f)


@pytest.mark.parametrize("mutation", ["bad_stdout", "bad_version", "process_failure", "compiled_registry", "compiled_ref",
                                    "source_identity", "loaded_page", "loaded_metadata", "omitted_loaded", "reversed_loaded",
                                    "blob_domain", "validated_domain", "nonoriginal_replay"])
def test_fresh_runtime_source_and_protocol_failures_do_not_return_approval(auth_fixture, mutation):
    f = auth_fixture
    if mutation == "bad_stdout":
        f.state["suffix"] = b"not-registered-png-bytes"
    elif mutation == "bad_version":
        f.state["version"] = b"pdftoppm version 99.0\n"
    elif mutation == "process_failure":
        f.state["fail"] = True
    elif mutation == "compiled_registry":
        f.compiled["income_tax_part_period_registry"]["contexts"][0]["review_evidence"]["no_reset_observation_exact"] += " forged"
    elif mutation == "compiled_ref":
        f.compiled["income_tax_part_period_registry_ref"]["sha256"] = "f" * 64
    elif mutation == "source_identity":
        f.document["manifest"]["document"]["source_sha256"] = "f" * 64
    elif mutation == "loaded_page":
        f.loaded[-1]["page_json"]["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "0"
    elif mutation == "loaded_metadata":
        f.loaded[-1]["physical_page"] += 1
    elif mutation == "omitted_loaded":
        f.loaded.pop()
    elif mutation == "reversed_loaded":
        f.loaded.reverse()
    elif mutation == "blob_domain":
        f.loaded[0]["source_json_replay_receipt"]["canonical_json_sha256"] = _sha(f.loaded[0]["page_json"])
    elif mutation == "validated_domain":
        f.loaded[0]["source_json_replay_receipt"]["validated_json_sha256"] = "f" * 64
    else:
        f.loaded[0]["source_json_replay_receipt"]["mapping_input"] = "VALIDATED_COPY"
    with pytest.raises(f.module.GeminiIncomeTaxPartPeriodPdfAuthV1Error):
        _authenticate(f)


@pytest.mark.parametrize("mutation", ["permission", "extra_approval", "stdout_hash", "file_prefix", "visual_page", "input_axis",
                                    "detached_pdf", "detached_manual", "detached_png", "missing_visual", "duplicate_receipt"])
def test_self_resealed_receipt_cannot_detach_approved_registry_inputs(auth_fixture, mutation):
    f = auth_fixture
    receipts = _authenticate(f)
    receipt = receipts[0]
    if mutation == "permission":
        receipt["permission_grants"]["family_acceptance"] = True
    elif mutation == "extra_approval":
        receipt["approved"] = True
    elif mutation == "stdout_hash":
        receipt["visual_receipts"][0]["stdout_sha256"] = "f" * 64
    elif mutation == "file_prefix":
        receipt["visual_receipts"][0]["stdout_render_command"].append("-")
    elif mutation == "visual_page":
        receipt["visual_receipts"][0]["physical_page"] = True
    elif mutation == "input_axis":
        receipt["input_refs"].reverse()
    elif mutation == "detached_pdf":
        receipt["pdf_ref"]["path"] = f.png_files[0].as_posix()
    elif mutation == "detached_manual":
        receipt["manual_review_ref"]["sha256"] = "f" * 64
    elif mutation == "detached_png":
        receipt["visual_receipts"][0]["png_ref"]["path"] = f.manual_path.as_posix()
    elif mutation == "missing_visual":
        receipt["visual_receipts"].pop()
    else:
        receipts.append(deepcopy(receipt))
    _reseal(receipt)
    with pytest.raises(f.module.GeminiIncomeTaxPartPeriodPdfAuthV1Error):
        f.module.recheck_registered_part_period_pdf_v1(receipts, registry_loader=f.loader)


def test_warm_success_does_not_admit_cold_with_changed_pdf(auth_fixture):
    f = auth_fixture
    warm = _authenticate(f)
    before = deepcopy(warm)
    f.pdf_path.write_bytes(f.pdf_path.read_bytes() + b"changed-before-independent-cold")
    with pytest.raises(f.module.GeminiIncomeTaxPartPeriodPdfAuthV1Error):
        _authenticate(f)
    assert warm == before


def test_recheck_does_not_represent_a_new_render_or_acceptance(auth_fixture):
    f = auth_fixture
    receipts = _authenticate(f)
    render_count = sum("-f" in command for command in f.state["commands"])
    f.module.recheck_registered_part_period_pdf_v1(receipts, registry_loader=f.loader)
    assert sum("-f" in command for command in f.state["commands"]) == render_count
    assert receipts[0]["recheck_is_not_a_substitute_for_fresh_warm_and_cold_authentication"] is True
