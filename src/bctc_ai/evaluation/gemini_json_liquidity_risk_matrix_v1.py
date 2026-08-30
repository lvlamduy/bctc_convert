"""Liquidity maturity matrices over the shared exact risk-matrix engine.

Gemini remains a structure reader.  This layer only canonicalizes liquidity
maturity headers and core accounting rows inside an explicit, reset-fenced
liquidity owner.  Equations, schema projection, period, unit, continuation and
source-only retention remain deterministic local operations.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from bctc_ai.evaluation import gemini_json_equity_matrix_accounting_family_v1 as engine
from bctc_ai.evaluation.gemini_json_currency_risk_matrix_v1 import (
    coalesce_gemini_json_currency_risk_document_v1,
    compile_gemini_json_currency_risk_matrix_specs_v1,
)
from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import _money
from bctc_ai.evaluation.gemini_json_interest_rate_risk_matrix_v1 import (
    _normalized_header_members_v1,
    _owner_filtered_page_records_v1,
    classify_interest_rate_row_role_v1,
    interest_rate_document_reporting_date_receipt_v1,
    normalize_interest_rate_money_cell_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

LIQUIDITY_RISK_CLAIM_BOUNDARY = (
    "SELECTED_GEMINI_JSON_EXPLICIT_LIQUIDITY_OWNER_RESET_FENCED_MONEY_"
    "MATURITY_MATRIX_CORE_ROWS_EXACT_ASSET_MINUS_LIABILITY_EQUALS_NET_GAP_"
    "SOURCE_ONLY_BUCKETS_RETAINED_NO_BANK_FILE_PAGE_VALUE_ROUTING"
)


class GeminiJsonLiquidityRiskMatrixV1Error(ValueError):
    """The liquidity matrix specification or source axis is invalid."""


def _error(message: str) -> GeminiJsonLiquidityRiskMatrixV1Error:
    return GeminiJsonLiquidityRiskMatrixV1Error(message)


_INVALID_MONEY = object()
_CORE_ROW_ROLE_AXIS = ("ASSET_TOTAL", "LIABILITY_TOTAL", "NET_LIQUIDITY_GAP")


def _coefficient_v1(value: Any) -> int | None | object:
    normalized, _state = normalize_interest_rate_money_cell_v1(value)
    if normalized is None:
        return None
    try:
        return _money(normalized)["coefficient"]
    except (TypeError, ValueError):
        return _INVALID_MONEY


def _offset_values_v1(
    values: list[Any], offset: int, source_span: list[str] | None
) -> list[Any] | None:
    if offset == 0:
        return canonical_clone_v1(values) if source_span is None else None
    if (
        type(source_span) is not list
        or len(source_span) != 2
        or any(
            type(column_id) is not str or not column_id.startswith("c") for column_id in source_span
        )
    ):
        return None
    try:
        start, end = (int(column_id[1:]) - 1 for column_id in source_span)
    except ValueError:
        return None
    if not 0 <= start < end < len(values):
        return None
    effective = canonical_clone_v1(values)
    if offset == 1:
        if _coefficient_v1(values[end]) is not None:
            return None
        effective[start : end + 1] = [None, *canonical_clone_v1(values[start:end])]
        return effective
    if offset == -1:
        if _coefficient_v1(values[start]) is not None:
            return None
        effective[start : end + 1] = [*canonical_clone_v1(values[start + 1 : end + 1]), None]
        return effective
    raise _error("liquidity row offset is outside the bounded projector")


def _aligned_equations_exact_v1(
    *, values_by_role: Mapping[str, list[Any]], mapped_column_indices: list[int]
) -> bool:
    if (
        set(values_by_role) != set(_CORE_ROW_ROLE_AXIS)
        or not mapped_column_indices
        or mapped_column_indices != sorted(set(mapped_column_indices))
        or any(type(axis) is not list for axis in values_by_role.values())
    ):
        return False
    column_counts = {len(axis) for axis in values_by_role.values()}
    if len(column_counts) != 1 or any(
        index < 0 or index >= next(iter(column_counts)) for index in mapped_column_indices
    ):
        return False
    for column_index in mapped_column_indices:
        values = {
            role: _coefficient_v1(axis[column_index]) for role, axis in values_by_role.items()
        }
        if any(value is _INVALID_MONEY for value in values.values()):
            return False
        unknown = [role for role, value in values.items() if value is None]
        if not unknown:
            if values["ASSET_TOTAL"] - values["LIABILITY_TOTAL"] != values["NET_LIQUIDITY_GAP"]:
                return False
            continue
        if len(unknown) != 1:
            return False
        role = unknown[0]
        if role == "ASSET_TOTAL":
            solution = values["NET_LIQUIDITY_GAP"] + values["LIABILITY_TOTAL"]
        elif role == "LIABILITY_TOTAL":
            solution = values["ASSET_TOTAL"] - values["NET_LIQUIDITY_GAP"]
        else:
            solution = values["ASSET_TOTAL"] - values["LIABILITY_TOTAL"]
        if solution != 0:
            return False
    return True


def _alignment_candidate_projections_v1(
    *, raw_values_by_role: Mapping[str, list[Any]], mapped_column_indices: list[int]
) -> list[dict[str, dict[str, Any]]]:
    """Enumerate the unique minimum-span projections from the raw source axis."""

    if not _aligned_equations_exact_v1(
        values_by_role=raw_values_by_role,
        mapped_column_indices=mapped_column_indices,
    ):
        if (
            set(raw_values_by_role) != set(_CORE_ROW_ROLE_AXIS)
            or not mapped_column_indices
            or len({len(axis) for axis in raw_values_by_role.values()}) != 1
        ):
            return []
    identity = {
        role: {"source_offset": 0, "source_span_column_ids": None} for role in _CORE_ROW_ROLE_AXIS
    }
    if _aligned_equations_exact_v1(
        values_by_role=raw_values_by_role,
        mapped_column_indices=mapped_column_indices,
    ):
        return [identity]
    candidate_projections: list[dict[str, dict[str, Any]]] = []
    column_count = len(next(iter(raw_values_by_role.values())))
    for shifted_role in _CORE_ROW_ROLE_AXIS:
        for start in range(column_count - 1):
            for end in range(start + 1, column_count):
                span = [f"c{start + 1}", f"c{end + 1}"]
                for offset in (-1, 1):
                    values = _offset_values_v1(raw_values_by_role[shifted_role], offset, span)
                    if values is None:
                        continue
                    projected = canonical_clone_v1(raw_values_by_role)
                    projected[shifted_role] = values
                    if _aligned_equations_exact_v1(
                        values_by_role=projected,
                        mapped_column_indices=mapped_column_indices,
                    ):
                        candidate = canonical_clone_v1(identity)
                        candidate[shifted_role] = {
                            "source_offset": offset,
                            "source_span_column_ids": span,
                        }
                        candidate_projections.append(candidate)
    if not candidate_projections:
        return []
    minimum_affected_span = min(
        sum(
            0
            if projection["source_span_column_ids"] is None
            else int(projection["source_span_column_ids"][1][1:])
            - int(projection["source_span_column_ids"][0][1:])
            + 1
            for projection in candidate.values()
        )
        for candidate in candidate_projections
    )
    return [
        candidate
        for candidate in candidate_projections
        if sum(
            0
            if projection["source_span_column_ids"] is None
            else int(projection["source_span_column_ids"][1][1:])
            - int(projection["source_span_column_ids"][0][1:])
            + 1
            for projection in candidate.values()
        )
        == minimum_affected_span
    ]


def build_liquidity_row_alignment_receipt_v1(
    table: Mapping[str, Any], *, classification: Mapping[str, Any]
) -> dict[str, Any]:
    """Project a uniquely shifted core row while preserving every visible value."""

    rows = table.get("rows")
    if type(rows) is not list or not rows:
        raise _error("liquidity alignment source rows are absent")
    core_axis = [
        item
        for item in classification["component_axis"]
        if item["kind"] == "CORE_ROW"
        and item["role"] in {"ASSET_TOTAL", "LIABILITY_TOTAL", "NET_LIQUIDITY_GAP"}
    ]
    role_axis = list(_CORE_ROW_ROLE_AXIS)
    by_role = {item["role"]: item for item in core_axis}
    mapped_column_indices = [
        item["source_order"] - 1
        for item in classification["column_axis"]
        if item["kind"] == "MAPPED_CURRENCY"
    ]
    raw_values_by_role = {
        role: canonical_clone_v1(rows[int(by_role[role]["row_id"][1:]) - 1]["values_exact"])
        for role in role_axis
        if role in by_role
    }
    raw_axis = [
        {
            "raw_values_exact": canonical_clone_v1(raw_values_by_role[role]),
            "role": role,
            "row_id": by_role[role]["row_id"],
        }
        for role in role_axis
        if role in by_role
    ]
    identity = {role: {"source_offset": 0, "source_span_column_ids": None} for role in role_axis}
    candidate_projections = _alignment_candidate_projections_v1(
        raw_values_by_role=raw_values_by_role,
        mapped_column_indices=mapped_column_indices,
    )
    selected_projection = candidate_projections[0] if len(candidate_projections) == 1 else identity
    effective_rows = []
    for raw in raw_axis:
        projection = selected_projection[raw["role"]]
        effective = _offset_values_v1(
            raw["raw_values_exact"],
            projection["source_offset"],
            projection["source_span_column_ids"],
        )
        if effective is None:
            raise _error("liquidity selected row alignment drops a visible value")
        effective_rows.append(
            {
                **raw,
                "effective_values_exact": effective,
                **projection,
            }
        )
    status = "NO_UNIQUE_EXACT_ALIGNMENT"
    if len(candidate_projections) == 1:
        status = (
            "RAW_AXIS_EXACT"
            if all(projection["source_offset"] == 0 for projection in selected_projection.values())
            else "UNIQUE_BOUNDARY_BLANK_OFFSET_EXACT"
        )
    material = {
        "candidate_offset_axes": [
            [[role, projection[role]] for role in role_axis] for projection in candidate_projections
        ],
        "effective_rows": effective_rows,
        "mapped_column_ids": [f"c{index + 1}" for index in mapped_column_indices],
        "raw_row_axis_sha256": canonical_json_sha256_v1(raw_axis),
        "rule": (
            "PRESERVE_VISIBLE_SEQUENCE_ONE_CORE_ROW_CONTIGUOUS_BOUNDARY_BLANK_SHIFT_"
            "MINUS_ONE_OR_PLUS_ONE_UNIQUE_MINIMUM_AFFECTED_SPAN_ALL_MAPPED_"
            "ASSET_MINUS_LIABILITY_EQUALS_NET"
        ),
        "status": status,
    }
    return {
        **material,
        "alignment_receipt_id": "gjlrmv1:alignment:" + canonical_json_sha256_v1(material),
    }


def validate_liquidity_row_alignment_receipt_v1(value: Any) -> dict[str, Any]:
    fields = {
        "alignment_receipt_id",
        "candidate_offset_axes",
        "effective_rows",
        "mapped_column_ids",
        "raw_row_axis_sha256",
        "rule",
        "status",
    }
    role_axis = list(_CORE_ROW_ROLE_AXIS)
    if (
        type(value) is not dict
        or set(value) != fields
        or value.get("status")
        not in {
            "NO_UNIQUE_EXACT_ALIGNMENT",
            "RAW_AXIS_EXACT",
            "UNIQUE_BOUNDARY_BLANK_OFFSET_EXACT",
        }
        or value.get("rule")
        != (
            "PRESERVE_VISIBLE_SEQUENCE_ONE_CORE_ROW_CONTIGUOUS_BOUNDARY_BLANK_SHIFT_"
            "MINUS_ONE_OR_PLUS_ONE_UNIQUE_MINIMUM_AFFECTED_SPAN_ALL_MAPPED_"
            "ASSET_MINUS_LIABILITY_EQUALS_NET"
        )
        or type(value.get("candidate_offset_axes")) is not list
        or type(value.get("effective_rows")) is not list
        or type(value.get("mapped_column_ids")) is not list
        or len(value["effective_rows"]) != len(role_axis)
    ):
        raise _error("liquidity row alignment receipt is invalid")
    raw_axis = []
    effective_by_role = {}
    for expected_role, row in zip(role_axis, value["effective_rows"], strict=True):
        if (
            type(row) is not dict
            or set(row)
            != {
                "effective_values_exact",
                "raw_values_exact",
                "role",
                "row_id",
                "source_offset",
                "source_span_column_ids",
            }
            or row.get("role") != expected_role
            or type(row.get("row_id")) is not str
            or type(row.get("raw_values_exact")) is not list
            or type(row.get("effective_values_exact")) is not list
            or len(row["raw_values_exact"]) != len(row["effective_values_exact"])
            or row.get("source_offset") not in {-1, 0, 1}
        ):
            raise _error("liquidity row alignment row projection is invalid")
        expected = _offset_values_v1(
            row["raw_values_exact"],
            row["source_offset"],
            row["source_span_column_ids"],
        )
        if expected is None or not same_typed_json_v1(expected, row["effective_values_exact"]):
            raise _error("liquidity row alignment changes the visible value sequence")
        raw_axis.append(
            {
                "raw_values_exact": canonical_clone_v1(row["raw_values_exact"]),
                "role": row["role"],
                "row_id": row["row_id"],
            }
        )
        effective_by_role[row["role"]] = row["effective_values_exact"]
    try:
        mapped_indices = [int(column_id[1:]) - 1 for column_id in value["mapped_column_ids"]]
    except (AttributeError, TypeError, ValueError) as exc:
        raise _error("liquidity mapped alignment column axis is invalid") from exc
    if (
        not mapped_indices
        or len(mapped_indices) != len(set(mapped_indices))
        or mapped_indices != sorted(mapped_indices)
        or any(index < 0 for index in mapped_indices)
        or value["mapped_column_ids"] != [f"c{index + 1}" for index in mapped_indices]
    ):
        raise _error("liquidity mapped alignment column axis is invalid")
    candidate_axes = value["candidate_offset_axes"]
    raw_by_role = {item["role"]: item["raw_values_exact"] for item in raw_axis}
    for axis in candidate_axes:
        axis_by_role = {}
        if type(axis) is list:
            for entry in axis:
                if type(entry) is not list or len(entry) != 2 or type(entry[0]) is not str:
                    raise _error("liquidity row alignment candidate axis is invalid")
                axis_by_role[entry[0]] = entry[1]
        if (
            type(axis) is not list
            or axis != [[role, axis_by_role.get(role)] for role in role_axis]
            or any(
                type(projection) is not dict
                or set(projection) != {"source_offset", "source_span_column_ids"}
                or projection["source_offset"] not in {-1, 0, 1}
                for _role, projection in axis
            )
        ):
            raise _error("liquidity row alignment candidate axis is invalid")
        projected_by_role = {}
        for role, projection in axis:
            projected = _offset_values_v1(
                raw_by_role[role],
                projection["source_offset"],
                projection["source_span_column_ids"],
            )
            if projected is None:
                raise _error("liquidity candidate alignment drops a visible value")
            projected_by_role[role] = projected
        if not _aligned_equations_exact_v1(
            values_by_role=projected_by_role,
            mapped_column_indices=mapped_indices,
        ):
            raise _error("liquidity candidate alignment equations do not close")
    expected_candidate_axes = [
        [[role, projection[role]] for role in role_axis]
        for projection in _alignment_candidate_projections_v1(
            raw_values_by_role=raw_by_role,
            mapped_column_indices=mapped_indices,
        )
    ]
    if not same_typed_json_v1(candidate_axes, expected_candidate_axes):
        raise _error("liquidity alignment candidate frontier is not exhaustive")
    selected_axis = [
        [
            row["role"],
            {
                "source_offset": row["source_offset"],
                "source_span_column_ids": row["source_span_column_ids"],
            },
        ]
        for row in value["effective_rows"]
    ]
    identity_axis = [
        [role, {"source_offset": 0, "source_span_column_ids": None}] for role in role_axis
    ]
    if (
        (
            value["status"] == "RAW_AXIS_EXACT"
            and (candidate_axes != [identity_axis] or selected_axis != candidate_axes[0])
        )
        or (
            value["status"] == "UNIQUE_BOUNDARY_BLANK_OFFSET_EXACT"
            and (
                len(candidate_axes) != 1
                or selected_axis != candidate_axes[0]
                or all(projection["source_offset"] == 0 for _role, projection in selected_axis)
            )
        )
        or (
            value["status"] == "NO_UNIQUE_EXACT_ALIGNMENT"
            and (len(candidate_axes) == 1 or selected_axis != identity_axis)
        )
    ):
        raise _error("liquidity row alignment disposition is inconsistent")
    if value.get("raw_row_axis_sha256") != canonical_json_sha256_v1(raw_axis) or value.get(
        "alignment_receipt_id"
    ) != "gjlrmv1:alignment:" + canonical_json_sha256_v1(
        {key: item for key, item in value.items() if key != "alignment_receipt_id"}
    ):
        raise _error("liquidity row alignment identity drifted")
    if value["status"] != "NO_UNIQUE_EXACT_ALIGNMENT" and not _aligned_equations_exact_v1(
        values_by_role=effective_by_role, mapped_column_indices=mapped_indices
    ):
        raise _error("liquidity aligned row equations do not close")
    return canonical_clone_v1(value)


def _duration_roles_v1(surface: str) -> set[str]:
    """Inventory every maturity semantic instead of choosing the last match."""

    surface = re.sub(r"(?<=\d)t\b", " t", surface)
    if "tai ngay" in surface or "ket thuc ngay" in surface:
        return set()
    roles: set[str] = set()
    pair_roles = {
        (1, 3): "WITHIN_1_3M",
        (3, 6): "WITHIN_3_6M_SOURCE",
        (3, 12): "WITHIN_3_12M",
        (4, 12): "WITHIN_3_12M",
        (5, 12): "WITHIN_3_12M",
        (6, 12): "WITHIN_6_12M_SOURCE",
    }
    for left, right in re.findall(
        r"0*(\d+)\s*(?:thang|t)?\s*(?:den|-)\s*0*(\d+)\s*(?:thang|t)\b",
        surface,
    ):
        role = pair_roles.get((int(left), int(right)))
        if role is not None:
            roles.add(role)
    numbers = [int(value) for value in re.findall(r"\d+", surface)]
    if (
        re.search(r"\btu(?:\s+tren)?\b", surface)
        and ("thang" in surface or re.search(r"\bt\b", surface))
        and len(numbers) == 2
    ):
        role = pair_roles.get(tuple(numbers))
        if role is not None:
            roles.add(role)
    for left, right in re.findall(r"0*(\d+)\s*nam\s*(?:den|-)\s*0*(\d+)\s*nam\b", surface):
        if (int(left), int(right)) == (1, 5):
            roles.add("WITHIN_1_5Y")
    if re.search(r"\btu(?:\s+tren)?\b", surface) and "nam" in surface and numbers == [1, 5]:
        roles.add("WITHIN_1_5Y")
    if re.search(r"\b(?:duoi|den|trong vong)\s+0*1\s*(?:thang|t)\b", surface) or re.search(
        r"\b0*1\s*(?:thang|t)\s+tro xuong\b", surface
    ):
        roles.add("WITHIN_LE1M")
    for segment in re.split(r"[/;|\n]", surface):
        numbers = [int(value) for value in re.findall(r"\d+", segment)]
        if "nam" in segment and numbers == [5] and re.search(r"\btren\b", segment):
            roles.add("WITHIN_GT5Y")
        if (
            ("thang" in segment or re.search(r"\bt\b", segment))
            and numbers == [1]
            and any(marker in segment for marker in ("duoi", "den", "trong vong", "tro xuong"))
        ):
            roles.add("WITHIN_LE1M")
    return roles


def _duration_role_v1(surface: str) -> str | None:
    roles = _duration_roles_v1(surface)
    return sorted(roles)[0] if len(roles) == 1 else None


def classify_liquidity_column_role_v1(
    column: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> tuple[str | None, str | None, list[str]]:
    """Inventory one header without preferring one of conflicting semantics."""

    members = _normalized_header_members_v1(column, compiled_specs=compiled_specs)
    if not members:
        return None, None, []
    roles: set[str] = set()
    combined = " ".join(members)
    if any(re.search(r"\bqua han\b", member) for member in members):
        if re.search(r"\btren\s+0*3\s*thang\b", combined):
            roles.add("OVERDUE_GT3M")
        if re.search(r"\b(?:den|duoi|khong qua)\s+0*3\s*thang\b", combined):
            roles.add("OVERDUE_LE3M")
        if not roles:
            roles.add("OVERDUE")
        if any(re.search(r"\btrong han\b", member) for member in members):
            roles.update(_duration_roles_v1(combined))
    else:
        for member in members:
            member_roles = _duration_roles_v1(member)
            if member_roles:
                roles.update(member_roles)
                continue
            if member == "tong" or member.startswith("tong cong"):
                roles.add("TOTAL")
    matches = sorted(roles)
    if len(matches) != 1:
        return None, None, matches
    role = matches[0]
    mapped = role in compiled_specs["currency_role_aliases_by_role"]
    source_only = role in compiled_specs["source_only_currency_aliases_by_role"]
    if mapped == source_only:
        return None, None, matches
    return role, "MAPPED_CURRENCY" if mapped else "SOURCE_ONLY_CURRENCY", matches


def classify_liquidity_row_role_v1(
    value: Any, *, aliases_by_role: Mapping[str, Any]
) -> tuple[str | None, list[str]]:
    """Bind only declared asset, liability and net-liquidity source rows."""

    role, matches = classify_interest_rate_row_role_v1(value, aliases_by_role=aliases_by_role)
    if role is not None or matches:
        return role, matches
    folded = engine._normalized(value)
    if "chenh" in folded and "thanh khoan" in folded:
        return "NET_LIQUIDITY_GAP", ["NET_LIQUIDITY_GAP"]
    return None, []


def compile_gemini_json_liquidity_risk_matrix_specs_v1(
    *, topology: Mapping[str, Any], evaluation_spec: Any, schema_binding_spec: Any
) -> dict[str, Any]:
    """Compile a liquidity triplet onto the shared exact matrix core."""

    if topology.get("family_id") != "LIQUIDITY_RISK":
        raise _error("liquidity matrix topology family is invalid")
    compiled = compile_gemini_json_currency_risk_matrix_specs_v1(
        topology=topology,
        evaluation_spec=evaluation_spec,
        schema_binding_spec=schema_binding_spec,
    )
    compiled["claim_boundary"] = LIQUIDITY_RISK_CLAIM_BOUNDARY
    compiled["liquidity_risk_mode"] = True
    return compiled


def coalesce_gemini_json_liquidity_risk_document_v1(
    *, page_records: Any, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Coalesce only maturity matrices under the latest liquidity owner."""

    filtered = _owner_filtered_page_records_v1(page_records, compiled_specs=compiled_specs)
    return coalesce_gemini_json_currency_risk_document_v1(
        page_records=filtered, compiled_specs=compiled_specs
    )


__all__ = [
    "LIQUIDITY_RISK_CLAIM_BOUNDARY",
    "classify_liquidity_column_role_v1",
    "classify_liquidity_row_role_v1",
    "coalesce_gemini_json_liquidity_risk_document_v1",
    "compile_gemini_json_liquidity_risk_matrix_specs_v1",
    "interest_rate_document_reporting_date_receipt_v1",
    "normalize_interest_rate_money_cell_v1",
]
