from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from bctc_ai.evaluation import accounting_family_occurrence_row_axis_v2 as occurrence_v2
from bctc_ai.evaluation import accounting_family_row_axis_v1 as row_v1
from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation import accounting_scoped_hierarchical_table_closure_v2 as subject
from bctc_ai.evaluation import family_first_accounting_schema_mapping_v1 as mapping_v1
from bctc_ai.evaluation import family_first_authenticated_page_region_v1 as region_v1
from bctc_ai.evaluation.adaptive_accounting_table_geometry_v1 import (
    propose_missing_value_lane_regions_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _matcher(alias: str, within: str | None = None) -> dict[str, object]:
    return {"aliases": [alias], "within_role": within}


def _topology() -> dict[str, object]:
    return {
        "children": [
            {
                "matchers": [_matcher("Tiền gửi tại TCTD khác")],
                "presence": "OPTIONAL",
                "role": "DEPOSIT_GROUP",
                "role_kind": "STRUCTURAL_GROUP",
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
                "matchers": [_matcher("Dự phòng cho vay TCTD khác", "LOAN_GROUP")],
                "presence": "OPTIONAL",
                "role": "LOAN_PROVISION",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "matchers": [_matcher("Tổng cộng")],
                "presence": "OPTIONAL",
                "role": "EXPLICIT_FAMILY_TOTAL",
                "role_kind": "TOTAL",
            },
        ],
        "family_id": "INTERBANK",
        "format_version": "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V3",
        "hard_negative_aliases": [],
        "limits": {
            "max_cluster_span_lines": 50,
            "max_continuation_pages": 1,
            "max_label_line_span": 2,
        },
        "parent": {
            "aliases": ["Tiền gửi và cho vay TCTD khác"],
            "resolution_mode": "EXPLICIT_ONLY",
            "role": "INTERBANK",
        },
        "presence_evidence_mode": "WITHIN_EXPLICIT_PARENT_CLUSTER",
        "required_role_combinations": [["DEPOSIT_GROUP", "LOAN_GROUP"]],
        "structural_reset_aliases": [],
    }


def _alternative(roles: list[str], *, derive: bool = True) -> dict[str, object]:
    return {
        "component_roles": roles,
        "coverage_policy": "EXHAUSTIVE_COMPONENT_SET",
        "derivation_policy": (
            "ALLOW_DERIVATION_FROM_EXHAUSTIVE_VISIBLE_COMPONENTS"
            if derive
            else "VISIBLE_RESULT_CORROBORATION_ONLY"
        ),
    }


def _hierarchy() -> dict[str, object]:
    return {
        "equations": [
            {
                "application_policy": "REQUIRED_WHEN_ANY_DECLARED_ROLE_VISIBLE",
                "component_role_alternatives": [
                    _alternative(["LOAN_VND", "LOAN_FOREIGN_CURRENCY"]),
                    _alternative(["LOAN_VND", "LOAN_FOREIGN_CURRENCY", "LOAN_PROVISION"]),
                ],
                "result_role": "LOAN_GROUP",
                "trailing_result_policy": "IGNORE",
                "visible_result_roles": ["LOAN_GROUP"],
                "visible_source_policy": "ALLOW_ONLY_WHEN_NO_DECLARED_COMPONENT_ROLE_VISIBLE",
            },
            {
                "application_policy": "REQUIRED_WHEN_ANY_DECLARED_ROLE_VISIBLE",
                "component_role_alternatives": [
                    _alternative(["DEPOSIT_GROUP", "LOAN_GROUP"]),
                    _alternative(["DEPOSIT_GROUP", "LOAN_GROUP", "LOAN_PROVISION"]),
                ],
                "result_role": "INTERBANK",
                "trailing_result_policy": "CORROBORATE_IF_PRESENT",
                "visible_result_roles": ["EXPLICIT_FAMILY_TOTAL"],
                "visible_source_policy": "REQUIRE_EXHAUSTIVE_COMPONENTS",
            },
        ],
        "family_id": "INTERBANK",
        "format_version": subject.SPEC_FORMAT_VERSION,
        "repeated_role_policy": {
            "aggregate_roles": [
                "LOAN_FOREIGN_CURRENCY",
                "LOAN_GROUP",
                "LOAN_VND",
            ],
            "local_subtotal_roles": ["LOAN_GROUP"],
        },
    }


def _hierarchy_v2(*, source_only_veto_roles: list[str] | None = None) -> dict[str, object]:
    hierarchy = copy.deepcopy(_hierarchy())
    hierarchy["format_version"] = subject.SPEC_FORMAT_VERSION_V2
    hierarchy["source_role_policy"] = {
        "one_edit_role_or_scope_match_policy": "VETO",
        "source_only_veto_roles": sorted(source_only_veto_roles or []),
    }
    return hierarchy


_ROUNDING_COMPONENT_LABELS = [
    "Khoản Alpha",
    "Khoản Bravo",
    "Khoản Charlie",
    "Khoản Delta",
    "Khoản Echo",
    "Khoản Foxtrot",
]
_ROUNDING_COMPONENT_ROLES = [f"COMPONENT_{ordinal}" for ordinal in range(1, 7)]


def _rounding_topology() -> dict[str, object]:
    topology = copy.deepcopy(_topology())
    topology["children"] = [
        {
            "matchers": [_matcher(label)],
            "presence": "OPTIONAL",
            "role": f"COMPONENT_{ordinal}",
            "role_kind": "ADDITIVE_CHILD",
        }
        for ordinal, label in enumerate(_ROUNDING_COMPONENT_LABELS, start=1)
    ] + [
        {
            "matchers": [_matcher("Tổng cộng")],
            "presence": "OPTIONAL",
            "role": "EXPLICIT_FAMILY_TOTAL",
            "role_kind": "TOTAL",
        }
    ]
    topology["required_role_combinations"] = [["COMPONENT_1", "COMPONENT_2"]]
    return topology


def _rounding_hierarchy(*, v2: bool = True) -> dict[str, object]:
    hierarchy = {
        "equations": [
            {
                "application_policy": "REQUIRED_WHEN_ANY_DECLARED_ROLE_VISIBLE",
                "component_role_alternatives": [
                    _alternative([f"COMPONENT_{ordinal}" for ordinal in range(1, 7)])
                ],
                "result_role": "INTERBANK",
                "trailing_result_policy": "CORROBORATE_IF_PRESENT",
                "visible_result_roles": ["EXPLICIT_FAMILY_TOTAL"],
                "visible_source_policy": "REQUIRE_EXHAUSTIVE_COMPONENTS",
            }
        ],
        "family_id": "INTERBANK",
        "format_version": subject.SPEC_FORMAT_VERSION,
        "repeated_role_policy": {"aggregate_roles": [], "local_subtotal_roles": []},
    }
    if v2:
        hierarchy["format_version"] = subject.SPEC_FORMAT_VERSION_V2
        hierarchy["source_role_policy"] = {
            "one_edit_role_or_scope_match_policy": "VETO",
            "source_only_veto_roles": [],
        }
    return hierarchy


def _line(ordinal: int, text: str, numeric: str, bbox: list[int]) -> dict[str, object]:
    return {
        "bbox": bbox,
        "crop_ref": {
            "path": f"opaque/crop-{ordinal + 1:04d}.png",
            "sha256": f"{ordinal + 1:064x}",
            "size_bytes": 100 + ordinal,
        },
        "line_ordinal": ordinal,
        "numeric_recognition": {"raw_prediction": numeric, "reader_score": 0.98},
        "sample_id": f"sample-{ordinal + 1:09d}",
        "vietocr_text": text,
    }


def _pages(
    rows: list[tuple[str, str, str]],
    *,
    trailing: list[tuple[str | None, str | None]] | None = None,
) -> list[dict[str, object]]:
    lines = [
        _line(0, "Tiền gửi và cho vay TCTD khác", "", [25, 15, 460, 38]),
        _line(1, "31/12/2025", "", [610, 45, 700, 65]),
        _line(2, "31/12/2024", "", [810, 45, 900, 65]),
        _line(3, "Đơn vị: Triệu đồng", "", [610, 72, 900, 94]),
    ]
    for row_index, (label, current, prior) in enumerate(rows):
        ordinal = len(lines)
        top = 110 + row_index * 50
        lines.extend(
            [
                _line(ordinal, label, "", [45, top, 430, top + 20]),
                _line(ordinal + 1, current, current, [610, top, 700, top + 20]),
                _line(ordinal + 2, prior, prior, [810, top, 900, top + 20]),
            ]
        )
    trailing_top = 110 + len(rows) * 50
    for trailing_index, (current, prior) in enumerate(trailing or []):
        ordinal = len(lines)
        top = trailing_top + trailing_index * 24
        if current is not None:
            lines.append(_line(ordinal, current, current, [610, top, 700, top + 20]))
            ordinal += 1
        if prior is not None:
            lines.append(_line(ordinal, prior, prior, [810, top, 900, top + 20]))
    return [{"lines": lines, "page_sequence": 1, "page_width": 1000}]


def _acb_shaped_preceding_subtotal_pages(
    *, demand_subtotal_current: str = "30", demand_subtotal_prior: str = "20"
) -> list[dict[str, object]]:
    """Provider-order fixture: prior subtotal touches the next group label."""

    lines = [
        _line(0, "Tiền gửi và cho vay các TCTD khác", "", [25, 15, 500, 49]),
        _line(1, "31/12/2025", "", [610, 65, 700, 92]),
        _line(2, "31/12/2024", "", [810, 65, 900, 92]),
        _line(3, "Đơn vị: Triệu đồng", "", [610, 96, 900, 123]),
        _line(4, "Tiền gửi không kỳ hạn", "", [45, 120, 430, 154]),
        _line(5, "Bằng Đồng Việt Nam", "", [65, 155, 430, 189]),
        _line(6, "20", "20", [610, 157, 700, 184]),
        _line(7, "15", "15", [810, 157, 900, 184]),
        _line(8, "Bằng ngoại tệ", "", [65, 190, 430, 224]),
        _line(9, "10", "10", [610, 192, 700, 219]),
        _line(10, "5", "5", [810, 192, 900, 219]),
        _line(
            11,
            demand_subtotal_current,
            demand_subtotal_current,
            [610, 245, 700, 279],
        ),
        _line(
            12,
            demand_subtotal_prior,
            demand_subtotal_prior,
            [810, 245, 900, 279],
        ),
        _line(13, "Tiền gửi có kỳ hạn", "", [45, 274, 430, 314]),
        _line(14, "Bằng Đồng Việt Nam", "", [65, 309, 430, 343]),
        _line(15, "100", "100", [610, 311, 700, 338]),
        _line(16, "80", "80", [810, 311, 900, 338]),
        _line(17, "Bằng ngoại tệ", "", [65, 344, 430, 378]),
        _line(18, "20", "20", [610, 346, 700, 373]),
        _line(19, "10", "10", [810, 346, 900, 373]),
        _line(20, "Cho vay các TCTD khác", "", [45, 410, 430, 444]),
        _line(21, "50", "50", [610, 412, 700, 439]),
        _line(22, "40", "40", [810, 412, 900, 439]),
        _line(
            23,
            "Tổng tiền gửi và cho vay các TCTD khác",
            "",
            [45, 470, 500, 504],
        ),
        _line(24, "200", "200", [610, 472, 700, 499]),
        _line(25, "150", "150", [810, 472, 900, 499]),
    ]
    return [{"lines": lines, "page_sequence": 1, "page_width": 1000}]


def _vib_shaped_unlabeled_subtotal_pages() -> list[dict[str, object]]:
    pages = _pages(
        [
            ("Tiền gửi không kỳ hạn", "30", "20"),
            ("Bằng VND", "20", "15"),
            ("Bằng ngoại tệ", "10", "5"),
            ("Tiền gửi có kỳ hạn", "70", "60"),
            ("Bằng VND", "60", "50"),
            ("Bằng ngoại tệ", "10", "10"),
            ("Cho vay các TCTD khác", "", ""),
            ("Bằng VND", "50", "40"),
            ("Bằng ngoại tệ", "0", "0"),
        ],
        trailing=[("50", "40"), ("150", "120")],
    )
    pages[0]["lines"][0]["vietocr_text"] = "Tiền gửi và cho vay các TCTD khác"
    lines = pages[0]["lines"]
    loan_index = next(
        index for index, line in enumerate(lines) if line["vietocr_text"] == "Cho vay các TCTD khác"
    )
    lines[loan_index:loan_index] = [
        _line(999, "100", "100", [610, 390, 700, 410]),
        _line(1_000, "80", "80", [810, 390, 900, 410]),
    ]
    for ordinal, line in enumerate(lines):
        line["line_ordinal"] = ordinal
        line["sample_id"] = f"sample-{ordinal + 1:09d}"
        line["crop_ref"] = {
            "path": f"opaque/crop-{ordinal + 1:04d}.png",
            "sha256": f"{ordinal + 1:064x}",
            "size_bytes": 100 + ordinal,
        }
    return pages


def _axis(
    pages: list[dict[str, object]],
    topology: dict[str, object] | None = None,
    *,
    visible_dash_rescues: tuple[dict[str, object], ...] = (),
) -> dict:
    topology = _topology() if topology is None else topology
    scan = topology_v1.build_accounting_family_topology_scan_v1(
        row_v1._topology_pages(pages), topology
    )
    assert scan["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    return occurrence_v2.build_accounting_family_occurrence_row_axis_v2(
        pages,
        topology,
        scan,
        scan["regions"][0],
        {
            "format_version": occurrence_v2.POLICY_FORMAT_VERSION,
            "require_authenticated_existing_dash_pixels": True,
            "retain_all_context_bound_role_occurrences": True,
        },
        visible_dash_rescues=visible_dash_rescues,
    )


def _closure(
    pages: list[dict[str, object]],
    *,
    topology: dict[str, object] | None = None,
    hierarchy: dict[str, object] | None = None,
    visible_dash_rescues: tuple[dict[str, object], ...] = (),
) -> tuple[dict, dict]:
    topology = _topology() if topology is None else topology
    hierarchy = _hierarchy() if hierarchy is None else hierarchy
    axis = _axis(pages, topology, visible_dash_rescues=visible_dash_rescues)
    closure = subject.build_accounting_scoped_hierarchical_table_closure_v2(
        axis, topology, hierarchy
    )
    return axis, closure


def _clear_detector_dash_rescue(
    pages: list[dict[str, object]],
    topology: dict[str, object],
    *,
    role: str,
) -> tuple[dict[str, object], ...]:
    parsed_pages = row_v1._pages(pages)
    scan = topology_v1.build_accounting_family_topology_scan_v1(
        row_v1._topology_pages(pages), topology
    )
    region = scan["regions"][0]
    base = row_v1._build_axis(parsed_pages, scan, region, ())
    target = next(row for row in base["rows"] if row["role"] == role)
    centers, visible_cells = row_v1._resolved_page_grid_inputs(
        base["rows"], target, base["column_grids"]
    )
    label_indices = row_v1._match_source_line_indices(target["label_match"])
    label_boxes = [
        line["bbox"] for line in parsed_pages[0]["lines"] if line["line_ordinal"] in label_indices
    ]
    proposals = propose_missing_value_lane_regions_v1(
        [{**line, "source_line_index": line["line_ordinal"]} for line in parsed_pages[0]["lines"]],
        label_boxes=label_boxes,
        is_numeric=row_v1._is_numeric,
        page_width=1000,
        page_height=1200,
        resolved_column_centers=centers,
        resolved_visible_value_cells=visible_cells,
    )
    assert len(proposals) == 1
    proposal = proposals[0]
    image = Image.new("RGB", (40, 32), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((16, 14, 24, 17), fill="black")
    stream = io.BytesIO()
    image.save(stream, format="PNG", optimize=False, compress_level=9)
    payload = stream.getvalue()
    raw_bbox = proposal["raw_pixel_bbox"]
    material = {
        "authority": dict(region_v1._REGION_AUTHORITY),
        "document_ordinal": 1,
        "format_version": region_v1.FORMAT_VERSION,
        "index_id": "index-rounding-dash",
        "ink_localization_status": "GLYPH_COMPONENT_TIGHTENED_WITHIN_PROPOSED_CELL",
        "physical_page": 1,
        "proposed_raw_pixel_bbox": list(raw_bbox),
        "recognition_raw_pixel_bbox": list(raw_bbox),
        "region_png_ref": {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        },
        "render_id": "render-rounding-dash",
        "render_ref": {
            "pixel_height": 1200,
            "pixel_width": 1000,
            "sha256": "3" * 64,
            "size_bytes": 100,
        },
        "state": "AUTHENTICATED_RENDER_CALLER_PROPOSED_REGION_CROP",
        "white_border": [12, 8, 12, 8],
    }
    detector_region = {
        **material,
        "region_id": "ffaprv1:region:" + canonical_json_sha256_v1(material),
        "region_png_bytes": payload,
    }
    return (
        {
            "column_ordinal": proposal["column_ordinal"],
            "page_sequence": 1,
            "region": detector_region,
            "role": role,
        },
    )


def _coherently_rehash_closure(closure: dict) -> None:
    closure["metrics"] = subject._metrics(
        closure["resolved_roles"],
        closure["equations"]["global"],
        closure["equations"]["local"],
        closure["coverage_receipt"],
        closure["unresolved_reasons"],
    )
    material = copy.deepcopy(closure)
    material.pop("closure_id")
    closure["closure_id"] = "ashtcv2:closure:" + canonical_json_sha256_v1(material)


def _insert_internal_numeric_pair(pages: list[dict], token: str) -> None:
    lines = pages[0]["lines"]
    lines[7:7] = [
        _line(999, token, token, [610, 185, 700, 205]),
        _line(1_000, token, token, [810, 185, 900, 205]),
    ]
    for ordinal, line in enumerate(lines):
        line["line_ordinal"] = ordinal
        line["sample_id"] = f"sample-{ordinal + 1:09d}"
        line["crop_ref"] = {
            "path": f"opaque/crop-{ordinal + 1:04d}.png",
            "sha256": f"{ordinal + 1:064x}",
            "size_bytes": 100 + ordinal,
        }


def _insert_off_lane_body_numeric(pages: list[dict], token: str) -> None:
    lines = pages[0]["lines"]
    lines[7:7] = [_line(999, token, token, [940, 185, 990, 205])]
    for ordinal, line in enumerate(lines):
        line["line_ordinal"] = ordinal
        line["sample_id"] = f"sample-{ordinal + 1:09d}"
        line["crop_ref"] = {
            "path": f"opaque/crop-{ordinal + 1:04d}.png",
            "sha256": f"{ordinal + 1:064x}",
            "size_bytes": 100 + ordinal,
        }


@pytest.mark.parametrize("token", ["0", "7", "-"])
def test_internal_typed_money_lane_sample_is_source_only_and_always_vetoes(
    token: str,
) -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
        ]
    )
    _insert_internal_numeric_pair(pages, token)

    axis, closure = _closure(pages)

    assert len(axis["internal_unassigned_numeric_clusters"]) == 1
    cluster = axis["internal_unassigned_numeric_clusters"][0]
    source_only = [
        sample
        for sample in axis["numeric_sample_universe"]
        if sample["owner_kind"] == "SOURCE_ONLY_INTERNAL_CLUSTER"
    ]
    assert [sample["sample_id"] for sample in source_only] == cluster["sample_ids"]
    assert {sample["parsed_token"]["classification"] for sample in source_only} == {
        "DASH_ZERO" if token == "-" else "SIGNED_NUMBER"
    }
    receipt = next(
        record
        for record in closure["coverage_receipt"]
        if record["row_kind"] == "INTERNAL_UNASSIGNED_NUMERIC_CLUSTER"
    )
    assert receipt["sample_ids"] == cluster["sample_ids"]
    assert receipt["disposition"] == "UNRESOLVED_SOURCE_ONLY_INTERNAL_NUMERIC_CLUSTER"
    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    assert (
        f"SOURCE_ONLY_INTERNAL_NUMERIC_CLUSTER_VETO:{cluster['cluster_id']}"
        in closure["unresolved_reasons"]
    )
    assert len(
        [sample_id for record in closure["coverage_receipt"] for sample_id in record["sample_ids"]]
    ) == len(axis["numeric_sample_universe"])


