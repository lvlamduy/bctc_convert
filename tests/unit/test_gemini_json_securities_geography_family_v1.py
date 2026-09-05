from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest
from test_gemini_financial_page_store_v1 import _ingest
from test_gemini_json_rollforward_indexed_wiring_v1 import (
    _bind_sweep_to_authenticated_corpus,
)

from bctc_ai.evaluation.gemini_json_dual_axis_accounting_family_v1 import (
    evaluate_gemini_json_dual_axis_family_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from bctc_ai.storage.gemini_accounting_family_store_v1 import (
    GeminiAccountingFamilyStoreV1Error,
    ingest_gemini_accounting_family_sweep_v1,
    load_gemini_accounting_family_sweep_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (
    GeminiFinancialPageStoreV1Error,
    initialize_gemini_financial_page_store_v1,
    query_selected_dual_axis_family_regions_v1,
    validate_selected_dual_axis_family_candidate_replays_v1,
)

ROOT = Path(__file__).resolve().parents[2]


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_text(encoding="utf-8"))


def _specs() -> tuple[dict, dict, dict, dict]:
    topology = _json("tm-securities-geography-topology-v1.json")
    evaluation = _json("tm-securities-geography-evaluation-v1.json")
    schema = _json("tm-securities-geography-schema-binding-v1.json")
    return (
        topology,
        evaluation,
        schema,
        compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema),
    )


def _target_page(
    *,
    foreign: str | None = "-",
    include_total: bool = True,
    metric_alias: str = "Kinh doanh và đầu tư chứng khoán",
    transposed: bool = False,
) -> dict:
    if transposed:
        columns = [
            {"header_path_exact": ["Trong nước", "Triệu VND"], "value_kind": "MONEY"},
            {"header_path_exact": ["Nước ngoài", "Triệu VND"], "value_kind": "MONEY"},
        ]
        values = ["100", foreign]
        if include_total:
            columns.append({"header_path_exact": ["Tổng cộng", "Triệu VND"], "value_kind": "MONEY"})
            values.append("100")
        rows = [
            {
                "hierarchy_path_exact": [metric_alias],
                "label_exact": metric_alias,
                "row_kind": "ITEM",
                "values_exact": values,
            }
        ]
    else:
        columns = [
            {
                "header_path_exact": [metric_alias, "Triệu VND"],
                "value_kind": "MONEY",
            }
        ]
        rows = [
            {
                "hierarchy_path_exact": ["Trong nước"],
                "label_exact": "Trong nước",
                "row_kind": "ITEM",
                "values_exact": ["100"],
            },
            {
                "hierarchy_path_exact": ["Nước ngoài"],
                "label_exact": "Nước ngoài",
                "row_kind": "ITEM",
                "values_exact": [foreign],
            },
        ]
        if include_total:
            rows.append(
                {
                    "hierarchy_path_exact": [None],
                    "label_exact": "Tổng cộng",
                    "row_kind": "TOTAL",
                    "values_exact": ["100"],
                }
            )
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [
                    {
                        "columns": columns,
                        "continuation": "NONE",
                        "rows": rows,
                        "title_exact": "Tại ngày 31/12/2025",
                        "unit_exact": "Đơn vị: Triệu VND",
                    }
                ],
                "title_exact": "Phân tích theo khu vực địa lý",
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _empty_page() -> dict:
    page = _target_page()
    page["sections"][0]["title_exact"] = "Tài sản cố định"
    page["sections"][0]["tables"] = []
    return page


def _trial(document: dict, *, candidate: dict | None) -> dict:
    if candidate is None:
        status = NOT_OBSERVED
        reasons = []
        mappings = []
        selected_candidate_id = None
    else:
        status = candidate["status"]
        reasons = candidate["reasons"] if status == UNRESOLVED else []
        mappings = candidate["mappings"] if status == READY else []
        selected_candidate_id = candidate["candidate_id"] if status == READY else None
    return {
        "candidate_count": int(candidate is not None),
        "candidates": [] if candidate is None else [candidate],
        "document_ordinal": document["document_ordinal"],
        "mappings": mappings,
        "reasons": reasons,
        "selected_candidate_id": selected_candidate_id,
        "source_logical_name": document["source_logical_name"],
        "source_sha256": document["source_sha256"],
        "status": status,
    }


