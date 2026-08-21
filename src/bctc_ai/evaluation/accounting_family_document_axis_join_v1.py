"""Exact semantic/numeric/render join for one complete accounting document.

Fresh VietOCR supplies label text, PP-OCRv6 medium recognition supplies raw
numeric proposals for the same immutable crops, and authenticated page-render
snapshots supply dimensions only for pages selected by whole-document topology.
Pages outside the selected region retain ``page_width=None``: their text still
participates in uniqueness, but they need not be re-rendered merely to reject a
second structural match.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from bctc_ai.evaluation import family_first_authenticated_page_region_v1 as render_v1
from bctc_ai.evaluation import family_first_semantic_index_v1 as semantic_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "AccountingFamilyDocumentAxisJoinV1Error",
    "build_accounting_family_document_axis_join_v1",
    "project_accounting_family_document_pages_v1",
    "validate_accounting_family_document_axis_join_replay_v1",
]


FORMAT_VERSION = "ACCOUNTING_FAMILY_DOCUMENT_AXIS_JOIN_V1"
CLAIM_BOUNDARY = (
    "EXACT_FRESH_VIETOCR_LABEL_AND_PPOCRV6_MEDIUM_RECOGNITION_JOIN_ON_SAME_"
    "IMMUTABLE_COMPLETE_DOCUMENT_CROP_AXIS_WITH_AUTHENTICATED_DIMENSIONS_ONLY_"
    "FOR_SELECTED_PAGES_NO_STRUCTURE_NUMERIC_PERIOD_UNIT_ACCOUNTING_SCHEMA_"
    "MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_SAFETY = {
    "all_document_lines_retained": True,
    "bank_file_note_page_period_family_used_for_joining": False,
    "detector_geometry_treated_as_numeric_recognition": False,
    "mapping_authority": False,
    "nonselected_pages_need_not_be_rendered": True,
    "numeric_authority": False,
    "ppocrv6_medium_recognition_used_as_raw_proposal_only": True,
    "raw_record_self_authenticating": False,
    "schema_authority": False,
    "vietocr_transformer_used_as_semantic_text_proposal": True,
}
_RESULT_FIELDS = {
    "claim_boundary",
    "document_axis_id",
    "document_ordinal",
    "format_version",
    "metrics",
    "pages",
    "safety",
    "semantic_document_id",
    "source_binding_sha256",
}
_METRIC_FIELDS = {
    "line_count",
    "page_count",
    "page_count_with_authenticated_dimensions",
}
_PAGE_FIELDS = {"lines", "page_sequence", "page_width"}
_LINE_FIELDS = {
    "bbox",
    "crop_ref",
    "line_ordinal",
    "numeric_recognition",
    "sample_id",
    "vietocr_text",
}
_RECOGNITION_FIELDS = {"raw_prediction", "reader_score"}
_REF_FIELDS = {"path", "sha256", "size_bytes"}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_NUMERIC_DOCUMENT_FIELDS = {
    "document_ordinal",
    "lines",
    "private_provenance",
    "source_pdf_ref",
}
_NUMERIC_LINE_FIELDS = {
    "crop_ref",
    "line_ordinal",
    "physical_page",
    "raw_prediction",
    "reader_score",
    "sample_id",
    "source_bbox_raw_pixels",
}
_RENDER_FIELDS = {
    "archive_id",
    "authority",
    "document_ordinal",
    "format_version",
    "index_id",
    "physical_page",
    "plan_id",
    "render_id",
    "render_png_bytes",
    "render_ref",
    "state",
}


class AccountingFamilyDocumentAxisJoinV1Error(ValueError):
    """The complete source axes, crop identity, render, or replay drifted."""


def _error(message: str) -> AccountingFamilyDocumentAxisJoinV1Error:
    return AccountingFamilyDocumentAxisJoinV1Error(message)


def _semantic_document(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != semantic_v1._DOCUMENT_FIELDS
        or value["format_version"] != semantic_v1.DOCUMENT_FORMAT_VERSION
        or type(value["document_ordinal"]) is not int
        or value["document_ordinal"] <= 0
        or type(value["page_count"]) is not int
        or value["page_count"] <= 0
        or type(value["line_count"]) is not int
        or value["line_count"] <= 0
        or type(value["pages"]) is not list
        or len(value["pages"]) != value["page_count"]
    ):
        raise _error("semantic document contract drifted")
    line_count = 0
    prior_sample = ""
    for physical_page, page in enumerate(value["pages"], 1):
        if (
            type(page) is not dict
            or set(page) != semantic_v1._PAGE_FIELDS
            or page["physical_page"] != physical_page
            or type(page["line_count"]) is not int
            or type(page["lines"]) is not list
            or page["line_count"] != len(page["lines"])
        ):
            raise _error("semantic document page axis drifted")
        for line_ordinal, line in enumerate(page["lines"]):
            if (
                type(line) is not dict
                or set(line) != semantic_v1._LINE_FIELDS
                or line["format_version"] != semantic_v1.LINE_FORMAT_VERSION
                or line["line_ordinal"] != line_ordinal
                or type(line["sample_id"]) is not str
                or not line["sample_id"]
                or line["sample_id"] <= prior_sample
                or type(line["vietocr_text"]) is not str
            ):
                raise _error("semantic document line axis drifted")
            prior_sample = line["sample_id"]
            line_count += 1
    if line_count != value["line_count"]:
        raise _error("semantic document line denominator drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("document_id")
    if identity != "ffsiv1:document:" + canonical_json_sha256_v1(material):
        raise _error("semantic document identity drifted")
    return canonical_clone_v1(value)


def _numeric_document(value: Any, semantic: dict[str, Any]) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _NUMERIC_DOCUMENT_FIELDS
        or value["document_ordinal"] != semantic["document_ordinal"]
        or type(value["lines"]) is not list
        or len(value["lines"]) != semantic["line_count"]
        or not same_typed_json_v1(value["private_provenance"], semantic["private_provenance"])
        or not same_typed_json_v1(value["source_pdf_ref"], semantic["source_pdf_ref"])
    ):
        raise _error("numeric document/source binding drifted")
    for line in value["lines"]:
        if (
            type(line) is not dict
            or set(line) != _NUMERIC_LINE_FIELDS
            or type(line["physical_page"]) is not int
            or not 1 <= line["physical_page"] <= semantic["page_count"]
            or type(line["line_ordinal"]) is not int
            or line["line_ordinal"] < 0
            or type(line["raw_prediction"]) is not str
            or type(line["reader_score"]) is not float
            or not 0 <= line["reader_score"] <= 1
            or type(line["sample_id"]) is not str
            or not line["sample_id"]
        ):
            raise _error("numeric document line contract drifted")
    return canonical_clone_v1(value)


def _render_snapshot(value: Any, *, document_ordinal: int, page_count: int) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _RENDER_FIELDS
        or value["format_version"] != render_v1.RENDER_FORMAT_VERSION
        or value["state"] != "AUTHENTICATED_EXACT_SOURCE_PAGE_RENDER_SNAPSHOT"
        or not same_typed_json_v1(value["authority"], render_v1._RENDER_AUTHORITY)
        or value["document_ordinal"] != document_ordinal
        or type(value["physical_page"]) is not int
        or not 1 <= value["physical_page"] <= page_count
        or type(value["render_png_bytes"]) is not bytes
    ):
        raise _error("authenticated render snapshot contract drifted")
    try:
        reference = render_v1._render_reference(value["render_ref"])
        image = render_v1._png_image(value["render_png_bytes"])
    except render_v1.FamilyFirstAuthenticatedPageRegionV1Error as exc:
        raise _error("authenticated render snapshot bytes drifted") from exc
    if (
        len(value["render_png_bytes"]) != reference["size_bytes"]
        or hashlib.sha256(value["render_png_bytes"]).hexdigest() != reference["sha256"]
        or image.width != reference["pixel_width"]
        or image.height != reference["pixel_height"]
    ):
        raise _error("authenticated render snapshot reference differs from its bytes")
    material = {
        key: canonical_clone_v1(item)
        for key, item in value.items()
        if key not in {"render_id", "render_png_bytes"}
    }
    if value["render_id"] != "ffaprv1:render:" + canonical_json_sha256_v1(material):
        raise _error("authenticated render snapshot identity drifted")
    record = {
        key: canonical_clone_v1(item) for key, item in value.items() if key != "render_png_bytes"
    }
    return {**record, "render_png_bytes": bytes(value["render_png_bytes"])}


def _render_widths(
    value: Any, *, document_ordinal: int, page_count: int
) -> dict[int, tuple[int, int]]:
    if type(value) is not tuple:
        raise _error("selected render snapshots must be one exact tuple")
    result: dict[int, tuple[int, int]] = {}
    shared_index_id: str | None = None
    shared_archive_id: str | None = None
    for raw in value:
        snapshot = _render_snapshot(raw, document_ordinal=document_ordinal, page_count=page_count)
        page = snapshot["physical_page"]
        if page in result:
            raise _error("selected render snapshot page repeats")
        if shared_index_id is None:
            shared_index_id = snapshot["index_id"]
            shared_archive_id = snapshot["archive_id"]
        elif snapshot["index_id"] != shared_index_id or snapshot["archive_id"] != shared_archive_id:
            raise _error("selected render snapshots belong to different live indices")
        result[page] = (
            snapshot["render_ref"]["pixel_width"],
            snapshot["render_ref"]["pixel_height"],
        )
    return result


def _join_pages(
    semantic: dict[str, Any], numeric: dict[str, Any], dimensions: dict[int, tuple[int, int]]
) -> list[dict[str, Any]]:
    numeric_cursor = 0
    pages = []
    for semantic_page in semantic["pages"]:
        page_number = semantic_page["physical_page"]
        width, height = dimensions.get(page_number, (None, None))
        lines = []
        for semantic_line in semantic_page["lines"]:
            numeric_line = numeric["lines"][numeric_cursor]
            if (
                numeric_line["physical_page"] != page_number
                or numeric_line["line_ordinal"] != semantic_line["line_ordinal"]
                or numeric_line["sample_id"] != semantic_line["sample_id"]
                or not same_typed_json_v1(numeric_line["crop_ref"], semantic_line["crop_ref"])
                or not same_typed_json_v1(
                    numeric_line["source_bbox_raw_pixels"],
                    semantic_line["source_bbox_raw_pixels"],
                )
            ):
                raise _error("semantic and numeric document crop axes differ")
            bbox = semantic_line["source_bbox_raw_pixels"]
            if (
                type(bbox) is not list
                or len(bbox) != 4
                or any(type(item) is not int for item in bbox)
                or bbox[0] < 0
                or bbox[1] < 0
                or bbox[2] <= bbox[0]
                or bbox[3] <= bbox[1]
                or (width is not None and (bbox[2] > width or bbox[3] > height))
            ):
                raise _error("joined source bbox lies outside its authenticated page")
            lines.append(
                {
                    "bbox": canonical_clone_v1(bbox),
                    "crop_ref": canonical_clone_v1(semantic_line["crop_ref"]),
                    "line_ordinal": semantic_line["line_ordinal"],
                    "numeric_recognition": {
                        "raw_prediction": numeric_line["raw_prediction"],
                        "reader_score": numeric_line["reader_score"],
                    },
                    "sample_id": semantic_line["sample_id"],
                    "vietocr_text": semantic_line["vietocr_text"],
                }
            )
            numeric_cursor += 1
        pages.append(
            {
                "lines": lines,
                "page_sequence": page_number,
                "page_width": width,
            }
        )
    if numeric_cursor != len(numeric["lines"]):
        raise _error("numeric document retained trailing lines after semantic join")
    return pages


def _metrics(pages: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "line_count": sum(len(page["lines"]) for page in pages),
        "page_count": len(pages),
        "page_count_with_authenticated_dimensions": sum(
            page["page_width"] is not None for page in pages
        ),
    }


def _valid_ref(value: Any) -> bool:
    return (
        type(value) is dict
        and set(value) == _REF_FIELDS
        and type(value["path"]) is str
        and bool(value["path"])
        and type(value["sha256"]) is str
        and _SHA256.fullmatch(value["sha256"]) is not None
        and type(value["size_bytes"]) is int
        and value["size_bytes"] > 0
    )


def _validate_result(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _RESULT_FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or type(value["document_ordinal"]) is not int
        or value["document_ordinal"] <= 0
        or type(value["semantic_document_id"]) is not str
        or not value["semantic_document_id"].startswith("ffsiv1:document:")
        or type(value["source_binding_sha256"]) is not str
        or len(value["source_binding_sha256"]) != 64
        or type(value["pages"]) is not list
        or type(value["metrics"]) is not dict
        or set(value["metrics"]) != _METRIC_FIELDS
        or any(type(item) is not int or item < 0 for item in value["metrics"].values())
    ):
        raise _error("accounting document-axis join result drifted")
    sample_ids: set[str] = set()
    for expected_page, page in enumerate(value["pages"], 1):
        if (
            type(page) is not dict
            or set(page) != _PAGE_FIELDS
            or page["page_sequence"] != expected_page
            or (
                page["page_width"] is not None
                and (type(page["page_width"]) is not int or page["page_width"] <= 0)
            )
            or type(page["lines"]) is not list
        ):
            raise _error("accounting document-axis joined page drifted")
        for expected_line, line in enumerate(page["lines"]):
            recognition = line.get("numeric_recognition") if type(line) is dict else None
            if (
                type(line) is not dict
                or set(line) != _LINE_FIELDS
                or line["line_ordinal"] != expected_line
                or type(line["sample_id"]) is not str
                or not line["sample_id"]
                or line["sample_id"] in sample_ids
                or type(line["vietocr_text"]) is not str
                or type(line["bbox"]) is not list
                or len(line["bbox"]) != 4
                or any(type(item) is not int for item in line["bbox"])
                or line["bbox"][0] < 0
                or line["bbox"][1] < 0
                or line["bbox"][2] <= line["bbox"][0]
                or line["bbox"][3] <= line["bbox"][1]
                or (page["page_width"] is not None and line["bbox"][2] > page["page_width"])
                or not _valid_ref(line["crop_ref"])
                or type(recognition) is not dict
                or set(recognition) != _RECOGNITION_FIELDS
                or type(recognition["raw_prediction"]) is not str
                or type(recognition["reader_score"]) is not float
                or not 0 <= recognition["reader_score"] <= 1
            ):
                raise _error("accounting document-axis joined line drifted")
            sample_ids.add(line["sample_id"])
    if not same_typed_json_v1(value["metrics"], _metrics(value["pages"])):
        raise _error("accounting document-axis join metrics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("document_axis_id")
    if identity != "afdajv1:axis:" + canonical_json_sha256_v1(material):
        raise _error("accounting document-axis join identity drifted")
    return canonical_clone_v1(value)


def build_accounting_family_document_axis_join_v1(
    semantic_document: Any,
    numeric_document: Any,
    *,
    selected_page_render_snapshots: Any,
) -> dict[str, Any]:
    """Join exact complete semantic/numeric axes and selected render dimensions."""

    semantic = _semantic_document(semantic_document)
    numeric = _numeric_document(numeric_document, semantic)
    dimensions = _render_widths(
        selected_page_render_snapshots,
        document_ordinal=semantic["document_ordinal"],
        page_count=semantic["page_count"],
    )
    pages = _join_pages(semantic, numeric, dimensions)
    source_binding = canonical_json_sha256_v1(
        {
            "document_id": semantic["document_id"],
            "private_provenance": semantic["private_provenance"],
            "source_pdf_ref": semantic["source_pdf_ref"],
        }
    )
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "document_ordinal": semantic["document_ordinal"],
        "format_version": FORMAT_VERSION,
        "metrics": _metrics(pages),
        "pages": pages,
        "safety": canonical_clone_v1(_SAFETY),
        "semantic_document_id": semantic["document_id"],
        "source_binding_sha256": source_binding,
    }
    return _validate_result(
        {
            **material,
            "document_axis_id": "afdajv1:axis:" + canonical_json_sha256_v1(material),
        }
    )


def project_accounting_family_document_pages_v1(value: Any) -> list[dict[str, Any]]:
    """Project the bank-blind complete pages for shared topology/row primitives."""

    return _validate_result(value)["pages"]


def validate_accounting_family_document_axis_join_replay_v1(
    value: Any,
    semantic_document: Any,
    numeric_document: Any,
    *,
    selected_page_render_snapshots: Any,
) -> dict[str, Any]:
    """Reject any source/text/number/geometry mutation by exact reconstruction."""

    persisted = _validate_result(value)
    expected = build_accounting_family_document_axis_join_v1(
        semantic_document,
        numeric_document,
        selected_page_render_snapshots=selected_page_render_snapshots,
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("accounting document-axis join does not replay exactly")
    return persisted
