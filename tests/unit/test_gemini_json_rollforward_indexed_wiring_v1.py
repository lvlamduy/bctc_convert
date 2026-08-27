from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest
from test_gemini_financial_page_store_v1 import _ingest
from test_gemini_json_rollforward_accounting_family_v1 import (
    _lane_page,
    _lane_table,
    _page,
    _period_table,
    _stacked_table,
)

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    GeminiJsonFlatAccountingFamilyV1Error,
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.evaluation.gemini_json_rollforward_accounting_family_v1 import (
    build_gemini_json_rollforward_region_query_receipt_v1,
    evaluate_gemini_json_rollforward_family_cluster_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.storage.gemini_accounting_family_store_v1 import (
    GeminiAccountingFamilyStoreV1Error,
    ingest_gemini_accounting_family_sweep_v1,
    load_gemini_accounting_family_sweep_v1,
)
from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import (
    build_current_corpus_manifest_index_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (
    GeminiFinancialPageStoreV1Error,
    initialize_gemini_financial_page_store_v1,
    query_selected_rollforward_family_regions_v1,
    validate_selected_rollforward_family_query_evidence_v1,
)

ROOT = Path(__file__).resolve().parents[2]


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_text(encoding="utf-8"))


def _specs() -> tuple[dict, dict, dict, dict]:
    topology = _json("tm-provision-movement-rollforward-topology-v1.json")
    evaluation = _json("tm-provision-movement-rollforward-evaluation-v1.json")
    schema = _json("tm-provision-movement-rollforward-schema-binding-v1.json")
    return (
        topology,
        evaluation,
        schema,
        compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema),
    )


def _engine_regions(indexed: dict) -> list[dict]:
    fields = (
        "document_id",
        "page_json_version_id",
        "physical_page",
        "section_id",
        "source_logical_name",
        "source_sha256",
        "table_id",
    )
    return [{field: region[field] for field in fields} for region in indexed["accepted_regions"]]


def _candidate_for_page(selected: dict, page_json: dict, indexed: dict, compiled: dict) -> dict:
    regions = _engine_regions(indexed)
    unit_context = next(
        item
        for item in indexed["document_unit_context_evidence"]
        if item["source_logical_name"] == regions[0]["source_logical_name"]
    )
    fiscal_context = next(
        item
        for item in indexed["document_fiscal_close_context_evidence"]
        if item["source_logical_name"] == regions[0]["source_logical_name"]
    )
    return evaluate_gemini_json_rollforward_family_cluster_v1(
        regions=regions,
        page_json_by_version={selected["page_json_version_id"]: page_json},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_rollforward_region_query_receipt_v1(regions),
        document_fiscal_close_context_evidence=fiscal_context,
        document_unit_context_evidence=unit_context,
    )


def _trial(
    *,
    ordinal: int,
    source: str,
    source_sha256: str,
    status: str,
    candidate: dict | None = None,
) -> dict:
    selected = candidate if candidate is not None and status == READY else None
    return {
        "candidate_count": int(candidate is not None),
        "candidates": [] if candidate is None else [candidate],
        "document_ordinal": ordinal,
        "mappings": [] if selected is None else selected["mappings"],
        "reasons": (
            []
            if status in {READY, NOT_OBSERVED}
            else (
                candidate["reasons"]
                if candidate is not None
                else ["PARTIAL_REQUIRED_ANCHOR_FRONTIER_ONLY"]
            )
        ),
        "selected_candidate_id": None if selected is None else selected["candidate_id"],
        "source_logical_name": source,
        "source_sha256": source_sha256,
        "status": status,
    }


def _reclose_rollforward_sweep(sweep: dict) -> None:
    candidate = sweep["trials"][0]["candidates"][0]
    for mapping in candidate["mappings"]:
        mapping_material = {
            key: value for key, value in mapping.items() if key != "item_mapping_id"
        }
        mapping["item_mapping_id"] = "gjfrfmv1:item:" + canonical_json_sha256_v1(mapping_material)
    candidate_material = {key: value for key, value in candidate.items() if key != "candidate_id"}
    candidate["candidate_id"] = "gjfafcv1:candidate:" + canonical_json_sha256_v1(candidate_material)
    trial = sweep["trials"][0]
    trial["mappings"] = deepcopy(candidate["mappings"])
    trial["selected_candidate_id"] = candidate["candidate_id"]
    sweep_material = {key: value for key, value in sweep.items() if key != "sweep_id"}
    sweep["sweep_id"] = "gjfafsv1:sweep:" + canonical_json_sha256_v1(sweep_material)


