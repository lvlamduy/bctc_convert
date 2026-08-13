#!/usr/bin/env python3
"""Run the fixed reference-blind 835-line VietOCR V3 experiment once."""

from __future__ import annotations

from pathlib import Path

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
    ARTIFACT_ROOT,
    replay_authenticated_vietocr_all_line_freeze_v3,
)
from bctc_ai.ocr.vietocr_all_line_runner_v3 import (
    run_authenticated_vietocr_all_line_v3,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
E0044 = Path("docs/experiments/E-0044-loan-maturity-8bank-vietocr-panel-prerequisite.json")
VPB_SOURCE_SHA256 = "614be8877c21ef189da90266c5b059eb0b7d47024444156241725820bb11dcde"
VCB_SOURCE_SHA256 = "fb0bc8ebbad76c175e61f7c2a7b78ae67608623a8d715d5470a08dbac00ff223"


def main() -> None:
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
    _audit, ready = compose_authenticated_loan_maturity_8bank_ready_panel_v1(
        PROJECT_ROOT,
        E0044,
        prerequisite,
        (vcb, vpb),
    )
    _projection, freeze = replay_authenticated_vietocr_all_line_freeze_v3(
        PROJECT_ROOT,
        ARTIFACT_ROOT,
        ready,
    )
    run = run_authenticated_vietocr_all_line_v3(PROJECT_ROOT, freeze)
    print(run["run_id"])


if __name__ == "__main__":
    main()
