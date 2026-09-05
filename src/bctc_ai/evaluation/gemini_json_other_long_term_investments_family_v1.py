"""Other-long-term-investment closure over selected Gemini page JSON.

Gemini remains a source reader.  The resolver inventories every declared-role
table in one document, binds one owner/reset fence, normalizes ordinary and
repeated-period layouts, and closes child/detail/provision/net equations in
deterministic code.  It contains no bank, filename, note-number, page, value or
prompt routing.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.accounting_family_topology_v1 import (
    compile_accounting_family_topology_spec_v1,
)
from bctc_ai.evaluation.gemini_json_customer_deposit_family_v1 import (
    _compile_units as _compile_single_accepted_unit_policy,
)
from bctc_ai.evaluation.gemini_json_customer_deposit_family_v1 import (
    _document_unit_context_axis,
    _money,
    _semantic_period_roles,
    _source_table,
    _two_period_axis,
    _unit_axis,
)
from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import (
    _header_dates,
    _header_text,
    _normalized,
    _period_signature,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

ENGINE_FORMAT_VERSION = "GEMINI_JSON_OTHER_LONG_TERM_INVESTMENTS_ACCOUNTING_FAMILY_V1"
INDEXED_QUERY_EVIDENCE_FORMAT_VERSION = (
    "GEMINI_JSON_INDEXED_OTHER_LONG_TERM_INVESTMENTS_QUERY_EVIDENCE_V1"
)
EVALUATION_FORMAT_VERSION = "ACCOUNTING_OTHER_LONG_TERM_INVESTMENTS_FAMILY_EVALUATION_SPEC_V1"
SCHEMA_FORMAT_VERSION = "ACCOUNTING_OTHER_LONG_TERM_INVESTMENTS_SCHEMA_BINDING_SPEC_V1"
SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION = (
    "GEMINI_JSON_OTHER_LONG_TERM_INVESTMENTS_AUTHENTICATED_SOURCE_REPAIR_ARTIFACT_V1"
)
READY = "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
NOT_OBSERVED = "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
UNRESOLVED = "UNRESOLVED_GEMINI_JSON_FAMILY"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_DECLARATIVE_OTHER_LONG_TERM_INVESTMENT_"
    "OWNER_OPTIONAL_CHILD_DETAIL_SUBTOTAL_PROVISION_NET_RESET_FENCE_EXACT_"
    "PERIOD_UNIT_OBSERVED_LANE_CLOSURE_BLANK_SOURCE_CELL_PRESERVED_SCHEMA_MAPPING_"
    "PROPOSAL_ONLY_GENERIC_CONTENT_ADDRESSED_VISUAL_DASH_SOURCE_REPAIR_"
    "TRANSCRIPTION_ONLY_NO_EQUATION_BACKSOLVE_PROVIDER_BANK_FILE_PAGE_NOTE_"
    "VALUE_PROMPT_ROUTING_CANONICAL_OR_EXPORT_AUTHORITY"
)

_PAGE_VERSION = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_DOCUMENT_ID = re.compile(r"gfpstorev1:document:[0-9a-f]{64}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SECTION_ID = re.compile(r"s[1-9][0-9]*\Z")
_TABLE_ID = re.compile(r"t[1-9][0-9]*\Z")
_ROW_ID = re.compile(r"r[1-9][0-9]*\Z")
_SOURCE_REPAIR_ID = re.compile(r"gjfoltisrv1:repair:[0-9a-f]{64}\Z")
_SOURCE_REPAIR_OVERLAY_ID = re.compile(r"gjfoltisrv1:overlay:[0-9a-f]{64}\Z")

_OUTPUT_ROLES = {
    "ASSOCIATE",
    "INVESTMENT_FUND",
    "JOINT_VENTURE",
    "ORGANIZATION_PROJECT",
    "OTHER_LONG_TERM",
    "PROVISION",
}
_TOP_LEVEL_ROLES = {"ASSOCIATE", "JOINT_VENTURE", "OTHER_LONG_TERM", "PROVISION"}
_DETAIL_ROLES = {"ASSOCIATE", "INVESTMENT_FUND", "JOINT_VENTURE", "ORGANIZATION_PROJECT"}
_MOVEMENT_TOKENS = (
    "so du dau nam",
    "so du dau ky",
    "tai ngay 1 thang 1",
    "trich lap trong nam",
    "hoan nhap trong nam",
    "bien dong khac",
    "so du cuoi nam",
)
_CARRYING_METRIC_TOKENS = (
    "gia tri ghi so",
    "gia tri hien tai",
    "gia tri rong cua khoan dau tu",
    "gia tri rong",
)
_FOLDED_VIETNAMESE_DATE = re.compile(
    r"(?<!\d)(?:tai\s+)?ngay\s*([0-3]?\d)\s*thang\s*([01]?\d)\s*nam\s*((?:19|20)\d{2})(?!\d)"
)


class GeminiJsonOtherLongTermInvestmentsFamilyV1Error(ValueError):
    """Selected JSON, declarative specs, or accounting closure drifted."""


def _error(message: str) -> GeminiJsonOtherLongTermInvestmentsFamilyV1Error:
    return GeminiJsonOtherLongTermInvestmentsFamilyV1Error(message)


def _aliases(child: Mapping[str, Any]) -> list[str]:
    return sorted({alias for matcher in child["matchers"] for alias in matcher["aliases"]})


def _compile_other_long_term_investment_units(
    value: Any,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Compile the two exact source units present in Family 17 notes.

    This family has source-visible disclosures in both million VND and exact
    VND; mappings retain the authenticated source unit and never silently
    rescale.  Reuse the shared strict binding validator after checking the
    family-specific accepted-unit frontier.
    """

    if type(value) is not list:
        raise ValueError("other-long-term-investment money-unit bindings are absent")
    accepted_units = {
        item.get("canonical_unit")
        for item in value
        if type(item) is dict and item.get("accepted") is True
    }
    if accepted_units != {"MILLION_VND", "VND"}:
        raise ValueError("other-long-term-investment accepted money-unit axis is invalid")
    return _compile_single_accepted_unit_policy(value)


