"""Authenticate local PDFs and render the Q1/2025-current universe."""

from __future__ import annotations

import hashlib
import html
import stat
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import fitz

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
)


class BankFilingUniversePublicationV1Error(ValueError):
    """The selected filing bytes or public inventory presentation drifted."""


def _error(message: str) -> BankFilingUniversePublicationV1Error:
    return BankFilingUniversePublicationV1Error(message)


def authenticate_bank_filing_universe_sources_v1(
    universe: dict[str, Any], *, source_root: Path
) -> dict[str, Any]:
    """Re-read every selected PDF and bind its exact page denominator."""

    if type(universe) is not dict or not isinstance(universe.get("filings"), list):
        raise _error("filing universe is not one canonical object")
    root = source_root.resolve()
    if not root.is_dir():
        raise _error("source root is not one directory")
    enriched: list[dict[str, Any]] = []
    for filing in universe["filings"]:
        if type(filing) is not dict or type(filing.get("content_ref")) is not dict:
            raise _error("filing record is malformed")
        content_ref = filing["content_ref"]
        relative = content_ref.get("path")
        if type(relative) is not str:
            raise _error("filing content path is invalid")
        supplied = Path(relative)
        if (
            supplied.is_absolute()
            or ".." in supplied.parts
            or supplied.parts[0] != "vietstock_bctc"
        ):
            raise _error("filing content path is unsafe")
        path = root / supplied
        before = path.stat(follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode) or path.is_symlink():
            raise _error(f"filing source is not one regular non-symlink file: {relative}")
        digest = hashlib.sha256()
        signature = b""
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                if not signature:
                    signature = chunk[:5]
                digest.update(chunk)
        after = path.stat(follow_symlinks=False)
        if (
            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            or signature != b"%PDF-"
            or before.st_size != content_ref.get("size_bytes")
            or digest.hexdigest() != content_ref.get("sha256")
        ):
            raise _error(f"filing source identity drifted: {relative}")
        try:
            with fitz.open(path) as document:
                page_count = document.page_count
        except Exception as exc:
            raise _error(f"filing PDF cannot be opened: {relative}") from exc
        if type(page_count) is not int or page_count <= 0:
            raise _error(f"filing PDF has no physical pages: {relative}")
        enriched.append({**canonical_clone_v1(filing), "page_count": page_count})

    material = {
        **{
            key: canonical_clone_v1(value)
            for key, value in universe.items()
            if key != "universe_id"
        },
        "filings": enriched,
        "local_source_authentication": {
            "all_content_sha256_verified": True,
            "all_pdf_signatures_verified": True,
            "all_sources_regular_nonsymlink_files": True,
            "page_count_engine": "PYMUPDF_DOCUMENT_PAGE_COUNT",
        },
        "summary": {
            **canonical_clone_v1(universe["summary"]),
            "candidate_page_count": sum(item["page_count"] for item in enriched),
            "provider_call_candidate_page_count": sum(
                item["page_count"]
                for item in enriched
                if item["provider_disposition"] == "NEW_VERTEX_FLEX_FRONTIER"
            ),
            "reuse_existing_candidate_page_count": sum(
                item["page_count"]
                for item in enriched
                if item["provider_disposition"] == "REUSE_EXISTING_GEMINI_JSON"
            ),
        },
    }
    return {
        **material,
        "authenticated_universe_id": "bankfilingauthv1:" + canonical_json_sha256_v1(material),
        "universe_id": universe["universe_id"],
    }


def _label(value: str) -> str:
    return {
        "ANNUAL": "Năm",
        "H1": "6 tháng",
        "Q1": "Quý 1",
        "Q2": "Quý 2",
        "Q3": "Quý 3",
        "Q4": "Quý 4",
        "UNKNOWN": "Cần xác thực",
        "AMBIGUOUS": "Tên file mâu thuẫn",
        "CONSOLIDATED": "Hợp nhất",
        "SEPARATE": "Riêng lẻ/CT mẹ",
        "AUDITED": "Kiểm toán",
        "REVIEWED": "Soát xét",
        "UNAUDITED": "Chưa kiểm toán",
    }.get(value, value.replace("_", " ").title())


