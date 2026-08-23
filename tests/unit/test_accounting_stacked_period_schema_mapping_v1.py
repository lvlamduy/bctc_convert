from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation import accounting_stacked_period_schema_mapping_v1 as mapping_v1
from bctc_ai.evaluation.accounting_stacked_period_lane_axis_v1 import (
    build_accounting_stacked_period_lane_axis_v1,
)
from bctc_ai.evaluation.accounting_stacked_period_schema_mapping_v1 import (
    AccountingStackedPeriodSchemaMappingV1Error,
    build_accounting_stacked_period_schema_mapping_v1,
    validate_accounting_stacked_period_schema_mapping_replay_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
TOPOLOGY = json.loads(
    (ROOT / "config/families/tm-derivative-financial-instruments-topology-v1.json").read_text(
        encoding="utf-8"
    )
)
LAYOUT = json.loads(
    (ROOT / "config/families/tm-derivative-financial-instruments-layout-v1.json").read_text(
        encoding="utf-8"
    )
)
BINDING = json.loads(
    (ROOT / "config/families/tm-derivative-financial-instruments-schema-binding-v1.json").read_text(
        encoding="utf-8"
    )
)
CHALLENGER_EVIDENCE = json.loads(
    (
        ROOT
        / "docs/experiments/E-0162-family-first-derivative-hosted-gemma4-numeric-challenger-v1.json"
    ).read_text(encoding="utf-8")
)
SCHEMA = [
    json.loads(line)
    for line in (ROOT / "reference/schemas/schema_graph.jsonl")
    .read_text(encoding="utf-8")
    .splitlines()
    if line
]


def _line(
    text: str,
    bbox: list[int],
    ordinal: int,
    *,
    numeric_text: str | None = None,
) -> dict[str, object]:
    return {
        "bbox": bbox,
        "crop_ref": {
            "path": f"crop/{ordinal}.png",
            "sha256": f"{ordinal + 1:064x}",
            "size_bytes": 1,
        },
        "line_ordinal": ordinal,
        "numeric_recognition": {
            "raw_prediction": text if numeric_text is None else numeric_text,
            "reader_score": 0.99,
        },
        "sample_id": f"sample-{ordinal}",
        "vietocr_text": text,
    }


def _pages() -> list[dict[str, object]]:
    raw = [
        ("CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÁC TÀI SẢN TÀI CHÍNH KHÁC", [40, 30, 900, 60]),
        ("Tại ngày 30/06/2026", [700, 80, 1050, 110]),
        ("Tổng giá trị của hợp đồng", [770, 120, 960, 150]),
        ("Tài sản", [1010, 120, 1110, 150]),
        ("Công nợ", [1210, 120, 1320, 150]),
        ("Tổng cộng", [1410, 120, 1530, 150]),
        ("Giao dịch kỳ hạn tiền tệ", [50, 220, 500, 250]),
        ("1.000", [820, 220, 920, 250]),
        ("20", [1030, 220, 1100, 250]),
        ("(5)", [1230, 220, 1310, 250]),
        ("15", [1430, 220, 1500, 250]),
        ("Giao dịch hoán đổi tiền tệ", [50, 270, 530, 300]),
        ("2.000", [820, 270, 920, 300]),
        ("30", [1030, 270, 1100, 300]),
        ("(10)", [1230, 270, 1310, 300]),
        ("20", [1430, 270, 1500, 300]),
        ("Tại ngày 31/12/2025", [700, 400, 1050, 430]),
        ("Tổng giá trị của hợp đồng", [770, 440, 960, 470]),
        ("Tài sản", [1010, 440, 1110, 470]),
        ("Công nợ", [1210, 440, 1320, 470]),
        ("Tổng cộng", [1410, 440, 1530, 470]),
        ("Giao dịch kỳ hạn tiền tệ", [50, 520, 500, 550]),
        ("900", [820, 520, 920, 550]),
        ("10", [1030, 520, 1100, 550]),
        ("(2)", [1230, 520, 1310, 550]),
        ("8", [1430, 520, 1500, 550]),
        ("Giao dịch hoán đổi tiền tệ", [50, 570, 530, 600]),
        ("1.800", [820, 570, 920, 600]),
        ("25", [1030, 570, 1100, 600]),
        ("(5)", [1230, 570, 1310, 600]),
        ("20", [1430, 570, 1500, 600]),
        ("Cho vay khách hàng", [50, 700, 500, 730]),
    ]
    return [
        {
            "lines": [_line(text, bbox, ordinal) for ordinal, (text, bbox) in enumerate(raw)],
            "page_sequence": 1,
            "page_width": 1600,
        }
    ]


def _horizontal_pages() -> list[dict[str, object]]:
    raw = [
        ("CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÁC TÀI SẢN TÀI CHÍNH KHÁC", [40, 30, 900, 60]),
        ("31/12/2025", [540, 80, 760, 110]),
        ("31/12/2024", [1040, 80, 1260, 110]),
        ("Giá trị", [500, 120, 650, 145]),
        ("hợp đồng", [500, 146, 650, 171]),
        ("Giá trị", [735, 120, 865, 145]),
        ("ghi sổ", [735, 146, 865, 171]),
        ("Giá trị", [1000, 120, 1150, 145]),
        ("hợp đồng", [1000, 146, 1150, 171]),
        ("Giá trị", [1235, 120, 1365, 145]),
        ("ghi sổ", [1235, 146, 1365, 171]),
        ("Hợp đồng hoán đổi tiền tệ", [50, 220, 500, 250]),
        ("204.012.086", [535, 220, 665, 250]),
        ("384.075", [755, 220, 845, 250]),
        ("340.865.305", [1035, 220, 1165, 250]),
        ("1.328.364", [1250, 220, 1350, 250]),
        ("Hợp đồng kỳ hạn tiền tệ", [50, 280, 500, 310]),
        ("(199.035)", [535, 280, 665, 310]),
        ("(9.157)", [755, 280, 845, 310]),
        ("(16.245.514)", [1035, 280, 1165, 310]),
        ("(13.930)", [1250, 280, 1350, 310]),
        ("Cho vay khách hàng", [50, 400, 500, 430]),
    ]
    return [
        {
            "lines": [_line(text, bbox, ordinal) for ordinal, (text, bbox) in enumerate(raw)],
            "page_sequence": 1,
            "page_width": 1600,
        }
    ]


def _topology_pages(pages: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "lines": [
                {
                    "bbox": line["bbox"],
                    "source_line_index": line["line_ordinal"],
                    "source_text": None,
                    "vietocr_text": line["vietocr_text"],
                }
                for line in pages[0]["lines"]
            ],
            "page_sequence": 1,
        }
    ]


