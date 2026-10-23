"""F36 exact held-row joins; this pure module grants no IO/visual authority."""
from __future__ import annotations

import re
from hashlib import sha256

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1 as clone,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_sha256_v1 as digest,
)
from bctc_ai.source_structure.contracts_v1 import (
    same_typed_json_v1 as same,
)

FORMAT = "F36_AUTHENTICATED_UNRESOLVED_PRINTED_FRONTIER_DISPOSITIONS_V1"
RESULT = "F36_UNRESOLVED_ROW_DISPOSITION_RECONCILIATION_V1"
DISPOSITION = "HELD_BY_AUTHENTICATED_UNRESOLVED_PRINTED_FRONTIER"
KINDS = {"PRINTED_CONTRADICTION", "INCOMPLETE_PRINTED_FRONTIER"}
AXES = ("source_row_axis", "candidate_table_total_row_axis", "raw_target_like_row_axis")
LOCATOR = ("document_id", "document_ordinal", "source_logical_name", "source_sha256",
           "page_json_version_id", "physical_page", "selected_page_ordinal", "section_id", "table_id")


class UnresolvedRowsV1Error(ValueError):
    pass


def need(ok, message):
    if not ok:
        raise UnresolvedRowsV1Error(message)


def positive(value):
    return type(value) is int and value > 0


def reference(value):
    need(type(value) is dict and set(value) == {"path", "sha256", "size_bytes"}
         and type(value["path"]) is str and value["path"]
         and type(value["sha256"]) is str and re.fullmatch("[0-9a-f]{64}", value["sha256"])
         and positive(value["size_bytes"]), "invalid review reference")


def validate_declaration_v1(value):
    need(type(value) is dict and set(value) == {"format_version", "family_id", "corpus_manifest_index_id",
         "raw_coverage_receipt_id", "pdf_residual_spec_ref", "reviews"}
         and value["format_version"] == FORMAT and value["family_id"] == "OPERATING_EXPENSE"
         and type(value["reviews"]) is list and value["reviews"], "invalid row disposition declaration")
    reference(value["pdf_residual_spec_ref"])
    ordinals = []
    fields = {"document", "source_size_bytes", "status", "reasons", "trial_sha256", "query_cluster_sha256",
              "pdf_residual_audit_id", "manual_review_ref", "manual_finding_id", "finding_kind",
              "printed_frontier", "held_rows", "disposition"}
    for review in value["reviews"]:
        need(type(review) is dict and set(review) == fields, "invalid row review fields")
        doc = review["document"]
        need(type(doc) is dict and set(doc) == set(LOCATOR[:4]) and positive(doc["document_ordinal"])
             and positive(review["source_size_bytes"]) and review["status"] == "UNRESOLVED_GEMINI_JSON_FAMILY"
             and type(review["reasons"]) is list and review["reasons"]
             and all(type(item) is str and item for item in review["reasons"])
             and review["finding_kind"] in KINDS and review["disposition"] == DISPOSITION,
             "invalid unresolved review identity/type")
        reference(review["manual_review_ref"])
        need(type(review["held_rows"]) is list and review["held_rows"], "empty held-row review")
        for item in review["held_rows"]:
            need(type(item) is dict and set(item) == {"axis_name", "raw_coverage_item_sha256"}
                 and item["axis_name"] in AXES, "invalid held-row declaration")
        need(len({digest(item) for item in review["held_rows"]}) == len(review["held_rows"]), "duplicate held row")
        ordinals.append(doc["document_ordinal"])
    need(ordinals == sorted(set(ordinals)), "review documents duplicate or unordered")
    return clone(value)


