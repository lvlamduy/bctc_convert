"""Pure declarative SECTION.title_exact private-clone replay, not approval.

No I/O, PDF interpretation, provider, source mutation or production authority.
The future integration MUST independently pin registry bytes, authenticate original
DB/manifest/PDF identity and fresh pixels, and derive the legacy target axis from
the unchanged authenticated thirteen-repair specification. Candidate hashes and
review refs are metadata here; neither caller seals nor this module grant approval.
"""
from __future__ import annotations

import json
import re
from copy import deepcopy
from hashlib import sha256

_FORMAT = "INCOME_TAX_SECTION_CAPTION_REPAIR_REGISTRY_V1"
_STATUS = "EXACT_DECLARED_SECTION_CAPTION_CLONE_REPLAY_NO_EXTERNAL_AUTHENTICATION"
_OBJECT_HASH_DOMAIN = "UTF8_JSON_ENSURE_ASCII_FALSE_SORTED_COMPACT_ONE_FINAL_LF"
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_DOC = re.compile(r"gfpstorev1:document:[0-9a-f]{64}\Z")
_VID = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_FLAGS = {
    "registry_approval_authenticated": False,
    "review_reference_bytes_authenticated": False,
    "source_database_authenticated": False,
    "pdf_bytes_authenticated": False,
    "fresh_pixels_authenticated": False,
    "legacy_axis_independently_authenticated": False,
    "report_scope_permission_granted": False,
    "entity_permission_granted": False,
    "unit_permission_granted": False,
    "period_permission_granted": False,
    "amount_permission_granted": False,
    "production_permission_granted": False,
    "acceptance_permission_granted": False,
}


class SectionCaptionRepairV1Error(ValueError):
    """Declarative structure or exact original-source clone replay drifted."""


def _require(ok, message):
    if not ok:
        raise SectionCaptionRepairV1Error(message)


def _text(value):
    _require(type(value) is str and bool(value), "Nonempty raw string required")
    _require(not any(ord(c) < 32 and c not in "\t\r\n" or 0xD800 <= ord(c) <= 0xDFFF
                     for c in value), "Noncanonical raw string")
    return value


def _shape(value, keys):
    _require(type(value) is dict and set(value) == set(keys.split()), "Exact object schema required")


def _positive(value):
    _require(type(value) is int and value > 0, "Positive plain integer required")


def _hash(value):
    _require(type(value) is str and _SHA.fullmatch(value) is not None, "Exact SHA256 required")


def _json(value):
    # Reject tuple/custom mapping/key coercion, nonfinite values and cycles;
    # keep JSON numeric types distinct in canonical bytes.
    def check(item):
        if type(item) is dict:
            _require(all(type(key) is str for key in item), "String JSON keys required")
            for key, child in item.items():
                _text(key)
                check(child)
        elif type(item) is list:
            for child in item:
                check(child)
        elif type(item) is str:
            _require(not any(0xD800 <= ord(c) <= 0xDFFF for c in item), "JSON surrogate forbidden")
        else:
            _require(item is None or type(item) in {bool, int, float}, "Plain JSON values required")
    try:
        check(value)
        return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                           allow_nan=False) + "\n").encode("utf-8")
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        raise SectionCaptionRepairV1Error("Noncanonical JSON") from exc


def _digest(value):
    return sha256(_json(value)).hexdigest()


def _ref(value):
    _shape(value, "path sha256 size_bytes")
    _text(value["path"])
    _hash(value["sha256"])
    _positive(value["size_bytes"])


def _pdf(value):
    _shape(value, "logical_name sha256 size_bytes")
    _text(value["logical_name"])
    _hash(value["sha256"])
    _positive(value["size_bytes"])


