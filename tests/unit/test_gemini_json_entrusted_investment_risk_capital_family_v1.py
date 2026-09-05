from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation import (
    gemini_json_entrusted_investment_risk_capital_family_v1 as subject,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    coalesce_gemini_json_multitable_hierarchical_document_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    validate_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "1" * 64
SOURCE_SHA256 = "2" * 64
PAGE_1 = "gfpstorev1:json:" + "3" * 64
PAGE_2 = "gfpstorev1:json:" + "4" * 64
PAGE_3 = "gfpstorev1:json:" + "5" * 64


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_bytes())


def _repair_spec(*repairs: dict) -> dict:
    return {
        "family_id": subject.FAMILY_ID,
        "format_version": subject.SOURCE_REPAIR_FORMAT_VERSION,
        "render_contract": {
            "alpha": False,
            "colorspace": "RGB",
            "format": "PNG",
            "matrix": [2, 2],
            "renderer": "PyMuPDF",
        },
        "repairs": list(repairs),
    }


def _compiled(*repairs: dict) -> dict:
    return subject.compile_gemini_json_entrusted_investment_risk_capital_family_specs_v1(
        _json("config/families/tm-entrusted-investment-risk-capital-topology-v1.json"),
        _json("config/families/tm-entrusted-investment-risk-capital-evaluation-v1.json"),
        _json(
            "config/families/tm-entrusted-investment-risk-capital-schema-binding-v1.json"
        ),
        _repair_spec(*repairs),
    )


def _source_ref(*, page: str = PAGE_1, row: int = 1) -> dict:
    return {
        "hierarchy_path_exact": ["Bằng VND"],
        "label_exact": "Bằng VND",
        "locator": {
            "component_roles": ["VND_RECEIVED_SOURCE"],
            "document_id": DOCUMENT_ID,
            "document_ordinal": 1,
            "fragment_ordinal": 1,
            "page_json_version_id": page,
            "physical_page": 1 if page == PAGE_1 else 2,
            "section_id": "s1",
            "selected_page_ordinal": 1 if page == PAGE_1 else 2,
            "source_logical_name": "fixture.pdf",
            "source_sha256": SOURCE_SHA256,
            "table_id": "t1",
        },
        "money_column_ordinals": [1, 2],
        "row_id": f"r{row}",
        "row_kind": "ITEM",
        "row_ordinal": row,
    }


def _mapping(
    *, role: str, report_norm_id: int, values: list[dict], derived: bool = False
) -> dict:
    material = {
        "report_norm_id": report_norm_id,
        "role": role,
        "row_id": f"corroborated:{role}",
        "source_refs": [_source_ref(), _source_ref()],
        "state": (
            "DECLARED_FAMILY_ROOT_DERIVED_FROM_COMPLETE_TOP_LEVEL_COMPONENT_SUM"
            if derived
            else "SOURCE_OBSERVED_ROLE_ROW"
        ),
        "unit": "MILLION_VND",
        "values": values,
    }
    return {
        **material,
        "item_mapping_id": "gjmthfmv1:item:" + canonical_json_sha256_v1(material),
    }


def _candidate(*mappings: dict) -> dict:
    region = _source_ref()["locator"]
    material = {
        "claim_boundary": "shared",
        "closure_receipt": {
            "equations": [],
            "query_receipt": {},
            "table_receipts": [
                {
                    "region": region,
                    "unit_axis": {"canonical_unit": "MILLION_VND", "complete": True},
                }
            ],
        },
        "component_regions": [region],
        "document_id": DOCUMENT_ID,
        "family_id": subject.FAMILY_ID,
        "mappings": list(mappings),
        "page_json_version_id": PAGE_1,
        "physical_page": 1,
        "reasons": [],
        "section_id": "s1",
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
        "status": subject.READY,
        "table_id": "t1",
    }
    return {
        **material,
        "candidate_id": "gjmthfcv1:candidate:" + canonical_json_sha256_v1(material),
    }


