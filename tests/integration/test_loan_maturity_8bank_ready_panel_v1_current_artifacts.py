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
    project_authenticated_loan_maturity_8bank_anonymous_batch_v1,
    project_authenticated_loan_maturity_8bank_ready_panel_audit_receipt_v1,
    read_authenticated_loan_maturity_8bank_anonymous_page_v1,
    validate_authenticated_loan_maturity_8bank_anonymous_batch_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
E0044 = Path("docs/experiments/E-0044-loan-maturity-8bank-vietocr-panel-prerequisite.json")
VPB_SOURCE_SHA256 = "614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde"
VCB_SOURCE_SHA256 = "fb0bc8ebbad76c175e61f7c2a7b78ae67608623a8d715d5470a08dbac00ff223"
EXPECTED_BATCH_ID = (
    "lm8brpv1:batch:90270f4f8edf4fc6bc4fcdaacaa55239c9835d420c3c80bf99016237481846f6"
)
EXPECTED_AUDIT_ID = (
    "lm8brpv1:audit:f6ecc9effc4b3452784964c3acf0701383d0d7facc9275a3559c83bf7dfbc2e1"
)
EXPECTED_VECTOR = [85, 109, 110, 101, 91, 88, 87, 164]
EXPECTED_DIMENSIONS = [
    (1654, 2339),
    (1654, 2339),
    (1700, 2200),
    (1653, 2328),
    (1643, 2344),
    (2482, 3510),
    (1656, 2339),
    (1654, 2339),
]
EXPECTED_RENDER_SIZES = [
    881_433,
    285_224,
    307_767,
    923_063,
    1_025_602,
    171_140,
    1_286_825,
    116_028,
]


def _all_keys(value: Any) -> set[str]:
    if type(value) is dict:
        return set(value).union(*(_all_keys(item) for item in value.values()), set())
    if type(value) is list:
        return set().union(*(_all_keys(item) for item in value), set())
    return set()


def test_current_artifacts_compose_exact_anonymous_eight_bank_ready_panel() -> None:
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

    audit, capability = compose_authenticated_loan_maturity_8bank_ready_panel_v1(
        PROJECT_ROOT,
        E0044,
        prerequisite,
        # Reversed deliberately: joining is by authenticated source state, not bank/order.
        (vcb, vpb),
    )
    batch = project_authenticated_loan_maturity_8bank_anonymous_batch_v1(capability)

    assert audit["audit_id"] == EXPECTED_AUDIT_ID
    assert batch["batch_id"] == EXPECTED_BATCH_ID
    assert batch["line_count_vector"] == EXPECTED_VECTOR
    assert batch["page_count"] == 8
    assert batch["sample_count"] == 835
    assert validate_authenticated_loan_maturity_8bank_anonymous_batch_v1(batch, capability) == batch
    assert (
        project_authenticated_loan_maturity_8bank_ready_panel_audit_receipt_v1(capability) == audit
    )

    pages = [
        read_authenticated_loan_maturity_8bank_anonymous_page_v1(capability, ordinal)
        for ordinal in range(1, 9)
    ]
    assert [(page["pixel_width"], page["pixel_height"]) for page in pages] == (EXPECTED_DIMENSIONS)
    assert [len(page["render_png_bytes"]) for page in pages] == EXPECTED_RENDER_SIZES
    assert [page["line_count"] for page in pages] == EXPECTED_VECTOR
    assert sum(len(page["line_bboxes"]) for page in pages) == 835
    for ordinal, page in enumerate(pages, start=1):
        assert page["page_id"] == f"page-{ordinal:04d}"
        assert page["page_ordinal"] == ordinal
        assert page["render_png_bytes"].startswith(b"\x89PNG\r\n\x1a\n")
        width, height = page["pixel_width"], page["pixel_height"]
        for bbox in page["line_bboxes"]:
            x0, y0, x1, y1 = bbox
            assert 0 <= x0 < x1 <= width
            assert 0 <= y0 < y1 <= height

    assert (
        audit["slots"][2]["render_sha256"]
        == hashlib.sha256(pages[2]["render_png_bytes"]).hexdigest()
    )
    assert (
        audit["slots"][4]["render_sha256"]
        == hashlib.sha256(pages[4]["render_png_bytes"]).hexdigest()
    )
    forbidden = {
        "adapter",
        "bank_code",
        "physical_page",
        "raw_text",
        "receipt",
        "result_ref",
        "source_pdf_sha256",
        "text",
        "word",
    }
    assert not (_all_keys(batch) & forbidden)
