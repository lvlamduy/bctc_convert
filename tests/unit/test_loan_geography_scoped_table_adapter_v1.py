from __future__ import annotations

import hashlib
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path

import pytest

from bctc_ai.evaluation import loan_geography_scoped_table_adapter_v1 as adapter_v1
from bctc_ai.evaluation.loan_geography_numeric_reconciliation_v1 import (
    build_loan_geography_numeric_reconciliation_v1,
)
from bctc_ai.evaluation.loan_geography_scoped_table_adapter_v1 import (
    FAMILY_ID,
    LOAN_GEOGRAPHY_REGION_QUERY_SPEC_V2,
    LOAN_GEOGRAPHY_SCOPED_TABLE_ALIAS_PROVENANCE_V1,
    LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1,
    LoanGeographyScopedTableAdapterV1Error,
    build_loan_geography_customer_loan_total_control_requests_v1,
    build_loan_geography_document_context_v1,
    build_loan_geography_region_query_spec_v2,
    build_loan_geography_scoped_graphs_v1,
    build_loan_geography_whole_document_scoped_graph_v1,
    compare_loan_geography_sparse_full_graphs_v1,
    project_loan_geography_numeric_input_v1,
    project_loan_geography_visible_dash_graph_v1,
    validate_loan_geography_customer_loan_total_control_requests_replay_v1,
    validate_loan_geography_customer_loan_total_control_requests_v1,
    validate_loan_geography_document_context_replay_v1,
    validate_loan_geography_scoped_graphs_replay_v1,
    validate_loan_geography_whole_document_scoped_graph_replay_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(_ROOT))

from scripts.experiments import customer_loan_total_control_v1 as upstream_control_v1  # noqa: E402


def _line(index: int, text: str, bbox: list[int], numeric: str | None = None) -> dict:
    return {
        "bbox": bbox,
        "crop_ref": {
            "path": f"crop-{index}.png",
            "sha256": str(index % 10) * 64,
            "size_bytes": 1,
        },
        "line_ordinal": index,
        "numeric_recognition": {
            "raw_prediction": numeric if numeric is not None else text,
            "reader_score": 0.9,
        },
        "sample_id": f"sample-{index}",
        "vietocr_text": text,
    }


def _exact_page(page_sequence: int = 1) -> dict:
    # Provider order is intentionally unrelated to visual order.
    lines = [
        _line(90, "Mức độ tập trung tài sản và công nợ", [20, 20, 610, 46]),
        _line(3, "theo khu vực địa lý", [20, 50, 310, 76]),
        _line(88, "31/12/2025", [650, 82, 810, 108]),
        _line(11, "Tổng dư nợ cho vay", [350, 120, 555, 148]),
        _line(12, "Cho vay", [650, 116, 790, 144]),
        _line(15, "Cho vay khách hàng và các TCTD", [810, 118, 990, 146]),
        _line(13, "khách hàng", [650, 148, 805, 176]),
        _line(14, "triệu đồng", [660, 180, 805, 206]),
        _line(4, "Trong nước", [40, 220, 190, 248]),
        _line(99, "1.000", [685, 220, 755, 248], "1.000"),
        _line(7, "Nuoc ngoai", [40, 270, 190, 298]),
        _line(5, "900", [685, 270, 755, 298], "900"),
        _line(16, "Tổng cộng", [40, 320, 190, 348]),
        _line(17, "1.900", [685, 320, 755, 348], "1.900"),
    ]
    return {"lines": list(reversed(lines)), "page_sequence": page_sequence, "page_width": 1_000}


def _unlabeled_total_page(page_sequence: int = 1, *, period: str = "31/12/2025") -> dict:
    lines = [
        _line(90, "Mức độ tập trung tài sản và công nợ", [20, 20, 610, 46]),
        _line(3, "theo khu vực địa lý", [20, 50, 310, 76]),
        _line(88, period, [585, 82, 785, 108]),
        _line(11, "Cho vay khách hàng", [575, 120, 795, 148]),
        _line(14, "triệu đồng", [595, 160, 775, 188]),
        _line(4, "Trong nước", [40, 220, 190, 248]),
        _line(7, "Nước ngoài", [40, 270, 190, 298]),
    ]
    for lane, center in enumerate([285, 485, 685, 835, 945]):
        left, right = center - 30, center + 30
        domestic = 800 + lane
        foreign = 100 + lane
        total = 900 + lane * 2
        lines.extend(
            [
                _line(20 + lane, str(domestic), [left, 220, right, 248], str(domestic)),
                _line(30 + lane, str(foreign), [left, 270, right, 298], str(foreign)),
                _line(40 + lane, str(total), [left, 310, right, 338], str(total)),
            ]
        )
    return {"lines": list(reversed(lines)), "page_sequence": page_sequence, "page_width": 1_000}


def _two_period_page() -> dict:
    lines = [
        _line(90, "Mức độ tập trung tài sản và công nợ", [20, 20, 610, 46]),
        _line(3, "theo khu vực địa lý", [20, 50, 310, 76]),
        _line(1, "31/12/2025", [540, 84, 690, 110]),
        _line(2, "31/12/2024", [760, 84, 910, 110]),
        _line(30, "Cho vay khách hàng", [520, 125, 710, 153]),
        _line(31, "Cho vay khách hàng", [740, 125, 930, 153]),
        _line(32, "triệu đồng", [550, 165, 690, 191]),
        _line(33, "triệu đồng", [770, 165, 910, 191]),
        _line(4, "Trong nước", [40, 220, 190, 248]),
        _line(5, "1.000", [580, 220, 660, 248], "1.000"),
        _line(6, "900", [800, 220, 870, 248], "900"),
        _line(7, "Nước ngoài", [40, 270, 190, 298]),
        _line(8, "100", [580, 270, 660, 298], "100"),
        _line(9, "90", [800, 270, 870, 298], "90"),
        _line(10, "Tổng cộng", [40, 320, 190, 348]),
        _line(11, "1.100", [580, 320, 660, 348], "1.100"),
        _line(12, "990", [800, 320, 870, 348], "990"),
    ]
    return {"lines": list(reversed(lines)), "page_sequence": 1, "page_width": 1_000}


def _snapshot_pages(pages: list[dict], *, ordinal: int = 1) -> dict:
    packet = {
        "document_evidence_root_sha256": str(ordinal % 10) * 64,
        "document_id": f"document-{ordinal}",
        "document_ordinal": ordinal,
        "line_count": sum(len(page["lines"]) for page in pages),
        "packet_id": f"packet-{ordinal}",
        "page_count": len(pages),
        "period": "ANNUAL",
        "year": 2025,
    }
    material = {
        "document_packet": packet,
        "joined_pages": pages,
        "manifest_id": "manifest",
        "query_selection_id": f"selection-{ordinal}",
        "selected_page_dimensions": [
            {
                "physical_page": page["page_sequence"],
                "pixel_height": 1_000,
                "pixel_width": 1_000,
                "render_sha256": "8" * 64,
                "render_size_bytes": 1,
            }
            for page in pages
        ],
        "state": "AUTHENTICATED_IMMUTABLE_SQLITE_SELECTED_PAGE_EVIDENCE",
    }
    return {
        **material,
        "snapshot_id": "ffdesv1:selected:" + canonical_json_sha256_v1(material),
    }