def _file_ref(path: Path, *, logical_path: str | None = None) -> dict:
    payload = path.read_bytes()
    return {
        "path": str(path.resolve()) if logical_path is None else logical_path,
        "sha256": sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _bind_sweep_to_authenticated_corpus(
    *,
    artifact_root: Path,
    page_database: Path,
    selected_ids: list[str],
    sweep: dict,
) -> tuple[dict, dict]:
    placeholders = ",".join("?" for _ in selected_ids)
    with sqlite3.connect(page_database) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            f"""
            SELECT j.page_json_version_id, j.page_status, p.physical_page,
                   d.source_logical_name, d.source_sha256, d.source_size_bytes
            FROM page_json_version AS j
            JOIN extraction_run AS r USING (extraction_run_id)
            JOIN page AS p USING (page_id)
            JOIN document AS d USING (document_id)
            WHERE j.page_json_version_id IN ({placeholders})
            """,
            selected_ids,
        ).fetchall()
    by_id = {row["page_json_version_id"]: row for row in rows}
    assert set(by_id) == set(selected_ids)
    grouped: dict[str, list[sqlite3.Row]] = {}
    for version_id in selected_ids:
        row = by_id[version_id]
        grouped.setdefault(row["source_logical_name"], []).append(row)

    documents = []
    for ordinal, source_name in enumerate(sorted(grouped), start=1):
        document_rows = grouped[source_name]
        assert [row["physical_page"] for row in document_rows] == sorted(
            {row["physical_page"] for row in document_rows}
        )
        pages = [
            {
                "page_json_version_id": row["page_json_version_id"],
                "physical_page": row["physical_page"],
            }
            for row in document_rows
        ]
        manifest_material = {
            "document": {
                "source_logical_name": source_name,
                "source_sha256": document_rows[0]["source_sha256"],
            },
            "format_version": "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_TEST_V1",
            "page_count": len(pages),
            "pages": pages,
        }
        manifest = {
            **manifest_material,
            "document_manifest_id": "gfdmv1:manifest:"
            + canonical_json_sha256_v1(manifest_material),
        }
        manifest_relative = f"documents/{ordinal}/manifest.json"
        manifest_path = artifact_root / manifest_relative
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_bytes(canonical_json_bytes_v1(manifest) + b"\n")
        status_counts = {
            "FINANCIAL_NOTE_CONTENT": 0,
            "MIXED_FINANCIAL_CONTENT": 0,
            "NO_RELEVANT_FINANCIAL_CONTENT": 0,
            "PRIMARY_FINANCIAL_STATEMENT": 0,
        }
        for row in document_rows:
            status_counts[row["page_status"]] += 1
        digit = format(ordinal, "x")[-1]
        documents.append(
            {
                "document_manifest_id": manifest["document_manifest_id"],
                "document_manifest_ref": _file_ref(manifest_path, logical_path=manifest_relative),
                "document_plan_id": "gjfpdocv1:" + digit * 64,
                "page_count": len(pages),
                "page_json_frontier_sha256": canonical_json_sha256_v1(pages),
                "page_status_counts": status_counts,
                "provider_counts": [
                    {
                        "count": len(pages),
                        "gateway": "TEST",
                        "selected_provider": "TEST",
                        "selected_service_tier": "TEST",
                    }
                ],
                "relative_path": source_name,
                "selection_id": "gjfcdmsv1:selection:" + digit * 64,
                "selection_ref": {
                    "path": f"documents/{ordinal}/selection.json",
                    "sha256": digit * 64,
                    "size_bytes": 1,
                },
                "source_ordinal": ordinal,
                "source_sha256": document_rows[0]["source_sha256"],
                "source_size_bytes": document_rows[0]["source_size_bytes"],
            }
        )
    database_relative = str(page_database.resolve().relative_to(artifact_root.resolve()))
    index = build_current_corpus_manifest_index_v1(
        corpus_plan_id="gjfpcorpusv1:" + "a" * 64,
        corpus_run_id="gjfpcrunv1:" + "b" * 64,
        corpus_plan_ref={"path": "plan.json", "sha256": "a" * 64, "size_bytes": 1},
        database_ref=_file_ref(page_database, logical_path=database_relative),
        ledger_ref={"path": "ledger.sqlite3", "sha256": "c" * 64, "size_bytes": 1},
        documents=documents,
        store_usage_summary={
            "attempts": [
                {
                    "count": len(selected_ids),
                    "credential_slot": "TEST",
                    "outcome": "COMPLETED",
                    "provider": "TEST",
                }
            ],
            "cached_input_tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "run_count": len(selected_ids),
            "thought_tokens": 0,
            "total_cost_usd": "0.000000000000",
        },
    )
    sweep["corpus_manifest_index_id"] = index["corpus_manifest_index_id"]
    sweep_material = {key: value for key, value in sweep.items() if key != "sweep_id"}
    sweep["sweep_id"] = "gjfafsv1:sweep:" + canonical_json_sha256_v1(sweep_material)
    index_path = (
        artifact_root
        / "current-corpus-manifest-indexes"
        / f"{index['corpus_manifest_index_id'].split(':')[-1]}.json"
    )
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_bytes(canonical_json_bytes_v1(index) + b"\n")
    return _file_ref(index_path), sweep


def _replace_string_recursive(value, *, old: str, new: str) -> None:
    if type(value) is dict:
        for key, item in value.items():
            if item == old:
                value[key] = new
            else:
                _replace_string_recursive(item, old=old, new=new)
    elif type(value) is list:
        for offset, item in enumerate(value):
            if item == old:
                value[offset] = new
            else:
                _replace_string_recursive(item, old=old, new=new)


def _inherited_unit_sweep(tmp_path: Path) -> tuple[Path, list[str], dict, dict]:
    database = tmp_path / "unit-pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    target_page = _page(
        _period_table("31/12/2025", unit=None),
        _period_table("31/12/2024", unit=None),
    )
    target = _ingest(database, page_json=target_page)
    selected_ids = [target["page_json_version_id"]]
    for physical_page, image_sha256 in ((8, "8" * 64), (9, "9" * 64)):
        context_page = _page(_period_table("31/12/2025", unit="Triệu đồng"))
        context_page["sections"][0]["title_exact"] = "Chứng khoán đầu tư"
        context_page["sections"][0]["narratives_exact"] = ["Biến động chứng khoán đầu tư trong kỳ."]
        selected = _ingest(
            database,
            physical_page=physical_page,
            image_sha256=image_sha256,
            page_json=context_page,
        )
        selected_ids.append(selected["page_json_version_id"])
    topology, evaluation, schema, compiled = _specs()
    indexed = query_selected_rollforward_family_regions_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
    )
    assert len(indexed["accepted_regions"]) == 2
    context = indexed["document_unit_context_evidence"][0]
    assert context["status"] == "UNIQUE_AUTHENTICATED_DOCUMENT_MONEY_UNIT_CONSENSUS"
    assert context["canonical_unit"] == "MILLION_VND"
    assert {item["source_kind"] for item in context["evidence"]} == {"TABLE_UNIT"}
    candidate = evaluate_gemini_json_rollforward_family_cluster_v1(
        regions=_engine_regions(indexed),
        page_json_by_version={target["page_json_version_id"]: target_page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_rollforward_region_query_receipt_v1(
            _engine_regions(indexed)
        ),
        document_unit_context_evidence=context,
    )
    assert candidate["status"] == READY
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "3" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=[
            _trial(
                ordinal=1,
                source="report.pdf",
                source_sha256="b" * 64,
                status=READY,
                candidate=candidate,
            )
        ],
        indexed_query_evidence=indexed,
    )
    return database, selected_ids, compiled, sweep


