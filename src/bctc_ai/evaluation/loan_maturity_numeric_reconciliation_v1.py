"""Graph-neutral numeric reconciliation for loan-maturity tables.

The structural graph supplies already-bound rows and typed lanes.  This layer
does not discover a table and does not map schema identities.  It preserves
both OCR surfaces, permits only authenticated visible-dash zero evidence or a
two-request E-0170 hosted challenger to alter PP-OCRv6's primary reading, and
then uses printed accounting controls only as corroboration or veto.  Missing
values are never back-solved.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

from bctc_ai.evaluation.accounting_table_axes_v1 import money_integer_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "INPUT_FORMAT_VERSION",
    "LoanMaturityNumericReconciliationV1Error",
    "build_loan_maturity_numeric_reconciliation_v1",
    "validate_loan_maturity_numeric_reconciliation_replay_v1",
    "validate_loan_maturity_numeric_reconciliation_v1",
]


FORMAT_VERSION = "LOAN_MATURITY_NUMERIC_RECONCILIATION_V1"
INPUT_FORMAT_VERSION = "LOAN_MATURITY_NUMERIC_RECONCILIATION_INPUT_V1"
FAMILY_ID = "LOAN_MATURITY_BUCKETS"
CLAIM_BOUNDARY = (
    "BOUND_PPOCRV6_VIETOCR_TYPED_VALUE_SURFACES_E0170_TWO_STATELESS_HOSTED_"
    "CHALLENGER_AND_VISIBLE_DASH_OVERLAYS_EXACT_PRINTED_ACCOUNTING_"
    "CORROBORATION_OR_VETO_ONLY_NO_BACKSOLVE_SCHEMA_MAPPING_TABLE_DISCOVERY_"
    "CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "accounting_can_infer_or_backsolve_value": False,
    "accounting_is_corroboration_or_veto_only": True,
    "blank_or_missing_cell_is_zero": False,
    "e0170_challenger_is_sole_numeric_authority": False,
    "mapping_authority": False,
    "parent_or_source_total_emitted_as_mapping": False,
    "ppocrv6_primary_surface_retained": True,
    "schema_authority": False,
    "source_rows_and_controls_retained_without_double_count": True,
    "vietocr_surface_retained": True,
    "visible_dash_requires_typed_pixel_evidence": True,
}
_CORE_ROLES = ("SHORT_TERM", "MEDIUM_TERM", "LONG_TERM")
_LANES = (("MONEY", "MONEY"), ("MONEY", "PERCENT", "MONEY", "PERCENT"))
_SHA = frozenset("0123456789abcdef")
_E0170_FORMAT = "FAMILY_FIRST_LOAN_MATURITY_HOSTED_GEMMA4_NUMERIC_CHALLENGER_EVALUATION_V1"
_DASH_FORMAT = "FAMILY_FIRST_VISIBLE_DASH_GLYPH_EVIDENCE_V1"
_ADDITIONAL_EVIDENCE_FORMAT = "LOAN_MATURITY_ADDITIONAL_POPULATION_EVIDENCE_V1"
_ADDITIONAL_EVIDENCE_CLAIM_BOUNDARY = (
    "UNIQUE_MATURITY_SOURCE_ONLY_PARENT_SHORT_AND_GRAND_ROWS_AUTHENTICATED_"
    "PIXEL_DASH_OR_ONE_PAIRED_CENTERED_HIGH_FILL_SHORT_MARK_EVIDENCE_PLUS_"
    "EXACT_ACCOUNTING_VETO_ONLY_NO_BANK_FILENAME_PAGE_PERIOD_NOTE_SCHEMA_MAPPING_"
    "CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
_ADDITIONAL_EVIDENCE_AUTHORITY = {
    "accounting_equation_used_as_final_corroboration_and_veto_only": True,
    "bank_filename_note_page_or_period_routing_authority": False,
    "blank_or_detector_omission_means_zero": False,
    "mapping_authority": False,
    "numeric_digits_authority": False,
    "one_centered_high_fill_short_mark_requires_related_clear_dash_peer": True,
    "paired_short_mark_requires_both_observed_equations_exact": True,
    "schema_authority": False,
    "visible_authenticated_pixel_dash_may_normalize_to_zero": True,
}


class LoanMaturityNumericReconciliationV1Error(ValueError):
    """The bound source, typed overlay, accounting closure, or replay drifted."""


def _error(message: str) -> LoanMaturityNumericReconciliationV1Error:
    return LoanMaturityNumericReconciliationV1Error(message)


def _digest(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 64 or any(char not in _SHA for char in value):
        raise _error(f"{label} digest drifted")
    return value


def _string(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        raise _error(f"{label} string drifted")
    return value


def _surface(value: Any, label: str) -> str | None:
    if value is not None and type(value) is not str:
        raise _error(f"{label} surface drifted")
    return value


def _percent(value: str) -> Decimal | None:
    compact = value.strip().replace(" ", "").rstrip("%").replace(",", ".")
    if not compact:
        return None
    try:
        parsed = Decimal(compact)
    except InvalidOperation:
        return None
    return parsed if parsed.is_finite() else None


def _percent_string(value: Decimal) -> str:
    rendered = format(value.normalize(), "f")
    return "0" if rendered in {"-0", ""} else rendered


def _parse(surface: str | None, lane_type: str) -> int | str | None:
    if surface is None:
        return None
    if lane_type == "MONEY":
        return money_integer_v1(surface)
    parsed = _percent(surface)
    return None if parsed is None else _percent_string(parsed)


def _decimal(value: int | str) -> Decimal:
    return Decimal(value)


def _input_cell(value: Any, lane_index: int, lane_type: str) -> dict[str, Any]:
    fields = {
        "bbox",
        "cell_id",
        "crop_sha256",
        "lane_index",
        "lane_type",
        "ppocrv6_score",
        "ppocrv6_surface",
        "sample_id",
        "source_line_index",
        "vietocr_surface",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error("maturity numeric input cell fields drifted")
    if value["lane_index"] != lane_index or value["lane_type"] != lane_type:
        raise _error("maturity numeric cell typed-lane binding drifted")
    _string(value["cell_id"], "maturity cell")
    bbox = value["bbox"]
    if bbox is not None and (
        type(bbox) is not list
        or len(bbox) != 4
        or any(type(item) is not int or item < 0 for item in bbox)
        or not (bbox[0] < bbox[2] and bbox[1] < bbox[3])
    ):
        raise _error("maturity numeric cell bbox drifted")
    line = value["source_line_index"]
    if line is not None and (type(line) is not int or line < 0):
        raise _error("maturity numeric source-line binding drifted")
    sample = value["sample_id"]
    if sample is not None and (type(sample) is not str or not sample):
        raise _error("maturity numeric sample binding drifted")
    crop = value["crop_sha256"]
    if crop is not None:
        _digest(crop, "maturity numeric crop")
    score = value["ppocrv6_score"]
    if score is not None and (type(score) is not float or not 0 <= score <= 1):
        raise _error("maturity PP-OCRv6 score drifted")
    _surface(value["ppocrv6_surface"], "PP-OCRv6")
    _surface(value["vietocr_surface"], "VietOCR")
    if bbox is None and line is not None:
        raise _error("maturity source line cannot exist without bbox")
    return canonical_clone_v1(value)


def _input_row(value: Any, role: str, lane_types: Sequence[str]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {"cells", "label_surface", "role"}:
        raise _error("maturity numeric input row fields drifted")
    if value["role"] != role:
        raise _error("maturity numeric input row role drifted")
    _string(value["label_surface"], "maturity row label")
    if type(value["cells"]) is not list or len(value["cells"]) != len(lane_types):
        raise _error("maturity numeric row lane count drifted")
    return {
        "cells": [
            _input_cell(cell, index, lane_types[index]) for index, cell in enumerate(value["cells"])
        ],
        "label_surface": value["label_surface"],
        "role": role,
    }


def _input_control(value: Any, role: str, lane_types: Sequence[str]) -> dict[str, Any]:
    return _input_row(value, role, lane_types)


def _validate_source(value: Any) -> dict[str, Any]:
    fields = {
        "additional_population",
        "core_rows",
        "core_subtotal",
        "family_id",
        "format_version",
        "grand_total",
        "lane_types",
        "margin",
        "period_axis",
        "source_id",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error("maturity numeric reconciliation input fields drifted")
    if value["format_version"] != INPUT_FORMAT_VERSION or value["family_id"] != FAMILY_ID:
        raise _error("maturity numeric input identity drifted")
    _string(value["source_id"], "maturity numeric source")
    if type(value["lane_types"]) is not list or tuple(value["lane_types"]) not in _LANES:
        raise _error("maturity numeric lane layout is unsupported")
    lane_types = list(value["lane_types"])
    if type(value["period_axis"]) is not dict:
        raise _error("maturity period axis must remain one typed object")
    rows = value["core_rows"]
    if type(rows) is not list or [row.get("role") for row in rows if type(row) is dict] != list(
        _CORE_ROLES
    ):
        raise _error("maturity core row population/order drifted")
    core_rows = [
        _input_row(row, role, lane_types) for row, role in zip(rows, _CORE_ROLES, strict=True)
    ]
    margin = (
        None
        if value["margin"] is None
        else _input_row(value["margin"], "MARGIN_AND_SECURITIES_ADVANCE", lane_types)
    )
    subtotal = (
        None
        if value["core_subtotal"] is None
        else _input_control(value["core_subtotal"], "CORE_SUBTOTAL", lane_types)
    )
    grand = (
        None
        if value["grand_total"] is None
        else _input_control(value["grand_total"], "GRAND_TOTAL", lane_types)
    )
    additional = value["additional_population"]
    if additional is not None:
        if type(additional) is not dict or set(additional) != {
            "breakdown_rows",
            "parent",
        }:
            raise _error("maturity additional population fields drifted")
        parent = _input_control(additional["parent"], "ADDITIONAL_POPULATION_PARENT", lane_types)
        breakdown = additional["breakdown_rows"]
        if type(breakdown) is not list or not breakdown:
            raise _error("maturity additional population breakdown is empty")
        seen_roles = set()
        typed_breakdown = []
        for row in breakdown:
            role = row.get("role") if type(row) is dict else None
            if type(role) is not str or not role.startswith("ADDITIONAL_") or role in seen_roles:
                raise _error("maturity additional population role drifted")
            seen_roles.add(role)
            typed_breakdown.append(_input_row(row, role, lane_types))
        additional = {"breakdown_rows": typed_breakdown, "parent": parent}
    if margin is not None and additional is not None:
        raise _error("combined margin and additional-population presentation is unsupported")
    if len(lane_types) == 4 and (margin is not None or additional is not None):
        raise _error("four-lane margin/additional presentation is outside observed contract")
    if margin is None and additional is None and (subtotal is None or grand is not None):
        raise _error("core-only presentation requires one core subtotal and no grand total")
    if margin is not None and grand is None:
        raise _error("margin presentation requires one printed grand total")
    if additional is not None and (subtotal is None or grand is None):
        raise _error("additional population requires core subtotal and grand total")
    result = {
        **canonical_clone_v1(value),
        "additional_population": additional,
        "core_rows": core_rows,
        "core_subtotal": subtotal,
        "grand_total": grand,
        "margin": margin,
    }
    cells = _all_input_cells(result)
    ids = [cell["cell_id"] for _role, cell in cells]
    if len(ids) != len(set(ids)):
        raise _error("maturity numeric cell identities are not unique")
    return result


def _all_input_cells(source: Mapping[str, Any]) -> list[tuple[str, Mapping[str, Any]]]:
    result = [(row["role"], cell) for row in source["core_rows"] for cell in row["cells"]]
    for key in ("margin", "core_subtotal", "grand_total"):
        if source[key] is not None:
            result.extend((source[key]["role"], cell) for cell in source[key]["cells"])
    additional = source["additional_population"]
    if additional is not None:
        result.extend(
            (additional["parent"]["role"], cell) for cell in additional["parent"]["cells"]
        )
        result.extend(
            (row["role"], cell) for row in additional["breakdown_rows"] for cell in row["cells"]
        )
    return result


def _typed_dash_overlays(
    values: Sequence[Any],
    cells: Mapping[str, tuple[str, Mapping[str, Any]]],
    *,
    source_id: str,
) -> dict[str, dict[str, Any]]:
    result = {}
    for bound in values:
        if type(bound) is dict and bound.get("format_version") == _ADDITIONAL_EVIDENCE_FORMAT:
            wrapper = _additional_population_wrapper_overlays(bound, cells, source_id=source_id)
            if set(result) & set(wrapper):
                raise _error("additional-population dash wrapper overlaps another overlay")
            result.update(wrapper)
            continue
        if type(bound) is not dict or set(bound) != {
            "cell_id",
            "evidence",
            "lane_index",
            "lane_type",
            "role",
        }:
            raise _error("visible-dash binding fields drifted")
        cell_id = _string(bound["cell_id"], "visible-dash cell")
        evidence = bound["evidence"]
        if type(evidence) is not dict or evidence.get("format_version") != _DASH_FORMAT:
            raise _error("visible-dash evidence type drifted")
        material = canonical_clone_v1(evidence)
        identity = material.pop("evidence_id", None)
        if identity != "ffvdgev1:evidence:" + canonical_json_sha256_v1(material):
            raise _error("visible-dash evidence identity drifted")
        crop = evidence.get("crop_ref")
        if (
            evidence.get("classification") != "VISIBLE_HORIZONTAL_DASH_GLYPH"
            or type(evidence.get("normalized_value")) is not int
            or evidence["normalized_value"] != 0
            or type(crop) is not dict
        ):
            raise _error("visible-dash evidence is not one authenticated zero")
        crop_sha = _digest(crop.get("sha256"), "visible-dash crop")
        if cell_id in result or cell_id not in cells:
            raise _error("visible-dash binding is duplicate or unused")
        source_role, source_cell = cells[cell_id]
        if (
            bound["role"] != source_role
            or bound["lane_index"] != source_cell["lane_index"]
            or bound["lane_type"] != source_cell["lane_type"]
            or (source_cell["crop_sha256"] is not None and source_cell["crop_sha256"] != crop_sha)
        ):
            raise _error("visible-dash crop does not bind the source cell")
        result[cell_id] = {
            "crop_sha256": crop_sha,
            "evidence_id": identity,
            "evidence_ref": {
                "classification": "VISIBLE_HORIZONTAL_DASH_GLYPH",
                "crop_sha256": crop_sha,
                "evidence_id": identity,
                "kind": "DIRECT_TYPED_VISIBLE_DASH_EVIDENCE",
            },
        }
    return result


def _dash_artifact_identity(value: Any) -> tuple[str, str]:
    if type(value) is not dict or value.get("format_version") != _DASH_FORMAT:
        raise _error("nested visible-dash evidence type drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("evidence_id", None)
    if identity != "ffvdgev1:evidence:" + canonical_json_sha256_v1(material):
        raise _error("nested visible-dash evidence identity drifted")
    crop = value.get("crop_ref")
    if type(crop) is not dict:
        raise _error("nested visible-dash crop reference drifted")
    return identity, _digest(crop.get("sha256"), "nested visible-dash crop")


def _additional_population_wrapper_overlays(
    value: Mapping[str, Any],
    cells: Mapping[str, tuple[str, Mapping[str, Any]]],
    *,
    source_id: str,
) -> dict[str, dict[str, Any]]:
    fields = {
        "accounting_checks",
        "additional_population",
        "authority",
        "base_result_id",
        "claim_boundary",
        "document_ordinal",
        "evidence",
        "family_id",
        "format_version",
        "page_sequence",
        "render_id",
        "render_ref",
        "result_id",
        "status",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error("additional-population evidence wrapper fields drifted")
    material = canonical_clone_v1(value)
    wrapper_id = material.pop("result_id")
    if wrapper_id != "lmaperv1:result:" + canonical_json_sha256_v1(material):
        raise _error("additional-population evidence wrapper identity drifted")
    if (
        value["status"] != "AUTHENTICATED_PIXEL_DASH_AND_ACCOUNTING_EXACT"
        or value["family_id"] != FAMILY_ID
        or value["base_result_id"] != source_id
        or value["claim_boundary"] != _ADDITIONAL_EVIDENCE_CLAIM_BOUNDARY
        or value["authority"] != _ADDITIONAL_EVIDENCE_AUTHORITY
        or type(value["render_id"]) is not str
        or not value["render_id"]
    ):
        raise _error("additional-population evidence wrapper/source binding drifted")
    checks = value["accounting_checks"]
    if (
        type(checks) is not list
        or len(checks) != 4
        or {(check.get("equation"), check.get("lane_index")) for check in checks}
        != {
            ("ADDITIONAL_PARENT_EQUALS_SHORT_BREAKDOWN", 0),
            ("ADDITIONAL_PARENT_EQUALS_SHORT_BREAKDOWN", 1),
            ("CORE_PLUS_ADDITIONAL_EQUALS_PRINTED_GRAND", 0),
            ("CORE_PLUS_ADDITIONAL_EQUALS_PRINTED_GRAND", 1),
        }
        or any(check.get("status") != "CORROBORATED_EXACT" for check in checks)
    ):
        raise _error("additional-population wrapper equations are not four exact controls")
    evidence = value["evidence"]
    if type(evidence) is not list or not evidence:
        raise _error("additional-population wrapper has no pixel evidence")
    by_region = {}
    normalized = []
    for item in evidence:
        if type(item) is not dict:
            raise _error("additional-population wrapper evidence item drifted")
        role = item.get("role")
        lane = item.get("lane_index")
        region_id = item.get("region_id")
        classification = item.get("classification")
        if (
            role not in {"ADDITIONAL_PARENT", "ADDITIONAL_SHORT_BREAKDOWN"}
            or type(lane) is not int
            or lane not in {0, 1}
            or type(region_id) is not str
            or not region_id
            or region_id in by_region
            or classification
            not in {
                "PAIRED_CENTERED_HIGH_FILL_SHORT_MARK_CANDIDATE",
                "VISIBLE_PIXEL_DASH_ZERO",
            }
        ):
            raise _error("additional-population wrapper evidence binding drifted")
        dash_id, crop_sha = _dash_artifact_identity(item.get("dash_evidence"))
        raw_dash = item["dash_evidence"]
        if classification == "VISIBLE_PIXEL_DASH_ZERO" and (
            raw_dash.get("classification") != "VISIBLE_HORIZONTAL_DASH_GLYPH"
            or raw_dash.get("normalized_value") != 0
        ):
            raise _error("wrapper clear-dash classification drifted")
        if classification == "PAIRED_CENTERED_HIGH_FILL_SHORT_MARK_CANDIDATE" and (
            raw_dash.get("classification") == "VISIBLE_HORIZONTAL_DASH_GLYPH"
            or raw_dash.get("normalized_value") is not None
        ):
            raise _error("wrapper paired-mark raw evidence was silently promoted")
        record = {
            "classification": classification,
            "crop_sha256": crop_sha,
            "dash_evidence_id": dash_id,
            "item": item,
            "lane_index": lane,
            "region_id": region_id,
            "role": role,
        }
        by_region[region_id] = record
        normalized.append(record)
    for record in normalized:
        if record["classification"] != "PAIRED_CENTERED_HIGH_FILL_SHORT_MARK_CANDIDATE":
            continue
        item = record["item"]
        peer = by_region.get(item.get("paired_clear_dash_peer_region_id"))
        expected_peer_role = (
            "ADDITIONAL_SHORT_BREAKDOWN"
            if record["role"] == "ADDITIONAL_PARENT"
            else "ADDITIONAL_PARENT"
        )
        if (
            peer is None
            or peer["classification"] != "VISIBLE_PIXEL_DASH_ZERO"
            or peer["region_id"] == record["region_id"]
            or peer["lane_index"] != record["lane_index"]
            or peer["role"] != expected_peer_role
            or item.get("paired_clear_dash_peer_role") != expected_peer_role
        ):
            raise _error("wrapper paired centered mark lacks its distinct clear-dash peer")
    population = value["additional_population"]
    breakdown = population.get("breakdown") if type(population) is dict else None
    if (
        type(population) is not dict
        or type(population.get("values")) is not list
        or type(breakdown) is not dict
        or type(breakdown.get("values")) is not list
    ):
        raise _error("wrapper selected additional population drifted")
    wrapper_vectors = {
        "ADDITIONAL_PARENT": population["values"],
        "ADDITIONAL_SHORT_BREAKDOWN": breakdown["values"],
    }
    output = {}
    for record in normalized:
        source_role = (
            "ADDITIONAL_POPULATION_PARENT" if record["role"] == "ADDITIONAL_PARENT" else None
        )
        candidates = [
            (cell_id, role, cell)
            for cell_id, (role, cell) in cells.items()
            if cell["lane_index"] == record["lane_index"]
            and (
                role == source_role
                if source_role is not None
                else role.startswith("ADDITIONAL_") and role != "ADDITIONAL_POPULATION_PARENT"
            )
        ]
        if len(candidates) != 1:
            raise _error("wrapper role/lane does not bind one source placeholder")
        cell_id, bound_role, cell = candidates[0]
        selected = wrapper_vectors[record["role"]][record["lane_index"]]
        if (
            cell_id in output
            or cell["ppocrv6_surface"] is not None
            or cell["source_line_index"] is not None
            or type(selected) is not dict
            or selected.get("selected_value") != 0
            or selected.get("lane_index") != record["lane_index"]
            or selected.get("ppocrv6_surface") is not None
            or selected.get("vietocr_transformer_surface") is not None
        ):
            raise _error("wrapper selected zero differs from the raw missing source cell")
        output[cell_id] = {
            "crop_sha256": record["crop_sha256"],
            "evidence_id": wrapper_id,
            "evidence_ref": {
                "bound_role": bound_role,
                "classification": record["classification"],
                "dash_evidence_id": record["dash_evidence_id"],
                "kind": "MATURITY_ADDITIONAL_POPULATION_EVIDENCE_WRAPPER",
                "region_id": record["region_id"],
                "render_id": value["render_id"],
                "wrapper_result_id": wrapper_id,
            },
        }
    return output


def _e0170_observations(
    values: Sequence[Any], cells: Mapping[str, tuple[str, Mapping[str, Any]]]
) -> dict[str, dict[str, Any]]:
    result = {}
    for challenge in values:
        if type(challenge) is not dict or challenge.get("format_version") != _E0170_FORMAT:
            raise _error("E0170 challenger type drifted")
        material = canonical_clone_v1(challenge)
        identity = material.pop("evaluation_id", None)
        if identity != "maturitygemma4v1:evaluation:" + canonical_json_sha256_v1(material):
            raise _error("E0170 challenger identity drifted")
        decision = challenge.get("decision")
        requests = challenge.get("requests")
        if (
            type(decision) is not dict
            or decision.get("fresh_request_count") != 2
            or decision.get("hosted_requests_are_stateless") is not True
            or decision.get("both_hosted_responses_agree_exactly") is not True
            or decision.get("gemma4_may_act_as_sole_numeric_reader") is not False
            or type(requests) is not list
            or len(requests) != 2
        ):
            raise _error("E0170 two-stateless-request decision drifted")
        content_digests = set()
        raw_digests = set()
        for ordinal, request in enumerate(requests, start=1):
            if (
                type(request) is not dict
                or request.get("request_ordinal") != ordinal
                or request.get("fresh_context") is not True
                or request.get("http_status") != 200
            ):
                raise _error("E0170 hosted request provenance drifted")
            content_digests.add(
                _digest(request.get("response_content_ref", {}).get("sha256"), "E0170 content")
            )
            raw_digests.add(
                _digest(request.get("raw_response_ref", {}).get("sha256"), "E0170 raw response")
            )
        if len(content_digests) != 1 or len(raw_digests) != 2:
            raise _error("E0170 consensus/fresh response digests drifted")
        for key in ("target_observation", "total_control_observation"):
            observation = challenge.get(key)
            if type(observation) is not dict:
                raise _error("E0170 observation drifted")
            sample_id = observation.get("sample_id")
            line = observation.get("source_line_index")
            bbox = observation.get("source_bbox_cached_200dpi")
            matches = [
                (cell_id, role, cell)
                for cell_id, (role, cell) in cells.items()
                if (
                    (sample_id is not None and cell["sample_id"] == sample_id)
                    or (
                        sample_id is None
                        and cell["source_line_index"] == line
                        and cell["bbox"] == bbox
                    )
                )
            ]
            if len(matches) != 1:
                raise _error("E0170 observation does not bind exactly one source cell")
            cell_id, role, cell = matches[0]
            selected_surface = observation.get("selected_surface")
            selected_value = observation.get("selected_value")
            observation_role = observation.get("role")
            role_matches = role == observation_role or (
                key == "total_control_observation"
                and role == "CORE_SUBTOTAL"
                and observation_role == "CORE_TOTAL"
            )
            if (
                cell_id in result
                or not role_matches
                or cell["lane_index"] != observation.get("lane_index")
                or cell["lane_type"] != observation.get("lane_type")
                or cell["ppocrv6_surface"] != observation.get("ppocrv6_original_surface")
                or cell["vietocr_surface"] != observation.get("vietocr_transformer_surface")
                or cell["bbox"] != bbox
                or cell["source_line_index"] != line
                or selected_surface != observation.get("hosted_gemma4_consensus_surface")
                or selected_surface not in {cell["ppocrv6_surface"], cell["vietocr_surface"]}
                or _parse(selected_surface, cell["lane_type"]) != selected_value
            ):
                raise _error("E0170 observation/raw source binding drifted")
            result[cell_id] = {
                "evaluation_id": identity,
                "selected_surface": selected_surface,
                "selected_value": selected_value,
            }
    return result


def _resolved_cell(
    cell: Mapping[str, Any],
    *,
    challenge: Mapping[str, Any] | None,
    dash: Mapping[str, Any] | None,
) -> dict[str, Any]:
    primary_value = _parse(cell["ppocrv6_surface"], cell["lane_type"])
    viet_value = _parse(cell["vietocr_surface"], cell["lane_type"])
    if challenge is not None and dash is not None:
        raise _error("one cell cannot consume both challenger and dash evidence")
    if challenge is not None:
        selected_surface = challenge["selected_surface"]
        selected_value = challenge["selected_value"]
        mode = (
            "E0170_TWO_STATELESS_HOSTED_CONSENSUS_CORROBORATES_PPOCRV6"
            if selected_surface == cell["ppocrv6_surface"]
            else "E0170_TWO_STATELESS_HOSTED_CONSENSUS_SELECTS_BOUND_VIETOCR"
        )
        evidence_ref = challenge["evaluation_id"]
    elif dash is not None:
        selected_surface = "VISIBLE_DASH"
        selected_value = 0
        mode = "TYPED_VISIBLE_DASH_PIXEL_EVIDENCE_ZERO"
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
        mode = "UNRESOLVED_NO_PRIMARY_OR_TYPED_OVERLAY"
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


def _resolved_row(
    row: Mapping[str, Any], challenges: Mapping[str, Any], dashes: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "cells": [
            _resolved_cell(
                cell,
                challenge=challenges.get(cell["cell_id"]),
                dash=dashes.get(cell["cell_id"]),
            )
            for cell in row["cells"]
        ],
        "label_surface": row["label_surface"],
        "role": row["role"],
    }


def _cell(row: Mapping[str, Any], lane: int) -> Mapping[str, Any]:
    return row["cells"][lane]


def _check(
    components: Sequence[tuple[str, Mapping[str, Any]]],
    target: tuple[str, Mapping[str, Any]],
    *,
    equation_id: str,
    lane_index: int,
    lane_type: str,
    target_near_100: bool = False,
) -> dict[str, Any]:
    observed = all(cell["selected_value"] is not None for _role, cell in (*components, target))
    component_values = [cell["selected_value"] for _role, cell in components]
    target_value = target[1]["selected_value"]
    if not observed:
        status = "UNRESOLVED_MISSING_OBSERVED_VALUE"
        computed = None
    else:
        computed_decimal = sum((_decimal(value) for value in component_values), Decimal(0))
        target_decimal = _decimal(target_value)
        tolerance = Decimal(0) if lane_type == "MONEY" else Decimal("0.05")
        residual = computed_decimal - target_decimal
        near_100 = not target_near_100 or abs(target_decimal - Decimal(100)) <= Decimal("0.05")
        if abs(residual) <= tolerance and near_100:
            status = (
                "CORROBORATED_EXACT_OBSERVED_EQUATION"
                if residual == 0
                else "CORROBORATED_BOUNDED_ROUNDING_OBSERVED_EQUATION"
            )
        else:
            status = "VETOED_OBSERVED_EQUATION"
        computed = (
            int(computed_decimal) if lane_type == "MONEY" else _percent_string(computed_decimal)
        )
        residual_output = int(residual) if lane_type == "MONEY" else _percent_string(residual)
        tolerance_output = "0" if lane_type == "MONEY" else "0.05"
    if not observed:
        residual_output = None
        tolerance_output = "0" if lane_type == "MONEY" else "0.05"
    return {
        "component_cell_ids": [cell["cell_id"] for _role, cell in components],
        "component_roles": [role for role, _cell_value in components],
        "component_values": component_values if observed else [],
        "computed_value": computed,
        "equation_id": equation_id,
        "equation_tolerance": tolerance_output,
        "lane_index": lane_index,
        "lane_type": lane_type,
        "required_for_acceptance": True,
        "residual": residual_output,
        "status": status,
        "target_cell_id": target[1]["cell_id"],
        "target_near_100_tolerance": "0.05" if target_near_100 else None,
        "target_role": target[0],
        "target_value": target_value if observed else None,
    }


def _shape(value: Any) -> dict[str, Any]:
    fields = {
        "accounting_checks",
        "additional_population",
        "authority",
        "claim_boundary",
        "core_rows",
        "core_subtotal",
        "family_id",
        "format_version",
        "grand_total",
        "input_id",
        "lane_types",
        "margin",
        "metrics",
        "period_axis",
        "result_id",
        "source_id",
        "status",
        "unresolved_reasons",
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
        raise _error("maturity numeric result contract drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "lmnrpv1:result:" + canonical_json_sha256_v1(material):
        raise _error("maturity numeric result identity drifted")
    return canonical_clone_v1(value)


def build_loan_maturity_numeric_reconciliation_v1(
    source: Any,
    *,
    challenger_overlays: Sequence[Any] = (),
    visible_dash_evidence: Sequence[Any] = (),
) -> dict[str, Any]:
    """Reconcile one structurally selected table without inferring any value."""

    if isinstance(challenger_overlays, (str, bytes, bytearray)) or not isinstance(
        challenger_overlays, Sequence
    ):
        raise _error("challenger overlays must be one sequence")
    if isinstance(visible_dash_evidence, (str, bytes, bytearray)) or not isinstance(
        visible_dash_evidence, Sequence
    ):
        raise _error("visible-dash overlays must be one sequence")
    typed = _validate_source(source)
    indexed = {cell["cell_id"]: (role, cell) for role, cell in _all_input_cells(typed)}
    challenges = _e0170_observations(challenger_overlays, indexed)
    dashes = _typed_dash_overlays(visible_dash_evidence, indexed, source_id=typed["source_id"])
    if set(challenges) & set(dashes):
        raise _error("challenger and visible-dash overlays overlap")

    rows = [_resolved_row(row, challenges, dashes) for row in typed["core_rows"]]
    margin = None if typed["margin"] is None else _resolved_row(typed["margin"], challenges, dashes)
    subtotal = (
        None
        if typed["core_subtotal"] is None
        else _resolved_row(typed["core_subtotal"], challenges, dashes)
    )
    grand = (
        None
        if typed["grand_total"] is None
        else _resolved_row(typed["grand_total"], challenges, dashes)
    )
    additional = None
    if typed["additional_population"] is not None:
        additional = {
            "breakdown_rows": [
                _resolved_row(row, challenges, dashes)
                for row in typed["additional_population"]["breakdown_rows"]
            ],
            "parent": _resolved_row(typed["additional_population"]["parent"], challenges, dashes),
        }

    checks = []
    money_lanes = [index for index, lane in enumerate(typed["lane_types"]) if lane == "MONEY"]
    for lane in money_lanes:
        core_components = [(row["role"], _cell(row, lane)) for row in rows]
        if margin is None and additional is None:
            checks.append(
                _check(
                    core_components,
                    (subtotal["role"], _cell(subtotal, lane)),
                    equation_id=f"CORE_BUCKETS_EQUAL_CORE_SUBTOTAL_LANE_{lane}",
                    lane_index=lane,
                    lane_type="MONEY",
                )
            )
        elif margin is not None and subtotal is None:
            checks.append(
                _check(
                    [*core_components, (margin["role"], _cell(margin, lane))],
                    (grand["role"], _cell(grand, lane)),
                    equation_id=f"CORE_BUCKETS_PLUS_MARGIN_EQUAL_GRAND_TOTAL_LANE_{lane}",
                    lane_index=lane,
                    lane_type="MONEY",
                )
            )
        elif margin is not None:
            checks.extend(
                [
                    _check(
                        core_components,
                        (subtotal["role"], _cell(subtotal, lane)),
                        equation_id=f"CORE_BUCKETS_EQUAL_CORE_SUBTOTAL_LANE_{lane}",
                        lane_index=lane,
                        lane_type="MONEY",
                    ),
                    _check(
                        [
                            (subtotal["role"], _cell(subtotal, lane)),
                            (margin["role"], _cell(margin, lane)),
                        ],
                        (grand["role"], _cell(grand, lane)),
                        equation_id=f"CORE_SUBTOTAL_PLUS_MARGIN_EQUAL_GRAND_TOTAL_LANE_{lane}",
                        lane_index=lane,
                        lane_type="MONEY",
                    ),
                ]
            )
        else:
            parent = additional["parent"]
            breakdown = additional["breakdown_rows"]
            checks.extend(
                [
                    _check(
                        core_components,
                        (subtotal["role"], _cell(subtotal, lane)),
                        equation_id=f"CORE_BUCKETS_EQUAL_CORE_SUBTOTAL_LANE_{lane}",
                        lane_index=lane,
                        lane_type="MONEY",
                    ),
                    _check(
                        [(row["role"], _cell(row, lane)) for row in breakdown],
                        (parent["role"], _cell(parent, lane)),
                        equation_id=f"ADDITIONAL_BREAKDOWN_EQUAL_PARENT_LANE_{lane}",
                        lane_index=lane,
                        lane_type="MONEY",
                    ),
                    _check(
                        [
                            (subtotal["role"], _cell(subtotal, lane)),
                            (parent["role"], _cell(parent, lane)),
                        ],
                        (grand["role"], _cell(grand, lane)),
                        equation_id=f"CORE_SUBTOTAL_PLUS_ADDITIONAL_EQUAL_GRAND_TOTAL_LANE_{lane}",
                        lane_index=lane,
                        lane_type="MONEY",
                    ),
                ]
            )
    percentage_lanes = [
        index for index, lane in enumerate(typed["lane_types"]) if lane == "PERCENT"
    ]
    for lane in percentage_lanes:
        checks.append(
            _check(
                [(row["role"], _cell(row, lane)) for row in rows],
                (subtotal["role"], _cell(subtotal, lane)),
                equation_id=f"CORE_PERCENTAGES_EQUAL_PRINTED_PERCENT_TOTAL_LANE_{lane}",
                lane_index=lane,
                lane_type="PERCENT",
                target_near_100=True,
            )
        )
    accepted_check_statuses = {
        "CORROBORATED_BOUNDED_ROUNDING_OBSERVED_EQUATION",
        "CORROBORATED_EXACT_OBSERVED_EQUATION",
    }
    failures = [
        check["equation_id"] for check in checks if check["status"] not in accepted_check_statuses
    ]
    unresolved = [f"REQUIRED_ACCOUNTING_CHECK_FAILED:{identifier}" for identifier in failures]
    used_cells = {cell_id for cell_id in (*challenges, *dashes)}
    if len(used_cells) != len(challenges) + len(dashes):
        raise _error("numeric overlay consumption drifted")
    material_input = {
        "challenger_evaluation_ids": sorted(
            {overlay["evaluation_id"] for overlay in challenges.values()}
        ),
        "source": typed,
        "visible_dash_evidence_ids": sorted(
            {overlay["evidence_id"] for overlay in dashes.values()}
        ),
    }
    input_id = "lmnrpv1:input:" + canonical_json_sha256_v1(material_input)
    material = {
        "accounting_checks": checks,
        "additional_population": additional,
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "core_rows": rows,
        "core_subtotal": subtotal,
        "family_id": FAMILY_ID,
        "format_version": FORMAT_VERSION,
        "grand_total": grand,
        "input_id": input_id,
        "lane_types": canonical_clone_v1(typed["lane_types"]),
        "margin": margin,
        "metrics": {
            "challenger_changed_primary_cell_count": sum(
                indexed[cell_id][1]["ppocrv6_surface"] != overlay["selected_surface"]
                for cell_id, overlay in challenges.items()
            ),
            "challenger_observation_count": len(challenges),
            "computed_unprinted_core_identity_count": (
                len(money_lanes) if margin is not None and subtotal is None else 0
            ),
            "independent_observed_equation_count": sum(
                check["status"] in accepted_check_statuses for check in checks
            ),
            "mapped_core_money_cell_count": len(rows) * len(money_lanes),
            "mapped_margin_money_cell_count": 0 if margin is None else len(money_lanes),
            "percentage_child_cell_count": len(rows) * len(percentage_lanes),
            "percentage_total_control_cell_count": len(percentage_lanes),
            "source_additional_population_count": 0 if additional is None else 1,
            "source_control_row_count": sum(item is not None for item in (subtotal, grand)),
            "visible_dash_zero_cell_count": len(dashes),
        },
        "period_axis": canonical_clone_v1(typed["period_axis"]),
        "source_id": typed["source_id"],
        "status": "EXACT_OBSERVED_NUMERIC_RECONCILIATION" if not unresolved else "UNRESOLVED",
        "unresolved_reasons": unresolved,
    }
    return _shape({**material, "result_id": "lmnrpv1:result:" + canonical_json_sha256_v1(material)})


def validate_loan_maturity_numeric_reconciliation_v1(value: Any) -> dict[str, Any]:
    """Validate one content-addressed numeric reconciliation result."""

    return _shape(value)


def validate_loan_maturity_numeric_reconciliation_replay_v1(
    value: Any,
    source: Any,
    *,
    challenger_overlays: Sequence[Any] = (),
    visible_dash_evidence: Sequence[Any] = (),
) -> dict[str, Any]:
    """Rebuild from the same raw evidence and require exact typed equality."""

    persisted = _shape(value)
    rebuilt = build_loan_maturity_numeric_reconciliation_v1(
        source,
        challenger_overlays=challenger_overlays,
        visible_dash_evidence=visible_dash_evidence,
    )
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("maturity numeric reconciliation does not replay exactly")
    return rebuilt
