#!/usr/bin/env python3
"""Run an EXPERIMENTAL dual-component family over an authenticated JSON corpus."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import stat
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.gemini_json_dual_component_accounting_family_v1 import (  # noqa: E402
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    build_gemini_json_dual_component_region_query_receipt_v1,
    evaluate_gemini_json_dual_component_family_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_json_bytes_v1,
    same_typed_json_v1,
)
from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import (  # noqa: E402
    validate_current_corpus_manifest_index_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    load_page_json_versions_v1,
    query_selected_dual_component_family_regions_v1,
    validate_selected_dual_component_family_candidate_replays_v1,
    validate_selected_dual_component_family_query_evidence_v1,
)


class RunGeminiJsonDualComponentAccountingFamilyV1Error(RuntimeError):
    """The immutable corpus, declarative policy, or experimental output drifted."""


def _error(message: str) -> RunGeminiJsonDualComponentAccountingFamilyV1Error:
    return RunGeminiJsonDualComponentAccountingFamilyV1Error(message)


AUDIT_FORMAT_VERSION = "GEMINI_JSON_DUAL_COMPONENT_EXPERIMENTAL_AUDIT_V1"
PINNED_OLD_ORACLES = (
    {
        "format_version": "PURCHASED_DEBT_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": "docs/experiments/E-0066-purchased-debt-8bank-codex-verified-mapping-v1.json",
        "sha256": "aa45d9122c8b84379d1522813027961ff229f3b34ea179fa7c933f680377a29e",
    },
    {
        "format_version": "ANNUAL_2025_PURCHASED_DEBT_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": "docs/experiments/E-0120-annual-2025-purchased-debt-8bank-codex-verified-mapping-v1.json",
        "sha256": "cb00c62820304fa4866af9c30741c6ee70fde256dc4710e422fe1c41be0914e4",
    },
)
PINNED_PREFLIGHT_AXIS_SHA256 = {
    "comparator": "65f5ca3015d64267a96ecc84780e0de5515e038d0fd17593cfece8a2a48df2fa",
    "equation": "399b5df50158286bc661a9a3d88f5feda35139ff78ff554ef8e3b86a067b267c",
    "mapping": "b808337b3418fea59ba8a489aa75bae262e5e341e49bf5b3f73a9b9e21f41194",
    "page": "60ef90ba34157272a95c7175d0497fc65dd32b60334987e4bfda9f9827c380f8",
    "region": "9c3756fcafaf04f2600f7e46325455bf9a14f9c55333ca3cf9f493846867c02f",
}
PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256 = (
    "601be9fc2a894af2ce4f4c982d5347521a6268a46c075d9cc96f9828baef8ae8"
)
PINNED_COMPILED_SPEC_SHA256 = {
    "evaluation": "b6f1703fe815a2741d8f22929c8aa094bb0ee76c801c132311ccb8c3a7db88ff",
    "schema": "caa93bd566b31f1645d7b0097eda5ee064c1acaae843a6b1d4afbe136949edfb",
    "topology": "bc1241b3cd77d9126e96c9ccb01078f0860bf4295c3f5622c5d5176ff17f084c",
}
PINNED_AUDIT_AXIS_COUNTS = {
    "comparator": 16,
    "equation": 256,
    "mapping": 254,
    "page": 64,
    "region": 64,
    "rich_comparator": 16,
    "rich_equation": 256,
    "rich_equation_summary": 256,
    "rich_mapping": 254,
    "rich_page": 64,
    "rich_region": 128,
    "selected_page_json_version": 8947,
}
PINNED_AUDIT_METRICS = {
    "fallback_document_ordinals": [81, 84],
    "mapped_source_cell_count": 508,
    "old_oracle_exact_not_observed_count": 8,
    "old_oracle_exact_ready_count": 8,
}


def _json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise _error(f"JSON input is absent or not regular: {path}")
    try:
        value = json.loads(path.read_bytes())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"JSON input is invalid: {path}") from exc
    if type(value) is not dict:
        raise _error("JSON input is not one object")
    return value


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _validate_pinned_compiled_specs(compiled_specs: dict[str, Any]) -> None:
    actual = {
        name: sha256(canonical_json_bytes_v1(compiled_specs.get(name))).hexdigest()
        for name in PINNED_COMPILED_SPEC_SHA256
    }
    if actual != PINNED_COMPILED_SPEC_SHA256:
        raise _error("dual-component pinned compiled spec triplet drifted")


def _content_ref(root: Path, reference: Any) -> Path:
    if type(reference) is not dict or set(reference) != {"path", "sha256", "size_bytes"}:
        raise _error("corpus content reference fields drifted")
    relative = Path(reference["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise _error("corpus content reference escapes its artifact root")
    path = root / relative
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_size != reference["size_bytes"]
        or _sha256(path) != reference["sha256"]
    ):
        raise _error("corpus content reference does not authenticate")
    return path


_SQLITE_SIDECAR_SUFFIXES = ("-journal", "-shm", "-wal")


def _file_identity(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _assert_no_sqlite_sidecars(path: Path) -> None:
    if any(os.path.lexists(f"{path}{suffix}") for suffix in _SQLITE_SIDECAR_SUFFIXES):
        raise _error("dual-component SQLite input has a journal/WAL sidecar")


def _fd_sha256(descriptor: int) -> str:
    offset = os.lseek(descriptor, 0, os.SEEK_CUR)
    digest = sha256()
    try:
        os.lseek(descriptor, 0, os.SEEK_SET)
        while block := os.read(descriptor, 1024 * 1024):
            digest.update(block)
    finally:
        os.lseek(descriptor, offset, os.SEEK_SET)
    return digest.hexdigest()


class _AuthenticatedSqliteSnapshot:
    def __init__(
        self,
        *,
        source: Path,
        source_descriptor: int,
        source_identity: tuple[int, ...],
        snapshot: Path,
        snapshot_identity: tuple[int, ...],
        expected_sha256: str,
        expected_size_bytes: int,
    ) -> None:
        self.source = source
        self.source_descriptor = source_descriptor
        self.source_identity = source_identity
        self.path = snapshot
        self.snapshot_identity = snapshot_identity
        self.expected_sha256 = expected_sha256
        self.expected_size_bytes = expected_size_bytes

    def validate(self) -> None:
        _assert_no_sqlite_sidecars(self.source)
        _assert_no_sqlite_sidecars(self.path)
        source_fd_stat = os.fstat(self.source_descriptor)
        try:
            source_name_stat = os.stat(self.source, follow_symlinks=False)
            snapshot_stat = os.stat(self.path, follow_symlinks=False)
        except FileNotFoundError as exc:
            raise _error("dual-component authenticated SQLite path disappeared") from exc
        if (
            not stat.S_ISREG(source_name_stat.st_mode)
            or not stat.S_ISREG(snapshot_stat.st_mode)
            or _file_identity(source_fd_stat) != self.source_identity
            or _file_identity(source_name_stat) != self.source_identity
            or _file_identity(snapshot_stat) != self.snapshot_identity
            or source_fd_stat.st_size != self.expected_size_bytes
            or snapshot_stat.st_size != self.expected_size_bytes
            or _fd_sha256(self.source_descriptor) != self.expected_sha256
            or _sha256(self.path) != self.expected_sha256
        ):
            raise _error("dual-component authenticated SQLite input changed during use")


@contextmanager
def _authenticated_sqlite_snapshot(
    source: Path, *, reference: dict[str, Any]
) -> Iterator[_AuthenticatedSqliteSnapshot]:
    """Pin exact main-file bytes and exclude mutable SQLite sidecar state."""

    _assert_no_sqlite_sidecars(source)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(source, flags)
    try:
        source_stat = os.fstat(descriptor)
        named_stat = os.stat(source, follow_symlinks=False)
        source_identity = _file_identity(source_stat)
        if (
            not stat.S_ISREG(source_stat.st_mode)
            or source_identity != _file_identity(named_stat)
            or source_stat.st_size != reference["size_bytes"]
        ):
            raise _error("dual-component SQLite source identity drifted before snapshot")
        with tempfile.TemporaryDirectory(prefix="family14-authenticated-sqlite-") as directory:
            snapshot = Path(directory) / "page-store.sqlite3"
            digest = sha256()
            copied = 0
            snapshot_descriptor = os.open(snapshot, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
            try:
                with os.fdopen(snapshot_descriptor, "wb") as output:
                    os.lseek(descriptor, 0, os.SEEK_SET)
                    while block := os.read(descriptor, 1024 * 1024):
                        output.write(block)
                        digest.update(block)
                        copied += len(block)
                    output.flush()
                    os.fsync(output.fileno())
            except BaseException:
                snapshot.unlink(missing_ok=True)
                raise
            if copied != reference["size_bytes"] or digest.hexdigest() != reference["sha256"]:
                raise _error("dual-component SQLite snapshot bytes do not authenticate")
            os.chmod(snapshot, 0o444)
            snapshot_identity = _file_identity(os.stat(snapshot, follow_symlinks=False))
            guard = _AuthenticatedSqliteSnapshot(
                source=source,
                source_descriptor=descriptor,
                source_identity=source_identity,
                snapshot=snapshot,
                snapshot_identity=snapshot_identity,
                expected_sha256=reference["sha256"],
                expected_size_bytes=reference["size_bytes"],
            )
            guard.validate()
            try:
                yield guard
            finally:
                guard.validate()
    finally:
        os.close(descriptor)


def _selected_page_axis(*, index: dict[str, Any], artifact_root: Path) -> list[str]:
    version_ids = []
    for document in index["documents"]:
        manifest = _json(_content_ref(artifact_root, document["document_manifest_ref"]))
        pages = manifest.get("pages")
        if (
            manifest.get("document_manifest_id") != document["document_manifest_id"]
            or manifest.get("page_count") != document["page_count"]
            or type(pages) is not list
            or len(pages) != document["page_count"]
        ):
            raise _error("selected document manifest identity or page axis drifted")
        version_ids.extend(page.get("page_json_version_id") for page in pages)
    if (
        len(version_ids) != index["summary"]["page_count"]
        or len(version_ids) != len(set(version_ids))
        or any(type(version_id) is not str for version_id in version_ids)
    ):
        raise _error("selected corpus JSON frontier is incomplete or duplicate")
    return version_ids


def _axis_file_sha256(value: list[Any]) -> str:
    """Hash compact sorted-key UTF-8 JSON list bytes plus one final LF."""

    return sha256(canonical_json_bytes_v1(value)).hexdigest()


def _pinned_old_oracles() -> list[tuple[dict[str, Any], dict[str, Any]]]:
    result = []
    for pinned in PINNED_OLD_ORACLES:
        path = ROOT / pinned["path"]
        oracle = _json(path)
        if (
            _sha256(path) != pinned["sha256"]
            or oracle.get("format_version") != pinned["format_version"]
            or type(oracle.get("trials")) is not list
            or len(oracle["trials"]) != 8
        ):
            raise _error("pinned purchased-debt comparator oracle drifted")
        result.append(
            (
                {
                    **pinned,
                    "size_bytes": path.stat().st_size,
                },
                oracle,
            )
        )
    return result


def _mapping_coefficients(mapping: dict[str, Any]) -> dict[str, Any]:
    values = mapping.get("values")
    if (
        type(mapping.get("report_norm_id")) is not int
        or type(values) is not list
        or len(values) != 2
        or any(
            type(item) is not dict or type(item.get("coefficient")) is not int for item in values
        )
    ):
        raise _error("dual-component mapping comparator projection drifted")
    return {
        "coefficients": [item["coefficient"] for item in values],
        "report_norm_id": mapping["report_norm_id"],
    }


def _oracle_mapping_coefficients(mapping: dict[str, Any]) -> dict[str, Any]:
    values = mapping.get("source_values")
    if (
        type(mapping.get("report_norm_id")) is not int
        or type(values) is not list
        or len(values) != 2
        or any(
            type(item) is not dict or type(item.get("normalized_value")) is not int
            for item in values
        )
    ):
        raise _error("pinned purchased-debt oracle mapping projection drifted")
    return {
        "coefficients": [item["normalized_value"] for item in values],
        "report_norm_id": mapping["report_norm_id"],
    }


def _old_oracle_comparator_axis(
    *, trials: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    trial_by_source: dict[str, dict[str, Any]] = {}
    for trial in trials:
        source_sha256 = trial.get("source_sha256")
        if type(source_sha256) is not str or source_sha256 in trial_by_source:
            raise _error("sweep source-SHA comparator join axis is ambiguous")
        trial_by_source[source_sha256] = trial
    comparator = []
    rich_comparator = []
    oracle_refs = []
    joined_sources = set()
    for oracle_ref, oracle in _pinned_old_oracles():
        oracle_refs.append(oracle_ref)
        for oracle_trial in oracle["trials"]:
            source_pdf = oracle_trial.get("source_pdf")
            source_sha256 = source_pdf.get("sha256") if type(source_pdf) is dict else None
            if (
                type(source_sha256) is not str
                or source_sha256 in joined_sources
                or source_sha256 not in trial_by_source
            ):
                raise _error("pinned old-oracle source-SHA join is not unique and exhaustive")
            joined_sources.add(source_sha256)
            sweep_trial = trial_by_source[source_sha256]
            oracle_status = oracle_trial.get("status")
            old_ready = oracle_status == "VERIFIED_BY_CODEX"
            current_ready = sweep_trial.get("status") == READY
            expected_mappings = {
                mapping["report_norm_id"]: _oracle_mapping_coefficients(mapping)["coefficients"]
                for mapping in oracle_trial.get("verified_mappings", [])
            }
            candidates = sweep_trial.get("candidates")
            candidate = (
                candidates[0]
                if current_ready and type(candidates) is list and len(candidates) == 1
                else None
            )
            actual_mappings = (
                {
                    mapping["report_norm_id"]: _mapping_coefficients(mapping)["coefficients"]
                    for mapping in candidate.get("mappings", [])
                }
                if candidate is not None
                else {}
            )
            old_pages = sorted(
                {
                    value.get("page_sequence")
                    for mapping in oracle_trial.get("verified_mappings", [])
                    for value in mapping.get("source_values", [])
                }
            )
            if any(type(page) is not int or page <= 0 for page in old_pages):
                raise _error("pinned purchased-debt oracle page axis drifted")
            exact = old_ready == current_ready and (
                not old_ready
                or (
                    candidate is not None
                    and candidate.get("physical_page") in old_pages
                    and actual_mappings == expected_mappings
                )
            )
            comparator.append(
                {
                    "artifact": Path(oracle_ref["path"]).name,
                    "current_ordinal": sweep_trial["document_ordinal"],
                    "current_page": (
                        candidate.get("physical_page") if candidate is not None else None
                    ),
                    "current_status": "READY" if current_ready else "NOT_OBSERVED",
                    "exact": exact,
                    "old_pages": old_pages,
                    "old_status": "READY" if old_ready else "NOT_OBSERVED",
                    "role_ids": sorted(expected_mappings),
                    "source_sha256": source_sha256,
                }
            )
            rich_comparator.append(
                {
                    "actual_mappings": [
                        {
                            "coefficients": actual_mappings[report_norm_id],
                            "report_norm_id": report_norm_id,
                        }
                        for report_norm_id in sorted(actual_mappings)
                    ],
                    "bank_provenance": oracle_trial.get("bank_provenance"),
                    "comparison": (
                        "EXACT_PAGE_RNID_TWO_COEFFICIENT_MATCH"
                        if old_ready and exact
                        else "EXACT_NOT_OBSERVED_MATCH"
                        if exact
                        else "MISMATCH"
                    ),
                    "document_ordinal": sweep_trial["document_ordinal"],
                    "expected_mappings": [
                        {
                            "coefficients": expected_mappings[report_norm_id],
                            "report_norm_id": report_norm_id,
                        }
                        for report_norm_id in sorted(expected_mappings)
                    ],
                    "old_pages": old_pages,
                    "oracle_format_version": oracle["format_version"],
                    "oracle_status": oracle_status,
                    "physical_page": (
                        candidate.get("physical_page") if candidate is not None else None
                    ),
                    "source_sha256": source_sha256,
                    "sweep_status": sweep_trial.get("status"),
                }
            )
            if oracle_status == "VERIFIED_BY_CODEX":
                if not current_ready or candidate is None or not exact:
                    raise _error("old-oracle READY page/RNID/two-coefficient comparator differs")
            elif oracle_status == "NOT_OBSERVED_IN_BOUND_SOURCE_SCOPE":
                if (
                    sweep_trial.get("status") != NOT_OBSERVED
                    or sweep_trial.get("candidate_count") != 0
                    or sweep_trial.get("candidates") != []
                    or sweep_trial.get("mappings") != []
                ):
                    raise _error("old-oracle absence source is not NOT_OBSERVED")
            else:
                raise _error("pinned purchased-debt oracle status is undeclared")
    if (
        len(comparator) != 16
        or len(joined_sources) != 16
        or sum(item["old_status"] == "READY" for item in comparator) != 8
        or sum(item["old_status"] == "NOT_OBSERVED" for item in comparator) != 8
        or not all(item["exact"] for item in comparator)
    ):
        raise _error("old-oracle comparator denominator drifted")
    return comparator, rich_comparator, oracle_refs


def _raw_source_coefficient(*, visual_state: str, source_text: str | None) -> int:
    if visual_state not in {"BLANK", "DASH", "PRINTED_ZERO", "VALUE"}:
        raise _error("raw mapping source visual state is invalid")
    if visual_state in {"BLANK", "DASH", "PRINTED_ZERO"} or source_text is None:
        return 0
    compact = "".join(source_text.split())
    if compact in {"-", "–", "—", "_"}:
        return 0
    negative = False
    if compact.startswith("(") and compact.endswith(")"):
        negative = True
        compact = compact[1:-1]
    elif compact.startswith("-"):
        negative = True
        compact = compact[1:]
    digits = compact.replace(".", "").replace(",", "")
    if not digits.isdigit():
        raise _error("raw mapping source coefficient is not an exact integer")
    coefficient = int(digits)
    return -coefficient if negative else coefficient


def _mapping_source_axis(*, database: Path, trials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = [
        (trial, trial["candidates"][0], mapping)
        for trial in trials
        if trial["status"] == READY
        for mapping in trial["candidates"][0]["mappings"]
    ]
    component_rank = {"BALANCE": 0, "DETAIL": 1}
    records.sort(
        key=lambda item: (
            item[0]["document_ordinal"],
            component_rank[item[2]["component_role"]],
            item[2]["row_ordinal"],
        )
    )
    identities = {
        (
            mapping["locator"]["page_json_version_id"],
            mapping["locator"]["section_id"],
            mapping["locator"]["table_id"],
            mapping["row_id"],
        )
        for _trial, _candidate, mapping in records
    }
    if len(identities) != len(records):
        raise _error("raw mapping source row axis is duplicate")
    connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only=ON")
        axis = []
        for trial, candidate, mapping in records:
            locator = mapping["locator"]
            parameters = (
                locator["page_json_version_id"],
                locator["section_id"],
                locator["table_id"],
                mapping["row_id"],
            )
            row = connection.execute(
                "SELECT source_order,label_exact FROM row_node "
                "WHERE page_json_version_id=? AND section_id=? AND table_id=? "
                "AND row_id=?",
                parameters,
            ).fetchone()
            cells = connection.execute(
                "SELECT value_cell.visual_state,value_cell.source_text,"
                "column_node.column_ordinal "
                "FROM value_cell JOIN column_node "
                "USING(page_json_version_id,section_id,table_id,column_id) "
                "WHERE value_cell.page_json_version_id=? "
                "AND value_cell.section_id=? AND value_cell.table_id=? "
                "AND value_cell.row_id=? ORDER BY column_node.column_ordinal",
                parameters,
            ).fetchall()
            values = [
                {
                    "coefficient": _raw_source_coefficient(
                        visual_state=cell["visual_state"],
                        source_text=cell["source_text"],
                    ),
                    "source_text": cell["source_text"],
                    "visual_state": cell["visual_state"],
                }
                for cell in cells
            ]
            if (
                row is None
                or row["source_order"] != mapping["row_ordinal"] - 1
                or row["label_exact"] != mapping["label_exact"]
                or len(cells) != 2
                or [cell["column_ordinal"] for cell in cells] != [0, 1]
                or [value["coefficient"] for value in values]
                != [value["coefficient"] for value in mapping["values"]]
            ):
                raise _error("raw mapping source row/cell replay drifted")
            axis.append(
                {
                    "component": mapping["component_role"],
                    "label_exact": row["label_exact"],
                    "page_json_version_id": candidate["page_json_version_id"],
                    "physical_page": candidate["physical_page"],
                    "report_norm_id": mapping["report_norm_id"],
                    "row_id": mapping["row_id"],
                    "section_id": locator["section_id"],
                    "source_ordinal": trial["document_ordinal"],
                    "source_sha256": trial["source_sha256"],
                    "table_id": locator["table_id"],
                    "values": values,
                }
            )
    finally:
        connection.close()
    return axis


def build_dual_component_experimental_audit_v1(
    *,
    database: Path,
    sweep: dict[str, Any],
    sweep_output: Path,
    selected_page_json_version_ids: list[str],
    indexed_query_evidence: dict[str, Any],
    trials: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return replayable source/mapping/equation/comparator axes and digests."""

    candidate_by_ordinal = {
        trial["document_ordinal"]: trial["candidates"][0] for trial in trials if trial["candidates"]
    }
    ready_trials = [trial for trial in trials if trial["status"] == READY]
    ready_trials.sort(key=lambda trial: trial["document_ordinal"])
    page_axis = [
        {
            "page_json_version_id": trial["candidates"][0]["page_json_version_id"],
            "physical_page": trial["candidates"][0]["physical_page"],
            "source_ordinal": trial["document_ordinal"],
            "source_sha256": trial["source_sha256"],
        }
        for trial in ready_trials
    ]
    region_axis = []
    for trial in ready_trials:
        candidate = trial["candidates"][0]
        balance, detail = candidate["component_regions"]
        mappings = sorted(
            candidate["mappings"],
            key=lambda mapping: (
                {"BALANCE": 0, "DETAIL": 1}[mapping["component_role"]],
                mapping["row_ordinal"],
            ),
        )
        region_axis.append(
            {
                "balance_locator": {
                    "section_id": balance["section_id"],
                    "table_id": balance["table_id"],
                },
                "detail_locator": {
                    "section_id": detail["section_id"],
                    "table_id": detail["table_id"],
                },
                "layout": (
                    "SAME_PAGE_SAME_SECTION_TWO_TABLE"
                    if balance["section_id"] == detail["section_id"]
                    else "SAME_PAGE_CROSS_SECTION_TWO_TABLE"
                ),
                "page_json_version_id": candidate["page_json_version_id"],
                "physical_page": candidate["physical_page"],
                "report_norm_ids": [mapping["report_norm_id"] for mapping in mappings],
                "source_ordinal": trial["document_ordinal"],
                "source_sha256": trial["source_sha256"],
            }
        )
    mapping_axis = _mapping_source_axis(database=database, trials=trials)
    equation_axis = []
    for trial in ready_trials:
        candidate = trial["candidates"][0]
        equation_by_lane = {
            (equation["period_role"], equation["component_role"]): equation
            for equation in candidate["closure_receipt"]["equations"]
        }
        for period_column_ordinal, period_role in enumerate(
            ("CURRENT_PERIOD", "COMPARATIVE_PERIOD")
        ):
            for component_role in ("BALANCE", "DETAIL"):
                equation = equation_by_lane.get((period_role, component_role))
                if equation is None:
                    raise _error("exact audit equation lane is absent")
                if component_role == "BALANCE":
                    equation_name = "PURCHASE_CURRENCY_PLUS_PROVISION_EQUALS_NET"
                elif equation["result_kind"] == "UNIQUE_BALANCE_GROSS_STRUCTURAL_FALLBACK":
                    equation_name = "DETAIL_COMPONENTS_EQUALS_PURCHASE_GROSS"
                else:
                    equation_name = "DETAIL_COMPONENTS_EQUALS_VISIBLE_DETAIL_TOTAL"
                equation_axis.append(
                    {
                        "equation": equation_name,
                        "lhs": equation["component_sum"],
                        "period_column_ordinal": period_column_ordinal,
                        "physical_page": candidate["physical_page"],
                        "rhs": equation["result_coefficient"],
                        "source_ordinal": trial["document_ordinal"],
                        "status": equation["status"],
                    }
                )
    rich_page_axis = [
        {
            "document_ordinal": cluster["document_ordinal"],
            "page_json_version_id": cluster["component_regions"][0]["page_json_version_id"],
            "physical_page": cluster["component_regions"][0]["physical_page"],
        }
        for cluster in indexed_query_evidence["accepted_clusters"]
    ]
    rich_region_axis = [
        {
            "component_role": component_role,
            **region,
        }
        for cluster in indexed_query_evidence["accepted_clusters"]
        for component_role, region in zip(
            ("BALANCE", "DETAIL"), cluster["component_regions"], strict=True
        )
    ]
    rich_mapping_axis = [
        {
            "document_ordinal": ordinal,
            **mapping,
        }
        for ordinal in sorted(candidate_by_ordinal)
        for mapping in candidate_by_ordinal[ordinal]["mappings"]
    ]
    rich_equation_axis = [
        {
            "document_ordinal": ordinal,
            **equation,
        }
        for ordinal in sorted(candidate_by_ordinal)
        for equation in candidate_by_ordinal[ordinal]["closure_receipt"]["equations"]
    ]
    rich_equation_summary_axis = [
        {
            "component_role": equation["component_role"],
            "component_sum": equation["component_sum"],
            "document_ordinal": ordinal,
            "period_role": equation["period_role"],
            "result_coefficient": equation["result_coefficient"],
            "result_kind": equation["result_kind"],
            "status": equation["status"],
        }
        for ordinal in sorted(candidate_by_ordinal)
        for equation in candidate_by_ordinal[ordinal]["closure_receipt"]["equations"]
    ]
    comparator_axis, rich_comparator_axis, oracle_refs = _old_oracle_comparator_axis(trials=trials)
    axes = {
        "comparator": comparator_axis,
        "equation": equation_axis,
        "mapping": mapping_axis,
        "page": page_axis,
        "region": region_axis,
        "rich_comparator": rich_comparator_axis,
        "rich_equation": rich_equation_axis,
        "rich_equation_summary": rich_equation_summary_axis,
        "rich_mapping": rich_mapping_axis,
        "rich_page": rich_page_axis,
        "rich_region": rich_region_axis,
        "selected_page_json_version": list(selected_page_json_version_ids),
    }
    axis_field_recipes = {
        "comparator": (
            "pinned E-0066 then E-0120 trial order; artifact basename, source_sha256, "
            "current_ordinal, normalized old/current status, old_pages, current_page, "
            "sorted role_ids, exact source-SHA/page/RNID/two-coefficient comparison"
        ),
        "equation": (
            "READY source_ordinal/physical_page; CURRENT then COMPARATIVE and BALANCE "
            "then DETAIL; period_column_ordinal, declared equation name, lhs, rhs, status"
        ),
        "mapping": (
            "READY raw frozen-DB row/value/column projection sorted by source_ordinal, "
            "BALANCE then DETAIL, row source_order; raw visual_state/source_text and "
            "strict raw signed-integer coefficient per money column ordinal"
        ),
        "page": (
            "READY source_ordinal, source_sha256, physical_page, page_json_version_id "
            "sorted by source_ordinal"
        ),
        "region": (
            "one READY composed two-table cluster per source with same/cross-section "
            "layout, balance/detail section+table locators, and RNIDs sorted by "
            "BALANCE/DETAIL then source row ordinal"
        ),
        "rich_comparator": "full pinned-oracle/current comparison evidence",
        "rich_equation": "source document_ordinal plus exact closure equation object",
        "rich_equation_summary": (
            "document_ordinal, component_role, period_role, component_sum, "
            "result_coefficient, result_kind, status"
        ),
        "rich_mapping": "source document_ordinal plus exact candidate mapping object",
        "rich_page": "accepted cluster document_ordinal/version/physical page",
        "rich_region": "component_role plus exact accepted component region locator",
        "selected_page_json_version": "ordered selected frontier page_json_version_id",
    }
    axis_sha256 = {name: _axis_file_sha256(axis) for name, axis in axes.items()}
    exact_preflight_sha256 = {name: axis_sha256[name] for name in PINNED_PREFLIGHT_AXIS_SHA256}
    if exact_preflight_sha256 != PINNED_PREFLIGHT_AXIS_SHA256:
        raise _error("dual-component exact preflight audit axis drifted")
    if axis_sha256["selected_page_json_version"] != PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256:
        raise _error("dual-component selected JSON frontier audit axis drifted")
    sweep_payload = canonical_json_bytes_v1(sweep)
    material = {
        "axes": axes,
        "axis_counts": {name: len(axis) for name, axis in axes.items()},
        "axis_field_recipes": axis_field_recipes,
        "axis_sha256": axis_sha256,
        "claim_boundary": (
            "EXPERIMENTAL_LOCAL_PINNED_JSON_CORPUS_AND_OLD_ORACLE_COMPARISON_ONLY_"
            "NO_PROVIDER_NO_OFFICIAL_NO_EXPORT_AUTHORITY"
        ),
        "format_version": AUDIT_FORMAT_VERSION,
        "metrics": {
            "fallback_document_ordinals": sorted(
                ordinal
                for ordinal, candidate in candidate_by_ordinal.items()
                if candidate["closure_receipt"]["fallback_used"]
            ),
            "mapped_source_cell_count": sum(len(mapping["values"]) for mapping in mapping_axis),
            "old_oracle_exact_not_observed_count": sum(
                item["old_status"] == "NOT_OBSERVED" and item["exact"] for item in comparator_axis
            ),
            "old_oracle_exact_ready_count": sum(
                item["old_status"] == "READY" and item["exact"] for item in comparator_axis
            ),
        },
        "pinned_preflight_axis_sha256": PINNED_PREFLIGHT_AXIS_SHA256,
        "pinned_selected_page_json_frontier_sha256": (PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256),
        "pinned_old_oracle_refs": oracle_refs,
        "query_evidence_id": indexed_query_evidence["query_evidence_id"],
        "serialization": "COMPACT_SORTED_KEY_UTF8_JSON_LIST_PLUS_LF",
        "state": "EXPERIMENTAL_AUDIT_COMPLETE",
        "sweep_ref": {
            "path": sweep_output.name,
            "sha256": sha256(sweep_payload).hexdigest(),
            "size_bytes": len(sweep_payload),
            "sweep_id": sweep["sweep_id"],
        },
    }
    return {
        **material,
        "audit_id": "gjdceav1:audit:" + sha256(canonical_json_bytes_v1(material)).hexdigest(),
    }


