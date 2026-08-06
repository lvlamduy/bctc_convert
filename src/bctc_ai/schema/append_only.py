from __future__ import annotations

import hashlib
import io
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_bytes, sha256_file, stable_records_hash
from bctc_ai.schema.xlsx_reader import read_rows

TM_1944_ID = 1944
TM_1944_NAME = "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán"
TM_1944_PREDECESSOR_ID = 1943
TM_1944_WORKBOOK = "template/Bank_TM_ReportNormId.xlsx"
TM_1944_BEFORE_SHA256 = "6af23d7bf930fe6db7cbfb83df78c7c7ab876142757d1dde5707c1667b54a8a0"
TM_1944_BEFORE_ROW_COUNT = 1385
TM_1944_APPEND_ROW = 1386
TM_1944_DISPLAY_ORDER = 1384

_SHEET_MEMBER = "xl/worksheets/sheet1.xml"
_SHARED_STRINGS_MEMBER = "xl/sharedStrings.xml"
_TARGET_MEMBERS = {_SHEET_MEMBER, _SHARED_STRINGS_MEMBER}


class AppendOnlySchemaError(RuntimeError):
    pass


@dataclass(frozen=True)
class AppendOnlyMigrationResult:
    status: str
    workbook_sha256: str
    audit_path: str


def _member_hashes(payload: bytes) -> dict[str, str]:
    with ZipFile(io.BytesIO(payload)) as archive:
        return {
            info.filename: hashlib.sha256(archive.read(info.filename)).hexdigest()
            for info in archive.infolist()
        }


