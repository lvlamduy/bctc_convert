"""Synthetic filesystem/subprocess protocol tests, not actual PDF acceptance."""
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
from test_gemini_json_income_tax_section_caption_repair_v1 import fixture as clone_fixture


def _json(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _hash(value):
    return sha256(_json(value)).hexdigest()


def _write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {"path": path.as_posix(), "sha256": sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _png(height=2):
    def chunk(kind, raw):
        return struct.pack(">I", len(raw)) + kind + raw + struct.pack(">I", zlib.crc32(kind + raw))

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress((b"\0" + bytes([1, 2, 3]) * 2) * height)) + chunk(b"IEND", b""))


@pytest.fixture
def auth_fixture(tmp_path, monkeypatch):
    actual_repo = Path(__file__).resolve().parents[2]
    experiments = actual_repo / "scripts/experiments"
    monkeypatch.syspath_prepend(str(experiments))
    specification = importlib.util.spec_from_file_location(
        "f39_caption_pdf_test_subject", experiments / "f39_registered_section_caption_pdf_auth_v1.py")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    repo, evidence, restore, pdf_root, tools = (tmp_path / name for name in (
        "repo", "evidence", "restore", "pdfs", "tools"))
    for directory in (repo, evidence, restore, pdf_root, tools):
        directory.mkdir()
    monkeypatch.setattr(module, "_REPO", repo)
    monkeypatch.setattr(module, "_EVIDENCE", (evidence,))
    monkeypatch.setattr(module, "_RESTORE", restore)
    monkeypatch.setattr(module.io_auth, "_RENDERER_ROOTS", (tools,))
    records, registry, _ = clone_fixture()
    record, source = records[0], registry["sources"][0]
    pdf_ref = _write(pdf_root / "synthetic/report.pdf", b"%PDF synthetic protocol fixture; not render authority\n")
    pdf = {"logical_name": "synthetic/report.pdf", "sha256": pdf_ref["sha256"], "size_bytes": pdf_ref["size_bytes"]}
    source["pdf_source"] = deepcopy(pdf)
    source["document_id"] = module.clone_core._document_id(pdf)
    record.update(document_id=source["document_id"], source_sha256=pdf["sha256"],
                  source_logical_name=pdf["logical_name"], document_ordinal=37, selected_page_ordinal=1)
    repair = source["repairs"][0]
    repair["locator"]["selected_page_ordinal"] = 1
    full_ref, crop_ref = _write(evidence / "full.png", _png()), _write(evidence / "crop.png", _png(1))
    crop = {"png_ref": crop_ref, "width_pixels": 2, "height_pixels": 1, "crop_box_pixels": [0, 0, 2, 1],
            "rgb_sha256": sha256(bytes([1, 2, 3]) * 2).hexdigest(), "rgb_size_bytes": 6, "mode": "RGB"}
    renderer = tools / "pdftoppm"
    renderer.write_bytes(b"synthetic subprocess protocol; not a genuine renderer executable")
    command = [renderer.as_posix(), "-f", "4", "-l", "4", "-singlefile", "-r", "200", "-png", pdf_ref["path"]]
    candidate = {
        "schema": "bctc-ai-f39-registered-caption-pixel-candidate-v1",
        "status": "PASS_PIXEL_CANDIDATE_ONLY_NOT_APPROVAL_NOT_REPAIR_NOT_ACCEPTANCE", "errors": [], "exit_code": 0,
        "physical_page": 4, "full_page_exact_historical_png_bytes": True, "production_permission_active": False,
        "registered_caption_repair_applied": False, "source_json_modified": False, "ocr_performed": False,
        "text_extraction_performed": False, "candidate_crop": deepcopy(crop), "render_command": command,
        "render_stdout_ref": full_ref, "original_pdf_ref": pdf_ref,
        "original_selected_source_metadata": {"page_json_version_id": record["page_json_version_id"],
            "physical_page": 4, "source_sha256": pdf["sha256"], "section_title_exact": repair["before_exact"],
            "table_title_exact": None},
    }
    candidate_ref = _write(evidence / "candidate.json", _json(candidate))
    manual = {
        "schema": "bctc-ai-f39-section-caption-fresh-pixel-manual-review-v1",
        "status": "VERIFIED_OWN_PAGE_CAPTION_TRANSCRIPTION_DISCREPANCY_NOT_REGISTERED_REPAIR_NOT_ACCEPTANCE",
        "source_pdf": {**pdf, "physical_page": 4}, "pixel_candidate_ref": candidate_ref,
        "capabilities": {"registered_registry_approval_granted": False},
        "manual_visual_finding": {"historically_selected_section_title_exact": repair["before_exact"],
            "own_page_heading_exact": repair["after_exact"], "proposed_pointer_kind": "SECTION.title_exact",
            "heading_on_own_page_not_inferred_from_filename_neighbour_or_equation": True,
            "caption_clear_in_whole_page_and_crop": True, "no_table_title_to_create": True,
            "historical_table_title_exact": None},
        "images_actually_viewed_by_reviewer": {
            "fresh_whole_page": {**full_ref, "render_dpi": 200, "width_pixels": 2, "height_pixels": 2},
            "fresh_header_crop": {**crop_ref, **{key: value for key, value in crop.items() if key != "png_ref"},
                                  "crop_is_reviewer_selected_not_ocr_or_mapping_geometry": True}},
    }
    manual_ref = _write(evidence / "manual.json", _json(manual))
    repair["review_evidence"] = {"manual_review_ref": manual_ref, "pixel_candidate_ref": candidate_ref}
    legacy_raw = (actual_repo / "config/families/tm-income-tax-source-repair-v1.json").read_bytes()
    legacy_spec = json.loads(legacy_raw)
    legacy_ref = _write(repo / "legacy.json", legacy_raw)
    object_key = "bctc-ai/objects/sha256/" + pdf["sha256"][:2] + "/" + pdf["sha256"]
    parent_key, coverage_key, migration_key = ("bctc-ai/synthetic/" + name for name in (
        "parent.json", "coverage.json", "migration.json"))
    parent = {"files": [{"asset_class": "source_pdf", "logical_path": pdf["logical_name"],
                          "object_key": object_key, "sha256": pdf["sha256"], "size_bytes": pdf["size_bytes"]}],
              "objects": [{"disposition": "UPLOADED", "object_key": object_key,
                           "sha256": pdf["sha256"], "size_bytes": pdf["size_bytes"], "version_id": "PDF_VERSION"}]}
    parent_ref = _write(restore / "parent.json", _json(parent))
    parent_binding = {"manifest_key": parent_key, "manifest_version_id": "PARENT_VERSION",
                      "manifest_sha256": parent_ref["sha256"], "manifest_size_bytes": parent_ref["size_bytes"]}
    coverage = {"schema": "bctc-ai-machine-migration-source-coverage-v1", "existing_parent_snapshot": parent_binding}
    coverage_ref = _write(restore / "coverage.json", _json(coverage))
    migration = {"schema": "bctc-ai-machine-migration-manifest-v1", "manifest_self": {"key": migration_key},
                 "source_pdf_backup": {"coverage_manifest": {"key": coverage_key, "version_id": "COVERAGE_VERSION",
                     "sha256": coverage_ref["sha256"], "size_bytes": coverage_ref["size_bytes"]},
                     "coverage_groups": {"existing_parent_snapshot": parent_binding}}}
    migration_ref = _write(restore / "migration.json", _json(migration))
    # Test-only synthetic independently pinned authorities, not production grants.
    for field, ref in (("_MIGRATION_SHA", migration_ref), ("_COVERAGE_SHA", coverage_ref), ("_PARENT_SHA", parent_ref)):
        monkeypatch.setattr(module, field, ref["sha256"])

    def authority(ref, key, version):
        return {"local_ref": ref, "s3": {"bucket": "test-s3-duylv", "key": key, "version_id": version}}

    lineage = {"document_id": source["document_id"], "pdf_source": pdf,
               "restore_authorities": {"migration_manifest": authority(migration_ref, migration_key, "MIGRATION_VERSION"),
                   "coverage_manifest": authority(coverage_ref, coverage_key, "COVERAGE_VERSION"),
                   "parent_snapshot_manifest": authority(parent_ref, parent_key, "PARENT_VERSION")},
               "pdf_object": {"bucket": "test-s3-duylv", "key": object_key, "version_id": "PDF_VERSION",
                              "sha256": pdf["sha256"], "size_bytes": pdf["size_bytes"]},
               "repair_evidence": [{"repair_id": repair["repair_id"], **repair["review_evidence"]}]}
    envelope = {"format_version": module._ENVELOPE, "family_id": "INCOME_TAX", "clone_registry": registry,
                "legacy_source_repair_spec_ref": legacy_ref, "source_version_lineages": [lineage]}
    envelope_path = repo / "envelope.json"
    envelope_ref = _write(envelope_path, _json(envelope))
    compiled = {"income_tax_section_caption_auth_envelope": deepcopy(envelope),
                "income_tax_section_caption_auth_envelope_ref": deepcopy(envelope_ref),
                "income_tax_source_repairs": deepcopy(legacy_spec["repairs"])}
    source_document = {"document_id": source["document_id"], "source_logical_name": pdf["logical_name"],
                       "source_sha256": pdf["sha256"], "source_size_bytes": pdf["size_bytes"]}
    document = {"manifest": {"document": source_document, "pages": [{"physical_page": 4,
                    "page_json_version_id": record["page_json_version_id"]}]}, "ids": [record["page_json_version_id"]]}
    item = {"physical_page": 4, "page_json_version_id": record["page_json_version_id"],
            "source_logical_name": pdf["logical_name"], "source_sha256": pdf["sha256"],
            "page_json": deepcopy(record["page_json"])}
    replay = {"schema": "bctc-ai-f39-original-source-json-replay-v1", "mapping_input": "ORIGINAL_STORED_JSON_UNMODIFIED",
              "all_original_cells_and_ordinals_retained": True, "classification": "EXACT_REPLAY", "changed_tables": [],
              "provenance": {key: value for key, value in item.items() if key != "page_json"},
              "canonical_json_sha256": sha256(_json(item["page_json"]) + b"\n").hexdigest(),
              "canonical_json_size_bytes": len(_json(item["page_json"]) + b"\n"), "validated_json_sha256": _hash(item["page_json"])}
    replay["replay_receipt_id"] = "f39sourcejsonv1:" + _hash(replay)
    item["source_json_replay_receipt"] = replay
    loaded = [item]
    state = {"commands": [], "suffix": b"", "version": b"pdftoppm version 24.02.0\n", "on_render": None}
    monkeypatch.setattr(module.io_auth.shutil, "which", lambda name: renderer.as_posix() if name == "pdftoppm" else None)

    def run(command, *, capture_output, check, timeout):
        assert capture_output is True and check is True and timeout == 60
        state["commands"].append(list(command))
        if command[1:] == ["-v"]:
            return subprocess.CompletedProcess(command, 0, b"", state["version"])
        if state["on_render"] is not None:
            callback, state["on_render"] = state["on_render"], None
            callback()
        return subprocess.CompletedProcess(command, 0, _png() + state["suffix"], b"")

    monkeypatch.setattr(module.io_auth.subprocess, "run", run)

    def loader():
        return deepcopy(envelope), deepcopy(envelope_ref)

    def repin():
        envelope_ref.update(_write(envelope_path, _json(envelope)))
        compiled["income_tax_section_caption_auth_envelope"] = deepcopy(envelope)
        compiled["income_tax_section_caption_auth_envelope_ref"] = deepcopy(envelope_ref)

    return SimpleNamespace(module=module, document=document, loaded=loaded, records=records, compiled=compiled,
        envelope=envelope, envelope_ref=envelope_ref, envelope_path=envelope_path, pdf_root=pdf_root,
        pdf_path=Path(pdf_ref["path"]), manual=manual, manual_path=Path(manual_ref["path"]), candidate=candidate,
        candidate_path=Path(candidate_ref["path"]), full_path=Path(full_ref["path"]), crop_path=Path(crop_ref["path"]),
        renderer=renderer, legacy_path=Path(legacy_ref["path"]), migration_path=Path(migration_ref["path"]),
        coverage_path=Path(coverage_ref["path"]), parent_path=Path(parent_ref["path"]), state=state,
        loader=loader, repin=repin)


