"""Bounded F36 streamed-store to canonical workbooks; EXPERIMENTAL only.

Every original document, including unresolved slots, is projected separately.
Files are unpublished staging until the final receipt exists. No SQL export or
selection is registered. The T8 reader's mandatory exit verification precedes
both the external manifest and the final publication receipt.
"""
from __future__ import annotations

import os
import stat
from hashlib import sha256
from pathlib import Path
from typing import Any

# Import the complete projector dependency graph before importing/opening T8.
from bctc_ai.notes.export_v1 import TM_TEMPLATE, TM_TEMPLATE_SHA256, tm_template_rows_v1
from bctc_ai.notes.f36_canonical_workbook_v1 import (
    PRODUCT_LABEL,
    build_f36_canonical_workbook_v1,
)

# isort: split

from bctc_ai.evaluation.gemini_json_f36_notes_stream_store_v1 import (
    open_f36_notes_streamed_run_v1,
)
from bctc_ai.evaluation.gemini_json_f36_notes_stream_v1 import (
    derive_f36_notes_proposed_run_id_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.storage.gemini_accounting_family_store_v1 import FORMAT_VERSION as STORE_FORMAT

FORMAT = "F36_STREAMED_CANONICAL_WORKBOOK_PUBLICATION_V1"
ROOT = Path(__file__).resolve().parents[3]


class F36StreamedWorkbookError(ValueError):
    """No complete authenticated workbook publication is available."""


def _need(ok: bool, message: str) -> None:
    if not ok:
        raise F36StreamedWorkbookError(message)


def _identity(value: os.stat_result) -> tuple[int, ...]:
    return (value.st_dev, value.st_ino, value.st_mode, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def _ref(path: Path) -> dict[str, Any]:
    """Chunked byte/identity observation; never load a whole SQLite BLOB/file."""
    path = path.absolute()
    _need(path.resolve(strict=True) == path and stat.S_ISREG(path.lstat().st_mode), "regular non-symlink file required")
    digest = sha256()
    with path.open("rb") as handle:
        before = os.fstat(handle.fileno())
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
        _need(_identity(before) == _identity(os.fstat(handle.fileno())) == _identity(path.lstat()),
              "file changed during hash observation")
    return {"path": str(path), "sha256": digest.hexdigest(), "size_bytes": before.st_size}


def _write(path: Path, raw: bytes, owned: list[Path]) -> dict[str, Any]:
    # Append only after exclusive open succeeds: cleanup cannot delete a prior file.
    with path.open("xb") as handle:
        owned.append(path)
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    return {"path": str(path), "sha256": sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _relative(ref: dict[str, Any], root: Path) -> dict[str, Any]:
    return {**ref, "path": Path(ref["path"]).relative_to(root).as_posix()}


def export_f36_streamed_canonical_workbooks_v1(*, store_ref: dict[str, Any], output_directory: Path,
        spool_report: dict[str, Any], compiled_specs: dict[str, Any],
        implementation_refs: list[dict[str, Any]], producer_refs: list[dict[str, Any]]) -> dict[str, Any]:
    """Project every original slot through the public checked T8 reader.

    The caller supplies the real current complete producer axis, as for T8.
    This API does not bypass changed package/code guards for historical stores.
    Output must be fresh. On failure, remove only files/directories created by
    this invocation; never remove an existing destination or SQL/source artifact.
    One trial/workbook is resident at a time, not a measured full-corpus RAM claim.
    """
    controls = canonical_clone_v1({"store_ref": store_ref, "spool_report": spool_report,
        "compiled_specs": compiled_specs, "implementation_refs": implementation_refs, "producer_refs": producer_refs})
    store_ref = controls["store_ref"]
    spool_report, compiled_specs = controls["spool_report"], controls["compiled_specs"]
    implementation_refs, producer_refs = controls["implementation_refs"], controls["producer_refs"]
    _need(set(store_ref) == {"path", "sha256", "size_bytes"}, "exact store byte reference required")
    store = Path(store_ref["path"])
    _need(_ref(store) == store_ref, "store reference differs")
    source = compiled_specs["topology"]["source"]
    axis = source["document_axis"]
    _need(type(axis) is list and bool(axis)
          and [d["document_ordinal"] for d in axis] == list(range(1, len(axis) + 1)), "complete original document axis required")
    template_path = ROOT / TM_TEMPLATE
    template_ref = _ref(template_path)
    _need(template_ref["sha256"] == TM_TEMPLATE_SHA256, "pinned template differs")
    template = tm_template_rows_v1(ROOT)
    bridge_ref = _ref(Path(__file__).absolute())
    run_id = derive_f36_notes_proposed_run_id_v1(corpus_index_sha256=source["index_ref"]["sha256"],
        implementation_refs=implementation_refs, sweep_id=spool_report["sweep_id"],
        sweep_sha256=spool_report["sweep_ref"]["sha256"])
    bindings = {"store_ref": store_ref, "store_format_version": STORE_FORMAT, "family_run_id": run_id,
        "sweep_id": spool_report["sweep_id"], "sweep_ref": spool_report["sweep_ref"],
        "trial_array_ref": spool_report["trial_array_ref"], "spool_report_sha256": canonical_json_sha256_v1(spool_report),
        "compiled_specs_sha256": canonical_json_sha256_v1(compiled_specs),
        "compiled_document_axis_sha256": canonical_json_sha256_v1(axis), "document_count": len(axis),
        "source_index_ref": source["index_ref"], "source_database_ref": source["database_ref"],
        "corpus_identity": source["corpus_identity"], "schema_binding_sha256": canonical_json_sha256_v1(compiled_specs["schema"]),
        "implementation_refs": sorted(implementation_refs, key=lambda ref: ref["path"]),
        "producer_refs": sorted(producer_refs, key=lambda ref: ref["path"]),
        "template_ref": template_ref, "bridge_ref": bridge_ref}
    workbook_pins = {"family_run_id": run_id, "store_sha256": store_ref["sha256"],
        "bindings_sha256": canonical_json_sha256_v1(bindings), "product_label": PRODUCT_LABEL}
    output = Path(output_directory).absolute()
    _need(output.parent.resolve(strict=True) == output.parent, "existing non-symlink output parent required")
    _need(not output.is_relative_to(ROOT), "publication must be external to the project clone")
    # Creating the root is exclusive; a pre-existing destination is never cleaned.
    output.mkdir()
    owned: list[Path] = []
    directories = [output]
    records = []
    try:
        staging = output / "staged-workbooks"
        staging.mkdir()
        directories.append(staging)
        with open_f36_notes_streamed_run_v1(store, spool_report=spool_report, compiled_specs=compiled_specs,
                implementation_refs=implementation_refs, producer_refs=producer_refs) as reader:
            for ordinal, document_axis in enumerate(axis, 1):
                trial = reader.original_trial(ordinal)
                _need(trial["document_ordinal"] == ordinal
                      and trial["source_logical_name"] == document_axis["source_logical_name"]
                      and trial["source_sha256"] == document_axis["source_sha256"], "original document binding differs")
                trial_sha = canonical_json_sha256_v1(trial)
                _need(trial_sha == spool_report["trial_offsets"][ordinal - 1]["trial_one_lf_sha256"],
                      "original trial one-LF byte binding differs")
                document = document_axis["document_identity"]
                payload, readback = build_f36_canonical_workbook_v1(document, trial, template, workbook_pins)
                workbook_ref = _write(staging / f"document-{ordinal:06d}.xlsx", payload, owned)
                _need(workbook_ref["sha256"] == readback["workbook_sha256"]
                      and workbook_ref["size_bytes"] == readback["workbook_size_bytes"], "workbook readback byte binding differs")
                audit = {"format_version": FORMAT, "product_label": PRODUCT_LABEL, "financial_acceptance": False,
                    "document_axis": document_axis, "trial_status": trial["status"], "trial_reasons": trial["reasons"],
                    "trial_one_lf_sha256": trial_sha, "mapping_count": len(trial["mappings"]),
                    "retained_count": len(trial["notes_ledger"]["retained"]),
                    "workbook_ref": _relative(workbook_ref, output), "readback": readback,
                    "bindings_sha256": workbook_pins["bindings_sha256"]}
                audit_ref = _write(staging / f"document-{ordinal:06d}.audit.json", canonical_json_bytes_v1(audit), owned)
                records.append({"document_ordinal": ordinal, "trial_status": trial["status"],
                    "trial_reasons": trial["reasons"], "mapping_count": audit["mapping_count"],
                    "workbook_ref": audit["workbook_ref"], "audit_ref": _relative(audit_ref, output)})
                del trial, payload, readback, audit
        # T8's full late store/source/code checks have now returned successfully.
        _need(_ref(store) == store_ref and _ref(template_path) == template_ref
              and _ref(Path(__file__).absolute()) == bridge_ref, "late store/template/bridge reference differs")
        _need(len(records) == len(axis), "original document publication coverage differs")
        for record in records:
            for field in ("workbook_ref", "audit_ref"):
                ref = record[field]
                _need(_relative(_ref(output / ref["path"]), output) == ref, "staged output changed before publication")
        manifest = {"format_version": FORMAT, "product_label": PRODUCT_LABEL,
            "status": "COMPLETE_ORIGINAL_AXIS_EXPERIMENTAL_PROJECTION", "financial_acceptance": False,
            "legacy_comparison": "NOT_SUPPLIED", "sqlite_export_rows_written": 0, "official_selection_mutated": False,
            "bindings": bindings, "documents": records}
        manifest_ref = _write(output / "manifest.json", canonical_json_bytes_v1(manifest), owned)
        receipt = {"format_version": FORMAT, "product_label": PRODUCT_LABEL, "status": "PASS_EXTERNAL_PUBLICATION",
            "financial_acceptance": False, "reader_exit_verification": "COMPLETED_BEFORE_PUBLICATION",
            "manifest_ref": _relative(manifest_ref, output), "bindings_sha256": workbook_pins["bindings_sha256"],
            "document_count": len(records), "ready_count": sum(r["trial_status"] == "READY" for r in records),
            "unresolved_count": sum(r["trial_status"] == "UNRESOLVED" for r in records)}
        receipt_ref = _write(output / "receipt.json", canonical_json_bytes_v1(receipt), owned)
        return {**receipt, "publication_directory": str(output), "receipt_ref": _relative(receipt_ref, output)}
    except BaseException:
        # No recursive cleanup and no deletion of caller-owned/pre-existing files.
        for path in reversed(owned):
            path.unlink(missing_ok=True)
        for directory in reversed(directories):
            directory.rmdir()
        raise
