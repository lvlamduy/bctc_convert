"""UNRUN F36-only canonical proposal adapter; no acceptance or default dispatch.

This version has its OWN notes frontier, never legacy multitable query evidence.
Structural validators do not authenticate files or establish financial meaning.
The checked IO replay rebuilds actual notes/source/PRIMARY/ROOT evidence before
the existing family store may persist a proposal. All nonmapped cells survive.
"""
from __future__ import annotations

import json
import os
import re
import stat
from collections import defaultdict
from dataclasses import replace
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import _money
from bctc_ai.evaluation.gemini_json_operating_expense_original_inventory_v1 import _nodes
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    validate_source_observation_mapping_contract_v1,
)
from bctc_ai.notes.config_v1 import Axis, Family, load_notes_config_v1
from bctc_ai.notes.engine_v1 import dispositions_v1, run_family_v1
from bctc_ai.notes.f36_strict_ledger_v1 import (
    classify_observation_v1,
    classify_rows_v1,
    classify_table_v1,
    exact_rnid_bindings_v1,
)
from bctc_ai.notes.kernel_v1 import (
    NotesSource,
    canonical_period_key_v1,
    load_primary_context_v1,
)
from bctc_ai.notes.root_closure_v1 import root_closure_v1
from bctc_ai.primary_statements.periods_v1 import (
    duration_lane_period_v1,
    statement_period_context_v1,
)
from bctc_ai.primary_statements.source_v1 import (
    SourceMetrics,
    load_corpus_selection_v1,
    sha256_file,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
)

FAMILY = "OPERATING_EXPENSE"
FORMAT = "GEMINI_JSON_F36_NOTES_STRICT_CORE_SWEEP_V1"
TOPOLOGY_FORMAT = "F36_NOTES_SOURCE_FRONTIER_SPEC_V1"
EVALUATION_FORMAT = "F36_NOTES_STRICT_CORE_EVALUATION_SPEC_V1"
SCHEMA_FORMAT = "F36_NOTES_CROSSWALK_BINDING_SPEC_V1"
QUERY_FORMAT = "F36_NOTES_REBUILT_SOURCE_FRONTIER_V1"
CLAIM = "F36_NOTES_AUTHENTICATED_REPLAY_REQUIRED_PROPOSAL_ONLY_NOT_ACCEPTANCE"
_SHA = re.compile(r"[0-9a-f]{64}")
_RECEIPTS = {"producer_manifest", "ledger_summary", "ledger_observations",
             "closure_results", "neutral_inventory", "root_build"}


class F36NotesCoreAdapterError(ValueError):
    pass


def _need(ok: bool, message: str) -> None:
    if not ok:
        raise F36NotesCoreAdapterError(message)


def _same(left: Any, right: Any) -> bool:
    # Canonical encoding preserves bool/int, null/empty, number/string distinctions.
    return canonical_json_sha256_v1(left) == canonical_json_sha256_v1(right)


def _ref(ref: Any) -> None:
    _need(type(ref) is dict and set(ref) == {"path", "sha256", "size_bytes"}, "File ref shape")
    _need(type(ref["path"]) is str and bool(ref["path"])
          and type(ref["sha256"]) is str and _SHA.fullmatch(ref["sha256"]) is not None
          and type(ref["size_bytes"]) is int and ref["size_bytes"] > 0, "File ref fields")


def _fd_sha(fd: int) -> str:
    digest, offset = sha256(), 0
    while chunk := os.pread(fd, 1024 * 1024, offset):
        digest.update(chunk)
        offset += len(chunk)
    return digest.hexdigest()


def _identity(status: Any) -> tuple[Any, ...]:
    return (status.st_dev, status.st_ino, status.st_mode, status.st_size, status.st_mtime_ns, status.st_ctime_ns)


