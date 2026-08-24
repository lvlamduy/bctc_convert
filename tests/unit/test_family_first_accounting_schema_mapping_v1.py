from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation import family_first_accounting_evidence_sweep_v1 as evidence_v1
from bctc_ai.evaluation import family_first_accounting_schema_mapping_v1 as subject
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _family_spec() -> dict[str, object]:
    return {
        "children": [
            {
                "aliases": ["Tiền mặt bằng VND"],
                "presence": "REQUIRED",
                "role": "CASH_VND",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "aliases": ["Tiền mặt bằng ngoại tệ"],
                "presence": "REQUIRED",
                "role": "CASH_FOREIGN",
                "role_kind": "ADDITIVE_CHILD",
            },
        ],
        "family_id": "CASH_PRECIOUS_METALS",
        "format_version": "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V1",
        "hard_negative_aliases": ["Rủi ro tiền tệ"],
        "limits": {
            "max_cluster_span_lines": 30,
            "max_continuation_pages": 1,
            "max_label_line_span": 2,
        },
        "parent": {
            "aliases": ["Tiền, kim loại quý và đá quý"],
            "resolution_mode": "EXPLICIT_ONLY",
            "role": "CASH_PRECIOUS_METALS",
        },
        "structural_reset_aliases": ["Tiền gửi tại Ngân hàng Nhà nước"],
    }


def _evaluation_spec() -> dict[str, object]:
    return {
        "closure_policy": "REQUIRE_EXACT_UNIQUE_VISIBLE_TRAILING_TOTAL",
        "expected_lane_unit_kinds": ["MONEY", "MONEY"],
        "family_id": "CASH_PRECIOUS_METALS",
        "format_version": "ACCOUNTING_FAMILY_EVALUATION_SPEC_V1",
        "period_semantics": "BALANCE_COMPARATIVE",
    }


def _binding_spec() -> dict[str, object]:
    return {
        "family_id": "CASH_PRECIOUS_METALS",
        "family_report_norm_id": 561,
        "format_version": subject.SPEC_FORMAT_VERSION,
        "role_bindings": [
            {"report_norm_id": 562, "role": "CASH_VND"},
            {"report_norm_id": 563, "role": "CASH_FOREIGN"},
        ],
    }


def _schema_payload(
    *,
    foreign_parent: int = 561,
    foreign_period_types: tuple[str, ...] = ("SNAPSHOT", "DURATION"),
    foreign_scope: tuple[str, ...] = ("SEPARATE", "CONSOLIDATED"),
    foreign_signs: tuple[str, ...] = ("POSITIVE", "NEGATIVE", "ZERO"),
) -> bytes:
    nodes = [
        {
            "canonical_name": "Tiền, kim loại quý và đá quý",
            "allowed_period_type": ["SNAPSHOT", "DURATION"],
            "allowed_sign": ["POSITIVE", "NEGATIVE", "ZERO"],
            "children": [562, 563],
            "parent_id": 560,
            "schema_id": 561,
            "scope": ["SEPARATE", "CONSOLIDATED"],
            "statement_type": "TM",
        },
        {
            "canonical_name": "Tiền mặt bằng VNĐ",
            "allowed_period_type": ["SNAPSHOT", "DURATION"],
            "allowed_sign": ["POSITIVE", "NEGATIVE", "ZERO"],
            "children": [],
            "parent_id": 561,
            "schema_id": 562,
            "scope": ["SEPARATE", "CONSOLIDATED"],
            "statement_type": "TM",
        },
        {
            "canonical_name": "Tiền mặt bằng ngoại tệ",
            "allowed_period_type": list(foreign_period_types),
            "allowed_sign": list(foreign_signs),
            "children": [],
            "parent_id": foreign_parent,
            "schema_id": 563,
            "scope": list(foreign_scope),
            "statement_type": "TM",
        },
    ]
    return (
        b"\n".join(
            json.dumps(node, ensure_ascii=False, sort_keys=True).encode("utf-8") for node in nodes
        )
        + b"\n"
    )


def _ref(ordinal: int) -> dict[str, object]:
    return {
        "path": f"opaque/value-{ordinal:04d}.png",
        "sha256": f"{ordinal:064x}",
        "size_bytes": 100 + ordinal,
    }


def _value(
    ordinal: int,
    column: int,
    coefficient: int,
    raw_prediction: str,
    *,
    dash: bool = False,
) -> dict[str, object]:
    return {
        "bbox": [600 + 200 * column, 100 + ordinal * 20, 700 + 200 * column, 122 + ordinal * 20],
        "column_ordinal": column,
        "crop_ref": _ref(ordinal * 10 + column),
        "page_sequence": 1,
        "parsed_token": {
            "classification": "DASH_ZERO" if dash else "SIGNED_NUMBER",
            "coefficient": coefficient,
            "percentage_mark_present": False,
            "scale": 0,
        },
        "raw_prediction": raw_prediction,
        "sample_id": f"sample-{ordinal * 10 + column:09d}",
    }


