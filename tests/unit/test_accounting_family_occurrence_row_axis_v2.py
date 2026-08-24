from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from bctc_ai.evaluation import accounting_family_coextensive_parent_total_v1 as total_v1
from bctc_ai.evaluation import accounting_family_occurrence_row_axis_v2 as subject
from bctc_ai.evaluation import accounting_family_row_axis_v1 as row_v1
from bctc_ai.evaluation import accounting_family_topology_candidates_v2 as candidates_v2
from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation import accounting_scoped_hierarchical_table_closure_v2 as closure_v2
from bctc_ai.evaluation import authenticated_semantic_region_snapshot_v1 as snapshot_v1
from bctc_ai.evaluation import family_first_authenticated_page_region_v1 as region_v1
from bctc_ai.evaluation.adaptive_accounting_table_geometry_v1 import (
    propose_missing_value_lane_regions_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_F3_TOPOLOGY_PATH = _PROJECT_ROOT / "config/families/tm-interbank-deposits-loans-topology-v4.json"
_F3_EVALUATION_PATH = (
    _PROJECT_ROOT / "config/families/tm-interbank-deposits-loans-evaluation-v4.json"
)


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


def test_numeric_universe_owns_internal_money_samples_but_excludes_header_dates() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
        ]
    )
    lines = pages[0]["lines"]
    lines[8:8] = [
        _line(999, "7", "7", [610, 213, 700, 233]),
        _line(1_000, "-2", "-2", [810, 213, 900, 233]),
    ]
    for ordinal, line in enumerate(lines):
        line["line_ordinal"] = ordinal
        line["sample_id"] = f"sample-{ordinal + 1:09d}"
        line["crop_ref"] = {
            "path": f"opaque/crop-{ordinal + 1:04d}.png",
            "sha256": f"{ordinal + 1:064x}",
            "size_bytes": 100 + ordinal,
        }

    _scan, axis = _build(pages)

    cluster = axis["internal_unassigned_numeric_clusters"]
    assert len(cluster) == 1
    assert cluster[0]["column_ordinals"] == [0, 1]
    universe = {sample["sample_id"]: sample for sample in axis["numeric_sample_universe"]}
    assert set(cluster[0]["sample_ids"]) <= set(universe)
    assert {universe[sample_id]["owner_kind"] for sample_id in cluster[0]["sample_ids"]} == {
        "SOURCE_ONLY_INTERNAL_CLUSTER"
    }
    assert lines[1]["sample_id"] not in universe
    assert lines[2]["sample_id"] not in universe
    owned_sample_ids = [
        value["sample_id"] for row in axis["row_axis"]["rows"] for value in row["values"]
    ]
    owned_sample_ids.extend(
        sample_id
        for evidence in axis["coextensive_structural_numeric_evidence"]
        if evidence["status"] == total_v1.COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_STATUS
        for sample_id in evidence["source_sample_ids"]
    )
    assert set(universe) == {*owned_sample_ids, *cluster[0]["sample_ids"]}

    attacked = copy.deepcopy(axis)
    attacked_sample = next(
        sample
        for sample in attacked["numeric_sample_universe"]
        if sample["owner_kind"] == "SOURCE_ONLY_INTERNAL_CLUSTER"
    )
    attacked_sample["owner_id"] = "aforav2:unassigned:forged"
    material = copy.deepcopy(attacked)
    material.pop("occurrence_axis_id")
    attacked["occurrence_axis_id"] = "aforav2:axis:" + canonical_json_sha256_v1(material)
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="internal cluster differs",
    ):
        subject._validate_result(attacked)


def test_numeric_universe_types_body_off_lane_number_but_excludes_header_and_footer() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
        ]
    )
    lines = pages[0]["lines"]
    lines[8:8] = [_line(999, "17", "17", [940, 213, 990, 233])]
    lines.append(_line(1_000, "19", "19", [940, 700, 990, 720]))
    _reindex_page_lines(lines)

    _scan, axis = _build(pages)

    clusters = axis["internal_unassigned_numeric_clusters"]
    assert len(clusters) == 1
    assert clusters[0]["status"] == "SOURCE_ONLY_OFF_LANE_NUMERIC_CLUSTER"
    assert len(clusters[0]["sample_ids"]) == 1
    universe = {sample["sample_id"]: sample for sample in axis["numeric_sample_universe"]}
    assert clusters[0]["sample_ids"][0] in universe
    assert lines[1]["sample_id"] not in universe
    assert lines[2]["sample_id"] not in universe
    assert lines[-1]["sample_id"] not in universe


def test_prose_candidate_with_empty_v1_grid_is_typed_unresolved_without_margin_numeric() -> None:
    pages = [
        {
            "lines": [
                _line(0, "Tiền gửi và cho vay TCTD khác", "", [45, 70, 460, 92]),
                _line(1, "Tiền gửi tại TCTD khác", "", [45, 110, 430, 132]),
                _line(2, "được ghi nhận theo giá gốc", "", [45, 140, 500, 162]),
                _line(3, "Cho vay TCTD khác", "", [45, 180, 430, 202]),
                _line(
                    4,
                    "được phân loại vào tài sản tài chính",
                    "",
                    [45, 210, 520, 232],
                ),
                _line(5, "1", "1", [10, 760, 22, 780]),
            ],
            "page_sequence": 1,
            "page_width": 1000,
        }
    ]

    _scan, axis = _build(pages)

    assert axis["row_axis"]["column_grids"] == [
        {
            "column_centers": [],
            "geometry_status": "BODY_DERIVED_NUMERIC_COLUMN_GRID",
            "header_evidence_source_line_indices": [],
            "page_sequence": 1,
        }
    ]
    assert axis["numeric_sample_universe"] == []
    assert axis["internal_unassigned_numeric_clusters"] == []
    assert axis["status"] == "UNRESOLVED_OCCURRENCE_ROW_AXIS_OR_EXISTING_DASH_EVIDENCE"
    assert axis["unresolved_reasons"] == ["VISIBLE_ROLE_OCCURRENCE_ROW_LANES_NOT_COMPLETE"]


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