def test_off_lane_body_numeric_is_owned_once_and_vetoes_closure() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
        ]
    )
    _insert_off_lane_body_numeric(pages, "7")

    axis, closure = _closure(pages)

    cluster = next(
        cluster
        for cluster in axis["internal_unassigned_numeric_clusters"]
        if cluster["status"] == occurrence_v2._OFF_LANE_NUMERIC_CLUSTER_STATUS
    )
    assert len(cluster["sample_ids"]) == 1
    receipt = next(
        record
        for record in closure["coverage_receipt"]
        if record["source_record"].get("cluster_id") == cluster["cluster_id"]
    )
    assert receipt["sample_ids"] == cluster["sample_ids"]
    assert receipt["disposition"] == "UNRESOLVED_OFF_LANE_NUMERIC_SOURCE_ONLY"
    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    assert (
        f"OFF_LANE_NUMERIC_SOURCE_ONLY_VETO:{cluster['cluster_id']}"
        in closure["unresolved_reasons"]
    )
    assert (
        sum(
            sample_id in cluster["sample_ids"]
            for record in closure["coverage_receipt"]
            for sample_id in record["sample_ids"]
        )
        == 1
    )


def test_off_lane_cluster_cause_cannot_be_retyped_by_coherent_rehash() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
        ]
    )
    _insert_off_lane_body_numeric(pages, "7")
    _axis_value, closure = _closure(pages)
    attacked = copy.deepcopy(closure)
    receipt = next(
        record
        for record in attacked["coverage_receipt"]
        if record["disposition"] == "UNRESOLVED_OFF_LANE_NUMERIC_SOURCE_ONLY"
    )
    receipt["disposition"] = "UNRESOLVED_SOURCE_ONLY_INTERNAL_NUMERIC_CLUSTER"
    _coherently_rehash_closure(attacked)

    with pytest.raises(
        subject.AccountingScopedHierarchicalTableClosureV2Error,
        match="cluster status|disposition drifted",
    ):
        subject._validate_result(attacked)