def validate_raw_coverage_v1(value):
    """Structural validation only. IO/source authority belongs to the runner."""
    need(type(value) is dict and value.get("family_id") == "OPERATING_EXPENSE"
         and value.get("format_version") == "OPERATING_EXPENSE_SOURCE_ROW_COVERAGE_V1", "wrong raw coverage")
    need(set(value) == {"family_id", "format_version", "receipt_id", "violation_axis", "violation_count",
         "source_row_disposition_counts", "candidate_table_total_disposition_counts", "raw_target_like_disposition_counts",
         *AXES, *(name + "_sha256" for name in AXES)}, "unexpected raw coverage fields")
    for name in AXES:
        need(type(value.get(name)) is list and value.get(name + "_sha256") == digest(value[name]), "raw coverage axis drift")
        need(len({digest(item) for item in value[name]}) == len(value[name]), "duplicate raw coverage item")
    violations = {}
    count_names = ("source_row_disposition_counts", "candidate_table_total_disposition_counts", "raw_target_like_disposition_counts")
    for name, count_name in zip(AXES, count_names, strict=True):
        counts = {}
        for item in value[name]:
            need(type(item) is dict and type(item.get("coverage")) is str, "invalid raw coverage row")
            for key in ("document_ordinal", "physical_page", "row_ordinal"):
                need(positive(item.get(key)), "noninteger raw coverage coordinate")
            counts[item["coverage"]] = counts.get(item["coverage"], 0) + 1
            if item["coverage"].startswith("VIOLATION_"):
                violations[digest(item)] = item
        need(same(value.get(count_name), counts), "raw coverage counts drift")
    need(same(value.get("violation_axis"), [violations[key] for key in sorted(violations)])
         and type(value.get("violation_count")) is int and value["violation_count"] == len(violations), "raw violation inventory drift")
    need(value.get("receipt_id") == "gjoefav1:source-row-coverage:" + digest(
        {k: v for k, v in value.items() if k != "receipt_id"}), "raw coverage seal drift")
    return clone(value)


def _numeric(family, value):
    need(type(value) is str and value == value.strip(), "numeric frontier cell must be literal numeric")
    body = value[1:-1] if value.startswith("(") and value.endswith(")") else value
    need(re.fullmatch(r"-?(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+|[0-9]{1,3}(?:\.[0-9]{3})+)", body),
         "DASH/annotation/unsupported numeric frontier cell")
    cell = family._source_money(value)
    need(type(cell.get("coefficient")) is int, "frontier number unproven")
    return cell["coefficient"]