def compile_f36_notes_core_specs_v1(topology_spec: Any, evaluation_spec: Any,
                                   schema_binding_spec: Any) -> dict[str, Any]:
    """Pure new-format compiler. References are declarations, not IO authentication."""
    for spec, version, fields in (
        (topology_spec, TOPOLOGY_FORMAT, {"format_version", "family_id", "source", "documents_requested"}),
        (evaluation_spec, EVALUATION_FORMAT, {"format_version", "family_id", "notes_config_pins",
                                             "notes_family", "production_policy", "production_policy_ref",
                                             "primary_store_ref", "frontier_receipt_refs"}),
        (schema_binding_spec, SCHEMA_FORMAT, {"format_version", "family_id", "crosswalk"}),
    ):
        _need(type(spec) is dict and set(spec) == fields and spec["family_id"] == FAMILY
              and spec["format_version"] == version, "F36-only versioned spec required")
    source = topology_spec["source"]
    _need(type(source) is dict and set(source) == {"corpus_name", "artifact_root", "index_ref",
                                                  "database_ref", "corpus_identity", "document_axis"},
          "Complete source frontier required")
    for key in ("index_ref", "database_ref"):
        _ref(source[key])
    _ref(evaluation_spec["primary_store_ref"])
    _ref(evaluation_spec["production_policy_ref"])
    _need(type(source["artifact_root"]) is str and Path(source["artifact_root"]).is_absolute()
          and type(source["corpus_name"]) is str, "Source root/name")
    identity = source["corpus_identity"]
    _need(type(identity) is dict and identity.get("index_sha256") == source["index_ref"]["sha256"]
          and identity.get("database_sha256") == source["database_ref"]["sha256"]
          and identity.get("corpus_name") == source["corpus_name"], "Corpus identity refs")
    docs = source["document_axis"]
    _need(type(docs) is list and bool(docs), "Document axis empty")
    for ordinal, doc in enumerate(docs, 1):
        _need(type(doc) is dict and set(doc) == {"document_ordinal", "source_logical_name", "source_sha256",
              "document_identity", "pages"} and type(doc["document_ordinal"]) is int
              and doc["document_ordinal"] == ordinal and type(doc["source_logical_name"]) is str
              and type(doc["source_sha256"]) is str and _SHA.fullmatch(doc["source_sha256"]) is not None
              and type(doc["document_identity"]) is dict and type(doc["pages"]) is list and bool(doc["pages"]),
              "Document identity/ordinal")
        _need(doc["document_identity"].get("relative_path") == doc["source_logical_name"]
              and doc["document_identity"].get("source_sha256") == doc["source_sha256"]
              and type(doc["document_identity"].get("document_ordinal")) is int
              and doc["document_identity"]["document_ordinal"] == ordinal, "Nested document identity")
        for page in doc["pages"]:
            _need(type(page) is dict and set(page) == {"physical_page", "page_json_version_id"}
                  and type(page["physical_page"]) is int and page["physical_page"] > 0
                  and type(page["page_json_version_id"]) is str
                  and page["page_json_version_id"].startswith("gfpstorev1:json:"), "Selected page axis")
        physical = [p["physical_page"] for p in doc["pages"]]
        _need(physical == sorted(set(physical)), "Physical page axis duplicate/order")
    versions = [p["page_json_version_id"] for d in docs for p in d["pages"]]
    _need(len(versions) == len(set(versions)), "Duplicate selected VID")
    _need(len({d["source_logical_name"] for d in docs}) == len(docs), "Duplicate source document")
    requested = topology_spec["documents_requested"]
    _need(type(requested) is list and bool(requested) and all(type(n) is int and 1 <= n <= len(docs) for n in requested)
          and requested == sorted(set(requested)), "Requested subset must be explicit")
    pins = evaluation_spec["notes_config_pins"]
    _need(type(pins) is dict and bool(pins) and all(type(k) is str and type(v) is str
          and re.fullmatch(r"(?:axes_v1|crosswalk_v1|families/[a-z0-9_]+)\.yaml", k) is not None
          and _SHA.fullmatch(v) is not None for k, v in pins.items()), "Notes config pins")
    _family(evaluation_spec)
    policy = evaluation_spec["production_policy"]
    _need(type(policy) is dict and policy.get("family_id") == FAMILY
          and policy.get("family_root_population_policy") == "WHOLE_TABLE"
          and policy.get("family_root_requirement") == "REQUIRED_SOURCE_VISIBLE_EXACT_ROOT"
          and policy.get("period_lane_policy") == "CURRENT_AND_COMPARATIVE_REQUIRED"
          and policy.get("source_presentation_rounding_policy")
          == "INDEPENDENT_DISPLAY_UNIT_ROUNDING_INTERVAL_ALL_EQUATIONS", "Production F36 policy changed")
    receipts = evaluation_spec["frontier_receipt_refs"]
    _need(type(receipts) is dict and set(receipts) == _RECEIPTS, "Actual frontier receipt axis incomplete")
    for ref in receipts.values():
        _ref(ref)
    crosswalk = schema_binding_spec["crosswalk"]
    _need(type(crosswalk) is list and bool(crosswalk), "Crosswalk empty")
    for entry in crosswalk:
        _need(type(entry) is dict and set(entry) == {"concept", "axis", "members", "report_norm_id"}
              and all(type(entry[k]) is str and entry[k] for k in ("concept", "axis"))
              and type(entry["members"]) is list and bool(entry["members"])
              and all(type(m) is str and m for m in entry["members"])
              and type(entry["report_norm_id"]) is int and entry["report_norm_id"] > 0, "Crosswalk fields")
    _need(len({(e["concept"], e["axis"], tuple(e["members"])) for e in crosswalk}) == len(crosswalk)
          and len({e["report_norm_id"] for e in crosswalk}) == len(crosswalk), "Crosswalk duplicate")
    return {"engine_format_version": FORMAT, "claim_boundary": CLAIM,
            "topology": canonical_clone_v1(topology_spec), "evaluation": canonical_clone_v1(evaluation_spec),
            "schema": canonical_clone_v1(schema_binding_spec)}