def test_numeric_universe_sample_cannot_lose_its_only_receipt_after_coherent_rehash() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
        ]
    )
    _insert_internal_numeric_pair(pages, "7")
    _axis_value, closure = _closure(pages)
    attacked = copy.deepcopy(closure)
    source_only = next(
        record
        for record in attacked["coverage_receipt"]
        if record["row_kind"] == "INTERNAL_UNASSIGNED_NUMERIC_CLUSTER"
    )
    source_only["sample_ids"].pop()
    source_only["source_record"]["sample_ids"].pop()
    source_only["source_record"]["column_ordinals"].pop()
    _coherently_rehash_closure(attacked)

    with pytest.raises(
        subject.AccountingScopedHierarchicalTableClosureV2Error,
        match="internal numeric cluster|numeric cluster status|exactly one owning coverage receipt",
    ):
        subject._validate_result(attacked)


def test_v4_unlabeled_deposit_and_loan_subtotals_are_exact_coverage_only() -> None:
    project_root = Path(__file__).resolve().parents[2]
    topology = json.loads(
        (project_root / "config/families/tm-interbank-deposits-loans-topology-v4.json").read_text()
    )
    hierarchy = json.loads(
        (
            project_root / "config/families/tm-interbank-deposits-loans-evaluation-v4.json"
        ).read_text()
    )["hierarchical_closure_spec"]

    axis, closure = _closure(
        _vib_shaped_unlabeled_subtotal_pages(), topology=topology, hierarchy=hierarchy
    )

    receipts = [
        receipt
        for receipt in closure["coverage_receipt"]
        if receipt["disposition"] == subject._UNLABELED_EXACT_SUBTOTAL_CORROBORATION
    ]
    assert [(receipt["row_kind"], receipt["role"]) for receipt in receipts] == [
        ("TRAILING_VALUE_ROW", "INTERBANK_LOAN_GROUP"),
        ("INTERNAL_UNASSIGNED_NUMERIC_CLUSTER", "INTERBANK_DEPOSIT_GROUP"),
    ]
    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    resolved = {record["role"]: record for record in closure["resolved_roles"]}
    assert resolved["INTERBANK_DEPOSIT_GROUP"]["source"] is None
    assert resolved["INTERBANK_LOAN_GROUP"]["source"] is None
    assert resolved["INTERBANK_DEPOSITS_AND_LOANS"]["source"]["kind"] == "TRAILING_VALUE_ROW"
    assert [
        value["number"]["coefficient"]
        for value in resolved["INTERBANK_DEPOSITS_AND_LOANS"]["values"]
    ] == [150, 120]
    assert (
        subject.validate_accounting_scoped_hierarchical_table_closure_replay_v2(
            closure, axis, topology, hierarchy
        )
        == closure
    )


def test_v4_explicit_unknown_same_row_label_cannot_be_laundered_as_unlabeled_subtotal() -> None:
    project_root = Path(__file__).resolve().parents[2]
    topology = json.loads(
        (project_root / "config/families/tm-interbank-deposits-loans-topology-v4.json").read_text()
    )
    hierarchy = json.loads(
        (
            project_root / "config/families/tm-interbank-deposits-loans-evaluation-v4.json"
        ).read_text()
    )["hierarchical_closure_spec"]
    pages = _vib_shaped_unlabeled_subtotal_pages()
    lines = pages[0]["lines"]
    subtotal_index = next(index for index, line in enumerate(lines) if line["bbox"][1] == 390)
    lines.insert(subtotal_index, _line(10_001, "UPAS L/C", "", [45, 390, 430, 410]))
    for ordinal, line in enumerate(lines):
        line["line_ordinal"] = ordinal
        line["sample_id"] = f"sample-{ordinal + 1:09d}"
        line["crop_ref"] = {
            "path": f"opaque/crop-{ordinal + 1:04d}.png",
            "sha256": f"{ordinal + 1:064x}",
            "size_bytes": 100 + ordinal,
        }

    axis, closure = _closure(pages, topology=topology, hierarchy=hierarchy)

    cluster = next(
        item
        for item in axis["internal_unassigned_numeric_clusters"]
        if item["same_row_label_evidence"]
    )
    assert cluster["label_lane_status"] == occurrence_v2._LABELED_LABEL_LANE_STATUS
    assert cluster["same_row_label_evidence"][0]["vietocr_text"] == "UPAS L/C"
    receipt = next(
        item
        for item in closure["coverage_receipt"]
        if item["source_record"].get("cluster_id") == cluster["cluster_id"]
    )
    assert receipt["disposition"] == "UNRESOLVED_SOURCE_ONLY_INTERNAL_NUMERIC_CLUSTER"
    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    assert not any(
        item["disposition"] == subject._UNLABELED_EXACT_SUBTOTAL_CORROBORATION
        and item["source_record"].get("cluster_id") == cluster["cluster_id"]
        for item in closure["coverage_receipt"]
    )

    def rekey_cluster(attacked: dict, attacked_cluster: dict, old_cluster_id: str) -> None:
        material = copy.deepcopy(attacked_cluster)
        material.pop("cluster_id")
        attacked_cluster["cluster_id"] = "aforav2:unassigned:" + canonical_json_sha256_v1(material)
        for sample in attacked["numeric_sample_universe"]:
            if sample["owner_id"] == old_cluster_id:
                sample["owner_id"] = attacked_cluster["cluster_id"]
        axis_material = copy.deepcopy(attacked)
        axis_material.pop("occurrence_axis_id")
        attacked["occurrence_axis_id"] = "aforav2:axis:" + canonical_json_sha256_v1(axis_material)

    evidence_deleted = copy.deepcopy(axis)
    attacked_cluster = next(
        item
        for item in evidence_deleted["internal_unassigned_numeric_clusters"]
        if item["same_row_label_evidence"]
    )
    old_cluster_id = attacked_cluster["cluster_id"]
    attacked_cluster["same_row_label_evidence"] = []
    attacked_cluster["label_lane_status"] = occurrence_v2._UNLABELED_LABEL_LANE_STATUS
    rekey_cluster(evidence_deleted, attacked_cluster, old_cluster_id)
    with pytest.raises(
        occurrence_v2.AccountingFamilyOccurrenceRowAxisV2Error,
        match="label-lane status did not replay",
    ):
        occurrence_v2._validate_result(evidence_deleted)

    band_deleted = copy.deepcopy(axis)
    attacked_cluster = next(
        item
        for item in band_deleted["internal_unassigned_numeric_clusters"]
        if item["same_row_label_evidence"]
    )
    old_cluster_id = attacked_cluster["cluster_id"]
    band = attacked_cluster["inspected_label_band"]
    band["source_line_axis"] = [
        line for line in band["source_line_axis"] if line["vietocr_text"] != "UPAS L/C"
    ]
    band["source_line_axis_sha256"] = canonical_json_sha256_v1(band["source_line_axis"])
    band_material = copy.deepcopy(band)
    band_material.pop("receipt_id")
    band["receipt_id"] = "aforav2:label-band:" + canonical_json_sha256_v1(band_material)
    attacked_cluster["same_row_label_evidence"] = []
    attacked_cluster["label_lane_status"] = occurrence_v2._UNLABELED_LABEL_LANE_STATUS
    rekey_cluster(band_deleted, attacked_cluster, old_cluster_id)
    assert occurrence_v2._validate_result(band_deleted) == band_deleted

    scan = topology_v1.build_accounting_family_topology_scan_v1(
        row_v1._topology_pages(pages), topology
    )
    policy = {
        "format_version": occurrence_v2.POLICY_FORMAT_VERSION,
        "require_authenticated_existing_dash_pixels": True,
        "retain_all_context_bound_role_occurrences": True,
    }
    with pytest.raises(
        occurrence_v2.AccountingFamilyOccurrenceRowAxisV2Error,
        match="does not replay exactly",
    ):
        occurrence_v2.validate_accounting_family_occurrence_row_axis_replay_v2(
            band_deleted,
            pages,
            topology,
            scan,
            scan["regions"][0],
            policy,
        )


def test_v4_single_equal_loan_and_root_unlabeled_row_is_ambiguous() -> None:
    project_root = Path(__file__).resolve().parents[2]
    topology = json.loads(
        (project_root / "config/families/tm-interbank-deposits-loans-topology-v4.json").read_text()
    )
    hierarchy = json.loads(
        (
            project_root / "config/families/tm-interbank-deposits-loans-evaluation-v4.json"
        ).read_text()
    )["hierarchical_closure_spec"]
    pages = _pages(
        [
            ("Tiền gửi tại các TCTD khác", "0", "0"),
            ("Cho vay các TCTD khác", "", ""),
            ("Bằng VND", "50", "40"),
            ("Bằng ngoại tệ", "0", "0"),
        ],
        trailing=[("50", "40")],
    )
    pages[0]["lines"][0]["vietocr_text"] = "Tiền gửi và cho vay các TCTD khác"

    _axis_value, closure = _closure(pages, topology=topology, hierarchy=hierarchy)

    receipt = next(
        receipt
        for receipt in closure["coverage_receipt"]
        if receipt["row_kind"] == "TRAILING_VALUE_ROW"
    )
    assert receipt["disposition"] == subject._UNLABELED_AMBIGUOUS_SUBTOTAL_DISPOSITION
    assert receipt["role"] == "INTERBANK_LOAN_GROUP"
    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    assert any(
        reason.startswith("AMBIGUOUS_UNLABELED_SUBTOTAL_SOURCE:INTERBANK_LOAN_GROUP:")
        for reason in closure["unresolved_reasons"]
    )


def test_v4_unlabeled_subtotal_target_cannot_be_forged_by_coherent_rehash() -> None:
    project_root = Path(__file__).resolve().parents[2]
    topology = json.loads(
        (project_root / "config/families/tm-interbank-deposits-loans-topology-v4.json").read_text()
    )
    hierarchy = json.loads(
        (
            project_root / "config/families/tm-interbank-deposits-loans-evaluation-v4.json"
        ).read_text()
    )["hierarchical_closure_spec"]
    _axis_value, closure = _closure(
        _vib_shaped_unlabeled_subtotal_pages(), topology=topology, hierarchy=hierarchy
    )
    attacked = copy.deepcopy(closure)
    receipt = next(
        receipt
        for receipt in attacked["coverage_receipt"]
        if receipt["row_kind"] == "INTERNAL_UNASSIGNED_NUMERIC_CLUSTER"
        and receipt["disposition"] == subject._UNLABELED_EXACT_SUBTOTAL_CORROBORATION
    )
    receipt["role"] = "INTERBANK_LOAN_GROUP"
    receipt["coverage_id"] = receipt["coverage_id"].replace(
        "INTERBANK_DEPOSIT_GROUP", "INTERBANK_LOAN_GROUP"
    )
    _coherently_rehash_closure(attacked)

    with pytest.raises(
        subject.AccountingScopedHierarchicalTableClosureV2Error,
        match="designation did not replay|boundary proof drifted",
    ):
        subject._validate_result(attacked)