def _inherited_fiscal_sweep(tmp_path: Path) -> tuple[Path, list[str], dict, dict]:
    database = tmp_path / "fiscal-pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    target_page = _page(
        _period_table("Năm tài chính 2025"),
        _period_table("Năm tài chính 2024"),
    )
    target = _ingest(database, page_json=target_page)
    selected_ids = [target["page_json_version_id"]]
    context_axis = (
        (8, "8" * 64, 2024),
        (9, "9" * 64, 2024),
        (10, "a" * 64, 2025),
        (11, "f" * 64, 2025),
    )
    for physical_page, image_sha256, year in context_axis:
        context_page = _page()
        context_page["sections"][0]["title_exact"] = (
            f"Báo cáo tài chính cho năm tài chính kết thúc ngày 31/12/{year}"
        )
        context_page["sections"][0]["narratives_exact"] = ["Thông tin báo cáo chung."]
        selected = _ingest(
            database,
            physical_page=physical_page,
            image_sha256=image_sha256,
            page_json=context_page,
        )
        selected_ids.append(selected["page_json_version_id"])
    topology, evaluation, schema, compiled = _specs()
    indexed = query_selected_rollforward_family_regions_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
    )
    assert len(indexed["accepted_regions"]) == 2
    fiscal_context = indexed["document_fiscal_close_context_evidence"][0]
    assert {item["year"] for item in fiscal_context["year_contexts"]} == {2024, 2025}
    assert all(
        item["status"] == "UNIQUE_AUTHENTICATED_DOCUMENT_FISCAL_CLOSE_CONSENSUS"
        for item in fiscal_context["year_contexts"]
    )
    regions = _engine_regions(indexed)
    candidate = evaluate_gemini_json_rollforward_family_cluster_v1(
        regions=regions,
        page_json_by_version={target["page_json_version_id"]: target_page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_rollforward_region_query_receipt_v1(regions),
        document_fiscal_close_context_evidence=fiscal_context,
        document_unit_context_evidence=indexed["document_unit_context_evidence"][0],
    )
    assert candidate["status"] == READY
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "4" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=[
            _trial(
                ordinal=1,
                source="report.pdf",
                source_sha256="b" * 64,
                status=READY,
                candidate=candidate,
            )
        ],
        indexed_query_evidence=indexed,
    )
    return database, selected_ids, compiled, sweep


@pytest.mark.parametrize(
    ("page_json", "layout_kind", "component_count"),
    [
        (_page(_stacked_table()), "STACKED_PERIOD_BLOCKS", 1),
        (
            _page(
                _period_table("Tại ngày 31 tháng 12 năm 2025"),
                _period_table("Tại ngày 31 tháng 12 năm 2024"),
            ),
            "PERIOD_TABLES_LANE_COLUMNS",
            2,
        ),
        (
            _lane_page(
                ["Dự phòng chung", "Dự phòng cụ thể"],
                _lane_table(),
                _lane_table(),
            ),
            "LANE_TABLES_PERIOD_COLUMNS",
            2,
        ),
    ],
)
def test_selected_rollforward_query_projects_each_layout_without_unselected_pages(
    tmp_path: Path,
    page_json: dict,
    layout_kind: str,
    component_count: int,
) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    selected = _ingest(database, page_json=page_json)
    unselected = _ingest(
        database,
        physical_page=8,
        image_sha256="1" * 64,
        page_json=page_json,
    )
    compiled = _specs()[3]

    indexed = query_selected_rollforward_family_regions_v1(
        database,
        selected_page_json_version_ids=[selected["page_json_version_id"]],
        compiled_specs=compiled,
    )

    assert len(indexed["accepted_regions"]) == component_count
    assert {region["layout_kind"] for region in indexed["accepted_regions"]} == {layout_kind}
    assert {region["page_json_version_id"] for region in indexed["accepted_regions"]} == {
        selected["page_json_version_id"]
    }
    assert unselected["page_json_version_id"] not in {
        disposition["page_json_version_id"] for disposition in indexed["candidate_dispositions"]
    }
    assert indexed["query_receipt"]["exact_region_count"] == component_count
    assert (
        validate_selected_rollforward_family_query_evidence_v1(
            database,
            selected_page_json_version_ids=[selected["page_json_version_id"]],
            compiled_specs=compiled,
            indexed_query_evidence=indexed,
        )
        == indexed
    )


def test_selected_rollforward_query_persists_typed_veto_and_rejects_hash_tamper(
    tmp_path: Path,
) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    page_json = _page(_stacked_table())
    page_json["sections"][0]["title_exact"] = "Thư tín dụng cho khách hàng"
    page_json["sections"][0]["narratives_exact"] = [
        "Dự phòng rủi ro cho vay khách hàng và thư tín dụng"
    ]
    selected = _ingest(database, page_json=page_json)
    compiled = _specs()[3]
    indexed = query_selected_rollforward_family_regions_v1(
        database,
        selected_page_json_version_ids=[selected["page_json_version_id"]],
        compiled_specs=compiled,
    )

    assert indexed["accepted_regions"] == []
    assert indexed["candidate_dispositions"][0]["disposition"] == ("RESET_OR_HARD_NEGATIVE_VETO")
    attacked = deepcopy(indexed)
    attacked["candidate_dispositions"][0]["row_axis_sha256"] = "f" * 64
    with pytest.raises(
        GeminiFinancialPageStoreV1Error,
        match="does not replay exactly",
    ):
        validate_selected_rollforward_family_query_evidence_v1(
            database,
            selected_page_json_version_ids=[selected["page_json_version_id"]],
            compiled_specs=compiled,
            indexed_query_evidence=attacked,
        )


def test_document_fiscal_context_extracts_only_the_governed_annual_date(
    tmp_path: Path,
) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    selected_ids = []
    target = _ingest(
        database,
        page_json=_page(
            _period_table("31/12/2025"),
            _period_table("31/12/2024"),
        ),
    )
    selected_ids.append(target["page_json_version_id"])
    annual_title = (
        "Báo cáo tài chính cho năm tài chính kết thúc ngày 31/12/2025 "
        "và cho giai đoạn từ ngày 01/10/2025 đến ngày 31/12/2025"
    )
    for physical_page, image_sha256 in ((8, "8" * 64), (9, "9" * 64)):
        context_page = _page(_period_table("31/12/2025"))
        context_page["sections"][0]["title_exact"] = annual_title
        context_page["sections"][0]["narratives_exact"] = ["Thông tin báo cáo chung."]
        selected = _ingest(
            database,
            physical_page=physical_page,
            image_sha256=image_sha256,
            page_json=context_page,
        )
        selected_ids.append(selected["page_json_version_id"])

    indexed = query_selected_rollforward_family_regions_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=_specs()[3],
    )
    fiscal_context = indexed["document_fiscal_close_context_evidence"][0]
    context_2025 = next(item for item in fiscal_context["year_contexts"] if item["year"] == 2025)

    assert context_2025["status"] == ("UNIQUE_AUTHENTICATED_DOCUMENT_FISCAL_CLOSE_CONSENSUS")
    assert (context_2025["month"], context_2025["day"]) == (12, 31)
    assert {item["date"] for item in context_2025["evidence"]} == {"2025-12-31"}
    assert len(context_2025["evidence"]) == 2


