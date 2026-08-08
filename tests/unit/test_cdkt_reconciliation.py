from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from bctc_ai.reconciliation.cdkt import (
    CDKTReconciliationError,
    TargetedNumericReread,
    bind_visible_report_scope,
    resolve_closed_subtype_absences,
    resolve_invalid_numeric_challenger,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
E0037_PATH = PROJECT_ROOT / "docs/experiments/E-0037-mbb-cdkt-sealed-evidence-mapping.json"
E0040_PATH = PROJECT_ROOT / "output/calibration/e0040-mbb-cdkt-formal-mapping/mapping_only.json"
E0041_PROVENANCE_PATH = (
    PROJECT_ROOT
    / "output/calibration/e0041-mbb-cdkt-post-mapping-development-excel/provenance.json"
)
CELL_CROP_PATH = (
    PROJECT_ROOT / "output/calibration/e0041-mbb-cdkt-reconstructed-geometry/65fa9b7c0de1/crops/"
    "page-0004-row-011-axis-1.png"
)
PP_OCRV6_MEDIUM_REC_SHA256 = "1b01c79a914587933f615569e75de54f2e638ebb5d3f3b3c1b38c24ede8c7319"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _cdkt_materials():
    evidence = _json(E0037_PATH)
    mapping = _json(E0040_PATH)["challenger_result"]["final_result"]
    return evidence, mapping


def _absence_resolution(evidence, mapping, *, complete=True):
    return resolve_closed_subtype_absences(
        schema_nodes=evidence["schema_projection"]["nodes"],
        source_rows=evidence["rows"],
        row_mappings=mapping["row_mappings"],
        schema_dispositions=mapping["schema_dispositions"],
        source_row_denominator_complete=complete,
    )


def _p4r11_numeric_evidence(evidence):
    return next(
        cell["numeric_evidence"]
        for cell in evidence["cells"]
        if cell["cell_id"] == "page-0004-row-011-axis-1"
    )


def _targeted_reread(crop_sha256: str, raw_text: str = "2.320"):
    return TargetedNumericReread(
        raw_text=raw_text,
        crop_sha256=crop_sha256,
        reader_model_sha256=PP_OCRV6_MEDIUM_REC_SHA256,
        reading_pass_id="PP_OCRV6_EXACT_CELL_CROP",
    )


def test_closed_parent_and_subtype_filter_resolve_only_finance_lease_absence():
    evidence, mapping = _cdkt_materials()
    before = {
        item["report_norm_id"]
        for item in mapping["schema_dispositions"]
        if item["status"] == "UNMATCHED_SCHEMA_NODE_WITH_SKIPPED_CANDIDATES"
    }

    resolved = _absence_resolution(evidence, mapping)

    assert before == {4329, 4369, 4370}
    assert [item.report_norm_id for item in resolved] == [4329, 4369, 4370]
    assert {item.status for item in resolved} == {"NOT_OBSERVED_IN_THIS_PDF"}
    assert resolved[0].mapped_sibling_report_norm_ids == (4328, 4330)
    assert resolved[1].root_report_norm_id == resolved[2].root_report_norm_id == 4329
    assert len(before) * 2 == 6  # AMBIGUOUS schema-period cells before reconciliation.
    assert len(resolved) * 2 == 6  # NOT_OBSERVED schema-period cells after reconciliation.


def test_subtype_absence_fails_closed_for_incomplete_or_combined_visible_family():
    evidence, mapping = _cdkt_materials()
    assert _absence_resolution(evidence, mapping, complete=False) == ()

    combined = deepcopy(evidence)
    row = next(item for item in combined["rows"] if item["row_id"] == "page-0003-row-023-label")
    row["semantic_proposals"]["vietocr"] = (
        "Tài sản cố định hữu hình và tài sản cố định thuê tài chính"
    )

    assert _absence_resolution(combined, mapping) == ()


def test_p4r11_invalid_challenger_resolves_from_exact_crop_reread_and_pixels():
    evidence, mapping = _cdkt_materials()
    numeric = _p4r11_numeric_evidence(evidence)
    provenance = _json(E0041_PROVENANCE_PATH)
    mapped_row = next(
        item for item in mapping["row_mappings"] if item["row_id"] == "page-0004-row-011-label"
    )

    result = resolve_invalid_numeric_challenger(
        numeric,
        crop_bytes=CELL_CROP_PATH.read_bytes(),
        targeted_rereads=[_targeted_reread(numeric["crop_sha256"])],
        primary_reading_pass_id="PP_OCRV6_PAGE_LINE",
    )

    assert mapped_row["selected_report_norm_id"] == 4363
    assert numeric["primary"]["raw_text"] == "2.320"
    assert numeric["challenger"]["raw_text"] == ".20"
    assert numeric["challenger"]["parsed_observation"] == "INVALID"
    assert result.verification_status == "VERIFIED_OBSERVED_VALUE"
    assert result.selected_raw_value == "2.320"
    assert result.normalized_numeric_value == "2320"
    assert result.pixel_glyph_pattern == (
        "DIGIT",
        "SEPARATOR",
        "DIGIT",
        "DIGIT",
        "DIGIT",
    )
    assert provenance["metrics"]["exported_numeric_cell_count"] == 111
    assert provenance["metrics"]["physical_cell_status_counts"]["UNRESOLVED"] == 7
    assert provenance["metrics"]["exported_numeric_cell_count"] + 1 == 112
    assert provenance["metrics"]["physical_cell_status_counts"]["UNRESOLVED"] - 1 == 6


def test_numeric_fallback_rejects_valid_conflict_reread_drift_and_crop_drift():
    evidence, _mapping = _cdkt_materials()
    numeric = _p4r11_numeric_evidence(evidence)
    crop_bytes = CELL_CROP_PATH.read_bytes()
    valid_conflict = deepcopy(numeric)
    valid_conflict["challenger"].update(
        {
            "raw_text": "2.020",
            "parsed_observation": "VALUE",
            "parsed_value": "2020",
            "parse_reason": None,
        }
    )

    conflict = resolve_invalid_numeric_challenger(
        valid_conflict,
        crop_bytes=crop_bytes,
        targeted_rereads=[_targeted_reread(numeric["crop_sha256"])],
        primary_reading_pass_id="PP_OCRV6_PAGE_LINE",
    )
    reread_drift = resolve_invalid_numeric_challenger(
        numeric,
        crop_bytes=crop_bytes,
        targeted_rereads=[_targeted_reread(numeric["crop_sha256"], raw_text=".20")],
        primary_reading_pass_id="PP_OCRV6_PAGE_LINE",
    )

    assert conflict.verification_status == "UNRESOLVED_READER_DISAGREEMENT"
    assert reread_drift.verification_status == "UNRESOLVED_READER_DISAGREEMENT"
    with pytest.raises(CDKTReconciliationError, match="crop identity"):
        resolve_invalid_numeric_challenger(
            numeric,
            crop_bytes=crop_bytes + b"drift",
            targeted_rereads=[_targeted_reread(numeric["crop_sha256"])],
            primary_reading_pass_id="PP_OCRV6_PAGE_LINE",
        )


def test_visible_title_binds_consolidated_scope_without_filename_inference():
    evidence = _json(E0037_PATH)
    result = bind_visible_report_scope(
        [
            "BÁO CÁO TiNH HìNH TÀI CHÍNH HP NHÁT",
            "BÁO CÁO TINH HINH TÀI CHÍNH HP NHÁT (tip theo)",
        ],
        current_scope=evidence["report_scope"]["value"],
    )

    assert evidence["report_scope"]["value"] == "UNKNOWN"
    assert result.scope == "CONSOLIDATED"
    assert result.status == "BOUND_FROM_VISIBLE_TITLE"
    assert len(result.evidence_keys) == 2


def test_visible_scope_binding_rejects_conflict_and_supports_exact_separate_title():
    conflict = bind_visible_report_scope(
        [
            "BÁO CÁO TÌNH HÌNH TÀI CHÍNH HỢP NHẤT",
            "BÁO CÁO TÌNH HÌNH TÀI CHÍNH RIÊNG",
        ]
    )
    separate = bind_visible_report_scope(["BÁO CÁO TÌNH HÌNH TÀI CHÍNH RIÊNG LẺ"])

    assert conflict.scope == "UNKNOWN"
    assert conflict.status == "UNRESOLVED_VISIBLE_TITLE_SCOPE"
    assert separate.scope == "SEPARATE"
    assert separate.status == "BOUND_FROM_VISIBLE_TITLE"