def test_one_edit_role_match_cannot_close_while_exact_source_can() -> None:
    exact_pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
            ("Tổng cộng", "150", "130"),
        ]
    )
    typo_pages = copy.deepcopy(exact_pages)
    typo_pages[0]["lines"][4]["vietocr_text"] = "Tiền gửi tại TCTD kháx"

    _exact_axis, exact = _closure(exact_pages, hierarchy=_hierarchy_v2())
    typo_axis, typo = _closure(typo_pages, hierarchy=_hierarchy_v2())

    assert exact["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    deposit = next(row for row in typo_axis["row_axis"]["rows"] if row["role"] == "DEPOSIT_GROUP")
    assert deposit["label_match"]["match_kind"].startswith("ONE_EDIT_")
    receipt = next(
        record for record in typo["coverage_receipt"] if record["role"] == "DEPOSIT_GROUP"
    )
    assert receipt["disposition"] == "UNRESOLVED_ONE_EDIT_ROLE_OR_SCOPE_MATCH"
    assert typo["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"


def test_other_requires_an_exact_unique_scope_owner_before_it_can_close() -> None:
    topology = copy.deepcopy(_topology())
    topology["children"].insert(
        -1,
        {
            "matchers": [_matcher("Khác", "LOAN_GROUP")],
            "presence": "OPTIONAL",
            "role": "LOAN_OTHER",
            "role_kind": "ADDITIVE_CHILD",
        },
    )
    hierarchy = _hierarchy_v2()
    hierarchy["equations"][0]["component_role_alternatives"].append(
        _alternative(["LOAN_OTHER"], derive=False)
    )
    hierarchy["repeated_role_policy"]["aggregate_roles"].append("LOAN_OTHER")
    hierarchy["repeated_role_policy"]["aggregate_roles"].sort()
    exact_pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "5", "4"),
            ("Khác", "5", "4"),
            ("Tổng cộng", "105", "94"),
        ]
    )
    typo_pages = copy.deepcopy(exact_pages)
    typo_pages[0]["lines"][7]["vietocr_text"] = "Cho vay TCTD kháx"

    _exact_axis, exact = _closure(exact_pages, topology=topology, hierarchy=hierarchy)
    typo_axis, typo = _closure(typo_pages, topology=topology, hierarchy=hierarchy)

    assert exact["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    exact_other = next(
        record for record in exact["coverage_receipt"] if record["role"] == "LOAN_OTHER"
    )
    assert exact_other["disposition"] == "LOCAL_EXHAUSTIVE_COMPONENT_OCCURRENCE"
    typo_other_occurrence = next(
        occurrence
        for occurrence in typo_axis["role_occurrences"]
        if occurrence["role"] == "LOAN_OTHER"
    )
    assert typo_other_occurrence["scope_owner_match_kind"].startswith("ONE_EDIT_")
    typo_other = next(
        record for record in typo["coverage_receipt"] if record["role"] == "LOAN_OTHER"
    )
    assert typo_other["disposition"] == "UNRESOLVED_ONE_EDIT_ROLE_OR_SCOPE_MATCH"
    assert typo["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"


def test_declared_source_only_role_is_typed_but_never_accounting_resolved() -> None:
    topology = copy.deepcopy(_topology())
    topology["children"].insert(
        -1,
        {
            "matchers": [_matcher("Dự phòng rủi ro")],
            "presence": "OPTIONAL",
            "role": "AMBIGUOUS_PROVISION",
            "role_kind": "NONADDITIVE_CHILD",
        },
    )
    hierarchy = _hierarchy_v2(source_only_veto_roles=["AMBIGUOUS_PROVISION"])
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
            ("Dự phòng rủi ro", "-5", "-4"),
            ("Tổng cộng", "150", "130"),
        ]
    )

    _axis_value, closure = _closure(pages, topology=topology, hierarchy=hierarchy)

    receipt = next(
        record for record in closure["coverage_receipt"] if record["role"] == "AMBIGUOUS_PROVISION"
    )
    assert receipt["disposition"] == "UNRESOLVED_SOURCE_ONLY_SCHEMA_INELIGIBLE_ROLE"
    assert "AMBIGUOUS_PROVISION" not in {record["role"] for record in closure["resolved_roles"]}
    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"


@pytest.mark.parametrize(
    ("label", "expected_role", "source_only"),
    [
        (
            "Chiết khấu, tái chiết khấu bằng VND",
            "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND",
            False,
        ),
        (
            "Chiết khấu, tái chiết khấu bằng ngoại tệ",
            "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_FOREIGN_CURRENCY",
            False,
        ),
        (
            "Chiết khấu, tái chiết khấu",
            "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS",
            True,
        ),
        ("Dự phòng rủi ro", "TOTAL_INTERBANK_PROVISION", False),
        (
            "Bằng vàng và ngoại tệ",
            "INTERBANK_LOAN_GOLD_AND_FOREIGN_CURRENCY",
            True,
        ),
    ],
)
def test_real_family3_currency_specific_roles_close_but_ambiguous_roles_veto(
    label: str,
    expected_role: str,
    source_only: bool,
) -> None:
    project_root = Path(__file__).resolve().parents[2]
    topology = json.loads(
        (project_root / "config/families/tm-interbank-deposits-loans-topology-v4.json").read_text()
    )
    hierarchy = json.loads(
        (
            project_root / "config/families/tm-interbank-deposits-loans-evaluation-v4.json"
        ).read_text()
    )["hierarchical_closure_spec"]
    provision_is_total = label == "Dự phòng rủi ro"
    pages = _pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
            (
                label,
                "-5" if provision_is_total else "5",
                "-4" if provision_is_total else "4",
            ),
        ]
    )
    pages[0]["lines"][0]["vietocr_text"] = "Tiền gửi và cho vay các TCTD khác"
    for ordinal, token, bbox in (
        (1, "145" if provision_is_total else "150", [610, 15, 700, 38]),
        (2, "126" if provision_is_total else "130", [810, 15, 900, 38]),
    ):
        pages[0]["lines"][ordinal]["vietocr_text"] = token
        pages[0]["lines"][ordinal]["numeric_recognition"]["raw_prediction"] = token
        pages[0]["lines"][ordinal]["bbox"] = bbox

    _axis_value, closure = _closure(pages, topology=topology, hierarchy=hierarchy)

    receipt = next(
        record for record in closure["coverage_receipt"] if record["role"] == expected_role
    )
    if source_only:
        assert receipt["disposition"] == "UNRESOLVED_SOURCE_ONLY_SCHEMA_INELIGIBLE_ROLE"
        assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
        assert expected_role not in {record["role"] for record in closure["resolved_roles"]}
    else:
        expected_disposition = (
            "GLOBAL_HIERARCHY_SOURCE_OCCURRENCE"
            if expected_role == "TOTAL_INTERBANK_PROVISION"
            else "NONADDITIVE_VISIBLE_SOURCE_ROLE"
        )
        assert receipt["disposition"] == expected_disposition
        assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
        assert expected_role in {record["role"] for record in closure["resolved_roles"]}


@pytest.mark.parametrize(
    ("loan_values", "root_values", "local_components", "root_components"),
    [
        (
            ("50", "40"),
            ("145", "126"),
            ["LOAN_VND", "LOAN_FOREIGN_CURRENCY"],
            ["DEPOSIT_GROUP", "LOAN_GROUP", "LOAN_PROVISION"],
        ),
        (
            ("45", "36"),
            ("145", "126"),
            ["LOAN_VND", "LOAN_FOREIGN_CURRENCY", "LOAN_PROVISION"],
            ["DEPOSIT_GROUP", "LOAN_GROUP"],
        ),
    ],
)
def test_visible_equations_adjudicate_root_sibling_or_local_provision_once(
    loan_values: tuple[str, str],
    root_values: tuple[str, str],
    local_components: list[str],
    root_components: list[str],
) -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", *loan_values),
            ("Bằng VND", "30", "25"),
            ("Bằng ngoại tệ", "20", "15"),
            ("Dự phòng cho vay TCTD khác", "-5", "-4"),
            ("Tổng cộng", *root_values),
        ]
    )
    axis, closure = _closure(pages)

    assert axis["status"] == (
        "OCCURRENCE_ROW_AXIS_BOUND_WITH_AUTHENTICATED_EXISTING_DASHES_PROPOSAL_ONLY"
    )
    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    global_by_role = {item["result_role"]: item for item in closure["equations"]["global"]}
    assert global_by_role["LOAN_GROUP"]["component_roles_present"] == local_components
    assert global_by_role["INTERBANK"]["component_roles_present"] == root_components
    provision = next(
        item for item in closure["coverage_receipt"] if item["role"] == "LOAN_PROVISION"
    )
    assert provision["disposition"] in {
        "GLOBAL_HIERARCHY_SOURCE_OCCURRENCE",
        "LOCAL_EXHAUSTIVE_COMPONENT_OCCURRENCE",
    }
    assert (
        subject.validate_accounting_scoped_hierarchical_table_closure_replay_v2(
            closure, axis, _topology(), _hierarchy()
        )
        == closure
    )


def test_repeated_role_under_same_owner_and_partial_equation_fail_closed() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
            ("Bằng VND", "20", "15"),
            ("Bằng VND", "30", "25"),
            ("Tổng cộng", "150", "130"),
        ]
    )
    _axis_value, closure = _closure(pages)

    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    assert any(
        reason.startswith("REPEATED_ROLE_SCOPE_IS_NOT_DISJOINT:LOAN_VND")
        for reason in closure["unresolved_reasons"]
    )
    assert any(
        reason.startswith("LOCAL_VISIBLE_RESULT_LACKS_EXHAUSTIVE_COMPONENT_SET")
        for reason in closure["unresolved_reasons"]
    )


def test_repeated_local_subtotals_are_corroborated_before_disjoint_aggregation() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "30", "25"),
            ("Bằng VND", "20", "15"),
            ("Bằng ngoại tệ", "10", "10"),
            ("Cho vay TCTD khác", "12", "10"),
            ("Bằng VND", "9", "8"),
            ("Bằng ngoại tệ", "3", "2"),
            ("Tổng cộng", "142", "125"),
        ]
    )
    _axis_value, closure = _closure(pages)

    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    loan = next(item for item in closure["resolved_roles"] if item["role"] == "LOAN_GROUP")
    assert loan["resolution_kind"] == (
        "DERIVED_EXACT_DISJOINT_OCCURRENCE_SUM_CORROBORATED_BY_COMPONENTS"
    )
    assert (
        len(
            [
                item
                for item in closure["equations"]["local"]
                if item["status"]
                == "LOCAL_VISIBLE_SUBTOTAL_CORROBORATED_BY_EXACT_SCOPED_COMPONENTS"
            ]
        )
        == 2
    )


def test_one_label_only_local_scope_can_use_exhaustive_global_derivation() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "", ""),
            ("Cho vay TCTD khác", "", ""),
            ("Bằng VND", "30", "25"),
            ("Bằng ngoại tệ", "20", "15"),
        ],
        trailing=[("150", "130")],
    )
    _axis_value, closure = _closure(pages)

    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    assert [record["status"] for record in closure["equations"]["local"]] == [
        "LOCAL_SINGLE_SCOPE_WITHOUT_VISIBLE_SUBTOTAL_DEFERRED_TO_EXHAUSTIVE_GLOBAL_EQUATION"
    ]
    loan = next(record for record in closure["resolved_roles"] if record["role"] == "LOAN_GROUP")
    assert loan["resolution_kind"] == "DERIVED_EXACT_COMPONENT_SUM"
    assert loan["component_roles"] == ["LOAN_VND", "LOAN_FOREIGN_CURRENCY"]


