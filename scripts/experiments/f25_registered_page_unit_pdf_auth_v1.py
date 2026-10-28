"""Authenticate registered F25 page-header units without changing source JSON.

Historical absolute references inside the pinned visual review are provenance
only. All executable/data authority is resolved from the CURRENT repository.
"""
from __future__ import annotations

import json
import os
import stat
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path, PurePosixPath

import fitz

from bctc_ai.evaluation import gemini_json_first_page_render_v1 as renderer
from bctc_ai.evaluation import gemini_json_issued_valuable_papers_family_v1 as family
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

ROOT = Path(__file__).resolve().parents[2]
# This authority is in authenticated source bytes, never a closure/caller pin.
CATALOG_SHA256 = "6a69a7e5c68a0808fa43055eee76d3c680f12ffd9c18151f8e635b0f0ee3381f"
CATALOG_SIZE_BYTES = 2065


def _need(condition, message):
    if not condition:
        raise ValueError("F25 registered page unit: " + message)


def _identity(path):
    value = path.stat()
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns


def _safe(path):
    path = Path(path).absolute()
    _need(path.resolve(strict=True) == path and path.is_file()
          and not any(p.is_symlink() for p in (path, *path.parents)), "canonical non-symlink file required")
    return path


def _local(root, relative):
    member = PurePosixPath(relative)
    _need(not member.is_absolute() and ".." not in member.parts and "\\" not in relative, "relative member required")
    path = _safe(root.joinpath(*member.parts))
    _need(path.is_relative_to(root), "member escaped current root")
    return path


def _read(path, expected_sha256, expected_size_bytes, maximum):
    path = _safe(path)
    _need(type(expected_size_bytes) is int and 0 < expected_size_bytes <= maximum, "bounded file required")
    before = _identity(path)
    with path.open("rb") as handle:
        raw = handle.read(expected_size_bytes + 1)
    _need(_identity(path) == before and len(raw) == expected_size_bytes
          and sha256(raw).hexdigest() == expected_sha256, "file bytes/identity drifted: " + str(path))
    return raw, before


class _HeldPageUnitInput:
    """One private read-only descriptor; no filesystem identity enters a claim."""

    def __init__(self, path, expected_sha256, expected_size_bytes):
        self.path = _safe(path)
        self.sha256, self.size_bytes = expected_sha256, expected_size_bytes
        self.fd = os.open(self.path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0))
        try:
            opened = os.fstat(self.fd)
            _need(stat.S_ISREG(opened.st_mode), "held input must be a regular file")
            self.identity = self._identity(opened)
            self.check()
        except BaseException:
            os.close(self.fd)
            raise

    @staticmethod
    def _identity(value):
        # Windows stat/fstat need not report ctime with the same semantics.
        return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns

    def check(self):
        _safe(self.path)
        _need(self._identity(os.fstat(self.fd)) == self.identity
              and self._identity(self.path.stat()) == self.identity,
              "HELD_PAGE_UNIT_INPUT_CHANGED: " + str(self.path))
        os.lseek(self.fd, 0, os.SEEK_SET)
        digest, size = sha256(), 0
        for block in iter(lambda: os.read(self.fd, 1024 * 1024), b""):
            digest.update(block)
            size += len(block)
        _need(size == self.size_bytes and digest.hexdigest() == self.sha256
              and self._identity(os.fstat(self.fd)) == self.identity
              and self._identity(self.path.stat()) == self.identity,
              "HELD_PAGE_UNIT_INPUT_CHANGED: " + str(self.path))

    def close(self):
        os.close(self.fd)


