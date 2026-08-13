from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from hashlib import sha256

import pytest
from test_source_structure_evidence_projection_v2 import _synthetic_ocr_pair

from bctc_ai.source_structure import local_accounting_graph_v1 as lag
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from bctc_ai.source_structure.evidence_projection_v2 import project_authenticated_page_v2


def _digest(label: str) -> str:
    return sha256(label.encode()).hexdigest()


def _atom_id(label: str) -> str:
    return f"ssv1:word:{_digest(label)}"


class EvidenceBuilder:
    def __init__(self) -> None:
        self.atoms: list[dict] = []
        self.y = 1_000

    def span(
        self,
        text: str,
        *,
        x: int = 1_000,
        y: int | None = None,
        advance: bool = True,
    ) -> dict:
        atom_id = _atom_id(f"{len(self.atoms)}:{text}")
        visible_y = self.y if y is None else y
        bbox = [x, visible_y, x + max(1_000, len(text) * 400), visible_y + 700]
        if advance:
            self.y = max(self.y, visible_y + 1_000)
        self.atoms.append(
            {
                "source_local_id": atom_id,
                "kind": "WORD",
                "authority": "AUTHENTICATED_PRIMARY",
                "raw_text": text,
                "canonical_bbox_mpt": bbox,
            }
        )
        return {"text": text, "canonical_bbox_mpt": bbox, "source_atom_ids": [atom_id]}

    def blank(self, *, x: int = 50_000, y: int | None = None) -> dict:
        visible_y = self.y if y is None else y
        bbox = [x, visible_y, x + 4_000, visible_y + 700]
        return {"text": None, "canonical_bbox_mpt": bbox, "source_atom_ids": []}

    def projection(self) -> dict:
        return {
            "source_local_page_id": f"ssv2:page:{_digest('page')}",
            "terminal": False,
            "coordinate_authority": {
                "pdf_rotation_degrees": 0,
                "unrotated_dimensions_mpt": [100_000, 100_000],
            },
            "neutral_page_v1": {"atoms": deepcopy(self.atoms)},
        }


@pytest.fixture(autouse=True)
def _compact_projection_validator(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        lag,
        "validate_source_evidence_projection_v2",
        lambda value: deepcopy(value),
    )


def _position(
    builder: EvidenceBuilder,
    text: str | None,
    axis_index: int,
    *,
    row_y: int | None = None,
) -> dict:
    if text is None:
        span = builder.blank(x=50_000 + axis_index * 10_000, y=row_y)
        state = "BLANK"
    else:
        span = builder.span(
            text,
            x=50_000 + axis_index * 10_000,
            y=row_y,
            advance=False,
        )
        state = (
            "DASH"
            if text in {"-", "–", "—"}
            else "OBSERVED_ZERO"
            if text.replace(".", "").replace(",", "") == "0"
            else "OBSERVED_VALUE"
        )
    return {
        "axis_index": axis_index,
        "state": state,
        "raw_text": text,
        "canonical_bbox_mpt": span["canonical_bbox_mpt"],
        "source_atom_ids": span["source_atom_ids"],
    }


def _row(
    builder: EvidenceBuilder,
    label: str | None,
    values: tuple[str | None, str | None],
) -> dict:
    row_y = builder.y
    label_span = builder.span(label) if label is not None else None
    if label is None:
        builder.y += 1_000
    return {
        "label": label_span,
        "value_positions": [
            _position(builder, value, axis_index, row_y=row_y)
            for axis_index, value in enumerate(values)
        ],
    }


