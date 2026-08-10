from __future__ import annotations

import ast
import json
import os
from collections import Counter
from collections.abc import Iterator
from copy import deepcopy
from hashlib import sha256
from importlib.metadata import version as distribution_version
from pathlib import Path
from types import SimpleNamespace

import fitz
import pytest

from bctc_ai.ocr.causal_native_text_evidence_v2 import (
    ORDERING_POLICY_RECORD_PATH,
    build_causal_native_text_evidence_v2,
)
from bctc_ai.rendering.page_reader import (
    coordinate_authority,
    public_coordinate_authority,
    transform_pixel_polygon_to_unrotated_mpt,
)
from bctc_ai.source_structure import contracts_v2 as contracts_v2_module
from bctc_ai.source_structure.contracts_v1 import (
    ATOM_DISPOSITION_FORMAT_VERSION,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    make_page_proposal_set_v1,
    make_source_object_id_v1,
)
from bctc_ai.source_structure.contracts_v2 import (
    SourceStructureContractV2Error,
    make_empty_page_proposal_set_v2,
    make_page_proposal_set_v2,
    validate_source_evidence_projection_v2,
)
from bctc_ai.source_structure.evidence_projection_v2 import (
    SourceEvidenceProjectionV2Error,
    project_authenticated_page_v2,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FINALIZED_V3_ROOT = (
    PROJECT_ROOT / "output/development/bank-corpus-wave-1-role-b-page-reader-v1/full-v3"
)


def _finalized_page_records() -> Iterator[dict]:
    if not FINALIZED_V3_ROOT.is_dir():
        pytest.skip("finalized V3 output is not hydrated")
    for index_path in sorted((FINALIZED_V3_ROOT / "documents").glob("*.json")):
        index = json.loads(index_path.read_bytes())
        yield from index["page_records"]


def _load_result(record: dict) -> dict:
    return json.loads((FINALIZED_V3_ROOT / record["result_ref"]["path"]).read_bytes())


def _finalized_records() -> Iterator[tuple[dict, dict]]:
    for record in _finalized_page_records():
        yield record, _load_result(record)


def _real_four_status_pairs() -> dict[str, tuple[dict, dict]]:
    pairs: dict[str, tuple[dict, dict]] = {}
    for record in _finalized_page_records():
        if record["status"] not in pairs:
            pairs[record["status"]] = (record, _load_result(record))
        if len(pairs) == 4:
            break
    assert set(pairs) == {
        "OCR_WORD_BOX_READ_COMPLETE",
        "UNRESOLVED_OCR_WORD_BOX_GEOMETRY",
        "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
        "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY",
    }
    return pairs


def _refresh_native_result_ref(record: dict, result: dict) -> None:
    payload = canonical_json_bytes_v1(result)
    digest = canonical_json_sha256_v1(result)
    record["result_ref"] = {
        "path": f"objects/sha256/{digest[:2]}/{digest}.json",
        "sha256": digest,
        "size_bytes": len(payload),
    }


def _json_object_ref(value: dict) -> dict:
    payload = canonical_json_bytes_v1(value)
    digest = canonical_json_sha256_v1(value)
    return {
        "path": f"objects/sha256/{digest[:2]}/{digest}.json",
        "sha256": digest,
        "size_bytes": len(payload),
    }


def _refresh_projection_identity(projection: dict) -> None:
    projection["source_local_page_id"] = "ssv2:page:" + canonical_json_sha256_v1(
        contracts_v2_module._identity_payload(projection)  # noqa: SLF001
    )


_UPSTREAM_SAFETY = {
    "statement_classified": False,
    "table_classified": False,
    "rows_reconstructed": False,
    "cells_interpreted": False,
    "absence_claimed": False,
    "bank_registry_metadata_used": False,
    "filename_metadata_used": False,
    "role_a_used": False,
    "schema_used": False,
    "mapping_used": False,
    "historical_values_used": False,
}


class _Box:
    def __init__(self, width: float, height: float) -> None:
        self.width = width
        self.height = height


def _object_ref(digest: str, size: int, suffix: str) -> dict:
    return {
        "path": f"objects/sha256/{digest[:2]}/{digest}{suffix}",
        "sha256": digest,
        "size_bytes": size,
    }


def _request(
    *,
    route: str,
    source_sha: str,
    source_size: int,
    provider_identity: str,
) -> tuple[dict, str]:
    ocr = route == "DOMINANT_RASTER_OCR"
    request = {
        "format_version": "BANK_CORPUS_WAVE_1_PAGE_READ_REQUEST_V1",
        "git_commit": "0" * 40,
        "implementation_ledger_sha256": "1" * 64,
        "input_ledger_sha256": "2" * 64,
        "selection_receipt_sha256": "3" * 64,
        "sentinel_sha256": "4" * 64,
        "route_plan_sha256": "5" * 64,
        "pre_ocr_feature_fingerprint_sha256": "6" * 64,
        "source_sha256": source_sha,
        "source_size_bytes": source_size,
        "physical_page": 1,
        "route": route,
        "provider_identity_sha256": provider_identity,
        "render_runtime_identity_sha256": "7" * 64 if ocr else None,
        "render_specification": (
            {
                "dpi": 300,
                "colorspace": "RGB",
                "alpha": False,
                "annotations": "INCLUDED",
                "source": "FULL_COMPOSITED_DISPLAYED_PDF_PAGE",
            }
            if ocr
            else None
        ),
        "bank_identity_used": False,
        "filename_used": False,
        "role_a_used": False,
        "schema_used": False,
        "historical_values_used": False,
    }
    return request, canonical_json_sha256_v1(request)


def _synthetic_ocr_pair() -> tuple[dict, dict]:
    source_sha = "a" * 64
    request, request_sha = _request(
        route="DOMINANT_RASTER_OCR",
        source_sha=source_sha,
        source_size=4_096,
        provider_identity="8" * 64,
    )
    page = SimpleNamespace(
        rotation=0,
        rect=_Box(600.0, 800.0),
        cropbox=_Box(600.0, 800.0),
    )
    private_authority = coordinate_authority(
        page,
        pixel_width=1_200,
        pixel_height=1_600,
    )
    authority = public_coordinate_authority(private_authority)
    raw_polygon = [[100, 120], [700, 120], [700, 200], [100, 200]]
    canonical_polygon = transform_pixel_polygon_to_unrotated_mpt(
        raw_polygon,
        private_authority,
    )
    word_polygon = transform_pixel_polygon_to_unrotated_mpt(
        [[100, 120], [300, 120], [300, 200], [100, 200]],
        private_authority,
    )
    word = {
        "raw_text": "0",
        "score": None,
        "score_kind": "PP_OCRV6_LINE_SCORE_ONLY",
        "normalized_pixel_bbox": [100, 120, 300, 200],
        "canonical_bbox_mpt": [
            min(point[0] for point in word_polygon),
            min(point[1] for point in word_polygon),
            max(point[0] for point in word_polygon),
            max(point[1] for point in word_polygon),
        ],
        "canonical_polygon_mpt": word_polygon,
    }
    line = {
        "raw_text": "0",
        "score": 0.95,
        "score_kind": "PP_OCRV6_LINE_RECOGNITION_SCORE",
        "raw_pixel_bbox": [100, 120, 700, 200],
        "raw_pixel_polygon": raw_polygon,
        "canonical_bbox_mpt": [
            min(point[0] for point in canonical_polygon),
            min(point[1] for point in canonical_polygon),
            max(point[0] for point in canonical_polygon),
            max(point[1] for point in canonical_polygon),
        ],
        "canonical_polygon_mpt": canonical_polygon,
        "words": [word],
    }
    render_ref = _object_ref("9" * 64, 17, ".png")
    backend_ref = _object_ref("b" * 64, 31, ".json")
    result = {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V2",
        "status": "OCR_WORD_BOX_READ_COMPLETE",
        "claim_boundary": "SOURCE_VISIBLE_PAGE_TEXT_AND_GEOMETRY_EVIDENCE_ONLY",
        "request_sha256": request_sha,
        "request": request,
        "source_sha256": source_sha,
        "source_size_bytes": 4_096,
        "physical_page": 1,
        "route": "DOMINANT_RASTER_OCR",
        "provider_identity_sha256": request["provider_identity_sha256"],
        "render_runtime_identity_sha256": request["render_runtime_identity_sha256"],
        "input_render_ref": render_ref,
        "backend_payload_ref": backend_ref,
        "word_box_normalization_ledger": {
            "format_version": (
                "BANK_CORPUS_WAVE_1_ROLE_B_PPOCRV6_WORD_BOX_NORMALIZATION_LEDGER_V1"
            ),
            "status": "NO_CHANGE",
            "rule_id": "PP_OCRV6_TEXT_WORD_BOX_PAGE_BOUNDARY_CLIP_MAX_1PX_V1",
            "maximum_per_edge_overshoot_pixels": 1,
            "policy_sha256": "c" * 64,
            "control_identity_sha256": "d" * 64,
            "normalization_producer_implementation_ledger_sha256": "e" * 64,
            "pixel_dimensions": authority["pixel_dimensions"],
            "raw_payload_sha256": "f" * 64,
            "normalized_payload_sha256": "f" * 64,
            "correction_count": 0,
            "corrected_edge_count": 0,
            "corrections": [],
        },
        "coordinate_authority": authority,
        "lines": [line],
        "words": [word],
        "metrics": {
            "line_count": 1,
            "word_token_count": 1,
            "minimum_line_score": 0.95,
            "mean_line_score": 0.95,
            "lines_below_0_8": 0,
            "lines_below_0_9": 0,
        },
        "source_blank_claimed": False,
        "safety": deepcopy(_UPSTREAM_SAFETY),
    }
    result_ref = _json_object_ref(result)
    adoption = {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_FAILED_V2_OCR_ADOPTION_V1",
        "incident_identity_sha256": "0" * 64,
        "archive_portable_manifest_sha256": "1" * 64,
        "archive_live_manifest_sha256": "2" * 64,
        "source_control_identity_sha256": "3" * 64,
        "source_checkpoint_sha256": "4" * 64,
        "source_checkpoint_size_bytes": 1_024,
        "source_checkpoint_generation": 1,
        "source_page_record_sha256": "5" * 64,
        "source_status": result["status"],
        "source_origin": "PINNED_PPOCRV6_FULL_READER",
        "source_unresolved": False,
        "source_refs": {
            "render_ref": deepcopy(render_ref),
            "backend_payload_ref": deepcopy(backend_ref),
            "result_ref": deepcopy(result_ref),
        },
        "copy_semantics": "BYTE_COPY_NEW_INODE_NO_HARDLINK_V1",
        "source_checkpoint_or_page_record_relabelled": False,
        "destination_control_identity_sha256": "6" * 64,
    }
    record = {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_FULL_PAGE_RECORD_V2",
        "request_ordinal": 1,
        "document_id": f"sha256:{source_sha}",
        "source_sha256": source_sha,
        "source_size_bytes": 4_096,
        "physical_page": 1,
        "route": "DOMINANT_RASTER_OCR",
        "request_sha256": request_sha,
        "request": request,
        "status": result["status"],
        "origin": "AUTHENTICATED_FAILED_V2_OCR_EVIDENCE_BYTE_COPY",
        "upstream_status": result["status"],
        "upstream_origin": "PINNED_PPOCRV6_FULL_READER",
        "upstream_unresolved": False,
        "render_ref": render_ref,
        "backend_payload_ref": backend_ref,
        "result_ref": result_ref,
        "upstream_v2_adoption": adoption,
        "line_axis_count": 1,
        "nonempty_line_axis_count": 1,
        "exact_empty_line_axis_count": 0,
        "accepted_line_count": 1,
        "word_token_count": 1,
        "quarantined_span_count": 0,
        "ordering_quarantined_raw_line_run_count": 0,
        "ordering_quarantined_raw_word_count": 0,
        "noncontiguous_line_identity_count": 0,
        "word_box_correction_count": 0,
        "word_box_corrected_edge_count": 0,
        "statement_classification_count": 0,
        "table_classification_count": 0,
        "row_reconstruction_count": 0,
        "cell_interpretation_count": 0,
        "absence_declaration_count": 0,
        "unresolved": False,
    }
    return record, result


def _provider_ledger() -> dict:
    config_records = []
    for relative in (
        Path("config/ocr/causal-native-text-v1.yaml"),
        Path("config/ocr/native-text-quality-v2.yaml"),
    ):
        payload = (PROJECT_ROOT / relative).read_bytes()
        config_records.append(
            {
                "path": relative.as_posix(),
                "sha256": sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
        )
    ledger = {
        "config_records": config_records,
        "ocr_fallback_allowed": False,
        "provider": "PYMUPDF_CAUSAL_NATIVE_TEXT_VISIBILITY_V1",
        "pymupdf_binding_version": fitz.VersionBind,
        "pymupdf_distribution_version": distribution_version("PyMuPDF"),
        "pymupdf_runtime_versions": list(fitz.version),
    }
    ledger["sha256"] = canonical_json_sha256_v1(ledger)
    return ledger


def _native_ordering_identity() -> dict:
    relative = Path(ORDERING_POLICY_RECORD_PATH)
    payload = (PROJECT_ROOT / relative).read_bytes()
    return {
        "path": relative.as_posix(),
        "sha256": sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _synthetic_native_pair(
    monkeypatch: pytest.MonkeyPatch,
    *,
    contiguity_terminal: bool,
) -> tuple[dict, dict]:
    document = fitz.open()
    document.new_page(width=400, height=300)
    source_bytes = document.tobytes(garbage=4, deflate=True)
    document.close()
    source_sha = sha256(source_bytes).hexdigest()
    provider_ledger = _provider_ledger()
    request, request_sha = _request(
        route="CAUSAL_NATIVE_TEXT",
        source_sha=source_sha,
        source_size=len(source_bytes),
        provider_identity=provider_ledger["sha256"],
    )

    def word(identity: tuple[int, int, int], ordinal: int) -> dict:
        x0 = 10_000 + ordinal * 8_000
        return {
            "raw_text": f"W{ordinal}",
            "score": None,
            "score_kind": "NATIVE_TEXT_NO_RECOGNITION_SCORE",
            "canonical_bbox_mpt": [x0, 10_000, x0 + 6_000, 18_000],
            "block_number": identity[0],
            "line_number": identity[1],
            "word_number": identity[2],
        }

    identities = (
        [(1, 0, 0), (2, 0, 0), (1, 0, 1)] if contiguity_terminal else [(1, 0, 0), (1, 0, 1)]
    )
    words = [word(identity, ordinal) for ordinal, identity in enumerate(identities)]
    grouped: dict[tuple[int, int], list[dict]] = {}
    for item in words:
        grouped.setdefault((item["block_number"], item["line_number"]), []).append(item)
    lines = []
    for identity in sorted(grouped):
        members = grouped[identity]
        boxes = [item["canonical_bbox_mpt"] for item in members]
        lines.append(
            {
                "raw_text": " ".join(item["raw_text"] for item in members),
                "score": None,
                "score_kind": "NATIVE_TEXT_NO_RECOGNITION_SCORE",
                "canonical_bbox_mpt": [
                    min(box[0] for box in boxes),
                    min(box[1] for box in boxes),
                    max(box[2] for box in boxes),
                    max(box[3] for box in boxes),
                ],
                "block_number": identity[0],
                "line_number": identity[1],
                "words": deepcopy(members),
            }
        )
    raw_payload = {
        "status": "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
        "native_text_quality": "USABLE_TEXT_LAYER",
        "corruption_markers": [],
        "lines": lines,
        "words": words,
        "quarantined_spans": (
            [
                {
                    "page": 1,
                    "text_sha256": sha256(b"GHOST SECRET").hexdigest(),
                    "nonwhitespace_character_count": 11,
                    "bbox_mpt": [200_000, 200_000, 220_000, 215_000],
                    "block_number": 91,
                    "line_number": 7,
                    "span_number": 3,
                    "color": 0xFFFFFF,
                    "alpha": 255,
                    "render_sequence": 19,
                    "occluding_sequence": None,
                    "occluding_object_type": None,
                    "reason": "NEAR_WHITE_TEXT_PAINT",
                }
            ]
            if contiguity_terminal
            else []
        ),
        "ocr_fallback_used": False,
        "source_blank_claimed": False,
    }
    monkeypatch.setattr(
        "bctc_ai.ocr.causal_native_text_evidence_v2.read_causal_native_text_page",
        lambda *_args, **_kwargs: deepcopy(raw_payload),
    )
    built_backend, result = build_causal_native_text_evidence_v2(
        request=request,
        request_sha256=request_sha,
        source_bytes=source_bytes,
        document_id=f"sha256:{source_sha}",
        physical_page=1,
        provider_runtime_ledger=provider_ledger,
        causal_policy_path=PROJECT_ROOT / "config/ocr/causal-native-text-v1.yaml",
        quality_policy_path=PROJECT_ROOT / "config/ocr/native-text-quality-v2.yaml",
        native_ordering_policy_identity=_native_ordering_identity(),
        full_control_identity_sha256="7" * 64,
    )
    metrics = result["metrics"]
    record = {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_FULL_PAGE_RECORD_V2",
        "request_ordinal": 1,
        "document_id": f"sha256:{source_sha}",
        "source_sha256": source_sha,
        "source_size_bytes": len(source_bytes),
        "physical_page": 1,
        "route": "CAUSAL_NATIVE_TEXT",
        "request_sha256": request_sha,
        "request": request,
        "status": result["status"],
        "origin": "FRESH_SEALED_CAUSAL_NATIVE_TEXT_GATE_V2",
        "upstream_status": None,
        "upstream_origin": None,
        "upstream_unresolved": None,
        "render_ref": None,
        "backend_payload_ref": _json_object_ref(built_backend),
        "result_ref": _json_object_ref(result),
        "upstream_v2_adoption": None,
        "line_axis_count": metrics["line_count"],
        "nonempty_line_axis_count": metrics["line_count"],
        "exact_empty_line_axis_count": 0,
        "accepted_line_count": metrics["line_count"],
        "word_token_count": metrics["word_token_count"],
        "quarantined_span_count": metrics["ghost_quarantined_span_count"],
        "ordering_quarantined_raw_line_run_count": metrics[
            "ordering_quarantined_raw_line_run_count"
        ],
        "ordering_quarantined_raw_word_count": metrics["ordering_quarantined_raw_word_count"],
        "noncontiguous_line_identity_count": metrics["noncontiguous_line_identity_count"],
        "word_box_correction_count": 0,
        "word_box_corrected_edge_count": 0,
        "statement_classification_count": 0,
        "table_classification_count": 0,
        "row_reconstruction_count": 0,
        "cell_interpretation_count": 0,
        "absence_declaration_count": 0,
        "unresolved": result["status"] != "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
    }
    return record, result


def test_synthetic_exact_ocr_and_native_v2_project_and_dispose_every_atom(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pairs = (
        _synthetic_ocr_pair(),
        _synthetic_native_pair(monkeypatch, contiguity_terminal=False),
    )
    for record, result in pairs:
        projection = project_authenticated_page_v2(page_record=record, page_result=result)
        proposal = make_empty_page_proposal_set_v2(projection)
        neutral = projection["neutral_page_v1"]

        assert projection["page_record_sha256"] == canonical_json_sha256_v1(record)
        assert projection["page_result_sha256"] == record["result_ref"]["sha256"]
        assert projection["page_result_ref"] == record["result_ref"]
        assert projection["page_record_accounting"] == {
            key: record[key] for key in projection["page_record_accounting"]
        }
        assert projection["coordinate_authority"] == result["coordinate_authority"]
        assert projection["upstream_status"] == record["status"]
        assert projection["v1_compatibility_view_authoritative"] is False
        assert proposal["proposal_set_v1"]["proposals"] == []
        assert len(proposal["proposal_set_v1"]["dispositions"]) == len(neutral["atoms"])
        if record["route"] == "CAUSAL_NATIVE_TEXT":
            assert (
                projection["native_ordering_policy_identity"] == result["ordering_policy_identity"]
            )
            assert projection["native_ordering_receipt"] == result["ordering_receipt"]
        else:
            assert projection["native_ordering_policy_identity"] is None
            assert projection["native_ordering_receipt"] is None


def test_synthetic_contiguity_terminal_preserves_ghost_quarantine_without_primary_atoms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record, result = _synthetic_native_pair(
        monkeypatch,
        contiguity_terminal=True,
    )
    projection = project_authenticated_page_v2(page_record=record, page_result=result)
    proposal = make_empty_page_proposal_set_v2(projection)
    neutral = projection["neutral_page_v1"]

    assert projection["upstream_status"] == ("UNRESOLVED_CAUSAL_NATIVE_LINE_CONTIGUITY")
    assert projection["terminal_reason"] == "NoncontiguousNativeLineIdentity"
    assert projection["page_record_accounting"] == {
        "absence_declaration_count": 0,
        "accepted_line_count": 0,
        "cell_interpretation_count": 0,
        "exact_empty_line_axis_count": 0,
        "line_axis_count": 0,
        "noncontiguous_line_identity_count": 1,
        "nonempty_line_axis_count": 0,
        "ordering_quarantined_raw_line_run_count": 3,
        "ordering_quarantined_raw_word_count": 3,
        "quarantined_span_count": 1,
        "row_reconstruction_count": 0,
        "statement_classification_count": 0,
        "table_classification_count": 0,
        "word_box_corrected_edge_count": 0,
        "word_box_correction_count": 0,
        "word_token_count": 0,
    }
    assert len(neutral["atoms"]) == 1
    assert neutral["atoms"][0]["kind"] == "QUARANTINED_SPAN"
    assert neutral["atoms"][0]["authority"] == "UPSTREAM_QUARANTINE"
    assert neutral["metrics"]["quarantined_atom_count"] == 1
    assert proposal["proposal_set_v1"]["proposals"] == []
    assert len(proposal["proposal_set_v1"]["dispositions"]) == 1


def test_real_finalized_v3_four_statuses_preserve_authoritative_bindings() -> None:
    for status, (record, result) in _real_four_status_pairs().items():
        projection = project_authenticated_page_v2(
            page_record=record,
            page_result=result,
        )

        assert projection["page_record_v2"] == record
        assert projection["page_record_sha256"] == canonical_json_sha256_v1(record)
        assert projection["page_result_ref"] == record["result_ref"]
        assert projection["page_result_sha256"] == record["result_ref"]["sha256"]
        assert projection["upstream_status"] == status
        assert projection["coordinate_authority"] == result["coordinate_authority"]
        assert projection["v1_compatibility_view_authoritative"] is False
        if record["route"] == "CAUSAL_NATIVE_TEXT":
            assert (
                projection["native_ordering_policy_identity"] == result["ordering_policy_identity"]
            )
            assert projection["native_ordering_receipt"] == result["ordering_receipt"]


def test_synthetic_ocr_adoption_and_result_fields_are_exact() -> None:
    record, result = _synthetic_ocr_pair()
    project_authenticated_page_v2(page_record=record, page_result=result)

    bad_adoption = deepcopy(record)
    bad_adoption["upstream_v2_adoption"]["source_checkpoint_generation"] = 0
    with pytest.raises(SourceEvidenceProjectionV2Error, match="positive"):
        project_authenticated_page_v2(
            page_record=bad_adoption,
            page_result=result,
        )

    bad_result = deepcopy(result)
    bad_result["schema_answer"] = "forbidden"
    bad_record = deepcopy(record)
    bad_record["result_ref"] = _json_object_ref(bad_result)
    bad_record["upstream_v2_adoption"]["source_refs"]["result_ref"] = deepcopy(
        bad_record["result_ref"]
    )
    with pytest.raises(SourceEvidenceProjectionV2Error, match="drifted"):
        project_authenticated_page_v2(
            page_record=bad_record,
            page_result=bad_result,
        )


@pytest.mark.skipif(
    os.environ.get("BCTC_RUN_REAL_V3_1449") != "1",
    reason="real finalized-V3 projection replay is an explicit integration gate",
)
def test_real_finalized_v3_all_1449_projects_exact_accounting() -> None:
    counts = Counter()
    documents = set()
    for record, result in _finalized_records():
        projection = project_authenticated_page_v2(page_record=record, page_result=result)
        neutral = projection["neutral_page_v1"]
        metrics = neutral["metrics"]
        accounting = projection["page_record_accounting"]
        documents.add(record["document_id"])
        counts["pages"] += 1
        counts["atoms"] += metrics["atom_count"]
        counts["primary_lines"] += metrics["primary_line_count"]
        counts["empty_lines"] += metrics["excluded_empty_line_axis_count"]
        counts["words"] += metrics["primary_word_count"]
        counts["quarantine_atoms"] += metrics["quarantined_atom_count"]
        counts["record_line_axes"] += accounting["line_axis_count"]
        counts["record_words"] += accounting["word_token_count"]
        counts["record_quarantine"] += accounting["quarantined_span_count"]
        counts["terminal"] += record["unresolved"]
        counts[f"route:{record['route']}"] += 1
        counts[f"status:{record['status']}"] += 1

    assert len(documents) == 27
    assert counts == Counter(
        {
            "pages": 1_449,
            "atoms": 1_454_160,
            "primary_lines": 103_246,
            "empty_lines": 65,
            "words": 1_350_798,
            "quarantine_atoms": 51,
            "record_line_axes": 103_311,
            "record_words": 1_350_798,
            "record_quarantine": 51,
            "terminal": 59,
            "route:DOMINANT_RASTER_OCR": 1_356,
            "route:CAUSAL_NATIVE_TEXT": 93,
            "status:OCR_WORD_BOX_READ_COMPLETE": 1_299,
            "status:UNRESOLVED_OCR_WORD_BOX_GEOMETRY": 57,
            "status:CAUSAL_NATIVE_TEXT_READ_COMPLETE": 91,
            "status:UNRESOLVED_CAUSAL_NATIVE_VISIBILITY": 2,
        }
    )


@pytest.mark.parametrize(
    "mutation",
    ("foreign_record_field", "record_accounting", "foreign_result_field"),
)
def test_exact_v2_record_and_result_schemas_reject_tampering(
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    record, result = _synthetic_native_pair(
        monkeypatch,
        contiguity_terminal=False,
    )
    if mutation == "foreign_record_field":
        record["bank"] = "forbidden"
    elif mutation == "record_accounting":
        record["word_token_count"] += 1
    else:
        result["schema_answer"] = "forbidden"
        _refresh_native_result_ref(record, result)
    with pytest.raises(SourceEvidenceProjectionV2Error, match="drifted"):
        project_authenticated_page_v2(page_record=record, page_result=result)


@pytest.mark.parametrize("axis", ("coordinate", "ordering"))
def test_native_v2_coordinate_and_order_authority_are_exact(
    monkeypatch: pytest.MonkeyPatch,
    axis: str,
) -> None:
    record, result = _synthetic_native_pair(
        monkeypatch,
        contiguity_terminal=False,
    )
    if axis == "coordinate":
        result["coordinate_authority"]["canonical_cropbox_bounds_mpt"][2] += 1
    else:
        result["ordering_receipt"]["line_run_count"] += 1
    _refresh_native_result_ref(record, result)
    with pytest.raises(SourceEvidenceProjectionV2Error, match="drifted"):
        project_authenticated_page_v2(page_record=record, page_result=result)


def test_compatibility_view_cannot_be_promoted_or_detached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record, result = _synthetic_native_pair(
        monkeypatch,
        contiguity_terminal=False,
    )
    projection = project_authenticated_page_v2(page_record=record, page_result=result)

    promoted = deepcopy(projection)
    promoted["v1_compatibility_view_authoritative"] = True
    with pytest.raises(SourceStructureContractV2Error, match="promoted"):
        validate_source_evidence_projection_v2(promoted)

    detached = deepcopy(projection)
    detached["page_record_accounting"]["word_token_count"] += 1
    with pytest.raises(SourceStructureContractV2Error, match="accounting|authority"):
        validate_source_evidence_projection_v2(detached)


def test_embedded_page_record_rejects_self_refreshed_accounting_and_request_safety(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record, result = _synthetic_native_pair(
        monkeypatch,
        contiguity_terminal=False,
    )
    projection = project_authenticated_page_v2(page_record=record, page_result=result)

    accounting_forgery = deepcopy(projection)
    accounting_forgery["page_record_v2"]["word_token_count"] += 1
    accounting_forgery["page_record_accounting"]["word_token_count"] += 1
    accounting_forgery["page_record_sha256"] = canonical_json_sha256_v1(
        accounting_forgery["page_record_v2"]
    )
    _refresh_projection_identity(accounting_forgery)
    with pytest.raises(SourceStructureContractV2Error, match="accounting|authority"):
        validate_source_evidence_projection_v2(accounting_forgery)

    request_forgery = deepcopy(projection)
    request = request_forgery["page_record_v2"]["request"]
    request["bank_identity_used"] = True
    request_forgery["page_record_v2"]["request_sha256"] = canonical_json_sha256_v1(request)
    request_forgery["source_locator"]["request_sha256"] = request_forgery["page_record_v2"][
        "request_sha256"
    ]
    request_forgery["page_record_sha256"] = canonical_json_sha256_v1(
        request_forgery["page_record_v2"]
    )
    _refresh_projection_identity(request_forgery)
    with pytest.raises(SourceStructureContractV2Error, match="safety"):
        validate_source_evidence_projection_v2(request_forgery)


@pytest.mark.parametrize(
    "forgery",
    ("policy", "receipt_schema", "source_words_sha256", "line_runs_sha256"),
)
def test_native_ordering_wrapper_rejects_self_refreshed_forgery(
    monkeypatch: pytest.MonkeyPatch,
    forgery: str,
) -> None:
    record, result = _synthetic_native_pair(
        monkeypatch,
        contiguity_terminal=False,
    )
    projection = project_authenticated_page_v2(page_record=record, page_result=result)
    forged = deepcopy(projection)
    if forgery == "policy":
        policy = forged["native_ordering_policy_identity"]
        policy["path"] = "config/ocr/forged-ordering.yaml"
        forged["native_ordering_policy_identity_sha256"] = canonical_json_sha256_v1(policy)
        forged["native_ordering_receipt"]["ordering_policy_identity"] = deepcopy(policy)
    elif forgery == "receipt_schema":
        forged["native_ordering_receipt"]["foreign_count"] = 0
    else:
        forged["native_ordering_receipt"][forgery] = "f" * 64
    forged["native_ordering_receipt_sha256"] = canonical_json_sha256_v1(
        forged["native_ordering_receipt"]
    )
    _refresh_projection_identity(forged)
    with pytest.raises(SourceStructureContractV2Error, match="ordering"):
        validate_source_evidence_projection_v2(forged)


def test_general_v2_wrapper_accepts_nonempty_validated_v1_geometry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record, result = _synthetic_native_pair(
        monkeypatch,
        contiguity_terminal=False,
    )
    projection = project_authenticated_page_v2(page_record=record, page_result=result)
    neutral = projection["neutral_page_v1"]
    primary = next(atom for atom in neutral["atoms"] if atom["kind"] == "LINE")
    evidence_codes = ["BBOX_CONTAINS_PRIMARY_ATOMS", "LOCAL_GEOMETRY"]
    proposal_identity = {
        "source_local_page_id": neutral["source_local_page_id"],
        "request_sha256": neutral["source_locator"]["request_sha256"],
        "kind": "SOURCE_BLOCK_CANDIDATE",
        "canonical_bbox_mpt": primary["canonical_bbox_mpt"],
        "primary_atom_ids": [primary["source_local_id"]],
        "supporting_atom_ids": [],
        "evidence_codes": evidence_codes,
    }
    proposal_id = make_source_object_id_v1("source_object", proposal_identity)
    v1_proposal = {
        "source_local_id": proposal_id,
        "kind": "SOURCE_BLOCK_CANDIDATE",
        "canonical_bbox_mpt": primary["canonical_bbox_mpt"],
        "primary_atom_ids": [primary["source_local_id"]],
        "supporting_atom_ids": [],
        "evidence_codes": evidence_codes,
    }
    dispositions = []
    for atom in neutral["atoms"]:
        owned = atom["source_local_id"] == primary["source_local_id"]
        dispositions.append(
            {
                "format_version": ATOM_DISPOSITION_FORMAT_VERSION,
                "source_atom_id": atom["source_local_id"],
                "primary_disposition": ("OWNED_BY_SOURCE_OBJECT" if owned else "RETAINED_UNOWNED"),
                "source_object_id": proposal_id if owned else None,
                "reason_code": (
                    "PRIMARY_LOCAL_GEOMETRY_OWNERSHIP"
                    if owned
                    else "NO_SOURCE_OBJECT_OWNERSHIP_PROPOSED"
                ),
            }
        )
    proposal_set_v1 = make_page_proposal_set_v1(
        neutral,
        proposals=[v1_proposal],
        dispositions=dispositions,
    )

    wrapped = make_page_proposal_set_v2(
        projection,
        proposal_set_v1=proposal_set_v1,
    )

    assert wrapped["source_projection_sha256"] == canonical_json_sha256_v1(projection)
    assert wrapped["proposal_set_v1"]["proposals"] == [v1_proposal]
    assert len(wrapped["proposal_set_v1"]["dispositions"]) == len(neutral["atoms"])


def test_v2_projection_imports_no_answer_or_routing_layer() -> None:
    allowed_internal = {
        "bctc_ai.ocr.causal_native_text_evidence_v2",
        "bctc_ai.source_structure.contracts_v1",
        "bctc_ai.source_structure.contracts_v2",
        "bctc_ai.source_structure.evidence_projection_v1",
    }
    for relative in (
        "src/bctc_ai/source_structure/contracts_v2.py",
        "src/bctc_ai/source_structure/evidence_projection_v2.py",
    ):
        tree = ast.parse((PROJECT_ROOT / relative).read_text(encoding="utf-8"))
        imported = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        internal = {name for name in imported if name.startswith("bctc_ai.")}
        assert internal <= allowed_internal
        assert not any(
            fragment in name.casefold()
            for name in internal
            for fragment in ("mapping", "reference", "schema", "history", "role_a")
        )
