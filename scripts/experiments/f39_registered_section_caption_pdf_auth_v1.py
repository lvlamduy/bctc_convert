"""Fresh registered SECTION-caption pixels/restore-lineage authentication.

The injected loader is a trusted independently pinned production boundary, not
caller JSON approval. Pure clone receipts remain unauthenticated. This module
does not open the source database: its held-FD authentication belongs to the
enclosing official source context. Warm and independent cold must both invoke
this function afresh; recheck alone cannot admit caller-created receipts.
No OCR, text extraction, PDF/source writes, scope/unit/period/value permission.
"""
from __future__ import annotations

import io
import sys
from functools import wraps
from hashlib import sha256
from pathlib import Path

import f39_registered_part_period_pdf_auth_v1 as io_auth

from bctc_ai.evaluation import gemini_json_income_tax_section_caption_repair_v1 as clone_core
from bctc_ai.storage import gemini_income_tax_raw_money_census_v1 as source_records

_REPO = Path(__file__).resolve().parents[2]
_CODE_ROOT = _REPO
_RESTORE = _REPO.parent / "restore-20260905T014806Z/objects"
_EVIDENCE = (_REPO.parent / "restore-receipts", Path("/srv/bctc-receipts"))
_LEGACY_SHA = "9aac4e448b82ee0078c007ca06a36f0e3f11c2b4f694266a1211929f16228ea4"
_MIGRATION_SHA = "2376cb2cbebdbe8d55f18679ee0982b7ee77a9bf610a5d214b75d32fe8bb6312"
_COVERAGE_SHA = "7e1c35cc26873477a53157754991a123ae2fc5fc2405470c7ba23c45980e5a35"
_PARENT_SHA = "74be9ea09905f0c7842d5a0b46bfe44f3fc5f32cc2c15b5040efcc4e99e8981b"
_ENVELOPE = "INCOME_TAX_REGISTERED_SECTION_CAPTION_AUTH_ENVELOPE_V1"
_FORMAT = "INCOME_TAX_REGISTERED_SECTION_CAPTION_PDF_AUTH_V1"
_STATUS = "PASS_REGISTERED_SECTION_CAPTION_PIXELS_AND_LOCAL_LINEAGE_NOT_FAMILY_ACCEPTANCE"
_RUNTIME_SCOPE = "RENDERER_EXECUTABLE_AND_PINNED_HELPER_PILLOW_FILES_NOT_ELF_FONTS_OR_ALL_RUNTIME"
_MAX_JSON = 8 * 1024 * 1024
_MAX_PNG = 64 * 1024 * 1024
_PERMISSIONS = {"report_scope": False, "entity": False, "unit": False, "period": False,
                "source_value": False, "family_acceptance": False, "export": False}


class GeminiIncomeTaxSectionCaptionPdfAuthV1Error(ValueError):
    """Incomplete or changed independent caption evidence fails closed."""


def _require(value, message):
    if not value:
        raise GeminiIncomeTaxSectionCaptionPdfAuthV1Error(message)


