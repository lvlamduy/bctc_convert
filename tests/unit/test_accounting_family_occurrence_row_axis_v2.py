from __future__ import annotations

import copy
import hashlib
import io

import pytest
from PIL import Image, ImageDraw

from bctc_ai.evaluation import accounting_family_coextensive_parent_total_v1 as total_v1
from bctc_ai.evaluation import accounting_family_occurrence_row_axis_v2 as subject
from bctc_ai.evaluation import accounting_family_row_axis_v1 as row_v1
from bctc_ai.evaluation import accounting_family_topology_candidates_v2 as candidates_v2
from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation import family_first_authenticated_page_region_v1 as region_v1
from bctc_ai.evaluation.adaptive_accounting_table_geometry_v1 import (
    propose_missing_value_lane_regions_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _matcher(alias: str, within: str | None = None) -> dict[str, object]:
    return {"aliases": [alias], "within_role": within}


def _spec() -> dict[str, object]:
    return {
        "children": [
            {
                "matchers": [_matcher("Tiền gửi tại TCTD khác")],
                "presence": "OPTIONAL",
                "role": "DEPOSIT_GROUP",
                "role_kind": "STRUCTURAL_GROUP",
            },
            {
                "matchers": [_matcher("Bằng VND", "DEPOSIT_GROUP")],
                "presence": "OPTIONAL",
                "role": "DEPOSIT_VND",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "matchers": [_matcher("Tiền gửi có kỳ hạn")],
                "presence": "OPTIONAL",
                "role": "TERM_GROUP",
                "role_kind": "STRUCTURAL_GROUP",
            },
            {
                "matchers": [_matcher("Bằng ngoại tệ", "TERM_GROUP")],
                "presence": "OPTIONAL",
                "role": "TERM_FOREIGN_CURRENCY",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "matchers": [_matcher("Cho vay TCTD khác")],
                "presence": "OPTIONAL",
                "role": "LOAN_GROUP",
                "role_kind": "STRUCTURAL_GROUP",
            },
            {
                "matchers": [_matcher("Bằng VND", "LOAN_GROUP")],
                "presence": "OPTIONAL",
                "role": "LOAN_VND",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "matchers": [_matcher("Bằng ngoại tệ", "LOAN_GROUP")],
                "presence": "OPTIONAL",
                "role": "LOAN_FOREIGN_CURRENCY",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "matchers": [_matcher("Dự phòng rủi ro tiền gửi tại TCTD khác")],
                "presence": "OPTIONAL",
                "role": "DEPOSIT_PROVISION",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "matchers": [_matcher("Tiền gửi và cho vay TCTD khác")],
                "presence": "OPTIONAL",
                "role": "EXPLICIT_FAMILY_TOTAL",
                "role_kind": "TOTAL",
            },
        ],
        "family_id": "INTERBANK",
        "format_version": "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V3",
        "hard_negative_aliases": [],
        "limits": {
            "max_cluster_span_lines": 60,
            "max_continuation_pages": 1,
            "max_label_line_span": 3,
        },
        "parent": {
            "aliases": ["Tiền gửi và cho vay TCTD khác"],
            "resolution_mode": "EXPLICIT_ONLY",
            "role": "INTERBANK",
        },
        "presence_evidence_mode": "WITHIN_EXPLICIT_PARENT_CLUSTER",
        "required_role_combinations": [["DEPOSIT_GROUP", "LOAN_GROUP"]],
        "structural_reset_aliases": ["Tiền gửi khách hàng"],
    }


def _line(ordinal: int, text: str, numeric: str, bbox: list[int]) -> dict[str, object]:
    return {
        "bbox": bbox,
        "crop_ref": {
            "path": f"opaque/crop-{ordinal + 1:04d}.png",
            "sha256": f"{ordinal + 1:064x}",
            "size_bytes": 100 + ordinal,
        },
        "line_ordinal": ordinal,
        "numeric_recognition": {"raw_prediction": numeric, "reader_score": 0.97},
        "sample_id": f"sample-{ordinal + 1:09d}",
        "vietocr_text": text,
    }


def _row(lines: list[dict[str, object]], label: str, current: str, prior: str) -> None:
    ordinal = len(lines)
    top = 70 + ordinal * 22
    lines.extend(
        [
            _line(ordinal, label, "", [45, top, 430, top + 20]),
            _line(ordinal + 1, current, current, [610, top, 700, top + 20]),
            _line(ordinal + 2, prior, prior, [810, top, 900, top + 20]),
        ]
    )


def _pages(rows: list[tuple[str, str, str]]) -> list[dict[str, object]]:
    lines = [
        _line(0, "Tiền gửi và cho vay TCTD khác", "", [25, 15, 460, 38]),
        _line(1, "31.12.2025", "31.12.2025", [610, 45, 700, 65]),
        _line(2, "31.12.2024", "31.12.2024", [810, 45, 900, 65]),
        _line(3, "150", "150", [610, 15, 700, 38]),
        _line(4, "130", "130", [810, 15, 900, 38]),
    ]
    for row in rows:
        _row(lines, *row)
    return [{"lines": lines, "page_sequence": 1, "page_width": 1000}]


def _build(pages: list[dict[str, object]]) -> tuple[dict, dict]:
    spec = _spec()
    scan = topology_v1.build_accounting_family_topology_scan_v1(row_v1._topology_pages(pages), spec)
    assert scan["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    effective = total_v1.project_accounting_family_coextensive_parent_total_region_v1(
        spec, scan, scan["regions"][0]
    )
    axis = subject.build_accounting_family_occurrence_row_axis_v2(
        pages,
        spec,
        scan,
        scan["regions"][0],
        {
            "format_version": subject.POLICY_FORMAT_VERSION,
            "require_authenticated_existing_dash_pixels": True,
            "retain_all_context_bound_role_occurrences": True,
        },
        effective_topology_region=effective,
    )
    return scan, axis


def _ref(label: str) -> dict[str, object]:
    payload = label.encode()
    return {
        "path": f"fixture/{label}.bin",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _snapshot_and_render(
    pages: list[dict[str, object]], dash_bboxes: list[list[int]]
) -> tuple[dict, dict]:
    image = Image.new("RGB", (1000, 800), "white")
    draw = ImageDraw.Draw(image)
    for left, top, right, bottom in dash_bboxes:
        center_y = (top + bottom) // 2
        center_x = (left + right) // 2
        draw.rectangle((center_x - 8, center_y - 2, center_x + 8, center_y + 2), fill="black")
    stream = io.BytesIO()
    image.save(stream, format="PNG", optimize=False, compress_level=9)
    payload = stream.getvalue()
    render_ref = {
        "pixel_height": 800,
        "pixel_width": 1000,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    packet_material = {
        "assurance": "AUDITED",
        "bank_provenance": "SYNTHETIC",
        "document_evidence_root_sha256": hashlib.sha256(b"document-root").hexdigest(),
        "document_id": "document-occurrence-dash",
        "document_ordinal": 1,
        "line_count": len(pages[0]["lines"]),
        "page_count": 1,
        "period": "ANNUAL",
        "scope": "CONSOLIDATED",
        "source_pdf_ref": _ref("source-pdf"),
        "year": 2025,
    }
    packet = {
        **packet_material,
        "packet_id": "ffdesv1:document:" + canonical_json_sha256_v1(packet_material),
    }
    dimensions = [
        {
            "physical_page": 1,
            "pixel_height": 800,
            "pixel_width": 1000,
            "render_sha256": render_ref["sha256"],
            "render_size_bytes": render_ref["size_bytes"],
        }
    ]
    selection_material = {
        "document_id": packet["document_id"],
        "document_ordinal": 1,
        "joined_pages": pages,
        "selected_page_dimensions": dimensions,
    }
    snapshot_material = {
        "document_packet": packet,
        "joined_pages": pages,
        "manifest_id": "ffdesv1:manifest:occurrence-dash",
        "query_selection_id": "ffoqcv1:selection:" + canonical_json_sha256_v1(selection_material),
        "selected_page_dimensions": dimensions,
        "state": "AUTHENTICATED_IMMUTABLE_SQLITE_SELECTED_PAGE_EVIDENCE",
    }
    snapshot = {
        **snapshot_material,
        "snapshot_id": "ffdesv1:selected:" + canonical_json_sha256_v1(snapshot_material),
    }
    render_material = {
        "archive_id": "archive-occurrence-dash",
        "authority": dict(region_v1._RENDER_AUTHORITY),
        "document_ordinal": 1,
        "format_version": region_v1.RENDER_FORMAT_VERSION,
        "index_id": "index-occurrence-dash",
        "physical_page": 1,
        "plan_id": "plan-occurrence-dash",
        "render_ref": render_ref,
        "state": "AUTHENTICATED_EXACT_SOURCE_PAGE_RENDER_SNAPSHOT",
    }
    render = {
        **render_material,
        "render_id": "ffaprv1:render:" + canonical_json_sha256_v1(render_material),
        "render_png_bytes": payload,
    }
    return snapshot, render


def _blank_region(raw_pixel_bbox: list[int]) -> dict[str, object]:
    image = Image.new("RGB", (42, 27), "white")
    stream = io.BytesIO()
    image.save(stream, format="PNG", optimize=False, compress_level=9)
    payload = stream.getvalue()
    material = {
        "authority": dict(region_v1._REGION_AUTHORITY),
        "document_ordinal": 1,
        "format_version": region_v1.FORMAT_VERSION,
        "index_id": "index-optional-blank",
        "ink_localization_status": "GLYPH_COMPONENT_TIGHTENED_WITHIN_PROPOSED_CELL",
        "physical_page": 1,
        "proposed_raw_pixel_bbox": list(raw_pixel_bbox),
        "recognition_raw_pixel_bbox": list(raw_pixel_bbox),
        "region_png_ref": {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        },
        "render_id": "render-optional-blank",
        "render_ref": {
            "pixel_height": 1200,
            "pixel_width": 1000,
            "sha256": "1" * 64,
            "size_bytes": 100,
        },
        "state": "AUTHENTICATED_RENDER_CALLER_PROPOSED_REGION_CROP",
        "white_border": [12, 8, 12, 8],
    }
    return {
        **material,
        "region_id": "ffaprv1:region:" + canonical_json_sha256_v1(material),
        "region_png_bytes": payload,
    }


def _optional_blank_v1_axis(*, partial: bool) -> dict:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Bằng VND", "" if not partial else "70", ""),
            ("Cho vay TCTD khác", "50", "40"),
            ("Bằng VND", "50", "40"),
        ]
    )
    spec = _spec()
    scan = topology_v1.build_accounting_family_topology_scan_v1(row_v1._topology_pages(pages), spec)
    region = scan["regions"][0]
    base = row_v1._build_accounting_family_row_axis_from_authenticated_topology_scan_v1(
        pages, spec, scan, region
    )
    child = next(row for row in base["rows"] if row["role"] == "DEPOSIT_VND")
    centers, visible_cells = row_v1._resolved_page_grid_inputs(
        base["rows"], child, base["column_grids"]
    )
    proposals = propose_missing_value_lane_regions_v1(
        [{**line, "source_line_index": line["line_ordinal"]} for line in pages[0]["lines"]],
        label_boxes=[pages[0]["lines"][child["label_match"]["source_line_index"]]["bbox"]],
        is_numeric=lambda line: line["numeric_recognition"]["raw_prediction"].isdigit(),
        page_width=1000,
        page_height=1200,
        resolved_column_centers=centers,
        resolved_visible_value_cells=visible_cells,
    )
    rescues = tuple(
        {
            "column_ordinal": proposal["column_ordinal"],
            "page_sequence": 1,
            "region": _blank_region(proposal["raw_pixel_bbox"]),
            "role": "DEPOSIT_VND",
        }
        for proposal in proposals
    )
    return row_v1._build_accounting_family_row_axis_from_authenticated_topology_scan_v1(
        pages,
        spec,
        scan,
        region,
        visible_dash_rescues=rescues,
    )


@pytest.mark.parametrize(
    ("partial", "expected_status"),
    [
        (False, "VISIBLE_OPTIONAL_LABEL_ONLY_NO_VALUE_CELLS"),
        (True, "VISIBLE_OPTIONAL_PARTIAL_VALUE_ROW_WITH_BLANK_LANES"),
    ],
)
def test_existing_dash_authentication_preserves_sealed_optional_blank_status_without_dash(
    partial: bool, expected_status: str
) -> None:
    axis = _optional_blank_v1_axis(partial=partial)
    before = next(row for row in axis["rows"] if row["role"] == "DEPOSIT_VND")
    assert before["status"] == expected_status

    completed, projections, reasons = subject._authenticate_existing_dashes(
        axis,
        selected_snapshot=None,
        render_snapshots=(),
    )

    after = next(row for row in completed["rows"] if row["role"] == "DEPOSIT_VND")
    assert completed == axis
    assert after["status"] == expected_status
    assert after["values"] == before["values"]
    assert completed["visible_dash_rescues"] == axis["visible_dash_rescues"]
    assert projections == []
    assert reasons == []


def test_repeated_children_bind_nearest_parent_and_foreign_term_row_survives() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Bằng VND", "100", "90"),
            ("Tiền gửi có kỳ hạn", "30", "20"),
            ("Bằng ngoại tệ", "30", "20"),
            ("Cho vay TCTD khác", "25", "22"),
            ("Bằng VND", "20", "18"),
            ("Bằng ngoại tệ", "5", "4"),
            ("Cho vay TCTD khác", "12", "10"),
            ("Bằng VND", "9", "8"),
            ("Bằng ngoại tệ", "3", "2"),
        ]
    )
    _scan, axis = _build(pages)

    occurrences = axis["role_occurrences"]
    loan_groups = [item for item in occurrences if item["role"] == "LOAN_GROUP"]
    loan_foreign = [item for item in occurrences if item["role"] == "LOAN_FOREIGN_CURRENCY"]
    assert len(loan_groups) == len(loan_foreign) == 2
    assert [item["scope_owner_occurrence_id"] for item in loan_foreign] == [
        item["occurrence_id"] for item in loan_groups
    ]
    assert any(item["role"] == "TERM_FOREIGN_CURRENCY" for item in occurrences)
    assert axis["status"] == (
        "OCCURRENCE_ROW_AXIS_BOUND_WITH_AUTHENTICATED_EXISTING_DASHES_PROPOSAL_ONLY"
    )


