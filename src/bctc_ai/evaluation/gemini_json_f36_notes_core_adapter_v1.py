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
from collections import Counter, defaultdict
from dataclasses import replace
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import (
    _money,
    _normalized,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import _owner_visible
from bctc_ai.evaluation.gemini_json_operating_expense_original_inventory_v1 import _nodes
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    validate_source_observation_mapping_contract_v1,
)
from bctc_ai.notes.annual_policy_v1 import (
    PolicyCapture,
    PolicyPage,
    verify_annual_policy_v1,
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
    DocumentContext,
    NotesSource,
    canonical_period_key_v1,
    load_primary_context_v1,
    table_context_v1,
    year_ended_policy_v1,
    year_ended_shadow_v1,
)
from bctc_ai.notes.list_shape_v1 import owned_date_texts_v1
from bctc_ai.notes.root_closure_v1 import root_closure_v1
from bctc_ai.primary_statements.periods_v1 import (
    PeriodDescriptor,
    _role_from_end,
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
COMPACT_FORMAT = "GEMINI_JSON_F36_NOTES_STRICT_CORE_COMPACT_A_SWEEP_V1"
COMPACT_EVALUATION_FORMAT = "F36_NOTES_STRICT_CORE_COMPACT_A_EVALUATION_SPEC_V1"
COMPACT_QUERY_FORMAT = "F36_NOTES_REBUILT_COMPACT_A_SOURCE_FRONTIER_V1"
COMPACT_PARTITION_FORMAT = "F36_NOTES_FRESH_COMPACT_SOURCE_PARTITION_V1"
_NODE_DIGEST_DOMAIN = "CANONICAL_JSON_ONE_LF_OF_ORDERED_FULL_NODE_SHA256_TRIPLES_V1"
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
    compact = type(evaluation_spec) is dict and evaluation_spec.get("format_version") == COMPACT_EVALUATION_FORMAT
    for spec, version, fields in (
        (topology_spec, TOPOLOGY_FORMAT, {"format_version", "family_id", "source", "documents_requested"}),
        (evaluation_spec, COMPACT_EVALUATION_FORMAT if compact else EVALUATION_FORMAT,
                                            {"format_version", "family_id", "notes_config_pins",
                                             "notes_family", "production_policy", "production_policy_ref",
                                             "production_topology", "production_topology_ref",
                                             "production_schema_binding", "production_schema_binding_ref",
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
    _ref(evaluation_spec["production_topology_ref"])
    _ref(evaluation_spec["production_schema_binding_ref"])
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
    _need(type(policy.get("minimum_source_visible_root_component_count")) is int
          and policy["minimum_source_visible_root_component_count"] > 0
          and policy.get("owner_match_policy") == "EXACT_NORMALIZED_WITH_BOUNDED_SOURCE_SUFFIX"
          and type(policy.get("owner_surface_kinds")) is list
          and len(policy["owner_surface_kinds"]) == 2
          and set(policy["owner_surface_kinds"]) == {"SECTION_TITLE", "TABLE_TITLE"}, "Production owner/minimum policy")
    production_topology = evaluation_spec["production_topology"]
    production_schema = evaluation_spec["production_schema_binding"]
    _need(type(production_topology) is dict and production_topology.get("family_id") == FAMILY
          and type(production_topology.get("parent")) is dict
          and type(production_topology["parent"].get("aliases")) is list
          and bool(production_topology["parent"]["aliases"]), "Production owner topology")
    _need(type(production_schema) is dict and production_schema.get("family_id") == FAMILY
          and type(production_schema.get("role_bindings")) is list, "Production role binding schema")
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
    return {"engine_format_version": COMPACT_FORMAT if compact else FORMAT, "claim_boundary": CLAIM,
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


def _compact(compiled: dict[str, Any]) -> bool:
    _need(compiled["engine_format_version"] in {FORMAT, COMPACT_FORMAT}
          and compiled["evaluation"]["format_version"] == (COMPACT_EVALUATION_FORMAT
              if compiled["engine_format_version"] == COMPACT_FORMAT else EVALUATION_FORMAT), "Compiled inventory format pairing")
    return compiled["engine_format_version"] == COMPACT_FORMAT


def _source_key(value: Any, *, original: bool = False) -> tuple[str, str, str]:
    _need(type(value) is dict and type(value.get("page_json_version_id")) is str
          and re.fullmatch(r"gfpstorev1:json:[0-9a-f]{64}", value["page_json_version_id"]) is not None,
          "Compact required source VID missing/malformed")
    if original:
        _need(all(type(value.get(k)) is int and value[k] > 0 for k in ("section_ordinal", "table_ordinal")),
              "Compact required ORIGINAL table axis missing/malformed")
        return value["page_json_version_id"], f"s{value['section_ordinal']}", f"t{value['table_ordinal']}"
    _need(all(type(value.get(k)) is str and re.fullmatch(pattern, value[k]) is not None
              for k, pattern in (("section_id", r"s[1-9][0-9]*"), ("table_id", r"t[1-9][0-9]*"))),
          "Compact required table axis missing/malformed")
    return value["page_json_version_id"], value["section_id"], value["table_id"]


def _required_source_keys(dispositions: list[dict[str, Any]], cells: list[dict[str, Any]]) -> set[tuple[str, str, str]]:
    """ALL statuses and fragments, never only mapped/numeric/READY owners.

    A None bridge/original_cell remains verbatim in its rejected/held record;
    it supplies no guessed coordinate. A nonempty declared coordinate must bind.
    """
    keys = set()
    for disposition in dispositions:
        keys.add(_source_key(disposition["locator"]))
        _need(type(disposition.get("fragments")) is list and type(disposition.get("source_bridges")) is list,
              "Compact fragment/bridge axes missing")
        keys.update(_source_key(fragment) for fragment in disposition["fragments"])
        for bridge in disposition["source_bridges"]:
            if bridge is None:
                continue
            try:
                keys.add(_source_key(bridge, original=True))
            except F36NotesCoreAdapterError as error:
                raise F36NotesCoreAdapterError("COMPACT_PROOF_UNSUPPORTED_BRIDGE_AXIS: "
                    f"status={disposition.get('status')!r}; owner={disposition['locator']!r}; bridge={bridge!r}") from error
    for cell in cells:
        keys.add(_source_key(cell["locator"]))
        if cell.get("original_cell") is not None:
            keys.add(_source_key(cell["original_cell"], original=True))
    return keys


def _inventory_counts(inventory: dict[str, Any]) -> dict[str, Any]:
    """Literal source slots/types only; non-null is never a numeric or financial-unread grant."""
    types, slots, nulls, missing = Counter(), 0, 0, 0
    for row in inventory["rows"]:
        axis = row.get("value_axis")
        if axis is None:
            missing += 1
        else:
            slots += axis["count"]
            nulls += len(axis["null_column_ordinals"])
            types.update(axis["item_types"])
    return {"column": len(inventory["columns"]), "row": len(inventory["rows"]),
            "unsupported_shape": len(inventory["unsupported"]), "value_slots": slots,
            "null_slots": nulls, "non_null_slots": slots - nulls, "rows_without_value_axis": missing,
            "item_types": dict(sorted(types.items()))}


def _node_axis(nodes: list[dict[str, Any]]) -> list[list[str]]:
    return [[node["record_type"], node["pointer"], canonical_json_sha256_v1(node)] for node in nodes]


def _table_nodes(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    # Order belongs to the page node_axis, not this grouped inventory codec.
    table = {k: v for k, v in inventory["table"].items() if k != "page_json_version_id"}
    return [table, *inventory["columns"], *inventory["rows"], *inventory["unsupported"]]


def _table_axis(axis: list[list[str]], pointer: str) -> list[list[str]]:
    return [node for node in axis if node[1] == pointer or node[1].startswith(pointer + "/")]


def _compact_descriptor(key: tuple[str, str, str], inventory: dict[str, Any], axis: list[list[str]],
                        required: set[tuple[str, str, str]], subjects: list[list[str]]) -> dict[str, Any]:
    classification = classify_table_v1(inventory["table"], inventory["section"], {}, subjects)
    reasons = (["REQUIRED_SOURCE_DEPENDENCY"] if key in required else [])
    if classification.get("tag") == "POTENTIAL_CANDIDATE":
        reasons.append("POTENTIAL_CANDIDATE")
    if inventory["unsupported"]:
        reasons.append("UNSUPPORTED_TABLE")
    return {"table_key": list(key), "table": inventory["table"], "section": inventory["section"],
            "inventory_sha256": canonical_json_sha256_v1(inventory),
            "node_axis_sha256": canonical_json_sha256_v1(_table_axis(axis, inventory["table"]["pointer"])),
            "counts": _inventory_counts(inventory), "retention_reasons": reasons,
            "disposition": "FULL_INVENTORY_RETAINED" if reasons else "UNASSESSED_NOT_ABSENT"}


def _compact_page(page: dict[str, Any], *, doc: dict[str, Any], selected: dict[str, Any], blob_sha: str,
                  required: set[tuple[str, str, str]], subjects: list[list[str]]) -> tuple[dict[str, Any], dict]:
    """One fresh page only. Irrelevant full row graphs die before the next page."""
    nodes = list(_nodes(page))
    axis = _node_axis(nodes)
    inventories = _inventory(page, selected["page_json_version_id"], blob_sha)
    # V1's table helper deliberately only collects descendants. A malformed
    # table itself has a same-pointer unsupported node: compact A must retain it.
    for inv in inventories.values():
        inv["unsupported"].extend(node for node in nodes if node["record_type"] == "unsupported_shape"
                                  and node["pointer"] == inv["table"]["pointer"])
    descriptors, retained = [], {}
    for key, inv in inventories.items():
        descriptor = _compact_descriptor(key, inv, axis, required, subjects)
        descriptors.append(descriptor)
        if descriptor["retention_reasons"]:
            retained[key] = inv
    pointers = [d["table"]["pointer"] for d in descriptors]
    outside = [node for node in nodes if not any(node["pointer"] == p or node["pointer"].startswith(p + "/") for p in pointers)]
    result = {"axis": {"document_ordinal": doc["document_ordinal"], **selected},
              "source_sha256": doc["source_sha256"], "source_logical_name": doc["source_logical_name"],
              "stored_blob_two_lf_sha256": blob_sha, "page_object_one_lf_sha256": canonical_json_sha256_v1(page),
              "node_axis": axis, "node_axis_sha256": canonical_json_sha256_v1(axis),
              "node_counts": dict(sorted(Counter(n[0] for n in axis).items())),
              "outside_table_nodes": outside, "tables": descriptors}
    return result, retained


def _source_partition(doc: dict[str, Any], compiled: dict[str, Any], pages: list[dict[str, Any]]) -> dict[str, Any]:
    # The external neutral ref is retained provenance, not a substitute cache:
    # rebuild_f36_notes_trials_v1 decodes ALL requested pages afresh on every call.
    source = compiled["topology"]["source"]
    counts = Counter()
    for page in pages:
        counts.update(page["node_counts"])
        for table in page["tables"]:
            counts["full_tables" if table["retention_reasons"] else "unassessed_tables"] += 1
            for key in ("value_slots", "null_slots", "non_null_slots", "rows_without_value_axis"):
                counts[key] += table["counts"][key]
    return {"format_version": COMPACT_PARTITION_FORMAT, "digest_domain": _NODE_DIGEST_DOMAIN,
            "validation_boundary": "STRUCTURAL_NOT_AUTHENTICATED_FRESH_IO_REBUILD_REQUIRED",
            "scope": "FRESH_ALL_REQUESTED_DOCUMENT_PAGES" if doc["document_ordinal"] in compiled["topology"]["documents_requested"]
                     else "OUTSIDE_REQUESTED_SUBSET_NOT_EVALUATED",
            "source": {"document_ordinal": doc["document_ordinal"], "source_logical_name": doc["source_logical_name"],
                       "source_sha256": doc["source_sha256"], "index_ref": source["index_ref"],
                       "database_ref": source["database_ref"],
                       "external_neutral_ref": compiled["evaluation"]["frontier_receipt_refs"]["neutral_inventory"]},
            "pages": pages, "counts": dict(sorted(counts.items())),
            "ordered_universe_sha256": canonical_json_sha256_v1(pages)}


def _validate_compact_partition(ledger: dict[str, Any], doc: dict[str, Any], compiled: dict[str, Any],
                                inventories: dict[tuple[str, str, str], dict[str, Any]], subjects: list[list[str]]) -> None:
    """Checks declared partition consistency; omitted raw rows are authenticated ONLY by fresh IO replay."""
    proof = ledger["source_partition"]
    _need(type(proof) is dict and type(proof.get("pages")) is list
          and _same(proof, _source_partition(doc, compiled, proof["pages"])), "Compact source partition/source/digest drift")
    pages = proof["pages"]
    expected_pages = doc["pages"] if doc["document_ordinal"] in compiled["topology"]["documents_requested"] else []
    _need(_same([p.get("axis") for p in pages], [{"document_ordinal": doc["document_ordinal"], **p} for p in expected_pages]),
          "Compact complete selected-page axis missing/order")
    required = _required_source_keys(ledger["dispositions"], ledger["cells"])
    universe, kept = set(), set()
    for page in pages:
        _need(type(page) is dict and set(page) == {"axis", "source_sha256", "source_logical_name", "stored_blob_two_lf_sha256",
              "page_object_one_lf_sha256", "node_axis", "node_axis_sha256", "node_counts", "outside_table_nodes", "tables"},
              "Compact page fields")
        _need(page["source_sha256"] == doc["source_sha256"] and page["source_logical_name"] == doc["source_logical_name"]
              and all(type(page[k]) is str and _SHA.fullmatch(page[k]) for k in ("stored_blob_two_lf_sha256", "page_object_one_lf_sha256")),
              "Compact page source/BLOB domains")
        axis = page["node_axis"]
        _need(type(axis) is list and all(type(n) is list and len(n) == 3 and n[0] in
              {"section", "table", "column", "row", "unsupported_shape"} and type(n[1]) is str
              and type(n[2]) is str and _SHA.fullmatch(n[2]) for n in axis), "Compact node axis")
        _need(len({(n[0], n[1]) for n in axis}) == len(axis)
              and _same(page["node_axis_sha256"], canonical_json_sha256_v1(axis))
              and _same(page["node_counts"], dict(sorted(Counter(n[0] for n in axis).items()))), "Compact node digest/counts")
        _need(type(page["tables"]) is list and type(page["outside_table_nodes"]) is list, "Compact page partition lists")
        table_axes, pointers = [], []
        for descriptor in page["tables"]:
            _need(type(descriptor) is dict and set(descriptor) == {"table_key", "table", "section", "inventory_sha256",
                  "node_axis_sha256", "counts", "retention_reasons", "disposition"}, "Compact table descriptor")
            table = descriptor["table"]
            key = _source_key(table)
            _need(key[0] == page["axis"]["page_json_version_id"] and key not in universe
                  and _same(descriptor["table_key"], list(key)), "Compact duplicate/foreign table")
            pointer = f"/sections/{int(key[1][1:]) - 1}/tables/{int(key[2][1:]) - 1}"
            _need(table.get("pointer") == pointer and type(descriptor["inventory_sha256"]) is str
                  and _SHA.fullmatch(descriptor["inventory_sha256"]), "Compact table pointer/inventory digest")
            section_pointer = f"/sections/{int(key[1][1:]) - 1}"
            sections = [n for n in page["outside_table_nodes"] if n.get("record_type") == "section"
                        and n.get("pointer") == section_pointer]
            _need(len(sections) == 1 and _same(descriptor["section"], sections[0]), "Compact table/section source binding")
            universe.add(key)
            pointers.append(pointer)
            own_axis = _table_axis(axis, pointer)
            table_axes.extend(own_axis)
            _need(_same(descriptor["node_axis_sha256"], canonical_json_sha256_v1(own_axis))
                  and [n for n in own_axis if n[0] == "table"] == _node_axis([
                      {k: v for k, v in table.items() if k != "page_json_version_id"}]), "Compact table node proof")
            counts = descriptor["counts"]
            _need(type(counts) is dict and set(counts) == {"column", "row", "unsupported_shape", "value_slots", "null_slots",
                  "non_null_slots", "rows_without_value_axis", "item_types"}
                  and all(type(counts[k]) is int and counts[k] >= 0 for k in counts if k != "item_types")
                  and type(counts["item_types"]) is dict
                  and all(k in {"str", "int", "float", "bool", "NoneType", "list", "dict"}
                          and type(v) is int and v > 0 for k, v in counts["item_types"].items()), "Compact source counts typed")
            node_counts = Counter(n[0] for n in own_axis)
            _need(all(counts[k] == node_counts[k] for k in ("column", "row", "unsupported_shape"))
                  and sum(counts["item_types"].values()) == counts["value_slots"]
                  and counts["item_types"].get("NoneType", 0) == counts["null_slots"]
                  and counts["null_slots"] + counts["non_null_slots"] == counts["value_slots"]
                  and counts["rows_without_value_axis"] <= counts["row"], "Compact source count arithmetic")
            potential = classify_table_v1(table, descriptor["section"], {}, subjects).get("tag") == "POTENTIAL_CANDIDATE"
            reasons = (["REQUIRED_SOURCE_DEPENDENCY"] if key in required else [])
            if potential:
                reasons.append("POTENTIAL_CANDIDATE")
            if counts["unsupported_shape"]:
                reasons.append("UNSUPPORTED_TABLE")
            _need(_same(descriptor["retention_reasons"], reasons)
                  and descriptor["disposition"] == ("FULL_INVENTORY_RETAINED" if reasons else "UNASSESSED_NOT_ABSENT"),
                  "Compact required/potential/unsupported disposition")
            if reasons:
                _need(key in inventories, "Compact required source inventory missing")
                inv = inventories[key]
                _need(_same(descriptor, _compact_descriptor(key, inv, axis, required, subjects))
                      and _same(inv["page"], {"axis": {"page_json_version_id": key[0]},
                          "source_proof": {"stored_blob_two_lf_sha256": page["stored_blob_two_lf_sha256"]}})
                      and sorted(_node_axis(_table_nodes(inv))) == sorted(own_axis), "Compact FULL inventory/source node drift")
                kept.add(key)
        _need([n[1] for n in axis if n[0] == "table"] == pointers, "Compact missing/order table universe")
        outside = page["outside_table_nodes"]
        table_positions = {(n[0], n[1]) for n in table_axes}
        _need(all(not any(n["pointer"] == p or n["pointer"].startswith(p + "/") for p in pointers) for n in outside)
              and _same(_node_axis(outside), [n for n in axis if (n[0], n[1]) not in table_positions]),
              "Compact outside-table nodes lost")
    _need(required <= universe and set(inventories) == kept, "Compact required/full/universe partition incomplete")


# A notes member with no ReportNormId can still be a proven top-level component of the ROOT. These are explicit
# same-meaning bindings to the production SOURCE_ONLY root role, used ONLY to count the source frontier; they never
# create a canonical mapping. GOODWILL_AMORTIZATION (notes all_of "loi the thuong mai") = production
# GOODWILL_AMORTIZATION_SOURCE_ONLY (aliases "Phân bổ lợi thế thương mại", "Chi phí lợi thế thương mại", ...). Added
# only where actual FULL frontiers need it (2 ROOT-closed tables), never by label similarity at run time.
_SOURCE_ONLY_FRONTIER_ROLES = {"GOODWILL_AMORTIZATION": "GOODWILL_AMORTIZATION_SOURCE_ONLY"}


def _source_only_frontier_role(member: str, topology: dict[str, Any], configured: set[str]) -> str | None:
    """The bound production role, only if the live topology declares it a top-level ADDITIVE_CHILD root component."""
    role = _SOURCE_ONLY_FRONTIER_ROLES[member]
    children = [c for c in topology.get("children") or [] if type(c) is dict and c.get("role") == role]
    top_level = (len(children) == 1 and children[0].get("role_kind") == "ADDITIVE_CHILD"
                 and type(children[0].get("matchers")) is list and bool(children[0]["matchers"])
                 and all(type(m) is dict and m.get("within_role") is None for m in children[0]["matchers"]))
    return role if top_level and role in configured else None


def _production_table_policy_v1(inventory: dict[str, Any], disposition: dict[str, Any],
                                closure: dict[str, Any], compiled: dict[str, Any]) -> dict[str, Any]:
    """F36 owner and distinct configured SOURCE-frontier minimum, no value inference."""
    evaluation = compiled["evaluation"]
    policy = evaluation["production_policy"]
    aliases = policy.get("query_owner_aliases")
    if aliases is None:
        aliases = [*evaluation["production_topology"]["parent"]["aliases"], *policy.get("supplemental_owner_aliases", [])]

    def title(record):
        field = (record.get("fields") or {}).get("title_exact")
        return field["value"] if (type(field) is dict and set(field) == {"present", "value"}
                and type(field["present"]) is bool and field["present"]) else None

    section_title, table_title = title(inventory.get("section") or {}), title(inventory["table"])
    owner = _owner_visible({"title_exact": section_title}, {"title_exact": table_title}, compiled_specs={
        "query_policy": {"owner_surface_kinds": policy["owner_surface_kinds"],
                         "owner_match_policy": policy["owner_match_policy"],
                         "owner_aliases": [_normalized(alias) for alias in aliases]}})
    production_by_id = {b["report_norm_id"]: b["role"] for b in evaluation["production_schema_binding"]["role_bindings"]}
    notes_by_member = {}
    raw_family = evaluation["notes_family"]["raw"]
    for binding in compiled["schema"]["crosswalk"]:
        if binding["concept"] == raw_family["concept"] and binding["axis"] == raw_family["axis"]:
            for member in binding["members"]:
                notes_by_member.setdefault(member, set()).add(binding["report_norm_id"])
    configured = set(policy["root_component_roles"])
    frontier, reasons = [], []
    for row in closure.get("rows") or []:
        if row.get("class") != "FRONTIER":
            continue
        source_rows = [r for r in disposition["rows"] if r["row_id"] == f"r{row['row_ordinal']}"]
        _need(len(source_rows) == 1, "Production frontier source row ambiguous")
        member = source_rows[0]["line"]
        ids = notes_by_member.get(member, set())
        role = member if member in configured else (production_by_id.get(next(iter(ids))) if len(ids) == 1 else None)
        if role is None and member in _SOURCE_ONLY_FRONTIER_ROLES:
            role = _source_only_frontier_role(member, evaluation["production_topology"], configured)
        if role not in configured:
            reasons.append("F36_PRODUCTION_FRONTIER_ROLE_UNPROVEN")
        frontier.append({"row_ordinal": row["row_ordinal"], "notes_member": member, "production_role": role})
    roles = sorted({r["production_role"] for r in frontier if r["production_role"] in configured})
    if not owner:
        reasons.append("F36_PRODUCTION_ORIGINAL_OWNER_NOT_PROVEN")
    if len(roles) < policy["minimum_source_visible_root_component_count"]:
        reasons.append("F36_PRODUCTION_ROOT_COMPONENT_MINIMUM_NOT_MET")
    return {"format_version": "F36_NOTES_PRODUCTION_TABLE_POLICY_V1", "source_owner_surfaces": {
                "SECTION_TITLE": section_title, "TABLE_TITLE": table_title},
            "source_frontier": frontier, "distinct_configured_root_roles": roles,
            "minimum_source_visible_root_component_count": policy["minimum_source_visible_root_component_count"],
            "reasons": sorted(set(reasons))}


def _annual_capture_json_v1(capture: PolicyCapture) -> dict[str, Any]:
    """Transport the fixed immutable capture axes as native JSON lists."""
    _need(type(capture) is PolicyCapture and all(type(page) is PolicyPage for page in capture.pages),
          "Annual transport requires a typed capture")
    return canonical_clone_v1({"binding": list(capture.binding),
        "frontier": [list(item) for item in capture.frontier],
        "pages": [{"page_json_version_id": page.page_json_version_id, "physical_page": page.physical_page,
            "original_blob_sha256": page.original_blob_sha256, "replay_receipt_id": page.replay_receipt_id,
            "narratives": [list(item) for item in page.narratives], "narratives_sha256": page.narratives_sha256}
            for page in capture.pages]})


def _annual_context_v1(payload: Any, doc: dict[str, Any], primary_texts: list[str]) -> dict[str, Any] | None:
    """Recheck a serialized capture's consistency only; checked IO must rebuild it.

    This does not authenticate a deserialized capture or its narrative pixels.
    Fresh reconstruction serializes the actual collector capture, and checked
    source replay compares the entire trial, including this payload, exactly.
    """
    if payload is None:
        return None
    _need(type(payload) is dict and set(payload) == {"capture", "owned_table_texts"}, "Annual context fields")
    raw = payload["capture"]
    _need(type(raw) is dict and set(raw) == {"binding", "frontier", "pages"}
          and type(raw["binding"]) is list and len(raw["binding"]) == 4
          and _same(raw["binding"][:3], [doc["document_ordinal"], doc["source_logical_name"], doc["source_sha256"]])
          and raw["binding"][3] in {"SEPARATE", "CONSOLIDATED"}
          and type(raw["frontier"]) is list and type(raw["pages"]) is list, "Annual document binding")
    _need(all(type(p) is list and len(p) == 2 and type(p[0]) is str and type(p[1]) is int and p[1] >= 0
              for p in raw["frontier"])
          and [p[0] for p in raw["frontier"]] == [p["page_json_version_id"] for p in doc["pages"]],
          "Annual complete selected frontier")
    pages = []
    for page in raw["pages"]:
        _need(type(page) is dict and set(page) == {"page_json_version_id", "physical_page", "original_blob_sha256",
              "replay_receipt_id", "narratives", "narratives_sha256"}
              and type(page["physical_page"]) is int
              and {"physical_page": page["physical_page"], "page_json_version_id": page["page_json_version_id"]} in doc["pages"]
              and type(page["replay_receipt_id"]) is str and bool(page["replay_receipt_id"])
              and type(page["narratives"]) is list
              and all(type(n) is list and len(n) == 2 and all(type(s) is str for s in n) for n in page["narratives"]),
              "Annual captured page fields")
        pages.append(PolicyPage(page["page_json_version_id"], page["physical_page"], page["original_blob_sha256"],
            page["replay_receipt_id"], tuple(tuple(n) for n in page["narratives"]), page["narratives_sha256"]))
    capture = PolicyCapture(tuple(raw["binding"]), tuple(tuple(p) for p in raw["frontier"]), tuple(pages))
    # Verification is repeated at each fallback by the existing kernel grant.
    # Unresolved captures stay evidence; they never become a granted status flag.
    verify_annual_policy_v1(capture, capture.binding)
    tables = {}
    _need(type(payload["owned_table_texts"]) is list, "Annual owned table axis")
    selected = {p["page_json_version_id"] for p in doc["pages"]}
    for item in payload["owned_table_texts"]:
        _need(type(item) is dict and set(item) == {"table", "texts"} and type(item["table"]) is list
              and len(item["table"]) == 3 and item["table"][0] in selected
              and all(type(s) is str for s in item["table"]) and type(item["texts"]) is list
              and all(type(t) is str for t in item["texts"]), "Annual table context")
        key = tuple(item["table"])
        _need(key not in tables, "Annual duplicate table context")
        tables[key] = statement_period_context_v1(item["texts"])
    document = DocumentContext(doc["document_ordinal"], doc["document_identity"]["document_plan_id"],
        doc["source_logical_name"], doc["source_sha256"], raw["binding"][3],
        "STRUCTURAL_CAPTURE_ONLY_AUTHENTICATION_REQUIRES_FRESH_IO", None, [], [], {},
        income_context_texts=primary_texts, annual_policy=capture)
    return {"document": document, "tables": tables}


def _annual_lane_v1(cell: dict[str, Any], descriptor: Any, report_context: Any,
                    annual: dict[str, Any] | None) -> Any:
    basis = cell.get("period_basis")
    if type(basis) is not str or not basis.startswith("PRINTED_YEAR_ENDED_WITH_DOCUMENT_ANNUAL_POLICY:"):
        return descriptor
    blocked = PeriodDescriptor("UNRESOLVED", None, None, "UNRESOLVED", (), (cell["header_text"],),
                               "DOCUMENT_ANNUAL_POLICY_NOT_REPROVEN")
    if annual is None:
        return blocked
    loc = cell["locator"]
    own = annual["tables"].get((loc["page_json_version_id"], loc["section_id"], loc["table_id"]))
    if own is None or annual["document"].scope != cell["scope"]:
        return blocked
    granted, _why = year_ended_policy_v1(cell["header_text"], annual["document"], own)
    ended = year_ended_shadow_v1(cell["header_text"])
    if (granted is None or ended is None or granted != (cell["period_key"], cell["period_basis"])):
        return blocked
    if (report_context.conflict or not report_context.reporting_date
            or report_context.reporting_date[5:] != "12-31"):
        return blocked
    role = _role_from_end(ended, report_context)
    if role not in {"CURRENT", "COMPARATIVE"}:
        return blocked
    return PeriodDescriptor("DURATION", role, granted[0], "CONTEXT_BOUND",
        (("grain", "YEAR"), ("end", ended), ("annual_policy_basis", granted[1])),
        (cell["header_text"], granted[1]))


# Fixed calendar quarter windows (month-day). Used ONLY to check an explicitly printed lane window against a printed
# "Quý q năm y" report frame that prints no reporting date; never to create a period key or a reporting date.
_QUARTER_START = {1: "01-01", 2: "04-01", 3: "07-01", 4: "10-01"}
_QUARTER_END = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}


def _quarter_frame_lane_v1(descriptor: Any, context: Any) -> Any:
    """CURRENT / COMPARATIVE of an EXPLICIT printed window under a printed quarter frame, else the descriptor unchanged.

    The window must end on the frame quarter's calendar end in the frame year (CURRENT) or the prior year
    (COMPARATIVE), and be that year-to-date, that quarter alone, or 3 / 3q months ended. Any printed evidence of a
    non-calendar fiscal year, a printed reporting date, or a conflicting frame leaves the role unresolved.
    """
    if (descriptor.basis != "DURATION" or descriptor.role is not None or descriptor.key is None
            or descriptor.resolution != "EXPLICIT"):
        return descriptor
    quarter, year = context.quarter, context.year
    if (context.conflict or context.reporting_date or type(quarter) is not int or quarter not in _QUARTER_END
            or type(year) is not int or context.first_months_of_fiscal_year
            or (context.fiscal_year_end and context.fiscal_year_end[5:] != "12-31")
            or (context.range_start and context.range_start[5:] != "01-01")
            or context.months not in (None, 3, 3 * quarter)):
        return descriptor
    fields = dict(descriptor.fields)
    end = fields.get("end")
    if type(end) is not str or len(end) != 10 or end[5:] != _QUARTER_END[quarter]:
        return descriptor
    if fields.get("grain") == "RANGE" and type(fields.get("start")) is str and fields["start"][:4] == end[:4] \
            and fields["start"][5:] in {"01-01", _QUARTER_START[quarter]}:
        shape = f"RANGE:{fields['start'][5:]}..{end[5:]}"
    elif fields.get("grain") == "MONTHS_ENDED" and fields.get("months") in {3, 3 * quarter}:
        shape = f"MONTHS_ENDED:{fields['months']}:{end[5:]}"
    else:
        return descriptor
    role = {year: "CURRENT", year - 1: "COMPARATIVE"}.get(int(end[:4]))
    if role is None:
        return descriptor
    return PeriodDescriptor("DURATION", role, descriptor.key, "QUARTER_FRAME_BOUND",
                            descriptor.fields + (("quarter_frame", f"Q{quarter}:{year}"), ("window_shape", shape)),
                            descriptor.evidence + context.evidence)


def _fragments(cells: list[dict[str, Any]], records: list[dict[str, Any]],
               allowed_units: set[str], period_contexts: dict[int, Any],
               table_policies: dict[tuple[str, str, str], dict[str, Any]],
               production_schema: dict[str, Any],
               annual_contexts: dict[int, Any] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Encoding only. Inputs must be freshly recomputed by rebuild_f36_notes_trials_v1."""
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    retained = []
    for cell, record in zip(cells, records, strict=True):
        _need(_same(record.get("cell"), cell), "Full cell/classification binding")
        loc = cell["locator"]
        table_policy = table_policies.get((loc["page_json_version_id"], loc["section_id"], loc["table_id"]))
        _need(type(table_policy) is dict and type(table_policy.get("reasons")) is list, "Fresh production table policy missing")
        if table_policy["reasons"]:
            retained.append({"classification": record, "adapter_disposition": "F36_PRODUCTION_TABLE_POLICY_BLOCKED",
                             "policy_reasons": canonical_clone_v1(table_policy["reasons"])})
            continue
        if record["class"] != "CORE_CANDIDATE":
            retained.append({"classification": record, "adapter_disposition": "RETAINED_NOT_CANONICAL"})
            continue
        _need(cell.get("acceptance") == "ACCEPTED" and record.get("lane_closure") == "ROOT_CLOSED"
              and type(record.get("exact_rnid_binding")) is int
              and record["exact_rnid_binding"] == cell.get("report_norm_id")
              and cell.get("observation_state") in {"VALUE", "PRINTED_ZERO"}
              and cell.get("scope") in {"SEPARATE", "CONSOLIDATED"}, "Core structural conditions")
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
        roles = [binding["role"] for binding in production_schema["role_bindings"]
                 if binding["report_norm_id"] == key[5]]
        if production_schema["family_root_report_norm_id"] == key[5]:
            roles.append("FAMILY_ROOT_TOTAL")
        if not roles:
            reason = "F36_CANONICAL_RNID_ROLE_UNDECLARED"
        elif len(roles) != 1:
            reason = "F36_CANONICAL_RNID_ROLE_AMBIGUOUS"
        elif len(own) != 2 or len({c["period_key"] for c in own}) != 2:
            reason = "EXPLICIT_TWO_LANE_PAIR_NOT_PROVEN"
        elif key[-1] not in allowed_units:
            reason = "UNIT_OUTSIDE_DECLARED_F36_BINDINGS"
        values = []
        periods = []
        if reason is None:
            for cell in own:
                descriptor = duration_lane_period_v1(cell["header_text"], period_contexts[cell["document_ordinal"]])
                descriptor = _annual_lane_v1(cell, descriptor, period_contexts[cell["document_ordinal"]],
                    (annual_contexts or {}).get(cell["document_ordinal"]))
                descriptor = _quarter_frame_lane_v1(descriptor, period_contexts[cell["document_ordinal"]])
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
            framed = [p for p in periods if p["resolution"] == "QUARTER_FRAME_BOUND"]
            if reason is None and framed and (len(framed) != len(periods)
                                              or len({p["fields"]["window_shape"] for p in framed}) != 1):
                reason = "SOURCE_PERIOD_QUARTER_FRAME_SHAPES_DIFFER"
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
        material = {"report_norm_id": key[5], "role": roles[0], "notes_member": key[4], "row_id": key[3], "source_refs": refs,
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
    annual_payloads = {}
    for doc in topo["source"]["document_axis"]:
        ordinal = doc["document_ordinal"]
        context = contexts.get(ordinal)
        if (ordinal not in requested or context is None or context.scope not in {"SEPARATE", "CONSOLIDATED"}
                or type(context.annual_policy) is not PolicyCapture):
            continue
        table_texts = []
        for result in run.evaluations:
            table = result.table
            if table.document_ordinal == ordinal:
                table_texts.append({"table": [table.page_json_version_id, table.section_id, table.table_id],
                    "texts": owned_date_texts_v1(table, table_context_v1(table, []))})
        annual_payloads[ordinal] = canonical_clone_v1({"capture": _annual_capture_json_v1(context.annual_policy),
                                                      "owned_table_texts": table_texts})
    inventories = {}
    compact = _compact(compiled)
    required = _required_source_keys(dispositions, run.cells) if compact else set()
    compact_pages = defaultdict(list)
    subjects = config.families[FAMILY].raw["subjects"]["OPERATING_EXPENSE_NOTE"]["any"]
    # Bounded per-page parsing; no whole-corpus ORIGINAL object cache.
    for doc in source.corpus.documents:
        if doc.ordinal not in requested:
            continue
        for selected in doc.pages:
            loaded = source._load_originals([selected.page_json_version_id])[selected.page_json_version_id]
            _need((loaded["source_sha256"], loaded["source_logical_name"], loaded["physical_page"])
                  == (doc.source_sha256, doc.relative_path, selected.physical_page), "Original source identity")
            blob = loaded["source_json_replay_receipt"]["canonical_json_sha256"]
            if compact:
                descriptor, kept = _compact_page(loaded["page_json"], doc=topo["source"]["document_axis"][doc.ordinal - 1],
                    selected={"physical_page": selected.physical_page, "page_json_version_id": selected.page_json_version_id},
                    blob_sha=blob, required=required, subjects=subjects)
                compact_pages[doc.ordinal].append(descriptor)
                inventories.update(kept)
            else:
                inventories.update(_inventory(loaded["page_json"], selected.page_json_version_id, blob))
    if compact:
        _need(required <= set(inventories), "Compact required source inventory missing after fresh scan")
    closure_by_table, policy_by_table, rows = {}, {}, {}
    for loc, inventory in inventories.items():
        for row in inventory["rows"]:
            rows[(loc[0], int(loc[1][1:]), int(loc[2][1:]), row["row_ordinal"])] = row
    for disposition in dispositions:
        loc = disposition["locator"]
        key = (loc["page_json_version_id"], loc["section_id"], loc["table_id"])
        if key in inventories:
            closure_by_table[key] = root_closure_v1(inventories[key], disposition, config.families[FAMILY])
            policy_by_table[key] = _production_table_policy_v1(inventories[key], disposition, closure_by_table[key], compiled)
    bindings = exact_rnid_bindings_v1(run.cells, config.crosswalk)
    records = []
    for cell, binding in zip(run.cells, bindings, strict=True):
        loc = cell["locator"]
        closure = closure_by_table.get((loc["page_json_version_id"], loc["section_id"], loc["table_id"]))
        records.append(classify_observation_v1(cell, binding, closure, rows))
    allowed_units = {u["canonical_unit"] for u in evaluation["production_policy"]["money_unit_bindings"] if u["accepted"] is True}
    period_contexts = {n: statement_period_context_v1(c.income_context_texts) for n, c in contexts.items()}
    annual_contexts = {doc["document_ordinal"]: _annual_context_v1(annual_payloads.get(doc["document_ordinal"]), doc,
                          contexts[doc["document_ordinal"]].income_context_texts)
                       for doc in topo["source"]["document_axis"] if doc["document_ordinal"] in annual_payloads}
    trials = []
    for doc in topo["source"]["document_axis"]:
        ordinal = doc["document_ordinal"]
        own_indices = [i for i, c in enumerate(run.cells) if c["document_ordinal"] == ordinal]
        own_cells, own_records = [run.cells[i] for i in own_indices], [records[i] for i in own_indices]
        mappings, retained = _fragments(own_cells, own_records, allowed_units, period_contexts, policy_by_table,
                                        evaluation["production_schema_binding"], annual_contexts)
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
                  "production_policy_receipts": [{"table": list(k), "receipt": v} for k, v in policy_by_table.items()
                      if k[0] in page_ids],
                  "primary_income_context_texts": contexts[ordinal].income_context_texts if ordinal in requested and ordinal in contexts else [],
                  "scope": "REQUESTED_F36_NOTES_DOCUMENT" if ordinal in requested else "NOT_EVALUATED_REQUESTED_SUBSET_ONLY"}
        if compact:
            ledger["source_partition"] = _source_partition(doc, compiled, compact_pages[ordinal])
        if ordinal in annual_payloads:
            ledger["annual_period_context"] = annual_payloads[ordinal]
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
    material = {"format_version": COMPACT_QUERY_FORMAT if _compact(compiled_specs) else QUERY_FORMAT, "family_id": FAMILY,
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
        base_fields = {"cells", "classifications", "retained", "dispositions", "root_closures",
                       "source_ledger", "production_policy_receipts", "primary_income_context_texts", "scope"}
        if _compact(compiled_specs):
            base_fields.add("source_partition")
        _need(set(ledger) in (base_fields, base_fields | {"annual_period_context"})
              and all(type(ledger[k]) is list for k in base_fields - {"scope", "source_partition"})
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
        if _compact(compiled_specs):
            _validate_compact_partition(ledger, doc, compiled_specs, inventories,
                family.raw["subjects"]["OPERATING_EXPENSE_NOTE"]["any"])
        closures, policies = {}, {}
        for disposition in ledger["dispositions"]:
            loc = disposition["locator"]
            key = (loc["page_json_version_id"], loc["section_id"], loc["table_id"])
            if key in inventories:
                _need(key not in closures, "Duplicate disposition")
                closures[key] = root_closure_v1(inventories[key], disposition, family)
                policies[key] = _production_table_policy_v1(inventories[key], disposition, closures[key], compiled_specs)
        expected_closures = [{"table": list(k), "closure": v} for k, v in closures.items()]
        _need(_same(expected_closures, ledger["root_closures"]), "ROOT proof does not recompute")
        _need(_same([{"table": list(k), "receipt": v} for k, v in policies.items()], ledger["production_policy_receipts"]),
              "Production owner/frontier policy does not recompute")
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
        annual = _annual_context_v1(ledger.get("annual_period_context"), doc, ledger["primary_income_context_texts"])
        expected_mappings, expected_retained = _fragments(ledger["cells"], ledger["classifications"], allowed, period_contexts, policies,
                                                         compiled_specs["evaluation"]["production_schema_binding"],
                                                         {doc["document_ordinal"]: annual})
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
    material = {"format_version": compiled["engine_format_version"], "family_id": FAMILY, "claim_boundary": CLAIM,
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
    _need(type(value) is dict and value.get("format_version") in {FORMAT, COMPACT_FORMAT}
          and value.get("family_id") == FAMILY, "Sweep format/family")
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
            evaluation["production_policy_ref"], evaluation["production_topology_ref"], evaluation["production_schema_binding_ref"],
            *evaluation["frontier_receipt_refs"].values(),
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
        for field, filename in (("production_topology", "tm-operating-expense-topology-v1.json"),
                                ("production_schema_binding", "tm-operating-expense-schema-binding-v1.json")):
            path = project_root / "config/families" / filename
            _need(Path(evaluation[field + "_ref"]["path"]).resolve() == path.resolve()
                  and _same(json.loads(path.read_bytes()), evaluation[field]), "Live F36 topology/schema differs")
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