def _family(evaluation: dict[str, Any]) -> Family:
    descriptor = evaluation["notes_family"]
    _need(type(descriptor) is dict and set(descriptor) == {"raw", "sha256", "axis"}
          and type(descriptor["sha256"]) is str and _SHA.fullmatch(descriptor["sha256"]) is not None,
          "Notes family declaration")
    raw = descriptor["raw"]
    _need(type(raw) is dict and raw.get("family") == FAMILY and raw.get("shape") == "CONCEPT_LIST"
          and raw.get("period_basis") == "DURATION", "Notes family/basis declaration")
    axis = descriptor["axis"]
    _need(type(axis) is dict and set(axis) == {"name", "members", "outside_members"}
          and axis["name"] == raw["axis"] and type(axis["members"]) is dict
          and bool(axis["members"]) and type(axis["outside_members"]) is dict, "Complete notes role axis")
    return Family(FAMILY, "CONCEPT_LIST", Axis(axis["name"], axis["members"], axis["outside_members"]),
                  "DURATION", raw, descriptor["sha256"])


def _document_axis(corpus: Any) -> list[dict[str, Any]]:
    return [{"document_ordinal": d.ordinal, "source_logical_name": d.relative_path,
             "source_sha256": d.source_sha256, "document_identity": d.identity(),
             "pages": [{"physical_page": p.physical_page, "page_json_version_id": p.page_json_version_id}
                       for p in d.pages]} for d in corpus.documents]


def _inventory(page: dict[str, Any], version: str, blob_sha: str) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Reuse unchanged neutral transport; freshness belongs to the actual original loader."""
    tables: dict[tuple[str, str, str], dict[str, Any]] = {}
    current = section = None
    for node in _nodes(page):
        if node["record_type"] == "section":
            current, section = None, node
        elif node["record_type"] == "table":
            current = (version, node["section_id"], node["table_id"])
            tables[current] = {"table": {**node, "page_json_version_id": version}, "section": section, "columns": [], "rows": [],
                               "unsupported": [], "page": {"axis": {"page_json_version_id": version},
                               "source_proof": {"stored_blob_two_lf_sha256": blob_sha}}}
        elif current is not None and node["pointer"].startswith(tables[current]["table"]["pointer"] + "/"):
            field = {"column": "columns", "row": "rows", "unsupported_shape": "unsupported"}.get(node["record_type"])
            if field is not None:
                tables[current][field].append(node)
    return tables


def _fragments(cells: list[dict[str, Any]], records: list[dict[str, Any]],
               allowed_units: set[str], period_contexts: dict[int, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Encoding only. Inputs must be freshly recomputed by rebuild_f36_notes_trials_v1."""
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    retained = []
    for cell, record in zip(cells, records, strict=True):
        _need(_same(record.get("cell"), cell), "Full cell/classification binding")
        if record["class"] != "CORE_CANDIDATE":
            retained.append({"classification": record, "adapter_disposition": "RETAINED_NOT_CANONICAL"})
            continue
        _need(cell.get("acceptance") == "ACCEPTED" and record.get("lane_closure") == "ROOT_CLOSED"
              and type(record.get("exact_rnid_binding")) is int
              and record["exact_rnid_binding"] == cell.get("report_norm_id")
              and cell.get("observation_state") in {"VALUE", "PRINTED_ZERO"}
              and cell.get("scope") in {"SEPARATE", "CONSOLIDATED"}, "Core structural conditions")
        loc = cell["locator"]
        origin = cell["original_cell"]
        _need(type(origin) is dict and all(type(origin.get(k)) is int and origin[k] > 0
              for k in ("section_ordinal", "table_ordinal", "row_ordinal", "column_ordinal"))
              and origin.get("page_json_version_id") == loc["page_json_version_id"], "Typed ORIGINAL coordinate")
        _need(loc["row_id"] == f"r{origin['row_ordinal']}" and loc["section_id"] == f"s{origin['section_ordinal']}"
              and loc["table_id"] == f"t{origin['table_ordinal']}"
              and type(loc.get("physical_page")) is int and loc["physical_page"] > 0, "Exact original row/table locator")
        key = (loc["page_json_version_id"], loc["section_id"], loc["table_id"], loc["row_id"],
               cell["member"], cell["report_norm_id"], cell["scope"], cell["classification_basis"], cell["unit"])
        groups[key].append(cell)
    mappings = []
    for key, own in groups.items():
        # Initial declared F36 policy needs both actual lanes. No placeholder comparative.
        own = sorted(own, key=lambda c: c["original_cell"]["column_ordinal"])
        reason = None
        if len(own) != 2 or len({c["period_key"] for c in own}) != 2:
            reason = "EXPLICIT_TWO_LANE_PAIR_NOT_PROVEN"
        elif key[-1] not in allowed_units:
            reason = "UNIT_OUTSIDE_DECLARED_F36_BINDINGS"
        values = []
        periods = []
        if reason is None:
            for cell in own:
                descriptor = duration_lane_period_v1(cell["header_text"], period_contexts[cell["document_ordinal"]])
                if (descriptor.basis != "DURATION" or descriptor.role not in {"CURRENT", "COMPARATIVE"}
                        or canonical_period_key_v1(descriptor.key) != canonical_period_key_v1(cell["period_key"])
                        or canonical_period_key_v1(cell["period_key"]) is None):
                    reason = "SOURCE_PERIOD_ROLE_PAIR_NOT_PROVEN_BY_EXISTING_PARSER"
                    break
                periods.append(descriptor.to_dict())
                try:
                    parsed = _money(cell["raw"])
                except ValueError:
                    reason = "SOURCE_NUMERIC_SYNTAX_OUTSIDE_EXISTING_INTEGER_CODEC"
                    break
                number = Decimal(cell["value"])
                if (parsed is None or parsed["state"] != "RAW_SIGNED_INTEGER" or not number.is_finite()
                        or number != number.to_integral_value() or parsed["coefficient"] != number):
                    reason = "EXISTING_INTEGER_CODEC_DIFFERS_FROM_PRODUCER_VALUE"
                    break
                values.append(parsed)
            if reason is None and {p["role"] for p in periods} != {"CURRENT", "COMPARATIVE"}:
                reason = "SOURCE_PERIOD_ROLE_PAIR_NOT_CURRENT_AND_COMPARATIVE"
        if reason is not None:
            retained.extend({"cell": c, "adapter_disposition": reason} for c in own)
            continue
        # Canonical values are CURRENT then COMPARATIVE, independently of the
        # printed column order. Keep every value/evidence axis zipped together.
        ordered = sorted(zip(own, periods, values, strict=True),
                         key=lambda item: {"CURRENT": 0, "COMPARATIVE": 1}[item[1]["role"]])
        own = [item[0] for item in ordered]
        periods = [item[1] for item in ordered]
        values = [item[2] for item in ordered]
        refs = []
        for cell in own:
            origin = cell["original_cell"]
            refs.append({"locator": {"page_json_version_id": origin["page_json_version_id"],
                         "physical_page": cell["locator"]["physical_page"],
                         "section_id": f"s{origin['section_ordinal']}", "table_id": f"t{origin['table_ordinal']}"},
                         "row_id": f"r{origin['row_ordinal']}", "row_ordinal": origin["row_ordinal"],
                         "money_column_ordinals": [origin["column_ordinal"]], "period_key": cell["period_key"],
                         "notes_observation_state": cell["observation_state"], "cell": _money(cell["raw"])})
        material = {"report_norm_id": key[5], "role": key[4], "row_id": key[3], "source_refs": refs,
                    "state": "SOURCE_VISIBLE_NOTES_STRICT_CORE_PROPOSAL", "unit": key[-1], "values": values,
                    "scope": key[6], "classification_basis": key[7],
                    "period_axis": [{"period_key": c["period_key"], "period_basis": c["period_basis"],
                                     "original_column_ordinal": c["original_cell"]["column_ordinal"],
                                     "parsed_period": p} for c, p in zip(own, periods, strict=True)]}
        mappings.append({**material, "item_mapping_id": "gjmthfmv1:item:" + canonical_json_sha256_v1(material)})
    validate_source_observation_mapping_contract_v1(mappings)
    return canonical_clone_v1(mappings), canonical_clone_v1(retained)


