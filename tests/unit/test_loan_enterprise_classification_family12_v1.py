from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from test_gemini_financial_page_store_v1 import _ingest

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    INDEXED_QUERY_EVIDENCE_FORMAT_VERSION,
    READY,
    UNRESOLVED,
    _validate_indexed_query_evidence_v1,
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
)
from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import (
    _matcher_match_kind,
    evaluate_gemini_json_hierarchical_family_table_v1,
)
from bctc_ai.evaluation.gemini_json_region_repair_queue_v1 import (
    build_family_region_repair_plans_v1,
)
from bctc_ai.evaluation.gemini_json_region_repair_v1 import (
    merge_structural_context_repair_v1,
    structural_context_repair_targets_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    validate_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (
    initialize_gemini_financial_page_store_v1,
    query_selected_hierarchical_title_axis_family_regions_v1,
    validate_selected_hierarchical_title_axis_query_evidence_v1,
)
from scripts.experiments.run_gemini_json_family_region_repair_worker_v1 import (
    _evaluate_indexed_query_disposition_repair_v1,
)

ROOT = Path(__file__).resolve().parents[2]


def _specs() -> tuple[dict, dict, dict]:
    prefix = ROOT / "config/families/tm-loan-enterprise-classification"
    return tuple(
        json.loads(Path(f"{prefix}-{kind}-v1.json").read_text(encoding="utf-8"))
        for kind in ("topology", "evaluation", "schema-binding")
    )


def _compiled() -> dict:
    return compile_gemini_json_flat_family_specs_v1(*_specs())


def test_unresolved_near_source_policy_is_strictly_config_gated() -> None:
    topology, evaluation, schema = _specs()
    evaluation["title_axis_projection_policy"]["unresolved_near_source_policy"] = (
        "ACCEPT_ANY_PARTIAL_ALIAS"
    )
    with pytest.raises(
        ValueError, match="hierarchical title-axis projection policy is invalid"
    ):
        compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)


