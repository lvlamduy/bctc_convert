from __future__ import annotations

import copy
import hashlib
import io
import json
from concurrent.futures import Future
from dataclasses import replace
from types import SimpleNamespace

import pytest
from PIL import Image, ImageDraw

from bctc_ai.evaluation import family_first_accounting_evidence_sweep_v1 as subject
from bctc_ai.evaluation import family_first_authenticated_page_region_v1 as render_v1
from bctc_ai.evaluation import family_first_semantic_index_v1 as semantic_v1
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _document_store_registry_size_in_spawned_worker() -> int:
    """Top-level probe used to prove the opaque store registry is not forked."""

    return len(subject.document_store_v1._STORES)  # noqa: SLF001


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


def test_selected_public_replay_input_binds_opaque_dash_region_by_validated_ref() -> None:
    rescue = {
        "column_ordinal": 0,
        "page_sequence": 1,
        "region": _dash_region(1, 1, [550, 100, 650, 130]),
        "role": "GENERIC_ADDITIVE_ROLE",
    }
    selected = {
        "additive_closure": {},
        "column_context": {},
        "column_context_visible_dash_rescues": (rescue,),
        "row_axis": {},
    }

    observed = subject._selected_one_edit_public_replay_input_v1(
        authority_pages_sha256="1" * 64,
        evaluation_spec={},
        family_spec={},
        receipt={},
        selected=selected,
        selected_topology_region={},
    )

    assert observed["visible_dash_rescues_sha256"] == (
        subject.one_edit_v1._visible_dash_rescues_sha256_v1((rescue,))
    )
    different = copy.deepcopy(rescue)
    different["region"] = _dash_region(1, 1, [560, 100, 660, 130])
    assert (
        subject.one_edit_v1._visible_dash_rescues_sha256_v1((different,))
        != observed["visible_dash_rescues_sha256"]
    )
    tampered = copy.deepcopy(rescue)
    tampered["region"]["region_png_bytes"] += b"tamper"
    with pytest.raises(
        subject.one_edit_v1.AccountingFamilyOneEditExactAuthorityV1Error,
        match="visible-dash region replay failed",
    ):
        subject.one_edit_v1._visible_dash_rescues_sha256_v1((tampered,))


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


def test_scoped_closure_mixed_token_reaches_visible_source_through_exact_derived_dag() -> None:
    closure = {
        "coverage_receipt": [
            {
                "candidate_ordinal": None,
                "disposition": "GLOBAL_HIERARCHY_SOURCE_OCCURRENCE",
                "occurrence_id": "leaf-occurrence",
                "role": "EXACT_LEAF",
                "row_kind": "ROLE_ROW",
                "sample_ids": ["mixed-leaf"],
                "source_record": {},
            }
        ],
        "equations": {
            "global": [
                {
                    "component_roles_present": ["DERIVED_CORE"],
                    "result_role": "VISIBLE_ROOT",
                    "status": "VISIBLE_TRAILING_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS",
                },
                {
                    "component_roles_present": ["DERIVED_GROUP"],
                    "result_role": "DERIVED_CORE",
                    "status": "DERIVED_EXACT_EXHAUSTIVE_COMPONENT_SUM",
                },
                {
                    "component_roles_present": ["EXACT_LEAF"],
                    "result_role": "DERIVED_GROUP",
                    "status": "DERIVED_EXACT_EXHAUSTIVE_COMPONENT_SUM",
                },
            ],
            "local": [],
        },
        "format_version": "ACCOUNTING_SCOPED_HIERARCHICAL_TABLE_CLOSURE_V2",
        "resolved_roles": [],
        "status": "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO",
    }

    assert subject._mixed_candidate_has_accounting_corroboration(
        role="EXACT_LEAF",
        sample_id="mixed-leaf",
        closure=closure,
    )

    no_visible_source = copy.deepcopy(closure)
    no_visible_source["equations"]["global"][0]["status"] = "DERIVED_EXACT_EXHAUSTIVE_COMPONENT_SUM"
    assert not subject._mixed_candidate_has_accounting_corroboration(
        role="EXACT_LEAF",
        sample_id="mixed-leaf",
        closure=no_visible_source,
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
    wrong_period = copy.deepcopy(snapshot)
    wrong_period["document_packet"]["period"] = "Q2"
    wrong_period_material = copy.deepcopy(wrong_period)
    wrong_period_material.pop("snapshot_id")
    wrong_period["snapshot_id"] = "ffdesv1:snapshot:" + canonical_json_sha256_v1(
        wrong_period_material
    )
    with pytest.raises(
        subject.FamilyFirstAccountingEvidenceSweepV1Error,
        match="another family trial",
    ):
        subject.rebuild_family_first_accounting_trial_from_document_snapshot_v1(
            baseline, wrong_period, family, policy
        )

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


@pytest.mark.parametrize("jobs", [False, 0, 17, "2"])
def test_document_store_parallel_worker_count_must_be_bounded_integer(
    monkeypatch,
    jobs,
) -> None:
    monkeypatch.setattr(subject.topology_v1, "_spec", lambda _value: {"family_id": "FAMILY"})
    monkeypatch.setattr(
        subject,
        "_evaluation_spec",
        lambda *_args, **_kwargs: {"format_version": subject.EVALUATION_SPEC_FORMAT_V4},
    )
    monkeypatch.setattr(
        subject.document_store_v1,
        "project_authenticated_family_first_document_evidence_store_v1",
        lambda _cap: {
            "input_indices": {
                "numeric_receipt_id": "ffpniv3:receipt:" + "1" * 64,
                "semantic_index_id": "ffsiv1:index:" + "2" * 64,
            },
            "metrics": {"document_count": 0},
        },
    )

    with pytest.raises(
        subject.FamilyFirstAccountingEvidenceSweepV1Error,
        match="worker count must be an integer from 1 to 16",
    ):
        subject.build_authenticated_family_first_accounting_evidence_sweep_from_document_store_v1(
            object(), {}, {}, jobs=jobs
        )


def test_document_store_parallel_workers_require_v4(monkeypatch) -> None:
    monkeypatch.setattr(subject.topology_v1, "_spec", lambda _value: {"family_id": "FAMILY"})
    monkeypatch.setattr(
        subject,
        "_evaluation_spec",
        lambda *_args, **_kwargs: {"format_version": subject.EVALUATION_SPEC_FORMAT_V3},
    )
    monkeypatch.setattr(
        subject.document_store_v1,
        "project_authenticated_family_first_document_evidence_store_v1",
        lambda _cap: {
            "input_indices": {
                "numeric_receipt_id": "ffpniv3:receipt:" + "1" * 64,
                "semantic_index_id": "ffsiv1:index:" + "2" * 64,
            },
            "metrics": {"document_count": 0},
        },
    )

    with pytest.raises(
        subject.FamilyFirstAccountingEvidenceSweepV1Error,
        match="parallel document-store trials require evaluation V4",
    ):
        subject.build_authenticated_family_first_accounting_evidence_sweep_from_document_store_v1(
            object(), {}, {}, jobs=2
        )


def test_v4_document_store_worker_rebuilds_from_parent_bound_source(monkeypatch) -> None:
    snapshot = _authenticated_selected_document_store_snapshot(_documents()[2])
    packet = snapshot["document_packet"]
    trial = {
        "document_ordinal": packet["document_ordinal"],
        "topology_scan": {"status": "NO_COMPLETE_TOPOLOGY_REGION"},
    }
    calls = []

    def build(
        selected,
        family,
        policy,
        *,
        render_snapshots,
        topology_scan,
        expected_packet,
        _v4_runtime_context,
        _defer_selected_public_replay_for_render,
    ):
        calls.append(
            (
                selected,
                family,
                policy,
                render_snapshots,
                topology_scan,
                expected_packet,
                _v4_runtime_context,
                _defer_selected_public_replay_for_render,
            )
        )
        return copy.deepcopy(trial)

    monkeypatch.setattr(subject, "_trial_from_document_store_snapshot_v1", build)

    result = subject._v4_document_store_trial_worker_v1(
        (
            packet,
            snapshot,
            _family_spec(),
            {"format_version": subject.EVALUATION_SPEC_FORMAT_V4},
            (),
            None,
            "NONE",
        )
    )

    assert result == {
        "document_ordinal": packet["document_ordinal"],
        "missing_render_pages": (),
        "packet_id": packet["packet_id"],
        "snapshot_id": snapshot["snapshot_id"],
        "trial": trial,
    }
    assert calls[0][0] is snapshot
    assert calls[0][3] == ()
    assert calls[0][4] is None
    assert calls[0][5] is packet
    assert calls[0][7] is True
    assert calls[0][6] == {}


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.__setitem__("document_ordinal", 2),
        lambda value: value.__setitem__("packet_id", "ffdesv1:document:" + "f" * 64),
        lambda value: value.__setitem__("snapshot_id", "ffdesv1:selected:" + "f" * 64),
        lambda value: value["trial"].__setitem__("document_ordinal", 2),
        lambda value: value.__setitem__("missing_render_pages", [1]),
        lambda value: value.__setitem__("missing_render_pages", (2, 1)),
        lambda value: value.__setitem__("missing_render_pages", (1, 1)),
        lambda value: value.__setitem__("missing_render_pages", (3,)),
    ],
)
def test_v4_document_store_worker_result_is_rebound_to_parent_source(mutation) -> None:
    snapshot = _authenticated_selected_document_store_snapshot(_documents()[1])
    packet = snapshot["document_packet"]
    result = {
        "document_ordinal": 1,
        "missing_render_pages": (),
        "packet_id": packet["packet_id"],
        "snapshot_id": snapshot["snapshot_id"],
        "trial": {"document_ordinal": 1},
    }
    mutation(result)

    with pytest.raises(
        subject.FamilyFirstAccountingEvidenceSweepV1Error,
        match="differs from its parent source",
    ):
        subject._validated_v4_document_store_worker_result_v1(
            result,
            packet=packet,
            snapshot=snapshot,
        )


def _render_preflight_fixture() -> tuple[dict, dict, dict]:
    packet = {
        "document_ordinal": 1,
        "packet_id": "ffdesv1:document:" + "a" * 64,
        "page_count": 3,
    }
    snapshot = {"snapshot_id": "ffdesv1:selected:" + "b" * 64}
    material = subject._v4_document_store_render_preflight_material_v1(
        document_ordinal=1,
        packet_id=packet["packet_id"],
        render_pages=(2,),
        reservoir_pages=(1, 2, 3),
        snapshot_id=snapshot["snapshot_id"],
        topology_candidates_id="aftcv2:result:" + "c" * 64,
        topology_scan_id="aftv1:scan:" + "d" * 64,
    )
    preflight = {
        **material,
        "completed_result": None,
        "preflight_id": "ffdrpv1:preflight:" + subject.canonical_json_sha256_v1(material),
        "render_pages": (2,),
        "reservoir_pages": (1, 2, 3),
    }
    return packet, snapshot, preflight


def _disable_v4_trial_checkpoints(monkeypatch) -> None:
    monkeypatch.setattr(subject, "_v4_trial_checkpoint_context_v1", lambda *_a, **_k: {})
    monkeypatch.setattr(subject, "_read_v4_trial_checkpoint_v1", lambda **_kwargs: None)
    monkeypatch.setattr(subject, "_write_v4_trial_checkpoint_v1", lambda **_kwargs: None)


def test_v4_trial_checkpoint_round_trips_exact_current_binding(tmp_path) -> None:
    snapshot = _authenticated_selected_document_store_snapshot(_documents()[1])
    packet = snapshot["document_packet"]
    binding = {
        "directory": tmp_path,
        "family_spec_sha256": "a" * 64,
        "git_head": "b" * 40,
        "manifest_id": "ffdesv1:manifest:" + "c" * 64,
        "policy_sha256": "d" * 64,
    }
    worker_result = {
        "document_ordinal": 1,
        "missing_render_pages": (),
        "packet_id": packet["packet_id"],
        "snapshot_id": snapshot["snapshot_id"],
        "trial": {"document_ordinal": 1, "value": 42},
    }

    subject._write_v4_trial_checkpoint_v1(
        binding=binding,
        packet=packet,
        snapshot=snapshot,
        worker_result=worker_result,
    )

    assert (
        subject._read_v4_trial_checkpoint_v1(
            binding=binding,
            packet=packet,
            snapshot=snapshot,
        )
        == worker_result
    )
    path = tmp_path / "document-001.json"
    assert path.stat().st_mode & 0o777 == 0o444


def test_v4_trial_checkpoint_rejects_coherently_rehashed_revision_tamper(tmp_path) -> None:
    snapshot = _authenticated_selected_document_store_snapshot(_documents()[1])
    packet = snapshot["document_packet"]
    binding = {
        "directory": tmp_path,
        "family_spec_sha256": "a" * 64,
        "git_head": "b" * 40,
        "manifest_id": "ffdesv1:manifest:" + "c" * 64,
        "policy_sha256": "d" * 64,
    }
    worker_result = {
        "document_ordinal": 1,
        "missing_render_pages": (),
        "packet_id": packet["packet_id"],
        "snapshot_id": snapshot["snapshot_id"],
        "trial": {"document_ordinal": 1},
    }
    subject._write_v4_trial_checkpoint_v1(
        binding=binding,
        packet=packet,
        snapshot=snapshot,
        worker_result=worker_result,
    )
    path = tmp_path / "document-001.json"
    path.chmod(0o600)
    value = json.loads(path.read_text())
    value["git_head"] = "e" * 40
    material = dict(value)
    material.pop("checkpoint_id")
    value["checkpoint_id"] = "ffdtcv1:checkpoint:" + subject.canonical_json_sha256_v1(material)
    path.write_bytes(subject._v4_trial_checkpoint_bytes_v1(value))

    with pytest.raises(
        subject.FamilyFirstAccountingEvidenceSweepV1Error,
        match="binding drifted",
    ):
        subject._read_v4_trial_checkpoint_v1(
            binding=binding,
            packet=packet,
            snapshot=snapshot,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.__setitem__("document_ordinal", 2),
        lambda value: value.__setitem__("packet_id", "ffdesv1:document:" + "e" * 64),
        lambda value: value.__setitem__("snapshot_id", "ffdesv1:selected:" + "e" * 64),
        lambda value: value.__setitem__("completed_result", {}),
        lambda value: value.__setitem__("render_pages", (2, 1)),
        lambda value: value.__setitem__("render_pages", (2, 2)),
        lambda value: value.__setitem__("render_pages", (4,)),
        lambda value: value.__setitem__("render_pages", (2, 3)),
        lambda value: value.__setitem__("reservoir_pages", (1, 2)),
        lambda value: value.__setitem__("reservoir_pages", (1, 2, 4)),
        lambda value: value.__setitem__("topology_scan_id", "aftv1:scan:" + "e" * 64),
        lambda value: value.__setitem__("preflight_id", "ffdrpv1:preflight:" + "e" * 64),
    ],
)
def test_v4_document_store_render_preflight_rejects_parent_or_axis_tamper(mutation) -> None:
    packet, snapshot, preflight = _render_preflight_fixture()
    mutation(preflight)

    with pytest.raises(subject.FamilyFirstAccountingEvidenceSweepV1Error):
        subject._validated_v4_document_store_render_preflight_v1(
            preflight,
            packet=packet,
            snapshot=snapshot,
        )


def test_v4_preflight_bound_trial_keeps_reservoir_private_until_exact_reveal(
    monkeypatch,
) -> None:
    packet, snapshot, preflight = _render_preflight_fixture()
    snapshot = {
        **snapshot,
        "document_packet": packet,
        "joined_pages": [{"physical_page": page} for page in (1, 2, 3)],
    }
    renders = tuple(_render(1, page) for page in (1, 2, 3))
    prepared = SimpleNamespace(prepared_snapshot=object())
    topology_scan = {"scan_id": preflight["topology_scan_id"]}
    topology_candidates = {
        "result_id": preflight["topology_candidates_id"],
        "regions": [{"candidate_id": "candidate-1"}],
    }
    family_spec = _family_spec()
    policy = {"format_version": subject.EVALUATION_SPEC_FORMAT_V4}
    trial_render_pages = []

    monkeypatch.setattr(
        subject,
        "_V4_RENDER_PREFLIGHT_CONTEXT_CACHE",
        {
            preflight["preflight_id"]: {
                "family_spec_sha256": subject.canonical_json_sha256_v1(family_spec),
                "packet_id": packet["packet_id"],
                "policy_sha256": subject.canonical_json_sha256_v1(policy),
                "prepared_context": prepared,
                "snapshot_id": snapshot["snapshot_id"],
                "topology_candidates_id": preflight["topology_candidates_id"],
                "topology_scan_id": preflight["topology_scan_id"],
            }
        },
    )
    monkeypatch.setattr(
        subject,
        "_open_prepared_v4_document_store_context_v1",
        lambda *_a, **_k: (snapshot, topology_scan, topology_candidates, (object(),)),
    )
    monkeypatch.setattr(
        subject,
        "_v4_prepruning_candidate_render_pages_v1",
        lambda *_a, **_k: (1, 2, 3),
    )
    monkeypatch.setattr(
        subject.occurrence_row_v2,
        "_validate_snapshot_and_renders",
        lambda *_a, **_k: None,
    )

    def trial_from(_snapshot, _family, _policy, *, render_snapshots, **_kwargs):
        pages = tuple(render["physical_page"] for render in render_snapshots)
        trial_render_pages.append(pages)
        return {"document_ordinal": 1, "topology_scan": topology_scan, "pages": pages}

    monkeypatch.setattr(subject, "_trial_from_document_store_snapshot_v1", trial_from)
    monkeypatch.setattr(
        subject,
        "_missing_render_pages_for_document_store_trial_v1",
        lambda *_a, **_k: pytest.fail("nonempty preflight repeated the ordinary render pass"),
    )
    monkeypatch.setattr(
        subject,
        "_v4_candidate_scoped_missing_dimension_render_pages",
        lambda trial, *_a, **_k: (3,) if trial["pages"] == (2,) else (),
    )

    result = subject._v4_document_store_preflight_bound_trial_worker_v1(
        (
            packet,
            snapshot,
            family_spec,
            policy,
            renders,
            preflight,
        )
    )

    assert trial_render_pages == [(2,), (2, 3)]
    assert result["trial"]["pages"] == (2, 3)
    assert result["missing_render_pages"] == ()


