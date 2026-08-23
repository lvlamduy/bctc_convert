from __future__ import annotations

import copy
import hashlib
import os
import sys
from pathlib import Path
from typing import Any

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(_ROOT))

from scripts.experiments import customer_loan_total_control_v1 as control_v1  # noqa: E402


def _surfaces() -> list[tuple[str, int, int]]:
    return [
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


def _packet(*, bank: str = "TEST") -> dict[str, Any]:
    material = {
        "assurance": "UNAUDITED",
        "bank_provenance": bank,
        "document_evidence_root_sha256": "1" * 64,
        "document_id": "ffsiv1:document:" + "2" * 64,
        "document_ordinal": 1,
        "line_count": len(_surfaces()),
        "page_count": 1,
        "period": "Q2",
        "scope": "CONSOLIDATED",
        "source_pdf_ref": {"path": "test.pdf", "sha256": "3" * 64, "size_bytes": 1},
        "year": 2026,
    }
    return {
        **material,
        "packet_id": "ffdesv1:document:" + canonical_json_sha256_v1(material),
    }


def _snapshot(*, bank: str = "TEST") -> dict[str, Any]:
    lines = []
    for index, (text, x, y) in enumerate(_surfaces()):
        sample_id = f"sample-{index:03d}"
        lines.append(
            {
                "bbox": [x, y, x + 160, y + 24],
                "crop_ref": {
                    "path": f"crop/{sample_id}.png",
                    "sha256": hashlib.sha256(sample_id.encode()).hexdigest(),
                    "size_bytes": 1,
                },
                "line_ordinal": index,
                "numeric_recognition": {
                    "raw_prediction": text,
                    "reader_score": 0.999,
                },
                "sample_id": sample_id,
                "vietocr_text": text,
            }
        )
    material = {
        "document_packet": _packet(bank=bank),
        "joined_pages": [{"lines": lines, "page_sequence": 1, "page_width": 1200}],
        "manifest_id": "ffdesv1:manifest:" + "4" * 64,
        "query_selection_id": "ffoqcv1:selection:" + "5" * 64,
        "selected_page_dimensions": [
            {
                "physical_page": 1,
                "pixel_height": 600,
                "pixel_width": 1200,
                "render_sha256": "6" * 64,
                "render_size_bytes": 1,
            }
        ],
        "state": "AUTHENTICATED_IMMUTABLE_SQLITE_SELECTED_PAGE_EVIDENCE",
    }
    return {
        **material,
        "snapshot_id": "ffdesv1:selected:" + canonical_json_sha256_v1(material),
    }


def _rehash_snapshot(snapshot: dict[str, Any]) -> None:
    material = copy.deepcopy(snapshot)
    material.pop("snapshot_id")
    snapshot["snapshot_id"] = "ffdesv1:selected:" + canonical_json_sha256_v1(material)


def _rehash_packet_and_snapshot(snapshot: dict[str, Any]) -> None:
    packet = snapshot["document_packet"]
    packet_material = copy.deepcopy(packet)
    packet_material.pop("packet_id")
    packet["packet_id"] = "ffdesv1:document:" + canonical_json_sha256_v1(packet_material)
    _rehash_snapshot(snapshot)


def _rehash_result(value: dict[str, Any]) -> None:
    material = copy.deepcopy(value)
    material.pop("result_id")
    value["result_id"] = "cltcv1:result:" + canonical_json_sha256_v1(material)


def _rehash_nested_result(value: dict[str, Any], *, prefix: str) -> None:
    material = copy.deepcopy(value)
    material.pop("result_id")
    value["result_id"] = prefix + canonical_json_sha256_v1(material)


def _coherently_rewrite_outer_total(value: dict[str, Any], parsed_value: int) -> None:
    value["total_control"]["parsed_value"] = parsed_value
    check = value["total_control"]["accounting_corroboration"]
    check["observed_additive_sum"] = parsed_value
    check["target_total"] = parsed_value
    _rehash_result(value)


def _coherently_rewrite_all_total_layers(value: dict[str, Any], parsed_value: int) -> None:
    surface = str(parsed_value)
    graph = value["loan_type_graph_result"]
    graph_total = next(item for item in graph["graphs"][0]["total"] if item["lane_index"] == 0)
    graph_total["semantic_surface"] = surface
    _rehash_nested_result(graph, prefix="ltvgv1:result:")

    numeric = value["loan_type_numeric_result"]
    numeric["graph_result_id"] = graph["result_id"]
    numeric_total = next(item for item in numeric["total"] if item["lane_index"] == 0)
    numeric_total["parsed_value"] = parsed_value
    numeric_total["ppocrv6_surface"] = surface
    numeric_total["semantic_surface"] = surface
    numeric_check = next(item for item in numeric["accounting_checks"] if item["lane_index"] == 0)
    numeric_check["observed_additive_sum"] = parsed_value
    numeric_check["target_total"] = parsed_value
    _rehash_nested_result(numeric, prefix="ltnrrv1:result:")

    total = value["total_control"]
    total["parsed_value"] = parsed_value
    total["source"]["ppocrv6_surface"] = surface
    total["source"]["vietocr_transformer_surface"] = surface
    total["accounting_corroboration"] = copy.deepcopy(numeric_check)
    _rehash_result(value)


def _line(snapshot: dict[str, Any], surface: str, *, occurrence: int = 0) -> dict[str, Any]:
    matches = [
        line
        for page in snapshot["joined_pages"]
        for line in page["lines"]
        if line["vietocr_text"] == surface
    ]
    return matches[occurrence]


def test_build_and_public_replay_bind_one_exact_printed_total_control() -> None:
    snapshot = _snapshot()

    built = control_v1.build_customer_loan_total_control_v1(snapshot, "30/06/2026")
    typed = control_v1.validate_customer_loan_total_control_v1(built)
    replayed = control_v1.validate_customer_loan_total_control_replay_v1(
        built, snapshot, "30/06/2026"
    )

    assert typed == built
    assert replayed == built
    assert built["period_lane"]["lane_index"] == 0
    assert built["period_lane"]["evidence"][0]["source_line_index"] == 1
    assert built["unit_evidence"] == {
        "currency": "VND",
        "lane_index": 0,
        "magnitude_power10": 6,
        "mode": "LOCAL_PER_LANE",
        "normalized_surface": "trieu dong",
        "source": built["unit_evidence"]["source"],
        "surface": "Triệu đồng",
    }
    assert built["total_control"]["parsed_value"] == 120
    assert built["total_control"]["source"]["sample_id"] == "sample-020"
    assert built["total_control"]["source"]["ppocrv6_surface"] == "120"
    assert built["total_control"]["source"]["page_render"] == {
        "physical_page": 1,
        "pixel_height": 600,
        "pixel_width": 1200,
        "render_sha256": "6" * 64,
        "render_size_bytes": 1,
    }
    assert built["authority"]["arithmetic_backsolve_used"] is False
    assert built["authority"]["authenticated_store_capability_required_by_caller"] is True
    assert built["authority"]["e0164_persisted_result_used_as_authority"] is False
    assert built["authority"]["snapshot_self_hash_is_not_source_authentication_authority"] is True
    assert built["authority"]["targeted_pixel_or_numeric_rescue_allowed"] is False


def test_cheap_validator_is_typed_only_and_public_replay_remains_source_authority() -> None:
    snapshot = _snapshot()
    built = control_v1.build_customer_loan_total_control_v1(snapshot, "30/06/2026")
    coherent = copy.deepcopy(built)
    _coherently_rewrite_all_total_layers(coherent, 121)

    # A coherent self-rehash can pass the deliberately cheap envelope gate.
    # It gains no source authority because exact replay still rebuilds.
    assert control_v1.validate_customer_loan_total_control_v1(coherent) == coherent
    with pytest.raises(
        control_v1.CustomerLoanTotalControlV1Error,
        match="upstream public replay failed|does not replay exactly",
    ):
        control_v1.validate_customer_loan_total_control_replay_v1(coherent, snapshot, "30/06/2026")


def test_cheap_validator_rejects_stale_identity_and_malformed_locator() -> None:
    built = control_v1.build_customer_loan_total_control_v1(_snapshot(), "30/06/2026")

    stale = copy.deepcopy(built)
    stale["total_control"]["parsed_value"] = 121
    with pytest.raises(
        control_v1.CustomerLoanTotalControlV1Error,
        match="result identity drifted",
    ):
        control_v1.validate_customer_loan_total_control_v1(stale)

    malformed = copy.deepcopy(built)
    malformed["total_control"]["source"]["page_render"]["physical_page"] = 2
    _rehash_result(malformed)
    with pytest.raises(
        control_v1.CustomerLoanTotalControlV1Error,
        match="total locator identity drifted",
    ):
        control_v1.validate_customer_loan_total_control_v1(malformed)


def test_cheap_validator_rejects_outer_total_that_conflicts_with_nested_evidence() -> None:
    snapshot = _snapshot()
    built = control_v1.build_customer_loan_total_control_v1(snapshot, "30/06/2026")
    forged = copy.deepcopy(built)
    _coherently_rewrite_outer_total(forged, 121)

    with pytest.raises(
        control_v1.CustomerLoanTotalControlV1Error,
        match="selected nested total binding drifted",
    ):
        control_v1.validate_customer_loan_total_control_v1(forged)


def test_cheap_validator_recomputes_requested_period_to_money_lane_binding() -> None:
    snapshot = _snapshot()
    current = control_v1.build_customer_loan_total_control_v1(snapshot, "30/06/2026")
    comparative = control_v1.build_customer_loan_total_control_v1(snapshot, "31/12/2025")
    forged = copy.deepcopy(current)
    forged["period_lane"]["lane_index"] = comparative["period_lane"]["lane_index"]
    forged["unit_evidence"] = copy.deepcopy(comparative["unit_evidence"])
    forged["total_control"] = copy.deepcopy(comparative["total_control"])
    _rehash_result(forged)

    with pytest.raises(
        control_v1.CustomerLoanTotalControlV1Error,
        match="period lane drifted",
    ):
        control_v1.validate_customer_loan_total_control_v1(forged)


def test_cheap_validator_recomputes_normalized_unit_surface() -> None:
    built = control_v1.build_customer_loan_total_control_v1(_snapshot(), "30/06/2026")
    forged = copy.deepcopy(built)
    forged["unit_evidence"]["normalized_surface"] = "forged"
    _rehash_result(forged)

    with pytest.raises(
        control_v1.CustomerLoanTotalControlV1Error,
        match="normalized unit binding drifted",
    ):
        control_v1.validate_customer_loan_total_control_v1(forged)


def test_replay_rejects_another_document_root_even_when_snapshot_is_rehashed() -> None:
    snapshot = _snapshot()
    built = control_v1.build_customer_loan_total_control_v1(snapshot, "30/06/2026")
    wrong = copy.deepcopy(snapshot)
    wrong["document_packet"]["document_evidence_root_sha256"] = "9" * 64
    _rehash_packet_and_snapshot(wrong)

    with pytest.raises(
        control_v1.CustomerLoanTotalControlV1Error,
        match="does not replay exactly",
    ):
        control_v1.validate_customer_loan_total_control_replay_v1(built, wrong, "30/06/2026")


def test_replay_rejects_wrong_requested_period() -> None:
    snapshot = _snapshot()
    built = control_v1.build_customer_loan_total_control_v1(snapshot, "30/06/2026")

    with pytest.raises(
        control_v1.CustomerLoanTotalControlV1Error,
        match="requested period replay drifted",
    ):
        control_v1.validate_customer_loan_total_control_replay_v1(built, snapshot, "31/12/2025")


@pytest.mark.parametrize("requested", ["2026-06-30", "31/02/2026", True])
def test_requested_period_requires_one_exact_valid_date(requested: Any) -> None:
    with pytest.raises(control_v1.CustomerLoanTotalControlV1Error):
        control_v1.build_customer_loan_total_control_v1(_snapshot(), requested)


def test_build_rejects_missing_or_multiple_requested_period() -> None:
    snapshot = _snapshot()
    with pytest.raises(
        control_v1.CustomerLoanTotalControlV1Error,
        match="requested period is missing or multiple",
    ):
        control_v1.build_customer_loan_total_control_v1(snapshot, "31/03/2026")

    duplicate = _snapshot()
    comparative = _line(duplicate, "31/12/2025")
    comparative["vietocr_text"] = "30/06/2026"
    comparative["numeric_recognition"]["raw_prediction"] = "30/06/2026"
    _rehash_snapshot(duplicate)
    with pytest.raises(
        control_v1.CustomerLoanTotalControlV1Error,
        match="requested period is missing or multiple",
    ):
        control_v1.build_customer_loan_total_control_v1(duplicate, "30/06/2026")


def test_build_rejects_non_exact_owner_and_non_million_unit() -> None:
    owner_drift = _snapshot()
    owner = _line(owner_drift, "5. CHO VAY KHÁCH HÀNG")
    owner["vietocr_text"] = "5. CHO VAY KHÁCH HÀN"
    owner["numeric_recognition"]["raw_prediction"] = owner["vietocr_text"]
    _rehash_snapshot(owner_drift)
    with pytest.raises(
        control_v1.CustomerLoanTotalControlV1Error,
        match="exact owner/table binding drifted",
    ):
        control_v1.build_customer_loan_total_control_v1(owner_drift, "30/06/2026")

    wrong_unit = _snapshot()
    unit = _line(wrong_unit, "Triệu đồng")
    unit["vietocr_text"] = "Nghìn đồng"
    unit["numeric_recognition"]["raw_prediction"] = "Nghìn đồng"
    _rehash_snapshot(wrong_unit)
    with pytest.raises(
        control_v1.CustomerLoanTotalControlV1Error,
        match="not exact million VND",
    ):
        control_v1.build_customer_loan_total_control_v1(wrong_unit, "30/06/2026")


def test_build_rejects_unresolved_pp_total_without_rescue_or_backsolve() -> None:
    snapshot = _snapshot()
    total = _line(snapshot, "120")
    total["numeric_recognition"]["raw_prediction"] = ""
    _rehash_snapshot(snapshot)

    with pytest.raises(
        control_v1.CustomerLoanTotalControlV1Error,
        match="requires exact base PP numeric evidence",
    ):
        control_v1.build_customer_loan_total_control_v1(snapshot, "30/06/2026")


def test_snapshot_rejects_bool_line_ordinal_and_partial_page_denominator() -> None:
    boolean = _snapshot()
    boolean["joined_pages"][0]["lines"][0]["line_ordinal"] = False
    _rehash_snapshot(boolean)
    with pytest.raises(control_v1.CustomerLoanTotalControlV1Error, match="source line identity"):
        control_v1.build_customer_loan_total_control_v1(boolean, "30/06/2026")

    partial = _snapshot()
    partial["document_packet"]["page_count"] = 2
    _rehash_packet_and_snapshot(partial)
    with pytest.raises(
        control_v1.CustomerLoanTotalControlV1Error,
        match="complete page denominator",
    ):
        control_v1.build_customer_loan_total_control_v1(partial, "30/06/2026")


def test_full_snapshot_may_omit_authenticated_zero_line_page_from_joined_axis() -> None:
    snapshot = _snapshot()
    snapshot["document_packet"]["page_count"] = 2
    snapshot["selected_page_dimensions"].append(
        {
            "physical_page": 2,
            "pixel_height": 600,
            "pixel_width": 1200,
            "render_sha256": "7" * 64,
            "render_size_bytes": 1,
        }
    )
    _rehash_packet_and_snapshot(snapshot)

    result = control_v1.build_customer_loan_total_control_v1(snapshot, "30/06/2026")

    assert result["document_binding"]["page_count"] == 2
    assert result["total_control"]["parsed_value"] == 120


def test_replay_rejects_self_rehashed_upstream_graph_and_numeric_tamper() -> None:
    snapshot = _snapshot()
    built = control_v1.build_customer_loan_total_control_v1(snapshot, "30/06/2026")

    graph_forged = copy.deepcopy(built)
    graph = graph_forged["loan_type_graph_result"]
    graph["graphs"][0]["owner"]["surface"] = "FORGED OWNER"
    _rehash_nested_result(graph, prefix="ltvgv1:result:")
    graph_forged["loan_type_numeric_result"]["graph_result_id"] = graph["result_id"]
    _rehash_nested_result(graph_forged["loan_type_numeric_result"], prefix="ltnrrv1:result:")
    _rehash_result(graph_forged)
    with pytest.raises(
        control_v1.CustomerLoanTotalControlV1Error,
        match="owner evidence drifted|upstream public replay failed",
    ):
        control_v1.validate_customer_loan_total_control_replay_v1(
            graph_forged, snapshot, "30/06/2026"
        )

    numeric_forged = copy.deepcopy(built)
    numeric = numeric_forged["loan_type_numeric_result"]
    numeric["total"][0]["parsed_value"] = 121
    _rehash_nested_result(numeric, prefix="ltnrrv1:result:")
    _rehash_result(numeric_forged)
    with pytest.raises(
        control_v1.CustomerLoanTotalControlV1Error,
        match="selected nested total binding drifted|upstream public replay failed",
    ):
        control_v1.validate_customer_loan_total_control_replay_v1(
            numeric_forged, snapshot, "30/06/2026"
        )


@pytest.mark.parametrize("field", ["render_sha256", "pixel_width", "crop_sha256"])
def test_replay_rejects_self_rehashed_render_dimension_and_crop_tamper(field: str) -> None:
    snapshot = _snapshot()
    built = control_v1.build_customer_loan_total_control_v1(snapshot, "30/06/2026")
    forged = copy.deepcopy(built)
    source = forged["total_control"]["source"]
    if field == "render_sha256":
        source["page_render"]["render_sha256"] = "8" * 64
    elif field == "pixel_width":
        source["page_render"]["pixel_width"] = 1300
    else:
        source["crop_ref"]["sha256"] = "9" * 64
    _rehash_result(forged)

    with pytest.raises(
        control_v1.CustomerLoanTotalControlV1Error,
        match="does not replay exactly",
    ):
        control_v1.validate_customer_loan_total_control_replay_v1(forged, snapshot, "30/06/2026")


def test_bank_metadata_is_bound_but_never_routes_total_selection() -> None:
    first = control_v1.build_customer_loan_total_control_v1(_snapshot(bank="FIRST"), "30/06/2026")
    second = control_v1.build_customer_loan_total_control_v1(_snapshot(bank="SECOND"), "30/06/2026")

    assert first["loan_type_graph_result"] == second["loan_type_graph_result"]
    assert first["loan_type_numeric_result"] == second["loan_type_numeric_result"]
    assert first["total_control"] == second["total_control"]
    assert (
        first["document_binding"]["document_packet_id"]
        != second["document_binding"]["document_packet_id"]
    )