def _authenticate(f):
    return f.module.authenticate_registered_section_caption_pdf_v1(
        f.document, f.loaded, f.compiled, f.pdf_root, original_records=f.records, registry_loader=f.loader)


def _reseal(f, receipt):
    receipt["receipt_id"] = "f39captionpdfv1:" + f.module._digest({k: v for k, v in receipt.items() if k != "receipt_id"})


def _repin_review(f):
    candidate_ref = _write(f.candidate_path, _json(f.candidate))
    f.manual["pixel_candidate_ref"] = candidate_ref
    manual_ref = _write(f.manual_path, _json(f.manual))
    evidence = {"manual_review_ref": manual_ref, "pixel_candidate_ref": candidate_ref}
    f.envelope["clone_registry"]["sources"][0]["repairs"][0]["review_evidence"] = evidence
    f.envelope["source_version_lineages"][0]["repair_evidence"][0].update(evidence)
    f.repin()


def test_fresh_warm_cold_original_records_runordinal_and_no_permissions(auth_fixture):
    f = auth_fixture
    original = deepcopy((f.document, f.loaded, f.records, f.compiled))
    warm, cold = _authenticate(f), _authenticate(f)
    assert warm == cold and len(warm) == 1
    assert warm[0]["runtime_document_ordinal"] == 37
    assert warm[0]["source_database_authenticated_by_this_helper"] is False
    assert all(value is False for value in warm[0]["permission_grants"].values())
    assert all(value is False for value in warm[0]["pure_clone_replay_receipt"]["capabilities"].values())
    assert (f.document, f.loaded, f.records, f.compiled) == original
    assert f.records[0]["page_json"]["sections"][0]["tables"][0]["title_exact"] is None
    renders = [command for command in f.state["commands"] if "-f" in command]
    assert len(renders) >= 4 and all(len(command) == 10 and command[-1] == f.pdf_path.as_posix() for command in renders)