def test_prepared_snapshot_projection_matches_public_build_without_replay(monkeypatch) -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Bằng VND", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
            ("Bằng VND", "50", "40"),
        ]
    )
    snapshot, _render = _snapshot_and_render(pages, [])
    expected_projection = snapshot_v1.build_authenticated_semantic_region_snapshot_v1(snapshot)
    prepared = subject._prepare_authenticated_snapshot_projection_v2(snapshot)
    typed_snapshot, projection = subject._prepared_authenticated_snapshot_projection_authority_v2(
        prepared
    )

    assert projection == expected_projection
    monkeypatch.setattr(
        snapshot_v1,
        "build_authenticated_semantic_region_snapshot_v1",
        lambda *_args, **_kwargs: pytest.fail("prepared occurrence rebuilt the snapshot"),
    )
    monkeypatch.setattr(
        snapshot_v1,
        "validate_authenticated_semantic_region_snapshot_replay_v1",
        lambda *_args, **_kwargs: pytest.fail("prepared occurrence replayed the snapshot"),
    )
    monkeypatch.setattr(
        subject,
        "_prepared_authenticated_snapshot_projection_authority_v2",
        lambda *_args, **_kwargs: pytest.fail("prepared occurrence rehashed the full snapshot"),
    )

    subject._validate_snapshot_and_renders(
        row_v1._pages(typed_snapshot["joined_pages"]),
        typed_snapshot,
        (),
        prepared_snapshot=prepared,
    )
    typed_snapshot["joined_pages"][0]["lines"][0]["vietocr_text"] = "MUTATED AFTER OPEN"
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="projection binding drifted",
    ):
        subject._validate_snapshot_and_renders(
            row_v1._pages(typed_snapshot["joined_pages"]),
            typed_snapshot,
            (),
            prepared_snapshot=prepared,
        )


def test_prepared_candidate_binding_skips_document_topology_replay(monkeypatch) -> None:
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
    prepared = candidates_v2._prepare_accounting_family_topology_candidates_v2(
        topology_pages,
        spec,
    )
    scan, candidates, bindings = candidates_v2._prepared_accounting_family_topology_authority_v2(
        prepared
    )
    monkeypatch.setattr(
        candidates_v2,
        "bind_accounting_family_topology_candidate_v2",
        lambda *_args, **_kwargs: pytest.fail("prepared binding replayed full topology"),
    )

    axis = subject._build_accounting_family_occurrence_row_axis_from_authenticated_topology_scan_v2(
        pages,
        spec,
        scan,
        candidates["regions"][0],
        {
            "format_version": subject.POLICY_FORMAT_VERSION,
            "require_authenticated_existing_dash_pixels": True,
            "retain_all_context_bound_role_occurrences": True,
        },
        topology_candidates=candidates,
        prepared_topology_binding=bindings[0],
    )

    assert axis["topology_candidates_id"] == candidates["result_id"]
    assert axis["topology_scan_id"] == scan["scan_id"]

    changed_spec = copy.deepcopy(spec)
    changed_spec["limits"]["max_cluster_span_lines"] -= 1
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="candidate replay failed",
    ):
        subject._build_accounting_family_occurrence_row_axis_from_authenticated_topology_scan_v2(
            pages,
            changed_spec,
            scan,
            candidates["regions"][0],
            {
                "format_version": subject.POLICY_FORMAT_VERSION,
                "require_authenticated_existing_dash_pixels": True,
                "retain_all_context_bound_role_occurrences": True,
            },
            topology_candidates=candidates,
            prepared_topology_binding=bindings[0],
        )


def _f3_spec() -> dict:
    return json.loads(_F3_TOPOLOGY_PATH.read_text(encoding="utf-8"))


def _f3_hierarchy() -> dict:
    return json.loads(_F3_EVALUATION_PATH.read_text(encoding="utf-8"))["hierarchical_closure_spec"]


def _f3_pages(rows: list[tuple[str, str, str]]) -> list[dict[str, object]]:
    pages = _pages(rows)
    pages[0]["lines"][0]["vietocr_text"] = "Tiền gửi và cho vay các TCTD khác"
    return pages


def _reindex_page_lines(lines: list[dict[str, object]]) -> None:
    for ordinal, line in enumerate(lines):
        line["line_ordinal"] = ordinal
        line["sample_id"] = f"sample-{ordinal + 1:09d}"
        line["crop_ref"] = {
            "path": f"opaque/crop-{ordinal + 1:04d}.png",
            "sha256": f"{ordinal + 1:064x}",
            "size_bytes": 100 + ordinal,
        }


