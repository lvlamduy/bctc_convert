from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/experiments/run_gemini_json_first_accounting_family_v1.py"
SPEC = importlib.util.spec_from_file_location("run_gemini_json_first_accounting_family_v1", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
target = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(target)


def test_parser_accepts_separate_effective_frontier_artifact_root(tmp_path) -> None:
    frontier = tmp_path / "frontier.json"
    corpus_root = tmp_path / "corpus"
    repair_root = tmp_path / "repair"
    corpus_root.mkdir()
    repair_root.mkdir()
    args = target._parser().parse_args(
        [
            "--corpus-index",
            str(tmp_path / "index.json"),
            "--artifact-root",
            str(corpus_root),
            "--effective-page-frontier",
            str(frontier),
            "--effective-page-artifact-root",
            str(repair_root),
            "--topology-spec",
            str(tmp_path / "topology.json"),
            "--evaluation-spec",
            str(tmp_path / "evaluation.json"),
            "--schema-binding-spec",
            str(tmp_path / "schema.json"),
            "--results-database",
            str(tmp_path / "results.sqlite3"),
            "--run-kind",
            "EXPERIMENTAL",
            "--output",
            str(tmp_path / "sweep.json"),
        ]
    )
    assert args.effective_page_frontier == frontier
    assert args.effective_page_artifact_root == repair_root


def test_query_anchor_axis_does_not_eagerly_require_legacy_fallback() -> None:
    compiled = {"query_anchor_alias_groups": [["owner"], ["child"]]}
    assert target._query_anchor_groups_v1(compiled) == [["owner"], ["child"]]
    assert target._query_anchor_groups_v1({"anchor_alias_groups": [["legacy"]]}) == [["legacy"]]
    assert target._query_anchor_groups_v1({}) == []


def test_dual_axis_runner_passes_compiled_external_population_control_exactly() -> None:
    family_root = ROOT / "config/families"
    topology, evaluation, schema = (
        json.loads(
            (
                family_root
                / f"tm-loan-geographic-classification-{kind}-v1.json"
            ).read_text(encoding="utf-8")
        )
        for kind in ("topology", "evaluation", "schema-binding")
    )
    compiled = target.compile_gemini_json_flat_family_specs_v1(
        topology, evaluation, schema
    )

    kwargs = target._dual_axis_query_kwargs_v1(compiled)

    assert kwargs["external_population_control"] == compiled[
        "dual_axis_projection_policy"
    ]["external_population_control"]
    assert kwargs["external_population_control"] is not compiled[
        "dual_axis_projection_policy"
    ]["external_population_control"]
    assert kwargs["external_population_control"]["control_report_norm_id"] == 716


def _compiled() -> dict:
    paths = (
        "config/families/tm-interbank-deposits-loans-topology-v4.json",
        "config/families/tm-interbank-deposits-loans-evaluation-v4.json",
        "config/families/tm-interbank-deposits-loans-schema-binding-v4.json",
    )
    topology, evaluation, schema = (
        json.loads((ROOT / path).read_text(encoding="utf-8")) for path in paths
    )
    return target.compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)


def _mapping(role: str, report_norm_id: int, values: tuple[int, int]) -> dict:
    return {
        "columns": [{"value_kind": "MONEY"}, {"value_kind": "MONEY"}],
        "report_norm_id": report_norm_id,
        "role": role,
        "values": [
            {"coefficient": value, "source_text": str(value), "state": "RAW_SIGNED_INTEGER"}
            for value in values
        ],
    }


def _candidate(candidate_id: str, roles: list[tuple[str, int]]) -> dict:
    return {
        "candidate_id": candidate_id,
        "mappings": [
            _mapping(
                role,
                report_norm_id,
                (170, 139) if role == "INTERBANK_DEPOSITS_AND_LOANS" else (1, 1),
            )
            for role, report_norm_id in roles
        ],
    }


