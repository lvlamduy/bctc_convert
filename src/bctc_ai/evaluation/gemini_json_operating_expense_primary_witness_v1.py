"""INACTIVE F36 PRIMARY witness primitive: metadata validation/private copying only.

No I/O, PDF authentication, registry approval, unit/period inference, source
mutation, public-query integration or mapping permission is provided here.
"""
from __future__ import annotations

import re
from typing import Any

from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import (
    _normalized,
    _without_leading_ordinal,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

FORMAT = "F36_PRIMARY_WITNESS_SPEC_V1"
POLICY = "THREE_SAME_ORIGINAL_ROW_NULLS_TO_DECLARED_PDF_VISIBLE_NONZERO_ASCII_INTEGERS"
KIND = "PRIMARY_WITNESS_NULL_TO_PDF_VISIBLE_SIGNED_INTEGER"
SPEC_KEY = "operating_expense_primary_witness_spec"
HASH_KEY = "operating_expense_primary_witness_spec_sha256"
RENDER_CONTRACT = {
    "alpha": False, "colorspace": "RGB", "format": "PNG", "render_dpi": 300,
    "renderer": "BCTC_AI_FULL_PDF_PAGE_RENDER_V1_PYMUPDF",
}
PERMISSIONS = {name: False for name in (
    "source_authenticated", "pdf_authenticated", "value_authority_granted",
    "unit_permission", "period_permission", "scope_permission",
    "mapping_permission", "financial_acceptance",
)}
_HEX = re.compile(r"[0-9a-f]{64}")
_VID = re.compile(r"gfpstorev1:json:[0-9a-f]{64}")
_DOC = re.compile(r"gfpstorev1:document:[0-9a-f]{64}")
_NUMBER = r"(?:[1-9][0-9]*|[1-9][0-9]{0,2}(?:,[0-9]{3})+|[1-9][0-9]{0,2}(?:\.[0-9]{3})+)"
_TOKEN = re.compile(r"(?:-?" + _NUMBER + r"|\(" + _NUMBER + r"\))")
_HASH_FIELDS = {
    "original_page_json_sha256", "original_section_json_sha256",
    "original_table_json_sha256", "original_row_json_sha256",
}


class F36PrimaryWitnessV1Error(ValueError):
    pass


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise F36PrimaryWitnessV1Error(message)


def _shape(value: Any, fields: set[str]) -> bool:
    return type(value) is dict and set(value) == fields


def _positive(value: Any) -> bool:
    return type(value) is int and value > 0


def _matches(pattern: re.Pattern[str], value: Any) -> bool:
    return type(value) is str and pattern.fullmatch(value) is not None


def _logical(value: Any) -> bool:
    return (type(value) is str and bool(value) and "\\" not in value
            and ":" not in value and not value.startswith("/")
            and all(part not in {"", ".", ".."} for part in value.split("/")))


def _hashes(page: dict, section: dict, table: dict, row: dict) -> dict:
    return {
        "original_page_json_sha256": canonical_json_sha256_v1(page),
        "original_section_json_sha256": canonical_json_sha256_v1(section),
        "original_table_json_sha256": canonical_json_sha256_v1(table),
        "original_row_json_sha256": canonical_json_sha256_v1(row),
    }


def _row_identity(witness: dict) -> dict:
    return {key: value for key, value in witness["locator"].items()
            if key != "column_ordinal"}


def validate_f36_primary_witness_spec_v1(value: Any) -> dict:
    """Check declarations and content IDs; this does not approve their facts."""
    canonical_json_bytes_v1(value)  # Preserve strict JSON types, including keys.
    _need(_shape(value, {"family_id", "format_version", "policy",
                        "render_contract", "witness_axis_sha256", "witnesses"})
          and value["family_id"] == "OPERATING_EXPENSE"
          and value["format_version"] == FORMAT and value["policy"] == POLICY
          and same_typed_json_v1(value["render_contract"], RENDER_CONTRACT)
          and type(value["witnesses"]) is list and len(value["witnesses"]) == 3,
          "invalid PRIMARY witness specification")
    seen = set()
    row_identity = None
    shared = None
    for witness in value["witnesses"]:
        _need(_shape(witness, {"witness_id", "witness_kind", "source", "locator",
                              "original_object_hashes", "expected_context",
                              "before_exact", "after_exact", "observed_pdf_glyph",
                              "render", "crop_evidence"}),
              "invalid PRIMARY witness fields")
        source, loc = witness["source"], witness["locator"]
        context, render, crop = (witness["expected_context"], witness["render"],
                                 witness["crop_evidence"])
        _need(_shape(source, {"source_logical_name", "source_sha256", "source_size_bytes"})
              and _logical(source["source_logical_name"])
              and _matches(_HEX, source["source_sha256"])
              and _positive(source["source_size_bytes"]),
              "invalid PRIMARY witness source")
        _need(_shape(loc, {"page_json_version_id", "physical_page", "selected_page_ordinal",
                          "section_id", "table_id", "row_ordinal", "column_ordinal"})
              and _matches(_VID, loc["page_json_version_id"])
              and all(_positive(loc[k]) for k in ("physical_page", "selected_page_ordinal",
                                                   "row_ordinal", "column_ordinal"))
              and _matches(re.compile(r"s[1-9][0-9]*"), loc["section_id"])
              and _matches(re.compile(r"t[1-9][0-9]*"), loc["table_id"]),
              "invalid PRIMARY witness locator")
        _need(_shape(witness["original_object_hashes"], _HASH_FIELDS)
              and all(_matches(_HEX, h) for h in witness["original_object_hashes"].values()),
              "invalid named ORIGINAL object hashes")
        _need(_shape(context, {"page_status", "content_kind", "statement_type",
                              "row_label_exact", "hierarchy_path_exact", "row_kind",
                              "column_header_path_exact", "column_value_kind"})
              and context["page_status"] == "PRIMARY_FINANCIAL_STATEMENT"
              and context["content_kind"] == "PRIMARY_STATEMENT"
              and context["statement_type"] == "INCOME_STATEMENT"
              and type(context["row_label_exact"]) is str and bool(context["row_label_exact"])
              and type(context["hierarchy_path_exact"]) is list
              and all(type(x) is str and bool(x) for x in context["hierarchy_path_exact"])
              and type(context["row_kind"]) is str
              and context["row_kind"] in {"ITEM", "SUBTOTAL", "TOTAL"}
              and type(context["column_header_path_exact"]) is list
              and bool(context["column_header_path_exact"])
              and all(type(x) is str and bool(x) for x in context["column_header_path_exact"])
              and context["column_value_kind"] == "MONEY",
              "invalid PRIMARY/INCOME raw context")
        _need(witness["witness_kind"] == KIND and witness["before_exact"] is None
              and _matches(_TOKEN, witness["after_exact"])
              and type(witness["observed_pdf_glyph"]) is str
              and witness["after_exact"] == witness["observed_pdf_glyph"],
              "replacement is not a declared nonzero raw ASCII integer")
        _need(_shape(render, {"image_sha256", "image_size_bytes", "media_type",
                             "physical_page", "pixel_height", "pixel_width",
                             "render_dpi", "render_receipt_sha256"})
              and all(_positive(render[k]) for k in ("image_size_bytes", "physical_page",
                                                       "pixel_height", "pixel_width", "render_dpi"))
              and render["physical_page"] == loc["physical_page"]
              and render["render_dpi"] == 300 and render["media_type"] == "image/png"
              and _matches(_HEX, render["image_sha256"])
              and _matches(_HEX, render["render_receipt_sha256"]),
              "invalid full-page render declaration")
        _need(_shape(crop, {"bbox_pixels_xyxy", "pixel_height", "pixel_width", "rgb_sha256"}),
              "invalid crop fields")
        box = crop["bbox_pixels_xyxy"]
        _need(type(box) is list and len(box) == 4 and all(type(x) is int for x in box)
              and 0 <= box[0] < box[2] <= render["pixel_width"]
              and 0 <= box[1] < box[3] <= render["pixel_height"]
              and _positive(crop["pixel_width"]) and _positive(crop["pixel_height"])
              and crop["pixel_width"] == box[2] - box[0]
              and crop["pixel_height"] == box[3] - box[1]
              and _matches(_HEX, crop["rgb_sha256"]), "invalid bounded RGB crop")
        material = {k: v for k, v in witness.items() if k != "witness_id"}
        _need(witness["witness_id"] == "gjoepwv1:witness:" + canonical_json_sha256_v1(material),
              "PRIMARY witness content ID drifted")
        key = loc["column_ordinal"]
        _need(key not in seen, "duplicate PRIMARY witness cell")
        seen.add(key)
        this_shared = {k: witness[k] for k in ("source", "original_object_hashes", "render")}
        this_shared["context"] = {k: v for k, v in context.items()
                                  if k != "column_header_path_exact"}
        if row_identity is None:
            row_identity, shared = _row_identity(witness), this_shared
        _need(same_typed_json_v1(_row_identity(witness), row_identity)
              and same_typed_json_v1(this_shared, shared),
              "PRIMARY witnesses must share exactly one ORIGINAL source row and render")
    _need(value["witness_axis_sha256"] == canonical_json_sha256_v1(value["witnesses"]),
          "PRIMARY witness axis content hash drifted")
    return canonical_clone_v1(value)


def _primary_witness_projection_v1(*, pages: Any, document: Any,
                                   selected_page_axis: Any, compiled_specs: Any) -> tuple[dict, list]:
    """Validate ALL before-images on ORIGINAL input; only then clone and edit.

    The document/page axes are the unchanged four/seven-field shared-query axes.
    PDF size binds through the declared document content ID, not a fabricated
    source_size_bytes field on that four-field runtime document axis.
    """
    doc_fields = {"document_id", "document_ordinal", "source_logical_name", "source_sha256"}
    _need(_shape(document, doc_fields) and _positive(document["document_ordinal"])
          and _matches(_DOC, document["document_id"])
          and _logical(document["source_logical_name"])
          and _matches(_HEX, document["source_sha256"]), "invalid selected document identity")
    page_fields = doc_fields | {"page_json_version_id", "physical_page", "selected_page_ordinal"}
    _need(type(pages) is dict and type(selected_page_axis) is list
          and type(compiled_specs) is dict, "invalid PRIMARY projection input containers")
    canonical_json_bytes_v1(pages)
    axis, selected, physical = {}, set(), set()
    for item in selected_page_axis:
        _need(_shape(item, page_fields)
              and all(same_typed_json_v1(item[k], document[k]) for k in doc_fields)
              and _matches(_VID, item["page_json_version_id"])
              and _positive(item["physical_page"]) and _positive(item["selected_page_ordinal"]),
              "selected page source/typed locator identity drifted")
        vid = item["page_json_version_id"]
        _need(vid not in axis and item["selected_page_ordinal"] not in selected
              and item["physical_page"] not in physical, "duplicate selected page identity")
        axis[vid] = item
        selected.add(item["selected_page_ordinal"])
        physical.add(item["physical_page"])
    _need(set(pages) == set(axis) and all(_matches(_VID, k) and type(v) is dict
                                        for k, v in pages.items()),
          "original pages do not equal complete selected-document page axis")
    present = (SPEC_KEY in compiled_specs, HASH_KEY in compiled_specs)
    _need(present[0] == present[1], "partial compiled PRIMARY witness authority")
    if not present[0]:
        return canonical_clone_v1(pages), []
    spec = validate_f36_primary_witness_spec_v1(compiled_specs[SPEC_KEY])
    spec_hash = canonical_json_sha256_v1(spec)
    _need(compiled_specs[HASH_KEY] == spec_hash, "compiled PRIMARY witness spec drifted")
    witnesses = spec["witnesses"]
    source = witnesses[0]["source"]
    source_doc = "gfpstorev1:document:" + canonical_json_sha256_v1(source)
    same_source = (document["source_sha256"] == source["source_sha256"]
                   and document["source_logical_name"] == source["source_logical_name"])
    if not same_source:
        _need(document["source_sha256"] != source["source_sha256"]
              and document["source_logical_name"] != source["source_logical_name"]
              and document["document_id"] != source_doc, "partial witness source identity collision")
        return canonical_clone_v1(pages), []
    _need(document["document_id"] == source_doc, "witness PDF size/document identity drifted")
    aliases = compiled_specs.get("topology", {}).get("parent", {}).get("aliases")
    _need(type(aliases) is list and bool(aliases)
          and all(type(alias) is str and bool(alias) for alias in aliases),
          "configured family parent authority absent")
    checked = []
    for witness in witnesses:
        loc, expected = witness["locator"], witness["expected_context"]
        vid = loc["page_json_version_id"]
        _need(vid in axis and axis[vid]["physical_page"] == loc["physical_page"]
              and axis[vid]["selected_page_ordinal"] == loc["selected_page_ordinal"],
              "witness is outside exact selected ORIGINAL page")
        page = pages[vid]
        try:
            section = page["sections"][int(loc["section_id"][1:]) - 1]
            table = section["tables"][int(loc["table_id"][1:]) - 1]
            row = table["rows"][loc["row_ordinal"] - 1]
            column = table["columns"][loc["column_ordinal"] - 1]
            before = row["values_exact"][loc["column_ordinal"] - 1]
        except (KeyError, IndexError, TypeError) as exc:
            raise F36PrimaryWitnessV1Error("witness raw positional locator does not resolve") from exc
        _need(all(type(obj) is dict for obj in (section, table, row, column))
              and type(page["sections"]) is list and type(section["tables"]) is list
              and type(table["rows"]) is list and type(table["columns"]) is list
              and type(row.get("values_exact")) is list,
              "witness raw table/row/column shape invalid")
        _need(_hashes(page, section, table, row) == witness["original_object_hashes"],
              "named ORIGINAL page/section/table/row before hash drifted")
        actual = {
            "page_status": page.get("status"), "content_kind": section.get("content_kind"),
            "statement_type": section.get("statement_type"), "row_label_exact": row.get("label_exact"),
            "hierarchy_path_exact": row.get("hierarchy_path_exact"), "row_kind": row.get("row_kind"),
            "column_header_path_exact": column.get("header_path_exact"),
            "column_value_kind": column.get("value_kind"),
        }
        _need(same_typed_json_v1(actual, expected) and before is None,
              "PRIMARY raw kind/owner/header or NULL before-image drifted")
        _need(_without_leading_ordinal(_normalized(row["label_exact"]))
              in {_normalized(alias) for alias in aliases}, "row is not the configured family parent")
        checked.append((witness, page, section, table, row))
    # No clone edit exists until every original before-image above has passed.
    private = canonical_clone_v1(pages)
    for witness, *_objects in checked:
        loc = witness["locator"]
        private[loc["page_json_version_id"]]["sections"][int(loc["section_id"][1:]) - 1][
            "tables"][int(loc["table_id"][1:]) - 1]["rows"][loc["row_ordinal"] - 1][
                "values_exact"][loc["column_ordinal"] - 1] = witness["after_exact"]
    receipts = []
    for witness, *_objects in checked:
        loc = witness["locator"]
        page = private[loc["page_json_version_id"]]
        section = page["sections"][int(loc["section_id"][1:]) - 1]
        table = section["tables"][int(loc["table_id"][1:]) - 1]
        row = table["rows"][loc["row_ordinal"] - 1]
        material = {
            "format_version": "F36_PRIMARY_WITNESS_PRIVATE_PROJECTION_RECEIPT_V1",
            "rule": "INACTIVE_METADATA_ONLY_ATOMIC_ORIGINAL_NULL_TRANSCRIPTION_PRIVATE_CLONE",
            "witness": canonical_clone_v1(witness), "witness_spec_sha256": spec_hash,
            "original_object_hashes": canonical_clone_v1(witness["original_object_hashes"]),
            "evaluation_object_hashes": {
                k.replace("original_", "evaluation_", 1): v
                for k, v in _hashes(page, section, table, row).items()
            },
            "permissions": canonical_clone_v1(PERMISSIONS),
        }
        receipts.append({**material, "receipt_id":
                         "gjoepwv1:projection:" + canonical_json_sha256_v1(material)})
    return private, receipts