def _insert_wrapped_other(
    pages: list[dict[str, object]],
    *,
    prefix: str,
) -> None:
    lines = pages[0]["lines"]
    insert_at = 8
    top = 205
    wrapped = [
        _line(900, prefix, "", [45, top, 430, top + 20]),
        _line(901, "Khác", "", [47, top + 19, 180, top + 39]),
        _line(902, "7", "7", [610, top + 19, 700, top + 39]),
        _line(903, "6", "6", [810, top + 19, 900, top + 39]),
    ]
    lines[insert_at:insert_at] = wrapped
    _reindex_page_lines(lines)


def _build_f3(pages: list[dict[str, object]]) -> tuple[dict, dict]:
    spec = _f3_spec()
    topology_pages = row_v1._topology_pages(pages)
    scan = topology_v1.build_accounting_family_topology_scan_v1(topology_pages, spec)
    assert scan["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    region = scan["regions"][0]
    effective = total_v1.project_accounting_family_coextensive_parent_total_region_v1(
        spec, scan, region
    )
    axis = subject.build_accounting_family_occurrence_row_axis_v2(
        pages,
        spec,
        scan,
        region,
        {
            "format_version": subject.POLICY_FORMAT_VERSION,
            "require_authenticated_existing_dash_pixels": True,
            "retain_all_context_bound_role_occurrences": True,
        },
        effective_topology_region=effective,
    )
    return scan, axis


def _coherently_rehash_occurrence(axis: dict) -> None:
    material = copy.deepcopy(axis)
    material.pop("occurrence_axis_id")
    axis["occurrence_axis_id"] = "aforav2:axis:" + canonical_json_sha256_v1(material)


def _coherently_replace_source_scope_binding(
    axis: dict, occurrence: dict, receipt: dict | None
) -> None:
    occurrence["source_scope_binding"] = copy.deepcopy(receipt)
    occurrence["label_match"]["source_scope_binding"] = copy.deepcopy(receipt)
    for row in axis["row_axis"]["rows"]:
        if row["label_match"].get("occurrence_id") == occurrence["occurrence_id"]:
            row["label_match"]["source_scope_binding"] = copy.deepcopy(receipt)
    axis["row_axis"] = subject._regenerate_v1_axis(axis["row_axis"])


def test_f3_blank_discount_does_not_steal_vnd_total_at_close_row_gaps() -> None:
    for gap in (18, 20):
        pages = _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
                ("Chiết khấu, tái chiết khấu", "", ""),
                ("Bằng ngoại tệ", "0", "0"),
            ]
        )
        lines = pages[0]["lines"]
        vnd_label = next(line for line in lines if line["vietocr_text"] == "Bằng VND")
        discount_label = next(
            line for line in lines if line["vietocr_text"] == "Chiết khấu, tái chiết khấu"
        )
        discount_top = vnd_label["bbox"][3] + gap
        delta = discount_top - discount_label["bbox"][1]
        for line in lines:
            if line is discount_label or (
                line["bbox"][1] == discount_label["bbox"][1] and line["vietocr_text"] == ""
            ):
                line["bbox"][1] += delta
                line["bbox"][3] += delta

        _scan, axis = _build_f3(pages)

        rows = {row["role"]: row for row in axis["row_axis"]["rows"]}
        assert [
            value["parsed_token"]["coefficient"] for value in rows["INTERBANK_LOAN_VND"]["values"]
        ] == [50, 40]
        discount_occurrence = next(
            item
            for item in axis["role_occurrences"]
            if item["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND"
        )
        assert discount_occurrence["source_scope_binding"]["binding_kind"] == (
            "UNIQUE_EXACT_PRECEDING_SOURCE_SUBSCOPE_INTERVAL"
        )
        discount_row = next(
            row
            for row in axis["row_axis"]["rows"]
            if row["label_match"]["occurrence_id"] == discount_occurrence["occurrence_id"]
        )
        assert discount_row["values"] == []


def test_f3_generic_discount_requires_nearest_exact_currency_interval() -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
            ("Chiết khấu, tái chiết khấu", "5", "4"),
            ("Bằng VND", "50", "40"),
        ]
    )

    _scan, axis = _build_f3(pages)

    ambiguous = next(
        item
        for item in axis["role_occurrences"]
        if item["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS"
    )
    assert ambiguous["source_scope_binding"] is None
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        axis, _f3_spec(), _f3_hierarchy()
    )
    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    assert any(
        reason.startswith(
            "SOURCE_ONLY_SCHEMA_INELIGIBLE_ROLE:INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS:"
        )
        for reason in closure["unresolved_reasons"]
    )


