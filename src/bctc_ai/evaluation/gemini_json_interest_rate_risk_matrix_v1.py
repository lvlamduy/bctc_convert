"""Interest-rate repricing matrices over the shared exact risk-matrix engine.

The accounting closure is the same asset-minus-liability/state graph used by
the currency matrix.  Retrieval is different: maturity labels also occur in
liquidity-risk and percentage tables, so only money tables inside the latest
explicit interest-rate owner/reset interval are allowed into the exhaustive
matrix inventory.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from bctc_ai.evaluation import gemini_json_equity_matrix_accounting_family_v1 as engine
from bctc_ai.evaluation.gemini_json_currency_risk_matrix_v1 import (
    classify_gemini_json_currency_risk_matrix_table_v1,
    coalesce_gemini_json_currency_risk_document_v1,
    compile_gemini_json_currency_risk_matrix_specs_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
)

INTEREST_RATE_RISK_CLAIM_BOUNDARY = (
    "SELECTED_GEMINI_JSON_EXPLICIT_INTEREST_RATE_OWNER_RESET_FENCED_MONEY_"
    "REPRICING_MATRIX_CORE_ROWS_EXACT_STATE_EQUATIONS_SOURCE_ONLY_BUCKETS_"
    "RETAINED_NO_BANK_FILE_PAGE_VALUE_ROUTING"
)


class GeminiJsonInterestRateRiskMatrixV1Error(ValueError):
    """The interest-rate matrix specification or owner interval is invalid."""


def _error(message: str) -> GeminiJsonInterestRateRiskMatrixV1Error:
    return GeminiJsonInterestRateRiskMatrixV1Error(message)


_ACCOUNTING_NUMBER = re.compile(
    r"\(\s*\d+(?:[., ]\d+)*\s*\)|"
    r"(?<!\d)-\s*\d+(?:[., ]\d+)*(?!\d)|"
    r"(?<!\d)\d+(?:[., ]\d+)*(?!\d)"
)
_DASH_GLYPHS = frozenset("-–—−")


def normalize_interest_rate_money_cell_v1(value: Any) -> tuple[Any, str | None]:
    """Project common provider noise to one unambiguous MONEY observation."""

    if type(value) is not str:
        return value, None
    body = value.strip()
    if body.casefold() == "null":
        return None, "NORMALIZED_TEXT_NULL_BLANK"
    matches = list(_ACCOUNTING_NUMBER.finditer(body))
    if len(matches) == 1:
        token = matches[0].group(0).strip()
        if matches[0].span() != (0, len(body)):
            return token, "NORMALIZED_UNIQUE_NOISY_SIGNED_INTEGER"
        return value, None
    if not matches and not re.search(r"\d", body) and any(glyph in body for glyph in _DASH_GLYPHS):
        return "-", "NORMALIZED_NOISY_DASH_ZERO"
    return value, None


def _normalized_header_members_v1(
    column: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> list[str]:
    unit_aliases = sorted(compiled_specs["unit_binding_by_alias"], key=len, reverse=True)
    members = []
    for raw in engine._header_members(column):
        folded = engine._normalized(raw)
        for alias in unit_aliases:
            folded = re.sub(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", " ", folded)
        folded = " ".join(folded.split())
        if folded:
            members.append(folded)
    return members


def _duration_role_v1(surface: str) -> str | None:
    surface = re.sub(r"(?<=\d)t\b", " t", surface)
    if "tai ngay" in surface or "ket thuc ngay" in surface:
        return None
    numbers = [int(value) for value in re.findall(r"\d+", surface)]
    if "nam" in surface:
        if "tren" in surface and numbers == [5]:
            return "WITHIN_GT5Y"
        if len(numbers) >= 2 and numbers[-2:] == [1, 5]:
            return "WITHIN_1_5Y"
        if "tren" in surface and numbers == [1]:
            return "WITHIN_GT1Y"
        return None
    if "thang" not in surface and not re.search(r"\bt\b", surface):
        return None
    if "tren" in surface and numbers == [12]:
        return "WITHIN_GT1Y"
    if (
        numbers
        and set(numbers) == {1}
        and any(marker in surface for marker in ("duoi", "den", "trong vong"))
    ):
        return "WITHIN_LE1M"
    distinct = []
    for value in numbers:
        if not distinct or distinct[-1] != value:
            distinct.append(value)
    pair = tuple(distinct[-2:]) if len(distinct) >= 2 else None
    return {
        (1, 3): "WITHIN_1_3M",
        (3, 6): "WITHIN_3_6M",
        (6, 12): "WITHIN_6_12M",
    }.get(pair)


def _duration_roles_v1(surface: str) -> set[str]:
    parts = [part.strip() for part in re.split(r"\s*(?:/|;|\||\bva\b)\s*", surface) if part.strip()]
    roles = {role for part in parts if (role := _duration_role_v1(part)) is not None}
    numbers = [int(value) for value in re.findall(r"\d+", surface)]
    if len(numbers) > 2 and ("thang" in surface or re.search(r"\bt\b", surface)):
        month_pairs = {
            (1, 3): "WITHIN_1_3M",
            (3, 6): "WITHIN_3_6M",
            (6, 12): "WITHIN_6_12M",
        }
        roles.update(
            month_pairs[pair]
            for pair in zip(numbers, numbers[1:], strict=False)
            if pair in month_pairs
        )
    if len(numbers) > 2 and "nam" in surface:
        roles.update(
            "WITHIN_1_5Y" for pair in zip(numbers, numbers[1:], strict=False) if pair == (1, 5)
        )
    return roles


def classify_interest_rate_column_role_v1(
    column: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> tuple[str | None, str | None, list[str]]:
    """Canonicalize equivalent maturity spellings without enumerating layouts."""

    members = _normalized_header_members_v1(column, compiled_specs=compiled_specs)
    if not members:
        return None, None, []
    joined = " ".join(members)
    roles = []
    overdue = any(re.search(r"\bqua han\b", member) for member in members)
    if overdue:
        duration_roles = {role for member in members for role in _duration_roles_v1(member)}
        if "WITHIN_3_6M" in duration_roles or any(
            re.search(r"\btren 0*3 thang\b", member) for member in members
        ):
            roles.append("OVERDUE_GT3M_SOURCE")
        elif "WITHIN_1_3M" in duration_roles or any(
            re.search(r"\b(?:den|duoi) 0*3 thang\b", member) for member in members
        ):
            roles.append("OVERDUE_LE3M_SOURCE")
        else:
            roles.append("OVERDUE")
    elif re.search(
        r"\bkhong\b.*\b(?:chiu|nhay cam|huong|sinh|bi dinh gia lai|anh huong thay doi)\b.*\blai",
        joined,
    ):
        roles.append("NO_INTEREST")
    else:
        duration_roles = {role for member in members for role in _duration_roles_v1(member)}
        roles.extend(sorted(duration_roles))
        if not duration_roles and any(
            member == "tong" or member.startswith("tong cong") for member in members
        ):
            roles.append("TOTAL")
    roles = sorted(set(roles))
    if len(roles) != 1:
        return None, None, roles
    role = roles[0]
    mapped = role in compiled_specs["currency_role_aliases_by_role"]
    source_only = role in compiled_specs["source_only_currency_aliases_by_role"]
    if mapped == source_only:
        return None, None, roles
    return (
        role,
        "MAPPED_CURRENCY" if mapped else "SOURCE_ONLY_CURRENCY",
        roles,
    )


def classify_interest_rate_row_role_v1(
    value: Any, *, aliases_by_role: Mapping[str, Any]
) -> tuple[str | None, list[str]]:
    """Bind only semantic core rows; ambiguous bare gaps are resolved later."""

    folded = engine._normalized(value)
    alias_tokens = folded.split()
    while alias_tokens and alias_tokens[-1].isdigit():
        alias_tokens.pop()
    alias_surface = " ".join(alias_tokens)
    direct = []
    for role, aliases in aliases_by_role.items():
        if engine._valuation_label_matches_v1(alias_surface, aliases):
            direct.append(role)
    if len(set(direct)) == 1:
        return direct[0], sorted(set(direct))
    if len(set(direct)) > 1:
        return None, sorted(set(direct))
    off_balance_commitment = "cam ket ngoai bang" in folded and (
        "nhay cam" in folded or "lai suat" in folded or re.search(r"\bls\b", folded)
    )
    if off_balance_commitment:
        return "STATE_EXTERNAL", ["STATE_EXTERNAL"]
    interest_gap = "chenh" in folded and ("lai suat" in folded or re.search(r"\bls\b", folded))
    if not interest_gap and "chenh lech rong" not in folded:
        return None, []
    has_combined = bool(re.search(r"\bnoi(?:\s+bang)?\s+ngoai\s+bang\b", folded))
    has_internal = "noi bang" in folded
    has_external = "ngoai bang" in folded or "cam ket ngoai" in folded
    if has_combined or (has_internal and has_external):
        return "STATE_COMBINED", ["STATE_COMBINED"]
    if has_external:
        return "STATE_EXTERNAL", ["STATE_EXTERNAL"]
    if has_internal or "chenh lech rong" in folded:
        return "STATE_INTERNAL", ["STATE_INTERNAL"]
    return None, []


def interest_rate_document_reporting_date_receipt_v1(
    pages: list[dict[str, Any]],
) -> dict[str, Any]:
    """Add exact typed statement-title dates when columns use semantic periods."""

    base = engine._valuation_document_reporting_date_receipt_v1(pages)
    evidence = canonical_clone_v1(base.get("evidence") or [])
    for record in pages:
        for section_ordinal, section in enumerate(
            record["page_json"].get("sections") or [], start=1
        ):
            if (
                type(section) is not dict
                or section.get("content_kind") != "PRIMARY_STATEMENT"
                or section.get("statement_type") != "BALANCE_SHEET"
            ):
                continue
            dates = sorted(
                {
                    item.isoformat()
                    for item in engine._header_dates(section.get("title_exact") or "")
                }
            )
            if len(dates) != 1:
                continue
            evidence.append(
                {
                    "comparative_date": None,
                    "current_date": dates[0],
                    "page_json_version_id": record["page_json_version_id"],
                    "physical_page": record["physical_page"],
                    "section_id": f"s{section_ordinal}",
                    "source_kind": "TYPED_PRIMARY_BALANCE_SHEET_TITLE_DATE",
                    "table_id": None,
                }
            )
    current_candidates = sorted(
        {
            item["current_date"]
            for item in evidence
            if type(item) is dict and type(item.get("current_date")) is str
        }
    )
    current_date = current_candidates[-1] if current_candidates else None
    comparative_candidates = sorted(
        {
            item["comparative_date"]
            for item in evidence
            if type(item) is dict
            and type(item.get("comparative_date")) is str
            and type(current_date) is str
            and item["comparative_date"] < current_date
        }
    )
    comparative_date = comparative_candidates[-1] if comparative_candidates else None
    material = {
        "base_receipt": canonical_clone_v1(base),
        "comparative_date": comparative_date,
        "current_date": current_date,
        "evidence": evidence,
        "rule": "LATEST_TYPED_PRIMARY_STATEMENT_OR_BALANCE_TITLE_DATE",
        "status": ("UNIQUE_LATEST_TYPED_DOCUMENT_REPORTING_DATE" if current_date else "NOT_UNIQUE"),
    }
    return {**material, "receipt_sha256": canonical_json_sha256_v1(material)}


def resolve_interest_rate_row_axis_v1(
    row_axis: list[dict[str, Any]], *, aliases_by_role: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Use ordered accounting roles only for otherwise bare gap labels."""

    checked = canonical_clone_v1(row_axis)
    assigned = {item["role"] for item in checked if item["role"] is not None}
    ambiguous = []
    for item in checked:
        if item["role"] is not None:
            continue
        folded = engine._normalized(item.get("label_exact"))
        if "chenh" in folded and ("lai suat" in folded or re.search(r"\bls\b", folded)):
            ambiguous.append(item)
    available = [
        role
        for role in ("STATE_INTERNAL", "STATE_EXTERNAL", "STATE_COMBINED")
        if role not in assigned
    ]
    if len(ambiguous) > len(available):
        for item in ambiguous:
            item["role_matches"] = available
        return checked
    for item, role in zip(ambiguous, available, strict=False):
        item["kind"] = "CORE_ROW"
        item["role"] = role
        item["role_matches"] = [role]
    return checked


