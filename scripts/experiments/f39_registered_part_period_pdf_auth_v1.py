"""Fresh, read-only F39 registered-part PDF/render authentication.

The trusted caller supplies an independently pinned registry loader. This
module never accepts an approval flag, repairs JSON, reads a provider key, or
writes a render. Warm and cold callers must invoke authentication separately;
recheck is an exit barrier, not a substitute for either fresh authentication.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import struct
import subprocess
from hashlib import sha256
from pathlib import Path, PurePosixPath

from bctc_ai.evaluation.gemini_json_income_tax_part_period_context_v1 import (
    validate_registered_part_period_registry_v1,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EVIDENCE_ROOTS = (_REPO_ROOT.parent / "restore-receipts", Path("/srv/bctc-receipts"))
_RENDERER_ROOTS = (Path("/usr"),)
_VERSION = "Poppler pdftoppm 24.02.0"
_ORIGINAL_REPAIR_SHA = "9aac4e448b82ee0078c007ca06a36f0e3f11c2b4f694266a1211929f16228ea4"
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_MAX_JSON = 8 * 1024 * 1024
_MAX_PNG = 64 * 1024 * 1024
_FORMAT = "INCOME_TAX_REGISTERED_PART_PERIOD_PDF_AUTH_V1"
_STATUS = "PASS_REGISTERED_PDF_RENDER_SOURCE_BINDINGS_NOT_ACCEPTANCE"
_PERMISSIONS = {"unit": False, "report_scope": False, "entity": False,
                "source_value": False, "family_acceptance": False}
_RECEIPT_KEYS = {
    "format_version", "status", "complete", "context_id", "document_id", "context_registration_sha256",
    "pdf_source", "source_pdf_root", "registry_ref", "pdf_ref", "renderer_ref", "manual_review_ref",
    "visual_receipts", "input_refs", "loaded_original_axis_sha256", "source_bindings_rechecked_from_original_loaded",
    "manual_review_interpretation_replayed", "historical_review_refs_are_immutable_inputs_not_new_manual_review",
    "source_values_changed", "unknown_columns_promoted", "permission_grants",
    "recheck_is_not_a_substitute_for_fresh_warm_and_cold_authentication", "receipt_id",
}


class GeminiIncomeTaxPartPeriodPdfAuthV1Error(ValueError):
    """Changed or incomplete PDF/registry/render evidence fails closed."""


def _require(condition, message):
    if not condition:
        raise GeminiIncomeTaxPartPeriodPdfAuthV1Error(message)


def _canonical(value):
    try:
        return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                           allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as error:
        raise GeminiIncomeTaxPartPeriodPdfAuthV1Error("Noncanonical evidence object") from error


def _clone(value):
    return json.loads(_canonical(value))


def _json_object(raw):
    def pairs(values):
        result = {}
        for key, value in values:
            _require(key not in result, "Duplicate evidence JSON key")
            result[key] = value
        return result

    def invalid(_token):
        raise GeminiIncomeTaxPartPeriodPdfAuthV1Error("Nonfinite evidence JSON number")

    def finite(token):
        value = float(token)
        _require(math.isfinite(value), "Nonfinite evidence JSON float")
        return value

    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid, parse_float=finite)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise GeminiIncomeTaxPartPeriodPdfAuthV1Error("Evidence JSON invalid") from error
    _require(type(value) is dict, "Evidence must be one JSON object")
    return value


def _safe_path(path, roots, *, directory=False):
    path = Path(path)
    _require(path.is_absolute() and not {".", ".."} & set(path.parts), "Absolute canonical evidence path required")
    _require(path.name.casefold() not in {"codex-session.passphrase", "openrouter_api.txt"}, "Secret path prohibited")
    _require(any(path.is_relative_to(Path(root)) for root in roots), "Evidence path outside approved roots")
    for entry in (path, *path.parents):
        _require(not entry.is_symlink() and not getattr(entry, "is_junction", lambda: False)(),
                 "Evidence symlink/junction prohibited")
    try:
        _require(path.resolve(strict=True) == path and (path.is_dir() if directory else path.is_file()),
                 "Canonical regular evidence file/directory required")
    except OSError as error:
        raise GeminiIncomeTaxPartPeriodPdfAuthV1Error("Evidence path missing") from error
    return path


def _identity(stat):
    return {"device": stat.st_dev, "inode": stat.st_ino, "size_bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns, "ctime_ns": stat.st_ctime_ns}


def _checked_ref(reference, roots, *, maximum=None, retain=False):
    _require(type(reference) is dict and set(reference) in (
                 {"path", "sha256", "size_bytes"}, {"path", "sha256", "size_bytes", "file_identity"})
             and type(reference.get("path")) is str
             and type(reference.get("sha256")) is str and _SHA.fullmatch(reference["sha256"]) is not None
             and type(reference.get("size_bytes")) is int and reference["size_bytes"] > 0,
             "Malformed evidence byte ref")
    _require(maximum is None or reference["size_bytes"] <= maximum, "Evidence exceeds reviewed size bound")
    path = _safe_path(reference["path"], roots)
    try:
        before = _identity(path.stat())
        checksum, size, blocks = sha256(), 0, []
        with path.open("rb") as stream:
            held_before = _identity(os.fstat(stream.fileno()))
            _require(held_before == before, "Evidence identity changed before read")
            while block := stream.read(1024 * 1024):
                checksum.update(block)
                size += len(block)
                if retain:
                    blocks.append(block)
                _require(size <= reference["size_bytes"], "Evidence grew during read")
            _require(_identity(os.fstat(stream.fileno())) == before, "Evidence held bytes changed")
        _require(size == reference["size_bytes"] and checksum.hexdigest() == reference["sha256"],
                 "Evidence bytes/SHA differ")
        _safe_path(path, roots)
        _require(_identity(path.stat()) == before, "Evidence path identity changed during read")
    except OSError as error:
        raise GeminiIncomeTaxPartPeriodPdfAuthV1Error("Evidence read failed") from error
    observed = {"path": path.as_posix(), "sha256": checksum.hexdigest(), "size_bytes": size, "file_identity": before}
    if "file_identity" in reference:
        _require(reference["file_identity"] == before, "Evidence identity changed since authentication")
    return observed, b"".join(blocks) if retain else None


def _registry(registry_loader):
    _require(callable(registry_loader), "Trusted registry loader required")
    result = registry_loader()
    _require(type(result) is tuple and len(result) == 2, "Trusted loader result differs")
    registry, reference = result
    registry = validate_registered_part_period_registry_v1(registry)
    _require(type(reference) is dict and type(reference.get("path")) is str, "Registry ref missing")
    spelling = reference["path"]
    relative = PurePosixPath(spelling)
    _require("\\" not in spelling and not {".", ".."} & set(spelling.split("/")), "Registry spelling unsafe")
    path = Path(spelling) if relative.is_absolute() else _REPO_ROOT / spelling
    actual, raw = _checked_ref({**reference, "path": path.as_posix()}, (_REPO_ROOT,), maximum=_MAX_JSON, retain=True)
    parsed = validate_registered_part_period_registry_v1(_json_object(raw))
    _require(_canonical(parsed) == _canonical(registry), "Trusted registry object differs from actual pinned bytes")
    return registry, reference, actual


def _source_binding(document, loaded, registry):
    _require(type(document) is dict and type(loaded) is list, "Original document/loaded shapes differ")
    try:
        source = document["manifest"]["document"]
        ids, pages = document["ids"], document["manifest"]["pages"]
        material = {key: source[key] for key in ("source_logical_name", "source_sha256", "source_size_bytes")}
    except (KeyError, TypeError) as error:
        raise GeminiIncomeTaxPartPeriodPdfAuthV1Error("Original document source axis missing") from error
    _require(type(material["source_logical_name"]) is str and type(material["source_sha256"]) is str
             and _SHA.fullmatch(material["source_sha256"]) is not None
             and type(material["source_size_bytes"]) is int and material["source_size_bytes"] > 0,
             "Original PDF source identity malformed")
    logical = material["source_logical_name"]
    _require(not logical.startswith("/") and "\\" not in logical and ":" not in logical
             and not {"", ".", ".."} & set(logical.split("/"))
             and not any(char in logical for char in "\x00\r\n"), "Original logical PDF path unsafe")
    document_id = "gfpstorev1:document:" + sha256(_canonical(material)).hexdigest()
    _require(source.get("document_id", document_id) == document_id, "Original source document ID differs")
    matches = []
    for context in registry["contexts"]:
        pdf = context["pdf_source"]
        axes = (context["document_id"] == document_id, pdf["logical_name"] == logical,
                pdf["sha256"] == material["source_sha256"])
        if any(axes):
            _require(all(axes) and pdf["size_bytes"] == material["source_size_bytes"], "Registered PDF source identity differs")
            matches.append(context)
    if not matches:
        return material, document_id, [], None
    _require(type(ids) is list and type(pages) is list and all(type(vid) is str for vid in ids)
             and len(ids) == len(pages) == len(loaded)
             and len(set(ids)) == len(ids), "Original selected source axis differs")
    by_vid, axis = {}, []
    for ordinal, (item, page, vid) in enumerate(zip(loaded, pages, ids, strict=True), 1):
        _require(type(item) is dict and type(page) is dict and type(vid) is str
                 and item.get("page_json_version_id") == page.get("page_json_version_id") == vid
                 and type(item.get("physical_page")) is int and type(page.get("physical_page")) is int
                 and item["physical_page"] == page["physical_page"]
                 and item.get("source_logical_name") == logical and item.get("source_sha256") == material["source_sha256"]
                 and type(item.get("page_json")) is dict, "Fresh loaded selection/source metadata differs")
        replay = item.get("source_json_replay_receipt")
        _require(type(replay) is dict and replay.get("schema") == "bctc-ai-f39-original-source-json-replay-v1"
                 and replay.get("mapping_input") == "ORIGINAL_STORED_JSON_UNMODIFIED"
                 and replay.get("all_original_cells_and_ordinals_retained") is True, "Original loaded replay receipt missing")
        page_sha = sha256(_canonical(item["page_json"])).hexdigest()
        axis.append({"page_json_version_id": vid, "physical_page": item["physical_page"],
                     "selected_page_ordinal": ordinal, "original_page_json_sha256": page_sha})
        by_vid[vid] = (item, axis[-1])
    for context in matches:
        span = context["span_pages"]
        actual = [item for item in axis if span[0]["physical_page"] <= item["physical_page"] <= span[-1]["physical_page"]]
        _require(actual == [{key: page[key] for key in ("page_json_version_id", "physical_page", "selected_page_ordinal",
                                                      "original_page_json_sha256")} for page in span],
                 "Fresh original registered span differs")
        for registered_page in span:
            item, _ = by_vid[registered_page["page_json_version_id"]]
            replay = item["source_json_replay_receipt"]
            _require(replay.get("classification") == "EXACT_REPLAY"
                     and replay.get("changed_tables") == []
                     and replay.get("validated_json_sha256") == registered_page["original_page_json_sha256"]
                     and replay.get("canonical_json_sha256") == sha256(_canonical(item["page_json"]) + b"\n").hexdigest(),
                     "Registered prefix original/validated/BLOB domains differ")
        for binding in [*context["heading_occurrences"], *context["period_occurrences"], *context["target_tables"]]:
            try:
                page = by_vid[binding["page_json_version_id"]][0]["page_json"]
                section = page["sections"][int(binding["section_id"][1:]) - 1]
                _require(sha256(_canonical(section)).hexdigest() == binding["original_section_json_sha256"],
                         "Original registered section differs")
                if "money_column_ordinals" in binding:
                    table = section["tables"][int(binding["table_id"][1:]) - 1]
                    _require(sha256(_canonical(table)).hexdigest() == binding["original_table_json_sha256"],
                             "Original registered target table differs")
                else:
                    kind = binding["carrier_kind"]
                    carrier = (section["title_exact"] if kind == "SECTION_TITLE" else
                               section["narratives_exact"][binding["narrative_ordinal"] - 1] if kind == "NARRATIVE" else
                               section["tables"][int(binding["table_id"][1:]) - 1]["title_exact"])
                    _require(carrier == binding["source_exact"], "Original registered carrier differs")
            except (KeyError, IndexError, TypeError, ValueError) as error:
                if isinstance(error, GeminiIncomeTaxPartPeriodPdfAuthV1Error):
                    raise
                raise GeminiIncomeTaxPartPeriodPdfAuthV1Error("Original context locator differs") from error
    return material, document_id, matches, sha256(_canonical(axis)).hexdigest()


def _tool_run(arguments):
    try:
        result = subprocess.run(arguments, capture_output=True, check=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as error:
        raise GeminiIncomeTaxPartPeriodPdfAuthV1Error("Registered Poppler command failed") from error
    _require(result.returncode == 0 and type(result.stdout) is bytes and type(result.stderr) is bytes,
             "Registered Poppler result malformed")
    return result


def _renderer():
    found = shutil.which("pdftoppm")
    _require(found is not None, "Registered Poppler executable absent")
    try:
        path = Path(found).resolve(strict=True)
    except OSError as error:
        raise GeminiIncomeTaxPartPeriodPdfAuthV1Error("Registered Poppler path absent") from error
    _require(path.name == "pdftoppm", "Unexpected renderer executable")
    path = _safe_path(path, _RENDERER_ROOTS)
    raw = path.read_bytes()
    observed, _ = _checked_ref({"path": path.as_posix(), "sha256": sha256(raw).hexdigest(), "size_bytes": len(raw)}, _RENDERER_ROOTS)
    result = _tool_run([path.as_posix(), "-v"])
    try:
        text = (result.stdout + result.stderr).decode("utf-8", errors="strict")
    except UnicodeError as error:
        raise GeminiIncomeTaxPartPeriodPdfAuthV1Error("Poppler version is not UTF8") from error
    _require(re.search(r"^pdftoppm version 24\.02\.0\s*$", text, re.MULTILINE) is not None,
             "Registered Poppler version differs")
    return path, observed


def _png_dimensions(raw):
    _require(len(raw) >= 33 and raw[:8] == b"\x89PNG\r\n\x1a\n" and raw[8:12] == b"\x00\x00\x00\r"
             and raw[12:16] == b"IHDR", "Registered full-page PNG header invalid")
    width, height = struct.unpack(">II", raw[16:24])
    _require(width > 0 and height > 0, "Registered PNG dimensions invalid")
    return width, height


def _render_bindings(context, pdf_path, renderer_path):
    visual_rows, refs = [], []
    manual_ref, manual_raw = _checked_ref(context["review_evidence"]["manual_review_ref"], _EVIDENCE_ROOTS,
                                         maximum=_MAX_JSON, retain=True)
    _json_object(manual_raw)  # Its exact approved bytes, not a new interpretation.
    refs.append(manual_ref)
    span_pages = [page["physical_page"] for page in context["span_pages"]]
    visuals = context["review_evidence"]["visual_refs"]
    _require([visual["physical_page"] for visual in visuals] == span_pages, "Whole reviewed prefix visual axis differs")
    for visual in visuals:
        physical, dpi = visual["physical_page"], visual["dpi"]
        _require(visual["renderer_version"] == _VERSION and type(dpi) is int and dpi == 144,
                 "Registered renderer profile differs")
        png_ref, image = _checked_ref(visual["png_ref"], _EVIDENCE_ROOTS, maximum=_MAX_PNG, retain=True)
        render_ref, raw = _checked_ref(visual["render_receipt_ref"], _EVIDENCE_ROOTS, maximum=_MAX_JSON, retain=True)
        render = _json_object(raw)
        _require(_png_dimensions(image) == (visual["width_pixels"], visual["height_pixels"]), "Registered image dimensions differ")
        _require({"schema", "renderer", "physical_page", "source", "source_spec_sha256", "source_bytes_unchanged",
                  "family_terminal_claimed", "registered_PyMuPDF_repair_pixels_replaced", "visual_review_performed",
                  "repair_id", "image", "command", "diagnostic_ref"} <= set(render)
                 and render.get("schema") == "bctc-ai-f39-independent-pdf-review-render-v1"
                 and render.get("renderer") == "Poppler pdftoppm" and type(render.get("physical_page")) is int
                 and render["physical_page"] == physical and render.get("source") == context["pdf_source"]
                 and render.get("source_spec_sha256") == _ORIGINAL_REPAIR_SHA
                 and render.get("source_bytes_unchanged") is True and render.get("family_terminal_claimed") is False
                 and render.get("registered_PyMuPDF_repair_pixels_replaced") is False
                 and render.get("visual_review_performed") is False and render.get("repair_id") is None,
                 "Registered render source/profile/permission fields differ")
        linked = render.get("image")
        _require(type(linked) is dict and all(linked.get(key) == visual["png_ref"][key]
                                             for key in ("path", "sha256", "size_bytes")), "Render links a different PNG")
        historical = render.get("command")
        expected_prefix = ["pdftoppm", "-f", str(physical), "-l", str(physical), "-singlefile", "-r", "144", "-png"]
        _require(type(historical) is list and len(historical) == 11 and historical[:9] == expected_prefix
                 and all(type(item) is str for item in historical), "Historical render command differs")
        logical_parts = PurePosixPath(context["pdf_source"]["logical_name"]).parts
        _require(PurePosixPath(historical[9]).is_absolute()
                 and PurePosixPath(historical[9]).parts[-len(logical_parts):] == logical_parts
                 and historical[10] + ".png" == visual["png_ref"]["path"], "Historical render source/output identity differs")
        # No file-prefix argument: stdout is the complete PNG, never a file '-'.
        command = [renderer_path.as_posix(), *expected_prefix[1:], pdf_path.as_posix()]
        fresh = _tool_run(command)
        _require(len(fresh.stdout) == len(image) and fresh.stdout == image, "Fresh full-page Poppler PNG differs")
        visual_rows.append({"physical_page": physical, "dpi": dpi, "renderer_version": _VERSION,
                            "width_pixels": visual["width_pixels"], "height_pixels": visual["height_pixels"],
                            "png_ref": png_ref, "render_receipt_ref": render_ref,
                            "stdout_render_command": command, "stdout_sha256": sha256(fresh.stdout).hexdigest(),
                            "stdout_size_bytes": len(fresh.stdout), "stdout_equals_registered_png": True})
        refs.extend((png_ref, render_ref))
    return manual_ref, visual_rows, refs


def authenticate_registered_part_period_pdf_v1(document, loaded, compiled, source_pdf_root, *, registry_loader):
    """Fresh PDF authentication per pass; all results remain provisional."""
    registry, registry_ref, actual_registry_ref = _registry(registry_loader)
    _require(type(compiled) is dict and _canonical(compiled.get("income_tax_part_period_registry")) == _canonical(registry)
             and _canonical(compiled.get("income_tax_part_period_registry_ref")) == _canonical(registry_ref),
             "Fresh registry differs from compiled registry/ref")
    before_inputs = sha256(_canonical((document, loaded, compiled))).hexdigest()
    source, document_id, contexts, loaded_sha = _source_binding(document, loaded, registry)
    if not contexts:
        return []
    _require(source_pdf_root is not None, "Applicable registered PDF context requires source_pdf_root")
    root = _safe_path(Path(source_pdf_root), (Path(source_pdf_root),), directory=True)
    pdf_path = root / source["source_logical_name"]
    pdf_ref, _ = _checked_ref({"path": pdf_path.as_posix(), "sha256": source["source_sha256"],
                               "size_bytes": source["source_size_bytes"]}, (root,))
    renderer_path, renderer_ref = _renderer()
    receipts = []
    for context in contexts:
        manual, visuals, evidence_refs = _render_bindings(context, pdf_path, renderer_path)
        refs = [actual_registry_ref, pdf_ref, renderer_ref, *evidence_refs]
        material = {"format_version": _FORMAT, "status": _STATUS, "complete": True,
                    "context_id": context["context_id"], "document_id": document_id,
                    "context_registration_sha256": sha256(_canonical(context)).hexdigest(),
                    "pdf_source": context["pdf_source"], "source_pdf_root": root.as_posix(),
                    "registry_ref": actual_registry_ref, "pdf_ref": pdf_ref, "renderer_ref": renderer_ref,
                    "manual_review_ref": manual, "visual_receipts": visuals, "input_refs": refs,
                    "loaded_original_axis_sha256": loaded_sha,
                    "source_bindings_rechecked_from_original_loaded": True,
                    "manual_review_interpretation_replayed": False,
                    "historical_review_refs_are_immutable_inputs_not_new_manual_review": True,
                    "source_values_changed": False, "unknown_columns_promoted": False,
                    "permission_grants": _PERMISSIONS,
                    "recheck_is_not_a_substitute_for_fresh_warm_and_cold_authentication": True}
        receipts.append({**_clone(material), "receipt_id": "f39partpdfv1:" + sha256(_canonical(material)).hexdigest()})
    _require(before_inputs == sha256(_canonical((document, loaded, compiled))).hexdigest(), "PDF auth mutated its source/spec inputs")
    recheck_registered_part_period_pdf_v1(receipts, registry_loader=registry_loader)
    return receipts


def recheck_registered_part_period_pdf_v1(receipts, *, registry_loader):
    """Exit-barrier checks for receipts produced by this trusted invocation.

    This is not admission of caller-created receipts or an ambient approval
    token. Both warm and cold must have run fresh authentication themselves.
    """
    registry, _registry_ref, actual_registry_ref = _registry(registry_loader)
    _require(type(receipts) is list, "PDF auth receipts must be a plain list")
    if not receipts:
        return
    by_id = {context["context_id"]: context for context in registry["contexts"]}
    renderer_path, current_renderer = _renderer()
    seen = set()
    for receipt in receipts:
        _require(type(receipt) is dict and set(receipt) == _RECEIPT_KEYS
                 and type(receipt.get("context_id")) is str and receipt["context_id"] in by_id
                 and receipt["context_id"] not in seen, "PDF auth context receipt missing/duplicate")
        seen.add(receipt["context_id"])
        context = by_id[receipt["context_id"]]
        material = {key: value for key, value in receipt.items() if key != "receipt_id"}
        _require(receipt.get("receipt_id") == "f39partpdfv1:" + sha256(_canonical(material)).hexdigest()
                 and receipt.get("format_version") == _FORMAT and receipt.get("status") == _STATUS
                 and receipt.get("complete") is True and receipt.get("document_id") == context["document_id"]
                 and receipt.get("context_registration_sha256") == sha256(_canonical(context)).hexdigest()
                 and receipt.get("pdf_source") == context["pdf_source"]
                 and receipt.get("registry_ref") == actual_registry_ref and receipt.get("renderer_ref") == current_renderer
                 and receipt.get("permission_grants") == _PERMISSIONS
                 and receipt.get("source_values_changed") is False and receipt.get("unknown_columns_promoted") is False
                 and receipt.get("source_bindings_rechecked_from_original_loaded") is True
                 and receipt.get("manual_review_interpretation_replayed") is False
                 and receipt.get("historical_review_refs_are_immutable_inputs_not_new_manual_review") is True
                 and receipt.get("recheck_is_not_a_substitute_for_fresh_warm_and_cold_authentication") is True,
                 "PDF auth registry/renderer/context binding drifted")
        root = _safe_path(Path(receipt["source_pdf_root"]), (Path(receipt["source_pdf_root"]),), directory=True)
        expected = [actual_registry_ref, receipt["pdf_ref"], current_renderer, receipt["manual_review_ref"]]
        _require(receipt["pdf_ref"]["path"] == (root / context["pdf_source"]["logical_name"]).as_posix()
                 and receipt["pdf_ref"]["sha256"] == context["pdf_source"]["sha256"]
                 and receipt["pdf_ref"]["size_bytes"] == context["pdf_source"]["size_bytes"], "PDF auth source ref drifted")
        _require(len(receipt["visual_receipts"]) == len(context["review_evidence"]["visual_refs"]), "PDF auth visual axis drifted")
        for observed, visual in zip(receipt["visual_receipts"], context["review_evidence"]["visual_refs"], strict=True):
            for key in ("physical_page", "dpi", "renderer_version", "width_pixels", "height_pixels"):
                _require(observed.get(key) == visual[key] and type(observed.get(key)) is type(visual[key]), "PDF auth visual metadata drifted")
            _require(observed.get("stdout_equals_registered_png") is True
                     and observed.get("stdout_sha256") == visual["png_ref"]["sha256"]
                     and type(observed.get("stdout_size_bytes")) is int
                     and observed["stdout_size_bytes"] == visual["png_ref"]["size_bytes"], "PDF auth stdout proof drifted")
            _require(observed.get("stdout_render_command") == [renderer_path.as_posix(), "-f", str(visual["physical_page"]),
                     "-l", str(visual["physical_page"]), "-singlefile", "-r", "144", "-png", receipt["pdf_ref"]["path"]],
                     "PDF auth command gained a file prefix or changed")
            for key, binding in (("png_ref", visual["png_ref"]), ("render_receipt_ref", visual["render_receipt_ref"])):
                _require(all(observed[key].get(field) == binding[field] for field in ("path", "sha256", "size_bytes")),
                         "PDF auth evidence ref detached")
                expected.append(observed[key])
        _require(all(receipt["manual_review_ref"].get(key) == context["review_evidence"]["manual_review_ref"][key]
                     for key in ("path", "sha256", "size_bytes")), "PDF auth manual review ref detached")
        _require(receipt.get("input_refs") == expected, "PDF auth input-ref axis drifted")
        for reference in expected:
            roots = ((_REPO_ROOT,) if reference["path"] == actual_registry_ref["path"] else
                     _RENDERER_ROOTS if reference["path"] == current_renderer["path"] else
                     (root,) if reference["path"] == receipt["pdf_ref"]["path"] else _EVIDENCE_ROOTS)
            _checked_ref(reference, roots)