def test_f3_repeated_retrieval_occurrence_ids_cannot_swap_physical_rows() -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
            ("Bằng VND", "50", "40"),
            ("Chiết khấu, tái chiết khấu", "5", "4"),
            ("Chiết khấu, tái chiết khấu", "6", "5"),
        ]
    )

    _scan, axis = _build_f3(pages)
    repeated = [
        item
        for item in axis["role_occurrences"]
        if item["label_match"]["retrieval_role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS"
    ]
    assert len(repeated) == 2
    assert len({item["retrieval_scope_owner_occurrence_id"] for item in repeated}) == 1

    attacked = copy.deepcopy(axis)
    attacked_repeated = [
        item
        for item in attacked["role_occurrences"]
        if item["label_match"]["retrieval_role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS"
    ]
    first_id, second_id = [item["retrieval_occurrence_id"] for item in attacked_repeated]
    for item, swapped_id in zip(attacked_repeated, (second_id, first_id), strict=True):
        original_id = item["retrieval_occurrence_id"]
        item["retrieval_occurrence_id"] = swapped_id
        item["label_match"]["retrieval_occurrence_id"] = swapped_id
        row = next(
            row
            for row in attacked["row_axis"]["rows"]
            if row["label_match"].get("occurrence_id") == item["occurrence_id"]
        )
        assert row["label_match"]["retrieval_occurrence_id"] == original_id
        row["label_match"]["retrieval_occurrence_id"] = swapped_id
    attacked["row_axis"] = subject._regenerate_v1_axis(attacked["row_axis"])
    _coherently_rehash_occurrence(attacked)

    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="retrieval occurrence physical identity or owner drifted",
    ):
        subject._validate_result(attacked)


def test_f3_one_edit_vnd_with_exact_same_crop_source_anchors_generic_discount() -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
            ("Bằng VNB", "50", "40"),
            ("Chiết khấu, tái chiết khấu", "5", "4"),
            ("Bằng ngoại tệ", "0", "0"),
        ]
    )
    vnd_line = next(line for line in pages[0]["lines"] if line["vietocr_text"] == "Bằng VNB")
    vnd_line["numeric_recognition"]["raw_prediction"] = "Bằng VND"

    _scan, axis = _build_f3(pages)

    vnd = next(item for item in axis["role_occurrences"] if item["role"] == "INTERBANK_LOAN_VND")
    assert vnd["label_match"]["match_kind"].startswith("ONE_EDIT_")
    assert vnd["label_match"]["one_edit_exact_source_authority_check"]["status"] == (
        "EXACT_SOURCE_ROLE_CONTEXT_SPAN_BOUND"
    )
    discount = next(
        item
        for item in axis["role_occurrences"]
        if item["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND"
    )
    assert discount["occurrence_id"] != discount["retrieval_occurrence_id"]
    assert discount["source_scope_binding"]["binding_kind"] == (
        "UNIQUE_EXACT_PRECEDING_SOURCE_SUBSCOPE_INTERVAL"
    )
    assert (
        discount["source_scope_binding"]["anchor_exact_source_authority_check"]
        == (vnd["label_match"]["one_edit_exact_source_authority_check"])
    )
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        axis, _f3_spec(), _f3_hierarchy()
    )
    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    assert not any("ONE_EDIT" in reason for reason in closure["unresolved_reasons"])

    attacked = copy.deepcopy(axis)
    attacked_vnd = next(
        item for item in attacked["role_occurrences"] if item["role"] == "INTERBANK_LOAN_VND"
    )
    attacked_deposit = next(
        item for item in attacked["role_occurrences"] if item["role"] == "INTERBANK_DEPOSIT_GROUP"
    )
    attacked_vnd["retrieval_scope_owner_occurrence_id"] = attacked_deposit[
        "retrieval_occurrence_id"
    ]
    attacked_vnd["label_match"]["retrieval_scope_owner_occurrence_id"] = attacked_deposit[
        "retrieval_occurrence_id"
    ]
    row = next(
        row
        for row in attacked["row_axis"]["rows"]
        if row["label_match"]["occurrence_id"] == attacked_vnd["occurrence_id"]
    )
    row["label_match"]["retrieval_scope_owner_occurrence_id"] = attacked_deposit[
        "retrieval_occurrence_id"
    ]
    attacked["row_axis"] = subject._regenerate_v1_axis(attacked["row_axis"])
    _coherently_rehash_occurrence(attacked)
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="one-edit exact-source structural occurrence proof|retrieval occurrence owner",
    ):
        subject._validate_result(attacked)


def test_f3_one_edit_vnd_without_independent_exact_source_keeps_discount_ambiguous() -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
            ("Bằng VNB", "50", "40"),
            ("Chiết khấu, tái chiết khấu", "5", "4"),
            ("Bằng ngoại tệ", "0", "0"),
        ]
    )
    vnd_line = next(line for line in pages[0]["lines"] if line["vietocr_text"] == "Bằng VNB")
    vnd_line["numeric_recognition"]["raw_prediction"] = "Bằng VNB"

    _scan, axis = _build_f3(pages)

    vnd = next(item for item in axis["role_occurrences"] if item["role"] == "INTERBANK_LOAN_VND")
    assert "one_edit_exact_source_authority_check" not in vnd["label_match"]
    assert any(
        item["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS"
        for item in axis["role_occurrences"]
    )
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        axis, _f3_spec(), _f3_hierarchy()
    )
    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    assert any(
        "ONE_EDIT_ROLE_OR_SCOPE_MATCH_SCHEMA_INELIGIBLE" in reason
        for reason in closure["unresolved_reasons"]
    )