def _cell(value: int | None, source: str | None, state: str) -> dict:
    return {"coefficient": value, "source_text": source, "state": state}


def _primary_page(*, unit: str | None, values: list[str | None]) -> dict:
    return {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            {
                "content_kind": "PRIMARY_STATEMENT",
                "narratives_exact": [],
                "statement_type": "BALANCE_SHEET",
                "tables": [
                    {
                        "columns": [
                            {
                                "header_path_exact": ["31/12/2025"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": ["31/12/2024"],
                                "value_kind": "MONEY",
                            },
                        ],
                        "continuation": "NONE",
                        "rows": [
                            {
                                "hierarchy_path_exact": [
                                    "Vốn tài trợ, ủy thác đầu tư, cho vay mà TCTD chịu rủi ro"
                                ],
                                "label_exact": (
                                    "Vốn tài trợ, ủy thác đầu tư, cho vay mà TCTD chịu rủi ro"
                                ),
                                "row_kind": "ITEM",
                                "values_exact": values,
                            }
                        ],
                        "title_exact": None,
                        "unit_exact": unit,
                    }
                ],
                "title_exact": "BẢNG CÂN ĐỐI KẾ TOÁN",
            }
        ],
        "status": "FINANCIAL_STATEMENT_CONTENT",
    }


def _region(*, page: str = PAGE_1, physical_page: int = 1) -> dict:
    return {
        "component_roles": [],
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "fragment_ordinal": 1,
        "page_json_version_id": page,
        "physical_page": physical_page,
        "section_id": "s1",
        "selected_page_ordinal": physical_page,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
        "table_id": "t1",
    }


def _selected(*, page: str = PAGE_1, physical_page: int = 1) -> dict:
    return {
        key: value
        for key, value in _region(page=page, physical_page=physical_page).items()
        if key not in {"component_roles", "fragment_ordinal", "section_id", "table_id"}
    }


def _note_page(*, amount: str, comparative: str | None = None) -> dict:
    return {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            {
                "content_kind": "NOTE_DETAIL",
                "narratives_exact": [],
                "statement_type": "FOOTNOTE",
                "tables": [
                    {
                        "columns": [
                            {
                                "header_path_exact": ["Cuối kỳ"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": ["Đầu kỳ"],
                                "value_kind": "MONEY",
                            },
                        ],
                        "continuation": "NONE",
                        "rows": [
                            {
                                "hierarchy_path_exact": [
                                    "Vốn nhận tài trợ, ủy thác đầu tư, cho vay bằng VND"
                                ],
                                "label_exact": (
                                    "Vốn nhận tài trợ, ủy thác đầu tư, cho vay bằng VND"
                                ),
                                "row_kind": "ITEM",
                                "values_exact": [amount, comparative],
                            },
                            {
                                "hierarchy_path_exact": [
                                    "Vốn nhận tài trợ, ủy thác đầu tư, cho vay bằng vàng, ngoại tệ"
                                ],
                                "label_exact": (
                                    "Vốn nhận tài trợ, ủy thác đầu tư, cho vay bằng vàng, ngoại tệ"
                                ),
                                "row_kind": "ITEM",
                                "values_exact": ["-", comparative],
                            },
                            {
                                "hierarchy_path_exact": [None],
                                "label_exact": None,
                                "row_kind": "TOTAL",
                                "values_exact": [amount, comparative],
                            },
                        ],
                        "title_exact": None,
                        "unit_exact": None,
                    }
                ],
                "title_exact": (
                    "Vốn tài trợ, ủy thác đầu tư, cho vay TCTD chịu rủi ro"
                ),
            }
        ],
        "status": "FINANCIAL_STATEMENT_CONTENT",
    }


def _note_region() -> dict:
    return {
        **_region(page=PAGE_3, physical_page=3),
        "component_roles": ["OTHER_RECEIVED_SOURCE", "VND_RECEIVED_SOURCE"],
    }


