from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.authenticated_line_pixel_hydration_v1 import (
    replay_authenticated_line_pixel_hydration_v1,
)
from bctc_ai.evaluation.loan_maturity_8bank_panel_prerequisite_v1 import (
    replay_loan_maturity_8bank_panel_prerequisite_v1,
)
from bctc_ai.evaluation.loan_maturity_8bank_ready_panel_v1 import (
    compose_authenticated_loan_maturity_8bank_ready_panel_v1,
)
from bctc_ai.evaluation.vietocr_all_line_freezer_v3 import (
    read_authenticated_vietocr_all_line_batch_v3,
    replay_authenticated_vietocr_all_line_freeze_v3,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
E0044 = Path("docs/experiments/E-0044-loan-maturity-8bank-vietocr-panel-prerequisite.json")
FREEZE_ROOT = Path("output/development/vietocr-all-line-freeze-v3")
VPB_SOURCE_SHA256 = "614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde"
VCB_SOURCE_SHA256 = "fb0bc8ebbad76c175e61f7c2a7b78ae67608623a8d715d5470a08dbac00ff223"
EXPECTED_FREEZE_ID = (
    "voalfv3:freeze:b36afc9068440653a89a64be1e70638abccd18bf4847137ce377aff5e1f573a8"
)
EXPECTED_MANIFEST_SHA256 = "cb105061d7e66a5ed6c6806a375df9904fe18fa3f7f17a16d7e5e2e6a86d5796"
EXPECTED_MANIFEST_SIZE = 322_141
EXPECTED_REQUEST_SHA256 = "381338e19ae33973be6b1f211f5835506ee2c0a464454d517694bebb236d34c1"
EXPECTED_REQUEST_SIZE = 232_953
EXPECTED_VECTOR = [85, 109, 110, 101, 91, 88, 87, 164]
EXPECTED_FIRST_CROP_SHA256 = "bc879e9708351e7e8a9a1e30e721aeea527c5f85d53d07f5672ed48dbfce0aa4"
EXPECTED_MIDDLE_CROP_SHA256 = "e697674ef2655cc6e97636096bcca62a9e1cf714f2f5f8b25d2219b5c3b22bb9"
EXPECTED_LAST_CROP_SHA256 = "dba71edb16afe7e4b7f1557a35e2ac350d395ecfe3bc0f627f05f1fb037608e5"


def _all_keys(value: Any) -> set[str]:
    if type(value) is dict:
        return set(value).union(*(_all_keys(item) for item in value.values()), set())
    if type(value) in {list, tuple}:
        return set().union(*(_all_keys(item) for item in value), set())
    return set()


def test_current_artifact_replays_exact_authenticated_835_crop_freeze() -> None:
    _panel, prerequisite = replay_loan_maturity_8bank_panel_prerequisite_v1(PROJECT_ROOT, E0044)
    _vpb_envelope, vpb = replay_authenticated_line_pixel_hydration_v1(
        PROJECT_ROOT,
        source_pdf_sha256=VPB_SOURCE_SHA256,
        physical_page=42,
    )
    _vcb_envelope, vcb = replay_authenticated_line_pixel_hydration_v1(
        PROJECT_ROOT,
        source_pdf_sha256=VCB_SOURCE_SHA256,
        physical_page=31,
    )
    _audit, ready_capability = compose_authenticated_loan_maturity_8bank_ready_panel_v1(
        PROJECT_ROOT,
        E0044,
        prerequisite,
        # Reversed deliberately: hydration is joined by source locator/state.
        (vcb, vpb),
    )

    projection, freeze_capability = replay_authenticated_vietocr_all_line_freeze_v3(
        PROJECT_ROOT,
        FREEZE_ROOT,
        ready_capability,
    )

    assert projection["freeze_id"] == EXPECTED_FREEZE_ID
    assert projection["line_count_vector"] == EXPECTED_VECTOR
    assert projection["page_count"] == 8
    assert projection["sample_count"] == 835
    assert projection["state"] == "FROZEN_READY_NO_MODEL_RUN"
    assert projection["crop_manifest_ref"] == {
        "path": f"{FREEZE_ROOT.as_posix()}/frozen/crop_manifest.json",
        "sha256": EXPECTED_MANIFEST_SHA256,
        "size_bytes": EXPECTED_MANIFEST_SIZE,
    }
    assert projection["reader_request_ref"] == {
        "path": f"{FREEZE_ROOT.as_posix()}/frozen/reader_request.json",
        "sha256": EXPECTED_REQUEST_SHA256,
        "size_bytes": EXPECTED_REQUEST_SIZE,
    }
    for name, expected_sha256, expected_size in (
        ("crop_manifest.json", EXPECTED_MANIFEST_SHA256, EXPECTED_MANIFEST_SIZE),
        ("reader_request.json", EXPECTED_REQUEST_SHA256, EXPECTED_REQUEST_SIZE),
    ):
        payload = (PROJECT_ROOT / FREEZE_ROOT / "frozen" / name).read_bytes()
        assert len(payload) == expected_size
        assert hashlib.sha256(payload).hexdigest() == expected_sha256

    batch = read_authenticated_vietocr_all_line_batch_v3(freeze_capability)
    assert type(batch) is tuple
    assert len(batch) == 835
    assert all(
        type(sample) is dict
        and set(sample) == {"crop_png_bytes", "crop_sha256", "page_id", "sample_id"}
        and type(sample["crop_png_bytes"]) is bytes
        and hashlib.sha256(sample["crop_png_bytes"]).hexdigest() == sample["crop_sha256"]
        for sample in batch
    )
    assert batch[0]["sample_id"] == "page-0001-line-0000"
    assert batch[0]["crop_sha256"] == EXPECTED_FIRST_CROP_SHA256
    assert batch[417]["sample_id"] == "page-0005-line-0012"
    assert batch[417]["crop_sha256"] == EXPECTED_MIDDLE_CROP_SHA256
    assert batch[-1]["sample_id"] == "page-0008-line-0163"
    assert batch[-1]["crop_sha256"] == EXPECTED_LAST_CROP_SHA256
    assert [
        sum(sample["page_id"] == f"page-{ordinal:04d}" for sample in batch)
        for ordinal in range(1, 9)
    ] == EXPECTED_VECTOR

    forbidden = {
        "adapter",
        "bank",
        "bank_code",
        "family",
        "filename",
        "physical_page",
        "raw_text",
        "receipt",
        "result_ref",
        "source_pdf_sha256",
        "transcript",
    }
    assert not (_all_keys(batch) & forbidden)