@pytest.mark.parametrize(
    "intervening_label",
    ["Khác", "Dự phòng rủi ro cho vay các TCTD khác"],
)
def test_f3_generic_discount_interval_stops_at_any_intervening_loan_sibling(
    intervening_label: str,
) -> None:
    _scan, axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "45", "36"),
                (intervening_label, "5", "4"),
                ("Chiết khấu, tái chiết khấu", "2", "1"),
            ]
        )
    )

    generic = next(
        item
        for item in axis["role_occurrences"]
        if item["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS"
    )
    assert generic["source_scope_binding"] is None
    assert not any(
        item["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND"
        and item["label_match"]["document_line_ordinal"]
        == generic["label_match"]["document_line_ordinal"]
        for item in axis["role_occurrences"]
    )


def test_f3_touching_wrapped_explicit_vnd_discount_overrides_prior_fx_scope() -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
            ("Bằng ngoại tệ", "20", "10"),
            ("Chiết khấu, tái chiết khấu", "", ""),
            ("Bằng VND", "5", "4"),
        ]
    )
    lines = pages[0]["lines"]
    prefix = next(line for line in lines if line["vietocr_text"] == "Chiết khấu, tái chiết khấu")
    suffix = next(
        line
        for line in lines
        if line["vietocr_text"] == "Bằng VND" and line["line_ordinal"] > prefix["line_ordinal"]
    )
    delta = prefix["bbox"][3] - suffix["bbox"][1]
    suffix_top = suffix["bbox"][1]
    for line in lines:
        if line["bbox"][1] == suffix_top:
            line["bbox"][1] += delta
            line["bbox"][3] += delta

    _scan, axis = _build_f3(pages)

    explicit = next(
        item
        for item in axis["role_occurrences"]
        if item["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND"
        and item["source_scope_binding"] is not None
        and item["source_scope_binding"]["binding_kind"]
        == "EXPLICIT_EXACT_SOURCE_SUBSCOPE_IN_LABEL"
    )
    assert explicit["source_scope_binding"]["source_scope_role"] == "INTERBANK_LOAN_VND"
    assert not any(
        item["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_FOREIGN_CURRENCY"
        and item["label_match"]["document_line_ordinal"]
        == explicit["label_match"]["document_line_ordinal"]
        for item in axis["role_occurrences"]
    )


@pytest.mark.parametrize(
    ("rows", "expected_role", "expected_kind"),
    [
        (
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Tiền gửi không kỳ hạn", "60", "50"),
                ("Bằng VND", "60", "50"),
                ("Tiền gửi có kỳ hạn", "40", "40"),
                ("Bằng VND", "40", "40"),
                ("Dự phòng rủi ro", "-2", "-1"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
            ],
            "INTERBANK_DEPOSIT_PROVISION",
            "EXACT_DEPOSIT_SUBTREE_BEFORE_NEXT_LOAN_BOUNDARY",
        ),
        (
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
                ("Dự phòng rủi ro", "-2", "-1"),
            ],
            "TOTAL_INTERBANK_PROVISION",
            "EXACT_TOP_SIBLING_AFTER_COMPLETE_DEPOSIT_AND_LOAN_SUBTREES",
        ),
        (
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Dự phòng rủi ro cho vay các TCTD khác", "-2", "-1"),
                ("Bằng VND", "50", "40"),
            ],
            "INTERBANK_LOAN_PROVISION",
            None,
        ),
    ],
)
def test_f3_provision_schema_role_is_bound_by_exact_parent_interval(
    rows: list[tuple[str, str, str]], expected_role: str, expected_kind: str | None
) -> None:
    _scan, axis = _build_f3(_f3_pages(rows))

    occurrence = next(item for item in axis["role_occurrences"] if item["role"] == expected_role)
    if expected_kind is None:
        assert occurrence["source_scope_binding"] is None
    else:
        assert occurrence["source_scope_binding"]["binding_kind"] == expected_kind


def test_f3_bare_provision_before_loan_leaf_remains_source_only_ambiguous() -> None:
    _scan, axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Dự phòng rủi ro", "-2", "-1"),
                ("Bằng VND", "50", "40"),
            ]
        )
    )

    occurrence = next(
        item for item in axis["role_occurrences"] if item["role"] == "INTERBANK_PROVISION_AMBIGUOUS"
    )
    assert occurrence["source_scope_binding"] is None


def test_f3_bare_deposit_provision_before_final_deposit_role_remains_ambiguous() -> None:
    _scan, axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Tiền gửi không kỳ hạn", "60", "50"),
                ("Bằng VND", "60", "50"),
                ("Dự phòng rủi ro", "-2", "-1"),
                ("Tiền gửi có kỳ hạn", "40", "40"),
                ("Bằng VND", "40", "40"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
            ]
        )
    )

    occurrence = next(
        item for item in axis["role_occurrences"] if item["role"] == "INTERBANK_PROVISION_AMBIGUOUS"
    )
    assert occurrence["source_scope_binding"] is None


def test_f3_bare_root_provision_with_later_deposit_role_remains_ambiguous() -> None:
    _scan, axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
                ("Dự phòng rủi ro", "-2", "-1"),
                ("Tiền gửi có kỳ hạn", "40", "40"),
                ("Bằng VND", "40", "40"),
            ]
        )
    )

    occurrence = next(
        item for item in axis["role_occurrences"] if item["role"] == "INTERBANK_PROVISION_AMBIGUOUS"
    )
    assert occurrence["source_scope_binding"] is None


def test_f3_root_provision_accepts_complete_exact_loan_group_total_without_leaves() -> None:
    _scan, axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Dự phòng rủi ro", "-2", "-1"),
            ]
        )
    )

    occurrence = next(
        item for item in axis["role_occurrences"] if item["role"] == "TOTAL_INTERBANK_PROVISION"
    )
    assert occurrence["source_scope_binding"]["binding_kind"] == (
        "EXACT_TOP_SIBLING_AFTER_COMPLETE_DEPOSIT_AND_LOAN_SUBTREES"
    )
    loan = next(item for item in axis["role_occurrences"] if item["role"] == "INTERBANK_LOAN_GROUP")
    loan_row = next(
        row
        for row in axis["row_axis"]["rows"]
        if row["label_match"]["occurrence_id"] == loan["occurrence_id"]
    )
    assert loan_row["status"] == "VISIBLE_VALUE_LANES_BOUND"


