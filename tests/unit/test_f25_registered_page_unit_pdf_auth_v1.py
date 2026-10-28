"""Filesystem/render protocol controls, explicitly NOT VAB financial acceptance."""
from __future__ import annotations

import copy
import shutil
from hashlib import sha256
from pathlib import Path

import fitz
import pytest
from test_gemini_json_issued_valuable_papers_page_unit_scopes_v1 import (
    ROOT,
    _catalog,
    _context,
)
from test_run_gemini_json_issued_valuable_papers_accounting_family_v1 import runner

from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

auth = runner.page_units


def _copy_controls(destination):
    catalog = _catalog()
    for relative in (runner.PAGE_UNIT_CATALOG_PATH, catalog["review_ref"]["path"], catalog["renderer_ref"]["path"]):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    return catalog


def test_current_relative_controls_relocate_without_opening_historic_absolute_refs(tmp_path, monkeypatch):
    catalog = _copy_controls(tmp_path)
    paths = []
    read = auth._read

    def observe(path, *args):
        paths.append(Path(path))
        return read(path, *args)

    monkeypatch.setattr(auth, "_read", observe)
    assert auth.load_registered_page_unit_catalog_v1(tmp_path) == catalog
    assert paths and all(path.is_relative_to(tmp_path) for path in paths)


@pytest.mark.parametrize("which", ["catalog", "review_ref", "renderer_ref"])
def test_missing_or_wrong_current_control_has_no_historic_fallback(tmp_path, which):
    catalog = _copy_controls(tmp_path)
    target = tmp_path / (runner.PAGE_UNIT_CATALOG_PATH if which == "catalog" else catalog[which]["path"])
    target.write_bytes(target.read_bytes() + b" ")
    with pytest.raises(ValueError, match="bytes/identity drifted"):
        auth.load_registered_page_unit_catalog_v1(tmp_path)
    target.unlink()
    with pytest.raises(FileNotFoundError):
        auth.load_registered_page_unit_catalog_v1(tmp_path)


def _synthetic_protocol(tmp_path, monkeypatch):
    """Real small PDF/render/files, synthetic registration confined to IO tests.

    Only the registration loader is replaced. No family financial evaluator or
    validator is mocked or invoked; this registration is not production-pinned.
    """
    catalog, context = _context()
    catalog = copy.deepcopy(catalog)
    registration = catalog["claims"][0]
    with fitz.open() as document:
        page = document.new_page(width=120, height=120)
        page.insert_text((10, 20), "Unit: VND")
        payload = document.tobytes()
    source = registration["source"]
    source.update(source_logical_name="synthetic.pdf", source_sha256=sha256(payload).hexdigest(),
                  source_size_bytes=len(payload), document_id="gfpstorev1:document:" + "9" * 64)
    (tmp_path / "synthetic.pdf").write_bytes(payload)
    selected = copy.deepcopy(context["selected_page_axis"][0])
    provenance = copy.deepcopy(context["selected_page_provenance"][0])
    for value in (selected, provenance):
        value.update({k: source[k] for k in ("document_id", "source_logical_name", "source_sha256")})
        value["physical_page"] = 1
    provenance["page_id"] = "gfpstorev1:page:" + "9" * 64
    provenance["extraction_run_id"] = "gfpstorev1:run:" + "8" * 64
    version = "gfpstorev1:json:" + canonical_json_sha256_v1({
        k: provenance[k] for k in ("canonical_json_sha256", "extraction_run_id", "page_id")})
    selected["page_json_version_id"] = provenance["page_json_version_id"] = version
    registration["locator"].update(page_json_version_id=version, physical_page=1)
    with fitz.open(stream=payload, filetype="pdf") as document:
        rendered = auth.renderer.render_full_pdf_page_v1(document[0], physical_page=1, dpi=300,
                                                        source_sha256=source["source_sha256"])
    registration["render"] = {**registration["render"], **{k: rendered.page[k] for k in (
        "image_sha256", "image_size_bytes", "pixel_width", "pixel_height", "render_dpi")},
        "render_receipt_sha256": sha256(canonical_json_bytes_v1(rendered.receipt)).hexdigest(),
        "render_receipt_size_bytes": len(canonical_json_bytes_v1(rendered.receipt))}
    registration["registration_id"] = "gjivppuv1:registration:" + canonical_json_sha256_v1({
        k: v for k, v in registration.items() if k != "registration_id"})
    monkeypatch.setattr(auth, "load_registered_page_unit_catalog_v1", lambda _root: catalog)
    options = {"source_pdf_root": tmp_path, "selected_page_axis": [selected],
        "selected_page_provenance": [provenance], "page_json_by_document": {
            1: {version: next(iter(context["page_json_by_version"].values()))}}}
    return catalog, options