def _axis(pages: list[dict[str, object]]) -> dict[str, object]:
    scan = topology_v1.build_accounting_family_topology_scan_v1(_topology_pages(pages), TOPOLOGY)
    assert scan["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    return build_accounting_stacked_period_lane_axis_v1(pages, TOPOLOGY, scan["regions"][0], LAYOUT)


def _mapping(pages: list[dict[str, object]]) -> dict[str, object]:
    axis = _axis(pages)
    return build_accounting_stacked_period_schema_mapping_v1(
        pages, TOPOLOGY, LAYOUT, axis, BINDING, SCHEMA
    )


def _challenger(line: dict[str, object], surface: str) -> dict[str, object]:
    return {
        "crop_ref": copy.deepcopy(line["crop_ref"]),
        "extracted_numeric_surface": surface,
        "extraction_json_path": ["table", "rows", 0, "value"],
        "format_version": "HOSTED_GEMMA4_FULL_PAGE_NUMERIC_CHALLENGER_OBSERVATION_V1",
        "full_page_render_ref": {
            "dpi": 200,
            "pixel_height": 2339,
            "pixel_width": 1654,
            "sha256": "a" * 64,
            "size_bytes": 123,
        },
        "inference": {
            "fresh_context": True,
            "max_output_tokens": 32768,
            "temperature": 0,
            "thinking_level": "MINIMAL",
        },
        "model": "gemma-4-26b-a4b-it",
        "prompt_sha256": "b" * 64,
        "response_ref": {"sha256": "c" * 64, "size_bytes": 456},
        "sample_id": line["sample_id"],
        "state": "COMPLETED_STATELESS_FULL_PAGE_JSON_CHALLENGE",
    }


def test_exact_equations_bind_only_schema_eligible_period_lane_roles() -> None:
    mapping = _mapping(_pages())
    assert mapping["status"] == "READY_FOR_SCOPE_UNIT_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
    assert mapping["metrics"] == {
        "accounting_check_count": 8,
        "corroborated_check_count": 4,
        "mapping_proposal_count": 12,
        "numeric_challenger_rescue_count": 0,
        "unresolved_cell_count": 0,
        "vetoed_check_count": 0,
    }
    ids = {
        (item["period_role"], item["lane_role"], item["role"]): item["report_norm_id"]
        for item in mapping["mapping_proposals"]
    }
    assert ids[("CURRENT_PERIOD", "CONTRACT_VALUE", "FORWARD_CURRENCY")] == 634
    assert ids[("CURRENT_PERIOD", "ASSET_CARRYING_VALUE", "FORWARD_CURRENCY")] == 662
    assert ids[("CURRENT_PERIOD", "LIABILITY_CARRYING_VALUE", "FORWARD_CURRENCY")] == 690
    assert ids[("COMPARATIVE_PERIOD", "CONTRACT_VALUE", "FORWARD_CURRENCY")] == 648
    assert ids[("COMPARATIVE_PERIOD", "ASSET_CARRYING_VALUE", "FORWARD_CURRENCY")] == 676
    assert ids[("COMPARATIVE_PERIOD", "LIABILITY_CARRYING_VALUE", "FORWARD_CURRENCY")] == 704
    assert all(item["lane_role"] != "NET_VALUE" for item in mapping["mapping_proposals"])


def test_hosted_full_page_challenger_must_join_one_other_numeric_reader() -> None:
    pages = _pages()
    contract = pages[0]["lines"][7]
    contract["numeric_recognition"]["raw_prediction"] = "36.046"
    contract["vietocr_text"] = "38.046"
    axis = _axis(pages)
    mapping = build_accounting_stacked_period_schema_mapping_v1(
        pages,
        TOPOLOGY,
        LAYOUT,
        axis,
        BINDING,
        SCHEMA,
        [_challenger(contract, "36.046")],
    )
    rescued = next(
        item
        for item in mapping["mapping_proposals"]
        if item["numeric_cell"]["sample_id"] == contract["sample_id"]
    )
    assert rescued["numeric_cell"]["numeric_value"] == {"coefficient": 36046, "scale": 0}
    assert rescued["numeric_cell"]["numeric_consensus_status"] == ("PPOCR_GEMMA4_EXACT_AGREEMENT")
    assert mapping["metrics"]["numeric_challenger_rescue_count"] == 1

    rejected = build_accounting_stacked_period_schema_mapping_v1(
        pages,
        TOPOLOGY,
        LAYOUT,
        axis,
        BINDING,
        SCHEMA,
        [_challenger(contract, "39.046")],
    )
    assert not any(
        item["numeric_cell"]["sample_id"] == contract["sample_id"]
        for item in rejected["mapping_proposals"]
    )


def test_tracked_hosted_challenger_evidence_is_hash_and_crop_bound() -> None:
    material = copy.deepcopy(CHALLENGER_EVIDENCE)
    evaluation_id = material.pop("evaluation_id")
    assert evaluation_id == "derivativegemma4v1:evaluation:" + canonical_json_sha256_v1(material)
    observations = CHALLENGER_EVIDENCE["observations"]
    source_lines = {
        item["sample_id"]: {"crop_ref": copy.deepcopy(item["crop_ref"])} for item in observations
    }
    assert set(mapping_v1._challengers(observations, source_lines)) == {
        "sample-000197648",
        "sample-000415290",
        "sample-000543238",
    }
    forged = copy.deepcopy(observations)
    forged[0]["crop_ref"]["sha256"] = "0" * 64
    with pytest.raises(AccountingStackedPeriodSchemaMappingV1Error):
        mapping_v1._challengers(forged, source_lines)


def test_vietocr_and_hosted_challenger_rescue_noninteger_primary_money_token() -> None:
    pages = _pages()
    contract = pages[0]["lines"][7]
    contract["numeric_recognition"]["raw_prediction"] = "250.20"
    contract["vietocr_text"] = "250.520"
    axis = _axis(pages)
    mapping = build_accounting_stacked_period_schema_mapping_v1(
        pages,
        TOPOLOGY,
        LAYOUT,
        axis,
        BINDING,
        SCHEMA,
        [_challenger(contract, "250.520")],
    )
    rescued = next(
        item
        for item in mapping["mapping_proposals"]
        if item["numeric_cell"]["sample_id"] == contract["sample_id"]
    )
    assert rescued["numeric_cell"]["numeric_value"] == {"coefficient": 250520, "scale": 0}
    assert rescued["numeric_cell"]["numeric_consensus_status"] == (
        "VIETOCR_GEMMA4_EXACT_AGREEMENT_PRIMARY_NONINTEGER_OR_INVALID"
    )


def test_visible_equation_mismatch_vetoes_only_participating_cells() -> None:
    pages = _pages()
    line = pages[0]["lines"][10]
    line["vietocr_text"] = "16"
    line["numeric_recognition"]["raw_prediction"] = "16"
    mapping = _mapping(pages)
    assert mapping["metrics"]["vetoed_check_count"] == 2
    current_forward = [
        item
        for item in mapping["mapping_proposals"]
        if item["period_role"] == "CURRENT_PERIOD" and item["role"] == "FORWARD_CURRENCY"
    ]
    assert [item["lane_role"] for item in current_forward] == ["CONTRACT_VALUE"]
    assert any(
        item["reason"] == "VISIBLE_ACCOUNTING_EQUATION_VETOED_CELL"
        for item in mapping["unresolved_cells"]
    )


def test_mixed_separator_needs_same_crop_peer_and_exact_equation() -> None:
    pages = _pages()
    asset = pages[0]["lines"][8]
    liability = pages[0]["lines"][9]
    net = pages[0]["lines"][10]
    asset["numeric_recognition"]["raw_prediction"] = "1.460,873"
    asset["vietocr_text"] = "1.460.873"
    liability["numeric_recognition"]["raw_prediction"] = "(873)"
    liability["vietocr_text"] = "(873)"
    net["numeric_recognition"]["raw_prediction"] = "1.460.000"
    net["vietocr_text"] = "1.460.000"
    mapping = _mapping(pages)
    rescued = next(
        item
        for item in mapping["mapping_proposals"]
        if item["period_role"] == "CURRENT_PERIOD"
        and item["role"] == "FORWARD_CURRENCY"
        and item["lane_role"] == "ASSET_CARRYING_VALUE"
    )
    assert rescued["numeric_cell"]["mixed_separator_rescued"] is True
    assert rescued["numeric_cell"]["numeric_value"] == {"coefficient": 1460873, "scale": 0}

    net["numeric_recognition"]["raw_prediction"] = "1.460.001"
    net["vietocr_text"] = "1.460.001"
    vetoed = _mapping(pages)
    assert not any(
        item["numeric_cell"]["sample_id"] == asset["sample_id"]
        for item in vetoed["mapping_proposals"]
    )


def test_visible_dash_is_zero_but_reader_disagreement_is_unresolved() -> None:
    pages = _pages()
    for ordinal in (8, 9, 10):
        pages[0]["lines"][ordinal]["numeric_recognition"]["raw_prediction"] = "-"
        pages[0]["lines"][ordinal]["vietocr_text"] = "-"
    mapping = _mapping(pages)
    dash_cells = [
        item["numeric_cell"]
        for item in mapping["mapping_proposals"]
        if item["period_role"] == "CURRENT_PERIOD"
        and item["role"] == "FORWARD_CURRENCY"
        and item["lane_role"] in {"ASSET_CARRYING_VALUE", "LIABILITY_CARRYING_VALUE"}
    ]
    assert len(dash_cells) == 2
    assert all(item["numeric_value"] == {"coefficient": 0, "scale": 0} for item in dash_cells)
    assert all(item["source_zero_kind"] == "VISIBLE_DASH" for item in dash_cells)

    pages[0]["lines"][8]["vietocr_text"] = "7"
    disagreement = _mapping(pages)
    assert not any(
        item["numeric_cell"]["sample_id"] == pages[0]["lines"][8]["sample_id"]
        for item in disagreement["mapping_proposals"]
    )


def test_exact_replay_rejects_coordinated_mapping_rehash() -> None:
    pages = _pages()
    axis = _axis(pages)
    mapping = build_accounting_stacked_period_schema_mapping_v1(
        pages, TOPOLOGY, LAYOUT, axis, BINDING, SCHEMA
    )
    assert (
        validate_accounting_stacked_period_schema_mapping_replay_v1(
            mapping, pages, TOPOLOGY, LAYOUT, axis, BINDING, SCHEMA
        )
        == mapping
    )
    forged = copy.deepcopy(mapping)
    forged["mapping_proposals"][0]["report_norm_id"] = 635
    material = copy.deepcopy(forged)
    material.pop("mapping_id")
    forged["mapping_id"] = "aspsmv1:mapping:" + canonical_json_sha256_v1(material)
    with pytest.raises(AccountingStackedPeriodSchemaMappingV1Error):
        validate_accounting_stacked_period_schema_mapping_replay_v1(
            forged, pages, TOPOLOGY, LAYOUT, axis, BINDING, SCHEMA
        )


def test_binding_config_is_bank_page_year_blind_and_schema_ids_exist() -> None:
    serialized = json.dumps(BINDING, ensure_ascii=False).lower()
    for forbidden in (
        "acb",
        "mbb",
        "vpb",
        "hdb",
        "vcb",
        "ctg",
        "bid",
        "vib",
        "page",
        "2025",
        "2026",
    ):
        assert forbidden not in serialized
    schema_ids = {node["schema_id"] for node in SCHEMA}
    assert all(
        identity in schema_ids
        for binding in BINDING["mapping_bindings"]
        for identity in binding["report_norm_id_by_source_role"].values()
    )


def test_horizontal_signed_carrying_lane_maps_by_exact_sign_only() -> None:
    mapping = _mapping(_horizontal_pages())
    assert mapping["status"] == "READY_FOR_SCOPE_UNIT_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
    by_sample = {item["numeric_cell"]["sample_id"]: item for item in mapping["mapping_proposals"]}
    assert by_sample["sample-13"]["lane_role"] == "ASSET_CARRYING_VALUE"
    assert by_sample["sample-13"]["report_norm_id"] == 663
    assert by_sample["sample-15"]["lane_role"] == "ASSET_CARRYING_VALUE"
    assert by_sample["sample-15"]["report_norm_id"] == 677
    assert by_sample["sample-18"]["lane_role"] == "LIABILITY_CARRYING_VALUE"
    assert by_sample["sample-18"]["report_norm_id"] == 690
    assert by_sample["sample-20"]["lane_role"] == "LIABILITY_CARRYING_VALUE"
    assert by_sample["sample-20"]["report_norm_id"] == 704
    assert all(
        item["source_lane_role"] == "SIGNED_CARRYING_VALUE"
        for sample_id, item in by_sample.items()
        if sample_id in {"sample-13", "sample-15", "sample-18", "sample-20"}
    )


def test_horizontal_zero_signed_carrying_lane_remains_unresolved() -> None:
    pages = _horizontal_pages()
    pages[0]["lines"][13]["numeric_recognition"]["raw_prediction"] = "-"
    pages[0]["lines"][13]["vietocr_text"] = "-"
    mapping = _mapping(pages)
    assert not any(
        item["numeric_cell"]["sample_id"] == "sample-13" for item in mapping["mapping_proposals"]
    )
    assert any(
        item["sample_id"] == "sample-13"
        and item["reason"] == "ZERO_SIGN_SPLIT_CARRYING_VALUE_CANNOT_CHOOSE_ASSET_OR_LIABILITY"
        for item in mapping["unresolved_cells"]
    )


def test_sole_net_carrying_lane_sign_split_is_disabled_when_atomic_lanes_exist() -> None:
    compiled = {
        "signed_carrying_lane_policy": ("POSITIVE_TO_ASSET_NEGATIVE_TO_LIABILITY_ZERO_UNRESOLVED"),
        "sole_net_carrying_lane_policy": (
            "WHEN_NO_ATOMIC_CARRYING_LANES_POSITIVE_TO_ASSET_NEGATIVE_TO_LIABILITY_ZERO_UNRESOLVED"
        ),
    }
    cell = {
        "lane_role": "NET_VALUE",
        "primary_token": {
            "classification": "SIGNED_NUMBER",
            "coefficient": -7,
            "scale": 0,
        },
    }
    assert mapping_v1._effective_mapping_lane(cell, compiled, {"CONTRACT_VALUE", "NET_VALUE"}) == (
        "LIABILITY_CARRYING_VALUE",
        None,
    )
    assert mapping_v1._effective_mapping_lane(
        cell,
        compiled,
        {"ASSET_CARRYING_VALUE", "LIABILITY_CARRYING_VALUE", "NET_VALUE"},
    ) == ("NET_VALUE", None)


def test_same_crop_semantic_thousands_mark_as_space_compares_digits_but_not_digit_loss() -> None:
    primary = mapping_v1.parse_visible_financial_numeric_token_v1("163.623.724")
    equivalent = mapping_v1.parse_visible_financial_numeric_token_v1("163.623 724")
    dropped = mapping_v1.parse_visible_financial_numeric_token_v1("163.623 72")
    decimal_ambiguous = mapping_v1.parse_visible_financial_numeric_token_v1("163.623,724")

    assert mapping_v1._same_number(primary, equivalent) is True
    assert mapping_v1._same_number(primary, dropped) is False
    assert mapping_v1._same_number(primary, decimal_ambiguous) is True