def test_missing_local_subtotals_cannot_authorize_cross_scope_leaf_aggregation() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "", ""),
            ("Bằng VND", "20", "15"),
            ("Bằng ngoại tệ", "10", "10"),
            ("Cho vay TCTD khác", "", ""),
            ("Bằng VND", "9", "8"),
            ("Bằng ngoại tệ", "3", "2"),
        ],
        trailing=[("142", "125")],
    )
    _axis_value, closure = _closure(pages)

    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    assert [record["status"] for record in closure["equations"]["local"]] == [
        "LOCAL_SUBTOTAL_RESULT_MISSING_OR_INCOMPLETE_VETO",
        "LOCAL_SUBTOTAL_RESULT_MISSING_OR_INCOMPLETE_VETO",
    ]
    assert (
        len(
            [
                reason
                for reason in closure["unresolved_reasons"]
                if reason.startswith("LOCAL_SUBTOTAL_RESULT_MISSING_OR_INCOMPLETE:LOAN_GROUP:")
            ]
        )
        == 2
    )
    assert any(
        reason.startswith("LOCAL_COMPONENT_SCOPE_LACKS_CORROBORATED_SUBTOTAL:LOAN_VND:")
        for reason in closure["unresolved_reasons"]
    )
    assert not any(
        record["role"] in {"LOAN_VND", "LOAN_FOREIGN_CURRENCY", "LOAN_GROUP", "INTERBANK"}
        for record in closure["resolved_roles"]
    )
    assert not any(
        record["resolution_kind"] == "DERIVED_EXACT_DISJOINT_OCCURRENCE_SUM"
        for record in closure["resolved_roles"]
    )


def test_real_v4_config_rejects_singleton_that_omits_visible_deposit_subtree() -> None:
    project_root = Path(__file__).resolve().parents[2]
    topology = json.loads(
        (project_root / "config/families/tm-interbank-deposits-loans-topology-v4.json").read_text()
    )
    hierarchy = json.loads(
        (
            project_root / "config/families/tm-interbank-deposits-loans-evaluation-v4.json"
        ).read_text()
    )["hierarchical_closure_spec"]
    pages = _pages(
        [
            ("Tiền gửi tại các TCTD khác", "60", "50"),
            ("Tiền gửi không kỳ hạn", "60", "50"),
            ("Bằng VND", "60", "50"),
            ("Tiền gửi có kỳ hạn", "40", "30"),
            ("Bằng VND", "40", "30"),
            ("Cho vay các TCTD khác", "50", "40"),
            ("Bằng VND", "50", "40"),
        ],
        trailing=[("110", "90")],
    )
    pages[0]["lines"][0]["vietocr_text"] = "Tiền gửi và cho vay các TCTD khác"

    _axis_value, closure = _closure(pages, topology=topology, hierarchy=hierarchy)

    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    deposit = next(
        record
        for record in closure["equations"]["global"]
        if record["result_role"] == "INTERBANK_DEPOSIT_GROUP"
    )
    assert deposit["status"] == "VISIBLE_RESULT_MISMATCH_VETO"
    assert deposit["component_roles_present"] == []
    assert (
        "VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM:INTERBANK_DEPOSIT_GROUP"
        in closure["unresolved_reasons"]
    )
    assert any(
        reason.startswith("ACCOUNTING_COMPONENT_ROLE_USE_COUNT_NOT_ONE:TERM_DEPOSIT_GROUP:")
        for reason in closure["unresolved_reasons"]
    )


def test_real_v4_acb_shaped_preceding_demand_subtotal_is_not_reused_as_term_total() -> None:
    project_root = Path(__file__).resolve().parents[2]
    topology = json.loads(
        (project_root / "config/families/tm-interbank-deposits-loans-topology-v4.json").read_text()
    )
    hierarchy = json.loads(
        (
            project_root / "config/families/tm-interbank-deposits-loans-evaluation-v4.json"
        ).read_text()
    )["hierarchical_closure_spec"]

    axis, closure = _closure(
        _acb_shaped_preceding_subtotal_pages(),
        topology=topology,
        hierarchy=hierarchy,
    )

    assert "TERM_DEPOSIT_GROUP" not in {row["role"] for row in axis["row_axis"]["rows"]}
    assert [evidence["status"] for evidence in axis["coextensive_structural_numeric_evidence"]] == [
        "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_ALREADY_OWNED"
    ]
    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    resolved = {record["role"]: record for record in closure["resolved_roles"]}
    assert [
        value["number"]["coefficient"] for value in resolved["TERM_DEPOSIT_GROUP"]["values"]
    ] == [
        120,
        90,
    ]
    assert [
        value["number"]["coefficient"]
        for value in resolved["INTERBANK_DEPOSITS_AND_LOANS"]["values"]
    ] == [200, 150]
    receipt = next(
        record
        for record in closure["coverage_receipt"]
        if record["row_kind"] == "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE"
    )
    assert receipt["disposition"] == "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_ALREADY_OWNED"
    assert (
        subject.validate_accounting_scoped_hierarchical_table_closure_replay_v2(
            closure,
            axis,
            topology,
            hierarchy,
        )
        == closure
    )


def test_validator_rejects_duplicate_coextensive_receipt_after_coherent_rehash() -> None:
    project_root = Path(__file__).resolve().parents[2]
    topology = json.loads(
        (project_root / "config/families/tm-interbank-deposits-loans-topology-v4.json").read_text()
    )
    hierarchy = json.loads(
        (
            project_root / "config/families/tm-interbank-deposits-loans-evaluation-v4.json"
        ).read_text()
    )["hierarchical_closure_spec"]
    _axis_value, closure = _closure(
        _acb_shaped_preceding_subtotal_pages(),
        topology=topology,
        hierarchy=hierarchy,
    )
    attacked = copy.deepcopy(closure)
    duplicate = copy.deepcopy(
        next(
            record
            for record in attacked["coverage_receipt"]
            if record["row_kind"] == "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE"
        )
    )
    duplicate["coverage_id"] += ":duplicate"
    attacked["coverage_receipt"].append(duplicate)
    _coherently_rehash_closure(attacked)

    with pytest.raises(
        subject.AccountingScopedHierarchicalTableClosureV2Error,
        match="coverage receipt drifted",
    ):
        subject._validate_result(attacked)


def test_real_v4_acb_shaped_one_unit_prior_subtotal_conflict_is_not_suppressed() -> None:
    project_root = Path(__file__).resolve().parents[2]
    topology = json.loads(
        (project_root / "config/families/tm-interbank-deposits-loans-topology-v4.json").read_text()
    )
    hierarchy = json.loads(
        (
            project_root / "config/families/tm-interbank-deposits-loans-evaluation-v4.json"
        ).read_text()
    )["hierarchical_closure_spec"]

    axis, closure = _closure(
        _acb_shaped_preceding_subtotal_pages(demand_subtotal_current="31"),
        topology=topology,
        hierarchy=hierarchy,
    )

    assert axis["coextensive_structural_numeric_evidence"] == []
    assert next(row for row in axis["row_axis"]["rows"] if row["role"] == "TERM_DEPOSIT_GROUP")
    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    assert any(
        reason.startswith("LOCAL_VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM:TERM_DEPOSIT_GROUP:")
        for reason in closure["unresolved_reasons"]
    )


def test_real_v4_equal_prior_and_current_scope_subtotal_is_ambiguous_veto() -> None:
    project_root = Path(__file__).resolve().parents[2]
    topology = json.loads(
        (project_root / "config/families/tm-interbank-deposits-loans-topology-v4.json").read_text()
    )
    hierarchy = json.loads(
        (
            project_root / "config/families/tm-interbank-deposits-loans-evaluation-v4.json"
        ).read_text()
    )["hierarchical_closure_spec"]
    pages = _acb_shaped_preceding_subtotal_pages()
    replacements = {15: "20", 16: "15", 18: "10", 19: "5", 24: "110", 25: "80"}
    for line in pages[0]["lines"]:
        if line["line_ordinal"] in replacements:
            replacement = replacements[line["line_ordinal"]]
            line["vietocr_text"] = replacement
            line["numeric_recognition"]["raw_prediction"] = replacement

    axis, closure = _closure(pages, topology=topology, hierarchy=hierarchy)

    term_row = next(row for row in axis["row_axis"]["rows"] if row["role"] == "TERM_DEPOSIT_GROUP")
    assert [value["parsed_token"]["coefficient"] for value in term_row["values"]] == [30, 20]
    assert [evidence["status"] for evidence in axis["coextensive_structural_numeric_evidence"]] == [
        "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_AMBIGUOUS_OWNERSHIP_VETO"
    ]
    assert axis["status"] == "UNRESOLVED_OCCURRENCE_ROW_AXIS_OR_EXISTING_DASH_EVIDENCE"
    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    assert any(
        reason.startswith("COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_AMBIGUOUS_OWNERSHIP_VETO:")
        for reason in closure["unresolved_reasons"]
    )
    assert not any(
        record["row_kind"] == "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE"
        for record in closure["coverage_receipt"]
    )
    local = next(
        record
        for record in closure["equations"]["local"]
        if record["result_role"] == "TERM_DEPOSIT_GROUP"
    )
    assert local["status"] == "LOCAL_VISIBLE_SUBTOTAL_CORROBORATED_BY_EXACT_SCOPED_COMPONENTS"


@pytest.mark.parametrize("tamper", ["EMPTY_EVIDENCE", "UNKNOWN_STATUS"])
def test_validator_rejects_malformed_ambiguous_evidence_after_coherent_rehash(
    tamper: str,
) -> None:
    project_root = Path(__file__).resolve().parents[2]
    topology = json.loads(
        (project_root / "config/families/tm-interbank-deposits-loans-topology-v4.json").read_text()
    )
    hierarchy = json.loads(
        (
            project_root / "config/families/tm-interbank-deposits-loans-evaluation-v4.json"
        ).read_text()
    )["hierarchical_closure_spec"]
    pages = _acb_shaped_preceding_subtotal_pages()
    replacements = {15: "20", 16: "15", 18: "10", 19: "5", 24: "110", 25: "80"}
    for line in pages[0]["lines"]:
        if line["line_ordinal"] in replacements:
            replacement = replacements[line["line_ordinal"]]
            line["vietocr_text"] = replacement
            line["numeric_recognition"]["raw_prediction"] = replacement
    _axis_value, closure = _closure(pages, topology=topology, hierarchy=hierarchy)
    attacked = copy.deepcopy(closure)
    if tamper == "EMPTY_EVIDENCE":
        attacked["coextensive_structural_numeric_evidence"] = [{}]
    else:
        attacked["coextensive_structural_numeric_evidence"][0]["status"] = "GARBAGE"
    _coherently_rehash_closure(attacked)

    with pytest.raises(
        subject.AccountingScopedHierarchicalTableClosureV2Error,
        match="coextensive source receipt drifted",
    ):
        subject._validate_result(attacked)


def test_partial_and_unbound_visible_numeric_occurrences_each_receive_one_veto_receipt() -> None:
    topology = _topology()
    topology["children"].append(
        {
            "matchers": [_matcher("Khoản mục ngoài phương trình")],
            "presence": "OPTIONAL",
            "role": "UNBOUND_ADDITIVE_ROLE",
            "role_kind": "ADDITIVE_CHILD",
        }
    )
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
            ("Bằng VND", "20", ""),
            ("Khoản mục ngoài phương trình", "7", "6"),
            ("Tổng cộng", "150", "130"),
        ]
    )
    _axis_value, closure = _closure(pages, topology=topology)

    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    dispositions = {item["role"]: item["disposition"] for item in closure["coverage_receipt"]}
    assert dispositions["LOAN_VND"] == "UNRESOLVED_PARTIAL_ROLE_NUMERIC_OCCURRENCE"
    assert dispositions["UNBOUND_ADDITIVE_ROLE"] == "UNBOUND_VISIBLE_ACCOUNTING_OCCURRENCE"
    assert (
        len(
            {
                item["coverage_id"]
                for item in closure["coverage_receipt"]
                if item["role"] in {"LOAN_VND", "UNBOUND_ADDITIVE_ROLE"}
            }
        )
        == 2
    )