def _traceable_candidate(candidate_id: str, table_id: str, roles: list[tuple[str, int]]) -> dict:
    candidate = _candidate(candidate_id, roles)
    candidate.update(
        {
            "closure_receipt": {"rule": "EXACT", "table_id": table_id},
            "family_id": "INTERBANK_DEPOSITS_AND_LOANS",
            "page_json_version_id": "gfpstorev1:json:" + "1" * 64,
            "physical_page": 7,
            "reasons": [],
            "section_id": "s1",
            "status": target.READY,
            "table_id": table_id,
        }
    )
    return candidate


def test_exact_role_rich_detail_uniquely_supersedes_its_summary() -> None:
    summary = _candidate(
        "summary",
        [
            ("INTERBANK_DEPOSITS_AND_LOANS", 575),
            ("INTERBANK_DEPOSIT_GROUP", 576),
            ("INTERBANK_LOAN_GROUP", 585),
            ("TOTAL_INTERBANK_PROVISION", 5718),
        ],
    )
    detail = _candidate(
        "detail",
        [
            ("INTERBANK_DEPOSITS_AND_LOANS", 575),
            ("INTERBANK_DEPOSIT_GROUP", 576),
            ("DEMAND_DEPOSIT_GROUP", 577),
            ("DEMAND_DEPOSIT_VND", 578),
            ("TERM_DEPOSIT_GROUP", 580),
            ("TERM_DEPOSIT_VND", 581),
            ("INTERBANK_LOAN_GROUP", 585),
            ("INTERBANK_LOAN_VND", 586),
            ("INTERBANK_LOAN_PROVISION", 590),
        ],
    )
    assert target._selected_ready_candidate([summary, detail], compiled_specs=_compiled()) == detail


def test_candidate_selection_rejects_root_drift_and_equal_detail_ambiguity() -> None:
    roles = [
        ("INTERBANK_DEPOSITS_AND_LOANS", 575),
        ("INTERBANK_DEPOSIT_GROUP", 576),
        ("INTERBANK_LOAN_GROUP", 585),
    ]
    first = _candidate("first", roles)
    second = _candidate("second", roles)
    assert target._selected_ready_candidate([first, second], compiled_specs=_compiled()) is None
    second["mappings"][0]["values"][0]["coefficient"] += 1
    assert target._selected_ready_candidate([first, second], compiled_specs=_compiled()) is None


def test_exact_duplicate_summary_and_titled_note_selects_note_only_with_full_provenance() -> None:
    roles = [
        ("INTERBANK_DEPOSITS_AND_LOANS", 575),
        ("INTERBANK_DEPOSIT_GROUP", 576),
        ("INTERBANK_LOAN_GROUP", 585),
    ]
    summary = _traceable_candidate("summary", "t1", roles)
    summary["parent_binding_kind"] = "EXPLICIT_PARENT_ROW"
    note = _traceable_candidate("note", "t2", roles)
    note["parent_binding_kind"] = "EXPLICIT_SECTION_OR_TABLE_TITLE"
    note["physical_page"] = 21
    note["page_json_version_id"] = "gfpstorev1:json:" + "2" * 64

    assert target._selected_ready_candidate([summary, note], compiled_specs=_compiled()) == note

    note["mappings"][1]["values"][0]["coefficient"] += 1
    assert target._selected_ready_candidate([summary, note], compiled_specs=_compiled()) is None


def test_explicit_parent_binding_uniquely_supersedes_shape_only_child_cluster() -> None:
    roles = [
        ("INTERBANK_DEPOSITS_AND_LOANS", 575),
        ("INTERBANK_DEPOSIT_GROUP", 576),
        ("INTERBANK_LOAN_GROUP", 585),
    ]
    explicit = _candidate("explicit", roles)
    explicit["parent_binding_kind"] = "EXPLICIT_SECTION_OR_TABLE_TITLE"
    implied = _candidate("implied", roles)
    implied["parent_binding_kind"] = "UNIQUE_REQUIRED_CHILD_CLUSTER"
    implied["mappings"][0]["values"][0]["coefficient"] += 1
    assert (
        target._selected_ready_candidate([implied, explicit], compiled_specs=_compiled())
        == explicit
    )

    peer = _candidate("peer", roles)
    peer["parent_binding_kind"] = "EXPLICIT_PARENT_ROW"
    assert target._selected_ready_candidate([explicit, peer], compiled_specs=_compiled()) is None