def _row(role: str, surface: str, ordinal: int, amounts: tuple[int, int]) -> dict[str, object]:
    return {
        "label_match": {"surface": surface},
        "role": role,
        "status": "VISIBLE_VALUE_LANES_BOUND",
        "values": [
            _value(ordinal, 0, amounts[0], str(amounts[0])),
            _value(
                ordinal,
                1,
                amounts[1],
                "-" if amounts[1] == 0 else str(amounts[1]),
                dash=amounts[1] == 0,
            ),
        ],
    }


def _ready_trial() -> dict[str, object]:
    rows = [
        _row("CASH_VND", "Tiền mặt bằng VND", 1, (100, 90)),
        _row("CASH_FOREIGN", "Tiền mặt bằng ngoại tệ", 2, (20, 0)),
    ]
    total = {
        "candidate_ordinal": 0,
        "status": "COMPLETE_VISIBLE_TRAILING_VALUE_ROW",
        "values": [_value(3, 0, 120, "120"), _value(3, 1, 90, "90")],
    }
    return {
        "additive_closure": {
            "exact_total_candidates": [{"candidate_ordinal": 0}],
            "status": "CORROBORATED_EXACT_UNIQUE_TRAILING_TOTAL",
        },
        "column_context": {
            "period_axis": [
                {
                    "column_ordinal": 0,
                    "resolved_period": {"as_of_date": "2025-12-31", "kind": "SNAPSHOT"},
                },
                {
                    "column_ordinal": 1,
                    "resolved_period": {"as_of_date": "2024-12-31", "kind": "SNAPSHOT"},
                },
            ],
            "status": "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY",
            "unit_axis": [
                {
                    "column_ordinal": 0,
                    "currency": "VND",
                    "magnitude_power10": 6,
                    "unit_kind": "MONEY",
                },
                {
                    "column_ordinal": 1,
                    "currency": "VND",
                    "magnitude_power10": 6,
                    "unit_kind": "MONEY",
                },
            ],
        },
        "document_ordinal": 1,
        "evidence_status": "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY",
        "private_provenance": {
            "opaque_filing": "filing-0001",
            "scope": "CONSOLIDATED",
        },
        "row_axis": {"rows": rows, "trailing_value_rows": [total]},
        "source_pdf_ref": {
            "path": "opaque/source-0001.pdf",
            "sha256": "1" * 64,
            "size_bytes": 1000,
        },
        "unresolved_reasons": [],
    }


def _sweep() -> dict[str, object]:
    return {
        "evaluation_spec": {
            "value": {"period_semantics": "BALANCE_COMPARATIVE"},
        },
        "family_id": "CASH_PRECIOUS_METALS",
        "sweep_id": "ffaesv1:sweep:" + "4" * 64,
        "trials": [
            _ready_trial(),
            {
                "document_ordinal": 2,
                "evidence_status": "NOT_OBSERVED_PROPOSAL_ONLY",
                "private_provenance": {"opaque_filing": "filing-0002"},
                "source_pdf_ref": {
                    "path": "opaque/source-0002.pdf",
                    "sha256": "2" * 64,
                    "size_bytes": 1001,
                },
                "unresolved_reasons": [],
            },
            {
                "document_ordinal": 3,
                "evidence_status": "UNRESOLVED_EVIDENCE_GATES",
                "private_provenance": {"opaque_filing": "filing-0003"},
                "source_pdf_ref": {
                    "path": "opaque/source-0003.pdf",
                    "sha256": "3" * 64,
                    "size_bytes": 1002,
                },
                "unresolved_reasons": ["VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE"],
            },
        ],
    }


def _patch_live(monkeypatch):
    state = {"graph": _schema_payload(), "sweep": _sweep()}
    monkeypatch.setattr(subject.archive_v1, "_root", lambda value: Path(value))
    monkeypatch.setattr(
        subject.archive_v1,
        "_root_bytes",
        lambda _root, _path, _label: state["graph"],
    )
    monkeypatch.setattr(
        subject.evidence_v1,
        "build_authenticated_family_first_accounting_evidence_sweep_v1",
        lambda *_args: copy.deepcopy(state["sweep"]),
    )
    return state


def _build() -> dict[str, object]:
    return subject.build_authenticated_family_first_accounting_schema_mapping_v1(
        Path("/repo"), object(), object(), _family_spec(), _evaluation_spec(), _binding_spec()
    )