@pytest.mark.parametrize("target", ["envelope", "pdf", "manual", "candidate", "full", "crop", "legacy", "migration", "coverage", "parent", "renderer"])
def test_every_retained_file_byte_drift_rejects_late_barrier(auth_fixture, target):
    f = auth_fixture
    receipts = _authenticate(f)
    path = getattr(f, target + "_path", None) if target != "renderer" else f.renderer
    path.write_bytes(path.read_bytes() + b"drift")
    with pytest.raises(f.module.GeminiIncomeTaxSectionCaptionPdfAuthV1Error):
        f.module.recheck_registered_section_caption_pdf_v1(receipts, registry_loader=f.loader)


def test_resealed_late_renderer_ref_outside_approved_renderer_roots_rejects(auth_fixture, monkeypatch):
    f = auth_fixture
    receipts = _authenticate(f)
    # A permitted evidence directory is not permission to execute a renderer.
    outside = f.manual_path.parent / "unapproved" / "pdftoppm"
    _write(outside, f.renderer.read_bytes())
    receipt = receipts[0]
    old_path = receipt["renderer_ref"]["path"]
    receipt["renderer_ref"]["path"] = outside.as_posix()
    for reference in receipt["input_refs"]:
        if reference["path"] == old_path:
            reference["path"] = outside.as_posix()
    _reseal(f, receipt)
    monkeypatch.setattr(f.module.io_auth.shutil, "which", lambda name: outside.as_posix())
    with pytest.raises(f.module.GeminiIncomeTaxSectionCaptionPdfAuthV1Error) as rejected:
        f.module.recheck_registered_section_caption_pdf_v1(receipts, registry_loader=f.loader)
    assert "outside approved roots" in str(rejected.value.__cause__)