def _quality_region(
    builder: EvidenceBuilder,
    *,
    owner: str = "Cho vay khách hàng",
    branch: str = "Phân tích chất lượng nợ cho vay",
    unit_labels: tuple[str, ...] = ("Đơn vị: triệu VND",),
    total_label: str | None = "Tổng cộng",
    optional_margin: bool = False,
    bad_total: bool = False,
) -> dict:
    owner_span = builder.span(owner)
    branch_span = builder.span(branch)
    axes = [
        {"header": builder.span("31/12/2025", x=50_000)},
        {"header": builder.span("31/12/2024", x=60_000)},
    ]
    units = [builder.span(text) for text in unit_labels]
    rows = [
        _row(builder, "Nợ đủ tiêu chuẩn", ("100", "90")),
        _row(builder, "Nợ cần chú ý", ("20", "15")),
        _row(builder, "Nợ dưới tiêu chuẩn", ("10", "8")),
        _row(builder, "Nợ nghi ngờ", ("5", "4")),
        _row(builder, "Nợ có khả năng mất vốn", ("3", "2")),
    ]
    if optional_margin:
        rows.append(_row(builder, "Cho vay ký quỹ", ("2", "1")))
    totals = (
        ("141" if bad_total else "140", "120")
        if optional_margin
        else (
            "139" if bad_total else "138",
            "119",
        )
    )
    rows.append(_row(builder, total_label, totals))
    boxes = [
        owner_span["canonical_bbox_mpt"],
        branch_span["canonical_bbox_mpt"],
        *(item["header"]["canonical_bbox_mpt"] for item in axes),
        *(item["canonical_bbox_mpt"] for item in units),
        *(position["canonical_bbox_mpt"] for row in rows for position in row["value_positions"]),
        *(row["label"]["canonical_bbox_mpt"] for row in rows if row["label"] is not None),
    ]
    return {
        "canonical_bbox_mpt": [
            min(box[0] for box in boxes),
            min(box[1] for box in boxes),
            max(box[2] for box in boxes),
            max(box[3] for box in boxes),
        ],
        "owner_label": owner_span,
        "branch_label": branch_span,
        "rows": rows,
        "axes": axes,
        "local_unit_labels": units,
        "adjacent_row_boundaries_verified": True,
    }


def _maturity_region(
    builder: EvidenceBuilder,
    *,
    owner: str = "Cho vay khách hàng",
    branch: str = "Phân tích dư nợ theo thời gian",
) -> dict:
    owner_span = builder.span(owner)
    branch_span = builder.span(branch)
    axes = [
        {"header": builder.span("31/12/2025", x=50_000)},
        {"header": builder.span("31/12/2024", x=60_000)},
    ]
    unit = builder.span("Đơn vị: triệu VND")
    rows = [
        _row(builder, "Ngắn hạn", ("60", "50")),
        _row(builder, "Trung hạn", ("30", "25")),
        _row(builder, "Dài hạn", ("10", "5")),
        _row(builder, "Tổng cộng", ("100", "80")),
    ]
    boxes = [
        owner_span["canonical_bbox_mpt"],
        branch_span["canonical_bbox_mpt"],
        unit["canonical_bbox_mpt"],
        *(item["header"]["canonical_bbox_mpt"] for item in axes),
        *(row["label"]["canonical_bbox_mpt"] for row in rows),
        *(position["canonical_bbox_mpt"] for row in rows for position in row["value_positions"]),
    ]
    return {
        "canonical_bbox_mpt": [
            min(box[0] for box in boxes),
            min(box[1] for box in boxes),
            max(box[2] for box in boxes),
            max(box[3] for box in boxes),
        ],
        "owner_label": owner_span,
        "branch_label": branch_span,
        "rows": rows,
        "axes": axes,
        "local_unit_labels": [unit],
        "adjacent_row_boundaries_verified": True,
    }


def _observation(projection: dict, regions: list[dict]) -> dict:
    return {
        "format_version": lag.LOCAL_ACCOUNTING_OBSERVATION_FORMAT_VERSION_V1,
        "source_local_page_id": projection["source_local_page_id"],
        "source_projection_sha256": canonical_json_sha256_v1(projection),
        "regions": regions,
    }


def _infer(builder: EvidenceBuilder, regions: list[dict], spec: lag.FamilySpecV1) -> dict:
    projection = builder.projection()
    return lag.infer_local_accounting_graph_v1(projection, _observation(projection, regions), spec)


def _move_position(
    builder: EvidenceBuilder,
    position: dict,
    *,
    dx: int = 0,
    dy: int = 0,
) -> None:
    position["canonical_bbox_mpt"] = [
        position["canonical_bbox_mpt"][0] + dx,
        position["canonical_bbox_mpt"][1] + dy,
        position["canonical_bbox_mpt"][2] + dx,
        position["canonical_bbox_mpt"][3] + dy,
    ]
    if position["source_atom_ids"]:
        atom = next(
            atom
            for atom in builder.atoms
            if atom["source_local_id"] == position["source_atom_ids"][0]
        )
        atom["canonical_bbox_mpt"] = list(position["canonical_bbox_mpt"])


