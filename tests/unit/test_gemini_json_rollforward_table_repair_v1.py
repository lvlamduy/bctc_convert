from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from test_gemini_financial_page_store_v1 import _result

from bctc_ai.evaluation import gemini_json_rollforward_table_repair_v1 as subject
from bctc_ai.evaluation.gemini_json_rollforward_table_repair_v1 import (
    GeminiJsonRollforwardTableRepairV1Error,
    build_rollforward_table_cell_repair_plans_v1,
    build_rollforward_table_repair_attempt_v1,
    build_rollforward_table_repair_overlay_v1,
    build_rollforward_table_repair_prompt_v1,
    crop_rollforward_table_image_v1,
    merge_rollforward_table_repair_v1,
    rollforward_table_repair_target_v1,
    validate_rollforward_table_repair_plan_page_store_v1,
    validate_rollforward_table_source_corroboration_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.storage import gemini_financial_page_store_v1 as page_store_subject
from bctc_ai.storage.gemini_financial_page_store_v1 import (
    ingest_financial_page_extraction_v1,
    initialize_gemini_financial_page_store_v1,
    record_page_json_region_repair_v1,
)

PRODUCTION_AXIS = [
    {
        "crop": [330, 1950, 2390, 3340],
        "ordinal": 9,
        "page": 17,
        "section_id": "s3",
        "source": "vietstock_bctc/ACB/2025/BCTC Hợp nhất quý 1 năm 2025.pdf",
        "source_sha256": "5a22f62d8b2853423f71fab7d09e42f96cf8dc3eacd9032836febb5550198db7",
        "table_id": "t1",
    },
    {
        "crop": [250, 1950, 2390, 3170],
        "ordinal": 10,
        "page": 18,
        "section_id": "s1",
        "source": "vietstock_bctc/ACB/2025/BCTC Hợp nhất quý 2 năm 2025.pdf",
        "source_sha256": "2952d7a567ca49f17867c4677d45a40632097eab74fa0a32c6c22ed52b21ede6",
        "table_id": "t3",
    },
    {
        "crop": [250, 1900, 2390, 3150],
        "ordinal": 11,
        "page": 18,
        "section_id": "s1",
        "source": "vietstock_bctc/ACB/2025/BCTC Hợp nhất quý 3 năm 2025.pdf",
        "source_sha256": "62ad59ba4d81857ba1c610c2d9733747283ed9f9b584a3bd1c5f2b2a48a75bff",
        "table_id": "t3",
    },
    {
        "crop": [220, 1750, 2400, 3070],
        "ordinal": 12,
        "page": 18,
        "section_id": "s1",
        "source": "vietstock_bctc/ACB/2025/BCTC Hợp nhất quý 4 năm 2025.pdf",
        "source_sha256": "ad6cab1acd7556f8ee0372764f732f2efe8746b36b5517761f68762b095b07b7",
        "table_id": "t3",
    },
    {
        "crop": [220, 1750, 2400, 3050],
        "ordinal": 18,
        "page": 18,
        "section_id": "s3",
        "source": "vietstock_bctc/ACB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf",
        "source_sha256": "db55bb607d254aeef6daafd873a8199d621ac0740849e68d09ab0db772d11c86",
        "table_id": "t1",
    },
    {
        "crop": [250, 2000, 2350, 3050],
        "ordinal": 35,
        "page": 42,
        "section_id": "s1",
        "source": "vietstock_bctc/CTG/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf",
        "source_sha256": "87f852400bf25421aa80000436387f25c5382bfd0d72a4d67122493361b486e6",
        "table_id": "t3",
    },
]
_CAPTURED_RESPONSES = (
    Path(__file__).resolve().parents[1] / "fixtures" / "family13_captured_table_responses_v1.json"
)


def _row(label: str, values: list[str | None], *, total: bool = False) -> dict:
    return {
        "hierarchy_path_exact": [label],
        "label_exact": label,
        "row_kind": "TOTAL" if total else "ITEM",
        "values_exact": values,
    }


def _columns() -> list[dict]:
    return [
        {"header_path_exact": ["Dự phòng cụ thể"], "value_kind": "MONEY"},
        {"header_path_exact": ["Dự phòng chung"], "value_kind": "MONEY"},
        {"header_path_exact": ["Tổng cộng"], "value_kind": "MONEY"},
    ]


def _acb_table() -> dict:
    return {
        "columns": _columns(),
        "continuation": "NONE",
        "rows": [
            _row("Số dư đầu kỳ 2025", ["100", "200", "110"]),
            _row("Trích lập 2025", ["20", "30", None]),
            _row("Sử dụng 2025", ["(10)", "(15)", None]),
            _row("Số dư cuối kỳ 2025", ["110", "215", "110"], total=True),
            _row("Số dư đầu kỳ 2024", ["90", "190", "100"]),
            _row("Trích lập 2024", ["10", "10", None]),
            _row("Sử dụng 2024", ["-", "-", None]),
            _row("Số dư cuối kỳ 2024", ["100", "200", "100"], total=True),
        ],
        "title_exact": "Biến động dự phòng rủi ro cho vay khách hàng",
        "unit_exact": "Triệu đồng",
    }


def _ctg_table() -> dict:
    return {
        "columns": _columns(),
        "continuation": "NONE",
        "rows": [
            _row("Số dư tại ngày 1 tháng 1 năm 2024", ["16.638.548", "10.860.006", "27.498.554"]),
            _row("Trích lập trong năm", ["25.424.264", "1.825.755", "27.250.019"]),
            _row("Sử dụng trong năm", ["(18.417.106)", "(18.417.106)", None]),
            _row("Số dư tại ngày 31 tháng 12 năm 2024", ["23.645.706", "12.685.761", "36.331.467"]),
            _row("Trích lập trong năm 2025", ["15.248.173", "2.009.598", "17.257.771"]),
            _row("Sử dụng trong năm 2025", ["(18.986.013)", "-", "(18.986.013)"]),
            _row("Số dư tại ngày 31 tháng 12 năm 2025", ["19.907.866", "14.695.359", "34.603.225"]),
        ],
        "title_exact": "7.6 Dự phòng rủi ro cho vay khách hàng",
        "unit_exact": "Triệu đồng",
    }


def _page_at(table: dict, section_id: str, table_id: str) -> dict:
    section_count = int(section_id[1:])
    table_count = int(table_id[1:])
    sections = []
    for section_ordinal in range(1, section_count + 1):
        tables = []
        for table_ordinal in range(1, table_count + 1):
            selected = (
                table
                if (section_ordinal, table_ordinal) == (section_count, table_count)
                else {
                    "columns": [{"header_path_exact": ["Giá trị"], "value_kind": "MONEY"}],
                    "continuation": "NONE",
                    "rows": [_row("Dòng kiểm soát", ["1"])],
                    "title_exact": "Bảng kiểm soát",
                    "unit_exact": "Triệu đồng",
                }
            )
            tables.append(deepcopy(selected))
        sections.append(
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": ["Dự phòng rủi ro cho vay khách hàng"],
                "statement_type": "NOT_APPLICABLE",
                "tables": tables,
                "title_exact": "Dự phòng rủi ro cho vay khách hàng",
            }
        )
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": sections,
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _png(ordinal: int, *, height: int) -> bytes:
    image = Image.new("RGB", (2481, height), (240 - ordinal % 20, 240, 240))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _cell_state(value: str | None) -> str:
    if value is None:
        return "BLANK"
    if value.strip() in {"-", "–", "—", "_"}:
        return "DASH"
    digits = value.strip().strip("()").replace(".", "").replace(",", "").replace(" ", "")
    return "PRINTED_ZERO" if digits == "0" else "VALUE"


def _response(page: dict, plan: dict, *, corrected: bool = True) -> dict:
    section = page["sections"][int(plan["section_id"][1:]) - 1]
    table = section["tables"][int(plan["table_id"][1:]) - 1]
    values = [list(row["values_exact"]) for row in table["rows"]]
    if corrected and plan["document_ordinal"] != 35:
        for row in (1, 2, 5, 6):
            values[row][2] = "-"
    elif corrected:
        values[2][1] = "-"
        values[2][2] = "(18.417.106)"
    return {
        "all_cells_transcribed": True,
        "columns": deepcopy(table["columns"]),
        "rows": [
            {
                "cells": [
                    {"source_text": value, "visual_state": _cell_state(value)} for value in row
                ],
                "label_exact": table["rows"][index]["label_exact"],
            }
            for index, row in enumerate(values)
        ],
        "table_title_exact": table["title_exact"],
        "target_id": f"{plan['section_id']}:{plan['table_id']}",
        "uncertainty_exact": [],
        "unit_exact": table["unit_exact"],
    }


def _target_response(page: dict, plan: dict, *, corrected: bool = True) -> dict:
    legacy = _response(page, plan, corrected=corrected)
    observations = []
    for allowed in plan["cell_allowlist"]:
        row, column = (int(part[1:]) - 1 for part in allowed["cell_id"].split(":"))
        observations.append(
            {
                "cell_id": allowed["cell_id"],
                "source_text": legacy["rows"][row]["cells"][column]["source_text"],
            }
        )
    return {"observations": observations}


def _source_record(region: dict, movement_role: str, row_id: str) -> dict:
    return {"locator": deepcopy(region), "movement_role": movement_role, "row_id": row_id}