def test_projected_owner_and_wrapped_provision_bind_but_reset_footer_does_not() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Bằng VND", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
            ("Bằng VND", "50", "40"),
        ]
    )
    lines = pages[0]["lines"]
    ordinal = len(lines)
    top = 70 + ordinal * 22
    lines.extend(
        [
            _line(ordinal, "Dự phòng rủi ro tiền gửi tại", "", [45, top, 380, top + 20]),
            _line(ordinal + 1, "TCTD khác", "", [45, top + 21, 250, top + 41]),
            _line(ordinal + 2, "-5", "-5", [610, top + 21, 700, top + 41]),
            _line(ordinal + 3, "-4", "-4", [810, top + 21, 900, top + 41]),
            _line(ordinal + 4, "Tiền gửi khách hàng", "", [45, top + 70, 380, top + 90]),
            _line(ordinal + 5, "999", "999", [610, top + 70, 700, top + 90]),
            _line(ordinal + 6, "888", "888", [810, top + 70, 900, top + 90]),
            _line(ordinal + 7, "21", "21", [810, top + 110, 900, top + 130]),
        ]
    )
    _scan, axis = _build(pages)

    rows = {row["role"]: row for row in axis["row_axis"]["rows"]}
    assert [
        item["parsed_token"]["coefficient"] for item in rows["EXPLICIT_FAMILY_TOTAL"]["values"]
    ] == [
        150,
        130,
    ]
    assert [
        item["parsed_token"]["coefficient"] for item in rows["DEPOSIT_PROVISION"]["values"]
    ] == [
        -5,
        -4,
    ]
    assert axis["row_axis"]["trailing_value_rows"] == []