def _row(label: str | None, values: list[str], *, kind: str = "ITEM", path=None) -> dict:
    return {
        "hierarchy_path_exact": path if path is not None else [label],
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _page(rows: list[dict]) -> dict:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [
                    {
                        "columns": [
                            {"header_path_exact": ["31.12.2025"], "value_kind": "MONEY"},
                            {"header_path_exact": ["31.12.2024"], "value_kind": "MONEY"},
                        ],
                        "continuation": "NONE",
                        "rows": rows,
                        "title_exact": "Phân tích theo loại hình doanh nghiệp",
                        "unit_exact": "Triệu đồng",
                    }
                ],
                "title_exact": "CHO VAY KHÁCH HÀNG",
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _evaluate(page: dict) -> dict:
    return evaluate_gemini_json_hierarchical_family_table_v1(
        page_json=page,
        page_json_version_id="gfpstorev1:json:" + "1" * 64,
        physical_page=7,
        section_id="s1",
        table_id="t1",
        compiled_specs=_compiled(),
    )


def _evaluate_indexed_region(database: Path, page: dict, identity: dict) -> dict:
    queried = _query(database, [identity["page_json_version_id"]])
    evidence = _evidence(queried)
    assert len(evidence["accepted_regions"]) == 1
    region = evidence["accepted_regions"][0]
    return evaluate_gemini_json_hierarchical_family_table_v1(
        page_json=page,
        page_json_version_id=identity["page_json_version_id"],
        physical_page=region["physical_page"],
        section_id=region["section_id"],
        table_id=region["table_id"],
        compiled_specs=_compiled(),
        external_context_receipt=region["structural_context_receipt"],
        external_context_pages=[
            {
                "document_id": region["document_id"],
                "page_json": page,
                "page_json_version_id": identity["page_json_version_id"],
                "physical_page": region["physical_page"],
                "source_logical_name": region["source_logical_name"],
                "source_sha256": region["source_sha256"],
            }
        ],
        external_document_id=region["document_id"],
        external_source_logical_name=region["source_logical_name"],
        external_source_sha256=region["source_sha256"],
        title_axis_query_receipt=evidence["query_receipt"],
    )


def _query(path: Path, selected_ids: list[str]) -> dict:
    compiled = _compiled()
    policy = compiled["title_axis_projection_policy"]
    branch_role = policy["structural_branch_role"]
    return query_selected_hierarchical_title_axis_family_regions_v1(
        path,
        selected_page_json_version_ids=selected_ids,
        query_aliases_by_role={
            role: compiled["query_presence_aliases_by_role"][role]
            for role in policy["required_child_roles"]
        },
        required_child_roles=policy["required_child_roles"],
        minimum_distinct_child_roles=policy["minimum_distinct_child_roles"],
        structural_branch_role=branch_role,
        structural_branch_aliases=compiled["query_presence_aliases_by_role"][branch_role],
        structural_branch_fallback_group_aliases=[
            alias
            for role in policy.get("structural_branch_fallback_group_roles", [])
            for alias in compiled["query_presence_aliases_by_role"][role]
        ],
        unresolved_near_source_policy=policy.get(
            "unresolved_near_source_policy", "ANY_UNVETOED_STRUCTURAL_AXIS"
        ),
        structural_surface_kinds=policy["structural_surface_kinds"],
        explicit_parent_role=compiled["topology"]["parent"]["role"],
        explicit_parent_aliases=compiled["query_parent_aliases"],
        hard_negative_aliases=compiled["topology"]["hard_negative_aliases"],
        owner_reset_aliases=policy["owner_reset_aliases"],
        adjacent_page_radius=policy["owner_page_radius"],
        query_group_receipt=compiled["query_group_compilation_receipt"],
    )


def _evidence(query: dict) -> dict:
    receipt = canonical_clone_v1(query["query_receipt"])
    ordinal_axis = [
        {
            "document_ordinal": 1,
            "source_sha256": region["source_sha256"],
            **{
                key: region[key]
                for key in (
                    "physical_page",
                    "page_json_version_id",
                    "section_id",
                    "table_id",
                )
            },
        }
        for region in query["regions"]
    ]
    receipt["exact_region_ordinal_source_axis_sha256"] = canonical_json_sha256_v1(ordinal_axis)
    receipt_sha256 = canonical_json_sha256_v1(receipt)
    return {
        "accepted_regions": [
            {
                **canonical_clone_v1(region),
                "document_ordinal": 1,
                "structural_context_receipt": {
                    **canonical_clone_v1(region["structural_context_receipt"]),
                    "title_axis_query_receipt_sha256": receipt_sha256,
                },
            }
            for region in query["regions"]
        ],
        "candidate_dispositions": canonical_clone_v1(query["candidate_dispositions"]),
        "format_version": INDEXED_QUERY_EVIDENCE_FORMAT_VERSION,
        "query_receipt": receipt,
    }


def _unresolved_sweep(query: dict) -> dict:
    topology, evaluation, schema = _specs()
    evidence = _evidence(query)
    disposition = query["candidate_dispositions"][0]
    trial = {
        "candidate_count": 0,
        "candidates": [],
        "document_ordinal": 1,
        "mappings": [],
        "reasons": [disposition["disposition"]],
        "selected_candidate_id": None,
        "source_logical_name": disposition["source_logical_name"],
        "source_sha256": disposition["source_sha256"],
        "status": UNRESOLVED,
    }
    return build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "5" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=[trial],
        indexed_query_evidence=evidence,
    )


def _deferred_rows(carrier: list[str], *, leading: bool) -> list[dict]:
    parent = "Cho vay khách hàng"
    branch = "Phân tích theo loại hình doanh nghiệp"
    leaf_values = (
        ("Doanh nghiệp nhà nước", ["10", "9"]),
        ("Công ty trách nhiệm hữu hạn khác", ["20", "18"]),
        ("Công ty cổ phần khác", ["30", "27"]),
        ("Doanh nghiệp tư nhân", ["40", "36"]),
        ("Hợp tác xã và liên hiệp hợp tác xã", ["50", "45"]),
        ("Doanh nghiệp có vốn đầu tư nước ngoài", ["60", "54"]),
        ("Hộ kinh doanh, cá nhân", ["70", "63"]),
        ("Thành phần kinh tế khác", ["80", "72"]),
    )
    leaves = [
        _row(
            label,
            values,
            path=[parent, label] if leading else [parent, branch, label],
        )
        for label, values in leaf_values
    ]
    peer = "Nghiệp vụ phát hành thư tín dụng trả chậm phát sinh trước ngày 01 tháng 7 năm 2024"
    fenced = [
        _row(peer, ["11", "7"], kind="SUBTOTAL", path=[peer]),
        _row("Công ty cổ phần khác", ["6", "4"], path=[peer, "Công ty cổ phần khác"]),
        _row("Công ty TNHH khác", ["5", "3"], path=[peer, "Công ty TNHH khác"]),
        _row(
            None, [str(int(carrier[0]) + 11), str(int(carrier[1]) + 7)], kind="TOTAL", path=[None]
        ),
    ]
    carrier_row = _row(
        parent if leading else None,
        carrier,
        kind="GROUP" if leading else "SUBTOTAL",
        path=[parent] if leading else [None],
    )
    return [carrier_row, *leaves, *fenced] if leading else [*leaves, carrier_row, *fenced]