def _compile_authenticated_source_repair_artifact_v1(
    value: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compile a byte-pinned, dash-only transcription overlay.

    This overlay is deliberately narrower than a model/OCR correction path: it
    may only replace an exact JSON ``null`` with a literal PDF-visible dash at
    a fully bound source/page/table/row/column identity.  It never accepts a
    numeric replacement and therefore cannot backsolve an accounting equation.
    """

    ref_fields = {
        "artifact_format_version",
        "overlay_id",
        "path",
        "sha256",
        "size_bytes",
    }
    if (
        type(value) is not dict
        or set(value) != ref_fields
        or value.get("artifact_format_version") != SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION
        or type(value.get("path")) is not str
        or not value["path"]
        or value["path"].startswith("/")
        or ".." in value["path"].split("/")
        or _SHA256.fullmatch(value.get("sha256", "")) is None
        or type(value.get("size_bytes")) is not int
        or value["size_bytes"] <= 0
        or _SOURCE_REPAIR_OVERLAY_ID.fullmatch(value.get("overlay_id", "")) is None
    ):
        raise _error("other-long-term-investment authenticated source-repair ref is invalid")
    artifact_path = Path(__file__).resolve().parents[3] / value["path"]
    try:
        payload = artifact_path.read_bytes()
    except OSError as exc:
        raise _error("other-long-term-investment source-repair artifact is absent") from exc
    if len(payload) != value["size_bytes"] or sha256(payload).hexdigest() != value["sha256"]:
        raise _error("other-long-term-investment source-repair artifact bytes drifted")
    try:
        raw = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("other-long-term-investment source-repair artifact JSON is invalid") from exc

    artifact_fields = {
        "format_version",
        "overlay_id",
        "policy",
        "repair_axis_sha256",
        "repair_count",
        "repairs",
    }
    policy = "ONLY_EXACT_PDF_RENDER_VISIBLE_DASH_MISSED_AS_NULL_NO_EQUATION_DERIVATION"
    if (
        type(raw) is not dict
        or set(raw) != artifact_fields
        or raw.get("format_version") != SOURCE_REPAIR_ARTIFACT_FORMAT_VERSION
        or raw.get("policy") != policy
        or type(raw.get("repairs")) is not list
        or not raw["repairs"]
        or raw.get("repair_count") != len(raw["repairs"])
        or raw.get("repair_axis_sha256") != canonical_json_sha256_v1(raw["repairs"])
    ):
        raise _error("other-long-term-investment source-repair artifact is invalid")

    repair_fields = {
        "base_page_json_sha256",
        "base_table_sha256",
        "cell_repairs",
        "page_image",
        "page_json_version_id",
        "physical_page",
        "reason",
        "repair_id",
        "section_id",
        "source_logical_name",
        "source_sha256",
        "table_id",
    }
    image_fields = {
        "height",
        "media_type",
        "render_dpi",
        "sha256",
        "size_bytes",
        "width",
    }
    cell_fields = {
        "column_ordinal",
        "original_value_exact",
        "replacement_value_exact",
        "row_hierarchy_path_exact",
        "row_id",
        "row_kind",
        "row_label_exact",
        "visual_observation",
    }
    checked_repairs = []
    seen_versions: set[str] = set()
    seen_repairs: set[str] = set()
    for raw_repair in raw["repairs"]:
        if type(raw_repair) is not dict or set(raw_repair) != repair_fields:
            raise _error("other-long-term-investment source-repair fields drifted")
        repair = canonical_clone_v1(raw_repair)
        image = repair["page_image"]
        if (
            type(image) is not dict
            or set(image) != image_fields
            or _SHA256.fullmatch(image.get("sha256", "")) is None
            or type(image.get("size_bytes")) is not int
            or image["size_bytes"] <= 0
            or type(image.get("width")) is not int
            or image["width"] <= 0
            or type(image.get("height")) is not int
            or image["height"] <= 0
            or image.get("render_dpi") not in {200, 300}
            or image.get("media_type") != "image/png"
        ):
            raise _error("other-long-term-investment source-repair page image is invalid")
        if (
            _SHA256.fullmatch(repair.get("base_page_json_sha256", "")) is None
            or _SHA256.fullmatch(repair.get("base_table_sha256", "")) is None
            or _PAGE_VERSION.fullmatch(repair.get("page_json_version_id", "")) is None
            or repair["page_json_version_id"] in seen_versions
            or type(repair.get("physical_page")) is not int
            or repair["physical_page"] <= 0
            or _SECTION_ID.fullmatch(repair.get("section_id", "")) is None
            or _TABLE_ID.fullmatch(repair.get("table_id", "")) is None
            or type(repair.get("source_logical_name")) is not str
            or not repair["source_logical_name"].strip()
            or _SHA256.fullmatch(repair.get("source_sha256", "")) is None
            or repair.get("reason") != "PDF_RENDER_VISIBLE_DASH_OMITTED_FROM_SELECTED_JSON"
            or type(repair.get("cell_repairs")) is not list
            or not repair["cell_repairs"]
        ):
            raise _error("other-long-term-investment source-repair binding is invalid")
        seen_versions.add(repair["page_json_version_id"])
        checked_cells = []
        seen_cells: set[tuple[str, int]] = set()
        for raw_cell in repair["cell_repairs"]:
            if type(raw_cell) is not dict or set(raw_cell) != cell_fields:
                raise _error("other-long-term-investment source-repair cell fields drifted")
            cell = canonical_clone_v1(raw_cell)
            cell_key = (cell.get("row_id"), cell.get("column_ordinal"))
            if (
                _ROW_ID.fullmatch(cell.get("row_id", "")) is None
                or type(cell.get("column_ordinal")) is not int
                or cell["column_ordinal"] <= 0
                or cell_key in seen_cells
                or cell.get("original_value_exact") is not None
                or cell.get("replacement_value_exact") != "-"
                or cell.get("visual_observation") != "PDF_RENDER_VISIBLE_DASH"
                or type(cell.get("row_kind")) is not str
                or not cell["row_kind"]
                or type(cell.get("row_label_exact")) is not str
                or not cell["row_label_exact"].strip()
                or type(cell.get("row_hierarchy_path_exact")) is not list
                or not cell["row_hierarchy_path_exact"]
                or any(
                    type(item) is not str or not item for item in cell["row_hierarchy_path_exact"]
                )
            ):
                raise _error("other-long-term-investment source-repair cell is invalid")
            seen_cells.add(cell_key)
            checked_cells.append(cell)
        ordered_cells = sorted(
            checked_cells,
            key=lambda item: (int(item["row_id"][1:]), item["column_ordinal"]),
        )
        if repair["cell_repairs"] != ordered_cells:
            raise _error("other-long-term-investment source-repair cell axis is unordered")
        expected_repair_id = "gjfoltisrv1:repair:" + canonical_json_sha256_v1(
            {key: repair[key] for key in repair if key != "repair_id"}
        )
        if (
            _SOURCE_REPAIR_ID.fullmatch(repair.get("repair_id", "")) is None
            or repair["repair_id"] != expected_repair_id
            or repair["repair_id"] in seen_repairs
        ):
            raise _error("other-long-term-investment source-repair identity does not replay")
        seen_repairs.add(repair["repair_id"])
        checked_repairs.append(repair)
    ordered_repairs = sorted(
        checked_repairs,
        key=lambda item: (
            item["source_logical_name"],
            item["physical_page"],
            int(item["section_id"][1:]),
            int(item["table_id"][1:]),
        ),
    )
    if raw["repairs"] != ordered_repairs:
        raise _error("other-long-term-investment source-repair axis is unordered")
    material = {key: canonical_clone_v1(raw[key]) for key in artifact_fields - {"overlay_id"}}
    expected_overlay_id = "gjfoltisrv1:overlay:" + canonical_json_sha256_v1(material)
    if raw.get("overlay_id") != expected_overlay_id or value["overlay_id"] != expected_overlay_id:
        raise _error("other-long-term-investment source-repair overlay identity does not replay")
    return canonical_clone_v1(raw), canonical_clone_v1(value)


def compile_gemini_json_other_long_term_investments_family_specs_v1(
    topology_spec: Any, evaluation_spec: Any, schema_binding_spec: Any
) -> dict[str, Any]:
    """Compile the data-only Family 17 topology/evaluation/schema triplet."""

    try:
        topology = compile_accounting_family_topology_spec_v1(topology_spec)
    except ValueError as exc:
        raise _error("other-long-term-investment topology spec is invalid") from exc
    evaluation_fields = {
        "authenticated_source_repair_artifact_ref",
        "blank_zero_policy",
        "closure_policy",
        "component_policy",
        "family_id",
        "format_version",
        "layout_policy",
        "money_unit_bindings",
        "period_semantics",
        "typed_control_exclusions",
    }
    if (
        type(evaluation_spec) is not dict
        or set(evaluation_spec) != evaluation_fields
        or evaluation_spec.get("format_version") != EVALUATION_FORMAT_VERSION
        or evaluation_spec.get("family_id") != topology["family_id"]
        or evaluation_spec.get("blank_zero_policy")
        != "PRESERVE_BLANK_SOURCE_CELL_NEVER_INFER_NUMERIC_ZERO"
        or evaluation_spec.get("closure_policy")
        != "EXACT_OPTIONAL_CHILD_DETAIL_SUBTOTAL_PROVISION_AND_NET_ALL_LANES"
        or evaluation_spec.get("component_policy")
        != "ONE_OWNER_RESET_FENCE_WITH_MAIN_TABLE_AND_OPTIONAL_DETAIL_OR_CONTINUATION_TABLES"
        or evaluation_spec.get("layout_policy")
        != "TWO_PERIOD_COLUMNS_OR_TWO_ORDERED_PERIOD_TABLES_WITH_EXACT_CARRYING_VALUE_LANE"
        or evaluation_spec.get("period_semantics") != "CURRENT_AND_COMPARATIVE_SNAPSHOT"
        or evaluation_spec.get("typed_control_exclusions")
        != [
            "PRIMARY_FINANCIAL_STATEMENT_SUMMARY",
            "PROVISION_MOVEMENT",
            "FAIR_VALUE_OR_FINANCIAL_INSTRUMENT_VIEW",
            "PERCENTAGE_ONLY_VIEW",
            "OPERATING_EXPENSE_OR_INCOME_VIEW",
            "RELATED_PARTY_TRANSACTION_OR_BALANCE_VIEW",
            "SUBSIDIARY_ONLY_INVESTMENT_VIEW",
            "NON_MONETARY_POLICY_OR_FORMULA_VIEW",
        ]
    ):
        raise _error("other-long-term-investment evaluation spec is invalid")
    try:
        unit_bindings, unit_binding_by_alias = _compile_other_long_term_investment_units(
            evaluation_spec["money_unit_bindings"]
        )
    except ValueError as exc:
        raise _error("other-long-term-investment unit bindings are invalid") from exc
    source_repair_overlay, source_repair_artifact_ref = (
        _compile_authenticated_source_repair_artifact_v1(
            evaluation_spec["authenticated_source_repair_artifact_ref"]
        )
    )

    child_by_role = {child["role"]: child for child in topology["children"]}
    if set(child_by_role) != _OUTPUT_ROLES:
        raise _error("other-long-term-investment role frontier is incomplete")
    matchers_by_role = {
        role: canonical_clone_v1(child["matchers"]) for role, child in child_by_role.items()
    }
    aliases_by_role = {role: _aliases(child) for role, child in child_by_role.items()}

    schema_fields = {
        "family_id",
        "family_root_report_norm_id",
        "format_version",
        "role_bindings",
        "root_mapping_policy",
        "schema_period_type",
    }
    if (
        type(schema_binding_spec) is not dict
        or set(schema_binding_spec) != schema_fields
        or schema_binding_spec.get("format_version") != SCHEMA_FORMAT_VERSION
        or schema_binding_spec.get("family_id") != topology["family_id"]
        or schema_binding_spec.get("family_root_report_norm_id") != 862
        or schema_binding_spec.get("root_mapping_policy") != "SOURCE_VISIBLE_NET_TOTAL"
        or schema_binding_spec.get("schema_period_type") != "SNAPSHOT"
        or type(schema_binding_spec.get("role_bindings")) is not list
    ):
        raise _error("other-long-term-investment schema binding spec is invalid")
    bindings: dict[str, int] = {}
    identities = {862}
    for raw in schema_binding_spec["role_bindings"]:
        if (
            type(raw) is not dict
            or set(raw) != {"report_norm_id", "role"}
            or raw.get("role") not in _OUTPUT_ROLES
            or raw["role"] in bindings
            or type(raw.get("report_norm_id")) is not int
            or raw["report_norm_id"] <= 0
            or raw["report_norm_id"] in identities
        ):
            raise _error("other-long-term-investment schema role binding is invalid")
        bindings[raw["role"]] = raw["report_norm_id"]
        identities.add(raw["report_norm_id"])
    if set(bindings) != _OUTPUT_ROLES:
        raise _error("other-long-term-investment schema binding frontier is incomplete")
    query_policy = {
        "authenticated_source_repair_artifact_ref": canonical_clone_v1(source_repair_artifact_ref),
        "hard_negative_aliases": canonical_clone_v1(topology["hard_negative_aliases"]),
        "owner_aliases": canonical_clone_v1(topology["parent"]["aliases"]),
        "reset_aliases": canonical_clone_v1(topology["structural_reset_aliases"]),
    }
    return {
        "aliases_by_role": aliases_by_role,
        "bindings": bindings,
        "claim_boundary": CLAIM_BOUNDARY,
        "child_by_role": child_by_role,
        "currency_aliases": {},
        "engine_format_version": ENGINE_FORMAT_VERSION,
        "evaluation": canonical_clone_v1(evaluation_spec),
        "matchers_by_role": matchers_by_role,
        "output_role_order": [item["role"] for item in schema_binding_spec["role_bindings"]],
        "query_policy": query_policy,
        "schema": canonical_clone_v1(schema_binding_spec),
        "source_repair_artifact_ref": source_repair_artifact_ref,
        "source_repair_overlay": source_repair_overlay,
        "topology": topology,
        "unit_binding_by_alias": unit_binding_by_alias,
        "unit_bindings": unit_bindings,
    }


def _contains_alias(value: Any, alias: str) -> bool:
    text = _normalized(value)
    return bool(text and (text == alias or f" {alias} " in f" {text} "))


def _surface_dates(value: Any) -> set[date]:
    if type(value) is not str:
        return set()
    parsed = set(_header_dates(value))
    for match in _FOLDED_VIETNAMESE_DATE.finditer(_normalized(value)):
        try:
            parsed.add(date(int(match.group(3)), int(match.group(2)), int(match.group(1))))
        except ValueError:
            continue
    return parsed


def _period_heading_dates(value: Any) -> list[str]:
    folded = _normalized(value)
    if not folded.startswith("tai ngay"):
        return []
    return sorted((item.isoformat() for item in _surface_dates(value)), reverse=True)


def _matches_alias(value: Any, alias: str) -> bool:
    text = _normalized(value)
    if not text:
        return False
    if text == alias or text.startswith(alias + " "):
        return True
    tokens = text.split()
    while len(tokens) > 1 and (
        tokens[0].isdigit()
        or (len(tokens[0]) == 1 and tokens[0].isalpha())
        or tokens[0] in {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"}
        or tokens[0] in {"less", "tru"}
    ):
        tokens.pop(0)
    stripped = " ".join(tokens)
    return stripped == alias or stripped.startswith(alias + " ")


def _surface_axis(section: Mapping[str, Any], table: Mapping[str, Any]) -> list[Any]:
    values: list[Any] = [section.get("title_exact"), table.get("title_exact")]
    narratives = section.get("narratives_exact")
    if type(narratives) is list:
        values.extend(narratives)
    return values


def _role_context_surface_axis(section: Mapping[str, Any], table: Mapping[str, Any]) -> list[Any]:
    """Return only surfaces that authoritatively own one table population.

    Narratives are useful owner/reset evidence, but they can contain a running
    header or prose about the preceding population.  Treating those mentions as
    the role of the current table can silently relabel a continuation.  Section
    and table titles are the bounded population context; row labels provide the
    remaining role evidence below.
    """

    return [section.get("title_exact"), table.get("title_exact")]


def _has_subsidiary_evidence(rows: Sequence[Mapping[str, Any]]) -> bool:
    return any(
        any(
            "dau tu vao cong ty con" in _normalized(value)
            for value in [row.get("label_exact"), *(row.get("hierarchy_path_exact") or [])]
            if type(value) is str
        )
        for row in rows
    )


def _owner_visible(
    section: Mapping[str, Any], table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> bool:
    return any(
        _contains_alias(value, alias)
        for value in _surface_axis(section, table)
        for alias in compiled_specs["query_policy"]["owner_aliases"]
    )


def _path_has_role(
    path: Any, role: str, *, label_exact: Any, compiled_specs: Mapping[str, Any]
) -> bool:
    if type(path) is not list:
        return False
    label = _normalized(label_exact)
    ancestors = [value for value in path if type(value) is str and _normalized(value) != label]
    return any(
        _matches_alias(value, alias)
        for value in ancestors
        for alias in compiled_specs["aliases_by_role"][role]
    )


def _role_match_score(
    row: Mapping[str, Any], role: str, *, compiled_specs: Mapping[str, Any]
) -> int | None:
    scores = []
    for matcher in compiled_specs["matchers_by_role"][role]:
        aliases = [
            alias for alias in matcher["aliases"] if _matches_alias(row.get("label_exact"), alias)
        ]
        if not aliases:
            continue
        within = matcher["within_role"]
        if within is None or _path_has_role(
            row.get("hierarchy_path_exact"),
            within,
            label_exact=row.get("label_exact"),
            compiled_specs=compiled_specs,
        ):
            scores.extend(len(_normalized(alias)) for alias in aliases)
    return max(scores) if scores else None


def _is_operating_flow_view(section: Mapping[str, Any], table: Mapping[str, Any]) -> bool:
    surfaces = [section.get("title_exact"), table.get("title_exact")]
    surfaces.extend(row.get("label_exact") for row in table.get("rows") or [] if type(row) is dict)
    folded = " ".join(_normalized(value) for value in surfaces if type(value) is str)
    return any(
        token in folded
        for token in (
            "chi phi hoat dong",
            "co tuc nhan duoc",
            "hach toan tren tk",
            "thu nhap",
        )
    )


def _typed_control_disposition(
    page_json: Mapping[str, Any], section: Mapping[str, Any], table: Mapping[str, Any]
) -> str | None:
    title = " ".join(
        value
        for value in (section.get("title_exact"), table.get("title_exact"))
        if type(value) is str
    )
    folded = _normalized(title)
    rows = [row for row in table.get("rows") or [] if type(row) is dict]
    labels = [_normalized(row.get("label_exact")) for row in rows]
    columns = table.get("columns")
    if page_json.get("status") == "PRIMARY_FINANCIAL_STATEMENT" or (
        section.get("content_kind") == "PRIMARY_STATEMENT"
        and section.get("statement_type") == "BALANCE_SHEET"
    ):
        return "PRIMARY_FINANCIAL_STATEMENT_SUMMARY"
    if any(token in " ".join(labels) for token in _MOVEMENT_TOKENS):
        return "PROVISION_MOVEMENT"
    if (
        "gia tri hop ly" in folded
        or "phan loai tai san tai chinh" in folded
        or "cong cu tai chinh" in folded
    ):
        return "FAIR_VALUE_OR_FINANCIAL_INSTRUMENT_VIEW"
    if _is_operating_flow_view(section, table):
        return "OPERATING_EXPENSE_OR_INCOME_VIEW"
    if "ben lien quan" in folded:
        return "RELATED_PARTY_TRANSACTION_OR_BALANCE_VIEW"
    money_ordinals = [
        ordinal
        for ordinal, column in enumerate(columns or [], start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    visible_detail_rows = [
        row
        for row in rows
        if row.get("row_kind") not in {"SUBTOTAL", "TOTAL"}
        and type(row.get("values_exact")) is list
        and any(
            ordinal <= len(row["values_exact"]) and row["values_exact"][ordinal - 1] is not None
            for ordinal in money_ordinals
        )
    ]
    subsidiary_evidence = _has_subsidiary_evidence(rows)
    if (
        subsidiary_evidence
        and visible_detail_rows
        and all(
            any(
                "dau tu vao cong ty con" in _normalized(value)
                for value in [row.get("label_exact"), *(row.get("hierarchy_path_exact") or [])]
                if type(value) is str
            )
            or "du phong" in _normalized(row.get("label_exact"))
            for row in visible_detail_rows
        )
    ):
        return "SUBSIDIARY_ONLY_INVESTMENT_VIEW"
    if (
        type(columns) is list
        and not any(
            type(column) is dict and column.get("value_kind") == "MONEY" for column in columns
        )
        and any(
            type(column) is dict and column.get("value_kind") == "PERCENT" for column in columns
        )
    ):
        return "PERCENTAGE_ONLY_VIEW"
    if type(columns) is list and not any(
        type(column) is dict and column.get("value_kind") == "MONEY" for column in columns
    ):
        return "NON_MONETARY_POLICY_OR_FORMULA_VIEW"
    return None


def _explicit_table_context_role(
    section: Mapping[str, Any], table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> str | None:
    surfaces = _role_context_surface_axis(section, table)
    matched = {
        role
        for role in _DETAIL_ROLES | {"OTHER_LONG_TERM"}
        if any(
            _contains_alias(value, alias)
            for value in surfaces
            for alias in compiled_specs["aliases_by_role"][role]
        )
    }
    if len(matched) == 1:
        return next(iter(matched))
    return None


def _table_context_role(
    section: Mapping[str, Any], table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> str | None:
    explicit = _explicit_table_context_role(section, table, compiled_specs=compiled_specs)
    if explicit is not None:
        return explicit
    rows = [row for row in table.get("rows") or [] if type(row) is dict]
    directly_declared_roles = {
        role
        for row in rows
        for role in _OUTPUT_ROLES
        if _role_match_score(row, role, compiled_specs=compiled_specs) is not None
    }
    if len(directly_declared_roles) > 1:
        return None
    item_labels = [
        _normalized(row.get("label_exact"))
        for row in rows
        if row.get("row_kind") not in {"GROUP", "SUBTOTAL", "TOTAL"}
        and _normalized(row.get("label_exact"))
    ]
    if _is_operating_flow_view(section, table):
        return None
    if item_labels and any("cong ty lien doanh" in label for label in item_labels):
        return "JOINT_VENTURE"
    return None


def _table_has_period_evidence(table: Mapping[str, Any]) -> bool:
    surfaces = [table.get("title_exact")]
    columns = table.get("columns")
    if type(columns) is list:
        surfaces.extend(
            _header_text(column)
            for column in columns
            if type(column) is dict and column.get("value_kind") == "MONEY"
        )
    return any(
        type(value) is str and (bool(_surface_dates(value)) or _period_signature(value) is not None)
        for value in surfaces
    )


def _section_table_has_period_evidence(
    section: Mapping[str, Any], table: Mapping[str, Any]
) -> bool:
    if _table_has_period_evidence(table):
        return True
    narratives = section.get("narratives_exact")
    return type(narratives) is list and any(_period_heading_dates(value) for value in narratives)


def _effective_table_context_role(
    section: Mapping[str, Any],
    table_ordinal: int,
    *,
    compiled_specs: Mapping[str, Any],
) -> str | None:
    tables = section.get("tables")
    if type(tables) is not list or not 1 <= table_ordinal <= len(tables):
        return None
    active = None
    for ordinal, table in enumerate(tables[:table_ordinal], start=1):
        if type(table) is not dict:
            continue
        explicit = _explicit_table_context_role(section, table, compiled_specs=compiled_specs)
        if explicit is not None:
            active = explicit
        elif (
            type(table.get("title_exact")) is str
            and table["title_exact"].strip()
            and not _table_has_period_evidence(table)
        ):
            # A newly titled sibling is a new population unless that title
            # itself declares a role.  An exact date/period-only title is the
            # ordinary comparative continuation of the preceding explicit
            # role and therefore does not reset it.
            active = None
        elif active is None:
            active = _table_context_role(section, table, compiled_specs=compiled_specs)
        elif ordinal == table_ordinal and not _table_has_period_evidence(table):
            return None
    return active


def _with_effective_table_context_role(
    classification: Mapping[str, Any],
    section: Mapping[str, Any],
    table_ordinal: int,
    *,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    if len({hit["role"] for hit in classification["role_hits"]}) > 1:
        return canonical_clone_v1(classification)
    effective = _effective_table_context_role(section, table_ordinal, compiled_specs=compiled_specs)
    if effective is None or effective == classification["table_context_role"]:
        return canonical_clone_v1(classification)
    material = {
        key: canonical_clone_v1(value)
        for key, value in classification.items()
        if key != "classification_id"
    }
    material["table_context_role"] = effective
    material["table_context_role_source"] = "PRIOR_EXPLICIT_SIBLING_PERIOD_TABLE"
    return {
        **material,
        "classification_id": "gjfolticv1:classification:" + canonical_json_sha256_v1(material),
    }


def _two_period_role_specific_lane_axes(
    table: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Resolve horizontal cost/provision or cost/net metric blocks by role.

    A number of ordinary notes repeat two metric columns inside each period:
    gross cost plus provision, or gross cost plus net carrying value.  A single
    table-wide metric choice cannot represent those rows.  This helper binds
    each schema role to one exact column per period and requires an identical
    two-period structure on both sides.
    """

    columns = table.get("columns")
    if type(columns) is not list:
        return {}
    by_signature: dict[tuple[str, str], list[int]] = defaultdict(list)
    for ordinal, column in enumerate(columns, start=1):
        if type(column) is not dict or column.get("value_kind") != "MONEY":
            continue
        header = _header_text(column)
        dates = sorted(item.isoformat() for item in _surface_dates(header))
        semantic_roles = _semantic_period_roles(header)
        if len(dates) > 1 or len(semantic_roles) > 1:
            return {}
        if dates:
            signature = ("DATE", dates[0])
        elif semantic_roles:
            signature = ("SEMANTIC_ALIAS", semantic_roles[0])
        else:
            return {}
        by_signature[signature].append(ordinal)
    if len(by_signature) != 2 or any(len(ordinals) < 2 for ordinals in by_signature.values()):
        return {}
    identities = set(by_signature)
    if all(signature[0] == "DATE" for signature in identities):
        ordered = sorted(identities, key=lambda item: date.fromisoformat(item[1]), reverse=True)
    elif identities == {
        ("SEMANTIC_ALIAS", "CURRENT_PERIOD"),
        ("SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"),
    }:
        ordered = [
            ("SEMANTIC_ALIAS", "CURRENT_PERIOD"),
            ("SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"),
        ]
    else:
        return {}

    def metric_class(ordinal: int) -> str:
        header = _normalized(_header_text(columns[ordinal - 1]))
        if "du phong" in header:
            return "PROVISION"
        if any(token in header for token in ("gia goc", "nguyen gia", "gia tri dau tu", "cost")):
            return "COST"
        if any(token in header for token in (*_CARRYING_METRIC_TOKENS, "gia tri thuan")):
            return "CARRYING_VALUE"
        return "GENERIC_AMOUNT"

    def select(role: str, ordinals: Sequence[int]) -> tuple[int, str] | None:
        classes = {ordinal: metric_class(ordinal) for ordinal in ordinals}
        preferred = (
            ("PROVISION", "CARRYING_VALUE")
            if role == "PROVISION"
            else ("COST", "CARRYING_VALUE", "GENERIC_AMOUNT")
        )
        for metric in preferred:
            matches = [ordinal for ordinal, kind in classes.items() if kind == metric]
            if len(matches) == 1:
                return matches[0], metric
            if len(matches) > 1:
                return None
        return None

    result = {}
    for role in _OUTPUT_ROLES:
        selected = [select(role, by_signature[signature]) for signature in ordered]
        if any(item is None for item in selected):
            continue
        checked = [item for item in selected if item is not None]
        if len({item[1] for item in checked}) != 1:
            continue
        result[role] = {
            "complete": True,
            "lane_keys": [list(signature) for signature in ordered],
            "layout_kind": "TWO_PERIOD_ROLE_SPECIFIC_MULTI_METRIC_COLUMNS",
            "money_column_ordinals": [item[0] for item in checked],
            "reasons": [],
            "selected_metric_kinds": [item[1] for item in checked],
            "source_period_axis": {
                "ordinals_by_signature": {
                    ":".join(signature): by_signature[signature] for signature in ordered
                }
            },
        }
    return result


def classify_gemini_json_other_long_term_investments_table_v1(
    page_json: Any,
    section: Any,
    table: Any,
    *,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Inventory one table without assigning document-level ownership."""

    if type(page_json) is not dict or type(section) is not dict or type(table) is not dict:
        raise _error("other-long-term-investment source table is invalid")
    columns = table.get("columns")
    rows = table.get("rows")
    if type(columns) is not list or type(rows) is not list:
        raise _error("other-long-term-investment table axes are invalid")
    money_ordinals = [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    role_hits = []
    ambiguous_rows = []
    anonymous_totals = []
    contextual_short_provision_rows = []
    unbound_money_rows = []
    for row_ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict or type(row.get("values_exact")) is not list:
            continue
        values = row["values_exact"]
        visible = any(
            ordinal <= len(values) and values[ordinal - 1] is not None for ordinal in money_ordinals
        )
        scored = [
            (role, score)
            for role in _OUTPUT_ROLES
            if (score := _role_match_score(row, role, compiled_specs=compiled_specs)) is not None
        ]
        maximum = max((score for _role, score in scored), default=None)
        matched = sorted(role for role, score in scored if score == maximum)
        if len(matched) > 1:
            ambiguous_rows.append({"matched_roles": matched, "row_ordinal": row_ordinal})
        elif matched:
            role_hits.append(
                {
                    "role": matched[0],
                    "row_ordinal": row_ordinal,
                    "row_kind": row.get("row_kind"),
                    "source_order": row_ordinal,
                }
            )
        elif money_ordinals and _normalized(row.get("label_exact")) == "du phong giam gia":
            contextual_short_provision_rows.append(
                {
                    "role": "PROVISION",
                    "row_ordinal": row_ordinal,
                    "row_kind": row.get("row_kind"),
                    "source_order": row_ordinal,
                }
            )
            unbound_money_rows.append(row_ordinal)
        elif visible and row.get("row_kind") in {"SUBTOTAL", "TOTAL"}:
            anonymous_totals.append(
                {
                    "row_ordinal": row_ordinal,
                    "row_kind": row.get("row_kind"),
                    "source_order": row_ordinal,
                }
            )
        elif visible and money_ordinals:
            unbound_money_rows.append(row_ordinal)
    # A few ordinary family summaries shorten the provision label to only
    # "Dự phòng giảm giá".  That phrase is unsafe as a document-wide alias,
    # but it is an exact sibling role when the same table also declares the
    # other-long-term-investment population.  Keep this contextual rule local
    # to the sealed owner/table instead of routing by document identity.
    if any(hit["role"] == "OTHER_LONG_TERM" for hit in role_hits):
        role_hits.extend(contextual_short_provision_rows)
        short_ordinals = {item["row_ordinal"] for item in contextual_short_provision_rows}
        unbound_money_rows = [
            ordinal for ordinal in unbound_money_rows if ordinal not in short_ordinals
        ]
    compound_role_projections = []
    role_specific_axes = _two_period_role_specific_lane_axes(table)
    role_axis_before_projection = {item["role"] for item in role_hits}
    other_hits = [item for item in role_hits if item["role"] == "OTHER_LONG_TERM"]
    if (
        "PROVISION" not in role_axis_before_projection
        and "OTHER_LONG_TERM" in role_specific_axes
        and "PROVISION" in role_specific_axes
        and len(other_hits) == 1
    ):
        source_row_ordinal = other_hits[0]["row_ordinal"]
        values = rows[source_row_ordinal - 1].get("values_exact")
        provision_ordinals = role_specific_axes["PROVISION"]["money_column_ordinals"]
        if type(values) is list and all(ordinal <= len(values) for ordinal in provision_ordinals):
            compound_role_projections.append(
                {
                    "projected_role": "PROVISION",
                    "source_role": "OTHER_LONG_TERM",
                    "source_row_ordinal": source_row_ordinal,
                }
            )
    typed_control = _typed_control_disposition(page_json, section, table)
    role_axis = {item["role"] for item in role_hits}
    title_axis = " ".join(
        _normalized(value)
        for value in (section.get("title_exact"), table.get("title_exact"))
        if type(value) is str
    )
    if (
        typed_control is None
        and "du phong" in title_axis
        and "PROVISION" in role_axis
        and role_axis <= {"PROVISION", "OTHER_LONG_TERM"}
    ):
        typed_control = "PROVISION_MOVEMENT"
    context_role = _table_context_role(section, table, compiled_specs=compiled_specs)
    if len(role_axis) >= 2:
        context_role = None
    context_role_source = None
    if (
        typed_control is None
        and context_role is None
        and _owner_visible(section, table, compiled_specs=compiled_specs)
        and role_axis <= {"PROVISION"}
        and anonymous_totals
        and any(
            ordinal in unbound_money_rows
            and type(rows[ordinal - 1]) is dict
            and rows[ordinal - 1].get("row_kind") == "ITEM"
            and "du phong" not in _normalized(rows[ordinal - 1].get("label_exact"))
            for ordinal in range(1, len(rows) + 1)
        )
        and not _has_subsidiary_evidence(rows)
    ):
        # Some statements print only investee names, a gross subtotal, the
        # explicit provision row, and a final net total below an exact family
        # owner.  The owner plus both exact controls identifies the anonymous
        # investee population as OTHER_LONG_TERM without any bank/value rule.
        context_role = "OTHER_LONG_TERM"
        context_role_source = "EXPLICIT_OWNER_ANONYMOUS_INVESTEES_WITH_TOTAL_CONTROLS"
    material = {
        "ambiguous_rows": ambiguous_rows,
        "anonymous_totals": anonymous_totals,
        "money_column_ordinals": money_ordinals,
        "owner_visible": _owner_visible(section, table, compiled_specs=compiled_specs),
        "role_hits": role_hits,
        "table_context_role": context_role,
        "typed_control_disposition": typed_control,
        "unbound_money_row_ordinals": unbound_money_rows,
    }
    if compound_role_projections:
        material["compound_role_projections"] = compound_role_projections
    if context_role_source is not None:
        material["table_context_role_source"] = context_role_source
    return {
        **material,
        "classification_id": "gjfolticv1:classification:" + canonical_json_sha256_v1(material),
    }


def _page_record_axis(page_records: Any) -> list[dict[str, Any]]:
    required = {
        "document_id",
        "document_ordinal",
        "page_json",
        "page_json_version_id",
        "physical_page",
        "selected_page_ordinal",
        "source_logical_name",
        "source_sha256",
    }
    if type(page_records) not in {list, tuple} or not page_records:
        raise _error("other-long-term-investment selected page records are absent")
    checked = []
    identity = None
    prior = None
    for raw in page_records:
        if (
            type(raw) is not dict
            or set(raw) != required
            or _DOCUMENT_ID.fullmatch(raw.get("document_id", "")) is None
            or type(raw.get("document_ordinal")) is not int
            or raw["document_ordinal"] <= 0
            or _PAGE_VERSION.fullmatch(raw.get("page_json_version_id", "")) is None
            or type(raw.get("physical_page")) is not int
            or raw["physical_page"] <= 0
            or type(raw.get("selected_page_ordinal")) is not int
            or raw["selected_page_ordinal"] <= 0
            or type(raw.get("source_logical_name")) is not str
            or not raw["source_logical_name"]
            or _SHA256.fullmatch(raw.get("source_sha256", "")) is None
            or type(raw.get("page_json")) is not dict
            or type(raw["page_json"].get("sections")) is not list
        ):
            raise _error("other-long-term-investment selected page record is invalid")
        current_identity = tuple(
            raw[key]
            for key in ("document_id", "document_ordinal", "source_logical_name", "source_sha256")
        )
        position = (raw["selected_page_ordinal"], raw["physical_page"])
        if identity is None:
            identity = current_identity
        elif identity != current_identity:
            raise _error("other-long-term-investment selected pages cross document identity")
        if prior is not None and position <= prior:
            raise _error("other-long-term-investment selected pages are not in source order")
        prior = position
        checked.append(canonical_clone_v1(raw))
    return checked


def _marker_matches(value: Any, aliases: Sequence[str]) -> str | None:
    matches = [alias for alias in aliases if _contains_alias(value, alias)]
    if not matches:
        return None
    maximum = max(map(len, matches))
    winners = sorted(alias for alias in matches if len(alias) == maximum)
    return winners[0] if len(winners) == 1 else None


def _heading_marker_matches(value: Any, aliases: Sequence[str]) -> str | None:
    """Match a narrative only when it is itself a structural heading."""

    matches = [alias for alias in aliases if _matches_alias(value, alias)]
    if not matches:
        return None
    maximum = max(map(len, matches))
    winners = sorted(alias for alias in matches if len(alias) == maximum)
    return winners[0] if len(winners) == 1 else None


def _region(item: Mapping[str, Any], fragment_ordinal: int) -> dict[str, Any]:
    record = item["record"]
    roles = sorted(
        {
            *(hit["role"] for hit in item["classification"]["role_hits"]),
            *(
                projection["projected_role"]
                for projection in item["classification"].get("compound_role_projections", [])
            ),
            *(
                []
                if item["classification"]["table_context_role"] is None
                else [item["classification"]["table_context_role"]]
            ),
        }
    )
    return {
        "component_roles": roles,
        "document_id": record["document_id"],
        "document_ordinal": record["document_ordinal"],
        "fragment_ordinal": fragment_ordinal,
        "page_json_version_id": record["page_json_version_id"],
        "physical_page": record["physical_page"],
        "section_id": item["section_id"],
        "selected_page_ordinal": record["selected_page_ordinal"],
        "source_logical_name": record["source_logical_name"],
        "source_sha256": record["source_sha256"],
        "table_id": item["table_id"],
    }


def coalesce_gemini_json_other_long_term_investments_document_v1(
    *, page_records: Any, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Select exactly one exhaustive owner/reset-fenced Family 17 cluster."""

    pages = _page_record_axis(page_records)
    inventory = []
    owner_markers = []
    reset_markers = []
    boundary_aliases = sorted(
        {
            *compiled_specs["query_policy"]["reset_aliases"],
            *compiled_specs["query_policy"]["hard_negative_aliases"],
        }
    )
    for record in pages:
        page_json = record["page_json"]
        primary = page_json.get("status") == "PRIMARY_FINANCIAL_STATEMENT"
        continuation_context_role = None
        for section_ordinal, section in enumerate(page_json["sections"], start=1):
            if type(section) is not dict:
                continue
            section_id = f"s{section_ordinal}"
            position = [record["selected_page_ordinal"], section_ordinal, 0]
            for value in [section.get("title_exact")]:
                if (
                    not primary
                    and (
                        alias := _marker_matches(
                            value, compiled_specs["query_policy"]["owner_aliases"]
                        )
                    )
                    is not None
                ):
                    owner_markers.append(
                        {
                            "_surface_ordinal": 0,
                            "alias": alias,
                            "position": position,
                            "source_exact": value,
                        }
                    )
                if (alias := _marker_matches(value, boundary_aliases)) is not None:
                    reset_markers.append(
                        {
                            "_surface_ordinal": 0,
                            "alias": alias,
                            "position": position,
                            "source_exact": value,
                        }
                    )
            narratives = section.get("narratives_exact")
            if type(narratives) is list:
                for narrative_ordinal, value in enumerate(narratives, start=1):
                    if (
                        not primary
                        and (
                            alias := _heading_marker_matches(
                                value, compiled_specs["query_policy"]["owner_aliases"]
                            )
                        )
                        is not None
                    ):
                        owner_markers.append(
                            {
                                "_surface_ordinal": narrative_ordinal,
                                "alias": alias,
                                "position": position,
                                "source_exact": value,
                            }
                        )
                    if (alias := _heading_marker_matches(value, boundary_aliases)) is not None:
                        reset_markers.append(
                            {
                                "_surface_ordinal": narrative_ordinal,
                                "alias": alias,
                                "position": position,
                                "source_exact": value,
                            }
                        )
            section_boundary_visible = _marker_matches(
                section.get("title_exact"), boundary_aliases
            ) is not None or (
                type(narratives) is list
                and any(
                    _heading_marker_matches(value, boundary_aliases) is not None
                    for value in narratives
                )
            )
            if section_boundary_visible:
                continuation_context_role = None
            tables = section.get("tables")
            if type(tables) is not list:
                continue
            for table_ordinal, table in enumerate(tables, start=1):
                if type(table) is not dict:
                    continue
                table_id = f"t{table_ordinal}"
                position = [record["selected_page_ordinal"], section_ordinal, table_ordinal]
                classification = classify_gemini_json_other_long_term_investments_table_v1(
                    page_json, section, table, compiled_specs=compiled_specs
                )
                classification = _with_effective_table_context_role(
                    classification,
                    section,
                    table_ordinal,
                    compiled_specs=compiled_specs,
                )
                if not primary and classification["typed_control_disposition"] is None:
                    row_owner_markers = [
                        row.get("label_exact")
                        for row in table.get("rows") or []
                        if type(row) is dict and row.get("row_kind") == "GROUP"
                    ]
                    for value in row_owner_markers:
                        if (
                            alias := _heading_marker_matches(
                                value, compiled_specs["query_policy"]["owner_aliases"]
                            )
                        ) is not None:
                            owner_markers.append(
                                {"alias": alias, "position": position, "source_exact": value}
                            )
                if (
                    not classification["role_hits"]
                    and classification["table_context_role"] is None
                    and continuation_context_role is not None
                    and section.get("title_exact") is None
                    and table.get("title_exact") is None
                    and _section_table_has_period_evidence(section, table)
                ):
                    material = {
                        key: canonical_clone_v1(value)
                        for key, value in classification.items()
                        if key != "classification_id"
                    }
                    material["table_context_role"] = continuation_context_role
                    material["table_context_role_source"] = (
                        "PRIOR_SECTION_EXPLICIT_ROLE_PERIOD_CONTINUATION"
                    )
                    classification = {
                        **material,
                        "classification_id": "gjfolticv1:classification:"
                        + canonical_json_sha256_v1(material),
                    }
                if classification["table_context_role"] is not None:
                    continuation_context_role = classification["table_context_role"]
                for value in (table.get("title_exact"),):
                    if (
                        classification["typed_control_disposition"] is None
                        and (
                            alias := _marker_matches(
                                value, compiled_specs["query_policy"]["owner_aliases"]
                            )
                        )
                        is not None
                    ):
                        owner_markers.append(
                            {"alias": alias, "position": position, "source_exact": value}
                        )
                    # A typed-control table cannot own Family 17, but its
                    # exact hard-negative/reset title still ends the preceding
                    # population.  Dropping that fence lets later, unrelated
                    # tables leak back into the earlier owner cluster.
                    if (alias := _marker_matches(value, boundary_aliases)) is not None:
                        reset_markers.append(
                            {"alias": alias, "position": position, "source_exact": value}
                        )
                if (
                    classification["role_hits"]
                    or classification["table_context_role"] is not None
                    or (classification["owner_visible"] and classification["anonymous_totals"])
                ):
                    inventory.append(
                        {
                            "classification": classification,
                            "position": position,
                            "record": record,
                            "section_id": section_id,
                            "table_id": table_id,
                        }
                    )

    actionable_inventory = [
        item for item in inventory if item["classification"]["typed_control_disposition"] is None
    ]

    def marker_key(marker: Mapping[str, Any]) -> tuple[int, int, int, int]:
        return (*marker["position"], int(marker.get("_surface_ordinal", 0)))

    groups: dict[tuple[int, int, int, int], dict[str, Any]] = {}
    for item in actionable_inventory:
        classification = item["classification"]
        prior_resets = [marker for marker in reset_markers if marker["position"] < item["position"]]
        latest_reset = max(prior_resets, key=marker_key) if prior_resets else None
        owners = [
            marker
            for marker in owner_markers
            if marker["position"] <= item["position"]
            and (latest_reset is None or marker_key(latest_reset) < marker_key(marker))
        ]
        if not owners:
            continue
        # Repeated running headers and per-period tables may restate the same
        # family owner.  Inside one reset-free interval those are continuation
        # evidence, not new populations.  Bind the interval to its first owner;
        # a typed reset starts a new interval and therefore a new key.
        owner = min(owners, key=marker_key)
        key = marker_key(owner)
        public_owner = {key: value for key, value in owner.items() if not key.startswith("_")}
        groups.setdefault(key, {"items": [], "owner": public_owner})["items"].append(item)

    complete_groups = []
    for group in groups.values():
        items = sorted(group["items"], key=lambda item: item["position"])
        roles = {
            *(hit["role"] for item in items for hit in item["classification"]["role_hits"]),
            *(
                projection["projected_role"]
                for item in items
                for projection in item["classification"].get("compound_role_projections", [])
            ),
            *(
                role
                for item in items
                if (role := item["classification"]["table_context_role"]) is not None
            ),
        }
        complete = any(
            set(combination) <= roles
            for combination in compiled_specs["topology"]["required_role_combinations"]
        )
        span = items[-1]["position"][0] - items[0]["position"][0]
        if complete and span <= compiled_specs["topology"]["limits"]["max_continuation_pages"]:
            complete_groups.append({**group, "items": items, "roles": sorted(roles)})

    reasons = []
    if len(complete_groups) > 1:
        reasons.append("MULTIPLE_COMPLETE_OWNER_CLUSTERS")
    selected = complete_groups[0] if len(complete_groups) == 1 else None
    if actionable_inventory and selected is None and not reasons:
        reasons.append("COMPLETE_OWNER_CLUSTER_NOT_RESOLVED")
    selected_keys = (
        {
            (item["record"]["page_json_version_id"], item["section_id"], item["table_id"])
            for item in selected["items"]
        }
        if selected is not None
        else set()
    )
    declared_inventory = []
    for item in inventory:
        key = (item["record"]["page_json_version_id"], item["section_id"], item["table_id"])
        if key in selected_keys:
            disposition = "SELECTED_FAMILY_COMPONENT"
        elif item["classification"]["typed_control_disposition"] is not None:
            disposition = "EXCLUDED_TYPED_CONTROL"
        else:
            disposition = "OUTSIDE_SELECTED_OWNER_FENCE_OR_INCOMPLETE_CLUSTER"
        declared_inventory.append(
            {
                "classification": canonical_clone_v1(item["classification"]),
                "disposition": disposition,
                "page_json_version_id": item["record"]["page_json_version_id"],
                "physical_page": item["record"]["physical_page"],
                "position": item["position"],
                "section_id": item["section_id"],
                "table_id": item["table_id"],
            }
        )
    regions = (
        [_region(item, ordinal) for ordinal, item in enumerate(selected["items"], start=1)]
        if selected is not None
        else []
    )
    status = (
        READY if regions and not reasons else UNRESOLVED if actionable_inventory else NOT_OBSERVED
    )
    material = {
        "component_regions": regions if status == READY else [],
        "declared_role_table_inventory": declared_inventory,
        "document_id": pages[0]["document_id"],
        "document_ordinal": pages[0]["document_ordinal"],
        "owner_receipt": None if selected is None else selected["owner"],
        "reasons": sorted(set(reasons)),
        "source_logical_name": pages[0]["source_logical_name"],
        "source_sha256": pages[0]["source_sha256"],
        "status": status,
    }
    return {
        **material,
        "cluster_id": "gjfoltifcv1:cluster:" + canonical_json_sha256_v1(material),
    }


def _region_axis(regions: Any) -> list[dict[str, Any]]:
    fields = {
        "component_roles",
        "document_id",
        "document_ordinal",
        "fragment_ordinal",
        "page_json_version_id",
        "physical_page",
        "section_id",
        "selected_page_ordinal",
        "source_logical_name",
        "source_sha256",
        "table_id",
    }
    if type(regions) not in {list, tuple} or not 1 <= len(regions) <= 16:
        raise _error("other-long-term-investment region axis cardinality is invalid")
    checked = []
    identity = None
    prior = None
    for ordinal, raw in enumerate(regions, start=1):
        if (
            type(raw) is not dict
            or set(raw) != fields
            or type(raw.get("component_roles")) is not list
            or raw["component_roles"] != sorted(set(raw["component_roles"]))
            or not set(raw["component_roles"]) <= _OUTPUT_ROLES
            or _DOCUMENT_ID.fullmatch(raw.get("document_id", "")) is None
            or type(raw.get("document_ordinal")) is not int
            or raw["document_ordinal"] <= 0
            or raw.get("fragment_ordinal") != ordinal
            or _PAGE_VERSION.fullmatch(raw.get("page_json_version_id", "")) is None
            or type(raw.get("physical_page")) is not int
            or raw["physical_page"] <= 0
            or type(raw.get("selected_page_ordinal")) is not int
            or raw["selected_page_ordinal"] <= 0
            or _SECTION_ID.fullmatch(raw.get("section_id", "")) is None
            or _TABLE_ID.fullmatch(raw.get("table_id", "")) is None
            or type(raw.get("source_logical_name")) is not str
            or not raw["source_logical_name"]
            or _SHA256.fullmatch(raw.get("source_sha256", "")) is None
        ):
            raise _error("other-long-term-investment region is invalid")
        current_identity = tuple(
            raw[key]
            for key in ("document_id", "document_ordinal", "source_logical_name", "source_sha256")
        )
        position = (
            raw["selected_page_ordinal"],
            int(raw["section_id"][1:]),
            int(raw["table_id"][1:]),
        )
        if identity is None:
            identity = current_identity
        elif identity != current_identity:
            raise _error("other-long-term-investment regions cross document identity")
        if prior is not None and position <= prior:
            raise _error("other-long-term-investment regions are not in source order")
        prior = position
        checked.append(canonical_clone_v1(raw))
    return checked


def build_gemini_json_other_long_term_investments_region_query_receipt_v1(
    regions: Any,
) -> dict[str, Any]:
    checked = _region_axis(regions)
    material = {
        "component_role_axis": [item["component_roles"] for item in checked],
        "exact_fragment_axis_sha256": canonical_json_sha256_v1(checked),
        "exact_fragment_count": len(checked),
        "format_version": ("GEMINI_JSON_OTHER_LONG_TERM_INVESTMENTS_REGION_QUERY_RECEIPT_V1"),
    }
    return {
        **material,
        "query_receipt_id": "gjfoltirqrv1:receipt:" + canonical_json_sha256_v1(material),
    }


def _source_ref(
    region: Mapping[str, Any],
    row_ordinal: int,
    row: Mapping[str, Any],
    *,
    money_column_ordinals: Sequence[int],
) -> dict[str, Any]:
    material = {
        "hierarchy_path_exact": canonical_clone_v1(row.get("hierarchy_path_exact")),
        "label_exact": row.get("label_exact"),
        "locator": canonical_clone_v1(region),
        "money_column_ordinals": list(money_column_ordinals),
        "row_id": f"r{row_ordinal}",
        "row_kind": row.get("row_kind"),
        "row_ordinal": row_ordinal,
    }
    projection = row.get("_compound_row_projection")
    if type(projection) is dict:
        material["compound_row_projection"] = canonical_clone_v1(projection)
        material["row_id"] = (
            f"r{projection['source_row_ordinal']}#line{projection['subrow_ordinal']}"
        )
    return material


def _source_money(value: Any) -> dict[str, Any]:
    if value is None or (type(value) is str and not value.strip()):
        return {
            "coefficient": None,
            "source_text": None,
            "state": "BLANK_SOURCE_CELL",
        }
    try:
        return _money(value)
    except ValueError:
        if type(value) is not str:
            raise
        body = value.strip()
        signed_body = body[1:-1].strip() if body.startswith("(") and body.endswith(")") else body
        if signed_body.startswith("-"):
            signed_body = signed_body[1:].strip()
        if re.fullmatch(r"[0-9]{1,3}(?:[.,][0-9]{3})*:[0-9]{3}", signed_body):
            parsed = _money(value.replace(":", "."))
            return {
                **parsed,
                "source_text": value,
                "state": "COLON_GROUP_SEPARATOR_INTEGER_IF_EQUATION_EXACT",
            }
        if body and all(character in "-–—−_:|·." or character.isspace() for character in body):
            return {
                "coefficient": 0,
                "source_text": value,
                "state": "PUNCTUATION_PLACEHOLDER_ZERO_IF_EQUATION_EXACT",
            }
        raise


def _metric_kind(column: Mapping[str, Any]) -> str:
    header = _normalized(_header_text(column))
    if any(token in header for token in _CARRYING_METRIC_TOKENS):
        return "CARRYING_VALUE"
    if "gia goc quy doi" in header:
        return "REPORTING_CURRENCY_COST"
    if any(token in header for token in ("gia goc", "nguyen gia", "cost")):
        return "COST"
    return "GENERIC_AMOUNT"


def _select_metric_column(
    ordinals: Sequence[int], columns: Sequence[Mapping[str, Any]]
) -> tuple[int | None, list[str]]:
    carrying = [
        ordinal for ordinal in ordinals if _metric_kind(columns[ordinal - 1]) == "CARRYING_VALUE"
    ]
    if len(carrying) == 1:
        return carrying[0], []
    if len(carrying) > 1:
        return None, ["MULTIPLE_CARRYING_VALUE_COLUMNS_IN_ONE_PERIOD_LANE"]
    reporting_currency = [
        ordinal
        for ordinal in ordinals
        if _metric_kind(columns[ordinal - 1]) == "REPORTING_CURRENCY_COST"
    ]
    if len(reporting_currency) == 1:
        return reporting_currency[0], []
    if len(reporting_currency) > 1:
        return None, ["MULTIPLE_REPORTING_CURRENCY_COLUMNS_IN_ONE_PERIOD_LANE"]
    if len(ordinals) == 1:
        return ordinals[0], []
    return None, ["CARRYING_VALUE_COLUMN_NOT_UNIQUELY_RESOLVED"]


def _one_period_surface_signature(
    section: Mapping[str, Any], table: Mapping[str, Any]
) -> tuple[list[str] | None, list[str]]:
    for source_kind, value in (
        ("TABLE_TITLE", table.get("title_exact")),
        ("SECTION_TITLE", section.get("title_exact")),
    ):
        if type(value) is not str or not value.strip():
            continue
        dates = sorted(item.isoformat() for item in _surface_dates(value))
        if len(dates) > 1:
            return None, [f"MULTIPLE_PERIOD_DATES_IN_{source_kind}"]
        if len(dates) == 1:
            return ["DATE", dates[0]], []
        signature = _period_signature(value)
        if signature is not None:
            return list(signature), []
    narratives = section.get("narratives_exact")
    tables = section.get("tables")
    table_ordinal = next(
        (ordinal for ordinal, candidate in enumerate(tables or [], start=1) if candidate is table),
        None,
    )
    headings = [
        dates
        for value in (narratives if type(narratives) is list else [])
        if len(dates := _period_heading_dates(value)) == 1
    ]
    if len(headings) == 1 and type(tables) is list and len(tables) == 1:
        return ["DATE", headings[0][0]], []
    if (
        type(tables) is list
        and table_ordinal is not None
        and len(headings) == len(tables)
        and len({dates[0] for dates in headings}) == len(headings)
    ):
        return ["DATE", headings[table_ordinal - 1][0]], []
    return None, ["ONE_PERIOD_TABLE_SIGNATURE_NOT_RESOLVED"]


def _table_lane_axis(section: Mapping[str, Any], table: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve carrying-value columns for row, metric, or repeated-table layouts."""

    columns = table.get("columns")
    if type(columns) is not list:
        return {
            "complete": False,
            "lane_keys": [],
            "money_column_ordinals": [],
            "reasons": ["COLUMN_AXIS_INVALID"],
        }
    money_ordinals = [
        ordinal
        for ordinal, column in enumerate(columns, start=1)
        if type(column) is dict and column.get("value_kind") == "MONEY"
    ]
    if not money_ordinals:
        return {
            "complete": False,
            "lane_keys": [],
            "money_column_ordinals": [],
            "reasons": ["MONEY_COLUMN_AXIS_EMPTY"],
        }
    ordinary = _two_period_axis(table)
    if ordinary["complete"]:
        return {
            "complete": True,
            "lane_keys": canonical_clone_v1(ordinary["signatures"]),
            "layout_kind": "TWO_PERIOD_MONEY_COLUMNS",
            "money_column_ordinals": ordinary["money_column_ordinals"],
            "reasons": [],
            "selected_metric_kinds": [
                _metric_kind(columns[ordinal - 1]) for ordinal in ordinary["money_column_ordinals"]
            ],
            "source_period_axis": ordinary,
        }

    signatures_by_ordinal: dict[int, list[str] | None] = {}
    semantic_roles_by_ordinal: dict[int, list[str]] = {}
    reasons = []
    for ordinal in money_ordinals:
        header = _header_text(columns[ordinal - 1])
        dates = sorted(item.isoformat() for item in _surface_dates(header))
        semantic_roles = _semantic_period_roles(header)
        semantic_roles_by_ordinal[ordinal] = semantic_roles
        if len(dates) > 1:
            reasons.append(f"MULTIPLE_PERIOD_DATES_IN_MONEY_COLUMN:c{ordinal}")
            signatures_by_ordinal[ordinal] = None
        elif len(semantic_roles) > 1:
            reasons.append(f"MULTIPLE_SEMANTIC_PERIOD_ROLES_IN_MONEY_COLUMN:c{ordinal}")
            signatures_by_ordinal[ordinal] = None
        elif len(dates) == 1:
            signatures_by_ordinal[ordinal] = ["DATE", dates[0]]
        else:
            signatures_by_ordinal[ordinal] = (
                None if not semantic_roles else ["SEMANTIC_ALIAS", semantic_roles[0]]
            )
    present = [signature for signature in signatures_by_ordinal.values() if signature is not None]
    identities = {tuple(signature) for signature in present}
    if not reasons and len(present) == len(money_ordinals) and len(identities) == 1:
        signature = next(iter(identities))
        selected, selection_reasons = _select_metric_column(money_ordinals, columns)
        if selected is not None and not selection_reasons:
            return {
                "complete": True,
                "lane_keys": [list(signature)],
                "layout_kind": "ONE_PERIOD_MULTI_METRIC_COLUMNS",
                "money_column_ordinals": [selected],
                "reasons": [],
                "selected_metric_kinds": [_metric_kind(columns[selected - 1])],
                "source_period_axis": {
                    "signatures_by_money_column": {
                        f"c{ordinal}": value for ordinal, value in signatures_by_ordinal.items()
                    }
                },
            }
    if not reasons and len(present) == len(money_ordinals) and len(identities) == 2:
        if all(signature[0] == "DATE" for signature in identities):
            ordered = sorted(identities, key=lambda item: date.fromisoformat(item[1]), reverse=True)
            expected_role_by_signature = {
                ordered[0]: "CURRENT_PERIOD",
                ordered[1]: "COMPARATIVE_PERIOD",
            }
            for ordinal, signature in signatures_by_ordinal.items():
                if signature is None:
                    continue
                semantic_roles = semantic_roles_by_ordinal[ordinal]
                if (
                    len(semantic_roles) == 1
                    and semantic_roles[0] != expected_role_by_signature[tuple(signature)]
                ):
                    reasons.append(f"DATE_AND_SEMANTIC_PERIOD_EVIDENCE_CONFLICT:c{ordinal}")
        elif identities == {
            ("SEMANTIC_ALIAS", "CURRENT_PERIOD"),
            ("SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"),
        }:
            ordered = [
                ("SEMANTIC_ALIAS", "CURRENT_PERIOD"),
                ("SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"),
            ]
        else:
            ordered = []
            reasons.append("PERIOD_SIGNATURE_KINDS_OR_ROLES_CONFLICT")
        selected = []
        for signature in ordered:
            ordinals = [
                ordinal
                for ordinal, value in signatures_by_ordinal.items()
                if value is not None and tuple(value) == signature
            ]
            chosen, selection_reasons = _select_metric_column(ordinals, columns)
            reasons.extend(selection_reasons)
            if chosen is not None:
                selected.append(chosen)
        if not reasons and len(selected) == 2:
            return {
                "complete": True,
                "lane_keys": [list(value) for value in ordered],
                "layout_kind": "TWO_PERIOD_MULTI_METRIC_COLUMNS",
                "money_column_ordinals": selected,
                "reasons": [],
                "selected_metric_kinds": [
                    _metric_kind(columns[ordinal - 1]) for ordinal in selected
                ],
                "source_period_axis": {
                    "signatures_by_money_column": {
                        f"c{ordinal}": value for ordinal, value in signatures_by_ordinal.items()
                    }
                },
            }
    shared_period_pairs = set()
    narratives = section.get("narratives_exact")
    if type(narratives) is list:
        for value in narratives:
            if type(value) is not str:
                continue
            folded = _normalized(value)
            narrative_dates = sorted(
                (item.isoformat() for item in _surface_dates(value)),
                key=date.fromisoformat,
                reverse=True,
            )
            if len(narrative_dates) == 2 and (" va " in f" {folded} " or " and " in f" {folded} "):
                shared_period_pairs.add(tuple(narrative_dates))
    shared_column, shared_reasons = _select_metric_column(money_ordinals, columns)
    if len(shared_period_pairs) == 1 and shared_column is not None and not shared_reasons:
        pair = next(iter(shared_period_pairs))
        return {
            "complete": True,
            "lane_keys": [["DATE", pair[0]], ["DATE", pair[1]]],
            "layout_kind": "ONE_SHARED_VALUE_FOR_TWO_EXPLICIT_PERIODS",
            "money_column_ordinals": [shared_column, shared_column],
            "reasons": [],
            "selected_metric_kinds": [
                _metric_kind(columns[shared_column - 1]),
                _metric_kind(columns[shared_column - 1]),
            ],
            "source_period_axis": {
                "shared_value_period_pair": list(pair),
                "source": "SECTION_NARRATIVE_EXPLICIT_TWO_PERIODS",
            },
        }
    if len(shared_period_pairs) > 1:
        reasons.append("MULTIPLE_SHARED_VALUE_PERIOD_PAIRS_IN_SECTION")
    signature, signature_reasons = _one_period_surface_signature(section, table)
    selected, selection_reasons = _select_metric_column(money_ordinals, columns)
    reasons.extend(signature_reasons)
    reasons.extend(selection_reasons)
    if signature is not None and selected is not None and not reasons:
        return {
            "complete": True,
            "lane_keys": [signature],
            "layout_kind": "ONE_PERIOD_CARRYING_VALUE_TABLE",
            "money_column_ordinals": [selected],
            "reasons": [],
            "selected_metric_kinds": [_metric_kind(columns[selected - 1])],
            "source_period_axis": {"signature": signature},
        }
    return {
        "complete": False,
        "lane_keys": [],
        "layout_kind": None,
        "money_column_ordinals": money_ordinals,
        "reasons": sorted(set(reasons or ordinary.get("reasons", []))),
        "source_period_axis": ordinary,
    }


def _family_document_unit_context_axis(
    page_json_by_version: Mapping[str, dict[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Add exact Family 17 owner-row evidence to a mixed-unit document.

    Some filings contain both exact-VND and million-VND renditions of the
    primary statements while the corresponding note omits its local unit.
    A document-wide unit vote is therefore unsafe.  When the shared context is
    mixed, retain explicit-unit Family 17 owner rows so ``_unit_axis`` can bind
    a unitless note only through an exact two-period total and period-axis
    match.
    """

    base = _document_unit_context_axis(page_json_by_version, compiled_specs=compiled_specs)
    if base["status"] == "UNIQUE":
        return base
    evidence_by_locator: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for evidence in base["evidence"]:
        evidence_by_locator[
            (
                evidence["page_json_version_id"],
                evidence["section_id"],
                evidence["table_id"],
            )
        ].append(evidence)
    owner_row_evidence = canonical_clone_v1(base["owner_row_evidence"])
    for page_json_version_id, page_json in sorted(page_json_by_version.items()):
        for section_ordinal, section in enumerate(page_json.get("sections") or [], start=1):
            if type(section) is not dict:
                continue
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                if type(table) is not dict:
                    continue
                section_id = f"s{section_ordinal}"
                table_id = f"t{table_ordinal}"
                unit_evidence = evidence_by_locator.get(
                    (page_json_version_id, section_id, table_id), []
                )
                identities = {
                    (item["canonical_unit"], item["magnitude_power10"])
                    for item in unit_evidence
                    if item["accepted"]
                }
                if len(identities) != 1:
                    continue
                period_axis = _two_period_axis(table)
                money_ordinals = period_axis.get("money_column_ordinals", [])
                signatures = period_axis.get("signatures", [])
                if not period_axis.get("complete"):
                    columns = table.get("columns")
                    money_ordinals = [
                        ordinal
                        for ordinal, column in enumerate(columns or [], start=1)
                        if type(column) is dict and column.get("value_kind") == "MONEY"
                    ]
                    if len(money_ordinals) != 2:
                        continue
                    headers = [
                        _normalized(_header_text(columns[ordinal - 1]))
                        for ordinal in money_ordinals
                    ]
                    if not (
                        any(token in headers[0] for token in ("cuoi ky", "cuoi quy", "cuoi nam"))
                        and any(token in headers[1] for token in ("dau ky", "dau nam"))
                    ):
                        continue
                    signatures = [
                        ["SEMANTIC_ALIAS", "CURRENT_PERIOD"],
                        ["SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"],
                    ]
                canonical_unit, magnitude_power10 = next(iter(identities))
                for row_ordinal, row in enumerate(table.get("rows") or [], start=1):
                    if (
                        type(row) is not dict
                        or _marker_matches(
                            row.get("label_exact"), compiled_specs["query_policy"]["owner_aliases"]
                        )
                        is None
                        or type(row.get("values_exact")) is not list
                    ):
                        continue
                    try:
                        cells = [
                            _source_money(row["values_exact"][ordinal - 1])
                            for ordinal in money_ordinals
                        ]
                    except (IndexError, ValueError):
                        continue
                    if any(cell["coefficient"] is None for cell in cells):
                        continue
                    owner_row_evidence.append(
                        {
                            "canonical_unit": canonical_unit,
                            "coefficients": [cell["coefficient"] for cell in cells],
                            "magnitude_power10": magnitude_power10,
                            "page_json_version_id": page_json_version_id,
                            "period_axis_complete": True,
                            "period_signatures": canonical_clone_v1(signatures),
                            "row_ordinal": row_ordinal,
                            "section_id": section_id,
                            "source_exact": unit_evidence[0]["source_exact"],
                            "source_kind": ("EXPLICIT_UNIT_OTHER_LONG_TERM_INVESTMENT_OWNER_ROW"),
                            "table_id": table_id,
                        }
                    )
    return {
        **base,
        "owner_row_evidence": owner_row_evidence,
        "owner_row_evidence_axis_sha256": canonical_json_sha256_v1(owner_row_evidence),
        "rule": ("MIXED_DOCUMENT_UNITS_REQUIRE_EXACT_FAMILY_OWNER_ROW_VALUE_AND_PERIOD_MATCH"),
    }


def _local_record(
    role: str,
    cells: Sequence[Mapping[str, Any]],
    lane_keys: Sequence[Sequence[str]],
    source_refs: Sequence[Mapping[str, Any]],
    state: str,
    valuation_basis: str = "GENERIC_AMOUNT",
) -> dict[str, Any]:
    return {
        "cells": canonical_clone_v1(cells),
        "lane_keys": canonical_clone_v1(lane_keys),
        "role": role,
        "source_refs": canonical_clone_v1(source_refs),
        "state": state,
        "valuation_basis": valuation_basis,
    }


def _local_coefficients(record: Mapping[str, Any]) -> list[int | None]:
    return [cell["coefficient"] for cell in record["cells"]]


def _local_equation(
    *,
    equation_kind: str,
    components: Sequence[Mapping[str, Any]],
    result: Mapping[str, Any],
    multipliers: Sequence[int] | None = None,
) -> dict[str, Any]:
    weights = list(multipliers) if multipliers is not None else [1] * len(components)
    result_values = _local_coefficients(result)
    sums: list[int | None] = []
    lane_statuses = []
    for lane, result_value in enumerate(result_values):
        component_values = [record["cells"][lane]["coefficient"] for record in components]
        if result_value is None or any(value is None for value in component_values):
            sums.append(None)
            lane_statuses.append("INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL")
            continue
        computed = sum(
            weight * value for value, weight in zip(component_values, weights, strict=True)
        )
        sums.append(computed)
        lane_statuses.append("EXACT" if computed == result_value else "MISMATCH")
    if all(status == "EXACT" for status in lane_statuses):
        status = "EXACT"
    elif any(status == "MISMATCH" for status in lane_statuses):
        status = "MISMATCH"
    else:
        status = "INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"
    material = {
        "component_roles": [record["role"] for record in components],
        "component_source_refs": [
            canonical_clone_v1(record["source_refs"]) for record in components
        ],
        "component_sums": sums,
        "equation_kind": equation_kind,
        "lane_keys": canonical_clone_v1(result["lane_keys"]),
        "multipliers": weights,
        "result_coefficients": result_values,
        "result_role": result["role"],
        "result_source_refs": canonical_clone_v1(result["source_refs"]),
        "status": status,
    }
    if status == "INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL":
        material["lane_statuses"] = lane_statuses
    return {
        **material,
        "equation_id": "gjfoltiev1:equation:" + canonical_json_sha256_v1(material),
    }


def _row_local_record(
    role: str,
    row_ordinal: int,
    row: Mapping[str, Any],
    *,
    region: Mapping[str, Any],
    lane_axis: Mapping[str, Any],
    state: str,
) -> dict[str, Any] | None:
    values = row.get("values_exact")
    if type(values) is not list:
        return None
    ordinals = lane_axis["money_column_ordinals"]
    if any(ordinal > len(values) for ordinal in ordinals):
        return None
    cells = [_source_money(values[ordinal - 1]) for ordinal in ordinals]
    metric_kinds = lane_axis.get("selected_metric_kinds", [])
    label = _normalized(row.get("label_exact"))
    if metric_kinds and all(kind == "CARRYING_VALUE" for kind in metric_kinds):
        valuation_basis = "CARRYING_VALUE"
    elif metric_kinds and all(kind == "REPORTING_CURRENCY_COST" for kind in metric_kinds):
        valuation_basis = "REPORTING_CURRENCY_COST"
    elif "gia goc" in label or (metric_kinds and all(kind == "COST" for kind in metric_kinds)):
        valuation_basis = "COST"
    else:
        valuation_basis = "GENERIC_AMOUNT"
    return _local_record(
        role,
        cells,
        lane_axis["lane_keys"],
        [
            _source_ref(
                region,
                row_ordinal,
                row,
                money_column_ordinals=ordinals,
            )
        ],
        state,
        valuation_basis,
    )


def _same_local_lane_axis(records: Sequence[Mapping[str, Any]]) -> bool:
    return bool(records) and all(
        records[0]["lane_keys"] == record["lane_keys"] for record in records
    )


def _exact_total_matches(
    components: Sequence[Mapping[str, Any]],
    totals: Sequence[Mapping[str, Any]],
    *,
    equation_kind: str,
    multipliers: Sequence[int] | None = None,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Match a printed total without fabricating values for blank lanes.

    A source-visible total can still identify the schema role when every
    observed lane closes, while another lane is explicitly blank in at least
    one source row.  The latter lane remains incomplete (and its mapping cell
    remains null); it is never promoted to an exact equation or inferred zero.
    """

    if not components or not _same_local_lane_axis(components):
        return []
    matches = []
    for total in totals:
        if total["lane_keys"] != components[0]["lane_keys"]:
            continue
        equation = _local_equation(
            equation_kind=equation_kind,
            components=components,
            result=total,
            multipliers=multipliers,
        )
        observed_lane_match = (
            equation["status"] == "INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"
            and "EXACT" in equation.get("lane_statuses", [])
            and set(equation.get("lane_statuses", []))
            <= {"EXACT", "INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"}
        )
        if observed_lane_match:
            equation = _local_equation(
                equation_kind=(
                    "OBSERVED_LANES_EXACT_REMAINDER_BLANK_" + equation_kind.removeprefix("EXACT_")
                ),
                components=components,
                result=total,
                multipliers=multipliers,
            )
        if equation["status"] == "EXACT" or observed_lane_match:
            matches.append((canonical_clone_v1(total), equation))
    return matches


def _extract_table_local_records(
    *,
    page_json: Mapping[str, Any],
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    region: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
    document_unit_context: Mapping[str, Any],
) -> dict[str, Any]:
    classification = classify_gemini_json_other_long_term_investments_table_v1(
        page_json, section, table, compiled_specs=compiled_specs
    )
    classification = _with_effective_table_context_role(
        classification,
        section,
        int(region["table_id"][1:]),
        compiled_specs=compiled_specs,
    )
    if (
        not classification["role_hits"]
        and classification["table_context_role"] is None
        and len(region["component_roles"]) == 1
        and region["component_roles"][0] in _DETAIL_ROLES | {"OTHER_LONG_TERM"}
        and section.get("title_exact") is None
        and _section_table_has_period_evidence(section, table)
    ):
        material = {
            key: canonical_clone_v1(value)
            for key, value in classification.items()
            if key != "classification_id"
        }
        material["table_context_role"] = region["component_roles"][0]
        material["table_context_role_source"] = (
            "QUERY_SEALED_PRIOR_SECTION_EXPLICIT_ROLE_PERIOD_CONTINUATION"
        )
        classification = {
            **material,
            "classification_id": "gjfolticv1:classification:" + canonical_json_sha256_v1(material),
        }
    expected_roles = sorted(
        {
            *(hit["role"] for hit in classification["role_hits"]),
            *(
                projection["projected_role"]
                for projection in classification.get("compound_role_projections", [])
            ),
            *(
                []
                if classification["table_context_role"] is None
                else [classification["table_context_role"]]
            ),
        }
    )
    if expected_roles != region["component_roles"]:
        raise _error("other-long-term-investment fragment classification drifted")
    lane_axis = _table_lane_axis(section, table)
    role_specific_lane_axes = _two_period_role_specific_lane_axes(table)
    use_role_specific_axes = bool(
        role_specific_lane_axes
        and expected_roles
        and set(expected_roles) <= set(role_specific_lane_axes)
        and (not lane_axis["complete"] or bool(classification.get("compound_role_projections")))
    )
    effective_lane_axis = (
        {
            "complete": True,
            "lane_keys": role_specific_lane_axes[expected_roles[0]]["lane_keys"],
            "layout_kind": "TWO_PERIOD_ROLE_SPECIFIC_MULTI_METRIC_COLUMNS",
            "money_column_ordinals": sorted(
                {
                    ordinal
                    for role in expected_roles
                    for ordinal in role_specific_lane_axes[role]["money_column_ordinals"]
                }
            ),
            "reasons": [],
            "role_lane_axes": {role: role_specific_lane_axes[role] for role in expected_roles},
        }
        if use_role_specific_axes
        else lane_axis
    )
    unit_table = canonical_clone_v1(table)
    if effective_lane_axis["complete"]:
        columns = table.get("columns")
        assert type(columns) is list
        selected_columns = []
        for ordinal in effective_lane_axis["money_column_ordinals"]:
            column = canonical_clone_v1(columns[ordinal - 1])
            column["header_path_exact"] = [_header_text(column)]
            selected_columns.append(column)
        unit_table["columns"] = selected_columns
    unit_axis = _unit_axis(
        unit_table,
        compiled_specs=compiled_specs,
        document_unit_context=document_unit_context,
    )
    if effective_lane_axis["complete"] and not unit_axis["complete"]:
        # Gemini can split one printed unit over adjacent header lines (for
        # example, "triệu" then "đồng").  Rejoin whitespace only; the exact
        # tokens and declared binding still have to resolve uniquely.
        joined_unit_table = canonical_clone_v1(unit_table)
        for column in joined_unit_table.get("columns") or []:
            if type(column) is dict:
                column["header_path_exact"] = [" ".join(_header_text(column).split())]
        joined_unit_axis = _unit_axis(
            joined_unit_table,
            compiled_specs=compiled_specs,
            document_unit_context=document_unit_context,
        )
        if joined_unit_axis["complete"]:
            unit_axis = joined_unit_axis
    receipt = {
        "classification": classification,
        "lane_axis": effective_lane_axis,
        "region": canonical_clone_v1(region),
        "unit_axis": unit_axis,
    }
    if not effective_lane_axis["complete"] or not unit_axis["complete"]:
        return {
            "equations": [],
            "local_records": [],
            "receipt": receipt,
            "unconsumed_reason": (
                "FRAGMENT_PERIOD_OR_UNIT_AXIS_NOT_LOCALLY_USABLE_AS_MAPPING_EVIDENCE"
            ),
        }
    rows = table.get("rows")
    assert type(rows) is list
    if use_role_specific_axes:
        if unit_axis.get("source") == "DOCUMENT_EXPLICIT_TABLE_UNIT_CONSENSUS":
            return {
                "equations": [],
                "local_records": [],
                "receipt": receipt,
                "unconsumed_reason": ("ROLE_SPECIFIC_MULTI_METRIC_UNIT_NOT_LOCAL_TO_FRAGMENT"),
            }
        local_records = []
        parse_reasons = []
        for hit in classification["role_hits"]:
            row_ordinal = hit["row_ordinal"]
            row = rows[row_ordinal - 1]
            if type(row) is not dict:
                continue
            try:
                record = _row_local_record(
                    hit["role"],
                    row_ordinal,
                    row,
                    region=region,
                    lane_axis=role_specific_lane_axes[hit["role"]],
                    state="SOURCE_OBSERVED_ROLE_ROW_ON_EXACT_ROLE_METRIC_AXIS",
                )
            except ValueError:
                parse_reasons.append(f"MONEY_CELL_NOT_EXACT_INTEGER:r{row_ordinal}")
                continue
            if record is not None:
                local_records.append(record)
        for projection_ordinal, projection in enumerate(
            classification.get("compound_role_projections", []), start=1
        ):
            row_ordinal = projection["source_row_ordinal"]
            row = rows[row_ordinal - 1]
            if type(row) is not dict:
                continue
            projected_row = canonical_clone_v1(row)
            projected_row["_compound_row_projection"] = {
                "source_row_ordinal": row_ordinal,
                "subrow_ordinal": projection_ordinal,
            }
            try:
                record = _row_local_record(
                    projection["projected_role"],
                    row_ordinal,
                    projected_row,
                    region=region,
                    lane_axis=role_specific_lane_axes[projection["projected_role"]],
                    state="SOURCE_OBSERVED_COMPOUND_ROLE_METRIC_PROJECTION",
                )
            except ValueError:
                parse_reasons.append(f"MONEY_CELL_NOT_EXACT_INTEGER:r{row_ordinal}")
                continue
            if record is not None:
                local_records.append(record)
        if parse_reasons:
            receipt["parse_reasons"] = sorted(set(parse_reasons))
        observed_roles = {record["role"] for record in local_records}
        missing_roles = set(expected_roles) - observed_roles
        return {
            "equations": [],
            "local_records": local_records,
            "proven_roles": [],
            "receipt": receipt,
            "unconsumed_reason": (
                None
                if not parse_reasons and not missing_roles
                else "ROLE_SPECIFIC_MULTI_METRIC_FRAGMENT_NOT_EXACTLY_EXTRACTED"
            ),
        }
    hit_by_row = {hit["row_ordinal"]: hit["role"] for hit in classification["role_hits"]}
    row_records: dict[int, dict[str, Any]] = {}
    parse_reasons = []
    for row_ordinal, row in enumerate(rows, start=1):
        if type(row) is not dict:
            continue
        try:
            record = _row_local_record(
                "SOURCE_ROW",
                row_ordinal,
                row,
                region=region,
                lane_axis=lane_axis,
                state="SOURCE_OBSERVED_ROW",
            )
        except ValueError:
            parse_reasons.append(f"MONEY_CELL_NOT_EXACT_INTEGER:r{row_ordinal}")
            continue
        if record is not None:
            row_records[row_ordinal] = record
    if parse_reasons:
        receipt["parse_reasons"] = sorted(set(parse_reasons))

    local_records = []
    blank_group_hits = []
    for row_ordinal, role in hit_by_row.items():
        record = row_records.get(row_ordinal)
        if record is None:
            continue
        if (
            all(cell["source_text"] is None for cell in record["cells"])
            and rows[row_ordinal - 1].get("row_kind") == "GROUP"
        ):
            blank_group_hits.append((row_ordinal, role))
            continue
        local_records.append(
            _local_record(
                role,
                record["cells"],
                record["lane_keys"],
                record["source_refs"],
                "SOURCE_OBSERVED_ROLE_ROW",
                record["valuation_basis"],
            )
        )

    anonymous_totals = []
    for item in classification["anonymous_totals"]:
        row_ordinal = item["row_ordinal"]
        record = row_records.get(row_ordinal)
        if record is not None and not all(cell["source_text"] is None for cell in record["cells"]):
            anonymous_totals.append(record)
    used_total_rows: set[int] = set()
    equations = []
    proven_roles: set[str] = set()

    all_visible_item_rows = [
        record
        for ordinal, record in row_records.items()
        if rows[ordinal - 1].get("row_kind") == "ITEM"
        and any(cell["source_text"] is not None for cell in record["cells"])
    ]
    all_item_matches = _exact_total_matches(
        all_visible_item_rows,
        anonymous_totals,
        equation_kind="EXACT_VISIBLE_ALL_ITEM_ROWS_EQUAL_TABLE_TOTAL_CONTROL",
    )
    if len(all_item_matches) == 1:
        _control_total, control_equation = all_item_matches[0]
        equations.append(control_equation)
        proven_roles.update(role for ordinal, role in hit_by_row.items() if ordinal in row_records)

    for group_ordinal, role in blank_group_hits:
        following_group = next(
            (
                ordinal
                for ordinal in range(group_ordinal + 1, len(rows) + 1)
                if type(rows[ordinal - 1]) is dict and rows[ordinal - 1].get("row_kind") == "GROUP"
            ),
            len(rows) + 1,
        )
        components = [
            record
            for ordinal, record in row_records.items()
            if group_ordinal < ordinal < following_group
            and rows[ordinal - 1].get("row_kind") == "ITEM"
            and ordinal not in hit_by_row
            and any(cell["source_text"] is not None for cell in record["cells"])
        ]
        totals = [
            record
            for record in anonymous_totals
            if group_ordinal < record["source_refs"][0]["row_ordinal"] < following_group
        ]
        matches = _exact_total_matches(
            components,
            totals,
            equation_kind="EXACT_VISIBLE_GROUP_ITEMS_EQUAL_TRAILING_SUBTOTAL",
        )
        if len(matches) == 1:
            total, equation = matches[0]
            total_row = total["source_refs"][0]["row_ordinal"]
            used_total_rows.add(total_row)
            local_records.append(
                _local_record(
                    role,
                    total["cells"],
                    total["lane_keys"],
                    total["source_refs"],
                    (
                        "SOURCE_TRAILING_TOTAL_PROVEN_AS_BLANK_GROUP_ROLE"
                        if equation["status"] == "EXACT"
                        else "SOURCE_TRAILING_TOTAL_CORROBORATED_ON_OBSERVED_LANES_AS_BLANK_GROUP_ROLE"
                    ),
                    total["valuation_basis"],
                )
            )
            equations.append(equation)
            proven_roles.add(role)

    roles_present = {record["role"] for record in local_records}
    context_role = classification["table_context_role"]
    nested_records = [
        record
        for record in local_records
        if record["role"] in {"ORGANIZATION_PROJECT", "INVESTMENT_FUND"}
    ]
    inferred_context_role = context_role
    if inferred_context_role is None and nested_records:
        inferred_context_role = "OTHER_LONG_TERM"
    if inferred_context_role is not None and inferred_context_role not in roles_present:
        unbound_items = [
            record
            for ordinal, record in row_records.items()
            if rows[ordinal - 1].get("row_kind") == "ITEM"
            and ordinal not in hit_by_row
            and any(cell["source_text"] is not None for cell in record["cells"])
        ]
        component_variants = []
        if unbound_items:
            component_variants.append(("UNBOUND_DETAIL_ITEMS", unbound_items))
        if nested_records:
            component_variants.append(("DECLARED_NESTED_ROLES", nested_records))
        context_matches = []
        for kind, components in component_variants:
            totals = [
                record
                for record in anonymous_totals
                if record["source_refs"][0]["row_ordinal"] not in used_total_rows
            ]
            for total, equation in _exact_total_matches(
                components,
                totals,
                equation_kind=f"EXACT_{kind}_EQUAL_CONTEXT_ROLE_TOTAL",
            ):
                context_matches.append((total, equation))
        unique_matches = {
            (
                match[0]["source_refs"][0]["row_ordinal"],
                tuple(_local_coefficients(match[0])),
            ): match
            for match in context_matches
        }
        if len(unique_matches) == 1:
            total, equation = next(iter(unique_matches.values()))
            used_total_rows.add(total["source_refs"][0]["row_ordinal"])
            local_records.append(
                _local_record(
                    inferred_context_role,
                    total["cells"],
                    total["lane_keys"],
                    total["source_refs"],
                    (
                        "SOURCE_TOTAL_PROVEN_AS_CONTEXT_ROLE"
                        if equation["status"] == "EXACT"
                        else "SOURCE_TOTAL_CORROBORATED_ON_OBSERVED_LANES_AS_CONTEXT_ROLE"
                    ),
                    total["valuation_basis"],
                )
            )
            equations.append(equation)
            proven_roles.update({inferred_context_role, *equation["component_roles"]})

    top_records_by_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in local_records:
        if record["role"] in _TOP_LEVEL_ROLES:
            top_records_by_role[record["role"]].append(record)
    top_records = [values[0] for values in top_records_by_role.values() if len(values) == 1]
    non_provision = [record for record in top_records if record["role"] != "PROVISION"]
    remaining_totals = [
        record
        for record in anonymous_totals
        if record["source_refs"][0]["row_ordinal"] not in used_total_rows
    ]
    if non_provision and remaining_totals:
        gross_variants = [
            ("EXACT_VISIBLE_FAMILY_GROSS_TOTAL", non_provision, [1] * len(non_provision))
        ]
        net_variants = []
        provision = next((record for record in top_records if record["role"] == "PROVISION"), None)
        if provision is not None:
            net_variants.extend(
                [
                    (
                        "EXACT_VISIBLE_FAMILY_NET_WITH_SOURCE_SIGNED_PROVISION",
                        [*non_provision, provision],
                        [*([1] * len(non_provision)), 1],
                    ),
                    (
                        "EXACT_VISIBLE_FAMILY_NET_LESS_POSITIVE_PROVISION",
                        [*non_provision, provision],
                        [*([1] * len(non_provision)), -1],
                    ),
                ]
            )
        gross_matches = []
        for kind, components, multipliers in gross_variants:
            for total, equation in _exact_total_matches(
                components,
                remaining_totals,
                equation_kind=kind,
                multipliers=multipliers,
            ):
                gross_matches.append((total, equation))
        net_matches = []
        provision_row_ordinal = (
            None if provision is None else provision["source_refs"][0]["row_ordinal"]
        )
        for kind, components, multipliers in net_variants:
            for total, equation in _exact_total_matches(
                components,
                remaining_totals,
                equation_kind=kind,
                multipliers=multipliers,
            ):
                if (
                    provision_row_ordinal is not None
                    and total["source_refs"][0]["row_ordinal"] > provision_row_ordinal
                ):
                    net_matches.append((total, equation))
        # A table may expose both a gross subtotal and a final net total.  Once
        # a provision row exists, only the provision-inclusive equation is an
        # authoritative root mapping; the gross subtotal remains a control and
        # must not make the net row ambiguous.
        matches = net_matches if provision is not None else gross_matches
        structural_incomplete_match = False
        structurally_final_totals = [
            total
            for total in remaining_totals
            if total["source_refs"][0].get("row_kind") == "TOTAL"
        ]
        if not matches and len(structurally_final_totals) == 1:
            total = structurally_final_totals[0]
            total_row_ordinal = total["source_refs"][0]["row_ordinal"]
            structural_components = (
                [*non_provision, provision] if provision is not None else list(non_provision)
            )
            structural_equation = _local_equation(
                equation_kind=(
                    "STRUCTURALLY_BOUND_VISIBLE_FAMILY_TOTAL_WITH_INCOMPLETE_"
                    "BLANK_SOURCE_COMPONENTS"
                ),
                components=structural_components,
                result=total,
            )
            structural_incomplete_match = (
                total["source_refs"][0].get("row_kind") == "TOTAL"
                and total_row_ordinal == max(row_records)
                and all(
                    record["source_refs"][0]["row_ordinal"] < total_row_ordinal
                    for record in structural_components
                )
                and all(
                    type(cell["coefficient"]) is int and type(cell["source_text"]) is str
                    for cell in total["cells"]
                )
                and structural_equation["status"] == "INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"
                and set(structural_equation.get("lane_statuses", []))
                == {"INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"}
            )
            if structural_incomplete_match:
                matches = [(total, structural_equation)]
        unique_matches = {
            (
                match[0]["source_refs"][0]["row_ordinal"],
                tuple(_local_coefficients(match[0])),
            ): match
            for match in matches
        }
        if len(unique_matches) == 1:
            total, equation = next(iter(unique_matches.values()))
            local_records.append(
                _local_record(
                    "NET_TOTAL",
                    total["cells"],
                    total["lane_keys"],
                    total["source_refs"],
                    (
                        "SOURCE_VISIBLE_FAMILY_TOTAL_PROVEN_BY_EXACT_EQUATION"
                        if equation["status"] == "EXACT"
                        else "SOURCE_VISIBLE_FAMILY_TOTAL_STRUCTURALLY_BOUND_WITH_INCOMPLETE_EQUATION"
                        if structural_incomplete_match
                        else "SOURCE_VISIBLE_FAMILY_TOTAL_CORROBORATED_ON_OBSERVED_LANES"
                    ),
                    total["valuation_basis"],
                )
            )
            equations.append(equation)
            proven_roles.update({"NET_TOTAL", *equation["component_roles"]})

    return {
        "equations": equations,
        "local_records": local_records,
        "proven_roles": sorted(proven_roles),
        "receipt": receipt,
        "unconsumed_reason": None,
    }


def _canonical_lane_role(
    lane_key: Sequence[str],
    *,
    ordered_dates: Sequence[str],
    ordered_bare_years: Sequence[str] = (),
) -> str | None:
    if list(lane_key) == ["SEMANTIC_ALIAS", "CURRENT_PERIOD"]:
        return "CURRENT_PERIOD"
    if list(lane_key) == ["SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"]:
        return "COMPARATIVE_PERIOD"
    if len(lane_key) == 2 and lane_key[0] == "DATE":
        if ordered_dates and lane_key[1] == ordered_dates[0]:
            return "CURRENT_PERIOD"
        if len(ordered_dates) == 2 and lane_key[1] == ordered_dates[1]:
            return "COMPARATIVE_PERIOD"
    if len(lane_key) == 2 and lane_key[0] == "BARE_YEAR":
        if ordered_bare_years and lane_key[1] == ordered_bare_years[0]:
            return "CURRENT_PERIOD"
        if len(ordered_bare_years) == 2 and lane_key[1] == ordered_bare_years[1]:
            return "COMPARATIVE_PERIOD"
    return None


def _observation_priority(item: Mapping[str, Any]) -> tuple[int, int, int]:
    basis_priority = {
        "COST": 0,
        "REPORTING_CURRENCY_COST": 1,
        "GENERIC_AMOUNT": 2,
        "CARRYING_VALUE": 3,
    }
    state = item["state"]
    identity_priority = {
        "SOURCE_PRINTED_TOTAL_PROVEN_AS_EXPLICIT_SECTION_CONTEXT_ROLE": 4,
        "SOURCE_PRINTED_TOTAL_PROVEN_AS_EXPLICIT_TABLE_CONTEXT_ROLE": 4,
        "SOURCE_PRINTED_TOTAL_PROVEN_AS_ROW_POPULATION_CONTEXT_ROLE": 1,
        "SOURCE_TOTAL_PROVEN_AS_CONTEXT_ROLE": 1,
        "SOURCE_TOTAL_CORROBORATED_ON_OBSERVED_LANES_AS_CONTEXT_ROLE": 1,
        "SOURCE_TRAILING_TOTAL_PROVEN_AS_BLANK_GROUP_ROLE": 2,
        "SOURCE_TRAILING_TOTAL_CORROBORATED_ON_OBSERVED_LANES_AS_BLANK_GROUP_ROLE": 2,
        "SOURCE_OBSERVED_ROLE_ROW": 3,
    }.get(state, 0)
    return (
        identity_priority,
        basis_priority[item["valuation_basis"]],
        int("PROVEN" in state or "CORROBORATED" in state),
    )


def _global_records(
    local_records: Sequence[Mapping[str, Any]],
    *,
    proven_roles: set[str],
    allow_bare_year: bool = False,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    dates = sorted(
        {
            lane_key[1]
            for record in local_records
            for lane_key in record["lane_keys"]
            if lane_key[0] == "DATE"
        },
        key=date.fromisoformat,
        reverse=True,
    )
    bare_years = sorted(
        {
            lane_key[1]
            for record in local_records
            for lane_key in record["lane_keys"]
            if lane_key[0] == "BARE_YEAR"
        },
        reverse=True,
    )
    reasons = []
    if len(dates) > 2:
        reasons.append("DOCUMENT_MAPPING_PERIOD_AXIS_HAS_MORE_THAN_TWO_DATES")
    if allow_bare_year and len(bare_years) > 2:
        reasons.append("DOCUMENT_MAPPING_PERIOD_AXIS_HAS_MORE_THAN_TWO_BARE_YEARS")
    mixed_period_axis = bool(allow_bare_year and dates and bare_years)
    if mixed_period_axis:
        reasons.append("DOCUMENT_MAPPING_PERIOD_AXIS_MIXES_DATE_AND_BARE_YEAR")
    observations: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for record in local_records:
        for lane_key, cell in zip(record["lane_keys"], record["cells"], strict=True):
            lane_role = (
                None
                if mixed_period_axis
                else _canonical_lane_role(
                    lane_key,
                    ordered_dates=dates,
                    ordered_bare_years=bare_years if allow_bare_year else (),
                )
            )
            if lane_role is None:
                continue
            observations[record["role"]][lane_role].append(
                {
                    "cell": canonical_clone_v1(cell),
                    "source_refs": canonical_clone_v1(record["source_refs"]),
                    "state": record["state"],
                    "valuation_basis": record["valuation_basis"],
                }
            )
    records = {}
    partial = []
    optional_conditional_omissions = []
    for role, by_lane in observations.items():
        cells = []
        source_refs = []
        states = []
        missing = []
        for lane_role in ("CURRENT_PERIOD", "COMPARATIVE_PERIOD"):
            values = by_lane.get(lane_role, [])
            if not values:
                missing.append(lane_role)
                continue
            observed = [item for item in values if type(item["cell"]["coefficient"]) is int]
            selectable = observed or values
            coefficients = {item["cell"]["coefficient"] for item in selectable}
            if len(coefficients) > 1 and role == "PROVISION":
                absolute = {abs(value) for value in coefficients}
                negative = [item for item in selectable if item["cell"]["coefficient"] < 0]
                if len(absolute) == 1 and negative:
                    selected = negative[0]
                else:
                    reasons.append(f"CONFLICTING_SOURCE_VALUES_FOR_ROLE_LANE:{role}:{lane_role}")
                    continue
            elif len(coefficients) == 1:
                selected = selectable[0]
            else:
                maximum = max(_observation_priority(item) for item in selectable)
                preferred = [item for item in selectable if _observation_priority(item) == maximum]
                preferred_coefficients = {item["cell"]["coefficient"] for item in preferred}
                if len(preferred_coefficients) == 1:
                    selected = preferred[0]
                else:
                    reasons.append(f"CONFLICTING_SOURCE_VALUES_FOR_ROLE_LANE:{role}:{lane_role}")
                    continue
            cells.append(canonical_clone_v1(selected["cell"]))
            states.append(selected["state"])
            for item in selectable:
                if item["cell"]["coefficient"] == selected["cell"]["coefficient"]:
                    source_refs.extend(canonical_clone_v1(item["source_refs"]))
        if missing:
            partial.append({"missing_lanes": missing, "role": role})
            continue
        if len(cells) != 2:
            continue
        if all(cell["coefficient"] is None for cell in cells):
            optional_conditional_omissions.append(
                {
                    "reason": "ALL_LANES_BLANK_SOURCE_ROLE_OMITTED",
                    "role": role,
                    "source_refs": source_refs,
                }
            )
            continue
        if any(cell["state"].endswith("_IF_EQUATION_EXACT") for cell in cells):
            if role not in proven_roles:
                if all(cell["coefficient"] == 0 for cell in cells):
                    optional_conditional_omissions.append(
                        {
                            "reason": "UNPROVEN_OPTIONAL_ZERO_PLACEHOLDER_OMITTED",
                            "role": role,
                            "source_refs": source_refs,
                        }
                    )
                    continue
                reasons.append(f"UNPROVEN_CONDITIONAL_SOURCE_CELL_IN_MAPPING_ROLE:{role}")
            else:
                for cell in cells:
                    if cell["state"].endswith("_IF_EQUATION_EXACT"):
                        cell["state"] = "INFERRED_" + cell["state"]
        state = (
            "PARTIAL_SOURCE_OBSERVATION"
            if any(cell["coefficient"] is None for cell in cells)
            else states[0]
            if len(set(states)) == 1
            else "CORROBORATED_MULTI_SOURCE_PRESENTATIONS"
        )
        records[role] = {
            "cells": cells,
            "role": role,
            "source_refs": source_refs,
            "state": state,
        }
    return records, partial, sorted(set(reasons)), optional_conditional_omissions


def _authenticated_source_repair_receipt_v1(
    *,
    compiled_specs: Mapping[str, Any],
    repair: Mapping[str, Any],
) -> dict[str, Any]:
    material = {
        "artifact_ref": canonical_clone_v1(compiled_specs["source_repair_artifact_ref"]),
        "base_page_json_sha256": repair["base_page_json_sha256"],
        "base_table_sha256": repair["base_table_sha256"],
        "cell_repairs": canonical_clone_v1(repair["cell_repairs"]),
        "overlay_id": compiled_specs["source_repair_overlay"]["overlay_id"],
        "page_image": canonical_clone_v1(repair["page_image"]),
        "page_json_version_id": repair["page_json_version_id"],
        "physical_page": repair["physical_page"],
        "repair_id": repair["repair_id"],
        "rule": (
            "EXACT_SOURCE_PDF_RENDER_SELECTED_JSON_TABLE_ROW_COLUMN_NULL_TO_"
            "LITERAL_DASH_TRANSCRIPTION_ONLY_NO_EQUATION_DERIVATION"
        ),
        "section_id": repair["section_id"],
        "source_logical_name": repair["source_logical_name"],
        "source_sha256": repair["source_sha256"],
        "status": "AUTHENTICATED_PDF_VISIBLE_DASH_TRANSCRIBED",
        "table_id": repair["table_id"],
    }
    return {
        **material,
        "receipt_id": "gjfoltisrv1:receipt:" + canonical_json_sha256_v1(material),
    }


def _apply_authenticated_source_repair_artifact_v1(
    *,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    regions: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Apply registered visible-dash repairs to page clones only."""

    overlay = compiled_specs.get("source_repair_overlay")
    artifact_ref = compiled_specs.get("source_repair_artifact_ref")
    if type(overlay) is not dict or type(artifact_ref) is not dict:
        raise _error("other-long-term-investment compiled source-repair overlay is invalid")
    region_by_version: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for region in regions:
        version_id = region.get("page_json_version_id")
        if type(version_id) is not str:
            raise _error("other-long-term-investment source-repair region identity is invalid")
        region_by_version[version_id].append(region)
    effective_pages = dict(page_json_by_version)
    receipts = []
    for repair in overlay["repairs"]:
        version_id = repair["page_json_version_id"]
        matching_regions = region_by_version.get(version_id, [])
        if not matching_regions:
            continue
        if any(
            region.get("source_logical_name") != repair["source_logical_name"]
            or region.get("source_sha256") != repair["source_sha256"]
            or region.get("physical_page") != repair["physical_page"]
            for region in matching_regions
        ):
            raise _error("other-long-term-investment source-repair source binding drifted")
        base_page = page_json_by_version.get(version_id)
        if (
            type(base_page) is not dict
            or canonical_json_sha256_v1(base_page) != repair["base_page_json_sha256"]
        ):
            raise _error("other-long-term-investment source-repair base page drifted")
        _section, base_table = _source_table(
            base_page,
            section_id=repair["section_id"],
            table_id=repair["table_id"],
        )
        if canonical_json_sha256_v1(base_table) != repair["base_table_sha256"]:
            raise _error("other-long-term-investment source-repair base table drifted")
        effective_page = canonical_clone_v1(base_page)
        _effective_section, effective_table = _source_table(
            effective_page,
            section_id=repair["section_id"],
            table_id=repair["table_id"],
        )
        rows = effective_table.get("rows")
        columns = effective_table.get("columns")
        if type(rows) is not list or type(columns) is not list:
            raise _error("other-long-term-investment source-repair table axes are invalid")
        row_by_id: dict[str, dict[str, Any]] = {}
        for row_ordinal, row in enumerate(rows, start=1):
            row_id = f"r{row_ordinal}"
            if type(row) is not dict or row.get("row_id", row_id) != row_id or row_id in row_by_id:
                raise _error("other-long-term-investment source-repair row axis is invalid")
            row_by_id[row_id] = row
        for cell in repair["cell_repairs"]:
            row = row_by_id.get(cell["row_id"])
            column_index = cell["column_ordinal"] - 1
            values = row.get("values_exact") if type(row) is dict else None
            if (
                row is None
                or not (0 <= column_index < len(columns))
                or type(columns[column_index]) is not dict
                or columns[column_index].get("value_kind") != "MONEY"
                or type(values) is not list
                or len(values) != len(columns)
                or row.get("row_kind") != cell["row_kind"]
                or row.get("label_exact") != cell["row_label_exact"]
                or not same_typed_json_v1(
                    row.get("hierarchy_path_exact"), cell["row_hierarchy_path_exact"]
                )
                or not same_typed_json_v1(values[column_index], cell["original_value_exact"])
            ):
                raise _error("other-long-term-investment source-repair cell binding drifted")
            values[column_index] = cell["replacement_value_exact"]
        effective_pages[version_id] = effective_page
        receipts.append(
            _authenticated_source_repair_receipt_v1(
                compiled_specs=compiled_specs,
                repair=repair,
            )
        )
    receipts.sort(key=lambda item: item["repair_id"])
    return effective_pages, receipts


def evaluate_gemini_json_other_long_term_investments_family_cluster_v1(
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate one owner-bound optional-child/detail/net Family 17 cluster."""

    region_axis = _region_axis(regions)
    expected_receipt = build_gemini_json_other_long_term_investments_region_query_receipt_v1(
        region_axis
    )
    if type(query_receipt) is not dict or not same_typed_json_v1(query_receipt, expected_receipt):
        raise _error("other-long-term-investment query receipt does not bind exact fragments")
    effective_page_json_by_version, source_repair_overlay_receipts = (
        _apply_authenticated_source_repair_artifact_v1(
            page_json_by_version=page_json_by_version,
            compiled_specs=compiled_specs,
            regions=region_axis,
        )
    )
    document_unit_context = _family_document_unit_context_axis(
        effective_page_json_by_version, compiled_specs=compiled_specs
    )
    local_records = []
    equations = []
    proven_roles: set[str] = set()
    table_receipts = []
    pending_unusable_fragments = []
    mapping_units = set()
    for region in region_axis:
        page_json = effective_page_json_by_version.get(region["page_json_version_id"])
        if type(page_json) is not dict:
            raise _error("other-long-term-investment selected page JSON is absent")
        section, table = _source_table(
            page_json, section_id=region["section_id"], table_id=region["table_id"]
        )
        extracted = _extract_table_local_records(
            page_json=page_json,
            section=section,
            table=table,
            region=region,
            compiled_specs=compiled_specs,
            document_unit_context=document_unit_context,
        )
        local_records.extend(extracted["local_records"])
        if extracted["local_records"] and extracted["receipt"]["unit_axis"].get("complete"):
            mapping_units.add(extracted["receipt"]["unit_axis"]["canonical_unit"])
        equations.extend(extracted["equations"])
        proven_roles.update(extracted.get("proven_roles", []))
        table_receipts.append(extracted["receipt"])
        if extracted["unconsumed_reason"] is not None:
            pending_unusable_fragments.append(
                {
                    "reason": extracted["unconsumed_reason"],
                    "region": canonical_clone_v1(region),
                }
            )
    records, partial_roles, reasons, optional_conditional_omissions = _global_records(
        local_records, proven_roles=proven_roles
    )
    unused_fragments = []
    redundant_non_mapping_fragments = []
    available_roles = set(records)
    for item in pending_unusable_fragments:
        roles = set(item["region"]["component_roles"])
        if not roles or roles <= available_roles:
            redundant_non_mapping_fragments.append(
                {
                    "reason": "REDUNDANT_SCHEMA_ROLE_ALREADY_OBSERVED_ON_COMPLETE_LOCAL_AXIS",
                    "region": item["region"],
                    "source_unusable_reason": item["reason"],
                }
            )
        else:
            unused_fragments.append(item)
    reasons.extend(item["reason"] for item in unused_fragments)
    if len(mapping_units) != 1:
        reasons.append(
            "DOCUMENT_MAPPING_UNIT_AXIS_NOT_UNIQUE"
            if mapping_units
            else "DOCUMENT_MAPPING_UNIT_AXIS_EMPTY"
        )
    candidate_unit = next(iter(mapping_units)) if len(mapping_units) == 1 else None
    if not any(role in records for role in _OUTPUT_ROLES):
        reasons.append("MAPPABLE_CHILD_ROLE_FRONTIER_IS_EMPTY")
    mappings = []
    if not reasons:
        for role in [*compiled_specs["output_role_order"], "NET_TOTAL"]:
            record = records.get(role)
            if record is None:
                continue
            report_norm_id = (
                compiled_specs["schema"]["family_root_report_norm_id"]
                if role == "NET_TOTAL"
                else compiled_specs["bindings"][role]
            )
            material = {
                "report_norm_id": report_norm_id,
                "role": role,
                "row_id": (
                    record["source_refs"][0]["row_id"]
                    if len(record["source_refs"]) == 1
                    else "corroborated:" + role
                ),
                "source_refs": canonical_clone_v1(record["source_refs"]),
                "state": record["state"],
                "unit": candidate_unit,
                "values": canonical_clone_v1(record["cells"]),
            }
            mappings.append(
                {
                    **material,
                    "item_mapping_id": "gjfoltimv1:item:" + canonical_json_sha256_v1(material),
                }
            )
    first = region_axis[0]
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "closure_receipt": {
            "document_unit_context": document_unit_context,
            "equations": equations,
            **(
                {"source_repair_overlay_receipts": source_repair_overlay_receipts}
                if source_repair_overlay_receipts
                else {}
            ),
            **(
                {"optional_conditional_omissions": optional_conditional_omissions}
                if optional_conditional_omissions
                else {}
            ),
            "partial_role_observations": partial_roles,
            "query_receipt": canonical_clone_v1(expected_receipt),
            "rule": "EXACT_OPTIONAL_CHILD_DETAIL_SUBTOTAL_PROVISION_AND_NET_ALL_LANES",
            "structural_root_receipt": {
                "emitted_mapping": "NET_TOTAL" in records and not reasons,
                "mapping_policy": compiled_specs["schema"]["root_mapping_policy"],
                "report_norm_id": compiled_specs["schema"]["family_root_report_norm_id"],
                "role": compiled_specs["topology"]["parent"]["role"],
            },
            "table_receipts": table_receipts,
            "unused_typed_fragments": unused_fragments,
            **(
                {"redundant_non_mapping_fragments": redundant_non_mapping_fragments}
                if redundant_non_mapping_fragments
                else {}
            ),
        },
        "component_regions": region_axis,
        "document_id": first["document_id"],
        "family_id": compiled_specs["topology"]["family_id"],
        "mappings": mappings,
        "page_json_version_id": first["page_json_version_id"],
        "physical_page": first["physical_page"],
        "reasons": sorted(set(reasons)),
        "section_id": first["section_id"],
        "source_logical_name": first["source_logical_name"],
        "source_sha256": first["source_sha256"],
        "status": READY if mappings and not reasons else UNRESOLVED,
        "table_id": first["table_id"],
    }
    return {
        "candidate_id": "gjfolticv1:candidate:" + canonical_json_sha256_v1(material),
        **material,
    }


def validate_gemini_json_other_long_term_investments_family_candidate_replay_v1(
    value: Any,
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    rebuilt = evaluate_gemini_json_other_long_term_investments_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled_specs,
        query_receipt=query_receipt,
    )
    if type(value) is not dict or not same_typed_json_v1(value, rebuilt):
        raise _error("other-long-term-investment candidate does not replay exactly")
    return rebuilt


def build_gemini_json_indexed_other_long_term_investments_query_evidence_v1(
    *,
    selected_document_axis: Sequence[dict[str, Any]],
    selected_page_axis: Sequence[dict[str, Any]],
    document_clusters: Sequence[dict[str, Any]],
    query_policy_sha256: str,
) -> dict[str, Any]:
    """Seal the exhaustive selected-frontier Family 17 query projection."""

    documents = canonical_clone_v1(list(selected_document_axis))
    pages = canonical_clone_v1(list(selected_page_axis))
    clusters = canonical_clone_v1(list(document_clusters))
    dispositions = [
        {
            "cluster": canonical_clone_v1(cluster),
            "disposition": cluster.get("status"),
            "document_id": cluster.get("document_id"),
            "document_ordinal": cluster.get("document_ordinal"),
            "source_logical_name": cluster.get("source_logical_name"),
            "source_sha256": cluster.get("source_sha256"),
        }
        for cluster in clusters
    ]
    accepted = [cluster for cluster in clusters if cluster.get("status") == READY]
    receipt = {
        "accepted_cluster_axis_sha256": canonical_json_sha256_v1(accepted),
        "accepted_cluster_count": len(accepted),
        "accepted_fragment_count": sum(len(item.get("component_regions", [])) for item in accepted),
        "candidate_disposition_axis_sha256": canonical_json_sha256_v1(dispositions),
        "candidate_disposition_count": len(dispositions),
        "disposition_counts": {
            status: sum(item.get("disposition") == status for item in dispositions)
            for status in (READY, NOT_OBSERVED, UNRESOLVED)
        },
        "query_policy_sha256": query_policy_sha256,
        "selected_document_axis_sha256": canonical_json_sha256_v1(documents),
        "selected_document_count": len(documents),
        "selected_page_axis_sha256": canonical_json_sha256_v1(pages),
        "selected_page_count": len(pages),
        "selected_page_json_frontier_sha256": canonical_json_sha256_v1(
            [item.get("page_json_version_id") for item in pages]
        ),
    }
    material = {
        "accepted_clusters": accepted,
        "candidate_dispositions": dispositions,
        "format_version": INDEXED_QUERY_EVIDENCE_FORMAT_VERSION,
        "query_receipt": receipt,
        "selected_document_axis": documents,
        "selected_page_axis": pages,
    }
    return {
        **material,
        "query_evidence_id": "gjfoltieqv1:evidence:" + canonical_json_sha256_v1(material),
    }


def validate_gemini_json_indexed_other_long_term_investments_query_evidence_v1(
    value: Any, *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate the complete indexed document/page/disposition closure."""

    fields = {
        "accepted_clusters",
        "candidate_dispositions",
        "format_version",
        "query_evidence_id",
        "query_receipt",
        "selected_document_axis",
        "selected_page_axis",
    }
    if (
        compiled_specs.get("engine_format_version") != ENGINE_FORMAT_VERSION
        or type(value) is not dict
        or set(value) != fields
        or value.get("format_version") != INDEXED_QUERY_EVIDENCE_FORMAT_VERSION
        or any(
            type(value.get(field)) is not list
            for field in (
                "accepted_clusters",
                "candidate_dispositions",
                "selected_document_axis",
                "selected_page_axis",
            )
        )
        or type(value.get("query_receipt")) is not dict
    ):
        raise _error("indexed other-long-term-investment query evidence is invalid")
    documents = value["selected_document_axis"]
    pages = value["selected_page_axis"]
    dispositions = value["candidate_dispositions"]
    document_fields = {
        "document_id",
        "document_ordinal",
        "source_logical_name",
        "source_sha256",
    }
    if not documents or len(documents) != len(dispositions):
        raise _error("indexed other-long-term-investment document axis is incomplete")
    by_ordinal = {}
    for ordinal, document in enumerate(documents, start=1):
        if (
            type(document) is not dict
            or set(document) != document_fields
            or document.get("document_ordinal") != ordinal
            or _DOCUMENT_ID.fullmatch(document.get("document_id", "")) is None
            or type(document.get("source_logical_name")) is not str
            or not document["source_logical_name"]
            or _SHA256.fullmatch(document.get("source_sha256", "")) is None
        ):
            raise _error("indexed other-long-term-investment document axis is invalid")
        by_ordinal[ordinal] = document
    page_fields = document_fields | {
        "page_json_version_id",
        "physical_page",
        "selected_page_ordinal",
    }
    per_document = defaultdict(int)
    page_versions = []
    prior_document = 0
    for page in pages:
        document = by_ordinal.get(page.get("document_ordinal")) if type(page) is dict else None
        if (
            type(page) is not dict
            or set(page) != page_fields
            or document is None
            or any(page.get(field) != document[field] for field in document_fields)
            or _PAGE_VERSION.fullmatch(page.get("page_json_version_id", "")) is None
            or type(page.get("physical_page")) is not int
            or page["physical_page"] <= 0
            or page["document_ordinal"] < prior_document
        ):
            raise _error("indexed other-long-term-investment page axis is invalid")
        prior_document = page["document_ordinal"]
        per_document[page["document_ordinal"]] += 1
        if page.get("selected_page_ordinal") != per_document[page["document_ordinal"]]:
            raise _error("indexed other-long-term-investment page order is incomplete")
        page_versions.append(page["page_json_version_id"])
    if len(page_versions) != len(set(page_versions)) or set(per_document) != set(by_ordinal):
        raise _error("indexed other-long-term-investment page frontier is incomplete")
    accepted = []
    for ordinal, (document, disposition) in enumerate(
        zip(documents, dispositions, strict=True), start=1
    ):
        cluster = disposition.get("cluster") if type(disposition) is dict else None
        if (
            type(disposition) is not dict
            or set(disposition) != document_fields | {"cluster", "disposition"}
            or any(disposition.get(field) != document[field] for field in document_fields)
            or disposition.get("disposition") not in {READY, NOT_OBSERVED, UNRESOLVED}
            or type(cluster) is not dict
            or cluster.get("document_ordinal") != ordinal
            or any(cluster.get(field) != document[field] for field in document_fields)
            or cluster.get("status") != disposition["disposition"]
            or cluster.get("cluster_id")
            != "gjfoltifcv1:cluster:"
            + canonical_json_sha256_v1(
                {key: item for key, item in cluster.items() if key != "cluster_id"}
            )
        ):
            raise _error("indexed other-long-term-investment cluster binding drifted")
        regions = cluster.get("component_regions")
        reasons = cluster.get("reasons")
        if (
            type(reasons) is not list
            or reasons != sorted(set(reasons))
            or (cluster["status"] == READY and (not regions or reasons))
            or (cluster["status"] == NOT_OBSERVED and regions)
            or (cluster["status"] == UNRESOLVED and (not reasons or regions))
        ):
            raise _error("indexed other-long-term-investment disposition drifted")
        if cluster["status"] == READY:
            _region_axis(regions)
            accepted.append(cluster)
    if not same_typed_json_v1(value["accepted_clusters"], accepted):
        raise _error("indexed other-long-term-investment accepted projection drifted")
    expected_receipt = {
        "accepted_cluster_axis_sha256": canonical_json_sha256_v1(accepted),
        "accepted_cluster_count": len(accepted),
        "accepted_fragment_count": sum(len(item["component_regions"]) for item in accepted),
        "candidate_disposition_axis_sha256": canonical_json_sha256_v1(dispositions),
        "candidate_disposition_count": len(dispositions),
        "disposition_counts": {
            status: sum(item["disposition"] == status for item in dispositions)
            for status in (READY, NOT_OBSERVED, UNRESOLVED)
        },
        "query_policy_sha256": canonical_json_sha256_v1(compiled_specs["query_policy"]),
        "selected_document_axis_sha256": canonical_json_sha256_v1(documents),
        "selected_document_count": len(documents),
        "selected_page_axis_sha256": canonical_json_sha256_v1(pages),
        "selected_page_count": len(pages),
        "selected_page_json_frontier_sha256": canonical_json_sha256_v1(page_versions),
    }
    if not same_typed_json_v1(value["query_receipt"], expected_receipt):
        raise _error("indexed other-long-term-investment query receipt drifted")
    material = {key: canonical_clone_v1(value[key]) for key in fields - {"query_evidence_id"}}
    if value["query_evidence_id"] != "gjfoltieqv1:evidence:" + canonical_json_sha256_v1(material):
        raise _error("indexed other-long-term-investment evidence identity drifted")
    return canonical_clone_v1(value)


def validate_gemini_json_other_long_term_investments_sweep_query_bindings_v1(
    *, trials: Any, indexed_query_evidence: Any, compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Bind every sweep trial to its exhaustive query disposition."""

    evidence = validate_gemini_json_indexed_other_long_term_investments_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    documents = evidence["selected_document_axis"]
    if type(trials) is not list or len(trials) != len(documents):
        raise _error("other-long-term-investment sweep trial axis is incomplete")
    accepted = {item["document_ordinal"]: item for item in evidence["accepted_clusters"]}
    for ordinal, (trial, document, disposition) in enumerate(
        zip(trials, documents, evidence["candidate_dispositions"], strict=True), start=1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("source_logical_name") != document["source_logical_name"]
            or trial.get("source_sha256") != document["source_sha256"]
            or type(trial.get("candidates")) is not list
            or trial.get("candidate_count") != len(trial["candidates"])
        ):
            raise _error("other-long-term-investment sweep trial identity drifted")
        if disposition["disposition"] == READY:
            if len(trial["candidates"]) != 1:
                raise _error("accepted other-long-term-investment needs one candidate")
            candidate = trial["candidates"][0]
            if not same_typed_json_v1(
                candidate.get("component_regions"), accepted[ordinal]["component_regions"]
            ):
                raise _error("other-long-term-investment candidate regions drifted")
            if candidate.get("status") == READY:
                if (
                    trial.get("status") != READY
                    or trial.get("selected_candidate_id") != candidate.get("candidate_id")
                    or not same_typed_json_v1(trial.get("mappings"), candidate.get("mappings"))
                    or trial.get("reasons")
                ):
                    raise _error("other-long-term-investment READY trial drifted")
            elif (
                trial.get("status") != UNRESOLVED
                or trial.get("selected_candidate_id") is not None
                or trial.get("mappings")
                or trial.get("reasons") != candidate.get("reasons")
            ):
                raise _error("other-long-term-investment unresolved candidate drifted")
        elif disposition["disposition"] == NOT_OBSERVED:
            if (
                trial.get("status") != NOT_OBSERVED
                or trial["candidates"]
                or trial.get("mappings")
                or trial.get("reasons")
                or trial.get("selected_candidate_id") is not None
            ):
                raise _error("other-long-term-investment not-observed trial drifted")
        elif (
            trial.get("status") != UNRESOLVED
            or trial["candidates"]
            or trial.get("mappings")
            or trial.get("selected_candidate_id") is not None
            or trial.get("reasons") != disposition["cluster"]["reasons"]
        ):
            raise _error("other-long-term-investment unresolved disposition drifted")
    return canonical_clone_v1(trials)