def test_decisive_hard_negative_candidate_is_removed_from_family_disposition() -> None:
    candidate = {
        "reasons": ["HARD_NEGATIVE_FAMILY_TITLE_PRESENT"],
        "status": target.UNRESOLVED,
    }
    assert target._candidate_is_decisive_hard_negative(candidate)

    candidate["reasons"] = ["FAMILY_PARENT_NOT_VISIBLE"]
    assert not target._candidate_is_decisive_hard_negative(candidate)

    candidate["reasons"] = ["HARD_NEGATIVE_FAMILY_TITLE_PRESENT"]
    candidate["status"] = target.READY
    assert not target._candidate_is_decisive_hard_negative(candidate)


def test_v2_explicit_parent_cluster_discards_only_unowned_anchor_collisions() -> None:
    candidate = {
        "reasons": ["FAMILY_PARENT_NOT_VISIBLE_IN_SECTION_OR_TABLE_TITLE"],
        "status": target.UNRESOLVED,
    }
    compiled = {
        "engine_format_version": "GEMINI_JSON_HIERARCHICAL_ACCOUNTING_FAMILY_SWEEP_V2",
        "topology": {"presence_evidence_mode": "WITHIN_EXPLICIT_PARENT_CLUSTER"},
    }
    assert target._candidate_is_unowned_explicit_parent_cluster_v1(
        candidate,
        compiled_specs=compiled,
        source_has_near_parent_evidence=False,
    )
    assert not target._candidate_is_unowned_explicit_parent_cluster_v1(
        candidate,
        compiled_specs=compiled,
        source_has_near_parent_evidence=True,
    )

    compiled["engine_format_version"] = "GEMINI_JSON_HIERARCHICAL_ACCOUNTING_FAMILY_SWEEP_V3"
    assert not target._candidate_is_unowned_explicit_parent_cluster_v1(
        candidate,
        compiled_specs=compiled,
        source_has_near_parent_evidence=False,
    )


def test_near_aliases_exclude_query_only_parent_and_owner_anchors() -> None:
    compiled = {
        "aliases_by_role": {"CHILD": ["child-normalized"]},
        "anchor_alias_groups": [["owner-normalized"], ["child-normalized"]],
        "query_aliases_by_role": {"CHILD": ["Child (raw punctuation)"]},
        "query_anchor_alias_groups": [
            [["Owner raw"], ["Child (raw punctuation)"]],
            [["Parent raw"], ["Child (raw punctuation)"]],
        ],
        "topology": {"required_role_combinations": [["CHILD"]]},
    }
    assert target._near_anchor_aliases_v1(compiled, stacked=False) == ["Child (raw punctuation)"]
    assert target._near_anchor_aliases_v1(compiled, stacked=True) == [
        "Child (raw punctuation)",
        "Owner raw",
        "Parent raw",
    ]