def test_rollforward_sweep_replays_and_store_dispatches_movement_roles(
    tmp_path: Path,
) -> None:
    page_database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(page_database)
    page_json = _page(_stacked_table())
    selected = _ingest(page_database, page_json=page_json)
    topology, evaluation, schema, compiled = _specs()
    indexed = query_selected_rollforward_family_regions_v1(
        page_database,
        selected_page_json_version_ids=[selected["page_json_version_id"]],
        compiled_specs=compiled,
    )
    regions = _engine_regions(indexed)
    candidate = evaluate_gemini_json_rollforward_family_cluster_v1(
        regions=regions,
        page_json_by_version={selected["page_json_version_id"]: page_json},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_rollforward_region_query_receipt_v1(regions),
    )
    assert candidate["status"] == READY
    assert candidate["mappings"]
    assert all(
        "movement_role" in mapping and "role" not in mapping for mapping in candidate["mappings"]
    )
    trial = {
        "candidate_count": 1,
        "candidates": [candidate],
        "document_ordinal": 1,
        "mappings": candidate["mappings"],
        "reasons": [],
        "selected_candidate_id": candidate["candidate_id"],
        "source_logical_name": "report.pdf",
        "source_sha256": "b" * 64,
        "status": READY,
    }
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "3" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=[trial],
        indexed_query_evidence=indexed,
    )
    assert validate_gemini_json_flat_family_sweep_v1(sweep) == sweep
    corpus_ref, sweep = _bind_sweep_to_authenticated_corpus(
        artifact_root=tmp_path,
        page_database=page_database,
        selected_ids=[selected["page_json_version_id"]],
        sweep=sweep,
    )

    family_database = tmp_path / "families.sqlite3"
    stored = ingest_gemini_accounting_family_sweep_v1(
        family_database,
        sweep=sweep,
        corpus_index_ref=corpus_ref,
        implementation_refs=[{"path": "engine.py", "sha256": "5" * 64, "size_bytes": 1}],
        run_kind="EXPERIMENTAL",
        source_page_database=page_database,
        selected_page_json_version_ids=[selected["page_json_version_id"]],
        corpus_artifact_root=tmp_path,
    )
    assert load_gemini_accounting_family_sweep_v1(family_database, stored["family_run_id"]) == sweep
    with sqlite3.connect(family_database) as connection:
        roles = {row[0] for row in connection.execute("SELECT role FROM family_mapping").fetchall()}
    assert roles == {mapping["movement_role"] for mapping in candidate["mappings"]}


def test_sqlite_replay_and_store_reject_coherently_rehashed_mapping_values(
    tmp_path: Path,
) -> None:
    page_database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(page_database)
    page_json = _page(_stacked_table())
    selected = _ingest(page_database, page_json=page_json)
    topology, evaluation, schema, compiled = _specs()
    indexed = query_selected_rollforward_family_regions_v1(
        page_database,
        selected_page_json_version_ids=[selected["page_json_version_id"]],
        compiled_specs=compiled,
    )
    candidate = _candidate_for_page(selected, page_json, indexed, compiled)
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "3" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=[
            _trial(
                ordinal=1,
                source="report.pdf",
                source_sha256="b" * 64,
                status=READY,
                candidate=candidate,
            )
        ],
        indexed_query_evidence=indexed,
    )
    corpus_ref, sweep = _bind_sweep_to_authenticated_corpus(
        artifact_root=tmp_path,
        page_database=page_database,
        selected_ids=[selected["page_json_version_id"]],
        sweep=sweep,
    )

    attacked = deepcopy(sweep)
    attacked_candidate = attacked["trials"][0]["candidates"][0]
    attacked_mapping = next(
        mapping for mapping in attacked_candidate["mappings"] if mapping["report_norm_id"] == 791
    )
    assert attacked_mapping["cell"]["coefficient"] == 110
    attacked_mapping["report_norm_id"] = 999999
    attacked_mapping["cell"]["coefficient"] = 123566
    mapping_material = {
        key: value for key, value in attacked_mapping.items() if key != "item_mapping_id"
    }
    attacked_mapping["item_mapping_id"] = "gjfrfmv1:item:" + canonical_json_sha256_v1(
        mapping_material
    )
    candidate_material = {
        key: value for key, value in attacked_candidate.items() if key != "candidate_id"
    }
    attacked_candidate["candidate_id"] = "gjfafcv1:candidate:" + canonical_json_sha256_v1(
        candidate_material
    )
    attacked_trial = attacked["trials"][0]
    attacked_trial["mappings"] = deepcopy(attacked_candidate["mappings"])
    attacked_trial["selected_candidate_id"] = attacked_candidate["candidate_id"]
    attacked_material = {key: value for key, value in attacked.items() if key != "sweep_id"}
    attacked["sweep_id"] = "gjfafsv1:sweep:" + canonical_json_sha256_v1(attacked_material)

    # Canonical role-vector projection seals the complete mapping axis before
    # the SQLite source-authenticity replay is reached.
    with pytest.raises(
        GeminiJsonFlatAccountingFamilyV1Error,
        match="mapping axis replay drifted",
    ):
        validate_gemini_json_flat_family_sweep_v1(attacked)
    with pytest.raises(
        GeminiFinancialPageStoreV1Error,
        match=(
            "candidate does not replay from SQLite|"
            "selected roll-forward sweep bindings do not replay exactly"
        ),
    ):
        validate_selected_rollforward_family_query_evidence_v1(
            page_database,
            selected_page_json_version_ids=[selected["page_json_version_id"]],
            compiled_specs=compiled,
            indexed_query_evidence=indexed,
            trials=attacked["trials"],
        )
    with pytest.raises(
        (GeminiAccountingFamilyStoreV1Error, GeminiJsonFlatAccountingFamilyV1Error),
        match=(
            "selected query and candidates do not replay from page store|"
            "mapping axis replay drifted"
        ),
    ):
        ingest_gemini_accounting_family_sweep_v1(
            tmp_path / "attacked-values.sqlite3",
            sweep=attacked,
            corpus_index_ref=corpus_ref,
            implementation_refs=[{"path": "engine.py", "sha256": "5" * 64, "size_bytes": 1}],
            run_kind="EXPERIMENTAL",
            source_page_database=page_database,
            selected_page_json_version_ids=[selected["page_json_version_id"]],
            corpus_artifact_root=tmp_path,
        )