def _snapshot(page: dict, *, ordinal: int = 1, page_count: int = 1) -> dict:
    assert page_count == 1
    return _snapshot_pages([page], ordinal=ordinal)


def _receipt(snapshot: dict) -> dict:
    packet = snapshot["document_packet"]
    outcome_material = {
        "coverage_status": "PROVEN_COMPLETE_FOR_DECLARED_SPEC",
        "document_evidence_root_sha256": packet["document_evidence_root_sha256"],
        "document_id": packet["document_id"],
        "document_ordinal": packet["document_ordinal"],
        "document_packet_id": packet["packet_id"],
        "selected_pages": [item["page_sequence"] for item in snapshot["joined_pages"]],
    }
    outcome = {
        **outcome_material,
        "outcome_id": "fffrrv2:document:" + canonical_json_sha256_v1(outcome_material),
    }
    material = {
        "documents": [outcome],
        "family_id": FAMILY_ID,
        "format_version": "FAMILY_FIRST_REGION_RETRIEVAL_RECEIPT_V2",
        "query_spec": deepcopy(LOAN_GEOGRAPHY_REGION_QUERY_SPEC_V2),
    }
    return {
        **material,
        "receipt_id": "fffrrv2:receipt:" + canonical_json_sha256_v1(material),
    }


def _absent_local_total_snapshot() -> dict:
    loan_type_surfaces = [
        ("5. CHO VAY KHÁCH HÀNG", 0, 0),
        ("30/06/2026", 500, 40),
        ("31/12/2025", 800, 40),
        ("Triệu đồng", 500, 70),
        ("Triệu đồng", 800, 70),
        ("Cho vay các tổ chức kinh tế, cá nhân trong nước", 0, 120),
        ("100", 500, 120),
        ("90", 800, 120),
        ("Cho vay chiết khấu công cụ chuyển nhượng và các giấy tờ có giá", 0, 165),
        ("10", 500, 165),
        ("9", 800, 165),
        ("Cho thuê tài chính", 0, 210),
        ("5", 500, 210),
        ("4", 800, 210),
        ("Các khoản trả thay khách hàng", 0, 255),
        ("3", 500, 255),
        ("2", 800, 255),
        ("Cho vay bằng vốn tài trợ, ủy thác đầu tư", 0, 300),
        ("2", 500, 300),
        ("1", 800, 300),
        ("120", 500, 345),
        ("106", 800, 345),
        ("Phân tích chất lượng nợ cho vay", 0, 400),
    ]

    def strict_line(index: int, text: str, bbox: list[int], *, page: int) -> dict:
        sample_id = f"sample-{page}-{index:03d}"
        return {
            "bbox": bbox,
            "crop_ref": {
                "path": f"crop/{sample_id}.png",
                "sha256": hashlib.sha256(sample_id.encode()).hexdigest(),
                "size_bytes": 1,
            },
            "line_ordinal": index,
            "numeric_recognition": {"raw_prediction": text, "reader_score": 0.999},
            "sample_id": sample_id,
            "vietocr_text": text,
        }

    upstream_lines = [
        strict_line(index, text, [x, y, x + 160, y + 24], page=1)
        for index, (text, x, y) in enumerate(loan_type_surfaces)
    ]
    table = _exact_page(2)
    table["lines"] = [item for item in table["lines"] if item["line_ordinal"] not in {16, 17}]
    replacements = {88: "30/06/2026", 99: "100", 5: "20"}
    for line in table["lines"]:
        if line["line_ordinal"] in replacements:
            surface = replacements[line["line_ordinal"]]
            line["vietocr_text"] = surface
            line["numeric_recognition"]["raw_prediction"] = surface
    visual = sorted(table["lines"], key=lambda item: (item["bbox"][1], item["bbox"][0]))
    table_lines = [
        strict_line(index, line["vietocr_text"], line["bbox"], page=2)
        for index, line in enumerate(visual)
    ]
    packet_material = {
        "assurance": "UNAUDITED",
        "bank_provenance": "TEST",
        "document_evidence_root_sha256": "1" * 64,
        "document_id": "ffsiv1:document:" + "2" * 64,
        "document_ordinal": 1,
        "line_count": len(upstream_lines) + len(table_lines),
        "page_count": 2,
        "period": "Q2",
        "scope": "CONSOLIDATED",
        "source_pdf_ref": {"path": "test.pdf", "sha256": "3" * 64, "size_bytes": 1},
        "year": 2026,
    }
    packet = {
        **packet_material,
        "packet_id": "ffdesv1:document:" + canonical_json_sha256_v1(packet_material),
    }
    material = {
        "document_packet": packet,
        "joined_pages": [
            {"lines": upstream_lines, "page_sequence": 1, "page_width": 1_200},
            {"lines": table_lines, "page_sequence": 2, "page_width": 1_000},
        ],
        "manifest_id": "ffdesv1:manifest:" + "4" * 64,
        "query_selection_id": "ffoqcv1:selection:" + "5" * 64,
        "selected_page_dimensions": [
            {
                "physical_page": 1,
                "pixel_height": 600,
                "pixel_width": 1_200,
                "render_sha256": "6" * 64,
                "render_size_bytes": 1,
            },
            {
                "physical_page": 2,
                "pixel_height": 1_000,
                "pixel_width": 1_000,
                "render_sha256": "7" * 64,
                "render_size_bytes": 1,
            },
        ],
        "state": "AUTHENTICATED_IMMUTABLE_SQLITE_SELECTED_PAGE_EVIDENCE",
    }
    return {
        **material,
        "snapshot_id": "ffdesv1:selected:" + canonical_json_sha256_v1(material),
    }


def _rehash_nested(value: dict, prefix: str) -> None:
    material = deepcopy(value)
    material.pop("result_id", None)
    value["result_id"] = prefix + canonical_json_sha256_v1(material)


def _rehash_control(value: dict) -> None:
    _rehash_nested(value, "cltcv1:result:")


def _rehash_total_control_request_set(value: dict) -> None:
    binding = value["document_binding"]
    binding["source_locator_axis_sha256"] = canonical_json_sha256_v1(value["source_locator_ids"])
    for lane in value["lane_requests"]:
        if lane["classification"] != "STRUCTURALLY_ABSENT":
            continue
        lane_material = deepcopy(lane)
        lane_material.pop("control_request_id")
        lane["control_request_id"] = "lgstv1:total-control-request:" + canonical_json_sha256_v1(
            {
                "document_binding": binding,
                "graph_binding": value["graph_binding"],
                "lane": lane_material,
            }
        )
    material = deepcopy(value)
    material.pop("request_set_id")
    value["request_set_id"] = "lgstv1:total-control-request-set:" + canonical_json_sha256_v1(
        material
    )


def _upstream_total_control(_requests: dict, _document: dict, snapshot: dict) -> dict:
    built = upstream_control_v1.build_customer_loan_total_control_v1(snapshot, "30/06/2026")
    return upstream_control_v1.validate_customer_loan_total_control_replay_v1(
        built, snapshot, "30/06/2026"
    )


