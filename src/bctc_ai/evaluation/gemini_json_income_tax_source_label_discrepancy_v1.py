"""Registered negative source observations for Family 39; no source repair.

The approved human observation is bound to an exact PDF render and selected
JSON profile. The family evaluator only withholds mappings. The runner separately
authenticates the original PDF bytes/pixels on its warm and independent cold pass.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from hashlib import sha256
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import _source_table
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

REGISTRY_RELATIVE_PATH = "config/families/tm-income-tax-source-label-discrepancies-v1.json"
REGISTRY_PATH = Path(__file__).resolve().parents[3] / REGISTRY_RELATIVE_PATH
REGISTRY_SHA256 = "c8788461c2e3aed5068c9ba3c329f39bfd13d2cf8dea7aede724bbff6b017bcf"
_LOCATOR_KEYS = (
    "document_id", "document_ordinal", "source_logical_name", "source_sha256",
    "page_json_version_id", "physical_page", "selected_page_ordinal",
)
PRINTED_DASH_CLASSIFICATION = "PRINTED_DASH_VS_JSON_NUMERIC"


def _validate_printed_dash_observation(observation):
    """A negative pixel review binds exact raw cells, never their replacement."""
    target, review = observation["locator"], observation["review"]
    source = observation["source"]
    _need(type(source) is dict and set(source) == {
        "document_id", "source_logical_name", "source_sha256", "source_size_bytes",
    } and type(source["source_size_bytes"]) is int and source["source_size_bytes"] > 0
          and source["document_id"] == "gfpstorev1:document:" + canonical_json_sha256_v1(
              {key: source[key] for key in ("source_logical_name", "source_sha256", "source_size_bytes")}),
          "printed-dash PDF document identity differs")
    _need(observation["expected_role"] in {"DEFERRED_TAX_NET", "NON_TAXABLE_AGGREGATE"}
          and observation["source_section_kind"] in {"PRIMARY_STATEMENT", "FINANCIAL_NOTE"}
          and observation["source_statement_type"] == (
              "INCOME_STATEMENT" if observation["source_section_kind"] == "PRIMARY_STATEMENT" else "NOT_APPLICABLE")
          and observation["source_page_status"] in {
              "PRIMARY_FINANCIAL_STATEMENT", "FINANCIAL_NOTE_CONTENT", "MIXED_FINANCIAL_CONTENT"},
          "unreviewed printed-dash source kind or role")
    before = observation["before_reference"]
    _need(type(before) is dict and set(before) == {
        "row_kind", "label_exact", "hierarchy_path_exact", "values_exact",
    } and type(before["values_exact"]) is list, "printed-dash full raw row before-image required")
    columns = observation["printed_dash_money_column_ordinals"]
    _need(type(columns) is list and columns and len(columns) == len(set(columns))
          and all(type(n) is int and n in target["money_column_ordinals"]
                  and 1 <= n <= len(before["values_exact"])
                  and type(before["values_exact"][n - 1]) is str
                  and before["values_exact"][n - 1] == "0" for n in columns),
          "printed-dash discrepancy must identify exact reviewed raw zero cells")
    _need(review["decision"] == "PRINTED_DASH_DIFFERS_FROM_JSON_NUMERIC_HOLD_NO_REPAIR"
          and review["source_values_changed"] is False and review["text_layer_claimed"] is False
          and review["printed_glyph_by_money_column"] == {str(n): "-" for n in columns},
          "printed-dash negative manual-review boundary differs")


class IncomeTaxSourceLabelDiscrepancyV1Error(ValueError):
    """A registered negative observation's immutable source binding drifted."""


def _need(condition: Any, message: str) -> None:
    if not condition:
        raise IncomeTaxSourceLabelDiscrepancyV1Error("income-tax negative source label: " + message)


def _sealed(value: dict[str, Any], key: str, prefix: str) -> None:
    material = {name: item for name, item in value.items() if name != key}
    _need(value.get(key) == prefix + canonical_json_sha256_v1(material), key + " differs")


