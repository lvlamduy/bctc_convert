from __future__ import annotations

import copy
import hashlib
import io
from dataclasses import replace

import pytest
from PIL import Image, ImageDraw

from bctc_ai.evaluation import family_first_accounting_evidence_sweep_v1 as subject
from bctc_ai.evaluation import family_first_authenticated_page_region_v1 as render_v1
from bctc_ai.evaluation import family_first_semantic_index_v1 as semantic_v1
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _family_spec() -> dict[str, object]:
    return {
        "children": [
            {
                "aliases": ["Tiền mặt bằng VND"],
                "presence": "REQUIRED",
                "role": "CASH_VND",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "aliases": ["Tiền mặt bằng ngoại tệ"],
                "presence": "REQUIRED",
                "role": "CASH_FOREIGN",
                "role_kind": "ADDITIVE_CHILD",
            },
        ],
        "family_id": "CASH_PRECIOUS_METALS",
        "format_version": "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V1",
        "hard_negative_aliases": ["Rủi ro tiền tệ"],
        "limits": {
            "max_cluster_span_lines": 30,
            "max_continuation_pages": 1,
            "max_label_line_span": 2,
        },
        "parent": {
            "aliases": ["Tiền, kim loại quý và đá quý"],
            "resolution_mode": "EXPLICIT_ONLY",
            "role": "CASH_PRECIOUS_METALS",
        },
        "structural_reset_aliases": ["Tiền gửi tại Ngân hàng Nhà nước"],
    }


def _evaluation_spec() -> dict[str, object]:
    return {
        "closure_policy": "REQUIRE_EXACT_UNIQUE_VISIBLE_TRAILING_TOTAL",
        "expected_lane_unit_kinds": ["MONEY", "MONEY"],
        "family_id": "CASH_PRECIOUS_METALS",
        "format_version": "ACCOUNTING_FAMILY_EVALUATION_SPEC_V1",
        "period_semantics": "BALANCE_COMPARATIVE",
    }


def _ref(sample: int) -> dict[str, object]:
    return {
        "path": f"opaque/crop-{sample:04d}.png",
        "sha256": f"{sample:064x}",
        "size_bytes": 100 + sample,
    }


def _semantic_line(sample: int, ordinal: int, text: str, bbox: list[int]):
    return {
        "accentless_text": text.lower(),
        "crop_ref": _ref(sample),
        "format_version": semantic_v1.LINE_FORMAT_VERSION,
        "line_ordinal": ordinal,
        "mean_decoded_character_probability": 0.95,
        "processed_height": 32,
        "processed_width": 100,
        "sample_id": f"sample-{sample:09d}",
        "source_bbox_raw_pixels": bbox,
        "vietocr_text": text,
        "vietocr_text_nfc": text,
    }


def _document(ordinal: int, pages: list[list[tuple[str, list[int]]]], sample_start: int):
    sample = sample_start
    page_records = []
    for physical_page, lines in enumerate(pages, 1):
        built = []
        for line_ordinal, (text, bbox) in enumerate(lines):
            built.append(_semantic_line(sample, line_ordinal, text, bbox))
            sample += 1
        page_records.append(
            {
                "line_count": len(built),
                "lines": built,
                "physical_page": physical_page,
            }
        )
    material = {
        "document_ordinal": ordinal,
        "format_version": semantic_v1.DOCUMENT_FORMAT_VERSION,
        "line_count": sum(page["line_count"] for page in page_records),
        "page_count": len(page_records),
        "pages": page_records,
        "private_provenance": {"opaque_filing": f"filing-{ordinal:04d}"},
        "source_pdf_ref": {
            "path": f"opaque/source-{ordinal:04d}.pdf",
            "sha256": f"{ordinal + 100:064x}",
            "size_bytes": 1000 + ordinal,
        },
    }
    return {
        **material,
        "document_id": "ffsiv1:document:" + canonical_json_sha256_v1(material),
    }


def _documents():
    family_page = [
        ("Tiền, kim loại quý và đá quý", [30, 20, 430, 42]),
        ("31/12/2025", [600, 50, 700, 72]),
        ("31/12/2024", [800, 50, 900, 72]),
        ("Đơn vị: Triệu đồng", [600, 75, 900, 95]),
        ("Tiền mặt bằng VND", [50, 100, 300, 122]),
        ("100", [600, 100, 700, 122]),
        ("90", [800, 100, 900, 122]),
        ("Tiền mặt bằng ngoại tệ", [50, 150, 300, 172]),
        ("20", [600, 150, 700, 172]),
        ("10", [800, 150, 900, 172]),
        ("120", [600, 200, 700, 222]),
        ("100", [800, 200, 900, 222]),
    ]
    next_page = [
        ("31.12.2025", [600, 30, 700, 52]),
        ("31.12.2024", [800, 30, 900, 52]),
        ("Đơn vị: Triệu đồng", [600, 60, 900, 82]),
        ("Tiền gửi tại Ngân hàng Nhà nước", [30, 100, 500, 122]),
    ]
    unrelated = [("Thuyết minh tài sản khác", [30, 20, 430, 42])]
    return {
        1: _document(1, [family_page, next_page], 1),
        2: _document(2, [unrelated], 17),
    }


def _numeric_document(document):
    numeric_values = {"10", "20", "90", "100", "120"}
    lines = []
    for page in document["pages"]:
        for line in page["lines"]:
            text = line["vietocr_text"]
            lines.append(
                {
                    "crop_ref": copy.deepcopy(line["crop_ref"]),
                    "line_ordinal": line["line_ordinal"],
                    "physical_page": page["physical_page"],
                    "raw_prediction": text if text in numeric_values else "",
                    "reader_score": 0.99 if text in numeric_values else 0.1,
                    "sample_id": line["sample_id"],
                    "source_bbox_raw_pixels": copy.deepcopy(line["source_bbox_raw_pixels"]),
                }
            )
    return {
        "document_ordinal": document["document_ordinal"],
        "lines": lines,
        "private_provenance": copy.deepcopy(document["private_provenance"]),
        "source_pdf_ref": copy.deepcopy(document["source_pdf_ref"]),
    }


def _document_store_snapshot(document: dict[str, object]) -> dict[str, object]:
    numeric = _numeric_document(document)
    numeric_by_sample = {line["sample_id"]: line for line in numeric["lines"]}
    joined_pages = [
        {
            "lines": [
                {
                    "bbox": copy.deepcopy(line["source_bbox_raw_pixels"]),
                    "crop_ref": copy.deepcopy(line["crop_ref"]),
                    "line_ordinal": line["line_ordinal"],
                    "numeric_recognition": {
                        "raw_prediction": numeric_by_sample[line["sample_id"]]["raw_prediction"],
                        "reader_score": numeric_by_sample[line["sample_id"]]["reader_score"],
                    },
                    "sample_id": line["sample_id"],
                    "vietocr_text": line["vietocr_text"],
                }
                for line in page["lines"]
            ],
            "page_sequence": page["physical_page"],
            "page_width": 1000,
        }
        for page in document["pages"]
    ]
    packet = {
        "assurance": "AUDITED",
        "bank_provenance": "ACB",
        "document_evidence_root_sha256": "1" * 64,
        "document_id": document["document_id"],
        "document_ordinal": document["document_ordinal"],
        "line_count": document["line_count"],
        "packet_id": f"ffdesv1:document:{document['document_ordinal']:064x}",
        "page_count": document["page_count"],
        "period": "ANNUAL",
        "scope": "CONSOLIDATED",
        "source_pdf_ref": copy.deepcopy(document["source_pdf_ref"]),
        "year": 2025,
    }
    return {"document_packet": packet, "joined_pages": joined_pages}


def _authenticated_selected_document_store_snapshot(
    document: dict[str, object],
) -> dict[str, object]:
    legacy = _document_store_snapshot(document)
    packet = copy.deepcopy(legacy["document_packet"])
    packet_material = copy.deepcopy(packet)
    packet_material.pop("packet_id")
    packet["packet_id"] = "ffdesv1:document:" + canonical_json_sha256_v1(packet_material)
    joined_pages = copy.deepcopy(legacy["joined_pages"])
    selected_page_dimensions = [
        {
            "physical_page": page["page_sequence"],
            "pixel_height": 1_400,
            "pixel_width": page["page_width"],
            "render_sha256": hashlib.sha256(
                f"render-{document['document_ordinal']}-{page['page_sequence']}".encode()
            ).hexdigest(),
            "render_size_bytes": 100 + page["page_sequence"],
        }
        for page in joined_pages
    ]
    selection_material = {
        "document_id": packet["document_id"],
        "document_ordinal": packet["document_ordinal"],
        "joined_pages": joined_pages,
        "selected_page_dimensions": selected_page_dimensions,
    }
    material = {
        "document_packet": packet,
        "joined_pages": joined_pages,
        "manifest_id": "ffdesv1:manifest:authenticated-fixture",
        "query_selection_id": ("ffoqcv1:selection:" + canonical_json_sha256_v1(selection_material)),
        "selected_page_dimensions": selected_page_dimensions,
        "state": "AUTHENTICATED_IMMUTABLE_SQLITE_SELECTED_PAGE_EVIDENCE",
    }
    return {
        **material,
        "snapshot_id": "ffdesv1:selected:" + canonical_json_sha256_v1(material),
    }


def _render(document: int, page: int):
    stream = io.BytesIO()
    Image.new("RGB", (1000, 1400), color=(255, 255, 255)).save(stream, format="PNG")
    payload = stream.getvalue()
    material = {
        "archive_id": "ffslav1:archive:" + "1" * 64,
        "authority": copy.deepcopy(render_v1._RENDER_AUTHORITY),
        "document_ordinal": document,
        "format_version": render_v1.RENDER_FORMAT_VERSION,
        "index_id": "ffsiv1:index:" + "2" * 64,
        "physical_page": page,
        "plan_id": "ffslpv1:plan:" + "3" * 64,
        "render_ref": {
            "pixel_height": 1400,
            "pixel_width": 1000,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        },
        "state": "AUTHENTICATED_EXACT_SOURCE_PAGE_RENDER_SNAPSHOT",
    }
    return {
        **material,
        "render_id": "ffaprv1:render:" + canonical_json_sha256_v1(material),
        "render_png_bytes": payload,
    }


def _dash_region(document: int, page: int, bbox: list[int]) -> dict[str, object]:
    image = Image.new("RGB", (42, 27), "white")
    ImageDraw.Draw(image).rectangle((16, 11, 25, 15), fill="black")
    stream = io.BytesIO()
    image.save(stream, format="PNG", optimize=False, compress_level=9)
    payload = stream.getvalue()
    render = _render(document, page)
    material = {
        "authority": copy.deepcopy(render_v1._REGION_AUTHORITY),
        "document_ordinal": document,
        "format_version": render_v1.FORMAT_VERSION,
        "index_id": render["index_id"],
        "ink_localization_status": "GLYPH_COMPONENT_TIGHTENED_WITHIN_PROPOSED_CELL",
        "physical_page": page,
        "proposed_raw_pixel_bbox": list(bbox),
        "recognition_raw_pixel_bbox": list(bbox),
        "region_png_ref": {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        },
        "render_id": render["render_id"],
        "render_ref": copy.deepcopy(render["render_ref"]),
        "state": "AUTHENTICATED_RENDER_CALLER_PROPOSED_REGION_CROP",
        "white_border": [12, 8, 12, 8],
    }
    return {
        **material,
        "region_id": "ffaprv1:region:" + canonical_json_sha256_v1(material),
        "region_png_bytes": payload,
    }