def test_f3_partial_loan_group_total_cannot_complete_root_provision_scope() -> None:
    _scan, axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Cho vay các TCTD khác", "50", ""),
                ("Dự phòng rủi ro", "-2", "-1"),
            ]
        )
    )

    provision = next(
        item for item in axis["role_occurrences"] if item["role"] == "INTERBANK_PROVISION_AMBIGUOUS"
    )
    assert provision["source_scope_binding"] is None
    loan = next(item for item in axis["role_occurrences"] if item["role"] == "INTERBANK_LOAN_GROUP")
    loan_row = next(
        row
        for row in axis["row_axis"]["rows"]
        if row["label_match"]["occurrence_id"] == loan["occurrence_id"]
    )
    assert loan_row["status"] == "PARTIAL_VISIBLE_VALUE_LANES_REQUIRES_PIXEL_RESCUE"
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        axis, _f3_spec(), _f3_hierarchy()
    )
    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"


def test_f3_discount_scope_never_borrows_an_anchor_from_a_prior_page() -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
            ("Bằng VND", "50", "40"),
            ("Chiết khấu, tái chiết khấu", "5", "4"),
        ]
    )
    lines = pages[0]["lines"]
    split = next(
        index
        for index, line in enumerate(lines)
        if line["vietocr_text"] == "Chiết khấu, tái chiết khấu"
    )
    second_page_lines = lines[split:]
    pages[0]["lines"] = lines[:split]
    for ordinal, line in enumerate(second_page_lines):
        line["line_ordinal"] = ordinal
    pages.append({"lines": second_page_lines, "page_sequence": 2, "page_width": 1000})

    _scan, axis = _build_f3(pages)

    source = next(
        item
        for item in axis["role_occurrences"]
        if item["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS"
    )
    assert source["label_match"]["page_sequence"] == 2
    assert source["source_scope_binding"] is None


def test_f3_provision_scope_never_borrows_an_anchor_from_a_prior_page() -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Dự phòng rủi ro", "-2", "-1"),
            ("Cho vay các TCTD khác", "50", "40"),
            ("Bằng VND", "50", "40"),
        ]
    )
    lines = pages[0]["lines"]
    split = next(
        index for index, line in enumerate(lines) if line["vietocr_text"] == "Dự phòng rủi ro"
    )
    second_page_lines = lines[split:]
    pages[0]["lines"] = lines[:split]
    for ordinal, line in enumerate(second_page_lines):
        line["line_ordinal"] = ordinal
    pages.append({"lines": second_page_lines, "page_sequence": 2, "page_width": 1000})

    _scan, axis = _build_f3(pages)

    source = next(
        item for item in axis["role_occurrences"] if item["role"] == "INTERBANK_PROVISION_AMBIGUOUS"
    )
    assert source["label_match"]["page_sequence"] == 2
    assert source["source_scope_binding"] is None


def test_f3_bare_provisions_are_unique_per_exact_parent_interval() -> None:
    _scan, distinct_axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Dự phòng rủi ro", "-2", "-1"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
                ("Dự phòng", "-3", "-2"),
            ]
        )
    )
    assert {
        occurrence["role"]
        for occurrence in distinct_axis["role_occurrences"]
        if occurrence["role"] in {"INTERBANK_DEPOSIT_PROVISION", "TOTAL_INTERBANK_PROVISION"}
    } == {"INTERBANK_DEPOSIT_PROVISION", "TOTAL_INTERBANK_PROVISION"}

    _scan, duplicate_axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Dự phòng rủi ro", "-2", "-1"),
                ("Dự phòng", "-3", "-2"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
            ]
        )
    )
    assert [
        occurrence["role"]
        for occurrence in duplicate_axis["role_occurrences"]
        if occurrence["role"] == "INTERBANK_PROVISION_AMBIGUOUS"
    ] == ["INTERBANK_PROVISION_AMBIGUOUS", "INTERBANK_PROVISION_AMBIGUOUS"]


def test_f3_explicit_provision_wins_over_bare_duplicate_in_same_interval() -> None:
    _scan, axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Dự phòng tiền gửi tại các TCTD khác", "-2", "-1"),
                ("Dự phòng", "-3", "-2"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
            ]
        )
    )

    roles = [occurrence["role"] for occurrence in axis["role_occurrences"]]
    assert roles.count("INTERBANK_DEPOSIT_PROVISION") == 1
    assert roles.count("INTERBANK_PROVISION_AMBIGUOUS") == 1


def test_f3_generic_discount_is_unique_within_one_currency_subscope() -> None:
    _scan, duplicate_axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
                ("Chiết khấu, tái chiết khấu", "5", "4"),
                ("Chiết khấu, tái chiết khấu", "6", "5"),
            ]
        )
    )
    assert [
        occurrence["role"]
        for occurrence in duplicate_axis["role_occurrences"]
        if occurrence["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS"
    ] == [
        "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS",
        "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS",
    ]

    _scan, explicit_axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
                ("Chiết khấu, tái chiết khấu", "5", "4"),
                ("Chiết khấu, tái chiết khấu bằng VND", "6", "5"),
            ]
        )
    )
    roles = [occurrence["role"] for occurrence in explicit_axis["role_occurrences"]]
    assert roles.count("INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND") == 1
    assert roles.count("INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS") == 1


