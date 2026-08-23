"""Authenticated printed customer-loan total control from one complete PDF.

The wrapper is deliberately narrower than the loan-type family result.  It
uses the bank-blind loan-type graph to prove one unique owner table, selects
one exact locally printed period lane, and binds that lane's PP-OCRv6 total to
the authenticated document snapshot.  It does not read a prior family result,
route on packet metadata, or derive a total from child rows.

``snapshot`` must be returned by an authenticated document-store accessor and
must cover the complete physical page and line denominator.  Exact replay
rebuilds the upstream graph and numeric evidence from those same bytes.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from bctc_ai.evaluation.accounting_table_axes_v1 import (
    accounting_unit_surface_v1,
    money_integer_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from scripts.experiments import loan_type_numeric_row_reconciliation_v1 as numeric_v1
from scripts.experiments import loan_type_variant_graph_v1 as graph_v1

__all__ = [
    "CLAIM_BOUNDARY",
    "FAMILY_ID",
    "FORMAT_VERSION",
    "CustomerLoanTotalControlV1Error",
    "build_customer_loan_total_control_v1",
    "validate_customer_loan_total_control_v1",
    "validate_customer_loan_total_control_replay_v1",
]


FORMAT_VERSION = "CUSTOMER_LOAN_TOTAL_CONTROL_V1"
FAMILY_ID = "CUSTOMER_LOAN_TOTAL_CONTROL"
CLAIM_BOUNDARY = (
    "AUTHENTICATED_COMPLETE_DOCUMENT_UNIQUE_CUSTOMER_LOAN_OWNER_TABLE_EXACT_LOCAL_"
    "PERIOD_MILLION_VND_UNIT_AND_PRINTED_PPOCRV6_TOTAL_CONTROL_ONLY_NO_CHILD_SUM_"
    "BACKSOLVE_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "accounting_equation_used_as_corroboration_or_veto_only": True,
    "arithmetic_backsolve_used": False,
    "authenticated_store_capability_required_by_caller": True,
    "bank_filename_page_year_or_ordinal_routing_used": False,
    "blank_or_missing_total_imputed_as_zero": False,
    "complete_document_unique_loan_type_graph_required": True,
    "e0164_persisted_result_used_as_authority": False,
    "gemma_used": False,
    "local_exact_period_lane_required": True,
    "local_million_vnd_unit_required": True,
    "ppocrv6_printed_total_authority": True,
    "public_exact_live_replay_required": True,
    "schema_mapping_authority": False,
    "snapshot_self_hash_is_not_source_authentication_authority": True,
    "targeted_pixel_or_numeric_rescue_allowed": False,
}
_RESULT_FIELDS = {
    "authority",
    "claim_boundary",
    "document_binding",
    "family_id",
    "format_version",
    "loan_type_graph_result",
    "loan_type_numeric_result",
    "owner_evidence",
    "period_lane",
    "requested_period_end",
    "result_id",
    "state",
    "total_control",
    "unit_evidence",
}
_PACKET_FIELDS = {
    "assurance",
    "bank_provenance",
    "document_evidence_root_sha256",
    "document_id",
    "document_ordinal",
    "line_count",
    "packet_id",
    "page_count",
    "period",
    "scope",
    "source_pdf_ref",
    "year",
}
_FULL_SNAPSHOT_FIELDS = {
    "document_packet",
    "joined_pages",
    "manifest_id",
    "selected_page_dimensions",
    "snapshot_id",
}
_SELECTED_FULL_SNAPSHOT_FIELDS = {
    *_FULL_SNAPSHOT_FIELDS,
    "query_selection_id",
    "state",
}
_PAGE_FIELDS = {"lines", "page_sequence", "page_width"}
_DIMENSION_FIELDS = {
    "physical_page",
    "pixel_height",
    "pixel_width",
    "render_sha256",
    "render_size_bytes",
}
_LINE_FIELDS = {
    "bbox",
    "crop_ref",
    "line_ordinal",
    "numeric_recognition",
    "sample_id",
    "vietocr_text",
}
_SOURCE_LOCATOR_FIELDS = {
    "bbox",
    "crop_ref",
    "page_render",
    "page_sequence",
    "ppocrv6_reader_score",
    "ppocrv6_surface",
    "sample_id",
    "source_line_index",
    "vietocr_transformer_surface",
}
_DOCUMENT_BINDING_FIELDS = {
    "document_evidence_root_sha256",
    "document_id",
    "document_ordinal",
    "document_packet_id",
    "line_count",
    "manifest_id",
    "page_count",
    "query_selection_id",
    "snapshot_id",
    "source_pdf_ref",
}
_OWNER_EVIDENCE_FIELDS = {"evidence", "match_kind", "surface"}
_PERIOD_LANE_FIELDS = {"evidence", "lane_index", "period_end", "x_center_x2"}
_TOTAL_CONTROL_FIELDS = {
    "accounting_corroboration",
    "lane_index",
    "lane_type",
    "parsed_value",
    "source",
    "status",
}
_TOTAL_CHECK_FIELDS = {
    "lane_index",
    "missing_cell_count",
    "observed_additive_sum",
    "status",
    "target_total",
}
_UNIT_EVIDENCE_FIELDS = {
    "currency",
    "lane_index",
    "magnitude_power10",
    "mode",
    "normalized_surface",
    "source",
    "surface",
}
_REF_FIELDS = {"path", "sha256", "size_bytes"}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PERIOD_END = re.compile(r"^\d{2}/\d{2}/\d{4}$")


class CustomerLoanTotalControlV1Error(ValueError):
    """The authenticated source, total-control topology, or replay drifted."""


def _error(message: str) -> CustomerLoanTotalControlV1Error:
    return CustomerLoanTotalControlV1Error(message)


def _exact_positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be one exact positive integer")
    return value


def _digest(value: Any, label: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise _error(f"{label} SHA-256 drifted")
    return value


def _digest_ref(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _REF_FIELDS:
        raise _error(f"{label} reference shape drifted")
    if type(value["path"]) is not str or not value["path"]:
        raise _error(f"{label} reference path drifted")
    _digest(value["sha256"], label)
    _exact_positive_int(value["size_bytes"], f"{label} size")
    return canonical_clone_v1(value)


def _period_end(value: Any) -> str:
    if type(value) is not str or _PERIOD_END.fullmatch(value) is None:
        raise _error("requested period end must use exact DD/MM/YYYY grammar")
    try:
        observed = datetime.strptime(value, "%d/%m/%Y")
    except ValueError as exc:
        raise _error("requested period end is not one valid calendar date") from exc
    if observed.strftime("%d/%m/%Y") != value:
        raise _error("requested period end canonical form drifted")
    return value


def _packet(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _PACKET_FIELDS:
        raise _error("customer-loan total-control document packet shape drifted")
    material = canonical_clone_v1(value)
    packet_id = material.pop("packet_id")
    if packet_id != "ffdesv1:document:" + canonical_json_sha256_v1(material):
        raise _error("customer-loan total-control document packet identity drifted")
    if (
        type(value["document_id"]) is not str
        or not value["document_id"].startswith("ffsiv1:document:")
        or type(value["document_ordinal"]) is not int
        or value["document_ordinal"] <= 0
        or type(value["line_count"]) is not int
        or value["line_count"] < 0
        or type(value["page_count"]) is not int
        or value["page_count"] <= 0
        or type(value["year"]) is not int
        or value["year"] <= 0
        or any(
            type(value[field]) is not str or not value[field]
            for field in ("assurance", "bank_provenance", "period", "scope")
        )
    ):
        raise _error("customer-loan total-control document packet fields drifted")
    _digest(value["document_evidence_root_sha256"], "document evidence root")
    _digest_ref(value["source_pdf_ref"], "source PDF")
    return canonical_clone_v1(value)


def _bbox(value: Any, *, width: int, height: int, label: str) -> list[int]:
    if (
        type(value) is not list
        or len(value) != 4
        or any(type(item) is not int for item in value)
        or value[0] < 0
        or value[1] < 0
        or value[0] >= value[2]
        or value[1] >= value[3]
        or value[2] > width
        or value[3] > height
    ):
        raise _error(f"{label} bbox drifted")
    return list(value)


def _snapshot(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise _error("customer-loan total-control full snapshot shape drifted")
    fields = set(value)
    if fields not in (_FULL_SNAPSHOT_FIELDS, _SELECTED_FULL_SNAPSHOT_FIELDS):
        raise _error("customer-loan total-control full snapshot shape drifted")
    material = canonical_clone_v1(value)
    snapshot_id = material.pop("snapshot_id")
    prefix = (
        "ffdesv1:selected:" if fields == _SELECTED_FULL_SNAPSHOT_FIELDS else "ffdesv1:snapshot:"
    )
    if snapshot_id != prefix + canonical_json_sha256_v1(material):
        raise _error("customer-loan total-control snapshot identity drifted")
    if fields == _SELECTED_FULL_SNAPSHOT_FIELDS and (
        value["state"] != "AUTHENTICATED_IMMUTABLE_SQLITE_SELECTED_PAGE_EVIDENCE"
        or type(value["query_selection_id"]) is not str
        or not value["query_selection_id"].startswith("ffoqcv1:selection:")
    ):
        raise _error("customer-loan total-control selected snapshot authority drifted")
    if type(value["manifest_id"]) is not str or not value["manifest_id"].startswith(
        "ffdesv1:manifest:"
    ):
        raise _error("customer-loan total-control manifest binding drifted")
    packet = _packet(value["document_packet"])
    pages = value["joined_pages"]
    dimensions = value["selected_page_dimensions"]
    if type(pages) is not list or type(dimensions) is not list:
        raise _error("customer-loan total-control page axis shape drifted")
    expected_pages = list(range(1, packet["page_count"] + 1))
    if any(type(item) is not dict or set(item) != _DIMENSION_FIELDS for item in dimensions):
        raise _error("customer-loan total-control page dimension shape drifted")
    if any(type(page) is not dict or set(page) != _PAGE_FIELDS for page in pages):
        raise _error("customer-loan total-control joined page shape drifted")
    page_ids = [page.get("page_sequence") for page in pages]
    if (
        len(dimensions) != packet["page_count"]
        or page_ids != sorted(set(page_ids))
        or any(type(page_id) is not int or page_id not in expected_pages for page_id in page_ids)
        or any(type(item["physical_page"]) is not int for item in dimensions)
        or [item.get("physical_page") for item in dimensions] != expected_pages
    ):
        raise _error("customer-loan total-control snapshot is not the complete page denominator")

    dimensions_by_page: dict[int, dict[str, Any]] = {}
    for dimension in dimensions:
        physical_page = dimension["physical_page"]
        width = _exact_positive_int(dimension["pixel_width"], "render width")
        height = _exact_positive_int(dimension["pixel_height"], "render height")
        _digest(dimension["render_sha256"], "page render")
        _exact_positive_int(dimension["render_size_bytes"], "page render size")
        dimensions_by_page[physical_page] = {
            **dimension,
            "pixel_height": height,
            "pixel_width": width,
        }

    line_count = 0
    sample_ids: set[str] = set()
    for page in pages:
        dimension = dimensions_by_page[page["page_sequence"]]
        width = dimension["pixel_width"]
        height = dimension["pixel_height"]
        if page["page_width"] != width or type(page["lines"]) is not list:
            raise _error("customer-loan total-control OCR/render page binding drifted")
        for offset, line in enumerate(page["lines"]):
            if type(line) is not dict or set(line) != _LINE_FIELDS:
                raise _error("customer-loan total-control source line shape drifted")
            numeric = line["numeric_recognition"]
            score = numeric.get("reader_score") if type(numeric) is dict else None
            if (
                type(line["line_ordinal"]) is not int
                or line["line_ordinal"] != offset
                or type(line["sample_id"]) is not str
                or not line["sample_id"]
                or line["sample_id"] in sample_ids
                or type(line["vietocr_text"]) is not str
                or line["vietocr_text"] != unicodedata.normalize("NFC", line["vietocr_text"])
                or type(numeric) is not dict
                or set(numeric) != {"raw_prediction", "reader_score"}
                or type(numeric["raw_prediction"]) is not str
                or type(score) not in {int, float}
                or not math.isfinite(score)
                or not 0 <= score <= 1
            ):
                raise _error("customer-loan total-control source line identity drifted")
            _bbox(line["bbox"], width=width, height=height, label="source line")
            _digest_ref(line["crop_ref"], "source crop")
            sample_ids.add(line["sample_id"])
            line_count += 1
    if line_count != packet["line_count"]:
        raise _error("customer-loan total-control snapshot line denominator drifted")
    return canonical_clone_v1(value)


def _matcher_pages(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "lines": [
                {
                    "bbox": canonical_clone_v1(line["bbox"]),
                    "source_line_index": line["line_ordinal"],
                    "source_text": line["numeric_recognition"]["raw_prediction"],
                    "vietocr_text": line["vietocr_text"],
                }
                for line in page["lines"]
            ],
            "page_sequence": page["page_sequence"],
            "primary_numeric_authority": True,
        }
        for page in snapshot["joined_pages"]
    ]


def _source_locator(
    snapshot: Mapping[str, Any], *, page_sequence: int, source_line_index: int
) -> dict[str, Any]:
    if (
        type(page_sequence) is not int
        or page_sequence <= 0
        or type(source_line_index) is not int
        or source_line_index < 0
    ):
        raise _error("customer-loan total-control source locator drifted")
    try:
        page = next(
            page for page in snapshot["joined_pages"] if page.get("page_sequence") == page_sequence
        )
        dimension = next(
            item
            for item in snapshot["selected_page_dimensions"]
            if item.get("physical_page") == page_sequence
        )
        line = page["lines"][source_line_index]
    except (IndexError, KeyError, StopIteration, TypeError) as exc:
        raise _error("customer-loan total-control source locator is absent") from exc
    if page.get("page_sequence") != page_sequence or line.get("line_ordinal") != source_line_index:
        raise _error("customer-loan total-control source locator identity drifted")
    numeric = line["numeric_recognition"]
    return {
        "bbox": canonical_clone_v1(line["bbox"]),
        "crop_ref": canonical_clone_v1(line["crop_ref"]),
        "page_render": canonical_clone_v1(dimension),
        "page_sequence": page_sequence,
        "ppocrv6_reader_score": numeric["reader_score"],
        "ppocrv6_surface": numeric["raw_prediction"],
        "sample_id": line["sample_id"],
        "source_line_index": source_line_index,
        "vietocr_transformer_surface": line["vietocr_text"],
    }


def _validate_source_locator(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _SOURCE_LOCATOR_FIELDS:
        raise _error(f"customer-loan total-control {label} locator shape drifted")
    render = value["page_render"]
    if type(render) is not dict or set(render) != _DIMENSION_FIELDS:
        raise _error(f"customer-loan total-control {label} render binding shape drifted")
    width = _exact_positive_int(render["pixel_width"], f"{label} render width")
    height = _exact_positive_int(render["pixel_height"], f"{label} render height")
    if (
        type(value["page_sequence"]) is not int
        or value["page_sequence"] <= 0
        or type(render["physical_page"]) is not int
        or render["physical_page"] != value["page_sequence"]
        or type(value["source_line_index"]) is not int
        or value["source_line_index"] < 0
        or type(value["sample_id"]) is not str
        or not value["sample_id"]
        or type(value["ppocrv6_surface"]) is not str
        or type(value["vietocr_transformer_surface"]) is not str
        or type(value["ppocrv6_reader_score"]) not in {int, float}
        or not math.isfinite(value["ppocrv6_reader_score"])
        or not 0 <= value["ppocrv6_reader_score"] <= 1
    ):
        raise _error(f"customer-loan total-control {label} locator identity drifted")
    _digest(render["render_sha256"], f"{label} page render")
    _exact_positive_int(render["render_size_bytes"], f"{label} page render size")
    _bbox(value["bbox"], width=width, height=height, label=f"{label} locator")
    _digest_ref(value["crop_ref"], f"{label} crop")
    return canonical_clone_v1(value)


def _content_addressed_result(value: Any, *, prefix: str, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise _error(f"customer-loan total-control {label} result shape drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id", None)
    if identity != prefix + canonical_json_sha256_v1(material):
        raise _error(f"customer-loan total-control {label} result identity drifted")
    return canonical_clone_v1(value)


def _typed_document_binding(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _DOCUMENT_BINDING_FIELDS:
        raise _error("customer-loan total-control document binding shape drifted")
    if (
        type(value["document_id"]) is not str
        or not value["document_id"].startswith("ffsiv1:document:")
        or type(value["document_ordinal"]) is not int
        or value["document_ordinal"] <= 0
        or type(value["document_packet_id"]) is not str
        or not value["document_packet_id"].startswith("ffdesv1:document:")
        or type(value["line_count"]) is not int
        or value["line_count"] < 0
        or type(value["page_count"]) is not int
        or value["page_count"] <= 0
        or type(value["manifest_id"]) is not str
        or not value["manifest_id"].startswith("ffdesv1:manifest:")
        or type(value["snapshot_id"]) is not str
        or not value["snapshot_id"].startswith(("ffdesv1:selected:", "ffdesv1:snapshot:"))
        or (
            value["query_selection_id"] is not None
            and (
                type(value["query_selection_id"]) is not str
                or not value["query_selection_id"].startswith("ffoqcv1:selection:")
            )
        )
    ):
        raise _error("customer-loan total-control document binding identity drifted")
    _digest(value["document_evidence_root_sha256"], "document binding root")
    _digest_ref(value["source_pdf_ref"], "document binding source PDF")
    return canonical_clone_v1(value)


def _typed_locator_axis(value: Any, *, label: str) -> list[dict[str, Any]]:
    if type(value) is not list or not value:
        raise _error(f"customer-loan total-control {label} evidence axis drifted")
    return [_validate_source_locator(item, label) for item in value]


def _evidence_lines(
    snapshot: Mapping[str, Any], *, page_sequence: int, source_line_indices: Any, label: str
) -> list[dict[str, Any]]:
    if (
        type(source_line_indices) is not list
        or not source_line_indices
        or any(type(index) is not int or index < 0 for index in source_line_indices)
        or source_line_indices != sorted(set(source_line_indices))
    ):
        raise _error(f"customer-loan total-control {label} line axis drifted")
    return [
        _source_locator(
            snapshot,
            page_sequence=page_sequence,
            source_line_index=source_line_index,
        )
        for source_line_index in source_line_indices
    ]


def _selected_lane(
    graph: Mapping[str, Any], requested_period_end: str
) -> tuple[int, dict[str, Any]]:
    if graph.get("period_mode") != "LOCAL_EXACT_DATES":
        raise _error("customer-loan total-control period axis is not local exact dates")
    periods = graph.get("period_axis")
    lane_types = graph.get("lane_types")
    lane_centers = graph.get("lane_centers_x2")
    if (
        type(periods) is not list
        or type(lane_types) is not list
        or type(lane_centers) is not list
        or len(lane_types) != len(lane_centers)
    ):
        raise _error("customer-loan total-control typed lane axis drifted")
    matching = [item for item in periods if item.get("period") == requested_period_end]
    if len(matching) != 1:
        raise _error("customer-loan total-control requested period is missing or multiple")
    money_lanes = sorted(
        (index for index, lane_type in enumerate(lane_types) if lane_type == "MONEY"),
        key=lambda index: lane_centers[index],
    )
    ordered_periods = sorted(periods, key=lambda item: item.get("x_center_x2", -1))
    if (
        len(money_lanes) != len(ordered_periods)
        or any(type(item.get("x_center_x2")) is not int for item in ordered_periods)
        or len({item["x_center_x2"] for item in ordered_periods}) != len(ordered_periods)
    ):
        raise _error("customer-loan total-control period/money lane cardinality drifted")
    position = next(
        index
        for index, period in enumerate(ordered_periods)
        if period["period"] == requested_period_end
    )
    return money_lanes[position], canonical_clone_v1(matching[0])


def _project(
    snapshot: Mapping[str, Any],
    requested_period_end: str,
    graph_result: Mapping[str, Any],
    numeric_result: Mapping[str, Any],
) -> dict[str, Any]:
    packet = snapshot["document_packet"]
    if (
        graph_result.get("status") != "ACCEPTED_UNIQUE_VARIANT_GRAPH"
        or graph_result.get("uniqueness") != {"full_match_count": 1, "status": "UNIQUE_FULL_MATCH"}
        or type(graph_result.get("graphs")) is not list
        or len(graph_result["graphs"]) != 1
    ):
        raise _error("customer-loan total-control requires one unique complete owner table")
    graph = graph_result["graphs"][0]
    owner = graph.get("owner")
    page_sequence = graph.get("page_sequence")
    if (
        graph.get("context_complete") is not True
        or graph.get("status") != "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"
        or graph.get("unresolved_reasons") != []
        or type(owner) is not dict
        or owner.get("match_kind") != "EXACT_ACCENTLESS_ALIAS"
        or type(owner.get("surface")) is not str
        or type(page_sequence) is not int
        or page_sequence <= 0
    ):
        raise _error("customer-loan total-control exact owner/table binding drifted")
    if (
        numeric_result.get("graph_result_id") != graph_result.get("result_id")
        or numeric_result.get("page_sequence") != page_sequence
        or numeric_result.get("status") != "PP_NUMERIC_EXACT"
    ):
        raise _error("customer-loan total-control requires exact base PP numeric evidence")

    lane_index, period = _selected_lane(graph, requested_period_end)
    period_evidence = _evidence_lines(
        snapshot,
        page_sequence=page_sequence,
        source_line_indices=period.get("evidence_source_line_indices"),
        label="period",
    )

    unit_scope = graph.get("unit_scope")
    if (
        type(unit_scope) is not dict
        or unit_scope.get("mode") != "LOCAL_PER_LANE"
        or type(unit_scope.get("source_line_indices")) is not list
        or type(unit_scope.get("surfaces")) is not list
        or len(unit_scope["source_line_indices"]) != len(graph["lane_types"])
        or len(unit_scope["surfaces"]) != len(graph["lane_types"])
    ):
        raise _error("customer-loan total-control requires one local unit per typed lane")
    unit_surface = unit_scope["surfaces"][lane_index]
    try:
        parsed_unit = accounting_unit_surface_v1(unit_surface)
    except ValueError as exc:
        raise _error("customer-loan total-control local unit cannot be parsed") from exc
    if parsed_unit is None or parsed_unit != {
        "currency": "VND",
        "magnitude_power10": 6,
        "normalized_surface": parsed_unit.get("normalized_surface") if parsed_unit else None,
        "unit_kind": "MONEY",
    }:
        raise _error("customer-loan total-control local unit is not exact million VND")
    unit_index = unit_scope["source_line_indices"][lane_index]
    unit_locator = _source_locator(
        snapshot,
        page_sequence=page_sequence,
        source_line_index=unit_index,
    )
    if unit_locator["vietocr_transformer_surface"] != unit_surface:
        raise _error("customer-loan total-control unit source surface drifted")

    graph_totals = graph.get("total")
    numeric_totals = numeric_result.get("total")
    if type(graph_totals) is not list or type(numeric_totals) is not list:
        raise _error("customer-loan total-control printed total axis drifted")
    graph_cells = [item for item in graph_totals if item.get("lane_index") == lane_index]
    numeric_cells = [item for item in numeric_totals if item.get("lane_index") == lane_index]
    if len(graph_cells) != 1 or len(numeric_cells) != 1:
        raise _error("customer-loan total-control requested total lane is missing or multiple")
    graph_cell = graph_cells[0]
    numeric_cell = numeric_cells[0]
    source_line_index = numeric_cell.get("source_line_index")
    if (
        numeric_cell.get("lane_type") != "MONEY"
        or numeric_cell.get("status") != "PP_OCRV6_NUMERIC_PROPOSAL"
        or type(numeric_cell.get("parsed_value")) is not int
        or type(source_line_index) is not int
        or source_line_index < 0
        or graph_cell.get("source_line_index") != source_line_index
        or graph_cell.get("semantic_surface") != numeric_cell.get("semantic_surface")
    ):
        raise _error("customer-loan total-control exact printed PP total drifted")
    total_locator = _source_locator(
        snapshot,
        page_sequence=page_sequence,
        source_line_index=source_line_index,
    )
    if total_locator["ppocrv6_surface"] != numeric_cell.get("ppocrv6_surface") or total_locator[
        "vietocr_transformer_surface"
    ] != numeric_cell.get("semantic_surface"):
        raise _error("customer-loan total-control total crop/text binding drifted")
    checks = [
        item
        for item in numeric_result.get("accounting_checks", [])
        if item.get("lane_index") == lane_index
    ]
    if len(checks) != 1 or checks[0].get("status") != "EXACT_PP_NUMERIC_EQUATION":
        raise _error("customer-loan total-control PP equation veto did not pass exactly")

    owner_evidence = _evidence_lines(
        snapshot,
        page_sequence=page_sequence,
        source_line_indices=owner.get("source_line_indices"),
        label="owner",
    )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "document_binding": {
            "document_evidence_root_sha256": packet["document_evidence_root_sha256"],
            "document_id": packet["document_id"],
            "document_ordinal": packet["document_ordinal"],
            "document_packet_id": packet["packet_id"],
            "line_count": packet["line_count"],
            "manifest_id": snapshot["manifest_id"],
            "page_count": packet["page_count"],
            "query_selection_id": snapshot.get("query_selection_id"),
            "snapshot_id": snapshot["snapshot_id"],
            "source_pdf_ref": canonical_clone_v1(packet["source_pdf_ref"]),
        },
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "loan_type_graph_result": canonical_clone_v1(graph_result),
        "loan_type_numeric_result": canonical_clone_v1(numeric_result),
        "owner_evidence": {
            "evidence": owner_evidence,
            "match_kind": owner["match_kind"],
            "surface": owner["surface"],
        },
        "period_lane": {
            "evidence": period_evidence,
            "lane_index": lane_index,
            "period_end": requested_period_end,
            "x_center_x2": period["x_center_x2"],
        },
        "requested_period_end": requested_period_end,
        "state": "EXACT_AUTHENTICATED_PRINTED_CUSTOMER_LOAN_TOTAL_CONTROL",
        "total_control": {
            "accounting_corroboration": canonical_clone_v1(checks[0]),
            "lane_index": lane_index,
            "lane_type": "MONEY",
            "parsed_value": numeric_cell["parsed_value"],
            "source": total_locator,
            "status": "EXACT_PRINTED_PPOCRV6_TOTAL_CONTROL",
        },
        "unit_evidence": {
            "currency": "VND",
            "lane_index": lane_index,
            "magnitude_power10": 6,
            "mode": "LOCAL_PER_LANE",
            "normalized_surface": parsed_unit["normalized_surface"],
            "source": unit_locator,
            "surface": unit_surface,
        },
    }
    return _validate_result(
        {
            **material,
            "result_id": "cltcv1:result:" + canonical_json_sha256_v1(material),
        }
    )


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("customer-loan total-control result shape drifted")
    material = canonical_clone_v1(value)
    result_id = material.pop("result_id")
    if result_id != "cltcv1:result:" + canonical_json_sha256_v1(material):
        raise _error("customer-loan total-control result identity drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or value["state"] != "EXACT_AUTHENTICATED_PRINTED_CUSTOMER_LOAN_TOTAL_CONTROL"
        or type(value["document_binding"]) is not dict
        or type(value["loan_type_graph_result"]) is not dict
        or type(value["loan_type_numeric_result"]) is not dict
        or type(value["owner_evidence"]) is not dict
        or type(value["period_lane"]) is not dict
        or type(value["total_control"]) is not dict
        or type(value["unit_evidence"]) is not dict
    ):
        raise _error("customer-loan total-control result contract drifted")
    requested = _period_end(value["requested_period_end"])
    document = _typed_document_binding(value["document_binding"])
    graph_result = _content_addressed_result(
        value["loan_type_graph_result"],
        prefix="ltvgv1:result:",
        label="loan-type graph",
    )
    numeric_result = _content_addressed_result(
        value["loan_type_numeric_result"],
        prefix="ltnrrv1:result:",
        label="loan-type numeric",
    )
    if (
        graph_result.get("status") != "ACCEPTED_UNIQUE_VARIANT_GRAPH"
        or graph_result.get("uniqueness") != {"full_match_count": 1, "status": "UNIQUE_FULL_MATCH"}
        or type(graph_result.get("graphs")) is not list
        or len(graph_result["graphs"]) != 1
        or numeric_result.get("graph_result_id") != graph_result.get("result_id")
        or numeric_result.get("status") != "PP_NUMERIC_EXACT"
    ):
        raise _error("customer-loan total-control nested graph/numeric binding drifted")
    graph = graph_result["graphs"][0]
    graph_page = graph.get("page_sequence")
    if (
        type(graph_page) is not int
        or graph_page <= 0
        or numeric_result.get("page_sequence") != graph_page
    ):
        raise _error("customer-loan total-control nested page binding drifted")

    owner = value["owner_evidence"]
    graph_owner = graph.get("owner")
    if (
        set(owner) != _OWNER_EVIDENCE_FIELDS
        or owner["match_kind"] != "EXACT_ACCENTLESS_ALIAS"
        or type(owner["surface"]) is not str
        or not owner["surface"]
        or type(graph_owner) is not dict
        or graph_owner.get("match_kind") != owner["match_kind"]
        or graph_owner.get("surface") != owner["surface"]
    ):
        raise _error("customer-loan total-control owner evidence drifted")
    owner_evidence = _typed_locator_axis(owner["evidence"], label="owner")
    if graph_owner.get("source_line_indices") != [
        item["source_line_index"] for item in owner_evidence
    ] or any(
        item["page_sequence"] != graph_page
        or item["vietocr_transformer_surface"] != owner["surface"]
        for item in owner_evidence
    ):
        raise _error("customer-loan total-control owner source binding drifted")

    period = value["period_lane"]
    selected_lane_index, selected_period = _selected_lane(graph, requested)
    if (
        set(period) != _PERIOD_LANE_FIELDS
        or type(period["lane_index"]) is not int
        or period["lane_index"] < 0
        or period["lane_index"] != selected_lane_index
        or type(period["x_center_x2"]) is not int
        or period["x_center_x2"] < 0
        or _period_end(period["period_end"]) != requested
        or selected_period.get("period") != period["period_end"]
        or selected_period.get("x_center_x2") != period["x_center_x2"]
    ):
        raise _error("customer-loan total-control period lane drifted")
    period_evidence = _typed_locator_axis(period["evidence"], label="period")
    graph_periods = graph.get("period_axis")
    matching_periods = (
        [item for item in graph_periods if item.get("period") == requested]
        if type(graph_periods) is list
        else []
    )
    if (
        len(matching_periods) != 1
        or not same_typed_json_v1(matching_periods[0], selected_period)
        or matching_periods[0].get("x_center_x2") != period["x_center_x2"]
        or matching_periods[0].get("evidence_source_line_indices")
        != [item["source_line_index"] for item in period_evidence]
        or any(item["page_sequence"] != graph_page for item in period_evidence)
    ):
        raise _error("customer-loan total-control period source binding drifted")

    unit = value["unit_evidence"]
    if (
        set(unit) != _UNIT_EVIDENCE_FIELDS
        or unit["currency"] != "VND"
        or type(unit["lane_index"]) is not int
        or unit["lane_index"] != period["lane_index"]
        or type(unit["magnitude_power10"]) is not int
        or unit["magnitude_power10"] != 6
        or unit["mode"] != "LOCAL_PER_LANE"
        or type(unit["normalized_surface"]) is not str
        or not unit["normalized_surface"]
        or type(unit["surface"]) is not str
        or not unit["surface"]
    ):
        raise _error("customer-loan total-control unit evidence drifted")
    try:
        parsed_unit = accounting_unit_surface_v1(unit["surface"])
    except ValueError as exc:
        raise _error("customer-loan total-control unit surface cannot be parsed") from exc
    if parsed_unit != {
        "currency": unit["currency"],
        "magnitude_power10": unit["magnitude_power10"],
        "normalized_surface": unit["normalized_surface"],
        "unit_kind": "MONEY",
    }:
        raise _error("customer-loan total-control normalized unit binding drifted")
    unit_source = _validate_source_locator(unit["source"], "unit")
    graph_unit = graph.get("unit_scope")
    if (
        unit_source["vietocr_transformer_surface"] != unit["surface"]
        or unit_source["page_sequence"] != graph_page
        or type(graph_unit) is not dict
        or graph_unit.get("mode") != unit["mode"]
        or type(graph_unit.get("source_line_indices")) is not list
        or type(graph_unit.get("surfaces")) is not list
        or len(graph_unit["source_line_indices"]) <= period["lane_index"]
        or len(graph_unit["surfaces"]) <= period["lane_index"]
        or graph_unit["source_line_indices"][period["lane_index"]]
        != unit_source["source_line_index"]
        or graph_unit["surfaces"][period["lane_index"]] != unit["surface"]
    ):
        raise _error("customer-loan total-control unit surface binding drifted")

    total = value["total_control"]
    if (
        set(total) != _TOTAL_CONTROL_FIELDS
        or type(total["lane_index"]) is not int
        or total["lane_index"] != period["lane_index"]
        or total["lane_type"] != "MONEY"
        or type(total["parsed_value"]) is not int
        or total["status"] != "EXACT_PRINTED_PPOCRV6_TOTAL_CONTROL"
        or type(total["accounting_corroboration"]) is not dict
        or set(total["accounting_corroboration"]) != _TOTAL_CHECK_FIELDS
    ):
        raise _error("customer-loan total-control printed total drifted")
    total_source = _validate_source_locator(total["source"], "total")
    check = total["accounting_corroboration"]
    if (
        type(check["lane_index"]) is not int
        or check["lane_index"] != period["lane_index"]
        or type(check["missing_cell_count"]) is not int
        or check["missing_cell_count"] != 0
        or type(check["observed_additive_sum"]) is not int
        or check["observed_additive_sum"] != total["parsed_value"]
        or check["status"] != "EXACT_PP_NUMERIC_EQUATION"
        or type(check["target_total"]) is not int
        or check["target_total"] != total["parsed_value"]
    ):
        raise _error("customer-loan total-control accounting corroboration drifted")
    graph_totals = graph.get("total")
    numeric_totals = numeric_result.get("total")
    graph_cells = (
        [item for item in graph_totals if item.get("lane_index") == period["lane_index"]]
        if type(graph_totals) is list
        else []
    )
    numeric_cells = (
        [item for item in numeric_totals if item.get("lane_index") == period["lane_index"]]
        if type(numeric_totals) is list
        else []
    )
    numeric_checks = numeric_result.get("accounting_checks")
    matching_checks = (
        [item for item in numeric_checks if item.get("lane_index") == period["lane_index"]]
        if type(numeric_checks) is list
        else []
    )
    if len(graph_cells) != 1 or len(numeric_cells) != 1 or len(matching_checks) != 1:
        raise _error("customer-loan total-control selected nested lane drifted")
    graph_cell = graph_cells[0]
    numeric_cell = numeric_cells[0]
    try:
        parsed_source = money_integer_v1(total_source["ppocrv6_surface"])
    except ValueError as exc:
        raise _error("customer-loan total-control printed PP source cannot be parsed") from exc
    if (
        graph_cell.get("lane_type") != "MONEY"
        or numeric_cell.get("lane_type") != "MONEY"
        or numeric_cell.get("status") != "PP_OCRV6_NUMERIC_PROPOSAL"
        or graph_cell.get("source_line_index") != total_source["source_line_index"]
        or numeric_cell.get("source_line_index") != total_source["source_line_index"]
        or graph_cell.get("semantic_surface") != total_source["vietocr_transformer_surface"]
        or numeric_cell.get("semantic_surface") != total_source["vietocr_transformer_surface"]
        or numeric_cell.get("ppocrv6_surface") != total_source["ppocrv6_surface"]
        or numeric_cell.get("parsed_value") != total["parsed_value"]
        or parsed_source != total["parsed_value"]
        or total_source["page_sequence"] != graph_page
        or not same_typed_json_v1(matching_checks[0], check)
    ):
        raise _error("customer-loan total-control selected nested total binding drifted")
    all_locators = [*owner_evidence, *period_evidence, unit_source, total_source]
    if any(item["page_sequence"] > document["page_count"] for item in all_locators):
        raise _error("customer-loan total-control locator exceeds document denominator")
    return canonical_clone_v1(value)


def build_customer_loan_total_control_v1(
    snapshot: Mapping[str, Any], requested_period_end: str
) -> dict[str, Any]:
    """Build one exact printed total control from a complete authenticated snapshot."""

    typed_snapshot = _snapshot(snapshot)
    requested = _period_end(requested_period_end)
    pages = _matcher_pages(typed_snapshot)
    try:
        graph_result = graph_v1.build_loan_type_variant_graph_document_v1(
            pages,
            enable_extended_owner_table_variants=True,
        )
        numeric_result = numeric_v1.build_loan_type_numeric_row_reconciliation_v1(pages)
    except (RuntimeError, ValueError) as exc:
        raise _error("customer-loan total-control upstream build failed") from exc
    return _project(typed_snapshot, requested, graph_result, numeric_result)


def validate_customer_loan_total_control_v1(value: Any) -> dict[str, Any]:
    """Validate the typed envelope without claiming source authentication.

    This is the cheap parent-process handoff gate for a result whose public
    exact replay already ran against a capability-minted full snapshot in a
    worker.  Content addressing and source-locator shape are checked here;
    only :func:`validate_customer_loan_total_control_replay_v1` establishes
    equality with authenticated source bytes.
    """

    return _validate_result(value)


def validate_customer_loan_total_control_replay_v1(
    value: Any,
    snapshot: Mapping[str, Any],
    requested_period_end: str,
) -> dict[str, Any]:
    """Publicly replay the upstream graph/numeric evidence and exact projection."""

    persisted = _validate_result(value)
    typed_snapshot = _snapshot(snapshot)
    requested = _period_end(requested_period_end)
    if persisted["requested_period_end"] != requested:
        raise _error("customer-loan total-control requested period replay drifted")
    pages = _matcher_pages(typed_snapshot)
    try:
        graph_result = graph_v1.validate_loan_type_variant_graph_replay_v1(
            persisted["loan_type_graph_result"],
            pages,
            enable_extended_owner_table_variants=True,
        )
        numeric_result = numeric_v1.validate_loan_type_numeric_row_reconciliation_replay_v1(
            persisted["loan_type_numeric_result"],
            pages,
        )
    except (RuntimeError, ValueError) as exc:
        raise _error("customer-loan total-control upstream public replay failed") from exc
    rebuilt = _project(typed_snapshot, requested, graph_result, numeric_result)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("customer-loan total-control does not replay exactly")
    return rebuilt