def _candidate(axis: dict, evidence: dict) -> dict:
    region = {
        "document_id": evidence["source_binding_without_crop"]["document_id"],
        "page_json_version_id": evidence["base_page_json_version_id"],
        "physical_page": axis["page"],
        "section_id": axis["section_id"],
        "source_logical_name": axis["source"],
        "source_sha256": axis["source_sha256"],
        "table_id": axis["table_id"],
    }
    roles = [
        ("OPENING_BALANCE_ROW", "r1"),
        ("PROVISION_OR_REVERSAL_ROW", "r2"),
        ("USE_MOVEMENT_ROW", "r3"),
        ("CLOSING_BALANCE_ROW", "r4"),
    ]
    if axis["ordinal"] == 35:
        frontier = {
            "lane_role": "GENERAL_PROVISION_LANE",
            "period_role": "COMPARATIVE_PERIOD",
            "reason": "ROLLFORWARD_LANE_EQUATION_MISMATCH:COMPARATIVE_PERIOD:GENERAL_PROVISION_LANE",
            "source_records": [_source_record(region, role, row) for role, row in roles],
            "unknown_roles": [],
        }
        coefficients = [10860006, 1825755, -18417106, 12685761]
        vectors = [
            {
                "column_ordinal": 2,
                "lane_role": frontier["lane_role"],
                "locator": deepcopy(region),
                "movement_role": role,
                "period_role": frontier["period_role"],
                "row_id": row,
            }
            for role, row in roles
        ]
        equations = [
            {
                "lane_role": frontier["lane_role"],
                "period_role": frontier["period_role"],
                "role_coefficients": [
                    {
                        "coefficient": coefficient,
                        "equation_coefficient": -1 if role == "CLOSING_BALANCE_ROW" else 1,
                        "role": role,
                    }
                    for (role, _row), coefficient in zip(roles, coefficients, strict=True)
                ],
            }
        ]
        frontiers = [frontier]
    else:
        vectors = []
        equations = []
        frontiers = []
        for period, offset in (("CURRENT_PERIOD", 0), ("COMPARATIVE_PERIOD", 4)):
            period_roles = [(role, f"r{int(row[1:]) + offset}") for role, row in roles]
            frontier = {
                "lane_role": "MARGIN_ADVANCE_PROVISION_LANE",
                "period_role": period,
                "reason": "ROLLFORWARD_LANE_EQUATION_RANK_DEFICIENT_MULTIPLE_UNKNOWNS:"
                + ("" if period == "CURRENT_PERIOD" else "COMPARATIVE_PERIOD:")
                + "MARGIN_ADVANCE_PROVISION_LANE",
                "source_records": [_source_record(region, role, row) for role, row in period_roles],
                "unknown_roles": ["PROVISION_OR_REVERSAL_ROW", "USE_MOVEMENT_ROW"],
            }
            frontiers.append(frontier)
            vectors.extend(
                {
                    "column_ordinal": 3,
                    "lane_role": frontier["lane_role"],
                    "locator": deepcopy(region),
                    "movement_role": role,
                    "period_role": period,
                    "row_id": row,
                }
                for role, row in period_roles
            )
            equations.append(
                {
                    "lane_role": frontier["lane_role"],
                    "period_role": period,
                    "role_coefficients": [
                        {
                            "coefficient": None if role in frontier["unknown_roles"] else 110,
                            "equation_coefficient": -1 if role == "CLOSING_BALANCE_ROW" else 1,
                            "role": role,
                        }
                        for role, _row in period_roles
                    ],
                }
            )
    return {
        "candidate_id": "gjfafcv1:candidate:" + sha256(str(axis["ordinal"]).encode()).hexdigest(),
        "closure_receipt": {
            "equations": equations,
            "role_vectors": vectors,
            "unresolved_frontiers": frontiers,
        },
        "component_regions": [region],
        "family_id": "PROVISION_MOVEMENT_ROLLFORWARD",
        "status": "UNRESOLVED_GEMINI_JSON_FAMILY",
    }


@pytest.fixture
def corpus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    store = tmp_path / "pages.sqlite3"
    initialize_gemini_financial_page_store_v1(store)
    pages = {}
    images = {}
    evidence = []
    for axis in PRODUCTION_AXIS:
        table = _ctg_table() if axis["ordinal"] == 35 else _acb_table()
        page = _page_at(table, axis["section_id"], axis["table_id"])
        height = 3508 if axis["ordinal"] == 35 else 3509
        image = _png(axis["ordinal"], height=height)
        ids = ingest_financial_page_extraction_v1(
            store,
            document={
                "source_logical_name": axis["source"],
                "source_sha256": axis["source_sha256"],
                "source_size_bytes": 1000 + axis["ordinal"],
            },
            page={
                "physical_page": axis["page"],
                "image_sha256": sha256(image).hexdigest(),
                "image_size_bytes": len(image),
                "pixel_width": 2481,
                "pixel_height": height,
                "render_dpi": 300,
                "media_type": "image/png",
            },
            prompt_variant="compact",
            output_contract_mode="JSON_SCHEMA",
            prompt_sha256=f"{axis['ordinal']:064x}",
            response_schema_sha256="e" * 64,
            requested_model="gemini-3.7-flash",
            requested_service_tier="flex",
            thinking_level="low",
            provider_result=_result(),
            page_json=page,
        )
        pages[ids["page_json_version_id"]] = page
        images[ids["page_json_version_id"]] = image
        evidence.extend(
            subject.load_rollforward_table_page_evidence_v1(
                store, page_json_version_ids=[ids["page_json_version_id"]]
            )
        )
    candidates = [
        _candidate(axis, item) for axis, item in zip(PRODUCTION_AXIS, evidence, strict=True)
    ]
    sweep = {
        "family_id": "PROVISION_MOVEMENT_ROLLFORWARD",
        "indexed_query_evidence": {"fixture": "exact-selected-frontier"},
        "specs": {
            "evaluation": {
                "value": {
                    "layout_spec": {
                        "movement_roles": [
                            {"kind": "OPENING", "role": "OPENING_BALANCE_ROW"},
                            {
                                "kind": "PROVISION_OR_REVERSAL",
                                "role": "PROVISION_OR_REVERSAL_ROW",
                            },
                            {"kind": "USE", "role": "USE_MOVEMENT_ROW"},
                            {"kind": "CLOSING", "role": "CLOSING_BALANCE_ROW"},
                        ]
                    }
                }
            },
            "schema_binding": {"value": {"fixture": "schema"}},
            "topology": {"value": {"fixture": "topology"}},
        },
        "sweep_id": "gjfafsv1:sweep:" + "9" * 64,
        "trials": [
            {
                "candidates": [candidate],
                "document_ordinal": axis["ordinal"],
                "status": "UNRESOLVED_GEMINI_JSON_FAMILY",
            }
            for axis, candidate in zip(PRODUCTION_AXIS, candidates, strict=True)
        ],
    }
    monkeypatch.setattr(subject, "validate_gemini_json_flat_family_sweep_v1", lambda value: value)
    compiled = {"fixture": "compiled-rollforward-specs"}
    monkeypatch.setattr(
        subject,
        "compile_gemini_json_flat_family_specs_v1",
        lambda _topology, _evaluation, _schema: compiled,
    )
    authoritative_candidates = {
        candidate["candidate_id"]: deepcopy(candidate) for candidate in candidates
    }

    def replay_query_and_candidates(_path, *, trials, **_kwargs):
        for trial in trials:
            for candidate in trial["candidates"]:
                expected = authoritative_candidates.get(candidate.get("candidate_id"))
                if expected != candidate:
                    raise GeminiJsonRollforwardTableRepairV1Error(
                        "fixture semantic candidate replay rejected coherent drift"
                    )
        return sweep["indexed_query_evidence"]

    monkeypatch.setattr(
        page_store_subject,
        "validate_selected_rollforward_family_query_evidence_v1",
        replay_query_and_candidates,
    )
    specs = []
    for axis, item in zip(PRODUCTION_AXIS[:5], evidence[:5], strict=True):
        specs.append(
            {
                "base_page_json_version_id": item["base_page_json_version_id"],
                "collateral_cell_ids": [],
                "collateral_equations": [],
                "crop_bbox_pixels_xyxy": axis["crop"],
                "format_version": subject.TABLE_SPEC_FORMAT_VERSION,
                "section_id": axis["section_id"],
                "table_id": axis["table_id"],
                "dash_zero_cell_ids": ["r2:c3", "r3:c3", "r6:c3", "r7:c3"],
            }
        )
    row_totals = [
        {
            "equation_id": f"row-total-r{row}",
            "result_cell_id": f"r{row}:c3",
            "terms": [
                {"cell_id": f"r{row}:c1", "multiplier": 1},
                {"cell_id": f"r{row}:c2", "multiplier": 1},
            ],
        }
        for row in range(1, 8)
    ]
    specs.append(
        {
            "base_page_json_version_id": evidence[-1]["base_page_json_version_id"],
            "collateral_cell_ids": ["r3:c3"],
            "collateral_equations": row_totals,
            "crop_bbox_pixels_xyxy": PRODUCTION_AXIS[-1]["crop"],
            "format_version": subject.TABLE_SPEC_FORMAT_VERSION,
            "section_id": "s1",
            "table_id": "t3",
            "dash_zero_cell_ids": ["r3:c2"],
        }
    )
    plans = build_rollforward_table_cell_repair_plans_v1(
        compiled_specs=compiled,
        family_sweep=sweep,
        page_store_path=store,
        selected_page_json_version_ids=[item["base_page_json_version_id"] for item in evidence],
        table_repair_specs=specs,
    )
    authority = subject.rollforward_table_repair_plan_authority_v1(
        compiled_spec_sources={
            "evaluation": sweep["specs"]["evaluation"]["value"],
            "schema_binding": sweep["specs"]["schema_binding"]["value"],
            "topology": sweep["specs"]["topology"]["value"],
        },
        family_sweep=sweep,
        selected_page_json_version_ids=[item["base_page_json_version_id"] for item in evidence],
        table_repair_specs=specs,
    )
    repair_spec_authority = subject.build_rollforward_table_repair_spec_authority_v1(
        authority_kind="PINNED_CONFIG",
        authority_ref="config://family13/rollforward-table-repairs-v1",
        authority_sha256="7" * 64,
        source_image_resolver_implementation_path=(
            "src/bctc_ai/evaluation/gemini_json_first_page_render_v1.py"
        ),
        source_image_resolver_implementation_sha256="8" * 64,
        source_image_resolver_implementation_size_bytes=123,
        source_image_resolver_mupdf_version="1.29.0",
        source_image_resolver_pymupdf_version="1.28.0",
        table_repair_specs=specs,
        plans=plans,
    )
    return {
        "authority": authority,
        "evidence": evidence,
        "compiled": compiled,
        "images": images,
        "pages": pages,
        "plans": plans,
        "repair_spec_authority": repair_spec_authority,
        "specs": specs,
        "store": store,
        "sweep": sweep,
    }


def _reseal_plan(plan: dict) -> None:
    material = {key: plan[key] for key in plan if key != "repair_job_id"}
    plan["repair_job_id"] = "gjfrrqv1:job:" + canonical_json_sha256_v1(material)


def _usage() -> dict:
    return {
        "actual_cost_usd": "0.001234",
        "cached_input_tokens": 0,
        "cost_disposition": "OPENROUTER_ACTUAL",
        "input_tokens": 600,
        "output_tokens": 300,
        "thought_tokens": 20,
        "total_tokens": 900,
    }


def _provider() -> dict:
    return {
        "provider_model": "google/gemini-3.7-flash",
        "provider_name": "openrouter",
        "request_id_sha256": "1" * 64,
        "response_id_sha256": "2" * 64,
        "service_tier": "flex",
    }