def test_partial_local_subtotal_without_children_is_one_typed_veto_not_an_exception() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", ""),
            ("Tổng cộng", "150", "130"),
        ]
    )

    axis, closure = _closure(pages)

    assert axis["status"] == "UNRESOLVED_OCCURRENCE_ROW_AXIS_OR_EXISTING_DASH_EVIDENCE"
    local = next(
        record for record in closure["equations"]["local"] if record["result_role"] == "LOAN_GROUP"
    )
    assert local["status"] == "LOCAL_SUBTOTAL_RESULT_PARTIAL_VALUE_LANES_VETO"
    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    assert any(
        reason.startswith("LOCAL_SUBTOTAL_RESULT_PARTIAL_VALUE_LANES:LOAN_GROUP:")
        for reason in closure["unresolved_reasons"]
    )
    receipt = next(
        record for record in closure["coverage_receipt"] if record["role"] == "LOAN_GROUP"
    )
    assert receipt["disposition"] == "UNRESOLVED_PARTIAL_ROLE_NUMERIC_OCCURRENCE"


def test_empty_local_subtotal_without_children_is_typed_instead_of_raising() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "", ""),
            ("Tổng cộng", "150", "130"),
        ]
    )

    _axis_value, closure = _closure(pages)

    local = next(
        record for record in closure["equations"]["local"] if record["result_role"] == "LOAN_GROUP"
    )
    assert local["status"] == "LOCAL_SUBTOTAL_RESULT_MISSING_OR_INCOMPLETE_VETO"
    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    assert any(
        reason.startswith("LOCAL_SUBTOTAL_RESULT_MISSING_OR_INCOMPLETE:LOAN_GROUP:")
        for reason in closure["unresolved_reasons"]
    )


def test_v4_printed_residual_two_with_six_components_is_rounding_corroborated_without_backsolve() -> (
    None
):
    component_values = ["10000000", "11000000", "12000000", "13000000", "14000000", "12305188"]
    pages = _pages(
        [
            (label, value, value)
            for label, value in zip(_ROUNDING_COMPONENT_LABELS, component_values, strict=True)
        ],
        trailing=[("72305188", "72305186")],
    )
    _axis_value, closure = _closure(
        pages,
        topology=_rounding_topology(),
        hierarchy=_rounding_hierarchy(),
    )

    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    root = next(
        item for item in closure["equations"]["global"] if item["result_role"] == "INTERBANK"
    )
    assert root["status"] == (
        "VISIBLE_TRAILING_RESULT_ROUNDING_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS"
    )
    evidence = root["residual_evidence"][0]
    assert evidence["convention"] == "PRINTED_RESULT_MINUS_EXHAUSTIVE_COMPONENT_SUM"
    assert [lane["residual_number"]["coefficient"] for lane in evidence["lanes"]] == [
        0,
        -2,
    ]
    rounding = root["rounding_evidence"][0]
    assert rounding["status"] == "ROUNDING_BOUND_SATISFIED_ALL_LANES"
    assert [lane["independently_printed_component_count"] for lane in rounding["lanes"]] == [
        6,
        6,
    ]
    assert [lane["bound_component_count_plus_one"] for lane in rounding["lanes"]] == [7, 7]
    assert [lane["twice_absolute_residual"] for lane in rounding["lanes"]] == [0, 4]
    resolved = next(item for item in closure["resolved_roles"] if item["role"] == "INTERBANK")
    assert resolved["resolution_kind"] == (
        "VISIBLE_TRAILING_TOTAL_ROUNDING_CORROBORATED_BY_COMPONENTS"
    )
    assert [value["number"]["coefficient"] for value in resolved["values"]] == [
        72305188,
        72305186,
    ]
    assert [value["number"]["coefficient"] for value in resolved["values"]] != [
        72305188,
        72305188,
    ]
    receipt = next(
        item for item in closure["coverage_receipt"] if item["row_kind"] == "TRAILING_VALUE_ROW"
    )
    assert receipt["disposition"] == ("SELECTED_ROUNDING_CORROBORATED_VISIBLE_TRAILING_ROOT_SOURCE")
    assert (
        subject.validate_accounting_scoped_hierarchical_table_closure_replay_v2(
            closure,
            _axis_value,
            _rounding_topology(),
            _rounding_hierarchy(),
        )
        == closure
    )
    nodes, _schema_ref = mapping_v1._schema_graph(Path(__file__).resolve().parents[2])
    trial = {
        "additive_closure": closure,
        "column_context": {
            "period_axis": [
                {"column_ordinal": 0, "resolved_period": "31/12/2025"},
                {"column_ordinal": 1, "resolved_period": "31/12/2024"},
            ],
            "period_semantics": "BALANCE_COMPARATIVE",
            "status": "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY",
            "unit_axis": [
                {
                    "column_ordinal": lane,
                    "currency": "VND",
                    "magnitude_power10": 6,
                    "unit_kind": "MONEY",
                }
                for lane in range(2)
            ],
        },
        "document_ordinal": 18,
        "evidence_status": "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY",
        "private_provenance": {"scope": "CONSOLIDATED"},
        "row_axis": _axis_value["row_axis"],
        "source_pdf_ref": {
            "path": "fixture/mbb-trial-18.pdf",
            "sha256": "1" * 64,
            "size_bytes": 1,
        },
        "unresolved_reasons": [],
    }
    mapping = mapping_v1._trial(
        trial,
        nodes[575],
        {},
        [],
        schema_period_type="SNAPSHOT",
        schema_binding_spec={
            "family_id": "INTERBANK",
            "family_report_norm_id": 575,
            "family_root_mapping_policy": "REQUIRE_HIERARCHICALLY_RESOLVED",
            "format_version": mapping_v1.SPEC_FORMAT_VERSION_V4,
            "ignored_roles": [*_ROUNDING_COMPONENT_ROLES, "EXPLICIT_FAMILY_TOTAL"],
            "role_bindings": [],
        },
    )
    assert mapping["mapping_status"] == "VERIFIED_BY_CODEX"
    root_mapping = next(item for item in mapping["mappings"] if item["report_norm_id"] == 575)
    assert [item["numeric_value"]["coefficient"] for item in root_mapping["values"]] == [
        72305188,
        72305186,
    ]