def test_generic_continuation_binds_only_one_adjacent_explicit_negative_family() -> None:
    current_id = "gfpstorev1:json:" + "1" * 64
    before_id = "gfpstorev1:json:" + "2" * 64
    after_id = "gfpstorev1:json:" + "3" * 64

    def page(title: str) -> dict:
        return {
            "page_json": {
                "sections": [
                    {
                        "tables": [],
                        "title_exact": title,
                    }
                ]
            }
        }

    candidate = {
        "candidate_id": "candidate",
        "reasons": [
            "FAMILY_PARENT_NOT_VISIBLE_IN_SECTION_TABLE_OR_UNIQUE_ROW",
            "HIERARCHICAL_SOLUTION_COUNT_NOT_ONE:0",
        ],
        "status": target.UNRESOLVED,
    }
    region = {
        "context_pages": [
            {"page_json_version_id": before_id, "physical_page": 38},
            {"page_json_version_id": current_id, "physical_page": 39},
            {"page_json_version_id": after_id, "physical_page": 40},
        ],
        "page_json_version_id": current_id,
        "physical_page": 39,
    }
    pages = {
        before_id: page("11. HOẠT ĐỘNG MUA NỢ"),
        current_id: page("THUYẾT MINH BÁO CÁO TÀI CHÍNH (tiếp theo)"),
        after_id: page(
            "12. CHỨNG KHOÁN ĐẦU TƯ (tiếp theo) - Chứng khoán đầu tư giữ đến ngày đáo hạn"
        ),
    }
    result = target._with_adjacent_continuation_hard_negative_v1(
        candidate,
        region=region,
        page_by_version=pages,
        parent_aliases=["Chứng khoán kinh doanh"],
        hard_negative_aliases=[
            "Chứng khoán đầu tư",
            "Chứng khoán đầu tư giữ đến ngày đáo hạn",
        ],
    )
    assert result["reasons"] == [
        "FAMILY_PARENT_NOT_VISIBLE_IN_SECTION_TABLE_OR_UNIQUE_ROW",
        "HARD_NEGATIVE_FAMILY_TITLE_PRESENT",
        "HIERARCHICAL_SOLUTION_COUNT_NOT_ONE:0",
    ]
    assert result["continuation_hard_negative_receipt"] == {
        "candidate_page_json_version_id": current_id,
        "candidate_physical_page": 39,
        "context_match": {
            "hard_negative_alias": "Chứng khoán đầu tư giữ đến ngày đáo hạn",
            "page_json_version_id": after_id,
            "physical_page": 40,
            "source_title_exact": (
                "12. CHỨNG KHOÁN ĐẦU TƯ (tiếp theo) - Chứng khoán đầu tư giữ đến ngày đáo hạn"
            ),
        },
        "rule": ("GENERIC_CONTINUATION_BOUND_TO_ONE_ADJACENT_EXPLICIT_HARD_NEGATIVE_CONTINUATION"),
    }
    assert candidate["reasons"] == [
        "FAMILY_PARENT_NOT_VISIBLE_IN_SECTION_TABLE_OR_UNIQUE_ROW",
        "HIERARCHICAL_SOLUTION_COUNT_NOT_ONE:0",
    ]

    no_continuation = json.loads(json.dumps(pages))
    no_continuation[current_id] = page("THUYẾT MINH BÁO CÁO TÀI CHÍNH")
    assert (
        target._with_adjacent_continuation_hard_negative_v1(
            candidate,
            region=region,
            page_by_version=no_continuation,
            parent_aliases=["Chứng khoán kinh doanh"],
            hard_negative_aliases=["Chứng khoán đầu tư"],
        )
        == candidate
    )

    adjacent_parent = json.loads(json.dumps(pages))
    adjacent_parent[before_id] = page("7. Chứng khoán kinh doanh (tiếp theo)")
    assert (
        target._with_adjacent_continuation_hard_negative_v1(
            candidate,
            region=region,
            page_by_version=adjacent_parent,
            parent_aliases=["Chứng khoán kinh doanh"],
            hard_negative_aliases=["Chứng khoán đầu tư"],
        )
        == candidate
    )

    two_negative_pages = json.loads(json.dumps(pages))
    two_negative_pages[before_id] = page("Chứng khoán đầu tư (tiếp theo)")
    assert (
        target._with_adjacent_continuation_hard_negative_v1(
            candidate,
            region=region,
            page_by_version=two_negative_pages,
            parent_aliases=["Chứng khoán kinh doanh"],
            hard_negative_aliases=["Chứng khoán đầu tư"],
        )
        == candidate
    )