def _raw_ref(payload: bytes, name: str = "response.json") -> dict:
    return {
        "path": f"artifacts/{name}",
        "sha256": sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _attempt_context(corpus: dict, plan: dict, crop: bytes) -> dict:
    return {
        "authority": corpus["authority"],
        "repair_spec_authority": corpus["repair_spec_authority"],
        "crop_image_bytes": crop,
        "page_store_path": corpus["store"],
        "source_image_bytes": corpus["images"][plan["base_page_json_version_id"]],
    }


def _artifact_map(*payloads: bytes) -> dict[str, bytes]:
    return {sha256(payload).hexdigest(): payload for payload in payloads}


def test_six_declarative_jobs_are_exactly_sweep_and_store_derived(corpus: dict) -> None:
    plans = corpus["plans"]
    assert [plan["document_ordinal"] for plan in plans] == [9, 10, 11, 12, 18, 35]
    assert [plan["source_binding"]["crop_bbox_pixels_xyxy"] for plan in plans] == [
        item["crop"] for item in PRODUCTION_AXIS
    ]
    for plan in plans[:5]:
        assert [item["cell_id"] for item in plan["cell_allowlist"]] == [
            "r2:c3",
            "r3:c3",
            "r6:c3",
            "r7:c3",
        ]
        assert {item["change_policy"] for item in plan["cell_allowlist"]} == {"MUST_CHANGE"}
        assert {item["after_policy"] for item in plan["cell_allowlist"]} == {"DASH_ZERO"}
        assert plan["shape_gate"]["row_count"] == 8
        assert plan["shape_gate"]["column_count"] == 3
    ctg = plans[-1]
    assert ctg["shape_gate"]["row_count"] == 7
    assert ctg["shape_gate"]["column_count"] == 3
    assert [item["cell_id"] for item in ctg["cell_allowlist"]] == [
        "r1:c2",
        "r2:c2",
        "r3:c2",
        "r3:c3",
        "r4:c2",
    ]
    assert {item["change_policy"] for item in ctg["cell_allowlist"]} == {"MAY_CHANGE"}
    assert len(ctg["equation_inventory"]) == 8
    for plan in plans:
        assert (
            validate_rollforward_table_repair_plan_page_store_v1(
                plan, page_store_path=corpus["store"]
            )["base_page_json_version_id"]
            == plan["base_page_json_version_id"]
        )


def test_planner_rejects_coherently_rehashed_unknown_role_and_vector_forgery(
    corpus: dict,
) -> None:
    attacked = deepcopy(corpus["sweep"])
    candidate = attacked["trials"][0]["candidates"][0]
    candidate["closure_receipt"]["unresolved_frontiers"][0]["unknown_roles"] = [
        "CLOSING_BALANCE_ROW",
        "PROVISION_OR_REVERSAL_ROW",
    ]
    candidate["closure_receipt"]["role_vectors"][1]["column_ordinal"] = 2
    material = {key: candidate[key] for key in candidate if key != "candidate_id"}
    candidate["candidate_id"] = "gjfafcv1:candidate:" + canonical_json_sha256_v1(material)
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="semantic candidate replay"):
        build_rollforward_table_cell_repair_plans_v1(
            compiled_specs=corpus["compiled"],
            family_sweep=attacked,
            page_store_path=corpus["store"],
            selected_page_json_version_ids=[
                item["base_page_json_version_id"] for item in corpus["evidence"]
            ],
            table_repair_specs=corpus["specs"],
        )


def test_planner_replays_exact_caller_authenticated_selected_frontier(
    corpus: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = [item["base_page_json_version_id"] for item in corpus["evidence"]]

    def exact_query_replay(_path, *, selected_page_json_version_ids, **_kwargs):
        if selected_page_json_version_ids != expected:
            raise ValueError("selected page frontier drifted")
        return corpus["sweep"]["indexed_query_evidence"]

    monkeypatch.setattr(
        page_store_subject,
        "validate_selected_rollforward_family_query_evidence_v1",
        exact_query_replay,
    )
    with pytest.raises(ValueError, match="selected page frontier drifted"):
        build_rollforward_table_cell_repair_plans_v1(
            compiled_specs=corpus["compiled"],
            family_sweep=corpus["sweep"],
            page_store_path=corpus["store"],
            selected_page_json_version_ids=expected[:-1],
            table_repair_specs=corpus["specs"],
        )


def test_prompt_is_structural_complete_and_response_blind(corpus: dict) -> None:
    plan = corpus["plans"][-1]
    page = corpus["pages"][plan["base_page_json_version_id"]]
    prompt = build_rollforward_table_repair_prompt_v1(
        base_page_json_version_id=plan["base_page_json_version_id"],
        target=rollforward_table_repair_target_v1(page, plan=plan),
    )
    assert "cell_id" in prompt and "column_header_exact" in prompt and "row_label_exact" in prompt
    assert "{cell_id, source_text}" in prompt
    assert "không tính toán hoặc suy ra" in prompt
    assert "visual_state" not in prompt
    assert "uncertainty_exact" not in prompt
    for forbidden in (
        "after_policy",
        "change_policy",
        "evidence_kind",
        "DASH_ZERO",
        "MUST_CHANGE",
        "MAY_CHANGE",
        "equation",
        "collateral",
    ):
        assert forbidden not in prompt
    assert set(subject.rollforward_table_repair_response_schema_v1()["properties"]) == {
        "observations"
    }
    assert "18.417.106" not in prompt
    assert "before_exact" not in prompt
    assert sha256(prompt.encode()).hexdigest() == plan["request_contract"]["prompt_sha256"]


def test_minimal_observations_ignore_outside_drift_and_normalize_cell_ids(corpus: dict) -> None:
    plan = corpus["plans"][0]
    page = corpus["pages"][plan["base_page_json_version_id"]]
    repair = _target_response(page, plan)
    for observation in repair["observations"]:
        row, column = observation["cell_id"].split(":")
        observation["cell_id"] = f" R 0{row[1:]} : C 0{column[1:]} "
    repair["observations"].append({"cell_id": "r1:c1", "source_text": "999999999"})
    repair["legacy_full_table_echo"] = {"changed": True}

    merged, receipt = merge_rollforward_table_repair_v1(
        page,
        plan=plan,
        repair=repair,
        page_store_path=corpus["store"],
        authority=corpus["authority"],
        repair_spec_authority=corpus["repair_spec_authority"],
    )

    projection = receipt["changes"][0]["response_projection"]
    assert projection["input_contract"] == "TARGET_OBSERVATIONS_V1"
    assert projection["ignored_observation_count"] == 1
    assert projection["ignored_top_level_fields"] == ["legacy_full_table_echo"]
    assert receipt["changes"][0]["changed_cell_count"] == 4
    assert page["sections"][2]["tables"][0]["rows"][0]["values_exact"][0] == "100"
    assert merged["sections"][2]["tables"][0]["rows"][0]["values_exact"][0] == "100"

    uncertain = _target_response(page, plan)
    uncertain["uncertainty_exact"] = ["Không đọc chắc R02:C03"]
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="uncertainty for a target"):
        subject.decode_rollforward_table_repair_text_v1(
            canonical_json_bytes_v1(uncertain).decode("utf-8"),
            target=rollforward_table_repair_target_v1(page, plan=plan),
        )
    unscoped = _target_response(page, plan)
    unscoped["uncertain_refs"] = ["không chắc"]
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="unscoped incomplete"):
        subject.decode_rollforward_table_repair_text_v1(
            canonical_json_bytes_v1(unscoped).decode("utf-8"),
            target=rollforward_table_repair_target_v1(page, plan=plan),
        )
    outside_uncertainty = _target_response(page, plan)
    outside_uncertainty["uncertainty_exact"] = ["Không đọc chắc Ｒ０１：Ｃ０１"]
    outside_projection = subject.decode_rollforward_table_repair_text_v1(
        canonical_json_bytes_v1(outside_uncertainty).decode("utf-8"),
        target=rollforward_table_repair_target_v1(page, plan=plan),
    )
    assert (
        "uncertainty_exact"
        in outside_projection["projection_diagnostics"]["ignored_top_level_fields"]
    )
    explicitly_incomplete = _target_response(page, plan)
    explicitly_incomplete["all_cells_transcribed"] = False
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="incomplete target"):
        subject.decode_rollforward_table_repair_text_v1(
            canonical_json_bytes_v1(explicitly_incomplete).decode("utf-8"),
            target=rollforward_table_repair_target_v1(page, plan=plan),
        )


def test_semantic_duplicate_corroborates_but_true_target_conflict_vetoes(corpus: dict) -> None:
    plan = corpus["plans"][-1]
    page = corpus["pages"][plan["base_page_json_version_id"]]
    repair = _target_response(page, plan)
    repair["observations"].append({"cell_id": "R03:C03", "source_text": "−18 417 106"})
    merged, receipt = merge_rollforward_table_repair_v1(
        page,
        plan=plan,
        repair=repair,
        page_store_path=corpus["store"],
        authority=corpus["authority"],
        repair_spec_authority=corpus["repair_spec_authority"],
    )
    projection = receipt["changes"][0]["response_projection"]
    assert projection["corroborated_duplicate_count"] == 1
    assert projection["corroborated_observations"][0]["semantic_equivalence"] == {
        "signed_integer": -18_417_106,
        "visual_state": "VALUE",
    }
    assert merged["sections"][0]["tables"][2]["rows"][2]["values_exact"][2] in {
        "(18.417.106)",
        "−18 417 106",
    }

    conflict = deepcopy(repair)
    conflict["observations"][-1]["source_text"] = "-18 417 105"
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="conflict"):
        merge_rollforward_table_repair_v1(
            page,
            plan=plan,
            repair=conflict,
            page_store_path=corpus["store"],
            authority=corpus["authority"],
            repair_spec_authority=corpus["repair_spec_authority"],
        )

    acb_plan = corpus["plans"][0]
    acb_page = corpus["pages"][acb_plan["base_page_json_version_id"]]
    acb_target = rollforward_table_repair_target_v1(acb_page, plan=acb_plan)
    dash_zero_conflict = _target_response(acb_page, acb_plan)
    dash_zero_conflict["observations"].append({"cell_id": "r2:c3", "source_text": "0"})
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="conflict"):
        subject.decode_rollforward_table_repair_text_v1(
            canonical_json_bytes_v1(dash_zero_conflict).decode("utf-8"), target=acb_target
        )
    declared_state_conflict = {
        "observations": [{"cell_id": "r2:c3", "source_text": "-", "visual_state": "PRINTED_ZERO"}]
    }
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="visual state conflicts"):
        subject.decode_rollforward_table_repair_text_v1(
            canonical_json_bytes_v1(declared_state_conflict).decode("utf-8"),
            target=acb_target,
        )