def test_f3_other_requires_noncontinuation_geometry_and_exact_parent_scope() -> None:
    known = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
        ]
    )
    _insert_wrapped_other(known, prefix="Tiền gửi tại các TCTD")
    _scan, known_axis = _build_f3(known)
    assert "INTERBANK_DEPOSIT_OTHER" not in {
        item["role"] for item in known_axis["role_occurrences"]
    }

    unknown = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
        ]
    )
    _insert_wrapped_other(unknown, prefix="Khoản diễn giải chưa có trong schema")
    _scan, unknown_axis = _build_f3(unknown)
    ambiguous = next(
        item
        for item in unknown_axis["role_occurrences"]
        if item["role"] == "INTERBANK_DEPOSIT_OTHER"
    )
    assert ambiguous["source_scope_binding"]["status"] == (
        "SOURCE_ONLY_AMBIGUOUS_TOUCHING_WRAPPED_LABEL"
    )
    closure = closure_v2.build_accounting_scoped_hierarchical_table_closure_v2(
        unknown_axis, _f3_spec(), _f3_hierarchy()
    )
    assert any(
        reason.startswith("SOURCE_ONLY_AMBIGUOUS_TOUCHING_WRAPPED_LABEL:")
        for reason in closure["unresolved_reasons"]
    )

    standalone = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Khác", "7", "6"),
            ("Cho vay các TCTD khác", "50", "40"),
        ]
    )
    _scan, standalone_axis = _build_f3(standalone)
    other = next(
        item
        for item in standalone_axis["role_occurrences"]
        if item["role"] == "INTERBANK_DEPOSIT_OTHER"
    )
    assert other["source_scope_binding"] is None
    other_row = next(
        row for row in standalone_axis["row_axis"]["rows"] if row["role"] == other["role"]
    )
    assert [value["parsed_token"]["coefficient"] for value in other_row["values"]] == [7, 6]


def test_f3_declared_scoped_other_alias_composes_touching_label_fragments() -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
        ]
    )
    _insert_wrapped_other(pages, prefix="Các khoản")

    _scan, axis = _build_f3(pages)

    other = next(
        item for item in axis["role_occurrences"] if item["role"] == "INTERBANK_DEPOSIT_OTHER"
    )
    assert other["source_scope_binding"] is None
    assert other["label_match"]["normalized_surface"] == "cac khoan khac"
    assert other["label_match"]["match_kind"] == ("EXACT_ACCENTLESS_ALIAS_VISUAL_CONTINUATION")
    row = next(
        row
        for row in axis["row_axis"]["rows"]
        if row["label_match"]["occurrence_id"] == other["occurrence_id"]
    )
    assert [value["parsed_token"]["coefficient"] for value in row["values"]] == [7, 6]


def test_f3_known_total_provision_wrap_suppresses_interleaved_other_suffix() -> None:
    pages = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
        ]
    )
    lines = pages[0]["lines"]
    lines.extend(
        [
            _line(
                900,
                "Dự phòng rủi ro tiền gửi và cho vay các TCTD",
                "",
                [45, 400, 500, 420],
            ),
            _line(901, "-2", "-2", [610, 400, 700, 420]),
            _line(902, "-1", "-1", [810, 400, 900, 420]),
            _line(903, "|", "", [950, 402, 990, 418]),
            _line(904, "Khác", "", [47, 419, 180, 439]),
        ]
    )
    _reindex_page_lines(lines)

    _scan, axis = _build_f3(pages)

    assert "INTERBANK_LOAN_OTHER" not in {item["role"] for item in axis["role_occurrences"]}
    total = next(
        item for item in axis["role_occurrences"] if item["role"] == "TOTAL_INTERBANK_PROVISION"
    )
    total_row = next(
        row
        for row in axis["row_axis"]["rows"]
        if row["label_match"]["occurrence_id"] == total["occurrence_id"]
    )
    assert [value["parsed_token"]["coefficient"] for value in total_row["values"]] == [
        -2,
        -1,
    ]


def test_heading_only_parent_total_clone_is_pruned_but_same_row_values_are_retained() -> None:
    heading_only = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
        ]
    )
    for line in heading_only[0]["lines"][3:5]:
        line["vietocr_text"] = ""
        line["numeric_recognition"]["raw_prediction"] = ""
    _scan, heading_axis = _build_f3(heading_only)
    assert "EXPLICIT_FAMILY_TOTAL" not in {
        item["role"] for item in heading_axis["role_occurrences"]
    }

    with_values = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
        ]
    )
    _scan, valued_axis = _build_f3(with_values)
    total = next(
        item for item in valued_axis["role_occurrences"] if item["role"] == "EXPLICIT_FAMILY_TOTAL"
    )
    total_row = next(
        row
        for row in valued_axis["row_axis"]["rows"]
        if row["label_match"]["occurrence_id"] == total["occurrence_id"]
    )
    assert [value["parsed_token"]["coefficient"] for value in total_row["values"]] == [
        150,
        130,
    ]


