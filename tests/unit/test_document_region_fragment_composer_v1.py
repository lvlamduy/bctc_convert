from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.document_region_fragment_composer_v1 import (
    POLICY_FORMAT_VERSION,
    DocumentRegionFragmentComposerV1Error,
    compose_document_region_fragments_v1,
    inventory_column_lane_document_region_fragment_v1,
    project_column_lane_document_region_fragment_v1,
    validate_document_region_fragment_composition_replay_v1,
    validate_document_region_fragment_composition_store_replay_v1,
)
from bctc_ai.evaluation.gemini_json_first_provider_v1 import ProviderResultV1
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    READY,
    UNRESOLVED,
    compile_gemini_json_flat_family_specs_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from bctc_ai.storage.gemini_financial_page_store_v1 import (
    ingest_financial_page_extraction_v1,
    initialize_gemini_financial_page_store_v1,
    load_page_json_versions_v1,
)

ROOT = Path(__file__).resolve().parents[2]


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict:
    return compile_gemini_json_flat_family_specs_v1(
        _json("tm-loan-currency-classification-topology-v1.json"),
        _json("tm-loan-currency-classification-evaluation-v1.json"),
        _json("tm-loan-currency-classification-schema-binding-v1.json"),
    )


def _row(label: str | None, values: list[str | None], kind: str = "ITEM") -> dict:
    return {
        "hierarchy_path_exact": [label],
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _table(
    rows: list[dict],
    *,
    continuation: str = "NONE",
    periods: tuple[str, str] = ("31/12/2025", "31/12/2024"),
    unit: str = "Triệu đồng",
) -> dict:
    return {
        "columns": [
            {"header_path_exact": [period, unit], "value_kind": "MONEY"} for period in periods
        ],
        "continuation": continuation,
        "rows": rows,
        "title_exact": None,
        "unit_exact": unit,
    }


def _page(tables: list[dict], *, title: str | None = None) -> dict:
    return {
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": tables,
                "title_exact": title,
            }
        ]
    }


def _policy(**changes: object) -> dict:
    value = {
        "allow_distinctive_child_cluster_cross_page": False,
        "branch_aliases": [],
        "control_surface_aliases": [],
        "cross_page_policy": "LOCAL_OWNER_OR_BRANCH_OR_EXPLICIT_CONTINUATION",
        "distinctive_child_roles": ["VND_LOANS", "FOREIGN_CURRENCY_AND_GOLD_LOANS"],
        "duplicate_policy": ("EXACT_ROLE_PERIOD_UNIT_VALUE_CORROBORATE_OTHERWISE_UNRESOLVED"),
        "exhaustiveness_policy": ("ALL_ROLE_BEARING_MONEY_TABLES_IN_FENCED_SELECTED_PAGE_INTERVAL"),
        "family_id": "LOAN_CURRENCY_CLASSIFICATION",
        "format_version": POLICY_FORMAT_VERSION,
        "hard_negative_aliases": ["Phân tích rủi ro tiền tệ"],
        "maximum_components": 8,
        "maximum_page_span": 4,
        "minimum_distinctive_child_roles": 2,
        "owner_aliases": ["Theo loại tiền tệ"],
        "period_axis_cardinality": 2,
        "period_axis_semantics": "EXACT_DOCUMENT_ACCOUNTING_PERIOD_AXIS",
        "reset_aliases": ["Theo ngành kinh tế"],
        "unit_aliases": ["Triệu đồng", "Nghìn đồng"],
    }
    value.update(changes)
    return value


def _axis(document_id: str = "document-1") -> dict:
    receipt = {"reporting_period": "2025-12-31", "comparative_period": "2024-12-31"}
    return {
        "document_id": document_id,
        "family_id": "LOAN_CURRENCY_CLASSIFICATION",
        "format_version": "DOCUMENT_REGION_ACCOUNTING_PERIOD_AXIS_V1",
        "period_signatures": [["DATE", "2025-12-31"], ["DATE", "2024-12-31"]],
        "source_metadata_receipt": receipt,
        "source_metadata_receipt_sha256": canonical_json_sha256_v1(receipt),
        "source_sha256": "f" * 64,
    }