def test_accepted_source_cannot_delete_its_candidate_and_downgrade_to_near_only(
    tmp_path: Path,
) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    page_json = _page(_stacked_table())
    selected = _ingest(database, page_json=page_json)
    topology, evaluation, schema, compiled = _specs()
    indexed = query_selected_rollforward_family_regions_v1(
        database,
        selected_page_json_version_ids=[selected["page_json_version_id"]],
        compiled_specs=compiled,
    )
    candidate = _candidate_for_page(selected, page_json, indexed, compiled)
    trial = _trial(
        ordinal=1,
        source="report.pdf",
        source_sha256="b" * 64,
        status=READY,
        candidate=candidate,
    )
    attacked_trial = deepcopy(trial)
    attacked_trial.update(
        {
            "candidate_count": 0,
            "candidates": [],
            "mappings": [],
            "reasons": ["PARTIAL_REQUIRED_ANCHOR_FRONTIER_ONLY"],
            "selected_candidate_id": None,
            "status": UNRESOLVED,
        }
    )
    with pytest.raises(
        GeminiJsonFlatAccountingFamilyV1Error,
        match="accepted source must have exactly one candidate",
    ):
        build_gemini_json_flat_family_sweep_v1(
            corpus_manifest_index_id="gjfccmiv1:index:" + "3" * 64,
            topology_spec=topology,
            evaluation_spec=evaluation,
            schema_binding_spec=schema,
            trials=[attacked_trial],
            indexed_query_evidence=indexed,
        )


def test_cross_document_ready_candidate_cannot_replace_a_near_only_trial(
    tmp_path: Path,
) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    near_page = _page(_stacked_table())
    near_page["sections"][0]["tables"][0]["rows"].pop()
    near = _ingest(
        database,
        source_logical_name="a-near.pdf",
        source_sha256="a" * 64,
        image_sha256="1" * 64,
        page_json=near_page,
    )
    ready_page = _page(_stacked_table())
    ready = _ingest(
        database,
        source_logical_name="b-ready.pdf",
        source_sha256="b" * 64,
        image_sha256="2" * 64,
        page_json=ready_page,
    )
    topology, evaluation, schema, compiled = _specs()
    indexed = query_selected_rollforward_family_regions_v1(
        database,
        selected_page_json_version_ids=[
            near["page_json_version_id"],
            ready["page_json_version_id"],
        ],
        compiled_specs=compiled,
    )
    assert len(indexed["accepted_regions"]) == 1
    assert indexed["accepted_regions"][0]["source_logical_name"] == "b-ready.pdf"
    assert "a-near.pdf" in {
        disposition["source_logical_name"]
        for disposition in indexed["candidate_dispositions"]
        if type(disposition["classification"]) is dict
        and disposition["classification"]["local_owner_visible"]
    }
    ready_candidate = _candidate_for_page(ready, ready_page, indexed, compiled)
    assert ready_candidate["status"] == READY
    valid_trials = [
        _trial(
            ordinal=1,
            source="a-near.pdf",
            source_sha256="a" * 64,
            status=UNRESOLVED,
        ),
        _trial(
            ordinal=2,
            source="b-ready.pdf",
            source_sha256="b" * 64,
            status=READY,
            candidate=ready_candidate,
        ),
    ]
    valid = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "3" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=valid_trials,
        indexed_query_evidence=indexed,
    )
    assert validate_gemini_json_flat_family_sweep_v1(valid) == valid

    attacked = deepcopy(valid)
    attacked["trials"][0] = _trial(
        ordinal=1,
        source="a-near.pdf",
        source_sha256="a" * 64,
        status=READY,
        candidate=deepcopy(ready_candidate),
    )
    attacked["metrics"] = {
        "document_count": 2,
        "mapping_count": len(ready_candidate["mappings"]) * 2,
        "not_observed_count": 0,
        "ready_count": 2,
        "unresolved_count": 0,
    }
    attacked_material = {key: value for key, value in attacked.items() if key != "sweep_id"}
    attacked["sweep_id"] = "gjfafsv1:sweep:" + canonical_json_sha256_v1(attacked_material)
    with pytest.raises(
        GeminiJsonFlatAccountingFamilyV1Error,
        match="not query-evidence bound",
    ):
        validate_gemini_json_flat_family_sweep_v1(attacked)
    with pytest.raises(
        GeminiFinancialPageStoreV1Error,
        match="sweep bindings do not replay exactly",
    ):
        validate_selected_rollforward_family_query_evidence_v1(
            database,
            selected_page_json_version_ids=[
                near["page_json_version_id"],
                ready["page_json_version_id"],
            ],
            compiled_specs=compiled,
            indexed_query_evidence=indexed,
            trials=attacked["trials"],
        )
    with pytest.raises(GeminiJsonFlatAccountingFamilyV1Error):
        ingest_gemini_accounting_family_sweep_v1(
            tmp_path / "attacked.sqlite3",
            sweep=attacked,
            corpus_index_ref={
                "path": "index.json",
                "sha256": "4" * 64,
                "size_bytes": 1,
            },
            implementation_refs=[{"path": "engine.py", "sha256": "5" * 64, "size_bytes": 1}],
            run_kind="EXPERIMENTAL",
            source_page_database=database,
            selected_page_json_version_ids=[
                near["page_json_version_id"],
                ready["page_json_version_id"],
            ],
        )


def test_empty_selected_query_cannot_admit_a_foreign_ready_candidate(
    tmp_path: Path,
) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    empty_page = {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [],
        "status": "NO_RELEVANT_FINANCIAL_CONTENT",
    }
    empty = _ingest(
        database,
        source_logical_name="a-empty.pdf",
        source_sha256="a" * 64,
        image_sha256="1" * 64,
        page_json=empty_page,
    )
    ready_page = _page(_stacked_table())
    ready = _ingest(
        database,
        source_logical_name="z-foreign.pdf",
        source_sha256="f" * 64,
        image_sha256="2" * 64,
        page_json=ready_page,
    )
    topology, evaluation, schema, compiled = _specs()
    empty_evidence = query_selected_rollforward_family_regions_v1(
        database,
        selected_page_json_version_ids=[empty["page_json_version_id"]],
        compiled_specs=compiled,
    )
    assert empty_evidence["candidate_dispositions"] == []
    assert empty_evidence["accepted_regions"] == []
    assert empty_evidence["selected_document_axis"][0]["source_logical_name"] == "a-empty.pdf"
    foreign_evidence = query_selected_rollforward_family_regions_v1(
        database,
        selected_page_json_version_ids=[ready["page_json_version_id"]],
        compiled_specs=compiled,
    )
    foreign_candidate = _candidate_for_page(ready, ready_page, foreign_evidence, compiled)
    attacked_trials = [
        _trial(
            ordinal=1,
            source="a-empty.pdf",
            source_sha256="a" * 64,
            status=READY,
            candidate=foreign_candidate,
        )
    ]
    with pytest.raises(
        GeminiJsonFlatAccountingFamilyV1Error,
        match="not query-evidence bound",
    ):
        build_gemini_json_flat_family_sweep_v1(
            corpus_manifest_index_id="gjfccmiv1:index:" + "3" * 64,
            topology_spec=topology,
            evaluation_spec=evaluation,
            schema_binding_spec=schema,
            trials=attacked_trials,
            indexed_query_evidence=empty_evidence,
        )
    with pytest.raises(
        GeminiFinancialPageStoreV1Error,
        match="sweep bindings do not replay exactly",
    ):
        validate_selected_rollforward_family_query_evidence_v1(
            database,
            selected_page_json_version_ids=[empty["page_json_version_id"]],
            compiled_specs=compiled,
            indexed_query_evidence=empty_evidence,
            trials=attacked_trials,
        )