def test_effective_region_injection_fails_closed() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Bằng VND", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
            ("Bằng VND", "50", "40"),
        ]
    )
    scan, axis = _build(pages)
    forged = copy.deepcopy(scan["regions"][0])
    forged["child_matches"][0]["role"] = "FORGED_ROLE"
    forged["observed_roles"][0] = "FORGED_ROLE"

    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error, match="closed generic projector"
    ):
        subject.build_accounting_family_occurrence_row_axis_v2(
            pages,
            _spec(),
            scan,
            scan["regions"][0],
            {
                "format_version": subject.POLICY_FORMAT_VERSION,
                "require_authenticated_existing_dash_pixels": True,
                "retain_all_context_bound_role_occurrences": True,
            },
            effective_topology_region=forged,
        )


def test_prepruning_candidate_envelope_is_replayed_and_bound_in_result() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
            ("Tiền gửi và cho vay TCTD khác", "200", "180"),
            ("Tiền gửi tại TCTD khác", "120", "110"),
            ("Cho vay TCTD khác", "80", "70"),
            ("Bằng VND", "80", "70"),
        ]
    )
    spec = _spec()
    topology_pages = row_v1._topology_pages(pages)
    scan = topology_v1.build_accounting_family_topology_scan_v1(topology_pages, spec)
    candidates = candidates_v2.build_accounting_family_topology_candidates_v2(topology_pages, spec)
    summary_region = candidates["regions"][0]
    assert len(candidates["regions"]) == 2
    assert summary_region not in scan["regions"]
    assert summary_region["observed_roles"] == ["DEPOSIT_GROUP", "LOAN_GROUP"]
    binding = candidates_v2.bind_accounting_family_topology_candidate_v2(
        topology_pages, spec, candidates, summary_region
    )

    axis = subject.build_accounting_family_occurrence_row_axis_v2(
        pages,
        spec,
        scan,
        summary_region,
        {
            "format_version": subject.POLICY_FORMAT_VERSION,
            "require_authenticated_existing_dash_pixels": True,
            "retain_all_context_bound_role_occurrences": True,
        },
        effective_topology_region=binding["effective_topology_region"],
        topology_candidates=candidates,
    )

    assert axis["topology_candidates_id"] == candidates["result_id"]
    assert axis["topology_scan_id"] == scan["scan_id"]