def _patch_live_inputs(monkeypatch):
    documents = _documents()
    numeric = {ordinal: _numeric_document(document) for ordinal, document in documents.items()}
    render_calls = []
    monkeypatch.setattr(
        subject.semantic_v1,
        "project_authenticated_family_first_semantic_index_v1",
        lambda _cap: {
            "index_id": "ffsiv1:index:" + "2" * 64,
            "metrics": {"document_count": 2, "page_count": 3, "sample_count": 17},
        },
    )
    monkeypatch.setattr(
        subject.numeric_v3,
        "project_authenticated_family_first_ppocrv6_numeric_index_v3",
        lambda _cap: {
            "receipt_id": "ffpniv3:receipt:" + "4" * 64,
            "metrics": {"document_count": 2, "page_count": 3, "sample_count": 17},
        },
    )
    monkeypatch.setattr(
        subject.snapshot_v1,
        "read_authenticated_family_first_semantic_documents_snapshot_v1",
        lambda _cap, *, document_ordinals: tuple(
            copy.deepcopy(documents[document_ordinal]) for document_ordinal in document_ordinals
        ),
    )
    monkeypatch.setattr(
        subject.snapshot_v1,
        "validate_authenticated_family_first_semantic_documents_snapshot_v1",
        lambda _cap, _documents: None,
    )
    monkeypatch.setattr(
        subject.snapshot_v1,
        "read_authenticated_family_first_numeric_documents_snapshot_v1",
        lambda _cap, *, document_ordinals: tuple(
            copy.deepcopy(numeric[document_ordinal]) for document_ordinal in document_ordinals
        ),
    )

    def read_renders(_cap, *, selections):
        result = []
        for selection in selections:
            locator = (selection["document_ordinal"], selection["physical_page"])
            render_calls.append(locator)
            result.append(_render(*locator))
        return tuple(result)

    monkeypatch.setattr(
        subject.render_v1,
        "read_authenticated_family_first_page_renders_v1",
        read_renders,
    )
    return documents, numeric, render_calls


def test_all_documents_scan_and_only_unique_region_opens_numeric_and_render(monkeypatch) -> None:
    _documents, _numeric, render_calls = _patch_live_inputs(monkeypatch)

    result = subject.build_authenticated_family_first_accounting_evidence_sweep_v1(
        object(), object(), _family_spec(), _evaluation_spec()
    )

    assert result["metrics"] == {
        "document_count": 2,
        "evidence_ready_for_schema_review_count": 1,
        "mapping_verified_count": 0,
        "not_observed_count": 1,
        "unique_topology_document_count": 1,
        "unresolved_document_count": 0,
    }
    ready, not_observed = result["trials"]
    assert ready["evidence_status"] == "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
    assert ready["row_axis"]["status"] == "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY"
    assert ready["additive_closure"]["status"] == "CORROBORATED_EXACT_UNIQUE_TRAILING_TOTAL"
    assert ready["column_context"]["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
    assert not_observed["evidence_status"] == "NOT_OBSERVED_PROPOSAL_ONLY"
    assert not_observed["unresolved_reasons"] == []
    assert not_observed["row_axis"] is None
    assert render_calls == [(1, 1)]
    assert result["authority"]["not_observed_authority"] is False


def test_public_full_index_entry_rejects_v4_before_expensive_reads(monkeypatch) -> None:
    monkeypatch.setattr(subject.topology_v1, "_spec", lambda _value: {"family_id": "FAMILY"})
    monkeypatch.setattr(
        subject,
        "_evaluation_spec",
        lambda *_args, **_kwargs: {"format_version": subject.EVALUATION_SPEC_FORMAT_V4},
    )
    monkeypatch.setattr(
        subject.semantic_v1,
        "project_authenticated_family_first_semantic_index_v1",
        lambda *_args, **_kwargs: pytest.fail("V4 full-index path read semantic evidence"),
    )
    monkeypatch.setattr(
        subject.numeric_v3,
        "project_authenticated_family_first_ppocrv6_numeric_index_v3",
        lambda *_args, **_kwargs: pytest.fail("V4 full-index path read numeric evidence"),
    )

    with pytest.raises(
        subject.FamilyFirstAccountingEvidenceSweepV1Error,
        match="V4_REQUIRES_AUTHENTICATED_DOCUMENT_STORE_SELECTED_SNAPSHOT",
    ):
        subject.build_authenticated_family_first_accounting_evidence_sweep_v1(
            object(), object(), {}, {}
        )


def test_exact_live_replay_rejects_numeric_change(monkeypatch) -> None:
    _documents, numeric, _render_calls = _patch_live_inputs(monkeypatch)
    result = subject.build_authenticated_family_first_accounting_evidence_sweep_v1(
        object(), object(), _family_spec(), _evaluation_spec()
    )
    numeric[1]["lines"][5]["raw_prediction"] = "999"

    with pytest.raises(subject.FamilyFirstAccountingEvidenceSweepV1Error, match="replay exactly"):
        subject.validate_authenticated_family_first_accounting_evidence_sweep_replay_v1(
            result, object(), object(), _family_spec(), _evaluation_spec()
        )


def test_detector_omitted_visible_dash_is_pixel_replayed_before_closure(monkeypatch) -> None:
    _documents, numeric, _render_calls = _patch_live_inputs(monkeypatch)
    numeric[1]["lines"][8]["raw_prediction"] = ""
    numeric[1]["lines"][8]["reader_score"] = 0.1
    numeric[1]["lines"][10]["raw_prediction"] = "100"
    crop_calls = []

    def crop(snapshot, *, raw_pixel_bbox):
        crop_calls.append(
            (snapshot["document_ordinal"], snapshot["physical_page"], list(raw_pixel_bbox))
        )
        return _dash_region(snapshot["document_ordinal"], snapshot["physical_page"], raw_pixel_bbox)

    monkeypatch.setattr(
        subject.render_v1,
        "_crop_authenticated_family_first_page_render_snapshot_v1",
        crop,
    )

    result = subject.build_authenticated_family_first_accounting_evidence_sweep_v1(
        object(), object(), _family_spec(), _evaluation_spec()
    )

    trial = result["trials"][0]
    foreign = next(row for row in trial["row_axis"]["rows"] if row["role"] == "CASH_FOREIGN")
    assert trial["evidence_status"] == "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
    assert trial["additive_closure"]["status"] == ("CORROBORATED_EXACT_UNIQUE_TRAILING_TOTAL")
    assert foreign["values"][0]["parsed_token"]["classification"] == "DASH_ZERO"
    assert trial["row_axis"]["metrics"]["visible_dash_zero_count"] == 1
    assert len(crop_calls) == 1

    assert (
        subject.validate_authenticated_family_first_accounting_evidence_sweep_replay_v1(
            result,
            object(),
            object(),
            _family_spec(),
            _evaluation_spec(),
        )
        == result
    )
    tampered = copy.deepcopy(result)
    tampered["trials"][0]["row_axis"]["visible_dash_rescues"][0]["role"] = "CASH_VND"
    material = copy.deepcopy(tampered)
    material.pop("sweep_id")
    tampered["sweep_id"] = "ffaesv1:sweep:" + canonical_json_sha256_v1(material)
    with pytest.raises(
        subject.FamilyFirstAccountingEvidenceSweepV1Error,
        match="does not replay exactly",
    ):
        subject.validate_authenticated_family_first_accounting_evidence_sweep_replay_v1(
            tampered,
            object(),
            object(),
            _family_spec(),
            _evaluation_spec(),
        )


def test_inconsistent_visible_grid_skips_optional_dash_rescue_and_stays_unresolved(
    monkeypatch,
) -> None:
    _documents, numeric, _render_calls = _patch_live_inputs(monkeypatch)
    numeric[1]["lines"][8]["raw_prediction"] = ""
    numeric[1]["lines"][8]["reader_score"] = 0.1
    monkeypatch.setattr(
        subject.row_axis_v1,
        "_resolved_page_grid_inputs",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            subject.row_axis_v1.AccountingFamilyRowAxisV1Error(
                "resolved page grid lane center is absent or inconsistent"
            )
        ),
    )

    result = subject.build_authenticated_family_first_accounting_evidence_sweep_v1(
        object(), object(), _family_spec(), _evaluation_spec()
    )

    trial = result["trials"][0]
    assert trial["evidence_status"] == "UNRESOLVED_EVIDENCE_GATES"
    assert trial["row_axis"]["metrics"]["visible_dash_rescue_attempt_count"] == 0
    assert trial["unresolved_reasons"] == [
        "VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE",
        "ADDITIVE_CLOSURE:ADDITIVE_CHILD_LANES_INCOMPLETE_OR_NUMERIC_TOKEN_UNRESOLVED",
    ]


@pytest.mark.parametrize(
    ("require_unique_owner", "reverse_rows", "expected_rescue_count"),
    [(True, False, 0), (True, True, 0), (False, False, 1)],
)
def test_v4_repeated_role_page_dash_rescue_is_skipped_without_legacy_drift(
    monkeypatch,
    require_unique_owner: bool,
    reverse_rows: bool,
    expected_rescue_count: int,
) -> None:
    rows = [
        {
            "label_match": {
                "end_source_line_index": 43,
                "page_sequence": 34,
                "source_line_index": 43,
            },
            "missing_column_ordinals": [0],
            "role": "INTERBANK_LOAN_VND",
        },
        {
            "label_match": {
                "end_source_line_index": 48,
                "page_sequence": 34,
                "source_line_index": 48,
            },
            "missing_column_ordinals": [],
            "role": "INTERBANK_LOAN_VND",
        },
    ]
    if reverse_rows:
        rows.reverse()
    proposal = {
        "column_center": 600.0,
        "column_ordinal": 0,
        "raw_pixel_bbox": [550, 100, 650, 130],
    }
    proposal_calls = []
    crop_calls = []

    def proposals(*_args, **_kwargs):
        proposal_calls.append(True)
        return [proposal]

    def crop(snapshot, *, raw_pixel_bbox):
        crop_calls.append(True)
        return _dash_region(snapshot["document_ordinal"], snapshot["physical_page"], raw_pixel_bbox)

    monkeypatch.setattr(subject.row_axis_v1, "_region_lines", lambda *_args: {34: []})
    monkeypatch.setattr(
        subject.row_axis_v1,
        "_resolved_page_grid_inputs",
        lambda *_args: ([600.0], []),
    )
    monkeypatch.setattr(
        subject,
        "propose_missing_value_lane_regions_v1",
        proposals,
    )
    monkeypatch.setattr(
        subject.render_v1,
        "_crop_authenticated_family_first_page_render_snapshot_v1",
        crop,
    )

    kwargs = {"require_unique_role_page_owner": True} if require_unique_owner else {}
    rescues = subject._visible_dash_rescue_inputs(
        joined_pages=[{"lines": [], "page_sequence": 34, "page_width": 1000}],
        row_axis={
            "column_grids": [],
            "rows": rows,
            "topology_region": {"page_sequence": 34},
        },
        render_snapshots=(_render(37, 34),),
        **kwargs,
    )

    assert len(rescues) == expected_rescue_count
    assert len(proposal_calls) == expected_rescue_count
    assert len(crop_calls) == expected_rescue_count
    if rescues:
        assert (
            rescues[0]["role"],
            rescues[0]["page_sequence"],
            rescues[0]["column_ordinal"],
        ) == ("INTERBANK_LOAN_VND", 34, 0)


def test_cached_evidence_without_render_pixels_defers_dash_rescue() -> None:
    assert (
        subject._visible_dash_rescue_inputs(
            joined_pages=[],
            row_axis={"topology_region": {"cluster_start_document_line_ordinal": 0}},
            render_snapshots=(),
        )
        == ()
    )


def test_optional_closure_policy_still_vetoes_a_visible_mismatching_total(monkeypatch) -> None:
    _documents, numeric, _render_calls = _patch_live_inputs(monkeypatch)
    numeric[1]["lines"][10]["raw_prediction"] = "121"
    policy = _evaluation_spec()
    policy["closure_policy"] = "CORROBORATE_IF_VISIBLE"

    result = subject.build_authenticated_family_first_accounting_evidence_sweep_v1(
        object(), object(), _family_spec(), policy
    )

    trial = result["trials"][0]
    assert trial["evidence_status"] == "UNRESOLVED_EVIDENCE_GATES"
    assert trial["unresolved_reasons"] == [
        "VISIBLE_ADDITIVE_CLOSURE_VETO:NO_TRAILING_ROW_EQUALS_VISIBLE_COMPONENT_SUMS_ON_EVERY_LANE"
    ]