def _refresh_region_bbox(region: dict) -> None:
    boxes = [
        region["owner_label"]["canonical_bbox_mpt"],
        region["branch_label"]["canonical_bbox_mpt"],
        *(item["header"]["canonical_bbox_mpt"] for item in region["axes"]),
        *(item["canonical_bbox_mpt"] for item in region["local_unit_labels"]),
        *(row["label"]["canonical_bbox_mpt"] for row in region["rows"] if row["label"] is not None),
        *(
            position["canonical_bbox_mpt"]
            for row in region["rows"]
            for position in row["value_positions"]
        ),
    ]
    region["canonical_bbox_mpt"] = [
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    ]


def test_accepts_quality_and_exact_source_bound_graph() -> None:
    builder = EvidenceBuilder()
    graph = _infer(builder, [_quality_region(builder)], lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1)

    assert graph["status"] == "CORE_ACCEPTED"
    assert graph["accepted_counts"] == {
        "TABLE": 1,
        "LOGICAL_ROW": 6,
        "VALUE_POSITION": 12,
        "AXIS": 2,
        "HIERARCHY": 18,
    }
    assert graph["arithmetic_check"]["status"] == "CORROBORATED"
    assert graph["canonicalization_eligible"] is False
    assert graph["export_eligible"] is False
    assert all(node["node_id"].startswith("lagv1:node:") for node in graph["nodes"])
    assert all(edge["edge_id"].startswith("lagv1:edge:") for edge in graph["edges"])


def test_small_visible_y_jitter_and_multiline_label_band_are_accepted() -> None:
    builder = EvidenceBuilder()
    region = _quality_region(builder)
    position = region["rows"][2]["value_positions"][0]
    _move_position(builder, position, dy=120)
    label = region["rows"][2]["label"]
    label["canonical_bbox_mpt"][3] += 250
    atom = next(
        atom for atom in builder.atoms if atom["source_local_id"] == label["source_atom_ids"][0]
    )
    atom["canonical_bbox_mpt"] = list(label["canonical_bbox_mpt"])
    _refresh_region_bbox(region)
    graph = _infer(builder, [region], lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1)
    assert graph["status"] == "CORE_ACCEPTED"


@pytest.mark.parametrize("row_index", (0, 2, 5))
def test_cross_row_value_theft_is_rejected(row_index: int) -> None:
    builder = EvidenceBuilder()
    region = _quality_region(builder)
    gap = 4_000 if row_index == 0 else -4_000 if row_index == 5 else 1_000
    _move_position(builder, region["rows"][row_index]["value_positions"][0], dy=gap)
    _refresh_region_bbox(region)
    with pytest.raises(
        lag.LocalAccountingGraphContractError,
        match="outside its visible row band",
    ):
        _infer(builder, [region], lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1)


def test_swapped_axis_assignment_and_inconsistent_lane_are_rejected() -> None:
    builder = EvidenceBuilder()
    region = _quality_region(builder)
    left, right = region["rows"][0]["value_positions"]
    left["axis_index"], right["axis_index"] = right["axis_index"], left["axis_index"]
    with pytest.raises(
        lag.LocalAccountingGraphContractError,
        match="numeric value lanes are inconsistent|axis header does not corroborate",
    ):
        _infer(builder, [region], lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1)

    builder = EvidenceBuilder()
    region = _quality_region(builder)
    _move_position(builder, region["rows"][2]["value_positions"][0], dx=9_000)
    _refresh_region_bbox(region)
    with pytest.raises(
        lag.LocalAccountingGraphContractError,
        match="numeric value lanes are inconsistent|axis header does not corroborate",
    ):
        _infer(builder, [region], lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1)