def test_each_authentication_freshly_reads_and_renders_real_synthetic_pdf(tmp_path, monkeypatch):
    catalog, options = _synthetic_protocol(tmp_path, monkeypatch)
    render = auth.renderer.render_full_pdf_page_v1
    calls = []

    def observed(*args, **kwargs):
        calls.append(kwargs)
        return render(*args, **kwargs)

    monkeypatch.setattr(auth.renderer, "render_full_pdf_page_v1", observed)
    first = auth.authenticate_registered_page_unit_scopes_v1(**options)
    second = auth.authenticate_registered_page_unit_scopes_v1(**options)
    assert first == second and len(calls) == 2
    assert first[0]["registration_id"] == catalog["claims"][0]["registration_id"]
    assert first[0]["registration_id"] != _catalog()["claims"][0]["registration_id"]


@pytest.mark.parametrize("mutation", ["source", "render", "provenance", "late_source"])
def test_synthetic_protocol_file_render_lineage_and_late_change_fail_closed(tmp_path, monkeypatch, mutation):
    catalog, options = _synthetic_protocol(tmp_path, monkeypatch)
    if mutation == "source":
        (tmp_path / "synthetic.pdf").write_bytes(b"different source")
    elif mutation == "render":
        catalog["claims"][0]["render"]["image_sha256"] = "0" * 64
    elif mutation == "provenance":
        options["selected_page_provenance"][0]["page_id"] = "gfpstorev1:page:" + "0" * 64
    else:
        render = auth.renderer.render_full_pdf_page_v1

        def changed(*args, **kwargs):
            result = render(*args, **kwargs)
            with (tmp_path / "synthetic.pdf").open("ab") as handle:
                handle.write(b"changed after render")
            return result

        monkeypatch.setattr(auth.renderer, "render_full_pdf_page_v1", changed)
    with pytest.raises(ValueError):
        auth.authenticate_registered_page_unit_scopes_v1(**options)


def test_unselected_registration_does_not_open_pdf_or_render(tmp_path, monkeypatch):
    monkeypatch.setattr(auth.fitz, "open", lambda **_kwargs: pytest.fail("unselected source was opened"))
    assert auth.authenticate_registered_page_unit_scopes_v1(source_pdf_root=tmp_path,
        selected_page_axis=[], selected_page_provenance=[], page_json_by_document={}) == []


def test_symlinked_source_is_rejected_before_pdf_read(tmp_path, monkeypatch):
    _catalog_value, options = _synthetic_protocol(tmp_path, monkeypatch)
    source = tmp_path / "synthetic.pdf"
    target = tmp_path / "actual.pdf"
    source.rename(target)
    source.symlink_to(target)
    with pytest.raises(ValueError, match="non-symlink"):
        auth.authenticate_registered_page_unit_scopes_v1(**options)