def test_compile_accepts_vnd_and_family_aliases() -> None:
    compiled = _compiled()

    assert {
        item["canonical_unit"]
        for item in compiled["unit_bindings"]
        if item["accepted"] is True
    } == {"MILLION_VND", "VND"}
    assert subject._is_parent_label(
        "Vốn tài trợ, ủy thác đầu tư, cho vay mà TCTD chịu rủi ro",
        compiled_specs=compiled,
    )
    assert subject._accepted_explicit_unit(
        "Đơn vị tính: triệu đồng", compiled_specs=compiled
    ) == ("MILLION_VND", 6)
    assert compiled[
        "entrusted_investment_risk_capital_owner_fenced_short_currency_aliases"
    ] == {
        "FOREIGN_CURRENCY_RECEIVED_SOURCE": ["Bằng ngoại tệ", "Bằng ngoại tệ (i)"],
        "VND_RECEIVED_SOURCE": ["Bằng VND"],
    }


def test_short_currency_rows_without_exact_family_owner_are_not_observed() -> None:
    page = _note_page(amount="7", comparative="6")
    page["sections"][0]["title_exact"] = "TIỀN GỬI CỦA KHÁCH HÀNG"
    page["sections"][0]["tables"][0]["title_exact"] = (
        "Thuyết minh theo loại tiền gửi"
    )
    page["sections"][0]["tables"][0]["rows"][0]["label_exact"] = "Bằng VND"
    page["sections"][0]["tables"][0]["rows"][0]["hierarchy_path_exact"] = [
        "Bằng VND"
    ]
    page["sections"][0]["tables"][0]["rows"][1]["label_exact"] = "Bằng ngoại tệ"
    page["sections"][0]["tables"][0]["rows"][1]["hierarchy_path_exact"] = [
        "Bằng ngoại tệ"
    ]

    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[{**_selected(), "page_json": page}],
        compiled_specs=_compiled(),
    )

    assert cluster["status"] == subject.NOT_OBSERVED
    assert cluster["component_regions"] == []