def test_accepts_maturity_without_page_wide_family_merge() -> None:
    builder = EvidenceBuilder()
    quality = _quality_region(builder)
    maturity = _maturity_region(builder)
    projection = builder.projection()
    observation = _observation(projection, [quality, maturity])

    quality_graph = lag.infer_local_accounting_graph_v1(
        projection, observation, lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1
    )
    maturity_graph = lag.infer_local_accounting_graph_v1(
        projection, observation, lag.LOAN_MATURITY_BUCKETS_SPEC_V1
    )

    assert quality_graph["accepted_counts"]["TABLE"] == 1
    assert maturity_graph["accepted_counts"]["TABLE"] == 1
    assert quality_graph["accepted_counts"]["LOGICAL_ROW"] == 6
    assert maturity_graph["accepted_counts"]["LOGICAL_ROW"] == 4


@pytest.mark.parametrize(
    ("owner", "branch"),
    [
        ("Chứng khoán đầu tư", "Phân tích chất lượng nợ cho vay"),
        ("Các khoản nợ đã mua", "Phân tích chất lượng nợ cho vay"),
        ("Cho vay khách hàng", "Tỷ lệ trích lập dự phòng theo nhóm nợ"),
    ],
)
def test_quality_hard_controls_abstain(owner: str, branch: str) -> None:
    builder = EvidenceBuilder()
    graph = _infer(
        builder,
        [_quality_region(builder, owner=owner, branch=branch)],
        lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    )

    assert graph["status"] == "EXPLICIT_UNRESOLVED"
    assert graph["accepted_counts"] == {key: 0 for key in graph["accepted_counts"]}


@pytest.mark.parametrize(
    "branch",
    (
        "Dự phòng theo phân tích chất lượng nợ cho vay",
        "Không phải phân tích chất lượng nợ cho vay",
    ),
)
def test_embedded_or_negated_branch_label_abstains(branch: str) -> None:
    builder = EvidenceBuilder()
    graph = _infer(
        builder,
        [_quality_region(builder, branch=branch)],
        lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    )
    assert graph["status"] == "EXPLICIT_UNRESOLVED"
    assert "BRANCH_NOT_RESOLVED" in graph["unresolved_reasons"]


def test_liquidity_matrix_maturity_buckets_do_not_merge() -> None:
    builder = EvidenceBuilder()
    graph = _infer(
        builder,
        [_maturity_region(builder, owner="Rủi ro thanh khoản")],
        lag.LOAN_MATURITY_BUCKETS_SPEC_V1,
    )
    assert graph["status"] == "EXPLICIT_UNRESOLVED"
    assert "NO_COMPLETE_MATCH" in graph["unresolved_reasons"]


@pytest.mark.parametrize("units", [(), ("triệu VND", "nghìn VND"), ("Đơn vị tiền tệ",)])
def test_missing_multiple_or_ambiguous_local_unit_abstains(units: tuple[str, ...]) -> None:
    builder = EvidenceBuilder()
    graph = _infer(
        builder,
        [_quality_region(builder, unit_labels=units)],
        lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    )
    assert graph["status"] == "EXPLICIT_UNRESOLVED"
    assert graph["accepted_counts"]["TABLE"] == 0


@pytest.mark.parametrize(
    "unit",
    (
        "Ngân hàng VND",
        "Đơn vị: triệu USD, quy đổi VND",
        "Đồng thời trình bày VND",
        "Đơn vị: phần trăm VND",
    ),
)
def test_non_unit_or_conflicting_currency_phrases_abstain(unit: str) -> None:
    builder = EvidenceBuilder()
    graph = _infer(
        builder,
        [_quality_region(builder, unit_labels=(unit,))],
        lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    )
    assert graph["status"] == "EXPLICIT_UNRESOLVED"
    assert "AMBIGUOUS_LOCAL_VISIBLE_UNIT" in graph["unresolved_reasons"]


@pytest.mark.parametrize("unit", ("triệu VND", "triu dong", "Đơn vị tính: triệu đồng"))
def test_bounded_cross_bank_visible_unit_surfaces_are_accepted(unit: str) -> None:
    builder = EvidenceBuilder()
    graph = _infer(
        builder,
        [_quality_region(builder, unit_labels=(unit,))],
        lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    )
    assert graph["status"] == "CORE_ACCEPTED"