def test_one_malformed_period_axis_stays_document_local_unresolved(monkeypatch) -> None:
    _patch_live_inputs(monkeypatch)
    monkeypatch.setattr(
        subject.column_context_v1,
        "_build_accounting_family_column_context_from_authenticated_row_axis_v1",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("period axis drifted")),
    )

    result = subject.build_authenticated_family_first_accounting_evidence_sweep_v1(
        object(), object(), _family_spec(), _evaluation_spec()
    )

    assert result["metrics"]["document_count"] == 2
    assert result["metrics"]["unresolved_document_count"] == 1
    assert result["trials"][0]["evidence_status"] == "UNRESOLVED_EVIDENCE_GATES"
    assert result["trials"][0]["unresolved_reasons"] == [
        "COLUMN_CONTEXT_ERROR:ValueError:period axis drifted"
    ]
    assert result["trials"][1]["evidence_status"] == "NOT_OBSERVED_PROPOSAL_ONLY"


def _mixed_value(sample_id: str, raw: str, coefficient: int) -> dict[str, object]:
    return {
        "column_ordinal": 0,
        "parsed_token": {
            "classification": "MIXED_GROUPED_INTEGER_CANDIDATE",
            "coefficient": coefficient,
            "negative_parentheses": False,
            "normalized_token": raw,
            "percentage_mark_present": False,
            "scale": 0,
            "separator_interpretation": "MIXED_GROUPED_INTEGER_CANDIDATE",
            "sign": 1,
        },
        "sample_id": sample_id,
    }


def _signed_value(sample_id: str, coefficient: int) -> dict[str, object]:
    return {
        "column_ordinal": 0,
        "parsed_token": {
            "classification": "SIGNED_NUMBER",
            "coefficient": coefficient,
            "negative_parentheses": False,
            "normalized_token": str(coefficient),
            "percentage_mark_present": False,
            "scale": 0,
            "separator_interpretation": "NONE",
            "sign": 1,
        },
        "sample_id": sample_id,
    }


def _noise_suffix_value(sample_id: str, raw: str, coefficient: int) -> dict[str, object]:
    return {
        "column_ordinal": 0,
        "parsed_token": {
            "classification": "NOISE_SUFFIXED_GROUPED_INTEGER_CANDIDATE",
            "coefficient": coefficient,
            "negative_parentheses": False,
            "normalized_token": raw,
            "percentage_mark_present": False,
            "scale": 0,
            "separator_interpretation": "NOISE_SUFFIXED_GROUPED_INTEGER_CANDIDATE",
            "sign": 1,
        },
        "sample_id": sample_id,
    }


def test_mixed_separator_candidate_requires_independent_reader_money_peers_and_equation() -> None:
    candidate = _mixed_value("mixed", "1.460,873", 1_460_873)
    row_axis = {
        "rows": [
            {"role": "CASH_VND", "values": [candidate]},
            {"role": "CASH_FOREIGN", "values": [_signed_value("peer-1", 382_482)]},
            {"role": "MONETARY_GOLD", "values": [_signed_value("peer-2", 94)]},
        ],
        "trailing_value_rows": [{"values": [_signed_value("total", 1_843_449)]}],
    }
    column = {"unit_axis": [{"column_ordinal": 0, "unit_kind": "MONEY"}]}
    closure = {
        "format_version": "ACCOUNTING_ADDITIVE_TABLE_CLOSURE_V1",
        "status": "CORROBORATED_EXACT_UNIQUE_TRAILING_TOTAL",
        "lane_sums": [{"component_sample_ids": ["mixed", "peer-1", "peer-2"]}],
        "exact_total_candidates": [{"sample_ids": ["total"]}],
    }
    pages = [{"lines": [{"sample_id": "mixed", "vietocr_text": "1.460.873"}]}]

    assert (
        subject._mixed_separator_consensus_reasons(
            row_axis=row_axis,
            column_context=column,
            closure=closure,
            joined_pages=pages,
        )
        == []
    )

    pages[0]["lines"][0]["vietocr_text"] = "1.460.879"
    assert subject._mixed_separator_consensus_reasons(
        row_axis=row_axis,
        column_context=column,
        closure=closure,
        joined_pages=pages,
    ) == ["MIXED_SEPARATOR:INDEPENDENT_SAME_CROP_READER_DISAGREES:mixed"]


def test_mixed_separator_candidate_never_passes_from_model_vote_without_equation() -> None:
    candidate = _mixed_value("mixed", "55,307.732", 55_307_732)
    reasons = subject._mixed_separator_consensus_reasons(
        row_axis={
            "rows": [
                {"role": "DEPOSIT_VND", "values": [candidate]},
                {"role": "DEPOSIT_FOREIGN", "values": [_signed_value("peer-1", 1)]},
                {"role": "DEPOSIT_LAOS", "values": [_signed_value("peer-2", 2)]},
            ],
            "trailing_value_rows": [],
        },
        column_context={"unit_axis": [{"column_ordinal": 0, "unit_kind": "MONEY"}]},
        closure={
            "format_version": "ACCOUNTING_ADDITIVE_TABLE_CLOSURE_V1",
            "status": "UNRESOLVED_ADDITIVE_TABLE_CLOSURE",
            "lane_sums": [],
            "exact_total_candidates": [],
        },
        joined_pages=[{"lines": [{"sample_id": "mixed", "vietocr_text": "55.307.732"}]}],
    )

    assert reasons == ["MIXED_SEPARATOR:EXACT_VISIBLE_ACCOUNTING_CLOSURE_ABSENT:mixed"]


def test_scoped_closure_mixed_token_requires_exact_visible_equation_use() -> None:
    closure = {
        "coverage_receipt": [
            {
                "candidate_ordinal": None,
                "disposition": "GLOBAL_HIERARCHY_SOURCE_OCCURRENCE",
                "occurrence_id": "exact-occurrence",
                "role": "EXACT_COMPONENT",
                "row_kind": "ROLE_ROW",
                "sample_ids": ["exact-mixed"],
                "source_record": {},
            },
            {
                "candidate_ordinal": None,
                "disposition": "NONADDITIVE_VISIBLE_SOURCE_ROLE",
                "occurrence_id": "nonadditive-occurrence",
                "role": "NONADDITIVE_NOTE",
                "row_kind": "ROLE_ROW",
                "sample_ids": ["nonadditive-mixed"],
                "source_record": {},
            },
        ],
        "equations": {
            "global": [
                {
                    "component_roles_present": ["EXACT_COMPONENT"],
                    "result_role": "VISIBLE_TOTAL",
                    "status": "VISIBLE_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS",
                }
            ],
            "local": [],
        },
        "format_version": "ACCOUNTING_SCOPED_HIERARCHICAL_TABLE_CLOSURE_V2",
        "resolved_roles": [
            {
                "role": "EXACT_COMPONENT",
                "source": None,
                "values": [{"source_sample_ids": ["exact-mixed"]}],
            },
            {
                "role": "NONADDITIVE_NOTE",
                "source": None,
                "values": [{"source_sample_ids": ["nonadditive-mixed"]}],
            },
        ],
        "status": "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO",
    }

    assert subject._mixed_candidate_has_accounting_corroboration(
        role="EXACT_COMPONENT", sample_id="exact-mixed", closure=closure
    )
    assert not subject._mixed_candidate_has_accounting_corroboration(
        role="NONADDITIVE_NOTE", sample_id="nonadditive-mixed", closure=closure
    )


def test_scoped_closure_mixed_token_is_bound_to_its_exact_local_occurrence() -> None:
    closure = {
        "coverage_receipt": [
            {
                "candidate_ordinal": None,
                "disposition": "LOCAL_SUBTOTAL_RESULT_OCCURRENCE",
                "occurrence_id": occurrence,
                "role": "REPEATED_GROUP",
                "row_kind": "ROLE_ROW",
                "sample_ids": [sample],
                "source_record": {},
            }
            for occurrence, sample in (
                ("exact-owner", "exact-local"),
                ("source-owner", "source-only"),
            )
        ],
        "equations": {
            "global": [
                {
                    "component_roles_present": ["REPEATED_GROUP"],
                    "result_role": "VISIBLE_TOTAL",
                    "status": "VISIBLE_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS",
                }
            ],
            "local": [
                {
                    "component_roles_present": ["CHILD"],
                    "result_occurrence_id": "exact-owner",
                    "result_role": "REPEATED_GROUP",
                    "status": "LOCAL_VISIBLE_SUBTOTAL_CORROBORATED_BY_EXACT_SCOPED_COMPONENTS",
                },
                {
                    "component_roles_present": [],
                    "result_occurrence_id": "source-owner",
                    "result_role": "REPEATED_GROUP",
                    "status": "LOCAL_VISIBLE_SOURCE_ONLY_NO_DECLARED_COMPONENT_VISIBLE",
                },
            ],
        },
        "format_version": "ACCOUNTING_SCOPED_HIERARCHICAL_TABLE_CLOSURE_V2",
        "resolved_roles": [
            {
                "role": "REPEATED_GROUP",
                "source": None,
                "values": [{"source_sample_ids": ["exact-local", "source-only"]}],
            }
        ],
        "status": "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO",
    }

    assert subject._mixed_candidate_has_accounting_corroboration(
        role="REPEATED_GROUP", sample_id="exact-local", closure=closure
    )
    assert not subject._mixed_candidate_has_accounting_corroboration(
        role="REPEATED_GROUP", sample_id="source-only", closure=closure
    )


def test_scoped_closure_mixed_trailing_token_requires_unique_selected_exact_source() -> None:
    closure = {
        "coverage_receipt": [
            {
                "candidate_ordinal": 0,
                "disposition": "SELECTED_VISIBLE_TRAILING_ROOT_SOURCE",
                "occurrence_id": None,
                "role": None,
                "row_kind": "TRAILING_VALUE_ROW",
                "sample_ids": ["selected-total"],
                "source_record": {},
            },
            {
                "candidate_ordinal": 1,
                "disposition": "UNRESOLVED_UNSELECTED_COMPLETE_TRAILING_NUMERIC_CHALLENGER",
                "occurrence_id": None,
                "role": None,
                "row_kind": "TRAILING_VALUE_ROW",
                "sample_ids": ["footer"],
                "source_record": {},
            },
        ],
        "equations": {
            "global": [
                {
                    "component_roles_present": ["COMPONENT"],
                    "result_role": "ROOT",
                    "selected_trailing_candidate_ordinal": 0,
                    "status": "VISIBLE_TRAILING_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS",
                    "trailing_candidate_evidence": [
                        {
                            "candidate_ordinal": 0,
                            "sample_ids": ["selected-total"],
                            "status": "SELECTED_VISIBLE_TRAILING_ROOT_SOURCE",
                        }
                    ],
                }
            ],
            "local": [],
        },
        "format_version": "ACCOUNTING_SCOPED_HIERARCHICAL_TABLE_CLOSURE_V2",
        "resolved_roles": [],
        "status": "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO",
    }

    assert subject._mixed_candidate_has_accounting_corroboration(
        role=None, sample_id="selected-total", closure=closure
    )
    assert not subject._mixed_candidate_has_accounting_corroboration(
        role=None, sample_id="footer", closure=closure
    )


