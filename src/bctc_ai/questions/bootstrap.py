from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

from bctc_ai.core.atomic import atomic_write_jsonl, atomic_write_text

QUESTION_FIELDS = [
    "question_id",
    "statement_type",
    "schema_id",
    "canonical_name",
    "bank",
    "document",
    "page",
    "table_id",
    "row_id",
    "pdf_label",
    "current_value",
    "comparative_value",
    "unit",
    "parent_id",
    "previous_schema_id",
    "next_schema_id",
    "role_a_result",
    "role_b_result",
    "mongodb_evidence",
    "ranked_candidates",
    "confidence_gap",
    "root_cause",
    "exact_question",
    "recommended_default",
    "priority",
    "user_response",
    "resolution_status",
]


def bootstrap_questions() -> list[dict[str, Any]]:
    empty = {key: None for key in QUESTION_FIELDS}
    common = {
        **empty,
        "role_a_result": "NOT_RUN",
        "role_b_result": "NOT_RUN",
        "mongodb_evidence": [],
        "ranked_candidates": [],
        "confidence_gap": None,
        "user_response": None,
        "resolution_status": "OPEN",
    }
    return [
        {
            **common,
            "question_id": "Q-BOOT-001",
            "statement_type": "LCTT",
            "root_cause": "SCHEMA_AUTHORITY_RESOLVED",
            "exact_question": (
                "Which contiguous workbook-order blocks define the semantic INDIRECT and "
                "DIRECT cash-flow branches?"
            ),
            "recommended_default": (
                "Use contiguous workbook positions, never increasing numeric ranges: positions "
                "1-57 with endpoints 4155→4168 are INDIRECT; positions 58-107 with endpoints "
                "4104→4116 are DIRECT."
            ),
            "priority": "CRITICAL",
            "user_response": (
                "Q-BOOT-001 confirmed on 2026-08-06: 4155→4168 in template order is "
                "INDIRECT; 4104→4116 in template order is DIRECT."
            ),
            "resolution_status": "RESOLVED",
        },
        {
            **common,
            "question_id": "Q-BOOT-002",
            "statement_type": "ALL",
            "root_cause": "MONGODB_NOT_DISCOVERED",
            "exact_question": (
                "Please provide the MongoDB URI (or secret name), database and collection names, "
                "and a read-only account for historical weak-reference indexing."
            ),
            "recommended_default": "Continue PDF-only; do not use historical values until read-only access is verified.",
            "priority": "HIGH",
            "user_response": (
                "Uploaded financial_20_02_2022.gz. Registered SHA-256 "
                "0456df4aebb93b58c433b0d2a8c13bbb9402e1511d07758716976b94989204b9."
            ),
            "resolution_status": "RESOLVED",
        },
        {
            **common,
            "question_id": "Q-BOOT-003",
            "statement_type": "ALL",
            "root_cause": "OFF_MACHINE_BACKUP_TARGET_CONFIGURED",
            "exact_question": (
                "Which versioned off-machine target should receive source PDFs, schemas, OCR, "
                "references, workbooks, experiments, database dumps, and model manifests?"
            ),
            "recommended_default": "Use a versioned S3-compatible bucket with object lock and a dedicated prefix.",
            "priority": "CRITICAL",
            "user_response": (
                "On 2026-08-06 the user supplied s3://test-s3-duylv/ and authorized backup; "
                "profile access, region, AES-256 default encryption and public-access blocking "
                "are verified."
            ),
            "resolution_status": "TARGET_CONFIGURED_UPLOAD_IN_PROGRESS",
        },
        {
            **common,
            "question_id": "Q-BOOT-004",
            "statement_type": "TM",
            "schema_id": 1944,
            "canonical_name": "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
            "role_a_result": "SCHEMA_TARGET_ENROLLED_MANDATORY_SEARCH_PENDING_PER_DOCUMENT",
            "role_b_result": "SCHEMA_TARGET_ENROLLED_MANDATORY_SEARCH_PENDING_PER_DOCUMENT",
            "root_cause": "APPEND_ONLY_SCHEMA_ITEM_APPLIED",
            "exact_question": (
                "The supplied TM schema ends at ID 1943. Should proposed TM ID 1944 be appended "
                "with the name stated in the directive?"
            ),
            "recommended_default": "Keep it as a pending append-only proposal; do not alter the supplied workbook yet.",
            "priority": "HIGH",
            "user_response": (
                "Approved on 2026-08-06: append TM ReportNormID 1944 with the exact proposed "
                "name under the append-only policy, preserving every existing ID, name, order, "
                "and mapping; include it in Role A, Role B, Excel, evaluation, mandatory search, "
                "and PROGRESS_REPORT.md."
            ),
            "resolution_status": "RESOLVED",
        },
        {
            **common,
            "question_id": "Q-BOOT-005",
            "statement_type": "ALL",
            "root_cause": "S3_BUCKET_VERSIONING_ENABLED",
            "exact_question": "May bucket versioning be enabled on test-s3-duylv?",
            "recommended_default": (
                "Do not change retention settings without explicit approval; use unique "
                "content-addressed keys and keep the production gate failed until versioning "
                "is enabled."
            ),
            "priority": "HIGH",
            "user_response": (
                "Approved on 2026-08-06. Enable bucket versioning, retain public-access "
                "blocking and default encryption, and do not enable Object Lock."
            ),
            "resolution_status": "RESOLVED",
        },
    ]


def write_questions(project_root: Path, records: list[dict[str, Any]]) -> None:
    atomic_write_jsonl(project_root / "questions_for_user.jsonl", records)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=QUESTION_FIELDS, lineterminator="\n")
    writer.writeheader()
    for record in records:
        row = {
            field: json.dumps(record[field], ensure_ascii=False)
            if isinstance(record[field], (list, dict))
            else record[field]
            for field in QUESTION_FIELDS
        }
        writer.writerow(row)
    atomic_write_text(project_root / "questions_for_user.csv", buffer.getvalue())

    lines = [
        "# Questions for the user",
        "",
        "Only material ambiguities that cannot be safely resolved from current evidence are listed.",
        "Answers should be recorded in the CSV or JSONL `user_response` field; IDs remain stable.",
        "Q-BOOT-004 and Q-BOOT-005 are approved; implementation evidence is tracked separately.",
        "",
    ]
    for record in records:
        lines.extend(
            [
                f"## {record['question_id']} — {record['priority']}",
                "",
                str(record["exact_question"]),
                "",
                f"Recommended safe default: {record['recommended_default']}",
                "",
            ]
        )
        if record.get("user_response"):
            lines.extend([f"Recorded response: {record['user_response']}", ""])
        lines.extend([f"Status: {record['resolution_status']}", ""])
    atomic_write_text(project_root / "questions_for_user.md", "\n".join(lines))