def test_nfkc_observation_variants_preserve_typed_semantics(corpus: dict) -> None:
    acb_plan = corpus["plans"][0]
    acb_page = corpus["pages"][acb_plan["base_page_json_version_id"]]
    dash = subject.decode_rollforward_table_repair_text_v1(
        '{"observations":[{"cell_id":"Ｒ０２：Ｃ０３","source_text":"－",'
        '"visual_state":"ＤＡＳＨ"}]}',
        target=rollforward_table_repair_target_v1(acb_page, plan=acb_plan),
    )
    assert dash["observations"] == [
        {"cell_id": "r2:c3", "source_text": "-", "visual_state": "DASH"}
    ]
    assert (
        dash["projection_diagnostics"]["normalized_observations"][0]["normalization_kind"]
        == "ACCOUNTING_DASH_TO_ASCII_DASH"
    )

    ctg_plan = corpus["plans"][-1]
    ctg_page = corpus["pages"][ctg_plan["base_page_json_version_id"]]
    numeric = subject.decode_rollforward_table_repair_text_v1(
        '{"observations":[{"cell_id":"Ｒ０３：Ｃ０３",'
        '"source_text":"（１８．４１７．１０６）","visual_state":"ＶＡＬＵＥ"}]}',
        target=rollforward_table_repair_target_v1(ctg_page, plan=ctg_plan),
    )
    assert numeric["observations"] == [
        {
            "cell_id": "r3:c3",
            "source_text": "（１８．４１７．１０６）",
            "visual_state": "VALUE",
        }
    ]
    assert (
        numeric["projection_diagnostics"]["normalized_observations"][0]["normalization_kind"]
        == "NFKC_SEMANTIC_VARIANT_PRESERVED"
    )
    assert subject._signed_integer(numeric["observations"][0]["source_text"]) == -18_417_106


def test_required_observations_and_may_change_semantics_are_local(corpus: dict) -> None:
    acb_plan = corpus["plans"][0]
    acb_page = corpus["pages"][acb_plan["base_page_json_version_id"]]
    incomplete = _target_response(acb_page, acb_plan)
    incomplete["observations"].pop()
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="omit a required"):
        merge_rollforward_table_repair_v1(
            acb_page,
            plan=acb_plan,
            repair=incomplete,
            page_store_path=corpus["store"],
            authority=corpus["authority"],
            repair_spec_authority=corpus["repair_spec_authority"],
        )
    target = rollforward_table_repair_target_v1(acb_page, plan=acb_plan)
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="omits source_text"):
        subject.decode_rollforward_table_repair_text_v1(
            '{"observations":[{"cell_id":"r2:c3"}]}', target=target
        )
    malformed_legacy = _response(acb_page, acb_plan)
    malformed_legacy["rows"][1]["cells"][2].pop("source_text")
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="omits source_text"):
        subject.decode_rollforward_table_repair_text_v1(
            canonical_json_bytes_v1(malformed_legacy).decode("utf-8"), target=target
        )

    ctg_plan = corpus["plans"][-1]
    ctg_page = corpus["pages"][ctg_plan["base_page_json_version_id"]]
    repair = _target_response(ctg_page, ctg_plan)
    repair["observations"] = [
        observation
        for observation in repair["observations"]
        if observation["cell_id"] in {"r1:c2", "r3:c2", "r3:c3"}
    ]
    repair["observations"][0]["source_text"] = "10 860 006"
    merged, receipt = merge_rollforward_table_repair_v1(
        ctg_page,
        plan=ctg_plan,
        repair=repair,
        page_store_path=corpus["store"],
        authority=corpus["authority"],
        repair_spec_authority=corpus["repair_spec_authority"],
    )
    table = merged["sections"][0]["tables"][2]
    assert table["rows"][0]["values_exact"][1] == "10.860.006"
    assert [item["cell_id"] for item in receipt["changes"][0]["cell_changes"]] == [
        "r3:c2",
        "r3:c3",
    ]


def test_must_change_target_accepts_unparseable_source_before_valid_accounting_parentheses() -> (
    None
):
    assert subject._repair_before_cell_semantic("(15)借-", change_policy="MUST_CHANGE") == (
        "INVALID_SOURCE",
        None,
    )
    assert subject._cell_semantic("(15)") == ("VALUE", -15)
    with pytest.raises(
        GeminiJsonRollforwardTableRepairV1Error,
        match="exact signed integer",
    ):
        subject._repair_before_cell_semantic("(15)借-", change_policy="MAY_CHANGE")


def test_legacy_projection_accepts_header_segmentation_and_null_dash(corpus: dict) -> None:
    plan = corpus["plans"][-1]
    page = corpus["pages"][plan["base_page_json_version_id"]]
    repair = _response(page, plan)
    repair["columns"][1]["header_path_exact"] = ["Dự phòng\nchung\nTriệu đồng"]
    repair["rows"][2]["cells"][1] = {"source_text": None, "visual_state": "DASH"}
    _, receipt = merge_rollforward_table_repair_v1(
        page,
        plan=plan,
        repair=repair,
        page_store_path=corpus["store"],
        authority=corpus["authority"],
        repair_spec_authority=corpus["repair_spec_authority"],
    )
    projection = receipt["changes"][0]["response_projection"]
    assert projection["input_contract"] == "LEGACY_FULL_TABLE_V1"
    assert any(
        item["normalization_kind"] == "LEGACY_NULL_WITH_DASH_STATE_TO_ASCII_DASH"
        for item in projection["normalized_observations"]
    )

    uncertain = _response(page, plan)
    uncertain["uncertainty_exact"] = ["Không đọc chắc ô r3:c2"]
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="uncertainty for a target"):
        subject.decode_rollforward_table_repair_text_v1(
            canonical_json_bytes_v1(uncertain).decode("utf-8"),
            target=rollforward_table_repair_target_v1(page, plan=plan),
        )
    outside_uncertainty = _response(page, plan)
    outside_uncertainty["uncertainty_exact"] = ["Không đọc chắc ô Ｒ０１：Ｃ０１"]
    outside_projection = subject.decode_rollforward_table_repair_text_v1(
        canonical_json_bytes_v1(outside_uncertainty).decode("utf-8"),
        target=rollforward_table_repair_target_v1(page, plan=plan),
    )
    assert (
        "uncertainty_exact"
        in outside_projection["projection_diagnostics"]["ignored_top_level_fields"]
    )


@pytest.mark.parametrize("attack", ["insert_row", "swap_rows", "swap_columns"])
def test_legacy_positional_projection_locks_shape_order_and_anchors(
    corpus: dict, attack: str
) -> None:
    plan = corpus["plans"][-1]
    page = corpus["pages"][plan["base_page_json_version_id"]]
    repair = _response(page, plan)
    if attack == "insert_row":
        repair["rows"].insert(0, deepcopy(repair["rows"][0]))
    elif attack == "swap_rows":
        repair["rows"][0], repair["rows"][1] = repair["rows"][1], repair["rows"][0]
    else:
        repair["columns"][1], repair["columns"][2] = (
            repair["columns"][2],
            repair["columns"][1],
        )
    with pytest.raises(
        GeminiJsonRollforwardTableRepairV1Error,
        match="shape or target identity|anchors drifted",
    ):
        subject.decode_rollforward_table_repair_text_v1(
            canonical_json_bytes_v1(repair).decode("utf-8"),
            target=rollforward_table_repair_target_v1(page, plan=plan),
        )


def test_canonical_projection_recomputes_source_diagnostics_and_target_axis(corpus: dict) -> None:
    plan = corpus["plans"][0]
    page = corpus["pages"][plan["base_page_json_version_id"]]
    target = rollforward_table_repair_target_v1(page, plan=plan)
    projected = subject.decode_rollforward_table_repair_text_v1(
        canonical_json_bytes_v1(_target_response(page, plan)).decode("utf-8"),
        target=target,
    )
    forged = deepcopy(projected)
    forged["projection_diagnostics"]["input_contract"] = "FORGED"
    forged["projection_diagnostics"]["raw_response_sha256"] = "f" * 64
    material = {key: value for key, value in forged.items() if key != "projection_sha256"}
    forged["projection_sha256"] = canonical_json_sha256_v1(material)
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="identity drifted"):
        subject.decode_rollforward_table_repair_text_v1(
            canonical_json_bytes_v1(forged).decode("utf-8"), target=target
        )

    drifted_target = deepcopy(target)
    drifted_target["target_cells"][0]["row_label_exact"] += " giả"
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="identity drifted"):
        subject.decode_rollforward_table_repair_text_v1(
            canonical_json_bytes_v1(projected).decode("utf-8"), target=drifted_target
        )


def test_all_twelve_captured_legacy_responses_project_to_the_golden_target_axis() -> None:
    fixture = json.loads(_CAPTURED_RESPONSES.read_bytes())
    assert fixture["format_version"] == "FAMILY13_CAPTURED_TARGET_OBSERVATION_FIXTURE_V1"
    assert fixture["source_authority"] == {
        "attempt_artifact_axis_sha256": (
            "b52a2782c74fcd9d4e3c4fdab1be74787ceab7c1b98e288f5feff4fb7ce7957a"
        ),
        "capture_checkpoint_sha256": (
            "28aa6e3a4e0e4502e21e9193644dbb71585504edfca95ecd04f1d3cafdbb8722"
        ),
        "quarantined_job_status_counts": {"ABSTAINED": 3, "RESOLVED": 3},
        "run_contract_sha256": ("6090d9fb78302eb2af73ed229f6fae1c9a79942709557d414e40ae28b7163c58"),
        "run_result_sha256": ("151651b757fee937b3493a752bb31e2e1c27184b49071f10691087af266c15d7"),
    }
    assert len(fixture["cases"]) == 12
    assert fixture["earliest_projection_valid_case_axis"] == [
        "jobs/job-001/attempt-01-low/table-response.json",
        "jobs/job-002/attempt-01-low/table-response.json",
        "jobs/job-003/attempt-02-medium/table-response.json",
        "jobs/job-004/attempt-01-low/table-response.json",
        "jobs/job-005/attempt-01-low/table-response.json",
        "jobs/job-006/attempt-01-low/table-response.json",
    ]
    projected_by_case = {}
    for case in fixture["cases"]:
        projected = subject.decode_rollforward_table_repair_text_v1(
            canonical_json_bytes_v1(case["response"]).decode("utf-8"),
            target=case["target"],
        )
        projected_by_case[case["case_id"]] = projected
        assert projected["observations"] == case["expected"]["observations"]
        assert projected["projection_sha256"] == case["expected"]["projection_sha256"]
        assert (
            projected["projection_diagnostics"]["ignored_observation_count"]
            == case["expected"]["ignored_observation_count"]
        )
        assert [
            item["normalization_kind"]
            for item in projected["projection_diagnostics"]["normalized_observations"]
        ] == case["expected"]["normalization_kinds"]
    assert any(
        item["normalization_kind"] == "LEGACY_NULL_WITH_DASH_STATE_TO_ASCII_DASH"
        for item in projected_by_case["jobs/job-006/attempt-03-high/table-response.json"][
            "projection_diagnostics"
        ]["normalized_observations"]
    )
    job_five_low = next(
        case
        for case in fixture["cases"]
        if case["case_id"] == "jobs/job-005/attempt-01-low/table-response.json"
    )
    assert job_five_low["response"]["columns"][0]["header_path_exact"] == [
        "Dự phòng\nchung\nTriệu đồng"
    ]
    assert job_five_low["target"]["column_headers_exact"][0] == [
        "Dự phòng chung",
        "Triệu đồng",
    ]