@pytest.mark.parametrize("period", ("31/02/2025", "31/12/2025 so sánh 2024"))
def test_impossible_or_conflicting_period_header_abstains(period: str) -> None:
    builder = EvidenceBuilder()
    region = _quality_region(builder)
    axis = region["axes"][0]["header"]
    axis["text"] = period
    atom = next(
        atom for atom in builder.atoms if atom["source_local_id"] == axis["source_atom_ids"][0]
    )
    atom["raw_text"] = period
    graph = _infer(builder, [region], lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1)
    assert graph["status"] == "EXPLICIT_UNRESOLVED"
    assert "COMPARATIVE_MONETARY_AXIS_LAYOUT_NOT_RESOLVED" in graph["unresolved_reasons"]


def test_multiple_complete_same_family_regions_fail_closed() -> None:
    builder = EvidenceBuilder()
    graph = _infer(
        builder,
        [_quality_region(builder), _quality_region(builder)],
        lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    )
    assert graph["status"] == "EXPLICIT_UNRESOLVED"
    assert graph["unresolved_reasons"] == ["MULTIPLE_COMPLETE_MATCHES"]


def test_shared_evidence_across_accepted_and_unresolved_regions_is_deduplicated() -> None:
    builder = EvidenceBuilder()
    quality = _quality_region(builder)
    maturity = _maturity_region(builder)
    maturity["owner_label"] = quality["owner_label"]
    boxes = [
        maturity["owner_label"]["canonical_bbox_mpt"],
        maturity["branch_label"]["canonical_bbox_mpt"],
        *(item["header"]["canonical_bbox_mpt"] for item in maturity["axes"]),
        *(item["canonical_bbox_mpt"] for item in maturity["local_unit_labels"]),
        *(row["label"]["canonical_bbox_mpt"] for row in maturity["rows"]),
        *(
            position["canonical_bbox_mpt"]
            for row in maturity["rows"]
            for position in row["value_positions"]
        ),
    ]
    maturity["canonical_bbox_mpt"] = [
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    ]
    graph = _infer(
        builder,
        [quality, maturity],
        lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    )
    assert graph["status"] == "CORE_ACCEPTED"
    node_ids = [node["node_id"] for node in graph["nodes"]]
    assert len(node_ids) == len(set(node_ids))
    assert sum(node["kind"] == "UNRESOLVED_REGION" for node in graph["nodes"]) == 1


def test_unlabeled_immediate_post_child_total_is_structurally_accepted() -> None:
    builder = EvidenceBuilder()
    graph = _infer(
        builder,
        [_quality_region(builder, total_label=None)],
        lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    )
    assert graph["status"] == "CORE_ACCEPTED"
    total = next(
        node
        for node in graph["nodes"]
        if node["kind"] == "LOGICAL_ROW" and node["attributes"]["row_kind"] == "TOTAL"
    )
    assert total["source_ref"]["source_atom_ids"]


def test_optional_margin_participates_in_closure_and_total_relations() -> None:
    builder = EvidenceBuilder()
    graph = _infer(
        builder,
        [_quality_region(builder, optional_margin=True)],
        lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    )
    assert graph["status"] == "CORE_ACCEPTED"
    assert graph["arithmetic_check"]["status"] == "CORROBORATED"
    assert graph["accepted_counts"]["LOGICAL_ROW"] == 7
    assert sum(edge["kind"] == "TOTAL_OF" for edge in graph["edges"]) == 6


def test_optional_margin_dash_preserves_structure_but_arithmetic_is_not_evaluable() -> None:
    builder = EvidenceBuilder()
    region = _quality_region(builder, optional_margin=True)
    by_id = {atom["source_local_id"]: atom for atom in builder.atoms}
    position = region["rows"][-2]["value_positions"][0]
    position["raw_text"] = "-"
    position["state"] = "DASH"
    by_id[position["source_atom_ids"][0]]["raw_text"] = "-"
    graph = _infer(builder, [region], lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1)
    assert graph["status"] == "CORE_ACCEPTED"
    assert graph["arithmetic_check"]["status"] == "NOT_EVALUABLE"
    assert graph["arithmetic_check"]["evaluated_axis_indexes"] == [1]