@pytest.mark.parametrize("target", ["envelope", "pdf", "manual", "crop", "legacy", "parent"])
def test_drift_during_last_pixel_callback_blocks_authentication_return(auth_fixture, target):
    f = auth_fixture
    path = getattr(f, target + "_path")
    f.state["on_render"] = lambda: path.write_bytes(path.read_bytes() + b"late")
    with pytest.raises(f.module.GeminiIncomeTaxSectionCaptionPdfAuthV1Error):
        _authenticate(f)


@pytest.mark.parametrize("mutation", ["missing_record", "ordinal", "VID", "physical", "source", "raw_before", "cell", "blob", "replay_id", "provenance", "compiled", "compiled_ref", "extra_loaded"])
def test_source_axis_replay_and_compiled_approval_not_caller_authority(auth_fixture, mutation):
    f = auth_fixture
    if mutation == "missing_record":
        f.records.clear()
    elif mutation == "ordinal":
        f.records[0]["document_ordinal"] = True
    elif mutation == "VID":
        f.records[0]["page_json_version_id"] = "gfpstorev1:json:" + "e" * 64
    elif mutation == "physical":
        f.loaded[0]["physical_page"] += 1
    elif mutation == "source":
        f.loaded[0]["source_sha256"] = "e" * 64
    elif mutation == "raw_before":
        f.loaded[0]["page_json"]["sections"][0]["title_exact"] = "Unprinted repair"
    elif mutation == "cell":
        f.records[0]["page_json"]["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "0"
    elif mutation == "blob":
        f.loaded[0]["source_json_replay_receipt"]["canonical_json_sha256"] = "e" * 64
    elif mutation == "replay_id":
        f.loaded[0]["source_json_replay_receipt"]["replay_receipt_id"] += "x"
    elif mutation == "provenance":
        f.loaded[0]["source_json_replay_receipt"]["provenance"]["physical_page"] += 1
    elif mutation == "compiled":
        f.compiled["income_tax_section_caption_auth_envelope"]["clone_registry"]["sources"][0]["repairs"][0]["after_exact"] += "x"
    elif mutation == "compiled_ref":
        f.compiled["income_tax_section_caption_auth_envelope_ref"]["sha256"] = "e" * 64
    else:
        f.loaded.append(deepcopy(f.loaded[0]))
    with pytest.raises(f.module.GeminiIncomeTaxSectionCaptionPdfAuthV1Error):
        _authenticate(f)


@pytest.mark.parametrize("mutation", ["permission", "extra_artifact", "pdf_ref", "drop_refs", "rgb", "physical", "duplicate", "all_runtime", "pure_drop", "pure_hash"])
def test_auth_receipt_self_reseal_is_not_approval(auth_fixture, mutation):
    f = auth_fixture
    receipts = _authenticate(f)
    receipt = receipts[0]
    if mutation == "permission":
        receipt["permission_grants"]["period"] = True
    elif mutation == "extra_artifact":
        receipt["approved"] = True
    elif mutation == "pdf_ref":
        receipt["pdf_ref"]["sha256"] = "e" * 64
    elif mutation == "drop_refs":
        receipt["input_refs"] = []
    elif mutation == "rgb":
        receipt["pixel_receipt"]["rgb_sha256"] = "e" * 64
    elif mutation == "physical":
        receipt["pixel_receipt"]["physical_page"] += 1
    elif mutation == "duplicate":
        receipts.append(deepcopy(receipt))
    elif mutation == "all_runtime":
        receipt["runtime_scope"] = "ALL_ELF_FONTS_AND_RUNTIME_VERIFIED"
    else:
        pure = receipt["pure_clone_replay_receipt"]
        if mutation == "pure_drop":
            pure["occurrences"] = []
        else:
            pure["occurrences"][0]["original_page_object_canonical_sha256"] = "e" * 64
        pure["receipt_id"] = "f39captionclonev1:" + f.module._digest({k: v for k, v in pure.items() if k != "receipt_id"})
    _reseal(f, receipt)
    with pytest.raises(f.module.GeminiIncomeTaxSectionCaptionPdfAuthV1Error):
        f.module.recheck_registered_section_caption_pdf_v1(receipts, registry_loader=f.loader)


@pytest.mark.parametrize("field,value", [("version_id", "wrong"), ("key", "bctc-ai/wrong"), ("bucket", "public"), ("size_bytes", 1)])
def test_approved_envelope_cannot_detach_local_pdf_version_lineage(auth_fixture, field, value):
    f = auth_fixture
    f.envelope["source_version_lineages"][0]["pdf_object"][field] = value
    f.repin()
    with pytest.raises(f.module.GeminiIncomeTaxSectionCaptionPdfAuthV1Error):
        _authenticate(f)


@pytest.mark.parametrize("field,value", [("source_pdf", {"physical_page": 99}), ("images_actually_viewed_by_reviewer", {}), ("capabilities", {"registered_registry_approval_granted": True})])
def test_changed_manual_with_resealed_candidate_ref_is_not_unbounded_permission(auth_fixture, field, value):
    f = auth_fixture
    f.manual[field] = value
    ref = _write(f.manual_path, _json(f.manual))
    f.envelope["clone_registry"]["sources"][0]["repairs"][0]["review_evidence"]["manual_review_ref"] = ref
    f.envelope["source_version_lineages"][0]["repair_evidence"][0]["manual_review_ref"] = ref
    f.repin()
    with pytest.raises(f.module.GeminiIncomeTaxSectionCaptionPdfAuthV1Error):
        _authenticate(f)


def test_bad_actual_renderer_version_or_png_stdout_is_not_candidate_success(auth_fixture):
    f = auth_fixture
    f.state["version"] = b"pdftoppm version 99.0\n"
    with pytest.raises(f.module.GeminiIncomeTaxSectionCaptionPdfAuthV1Error):
        _authenticate(f)
    f.state["version"] = b"pdftoppm version 24.02.0\n"
    f.state["suffix"] = b"foreign-bytes"
    with pytest.raises(f.module.GeminiIncomeTaxSectionCaptionPdfAuthV1Error):
        _authenticate(f)


def test_applicable_caption_requires_pdf_root_and_does_not_write_a_render(auth_fixture):
    f = auth_fixture
    before = sorted(path.relative_to(f.pdf_root) for path in f.pdf_root.rglob("*"))
    with pytest.raises(f.module.GeminiIncomeTaxSectionCaptionPdfAuthV1Error):
        f.module.authenticate_registered_section_caption_pdf_v1(
            f.document, f.loaded, f.compiled, None, original_records=f.records, registry_loader=f.loader)
    _authenticate(f)
    assert sorted(path.relative_to(f.pdf_root) for path in f.pdf_root.rglob("*")) == before


@pytest.mark.parametrize("mutation", ["width", "height", "rgb_hash", "rgb_size", "crop_box", "bool_dpi", "bool_page", "table_title", "wrong_before", "wrong_after", "extra_image"])
def test_self_consistent_candidate_metadata_cannot_replace_actual_pixels_or_caption(auth_fixture, mutation):
    f = auth_fixture
    whole = f.manual["images_actually_viewed_by_reviewer"]["fresh_whole_page"]
    crop = f.manual["images_actually_viewed_by_reviewer"]["fresh_header_crop"]
    if mutation in {"width", "height", "rgb_hash", "rgb_size", "crop_box"}:
        key, value = {"width": ("width_pixels", 3), "height": ("height_pixels", 2),
                      "rgb_hash": ("rgb_sha256", "e" * 64), "rgb_size": ("rgb_size_bytes", 7),
                      "crop_box": ("crop_box_pixels", [0, 0, 3, 1])}[mutation]
        crop[key] = value
        f.candidate["candidate_crop"][key] = value
    elif mutation == "bool_dpi":
        whole["render_dpi"] = True
    elif mutation == "bool_page":
        f.candidate["physical_page"] = True
    elif mutation == "table_title":
        f.manual["manual_visual_finding"]["historical_table_title_exact"] = "Invented title"
    elif mutation == "wrong_before":
        f.manual["manual_visual_finding"]["historically_selected_section_title_exact"] += "x"
    elif mutation == "wrong_after":
        f.manual["manual_visual_finding"]["own_page_heading_exact"] += "x"
    else:
        f.manual["images_actually_viewed_by_reviewer"]["unreviewed_extra_crop"] = deepcopy(crop)
    _repin_review(f)
    with pytest.raises(f.module.GeminiIncomeTaxSectionCaptionPdfAuthV1Error):
        _authenticate(f)


@pytest.mark.parametrize("mutation", ["approved", "caller_hash", "extra_evidence", "missing_legacy", "wrong_legacy_sha", "coverage_version", "parent_version"])
def test_neutral_envelope_cannot_grant_missing_legacy_or_restore_authority(auth_fixture, mutation):
    f = auth_fixture
    if mutation == "approved":
        f.envelope["approved"] = True
    elif mutation == "caller_hash":
        f.envelope["expected_registry_sha256"] = "e" * 64
    elif mutation == "extra_evidence":
        f.envelope["source_version_lineages"][0]["repair_evidence"].append(
            deepcopy(f.envelope["source_version_lineages"][0]["repair_evidence"][0]))
    elif mutation == "missing_legacy":
        f.compiled["income_tax_source_repairs"] = []
    elif mutation == "wrong_legacy_sha":
        f.envelope["legacy_source_repair_spec_ref"]["sha256"] = "e" * 64
    else:
        key = "coverage_manifest" if mutation == "coverage_version" else "parent_snapshot_manifest"
        f.envelope["source_version_lineages"][0]["restore_authorities"][key]["s3"]["version_id"] = "foreign_version"
    f.repin()
    with pytest.raises(f.module.GeminiIncomeTaxSectionCaptionPdfAuthV1Error):
        _authenticate(f)


def test_original_source_changed_and_receipt_resealed_still_fails_registered_before(auth_fixture):
    f = auth_fixture
    f.records[0]["page_json"]["sections"][0]["title_exact"] = "Caller invented original"
    f.loaded[0]["page_json"] = deepcopy(f.records[0]["page_json"])
    replay = f.loaded[0]["source_json_replay_receipt"]
    replay["canonical_json_sha256"] = sha256(_json(f.loaded[0]["page_json"]) + b"\n").hexdigest()
    replay["canonical_json_size_bytes"] = len(_json(f.loaded[0]["page_json"]) + b"\n")
    replay["validated_json_sha256"] = _hash(f.loaded[0]["page_json"])
    replay["replay_receipt_id"] = "f39sourcejsonv1:" + _hash({k: v for k, v in replay.items() if k != "replay_receipt_id"})
    with pytest.raises(f.module.GeminiIncomeTaxSectionCaptionPdfAuthV1Error):
        _authenticate(f)