def test_exact_balance_date_conflicting_with_unique_typed_reporting_endpoint_is_unresolved() -> None:
    current_id = "gfpstorev1:json:" + "4" * 64
    adjacent_id = "gfpstorev1:json:" + "5" * 64
    candidate = {
        "candidate_id": "gjfafcv1:candidate:" + "6" * 64,
        "closure_receipt": {
            "period_value_column_axis": {
                "period_signatures": [
                    ["DATE", "2025-12-31"],
                    ["DATE", "2024-12-31"],
                ]
            }
        },
        "mappings": [{"report_norm_id": 753}],
        "reasons": [],
        "status": target.READY,
    }
    region = {
        "context_pages": [
            {"page_json_version_id": current_id, "physical_page": 26},
            {"page_json_version_id": adjacent_id, "physical_page": 27},
        ],
        "physical_page": 26,
    }
    pages = {
        current_id: {
            "page_json": {
                "sections": [{"tables": [], "title_exact": "6. CHO VAY KHÁCH HÀNG"}]
            }
        },
        adjacent_id: {
            "page_json": {
                "sections": [
                    {
                        "tables": [],
                        "title_exact": (
                            "NGÂN HÀNG TMCP THỊNH VƯỢNG VÀ PHÁT TRIỂN\n"
                            "THUYẾT MINH BÁO CÁO TÀI CHÍNH\n"
                            "Cho giai đoạn từ ngày 01/01/2025 đến 31/03/2025"
                        ),
                    }
                ]
            }
        },
    }
    result = target._with_reporting_endpoint_conflict_v1(
        candidate,
        region=region,
        page_by_version=pages,
        compiled_specs={
            "evaluation": {"period_semantics": "BALANCE_COMPARATIVE"},
            "topology": {"family_id": "LOAN_MATURITY_BUCKETS"},
        },
    )

    assert result["status"] == target.UNRESOLVED
    assert result["mappings"] == []
    assert result["reasons"] == ["CURRENT_PERIOD_CONFLICTS_WITH_TYPED_REPORTING_ENDPOINT"]
    assert result["candidate_id"] != candidate["candidate_id"]
    assert result["reporting_endpoint_conflict_receipt"] == {
        "candidate_current_period_signature": ["DATE", "2025-12-31"],
        "context_matches": [
            {
                "date_axis": [
                    {
                        "date": "2025-01-01",
                        "source_span": [
                            pages[adjacent_id]["page_json"]["sections"][0]["title_exact"].index(
                                "01/01/2025"
                            ),
                            pages[adjacent_id]["page_json"]["sections"][0]["title_exact"].index(
                                "01/01/2025"
                            )
                            + len("01/01/2025"),
                        ],
                        "source_text": "01/01/2025",
                    },
                    {
                        "date": "2025-03-31",
                        "source_span": [
                            pages[adjacent_id]["page_json"]["sections"][0]["title_exact"].index(
                                "31/03/2025"
                            ),
                            pages[adjacent_id]["page_json"]["sections"][0]["title_exact"].index(
                                "31/03/2025"
                            )
                            + len("31/03/2025"),
                        ],
                        "source_text": "31/03/2025",
                    },
                ],
                "page_json_version_id": adjacent_id,
                "physical_page": 27,
                "reporting_endpoint": "2025-03-31",
                "source_title_exact": pages[adjacent_id]["page_json"]["sections"][0][
                    "title_exact"
                ],
                "title_ordinal": 1,
            }
        ],
        "reporting_endpoint": "2025-03-31",
        "rule": "UNIQUE_TYPED_LOCAL_REPORTING_ENDPOINT_CONFLICTS_WITH_EXACT_BALANCE_DATE",
        "superseded_candidate_id": candidate["candidate_id"],
    }
    assert candidate["status"] == target.READY
    assert candidate["mappings"] == [{"report_norm_id": 753}]