def _aggregate_family_spec() -> dict[str, object]:
    spec = _family_spec()
    spec["format_version"] = "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V2"
    spec["required_role_combinations"] = [
        ["CASH_VND", "CASH_FOREIGN"],
        ["CENTRAL_BANK_LAOS", "CENTRAL_BANK_CAMBODIA"],
    ]
    for child in spec["children"]:
        child["presence"] = "OPTIONAL"
    spec["children"].extend(
        [
            {
                "aliases": ["Tiền gửi tại Ngân hàng Nhà nước Lào"],
                "presence": "OPTIONAL",
                "role": "CENTRAL_BANK_LAOS",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "aliases": ["Tiền gửi tại Ngân hàng Quốc gia Campuchia"],
                "presence": "OPTIONAL",
                "role": "CENTRAL_BANK_CAMBODIA",
                "role_kind": "ADDITIVE_CHILD",
            },
        ]
    )
    return spec


def _aggregate_binding_spec() -> dict[str, object]:
    return {
        "aggregate_role_bindings": [
            {
                "operation": "SUM_OBSERVED_SOURCE_ROLES",
                "report_norm_id": 564,
                "role": "OTHER_CENTRAL_BANK_DEPOSITS_AGGREGATE",
                "source_roles": ["CENTRAL_BANK_LAOS", "CENTRAL_BANK_CAMBODIA"],
            }
        ],
        "family_id": "CASH_PRECIOUS_METALS",
        "family_report_norm_id": 561,
        "format_version": subject.SPEC_FORMAT_VERSION_V2,
        "role_bindings": [
            {"report_norm_id": 562, "role": "CASH_VND"},
            {"report_norm_id": 563, "role": "CASH_FOREIGN"},
        ],
    }


def _aggregate_schema_payload() -> bytes:
    nodes = [json.loads(line) for line in _schema_payload().decode("utf-8").splitlines()]
    nodes[0]["children"].append(564)
    nodes.append(
        {
            "allowed_period_type": ["SNAPSHOT", "DURATION"],
            "allowed_sign": ["POSITIVE", "NEGATIVE", "ZERO"],
            "canonical_name": "Tiền gửi khác",
            "children": [],
            "parent_id": 561,
            "schema_id": 564,
            "scope": ["SEPARATE", "CONSOLIDATED"],
            "statement_type": "TM",
        }
    )
    return (
        b"\n".join(
            json.dumps(node, ensure_ascii=False, sort_keys=True).encode("utf-8") for node in nodes
        )
        + b"\n"
    )


def _aggregate_ready_trial(*, include_cambodia: bool = True) -> dict[str, object]:
    trial = _ready_trial()
    trial["row_axis"]["rows"].append(
        _row(
            "CENTRAL_BANK_LAOS",
            "Tiền gửi tại Ngân hàng Nhà nước Lào",
            4,
            (10, 5),
        )
    )
    if include_cambodia:
        trial["row_axis"]["rows"].append(
            _row(
                "CENTRAL_BANK_CAMBODIA",
                "Tiền gửi tại Ngân hàng Quốc gia Campuchia",
                5,
                (20, 7),
            )
        )
    return trial


def _build_aggregate(
    monkeypatch: pytest.MonkeyPatch, *, include_cambodia: bool = True
) -> dict[str, object]:
    state = _patch_live(monkeypatch)
    state["graph"] = _aggregate_schema_payload()
    state["sweep"]["trials"][0] = _aggregate_ready_trial(include_cambodia=include_cambodia)
    return subject.build_authenticated_family_first_accounting_schema_mapping_v1(
        Path("/repo"),
        object(),
        object(),
        _aggregate_family_spec(),
        _evaluation_spec(),
        _aggregate_binding_spec(),
    )


def test_live_ready_not_observed_and_unresolved_outcomes(monkeypatch) -> None:
    _patch_live(monkeypatch)

    result = _build()

    assert result["metrics"] == {
        "document_count": 3,
        "not_observed_proposal_count": 1,
        "unresolved_document_count": 1,
        "verified_document_count": 1,
        "verified_mapping_count": 3,
    }
    verified, not_observed, unresolved = result["trials"]
    assert verified["mapping_status"] == "VERIFIED_BY_CODEX"
    assert [item["report_norm_id"] for item in verified["mappings"]] == [562, 563, 561]
    assert verified["mappings"][1]["values"][1]["numeric_value"] == {
        "coefficient": 0,
        "scale": 0,
    }
    assert verified["mappings"][1]["values"][1]["source_zero_kind"] == "VISIBLE_DASH"
    assert verified["mappings"][0]["values"][0]["period"]["as_of_date"] == "2025-12-31"
    assert verified["mappings"][0]["values"][0]["magnitude_power10"] == 6
    assert not_observed["mapping_status"] == "NOT_OBSERVED_PROPOSAL_ONLY"
    assert not_observed["mappings"] == []
    assert unresolved["mapping_status"] == "UNRESOLVED"
    assert unresolved["unresolved_reasons"] == ["VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE"]
    assert result["authority"]["persisted_result_self_authenticating"] is False