def validate_dual_component_experimental_audit_replay_v1(
    value: Any,
    *,
    compiled_specs: dict[str, Any],
    database: Path,
    sweep: dict[str, Any],
    sweep_output: Path,
    selected_page_json_version_ids: list[str],
    indexed_query_evidence: dict[str, Any],
    trials: list[dict[str, Any]],
) -> dict[str, Any]:
    """Rebuild the complete persisted audit and reject any changed byte axis."""

    checked_sweep = validate_gemini_json_flat_family_sweep_v1(sweep)
    embedded_compiled_specs = compile_gemini_json_flat_family_specs_v1(
        checked_sweep["specs"]["topology"]["value"],
        checked_sweep["specs"]["evaluation"]["value"],
        checked_sweep["specs"]["schema_binding"]["value"],
    )
    _validate_pinned_compiled_specs(embedded_compiled_specs)
    if not same_typed_json_v1(compiled_specs, embedded_compiled_specs):
        raise _error("dual-component caller/sweep compiled spec triplet drifted")
    validate_dual_component_experimental_audit_content_v1(value)
    if not same_typed_json_v1(checked_sweep["trials"], trials) or not same_typed_json_v1(
        checked_sweep.get("indexed_query_evidence"), indexed_query_evidence
    ):
        raise _error("dual-component audit query/trial/sweep axis drifted")
    validate_selected_dual_component_family_candidate_replays_v1(
        database,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=embedded_compiled_specs,
        indexed_query_evidence=checked_sweep["indexed_query_evidence"],
        trials=checked_sweep["trials"],
    )
    expected = build_dual_component_experimental_audit_v1(
        database=database,
        sweep=checked_sweep,
        sweep_output=sweep_output,
        selected_page_json_version_ids=selected_page_json_version_ids,
        indexed_query_evidence=checked_sweep["indexed_query_evidence"],
        trials=checked_sweep["trials"],
    )
    if type(value) is not dict or not same_typed_json_v1(value, expected):
        raise _error("dual-component experimental audit does not replay exactly")
    return expected