def _version(ordinal: int) -> str:
    return "gfpstorev1:json:" + format(ordinal, "064x")


def _records(pages: list[dict], document_id: str = "document-1") -> tuple[list[str], list[dict]]:
    version_ids = [_version(ordinal) for ordinal in range(1, len(pages) + 1)]
    return version_ids, [
        {
            "document_id": document_id,
            "page_json": page,
            "page_json_version_id": version_id,
            "physical_page": ordinal,
            "selected_frontier_ordinal": ordinal,
            "source_logical_name": "document.pdf",
            "source_sha256": "f" * 64,
        }
        for ordinal, (version_id, page) in enumerate(zip(version_ids, pages, strict=True), start=1)
    ]


def _request(version_id: str, table: int, columns: tuple[int, ...] = (1, 2)) -> dict:
    return {
        "control_column_ids": [],
        "mapping_column_ids": [f"c{column}" for column in columns],
        "page_json_version_id": version_id,
        "projection_kind": "BALANCE_MAPPING",
        "section_id": "s1",
        "table_id": f"t{table}",
    }


def _compose(pages: list[dict], requests: list[dict], **policy_changes: object) -> dict:
    version_ids, records = _records(pages)
    return compose_document_region_fragments_v1(
        selected_page_json_version_ids=version_ids,
        page_records=records,
        fragment_requests=requests,
        document_period_axis=_axis(),
        policy=_policy(**policy_changes),
        compiled_specs=_compiled(),
        projection_adapter=project_column_lane_document_region_fragment_v1,
        projection_inventory_adapter=inventory_column_lane_document_region_fragment_v1,
    )


def _basic_pages() -> tuple[list[dict], list[dict]]:
    pages = [
        _page([_table([_row("Cho vay bằng VND", ["60", "50"])])], title="Theo loại tiền tệ"),
        _page(
            [
                _table(
                    [
                        _row("Cho vay bằng ngoại tệ", ["40", "30"]),
                        _row(None, ["100", "80"], "TOTAL"),
                    ],
                    continuation="CONTINUES_FROM_PREVIOUS_PAGE",
                )
            ]
        ),
    ]
    ids, _ = _records(pages)
    return pages, [_request(ids[0], 1), _request(ids[1], 1)]


def test_disjoint_adjacent_fragments_recompute_existing_accounting_closure() -> None:
    pages, requests = _basic_pages()
    result = _compose(pages, requests)
    assert result["status"] == READY
    assert result["reasons"] == []
    assert {
        mapping["role"]: [value["coefficient"] for value in mapping["values"]]
        for mapping in result["mappings"]
    } == {"VND_LOANS": [60, 50], "FOREIGN_CURRENCY_AND_GOLD_LOANS": [40, 30]}
    assert all(
        value["document_region_fragment_source_cells"]
        for mapping in result["mappings"]
        for value in mapping["values"]
    )
    assert result["composition_receipt"]["final_closure_sha256"] == canonical_json_sha256_v1(
        result["closure_receipt"]
    )


def test_eight_fragments_across_four_contiguous_selected_pages_are_supported() -> None:
    pages = [
        _page(
            [
                _table([_row("Cho vay bằng VND", ["60", "50"])]),
                _table([_row("Cho vay bằng VND", ["60", "50"])]),
            ],
            title="Theo loại tiền tệ",
        ),
        _page(
            [
                _table(
                    [_row("Cho vay bằng VND", ["60", "50"])],
                    continuation="CONTINUES_FROM_PREVIOUS_PAGE",
                ),
                _table([_row("Cho vay bằng VND", ["60", "50"])]),
            ]
        ),
        _page(
            [
                _table(
                    [_row("Cho vay bằng ngoại tệ", ["40", "30"])],
                    continuation="CONTINUES_FROM_PREVIOUS_PAGE",
                ),
                _table([_row("Cho vay bằng ngoại tệ", ["40", "30"])]),
            ]
        ),
        _page(
            [
                _table(
                    [_row("Cho vay bằng ngoại tệ", ["40", "30"])],
                    continuation="CONTINUES_FROM_PREVIOUS_PAGE",
                ),
                _table([_row(None, ["100", "80"], "TOTAL")]),
            ]
        ),
    ]
    ids, _ = _records(pages)
    requests = [_request(version_id, table_index) for version_id in ids for table_index in (1, 2)]
    result = _compose(pages, requests)
    assert result["status"] == READY
    assert len(result["component_fragments"]) == 8
    assert len(result["composition_receipt"]["duplicate_corroborations"]) == 4
    assert len(result["composition_receipt"]["page_axis"]) == 4