def test_v8_matcher_equivalences_are_secondary_and_legacy_default_is_exact_only() -> None:
    matcher = {
        "aliases": ["Công ty TNHH MTV vốn nhà nước 100%"],
        "match_mode": "EXACT_NORMALIZED",
        "normalize_single_member_abbreviations": True,
    }
    assert _matcher_match_kind("Công ty TNHH MTV vốn nhà nước 100%", matcher) == (
        "EXACT_NORMALIZED"
    )
    assert _matcher_match_kind("Công ty TNHH 1TV vốn nhà nước 100%", matcher) is None
    assert (
        _matcher_match_kind(
            "Công ty TNHH 1TV vốn nhà nước 100%",
            matcher,
            enable_declared_equivalences=True,
        )
        == "EXACT_NORMALIZED_SINGLE_MEMBER_ABBREVIATION_EQUIVALENCE"
    )


def test_flat_unqualified_legal_forms_redirect_to_terminal_residual_roles_once() -> None:
    page = _page(
        [
            _row("Doanh nghiệp nhà nước", ["10", "9"]),
            _row("Công ty trách nhiệm hữu hạn", ["20", "18"]),
            _row("Công ty cổ phần", ["30", "27"]),
            _row(None, ["60", "54"], kind="TOTAL", path=[None]),
        ]
    )
    result = _evaluate(page)
    assert result["status"] == READY
    by_row = {mapping["row_id"]: mapping["report_norm_id"] for mapping in result["mappings"]}
    assert by_row["r2"] == 771
    assert by_row["r3"] == 773
    assert 768 not in by_row.values()
    assert len(by_row) == len(result["mappings"])


def test_visible_root_allows_only_one_coefficient_of_source_rounding() -> None:
    page = _page(
        [
            _row("Doanh nghiệp nhà nước", ["0", "0"]),
            _row("Công ty trách nhiệm hữu hạn", ["20", "18"]),
            _row("Công ty cổ phần", ["30", "27"]),
            _row("Cá nhân và khách hàng khác", ["11", "9"]),
            _row(None, ["60", "54"], kind="TOTAL", path=[None]),
        ]
    )

    accepted = _evaluate(page)

    assert accepted["status"] == READY
    root = next(
        equation
        for equation in accepted["closure_receipt"]["equations"]
        if equation["result_role"] == "LOAN_ENTERPRISE_FAMILY12"
    )
    assert root["source_rounding_residual_coefficients"] == [-1, 0]

    beyond_bound = deepcopy(page)
    beyond_bound["sections"][0]["tables"][0]["rows"][-1]["values_exact"][0] = "59"
    assert _evaluate(beyond_bound)["status"] == UNRESOLVED