def test_partial_source_blank_is_typed_null_and_does_not_erase_visible_lane() -> None:
    detail = _mapping(
        role="VND_RECEIVED_SOURCE",
        report_norm_id=1094,
        values=[
            _cell(7, "7", "RAW_SIGNED_INTEGER"),
            _cell(0, None, "INFERRED_BLANK_ZERO_IF_EQUATION_EXACT"),
        ],
    )
    root = _mapping(
        role="FAMILY_ROOT_TOTAL",
        report_norm_id=1092,
        derived=True,
        values=[
            _cell(7, None, "EXACT_COMPLETE_TOP_LEVEL_COMPONENT_SUM"),
            _cell(0, None, "EXACT_COMPLETE_TOP_LEVEL_COMPONENT_SUM"),
        ],
    )

    result = subject._reseal_note_candidate(
        _candidate(detail, root), compiled_specs=_compiled()
    )

    by_role = {mapping["role"]: mapping for mapping in result["mappings"]}
    assert [cell["coefficient"] for cell in by_role["VND_RECEIVED_SOURCE"]["values"]] == [
        7,
        None,
    ]
    assert by_role["VND_RECEIVED_SOURCE"]["values"][1]["state"] == "BLANK_SOURCE_CELL"
    assert [cell["coefficient"] for cell in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [
        7,
        None,
    ]
    assert by_role["FAMILY_ROOT_TOTAL"]["values"][0]["state"].startswith("DERIVED_")
    assert by_role["FAMILY_ROOT_TOTAL"]["values"][1]["state"] == (
        "DERIVED_INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"
    )
    validate_source_observation_mapping_contract_v1(result)


def test_exact_total_closure_never_turns_all_blank_child_into_zero_mapping() -> None:
    blank_child = _mapping(
        role="VND_RECEIVED_SOURCE",
        report_norm_id=1094,
        values=[
            _cell(0, None, "INFERRED_BLANK_ZERO_IF_EQUATION_EXACT"),
            _cell(0, None, "INFERRED_BLANK_ZERO_IF_EQUATION_EXACT"),
        ],
    )
    derived_root = _mapping(
        role="FAMILY_ROOT_TOTAL",
        report_norm_id=1092,
        derived=True,
        values=[
            _cell(0, None, "EXACT_COMPLETE_TOP_LEVEL_COMPONENT_SUM"),
            _cell(0, None, "EXACT_COMPLETE_TOP_LEVEL_COMPONENT_SUM"),
        ],
    )

    result = subject._reseal_note_candidate(
        _candidate(blank_child, derived_root), compiled_specs=_compiled()
    )

    assert result["status"] == subject.UNRESOLVED
    assert result["mappings"] == []
    assert result["reasons"] == ["ALL_MAPPABLE_SOURCE_ROLES_ARE_BLANK"]
    validate_source_observation_mapping_contract_v1(result)


def test_primary_result_preserves_one_blank_lane_as_typed_null() -> None:
    page = _primary_page(unit="Triệu đồng", values=["7", None])

    result = subject._root_candidate(
        regions=[_region()],
        page_json_by_version={PAGE_1: page},
        selected_page_axis=[_selected()],
        compiled_specs=_compiled(),
    )

    assert result["status"] == subject.READY
    assert [cell["coefficient"] for cell in result["mappings"][0]["values"]] == [7, None]
    assert result["mappings"][0]["values"][1]["state"] == "BLANK_SOURCE_CELL"
    validate_source_observation_mapping_contract_v1(result)


def test_primary_result_omits_an_all_blank_role() -> None:
    page = _primary_page(unit="Triệu đồng", values=[None, None])

    result = subject._root_candidate(
        regions=[_region()],
        page_json_by_version={PAGE_1: page},
        selected_page_axis=[_selected()],
        compiled_specs=_compiled(),
    )

    assert result["status"] == subject.UNRESOLVED
    assert result["mappings"] == []
    assert "PRIMARY_SOURCE_RESULT_ALL_LANES_BLANK" in result["reasons"]


def test_duplicate_scaled_primary_presentations_select_highest_precision_once() -> None:
    million = _primary_page(unit="Triệu đồng", values=["1", "2"])
    vnd = _primary_page(unit="VND", values=["1.000.000", "2.000.000"])
    regions = [_region(), _region(page=PAGE_2, physical_page=2)]

    selected, receipt = subject._select_root_regions(
        regions=regions,
        pages={PAGE_1: million, PAGE_2: vnd},
        selected_page_axis=[_selected(), _selected(page=PAGE_2, physical_page=2)],
        compiled_specs=_compiled(),
        repairs=[],
    )

    assert [region["page_json_version_id"] for region in selected] == [PAGE_2]
    assert receipt["rule"] == (
        "EXACT_SCALED_DUPLICATE_CORROBORATION_HIGHEST_PRECISION_SOURCE_UNIT"
    )


def test_noncontiguous_prior_unit_cannot_seal_primary_result() -> None:
    prior = _primary_page(unit="VND", values=["1", "2"])
    current = _primary_page(unit=None, values=["3", "4"])
    current_region = _region(page=PAGE_2, physical_page=3)

    result = subject._root_candidate(
        regions=[current_region],
        page_json_by_version={PAGE_1: prior, PAGE_2: current},
        selected_page_axis=[_selected(), _selected(page=PAGE_2, physical_page=3)],
        compiled_specs=_compiled(),
    )

    assert result["status"] == subject.UNRESOLVED
    assert "PRIMARY_SOURCE_RESULT_UNIT_AXIS_INCOMPLETE" in result["reasons"]


def test_unitless_note_uses_unique_exact_primary_result_unit_and_keeps_blank() -> None:
    pages = {
        PAGE_1: _primary_page(unit="VND", values=["7,000,000", "-"]),
        PAGE_2: _primary_page(unit="Triệu đồng", values=["7", "-"]),
        PAGE_3: _note_page(amount="7"),
    }
    region = _note_region()
    selected = [
        _selected(),
        _selected(page=PAGE_2, physical_page=2),
        _selected(page=PAGE_3, physical_page=3),
    ]

    result = subject.evaluate_gemini_json_entrusted_investment_risk_capital_family_cluster_v1(
        regions=[region],
        page_json_by_version=pages,
        selected_page_axis=selected,
        compiled_specs=_compiled(),
        query_receipt=(
            subject.build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
                [region]
            )
        ),
    )

    assert result["status"] == subject.READY
    assert {mapping["unit"] for mapping in result["mappings"]} == {"MILLION_VND"}
    assert all(mapping["values"][1]["coefficient"] is None for mapping in result["mappings"])
    receipt = result["closure_receipt"][
        "entrusted_investment_risk_capital_adapter_receipt"
    ]["primary_source_unit_receipt"]
    assert receipt["matched_observed_lane_ordinals"] == [1]
    assert receipt["primary_unit_receipt"]["canonical_unit"] == "MILLION_VND"
    validate_source_observation_mapping_contract_v1(result)