def test_reporting_endpoint_guard_ignores_non_authoritative_or_ambiguous_context() -> None:
    current_id = "gfpstorev1:json:" + "7" * 64
    adjacent_id = "gfpstorev1:json:" + "8" * 64
    candidate = {
        "candidate_id": "gjfafcv1:candidate:" + "9" * 64,
        "closure_receipt": {
            "period_value_column_axis": {
                "period_signatures": [
                    ["DATE", "2025-12-31"],
                    ["DATE", "2024-12-31"],
                ]
            }
        },
        "mappings": [{"report_norm_id": 753}],
        "reasons": [],
        "status": target.READY,
    }
    region = {
        "context_pages": [
            {"page_json_version_id": current_id, "physical_page": 26},
            {"page_json_version_id": adjacent_id, "physical_page": 27},
        ],
        "physical_page": 26,
    }

    def pages(*titles: str) -> dict:
        return {
            current_id: {
                "page_json": {"sections": [{"tables": [], "title_exact": titles[0]}]}
            },
            adjacent_id: {
                "page_json": {
                    "sections": [
                        {"tables": [], "title_exact": title} for title in titles[1:]
                    ]
                }
            },
        }

    compiled = {
        "evaluation": {"period_semantics": "BALANCE_COMPARATIVE"},
        "topology": {"family_id": "LOAN_MATURITY_BUCKETS"},
    }
    unchanged_contexts = [
        # The exact endpoint agrees with the current balance date.
        pages("6. Cho vay khách hàng", "Cho giai đoạn từ 01/01/2025 đến 31/12/2025"),
        # A bare year cannot be fabricated into a reporting endpoint.
        pages("6. Cho vay khách hàng", "Cho giai đoạn từ năm 2024 đến năm 2025"),
        # A reversed range is not authoritative reporting-period evidence.
        pages("6. Cho vay khách hàng", "Cho giai đoạn từ 31/03/2025 đến 01/01/2025"),
        # Two distinct typed endpoints are ambiguous local context.
        pages(
            "Cho giai đoạn từ 01/01/2025 đến 31/03/2025",
            "Cho giai đoạn từ 01/01/2025 đến 30/06/2025",
        ),
    ]
    for page_by_version in unchanged_contexts:
        assert (
            target._with_reporting_endpoint_conflict_v1(
                candidate,
                region=region,
                page_by_version=page_by_version,
                compiled_specs=compiled,
            )
            == candidate
        )

    relative_candidate = json.loads(json.dumps(candidate))
    relative_candidate["closure_receipt"]["period_value_column_axis"]["period_signatures"][
        0
    ] = ["ROLE", "CURRENT"]
    assert (
        target._with_reporting_endpoint_conflict_v1(
            relative_candidate,
            region=region,
            page_by_version=pages(
                "6. Cho vay khách hàng",
                "Cho giai đoạn từ 01/01/2025 đến 31/03/2025",
            ),
            compiled_specs=compiled,
        )
        == relative_candidate
    )

    other_family = json.loads(json.dumps(candidate))
    assert (
        target._with_reporting_endpoint_conflict_v1(
            other_family,
            region=region,
            page_by_version=pages(
                "6. Cho vay khách hàng",
                "Cho giai đoạn từ 01/01/2025 đến 31/03/2025",
            ),
            compiled_specs={
                "evaluation": {"period_semantics": "BALANCE_COMPARATIVE"},
                "topology": {"family_id": "LOAN_INDUSTRY_CLASSIFICATION"},
            },
        )
        == other_family
    )