def test_acb_dash_and_ctg_shifted_total_merge_only_exact_changed_cells(corpus: dict) -> None:
    for plan in (corpus["plans"][0], corpus["plans"][-1]):
        page = corpus["pages"][plan["base_page_json_version_id"]]
        repair = _response(page, plan)
        merged, receipt = merge_rollforward_table_repair_v1(
            page,
            plan=plan,
            repair=repair,
            page_store_path=corpus["store"],
            authority=corpus["authority"],
            repair_spec_authority=corpus["repair_spec_authority"],
        )
        change = receipt["changes"][0]
        changed_ids = [item["cell_id"] for item in change["cell_changes"]]
        assert changed_ids == (
            ["r2:c3", "r3:c3", "r6:c3", "r7:c3"]
            if plan["document_ordinal"] != 35
            else ["r3:c2", "r3:c3"]
        )
        assert change["all_other_cells_byte_equal"] is True
        assert change["equation_gate"]["closed_equation_count"] == len(plan["equation_inventory"])
        base_copy = deepcopy(page)
        table = base_copy["sections"][int(plan["section_id"][1:]) - 1]["tables"][
            int(plan["table_id"][1:]) - 1
        ]
        merged_table = merged["sections"][int(plan["section_id"][1:]) - 1]["tables"][
            int(plan["table_id"][1:]) - 1
        ]
        for item in change["cell_changes"]:
            row, column = (int(part[1:]) - 1 for part in item["cell_id"].split(":"))
            table["rows"][row]["values_exact"][column] = merged_table["rows"][row]["values_exact"][
                column
            ]
        assert merged == base_copy


@pytest.mark.parametrize(
    ("attack", "match"),
    [
        ("blank_as_zero", "dash zero"),
        ("partial", "shape or target identity"),
        ("two_unknown_inference", "dash zero"),
    ],
)
def test_atomic_validator_rejects_incomplete_inferred_or_outside_drift(
    corpus: dict, attack: str, match: str
) -> None:
    plan = corpus["plans"][0]
    page = corpus["pages"][plan["base_page_json_version_id"]]
    repair = _response(page, plan)
    if attack == "blank_as_zero":
        repair = _response(page, plan, corrected=False)
    elif attack == "partial":
        repair["rows"][6]["cells"].pop()
    else:
        repair["rows"][1]["cells"][2] = {"source_text": "1", "visual_state": "VALUE"}
        repair["rows"][2]["cells"][2] = {"source_text": "(1)", "visual_state": "VALUE"}
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match=match):
        merge_rollforward_table_repair_v1(
            page,
            plan=plan,
            repair=repair,
            page_store_path=corpus["store"],
            authority=corpus["authority"],
            repair_spec_authority=corpus["repair_spec_authority"],
        )


def test_shifted_total_must_close_both_lane_and_row_equations(corpus: dict) -> None:
    plan = corpus["plans"][-1]
    page = corpus["pages"][plan["base_page_json_version_id"]]
    repair = _response(page, plan)
    repair["rows"][2]["cells"][2] = {"source_text": None, "visual_state": "BLANK"}
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="source-transcribed integer"):
        merge_rollforward_table_repair_v1(
            page,
            plan=plan,
            repair=repair,
            page_store_path=corpus["store"],
            authority=corpus["authority"],
            repair_spec_authority=corpus["repair_spec_authority"],
        )


def test_crop_and_page_store_replay_reject_cross_page_same_shape_source(corpus: dict) -> None:
    plan = corpus["plans"][0]
    image = corpus["images"][plan["base_page_json_version_id"]]
    crop, receipt = crop_rollforward_table_image_v1(
        image,
        plan=plan,
        page_store_path=corpus["store"],
        authority=corpus["authority"],
        repair_spec_authority=corpus["repair_spec_authority"],
    )
    assert sha256(crop).hexdigest() == receipt["crop_image_sha256"]
    assert receipt["prompt_sha256"] == plan["request_contract"]["prompt_sha256"]
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="image bytes"):
        crop_rollforward_table_image_v1(
            corpus["images"][corpus["plans"][1]["base_page_json_version_id"]],
            plan=plan,
            page_store_path=corpus["store"],
            authority=corpus["authority"],
            repair_spec_authority=corpus["repair_spec_authority"],
        )
    attacked = deepcopy(plan)
    attacked["source_binding"] = deepcopy(corpus["plans"][1]["source_binding"])
    attacked["source_logical_name"] = attacked["source_binding"]["source_logical_name"]
    attacked["source_sha256"] = attacked["source_binding"]["source_sha256"]
    attacked["physical_page"] = attacked["source_binding"]["physical_page"]
    attacked["page_evidence_id"] = corpus["plans"][1]["page_evidence_id"]
    _reseal_plan(attacked)
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="frozen page store"):
        validate_rollforward_table_repair_plan_page_store_v1(
            attacked, page_store_path=corpus["store"]
        )


def test_plan_hashes_fail_closed_on_crop_version_and_equation_spec_tamper(corpus: dict) -> None:
    plan = corpus["plans"][0]
    for mutate in (
        lambda value: value["source_binding"]["crop_bbox_pixels_xyxy"].__setitem__(0, 0),
        lambda value: value.__setitem__(
            "base_page_json_version_id", corpus["plans"][1]["base_page_json_version_id"]
        ),
        lambda value: value.__setitem__("repair_spec_sha256", "f" * 64),
        lambda value: value.__setitem__("equation_inventory_sha256", "e" * 64),
    ):
        attacked = deepcopy(plan)
        mutate(attacked)
        with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="identity"):
            validate_rollforward_table_repair_plan_page_store_v1(
                attacked, page_store_path=corpus["store"]
            )


def _resolved_lineage(corpus: dict, plan: dict) -> tuple[dict, dict, bytes, dict, bytes]:
    page = corpus["pages"][plan["base_page_json_version_id"]]
    repair = _response(page, plan)
    merged, receipt = merge_rollforward_table_repair_v1(
        page,
        plan=plan,
        repair=repair,
        page_store_path=corpus["store"],
        authority=corpus["authority"],
        repair_spec_authority=corpus["repair_spec_authority"],
    )
    raw = canonical_json_bytes_v1(repair) + b"\n"
    binding = plan["source_binding"]
    merged_ids = ingest_financial_page_extraction_v1(
        corpus["store"],
        document={
            "source_logical_name": binding["source_logical_name"],
            "source_sha256": binding["source_sha256"],
            "source_size_bytes": binding["source_size_bytes"],
        },
        page={
            "physical_page": binding["physical_page"],
            "image_sha256": binding["image_sha256"],
            "image_size_bytes": binding["image_size_bytes"],
            "pixel_width": binding["pixel_width"],
            "pixel_height": binding["pixel_height"],
            "render_dpi": binding["render_dpi"],
            "media_type": binding["media_type"],
        },
        prompt_variant="region-repair-row-values",
        output_contract_mode="JSON_SCHEMA",
        prompt_sha256=plan["request_contract"]["prompt_sha256"],
        response_schema_sha256=plan["request_contract"]["response_schema_sha256"],
        requested_model="gemini-3.7-flash",
        requested_service_tier="flex",
        thinking_level="high",
        provider_result=replace(_result(), raw_response_bytes=raw),
        page_json=merged,
    )
    lineage = record_page_json_region_repair_v1(
        corpus["store"],
        merged_page_json_version_id=merged_ids["page_json_version_id"],
        receipt=receipt,
    )
    crop, crop_receipt = crop_rollforward_table_image_v1(
        corpus["images"][plan["base_page_json_version_id"]],
        plan=plan,
        page_store_path=corpus["store"],
        authority=corpus["authority"],
        repair_spec_authority=corpus["repair_spec_authority"],
    )
    return receipt, lineage, raw, crop_receipt, crop


def _resolved_low_attempt(corpus: dict, plan: dict) -> tuple[dict, dict, bytes, dict, bytes]:
    receipt, lineage, raw, crop_receipt, crop = _resolved_lineage(corpus, plan)
    attempt = build_rollforward_table_repair_attempt_v1(
        plan=plan,
        **_attempt_context(corpus, plan, crop),
        prior_attempts=[],
        thinking_level="low",
        outcome="RESOLVED",
        observed_page_json_version_id=lineage["observed_page_json_version_id"],
        repair_receipt=receipt,
        crop_receipt=crop_receipt,
        response_artifact_ref=_raw_ref(raw),
        raw_response_bytes=raw,
        validation={"reason_codes": [], "status": "PASS"},
        usage=_usage(),
        provider=_provider(),
        elapsed_seconds="1",
    )
    return attempt, receipt, raw, crop_receipt, crop


def _source_corroborated_attempt(corpus: dict, plan: dict) -> tuple[dict, dict, bytes, dict, bytes]:
    page = corpus["pages"][plan["base_page_json_version_id"]]
    response = _target_response(page, plan, corrected=False)
    receipt = validate_rollforward_table_source_corroboration_v1(
        page,
        plan=plan,
        repair=response,
        page_store_path=corpus["store"],
        authority=corpus["authority"],
        repair_spec_authority=corpus["repair_spec_authority"],
    )
    raw = canonical_json_bytes_v1(response) + b"\n"
    crop, crop_receipt = crop_rollforward_table_image_v1(
        corpus["images"][plan["base_page_json_version_id"]],
        plan=plan,
        page_store_path=corpus["store"],
        authority=corpus["authority"],
        repair_spec_authority=corpus["repair_spec_authority"],
    )
    attempt = build_rollforward_table_repair_attempt_v1(
        plan=plan,
        **_attempt_context(corpus, plan, crop),
        prior_attempts=[],
        thinking_level="low",
        outcome="SOURCE_CORROBORATED_NO_CHANGE",
        observed_page_json_version_id=plan["base_page_json_version_id"],
        repair_receipt=receipt,
        crop_receipt=crop_receipt,
        response_artifact_ref=_raw_ref(raw),
        raw_response_bytes=raw,
        validation={"reason_codes": [], "status": "PASS"},
        usage=_usage(),
        provider=_provider(),
        elapsed_seconds="1",
    )
    return attempt, receipt, raw, crop_receipt, crop