def _identity_records(path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for source_row, row in enumerate(read_rows(path), start=1):
        records.append(
            {
                "source_row": source_row,
                "ordinal": row.get("A", ""),
                "report_norm_id": row.get("B", ""),
                "report_norm_name": row.get("C", ""),
            }
        )
    return records


def _identity_hash(records: list[dict[str, object]]) -> str:
    return stable_records_hash(
        json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records
    )


def _replace_once(payload: bytes, old: bytes, new: bytes, *, description: str) -> bytes:
    if payload.count(old) != 1:
        raise AppendOnlySchemaError(f"expected exactly one {description} marker")
    return payload.replace(old, new, 1)


def _patch_shared_strings(payload: bytes) -> tuple[bytes, int]:
    if TM_1944_NAME.encode("utf-8") in payload:
        raise AppendOnlySchemaError("TM 1944 name already exists in shared strings")
    root_match = re.search(rb"<sst\b[^>]*>", payload)
    if root_match is None:
        raise AppendOnlySchemaError("sharedStrings.xml has no sst root")
    root = root_match.group(0)
    count_match = re.search(rb'\bcount="(\d+)"', root)
    unique_match = re.search(rb'\buniqueCount="(\d+)"', root)
    if count_match is None or unique_match is None:
        raise AppendOnlySchemaError("sharedStrings.xml lacks count metadata")
    count = int(count_match.group(1))
    unique_count = int(unique_match.group(1))
    actual_unique = payload.count(b"<si>")
    if unique_count != actual_unique:
        raise AppendOnlySchemaError(
            f"shared-string count drift: declared={unique_count}, actual={actual_unique}"
        )
    new_root = root.replace(
        count_match.group(0), f'count="{count + 1}"'.encode("ascii"), 1
    ).replace(
        unique_match.group(0), f'uniqueCount="{unique_count + 1}"'.encode("ascii"), 1
    )
    patched = _replace_once(payload, root, new_root, description="shared-string root")
    escaped_name = (
        TM_1944_NAME.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    appended = f"<si><t>{escaped_name}</t></si></sst>".encode()
    patched = _replace_once(
        patched,
        b"</sst>",
        appended,
        description="shared-string closing tag",
    )
    return patched, unique_count


def _patch_sheet(payload: bytes, *, shared_string_index: int) -> bytes:
    patched = _replace_once(
        payload,
        b'<dimension ref="A1:C1385"/>',
        b'<dimension ref="A1:C1386"/>',
        description="worksheet dimension",
    )
    predecessor = (
        b'<row r="1385" spans="1:3" ht="15" x14ac:dyDescent="0.2">'
        b'<c r="A1385" s="1"><v>1383</v></c><c r="B1385"><v>1943</v></c>'
    )
    if predecessor not in patched:
        raise AppendOnlySchemaError("TM predecessor row 1943 does not match the approved baseline")
    appended_row = (
        '<row r="1386" spans="1:3" ht="15" x14ac:dyDescent="0.2">'
        '<c r="A1386" s="1"><v>1384</v></c>'
        '<c r="B1386"><v>1944</v></c>'
        f'<c r="C1386" t="s"><v>{shared_string_index}</v></c></row>'
    ).encode("ascii")
    return _replace_once(
        patched,
        b"</sheetData>",
        appended_row + b"</sheetData>",
        description="sheetData closing tag",
    )


def _build_appended_workbook(before: bytes) -> tuple[bytes, dict[str, str], dict[str, str]]:
    before_hashes = _member_hashes(before)
    output = io.BytesIO()
    with ZipFile(io.BytesIO(before)) as source, ZipFile(
        output, "w", compression=ZIP_DEFLATED
    ) as destination:
        patched_shared_strings, shared_string_index = _patch_shared_strings(
            source.read(_SHARED_STRINGS_MEMBER)
        )
        destination.comment = source.comment
        for info in source.infolist():
            payload = source.read(info.filename)
            if info.filename == _SHARED_STRINGS_MEMBER:
                payload = patched_shared_strings
            elif info.filename == _SHEET_MEMBER:
                payload = _patch_sheet(payload, shared_string_index=shared_string_index)
            destination.writestr(info, payload)
    after = output.getvalue()
    after_hashes = _member_hashes(after)
    if set(before_hashes) != set(after_hashes):
        raise AppendOnlySchemaError("XLSX ZIP member set changed during append")
    changed = {name for name in before_hashes if before_hashes[name] != after_hashes[name]}
    if changed != _TARGET_MEMBERS:
        raise AppendOnlySchemaError(f"unexpected XLSX members changed: {sorted(changed)}")
    return after, before_hashes, after_hashes


def _atomic_replace_authorized_schema(path: Path, payload: bytes) -> str:
    expected = sha256_bytes(payload)
    mode = path.stat().st_mode & 0o777
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary_path, mode)
        if sha256_file(temporary_path) != expected:
            raise AppendOnlySchemaError("temporary appended workbook failed SHA-256 verification")
        os.replace(temporary_path, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        if sha256_file(path) != expected:
            raise AppendOnlySchemaError("appended workbook failed post-rename SHA-256 verification")
        return expected
    finally:
        temporary_path.unlink(missing_ok=True)


def verify_tm_1944_append(project_root: Path, audit_path: Path) -> dict[str, object]:
    project_root = project_root.resolve()
    workbook_path = project_root / TM_1944_WORKBOOK
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit.get("format_version") != 1 or audit.get("status") != "APPLIED_AND_VERIFIED":
        raise AppendOnlySchemaError("invalid TM 1944 append audit status")
    if audit.get("workbook", {}).get("before_sha256") != TM_1944_BEFORE_SHA256:
        raise AppendOnlySchemaError("TM 1944 baseline hash does not match the approved workbook")
    current_hash = sha256_file(workbook_path)
    if current_hash != audit.get("workbook", {}).get("after_sha256"):
        raise AppendOnlySchemaError("TM workbook differs from the verified post-append identity")
    records = _identity_records(workbook_path)
    if len(records) != TM_1944_APPEND_ROW:
        raise AppendOnlySchemaError(f"unexpected TM row count after append: {len(records)}")
    expected_last = {
        "source_row": TM_1944_APPEND_ROW,
        "ordinal": str(TM_1944_DISPLAY_ORDER),
        "report_norm_id": str(TM_1944_ID),
        "report_norm_name": TM_1944_NAME,
    }
    if records[-1] != expected_last:
        raise AppendOnlySchemaError(f"TM 1944 appended row drift: {records[-1]}")
    prefix_hash = _identity_hash(records[:-1])
    if prefix_hash != audit.get("preservation", {}).get("existing_rows_sha256"):
        raise AppendOnlySchemaError("one or more pre-existing TM identities/order/names changed")
    member_hashes = _member_hashes(workbook_path.read_bytes())
    for member, expected in audit.get("preservation", {}).get(
        "unchanged_zip_members_sha256", {}
    ).items():
        if member_hashes.get(member) != expected:
            raise AppendOnlySchemaError(f"unchanged XLSX member drift: {member}")
    return audit


def append_tm_1944(
    project_root: Path,
    *,
    audit_path: Path | None = None,
) -> AppendOnlyMigrationResult:
    project_root = project_root.resolve()
    workbook_path = project_root / TM_1944_WORKBOOK
    audit_path = (
        audit_path.resolve()
        if audit_path is not None
        else project_root / "data/registered/schema_append_1944.json"
    )
    if audit_path.is_file():
        audit = verify_tm_1944_append(project_root, audit_path)
        return AppendOnlyMigrationResult(
            status="ALREADY_APPLIED_AND_VERIFIED",
            workbook_sha256=str(audit["workbook"]["after_sha256"]),
            audit_path=str(audit_path),
        )

    before = workbook_path.read_bytes()
    if sha256_bytes(before) != TM_1944_BEFORE_SHA256:
        raise AppendOnlySchemaError("TM workbook is neither the approved baseline nor audited append")
    before_records = _identity_records(workbook_path)
    if len(before_records) != TM_1944_BEFORE_ROW_COUNT:
        raise AppendOnlySchemaError("approved TM baseline row count changed")
    if before_records[-1]["report_norm_id"] != str(TM_1944_PREDECESSOR_ID):
        raise AppendOnlySchemaError("approved TM predecessor is no longer ID 1943")
    if any(record["report_norm_id"] == str(TM_1944_ID) for record in before_records):
        raise AppendOnlySchemaError("TM ID 1944 already exists without an append audit")
    existing_rows_hash = _identity_hash(before_records)

    after, before_members, after_members = _build_appended_workbook(before)
    descriptor, candidate_name = tempfile.mkstemp(
        prefix=".tm-1944-candidate-", suffix=".xlsx", dir=workbook_path.parent
    )
    candidate_path = Path(candidate_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(after)
            stream.flush()
            os.fsync(stream.fileno())
        candidate_records = _identity_records(candidate_path)
        if candidate_records[:-1] != before_records:
            raise AppendOnlySchemaError("candidate append changed an existing TM row")
        if candidate_records[-1] != {
            "source_row": TM_1944_APPEND_ROW,
            "ordinal": str(TM_1944_DISPLAY_ORDER),
            "report_norm_id": str(TM_1944_ID),
            "report_norm_name": TM_1944_NAME,
        }:
            raise AppendOnlySchemaError("candidate append does not contain the authorized row")
    finally:
        candidate_path.unlink(missing_ok=True)

    after_sha256 = _atomic_replace_authorized_schema(workbook_path, after)
    unchanged_members = {
        name: digest for name, digest in before_members.items() if name not in _TARGET_MEMBERS
    }
    audit: dict[str, object] = {
        "format_version": 1,
        "status": "APPLIED_AND_VERIFIED",
        "applied_at": datetime.now(UTC).isoformat(),
        "authority": {
            "question_id": "Q-BOOT-004",
            "approved_on": "2026-08-06",
            "policy": "APPEND_ONLY",
        },
        "workbook": {
            "path": TM_1944_WORKBOOK,
            "before_sha256": TM_1944_BEFORE_SHA256,
            "after_sha256": after_sha256,
            "before_row_count_including_header": TM_1944_BEFORE_ROW_COUNT,
            "after_row_count_including_header": TM_1944_APPEND_ROW,
        },
        "appended_item": {
            "statement_type": "TM",
            "schema_id": TM_1944_ID,
            "canonical_name": TM_1944_NAME,
            "source_row": TM_1944_APPEND_ROW,
            "display_order_zero_based": TM_1944_DISPLAY_ORDER,
            "previous_schema_id": TM_1944_PREDECESSOR_ID,
            "next_schema_id": None,
        },
        "preservation": {
            "existing_rows_preserved": True,
            "existing_rows_sha256": existing_rows_hash,
            "existing_id_name_order_mapping_preserved": True,
            "zip_member_set_preserved": True,
            "only_changed_zip_members": sorted(_TARGET_MEMBERS),
            "unchanged_zip_members_sha256": unchanged_members,
            "changed_zip_members_before_sha256": {
                name: before_members[name] for name in sorted(_TARGET_MEMBERS)
            },
            "changed_zip_members_after_sha256": {
                name: after_members[name] for name in sorted(_TARGET_MEMBERS)
            },
            "supporting_hierarchy_workbook_mutated": False,
            "hierarchy_parent_status": "NOT_INFERRED_WITHOUT_SOURCE_AUTHORITY",
        },
    }
    atomic_write_json(audit_path, audit)
    verify_tm_1944_append(project_root, audit_path)
    return AppendOnlyMigrationResult(
        status="APPLIED_AND_VERIFIED",
        workbook_sha256=after_sha256,
        audit_path=str(audit_path),
    )