def test_stacked_regions_are_derived_from_one_hit_frontier_with_punctuation_variants() -> None:
    parent = "Các công cụ tài chính phái sinh và các tài sản/khoản nợ tài chính khác"
    hit = {
        "hierarchy_path_exact": [],
        "label_exact": "I. Giao dịch kỳ hạn tiền tệ",
        "page_json_version_id": "gfpstorev1:json:" + "1" * 64,
        "physical_page": 38,
        "row_id": "r2",
        "section_id": "s2",
        "section_title_exact": (
            "8. CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÁC TÀI SẢN/(KHOẢN NỢ) TÀI CHÍNH KHÁC"
        ),
        "source_logical_name": "VIB/report.pdf",
        "table_has_explicit_parent_row": 0,
        "table_id": "t1",
        "table_title_exact": None,
    }
    regions = target._stacked_candidate_regions_from_hits_v1(
        [hit],
        anchor_alias_groups=[[[parent], ["Giao dịch kỳ hạn tiền tệ"]]],
        parent_aliases=[target.normalize_vietnamese_anchor_v1(parent)],
    )
    assert regions == [
        {
            "page_json_version_id": "gfpstorev1:json:" + "1" * 64,
            "physical_page": 38,
            "section_id": "s2",
            "source_logical_name": "VIB/report.pdf",
            "table_id": "t1",
        }
    ]


def test_stacked_regions_require_distinct_rows_for_child_child_anchor() -> None:
    hit = {
        "hierarchy_path_exact": [],
        "label_exact": "Giao dịch hoán đổi tiền tệ",
        "page_json_version_id": "gfpstorev1:json:" + "2" * 64,
        "physical_page": 7,
        "row_id": "r1",
        "section_id": "s1",
        "section_title_exact": "Công cụ tài chính phái sinh",
        "source_logical_name": "bank/report.pdf",
        "table_has_explicit_parent_row": 0,
        "table_id": "t1",
        "table_title_exact": None,
    }
    assert (
        target._stacked_candidate_regions_from_hits_v1(
            [hit],
            anchor_alias_groups=[[["Giao dịch hoán đổi tiền tệ"], ["Giao dịch hoán đổi tiền tệ"]]],
            parent_aliases=["cong cu tai chinh phai sinh"],
        )
        == []
    )


def test_row_level_parent_authority_is_opt_in_for_recursive_json_engine() -> None:
    hit = {
        "hierarchy_path_exact": ["Tiền gửi và cho vay các TCTD khác"],
        "label_exact": "Tiền gửi và cho vay các TCTD khác",
        "section_title_exact": "BẢNG CÂN ĐỐI KẾ TOÁN",
        "table_has_explicit_parent_row": 1,
        "table_title_exact": None,
    }
    aliases = _compiled()["topology"]["parent"]["aliases"]
    assert not target._hit_has_explicit_parent(
        hit,
        allow_row_parent=False,
        parent_aliases=aliases,
    )
    assert target._hit_has_explicit_parent(
        hit,
        allow_row_parent=True,
        parent_aliases=aliases,
    )