def test_v4_mbb_shaped_authenticated_dash_zero_uses_five_cell_prior_rounding_bound() -> None:
    topology = _rounding_topology()
    rows = [
        (label, str(current), "" if prior is None else str(prior))
        for label, current, prior in zip(
            _ROUNDING_COMPONENT_LABELS,
            [10, 20, 30, 40, 50, 60],
            [10, 20, 30, 40, 50, None],
            strict=True,
        )
    ]
    pages = _pages(rows, trailing=[("210", "148")])
    rescues = _clear_detector_dash_rescue(
        pages,
        topology,
        role=_ROUNDING_COMPONENT_ROLES[-1],
    )
    axis, closure = _closure(
        pages,
        topology=topology,
        hierarchy=_rounding_hierarchy(),
        visible_dash_rescues=rescues,
    )

    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    root = closure["equations"]["global"][0]
    assert root["status"] == (
        "VISIBLE_TRAILING_RESULT_ROUNDING_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS"
    )
    rounding = root["rounding_evidence"][0]
    assert [lane["independently_printed_component_count"] for lane in rounding["lanes"]] == [
        6,
        5,
    ]
    assert [lane["bound_component_count_plus_one"] for lane in rounding["lanes"]] == [7, 6]
    assert [lane["twice_absolute_residual"] for lane in rounding["lanes"]] == [0, 4]
    assert [lane["residual_number"]["coefficient"] for lane in rounding["lanes"]] == [0, -2]
    dash_samples = [
        sample
        for sample in axis["numeric_sample_universe"]
        if sample["parsed_token"]["classification"] == "DASH_ZERO"
    ]
    assert len(dash_samples) == 1
    resolved = next(item for item in closure["resolved_roles"] if item["role"] == "INTERBANK")
    assert [value["number"]["coefficient"] for value in resolved["values"]] == [210, 148]
    assert [value["number"]["coefficient"] for value in resolved["values"]] != [210, 150]
    assert (
        subject.validate_accounting_scoped_hierarchical_table_closure_replay_v2(
            closure,
            axis,
            topology,
            _rounding_hierarchy(),
        )
        == closure
    )

    count_tamper = copy.deepcopy(closure)
    prior_lane = count_tamper["equations"]["global"][0]["rounding_evidence"][0]["lanes"][1]
    prior_lane["independently_printed_component_count"] = 6
    prior_lane["bound_component_count_plus_one"] = 7
    _coherently_rehash_closure(count_tamper)
    with pytest.raises(
        subject.AccountingScopedHierarchicalTableClosureV2Error,
        match="integer rounding lane|numeric universe record",
    ):
        subject._validate_result(count_tamper)

    classification_tamper = copy.deepcopy(closure)
    dash_sample = next(
        sample
        for sample in classification_tamper["numeric_sample_universe"]
        if sample["sample_id"] == dash_samples[0]["sample_id"]
    )
    dash_sample["parsed_token"]["classification"] = "SIGNED_NUMBER"
    _coherently_rehash_closure(classification_tamper)
    with pytest.raises(
        subject.AccountingScopedHierarchicalTableClosureV2Error,
        match="integer rounding lane|numeric universe record",
    ):
        subject._validate_result(classification_tamper)

    over_bound_pages = _pages(rows, trailing=[("210", "146")])
    over_bound_axis, over_bound = _closure(
        over_bound_pages,
        topology=topology,
        hierarchy=_rounding_hierarchy(),
        visible_dash_rescues=_clear_detector_dash_rescue(
            over_bound_pages,
            topology,
            role=_ROUNDING_COMPONENT_ROLES[-1],
        ),
    )
    assert over_bound_axis["row_axis"]["metrics"]["visible_dash_zero_count"] == 1
    assert over_bound["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    over_lane = over_bound["equations"]["global"][0]["rounding_evidence"][0]["lanes"][1]
    assert over_lane["independently_printed_component_count"] == 5
    assert over_lane["bound_component_count_plus_one"] == 6
    assert over_lane["twice_absolute_residual"] == 8

    unauthenticated_pages = _pages(
        [
            (label, str(current), "-" if prior is None else str(prior))
            for label, current, prior in zip(
                _ROUNDING_COMPONENT_LABELS,
                [10, 20, 30, 40, 50, 60],
                [10, 20, 30, 40, 50, None],
                strict=True,
            )
        ],
        trailing=[("210", "148")],
    )
    _unauthenticated_axis, unauthenticated = _closure(
        unauthenticated_pages,
        topology=topology,
        hierarchy=_rounding_hierarchy(),
    )
    assert unauthenticated["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    assert unauthenticated["equations"]["global"][0]["rounding_evidence"] == []


@pytest.mark.parametrize(
    ("residual", "expected_status"),
    [
        (3, "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"),
        (4, "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"),
    ],
)
def test_v4_rounding_bound_is_exact_at_boundary_and_vetoes_over_bound(
    residual: int, expected_status: str
) -> None:
    component_values = ["10", "20", "30", "40", "50", "60"]
    pages = _pages(
        [
            (label, value, value)
            for label, value in zip(_ROUNDING_COMPONENT_LABELS, component_values, strict=True)
        ],
        trailing=[("210", str(210 + residual))],
    )

    _axis_value, closure = _closure(
        pages,
        topology=_rounding_topology(),
        hierarchy=_rounding_hierarchy(),
    )

    root = closure["equations"]["global"][0]
    assert closure["status"] == expected_status
    lane = root["rounding_evidence"][0]["lanes"][1]
    assert lane["twice_absolute_residual"] == 2 * residual
    assert lane["bound_component_count_plus_one"] == 7
    if residual == 3:
        assert root["status"] == (
            "VISIBLE_TRAILING_RESULT_ROUNDING_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS"
        )
        resolved = next(item for item in closure["resolved_roles"] if item["role"] == "INTERBANK")
        assert resolved["values"][1]["number"]["coefficient"] == 213
    else:
        assert root["status"] == "TRAILING_NUMERIC_CHALLENGER_VETO"
        assert "INTERBANK" not in {item["role"] for item in closure["resolved_roles"]}


@pytest.mark.parametrize(
    "disallowed_classification",
    [
        "MIXED_GROUPED_INTEGER_CANDIDATE",
        "NOISE_SUFFIXED_GROUPED_INTEGER_CANDIDATE",
    ],
)
def test_v4_only_signed_number_cells_may_support_integer_rounding_bound(
    disallowed_classification: str,
) -> None:
    component_cells = [
        {
            "classification": "SIGNED_NUMBER",
            "number": {
                "coefficient": 10 if ordinal < 4 else 0,
                "percentage_mark_present": False,
                "scale": 0,
            },
            "source_sample_id": f"component-{ordinal}",
        }
        for ordinal in range(6)
    ]
    component = {
        subject._PRINTED_SOURCE_CELLS_KEY: [component_cells],
        "values": [
            {
                "column_ordinal": 0,
                "number": {
                    "coefficient": 40,
                    "percentage_mark_present": False,
                    "scale": 0,
                },
                "source_sample_ids": [cell["source_sample_id"] for cell in component_cells],
            }
        ],
    }
    printed = {
        subject._PRINTED_SOURCE_CELLS_KEY: [
            [
                {
                    "classification": "SIGNED_NUMBER",
                    "number": {
                        "coefficient": 43,
                        "percentage_mark_present": False,
                        "scale": 0,
                    },
                    "source_sample_id": "printed-result",
                }
            ]
        ],
        "source": {
            "kind": "ROLE_ROW",
            "record": {
                "label_match": {"occurrence_id": "printed-result-occurrence"},
                "role": "EXPLICIT_FAMILY_TOTAL",
            },
        },
        "values": [
            {
                "column_ordinal": 0,
                "number": {
                    "coefficient": 43,
                    "percentage_mark_present": False,
                    "scale": 0,
                },
                "source_sample_ids": ["printed-result"],
            }
        ],
    }

    accepted = subject._rounding_assessment(
        result_role="INTERBANK",
        printed=printed,
        component=component,
        component_roles=_ROUNDING_COMPONENT_ROLES,
    )
    assert accepted is not None
    assert accepted["status"] == "ROUNDING_BOUND_SATISFIED_ALL_LANES"

    for cell in component_cells[-2:]:
        cell["classification"] = disallowed_classification
    assert (
        subject._rounding_assessment(
            result_role="INTERBANK",
            printed=printed,
            component=component,
            component_roles=_ROUNDING_COMPONENT_ROLES,
        )
        is None
    )
    for cell in component_cells:
        cell["classification"] = "SIGNED_NUMBER"
    printed[subject._PRINTED_SOURCE_CELLS_KEY][0][0]["classification"] = disallowed_classification
    assert (
        subject._rounding_assessment(
            result_role="INTERBANK",
            printed=printed,
            component=component,
            component_roles=_ROUNDING_COMPONENT_ROLES,
        )
        is None
    )


def test_v4_authenticated_dash_zero_is_exact_zero_but_does_not_enlarge_rounding_bound() -> None:
    component_cells = [
        {
            "classification": "SIGNED_NUMBER" if ordinal < 4 else "DASH_ZERO",
            "number": {
                "coefficient": 10 if ordinal < 4 else 0,
                "percentage_mark_present": False,
                "scale": 0,
            },
            "source_sample_id": f"component-{ordinal}",
        }
        for ordinal in range(6)
    ]
    component = {
        subject._PRINTED_SOURCE_CELLS_KEY: [component_cells],
        "values": [
            {
                "column_ordinal": 0,
                "number": {
                    "coefficient": 40,
                    "percentage_mark_present": False,
                    "scale": 0,
                },
                "source_sample_ids": [cell["source_sample_id"] for cell in component_cells],
            }
        ],
    }
    printed = {
        subject._PRINTED_SOURCE_CELLS_KEY: [
            [
                {
                    "classification": "SIGNED_NUMBER",
                    "number": {
                        "coefficient": 43,
                        "percentage_mark_present": False,
                        "scale": 0,
                    },
                    "source_sample_id": "printed-result",
                }
            ]
        ],
        "source": {
            "kind": "ROLE_ROW",
            "record": {
                "label_match": {"occurrence_id": "printed-result-occurrence"},
                "role": "EXPLICIT_FAMILY_TOTAL",
            },
        },
        "values": [
            {
                "column_ordinal": 0,
                "number": {
                    "coefficient": 43,
                    "percentage_mark_present": False,
                    "scale": 0,
                },
                "source_sample_ids": ["printed-result"],
            }
        ],
    }

    assessment = subject._rounding_assessment(
        result_role="INTERBANK",
        printed=printed,
        component=component,
        component_roles=_ROUNDING_COMPONENT_ROLES,
    )
    assert assessment is not None
    lane = assessment["lanes"][0]
    assert lane["independently_printed_component_count"] == 4
    assert lane["bound_component_count_plus_one"] == 5
    assert lane["twice_absolute_residual"] == 6
    assert assessment["status"] == "ROUNDING_BOUND_EXCEEDED_AT_LEAST_ONE_LANE"

    for cell in component_cells:
        cell["classification"] = "DASH_ZERO"
        cell["number"]["coefficient"] = 0
    component["values"][0]["number"]["coefficient"] = 0
    assert (
        subject._rounding_assessment(
            result_role="INTERBANK",
            printed=printed,
            component=component,
            component_roles=_ROUNDING_COMPONENT_ROLES,
        )
        is None
    )


@pytest.mark.parametrize(
    "candidate_token",
    ["1.000,000", "1.000.000 0UNG"],
)
def test_v4_candidate_numeric_classifications_cannot_resolve_by_rounding(
    candidate_token: str,
) -> None:
    component_values = [candidate_token, "20", "30", "40", "50", "60"]
    pages = _pages(
        [
            (label, value, value)
            for label, value in zip(_ROUNDING_COMPONENT_LABELS, component_values, strict=True)
        ],
        trailing=[("1.000.202", "1.000.202")],
    )

    _axis_value, closure = _closure(
        pages,
        topology=_rounding_topology(),
        hierarchy=_rounding_hierarchy(),
    )

    root = closure["equations"]["global"][0]
    assert root["rounding_evidence"] == []
    assert root["status"] == "TRAILING_NUMERIC_CHALLENGER_VETO"
    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"


def test_v1_does_not_enable_v4_rounding_corroboration() -> None:
    component_values = ["10", "20", "30", "40", "50", "60"]
    pages = _pages(
        [
            (label, value, value)
            for label, value in zip(_ROUNDING_COMPONENT_LABELS, component_values, strict=True)
        ],
        trailing=[("210", "212")],
    )

    _axis_value, closure = _closure(
        pages,
        topology=_rounding_topology(),
        hierarchy=_rounding_hierarchy(v2=False),
    )

    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    root = closure["equations"]["global"][0]
    assert root["status"] == "TRAILING_NUMERIC_CHALLENGER_VETO"
    assert "rounding_evidence" not in root


def test_v4_exact_equality_has_precedence_over_rounding_path() -> None:
    pages = _pages(
        [
            (label, value, value)
            for label, value in zip(
                _ROUNDING_COMPONENT_LABELS,
                ["10", "20", "30", "40", "50", "60"],
                strict=True,
            )
        ],
        trailing=[("210", "210")],
    )

    _axis_value, closure = _closure(
        pages,
        topology=_rounding_topology(),
        hierarchy=_rounding_hierarchy(),
    )

    root = closure["equations"]["global"][0]
    assert root["status"] == "VISIBLE_TRAILING_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS"
    assert root["rounding_evidence"] == []
    resolved = next(item for item in closure["resolved_roles"] if item["role"] == "INTERBANK")
    assert resolved["resolution_kind"] == "VISIBLE_TRAILING_TOTAL_CORROBORATED_BY_COMPONENTS"
    receipt = next(
        item for item in closure["coverage_receipt"] if item["row_kind"] == "TRAILING_VALUE_ROW"
    )
    assert receipt["disposition"] == "SELECTED_VISIBLE_TRAILING_ROOT_SOURCE"


def test_v4_global_visible_labeled_result_uses_rounding_receipt_without_backsolve() -> None:
    rows = [
        (label, value, value)
        for label, value in zip(
            _ROUNDING_COMPONENT_LABELS,
            ["10", "20", "30", "40", "50", "60"],
            strict=True,
        )
    ]
    rows.append(("Tổng cộng", "212", "212"))

    _axis_value, closure = _closure(
        _pages(rows),
        topology=_rounding_topology(),
        hierarchy=_rounding_hierarchy(),
    )

    root = closure["equations"]["global"][0]
    assert root["status"] == "VISIBLE_RESULT_ROUNDING_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS"
    resolved = next(item for item in closure["resolved_roles"] if item["role"] == "INTERBANK")
    assert resolved["resolution_kind"] == "VISIBLE_SOURCE_ROLE_ROUNDING_CORROBORATED_BY_COMPONENTS"
    assert [value["number"]["coefficient"] for value in resolved["values"]] == [212, 212]

    attacked = copy.deepcopy(closure)
    attacked_root = attacked["equations"]["global"][0]
    attacked_root["status"] = "VISIBLE_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS"
    attacked_root["rounding_evidence"] = []
    attacked_resolved = next(
        item for item in attacked["resolved_roles"] if item["role"] == "INTERBANK"
    )
    attacked_resolved["resolution_kind"] = "VISIBLE_SOURCE_ROLE_CORROBORATED_BY_COMPONENTS"
    _coherently_rehash_closure(attacked)
    with pytest.raises(
        subject.AccountingScopedHierarchicalTableClosureV2Error,
        match="resolved arithmetic authority",
    ):
        subject._validate_result(attacked)

    attacked = copy.deepcopy(closure)
    attacked["equations"]["global"][0]["status"] = "VISIBLE_RESULT_MISMATCH_VETO"
    _coherently_rehash_closure(attacked)
    with pytest.raises(
        subject.AccountingScopedHierarchicalTableClosureV2Error,
        match="failure status retained selected",
    ):
        subject._validate_result(attacked)

    attacked = copy.deepcopy(closure)
    attacked_root = attacked["equations"]["global"][0]
    printed_owner = attacked_root["rounding_evidence"][0]["printed_result_owner"]
    printed_owner["occurrence_id"] = next(
        record["owner_id"]
        for record in attacked["numeric_sample_universe"]
        if record["owner_kind"] == "ROLE_OCCURRENCE"
        and record["owner_id"] != printed_owner["occurrence_id"]
    )
    _coherently_rehash_closure(attacked)
    with pytest.raises(
        subject.AccountingScopedHierarchicalTableClosureV2Error,
        match="rounding printed result owner receipt",
    ):
        subject._validate_result(attacked)


def test_v4_multiple_rounding_trailing_candidates_remain_ambiguous_and_veto() -> None:
    component_values = ["10", "20", "30", "40", "50", "60"]
    pages = _pages(
        [
            (label, value, value)
            for label, value in zip(_ROUNDING_COMPONENT_LABELS, component_values, strict=True)
        ],
        trailing=[("212", "212"), ("211", "211")],
    )

    _axis_value, closure = _closure(
        pages,
        topology=_rounding_topology(),
        hierarchy=_rounding_hierarchy(),
    )

    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    root = closure["equations"]["global"][0]
    assert root["status"] == "TRAILING_NUMERIC_CHALLENGER_VETO"
    assert root["selected_trailing_candidate_ordinal"] is None
    assert len(root["rounding_evidence"]) == 2


def test_v4_local_subtotal_uses_same_integer_rounding_bound() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "51", "41"),
            ("Bằng VND", "30", "25"),
            ("Bằng ngoại tệ", "20", "15"),
            ("Tổng cộng", "151", "131"),
        ]
    )

    _axis_value, closure = _closure(pages, hierarchy=_hierarchy_v2())

    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    local = next(
        equation
        for equation in closure["equations"]["local"]
        if equation["result_role"] == "LOAN_GROUP"
    )
    assert local["status"] == (
        "LOCAL_VISIBLE_SUBTOTAL_ROUNDING_CORROBORATED_BY_EXHAUSTIVE_SCOPED_COMPONENTS"
    )
    assert [lane["twice_absolute_residual"] for lane in local["rounding_evidence"][0]["lanes"]] == [
        2,
        2,
    ]

    attacked = copy.deepcopy(closure)
    attacked_local = next(
        equation
        for equation in attacked["equations"]["local"]
        if equation["result_role"] == "LOAN_GROUP"
    )
    attacked_local["status"] = "LOCAL_VISIBLE_SUBTOTAL_CORROBORATED_BY_EXACT_SCOPED_COMPONENTS"
    attacked_local["rounding_evidence"] = []
    _coherently_rehash_closure(attacked)
    with pytest.raises(
        subject.AccountingScopedHierarchicalTableClosureV2Error,
        match="local equation status",
    ):
        subject._validate_result(attacked)


