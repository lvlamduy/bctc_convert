from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from bctc_ai.evaluation.loan_geography_numeric_reconciliation_v1 import (
    build_loan_geography_numeric_reconciliation_v1,
)
from bctc_ai.evaluation.loan_geography_scoped_table_adapter_v1 import (
    FAMILY_ID,
    LOAN_GEOGRAPHY_REGION_QUERY_SPEC_V2,
    LOAN_GEOGRAPHY_SCOPED_TABLE_ALIAS_PROVENANCE_V1,
    LOAN_GEOGRAPHY_SCOPED_TABLE_SPEC_V1,
    LoanGeographyScopedTableAdapterV1Error,
    build_loan_geography_document_context_v1,
    build_loan_geography_region_query_spec_v2,
    build_loan_geography_scoped_graphs_v1,
    build_loan_geography_whole_document_scoped_graph_v1,
    compare_loan_geography_sparse_full_graphs_v1,
    project_loan_geography_numeric_input_v1,
    project_loan_geography_visible_dash_graph_v1,
    validate_loan_geography_document_context_replay_v1,
    validate_loan_geography_scoped_graphs_replay_v1,
    validate_loan_geography_whole_document_scoped_graph_replay_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


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