def _validate_registry(registry: Any) -> dict[str, Any]:
    _need(type(registry) is dict and set(registry) == {
        "format_version", "family_id", "observations", "registry_id",
    }, "registry fields differ")
    _need(registry["format_version"] == "INCOME_TAX_REGISTERED_SOURCE_LABEL_DISCREPANCIES_V1"
          and registry["family_id"] == "INCOME_TAX" and type(registry["observations"]) is list,
          "registry format/family differs")
    _sealed(registry, "registry_id", "gjitflabelv1:registry:")
    # Independent approval is the loader's fixed file SHA, not these content IDs.
    # This validator is also used with explicit synthetic loader fixtures in tests.
    seen = set()
    for observation in registry["observations"]:
        _need(type(observation) is dict, "observation is not an object")
        _sealed(observation, "observation_id", "gjitflabelv1:observation:")
        _need(observation["observation_id"] not in seen, "duplicate observation")
        seen.add(observation["observation_id"])
        review = observation["review"]
        if observation["classification"] == PRINTED_DASH_CLASSIFICATION:
            _validate_printed_dash_observation(observation)
        else:
            _need(observation["classification"] == "SOURCE_LABEL_SUBSTITUTION_NOT_EXTRA_ROW"
                  and observation["expected_role"] == "DEFERRED_TAX_NET", "unreviewed observation semantics")
            _need(review["decision"] == "ROLE_LABEL_HAS_NO_PRINTED_COUNTERPART_HOLD_NO_REPAIR"
                  and review["printed_counterpart_for_claimed_role"] is False
                  and review["source_values_changed"] is False and review["text_layer_claimed"] is False,
                  "negative manual-review boundary differs")
        render = review["page_render"]
        _need(render["renderer"] == "pdftoppm" and render["resolution_dpi"] == 100
              and render["format"] == "PNG" and render["alpha"] is False
              and render["colorspace"] == "RGB", "unreviewed PDF render contract")
        target = observation["locator"]
        _need(type(target["row_ordinal"]) is int and target["row_ordinal"] > 0
              and target["row_id"] == f"r{target['row_ordinal']}"
              and type(target["physical_page"]) is int and target["physical_page"] > 0
              and type(target["money_column_ordinals"]) is list
              and len(target["money_column_ordinals"]) == len(set(target["money_column_ordinals"]))
              and all(type(n) is int and n > 0 for n in target["money_column_ordinals"]), "registered locator fields differ")
    return registry


def load_registered_negative_source_label_observations_v1() -> dict[str, Any]:
    """No caller-selected approval path/hash; resealing cannot replace approval."""
    try:
        raw = REGISTRY_PATH.read_bytes()
    except OSError as error:
        raise IncomeTaxSourceLabelDiscrepancyV1Error(
            f"income-tax negative source label: approval unavailable at {REGISTRY_PATH}: {error}"
        ) from error
    _need(sha256(raw).hexdigest() == REGISTRY_SHA256, "registered approval bytes differ")
    return _validate_registry(json.loads(raw))


