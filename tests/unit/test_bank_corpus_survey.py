from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from bctc_ai.core.hashing import sha256_bytes
from bctc_ai.corpus.bank_survey import (
    POLICY_RELATIVE_PATH,
    BankCorpusSurveyError,
    _classify_source_route,
    _filename_metadata,
    build_bank_corpus_inventory,
    build_wave_one_source_profile,
    publish_bank_corpus_inventory,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_real_registered_inventory_is_complete_and_wave_one_is_bank_wide() -> None:
    payload = build_bank_corpus_inventory(PROJECT_ROOT, PROJECT_ROOT / POLICY_RELATIVE_PATH)
    accounting = payload["accounting"]
    selection = payload["wave_1"]

    assert accounting["registered_bank_count"] == 27
    assert accounting["registered_pdf_path_count"] == 2_567
    assert accounting["unique_pdf_content_count"] == 2_435
    assert accounting["duplicate_content_group_count"] == 132
    assert accounting["duplicate_extra_path_count"] == 132
    assert accounting["registered_pdf_bytes"] == 17_761_344_114
    assert selection["selected_bank_count"] == 27
    assert selection["selected_document_count"] == 27
    assert len({record["bank"] for record in selection["selected_documents"]}) == 27
    assert all(
        record["selection_status"] == "SELECTED_PENDING_SOURCE_SURVEY"
        and record["source_type_used_for_selection"] is False
        and record["dataset_role"] != "UNTOUCHED_HOLDOUT"
        for record in selection["selected_documents"]
    )
    assert accounting["filename_metadata_authoritative"] is False
    assert accounting["source_type_assessment_status"] == "PENDING_PDF_INSPECTION"


def test_wave_one_prefers_target_period_but_records_fallbacks() -> None:
    payload = build_bank_corpus_inventory(PROJECT_ROOT, PROJECT_ROOT / POLICY_RELATIVE_PATH)
    selected = {record["bank"]: record for record in payload["wave_1"]["selected_documents"]}

    projection = [
        {
            key: record[key]
            for key in ("bank", "document_id", "sha256", "size_bytes", "relative_path")
        }
        for record in payload["wave_1"]["selected_documents"]
    ]
    projection_bytes = (
        json.dumps(projection, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    assert sha256_bytes(projection_bytes) == (
        "832cea1bee22f0bb08c422490dd2afe4e23bc91c56cdee6db382b1bfdc744d28"
    )
    assert payload["wave_1"]["selection_receipt_sha256"] == sha256_bytes(projection_bytes)
    assert payload["wave_1"]["selection_receipt_size_bytes"] == 7_665
    assert payload["wave_1"]["selected_document_bytes"] == 248_588_591
    assert payload["wave_1"]["selection_rationale_counts"] == {
        "FALLBACK_Q2_2026_SCOPE_UNKNOWN": 2,
        "FALLBACK_Q2_2026_SEPARATE_SCOPE": 1,
        "PRIMARY_COMPARABLE_VI_Q2_2026_CONSOLIDATED": 23,
        "REUSED_REGISTERED_DEVELOPMENT_EVIDENCE_AFTER_METADATA_TIE": 1,
    }
    assert payload["wave_1"]["selected_dataset_role_counts"] == {
        "CALIBRATION": 2,
        "LOGIC_DEVELOPMENT": 1,
        "UNASSIGNED": 24,
    }
    assert payload["wave_1"]["filename_derived_counts"] == {
        "document_kind": {
            "FULL_FINANCIAL_STATEMENT_CANDIDATE": 27,
            "SUPPORTING_OR_PARTIAL_DOCUMENT": 0,
            "UNCLASSIFIED_DOCUMENT_KIND": 0,
        },
        "scope_hint": {
            "CONSOLIDATED": 24,
            "SEPARATE": 1,
            "UNKNOWN": 2,
            "AMBIGUOUS": 0,
        },
        "reporting_period_hint": {
            "ANNUAL": 0,
            "H1": 0,
            "Q1": 0,
            "Q2": 26,
            "Q3": 0,
            "Q4": 0,
            "UNKNOWN": 1,
            "AMBIGUOUS": 0,
        },
        "assurance_hint": {
            "AUDITED": 0,
            "REVIEWED": 0,
            "UNAUDITED": 0,
            "UNKNOWN": 27,
            "AMBIGUOUS": 0,
        },
        "language_hint": {
            "VI": 27,
            "EN": 0,
            "BILINGUAL_OR_AMBIGUOUS": 0,
            "UNKNOWN": 0,
        },
        "source_type_hint": {
            "SEARCHABLE_FILENAME_HINT": 1,
            "UNASSESSED_REQUIRES_PDF_INSPECTION": 26,
        },
    }

    assert selected["MBB"]["filename_metadata"]["reporting_period_hint"] == "Q2"
    assert selected["MBB"]["filename_metadata"]["scope_hint"] == "CONSOLIDATED"
    # The preserved VPB filename does not encode a quarter. Source inspection may
    # later establish Q1, but the metadata inventory must not infer it from prior work.
    assert selected["VPB"]["filename_metadata"]["reporting_period_hint"] == "UNKNOWN"
    assert selected["VPB"]["preferred_variant_matched"]["period"] is False
    assert selected["ABB"]["filename_metadata"]["scope_hint"] == "SEPARATE"
    assert selected["ABB"]["preferred_variant_matched"]["scope"] is False
    assert selected["LPB"]["filename_metadata"]["scope_hint"] == "UNKNOWN"
    assert selected["PGB"]["filename_metadata"]["scope_hint"] == "UNKNOWN"
    assert selected["SGB"]["relative_path"].endswith(
        "5_sgb_2026_7_27_989deeb_vi__bao_cao_tai_chinh_hop_nhat_q22026_daky.pdf"
    )


def test_filename_metadata_is_conservative_for_compact_and_vietnamese_forms() -> None:
    h1 = _filename_metadata(
        "vietstock_bctc/AAA/2026/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2026.pdf",
        2026,
    )
    supporting = _filename_metadata(
        "vietstock_bctc/AAA/2026/2_vi_giaitrinhlienquandenbctc_q2_2026.pdf",
        2026,
    )
    unaudited = _filename_metadata(
        "vietstock_bctc/AAA/2026/BCTC hopnhat Q2 2026 chua kiem toan.pdf",
        2026,
    )

    assert h1["reporting_period_hint"] == "H1"
    assert h1["assurance_hint"] == "REVIEWED"
    assert supporting["document_kind"] == "SUPPORTING_OR_PARTIAL_DOCUMENT"
    assert unaudited["scope_hint"] == "CONSOLIDATED"
    assert unaudited["assurance_hint"] == "UNAUDITED"


def test_source_route_profile_is_page_evidence_driven() -> None:
    cases = (
        ((0, 0, 10, 10), "SCAN_ROUTE"),
        ((2, 2, 10, 10), "MIXED_PAGE_HYBRID_ROUTE"),
        (
            (10, 0, 10, 10),
            "SEARCHABLE_OVER_IMAGE_REQUIRES_GHOST_TEXT_VALIDATION",
        ),
        ((10, 10, 1, 0), "NATIVE_SEARCHABLE_ROUTE"),
        ((0, 0, 0, 0), "UNRESOLVED_SOURCE_ROUTE"),
    )
    for counts, expected in cases:
        assert (
            _classify_source_route(
                page_count=10,
                substantive_extracted_text_pages=counts[0],
                substantive_nonzero_alpha_text_pages=counts[1],
                displayed_image_pages=counts[2],
                dominant_raster_pages=counts[3],
            )
            == expected
        )
    with pytest.raises(BankCorpusSurveyError, match="page-evidence"):
        _classify_source_route(
            page_count=10,
            substantive_extracted_text_pages=11,
            substantive_nonzero_alpha_text_pages=0,
            displayed_image_pages=0,
            dominant_raster_pages=0,
        )


@pytest.mark.skipif(
    not (
        PROJECT_ROOT / "vietstock_bctc/ABB/2026/"
        "phpnchaip-bao-cao-tai-chinh-rieng-le-quy-ii-nam-2026-6a5df290b2d0a.pdf"
    ).is_file(),
    reason="Wave 1 PDFs are deliberately offloaded in lean checkouts",
)
def test_hydrated_wave_one_source_profile_has_exact_page_accounting() -> None:
    payload = build_wave_one_source_profile(PROJECT_ROOT, PROJECT_ROOT / POLICY_RELATIVE_PATH)

    assert payload["accounting"] == {
        "selected_document_count": 27,
        "source_profiled_document_count": 27,
        "structurally_surveyed_document_count": 0,
        "source_accounted_statement_block_count": 0,
        "source_accounted_visible_row_count": 0,
        "source_accounted_visible_value_cell_count": 0,
        "total_pdf_page_count": 1_449,
        "any_extractable_text_layer_page_count": 156,
        "substantive_extractable_text_layer_page_count": 156,
        "substantive_nonzero_alpha_text_layer_page_count": 111,
        "substantive_zero_alpha_text_layer_page_count": 46,
        "displayed_image_page_count": 1_363,
        "dominant_displayed_raster_page_count": 1_356,
        "no_extracted_text_or_displayed_image_page_count": 0,
        "source_route_counts": {
            "SCAN_ROUTE": 11,
            "MIXED_PAGE_HYBRID_ROUTE": 14,
            "SEARCHABLE_OVER_IMAGE_REQUIRES_GHOST_TEXT_VALIDATION": 1,
            "NATIVE_SEARCHABLE_ROUTE": 1,
            "UNRESOLVED_SOURCE_ROUTE": 0,
        },
        "source_route_page_quadrant_counts": {
            "TEXT_LAYER_AND_DOMINANT_RASTER": 63,
            "TEXT_LAYER_AND_NONDOMINANT_RASTER": 93,
            "NO_TEXT_LAYER_AND_DOMINANT_RASTER": 1_293,
            "NO_TEXT_LAYER_AND_NONDOMINANT_RASTER": 0,
        },
        "ocr_executed": False,
        "schema_used": False,
        "canonical_mapping_attempted": False,
    }
    profiles = {profile["bank"]: profile for profile in payload["profiles"]}
    assert profiles["HDB"]["source_route_recommendation"] == (
        "SEARCHABLE_OVER_IMAGE_REQUIRES_GHOST_TEXT_VALIDATION"
    )
    assert profiles["HDB"]["substantive_zero_alpha_text_layer_page_count"] == 44
    assert profiles["HDB"]["dominant_displayed_raster_page_count"] == 44
    assert profiles["MSB"]["displayed_image_page_count"] == 57
    assert profiles["VBB"]["substantive_extractable_text_layer_page_count"] == 2
    assert profiles["VBB"]["substantive_nonzero_alpha_text_layer_page_count"] == 1
    assert profiles["VPB"]["source_route_recommendation"] == "NATIVE_SEARCHABLE_ROUTE"
    assert profiles["VPB"]["substantive_nonzero_alpha_text_layer_page_count"] == 91
    assert profiles["VPB"]["dominant_displayed_raster_page_count"] == 0


def test_policy_rejects_source_type_or_schema_routing(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / POLICY_RELATIVE_PATH.parent).mkdir(parents=True)
    policy = yaml.safe_load((PROJECT_ROOT / POLICY_RELATIVE_PATH).read_text(encoding="utf-8"))
    policy["wave_1"]["source_type_used_for_selection"] = True
    (project / POLICY_RELATIVE_PATH).write_text(
        yaml.safe_dump(policy, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )

    with pytest.raises(BankCorpusSurveyError, match="selection gates"):
        build_bank_corpus_inventory(project, project / POLICY_RELATIVE_PATH)


def test_dataset_role_must_bind_an_exact_registered_source_path(tmp_path: Path) -> None:
    root = tmp_path / "project"
    fixture_paths = (
        POLICY_RELATIVE_PATH,
        Path("data/registered/bank_registry.json"),
        Path("data/registered/source_registry.jsonl"),
        Path("data/registered/dataset_roles.jsonl"),
        Path("src/bctc_ai/corpus/bank_survey.py"),
    )
    for relative in fixture_paths:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((PROJECT_ROOT / relative).read_bytes())
    role_path = root / "data/registered/dataset_roles.jsonl"
    records = [json.loads(line) for line in role_path.read_text(encoding="utf-8").splitlines()]
    records[0]["source_path"] = records[1]["source_path"]
    role_path.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records
        ),
        encoding="utf-8",
    )

    with pytest.raises(BankCorpusSurveyError, match="malformed record"):
        build_bank_corpus_inventory(root, root / POLICY_RELATIVE_PATH)


def test_publication_is_canonical_and_exclusive(tmp_path: Path) -> None:
    root = tmp_path / "project"
    for relative in (
        POLICY_RELATIVE_PATH,
        Path("data/registered/bank_registry.json"),
        Path("data/registered/source_registry.jsonl"),
        Path("data/registered/dataset_roles.jsonl"),
        Path("src/bctc_ai/corpus/bank_survey.py"),
    ):
        source = PROJECT_ROOT / relative
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    output = root / "output/development/bank-corpus-survey-v1/corpus-inventory.json"
    path, digest, size = publish_bank_corpus_inventory(root, output_path=output)
    encoded = path.read_bytes()
    payload = json.loads(encoded)

    assert digest == sha256_bytes(encoded)
    assert size == len(encoded)
    assert encoded == (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    with pytest.raises(BankCorpusSurveyError, match="already exists"):
        publish_bank_corpus_inventory(root, output_path=output)