def test_two_authenticated_dash_lanes_survive_and_coherent_rehash_replay_fails() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Bằng VND", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
            ("Bằng VND", "50", "40"),
            ("Dự phòng rủi ro tiền gửi tại TCTD khác", "-", "-"),
        ]
    )
    dash_lines = [line for line in pages[0]["lines"] if line["vietocr_text"] == "-"]
    snapshot, render = _snapshot_and_render(pages, [line["bbox"] for line in dash_lines])
    spec = _spec()
    scan = topology_v1.build_accounting_family_topology_scan_v1(row_v1._topology_pages(pages), spec)
    effective = total_v1.project_accounting_family_coextensive_parent_total_region_v1(
        spec, scan, scan["regions"][0]
    )
    axis = subject.build_accounting_family_occurrence_row_axis_v2(
        pages,
        spec,
        scan,
        scan["regions"][0],
        {
            "format_version": subject.POLICY_FORMAT_VERSION,
            "require_authenticated_existing_dash_pixels": True,
            "retain_all_context_bound_role_occurrences": True,
        },
        effective_topology_region=effective,
        selected_snapshot=snapshot,
        render_snapshots=(render,),
    )

    provision = next(row for row in axis["row_axis"]["rows"] if row["role"] == "DEPOSIT_PROVISION")
    assert [value["parsed_token"]["coefficient"] for value in provision["values"]] == [0, 0]
    assert [item["status"] for item in axis["authenticated_existing_dash_evidence"]] == [
        "AUTHENTICATED_VISIBLE_EXISTING_CELL_DASH_ZERO",
        "AUTHENTICATED_VISIBLE_EXISTING_CELL_DASH_ZERO",
    ]
    assert axis["status"] == (
        "OCCURRENCE_ROW_AXIS_BOUND_WITH_AUTHENTICATED_EXISTING_DASHES_PROPOSAL_ONLY"
    )

    blank_snapshot, blank_render = _snapshot_and_render(pages, [])
    blank_axis = subject.build_accounting_family_occurrence_row_axis_v2(
        pages,
        spec,
        scan,
        scan["regions"][0],
        {
            "format_version": subject.POLICY_FORMAT_VERSION,
            "require_authenticated_existing_dash_pixels": True,
            "retain_all_context_bound_role_occurrences": True,
        },
        effective_topology_region=effective,
        selected_snapshot=blank_snapshot,
        render_snapshots=(blank_render,),
    )
    blank_provision = next(
        row for row in blank_axis["row_axis"]["rows"] if row["role"] == "DEPOSIT_PROVISION"
    )
    assert blank_provision["values"] == []
    assert blank_provision["missing_column_ordinals"] == [0, 1]
    assert blank_axis["status"] == "UNRESOLVED_OCCURRENCE_ROW_AXIS_OR_EXISTING_DASH_EVIDENCE"

    attacked = copy.deepcopy(axis)
    attacked["unresolved_reasons"] = ["COHERENT_REHASH_FORGED_REASON"]
    attacked["status"] = "UNRESOLVED_OCCURRENCE_ROW_AXIS_OR_EXISTING_DASH_EVIDENCE"
    material = copy.deepcopy(attacked)
    material.pop("occurrence_axis_id")
    attacked["occurrence_axis_id"] = "aforav2:axis:" + canonical_json_sha256_v1(material)
    with pytest.raises(subject.AccountingFamilyOccurrenceRowAxisV2Error, match="replay exactly"):
        subject.validate_accounting_family_occurrence_row_axis_replay_v2(
            attacked,
            pages,
            _spec(),
            scan,
            scan["regions"][0],
            {
                "format_version": subject.POLICY_FORMAT_VERSION,
                "require_authenticated_existing_dash_pixels": True,
                "retain_all_context_bound_role_occurrences": True,
            },
            effective_topology_region=total_v1.project_accounting_family_coextensive_parent_total_region_v1(
                _spec(), scan, scan["regions"][0]
            ),
            selected_snapshot=snapshot,
            render_snapshots=(render,),
        )