def build_printed_frontier_v1(*, document, page_axis, pages, cluster, compiled_specs, source_page_blob_refs):
    """Initial scope: one original NOTE table, closed continuation, unchanged projection.

    All rows and hierarchy are retained. Existing extraction supplies positive
    owner/unit/period gates; top-level operand membership is source-hierarchical,
    never chosen by amounts. Unsupported shapes remain errors, not exemptions.
    """
    from bctc_ai.evaluation import gemini_json_operating_expense_family_v1 as family

    regions = cluster.get("component_regions")
    need(type(regions) is list and len(regions) == 1, "only one complete original table is supported")
    region = regions[0]
    need(all(positive(region.get(k)) for k in ("document_ordinal", "physical_page", "selected_page_ordinal")), "invalid frontier locator")
    matches = [axis for axis in page_axis if axis["page_json_version_id"] == region["page_json_version_id"]]
    need(len(matches) == 1 and same({k: region[k] for k in LOCATOR[:7]}, matches[0])
         and same({k: region[k] for k in LOCATOR[:4]}, document), "frontier source axis mismatch")
    original = pages[region["page_json_version_id"]]
    blob_ref = source_page_blob_refs.get(region["page_json_version_id"])
    raw_blob = canonical_json_bytes_v1(original) + b"\n"
    need(type(blob_ref) is dict and blob_ref == {
        "page_json_version_id": region["page_json_version_id"], "stored_blob_sha256": sha256(raw_blob).hexdigest(),
        "stored_blob_size_bytes": len(raw_blob), "original_object_sha256": digest(original)},
        "missing/wrong original BLOB versus object domain")
    private, _repairs = family._apply_authenticated_source_repairs(pages=pages, regions=regions, compiled_specs=compiled_specs)
    page = private[region["page_json_version_id"]]
    need(same(page, original), "changed source domain requires separate authenticated coordinate support")
    section, table = family._source_table(page, section_id=region["section_id"], table_id=region["table_id"])
    need(section.get("content_kind") == "FINANCIAL_NOTE" and section.get("statement_type") == "NOT_APPLICABLE"
         and table.get("continuation") == "NONE", "wrong owner or open continuation")
    qualified = family._qualified_provision_literal_receipts_v1(
        table=table, original_table=table, locator={k: region[k] for k in LOCATOR}, compiled_specs=compiled_specs)
    need(all(item.get("complete") is True for item in qualified), "unproven whole qualified provision literal")
    payroll = family._literal_payroll_scope_receipts_v1(
        table=table, original_table=table, locator={k: region[k] for k in LOCATOR}, compiled_specs=compiled_specs)
    need(all(item.get("complete") is True for item in payroll), "unproven family-local payroll population")
    extracted = family._extract_table_local_records(
        page_json=page, section=section, table=table, region=region, compiled_specs=compiled_specs,
        document_unit_context=family._document_unit_context_axis(pages, compiled_specs=compiled_specs),
        document_period_context={}, prior_fragment=None)
    facts = extracted["receipt"]
    classification, lane, unit = facts["classification"], facts["lane_axis"], facts["unit_axis"]
    need(extracted.get("unconsumed_reason") is None and classification.get("owner_visible") is True
         and classification.get("family_presence_anchor_visible") is True
         and not classification.get("ambiguous_rows") and classification.get("typed_control_disposition") is None
         and lane.get("complete") is True and unit.get("complete") is True, "unproven owner/unit/period/population")
    cols = lane.get("money_column_ordinals")
    need(type(cols) is list and len(cols) == 2 and len(set(cols)) == 2 and all(positive(c) for c in cols), "frontier needs exact two columns")
    rows = table["rows"]
    need(rows and rows[-1].get("row_kind") == "TOTAL"
         and type(rows[-1].get("values_exact")) is list and len(rows[-1]["values_exact"]) == len(table["columns"])
         and classification.get("total_rows") == [{"row_kind": "TOTAL", "row_ordinal": len(rows), "source_order": len(rows)}],
         "unique terminal printed total required")
    roles = {}
    for hit in classification.get("role_hits", []):
        roles.setdefault(hit["row_ordinal"], set()).add(hit["role"])
    need(compiled_specs["evaluation"].get("root_component_equation_policy") == "DECLARED_DIRECT_SUM"
         and compiled_specs["evaluation"].get("direct_frontier_policy")
         == "CANONICAL_PROVEN_OR_CONTIGUOUS_NUMBERED_TOP_LEVEL_DIRECT_FRONTIER", "unsupported direct-frontier policy")
    operands, dependency, parent_labels, numbered, operand_roles = [], [], {}, [], []
    owner_aliases = family._parent_aliases(compiled_specs)
    for ordinal, row in enumerate(rows[:-1], 1):
        need(type(row.get("values_exact")) is list and len(row["values_exact"]) == len(table["columns"]), "raw width mismatch")
        label = family._normalized(row.get("label_exact"))
        path = [family._without_leading_ordinal(family._normalized(v)) for v in row.get("hierarchy_path_exact", []) if family._normalized(v)]
        if path and path[0] in owner_aliases:
            path = path[1:]
        label = family._without_leading_ordinal(label)
        if row.get("row_kind") == "GROUP" and label in {"trong do", "bao gom"} and all(v is None for v in row["values_exact"]):
            continue
        need(label and path and path[-1] == label and len(roles.get(ordinal, set())) == 1, "unknown/unclassified frontier row")
        if len(path) == 1:
            printed = re.fullmatch(r"([1-9][0-9]*)\. ([^\r\n]+)", row.get("label_exact", ""))
            need(printed is not None and printed[1] == str(len(operands) + 1), "top-level source numbering is not contiguous ASCII1..N")
            role = next(iter(roles[ordinal]))
            need(role in compiled_specs["root_component_roles"] and role not in operand_roles,
                 "top-level operand is not a unique configured root component")
            need(label not in parent_labels, "duplicate top-level operand")
            operands.append(ordinal)
            operand_roles.append(role)
            numbered.append({"row_ordinal": ordinal, "printed_number_exact": printed[1],
                             "raw_label_exact": row["label_exact"], "label_without_number_exact": printed[2], "role": role})
            parent_labels[label] = ordinal
        else:
            need(len(path) == 2 and path[0] in parent_labels, "missing/ambiguous source parent")
        dependency.append(ordinal)
    for equation in compiled_specs["evaluation"].get("derived_role_equations", []):
        need(not (equation["result_role"] in operand_roles and set(equation["component_roles"]) & set(operand_roles)),
             "aggregate and its flat detail cannot both be root operands")
    need(len(operands) >= compiled_specs["evaluation"]["minimum_source_visible_root_component_count"], "incomplete source frontier")
    unknown, numbers = [], []
    locator = {k: region[k] for k in LOCATOR}
    for ordinal in operands:
        observed = []
        for col in cols:
            value = rows[ordinal - 1]["values_exact"][col - 1]
            if value is None:
                unknown.append({"locator": locator, "row_ordinal": ordinal, "raw_column_ordinal": col,
                                "header_path_exact": table["columns"][col - 1]["header_path_exact"],
                                "value_kind": table["columns"][col - 1]["value_kind"],
                                "row_sha256": digest(rows[ordinal - 1]), "source_exact": None})
                observed.append(None)
            else:
                observed.append(_numeric(family, value))
        numbers.append(observed)
    result = [_numeric(family, rows[-1]["values_exact"][col - 1]) for col in cols]
    if unknown:
        kind, equation = "INCOMPLETE_PRINTED_FRONTIER", {"status": "INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL"}
    else:
        sums = [sum(row[lane_no] for row in numbers) for lane_no in (0, 1)]
        need(sums != result, "complete numeric frontier is not contradictory")
        kind, equation = "PRINTED_CONTRADICTION", {"status": "MISMATCH", "component_sums": sums, "printed_result": result}
    proof = {"locator": locator, "stored_page_blob_ref": clone(blob_ref),
            "original_page_sha256": digest(original), "evaluation_page_sha256": digest(page),
            "original_table_sha256": digest(table), "evaluation_table_sha256": digest(table),
            "rows_exact": clone(rows), "columns_exact": clone(table["columns"]), "money_column_ordinals": clone(cols),
            "operand_row_ordinals": operands, "result_row_ordinal": len(rows), "dependency_row_ordinals": [*dependency, len(rows)],
            "numbered_operand_axis": numbered, "literal_payroll_scope_receipts": clone(payroll),
            "classification_sha256": digest(classification), "unit_axis": clone(unit), "lane_axis": clone(lane),
            "finding_kind": kind, "unknown_operand_axis": unknown, "equation": equation,
            "contradiction_proven": not bool(unknown), "imputation_performed": False}
    if qualified:
        proof["qualified_provision_literal_receipts"] = clone(qualified)
    return proof


