"""Observed-surface numeric reconciliation for customer-loan quality tables.

The module starts after a structural graph has selected one loan-quality
table.  It keeps the PP-OCRv6 and VietOCR surfaces separately, parses only
values that were actually observed, and uses exact accounting equations only
to corroborate or veto those observations.  An equation may select one of two
observed reader values when exactly one observed assignment closes; it never
invents or back-solves a missing value.  In particular, a blank is unresolved
while an explicit visible dash is an observed zero.

The horizontal contract covers two money lanes and interleaved
money/percentage lanes.  The stacked contract covers VIB-style repeated
period blocks whose non-target asset columns may be sparse.  Missing sparse
columns are recorded and are never treated as zero.
"""

from __future__ import annotations

import itertools
import json
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.family_first_numeric_cell_evidence_v1 import (
    parse_visible_financial_numeric_token_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "CLOSED_SCHEMA_FORMAT_VERSION",
    "CONTEXT_FORMAT_VERSION",
    "FORMAT_VERSION",
    "INPUT_FORMAT_VERSION",
    "MARGIN_PRESENTATION_MODES",
    "LoanQualityNumericRowReconciliationV1Error",
    "build_loan_quality_numeric_row_reconciliation_v1",
    "load_loan_quality_margin_context_140_v2",
    "project_loan_quality_closed_schema_v1",
    "validate_loan_quality_closed_schema_v1",
    "validate_loan_quality_closed_schema_projection_v1",
    "validate_loan_quality_margin_context_140_v2",
    "validate_loan_quality_numeric_row_reconciliation_input_v1",
    "validate_loan_quality_numeric_row_reconciliation_replay_v1",
    "validate_loan_quality_numeric_row_reconciliation_v1",
]


