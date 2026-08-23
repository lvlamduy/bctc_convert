from __future__ import annotations

import copy
import hashlib
import json
import stat
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEAL_PATH = ROOT / (
    "docs/experiments/E-0173-family-first-loan-currency-140-filing-schema-sweep-seal-v1.json"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _seal_digest(seal: dict[str, object]) -> str:
    material = dict(seal)
    material.pop("seal_id")
    canonical = json.dumps(
        material, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def test_loan_currency_seal_is_hash_bound_closed_and_tamper_sensitive() -> None:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    assert seal["seal_id"] == "e0173:seal:" + _seal_digest(seal)
    assert seal["state"] == "COMPLETE"
    assert seal["family_id"] == "LOAN_CURRENCY_CLASSIFICATION"
    assert seal["git_commit"] == "3199e34620e347cf7ff4c720d997f9e09e0b77e3"
    assert seal["sweep_id"] == (
        "lc140v1:sweep:bbcdfe8091911419de5e41637ee6a974511a9013655a76551a59b7ac864beb2d"
    )

    metrics = seal["metrics"]
    assert set(metrics) == {
        "absence_numeric_hydration_count",
        "additional_source_population_document_count",
        "additional_source_population_money_cell_count",
        "additional_source_population_row_count",
        "bank_bounded_absence_counts",
        "bank_document_counts",
        "bank_mapped_record_counts",
        "bank_presence_counts",
        "bounded_absence_trial_count",
        "bounded_paired_dash_zero_cell_count",
        "direct_visible_dash_zero_cell_count",
        "document_count",
        "full_axis_positive_document_count",
        "full_axis_positive_joined_line_count",
        "full_axis_positive_nonempty_page_count",
        "full_axis_positive_packet_page_count",
        "full_axis_positive_registered_zero_line_page_count",
        "mapped_money_cell_count",
        "mapped_parent_716_or_756_record_count",
        "mapped_record_count",
        "minimal_unique_two_anchor_region_count",
        "numeric_exact_trial_count",
        "observed_accounting_equation_count",
        "owner_mode_trial_counts",
        "period_mode_trial_counts",
        "pixel_overlay_document_count",
        "pixel_render_replay_count",
        "ppocrv6_vietocr_numeric_disagreement_count",
        "ppocrv6_vietocr_raw_surface_disagreement_count",
        "schema_report_norm_id_record_counts",
        "source_control_money_cell_count",
        "source_control_row_count",
        "structure_unique_trial_count",
        "typed_lane_axis_trial_counts",
        "unit_scope_trial_counts",
        "unresolved_trial_count",
        "verified_trial_count",
        "visible_dash_detector_hole_count",
        "visible_dash_rescue_cell_count_distribution",
        "visible_dash_zero_cell_count",
    }
    assert {
        key: metrics[key]
        for key in (
            "document_count",
            "verified_trial_count",
            "full_axis_positive_document_count",
            "bounded_absence_trial_count",
            "unresolved_trial_count",
            "mapped_record_count",
            "mapped_money_cell_count",
            "observed_accounting_equation_count",
            "visible_dash_zero_cell_count",
        )
    } == {
        "document_count": 140,
        "verified_trial_count": 140,
        "full_axis_positive_document_count": 10,
        "bounded_absence_trial_count": 130,
        "unresolved_trial_count": 0,
        "mapped_record_count": 20,
        "mapped_money_cell_count": 40,
        "observed_accounting_equation_count": 36,
        "visible_dash_zero_cell_count": 8,
    }
    assert metrics["schema_report_norm_id_record_counts"] == {"757": 10, "758": 10}
    assert metrics["bank_presence_counts"] == {
        "ACB": 6,
        "MBB": 0,
        "VPB": 0,
        "HDB": 4,
        "VCB": 0,
        "CTG": 0,
        "BID": 0,
        "VIB": 0,
    }
    assert metrics["bank_bounded_absence_counts"] == {
        "ACB": 12,
        "MBB": 18,
        "VPB": 18,
        "HDB": 12,
        "VCB": 18,
        "CTG": 18,
        "BID": 16,
        "VIB": 18,
    }
    assert sum(item["document_count"] for item in seal["bank_summary"]) == 140
    assert sum(item["verified_present_document_count"] for item in seal["bank_summary"]) == 10
    assert (
        sum(item["verified_bounded_absence_document_count"] for item in seal["bank_summary"]) == 130
    )
    assert sum(item["mapped_record_count"] for item in seal["bank_summary"]) == 20

    for field, value in (
        ("mapped_record_count", 21),
        ("bounded_paired_dash_zero_cell_count", 3),
    ):
        tampered = copy.deepcopy(seal)
        tampered["metrics"][field] = value
        assert "e0173:seal:" + _seal_digest(tampered) != seal["seal_id"]


def test_loan_currency_seal_implementation_refs_match_disk() -> None:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    for reference in seal["implementation_refs"].values():
        path = ROOT / reference["path"]
        assert path.stat().st_size == reference["size_bytes"]
        assert _sha(path) == reference["sha256"]


def test_formal_loan_currency_result_matches_seal_when_available() -> None:
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
    statuses = Counter(trial["status"] for trial in result["trials"])
    assert statuses == Counter({"VERIFIED_BOUNDED_ABSENCE": 130, "VERIFIED_BY_CODEX": 10})
    mappings = [
        mapping
        for trial in result["trials"]
        if trial["status"] == "VERIFIED_BY_CODEX"
        for mapping in trial["mapped_children"]
    ]
    assert Counter(mapping["report_norm_id"] for mapping in mappings) == Counter({757: 10, 758: 10})
    assert all(
        trial["source_hydration"] is None and trial["numeric_evidence"] is None
        for trial in result["trials"]
        if trial["status"] == "VERIFIED_BOUNDED_ABSENCE"
    )
    inputs = result["inputs"]
    identities = seal["input_identities"]
    store = inputs["document_evidence_store"]
    assert identities == {
        "bounded_schema_projection_id": inputs["bounded_schema_projection"]["projection_id"],
        "document_evidence_store_manifest_id": store["manifest_id"],
        "numeric_axis_sha256": store["input_indices"]["numeric_axis_sha256"],
        "numeric_receipt_id": store["input_indices"]["numeric_receipt_id"],
        "semantic_index_id": store["input_indices"]["semantic_index_id"],
        "evaluation_spec_sha256": inputs["evaluation_spec_sha256"],
        "hierarchy_spec_sha256": inputs["hierarchy_spec_sha256"],
        "topology_spec_sha256": inputs["topology_spec_sha256"],
    }
    assert sorted(seal["implementation_refs"].values(), key=lambda item: item["path"]) == sorted(
        inputs["implementation_refs"].values(), key=lambda item: item["path"]
    )
    assert result["authority"]["gemma_used"] is False