def rebuild_f36_notes_trials_v1(*, source: NotesSource, contexts: dict[int, Any], config: Any,
                                compiled_specs: dict[str, Any]) -> list[dict[str, Any]]:
    """Actual financial/bridge/ROOT rebuild, not an encoder of caller classifications.

    The IO caller owns the authenticated original snapshot, PRIMARY/config refs,
    complete frontier receipts and final barriers. No arbitrary evaluator callback.
    """
    compiled = compile_f36_notes_core_specs_v1(compiled_specs["topology"], compiled_specs["evaluation"], compiled_specs["schema"])
    _need(_same(compiled, compiled_specs), "Compiled notes authority changed")
    topo, evaluation = compiled["topology"], compiled["evaluation"]
    _need(_same(_document_axis(source.corpus), topo["source"]["document_axis"])
          and _same(source.corpus.identity(), topo["source"]["corpus_identity"]), "Fresh source axis differs")
    _need(_same(config.pins, evaluation["notes_config_pins"]), "Fresh notes config differs")
    _need(_same(config.families[FAMILY].raw, evaluation["notes_family"]["raw"])
          and config.families[FAMILY].sha256 == evaluation["notes_family"]["sha256"], "Fresh family rules differ")
    axis = config.families[FAMILY].axis
    _need(_same({"name": axis.name, "members": axis.members, "outside_members": axis.outside_members},
                evaluation["notes_family"]["axis"]), "Fresh role axis differs")
    crosswalk = [{"concept": k[0], "axis": k[1], "members": list(k[2]), "report_norm_id": v}
                 for k, v in config.crosswalk.items()]
    _need(_same(crosswalk, compiled["schema"]["crosswalk"]), "Fresh crosswalk differs")
    requested = set(topo["documents_requested"])
    run = run_family_v1(FAMILY, config, source, contexts, document_ordinals=requested)
    dispositions = dispositions_v1(run)
    inventories = {}
    # Bounded per-page parsing; no whole-corpus ORIGINAL object cache.
    for doc in source.corpus.documents:
        if doc.ordinal not in requested:
            continue
        for selected in doc.pages:
            loaded = source._load_originals([selected.page_json_version_id])[selected.page_json_version_id]
            _need((loaded["source_sha256"], loaded["source_logical_name"], loaded["physical_page"])
                  == (doc.source_sha256, doc.relative_path, selected.physical_page), "Original source identity")
            blob = loaded["source_json_replay_receipt"]["canonical_json_sha256"]
            inventories.update(_inventory(loaded["page_json"], selected.page_json_version_id, blob))
    closure_by_table, rows = {}, {}
    for loc, inventory in inventories.items():
        for row in inventory["rows"]:
            rows[(loc[0], int(loc[1][1:]), int(loc[2][1:]), row["row_ordinal"])] = row
    for disposition in dispositions:
        loc = disposition["locator"]
        key = (loc["page_json_version_id"], loc["section_id"], loc["table_id"])
        if key in inventories:
            closure_by_table[key] = root_closure_v1(inventories[key], disposition, config.families[FAMILY])
    bindings = exact_rnid_bindings_v1(run.cells, config.crosswalk)
    records = []
    for cell, binding in zip(run.cells, bindings, strict=True):
        loc = cell["locator"]
        closure = closure_by_table.get((loc["page_json_version_id"], loc["section_id"], loc["table_id"]))
        records.append(classify_observation_v1(cell, binding, closure, rows))
    allowed_units = {u["canonical_unit"] for u in evaluation["production_policy"]["money_unit_bindings"] if u["accepted"] is True}
    period_contexts = {n: statement_period_context_v1(c.income_context_texts) for n, c in contexts.items()}
    trials = []
    for doc in topo["source"]["document_axis"]:
        ordinal = doc["document_ordinal"]
        own_indices = [i for i, c in enumerate(run.cells) if c["document_ordinal"] == ordinal]
        own_cells, own_records = [run.cells[i] for i in own_indices], [records[i] for i in own_indices]
        mappings, retained = _fragments(own_cells, own_records, allowed_units, period_contexts)
        own_dispositions = [d for d in dispositions if d["locator"]["document_ordinal"] == ordinal]
        closures = [{"table": list(k), "closure": v} for k, v in closure_by_table.items()
                    if any(p["page_json_version_id"] == k[0] for p in doc["pages"])]
        source_ledger = []
        page_ids = {p["page_json_version_id"] for p in doc["pages"]}
        assessed = {(k[0], int(k[1][1:]), int(k[2][1:])): v for k, v in closure_by_table.items()}
        subjects = config.families[FAMILY].raw["subjects"]["OPERATING_EXPENSE_NOTE"]["any"]
        for key, inv in inventories.items():
            if key[0] not in page_ids:
                continue
            table_cells = [c for c in own_cells if (c["locator"]["page_json_version_id"],
                           c["locator"]["section_id"], c["locator"]["table_id"]) == key]
            source_ledger.append({"inventory": inv,
                "table_classification": classify_table_v1(inv["table"], inv["section"], assessed, subjects),
                "rows": classify_rows_v1(inv["rows"], inv["columns"], table_cells, closure_by_table.get(key))})
        ledger = {"cells": own_cells, "classifications": own_records, "retained": retained,
                  "dispositions": own_dispositions, "root_closures": closures,
                  "source_ledger": source_ledger,
                  "primary_income_context_texts": contexts[ordinal].income_context_texts if ordinal in requested and ordinal in contexts else [],
                  "scope": "REQUESTED_F36_NOTES_DOCUMENT" if ordinal in requested else "NOT_EVALUATED_REQUESTED_SUBSET_ONLY"}
        candidates = []
        if own_dispositions:
            first = own_dispositions[0]["locator"]
            material = {**first, "status": "READY" if mappings else "UNRESOLVED",
                        "reasons": [] if mappings else ["NO_ENCODABLE_STRICT_CORE_LANES"],
                        "mappings": mappings, "closure_receipt": ledger,
                        "component_regions": [d["locator"] for d in own_dispositions]}
            candidates = [{**material, "candidate_id": "gjf36ncv1:candidate:" + canonical_json_sha256_v1(material)}]
        reasons = [] if mappings else ["NO_ENCODABLE_STRICT_CORE_LANES" if ordinal in requested else "DOCUMENT_OUTSIDE_REQUESTED_SCOPE"]
        trials.append({"document_ordinal": ordinal, "source_logical_name": doc["source_logical_name"],
                       "source_sha256": doc["source_sha256"], "status": "READY" if mappings else "UNRESOLVED",
                       "candidate_count": len(candidates), "candidates": candidates,
                       "selected_candidate_id": candidates[0]["candidate_id"] if mappings else None,
                       "mappings": mappings, "reasons": reasons, "notes_ledger": ledger})
    return canonical_clone_v1(trials)