def _all_may_source_corroboration_corpus(corpus: dict) -> dict:
    authority = deepcopy(corpus["authority"])
    authority["table_repair_specs"][-1]["dash_zero_cell_ids"] = []
    authority["table_repair_specs"][-1]["collateral_cell_ids"] = []
    authority["table_repair_specs"][-1]["collateral_equations"] = []
    plans = build_rollforward_table_cell_repair_plans_v1(
        compiled_specs=corpus["compiled"],
        family_sweep=authority["family_sweep"],
        page_store_path=corpus["store"],
        selected_page_json_version_ids=authority["selected_page_json_version_ids"],
        table_repair_specs=authority["table_repair_specs"],
    )
    old_external = corpus["repair_spec_authority"]
    resolver = old_external["source_image_resolver"]
    external = old_external["authority"]
    repair_spec_authority = subject.build_rollforward_table_repair_spec_authority_v1(
        authority_kind=external["authority_kind"],
        authority_ref=external["authority_ref"],
        authority_sha256=external["authority_sha256"],
        source_image_resolver_implementation_path=resolver["implementation_path"],
        source_image_resolver_implementation_sha256=resolver["implementation_sha256"],
        source_image_resolver_implementation_size_bytes=resolver["implementation_size_bytes"],
        source_image_resolver_mupdf_version=resolver["mupdf_version"],
        source_image_resolver_pymupdf_version=resolver["pymupdf_version"],
        table_repair_specs=authority["table_repair_specs"],
        plans=plans,
    )
    return {
        **corpus,
        "authority": authority,
        "plans": plans,
        "repair_spec_authority": repair_spec_authority,
        "specs": authority["table_repair_specs"],
    }


def _reseal_attempt(attempt: dict) -> None:
    material = {key: attempt[key] for key in attempt if key != "attempt_id"}
    attempt["attempt_id"] = "gjfrtav1:attempt:" + canonical_json_sha256_v1(material)


def _overlay_artifacts(corpus: dict, plan: dict, crop: bytes, *responses: bytes) -> dict:
    return {
        "authority": corpus["authority"],
        "repair_spec_authority": corpus["repair_spec_authority"],
        "source_image_artifacts_by_sha256": _artifact_map(
            corpus["images"][plan["base_page_json_version_id"]]
        ),
        "crop_image_artifacts_by_sha256": _artifact_map(crop),
        "response_artifacts_by_sha256": _artifact_map(*responses),
    }


def test_retry_tiers_are_siblings_and_preserve_raw_usage_cost_and_validation(corpus: dict) -> None:
    plan = corpus["plans"][0]
    receipt, lineage, raw, crop_receipt, crop = _resolved_lineage(corpus, plan)
    bad = b'{"partial":true}'
    low = build_rollforward_table_repair_attempt_v1(
        plan=plan,
        **_attempt_context(corpus, plan, crop),
        prior_attempts=[],
        thinking_level="low",
        outcome="RETRYABLE_VALIDATION_FAILURE",
        observed_page_json_version_id=None,
        repair_receipt=None,
        crop_receipt=crop_receipt,
        response_artifact_ref=_raw_ref(bad, "low.json"),
        raw_response_bytes=bad,
        validation={"reason_codes": ["PARTIAL_TABLE"], "status": "FAIL"},
        usage=_usage(),
        provider=_provider(),
        elapsed_seconds="1.25",
    )
    medium = build_rollforward_table_repair_attempt_v1(
        plan=plan,
        **_attempt_context(corpus, plan, crop),
        prior_attempts=[low],
        thinking_level="medium",
        outcome="RETRYABLE_VALIDATION_FAILURE",
        observed_page_json_version_id=None,
        repair_receipt=None,
        crop_receipt=crop_receipt,
        response_artifact_ref=_raw_ref(bad, "medium.json"),
        raw_response_bytes=bad,
        validation={"reason_codes": ["OUTSIDE_ALLOWLIST_DRIFT"], "status": "FAIL"},
        usage=_usage(),
        provider=_provider(),
        elapsed_seconds="2.50",
    )
    high = build_rollforward_table_repair_attempt_v1(
        plan=plan,
        **_attempt_context(corpus, plan, crop),
        prior_attempts=[low, medium],
        thinking_level="high",
        outcome="RESOLVED",
        observed_page_json_version_id=lineage["observed_page_json_version_id"],
        repair_receipt=receipt,
        crop_receipt=crop_receipt,
        response_artifact_ref=_raw_ref(raw, "high.json"),
        raw_response_bytes=raw,
        validation={"reason_codes": [], "status": "PASS"},
        usage=_usage(),
        provider=_provider(),
        elapsed_seconds="3.75",
    )
    assert [item["thinking_level"] for item in (low, medium, high)] == [
        "low",
        "medium",
        "high",
    ]
    assert {item["sibling_base_page_json_version_id"] for item in (low, medium, high)} == {
        plan["base_page_json_version_id"]
    }
    assert high["decoded_response_sha256"] == receipt["repair_response_sha256"]
    assert high["usage"]["actual_cost_usd"] == "0.001234"
    overlay = build_rollforward_table_repair_overlay_v1(
        family_run_id="gjfafstorev1:run:" + "a" * 64,
        plans=[plan],
        attempts=[low, medium, high],
        page_store_path=corpus["store"],
        authority=corpus["authority"],
        repair_spec_authority=corpus["repair_spec_authority"],
        source_image_artifacts_by_sha256=_artifact_map(
            corpus["images"][plan["base_page_json_version_id"]]
        ),
        crop_image_artifacts_by_sha256=_artifact_map(crop),
        response_artifacts_by_sha256=_artifact_map(bad, raw),
    )
    assert overlay["job_status_counts"] == {"ABSTAINED": 0, "RESOLVED": 1}
    assert (
        overlay["replacements"][0]["selected_page_json_version_id"]
        == lineage["merged_page_json_version_id"]
    )


def test_prevalidated_plan_axis_avoids_requery_inside_one_transaction(
    corpus: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = corpus["plans"][0]
    page = corpus["pages"][plan["base_page_json_version_id"]]

    def forbidden_requery(*_args, **_kwargs):
        raise AssertionError("the full selected frontier was queried twice")

    monkeypatch.setattr(subject, "_authoritative_plan_axis", forbidden_requery)
    merged, receipt = merge_rollforward_table_repair_v1(
        page,
        plan=plan,
        repair=_response(page, plan),
        page_store_path=corpus["store"],
        authority=corpus["authority"],
        repair_spec_authority=corpus["repair_spec_authority"],
        _prevalidated_plan_axis=corpus["plans"],
    )
    assert receipt["merged_page_json_sha256"] == canonical_json_sha256_v1(merged)


def test_source_corroborated_ready_job_resolves_without_a_replacement(
    corpus: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    corpus = _all_may_source_corroboration_corpus(corpus)
    plan = corpus["plans"][-1]
    attempt, receipt, raw, _crop_receipt, crop = _source_corroborated_attempt(corpus, plan)
    assert {item["status"] for item in receipt["equation_receipts"]} == {
        "SOURCE_VISIBLE_NONCLOSING"
    }
    assert attempt["repair_id"] is None
    assert attempt["next_status"] == "RESOLVED"
    monkeypatch.setattr(
        subject,
        "_repair_plan_candidate_status_v1",
        lambda *_args, **_kw: "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY",
    )
    overlay = build_rollforward_table_repair_overlay_v1(
        family_run_id="gjfafstorev1:run:" + "a" * 64,
        plans=[plan],
        attempts=[attempt],
        page_store_path=corpus["store"],
        **_overlay_artifacts(corpus, plan, crop, raw),
    )
    assert overlay["job_status_counts"] == {"ABSTAINED": 0, "RESOLVED": 1}
    assert overlay["replacements"] == []


def test_ready_correction_requires_two_matching_validated_observations(
    corpus: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = corpus["plans"][-1]
    receipt, lineage, raw, crop_receipt, crop = _resolved_lineage(corpus, plan)
    monkeypatch.setattr(
        subject,
        "_repair_plan_candidate_status_v1",
        lambda *_args, **_kw: "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY",
    )
    one_shot, _receipt, _raw, _crop, _crop_bytes = _resolved_low_attempt(corpus, plan)
    with pytest.raises(
        GeminiJsonRollforwardTableRepairV1Error, match="lacks two matching observations"
    ):
        build_rollforward_table_repair_overlay_v1(
            family_run_id="gjfafstorev1:run:" + "a" * 64,
            plans=[plan],
            attempts=[one_shot],
            page_store_path=corpus["store"],
            **_overlay_artifacts(corpus, plan, crop, raw),
        )
    pending = build_rollforward_table_repair_attempt_v1(
        plan=plan,
        **_attempt_context(corpus, plan, crop),
        prior_attempts=[],
        thinking_level="low",
        outcome="VALIDATED_OBSERVATION_PENDING_CONSENSUS",
        observed_page_json_version_id=lineage["observed_page_json_version_id"],
        repair_receipt=receipt,
        crop_receipt=crop_receipt,
        response_artifact_ref=_raw_ref(raw, "low.json"),
        raw_response_bytes=raw,
        validation={"reason_codes": [], "status": "PASS"},
        usage=_usage(),
        provider=_provider(),
        elapsed_seconds="1",
    )
    resolved = build_rollforward_table_repair_attempt_v1(
        plan=plan,
        **_attempt_context(corpus, plan, crop),
        prior_attempts=[pending],
        thinking_level="medium",
        outcome="RESOLVED",
        observed_page_json_version_id=lineage["observed_page_json_version_id"],
        repair_receipt=receipt,
        crop_receipt=crop_receipt,
        response_artifact_ref=_raw_ref(raw, "medium.json"),
        raw_response_bytes=raw,
        validation={"reason_codes": [], "status": "PASS"},
        usage=_usage(),
        provider=_provider(),
        elapsed_seconds="1",
    )
    overlay = build_rollforward_table_repair_overlay_v1(
        family_run_id="gjfafstorev1:run:" + "a" * 64,
        plans=[plan],
        attempts=[pending, resolved],
        page_store_path=corpus["store"],
        **_overlay_artifacts(corpus, plan, crop, raw),
    )
    assert overlay["job_status_counts"] == {"ABSTAINED": 0, "RESOLVED": 1}
    assert len(overlay["replacements"]) == 1


def test_attempt_rejects_response_ref_mismatch_and_arbitrary_observed_version(
    corpus: dict,
) -> None:
    plan = corpus["plans"][0]
    receipt, lineage, raw, crop_receipt, crop = _resolved_lineage(corpus, plan)
    wrong_ref = _raw_ref(raw)
    wrong_ref["sha256"] = "f" * 64
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="do not bind"):
        build_rollforward_table_repair_attempt_v1(
            plan=plan,
            **_attempt_context(corpus, plan, crop),
            prior_attempts=[],
            thinking_level="low",
            outcome="RESOLVED",
            observed_page_json_version_id=lineage["observed_page_json_version_id"],
            repair_receipt=receipt,
            crop_receipt=crop_receipt,
            response_artifact_ref=wrong_ref,
            raw_response_bytes=raw,
            validation={"reason_codes": [], "status": "PASS"},
            usage=_usage(),
            provider=_provider(),
            elapsed_seconds="1",
        )
    with pytest.raises(Exception, match="lineage is absent"):
        build_rollforward_table_repair_attempt_v1(
            plan=plan,
            **_attempt_context(corpus, plan, crop),
            prior_attempts=[],
            thinking_level="low",
            outcome="RESOLVED",
            observed_page_json_version_id=corpus["plans"][1]["base_page_json_version_id"],
            repair_receipt=receipt,
            crop_receipt=crop_receipt,
            response_artifact_ref=_raw_ref(raw),
            raw_response_bytes=raw,
            validation={"reason_codes": [], "status": "PASS"},
            usage=_usage(),
            provider=_provider(),
            elapsed_seconds="1",
        )


def test_failed_tier_cannot_chain_from_a_different_job_or_crop(corpus: dict) -> None:
    first, second = corpus["plans"][:2]
    crop_bytes, crop = crop_rollforward_table_image_v1(
        corpus["images"][first["base_page_json_version_id"]],
        plan=first,
        page_store_path=corpus["store"],
        authority=corpus["authority"],
        repair_spec_authority=corpus["repair_spec_authority"],
    )
    bad = b"not json"
    low = build_rollforward_table_repair_attempt_v1(
        plan=first,
        **_attempt_context(corpus, first, crop_bytes),
        prior_attempts=[],
        thinking_level="low",
        outcome="PROVIDER_OR_VALIDATION_FAILURE",
        observed_page_json_version_id=None,
        repair_receipt=None,
        crop_receipt=crop,
        response_artifact_ref=_raw_ref(bad),
        raw_response_bytes=bad,
        validation={"reason_codes": ["INVALID_JSON"], "status": "FAIL"},
        usage=_usage(),
        provider=_provider(),
        elapsed_seconds="1",
    )
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="frontier"):
        build_rollforward_table_repair_attempt_v1(
            plan=second,
            **_attempt_context(corpus, second, crop_bytes),
            prior_attempts=[low],
            thinking_level="medium",
            outcome="PROVIDER_OR_VALIDATION_FAILURE",
            observed_page_json_version_id=None,
            repair_receipt=None,
            crop_receipt=crop,
            response_artifact_ref=_raw_ref(bad),
            raw_response_bytes=bad,
            validation={"reason_codes": ["INVALID_JSON"], "status": "FAIL"},
            usage=_usage(),
            provider=_provider(),
            elapsed_seconds="1",
        )


def test_attempt_rejects_incoherent_token_or_cache_accounting(corpus: dict) -> None:
    plan = corpus["plans"][0]
    crop_bytes, crop = crop_rollforward_table_image_v1(
        corpus["images"][plan["base_page_json_version_id"]],
        plan=plan,
        page_store_path=corpus["store"],
        authority=corpus["authority"],
        repair_spec_authority=corpus["repair_spec_authority"],
    )
    raw = b"not json"
    for field, value, match in (
        ("total_tokens", 901, "token equation"),
        ("cached_input_tokens", 601, "cached input"),
        ("thought_tokens", 301, "token equation"),
    ):
        usage = _usage()
        usage[field] = value
        with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match=match):
            build_rollforward_table_repair_attempt_v1(
                plan=plan,
                **_attempt_context(corpus, plan, crop_bytes),
                prior_attempts=[],
                thinking_level="low",
                outcome="PROVIDER_OR_VALIDATION_FAILURE",
                observed_page_json_version_id=None,
                repair_receipt=None,
                crop_receipt=crop,
                response_artifact_ref=_raw_ref(raw),
                raw_response_bytes=raw,
                validation={"reason_codes": ["INVALID_JSON"], "status": "FAIL"},
                usage=usage,
                provider=_provider(),
                elapsed_seconds="1",
            )