@contextmanager
def hold_registered_page_unit_inputs_v1(*, source_pdf_root, selected_page_json_version_ids, repo_root=ROOT):
    """Hold current controls/applicable PDF through the caller's COMPLETE work.

    This guard grants no claim and never shares warm permission with cold work.
    Every cold owner still reloads SQL/provenance and freshly renders inside it.
    """
    root = Path(repo_root).absolute()
    catalog = load_registered_page_unit_catalog_v1(root)
    references = [(_local(root, family.PAGE_UNIT_CATALOG_PATH), CATALOG_SHA256, CATALOG_SIZE_BYTES)]
    references += [(_local(root, catalog[k]["path"]), catalog[k]["sha256"], catalog[k]["size_bytes"])
                   for k in ("review_ref", "renderer_ref")]
    for registration in catalog["claims"]:
        if registration["locator"]["page_json_version_id"] in selected_page_json_version_ids:
            pdf_root = Path(source_pdf_root).absolute()
            _need(pdf_root.resolve(strict=True) == pdf_root, "canonical held source PDF root required")
            source = registration["source"]
            references.append((_local(pdf_root, source["source_logical_name"]),
                               source["source_sha256"], source["source_size_bytes"]))
    held = []
    try:
        for path, digest, size in references:
            held.append(_HeldPageUnitInput(path, digest, size))
        yield
    finally:
        try:
            for item in held:
                item.check()
        finally:
            for item in held:
                item.close()


def load_registered_page_unit_catalog_v1(repo_root=ROOT):
    root = Path(repo_root).absolute()
    _need(root.resolve(strict=True) == root, "current repo root required")
    path = _local(root, family.PAGE_UNIT_CATALOG_PATH)
    _need(family.PAGE_UNIT_CATALOG_SHA256 == CATALOG_SHA256, "source catalog pins disagree")
    raw, _identity_before = _read(path, CATALOG_SHA256, CATALOG_SIZE_BYTES, 65536)
    catalog = json.loads(raw)
    _need(canonical_json_bytes_v1(catalog) == raw, "canonical pinned catalog required")
    _need(len(catalog["claims"]) == 1 and catalog["claims"][0]["before_unit_exact"] is None,
          "one exact null-unit transcription registration required")
    review_raw = None
    for key in ("review_ref", "renderer_ref"):
        ref = catalog[key]
        checked, _checked_identity = _read(_local(root, ref["path"]), ref["sha256"], ref["size_bytes"], 65536)
        if key == "review_ref":
            review_raw = checked
    review = json.loads(review_raw)
    finding = review["literal_visual_finding"]
    registration = catalog["claims"][0]
    _need(review["source_input_beforeafter_equal"] is True and review["qa_helpers_beforeafter_equal"] is True
          and review["visual_review_performed"] is True
          and finding["printed_scope"] == "GLOBAL_FOR_THIS_PHYSICAL_PAGE"
          and finding["unit_declaration_exact"] == registration["printed_unit_exact"]
          and all(finding[key] is True for key in ("target_heading_below_same_page_header",
              "no_intervening_unit_reset_visible", "no_target_local_unit_override_visible",
              "no_conflicting_unit_multiplier_visible_on_page")), "review does not attest exact page scope")
    return catalog


