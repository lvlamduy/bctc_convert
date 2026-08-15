from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/scan_leased_fixed_assets_full_document_vietocr_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "scan_leased_fixed_assets_full_document_vietocr_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
scanner = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scanner
_SPEC.loader.exec_module(scanner)


@pytest.fixture(scope="module")
def live_scan() -> dict[str, object]:
    return scanner.build_live_leased_fixed_assets_full_document_scan_v1()


def test_live_complete_pdf_scan_finds_no_leased_asset_rollforward(
    live_scan: dict[str, object],
) -> None:
    assert live_scan["metrics"] == {
        "complete_region_count": 0,
        "document_count": 8,
        "document_unique_structural_match_count": 0,
        "mapping_verified_count": 0,
        "near_region_count": 0,
        "negative_control_line_count": 24,
        "unresolved_document_count": 8,
    }
    assert [trial["document_provenance"] for trial in live_scan["trials"]] == [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert all(
        trial["matcher_result"]["metrics"]
        == {"complete_region_count": 0, "near_region_count": 0, "owner_candidate_count": 0}
        for trial in live_scan["trials"]
    )


def test_policy_service_and_customer_loan_hits_remain_negative_controls(
    live_scan: dict[str, object],
) -> None:
    controls = [control for trial in live_scan["trials"] for control in trial["negative_controls"]]
    assert any(control["semantic_text"] == "Cho thuê tài chính" for control in controls)
    assert any("khoản thuê" in control["semantic_text"].lower() for control in controls)
    assert all(
        "tai san co dinh thue tai chinh" not in control["normalized_text"] for control in controls
    )


def test_live_replay_rejects_coordinated_absence_rehash(live_scan: dict[str, object]) -> None:
    forged = copy.deepcopy(live_scan)
    forged["metrics"]["negative_control_line_count"] = 0
    material = copy.deepcopy(forged)
    material.pop("scan_id")
    forged["scan_id"] = "lfafdsv1:scan:" + scanner.canonical_json_sha256_v1(material)

    with pytest.raises(
        scanner.LeasedFixedAssetsFullDocumentScanV1Error,
        match="metrics drifted|replay exactly",
    ):
        scanner.validate_live_leased_fixed_assets_full_document_scan_v1(forged)