def test_v4_render_preflight_completes_no_render_trial_without_retaining_context(
    monkeypatch,
) -> None:
    packet, snapshot, _preflight = _render_preflight_fixture()
    snapshot = {
        **snapshot,
        "document_packet": packet,
        "joined_pages": [{"physical_page": 1}],
    }
    prepared = SimpleNamespace(prepared_snapshot=object())
    topology_scan = {"scan_id": "aftv1:scan:" + "d" * 64}
    topology_candidates = {
        "result_id": "aftcv2:result:" + "c" * 64,
        "regions": [{"candidate_id": "candidate-1"}],
    }
    trial = {"document_ordinal": 1, "topology_scan": topology_scan}
    monkeypatch.setattr(subject, "_V4_RENDER_PREFLIGHT_CONTEXT_CACHE", {})
    monkeypatch.setattr(
        subject, "_prepare_v4_document_store_context_v1", lambda *_a, **_k: prepared
    )
    monkeypatch.setattr(
        subject,
        "_open_prepared_v4_document_store_context_v1",
        lambda *_a, **_k: (snapshot, topology_scan, topology_candidates, (object(),)),
    )
    monkeypatch.setattr(subject, "_v4_prepruning_candidate_render_pages_v1", lambda *_a, **_k: (1,))
    monkeypatch.setattr(subject, "_trial_from_document_store_snapshot_v1", lambda *_a, **_k: trial)
    monkeypatch.setattr(
        subject,
        "_missing_render_pages_for_document_store_trial_v1",
        lambda *_a, **_k: (),
    )

    result = subject._v4_document_store_render_preflight_worker_v1(
        (packet, snapshot, _family_spec(), {"format_version": subject.EVALUATION_SPEC_FORMAT_V4})
    )

    assert result["render_pages"] == ()
    assert result["completed_result"]["trial"] is trial
    assert subject._V4_RENDER_PREFLIGHT_CONTEXT_CACHE == {}


def test_v4_render_preflight_reveals_only_base_trial_missing_page(monkeypatch) -> None:
    packet, snapshot, _preflight = _render_preflight_fixture()
    snapshot = {
        **snapshot,
        "document_packet": packet,
        "joined_pages": [{"physical_page": page} for page in (1, 2, 3)],
    }
    prepared = SimpleNamespace(prepared_snapshot=object())
    topology_scan = {"scan_id": "aftv1:scan:" + "d" * 64}
    topology_candidates = {
        "result_id": "aftcv2:result:" + "c" * 64,
        "regions": [{"candidate_id": "candidate-1"}],
    }
    monkeypatch.setattr(subject, "_V4_RENDER_PREFLIGHT_CONTEXT_CACHE", {})
    monkeypatch.setattr(
        subject, "_prepare_v4_document_store_context_v1", lambda *_a, **_k: prepared
    )
    monkeypatch.setattr(
        subject,
        "_open_prepared_v4_document_store_context_v1",
        lambda *_a, **_k: (snapshot, topology_scan, topology_candidates, (object(),)),
    )
    monkeypatch.setattr(
        subject, "_v4_prepruning_candidate_render_pages_v1", lambda *_a, **_k: (1, 2, 3)
    )
    monkeypatch.setattr(
        subject,
        "_trial_from_document_store_snapshot_v1",
        lambda *_a, **_k: {"document_ordinal": 1, "topology_scan": topology_scan},
    )
    monkeypatch.setattr(
        subject,
        "_missing_render_pages_for_document_store_trial_v1",
        lambda *_a, **_k: (2,),
    )

    result = subject._v4_document_store_render_preflight_worker_v1(
        (packet, snapshot, _family_spec(), {"format_version": subject.EVALUATION_SPEC_FORMAT_V4})
    )

    assert result["render_pages"] == (2,)
    assert result["reservoir_pages"] == (1, 2, 3)
    assert result["completed_result"] is None
    assert set(subject._V4_RENDER_PREFLIGHT_CONTEXT_CACHE) == {result["preflight_id"]}


def test_parallel_v4_document_store_trials_preserve_order_and_render_only_requests(
    monkeypatch,
) -> None:
    _disable_v4_trial_checkpoints(monkeypatch)
    documents = _documents()
    snapshots = tuple(
        _authenticated_selected_document_store_snapshot(documents[ordinal]) for ordinal in (1, 2)
    )
    packets = tuple(snapshot["document_packet"] for snapshot in snapshots)
    selections = tuple(
        (
            packet["document_ordinal"],
            tuple(range(1, packet["page_count"] + 1)),
        )
        for packet in packets
    )
    calls = {"executor": [], "renders": [], "selected": []}

    class SynchronousExecutor:
        def __init__(self, *, max_workers, mp_context):
            calls["executor"].append((max_workers, mp_context.get_start_method()))

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def submit(self, function, request):
            future = Future()
            try:
                future.set_result(function(request))
            except Exception as exc:  # pragma: no cover - production future parity
                future.set_exception(exc)
            return future

    def selected(_cap, *, document_page_selections):
        calls["selected"].append(document_page_selections)
        return tuple(copy.deepcopy(snapshot) for snapshot in snapshots)

    def renders(_cap, *, document_ordinal, physical_pages):
        calls["renders"].append((document_ordinal, physical_pages))
        return tuple(_render(document_ordinal, page) for page in physical_pages)

    def preflight_worker(request):
        packet, _snapshot, _family, _policy = request
        return {
            "render_pages": (1,) if packet["document_ordinal"] == 1 else (),
            "reservoir_pages": (1, 2) if packet["document_ordinal"] == 1 else (),
        }

    def final_worker(request):
        packet, snapshot, _family, _policy, render_axis, _preflight = request
        ordinal = packet["document_ordinal"]
        assert snapshot["snapshot_id"] == snapshots[ordinal - 1]["snapshot_id"]
        return {
            "document_ordinal": ordinal,
            "missing_render_pages": (),
            "packet_id": packet["packet_id"],
            "snapshot_id": snapshot["snapshot_id"],
            "trial": {
                "document_ordinal": ordinal,
                "rendered": bool(render_axis),
                "rendered_pages": [render["physical_page"] for render in render_axis],
            },
        }

    monkeypatch.setattr(subject, "ProcessPoolExecutor", SynchronousExecutor)
    monkeypatch.setattr(subject, "_v4_document_store_render_preflight_worker_v1", preflight_worker)
    monkeypatch.setattr(subject, "_v4_document_store_preflight_bound_trial_worker_v1", final_worker)
    monkeypatch.setattr(
        subject,
        "_validated_v4_document_store_render_preflight_v1",
        lambda value, **_kwargs: value,
    )
    monkeypatch.setattr(
        subject.document_store_v1,
        "read_authenticated_family_first_documents_selected_pages_v1",
        selected,
    )
    monkeypatch.setattr(
        subject.document_store_v1,
        "read_authenticated_family_first_document_page_renders_v1",
        renders,
    )

    trials = subject._parallel_v4_document_store_trials_v1(
        object(),
        packets=packets,
        selections=selections,
        family_spec=_family_spec(),
        policy={"format_version": subject.EVALUATION_SPEC_FORMAT_V4},
        jobs=2,
    )

    assert calls == {
        "executor": [(1, "spawn"), (1, "spawn")],
        "renders": [(1, (1, 2))],
        "selected": [selections],
    }
    assert [trial["document_ordinal"] for trial in trials] == [1, 2]
    assert trials[0]["rendered"] is True
    assert trials[0]["rendered_pages"] == [1, 2]
    assert trials[1]["rendered"] is False


@pytest.mark.parametrize(
    ("document_count", "expected_batch_sizes"),
    [(32, [16, 16]), (140, [16] * 8 + [12])],
)
def test_parallel_v4_document_store_trials_use_sliding_snapshot_window_and_source_order(
    monkeypatch,
    document_count,
    expected_batch_sizes,
) -> None:
    _disable_v4_trial_checkpoints(monkeypatch)
    packets = tuple(
        {
            "document_ordinal": ordinal,
            "packet_id": f"ffdesv1:document:{ordinal:064x}",
            "page_count": 1,
        }
        for ordinal in range(1, document_count + 1)
    )
    snapshots = {
        ordinal: {
            "document_packet": packet,
            "snapshot_id": f"ffdesv1:selected:{ordinal:064x}",
        }
        for ordinal, packet in enumerate(packets, 1)
    }
    selections = tuple((ordinal, (1,)) for ordinal in range(1, document_count + 1))
    batches = []
    pending_sizes = []

    class SynchronousExecutor:
        def __init__(self, *, max_workers, mp_context):
            assert max_workers == 1
            assert mp_context.get_start_method() == "spawn"

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def submit(self, function, request):
            future = Future()
            future.document_ordinal = request[0]["document_ordinal"]
            try:
                future.set_result(function(request))
            except Exception as exc:  # pragma: no cover - production future parity
                future.set_exception(exc)
            return future

    def reverse_wait(futures, *, return_when):
        assert return_when is subject.FIRST_COMPLETED
        pending_sizes.append(len(futures))
        completed = max(futures, key=lambda future: future.document_ordinal)
        return {completed}, set(futures) - {completed}

    def selected(_cap, *, document_page_selections):
        batches.append(document_page_selections)
        return tuple(
            copy.deepcopy(snapshots[ordinal]) for ordinal, _pages in document_page_selections
        )

    def preflight_worker(request):
        packet, _snapshot, _family, _policy = request
        return {"render_pages": (), "reservoir_pages": (), "ordinal": packet["document_ordinal"]}

    def final_worker(request):
        packet, snapshot, _family, _policy, _renders, _preflight = request
        return {
            "document_ordinal": packet["document_ordinal"],
            "missing_render_pages": (),
            "packet_id": packet["packet_id"],
            "snapshot_id": snapshot["snapshot_id"],
            "trial": {
                "document_ordinal": packet["document_ordinal"],
                "topology_scan": {"status": "NO_COMPLETE_TOPOLOGY_REGION"},
            },
        }

    monkeypatch.setattr(subject, "ProcessPoolExecutor", SynchronousExecutor)
    monkeypatch.setattr(subject, "wait", reverse_wait)
    monkeypatch.setattr(subject, "_v4_document_store_render_preflight_worker_v1", preflight_worker)
    monkeypatch.setattr(subject, "_v4_document_store_preflight_bound_trial_worker_v1", final_worker)
    monkeypatch.setattr(
        subject,
        "_validated_v4_document_store_render_preflight_v1",
        lambda value, **_kwargs: value,
    )
    monkeypatch.setattr(
        subject.document_store_v1,
        "read_authenticated_family_first_documents_selected_pages_v1",
        selected,
    )

    trials = subject._parallel_v4_document_store_trials_v1(
        object(),
        packets=packets,
        selections=selections,
        family_spec=_family_spec(),
        policy={"format_version": subject.EVALUATION_SPEC_FORMAT_V4},
        jobs=16,
    )

    assert [len(batch) for batch in batches] == expected_batch_sizes
    assert max(pending_sizes) <= 16
    assert [trial["document_ordinal"] for trial in trials] == list(range(1, document_count + 1))


def test_parallel_v4_document_store_trials_submit_retry_before_refilling_source_tail(
    monkeypatch,
) -> None:
    _disable_v4_trial_checkpoints(monkeypatch)
    packets = tuple(
        {
            "document_ordinal": ordinal,
            "packet_id": f"ffdesv1:document:{ordinal:064x}",
            "page_count": 1,
        }
        for ordinal in range(1, 34)
    )
    snapshots = {
        ordinal: {
            "document_packet": packet,
            "snapshot_id": f"ffdesv1:selected:{ordinal:064x}",
        }
        for ordinal, packet in enumerate(packets, 1)
    }
    selections = tuple((ordinal, (1,)) for ordinal in range(1, 34))
    selected_batch_sizes = []
    submission_events = []
    sequence = 0

    class SynchronousExecutor:
        def __init__(self, *, max_workers, mp_context):
            assert max_workers == 1
            assert mp_context.get_start_method() == "spawn"

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def submit(self, function, request):
            nonlocal sequence
            sequence += 1
            packet = request[0]
            stage = "PREFLIGHT" if len(request) == 4 else "FINAL"
            submission_events.append((packet["document_ordinal"], stage))
            future = Future()
            future.sequence = sequence
            try:
                future.set_result(function(request))
            except Exception as exc:  # pragma: no cover - production future parity
                future.set_exception(exc)
            return future

    def fifo_wait(futures, *, return_when):
        assert return_when is subject.FIRST_COMPLETED
        completed = min(futures, key=lambda future: future.sequence)
        return {completed}, set(futures) - {completed}

    def selected(_cap, *, document_page_selections):
        selected_batch_sizes.append(len(document_page_selections))
        return tuple(
            copy.deepcopy(snapshots[ordinal]) for ordinal, _pages in document_page_selections
        )

    def preflight_worker(request):
        packet, _snapshot, _family, _policy = request
        return {"render_pages": (), "reservoir_pages": (), "ordinal": packet["document_ordinal"]}

    def final_worker(request):
        packet, snapshot, _family, _policy, _renders, _preflight = request
        ordinal = packet["document_ordinal"]
        return {
            "document_ordinal": ordinal,
            "missing_render_pages": (),
            "packet_id": packet["packet_id"],
            "snapshot_id": snapshot["snapshot_id"],
            "trial": {
                "document_ordinal": ordinal,
                "topology_scan": {"scan_id": f"scan-{ordinal}"},
            },
        }

    monkeypatch.setattr(subject, "ProcessPoolExecutor", SynchronousExecutor)
    monkeypatch.setattr(subject, "wait", fifo_wait)
    monkeypatch.setattr(subject, "_v4_document_store_render_preflight_worker_v1", preflight_worker)
    monkeypatch.setattr(subject, "_v4_document_store_preflight_bound_trial_worker_v1", final_worker)
    monkeypatch.setattr(
        subject,
        "_validated_v4_document_store_render_preflight_v1",
        lambda value, **_kwargs: value,
    )
    monkeypatch.setattr(
        subject.document_store_v1,
        "read_authenticated_family_first_documents_selected_pages_v1",
        selected,
    )
    monkeypatch.setattr(
        subject.document_store_v1,
        "read_authenticated_family_first_document_page_renders_v1",
        lambda _cap, *, document_ordinal, physical_pages: (
            _render(document_ordinal, physical_pages[0]),
        ),
    )

    trials = subject._parallel_v4_document_store_trials_v1(
        object(),
        packets=packets,
        selections=selections,
        family_spec=_family_spec(),
        policy={"format_version": subject.EVALUATION_SPEC_FORMAT_V4},
        jobs=16,
    )

    assert selected_batch_sizes == [16, 16, 1]
    assert submission_events.index((1, "FINAL")) < submission_events.index((33, "PREFLIGHT"))
    assert [trial["document_ordinal"] for trial in trials] == list(range(1, 34))


def test_parallel_v4_document_store_trials_execute_in_real_worker_processes(
    monkeypatch,
) -> None:
    _disable_v4_trial_checkpoints(monkeypatch)
    documents = {
        ordinal: _document(
            ordinal,
            [[("Thuyết minh tài sản khác", [30, 20, 430, 42])]],
            100 + ordinal,
        )
        for ordinal in (1, 2)
    }
    snapshots = tuple(
        _authenticated_selected_document_store_snapshot(documents[ordinal]) for ordinal in (1, 2)
    )
    packets = tuple(snapshot["document_packet"] for snapshot in snapshots)
    selections = tuple((packet["document_ordinal"], (1,)) for packet in packets)
    monkeypatch.setattr(
        subject.document_store_v1,
        "read_authenticated_family_first_documents_selected_pages_v1",
        lambda _cap, *, document_page_selections: (
            tuple(copy.deepcopy(snapshot) for snapshot in snapshots)
            if document_page_selections == selections
            else pytest.fail("parallel worker parent requested a different source axis")
        ),
    )
    monkeypatch.setattr(
        subject.document_store_v1,
        "read_authenticated_family_first_document_page_renders_v1",
        lambda *_args, **_kwargs: pytest.fail("NOT_OBSERVED worker requested a render"),
    )

    trials = subject._parallel_v4_document_store_trials_v1(
        object(),
        packets=packets,
        selections=selections,
        family_spec=_family_spec(),
        policy={"format_version": subject.EVALUATION_SPEC_FORMAT_V4},
        jobs=2,
    )
    sequential = [
        subject._document_store_trial_with_render_rescue_v1(
            object(),
            packet=packet,
            snapshot=snapshot,
            family_spec=_family_spec(),
            policy={"format_version": subject.EVALUATION_SPEC_FORMAT_V4},
            topology_scan=None,
        )
        for packet, snapshot in zip(packets, snapshots, strict=True)
    ]

    assert [trial["document_ordinal"] for trial in trials] == [1, 2]
    assert [trial["evidence_status"] for trial in trials] == [
        "NOT_OBSERVED_PROPOSAL_ONLY",
        "NOT_OBSERVED_PROPOSAL_ONLY",
    ]
    assert trials == sequential