def test_dash_zero_policy_accepts_equivalent_printed_zero_and_preserves_raw_text(
    corpus: dict,
) -> None:
    dash_cells = [
        (plan, item["cell_id"])
        for plan in corpus["plans"]
        for item in plan["cell_allowlist"]
        if item["after_policy"] == "DASH_ZERO"
    ]
    assert len(dash_cells) == 21
    for plan in corpus["plans"]:
        page = corpus["pages"][plan["base_page_json_version_id"]]
        repair = _response(page, plan)
        selected = [item for item in plan["cell_allowlist"] if item["after_policy"] == "DASH_ZERO"]
        for item in selected:
            row, column = (int(part[1:]) - 1 for part in item["cell_id"].split(":"))
            repair["rows"][row]["cells"][column] = {
                "source_text": "0",
                "visual_state": "PRINTED_ZERO",
            }
        merged, receipt = merge_rollforward_table_repair_v1(
            page,
            plan=plan,
            repair=repair,
            page_store_path=corpus["store"],
            authority=corpus["authority"],
            repair_spec_authority=corpus["repair_spec_authority"],
        )
        table = merged["sections"][int(plan["section_id"][1:]) - 1]["tables"][
            int(plan["table_id"][1:]) - 1
        ]
        for item in selected:
            row, column = (int(part[1:]) - 1 for part in item["cell_id"].split(":"))
            assert table["rows"][row]["values_exact"][column] == "0"
        projected = receipt["changes"][0]["response_projection"]
        assert all(
            observation["source_text"] == "0"
            for observation in projected["normalized_observations"]
            if observation["cell_id"] in {item["cell_id"] for item in selected}
        )


def test_audit_crop_rejects_coherent_crop_and_spec_self_reseal(corpus: dict) -> None:
    plan = deepcopy(corpus["plans"][0])
    attacked_spec = deepcopy(corpus["specs"][0])
    attacked_spec["crop_bbox_pixels_xyxy"][0] += 1
    plan["source_binding"]["crop_bbox_pixels_xyxy"] = attacked_spec["crop_bbox_pixels_xyxy"]
    plan["repair_spec_sha256"] = canonical_json_sha256_v1(attacked_spec)
    _reseal_plan(plan)
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="authoritative replay"):
        crop_rollforward_table_image_v1(
            corpus["images"][plan["base_page_json_version_id"]],
            plan=plan,
            page_store_path=corpus["store"],
            authority=corpus["authority"],
            repair_spec_authority=corpus["repair_spec_authority"],
        )


def test_audit_merge_rejects_partial_allowlist_and_cross_candidate_self_reseal(
    corpus: dict,
) -> None:
    original = corpus["plans"][0]
    page = corpus["pages"][original["base_page_json_version_id"]]
    repair = _response(page, original)
    partial = deepcopy(original)
    partial["cell_allowlist"].pop()
    partial["target_ids"] = partial["target_ids"][:-1]
    _reseal_plan(partial)
    crossed = deepcopy(original)
    crossed["candidate_id"] = corpus["plans"][1]["candidate_id"]
    crossed["candidate_semantic_replay_sha256"] = corpus["plans"][1][
        "candidate_semantic_replay_sha256"
    ]
    _reseal_plan(crossed)
    for attacked in (partial, crossed):
        with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="authoritative replay"):
            merge_rollforward_table_repair_v1(
                page,
                plan=attacked,
                repair=repair,
                page_store_path=corpus["store"],
                authority=corpus["authority"],
                repair_spec_authority=corpus["repair_spec_authority"],
            )


def test_audit_attempt_and_overlay_reject_cross_candidate_plan_reseal(corpus: dict) -> None:
    original = corpus["plans"][0]
    attempt, _receipt, raw, crop_receipt, crop = _resolved_low_attempt(corpus, original)
    attacked = deepcopy(original)
    attacked["candidate_id"] = corpus["plans"][1]["candidate_id"]
    attacked["candidate_semantic_replay_sha256"] = corpus["plans"][1][
        "candidate_semantic_replay_sha256"
    ]
    _reseal_plan(attacked)
    bad = b"not json"
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="authoritative replay"):
        build_rollforward_table_repair_attempt_v1(
            plan=attacked,
            **_attempt_context(corpus, original, crop),
            prior_attempts=[],
            thinking_level="low",
            outcome="PROVIDER_OR_VALIDATION_FAILURE",
            observed_page_json_version_id=None,
            repair_receipt=None,
            crop_receipt=crop_receipt,
            response_artifact_ref=_raw_ref(bad),
            raw_response_bytes=bad,
            validation={"reason_codes": ["INVALID_JSON"], "status": "FAIL"},
            usage=_usage(),
            provider=_provider(),
            elapsed_seconds="1",
        )
    attacked_attempt = deepcopy(attempt)
    attacked_attempt["repair_job_id"] = attacked["repair_job_id"]
    _reseal_attempt(attacked_attempt)
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="authoritative replay"):
        build_rollforward_table_repair_overlay_v1(
            family_run_id="gjfafstorev1:run:" + "a" * 64,
            plans=[attacked],
            attempts=[attacked_attempt],
            page_store_path=corpus["store"],
            **_overlay_artifacts(corpus, original, crop, raw),
        )


def test_audit_attempt_and_overlay_bind_actual_crop_pixels(corpus: dict) -> None:
    plan = corpus["plans"][0]
    attempt, _receipt, raw, crop_receipt, crop = _resolved_low_attempt(corpus, plan)
    wrong_crop = crop[:-1] + bytes([crop[-1] ^ 1])
    context = _attempt_context(corpus, plan, wrong_crop)
    bad = b"not json"
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="crop artifact"):
        build_rollforward_table_repair_attempt_v1(
            plan=plan,
            **context,
            prior_attempts=[],
            thinking_level="low",
            outcome="PROVIDER_OR_VALIDATION_FAILURE",
            observed_page_json_version_id=None,
            repair_receipt=None,
            crop_receipt=crop_receipt,
            response_artifact_ref=_raw_ref(bad),
            raw_response_bytes=bad,
            validation={"reason_codes": ["INVALID_JSON"], "status": "FAIL"},
            usage=_usage(),
            provider=_provider(),
            elapsed_seconds="1",
        )
    artifacts = _overlay_artifacts(corpus, plan, crop, raw)
    artifacts["crop_image_artifacts_by_sha256"] = {crop_receipt["crop_image_sha256"]: wrong_crop}
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="artifact bytes"):
        build_rollforward_table_repair_overlay_v1(
            family_run_id="gjfafstorev1:run:" + "a" * 64,
            plans=[plan],
            attempts=[attempt],
            page_store_path=corpus["store"],
            **artifacts,
        )