def validate_dual_component_experimental_audit_content_v1(
    value: Any,
) -> dict[str, Any]:
    """Recompute every persisted axis digest, pin, count, and audit identity."""

    fields = {
        "audit_id",
        "axes",
        "axis_counts",
        "axis_field_recipes",
        "axis_sha256",
        "claim_boundary",
        "format_version",
        "metrics",
        "pinned_old_oracle_refs",
        "pinned_preflight_axis_sha256",
        "pinned_selected_page_json_frontier_sha256",
        "query_evidence_id",
        "serialization",
        "state",
        "sweep_ref",
    }
    expected_axis_counts = PINNED_AUDIT_AXIS_COUNTS
    if (
        type(value) is not dict
        or set(value) != fields
        or value.get("format_version") != AUDIT_FORMAT_VERSION
        or value.get("serialization") != "COMPACT_SORTED_KEY_UTF8_JSON_LIST_PLUS_LF"
        or value.get("state") != "EXPERIMENTAL_AUDIT_COMPLETE"
        or type(value.get("axes")) is not dict
        or set(value["axes"]) != set(expected_axis_counts)
        or any(type(axis) is not list for axis in value["axes"].values())
        or type(value.get("axis_field_recipes")) is not dict
        or set(value["axis_field_recipes"]) != set(expected_axis_counts)
        or any(
            type(recipe) is not str or not recipe for recipe in value["axis_field_recipes"].values()
        )
    ):
        raise _error("dual-component experimental audit shape drifted")
    actual_counts = {name: len(axis) for name, axis in value["axes"].items()}
    actual_sha256 = {name: _axis_file_sha256(axis) for name, axis in value["axes"].items()}
    if (
        value.get("axis_counts") != expected_axis_counts
        or actual_counts != expected_axis_counts
        or value.get("axis_sha256") != actual_sha256
        or value.get("pinned_preflight_axis_sha256") != PINNED_PREFLIGHT_AXIS_SHA256
        or {name: actual_sha256[name] for name in PINNED_PREFLIGHT_AXIS_SHA256}
        != PINNED_PREFLIGHT_AXIS_SHA256
        or value.get("pinned_selected_page_json_frontier_sha256")
        != PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256
        or actual_sha256["selected_page_json_version"] != PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256
    ):
        raise _error("dual-component experimental audit count/hash pin drifted")
    metrics = value.get("metrics")
    if metrics != PINNED_AUDIT_METRICS:
        raise _error("dual-component experimental audit metric pin drifted")
    expected_oracle_refs = [reference for reference, _oracle in _pinned_old_oracles()]
    sweep_ref = value.get("sweep_ref")
    if (
        value.get("pinned_old_oracle_refs") != expected_oracle_refs
        or type(value.get("query_evidence_id")) is not str
        or not value["query_evidence_id"].startswith("gjfidcqev1:evidence:")
        or type(sweep_ref) is not dict
        or set(sweep_ref) != {"path", "sha256", "size_bytes", "sweep_id"}
        or type(sweep_ref.get("path")) is not str
        or not sweep_ref["path"]
        or type(sweep_ref.get("sha256")) is not str
        or len(sweep_ref["sha256"]) != 64
        or type(sweep_ref.get("size_bytes")) is not int
        or sweep_ref["size_bytes"] <= 0
        or type(sweep_ref.get("sweep_id")) is not str
        or not sweep_ref["sweep_id"].startswith("gjfafsv1:sweep:")
    ):
        raise _error("dual-component experimental audit input binding drifted")
    material = {key: value[key] for key in fields - {"audit_id"}}
    expected_id = "gjdceav1:audit:" + sha256(canonical_json_bytes_v1(material)).hexdigest()
    if value.get("audit_id") != expected_id:
        raise _error("dual-component experimental audit identity drifted")
    return json.loads(canonical_json_bytes_v1(value))


