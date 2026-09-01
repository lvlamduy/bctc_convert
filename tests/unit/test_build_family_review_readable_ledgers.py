from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/review/build_family_review_readable_ledgers.py"
SPEC = importlib.util.spec_from_file_location("build_family_review_readable_ledgers", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)


def _document(source: str, *, status: str, filename: str) -> dict:
    return {
        "assurance_label": "Kiểm toán",
        "bank": "ACB",
        "filename": filename,
        "period_label": "Năm 2025",
        "scope_label": "Hợp nhất",
        "source_sha256": source,
        "status": status,
    }


class _Repository:
    def families(self) -> list[dict]:
        return [
            {
                "id": "TRADING_SECURITIES",
                "name": "Chứng khoán kinh doanh",
                "order": 4,
                "document_count": 2,
                "ready_count": 1,
                "not_observed_count": 0,
                "unresolved_count": 1,
                "mapping_count": 3,
            }
        ]

    def documents(self, family_id: str, _filters: dict) -> list[dict]:
        assert family_id == "TRADING_SECURITIES"
        return [
            _document("a" * 64, status="READY", filename="BCTC năm 2025.pdf"),
            _document("b" * 64, status="UNRESOLVED", filename="BCTC lỗi năm 2025.pdf"),
        ]

    def review(self, _family_id: str, source_sha256: str) -> dict:
        if source_sha256 == "a" * 64:
            source_only = {
                "candidate_reason_labels": [],
                "classification": "NGHI THUỘC FAMILY KHÁC",
                "explanation": "Dòng này có thể thuộc chứng khoán đầu tư.",
                "hierarchy": ["Chứng khoán", "Khoản khác"],
                "physical_page": 40,
                "row_id": "r7",
                "section_id": "s1",
                "source_label": "Khoản khác",
                "table_id": "t1",
                "values": ["100", "90"],
            }
            return {
                "coverage": {
                    "not_seen": [{"report_norm_id": 618}],
                    "source_only": [source_only, dict(source_only)],
                    "unresolved_tables": [],
                    "visible_unmapped": [
                        {
                            "candidate_reason_labels": ["Ô số không đọc được"],
                            "classification": "CÓ TRÊN PDF NHƯNG CHƯA MAP",
                            "explanation": "Ô số không đọc được thành số nguyên chính xác.",
                            "hierarchy": ["Chứng khoán nợ", "Đã niêm yết"],
                            "physical_page": 40,
                            "report_norm_id": 618,
                            "row_id": "r3",
                            "schema_name": "+ Đã niêm yết",
                            "section_id": "s1",
                            "source_label": "Đã niêm yết",
                            "table_id": "t1",
                            "values": ["1.2.3", "90"],
                        }
                    ],
                }
            }
        return {
            "coverage": {
                "not_seen": [],
                "source_only": [],
                "unresolved_tables": [
                    {
                        "physical_page": 41,
                        "reason_labels": ["Không xác định được cột/kỳ"],
                        "section_id": "s1",
                        "table_id": "t2",
                        "table_title": "Phân loại chứng khoán",
                    }
                ],
                "visible_unmapped": [],
            },
            "disposition": {"reason_labels": ["Không xác định được cột/kỳ"]},
        }


def test_ledgers_distinguish_unresolved_visible_unmapped_and_source_only() -> None:
    completed, ledger, metrics = builder.build_ledgers(
        _Repository(),
        notes_by_order={4: "Nợ/vốn × niêm yết/chưa niêm yết."},
        expected_family_count=1,
        expected_document_count=2,
    )

    assert metrics == {
        "family_count": 1,
        "family_document_observation_count": 2,
        "ready_count": 1,
        "not_observed_count": 0,
        "unresolved_count": 1,
        "ledger_record_count": 3,
    }
    assert "| 4 | Chứng khoán kinh doanh | 2 | 1 | 0 | 1 | 1 dòng/1 PDF | 1 dòng/1 PDF" in completed
    assert "Nợ/vốn × niêm yết/chưa niêm yết" in completed
    assert "## UNRESOLVED — 1 record" in ledger
    assert "## CÓ TRÊN PDF NHƯNG CHƯA MAP — 1 record" in ledger
    assert "## SOURCE_ONLY — 1 record" in ledger
    assert "**LỖI SOURCE/OCR**" in ledger
    assert "**NGHI LÀ THUỘC FAMILY KHÁC**" in ledger
    assert "ReportNormId gần nhất:** 618 — + Đã niêm yết" in ledger
    assert "source_sha256=" in ledger
    assert "Phân loại nguyên nhân:** **CHƯA CÓ TRONG SCHEMA**" not in ledger


def test_ledgers_reject_family_metrics_that_do_not_match_documents() -> None:
    repository = _Repository()
    repository.families = lambda: [repository.__class__().families()[0] | {"ready_count": 2}]

    with pytest.raises(builder.BuildFamilyReviewReadableLedgersError, match="metrics"):
        builder.build_ledgers(
            repository,
            notes_by_order={},
            expected_family_count=1,
            expected_document_count=2,
        )