def test_parallel_v4_document_store_workers_do_not_inherit_store_capabilities() -> None:
    store = subject.document_store_v1
    capability = store.AuthenticatedFamilyFirstDocumentEvidenceStoreV1(store._MINT)  # noqa: SLF001
    store._STORES[capability] = object()  # type: ignore[assignment]  # noqa: SLF001
    try:
        with subject.ProcessPoolExecutor(
            max_workers=1,
            mp_context=subject.get_context("spawn"),
        ) as executor:
            assert executor.submit(_document_store_registry_size_in_spawned_worker).result() == 0
    finally:
        del store._STORES[capability]  # noqa: SLF001


def test_parallel_v4_document_store_worker_exception_is_typed(monkeypatch) -> None:
    _disable_v4_trial_checkpoints(monkeypatch)
    snapshot = _authenticated_selected_document_store_snapshot(_documents()[2])
    packet = snapshot["document_packet"]

    class BrokenExecutor:
        def __init__(self, *, max_workers, mp_context):
            assert max_workers == 1
            assert mp_context.get_start_method() == "spawn"

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def submit(self, *_args, **_kwargs):
            raise RuntimeError("worker died")

    monkeypatch.setattr(subject, "ProcessPoolExecutor", BrokenExecutor)
    monkeypatch.setattr(
        subject.document_store_v1,
        "read_authenticated_family_first_documents_selected_pages_v1",
        lambda *_args, **_kwargs: (snapshot,),
    )

    with pytest.raises(
        subject.FamilyFirstAccountingEvidenceSweepV1Error,
        match="worker execution failed",
    ):
        subject._parallel_v4_document_store_trials_v1(
            object(),
            packets=(packet,),
            selections=((packet["document_ordinal"], (1,)),),
            family_spec=_family_spec(),
            policy={"format_version": subject.EVALUATION_SPEC_FORMAT_V4},
            jobs=2,
        )


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


def test_document_store_v4_render_topology_handoff_avoids_second_snapshot_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _authenticated_selected_document_store_snapshot(_documents()[2])
    packet = snapshot["document_packet"]
    family_spec = _family_spec()
    policy = {"format_version": subject.EVALUATION_SPEC_FORMAT_V4}
    original_open = subject._open_prepared_v4_document_store_context_v1
    full_open_count = 0

    def counted_open(*args: object, **kwargs: object):
        nonlocal full_open_count
        full_open_count += 1
        return original_open(*args, **kwargs)

    monkeypatch.setattr(
        subject,
        "_open_prepared_v4_document_store_context_v1",
        counted_open,
    )
    trial = subject._document_store_trial_with_render_rescue_v1(
        object(),
        packet=packet,
        snapshot=snapshot,
        family_spec=family_spec,
        policy=policy,
        topology_scan=None,
    )

    assert trial["evidence_status"] == "NOT_OBSERVED_PROPOSAL_ONLY"
    assert full_open_count == 1

    runtime_context: dict[str, object] = {}
    trial = subject._trial_from_document_store_snapshot_v1(
        snapshot,
        family_spec,
        policy,
        expected_packet=packet,
        _v4_runtime_context=runtime_context,
    )
    handoff = runtime_context["render_topology_handoff"]
    runtime_context["render_topology_handoff"] = replace(
        handoff,
        topology_candidates_id="aftcv2:result:" + "0" * 64,
    )
    with pytest.raises(
        subject.FamilyFirstAccountingEvidenceSweepV1Error,
        match="render-topology source binding drifted",
    ):
        subject._open_prepared_v4_render_topology_handoff_v1(
            runtime_context["prepared_context"],
            runtime_context["render_topology_handoff"],
            expected_legacy_scan=trial["topology_scan"],
        )


def test_selected_public_replay_defers_only_until_exact_render_is_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replay_calls = []

    def replay(*args: object, **kwargs: object):
        replay_calls.append((args, kwargs))
        return {"receipt": "exact-public-replay"}, []

    monkeypatch.setattr(subject, "_selected_v4_one_edit_authority_v1", replay)
    call = {
        "selected": {"row_axis": {"row_axis_id": "axis"}},
        "joined_pages": [{"lines": [], "page_sequence": 1, "page_width": 1000}],
        "family_spec": {},
        "topology_candidates": {},
        "evaluation_spec": {},
        "prepared_source_exact_axis_cache": {},
        "prepared_public_replay_cache": {},
        "defer_for_render": True,
    }

    assert subject._selected_v4_one_edit_authority_or_defer_for_render_v1(
        **call,
        pending_render_pages=(1,),
    ) == (
        None,
        [subject._SELECTED_PUBLIC_REPLAY_DEFERRED_FOR_RENDER_REASON],
        True,
    )
    assert replay_calls == []

    receipt, reasons, deferred = subject._selected_v4_one_edit_authority_or_defer_for_render_v1(
        **call,
        pending_render_pages=(),
    )
    assert receipt == {"receipt": "exact-public-replay"}
    assert reasons == []
    assert deferred is False
    assert len(replay_calls) == 1


def test_v4_candidate_render_schedule_selects_only_candidate_with_missing_lane() -> None:
    joined_pages = [
        {"lines": [{} for _ in range(10)], "page_sequence": page, "page_width": 1000}
        for page in (1, 2)
    ]
    regions = [
        {
            "cluster_start_document_line_ordinal": 2,
            "cluster_end_document_line_ordinal_exclusive": 8,
        },
        {
            "cluster_start_document_line_ordinal": 12,
            "cluster_end_document_line_ordinal_exclusive": 18,
        },
    ]
    complete_row_axis = {
        "row_axis_id": "afrav1:axis:" + "1" * 64,
        "rows": [
            {
                "label_match": {"page_sequence": 1},
                "missing_column_ordinals": [],
            }
        ],
        "status": "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY",
        "trailing_value_rows": [],
    }
    missing_row_axis = copy.deepcopy(complete_row_axis)
    missing_row_axis["row_axis_id"] = "afrav1:axis:" + "2" * 64
    missing_row_axis["rows"][0]["label_match"]["page_sequence"] = 2
    missing_row_axis["trailing_value_rows"] = [{"missing_column_ordinals": [0], "page_sequence": 2}]
    candidates = [
        {
            "candidate_ordinal": 0,
            "reasons": [],
            "row_axis": complete_row_axis,
        },
        {
            "candidate_ordinal": 1,
            "reasons": ["COLUMN_CONTEXT_ERROR:unresolved lane kind"],
            "row_axis": missing_row_axis,
        },
    ]
    topology_scan = {"scan_id": "aftv1:scan:" + "3" * 64, "regions": regions[1:]}
    topology_candidates = {
        "regions": regions,
        "result_id": "aftcv2:result:" + "4" * 64,
        "status": "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS",
    }

    prepared = subject._prepare_v4_candidate_render_schedule_v1(
        candidates,
        topology_scan=topology_scan,
        topology_candidates=topology_candidates,
        joined_pages=joined_pages,
        evaluation_spec={"format_version": subject.EVALUATION_SPEC_FORMAT_V4},
    )
    assert prepared.render_pages == (2,)
    assert subject._open_prepared_v4_candidate_render_schedule_v1(
        prepared,
        topology_scan=topology_scan,
        topology_candidates=topology_candidates,
        joined_pages=joined_pages,
    ) == (2,)

    with pytest.raises(
        subject.FamilyFirstAccountingEvidenceSweepV1Error,
        match="render schedule binding drifted",
    ):
        subject._open_prepared_v4_candidate_render_schedule_v1(
            replace(prepared, render_pages=(1, 2)),
            topology_scan=topology_scan,
            topology_candidates=topology_candidates,
            joined_pages=joined_pages,
        )


