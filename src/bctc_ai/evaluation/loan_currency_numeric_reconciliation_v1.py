"""Graph-neutral numeric reconciliation for customer-loan currency tables.

The caller supplies rows already bound by a structural graph.  This module
does not discover tables or choose schema identities.  PP-OCRv6 remains the
primary numeric surface, VietOCR is retained as an independent raw surface,
and only a content-addressed visible-dash pixel observation may normalize an
otherwise unreadable cell to zero.  Printed totals corroborate or veto the
observations; they never infer or back-solve a missing value.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
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
    "LoanCurrencyNumericReconciliationV1Error",
    "build_loan_currency_numeric_reconciliation_v1",
    "validate_loan_currency_numeric_reconciliation_replay_v1",
    "validate_loan_currency_numeric_reconciliation_v1",
]


FORMAT_VERSION = "LOAN_CURRENCY_NUMERIC_RECONCILIATION_V1"
INPUT_FORMAT_VERSION = "LOAN_CURRENCY_NUMERIC_RECONCILIATION_INPUT_V1"
FAMILY_ID = "LOAN_CURRENCY_CLASSIFICATION"
CLAIM_BOUNDARY = (
    "BOUND_PPOCRV6_VIETOCR_TWO_MONEY_LANES_AND_AUTHENTICATED_VISIBLE_DASH_"
    "PIXEL_EVIDENCE_OR_BOUNDED_HIGH_FILL_MARK_WITH_DISTINCT_AUTHENTICATED_PIXEL_"
    "PEER_AND_EXACT_PRINTED_ACCOUNTING_CORROBORATION_OR_VETO_ONLY_"
    "NO_BACKSOLVE_GEMMA_SCHEMA_MAPPING_TABLE_DISCOVERY_CANONICALIZATION_OR_"
    "EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "accounting_can_infer_or_backsolve_value": False,
    "accounting_is_corroboration_or_veto_only": True,
    "blank_or_missing_cell_is_zero": False,
    "bounded_mark_pairing_is_pixel_only_before_accounting_veto": True,
    "gemma_used": False,
    "mapping_authority": False,
    "parent_or_source_total_emitted_as_mapping": False,
    "ppocrv6_primary_surface_retained": True,
    "schema_authority": False,
    "source_only_additional_population_emitted_as_mapping": False,
    "vietocr_surface_retained": True,
    "visible_dash_requires_typed_pixel_evidence": True,
}
_MAPPED_ROLES = ("VND_LOANS", "FOREIGN_CURRENCY_AND_GOLD_LOANS")
_ADDITIONAL_PARENT_ROLE = "DEFERRED_LC_PRE_2024_GROUP"
_ADDITIONAL_BREAKDOWN_ROLES = ("DEFERRED_LC_VND", "DEFERRED_LC_FOREIGN")
_LANE_TYPES = ("MONEY", "MONEY")
_DASH_FORMAT = "FAMILY_FIRST_VISIBLE_DASH_GLYPH_EVIDENCE_V1"
_SHA = frozenset("0123456789abcdef")
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
_RESOLUTION_CELL_FIELDS = {
    "evidence_ref",
    "ppocrv6_parsed_value",
    "selected_surface",
    "selected_value",
    "selection_mode",
    "status",
    "vietocr_parsed_value",
}
_ACCEPTED_CHECK_STATUS = "CORROBORATED_EXACT_OBSERVED_EQUATION"
_PAIR_BINDING_FIELDS = {
    "candidate_admission_class",
    "candidate_cell_id",
    "candidate_evidence_id",
    "candidate_overlay_evidence_id",
    "candidate_packet_id",
    "candidate_raw_classification",
    "candidate_region_id",
    "column_ordinal",
    "pair_binding_id",
    "peer_cell_id",
    "peer_evidence_id",
    "peer_overlay_evidence_id",
    "peer_packet_id",
    "peer_raw_classification",
    "peer_region_id",
    "resolved_period",
    "role",
    "source_population_role",
}
_REPLAY_MATERIAL_FIELDS = {
    "admission_class",
    "cell_id",
    "crop_png_bytes",
    "document_packet_id",
    "evidence",
    "lane_index",
    "lane_type",
    "overlay_evidence_id",
    "page_sequence",
    "raw_classification",
    "region_id",
    "resolved_period",
    "role",
    "source_population_role",
    "source_population_surface",
}
_PAIR_EVIDENCE_REF_FIELDS = {
    "candidate_crop_sha256",
    "classification",
    "crop_sha256",
    "evidence_id",
    "kind",
    "pair_binding",
    "peer_crop_sha256",
    "region_id",
}


class LoanCurrencyNumericReconciliationV1Error(ValueError):
    """The bound source, dash observation, accounting closure, or replay drifted."""


def _error(message: str) -> LoanCurrencyNumericReconciliationV1Error:
    return LoanCurrencyNumericReconciliationV1Error(message)


def _string(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        raise _error(f"{label} string drifted")
    return value


def _digest(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 64 or any(char not in _SHA for char in value):
        raise _error(f"{label} digest drifted")
    return value


def _dash_evidence_identifier(value: Any, label: str) -> str:
    prefix = "ffvdgev1:evidence:"
    if type(value) is not str or not value.startswith(prefix):
        raise _error(f"{label} identity drifted")
    _digest(value.removeprefix(prefix), label)
    return value


def _surface(value: Any, label: str) -> str | None:
    if value is not None and type(value) is not str:
        raise _error(f"{label} surface drifted")
    return value


def _parse(surface: str | None) -> int | None:
    return None if surface is None else money_integer_v1(surface)


def _input_cell(value: Any, lane_index: int) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _INPUT_CELL_FIELDS:
        raise _error("loan-currency numeric input cell fields drifted")
    if (
        type(value["lane_index"]) is not int
        or value["lane_index"] != lane_index
        or value["lane_type"] != "MONEY"
    ):
        raise _error("loan-currency numeric cell typed-lane binding drifted")
    _string(value["cell_id"], "loan-currency cell")
    bbox = value["bbox"]
    if bbox is not None and (
        type(bbox) is not list
        or len(bbox) != 4
        or any(type(item) is not int or item < 0 for item in bbox)
        or not (bbox[0] < bbox[2] and bbox[1] < bbox[3])
    ):
        raise _error("loan-currency numeric cell bbox drifted")
    page = value["page_sequence"]
    if type(page) is not int or page <= 0:
        raise _error("loan-currency numeric cell page binding drifted")
    line = value["source_line_index"]
    if line is not None and (type(line) is not int or line < 0):
        raise _error("loan-currency numeric source-line binding drifted")
    sample = value["sample_id"]
    if sample is not None and (type(sample) is not str or not sample):
        raise _error("loan-currency numeric sample binding drifted")
    crop = value["crop_sha256"]
    if crop is not None:
        _digest(crop, "loan-currency numeric crop")
    score = value["ppocrv6_score"]
    if score is not None and (type(score) is not float or not 0 <= score <= 1):
        raise _error("loan-currency PP-OCRv6 score drifted")
    _surface(value["ppocrv6_surface"], "PP-OCRv6")
    _surface(value["vietocr_surface"], "VietOCR")
    if bbox is None and line is not None:
        raise _error("loan-currency source line cannot exist without bbox")
    return canonical_clone_v1(value)


def _input_row(value: Any, role: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {"cells", "label_surface", "role"}:
        raise _error("loan-currency numeric input row fields drifted")
    if value["role"] != role:
        raise _error("loan-currency numeric input row role drifted")
    _string(value["label_surface"], "loan-currency row label")
    if type(value["cells"]) is not list or len(value["cells"]) != 2:
        raise _error("loan-currency numeric row must bind exactly two money lanes")
    return {
        "cells": [_input_cell(cell, index) for index, cell in enumerate(value["cells"])],
        "label_surface": value["label_surface"],
        "role": role,
    }


def _validate_source(value: Any) -> dict[str, Any]:
    fields = {
        "additional_population",
        "core_total",
        "family_id",
        "format_version",
        "grand_total",
        "lane_types",
        "mapped_rows",
        "period_axis",
        "source_id",
        "unit_context",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error("loan-currency numeric reconciliation input fields drifted")
    if value["format_version"] != INPUT_FORMAT_VERSION or value["family_id"] != FAMILY_ID:
        raise _error("loan-currency numeric input identity drifted")
    _string(value["source_id"], "loan-currency numeric source")
    if type(value["lane_types"]) is not list or tuple(value["lane_types"]) != _LANE_TYPES:
        raise _error("loan-currency numeric lane layout is unsupported")
    if (
        type(value["period_axis"]) is not dict
        or not value["period_axis"]
        or type(value["unit_context"]) is not dict
        or not value["unit_context"]
    ):
        raise _error("loan-currency period/unit context must remain typed objects")
    rows = value["mapped_rows"]
    if (
        type(rows) is not list
        or len(rows) != 2
        or [row.get("role") for row in rows if type(row) is dict] != list(_MAPPED_ROLES)
    ):
        raise _error("loan-currency mapped row population/order drifted")
    mapped_rows = [_input_row(row, role) for row, role in zip(rows, _MAPPED_ROLES, strict=True)]
    core_total = _input_row(value["core_total"], "CORE_TOTAL")
    additional = value["additional_population"]
    if additional is None:
        typed_additional = None
        if value["grand_total"] is not None:
            raise _error("grand total without additional source population is unsupported")
        grand_total = None
    else:
        if type(additional) is not dict or set(additional) != {"breakdown_rows", "parent"}:
            raise _error("loan-currency additional population fields drifted")
        breakdown = additional["breakdown_rows"]
        if (
            type(breakdown) is not list
            or len(breakdown) != 2
            or [row.get("role") for row in breakdown if type(row) is dict]
            != list(_ADDITIONAL_BREAKDOWN_ROLES)
        ):
            raise _error("loan-currency additional breakdown population/order drifted")
        typed_additional = {
            "breakdown_rows": [
                _input_row(row, role)
                for row, role in zip(breakdown, _ADDITIONAL_BREAKDOWN_ROLES, strict=True)
            ],
            "parent": _input_row(additional["parent"], _ADDITIONAL_PARENT_ROLE),
        }
        if value["grand_total"] is None:
            raise _error("additional source population requires one printed grand total")
        grand_total = _input_row(value["grand_total"], "GRAND_TOTAL")
    result = {
        **canonical_clone_v1(value),
        "additional_population": typed_additional,
        "core_total": core_total,
        "grand_total": grand_total,
        "mapped_rows": mapped_rows,
    }
    cells = _all_input_cells(result)
    identities = [cell["cell_id"] for _role, cell in cells]
    if len(identities) != len(set(identities)):
        raise _error("loan-currency numeric cell identities are not unique")
    return result


def _all_input_cells(source: Mapping[str, Any]) -> list[tuple[str, Mapping[str, Any]]]:
    result = [(row["role"], cell) for row in source["mapped_rows"] for cell in row["cells"]]
    result.extend((source["core_total"]["role"], cell) for cell in source["core_total"]["cells"])
    additional = source["additional_population"]
    if additional is not None:
        result.extend(
            (additional["parent"]["role"], cell) for cell in additional["parent"]["cells"]
        )
        result.extend(
            (row["role"], cell) for row in additional["breakdown_rows"] for cell in row["cells"]
        )
        result.extend(
            (source["grand_total"]["role"], cell) for cell in source["grand_total"]["cells"]
        )
    return result


def _dash_overlays(
    values: Sequence[Any], cells: Mapping[str, tuple[str, Mapping[str, Any]]]
) -> dict[str, dict[str, Any]]:
    result = {}
    for bound in values:
        fields = {
            "cell_id",
            "crop_png_bytes",
            "evidence",
            "lane_index",
            "lane_type",
            "page_sequence",
            "region_id",
            "role",
        }
        if type(bound) is not dict or set(bound) != fields:
            raise _error("loan-currency visible-dash binding fields drifted")
        cell_id = _string(bound["cell_id"], "loan-currency visible-dash cell")
        region_id = _string(bound["region_id"], "loan-currency visible-dash region")
        if type(bound["lane_index"]) is not int or type(bound["page_sequence"]) is not int:
            raise _error("loan-currency visible-dash typed lane/page drifted")
        crop_png_bytes = bound["crop_png_bytes"]
        if type(crop_png_bytes) is not bytes:
            raise _error("loan-currency visible-dash replay crop bytes drifted")
        try:
            evidence = validate_family_first_visible_dash_glyph_evidence_replay_v1(
                bound["evidence"], crop_png_bytes=crop_png_bytes
            )
        except FamilyFirstVisibleDashGlyphEvidenceV1Error as exc:
            raise _error("loan-currency visible-dash pixel replay failed") from exc
        if evidence.get("format_version") != _DASH_FORMAT:
            raise _error("loan-currency visible-dash evidence type drifted")
        material = canonical_clone_v1(evidence)
        evidence_id = material.pop("evidence_id", None)
        if evidence_id != "ffvdgev1:evidence:" + canonical_json_sha256_v1(material):
            raise _error("loan-currency visible-dash evidence identity drifted")
        crop = evidence.get("crop_ref")
        if (
            evidence.get("classification") != "VISIBLE_HORIZONTAL_DASH_GLYPH"
            or type(evidence.get("normalized_value")) is not int
            or evidence["normalized_value"] != 0
            or type(crop) is not dict
        ):
            raise _error("loan-currency visible-dash evidence is not one authenticated zero")
        crop_sha = _digest(crop.get("sha256"), "loan-currency visible-dash crop")
        if cell_id in result or cell_id not in cells:
            raise _error("loan-currency visible-dash binding is duplicate or unused")
        source_role, source_cell = cells[cell_id]
        if (
            bound["role"] != source_role
            or bound["lane_index"] != source_cell["lane_index"]
            or bound["lane_type"] != source_cell["lane_type"]
            or bound["page_sequence"] != source_cell["page_sequence"]
            or _parse(source_cell["ppocrv6_surface"]) is not None
            or (source_cell["crop_sha256"] is not None and source_cell["crop_sha256"] != crop_sha)
        ):
            raise _error("loan-currency visible-dash evidence does not bind its raw source cell")
        result[cell_id] = {
            "crop_sha256": crop_sha,
            "evidence_id": evidence_id,
            "evidence_ref": {
                "classification": "VISIBLE_HORIZONTAL_DASH_GLYPH",
                "crop_sha256": crop_sha,
                "evidence_id": evidence_id,
                "kind": "DIRECT_TYPED_VISIBLE_DASH_EVIDENCE",
                "region_id": region_id,
            },
        }
    return result


def _bounded_high_fill_candidate(value: Mapping[str, Any]) -> bool:
    metrics = value.get("glyph_metrics")
    return (
        type(metrics) is dict
        and metrics.get("component_count") == 1
        and type(metrics.get("component_aspect_ratio")) is float
        and 1.25 <= metrics["component_aspect_ratio"] < 1.8
        and type(metrics.get("component_height_ratio")) is float
        and 0.15 <= metrics["component_height_ratio"] <= 0.30
        and type(metrics.get("component_width_ratio")) is float
        and 0.10 <= metrics["component_width_ratio"] <= 0.30
        and type(metrics.get("ink_fill_ratio")) is float
        and metrics["ink_fill_ratio"] >= 0.60
        and type(metrics.get("horizontal_center_displacement_ratio")) is float
        and metrics["horizontal_center_displacement_ratio"] <= 0.05
        and type(metrics.get("vertical_center_displacement_ratio")) is float
        and metrics["vertical_center_displacement_ratio"] <= 0.05
    )


def _pair_binding(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _PAIR_BINDING_FIELDS:
        raise _error("loan-currency bounded dash pair binding fields drifted")
    for field in _PAIR_BINDING_FIELDS - {"column_ordinal"}:
        _string(value[field], f"loan-currency bounded dash pair {field}")
    if type(value["column_ordinal"]) is not int or value["column_ordinal"] not in {0, 1}:
        raise _error("loan-currency bounded dash pair lane drifted")
    _dash_evidence_identifier(
        value["candidate_evidence_id"], "loan-currency bounded candidate evidence"
    )
    _dash_evidence_identifier(value["peer_evidence_id"], "loan-currency bounded peer evidence")
    if (
        value["candidate_admission_class"] != "BOUNDED_CENTERED_HIGH_FILL_HORIZONTAL_MARK_CANDIDATE"
        or value["peer_raw_classification"] != "VISIBLE_HORIZONTAL_DASH_GLYPH"
        or value["candidate_raw_classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH"
        or value["role"] not in {_ADDITIONAL_PARENT_ROLE, *_ADDITIONAL_BREAKDOWN_ROLES}
        or value["source_population_role"] != _ADDITIONAL_PARENT_ROLE
        or value["candidate_cell_id"] == value["peer_cell_id"]
        or value["candidate_region_id"] == value["peer_region_id"]
        or value["candidate_packet_id"] == value["peer_packet_id"]
    ):
        raise _error("loan-currency bounded dash pair semantics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("pair_binding_id")
    if identity != "lcdashv1:pair:" + canonical_json_sha256_v1(material):
        raise _error("loan-currency bounded dash pair identity drifted")
    return canonical_clone_v1(value)


def _replayed_mark_material(value: Any, *, expected_admission: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _REPLAY_MATERIAL_FIELDS:
        raise _error("loan-currency bounded dash replay material fields drifted")
    if value["admission_class"] != expected_admission or value["lane_type"] != "MONEY":
        raise _error("loan-currency bounded dash replay admission/lane drifted")
    if (
        type(value["lane_index"]) is not int
        or value["lane_index"] not in {0, 1}
        or type(value["page_sequence"]) is not int
        or value["page_sequence"] <= 0
    ):
        raise _error("loan-currency bounded dash replay geometry axis drifted")
    for field in (
        "cell_id",
        "document_packet_id",
        "overlay_evidence_id",
        "raw_classification",
        "region_id",
        "resolved_period",
        "role",
        "source_population_role",
        "source_population_surface",
    ):
        _string(value[field], f"loan-currency bounded dash replay {field}")
    crop = value["crop_png_bytes"]
    if type(crop) is not bytes:
        raise _error("loan-currency bounded dash replay crop bytes drifted")
    try:
        evidence = validate_family_first_visible_dash_glyph_evidence_replay_v1(
            value["evidence"], crop_png_bytes=crop
        )
    except FamilyFirstVisibleDashGlyphEvidenceV1Error as exc:
        raise _error("loan-currency bounded dash exact pixel replay failed") from exc
    if (
        evidence.get("format_version") != _DASH_FORMAT
        or evidence.get("classification") != value["raw_classification"]
        or type(evidence.get("crop_ref")) is not dict
    ):
        raise _error("loan-currency bounded dash raw classifier binding drifted")
    if expected_admission == "DIRECT_VISIBLE_HORIZONTAL_DASH":
        if (
            evidence["classification"] != "VISIBLE_HORIZONTAL_DASH_GLYPH"
            or evidence.get("normalized_value") != 0
        ):
            raise _error("loan-currency bounded dash peer is not one direct dash")
    elif (
        evidence["classification"] == "VISIBLE_HORIZONTAL_DASH_GLYPH"
        or evidence.get("normalized_value") is not None
        or not _bounded_high_fill_candidate(evidence)
    ):
        raise _error("loan-currency bounded dash candidate pixel predicate failed")
    return {
        **{
            key: bytes(item) if key == "crop_png_bytes" else canonical_clone_v1(item)
            for key, item in value.items()
        },
        "evidence": evidence,
    }


def _source_period(source: Mapping[str, Any], lane: int) -> str:
    periods = source["period_axis"].get("periods")
    if type(periods) is not list or len(periods) != 2:
        raise _error("loan-currency bounded dash needs two source periods")
    item = periods[lane]
    if type(item) is str:
        return _string(item, "loan-currency source period")
    if type(item) is dict:
        for key in ("resolved_period", "period"):
            if key in item:
                return _string(item[key], "loan-currency source period")
    raise _error("loan-currency source period record drifted")


def _bounded_dash_overlays(
    values: Sequence[Any],
    cells: Mapping[str, tuple[str, Mapping[str, Any]]],
    source: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    result = {}
    for value in values:
        if type(value) is not dict or set(value) != {"candidate", "pair_binding", "peer"}:
            raise _error("loan-currency bounded dash input fields drifted")
        pair = _pair_binding(value["pair_binding"])
        candidate = _replayed_mark_material(
            value["candidate"],
            expected_admission="BOUNDED_CENTERED_HIGH_FILL_HORIZONTAL_MARK_CANDIDATE",
        )
        peer = _replayed_mark_material(
            value["peer"], expected_admission="DIRECT_VISIBLE_HORIZONTAL_DASH"
        )
        candidate_id = candidate["cell_id"]
        if candidate_id in result or candidate_id not in cells:
            raise _error("loan-currency bounded dash candidate is duplicate or unused")
        source_role, source_cell = cells[candidate_id]
        joins = {
            "candidate_admission_class": candidate["admission_class"],
            "candidate_cell_id": candidate_id,
            "candidate_evidence_id": candidate["evidence"]["evidence_id"],
            "candidate_overlay_evidence_id": candidate["overlay_evidence_id"],
            "candidate_packet_id": candidate["document_packet_id"],
            "candidate_raw_classification": candidate["raw_classification"],
            "candidate_region_id": candidate["region_id"],
            "column_ordinal": candidate["lane_index"],
            "peer_cell_id": peer["cell_id"],
            "peer_evidence_id": peer["evidence"]["evidence_id"],
            "peer_overlay_evidence_id": peer["overlay_evidence_id"],
            "peer_packet_id": peer["document_packet_id"],
            "peer_raw_classification": peer["raw_classification"],
            "peer_region_id": peer["region_id"],
            "resolved_period": candidate["resolved_period"],
            "role": candidate["role"],
            "source_population_role": candidate["source_population_role"],
        }
        if any(pair[field] != observed for field, observed in joins.items()):
            raise _error("loan-currency bounded dash pair/replay join drifted")
        if (
            peer["role"] != candidate["role"]
            or peer["source_population_role"] != candidate["source_population_role"]
            or peer["source_population_surface"] != candidate["source_population_surface"]
            or peer["lane_index"] != candidate["lane_index"]
            or peer["resolved_period"] != candidate["resolved_period"]
            or source_role != candidate["role"]
            or source_cell["lane_index"] != candidate["lane_index"]
            or source_cell["page_sequence"] != candidate["page_sequence"]
            or candidate["resolved_period"] != _source_period(source, candidate["lane_index"])
            or _parse(source_cell["ppocrv6_surface"]) is not None
        ):
            raise _error("loan-currency bounded dash candidate does not bind source/peer")
        candidate_crop_sha = _digest(
            candidate["evidence"]["crop_ref"]["sha256"],
            "loan-currency bounded candidate crop",
        )
        peer_crop_sha = _digest(
            peer["evidence"]["crop_ref"]["sha256"], "loan-currency bounded peer crop"
        )
        if (
            source_cell["crop_sha256"] is not None
            and source_cell["crop_sha256"] != candidate_crop_sha
        ):
            raise _error("loan-currency bounded dash candidate/source crop drifted")
        evidence_ref = {
            "candidate_crop_sha256": candidate_crop_sha,
            "classification": candidate["raw_classification"],
            "crop_sha256": candidate_crop_sha,
            "evidence_id": candidate["evidence"]["evidence_id"],
            "kind": "BOUNDED_PAIRED_HIGH_FILL_DASH_EVIDENCE",
            "pair_binding": pair,
            "peer_crop_sha256": peer_crop_sha,
            "region_id": candidate["region_id"],
        }
        result[candidate_id] = {"evidence_ref": evidence_ref}
    return result


def _resolved_cell(cell: Mapping[str, Any], dash: Mapping[str, Any] | None) -> dict[str, Any]:
    primary_value = _parse(cell["ppocrv6_surface"])
    viet_value = _parse(cell["vietocr_surface"])
    if dash is not None:
        paired = (
            dash.get("evidence_ref", {}).get("kind") == "BOUNDED_PAIRED_HIGH_FILL_DASH_EVIDENCE"
        )
        selected_surface = "BOUNDED_PAIRED_DASH_MARK" if paired else "VISIBLE_DASH"
        selected_value = 0
        mode = (
            "BOUNDED_PAIRED_HIGH_FILL_DASH_PIXEL_EVIDENCE_ZERO"
            if paired
            else "TYPED_VISIBLE_DASH_PIXEL_EVIDENCE_ZERO"
        )
        evidence_ref = canonical_clone_v1(dash["evidence_ref"])
    elif primary_value is not None:
        selected_surface = cell["ppocrv6_surface"]
        selected_value = primary_value
        mode = (
            "PPOCRV6_PRIMARY_VIETOCR_CORROBORATED"
            if viet_value == primary_value
            else "PPOCRV6_PRIMARY_RAW_VIETOCR_RETAINED"
        )
        evidence_ref = None
    else:
        selected_surface = None
        selected_value = None
        mode = "UNRESOLVED_NO_PRIMARY_OR_TYPED_DASH_EVIDENCE"
        evidence_ref = None
    return {
        **canonical_clone_v1(cell),
        "evidence_ref": evidence_ref,
        "ppocrv6_parsed_value": primary_value,
        "selected_surface": selected_surface,
        "selected_value": selected_value,
        "selection_mode": mode,
        "status": "RESOLVED_OBSERVED_VALUE" if selected_value is not None else "UNRESOLVED",
        "vietocr_parsed_value": viet_value,
    }


def _resolved_row(row: Mapping[str, Any], dashes: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "cells": [_resolved_cell(cell, dashes.get(cell["cell_id"])) for cell in row["cells"]],
        "label_surface": row["label_surface"],
        "role": row["role"],
    }


def _cell(row: Mapping[str, Any], lane_index: int) -> Mapping[str, Any]:
    return row["cells"][lane_index]


def _check(
    components: Sequence[tuple[str, Mapping[str, Any]]],
    target: tuple[str, Mapping[str, Any]],
    *,
    equation_id: str,
    lane_index: int,
) -> dict[str, Any]:
    observed = all(cell["selected_value"] is not None for _role, cell in (*components, target))
    component_values = [cell["selected_value"] for _role, cell in components]
    target_value = target[1]["selected_value"]
    if observed:
        computed = sum(component_values)
        residual = computed - target_value
        status = _ACCEPTED_CHECK_STATUS if residual == 0 else "VETOED_OBSERVED_EQUATION"
    else:
        component_values = []
        computed = None
        residual = None
        target_value = None
        status = "UNRESOLVED_MISSING_OBSERVED_VALUE"
    return {
        "component_cell_ids": [cell["cell_id"] for _role, cell in components],
        "component_roles": [role for role, _cell_value in components],
        "component_values": component_values,
        "computed_value": computed,
        "equation_id": equation_id,
        "equation_tolerance": 0,
        "lane_index": lane_index,
        "lane_type": "MONEY",
        "required_for_acceptance": True,
        "residual": residual,
        "status": status,
        "target_cell_id": target[1]["cell_id"],
        "target_role": target[0],
        "target_value": target_value,
    }


def _accounting_checks(
    mapped_rows: Sequence[Mapping[str, Any]],
    core_total: Mapping[str, Any],
    additional: Mapping[str, Any] | None,
    grand_total: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    checks = []
    for lane in range(2):
        checks.append(
            _check(
                [(row["role"], _cell(row, lane)) for row in mapped_rows],
                (core_total["role"], _cell(core_total, lane)),
                equation_id=f"MAPPED_CURRENCY_ROWS_EQUAL_CORE_TOTAL_LANE_{lane}",
                lane_index=lane,
            )
        )
        if additional is not None:
            checks.extend(
                [
                    _check(
                        [(row["role"], _cell(row, lane)) for row in additional["breakdown_rows"]],
                        (additional["parent"]["role"], _cell(additional["parent"], lane)),
                        equation_id=f"DEFERRED_LC_BREAKDOWN_EQUAL_PARENT_LANE_{lane}",
                        lane_index=lane,
                    ),
                    _check(
                        [
                            (core_total["role"], _cell(core_total, lane)),
                            (additional["parent"]["role"], _cell(additional["parent"], lane)),
                        ],
                        (grand_total["role"], _cell(grand_total, lane)),
                        equation_id=f"CORE_TOTAL_PLUS_DEFERRED_LC_EQUAL_GRAND_TOTAL_LANE_{lane}",
                        lane_index=lane,
                    ),
                ]
            )
    return checks


def _resolve_source_population(
    source: Mapping[str, Any], dashes: Mapping[str, Any]
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
    dict[str, Any] | None,
    dict[str, Any] | None,
]:
    mapped_rows = [_resolved_row(row, dashes) for row in source["mapped_rows"]]
    core_total = _resolved_row(source["core_total"], dashes)
    additional = None
    grand_total = None
    if source["additional_population"] is not None:
        additional = {
            "breakdown_rows": [
                _resolved_row(row, dashes)
                for row in source["additional_population"]["breakdown_rows"]
            ],
            "parent": _resolved_row(source["additional_population"]["parent"], dashes),
        }
        grand_total = _resolved_row(source["grand_total"], dashes)
    return mapped_rows, core_total, additional, grand_total


def _resolved_cells(
    mapped_rows: Sequence[Mapping[str, Any]],
    core_total: Mapping[str, Any],
    additional: Mapping[str, Any] | None,
    grand_total: Mapping[str, Any] | None,
) -> list[Mapping[str, Any]]:
    rows = [*mapped_rows, core_total]
    if additional is not None:
        rows.extend([additional["parent"], *additional["breakdown_rows"], grand_total])
    return [cell for row in rows for cell in row["cells"]]


def _metrics(
    mapped_rows: Sequence[Mapping[str, Any]],
    core_total: Mapping[str, Any],
    additional: Mapping[str, Any] | None,
    grand_total: Mapping[str, Any] | None,
    checks: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    cells = _resolved_cells(mapped_rows, core_total, additional, grand_total)
    return {
        "independent_observed_equation_count": sum(
            check["status"] == _ACCEPTED_CHECK_STATUS for check in checks
        ),
        "mapped_money_cell_count": len(mapped_rows) * 2,
        "bounded_paired_dash_zero_cell_count": sum(
            cell["selection_mode"] == "BOUNDED_PAIRED_HIGH_FILL_DASH_PIXEL_EVIDENCE_ZERO"
            for cell in cells
        ),
        "direct_visible_dash_zero_cell_count": sum(
            cell["selection_mode"] == "TYPED_VISIBLE_DASH_PIXEL_EVIDENCE_ZERO" for cell in cells
        ),
        "ppocrv6_vietocr_raw_surface_disagreement_count": sum(
            cell["ppocrv6_surface"] is not None
            and cell["vietocr_surface"] is not None
            and cell["ppocrv6_surface"] != cell["vietocr_surface"]
            for cell in cells
        ),
        "ppocrv6_vietocr_numeric_disagreement_count": sum(
            cell["ppocrv6_parsed_value"] is not None
            and cell["vietocr_parsed_value"] is not None
            and cell["ppocrv6_parsed_value"] != cell["vietocr_parsed_value"]
            for cell in cells
        ),
        "source_control_money_cell_count": 2 + (2 if grand_total is not None else 0),
        "source_control_row_count": 1 + (1 if grand_total is not None else 0),
        "source_only_additional_money_cell_count": 0 if additional is None else 6,
        "source_only_additional_row_count": 0 if additional is None else 3,
        "unresolved_observed_cell_count": sum(cell["selected_value"] is None for cell in cells),
        "visible_dash_zero_cell_count": sum(
            cell["selection_mode"]
            in {
                "TYPED_VISIBLE_DASH_PIXEL_EVIDENCE_ZERO",
                "BOUNDED_PAIRED_HIGH_FILL_DASH_PIXEL_EVIDENCE_ZERO",
            }
            for cell in cells
        ),
    }


def _unresolved_reasons(checks: Sequence[Mapping[str, Any]]) -> list[str]:
    return [
        f"REQUIRED_ACCOUNTING_CHECK_FAILED:{check['equation_id']}"
        for check in checks
        if check["status"] != _ACCEPTED_CHECK_STATUS
    ]


def _raw_cell(cell: Mapping[str, Any]) -> dict[str, Any]:
    return {field: canonical_clone_v1(cell[field]) for field in _INPUT_CELL_FIELDS}


def _raw_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "cells": [_raw_cell(cell) for cell in row["cells"]],
        "label_surface": row["label_surface"],
        "role": row["role"],
    }


def _source_from_result(value: Mapping[str, Any]) -> dict[str, Any]:
    additional = value["additional_population"]
    return {
        "additional_population": (
            None
            if additional is None
            else {
                "breakdown_rows": [_raw_row(row) for row in additional["breakdown_rows"]],
                "parent": _raw_row(additional["parent"]),
            }
        ),
        "core_total": _raw_row(value["core_total"]),
        "family_id": FAMILY_ID,
        "format_version": INPUT_FORMAT_VERSION,
        "grand_total": None if value["grand_total"] is None else _raw_row(value["grand_total"]),
        "lane_types": canonical_clone_v1(value["lane_types"]),
        "mapped_rows": [_raw_row(row) for row in value["mapped_rows"]],
        "period_axis": canonical_clone_v1(value["period_axis"]),
        "source_id": value["source_id"],
        "unit_context": canonical_clone_v1(value["unit_context"]),
    }


def _validate_pair_evidence_ref(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _PAIR_EVIDENCE_REF_FIELDS:
        raise _error("loan-currency bounded pair evidence reference fields drifted")
    if value["kind"] != "BOUNDED_PAIRED_HIGH_FILL_DASH_EVIDENCE":
        raise _error("loan-currency bounded pair evidence kind drifted")
    pair = _pair_binding(value["pair_binding"])
    for field in ("candidate_crop_sha256", "crop_sha256", "peer_crop_sha256"):
        _digest(value[field], f"loan-currency bounded pair {field}")
    _dash_evidence_identifier(value["evidence_id"], "loan-currency bounded pair evidence")
    _string(value["region_id"], "loan-currency bounded pair region")
    if (
        value["candidate_crop_sha256"] != value["crop_sha256"]
        or value["classification"] != pair["candidate_raw_classification"]
        or value["evidence_id"] != pair["candidate_evidence_id"]
        or value["region_id"] != pair["candidate_region_id"]
    ):
        raise _error("loan-currency bounded pair evidence join drifted")
    return canonical_clone_v1(value)


def _validate_resolved_cell(value: Any, lane_index: int) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _INPUT_CELL_FIELDS | _RESOLUTION_CELL_FIELDS:
        raise _error("loan-currency resolved cell fields drifted")
    raw = _input_cell(_raw_cell(value), lane_index)
    primary = _parse(raw["ppocrv6_surface"])
    viet = _parse(raw["vietocr_surface"])
    evidence = value["evidence_ref"]
    if evidence is None:
        expected = _resolved_cell(raw, None)
    else:
        if type(evidence) is not dict:
            raise _error("loan-currency resolved dash reference drifted")
        if evidence.get("kind") == "BOUNDED_PAIRED_HIGH_FILL_DASH_EVIDENCE":
            evidence = _validate_pair_evidence_ref(evidence)
        else:
            fields = {"classification", "crop_sha256", "evidence_id", "kind", "region_id"}
            if (
                type(evidence) is not dict
                or set(evidence) != fields
                or evidence["classification"] != "VISIBLE_HORIZONTAL_DASH_GLYPH"
                or evidence["kind"] != "DIRECT_TYPED_VISIBLE_DASH_EVIDENCE"
            ):
                raise _error("loan-currency resolved dash reference drifted")
            _dash_evidence_identifier(
                evidence["evidence_id"], "loan-currency resolved dash evidence"
            )
            _digest(evidence["crop_sha256"], "loan-currency resolved dash crop")
            _string(evidence["region_id"], "loan-currency resolved dash region")
        if _parse(raw["ppocrv6_surface"]) is not None:
            raise _error("loan-currency resolved dash overlays a primary numeric value")
        if raw["crop_sha256"] is not None and raw["crop_sha256"] != evidence["crop_sha256"]:
            raise _error("loan-currency resolved dash/source crop binding drifted")
        expected = _resolved_cell(raw, {"evidence_ref": evidence})
    if primary != value["ppocrv6_parsed_value"] or viet != value["vietocr_parsed_value"]:
        raise _error("loan-currency resolved raw parse drifted")
    if not same_typed_json_v1(value, expected):
        raise _error("loan-currency resolved selection drifted")
    return canonical_clone_v1(value)


def _validate_resolved_row(value: Any, role: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {"cells", "label_surface", "role"}:
        raise _error("loan-currency resolved row fields drifted")
    if value["role"] != role or type(value["cells"]) is not list or len(value["cells"]) != 2:
        raise _error("loan-currency resolved row binding drifted")
    _string(value["label_surface"], "loan-currency resolved row label")
    return {
        "cells": [_validate_resolved_cell(cell, lane) for lane, cell in enumerate(value["cells"])],
        "label_surface": value["label_surface"],
        "role": role,
    }


def _validate_result(value: Any) -> dict[str, Any]:
    fields = {
        "accounting_checks",
        "additional_population",
        "authority",
        "bounded_dash_pair_evidence_refs",
        "claim_boundary",
        "core_total",
        "family_id",
        "format_version",
        "grand_total",
        "input_id",
        "lane_types",
        "mapped_rows",
        "metrics",
        "period_axis",
        "result_id",
        "source_id",
        "status",
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
        or type(value["lane_types"]) is not list
        or tuple(value["lane_types"]) != _LANE_TYPES
        or type(value["period_axis"]) is not dict
        or type(value["unit_context"]) is not dict
    ):
        raise _error("loan-currency numeric result contract drifted")
    _string(value["source_id"], "loan-currency result source")
    rows = value["mapped_rows"]
    if type(rows) is not list or len(rows) != 2:
        raise _error("loan-currency result mapped row population drifted")
    mapped_rows = [
        _validate_resolved_row(row, role) for row, role in zip(rows, _MAPPED_ROLES, strict=True)
    ]
    core_total = _validate_resolved_row(value["core_total"], "CORE_TOTAL")
    additional = value["additional_population"]
    if additional is None:
        typed_additional = None
        if value["grand_total"] is not None:
            raise _error("loan-currency result has a grand total without additional population")
        grand_total = None
    else:
        if type(additional) is not dict or set(additional) != {"breakdown_rows", "parent"}:
            raise _error("loan-currency result additional population fields drifted")
        breakdown = additional["breakdown_rows"]
        if type(breakdown) is not list or len(breakdown) != 2:
            raise _error("loan-currency result additional breakdown population drifted")
        typed_additional = {
            "breakdown_rows": [
                _validate_resolved_row(row, role)
                for row, role in zip(breakdown, _ADDITIONAL_BREAKDOWN_ROLES, strict=True)
            ],
            "parent": _validate_resolved_row(additional["parent"], _ADDITIONAL_PARENT_ROLE),
        }
        if value["grand_total"] is None:
            raise _error("loan-currency result additional population lacks grand total")
        grand_total = _validate_resolved_row(value["grand_total"], "GRAND_TOTAL")

    pair_refs_value = value["bounded_dash_pair_evidence_refs"]
    if type(pair_refs_value) is not list:
        raise _error("loan-currency bounded pair evidence reference axis drifted")
    pair_refs = [_validate_pair_evidence_ref(item) for item in pair_refs_value]
    pair_ids = [item["pair_binding"]["pair_binding_id"] for item in pair_refs]
    if pair_ids != sorted(pair_ids) or len(pair_ids) != len(set(pair_ids)):
        raise _error("loan-currency bounded pair evidence references repeat or reorder")
    normalized = {
        **canonical_clone_v1(value),
        "additional_population": typed_additional,
        "bounded_dash_pair_evidence_refs": pair_refs,
        "core_total": core_total,
        "grand_total": grand_total,
        "mapped_rows": mapped_rows,
    }
    source = _validate_source(_source_from_result(normalized))
    indexed = {cell["cell_id"]: (role, cell) for role, cell in _all_input_cells(source)}
    actual_cells = _resolved_cells(mapped_rows, core_total, typed_additional, grand_total)
    direct_dashes = {
        cell["cell_id"]: {"evidence_ref": canonical_clone_v1(cell["evidence_ref"])}
        for cell in actual_cells
        if type(cell["evidence_ref"]) is dict
        and cell["evidence_ref"].get("kind") == "DIRECT_TYPED_VISIBLE_DASH_EVIDENCE"
    }
    pair_dashes = {}
    for pair_ref in pair_refs:
        pair = pair_ref["pair_binding"]
        cell_id = pair["candidate_cell_id"]
        source_binding = indexed.get(cell_id)
        if (
            source_binding is None
            or source_binding[0] != pair["role"]
            or source_binding[1]["lane_index"] != pair["column_ordinal"]
            or pair["resolved_period"] != _source_period(source, pair["column_ordinal"])
            or _parse(source_binding[1]["ppocrv6_surface"]) is not None
            or cell_id in direct_dashes
            or cell_id in pair_dashes
        ):
            raise _error("loan-currency bounded pair reference does not bind raw source")
        pair_dashes[cell_id] = {"evidence_ref": canonical_clone_v1(pair_ref)}
    expected_population = _resolve_source_population(source, {**direct_dashes, **pair_dashes})
    if not all(
        same_typed_json_v1(observed, expected)
        for observed, expected in zip(
            (mapped_rows, core_total, typed_additional, grand_total),
            expected_population,
            strict=True,
        )
    ):
        raise _error("loan-currency bounded pair pixel selection drifted")
    expected_checks = _accounting_checks(mapped_rows, core_total, typed_additional, grand_total)
    if not same_typed_json_v1(value["accounting_checks"], expected_checks):
        raise _error("loan-currency accounting checks drifted")
    expected_metrics = _metrics(
        mapped_rows, core_total, typed_additional, grand_total, expected_checks
    )
    if not same_typed_json_v1(value["metrics"], expected_metrics):
        raise _error("loan-currency numeric metrics drifted")
    expected_unresolved = _unresolved_reasons(expected_checks)
    expected_status = (
        "EXACT_OBSERVED_NUMERIC_RECONCILIATION" if not expected_unresolved else "UNRESOLVED"
    )
    if value["unresolved_reasons"] != expected_unresolved or value["status"] != expected_status:
        raise _error("loan-currency numeric acceptance status drifted")
    evidence_ids = value["visible_dash_evidence_ids"]
    if (
        type(evidence_ids) is not list
        or evidence_ids != sorted(evidence_ids)
        or any(
            _dash_evidence_identifier(identifier, "loan-currency visible-dash evidence")
            != identifier
            for identifier in evidence_ids
        )
    ):
        raise _error("loan-currency visible-dash evidence identity list drifted")
    resolved_cells = _resolved_cells(mapped_rows, core_total, typed_additional, grand_total)
    referenced_ids = sorted(
        cell["evidence_ref"]["evidence_id"]
        for cell in resolved_cells
        if cell["evidence_ref"] is not None
    )
    if referenced_ids != evidence_ids:
        raise _error("loan-currency visible-dash evidence consumption drifted")
    direct_ids = sorted(item["evidence_ref"]["evidence_id"] for item in direct_dashes.values())
    expected_input_id = "lcnrv1:input:" + canonical_json_sha256_v1(
        {
            "bounded_dash_pair_evidence_refs": pair_refs,
            "direct_visible_dash_evidence_ids": direct_ids,
            "source": source,
        }
    )
    if value["input_id"] != expected_input_id:
        raise _error("loan-currency numeric input identity drifted")
    material = canonical_clone_v1(normalized)
    identity = material.pop("result_id")
    if identity != "lcnrv1:result:" + canonical_json_sha256_v1(material):
        raise _error("loan-currency numeric result identity drifted")
    return canonical_clone_v1(normalized)


def build_loan_currency_numeric_reconciliation_v1(
    source: Any,
    *,
    bounded_dash_peer_evidence: Sequence[Any] = (),
    visible_dash_evidence: Sequence[Any] = (),
) -> dict[str, Any]:
    """Reconcile one structurally selected currency table without inference."""

    if isinstance(visible_dash_evidence, (str, bytes, bytearray)) or not isinstance(
        visible_dash_evidence, Sequence
    ):
        raise _error("loan-currency visible-dash overlays must be one sequence")
    if isinstance(bounded_dash_peer_evidence, (str, bytes, bytearray)) or not isinstance(
        bounded_dash_peer_evidence, Sequence
    ):
        raise _error("loan-currency bounded dash peer inputs must be one sequence")
    typed = _validate_source(source)
    indexed = {cell["cell_id"]: (role, cell) for role, cell in _all_input_cells(typed)}
    direct_dashes = _dash_overlays(visible_dash_evidence, indexed)
    pair_dashes = _bounded_dash_overlays(bounded_dash_peer_evidence, indexed, typed)
    if set(direct_dashes) & set(pair_dashes):
        raise _error("loan-currency direct and bounded dash evidence overlap")
    dashes = {**direct_dashes, **pair_dashes}
    mapped_rows, core_total, additional, grand_total = _resolve_source_population(typed, dashes)
    checks = _accounting_checks(mapped_rows, core_total, additional, grand_total)
    unresolved = _unresolved_reasons(checks)
    evidence_ids = sorted(overlay["evidence_ref"]["evidence_id"] for overlay in dashes.values())
    pair_refs = sorted(
        (canonical_clone_v1(item["evidence_ref"]) for item in pair_dashes.values()),
        key=lambda item: item["pair_binding"]["pair_binding_id"],
    )
    direct_ids = sorted(item["evidence_id"] for item in direct_dashes.values())
    input_id = "lcnrv1:input:" + canonical_json_sha256_v1(
        {
            "bounded_dash_pair_evidence_refs": pair_refs,
            "direct_visible_dash_evidence_ids": direct_ids,
            "source": typed,
        }
    )
    material = {
        "accounting_checks": checks,
        "additional_population": additional,
        "authority": canonical_clone_v1(_AUTHORITY),
        "bounded_dash_pair_evidence_refs": pair_refs,
        "claim_boundary": CLAIM_BOUNDARY,
        "core_total": core_total,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "grand_total": grand_total,
        "input_id": input_id,
        "lane_types": canonical_clone_v1(typed["lane_types"]),
        "mapped_rows": mapped_rows,
        "metrics": _metrics(mapped_rows, core_total, additional, grand_total, checks),
        "period_axis": canonical_clone_v1(typed["period_axis"]),
        "source_id": typed["source_id"],
        "status": "EXACT_OBSERVED_NUMERIC_RECONCILIATION" if not unresolved else "UNRESOLVED",
        "unit_context": canonical_clone_v1(typed["unit_context"]),
        "unresolved_reasons": unresolved,
        "visible_dash_evidence_ids": evidence_ids,
    }
    return _validate_result(
        {**material, "result_id": "lcnrv1:result:" + canonical_json_sha256_v1(material)}
    )


def validate_loan_currency_numeric_reconciliation_v1(value: Any) -> dict[str, Any]:
    """Validate one content-addressed, semantically closed result."""

    return _validate_result(value)


def validate_loan_currency_numeric_reconciliation_replay_v1(
    value: Any,
    source: Any,
    *,
    bounded_dash_peer_evidence: Sequence[Any] = (),
    visible_dash_evidence: Sequence[Any] = (),
) -> dict[str, Any]:
    """Rebuild from the same raw evidence and require exact typed equality."""

    persisted = _validate_result(value)
    rebuilt = build_loan_currency_numeric_reconciliation_v1(
        source,
        bounded_dash_peer_evidence=bounded_dash_peer_evidence,
        visible_dash_evidence=visible_dash_evidence,
    )
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("loan-currency numeric reconciliation does not replay exactly")
    return rebuilt
