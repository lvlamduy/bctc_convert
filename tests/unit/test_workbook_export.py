from __future__ import annotations

from bctc_ai.core.contracts import EvidenceStatus, PipelineRecord
from bctc_ai.export.workbook import export_workbook, verify_export
from bctc_ai.schema.registry import load_all


def test_workbook_preserves_schema_order_and_support_sheets(tmp_path, project_root):
    output = tmp_path / "result.xlsx"
    records = [
        PipelineRecord(
            document_id="sha256:sample",
            statement_type="CDKT",
            schema_id=4302,
            canonical_name="TÀI SẢN",
            raw_value="1.234",
            normalized_value="1234",
            current_or_comparative="CURRENT",
            status=EvidenceStatus.AUTO_VERIFIED_MEDIUM,
            unit="VND",
            period_end="2026-06-30",
        ),
        PipelineRecord(
            document_id="sha256:sample",
            statement_type="CDKT",
            schema_id=4310,
            canonical_name="Tiền mặt, vàng bạc, đá quý",
            raw_value="khó đọc",
            normalized_value=None,
            current_or_comparative="CURRENT",
            status=EvidenceStatus.REVIEW_REQUIRED,
            rejection_reason="independent OCR disagreement",
        ),
    ]
    result = export_workbook(
        project_root,
        output,
        records,
        run_metadata={"run_id": "test", "source_sha256": "sample"},
        questions_path=project_root / "questions_for_user.jsonl",
        schema_additions_path=project_root / "proposed_schema_additions.jsonl",
    )
    workbooks, _ = load_all(project_root / "template", project_root)
    verify_export(output, workbooks)
    assert result.exported_value_count == 1
    assert result.review_count == 1
    assert result.schema_counts == {"CDKT": 77, "KQKD": 24, "LCTT": 107, "TM": 1384}