def test_unitless_note_primary_result_value_mismatch_stays_unresolved() -> None:
    pages = {
        PAGE_1: _primary_page(unit="VND", values=["7,000,000", "-"]),
        PAGE_2: _primary_page(unit="Triệu đồng", values=["7", "-"]),
        PAGE_3: _note_page(amount="8"),
    }
    region = _note_region()

    result = subject.evaluate_gemini_json_entrusted_investment_risk_capital_family_cluster_v1(
        regions=[region],
        page_json_by_version=pages,
        selected_page_axis=[
            _selected(),
            _selected(page=PAGE_2, physical_page=2),
            _selected(page=PAGE_3, physical_page=3),
        ],
        compiled_specs=_compiled(),
        query_receipt=(
            subject.build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
                [region]
            )
        ),
    )

    assert result["status"] == subject.UNRESOLVED
    assert result["mappings"] == []
    assert result["reasons"] == ["FRAGMENT_PERIOD_OR_UNIT_AXIS_NOT_LOCALLY_USABLE"]


def _repair(*, before: str | None = None, after: str = "-") -> dict:
    material = {
        "after_exact": after,
        "before_exact": before,
        "column_ordinal": 2,
        "locator": {
            "page_json_version_id": PAGE_1,
            "physical_page": 1,
            "row_ordinal": 1,
            "section_id": "s1",
            "table_id": "t1",
        },
        "pdf_page_render_sha256": "5" * 64,
        "repair_kind": "MONEY_CELL_VISIBLE_DASH",
        "source_sha256": SOURCE_SHA256,
    }
    return {
        **material,
        "repair_id": "geircfav1:repair:" + canonical_json_sha256_v1(material),
    }


def test_authenticated_dash_repair_is_exactly_bound_to_source_page_table_row_cell() -> None:
    repair = _repair()
    compiled = _compiled(repair)
    page = _primary_page(unit="Triệu đồng", values=["7", None])

    pages, receipts = subject._document_repairs(
        source_sha256=SOURCE_SHA256,
        page_json_by_version={PAGE_1: page},
        compiled_specs=compiled,
    )

    assert pages[PAGE_1]["sections"][0]["tables"][0]["rows"][0]["values_exact"] == [
        "7",
        "-",
    ]
    assert [item["repair_id"] for item in receipts] == [repair["repair_id"]]

    drifted = copy.deepcopy(page)
    drifted["sections"][0]["tables"][0]["rows"][0]["values_exact"][1] = "0"
    with pytest.raises(subject.GeminiJsonEntrustedInvestmentRiskCapitalFamilyV1Error):
        subject._document_repairs(
            source_sha256=SOURCE_SHA256,
            page_json_by_version={PAGE_1: drifted},
            compiled_specs=compiled,
        )


def test_source_repair_identity_tampering_fails_closed() -> None:
    repair = _repair()
    repair["locator"]["row_ordinal"] = 2

    with pytest.raises(
        subject.GeminiJsonEntrustedInvestmentRiskCapitalFamilyV1Error,
        match="identity drifted",
    ):
        _compiled(repair)
