"""Read-only canonical-store bridge for the ordinary MULTITABLE source grammar.

No family/store selection is changed. Unsupported transformations or period
proofs stop the entire requested document before creating an output directory.
An OFFICIAL historical row is not a waiver of the current source-state rules.
"""

from __future__ import annotations

import inspect
import json
import re
import sqlite3
from contextlib import closing
from datetime import date
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    _money,
    compile_gemini_json_flat_family_specs_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    ENGINE_FORMAT_VERSION,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    validate_source_observation_mapping_contract_v1,
)
from bctc_ai.export.gemini_projected_tm_workbook_v1 import (
    CODEC,
    LABEL,
    SUPPORTED_STATES,
    TM_TEMPLATE_SHA256,
    json_bytes,
    render_projected_tm_workbook_v1,
    require,
    template_rows_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from bctc_ai.storage.gemini_accounting_family_store_v1 import (
    _selected_corpus_page_frontier_v1,
    load_gemini_accounting_family_sweep_v1,
)
from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import (
    validate_current_corpus_manifest_index_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (
    load_page_json_versions_v1,
    validate_selected_multitable_hierarchical_family_candidate_replays_v1,
)

FORMAT = "GEMINI_TM_MULTITABLE_STORE_BRIDGE_V1"
MAX_SWEEP_BYTES = 256 * 1024 * 1024
MAX_DOCUMENT_PROJECTION_BYTES = 32 * 1024 * 1024
_SHA = re.compile(r"[0-9a-f]{64}")
_REQUEST_FIELDS = {
    "store_ref", "family_run_id", "corpus_index_ref", "source_page_database_ref",
    "corpus_artifact_root", "effective_page_artifact_root", "source_pdf_root",
    "producer_root", "producer_refs", "document_ordinal", "expected_family_id",
    "expected_run_kind", "require_current_selection", "template_ref", "output_dir",
}


def strict_json_v1(payload: bytes) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    def bad_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON token: {value}")

    return json.loads(payload, object_pairs_hook=pairs, parse_constant=bad_constant)


def regular_path_v1(path: Path) -> Path:
    require(path.is_absolute(), "authority paths must be absolute")
    for parent in [path, *path.parents]:
        require(not parent.is_symlink() and not getattr(parent, "is_junction", lambda: False)(),
                "authority path crosses a symlink/junction")
    require(path.is_file(), f"authority file absent: {path}")
    return path.resolve()


def file_ref_v1(path: Path) -> dict[str, Any]:
    path = regular_path_v1(path)
    before = path.stat()
    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
            "authority file changed during hashing")
    return {"path": str(path), "sha256": digest.hexdigest(), "size_bytes": after.st_size}


def authenticate_ref_v1(reference: dict[str, Any]) -> dict[str, Any]:
    require(type(reference) is dict and set(reference) == {"path", "sha256", "size_bytes"},
            "reference requires exact path/hash/size fields")
    require(type(reference["path"]) is str and type(reference["sha256"]) is str
            and _SHA.fullmatch(reference["sha256"]) is not None
            and type(reference["size_bytes"]) is int and reference["size_bytes"] > 0,
            "invalid pinned reference")
    actual = file_ref_v1(Path(reference["path"]))
    require(actual["sha256"] == reference["sha256"]
            and actual["size_bytes"] == reference["size_bytes"],
            f"authority SHA/byte mismatch: {reference['path']}")
    return actual


def pinned_bytes_v1(reference: dict[str, Any]) -> bytes:
    actual = authenticate_ref_v1(reference)
    payload = Path(actual["path"]).read_bytes()
    require(len(payload) == actual["size_bytes"] and sha256(payload).hexdigest() == actual["sha256"],
            "authority bytes changed while reading")
    return payload


def assert_sealed_sqlite_snapshot_v1(path: Path) -> None:
    """Reject sidecars before use and again after replay/render callbacks."""
    regular_path_v1(path)
    for suffix in ("-wal", "-shm", "-journal"):
        require(not Path(str(path) + suffix).exists(), "SQLite must be a sealed snapshot without sidecars")


def _ro(path: Path) -> sqlite3.Connection:
    assert_sealed_sqlite_snapshot_v1(path)
    connection = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    return connection


def _check_trace_rows_v1(connection: sqlite3.Connection, run_id: str, sweep: dict[str, Any]) -> None:
    """Join every persisted trace row to the already revalidated sweep by ordinal."""
    trials = connection.execute(
        "SELECT * FROM family_trial WHERE family_run_id=? ORDER BY document_ordinal", (run_id,)
    ).fetchall()
    require(len(trials) == len(sweep["trials"]), "persisted trial axis incomplete")
    for row, trial in zip(trials, sweep["trials"], strict=True):
        payload = json_bytes(trial)
        require(bytes(row["trial_bytes"]) == payload
                and row["trial_sha256"] == sha256(payload).hexdigest(), "persisted trial bytes drift")
        for key in ("document_ordinal", "source_logical_name", "source_sha256", "status",
                    "selected_candidate_id"):
            require(row[key] == trial[key], f"persisted trial field drift: {key}")
        require(row["candidate_count"] == len(trial["candidates"])
                and row["mapping_count"] == len(trial["mappings"])
                and bytes(row["reasons_json"]) == json_bytes(trial["reasons"]), "trial trace counts drift")
        ordinal = trial["document_ordinal"]
        for table, kind, items in (("family_mapping", "mapping", trial["mappings"]),
                                   ("family_candidate", "candidate", trial["candidates"])):
            order = "mapping_ordinal" if kind == "mapping" else "candidate_id"
            rows = connection.execute(
                f"SELECT * FROM {table} WHERE family_run_id=? AND document_ordinal=? ORDER BY {order}",
                (run_id, ordinal),
            ).fetchall()
            expected = items if kind == "mapping" else sorted(items, key=lambda item: item["candidate_id"])
            require(len(rows) == len(expected), f"persisted {kind} axis incomplete")
            for n, (stored, item) in enumerate(zip(rows, expected, strict=True), 1):
                raw = json_bytes(item)
                require(bytes(stored[f"{kind}_bytes"]) == raw
                        and stored[f"{kind}_sha256"] == sha256(raw).hexdigest(), f"{kind} trace drift")
                fields = ("report_norm_id", "role", "row_id") if kind == "mapping" else (
                    "candidate_id", "page_json_version_id", "physical_page", "section_id", "table_id", "status")
                require(all(stored[key] == item[key] for key in fields), f"{kind} projection drift")
                if kind == "mapping":
                    require(stored["mapping_ordinal"] == n, "mapping ordinal drift")
                else:
                    require(stored["mapping_count"] == len(item["mappings"])
                            and stored["reason_count"] == len(item["reasons"]), "candidate counts drift")
    for table in ("family_trial", "family_mapping", "family_candidate"):
        require(connection.execute(
            f"SELECT COUNT(*) FROM {table} WHERE family_run_id=? AND document_ordinal NOT BETWEEN 1 AND ?",
            (run_id, len(trials)),
        ).fetchone()[0] == 0, "orphan document ordinal")


def reject_legacy_imputation_v1(value: Any) -> None:
    if type(value) is dict:
        state = value.get("state")
        if type(state) is str:
            require(not ("BLANK_ZERO" in state or "ONE_UNKNOWN" in state
                         or "BACKSOLV" in state or "IMPUT" in state),
                    f"legacy imputed/backsolved state is prohibited: {state}")
        for item in value.values():
            reject_legacy_imputation_v1(item)
    elif type(value) is list:
        for item in value:
            reject_legacy_imputation_v1(item)


def _producer_files_v1(request: dict[str, Any], stored: list[dict[str, Any]]) -> list[dict[str, Any]]:
    require(request["producer_refs"] == stored and bool(stored), "producer axis differs from SQLite run")
    root = Path(request["producer_root"]).resolve()
    actuals, by_path = [], {}
    for reference in stored:
        path = Path(reference["path"])
        path = path if path.is_absolute() else root / path
        actual = authenticate_ref_v1({**reference, "path": str(path)})
        require(str(path.resolve()) not in by_path, "duplicate runtime producer path")
        actuals.append(actual)
        by_path[str(path.resolve())] = actual
    # Authenticate loaded callable origins, not a supplied Git HEAD string.
    for function in (load_gemini_accounting_family_sweep_v1,
                     compile_gemini_json_flat_family_specs_v1,
                     evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
                     validate_selected_multitable_hierarchical_family_candidate_replays_v1):
        source = inspect.getsourcefile(function)
        require(source is not None and str(Path(source).resolve()) in by_path,
                f"loaded runtime producer is not in pinned run axis: {function.__name__}")
        authenticate_ref_v1(by_path[str(Path(source).resolve())])
    return actuals


def _authenticate_multitable_store_run_v1(
    request: dict[str, Any], *, replay_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Revalidate read-only run, persisted traces, selected corpus and source replay.

    This does not create a new store or assert the family's PDF residual audits.
    Existing loader/replay materializes one bounded sweep, up to 256 MiB.
    """
    require(type(request) is dict, "request must be a JSON object")
    request = strict_json_v1(json_bytes(request))
    require(set(request) == _REQUEST_FIELDS, "request fields drift")
    require(type(request["document_ordinal"]) is int and request["document_ordinal"] > 0,
            "document ordinal must be the global positive integer")
    require(type(request["require_current_selection"]) is bool, "selection policy must be explicit")
    require(request["expected_run_kind"] in {"OFFICIAL", "EXPERIMENTAL"}, "run kind policy missing")
    refs = {key: authenticate_ref_v1(request[key]) for key in
            ("store_ref", "corpus_index_ref", "source_page_database_ref", "template_ref")}
    require(refs["template_ref"]["sha256"] == TM_TEMPLATE_SHA256, "wrong template authority")
    store = Path(refs["store_ref"]["path"])
    run_id = request["family_run_id"]
    with closing(_ro(store)) as connection:
        require([row[0] for row in connection.execute("PRAGMA quick_check")] == ["ok"], "SQLite quick_check failed")
        require(connection.execute("PRAGMA foreign_key_check").fetchone() is None, "SQLite foreign key violation")
        identity = connection.execute("SELECT * FROM store_identity").fetchall()
        require(len(identity) == 1 and identity[0]["format_version"] == "GEMINI_ACCOUNTING_FAMILY_STORE_V1",
                "unsupported store codec")
        columns = (
            "family_run_id,sweep_id,family_id,sweep_format_version,corpus_manifest_index_id,"
            "corpus_index_sha256,topology_spec_sha256,evaluation_spec_sha256,"
            "schema_binding_spec_sha256,implementation_axis_sha256,implementation_refs_json,"
            "sweep_sha256,document_count,ready_count,not_observed_count,unresolved_count,mapping_count"
        )
        run = connection.execute(f"SELECT {columns} FROM family_run WHERE family_run_id=?", (run_id,)).fetchone()
        require(run is not None, "family run absent")
        require(run["sweep_format_version"] == ENGINE_FORMAT_VERSION, "unsupported family codec")
        require(run["family_id"] == request["expected_family_id"], "family identity mismatch")
        require(connection.execute(
            "SELECT 1 FROM family_run_execution WHERE family_run_id=? AND run_kind=?", (run_id, request["expected_run_kind"])
        ).fetchone() is not None, "requested run kind was not persisted")
        if request["require_current_selection"]:
            selected = connection.execute("SELECT family_run_id FROM family_current_selection WHERE family_id=?", (run["family_id"],)).fetchone()
            require(selected is not None and selected[0] == run_id, "run is not the selected family run")
        size = connection.execute("SELECT length(sweep_bytes) FROM family_run WHERE family_run_id=?", (run_id,)).fetchone()[0]
        require(type(size) is int and 0 < size <= MAX_SWEEP_BYTES, "sweep exceeds bounded V1 loader")
        producer_refs = strict_json_v1(bytes(run["implementation_refs_json"]))
        require(type(producer_refs) is list and producer_refs == sorted(producer_refs, key=lambda item: item["path"]), "producer axis order drift")
        require(sha256(json_bytes(producer_refs)).hexdigest() == run["implementation_axis_sha256"], "producer axis hash drift")
        producer_files = _producer_files_v1(request, producer_refs)
        if replay_profile is not None:
            from bctc_ai.export.gemini_tm_family_replay_profiles_v2 import (
                validate_f40_profile_axis_v2,
            )

            validate_f40_profile_axis_v2(
                request=request, profile=replay_profile, stored_refs=producer_refs,
                stored_axis_bytes=bytes(run["implementation_refs_json"]),
            )
        require(run["corpus_index_sha256"] == refs["corpus_index_ref"]["sha256"], "stored corpus index hash drift")
        sweep = load_gemini_accounting_family_sweep_v1(store, run_id)
        require(run["family_id"] == sweep["family_id"]
                and run["sweep_format_version"] == sweep["format_version"]
                and run["corpus_manifest_index_id"] == sweep["corpus_manifest_index_id"],
                "stored run/sweep metadata drift")
        stored_bytes = bytes(connection.execute("SELECT sweep_bytes FROM family_run WHERE family_run_id=?", (run_id,)).fetchone()[0])
        require(json_bytes(sweep) + b"\n" == stored_bytes, "stored sweep is not exact canonical bytes")
        require(run["sweep_sha256"] == sha256(stored_bytes).hexdigest(), "sweep byte SHA drift")
        del stored_bytes
        expected_run_id = "gjfafstorev1:run:" + canonical_json_sha256_v1({
            "corpus_index_sha256": run["corpus_index_sha256"],
            "implementation_axis_sha256": run["implementation_axis_sha256"],
            "sweep_id": sweep["sweep_id"], "sweep_sha256": run["sweep_sha256"],
        })
        require(run_id == expected_run_id and run["sweep_id"] == sweep["sweep_id"], "SQLite run identity drift")
        for key, value in sweep["metrics"].items():
            require(run[key] == value, f"stored metric drift: {key}")
        for kind in ("topology", "evaluation", "schema_binding"):
            require(run[f"{kind}_spec_sha256"] == sweep["specs"][kind]["sha256"], "stored spec hash drift")
        _check_trace_rows_v1(connection, run_id, sweep)
        run_metadata = {key: run[key] for key in run.keys() if key != "implementation_refs_json"}
    reject_legacy_imputation_v1(sweep)
    validate_source_observation_mapping_contract_v1(sweep)
    compiled = compile_gemini_json_flat_family_specs_v1(
        sweep["specs"]["topology"]["value"], sweep["specs"]["evaluation"]["value"],
        sweep["specs"]["schema_binding"]["value"],
    )
    page_db = Path(refs["source_page_database_ref"]["path"])
    with closing(_ro(page_db)) as connection:
        require([row[0] for row in connection.execute("PRAGMA quick_check")] == ["ok"], "source SQLite quick_check failed")
        require(connection.execute("PRAGMA foreign_key_check").fetchone() is None, "source SQLite foreign key violation")
    selected = _selected_corpus_page_frontier_v1(
        corpus_index_ref=refs["corpus_index_ref"],
        corpus_artifact_root=Path(request["corpus_artifact_root"]),
        effective_page_artifact_root=(Path(request["effective_page_artifact_root"])
                                      if request["effective_page_artifact_root"] is not None else None),
        checked_sweep=sweep, source_page_database=page_db,
    )
    profile_receipt, extra_refs = None, []
    if replay_profile is None:
        replayed = validate_selected_multitable_hierarchical_family_candidate_replays_v1(
            page_db, selected_page_json_version_ids=selected, compiled_specs=compiled,
            indexed_query_evidence=sweep["indexed_query_evidence"], trials=sweep["trials"],
        )
    else:
        from bctc_ai.export.gemini_tm_family_replay_profiles_v2 import replay_f40_profile_v2

        replayed, profile_receipt, extra_refs = replay_f40_profile_v2(
            request=request, profile=replay_profile, sweep=sweep, compiled_specs=compiled,
            selected=selected, source_page_database=page_db,
        )
    require(json_bytes(replayed) == json_bytes(sweep["trials"]), "fresh source replay trial axis drift")
    index = validate_current_corpus_manifest_index_v1(strict_json_v1(pinned_bytes_v1(refs["corpus_index_ref"])))
    ordinal = request["document_ordinal"]
    require(ordinal <= len(sweep["trials"]) and ordinal <= len(index["documents"]), "global document ordinal outside corpus")
    trial = sweep["trials"][ordinal - 1]
    document = index["documents"][ordinal - 1]
    axis = sweep["indexed_query_evidence"]["selected_document_axis"][ordinal - 1]
    require(trial["document_ordinal"] == axis["document_ordinal"] == document["source_ordinal"] == ordinal
            and trial["source_logical_name"] == axis["source_logical_name"] == document["relative_path"]
            and trial["source_sha256"] == axis["source_sha256"] == document["source_sha256"], "global document/source join drift")
    relative = PurePosixPath(document["relative_path"])
    require(not relative.is_absolute() and not any(part in {"..", "."} for part in relative.parts)
            and "\\" not in document["relative_path"], "unsafe PDF logical path")
    pdf = Path(request["source_pdf_root"]).joinpath(*relative.parts)
    pdf_ref = authenticate_ref_v1({"path": str(pdf), "sha256": document["source_sha256"],
                                   "size_bytes": document["source_size_bytes"]})
    page_axis = [item for item in sweep["indexed_query_evidence"]["selected_page_axis"]
                 if item["document_ordinal"] == ordinal]
    pages = load_page_json_versions_v1(page_db, page_json_version_ids=[item["page_json_version_id"] for item in page_axis])
    page_map = {item["page_json_version_id"]: item for item in pages}
    require(len(page_map) == len(page_axis), "selected document page frontier incomplete")
    for item in page_axis:
        loaded = page_map[item["page_json_version_id"]]
        require(loaded["source_sha256"] == document["source_sha256"]
                and loaded["physical_page"] == item["physical_page"], "page provenance/source drift")
    for reference in [*refs.values(), *producer_files, pdf_ref, *extra_refs]:
        authenticate_ref_v1(reference)
    assert_sealed_sqlite_snapshot_v1(store)
    assert_sealed_sqlite_snapshot_v1(page_db)
    return {"sweep": sweep, "trial": trial, "document": {**document, **axis, "status": trial["status"]},
            "compiled": compiled, "pages": page_map, "page_axis": page_axis,
            "refs": refs, "producer_files": producer_files, "pdf_ref": pdf_ref,
            "run_metadata": run_metadata, "request": request,
            **({"source_replay_profile_receipt": profile_receipt, "extra_input_refs": extra_refs}
               if profile_receipt is not None else {})}


def authenticate_multitable_store_run_v1(request: dict[str, Any]) -> dict[str, Any]:
    """Legacy V1 strict request and generic MTH replay; no family profile fallback."""
    return _authenticate_multitable_store_run_v1(request)


def period_from_source_lane_v1(key: list[str], period_type: str) -> dict[str, str]:
    if period_type == "SNAPSHOT" and len(key) == 2 and key[0] == "DATE":
        parsed = date.fromisoformat(key[1])
        require(parsed.isoformat() == key[1], "noncanonical source date")
        return {"basis": "STOCK_AS_OF", "as_of": key[1]}
    if period_type == "DURATION" and len(key) == 3 and key[0] == "DURATION_DATE_RANGE":
        start, end = (date.fromisoformat(value) for value in key[1:])
        require(start.isoformat() == key[1] and end.isoformat() == key[2] and start <= end,
                "invalid complete source flow interval")
        return {"basis": "FLOW_RANGE", "start": key[1], "end": key[2]}
    raise ValueError("full source-proven stock date/flow range is unavailable; semantic lane/year is insufficient")


def _ordinal_id(value: str, prefix: str) -> int:
    require(type(value) is str and re.fullmatch(prefix + r"[1-9][0-9]*", value) is not None,
            "unsupported structural source locator")
    return int(value[1:])


def project_multitable_document_v1(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    """Project every accepted mapping lane or reject the entire document.

    Initial grammar: direct/corroborated raw integer/dash/blank rows, ordinary
    one-to-one source column axes, complete dated stock/flow periods. Derived,
    transposed, sign/scaling and semantic-only period projections are withheld.
    """
    trial, document, sweep = (bundle[key] for key in ("trial", "document", "sweep"))
    if trial["status"] != "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY":
        require(not trial["mappings"], "non-ready document has numeric mappings")
        raise ValueError(f"document remains {trial['status']}; no accepted-source workbook is published")
    candidates = [item for item in trial["candidates"] if item["candidate_id"] == trial["selected_candidate_id"]]
    require(len(candidates) == 1 and candidates[0]["mappings"] == trial["mappings"], "selected candidate mapping join drift")
    candidate = candidates[0]
    schema = sweep["specs"]["schema_binding"]["value"]
    roles = {item["role"]: item["report_norm_id"] for item in schema["role_bindings"]}
    roles["FAMILY_ROOT_TOTAL"] = schema["family_root_report_norm_id"]
    tables = candidate["closure_receipt"]["table_receipts"]
    records, current_ends = [], set()
    axis_by_version = {item["page_json_version_id"]: item for item in bundle["page_axis"]}
    for mapping_n, mapping in enumerate(trial["mappings"], 1):
        require(roles.get(mapping["role"]) == mapping["report_norm_id"], "mapping role/RNID outside schema binding")
        require(type(mapping["unit"]) is str and bool(mapping["unit"]), "mapping unit unknown")
        require(type(mapping["source_refs"]) is list and bool(mapping["source_refs"]), "mapping source axis absent")
        for lane, cell in enumerate(mapping["values"]):
            require(cell.get("state") in SUPPORTED_STATES, "derived/transformed cell is outside V1 grammar")
            require(json_bytes(cell) == json_bytes(_money(cell.get("source_text"))),
                    "raw source text/coefficient/state mismatch")
            proof_rows, periods, unit_proofs, lane_roles = [], [], [], []
            for ref in mapping["source_refs"]:
                locator = ref["locator"]
                version = locator["page_json_version_id"]
                axis = axis_by_version.get(version)
                require(axis is not None and all(locator.get(key) == axis[key] for key in axis), "source locator/document/page join drift")
                matching = [item for item in tables if item["region"] == locator]
                require(len(matching) == 1, "source table receipt is absent or ambiguous")
                receipt = matching[0]
                lanes = receipt["lane_axis"]
                columns = ref["money_column_ordinals"]
                require(lanes.get("complete") is True and lanes["money_column_ordinals"] == columns
                        and len(columns) == len(mapping["values"]), "unsupported transformed/projected source columns")
                source_keys = lanes.get("source_lane_keys", lanes["lane_keys"])
                require(len(source_keys) == len(columns), "source period axis incomplete")
                periods.append(period_from_source_lane_v1(source_keys[lane], schema["schema_period_type"]))
                period_ends = [period_from_source_lane_v1(key, schema["schema_period_type"]) for key in source_keys]
                ends = [item.get("as_of", item.get("end")) for item in period_ends]
                require(len(set(ends)) == len(ends), "duplicate/ambiguous dated lane axis")
                lane_role = "CURRENT" if ends[lane] == max(ends) else "COMPARATIVE"
                canonical_key = lanes["lane_keys"][lane]
                if canonical_key[0] == "SEMANTIC_ALIAS":
                    expected_role = {"CURRENT_PERIOD": "CURRENT", "COMPARATIVE_PERIOD": "COMPARATIVE"}.get(canonical_key[1])
                    require(expected_role == lane_role, "semantic role conflicts with full source dates")
                lane_roles.append(lane_role)
                if lane_role == "CURRENT":
                    current_ends.add(ends[lane])
                unit_axis = receipt["unit_axis"]
                require(unit_axis.get("complete") is True
                        and unit_axis.get("canonical_unit") == mapping["unit"], "unit is not bound to source table")
                page = bundle["pages"][version]["page_json"]
                section = page["sections"][_ordinal_id(locator["section_id"], "s") - 1]
                table = section["tables"][_ordinal_id(locator["table_id"], "t") - 1]
                row = table["rows"][ref["row_ordinal"] - 1]
                require(ref["row_id"] == f"r{ref['row_ordinal']}" and all(
                    ref.get(key) == row.get(key) for key in ("label_exact", "row_kind", "hierarchy_path_exact")
                ), "source row identity drift")
                raw = row["values_exact"][columns[lane] - 1]
                require(raw == cell["source_text"] and type(raw) is type(cell["source_text"]),
                        "projection source string differs from exact selected JSON cell")
                proof_rows.append({"source_ref": ref, "column_ordinal": columns[lane],
                                   "header_path_exact": table["columns"][columns[lane] - 1]["header_path_exact"],
                                   "source_lane_key": source_keys[lane], "lane_axis": lanes})
                unit_proofs.append({"source_ref": ref, "unit_axis": unit_axis})
            require(all(item == periods[0] for item in periods) and len(set(lane_roles)) == 1,
                    "source periods disagree across corroborated rows")
            record = {"document_id": document["document_id"], "document_plan_id": document["document_plan_id"],
                      "global_document_ordinal": document["document_ordinal"],
                      "family_id": sweep["family_id"], "family_run_id": bundle["run_metadata"]["family_run_id"],
                      "sweep_id": sweep["sweep_id"], "mapping_ordinal": mapping_n,
                      "mapping_id": mapping["item_mapping_id"], "role": mapping["role"],
                      "report_norm_id": mapping["report_norm_id"], "coefficient_codec": CODEC,
                      "cell": cell, "unit": mapping["unit"], "period": periods[0],
                      "lane_role": lane_roles[0], "lane_ordinal": lane + 1,
                      "source_refs": mapping["source_refs"], "period_proofs": proof_rows,
                      "unit_proofs": unit_proofs, "mapping_state": mapping["state"]}
            record["record_id"] = "gjtmprojv1:" + canonical_json_sha256_v1(record)
            records.append(record)
    require(bool(records) and len(current_ends) == 1, "document current reporting period is not unique")
    current_end = date.fromisoformat(next(iter(current_ends)))
    require(2025 <= current_end.year and current_end <= date.today(), "report outside 2025-current production scope")
    require(len(json_bytes(records)) <= MAX_DOCUMENT_PROJECTION_BYTES, "document projection exceeds V1 memory bound")
    return records


def export_tm_multitable_store_document_v1(*, request: dict[str, Any]) -> dict[str, Any]:
    require(type(request) is dict, "request must be a JSON object")
    request = strict_json_v1(json_bytes(request))
    bundle = authenticate_multitable_store_run_v1(request)
    return _export_authenticated_multitable_document_v1(request=request, bundle=bundle)


def _export_authenticated_multitable_document_v1(
    *, request: dict[str, Any], bundle: dict[str, Any],
) -> dict[str, Any]:
    records = project_multitable_document_v1(bundle)
    template = template_rows_v1(pinned_bytes_v1(bundle["refs"]["template_ref"]))
    provenance = {"format_version": FORMAT, "label": LABEL, "run_metadata": bundle["run_metadata"],
                  "input_refs": bundle["refs"], "producer_files": bundle["producer_files"],
                  "source_pdf_ref": bundle["pdf_ref"], "source_replay": "EXACT_FULL_STORED_TRIAL_AXIS",
                  "schema_binding": bundle["sweep"]["specs"]["schema_binding"],
                  "checked_request_sha256": sha256(json_bytes(request)).hexdigest(),
                  "trial": bundle["trial"], "projection_sha256": sha256(json_bytes(records)).hexdigest(),
                  "bridge_implementation_ref": file_ref_v1(Path(__file__).resolve()),
                  "renderer_implementation_ref": file_ref_v1(Path(inspect.getsourcefile(render_projected_tm_workbook_v1)).resolve())}
    if "source_replay_profile_receipt" in bundle:
        provenance["source_replay_profile"] = bundle["source_replay_profile_receipt"]
    require(len(json_bytes(provenance)) <= MAX_DOCUMENT_PROJECTION_BYTES,
            "document provenance exceeds V1 memory bound")
    payload, verification = render_projected_tm_workbook_v1(
        document=bundle["document"], records=records, template=template, provenance=provenance,
    )
    # Final byte authentication after replay/render and before any output mutation.
    for ref in [*bundle["refs"].values(), *bundle["producer_files"], bundle["pdf_ref"],
                provenance["bridge_implementation_ref"], provenance["renderer_implementation_ref"],
                *bundle.get("extra_input_refs", [])]:
        authenticate_ref_v1(ref)
    assert_sealed_sqlite_snapshot_v1(Path(bundle["refs"]["store_ref"]["path"]))
    assert_sealed_sqlite_snapshot_v1(Path(bundle["refs"]["source_page_database_ref"]["path"]))
    output = Path(request["output_dir"])
    require(output.is_absolute() and not output.exists(), "output directory must be new and absolute")
    require(output.parent.is_dir(), "output parent must already exist")
    for parent in [output.parent, *output.parent.parents]:
        require(not parent.is_symlink() and not getattr(parent, "is_junction", lambda: False)()
                and not (parent / ".git").exists(), "output cannot cross symlink/junction or Git worktree")
    forbidden_roots = [Path(request[key]).resolve() for key in
                       ("source_pdf_root", "corpus_artifact_root", "producer_root")]
    if request["effective_page_artifact_root"] is not None:
        forbidden_roots.append(Path(request["effective_page_artifact_root"]).resolve())
    forbidden_roots += [Path(ref["path"]).parent for ref in bundle["refs"].values()]
    forbidden_roots += [Path(ref["path"]).parent for ref in bundle["producer_files"]]
    forbidden_roots += [Path(ref["path"]).parent for ref in bundle.get("extra_input_refs", [])]
    require(not any(output.resolve().is_relative_to(root) for root in forbidden_roots), "output overlaps input authority")
    receipt = {"format_version": FORMAT, "label": LABEL, "document": bundle["document"],
               "provenance": provenance, "projection_count": len(records),
               "xlsx": {**verification, "path": str(output / "tm.xlsx")},
               "run_kind_requested": request["expected_run_kind"],
               "current_selection_required": request["require_current_selection"],
               "scope_check_date": date.today().isoformat(),
               "financial_acceptance": "NOT_CLAIMED", "store_modified": False}
    receipt["receipt_material_sha256"] = sha256(json_bytes(receipt)).hexdigest()
    receipt_payload = json_bytes(receipt)
    # Exclusive directory is the publish boundary. A partial directory after an
    # I/O failure is not a successful export; no old outputs are removed/replaced.
    output.mkdir(exist_ok=False)
    with (output / "tm.xlsx").open("xb") as destination:
        destination.write(payload)
    require((output / "tm.xlsx").read_bytes() == payload, "published workbook bytes differ from typed-verified bytes")
    with (output / "receipt.json").open("xb") as destination:
        destination.write(receipt_payload)
    with (output / "receipt.sha256").open("xb") as destination:
        destination.write((sha256(receipt_payload).hexdigest() + "  receipt.json\n").encode("ascii"))
    return {"output_dir": str(output), "xlsx_sha256": verification["sha256"],
            "receipt_sha256": sha256(receipt_payload).hexdigest(), "label": LABEL}