def test_layout_continuation_marker_in_a_money_cell_is_an_exact_dash_zero() -> None:
    page = _page(
        [
            _row(
                "Công ty trách nhiệm hữu hạn một thành viên do Nhà nước sở hữu 100% vốn điều lệ",
                ["- tiep theo -", "-"],
            ),
            _row("Công ty TNHH khác", ["20", "18"]),
            _row("Công ty cổ phần khác", ["30", "27"]),
            _row(None, ["50", "45"], kind="TOTAL", path=[None]),
        ]
    )

    result = _evaluate(page)

    assert result["status"] == READY
    state_llc = next(mapping for mapping in result["mappings"] if mapping["report_norm_id"] == 769)
    assert state_llc["values"][0] == {
        "coefficient": 0,
        "source_text": "- tiep theo -",
        "state": "LAYOUT_CONTINUATION_MARKER_ZERO",
    }

    unbounded_text = deepcopy(page)
    unbounded_text["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "tiep theo"
    assert _evaluate(unbounded_text)["status"] == UNRESOLVED


def test_unique_exact_closure_repairs_one_missing_four_lane_percentage_cell() -> None:
    page = _page(
        [
            _row("Doanh nghiệp nhà nước", ["-", "3.626", "0,00", None]),
            _row("Công ty TNHH khác", ["100", "50,00", "100", "50,00"]),
            _row("Công ty cổ phần khác", ["100", "50,00", "100", "50,00"]),
            _row(None, ["200", "100,00", "3.826", "100,00"], kind="TOTAL", path=[None]),
        ]
    )
    page["sections"][0]["tables"][0]["columns"] = [
        {"header_path_exact": ["31.12.2025"], "value_kind": "MONEY"},
        {"header_path_exact": ["31.12.2025", "%"], "value_kind": "PERCENT"},
        {"header_path_exact": ["31.12.2024"], "value_kind": "MONEY"},
        {"header_path_exact": ["31.12.2024", "%"], "value_kind": "PERCENT"},
    ]

    repaired = _evaluate(page)

    assert repaired["status"] == READY
    assert repaired["closure_receipt"]["source_cell_alignment_repair"]["row_id"] == "r1"
    state = next(mapping for mapping in repaired["mappings"] if mapping["report_norm_id"] == 767)
    assert [value["coefficient"] for value in state["values"]] == [0, 3626]
    assert [
        value.get("coefficient") for value in state["percentage_companion_values"]
    ] == [None, 0]

    default_closes = deepcopy(page)
    default_closes["sections"][0]["tables"][0]["rows"][-1]["values_exact"][2] = "200"
    ordinary = _evaluate(default_closes)
    assert ordinary["status"] == READY
    assert "source_cell_alignment_repair" not in ordinary["closure_receipt"]


def test_other_row_closes_visible_economic_organization_carrier() -> None:
    page = _page(
        [
            _row("Cho vay các tổ chức kinh tế", ["65", "58"]),
            _row("Công ty TNHH", ["20", "18"]),
            _row("Công ty cổ phần", ["30", "27"]),
            _row("Khác", ["10", "9"]),
            _row("Đơn vị hành chính sự nghiệp, Đảng, đoàn thể, hiệp hội", ["5", "4"]),
            _row("Cho vay cá nhân, hộ kinh doanh", ["40", "36"]),
            _row(None, ["105", "94"], kind="TOTAL", path=[None]),
        ]
    )

    result = _evaluate(page)

    assert result["status"] == READY
    assert result["reasons"] == []
    economic = next(
        equation
        for equation in result["closure_receipt"]["equations"]
        if equation["result_role"] == "ECONOMIC_ORGANIZATION_LOANS_GROUP"
    )
    assert economic["component_row_ids"] == ["r2", "r3", "r4", "r5"]


def test_partial_descendant_lane_collapses_only_the_proved_sister_lane() -> None:
    page = _page(
        [
            _row("Công ty TNHH khác", ["20", "18"]),
            _row("Công ty cổ phần khác", ["30", "27"]),
            _row("Doanh nghiệp tư nhân", ["-", None]),
            _row("Hộ kinh doanh, cá nhân", ["40", "36"]),
            _row(None, ["90", "81"], kind="TOTAL", path=[None]),
        ]
    )

    result = _evaluate(page)

    assert result["status"] == READY
    assert result["reasons"] == []
    private = next(
        mapping for mapping in result["mappings"] if mapping["report_norm_id"] == 774
    )
    assert private["values"] == [
        {"coefficient": 0, "source_text": "-", "state": "DASH_ZERO"},
        {"coefficient": None, "source_text": None, "state": "BLANK_SOURCE_CELL"},
    ]
    equations = {
        equation["result_role"]: equation
        for equation in result["closure_receipt"]["equations"]
    }
    assert equations["CORE_LOAN_ENTERPRISE_SUBTOTAL"]["lane_component_sums"] == [
        90,
        None,
    ]
    assert equations["LOAN_ENTERPRISE_FAMILY12"]["component_roles_by_lane"] == [
        ["CORE_LOAN_ENTERPRISE_SUBTOTAL"],
        [],
    ]
    assert validate_source_observation_mapping_contract_v1(result)["status"] == "PASS"


def test_explicit_group_row_branch_is_bounded_by_its_closing_total(
    tmp_path: Path,
) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    branch = "Phân tích dư nợ theo đối tượng khách hàng và loại hình doanh nghiệp"
    sibling = "Phân tích dư nợ cho vay theo ngành"
    page = _page(
        [
            _row(branch, [None, None], kind="GROUP", path=[branch]),
            _row("Hộ kinh doanh và cá nhân", ["10", "9"], path=[branch, "Hộ kinh doanh và cá nhân"]),
            _row("Công ty TNHH", ["20", "18"], path=[branch, "Công ty TNHH"]),
            _row("Công ty cổ phần", ["30", "27"], path=[branch, "Công ty cổ phần"]),
            _row("Cộng", ["60", "54"], kind="TOTAL", path=[branch, "Cộng"]),
            _row(sibling, [None, None], kind="GROUP", path=[sibling]),
            _row("Dòng ngành ngoài family", ["60", "54"], path=[sibling, "Dòng ngành ngoài family"]),
        ]
    )
    page["sections"][0]["tables"][0]["title_exact"] = "8. Cho vay khách hàng"
    identity = _ingest(database, page_json=page)

    result = _evaluate_indexed_region(database, page, identity)

    assert result["status"] == READY
    assert {"r2", "r3", "r4"} <= {
        mapping["row_id"] for mapping in result["mappings"]
    }
    assert all(mapping["row_id"] != "r7" for mapping in result["mappings"])
    assert all("DETACHED_ROOT" not in reason for reason in result["reasons"])


def test_explicit_group_row_branch_does_not_use_a_sibling_total_as_its_fence(
    tmp_path: Path,
) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    branch = "Phân tích dư nợ theo đối tượng khách hàng và loại hình doanh nghiệp"
    sibling = "Phân tích dư nợ cho vay theo ngành"
    page = _page(
        [
            _row(branch, [None, None], kind="GROUP", path=[branch]),
            _row("Hộ kinh doanh và cá nhân", ["10", "9"], path=[branch, "Hộ kinh doanh và cá nhân"]),
            _row("Công ty TNHH", ["20", "18"], path=[branch, "Công ty TNHH"]),
            _row("Công ty cổ phần", ["30", "27"], path=[branch, "Công ty cổ phần"]),
            _row(sibling, [None, None], kind="GROUP", path=[sibling]),
            _row("Dòng ngành ngoài family", ["60", "54"], path=[sibling, "Dòng ngành ngoài family"]),
            _row("Cộng", ["60", "54"], kind="TOTAL", path=[sibling, "Cộng"]),
        ]
    )
    page["sections"][0]["tables"][0]["title_exact"] = "8. Cho vay khách hàng"
    identity = _ingest(database, page_json=page)

    result = _evaluate_indexed_region(database, page, identity)

    assert result["status"] == UNRESOLVED
    assert result["mappings"] == []


def test_exact_population_group_row_authenticates_a_titleless_family_table(
    tmp_path: Path,
) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    economic = "Cho vay các tổ chức kinh tế"
    individual = "Cho vay cá nhân"
    page = _page(
        [
            _row(economic, [None, None], kind="GROUP", path=[economic]),
            _row("Công ty TNHH", ["20", "18"], path=[economic, "Công ty TNHH"]),
            _row("Công ty cổ phần", ["30", "27"], path=[economic, "Công ty cổ phần"]),
            _row(individual, [None, None], kind="GROUP", path=[individual]),
            _row("Hộ kinh doanh và cá nhân", ["40", "36"], path=[individual, "Hộ kinh doanh và cá nhân"]),
            _row(None, ["90", "81"], kind="TOTAL", path=[None]),
        ]
    )
    page["sections"][0]["tables"][0]["title_exact"] = None
    identity = _ingest(database, page_json=page)

    queried = _query(database, [identity["page_json_version_id"]])
    assert len(queried["regions"]) == 1
    assert queried["regions"][0]["structural_context_receipt"]["branch_evidence"][
        "source_kind"
    ] == "ROW_LABEL"
    assert _evaluate_indexed_region(database, page, identity)["status"] == READY


def test_flat_legal_rows_do_not_invent_a_population_group_branch(tmp_path: Path) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    page = _page(
        [
            _row("Công ty TNHH", ["20", "18"]),
            _row("Công ty cổ phần", ["30", "27"]),
            _row(None, ["50", "45"], kind="TOTAL", path=[None]),
        ]
    )
    page["sections"][0]["tables"][0]["title_exact"] = None
    identity = _ingest(database, page_json=page)

    queried = _query(database, [identity["page_json_version_id"]])

    assert queried["regions"] == []
    assert queried["candidate_dispositions"][0]["disposition"] == "BRANCH_ABSENT"


@pytest.mark.parametrize("leading", [False, True])
def test_peer_population_fence_is_exact_and_rejects_all_coherent_breaks(leading: bool) -> None:
    carrier = ["360", "324"]
    page = _page(_deferred_rows(carrier, leading=leading))
    baseline = _evaluate(page)
    assert baseline["status"] == READY
    boundaries_key = (
        "leading_parent_population_boundaries"
        if leading
        else "trailing_subtotal_population_boundaries"
    )
    assert (
        baseline["closure_receipt"][boundaries_key][0]["peer_fence_equation"]["later_total_row_id"]
        == "r13"
    )

    for mutation in ("delete_child", "peer_mismatch", "total_mismatch", "numeric_tail"):
        changed = deepcopy(page)
        rows = changed["sections"][0]["tables"][0]["rows"]
        if mutation == "delete_child":
            del rows[11]
        elif mutation == "peer_mismatch":
            rows[9]["values_exact"][0] = "12"
        elif mutation == "total_mismatch":
            rows[12]["values_exact"][0] = "999"
        else:
            rows.append(_row("Công ty cổ phần khác", ["1", "1"]))
        failed = _evaluate(changed)
        assert failed["status"] == UNRESOLVED
        assert failed["mappings"] == []


def test_structural_context_repair_atomically_updates_all_declared_surfaces() -> None:
    page = _page([_row("Doanh nghiệp nhà nước", ["10", "9"])])
    page["sections"][0]["title_exact"] = None
    page["sections"][0]["tables"][0]["title_exact"] = None
    targets = structural_context_repair_targets_v1(
        page, table_refs=[{"section_id": "s1", "table_id": "t1"}]
    )
    merged, receipt = merge_structural_context_repair_v1(
        page,
        base_page_json_version_id="gfpstorev1:json:" + "2" * 64,
        targets=targets,
        repair={
            "all_targets_transcribed": True,
            "targets": [
                {
                    "narratives_exact": ["Phân tích theo loại hình doanh nghiệp"],
                    "section_title_exact": "CHO VAY KHÁCH HÀNG",
                    "table_title_exact": "Theo loại hình doanh nghiệp",
                    "target_id": "s1:t1",
                }
            ],
            "uncertainty_exact": [],
        },
    )
    section = merged["sections"][0]
    assert section["title_exact"] == "CHO VAY KHÁCH HÀNG"
    assert section["narratives_exact"] == ["Phân tích theo loại hình doanh nghiệp"]
    assert section["tables"][0]["title_exact"] == "Theo loại hình doanh nghiệp"
    assert receipt["changes"][0]["target_id"] == "s1:t1"


def test_v8_sweep_requires_authenticated_indexed_query_evidence() -> None:
    topology, evaluation, schema = _specs()
    trial = {
        "candidate_count": 0,
        "candidates": [],
        "document_ordinal": 1,
        "mappings": [],
        "reasons": [],
        "selected_candidate_id": None,
        "source_logical_name": "bank/report.pdf",
        "source_sha256": "3" * 64,
        "status": UNRESOLVED,
    }
    with pytest.raises(ValueError, match="indexed query evidence presence"):
        build_gemini_json_flat_family_sweep_v1(
            corpus_manifest_index_id="gjfccmiv1:index:" + "4" * 64,
            topology_spec=topology,
            evaluation_spec=evaluation,
            schema_binding_spec=schema,
            trials=[trial],
        )


def test_indexed_query_decodes_one_hit_and_emits_typed_insufficient_disposition(
    tmp_path: Path,
) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    page = _page([_row("Doanh nghiệp nhà nước", ["10", "9"])])
    identity = _ingest(database, page_json=page)
    queried = _query(database, [identity["page_json_version_id"]])
    assert queried["regions"] == []
    assert queried["near_parent_sources"] == ["report.pdf"]
    assert queried["unresolved_near_parent_sources"] == []
    assert len(queried["candidate_dispositions"]) == 1
    disposition = queried["candidate_dispositions"][0]
    assert disposition["disposition"] == "INSUFFICIENT_DISTINCT_CHILD_ROLES"
    assert disposition["child_role_row_assignment"] == [
        {"role": "STATE_ENTERPRISE_LOANS", "row_id": "r1"}
    ]
    assert disposition["context_pages"] == [
        {
            "page_json_version_id": identity["page_json_version_id"],
            "physical_page": 7,
        }
    ]


def test_indexed_query_evidence_replays_sqlite_and_rejects_coherent_owner_tamper(
    tmp_path: Path,
) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    page = _page(
        [
            _row("Doanh nghiệp nhà nước", ["10", "9"]),
            _row("Doanh nghiệp có vốn đầu tư nước ngoài", ["20", "18"]),
        ]
    )
    identity = _ingest(database, page_json=page)
    queried = _query(database, [identity["page_json_version_id"]])
    assert len(queried["regions"]) == 1
    assert queried["unresolved_near_parent_sources"] == ["report.pdf"]
    evidence = _evidence(queried)
    compiled = _compiled()
    checked = _validate_indexed_query_evidence_v1(evidence, compiled_specs=compiled)
    assert (
        validate_selected_hierarchical_title_axis_query_evidence_v1(
            database,
            selected_page_json_version_ids=[identity["page_json_version_id"]],
            compiled_specs=compiled,
            source_ordinal_and_sha256_by_logical_name={"report.pdf": (1, "b" * 64)},
            indexed_query_evidence=evidence,
        )
        == checked
    )

    forged = deepcopy(evidence)
    forged_owner = forged["candidate_dispositions"][0]["owner_evidence"]
    forged_owner["source_exact"] = "CHO VAY KHÁCH HÀNG GIẢ"
    forged["accepted_regions"][0]["structural_context_receipt"]["owner_evidence"] = (
        canonical_clone_v1(forged_owner)
    )
    forged["query_receipt"]["candidate_disposition_axis_sha256"] = canonical_json_sha256_v1(
        forged["candidate_dispositions"]
    )
    forged["accepted_regions"][0]["structural_context_receipt"][
        "title_axis_query_receipt_sha256"
    ] = canonical_json_sha256_v1(forged["query_receipt"])
    _validate_indexed_query_evidence_v1(forged, compiled_specs=compiled)
    with pytest.raises(RuntimeError, match="drifted from SQLite"):
        validate_selected_hierarchical_title_axis_query_evidence_v1(
            database,
            selected_page_json_version_ids=[identity["page_json_version_id"]],
            compiled_specs=compiled,
            source_ordinal_and_sha256_by_logical_name={"report.pdf": (1, "b" * 64)},
            indexed_query_evidence=forged,
        )


@pytest.mark.parametrize(
    ("row_count", "branch_present", "expected_disposition", "expected_scope"),
    [
        (1, True, "INSUFFICIENT_DISTINCT_CHILD_ROLES", "ROW_LABEL_AND_VALUES"),
        (2, False, "BRANCH_ABSENT", "STRUCTURAL_CONTEXT_SURFACES"),
    ],
)
def test_pre_evaluation_disposition_builds_only_bounded_authenticated_repair(
    tmp_path: Path,
    row_count: int,
    branch_present: bool,
    expected_disposition: str,
    expected_scope: str,
) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    rows = [
        _row("Doanh nghiệp nhà nước", ["10", "9"]),
        _row("Doanh nghiệp có vốn đầu tư nước ngoài", ["20", "18"]),
    ][:row_count]
    page = _page(rows)
    if not branch_present:
        page["sections"][0]["tables"][0]["title_exact"] = "Bảng chi tiết"
    identity = _ingest(database, page_json=page)
    queried = _query(database, [identity["page_json_version_id"]])
    disposition = queried["candidate_dispositions"][0]
    assert disposition["disposition"] == expected_disposition
    sweep = _unresolved_sweep(queried)
    plans = build_family_region_repair_plans_v1(
        sweep=sweep,
        page_json_by_version={identity["page_json_version_id"]: page},
        compiled_specs=_compiled(),
    )
    assert len(plans) == 1
    assert plans[0]["repair_scope"] == expected_scope
    assert plans[0]["structural_context_pages"] == disposition["context_pages"]
    assert plans[0]["target_table_refs"] == [{"section_id": "s1", "table_id": "t1"}]
    assert plans[0]["query_disposition_sha256"] == canonical_json_sha256_v1(disposition)


def test_owner_absent_is_not_unresolved_family_evidence_and_has_no_repair_job(
    tmp_path: Path,
) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    page = _page(
        [
            _row("Doanh nghiệp nhà nước", ["10", "9"]),
            _row("Doanh nghiệp có vốn đầu tư nước ngoài", ["20", "18"]),
        ]
    )
    page["sections"][0]["title_exact"] = "THUYẾT MINH"
    identity = _ingest(database, page_json=page)
    queried = _query(database, [identity["page_json_version_id"]])
    assert queried["near_parent_sources"] == ["report.pdf"]
    assert queried["unresolved_near_parent_sources"] == []
    assert queried["candidate_dispositions"][0]["disposition"] == ("OWNER_ABSENT_OR_AMBIGUOUS")
    sweep = _unresolved_sweep(queried)
    assert sweep["trials"][0]["status"] == UNRESOLVED
    assert (
        build_family_region_repair_plans_v1(
            sweep=sweep,
            page_json_by_version={identity["page_json_version_id"]: page},
            compiled_specs=_compiled(),
        )
        == []
    )


def test_near_source_policy_requires_paired_axes_across_whole_document_frontier(
    tmp_path: Path,
) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    rows = [
        _row("Doanh nghiệp nhà nước", ["10", "9"]),
        _row("Doanh nghiệp có vốn đầu tư nước ngoài", ["20", "18"]),
    ]
    owner_only = _page(deepcopy(rows))
    owner_only["sections"][0]["tables"][0]["title_exact"] = "Bảng chi tiết"
    owner_identity = _ingest(
        database,
        physical_page=7,
        image_sha256="7" * 64,
        page_json=owner_only,
    )
    branch_only = _page(deepcopy(rows))
    branch_only["sections"][0]["title_exact"] = "THUYẾT MINH"
    branch_identity = _ingest(
        database,
        physical_page=20,
        image_sha256="8" * 64,
        prompt_sha256="9" * 64,
        page_json=branch_only,
    )
    queried = _query(
        database,
        [
            owner_identity["page_json_version_id"],
            branch_identity["page_json_version_id"],
        ],
    )
    assert queried["regions"] == []
    assert queried["near_parent_sources"] == ["report.pdf"]
    assert queried["unresolved_near_parent_sources"] == []
    assert {item["disposition"] for item in queried["candidate_dispositions"]} == {
        "BRANCH_ABSENT",
        "OWNER_ABSENT_OR_AMBIGUOUS",
    }


def test_accepted_source_suppresses_unrelated_pre_evaluation_repair(
    tmp_path: Path,
) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    page = _page(
        [
            _row("Doanh nghiệp nhà nước", ["10", "9"]),
            _row("Doanh nghiệp có vốn đầu tư nước ngoài", ["20", "18"]),
        ]
    )
    unrelated = deepcopy(page["sections"][0]["tables"][0])
    unrelated["title_exact"] = "Bảng chi tiết khác"
    page["sections"][0]["tables"].append(unrelated)
    identity = _ingest(database, page_json=page)
    queried = _query(database, [identity["page_json_version_id"]])
    assert {item["disposition"] for item in queried["candidate_dispositions"]} == {
        "ACCEPTED",
        "BRANCH_ABSENT",
    }
    sweep = _unresolved_sweep(queried)
    assert (
        build_family_region_repair_plans_v1(
            sweep=sweep,
            page_json_by_version={identity["page_json_version_id"]: page},
            compiled_specs=_compiled(),
        )
        == []
    )


def test_detached_root_frontier_rejects_unknown_numeric_and_multiple_totals() -> None:
    parent = "Cho vay khách hàng"
    rows = [
        _row(parent, [None, None], kind="GROUP", path=[parent]),
        _row("Doanh nghiệp nhà nước", ["10", "9"], path=[parent, "Doanh nghiệp nhà nước"]),
        _row(
            "Doanh nghiệp có vốn đầu tư nước ngoài",
            ["20", "18"],
            path=[parent, "Doanh nghiệp có vốn đầu tư nước ngoài"],
        ),
        _row(
            "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
            ["5", "4"],
        ),
        _row(None, ["35", "31"], kind="TOTAL", path=[None]),
    ]
    page = _page(rows)
    page["sections"][0]["title_exact"] = "THUYẾT MINH"
    baseline = _evaluate(page)
    assert baseline["status"] == READY
    assert baseline["closure_receipt"]["detached_root_frontier"]["total_row_ids"] == ["r5"]

    unknown = deepcopy(page)
    unknown["sections"][0]["tables"][0]["rows"].insert(4, _row("Dòng số ngoài graph", ["1", "1"]))
    assert _evaluate(unknown)["status"] == UNRESOLVED

    duplicate_total = deepcopy(page)
    duplicate_total["sections"][0]["tables"][0]["rows"].append(
        _row(None, ["35", "31"], kind="TOTAL", path=[None])
    )
    assert _evaluate(duplicate_total)["status"] == UNRESOLVED


def test_structural_disposition_repair_requeries_context_before_ready(
    tmp_path: Path,
) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    base_page = _page(
        [
            _row("Doanh nghiệp nhà nước", ["10", "9"]),
            _row("Doanh nghiệp có vốn đầu tư nước ngoài", ["20", "18"]),
            _row(None, ["30", "27"], kind="TOTAL", path=[None]),
        ]
    )
    base_page["sections"][0]["tables"][0]["title_exact"] = "Bảng chi tiết"
    base = _ingest(database, page_json=base_page)
    queried = _query(database, [base["page_json_version_id"]])
    sweep = _unresolved_sweep(queried)
    plans = build_family_region_repair_plans_v1(
        sweep=sweep,
        page_json_by_version={base["page_json_version_id"]: base_page},
        compiled_specs=_compiled(),
    )
    assert len(plans) == 1
    repaired_page = deepcopy(base_page)
    repaired_page["sections"][0]["tables"][0]["title_exact"] = (
        "Phân tích theo loại hình doanh nghiệp"
    )
    repaired = _ingest(
        database,
        page_json=repaired_page,
        prompt_sha256="f" * 64,
        prompt_variant="region-repair-structural-context-surfaces",
    )
    candidate = _evaluate_indexed_query_disposition_repair_v1(
        plan=plans[0],
        repaired_page_json_version_id=repaired["page_json_version_id"],
        compiled_specs=_compiled(),
        page_database=database,
    )
    assert candidate["status"] == READY
    assert {mapping["report_norm_id"] for mapping in candidate["mappings"]} == {
        766,
        767,
        779,
    }