def compile_gemini_json_interest_rate_risk_matrix_specs_v1(
    *, topology: Mapping[str, Any], evaluation_spec: Any, schema_binding_spec: Any
) -> dict[str, Any]:
    """Compile an interest-rate triplet onto the shared exact matrix core."""

    if topology.get("family_id") != "INTEREST_RATE_RISK":
        raise _error("interest-rate matrix topology family is invalid")
    compiled = compile_gemini_json_currency_risk_matrix_specs_v1(
        topology=topology,
        evaluation_spec=evaluation_spec,
        schema_binding_spec=schema_binding_spec,
    )
    compiled["claim_boundary"] = INTEREST_RATE_RISK_CLAIM_BOUNDARY
    compiled["interest_rate_risk_mode"] = True
    return compiled


def _declared_interest_table_v1(
    table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> bool:
    classification = classify_gemini_json_currency_risk_matrix_table_v1(
        table, compiled_specs=compiled_specs
    )
    declared_rows = classification["row_declared_component_roles"]
    declared_columns = [
        column
        for column in classification["column_axis"]
        if column["role"] is not None
        and column["role"] != compiled_specs["grand_total_currency_role"]
    ]
    return bool(declared_rows and declared_columns)


def _inside_interest_owner_interval_v1(
    *,
    position: list[int],
    markers: list[dict[str, Any]],
    max_continuation_pages: int,
) -> bool:
    prior = [marker for marker in markers if marker["position"] <= position]
    if not prior:
        return False
    latest = max(prior, key=lambda item: item["position"])
    return bool(
        latest["kind"] == "OWNER" and position[0] - latest["position"][0] <= max_continuation_pages
    )


def _owner_filtered_page_records_v1(
    page_records: Any, *, compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    pages = engine._selected_page_record_axis(page_records)
    markers: list[dict[str, Any]] = []
    for record in pages:
        for section_ordinal, section in enumerate(record["page_json"]["sections"], start=1):
            if type(section) is not dict:
                continue
            surfaces = [section.get("title_exact"), *(section.get("narratives_exact") or [])]
            for surface_ordinal, source_exact in enumerate(surfaces):
                position = [
                    record["selected_page_ordinal"],
                    section_ordinal,
                    0,
                    surface_ordinal,
                ]
                owner = engine._contained_declared_alias(
                    source_exact, compiled_specs["query_policy"]["owner_aliases"]
                )
                reset = engine._contained_declared_alias(
                    source_exact,
                    [
                        *compiled_specs["query_policy"]["reset_aliases"],
                        *compiled_specs["query_policy"]["hard_negative_aliases"],
                    ],
                )
                if owner is not None:
                    markers.append({"kind": "OWNER", "position": position})
                elif reset is not None:
                    markers.append({"kind": "RESET", "position": position})
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                if type(table) is not dict:
                    continue
                position = [
                    record["selected_page_ordinal"],
                    section_ordinal,
                    1,
                    table_ordinal,
                ]
                source_exact = table.get("title_exact")
                owner = engine._contained_declared_alias(
                    source_exact, compiled_specs["query_policy"]["owner_aliases"]
                )
                reset = engine._contained_declared_alias(
                    source_exact,
                    [
                        *compiled_specs["query_policy"]["reset_aliases"],
                        *compiled_specs["query_policy"]["hard_negative_aliases"],
                    ],
                )
                if owner is not None:
                    markers.append({"kind": "OWNER", "position": position})
                elif reset is not None:
                    markers.append({"kind": "RESET", "position": position})
    markers.sort(key=lambda item: item["position"])

    filtered = []
    for record in pages:
        checked_record = canonical_clone_v1(record)
        for section_ordinal, section in enumerate(checked_record["page_json"]["sections"], start=1):
            retained_tables = []
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                if type(table) is not dict:
                    continue
                position = [
                    checked_record["selected_page_ordinal"],
                    section_ordinal,
                    1,
                    table_ordinal,
                ]
                declared = _declared_interest_table_v1(table, compiled_specs=compiled_specs)
                if declared and not _inside_interest_owner_interval_v1(
                    position=position,
                    markers=markers,
                    max_continuation_pages=compiled_specs["query_policy"]["max_continuation_pages"],
                ):
                    continue
                retained_tables.append(table)
            section["tables"] = retained_tables
        filtered.append(checked_record)
    return filtered


def coalesce_gemini_json_interest_rate_risk_document_v1(
    *, page_records: Any, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Coalesce only repricing money matrices under the interest-rate owner."""

    filtered = _owner_filtered_page_records_v1(page_records, compiled_specs=compiled_specs)
    return coalesce_gemini_json_currency_risk_document_v1(
        page_records=filtered, compiled_specs=compiled_specs
    )