def test_arithmetic_only_vetoes_and_never_selects_structure() -> None:
    builder = EvidenceBuilder()
    graph = _infer(
        builder,
        [_quality_region(builder, bad_total=True)],
        lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    )
    assert graph["status"] == "EXPLICIT_UNRESOLVED"
    assert graph["arithmetic_check"]["status"] == "VETOED"
    assert "ARITHMETIC_CLOSURE_VETO" in graph["unresolved_reasons"]


def test_locale_ambiguous_single_separator_token_cannot_be_observed_value() -> None:
    builder = EvidenceBuilder()
    region = _quality_region(builder)
    by_id = {atom["source_local_id"]: atom for atom in builder.atoms}
    position = region["rows"][0]["value_positions"][0]
    position["raw_text"] = "1.234"
    by_id[position["source_atom_ids"][0]]["raw_text"] = "1.234"
    with pytest.raises(
        lag.LocalAccountingGraphContractError,
        match="OBSERVED_VALUE must retain an observed non-zero number",
    ):
        _infer(builder, [region], lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1)


def test_dash_blank_and_zero_remain_distinct_and_blank_abstains() -> None:
    builder = EvidenceBuilder()
    region = _quality_region(builder)
    by_id = {atom["source_local_id"]: atom for atom in builder.atoms}
    zero = region["rows"][0]["value_positions"][0]
    zero["raw_text"] = "0"
    zero["state"] = "OBSERVED_ZERO"
    by_id[zero["source_atom_ids"][0]]["raw_text"] = "0"
    dash = region["rows"][1]["value_positions"][0]
    dash["raw_text"] = "-"
    dash["state"] = "DASH"
    by_id[dash["source_atom_ids"][0]]["raw_text"] = "-"
    blank = region["rows"][2]["value_positions"][0]
    blank["raw_text"] = None
    blank["state"] = "BLANK"
    blank["source_atom_ids"] = []
    graph = _infer(builder, [region], lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1)
    states = {
        node["attributes"].get("value_state")
        for node in graph["nodes"]
        if node["kind"] == "EVIDENCE"
    }
    assert {"OBSERVED_ZERO", "DASH", "BLANK"}.issubset(states)
    assert graph["status"] == "EXPLICIT_UNRESOLVED"


@pytest.mark.parametrize("tamper", ["atom", "text", "bbox", "projection_hash"])
def test_forged_source_evidence_is_rejected(tamper: str) -> None:
    builder = EvidenceBuilder()
    region = _quality_region(builder)
    projection = builder.projection()
    observation = _observation(projection, [region])
    if tamper == "atom":
        region["owner_label"]["source_atom_ids"] = [_atom_id("invented")]
    elif tamper == "text":
        region["owner_label"]["text"] = "Cho vay khách hàng sửa giả"
    elif tamper == "bbox":
        region["owner_label"]["canonical_bbox_mpt"][2] += 1
    else:
        observation["source_projection_sha256"] = _digest("forged projection")

    with pytest.raises(lag.LocalAccountingGraphContractError):
        lag.infer_local_accounting_graph_v1(
            projection, observation, lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1
        )


def test_long_spanning_headers_only_corroborate_value_derived_lanes() -> None:
    builder = EvidenceBuilder()
    region = _quality_region(builder)
    for axis in region["axes"]:
        header = axis["header"]
        header["canonical_bbox_mpt"] = [
            40_000,
            header["canonical_bbox_mpt"][1],
            75_000,
            header["canonical_bbox_mpt"][3],
        ]
        atom = next(
            item
            for item in builder.atoms
            if item["source_local_id"] == header["source_atom_ids"][0]
        )
        atom["canonical_bbox_mpt"] = list(header["canonical_bbox_mpt"])
    _refresh_region_bbox(region)
    graph = _infer(builder, [region], lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1)
    assert graph["status"] == "CORE_ACCEPTED"