def test_near_only_and_empty_source_dispositions_are_exactly_bound(tmp_path: Path) -> None:
    database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(database)
    near_page = _page(_stacked_table())
    near_page["sections"][0]["tables"][0]["rows"].pop()
    near = _ingest(
        database,
        source_logical_name="a-near.pdf",
        source_sha256="a" * 64,
        image_sha256="1" * 64,
        page_json=near_page,
    )
    empty_page = {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [],
        "status": "NO_RELEVANT_FINANCIAL_CONTENT",
    }
    empty = _ingest(
        database,
        source_logical_name="b-empty.pdf",
        source_sha256="b" * 64,
        image_sha256="2" * 64,
        page_json=empty_page,
    )
    topology, evaluation, schema, compiled = _specs()
    indexed = query_selected_rollforward_family_regions_v1(
        database,
        selected_page_json_version_ids=[
            near["page_json_version_id"],
            empty["page_json_version_id"],
        ],
        compiled_specs=compiled,
    )
    trials = [
        _trial(
            ordinal=1,
            source="a-near.pdf",
            source_sha256="a" * 64,
            status=UNRESOLVED,
        ),
        _trial(
            ordinal=2,
            source="b-empty.pdf",
            source_sha256="b" * 64,
            status=NOT_OBSERVED,
        ),
    ]
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "3" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=trials,
        indexed_query_evidence=indexed,
    )
    assert sweep["metrics"] == {
        "document_count": 2,
        "mapping_count": 0,
        "not_observed_count": 1,
        "ready_count": 0,
        "unresolved_count": 1,
    }
    attacked = deepcopy(trials)
    attacked[0]["status"] = NOT_OBSERVED
    attacked[0]["reasons"] = []
    with pytest.raises(
        GeminiJsonFlatAccountingFamilyV1Error,
        match="near-only trial binding drifted",
    ):
        build_gemini_json_flat_family_sweep_v1(
            corpus_manifest_index_id="gjfccmiv1:index:" + "3" * 64,
            topology_spec=topology,
            evaluation_spec=evaluation,
            schema_binding_spec=schema,
            trials=attacked,
            indexed_query_evidence=indexed,
        )


def test_flat_rejects_candidate_only_document_unit_context_scale_mutation(
    tmp_path: Path,
) -> None:
    _database, _selected_ids, _compiled, sweep = _inherited_unit_sweep(tmp_path)
    attacked = deepcopy(sweep)
    candidate_context = attacked["trials"][0]["candidates"][0]["closure_receipt"][
        "unit_provenance_receipt"
    ]["document_unit_context_evidence"]
    candidate_context["canonical_unit"] = "BILLION_VND"
    candidate_context["canonical_units"] = ["BILLION_VND"]
    _reclose_rollforward_sweep(attacked)
    with pytest.raises(
        GeminiJsonFlatAccountingFamilyV1Error,
        match="inherited unit provenance",
    ):
        validate_gemini_json_flat_family_sweep_v1(attacked)


def test_flat_rejects_candidate_only_fiscal_year_context_swap(tmp_path: Path) -> None:
    _database, _selected_ids, _compiled, sweep = _inherited_fiscal_sweep(tmp_path)
    attacked = deepcopy(sweep)
    candidate = attacked["trials"][0]["candidates"][0]
    embedded_receipts = [
        vector["period_semantics_evidence"]["document_fiscal_close_year_binding_receipt"]
        for vector in candidate["closure_receipt"]["role_vectors"]
        if vector["period_role"] == "COMPARATIVE_PERIOD"
    ]
    assert embedded_receipts and all(receipt is not None for receipt in embedded_receipts)
    for receipt in embedded_receipts:
        receipt["document_ordinal"] = 2
    _reclose_rollforward_sweep(attacked)

    with pytest.raises(
        GeminiJsonFlatAccountingFamilyV1Error,
        match="fiscal year binding drifted",
    ):
        validate_gemini_json_flat_family_sweep_v1(attacked)


def test_flat_rejects_fiscal_receipt_drift_in_endpoint_and_mapping_copies(
    tmp_path: Path,
) -> None:
    _database, _selected_ids, _compiled, sweep = _inherited_fiscal_sweep(tmp_path)

    endpoint_attack = deepcopy(sweep)
    endpoint_candidate = endpoint_attack["trials"][0]["candidates"][0]
    endpoint_receipt = endpoint_candidate["closure_receipt"]["endpoint_continuity_receipts"][0][
        "previous_opening"
    ]["period_semantics_evidence"]["document_fiscal_close_year_binding_receipt"]
    assert endpoint_receipt is not None
    endpoint_receipt["document_ordinal"] += 1000
    _reclose_rollforward_sweep(endpoint_attack)
    with pytest.raises(
        GeminiJsonFlatAccountingFamilyV1Error,
        match=(
            "fiscal year binding drifted|endpoint period evidence drifted|"
            "endpoint continuity replay drifted"
        ),
    ):
        validate_gemini_json_flat_family_sweep_v1(endpoint_attack)

    endpoint_cell_attack = deepcopy(sweep)
    endpoint_cell_attack["trials"][0]["candidates"][0]["closure_receipt"][
        "endpoint_continuity_receipts"
    ][0]["previous_opening"]["cell"]["coefficient"] += 777
    _reclose_rollforward_sweep(endpoint_cell_attack)
    with pytest.raises(
        GeminiJsonFlatAccountingFamilyV1Error,
        match="endpoint continuity replay drifted",
    ):
        validate_gemini_json_flat_family_sweep_v1(endpoint_cell_attack)

    mapping_attack = deepcopy(sweep)
    mapping_candidate = mapping_attack["trials"][0]["candidates"][0]
    comparative_mapping = next(
        mapping
        for mapping in mapping_candidate["mappings"]
        if mapping["period_semantics_evidence"]["document_fiscal_close_year_binding_receipt"]
        is not None
    )
    mapping_receipt = comparative_mapping["period_semantics_evidence"][
        "document_fiscal_close_year_binding_receipt"
    ]
    assert mapping_receipt is not None
    mapping_receipt["document_ordinal"] += 1000
    _reclose_rollforward_sweep(mapping_attack)
    with pytest.raises(
        GeminiJsonFlatAccountingFamilyV1Error,
        match="mapping axis replay drifted|mapping is not component bound",
    ):
        validate_gemini_json_flat_family_sweep_v1(mapping_attack)