def test_noise_suffix_candidate_needs_shared_prefix_money_peers_and_exact_equation() -> None:
    candidate = _noise_suffix_value("stamped", "3.202.820 0UNG", 3_202_820)
    row_axis = {
        "rows": [
            {"role": "DEBT_OTHER_BANK", "values": [candidate]},
            {"role": "DEBT_GOVERNMENT", "values": [_signed_value("peer-1", 2_000_000)]},
            {"role": "DEBT_ECONOMIC", "values": [_signed_value("peer-2", 1_000_000)]},
        ],
        "trailing_value_rows": [{"values": [_signed_value("total", 6_202_820)]}],
    }
    column = {"unit_axis": [{"column_ordinal": 0, "unit_kind": "MONEY"}]}
    closure = {
        "format_version": "ACCOUNTING_ADDITIVE_TABLE_CLOSURE_V1",
        "status": "CORROBORATED_EXACT_UNIQUE_TRAILING_TOTAL",
        "lane_sums": [{"component_sample_ids": ["stamped", "peer-1", "peer-2"]}],
        "exact_total_candidates": [{"sample_ids": ["total"]}],
    }
    pages = [{"lines": [{"sample_id": "stamped", "vietocr_text": "3.202.820.000NG)"}]}]

    assert (
        subject._mixed_separator_consensus_reasons(
            row_axis=row_axis,
            column_context=column,
            closure=closure,
            joined_pages=pages,
        )
        == []
    )

    pages[0]["lines"][0]["vietocr_text"] = "3.202.829.000NG)"
    assert subject._mixed_separator_consensus_reasons(
        row_axis=row_axis,
        column_context=column,
        closure=closure,
        joined_pages=pages,
    ) == ["OCR_NOISE_SUFFIX:INDEPENDENT_SAME_CROP_READER_DISAGREES:stamped"]

    pages[0]["lines"][0]["vietocr_text"] = "3.202.820.000NG)"
    closure["status"] = "UNRESOLVED_ADDITIVE_TABLE_CLOSURE"
    closure["lane_sums"] = []
    assert subject._mixed_separator_consensus_reasons(
        row_axis=row_axis,
        column_context=column,
        closure=closure,
        joined_pages=pages,
    ) == ["OCR_NOISE_SUFFIX:EXACT_VISIBLE_ACCOUNTING_CLOSURE_ABSENT:stamped"]


def test_bounded_document_snapshot_rebuilds_only_one_existing_trial(monkeypatch) -> None:
    _patch_live_inputs(monkeypatch)
    family = _family_spec()
    policy = _evaluation_spec()
    sweep = subject.build_authenticated_family_first_accounting_evidence_sweep_v1(
        object(), object(), family, policy
    )
    baseline = copy.deepcopy(sweep["trials"][0])
    baseline["private_provenance"] = {
        "bank": "ACB",
        "period": "ANNUAL",
        "scope": "CONSOLIDATED",
        "year": 2025,
    }
    semantic = _documents()[1]
    numeric = _numeric_document(semantic)
    numeric_by_sample = {line["sample_id"]: line for line in numeric["lines"]}
    joined = [
        {
            "lines": [
                {
                    "bbox": copy.deepcopy(line["source_bbox_raw_pixels"]),
                    "crop_ref": copy.deepcopy(line["crop_ref"]),
                    "line_ordinal": line["line_ordinal"],
                    "numeric_recognition": {
                        "raw_prediction": numeric_by_sample[line["sample_id"]]["raw_prediction"],
                        "reader_score": numeric_by_sample[line["sample_id"]]["reader_score"],
                    },
                    "sample_id": line["sample_id"],
                    "vietocr_text": line["vietocr_text"],
                }
                for line in page["lines"]
            ],
            "page_sequence": page["physical_page"],
            "page_width": 1000,
        }
        for page in semantic["pages"]
    ]
    joined[1]["page_width"] = None
    packet = {
        "assurance": "AUDITED",
        "bank_provenance": "ACB",
        "document_evidence_root_sha256": "1" * 64,
        "document_id": semantic["document_id"],
        "document_ordinal": 1,
        "line_count": semantic["line_count"],
        "packet_id": "ffdesv1:document:" + "2" * 64,
        "page_count": semantic["page_count"],
        "period": "ANNUAL",
        "scope": "CONSOLIDATED",
        "source_pdf_ref": copy.deepcopy(semantic["source_pdf_ref"]),
        "year": 2025,
    }
    material = {
        "document_packet": packet,
        "joined_pages": joined,
        "manifest_id": "ffdesv1:manifest:" + "3" * 64,
        "selected_page_dimensions": [
            {
                "physical_page": 1,
                "pixel_height": 1400,
                "pixel_width": 1000,
                "render_sha256": "4" * 64,
                "render_size_bytes": 100,
            },
        ],
    }
    snapshot = {
        **material,
        "snapshot_id": "ffdesv1:snapshot:" + canonical_json_sha256_v1(material),
    }

    rebuilt = subject.rebuild_family_first_accounting_trial_from_document_snapshot_v1(
        baseline, snapshot, family, policy
    )

    assert rebuilt["document_ordinal"] == 1
    assert rebuilt["evidence_status"] == "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
    assert rebuilt["document_axis_binding"] == baseline["document_axis_binding"]
    snapshot["joined_pages"][0]["lines"][5]["numeric_recognition"]["raw_prediction"] = "999"
    with pytest.raises(
        subject.FamilyFirstAccountingEvidenceSweepV1Error,
        match="snapshot identity",
    ):
        subject.rebuild_family_first_accounting_trial_from_document_snapshot_v1(
            baseline, snapshot, family, policy
        )


def test_document_store_sweep_recomputes_each_packet_once_without_live_ocr(monkeypatch) -> None:
    documents = _documents()
    snapshots = {
        ordinal: _document_store_snapshot(document) for ordinal, document in documents.items()
    }
    topology_scans = tuple(
        subject.topology_v1.build_accounting_family_topology_scan_v1(
            subject._topology_pages_from_document_snapshot_v1(snapshot["joined_pages"]),
            _family_spec(),
        )
        for snapshot in snapshots.values()
    )
    calls = {"packet": [], "snapshot": []}
    monkeypatch.setattr(
        subject.document_store_v1,
        "project_authenticated_family_first_document_evidence_store_v1",
        lambda _cap: {
            "input_indices": {
                "numeric_axis_sha256": "3" * 64,
                "numeric_receipt_id": "ffpniv3:receipt:" + "1" * 64,
                "semantic_index_id": "ffsiv1:index:" + "2" * 64,
            },
            "metrics": {"document_count": 2},
        },
    )

    def packet(_cap, *, document_ordinal):
        calls["packet"].append(document_ordinal)
        return copy.deepcopy(snapshots[document_ordinal]["document_packet"])

    def snapshot(_cap, *, document_ordinal, selected_pages):
        calls["snapshot"].append((document_ordinal, selected_pages))
        return copy.deepcopy(snapshots[document_ordinal])

    monkeypatch.setattr(
        subject.document_store_v1,
        "read_authenticated_family_first_document_packet_v1",
        packet,
    )
    monkeypatch.setattr(
        subject.document_store_v1,
        "read_authenticated_family_first_document_evidence_snapshot_v1",
        snapshot,
    )
    monkeypatch.setattr(
        subject.document_store_v1,
        "read_authenticated_family_first_topology_scans_v1",
        lambda _cap, _family: copy.deepcopy(topology_scans),
    )
    monkeypatch.setattr(
        subject.topology_v1,
        "build_accounting_family_topology_scan_v1",
        lambda *_args, **_kwargs: pytest.fail("document-store sweep rescanned topology"),
    )
    monkeypatch.setattr(
        subject.semantic_v1,
        "project_authenticated_family_first_semantic_index_v1",
        lambda *_args, **_kwargs: pytest.fail("document-store sweep replayed semantic OCR"),
    )
    monkeypatch.setattr(
        subject.numeric_v3,
        "project_authenticated_family_first_ppocrv6_numeric_index_v3",
        lambda *_args, **_kwargs: pytest.fail("document-store sweep replayed numeric OCR"),
    )

    result = (
        subject.build_authenticated_family_first_accounting_evidence_sweep_from_document_store_v1(
            object(), _family_spec(), _evaluation_spec()
        )
    )

    assert result["metrics"] == {
        "document_count": 2,
        "evidence_ready_for_schema_review_count": 1,
        "mapping_verified_count": 0,
        "not_observed_count": 1,
        "unique_topology_document_count": 1,
        "unresolved_document_count": 0,
    }
    assert calls["packet"] == [1, 2]
    assert calls["snapshot"] == [(1, (1, 2)), (2, (1,))]


def test_document_store_v4_uses_exact_full_page_batch_snapshot_with_zero_line_page(
    monkeypatch,
) -> None:
    document = _document(
        1,
        [
            [("Thuyết minh tài sản khác", [30, 20, 430, 42])],
            [],
            [("Thuyết minh nợ phải trả khác", [30, 20, 430, 42])],
        ],
        1,
    )
    snapshot = _authenticated_selected_document_store_snapshot(document)
    calls = {"batch": []}
    monkeypatch.setattr(
        subject,
        "_evaluation_spec",
        lambda *_args, **_kwargs: {"format_version": subject.EVALUATION_SPEC_FORMAT_V4},
    )
    monkeypatch.setattr(subject, "_validate", lambda value: value)
    monkeypatch.setattr(
        subject.document_store_v1,
        "project_authenticated_family_first_document_evidence_store_v1",
        lambda _cap: {
            "input_indices": {
                "numeric_receipt_id": "ffpniv3:receipt:" + "1" * 64,
                "semantic_index_id": "ffsiv1:index:" + "2" * 64,
            },
            "metrics": {"document_count": 1},
        },
    )
    monkeypatch.setattr(
        subject.document_store_v1,
        "read_authenticated_family_first_topology_scans_v1",
        lambda *_args, **_kwargs: pytest.fail("V4 used the zero-line-dropping topology cache"),
    )
    monkeypatch.setattr(
        subject.document_store_v1,
        "read_authenticated_family_first_document_packet_v1",
        lambda *_args, **_kwargs: copy.deepcopy(snapshot["document_packet"]),
    )
    monkeypatch.setattr(
        subject.document_store_v1,
        "read_authenticated_family_first_document_evidence_snapshot_v1",
        lambda *_args, **_kwargs: pytest.fail("V4 used the legacy five-field snapshot accessor"),
    )

    def selected_pages(_cap, *, document_page_selections):
        calls["batch"].append(document_page_selections)
        return (copy.deepcopy(snapshot),)

    monkeypatch.setattr(
        subject.document_store_v1,
        "read_authenticated_family_first_documents_selected_pages_v1",
        selected_pages,
    )
    monkeypatch.setattr(
        subject.document_store_v1,
        "read_authenticated_family_first_document_page_renders_v1",
        lambda *_args, **_kwargs: pytest.fail("NOT_OBSERVED trial requested a page render"),
    )

    result = (
        subject.build_authenticated_family_first_accounting_evidence_sweep_from_document_store_v1(
            object(), _family_spec(), {}
        )
    )

    assert calls["batch"] == [((1, (1, 2, 3)),)]
    assert [page["page_sequence"] for page in snapshot["joined_pages"]] == [1, 2, 3]
    assert snapshot["joined_pages"][1]["lines"] == []
    assert result["trials"][0]["evidence_status"] == "NOT_OBSERVED_PROPOSAL_ONLY"


def test_document_store_v4_rejects_legacy_five_field_snapshot_before_topology(
    monkeypatch,
) -> None:
    document = _document(
        1,
        [[("Thuyết minh tài sản khác", [30, 20, 430, 42])], []],
        1,
    )
    selected = _authenticated_selected_document_store_snapshot(document)
    legacy_material = {
        "document_packet": copy.deepcopy(selected["document_packet"]),
        "joined_pages": copy.deepcopy(selected["joined_pages"][:1]),
        "manifest_id": selected["manifest_id"],
        "selected_page_dimensions": copy.deepcopy(selected["selected_page_dimensions"]),
    }
    legacy = {
        **legacy_material,
        "snapshot_id": "ffdesv1:snapshot:" + canonical_json_sha256_v1(legacy_material),
    }
    monkeypatch.setattr(
        subject,
        "_v4_topology_authority",
        lambda *_args, **_kwargs: pytest.fail("legacy snapshot reached V4 topology"),
    )

    with pytest.raises(
        subject.FamilyFirstAccountingEvidenceSweepV1Error,
        match="selected snapshot contract drifted",
    ):
        subject._trial_from_document_store_snapshot_v1(
            legacy,
            _family_spec(),
            {"format_version": subject.EVALUATION_SPEC_FORMAT_V4},
        )


