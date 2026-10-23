"""F36 runtime-only PRIMARY witness admission; no serialized token is authority."""
from __future__ import annotations

import os
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import fitz
from PIL import Image

from bctc_ai.evaluation.gemini_json_first_page_render_v1 import render_full_pdf_page_v1
from bctc_ai.evaluation.gemini_json_operating_expense_primary_witness_v1 import (
    HASH_KEY,
    SPEC_KEY,
    _primary_witness_projection_v1,
    validate_f36_primary_witness_spec_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

AXIS_FIELD = "operating_expense_primary_witness_axis_v1"
_DOC_FIELDS = ("document_id", "document_ordinal", "source_logical_name", "source_sha256")


class PrimaryWitnessAdmissionError(ValueError):
    pass


def _need(ok, code):
    if not ok:
        raise PrimaryWitnessAdmissionError(code)


def _identity(st):
    return (st.st_dev, st.st_ino, st.st_mode, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def _read(path):
    path = Path(path)
    _need(path.is_absolute() and ".." not in path.parts
          and not any(p.is_symlink() for p in (path, *path.parents)), "unsafe witness authority path")
    with path.open("rb") as stream:
        before = _identity(os.fstat(stream.fileno()))
        _need(before == _identity(path.stat()), "witness authority FD/path mismatch")
        payload = stream.read()
        _need(before == _identity(os.fstat(stream.fileno())) == _identity(path.stat()),
              "witness authority changed during read")
    return payload, {"path": str(path), "sha256": sha256(payload).hexdigest(),
                     "size_bytes": len(payload), "identity": list(before)}


def _fingerprint(pages, axis):
    return canonical_json_sha256_v1({
        "page_axis": list(axis),
        "page_objects": [{"page_json_version_id": p["page_json_version_id"],
                          "original_object_sha256": canonical_json_sha256_v1(pages[p["page_json_version_id"]])}
                         for p in axis],
    })


def _document(value):
    return {key: value[key] for key in _DOC_FIELDS}


class PrimaryWitnessAdmissionV1:
    """Only authenticate_primary_witness_admission_v1 can ordinarily create one.

    This is a trusted-runtime capability, not a defence against arbitrary Python
    memory mutation/reflection. JSON facts, hashes and approval booleans cannot
    be passed as this object. All persisted facts below are deterministic.
    """
    __slots__ = ("_data", "_seal", "_active")

    def __new__(cls, *args, **kwargs):
        raise PrimaryWitnessAdmissionError("live pixel authentication factory required")

    def __setattr__(self, name, value):
        raise PrimaryWitnessAdmissionError("admission is immutable")

    def _check(self, compiled_specs):
        _need(type(self) is PrimaryWitnessAdmissionV1
              and getattr(self, "_active", False) is True
              and canonical_json_sha256_v1(self._data) == self._seal,
              "closed/forged witness admission")
        _need(compiled_specs.get(HASH_KEY) == self._data["spec_sha256"]
              and canonical_json_sha256_v1(compiled_specs.get(SPEC_KEY)) == self._data["spec_sha256"],
              "witness admission/spec scope mismatch")
        for reference in self._data["authority_refs"]:
            path = Path(reference["path"])
            _need(_identity(path.stat()) == tuple(reference["identity"]),
                  "witness authority identity changed")

    def require_run(self, documents, page_axis, compiled_specs):
        self._check(compiled_specs)
        _need(same_typed_json_v1(list(documents), self._data["documents"])
              and same_typed_json_v1(list(page_axis), self._data["page_axis"]),
              "witness admission reused for another selected run")

    def project(self, *, pages, document, selected_page_axis, compiled_specs):
        self._check(compiled_specs)
        document = _document(document)
        ordinal = document["document_ordinal"]
        matches = [d for d in self._data["bindings"] if d["document"]["document_ordinal"] == ordinal]
        _need(len(matches) == 1 and same_typed_json_v1(matches[0]["document"], document)
              and matches[0]["original_fingerprint"] == _fingerprint(pages, selected_page_axis),
              "witness admission reused for another ORIGINAL document/page scope")
        private, projections = _primary_witness_projection_v1(
            pages=pages, document=document, selected_page_axis=list(selected_page_axis), compiled_specs=compiled_specs)
        facts = {
            "format_version": "F36_AUTHENTICATED_PRIMARY_WITNESS_DOCUMENT_AXIS_V1",
            "document": document, "spec_sha256": self._data["spec_sha256"],
            "spec_ref": {k: self._data["spec_ref"][k] for k in ("path", "sha256", "size_bytes")},
            "original_fingerprint": matches[0]["original_fingerprint"],
            "projection_receipts": projections,
            "pixel_verification_receipts": canonical_clone_v1(matches[0]["pixel_receipts"]),
            "pdf_pixels_verified": bool(projections),
            "mapping_permission": False, "unit_permission": False,
            "period_permission": False, "scope_permission": False, "financial_acceptance": False,
        }
        self.recheck()
        return private, {**facts, "receipt_id": "gjoepwa1:document:" + canonical_json_sha256_v1(facts)}

    def recheck(self):
        _need(getattr(self, "_active", False) is True
              and canonical_json_sha256_v1(self._data) == self._seal,
              "closed/altered witness admission")
        for reference in self._data["authority_refs"]:
            _payload, actual = _read(reference["path"])
            _need(actual == reference, "witness PDF/spec bytes drifted")

    def close(self):
        try:
            self.recheck()
        finally:
            object.__setattr__(self, "_active", False)


def authenticate_primary_witness_admission_v1(*, spec_path, expected_sha256, index,
                                              selected_document_axis, selected_page_axis,
                                              page_json_by_document, compiled_specs,
                                              source_pdf_root):
    """Read the approved-by-operator spec and verify actual PDF/render/crop bytes.

    The expected SHA must come from the separately reviewed invocation. This
    factory does not discover/approve a transcription by reading pixels as text.
    It never treats the pure primitive's all-false flags as authentication.
    """
    payload, spec_ref = _read(spec_path)
    _need(spec_ref["sha256"] == expected_sha256 == compiled_specs.get(HASH_KEY),
          "explicit witness spec pin mismatch")
    import json
    def pairs(items):
        result = {}
        for key, value in items:
            _need(key not in result, "duplicate witness spec JSON key")
            result[key] = value
        return result
    declared = validate_f36_primary_witness_spec_v1(json.loads(payload, object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(PrimaryWitnessAdmissionError("nonfinite witness spec"))))
    _need(same_typed_json_v1(declared, compiled_specs.get(SPEC_KEY)),
          "compiled witness declarations differ from fresh file")
    docs = list(selected_document_axis)
    axes = list(selected_page_axis)
    _need(set(page_json_by_document) == {d["document_ordinal"] for d in docs},
          "witness original selected document axis incomplete")
    by_source = {}
    for document in index["documents"]:
        by_source.setdefault(document["source_sha256"], []).append(document)
    references, pixels, source_payloads, renders = [spec_ref], {}, {}, {}
    root = Path(source_pdf_root).resolve(strict=True)
    for item in declared["witnesses"]:
        source, loc = item["source"], item["locator"]
        selected_documents = [d for d in docs if d["source_sha256"] == source["source_sha256"]
                              or d["source_logical_name"] == source["source_logical_name"]]
        if not selected_documents:
            continue
        _need(len(selected_documents) == 1
              and selected_documents[0]["source_sha256"] == source["source_sha256"]
              and selected_documents[0]["source_logical_name"] == source["source_logical_name"],
              "partial/nonunique witness selected source identity")
        selected_sources = by_source.get(source["source_sha256"], [])
        _need(len(selected_sources) == 1, "witness selected source identity not unique")
        selected_source = selected_sources[0]
        _need(selected_source["relative_path"] == source["source_logical_name"]
              and selected_source["source_size_bytes"] == source["source_size_bytes"],
              "witness source differs from selected index")
        selected = [p for p in axes if p["page_json_version_id"] == loc["page_json_version_id"]]
        _need(len(selected) == 1 and selected[0]["source_sha256"] == source["source_sha256"]
              and selected[0]["source_logical_name"] == source["source_logical_name"]
              and selected[0]["physical_page"] == loc["physical_page"]
              and selected[0]["selected_page_ordinal"] == loc["selected_page_ordinal"],
              "witness selected original VID/page mismatch")
        path = root / source["source_logical_name"]
        _need(path.resolve(strict=True).is_relative_to(root), "witness PDF escaped root")
        if source["source_sha256"] not in source_payloads:
            content, reference = _read(path)
            _need(reference["sha256"] == source["source_sha256"]
                  and reference["size_bytes"] == source["source_size_bytes"], "witness PDF bytes mismatch")
            source_payloads[source["source_sha256"]] = content
            references.append(reference)
        key = (source["source_sha256"], loc["physical_page"])
        if key not in renders:
            with fitz.open(stream=source_payloads[source["source_sha256"]], filetype="pdf") as pdf:
                _need(0 < loc["physical_page"] <= len(pdf), "witness physical page outside PDF")
                rendered = render_full_pdf_page_v1(pdf[loc["physical_page"] - 1],
                    physical_page=loc["physical_page"], dpi=300, source_sha256=source["source_sha256"])
            renders[key] = (rendered.image, rendered.receipt)
        image_bytes, render_receipt = renders[key]
        with Image.open(BytesIO(image_bytes)) as image:
            image.load()
            rgb = image.convert("RGB")
            box = item["crop_evidence"]["bbox_pixels_xyxy"]
            crop = rgb.crop(tuple(box))
            actual_render = {"image_sha256": sha256(image_bytes).hexdigest(), "image_size_bytes": len(image_bytes),
                "media_type": "image/png", "physical_page": loc["physical_page"], "pixel_height": rgb.height,
                "pixel_width": rgb.width, "render_dpi": 300,
                "render_receipt_sha256": canonical_json_sha256_v1(render_receipt)}
            actual_crop = {"bbox_pixels_xyxy": box, "pixel_height": crop.height, "pixel_width": crop.width,
                           "rgb_sha256": sha256(crop.tobytes()).hexdigest()}
        _need(same_typed_json_v1(actual_render, item["render"])
              and same_typed_json_v1(actual_crop, item["crop_evidence"]),
              "witness actual full render/crop mismatch")
        facts = {"witness_id": item["witness_id"], "witness_kind": item["witness_kind"],
                 "after_exact": item["after_exact"], "observed_pdf_glyph": item["observed_pdf_glyph"],
                 "source": source, "locator": loc, "actual_render": actual_render, "actual_crop": actual_crop}
        pixels[item["witness_id"]] = {**facts, "receipt_id": "gjoepwa1:pixels:" + canonical_json_sha256_v1(facts)}
    bindings = []
    for document in docs:
        ordinal = document["document_ordinal"]
        axis = [p for p in axes if p["document_ordinal"] == ordinal]
        private, receipts = _primary_witness_projection_v1(
            pages=page_json_by_document[ordinal], document=document,
            selected_page_axis=axis, compiled_specs=compiled_specs)
        del private
        ids = [r["witness"]["witness_id"] for r in receipts]
        _need(all(wid in pixels for wid in ids), "applicable witness lacks actual pixel authentication")
        bindings.append({"document": document, "original_fingerprint": _fingerprint(page_json_by_document[ordinal], axis),
                         "pixel_receipts": [pixels[wid] for wid in ids]})
    data = {"documents": docs, "page_axis": axes, "bindings": bindings, "spec_ref": spec_ref,
            "spec_sha256": expected_sha256, "authority_refs": references}
    admission = object.__new__(PrimaryWitnessAdmissionV1)
    object.__setattr__(admission, "_data", canonical_clone_v1(data))
    object.__setattr__(admission, "_seal", canonical_json_sha256_v1(data))
    object.__setattr__(admission, "_active", True)
    admission.recheck()
    return admission


def require_admission_v1(value):
    _need(type(value) is PrimaryWitnessAdmissionV1, "live witness pixel admission required; JSON/hash/bool is not authority")
    return value