def test_ninth_fragment_or_fifth_selected_page_is_rejected_by_declared_caps() -> None:
    table = _table([_row("Cho vay bằng VND", ["60", "50"])])
    page = _page([copy.deepcopy(table) for _ in range(9)], title="Theo loại tiền tệ")
    ids, _ = _records([page])
    with pytest.raises(DocumentRegionFragmentComposerV1Error, match="above the cap"):
        _compose([page], [_request(ids[0], index) for index in range(1, 10)])

    pages = [
        _page(
            [
                _table(
                    [_row("Cho vay bằng VND", ["60", "50"])],
                    continuation=("NONE" if ordinal == 1 else "CONTINUES_FROM_PREVIOUS_PAGE"),
                )
            ],
            title=("Theo loại tiền tệ" if ordinal == 1 else None),
        )
        for ordinal in range(1, 6)
    ]
    ids, _ = _records(pages)
    with pytest.raises(DocumentRegionFragmentComposerV1Error, match="exceeds the cap"):
        _compose(pages, [_request(version_id, 1) for version_id in ids])


def test_reset_hard_negative_and_unqualified_following_page_fail_closed() -> None:
    pages, requests = _basic_pages()
    hard_negative = copy.deepcopy(pages)
    hard_negative[1]["sections"][0]["title_exact"] = "Phân tích rủi ro tiền tệ"
    assert _compose(hard_negative, requests)["status"] == UNRESOLVED

    following = copy.deepcopy(pages)
    following[1]["sections"][0]["tables"][0]["continuation"] = "NONE"
    result = _compose(following, requests)
    assert result["status"] == UNRESOLVED
    assert any("CROSS_PAGE_FRAGMENT" in reason for reason in result["reasons"])


def test_duplicate_conflict_and_unit_or_period_mismatch_are_unresolved() -> None:
    pages = [
        _page(
            [
                _table([_row("Cho vay bằng VND", ["60", "50"])]),
                _table([_row("Cho vay bằng VND", ["61", "50"])]),
                _table(
                    [
                        _row("Cho vay bằng ngoại tệ", ["40", "30"]),
                        _row(None, ["100", "80"], "TOTAL"),
                    ]
                ),
            ],
            title="Theo loại tiền tệ",
        )
    ]
    ids, _ = _records(pages)
    result = _compose(pages, [_request(ids[0], index) for index in range(1, 4)])
    assert (
        "DUPLICATE_ROLE_PERIOD_UNIT_VALUE_CONFLICT:VND_LOANS:DATE/2025-12-31" in result["reasons"]
    )

    unit_pages, unit_requests = _basic_pages()
    unit_pages[1]["sections"][0]["tables"][0] = _table(
        [
            _row("Cho vay bằng ngoại tệ", ["40", "30"]),
            _row(None, ["100", "80"], "TOTAL"),
        ],
        continuation="CONTINUES_FROM_PREVIOUS_PAGE",
        unit="Nghìn đồng",
    )
    assert (
        "COMPOSED_MAPPING_UNIT_SIGNATURE_COUNT_NOT_ONE"
        in _compose(unit_pages, unit_requests)["reasons"]
    )

    period_pages, period_requests = _basic_pages()
    period_pages[1]["sections"][0]["tables"][0] = _table(
        [
            _row("Cho vay bằng ngoại tệ", ["40", "30"]),
            _row(None, ["100", "80"], "TOTAL"),
        ],
        continuation="CONTINUES_FROM_PREVIOUS_PAGE",
        periods=("31/12/2025", "31/12/2023"),
    )
    assert any(
        "MAPPING_COLUMN_PERIOD_IS_NOT_DECLARED" in reason
        for reason in _compose(period_pages, period_requests)["reasons"]
    )