@pytest.mark.parametrize(
    ("include_cambodia", "expected", "component_roles"),
    [
        (True, (30, 12), ["CENTRAL_BANK_LAOS", "CENTRAL_BANK_CAMBODIA"]),
        (False, (10, 5), ["CENTRAL_BANK_LAOS"]),
    ],
)
def test_v2_aggregates_only_observed_source_roles_with_exact_component_evidence(
    monkeypatch, include_cambodia: bool, expected: tuple[int, int], component_roles: list[str]
) -> None:
    result = _build_aggregate(monkeypatch, include_cambodia=include_cambodia)

    trial = result["trials"][0]
    assert trial["mapping_status"] == "VERIFIED_BY_CODEX"
    aggregate = next(item for item in trial["mappings"] if item["report_norm_id"] == 564)
    assert aggregate["mapping_kind"] == "SUM_OBSERVED_SOURCE_ROLES_TO_LIVE_SCHEMA_CHILD"
    assert aggregate["role"] == "OTHER_CENTRAL_BANK_DEPOSITS_AGGREGATE"
    assert [item["role"] for item in aggregate["source_components"]] == component_roles
    assert tuple(item["numeric_value"]["coefficient"] for item in aggregate["values"]) == expected
    assert all(
        len(item["source_component_sample_ids"]) == len(component_roles)
        for item in aggregate["values"]
    )


def test_v2_aggregate_uses_exact_decimal_scale_arithmetic(monkeypatch) -> None:
    state = _patch_live(monkeypatch)
    state["graph"] = _aggregate_schema_payload()
    trial = _aggregate_ready_trial()
    laos, cambodia = trial["row_axis"]["rows"][-2:]
    laos["values"][0]["parsed_token"].update({"coefficient": 15, "scale": 1})
    cambodia["values"][0]["parsed_token"].update({"coefficient": 225, "scale": 2})
    state["sweep"]["trials"][0] = trial

    result = subject.build_authenticated_family_first_accounting_schema_mapping_v1(
        Path("/repo"),
        object(),
        object(),
        _aggregate_family_spec(),
        _evaluation_spec(),
        _aggregate_binding_spec(),
    )

    aggregate = next(
        item for item in result["trials"][0]["mappings"] if item["report_norm_id"] == 564
    )
    assert aggregate["values"][0]["numeric_value"] == {"coefficient": 375, "scale": 2}


def test_exact_live_replay_rejects_coordinated_persisted_numeric_change(monkeypatch) -> None:
    _patch_live(monkeypatch)
    result = _build()
    forged = copy.deepcopy(result)
    mapping = forged["trials"][0]["mappings"][0]
    mapping["values"][0]["numeric_value"]["coefficient"] = 999
    material = copy.deepcopy(forged)
    material.pop("mapping_id")
    forged["mapping_id"] = "ffasmv1:mapping:" + canonical_json_sha256_v1(material)

    with pytest.raises(subject.FamilyFirstAccountingSchemaMappingV1Error, match="replay exactly"):
        subject.validate_authenticated_family_first_accounting_schema_mapping_replay_v1(
            forged,
            Path("/repo"),
            object(),
            object(),
            _family_spec(),
            _evaluation_spec(),
            _binding_spec(),
        )


def test_live_schema_graph_drift_rejects_direct_child_binding(monkeypatch) -> None:
    state = _patch_live(monkeypatch)
    state["graph"] = _schema_payload(foreign_parent=999)

    with pytest.raises(
        subject.FamilyFirstAccountingSchemaMappingV1Error, match="direct live child"
    ):
        _build()


def test_live_schema_scope_incompatibility_remains_unresolved(monkeypatch) -> None:
    state = _patch_live(monkeypatch)
    state["graph"] = _schema_payload(foreign_scope=("SEPARATE",))

    result = _build()

    assert result["trials"][0]["mapping_status"] == "UNRESOLVED"
    assert result["trials"][0]["mappings"] == []
    assert result["trials"][0]["unresolved_reasons"] == [
        "SCHEMA_SCOPE_NOT_ALLOWED:563:CONSOLIDATED"
    ]