def test_rotation_aware_geometry_accepts_display_order_at_270_degrees() -> None:
    builder = EvidenceBuilder()
    region = _quality_region(builder)
    width = 100_000

    def inverse_270(box: list[int]) -> list[int]:
        return [width - box[3], box[0], width - box[1], box[2]]

    for atom in builder.atoms:
        atom["canonical_bbox_mpt"] = inverse_270(atom["canonical_bbox_mpt"])
    for span in (
        region["owner_label"],
        region["branch_label"],
        *(axis["header"] for axis in region["axes"]),
        *region["local_unit_labels"],
        *(row["label"] for row in region["rows"] if row["label"] is not None),
        *(position for row in region["rows"] for position in row["value_positions"]),
    ):
        span["canonical_bbox_mpt"] = inverse_270(span["canonical_bbox_mpt"])
    _refresh_region_bbox(region)
    projection = builder.projection()
    projection["coordinate_authority"]["pdf_rotation_degrees"] = 270
    graph = lag.infer_local_accounting_graph_v1(
        projection,
        _observation(projection, [region]),
        lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    )
    assert graph["status"] == "CORE_ACCEPTED"


def test_diagnostic_role_and_schema_metadata_cannot_change_identity() -> None:
    builder = EvidenceBuilder()
    region = _quality_region(builder)
    projection = builder.projection()
    observation = _observation(projection, [region])
    baseline = lag.infer_local_accounting_graph_v1(
        projection, observation, lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1
    )
    annotated = lag.infer_local_accounting_graph_v1(
        projection,
        observation,
        lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
        diagnostic_metadata={
            "bank": "ignored",
            "filename": "ignored.pdf",
            "page": 31,
            "note": "10",
            "role_a": "ignored",
            "schema": "ignored",
        },
    )
    assert annotated == baseline


def test_mutated_same_id_family_spec_is_rejected() -> None:
    builder = EvidenceBuilder()
    region = _quality_region(builder)
    mutated = replace(
        lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
        branch_aliases=(
            *lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1.branch_aliases,
            "arbitrary alias",
        ),
    )
    with pytest.raises(
        lag.LocalAccountingGraphContractError,
        match="not an exact frozen LAG v1 configuration",
    ):
        _infer(builder, [region], mutated)


def test_validator_rejects_content_identity_tamper() -> None:
    builder = EvidenceBuilder()
    graph = _infer(builder, [_quality_region(builder)], lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1)
    graph["nodes"][0]["attributes"]["raw_text"] = "tampered"
    with pytest.raises(lag.LocalAccountingGraphContractError):
        lag.validate_local_accounting_graph_v1(graph)


def test_region_bbox_expansion_and_row_reordering_are_rejected() -> None:
    builder = EvidenceBuilder()
    region = _quality_region(builder)
    projection = builder.projection()
    expanded = deepcopy(region)
    expanded["canonical_bbox_mpt"][2] += 1
    with pytest.raises(lag.LocalAccountingGraphContractError):
        lag.infer_local_accounting_graph_v1(
            projection,
            _observation(projection, [expanded]),
            lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
        )

    reordered = deepcopy(region)
    reordered["rows"][0], reordered["rows"][1] = (
        reordered["rows"][1],
        reordered["rows"][0],
    )
    with pytest.raises(lag.LocalAccountingGraphContractError):
        lag.infer_local_accounting_graph_v1(
            projection,
            _observation(projection, [reordered]),
            lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
        )


def test_unlabeled_total_requires_exact_verified_adjacency() -> None:
    builder = EvidenceBuilder()
    region = _quality_region(builder, total_label=None)
    region["adjacent_row_boundaries_verified"] = False
    graph = _infer(builder, [region], lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1)
    assert graph["status"] == "EXPLICIT_UNRESOLVED"
    assert "TOTAL_NOT_RESOLVED" in graph["unresolved_reasons"]


def test_unlabeled_total_abstains_when_an_uncited_source_atom_intervenes() -> None:
    builder = EvidenceBuilder()
    region = _quality_region(builder, total_label=None)
    previous_id = region["rows"][-2]["value_positions"][-1]["source_atom_ids"][0]
    total_id = region["rows"][-1]["value_positions"][0]["source_atom_ids"][0]
    previous_index = next(
        index for index, atom in enumerate(builder.atoms) if atom["source_local_id"] == previous_id
    )
    total_atom = next(atom for atom in builder.atoms if atom["source_local_id"] == total_id)
    previous_atom = builder.atoms[previous_index]
    intervening = {
        "source_local_id": _atom_id("uncited intervening source row"),
        "kind": "WORD",
        "authority": "AUTHENTICATED_PRIMARY",
        "raw_text": "Khác",
        "canonical_bbox_mpt": [
            2_000,
            previous_atom["canonical_bbox_mpt"][3] + 1,
            4_000,
            total_atom["canonical_bbox_mpt"][1] - 1,
        ],
    }
    builder.atoms.insert(previous_index + 1, intervening)
    graph = _infer(builder, [region], lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1)
    assert graph["status"] == "EXPLICIT_UNRESOLVED"
    assert "TOTAL_NOT_RESOLVED" in graph["unresolved_reasons"]