def test_flat_exact_binds_component_classification_and_orientation_to_index(
    tmp_path: Path,
) -> None:
    _database, _selected_ids, _compiled, sweep = _inherited_fiscal_sweep(tmp_path)

    for field, forged_value in (
        ("context_reset_visible", True),
        ("local_owner_visible", False),
        ("structural_hard_negative_visible", True),
        (
            "continuation_evidence",
            [{"direction": "FROM_PREVIOUS_PAGE", "source_exact": "continued"}],
        ),
    ):
        attacked = deepcopy(sweep)
        attacked["trials"][0]["candidates"][0]["closure_receipt"]["component_classifications"][0][
            field
        ] = forged_value
        _reclose_rollforward_sweep(attacked)
        with pytest.raises(
            GeminiJsonFlatAccountingFamilyV1Error,
            match="component classification drifted from indexed evidence",
        ):
            validate_gemini_json_flat_family_sweep_v1(attacked)

    orientation_attack = deepcopy(sweep)
    orientation_attack["trials"][0]["candidates"][0]["closure_receipt"]["orientation"] = (
        "STACKED_PERIOD_BLOCKS"
    )
    _reclose_rollforward_sweep(orientation_attack)
    with pytest.raises(
        GeminiJsonFlatAccountingFamilyV1Error,
        match="orientation drifted from indexed evidence",
    ):
        validate_gemini_json_flat_family_sweep_v1(orientation_attack)


def test_flat_replays_equation_and_complete_mapping_axes_from_role_vectors(
    tmp_path: Path,
) -> None:
    _database, _selected_ids, _compiled, sweep = _inherited_fiscal_sweep(tmp_path)

    equation_attack = deepcopy(sweep)
    equation_attack["trials"][0]["candidates"][0]["closure_receipt"]["equations"][0]["status"] = (
        "MISMATCH"
    )
    _reclose_rollforward_sweep(equation_attack)
    with pytest.raises(
        GeminiJsonFlatAccountingFamilyV1Error,
        match="equation axis replay drifted",
    ):
        validate_gemini_json_flat_family_sweep_v1(equation_attack)

    mapping_attack = deepcopy(sweep)
    mapping_attack["trials"][0]["candidates"][0]["mappings"].pop()
    mapping_attack["metrics"]["mapping_count"] -= 1
    _reclose_rollforward_sweep(mapping_attack)
    with pytest.raises(
        GeminiJsonFlatAccountingFamilyV1Error,
        match="mapping axis replay drifted",
    ):
        validate_gemini_json_flat_family_sweep_v1(mapping_attack)


def test_official_ingest_rejects_coherently_rehashed_stale_unit_context_before_store_init(
    tmp_path: Path,
) -> None:
    database, selected_ids, _compiled, sweep = _inherited_unit_sweep(tmp_path)
    corpus_ref, sweep = _bind_sweep_to_authenticated_corpus(
        artifact_root=tmp_path,
        page_database=database,
        selected_ids=selected_ids,
        sweep=sweep,
    )
    attacked = deepcopy(sweep)
    indexed_context = attacked["indexed_query_evidence"]["document_unit_context_evidence"][0]
    stale_id = "gfpstorev1:json:" + "0" * 64
    indexed_context["evidence"][0]["page_json_version_id"] = stale_id
    indexed_context["evidence_axis_sha256"] = canonical_json_sha256_v1(indexed_context["evidence"])
    attacked["indexed_query_evidence"]["query_receipt"]["document_unit_context_axis_sha256"] = (
        canonical_json_sha256_v1(
            attacked["indexed_query_evidence"]["document_unit_context_evidence"]
        )
    )
    candidate = attacked["trials"][0]["candidates"][0]
    candidate["closure_receipt"]["unit_provenance_receipt"]["document_unit_context_evidence"] = (
        deepcopy(indexed_context)
    )
    _reclose_rollforward_sweep(attacked)
    assert validate_gemini_json_flat_family_sweep_v1(attacked) == attacked

    destination = tmp_path / "forged-official.sqlite3"
    with pytest.raises(
        GeminiAccountingFamilyStoreV1Error,
        match="selected query and candidates do not replay from page store",
    ):
        ingest_gemini_accounting_family_sweep_v1(
            destination,
            sweep=attacked,
            corpus_index_ref=corpus_ref,
            implementation_refs=[{"path": "engine.py", "sha256": "5" * 64, "size_bytes": 1}],
            run_kind="OFFICIAL",
            source_page_database=database,
            selected_page_json_version_ids=selected_ids,
            corpus_artifact_root=tmp_path,
        )
    assert not destination.exists()


def test_official_ingest_rejects_coherently_rehashed_stale_fiscal_context(
    tmp_path: Path,
) -> None:
    database, selected_ids, _compiled, sweep = _inherited_fiscal_sweep(tmp_path)
    corpus_ref, sweep = _bind_sweep_to_authenticated_corpus(
        artifact_root=tmp_path,
        page_database=database,
        selected_ids=selected_ids,
        sweep=sweep,
    )
    attacked = deepcopy(sweep)
    indexed_context = attacked["indexed_query_evidence"]["document_fiscal_close_context_evidence"][
        0
    ]
    year_context = indexed_context["year_contexts"][0]
    original_id = year_context["evidence"][0]["page_json_version_id"]
    stale_id = "gfpstorev1:json:" + "0" * 64
    year_context["evidence"][0]["page_json_version_id"] = stale_id
    year_context["evidence_axis_sha256"] = canonical_json_sha256_v1(year_context["evidence"])
    indexed_context["year_context_axis_sha256"] = canonical_json_sha256_v1(
        indexed_context["year_contexts"]
    )
    attacked["indexed_query_evidence"]["query_receipt"][
        "document_fiscal_close_context_axis_sha256"
    ] = canonical_json_sha256_v1(
        attacked["indexed_query_evidence"]["document_fiscal_close_context_evidence"]
    )
    candidate = attacked["trials"][0]["candidates"][0]
    _replace_string_recursive(candidate, old=original_id, new=stale_id)
    nested_axis = [candidate]
    while nested_axis:
        nested = nested_axis.pop()
        if type(nested) is dict:
            binding = nested.get("document_fiscal_close_year_binding_receipt")
            if binding is not None and binding["year_context"]["year"] == year_context["year"]:
                binding["year_context"] = deepcopy(year_context)
            nested_axis.extend(nested.values())
        elif type(nested) is list:
            nested_axis.extend(nested)
    _reclose_rollforward_sweep(attacked)
    assert validate_gemini_json_flat_family_sweep_v1(attacked) == attacked

    destination = tmp_path / "forged-fiscal-official.sqlite3"
    with pytest.raises(
        GeminiAccountingFamilyStoreV1Error,
        match="selected query and candidates do not replay from page store",
    ):
        ingest_gemini_accounting_family_sweep_v1(
            destination,
            sweep=attacked,
            corpus_index_ref=corpus_ref,
            implementation_refs=[{"path": "engine.py", "sha256": "5" * 64, "size_bytes": 1}],
            run_kind="OFFICIAL",
            source_page_database=database,
            selected_page_json_version_ids=selected_ids,
            corpus_artifact_root=tmp_path,
        )
    assert not destination.exists()


