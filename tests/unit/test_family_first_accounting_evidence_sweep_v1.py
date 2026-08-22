from __future__ import annotations

import copy
import hashlib
import io

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
    assert render_calls == [(1, 1), (1, 2)]
    assert result["authority"]["not_observed_authority"] is False


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
            {
                "physical_page": 2,
                "pixel_height": 1400,
                "pixel_width": 1000,
                "render_sha256": "5" * 64,
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


def test_hierarchical_downstream_role_superset_selects_detail_over_summary() -> None:
    summary = {
        "additive_closure": {
            "resolved_roles": [
                {"role": "DEPOSIT_GROUP"},
                {"role": "LOAN_GROUP"},
                {"role": "FAMILY"},
            ]
        },
        "candidate_ordinal": 0,
        "reasons": [],
    }
    detail = {
        "additive_closure": {
            "resolved_roles": [
                {"role": "DEPOSIT_VND"},
                {"role": "DEPOSIT_GROUP"},
                {"role": "LOAN_VND"},
                {"role": "LOAN_GROUP"},
                {"role": "FAMILY"},
            ]
        },
        "candidate_ordinal": 1,
        "reasons": [],
    }

    selected, reasons = subject._select_candidate_evidence(
        [summary, detail],
        {"closure_policy": "HIERARCHICAL_RECURSIVE_CORROBORATE_OR_DERIVE"},
    )

    assert selected is detail
    assert reasons == []


def test_equal_hierarchical_candidates_remain_unresolved_without_page_routing() -> None:
    candidates = [
        {
            "additive_closure": {
                "resolved_roles": [{"role": "DEPOSIT_GROUP"}, {"role": "LOAN_GROUP"}]
            },
            "candidate_ordinal": ordinal,
            "reasons": [],
        }
        for ordinal in range(2)
    ]

    selected, reasons = subject._select_candidate_evidence(
        candidates,
        {"closure_policy": "HIERARCHICAL_RECURSIVE_CORROBORATE_OR_DERIVE"},
    )

    assert selected is None
    assert reasons == ["MULTIPLE_DOWNSTREAM_EVIDENCE_COMPLETE_TOPOLOGY_REGIONS"]


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