def reconcile_unresolved_rows_v1(*, corpus_manifest_index_id, raw_coverage, indexed_query_evidence, trials, page_json_by_document,
                                compiled_specs, declaration, declaration_ref, authenticated_pdf_residuals, source_page_blob_refs):
    """Pure exact join. The runner must separately authenticate declaration/review IO."""
    raw = validate_raw_coverage_v1(raw_coverage)
    declared = validate_declaration_v1(declaration)
    reference(declaration_ref)
    need(declared["raw_coverage_receipt_id"] == raw["receipt_id"]
         and declared["corpus_manifest_index_id"] == corpus_manifest_index_id, "declaration binds another run")
    docs = indexed_query_evidence["selected_document_axis"]
    need(len(docs) == len(trials) == len(indexed_query_evidence["candidate_dispositions"]), "all-status denominator drift")
    for ordinal, (doc, trial) in enumerate(zip(docs, trials, strict=True), 1):
        need(positive(doc.get("document_ordinal")) and doc["document_ordinal"] == ordinal
             and positive(trial.get("document_ordinal")) and trial["document_ordinal"] == ordinal
             and trial.get("source_logical_name") == doc["source_logical_name"]
             and trial.get("source_sha256") == doc["source_sha256"]
             and trial.get("status") in {"READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY", "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY", "UNRESOLVED_GEMINI_JSON_FAMILY"},
             "all-status source identity drift")
        if trial["status"] != "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY":
            need(trial.get("mappings") == [] and type(trial.get("mapping_count")) is int
                 and trial["mapping_count"] == 0, "nonREADY trial leaked mappings")
    row_index = {(axis, digest(item)): item for axis in AXES for item in raw[axis]}
    held, seen = [], set()
    for review in declared["reviews"]:
        ordinal = review["document"]["document_ordinal"]
        need(1 <= ordinal <= len(docs), "review ordinal out of range")
        doc, trial = docs[ordinal - 1], trials[ordinal - 1]
        cluster = indexed_query_evidence["candidate_dispositions"][ordinal - 1]["cluster"]
        need(same(doc, review["document"]) and trial.get("document_ordinal") == ordinal
             and trial.get("status") == review["status"] and same(trial.get("reasons"), review["reasons"])
             and trial.get("mappings") == [] and type(trial.get("mapping_count")) is int and trial["mapping_count"] == 0
             and trial.get("source_sha256") == doc["source_sha256"] and trial.get("source_logical_name") == doc["source_logical_name"]
             and digest(trial) == review["trial_sha256"] and digest(cluster) == review["query_cluster_sha256"], "review trial/source/status binding drift")
        residuals = [item for item in authenticated_pdf_residuals if item["document_ordinal"] == ordinal]
        need(len(residuals) == 1 and residuals[0]["residual_audit_id"] == review["pdf_residual_audit_id"]
             and residuals[0]["status"] == trial["status"] and same(residuals[0]["reasons"], trial["reasons"])
             and residuals[0]["source_sha256"] == doc["source_sha256"]
             and residuals[0]["source_size_bytes"] == review["source_size_bytes"], "missing/wrong authenticated PDF residual")
        frontier = build_printed_frontier_v1(document=doc,
            page_axis=[p for p in indexed_query_evidence["selected_page_axis"] if p["document_ordinal"] == ordinal],
            pages=page_json_by_document[ordinal], cluster=cluster, compiled_specs=compiled_specs, source_page_blob_refs=source_page_blob_refs)
        need(same(frontier, review["printed_frontier"]) and frontier["finding_kind"] == review["finding_kind"], "fresh printed frontier differs")
        expected = set()
        for key, item in row_index.items():
            if item["document_ordinal"] != ordinal or not item["coverage"].startswith("VIOLATION_"):
                continue
            loc = frontier["locator"]
            if all(item[name] == loc[name] for name in ("source_sha256", "page_json_version_id", "physical_page", "section_id", "table_id")) \
                    and item["row_ordinal"] in frontier["dependency_row_ordinals"]:
                expected.add(key)
        actual = {(item["axis_name"], item["raw_coverage_item_sha256"]) for item in review["held_rows"]}
        need(actual and actual == expected and not (actual & seen), "missing/extra/unrelated held review row")
        for key in sorted(actual):
            item = row_index[key]
            row = frontier["rows_exact"][item["row_ordinal"] - 1]
            need(same(item["values_exact"], row["values_exact"]) and item["label_exact"] == row["label_exact"]
                 and same(item["hierarchy_path_exact"], row.get("hierarchy_path_exact", []))
                 and item["row_kind"] == row["row_kind"], "held row raw before-image drift")
            held.append({"axis_name": key[0], "raw_coverage_item_sha256": key[1], "raw_item": clone(item),
                         "finding_kind": review["finding_kind"], "disposition": DISPOSITION,
                         "manual_review_ref": clone(review["manual_review_ref"]), "manual_finding_id": review["manual_finding_id"],
                         "pdf_residual_audit_id": review["pdf_residual_audit_id"], "printed_frontier_sha256": digest(frontier)})
        seen.update(actual)
    matched_hashes = {key[1] for key in seen}
    unjoined = [item for item in raw["violation_axis"] if digest(item) not in matched_hashes]
    material = {"format_version": RESULT, "family_id": "OPERATING_EXPENSE",
                "corpus_manifest_index_id": declared["corpus_manifest_index_id"],
                "raw_coverage_receipt_id": raw["receipt_id"], "raw_coverage_sha256": digest(raw),
                "declaration_ref": clone(declaration_ref), "held_row_axis": held, "held_row_axis_sha256": digest(held),
                "unjoined_violation_axis": clone(unjoined), "unjoined_violation_axis_sha256": digest(unjoined),
                "unjoined_violation_count": len(unjoined)}
    return {**material, "receipt_id": "gjoeurd1:reconciliation:" + digest(material)}


