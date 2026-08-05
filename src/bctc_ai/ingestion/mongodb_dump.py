from __future__ import annotations

import gzip
import struct
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pymongo import MongoClient
from rapidfuzz.fuzz import ratio

from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import retrieval_key
from bctc_ai.schema.hierarchy import load_hierarchy_reference
from bctc_ai.schema.registry import load_all


@dataclass(frozen=True)
class MongoArchiveHeader:
    database: str | None
    first_collection: str | None
    server_version: str | None
    tool_version: str | None


def _bson_string_after_key(data: bytes, key: bytes) -> str | None:
    marker = key + b"\x00"
    index = data.find(marker)
    if index < 0:
        return None
    length_start = index + len(marker)
    if length_start + 4 > len(data):
        return None
    length = struct.unpack_from("<i", data, length_start)[0]
    value_start = length_start + 4
    value_end = value_start + length - 1
    if length < 1 or value_end >= len(data) or data[value_end] != 0:
        return None
    return data[value_start:value_end].decode("utf-8", errors="replace")


def read_mongodb_archive_header(path: Path) -> MongoArchiveHeader:
    with gzip.open(path, "rb") as stream:
        header = stream.read(1_048_576)
    return MongoArchiveHeader(
        database=_bson_string_after_key(header, b"db"),
        first_collection=_bson_string_after_key(header, b"collection"),
        server_version=_bson_string_after_key(header, b"server_version"),
        tool_version=_bson_string_after_key(header, b"tool_version"),
    )


def audit_financial_reference_dump(
    archive: Path,
    project_root: Path,
    *,
    mongo_uri: str,
    proposed_id: int,
    proposed_name: str,
) -> dict[str, Any]:
    """Audit only the restored financial template collection; never write the URI."""
    archive = archive.resolve()
    header = read_mongodb_archive_header(archive)
    if not header.database:
        raise ValueError(f"Mongo archive database name was not found: {archive}")

    _, schema = load_all(project_root / "template", project_root)
    hierarchy_registry, hierarchy = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml",
        project_root,
        schema,
    )
    schema_collisions = [
        {"statement_type": item.statement_type, "name": item.canonical_name}
        for item in schema
        if item.schema_id == proposed_id
    ]
    hierarchy_collisions = [
        {"statement_type": item.statement_type, "label": item.label}
        for item in hierarchy
        if item.schema_id == proposed_id
    ]

    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5_000)
    try:
        client.admin.command("ping")
        database = client[header.database]
        collection = database["financial_report_templates"]
        template_count = collection.count_documents({})
        if template_count == 0:
            raise ValueError("financial_report_templates is not restored or is empty")
        mongo_collisions = list(
            collection.find(
                {"report_norm_id": proposed_id},
                {"_id": 0, "stock_industry": 1, "chart_menu_id": 1, "report_name": 1},
            )
        )
        candidates = []
        proposed_key = retrieval_key(proposed_name)
        for document in collection.find(
            {"stock_industry": "bank"},
            {"_id": 0, "report_norm_id": 1, "report_name": 1, "chart_menu_id": 1},
        ):
            name = str(document.get("report_name", ""))
            candidates.append(
                {
                    "report_norm_id": document.get("report_norm_id"),
                    "report_name": name,
                    "chart_menu_id": document.get("chart_menu_id"),
                    "name_similarity": round(ratio(proposed_key, retrieval_key(name)) / 100, 6),
                }
            )
        candidates.sort(key=lambda record: (-record["name_similarity"], record["report_norm_id"]))
        bank_template_count = collection.count_documents({"stock_industry": "bank"})
    finally:
        client.close()

    append_safe = not schema_collisions and not hierarchy_collisions and not mongo_collisions
    return {
        "format_version": 1,
        "captured_at": datetime.now(UTC).isoformat(),
        "archive": {
            "path": archive.relative_to(project_root).as_posix(),
            "size_bytes": archive.stat().st_size,
            "sha256": sha256_file(archive),
            "header": asdict(header),
        },
        "restored_scope": {
            "database": header.database,
            "collection": "financial_report_templates",
            "document_count": template_count,
            "bank_document_count": bank_template_count,
            "excluded_out_of_scope_collections": ["user", "chat_sessions"],
        },
        "collision_audit": {
            "proposed_id": proposed_id,
            "proposed_name": proposed_name,
            "supplied_schema_collisions": schema_collisions,
            "hierarchy_reference_collisions": hierarchy_collisions,
            "mongodb_template_collisions": mongo_collisions,
            "append_safe_from_id_collision_perspective": append_safe,
            "semantic_or_parent_approval_still_required": True,
            "nearest_mongodb_name_candidates": candidates[:10],
        },
        "hierarchy_reference_status": hierarchy_registry.status,
    }
