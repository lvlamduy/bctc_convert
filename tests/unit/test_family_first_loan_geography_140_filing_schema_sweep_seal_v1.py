from __future__ import annotations

import copy
import hashlib
import json
import stat
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEAL_PATH = ROOT / (
    "docs/experiments/"
    "E-0175-family-first-loan-geography-140-filing-schema-sweep-seal-v1.json"
)


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _seal_digest(seal: dict[str, object]) -> str:
    material = dict(seal)
    material.pop("seal_id")
    canonical = json.dumps(
        material, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def test_loan_geography_seal_is_hash_bound_closed_and_tamper_sensitive() -> None:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    assert set(seal) == {
        "authority",
        "bank_summary",
        "claim_boundary",
        "family_id",
        "formal_result_ref",
        "format_version",
        "git_commit",
        "implementation_refs",
        "input_identities",
        "input_refs",
        "metrics",
        "seal_id",
        "state",
        "sweep_id",
    }
    assert seal["seal_id"] == "e0175:seal:" + _seal_digest(seal)
    assert seal["format_version"] == (
        "FAMILY_FIRST_LOAN_GEOGRAPHY_140_FILING_SCHEMA_SWEEP_SEAL_V1"
    )
    assert seal["state"] == "COMPLETE"
    assert seal["family_id"] == "LOAN_GEOGRAPHIC_CLASSIFICATION"
    assert seal["git_commit"] == "350ad6f46d1ff3685f127ea08ff852e56d1b4618"
    assert seal["sweep_id"] == (
        "lg140v1:sweep:31983f20ac0700e5a7c4ab2be463de1808a8a34bbe695e0a67583365f76dbeae"
    )

    metrics = seal["metrics"]
    assert set(metrics) == {
        "absence_numeric_pixel_or_total_control_hydration_count",
        "accounting_backsolved_or_invented_value_count",
        "bank_broad_bounded_absence_counts",
        "bank_document_counts",
        "bank_exact_counts",
        "bank_mapped_record_counts",
        "bank_not_observed_counts",
        "bank_repeated_full_segment_counts",
        "bank_visible_dash_zero_counts",
        "broad_bounded_absence_trial_count",
        "broad_mixed_population_trial_count",
        "broad_total_population_trial_count",
        "column_layout_trial_count",
        "continuation_mode_trial_counts",
        "customer_loan_total_control_public_replay_count",
        "customer_loan_total_control_request_count",
        "customer_loan_total_control_request_set_count",
        "direct_whole_document_line_count",
        "direct_whole_document_page_count",
        "document_count",
        "document_inherited_period_lane_count",
        "document_inherited_unit_trial_count",
        "document_pdf_internal_context_evidence_count",
        "exact_accounting_equation_count",
        "exact_customer_loan_geography_trial_count",
        "gemma_request_count",
        "known_nested_domestic_mapping_count",
        "local_upstream_total_control_conflict_count",
        "mapped_money_cell_count",
        "mapped_parent_716_or_759_record_count",
        "mapped_record_count",
        "multiple_identical_region_count",
        "not_observed_trial_count",
        "numeric_gemma_authority_count",
        "numeric_unresolved_observed_cell_count",
        "numeric_vetoed_equation_count",
        "observed_numeric_mapped_cell_count",
        "partial_continuation_trial_count",
        "partial_nonterminal_graph_count",
        "ppocrv6_vietocr_numeric_disagreement_count",
        "printed_customer_loan_total_control_cell_count",
        "printed_customer_loan_total_control_source_mode_counts",
        "region_retrieval_mapping_or_absence_authority_count",
        "repeated_full_segment_trial_count",
        "row_layout_trial_count",
        "schema_report_norm_id_record_counts",
        "sparse_hydrated_line_count",
        "sparse_hydrated_page_count",
        "sparse_line_reduction_ppm",
        "sparse_page_reduction_ppm",
        "sparse_to_whole_document_equivalence_count",
        "unresolved_trial_count",
        "upstream_customer_loan_total_control_document_count",
        "upstream_customer_loan_total_control_lane_count",
        "visible_dash_zero_cell_count",
    }
    assert {
        key: metrics[key]
        for key in (
            "document_count",
            "exact_customer_loan_geography_trial_count",
            "broad_bounded_absence_trial_count",
            "not_observed_trial_count",
            "unresolved_trial_count",
            "mapped_record_count",
            "mapped_money_cell_count",
            "observed_numeric_mapped_cell_count",
            "visible_dash_zero_cell_count",
            "exact_accounting_equation_count",
        )
    } == {
        "document_count": 140,
        "exact_customer_loan_geography_trial_count": 38,
        "broad_bounded_absence_trial_count": 78,
        "not_observed_trial_count": 24,
        "unresolved_trial_count": 0,
        "mapped_record_count": 76,
        "mapped_money_cell_count": 130,
        "observed_numeric_mapped_cell_count": 88,
        "visible_dash_zero_cell_count": 42,
        "exact_accounting_equation_count": 65,
    }
    assert metrics["document_count"] == sum(
        metrics[key]
        for key in (
            "exact_customer_loan_geography_trial_count",
            "broad_bounded_absence_trial_count",
            "not_observed_trial_count",
            "unresolved_trial_count",
        )
    )
    assert metrics["broad_bounded_absence_trial_count"] == (
        metrics["broad_mixed_population_trial_count"]
        + metrics["broad_total_population_trial_count"]
    )
    assert metrics["mapped_record_count"] == 2 * metrics[
        "exact_customer_loan_geography_trial_count"
    ]
    assert metrics["schema_report_norm_id_record_counts"] == {"5752": 38, "765": 38}
    assert metrics["mapped_money_cell_count"] == (
        metrics["observed_numeric_mapped_cell_count"]
        + metrics["visible_dash_zero_cell_count"]
    )
    assert metrics["printed_customer_loan_total_control_cell_count"] == sum(
        metrics["printed_customer_loan_total_control_source_mode_counts"].values()
    )
    assert metrics["customer_loan_total_control_request_set_count"] == metrics[
        "exact_customer_loan_geography_trial_count"
    ]
    assert metrics["customer_loan_total_control_request_count"] == metrics[
        "upstream_customer_loan_total_control_lane_count"
    ]
    assert metrics["sparse_to_whole_document_equivalence_count"] == metrics[
        "document_count"
    ]

    summary = seal["bank_summary"]
    assert [item["bank"] for item in summary] == [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert metrics["bank_document_counts"] == {
        item["bank"]: item["document_count"] for item in summary
    }
    assert metrics["bank_exact_counts"] == {
        item["bank"]: item["verified_exact_document_count"] for item in summary
    }
    assert metrics["bank_broad_bounded_absence_counts"] == {
        item["bank"]: item["verified_broad_bounded_absence_document_count"]
        for item in summary
    }
    assert metrics["bank_not_observed_counts"] == {
        item["bank"]: item["verified_not_observed_document_count"] for item in summary
    }
    assert metrics["bank_mapped_record_counts"] == {
        item["bank"]: item["mapped_record_count"] for item in summary
    }
    assert metrics["bank_visible_dash_zero_counts"] == {
        item["bank"]: item["visible_dash_zero_cell_count"] for item in summary
    }

    for mutate in (
        lambda value: value["metrics"].__setitem__("mapped_record_count", 77),
        lambda value: value["input_identities"].__setitem__(
            "region_retrieval_receipt_id", "fffrrv2:receipt:" + "0" * 64
        ),
        lambda value: value["formal_result_ref"].__setitem__("size_bytes", 29617255),
        lambda value: value["authority"].__setitem__(
            "broad_or_mixed_geography_population_mapping_authority", True
        ),
    ):
        tampered = copy.deepcopy(seal)
        mutate(tampered)
        assert "e0175:seal:" + _seal_digest(tampered) != seal["seal_id"]


def test_loan_geography_seal_tracked_refs_match_disk() -> None:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    references = list(seal["implementation_refs"].values()) + [
        seal["input_refs"]["document_evidence_manifest"]
    ]
    for reference in references:
        path = ROOT / reference["path"]
        assert path.stat().st_size == reference["size_bytes"]
        assert _sha(path) == reference["sha256"]

    manifest = json.loads(
        (ROOT / seal["input_refs"]["document_evidence_manifest"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    assert manifest["manifest_id"] == seal["input_identities"][
        "document_evidence_store_manifest_id"
    ]
    assert manifest["database_ref"] == seal["input_refs"]["region_retrieval_database"]
    assert manifest["metrics"] == {
        "document_count": 140,
        "line_count": 667224,
        "page_count": 8947,
    }


def test_loan_geography_local_retrieval_database_matches_when_available() -> None:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    reference = seal["input_refs"]["region_retrieval_database"]
    path = ROOT / reference["path"]
    if not path.exists():
        return
    assert path.stat().st_size == reference["size_bytes"]
    assert _sha(path) == reference["sha256"]
    assert seal["authority"]["persisted_retrieval_receipt_is_bounded_roots_and_coverage_only"]
    assert seal["authority"]["region_retrieval_is_mapping_or_absence_authority"] is False


def test_formal_loan_geography_result_matches_and_validates_offline_when_available() -> None:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    reference = seal["formal_result_ref"]
    path = ROOT / reference["path"]
    if not path.exists():
        return

    payload = path.read_bytes()
    result = json.loads(payload.decode("utf-8"))
    canonical = (
        json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    assert payload == canonical
    assert payload.endswith(b"\n") and not payload.endswith(b"\n\n")
    assert path.stat().st_size == reference["size_bytes"]
    assert _sha(path) == reference["sha256"]
    assert stat.S_IMODE(path.stat().st_mode) == int(reference["mode"], 8)
    assert path.stat().st_nlink == 1
    assert set(result) == {
        "authority",
        "claim_boundary",
        "format_version",
        "inputs",
        "metrics",
        "state",
        "sweep_id",
        "trials",
    }
    assert result["state"] == "COMPLETE"
    assert result["sweep_id"] == seal["sweep_id"]
    assert result["metrics"] == seal["metrics"]

    inputs = result["inputs"]
    store = inputs["document_evidence_store"]
    receipt = inputs["region_retrieval_receipt"]
    assert inputs["tracked_git_head"] == seal["git_commit"]
    assert seal["input_identities"] == {
        "bounded_schema_projection_id": inputs["bounded_schema_projection"]["projection_id"],
        "document_evidence_store_manifest_id": store["manifest_id"],
        "numeric_axis_sha256": store["input_indices"]["numeric_axis_sha256"],
        "numeric_receipt_id": store["input_indices"]["numeric_receipt_id"],
        "semantic_index_id": store["input_indices"]["semantic_index_id"],
        "region_query_spec_id": receipt["query_spec_id"],
        "region_retrieval_receipt_id": receipt["receipt_id"],
        "region_retrieval_binding_id": receipt["binding_id"],
    }
    assert receipt["source_binding"]["database_ref"] == seal["input_refs"][
        "region_retrieval_database"
    ]
    assert inputs["implementation_refs"] == seal["implementation_refs"]
    assert {
        key: seal["authority"][key] for key in result["authority"]
    } == result["authority"]

    for reference in inputs["schema_source_refs"].values():
        schema_path = ROOT / reference["path"]
        assert schema_path.stat().st_size == reference["size_bytes"]
        assert _sha(schema_path) == reference["sha256"]

    trials = result["trials"]
    assert len(trials) == 140
    assert Counter(trial["status"] for trial in trials) == Counter(
        {"VERIFIED_BY_CODEX": 38, "VERIFIED_BOUNDED_ABSENCE": 102}
    )
    assert Counter(trial["disposition"] for trial in trials) == Counter(
        {
            "EXACT_CUSTOMER_LOAN_GEOGRAPHY": 38,
            "BROAD_POPULATION_BOUNDED_ABSENCE": 78,
            "NOT_OBSERVED": 24,
        }
    )
    mappings = [
        mapping
        for trial in trials
        if trial["disposition"] == "EXACT_CUSTOMER_LOAN_GEOGRAPHY"
        for mapping in trial["mapped_children"]
    ]
    assert Counter(mapping["report_norm_id"] for mapping in mappings) == Counter(
        {5752: 38, 765: 38}
    )
    assert all(
        trial["numeric_evidence"] is None
        and trial["pixel_dash_evidence"] is None
        and trial["customer_loan_total_control_request_set"] is None
        and trial["customer_loan_total_controls"] == []
        and trial["mapped_children"] == []
        for trial in trials
        if trial["disposition"] != "EXACT_CUSTOMER_LOAN_GEOGRAPHY"
    )

    # This validator recomputes every ID and denominator from the embedded trials only.
    # It deliberately does not open the SQLite store, PDFs, OCR corpus, or auth capability.
    from scripts.experiments import (  # noqa: PLC0415
        build_family_first_loan_geography_140_filing_schema_sweep_v1 as sweep_v1,
    )

    assert (
        sweep_v1.validate_authenticated_family_first_loan_geography_140_filing_schema_sweep_v1(
            result
        )
        == result
    )