def _closed_errors(function):
    @wraps(function)
    def invoke(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except GeminiIncomeTaxSectionCaptionPdfAuthV1Error:
            raise
        except (KeyError, IndexError, TypeError, ValueError, OSError) as error:
            raise GeminiIncomeTaxSectionCaptionPdfAuthV1Error("Caption authentication failed closed") from error
    return invoke


def _canonical(value):
    return clone_core._json(value)


def _digest(value):
    return sha256(_canonical(value)).hexdigest()


def _clone(value):
    return io_auth._json_object(_canonical(value)) if type(value) is dict else io_auth._clone(value)


def _shape(value, keys):
    _require(type(value) is dict and set(value) == set(keys.split()), "Exact caption-auth schema required")


def _path(spelling, *, project_relative=False):
    _require(type(spelling) is str, "String evidence path required")
    _require(not any(char in spelling for char in "\x00\r\n\\")
             and not {".", ".."} & set(spelling.split("/")), "Unsafe evidence path spelling")
    if spelling.startswith("D:/bctc_bank/"):
        spelling = (_REPO.parent / spelling[len("D:/bctc_bank/"):]).as_posix()
    path = Path(spelling)
    _require(path.as_posix() == spelling, "Noncanonical evidence path spelling")
    return _REPO / path if project_relative and not path.is_absolute() else path


def _read(reference, roots, *, project_relative=False, json_value=False, maximum=None):
    _shape(reference, "path sha256 size_bytes")
    path = _path(reference["path"], project_relative=project_relative)
    observed, raw = io_auth._checked_ref({**reference, "path": path.as_posix()}, roots,
                                        maximum=maximum, retain=json_value)
    return observed, io_auth._json_object(raw) if json_value else raw


def _s3(value):
    _shape(value, "bucket key version_id")
    _require(value["bucket"] == "test-s3-duylv" and type(value["key"]) is str
             and value["key"].startswith("bctc-ai/") and "\\" not in value["key"]
             and not any(ord(char) < 32 for char in value["key"])
             and not {"", ".", ".."} & set(value["key"].split("/"))
             and type(value["version_id"]) is str and value["version_id"].strip() == value["version_id"]
             and value["version_id"].casefold() not in {"", "null"}
             and not any(ord(char) < 32 for char in value["version_id"]),
             "Exact versioned private S3 provenance required")


def _validate_envelope(value):
    _canonical(value)
    _shape(value, "format_version family_id clone_registry legacy_source_repair_spec_ref source_version_lineages")
    _require(value["format_version"] == _ENVELOPE and value["family_id"] == "INCOME_TAX",
             "Caption envelope format/family differs")
    registry = clone_core.validate_section_caption_registry_v1(value["clone_registry"])
    _shape(value["legacy_source_repair_spec_ref"], "path sha256 size_bytes")
    _require(value["legacy_source_repair_spec_ref"]["sha256"] == _LEGACY_SHA,
             "Legacy thirteen-repair independent pin differs")
    lineages = value["source_version_lineages"]
    _require(type(lineages) is list and len(lineages) == len(registry["sources"]),
             "Caption lineage source axis differs")
    for lineage, source in zip(lineages, registry["sources"], strict=True):
        _shape(lineage, "document_id pdf_source restore_authorities pdf_object repair_evidence")
        _require(lineage["document_id"] == source["document_id"]
                 and _canonical(lineage["pdf_source"]) == _canonical(source["pdf_source"]),
                 "Caption lineage document/PDF differs")
        _shape(lineage["restore_authorities"], "migration_manifest coverage_manifest parent_snapshot_manifest")
        for authority in lineage["restore_authorities"].values():
            _shape(authority, "local_ref s3")
            _shape(authority["local_ref"], "path sha256 size_bytes")
            _s3(authority["s3"])
        obj = lineage["pdf_object"]
        _shape(obj, "bucket key version_id sha256 size_bytes")
        _s3({key: obj[key] for key in ("bucket", "key", "version_id")})
        _require(obj["sha256"] == source["pdf_source"]["sha256"]
                 and type(obj["size_bytes"]) is int
                 and obj["size_bytes"] == source["pdf_source"]["size_bytes"], "PDF object content differs")
        _require(type(lineage["repair_evidence"]) is list
                 and len(lineage["repair_evidence"]) == len(source["repairs"]), "Repair evidence axis differs")
        for evidence, repair in zip(lineage["repair_evidence"], source["repairs"], strict=True):
            _shape(evidence, "repair_id manual_review_ref pixel_candidate_ref")
            _require(evidence["repair_id"] == repair["repair_id"]
                     and _canonical({key: evidence[key] for key in ("manual_review_ref", "pixel_candidate_ref")})
                     == _canonical(repair["review_evidence"]), "Caption repair evidence detached")
    return _clone(value)


def _registry(loader, compiled=None):
    _require(callable(loader), "Trusted independent caption registry loader required")
    result = loader()
    _require(type(result) is tuple and len(result) == 2, "Caption loader result differs")
    envelope, reference = result
    envelope = _validate_envelope(envelope)
    actual, parsed = _read(reference, (_REPO,), project_relative=True, json_value=True, maximum=_MAX_JSON)
    _require(_canonical(_validate_envelope(parsed)) == _canonical(envelope),
             "Fresh approved envelope object differs from pinned file bytes")
    if compiled is not None:
        _require(type(compiled) is dict
                 and _canonical(compiled.get("income_tax_section_caption_auth_envelope")) == _canonical(envelope)
                 and _canonical(compiled.get("income_tax_section_caption_auth_envelope_ref")) == _canonical(reference),
                 "Fresh caption envelope/ref differs from compiled approval")
    return envelope, actual


def _legacy(envelope, compiled=None):
    reference, spec = _read(envelope["legacy_source_repair_spec_ref"], (_REPO,),
                            project_relative=True, json_value=True, maximum=_MAX_JSON)
    _require(reference["sha256"] == _LEGACY_SHA, "Legacy thirteen-repair actual bytes differ")
    _shape(spec, "format_version family_id render_contract repairs")
    repairs = spec["repairs"]
    _require(spec["format_version"] == "INCOME_TAX_AUTHENTICATED_SOURCE_REPAIR_SPEC_V1"
             and spec["family_id"] == "INCOME_TAX" and type(repairs) is list and len(repairs) == 13,
             "Complete thirteen-repair specification required")
    ids, axis = set(), []
    for repair in repairs:
        _require(type(repair) is dict and repair.get("repair_id") not in ids
                 and repair.get("repair_id") == "gjitfav1:repair:" + _digest(
                     {key: value for key, value in repair.items() if key != "repair_id"}),
                 "Legacy repair content identity differs")
        ids.add(repair["repair_id"])
        axis.append({"repair_id": repair["repair_id"], "pdf_source": repair["pdf_source"],
                     "page_json_version_id": repair["locator"]["page_json_version_id"],
                     "physical_page": repair["locator"]["physical_page"]})
    clone_core._legacy_page_axis(axis)
    if compiled is not None:
        _require(_canonical(compiled.get("income_tax_source_repairs")) == _canonical(repairs),
                 "Compiled legacy thirteen-repair axis differs")
    return axis, reference


def _lineage(lineage):
    authorities, parsed, refs = lineage["restore_authorities"], {}, []
    for name, expected in (("migration_manifest", _MIGRATION_SHA), ("coverage_manifest", _COVERAGE_SHA),
                           ("parent_snapshot_manifest", _PARENT_SHA)):
        authority = authorities[name]
        _require(authority["local_ref"]["sha256"] == expected, "Independent restore manifest pin differs")
        ref, value = _read(authority["local_ref"], (_RESTORE,), json_value=True, maximum=_MAX_JSON)
        refs.append(ref)
        parsed[name] = value
    migration, coverage, parent = (parsed[name] for name in (
        "migration_manifest", "coverage_manifest", "parent_snapshot_manifest"))
    _require(migration.get("schema") == "bctc-ai-machine-migration-manifest-v1"
             and coverage.get("schema") == "bctc-ai-machine-migration-source-coverage-v1"
             and authorities["migration_manifest"]["s3"]["key"] == migration["manifest_self"]["key"],
             "Migration/coverage authority identity differs")
    cover = migration["source_pdf_backup"]["coverage_manifest"]
    parent_ref = coverage["existing_parent_snapshot"]
    for source, reference, prefix in ((cover, authorities["coverage_manifest"], ""),
                                      (parent_ref, authorities["parent_snapshot_manifest"], "manifest_")):
        _require(reference["s3"]["key"] == source[prefix + "key"]
                 and reference["s3"]["version_id"] == source[prefix + "version_id"]
                 and reference["local_ref"]["sha256"] == source[prefix + "sha256"]
                 and reference["local_ref"]["size_bytes"] == source[prefix + "size_bytes"],
                 "Local restore manifest/S3 version chain differs")
    migrated_parent = migration["source_pdf_backup"]["coverage_groups"]["existing_parent_snapshot"]
    _require(all(migrated_parent[key] == parent_ref[key] for key in (
        "manifest_key", "manifest_version_id", "manifest_sha256")), "Migration/coverage parent chain differs")
    pdf, obj = lineage["pdf_source"], lineage["pdf_object"]
    files = [entry for entry in parent["files"] if entry.get("logical_path") == pdf["logical_name"]]
    objects = [entry for entry in parent["objects"] if entry.get("object_key") == obj["key"]]
    _require(len(files) == len(objects) == 1, "PDF parent file/object lineage not unique")
    file, stored = files[0], objects[0]
    _require(file.get("asset_class") == "source_pdf" and file.get("object_key") == obj["key"]
             and all(file.get(key) == stored.get(key) == obj[key] for key in ("sha256", "size_bytes"))
             and stored.get("version_id") == obj["version_id"]
             and stored.get("disposition") == "UPLOADED", "PDF exact content-object VersionId differs")
    return refs


def _source(document, loaded, original_records, registry):
    _require(type(original_records) is list and bool(original_records), "Original records required")
    ordinal = original_records[0].get("document_ordinal")
    _, records = source_records.original_income_tax_records_from_loaded_v1(
        document, loaded, run_document_ordinal=ordinal)
    _require(_canonical(records) == _canonical(original_records), "Original document/loaded/ordered records differ")
    source = document["manifest"]["document"]
    pdf = {"logical_name": source["source_logical_name"], "sha256": source["source_sha256"],
           "size_bytes": source["source_size_bytes"]}
    document_id = clone_core._document_id(pdf)
    sources = []
    for item in registry["sources"]:
        same = (item["document_id"] == document_id, item["pdf_source"]["logical_name"] == pdf["logical_name"])
        if any(same):
            _require(all(same) and _canonical(item["pdf_source"]) == _canonical(pdf),
                     "Caption registered source identity partially matches")
            sources.append(item)
        else:
            _require(not any(repair["locator"]["page_json_version_id"] in document["ids"]
                             for repair in item["repairs"]), "Foreign caption source reuses selected VID")
    for item in loaded:
        replay = item.get("source_json_replay_receipt")
        _require(type(replay) is dict and replay.get("schema") == "bctc-ai-f39-original-source-json-replay-v1"
                 and replay.get("mapping_input") == "ORIGINAL_STORED_JSON_UNMODIFIED"
                 and replay.get("all_original_cells_and_ordinals_retained") is True
                 and replay.get("replay_receipt_id") == "f39sourcejsonv1:" + _digest(
                     {key: value for key, value in replay.items() if key != "replay_receipt_id"})
                 and _canonical(replay.get("provenance")) == _canonical({key: value for key, value in item.items()
                     if key not in {"page_json", "source_json_replay_receipt"}})
                 and replay.get("canonical_json_sha256") == sha256(_canonical(item["page_json"]) + b"\n").hexdigest()
                 and replay.get("canonical_json_size_bytes") == len(_canonical(item["page_json"]) + b"\n"),
                 "Original loaded replay/BLOB/provenance differs")
        classification = replay.get("classification")
        _require(classification in {"EXACT_REPLAY", "LOSSLESS_REDUNDANT_TEXT_LABEL_COLUMN_NORMALIZATION"}
                 and type(replay.get("validated_json_sha256")) is str
                 and io_auth._SHA.fullmatch(replay["validated_json_sha256"]) is not None,
                 "Original validator classification/hash metadata differs")
        if classification == "EXACT_REPLAY":
            _require(replay.get("changed_tables") == []
                     and replay["validated_json_sha256"] == _digest(item["page_json"]),
                     "Exact original/validated object domains disagree")
        else:
            _require(type(replay.get("changed_tables")) is list and bool(replay["changed_tables"]),
                     "Lossless validator metadata needs explicit retained projection evidence")
    return pdf, document_id, sources


def _pixels(repair, pdf, pdf_ref, renderer_path):
    manual_ref, manual = _read(repair["review_evidence"]["manual_review_ref"], _EVIDENCE,
                              json_value=True, maximum=_MAX_JSON)
    candidate_ref, candidate = _read(repair["review_evidence"]["pixel_candidate_ref"], _EVIDENCE,
                                     json_value=True, maximum=_MAX_JSON)
    physical = repair["locator"]["physical_page"]
    _require(manual.get("schema") == "bctc-ai-f39-section-caption-fresh-pixel-manual-review-v1"
             and manual.get("status") == "VERIFIED_OWN_PAGE_CAPTION_TRANSCRIPTION_DISCREPANCY_NOT_REGISTERED_REPAIR_NOT_ACCEPTANCE"
             and all(manual["source_pdf"][key] == pdf[key] for key in ("logical_name", "sha256", "size_bytes"))
             and type(manual["source_pdf"]["physical_page"]) is int
             and manual["source_pdf"]["physical_page"] == physical
             and manual["pixel_candidate_ref"] == repair["review_evidence"]["pixel_candidate_ref"]
             and all(value is False for value in manual["capabilities"].values()), "Approved manual source/candidate differs")
    finding = manual["manual_visual_finding"]
    _require(finding["historically_selected_section_title_exact"] == repair["before_exact"]
             and finding["own_page_heading_exact"] == repair["after_exact"]
             and finding["proposed_pointer_kind"] == "SECTION.title_exact"
             and finding["heading_on_own_page_not_inferred_from_filename_neighbour_or_equation"] is True
             and finding["caption_clear_in_whole_page_and_crop"] is True
             and finding["no_table_title_to_create"] is True and finding["historical_table_title_exact"] is None,
             "Manual own-page exact before/after heading differs")
    _require(candidate.get("schema") == "bctc-ai-f39-registered-caption-pixel-candidate-v1"
             and candidate.get("status") == "PASS_PIXEL_CANDIDATE_ONLY_NOT_APPROVAL_NOT_REPAIR_NOT_ACCEPTANCE"
             and candidate.get("errors") == [] and type(candidate.get("exit_code")) is int
             and candidate.get("exit_code") == 0 and type(candidate.get("physical_page")) is int
             and candidate.get("physical_page") == physical
             and candidate.get("full_page_exact_historical_png_bytes") is True
             and candidate.get("production_permission_active") is False
             and candidate.get("registered_caption_repair_applied") is False
             and candidate.get("source_json_modified") is False and candidate.get("ocr_performed") is False
             and candidate.get("text_extraction_performed") is False, "Pinned inactive pixel candidate differs")
    images = manual["images_actually_viewed_by_reviewer"]
    _shape(images, "fresh_whole_page fresh_header_crop")
    full, crop = images["fresh_whole_page"], images["fresh_header_crop"]
    _require(type(full["render_dpi"]) is int and full["render_dpi"] == 200 and crop["mode"] == "RGB"
             and all(type(value[dimension]) is int and 0 < value[dimension] <= 10000
                     for value in (full, crop) for dimension in ("width_pixels", "height_pixels"))
             and crop["crop_is_reviewer_selected_not_ocr_or_mapping_geometry"] is True,
             "Reviewed pixel profile differs")
    full_ref, full_raw = io_auth._checked_ref({key: full[key] for key in ("path", "sha256", "size_bytes")},
                                             _EVIDENCE, retain=True, maximum=_MAX_PNG)
    crop_ref, crop_raw = io_auth._checked_ref({key: crop[key] for key in ("path", "sha256", "size_bytes")},
                                             _EVIDENCE, retain=True, maximum=_MAX_PNG)
    _require(full["width_pixels"] * full["height_pixels"] <= 16 * 1024 * 1024
             and io_auth._png_dimensions(full_raw) == (full["width_pixels"], full["height_pixels"])
             and io_auth._png_dimensions(crop_raw) == (crop["width_pixels"], crop["height_pixels"]),
             "Reviewed PNG header/dimensions exceeds or differs from bounded profile")
    pixel = candidate["candidate_crop"]
    _require(all(candidate["render_stdout_ref"][key] == full[key] for key in ("path", "sha256", "size_bytes"))
             and all(pixel["png_ref"][key] == crop[key] for key in ("path", "sha256", "size_bytes"))
             and all(pixel[key] == crop[key] for key in ("width_pixels", "height_pixels", "crop_box_pixels",
                                                         "rgb_sha256", "rgb_size_bytes", "mode"))
             and all(candidate["original_pdf_ref"][key] == pdf_ref[key] for key in ("path", "sha256", "size_bytes")),
             "Candidate/full/crop/source link differs")
    command = [renderer_path.as_posix(), "-f", str(physical), "-l", str(physical),
               "-singlefile", "-r", "200", "-png", pdf_ref["path"]]
    _require(candidate["render_command"] == command, "Pixel collector render gained prefix/profile/source drift")
    fresh = io_auth._tool_run(command)
    _require(fresh.stdout == full_raw, "Fresh 200dpi whole PNG differs from independently reviewed bytes")
    from PIL import Image

    box = crop["crop_box_pixels"]
    _require(type(box) is list and len(box) == 4 and all(type(value) is int for value in box)
             and 0 <= box[0] < box[2] <= full["width_pixels"]
             and 0 <= box[1] < box[3] <= full["height_pixels"], "Reviewed crop box invalid")
    with Image.open(io.BytesIO(fresh.stdout)) as image, Image.open(io.BytesIO(crop_raw)) as cropped:
        _require(image.format == cropped.format == "PNG" and getattr(image, "n_frames", 1) == 1
                 and getattr(cropped, "n_frames", 1) == 1
                 and image.size == (full["width_pixels"], full["height_pixels"]), "Reviewed whole PNG dimensions differ")
        image.load()
        cropped.load()
        raw = image.convert("RGB").crop(tuple(box)).tobytes()
        _require(cropped.mode == "RGB" and cropped.size == (crop["width_pixels"], crop["height_pixels"])
                 == (box[2] - box[0], box[3] - box[1]) and cropped.tobytes() == raw
                 and len(raw) == crop["rgb_size_bytes"] and sha256(raw).hexdigest() == crop["rgb_sha256"],
                 "Fresh crop RGB/dimensions differs from registered manual pixels")
    metadata = candidate["original_selected_source_metadata"]
    _require(metadata["page_json_version_id"] == repair["locator"]["page_json_version_id"]
             and metadata["physical_page"] == physical and metadata["source_sha256"] == pdf["sha256"]
             and metadata["section_title_exact"] == repair["before_exact"]
             and metadata["table_title_exact"] is None, "Candidate original source locator/title differs")
    return {"manual_review_ref": manual_ref, "pixel_candidate_ref": candidate_ref,
            "whole_png_ref": full_ref, "crop_png_ref": crop_ref, "crop_box_pixels": box,
            "rgb_sha256": crop["rgb_sha256"], "rgb_size_bytes": crop["rgb_size_bytes"],
            "width_pixels": crop["width_pixels"], "height_pixels": crop["height_pixels"],
            "physical_page": physical, "dpi": 200, "stdout_render_command": command,
            "fresh_whole_png_matches_reviewed_bytes": True, "fresh_crop_rgb_matches_reviewed_bytes": True}, [
                manual_ref, candidate_ref, full_ref, crop_ref]


def _pure_occurrences(source, ordinal):
    output = []
    for repair in source["repairs"]:
        output.append({
            "repair_id": repair["repair_id"], "locator": _clone(repair["locator"]),
            "runtime_document_ordinal": ordinal, "document_id": source["document_id"],
            "pdf_source": _clone(source["pdf_source"]), "before_exact": repair["before_exact"],
            "after_exact": repair["after_exact"],
            "before_utf8_sha256": sha256(repair["before_exact"].encode("utf-8")).hexdigest(),
            "after_utf8_sha256": sha256(repair["after_exact"].encode("utf-8")).hexdigest(),
            **{key: repair[key] for key in (
                "original_page_object_canonical_sha256", "evaluation_page_object_canonical_sha256",
                "original_section_object_canonical_sha256", "evaluation_section_object_canonical_sha256")},
            "review_evidence": _clone(repair["review_evidence"]),
        })
    return output


def _implementation_refs():
    from PIL import Image

    paths = [Path(__file__).resolve(), Path(io_auth.__file__).resolve(), Path(clone_core.__file__).resolve(),
             Path(source_records.__file__).resolve(), Path(Image.__file__).resolve(), Path(Image.core.__file__).resolve()]
    refs = []
    for path in paths:
        raw = path.read_bytes()
        reference = {"path": path.as_posix(), "sha256": sha256(raw).hexdigest(), "size_bytes": len(raw)}
        ref, _ = io_auth._checked_ref(reference, (_CODE_ROOT, _REPO, Path(sys.prefix)))
        refs.append(ref)
    return refs


@_closed_errors
def authenticate_registered_section_caption_pdf_v1(document, loaded, compiled, source_pdf_root, *,
                                                   original_records, registry_loader):
    """Fresh warm/cold auth; enclosing original source context owns DB authority."""
    snapshot = _digest([document, loaded, compiled, original_records])
    envelope, envelope_ref = _registry(registry_loader, compiled)
    pdf, document_id, sources = _source(document, loaded, original_records, envelope["clone_registry"])
    if not sources:
        return []
    _require(source_pdf_root is not None, "Registered section caption requires source_pdf_root")
    root = io_auth._safe_path(Path(source_pdf_root), (Path(source_pdf_root),), directory=True)
    logical = pdf["logical_name"]
    _require(not logical.startswith("/") and "\\" not in logical and ":" not in logical
             and not any(ord(char) < 32 for char in logical)
             and not {"", ".", ".."} & set(logical.split("/")), "Unsafe registered PDF logical path")
    pdf_ref, _ = io_auth._checked_ref({"path": (root / logical).as_posix(), "sha256": pdf["sha256"],
                                      "size_bytes": pdf["size_bytes"]}, (root,))
    implementations = _implementation_refs()
    legacy, legacy_ref = _legacy(envelope, compiled)
    evaluation, clone_receipt = clone_core.apply_registered_section_caption_repairs_v1(
        original_records, registry=envelope["clone_registry"], source_pdf_identity=pdf,
        legacy_repair_page_axis=legacy)
    clone_core.replay_registered_section_caption_repairs_v1(
        original_records, evaluation, clone_receipt, registry=envelope["clone_registry"],
        source_pdf_identity=pdf, legacy_repair_page_axis=legacy)
    renderer_path, renderer = io_auth._renderer()
    receipts = []
    for source in sources:
        lineage = next(item for item in envelope["source_version_lineages"] if item["document_id"] == document_id)
        lineage_refs = _lineage(lineage)
        for repair in source["repairs"]:
            pixels, pixel_refs = _pixels(repair, pdf, pdf_ref, renderer_path)
            material = {"format_version": _FORMAT, "status": _STATUS, "complete": True,
                        "repair_id": repair["repair_id"], "document_id": document_id,
                        "runtime_document_ordinal": original_records[0]["document_ordinal"],
                        "pdf_source": pdf, "source_pdf_root": root.as_posix(), "pdf_ref": pdf_ref,
                        "envelope_ref": envelope_ref, "registered_repair_object_sha256": _digest(repair),
                        "loaded_original_records_object_sha256": _digest(original_records),
                        "pure_clone_replay_receipt": clone_receipt,
                        "renderer_ref": renderer, "pixel_receipt": pixels,
                        "local_restore_lineage_verified_no_fresh_s3_get": True,
                        "source_database_authenticated_by_this_helper": False,
                        "permission_grants": _PERMISSIONS,
                        "runtime_scope": _RUNTIME_SCOPE,
                        "input_refs": [envelope_ref, legacy_ref, pdf_ref, renderer, *implementations,
                                       *lineage_refs, *pixel_refs]}
            receipts.append({**_clone(material), "receipt_id": "f39captionpdfv1:" + _digest(material)})
    _require(snapshot == _digest([document, loaded, compiled, original_records]), "Caption auth mutated source/compiled input")
    recheck_registered_section_caption_pdf_v1(receipts, registry_loader=registry_loader)
    _require(snapshot == _digest([document, loaded, compiled, original_records]), "Caption exit callbacks mutated source input")
    return receipts


@_closed_errors
def recheck_registered_section_caption_pdf_v1(receipts, *, registry_loader):
    """Fresh file/pixel exit barrier only, not admission of caller-made receipts."""
    envelope, actual_envelope = _registry(registry_loader)
    _require(type(receipts) is list, "Caption receipts must be a plain list")
    if not receipts:
        return
    legacy, legacy_ref = _legacy(envelope)
    implementations = _implementation_refs()
    renderer_path, renderer = io_auth._renderer()
    registered = {repair["repair_id"]: (source, repair) for source in envelope["clone_registry"]["sources"]
                  for repair in source["repairs"]}
    seen = set()
    for receipt in receipts:
        _require(type(receipt) is dict and receipt.get("repair_id") in registered
                 and receipt["repair_id"] not in seen, "Caption repair receipt missing/duplicate")
        seen.add(receipt["repair_id"])
        source, repair = registered[receipt["repair_id"]]
        material = {key: value for key, value in receipt.items() if key != "receipt_id"}
        _require(receipt.get("receipt_id") == "f39captionpdfv1:" + _digest(material)
                 and receipt.get("format_version") == _FORMAT and receipt.get("status") == _STATUS
                 and receipt.get("complete") is True and receipt.get("document_id") == source["document_id"]
                 and receipt.get("pdf_source") == source["pdf_source"]
                 and receipt.get("registered_repair_object_sha256") == _digest(repair)
                 and receipt.get("envelope_ref") == actual_envelope and receipt.get("renderer_ref") == renderer
                 and receipt.get("permission_grants") == _PERMISSIONS
                 and receipt.get("runtime_scope") == _RUNTIME_SCOPE
                 and type(receipt.get("runtime_document_ordinal")) is int
                 and receipt["runtime_document_ordinal"] > 0
                 and receipt.get("source_database_authenticated_by_this_helper") is False
                 and receipt.get("local_restore_lineage_verified_no_fresh_s3_get") is True,
                 "Caption receipt/source/approval/permission drifted")
        root = io_auth._safe_path(Path(receipt["source_pdf_root"]), (Path(receipt["source_pdf_root"]),), directory=True)
        pdf = source["pdf_source"]
        pdf_ref, _ = io_auth._checked_ref(receipt["pdf_ref"], (root,))
        _require(pdf_ref["path"] == (root / pdf["logical_name"]).as_posix()
                 and all(pdf_ref[key] == pdf[key] for key in ("sha256", "size_bytes")), "Caption PDF ref detached")
        lineage = next(item for item in envelope["source_version_lineages"] if item["document_id"] == source["document_id"])
        lineage_refs = _lineage(lineage)
        pixels, pixel_refs = _pixels(repair, pdf, pdf_ref, renderer_path)
        expected = [actual_envelope, legacy_ref, pdf_ref, renderer, *implementations, *lineage_refs, *pixel_refs]
        _require(receipt.get("input_refs") == expected and receipt.get("pixel_receipt") == pixels,
                 "Caption actual exit evidence axis differs")
        pure = receipt["pure_clone_replay_receipt"]
        _shape(pure, "format_version status capabilities occurrences object_hash_domain "
               "official_stored_blob_or_validator_hash_equivalence_claimed registry_object_canonical_sha256 "
               "declared_legacy_axis_object_canonical_sha256 declared_pdf_identity "
               "original_records_object_canonical_sha256 evaluation_records_object_canonical_sha256 "
               "original_source_modified monetary_cells_modified private_caption_modified "
               "receipt_hash_is_approval production_integration_required receipt_id")
        pure_material = {key: value for key, value in pure.items() if key != "receipt_id"}
        _require(pure.get("receipt_id") == "f39captionclonev1:" + _digest(pure_material)
                 and pure.get("format_version") == "INCOME_TAX_DECLARED_SECTION_CAPTION_CLONE_REPLAY_V1"
                 and pure.get("status") == clone_core._STATUS
                 and pure.get("object_hash_domain") == clone_core._OBJECT_HASH_DOMAIN
                 and pure.get("official_stored_blob_or_validator_hash_equivalence_claimed") is False
                 and pure.get("capabilities") == clone_core._FLAGS
                 and pure.get("occurrences") == _pure_occurrences(source, receipt["runtime_document_ordinal"])
                 and pure.get("declared_pdf_identity") == pdf
                 and pure.get("original_source_modified") is False and pure.get("monetary_cells_modified") is False
                 and pure.get("private_caption_modified") is True and pure.get("receipt_hash_is_approval") is False
                 and pure.get("production_integration_required") is True
                 and pure.get("registry_object_canonical_sha256") == _digest(envelope["clone_registry"])
                 and pure.get("declared_legacy_axis_object_canonical_sha256") == _digest(legacy)
                 and pure.get("original_records_object_canonical_sha256") == receipt["loaded_original_records_object_sha256"],
                 "Caption pure replay declaration detached")
        expected_keys = {
            "format_version", "status", "complete", "repair_id", "document_id", "runtime_document_ordinal",
            "pdf_source", "source_pdf_root", "pdf_ref", "envelope_ref", "registered_repair_object_sha256",
            "loaded_original_records_object_sha256", "pure_clone_replay_receipt", "renderer_ref", "pixel_receipt",
            "local_restore_lineage_verified_no_fresh_s3_get", "source_database_authenticated_by_this_helper",
            "permission_grants", "runtime_scope", "input_refs", "receipt_id"}
        _require(set(receipt) == expected_keys, "Caption auth receipt has unreviewed fields")
    expected_repairs = [repair["repair_id"] for source in envelope["clone_registry"]["sources"]
                        if source["document_id"] in {receipt["document_id"] for receipt in receipts}
                        for repair in source["repairs"]]
    _require([receipt["repair_id"] for receipt in receipts] == expected_repairs,
             "Caption receipt registered-document repair axis incomplete/reordered")
    # Last callbacks (loader, renderer, PNG/Pillow) finished. Recheck actual bytes.
    fresh_envelope, fresh_ref = _registry(registry_loader)
    _require(fresh_ref == actual_envelope and _canonical(fresh_envelope) == _canonical(envelope),
             "Caption approval changed at final barrier")
    for receipt in receipts:
        for reference in receipt["input_refs"]:
            roots = (io_auth._RENDERER_ROOTS if reference["path"] == renderer["path"] else
                     (_CODE_ROOT, _REPO, _RESTORE, *_EVIDENCE, Path(sys.prefix),
                      Path(receipt["source_pdf_root"]), Path("/usr")))
            io_auth._checked_ref(reference, roots)