def authenticate_registered_page_unit_scopes_v1(*, source_pdf_root, selected_page_axis,
        selected_page_provenance, page_json_by_document, repo_root=ROOT):
    """Fresh bounded source/render validation on EACH warm/cold invocation.

    The returned compact data is not a financial PASS. Public family evaluation
    independently checks raw, selected identity and unit scope; cold persistence
    re-queries its own payload/provenance and calls this authenticator again.
    """
    root = Path(repo_root).absolute()
    catalog = load_registered_page_unit_catalog_v1(root)
    controls = [(family.PAGE_UNIT_CATALOG_PATH, CATALOG_SHA256, CATALOG_SIZE_BYTES)]
    controls += [(catalog[k]["path"], catalog[k]["sha256"], catalog[k]["size_bytes"])
                 for k in ("review_ref", "renderer_ref")]
    held = [(path, _read(_local(root, path), digest, size, 65536)[1], digest, size)
            for path, digest, size in controls]
    expected_renderer = _local(root, catalog["renderer_ref"]["path"])
    _need(Path(renderer.__file__).absolute() == expected_renderer, "foreign renderer module")
    claims = []
    source_checks = []
    for registration in catalog["claims"]:
        locator, source = registration["locator"], registration["source"]
        selected = [item for item in selected_page_axis
                    if item["page_json_version_id"] == locator["page_json_version_id"]]
        if not selected:
            continue  # Another selected version, including COMMON, cannot inherit.
        _need(len(selected) == 1, "duplicate selected page")
        selected = selected[0]
        _need(all(selected.get(k) == v for k, v in source.items() if k != "source_size_bytes")
              and selected["physical_page"] == locator["physical_page"], "selected source identity differs")
        provenance = [item for item in selected_page_provenance
                      if item["page_json_version_id"] == locator["page_json_version_id"]]
        _need(len(provenance) == 1, "unique selected provenance required")
        provenance = provenance[0]
        _need(all(provenance.get(k) == selected[k] for k in ("document_id", "source_logical_name", "source_sha256",
              "page_json_version_id", "physical_page")), "payload provenance source differs")
        _need(selected["page_json_version_id"] == "gfpstorev1:json:" + canonical_json_sha256_v1({
            k: provenance[k] for k in ("canonical_json_sha256", "extraction_run_id", "page_id")}),
            "payload version formula differs")
        page = page_json_by_document[selected["document_ordinal"]][selected["page_json_version_id"]]
        raw = canonical_json_bytes_v1(page) + b"\n"
        original = registration["original_payload"]
        _need(len(raw) == original["size_bytes"] and sha256(raw).hexdigest() == original["sha256"]
              and provenance["canonical_json_sha256"] == original["sha256"], "original two-LF payload differs")
        table = page["sections"][int(locator["section_id"][1:]) - 1]["tables"][int(locator["table_id"][1:]) - 1]
        _need(registration["before_unit_exact"] is None and table.get("unit_exact") is None,
              "original unit before-image differs")
        pdf_root = Path(source_pdf_root).absolute()
        _need(pdf_root.resolve(strict=True) == pdf_root, "canonical source PDF root required")
        pdf = _local(pdf_root, source["source_logical_name"])
        payload, identity = _read(pdf, source["source_sha256"], source["source_size_bytes"], 32 * 1024 * 1024)
        source_checks.append((pdf, identity, source))
        expected = registration["render"]
        render_identity = expected["renderer_identity"]
        _need(fitz.VersionBind == render_identity["pymupdf_version"]
              and render_identity == {"pymupdf_version": "1.28.2", "render_dpi": 300, "alpha": False,
                  "colorspace": "RGB", "page_box_mode": "DECLARED_PAGE_BOX",
                  "renderer_source_sha256": catalog["renderer_ref"]["sha256"]},
              "PAGE_UNIT_RENDER_IDENTITY_MISMATCH: reviewed PyMuPDF1.28.2/300dpi/RGB/alphaFalse/page-box required; actual="
              + str(fitz.VersionBind))
        with fitz.open(stream=payload, filetype="pdf") as document:
            _need(locator["physical_page"] <= len(document), "PDF page is absent")
            rendered = renderer.render_full_pdf_page_v1(document[locator["physical_page"] - 1],
                physical_page=locator["physical_page"], dpi=300, source_sha256=source["source_sha256"])
        receipt_raw = canonical_json_bytes_v1(rendered.receipt)
        _need(sha256(rendered.image).hexdigest() == expected["image_sha256"]
              and len(rendered.image) == expected["image_size_bytes"]
              and rendered.page == {"physical_page": locator["physical_page"], "image_sha256": expected["image_sha256"],
                  "image_size_bytes": expected["image_size_bytes"], "pixel_width": expected["pixel_width"],
                  "pixel_height": expected["pixel_height"], "render_dpi": 300, "media_type": "image/png"}
              and sha256(receipt_raw).hexdigest() == expected["render_receipt_sha256"]
              and len(receipt_raw) == expected["render_receipt_size_bytes"]
              and rendered.receipt["mode"] == render_identity["page_box_mode"],
              "PAGE_UNIT_RENDER_IDENTITY_MISMATCH: expected image=" + expected["image_sha256"]
              + ", actual=" + sha256(rendered.image).hexdigest()
              + "; expected receipt=" + expected["render_receipt_sha256"]
              + ", actual=" + sha256(receipt_raw).hexdigest())
        claims.append(family.build_gemini_json_issued_valuable_papers_page_unit_claim_v1(registration, selected, provenance))
        del payload, rendered, receipt_raw
    for relative, identity, digest, size in held:
        path = _local(root, relative)
        _need(_identity(path) == identity and _read(path, digest, size, 65536)[1] == identity,
              "late current-local control drift")
    for path, identity, source in source_checks:
        _need(_identity(path) == identity and _read(path, source["source_sha256"],
              source["source_size_bytes"], 32 * 1024 * 1024)[1] == identity, "late source PDF drift")
    return claims