def test_multi_atom_span_requires_source_order_exact_text_and_union_bbox() -> None:
    builder = EvidenceBuilder()
    region = _quality_region(builder)
    extra = builder.span("hàng")
    owner = region["owner_label"]
    owner_atom = next(
        atom for atom in builder.atoms if atom["source_local_id"] == owner["source_atom_ids"][0]
    )
    owner_atom["raw_text"] = "Cho vay khách"
    owner["text"] = "Cho vay khách hàng"
    owner["source_atom_ids"].append(extra["source_atom_ids"][0])
    owner["canonical_bbox_mpt"] = [
        min(owner["canonical_bbox_mpt"][0], extra["canonical_bbox_mpt"][0]),
        min(owner["canonical_bbox_mpt"][1], extra["canonical_bbox_mpt"][1]),
        max(owner["canonical_bbox_mpt"][2], extra["canonical_bbox_mpt"][2]),
        max(owner["canonical_bbox_mpt"][3], extra["canonical_bbox_mpt"][3]),
    ]
    projection = builder.projection()
    with pytest.raises(lag.LocalAccountingGraphContractError):
        lag.infer_local_accounting_graph_v1(
            projection,
            _observation(projection, [region]),
            lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
        )


def test_contiguous_multi_atom_span_is_exact_and_cherry_pick_is_rejected() -> None:
    builder = EvidenceBuilder()
    region = _quality_region(builder)
    owner = region["owner_label"]
    original = builder.atoms[0]
    original_box = original["canonical_bbox_mpt"]
    original["raw_text"] = "Cho"
    original["canonical_bbox_mpt"] = [
        original_box[0],
        original_box[1],
        original_box[0] + 2_000,
        original_box[3],
    ]
    continuation = {
        "source_local_id": _atom_id("owner continuation"),
        "kind": "WORD",
        "authority": "AUTHENTICATED_PRIMARY",
        "raw_text": "vay khách hàng",
        "canonical_bbox_mpt": [
            original["canonical_bbox_mpt"][2],
            original_box[1],
            original_box[2],
            original_box[3],
        ],
    }
    builder.atoms.insert(1, continuation)
    owner["source_atom_ids"].append(continuation["source_local_id"])
    graph = _infer(builder, [region], lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1)
    assert graph["status"] == "CORE_ACCEPTED"

    unrelated = {
        "source_local_id": _atom_id("cherry-picked intervening atom"),
        "kind": "WORD",
        "authority": "AUTHENTICATED_PRIMARY",
        "raw_text": "không thuộc span",
        "canonical_bbox_mpt": [
            original["canonical_bbox_mpt"][2] - 100,
            original_box[1],
            original["canonical_bbox_mpt"][2],
            original_box[3],
        ],
    }
    builder.atoms.insert(1, unrelated)
    projection = builder.projection()
    with pytest.raises(
        lag.LocalAccountingGraphContractError,
        match="cherry-picks noncontiguous source atoms",
    ):
        lag.infer_local_accounting_graph_v1(
            projection,
            _observation(projection, [region]),
            lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
        )


def test_production_validator_accepts_exact_projected_v2_before_family_evaluation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.undo()
    record, result = _synthetic_ocr_pair()
    projection = project_authenticated_page_v2(page_record=record, page_result=result)
    observation = {
        "format_version": lag.LOCAL_ACCOUNTING_OBSERVATION_FORMAT_VERSION_V1,
        "source_local_page_id": projection["source_local_page_id"],
        "source_projection_sha256": canonical_json_sha256_v1(projection),
        "regions": [],
    }
    with pytest.raises(
        lag.LocalAccountingGraphContractError,
        match="at least one bounded region",
    ):
        lag.infer_local_accounting_graph_v1(
            projection,
            observation,
            lag.LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
        )