def test_document_store_v4_rejects_selected_snapshot_from_another_packet(
    monkeypatch,
) -> None:
    document = _document(
        1,
        [[("Thuyết minh tài sản khác", [30, 20, 430, 42])]],
        1,
    )
    selected = _authenticated_selected_document_store_snapshot(document)
    other_packet = copy.deepcopy(selected["document_packet"])
    other_packet["source_pdf_ref"]["sha256"] = "f" * 64
    monkeypatch.setattr(
        subject,
        "_v4_topology_authority",
        lambda *_args, **_kwargs: pytest.fail("cross-packet snapshot reached V4 topology"),
    )

    with pytest.raises(
        subject.FamilyFirstAccountingEvidenceSweepV1Error,
        match="packet or full-page axis drifted",
    ):
        subject._trial_from_document_store_snapshot_v1(
            selected,
            _family_spec(),
            {"format_version": subject.EVALUATION_SPEC_FORMAT_V4},
            expected_packet=other_packet,
        )


def test_document_store_v4_rejects_coherently_rehashed_truncated_full_line_axis(
    monkeypatch,
) -> None:
    document = _document(
        1,
        [
            [("Thuyết minh tài sản khác", [30, 20, 430, 42])],
            [],
            [("Thuyết minh nợ phải trả khác", [30, 20, 430, 42])],
        ],
        1,
    )
    selected = _authenticated_selected_document_store_snapshot(document)
    selected["joined_pages"][2]["lines"] = []
    selection_material = {
        "document_id": selected["document_packet"]["document_id"],
        "document_ordinal": selected["document_packet"]["document_ordinal"],
        "joined_pages": selected["joined_pages"],
        "selected_page_dimensions": selected["selected_page_dimensions"],
    }
    selected["query_selection_id"] = "ffoqcv1:selection:" + canonical_json_sha256_v1(
        selection_material
    )
    snapshot_material = copy.deepcopy(selected)
    snapshot_material.pop("snapshot_id")
    selected["snapshot_id"] = "ffdesv1:selected:" + canonical_json_sha256_v1(snapshot_material)
    monkeypatch.setattr(
        subject,
        "_v4_topology_authority",
        lambda *_args, **_kwargs: pytest.fail("truncated snapshot reached V4 topology"),
    )

    with pytest.raises(
        subject.FamilyFirstAccountingEvidenceSweepV1Error,
        match="packet or full-page axis drifted",
    ):
        subject._trial_from_document_store_snapshot_v1(
            selected,
            _family_spec(),
            {"format_version": subject.EVALUATION_SPEC_FORMAT_V4},
            expected_packet=selected["document_packet"],
        )


@pytest.mark.parametrize("mutated_inner", ["CANDIDATES", "SCAN"])
def test_document_store_v4_cached_context_reopens_inner_authority_before_early_return(
    mutated_inner: str,
) -> None:
    snapshot = _authenticated_selected_document_store_snapshot(_documents()[2])
    family_spec = _family_spec()
    policy = {"format_version": subject.EVALUATION_SPEC_FORMAT_V4}
    runtime_context: dict[str, object] = {}
    first = subject._trial_from_document_store_snapshot_v1(
        snapshot,
        family_spec,
        policy,
        expected_packet=snapshot["document_packet"],
        _v4_runtime_context=runtime_context,
    )
    assert first["evidence_status"] == "NOT_OBSERVED_PROPOSAL_ONLY"
    prepared = runtime_context["prepared_context"]
    if mutated_inner == "CANDIDATES":
        prepared.prepared_topology._topology_candidates[  # noqa: SLF001
            "status"
        ] = "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    else:
        prepared.prepared_topology._legacy_topology_scan[  # noqa: SLF001
            "status"
        ] = "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"

    with pytest.raises(
        subject.FamilyFirstAccountingEvidenceSweepV1Error,
        match="inner authority drifted",
    ):
        subject._trial_from_document_store_snapshot_v1(
            snapshot,
            family_spec,
            policy,
            expected_packet=snapshot["document_packet"],
            _v4_runtime_context=runtime_context,
        )


def test_document_store_v4_rejects_forged_outer_prepared_context() -> None:
    snapshot = _authenticated_selected_document_store_snapshot(_documents()[2])
    family_spec = _family_spec()
    policy = {"format_version": subject.EVALUATION_SPEC_FORMAT_V4}
    runtime_context: dict[str, object] = {}
    subject._trial_from_document_store_snapshot_v1(
        snapshot,
        family_spec,
        policy,
        expected_packet=snapshot["document_packet"],
        _v4_runtime_context=runtime_context,
    )
    runtime_context["prepared_context"] = replace(
        runtime_context["prepared_context"],
        family_spec_sha256="0" * 64,
    )

    with pytest.raises(
        subject.FamilyFirstAccountingEvidenceSweepV1Error,
        match="differs from its source",
    ):
        subject._trial_from_document_store_snapshot_v1(
            snapshot,
            family_spec,
            policy,
            expected_packet=snapshot["document_packet"],
            _v4_runtime_context=runtime_context,
        )


def test_document_store_v4_rehydrates_multi_candidate_union_before_final_selection(
    monkeypatch,
) -> None:
    legacy_scan = {
        "regions": [
            {
                "cluster_start_document_line_ordinal": 12,
                "cluster_end_document_line_ordinal_exclusive": 18,
            }
        ],
        "scan_id": "legacy-scan",
        "status": "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL",
    }
    topology_candidates = {
        "regions": [
            {
                "cluster_start_document_line_ordinal": 2,
                "cluster_end_document_line_ordinal_exclusive": 8,
            },
            *legacy_scan["regions"],
        ],
        "status": "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS",
    }
    joined_pages = [
        {
            "lines": [
                {
                    "bbox": [0, line * 10, 100, line * 10 + 8],
                    "line_ordinal": line,
                    "vietocr_text": f"line-{page}-{line}",
                }
                for line in range(10)
            ],
            "page_sequence": page,
        }
        for page in (1, 2)
    ]
    snapshot = {
        "document_packet": {"document_ordinal": 1, "page_count": 2},
        "joined_pages": joined_pages,
    }
    batch_calls = []
    render_calls = []
    snapshot_object_ids = []
    trial_calls = []

    def trial_from_snapshot(_snapshot, _family, _policy, *, render_snapshots=(), **_kwargs):
        selected = "DETAIL" if render_snapshots else "SUMMARY"
        snapshot_object_ids.append(id(_snapshot))
        trial_calls.append(selected)
        return {
            "additive_closure": None,
            "column_context": None,
            "document_axis_binding": None,
            "document_ordinal": 1,
            "evidence_status": "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY",
            "private_provenance": {},
            "row_axis": {
                "rows": [
                    {
                        "label_match": {"page_sequence": 2 if render_snapshots else 1},
                        "missing_column_ordinals": [],
                    }
                ],
                "selected_fixture_candidate": selected,
                "status": "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY",
                "trailing_value_rows": [],
            },
            "source_pdf_ref": {},
            "topology_scan": legacy_scan,
            "unresolved_reasons": [],
        }

    monkeypatch.setattr(subject.topology_v1, "_spec", lambda _value: {"family_id": "FAMILY"})
    monkeypatch.setattr(
        subject,
        "_evaluation_spec",
        lambda *_args, **_kwargs: {"format_version": subject.EVALUATION_SPEC_FORMAT_V4},
    )
    monkeypatch.setattr(subject, "_validate", lambda value: value)
    monkeypatch.setattr(subject, "_trial_from_document_store_snapshot_v1", trial_from_snapshot)
    monkeypatch.setattr(
        subject,
        "_v4_topology_authority",
        lambda *_args, **_kwargs: (legacy_scan, topology_candidates),
    )
    monkeypatch.setattr(
        subject.document_store_v1,
        "project_authenticated_family_first_document_evidence_store_v1",
        lambda _cap: {
            "input_indices": {
                "numeric_receipt_id": "ffpniv3:receipt:" + "1" * 64,
                "semantic_index_id": "ffsiv1:index:" + "2" * 64,
            },
            "metrics": {"document_count": 1},
        },
    )
    monkeypatch.setattr(
        subject.document_store_v1,
        "read_authenticated_family_first_topology_scans_v1",
        lambda *_args, **_kwargs: pytest.fail("V4 used the cached topology accessor"),
    )
    monkeypatch.setattr(
        subject.document_store_v1,
        "read_authenticated_family_first_document_packet_v1",
        lambda *_args, **_kwargs: snapshot["document_packet"],
    )
    monkeypatch.setattr(
        subject.document_store_v1,
        "read_authenticated_family_first_document_evidence_snapshot_v1",
        lambda *_args, **_kwargs: pytest.fail("V4 used the legacy snapshot accessor"),
    )

    def selected_pages(_cap, *, document_page_selections):
        batch_calls.append(document_page_selections)
        return (snapshot,)

    monkeypatch.setattr(
        subject.document_store_v1,
        "read_authenticated_family_first_documents_selected_pages_v1",
        selected_pages,
    )

    def renders(_cap, *, document_ordinal, physical_pages):
        render_calls.append((document_ordinal, physical_pages))
        return ({"render": "authenticated"},)

    monkeypatch.setattr(
        subject.document_store_v1,
        "read_authenticated_family_first_document_page_renders_v1",
        renders,
    )

    result = (
        subject.build_authenticated_family_first_accounting_evidence_sweep_from_document_store_v1(
            object(), {}, {}
        )
    )

    assert batch_calls == [((1, (1, 2)),)]
    assert render_calls == [(1, (1, 2))]
    assert trial_calls == ["SUMMARY", "DETAIL"]
    assert snapshot_object_ids[0] == snapshot_object_ids[1]
    assert result["trials"][0]["row_axis"]["selected_fixture_candidate"] == "DETAIL"


def _ready_hierarchical_candidate(
    roles: list[str],
    *,
    candidate_ordinal: int,
    coefficients: tuple[int, int] = (149_990_681, 117_882_259),
    magnitude_power10: int = 6,
    periods: tuple[str, str] = ("31/12/2025", "31/12/2024"),
    root_resolution: str = "VISIBLE_SOURCE_ROLE_CORROBORATED_BY_COMPONENTS",
) -> dict:
    resolved = [{"role": role} for role in roles if role != "FAMILY"]
    resolved.append(
        {
            "resolution_kind": root_resolution,
            "role": "FAMILY",
            "values": [
                {
                    "column_ordinal": ordinal,
                    "number": {
                        "coefficient": coefficient,
                        "percentage_mark_present": False,
                        "scale": 0,
                    },
                }
                for ordinal, coefficient in enumerate(coefficients)
            ],
        }
    )
    return {
        "additive_closure": {
            "family_id": "FAMILY",
            "resolved_roles": resolved,
        },
        "candidate_ordinal": candidate_ordinal,
        "column_context": {
            "period_axis": [
                {"column_ordinal": ordinal, "resolved_period": period}
                for ordinal, period in enumerate(periods)
            ],
            "period_semantics": "BALANCE_COMPARATIVE",
            "unit_axis": [
                {
                    "column_ordinal": ordinal,
                    "currency": "VND",
                    "magnitude_power10": magnitude_power10,
                    "unit_kind": "MONEY",
                }
                for ordinal in range(2)
            ],
        },
        "reasons": [],
    }


def _strict_same_population_selection_policy() -> dict:
    return {
        "candidate_selection_policy": (
            "SAME_POPULATION_STRICT_ROLE_SUPERSET_WITH_EXACT_PERIOD_UNIT_ROOT_TOTAL"
        ),
        "closure_policy": "SCOPED_HIERARCHICAL_EXHAUSTIVE_CORROBORATE_OR_DERIVE",
    }


def test_same_population_summary_control_yields_to_unique_role_rich_detail() -> None:
    summary = _ready_hierarchical_candidate(
        ["EXPLICIT_FAMILY_TOTAL", "DEPOSIT_GROUP", "LOAN_GROUP", "FAMILY"],
        candidate_ordinal=0,
    )
    detail = _ready_hierarchical_candidate(
        ["DEPOSIT_VND", "DEPOSIT_GROUP", "LOAN_VND", "LOAN_GROUP", "FAMILY"],
        candidate_ordinal=1,
    )
    for candidate in (summary, detail):
        candidate["additive_closure"]["equations"] = {
            "global": [
                {
                    "result_role": "FAMILY",
                    "visible_result_roles": ["EXPLICIT_FAMILY_TOTAL"],
                }
            ]
        }

    selected, reasons = subject._select_candidate_evidence(
        [summary, detail],
        _strict_same_population_selection_policy(),
    )

    assert selected is detail
    assert reasons == []