@pytest.mark.parametrize(
    ("graph", "reason"),
    [
        (
            _schema_payload(foreign_period_types=("DURATION",)),
            "SCHEMA_PERIOD_TYPE_NOT_ALLOWED:563:SNAPSHOT",
        ),
        (
            _schema_payload(foreign_signs=("POSITIVE",)),
            "SCHEMA_SIGN_NOT_ALLOWED:563:ZERO",
        ),
    ],
)
def test_live_schema_period_and_sign_incompatibility_remain_unresolved(
    monkeypatch, graph: bytes, reason: str
) -> None:
    state = _patch_live(monkeypatch)
    state["graph"] = graph

    result = _build()

    assert result["trials"][0]["mapping_status"] == "UNRESOLVED"
    assert result["trials"][0]["unresolved_reasons"] == [reason]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.__setitem__("family_report_norm_id", True),
        lambda value: value["role_bindings"][0].__setitem__("report_norm_id", 563),
        lambda value: value["role_bindings"].reverse(),
        lambda value: value["role_bindings"][0].__setitem__("role", "BANK_SPECIFIC"),
    ],
)
def test_schema_binding_spec_type_identity_and_role_axis_fail_closed(monkeypatch, mutation) -> None:
    _patch_live(monkeypatch)
    spec = _binding_spec()
    mutation(spec)

    with pytest.raises(subject.FamilyFirstAccountingSchemaMappingV1Error):
        subject.build_authenticated_family_first_accounting_schema_mapping_v1(
            Path("/repo"), object(), object(), _family_spec(), _evaluation_spec(), spec
        )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["aggregate_role_bindings"][0].__setitem__("operation", []),
        lambda value: value["aggregate_role_bindings"][0].__setitem__(
            "operation", "CALLER_DEFINED_SUM"
        ),
        lambda value: value["aggregate_role_bindings"][0].__setitem__(
            "source_roles", ["CASH_FOREIGN", "CENTRAL_BANK_CAMBODIA"]
        ),
        lambda value: value["aggregate_role_bindings"][0].__setitem__(
            "source_roles", ["CENTRAL_BANK_CAMBODIA", "CENTRAL_BANK_LAOS"]
        ),
        lambda value: value["aggregate_role_bindings"][0].__setitem__(
            "source_roles", ["CENTRAL_BANK_LAOS", "BANK_SPECIFIC"]
        ),
        lambda value: value["aggregate_role_bindings"][0].__setitem__("report_norm_id", 563),
        lambda value: value["aggregate_role_bindings"][0].__setitem__("role", "CENTRAL_BANK_LAOS"),
        lambda value: value["role_bindings"].pop(),
    ],
)
def test_v2_schema_binding_rejects_overlap_order_unknown_and_caller_operation(
    monkeypatch, mutation
) -> None:
    _patch_live(monkeypatch)
    spec = _aggregate_binding_spec()
    mutation(spec)

    with pytest.raises(subject.FamilyFirstAccountingSchemaMappingV1Error):
        subject.build_authenticated_family_first_accounting_schema_mapping_v1(
            Path("/repo"),
            object(),
            object(),
            _aggregate_family_spec(),
            _evaluation_spec(),
            spec,
        )


def test_mapper_contains_no_bank_page_year_or_filing_specific_route() -> None:
    payload = Path(subject.__file__).read_text(encoding="utf-8")
    for token in ("ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB", "2025", "2026"):
        assert token not in payload


def test_tracked_central_bank_deposit_specs_bind_generic_variants_to_live_schema() -> None:
    config_root = _PROJECT_ROOT / "config/families"
    family = json.loads(
        (config_root / "tm-central-bank-deposits-topology-v2.json").read_text(encoding="utf-8")
    )
    evaluation = json.loads(
        (config_root / "tm-central-bank-deposits-evaluation-v1.json").read_text(encoding="utf-8")
    )
    binding = json.loads(
        (config_root / "tm-central-bank-deposits-schema-binding-v2.json").read_text(
            encoding="utf-8"
        )
    )

    compiled = topology_v1._spec(family)
    evidence_v1._evaluation_spec(evaluation, compiled)
    parsed_binding = subject._schema_spec(binding, family)
    nodes, _ = subject._schema_graph(_PROJECT_ROOT)
    parent, direct, aggregates = subject._bind_schema(nodes, parsed_binding)

    assert compiled["required_role_combinations"] == [
        ["DEPOSIT_VND", "DEPOSIT_FOREIGN_CURRENCY"],
        ["CENTRAL_BANK_VIETNAM_PARENT", "CENTRAL_BANK_LAOS"],
        ["CENTRAL_BANK_VIETNAM_PARENT", "CENTRAL_BANK_CAMBODIA"],
    ]
    assert parent["schema_id"] == 569
    assert {role: node["schema_id"] for role, node in direct.items()} == {
        "BLOCKED_DEPOSIT": 573,
        "CENTRAL_BANK_VIETNAM_PARENT": 570,
        "DEPOSIT_FOREIGN_CURRENCY": 572,
        "DEPOSIT_VND": 571,
    }
    assert [(item["role"], node["schema_id"]) for item, node in aggregates] == [
        ("OTHER_CENTRAL_BANK_DEPOSITS_AGGREGATE", 574)
    ]
    serialized = json.dumps(
        {"binding": binding, "evaluation": evaluation, "family": family},
        ensure_ascii=False,
    )
    for token in ("ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB", "2025", "2026"):
        assert token not in serialized