def _write_once(path: Path, value: dict[str, Any]) -> None:
    payload = canonical_json_bytes_v1(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
            raise _error("dual-component experimental output exists with different bytes")
        return
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-index", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--topology-spec", type=Path, required=True)
    parser.add_argument("--evaluation-spec", type=Path, required=True)
    parser.add_argument("--schema-binding-spec", type=Path, required=True)
    parser.add_argument("--run-kind", choices=("EXPERIMENTAL",), required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def _run_with_authenticated_database(
    args: argparse.Namespace,
    *,
    index: dict[str, Any],
    database_guard: _AuthenticatedSqliteSnapshot,
    selected_ids: list[str],
    topology: dict[str, Any],
    evaluation: dict[str, Any],
    schema: dict[str, Any],
    compiled: dict[str, Any],
) -> dict[str, Any]:
    database = database_guard.path
    indexed = query_selected_dual_component_family_regions_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
    )
    validate_selected_dual_component_family_query_evidence_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
        indexed_query_evidence=indexed,
    )
    candidate_version_ids = list(
        dict.fromkeys(
            region["page_json_version_id"]
            for cluster in indexed["accepted_clusters"]
            for region in cluster["component_regions"]
        )
    )
    loaded = load_page_json_versions_v1(database, page_json_version_ids=candidate_version_ids)
    page_json_by_version = {
        record["page_json_version_id"]: record["page_json"] for record in loaded
    }
    candidates_by_ordinal = {}
    for cluster in indexed["accepted_clusters"]:
        regions = cluster["component_regions"]
        candidate = evaluate_gemini_json_dual_component_family_cluster_v1(
            regions=regions,
            page_json_by_version=page_json_by_version,
            compiled_specs=compiled,
            query_receipt=build_gemini_json_dual_component_region_query_receipt_v1(regions),
        )
        candidates_by_ordinal[cluster["document_ordinal"]] = candidate
    trials = []
    for document, disposition in zip(
        indexed["selected_document_axis"],
        indexed["candidate_dispositions"],
        strict=True,
    ):
        ordinal = document["document_ordinal"]
        candidate = candidates_by_ordinal.get(ordinal)
        if candidate is not None and candidate["status"] == READY:
            status = READY
            reasons = []
            mappings = candidate["mappings"]
            selected_candidate_id = candidate["candidate_id"]
        elif candidate is not None:
            status = UNRESOLVED
            reasons = candidate["reasons"]
            mappings = []
            selected_candidate_id = None
        elif disposition["disposition"] == "NOT_OBSERVED":
            status = NOT_OBSERVED
            reasons = []
            mappings = []
            selected_candidate_id = None
        else:
            status = UNRESOLVED
            reasons = disposition["reason_codes"]
            mappings = []
            selected_candidate_id = None
        trials.append(
            {
                "candidate_count": int(candidate is not None),
                "candidates": [] if candidate is None else [candidate],
                "document_ordinal": ordinal,
                "mappings": mappings,
                "reasons": reasons,
                "selected_candidate_id": selected_candidate_id,
                "source_logical_name": document["source_logical_name"],
                "source_sha256": document["source_sha256"],
                "status": status,
            }
        )
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id=index["corpus_manifest_index_id"],
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=trials,
        indexed_query_evidence=indexed,
    )
    validate_gemini_json_flat_family_sweep_v1(sweep)
    validate_selected_dual_component_family_candidate_replays_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
        indexed_query_evidence=indexed,
        trials=trials,
    )
    audit = build_dual_component_experimental_audit_v1(
        database=database,
        sweep=sweep,
        sweep_output=args.output,
        selected_page_json_version_ids=selected_ids,
        indexed_query_evidence=indexed,
        trials=trials,
    )
    validate_dual_component_experimental_audit_replay_v1(
        audit,
        compiled_specs=compiled,
        database=database,
        sweep=sweep,
        sweep_output=args.output,
        selected_page_json_version_ids=selected_ids,
        indexed_query_evidence=indexed,
        trials=trials,
    )
    audit_output = args.output.with_suffix(".audit.json")
    database_guard.validate()
    _write_once(args.output, sweep)
    _write_once(audit_output, audit)
    return {
        "audit_id": audit["audit_id"],
        "audit_output": str(audit_output),
        "axis_counts": audit["axis_counts"],
        "axis_sha256": audit["axis_sha256"],
        "disposition": "SUCCEEDED",
        "metrics": sweep["metrics"],
        "output": str(args.output),
        "run_kind": "EXPERIMENTAL",
        "sweep_id": sweep["sweep_id"],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Evaluate locally selected JSON only; no provider or OFFICIAL path exists."""

    if args.run_kind != "EXPERIMENTAL":
        raise _error("dual-component runner is EXPERIMENTAL-only")
    index = validate_current_corpus_manifest_index_v1(_json(args.corpus_index))
    artifact_root = args.artifact_root.resolve()
    source_database = _content_ref(artifact_root, index["database_ref"])
    selected_ids = _selected_page_axis(index=index, artifact_root=artifact_root)
    topology = _json(args.topology_spec)
    evaluation = _json(args.evaluation_spec)
    schema = _json(args.schema_binding_spec)
    compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
    _validate_pinned_compiled_specs(compiled)
    with _authenticated_sqlite_snapshot(
        source_database, reference=index["database_ref"]
    ) as database_guard:
        return _run_with_authenticated_database(
            args,
            index=index,
            database_guard=database_guard,
            selected_ids=selected_ids,
            topology=topology,
            evaluation=evaluation,
            schema=schema,
            compiled=compiled,
        )


def main() -> int:
    print(json.dumps(run(_parser().parse_args()), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