@pytest.mark.parametrize("mutation", ["ROOT", "PERIOD", "UNIT"])
def test_root_presentation_alias_never_bypasses_population_signature(
    mutation: str,
) -> None:
    summary = _ready_hierarchical_candidate(
        ["EXPLICIT_FAMILY_TOTAL", "DEPOSIT_GROUP", "LOAN_GROUP", "FAMILY"],
        candidate_ordinal=0,
    )
    detail = _ready_hierarchical_candidate(
        ["DEPOSIT_VND", "DEPOSIT_GROUP", "LOAN_VND", "LOAN_GROUP", "FAMILY"],
        candidate_ordinal=1,
    )
    for candidate in (summary, detail):
        candidate["additive_closure"]["equations"] = {
            "global": [
                {
                    "result_role": "FAMILY",
                    "visible_result_roles": ["EXPLICIT_FAMILY_TOTAL"],
                }
            ]
        }
    if mutation == "ROOT":
        detail["additive_closure"]["resolved_roles"][-1]["values"][0]["number"]["coefficient"] += 1
    elif mutation == "PERIOD":
        detail["column_context"]["period_axis"][0]["resolved_period"] = "30/06/2025"
    else:
        detail["column_context"]["unit_axis"][0]["magnitude_power10"] = 3

    selected, reasons = subject._select_candidate_evidence(
        [summary, detail],
        _strict_same_population_selection_policy(),
    )

    assert selected is None
    assert reasons == ["MULTIPLE_DOWNSTREAM_EVIDENCE_COMPLETE_TOPOLOGY_REGIONS"]


def test_v4_same_population_summary_cannot_launder_detail_numeric_schema_gap() -> None:
    summary = _ready_hierarchical_candidate(
        ["DEPOSIT_GROUP", "LOAN_GROUP", "FAMILY"], candidate_ordinal=0
    )
    detail = _ready_hierarchical_candidate(
        ["DEPOSIT_VND", "DEPOSIT_GROUP", "LOAN_VND", "LOAN_GROUP", "FAMILY"],
        candidate_ordinal=1,
    )
    detail["reasons"] = ["SOURCE_ONLY_INTERNAL_NUMERIC_CLUSTER_VETO:aforav2:unassigned:upas"]
    detail["row_axis"] = {
        "rows": [{"label_match": {"page_sequence": 33}}],
    }
    policy = {
        **_strict_same_population_selection_policy(),
        "format_version": subject.EVALUATION_SPEC_FORMAT_V4,
    }

    selected, reasons = subject._select_candidate_evidence([summary, detail], policy)

    assert selected is None
    assert reasons == [
        "COMPATIBLE_CANDIDATE_NUMERIC_SCHEMA_GAP_VETO:READY_CANDIDATE_1:"
        "THREAT_CANDIDATE_2:THREAT_PAGES_33:"
        "SOURCE_ONLY_INTERNAL_NUMERIC_CLUSTER_VETO:aforav2:unassigned:upas"
    ]


def test_v4_ready_summary_cannot_launder_rootless_hdb_shaped_detail_gap() -> None:
    def values(coefficients: tuple[int, int]) -> list[dict]:
        return [
            {
                "column_ordinal": ordinal,
                "number": {
                    "coefficient": coefficient,
                    "percentage_mark_present": False,
                    "scale": 0,
                },
            }
            for ordinal, coefficient in enumerate(coefficients)
        ]

    deposit = (156_312_673, 94_198_824)
    loan = (31_521_384, 12_474_353)
    root = tuple(left + right for left, right in zip(deposit, loan, strict=True))
    summary = _ready_hierarchical_candidate(
        ["DEPOSIT_GROUP", "LOAN_GROUP", "FAMILY"],
        candidate_ordinal=0,
        coefficients=root,
    )
    summary["additive_closure"]["resolved_roles"] = [
        {"role": "DEPOSIT_GROUP", "values": values(deposit)},
        {"role": "LOAN_GROUP", "values": values(loan)},
        summary["additive_closure"]["resolved_roles"][-1],
    ]
    summary["additive_closure"]["equations"] = {
        "global": [
            {
                "component_roles_present": ["DEPOSIT_GROUP", "LOAN_GROUP"],
                "result_role": "FAMILY",
            }
        ]
    }
    detail = copy.deepcopy(summary)
    detail["candidate_ordinal"] = 1
    detail["additive_closure"]["resolved_roles"] = [
        {"role": "DEPOSIT_GROUP", "values": values(deposit)},
        # The known branch excludes the schema-unknown UPAS L/C source.
        {"role": "LOAN_GROUP", "values": values((31_521_384, 11_316_686))},
    ]
    detail["additive_closure"]["equations"] = {"global": []}
    detail["row_axis"] = {
        "rows": [{"label_match": {"page_sequence": 33}}],
        "trailing_value_rows": [
            {
                "candidate_ordinal": 0,
                "missing_column_ordinals": [],
                "page_sequence": 33,
                "status": "COMPLETE_VISIBLE_TRAILING_VALUE_ROW",
                "values": [
                    {
                        "column_ordinal": ordinal,
                        "parsed_token": {
                            "classification": "SIGNED_NUMBER",
                            "coefficient": coefficient,
                            "percentage_mark_present": False,
                            "scale": 0,
                        },
                    }
                    for ordinal, coefficient in enumerate(loan)
                ],
            }
        ],
    }
    detail["reasons"] = ["SOURCE_ONLY_INTERNAL_NUMERIC_CLUSTER_VETO:aforav2:unassigned:upas"]
    policy = {
        **_strict_same_population_selection_policy(),
        "format_version": subject.EVALUATION_SPEC_FORMAT_V4,
    }

    assert subject._candidate_population_signature(detail) is None
    selected, reasons = subject._select_candidate_evidence([summary, detail], policy)

    assert selected is None
    assert reasons == [
        "COMPATIBLE_CANDIDATE_NUMERIC_SCHEMA_GAP_VETO:READY_CANDIDATE_1:"
        "THREAT_CANDIDATE_2:THREAT_PAGES_33:"
        "SOURCE_ONLY_INTERNAL_NUMERIC_CLUSTER_VETO:aforav2:unassigned:upas"
    ]

    for mutation in ("TRAILING_VALUE", "MATCHED_COMPONENT", "PERIOD", "UNIT"):
        unrelated = copy.deepcopy(detail)
        if mutation == "TRAILING_VALUE":
            unrelated["row_axis"]["trailing_value_rows"][0]["values"][1]["parsed_token"][
                "coefficient"
            ] += 1
        elif mutation == "MATCHED_COMPONENT":
            unrelated["additive_closure"]["resolved_roles"][0]["values"][0]["number"][
                "coefficient"
            ] += 1
        elif mutation == "UNIT":
            unrelated["column_context"]["unit_axis"][0]["magnitude_power10"] = 3
        else:
            unrelated["column_context"]["period_axis"][0]["resolved_period"] = "30/06/2025"
        selected, reasons = subject._select_candidate_evidence([summary, unrelated], policy)
        assert selected is summary
        assert reasons == []

    for resolution_kind, equation_status in (
        (
            "VISIBLE_SOURCE_ROLE_ROUNDING_CORROBORATED_BY_COMPONENTS",
            "VISIBLE_RESULT_ROUNDING_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS",
        ),
        (
            "VISIBLE_TRAILING_TOTAL_ROUNDING_CORROBORATED_BY_COMPONENTS",
            "VISIBLE_TRAILING_RESULT_ROUNDING_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS",
        ),
    ):
        rounded_summary = copy.deepcopy(summary)
        rounded_root = next(
            record
            for record in rounded_summary["additive_closure"]["resolved_roles"]
            if record["role"] == "FAMILY"
        )
        rounded_root["resolution_kind"] = resolution_kind
        rounded_root["values"][0]["number"]["coefficient"] -= 2
        rounded_equation = rounded_summary["additive_closure"]["equations"]["global"][0]
        rounded_equation["status"] = equation_status
        rounded_equation["rounding_evidence"] = [{"status": "ROUNDING_BOUND_SATISFIED_ALL_LANES"}]

        selected, reasons = subject._select_candidate_evidence([rounded_summary, detail], policy)
        assert selected is None
        assert reasons[0].startswith("COMPATIBLE_CANDIDATE_NUMERIC_SCHEMA_GAP_VETO:")


def test_v4_numeric_schema_gap_from_different_population_does_not_veto_summary() -> None:
    summary = _ready_hierarchical_candidate(
        ["DEPOSIT_GROUP", "LOAN_GROUP", "FAMILY"], candidate_ordinal=0
    )
    unrelated = _ready_hierarchical_candidate(
        ["DEPOSIT_VND", "DEPOSIT_GROUP", "LOAN_VND", "LOAN_GROUP", "FAMILY"],
        candidate_ordinal=1,
        coefficients=(149_990_682, 117_882_259),
    )
    unrelated["reasons"] = ["SOURCE_ONLY_INTERNAL_NUMERIC_CLUSTER_VETO:unrelated"]

    selected, reasons = subject._select_candidate_evidence(
        [summary, unrelated],
        {
            **_strict_same_population_selection_policy(),
            "format_version": subject.EVALUATION_SPEC_FORMAT_V4,
        },
    )

    assert selected is summary
    assert reasons == []


def test_equal_hierarchical_candidates_remain_unresolved_without_page_routing() -> None:
    candidates = [
        _ready_hierarchical_candidate(
            ["DEPOSIT_GROUP", "LOAN_GROUP", "FAMILY"],
            candidate_ordinal=ordinal,
        )
        for ordinal in range(2)
    ]

    selected, reasons = subject._select_candidate_evidence(
        candidates,
        {"closure_policy": "HIERARCHICAL_RECURSIVE_CORROBORATE_OR_DERIVE"},
    )

    assert selected is None
    assert reasons == ["MULTIPLE_DOWNSTREAM_EVIDENCE_COMPLETE_TOPOLOGY_REGIONS"]


@pytest.mark.parametrize(
    ("summary_kwargs", "detail_kwargs"),
    [
        ({}, {"coefficients": (149_990_682, 117_882_259)}),
        ({}, {"periods": ("30/06/2025", "31/12/2024")}),
        ({}, {"magnitude_power10": 3}),
        (
            {},
            {"root_resolution": "DERIVED_EXACT_COMPONENT_SUM"},
        ),
    ],
)
def test_role_superset_never_routes_across_population_or_source_total_mismatch(
    summary_kwargs: dict, detail_kwargs: dict
) -> None:
    summary = _ready_hierarchical_candidate(
        ["DEPOSIT_GROUP", "LOAN_GROUP", "FAMILY"],
        candidate_ordinal=0,
        **summary_kwargs,
    )
    detail = _ready_hierarchical_candidate(
        ["DEPOSIT_VND", "DEPOSIT_GROUP", "LOAN_VND", "LOAN_GROUP", "FAMILY"],
        candidate_ordinal=1,
        **detail_kwargs,
    )

    selected, reasons = subject._select_candidate_evidence(
        [summary, detail],
        _strict_same_population_selection_policy(),
    )

    assert selected is None
    assert reasons == ["MULTIPLE_DOWNSTREAM_EVIDENCE_COMPLETE_TOPOLOGY_REGIONS"]


def test_numeric_statement_candidate_wins_only_because_policy_prose_fails_evidence() -> None:
    statement = _ready_hierarchical_candidate(
        ["DEPOSIT_GROUP", "LOAN_GROUP", "FAMILY"], candidate_ordinal=0
    )
    policy_prose = {
        "additive_closure": None,
        "candidate_ordinal": 1,
        "column_context": None,
        "reasons": ["VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE"],
    }

    selected, reasons = subject._select_candidate_evidence(
        [statement, policy_prose],
        {
            **_strict_same_population_selection_policy(),
            "format_version": subject.EVALUATION_SPEC_FORMAT_V4,
        },
    )

    assert selected is statement
    assert reasons == []