def test_hierarchical_trial_maps_derived_family_and_visible_descendant_roles() -> None:
    trial = _ready_trial()
    cash_vnd, cash_foreign = trial["row_axis"]["rows"]

    def visible_record(row):
        return {
            "component_roles": [],
            "resolution_kind": "VISIBLE_SOURCE_ROLE",
            "role": row["role"],
            "source": {"kind": "ROLE_ROW", "record": copy.deepcopy(row)},
            "values": [],
        }

    trial["additive_closure"] = {
        "family_id": "CASH_PRECIOUS_METALS",
        "resolved_roles": [
            visible_record(cash_vnd),
            visible_record(cash_foreign),
            {
                "component_roles": ["CASH_VND", "CASH_FOREIGN"],
                "resolution_kind": "DERIVED_EXACT_COMPONENT_SUM",
                "role": "CASH_PRECIOUS_METALS",
                "source": None,
                "values": [
                    {
                        "column_ordinal": 0,
                        "number": {
                            "coefficient": 120,
                            "percentage_mark_present": False,
                            "scale": 0,
                        },
                        "source_sample_ids": [
                            cash_vnd["values"][0]["sample_id"],
                            cash_foreign["values"][0]["sample_id"],
                        ],
                    },
                    {
                        "column_ordinal": 1,
                        "number": {
                            "coefficient": 90,
                            "percentage_mark_present": False,
                            "scale": 0,
                        },
                        "source_sample_ids": [
                            cash_vnd["values"][1]["sample_id"],
                            cash_foreign["values"][1]["sample_id"],
                        ],
                    },
                ],
            },
        ],
        "status": "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO",
    }
    nodes = {
        node["schema_id"]: node
        for node in map(json.loads, _schema_payload().decode("utf-8").splitlines())
    }
    schema_spec = {
        "family_id": "CASH_PRECIOUS_METALS",
        "family_report_norm_id": 561,
        "format_version": subject.SPEC_FORMAT_VERSION_V3,
        "ignored_roles": [],
        "role_bindings": [
            {"report_norm_id": 562, "role": "CASH_VND"},
            {"report_norm_id": 563, "role": "CASH_FOREIGN"},
        ],
    }

    result = subject._trial(
        trial,
        nodes[561],
        {"CASH_VND": nodes[562], "CASH_FOREIGN": nodes[563]},
        [],
        schema_period_type="SNAPSHOT",
        schema_binding_spec=schema_spec,
    )

    assert result["mapping_status"] == "VERIFIED_BY_CODEX"
    assert [mapping["report_norm_id"] for mapping in result["mappings"]] == [561, 562, 563]
    family = result["mappings"][0]
    assert family["mapping_kind"] == "HIERARCHICAL_DERIVED_EXACT_COMPONENT_SUM"
    assert family["values"][0]["source_component_sample_ids"] == [
        cash_vnd["values"][0]["sample_id"],
        cash_foreign["values"][0]["sample_id"],
    ]


def test_v4_hierarchical_binding_maps_complete_leaf_without_inventing_family_root() -> None:
    trial = _ready_trial()
    cash_vnd = trial["row_axis"]["rows"][0]
    trial["additive_closure"] = {
        "family_id": "CASH_PRECIOUS_METALS",
        "resolved_roles": [
            {
                "component_roles": [],
                "resolution_kind": "VISIBLE_SOURCE_ROLE",
                "role": "CASH_VND",
                "source": {"kind": "ROLE_ROW", "record": copy.deepcopy(cash_vnd)},
                "values": [],
            }
        ],
        "status": "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO",
    }
    nodes = {
        node["schema_id"]: node
        for node in map(json.loads, _schema_payload().decode("utf-8").splitlines())
    }
    schema_spec = {
        "family_id": "CASH_PRECIOUS_METALS",
        "family_report_norm_id": 561,
        "family_root_mapping_policy": "MAP_WHEN_HIERARCHICALLY_RESOLVED",
        "format_version": subject.SPEC_FORMAT_VERSION_V4,
        "ignored_roles": [],
        "role_bindings": [
            {"report_norm_id": 562, "role": "CASH_VND"},
            {"report_norm_id": 563, "role": "CASH_FOREIGN"},
        ],
    }

    result = subject._trial(
        trial,
        nodes[561],
        {"CASH_VND": nodes[562], "CASH_FOREIGN": nodes[563]},
        [],
        schema_period_type="SNAPSHOT",
        schema_binding_spec=schema_spec,
    )

    assert result["mapping_status"] == "VERIFIED_BY_CODEX"
    assert [mapping["report_norm_id"] for mapping in result["mappings"]] == [562]


