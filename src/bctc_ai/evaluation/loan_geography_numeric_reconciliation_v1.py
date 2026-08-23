"""Graph-neutral numeric reconciliation for customer-loan geography totals.

The caller supplies a normalized ``role x period`` matrix after table
discovery.  This module neither discovers a table nor resolves schema IDs.  It
preserves PP-OCRv6 and VietOCR observations as candidates, admits zero only
from replayable visible-dash pixels, and lets an exact printed customer-loan
total select a value only when exactly one combination of already observed
candidates closes.  Accounting can therefore corroborate or veto evidence,
but cannot invent or back-solve a missing number.

Single-page row/column layouts and repeated full segments on adjacent pages
share the same input matrix.  Optional Gemma references are structure-only
provenance; they contain no numeric surface and never enter reconciliation.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from bctc_ai.evaluation.accounting_table_axes_v1 import money_integer_v1
from bctc_ai.evaluation.family_first_visible_dash_glyph_evidence_v1 import (
    FamilyFirstVisibleDashGlyphEvidenceV1Error,
    validate_family_first_visible_dash_glyph_evidence_replay_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "INPUT_FORMAT_VERSION",
    "LoanGeographyNumericReconciliationV1Error",
    "build_loan_geography_numeric_reconciliation_v1",
    "validate_loan_geography_numeric_reconciliation_replay_v1",
    "validate_loan_geography_numeric_reconciliation_v1",
]


FORMAT_VERSION = "LOAN_GEOGRAPHY_NUMERIC_RECONCILIATION_V1"
INPUT_FORMAT_VERSION = "LOAN_GEOGRAPHY_NUMERIC_RECONCILIATION_INPUT_V1"
FAMILY_ID = "LOAN_GEOGRAPHIC_CLASSIFICATION"
CLAIM_BOUNDARY = (
    "GRAPH_BOUND_NORMALIZED_DOMESTIC_FOREIGN_BY_ONE_OR_MORE_MONEY_PERIOD_LANES_RAW_"
    "PPOCRV6_VIETOCR_CANDIDATES_TYPED_VISIBLE_DASH_PIXEL_REPLAY_AND_EXACT_"
    "PRINTED_CUSTOMER_LOAN_TOTAL_EXACT_MILLION_VND_UNIQUE_OBSERVED_CANDIDATE_"
    "SELECTION_OR_VETO_"
    "ONLY_NO_BLANK_ZERO_BACKSOLVE_GEMMA_NUMERIC_SCHEMA_TABLE_DISCOVERY_"
    "CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "accounting_can_infer_or_backsolve_value": False,
    "accounting_can_select_only_one_unique_observed_candidate_assignment": True,
    "accounting_is_corroboration_or_veto_only": True,
    "blank_or_missing_cell_is_zero": False,
    "gemma_structure_challenger_has_numeric_authority": False,
    "mapping_authority": False,
    "parent_716_or_759_emitted_as_mapping": False,
    "persisted_result_self_authenticating": False,
    "ppocrv6_and_vietocr_raw_surfaces_retained": True,
    "schema_authority": False,
    "table_discovery_authority": False,
    "unit_contract_is_exact_million_vnd": True,
    "unit_conversion_performed": False,
    "visible_dash_requires_exact_pixel_replay": True,
}
_ROLES = ("DOMESTIC_TOTAL", "FOREIGN_TOTAL")
_TOTAL_ROLE = "PRINTED_CUSTOMER_LOAN_TOTAL"
_PRESENTATION_MODES = {
    "REPEATED_FULL_SEGMENT_ONE_PERIOD_PER_PAGE",
    "SINGLE_PAGE_GEOGRAPHY_COLUMNS_ACCOUNTING_ROWS",
    "SINGLE_PAGE_GEOGRAPHY_ROWS_ACCOUNTING_COLUMNS",
}
_PERIOD_ROLES = {"CURRENT", "COMPARATIVE"}
_PERIOD_RESOLUTION_MODES = {"LOCAL_EXACT_DATE", "DOCUMENT_INHERITED_EXACT_DATE"}
_UNIT_RESOLUTION_MODES = {"LOCAL_EXACT_UNIT", "DOCUMENT_INHERITED_EXACT_UNIT"}
_TOTAL_CONTROL_RESOLUTION_MODES = {
    "LOCAL_LABELED_TOTAL",
    "LOCAL_UNLABELED_TOTAL_ROW",
}
_KNOWN_NESTED_ROLES = (
    "HO_CHI_MINH_CITY",
    "MEKONG_DELTA",
    "CENTRAL_AND_CENTRAL_HIGHLANDS",
    "NORTH",
    "SOUTHEAST",
)
_DATE = re.compile(r"^20\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$")
_SHA = re.compile(r"^[0-9a-f]{64}$")
_DASH_ID = re.compile(r"^ffvdgev1:evidence:[0-9a-f]{64}$")
_DASH_FORMAT = "FAMILY_FIRST_VISIBLE_DASH_GLYPH_EVIDENCE_V1"
_INPUT_CELL_FIELDS = {
    "bbox",
    "cell_id",
    "crop_sha256",
    "lane_index",
    "lane_type",
    "page_sequence",
    "ppocrv6_score",
    "ppocrv6_surface",
    "sample_id",
    "source_line_index",
    "vietocr_surface",
}
_RESOLUTION_FIELDS = {
    "candidate_values",
    "dash_evidence_ref",
    "ppocrv6_parsed_value",
    "selected_readers",
    "selected_value",
    "selection_mode",
    "status",
    "vietocr_parsed_value",
}
_DASH_BINDING_FIELDS = {
    "cell_id",
    "crop_png_bytes",
    "evidence",
    "lane_index",
    "lane_type",
    "page_sequence",
    "region_id",
    "role",
}
_DASH_REF_FIELDS = {
    "classification",
    "crop_sha256",
    "evidence_id",
    "kind",
    "region_id",
}
_ACCEPTED_CHECK_STATUSES = {
    "EXACT_OBSERVED_EQUATION",
    "EXACT_EQUATION_UNIQUELY_SELECTED_OBSERVED_CANDIDATES",
}


class LoanGeographyNumericReconciliationV1Error(ValueError):
    """The geography source, dash replay, candidates, or equation drifted."""


def _error(message: str) -> LoanGeographyNumericReconciliationV1Error:
    return LoanGeographyNumericReconciliationV1Error(message)


def _string(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        raise _error(f"{label} string drifted")
    return value


def _surface(value: Any, label: str) -> str | None:
    if value is not None and type(value) is not str:
        raise _error(f"{label} surface drifted")
    return value


def _digest(value: Any, label: str) -> str:
    if type(value) is not str or _SHA.fullmatch(value) is None:
        raise _error(f"{label} digest drifted")
    return value


def _parse(value: str | None) -> int | None:
    return None if value is None else money_integer_v1(value)


def _period_axis(value: Any) -> list[dict[str, Any]]:
    if type(value) is not list or not value:
        raise _error("loan-geography period axis must contain one or more lanes")
    result = []
    seen_periods: set[str] = set()
    period_roles: list[str] = []
    for lane_index, raw in enumerate(value):
        fields = {
            "evidence_ref",
            "lane_index",
            "lane_type",
            "period_end",
            "period_role",
            "resolution_mode",
            "source_surface",
        }
        if type(raw) is not dict or set(raw) != fields:
            raise _error("loan-geography period lane fields drifted")
        if (
            type(raw["lane_index"]) is not int
            or raw["lane_index"] != lane_index
            or raw["lane_type"] != "MONEY"
            or type(raw["period_end"]) is not str
            or _DATE.fullmatch(raw["period_end"]) is None
            or raw["period_role"] not in _PERIOD_ROLES
            or raw["resolution_mode"] not in _PERIOD_RESOLUTION_MODES
        ):
            raise _error("loan-geography period lane identity drifted")
        try:
            date.fromisoformat(raw["period_end"])
        except ValueError as exc:
            raise _error("loan-geography period lane date is invalid") from exc
        _string(raw["evidence_ref"], "loan-geography period evidence")
        _string(raw["source_surface"], "loan-geography period surface")
        if raw["period_end"] in seen_periods:
            raise _error("loan-geography period lanes repeat")
        seen_periods.add(raw["period_end"])
        period_roles.append(raw["period_role"])
        result.append(canonical_clone_v1(raw))
    if period_roles.count("CURRENT") != 1:
        raise _error("loan-geography period axis must contain exactly one current lane")
    return result


def _unit_context(value: Any) -> dict[str, Any]:
    fields = {
        "currency",
        "evidence_ref",
        "resolution_mode",
        "scale",
        "source_surface",
        "unit_kind",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error("loan-geography unit context fields drifted")
    if (
        value["unit_kind"] != "MONEY"
        or value["currency"] != "VND"
        or value["resolution_mode"] not in _UNIT_RESOLUTION_MODES
        or type(value["scale"]) is not int
        or value["scale"] != 6
    ):
        raise _error("loan-geography unit context identity drifted")
    _string(value["evidence_ref"], "loan-geography unit evidence")
    _string(value["source_surface"], "loan-geography unit surface")
    return canonical_clone_v1(value)


def _challenger_refs(value: Any) -> list[dict[str, Any]]:
    if type(value) is not list:
        raise _error("loan-geography structure challenger references drifted")
    result = []
    identities = []
    fields = {
        "challenger_id",
        "kind",
        "model",
        "numeric_authority",
        "page_image_sha256",
        "page_sequence",
        "prompt_sha256",
        "provider",
        "raw_response_sha256",
    }
    for raw in value:
        if (
            type(raw) is not dict
            or set(raw) != fields
            or raw["kind"] != "FULL_PAGE_TABLE_STRUCTURE_PROPOSAL"
            or type(raw["numeric_authority"]) is not bool
            or raw["numeric_authority"] is not False
        ):
            raise _error("loan-geography structure challenger contract drifted")
        identity = _string(raw["challenger_id"], "loan-geography challenger")
        _string(raw["model"], "loan-geography challenger model")
        _string(raw["provider"], "loan-geography challenger provider")
        if type(raw["page_sequence"]) is not int or raw["page_sequence"] <= 0:
            raise _error("loan-geography challenger page binding drifted")
        _digest(raw["page_image_sha256"], "loan-geography challenger page image")
        _digest(raw["prompt_sha256"], "loan-geography challenger prompt")
        _digest(raw["raw_response_sha256"], "loan-geography challenger response")
        identities.append(identity)
        result.append(canonical_clone_v1(raw))
    if identities != sorted(identities) or len(identities) != len(set(identities)):
        raise _error("loan-geography challenger references repeat or reorder")
    return result


def _input_cell(value: Any, lane_index: int) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _INPUT_CELL_FIELDS:
        raise _error("loan-geography input cell fields drifted")
    if (
        type(value["lane_index"]) is not int
        or value["lane_index"] != lane_index
        or value["lane_type"] != "MONEY"
        or type(value["page_sequence"]) is not int
        or value["page_sequence"] <= 0
    ):
        raise _error("loan-geography input cell lane/page binding drifted")
    _string(value["cell_id"], "loan-geography cell")
    bbox = value["bbox"]
    if bbox is not None and (
        type(bbox) is not list
        or len(bbox) != 4
        or any(type(item) is not int or item < 0 for item in bbox)
        or not (bbox[0] < bbox[2] and bbox[1] < bbox[3])
    ):
        raise _error("loan-geography cell bbox drifted")
    line = value["source_line_index"]
    if line is not None and (type(line) is not int or line < 0):
        raise _error("loan-geography cell source line drifted")
    sample = value["sample_id"]
    if sample is not None and (type(sample) is not str or not sample):
        raise _error("loan-geography cell sample drifted")
    crop = value["crop_sha256"]
    if crop is not None:
        _digest(crop, "loan-geography cell crop")
    score = value["ppocrv6_score"]
    if score is not None and (type(score) is not float or not 0 <= score <= 1):
        raise _error("loan-geography PP-OCRv6 score drifted")
    _surface(value["ppocrv6_surface"], "loan-geography PP-OCRv6")
    _surface(value["vietocr_surface"], "loan-geography VietOCR")
    if bbox is None and line is not None:
        raise _error("loan-geography source line cannot exist without bbox")
    return canonical_clone_v1(value)


def _input_row(value: Any, role: str, lane_count: int) -> dict[str, Any]:
    fields = {"cells", "label_evidence_ref", "label_surface", "role"}
    if type(value) is not dict or set(value) != fields or value["role"] != role:
        raise _error("loan-geography input row identity drifted")
    _string(value["label_evidence_ref"], "loan-geography label evidence")
    _string(value["label_surface"], "loan-geography label surface")
    if type(value["cells"]) is not list or len(value["cells"]) != lane_count:
        raise _error("loan-geography row must bind every observed money period lane")
    return {
        "cells": [_input_cell(cell, lane) for lane, cell in enumerate(value["cells"])],
        "label_evidence_ref": value["label_evidence_ref"],
        "label_surface": value["label_surface"],
        "role": role,
    }


def _total_control_evidence(value: Any, lane_count: int) -> list[dict[str, Any]]:
    if type(value) is not list or len(value) != lane_count:
        raise _error("loan-geography printed-total control axis drifted")
    result = []
    fields = {
        "evidence_refs",
        "label_evidence_ref",
        "label_surface",
        "lane_index",
        "page_sequence",
        "resolution_mode",
        "row_bbox",
        "source_bboxes",
        "source_line_indices",
        "source_surfaces_raw_nfc",
    }
    for lane_index, raw in enumerate(value):
        if (
            type(raw) is not dict
            or set(raw) != fields
            or raw["lane_index"] != lane_index
            or type(raw["page_sequence"]) is not int
            or raw["page_sequence"] <= 0
            or raw["resolution_mode"] not in _TOTAL_CONTROL_RESOLUTION_MODES
        ):
            raise _error("loan-geography printed-total control identity drifted")
        _string(raw["label_evidence_ref"], "loan-geography printed-total lane evidence")
        _surface(raw["label_surface"], "loan-geography printed-total lane label")
        if (
            raw["resolution_mode"] == "LOCAL_UNLABELED_TOTAL_ROW"
            and raw["label_surface"] is not None
        ) or (
            raw["resolution_mode"] == "LOCAL_LABELED_TOTAL"
            and type(raw["label_surface"]) is not str
        ):
            raise _error("loan-geography printed-total lane label/resolution mode conflicts")
        row_bbox = raw["row_bbox"]
        if (
            type(row_bbox) is not list
            or len(row_bbox) != 4
            or any(type(item) is not int or item < 0 for item in row_bbox)
            or not (row_bbox[0] < row_bbox[2] and row_bbox[1] < row_bbox[3])
        ):
            raise _error("loan-geography printed-total row bbox drifted")
        evidence_refs = raw["evidence_refs"]
        source_bboxes = raw["source_bboxes"]
        source_indices = raw["source_line_indices"]
        source_surfaces = raw["source_surfaces_raw_nfc"]
        if (
            type(evidence_refs) is not list
            or not evidence_refs
            or type(source_bboxes) is not list
            or type(source_indices) is not list
            or type(source_surfaces) is not list
            or not (
                len(evidence_refs)
                == len(source_bboxes)
                == len(source_indices)
                == len(source_surfaces)
            )
            or any(type(item) is not str or not item for item in evidence_refs)
            or any(type(item) is not int or item < 0 for item in source_indices)
            or any(type(item) is not str for item in source_surfaces)
            or len(source_indices) != len(set(source_indices))
        ):
            raise _error("loan-geography printed-total raw evidence axis drifted")
        for bbox in source_bboxes:
            if (
                type(bbox) is not list
                or len(bbox) != 4
                or any(type(item) is not int or item < 0 for item in bbox)
                or not (bbox[0] < bbox[2] and bbox[1] < bbox[3])
            ):
                raise _error("loan-geography printed-total evidence bbox drifted")
        result.append(canonical_clone_v1(raw))
    return result


def _input_total_row(value: Any, lane_count: int) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "cells",
        "control_evidence",
        "label_evidence_ref",
        "label_surface",
        "role",
    }:
        raise _error("loan-geography printed-total row fields drifted")
    if value["role"] != _TOTAL_ROLE:
        raise _error("loan-geography printed-total row identity drifted")
    _string(value["label_evidence_ref"], "loan-geography printed-total evidence")
    _surface(value["label_surface"], "loan-geography printed-total label")
    if type(value["cells"]) is not list or len(value["cells"]) != lane_count:
        raise _error("loan-geography printed-total row must bind every money lane")
    cells = [_input_cell(cell, lane) for lane, cell in enumerate(value["cells"])]
    evidence = _total_control_evidence(value["control_evidence"], lane_count)
    expected_ref = "|".join(item["label_evidence_ref"] for item in evidence)
    lane_surfaces = [item["label_surface"] for item in evidence]
    expected_surface = (
        " | ".join(lane_surfaces) if all(type(item) is str for item in lane_surfaces) else None
    )
    if value["label_evidence_ref"] != expected_ref or value["label_surface"] != expected_surface:
        raise _error("loan-geography printed-total label/resolution mode conflicts")
    for cell, lane_evidence in zip(cells, evidence, strict=True):
        expected_refs = [
            f"line:{lane_evidence['page_sequence']}:{index}"
            for index in lane_evidence["source_line_indices"]
        ]
        boxes = lane_evidence["source_bboxes"]
        union = [
            min(box[0] for box in boxes),
            min(box[1] for box in boxes),
            max(box[2] for box in boxes),
            max(box[3] for box in boxes),
        ]
        if lane_evidence["evidence_refs"] != expected_refs or lane_evidence["row_bbox"] != union:
            raise _error("loan-geography printed-total raw evidence binding drifted")
        if lane_evidence["resolution_mode"] == "LOCAL_UNLABELED_TOTAL_ROW" and (
            cell["page_sequence"] != lane_evidence["page_sequence"]
            or cell["bbox"] not in boxes
            or cell["source_line_index"] not in lane_evidence["source_line_indices"]
        ):
            raise _error("loan-geography unlabeled printed-total cell binding drifted")
    return {
        "cells": cells,
        "control_evidence": evidence,
        "label_evidence_ref": value["label_evidence_ref"],
        "label_surface": value["label_surface"],
        "role": _TOTAL_ROLE,
    }


def _validate_source(value: Any) -> dict[str, Any]:
    fields = {
        "family_id",
        "format_version",
        "known_nested_domestic_roles_outside_contract",
        "lane_types",
        "mapped_rows",
        "period_axis",
        "presentation_mode",
        "printed_customer_loan_total",
        "region_id",
        "source_id",
        "structure_challenger_refs",
        "unit_context",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error("loan-geography numeric input fields drifted")
    if value["format_version"] != INPUT_FORMAT_VERSION or value["family_id"] != FAMILY_ID:
        raise _error("loan-geography numeric input identity drifted")
    _string(value["source_id"], "loan-geography source")
    _string(value["region_id"], "loan-geography region")
    if value["presentation_mode"] not in _PRESENTATION_MODES:
        raise _error("loan-geography presentation mode drifted")
    periods = _period_axis(value["period_axis"])
    lane_count = len(periods)
    if (
        type(value["lane_types"]) is not list
        or len(value["lane_types"]) != lane_count
        or any(lane_type != "MONEY" for lane_type in value["lane_types"])
    ):
        raise _error("loan-geography numeric lane types drifted")
    if value["known_nested_domestic_roles_outside_contract"] != list(_KNOWN_NESTED_ROLES):
        raise _error("loan-geography known nested-role boundary drifted")
    rows = value["mapped_rows"]
    if type(rows) is not list or len(rows) != 2 or any(type(row) is not dict for row in rows):
        raise _error("loan-geography mapped row population drifted")
    row_roles = [row.get("role") for row in rows]
    if len(set(row_roles)) != 2 or set(row_roles) != set(_ROLES):
        raise _error("loan-geography mapped row roles are missing, duplicate, or extra")
    rows_by_role = {row["role"]: row for row in rows}
    typed = {
        **canonical_clone_v1(value),
        "mapped_rows": [_input_row(rows_by_role[role], role, lane_count) for role in _ROLES],
        "period_axis": periods,
        "printed_customer_loan_total": _input_total_row(
            value["printed_customer_loan_total"], lane_count
        ),
        "structure_challenger_refs": _challenger_refs(value["structure_challenger_refs"]),
        "unit_context": _unit_context(value["unit_context"]),
    }
    cells = [
        cell
        for row in [*typed["mapped_rows"], typed["printed_customer_loan_total"]]
        for cell in row["cells"]
    ]
    identities = [cell["cell_id"] for cell in cells]
    if len(identities) != len(set(identities)):
        raise _error("loan-geography input cell identities repeat")
    return typed


def _indexed_cells(source: Mapping[str, Any]) -> dict[str, tuple[str, Mapping[str, Any]]]:
    rows = [*source["mapped_rows"], source["printed_customer_loan_total"]]
    return {cell["cell_id"]: (row["role"], cell) for row in rows for cell in row["cells"]}


def _dash_overlays(
    values: Sequence[Any],
    cells: Mapping[str, tuple[str, Mapping[str, Any]]],
    *,
    region_id: str,
) -> dict[str, dict[str, Any]]:
    result = {}
    for bound in values:
        if type(bound) is not dict or set(bound) != _DASH_BINDING_FIELDS:
            raise _error("loan-geography visible-dash binding fields drifted")
        cell_id = _string(bound["cell_id"], "loan-geography visible-dash cell")
        if (
            type(bound["lane_index"]) is not int
            or type(bound["page_sequence"]) is not int
            or bound["region_id"] != region_id
            or bound["lane_type"] != "MONEY"
        ):
            raise _error("loan-geography visible-dash lane/region binding drifted")
        crop_bytes = bound["crop_png_bytes"]
        if type(crop_bytes) is not bytes:
            raise _error("loan-geography visible-dash crop bytes drifted")
        try:
            evidence = validate_family_first_visible_dash_glyph_evidence_replay_v1(
                bound["evidence"], crop_png_bytes=crop_bytes
            )
        except FamilyFirstVisibleDashGlyphEvidenceV1Error as exc:
            raise _error("loan-geography visible-dash pixel replay failed") from exc
        crop = evidence.get("crop_ref")
        if (
            evidence.get("format_version") != _DASH_FORMAT
            or evidence.get("classification") != "VISIBLE_HORIZONTAL_DASH_GLYPH"
            or type(evidence.get("normalized_value")) is not int
            or evidence["normalized_value"] != 0
            or type(crop) is not dict
        ):
            raise _error("loan-geography dash evidence is not one authenticated zero")
        if cell_id in result or cell_id not in cells:
            raise _error("loan-geography dash binding is duplicate or unused")
        source_role, cell = cells[cell_id]
        crop_sha = _digest(crop.get("sha256"), "loan-geography dash crop")
        if (
            bound["role"] != source_role
            or bound["lane_index"] != cell["lane_index"]
            or bound["page_sequence"] != cell["page_sequence"]
            or _parse(cell["ppocrv6_surface"]) is not None
            or _parse(cell["vietocr_surface"]) is not None
            or (cell["crop_sha256"] is not None and cell["crop_sha256"] != crop_sha)
        ):
            raise _error("loan-geography dash evidence does not bind a nonnumeric source cell")
        evidence_id = evidence.get("evidence_id")
        if type(evidence_id) is not str or _DASH_ID.fullmatch(evidence_id) is None:
            raise _error("loan-geography dash evidence identity drifted")
        result[cell_id] = {
            "classification": "VISIBLE_HORIZONTAL_DASH_GLYPH",
            "crop_sha256": crop_sha,
            "evidence_id": evidence_id,
            "kind": "DIRECT_TYPED_VISIBLE_DASH_EVIDENCE",
            "region_id": region_id,
        }
    return result


def _candidate_values(
    cell: Mapping[str, Any], dash_ref: Mapping[str, Any] | None
) -> tuple[list[dict[str, Any]], int | None, int | None]:
    ppocr = _parse(cell["ppocrv6_surface"])
    viet = _parse(cell["vietocr_surface"])
    grouped: dict[int, list[str]] = {}
    if ppocr is not None:
        grouped.setdefault(ppocr, []).append("PPOCRV6")
    if viet is not None:
        grouped.setdefault(viet, []).append("VIETOCR")
    if dash_ref is not None:
        if grouped:
            raise _error("loan-geography dash evidence overlaps a numeric observation")
        grouped[0] = ["PIXEL_DASH"]
    return (
        [{"readers": readers, "value": value} for value, readers in sorted(grouped.items())],
        ppocr,
        viet,
    )


def _resolved_cell(cell: Mapping[str, Any], dash_ref: Mapping[str, Any] | None) -> dict[str, Any]:
    candidates, ppocr, viet = _candidate_values(cell, dash_ref)
    selected_value = None
    selected_readers: list[str] = []
    if len(candidates) == 1:
        selected_value = candidates[0]["value"]
        selected_readers = list(candidates[0]["readers"])
        if selected_readers == ["PIXEL_DASH"]:
            mode = "TYPED_VISIBLE_DASH_PIXEL_EVIDENCE_ZERO"
        elif len(selected_readers) == 2:
            mode = "READER_CONSENSUS"
        else:
            mode = "SINGLE_PARSEABLE_OBSERVATION"
        status = "RESOLVED_OBSERVED_VALUE"
    elif candidates:
        mode = "UNRESOLVED_READER_CONFLICT"
        status = "UNRESOLVED"
    else:
        mode = "UNRESOLVED_NO_PARSEABLE_OR_TYPED_DASH_OBSERVATION"
        status = "UNRESOLVED"
    return {
        **canonical_clone_v1(cell),
        "candidate_values": candidates,
        "dash_evidence_ref": None if dash_ref is None else canonical_clone_v1(dash_ref),
        "ppocrv6_parsed_value": ppocr,
        "selected_readers": selected_readers,
        "selected_value": selected_value,
        "selection_mode": mode,
        "status": status,
        "vietocr_parsed_value": viet,
    }


def _resolved_row(
    row: Mapping[str, Any], dashes: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    result = {
        "cells": [_resolved_cell(cell, dashes.get(cell["cell_id"])) for cell in row["cells"]],
        "label_evidence_ref": row["label_evidence_ref"],
        "label_surface": row["label_surface"],
        "role": row["role"],
    }
    if "control_evidence" in row:
        result["control_evidence"] = canonical_clone_v1(row["control_evidence"])
    return result


def _choices(cell: Mapping[str, Any]) -> list[tuple[int, list[str]]]:
    if cell["selected_value"] is not None:
        return [(cell["selected_value"], list(cell["selected_readers"]))]
    return [
        (candidate["value"], list(candidate["readers"])) for candidate in cell["candidate_values"]
    ]


def _accounting_check(
    rows: Sequence[Mapping[str, Any]], total: Mapping[str, Any], lane_index: int
) -> dict[str, Any]:
    cells = [row["cells"][lane_index] for row in rows]
    target = total["cells"][lane_index]
    choices = [_choices(cell) for cell in [*cells, target]]
    candidate_assignment_count = 0
    exact = []
    if all(choices):
        candidate_assignment_count = 1
        for options in choices:
            candidate_assignment_count *= len(options)
        for assignment in itertools.product(*choices):
            if assignment[0][0] + assignment[1][0] == assignment[2][0]:
                exact.append(assignment)
    if not all(choices):
        status = "UNRESOLVED_MISSING_OBSERVED_CANDIDATE"
        selected_components: list[int] = []
        selected_total = None
        residual = None
    elif len(exact) == 1:
        assignment = exact[0]
        selected_conflict = False
        for cell, (selected, readers) in zip([*cells, target], assignment, strict=True):
            if cell["selected_value"] is None:
                selected_conflict = True
                cell["selected_value"] = selected
                cell["selected_readers"] = readers
                cell["selection_mode"] = "UNIQUE_OBSERVED_CANDIDATE_SELECTED_BY_EXACT_EQUATION"
                cell["status"] = "RESOLVED_OBSERVED_VALUE"
        selected_components = [assignment[0][0], assignment[1][0]]
        selected_total = assignment[2][0]
        residual = sum(selected_components) - selected_total
        status = (
            "EXACT_EQUATION_UNIQUELY_SELECTED_OBSERVED_CANDIDATES"
            if selected_conflict
            else "EXACT_OBSERVED_EQUATION"
        )
    elif exact:
        status = "UNRESOLVED_MULTIPLE_EXACT_OBSERVED_ASSIGNMENTS"
        selected_components = []
        selected_total = None
        residual = None
    else:
        status = "VETOED_NO_EXACT_OBSERVED_ASSIGNMENT"
        selected_components = []
        selected_total = None
        residual = None
    return {
        "candidate_assignment_count": candidate_assignment_count,
        "component_cell_ids": [cell["cell_id"] for cell in cells],
        "component_roles": list(_ROLES),
        "equation_id": f"DOMESTIC_PLUS_FOREIGN_EQUALS_PRINTED_CUSTOMER_LOAN_TOTAL_LANE_{lane_index}",
        "equation_tolerance": 0,
        "exact_observed_assignment_count": len(exact),
        "lane_index": lane_index,
        "lane_type": "MONEY",
        "required_for_acceptance": True,
        "residual": residual,
        "selected_component_values": selected_components,
        "selected_target_value": selected_total,
        "status": status,
        "target_cell_id": target["cell_id"],
        "target_role": _TOTAL_ROLE,
    }


def _all_cells(
    mapped_rows: Sequence[Mapping[str, Any]], total: Mapping[str, Any]
) -> list[Mapping[str, Any]]:
    return [cell for row in [*mapped_rows, total] for cell in row["cells"]]


def _metrics(
    mapped_rows: Sequence[Mapping[str, Any]],
    total: Mapping[str, Any],
    checks: Sequence[Mapping[str, Any]],
    challengers: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    cells = _all_cells(mapped_rows, total)
    return {
        "accounting_backsolved_or_invented_value_count": 0,
        "accounting_ambiguous_equation_count": sum(
            check["status"] == "UNRESOLVED_MULTIPLE_EXACT_OBSERVED_ASSIGNMENTS" for check in checks
        ),
        "accounting_missing_candidate_equation_count": sum(
            check["status"] == "UNRESOLVED_MISSING_OBSERVED_CANDIDATE" for check in checks
        ),
        "accounting_uniquely_selected_observed_cell_count": sum(
            cell["selection_mode"] == "UNIQUE_OBSERVED_CANDIDATE_SELECTED_BY_EXACT_EQUATION"
            for cell in cells
        ),
        "exact_observed_equation_count": sum(
            check["status"] in _ACCEPTED_CHECK_STATUSES for check in checks
        ),
        "gemma_numeric_authority_count": 0,
        "known_nested_domestic_role_count": len(_KNOWN_NESTED_ROLES),
        "mapped_money_cell_count": len(mapped_rows) * len(mapped_rows[0]["cells"]),
        "observed_numeric_candidate_value_count": sum(
            len(cell["candidate_values"]) for cell in cells
        ),
        "period_lane_count": len(total["cells"]),
        "ppocrv6_vietocr_numeric_disagreement_count": sum(
            cell["ppocrv6_parsed_value"] is not None
            and cell["vietocr_parsed_value"] is not None
            and cell["ppocrv6_parsed_value"] != cell["vietocr_parsed_value"]
            for cell in cells
        ),
        "ppocrv6_vietocr_raw_surface_disagreement_count": sum(
            cell["ppocrv6_surface"] is not None
            and cell["vietocr_surface"] is not None
            and cell["ppocrv6_surface"] != cell["vietocr_surface"]
            for cell in cells
        ),
        "source_control_money_cell_count": len(total["cells"]),
        "source_control_row_count": 1,
        "structure_challenger_count": len(challengers),
        "unresolved_observed_cell_count": sum(cell["selected_value"] is None for cell in cells),
        "visible_dash_zero_cell_count": sum(
            cell["selection_mode"] == "TYPED_VISIBLE_DASH_PIXEL_EVIDENCE_ZERO" for cell in cells
        ),
        "vetoed_equation_count": sum(
            check["status"] == "VETOED_NO_EXACT_OBSERVED_ASSIGNMENT" for check in checks
        ),
    }


def _unresolved_reasons(
    checks: Sequence[Mapping[str, Any]], cells: Sequence[Mapping[str, Any]]
) -> list[str]:
    reasons = [
        f"REQUIRED_ACCOUNTING_CHECK_FAILED:{check['equation_id']}:{check['status']}"
        for check in checks
        if check["status"] not in _ACCEPTED_CHECK_STATUSES
    ]
    if any(cell["selected_value"] is None for cell in cells):
        reasons.append("ONE_OR_MORE_SOURCE_CELLS_LACK_A_UNIQUE_OBSERVED_VALUE")
    return reasons


def _raw_cell(value: Mapping[str, Any]) -> dict[str, Any]:
    return {field: canonical_clone_v1(value[field]) for field in _INPUT_CELL_FIELDS}


def _raw_row(value: Mapping[str, Any]) -> dict[str, Any]:
    result = {
        "cells": [_raw_cell(cell) for cell in value["cells"]],
        "label_evidence_ref": value["label_evidence_ref"],
        "label_surface": value["label_surface"],
        "role": value["role"],
    }
    if "control_evidence" in value:
        result["control_evidence"] = canonical_clone_v1(value["control_evidence"])
    return result


def _source_from_result(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "family_id": FAMILY_ID,
        "format_version": INPUT_FORMAT_VERSION,
        "known_nested_domestic_roles_outside_contract": canonical_clone_v1(
            value["known_nested_domestic_roles_outside_contract"]
        ),
        "lane_types": canonical_clone_v1(value["lane_types"]),
        "mapped_rows": [_raw_row(row) for row in value["mapped_rows"]],
        "period_axis": canonical_clone_v1(value["period_axis"]),
        "presentation_mode": value["presentation_mode"],
        "printed_customer_loan_total": _raw_row(value["printed_customer_loan_total"]),
        "region_id": value["region_id"],
        "source_id": value["source_id"],
        "structure_challenger_refs": canonical_clone_v1(value["structure_challenger_refs"]),
        "unit_context": canonical_clone_v1(value["unit_context"]),
    }


def _validate_dash_ref(value: Any, cell: Mapping[str, Any], region_id: str) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _DASH_REF_FIELDS
        or value["classification"] != "VISIBLE_HORIZONTAL_DASH_GLYPH"
        or value["kind"] != "DIRECT_TYPED_VISIBLE_DASH_EVIDENCE"
        or value["region_id"] != region_id
        or type(value["evidence_id"]) is not str
        or _DASH_ID.fullmatch(value["evidence_id"]) is None
    ):
        raise _error("loan-geography persisted dash evidence reference drifted")
    crop = _digest(value["crop_sha256"], "loan-geography persisted dash crop")
    if (
        _parse(cell["ppocrv6_surface"]) is not None
        or _parse(cell["vietocr_surface"]) is not None
        or (cell["crop_sha256"] is not None and cell["crop_sha256"] != crop)
    ):
        raise _error("loan-geography persisted dash reference overlaps numeric source")
    return canonical_clone_v1(value)


def _build_material(
    source: Mapping[str, Any], dashes: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    mapped = [_resolved_row(row, dashes) for row in source["mapped_rows"]]
    total = _resolved_row(source["printed_customer_loan_total"], dashes)
    checks = [_accounting_check(mapped, total, lane) for lane in range(len(source["period_axis"]))]
    cells = _all_cells(mapped, total)
    unresolved = _unresolved_reasons(checks, cells)
    evidence_ids = sorted(ref["evidence_id"] for ref in dashes.values())
    input_id = "lgnrv1:input:" + canonical_json_sha256_v1(
        {"source": source, "visible_dash_evidence_ids": evidence_ids}
    )
    return {
        "accounting_checks": checks,
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "input_id": input_id,
        "known_nested_domestic_roles_outside_contract": canonical_clone_v1(
            source["known_nested_domestic_roles_outside_contract"]
        ),
        "lane_types": canonical_clone_v1(source["lane_types"]),
        "mapped_rows": mapped,
        "metrics": _metrics(mapped, total, checks, source["structure_challenger_refs"]),
        "period_axis": canonical_clone_v1(source["period_axis"]),
        "presentation_mode": source["presentation_mode"],
        "printed_customer_loan_total": total,
        "region_id": source["region_id"],
        "source_id": source["source_id"],
        "status": "EXACT_OBSERVED_NUMERIC_RECONCILIATION" if not unresolved else "UNRESOLVED",
        "structure_challenger_refs": canonical_clone_v1(source["structure_challenger_refs"]),
        "unit_context": canonical_clone_v1(source["unit_context"]),
        "unresolved_reasons": unresolved,
        "visible_dash_evidence_ids": evidence_ids,
    }


def _validate_result(value: Any) -> dict[str, Any]:
    fields = {
        "accounting_checks",
        "authority",
        "claim_boundary",
        "family_id",
        "format_version",
        "input_id",
        "known_nested_domestic_roles_outside_contract",
        "lane_types",
        "mapped_rows",
        "metrics",
        "period_axis",
        "presentation_mode",
        "printed_customer_loan_total",
        "region_id",
        "result_id",
        "source_id",
        "status",
        "structure_challenger_refs",
        "unit_context",
        "unresolved_reasons",
        "visible_dash_evidence_ids",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value["format_version"] != FORMAT_VERSION
        or value["family_id"] != FAMILY_ID
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["authority"] != _AUTHORITY
        or value["status"] not in {"EXACT_OBSERVED_NUMERIC_RECONCILIATION", "UNRESOLVED"}
    ):
        raise _error("loan-geography numeric result contract drifted")
    source = _validate_source(_source_from_result(value))
    rows = value["mapped_rows"]
    if type(rows) is not list or len(rows) != 2:
        raise _error("loan-geography result mapped rows drifted")
    raw_index = _indexed_cells(source)
    dashes: dict[str, dict[str, Any]] = {}
    for row, expected_role in zip(
        [*rows, value["printed_customer_loan_total"]], [*_ROLES, _TOTAL_ROLE], strict=True
    ):
        expected_fields = {"cells", "label_evidence_ref", "label_surface", "role"}
        if expected_role == _TOTAL_ROLE:
            expected_fields.add("control_evidence")
        if (
            type(row) is not dict
            or set(row) != expected_fields
            or row["role"] != expected_role
            or type(row["cells"]) is not list
            or len(row["cells"]) != len(source["period_axis"])
        ):
            raise _error("loan-geography resolved row contract drifted")
        for lane, cell in enumerate(row["cells"]):
            if type(cell) is not dict or set(cell) != _INPUT_CELL_FIELDS | _RESOLUTION_FIELDS:
                raise _error("loan-geography resolved cell fields drifted")
            raw = _input_cell(_raw_cell(cell), lane)
            indexed = raw_index.get(raw["cell_id"])
            if indexed is None or indexed[0] != expected_role:
                raise _error("loan-geography resolved cell/source binding drifted")
            dash_ref = cell["dash_evidence_ref"]
            if dash_ref is not None:
                if raw["cell_id"] in dashes:
                    raise _error("loan-geography persisted dash reference repeats")
                dashes[raw["cell_id"]] = _validate_dash_ref(dash_ref, raw, value["region_id"])
    expected = _build_material(source, dashes)
    observed_material = canonical_clone_v1(value)
    identity = observed_material.pop("result_id")
    if not same_typed_json_v1(observed_material, expected):
        raise _error("loan-geography numeric result semantics drifted")
    if identity != "lgnrv1:result:" + canonical_json_sha256_v1(expected):
        raise _error("loan-geography numeric result identity drifted")
    return canonical_clone_v1(value)


def build_loan_geography_numeric_reconciliation_v1(
    source: Any, *, visible_dash_evidence: Sequence[Any] = ()
) -> dict[str, Any]:
    """Reconcile one graph-bound geography matrix without inference."""

    if isinstance(visible_dash_evidence, (str, bytes, bytearray)) or not isinstance(
        visible_dash_evidence, Sequence
    ):
        raise _error("loan-geography visible-dash evidence must be one sequence")
    typed = _validate_source(source)
    dashes = _dash_overlays(
        visible_dash_evidence, _indexed_cells(typed), region_id=typed["region_id"]
    )
    material = _build_material(typed, dashes)
    return _validate_result(
        {**material, "result_id": "lgnrv1:result:" + canonical_json_sha256_v1(material)}
    )


def validate_loan_geography_numeric_reconciliation_v1(value: Any) -> dict[str, Any]:
    """Validate one content-addressed, semantically closed result."""

    return _validate_result(value)


def validate_loan_geography_numeric_reconciliation_replay_v1(
    value: Any,
    source: Any,
    *,
    visible_dash_evidence: Sequence[Any] = (),
) -> dict[str, Any]:
    """Rebuild from raw source and pixel evidence, then require exact equality."""

    persisted = _validate_result(value)
    rebuilt = build_loan_geography_numeric_reconciliation_v1(
        source, visible_dash_evidence=visible_dash_evidence
    )
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("loan-geography numeric reconciliation does not replay exactly")
    return rebuilt