def test_v4_candidate_occurrence_cache_reuses_only_identical_local_render_axis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    built = []

    def build(*args: object, **kwargs: object):
        built.append((args, kwargs))
        return {
            "occurrence_axis_id": f"aforav2:axis:{len(built):064x}",
            "value": len(built),
        }

    monkeypatch.setattr(
        subject.occurrence_row_v2,
        "_build_accounting_family_occurrence_row_axis_from_authenticated_topology_scan_v2",
        build,
    )
    monkeypatch.setattr(
        subject.occurrence_row_v2,
        "_validate_result",
        lambda value: value,
    )
    cache: dict[str, object] = {}
    call = {
        "joined_pages": [{"lines": [], "page_sequence": 1, "page_width": 1000}],
        "family_spec": {"family_id": "FAMILY"},
        "topology_scan": {"scan_id": "aftv1:scan:" + "1" * 64},
        "topology_region": {
            "cluster_start_document_line_ordinal": 0,
            "cluster_end_document_line_ordinal_exclusive": 1,
        },
        "occurrence_row_axis_policy": {"format_version": "POLICY"},
        "topology_candidates": {"result_id": "aftcv2:result:" + "2" * 64},
        "prepared_topology_binding": SimpleNamespace(prepared_context_sha256="3" * 64),
        "selected_snapshot": {"snapshot_id": "ffdesv1:selected:" + "4" * 64},
        "prepared_snapshot": SimpleNamespace(prepared_context_sha256="5" * 64),
        "prepared_source_exact_axis_cache": {},
        "prepared_candidate_occurrence_axis_cache": cache,
    }

    first = subject._build_or_reopen_candidate_occurrence_axis_v1(
        **call,
        render_snapshots=(),
    )
    second = subject._build_or_reopen_candidate_occurrence_axis_v1(
        **call,
        render_snapshots=(),
    )
    assert second == first
    assert len(built) == 1

    render = {
        "physical_page": 1,
        "render_id": "ffaprv1:render:" + "6" * 64,
        "render_ref": {"sha256": "7" * 64, "size_bytes": 10},
    }
    changed = subject._build_or_reopen_candidate_occurrence_axis_v1(
        **call,
        render_snapshots=(render,),
    )
    assert changed["value"] == 2
    assert len(built) == 2

    first_key = next(iter(cache))
    cache[first_key] = replace(cache[first_key], occurrence_axis_sha256="0" * 64)
    with pytest.raises(
        subject.FamilyFirstAccountingEvidenceSweepV1Error,
        match="occurrence-axis cache content drifted",
    ):
        subject._build_or_reopen_candidate_occurrence_axis_v1(
            **call,
            render_snapshots=(),
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


def _direct_visible_provision_record(
    role: str,
    coefficients: tuple[int, int],
    *,
    parent_role: str,
) -> dict:
    line_ordinal = {
        "TOTAL_INTERBANK_PROVISION": 10,
        "INTERBANK_DEPOSIT_PROVISION": 20,
        "INTERBANK_LOAN_PROVISION": 30,
    }[role]
    occurrence_material = {
        "document_line_ordinal": line_ordinal,
        "end_document_line_ordinal": line_ordinal,
        "page_sequence": 1,
        "role": role,
        "role_occurrence_ordinal": 0,
    }
    scope_binding_material = {
        "source_scope_role": parent_role,
        "status": "REVIEWED_EXACT_SOURCE_SCOPE_TO_SCHEMA_ROLE_BINDING",
        "target_role": role,
    }
    values = [
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
    source_values = []
    for value in values:
        ordinal = value["column_ordinal"]
        coefficient = value["number"]["coefficient"]
        raw_prediction = "-" if coefficient == 0 else f"({abs(coefficient)})"
        source_values.append(
            {
                "bbox": [
                    600 + ordinal * 200,
                    line_ordinal * 10,
                    680 + ordinal * 200,
                    line_ordinal * 10 + 20,
                ],
                "column_center": float(640 + ordinal * 200),
                "column_ordinal": ordinal,
                "crop_ref": _ref(1_000 + line_ordinal * 10 + ordinal),
                "line_ordinal": line_ordinal + ordinal,
                "page_sequence": 1,
                "parsed_token": subject.parse_visible_financial_numeric_token_v1(raw_prediction),
                "raw_prediction": raw_prediction,
                "reader_score": 1.0,
                "row_affinity": 1.0,
                "sample_id": f"sample:{role}:{ordinal}",
            }
        )
    return {
        "component_roles": [],
        "resolution_kind": "VISIBLE_SOURCE_ROLE",
        "role": role,
        "source": {
            "kind": "ROLE_ROW",
            "record": {
                "label_match": {
                    "document_line_ordinal": line_ordinal,
                    "end_document_line_ordinal": line_ordinal,
                    "match_kind": "EXACT_ACCENTLESS_ALIAS",
                    "occurrence_id": (
                        "aforav2:occurrence:" + canonical_json_sha256_v1(occurrence_material)
                    ),
                    "page_sequence": 1,
                    "role": role,
                    "role_kind": "ADDITIVE_CHILD",
                    "role_occurrence_ordinal": 0,
                    "scope_owner_occurrence_id": f"aforav2:owner:{parent_role.lower()}",
                    "scope_owner_role": None if parent_role == "FAMILY" else parent_role,
                    "source_scope_binding": {
                        **scope_binding_material,
                        "binding_id": (
                            "aforav2:scope-binding:"
                            + canonical_json_sha256_v1(scope_binding_material)
                        ),
                    },
                },
                "missing_column_ordinals": [],
                "role": role,
                "role_kind": "ADDITIVE_CHILD",
                "status": "VISIBLE_VALUE_LANES_BOUND",
                "values": source_values,
            },
        },
        "values": values,
    }


def _v4_occurrence_label(
    role: str,
    *,
    line_ordinal: int,
    root_occurrence_id: str,
) -> dict:
    material = {
        "document_line_ordinal": line_ordinal,
        "end_document_line_ordinal": line_ordinal,
        "page_sequence": 1,
        "role": role,
        "role_occurrence_ordinal": 0,
    }
    return {
        **material,
        "match_kind": "EXACT_ACCENTLESS_ALIAS",
        "occurrence_id": "aforav2:occurrence:" + canonical_json_sha256_v1(material),
        "role_kind": "STRUCTURAL_GROUP",
        "scope_owner_occurrence_id": root_occurrence_id,
        "scope_owner_role": None,
    }


def _v4_role_occurrence(label: dict, *, has_bound_value_row: bool) -> dict:
    return {
        "has_bound_value_row": has_bound_value_row,
        "label_match": copy.deepcopy(label),
        "occurrence_id": label["occurrence_id"],
        "role": label["role"],
        "role_kind": label["role_kind"],
        "scope_owner_occurrence_id": label["scope_owner_occurrence_id"],
        "scope_owner_role": label["scope_owner_role"],
        "source_scope_binding": copy.deepcopy(label.get("source_scope_binding")),
    }


def _v4_reseal_candidate_envelopes(candidate: dict) -> None:
    row_axis = candidate["row_axis"]
    row_material = copy.deepcopy(row_axis)
    row_material.pop("row_axis_id", None)
    row_axis["row_axis_id"] = "afrav1:axis:" + canonical_json_sha256_v1(row_material)
    closure = candidate["additive_closure"]
    closure["row_axis_id"] = row_axis["row_axis_id"]
    closure_material = copy.deepcopy(closure)
    closure_material.pop("closure_id", None)
    closure["closure_id"] = "ashtcv2:closure:" + canonical_json_sha256_v1(closure_material)


def _v4_seal_candidate_axes(candidate: dict) -> None:
    closure = candidate["additive_closure"]
    provision_records = [
        record
        for record in closure["resolved_roles"]
        if record["role"]
        in {
            "TOTAL_INTERBANK_PROVISION",
            "INTERBANK_DEPOSIT_PROVISION",
            "INTERBANK_LOAN_PROVISION",
        }
    ]
    root_material = {
        "candidate_ordinal": candidate["candidate_ordinal"],
        "provision_roles": [record["role"] for record in provision_records],
    }
    root_occurrence_id = "aforav2:root:" + canonical_json_sha256_v1(root_material)
    split = any(record["role"] != "TOTAL_INTERBANK_PROVISION" for record in provision_records)
    parent_lines = (
        {"INTERBANK_DEPOSIT_GROUP": 10, "INTERBANK_LOAN_GROUP": 25}
        if split
        else {"INTERBANK_DEPOSIT_GROUP": 2, "INTERBANK_LOAN_GROUP": 5}
    )
    parent_labels = {
        role: _v4_occurrence_label(
            role,
            line_ordinal=line_ordinal,
            root_occurrence_id=root_occurrence_id,
        )
        for role, line_ordinal in parent_lines.items()
    }
    for record in provision_records:
        label = record["source"]["record"]["label_match"]
        parent_role = (
            "FAMILY"
            if record["role"] == "TOTAL_INTERBANK_PROVISION"
            else {
                "INTERBANK_DEPOSIT_PROVISION": "INTERBANK_DEPOSIT_GROUP",
                "INTERBANK_LOAN_PROVISION": "INTERBANK_LOAN_GROUP",
            }[record["role"]]
        )
        label["scope_owner_occurrence_id"] = (
            root_occurrence_id
            if parent_role == "FAMILY"
            else parent_labels[parent_role]["occurrence_id"]
        )

    candidate["row_axis"] = {
        "family_id": closure["family_id"],
        "rows": [copy.deepcopy(record["source"]["record"]) for record in provision_records],
        "status": "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY",
    }
    role_occurrences = [
        _v4_role_occurrence(label, has_bound_value_row=False) for label in parent_labels.values()
    ]
    role_occurrences.extend(
        _v4_role_occurrence(record["source"]["record"]["label_match"], has_bound_value_row=True)
        for record in provision_records
    )
    numeric_sample_universe = sorted(
        (
            subject.occurrence_row_v2._numeric_universe_record(
                value,
                owner_kind="ROLE_OCCURRENCE",
                owner_id=record["source"]["record"]["label_match"]["occurrence_id"],
            )
            for record in provision_records
            for value in record["source"]["record"]["values"]
        ),
        key=lambda sample: (
            sample["page_sequence"],
            sample["line_ordinal"],
            sample["column_ordinal"],
            sample["sample_id"],
        ),
    )
    coverage_receipt = []
    for record in provision_records:
        source_record = record["source"]["record"]
        occurrence_id = source_record["label_match"]["occurrence_id"]
        coverage_receipt.append(
            {
                "candidate_ordinal": None,
                "coverage_id": f"ashtcv2:coverage:role:{occurrence_id}",
                "disposition": "GLOBAL_HIERARCHY_SOURCE_OCCURRENCE",
                "occurrence_id": occurrence_id,
                "role": record["role"],
                "row_kind": "ROLE_ROW",
                "sample_ids": [value["sample_id"] for value in source_record["values"]],
                "source_record": copy.deepcopy(source_record),
            }
        )
    occurrence_axis_material = {
        "family_id": closure["family_id"],
        "numeric_sample_universe": numeric_sample_universe,
        "role_occurrences": role_occurrences,
    }
    occurrence_axis_id = "aforav2:axis:" + canonical_json_sha256_v1(occurrence_axis_material)
    closure.update(
        {
            "coverage_receipt": coverage_receipt,
            "dependency_content_refs": subject.scoped_v2._dependency_refs(),
            "numeric_sample_universe": numeric_sample_universe,
            "occurrence_axis_binding": {
                "dependency_content_refs": subject.occurrence_row_v2._dependency_refs(),
                "occurrence_axis_id": occurrence_axis_id,
                "topology_candidates_id": "aftcv2:result:" + "1" * 64,
                "topology_scan_id": "aftv1:scan:" + "2" * 64,
            },
            "occurrence_axis_id": occurrence_axis_id,
            "role_occurrences": role_occurrences,
            "status": "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO",
        }
    )
    _v4_reseal_candidate_envelopes(candidate)


def _v4_direct_visible_test_record(
    role: str,
    coefficients: tuple[int, int],
    *,
    line_ordinal: int,
    role_kind: str,
) -> dict:
    occurrence_material = {
        "document_line_ordinal": line_ordinal,
        "end_document_line_ordinal": line_ordinal,
        "page_sequence": 1,
        "role": role,
        "role_occurrence_ordinal": 0,
    }
    label = {
        **occurrence_material,
        "match_kind": "EXACT_ACCENTLESS_ALIAS",
        "occurrence_id": "aforav2:occurrence:" + canonical_json_sha256_v1(occurrence_material),
        "role_kind": role_kind,
        "scope_owner_occurrence_id": "aforav2:root:unsealed",
        "scope_owner_role": None,
    }
    source_values = []
    resolved_values = []
    for ordinal, coefficient in enumerate(coefficients):
        raw_prediction = str(coefficient)
        sample = line_ordinal * 10 + ordinal
        parsed = subject.parse_visible_financial_numeric_token_v1(raw_prediction)
        source_values.append(
            {
                "bbox": [600 + ordinal * 200, line_ordinal, 680 + ordinal * 200, line_ordinal + 20],
                "column_center": float(640 + ordinal * 200),
                "column_ordinal": ordinal,
                "crop_ref": _ref(sample),
                "line_ordinal": line_ordinal + ordinal,
                "page_sequence": 1,
                "parsed_token": parsed,
                "raw_prediction": raw_prediction,
                "reader_score": 1.0,
                "row_affinity": 1.0,
                "sample_id": f"sample:{role}:{ordinal}",
            }
        )
        resolved_values.append(
            {
                "column_ordinal": ordinal,
                "number": {
                    "coefficient": coefficient,
                    "percentage_mark_present": False,
                    "scale": 0,
                },
            }
        )
    return {
        "component_roles": [],
        "resolution_kind": "VISIBLE_SOURCE_ROLE",
        "role": role,
        "source": {
            "kind": "ROLE_ROW",
            "record": {
                "label_match": label,
                "missing_column_ordinals": [],
                "role": role,
                "role_kind": role_kind,
                "status": "VISIBLE_VALUE_LANES_BOUND",
                "values": source_values,
            },
        },
        "values": resolved_values,
    }


def _v4_seal_generic_visible_axes(
    candidate: dict,
    *,
    parent_roles: dict[str, str],
) -> None:
    closure = candidate["additive_closure"]
    family_id = closure["family_id"]
    visible_records = [
        record
        for record in closure["resolved_roles"]
        if type(record.get("source")) is dict and type(record["source"].get("record")) is dict
    ]
    root_material = {
        "candidate_ordinal": candidate["candidate_ordinal"],
        "family_id": family_id,
        "visible_roles": [record["role"] for record in visible_records],
    }
    root_occurrence_id = "aforav2:root:" + canonical_json_sha256_v1(root_material)
    visible_by_role = {record["role"]: record for record in visible_records}
    nested_parent_roles = sorted(
        {parent_roles[record["role"]] for record in visible_records} - {family_id}
    )
    unbound_parent_roles = [role for role in nested_parent_roles if role not in visible_by_role]
    parent_labels = {
        role: _v4_occurrence_label(
            role,
            line_ordinal=5 + ordinal * 30,
            root_occurrence_id=root_occurrence_id,
        )
        for ordinal, role in enumerate(unbound_parent_roles)
    }
    for record in visible_records:
        label = record["source"]["record"]["label_match"]
        parent_role = parent_roles[record["role"]]
        label["scope_owner_occurrence_id"] = (
            root_occurrence_id
            if parent_role == family_id
            else (
                visible_by_role[parent_role]["source"]["record"]["label_match"]["occurrence_id"]
                if parent_role in visible_by_role
                else parent_labels[parent_role]["occurrence_id"]
            )
        )
        label["scope_owner_role"] = None if parent_role == family_id else parent_role

    rows = [copy.deepcopy(record["source"]["record"]) for record in visible_records]
    candidate["row_axis"] = {
        "column_grids": [],
        "family_id": family_id,
        "rows": rows,
        "status": "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY",
        "trailing_value_rows": [],
        "visible_dash_rescues": [],
    }
    role_occurrences = [
        _v4_role_occurrence(label, has_bound_value_row=False) for label in parent_labels.values()
    ] + [
        _v4_role_occurrence(record["source"]["record"]["label_match"], has_bound_value_row=True)
        for record in visible_records
    ]
    numeric_sample_universe = sorted(
        (
            subject.occurrence_row_v2._numeric_universe_record(
                value,
                owner_kind="ROLE_OCCURRENCE",
                owner_id=record["source"]["record"]["label_match"]["occurrence_id"],
            )
            for record in visible_records
            for value in record["source"]["record"]["values"]
        ),
        key=lambda sample: (
            sample["page_sequence"],
            sample["line_ordinal"],
            sample["column_ordinal"],
            sample["sample_id"],
        ),
    )
    coverage_receipt = []
    for record in visible_records:
        source_record = record["source"]["record"]
        occurrence_id = source_record["label_match"]["occurrence_id"]
        coverage_receipt.append(
            {
                "candidate_ordinal": None,
                "coverage_id": f"ashtcv2:coverage:role:{occurrence_id}",
                "disposition": "GLOBAL_HIERARCHY_SOURCE_OCCURRENCE",
                "occurrence_id": occurrence_id,
                "role": record["role"],
                "row_kind": "ROLE_ROW",
                "sample_ids": [value["sample_id"] for value in source_record["values"]],
                "source_record": copy.deepcopy(source_record),
            }
        )
    occurrence_axis_material = {
        "family_id": family_id,
        "numeric_sample_universe": numeric_sample_universe,
        "role_occurrences": role_occurrences,
    }
    occurrence_axis_id = "aforav2:axis:" + canonical_json_sha256_v1(occurrence_axis_material)
    closure.update(
        {
            "authenticated_extreme_margin_furniture_evidence": [],
            "coextensive_structural_numeric_evidence": [],
            "coverage_receipt": coverage_receipt,
            "dependency_content_refs": subject.scoped_v2._dependency_refs(),
            "internal_unassigned_numeric_clusters": [],
            "numeric_sample_universe": numeric_sample_universe,
            "occurrence_axis_binding": {
                "dependency_content_refs": subject.occurrence_row_v2._dependency_refs(),
                "occurrence_axis_id": occurrence_axis_id,
                "topology_candidates_id": "aftcv2:result:" + "1" * 64,
                "topology_scan_id": "aftv1:scan:" + "2" * 64,
            },
            "occurrence_axis_id": occurrence_axis_id,
            "role_occurrences": role_occurrences,
            "status": "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO",
        }
    )
    _v4_reseal_candidate_envelopes(candidate)


def _v4_replace_visible_alias_with_trailing_result(
    candidate: dict,
    *,
    alias_role: str,
    result_role: str,
) -> None:
    """Make a generic fixture mirror a real selected trailing-root receipt."""

    closure = candidate["additive_closure"]
    records = {record["role"]: record for record in closure["resolved_roles"]}
    alias = records[alias_role]
    result = records[result_role]
    alias_source = alias["source"]["record"]
    trailing = {
        "candidate_ordinal": 0,
        "missing_column_ordinals": [],
        "page_sequence": alias_source["label_match"]["page_sequence"],
        "status": "COMPLETE_VISIBLE_TRAILING_VALUE_ROW",
        "values": copy.deepcopy(alias_source["values"]),
    }
    alias_occurrence_id = alias_source["label_match"]["occurrence_id"]
    alias_sample_ids = [value["sample_id"] for value in trailing["values"]]

    closure["resolved_roles"] = [
        record for record in closure["resolved_roles"] if record["role"] != alias_role
    ]
    result["resolution_kind"] = "VISIBLE_TRAILING_TOTAL_CORROBORATED_BY_COMPONENTS"
    result["source"] = {"kind": "TRAILING_VALUE_ROW", "record": copy.deepcopy(trailing)}
    equation = next(
        equation
        for equation in closure["equations"]["global"]
        if equation["result_role"] == result_role
    )
    equation["selected_trailing_candidate_ordinal"] = 0
    equation["trailing_candidate_evidence"] = [
        {
            "candidate_ordinal": 0,
            "sample_ids": alias_sample_ids,
            "source_record": copy.deepcopy(trailing),
            "status": "SELECTED_VISIBLE_TRAILING_ROOT_SOURCE",
        }
    ]

    candidate["row_axis"]["rows"] = [
        row
        for row in candidate["row_axis"]["rows"]
        if row["label_match"]["occurrence_id"] != alias_occurrence_id
    ]
    candidate["row_axis"]["trailing_value_rows"] = [copy.deepcopy(trailing)]
    closure["role_occurrences"] = [
        occurrence
        for occurrence in closure["role_occurrences"]
        if occurrence["occurrence_id"] != alias_occurrence_id
    ]
    closure["numeric_sample_universe"] = [
        sample
        for sample in closure["numeric_sample_universe"]
        if sample["sample_id"] not in alias_sample_ids
    ] + [
        subject.occurrence_row_v2._numeric_universe_record(
            value,
            owner_kind="TRAILING_VALUE_ROW",
            owner_id="aforav2:trailing:0",
        )
        for value in trailing["values"]
    ]
    closure["numeric_sample_universe"].sort(
        key=lambda sample: (
            sample["page_sequence"],
            sample["line_ordinal"],
            sample["column_ordinal"],
            sample["sample_id"],
        )
    )
    closure["coverage_receipt"] = [
        receipt
        for receipt in closure["coverage_receipt"]
        if receipt["occurrence_id"] != alias_occurrence_id
    ] + [
        {
            "candidate_ordinal": 0,
            "coverage_id": "ashtcv2:coverage:trailing:0",
            "disposition": "SELECTED_VISIBLE_TRAILING_ROOT_SOURCE",
            "occurrence_id": None,
            "role": None,
            "row_kind": "TRAILING_VALUE_ROW",
            "sample_ids": alias_sample_ids,
            "source_record": copy.deepcopy(trailing),
        }
    ]
    occurrence_axis_material = {
        "family_id": closure["family_id"],
        "numeric_sample_universe": closure["numeric_sample_universe"],
        "role_occurrences": closure["role_occurrences"],
    }
    occurrence_axis_id = "aforav2:axis:" + canonical_json_sha256_v1(occurrence_axis_material)
    closure["occurrence_axis_id"] = occurrence_axis_id
    closure["occurrence_axis_binding"]["occurrence_axis_id"] = occurrence_axis_id
    _v4_reseal_candidate_envelopes(candidate)


def _v4_visible_summary_and_derived_detail_candidates(
    *,
    detail_deposit: tuple[int, int] = (70, 60),
    detail_loan: tuple[int, int] = (30, 40),
    detail_periods: tuple[str, str] = ("31/12/2025", "31/12/2024"),
    partial_detail_leaf: bool = False,
    wrong_detail_parent: bool = False,
    with_authenticated_nonadditive_child: bool = False,
) -> tuple[dict, dict]:
    summary_deposit = (70, 60)
    summary_loan = (30, 40)
    summary_root = tuple(
        deposit + loan for deposit, loan in zip(summary_deposit, summary_loan, strict=True)
    )
    detail_root = tuple(
        deposit + loan for deposit, loan in zip(detail_deposit, detail_loan, strict=True)
    )

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

    def derived(role: str, coefficients: tuple[int, int], components: list[str]) -> dict:
        return {
            "component_roles": components,
            "resolution_kind": "DERIVED_EXACT_COMPONENT_SUM",
            "role": role,
            "source": None,
            "values": values(coefficients),
        }

    summary_deposit_record = _v4_direct_visible_test_record(
        "DEPOSIT_GROUP", summary_deposit, line_ordinal=20, role_kind="STRUCTURAL_GROUP"
    )
    summary_loan_record = _v4_direct_visible_test_record(
        "LOAN_GROUP", summary_loan, line_ordinal=50, role_kind="STRUCTURAL_GROUP"
    )
    summary = _ready_hierarchical_candidate(
        ["DEPOSIT_GROUP", "LOAN_GROUP", "FAMILY"],
        candidate_ordinal=0,
        coefficients=summary_root,
    )
    summary["additive_closure"]["resolved_roles"] = [
        summary_deposit_record,
        summary_loan_record,
        {
            "component_roles": ["DEPOSIT_GROUP", "LOAN_GROUP"],
            "resolution_kind": "VISIBLE_SOURCE_ROLE_CORROBORATED_BY_COMPONENTS",
            "role": "FAMILY",
            "source": None,
            "values": values(summary_root),
        },
    ]
    summary["additive_closure"]["equations"] = {
        "global": [
            {
                "component_roles_present": [],
                "result_role": "DEPOSIT_GROUP",
                "status": "VISIBLE_SOURCE_ONLY_NO_DECLARED_COMPONENT_VISIBLE",
                "visible_result_roles": ["DEPOSIT_GROUP"],
            },
            {
                "component_roles_present": [],
                "result_role": "LOAN_GROUP",
                "status": "VISIBLE_SOURCE_ONLY_NO_DECLARED_COMPONENT_VISIBLE",
                "visible_result_roles": ["LOAN_GROUP"],
            },
            {
                "component_roles_present": ["DEPOSIT_GROUP", "LOAN_GROUP"],
                "result_role": "FAMILY",
                "status": "VISIBLE_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS",
                "visible_result_roles": ["FAMILY"],
            },
        ],
        "local": [],
    }
    _v4_seal_generic_visible_axes(
        summary,
        parent_roles={"DEPOSIT_GROUP": "FAMILY", "LOAN_GROUP": "FAMILY"},
    )

    deposit_a = (40, 35)
    deposit_b = tuple(total - left for total, left in zip(detail_deposit, deposit_a, strict=True))
    loan_a = (20, 25)
    loan_b = tuple(total - left for total, left in zip(detail_loan, loan_a, strict=True))
    detail_leaf_records = [
        _v4_direct_visible_test_record(
            "DEPOSIT_A", deposit_a, line_ordinal=20, role_kind="ADDITIVE_CHILD"
        ),
        _v4_direct_visible_test_record(
            "DEPOSIT_B", deposit_b, line_ordinal=30, role_kind="ADDITIVE_CHILD"
        ),
        _v4_direct_visible_test_record(
            "LOAN_A", loan_a, line_ordinal=50, role_kind="ADDITIVE_CHILD"
        ),
        _v4_direct_visible_test_record(
            "LOAN_B", loan_b, line_ordinal=60, role_kind="ADDITIVE_CHILD"
        ),
    ]
    if partial_detail_leaf:
        partial = detail_leaf_records[1]
        partial["values"] = partial["values"][:1]
        partial["source"]["record"]["values"] = partial["source"]["record"]["values"][:1]
        partial["source"]["record"]["missing_column_ordinals"] = [1]
        partial["source"]["record"]["status"] = "PARTIAL_VISIBLE_VALUE_ROW"
    detail = _ready_hierarchical_candidate(
        [
            "DEPOSIT_A",
            "DEPOSIT_B",
            "DEPOSIT_GROUP",
            "LOAN_A",
            "LOAN_B",
            "LOAN_GROUP",
            "FAMILY",
        ],
        candidate_ordinal=1,
        coefficients=detail_root,
        periods=detail_periods,
        root_resolution="DERIVED_EXACT_COMPONENT_SUM",
    )
    detail["additive_closure"]["resolved_roles"] = [
        *detail_leaf_records[:2],
        derived("DEPOSIT_GROUP", detail_deposit, ["DEPOSIT_A", "DEPOSIT_B"]),
        *detail_leaf_records[2:],
        derived("LOAN_GROUP", detail_loan, ["LOAN_A", "LOAN_B"]),
        derived("FAMILY", detail_root, ["DEPOSIT_GROUP", "LOAN_GROUP"]),
    ]
    if with_authenticated_nonadditive_child:
        detail["additive_closure"]["resolved_roles"].append(
            _v4_direct_visible_test_record(
                "LOAN_A_MEMO_BREAKDOWN",
                (7, 8),
                line_ordinal=55,
                role_kind="NONADDITIVE_CHILD",
            )
        )
    detail["additive_closure"]["equations"] = {
        "global": [
            {
                "component_roles_present": ["DEPOSIT_A", "DEPOSIT_B"],
                "result_role": "DEPOSIT_GROUP",
                "status": "DERIVED_EXACT_EXHAUSTIVE_COMPONENT_SUM",
                "visible_result_roles": ["DEPOSIT_GROUP"],
            },
            {
                "component_roles_present": ["LOAN_A", "LOAN_B"],
                "result_role": "LOAN_GROUP",
                "status": "DERIVED_EXACT_EXHAUSTIVE_COMPONENT_SUM",
                "visible_result_roles": ["LOAN_GROUP"],
            },
            {
                "component_roles_present": ["DEPOSIT_GROUP", "LOAN_GROUP"],
                "result_role": "FAMILY",
                "status": "DERIVED_EXACT_EXHAUSTIVE_COMPONENT_SUM",
                "visible_result_roles": ["FAMILY"],
            },
        ],
        "local": [],
    }
    parent_roles = {
        "DEPOSIT_A": "LOAN_GROUP" if wrong_detail_parent else "DEPOSIT_GROUP",
        "DEPOSIT_B": "DEPOSIT_GROUP",
        "LOAN_A": "LOAN_GROUP",
        "LOAN_B": "LOAN_GROUP",
    }
    if with_authenticated_nonadditive_child:
        parent_roles["LOAN_A_MEMO_BREAKDOWN"] = "LOAN_A"
    _v4_seal_generic_visible_axes(detail, parent_roles=parent_roles)
    return summary, detail


@pytest.mark.parametrize("with_nonadditive_child", [False, True])
def test_v4_visible_summary_yields_to_authenticated_exact_component_detail(
    with_nonadditive_child: bool,
) -> None:
    summary, detail = _v4_visible_summary_and_derived_detail_candidates(
        with_authenticated_nonadditive_child=with_nonadditive_child
    )
    policy = {
        **_strict_same_population_selection_policy(),
        "format_version": subject.EVALUATION_SPEC_FORMAT_V4,
    }

    selected, reasons = subject._select_candidate_evidence([summary, detail], policy)

    assert selected is detail
    assert reasons == []


@pytest.mark.parametrize(
    "mutation",
    [
        "SHARED_COMPONENT_MISMATCH",
        "COMPENSATING_COMPONENT_MISMATCH",
        "PARTIAL_DETAIL_LANE",
        "ROUNDING_ONLY_ROOT",
        "DIFFERENT_PERIOD",
        "COHERENT_WRONG_PARENT",
        "MISSING_SUMMARY_SOURCE_RECEIPT",
        "ARITHMETIC_ONLY_UNSEALED_DETAIL",
        "ARBITRARY_ADDITIVE_EXTRA_ROLE",
    ],
)
def test_v4_derived_detail_stays_incomparable_without_complete_typed_frontier(
    mutation: str,
) -> None:
    builder_kwargs: dict = {}
    if mutation == "SHARED_COMPONENT_MISMATCH":
        builder_kwargs["detail_deposit"] = (71, 60)
    elif mutation == "COMPENSATING_COMPONENT_MISMATCH":
        builder_kwargs.update(detail_deposit=(71, 60), detail_loan=(29, 40))
    elif mutation == "PARTIAL_DETAIL_LANE":
        builder_kwargs["partial_detail_leaf"] = True
    elif mutation == "DIFFERENT_PERIOD":
        builder_kwargs["detail_periods"] = ("30/06/2025", "31/12/2024")
    elif mutation == "COHERENT_WRONG_PARENT":
        builder_kwargs["wrong_detail_parent"] = True
    summary, detail = _v4_visible_summary_and_derived_detail_candidates(**builder_kwargs)
    if mutation == "ROUNDING_ONLY_ROOT":
        root = next(
            record
            for record in detail["additive_closure"]["resolved_roles"]
            if record["role"] == "FAMILY"
        )
        root["resolution_kind"] = "DERIVED_ROUNDING_COMPONENT_SUM"
        equation = next(
            equation
            for equation in detail["additive_closure"]["equations"]["global"]
            if equation["result_role"] == "FAMILY"
        )
        equation["status"] = "DERIVED_ROUNDING_EXHAUSTIVE_COMPONENT_SUM"
        _v4_reseal_candidate_envelopes(detail)
    elif mutation == "MISSING_SUMMARY_SOURCE_RECEIPT":
        summary["additive_closure"]["coverage_receipt"] = summary["additive_closure"][
            "coverage_receipt"
        ][1:]
        _v4_reseal_candidate_envelopes(summary)
    elif mutation == "ARITHMETIC_ONLY_UNSEALED_DETAIL":
        detail.pop("row_axis")
    elif mutation == "ARBITRARY_ADDITIVE_EXTRA_ROLE":
        detail["additive_closure"]["resolved_roles"].append(
            {
                "component_roles": [],
                "resolution_kind": "DERIVED_EXACT_COMPONENT_SUM",
                "role": "UNRELATED_ADDITIVE_DETAIL",
                "source": None,
                "values": [
                    {
                        "column_ordinal": ordinal,
                        "number": {
                            "coefficient": 0,
                            "percentage_mark_present": False,
                            "scale": 0,
                        },
                    }
                    for ordinal in range(2)
                ],
            }
        )
        _v4_reseal_candidate_envelopes(detail)

    selected, reasons = subject._select_candidate_evidence(
        [summary, detail],
        {
            **_strict_same_population_selection_policy(),
            "format_version": subject.EVALUATION_SPEC_FORMAT_V4,
        },
    )

    assert selected is None
    assert reasons == ["MULTIPLE_DOWNSTREAM_EVIDENCE_COMPLETE_TOPOLOGY_REGIONS"]


def test_v4_duplicate_exact_detail_candidates_preserve_ambiguity() -> None:
    summary, detail = _v4_visible_summary_and_derived_detail_candidates()
    competing = copy.deepcopy(detail)
    competing["candidate_ordinal"] = 2

    selected, reasons = subject._select_candidate_evidence(
        [summary, detail, competing],
        {
            **_strict_same_population_selection_policy(),
            "format_version": subject.EVALUATION_SPEC_FORMAT_V4,
        },
    )

    assert selected is None
    assert reasons == ["MULTIPLE_DOWNSTREAM_EVIDENCE_COMPLETE_TOPOLOGY_REGIONS"]


def _v4_visible_summary_and_correlated_detail_candidates(
    *,
    adjustment_axis: tuple[int, int] = (0, 0),
    adjustment_role: str = "INTERBANK_LOAN_PROVISION",
    nested_discount: bool = False,
    off_frontier_row: bool = False,
    partial_provision: bool = False,
    root_scoped_demand_line: int = 5,
    root_scoped_term_line: int = 30,
    root_adjustment: bool = False,
    same_role_group_sources: bool = False,
    trailing_detail_root: bool = False,
    wrong_provision_parent: bool = False,
) -> tuple[dict, dict]:
    family = "INTERBANK_DEPOSITS_AND_LOANS"
    deposit = "INTERBANK_DEPOSIT_GROUP"
    loan = "INTERBANK_LOAN_GROUP"
    demand = "DEMAND_DEPOSIT_GROUP"
    term = "TERM_DEPOSIT_GROUP"
    provision = adjustment_role
    root_adjustment_role = "ROOT_LEVEL_ADJUSTMENT"
    root_axis = (100, 100)
    deposit_axis = (70, 60)
    loan_axis = (30, 40)
    loan_direct_axis = tuple(
        total - adjustment for total, adjustment in zip(loan_axis, adjustment_axis, strict=True)
    )

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

    def result_record(
        role: str,
        coefficients: tuple[int, int],
        components: list[str],
        *,
        resolution_kind: str,
    ) -> dict:
        return {
            "component_roles": components,
            "resolution_kind": resolution_kind,
            "role": role,
            "source": None,
            "values": values(coefficients),
        }

    context = _ready_hierarchical_candidate(
        ["FAMILY"],
        candidate_ordinal=0,
        coefficients=root_axis,
    )["column_context"]

    summary_deposit = _v4_direct_visible_test_record(
        deposit,
        deposit_axis,
        line_ordinal=20,
        role_kind="STRUCTURAL_GROUP",
    )
    summary_loan = _v4_direct_visible_test_record(
        loan,
        loan_axis,
        line_ordinal=50,
        role_kind="STRUCTURAL_GROUP",
    )
    summary_root_alias = _v4_direct_visible_test_record(
        "EXPLICIT_FAMILY_TOTAL",
        root_axis,
        line_ordinal=80,
        role_kind="TOTAL",
    )
    summary_root = result_record(
        family,
        root_axis,
        [deposit, loan, *([root_adjustment_role] if root_adjustment else [])],
        resolution_kind="VISIBLE_SOURCE_ROLE_CORROBORATED_BY_COMPONENTS",
    )
    summary_adjustment = (
        _v4_direct_visible_test_record(
            root_adjustment_role,
            (0, 0),
            line_ordinal=60,
            role_kind="ADDITIVE_CHILD",
        )
        if root_adjustment
        else None
    )
    summary = {
        "additive_closure": {
            "equations": {
                "global": [
                    {
                        "component_roles_present": [],
                        "result_role": deposit,
                        "status": "VISIBLE_SOURCE_ONLY_NO_DECLARED_COMPONENT_VISIBLE",
                        "visible_result_roles": [deposit],
                    },
                    {
                        "component_roles_present": [],
                        "result_role": loan,
                        "status": "VISIBLE_SOURCE_ONLY_NO_DECLARED_COMPONENT_VISIBLE",
                        "visible_result_roles": [loan],
                    },
                    {
                        "component_roles_present": [
                            deposit,
                            loan,
                            *([root_adjustment_role] if root_adjustment else []),
                        ],
                        "result_role": family,
                        "status": "VISIBLE_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS",
                        "visible_result_roles": ["EXPLICIT_FAMILY_TOTAL"],
                    },
                ],
                "local": [],
            },
            "family_id": family,
            "resolved_roles": [
                summary_deposit,
                summary_loan,
                *([summary_adjustment] if summary_adjustment is not None else []),
                summary_root_alias,
                summary_root,
            ],
        },
        "candidate_ordinal": 0,
        "column_context": copy.deepcopy(context),
        "reasons": [],
    }
    _v4_seal_generic_visible_axes(
        summary,
        parent_roles={
            deposit: family,
            loan: family,
            **({root_adjustment_role: family} if root_adjustment else {}),
            "EXPLICIT_FAMILY_TOTAL": family,
        },
    )
    summary_root["source"] = copy.deepcopy(summary_root_alias["source"])
    _v4_reseal_candidate_envelopes(summary)

    visible_records = [
        _v4_direct_visible_test_record(
            "DEMAND_DEPOSIT_VND",
            (40, 30),
            line_ordinal=10,
            role_kind="ADDITIVE_CHILD",
        ),
        _v4_direct_visible_test_record(
            "DEMAND_DEPOSIT_FOREIGN_CURRENCY",
            (10, 10),
            line_ordinal=20,
            role_kind="ADDITIVE_CHILD",
        ),
        _v4_direct_visible_test_record(
            "TERM_DEPOSIT_VND",
            (15, 15),
            line_ordinal=40 if same_role_group_sources else 100,
            role_kind="ADDITIVE_CHILD",
        ),
        _v4_direct_visible_test_record(
            "TERM_DEPOSIT_FOREIGN_CURRENCY",
            (5, 5),
            line_ordinal=50 if same_role_group_sources else 110,
            role_kind="ADDITIVE_CHILD",
        ),
        _v4_direct_visible_test_record(
            "INTERBANK_LOAN_VND",
            loan_direct_axis,
            line_ordinal=70,
            role_kind="ADDITIVE_CHILD",
        ),
        _v4_direct_visible_test_record(
            "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND",
            (7, 8),
            line_ordinal=75,
            role_kind="NONADDITIVE_CHILD",
        ),
        _v4_direct_visible_test_record(
            provision,
            adjustment_axis,
            line_ordinal=80,
            role_kind="ADDITIVE_CHILD",
        ),
        *(
            []
            if same_role_group_sources
            else [
                _v4_direct_visible_test_record(
                    "EXPLICIT_INTERBANK_DEPOSIT_TOTAL",
                    deposit_axis,
                    line_ordinal=120,
                    role_kind="TOTAL",
                ),
                _v4_direct_visible_test_record(
                    "EXPLICIT_INTERBANK_LOAN_TOTAL",
                    loan_axis,
                    line_ordinal=90,
                    role_kind="TOTAL",
                ),
            ]
        ),
        _v4_direct_visible_test_record(
            "EXPLICIT_FAMILY_TOTAL",
            root_axis,
            line_ordinal=130,
            role_kind="TOTAL",
        ),
    ]
    if partial_provision:
        provision_record = next(record for record in visible_records if record["role"] == provision)
        provision_record["source"]["record"]["status"] = "PARTIAL_VISIBLE_VALUE_ROW"
        provision_record["source"]["record"]["missing_column_ordinals"] = [1]
    if off_frontier_row:
        visible_records.append(
            _v4_direct_visible_test_record(
                "UNRELATED_ZERO_ADDITIVE_ROW",
                (0, 0),
                line_ordinal=85,
                role_kind="ADDITIVE_CHILD",
            )
        )
    if nested_discount:
        visible_records.append(
            _v4_direct_visible_test_record(
                "NESTED_DISCOUNT_MEMO",
                (1, 1),
                line_ordinal=78,
                role_kind="NONADDITIVE_CHILD",
            )
        )
    if root_adjustment:
        visible_records.append(
            _v4_direct_visible_test_record(
                root_adjustment_role,
                (0, 0),
                line_ordinal=125,
                role_kind="ADDITIVE_CHILD",
            )
        )

    derived_records = [
        result_record(
            demand,
            (50, 40),
            ["DEMAND_DEPOSIT_VND", "DEMAND_DEPOSIT_FOREIGN_CURRENCY"],
            resolution_kind="DERIVED_EXACT_COMPONENT_SUM",
        ),
        result_record(
            term,
            (20, 20),
            ["TERM_DEPOSIT_VND", "TERM_DEPOSIT_FOREIGN_CURRENCY"],
            resolution_kind="DERIVED_EXACT_COMPONENT_SUM",
        ),
        result_record(
            deposit,
            deposit_axis,
            [demand, term],
            resolution_kind="VISIBLE_SOURCE_ROLE_CORROBORATED_BY_COMPONENTS",
        ),
        result_record(
            loan,
            loan_axis,
            ["INTERBANK_LOAN_VND", provision],
            resolution_kind="VISIBLE_SOURCE_ROLE_CORROBORATED_BY_COMPONENTS",
        ),
        result_record(
            family,
            root_axis,
            [deposit, loan, *([root_adjustment_role] if root_adjustment else [])],
            resolution_kind="VISIBLE_SOURCE_ROLE_CORROBORATED_BY_COMPONENTS",
        ),
    ]
    if same_role_group_sources:
        for role, coefficients, line_ordinal in (
            (deposit, deposit_axis, 1),
            (demand, (50, 40), root_scoped_demand_line),
            (term, (20, 20), root_scoped_term_line),
            (loan, loan_axis, 60),
        ):
            result = next(record for record in derived_records if record["role"] == role)
            source = _v4_direct_visible_test_record(
                role,
                coefficients,
                line_ordinal=line_ordinal,
                role_kind="STRUCTURAL_GROUP",
            )
            result["source"] = source["source"]
            result["resolution_kind"] = "VISIBLE_SOURCE_ROLE_CORROBORATED_BY_COMPONENTS"
    detail = {
        "additive_closure": {
            "equations": {
                "global": [
                    {
                        "component_roles_present": [
                            "DEMAND_DEPOSIT_VND",
                            "DEMAND_DEPOSIT_FOREIGN_CURRENCY",
                        ],
                        "result_role": demand,
                        "status": (
                            "VISIBLE_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS"
                            if same_role_group_sources
                            else "DERIVED_EXACT_EXHAUSTIVE_COMPONENT_SUM"
                        ),
                        "visible_result_roles": [demand],
                    },
                    {
                        "component_roles_present": [
                            "TERM_DEPOSIT_VND",
                            "TERM_DEPOSIT_FOREIGN_CURRENCY",
                        ],
                        "result_role": term,
                        "status": (
                            "VISIBLE_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS"
                            if same_role_group_sources
                            else "DERIVED_EXACT_EXHAUSTIVE_COMPONENT_SUM"
                        ),
                        "visible_result_roles": [term],
                    },
                    {
                        "component_roles_present": [demand, term],
                        "result_role": deposit,
                        "status": "VISIBLE_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS",
                        "visible_result_roles": [deposit, "EXPLICIT_INTERBANK_DEPOSIT_TOTAL"],
                    },
                    {
                        "component_roles_present": ["INTERBANK_LOAN_VND", provision],
                        "result_role": loan,
                        "status": "VISIBLE_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS",
                        "visible_result_roles": [loan, "EXPLICIT_INTERBANK_LOAN_TOTAL"],
                    },
                    {
                        "component_roles_present": [
                            deposit,
                            loan,
                            *([root_adjustment_role] if root_adjustment else []),
                        ],
                        "result_role": family,
                        "status": (
                            "VISIBLE_TRAILING_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS"
                            if trailing_detail_root
                            else "VISIBLE_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS"
                        ),
                        "visible_result_roles": ["EXPLICIT_FAMILY_TOTAL"],
                    },
                ],
                "local": [],
            },
            "family_id": family,
            "resolved_roles": [*visible_records, *derived_records],
        },
        "candidate_ordinal": 1,
        "column_context": copy.deepcopy(context),
        "reasons": [],
    }
    detail_parent_roles = {
        "DEMAND_DEPOSIT_VND": demand,
        "DEMAND_DEPOSIT_FOREIGN_CURRENCY": demand,
        "TERM_DEPOSIT_VND": term,
        "TERM_DEPOSIT_FOREIGN_CURRENCY": term,
        "INTERBANK_LOAN_VND": loan,
        "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND": "INTERBANK_LOAN_VND",
        provision: deposit if wrong_provision_parent else loan,
        **(
            {deposit: family, demand: family, term: family, loan: family}
            if same_role_group_sources
            else {}
        ),
        **({root_adjustment_role: family} if root_adjustment else {}),
        "EXPLICIT_INTERBANK_DEPOSIT_TOTAL": deposit,
        "EXPLICIT_INTERBANK_LOAN_TOTAL": loan,
        "EXPLICIT_FAMILY_TOTAL": family,
    }
    if off_frontier_row:
        detail_parent_roles["UNRELATED_ZERO_ADDITIVE_ROW"] = loan
    if nested_discount:
        detail_parent_roles["NESTED_DISCOUNT_MEMO"] = "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND"
    _v4_seal_generic_visible_axes(detail, parent_roles=detail_parent_roles)
    aliases = {
        deposit: "EXPLICIT_INTERBANK_DEPOSIT_TOTAL",
        loan: "EXPLICIT_INTERBANK_LOAN_TOTAL",
        family: "EXPLICIT_FAMILY_TOTAL",
    }
    records = {record["role"]: record for record in detail["additive_closure"]["resolved_roles"]}
    for role, alias in aliases.items():
        if same_role_group_sources and role in {deposit, loan}:
            continue
        records[role]["source"] = copy.deepcopy(records[alias]["source"])
    if trailing_detail_root:
        _v4_replace_visible_alias_with_trailing_result(
            detail,
            alias_role="EXPLICIT_FAMILY_TOTAL",
            result_role=family,
        )
        detail["additive_closure"]["resolved_roles"] = [
            record
            for record in detail["additive_closure"]["resolved_roles"]
            if record["role"]
            not in {"EXPLICIT_INTERBANK_DEPOSIT_TOTAL", "EXPLICIT_INTERBANK_LOAN_TOTAL"}
        ]
    _v4_reseal_candidate_envelopes(detail)
    return summary, detail


@pytest.mark.parametrize(
    ("adjustment_role", "adjustment_axis"),
    [
        ("INTERBANK_LOAN_PROVISION", (0, 0)),
        ("OTHER_EXACT_LOAN_ADJUSTMENT", (2, -3)),
    ],
)
def test_v4_visible_summary_yields_to_unique_visible_correlated_exact_detail(
    adjustment_role: str,
    adjustment_axis: tuple[int, int],
) -> None:
    summary, detail = _v4_visible_summary_and_correlated_detail_candidates(
        adjustment_axis=adjustment_axis,
        adjustment_role=adjustment_role,
    )

    selected, reasons = subject._select_candidate_evidence(
        [summary, detail],
        {
            **_strict_same_population_selection_policy(),
            "format_version": subject.EVALUATION_SPEC_FORMAT_V4,
        },
    )

    assert selected is detail
    assert reasons == []


def test_v4_visible_summary_yields_to_exact_richer_trailing_root_detail() -> None:
    summary, detail = _v4_visible_summary_and_correlated_detail_candidates(
        root_adjustment=True,
        same_role_group_sources=True,
        trailing_detail_root=True,
    )

    selected, reasons = subject._select_candidate_evidence(
        [summary, detail],
        {
            **_strict_same_population_selection_policy(),
            "format_version": subject.EVALUATION_SPEC_FORMAT_V4,
        },
    )

    assert selected is detail
    assert reasons == []


@pytest.mark.parametrize(
    "mutation",
    [
        "DUPLICATE_TRAILING_ROW",
        "WRONG_TRAILING_COVERAGE_DISPOSITION",
        "WRONG_TRAILING_EQUATION_EVIDENCE",
        "WRONG_TRAILING_NUMERIC_OWNER",
        "MISMATCHED_TRAILING_SOURCE_ROW",
    ],
)
def test_v4_trailing_root_detail_requires_one_exact_source_bound_receipt(
    mutation: str,
) -> None:
    summary, detail = _v4_visible_summary_and_correlated_detail_candidates(
        root_adjustment=True,
        same_role_group_sources=True,
        trailing_detail_root=True,
    )
    closure = detail["additive_closure"]
    root = next(
        record for record in closure["resolved_roles"] if record["role"] == closure["family_id"]
    )
    equation = next(
        item
        for item in closure["equations"]["global"]
        if item["result_role"] == closure["family_id"]
    )
    trailing = detail["row_axis"]["trailing_value_rows"][0]
    coverage = next(
        receipt
        for receipt in closure["coverage_receipt"]
        if receipt["row_kind"] == "TRAILING_VALUE_ROW"
    )
    if mutation == "DUPLICATE_TRAILING_ROW":
        detail["row_axis"]["trailing_value_rows"].append(copy.deepcopy(trailing))
    elif mutation == "WRONG_TRAILING_COVERAGE_DISPOSITION":
        coverage["disposition"] = "UNRESOLVED_UNSELECTED_COMPLETE_TRAILING_NUMERIC_CHALLENGER"
    elif mutation == "WRONG_TRAILING_EQUATION_EVIDENCE":
        equation["trailing_candidate_evidence"][0]["sample_ids"].reverse()
    elif mutation == "WRONG_TRAILING_NUMERIC_OWNER":
        sample_id = trailing["values"][0]["sample_id"]
        next(
            sample
            for sample in closure["numeric_sample_universe"]
            if sample["sample_id"] == sample_id
        )["owner_id"] = "aforav2:trailing:1"
    else:
        root["source"]["record"]["values"][0]["raw_prediction"] = "101"
    _v4_reseal_candidate_envelopes(detail)

    selected, reasons = subject._select_candidate_evidence(
        [summary, detail],
        {
            **_strict_same_population_selection_policy(),
            "format_version": subject.EVALUATION_SPEC_FORMAT_V4,
        },
    )

    assert selected is None
    assert reasons == ["MULTIPLE_DOWNSTREAM_EVIDENCE_COMPLETE_TOPOLOGY_REGIONS"]


@pytest.mark.parametrize(
    ("demand_line", "term_line"),
    [
        (0, 30),
        (5, 65),
    ],
)
def test_v4_root_owned_subgroup_result_requires_parent_to_next_sibling_interval(
    demand_line: int,
    term_line: int,
) -> None:
    summary, detail = _v4_visible_summary_and_correlated_detail_candidates(
        root_adjustment=True,
        root_scoped_demand_line=demand_line,
        root_scoped_term_line=term_line,
        same_role_group_sources=True,
        trailing_detail_root=True,
    )

    selected, reasons = subject._select_candidate_evidence(
        [summary, detail],
        {
            **_strict_same_population_selection_policy(),
            "format_version": subject.EVALUATION_SPEC_FORMAT_V4,
        },
    )

    assert selected is None
    assert reasons == ["MULTIPLE_DOWNSTREAM_EVIDENCE_COMPLETE_TOPOLOGY_REGIONS"]


@pytest.mark.parametrize(
    "mutation",
    [
        "AXIS_MISMATCH",
        "PERIOD_MISMATCH",
        "UNSEALED",
        "PARTIAL",
        "DUPLICATE_ROLE",
        "WRONG_PARENT",
        "OFF_FRONTIER",
        "MIXED_LEVEL",
        "NESTED_DISCOUNT",
        "UNCLAIMED_NUMERIC_SAMPLE",
    ],
)
@pytest.mark.parametrize("trailing_detail_root", [False, True])
def test_v4_visible_correlated_detail_requires_one_exhaustive_direct_frontier(
    mutation: str,
    trailing_detail_root: bool,
) -> None:
    summary, detail = _v4_visible_summary_and_correlated_detail_candidates(
        nested_discount=mutation == "NESTED_DISCOUNT",
        off_frontier_row=mutation == "OFF_FRONTIER",
        partial_provision=mutation == "PARTIAL",
        same_role_group_sources=trailing_detail_root,
        trailing_detail_root=trailing_detail_root,
        wrong_provision_parent=mutation == "WRONG_PARENT",
    )
    if mutation == "AXIS_MISMATCH":
        record = next(
            record
            for record in detail["additive_closure"]["resolved_roles"]
            if record["role"] == "INTERBANK_DEPOSIT_GROUP"
        )
        record["values"][0]["number"]["coefficient"] += 1
        _v4_reseal_candidate_envelopes(detail)
    elif mutation == "PERIOD_MISMATCH":
        detail["column_context"]["period_axis"][0]["resolved_period"] = "30/06/2025"
    elif mutation == "UNSEALED":
        detail["row_axis"]["rows"][0]["status"] = "PARTIAL_VISIBLE_VALUE_ROW"
    elif mutation == "DUPLICATE_ROLE":
        detail["additive_closure"]["resolved_roles"].append(
            copy.deepcopy(detail["additive_closure"]["resolved_roles"][0])
        )
        _v4_reseal_candidate_envelopes(detail)
    elif mutation == "MIXED_LEVEL":
        equation = next(
            equation
            for equation in detail["additive_closure"]["equations"]["global"]
            if equation["result_role"] == "INTERBANK_DEPOSITS_AND_LOANS"
        )
        equation["component_roles_present"].append("INTERBANK_LOAN_PROVISION")
        root = next(
            record
            for record in detail["additive_closure"]["resolved_roles"]
            if record["role"] == "INTERBANK_DEPOSITS_AND_LOANS"
        )
        root["component_roles"].append("INTERBANK_LOAN_PROVISION")
        _v4_reseal_candidate_envelopes(detail)
    elif mutation == "UNCLAIMED_NUMERIC_SAMPLE":
        sample = copy.deepcopy(detail["additive_closure"]["numeric_sample_universe"][0])
        sample["sample_id"] += ":unclaimed"
        sample["owner_kind"] = "SOURCE_ONLY_INTERNAL_CLUSTER"
        sample["owner_id"] = "aforav2:unassigned:" + "3" * 64
        detail["additive_closure"]["numeric_sample_universe"].append(sample)
        detail["additive_closure"]["numeric_sample_universe"].sort(
            key=lambda record: (
                record["page_sequence"],
                record["line_ordinal"],
                record["column_ordinal"],
                record["sample_id"],
            )
        )
        _v4_reseal_candidate_envelopes(detail)

    selected, reasons = subject._select_candidate_evidence(
        [summary, detail],
        {
            **_strict_same_population_selection_policy(),
            "format_version": subject.EVALUATION_SPEC_FORMAT_V4,
        },
    )

    assert selected is None
    assert reasons == ["MULTIPLE_DOWNSTREAM_EVIDENCE_COMPLETE_TOPOLOGY_REGIONS"]


def test_v4_two_visible_correlated_exact_details_preserve_ambiguity() -> None:
    summary, detail = _v4_visible_summary_and_correlated_detail_candidates()
    competing = copy.deepcopy(detail)
    competing["candidate_ordinal"] = 2

    selected, reasons = subject._select_candidate_evidence(
        [summary, detail, competing],
        {
            **_strict_same_population_selection_policy(),
            "format_version": subject.EVALUATION_SPEC_FORMAT_V4,
        },
    )

    assert selected is None
    assert reasons == ["MULTIPLE_DOWNSTREAM_EVIDENCE_COMPLETE_TOPOLOGY_REGIONS"]


def _v4_coarse_and_split_provision_candidates(*, root: tuple[int, int]) -> tuple[dict, dict]:
    coarse_provision = (0, -50_000)
    gross_loan = (494_565, 1_216_832)
    deposit = tuple(
        root_value - loan_value - provision_value
        for root_value, loan_value, provision_value in zip(
            root, gross_loan, coarse_provision, strict=True
        )
    )
    net_loan = tuple(
        loan_value + provision_value
        for loan_value, provision_value in zip(gross_loan, coarse_provision, strict=True)
    )
    summary = _ready_hierarchical_candidate(
        [
            "EXPLICIT_FAMILY_TOTAL",
            "INTERBANK_DEPOSIT_GROUP",
            "INTERBANK_LOAN_GROUP",
            "TOTAL_INTERBANK_PROVISION",
            "FAMILY",
        ],
        candidate_ordinal=0,
        coefficients=root,
    )
    detail = _ready_hierarchical_candidate(
        [
            "EXPLICIT_FAMILY_TOTAL",
            "DEMAND_DEPOSIT_VND",
            "INTERBANK_DEPOSIT_GROUP",
            "INTERBANK_LOAN_VND",
            "INTERBANK_LOAN_GROUP",
            "INTERBANK_DEPOSIT_PROVISION",
            "INTERBANK_LOAN_PROVISION",
            "FAMILY",
        ],
        candidate_ordinal=1,
        coefficients=root,
    )

    def replace_role(candidate: dict, record: dict) -> None:
        records = candidate["additive_closure"]["resolved_roles"]
        records[records.index(next(item for item in records if item["role"] == record["role"]))] = (
            record
        )

    def resolved_record(role: str, coefficients: tuple[int, int]) -> dict:
        return {
            "component_roles": [],
            "resolution_kind": "DERIVED_EXACT_COMPONENT_SUM",
            "role": role,
            "source": None,
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

    replace_role(
        summary,
        _direct_visible_provision_record(
            "TOTAL_INTERBANK_PROVISION", coarse_provision, parent_role="FAMILY"
        ),
    )
    replace_role(summary, resolved_record("INTERBANK_DEPOSIT_GROUP", deposit))
    replace_role(summary, resolved_record("INTERBANK_LOAN_GROUP", gross_loan))
    replace_role(
        detail,
        _direct_visible_provision_record(
            "INTERBANK_DEPOSIT_PROVISION",
            (0, 0),
            parent_role="INTERBANK_DEPOSIT_GROUP",
        ),
    )
    replace_role(
        detail,
        _direct_visible_provision_record(
            "INTERBANK_LOAN_PROVISION",
            coarse_provision,
            parent_role="INTERBANK_LOAN_GROUP",
        ),
    )
    replace_role(detail, resolved_record("DEMAND_DEPOSIT_VND", deposit))
    replace_role(detail, resolved_record("INTERBANK_DEPOSIT_GROUP", deposit))
    replace_role(detail, resolved_record("INTERBANK_LOAN_VND", gross_loan))
    replace_role(detail, resolved_record("INTERBANK_LOAN_GROUP", net_loan))
    summary["row_axis"] = {
        "rows": [
            copy.deepcopy(
                next(
                    record
                    for record in summary["additive_closure"]["resolved_roles"]
                    if record["role"] == "TOTAL_INTERBANK_PROVISION"
                )["source"]["record"]
            )
        ],
        "status": "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY",
    }
    detail["row_axis"] = {
        "rows": [
            copy.deepcopy(record["source"]["record"])
            for record in detail["additive_closure"]["resolved_roles"]
            if record["role"] in {"INTERBANK_DEPOSIT_PROVISION", "INTERBANK_LOAN_PROVISION"}
        ],
        "status": "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY",
    }
    summary["additive_closure"]["equations"] = {
        "global": [
            {
                "component_roles_present": [
                    "INTERBANK_DEPOSIT_GROUP",
                    "INTERBANK_LOAN_GROUP",
                    "TOTAL_INTERBANK_PROVISION",
                ],
                "result_role": "FAMILY",
                "status": "VISIBLE_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS",
                "visible_result_roles": ["FAMILY", "EXPLICIT_FAMILY_TOTAL"],
            }
        ]
    }
    detail["additive_closure"]["equations"] = {
        "global": [
            {
                "component_roles_present": [
                    "DEMAND_DEPOSIT_VND",
                    "INTERBANK_DEPOSIT_PROVISION",
                ],
                "result_role": "INTERBANK_DEPOSIT_GROUP",
                "status": "DERIVED_EXACT_EXHAUSTIVE_COMPONENT_SUM",
                "visible_result_roles": ["INTERBANK_DEPOSIT_GROUP"],
            },
            {
                "component_roles_present": [
                    "INTERBANK_LOAN_VND",
                    "INTERBANK_LOAN_PROVISION",
                ],
                "result_role": "INTERBANK_LOAN_GROUP",
                "status": "VISIBLE_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS",
                "visible_result_roles": ["INTERBANK_LOAN_GROUP"],
            },
            {
                "component_roles_present": [
                    "INTERBANK_DEPOSIT_GROUP",
                    "INTERBANK_LOAN_GROUP",
                ],
                "result_role": "FAMILY",
                "status": "VISIBLE_RESULT_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS",
                "visible_result_roles": ["FAMILY", "EXPLICIT_FAMILY_TOTAL"],
            },
        ]
    }
    _v4_seal_candidate_axes(summary)
    _v4_seal_candidate_axes(detail)
    return summary, detail


@pytest.mark.parametrize(
    "root",
    [
        (110_986_765, 108_003_288),
        (92_094_858, 108_003_288),
    ],
)
def test_v4_exact_coarse_provision_yields_to_parented_split_detail(root: tuple[int, int]) -> None:
    summary, detail = _v4_coarse_and_split_provision_candidates(root=root)

    selected, reasons = subject._select_candidate_evidence(
        [summary, detail],
        {
            **_strict_same_population_selection_policy(),
            "format_version": subject.EVALUATION_SPEC_FORMAT_V4,
        },
    )

    assert selected is detail
    assert reasons == []


@pytest.mark.parametrize(
    "mutation",
    [
        "MISMATCH_WITH_SAME_ROOT",
        "MISSING_SPLIT_ROLE",
        "OMITTED_COMMON_LANE",
        "PARTIAL_SPLIT_LANES",
        "DUPLICATE_SPLIT_ROLE",
        "ROUNDED_SPLIT_ROLE",
        "WRONG_SPLIT_PARENT",
        "SPLIT_GROUP_NOT_RECONCILED",
    ],
)
def test_v4_provision_presentation_stays_incomparable_without_exact_split_proof(
    mutation: str,
) -> None:
    summary, detail = _v4_coarse_and_split_provision_candidates(root=(110_986_765, 108_003_288))
    records = detail["additive_closure"]["resolved_roles"]
    coarse = next(
        item
        for item in summary["additive_closure"]["resolved_roles"]
        if item["role"] == "TOTAL_INTERBANK_PROVISION"
    )
    deposit = next(item for item in records if item["role"] == "INTERBANK_DEPOSIT_PROVISION")
    loan = next(item for item in records if item["role"] == "INTERBANK_LOAN_PROVISION")
    if mutation == "MISMATCH_WITH_SAME_ROOT":
        loan["values"][1]["number"]["coefficient"] += 1
        loan["source"]["record"]["values"][1]["parsed_token"]["coefficient"] += 1
    elif mutation == "MISSING_SPLIT_ROLE":
        records.remove(loan)
    elif mutation == "OMITTED_COMMON_LANE":
        for record in (coarse, deposit, loan):
            record["values"] = record["values"][:1]
            record["source"]["record"]["values"] = record["source"]["record"]["values"][:1]
    elif mutation == "PARTIAL_SPLIT_LANES":
        loan["source"]["record"]["missing_column_ordinals"] = [1]
        loan["source"]["record"]["status"] = "PARTIAL_VISIBLE_VALUE_ROW"
    elif mutation == "DUPLICATE_SPLIT_ROLE":
        records.append(copy.deepcopy(deposit))
    elif mutation == "ROUNDED_SPLIT_ROLE":
        loan["resolution_kind"] = "VISIBLE_SOURCE_ROLE_ROUNDING_CORROBORATED_BY_COMPONENTS"
    elif mutation == "WRONG_SPLIT_PARENT":
        match = deposit["source"]["record"]["label_match"]
        match["scope_owner_role"] = "INTERBANK_LOAN_GROUP"
        match["source_scope_binding"]["source_scope_role"] = "INTERBANK_LOAN_GROUP"
    else:
        equation = next(
            item
            for item in detail["additive_closure"]["equations"]["global"]
            if item["result_role"] == "INTERBANK_DEPOSIT_GROUP"
        )
        equation["status"] = "VISIBLE_RESULT_ROUNDING_CORROBORATED_BY_EXHAUSTIVE_COMPONENTS"

    selected, reasons = subject._select_candidate_evidence(
        [summary, detail],
        {
            **_strict_same_population_selection_policy(),
            "format_version": subject.EVALUATION_SPEC_FORMAT_V4,
        },
    )

    assert selected is None
    assert reasons == ["MULTIPLE_DOWNSTREAM_EVIDENCE_COMPLETE_TOPOLOGY_REGIONS"]


def test_v4_provision_projection_recomputes_stale_exact_equations_per_lane() -> None:
    summary, detail = _v4_coarse_and_split_provision_candidates(root=(110_986_765, 108_003_288))

    for candidate, role in (
        (summary, "TOTAL_INTERBANK_PROVISION"),
        (detail, "INTERBANK_LOAN_PROVISION"),
    ):
        record = next(
            item for item in candidate["additive_closure"]["resolved_roles"] if item["role"] == role
        )
        row = next(item for item in candidate["row_axis"]["rows"] if item["role"] == role)
        record["values"][1]["number"]["coefficient"] += 1
        record["source"]["record"]["values"][1]["parsed_token"]["coefficient"] += 1
        row["values"][1]["parsed_token"]["coefficient"] += 1

    selected, reasons = subject._select_candidate_evidence(
        [summary, detail],
        {
            **_strict_same_population_selection_policy(),
            "format_version": subject.EVALUATION_SPEC_FORMAT_V4,
        },
    )

    assert selected is None
    assert reasons == ["MULTIPLE_DOWNSTREAM_EVIDENCE_COMPLETE_TOPOLOGY_REGIONS"]


@pytest.mark.parametrize(
    "mutation",
    [
        "COHERENTLY_REHASHED_SOURCE_OCCURRENCE",
        "DUPLICATE_ROW_OCCURRENCE",
        "WRONG_ROW_VALUE",
        "WRONG_ROW_PARENT_OCCURRENCE",
        "WRONG_SOURCE_SCOPE_BINDING",
        "INCOMPLETE_ROW",
    ],
)
def test_v4_provision_projection_requires_one_exact_authenticated_row_binding(
    mutation: str,
) -> None:
    summary, detail = _v4_coarse_and_split_provision_candidates(root=(110_986_765, 108_003_288))
    deposit = next(
        item
        for item in detail["additive_closure"]["resolved_roles"]
        if item["role"] == "INTERBANK_DEPOSIT_PROVISION"
    )
    source_row = deposit["source"]["record"]
    row = next(
        item for item in detail["row_axis"]["rows"] if item["role"] == "INTERBANK_DEPOSIT_PROVISION"
    )
    if mutation == "COHERENTLY_REHASHED_SOURCE_OCCURRENCE":
        label = source_row["label_match"]
        label["document_line_ordinal"] += 1
        label["end_document_line_ordinal"] += 1
        label["occurrence_id"] = "aforav2:occurrence:" + canonical_json_sha256_v1(
            {
                "document_line_ordinal": label["document_line_ordinal"],
                "end_document_line_ordinal": label["end_document_line_ordinal"],
                "page_sequence": label["page_sequence"],
                "role": label["role"],
                "role_occurrence_ordinal": label["role_occurrence_ordinal"],
            }
        )
    elif mutation == "DUPLICATE_ROW_OCCURRENCE":
        detail["row_axis"]["rows"].append(copy.deepcopy(row))
    elif mutation == "WRONG_ROW_VALUE":
        row["values"][1]["parsed_token"]["coefficient"] += 1
    elif mutation == "WRONG_ROW_PARENT_OCCURRENCE":
        row["label_match"]["scope_owner_occurrence_id"] = "aforav2:occurrence:wrong-parent"
    elif mutation == "WRONG_SOURCE_SCOPE_BINDING":
        binding = source_row["label_match"]["source_scope_binding"]
        binding["source_scope_role"] = "INTERBANK_LOAN_GROUP"
        material = copy.deepcopy(binding)
        material.pop("binding_id")
        binding["binding_id"] = "aforav2:scope-binding:" + canonical_json_sha256_v1(material)
    else:
        row["missing_column_ordinals"] = [1]
        row["status"] = "PARTIAL_VISIBLE_VALUE_ROW"

    selected, reasons = subject._select_candidate_evidence(
        [summary, detail],
        {
            **_strict_same_population_selection_policy(),
            "format_version": subject.EVALUATION_SPEC_FORMAT_V4,
        },
    )

    assert selected is None
    assert reasons == ["MULTIPLE_DOWNSTREAM_EVIDENCE_COMPLETE_TOPOLOGY_REGIONS"]


@pytest.mark.parametrize(
    "mutation",
    [
        "COHERENT_WRONG_PARENT_OCCURRENCE",
        "COHERENT_REHASHED_PHYSICAL_OCCURRENCE",
        "COHERENT_FORGED_SAMPLE_IDS",
        "REHASHED_DUPLICATE_SEALED_OCCURRENCE",
        "REHASHED_CROSS_ROOT_PARENT",
        "REHASHED_WRONG_COVERAGE_ID",
        "REHASHED_WRONG_OCCURRENCE_PIN",
        "REHASHED_WRONG_ROW_BBOX",
    ],
)
def test_v4_provision_projection_binds_dual_copies_to_authenticated_candidate_axes(
    mutation: str,
) -> None:
    summary, detail = _v4_coarse_and_split_provision_candidates(root=(110_986_765, 108_003_288))
    deposit = next(
        record
        for record in detail["additive_closure"]["resolved_roles"]
        if record["role"] == "INTERBANK_DEPOSIT_PROVISION"
    )
    source_row = deposit["source"]["record"]
    axis_row = next(
        row for row in detail["row_axis"]["rows"] if row["role"] == "INTERBANK_DEPOSIT_PROVISION"
    )
    if mutation == "COHERENT_WRONG_PARENT_OCCURRENCE":
        for row in (source_row, axis_row):
            row["label_match"]["scope_owner_occurrence_id"] = (
                "aforav2:occurrence:nonexistent-same-role-parent"
            )
    elif mutation == "COHERENT_REHASHED_PHYSICAL_OCCURRENCE":
        for row in (source_row, axis_row):
            label = row["label_match"]
            label["document_line_ordinal"] += 7
            label["end_document_line_ordinal"] += 7
            label["page_sequence"] += 1
            label["occurrence_id"] = "aforav2:occurrence:" + canonical_json_sha256_v1(
                {
                    "document_line_ordinal": label["document_line_ordinal"],
                    "end_document_line_ordinal": label["end_document_line_ordinal"],
                    "page_sequence": label["page_sequence"],
                    "role": label["role"],
                    "role_occurrence_ordinal": label["role_occurrence_ordinal"],
                }
            )
    elif mutation == "COHERENT_FORGED_SAMPLE_IDS":
        for row in (source_row, axis_row):
            for value in row["values"]:
                value["sample_id"] = f"sample:forged:{value['column_ordinal']}"
    elif mutation == "REHASHED_DUPLICATE_SEALED_OCCURRENCE":
        detail["additive_closure"]["role_occurrences"].append(
            copy.deepcopy(detail["additive_closure"]["role_occurrences"][-1])
        )
    elif mutation == "REHASHED_CROSS_ROOT_PARENT":
        parent = next(
            occurrence
            for occurrence in detail["additive_closure"]["role_occurrences"]
            if occurrence["role"] == "INTERBANK_DEPOSIT_GROUP"
        )
        parent["scope_owner_occurrence_id"] = "aforav2:root:" + "3" * 64
        parent["label_match"]["scope_owner_occurrence_id"] = parent["scope_owner_occurrence_id"]
    elif mutation == "REHASHED_WRONG_COVERAGE_ID":
        receipt = next(
            receipt
            for receipt in detail["additive_closure"]["coverage_receipt"]
            if receipt["role"] == "INTERBANK_DEPOSIT_PROVISION"
        )
        receipt["coverage_id"] = "ashtcv2:coverage:role:forged"
    elif mutation == "REHASHED_WRONG_OCCURRENCE_PIN":
        detail["additive_closure"]["occurrence_axis_binding"]["dependency_content_refs"] = {}
    else:
        axis_row["values"][0]["bbox"][0] += 1
    _v4_reseal_candidate_envelopes(detail)

    selected, reasons = subject._select_candidate_evidence(
        [summary, detail],
        {
            **_strict_same_population_selection_policy(),
            "format_version": subject.EVALUATION_SPEC_FORMAT_V4,
        },
    )

    assert selected is None
    assert reasons == ["MULTIPLE_DOWNSTREAM_EVIDENCE_COMPLETE_TOPOLOGY_REGIONS"]


def test_v4_provision_projection_rejects_reused_occurrence_ids_across_candidates() -> None:
    summary, _ = _v4_coarse_and_split_provision_candidates(root=(110_986_765, 108_003_288))
    richer = copy.deepcopy(summary)
    richer["candidate_ordinal"] = 1
    richer["additive_closure"]["resolved_roles"].append(
        {"role": "ADDITIONAL_EXACT_INTERBANK_DETAIL"}
    )

    selected, reasons = subject._select_candidate_evidence(
        [summary, richer],
        {
            **_strict_same_population_selection_policy(),
            "format_version": subject.EVALUATION_SPEC_FORMAT_V4,
        },
    )

    assert selected is None
    assert reasons == ["MULTIPLE_DOWNSTREAM_EVIDENCE_COMPLETE_TOPOLOGY_REGIONS"]


def test_v4_equal_split_detail_candidates_remain_ambiguous() -> None:
    _, first = _v4_coarse_and_split_provision_candidates(root=(110_986_765, 108_003_288))
    second = copy.deepcopy(first)
    second["candidate_ordinal"] = 2

    selected, reasons = subject._select_candidate_evidence(
        [first, second],
        {
            **_strict_same_population_selection_policy(),
            "format_version": subject.EVALUATION_SPEC_FORMAT_V4,
        },
    )

    assert selected is None
    assert reasons == ["MULTIPLE_DOWNSTREAM_EVIDENCE_COMPLETE_TOPOLOGY_REGIONS"]


def test_v3_does_not_apply_v4_provision_presentation_equivalence() -> None:
    summary, detail = _v4_coarse_and_split_provision_candidates(root=(110_986_765, 108_003_288))

    selected, reasons = subject._select_candidate_evidence(
        [summary, detail], _strict_same_population_selection_policy()
    )

    assert selected is None
    assert reasons == ["MULTIPLE_DOWNSTREAM_EVIDENCE_COMPLETE_TOPOLOGY_REGIONS"]


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


@pytest.mark.parametrize("include_root_alias", [False, True])
def test_v4_all_equation_presentation_totals_do_not_inflate_role_richness(
    include_root_alias: bool,
) -> None:
    aliases = ["EXPLICIT_DEPOSIT_TOTAL", "EXPLICIT_LOAN_TOTAL"]
    if include_root_alias:
        aliases.append("EXPLICIT_FAMILY_TOTAL")
    summary = _ready_hierarchical_candidate(
        [*aliases, "DEPOSIT_GROUP", "LOAN_GROUP", "FAMILY"],
        candidate_ordinal=0,
    )
    detail = _ready_hierarchical_candidate(
        ["DEPOSIT_VND", "DEPOSIT_GROUP", "LOAN_VND", "LOAN_GROUP", "FAMILY"],
        candidate_ordinal=1,
    )
    equations = {
        "global": [
            {
                "result_role": "DEPOSIT_GROUP",
                "visible_result_roles": ["DEPOSIT_GROUP", "EXPLICIT_DEPOSIT_TOTAL"],
            },
            {
                "result_role": "LOAN_GROUP",
                "visible_result_roles": ["LOAN_GROUP", "EXPLICIT_LOAN_TOTAL"],
            },
            {
                "result_role": "FAMILY",
                "visible_result_roles": ["FAMILY", "EXPLICIT_FAMILY_TOTAL"],
            },
            {
                "result_role": "OPTIONAL_UNOBSERVED_GROUP",
                "visible_result_roles": [
                    "OPTIONAL_UNOBSERVED_GROUP",
                    "OPTIONAL_UNOBSERVED_TOTAL",
                ],
            },
        ]
    }
    for candidate in (summary, detail):
        candidate["additive_closure"]["equations"] = copy.deepcopy(equations)
    policy = {
        **_strict_same_population_selection_policy(),
        "format_version": subject.EVALUATION_SPEC_FORMAT_V4,
    }

    selected, reasons = subject._select_candidate_evidence([summary, detail], policy)

    assert selected is detail
    assert reasons == []


def test_v4_same_semantic_roles_with_or_without_presentation_totals_are_equal() -> None:
    base = _ready_hierarchical_candidate(
        ["DEPOSIT_GROUP", "LOAN_GROUP", "FAMILY"], candidate_ordinal=0
    )
    aliases = _ready_hierarchical_candidate(
        [
            "EXPLICIT_DEPOSIT_TOTAL",
            "EXPLICIT_LOAN_TOTAL",
            "EXPLICIT_FAMILY_TOTAL",
            "DEPOSIT_GROUP",
            "LOAN_GROUP",
            "FAMILY",
        ],
        candidate_ordinal=1,
    )
    equations = {
        "global": [
            {
                "result_role": "DEPOSIT_GROUP",
                "visible_result_roles": ["DEPOSIT_GROUP", "EXPLICIT_DEPOSIT_TOTAL"],
            },
            {
                "result_role": "LOAN_GROUP",
                "visible_result_roles": ["LOAN_GROUP", "EXPLICIT_LOAN_TOTAL"],
            },
            {
                "result_role": "FAMILY",
                "visible_result_roles": ["FAMILY", "EXPLICIT_FAMILY_TOTAL"],
            },
        ]
    }
    for candidate in (base, aliases):
        candidate["additive_closure"]["equations"] = copy.deepcopy(equations)

    selected, reasons = subject._select_candidate_evidence(
        [base, aliases],
        {
            **_strict_same_population_selection_policy(),
            "format_version": subject.EVALUATION_SPEC_FORMAT_V4,
        },
    )

    assert selected is None
    assert reasons == ["MULTIPLE_DOWNSTREAM_EVIDENCE_COMPLETE_TOPOLOGY_REGIONS"]


@pytest.mark.parametrize("malformation", ["REUSED_ALIAS", "MISSING_RESULT"])
def test_v4_malformed_presentation_metadata_is_noncomparable(malformation: str) -> None:
    observed_alias = "PRESENTATION_ALIAS" if malformation == "REUSED_ALIAS" else "FAMILY_ALIAS"
    first = _ready_hierarchical_candidate(
        [observed_alias, "DEPOSIT_GROUP", "LOAN_GROUP", "FAMILY"], candidate_ordinal=0
    )
    second = _ready_hierarchical_candidate(
        [observed_alias, "DEPOSIT_VND", "DEPOSIT_GROUP", "LOAN_GROUP", "FAMILY"],
        candidate_ordinal=1,
    )
    equations = [
        {
            "result_role": "DEPOSIT_GROUP",
            "visible_result_roles": ["DEPOSIT_GROUP", "PRESENTATION_ALIAS"],
        },
        {
            "result_role": "LOAN_GROUP",
            "visible_result_roles": [
                "LOAN_GROUP",
                "PRESENTATION_ALIAS" if malformation == "REUSED_ALIAS" else "LOAN_ALIAS",
            ],
        },
        {
            "result_role": "MISSING" if malformation == "MISSING_RESULT" else "FAMILY",
            "visible_result_roles": ["FAMILY_ALIAS"],
        },
    ]
    for candidate in (first, second):
        candidate["additive_closure"]["equations"] = {"global": copy.deepcopy(equations)}

    selected, reasons = subject._select_candidate_evidence(
        [first, second],
        {
            **_strict_same_population_selection_policy(),
            "format_version": subject.EVALUATION_SPEC_FORMAT_V4,
        },
    )

    assert selected is None
    assert reasons == ["MULTIPLE_DOWNSTREAM_EVIDENCE_COMPLETE_TOPOLOGY_REGIONS"]


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


def test_v4_compatible_numeric_gap_preserves_candidate_bound_margin_render_request() -> None:
    summary = _ready_hierarchical_candidate(
        ["DEPOSIT_GROUP", "LOAN_GROUP", "FAMILY"], candidate_ordinal=0
    )
    detail = _ready_hierarchical_candidate(
        ["DEPOSIT_VND", "DEPOSIT_GROUP", "LOAN_VND", "LOAN_GROUP", "FAMILY"],
        candidate_ordinal=1,
    )
    detail["reasons"] = [
        "SOURCE_ONLY_INTERNAL_NUMERIC_CLUSTER_VETO:aforav2:unassigned:stamp",
        "EXTREME_MARGIN_ANNOTATION_RENDER_REQUIRED:PAGE_SEQUENCE:33",
    ]
    detail["row_axis"] = {"rows": [{"label_match": {"page_sequence": 33}}]}

    selected, reasons = subject._select_candidate_evidence(
        [summary, detail],
        {
            **_strict_same_population_selection_policy(),
            "format_version": subject.EVALUATION_SPEC_FORMAT_V4,
        },
    )

    assert selected is None
    assert reasons == [
        "COMPATIBLE_CANDIDATE_NUMERIC_SCHEMA_GAP_VETO:READY_CANDIDATE_1:"
        "THREAT_CANDIDATE_2:THREAT_PAGES_33:"
        "SOURCE_ONLY_INTERNAL_NUMERIC_CLUSTER_VETO:aforav2:unassigned:stamp",
        "CANDIDATE_2:EXTREME_MARGIN_ANNOTATION_RENDER_REQUIRED:PAGE_SEQUENCE:33",
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
    for candidate in candidate_by_region.values():
        candidate["additive_closure"]["equations"] = {
            "global": [
                {
                    "result_role": "FAMILY",
                    "visible_result_roles": ["FAMILY"],
                }
            ]
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


def test_v4_candidate_scoped_missing_render_dimension_requests_only_its_single_page() -> None:
    joined_pages = [{"lines": [{} for _ in range(10)], "page_sequence": page} for page in (1, 2, 3)]
    topology_scan = {
        "regions": [
            {
                "cluster_start_document_line_ordinal": 2,
                "cluster_end_document_line_ordinal_exclusive": 8,
            }
        ],
        "status": "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL",
    }
    topology_candidates = {
        "regions": [
            topology_scan["regions"][0],
            {
                "cluster_start_document_line_ordinal": 22,
                "cluster_end_document_line_ordinal_exclusive": 28,
            },
        ],
        "status": "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS",
    }
    trial = {
        "row_axis": None,
        "unresolved_reasons": [
            "CANDIDATE_1:VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE",
            "CANDIDATE_2:ROW_AXIS_ERROR:FamilyFirstAccountingEvidenceSweepV1Error:"
            "missing-lane page lacks authenticated render dimensions",
        ],
    }

    assert subject._missing_render_pages_for_document_store_trial_v1(
        trial,
        topology_scan,
        joined_pages,
        evaluation_spec={"format_version": subject.EVALUATION_SPEC_FORMAT_V4},
        topology_candidates=topology_candidates,
    ) == (3,)


@pytest.mark.parametrize(
    ("reason", "candidate_regions"),
    [
        (
            "ROW_AXIS_ERROR:FamilyFirstAccountingEvidenceSweepV1Error:"
            "missing-lane page lacks authenticated render dimensions",
            [(22, 28)],
        ),
        (
            "CANDIDATE_2:ROW_AXIS_ERROR:FamilyFirstAccountingEvidenceSweepV1Error:"
            "missing-lane page lacks authenticated render dimension",
            [(2, 8), (22, 28)],
        ),
        (
            "CANDIDATE_2:ROW_AXIS_ERROR:OtherError:"
            "missing-lane page lacks authenticated render dimensions",
            [(2, 8), (22, 28)],
        ),
        (
            "CANDIDATE_3:ROW_AXIS_ERROR:FamilyFirstAccountingEvidenceSweepV1Error:"
            "missing-lane page lacks authenticated render dimensions",
            [(2, 8), (22, 28)],
        ),
        (
            "CANDIDATE_1:ROW_AXIS_ERROR:FamilyFirstAccountingEvidenceSweepV1Error:"
            "missing-lane page lacks authenticated render dimensions",
            [(8, 22)],
        ),
        (
            "CANDIDATE_1:ROW_AXIS_ERROR:FamilyFirstAccountingEvidenceSweepV1Error:"
            "numeric row missing",
            [(22, 28)],
        ),
    ],
)
def test_v4_missing_render_dimension_retry_rejects_unbound_or_inexact_request(
    reason: str,
    candidate_regions: list[tuple[int, int]],
) -> None:
    joined_pages = [{"lines": [{} for _ in range(10)], "page_sequence": page} for page in (1, 2, 3)]
    topology_scan = {
        "regions": [],
        "status": "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL",
    }
    topology_candidates = {
        "regions": [
            {
                "cluster_start_document_line_ordinal": start,
                "cluster_end_document_line_ordinal_exclusive": end,
            }
            for start, end in candidate_regions
        ],
        "status": "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS",
    }

    assert (
        subject._missing_render_pages_for_document_store_trial_v1(
            {"row_axis": None, "unresolved_reasons": [reason]},
            topology_scan,
            joined_pages,
            evaluation_spec={"format_version": subject.EVALUATION_SPEC_FORMAT_V4},
            topology_candidates=topology_candidates,
        )
        == ()
    )


def test_v4_missing_render_dimension_retry_rejects_duplicate_and_v3_requests() -> None:
    reason = (
        "CANDIDATE_1:ROW_AXIS_ERROR:FamilyFirstAccountingEvidenceSweepV1Error:"
        "missing-lane page lacks authenticated render dimensions"
    )
    trial = {"row_axis": None, "unresolved_reasons": [reason, reason]}
    topology_scan = {
        "regions": [
            {
                "cluster_start_document_line_ordinal": 2,
                "cluster_end_document_line_ordinal_exclusive": 8,
            }
        ],
        "status": "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL",
    }
    topology_candidates = {
        "regions": topology_scan["regions"],
        "status": "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL",
    }
    joined_pages = [{"lines": [{} for _ in range(10)], "page_sequence": 1}]

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
    assert (
        subject._missing_render_pages_for_document_store_trial_v1(
            {"row_axis": None, "unresolved_reasons": [reason]},
            topology_scan,
            joined_pages,
            evaluation_spec={"format_version": subject.EVALUATION_SPEC_FORMAT_V3},
        )
        == ()
    )


@pytest.mark.parametrize(("ordinary_page", "candidate_page"), [(1, 2), (2, 1)])
def test_v4_exact_candidate_missing_dimension_gets_one_bounded_second_render_pass(
    monkeypatch,
    ordinary_page: int,
    candidate_page: int,
) -> None:
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
    legacy_scan = {
        "regions": [
            {
                "cluster_start_document_line_ordinal": 2,
                "cluster_end_document_line_ordinal_exclusive": 8,
            }
        ],
        "status": "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL",
    }
    topology_candidates = {
        "regions": [
            legacy_scan["regions"][0],
            {
                "cluster_start_document_line_ordinal": 12,
                "cluster_end_document_line_ordinal_exclusive": 18,
            },
        ],
        "status": "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS",
    }
    trial_render_pages = []

    def trial_from_snapshot(
        _snapshot,
        _family,
        _policy,
        *,
        render_snapshots=(),
        **_kwargs,
    ):
        pages = tuple(render["physical_page"] for render in render_snapshots)
        trial_render_pages.append(pages)
        if not pages:
            reasons = [
                f"CANDIDATE_{ordinary_page}:"
                f"EXTREME_MARGIN_ANNOTATION_RENDER_REQUIRED:PAGE_SEQUENCE:{ordinary_page}"
            ]
        elif pages == (ordinary_page,):
            reasons = [
                f"CANDIDATE_{candidate_page}:"
                "ROW_AXIS_ERROR:FamilyFirstAccountingEvidenceSweepV1Error:"
                "missing-lane page lacks authenticated render dimensions"
            ]
        else:
            reasons = []
        return {
            "row_axis": (
                {
                    "rows": [],
                    "status": "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY",
                    "trailing_value_rows": [],
                }
                if not reasons
                else None
            ),
            "topology_scan": legacy_scan,
            "unresolved_reasons": reasons,
        }

    render_calls = []

    def read_renders(_capability, *, document_ordinal, physical_pages):
        render_calls.append((document_ordinal, physical_pages))
        return tuple(
            {"physical_page": page, "render_id": f"authenticated-render:{page}"}
            for page in physical_pages
        )

    monkeypatch.setattr(subject, "_trial_from_document_store_snapshot_v1", trial_from_snapshot)
    monkeypatch.setattr(
        subject,
        "_v4_topology_authority",
        lambda *_args, **_kwargs: (legacy_scan, topology_candidates),
    )
    monkeypatch.setattr(
        subject.document_store_v1,
        "read_authenticated_family_first_document_page_renders_v1",
        read_renders,
    )
    telemetry = {}

    trial = subject._document_store_trial_with_render_rescue_v1(
        object(),
        packet={"document_ordinal": 1},
        snapshot={"joined_pages": joined_pages},
        family_spec={},
        policy={"format_version": subject.EVALUATION_SPEC_FORMAT_V4},
        topology_scan=None,
        runtime_telemetry=telemetry,
    )

    assert trial["unresolved_reasons"] == []
    assert trial_render_pages == [(), (ordinary_page,), (1, 2)]
    assert render_calls == [(1, (ordinary_page,)), (1, (candidate_page,))]
    assert telemetry == {"render_page_count": 2, "render_retry_count": 2}


def test_authenticated_render_merge_deduplicates_only_one_exact_render_identity() -> None:
    page = {"physical_page": 2, "render_id": "authenticated-render:2", "sealed": True}

    assert subject._canonical_authenticated_render_snapshot_order_v1(
        ({"physical_page": 3, "render_id": "authenticated-render:3"}, page),
        (copy.deepcopy(page), {"physical_page": 1, "render_id": "authenticated-render:1"}),
    ) == (
        {"physical_page": 1, "render_id": "authenticated-render:1"},
        page,
        {"physical_page": 3, "render_id": "authenticated-render:3"},
    )
    with pytest.raises(
        subject.FamilyFirstAccountingEvidenceSweepV1Error,
        match="conflicting page",
    ):
        subject._canonical_authenticated_render_snapshot_order_v1(
            (page,),
            ({"physical_page": 2, "render_id": "authenticated-render:other"},),
        )


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


def _v5_lane_alternative_policy() -> dict[str, object]:
    return {
        **_strict_same_population_selection_policy(),
        "expected_lane_unit_kind_alternatives": [
            ["MONEY", "MONEY"],
            ["MONEY", "PERCENT", "MONEY", "PERCENT"],
        ],
        "family_id": "CASH_PRECIOUS_METALS",
        "format_version": subject.EVALUATION_SPEC_FORMAT_V5,
        "hierarchical_closure_spec": {"generic": "hierarchy"},
        "occurrence_row_axis_policy": {"generic": "occurrence"},
        "period_semantics": "BALANCE_COMPARATIVE",
    }


def test_v5_evaluation_accepts_only_unique_declared_lane_layouts(monkeypatch) -> None:
    monkeypatch.setattr(subject.occurrence_row_v2, "_policy", lambda value: value)
    monkeypatch.setattr(subject.scoped_v2, "_spec", lambda value, _family: value)

    policy = subject._evaluation_spec(
        _v5_lane_alternative_policy(),
        _family_spec(),
        raw_family_spec=_family_spec(),
    )

    assert policy["expected_lane_unit_kind_alternatives"] == [
        ["MONEY", "MONEY"],
        ["MONEY", "PERCENT", "MONEY", "PERCENT"],
    ]


@pytest.mark.parametrize(
    "alternatives",
    [
        [],
        [["MONEY", "MONEY"], ["MONEY", "MONEY"]],
        [["MONEY", "BANK_SPECIFIC"]],
        ["MONEY", "PERCENT"],
    ],
)
def test_v5_evaluation_rejects_empty_duplicate_or_untyped_lane_layouts(
    monkeypatch, alternatives
) -> None:
    monkeypatch.setattr(subject.occurrence_row_v2, "_policy", lambda value: value)
    monkeypatch.setattr(subject.scoped_v2, "_spec", lambda value, _family: value)
    policy = _v5_lane_alternative_policy()
    policy["expected_lane_unit_kind_alternatives"] = alternatives

    with pytest.raises(
        subject.FamilyFirstAccountingEvidenceSweepV1Error,
        match="lane-unit alternatives",
    ):
        subject._evaluation_spec(policy, _family_spec(), raw_family_spec=_family_spec())


def test_v5_column_context_selects_one_layout_and_rejects_zero_or_multiple(
    monkeypatch,
) -> None:
    policy = _v5_lane_alternative_policy()
    calls = []

    def build(_row, _pages, _family, *, expected_lane_unit_kinds, **_kwargs):
        calls.append(copy.deepcopy(expected_lane_unit_kinds))
        return {
            "status": (
                "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
                if expected_lane_unit_kinds == ["MONEY", "PERCENT", "MONEY", "PERCENT"]
                else "UNRESOLVED_PERIOD_UNIT_COLUMN_CONTEXT"
            ),
            "unit_axis": [
                {"column_ordinal": ordinal, "unit_kind": kind}
                for ordinal, kind in enumerate(expected_lane_unit_kinds)
            ],
        }

    monkeypatch.setattr(
        subject.column_context_multilevel_v2,
        "_build_accounting_family_column_context_multilevel_from_authenticated_row_axis_v2",
        build,
    )
    context, selected = subject._build_column_context_for_evaluation_v1(
        {}, [], {}, policy, visible_dash_rescues=()
    )

    assert selected == ["MONEY", "PERCENT", "MONEY", "PERCENT"]
    assert subject._resolved_lane_unit_kinds(policy, context) == selected
    assert calls == policy["expected_lane_unit_kind_alternatives"]

    for resolved_count in (0, 2):
        count = 0

        def ambiguous(
            _row,
            _pages,
            _family,
            *,
            expected_lane_unit_kinds,
            _resolved_count=resolved_count,
            **_kwargs,
        ):
            nonlocal count
            count += 1
            return {
                "status": (
                    "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
                    if count <= _resolved_count
                    else "UNRESOLVED_PERIOD_UNIT_COLUMN_CONTEXT"
                )
            }

        monkeypatch.setattr(
            subject.column_context_multilevel_v2,
            "_build_accounting_family_column_context_multilevel_from_authenticated_row_axis_v2",
            ambiguous,
        )
        with pytest.raises(
            subject.FamilyFirstAccountingEvidenceSweepV1Error,
            match="exactly one declared lane-unit alternative",
        ):
            subject._build_column_context_for_evaluation_v1(
                {}, [], {}, policy, visible_dash_rescues=()
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