def test_tracked_interbank_specs_bind_recursive_roles_to_live_schema_descendants() -> None:
    config_root = _PROJECT_ROOT / "config/families"
    family = json.loads(
        (config_root / "tm-interbank-deposits-loans-topology-v3.json").read_text(encoding="utf-8")
    )
    evaluation = json.loads(
        (config_root / "tm-interbank-deposits-loans-evaluation-v3.json").read_text(encoding="utf-8")
    )
    binding = json.loads(
        (config_root / "tm-interbank-deposits-loans-schema-binding-v3.json").read_text(
            encoding="utf-8"
        )
    )

    compiled = topology_v1._spec(family)
    evidence_v1._evaluation_spec(evaluation, compiled, raw_family_spec=family)
    parsed_binding = subject._schema_spec(binding, family)
    nodes, _ = subject._schema_graph(_PROJECT_ROOT)
    parent, direct, aggregates = subject._bind_schema(nodes, parsed_binding)

    assert parent["schema_id"] == 575
    assert direct["INTERBANK_DEPOSIT_GROUP"]["schema_id"] == 576
    assert direct["DEMAND_DEPOSIT_VND"]["schema_id"] == 578
    assert direct["INTERBANK_LOAN_FOREIGN_CURRENCY"]["schema_id"] == 588
    assert direct["TOTAL_INTERBANK_PROVISION"]["schema_id"] == 5718
    assert aggregates == []
    assert binding["ignored_roles"] == ["EXPLICIT_FAMILY_TOTAL"]


