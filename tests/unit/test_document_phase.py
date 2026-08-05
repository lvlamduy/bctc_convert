from __future__ import annotations

from bctc_ai.core.contracts import PagePhase
from bctc_ai.document_phase.classifier import PageObservation, classify_page_sequence


def test_sequence_decoder_separates_policy_from_quantitative_notes():
    observations = [
        PageObservation(1, "Báo cáo tài chính hợp nhất năm 2025"),
        PageObservation(2, "MỤC LỤC Thông tin chung"),
        PageObservation(3, "BÁO CÁO TÌNH HÌNH TÀI CHÍNH Tại ngày 31 tháng 12 năm 2025", 0.3, 0.5),
        PageObservation(
            4, "THUYẾT MINH BÁO CÁO TÀI CHÍNH TÓM TẮT CÁC CHÍNH SÁCH KẾ TOÁN", 0.01, 0.0
        ),
        PageObservation(5, "THUYẾT MINH BÁO CÁO TÀI CHÍNH 12. CHO VAY KHÁCH HÀNG", 0.35, 0.7),
    ]
    phases = [decision.phase for decision in classify_page_sequence(observations)]
    assert phases == [
        PagePhase.COVER,
        PagePhase.NON_DATA,
        PagePhase.MAIN_STATEMENTS,
        PagePhase.ACCOUNTING_POLICIES,
        PagePhase.QUANTITATIVE_NOTES,
    ]