def registered_negative_source_label_observation_axis_v1(page_records) -> list[dict[str, Any]]:
    registry = _validate_registry(load_registered_negative_source_label_observations_v1())
    output = []
    for observation in registry["observations"]:
        source, target = observation["source"], observation["locator"]
        records = [record for record in page_records
                   if record["source_sha256"] == source["source_sha256"]
                   and record["physical_page"] == target["physical_page"]]
        if not records:
            continue
        _need(len(records) == 1, "selected source page is not unique")
        record = records[0]
        # Page records carry the document content ID rather than a separate PDF
        # byte count. The new registry replays that ID from name/SHA/size, and
        # the independent warm/cold PDF authenticator checks the runtime size.
        source_keys = set(source) - {"source_size_bytes"} if observation["classification"] == PRINTED_DASH_CLASSIFICATION else source
        _need(all(record[key] == source[key] for key in source_keys), "source PDF identity differs")
        _need(record["page_json_version_id"] == target["page_json_version_id"],
              "unregistered selected JSON version; old review cannot authorize a new source profile")
        _need(type(record["document_ordinal"]) is int and record["document_ordinal"] > 0,
              "invalid runtime document ordinal")
        page = record["page_json"]
        section, table = _source_table(page, section_id=target["section_id"], table_id=target["table_id"])
        if observation["classification"] == PRINTED_DASH_CLASSIFICATION:
            _need(page.get("status") == observation["source_page_status"]
                  and section.get("content_kind") == observation["source_section_kind"]
                  and section.get("statement_type") == observation["source_statement_type"],
                  "registered printed-dash source kind differs")
        else:
            _need(page.get("status") == "PRIMARY_FINANCIAL_STATEMENT"
                  and section.get("content_kind") == "PRIMARY_STATEMENT"
                  and section.get("statement_type") == "INCOME_STATEMENT", "registered PRIMARY source kind differs")
        _need(1 <= target["row_ordinal"] <= len(table["rows"]), "registered row absent")
        row = table["rows"][target["row_ordinal"] - 1]
        _need(all(same_typed_json_v1(row.get(key), value)
                  for key, value in observation["before_reference"].items()), "registered row before-image differs")
        columns = target["money_column_ordinals"]
        _need(type(row.get("values_exact")) is list and columns
              and all(type(n) is int and 1 <= n <= len(row["values_exact"])
                      and n <= len(table["columns"]) and table["columns"][n - 1].get("value_kind") == "MONEY"
                      for n in columns),
              "registered raw money-column frontier differs")
        locator = {key: canonical_clone_v1(record[key]) for key in _LOCATOR_KEYS}
        locator.update(section_id=target["section_id"], table_id=target["table_id"])
        material = {
            "observation_id": observation["observation_id"], "registry_id": registry["registry_id"],
            "registered_approval_sha256": REGISTRY_SHA256, "source_locator": locator,
            "original_page_json_sha256": canonical_json_sha256_v1(page),
            "original_section_json_sha256": canonical_json_sha256_v1(section),
            "original_table_json_sha256": canonical_json_sha256_v1(table),
            "source_section_kind": section.get("content_kind"),
            "row_ordinal": target["row_ordinal"], "row_id": target["row_id"],
            "money_column_ordinals": canonical_clone_v1(columns),
            "original_source_row_exact": canonical_clone_v1(row),
            "registered_negative_observation": canonical_clone_v1(observation),
            "classification": (PRINTED_DASH_CLASSIFICATION if observation["classification"] == PRINTED_DASH_CLASSIFICATION
                               else "SOURCE_TRANSCRIPTION_DISCREPANCY"),
            "source_values_changed": False, "fresh_pdf_authentication_claimed": False,
        }
        output.append({**material, "receipt_id": "gjitflabelv1:source:" + canonical_json_sha256_v1(material)})
    return output


