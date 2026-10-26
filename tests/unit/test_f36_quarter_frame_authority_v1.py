"""F36 quarter-frame role needs one explicit printed report frame (Codex review 0393 / 0396)."""
import pytest

from bctc_ai.evaluation.gemini_json_f36_notes_core_adapter_v1 import (
    _quarter_frame_lane_v1,
)
from bctc_ai.primary_statements.periods_v1 import (
    duration_lane_period_v1,
    statement_period_context_v1,
)

FRAME_2025 = "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG RIÊNG\nQuý I năm 2025"
FRAME_2024 = "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG RIÊNG\nQuý I năm 2024"
FISCAL_END = "Năm tài chính kết thúc ngày 31/12/2025"


@pytest.mark.parametrize(
    "frames",
    [
        [FRAME_2025, FRAME_2024, FISCAL_END],
        ["Quý I", FISCAL_END],
    ],
    ids=["conflicting-quarter-years", "quarter-without-printed-year"],
)
def test_quarter_role_requires_one_explicit_report_frame(frames):
    context = statement_period_context_v1(frames)
    for year in (2025, 2024):
        header = f"Kỳ ba tháng kết thúc ngày 31/03/{year}"
        descriptor = duration_lane_period_v1(header, context)
        assert descriptor.role is None
        assert descriptor.resolution == "EXPLICIT"
        assert descriptor.key == f"DURATION:MONTHS_ENDED:3:{year}-03-31"
        bound = _quarter_frame_lane_v1(descriptor, context)
        assert bound.role is None
        assert bound.resolution == "EXPLICIT"
        assert bound.key == descriptor.key


@pytest.mark.parametrize(
    "frames",
    [[FRAME_2025, FISCAL_END], [FRAME_2025, FRAME_2025, FISCAL_END]],
    ids=["unique-frame", "duplicate-identical-frame"],
)
def test_unique_frame_preserves_both_printed_comparative_windows(frames):
    context = statement_period_context_v1(frames)
    for year, role in ((2025, "CURRENT"), (2024, "COMPARATIVE")):
        header = f"Kỳ ba tháng kết thúc ngày 31/03/{year}"
        descriptor = duration_lane_period_v1(header, context)
        assert descriptor.role is None
        assert descriptor.resolution == "EXPLICIT"
        bound = _quarter_frame_lane_v1(descriptor, context)
        assert bound.role == role
        assert bound.resolution == "QUARTER_FRAME_BOUND"
        assert bound.key == descriptor.key
        assert dict(bound.fields)["quarter_frame"] == "Q1:2025"
        assert dict(bound.fields)["window_shape"] == "MONTHS_ENDED:3:03-31"