def test_db_replay_rejects_coherent_explicit_local_unit_scale_forge(
    tmp_path: Path,
) -> None:
    page_database = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(page_database)
    page_json = _page(_stacked_table())
    selected = _ingest(page_database, page_json=page_json)
    topology, evaluation, schema, compiled = _specs()
    selected_ids = [selected["page_json_version_id"]]
    indexed = query_selected_rollforward_family_regions_v1(
        page_database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
    )
    candidate = _candidate_for_page(selected, page_json, indexed, compiled)
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "3" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=[
            _trial(
                ordinal=1,
                source="report.pdf",
                source_sha256="b" * 64,
                status=READY,
                candidate=candidate,
            )
        ],
        indexed_query_evidence=indexed,
    )
    corpus_ref, sweep = _bind_sweep_to_authenticated_corpus(
        artifact_root=tmp_path,
        page_database=page_database,
        selected_ids=selected_ids,
        sweep=sweep,
    )
    attacked = deepcopy(sweep)
    _replace_string_recursive(
        attacked["trials"][0]["candidates"][0],
        old="MILLION_VND",
        new="BILLION_VND",
    )
    _reclose_rollforward_sweep(attacked)
    assert validate_gemini_json_flat_family_sweep_v1(attacked) == attacked
    with pytest.raises(
        GeminiAccountingFamilyStoreV1Error,
        match="selected query and candidates do not replay from page store",
    ):
        ingest_gemini_accounting_family_sweep_v1(
            tmp_path / "forged-local-unit.sqlite3",
            sweep=attacked,
            corpus_index_ref=corpus_ref,
            implementation_refs=[{"path": "engine.py", "sha256": "5" * 64, "size_bytes": 1}],
            run_kind="OFFICIAL",
            source_page_database=page_database,
            selected_page_json_version_ids=selected_ids,
            corpus_artifact_root=tmp_path,
        )


def test_official_ingest_authenticates_corpus_ref_before_store_init(tmp_path: Path) -> None:
    database, selected_ids, _compiled, sweep = _inherited_unit_sweep(tmp_path)
    corpus_ref, sweep = _bind_sweep_to_authenticated_corpus(
        artifact_root=tmp_path,
        page_database=database,
        selected_ids=selected_ids,
        sweep=sweep,
    )
    attacked_ref = {**corpus_ref, "sha256": "f" * 64}
    destination = tmp_path / "fake-index-official.sqlite3"

    with pytest.raises(
        GeminiAccountingFamilyStoreV1Error,
        match="content reference does not authenticate",
    ):
        ingest_gemini_accounting_family_sweep_v1(
            destination,
            sweep=sweep,
            corpus_index_ref=attacked_ref,
            implementation_refs=[{"path": "engine.py", "sha256": "5" * 64, "size_bytes": 1}],
            run_kind="OFFICIAL",
            source_page_database=database,
            selected_page_json_version_ids=selected_ids,
            corpus_artifact_root=tmp_path,
        )
    assert not destination.exists()


def test_official_ingest_rejects_an_alternate_valid_db_frontier_bound_sweep(
    tmp_path: Path,
) -> None:
    database, selected_ids, compiled, sweep = _inherited_unit_sweep(tmp_path)
    corpus_ref, sweep = _bind_sweep_to_authenticated_corpus(
        artifact_root=tmp_path,
        page_database=database,
        selected_ids=selected_ids,
        sweep=sweep,
    )
    alternate_ids = selected_ids[:-1]
    alternate_evidence = query_selected_rollforward_family_regions_v1(
        database,
        selected_page_json_version_ids=alternate_ids,
        compiled_specs=compiled,
    )
    alternate_context = alternate_evidence["document_unit_context_evidence"][0]
    target_page = _page(
        _period_table("31/12/2025", unit=None),
        _period_table("31/12/2024", unit=None),
    )
    alternate_candidate = evaluate_gemini_json_rollforward_family_cluster_v1(
        regions=_engine_regions(alternate_evidence),
        page_json_by_version={alternate_ids[0]: target_page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_rollforward_region_query_receipt_v1(
            _engine_regions(alternate_evidence)
        ),
        document_unit_context_evidence=alternate_context,
    )
    assert alternate_candidate["status"] == UNRESOLVED
    topology, evaluation, schema, _compiled = _specs()
    attacked = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id=sweep["corpus_manifest_index_id"],
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=[
            _trial(
                ordinal=1,
                source="report.pdf",
                source_sha256="b" * 64,
                status=UNRESOLVED,
                candidate=alternate_candidate,
            )
        ],
        indexed_query_evidence=alternate_evidence,
    )
    assert validate_gemini_json_flat_family_sweep_v1(attacked) == attacked
    destination = tmp_path / "alternate-frontier-official.sqlite3"

    with pytest.raises(
        GeminiAccountingFamilyStoreV1Error,
        match="caller page frontier differs from authenticated corpus authority",
    ):
        ingest_gemini_accounting_family_sweep_v1(
            destination,
            sweep=attacked,
            corpus_index_ref=corpus_ref,
            implementation_refs=[{"path": "engine.py", "sha256": "5" * 64, "size_bytes": 1}],
            run_kind="OFFICIAL",
            source_page_database=database,
            selected_page_json_version_ids=alternate_ids,
            corpus_artifact_root=tmp_path,
        )
    assert not destination.exists()