def build_f36_notes_query_evidence_v1(*, trials: list[dict[str, Any]], compiled_specs: dict[str, Any]) -> dict[str, Any]:
    material = {"format_version": QUERY_FORMAT, "family_id": FAMILY,
                "selected_document_axis": compiled_specs["topology"]["source"]["document_axis"],
                "frontier_receipt_refs": compiled_specs["evaluation"]["frontier_receipt_refs"],
                "trial_frontier": [{"document_ordinal": t["document_ordinal"], "trial_sha256": canonical_json_sha256_v1(t)} for t in trials]}
    return {**canonical_clone_v1(material), "query_evidence_id": "gjf36nieqv1:evidence:" + canonical_json_sha256_v1(material)}


def validate_f36_notes_trials_v1(*, trials: Any, indexed_query_evidence: Any,
                                compiled_specs: dict[str, Any]) -> list[dict[str, Any]]:
    docs = compiled_specs["topology"]["source"]["document_axis"]
    _need(type(trials) is list and len(trials) == len(docs), "Complete trial denominator")
    for trial, doc in zip(trials, docs, strict=True):
        _need(type(trial) is dict and set(trial) == {"document_ordinal", "source_logical_name", "source_sha256", "status",
              "candidate_count", "candidates", "selected_candidate_id", "mappings", "reasons", "notes_ledger"}, "Trial fields")
        _need(all(type(trial[k]) is type(doc[k]) and trial[k] == doc[k] for k in
                  ("document_ordinal", "source_logical_name", "source_sha256")), "Trial source axis")
        _need(type(trial["mappings"]) is list and type(trial["candidates"]) is list
              and type(trial["candidate_count"]) is int and trial["candidate_count"] == len(trial["candidates"]) <= 1,
              "Candidate axis")
        _need(trial["status"] in {"READY", "UNRESOLVED"} and type(trial["reasons"]) is list
              and type(trial["notes_ledger"]) is dict, "Status/ledger axis")
        ledger = trial["notes_ledger"]
        _need(set(ledger) == {"cells", "classifications", "retained", "dispositions", "root_closures",
                             "source_ledger", "primary_income_context_texts", "scope"}
              and all(type(ledger[k]) is list for k in set(ledger) - {"scope"})
              and len(ledger["cells"]) == len(ledger["classifications"]), "Complete ledger fields")
        expected_scope = ("REQUESTED_F36_NOTES_DOCUMENT" if doc["document_ordinal"] in compiled_specs["topology"]["documents_requested"]
                          else "NOT_EVALUATED_REQUESTED_SUBSET_ONLY")
        _need(ledger["scope"] == expected_scope, "Requested scope drift")
        _need(all(c.get("document_ordinal") == doc["document_ordinal"] and c.get("family") == FAMILY for c in ledger["cells"]),
              "Ledger cells belong to another source")
        family = _family(compiled_specs["evaluation"])
        inventories, inventory_rows = {}, {}
        for source_record in ledger["source_ledger"]:
            _need(type(source_record) is dict and set(source_record) == {"inventory", "table_classification", "rows"},
                  "Source ledger entry")
            inv = source_record["inventory"]
            table = inv["table"]
            match = re.fullmatch(r"/sections/([0-9]+)/tables/([0-9]+)", table["pointer"])
            _need(match is not None, "Original table pointer")
            section, table_id = match.groups()
            key = (table["page_json_version_id"], f"s{int(section) + 1}", f"t{int(table_id) + 1}")
            _need(key not in inventories and any(p["page_json_version_id"] == key[0] for p in doc["pages"]),
                  "Duplicate/foreign source table")
            inventories[key] = inv
            for row in inv["rows"]:
                coordinate = (key[0], int(section) + 1, int(table_id) + 1, row["row_ordinal"])
                _need(coordinate not in inventory_rows, "Duplicate source row")
                inventory_rows[coordinate] = row
        closures = {}
        for disposition in ledger["dispositions"]:
            loc = disposition["locator"]
            key = (loc["page_json_version_id"], loc["section_id"], loc["table_id"])
            if key in inventories:
                _need(key not in closures, "Duplicate disposition")
                closures[key] = root_closure_v1(inventories[key], disposition, family)
        expected_closures = [{"table": list(k), "closure": v} for k, v in closures.items()]
        _need(_same(expected_closures, ledger["root_closures"]), "ROOT proof does not recompute")
        crosswalk = {(e["concept"], e["axis"], tuple(e["members"])): e["report_norm_id"]
                     for e in compiled_specs["schema"]["crosswalk"]}
        bindings = exact_rnid_bindings_v1(ledger["cells"], crosswalk)
        classified = []
        for cell, binding in zip(ledger["cells"], bindings, strict=True):
            loc = cell["locator"]
            classified.append(classify_observation_v1(cell, binding,
                closures.get((loc["page_json_version_id"], loc["section_id"], loc["table_id"])), inventory_rows))
        _need(_same(classified, ledger["classifications"]), "Original/RNID classification does not recompute")
        assessed = {(k[0], int(k[1][1:]), int(k[2][1:])): v for k, v in closures.items()}
        subjects = family.raw["subjects"]["OPERATING_EXPENSE_NOTE"]["any"]
        for source_record in ledger["source_ledger"]:
            inv = source_record["inventory"]
            key = (inv["table"]["page_json_version_id"], inv["table"]["section_id"], inv["table"]["table_id"])
            table_cells = [c for c in ledger["cells"] if (c["locator"]["page_json_version_id"], c["locator"]["section_id"],
                           c["locator"]["table_id"]) == key]
            _need(_same(source_record["table_classification"], classify_table_v1(inv["table"], inv["section"], assessed, subjects))
                  and _same(source_record["rows"], classify_rows_v1(inv["rows"], inv["columns"], table_cells, closures.get(key))),
                  "Table/row source accounting does not recompute")
        allowed = {u["canonical_unit"] for u in compiled_specs["evaluation"]["production_policy"]["money_unit_bindings"] if u["accepted"] is True}
        period_contexts = {doc["document_ordinal"]: statement_period_context_v1(ledger["primary_income_context_texts"])}
        expected_mappings, expected_retained = _fragments(ledger["cells"], ledger["classifications"], allowed, period_contexts)
        _need(_same(expected_mappings, trial["mappings"]) and _same(expected_retained, ledger["retained"]),
              "Mapping/raw/state/period/retention encoding differs from complete ledger")
        for candidate in trial["candidates"]:
            _need(type(candidate) is dict and set(candidate) == {"candidate_id", "document_ordinal", "physical_page",
                  "page_json_version_id", "section_id", "table_id", "status", "reasons", "mappings",
                  "closure_receipt", "component_regions"}, "Candidate fields")
            material = {k: v for k, v in candidate.items() if k != "candidate_id"}
            regions = [d["locator"] for d in ledger["dispositions"]]
            _need(candidate.get("candidate_id") == "gjf36ncv1:candidate:" + canonical_json_sha256_v1(material)
                  and _same(candidate.get("mappings"), trial["mappings"])
                  and _same(candidate.get("closure_receipt"), trial["notes_ledger"])
                  and candidate.get("status") == trial["status"]
                  and _same(candidate.get("reasons"), trial["reasons"])
                  and _same(candidate["component_regions"], regions)
                  and bool(regions) and all(candidate[k] == regions[0][k] for k in regions[0]), "Candidate identity/evidence")
        if trial["status"] == "READY":
            _need(bool(trial["mappings"]) and len(trial["candidates"]) == 1 and not trial["reasons"]
                  and trial["selected_candidate_id"] == trial["candidates"][0]["candidate_id"], "READY selection")
        else:
            _need(not trial["mappings"] and trial["selected_candidate_id"] is None and bool(trial["reasons"]), "U has mappings")
        for mapping in trial["mappings"]:
            material = {k: v for k, v in mapping.items() if k != "item_mapping_id"}
            _need(mapping.get("item_mapping_id") == "gjmthfmv1:item:" + canonical_json_sha256_v1(material)
                  and type(mapping.get("report_norm_id")) is int and mapping["report_norm_id"] > 0
                  and type(mapping.get("role")) is str and type(mapping.get("row_id")) is str
                  and type(mapping.get("source_refs")) is list and len(mapping["source_refs"]) == 2
                  and type(mapping.get("values")) is list and len(mapping["values"]) == 2
                  and type(mapping.get("period_axis")) is list and len(mapping["period_axis"]) == 2,
                  "Mapping codec/axes")
        validate_source_observation_mapping_contract_v1(trial["mappings"])
    expected = build_f36_notes_query_evidence_v1(trials=trials, compiled_specs=compiled_specs)
    _need(_same(expected, indexed_query_evidence), "Notes frontier/query binding")
    return canonical_clone_v1(trials)