def test_f3_scope_receipts_reject_coherent_status_anchor_and_explicit_surface_forgery() -> None:
    unknown = _f3_pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
        ]
    )
    _insert_wrapped_other(unknown, prefix="Khoản diễn giải chưa có trong schema")
    _scan, unknown_axis = _build_f3(unknown)
    attacked = copy.deepcopy(unknown_axis)
    occurrence = next(
        item for item in attacked["role_occurrences"] if item["role"] == "INTERBANK_DEPOSIT_OTHER"
    )
    occurrence["source_scope_binding"]["status"] = (
        "REVIEWED_EXACT_SOURCE_SCOPE_TO_SCHEMA_ROLE_BINDING"
    )
    material = copy.deepcopy(occurrence["source_scope_binding"])
    material.pop("binding_id")
    occurrence["source_scope_binding"]["binding_id"] = (
        "aforav2:scope-binding:" + canonical_json_sha256_v1(material)
    )
    _coherently_replace_source_scope_binding(
        attacked, occurrence, occurrence["source_scope_binding"]
    )
    _coherently_rehash_occurrence(attacked)
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="semantic matrix",
    ):
        subject._validate_result(attacked)

    _scan, discount_axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
                ("Chiết khấu, tái chiết khấu", "5", "4"),
                ("Bằng ngoại tệ", "0", "0"),
            ]
        )
    )
    split_brain = copy.deepcopy(discount_axis)
    split_occurrence = next(
        item
        for item in split_brain["role_occurrences"]
        if item["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND"
    )
    split_occurrence["source_scope_binding"] = None
    _coherently_rehash_occurrence(split_brain)
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="nearest-parent scope axis",
    ):
        subject._validate_result(split_brain)

    attacked = copy.deepcopy(discount_axis)
    occurrence = next(
        item
        for item in attacked["role_occurrences"]
        if item["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND"
    )
    receipt = occurrence["source_scope_binding"]
    receipt["anchor_span"]["source_line_index"] += 1
    material = copy.deepcopy(receipt)
    material.pop("binding_id")
    receipt["binding_id"] = "aforav2:scope-binding:" + canonical_json_sha256_v1(material)
    _coherently_replace_source_scope_binding(attacked, occurrence, receipt)
    _coherently_rehash_occurrence(attacked)
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="actual occurrence",
    ):
        subject._validate_result(attacked)

    bare_occurrence = next(
        item
        for item in discount_axis["role_occurrences"]
        if item["role"] == "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND"
    )
    receipt = copy.deepcopy(bare_occurrence["source_scope_binding"])
    receipt.update(
        {
            "anchor_span": None,
            "binding_kind": "EXPLICIT_EXACT_SOURCE_SUBSCOPE_IN_LABEL",
            "interval": {
                "end_document_line_ordinal_exclusive": bare_occurrence["label_match"][
                    "end_document_line_ordinal"
                ]
                + 1,
                "start_document_line_ordinal": bare_occurrence["label_match"][
                    "document_line_ordinal"
                ],
            },
            "source_role": bare_occurrence["role"],
        }
    )
    receipt["source_span"]["role"] = bare_occurrence["role"]
    material = copy.deepcopy(receipt)
    material.pop("binding_id")
    receipt["binding_id"] = "aforav2:scope-binding:" + canonical_json_sha256_v1(material)
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="semantic matrix",
    ):
        subject._validate_source_scope_binding(
            receipt,
            label_match=bare_occurrence["label_match"],
            role=bare_occurrence["role"],
        )


def test_f3_provision_receipts_rederive_interval_and_actual_bbox_geometry() -> None:
    _scan, deposit_axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Tiền gửi không kỳ hạn", "60", "50"),
                ("Bằng VND", "60", "50"),
                ("Tiền gửi có kỳ hạn", "40", "40"),
                ("Bằng VND", "40", "40"),
                ("Dự phòng rủi ro", "-2", "-1"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
            ]
        )
    )
    attacked = copy.deepcopy(deposit_axis)
    provision = next(
        item
        for item in attacked["role_occurrences"]
        if item["role"] == "INTERBANK_DEPOSIT_PROVISION"
    )
    deposit_group = next(
        item for item in attacked["role_occurrences"] if item["role"] == "INTERBANK_DEPOSIT_GROUP"
    )
    receipt = provision["source_scope_binding"]
    receipt["anchor_span"] = subject._source_span(deposit_group["label_match"])
    material = copy.deepcopy(receipt)
    material.pop("binding_id")
    receipt["binding_id"] = "aforav2:scope-binding:" + canonical_json_sha256_v1(material)
    _coherently_replace_source_scope_binding(attacked, provision, receipt)
    _coherently_rehash_occurrence(attacked)
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="exact deposit interval",
    ):
        subject._validate_result(attacked)

    _scan, total_axis = _build_f3(
        _f3_pages(
            [
                ("Tiền gửi tại các TCTD khác", "100", "90"),
                ("Cho vay các TCTD khác", "50", "40"),
                ("Bằng VND", "50", "40"),
                ("Dự phòng rủi ro", "-2", "-1"),
            ]
        )
    )
    attacked = copy.deepcopy(total_axis)
    provision = next(
        item for item in attacked["role_occurrences"] if item["role"] == "TOTAL_INTERBANK_PROVISION"
    )
    receipt = provision["source_scope_binding"]
    receipt["geometry"]["source_left"] += 1
    receipt["geometry"]["absolute_left_delta"] = abs(
        receipt["geometry"]["source_left"] - receipt["geometry"]["anchor_left"]
    )
    material = copy.deepcopy(receipt)
    material.pop("binding_id")
    receipt["binding_id"] = "aforav2:scope-binding:" + canonical_json_sha256_v1(material)
    _coherently_replace_source_scope_binding(attacked, provision, receipt)
    _coherently_rehash_occurrence(attacked)
    with pytest.raises(
        subject.AccountingFamilyOccurrenceRowAxisV2Error,
        match="semantic matrix",
    ):
        subject._validate_result(attacked)