def test_catalog_authority_is_literal_current_source_not_mutable_caller_pin(monkeypatch):
    assert auth.CATALOG_SHA256 == runner.PAGE_UNIT_CATALOG_SHA256
    monkeypatch.setattr(auth.family, "PAGE_UNIT_CATALOG_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="source catalog pins disagree"):
        auth.load_registered_page_unit_catalog_v1(ROOT)


def test_renderer_version_change_is_explicit_mismatch_not_silent_missing_permission(tmp_path, monkeypatch):
    _catalog_value, options = _synthetic_protocol(tmp_path, monkeypatch)
    monkeypatch.setattr(auth.fitz, "VersionBind", "future-version")
    with pytest.raises(ValueError, match="PAGE_UNIT_RENDER_IDENTITY_MISMATCH"):
        auth.authenticate_registered_page_unit_scopes_v1(**options)


def _held_protocol(tmp_path, monkeypatch):
    pdf_root = tmp_path / "source"
    pdf_root.mkdir()
    catalog, options = _synthetic_protocol(pdf_root, monkeypatch)
    controls = tmp_path / "current-repo"
    _copy_controls(controls)
    # Relocated module identity is protocol metadata only; the actual renderer
    # function and its byte-identical source copy are used, no financial API.
    monkeypatch.setattr(auth.renderer, "__file__", str(controls / catalog["renderer_ref"]["path"]))
    options["repo_root"] = controls
    held_options = {"source_pdf_root": pdf_root, "repo_root": controls,
        "selected_page_json_version_ids": (options["selected_page_axis"][0]["page_json_version_id"],)}
    return catalog, options, held_options


@pytest.mark.parametrize("stage,target,mutation", [
    ("after_auth_before_eval", "pdf", "remove"), ("after_auth_before_eval", "catalog", "replace"),
    ("after_ingest", "pdf", "replace"), ("after_ingest", "review_ref", "remove"),
    ("after_export", "pdf", "remove"), ("after_export", "renderer_ref", "replace"),
])
def test_descriptor_guard_outlives_authentication_through_caller_publication_protocol(
        tmp_path, monkeypatch, stage, target, mutation):
    catalog, options, held_options = _held_protocol(tmp_path, monkeypatch)
    root = held_options["repo_root"]
    path = (options["source_pdf_root"] / "synthetic.pdf" if target == "pdf" else
            root / (runner.PAGE_UNIT_CATALOG_PATH if target == "catalog" else catalog[target]["path"]))
    reached = []
    # These labels describe a caller lifetime protocol, not real SQL ingestion
    # or financial evaluation. The real descriptor/PDF/render checks execute.
    with pytest.raises((ValueError, FileNotFoundError)):
        with auth.hold_registered_page_unit_inputs_v1(**held_options):
            assert auth.authenticate_registered_page_unit_scopes_v1(**options)
            reached.append("authenticated")
            if mutation == "remove":
                path.unlink()
            else:
                replacement = path.with_name(path.name + ".replacement")
                replacement.write_bytes(path.read_bytes())  # same bytes, new inode
                replacement.replace(path)
            reached.append(stage)
    assert reached == ["authenticated", stage]


def test_cold_factory_cannot_return_trials_after_post_auth_pdf_replacement(tmp_path, monkeypatch):
    _catalog_value, options, held_options = _held_protocol(tmp_path, monkeypatch)
    hold = auth.hold_registered_page_unit_inputs_v1
    monkeypatch.setattr(auth, "hold_registered_page_unit_inputs_v1", lambda **_kwargs: hold(**held_options))
    callback = runner._fresh_page_unit_source_replay_adapter_v1(options["source_pdf_root"])
    mutated = []

    def cold_body(**kwargs):
        assert kwargs["source_pdf_root"] == options["source_pdf_root"]
        assert auth.authenticate_registered_page_unit_scopes_v1(**options)
        path = options["source_pdf_root"] / "synthetic.pdf"
        replacement = path.with_name("replacement.pdf")
        replacement.write_bytes(path.read_bytes())
        replacement.replace(path)
        mutated.append(True)
        return []  # Never escapes the real factory context; no financial PASS.

    monkeypatch.setattr(runner, "_replay_issued_valuable_papers_trials_from_source_v1", cold_body)
    with pytest.raises(ValueError, match="HELD_PAGE_UNIT_INPUT_CHANGED"):
        callback(source_page_database=tmp_path / "unopened.sqlite3",
            selected_page_json_version_ids=held_options["selected_page_json_version_ids"],
            compiled_specs={}, indexed_query_evidence={})
    assert mutated == [True]