def test_disjoint_equivalent_table_presentations_are_composed_without_double_counting() -> None:
    issuer = _traceable_candidate(
        "issuer",
        "t1",
        [
            ("INTERBANK_DEPOSITS_AND_LOANS", 575),
            ("DEMAND_DEPOSIT_VND", 578),
        ],
    )
    currency = _traceable_candidate(
        "currency",
        "t2",
        [
            ("INTERBANK_DEPOSITS_AND_LOANS", 575),
            ("TERM_DEPOSIT_VND", 581),
        ],
    )
    selected = target._selected_ready_candidate([issuer, currency], compiled_specs=_compiled())
    assert selected is not None
    assert selected["component_table_ids"] == ["t1", "t2"]
    assert [mapping["role"] for mapping in selected["mappings"]] == [
        "INTERBANK_DEPOSITS_AND_LOANS",
        "DEMAND_DEPOSIT_VND",
        "TERM_DEPOSIT_VND",
    ]
    assert selected["closure_receipt"]["component_candidate_ids"] == [
        "issuer",
        "currency",
    ]

    overlap = _traceable_candidate(
        "overlap",
        "t3",
        [
            ("INTERBANK_DEPOSITS_AND_LOANS", 575),
            ("DEMAND_DEPOSIT_VND", 578),
        ],
    )
    assert target._selected_ready_candidate([issuer, overlap], compiled_specs=_compiled()) is None
    currency["section_id"] = "s2"
    assert target._selected_ready_candidate([issuer, currency], compiled_specs=_compiled()) is None

    currency["page_json_version_id"] = "gfpstorev1:json:" + "2" * 64
    currency["physical_page"] = 8
    issuer["mappings"][0]["columns"] = [
        {"header_path_exact": ["2025", "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": ["2024", "Triệu đồng"], "value_kind": "MONEY"},
    ]
    currency["mappings"][0]["columns"] = [
        {"header_path_exact": ["2025"], "value_kind": "MONEY"},
        {"header_path_exact": ["2024"], "value_kind": "MONEY"},
    ]
    adjacent = target._selected_ready_candidate([currency, issuer], compiled_specs=_compiled())
    assert adjacent is not None
    assert adjacent["component_page_json_version_ids"] == [
        issuer["page_json_version_id"],
        currency["page_json_version_id"],
    ]
    assert adjacent["closure_receipt"]["rule"].startswith("ADJACENT_CONTINUATION_")

    currency["physical_page"] = 9
    assert target._selected_ready_candidate([issuer, currency], compiled_specs=_compiled()) is None


def test_net_adjusted_table_supersedes_adjacent_gross_view_and_keeps_both_axes() -> None:
    net = _traceable_candidate(
        "net",
        "t1",
        [
            ("INTERBANK_DEPOSITS_AND_LOANS", 575),
            ("DEMAND_DEPOSIT_VND", 578),
        ],
    )
    gross = _traceable_candidate(
        "gross",
        "t1",
        [
            ("INTERBANK_DEPOSITS_AND_LOANS", 575),
            ("TERM_DEPOSIT_VND", 581),
        ],
    )
    columns = [
        {"header_path_exact": ["2025", "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": ["2024", "Triệu đồng"], "value_kind": "MONEY"},
    ]
    net["mappings"][0]["columns"] = columns
    gross["mappings"][0]["columns"] = [
        {"header_path_exact": ["2025"], "value_kind": "MONEY"},
        {"header_path_exact": ["2024"], "value_kind": "MONEY"},
    ]
    for value, coefficient in zip(net["mappings"][0]["values"], (90, 80), strict=True):
        value["coefficient"] = coefficient
        value["source_text"] = str(coefficient)
    for value, coefficient in zip(gross["mappings"][0]["values"], (100, 90), strict=True):
        value["coefficient"] = coefficient
        value["source_text"] = str(coefficient)
    net["closure_receipt"] = {
        "equations": [
            {
                "component_roles": [],
                "result_coefficients": [-10, -10],
                "result_role": "TOTAL_INTERBANK_PROVISION",
            },
            {
                "component_roles": [
                    "INTERBANK_DEPOSIT_GROUP",
                    "INTERBANK_LOAN_GROUP",
                    "TOTAL_INTERBANK_PROVISION",
                ],
                "result_coefficients": [90, 80],
                "result_role": "INTERBANK_DEPOSITS_AND_LOANS",
            },
        ]
    }
    gross["closure_receipt"] = {
        "equations": [
            {
                "component_roles": [
                    "INTERBANK_DEPOSIT_GROUP",
                    "INTERBANK_LOAN_GROUP",
                ],
                "result_coefficients": [100, 90],
                "result_role": "INTERBANK_DEPOSITS_AND_LOANS",
            }
        ]
    }
    gross["physical_page"] = 8
    gross["page_json_version_id"] = "gfpstorev1:json:" + "2" * 64
    selected = target._selected_ready_candidate([net, gross], compiled_specs=_compiled())
    assert selected is not None
    assert selected["physical_page"] == 7
    assert selected["closure_receipt"]["adjustment_coefficients"] == [-10, -10]
    assert [mapping["role"] for mapping in selected["mappings"]] == [
        "INTERBANK_DEPOSITS_AND_LOANS",
        "DEMAND_DEPOSIT_VND",
        "TERM_DEPOSIT_VND",
    ]

    gross["mappings"][0]["values"][0]["coefficient"] += 1
    assert target._selected_ready_candidate([net, gross], compiled_specs=_compiled()) is None