def test_omitted_role_bearing_table_is_not_silently_ignored() -> None:
    pages = [
        _page(
            [
                _table([_row("Cho vay bằng VND", ["60", "50"])]),
                _table([_row("Cho vay bằng ngoại tệ", ["40", "30"])]),
                _table([_row(None, ["100", "80"], "TOTAL")]),
            ],
            title="Theo loại tiền tệ",
        )
    ]
    ids, _ = _records(pages)
    result = _compose(pages, [_request(ids[0], 1), _request(ids[0], 3)])
    assert result["status"] == UNRESOLVED
    assert any("UNCONSUMED_ROLE_BEARING" in reason for reason in result["reasons"])


def test_blank_structural_group_is_context_only_not_visible_zero_carrier() -> None:
    page = _page(
        [
            _table(
                [
                    _row("Cho vay khách hàng", [None, None], "GROUP"),
                    _row("Cho vay bằng VND", ["-", "-"]),
                    _row("Cho vay bằng ngoại tệ", ["-", "-"]),
                    _row(None, ["-", "-"], "TOTAL"),
                ]
            )
        ],
        title="Theo loại tiền tệ",
    )
    ids, _ = _records([page])
    result = _compose([page], [_request(ids[0], 1)])
    assert result["status"] == READY
    source_rows = {
        source["row_id"]
        for mapping in result["mappings"]
        for source in mapping["document_region_fragment_provenance"]["source_rows"]
    }
    assert "r1" not in source_rows
    assert {mapping["role"] for mapping in result["mappings"]} == {
        "VND_LOANS",
        "FOREIGN_CURRENCY_AND_GOLD_LOANS",
    }


def test_blank_additive_cell_is_unknown_not_zero() -> None:
    pages, requests = _basic_pages()
    pages[0]["sections"][0]["tables"][0]["rows"][0]["values_exact"][1] = None
    result = _compose(pages, requests)
    assert result["status"] == UNRESOLVED
    assert "MAPPED_ROLE_CELL_IS_BLANK_UNKNOWN:r1" in result["reasons"]


def test_identical_role_values_under_different_parent_contexts_are_not_deduplicated() -> None:
    page = _page(
        [
            _table(
                [
                    {
                        **_row("Cho vay bằng VND", ["60", "50"]),
                        "hierarchy_path_exact": ["Nhánh A", "Cho vay bằng VND"],
                    },
                    {
                        **_row("Cho vay bằng VND", ["60", "50"]),
                        "hierarchy_path_exact": ["Nhánh B", "Cho vay bằng VND"],
                    },
                    _row("Cho vay bằng ngoại tệ", ["40", "30"]),
                    _row(None, ["100", "80"], "TOTAL"),
                ]
            )
        ],
        title="Theo loại tiền tệ",
    )
    ids, _ = _records([page])
    result = _compose([page], [_request(ids[0], 1)])
    assert result["status"] == UNRESOLVED
    assert "COMPOSED_ACCOUNTING_CLOSURE_IS_NOT_READY" in result["reasons"]


def test_pure_replay_rejects_composition_receipt_or_source_tamper() -> None:
    pages, requests = _basic_pages()
    ids, records = _records(pages)
    kwargs = {
        "compiled_specs": _compiled(),
        "document_period_axis": _axis(),
        "fragment_requests": requests,
        "page_records": records,
        "policy": _policy(),
        "projection_adapter": project_column_lane_document_region_fragment_v1,
        "projection_inventory_adapter": inventory_column_lane_document_region_fragment_v1,
        "selected_page_json_version_ids": ids,
    }
    result = compose_document_region_fragments_v1(**kwargs)
    assert (
        validate_document_region_fragment_composition_replay_v1(**kwargs, composition=result)
        == result
    )
    tampered = copy.deepcopy(result)
    tampered["composition_receipt"]["ordered_region_axis_sha256"] = "0" * 64
    with pytest.raises(DocumentRegionFragmentComposerV1Error, match="does not replay"):
        validate_document_region_fragment_composition_replay_v1(**kwargs, composition=tampered)