def build_f36_notes_core_sweep_v1(*, corpus_manifest_index_id: str, topology_spec: Any, evaluation_spec: Any,
                                 schema_binding_spec: Any, trials: Any, indexed_query_evidence: Any,
                                 effective_page_frontier: Any = None) -> dict[str, Any]:
    _need(effective_page_frontier is None, "Effective source projection unsupported by notes V1")
    compiled = compile_f36_notes_core_specs_v1(topology_spec, evaluation_spec, schema_binding_spec)
    _need(type(corpus_manifest_index_id) is str and corpus_manifest_index_id.startswith("gjfccmiv1:index:")
          and corpus_manifest_index_id == topology_spec["source"]["corpus_identity"].get("corpus_manifest_index_id"), "Corpus ID")
    checked = validate_f36_notes_trials_v1(trials=trials, indexed_query_evidence=indexed_query_evidence, compiled_specs=compiled)
    material = {"format_version": FORMAT, "family_id": FAMILY, "claim_boundary": CLAIM,
                "state": "COMPLETE_DOCUMENT_F36_NOTES_STRICT_CORE_PROPOSAL_ONLY",
                "corpus_manifest_index_id": corpus_manifest_index_id,
                "specs": {name: {"value": canonical_clone_v1(value), "sha256": canonical_json_sha256_v1(value)}
                          for name, value in (("topology", topology_spec), ("evaluation", evaluation_spec), ("schema_binding", schema_binding_spec))},
                "indexed_query_evidence": canonical_clone_v1(indexed_query_evidence), "trials": checked,
                "metrics": {"document_count": len(checked), "mapping_count": sum(len(t["mappings"]) for t in checked),
                            "ready_count": sum(t["status"] == "READY" for t in checked), "not_observed_count": 0,
                            "unresolved_count": sum(t["status"] == "UNRESOLVED" for t in checked)}}
    return {**material, "sweep_id": "gjfafsv1:sweep:" + canonical_json_sha256_v1(material)}