def validate_section_caption_registry_v1(registry):
    """Validate neutral declarations only; no supplied hash/flag is approval."""
    _json(registry)
    _shape(registry, "format_version family_id sources")
    _require(registry["format_version"] == _FORMAT and registry["family_id"] == "INCOME_TAX",
             "Declarative caption registry format required")
    _require(type(registry["sources"]) is list, "Source list required")
    source_axes = [set(), set()]
    repair_ids, targets, page_axes = set(), set(), set()
    for source in registry["sources"]:
        _shape(source, "document_id pdf_source repairs")
        _require(type(source["document_id"]) is str and _DOC.fullmatch(source["document_id"]) is not None,
                 "Exact document ID required")
        _pdf(source["pdf_source"])
        _require(source["document_id"] == _document_id(source["pdf_source"]),
                 "Declared document ID is not derived from complete PDF identity")
        for value, seen in zip((source["document_id"], source["pdf_source"]["logical_name"]),
                               source_axes, strict=True):
            _require(value not in seen, "Duplicate registered source identity")
            seen.add(value)
        _require(type(source["repairs"]) is list and bool(source["repairs"]), "Nonempty repair list required")
        for repair in source["repairs"]:
            _shape(repair, "repair_id repair_kind locator before_exact after_exact "
                   "original_page_object_canonical_sha256 evaluation_page_object_canonical_sha256 original_section_object_canonical_sha256 "
                   "evaluation_section_object_canonical_sha256 review_evidence")
            _require(type(repair["repair_id"]) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}",
                                                                       repair["repair_id"]) is not None,
                     "Opaque unique candidate repair ID required")
            _require(repair["repair_id"] not in repair_ids, "Duplicate repair ID")
            repair_ids.add(repair["repair_id"])
            _require(repair["repair_kind"] == "SECTION_TITLE_PDF_VISIBLE_EXACT", "Caption-only repair required")
            locator = repair["locator"]
            _shape(locator, "page_json_version_id physical_page selected_page_ordinal section_id json_pointer")
            _require(type(locator["page_json_version_id"]) is str
                     and _VID.fullmatch(locator["page_json_version_id"]) is not None, "Exact page VID required")
            _positive(locator["physical_page"])
            _positive(locator["selected_page_ordinal"])
            _require(type(locator["section_id"]) is str and re.fullmatch(r"s[1-9][0-9]*", locator["section_id"]) is not None,
                     "Exact section ordinal required")
            _require(locator["json_pointer"] == f"/sections/{int(locator['section_id'][1:]) - 1}/title_exact",
                     "Only SECTION.title_exact pointer permitted")
            _text(repair["before_exact"])
            _text(repair["after_exact"])
            _require(repair["before_exact"] != repair["after_exact"], "No-op repair forbidden")
            for key in ("original_page_object_canonical_sha256", "evaluation_page_object_canonical_sha256",
                        "original_section_object_canonical_sha256", "evaluation_section_object_canonical_sha256"):
                _hash(repair[key])
            _require(repair["original_page_object_canonical_sha256"] != repair["evaluation_page_object_canonical_sha256"]
                     and repair["original_section_object_canonical_sha256"] != repair["evaluation_section_object_canonical_sha256"],
                     "Original/evaluation domains must differ for a title change")
            _shape(repair["review_evidence"], "manual_review_ref pixel_candidate_ref")
            for ref in repair["review_evidence"].values():
                _ref(ref)
            target = (source["document_id"], locator["page_json_version_id"], locator["section_id"])
            _require(target not in targets, "Duplicate caption target")
            targets.add(target)
            # No multi-caption/page composition is admitted by this first proposal.
            for kind in ("page_json_version_id", "physical_page", "selected_page_ordinal"):
                owner = None if kind == "page_json_version_id" else source["document_id"]
                page_key = (owner, kind, locator[kind])
                _require(page_key not in page_axes, "Multiple repairs per page require separate composition proof")
                page_axes.add(page_key)
    return deepcopy(registry)


def _document_id(pdf):
    """The stored-document identity domain; derivation is NOT authentication."""
    _pdf(pdf)
    material = {"source_logical_name": pdf["logical_name"], "source_sha256": pdf["sha256"],
                "source_size_bytes": pdf["size_bytes"]}
    return "gfpstorev1:document:" + _digest(material)


