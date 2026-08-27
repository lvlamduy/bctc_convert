from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.document_region_fragment_composer_v1 import (
    POLICY_FORMAT_VERSION,
    DocumentRegionFragmentComposerV1Error,
    build_normalized_document_region_fragment_candidate_v1,
    compile_document_region_fragment_composer_policy_v1,
    compose_document_region_fragments_v1,
    document_region_fragment_adapter_identity_v1,
    inventory_column_lane_document_region_fragment_v1,
    inventory_exact_axis_document_region_fragment_v1,
    project_column_lane_document_region_fragment_v1,
    project_exact_axis_document_region_fragment_v1,
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


def _policy(
    *,
    projection_adapter: object = project_column_lane_document_region_fragment_v1,
    projection_inventory_adapter: object = inventory_column_lane_document_region_fragment_v1,
    projection_adapter_id: str = "DOCUMENT_REGION_COLUMN_LANE_PROJECTION",
    projection_adapter_format_version: str = "DOCUMENT_REGION_COLUMN_LANE_ADAPTER_V1",
    projection_inventory_adapter_id: str = "DOCUMENT_REGION_COLUMN_LANE_INVENTORY",
    projection_inventory_adapter_format_version: str = ("DOCUMENT_REGION_COLUMN_LANE_INVENTORY_V1"),
    **changes: object,
) -> dict:
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
        "metric_projection_rules": [
            {
                "header_aliases": [],
                "metric_signature": "UNQUALIFIED_BALANCE_AMOUNT",
                "rule": "EXACT_MONEY_COLUMN_UNQUALIFIED",
                "source_value_kind": "MONEY",
            }
        ],
        "minimum_distinctive_child_roles": 2,
        "owner_aliases": ["Theo loại tiền tệ"],
        "period_axis_cardinality": 2,
        "period_axis_semantics": "EXACT_DOCUMENT_ACCOUNTING_PERIOD_AXIS",
        "projection_adapter_identity": document_region_fragment_adapter_identity_v1(
            projection_adapter,
            adapter_id=projection_adapter_id,
            adapter_format_version=projection_adapter_format_version,
        ),
        "projection_inventory_adapter_identity": document_region_fragment_adapter_identity_v1(
            projection_inventory_adapter,
            adapter_id=projection_inventory_adapter_id,
            adapter_format_version=projection_inventory_adapter_format_version,
        ),
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


def _request(
    version_id: str,
    table: int,
    columns: tuple[int, ...] = (1, 2),
    *,
    projection_adapter_id: str = "DOCUMENT_REGION_COLUMN_LANE_PROJECTION",
    projection_adapter_format_version: str = "DOCUMENT_REGION_COLUMN_LANE_ADAPTER_V1",
    projection_adapter: object = project_column_lane_document_region_fragment_v1,
    projection_inventory_adapter_id: str = "DOCUMENT_REGION_COLUMN_LANE_INVENTORY",
    projection_inventory_adapter_format_version: str = ("DOCUMENT_REGION_COLUMN_LANE_INVENTORY_V1"),
    projection_inventory_adapter: object = inventory_column_lane_document_region_fragment_v1,
) -> dict:
    policy = _policy(
        projection_adapter=projection_adapter,
        projection_inventory_adapter=projection_inventory_adapter,
        projection_adapter_id=projection_adapter_id,
        projection_adapter_format_version=projection_adapter_format_version,
        projection_inventory_adapter_id=projection_inventory_adapter_id,
        projection_inventory_adapter_format_version=projection_inventory_adapter_format_version,
    )
    return {
        "composer_policy_sha256": canonical_json_sha256_v1(policy),
        "control_column_ids": [],
        "mapping_column_ids": [f"c{column}" for column in columns],
        "page_json_version_id": version_id,
        "projection_adapter_format_version": projection_adapter_format_version,
        "projection_adapter_id": projection_adapter_id,
        "projection_adapter_implementation_ref_sha256": policy["projection_adapter_identity"][
            "implementation_ref_sha256"
        ],
        "projection_inventory_adapter_format_version": (
            projection_inventory_adapter_format_version
        ),
        "projection_inventory_adapter_id": projection_inventory_adapter_id,
        "projection_inventory_adapter_implementation_ref_sha256": policy[
            "projection_inventory_adapter_identity"
        ]["implementation_ref_sha256"],
        "projection_kind": "BALANCE_MAPPING",
        "section_id": "s1",
        "table_id": f"t{table}",
    }


def _compose(
    pages: list[dict],
    requests: list[dict],
    *,
    projection_adapter: object = project_column_lane_document_region_fragment_v1,
    projection_inventory_adapter: object = inventory_column_lane_document_region_fragment_v1,
    projection_adapter_id: str = "DOCUMENT_REGION_COLUMN_LANE_PROJECTION",
    projection_adapter_format_version: str = "DOCUMENT_REGION_COLUMN_LANE_ADAPTER_V1",
    projection_inventory_adapter_id: str = "DOCUMENT_REGION_COLUMN_LANE_INVENTORY",
    projection_inventory_adapter_format_version: str = ("DOCUMENT_REGION_COLUMN_LANE_INVENTORY_V1"),
    **policy_changes: object,
) -> dict:
    version_ids, records = _records(pages)
    return compose_document_region_fragments_v1(
        selected_page_json_version_ids=version_ids,
        page_records=records,
        fragment_requests=requests,
        document_period_axis=_axis(),
        policy=_policy(
            projection_adapter=projection_adapter,
            projection_inventory_adapter=projection_inventory_adapter,
            projection_adapter_id=projection_adapter_id,
            projection_adapter_format_version=projection_adapter_format_version,
            projection_inventory_adapter_id=projection_inventory_adapter_id,
            projection_inventory_adapter_format_version=(
                projection_inventory_adapter_format_version
            ),
            **policy_changes,
        ),
        compiled_specs=_compiled(),
        projection_adapter=projection_adapter,
        projection_inventory_adapter=projection_inventory_adapter,
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


GENERAL_ADAPTER_ID = "DOCUMENT_REGION_EXACT_AXIS_PROJECTION"
GENERAL_ADAPTER_VERSION = "DOCUMENT_REGION_EXACT_AXIS_ADAPTER_V1"
GENERAL_INVENTORY_ID = "DOCUMENT_REGION_EXACT_AXIS_INVENTORY"
GENERAL_INVENTORY_VERSION = "DOCUMENT_REGION_EXACT_AXIS_INVENTORY_V1"


def _coherent_period_swapping_column_adapter(**kwargs: object) -> dict:
    candidate = project_column_lane_document_region_fragment_v1(**kwargs)
    for field in ("role_rows", "anonymous_rows"):
        for row in candidate[field]:
            periods = [cell["period_signature"] for cell in row["cells"]]
            for cell, period in zip(row["cells"], reversed(periods), strict=True):
                cell["period_signature"] = period
    candidate["projection_closure"]["role_rows"] = copy.deepcopy(candidate["role_rows"])
    candidate["projection_closure"]["anonymous_rows"] = copy.deepcopy(candidate["anonymous_rows"])
    candidate["projection_closure_sha256"] = canonical_json_sha256_v1(
        candidate["projection_closure"]
    )
    policy = kwargs["policy"]
    candidate["candidate_id"] = "drfcv1:fragment:" + canonical_json_sha256_v1(
        {
            "family_id": policy["family_id"],
            "page_json_version_id": candidate["page_json_version_id"],
            "projection_closure_sha256": candidate["projection_closure_sha256"],
            "section_id": candidate["section_id"],
            "table_id": candidate["table_id"],
        }
    )
    return candidate


def _general_request(version_id: str, *, layout_kind: str) -> dict:
    policy = _policy(
        projection_adapter=_general_layout_projection_adapter,
        projection_inventory_adapter=_general_layout_inventory_adapter,
        projection_adapter_id=GENERAL_ADAPTER_ID,
        projection_adapter_format_version=GENERAL_ADAPTER_VERSION,
        projection_inventory_adapter_id=GENERAL_INVENTORY_ID,
        projection_inventory_adapter_format_version=GENERAL_INVENTORY_VERSION,
    )
    return {
        "composer_policy_sha256": canonical_json_sha256_v1(policy),
        "layout_kind": layout_kind,
        "page_json_version_id": version_id,
        "projection_adapter_format_version": GENERAL_ADAPTER_VERSION,
        "projection_adapter_id": GENERAL_ADAPTER_ID,
        "projection_adapter_implementation_ref_sha256": policy["projection_adapter_identity"][
            "implementation_ref_sha256"
        ],
        "projection_inventory_adapter_format_version": GENERAL_INVENTORY_VERSION,
        "projection_inventory_adapter_id": GENERAL_INVENTORY_ID,
        "projection_inventory_adapter_implementation_ref_sha256": policy[
            "projection_inventory_adapter_identity"
        ]["implementation_ref_sha256"],
        "projection_kind": "BALANCE_MAPPING",
        "section_id": "s1",
        "table_id": "t1",
    }


def _general_layout_inventory_adapter(
    *,
    page_record: dict,
    section_id: str,
    table_id: str,
    document_period_axis: dict,
    policy: dict,
    compiled_specs: dict,
) -> dict | None:
    del document_period_axis, compiled_specs
    section_index = int(section_id[1:]) - 1
    table_index = int(table_id[1:]) - 1
    table = page_record["page_json"]["sections"][section_index]["tables"][table_index]
    layout_kind = table.get("title_exact")
    if type(layout_kind) is not str or not layout_kind.startswith(("STACKED", "TRANSPOSED")):
        return None
    return {
        "composer_policy_sha256": policy["policy_sha256"],
        "layout_kind": layout_kind,
        "page_json_version_id": page_record["page_json_version_id"],
        "projection_adapter_format_version": policy["projection_adapter_identity"][
            "adapter_format_version"
        ],
        "projection_adapter_id": policy["projection_adapter_identity"]["adapter_id"],
        "projection_adapter_implementation_ref_sha256": policy["projection_adapter_identity"][
            "implementation_ref_sha256"
        ],
        "projection_inventory_adapter_format_version": policy[
            "projection_inventory_adapter_identity"
        ]["adapter_format_version"],
        "projection_inventory_adapter_id": policy["projection_inventory_adapter_identity"][
            "adapter_id"
        ],
        "projection_inventory_adapter_implementation_ref_sha256": policy[
            "projection_inventory_adapter_identity"
        ]["implementation_ref_sha256"],
        "projection_kind": "BALANCE_MAPPING",
        "section_id": section_id,
        "table_id": table_id,
    }


def _money_receipt(value: str | None) -> dict | None:
    if value is None:
        return None
    return {
        "coefficient": int(value.replace(",", "")),
        "source_text": value,
        "state": "RAW_SIGNED_INTEGER",
    }


def _general_layout_projection_adapter(
    *,
    page_record: dict,
    request: dict,
    document_period_axis: dict,
    policy: dict,
    compiled_specs: dict,
) -> dict:
    del document_period_axis
    table = page_record["page_json"]["sections"][0]["tables"][0]
    bindings: list[dict] = []

    def add(kind: str, **fields: object) -> str:
        binding_id = f"b{len(bindings) + 1}"
        bindings.append({"binding_id": binding_id, "binding_kind": kind, **fields})
        return binding_id

    unit_id = add("TABLE_UNIT", unit_exact=table["unit_exact"])
    logical_rows = []
    if request["layout_kind"].startswith("STACKED"):
        metric_id = add(
            "COLUMN",
            column_id="c1",
            header_path_exact=table["columns"][0]["header_path_exact"],
            value_kind="MONEY",
        )
        row_ids = {
            ordinal: add(
                "ROW",
                row_id=f"r{ordinal}",
                label_exact=row["label_exact"],
                hierarchy_path_exact=row["hierarchy_path_exact"],
                row_kind=row["row_kind"],
            )
            for ordinal, row in enumerate(table["rows"], start=1)
        }
        block_ids = {
            1: add("ROW_BLOCK", row_ids=["r1", "r2", "r3", "r4"]),
            2: add("ROW_BLOCK", row_ids=["r5", "r6", "r7", "r8"]),
        }
        value_ids = {
            ordinal: add(
                "VALUE_CELL",
                row_id=f"r{ordinal}",
                column_id="c1",
                source_text=table["rows"][ordinal - 1]["values_exact"][0],
            )
            for ordinal in (2, 3, 4, 6, 7, 8)
        }
        row_specs = [
            ("Cho vay bằng VND", "ITEM", {"VND_LOANS": "EXACT_NORMALIZED"}, 2, 6),
            (
                "Cho vay bằng ngoại tệ",
                "ITEM",
                {"FOREIGN_CURRENCY_AND_GOLD_LOANS": "EXACT_NORMALIZED"},
                3,
                7,
            ),
            ("Tổng cộng", "TOTAL", {}, 4, 8),
        ]
        for logical_ordinal, (label, row_kind, modes, current_row, prior_row) in enumerate(
            row_specs, start=1
        ):
            row_binding_ids = [row_ids[current_row], row_ids[prior_row]]
            source_path = table["rows"][current_row - 1]["hierarchy_path_exact"]
            population_context = list(source_path[:-1]) if source_path[-1] == label else []
            cells = []
            for cell_ordinal, (period, value_row, period_row, block) in enumerate(
                [
                    (["DATE", "2025-12-31"], current_row, 1, 1),
                    (["DATE", "2024-12-31"], prior_row, 5, 2),
                ],
                start=1,
            ):
                value = table["rows"][value_row - 1]["values_exact"][0]
                cells.append(
                    {
                        "logical_cell_id": f"lc{logical_ordinal}_{cell_ordinal}",
                        "metric_signature": "UNQUALIFIED_BALANCE_AMOUNT",
                        "metric_source_binding_ids": [metric_id],
                        "money": _money_receipt(value),
                        "period_signature": period,
                        "period_source_binding_ids": [row_ids[period_row], block_ids[block]],
                        "source_text": value,
                        "unit_signature": "trieu dong",
                        "unit_source_binding_ids": [unit_id],
                        "value_source_binding_ids": [value_ids[value_row]],
                    }
                )
            logical_rows.append(
                {
                    "cells": cells,
                    "hierarchy_path_exact": [*population_context, label],
                    "label_exact": label,
                    "label_match_modes": modes,
                    "logical_row_id": f"lr{logical_ordinal}",
                    "population_context_exact": population_context,
                    "population_source_binding_ids": (
                        row_binding_ids if population_context else []
                    ),
                    "role_source_binding_ids": row_binding_ids if modes else [],
                    "row_kind": row_kind,
                    "row_source_binding_ids": row_binding_ids,
                    "source_position": [
                        page_record["selected_frontier_ordinal"],
                        1,
                        1,
                        current_row,
                        1,
                    ],
                }
            )
    else:
        column_ids = {
            ordinal: add(
                "COLUMN",
                column_id=f"c{ordinal}",
                header_path_exact=column["header_path_exact"],
                value_kind=column["value_kind"],
            )
            for ordinal, column in enumerate(table["columns"], start=1)
        }
        row_ids = {
            ordinal: add(
                "ROW",
                row_id=f"r{ordinal}",
                label_exact=row["label_exact"],
                hierarchy_path_exact=row["hierarchy_path_exact"],
                row_kind=row["row_kind"],
            )
            for ordinal, row in enumerate(table["rows"], start=1)
        }
        value_ids = {
            (row_ordinal, column_ordinal): add(
                "VALUE_CELL",
                row_id=f"r{row_ordinal}",
                column_id=f"c{column_ordinal}",
                source_text=table["rows"][row_ordinal - 1]["values_exact"][column_ordinal - 1],
            )
            for row_ordinal in (1, 2)
            for column_ordinal in (1, 2, 3)
        }
        column_specs = [
            ("Cho vay bằng VND", "ITEM", {"VND_LOANS": "EXACT_NORMALIZED"}, 1),
            (
                "Cho vay bằng ngoại tệ",
                "ITEM",
                {"FOREIGN_CURRENCY_AND_GOLD_LOANS": "EXACT_NORMALIZED"},
                2,
            ),
            ("Tổng cộng", "TOTAL", {}, 3),
        ]
        for logical_ordinal, (label, row_kind, modes, column_ordinal) in enumerate(
            column_specs, start=1
        ):
            cells = []
            for row_ordinal, period in (
                (1, ["DATE", "2025-12-31"]),
                (2, ["DATE", "2024-12-31"]),
            ):
                value = table["rows"][row_ordinal - 1]["values_exact"][column_ordinal - 1]
                cells.append(
                    {
                        "logical_cell_id": f"lc{logical_ordinal}_{row_ordinal}",
                        "metric_signature": "UNQUALIFIED_BALANCE_AMOUNT",
                        "metric_source_binding_ids": [column_ids[column_ordinal]],
                        "money": _money_receipt(value),
                        "period_signature": period,
                        "period_source_binding_ids": [row_ids[row_ordinal]],
                        "source_text": value,
                        "unit_signature": "trieu dong",
                        "unit_source_binding_ids": [unit_id],
                        "value_source_binding_ids": [value_ids[(row_ordinal, column_ordinal)]],
                    }
                )
            logical_rows.append(
                {
                    "cells": cells,
                    "hierarchy_path_exact": [label],
                    "label_exact": label,
                    "label_match_modes": modes,
                    "logical_row_id": f"lr{logical_ordinal}",
                    "population_context_exact": [],
                    "population_source_binding_ids": [],
                    "role_source_binding_ids": [column_ids[column_ordinal]] if modes else [],
                    "row_kind": row_kind,
                    "row_source_binding_ids": [column_ids[column_ordinal]],
                    "source_position": [
                        page_record["selected_frontier_ordinal"],
                        1,
                        1,
                        1,
                        column_ordinal,
                    ],
                }
            )
    mutation = request["layout_kind"]
    if mutation.endswith("_FORGED_VALUE"):
        bindings[-1]["source_text"] = "999"
    elif mutation.endswith("_MISSING_REF"):
        logical_rows[0]["cells"][0]["value_source_binding_ids"] = ["b999"]
    elif mutation.endswith("_DUPLICATE_BINDING"):
        bindings.append(copy.deepcopy(bindings[0]))
    elif mutation.endswith("_UNUSED_BINDING"):
        add("SECTION_TITLE", title_exact=page_record["page_json"]["sections"][0]["title_exact"])
    elif mutation.endswith("_SWAPPED_PERIOD"):
        (
            logical_rows[0]["cells"][0]["period_signature"],
            logical_rows[0]["cells"][1]["period_signature"],
        ) = (
            logical_rows[0]["cells"][1]["period_signature"],
            logical_rows[0]["cells"][0]["period_signature"],
        )
    elif mutation.endswith("_FORGED_ROLE"):
        logical_rows[0]["label_match_modes"] = {
            "FOREIGN_CURRENCY_AND_GOLD_LOANS": "EXACT_NORMALIZED"
        }
    elif mutation.endswith("_STRIPPED_CONTEXT"):
        logical_rows[0]["hierarchy_path_exact"] = [logical_rows[0]["label_exact"]]
        logical_rows[0]["population_context_exact"] = []
        logical_rows[0]["population_source_binding_ids"] = []
    elif mutation.endswith("_SWAPPED_LOGICAL_ORDER"):
        logical_rows.reverse()
        for ordinal, row in enumerate(logical_rows, start=1):
            row["logical_row_id"] = f"lr{ordinal}"
    return build_normalized_document_region_fragment_candidate_v1(
        page_record=page_record,
        section_id=request["section_id"],
        table_id=request["table_id"],
        adapter_format_version=GENERAL_ADAPTER_VERSION,
        projection_kind=request["projection_kind"],
        source_bindings=bindings,
        logical_rows=logical_rows,
        adapter_projection_receipt={
            "layout_kind": request["layout_kind"],
            "rule": "TEST_LAYOUT_EXACT_AXIS_PROJECTION",
        },
        reasons=[],
        policy=policy,
        compiled_specs=compiled_specs,
    )


def _stacked_table(*, title: str = "STACKED") -> dict:
    return {
        "columns": [{"header_path_exact": ["Giá trị", "Triệu đồng"], "value_kind": "MONEY"}],
        "continuation": "NONE",
        "rows": [
            _row("31/12/2025", [None], "GROUP"),
            _row("Cho vay bằng VND", ["60"]),
            _row("Cho vay bằng ngoại tệ", ["40"]),
            _row("Tổng cộng", ["100"], "TOTAL"),
            _row("31/12/2024", [None], "GROUP"),
            _row("Cho vay bằng VND", ["50"]),
            _row("Cho vay bằng ngoại tệ", ["30"]),
            _row("Tổng cộng", ["80"], "TOTAL"),
        ],
        "title_exact": title,
        "unit_exact": "Triệu đồng",
    }


def _transposed_table(*, title: str = "TRANSPOSED") -> dict:
    return {
        "columns": [
            {"header_path_exact": [label, "Triệu đồng"], "value_kind": "MONEY"}
            for label in ("Cho vay bằng VND", "Cho vay bằng ngoại tệ", "Tổng cộng")
        ],
        "continuation": "NONE",
        "rows": [
            _row("31/12/2025", ["60", "40", "100"]),
            _row("31/12/2024", ["50", "30", "80"]),
        ],
        "title_exact": title,
        "unit_exact": "Triệu đồng",
    }


def _compose_general(table: dict, *, mutation: str | None = None) -> dict:
    pages = [_page([table], title="Theo loại tiền tệ")]
    ids, records = _records(pages)
    compiled_specs = _compiled()
    raw_policy = _policy(
        projection_adapter=project_exact_axis_document_region_fragment_v1,
        projection_inventory_adapter=inventory_exact_axis_document_region_fragment_v1,
        projection_adapter_id=GENERAL_ADAPTER_ID,
        projection_adapter_format_version=GENERAL_ADAPTER_VERSION,
        projection_inventory_adapter_id=GENERAL_INVENTORY_ID,
        projection_inventory_adapter_format_version=GENERAL_INVENTORY_VERSION,
    )
    compiled_policy = compile_document_region_fragment_composer_policy_v1(
        raw_policy, compiled_specs=compiled_specs
    )
    request = inventory_exact_axis_document_region_fragment_v1(
        page_record=records[0],
        section_id="s1",
        table_id="t1",
        document_period_axis=_axis(),
        policy=compiled_policy,
        compiled_specs=compiled_specs,
    )
    assert request is not None
    if mutation == "FORGED_VALUE":
        next(
            binding
            for binding in request["source_bindings"]
            if binding["binding_kind"] == "VALUE_CELL"
        )["source_text"] = "999"
    elif mutation == "MISSING_REF":
        request["logical_rows"][0]["cells"][0]["value_source_binding_ids"] = ["b999"]
    elif mutation == "DUPLICATE_BINDING":
        request["source_bindings"].append(copy.deepcopy(request["source_bindings"][0]))
    elif mutation == "UNUSED_BINDING":
        request["source_bindings"].append(
            {
                "binding_id": f"b{len(request['source_bindings']) + 1}",
                "binding_kind": "SECTION_TITLE",
                "title_exact": "Theo loại tiền tệ",
            }
        )
    elif mutation == "SWAPPED_PERIOD":
        cells = request["logical_rows"][0]["cells"]
        cells[0]["period_signature"], cells[1]["period_signature"] = (
            cells[1]["period_signature"],
            cells[0]["period_signature"],
        )
    elif mutation == "FORGED_ROLE":
        request["logical_rows"][0]["label_match_modes"] = {
            "FOREIGN_CURRENCY_AND_GOLD_LOANS": "EXACT_NORMALIZED"
        }
    elif mutation == "STRIPPED_CONTEXT":
        row = request["logical_rows"][0]
        row["hierarchy_path_exact"] = [row["label_exact"]]
        row["population_context_exact"] = []
        row["population_source_binding_ids"] = []
    elif mutation == "SWAPPED_LOGICAL_ORDER":
        request["logical_rows"].reverse()
        for ordinal, row in enumerate(request["logical_rows"], start=1):
            row["logical_row_id"] = f"lr{ordinal}"
    elif mutation == "FORGED_METRIC":
        request["logical_rows"][0]["cells"][0]["metric_signature"] = "FORGED_METRIC"
    elif mutation == "FORGED_ROW_KIND":
        request["logical_rows"][0]["row_kind"] = "TOTAL"
    elif mutation == "HIDDEN_VALUE_REF":
        hidden_row = len(table["rows"])
        binding_id = f"b{len(request['source_bindings']) + 1}"
        request["source_bindings"].append(
            {
                "binding_id": binding_id,
                "binding_kind": "VALUE_CELL",
                "column_id": "c1",
                "row_id": f"r{hidden_row}",
                "source_text": table["rows"][hidden_row - 1]["values_exact"][0],
            }
        )
        request["logical_rows"][0]["row_source_binding_ids"].append(binding_id)
    elif mutation == "COORDINATE_REBIND":
        cells = request["logical_rows"][0]["cells"]
        source_binding_id = cells[1]["value_source_binding_ids"][0]
        source_binding = next(
            binding
            for binding in request["source_bindings"]
            if binding["binding_id"] == source_binding_id
        )
        cells[0]["value_source_binding_ids"] = [source_binding_id]
        cells[0]["source_text"] = source_binding["source_text"]
        cells[0]["money"] = _money_receipt(source_binding["source_text"])
    return compose_document_region_fragments_v1(
        selected_page_json_version_ids=ids,
        page_records=records,
        fragment_requests=[request],
        document_period_axis=_axis(),
        policy=raw_policy,
        compiled_specs=compiled_specs,
        projection_adapter=project_exact_axis_document_region_fragment_v1,
        projection_inventory_adapter=inventory_exact_axis_document_region_fragment_v1,
    )


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

    basic_pages, basic_requests = _basic_pages()
    with pytest.raises(DocumentRegionFragmentComposerV1Error, match="policy is invalid"):
        _compose(basic_pages, basic_requests, maximum_components=9)


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


def test_fully_blank_declared_role_table_is_inventoried_and_remains_unknown() -> None:
    page = _page(
        [
            _table([_row("Cho vay bằng VND", [None, None])]),
            _table([_row("Cho vay bằng VND", ["60", "50"])]),
            _table(
                [
                    _row("Cho vay bằng ngoại tệ", ["40", "30"]),
                    _row(None, ["100", "80"], "TOTAL"),
                ]
            ),
        ],
        title="Theo loại tiền tệ",
    )
    ids, _ = _records([page])
    omitted = _compose([page], [_request(ids[0], 2), _request(ids[0], 3)])
    assert omitted["status"] == UNRESOLVED
    assert any("UNCONSUMED_ROLE_BEARING" in reason for reason in omitted["reasons"])
    included = _compose([page], [_request(ids[0], 1), _request(ids[0], 2), _request(ids[0], 3)])
    assert included["status"] == UNRESOLVED
    assert "MAPPED_ROLE_CELL_IS_BLANK_UNKNOWN:r1" in included["reasons"]


@pytest.mark.parametrize("table", [_stacked_table(), _transposed_table()])
def test_general_adapter_composes_true_stacked_and_transposed_period_axes(table: dict) -> None:
    result = _compose_general(copy.deepcopy(table))
    assert result["status"] == READY
    assert {
        mapping["role"]: [value["coefficient"] for value in mapping["values"]]
        for mapping in result["mappings"]
    } == {"VND_LOANS": [60, 50], "FOREIGN_CURRENCY_AND_GOLD_LOANS": [40, 30]}
    assert all(
        value["document_region_fragment_source_cells"][0]["exact_source_bindings"]
        for mapping in result["mappings"]
        for value in mapping["values"]
    )
    fragment = result["component_fragments"][0]
    assert fragment["binding_model"] == "GENERAL_EXACT_SOURCE_BINDINGS"
    assert fragment["adapter_identity"]["implementation_ref_sha256"]


def test_exact_axis_inventory_fails_closed_on_conflicting_unsupported_role_table() -> None:
    page = _page(
        [
            _stacked_table(),
            _table([_row("Cho vay bằng VND", ["999", "998"])]),
        ],
        title="Theo loại tiền tệ",
    )
    version_ids, records = _records([page])
    compiled_specs = _compiled()
    raw_policy = _policy(
        projection_adapter=project_exact_axis_document_region_fragment_v1,
        projection_inventory_adapter=inventory_exact_axis_document_region_fragment_v1,
        projection_adapter_id=GENERAL_ADAPTER_ID,
        projection_adapter_format_version=GENERAL_ADAPTER_VERSION,
        projection_inventory_adapter_id=GENERAL_INVENTORY_ID,
        projection_inventory_adapter_format_version=GENERAL_INVENTORY_VERSION,
    )
    policy = compile_document_region_fragment_composer_policy_v1(
        raw_policy, compiled_specs=compiled_specs
    )
    requests = [
        inventory_exact_axis_document_region_fragment_v1(
            page_record=records[0],
            section_id="s1",
            table_id=f"t{table_ordinal}",
            document_period_axis=_axis(),
            policy=policy,
            compiled_specs=compiled_specs,
        )
        for table_ordinal in (1, 2)
    ]
    assert all(request is not None for request in requests)
    assert requests[1]["projection_reasons"] == ["UNSUPPORTED_ROLE_BEARING_EXACT_AXIS_LAYOUT"]
    result = compose_document_region_fragments_v1(
        selected_page_json_version_ids=version_ids,
        page_records=records,
        fragment_requests=requests,
        document_period_axis=_axis(),
        policy=raw_policy,
        compiled_specs=compiled_specs,
        projection_adapter=project_exact_axis_document_region_fragment_v1,
        projection_inventory_adapter=inventory_exact_axis_document_region_fragment_v1,
    )
    assert result["status"] == UNRESOLVED
    assert "UNSUPPORTED_ROLE_BEARING_EXACT_AXIS_LAYOUT" in result["reasons"]


def test_exact_axis_inventory_handles_null_period_row_as_typed_unsupported() -> None:
    table = _transposed_table()
    table["rows"][0]["label_exact"] = None
    table["rows"][0]["hierarchy_path_exact"] = []
    _ids, records = _records([_page([table], title="Theo loại tiền tệ")])
    compiled_specs = _compiled()
    policy = compile_document_region_fragment_composer_policy_v1(
        _policy(
            projection_adapter=project_exact_axis_document_region_fragment_v1,
            projection_inventory_adapter=inventory_exact_axis_document_region_fragment_v1,
            projection_adapter_id=GENERAL_ADAPTER_ID,
            projection_adapter_format_version=GENERAL_ADAPTER_VERSION,
            projection_inventory_adapter_id=GENERAL_INVENTORY_ID,
            projection_inventory_adapter_format_version=GENERAL_INVENTORY_VERSION,
        ),
        compiled_specs=compiled_specs,
    )
    request = inventory_exact_axis_document_region_fragment_v1(
        page_record=records[0],
        section_id="s1",
        table_id="t1",
        document_period_axis=_axis(),
        policy=policy,
        compiled_specs=compiled_specs,
    )
    assert request is not None
    assert request["projection_reasons"] == ["UNSUPPORTED_ROLE_BEARING_EXACT_AXIS_LAYOUT"]


def test_general_adapter_preserves_exact_parent_population_context() -> None:
    table = _stacked_table()
    for ordinal in (2, 3, 4, 6, 7, 8):
        row = table["rows"][ordinal - 1]
        row["hierarchy_path_exact"] = ["Theo loại tiền tệ", row["label_exact"]]
    result = _compose_general(table)
    assert result["status"] == READY
    assert all(
        row["population_context_exact"] == ["Theo loại tiền tệ"]
        for row in result["component_fragments"][0]["logical_rows"]
    )

    stripped = copy.deepcopy(table)
    stripped["title_exact"] = "STACKED_STRIPPED_CONTEXT"
    with pytest.raises(DocumentRegionFragmentComposerV1Error, match="population context"):
        _compose_general(stripped, mutation="STRIPPED_CONTEXT")


@pytest.mark.parametrize(
    "suffix,match",
    [
        ("FORGED_VALUE", "VALUE_CELL binding drifted"),
        ("MISSING_REF", "value-source binding references"),
        ("DUPLICATE_BINDING", "source binding identity"),
        ("UNUSED_BINDING", "source bindings are not exhaustive"),
        ("SWAPPED_PERIOD", "period is not source-authenticated"),
        ("FORGED_ROLE", "role projection is not source-authenticated"),
        ("SWAPPED_LOGICAL_ORDER", "logical source order"),
        ("FORGED_METRIC", "metric is not source-authenticated"),
        ("FORGED_ROW_KIND", "source row_kind drifted"),
        ("COORDINATE_REBIND", "stacked coordinate relation"),
    ],
)
def test_general_adapter_rejects_forged_missing_duplicate_or_semantic_rebinding(
    suffix: str, match: str
) -> None:
    with pytest.raises(DocumentRegionFragmentComposerV1Error, match=match):
        _compose_general(_stacked_table(), mutation=suffix)


def test_general_adapter_rejects_hidden_numeric_value_cell_as_row_evidence() -> None:
    table = _stacked_table()
    table["rows"].append(_row("Không liên quan", ["999"]))
    with pytest.raises(
        DocumentRegionFragmentComposerV1Error,
        match="VALUE_CELL binding is outside value_source_binding_ids",
    ):
        _compose_general(table, mutation="HIDDEN_VALUE_REF")


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


def test_source_header_period_binding_rejects_a_coherent_period_swapping_adapter() -> None:
    with pytest.raises(DocumentRegionFragmentComposerV1Error, match="trusted registry"):
        document_region_fragment_adapter_identity_v1(
            _coherent_period_swapping_column_adapter,
            adapter_id="DOCUMENT_REGION_COHERENT_PERIOD_SWAP_ATTACK",
            adapter_format_version="DOCUMENT_REGION_COLUMN_LANE_ADAPTER_V1",
        )


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
    malicious_kwargs = {**kwargs, "projection_adapter": _coherent_period_swapping_column_adapter}
    with pytest.raises(DocumentRegionFragmentComposerV1Error, match="trusted registry"):
        validate_document_region_fragment_composition_store_replay_v1(
            path, **malicious_kwargs, composition=result
        )
    attack_id = "DOCUMENT_REGION_COHERENT_PERIOD_SWAP_ATTACK"
    attack_policy = copy.deepcopy(kwargs["policy"])
    forged_identity = copy.deepcopy(attack_policy["projection_adapter_identity"])
    forged_identity["adapter_id"] = attack_id
    forged_identity["implementation_ref_sha256"] = "9" * 64
    attack_policy["projection_adapter_identity"] = forged_identity
    attack_requests = copy.deepcopy(requests)
    for request in attack_requests:
        request["composer_policy_sha256"] = canonical_json_sha256_v1(attack_policy)
        request["projection_adapter_id"] = attack_id
        request["projection_adapter_implementation_ref_sha256"] = "9" * 64
    with pytest.raises(DocumentRegionFragmentComposerV1Error, match="not registered"):
        validate_document_region_fragment_composition_store_replay_v1(
            path,
            selected_page_json_version_ids=version_ids,
            fragment_requests=attack_requests,
            document_period_axis=_axis(document_id),
            policy=attack_policy,
            compiled_specs=_compiled(),
            projection_adapter=_coherent_period_swapping_column_adapter,
            projection_inventory_adapter=inventory_column_lane_document_region_fragment_v1,
            composition=result,
        )