def _fixture(
    tmp_path: Path,
    *,
    asymmetric_period_blank: bool = False,
    blank_foreign: bool = False,
    metric_alias: str = "Kinh doanh và đầu tư chứng khoán",
    transposed: bool = False,
) -> dict:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    page = (
        _target_page(
            foreign=None,
            include_total=False,
            metric_alias=metric_alias,
            transposed=transposed,
        )
        if blank_foreign
        else _target_page(metric_alias=metric_alias, transposed=transposed)
    )
    target = _ingest(database, source_logical_name="a-report.pdf", page_json=page)
    page_by_version = {target["page_json_version_id"]: page}
    target_versions = [target["page_json_version_id"]]
    if asymmetric_period_blank:
        page["sections"][0]["tables"][0]["continuation"] = "CONTINUES_ON_NEXT_PAGE"
        comparative_page = _target_page(foreign=None, include_total=False)
        comparative_page["sections"][0]["tables"][0]["title_exact"] = "Tại ngày 31/12/2024"
        comparative = _ingest(
            database,
            physical_page=8,
            image_sha256="8" * 64,
            prompt_sha256="9" * 64,
            source_logical_name="a-report.pdf",
            page_json=comparative_page,
        )
        page_by_version[comparative["page_json_version_id"]] = comparative_page
        target_versions.append(comparative["page_json_version_id"])
    absent = _ingest(
        database,
        physical_page=1,
        image_sha256="1" * 64,
        prompt_sha256="2" * 64,
        source_logical_name="z-absent.pdf",
        source_sha256="3" * 64,
        page_json=_empty_page(),
    )
    selected = [*target_versions, absent["page_json_version_id"]]
    topology, evaluation, schema, compiled = _specs()
    policy = compiled["dual_axis_projection_policy"]
    queried = query_selected_dual_axis_family_regions_v1(
        database,
        selected_page_json_version_ids=selected,
        metric_aliases=policy["metric_aliases"],
        role_aliases={
            role: compiled["query_aliases_by_role"][role] for role in policy["projected_role_order"]
        },
        unit_aliases=policy["unit_aliases"],
    )
    assert "external_population_control" not in policy
    explicitly_disabled = query_selected_dual_axis_family_regions_v1(
        database,
        selected_page_json_version_ids=selected,
        metric_aliases=policy["metric_aliases"],
        role_aliases={
            role: compiled["query_aliases_by_role"][role]
            for role in policy["projected_role_order"]
        },
        unit_aliases=policy["unit_aliases"],
        external_population_control=None,
    )
    assert canonical_json_sha256_v1(queried) == canonical_json_sha256_v1(
        explicitly_disabled
    )
    regions = [
        region
        for region in queried["regions"]
        if region["source_logical_name"] == "a-report.pdf"
    ]
    candidate = evaluate_gemini_json_dual_axis_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_by_version,
        document_context=queried["document_context_by_source"]["a-report.pdf"],
        compiled_specs=compiled,
        query_receipt=queried["query_receipt"],
    )
    documents = [
        {
            "document_ordinal": 1,
            "source_logical_name": "a-report.pdf",
            "source_sha256": "b" * 64,
        },
        {
            "document_ordinal": 2,
            "source_logical_name": "z-absent.pdf",
            "source_sha256": "3" * 64,
        },
    ]
    trials = [_trial(documents[0], candidate=candidate), _trial(documents[1], candidate=None)]
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "4" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=trials,
    )
    return {
        "candidate": candidate,
        "compiled": compiled,
        "database": database,
        "page": page,
        "queried": queried,
        "selected": selected,
        "sweep": sweep,
        "target": target,
        "trials": trials,
    }


