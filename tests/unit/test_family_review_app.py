from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import fitz
import pytest

from bctc_ai.review_app import create_app
from bctc_ai.review_app.repository import ReviewSettings

SOURCE_SHA = "a" * 64
PAGE_VERSION = "page-json-version-1"
SOURCE_NAME = "vietstock_bctc/ACB/2025/BCTC Hợp nhất quý 2 năm 2025 Soát xét.pdf"


def _results_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE family_current_selection (
            family_id TEXT PRIMARY KEY,
            family_run_id TEXT NOT NULL
        );
        CREATE TABLE family_run (
            family_run_id TEXT PRIMARY KEY,
            document_count INTEGER NOT NULL,
            ready_count INTEGER NOT NULL,
            not_observed_count INTEGER NOT NULL,
            unresolved_count INTEGER NOT NULL,
            mapping_count INTEGER NOT NULL
        );
        CREATE TABLE family_trial (
            family_run_id TEXT NOT NULL,
            document_ordinal INTEGER NOT NULL,
            source_logical_name TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,
            status TEXT NOT NULL,
            candidate_count INTEGER NOT NULL,
            selected_candidate_id TEXT,
            mapping_count INTEGER NOT NULL,
            reasons_json BLOB NOT NULL,
            trial_bytes BLOB NOT NULL
        );
        CREATE TABLE family_candidate (
            family_run_id TEXT NOT NULL,
            document_ordinal INTEGER NOT NULL,
            candidate_id TEXT NOT NULL,
            page_json_version_id TEXT NOT NULL,
            physical_page INTEGER NOT NULL,
            section_id TEXT NOT NULL,
            table_id TEXT NOT NULL,
            status TEXT NOT NULL,
            reason_count INTEGER NOT NULL,
            mapping_count INTEGER NOT NULL,
            candidate_bytes BLOB NOT NULL
        );
        CREATE TABLE family_mapping (
            family_run_id TEXT NOT NULL,
            document_ordinal INTEGER NOT NULL,
            mapping_ordinal INTEGER NOT NULL,
            report_norm_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            row_id TEXT NOT NULL,
            mapping_bytes BLOB NOT NULL
        );
        """
    )
    candidate = {
        "candidate_id": "candidate-1",
        "page_json_version_id": PAGE_VERSION,
        "physical_page": 2,
        "section_id": "s1",
        "table_id": "t1",
        "status": "READY",
        "reasons": [],
    }
    mapping = {
        "report_norm_id": 747,
        "role": "STANDARD",
        "row_id": "derived:STANDARD",
        "label_exact": "STANDARD",
        "hierarchy_path_exact": [],
        "derived_from_row_ids": ["r1"],
        "derived_from_roles": ["STANDARD_CORE"],
        "columns": [
            {"header_path_exact": ["30/06/2025", "Triệu VND"], "value_kind": "MONEY"},
            {"header_path_exact": ["31/12/2024", "Triệu VND"], "value_kind": "MONEY"},
        ],
        "values": [
            {
                "coefficient": 2_474_846,
                "source_text": None,
                "state": "DERIVED_EXACT_RECURSIVE_DIRECT_FRONTIER",
            },
            {
                "coefficient": 2_100_000,
                "source_text": None,
                "state": "DERIVED_EXACT_RECURSIVE_DIRECT_FRONTIER",
            },
        ],
    }
    connection.execute(
        "INSERT INTO family_current_selection VALUES (?, ?)",
        ("LOAN_QUALITY_CLASSIFICATION", "run-1"),
    )
    connection.execute("INSERT INTO family_run VALUES (?, ?, ?, ?, ?, ?)", ("run-1", 1, 1, 0, 0, 1))
    connection.execute(
        "INSERT INTO family_trial VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("run-1", 1, SOURCE_NAME, SOURCE_SHA, "READY", 1, "candidate-1", 1, b"[]", b"{}"),
    )
    connection.execute(
        "INSERT INTO family_candidate VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "run-1",
            1,
            "candidate-1",
            PAGE_VERSION,
            2,
            "s1",
            "t1",
            "READY",
            0,
            1,
            json.dumps(candidate, ensure_ascii=False).encode(),
        ),
    )
    connection.execute(
        "INSERT INTO family_mapping VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "run-1",
            1,
            1,
            747,
            "STANDARD",
            "derived:STANDARD",
            json.dumps(mapping, ensure_ascii=False).encode(),
        ),
    )
    connection.commit()
    connection.close()


def _page_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE document (
            document_id TEXT PRIMARY KEY,
            source_sha256 TEXT NOT NULL,
            source_logical_name TEXT NOT NULL
        );
        CREATE TABLE page (
            page_id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            physical_page INTEGER NOT NULL,
            pixel_width INTEGER NOT NULL,
            pixel_height INTEGER NOT NULL
        );
        CREATE TABLE page_json_version (
            page_json_version_id TEXT PRIMARY KEY,
            page_id TEXT NOT NULL,
            page_status TEXT NOT NULL,
            canonical_json_bytes BLOB NOT NULL
        );
        """
    )
    canonical = {
        "status": "FINANCIAL_NOTE_CONTENT",
        "sections": [
            {
                "title_exact": "Thuyết minh báo cáo tài chính hợp nhất",
                "tables": [
                    {
                        "title_exact": "Phân tích chất lượng nợ cho vay",
                        "unit_exact": "Triệu VND",
                        "continuation": "NONE",
                        "columns": [
                            {
                                "header_path_exact": ["30/06/2025", "Triệu VND"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": ["31/12/2024", "Triệu VND"],
                                "value_kind": "MONEY",
                            },
                        ],
                        "rows": [
                            {
                                "label_exact": "Nhóm 1 - Nợ đủ tiêu chuẩn",
                                "hierarchy_path_exact": [
                                    "Phân tích chất lượng nợ",
                                    "Nhóm 1 - Nợ đủ tiêu chuẩn",
                                ],
                                "row_kind": "ITEM",
                                "values_exact": ["2.474.846", "2.100.000"],
                            }
                        ],
                    }
                ],
            }
        ],
    }
    connection.execute(
        "INSERT INTO document VALUES (?, ?, ?)", ("document-1", SOURCE_SHA, SOURCE_NAME)
    )
    connection.execute(
        "INSERT INTO page VALUES (?, ?, ?, ?, ?)", ("page-1", "document-1", 2, 595, 842)
    )
    connection.execute(
        "INSERT INTO page_json_version VALUES (?, ?, ?, ?)",
        (
            PAGE_VERSION,
            "page-1",
            "FINANCIAL_NOTE_CONTENT",
            json.dumps(canonical, ensure_ascii=False).encode(),
        ),
    )
    connection.commit()
    connection.close()


def _pdf(root: Path) -> None:
    path = root / "ACB/2025/BCTC Hợp nhất quý 2 năm 2025 Soát xét.pdf"
    path.parent.mkdir(parents=True)
    document = fitz.open()
    document.new_page().insert_text((72, 72), "Trang 1")
    document.new_page().insert_text((72, 72), "Phan tich chat luong no cho vay")
    document.save(path)
    document.close()


@pytest.fixture
def client(tmp_path: Path):
    results = tmp_path / "results.sqlite3"
    pages = tmp_path / "pages.sqlite3"
    pdf_root = tmp_path / "vietstock_bctc"
    schema = tmp_path / "schema.jsonl"
    _results_database(results)
    _page_database(pages)
    _pdf(pdf_root)
    schema.write_text(
        "\n".join(
            json.dumps(record, ensure_ascii=False)
            for record in (
                {
                    "schema_id": 747,
                    "canonical_name": "Nhóm 1: Nợ đủ tiêu chuẩn",
                    "parent_id": 746,
                },
                {
                    "schema_id": 616,
                    "canonical_name": "Chứng khoán kinh doanh (Phân loại theo đã NY và chưa NY)",
                    "parent_id": 592,
                },
                {"schema_id": 618, "canonical_name": "+ Đã niêm yết", "parent_id": 616},
                {"schema_id": 619, "canonical_name": "+ Chưa niêm yết", "parent_id": 616},
                {"schema_id": 621, "canonical_name": "+ Đã niêm yết", "parent_id": 616},
                {"schema_id": 622, "canonical_name": "+ Chưa niêm yết", "parent_id": 616},
            )
        )
        + "\n",
        encoding="utf-8",
    )
    app = create_app(
        ReviewSettings(
            results_database=results,
            page_database=pages,
            pdf_root=pdf_root,
            schema_path=schema,
            cache_directory=tmp_path / "cache",
        )
    )
    app.config.update(TESTING=True)
    return app.test_client()


def test_options_and_document_filters_are_human_readable(client) -> None:
    options = client.get("/api/options")
    assert options.status_code == 200
    payload = options.get_json()
    assert payload["default_family"] == "LOAN_QUALITY_CLASSIFICATION"
    assert payload["families"][0]["name"] == "Phân tích chất lượng cho vay"
    assert payload["families"][0]["order"] == 8
    assert payload["configuration"]["pdf_root"] is True

    response = client.get(
        "/api/documents?family_id=LOAN_QUALITY_CLASSIFICATION&bank=ACB&period=Q2&scope=CONSOLIDATED"
    )
    document = response.get_json()["documents"][0]
    assert document["filename"].endswith("Soát xét.pdf")
    assert document["period_label"] == "Quý 2 2025"
    assert document["status_label"] == "Đã map"


def test_review_aligns_gemini_row_with_schema_mapping(client) -> None:
    response = client.get(f"/api/review/LOAN_QUALITY_CLASSIFICATION/{SOURCE_SHA}")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["gemini_tables"][0]["rows"][0]["label"] == "Nhóm 1 - Nợ đủ tiêu chuẩn"
    assert payload["gemini_tables"][0]["columns"][0]["label"] == "30/06/2025\nTriệu VND"
    assert payload["mappings"][0]["report_norm_id"] == 747
    assert payload["mappings"][0]["schema_name"] == "Nhóm 1: Nợ đủ tiêu chuẩn"
    assert payload["mappings"][0]["values"][0]["coefficient"] == 2_474_846
    assert payload["mappings"][0]["values"][0]["header"] == "30/06/2025\nTriệu VND"
    assert payload["mappings"][0]["values"][0]["physical_page"] == 2
    assert payload["mappings"][0]["values"][0]["section_id"] == "s1"
    assert payload["mappings"][0]["values"][0]["table_id"] == "t1"
    assert payload["mappings"][0]["is_derived"] is True
    assert payload["mappings"][0]["derived_from_row_ids"] == ["r1"]
    assert "tính chính xác" in payload["mappings"][0]["values"][0]["state_label"]
    assert payload["mappings"][0]["values"][0]["display_source_text"] == "2.474.846"
    assert payload["mappings"][0]["derived_source_rows"][0]["label"] == (
        "Nhóm 1 - Nợ đủ tiêu chuẩn"
    )
    assert payload["gemini_tables"][0]["rows"][0]["mapping_state"] == "MAPPED"
    assert payload["coverage"]["summary"]["visible_unmapped_items"] == 0
    assert payload["pages"][0]["physical_page"] == 2


def test_page_image_is_rendered_from_configured_pdf(client) -> None:
    response = client.get(f"/api/page-image/{SOURCE_SHA}/2")
    assert response.status_code == 200
    assert response.content_type == "image/png"
    assert response.data.startswith(b"\x89PNG")


def test_unknown_document_fails_without_exposing_files(client) -> None:
    response = client.get(f"/api/review/LOAN_QUALITY_CLASSIFICATION/{'b' * 64}")
    assert response.status_code == 404
    assert "Không tìm thấy PDF" in response.get_json()["error"]


def test_schema_coverage_exposes_listing_status_branch_instead_of_source_only(client) -> None:
    repository = client.application.extensions["bctc_review_repository"]
    pages = [{"physical_page": 48, "canonical": {"sections": []}}]
    gemini_tables = [
        {
            "physical_page": 48,
            "section_id": "s1",
            "table_id": "t2",
            "table_title": "7.3 Tình trạng niêm yết",
            "section_title": "Thuyết minh báo cáo tài chính hợp nhất",
            "candidate_status": "UNRESOLVED",
            "candidate_status_label": "Cần kiểm tra",
            "candidate_reason_labels": ["Không thấy nhãn family cha ngay trong bảng/section"],
            "rows": [
                {
                    "id": "r1",
                    "label": "Chứng khoán nợ",
                    "hierarchy": ["Chứng khoán nợ"],
                    "values": [None, None],
                },
                {
                    "id": "r2",
                    "label": "Đã niêm yết",
                    "hierarchy": ["Chứng khoán nợ", "Đã niêm yết"],
                    "values": ["1.274.577", "841.743"],
                },
                {
                    "id": "r3",
                    "label": "Chưa niêm yết",
                    "hierarchy": ["Chứng khoán nợ", "Chưa niêm yết"],
                    "values": ["1.270.000", None],
                },
                {
                    "id": "r4",
                    "label": "Chứng khoán vốn",
                    "hierarchy": ["Chứng khoán vốn"],
                    "values": [None, None],
                },
                {
                    "id": "r5",
                    "label": "Đã niêm yết",
                    "hierarchy": ["Chứng khoán vốn", "Đã niêm yết"],
                    "values": ["4.137.322", "3.130.761"],
                },
                {
                    "id": "r6",
                    "label": "Chưa niêm yết",
                    "hierarchy": ["Chứng khoán vốn", "Chưa niêm yết"],
                    "values": ["26.459", "56.584"],
                },
            ],
        }
    ]
    specs = {
        "schema_binding": {
            "family_report_norm_id": 592,
            "role_bindings": [
                {"role": "DEBT_LISTED", "report_norm_id": 618},
                {"role": "DEBT_UNLISTED", "report_norm_id": 619},
                {"role": "EQUITY_LISTED", "report_norm_id": 621},
                {"role": "EQUITY_UNLISTED", "report_norm_id": 622},
            ],
        },
        "topology": {
            "children": [
                {
                    "role": "DEBT_GROUP",
                    "role_kind": "STRUCTURAL_GROUP",
                    "matchers": [{"aliases": ["Chứng khoán nợ"], "within_role": None}],
                },
                {
                    "role": "EQUITY_GROUP",
                    "role_kind": "STRUCTURAL_GROUP",
                    "matchers": [{"aliases": ["Chứng khoán vốn"], "within_role": None}],
                },
                {
                    "role": "DEBT_LISTED",
                    "matchers": [{"aliases": ["Đã niêm yết"], "within_role": "DEBT_GROUP"}],
                },
                {
                    "role": "DEBT_UNLISTED",
                    "matchers": [{"aliases": ["Chưa niêm yết"], "within_role": "DEBT_GROUP"}],
                },
                {
                    "role": "EQUITY_LISTED",
                    "matchers": [{"aliases": ["Đã niêm yết"], "within_role": "EQUITY_GROUP"}],
                },
                {
                    "role": "EQUITY_UNLISTED",
                    "matchers": [{"aliases": ["Chưa niêm yết"], "within_role": "EQUITY_GROUP"}],
                },
            ]
        },
    }

    coverage = repository._schema_coverage(pages, gemini_tables, [], specs)

    assert [item["report_norm_id"] for item in coverage["visible_unmapped"]] == [
        618,
        619,
        621,
        622,
    ]
    assert coverage["structural_context"] == [
        {
            "report_norm_id": 616,
            "schema_name": "Chứng khoán kinh doanh (Phân loại theo đã NY và chưa NY)",
            "classification": "NÚT CHA CẤU TRÚC",
            "explanation": (
                "Nút này mô tả nhánh phân loại; thường không có một ô số riêng. "
                "Các giá trị được map vào những khoản mục con bên dưới; "
                "không được tạo thêm một giá trị trùng cho nút cha."
            ),
        }
    ]


def test_schema_coverage_uses_aggregate_source_refs_instead_of_reporting_false_unmapped(
    client,
) -> None:
    repository = client.application.extensions["bctc_review_repository"]
    mapping = repository._normalized_mapping(
        {
            "report_norm_id": 747,
            "role": "STANDARD",
            "row_id": "aggregate:STANDARD",
            "source_refs": [
                {
                    "label_exact": "Nhóm 1 - Nợ đủ tiêu chuẩn",
                    "row_id": "r1",
                    "locator": {
                        "page_json_version_id": PAGE_VERSION,
                        "section_id": "s1",
                        "table_id": "t1",
                    },
                }
            ],
            "values": [
                {
                    "coefficient": 2_474_846,
                    "source_text": None,
                    "state": "DERIVED_EXACT_SUM_OF_SOURCE_ROWS",
                }
            ],
        },
        physical_page_by_version={PAGE_VERSION: 2},
    )
    gemini_tables = [
        {
            "physical_page": 2,
            "section_id": "s1",
            "table_id": "t1",
            "table_title": "Phân tích chất lượng nợ cho vay",
            "section_title": "Thuyết minh báo cáo tài chính hợp nhất",
            "candidate_status": "READY",
            "candidate_reasons": [],
            "rows": [
                {
                    "id": "r1",
                    "label": "Nhóm 1 - Nợ đủ tiêu chuẩn",
                    "hierarchy": ["Nhóm 1 - Nợ đủ tiêu chuẩn"],
                    "values": ["2.474.846"],
                }
            ],
        }
    ]
    specs = {
        "schema_binding": {
            "family_report_norm_id": 746,
            "role_bindings": [{"role": "STANDARD", "report_norm_id": 747}],
        },
        "topology": {
            "children": [
                {
                    "role": "STANDARD",
                    "role_kind": "ADDITIVE_CHILD",
                    "matchers": [
                        {
                            "aliases": ["Nhóm 1 - Nợ đủ tiêu chuẩn"],
                            "within_role": None,
                        }
                    ],
                }
            ],
            "hard_negative_aliases": [],
        },
    }

    coverage = repository._schema_coverage([], gemini_tables, [mapping], specs)

    assert mapping["source_refs"][0]["physical_page"] == 2
    assert gemini_tables[0]["rows"][0]["mapping_state"] == "MAPPED"
    assert coverage["visible_unmapped"] == []
    assert coverage["source_only"] == []


def test_normalized_mapping_reads_rollforward_top_level_cell_and_locator(client) -> None:
    repository = client.application.extensions["bctc_review_repository"]

    mapping = repository._normalized_mapping(
        {
            "report_norm_id": 747,
            "row_id": "r7",
            "row_label_exact": "Tại ngày 31 tháng 12 năm 2025",
            "period_date": "2025-12-31",
            "locator": {
                "page_json_version_id": PAGE_VERSION,
                "section_id": "s1",
                "table_id": "t1",
            },
            "cell": {
                "coefficient": 4_982_250,
                "source_text": "4.982.250",
                "state": "RAW_SIGNED_INTEGER",
            },
        },
        physical_page_by_version={PAGE_VERSION: 2},
    )

    assert mapping["source_label"] == "Tại ngày 31 tháng 12 năm 2025"
    assert mapping["values"][0]["coefficient"] == 4_982_250
    assert mapping["source_refs"][0]["row_id"] == "r7"
    assert mapping["source_refs"][0]["physical_page"] == 2