def render_bank_filing_universe_markdown_v1(universe: dict[str, Any]) -> str:
    """Render a human-first matrix plus a PDF-level inspection appendix."""

    if (
        type(universe) is not dict
        or not isinstance(universe.get("filings"), list)
        or any(type(item.get("page_count")) is not int for item in universe["filings"])
    ):
        raise _error("authenticated filing universe is required for Markdown rendering")
    filings = universe["filings"]
    processed_corpus = universe.get("already_processed_corpus_ref", {})
    processed_filings = processed_corpus.get("document_count", 0)
    processed_pages = processed_corpus.get("page_count", 0)
    new_filings = universe["summary"]["provider_call_candidate_filing_count"]
    new_pages = universe["summary"]["provider_call_candidate_page_count"]
    by_bank = defaultdict(list)
    for filing in filings:
        by_bank[filing["bank"]].append(filing)
    lines = [
        (f"# Ma trận BCTC 27 ngân hàng từ Quý 1/{universe['from_year']} đến hiện tại"),
        "",
        f"Cập nhật theo nguồn đã đăng ký đến ngày **{universe['as_of_date']}**.",
        "",
        (
            "Đây là ma trận **file đầu vào cho Gemini**, chưa phải kết luận mapping. "
            "Tên file chỉ dùng để sắp xếp; phạm vi, kỳ và tình trạng kiểm toán sẽ được "
            "xác thực lại từ nội dung nhìn thấy trong PDF."
        ),
        "",
        "## Tổng quan",
        "",
        "| Chỉ tiêu | Số lượng |",
        "|---|---:|",
        f"| Ngân hàng | {universe['summary']['bank_count']:,} |",
        f"| Ngân hàng tái sử dụng JSON đã có, không gọi API | {universe['summary']['already_processed_bank_count']:,} |",
        f"| Ngân hàng mới trong Vertex Flex frontier | {universe['summary']['new_bank_count']:,} |",
        f"| PDF corpus 8 ngân hàng đã có JSON, chỉ tái sử dụng | {processed_filings:,} |",
        f"| Trang corpus 8 ngân hàng đã có JSON, không gửi lại | {processed_pages:,} |",
        f"| PDF ứng viên của 19 ngân hàng mới | {new_filings:,} |",
        f"| Trang ứng viên được phép gọi Vertex Flex | {new_pages:,} |",
        f"| Tổng PDF được theo dõi sau khi mở rộng | {processed_filings + new_filings:,} |",
        f"| Tổng trang được theo dõi sau khi mở rộng | {processed_pages + new_pages:,} |",
        (
            "| PDF mới cần Gemini xác thực ít nhất một thuộc tính kỳ/phạm vi/kiểm toán | "
            f"{universe['summary']['provider_call_source_authentication_required_count']:,} |"
        ),
        f"| Đường dẫn trùng nội dung đã loại | {universe['summary']['exact_duplicate_path_count']:,} |",
        "",
        "## Tiến độ theo ngân hàng",
        "",
        "| STT | Mã | Xử lý Gemini | PDF mới 2025 | PDF mới 2026 | Tổng PDF mới | Trang mới | Cần xác thực nội dung |",
        "|---:|---|---|---:|---:|---:|---:|---:|",
    ]
    for ordinal, bank in enumerate(universe["bank_codes"], start=1):
        bank_rows = by_bank[bank]
        if bank in universe["already_processed_bank_codes"]:
            lines.append(
                f"| {ordinal} | {bank} | Tái sử dụng JSON đã có; không gọi API | — | — | "
                "— | — | — |"
            )
        else:
            counts = Counter(item["year"] for item in bank_rows)
            lines.append(
                f"| {ordinal} | {bank} | Vertex Flex mới | {counts[2025]} | "
                f"{counts[2026]} | {len(bank_rows)} | "
                f"{sum(item['page_count'] for item in bank_rows):,} | "
                f"{sum(bool(item['source_authentication_flags']) for item in bank_rows)} |"
            )

    lines.extend(
        [
            "",
            "## Danh sách PDF để kiểm tra",
            "",
            (
                "Các nhãn “cần xác thực” không phải lỗi và không phải `UNRESOLVED`; chúng chỉ "
                "cho biết tên file chưa đủ mạnh để kết luận trước khi đọc PDF."
            ),
        ]
    )
    for bank in universe["bank_codes"]:
        lines.extend(["", f"### {bank}", ""])
        if bank in universe["already_processed_bank_codes"]:
            lines.extend(
                [
                    (
                        "Đã xử lý trong corpus 8 ngân hàng; **không đưa bất kỳ PDF nào "
                        "của ngân hàng này vào paid frontier**. Xem danh sách PDF đã chọn "
                        "tại [ma trận 8 ngân hàng](FINANCIAL_REPORT_INVENTORY_8BANK.md)."
                    ),
                    "",
                ]
            )
            continue
        for year in range(universe["from_year"], int(universe["as_of_date"][:4]) + 1):
            year_rows = sorted(
                (item for item in by_bank[bank] if item["year"] == year),
                key=lambda item: item["content_ref"]["path"],
            )
            if not year_rows:
                continue
            lines.extend(
                [
                    f"#### {year}",
                    "",
                    "| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |",
                    "|---|---:|---|---|---|---|",
                ]
            )
            for filing in year_rows:
                ref = filing["content_ref"]["path"]
                filename = ref.rsplit("/", 1)[-1]
                href = "../../" + ref.replace(" ", "%20")
                hints = filing["filename_hints_non_authoritative"]
                flags = filing["source_authentication_flags"]
                flag_label = "Không" if not flags else "; ".join(_label(flag) for flag in flags)
                lines.append(
                    f"| [{html.escape(filename)}](<{href}>) | {filing['page_count']} | "
                    f"{_label(hints['period'])} | {_label(hints['scope'])} | "
                    f"{_label(hints['assurance'])} | {flag_label} |"
                )

    lines.extend(
        [
            "",
            "## Phân biệt trạng thái",
            "",
            "- **Có file nguồn:** PDF đã được xác thực đúng nội dung byte và mở được; chưa nói rằng một family cụ thể có xuất hiện.",
            "- **NOT_OBSERVED:** sau khi đọc đúng phạm vi PDF, family không xuất hiện. Đây không phải lỗi.",
            "- **UNRESOLVED:** family có xuất hiện nhưng kỳ, đơn vị, cấu trúc hoặc mapping chưa đủ chắc chắn.",
            "- **SOURCE_ONLY:** nội dung nhìn thấy nhưng không thuộc khoản mục đích của family đang xét; vẫn được giữ để kiểm toán.",
            "",
            "## Truy vết kỹ thuật",
            "",
            (
                "Các định danh kỹ thuật được giữ ở manifest JSON đi kèm, không dùng làm tên "
                "nhận diện chính trong tài liệu này."
            ),
            "",
        ]
    )
    return "\n".join(lines)