def _coherently_drift_candidate_receipt(sweep: dict) -> dict:
    attacked = copy.deepcopy(sweep)
    candidate = attacked["trials"][0]["candidates"][0]
    candidate["dual_axis_projection_receipt"]["parent_context"]["text_exact"] = (
        "coherently forged source context"
    )
    candidate["closure_receipt"]["dual_axis_projection"] = copy.deepcopy(
        candidate["dual_axis_projection_receipt"]
    )
    material = {key: value for key, value in attacked.items() if key != "sweep_id"}
    attacked["sweep_id"] = "gjfafsv1:sweep:" + canonical_json_sha256_v1(material)
    return attacked


def test_securities_geography_specs_bind_only_two_children_and_context_root() -> None:
    _topology, _evaluation, _schema, compiled = _specs()

    assert compiled["topology"]["family_id"] == "SECURITIES_GEOGRAPHY"
    assert compiled["schema"]["family_owner_report_norm_id"] == 1259
    assert compiled["schema"]["family_report_norm_id"] == 5759
    assert compiled["bindings"] == {"DOMESTIC": 5760, "FOREIGN": 5761}
    assert compiled["schema"]["family_root_mapping_policy"] == (
        "REQUIRE_HIERARCHICALLY_RESOLVED_CONTEXT_ONLY"
    )


@pytest.mark.parametrize(
    ("metric_alias", "transposed"),
    [
        ("Kinh doanh và đầu tư chứng khoán (Chênh lệch DN-DC)", False),
        ("Kinh doanh và đầu tư chứng khoán (Chênh lệch DN-DC)", True),
        ("Chứng khoán đầu tư", False),
        ("Chứng khoán đầu tư", True),
    ],
)
def test_declared_source_metric_variants_are_matched_without_punctuation_or_page_routing(
    tmp_path: Path,
    metric_alias: str,
    transposed: bool,
) -> None:
    fixture = _fixture(tmp_path, metric_alias=metric_alias, transposed=transposed)

    assert fixture["candidate"]["status"] == READY
    assert [mapping["role"] for mapping in fixture["candidate"]["mappings"]] == [
        "DOMESTIC",
        "FOREIGN",
    ]


def test_dual_axis_sqlite_candidate_replay_rejects_coherent_source_receipt_drift(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)

    assert fixture["sweep"]["metrics"] == {
        "document_count": 2,
        "mapping_count": 2,
        "not_observed_count": 1,
        "ready_count": 1,
        "unresolved_count": 0,
    }
    assert (
        validate_selected_dual_axis_family_candidate_replays_v1(
            fixture["database"],
            selected_page_json_version_ids=fixture["selected"],
            compiled_specs=fixture["compiled"],
            trials=fixture["sweep"]["trials"],
        )
        == fixture["sweep"]["trials"]
    )

    attacked = _coherently_drift_candidate_receipt(fixture["sweep"])
    assert validate_gemini_json_flat_family_sweep_v1(attacked) == attacked
    with pytest.raises(
        GeminiFinancialPageStoreV1Error,
        match="do not replay from canonical page JSON",
    ):
        validate_selected_dual_axis_family_candidate_replays_v1(
            fixture["database"],
            selected_page_json_version_ids=fixture["selected"],
            compiled_specs=fixture["compiled"],
            trials=attacked["trials"],
        )