def registered_negative_source_label_conflicts_v1(candidate, *, source_context, repaired_records, compiled_specs):
    """A pinned negative review withholds a cited row; it never supplies a value."""
    del compiled_specs  # Existing context/source receipts own units and periods.
    axis = registered_negative_source_label_observation_axis_v1(repaired_records)
    if not axis:
        return []
    _need(candidate.get("candidate_id") == "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in candidate.items() if key != "candidate_id"}), "selected candidate content ID differs")
    context_material = {key: value for key, value in source_context.items() if key != "receipt_id"}
    _need(source_context.get("receipt_id") == "gjitfav1:source-context:" + canonical_json_sha256_v1(context_material),
          "source context receipt differs")
    _need(same_typed_json_v1(source_context.get("registered_source_label_discrepancy_observations"), axis),
          "negative observation is not bound to the runtime source context")
    periods = source_context["document_statement_period_inventory"]
    _sealed(periods, "receipt_id", "gjitfav1:document-statement-periods:")
    for observed in axis:
        if observed["classification"] == PRINTED_DASH_CLASSIFICATION and observed["source_section_kind"] == "FINANCIAL_NOTE":
            populations = [item for item in source_context["tax_population_inventory"]
                           if same_typed_json_v1(item["locator"], observed["source_locator"])]
            _need(len(populations) == 1, "printed-dash NOTE population source join is not unique")
            population = populations[0]
            _sealed(population, "receipt_id", "gjitfav1:tax-population:")
            _need(population["original_page_json_sha256"] == observed["original_page_json_sha256"]
                  and population["original_table_json_sha256"] == observed["original_table_json_sha256"]
                  and same_typed_json_v1(population["lane_axis"].get("money_column_ordinals"),
                                         observed["money_column_ordinals"])
                  and same_typed_json_v1(population["source_table_rows_exact"][observed["row_ordinal"] - 1],
                                         observed["original_source_row_exact"]),
                  "printed-dash NOTE population/row/hash binding differs")
            continue
        sources = [item for item in periods["sources"]
                   if same_typed_json_v1(item["locator"], observed["source_locator"])]
        _need(len(sources) == 1 and sources[0]["statement_type"] == "INCOME_STATEMENT"
              and all(sources[0][key] == observed[key] for key in (
                  "original_page_json_sha256", "original_section_json_sha256", "original_table_json_sha256"))
              and same_typed_json_v1(sources[0]["lane_axis"].get("money_column_ordinals"),
                                     observed["money_column_ordinals"]), "PRIMARY inventory/source/axis binding differs")
    conflicts = []
    for mapping in candidate.get("mappings", []):
        for ref in mapping.get("source_refs", []):
            for observed in axis:
                profile = observed["registered_negative_observation"]
                printed_dash = profile["classification"] == PRINTED_DASH_CLASSIFICATION
                if not printed_dash and mapping.get("role") != profile["expected_role"]:
                    continue
                target, locator = profile["locator"], observed["source_locator"]
                supplied = ref["locator"]
                related = (supplied.get("page_json_version_id") == locator["page_json_version_id"] or (
                    supplied.get("source_sha256") == locator["source_sha256"]
                    and supplied.get("physical_page") == locator["physical_page"]))
                if not related:
                    continue
                if printed_dash and all(type(supplied.get(key)) is str for key in ("section_id", "table_id")) and any(
                    supplied[key] != locator[key] for key in ("section_id", "table_id")
                ):
                    # Row IDs are local to a source table. Another actual
                    # table on this page cannot borrow or collide with them.
                    continue
                if printed_dash and ref.get("row_ordinal") != target["row_ordinal"] and ref.get("row_id") != target["row_id"]:
                    continue
                _need(all(same_typed_json_v1(supplied.get(key), value) for key, value in locator.items()),
                      "selected mapping has a partial registered-source locator mismatch")
                reference_before = {key: value for key, value in profile["before_reference"].items()
                                    if key != "values_exact"}
                _need(ref.get("row_ordinal") == target["row_ordinal"] and ref.get("row_id") == target["row_id"]
                      and same_typed_json_v1(ref.get("money_column_ordinals"), target["money_column_ordinals"])
                      and all(same_typed_json_v1(ref.get(key), value)
                              for key, value in reference_before.items()),
                      "selected mapping reference differs from registered original row")
                # Applicability belongs to the original cited raw row. A
                # derived/aggregated output can have source_text=None and a
                # nonzero total while still citing this untrusted source cell.
                material = {"classification": PRINTED_DASH_CLASSIFICATION if printed_dash else "SOURCE_TRANSCRIPTION_DISCREPANCY",
                            "source_observation": canonical_clone_v1(observed),
                            "source_context_receipt_id": source_context["receipt_id"],
                            "selected_mapping": canonical_clone_v1(mapping), "selected_source_ref": canonical_clone_v1(ref),
                            "candidate_id_before_hold": candidate["candidate_id"],
                            "rule": ("REGISTERED_PRINTED_DASH_CANNOT_AUTHORIZE_JSON_NUMERIC_OUTPUT" if printed_dash
                                     else "REGISTERED_PDF_LABEL_SUBSTITUTION_CANNOT_BIND_A_FINANCIAL_ROLE"),
                            "source_values_changed": False, "fresh_pdf_authentication_claimed": False}
                conflicts.append({**material, "receipt_id": "gjitflabelv1:hold:" + canonical_json_sha256_v1(material)})
    return conflicts


def _file_sha256(path: Path) -> str:
    value = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def _render_registered_page_v1(pdf_path: Path, physical_page: int) -> bytes:
    """Only the corpus owner invokes this on real PDFs; unit tests use fixtures."""
    with tempfile.TemporaryDirectory(prefix="f39-negative-label-render-") as temporary:
        prefix = Path(temporary) / "page"
        subprocess.run(["/usr/bin/pdftoppm", "-f", str(physical_page), "-l", str(physical_page),
                        "-r", "100", "-png", "-singlefile", str(pdf_path), str(prefix)],
                       check=True, capture_output=True, timeout=120)
        return prefix.with_suffix(".png").read_bytes()


def authenticate_registered_negative_source_labels_v1(*, document_source, original_records, pdf_path: Path):
    """Fresh original-PDF pixel authentication, independently called warm/cold."""
    axis = registered_negative_source_label_observation_axis_v1(original_records)
    if not axis:
        return []
    before = pdf_path.stat()
    def identity(value):
        return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    source_material = {key: document_source[key] for key in (
        "source_logical_name", "source_sha256", "source_size_bytes",
    )}
    _need(type(document_source["source_size_bytes"]) is int and document_source["source_size_bytes"] > 0
          and document_source["document_id"] == "gfpstorev1:document:" + canonical_json_sha256_v1(source_material),
          "original PDF document content identity differs")
    _need(before.st_size == document_source["source_size_bytes"]
          and _file_sha256(pdf_path) == document_source["source_sha256"], "original PDF bytes differ")
    receipts = []
    for observation in axis:
        profile = observation["registered_negative_observation"]
        _need(all(document_source.get(key) == value for key, value in profile["source"].items()),
              "original PDF source/profile identity differs")
        render = profile["review"]["page_render"]
        raw = _render_registered_page_v1(pdf_path, profile["locator"]["physical_page"])
        _need(len(raw) == render["size_bytes"] and sha256(raw).hexdigest() == render["sha256"],
              "original PDF render differs from the registered reviewed pixels")
        _need(len(raw) >= 33 and raw[:8] == b"\x89PNG\r\n\x1a\n"
              and int.from_bytes(raw[16:20], "big") == render["width_pixels"]
              and int.from_bytes(raw[20:24], "big") == render["height_pixels"]
              and raw[24:26] == bytes((8, 2)), "registered page is not the approved 8-bit RGB PNG")
        material = {"source_observation_receipt": observation, "registered_approval_sha256": REGISTRY_SHA256,
                    "source_pdf": canonical_clone_v1(document_source), "page_render": canonical_clone_v1(render),
                    "status": "PASS_FRESH_PDF_PIXELS_REGISTERED_MANUAL_NEGATIVE_REVIEW_NOT_FINANCIAL_ACCEPTANCE",
                    "text_layer_claimed": False, "source_values_changed": False}
        receipts.append({**material, "receipt_id": "gjitflabelv1:pdf-auth:" + canonical_json_sha256_v1(material)})
    _need(identity(before) == identity(pdf_path.stat())
          and _file_sha256(pdf_path) == document_source["source_sha256"], "original PDF changed during pixel callbacks")
    return receipts