def test_v4_rounding_receipt_cannot_be_forged_with_a_coherent_closure_rehash() -> None:
    component_values = ["10", "20", "30", "40", "50", "60"]
    pages = _pages(
        [
            (label, value, value)
            for label, value in zip(_ROUNDING_COMPONENT_LABELS, component_values, strict=True)
        ],
        trailing=[("210", "213")],
    )
    _axis_value, closure = _closure(
        pages,
        topology=_rounding_topology(),
        hierarchy=_rounding_hierarchy(),
    )
    attacked = copy.deepcopy(closure)
    lane = attacked["equations"]["global"][0]["rounding_evidence"][0]["lanes"][1]
    lane["bound_component_count_plus_one"] = 8
    _coherently_rehash_closure(attacked)

    with pytest.raises(
        subject.AccountingScopedHierarchicalTableClosureV2Error,
        match="integer rounding lane",
    ):
        subject._validate_result(attacked)


@pytest.mark.parametrize(
    ("component_values", "printed"),
    [
        (["1.2", "1.8", "10", "20", "30", "40"], "104"),
        (["-1", "0", "0", "0", "0", "0"], "1"),
    ],
)
def test_v4_rounding_rejects_decimal_precision_and_opposite_nonzero_sign(
    component_values: list[str], printed: str
) -> None:
    pages = _pages(
        [
            (label, value, value)
            for label, value in zip(_ROUNDING_COMPONENT_LABELS, component_values, strict=True)
        ],
        trailing=[(printed, printed)],
    )

    _axis_value, closure = _closure(
        pages,
        topology=_rounding_topology(),
        hierarchy=_rounding_hierarchy(),
    )

    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    root = closure["equations"]["global"][0]
    assert root["status"] == "TRAILING_NUMERIC_CHALLENGER_VETO"
    assert root["rounding_evidence"] == []


def test_v4_rounding_validator_cross_binds_cells_count_and_arithmetic_to_numeric_universe() -> None:
    pages = _pages(
        [
            (label, value, value)
            for label, value in zip(
                _ROUNDING_COMPONENT_LABELS,
                ["10", "20", "30", "40", "50", "60"],
                strict=True,
            )
        ],
        trailing=[("210", "213")],
    )
    _axis_value, closure = _closure(
        pages,
        topology=_rounding_topology(),
        hierarchy=_rounding_hierarchy(),
    )

    correlated = copy.deepcopy(closure)
    residual_lane = correlated["equations"]["global"][0]["residual_evidence"][0]["lanes"][1]
    rounding_lane = correlated["equations"]["global"][0]["rounding_evidence"][0]["lanes"][1]
    residual_lane["component_sum_number"]["coefficient"] = 212
    residual_lane["residual_number"]["coefficient"] = 1
    rounding_lane["printed_component_cells"][0]["number"]["coefficient"] = 12
    rounding_lane["residual_number"]["coefficient"] = 1
    rounding_lane["twice_absolute_residual"] = 2
    _coherently_rehash_closure(correlated)
    with pytest.raises(
        subject.AccountingScopedHierarchicalTableClosureV2Error,
        match="numeric universe sample",
    ):
        subject._validate_result(correlated)

    padded = copy.deepcopy(closure)
    residual_lane = padded["equations"]["global"][0]["residual_evidence"][0]["lanes"][1]
    rounding_lane = padded["equations"]["global"][0]["rounding_evidence"][0]["lanes"][1]
    residual_lane["component_source_sample_ids"].append("forged-padding-sample")
    rounding_lane["printed_component_cells"].append(
        {
            "number": {
                "coefficient": 0,
                "percentage_mark_present": False,
                "scale": 0,
            },
            "source_sample_id": "forged-padding-sample",
        }
    )
    rounding_lane["independently_printed_component_count"] = 7
    rounding_lane["bound_component_count_plus_one"] = 8
    _coherently_rehash_closure(padded)
    with pytest.raises(
        subject.AccountingScopedHierarchicalTableClosureV2Error,
        match="selected source roles|integer rounding lane",
    ):
        subject._validate_result(padded)

    boolean = copy.deepcopy(closure)
    boolean["equations"]["global"][0]["rounding_evidence"][0]["lanes"][0][
        "twice_absolute_residual"
    ] = False
    _coherently_rehash_closure(boolean)
    with pytest.raises(
        subject.AccountingScopedHierarchicalTableClosureV2Error,
        match="integer rounding lane",
    ):
        subject._validate_result(boolean)


@pytest.mark.parametrize(
    ("trailing", "expected_disposition"),
    [
        (
            [("150", "130"), ("150", "130")],
            "UNRESOLVED_UNSELECTED_COMPLETE_TRAILING_NUMERIC_CHALLENGER",
        ),
        (
            [(None, "21")],
            "UNRESOLVED_PARTIAL_TRAILING_NUMERIC_CHALLENGER",
        ),
    ],
)
def test_duplicate_total_and_numeric_page_footer_are_typed_trailing_challengers(
    trailing: list[tuple[str | None, str | None]], expected_disposition: str
) -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
        ],
        trailing=trailing,
    )
    _axis_value, closure = _closure(pages)

    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    trailing_receipts = [
        item for item in closure["coverage_receipt"] if item["row_kind"] == "TRAILING_VALUE_ROW"
    ]
    assert trailing_receipts
    assert {item["disposition"] for item in trailing_receipts} == {expected_disposition}


def test_closure_coherent_rehash_tamper_is_rejected_by_exact_replay() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
            ("Tổng cộng", "150", "130"),
        ]
    )
    axis, closure = _closure(pages)
    attacked = copy.deepcopy(closure)
    attacked["unresolved_reasons"] = ["FORGED_REASON"]
    attacked["status"] = "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    attacked["metrics"]["accounting_veto_count"] = 1
    material = copy.deepcopy(attacked)
    material.pop("closure_id")
    attacked["closure_id"] = "ashtcv2:closure:" + canonical_json_sha256_v1(material)

    with pytest.raises(
        subject.AccountingScopedHierarchicalTableClosureV2Error, match="replay exactly"
    ):
        subject.validate_accounting_scoped_hierarchical_table_closure_replay_v2(
            attacked, axis, _topology(), _hierarchy()
        )


def test_scoped_closure_contract_maps_through_existing_schema_mapper_without_adapter() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
            ("Bằng VND", "30", "25"),
            ("Bằng ngoại tệ", "20", "15"),
            ("Dự phòng cho vay TCTD khác", "-5", "-4"),
            ("Tổng cộng", "145", "126"),
        ]
    )
    axis, closure = _closure(pages)
    nodes, _schema_ref = mapping_v1._schema_graph(Path(__file__).resolve().parents[2])
    report_norm_ids = {
        "DEPOSIT_GROUP": 576,
        "LOAN_GROUP": 585,
        "LOAN_VND": 586,
        "LOAN_FOREIGN_CURRENCY": 588,
        "LOAN_PROVISION": 590,
    }
    binding = {
        "family_id": "INTERBANK",
        "family_report_norm_id": 575,
        "format_version": mapping_v1.SPEC_FORMAT_VERSION_V3,
        "ignored_roles": ["EXPLICIT_FAMILY_TOTAL"],
        "role_bindings": [
            {"report_norm_id": report_norm_id, "role": role}
            for role, report_norm_id in report_norm_ids.items()
        ],
    }
    context = {
        "period_axis": [
            {"column_ordinal": 0, "resolved_period": "31/12/2025"},
            {"column_ordinal": 1, "resolved_period": "31/12/2024"},
        ],
        "period_semantics": "BALANCE_COMPARATIVE",
        "status": "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY",
        "unit_axis": [
            {
                "column_ordinal": 0,
                "currency": "VND",
                "magnitude_power10": 6,
                "unit_kind": "MONEY",
            },
            {
                "column_ordinal": 1,
                "currency": "VND",
                "magnitude_power10": 6,
                "unit_kind": "MONEY",
            },
        ],
    }
    trial = {
        "additive_closure": closure,
        "column_context": context,
        "document_ordinal": 1,
        "evidence_status": "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY",
        "private_provenance": {"scope": "CONSOLIDATED"},
        "row_axis": axis["row_axis"],
        "source_pdf_ref": {"path": "fixture/source.pdf", "sha256": "1" * 64, "size_bytes": 1},
        "unresolved_reasons": [],
    }

    result = mapping_v1._trial(
        trial,
        nodes[575],
        {role: nodes[report_norm_id] for role, report_norm_id in report_norm_ids.items()},
        [],
        schema_period_type="SNAPSHOT",
        schema_binding_spec=binding,
    )

    assert result["mapping_status"] == "VERIFIED_BY_CODEX"
    assert [item["report_norm_id"] for item in result["mappings"]] == [
        575,
        576,
        585,
        586,
        588,
        590,
    ]