def test_dual_axis_store_requires_authenticated_sqlite_candidate_replay(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    corpus_ref, sweep = _bind_sweep_to_authenticated_corpus(
        artifact_root=tmp_path,
        page_database=fixture["database"],
        selected_ids=fixture["selected"],
        sweep=fixture["sweep"],
    )
    source_snapshot = tmp_path / "source.sqlite3"
    shutil.copyfile(fixture["database"], source_snapshot)
    results = tmp_path / "results.sqlite3"
    stored = ingest_gemini_accounting_family_sweep_v1(
        results,
        sweep=sweep,
        corpus_index_ref=corpus_ref,
        implementation_refs=[{"path": "engine.py", "sha256": "5" * 64, "size_bytes": 1}],
        run_kind="EXPERIMENTAL",
        source_page_database=source_snapshot,
        selected_page_json_version_ids=fixture["selected"],
        corpus_artifact_root=tmp_path,
    )
    assert load_gemini_accounting_family_sweep_v1(results, stored["family_run_id"]) == sweep

    attacked = _coherently_drift_candidate_receipt(sweep)
    assert validate_gemini_json_flat_family_sweep_v1(attacked) == attacked
    with pytest.raises(
        GeminiAccountingFamilyStoreV1Error,
        match="query and candidates do not replay",
    ):
        ingest_gemini_accounting_family_sweep_v1(
            tmp_path / "attacked-results.sqlite3",
            sweep=attacked,
            corpus_index_ref=corpus_ref,
            implementation_refs=[{"path": "engine.py", "sha256": "5" * 64, "size_bytes": 1}],
            run_kind="EXPERIMENTAL",
            source_page_database=source_snapshot,
            selected_page_json_version_ids=fixture["selected"],
            corpus_artifact_root=tmp_path,
        )


def test_source_blank_omits_only_unproven_role_and_keeps_visible_mapping(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path, blank_foreign=True)
    candidate = fixture["candidate"]
    assert candidate["status"] == READY
    assert candidate["reasons"] == []
    assert [mapping["role"] for mapping in candidate["mappings"]] == ["DOMESTIC"]
    assert candidate["mappings"][0]["report_norm_id"] == 5760
    assert candidate["mappings"][0]["values"] == [
        {"coefficient": 100, "source_text": "100", "state": "RAW_SIGNED_INTEGER"}
    ]
    assert candidate["closure_receipt"]["equations"] == []
    assert candidate["closure_receipt"]["unmapped_source_blank_roles"] == ["FOREIGN"]
    foreign_receipt = candidate["dual_axis_projection_receipt"]["source_table_equations"][0][
        "role_cells"
    ][1]
    assert foreign_receipt["coefficient"] is None
    assert foreign_receipt["raw_value_exact"] is None
    assert foreign_receipt["value_disposition"] == "UNMAPPED_SOURCE_BLANK"
    assert fixture["sweep"]["metrics"] == {
        "document_count": 2,
        "mapping_count": 1,
        "not_observed_count": 1,
        "ready_count": 1,
        "unresolved_count": 0,
    }
    assert (
        validate_selected_dual_axis_family_candidate_replays_v1(
            fixture["database"],
            selected_page_json_version_ids=fixture["selected"],
            compiled_specs=fixture["compiled"],
            trials=fixture["sweep"]["trials"],
        )
        == fixture["sweep"]["trials"]
    )


def test_asymmetric_period_blank_mapping_replays_exactly_from_sqlite(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path, asymmetric_period_blank=True)
    candidate = fixture["candidate"]

    assert candidate["status"] == READY
    assert [mapping["role"] for mapping in candidate["mappings"]] == [
        "DOMESTIC",
        "FOREIGN",
    ]
    foreign = candidate["mappings"][1]
    assert foreign["values"] == [
        {"coefficient": 0, "source_text": "-", "state": "DASH_ZERO"},
        {"coefficient": None, "source_text": None, "state": "BLANK_SOURCE_CELL"},
    ]
    equations = candidate["dual_axis_projection_receipt"]["source_table_equations"]
    assert equations[1]["blank_zero_equations"] == []
    assert equations[1]["total_equation_residual"] is None
    assert candidate["closure_receipt"]["partially_blank_mapped_roles"] == ["FOREIGN"]
    assert candidate["closure_receipt"]["unmapped_source_blank_roles"] == []
    assert (
        validate_selected_dual_axis_family_candidate_replays_v1(
            fixture["database"],
            selected_page_json_version_ids=fixture["selected"],
            compiled_specs=fixture["compiled"],
            trials=fixture["sweep"]["trials"],
        )
        == fixture["sweep"]["trials"]
    )