def test_tracked_interbank_v4_binds_the_full_reviewed_role_to_rnid_matrix() -> None:
    config_root = _PROJECT_ROOT / "config/families"
    family = json.loads(
        (config_root / "tm-interbank-deposits-loans-topology-v4.json").read_text(encoding="utf-8")
    )
    evaluation = json.loads(
        (config_root / "tm-interbank-deposits-loans-evaluation-v4.json").read_text(encoding="utf-8")
    )
    binding = json.loads(
        (config_root / "tm-interbank-deposits-loans-schema-binding-v4.json").read_text(
            encoding="utf-8"
        )
    )

    compiled = topology_v1._spec(family)
    evidence_v1._evaluation_spec(evaluation, compiled, raw_family_spec=family)
    parsed_binding = subject._schema_spec(binding, family)
    nodes, _ = subject._schema_graph(_PROJECT_ROOT)
    parent, direct, aggregates = subject._bind_schema(nodes, parsed_binding)

    assert parent["schema_id"] == 575
    assert {role: node["schema_id"] for role, node in direct.items()} == {
        "INTERBANK_DEPOSIT_GROUP": 576,
        "DEMAND_DEPOSIT_GROUP": 577,
        "DEMAND_DEPOSIT_VND": 578,
        "DEMAND_DEPOSIT_FOREIGN_CURRENCY": 579,
        "TERM_DEPOSIT_GROUP": 580,
        "TERM_DEPOSIT_VND": 581,
        "TERM_DEPOSIT_FOREIGN_CURRENCY": 582,
        "INTERBANK_DEPOSIT_PROVISION": 583,
        "INTERBANK_DEPOSIT_OTHER": 584,
        "INTERBANK_LOAN_GROUP": 585,
        "INTERBANK_LOAN_VND": 586,
        "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND": 587,
        "INTERBANK_LOAN_FOREIGN_CURRENCY": 588,
        "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_FOREIGN_CURRENCY": 589,
        "INTERBANK_LOAN_PROVISION": 590,
        "INTERBANK_LOAN_OTHER": 591,
        "TOTAL_INTERBANK_PROVISION": 5718,
    }
    expected_parent_by_role = {
        "INTERBANK_DEPOSIT_GROUP": 575,
        "DEMAND_DEPOSIT_GROUP": 576,
        "DEMAND_DEPOSIT_VND": 576,
        "DEMAND_DEPOSIT_FOREIGN_CURRENCY": 576,
        "TERM_DEPOSIT_GROUP": 576,
        "TERM_DEPOSIT_VND": 576,
        "TERM_DEPOSIT_FOREIGN_CURRENCY": 576,
        "INTERBANK_DEPOSIT_PROVISION": 576,
        "INTERBANK_DEPOSIT_OTHER": 576,
        "INTERBANK_LOAN_GROUP": 575,
        "INTERBANK_LOAN_VND": 585,
        "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND": 585,
        "INTERBANK_LOAN_FOREIGN_CURRENCY": 585,
        "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_FOREIGN_CURRENCY": 585,
        "INTERBANK_LOAN_PROVISION": 585,
        "INTERBANK_LOAN_OTHER": 585,
        "TOTAL_INTERBANK_PROVISION": 575,
    }
    binding_by_role = {item["role"]: item for item in parsed_binding["role_bindings"]}
    assert {
        role: item["parent_report_norm_id"] for role, item in binding_by_role.items()
    } == expected_parent_by_role
    assert {role: node["parent_id"] for role, node in direct.items()} == expected_parent_by_role
    assert {
        role: (
            item["source_subscope_role"],
            item["preceding_schema_sibling_id"],
        )
        for role, item in binding_by_role.items()
        if "source_subscope_role" in item
    } == {
        "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND": ("INTERBANK_LOAN_VND", 586),
        "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_FOREIGN_CURRENCY": (
            "INTERBANK_LOAN_FOREIGN_CURRENCY",
            588,
        ),
    }
    assert binding["ignored_roles"] == [
        "DEMAND_DEPOSIT_GOLD_AND_FOREIGN_CURRENCY",
        "TERM_DEPOSIT_GOLD_AND_FOREIGN_CURRENCY",
        "INTERBANK_LOAN_GOLD_AND_FOREIGN_CURRENCY",
        "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS",
        "INTERBANK_PROVISION_AMBIGUOUS",
        "EXPLICIT_FAMILY_TOTAL",
    ]
    assert aggregates == []

    attacked_without_parents = copy.deepcopy(binding)
    for item in attacked_without_parents["role_bindings"]:
        item.pop("parent_report_norm_id")
        item.pop("source_subscope_role", None)
        item.pop("preceding_schema_sibling_id", None)
    with pytest.raises(
        subject.FamilyFirstAccountingSchemaMappingV1Error,
        match="schema role binding",
    ):
        subject._schema_spec(attacked_without_parents, family)

    attacked_parent = copy.deepcopy(parsed_binding)
    next(
        item
        for item in attacked_parent["role_bindings"]
        if item["role"] == "INTERBANK_DEPOSIT_PROVISION"
    )["parent_report_norm_id"] = 585
    with pytest.raises(
        subject.FamilyFirstAccountingSchemaMappingV1Error,
        match="role ReportNormId",
    ):
        subject._bind_schema(nodes, attacked_parent)

    attacked_subscope = copy.deepcopy(parsed_binding)
    next(
        item
        for item in attacked_subscope["role_bindings"]
        if item["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND"
    )["preceding_schema_sibling_id"] = 588
    with pytest.raises(
        subject.FamilyFirstAccountingSchemaMappingV1Error,
        match="exact preceding live schema sibling",
    ):
        subject._bind_schema(nodes, attacked_subscope)


def test_tracked_trading_securities_specs_partition_variants_without_bank_routes() -> None:
    config_root = _PROJECT_ROOT / "config/families"
    family = json.loads(
        (config_root / "tm-trading-securities-topology-v1.json").read_text(encoding="utf-8")
    )
    evaluation = json.loads(
        (config_root / "tm-trading-securities-evaluation-v1.json").read_text(encoding="utf-8")
    )
    binding = json.loads(
        (config_root / "tm-trading-securities-schema-binding-v1.json").read_text(encoding="utf-8")
    )

    compiled = topology_v1._spec(family)
    evidence_v1._evaluation_spec(evaluation, compiled, raw_family_spec=family)
    parsed_binding = subject._schema_spec(binding, family)
    nodes, _ = subject._schema_graph(_PROJECT_ROOT)
    parent, direct, aggregates = subject._bind_schema(nodes, parsed_binding)

    assert parent["schema_id"] == 592
    assert direct["DEBT_GOVERNMENT"]["schema_id"] == 595
    assert direct["DEBT_LISTED"]["schema_id"] == 618
    assert direct["EQUITY_UNLISTED"]["schema_id"] == 622
    assert direct["OTHER_UNLISTED"]["schema_id"] == 625
    assert aggregates == []
    assert binding["ignored_roles"] == [
        "DEBT_SECURITIES_GROUP",
        "EQUITY_SECURITIES_GROUP",
        "OTHER_TRADING_SECURITIES_GROUP",
        "EXPLICIT_GROSS_TOTAL",
        "TRADING_SECURITIES_PROVISION_GROUP",
        "PROVISION_PRICE_DECREASE",
        "PROVISION_GENERAL",
        "PROVISION_SPECIFIC",
        "EXPLICIT_NET_TOTAL",
    ]
    serialized = json.dumps(
        {"binding": binding, "evaluation": evaluation, "family": family},
        ensure_ascii=False,
    )
    for token in ("ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB", "2025", "2026"):
        assert token not in serialized