def test_role_superset_rejects_json_equal_but_differently_typed_total_lane() -> None:
    summary = _ready_hierarchical_candidate(
        ["DEPOSIT_GROUP", "LOAN_GROUP", "FAMILY"],
        candidate_ordinal=0,
        coefficients=(1, 117_882_259),
    )
    detail = _ready_hierarchical_candidate(
        ["DEPOSIT_VND", "DEPOSIT_GROUP", "LOAN_VND", "LOAN_GROUP", "FAMILY"],
        candidate_ordinal=1,
        coefficients=(1, 117_882_259),
    )
    detail["additive_closure"]["resolved_roles"][-1]["values"][0]["number"]["coefficient"] = True

    selected, reasons = subject._select_candidate_evidence(
        [summary, detail],
        _strict_same_population_selection_policy(),
    )

    assert selected is None
    assert reasons == ["MULTIPLE_DOWNSTREAM_EVIDENCE_COMPLETE_TOPOLOGY_REGIONS"]


def test_default_v3_preserves_legacy_role_superset_selection_without_population_gate() -> None:
    summary = _ready_hierarchical_candidate(
        ["DEPOSIT_GROUP", "LOAN_GROUP", "FAMILY"], candidate_ordinal=0
    )
    detail = _ready_hierarchical_candidate(
        ["DEPOSIT_VND", "DEPOSIT_GROUP", "LOAN_VND", "LOAN_GROUP", "FAMILY"],
        candidate_ordinal=1,
        coefficients=(149_990_682, 117_882_259),
    )

    selected, reasons = subject._select_candidate_evidence(
        [summary, detail],
        {"closure_policy": "HIERARCHICAL_RECURSIVE_CORROBORATE_OR_DERIVE"},
    )

    assert selected is detail
    assert reasons == []


def test_default_v3_preserves_presentation_alias_in_legacy_raw_role_richness() -> None:
    base = _ready_hierarchical_candidate(
        ["DEPOSIT_GROUP", "LOAN_GROUP", "FAMILY"], candidate_ordinal=0
    )
    presentation_superset = _ready_hierarchical_candidate(
        ["EXPLICIT_FAMILY_TOTAL", "DEPOSIT_GROUP", "LOAN_GROUP", "FAMILY"],
        candidate_ordinal=1,
    )
    for candidate in (base, presentation_superset):
        candidate["additive_closure"]["equations"] = {
            "global": [
                {
                    "result_role": "FAMILY",
                    "visible_result_roles": ["EXPLICIT_FAMILY_TOTAL"],
                }
            ]
        }

    selected, reasons = subject._select_candidate_evidence(
        [base, presentation_superset],
        {"closure_policy": "HIERARCHICAL_RECURSIVE_CORROBORATE_OR_DERIVE"},
    )

    assert selected is presentation_superset
    assert reasons == []


def test_v4_prepruning_candidates_reach_strict_downstream_comparator(monkeypatch) -> None:
    summary_region = {"region": "SUMMARY_CONTROL"}
    detail_region = {"region": "ROLE_RICH_DETAIL"}
    topology_scan = {
        "regions": [detail_region],
        "scan_id": "aftv1:scan:" + "1" * 64,
    }
    topology_candidates = {
        "input_binding": {"legacy_topology_scan_id": topology_scan["scan_id"]},
        "regions": [summary_region, detail_region],
    }
    family_spec = {"family_id": "FAMILY"}
    candidate_by_region = {
        "SUMMARY_CONTROL": _ready_hierarchical_candidate(
            ["DEPOSIT_GROUP", "LOAN_GROUP", "FAMILY"],
            candidate_ordinal=0,
        ),
        "ROLE_RICH_DETAIL": _ready_hierarchical_candidate(
            ["DEPOSIT_VND", "DEPOSIT_GROUP", "LOAN_VND", "LOAN_GROUP", "FAMILY"],
            candidate_ordinal=1,
        ),
    }
    occurrence_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        subject.row_axis_v1,
        "_topology_pages",
        lambda _pages: [{"exact": "COMPLETE_TOPOLOGY_PAGES"}],
    )
    monkeypatch.setattr(
        subject.row_axis_v1,
        "_build_accounting_family_row_axis_from_authenticated_topology_scan_v1",
        lambda *_args, **_kwargs: pytest.fail(
            "V4 candidate was routed through the legacy pruned-region selector"
        ),
    )
    monkeypatch.setattr(subject, "_visible_dash_rescue_inputs", lambda **_kwargs: ())
    monkeypatch.setattr(
        subject.topology_candidates_v2,
        "validate_accounting_family_topology_candidates_replay_v2",
        lambda received, _pages, received_spec: (
            received
            if received is topology_candidates and received_spec is family_spec
            else pytest.fail("candidate envelope lost exact replay inputs")
        ),
    )

    def occurrence_builder(
        _pages,
        received_spec,
        received_scan,
        received_region,
        received_policy,
        **kwargs,
    ):
        occurrence_calls.append(
            {
                "candidates": kwargs["topology_candidates"],
                "policy": received_policy,
                "region": received_region,
                "scan": received_scan,
                "spec": received_spec,
            }
        )
        return {
            "candidate": candidate_by_region[received_region["region"]],
            "one_edit_exact_source_structural_proofs": {"checks": []},
            "row_axis": {"region": received_region["region"]},
            "unresolved_reasons": [],
        }

    monkeypatch.setattr(
        subject.occurrence_row_v2,
        "_build_accounting_family_occurrence_row_axis_from_authenticated_topology_scan_v2",
        occurrence_builder,
    )
    monkeypatch.setattr(
        subject.column_context_v1,
        "_build_accounting_family_column_context_from_authenticated_row_axis_v1",
        lambda row_axis, *_args, **_kwargs: candidate_by_region[row_axis["region"]][
            "column_context"
        ],
    )
    monkeypatch.setattr(
        subject.scoped_v2,
        "_build_accounting_scoped_hierarchical_table_closure_from_authenticated_axis_v2",
        lambda occurrence_axis, *_args, **_kwargs: occurrence_axis["candidate"]["additive_closure"],
    )
    monkeypatch.setattr(subject, "_unresolved_reasons", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(subject, "_mixed_separator_consensus_reasons", lambda **_kwargs: [])
    monkeypatch.setattr(subject, "_degraded_dash_consensus_reasons", lambda **_kwargs: [])
    policy = {
        **_strict_same_population_selection_policy(),
        "expected_lane_unit_kinds": ["MONEY"],
        "format_version": subject.EVALUATION_SPEC_FORMAT_V4,
        "hierarchical_closure_spec": {"closed": True},
        "occurrence_row_axis_policy": {"closed": True},
        "period_semantics": "BALANCE_COMPARATIVE",
    }

    telemetry = subject._new_v4_runtime_telemetry_v1()
    evidence = subject._candidate_evidence_from_joined_pages(
        joined_pages=[],
        topology_scan=topology_scan,
        family_spec=family_spec,
        evaluation_spec=policy,
        render_snapshots=(),
        topology_candidates=topology_candidates,
        runtime_telemetry=telemetry,
    )
    selected, reasons = subject._select_candidate_evidence(evidence, policy)

    assert [call["region"] for call in occurrence_calls] == [
        summary_region,
        detail_region,
    ]
    assert all(call["scan"] is topology_scan for call in occurrence_calls)
    assert all(call["candidates"] is topology_candidates for call in occurrence_calls)
    assert [candidate["candidate_ordinal"] for candidate in evidence] == [0, 1]
    assert selected is evidence[1]
    assert reasons == []
    assert telemetry["candidate_count"] == 2
    assert telemetry["occurrence_axis_build_count"] == 2
    assert telemetry["occurrence_base_reuse_count"] == 2


def test_two_independent_role_rich_v4_details_remain_unresolved() -> None:
    details = [
        _ready_hierarchical_candidate(
            ["DEPOSIT_VND", "DEPOSIT_GROUP", "LOAN_VND", "LOAN_GROUP", "FAMILY"],
            candidate_ordinal=ordinal,
        )
        for ordinal in (1, 0)
    ]

    selected, reasons = subject._select_candidate_evidence(
        details,
        _strict_same_population_selection_policy(),
    )

    assert selected is None
    assert reasons == ["MULTIPLE_DOWNSTREAM_EVIDENCE_COMPLETE_TOPOLOGY_REGIONS"]


def test_multiple_candidates_with_missing_lanes_request_only_candidate_pages() -> None:
    joined_pages = [
        {"lines": [{} for _ in range(10)], "page_sequence": 1},
        {"lines": [{} for _ in range(10)], "page_sequence": 2},
        {"lines": [{} for _ in range(10)], "page_sequence": 3},
    ]
    topology_scan = {
        "regions": [
            {
                "cluster_start_document_line_ordinal": 12,
                "cluster_end_document_line_ordinal_exclusive": 18,
            }
        ],
        "status": "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS",
    }
    trial = {
        "row_axis": None,
        "unresolved_reasons": [
            "CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE",
            "CANDIDATE_2:COLUMN_CONTEXT:PERIOD_AXIS_NOT_BOUND_TO_EVERY_BODY_COLUMN",
        ],
    }

    assert subject._missing_render_pages_for_document_store_trial_v1(
        trial, topology_scan, joined_pages
    ) == (2,)

    trial["unresolved_reasons"] = ["MULTIPLE_DOWNSTREAM_EVIDENCE_COMPLETE_TOPOLOGY_REGIONS"]
    assert (
        subject._missing_render_pages_for_document_store_trial_v1(
            trial, topology_scan, joined_pages
        )
        == ()
    )


def test_v4_extreme_margin_render_request_selects_only_its_bound_candidate_page() -> None:
    joined_pages = [{"lines": [{} for _ in range(10)], "page_sequence": page} for page in (1, 2, 3)]
    topology_scan = {
        "regions": [
            {
                "cluster_start_document_line_ordinal": 12,
                "cluster_end_document_line_ordinal_exclusive": 18,
            }
        ],
        "status": "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL",
    }
    topology_candidates = {
        "regions": [
            {
                "cluster_start_document_line_ordinal": 2,
                "cluster_end_document_line_ordinal_exclusive": 8,
            },
            topology_scan["regions"][0],
        ],
        "status": "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS",
    }
    trial = {
        "row_axis": None,
        "unresolved_reasons": [
            "CANDIDATE_1:VISIBLE_ROLE_OCCURRENCE_ROW_LANES_NOT_COMPLETE",
            "CANDIDATE_2:EXTREME_MARGIN_ANNOTATION_RENDER_REQUIRED:PAGE_SEQUENCE:2",
        ],
    }

    assert subject._missing_render_pages_for_document_store_trial_v1(
        trial,
        topology_scan,
        joined_pages,
        evaluation_spec={"format_version": subject.EVALUATION_SPEC_FORMAT_V4},
        topology_candidates=topology_candidates,
    ) == (2,)


@pytest.mark.parametrize(
    "reason",
    [
        "CANDIDATE_2:EXTREME_MARGIN_ANNOTATION_RENDER_REQUIRED:PAGE_SEQUENCE:1",
        "CANDIDATE_3:EXTREME_MARGIN_ANNOTATION_RENDER_REQUIRED:PAGE_SEQUENCE:2",
        "EXTREME_MARGIN_ANNOTATION_RENDER_REQUIRED:PAGE_SEQUENCE:2",
        "CANDIDATE_2:EXTREME_MARGIN_ANNOTATION_RENDER_REQUIRED:PAGE_SEQUENCE:" + "9" * 100,
        "CANDIDATE_2:OFF_LANE_NUMERIC_SOURCE_ONLY_VETO:PAGE_SEQUENCE:2",
    ],
)
def test_extreme_margin_render_request_must_be_exact_and_candidate_bound(reason: str) -> None:
    joined_pages = [{"lines": [{} for _ in range(10)], "page_sequence": page} for page in (1, 2)]
    topology_scan = {
        "regions": [
            {
                "cluster_start_document_line_ordinal": 12,
                "cluster_end_document_line_ordinal_exclusive": 18,
            }
        ],
        "status": "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL",
    }
    topology_candidates = {
        "regions": [
            {
                "cluster_start_document_line_ordinal": 2,
                "cluster_end_document_line_ordinal_exclusive": 8,
            },
            topology_scan["regions"][0],
        ],
        "status": "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS",
    }
    trial = {"row_axis": None, "unresolved_reasons": [reason]}

    assert (
        subject._missing_render_pages_for_document_store_trial_v1(
            trial,
            topology_scan,
            joined_pages,
            evaluation_spec={"format_version": subject.EVALUATION_SPEC_FORMAT_V4},
            topology_candidates=topology_candidates,
        )
        == ()
    )


def test_v3_never_schedules_extreme_margin_furniture_render_request() -> None:
    trial = {
        "row_axis": None,
        "unresolved_reasons": ["EXTREME_MARGIN_ANNOTATION_RENDER_REQUIRED:PAGE_SEQUENCE:1"],
    }
    topology_scan = {
        "regions": [
            {
                "cluster_start_document_line_ordinal": 0,
                "cluster_end_document_line_ordinal_exclusive": 1,
            }
        ],
        "status": "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL",
    }
    assert (
        subject._missing_render_pages_for_document_store_trial_v1(
            trial,
            topology_scan,
            [{"lines": [{}], "page_sequence": 1}],
            evaluation_spec={"format_version": subject.EVALUATION_SPEC_FORMAT_V3},
        )
        == ()
    )


def test_v4_render_scheduler_uses_prepruning_candidate_page_union() -> None:
    joined_pages = [{"lines": [{} for _ in range(10)], "page_sequence": page} for page in (1, 2, 3)]
    topology_scan = {
        "regions": [
            {
                "cluster_start_document_line_ordinal": 22,
                "cluster_end_document_line_ordinal_exclusive": 28,
            }
        ],
        "status": "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL",
    }
    topology_candidates = {
        "regions": [
            {
                "cluster_start_document_line_ordinal": 12,
                "cluster_end_document_line_ordinal_exclusive": 18,
            },
            *topology_scan["regions"],
        ],
        "status": "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS",
    }
    trial = {
        "row_axis": None,
        "unresolved_reasons": [
            "CANDIDATE_1:VISIBLE_ROLE_OCCURRENCE_ROW_LANES_NOT_COMPLETE",
        ],
    }

    assert subject._missing_render_pages_for_document_store_trial_v1(
        trial,
        topology_scan,
        joined_pages,
        evaluation_spec={"format_version": subject.EVALUATION_SPEC_FORMAT_V4},
        topology_candidates=topology_candidates,
    ) == (2, 3)


def test_v4_ready_summary_cannot_hide_detail_candidate_dash_page() -> None:
    joined_pages = [{"lines": [{} for _ in range(10)], "page_sequence": page} for page in (1, 2)]
    summary_region = {
        "cluster_start_document_line_ordinal": 2,
        "cluster_end_document_line_ordinal_exclusive": 8,
    }
    detail_region = {
        "cluster_start_document_line_ordinal": 12,
        "cluster_end_document_line_ordinal_exclusive": 18,
    }
    topology_scan = {
        "regions": [detail_region],
        "status": "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL",
    }
    topology_candidates = {
        "regions": [summary_region, detail_region],
        "status": "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS",
    }
    trial = {
        # The first-pass selector kept the complete summary and discarded the
        # detail candidate's missing-DASH reason from the public trial shape.
        "row_axis": {
            "rows": [
                {
                    "label_match": {"page_sequence": 1},
                    "missing_column_ordinals": [],
                }
            ],
            "status": "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY",
            "trailing_value_rows": [],
        },
        "unresolved_reasons": [],
    }

    assert subject._missing_render_pages_for_document_store_trial_v1(
        trial,
        topology_scan,
        joined_pages,
        evaluation_spec={"format_version": subject.EVALUATION_SPEC_FORMAT_V4},
        topology_candidates=topology_candidates,
    ) == (1, 2)
    assert (
        subject._missing_render_pages_for_document_store_trial_v1(
            trial,
            topology_scan,
            joined_pages,
            evaluation_spec={"format_version": subject.EVALUATION_SPEC_FORMAT_V3},
        )
        == ()
    )


def test_v4_trailing_dash_hole_requests_render_even_when_role_rows_are_complete() -> None:
    trial = {
        "row_axis": {
            "rows": [
                {
                    "label_match": {"page_sequence": 6},
                    "missing_column_ordinals": [],
                }
            ],
            "status": "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY",
            "trailing_value_rows": [
                {
                    "missing_column_ordinals": [0],
                    "page_sequence": 7,
                }
            ],
        },
        "unresolved_reasons": [],
    }
    topology_scan = {"regions": [], "status": "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"}

    assert subject._missing_render_pages_for_document_store_trial_v1(
        trial,
        topology_scan,
        [],
        evaluation_spec={"format_version": subject.EVALUATION_SPEC_FORMAT_V4},
    ) == (7,)
    assert (
        subject._missing_render_pages_for_document_store_trial_v1(
            trial,
            topology_scan,
            [],
            evaluation_spec={"format_version": subject.EVALUATION_SPEC_FORMAT_V3},
        )
        == ()
    )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["expected_lane_unit_kinds"].__setitem__(0, "BANK_SPECIFIC"),
        lambda value: value.__setitem__("period_semantics", "2026_ONLY"),
        lambda value: value.__setitem__("closure_policy", True),
    ],
)
def test_evaluation_policy_type_and_enum_drift_fail_closed(monkeypatch, mutation) -> None:
    _patch_live_inputs(monkeypatch)
    policy = _evaluation_spec()
    mutation(policy)

    with pytest.raises(subject.FamilyFirstAccountingEvidenceSweepV1Error, match="specification"):
        subject.build_authenticated_family_first_accounting_evidence_sweep_v1(
            object(), object(), _family_spec(), policy
        )


