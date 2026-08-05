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
            "root_cause": "SCHEMA_AUTHORITY_CONFLICT",
            "exact_question": (
                "The directive says IDs 4104-4154 are indirect and 4155-4168 are direct, "
                "but the supplied workbook labels 4155+ with profit-before-tax adjustments "
                "(indirect) and 4104+ with cash received/paid rows (direct). Which authority "
                "should define the semantic DIRECT/INDIRECT branch names?"
            ),
            "recommended_default": (
                "Segment by contiguous workbook position, never numeric ranges. Workbook rows 1-57 "
                "run 4155→4168 and contain the profit/adjustment anchors; rows 58-107 run "
                "4104→4116 and contain cash-receipt/payment anchors. Withhold semantic "
                "high-confidence acceptance until the contradictory labels/endpoints are confirmed."
            ),
            "priority": "CRITICAL",
            "user_response": (
                "Use workbook order, not increasing numeric ID. The response also states "
                "4104-4154 is indirect and 4155-4168 is direct, which conflicts with the "
                "visible ordered anchor examples and with 4154 being mid-block."
            ),
            "resolution_status": "REOPENED_EVIDENCE_CONFLICT",
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
            "root_cause": "OFF_MACHINE_BACKUP_NOT_CONFIGURED",
            "exact_question": (
                "Which versioned off-machine target should receive source PDFs, schemas, OCR, "
                "references, workbooks, experiments, database dumps, and model manifests?"
            ),
            "recommended_default": "Use a versioned S3-compatible bucket with object lock and a dedicated prefix.",
            "priority": "CRITICAL",
            "user_response": (
                "During model development, keep artifacts on the VPS and commit every working "
                "version to Git."
            ),
            "resolution_status": "RESOLVED_FOR_DEVELOPMENT",
        },
        {
            **common,
            "question_id": "Q-BOOT-004",
            "statement_type": "TM",
            "schema_id": 1944,
            "canonical_name": "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
            "root_cause": "APPEND_ONLY_SCHEMA_ITEM_MISSING",
            "exact_question": (
                "The supplied TM schema ends at ID 1943. Should proposed TM ID 1944 be appended "
                "with the name stated in the directive?"
            ),
            "recommended_default": "Keep it as a pending append-only proposal; do not alter the supplied workbook yet.",
            "priority": "HIGH",
            "user_response": "Check that ReportNormID 1944 does not collide before adding it.",
            "resolution_status": "COLLISION_CHECK_PASSED_APPEND_DECISION_OPEN",
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