def _original_axis(records, pdf):
    _pdf(pdf)
    _json(records)
    _require(type(records) is list and bool(records), "Original record list required")
    identity, versions, physicals, selections = set(), set(), set(), set()
    required = {"document_id", "document_ordinal", "source_sha256", "source_logical_name",
                "page_json_version_id", "physical_page", "selected_page_ordinal", "page_json"}
    for record in records:
        _require(type(record) is dict and required <= set(record), "Original record axis incomplete")
        _require(type(record["document_id"]) is str and _DOC.fullmatch(record["document_id"]) is not None,
                 "Runtime document ID invalid")
        _hash(record["source_sha256"])
        _text(record["source_logical_name"])
        for key in ("document_ordinal", "physical_page", "selected_page_ordinal"):
            _positive(record[key])
        _require(type(record["page_json_version_id"]) is str
                 and _VID.fullmatch(record["page_json_version_id"]) is not None, "Runtime VID invalid")
        for key, seen in (("page_json_version_id", versions), ("physical_page", physicals),
                          ("selected_page_ordinal", selections)):
            _require(record[key] not in seen, "Duplicate original record axis")
            seen.add(record[key])
        identity.add((record["document_id"], record["document_ordinal"],
                      record["source_logical_name"], record["source_sha256"]))
        _require(type(record["page_json"]) is dict and type(record["page_json"].get("sections")) is list,
                 "Original page/section container invalid")
    _require(len(identity) == 1 and records[0]["source_sha256"] == pdf["sha256"]
             and records[0]["source_logical_name"] == pdf["logical_name"], "Cross-document/PDF source axis")
    _require(records[0]["document_id"] == _document_id(pdf),
             "Runtime document ID is not derived from complete declared PDF identity")
    _require([record["selected_page_ordinal"] for record in records] == sorted(selections)
             and [record["physical_page"] for record in records] == sorted(physicals),
             "Original records must preserve strictly increasing selected/physical order")
    return {record["page_json_version_id"]: record for record in records}


def _legacy_page_axis(axis):
    _require(type(axis) is list, "Explicit legacy repair page axis required")
    ids = set()
    for target in axis:
        _shape(target, "repair_id pdf_source page_json_version_id physical_page")
        _text(target["repair_id"])
        _require(target["repair_id"] not in ids, "Duplicate legacy repair identity")
        ids.add(target["repair_id"])
        _pdf(target["pdf_source"])
        _require(type(target["page_json_version_id"]) is str
                 and _VID.fullmatch(target["page_json_version_id"]) is not None, "Legacy VID invalid")
        _positive(target["physical_page"])
    return deepcopy(axis)