@pytest.mark.parametrize("equivalences", [[], 0, False, {}])
def test_v2_source_group_equivalence_requires_one_exact_nonempty_list(equivalences) -> None:
    family = _family_spec()
    family["format_version"] = "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V2"
    family["presence_evidence_mode"] = "GLOBAL_CORE_HITS"
    family["required_role_combinations"] = [["CASH_VND", "CASH_FOREIGN"]]
    for child in family["children"]:
        child["presence"] = "OPTIONAL"
    family["children"].append(
        {
            "aliases": ["Tiền mặt tại Việt Nam"],
            "presence": "OPTIONAL",
            "role": "CASH_VIETNAM_PARENT",
            "role_kind": "SOURCE_ONLY_GROUP_PARENT",
        }
    )
    policy = _evaluation_spec()
    policy["format_version"] = "ACCOUNTING_FAMILY_EVALUATION_SPEC_V2"
    policy["source_group_equivalences"] = equivalences

    with pytest.raises(
        subject.FamilyFirstAccountingEvidenceSweepV1Error,
        match="source-group equivalence",
    ):
        subject._evaluation_spec(policy, family)


def test_semantic_numeric_denominator_mismatch_fails_before_documents(monkeypatch) -> None:
    _patch_live_inputs(monkeypatch)
    monkeypatch.setattr(
        subject.numeric_v3,
        "project_authenticated_family_first_ppocrv6_numeric_index_v3",
        lambda _cap: {
            "receipt_id": "ffpniv3:receipt:" + "4" * 64,
            "metrics": {"document_count": 2, "page_count": 3, "sample_count": 18},
        },
    )

    with pytest.raises(subject.FamilyFirstAccountingEvidenceSweepV1Error, match="denominators"):
        subject.build_authenticated_family_first_accounting_evidence_sweep_v1(
            object(), object(), _family_spec(), _evaluation_spec()
        )


def test_bool_numeric_denominator_does_not_launder_as_integer(monkeypatch) -> None:
    _patch_live_inputs(monkeypatch)
    monkeypatch.setattr(
        subject.numeric_v3,
        "project_authenticated_family_first_ppocrv6_numeric_index_v3",
        lambda _cap: {
            "receipt_id": "ffpniv3:receipt:" + "4" * 64,
            "metrics": {"document_count": 2, "page_count": 3, "sample_count": True},
        },
    )

    with pytest.raises(subject.FamilyFirstAccountingEvidenceSweepV1Error, match="denominators"):
        subject.build_authenticated_family_first_accounting_evidence_sweep_v1(
            object(), object(), _family_spec(), _evaluation_spec()
        )


def test_degraded_dash_requires_exact_accounting_corroboration() -> None:
    sample_id = "ffaprv1:region:" + "1" * 64
    row_axis = {
        "rows": [
            {
                "role": "CASH_VND",
                "values": [{"sample_id": sample_id}],
            }
        ],
        "visible_dash_rescues": [
            {
                "classification": "DEGRADED_CENTERED_SHORT_MARK_CANDIDATE",
                "region_id": sample_id,
                "supporting_peer_dash_column_ordinal": 1,
            }
        ],
    }
    unresolved = {
        "equations": [],
        "format_version": "ACCOUNTING_HIERARCHICAL_TABLE_CLOSURE_V1",
        "status": "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO",
    }
    corroborated = copy.deepcopy(unresolved)
    corroborated["equations"] = [
        {
            "component_roles_present": ["CASH_VND"],
            "result_role": "CASH_TOTAL",
            "status": "VISIBLE_RESULT_CORROBORATED_BY_COMPONENTS",
        }
    ]

    assert subject._degraded_dash_consensus_reasons(
        row_axis=row_axis,
        closure=unresolved,
    ) == ["DEGRADED_DASH:EXACT_VISIBLE_ACCOUNTING_CLOSURE_ABSENT:" + sample_id]
    assert (
        subject._degraded_dash_consensus_reasons(
            row_axis=row_axis,
            closure=corroborated,
        )
        == []
    )


def test_degraded_dash_accepts_repeated_same_page_pixel_glyph_family() -> None:
    sample_id = "ffaprv1:region:" + "1" * 64

    def glyph(
        role: str,
        column: int,
        *,
        classification: str,
        width: int,
        height: int = 6,
        peer: int | None = None,
    ) -> dict[str, object]:
        return {
            "classification": classification,
            "column_ordinal": column,
            "dash_evidence": {
                "crop_ref": {"pixel_height": 28},
                "glyph_metrics": {"component_bbox": [16, 11, 16 + width, 11 + height]},
            },
            "page_sequence": 1,
            "region_id": sample_id if classification.startswith("DEGRADED") else "peer",
            "role": role,
            "supporting_peer_dash_column_ordinal": peer,
        }

    row_axis = {
        "rows": [{"role": "CASH_VND", "values": [{"sample_id": sample_id}]}],
        "visible_dash_rescues": [
            glyph(
                "CASH_VND",
                0,
                classification="DEGRADED_CENTERED_SHORT_MARK_CANDIDATE",
                width=6,
                peer=1,
            ),
            glyph(
                "CASH_VND",
                1,
                classification="VISIBLE_HORIZONTAL_DASH_GLYPH",
                width=9,
                height=4,
            ),
            glyph("PEER_2", 0, classification="VISIBLE_HORIZONTAL_DASH_GLYPH", width=8, height=4),
            glyph("PEER_3", 0, classification="VISIBLE_HORIZONTAL_DASH_GLYPH", width=9, height=4),
            glyph("PEER_4", 0, classification="VISIBLE_HORIZONTAL_DASH_GLYPH", width=10, height=4),
            glyph("PEER_5", 0, classification="VISIBLE_HORIZONTAL_DASH_GLYPH", width=8, height=4),
            glyph("PEER_6", 0, classification="VISIBLE_HORIZONTAL_DASH_GLYPH", width=9, height=4),
        ],
    }
    closure = {
        "equations": [],
        "format_version": "ACCOUNTING_HIERARCHICAL_TABLE_CLOSURE_V1",
        "status": "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO",
    }

    assert subject._degraded_dash_consensus_reasons(row_axis=row_axis, closure=closure) == []

    row_axis["visible_dash_rescues"] = row_axis["visible_dash_rescues"][:-2]
    assert subject._degraded_dash_consensus_reasons(row_axis=row_axis, closure=closure) == [
        "DEGRADED_DASH:EXACT_VISIBLE_ACCOUNTING_CLOSURE_ABSENT:" + sample_id
    ]