def _store_page(page: dict) -> dict:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        **copy.deepcopy(page),
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _provider_result() -> ProviderResultV1:
    usage = {
        "billing_disposition": "ESTIMATED_LIST_PRICE",
        "cached_input_tokens": 0,
        "estimated_cost_usd": "0.001000000000",
        "input_tokens": 100,
        "output_tokens": 100,
        "thought_tokens": 0,
        "total_tokens": 200,
    }
    return ProviderResultV1(
        output_text="{}",
        raw_response_bytes=b'{"provider":"response"}',
        provider_name="GOOGLE_GEMINI_API",
        provider_model="gemini-3.7-flash-001",
        service_tier="flex",
        attempts=(
            {
                "attempt_ordinal": 1,
                "credential_slot": "TEST",
                "elapsed_seconds": "1.000",
                "http_status": 200,
                "outcome": "COMPLETED",
                "provider": "GOOGLE_GEMINI_API",
                "usage": usage,
            },
        ),
        usage=usage,
        response_id_sha256="a" * 64,
    )


def _store_ingest(path: Path, page: dict, ordinal: int) -> str:
    result = ingest_financial_page_extraction_v1(
        path,
        document={
            "source_logical_name": "document.pdf",
            "source_sha256": "f" * 64,
            "source_size_bytes": 123,
        },
        page={
            "image_sha256": format(ordinal, "064x"),
            "image_size_bytes": 456,
            "media_type": "image/png",
            "physical_page": ordinal,
            "pixel_height": 2339,
            "pixel_width": 1654,
            "render_dpi": 200,
        },
        prompt_variant="compact",
        output_contract_mode="JSON_SCHEMA",
        prompt_sha256=format(ordinal + 100, "064x"),
        response_schema_sha256="e" * 64,
        requested_model="gemini-3.7-flash",
        requested_service_tier="flex",
        thinking_level="low",
        provider_result=_provider_result(),
        page_json=_store_page(page),
    )
    return result["page_json_version_id"]


def test_public_store_replay_reloads_canonical_selected_json_and_rejects_tamper(
    tmp_path: Path,
) -> None:
    path = tmp_path / "store.sqlite3"
    initialize_gemini_financial_page_store_v1(path)
    pages, _ = _basic_pages()
    version_ids = [
        _store_ingest(path, page, ordinal) for ordinal, page in enumerate(pages, start=1)
    ]
    loaded = load_page_json_versions_v1(path, page_json_version_ids=version_ids)
    document_id = "drfcv1:document:" + canonical_json_sha256_v1(
        {"source_logical_name": "document.pdf", "source_sha256": "f" * 64}
    )
    records = [
        {
            "document_id": document_id,
            "page_json": record["page_json"],
            "page_json_version_id": record["page_json_version_id"],
            "physical_page": record["physical_page"],
            "selected_frontier_ordinal": ordinal,
            "source_logical_name": record["source_logical_name"],
            "source_sha256": record["source_sha256"],
        }
        for ordinal, record in enumerate(loaded, start=1)
    ]
    requests = [_request(version_ids[0], 1), _request(version_ids[1], 1)]
    kwargs = {
        "compiled_specs": _compiled(),
        "document_period_axis": _axis(document_id),
        "fragment_requests": requests,
        "policy": _policy(),
        "projection_adapter": project_column_lane_document_region_fragment_v1,
        "projection_inventory_adapter": inventory_column_lane_document_region_fragment_v1,
        "selected_page_json_version_ids": version_ids,
    }
    result = compose_document_region_fragments_v1(page_records=records, **kwargs)
    assert (
        validate_document_region_fragment_composition_store_replay_v1(
            path, **kwargs, composition=result
        )
        == result
    )
    tampered = copy.deepcopy(result)
    tampered["component_fragments"][0]["role_rows"][0]["cells"][0]["source_text"] = "61"
    with pytest.raises(DocumentRegionFragmentComposerV1Error, match="does not replay"):
        validate_document_region_fragment_composition_store_replay_v1(
            path, **kwargs, composition=tampered
        )