def validate_reconciliation_v1(raw_coverage, value):
    raw = validate_raw_coverage_v1(raw_coverage)
    need(type(value) is dict and value.get("format_version") == RESULT
         and value.get("raw_coverage_receipt_id") == raw["receipt_id"]
         and value.get("raw_coverage_sha256") == digest(raw), "wrong reconciliation raw domain")
    reference(value.get("declaration_ref"))
    held = value.get("held_row_axis")
    need(type(held) is list and value.get("held_row_axis_sha256") == digest(held), "held axis drift")
    allowed = {(axis, digest(item)): item for axis in AXES for item in raw[axis] if item["coverage"].startswith("VIOLATION_")}
    seen = set()
    for item in held:
        key = (item["axis_name"], item["raw_coverage_item_sha256"])
        need(key in allowed and key not in seen and same(item["raw_item"], allowed[key])
             and item["disposition"] == DISPOSITION and item["finding_kind"] in KINDS, "held item identity drift")
        seen.add(key)
    unresolved = [item for item in raw["violation_axis"] if digest(item) not in {key[1] for key in seen}]
    need(same(value.get("unjoined_violation_axis"), unresolved)
         and value.get("unjoined_violation_axis_sha256") == digest(unresolved)
         and type(value.get("unjoined_violation_count")) is int and value["unjoined_violation_count"] == len(unresolved)
         and value.get("receipt_id") == "gjoeurd1:reconciliation:" + digest({k: v for k, v in value.items() if k != "receipt_id"}),
         "reconciliation inventory/seal drift")
    return clone(value)