def test_thin_adapter_replays_and_projects_overlay_and_printed_total_matrix() -> None:
    snapshot = _snapshot(_exact_page())
    receipt = _receipt(snapshot)
    result = build_loan_geography_scoped_graphs_v1(receipt, [snapshot])
    document = result["documents"][0]

    assert document["disposition"] == "EXACT_CUSTOMER_LOAN_GEOGRAPHY"
    assert document["uniqueness"] == {
        "exact_logical_graph_count": 1,
        "multiple_identical_region_count": 0,
        "partial_nonterminal_graph_count": 0,
        "physical_region_count": 2,
    }
    assert document["evidence_binding"]["document_id"] == snapshot["document_packet"]["document_id"]
    assert document["evidence_binding"]["document_ordinal"] == 1
    assert validate_loan_geography_scoped_graphs_replay_v1(result, receipt, [snapshot]) == result

    overlay = project_loan_geography_visible_dash_graph_v1(document, snapshot["document_packet"])
    assert overlay["evidence_binding"]["document_id"] == document["document_id"]
    assert overlay["evidence_binding"]["document_ordinal"] == 1
    segment = overlay["graphs"][0]["segments"][0]
    assert segment["resolved_period"] == "2025-12-31"
    assert [item["role"] for item in segment["role_cells"]] == [
        "DOMESTIC_TOTAL",
        "FOREIGN_TOTAL",
    ]

    numeric_input = project_loan_geography_numeric_input_v1(document, snapshot["document_packet"])
    assert overlay["graphs"][0]["graph_id"] == document["graphs"][0]["graph_id"]
    assert numeric_input["region_id"] == overlay["graphs"][0]["graph_id"]
    assert [item["cell_id"] for row in numeric_input["mapped_rows"] for item in row["cells"]] == [
        item["graph_cell_id"] for item in segment["role_cells"]
    ]
    assert numeric_input["printed_customer_loan_total"]["cells"][0]["vietocr_surface"] == "1.900"
    numeric = build_loan_geography_numeric_reconciliation_v1(numeric_input)
    assert numeric["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"


def test_unlabeled_printed_total_projects_nullable_label_and_raw_geometry() -> None:
    snapshot = _snapshot(_unlabeled_total_page())
    receipt = _receipt(snapshot)
    document = build_loan_geography_scoped_graphs_v1(receipt, [snapshot])["documents"][0]

    numeric_input = project_loan_geography_numeric_input_v1(document, snapshot["document_packet"])

    segment = document["graphs"][0]["segments"][0]
    assert segment["trailing_total_match"] is None
    assert segment["trailing_total_resolution"]["mode"] == ("UNLABELED_COMPLETE_NUMERIC_TOTAL_ROW")
    total = numeric_input["printed_customer_loan_total"]
    assert total["label_surface"] is None
    assert total["control_evidence"] == [
        {
            "evidence_refs": [
                "line:1:40",
                "line:1:41",
                "line:1:42",
                "line:1:43",
                "line:1:44",
            ],
            "label_evidence_ref": segment["trailing_total_resolution"]["resolution_id"],
            "label_surface": None,
            "lane_index": 0,
            "page_sequence": 1,
            "resolution_mode": "LOCAL_UNLABELED_TOTAL_ROW",
            "row_bbox": [255, 310, 975, 338],
            "source_bboxes": [
                [255, 310, 315, 338],
                [455, 310, 515, 338],
                [655, 310, 715, 338],
                [805, 310, 865, 338],
                [915, 310, 975, 338],
            ],
            "source_line_indices": [40, 41, 42, 43, 44],
            "source_surfaces_raw_nfc": ["900", "902", "904", "906", "908"],
        }
    ]
    assert total["cells"][0]["vietocr_surface"] == "904"
    numeric = build_loan_geography_numeric_reconciliation_v1(numeric_input)
    assert numeric["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"


def test_labeled_and_unlabeled_period_lanes_keep_per_lane_control_modes() -> None:
    labeled = _unlabeled_total_page(1)
    labeled["lines"].append(_line(50, "Tổng cộng", [40, 310, 190, 338]))
    pages = [labeled, _unlabeled_total_page(2, period="31/12/2024")]
    snapshot = _snapshot_pages(pages)
    receipt = _receipt(snapshot)
    document = build_loan_geography_scoped_graphs_v1(receipt, [snapshot])["documents"][0]

    numeric_input = project_loan_geography_numeric_input_v1(document, snapshot["document_packet"])

    total = numeric_input["printed_customer_loan_total"]
    assert total["label_surface"] is None
    assert [item["resolution_mode"] for item in total["control_evidence"]] == [
        "LOCAL_LABELED_TOTAL",
        "LOCAL_UNLABELED_TOTAL_ROW",
    ]
    assert [item["label_surface"] for item in total["control_evidence"]] == [
        "Tổng cộng",
        None,
    ]
    numeric = build_loan_geography_numeric_reconciliation_v1(numeric_input)
    assert numeric["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"


def test_total_control_request_public_replay_classifies_all_three_lane_states() -> None:
    fixtures = [
        (_snapshot(_exact_page()), "LOCAL_LABELED_TOTAL"),
        (_snapshot(_unlabeled_total_page()), "LOCAL_UNLABELED_TOTAL_ROW"),
        (_absent_local_total_snapshot(), "STRUCTURALLY_ABSENT"),
    ]
    for snapshot, expected in fixtures:
        receipt = _receipt(snapshot)
        document = build_loan_geography_whole_document_scoped_graph_v1(receipt, snapshot)
        requests = build_loan_geography_customer_loan_total_control_requests_v1(
            document, snapshot["document_packet"], snapshot
        )

        assert requests["lane_requests"][0]["classification"] == expected
        assert validate_loan_geography_customer_loan_total_control_requests_v1(requests) == requests
        assert (
            validate_loan_geography_customer_loan_total_control_requests_replay_v1(
                requests, document, snapshot["document_packet"], snapshot
            )
            == requests
        )
        has_request = requests["lane_requests"][0]["control_request_id"] is not None
        assert has_request is (expected == "STRUCTURALLY_ABSENT")


def test_labeled_missing_detector_total_is_not_reclassified_as_structural_absence() -> None:
    page = _exact_page()
    page["lines"] = [item for item in page["lines"] if item["line_ordinal"] != 17]
    snapshot = _snapshot(page)
    receipt = _receipt(snapshot)
    whole = build_loan_geography_whole_document_scoped_graph_v1(receipt, snapshot)

    requests = build_loan_geography_customer_loan_total_control_requests_v1(
        whole, snapshot["document_packet"], snapshot
    )

    lane = requests["lane_requests"][0]
    assert lane["classification"] == "LOCAL_LABELED_TOTAL"
    assert lane["control_request_id"] is None
    assert whole["graphs"][0]["segments"][0]["trailing_total_cells"][0]["source_line_index"] is None


def test_request_replay_rejects_self_rehashed_request_document_or_snapshot_drift() -> None:
    snapshot = _absent_local_total_snapshot()
    receipt = _receipt(snapshot)
    whole = build_loan_geography_whole_document_scoped_graph_v1(receipt, snapshot)
    requests = build_loan_geography_customer_loan_total_control_requests_v1(
        whole, snapshot["document_packet"], snapshot
    )

    forged_request = deepcopy(requests)
    forged_request["source_locator_ids"].pop()
    forged_request["document_binding"]["source_locator_axis_sha256"] = canonical_json_sha256_v1(
        forged_request["source_locator_ids"]
    )
    lane_material = deepcopy(forged_request["lane_requests"][0])
    lane_material.pop("control_request_id")
    forged_request["lane_requests"][0]["control_request_id"] = (
        "lgstv1:total-control-request:"
        + canonical_json_sha256_v1(
            {
                "document_binding": forged_request["document_binding"],
                "graph_binding": forged_request["graph_binding"],
                "lane": lane_material,
            }
        )
    )
    material = deepcopy(forged_request)
    material.pop("request_set_id")
    forged_request["request_set_id"] = "lgstv1:total-control-request-set:" + (
        canonical_json_sha256_v1(material)
    )
    assert validate_loan_geography_customer_loan_total_control_requests_v1(forged_request)
    with pytest.raises(LoanGeographyScopedTableAdapterV1Error, match="replay exactly"):
        validate_loan_geography_customer_loan_total_control_requests_replay_v1(
            forged_request, whole, snapshot["document_packet"], snapshot
        )

    forged_document = deepcopy(whole)
    forged_document["source_line_bindings"][0]["crop_ref"]["sha256"] = "5" * 64
    _rehash_nested(forged_document, "lgstv1:document:")
    with pytest.raises(LoanGeographyScopedTableAdapterV1Error, match="replay exactly"):
        validate_loan_geography_customer_loan_total_control_requests_replay_v1(
            requests, forged_document, snapshot["document_packet"], snapshot
        )

    forged_snapshot = deepcopy(snapshot)
    forged_snapshot["joined_pages"][0]["lines"][0]["crop_ref"]["sha256"] = "6" * 64
    snapshot_material = deepcopy(forged_snapshot)
    snapshot_material.pop("snapshot_id")
    forged_snapshot["snapshot_id"] = "ffdesv1:selected:" + canonical_json_sha256_v1(
        snapshot_material
    )
    with pytest.raises(LoanGeographyScopedTableAdapterV1Error):
        validate_loan_geography_customer_loan_total_control_requests_replay_v1(
            requests, whole, snapshot["document_packet"], forged_snapshot
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "AUTHORITY_CONTRADICTION",
        "AUTHORITY_EXTRA",
        "CLAIM",
        "UNIT_EXTRA",
        "UNIT_EVIDENCE_EMPTY",
        "UNIT_BOOL_SCALE",
        "PAGE_ZERO",
        "PAGE_BOOL",
        "PAGE_PAST_DENOMINATOR",
        "LOCATOR_NONHEX",
        "LOCATOR_UPPERCASE",
    ],
)
def test_total_control_request_cheap_gate_rejects_self_rehashed_contract_drift(
    mutation: str,
) -> None:
    snapshot = _absent_local_total_snapshot()
    receipt = _receipt(snapshot)
    whole = build_loan_geography_whole_document_scoped_graph_v1(receipt, snapshot)
    request = build_loan_geography_customer_loan_total_control_requests_v1(
        whole, snapshot["document_packet"], snapshot
    )
    lane = request["lane_requests"][0]

    if mutation == "AUTHORITY_CONTRADICTION":
        request["authority"]["numeric_or_mapping_authority"] = True
    elif mutation == "AUTHORITY_EXTRA":
        request["authority"]["self_hash_is_source_authority"] = True
    elif mutation == "CLAIM":
        request["claim_boundary"] = "FORGED_BROADER_CLAIM"
    elif mutation == "UNIT_EXTRA":
        lane["unit_context"]["inferred"] = True
    elif mutation == "UNIT_EVIDENCE_EMPTY":
        lane["unit_context"]["evidence_ref"] = ""
    elif mutation == "UNIT_BOOL_SCALE":
        lane["unit_context"]["scale"] = True
    elif mutation == "PAGE_ZERO":
        lane["page_sequences"] = [0]
    elif mutation == "PAGE_BOOL":
        lane["page_sequences"] = [True]
    elif mutation == "PAGE_PAST_DENOMINATOR":
        lane["page_sequences"] = [len(request["source_page_render_bindings"]) + 1]
    else:
        prefix = "lgstv1:source-locator:"
        suffix = "g" * 64 if mutation == "LOCATOR_NONHEX" else "A" * 64
        request["source_locator_ids"][0] = prefix + suffix
        request["source_locator_ids"].sort()
    _rehash_total_control_request_set(request)

    with pytest.raises(LoanGeographyScopedTableAdapterV1Error):
        validate_loan_geography_customer_loan_total_control_requests_v1(request)


def test_upstream_control_projects_cross_page_total_and_reconciles_without_backsolve() -> None:
    snapshot = _absent_local_total_snapshot()
    receipt = _receipt(snapshot)
    whole = build_loan_geography_whole_document_scoped_graph_v1(receipt, snapshot)
    requests = build_loan_geography_customer_loan_total_control_requests_v1(
        whole, snapshot["document_packet"], snapshot
    )
    control = _upstream_total_control(requests, whole, snapshot)

    numeric_input = project_loan_geography_numeric_input_v1(
        whole,
        snapshot["document_packet"],
        upstream_total_control_requests=requests,
        upstream_total_control_source_document=whole,
        upstream_total_control_source_snapshot=snapshot,
        upstream_total_controls=[control],
    )

    lane = numeric_input["printed_customer_loan_total"]["control_evidence"][0]
    segment = whole["graphs"][0]["segments"][0]
    assert segment["page_sequences"] == [2]
    assert lane["page_sequence"] == 1
    assert lane["resolution_mode"] == ("UPSTREAM_AUTHENTICATED_CUSTOMER_LOAN_TOTAL_CONTROL")
    assert lane["control_result_id"] == control["result_id"]
    assert lane["control_request_id"] == requests["lane_requests"][0]["control_request_id"]
    assert lane["source_snapshot_id"] == snapshot["snapshot_id"]
    assert lane["source_locator"]["page_render"]["physical_page"] == 1
    assert lane["source_locator"]["crop_ref"] == control["total_control"]["source"]["crop_ref"]
    numeric = build_loan_geography_numeric_reconciliation_v1(numeric_input)
    assert numeric["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    assert numeric["accounting_checks"][0]["residual"] == 0
    assert numeric["metrics"]["accounting_backsolved_or_invented_value_count"] == 0
    assert numeric["authority"]["upstream_authenticated_total_control_can_backsolve"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        "MISSING",
        "DUPLICATE",
        "DOCUMENT",
        "ROOT",
        "SNAPSHOT",
        "PERIOD",
        "UNIT",
        "RENDER",
        "CROP",
        "SOURCE_LINE",
        "LANE_TRANSPLANT",
    ],
)
def test_upstream_control_binding_tamper_fails_closed(mutation: str) -> None:
    snapshot = _absent_local_total_snapshot()
    receipt = _receipt(snapshot)
    whole = build_loan_geography_whole_document_scoped_graph_v1(receipt, snapshot)
    requests = build_loan_geography_customer_loan_total_control_requests_v1(
        whole, snapshot["document_packet"], snapshot
    )
    control = _upstream_total_control(requests, whole, snapshot)
    controls = [control]
    if mutation == "MISSING":
        controls = []
    elif mutation == "DUPLICATE":
        controls = [control, deepcopy(control)]
    elif mutation == "DOCUMENT":
        control["document_binding"]["document_id"] = "different-document"
        _rehash_control(control)
    elif mutation == "ROOT":
        control["document_binding"]["document_evidence_root_sha256"] = "9" * 64
        _rehash_control(control)
    elif mutation == "SNAPSHOT":
        control["document_binding"]["snapshot_id"] = "ffdesv1:snapshot:different"
        _rehash_control(control)
    elif mutation == "PERIOD":
        control["requested_period_end"] = "31/12/2024"
        control["period_lane"]["period_end"] = "31/12/2024"
        control["loan_type_graph_result"]["graphs"][0]["period_axis"][0]["period"] = "31/12/2024"
        _rehash_nested(control["loan_type_graph_result"], "ltvgv1:result:")
        control["loan_type_numeric_result"]["graph_result_id"] = control["loan_type_graph_result"][
            "result_id"
        ]
        _rehash_nested(control["loan_type_numeric_result"], "ltnrrv1:result:")
        _rehash_control(control)
    elif mutation == "UNIT":
        control["unit_evidence"]["magnitude_power10"] = 3
        _rehash_control(control)
    elif mutation == "RENDER":
        control["total_control"]["source"]["page_render"]["render_sha256"] = "4" * 64
        _rehash_control(control)
    elif mutation == "CROP":
        control["total_control"]["source"]["crop_ref"]["sha256"] = "4" * 64
        _rehash_control(control)
    elif mutation == "SOURCE_LINE":
        control["total_control"]["source"]["source_line_index"] = 201
        control["loan_type_graph_result"]["graphs"][0]["total"][0]["source_line_index"] = 201
        control["loan_type_numeric_result"]["total"][0]["source_line_index"] = 201
        _rehash_nested(control["loan_type_graph_result"], "ltvgv1:result:")
        control["loan_type_numeric_result"]["graph_result_id"] = control["loan_type_graph_result"][
            "result_id"
        ]
        _rehash_nested(control["loan_type_numeric_result"], "ltnrrv1:result:")
        _rehash_control(control)
    else:
        graph = control["loan_type_graph_result"]["graphs"][0]
        graph["lane_centers_x2"] = [1_400, 1_800]
        graph["lane_types"] = ["MONEY", "MONEY"]
        graph["period_axis"] = [
            {"period": control["requested_period_end"], "x_center_x2": 1_400},
            {"period": "31/12/2024", "x_center_x2": 1_800},
        ]
        graph["total"][0]["lane_index"] = 1
        control["period_lane"]["lane_index"] = 1
        control["total_control"]["lane_index"] = 1
        control["unit_evidence"]["lane_index"] = 1
        control["loan_type_numeric_result"]["total"][0]["lane_index"] = 1
        _rehash_nested(control["loan_type_graph_result"], "ltvgv1:result:")
        control["loan_type_numeric_result"]["graph_result_id"] = control["loan_type_graph_result"][
            "result_id"
        ]
        _rehash_nested(control["loan_type_numeric_result"], "ltnrrv1:result:")
        _rehash_control(control)

    with pytest.raises(LoanGeographyScopedTableAdapterV1Error):
        project_loan_geography_numeric_input_v1(
            whole,
            snapshot["document_packet"],
            upstream_total_control_requests=requests,
            upstream_total_control_source_document=whole,
            upstream_total_control_source_snapshot=snapshot,
            upstream_total_controls=controls,
        )


def test_coordinated_self_rehashed_control_requires_real_source_replay() -> None:
    snapshot = _absent_local_total_snapshot()
    receipt = _receipt(snapshot)
    whole = build_loan_geography_whole_document_scoped_graph_v1(receipt, snapshot)
    requests = build_loan_geography_customer_loan_total_control_requests_v1(
        whole, snapshot["document_packet"], snapshot
    )
    control = _upstream_total_control(requests, whole, snapshot)

    control["total_control"]["source"]["source_line_index"] = 201
    control["loan_type_graph_result"]["graphs"][0]["total"][0]["source_line_index"] = 201
    control["loan_type_numeric_result"]["total"][0]["source_line_index"] = 201
    _rehash_nested(control["loan_type_graph_result"], "ltvgv1:result:")
    control["loan_type_numeric_result"]["graph_result_id"] = control["loan_type_graph_result"][
        "result_id"
    ]
    _rehash_nested(control["loan_type_numeric_result"], "ltnrrv1:result:")
    _rehash_control(control)

    assert upstream_control_v1.validate_customer_loan_total_control_v1(control) == control
    with pytest.raises(LoanGeographyScopedTableAdapterV1Error, match="did not publicly replay"):
        project_loan_geography_numeric_input_v1(
            whole,
            snapshot["document_packet"],
            upstream_total_control_requests=requests,
            upstream_total_control_source_document=whole,
            upstream_total_control_source_snapshot=snapshot,
            upstream_total_controls=[control],
        )


@pytest.mark.parametrize("local_total_surface", ["120", "121"])
def test_local_total_rejects_equal_or_unequal_unused_upstream_control(
    local_total_surface: str,
) -> None:
    snapshot = _absent_local_total_snapshot()
    page = snapshot["joined_pages"][1]
    for text, bbox in (
        ("Tổng cộng", [40, 320, 190, 348]),
        (local_total_surface, [685, 320, 755, 348]),
    ):
        index = len(page["lines"])
        sample_id = f"sample-2-{index:03d}"
        page["lines"].append(
            {
                "bbox": bbox,
                "crop_ref": {
                    "path": f"crop/{sample_id}.png",
                    "sha256": hashlib.sha256(sample_id.encode()).hexdigest(),
                    "size_bytes": 1,
                },
                "line_ordinal": index,
                "numeric_recognition": {"raw_prediction": text, "reader_score": 0.999},
                "sample_id": sample_id,
                "vietocr_text": text,
            }
        )
    packet = snapshot["document_packet"]
    packet["line_count"] += 2
    packet_material = deepcopy(packet)
    packet_material.pop("packet_id")
    packet["packet_id"] = "ffdesv1:document:" + canonical_json_sha256_v1(packet_material)
    snapshot_material = deepcopy(snapshot)
    snapshot_material.pop("snapshot_id")
    snapshot["snapshot_id"] = "ffdesv1:selected:" + canonical_json_sha256_v1(snapshot_material)
    receipt = _receipt(snapshot)
    whole = build_loan_geography_whole_document_scoped_graph_v1(receipt, snapshot)
    requests = build_loan_geography_customer_loan_total_control_requests_v1(
        whole, snapshot["document_packet"], snapshot
    )
    assert requests["lane_requests"][0]["classification"] == "LOCAL_LABELED_TOTAL"
    control = _upstream_total_control(requests, whole, snapshot)

    with pytest.raises(
        LoanGeographyScopedTableAdapterV1Error, match="missing, duplicate, or unused"
    ):
        project_loan_geography_numeric_input_v1(
            whole,
            snapshot["document_packet"],
            upstream_total_control_requests=requests,
            upstream_total_control_source_document=whole,
            upstream_total_control_source_snapshot=snapshot,
            upstream_total_controls=[control],
        )


def test_alias_provenance_is_exactly_the_executable_spec_axis() -> None:
    executable = {
        "CONTINUATION": LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1["continuation_aliases"],
        "GEOGRAPHIC_CONCENTRATION_OWNER": LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1["owner_aliases"],
        **{
            item["component_id"]: item["aliases"]
            for item in LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1["owner_component_groups"]
        },
        "STRUCTURAL_RESET": LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1["structural_reset_aliases"],
        "TRAILING_TOTAL": LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1["trailing_total_aliases"],
        **{
            item["role"]: item["aliases"]
            for item in LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1["role_axis"]
        },
        **{
            item["scope_id"]: item["aliases"]
            for item in LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1["scope_axis"]
        },
        **{
            component["component_id"]: component["aliases"]
            for scope in LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1["scope_axis"]
            for component in scope.get("required_component_groups", [])
        },
        **{
            component["component_id"]: component["aliases"]
            for scope in LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1["scope_axis"]
            for component in scope.get("lane_component_groups", [])
        },
    }
    assert set(executable) == set(LOAN_GEOGRAPHY_SCOPED_TABLE_ALIAS_PROVENANCE_V1)
    assert all(
        executable[key] == [item["surface"] for item in records]
        for key, records in LOAN_GEOGRAPHY_SCOPED_TABLE_ALIAS_PROVENANCE_V1.items()
    )
    assert all(
        item["kind"] == "CANONICAL"
        for records in LOAN_GEOGRAPHY_SCOPED_TABLE_ALIAS_PROVENANCE_V1.values()
        for item in records
    )


def test_family11_pins_its_unlabeled_total_geometry_limits_declaratively() -> None:
    limits = LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1["limits"]
    assert limits["unlabeled_total_min_numeric_columns"] == 5
    assert limits["unlabeled_total_max_numeric_columns"] == 8
    assert limits["unlabeled_total_max_gap_lines"] == 2
    assert limits["unlabeled_total_gap_jitter_ppm"] == 200_000


def test_authoritative_query_spec_is_adapter_content_bound_and_canonical_only() -> None:
    root = Path(__file__).resolve().parents[2]
    query = build_loan_geography_region_query_spec_v2(root)
    reference = query["semantic_assignment_adapter_ref"]
    adapter = root / reference["path"]

    assert query == LOAN_GEOGRAPHY_REGION_QUERY_SPEC_V2
    assert reference["size_bytes"] == adapter.stat().st_size
    assert all(not item["verified_historical_variants"] for item in query["anchors"])


def test_unproved_coverage_and_self_rehashed_result_are_rejected() -> None:
    snapshot = _snapshot(_exact_page())
    receipt = _receipt(snapshot)
    bad_receipt = deepcopy(receipt)
    bad_receipt["documents"][0]["coverage_status"] = "UNRESOLVED"
    outcome = bad_receipt["documents"][0]
    outcome_material = deepcopy(outcome)
    outcome_material.pop("outcome_id")
    outcome["outcome_id"] = "fffrrv2:document:" + canonical_json_sha256_v1(outcome_material)
    receipt_material = deepcopy(bad_receipt)
    receipt_material.pop("receipt_id")
    bad_receipt["receipt_id"] = "fffrrv2:receipt:" + canonical_json_sha256_v1(receipt_material)
    with pytest.raises(LoanGeographyScopedTableAdapterV1Error, match="coverage"):
        build_loan_geography_scoped_graphs_v1(bad_receipt, [snapshot])

    result = build_loan_geography_scoped_graphs_v1(receipt, [snapshot])
    forged = deepcopy(result)
    forged["metrics"]["gemma_request_count"] = 1
    material = deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "lgstv1:batch:" + canonical_json_sha256_v1(material)
    with pytest.raises(LoanGeographyScopedTableAdapterV1Error, match="replay exactly"):
        validate_loan_geography_scoped_graphs_replay_v1(forged, receipt, [snapshot])


def test_self_rehashed_boolean_document_ordinal_is_rejected_as_untyped() -> None:
    snapshot = _snapshot(_exact_page())
    receipt = _receipt(snapshot)
    receipt["documents"][0]["document_ordinal"] = True
    outcome_material = deepcopy(receipt["documents"][0])
    outcome_material.pop("outcome_id")
    receipt["documents"][0]["outcome_id"] = (
        "fffrrv2:document:" + canonical_json_sha256_v1(outcome_material)
    )
    receipt_material = deepcopy(receipt)
    receipt_material.pop("receipt_id")
    receipt["receipt_id"] = "fffrrv2:receipt:" + canonical_json_sha256_v1(receipt_material)

    with pytest.raises(LoanGeographyScopedTableAdapterV1Error, match="coverage"):
        adapter_v1._prepare_loan_geography_receipt_v1(receipt)


def test_prepared_receipt_is_detached_from_nested_and_coordinated_rehash_mutation() -> None:
    snapshot = _snapshot(_exact_page())
    receipt = _receipt(snapshot)
    prepared = adapter_v1._prepare_loan_geography_receipt_v1(receipt)
    baseline = build_loan_geography_scoped_graphs_v1(prepared, [snapshot])
    assert prepared.canonical_payload_sha256 == hashlib.sha256(
        adapter_v1.canonical_json_bytes_v1(receipt)
    ).hexdigest()

    receipt["documents"][0]["retrieval_diagnostics"] = {"nested": ["changed"]}
    outcome_material = deepcopy(receipt["documents"][0])
    outcome_material.pop("outcome_id")
    receipt["documents"][0]["outcome_id"] = (
        "fffrrv2:document:" + canonical_json_sha256_v1(outcome_material)
    )
    receipt_material = deepcopy(receipt)
    receipt_material.pop("receipt_id")
    receipt["receipt_id"] = "fffrrv2:receipt:" + canonical_json_sha256_v1(receipt_material)
    changed = adapter_v1._prepare_loan_geography_receipt_v1(receipt)

    assert prepared.canonical_payload_sha256 != changed.canonical_payload_sha256
    assert build_loan_geography_scoped_graphs_v1(prepared, [snapshot]) == baseline
    assert build_loan_geography_scoped_graphs_v1(changed, [snapshot]) != baseline


def test_raw_nested_mutation_does_not_turn_prepared_receipt_into_cache_authority() -> None:
    snapshot = _snapshot(_exact_page())
    receipt = _receipt(snapshot)
    prepared = adapter_v1._prepare_loan_geography_receipt_v1(receipt)
    baseline = build_loan_geography_scoped_graphs_v1(prepared, [snapshot])
    receipt["documents"][0]["selected_pages"].append(2)

    assert build_loan_geography_scoped_graphs_v1(prepared, [snapshot]) == baseline
    with pytest.raises(LoanGeographyScopedTableAdapterV1Error, match="content identity"):
        build_loan_geography_scoped_graphs_v1(receipt, [snapshot])


def test_prepared_receipt_rejects_loaded_query_trust_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _snapshot(_exact_page())
    prepared = adapter_v1._prepare_loan_geography_receipt_v1(_receipt(snapshot))
    drifted_query = deepcopy(adapter_v1.LOAN_GEOGRAPHY_REGION_QUERY_SPEC_V2)
    drifted_query["window_line_span"] += 1
    monkeypatch.setattr(adapter_v1, "LOAN_GEOGRAPHY_REGION_QUERY_SPEC_V2", drifted_query)

    with pytest.raises(LoanGeographyScopedTableAdapterV1Error, match="query spec"):
        build_loan_geography_scoped_graphs_v1(prepared, [snapshot])


def test_prepared_receipt_is_safe_for_concurrent_repeated_document_builds() -> None:
    snapshot = _snapshot(_exact_page())
    prepared = adapter_v1._prepare_loan_geography_receipt_v1(_receipt(snapshot))

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(
            executor.map(
                lambda _index: build_loan_geography_scoped_graphs_v1(prepared, [snapshot]),
                range(12),
            )
        )

    assert all(result == results[0] for result in results)


def test_prepared_receipt_replay_still_invokes_shared_graph_public_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _snapshot(_exact_page())
    prepared = adapter_v1._prepare_loan_geography_receipt_v1(_receipt(snapshot))
    whole = build_loan_geography_whole_document_scoped_graph_v1(prepared, snapshot)
    calls: list[str] = []
    original = adapter_v1.validate_accounting_scoped_table_graph_replay_v1

    def replay(value: dict, pages: list[dict], spec: dict) -> dict:
        calls.append(value["result_id"])
        return original(value, pages, spec)

    monkeypatch.setattr(adapter_v1, "validate_accounting_scoped_table_graph_replay_v1", replay)

    assert (
        validate_loan_geography_whole_document_scoped_graph_replay_v1(
            whole,
            prepared,
            snapshot,
        )
        == whole
    )
    assert calls == [whole["scoped_table_graph"]["result_id"]]


def test_sparse_full_equivalence_uses_visual_region_not_result_identity() -> None:
    snapshot = _snapshot(_exact_page())
    receipt = _receipt(snapshot)
    first = build_loan_geography_scoped_graphs_v1(receipt, [snapshot])["documents"][0]
    result = compare_loan_geography_sparse_full_graphs_v1(
        first,
        first,
        whole_document_line_count=snapshot["document_packet"]["line_count"],
        whole_document_page_count=1,
    )
    assert result["sparse_region_fingerprint"] == result["whole_document_region_fingerprint"]


def test_whole_document_graph_public_replay_rebuilds_exact_snapshot_and_generic_core() -> None:
    snapshot = _snapshot(_exact_page())
    receipt = _receipt(snapshot)
    whole = build_loan_geography_whole_document_scoped_graph_v1(receipt, snapshot)

    assert (
        validate_loan_geography_whole_document_scoped_graph_replay_v1(whole, receipt, snapshot)
        == whole
    )


def test_whole_document_graph_replay_rejects_self_rehashed_output_tamper() -> None:
    snapshot = _snapshot(_exact_page())
    receipt = _receipt(snapshot)
    whole = build_loan_geography_whole_document_scoped_graph_v1(receipt, snapshot)
    forged = deepcopy(whole)
    forged["source_line_bindings"][0]["vietocr_transformer_surface"] = "forged"
    material = deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "lgstv1:document:" + canonical_json_sha256_v1(material)

    with pytest.raises(LoanGeographyScopedTableAdapterV1Error, match="does not replay exactly"):
        validate_loan_geography_whole_document_scoped_graph_replay_v1(forged, receipt, snapshot)


def test_whole_document_graph_replay_rejects_unhashed_output_tamper() -> None:
    snapshot = _snapshot(_exact_page())
    receipt = _receipt(snapshot)
    whole = build_loan_geography_whole_document_scoped_graph_v1(receipt, snapshot)
    forged = deepcopy(whole)
    forged["status"] = "FORGED_WHOLE_DOCUMENT_STATUS"

    with pytest.raises(LoanGeographyScopedTableAdapterV1Error, match="content identity"):
        validate_loan_geography_whole_document_scoped_graph_replay_v1(forged, receipt, snapshot)


def test_whole_document_graph_replay_rejects_a_different_rehashed_source_snapshot() -> None:
    snapshot = _snapshot(_exact_page())
    receipt = _receipt(snapshot)
    whole = build_loan_geography_whole_document_scoped_graph_v1(receipt, snapshot)
    forged_snapshot = deepcopy(snapshot)
    forged_snapshot["joined_pages"][0]["lines"][0]["crop_ref"]["path"] = (
        "different-authenticated-crop.png"
    )
    snapshot_material = deepcopy(forged_snapshot)
    snapshot_material.pop("snapshot_id")
    forged_snapshot["snapshot_id"] = "ffdesv1:selected:" + canonical_json_sha256_v1(
        snapshot_material
    )

    with pytest.raises(LoanGeographyScopedTableAdapterV1Error, match="does not replay exactly"):
        validate_loan_geography_whole_document_scoped_graph_replay_v1(
            whole, receipt, forged_snapshot
        )


def _context_page(
    sequence: int,
    *,
    period_text: str = "Tại ngày 30 tháng 6 năm 2025",
    unit: str = "Đơn vị tính: triệu đồng",
) -> dict:
    return {
        "lines": [
            _line(sequence * 10, period_text, [400, 40, 760, 70]),
            _line(sequence * 10 + 1, unit, [600, 90, 900, 120]),
        ],
        "page_sequence": sequence,
        "page_width": 1_000,
    }


def test_pdf_internal_context_rescues_missing_local_date_and_unit_not_packet_year() -> None:
    table = _exact_page()
    table["lines"] = [item for item in table["lines"] if item["line_ordinal"] not in {88, 14}]
    snapshot = _snapshot_pages([table, _context_page(2), _context_page(3)])
    receipt = _receipt(snapshot)
    document = build_loan_geography_scoped_graphs_v1(receipt, [snapshot])["documents"][0]
    context = build_loan_geography_document_context_v1(snapshot)

    assert validate_loan_geography_document_context_replay_v1(context, snapshot) == context
    overlay = project_loan_geography_visible_dash_graph_v1(
        document, snapshot["document_packet"], document_context=context
    )
    assert overlay["document_context_result_id"] == context["result_id"]
    assert overlay["graphs"][0]["segments"][0]["resolved_period"] == "2025-06-30"
    numeric = project_loan_geography_numeric_input_v1(
        document, snapshot["document_packet"], document_context=context
    )
    assert numeric["unit_context"]["resolution_mode"] == "DOCUMENT_INHERITED_EXACT_UNIT"
    assert numeric["period_axis"][0]["resolution_mode"] == ("DOCUMENT_INHERITED_EXACT_DATE")

    tampered_packet = deepcopy(snapshot["document_packet"])
    tampered_packet["year"] = 2099
    assert (
        project_loan_geography_numeric_input_v1(document, tampered_packet, document_context=context)
        == numeric
    )

    with pytest.raises(LoanGeographyScopedTableAdapterV1Error, match="period remains unresolved"):
        project_loan_geography_visible_dash_graph_v1(document, snapshot["document_packet"])


def test_conflicting_document_unit_does_not_inherit_and_local_exact_unit_dominates() -> None:
    no_local = _exact_page()
    no_local["lines"] = [item for item in no_local["lines"] if item["line_ordinal"] not in {88, 14}]
    conflicting_snapshot = _snapshot_pages(
        [no_local, _context_page(2), _context_page(3, unit="Đơn vị tính: nghìn đồng")]
    )
    receipt = _receipt(conflicting_snapshot)
    document = build_loan_geography_scoped_graphs_v1(receipt, [conflicting_snapshot])["documents"][
        0
    ]
    context = build_loan_geography_document_context_v1(conflicting_snapshot)
    with pytest.raises(LoanGeographyScopedTableAdapterV1Error, match="million-VND"):
        project_loan_geography_numeric_input_v1(
            document,
            conflicting_snapshot["document_packet"],
            document_context=context,
        )

    local_snapshot = _snapshot_pages(
        [
            _exact_page(),
            _context_page(2, period_text="Tại ngày 31 tháng 12 năm 2025"),
            _context_page(
                3,
                period_text="Tại ngày 31 tháng 12 năm 2025",
                unit="Đơn vị tính: nghìn đồng",
            ),
        ]
    )
    local_receipt = _receipt(local_snapshot)
    local_document = build_loan_geography_scoped_graphs_v1(local_receipt, [local_snapshot])[
        "documents"
    ][0]
    local_context = build_loan_geography_document_context_v1(local_snapshot)
    local_numeric = project_loan_geography_numeric_input_v1(
        local_document, local_snapshot["document_packet"], document_context=local_context
    )
    assert local_numeric["unit_context"]["resolution_mode"] == "LOCAL_EXACT_UNIT"


def test_zero_line_pages_keep_original_denominator_but_do_not_enter_graph_geometry() -> None:
    empty_middle = {"lines": [], "page_sequence": 2, "page_width": 1_000}
    terminal = {
        "lines": [_line(1, "Diễn giải không phải bảng", [20, 20, 300, 48])],
        "page_sequence": 3,
        "page_width": 1_000,
    }
    snapshot = _snapshot_pages([_exact_page(), empty_middle, terminal])
    receipt = _receipt(snapshot)
    result = build_loan_geography_scoped_graphs_v1(receipt, [snapshot])
    document = result["documents"][0]

    assert document["disposition"] == "EXACT_CUSTOMER_LOAN_GEOGRAPHY"
    assert [item["physical_page"] for item in document["selected_page_bindings"]] == [1, 2, 3]
    assert [item["line_count"] for item in document["selected_page_bindings"]] == [14, 0, 1]
    assert document["scoped_table_graph"]["metrics"]["page_count"] == 2
    assert result["metrics"]["selected_page_count"] == 3
    assert validate_loan_geography_scoped_graphs_replay_v1(result, receipt, [snapshot]) == result
    context = build_loan_geography_document_context_v1(snapshot)
    assert context["snapshot_id"] == snapshot["snapshot_id"]


def test_missing_role_cell_keeps_one_identity_across_graph_overlay_and_numeric() -> None:
    page = _exact_page()
    page["lines"] = [item for item in page["lines"] if item["line_ordinal"] != 5]
    snapshot = _snapshot(page)
    receipt = _receipt(snapshot)
    document = build_loan_geography_scoped_graphs_v1(receipt, [snapshot])["documents"][0]
    overlay = project_loan_geography_visible_dash_graph_v1(document, snapshot["document_packet"])
    numeric = project_loan_geography_numeric_input_v1(document, snapshot["document_packet"])
    hole = next(
        item
        for item in overlay["graphs"][0]["segments"][0]["role_cells"]
        if item["status"] == "MISSING_DETECTOR_CELL_REQUIRES_AUTHENTICATED_PIXEL_EVIDENCE"
    )
    numeric_hole = next(
        item
        for row in numeric["mapped_rows"]
        for item in row["cells"]
        if item["source_line_index"] is None
    )
    assert numeric["region_id"] == overlay["graphs"][0]["graph_id"]
    assert numeric_hole["cell_id"] == hole["graph_cell_id"]


def test_numeric_projection_orders_by_period_lane_not_provider_segment_order() -> None:
    snapshot = _snapshot(_two_period_page())
    receipt = _receipt(snapshot)
    document = build_loan_geography_scoped_graphs_v1(receipt, [snapshot])["documents"][0]
    forged = deepcopy(document)
    forged["graphs"][0]["segments"].reverse()
    forged["scoped_table_graph"]["graphs"][0]["segments"].reverse()
    material = deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "lgstv1:document:" + canonical_json_sha256_v1(material)

    numeric = project_loan_geography_numeric_input_v1(forged, snapshot["document_packet"])

    assert [item["lane_index"] for item in numeric["period_axis"]] == [0, 1]
    assert [item["period_end"] for item in numeric["period_axis"]] == [
        "2025-12-31",
        "2024-12-31",
    ]
    assert [item["source_line_index"] for item in numeric["mapped_rows"][0]["cells"]] == [5, 6]


def test_period_axis_retains_all_raw_split_header_surfaces_and_refs() -> None:
    page = _exact_page()
    page["lines"] = [item for item in page["lines"] if item["line_ordinal"] != 88]
    page["lines"].extend(
        [
            _line(88, "31 tháng 12", [650, 78, 810, 96]),
            _line(89, "năm 2025", [650, 98, 810, 114]),
        ]
    )
    snapshot = _snapshot(page)
    receipt = _receipt(snapshot)
    document = build_loan_geography_scoped_graphs_v1(receipt, [snapshot])["documents"][0]

    numeric = project_loan_geography_numeric_input_v1(document, snapshot["document_packet"])

    assert numeric["period_axis"][0]["period_end"] == "2025-12-31"
    assert numeric["period_axis"][0]["evidence_ref"] == "line:1:88|line:1:89"
    assert numeric["period_axis"][0]["source_surface"] == ("31 tháng 12 | năm 2025")
    assert numeric["period_axis"][0]["source_surface"] != "31/12/2025"


def test_conflicting_local_unit_header_fails_instead_of_selecting_first_million() -> None:
    page = _exact_page()
    page["lines"].append(_line(141, "Đơn vị tính: nghìn đồng", [820, 180, 990, 206]))
    snapshot = _snapshot(page)
    receipt = _receipt(snapshot)
    document = build_loan_geography_scoped_graphs_v1(receipt, [snapshot])["documents"][0]

    with pytest.raises(LoanGeographyScopedTableAdapterV1Error, match="local unit evidence"):
        project_loan_geography_numeric_input_v1(document, snapshot["document_packet"])


@pytest.mark.parametrize(
    "path",
    [
        ("period_key",),
        ("header_context", "unit_resolution", "magnitude_power10"),
        ("axis_centers_x2", 0),
        ("trailing_total_cells", 0, "expected_pixel_bbox", 0),
        ("role_cells", 0, "expected_pixel_bbox", 0),
    ],
)
def test_structural_fingerprint_rejects_period_unit_axis_total_or_cell_tamper(
    path: tuple[object, ...],
) -> None:
    snapshot = _snapshot(_exact_page())
    receipt = _receipt(snapshot)
    document = build_loan_geography_scoped_graphs_v1(receipt, [snapshot])["documents"][0]
    forged = deepcopy(document)

    def mutate(container: object, route: tuple[object, ...]) -> None:
        current = container
        for key in route[:-1]:
            current = current[key]  # type: ignore[index]
        key = route[-1]
        value = current[key]  # type: ignore[index]
        current[key] = value + 1 if type(value) is int else "31/12/2099"  # type: ignore[index]

    mutate(forged["scoped_table_graph"]["graphs"][0]["segments"][0], path)
    mutate(forged["graphs"][0]["segments"][0], path)
    material = deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "lgstv1:document:" + canonical_json_sha256_v1(material)
    with pytest.raises(LoanGeographyScopedTableAdapterV1Error, match="structural fingerprint"):
        compare_loan_geography_sparse_full_graphs_v1(
            document,
            forged,
            whole_document_line_count=snapshot["document_packet"]["line_count"],
            whole_document_page_count=1,
        )
