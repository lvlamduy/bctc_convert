"""Close project-owner catch-all and employee-average decisions.

The five base results remain byte-immutable.  This overlay binds their exact
source rows, the live TM schema graph, derives ACB monthly averages, and
aggregates catch-all rows once so downstream consumers cannot double count.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = Path("docs/experiments/E-0100-owner-adjudicated-catchall-average-closure-v1.json")
SCHEMA_GRAPH_PATH = Path("reference/schemas/schema_graph.jsonl")
SCHEMA_GRAPH_SHA256 = "a5ad1b0f1fa89fdf6d07c07b3a32b5bfc06b844433aeba3755be479844848e39"

BASES = {
    "credit_risk_provision": (
        Path(
            "docs/experiments/E-0089-credit-risk-provision-expense-8bank-codex-verified-mapping-v1.json"
        ),
        "4cca556974e99786454526466680a0ccefb7ae5271c5523804e3e69d34e03051",
        "e0089:result:dd1a86d9db53e3bc656b66177700b3c92000a30d0336f1cda7f600ba8edd2710",
    ),
    "other_activity": (
        Path("docs/experiments/E-0090-other-activity-8bank-codex-verified-mapping-v1.json"),
        "476ebe2f63b7285fd2dc43935ff022b6a763431bb4d8d465c80e077cd1da0d80",
        "e0090:result:85652f29f00e2db0b2030057a3e1478a91082adc31021e70ef638684412a321e",
    ),
    "employee_income": (
        Path("docs/experiments/E-0094-employee-income-8bank-codex-verified-mapping-v1.json"),
        "9e5ccefaa58769ed126fee71eb78d1c66d50ba0699006b2736de54e191d9300d",
        "e0094:result:30d685720a7731428e48bb664bb8630ddc0896f6da0537cb645d9fd2cdfa51a4",
    ),
    "state_budget": (
        Path(
            "docs/experiments/E-0095-state-budget-obligations-8bank-codex-verified-mapping-v1.json"
        ),
        "d22ab081487f1ddb3076b6069a09583018181f5c897bdb2f1332c3d673e06530",
        "e0095:result:a95b49ae447073af67bae4fce1fced8184a91d1b5ce3bebf945dad1671c95e37",
    ),
    "customer_collateral": (
        Path("docs/experiments/E-0096-customer-collateral-8bank-codex-verified-mapping-v1.json"),
        "ae784697189d893b5ec5af93cc179045f42ba8d43f4bc76cd182fb8ccddf0da6",
        "e0096:result:528759050a42e15e3a647037f2112f91f4c774c1f4345448a12ac1ad8263aea0",
    ),
}

FORMAT_VERSION = "PROJECT_OWNER_CATCHALL_AND_MONTHLY_AVERAGE_CLOSURE_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_BOUND_REPORT_PROJECT_OWNER_ADJUDICATION_EXACT_BASE_ROWS_LIVE_"
    "TM_SCHEMA_SIX_MONTH_TO_MONTHLY_DERIVATION_CATCHALL_AGGREGATION_ACCOUNTING_"
    "REPLAY_ONLY_NO_BASE_REWRITE_NO_CANONICAL_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "base_results_rewritten": False,
    "canonicalization_or_export_authority": False,
    "catchall_rows_double_mapped": False,
    "live_tm_schema_checked": True,
    "persisted_result_self_authenticating": False,
    "project_owner_adjudication_authority": True,
    "public_exact_replay_required": True,
    "source_values_changed_before_aggregation": False,
    "text_similarity_alone_used_for_mapping": False,
}

_SCHEMA = {
    1228: ("Dự phòng khác", 1221, 787),
    1239: ("Khác", 1229, 800),
    1267: ("Lương bình quân người/tháng", 1260, 843),
    1268: ("Thu nhập bình quân người/tháng", 1260, 844),
    1279: ("Các khoản phải nộp khác", 1269, 855),
    1288: ("Khác", 1280, 864),
}


class OwnerAdjudicatedClosureV1Error(ValueError):
    """A base result, source row, schema item, derivation, or closure drifted."""


def _error(message: str) -> OwnerAdjudicatedClosureV1Error:
    return OwnerAdjudicatedClosureV1Error(message)


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise _error(f"non-finite JSON constant in {label}: {value}")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise _error(f"duplicate JSON key in {label}: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"invalid UTF-8 JSON: {label}") from exc
    if type(value) is not dict:
        raise _error(f"JSON root must be one object: {label}")
    return value


def _stable_bytes(relative: Path) -> bytes:
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise _error(f"fixed path escaped project root: {relative}")
    directory_fd = os.open(PROJECT_ROOT, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in relative.parts[:-1]:
            child_fd = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = child_fd
        descriptor = os.open(
            relative.parts[-1],
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=directory_fd,
        )
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise _error(f"fixed input is not a single-link regular file: {relative}")
            chunks: list[bytes] = []
            while chunk := os.read(descriptor, 1 << 20):
                chunks.append(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
    finally:
        os.close(directory_fd)
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_nlink,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_nlink,
    ):
        raise _error(f"fixed input changed during read: {relative}")
    return b"".join(chunks)


def _base_inputs() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    values: dict[str, dict[str, Any]] = {}
    refs: dict[str, dict[str, Any]] = {}
    for name, (path, expected_sha, expected_id) in BASES.items():
        payload = _stable_bytes(path)
        digest = hashlib.sha256(payload).hexdigest()
        value = _strict_json(payload, path.as_posix())
        if digest != expected_sha or value.get("result_id") != expected_id:
            raise _error(f"pinned base result drifted: {name}")
        values[name] = value
        refs[name] = {
            "path": path.as_posix(),
            "result_id": expected_id,
            "sha256": digest,
            "size_bytes": len(payload),
        }
    return values, refs


def _schema_bindings() -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    payload = _stable_bytes(SCHEMA_GRAPH_PATH)
    if hashlib.sha256(payload).hexdigest() != SCHEMA_GRAPH_SHA256:
        raise _error("live schema graph drifted")
    selected: dict[int, dict[str, Any]] = {}
    for line in payload.splitlines():
        item = _strict_json(line, SCHEMA_GRAPH_PATH.as_posix())
        schema_id = item.get("schema_id")
        if schema_id not in _SCHEMA:
            continue
        name, parent, order = _SCHEMA[schema_id]
        if (
            item.get("canonical_name") != name
            or item.get("parent_id") != parent
            or item.get("display_order") != order
            or item.get("hierarchy_level") != 2
        ):
            raise _error(f"live schema item {schema_id} drifted")
        selected[schema_id] = {
            "canonical_name": name,
            "display_order": order,
            "hierarchy_level": 2,
            "report_norm_id": schema_id,
            "schema_parent_report_norm_id": parent,
        }
    if set(selected) != set(_SCHEMA):
        raise _error("live schema item denominator drifted")
    return selected, {
        "path": SCHEMA_GRAPH_PATH.as_posix(),
        "sha256": SCHEMA_GRAPH_SHA256,
        "size_bytes": len(payload),
    }


def _trial(base: dict[str, Any], bank: str) -> dict[str, Any]:
    matches = [
        trial for trial in base.get("trials", []) if trial.get("document_provenance") == bank
    ]
    if len(matches) != 1:
        raise _error(f"base result does not contain one {bank} trial")
    return matches[0]


def _source_row(trial: dict[str, Any], row_id: str) -> dict[str, Any]:
    matches = [
        row for row in trial.get("verified_source_only_rows", []) if row.get("row_id") == row_id
    ]
    if len(matches) != 1:
        raise _error(f"base trial does not contain source row {row_id}")
    return canonical_clone_v1(matches[0])


def _mapping(trial: dict[str, Any], report_norm_id: int) -> dict[str, Any]:
    matches = [
        row
        for row in trial.get("verified_mappings", [])
        if row.get("schema_binding", {}).get("report_norm_id") == report_norm_id
    ]
    if len(matches) != 1:
        raise _error(f"base trial does not contain one mapping {report_norm_id}")
    return canonical_clone_v1(matches[0])


def _axis_values(row: dict[str, Any]) -> dict[str, int]:
    values = row.get("values")
    if type(values) is not list:
        raise _error("source/mapping value axis is absent")
    result: dict[str, int] = {}
    for value in values:
        axis = value.get("axis_role")
        numeric = value.get("normalized_value")
        if type(axis) is not str or type(numeric) is not int or axis in result:
            raise _error("source/mapping value axis drifted")
        result[axis] = numeric
    return result


def _schema_row(
    row_ids: list[str],
    bank: str,
    page: int,
    binding: dict[str, Any],
    values: dict[str, Any],
    mode: str,
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "bank_code": bank,
        "mapping_mode": mode,
        "page_sequence": page,
        "schema_binding": binding,
        "source_evidence": evidence,
        "source_row_ids": row_ids,
        "status": "VERIFIED_BY_CODEX_PROJECT_OWNER_ADJUDICATION",
        "values": values,
    }


def _monthly_values(row: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for axis, source in _axis_values(row).items():
        exact = Fraction(source, 6)
        with localcontext() as context:
            context.prec = 30
            decimal = Decimal(exact.numerator) / Decimal(exact.denominator)
        result[axis] = {
            "derived_decimal_12dp": format(decimal, ".12f").rstrip("0").rstrip("."),
            "derived_exact_rational": {
                "denominator": exact.denominator,
                "numerator": exact.numerator,
            },
            "months_in_source_period": 6,
            "source_per_employee_reporting_period_value": source,
            "unit": "TRIEU_VND_PER_EMPLOYEE_PER_MONTH",
        }
    return result


def _sum_values(rows: list[dict[str, Any]]) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in rows:
        for axis, value in _axis_values(row).items():
            result[axis] = result.get(axis, 0) + value
    return result


def build_live_owner_adjudicated_catchall_average_closure_v1() -> dict[str, Any]:
    """Exact-rebuild the ten project-owner row closures."""
    bases, base_refs = _base_inputs()
    schema, schema_ref = _schema_bindings()

    crpe_vpb = _trial(bases["credit_risk_provision"], "VPB")
    crpe_vib = _trial(bases["credit_risk_provision"], "VIB")
    crpe1 = _source_row(crpe_vpb, "CRPE-001")
    crpe2 = _source_row(crpe_vib, "CRPE-002")

    oact_vpb = _trial(bases["other_activity"], "VPB")
    oact = _source_row(oact_vpb, "OACT-001")
    oact_other = _mapping(oact_vpb, 1239)

    employee_acb = _trial(bases["employee_income"], "ACB")
    employee_salary = _source_row(employee_acb, "EI-001")
    employee_income = _source_row(employee_acb, "EI-002")

    budget_hdb = _trial(bases["state_budget"], "HDB")
    land_rent = _source_row(budget_hdb, "SBO-001")
    other_payable = _mapping(budget_hdb, 1279)

    collateral_vcb = _trial(bases["customer_collateral"], "VCB")
    collateral_vib = _trial(bases["customer_collateral"], "VIB")
    cc1 = _source_row(collateral_vcb, "CC-001")
    cc2 = _source_row(collateral_vib, "CC-002")
    cc3 = _source_row(collateral_vib, "CC-003")
    cc4 = _source_row(collateral_vib, "CC-004")
    vcb_other = _mapping(collateral_vcb, 1288)
    vib_other = _mapping(collateral_vib, 1288)

    rows = [
        _schema_row(
            ["CRPE-001"],
            "VPB",
            66,
            schema[1228],
            _axis_values(crpe1),
            "DIRECT_CATCHALL_MAPPING",
            [crpe1],
        ),
        _schema_row(
            ["CRPE-002"],
            "VIB",
            47,
            schema[1228],
            _axis_values(crpe2),
            "DIRECT_CATCHALL_MAPPING",
            [crpe2],
        ),
        _schema_row(
            ["OACT-001"],
            "VPB",
            64,
            schema[1239],
            _sum_values([oact_other, oact]),
            "AGGREGATE_WITH_EXISTING_CATCHALL_ONCE",
            [oact_other, oact],
        ),
        _schema_row(
            ["EI-001"],
            "ACB",
            26,
            schema[1267],
            _monthly_values(employee_salary),
            "DERIVE_SIX_MONTH_PER_EMPLOYEE_TO_PER_EMPLOYEE_PER_MONTH",
            [employee_salary],
        ),
        _schema_row(
            ["EI-002"],
            "ACB",
            26,
            schema[1268],
            _monthly_values(employee_income),
            "DERIVE_SIX_MONTH_PER_EMPLOYEE_TO_PER_EMPLOYEE_PER_MONTH",
            [employee_income],
        ),
        _schema_row(
            ["SBO-001"],
            "HDB",
            32,
            schema[1279],
            _axis_values(other_payable),
            "AGGREGATE_FIVE_VISIBLE_DASH_ZEROES_WITH_EXISTING_CATCHALL",
            [
                other_payable,
                land_rent,
                {
                    "axis_roles": [
                        "OPENING",
                        "BUSINESS_COMBINATION_INCREASE",
                        "PAYABLE_INCREASE",
                        "PAID_DECREASE",
                        "CLOSING",
                    ],
                    "authenticated_render_sha256": "a877c7ecdd793ae53c23f1e078a8585b778fe3af9579a85dcd4e135d08998551",
                    "normalized_values": [0, 0, 0, 0, 0],
                    "pixel_transcriptions": ["-", "-", "-", "-", "-"],
                },
            ],
        ),
        _schema_row(
            ["CC-001"],
            "VCB",
            47,
            schema[1288],
            _sum_values([vcb_other, cc1]),
            "AGGREGATE_WITH_EXISTING_CATCHALL_ONCE",
            [vcb_other, cc1],
        ),
        _schema_row(
            ["CC-002", "CC-003", "CC-004"],
            "VIB",
            49,
            schema[1288],
            _sum_values([vib_other, cc2, cc3, cc4]),
            "AGGREGATE_WITH_EXISTING_CATCHALL_ONCE",
            [vib_other, cc2, cc3, cc4],
        ),
    ]

    expected_values = [
        {"COMPARATIVE_PERIOD": 29368, "CURRENT_PERIOD": 0},
        {"COMPARATIVE_PERIOD": -244, "CURRENT_PERIOD": 0},
        {"COMPARATIVE_PERIOD": 230643, "CURRENT_PERIOD": 584150},
        {
            "COMPARATIVE_PERIOD": {
                "derived_decimal_12dp": "14.333333333333",
                "derived_exact_rational": {"denominator": 3, "numerator": 43},
                "months_in_source_period": 6,
                "source_per_employee_reporting_period_value": 86,
                "unit": "TRIEU_VND_PER_EMPLOYEE_PER_MONTH",
            },
            "CURRENT_PERIOD": {
                "derived_decimal_12dp": "15",
                "derived_exact_rational": {"denominator": 1, "numerator": 15},
                "months_in_source_period": 6,
                "source_per_employee_reporting_period_value": 90,
                "unit": "TRIEU_VND_PER_EMPLOYEE_PER_MONTH",
            },
        },
        {
            "COMPARATIVE_PERIOD": {
                "derived_decimal_12dp": "41.166666666667",
                "derived_exact_rational": {"denominator": 6, "numerator": 247},
                "months_in_source_period": 6,
                "source_per_employee_reporting_period_value": 247,
                "unit": "TRIEU_VND_PER_EMPLOYEE_PER_MONTH",
            },
            "CURRENT_PERIOD": {
                "derived_decimal_12dp": "40.5",
                "derived_exact_rational": {"denominator": 2, "numerator": 81},
                "months_in_source_period": 6,
                "source_per_employee_reporting_period_value": 243,
                "unit": "TRIEU_VND_PER_EMPLOYEE_PER_MONTH",
            },
        },
        {
            "BUSINESS_COMBINATION_INCREASE": 0,
            "CLOSING": 0,
            "OPENING": 0,
            "PAID_DECREASE": -2500,
            "PAYABLE_INCREASE": 2500,
        },
        {"COMPARATIVE": 687893688, "CURRENT": 688039608},
        {"COMPARATIVE": 153501606, "CURRENT": 204865534},
    ]
    if [row["values"] for row in rows] != expected_values:
        raise _error("owner-adjudicated value derivation drifted")

    equations = [
        {
            "axis_role": "CURRENT_PERIOD",
            "computed_value": 7669094,
            "name": "VPB_PROVISION_COMPONENTS_AFTER_1228_EQUAL_TOTAL",
            "status": "VERIFIED_EXACT",
            "visible_value": 7669094,
        },
        {
            "axis_role": "COMPARATIVE_PERIOD",
            "computed_value": 6677305,
            "name": "VPB_PROVISION_COMPONENTS_AFTER_1228_EQUAL_TOTAL",
            "status": "VERIFIED_EXACT",
            "visible_value": 6677305,
        },
        {
            "axis_role": "CURRENT_PERIOD",
            "computed_value": 2485817,
            "name": "VIB_PROVISION_COMPONENTS_AFTER_1228_EQUAL_TOTAL",
            "status": "VERIFIED_EXACT",
            "visible_value": 2485817,
        },
        {
            "axis_role": "COMPARATIVE_PERIOD",
            "computed_value": 1056969,
            "name": "VIB_PROVISION_COMPONENTS_AFTER_1228_EQUAL_TOTAL",
            "status": "VERIFIED_EXACT",
            "visible_value": 1056969,
        },
        {
            "axis_role": "CURRENT_PERIOD",
            "computed_value": 2364329,
            "name": "VPB_OTHER_INCOME_AFTER_1239_AGGREGATION_EQUAL_PARENT",
            "status": "VERIFIED_EXACT",
            "visible_value": 2364329,
        },
        {
            "axis_role": "COMPARATIVE_PERIOD",
            "computed_value": 2128736,
            "name": "VPB_OTHER_INCOME_AFTER_1239_AGGREGATION_EQUAL_PARENT",
            "status": "VERIFIED_EXACT",
            "visible_value": 2128736,
        },
        {
            "axis_role": "CURRENT",
            "computed_value": 2638095400,
            "name": "VCB_COLLATERAL_AFTER_1288_AGGREGATION_EQUAL_TOTAL",
            "status": "VERIFIED_EXACT",
            "visible_value": 2638095400,
        },
        {
            "axis_role": "COMPARATIVE",
            "computed_value": 2637950498,
            "name": "VCB_COLLATERAL_AFTER_1288_AGGREGATION_EQUAL_TOTAL",
            "status": "VERIFIED_EXACT",
            "visible_value": 2637950498,
        },
        {
            "axis_role": "CURRENT",
            "computed_value": 756496471,
            "name": "VIB_COLLATERAL_AFTER_1288_AGGREGATION_EQUAL_TOTAL",
            "status": "VERIFIED_EXACT",
            "visible_value": 756496471,
        },
        {
            "axis_role": "COMPARATIVE",
            "computed_value": 702878947,
            "name": "VIB_COLLATERAL_AFTER_1288_AGGREGATION_EQUAL_TOTAL",
            "status": "VERIFIED_EXACT",
            "visible_value": 702878947,
        },
    ]

    material = {
        "authority": _AUTHORITY,
        "claim_boundary": CLAIM_BOUNDARY,
        "closed_source_row_ids": [
            "CRPE-001",
            "CRPE-002",
            "OACT-001",
            "EI-001",
            "EI-002",
            "SBO-001",
            "CC-001",
            "CC-002",
            "CC-003",
            "CC-004",
        ],
        "format_version": FORMAT_VERSION,
        "input_refs": {"base_results": base_refs, "schema_graph": schema_ref},
        "metrics": {
            "accounting_equation_verified_count": 10,
            "catchall_aggregate_output_count": 4,
            "closed_open_source_row_count": 10,
            "derived_monthly_mapping_count": 2,
            "direct_catchall_mapping_count": 2,
            "output_mapping_count": 8,
            "source_value_component_count": 23,
        },
        "owner_decision": (
            "Map CRPE-001/002 to 1228; aggregate OACT-001 into 1239; divide ACB "
            "six-month per-employee averages by six for 1267/1268; aggregate HDB "
            "land-rent dashes into 1279; aggregate VCB/VIB collateral rows into 1288."
        ),
        "state": "PROJECT_OWNER_CATCHALL_AND_MONTHLY_AVERAGE_CLOSURE_COMPLETE",
        "verified_accounting_equations": equations,
        "verified_mappings": rows,
    }
    return {
        **material,
        "result_id": "e0100:result:" + canonical_json_sha256_v1(material),
    }


def validate_owner_adjudicated_catchall_average_closure_replay_v1(
    result: Any,
) -> dict[str, Any]:
    if type(result) is not dict:
        raise _error("closure must be one exact dict")
    rebuilt = build_live_owner_adjudicated_catchall_average_closure_v1()
    if not same_typed_json_v1(result, rebuilt):
        raise _error("owner-adjudicated closure does not exact-replay")
    return canonical_clone_v1(rebuilt)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-result", action="store_true")
    parser.add_argument("--validate-result", action="store_true")
    args = parser.parse_args()
    if args.write_result == args.validate_result:
        parser.error("choose exactly one of --write-result or --validate-result")
    if args.write_result:
        payload = build_live_owner_adjudicated_catchall_average_closure_v1()
        destination = PROJECT_ROOT / OUTPUT_PATH
        if destination.exists():
            raise _error(f"refusing to overwrite existing closure: {OUTPUT_PATH}")
        destination.write_bytes(canonical_json_bytes_v1(payload) + b"\n")
        return
    payload = _strict_json(_stable_bytes(OUTPUT_PATH), OUTPUT_PATH.as_posix())
    validate_owner_adjudicated_catchall_average_closure_replay_v1(payload)


if __name__ == "__main__":
    main()