def test_audit_overlay_recomputes_stored_page_and_rejects_outside_r1c1(corpus: dict) -> None:
    plan = corpus["plans"][0]
    attempt, receipt, raw, _crop_receipt, crop = _resolved_low_attempt(corpus, plan)
    page = corpus["pages"][plan["base_page_json_version_id"]]
    legitimate, _receipt = merge_rollforward_table_repair_v1(
        page,
        plan=plan,
        repair=_response(page, plan),
        page_store_path=corpus["store"],
        authority=corpus["authority"],
        repair_spec_authority=corpus["repair_spec_authority"],
    )
    malicious = deepcopy(legitimate)
    table = malicious["sections"][int(plan["section_id"][1:]) - 1]["tables"][
        int(plan["table_id"][1:]) - 1
    ]
    table["rows"][0]["values_exact"][0] = "999"
    binding = plan["source_binding"]
    malicious_ids = ingest_financial_page_extraction_v1(
        corpus["store"],
        document={
            "source_logical_name": binding["source_logical_name"],
            "source_sha256": binding["source_sha256"],
            "source_size_bytes": binding["source_size_bytes"],
        },
        page={
            "physical_page": binding["physical_page"],
            "image_sha256": binding["image_sha256"],
            "image_size_bytes": binding["image_size_bytes"],
            "pixel_width": binding["pixel_width"],
            "pixel_height": binding["pixel_height"],
            "render_dpi": binding["render_dpi"],
            "media_type": binding["media_type"],
        },
        prompt_variant="region-repair-row-values-audit-outside-diff",
        output_contract_mode="JSON_SCHEMA",
        prompt_sha256=plan["request_contract"]["prompt_sha256"],
        response_schema_sha256=plan["request_contract"]["response_schema_sha256"],
        requested_model="gemini-3.7-flash",
        requested_service_tier="flex",
        thinking_level="high",
        provider_result=replace(_result(), raw_response_bytes=raw),
        page_json=malicious,
    )
    forged_receipt = deepcopy(receipt)
    forged_receipt["merged_page_json_sha256"] = canonical_json_sha256_v1(malicious)
    receipt_material = {key: forged_receipt[key] for key in forged_receipt if key != "repair_id"}
    forged_receipt["repair_id"] = "gjfrrv1:repair:" + canonical_json_sha256_v1(receipt_material)
    malicious_lineage = record_page_json_region_repair_v1(
        corpus["store"],
        merged_page_json_version_id=malicious_ids["page_json_version_id"],
        receipt=forged_receipt,
    )
    forged_attempt = deepcopy(attempt)
    forged_attempt["observed_page_json_version_id"] = malicious_lineage[
        "observed_page_json_version_id"
    ]
    forged_attempt["repair_id"] = malicious_lineage["repair_id"]
    forged_attempt["repair_receipt_sha256"] = malicious_lineage["repair_receipt_sha256"]
    _reseal_attempt(forged_attempt)
    with pytest.raises(
        GeminiJsonRollforwardTableRepairV1Error,
        match="validated correction attempt does not exact-replay|exact page diff",
    ):
        build_rollforward_table_repair_overlay_v1(
            family_run_id="gjfafstorev1:run:" + "a" * 64,
            plans=[plan],
            attempts=[forged_attempt],
            page_store_path=corpus["store"],
            **_overlay_artifacts(corpus, plan, crop, raw),
        )


def test_audit_overlay_rejects_high_only_noncontiguous_ledger(corpus: dict) -> None:
    plan = corpus["plans"][0]
    attempt, _receipt, raw, _crop_receipt, crop = _resolved_low_attempt(corpus, plan)
    high_only = deepcopy(attempt)
    high_only["attempt_ordinal"] = 3
    high_only["thinking_level"] = "high"
    _reseal_attempt(high_only)
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="nonterminal job"):
        build_rollforward_table_repair_overlay_v1(
            family_run_id="gjfafstorev1:run:" + "a" * 64,
            plans=[plan],
            attempts=[high_only],
            page_store_path=corpus["store"],
            **_overlay_artifacts(corpus, plan, crop, raw),
        )


def _rebuild_plans_from_replay_bundle(corpus: dict, replay_bundle: dict) -> list[dict]:
    sources = replay_bundle["compiled_spec_sources"]
    return build_rollforward_table_cell_repair_plans_v1(
        compiled_specs=subject.compile_gemini_json_flat_family_specs_v1(
            sources["topology"], sources["evaluation"], sources["schema_binding"]
        ),
        family_sweep=replay_bundle["family_sweep"],
        page_store_path=corpus["store"],
        selected_page_json_version_ids=replay_bundle["selected_page_json_version_ids"],
        table_repair_specs=replay_bundle["table_repair_specs"],
    )


def test_external_spec_authority_rejects_joint_bbox_bundle_and_plan_tamper(corpus: dict) -> None:
    replay = deepcopy(corpus["authority"])
    replay["table_repair_specs"][0]["crop_bbox_pixels_xyxy"][0] += 1
    attacked = _rebuild_plans_from_replay_bundle(corpus, replay)[0]
    external = corpus["repair_spec_authority"]
    assert external["authenticity"] == {
        "caller_must_verify_and_pin_external_authority": True,
        "caller_must_verify_source_root_and_files": True,
        "self_hash_authenticates_external_authority": False,
    }
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="external repair-spec"):
        crop_rollforward_table_image_v1(
            corpus["images"][attacked["base_page_json_version_id"]],
            plan=attacked,
            page_store_path=corpus["store"],
            authority=replay,
            repair_spec_authority=external,
        )
    for field, value in (
        ("source_logical_name", "forged/source.pdf"),
        ("physical_page", 99),
        ("image_sha256", "f" * 64),
    ):
        forged_external = deepcopy(external)
        forged_external["source_image_bindings"][0][field] = value
        forged_external["source_image_bindings_sha256"] = canonical_json_sha256_v1(
            forged_external["source_image_bindings"]
        )
        material = {
            key: forged_external[key] for key in forged_external if key != "manifest_sha256"
        }
        forged_external["manifest_sha256"] = canonical_json_sha256_v1(material)
        with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="external repair-spec"):
            crop_rollforward_table_image_v1(
                corpus["images"][corpus["plans"][0]["base_page_json_version_id"]],
                plan=corpus["plans"][0],
                page_store_path=corpus["store"],
                authority=corpus["authority"],
                repair_spec_authority=forged_external,
            )
    forged_resolver = deepcopy(external)
    forged_resolver["source_image_resolver"]["implementation_path"] = "forged/renderer.py"
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="external repair-spec"):
        crop_rollforward_table_image_v1(
            corpus["images"][corpus["plans"][0]["base_page_json_version_id"]],
            plan=corpus["plans"][0],
            page_store_path=corpus["store"],
            authority=corpus["authority"],
            repair_spec_authority=forged_resolver,
        )


def test_external_spec_authority_rejects_joint_dash_policy_bundle_and_plan_tamper(
    corpus: dict,
) -> None:
    replay = deepcopy(corpus["authority"])
    replay["table_repair_specs"][0]["dash_zero_cell_ids"].remove("r2:c3")
    attacked = _rebuild_plans_from_replay_bundle(corpus, replay)[0]
    assert (
        next(item for item in attacked["cell_allowlist"] if item["cell_id"] == "r2:c3")[
            "after_policy"
        ]
        == "SIGNED_INTEGER"
    )
    page = corpus["pages"][attacked["base_page_json_version_id"]]
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="external repair-spec"):
        merge_rollforward_table_repair_v1(
            page,
            plan=attacked,
            repair=_response(page, attacked),
            page_store_path=corpus["store"],
            authority=replay,
            repair_spec_authority=corpus["repair_spec_authority"],
        )


def test_external_spec_authority_rejects_joint_ctg_collateral_equation_bundle_and_plan_tamper(
    corpus: dict,
) -> None:
    replay = deepcopy(corpus["authority"])
    ctg_spec = replay["table_repair_specs"][-1]
    ctg_spec["collateral_cell_ids"] = []
    ctg_spec["collateral_equations"] = []
    attacked = _rebuild_plans_from_replay_bundle(corpus, replay)[-1]
    assert "r3:c3" not in {item["cell_id"] for item in attacked["cell_allowlist"]}
    assert len(attacked["equation_inventory"]) == 1
    page = corpus["pages"][attacked["base_page_json_version_id"]]
    with pytest.raises(GeminiJsonRollforwardTableRepairV1Error, match="external repair-spec"):
        merge_rollforward_table_repair_v1(
            page,
            plan=attacked,
            repair=_response(page, attacked),
            page_store_path=corpus["store"],
            authority=replay,
            repair_spec_authority=corpus["repair_spec_authority"],
        )


def test_source_image_resolver_executes_the_exact_manifest_pinned_module() -> None:
    import fitz

    from bctc_ai.evaluation import gemini_json_first_page_render_v1 as renderer_module

    root = Path(subject.__file__).resolve().parents[3]
    implementation = Path(renderer_module.__file__).resolve()
    payload = implementation.read_bytes()
    resolver = {
        "implementation_path": implementation.relative_to(root).as_posix(),
        "implementation_sha256": sha256(payload).hexdigest(),
        "implementation_size_bytes": len(payload),
        "mupdf_version": fitz.mupdf_version,
        "pymupdf_version": fitz.__version__,
    }
    assert (
        subject.validate_rollforward_source_image_resolver_implementation_v1(
            root, resolver=resolver
        )
        == resolver
    )
    drifted_runtime = deepcopy(resolver)
    drifted_runtime["pymupdf_version"] += "-drift"
    with pytest.raises(
        GeminiJsonRollforwardTableRepairV1Error,
        match="runtime pin drifted",
    ):
        subject.validate_rollforward_source_image_resolver_implementation_v1(
            root, resolver=drifted_runtime
        )


def test_source_image_resolver_rejects_cross_root_manifest_pinned_shadow_module(
    tmp_path: Path,
) -> None:
    import fitz

    from bctc_ai.evaluation import gemini_json_first_page_render_v1 as renderer_module

    real_root = Path(subject.__file__).resolve().parents[3]
    real_path = Path(renderer_module.__file__).resolve()
    relative = real_path.relative_to(real_root)
    shadow_path = tmp_path / relative
    shadow_path.parent.mkdir(parents=True)
    shadow_bytes = real_path.read_bytes() + b"\n# coherent pinned shadow module\n"
    shadow_path.write_bytes(shadow_bytes)
    resolver = {
        "implementation_path": relative.as_posix(),
        "implementation_sha256": sha256(shadow_bytes).hexdigest(),
        "implementation_size_bytes": len(shadow_bytes),
        "mupdf_version": fitz.mupdf_version,
        "pymupdf_version": fitz.__version__,
    }
    with pytest.raises(
        GeminiJsonRollforwardTableRepairV1Error,
        match="executed module differs from the pinned file",
    ):
        subject.validate_rollforward_source_image_resolver_implementation_v1(
            tmp_path, resolver=resolver
        )
