#!/usr/bin/env python3
"""Render human-readable family progress and unmapped-source ledgers from exact runs."""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.review_app.federated import build_review_repository  # noqa: E402
from bctc_ai.review_app.repository import ReviewSettings  # noqa: E402


class BuildFamilyReviewReadableLedgersError(RuntimeError):
    """The exact review corpus cannot support one complete human ledger."""


def _error(message: str) -> BuildFamilyReviewReadableLedgersError:
    return BuildFamilyReviewReadableLedgersError(message)


def _text(value: Any, fallback: str = "Không xác định") -> str:
    if isinstance(value, str) and value.strip():
        return " ".join(value.strip().split())
    return fallback


def _cell(value: Any) -> str:
    return _text(value, "—").replace("|", "\\|").replace("\n", "<br>")


def _notes(path: Path | None) -> dict[int, str]:
    if path is None:
        return {}
    if path.is_symlink() or not path.is_file():
        raise _error("completed-family notes template is absent")
    result: dict[int, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not re.match(r"^\|\s*\d+\s*\|", line):
            continue
        parts = [part.strip() for part in line.split("|")]
        try:
            ordinal = int(parts[1])
        except (IndexError, ValueError):
            continue
        note = parts[-2] if len(parts) >= 3 else ""
        if note:
            result[ordinal] = note
    return result


def _category(explanation: str, classification: str) -> str:
    upper = f"{classification} {explanation}".upper()
    if "NGHI THUỘC FAMILY KHÁC" in upper:
        return "NGHI LÀ THUỘC FAMILY KHÁC"
    if "NHIỀU ID" in upper:
        return "NHIỀU ID CÓ THỂ PHÙ HỢP"
    if any(token in upper for token in ("OCR", "TOKEN", "KHÔNG ĐỌC", "Ô SỐ", "SỐ NGUYÊN")):
        return "LỖI SOURCE/OCR"
    if any(token in upper for token in ("KỲ", "CỘT", "ĐƠN VỊ", "PERIOD", "UNIT")):
        return "KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ"
    if any(token in upper for token in ("CHA", "CON", "HIERARCH", "CẤU TRÚC")):
        return "KHÔNG XÁC ĐỊNH ĐƯỢC QUAN HỆ CHA/CON"
    return "CHƯA ĐỦ THÔNG TIN ĐỂ XÁC ĐỊNH"


def _parent(item: dict[str, Any]) -> str:
    hierarchy = [value for value in item.get("hierarchy", []) if isinstance(value, str)]
    if len(hierarchy) >= 2:
        return _text(hierarchy[-2])
    return _text(item.get("schema_parent_name"), "Chưa xác định")


def _related(item: dict[str, Any]) -> str:
    values = item.get("values")
    if isinstance(values, list):
        visible = [_text(value, "trống") for value in values]
        return "; ".join(visible)
    return "Chưa xác định"


def _record(
    *,
    family: dict[str, Any],
    document: dict[str, Any],
    status: str,
    kind: str,
    item: dict[str, Any],
) -> dict[str, Any]:
    explanation = _text(
        item.get("explanation")
        or "; ".join(item.get("reason_labels") or item.get("candidate_reason_labels") or []),
        "Candidate có nội dung nguồn nhưng chưa đủ bằng chứng để map chắc chắn.",
    )
    classification = _text(item.get("classification"), kind)
    return {
        "family_order": family["order"],
        "family": family["name"],
        "bank": document["bank"],
        "period": document["period_label"],
        "scope": document["scope_label"],
        "assurance": document["assurance_label"],
        "filename": document["filename"],
        "page": item.get("physical_page"),
        "source_label": _text(
            item.get("source_label") or item.get("table_title"), "Cụm bảng chưa xác định"
        ),
        "parent": _parent(item),
        "related": _related(item),
        "report_norm_id": item.get("report_norm_id"),
        "schema_name": item.get("schema_name"),
        "reason": explanation,
        "classification": classification,
        "category": _category(explanation, classification),
        "kind": kind,
        "status": status,
        "source_sha256": document["source_sha256"],
        "section_id": item.get("section_id"),
        "table_id": item.get("table_id"),
        "row_id": item.get("row_id"),
    }


def _coverage_key(source_sha256: str, kind: str, item: dict[str, Any]) -> tuple[Any, ...]:
    return (
        source_sha256,
        kind,
        item.get("physical_page"),
        item.get("section_id"),
        item.get("table_id"),
        item.get("row_id"),
        item.get("source_label") or item.get("table_title"),
        item.get("report_norm_id"),
    )


def _deduplicated(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[tuple[Any, ...], dict[str, Any]] = {}
    for item in records:
        key = (
            item["family"],
            item["source_sha256"],
            item["kind"],
            item["page"],
            item["section_id"],
            item["table_id"],
            item["row_id"],
            item["source_label"],
            item["report_norm_id"],
        )
        unique.setdefault(key, item)
    return sorted(
        unique.values(),
        key=lambda item: (
            item["family_order"],
            item["bank"],
            item["period"],
            item["filename"],
            item["page"] or 0,
            item["source_label"],
        ),
    )


def build_ledgers(
    repository: Any,
    *,
    notes_by_order: dict[int, str],
    expected_family_count: int,
    expected_document_count: int,
) -> tuple[str, str, dict[str, int]]:
    families = repository.families()
    if len(families) != expected_family_count:
        raise _error("review manifest does not contain the expected family count")
    completed_rows: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    total_ready = total_not_observed = total_unresolved = 0
    for family in families:
        documents = repository.documents(family["id"], {})
        if len(documents) != expected_document_count:
            raise _error(f"family {family['name']} does not cover the expected PDF count")
        counts = defaultdict(int)
        ready_source_only_keys: set[tuple[Any, ...]] = set()
        ready_visible_unmapped_keys: set[tuple[Any, ...]] = set()
        ready_not_seen_keys: set[tuple[Any, ...]] = set()
        source_only_pdfs: set[str] = set()
        visible_unmapped_pdfs: set[str] = set()
        for document in documents:
            status = document["status"]
            counts[status] += 1
            if status == "NOT_OBSERVED":
                continue
            review = repository.review(family["id"], document["source_sha256"])
            coverage = review.get("coverage") or {}
            source_only = coverage.get("source_only") or []
            visible_unmapped = coverage.get("visible_unmapped") or []
            not_seen = coverage.get("not_seen") or []
            if status == "READY":
                ready_source_only_keys.update(
                    _coverage_key(document["source_sha256"], "SOURCE_ONLY", item)
                    for item in source_only
                )
                ready_visible_unmapped_keys.update(
                    _coverage_key(document["source_sha256"], "VISIBLE_UNMAPPED", item)
                    for item in visible_unmapped
                )
                ready_not_seen_keys.update(
                    _coverage_key(document["source_sha256"], "NOT_SEEN", item) for item in not_seen
                )
                if source_only:
                    source_only_pdfs.add(document["source_sha256"])
                if visible_unmapped:
                    visible_unmapped_pdfs.add(document["source_sha256"])
            for item in visible_unmapped:
                records.append(
                    _record(
                        family=family,
                        document=document,
                        status=status,
                        kind="CÓ TRÊN PDF NHƯNG CHƯA MAP",
                        item=item,
                    )
                )
            for item in source_only:
                records.append(
                    _record(
                        family=family,
                        document=document,
                        status=status,
                        kind="SOURCE_ONLY",
                        item=item,
                    )
                )
            if status == "UNRESOLVED":
                unresolved_tables = coverage.get("unresolved_tables") or []
                if not unresolved_tables:
                    unresolved_tables = [
                        {
                            "reason_labels": review.get("disposition", {}).get("reason_labels", []),
                            "table_title": "Cụm family chưa xác định duy nhất",
                        }
                    ]
                for item in unresolved_tables:
                    records.append(
                        _record(
                            family=family,
                            document=document,
                            status=status,
                            kind="UNRESOLVED",
                            item=item,
                        )
                    )
        if (
            counts["READY"] != family["ready_count"]
            or counts["NOT_OBSERVED"] != family["not_observed_count"]
            or counts["UNRESOLVED"] != family["unresolved_count"]
            or sum(counts.values()) != family["document_count"]
        ):
            raise _error(f"family {family['name']} metrics do not match its document frontier")
        total_ready += counts["READY"]
        total_not_observed += counts["NOT_OBSERVED"]
        total_unresolved += counts["UNRESOLVED"]
        completed_rows.append(
            {
                **family,
                "ready_source_only": len(ready_source_only_keys),
                "ready_source_only_pdfs": len(source_only_pdfs),
                "ready_visible_unmapped": len(ready_visible_unmapped_keys),
                "ready_visible_unmapped_pdfs": len(visible_unmapped_pdfs),
                "ready_not_seen": len(ready_not_seen_keys),
            }
        )

    records = _deduplicated(records)
    metrics = {
        "family_count": len(families),
        "family_document_observation_count": sum(item["document_count"] for item in families),
        "ready_count": total_ready,
        "not_observed_count": total_not_observed,
        "unresolved_count": total_unresolved,
        "ledger_record_count": len(records),
    }
    completed = _completed_markdown(completed_rows, metrics, notes_by_order)
    ledger = _ledger_markdown(records, metrics)
    return completed, ledger, metrics


def _completed_markdown(
    families: list[dict[str, Any]], metrics: dict[str, int], notes_by_order: dict[int, str]
) -> str:
    lines = [
        "# Tiến độ toàn bộ family — bản review 27 ngân hàng",
        "",
        "Bảng này được tạo từ exact family runs trong review manifest. Mã kỹ thuật không ",
        "được dùng làm thông tin nhận diện chính.",
        "",
        "Quy ước: **NOT_OBSERVED** là family không xuất hiện trong đúng phạm vi PDF; ",
        "**UNRESOLVED** là có nội dung nguồn nhưng chưa map/cấu trúc chắc chắn; ",
        "**SOURCE_ONLY** là dòng nhìn thấy nhưng chưa thuộc mapping đích của family.",
        "",
        f"Tổng cộng: **{metrics['family_count']} family**, "
        f"**{metrics['family_document_observation_count']} lượt family–PDF**, "
        f"**{metrics['ready_count']} READY**, "
        f"**{metrics['not_observed_count']} NOT_OBSERVED**, "
        f"**{metrics['unresolved_count']} UNRESOLVED**.",
        "",
        "| # | Family | PDF khảo sát | READY | NOT_OBSERVED | UNRESOLVED | "
        "READY còn dòng chưa map | SOURCE_ONLY trong READY | Schema item chưa thấy trong READY | "
        "Cấu trúc/biến thể chính |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for family in families:
        lines.append(
            "| {order} | {name} | {document_count} | {ready_count} | "
            "{not_observed_count} | {unresolved_count} | {ready_visible_unmapped} dòng/"
            "{ready_visible_unmapped_pdfs} PDF | {ready_source_only} dòng/"
            "{ready_source_only_pdfs} PDF | {ready_not_seen} | {note} |".format(
                note=_cell(
                    notes_by_order.get(
                        family["order"], "Xem trực tiếp cấu trúc nguồn trong dashboard."
                    )
                ),
                **family,
            )
        )
    lines.extend(
        [
            "",
            "Chi tiết từng PDF/dòng chưa map và SOURCE_ONLY nằm trong file ledger đi kèm. "
            "Các schema item chưa thấy chỉ là kiểm kê âm trong PDF READY, không phải lỗi và "
            "không được gộp vào UNRESOLVED.",
            "",
        ]
    )
    return "\n".join(lines)


def _ledger_markdown(records: list[dict[str, Any]], metrics: dict[str, int]) -> str:
    lines = [
        "# Các PDF và khoản mục chưa map — ledger review 27 ngân hàng",
        "",
        "Ledger này tách rõ UNRESOLVED, dòng có trên PDF nhưng chưa map và SOURCE_ONLY. "
        "Không có dòng nào tự động bị kết luận ‘CHƯA CÓ TRONG SCHEMA’; kết luận đó chỉ được "
        "ghi sau một cuộc rà toàn schema có bằng chứng riêng.",
        "",
        f"Tổng số record sau khử trùng: **{metrics['ledger_record_count']}**.",
        "",
    ]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["kind"]].append(record)
    for kind in ("UNRESOLVED", "CÓ TRÊN PDF NHƯNG CHƯA MAP", "SOURCE_ONLY"):
        items = grouped.get(kind, [])
        lines.extend([f"## {kind} — {len(items)} record", ""])
        if not items:
            lines.extend(["Không có.", ""])
            continue
        for ordinal, item in enumerate(items, start=1):
            schema = (
                f"{item['report_norm_id']} — {_text(item['schema_name'])}"
                if isinstance(item["report_norm_id"], int)
                else "Chưa có ID gần nhất được xác định duy nhất"
            )
            lines.extend(
                [
                    f"### {ordinal}. {_text(item['family'])} — {_text(item['bank'])} — "
                    f"{_text(item['filename'])}",
                    "",
                    f"- **Family:** {_text(item['family'])}",
                    f"- **Ngân hàng:** {_text(item['bank'])}",
                    f"- **Kỳ:** {_text(item['period'])}",
                    f"- **Báo cáo:** {_text(item['scope'])}; {_text(item['assurance'])}",
                    f"- **File PDF:** `{_text(item['filename'])}`",
                    f"- **Trang PDF:** {item['page'] if item['page'] is not None else 'Chưa định vị được trang duy nhất'}",
                    f"- **Khoản mục nhìn thấy:** `{_text(item['source_label'])}`",
                    f"- **Khoản mục cha:** {_text(item['parent'])}",
                    f"- **Giá trị/hàng liên quan:** {_text(item['related'])}",
                    f"- **ReportNormId gần nhất:** {schema}",
                    f"- **Lý do chưa map/giữ SOURCE_ONLY:** {_text(item['reason'])}",
                    f"- **Phân loại nguyên nhân:** **{_text(item['category'])}**",
                    f"- **Trạng thái PDF trong family:** {_text(item['status'])}",
                    "",
                    "<details><summary>Truy vết kỹ thuật</summary>",
                    "",
                    f"`source_sha256={item['source_sha256']}; section={item['section_id']}; "
                    f"table={item['table_id']}; row={item['row_id']}`",
                    "",
                    "</details>",
                    "",
                ]
            )
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-manifest", type=Path, required=True)
    parser.add_argument(
        "--schema",
        type=Path,
        default=ROOT / "reference/schemas/schema_graph.jsonl",
    )
    parser.add_argument("--notes-template", type=Path)
    parser.add_argument("--completed-output", type=Path, required=True)
    parser.add_argument("--ledger-output", type=Path, required=True)
    parser.add_argument("--expected-family-count", type=int, default=55)
    parser.add_argument("--expected-document-count", type=int, default=419)
    return parser


def _write_once(path: Path, value: str) -> None:
    payload = value.encode("utf-8")
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
            raise _error(f"write-once readable ledger drifted: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def main() -> int:
    args = _parser().parse_args()
    settings = ReviewSettings(
        results_database=None,
        page_database=None,
        pdf_root=None,
        schema_path=args.schema,
        cache_directory=Path("/tmp/bctc-ai-review-ledger-cache"),
        run_manifest=args.run_manifest,
    )
    completed, ledger, metrics = build_ledgers(
        build_review_repository(settings),
        notes_by_order=_notes(args.notes_template),
        expected_family_count=args.expected_family_count,
        expected_document_count=args.expected_document_count,
    )
    _write_once(args.completed_output, completed)
    _write_once(args.ledger_output, ledger)
    print(metrics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