def apply_registered_section_caption_repairs_v1(
    original_records, *, registry, source_pdf_identity, legacy_repair_page_axis,
):
    """Return an exact declared clone and receipt; authenticate NO external input.

    Caller-supplied self-consistent alternative declarations are not approvals.
    Production wrappers must independently pin registry/source/pixel authority.
    """
    checked = validate_section_caption_registry_v1(registry)
    axis = _original_axis(original_records, source_pdf_identity)
    legacy = _legacy_page_axis(legacy_repair_page_axis)
    original_bytes = _json(original_records)
    result = json.loads(original_bytes)  # Break caller-created shared mutable aliases.
    result_axis = {record["page_json_version_id"]: record for record in result}
    occurrences = []
    identity = original_records[0]
    for source in checked["sources"]:
        matches = (source["document_id"] == identity["document_id"],
                   source["pdf_source"]["logical_name"] == source_pdf_identity["logical_name"])
        if not any(matches):
            _require(not any(repair["locator"]["page_json_version_id"] in axis for repair in source["repairs"]),
                     "Foreign source reuses selected VID")
            continue
        _require(all(matches) and source["pdf_source"] == source_pdf_identity, "Partial registered source identity")
        for repair in source["repairs"]:
            locator = repair["locator"]
            for old in legacy:
                same_source = old["pdf_source"] == source_pdf_identity
                same_name = old["pdf_source"]["logical_name"] == source_pdf_identity["logical_name"]
                same_vid = old["page_json_version_id"] == locator["page_json_version_id"]
                if same_source or same_name or same_vid:
                    _require(same_source,
                             "Legacy partial/foreign source identity")
                    _require(not same_vid and old["physical_page"] != locator["physical_page"],
                             "Caption/legacy page overlap requires separate composition proof")
            record = axis.get(locator["page_json_version_id"])
            _require(record is not None and record["physical_page"] == locator["physical_page"]
                     and record["selected_page_ordinal"] == locator["selected_page_ordinal"],
                     "Registered original page locator drifted")
            page = record["page_json"]
            _require(_digest(page) == repair["original_page_object_canonical_sha256"], "Original page bytes drifted")
            ordinal = int(locator["section_id"][1:]) - 1
            _require(ordinal < len(page["sections"]) and type(page["sections"][ordinal]) is dict,
                     "Registered section absent")
            section = page["sections"][ordinal]
            _require(_digest(section) == repair["original_section_object_canonical_sha256"]
                     and section.get("title_exact") == repair["before_exact"], "Original section/title drifted")
            modified = result_axis[locator["page_json_version_id"]]["page_json"]
            modified_section = modified["sections"][ordinal]
            modified_section["title_exact"] = repair["after_exact"]
            _require(_digest(modified) == repair["evaluation_page_object_canonical_sha256"]
                     and _digest(modified_section) == repair["evaluation_section_object_canonical_sha256"],
                     "Evaluation caption clone bytes drifted")
            restored_page = deepcopy(modified)
            restored_page["sections"][ordinal]["title_exact"] = repair["before_exact"]
            _require(_json(restored_page) == _json(page), "Non-caption page mutation")
            occurrences.append({
                "repair_id": repair["repair_id"], "locator": deepcopy(locator),
                "runtime_document_ordinal": record["document_ordinal"],
                "document_id": record["document_id"], "pdf_source": deepcopy(source_pdf_identity),
                "before_exact": repair["before_exact"], "after_exact": repair["after_exact"],
                "before_utf8_sha256": sha256(repair["before_exact"].encode("utf-8")).hexdigest(),
                "after_utf8_sha256": sha256(repair["after_exact"].encode("utf-8")).hexdigest(),
                **{key: repair[key] for key in ("original_page_object_canonical_sha256", "evaluation_page_object_canonical_sha256",
                                               "original_section_object_canonical_sha256", "evaluation_section_object_canonical_sha256")},
                "review_evidence": deepcopy(repair["review_evidence"]),
            })
    _require(_json(original_records) == original_bytes, "Original input mutated")
    restored = json.loads(_json(result))
    restored_axis = {record["page_json_version_id"]: record for record in restored}
    for occurrence in occurrences:
        locator = occurrence["locator"]
        section = restored_axis[locator["page_json_version_id"]]["page_json"]["sections"][
            int(locator["section_id"][1:]) - 1]
        section["title_exact"] = occurrence["before_exact"]
    _require(_json(restored) == original_bytes, "Non-caption original-record axis mutation")
    material = {
        "format_version": "INCOME_TAX_DECLARED_SECTION_CAPTION_CLONE_REPLAY_V1",
        "status": _STATUS, "capabilities": deepcopy(_FLAGS), "occurrences": occurrences,
        "object_hash_domain": _OBJECT_HASH_DOMAIN,
        "official_stored_blob_or_validator_hash_equivalence_claimed": False,
        "registry_object_canonical_sha256": _digest(checked),
        "declared_legacy_axis_object_canonical_sha256": _digest(legacy),
        "declared_pdf_identity": deepcopy(source_pdf_identity),
        "original_records_object_canonical_sha256": sha256(original_bytes).hexdigest(),
        "evaluation_records_object_canonical_sha256": _digest(result),
        "original_source_modified": False, "monetary_cells_modified": False,
        "private_caption_modified": bool(occurrences),
        "receipt_hash_is_approval": False, "production_integration_required": True,
    }
    return result, {**material, "receipt_id": "f39captionclonev1:" + _digest(material)}


def replay_registered_section_caption_repairs_v1(
    original_records, evaluation_records, receipt, *, registry, source_pdf_identity, legacy_repair_page_axis,
):
    """Rebuild from ORIGINAL bytes. A resealed receipt alone never replays."""
    expected_records, expected_receipt = apply_registered_section_caption_repairs_v1(
        original_records, registry=registry, source_pdf_identity=source_pdf_identity,
        legacy_repair_page_axis=legacy_repair_page_axis,
    )
    _require(_json(evaluation_records) == _json(expected_records), "Evaluation object source replay drifted")
    _require(_json(receipt) == _json(expected_receipt), "Receipt exact source replay drifted")
    return deepcopy(expected_receipt)