def validate_f36_notes_core_sweep_v1(value: Any) -> dict[str, Any]:
    _need(type(value) is dict and value.get("format_version") == FORMAT and value.get("family_id") == FAMILY, "Sweep format/family")
    specs = value["specs"]
    rebuilt = build_f36_notes_core_sweep_v1(corpus_manifest_index_id=value["corpus_manifest_index_id"],
        topology_spec=specs["topology"]["value"], evaluation_spec=specs["evaluation"]["value"],
        schema_binding_spec=specs["schema_binding"]["value"], trials=value["trials"], indexed_query_evidence=value["indexed_query_evidence"])
    _need(_same(rebuilt, value), "Full notes sweep does not rebuild")
    return rebuilt


def replay_f36_notes_core_trials_from_source_v1(*, source_page_database: Path,
        selected_page_json_version_ids: Any, compiled_specs: dict[str, Any], indexed_query_evidence: Any) -> list[dict[str, Any]]:
    """Existing store's checked IO hook: rebuild actual notes, not stored decisions.

    Caller must also retain the existing held-source/SQLite integrity/code/final
    barriers. This function neither publishes nor supplies a financial grant.
    """
    compiled = compile_f36_notes_core_specs_v1(compiled_specs["topology"], compiled_specs["evaluation"], compiled_specs["schema"])
    _need(_same(compiled, compiled_specs), "Compiled notes authority changed")
    source_spec, evaluation = compiled["topology"]["source"], compiled["evaluation"]
    project_root = Path(__file__).resolve().parents[3]
    config_root = project_root / "config/notes"
    refs = [source_spec["index_ref"], source_spec["database_ref"], evaluation["primary_store_ref"],
            evaluation["production_policy_ref"], *evaluation["frontier_receipt_refs"].values(),
            {**source_spec["database_ref"], "path": str(source_page_database)}]
    refs += [{"path": str(config_root / key), "sha256": pin, "size_bytes": (config_root / key).stat().st_size}
             for key, pin in evaluation["notes_config_pins"].items()]
    before = []
    try:
        for ref in refs:
            path = Path(ref["path"])
            _need(path.is_absolute() and not any(p.is_symlink() for p in (path, *path.parents))
                  and path.is_file(), "Pinned replay input path")
            if path.suffix in {".sqlite3", ".sqlite", ".db"}:
                _need(not any(os.path.lexists(str(path) + suffix) for suffix in ("-wal", "-shm", "-journal")), "Replay DB sidecar")
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            status = os.fstat(fd)
            before.append((ref, path, fd, status))
            _need(stat.S_ISREG(status.st_mode) and status.st_size == ref["size_bytes"]
                  and _identity(status) == _identity(path.stat()) and _fd_sha(fd) == ref["sha256"]
                  and _identity(status) == _identity(os.fstat(fd)), "Pinned replay input changed")
        root = Path(source_spec["artifact_root"])
        policy_path = project_root / "config/families/tm-operating-expense-evaluation-v1.json"
        _need(Path(evaluation["production_policy_ref"]["path"]).resolve() == policy_path.resolve()
              and _same(json.loads(policy_path.read_bytes()), evaluation["production_policy"]), "Live F36 policy differs")
        corpus = load_corpus_selection_v1(name=source_spec["corpus_name"], root=root,
            index_relative_path=str(Path(source_spec["index_ref"]["path"]).relative_to(root)),
            expected_index_sha256=source_spec["index_ref"]["sha256"], expected_db_sha256=source_spec["database_ref"]["sha256"])
        versions = [p.page_json_version_id for d in corpus.documents for p in d.pages]
        _need(type(selected_page_json_version_ids) in {tuple, list} and list(selected_page_json_version_ids) == versions,
              "Replay selected VID frontier")
        _need(sha256_file(source_page_database) == source_spec["database_ref"]["sha256"], "Snapshot bytes")
        corpus = replace(corpus, db_path=Path(source_page_database))
        contexts = load_primary_context_v1(Path(evaluation["primary_store_ref"]["path"]), evaluation["primary_store_ref"]["sha256"])
        config = load_notes_config_v1(project_root)
        source = NotesSource(corpus, SourceMetrics())
        requested = set(compiled["topology"]["documents_requested"])
        policies = source.annual_policies_v1({n: c.scope for n, c in contexts.items() if n in requested})
        contexts = {n: replace(c, annual_policy=policies.get(n)) for n, c in contexts.items()}
        trials = rebuild_f36_notes_trials_v1(source=source, contexts=contexts, config=config, compiled_specs=compiled)
        validate_f36_notes_trials_v1(trials=trials, indexed_query_evidence=indexed_query_evidence, compiled_specs=compiled)
        _need(_same(load_notes_config_v1(project_root).pins, evaluation["notes_config_pins"]), "Late notes config changed")
        return trials
    finally:
        failures = []
        for ref, path, fd, status in before:
            try:
                if not (_identity(status) == _identity(os.fstat(fd)) == _identity(path.stat())
                        and _fd_sha(fd) == ref["sha256"] and _identity(status) == _identity(os.fstat(fd))):
                    failures.append(str(path))
                if path.suffix in {".sqlite3", ".sqlite", ".db"} and any(
                        os.path.lexists(str(path) + suffix) for suffix in ("-wal", "-shm", "-journal")):
                    failures.append(str(path) + ":sidecar")
            except OSError:
                failures.append(str(path))
            finally:
                os.close(fd)
        _need(not failures, "Replay held input changed before result escape: " + ",".join(failures))