FORMAT_VERSION = "LOAN_QUALITY_NUMERIC_ROW_RECONCILIATION_V1"
INPUT_FORMAT_VERSION = "LOAN_QUALITY_NUMERIC_ROW_RECONCILIATION_INPUT_V1"
CONTEXT_FORMAT_VERSION = "LOAN_QUALITY_MARGIN_CONTEXT_140_V2"
CLOSED_SCHEMA_FORMAT_VERSION = "LOAN_QUALITY_CLOSED_SCHEMA_PROJECTION_V1"
CLAIM_BOUNDARY = (
    "BOUND_PP_OCRV6_AND_VIETOCR_OBSERVED_SURFACE_TYPED_LANE_EXACT_ACCOUNTING_"
    "CORROBORATION_OR_VETO_ONLY_UNIQUE_CONFLICT_SELECTION_FROM_OBSERVED_VALUES_"
    "NO_MISSING_VALUE_INFERENCE_BACKSOLVE_SCHEMA_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)

MARGIN_PRESENTATION_MODES = (
    "STANDALONE_AFTER_FIVE_GRADES",
    "INCLUDED_IN_747_VIA_5746",
    "EXPLICITLY_EXCLUDED_FROM_CORE_VIA_FOOTNOTE",
    "NOT_OBSERVED_DO_NOT_SYNTHESIZE",
)
_ROLES = ("STANDARD", "SPECIAL_MENTION", "SUBSTANDARD", "DOUBTFUL", "LOSS")
_SUPPORTED_LANES = (
    ("MONEY", "MONEY"),
    ("MONEY", "PERCENT", "MONEY", "PERCENT"),
)
_LAYOUT_HORIZONTAL = "HORIZONTAL_TYPED_PERIOD_LANES"
_LAYOUT_STACKED = "STACKED_PERIOD_BLOCKS_MULTI_ASSET_COLUMNS"
_AUTHORITY = {
    "accounting_equation_can_infer_or_backsolve_value": False,
    "accounting_equation_is_corroborator_or_veto_only": True,
    "blank_or_missing_cell_imputed_as_zero": False,
    "conflict_selection_requires_one_exact_observed_assignment": True,
    "dash_only_surface_is_observed_zero": True,
    "mapping_authority": False,
    "ppocrv6_surface_retained": True,
    "schema_authority": False,
    "sparse_absent_column_imputed_as_zero": False,
    "vietocr_surface_retained": True,
}

_INPUT_FIELDS = {
    "format_version",
    "lane_types",
    "layout_mode",
    "margin",
    "margin_mode",
    "parent_total",
    "rows",
    "source_id",
    "sparse_blocks",
    "total",
}
_INPUT_CELL_FIELDS = {
    "lane_index",
    "page_sequence",
    "ppocrv6_surface",
    "source_line_index",
    "vietocr_surface",
}
_INPUT_ROW_FIELDS = {"cells", "label_surface", "role"}
_INPUT_TOTAL_FIELDS = {"cells", "label_surface"}
_SPARSE_BLOCK_FIELDS = {
    "block_ordinal",
    "column_count",
    "rows",
    "target_column_index",
    "total",
    "total_column_index",
}
_RESULT_FIELDS = {
    "accounting_checks",
    "authority",
    "claim_boundary",
    "format_version",
    "input_id",
    "lane_types",
    "layout_mode",
    "margin",
    "margin_mode",
    "metrics",
    "parent_total",
    "result_id",
    "rows",
    "source_id",
    "sparse_blocks",
    "status",
    "total",
    "unresolved_reasons",
}
_RESULT_CELL_FIELDS = {
    "candidate_values",
    "lane_index",
    "lane_type",
    "page_sequence",
    "ppocrv6_surface",
    "selected_readers",
    "selected_value",
    "source_line_index",
    "status",
    "vietocr_surface",
}
_CHECK_FIELDS = {
    "component_count",
    "equation_id",
    "exact_observed_assignment_count",
    "lane_index",
    "lane_type",
    "required_for_acceptance",
    "selected_component_values",
    "selected_sum",
    "selected_target",
    "status",
    "target_kind",
    "term_roles",
}
_EXACT_CHECK_STATUSES = {
    "EXACT_OBSERVED_EQUATION",
    "EXACT_EQUATION_UNIQUELY_SELECTED_OBSERVED_CONFLICT",
}
_CHECK_STATUSES = {
    *_EXACT_CHECK_STATUSES,
    "NOT_EVALUATED_INCOMPLETE_SPARSE_SOURCE_COLUMN",
    "UNRESOLVED_MISSING_OBSERVED_VALUE",
    "UNRESOLVED_MULTIPLE_EXACT_OBSERVED_ASSIGNMENTS",
    "VETOED_NO_EXACT_OBSERVED_ASSIGNMENT",
}

_CORE_SCHEMA = {
    746: ("Phân tích chất lượng nợ cho vay", 716),
    747: ("+ Nhóm 1: Nợ đủ tiêu chuẩn", 746),
    5746: ("Trong đó: Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán", 747),
    748: ("+ Nhóm 2: Nợ cần chú ý", 746),
    749: ("+ Nhóm 3: Nợ dưới tiêu chuẩn", 746),
    750: ("+ Nhóm 4: Nợ nghi ngờ", 746),
    751: ("+ Nhóm 5: Nợ có khả năng mất vốn", 746),
    1944: ("Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán", None),
}
_SCHEMA_ORDER = (746, 747, 5746, 748, 749, 750, 751, 1944)
_ROLE_SCHEMA_IDS = {
    "STANDARD": 747,
    "SPECIAL_MENTION": 748,
    "SUBSTANDARD": 749,
    "DOUBTFUL": 750,
    "LOSS": 751,
    "MARGIN_AND_SECURITIES_ADVANCE": 1944,
    "INCLUDED_MARGIN_SOURCE_DISCLOSURE": 5746,
}


class LoanQualityNumericRowReconciliationV1Error(ValueError):
    """The context, schema, observed numeric axis, or replay drifted."""


def _error(message: str) -> LoanQualityNumericRowReconciliationV1Error:
    return LoanQualityNumericRowReconciliationV1Error(message)


def _strict_object(payload: bytes, label: str) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise _error(f"{label} contains duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                _error(f"{label} contains non-finite JSON: {token}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"{label} is not strict UTF-8 JSON") from exc
    if type(value) is not dict:
        raise _error(f"{label} root must be one object")
    return value


def validate_loan_quality_margin_context_140_v2(value: Any) -> dict[str, Any]:
    """Validate the immutable 140-filing margin normalization context."""

    expected_fields = {
        "authority",
        "context_id",
        "explicit_excluded_footnote",
        "family",
        "format_version",
        "included_source_disclosure",
        "normalization_policy",
        "presentation_modes",
        "standalone_item",
        "state",
    }
    if type(value) is not dict or set(value) != expected_fields:
        raise _error("loan-quality margin context fields drifted")
    expected_authority = {
        "bank_page_or_filename_is_a_mapping_rule": False,
        "bounded_loan_quality_normalization_only": True,
        "canonical_or_export_authority": False,
        "project_owner_decision_required": True,
        "raw_text_similarity_is_mapping_authority": False,
        "source_geometry_period_unit_and_accounting_replay_required": True,
    }
    expected_policy = {
        "double_count_permitted": False,
        "explicitly_excluded_footnote": (
            "KEEP_747_UNCHANGED_EMIT_INDEPENDENTLY_OBSERVED_1944_AND_"
            "RECONCILE_CORE_PLUS_1944_TO_PARENT"
        ),
        "included_in_747": "SUBTRACT_EXACT_5746_VALUE_FROM_747_AND_EMIT_1944",
        "standalone_after_five_grades": "KEEP_747_UNCHANGED_AND_EMIT_1944",
        "unobserved": "DO_NOT_SYNTHESIZE_1944",
    }
    if (
        value["format_version"] != CONTEXT_FORMAT_VERSION
        or value["state"] != "PROJECT_OWNER_ADJUDICATED_BOUNDED_SCHEMA_CONTEXT"
        or not same_typed_json_v1(value["authority"], expected_authority)
        or not same_typed_json_v1(
            value["family"],
            {"canonical_name": "Phân tích chất lượng nợ cho vay", "report_norm_id": 746},
        )
        or not same_typed_json_v1(value["normalization_policy"], expected_policy)
        or value["presentation_modes"] != list(MARGIN_PRESENTATION_MODES)
    ):
        raise _error("loan-quality margin context meanings drifted")
    included = value["included_source_disclosure"]
    standalone = value["standalone_item"]
    excluded = value["explicit_excluded_footnote"]
    if (
        type(included) is not dict
        or included.get("report_norm_id") != 5746
        or included.get("parent_report_norm_id") != 747
        or included.get("mapping_output_authority") is not False
        or included.get("role") != "SOURCE_PRESENTATION_BRIDGE_ONLY"
        or type(standalone) is not dict
        or standalone.get("report_norm_id") != 1944
        or standalone.get("parent_report_norm_id") != 746
        or standalone.get("hierarchy_level") != 2
        or standalone.get("mapping_eligible_in_this_bounded_context") is not True
        or standalone.get("template_identity_reused") is not True
        or type(excluded) is not dict
        or set(excluded)
        != {
            "mapping_output_authority",
            "parent_report_norm_id",
            "population_relation",
            "role",
            "standalone_report_norm_id",
        }
        or excluded["mapping_output_authority"] is not True
        or excluded["parent_report_norm_id"] != 746
        or excluded["standalone_report_norm_id"] != 1944
        or excluded["population_relation"] != "EXCLUDED_FROM_PRINTED_FIVE_GRADE_TOTAL"
        or excluded["role"] != "NONADDITIVE_EXCLUDED_DISCLOSURE"
    ):
        raise _error("loan-quality margin context disclosure semantics drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("context_id")
    if identity != "lqmc:140:v2:" + canonical_json_sha256_v1(material):
        raise _error("loan-quality margin context identity drifted")
    return canonical_clone_v1(value)


def load_loan_quality_margin_context_140_v2(path: str | Path) -> dict[str, Any]:
    """Read and validate one strict UTF-8 context file."""

    target = Path(path)
    try:
        payload = target.read_bytes()
    except OSError as exc:
        raise _error("loan-quality margin context cannot be read") from exc
    return validate_loan_quality_margin_context_140_v2(
        _strict_object(payload, "loan-quality margin context")
    )


def _node_value(node: Any, field: str) -> Any:
    if isinstance(node, Mapping):
        return node.get(field)
    return getattr(node, field, None)


def _presentation_bindings(context: Mapping[str, Any]) -> list[dict[str, Any]]:
    policy = context["normalization_policy"]
    return [
        {
            "emit_report_norm_id": 1944,
            "normalization_policy": policy["standalone_after_five_grades"],
            "presentation_mode": "STANDALONE_AFTER_FIVE_GRADES",
            "source_bridge_report_norm_id": None,
        },
        {
            "emit_report_norm_id": 1944,
            "normalization_policy": policy["included_in_747"],
            "presentation_mode": "INCLUDED_IN_747_VIA_5746",
            "source_bridge_report_norm_id": 5746,
        },
        {
            "emit_report_norm_id": 1944,
            "normalization_policy": policy["explicitly_excluded_footnote"],
            "presentation_mode": "EXPLICITLY_EXCLUDED_FROM_CORE_VIA_FOOTNOTE",
            "source_bridge_report_norm_id": None,
        },
        {
            "emit_report_norm_id": None,
            "normalization_policy": policy["unobserved"],
            "presentation_mode": "NOT_OBSERVED_DO_NOT_SYNTHESIZE",
            "source_bridge_report_norm_id": None,
        },
    ]


def project_loan_quality_closed_schema_v1(
    schema_by_id: Mapping[int, Any], margin_context: Any
) -> dict[str, Any]:
    """Project and close the exact live schema nodes used by a family builder."""

    if not isinstance(schema_by_id, Mapping):
        raise _error("loan-quality live schema must be one mapping")
    context = validate_loan_quality_margin_context_140_v2(margin_context)
    nodes = []
    for schema_id in _SCHEMA_ORDER:
        node = schema_by_id.get(schema_id)
        if node is None:
            raise _error(f"required loan-quality schema node is absent: {schema_id}")
        canonical_name, expected_parent = _CORE_SCHEMA[schema_id]
        live_parent = _node_value(node, "parent_id")
        scope = _node_value(node, "scope")
        display_order = _node_value(node, "display_order")
        statement_type = _node_value(node, "statement_type")
        if (
            _node_value(node, "canonical_name") != canonical_name
            or type(display_order) is not int
            or display_order < 0
            or statement_type != "TM"
            or type(scope) is not list
            or scope != ["SEPARATE", "CONSOLIDATED"]
            or (schema_id != 1944 and live_parent != expected_parent)
            or (schema_id == 1944 and live_parent not in {None, 746})
        ):
            raise _error(f"loan-quality live schema node drifted: {schema_id}")
        disposition = (
            "MAPPING_ELIGIBLE_FAMILY_PARENT"
            if schema_id == 746
            else "SOURCE_PRESENTATION_BRIDGE_ONLY"
            if schema_id == 5746
            else "BOUNDED_CONTEXT_MAPPING_ELIGIBLE"
            if schema_id == 1944
            else "MAPPING_ELIGIBLE_CORE_GRADE"
        )
        nodes.append(
            {
                "canonical_name": canonical_name,
                "display_order": display_order,
                "effective_parent_id": 746 if schema_id == 1944 else expected_parent,
                "live_parent_id": live_parent,
                "mapping_disposition": disposition,
                "report_norm_id": schema_id,
                "scope": list(scope),
                "statement_type": statement_type,
            }
        )
    by_id = {node["report_norm_id"]: node for node in nodes}
    ordered_core = [
        by_id[schema_id]["display_order"] for schema_id in (746, 747, 5746, 748, 749, 750, 751)
    ]
    if ordered_core != sorted(ordered_core) or len(ordered_core) != len(set(ordered_core)):
        raise _error("loan-quality live schema display order drifted")
    role_bindings = [
        {
            "mapping_disposition": by_id[schema_id]["mapping_disposition"],
            "report_norm_id": schema_id,
            "role": role,
        }
        for role, schema_id in _ROLE_SCHEMA_IDS.items()
    ]
    material = {
        "context_id": context["context_id"],
        "family_report_norm_id": 746,
        "format_version": CLOSED_SCHEMA_FORMAT_VERSION,
        "nodes": nodes,
        "presentation_bindings": _presentation_bindings(context),
        "role_bindings": role_bindings,
    }
    return validate_loan_quality_closed_schema_projection_v1(
        {
            **material,
            "projection_id": "lqcspv1:schema:" + canonical_json_sha256_v1(material),
        }
    )


def validate_loan_quality_closed_schema_projection_v1(value: Any) -> dict[str, Any]:
    """Validate a self-identifying, builder-safe closed family projection."""

    fields = {
        "context_id",
        "family_report_norm_id",
        "format_version",
        "nodes",
        "presentation_bindings",
        "projection_id",
        "role_bindings",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value["format_version"] != CLOSED_SCHEMA_FORMAT_VERSION
        or value["family_report_norm_id"] != 746
        or type(value["context_id"]) is not str
        or not value["context_id"].startswith("lqmc:140:v2:")
        or type(value["nodes"]) is not list
        or [node.get("report_norm_id") for node in value["nodes"]] != list(_SCHEMA_ORDER)
        or type(value["role_bindings"]) is not list
        or type(value["presentation_bindings"]) is not list
        or [item.get("presentation_mode") for item in value["presentation_bindings"]]
        != list(MARGIN_PRESENTATION_MODES)
    ):
        raise _error("loan-quality closed schema projection fields drifted")
    by_id: dict[int, Mapping[str, Any]] = {}
    node_fields = {
        "canonical_name",
        "display_order",
        "effective_parent_id",
        "live_parent_id",
        "mapping_disposition",
        "report_norm_id",
        "scope",
        "statement_type",
    }
    for node in value["nodes"]:
        if type(node) is not dict or set(node) != node_fields:
            raise _error("loan-quality closed schema node fields drifted")
        schema_id = node["report_norm_id"]
        canonical_name, parent = _CORE_SCHEMA[schema_id]
        expected_disposition = (
            "MAPPING_ELIGIBLE_FAMILY_PARENT"
            if schema_id == 746
            else "SOURCE_PRESENTATION_BRIDGE_ONLY"
            if schema_id == 5746
            else "BOUNDED_CONTEXT_MAPPING_ELIGIBLE"
            if schema_id == 1944
            else "MAPPING_ELIGIBLE_CORE_GRADE"
        )
        if (
            node["canonical_name"] != canonical_name
            or type(node["display_order"]) is not int
            or node["display_order"] < 0
            or node["statement_type"] != "TM"
            or node["scope"] != ["SEPARATE", "CONSOLIDATED"]
            or node["effective_parent_id"] != (746 if schema_id == 1944 else parent)
            or (schema_id != 1944 and node["live_parent_id"] != parent)
            or (schema_id == 1944 and node["live_parent_id"] not in {None, 746})
            or node["mapping_disposition"] != expected_disposition
        ):
            raise _error("loan-quality closed schema node semantics drifted")
        by_id[schema_id] = node
    expected_roles = [
        {
            "mapping_disposition": by_id[schema_id]["mapping_disposition"],
            "report_norm_id": schema_id,
            "role": role,
        }
        for role, schema_id in _ROLE_SCHEMA_IDS.items()
    ]
    if not same_typed_json_v1(value["role_bindings"], expected_roles):
        raise _error("loan-quality closed schema role bindings drifted")
    expected_presentations = [
        {
            "emit_report_norm_id": 1944,
            "normalization_policy": "KEEP_747_UNCHANGED_AND_EMIT_1944",
            "presentation_mode": "STANDALONE_AFTER_FIVE_GRADES",
            "source_bridge_report_norm_id": None,
        },
        {
            "emit_report_norm_id": 1944,
            "normalization_policy": "SUBTRACT_EXACT_5746_VALUE_FROM_747_AND_EMIT_1944",
            "presentation_mode": "INCLUDED_IN_747_VIA_5746",
            "source_bridge_report_norm_id": 5746,
        },
        {
            "emit_report_norm_id": 1944,
            "normalization_policy": (
                "KEEP_747_UNCHANGED_EMIT_INDEPENDENTLY_OBSERVED_1944_AND_"
                "RECONCILE_CORE_PLUS_1944_TO_PARENT"
            ),
            "presentation_mode": "EXPLICITLY_EXCLUDED_FROM_CORE_VIA_FOOTNOTE",
            "source_bridge_report_norm_id": None,
        },
        {
            "emit_report_norm_id": None,
            "normalization_policy": "DO_NOT_SYNTHESIZE_1944",
            "presentation_mode": "NOT_OBSERVED_DO_NOT_SYNTHESIZE",
            "source_bridge_report_norm_id": None,
        },
    ]
    for binding in value["presentation_bindings"]:
        if (
            type(binding) is not dict
            or set(binding)
            != {
                "emit_report_norm_id",
                "normalization_policy",
                "presentation_mode",
                "source_bridge_report_norm_id",
            }
            or type(binding["normalization_policy"]) is not str
            or not binding["normalization_policy"]
        ):
            raise _error("loan-quality presentation binding drifted")
    if not same_typed_json_v1(value["presentation_bindings"], expected_presentations):
        raise _error("loan-quality presentation binding meanings drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("projection_id")
    if identity != "lqcspv1:schema:" + canonical_json_sha256_v1(material):
        raise _error("loan-quality closed schema projection identity drifted")
    return canonical_clone_v1(value)


def validate_loan_quality_closed_schema_v1(value: Any) -> dict[str, Any]:
    """Builder-facing alias for the exact closed-schema projection validator."""

    return validate_loan_quality_closed_schema_projection_v1(value)


def _surface(value: Any, label: str) -> str | None:
    if value is not None and type(value) is not str:
        raise _error(f"{label} must be a string or null")
    return value


def _input_cell(value: Any, *, lane_count: int, label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _INPUT_CELL_FIELDS:
        raise _error(f"{label} fields drifted")
    lane = value["lane_index"]
    page = value["page_sequence"]
    line = value["source_line_index"]
    if (
        type(lane) is not int
        or not 0 <= lane < lane_count
        or type(page) is not int
        or page <= 0
        or (line is not None and (type(line) is not int or line < 0))
    ):
        raise _error(f"{label} locator drifted")
    pp = _surface(value["ppocrv6_surface"], f"{label} PP-OCRv6 surface")
    viet = _surface(value["vietocr_surface"], f"{label} VietOCR surface")
    if pp is None and viet is None:
        raise _error(f"{label} must retain at least one reader surface")
    return {
        "lane_index": lane,
        "page_sequence": page,
        "ppocrv6_surface": pp,
        "source_line_index": line,
        "vietocr_surface": viet,
    }


def _input_cells(
    value: Any,
    *,
    lane_count: int,
    exact_axis: Sequence[int] | None,
    label: str,
) -> list[dict[str, Any]]:
    if type(value) is not list:
        raise _error(f"{label} must be one cell list")
    cells = [
        _input_cell(cell, lane_count=lane_count, label=f"{label} cell {ordinal}")
        for ordinal, cell in enumerate(value)
    ]
    lanes = [cell["lane_index"] for cell in cells]
    if lanes != sorted(set(lanes)):
        raise _error(f"{label} lane axis repeats or is not ordered")
    if exact_axis is not None and lanes != list(exact_axis):
        raise _error(f"{label} does not cover its required lane axis")
    return cells


def _input_row(
    value: Any,
    *,
    expected_role: str,
    lane_count: int,
    exact_axis: Sequence[int] | None,
    label: str,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _INPUT_ROW_FIELDS:
        raise _error(f"{label} fields drifted")
    if (
        value["role"] != expected_role
        or type(value["label_surface"]) is not str
        or not value["label_surface"].strip()
    ):
        raise _error(f"{label} role or label drifted")
    return {
        "cells": _input_cells(
            value["cells"], lane_count=lane_count, exact_axis=exact_axis, label=label
        ),
        "label_surface": value["label_surface"],
        "role": expected_role,
    }


def _input_total(
    value: Any,
    *,
    lane_count: int,
    exact_axis: Sequence[int] | None,
    label: str,
) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _INPUT_TOTAL_FIELDS
        or type(value["label_surface"]) is not str
    ):
        raise _error(f"{label} fields drifted")
    return {
        "cells": _input_cells(
            value["cells"], lane_count=lane_count, exact_axis=exact_axis, label=label
        ),
        "label_surface": value["label_surface"],
    }


def _input_margin(
    value: Any,
    *,
    mode: str,
    lane_types: Sequence[str],
) -> dict[str, Any] | None:
    if mode == "NOT_OBSERVED_DO_NOT_SYNTHESIZE":
        if value is not None:
            raise _error("unobserved margin mode cannot carry a source row")
        return None
    if (
        type(value) is not dict
        or set(value) != _INPUT_TOTAL_FIELDS
        or type(value["label_surface"]) is not str
        or not value["label_surface"].strip()
    ):
        raise _error("observed margin record fields drifted")
    money_axis = [index for index, lane_type in enumerate(lane_types) if lane_type == "MONEY"]
    cells = _input_cells(
        value["cells"], lane_count=len(lane_types), exact_axis=None, label="margin"
    )
    lanes = [cell["lane_index"] for cell in cells]
    if lanes not in (money_axis, list(range(len(lane_types)))):
        raise _error("observed margin row must cover every money lane or the full typed axis")
    return {"cells": cells, "label_surface": value["label_surface"]}


def _input_horizontal(value: Mapping[str, Any], lane_types: Sequence[str]) -> dict[str, Any]:
    lane_count = len(lane_types)
    axis = list(range(lane_count))
    if type(value["rows"]) is not list or len(value["rows"]) != len(_ROLES):
        raise _error("horizontal loan-quality input requires exactly five grade rows")
    rows = [
        _input_row(
            row,
            expected_role=role,
            lane_count=lane_count,
            exact_axis=axis,
            label=f"horizontal {role} row",
        )
        for role, row in zip(_ROLES, value["rows"], strict=True)
    ]
    total = _input_total(
        value["total"], lane_count=lane_count, exact_axis=axis, label="quality table total"
    )
    parent = value["parent_total"]
    if parent is not None:
        parent = _input_total(
            parent, lane_count=lane_count, exact_axis=None, label="customer-loan parent total"
        )
        money_axis = [index for index, lane_type in enumerate(lane_types) if lane_type == "MONEY"]
        if [cell["lane_index"] for cell in parent["cells"]] not in (
            money_axis,
            axis,
        ):
            raise _error("customer-loan parent total lane axis drifted")
    if value["sparse_blocks"] != []:
        raise _error("horizontal loan-quality input cannot carry sparse period blocks")
    return {"parent_total": parent, "rows": rows, "sparse_blocks": [], "total": total}


def _input_sparse(value: Mapping[str, Any], lane_types: Sequence[str]) -> dict[str, Any]:
    if list(lane_types) != ["MONEY", "MONEY"] or value["rows"] != [] or value["total"] is not None:
        raise _error("stacked sparse input must project exactly two money periods from blocks")
    blocks = value["sparse_blocks"]
    if type(blocks) is not list or len(blocks) != 2:
        raise _error("stacked sparse input requires exactly two period blocks")
    normalized = []
    for expected_block, block in enumerate(blocks):
        if type(block) is not dict or set(block) != _SPARSE_BLOCK_FIELDS:
            raise _error("stacked sparse block fields drifted")
        column_count = block["column_count"]
        target = block["target_column_index"]
        companion = block["total_column_index"]
        if (
            block["block_ordinal"] != expected_block
            or type(column_count) is not int
            or column_count < 2
            or type(target) is not int
            or type(companion) is not int
            or not 0 <= target < column_count
            or not 0 <= companion < column_count
            or target == companion
            or type(block["rows"]) is not list
            or len(block["rows"]) != len(_ROLES)
        ):
            raise _error("stacked sparse block axis drifted")
        rows = [
            _input_row(
                row,
                expected_role=role,
                lane_count=column_count,
                exact_axis=None,
                label=f"stacked block {expected_block} {role} row",
            )
            for role, row in zip(_ROLES, block["rows"], strict=True)
        ]
        total = _input_total(
            block["total"],
            lane_count=column_count,
            exact_axis=None,
            label=f"stacked block {expected_block} total",
        )
        normalized.append(
            {
                "block_ordinal": expected_block,
                "column_count": column_count,
                "rows": rows,
                "target_column_index": target,
                "total": total,
                "total_column_index": companion,
            }
        )
    parent = value["parent_total"]
    if parent is not None:
        parent = _input_total(parent, lane_count=2, exact_axis=[0, 1], label="parent total")
    return {"parent_total": parent, "rows": [], "sparse_blocks": normalized, "total": None}


def _input(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _INPUT_FIELDS:
        raise _error("loan-quality numeric reconciliation input fields drifted")
    lane_types = value["lane_types"]
    if (
        value["format_version"] != INPUT_FORMAT_VERSION
        or type(value["source_id"]) is not str
        or not value["source_id"]
        or type(lane_types) is not list
        or tuple(lane_types) not in _SUPPORTED_LANES
        or value["layout_mode"] not in {_LAYOUT_HORIZONTAL, _LAYOUT_STACKED}
        or value["margin_mode"] not in MARGIN_PRESENTATION_MODES
    ):
        raise _error("loan-quality numeric reconciliation input identity or axis drifted")
    structural = (
        _input_horizontal(value, lane_types)
        if value["layout_mode"] == _LAYOUT_HORIZONTAL
        else _input_sparse(value, lane_types)
    )
    margin = _input_margin(value["margin"], mode=value["margin_mode"], lane_types=lane_types)
    if (
        value["margin_mode"] == "EXPLICITLY_EXCLUDED_FROM_CORE_VIA_FOOTNOTE"
        and structural["parent_total"] is None
    ):
        raise _error("excluded-footnote mode requires an independently observed parent total")
    if value["layout_mode"] == _LAYOUT_STACKED and value["margin_mode"] not in {
        "NOT_OBSERVED_DO_NOT_SYNTHESIZE",
        "EXPLICITLY_EXCLUDED_FROM_CORE_VIA_FOOTNOTE",
    }:
        raise _error("stacked sparse margin presentation is not declared by this contract")
    return {
        "format_version": INPUT_FORMAT_VERSION,
        "lane_types": list(lane_types),
        "layout_mode": value["layout_mode"],
        "margin": margin,
        "margin_mode": value["margin_mode"],
        "parent_total": structural["parent_total"],
        "rows": structural["rows"],
        "source_id": value["source_id"],
        "sparse_blocks": structural["sparse_blocks"],
        "total": structural["total"],
    }


def validate_loan_quality_numeric_row_reconciliation_input_v1(
    value: Any,
) -> dict[str, Any]:
    """Validate and clone the graph-neutral observed-surface input contract."""

    return _input(value)


def _canonical_percent(coefficient: int, scale: int) -> str:
    value = format(Decimal(coefficient).scaleb(-scale), "f")
    if "." in value:
        value = value.rstrip("0").rstrip(".")
    return value or "0"


def _parsed_surface(surface: str | None, lane_type: str) -> int | str | None:
    if surface is None:
        return None
    parsed = parse_visible_financial_numeric_token_v1(surface)
    classification = parsed["classification"]
    if classification in {"BLANK_UNRESOLVED", "UNRESOLVED_TOKEN"}:
        return None
    coefficient = parsed["coefficient"]
    scale = parsed["scale"]
    percentage = parsed["percentage_mark_present"]
    if type(coefficient) is not int or type(scale) is not int or scale < 0:
        return None
    if lane_type == "MONEY":
        return coefficient if not percentage and scale == 0 else None
    if classification == "DASH_ZERO":
        return None
    return _canonical_percent(coefficient, scale)


def _cell(value: Mapping[str, Any], lane_type: str) -> dict[str, Any]:
    grouped: list[dict[str, Any]] = []
    for reader, field in (("PPOCRV6", "ppocrv6_surface"), ("VIETOCR", "vietocr_surface")):
        parsed = _parsed_surface(value[field], lane_type)
        if parsed is None:
            continue
        existing = next(
            (
                candidate
                for candidate in grouped
                if type(candidate["value"]) is type(parsed) and candidate["value"] == parsed
            ),
            None,
        )
        if existing is None:
            grouped.append({"readers": [reader], "value": parsed})
        else:
            existing["readers"].append(reader)
    if not grouped:
        status = "UNRESOLVED_NO_PARSEABLE_OBSERVED_VALUE"
        selected = None
        readers: list[str] = []
    elif len(grouped) == 1:
        selected = grouped[0]["value"]
        readers = list(grouped[0]["readers"])
        status = (
            "SELECTED_READER_CONSENSUS"
            if len(readers) == 2
            else "SELECTED_SINGLE_PARSEABLE_OBSERVATION"
        )
    else:
        status = "UNRESOLVED_READER_CONFLICT"
        selected = None
        readers = []
    return {
        "candidate_values": grouped,
        "lane_index": value["lane_index"],
        "lane_type": lane_type,
        "page_sequence": value["page_sequence"],
        "ppocrv6_surface": value["ppocrv6_surface"],
        "selected_readers": readers,
        "selected_value": selected,
        "source_line_index": value["source_line_index"],
        "status": status,
        "vietocr_surface": value["vietocr_surface"],
    }


def _missing_cell(*, lane_index: int, lane_type: str) -> dict[str, Any]:
    return {
        "candidate_values": [],
        "lane_index": lane_index,
        "lane_type": lane_type,
        "page_sequence": None,
        "ppocrv6_surface": None,
        "selected_readers": [],
        "selected_value": None,
        "source_line_index": None,
        "status": "UNRESOLVED_MISSING_SPARSE_CELL",
        "vietocr_surface": None,
    }


def _output_row(row: Mapping[str, Any], lane_types: Sequence[str]) -> dict[str, Any]:
    return {
        "cells": [_cell(cell, lane_types[cell["lane_index"]]) for cell in row["cells"]],
        "label_surfaces": [row["label_surface"]],
        "role": row["role"],
    }


def _output_total(total: Mapping[str, Any], lane_types: Sequence[str]) -> dict[str, Any]:
    return {
        "cells": [_cell(cell, lane_types[cell["lane_index"]]) for cell in total["cells"]],
        "label_surfaces": [total["label_surface"]],
    }


def _value_decimal(value: int | str) -> Decimal:
    return Decimal(value)


def _choices(cell: Mapping[str, Any]) -> list[tuple[int | str, list[str]]]:
    if cell["selected_value"] is not None:
        return [(cell["selected_value"], list(cell["selected_readers"]))]
    return [
        (candidate["value"], list(candidate["readers"])) for candidate in cell["candidate_values"]
    ]


def _evaluate_equation(
    components: Sequence[dict[str, Any]],
    target: dict[str, Any],
    *,
    equation_id: str,
    lane_index: int,
    lane_type: str,
    required: bool,
    target_kind: str,
    term_roles: Sequence[str],
) -> dict[str, Any]:
    cells = [*components, target]
    choices = [_choices(cell) for cell in cells]
    if any(not options for options in choices):
        return {
            "component_count": len(components),
            "equation_id": equation_id,
            "exact_observed_assignment_count": 0,
            "lane_index": lane_index,
            "lane_type": lane_type,
            "required_for_acceptance": required,
            "selected_component_values": [],
            "selected_sum": None,
            "selected_target": None,
            "status": "UNRESOLVED_MISSING_OBSERVED_VALUE",
            "target_kind": target_kind,
            "term_roles": list(term_roles),
        }
    exact: list[tuple[tuple[int | str, list[str]], ...]] = []
    for assignment in itertools.product(*choices):
        if sum((_value_decimal(item[0]) for item in assignment[:-1]), Decimal(0)) == _value_decimal(
            assignment[-1][0]
        ):
            exact.append(assignment)
    if len(exact) == 1:
        selected = exact[0]
        selected_conflict = False
        for cell, (observed_value, readers) in zip(cells, selected, strict=True):
            if cell["selected_value"] is None:
                selected_conflict = selected_conflict or len(cell["candidate_values"]) > 1
                cell["selected_value"] = observed_value
                cell["selected_readers"] = readers
                cell["status"] = "SELECTED_UNIQUE_OBSERVED_VALUE_BY_EXACT_EQUATION"
        component_values = [item[0] for item in selected[:-1]]
        selected_sum = sum((_value_decimal(item) for item in component_values), Decimal(0))
        display_sum: int | str = (
            int(selected_sum)
            if lane_type == "MONEY"
            else _canonical_percent(
                int(selected_sum.scaleb(max(0, -selected_sum.as_tuple().exponent))),
                max(0, -selected_sum.as_tuple().exponent),
            )
        )
        return {
            "component_count": len(components),
            "equation_id": equation_id,
            "exact_observed_assignment_count": 1,
            "lane_index": lane_index,
            "lane_type": lane_type,
            "required_for_acceptance": required,
            "selected_component_values": component_values,
            "selected_sum": display_sum,
            "selected_target": selected[-1][0],
            "status": (
                "EXACT_EQUATION_UNIQUELY_SELECTED_OBSERVED_CONFLICT"
                if selected_conflict
                else "EXACT_OBSERVED_EQUATION"
            ),
            "target_kind": target_kind,
            "term_roles": list(term_roles),
        }
    return {
        "component_count": len(components),
        "equation_id": equation_id,
        "exact_observed_assignment_count": len(exact),
        "lane_index": lane_index,
        "lane_type": lane_type,
        "required_for_acceptance": required,
        "selected_component_values": [],
        "selected_sum": None,
        "selected_target": None,
        "status": (
            "UNRESOLVED_MULTIPLE_EXACT_OBSERVED_ASSIGNMENTS"
            if exact
            else "VETOED_NO_EXACT_OBSERVED_ASSIGNMENT"
        ),
        "target_kind": target_kind,
        "term_roles": list(term_roles),
    }


def _cell_at(cells: Sequence[dict[str, Any]], lane: int) -> dict[str, Any] | None:
    return next((cell for cell in cells if cell["lane_index"] == lane), None)


def _margin_disposition(mode: str) -> str:
    return {
        "STANDALONE_AFTER_FIVE_GRADES": "EMIT_OBSERVED_1944_AS_ADDITIVE_CHILD",
        "INCLUDED_IN_747_VIA_5746": "NORMALIZE_747_AND_EMIT_OBSERVED_1944_VIA_5746_BRIDGE",
        "EXPLICITLY_EXCLUDED_FROM_CORE_VIA_FOOTNOTE": (
            "EMIT_OBSERVED_1944_OUTSIDE_PRINTED_FIVE_GRADE_TOTAL"
        ),
        "NOT_OBSERVED_DO_NOT_SYNTHESIZE": "DO_NOT_SYNTHESIZE_1944",
    }[mode]


def _horizontal(
    source: Mapping[str, Any], lane_types: Sequence[str]
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
    dict[str, Any] | None,
    dict[str, Any] | None,
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    rows = [_output_row(row, lane_types) for row in source["rows"]]
    total = _output_total(source["total"], lane_types)
    margin = (
        None
        if source["margin"] is None
        else {
            **_output_total(source["margin"], lane_types),
            "mapping_disposition": _margin_disposition(source["margin_mode"]),
            "mode": source["margin_mode"],
        }
    )
    parent = (
        None
        if source["parent_total"] is None
        else _output_total(source["parent_total"], lane_types)
    )
    checks = []
    for lane, lane_type in enumerate(lane_types):
        components = [_cell_at(row["cells"], lane) for row in rows]
        typed_components = [cell for cell in components if cell is not None]
        if margin is not None and source["margin_mode"] == "STANDALONE_AFTER_FIVE_GRADES":
            margin_cell = _cell_at(margin["cells"], lane)
            if margin_cell is not None:
                typed_components.append(margin_cell)
        checks.append(
            _evaluate_equation(
                typed_components,
                _cell_at(total["cells"], lane)
                or _missing_cell(lane_index=lane, lane_type=lane_type),
                equation_id=f"QUALITY_TABLE_TOTAL_LANE_{lane}",
                lane_index=lane,
                lane_type=lane_type,
                required=True,
                target_kind="QUALITY_TABLE_TOTAL",
                term_roles=[
                    *_ROLES,
                    *(
                        ["MARGIN_AND_SECURITIES_ADVANCE"]
                        if margin is not None
                        and source["margin_mode"] == "STANDALONE_AFTER_FIVE_GRADES"
                        and _cell_at(margin["cells"], lane) is not None
                        else []
                    ),
                ],
            )
        )
    if parent is not None:
        for lane, lane_type in enumerate(lane_types):
            parent_cell = _cell_at(parent["cells"], lane)
            total_cell = _cell_at(total["cells"], lane)
            if parent_cell is None or total_cell is None:
                continue
            components = [total_cell]
            term_roles = ["PRINTED_QUALITY_TOTAL"]
            if (
                margin is not None
                and source["margin_mode"] == "EXPLICITLY_EXCLUDED_FROM_CORE_VIA_FOOTNOTE"
                and (margin_cell := _cell_at(margin["cells"], lane)) is not None
            ):
                components.append(margin_cell)
                term_roles.append("MARGIN_AND_SECURITIES_ADVANCE")
            checks.append(
                _evaluate_equation(
                    components,
                    parent_cell,
                    equation_id=f"CUSTOMER_LOAN_PARENT_TOTAL_LANE_{lane}",
                    lane_index=lane,
                    lane_type=lane_type,
                    required=True,
                    target_kind="CUSTOMER_LOAN_PARENT_TOTAL",
                    term_roles=term_roles,
                )
            )
    return rows, total, parent, margin, [], checks


def _sparse(
    source: Mapping[str, Any], lane_types: Sequence[str]
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
    dict[str, Any] | None,
    dict[str, Any] | None,
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    blocks = []
    checks = []
    for block in source["sparse_blocks"]:
        column_types = ["MONEY"] * block["column_count"]
        rows = [_output_row(row, column_types) for row in block["rows"]]
        total = _output_total(block["total"], column_types)
        required_columns = {block["target_column_index"], block["total_column_index"]}
        for row in rows:
            row["missing_column_indices"] = [
                column
                for column in range(block["column_count"])
                if _cell_at(row["cells"], column) is None
            ]
        total["missing_column_indices"] = [
            column
            for column in range(block["column_count"])
            if _cell_at(total["cells"], column) is None
        ]
        for column in range(block["column_count"]):
            components = [_cell_at(row["cells"], column) for row in rows]
            target = _cell_at(total["cells"], column)
            complete = all(cell is not None for cell in components) and target is not None
            required = column in required_columns
            if not complete and not required:
                checks.append(
                    {
                        "component_count": sum(cell is not None for cell in components),
                        "equation_id": f"SPARSE_BLOCK_{block['block_ordinal']}_COLUMN_{column}",
                        "exact_observed_assignment_count": 0,
                        "lane_index": column,
                        "lane_type": "MONEY",
                        "required_for_acceptance": False,
                        "selected_component_values": [],
                        "selected_sum": None,
                        "selected_target": None,
                        "status": "NOT_EVALUATED_INCOMPLETE_SPARSE_SOURCE_COLUMN",
                        "target_kind": "SPARSE_BLOCK_COLUMN_TOTAL",
                        "term_roles": list(_ROLES),
                    }
                )
                continue
            typed_components = [
                cell if cell is not None else _missing_cell(lane_index=column, lane_type="MONEY")
                for cell in components
            ]
            checks.append(
                _evaluate_equation(
                    typed_components,
                    target or _missing_cell(lane_index=column, lane_type="MONEY"),
                    equation_id=f"SPARSE_BLOCK_{block['block_ordinal']}_COLUMN_{column}",
                    lane_index=column,
                    lane_type="MONEY",
                    required=required,
                    target_kind="SPARSE_BLOCK_COLUMN_TOTAL",
                    term_roles=_ROLES,
                )
            )
        blocks.append(
            {
                "block_ordinal": block["block_ordinal"],
                "column_count": block["column_count"],
                "rows": rows,
                "target_column_index": block["target_column_index"],
                "total": total,
                "total_column_index": block["total_column_index"],
            }
        )
    projected_rows = []
    for role_index, role in enumerate(_ROLES):
        cells = []
        labels = []
        for period_lane, block in enumerate(blocks):
            row = block["rows"][role_index]
            labels.extend(row["label_surfaces"])
            source_cell = _cell_at(row["cells"], block["target_column_index"])
            cell = (
                _missing_cell(lane_index=period_lane, lane_type="MONEY")
                if source_cell is None
                else {**canonical_clone_v1(source_cell), "lane_index": period_lane}
            )
            cells.append(cell)
        projected_rows.append({"cells": cells, "label_surfaces": labels, "role": role})
    projected_total_cells = []
    total_labels = []
    for period_lane, block in enumerate(blocks):
        total_labels.extend(block["total"]["label_surfaces"])
        source_cell = _cell_at(block["total"]["cells"], block["target_column_index"])
        projected_total_cells.append(
            _missing_cell(lane_index=period_lane, lane_type="MONEY")
            if source_cell is None
            else {**canonical_clone_v1(source_cell), "lane_index": period_lane}
        )
    projected_total = {"cells": projected_total_cells, "label_surfaces": total_labels}
    parent = (
        None
        if source["parent_total"] is None
        else _output_total(source["parent_total"], lane_types)
    )
    margin = (
        None
        if source["margin"] is None
        else {
            **_output_total(source["margin"], lane_types),
            "mapping_disposition": _margin_disposition(source["margin_mode"]),
            "mode": source["margin_mode"],
        }
    )
    if parent is not None:
        for lane, lane_type in enumerate(lane_types):
            parent_cell = _cell_at(parent["cells"], lane)
            total_cell = _cell_at(projected_total["cells"], lane)
            if parent_cell is None or total_cell is None:
                continue
            components = [total_cell]
            term_roles = ["PRINTED_QUALITY_TOTAL"]
            if (
                margin is not None
                and source["margin_mode"] == "EXPLICITLY_EXCLUDED_FROM_CORE_VIA_FOOTNOTE"
                and (margin_cell := _cell_at(margin["cells"], lane)) is not None
            ):
                components.append(margin_cell)
                term_roles.append("MARGIN_AND_SECURITIES_ADVANCE")
            checks.append(
                _evaluate_equation(
                    components,
                    parent_cell,
                    equation_id=f"CUSTOMER_LOAN_PARENT_TOTAL_LANE_{lane}",
                    lane_index=lane,
                    lane_type=lane_type,
                    required=True,
                    target_kind="CUSTOMER_LOAN_PARENT_TOTAL",
                    term_roles=term_roles,
                )
            )
    return projected_rows, projected_total, parent, margin, blocks, checks


def _all_cells(
    rows: Sequence[Mapping[str, Any]],
    total: Mapping[str, Any],
    parent: Mapping[str, Any] | None,
    margin: Mapping[str, Any] | None,
    blocks: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    result: list[Mapping[str, Any]] = [cell for row in rows for cell in row["cells"]]
    result.extend(total["cells"])
    if parent is not None:
        result.extend(parent["cells"])
    if margin is not None:
        result.extend(margin["cells"])
    for block in blocks:
        result.extend(cell for row in block["rows"] for cell in row["cells"])
        result.extend(block["total"]["cells"])
    return result


def _metrics(
    checks: Sequence[Mapping[str, Any]], cells: Sequence[Mapping[str, Any]]
) -> dict[str, int]:
    return {
        "accounting_check_count": len(checks),
        "exact_required_check_count": sum(
            check["required_for_acceptance"]
            and check["status"]
            in {
                "EXACT_OBSERVED_EQUATION",
                "EXACT_EQUATION_UNIQUELY_SELECTED_OBSERVED_CONFLICT",
            }
            for check in checks
        ),
        "observed_cell_count": len(cells),
        "selected_cell_count": sum(cell["selected_value"] is not None for cell in cells),
        "unique_equation_selection_cell_count": sum(
            cell["status"] == "SELECTED_UNIQUE_OBSERVED_VALUE_BY_EXACT_EQUATION" for cell in cells
        ),
        "unresolved_cell_count": sum(cell["selected_value"] is None for cell in cells),
        "unresolved_required_check_count": sum(
            check["required_for_acceptance"]
            and check["status"]
            not in {
                "EXACT_OBSERVED_EQUATION",
                "EXACT_EQUATION_UNIQUELY_SELECTED_OBSERVED_CONFLICT",
            }
            for check in checks
        ),
    }


def _required_mapping_cells(
    rows: Sequence[Mapping[str, Any]],
    total: Mapping[str, Any],
    parent: Mapping[str, Any] | None,
    margin: Mapping[str, Any] | None,
) -> list[Mapping[str, Any]]:
    cells = [cell for row in rows for cell in row["cells"]]
    cells.extend(total["cells"])
    if parent is not None:
        cells.extend(parent["cells"])
    if margin is not None:
        cells.extend(margin["cells"])
    return cells


def build_loan_quality_numeric_row_reconciliation_v1(source_input: Any) -> dict[str, Any]:
    """Reconcile one graph-selected loan-quality table from observed surfaces."""

    source = _input(source_input)
    lane_types = source["lane_types"]
    if source["layout_mode"] == _LAYOUT_HORIZONTAL:
        rows, total, parent, margin, blocks, checks = _horizontal(source, lane_types)
    else:
        rows, total, parent, margin, blocks, checks = _sparse(source, lane_types)
    required_checks_ok = all(
        not check["required_for_acceptance"]
        or check["status"]
        in {
            "EXACT_OBSERVED_EQUATION",
            "EXACT_EQUATION_UNIQUELY_SELECTED_OBSERVED_CONFLICT",
        }
        for check in checks
    )
    required_cells = _required_mapping_cells(rows, total, parent, margin)
    required_cells_ok = all(cell["selected_value"] is not None for cell in required_cells)
    unresolved_reasons = []
    if not required_checks_ok:
        unresolved_reasons.append("REQUIRED_EXACT_ACCOUNTING_EQUATION_NOT_CLOSED")
    if not required_cells_ok:
        unresolved_reasons.append("REQUIRED_MAPPING_CELL_NOT_RESOLVED_FROM_OBSERVED_SURFACE")
    status = (
        "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
        if not unresolved_reasons
        else "UNRESOLVED_OBSERVED_NUMERIC_RECONCILIATION"
    )
    all_cells = _all_cells(rows, total, parent, margin, blocks)
    material = {
        "accounting_checks": checks,
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_id": "lqnrrv1:input:" + canonical_json_sha256_v1(source),
        "lane_types": list(lane_types),
        "layout_mode": source["layout_mode"],
        "margin": margin,
        "margin_mode": source["margin_mode"],
        "metrics": _metrics(checks, all_cells),
        "parent_total": parent,
        "rows": rows,
        "source_id": source["source_id"],
        "sparse_blocks": blocks,
        "status": status,
        "total": total,
        "unresolved_reasons": unresolved_reasons,
    }
    return validate_loan_quality_numeric_row_reconciliation_v1(
        {
            **material,
            "result_id": "lqnrrv1:result:" + canonical_json_sha256_v1(material),
        }
    )


def _validate_result_cell(value: Any, *, allow_missing_locator: bool = False) -> None:
    if type(value) is not dict or set(value) != _RESULT_CELL_FIELDS:
        raise _error("loan-quality reconciled cell fields drifted")
    if (
        type(value["lane_index"]) is not int
        or value["lane_index"] < 0
        or value["lane_type"] not in {"MONEY", "PERCENT"}
        or type(value["candidate_values"]) is not list
        or type(value["selected_readers"]) is not list
        or any(reader not in {"PPOCRV6", "VIETOCR"} for reader in value["selected_readers"])
        or value["status"]
        not in {
            "SELECTED_READER_CONSENSUS",
            "SELECTED_SINGLE_PARSEABLE_OBSERVATION",
            "SELECTED_UNIQUE_OBSERVED_VALUE_BY_EXACT_EQUATION",
            "UNRESOLVED_MISSING_SPARSE_CELL",
            "UNRESOLVED_NO_PARSEABLE_OBSERVED_VALUE",
            "UNRESOLVED_READER_CONFLICT",
        }
    ):
        raise _error("loan-quality reconciled cell axis or status drifted")
    missing = value["status"] == "UNRESOLVED_MISSING_SPARSE_CELL"
    if missing:
        if (
            not allow_missing_locator
            or any(
                value[field] is not None
                for field in (
                    "page_sequence",
                    "ppocrv6_surface",
                    "selected_value",
                    "source_line_index",
                    "vietocr_surface",
                )
            )
            or value["candidate_values"]
            or value["selected_readers"]
        ):
            raise _error("missing sparse cell acquired source or numeric evidence")
    elif (
        type(value["page_sequence"]) is not int
        or value["page_sequence"] <= 0
        or (
            value["source_line_index"] is not None
            and (type(value["source_line_index"]) is not int or value["source_line_index"] < 0)
        )
        or (value["ppocrv6_surface"] is not None and type(value["ppocrv6_surface"]) is not str)
        or (value["vietocr_surface"] is not None and type(value["vietocr_surface"]) is not str)
        or (value["ppocrv6_surface"] is None and value["vietocr_surface"] is None)
    ):
        raise _error("loan-quality reconciled cell locator drifted")
    for candidate in value["candidate_values"]:
        if (
            type(candidate) is not dict
            or set(candidate) != {"readers", "value"}
            or type(candidate["readers"]) is not list
            or not candidate["readers"]
            or any(reader not in {"PPOCRV6", "VIETOCR"} for reader in candidate["readers"])
            or len(candidate["readers"]) != len(set(candidate["readers"]))
            or type(candidate["value"]) not in {int, str}
            or (value["lane_type"] == "MONEY" and type(candidate["value"]) is not int)
            or (value["lane_type"] == "PERCENT" and type(candidate["value"]) is not str)
        ):
            raise _error("loan-quality observed candidate record drifted")
    selected = value["selected_value"]
    if selected is not None and not any(
        type(candidate["value"]) is type(selected) and candidate["value"] == selected
        for candidate in value["candidate_values"]
    ):
        raise _error("loan-quality cell selected a value not emitted by either reader")
    selected_status = value["status"].startswith("SELECTED_")
    if selected_status != (selected is not None) or selected_status != bool(
        value["selected_readers"]
    ):
        raise _error("loan-quality cell selection status drifted")
    if selected is not None:
        candidate = next(
            candidate
            for candidate in value["candidate_values"]
            if type(candidate["value"]) is type(selected) and candidate["value"] == selected
        )
        if value["selected_readers"] != candidate["readers"]:
            raise _error("loan-quality cell selected reader binding drifted")
    if (
        (
            value["status"] == "SELECTED_READER_CONSENSUS"
            and (len(value["candidate_values"]) != 1 or len(value["selected_readers"]) != 2)
        )
        or (
            value["status"] == "SELECTED_SINGLE_PARSEABLE_OBSERVATION"
            and (len(value["candidate_values"]) != 1 or len(value["selected_readers"]) != 1)
        )
        or (
            value["status"] == "SELECTED_UNIQUE_OBSERVED_VALUE_BY_EXACT_EQUATION"
            and len(value["candidate_values"]) <= 1
        )
        or (
            value["status"] == "UNRESOLVED_NO_PARSEABLE_OBSERVED_VALUE"
            and value["candidate_values"]
        )
        or (value["status"] == "UNRESOLVED_READER_CONFLICT" and len(value["candidate_values"]) <= 1)
    ):
        raise _error("loan-quality cell candidate/status semantics drifted")


def _validate_labels(value: Any, label: str) -> None:
    if (
        type(value) is not list
        or not value
        or any(type(item) is not str or not item.strip() for item in value)
    ):
        raise _error(f"{label} surfaces drifted")


def _validate_result_row(
    value: Any,
    *,
    role: str,
    lane_types: Sequence[str],
    label_count: int,
    allow_missing: bool,
) -> None:
    if (
        type(value) is not dict
        or set(value) != {"cells", "label_surfaces", "role"}
        or value["role"] != role
        or len(value["label_surfaces"]) != label_count
        or type(value["cells"]) is not list
        or [cell.get("lane_index") for cell in value["cells"]] != list(range(len(lane_types)))
    ):
        raise _error("loan-quality reconciled row axis drifted")
    _validate_labels(value["label_surfaces"], "loan-quality row label")
    for lane, cell in enumerate(value["cells"]):
        _validate_result_cell(cell, allow_missing_locator=allow_missing)
        if cell["lane_type"] != lane_types[lane]:
            raise _error("loan-quality reconciled row typed lane drifted")


def _validate_result_total(
    value: Any,
    *,
    lane_types: Sequence[str],
    exact_axis: Sequence[int] | None,
    label_count: int,
    label: str,
    allow_missing: bool = False,
) -> None:
    if (
        type(value) is not dict
        or set(value) != {"cells", "label_surfaces"}
        or type(value["cells"]) is not list
        or len(value["label_surfaces"]) != label_count
    ):
        raise _error(f"{label} fields drifted")
    _validate_labels(value["label_surfaces"], f"{label} label")
    lanes = [cell.get("lane_index") for cell in value["cells"]]
    if lanes != sorted(set(lanes)) or (exact_axis is not None and lanes != list(exact_axis)):
        raise _error(f"{label} lane axis drifted")
    for cell in value["cells"]:
        _validate_result_cell(cell, allow_missing_locator=allow_missing)
        lane = cell["lane_index"]
        if lane >= len(lane_types) or cell["lane_type"] != lane_types[lane]:
            raise _error(f"{label} typed lane drifted")


def _validate_check(value: Any) -> None:
    if (
        type(value) is not dict
        or set(value) != _CHECK_FIELDS
        or type(value["component_count"]) is not int
        or value["component_count"] < 0
        or type(value["equation_id"]) is not str
        or not value["equation_id"]
        or type(value["exact_observed_assignment_count"]) is not int
        or value["exact_observed_assignment_count"] < 0
        or type(value["lane_index"]) is not int
        or value["lane_index"] < 0
        or value["lane_type"] not in {"MONEY", "PERCENT"}
        or type(value["required_for_acceptance"]) is not bool
        or type(value["selected_component_values"]) is not list
        or value["status"] not in _CHECK_STATUSES
        or type(value["target_kind"]) is not str
        or not value["target_kind"]
        or type(value["term_roles"]) is not list
        or any(type(role) is not str or not role for role in value["term_roles"])
    ):
        raise _error("loan-quality accounting check fields drifted")
    exact = value["status"] in _EXACT_CHECK_STATUSES
    if (
        (
            exact
            and (
                value["exact_observed_assignment_count"] != 1
                or len(value["selected_component_values"]) != value["component_count"]
                or len(value["term_roles"]) != value["component_count"]
                or type(value["selected_sum"]) not in {int, str}
                or type(value["selected_target"]) is not type(value["selected_sum"])
                or value["selected_target"] != value["selected_sum"]
            )
        )
        or (
            not exact
            and (
                value["selected_component_values"]
                or value["selected_sum"] is not None
                or value["selected_target"] is not None
            )
        )
        or (
            value["status"] == "NOT_EVALUATED_INCOMPLETE_SPARSE_SOURCE_COLUMN"
            and value["required_for_acceptance"]
        )
    ):
        raise _error("loan-quality accounting check equation semantics drifted")


def _validate_sparse_blocks(value: Any) -> None:
    if type(value) is not list or len(value) != 2:
        raise _error("loan-quality stacked result requires two sparse blocks")
    for ordinal, block in enumerate(value):
        if type(block) is not dict or set(block) != _SPARSE_BLOCK_FIELDS:
            raise _error("loan-quality stacked result block fields drifted")
        column_count = block["column_count"]
        target = block["target_column_index"]
        companion = block["total_column_index"]
        if (
            block["block_ordinal"] != ordinal
            or type(column_count) is not int
            or column_count < 2
            or type(target) is not int
            or type(companion) is not int
            or not 0 <= target < column_count
            or not 0 <= companion < column_count
            or target == companion
            or type(block["rows"]) is not list
            or len(block["rows"]) != len(_ROLES)
        ):
            raise _error("loan-quality stacked result block axis drifted")
        for role, row in zip(_ROLES, block["rows"], strict=True):
            if (
                type(row) is not dict
                or set(row) != {"cells", "label_surfaces", "missing_column_indices", "role"}
                or row["role"] != role
                or type(row["cells"]) is not list
                or type(row["missing_column_indices"]) is not list
            ):
                raise _error("loan-quality stacked result row fields drifted")
            _validate_labels(row["label_surfaces"], "loan-quality stacked row label")
            lanes = [cell.get("lane_index") for cell in row["cells"]]
            if lanes != sorted(set(lanes)) or row["missing_column_indices"] != [
                lane for lane in range(column_count) if lane not in lanes
            ]:
                raise _error("loan-quality stacked sparse row axis drifted")
            for cell in row["cells"]:
                _validate_result_cell(cell)
                if cell["lane_type"] != "MONEY" or cell["lane_index"] >= column_count:
                    raise _error("loan-quality stacked sparse row typed lane drifted")
        total = block["total"]
        if (
            type(total) is not dict
            or set(total) != {"cells", "label_surfaces", "missing_column_indices"}
            or type(total["cells"]) is not list
            or type(total["missing_column_indices"]) is not list
        ):
            raise _error("loan-quality stacked sparse total fields drifted")
        _validate_labels(total["label_surfaces"], "loan-quality stacked total label")
        total_lanes = [cell.get("lane_index") for cell in total["cells"]]
        if total_lanes != sorted(set(total_lanes)) or total["missing_column_indices"] != [
            lane for lane in range(column_count) if lane not in total_lanes
        ]:
            raise _error("loan-quality stacked sparse total axis drifted")
        for cell in total["cells"]:
            _validate_result_cell(cell)
            if cell["lane_type"] != "MONEY" or cell["lane_index"] >= column_count:
                raise _error("loan-quality stacked sparse total typed lane drifted")


def validate_loan_quality_numeric_row_reconciliation_v1(value: Any) -> dict[str, Any]:
    """Validate the closed result shape and its self-authenticating identity."""

    if (
        type(value) is not dict
        or set(value) != _RESULT_FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["input_id"]) is not str
        or not value["input_id"].startswith("lqnrrv1:input:")
        or type(value["source_id"]) is not str
        or not value["source_id"]
        or type(value["lane_types"]) is not list
        or tuple(value["lane_types"]) not in _SUPPORTED_LANES
        or value["layout_mode"] not in {_LAYOUT_HORIZONTAL, _LAYOUT_STACKED}
        or value["margin_mode"] not in MARGIN_PRESENTATION_MODES
        or type(value["rows"]) is not list
        or len(value["rows"]) != len(_ROLES)
        or type(value["accounting_checks"]) is not list
        or type(value["sparse_blocks"]) is not list
        or type(value["unresolved_reasons"]) is not list
        or value["status"]
        not in {
            "EXACT_OBSERVED_NUMERIC_RECONCILIATION",
            "UNRESOLVED_OBSERVED_NUMERIC_RECONCILIATION",
        }
    ):
        raise _error("loan-quality numeric reconciliation result fields drifted")
    lane_types = value["lane_types"]
    label_count = 1 if value["layout_mode"] == _LAYOUT_HORIZONTAL else 2
    for role, row in zip(_ROLES, value["rows"], strict=True):
        _validate_result_row(
            row,
            role=role,
            lane_types=lane_types,
            label_count=label_count,
            allow_missing=value["layout_mode"] == _LAYOUT_STACKED,
        )
    if value["total"] is None:
        raise _error("loan-quality reconciled result lost its quality total")
    _validate_result_total(
        value["total"],
        lane_types=lane_types,
        exact_axis=range(len(lane_types)),
        label_count=label_count,
        label="loan-quality table total",
        allow_missing=value["layout_mode"] == _LAYOUT_STACKED,
    )
    money_axis = [lane for lane, lane_type in enumerate(lane_types) if lane_type == "MONEY"]
    if value["parent_total"] is not None:
        _validate_result_total(
            value["parent_total"],
            lane_types=lane_types,
            exact_axis=None,
            label_count=1,
            label="customer-loan parent total",
        )
        if [cell["lane_index"] for cell in value["parent_total"]["cells"]] not in (
            money_axis,
            list(range(len(lane_types))),
        ):
            raise _error("customer-loan parent total result axis drifted")
    margin = value["margin"]
    if value["margin_mode"] == "NOT_OBSERVED_DO_NOT_SYNTHESIZE":
        if margin is not None:
            raise _error("unobserved result synthesized a margin row")
    elif (
        type(margin) is not dict
        or set(margin) != {"cells", "label_surfaces", "mapping_disposition", "mode"}
        or margin["mode"] != value["margin_mode"]
        or margin["mapping_disposition"] != _margin_disposition(value["margin_mode"])
    ):
        raise _error("observed result margin disposition drifted")
    else:
        _validate_labels(margin["label_surfaces"], "loan-quality margin label")
        margin_lanes = [cell.get("lane_index") for cell in margin["cells"]]
        if margin_lanes not in (money_axis, list(range(len(lane_types)))):
            raise _error("observed result margin lane axis drifted")
        for cell in margin["cells"]:
            _validate_result_cell(cell)
            if cell["lane_type"] != lane_types[cell["lane_index"]]:
                raise _error("observed result margin typed lane drifted")
    if (
        value["margin_mode"] == "EXPLICITLY_EXCLUDED_FROM_CORE_VIA_FOOTNOTE"
        and value["parent_total"] is None
    ):
        raise _error("excluded-footnote result lost its observed parent total")
    if value["layout_mode"] == _LAYOUT_HORIZONTAL:
        if value["sparse_blocks"] != []:
            raise _error("horizontal result acquired stacked sparse blocks")
    else:
        _validate_sparse_blocks(value["sparse_blocks"])
    for check in value["accounting_checks"]:
        _validate_check(check)
    if (
        type(value["metrics"]) is not dict
        or set(value["metrics"])
        != {
            "accounting_check_count",
            "exact_required_check_count",
            "observed_cell_count",
            "selected_cell_count",
            "unique_equation_selection_cell_count",
            "unresolved_cell_count",
            "unresolved_required_check_count",
        }
        or any(type(metric) is not int or metric < 0 for metric in value["metrics"].values())
    ):
        raise _error("loan-quality numeric reconciliation metrics drifted")
    all_cells = _all_cells(
        value["rows"], value["total"], value["parent_total"], margin, value["sparse_blocks"]
    )
    if not same_typed_json_v1(value["metrics"], _metrics(value["accounting_checks"], all_cells)):
        raise _error("loan-quality numeric reconciliation metrics do not replay from rows")
    required_checks_ok = all(
        not check["required_for_acceptance"] or check["status"] in _EXACT_CHECK_STATUSES
        for check in value["accounting_checks"]
    )
    required_cells_ok = all(
        cell["selected_value"] is not None
        for cell in _required_mapping_cells(
            value["rows"], value["total"], value["parent_total"], margin
        )
    )
    expected_reasons = []
    if not required_checks_ok:
        expected_reasons.append("REQUIRED_EXACT_ACCOUNTING_EQUATION_NOT_CLOSED")
    if not required_cells_ok:
        expected_reasons.append("REQUIRED_MAPPING_CELL_NOT_RESOLVED_FROM_OBSERVED_SURFACE")
    expected_status = (
        "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
        if not expected_reasons
        else "UNRESOLVED_OBSERVED_NUMERIC_RECONCILIATION"
    )
    if value["unresolved_reasons"] != expected_reasons or value["status"] != expected_status:
        raise _error("loan-quality numeric reconciliation status drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "lqnrrv1:result:" + canonical_json_sha256_v1(material):
        raise _error("loan-quality numeric reconciliation identity drifted")
    return canonical_clone_v1(value)


def validate_loan_quality_numeric_row_reconciliation_replay_v1(
    value: Any, source_input: Any
) -> dict[str, Any]:
    """Reject a result unless the exact observed input rebuilds it byte-for-byte."""

    persisted = validate_loan_quality_numeric_row_reconciliation_v1(value)
    rebuilt = build_loan_quality_numeric_row_reconciliation_v1(source_input)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("loan-quality numeric reconciliation does not replay exactly")
    return persisted
