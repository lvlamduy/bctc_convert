"""Family-local source adapter for income-tax expense disclosures.

The shared multi-table engine remains the accounting authority.  This module
adds a deterministic fallback for tax rows printed directly on the primary
income statement and applies separately authenticated PDF transcription
repairs on private page clones.  It never derives a source value, turns a
blank into zero, or changes the shared evaluator/query policy.
"""

from __future__ import annotations

import json
import re
import unicodedata
from asyncio import current_task
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date, timedelta
from functools import wraps
from hashlib import sha256
from pathlib import Path
from threading import get_ident
from time import perf_counter
from typing import Any

from bctc_ai.evaluation import (
    gemini_json_income_tax_section_caption_repair_v1 as section_caption_core,
)
from bctc_ai.evaluation import (
    gemini_json_income_tax_source_label_discrepancy_v1 as source_label_discrepancy,
)
from bctc_ai.evaluation.gemini_json_hierarchical_accounting_family_v1 import (
    _normalized,
    _path_has_role,
    _without_leading_ordinal,
)
from bctc_ai.evaluation.gemini_json_income_tax_part_period_context_v1 import (
    GeminiJsonIncomeTaxPartPeriodContextV1Error,
    replay_registered_part_period_contexts_v1,
    select_declared_part_period_registry_variant_v1,
    validate_registered_part_period_registry_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    CLAIM_BOUNDARY as SHARED_CLAIM_BOUNDARY,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    _multitable_lane_axis,
    _source_money,
    _source_table,
    _unit_axis,
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    classify_gemini_json_multitable_hierarchical_table_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
    validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    validate_gemini_json_multitable_hierarchical_sweep_query_bindings_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    decode_canonical_json_bytes_v1,
    same_typed_json_v1,
)

FAMILY_ID = "INCOME_TAX"
ADAPTER_FORMAT_VERSION = "GEMINI_JSON_INCOME_TAX_FAMILY_ADAPTER_V1"
ADAPTER_SPEC_FORMAT_VERSION = "INCOME_TAX_FAMILY_ADAPTER_SPEC_V1"
SOURCE_REPAIR_FORMAT_VERSION = "INCOME_TAX_AUTHENTICATED_SOURCE_REPAIR_SPEC_V1"
QUERY_RECEIPT_FORMAT_VERSION = "GEMINI_JSON_INCOME_TAX_QUERY_RECEIPT_V1"
DEFAULT_ADAPTER_SPEC_PATH = "config/families/tm-income-tax-adapter-v1.json"
DEFAULT_SOURCE_REPAIR_SPEC_PATH = "config/families/tm-income-tax-source-repair-v1.json"
DEFAULT_PART_PERIOD_CONTEXT_REGISTRY_PATH = "config/families/tm-income-tax-part-period-contexts-v1.json"
DEFAULT_SECTION_CAPTION_AUTH_ENVELOPE_PATH = "config/families/tm-income-tax-section-caption-repair-auth-v2.json"
_SECTION_CAPTION_AUTH_ENVELOPE_SHA256 = "dc80fc86b1e718117e5a6ea80bf9a45d5c7a04a6cf084db89daa8621f4a14c74"
_SECTION_CAPTION_CLONE_CORE_SHA256 = "13395179d0ec6e48bea94f0adb02f05c1972defd4fa6633a597596e3a2425ccc"
_SECTION_CAPTION_LEGACY_SPEC_SHA256 = "9aac4e448b82ee0078c007ca06a36f0e3f11c2b4f694266a1211929f16228ea4"
DEFAULT_PART_PERIOD_COMMON204_REGISTRY_PATH = "config/families/tm-income-tax-part-period-contexts-common204-v1.json"
_PART_PERIOD_COMMON204_REGISTRY_SHA256 = "7ba529e7878c1fd5d6af27abe4b5a7d2937bd395b40e3ea1160ee261448adaeb"
_PART_PERIOD_ORIGINAL_REPAIR_SHA256 = "9aac4e448b82ee0078c007ca06a36f0e3f11c2b4f694266a1211929f16228ea4"
# Independently reviewed source-context approval bytes. A caller-resealed
# registry or receipt cannot replace this approval; PDF checks remain separate.
_PART_PERIOD_CONTEXT_REGISTRY_SHA256 = "c98624ac7822b44fa53c055ad094968a7fb11f3e96751a1c06e875b4999c140b"
CLAIM_BOUNDARY = (
    "MANIFEST_SELECTED_GEMINI_JSON_ONLY_INCOME_TAX_EXACT_PRIMARY_INCOME_"
    "STATEMENT_DIRECT_SOURCE_ROWS_FINAL_DURATION_LANES_PDF_AUTHENTICATED_"
    "PRIVATE_CLONE_REPAIR_NO_BLANK_ZERO_NO_VALUE_MAGNITUDE_OR_SIGN_"
    "BACKSOLVE_NO_BANK_FILE_YEAR_PAGE_ROUTING_PROPOSAL_ONLY_" + SHARED_CLAIM_BOUNDARY
)
_QUERY_ADAPTER_RULE = (
    "EXACT_PRIMARY_INCOME_STATEMENT_TAX_ROWS_PROJECTED_ON_PRIVATE_CLONE_"
    "WITH_OR_WITHOUT_A_READY_DIRECT_NOTE"
)
_QUERY_ADAPTER_STRATEGIES = {
    "DIRECT_NOTE_PLUS_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION",
    "DIRECT_NOTE_PLUS_SUPPLEMENTAL_NOTE_PLUS_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION",
    "DIRECT_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION",
}
ORIGINAL_NOTE_ADAPTER_FORMAT_VERSION = "GEMINI_JSON_INCOME_TAX_ORIGINAL_NOTE_ADAPTER_V1"
_ORIGINAL_NOTE_STRATEGY = "DIRECT_ORIGINAL_NOTE_POPULATIONS_SOURCE_PRESENTATION"
_ORIGINAL_BASIS_ROLES = {
    "RATE": ("PROFIT_BEFORE_TAX", "CURRENT_TAX_PARENT", "PRIOR_PERIOD_TAX_ADJUSTMENT"),
    "INCOME": ("PROFIT_BEFORE_TAX", "NON_TAXABLE_AGGREGATE", "NON_DEDUCTIBLE_EXPENSE", "TAXABLE_INCOME"),
}
_ORIGINAL_RATE_PRIVATE_ALIASES = {
    "CURRENT_TAX_PARENT": ("Chi phí thuế thu nhập doanh nghiệp hiện hành",),
    "PRIOR_PERIOD_TAX_ADJUSTMENT": (
        "Thuế TNDN nộp bổ sung từ các năm trước",
        "Nộp thuế bổ sung từ các năm trước",
    ),
}

_ROOT_LABELS = {
    "chi phi thue tndn",
    "chi phi thue tndn tam tinh",
    "chi phi thue thu nhap doanh nghiep",
    "chi phi thue thu nhap doanh nghiep tam tinh",
    "tong chi phi thue tndn",
    "tong chi phi thue thu nhap doanh nghiep",
}
_CANONICAL_LABEL = {
    "PROFIT_BEFORE_TAX": "Lợi nhuận kế toán trước thuế",
    "NON_DEDUCTIBLE_EXPENSE": "Chi phí không được khấu trừ",
    "CURRENT_TAX_AT_RATE": "Chi phí thuế TNDN theo thuế suất",
    "STATUTORY_TAX_AMOUNT_SOURCE_ONLY": "Thuế tính ở thuế suất 20%",
    "CURRENT_YEAR_TAX_EXPENSE": "Năm hiện hành",
    "CURRENT_PERIOD_TAX_EXPENSE_SOURCE_ONLY": "Kỳ hiện hành",
    "CURRENT_YEAR_EXPENSE_CONTEXT": "Chi phí thuế hiện hành",
    "CURRENT_TAX_BANK": "Chi phí thuế TNDN hiện hành ước tính của Ngân hàng",
    "SUBSIDIARY_TAX": "Chi phí thuế TNDN hiện hành của công ty con",
    "PRIOR_PERIOD_TAX_ADJUSTMENT": "Điều chỉnh thuế TNDN các năm trước",
    "SOURCE_ONLY_EQUATION_COMPONENT": "Điều chỉnh khác",
    "CURRENT_TAX_PARENT": "Chi phí thuế TNDN hiện hành",
    "DEFERRED_TAX_NET": "Chi phí thuế thu nhập doanh nghiệp hoãn lại",
    "FAMILY_ROOT_TOTAL": "Chi phí thuế thu nhập doanh nghiệp",
}

_SUPPLEMENTAL_DIRECT_ROLES = (
    "PROFIT_BEFORE_TAX",
    "NON_DEDUCTIBLE_EXPENSE",
    "CURRENT_TAX_AT_RATE",
    "STATUTORY_TAX_AMOUNT_SOURCE_ONLY",
    "CURRENT_YEAR_TAX_EXPENSE",
    "CURRENT_PERIOD_TAX_EXPENSE_SOURCE_ONLY",
    "CURRENT_TAX_BANK",
    "SUBSIDIARY_TAX",
    "PRIOR_PERIOD_TAX_ADJUSTMENT",
    "CURRENT_TAX_PARENT",
    "DEFERRED_TAX_NET",
)
_SUPPLEMENTAL_PROJECTED_ROLES = (
    *_SUPPLEMENTAL_DIRECT_ROLES,
    "SOURCE_ONLY_EQUATION_COMPONENT",
)


class GeminiJsonIncomeTaxFamilyV1Error(ValueError):
    """Family-39 source evidence, projection, or replay drifted."""


def _error(message: str) -> GeminiJsonIncomeTaxFamilyV1Error:
    return GeminiJsonIncomeTaxFamilyV1Error(message)


_DOCUMENT_PERIOD_OPERATION = ContextVar("f39_document_period_operation", default=None)
_PERIOD_INVENTORY_DEPENDENCY_PATHS = (
    "evaluation/gemini_json_income_tax_source_label_discrepancy_v1.py",
    "evaluation/gemini_json_income_tax_section_caption_repair_v1.py",
    "evaluation/gemini_json_income_tax_family_v1.py",
    "evaluation/gemini_json_income_tax_part_period_context_v1.py",
    "evaluation/gemini_json_multitable_hierarchical_family_v1.py",
    "evaluation/gemini_json_hierarchical_accounting_family_v1.py",
    "evaluation/gemini_json_customer_deposit_family_v1.py",
    "evaluation/gemini_json_other_long_term_investments_family_v1.py",
    "evaluation/accounting_variant_graph_engine_v1.py",
    "evaluation/source_observation_lane_math_v1.py",
    "evaluation/gemini_json_flat_accounting_family_v1.py",
    "source_structure/contracts_v1.py",
)


def _period_inventory_execution_owner_v1():
    try:
        task = current_task()
    except RuntimeError:  # Synchronous caller, no running asyncio loop.
        task = None
    return get_ident(), task


@contextmanager
def income_tax_document_period_evaluation_scope_v1(*, enabled: bool = True):
    """Memoize source-derived inventory only within one evaluation operation.

    No candidate/READY result or caller-supplied receipt is cached. A disabled
    scope is sticky through nested public APIs, including independent replay.
    The yielded counters contain no cached values; all entries are discarded
    in finally, including after early returns and exceptions. This operation
    is synchronous: inherited contexts cannot share it across tasks/threads.
    Acceptance requires a fresh, pinned, trusted Python runtime without hot
    reload or arbitrary memory mutation. The entry-point fence below is only
    supplemental invalidation, not authentication of Python runtime memory.
    Implementation bytes are pinned at first use and verified again before
    successful owner exit. Nested results are provisional until that exit:
    no persistence, export or accepted handoff is permitted inside the scope.
    This is an acceptance barrier, not a monitor for transient filesystem edits.
    """
    if type(enabled) is not bool:
        raise _error("income-tax period inventory cache switch is invalid")
    parent = _DOCUMENT_PERIOD_OPERATION.get()
    if parent is not None and (parent["closed"] or parent["invalidated"]):
        raise _error("income-tax period inventory operation is closed or invalidated")
    if parent is not None and parent["execution_owner"] != _period_inventory_execution_owner_v1():
        raise _error("income-tax period inventory operation cannot cross tasks or threads")
    if parent is not None and (enabled or not parent["enabled"]):
        yield parent["metrics"]
        return
    metrics = {"requests": 0, "hits": 0, "builds": 0, "disabled_requests": 0,
               "key_seconds": 0.0, "build_seconds": 0.0, "clone_seconds": 0.0,
               "dependency_checks": 0, "dependency_check_seconds": 0.0,
               "peak_entries": 0, "peak_stored_bytes": 0}
    state = {"enabled": enabled, "entries": {}, "metrics": metrics,
             "execution_owner": _period_inventory_execution_owner_v1(),
             "implementation_refs": None, "callable_fence": None,
             "closed": False, "invalidated": False}
    token = _DOCUMENT_PERIOD_OPERATION.set(state)
    try:
        yield metrics
    finally:
        try:
            if state["enabled"] and state["implementation_refs"] is not None:
                started = perf_counter()
                try:
                    _period_inventory_check_dependencies_v1(state)
                    if (state["callable_fence"] is not None
                            and not all(left is right for left, right in zip(
                                state["callable_fence"], _period_inventory_callable_fence_v1(), strict=True))):
                        state["invalidated"] = True
                        raise _error("income-tax period inventory callable changed during operation")
                finally:
                    metrics["key_seconds"] += perf_counter() - started
            if state["invalidated"]:
                raise _error("income-tax period inventory operation is closed or invalidated")
        finally:
            state["closed"] = True
            state["entries"].clear()
            _DOCUMENT_PERIOD_OPERATION.reset(token)


def _document_period_operation(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with income_tax_document_period_evaluation_scope_v1():
            return function(*args, **kwargs)
    return wrapped


def _period_inventory_dependency_refs_v1() -> list[dict[str, Any]]:
    """Read actual reviewed transitive implementation bytes, never mtime/IDs."""
    root = Path(__file__).resolve().parents[1]
    refs = []
    try:
        for relative in _PERIOD_INVENTORY_DEPENDENCY_PATHS:
            raw = (root / relative).read_bytes()
            refs.append({"path": relative, "size_bytes": len(raw), "sha256": sha256(raw).hexdigest()})
        # Registry bytes are also checked at the operation's exit barrier,
        # including after the last memo hit. This path is relative to repo,
        # unlike the implementation paths above; it is never caller-supplied.
        for relative in (source_label_discrepancy.REGISTRY_RELATIVE_PATH,
                         DEFAULT_PART_PERIOD_CONTEXT_REGISTRY_PATH, DEFAULT_PART_PERIOD_COMMON204_REGISTRY_PATH,
                         DEFAULT_SOURCE_REPAIR_SPEC_PATH, DEFAULT_SECTION_CAPTION_AUTH_ENVELOPE_PATH):
            raw = (root.parents[1] / relative).read_bytes()
            refs.append({"path": relative, "size_bytes": len(raw), "sha256": sha256(raw).hexdigest()})
    except OSError as exc:
        raise _error("income-tax period inventory implementation dependency is absent") from exc
    return refs


def _period_inventory_check_dependencies_v1(state):
    started = perf_counter()
    state["metrics"]["dependency_checks"] += 1
    try:
        refs = _period_inventory_dependency_refs_v1()
    except GeminiJsonIncomeTaxFamilyV1Error:
        state["invalidated"] = True
        raise
    finally:
        state["metrics"]["dependency_check_seconds"] += perf_counter() - started
    if state["implementation_refs"] is None:
        state["implementation_refs"] = canonical_clone_v1(refs)
    elif not same_typed_json_v1(state["implementation_refs"], refs):
        state["invalidated"] = True
        raise _error("income-tax period inventory implementation changed during operation")
    return refs


def _period_inventory_key_v1(page_records, compiled_specs):
    state = _DOCUMENT_PERIOD_OPERATION.get()
    if state is None or not state["enabled"]:
        refs = _period_inventory_dependency_refs_v1()
    else:
        if state["closed"] or state["invalidated"]:
            raise _error("income-tax period inventory operation is closed or invalidated")
        refs = state["implementation_refs"]
        if refs is None:
            refs = _period_inventory_check_dependencies_v1(state)
    return canonical_json_sha256_v1({
        "format_version": "F39_OPERATION_LOCAL_SOURCE_PERIOD_INVENTORY_CACHE_V1",
        "page_records": list(page_records), "compiled_specs": dict(compiled_specs),
        "implementation_refs": refs,
    })


def _period_inventory_callable_fence_v1():
    # Supplemental invalidation for replaced entry points in a trusted Python
    # runtime. Function objects are NOT source identities, provenance keys or
    # receipt material. File/source/spec hashes remain the content key.
    return (
        _build_document_statement_period_inventory_uncached_v1,
        _document_report_scope_receipt, _document_comparative_flow_policy_receipt,
        _document_annual_period_receipt, _multitable_lane_axis,
        _owned_current_period_constraints, _note_report_scope_receipt,
        _printed_duration_lengths, _absolute_source_duration_semantics,
        _owned_relative_year_duration_evidence, _printed_ytd_sibling_period_evidence,
        _load_registered_part_period_registry_v1, _load_registered_part_period_common204_registry_v1,
        _load_registered_part_period_catalog_v1, _checked_registered_part_period_catalog_v1,
        _registered_part_original_identity_stage_v1, _compile_source_repairs,
        _registered_part_period_source_view_v1,
        _registered_part_period_contexts_v1, _approved_registered_part_period_loader_v1,
        select_declared_part_period_registry_variant_v1,
        replay_registered_part_period_contexts_v1, validate_registered_part_period_registry_v1,
        _registered_part_period_receipt, _owned_flow_report_quarter_constraint,
        _owned_note_report_quarter_constraint_v1,
        _cash_flow_partial_current_header_assertion_v1, _cash_flow_printed_period_control_v1,
        _recognition_immediate_ancestor_owner_v1, _recognition_expense_source_frontier,
        _recognition_rate_effect_forward_control,
        _competing_taxable_stage_control_v1,
        _load_registered_section_caption_auth_envelope_v1, _section_caption_core_ref_v1,
        _section_caption_pinned_bytes_v1, _section_caption_part_span_disjointness_v1,
        _prepare_income_tax_evaluation_records_v1, _recover_income_tax_query_cluster_v1,
        section_caption_core.validate_section_caption_registry_v1,
        section_caption_core.apply_registered_section_caption_repairs_v1,
        section_caption_core.replay_registered_section_caption_repairs_v1,
    )


def _load_json(path: str, *, message: str) -> dict[str, Any]:
    resolved = Path(__file__).resolve().parents[3] / path
    try:
        value = json.loads(resolved.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(message) from exc
    if type(value) is not dict:
        raise _error(message)
    return value


def _load_registered_part_period_registry_v1() -> tuple[dict[str, Any], dict[str, Any]]:
    """Read independently pinned approval bytes; a caller seal is not authority."""
    path = Path(__file__).resolve().parents[3] / DEFAULT_PART_PERIOD_CONTEXT_REGISTRY_PATH
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise _error("income-tax registered part-period authority is absent") from exc
    if sha256(raw).hexdigest() != _PART_PERIOD_CONTEXT_REGISTRY_SHA256:
        raise _error("income-tax registered part-period authority bytes differ")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise _error("income-tax registered part-period duplicate JSON key")
            result[key] = value
        return result

    def invalid_number(_token):
        raise _error("income-tax registered part-period nonfinite JSON number")

    try:
        registry = validate_registered_part_period_registry_v1(json.loads(
            raw, object_pairs_hook=pairs, parse_constant=invalid_number,
        ))
    except (UnicodeDecodeError, json.JSONDecodeError, GeminiJsonIncomeTaxPartPeriodContextV1Error) as exc:
        raise _error("income-tax registered part-period authority is invalid") from exc
    return registry, {"path": DEFAULT_PART_PERIOD_CONTEXT_REGISTRY_PATH,
                      "sha256": sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _load_registered_part_period_common204_registry_v1() -> tuple[dict[str, Any], dict[str, Any]]:
    """Read only the separately approved alternative; never replace c986."""
    path = Path(__file__).resolve().parents[3] / DEFAULT_PART_PERIOD_COMMON204_REGISTRY_PATH
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise _error("income-tax alternative part-period authority is absent") from exc
    if sha256(raw).hexdigest() != _PART_PERIOD_COMMON204_REGISTRY_SHA256:
        raise _error("income-tax alternative part-period authority bytes differ")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise _error("income-tax alternative part-period duplicate JSON key")
            result[key] = value
        return result

    def invalid_number(_token):
        raise _error("income-tax alternative part-period nonfinite JSON number")

    try:
        registry = validate_registered_part_period_registry_v1(json.loads(
            raw, object_pairs_hook=pairs, parse_constant=invalid_number,
        ))
    except (UnicodeDecodeError, json.JSONDecodeError, GeminiJsonIncomeTaxPartPeriodContextV1Error) as exc:
        raise _error("income-tax alternative part-period authority is invalid") from exc
    return registry, {"path": DEFAULT_PART_PERIOD_COMMON204_REGISTRY_PATH,
                      "sha256": sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _load_registered_part_period_catalog_v1() -> list[dict[str, Any]]:
    # Fixed trusted loader origin/order, not a caller's path/catalog/flag.
    return [{"registry": registry, "registry_ref": ref} for registry, ref in (
        _load_registered_part_period_registry_v1(),
        _load_registered_part_period_common204_registry_v1(),
    )]


def _checked_registered_part_period_catalog_v1(compiled_specs) -> list[dict[str, Any]]:
    catalog = _load_registered_part_period_catalog_v1()
    if (not same_typed_json_v1(catalog, compiled_specs.get("income_tax_part_period_registry_catalog"))
            or not same_typed_json_v1(catalog[0]["registry"], compiled_specs.get("income_tax_part_period_registry"))
            or not same_typed_json_v1(catalog[0]["registry_ref"], compiled_specs.get("income_tax_part_period_registry_ref"))):
        raise _error("income-tax compiled part-period authority drifted (catalog/refs)")
    return catalog


def _approved_registered_part_period_loader_v1(reference):
    """Resolve an exact fresh approved ref to a fixed loader, not a closure."""
    catalog = _load_registered_part_period_catalog_v1()
    loaders = (_load_registered_part_period_registry_v1, _load_registered_part_period_common204_registry_v1)
    matches = [loader for item, loader in zip(catalog, loaders, strict=True)
               if same_typed_json_v1(item["registry_ref"], reference)]
    if len(matches) != 1:
        raise _error("income-tax part-period loader ref is not one unique approved authority")
    return matches[0]


def _registered_part_original_identity_stage_v1(contexts, *, compiled_specs):
    """Bounded ORIGINAL==EVALUATION proof, not arbitrary clone provenance.

    The currently approved variants are all disjoint from old13. Any future
    registry with real original/evaluation differences must add an explicit
    independently source-bound original-record seam; this path will HOLD.
    """
    path = Path(__file__).resolve().parents[3] / DEFAULT_SOURCE_REPAIR_SPEC_PATH
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise _error("income-tax registered context old13 authority is absent") from exc
    if sha256(raw).hexdigest() != _PART_PERIOD_ORIGINAL_REPAIR_SHA256:
        raise _error("income-tax registered context old13 authority bytes differ")
    # Exact independent old13 bytes constrain the exclusion, not a caller list.
    repairs = _compile_source_repairs(json.loads(raw))
    supplied = compiled_specs.get("income_tax_source_repairs")
    if not same_typed_json_v1(supplied, repairs):
        raise _error("income-tax compiled old13 repair axis differs from freshly pinned authority")
    for context in contexts:
        components = [(item, ("page_json",)) for item in context["span_pages"]]
        components.extend((item, ("section_json",)) for item in [
            *context["heading_occurrences"], *context["period_occurrences"],
        ])
        components.extend((item, ("section_json", "table_json")) for item in context["target_tables"])
        for item, keys in components:
            for suffix in keys:
                if item["original_" + suffix + "_sha256"] != item["evaluation_" + suffix + "_sha256"]:
                    raise _error("income-tax registered context requires an explicit original-to-evaluation replay")
        vids = {page["page_json_version_id"] for page in context["span_pages"]}
        pdf = context["pdf_source"]
        for repair in repairs:
            if (repair["locator"]["page_json_version_id"] in vids
                    or repair["pdf_source"]["sha256"] == pdf["sha256"]
                    or repair["pdf_source"]["logical_name"] == pdf["logical_name"]):
                raise _error("income-tax registered ORIGINAL identity span intersects a repair authority")
    return {"rule": "EXACT_REGISTERED_ORIGINAL_EQUALS_EVALUATION_AND_FRESH_OLD13_SOURCE_EXCLUSION",
            "old13_spec_ref": {"path": DEFAULT_SOURCE_REPAIR_SPEC_PATH,
                              "sha256": sha256(raw).hexdigest(), "size_bytes": len(raw)},
            "original_and_evaluation_hash_domains_explicit": True,
            "private_clone_alone_authenticated_as_original": False}


def _registered_part_period_source_view_v1(page_records, *, compiled_specs):
    catalog = _checked_registered_part_period_catalog_v1(compiled_specs)
    # Preserve the old unrelated-legacy short circuit BEFORE deep validation.
    if not any(record.get("document_id") == context["document_id"]
               or record.get("source_logical_name") == context["pdf_source"]["logical_name"]
               or record.get("source_sha256") == context["pdf_source"]["sha256"]
               for record in page_records for item in catalog for context in item["registry"]["contexts"]):
        return {"contexts": [], "registry_ref": None, "source_variant_selection": None}
    before = canonical_json_sha256_v1({"records": list(page_records), "compiled": dict(compiled_specs)})
    try:
        selection = select_declared_part_period_registry_variant_v1(
            list(page_records), registries=[item["registry"] for item in catalog],
        )
        if selection["status"] != "EXACT_DECLARED_SOURCE_SPAN_SELECTION_NOT_APPROVAL":
            raise _error("income-tax related part-period source has no exact registered variant")
        item = catalog[selection["selected_registry_position"]]
        ids = selection["selected_context_ids"]
        selected = [context for context in item["registry"]["contexts"] if context["context_id"] in ids]
        stage = _registered_part_original_identity_stage_v1(selected, compiled_specs=compiled_specs)
        contexts = replay_registered_part_period_contexts_v1(page_records, registry=item["registry"])
    except GeminiJsonIncomeTaxPartPeriodContextV1Error as exc:
        raise _error("income-tax registered part-period source binding drifted") from exc
    if before != canonical_json_sha256_v1({"records": list(page_records), "compiled": dict(compiled_specs)}):
        raise _error("income-tax original part-period source/spec inputs changed during selection")
    material = {"declared_span_selection": selection, "registry_ref": item["registry_ref"],
                "original_identity_stage": stage,
                "source_span_selected_by_full_original_object_hashes": True,
                "runtime_document_ordinal_is_registration_authority": False}
    proof = {**material, "receipt_id": "gjitfav1:part-registry-selection:" + canonical_json_sha256_v1(material)}
    return {"contexts": contexts, "registry_ref": canonical_clone_v1(item["registry_ref"]),
            "source_variant_selection": proof}


def _registered_part_period_contexts_v1(
    page_records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    # Compatibility list API; full selected ref/proof lives in the source view.
    return _registered_part_period_source_view_v1(page_records, compiled_specs=compiled_specs)["contexts"]


def _compile_adapter_spec(value: Any) -> dict[str, Any]:
    expected = {
        "family_id": FAMILY_ID,
        "format_version": ADAPTER_SPEC_FORMAT_VERSION,
        "primary_duplicate_presentation_policy": (
            "EVIDENCE_FRONTIER_DOMINANT_PRESENTATION_THEN_UNIQUE_VND_WITH_EXACT_"
            "COMMON_ROLE_ECONOMIC_COMPATIBILITY"
        ),
        "primary_projection_policy": (
            "EXACT_PRIMARY_INCOME_STATEMENT_TAX_ROWS_AND_FINAL_DURATION_LANES_PRIVATE_CLONE_ONLY"
        ),
        "primary_unit_corroboration_policy": (
            "UNIQUE_CANONICAL_UNIT_FROM_AT_LEAST_TWO_EXPLICIT_PRIMARY_"
            "STATEMENT_TABLES_SAME_DOCUMENT"
        ),
        "supplemental_note_projection_policy": (
            "EXACT_TAX_OWNER_TWO_LANE_DIRECT_ROLES_WITH_SOURCE_EQUATION_"
            "AND_EXHAUSTIVE_ROW_RECEIPT"
        ),
        "source_repair_policy": (
            "PDF_RENDER_AUTHENTICATED_EXACT_CELL_OR_ROW_TRANSCRIPTION_PRIVATE_CLONE_ONLY"
        ),
    }
    if type(value) is not dict or not same_typed_json_v1(value, expected):
        raise _error("income-tax adapter spec is invalid")
    return canonical_clone_v1(value)


def _sha256_string(value: Any) -> bool:
    return bool(
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _compile_source_repairs(value: Any) -> list[dict[str, Any]]:
    if (
        type(value) is not dict
        or set(value) != {"family_id", "format_version", "render_contract", "repairs"}
        or value.get("family_id") != FAMILY_ID
        or value.get("format_version") != SOURCE_REPAIR_FORMAT_VERSION
        or value.get("render_contract")
        != {
            "alpha": False,
            "colorspace": "RGB",
            "format": "PNG",
            "matrix": [2, 2],
            "renderer": "PyMuPDF",
        }
        or type(value.get("repairs")) is not list
    ):
        raise _error("income-tax source-repair spec is invalid")
    checked = []
    identities = set()
    for raw in value["repairs"]:
        locator = raw.get("locator") if type(raw) is dict else None
        visual = raw.get("visual_evidence") if type(raw) is dict else None
        kind = raw.get("repair_kind") if type(raw) is dict else None
        fields = {
            "after_exact",
            "before_exact",
            "locator",
            "pdf_source",
            "repair_id",
            "repair_kind",
            "visual_evidence",
        }
        if kind == "MONEY_CELL_PDF_VISIBLE_DASH":
            fields.add("column_ordinal")
        if (
            type(raw) is not dict
            or set(raw) != fields
            or kind not in {"MONEY_CELL_PDF_VISIBLE_DASH", "ROW_PDF_VISIBLE_EXACT"}
            or type(locator) is not dict
            or set(locator)
            != {
                "page_json_version_id",
                "physical_page",
                "row_ordinal",
                "section_id",
                "table_id",
            }
            or not str(locator.get("page_json_version_id", "")).startswith("gfpstorev1:json:")
            or type(locator.get("physical_page")) is not int
            or locator["physical_page"] <= 0
            or type(locator.get("row_ordinal")) is not int
            or locator["row_ordinal"] <= 0
            or type(locator.get("section_id")) is not str
            or type(locator.get("table_id")) is not str
            or type(raw.get("pdf_source")) is not dict
            or set(raw["pdf_source"]) != {"logical_name", "sha256", "size_bytes"}
            or type(raw["pdf_source"].get("logical_name")) is not str
            or not raw["pdf_source"]["logical_name"]
            or not _sha256_string(raw["pdf_source"].get("sha256"))
            or type(raw["pdf_source"].get("size_bytes")) is not int
            or raw["pdf_source"]["size_bytes"] <= 0
            or type(visual) is not dict
            or set(visual) != {"crop_bbox_pixels", "crop_rgb_sha256", "page_render"}
            or type(visual.get("crop_bbox_pixels")) is not list
            or len(visual["crop_bbox_pixels"]) != 4
            or any(type(item) is not int or item < 0 for item in visual["crop_bbox_pixels"])
            or not _sha256_string(visual.get("crop_rgb_sha256"))
            or type(visual.get("page_render")) is not dict
            or set(visual["page_render"]) != {"height_pixels", "sha256", "width_pixels"}
            or not _sha256_string(visual["page_render"].get("sha256"))
            or any(
                type(visual["page_render"].get(field)) is not int
                or visual["page_render"][field] <= 0
                for field in ("height_pixels", "width_pixels")
            )
            or visual["crop_bbox_pixels"][0] >= visual["crop_bbox_pixels"][2]
            or visual["crop_bbox_pixels"][1] >= visual["crop_bbox_pixels"][3]
            or visual["crop_bbox_pixels"][2] > visual["page_render"]["width_pixels"]
            or visual["crop_bbox_pixels"][3] > visual["page_render"]["height_pixels"]
        ):
            raise _error("income-tax source repair is invalid")
        if kind == "MONEY_CELL_PDF_VISIBLE_DASH" and (
            raw.get("before_exact") is not None
            or raw.get("after_exact") != "-"
            or type(raw.get("column_ordinal")) is not int
            or raw["column_ordinal"] <= 0
        ):
            raise _error("income-tax dash source repair is invalid")
        if kind == "ROW_PDF_VISIBLE_EXACT" and (
            type(raw.get("before_exact")) is not dict
            or type(raw.get("after_exact")) is not dict
            or set(raw["before_exact"])
            != {"hierarchy_path_exact", "label_exact", "row_kind", "values_exact"}
            or set(raw["after_exact"]) != set(raw["before_exact"])
        ):
            raise _error("income-tax row source repair is invalid")
        material = {
            key: canonical_clone_v1(item) for key, item in raw.items() if key != "repair_id"
        }
        if raw.get("repair_id") != "gjitfav1:repair:" + canonical_json_sha256_v1(material):
            raise _error("income-tax source-repair identity drifted")
        identity = (
            raw["pdf_source"]["sha256"],
            locator["page_json_version_id"],
            locator["section_id"],
            locator["table_id"],
            locator["row_ordinal"],
            raw.get("column_ordinal"),
        )
        if identity in identities:
            raise _error("income-tax source-repair axis is duplicate")
        identities.add(identity)
        checked.append(canonical_clone_v1(raw))
    ordered = sorted(
        checked,
        key=lambda item: (
            item["pdf_source"]["sha256"],
            item["locator"]["physical_page"],
            item["locator"]["section_id"],
            item["locator"]["table_id"],
            item["locator"]["row_ordinal"],
            item.get("column_ordinal", 0),
        ),
    )
    if not same_typed_json_v1(checked, ordered):
        raise _error("income-tax source-repair axis is unordered")
    return checked


def _section_caption_pinned_bytes_v1(relative: str, expected_sha256: str) -> tuple[bytes, dict[str, Any]]:
    """Fixed independently approved local files only; no caller path or I/O grant."""
    root = Path(__file__).resolve().parents[3]
    path = root / relative
    try:
        if (path.resolve(strict=True) != path or not path.is_file()
                or any(entry.is_symlink() for entry in (path, *path.parents))):
            raise _error("income-tax caption authority origin is not canonical")
        before = path.stat()
        raw = path.read_bytes()
        after = path.stat()
    except OSError as exc:
        raise _error("income-tax caption authority file is absent") from exc
    def identity(value):
        return tuple(getattr(value, key) for key in (
            "st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns"))
    if (identity(before) != identity(after) or len(raw) != before.st_size or sha256(raw).hexdigest() != expected_sha256):
        raise _error("income-tax caption authority actual bytes differ from independent pin")
    return raw, {"path": relative, "sha256": expected_sha256, "size_bytes": len(raw)}


def _section_caption_core_ref_v1() -> dict[str, Any]:
    relative = "src/bctc_ai/evaluation/gemini_json_income_tax_section_caption_repair_v1.py"
    expected = Path(__file__).resolve().parents[3] / relative
    if (Path(section_caption_core.__file__).resolve() != expected
            or Path(section_caption_core.__spec__.origin).resolve() != expected):
        raise _error("income-tax caption clone core actual origin differs")
    return _section_caption_pinned_bytes_v1(relative, _SECTION_CAPTION_CLONE_CORE_SHA256)[1]


def _load_registered_section_caption_auth_envelope_v1() -> tuple[dict[str, Any], dict[str, Any]]:
    """Independent approved bytes, not caller-self-sealed registration authority.

    Pure compilation verifies declarations/disjoint old13 only. Runtime PDF,
    pixel, restore-lineage and source DB admission remain runner responsibilities.
    """
    raw, reference = _section_caption_pinned_bytes_v1(
        DEFAULT_SECTION_CAPTION_AUTH_ENVELOPE_PATH, _SECTION_CAPTION_AUTH_ENVELOPE_SHA256)
    _section_caption_core_ref_v1()
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise _error("income-tax caption envelope duplicate JSON key")
            result[key] = value
        return result
    def nonfinite(_value):
        raise _error("income-tax caption envelope nonfinite JSON number")
    try:
        envelope = json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)
        if (type(envelope) is not dict or set(envelope) != {
                "format_version", "family_id", "clone_registry", "legacy_source_repair_spec_ref", "source_version_lineages"}
                or envelope["format_version"] != "INCOME_TAX_REGISTERED_SECTION_CAPTION_AUTH_ENVELOPE_V1"
                or envelope["family_id"] != FAMILY_ID):
            raise _error("income-tax caption envelope schema differs")
        registry = section_caption_core.validate_section_caption_registry_v1(envelope["clone_registry"])
        legacy_raw, legacy_ref = _section_caption_pinned_bytes_v1(
            DEFAULT_SOURCE_REPAIR_SPEC_PATH, _SECTION_CAPTION_LEGACY_SPEC_SHA256)
        declared = envelope["legacy_source_repair_spec_ref"]
        if (type(declared) is not dict or set(declared) != {"path", "sha256", "size_bytes"}
                or declared["sha256"] != legacy_ref["sha256"] or type(declared["size_bytes"]) is not int
                or declared["size_bytes"] != legacy_ref["size_bytes"]):
            raise _error("income-tax caption envelope legacy authority differs")
        # Read the fixed project path above, never an arbitrary declared ref path.
        legacy = _compile_source_repairs(json.loads(legacy_raw, object_pairs_hook=pairs, parse_constant=nonfinite))
        if len(legacy) != 13:
            raise _error("income-tax caption envelope requires complete unchanged legacy13")
        lineages = envelope["source_version_lineages"]
        if type(lineages) is not list or len(lineages) != len(registry["sources"]):
            raise _error("income-tax caption envelope lineage axis differs")
        for source, lineage in zip(registry["sources"], lineages, strict=True):
            pdf = source["pdf_source"]
            if (source["document_id"] != section_caption_core._document_id(pdf)
                    or type(lineage) is not dict or set(lineage) != {
                        "document_id", "pdf_source", "restore_authorities", "pdf_object", "repair_evidence"}
                    or lineage["document_id"] != source["document_id"]
                    or not same_typed_json_v1(lineage["pdf_source"], pdf)
                    or not same_typed_json_v1(lineage["repair_evidence"], [
                        {"repair_id": repair["repair_id"], **repair["review_evidence"]} for repair in source["repairs"]])):
                raise _error("income-tax caption envelope source/review lineage differs")
            for repair in source["repairs"]:
                target = repair["locator"]
                for old in legacy:
                    same_source = same_typed_json_v1(old["pdf_source"], pdf)
                    same_name = old["pdf_source"]["logical_name"] == pdf["logical_name"]
                    same_vid = old["locator"]["page_json_version_id"] == target["page_json_version_id"]
                    if ((same_name or same_vid) and not same_source) or (same_source and (
                            same_vid or old["locator"]["physical_page"] == target["physical_page"])):
                        raise _error("income-tax caption/legacy page composition is not approved")
    except (OSError, KeyError, TypeError, ValueError, UnicodeError) as exc:
        raise _error("income-tax caption envelope declaration is invalid") from exc
    return canonical_clone_v1(envelope), reference


def _section_caption_part_span_disjointness_v1(original_records, sources, *, compiled_specs):
    """Fresh ORIGINAL-source selection only; no caption clone may select PART."""
    before = canonical_json_sha256_v1({
        "records": list(original_records), "sources": list(sources), "compiled": dict(compiled_specs),
    })
    # This preserves both fixed catalog loaders, exact source variant selection
    # and the independently pinned ORIGINAL==EVALUATION/old13 exclusion guard.
    view = _registered_part_period_source_view_v1(original_records, compiled_specs=compiled_specs)
    catalog = _checked_registered_part_period_catalog_v1(compiled_specs)
    selected_contexts = []
    if view["registry_ref"] is not None:
        matches = [item for item in catalog
                   if same_typed_json_v1(item["registry_ref"], view["registry_ref"])]
        ids = {item["context_id"] for item in view["contexts"]}
        if len(matches) != 1 or not ids:
            raise _error("income-tax caption/PART selected authority is ambiguous")
        selected_contexts = [context for context in matches[0]["registry"]["contexts"]
                             if context["context_id"] in ids]
        if {context["context_id"] for context in selected_contexts} != ids:
            raise _error("income-tax caption/PART selected context axis differs")
    for source in sources:
        for context in selected_contexts:
            pdf = context["pdf_source"]
            same_source = (source["document_id"] == context["document_id"]
                           and same_typed_json_v1(source["pdf_source"], pdf))
            # A partial source identity must never turn an overlap into absence.
            related = (source["document_id"] == context["document_id"]
                       or source["pdf_source"]["logical_name"] == pdf["logical_name"]
                       or source["pdf_source"]["sha256"] == pdf["sha256"])
            if related and not same_source:
                raise _error("income-tax caption/PART partial source identity")
            if not same_source:
                continue
            vids = {page["page_json_version_id"] for page in context["span_pages"]}
            physical_pages = {page["physical_page"] for page in context["span_pages"]}
            if any(repair["locator"]["page_json_version_id"] in vids
                   or repair["locator"]["physical_page"] in physical_pages
                   for repair in source["repairs"]):
                raise _error("income-tax caption target intersects registered part-period span")
    if before != canonical_json_sha256_v1({
            "records": list(original_records), "sources": list(sources), "compiled": dict(compiled_specs)}):
        raise _error("income-tax caption/PART disjointness changed original inputs")
    material = {
        "rule": "FRESH_ORIGINAL_SELECTED_PART_SPAN_DISJOINT_FROM_ALL_APPLICABLE_CAPTION_TARGET_PAGES",
        "approved_catalog_refs": [item["registry_ref"] for item in catalog],
        "selected_registry_ref": view["registry_ref"],
        "selected_source_variant_receipt": view["source_variant_selection"],
        "selected_context_ids": [context["context_id"] for context in selected_contexts],
        "checked_caption_repair_ids": [repair["repair_id"] for source in sources for repair in source["repairs"]],
        "pdf_pixels_or_source_database_authenticated": False,
        "scope_entity_unit_period_value_or_acceptance_permission": False,
    }
    return {**material, "receipt_id": "gjitfav1:caption-part-disjointness:" + canonical_json_sha256_v1(material)}


def _prepare_income_tax_evaluation_records_v1(
    original_records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Always rebuild caption then legacy13 from ORIGINAL selected records."""
    envelope, reference = _load_registered_section_caption_auth_envelope_v1()
    core_ref = _section_caption_core_ref_v1()
    if any(not same_typed_json_v1(compiled_specs.get(key), value) for key, value in (
            ("income_tax_section_caption_auth_envelope", envelope),
            ("income_tax_section_caption_auth_envelope_ref", reference),
            ("income_tax_section_caption_clone_core_ref", core_ref))):
        raise _error("income-tax compiled caption approval/ref/core differs from fresh authority")
    if type(original_records) not in {list, tuple} or not original_records:
        raise _error("income-tax caption original record axis is absent")
    # Two independent ordering domains. The caller's raw order and old13
    # receipt order remain unchanged. Only the pure caption-core traversal and
    # projection content hashes use a private physical/selected canonical axis.
    raw_original = canonical_clone_v1(list(original_records))
    raw_input_sha256 = canonical_json_sha256_v1(raw_original)
    identity = {(item["document_id"], item["document_ordinal"], item["source_logical_name"], item["source_sha256"])
                for item in raw_original}
    if len(identity) != 1 or any(type(item[key]) is not int or item[key] <= 0 for item in raw_original
                               for key in ("document_ordinal", "physical_page", "selected_page_ordinal")):
        raise _error("income-tax caption original source axis is ambiguous")
    versions = {item["page_json_version_id"] for item in raw_original}
    if (len(versions) != len(raw_original)
            or len({item["physical_page"] for item in raw_original}) != len(raw_original)
            or len({item["selected_page_ordinal"] for item in raw_original}) != len(raw_original)):
        raise _error("income-tax caption original selected axis is duplicate")
    original = sorted(canonical_clone_v1(raw_original),
                      key=lambda item: (item["physical_page"], item["selected_page_ordinal"]))
    if [item["selected_page_ordinal"] for item in original] != sorted(
            item["selected_page_ordinal"] for item in original):
        raise _error("income-tax caption original physical/selected axes disagree")
    before = canonical_json_sha256_v1(original)
    first = original[0]
    sources = []
    for source in envelope["clone_registry"]["sources"]:
        axes = (source["document_id"] == first["document_id"],
                source["pdf_source"]["logical_name"] == first["source_logical_name"],
                source["pdf_source"]["sha256"] == first["source_sha256"])
        if any(axes):
            if not all(axes) or source["pdf_source"]["sha256"] != first["source_sha256"]:
                raise _error("income-tax caption partially matching registered source")
            sources.append(source)
        elif any(repair["locator"]["page_json_version_id"] in versions for repair in source["repairs"]):
            raise _error("income-tax caption foreign source reuses selected VID")
    part_disjointness = _section_caption_part_span_disjointness_v1(
        original, sources, compiled_specs=compiled_specs)
    caption_records, clone_receipts = canonical_clone_v1(original), []
    if sources:
        if len(sources) != 1:
            raise _error("income-tax caption source registration is not unique")
        legacy_raw, _ = _section_caption_pinned_bytes_v1(DEFAULT_SOURCE_REPAIR_SPEC_PATH, _SECTION_CAPTION_LEGACY_SPEC_SHA256)
        legacy_spec = json.loads(legacy_raw)
        approved_legacy = _compile_source_repairs(legacy_spec)
        if (not same_typed_json_v1(approved_legacy, compiled_specs["income_tax_source_repairs"])
                or compiled_specs.get("income_tax_source_repair_spec_sha256") != canonical_json_sha256_v1(legacy_spec)):
            raise _error("income-tax caption cannot use a substituted legacy repair axis")
        legacy_axis = [{"repair_id": item["repair_id"], "pdf_source": item["pdf_source"],
                        "page_json_version_id": item["locator"]["page_json_version_id"],
                        "physical_page": item["locator"]["physical_page"]} for item in approved_legacy]
        try:
            caption_records, receipt = section_caption_core.apply_registered_section_caption_repairs_v1(
                original, registry=envelope["clone_registry"], source_pdf_identity=sources[0]["pdf_source"],
                legacy_repair_page_axis=legacy_axis)
            section_caption_core.replay_registered_section_caption_repairs_v1(
                original, caption_records, receipt, registry=envelope["clone_registry"],
                source_pdf_identity=sources[0]["pdf_source"], legacy_repair_page_axis=legacy_axis)
        except section_caption_core.SectionCaptionRepairV1Error as exc:
            raise _error("income-tax caption original-source clone replay drifted") from exc
        clone_receipts.append(receipt)
    caption_by_version = {record["page_json_version_id"]: record for record in caption_records}
    caller_order_caption_records = [caption_by_version[record["page_json_version_id"]] for record in raw_original]
    evaluation, legacy_receipts = _apply_source_repairs(
        caller_order_caption_records, compiled_specs=compiled_specs)
    canonical_evaluation = sorted(canonical_clone_v1(evaluation),
                                 key=lambda item: (item["physical_page"], item["selected_page_ordinal"]))
    material = {
        "format_version": "INCOME_TAX_ORDERED_SECTION_CAPTION_AND_LEGACY_PROJECTION_V1",
        "status": "EXACT_PRIVATE_CAPTION_PROJECTION_NOT_PDF_AUTHENTICATION" if sources else "NOT_APPLICABLE_EXACT_EMPTY_CAPTION_AXIS",
        "envelope_ref": reference, "clone_core_ref": core_ref,
        "registry_object_canonical_sha256": canonical_json_sha256_v1(envelope["clone_registry"]),
        "source_page_axis": [{key: item[key] for key in (
            "document_id", "document_ordinal", "source_logical_name", "source_sha256", "page_json_version_id",
            "physical_page", "selected_page_ordinal")} for item in original],
        "original_records_object_canonical_sha256": before,
        "caption_stage_records_object_canonical_sha256": canonical_json_sha256_v1(caption_records),
        "evaluation_records_object_canonical_sha256": canonical_json_sha256_v1(canonical_evaluation),
        "part_period_disjointness_receipt": part_disjointness,
        "ordered_caption_clone_receipts": clone_receipts,
        "ordered_caption_repair_ids": [repair["repair_id"] for source in sources for repair in source["repairs"]],
        "ordered_legacy_repair_receipts": legacy_receipts,
        "stage_order": ["ORIGINAL", "DISJOINT_PRIVATE_SECTION_CAPTIONS", "UNCHANGED_LEGACY13_PRIVATE_TRANSCRIPTIONS"],
        "source_database_pdf_or_pixels_authenticated": False,
        "source_values_changed_by_caption_stage": False,
        "permission_grants": {key: False for key in ("scope", "entity", "unit", "period", "source_value", "acceptance", "export")},
    }
    if raw_input_sha256 != canonical_json_sha256_v1(list(original_records)):
        raise _error("income-tax caption preparation mutated original records")
    return evaluation, legacy_receipts, {**material, "receipt_id": "gjitfav1:caption-projection:" + canonical_json_sha256_v1(material)}


def _private_specs(
    topology_spec: Mapping[str, Any],
    evaluation_spec: Mapping[str, Any],
    schema_binding_spec: Mapping[str, Any],
    *,
    root_component_roles: Sequence[str],
    root_policy: str,
) -> dict[str, Any]:
    topology = canonical_clone_v1(topology_spec)
    topology["required_role_combinations"] = [
        ["CURRENT_TAX_PARENT"],
        ["DEFERRED_TAX_NET"],
    ]
    evaluation = canonical_clone_v1(evaluation_spec)
    evaluation["family_root_requirement"] = "OPTIONAL"
    evaluation["minimum_declared_detail_role_count"] = 1
    evaluation["minimum_source_visible_root_component_count"] = 1
    evaluation["ordered_role_scopes"] = []
    evaluation["ordered_role_scope_projections"] = []
    evaluation["root_component_roles"] = list(root_component_roles)
    evaluation["unmapped_direct_family_row_policy"] = "IGNORE"
    schema = canonical_clone_v1(schema_binding_spec)
    schema["root_mapping_policy"] = root_policy
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(topology, evaluation, schema)


def _supplemental_specs(
    topology_spec: Mapping[str, Any],
    evaluation_spec: Mapping[str, Any],
    schema_binding_spec: Mapping[str, Any],
) -> dict[str, Any]:
    topology = canonical_clone_v1(topology_spec)
    topology["required_role_combinations"] = [
        [role] for role in _SUPPLEMENTAL_DIRECT_ROLES
    ]
    evaluation = canonical_clone_v1(evaluation_spec)
    evaluation["family_root_requirement"] = "OPTIONAL"
    evaluation["minimum_declared_detail_role_count"] = 1
    evaluation["minimum_source_visible_root_component_count"] = 1
    evaluation["ordered_role_scopes"] = []
    evaluation["ordered_role_scope_projections"] = []
    evaluation["root_component_roles"] = list(_SUPPLEMENTAL_PROJECTED_ROLES)
    evaluation["unmapped_direct_family_row_policy"] = "IGNORE"
    schema = canonical_clone_v1(schema_binding_spec)
    schema["root_mapping_policy"] = "STRUCTURAL_CONTEXT_ONLY"
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        topology, evaluation, schema
    )


def _original_note_basis_specs(
    topology_spec: Mapping[str, Any],
    evaluation_spec: Mapping[str, Any],
    schema_binding_spec: Mapping[str, Any],
    *, basis: str,
) -> dict[str, Any]:
    """Change only measurement-basis bindings, never accounting/query policies.

    These specs evaluate an original table, not the canonical supplemental
    projection.  INCOME must retain its ordered source-only-to-income projection;
    RATE cannot retain that projection because its adjustments are tax effects.
    Private aliases are usable only through the authenticated RATE-table builder.
    """
    if type(basis) is not str or basis not in _ORIGINAL_BASIS_ROLES:
        raise _error("income-tax original measurement basis is invalid")
    topology = canonical_clone_v1(topology_spec)
    topology["required_role_combinations"] = (
        [["PROFIT_BEFORE_TAX", "CURRENT_TAX_AT_RATE", "CURRENT_TAX_PARENT"],
         ["PROFIT_BEFORE_TAX", "STATUTORY_TAX_AMOUNT_SOURCE_ONLY", "CURRENT_TAX_PARENT"]]
        if basis == "RATE" else [["PROFIT_BEFORE_TAX", "TAXABLE_INCOME"]]
    )
    if basis == "RATE":
        for child in topology["children"]:
            additions = _ORIGINAL_RATE_PRIVATE_ALIASES.get(child["role"], ())
            if additions:
                # An unscoped exact matcher remains subject to original-table
                # ownership and basis-frontier checks at the caller boundary.
                child["matchers"].append({"aliases": list(additions), "within_role": None})
    evaluation = canonical_clone_v1(evaluation_spec)
    roles = set(_ORIGINAL_BASIS_ROLES[basis])
    evaluation["validation_only_roles"] = [
        child["role"] for child in topology["children"] if child["role"] not in roles
    ]
    if basis == "RATE":
        evaluation["ordered_role_scope_projections"] = []
    schema = canonical_clone_v1(schema_binding_spec)
    schema["role_bindings"] = [item for item in schema["role_bindings"] if item["role"] in roles]
    schema["root_mapping_policy"] = "STRUCTURAL_CONTEXT_ONLY"
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(topology, evaluation, schema)


def compile_gemini_json_income_tax_family_specs_v1(
    topology_spec: Any,
    evaluation_spec: Any,
    schema_binding_spec: Any,
    adapter_spec: Any | None = None,
    source_repair_spec: Any | None = None,
) -> dict[str, Any]:
    """Compile the shared family plus narrow private primary projections."""

    base = compile_gemini_json_multitable_hierarchical_family_specs_v1(
        topology_spec, evaluation_spec, schema_binding_spec
    )
    if base.get("topology", {}).get("family_id") != FAMILY_ID:
        raise _error("income-tax adapter received another family")
    adapter_raw = (
        _load_json(DEFAULT_ADAPTER_SPEC_PATH, message="income-tax adapter spec is absent")
        if adapter_spec is None
        else adapter_spec
    )
    repairs_raw = (
        _load_json(
            DEFAULT_SOURCE_REPAIR_SPEC_PATH,
            message="income-tax source-repair spec is absent",
        )
        if source_repair_spec is None
        else source_repair_spec
    )
    base["income_tax_adapter_spec"] = _compile_adapter_spec(adapter_raw)
    base["income_tax_adapter_spec_sha256"] = canonical_json_sha256_v1(adapter_raw)
    base["income_tax_source_repairs"] = _compile_source_repairs(repairs_raw)
    base["income_tax_source_repair_spec_sha256"] = canonical_json_sha256_v1(repairs_raw)
    catalog = _load_registered_part_period_catalog_v1()
    base["income_tax_part_period_registry"] = canonical_clone_v1(catalog[0]["registry"])
    base["income_tax_part_period_registry_ref"] = canonical_clone_v1(catalog[0]["registry_ref"])
    base["income_tax_part_period_registry_catalog"] = canonical_clone_v1(catalog)
    caption_envelope, caption_ref = _load_registered_section_caption_auth_envelope_v1()
    base["income_tax_section_caption_auth_envelope"] = caption_envelope
    base["income_tax_section_caption_auth_envelope_ref"] = caption_ref
    base["income_tax_section_caption_clone_core_ref"] = _section_caption_core_ref_v1()
    base["income_tax_original_basis_source_specs"] = canonical_clone_v1({
        "topology": topology_spec, "evaluation": evaluation_spec, "schema": schema_binding_spec,
    })
    base["income_tax_primary_both_specs"] = _private_specs(
        topology_spec,
        evaluation_spec,
        schema_binding_spec,
        root_component_roles=["CURRENT_TAX_PARENT", "DEFERRED_TAX_NET"],
        root_policy="SOURCE_VISIBLE_TOTAL_PROVEN_BY_EXACT_EQUATION_ONLY",
    )
    base["income_tax_primary_current_specs"] = _private_specs(
        topology_spec,
        evaluation_spec,
        schema_binding_spec,
        root_component_roles=["CURRENT_TAX_PARENT"],
        root_policy="SOURCE_VISIBLE_TOTAL_PROVEN_BY_EXACT_EQUATION_ONLY",
    )
    base["income_tax_primary_detail_specs"] = _private_specs(
        topology_spec,
        evaluation_spec,
        schema_binding_spec,
        root_component_roles=["CURRENT_TAX_PARENT", "DEFERRED_TAX_NET"],
        root_policy="STRUCTURAL_CONTEXT_ONLY",
    )
    base["income_tax_supplemental_specs"] = _supplemental_specs(
        topology_spec,
        evaluation_spec,
        schema_binding_spec,
    )
    for basis in _ORIGINAL_BASIS_ROLES:
        base[f"income_tax_original_{basis.lower()}_specs"] = _original_note_basis_specs(
            topology_spec, evaluation_spec, schema_binding_spec, basis=basis,
        )
    return base


def _reseal_cluster(cluster: Mapping[str, Any], **updates: Any) -> dict[str, Any]:
    material = {
        key: canonical_clone_v1(value) for key, value in cluster.items() if key != "cluster_id"
    }
    material.update(canonical_clone_v1(updates))
    return {
        **material,
        "cluster_id": "gjmthfcv1:cluster:" + canonical_json_sha256_v1(material),
    }


def _apply_source_repairs(
    page_records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records = [canonical_clone_v1(item) for item in page_records]
    by_version = {item["page_json_version_id"]: item for item in records}
    if len(by_version) != len(records):
        raise _error("income-tax selected page axis is duplicate")
    source_sha256s = {item.get("source_sha256") for item in records}
    if len(source_sha256s) != 1:
        raise _error("income-tax selected document source axis is invalid")
    receipts = []
    source_sha256 = next(iter(source_sha256s))
    for repair in compiled_specs["income_tax_source_repairs"]:
        if repair["pdf_source"]["sha256"] != source_sha256:
            continue
        locator = repair["locator"]
        record = by_version.get(locator["page_json_version_id"])
        if (
            record is None
            or record.get("physical_page") != locator["physical_page"]
            or record.get("source_logical_name") != repair["pdf_source"]["logical_name"]
        ):
            raise _error("income-tax source-repair selected page drifted")
        page = record["page_json"]
        before_page_sha = canonical_json_sha256_v1(page)
        try:
            _section, table = _source_table(
                page,
                section_id=locator["section_id"],
                table_id=locator["table_id"],
            )
            row = table["rows"][locator["row_ordinal"] - 1]
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise _error("income-tax source-repair locator drifted") from exc
        if repair["repair_kind"] == "MONEY_CELL_PDF_VISIBLE_DASH":
            try:
                before = row["values_exact"][repair["column_ordinal"] - 1]
            except (IndexError, KeyError, TypeError) as exc:
                raise _error("income-tax source-repair cell drifted") from exc
            if before != repair["before_exact"]:
                raise _error("income-tax source-repair before image drifted")
            row["values_exact"][repair["column_ordinal"] - 1] = repair["after_exact"]
        else:
            before = {
                key: canonical_clone_v1(row.get(key))
                for key in (
                    "hierarchy_path_exact",
                    "label_exact",
                    "row_kind",
                    "values_exact",
                )
            }
            if not same_typed_json_v1(before, repair["before_exact"]):
                raise _error("income-tax source-repair row before image drifted")
            row.clear()
            row.update(canonical_clone_v1(repair["after_exact"]))
        after_page_sha = canonical_json_sha256_v1(page)
        material = {
            "after_page_json_sha256": after_page_sha,
            "before_page_json_sha256": before_page_sha,
            "repair": canonical_clone_v1(repair),
            "rule": (
                "PDF_RENDER_AUTHENTICATED_VISIBLE_SOURCE_TRANSCRIPTION_TO_PRIVATE_"
                "PAGE_CLONE_NO_BLANK_OR_VALUE_INFERENCE"
            ),
            "source_repair_spec_sha256": compiled_specs["income_tax_source_repair_spec_sha256"],
        }
        receipts.append(
            {
                **material,
                "receipt_id": "gjitfav1:repair-receipt:" + canonical_json_sha256_v1(material),
            }
        )
    return records, receipts


def _primary_root_printed_text(value: Any) -> str | None:
    """Permit declared layout, not glyphs erased by the legacy normalizer."""
    if type(value) is not str:
        return None
    layout = value.replace("\\n", "\n")
    if any(unicodedata.category(char) == "Cc" and char not in "\t\r\n" for char in layout):
        return None
    return _recognition_printed_text(" ".join(layout.split()))


def _primary_quoted_tndn_root_label_matches(value: Any) -> bool:
    """Recognize one whole PRIMARY label, not NOTE or population authority.

    Keep punctuation and the literal ASCII quoted acronym. Folding Vietnamese
    letters cannot manufacture an acronym by erasing its source annotations.
    Layout recognition never changes the original row, unit, period or sign.
    """
    if type(value) is not str:
        return False
    layout = value.replace("\\n", "\n")
    if any(unicodedata.category(char) == "Cc" and char not in "\t\r\n" for char in layout):
        return False
    if re.search(r'(?<!\S)\("[Tt][Nn][Dd][Nn]"\)\s*\Z', layout) is None:
        return False
    printed = _primary_root_printed_text(value)
    return re.fullmatch(r'chi phi thue thu nhap doanh nghiep \("tndn"\)', printed or "") is not None


def _legacy_primary_role_for_label(value: Any) -> str | None:
    """Preserve existing role vocabulary for shared NOTE/ancestry consumers."""
    label = _without_leading_ordinal(_normalized(value))
    if "hien hanh" in label and "chi phi thue" in label:
        return "CURRENT_TAX_PARENT"
    if "hoan lai" in label and (
        "chi phi thue" in label or "loi ich thue" in label or "thu nhap thue" in label
    ):
        return "DEFERRED_TAX_NET"
    if label in _ROOT_LABELS:
        return "FAMILY_ROOT_TOTAL"
    return None


def _role_for_primary_label(value: Any) -> str | None:
    role = _legacy_primary_role_for_label(value)
    if role == "FAMILY_ROOT_TOTAL" and (
        _primary_root_printed_text(value) is None
        or any(char in "\"'" or unicodedata.category(char) in {"Pi", "Pf"} for char in value)
        and not _primary_quoted_tndn_root_label_matches(value)
    ):
        # E.g. a fullwidth quoted acronym must not disappear and manufacture a
        # legacy expanded ROOT before the literal quoted-label rule can veto it.
        return None
    if role is not None:
        return role
    return "FAMILY_ROOT_TOTAL" if _primary_quoted_tndn_root_label_matches(value) else None


def _record_locator(record: Mapping[str, Any], *, section_id: str, table_id: str) -> dict[str, Any]:
    return {
        key: canonical_clone_v1(record[key])
        for key in (
            "document_id",
            "document_ordinal",
            "page_json_version_id",
            "physical_page",
            "selected_page_ordinal",
            "source_logical_name",
            "source_sha256",
        )
    } | {"section_id": section_id, "table_id": table_id}


def _primary_statement_unit_corroboration(
    page_records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> dict[str, Any] | None:
    sources = []
    for record in page_records:
        page = record["page_json"]
        if page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            continue
        for section_ordinal, section in enumerate(page.get("sections") or [], start=1):
            if type(section) is not dict or section.get("content_kind") != "PRIMARY_STATEMENT":
                continue
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                if type(table) is not dict:
                    continue
                unit = _unit_axis(table, compiled_specs=compiled_specs)
                if not unit.get("complete"):
                    if not _local_money_unit_is_truly_absent(unit):
                        return None
                    continue
                if unit.get("canonical_unit") not in {"MILLION_VND", "VND"}:
                    return None
                sources.append(
                    {
                        "canonical_unit": unit["canonical_unit"],
                        "evidence": canonical_clone_v1(unit["evidence"]),
                        "locator": _record_locator(
                            record,
                            section_id=f"s{section_ordinal}",
                            table_id=f"t{table_ordinal}",
                        ),
                        "statement_type": section.get("statement_type"),
                        "table_json_sha256": canonical_json_sha256_v1(table),
                    }
                )
    canonical_units = {item["canonical_unit"] for item in sources}
    if len(sources) < 2 or len(canonical_units) != 1:
        return None
    material = {
        "canonical_unit": next(iter(canonical_units)),
        "rule": (
            "AT_LEAST_TWO_DISTINCT_PRIMARY_STATEMENT_TABLES_EXPLICITLY_DECLARE_"
            "ONE_CANONICAL_UNIT_NO_VALUE_OR_MAGNITUDE_INFERENCE"
        ),
        "sources": sources,
    }
    return {
        **material,
        "receipt_id": "gjitfav1:primary-unit:" + canonical_json_sha256_v1(material),
    }


def _local_money_unit_is_truly_absent(unit_axis: Mapping[str, Any]) -> bool:
    """Permit document corroboration only when no local unit surface exists."""

    return bool(
        not unit_axis.get("complete")
        and unit_axis.get("canonical_unit") is None
        and unit_axis.get("evidence") == []
        and unit_axis.get("undeclared_evidence") == []
        and unit_axis.get("document_unit_context_evidence") is None
    )


def _primary_invalid_source_role_rows(
    page_records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    invalid = []
    for record in page_records:
        page = record["page_json"]
        if page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            continue
        for section_ordinal, section in enumerate(page.get("sections") or [], start=1):
            if (
                type(section) is not dict
                or section.get("content_kind") != "PRIMARY_STATEMENT"
                or section.get("statement_type") != "INCOME_STATEMENT"
            ):
                continue
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                if type(table) is not dict:
                    continue
                lane = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
                money_ordinals = lane.get("money_column_ordinals")
                lane_usable = bool(lane.get("complete") and type(money_ordinals) is list and len(money_ordinals) == 2)
                unit = _unit_axis(table, compiled_specs=compiled_specs)
                accepted_kinds = compiled_specs.get("accepted_value_column_kinds", ["MONEY"])
                unknown_unit_columns = [ordinal for ordinal, column in enumerate(table["columns"], 1)
                                        if column.get("value_kind") == "UNKNOWN" and "UNKNOWN" in accepted_kinds]
                if unknown_unit_columns:
                    # Veto-only unit inspection of configured UNKNOWN value
                    # columns, matching the shared evaluator's private unit
                    # view. This neither promotes raw columns nor grants any
                    # amount, period, unit or mapping acceptance.
                    unit_view = {**table, "columns": [
                        {**column, "value_kind": "MONEY"} if ordinal in unknown_unit_columns else column
                        for ordinal, column in enumerate(table["columns"], 1)
                    ]}
                    unit = {**_unit_axis(unit_view, compiled_specs=compiled_specs),
                            "veto_only_unknown_column_unit_view": {
                                "column_ordinals": unknown_unit_columns,
                                "source_column_kinds_modified": False,
                                "positive_unit_permission_granted": False,
                            }}
                explicit_unit_conflict = bool(set(unit.get("reasons") or []) & {
                    "CONFLICTING_EXPLICIT_MONEY_UNITS",
                    "MULTIPLE_CONFLICTING_DECLARED_MONEY_UNITS_ON_ONE_SURFACE",
                })
                # A declared but unaccepted table unit remains contrary source
                # evidence. The shared resolver can retain accepted column
                # units and report only EXPLICIT_MONEY_UNIT_IS_NOT_ACCEPTED;
                # it must not let that mixed-scale tax table disappear behind
                # an otherwise valid NOTE-only presentation.
                explicit_unit_identities = {
                    (item["canonical_unit"], item["magnitude_power10"])
                    for item in unit.get("evidence") or []
                }
                explicit_unit_conflict |= len(explicit_unit_identities) > 1
                if not lane_usable and not explicit_unit_conflict:
                    continue
                for row_ordinal, row in enumerate(table.get("rows") or [], start=1):
                    if type(row) is not dict:
                        continue
                    role = _role_for_primary_label(row.get("label_exact"))
                    if role is None:
                        continue
                    values = row.get("values_exact")
                    selected = [
                        values[ordinal - 1]
                        if type(values) is list and ordinal <= len(values)
                        else None
                        for ordinal in (money_ordinals if lane_usable else [])
                    ]
                    # An observed PRIMARY tax row with conflicting explicit
                    # units is invalid source evidence, not an absent optional
                    # presentation that a valid NOTE is allowed to hide.
                    reasons = ["INVALID_PRIMARY_SOURCE_MONEY_UNIT_CONFLICT"] if explicit_unit_conflict else []
                    for value in selected:
                        try:
                            parsed = _source_money(value)
                        except (TypeError, ValueError):
                            reasons.append("INVALID_PRIMARY_SOURCE_MONEY_CELL")
                        else:
                            reasons.extend(parsed.get("reasons", []))
                    if reasons:
                        invalid.append(
                            {
                                "locator": _record_locator(
                                    record,
                                    section_id=f"s{section_ordinal}",
                                    table_id=f"t{table_ordinal}",
                                ),
                                "reasons": sorted(set(reasons)),
                                "role": role,
                                "row_ordinal": row_ordinal,
                                "source_values_exact": canonical_clone_v1(selected),
                                "table_json_sha256": canonical_json_sha256_v1(table),
                                **({"source_unit_axis": canonical_clone_v1(unit),
                                    "source_lane_axis": canonical_clone_v1(lane),
                                    "source_row_exact": canonical_clone_v1(row),
                                    "source_money_columns_exact": [
                                        {"column_ordinal": ordinal, "source_column_exact": canonical_clone_v1(column)}
                                        for ordinal, column in enumerate(table["columns"], 1)
                                        if column["value_kind"] in accepted_kinds
                                    ]} if explicit_unit_conflict else {}),
                            }
                        )
    return invalid


def _primary_duplicate_source_role_rows(
    page_records: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    duplicates = []
    for record in page_records:
        page = record["page_json"]
        if page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            continue
        for section_ordinal, section in enumerate(page.get("sections") or [], start=1):
            if (
                type(section) is not dict
                or section.get("content_kind") != "PRIMARY_STATEMENT"
                or section.get("statement_type") != "INCOME_STATEMENT"
            ):
                continue
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                if type(table) is not dict:
                    continue
                by_role: dict[str, list[dict[str, Any]]] = {}
                for row_ordinal, row in enumerate(table.get("rows") or [], start=1):
                    if type(row) is not dict:
                        continue
                    role = _role_for_primary_label(row.get("label_exact"))
                    if role is not None:
                        by_role.setdefault(role, []).append(
                            {
                                "label_exact": row.get("label_exact"),
                                "row_ordinal": row_ordinal,
                                "values_exact": canonical_clone_v1(row.get("values_exact")),
                            }
                        )
                for role, rows in by_role.items():
                    if len(rows) > 1:
                        duplicates.append(
                            {
                                "locator": _record_locator(
                                    record,
                                    section_id=f"s{section_ordinal}",
                                    table_id=f"t{table_ordinal}",
                                ),
                                "role": role,
                                "rows": rows,
                                "table_json_sha256": canonical_json_sha256_v1(table),
                            }
                        )
    return duplicates


def _primary_equation_mismatch_axis(
    page_records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    mismatches = []
    for record in page_records:
        page = record["page_json"]
        if page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            continue
        for section_ordinal, section in enumerate(page.get("sections") or [], start=1):
            if (
                type(section) is not dict
                or section.get("content_kind") != "PRIMARY_STATEMENT"
                or section.get("statement_type") != "INCOME_STATEMENT"
            ):
                continue
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                if type(table) is not dict:
                    continue
                lane = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
                money_ordinals = lane.get("money_column_ordinals")
                if (
                    not lane.get("complete")
                    or type(money_ordinals) is not list
                    or len(money_ordinals) != 2
                ):
                    continue
                by_role: dict[str, Mapping[str, Any]] = {}
                duplicate = False
                for row in table.get("rows") or []:
                    if type(row) is not dict:
                        continue
                    role = _role_for_primary_label(row.get("label_exact"))
                    if role is None:
                        continue
                    if role in by_role:
                        duplicate = True
                        break
                    by_role[role] = row
                if duplicate or not {"FAMILY_ROOT_TOTAL", "CURRENT_TAX_PARENT"}.issubset(
                    by_role
                ):
                    continue
                parsed_by_role = {}
                invalid = False
                for role in ("FAMILY_ROOT_TOTAL", "CURRENT_TAX_PARENT", "DEFERRED_TAX_NET"):
                    row = by_role.get(role)
                    if row is None:
                        parsed_by_role[role] = [0, 0]
                        continue
                    values = row.get("values_exact")
                    selected = [
                        values[ordinal - 1]
                        if type(values) is list and ordinal <= len(values)
                        else None
                        for ordinal in money_ordinals
                    ]
                    parsed = []
                    for value in selected:
                        try:
                            item = _source_money(value)
                        except (TypeError, ValueError):
                            invalid = True
                            break
                        if item.get("reasons"):
                            invalid = True
                            break
                        parsed.append(item.get("coefficient"))
                    if invalid:
                        break
                    parsed_by_role[role] = parsed
                if invalid:
                    continue
                lane_mismatches = []
                for ordinal, (root, current, deferred) in enumerate(
                    zip(
                        parsed_by_role["FAMILY_ROOT_TOTAL"],
                        parsed_by_role["CURRENT_TAX_PARENT"],
                        parsed_by_role["DEFERRED_TAX_NET"],
                        strict=True,
                    )
                ):
                    if root is None or current is None or deferred is None:
                        continue
                    if current + deferred != root:
                        lane_mismatches.append(
                            {
                                "current": current,
                                "deferred": deferred,
                                "lane_ordinal": ordinal,
                                "root": root,
                            }
                        )
                if lane_mismatches:
                    mismatches.append(
                        {
                            "lane_mismatches": lane_mismatches,
                            "locator": _record_locator(
                                record,
                                section_id=f"s{section_ordinal}",
                                table_id=f"t{table_ordinal}",
                            ),
                            "table_json_sha256": canonical_json_sha256_v1(table),
                        }
                    )
    return mismatches


def _primary_printed_outline_frontier_receipt_v1(
    section: Mapping[str, Any], table: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Whole printed dual outline only; no amount or population inference."""
    if (section.get("content_kind") != "PRIMARY_STATEMENT"
            or section.get("statement_type") != "INCOME_STATEMENT"):
        return None
    tables = section.get("tables")
    if (type(tables) is not list
            or sum(same_typed_json_v1(item, table) for item in tables) != 1):
        return None
    rows, columns = table.get("rows"), table.get("columns")
    if type(rows) is not list or len(rows) < 7 or type(columns) is not list or not columns:
        return None
    romans = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
              "XI", "XII", "XIII", "XIV", "XV")
    before_aliases = {"loi nhuan truoc thue", "tong loi nhuan truoc thue",
                      "loi nhuan ke toan truoc thue", "tong loi nhuan ke toan truoc thue"}
    after_aliases = {"loi nhuan sau thue", "tong loi nhuan sau thue",
                     "loi nhuan sau thue tndn", "tong loi nhuan sau thue tndn",
                     "loi nhuan sau thue thu nhap doanh nghiep",
                     "tong loi nhuan sau thue thu nhap doanh nghiep"}
    arabic_axis, roman_axis, source_axis, semantic_roles = [], [], [], []
    for ordinal, row in enumerate(rows, 1):
        if type(row) is not dict or row.get("row_kind") not in {"ITEM", "SUBTOTAL", "TOTAL"}:
            return None
        path, label, values = row.get("hierarchy_path_exact"), row.get("label_exact"), row.get("values_exact")
        if (type(path) is not list or len(path) != 2 or type(label) is not str or not label.strip()
                or path[-1] != label or type(path[0]) is not str
                or type(values) is not list or len(values) != len(columns)):
            return None
        token = path[0]
        if re.fullmatch(r"[1-9][0-9]*", token):
            arabic_axis.append(int(token))
            token_kind = "ARABIC"
        elif token in romans:
            roman_axis.append(romans.index(token) + 1)
            token_kind = "ROMAN"
        else:
            return None
        normalized_label = _without_leading_ordinal(_normalized(label))
        role = ("PROFIT_BEFORE_TAX" if normalized_label in before_aliases
                else "PROFIT_AFTER_TAX" if normalized_label in after_aliases
                else _role_for_primary_label(label))
        semantic_roles.append(role)
        source_axis.append({
            "row_ordinal": ordinal, "hierarchy_path_ordinal": 1,
            "source_token_exact": token, "token_kind": token_kind,
            "source_row_json_sha256": canonical_json_sha256_v1(row),
        })
    if (len(arabic_axis) < 2 or len(roman_axis) < 3
            or arabic_axis != list(range(1, len(arabic_axis) + 1))
            or roman_axis != list(range(1, len(roman_axis) + 1))):
        return None
    expected_roles = ["PROFIT_BEFORE_TAX", "CURRENT_TAX_PARENT", "DEFERRED_TAX_NET",
                      "FAMILY_ROOT_TOTAL", "PROFIT_AFTER_TAX"]
    if (semantic_roles[-5:] != expected_roles
            or any(role is not None for role in semantic_roles[:-5])):
        return None
    numeric_count, roman_count = len(arabic_axis), len(roman_axis)
    expected_tokens = [romans[roman_count - 3], str(numeric_count - 1),
                       str(numeric_count), romans[roman_count - 2], romans[roman_count - 1]]
    if [row["hierarchy_path_exact"][0] for row in rows[-5:]] != expected_tokens:
        return None
    material = {
        "rule": "WHOLE_COMPLETE_DUAL_PRINTED_OUTLINE_WITH_UNIQUE_TERMINAL_PROFIT_TAX_FRONTIER_V1",
        "section_json_sha256": canonical_json_sha256_v1(section),
        "original_table_json_sha256": canonical_json_sha256_v1(table),
        "source_columns_exact": canonical_clone_v1(columns),
        "source_rows_exact": canonical_clone_v1(rows),
        "ordered_outline_axis": source_axis,
        "arabic_outline_length": numeric_count, "roman_outline_length": roman_count,
        "permitted_frontier_tokens": [
            {**item, "semantic_role": role}
            for item, role in zip(source_axis[-5:], expected_roles, strict=True)
        ],
        "amounts_used_as_authority": False, "source_values_changed": False,
        "report_scope_permission_granted": False, "entity_permission_granted": False,
        "unit_permission_granted": False, "period_permission_granted": False,
        "source_kind_permission_granted": False,
    }
    return {**material, "receipt_id": "gjitfav1:printed-primary-outline:" + canonical_json_sha256_v1(material)}


def _primary_bridge_population_ancestry(
    table: Mapping[str, Any], *, row_ordinals: Sequence[int],
    structural_owner_surfaces: Sequence[Any] = (), structural_owner_aliases: Sequence[str] = (),
    primary_section: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Same printed ancestry only; amounts cannot establish entity population."""
    outline = (None if primary_section is None
               else _primary_printed_outline_frontier_receipt_v1(primary_section, table))
    permitted_outline_tokens = {
        (item["row_ordinal"], item["hierarchy_path_ordinal"] - 1, item["source_token_exact"])
        for item in (outline or {}).get("permitted_frontier_tokens", [])
    }
    used_outline = False
    roman_ordinals = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii", "xiii", "xiv", "xv"}
    groups = [
        {"row_ordinal": ordinal, "source_row": canonical_clone_v1(row)}
        for ordinal, row in enumerate(table["rows"], 1)
        if row.get("row_kind") == "GROUP"
        # This helper is also used by original-NOTE ancestry fallback. A new
        # PRIMARY row-label spelling must not discharge a NOTE GROUP ancestor.
        # Keep structural GROUP recognition at its pre-existing legacy scope.
        and _legacy_primary_role_for_label(row.get("label_exact")) == "FAMILY_ROOT_TOTAL"
    ]
    owner_aliases = {_without_leading_ordinal(_normalized(alias)) for alias in structural_owner_aliases}
    owner_sources = [
        {"surface_exact": surface,
         "normalized_owner": _without_leading_ordinal(_normalized(surface))}
        for surface in structural_owner_surfaces if type(surface) is str
        if _without_leading_ordinal(_normalized(surface)) in owner_aliases
    ]
    used_groups, used_owners = {}, {}
    proofs = []
    for ordinal in row_ordinals:
        row = table["rows"][ordinal - 1]
        path, label = row.get("hierarchy_path_exact"), row.get("label_exact")
        if (
            type(path) is not list or not path
            or any(type(item) is not str or not item.strip() for item in path)
            or type(label) is not str
            or _normalized(path[-1]) != _normalized(label)
        ):
            return None
        # Only the reviewed Roman row-ordinal vocabulary is stripped. Numeric
        # years/entity IDs and unknown qualifiers remain exact source evidence.
        ancestry = []
        for index, item in enumerate(path[:-1]):
            if (ordinal, index, item) in permitted_outline_tokens:
                used_outline = True
                continue
            if _normalized(item) in roman_ordinals:
                continue
            parent_groups = [group for group in groups
                             if group["row_ordinal"] < ordinal
                             and group["source_row"].get("hierarchy_path_exact") == path[:index + 1]]
            if len(parent_groups) == 1:
                group = parent_groups[0]
                used_groups[group["row_ordinal"]] = group
                continue
            owners = [source for source in owner_sources
                      if source["normalized_owner"] == _without_leading_ordinal(_normalized(item))]
            if owners:
                for owner in owners:
                    used_owners[canonical_json_sha256_v1(owner)] = owner
                continue
            ancestry.append(item)
        proofs.append({
            "row_ordinal": ordinal, "source_row": canonical_clone_v1(row),
            "population_ancestry_exact": ancestry,
            "normalized_ancestry": [_normalized(item) for item in ancestry],
        })
    if not proofs or any(
        proof["population_ancestry_exact"] != proofs[0]["population_ancestry_exact"] for proof in proofs
    ):
        return None
    material = {
        "rule": "EXACT_EQUAL_PRINTED_POPULATION_ANCESTRY_ONLY_OBSERVED_TAX_STRUCTURE_REMOVED_NO_AMOUNT_INFERENCE",
        "common_normalized_ancestry": proofs[0]["normalized_ancestry"],
        "common_population_ancestry_exact": proofs[0]["population_ancestry_exact"],
        "structural_tax_group_sources": [used_groups[key] for key in sorted(used_groups)],
        "structural_owner_sources": [used_owners[key] for key in sorted(used_owners)],
        "source_rows": proofs, "original_table_json_sha256": canonical_json_sha256_v1(table),
    }
    if used_outline:
        material["printed_primary_outline_receipt"] = outline
    return {**material, "receipt_id": "gjitfav1:bridge-population:" + canonical_json_sha256_v1(material)}


def _primary_expense_display_receipt(
    table: Mapping[str, Any], *, rows: Sequence[Mapping[str, Any]],
    money_ordinals: Sequence[int], locator: Mapping[str, Any], lane: Mapping[str, Any],
    canonical_unit: str, primary_section: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Check printed before + signed expense = after; never derive an operand."""
    before_aliases = {
        "loi nhuan truoc thue", "tong loi nhuan truoc thue",
        "loi nhuan ke toan truoc thue", "tong loi nhuan ke toan truoc thue",
    }
    # These exact printed annotations describe an observed carried row, not a
    # different profit population. Never strip arbitrary parenthetical text.
    before_aliases |= {
        _normalized(alias + suffix) for alias in before_aliases
        for suffix in (" (mang sang tu trang truoc)", " (mang tu trang truoc)")
    }
    after_aliases = {
        "loi nhuan sau thue", "tong loi nhuan sau thue",
        "loi nhuan sau thue tndn", "tong loi nhuan sau thue tndn",
        "loi nhuan sau thue thu nhap doanh nghiep",
        "tong loi nhuan sau thue thu nhap doanh nghiep",
    }
    anchors: dict[str, list[dict[str, Any]]] = {"before": [], "after": []}
    for ordinal, row in enumerate(table.get("rows") or [], 1):
        if type(row) is not dict:
            continue
        label = _without_leading_ordinal(_normalized(row.get("label_exact") or ""))
        role = "before" if label in before_aliases else "after" if label in after_aliases else None
        if role is None:
            continue
        values = row.get("values_exact")
        parsed = []
        if type(values) is list and all(index <= len(values) for index in money_ordinals):
            try:
                parsed = [_source_money(values[index - 1]) for index in money_ordinals]
            except (TypeError, ValueError):
                pass
        anchors[role].append({
            "row_ordinal": ordinal, "source_row": canonical_clone_v1(row),
            "parsed_values": parsed,
        })
    if any(len(items) != 1 for items in anchors.values()):
        return None
    by_role = {row["role"]: row for row in rows}
    expense = by_role.get("FAMILY_ROOT_TOTAL")
    if expense is None and "DEFERRED_TAX_NET" not in by_role:
        expense = by_role.get("CURRENT_TAX_PARENT")
    if expense is None or not expense["values_usable"]:
        return None
    before, after = anchors["before"][0], anchors["after"][0]
    if not before["row_ordinal"] < expense["row_ordinal"] < after["row_ordinal"]:
        return None
    population_ancestry = _primary_bridge_population_ancestry(
        table, row_ordinals=[before["row_ordinal"], *(row["row_ordinal"] for row in rows), after["row_ordinal"]],
        primary_section=primary_section,
    )
    if population_ancestry is None:
        return None
    if any(
        len(anchor["parsed_values"]) != 2
        or any(cell.get("reasons") or cell.get("coefficient") is None for cell in anchor["parsed_values"])
        for anchor in (before, after)
    ):
        return None
    expense_values = expense["parsed_values"]
    if (
        len(expense_values) != 2 or any(type(value) is not int or value > 0 for value in expense_values)
        or not any(value < 0 for value in expense_values)
    ):
        return None
    lane_receipts = []
    for ordinal, (first, cost, last) in enumerate(zip(
        before["parsed_values"], expense_values, after["parsed_values"], strict=True
    )):
        if first["coefficient"] + cost != last["coefficient"]:
            return None
        lane_receipts.append({
            "lane_ordinal": ordinal, "before": first["coefficient"],
            "signed_expense": cost, "after": last["coefficient"], "residual": 0,
        })
    material = {
        "rule": "PRINTED_BEFORE_PLUS_PRINTED_SIGNED_EXPENSE_EQUALS_PRINTED_AFTER_NO_BACKSOLVE",
        "locator": canonical_clone_v1(locator), "canonical_unit": canonical_unit,
        "original_table_json_sha256": canonical_json_sha256_v1(table),
        "money_column_ordinals": list(money_ordinals), "lane_axis": canonical_clone_v1(lane),
        "before_source_row": before, "expense_source_row": canonical_clone_v1(expense),
        "after_source_row": after, "lane_receipts": lane_receipts,
        "population_ancestry_receipt": population_ancestry,
        "source_values_changed": False, "missing_root_created": False,
    }
    return {**material, "receipt_id": "gjitfav1:expense-display:" + canonical_json_sha256_v1(material)}


def _primary_presentations(
    page_records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> list[dict[str, Any]]:
    presentations = []
    document_unit = _primary_statement_unit_corroboration(
        page_records, compiled_specs=compiled_specs
    )
    for record in page_records:
        page = record["page_json"]
        if page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            continue
        for section_ordinal, section in enumerate(page.get("sections") or [], start=1):
            if (
                type(section) is not dict
                or section.get("content_kind") != "PRIMARY_STATEMENT"
                or section.get("statement_type") != "INCOME_STATEMENT"
            ):
                continue
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                if type(table) is not dict:
                    continue
                by_role: dict[str, list[tuple[int, Mapping[str, Any]]]] = {}
                for row_ordinal, row in enumerate(table.get("rows") or [], start=1):
                    if type(row) is not dict:
                        continue
                    role = _role_for_primary_label(row.get("label_exact"))
                    if role is not None:
                        by_role.setdefault(role, []).append((row_ordinal, row))
                if not by_role or any(len(items) != 1 for items in by_role.values()):
                    continue
                lane = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
                unit = _unit_axis(table, compiled_specs=compiled_specs)
                money_ordinals = lane.get("money_column_ordinals")
                if (
                    not lane.get("complete")
                    or type(money_ordinals) is not list
                    or len(money_ordinals) != 2
                ):
                    continue
                unit_receipt = None
                if unit.get("complete") and unit.get("canonical_unit") in {
                    "MILLION_VND",
                    "VND",
                }:
                    canonical_unit = unit["canonical_unit"]
                    unit_evidence = canonical_clone_v1(unit["evidence"])
                elif (
                    document_unit is not None
                    and _local_money_unit_is_truly_absent(unit)
                ):
                    canonical_unit = document_unit["canonical_unit"]
                    unit_evidence = canonical_clone_v1(document_unit["sources"])
                    unit_receipt = canonical_clone_v1(document_unit)
                else:
                    continue
                rows = []
                for role in (
                    "FAMILY_ROOT_TOTAL",
                    "CURRENT_TAX_PARENT",
                    "DEFERRED_TAX_NET",
                ):
                    if role not in by_role:
                        continue
                    row_ordinal, row = by_role[role][0]
                    values = row.get("values_exact")
                    if type(values) is not list or any(
                        ordinal > len(values) for ordinal in money_ordinals
                    ):
                        rows = []
                        break
                    selected = [values[ordinal - 1] for ordinal in money_ordinals]
                    parsed = []
                    for value in selected:
                        try:
                            parsed.append(_source_money(value))
                        except (TypeError, ValueError):
                            parsed.append(
                                {
                                    "coefficient": None,
                                    "reasons": ["INVALID_PRIMARY_SOURCE_MONEY_CELL"],
                                }
                            )
                    rows.append(
                        {
                            "hierarchy_path_exact": canonical_clone_v1(
                                row.get("hierarchy_path_exact")
                            ),
                            "label_exact": row.get("label_exact"),
                            "parsed_values": [item.get("coefficient") for item in parsed],
                            "row_kind": row.get("row_kind"),
                            "row_ordinal": row_ordinal,
                            "role": role,
                            "source_values_exact": canonical_clone_v1(selected),
                            "values_usable": all(not item.get("reasons") for item in parsed),
                        }
                    )
                if not rows:
                    continue
                by_output_role = {item["role"]: item for item in rows}
                root = by_output_role.get("FAMILY_ROOT_TOTAL")
                current = by_output_role.get("CURRENT_TAX_PARENT")
                deferred = by_output_role.get("DEFERRED_TAX_NET")
                included = []
                if root is not None and root["values_usable"]:
                    included.append(root)
                if current is not None and current["values_usable"]:
                    included.append(current)
                if deferred is not None and deferred["values_usable"]:
                    if any(value is not None for value in deferred["parsed_values"]):
                        included.append(deferred)
                included_by_role = {item["role"]: item for item in included}
                root_values = (
                    included_by_role["FAMILY_ROOT_TOTAL"]["parsed_values"]
                    if "FAMILY_ROOT_TOTAL" in included_by_role
                    else None
                )
                current_values = (
                    included_by_role["CURRENT_TAX_PARENT"]["parsed_values"]
                    if "CURRENT_TAX_PARENT" in included_by_role
                    else None
                )
                deferred_values = (
                    included_by_role["DEFERRED_TAX_NET"]["parsed_values"]
                    if "DEFERRED_TAX_NET" in included_by_role
                    else None
                )
                if root_values is not None and current_values is not None:
                    observed_lane_mismatch = False
                    for root_value, current_value, deferred_value in zip(
                        root_values,
                        current_values,
                        deferred_values or [0] * len(root_values),
                        strict=True,
                    ):
                        if root_value is None or current_value is None or deferred_value is None:
                            continue
                        if current_value + deferred_value != root_value:
                            observed_lane_mismatch = True
                            break
                    if observed_lane_mismatch:
                        continue
                if not included:
                    continue
                role_axis = [item["role"] for item in included]
                if "FAMILY_ROOT_TOTAL" in role_axis and "DEFERRED_TAX_NET" in role_axis:
                    specs_key = "income_tax_primary_both_specs"
                elif "FAMILY_ROOT_TOTAL" in role_axis and "CURRENT_TAX_PARENT" in role_axis:
                    specs_key = "income_tax_primary_current_specs"
                elif "FAMILY_ROOT_TOTAL" in role_axis:
                    specs_key = "income_tax_primary_current_specs"
                else:
                    specs_key = "income_tax_primary_detail_specs"
                columns = table.get("columns")
                if type(columns) is not list:
                    continue
                descriptor = {
                    "canonical_unit": canonical_unit,
                    "locator": _record_locator(
                        record,
                        section_id=f"s{section_ordinal}",
                        table_id=f"t{table_ordinal}",
                    ),
                    "money_column_ordinals": canonical_clone_v1(money_ordinals),
                    "original_page_json_sha256": canonical_json_sha256_v1(page),
                    "original_table_json_sha256": canonical_json_sha256_v1(table),
                    "primary_unit_corroboration_receipt": unit_receipt,
                    "projected_unit_exact": (
                        "Triệu VND" if canonical_unit == "MILLION_VND" else "VND"
                    ),
                    "projected_specs_key": specs_key,
                    "rows": canonical_clone_v1(included),
                    "source_role_rows": canonical_clone_v1(rows),
                    "unit_evidence": unit_evidence,
                }
                descriptor["expense_display_receipt"] = _primary_expense_display_receipt(
                    table, rows=rows, money_ordinals=money_ordinals,
                    locator=descriptor["locator"], lane=lane, canonical_unit=canonical_unit,
                    primary_section=section,
                )
                projected_page = _project_primary_page(page, descriptor=descriptor)
                descriptor["projected_page_json_sha256"] = canonical_json_sha256_v1(projected_page)
                presentations.append(descriptor)
    return presentations


def _supplemental_owner_matches(
    section: Mapping[str, Any],
    table: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
) -> bool:
    surface = _normalized(
        " | ".join(
            value
            for value in (section.get("title_exact"), table.get("title_exact"))
            if type(value) is str and value.strip()
        )
    )
    aliases = compiled_specs.get("query_policy", {}).get("owner_aliases", [])
    negative_aliases = {
        *compiled_specs.get("query_policy", {}).get("hard_negative_aliases", []),
        *compiled_specs.get("query_policy", {}).get("reset_aliases", []),
    }
    if any(alias in surface for alias in negative_aliases):
        return False
    return bool(surface and any(alias in surface for alias in aliases))


def _supplemental_role_alias_axis(
    compiled_specs: Mapping[str, Any],
) -> dict[str, str]:
    axis: dict[str, str] = {}
    for child in compiled_specs["topology"]["children"]:
        role = child["role"]
        if role not in _SUPPLEMENTAL_DIRECT_ROLES:
            continue
        for matcher in child["matchers"]:
            for alias in matcher["aliases"]:
                if alias in axis and axis[alias] != role:
                    raise _error("income-tax supplemental role alias is ambiguous")
                axis[alias] = role
    return axis


def _supplemental_negative_surface(
    item: Mapping[str, Any], negative_aliases: Sequence[str]
) -> bool:
    """Fence source labels and ancestors independently of the proposed row kind."""

    path = item.get("hierarchy_path_exact")
    surfaces = [item.get("normalized_label", item.get("label_exact"))]
    if type(path) is list:
        surfaces.extend(path)
    return any(
        _normalized(alias) in _normalized(surface)
        for surface in surfaces
        if _normalized(surface)
        for alias in negative_aliases
        if _normalized(alias)
    )


def _supplemental_candidate_surface(item: Mapping[str, Any]) -> bool:
    label = item["normalized_label"]
    return bool(
        item["matched_role"] in _SUPPLEMENTAL_DIRECT_ROLES
        or ("ngan hang" in label and "cong ty" not in label and "thue" not in label)
        or (
            "cong ty" in label
            and any(alias in label for alias in ("quan ly no", "khai thac tai san", "amc"))
        )
        or label in {"ky hien hanh", "nam hien hanh"}
    )


def _supplemental_rate_parent_matches(
    item: Mapping[str, Any], *, compiled_specs: Mapping[str, Any]
) -> bool:
    """Arithmetic cannot relabel another declared semantic subtotal as current tax."""

    label = item["normalized_label"]
    aliases_by_role = {
        child["role"]: [alias for matcher in child["matchers"] for alias in matcher["aliases"]]
        for child in compiled_specs["topology"]["children"]
    }
    label_roles = {
        role
        for role, aliases in aliases_by_role.items()
        if label in {_without_leading_ordinal(_normalized(alias)) for alias in aliases}
    }
    path_roles = {
        role
        for role, aliases in aliases_by_role.items()
        if _path_has_role(
            item.get("hierarchy_path_exact"), aliases=aliases, label_exact=item.get("label_exact")
        )
    }
    if label_roles - {"CURRENT_TAX_PARENT"} or path_roles - {"CURRENT_TAX_PARENT"}:
        return False
    if label in _ROOT_LABELS:
        return False
    return bool(
        label_roles == {"CURRENT_TAX_PARENT"}
        or (
            label in {"", "cong", "tong cong"}
            and path_roles == {"CURRENT_TAX_PARENT"}
        )
    )


def _supplemental_source_rows(
    table: Mapping[str, Any],
    *,
    money_column_ordinals: Sequence[int],
    role_alias_axis: Mapping[str, str],
) -> list[dict[str, Any]]:
    output = []
    for row_ordinal, row in enumerate(table.get("rows") or [], start=1):
        if type(row) is not dict:
            raise _error("income-tax supplemental source row is invalid")
        values = row.get("values_exact")
        if type(values) is not list:
            raise _error("income-tax supplemental source values are invalid")
        selected = [
            values[ordinal - 1] if ordinal <= len(values) else None
            for ordinal in money_column_ordinals
        ]
        parsed = []
        for value in selected:
            try:
                parsed.append(_source_money(value))
            except (TypeError, ValueError):
                parsed.append(
                    {
                        "coefficient": None,
                        "reasons": ["INVALID_SUPPLEMENTAL_SOURCE_MONEY_CELL"],
                    }
                )
        normalized_label = _without_leading_ordinal(_normalized(row.get("label_exact")))
        output.append(
            {
                "hierarchy_path_exact": canonical_clone_v1(row.get("hierarchy_path_exact")),
                "label_exact": row.get("label_exact"),
                "matched_role": role_alias_axis.get(normalized_label),
                "normalized_label": normalized_label,
                "parsed_values": [item.get("coefficient") for item in parsed],
                "row_kind": row.get("row_kind"),
                "row_ordinal": row_ordinal,
                "source_values_exact": canonical_clone_v1(selected),
                "values_usable": all(not item.get("reasons") for item in parsed),
            }
        )
    return output


def _all_observed(values: Sequence[int | None]) -> bool:
    return bool(values and all(value is not None for value in values))


def _deferred_net_source_frontier(source_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    """One explicitly named net child, not a blank group or inferred residual."""
    group_labels = {_normalized(label) for label in (
        "Chi phí thuế TNDN hoãn lại", "Chi phí thuế thu nhập doanh nghiệp hoãn lại",
    )}
    net_label = _normalized("Phát sinh và hoàn nhập các chênh lệch tạm thời")
    groups = [item for item in source_rows if item["normalized_label"] in group_labels and item["row_kind"] == "GROUP"]
    children = [item for item in source_rows if item["normalized_label"] == net_label]
    if len(groups) != 1 or len(children) != 1:
        return None
    group, child = groups[0], children[0]
    ordinal = group["row_ordinal"]
    if ordinal + 2 > len(source_rows):
        return None
    root = source_rows[ordinal + 1]
    if (group["hierarchy_path_exact"] != [group["label_exact"]]
            or any(value is not None for value in group["source_values_exact"])
            or child["row_ordinal"] != ordinal + 1 or child["row_kind"] != "ITEM"
            or child["hierarchy_path_exact"] != [group["label_exact"], child["label_exact"]]
            or root["row_kind"] != "TOTAL" or root["normalized_label"] not in _ROOT_LABELS
            or root["hierarchy_path_exact"] != [root["label_exact"]]
            or not all(item["values_usable"] and _all_observed(item["parsed_values"]) for item in (child, root))):
        return None
    material = {"group_source_row": canonical_clone_v1(group), "net_source_row": canonical_clone_v1(child),
                "closing_root_source_row": canonical_clone_v1(root),
                "rule": "SOLE_PRINTED_DEFERRED_NET_CHANGE_CHILD_UNDER_EXACT_BLANK_EXPENSE_GROUP_NO_VALUE_INFERENCE"}
    return {**material, "receipt_id": "gjitfav1:deferred-net-frontier:" + canonical_json_sha256_v1(material)}


def _exact_sum(
    components: Sequence[Mapping[str, Any]], parent: Mapping[str, Any]
) -> bool:
    component_values = [item["parsed_values"] for item in components]
    parent_values = parent["parsed_values"]
    if (
        not components
        or not _all_observed(parent_values)
        or any(not _all_observed(values) for values in component_values)
    ):
        return False
    return all(
        sum(values[lane] for values in component_values) == parent_values[lane]
        for lane in range(len(parent_values))
    )


def _projected_source_row(
    item: Mapping[str, Any], *, role: str, projected_row_kind: str
) -> dict[str, Any]:
    return {
        key: canonical_clone_v1(item[key])
        for key in (
            "hierarchy_path_exact",
            "label_exact",
            "parsed_values",
            "row_kind",
            "row_ordinal",
            "source_values_exact",
            "values_usable",
        )
    } | {"projected_row_kind": projected_row_kind, "role": role}


def _supplemental_equation_receipt(
    *,
    component_rows: Sequence[Mapping[str, Any]],
    parent_row: Mapping[str, Any],
    equation_kind: str,
) -> dict[str, Any]:
    material = {
        "component_rows": [
            {
                "parsed_values": canonical_clone_v1(item["parsed_values"]),
                "role": item["role"],
                "row_ordinal": item["row_ordinal"],
            }
            for item in component_rows
        ],
        "equation_kind": equation_kind,
        "parent_row": {
            "parsed_values": canonical_clone_v1(parent_row["parsed_values"]),
            "role": parent_row["role"],
            "row_ordinal": parent_row["row_ordinal"],
        },
        "status": "EXACT_ALL_OBSERVED_LANES",
    }
    return {
        **material,
        "equation_id": "gjitfav1:supplemental-equation:"
        + canonical_json_sha256_v1(material),
    }


def _finalize_supplemental_descriptor(
    *,
    record: Mapping[str, Any],
    page: Mapping[str, Any],
    section_ordinal: int,
    table_ordinal: int,
    table: Mapping[str, Any],
    money_column_ordinals: Sequence[int],
    canonical_unit: str,
    unit_evidence: Any,
    unit_receipt: Mapping[str, Any] | None,
    source_rows: Sequence[Mapping[str, Any]],
    rows: Sequence[Mapping[str, Any]],
    presentation_kind: str,
    equation_receipts: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    source_population_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    descriptor = {
        "canonical_unit": canonical_unit,
        "equation_receipts": canonical_clone_v1(list(equation_receipts)),
        "locator": _record_locator(
            record,
            section_id=f"s{section_ordinal}",
            table_id=f"t{table_ordinal}",
        ),
        "money_column_ordinals": canonical_clone_v1(list(money_column_ordinals)),
        "original_page_json_sha256": canonical_json_sha256_v1(page),
        "original_table_json_sha256": canonical_json_sha256_v1(table),
        "presentation_kind": presentation_kind,
        "primary_unit_corroboration_receipt": canonical_clone_v1(unit_receipt),
        "projected_specs_key": "income_tax_supplemental_specs",
        "projected_unit_exact": "Triệu VND" if canonical_unit == "MILLION_VND" else "VND",
        "rows": canonical_clone_v1(list(rows)),
        "source_table_row_axis": canonical_clone_v1(list(source_rows)),
        "source_population_receipt": canonical_clone_v1(source_population_receipt),
        "projected_semantic_spec_sha256": _semantic_spec_sha256(compiled_specs["income_tax_supplemental_specs"]),
        "unit_evidence": canonical_clone_v1(unit_evidence),
    }
    projected_page = _project_primary_page(page, descriptor=descriptor)
    descriptor["projected_page_json_sha256"] = canonical_json_sha256_v1(projected_page)
    projected_record = {
        key: canonical_clone_v1(descriptor["locator"][key])
        for key in (
            "document_id",
            "document_ordinal",
            "page_json_version_id",
            "physical_page",
            "selected_page_ordinal",
            "source_logical_name",
            "source_sha256",
        )
    } | {"page_json": projected_page}
    specs = compiled_specs["income_tax_supplemental_specs"]
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[projected_record], compiled_specs=specs
    )
    if cluster.get("status") != READY:
        return None
    regions = cluster["component_regions"]
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=regions,
        page_json_by_version={descriptor["locator"]["page_json_version_id"]: projected_page},
        compiled_specs=specs,
        query_receipt=(
            build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
        ),
    )
    if candidate.get("status") != READY:
        return None
    descriptor["projected_component_regions"] = canonical_clone_v1(regions)
    material = canonical_clone_v1(descriptor)
    descriptor["descriptor_id"] = (
        "gjitfav1:supplemental:" + canonical_json_sha256_v1(material)
    )
    return descriptor


def _supplemental_root_controls(
    page_records: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
    issues: list[str],
) -> list[dict[str, Any]]:
    """Bind exact supplemental roots as source controls, never as mappings."""

    controls: list[dict[str, Any]] = []
    root_surface_count = 0
    role_alias_axis = _supplemental_role_alias_axis(compiled_specs)
    document_unit = _primary_statement_unit_corroboration(
        page_records, compiled_specs=compiled_specs
    )
    negative_aliases = {
        *compiled_specs.get("query_policy", {}).get("hard_negative_aliases", []),
        *compiled_specs.get("query_policy", {}).get("reset_aliases", []),
    }
    for record in page_records:
        page = record["page_json"]
        for section_ordinal, section in enumerate(page.get("sections") or [], start=1):
            if type(section) is not dict or section.get("content_kind") != "FINANCIAL_NOTE":
                continue
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                if type(table) is not dict or not _supplemental_owner_matches(
                    section, table, compiled_specs=compiled_specs
                ):
                    continue
                root_ordinals = [
                    ordinal
                    for ordinal, row in enumerate(table.get("rows") or [], start=1)
                    if type(row) is dict
                    and _without_leading_ordinal(_normalized(row.get("label_exact")))
                    in _ROOT_LABELS
                ]
                if not root_ordinals:
                    continue
                root_surface_count += len(root_ordinals)
                recognition = _recognition_expense_source_frontier(section, table, compiled_specs=compiled_specs)
                if recognition["status"] == "ALGORITHM_HOLD":
                    issues.append("SUPPLEMENTAL_RECOGNITION_SOURCE_FRONTIER_INCOMPLETE")
                    continue
                lane_axis = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
                money_ordinals = lane_axis.get("money_column_ordinals")
                if (
                    not lane_axis.get("complete")
                    or type(money_ordinals) is not list
                    or len(money_ordinals) != 2
                ):
                    issues.append("SUPPLEMENTAL_ROOT_LANE_AXIS_NOT_COMPLETE")
                    continue
                unit_axis = _unit_axis(table, compiled_specs=compiled_specs)
                unit_receipt = None
                if unit_axis.get("complete") and unit_axis.get("canonical_unit") in {
                    "MILLION_VND", "VND"
                }:
                    canonical_unit = unit_axis["canonical_unit"]
                    unit_evidence = canonical_clone_v1(unit_axis["evidence"])
                elif document_unit is not None and _local_money_unit_is_truly_absent(unit_axis):
                    canonical_unit = document_unit["canonical_unit"]
                    unit_evidence = canonical_clone_v1(document_unit["sources"])
                    unit_receipt = canonical_clone_v1(document_unit)
                else:
                    issues.append("SUPPLEMENTAL_ROOT_UNIT_AXIS_NOT_COMPLETE")
                    continue
                source_rows = _supplemental_source_rows(
                    table,
                    money_column_ordinals=money_ordinals,
                    role_alias_axis=role_alias_axis,
                )
                resets = [
                    item["row_ordinal"] for item in source_rows
                    if _supplemental_negative_surface(item, negative_aliases)
                ]
                locator = _record_locator(
                    record, section_id=f"s{section_ordinal}", table_id=f"t{table_ordinal}"
                )
                for row_ordinal in root_ordinals:
                    item = source_rows[row_ordinal - 1]
                    if resets and row_ordinal >= min(resets):
                        issues.append("SUPPLEMENTAL_ROOT_AFTER_STRUCTURAL_RESET")
                    if not item["values_usable"] or not _all_observed(item["parsed_values"]):
                        issues.append("SUPPLEMENTAL_ROOT_FRONTIER_NOT_COMPLETE")
                    source_ref = {
                        "hierarchy_path_exact": canonical_clone_v1(item["hierarchy_path_exact"]),
                        "label_exact": item["label_exact"],
                        "locator": canonical_clone_v1(locator),
                        "money_column_ordinals": canonical_clone_v1(money_ordinals),
                        "row_id": f"r{row_ordinal}",
                        "row_kind": item["row_kind"],
                        "row_ordinal": row_ordinal,
                    }
                    root_row = canonical_clone_v1(item)
                    root_row.update({
                        "coefficients": canonical_clone_v1(item["parsed_values"]),
                        "role": "FAMILY_ROOT_TOTAL",
                        "source_ref": source_ref,
                        "values_exact": canonical_clone_v1(item["source_values_exact"]),
                    })
                    material = {
                        "canonical_unit": canonical_unit,
                        "lane_axis": canonical_clone_v1(lane_axis),
                        "locator": canonical_clone_v1(locator),
                        "money_column_ordinals": canonical_clone_v1(money_ordinals),
                        "original_page_json_sha256": canonical_json_sha256_v1(page),
                        "original_table_json_sha256": canonical_json_sha256_v1(table),
                        "primary_unit_corroboration_receipt": unit_receipt,
                        "root_source_row": root_row,
                        "source_table_row_axis": canonical_clone_v1(source_rows),
                        "recognition_expense_frontier_receipt": (recognition if recognition["status"] == "PASS" else None),
                        "unit_evidence": canonical_clone_v1(unit_evidence),
                        "rule": "EXACT_SOURCE_VISIBLE_SUPPLEMENTAL_ROOT_IS_CONTROL_ONLY",
                    }
                    controls.append({
                        **material,
                        "control_id": "gjitfav1:supplemental-root-control:"
                        + canonical_json_sha256_v1(material),
                    })
    if root_surface_count > 1:
        issues.append("SUPPLEMENTAL_ROOT_AXIS_NOT_UNIQUE")
    issues[:] = sorted(set(issues))
    return sorted(controls, key=lambda item: (
        item["locator"]["selected_page_ordinal"],
        item["locator"]["section_id"],
        item["locator"]["table_id"],
        item["root_source_row"]["row_ordinal"],
    ))


def _supplemental_presentations(
    page_records: Sequence[Mapping[str, Any]],
    *,
    compiled_specs: Mapping[str, Any],
    issues: list[str] | None = None,
    consumed_source_rows: frozenset[tuple[str, str, str, int]] = frozenset(),
    authenticated_rate_table_axis: frozenset[tuple[str, str, str]] = frozenset(),
) -> list[dict[str, Any]]:
    role_alias_axis = _supplemental_role_alias_axis(compiled_specs)
    document_unit = _primary_statement_unit_corroboration(
        page_records, compiled_specs=compiled_specs
    )
    descriptors = []
    for record in page_records:
        page = record["page_json"]
        for section_ordinal, section in enumerate(page.get("sections") or [], start=1):
            if type(section) is not dict or section.get("content_kind") != "FINANCIAL_NOTE":
                continue
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                if type(table) is not dict or not _supplemental_owner_matches(
                    section, table, compiled_specs=compiled_specs
                ):
                    continue
                lane = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
                money_ordinals = lane.get("money_column_ordinals")
                if (
                    not lane.get("complete")
                    or type(money_ordinals) is not list
                    or len(money_ordinals) != 2
                ):
                    continue
                unit = _unit_axis(table, compiled_specs=compiled_specs)
                unit_receipt = None
                if unit.get("complete") and unit.get("canonical_unit") in {
                    "MILLION_VND",
                    "VND",
                }:
                    canonical_unit = unit["canonical_unit"]
                    unit_evidence = canonical_clone_v1(unit["evidence"])
                elif (
                    document_unit is not None
                    and _local_money_unit_is_truly_absent(unit)
                ):
                    canonical_unit = document_unit["canonical_unit"]
                    unit_evidence = canonical_clone_v1(document_unit["sources"])
                    unit_receipt = canonical_clone_v1(document_unit)
                else:
                    continue
                all_source_rows = _supplemental_source_rows(
                    table,
                    money_column_ordinals=money_ordinals,
                    role_alias_axis=role_alias_axis,
                )
                negative_aliases = {
                    *compiled_specs.get("query_policy", {}).get(
                        "hard_negative_aliases", []
                    ),
                    *compiled_specs.get("query_policy", {}).get("reset_aliases", []),
                }
                reset_ordinals = [
                    item["row_ordinal"]
                    for item in all_source_rows
                    if _supplemental_negative_surface(item, negative_aliases)
                ]
                if reset_ordinals:
                    first_reset = min(reset_ordinals)
                    if any(
                        item["row_ordinal"] >= first_reset
                        and _supplemental_candidate_surface(item)
                        for item in all_source_rows
                    ):
                        if issues is not None:
                            issues.append("SUPPLEMENTAL_ROLE_AFTER_STRUCTURAL_RESET")
                        continue
                    source_rows = [
                        item
                        for item in all_source_rows
                        if item["row_ordinal"] < first_reset
                    ]
                else:
                    source_rows = all_source_rows
                recognition = _recognition_expense_source_frontier(section, table, compiled_specs=compiled_specs)
                if recognition["status"] == "ALGORITHM_HOLD":
                    if issues is not None:
                        issues.append("SUPPLEMENTAL_RECOGNITION_SOURCE_FRONTIER_INCOMPLETE")
                    continue
                recognition_rate = _recognition_rate_effect_forward_control(section, table, compiled_specs=compiled_specs)
                ancestry_rate = (recognition_rate["status"] == "PASS" and (
                    recognition.get("owner_representation") == "REPEATED_EXACT_IMMEDIATE_ANCESTOR_NOT_A_ROW"
                    or recognition_rate.get("adjustment_owner_receipt") is not None))
                if recognition_rate["status"] == "ALGORITHM_HOLD" and recognition.get("owner_representation"):
                    if issues is not None:
                        issues.append("SUPPLEMENTAL_RECOGNITION_RATE_SOURCE_FRONTIER_INCOMPLETE")
                    continue
                # A generic note may already have claimed the row.  That is
                # never authority to bypass a contradictory source boundary.
                if consumed_source_rows and not any(
                    _supplemental_candidate_surface(item)
                    and (
                        record["page_json_version_id"],
                        f"s{section_ordinal}",
                        f"t{table_ordinal}",
                        item["row_ordinal"],
                    )
                    not in consumed_source_rows
                    for item in all_source_rows
                ):
                    continue
                claimed: set[int] = set()
                table_has_certified_equation = False
                table_equation_receipts: list[dict[str, Any]] = []
                certified_adjustment_ordinals: set[int] = set()

                if recognition["status"] == "PASS":
                    current = _projected_source_row(recognition["current_source_row"],
                                                    role="CURRENT_TAX_PARENT", projected_row_kind="ITEM")
                    deferred = _projected_source_row(recognition["deferred_source_row"],
                                                     role="DEFERRED_TAX_NET", projected_row_kind="ITEM")
                    root = _projected_source_row(recognition["parent_source_row"],
                                                 role="FAMILY_ROOT_TOTAL", projected_row_kind="TOTAL")
                    equation = _supplemental_equation_receipt(
                        component_rows=[current, deferred], parent_row=root,
                        equation_kind="OBSERVED_CURRENT_PLUS_OBSERVED_ZERO_DEFERRED_INCOME_EQUALS_PRINTED_ROOT_CONTROL_ONLY",
                    )
                    descriptor = _finalize_supplemental_descriptor(
                        record=record, page=page, section_ordinal=section_ordinal, table_ordinal=table_ordinal,
                        table=table, money_column_ordinals=money_ordinals, canonical_unit=canonical_unit,
                        unit_evidence=unit_evidence, unit_receipt=unit_receipt, source_rows=all_source_rows,
                        rows=[current, deferred], presentation_kind="RECOGNITION_GROUP_OBSERVED_CURRENT_AND_ZERO_DEFERRED",
                        equation_receipts=[equation], compiled_specs=compiled_specs, source_population_receipt=recognition,
                    )
                    if descriptor is None:
                        if issues is not None:
                            issues.append("SUPPLEMENTAL_RECOGNITION_PRIVATE_PROJECTION_INCOMPLETE")
                    else:
                        descriptors.append(descriptor)
                        claimed.update(item["row_ordinal"] for item in (recognition["group_source_row"], current, deferred)
                                       if item is not None)
                    if ancestry_rate:
                        profit = recognition_rate["profit_source_row"]
                        descriptor = _finalize_supplemental_descriptor(
                            record=record, page=page, section_ordinal=section_ordinal, table_ordinal=table_ordinal,
                            table=table, money_column_ordinals=money_ordinals, canonical_unit=canonical_unit,
                            unit_evidence=unit_evidence, unit_receipt=unit_receipt, source_rows=all_source_rows,
                            rows=[_projected_source_row(profit, role="PROFIT_BEFORE_TAX", projected_row_kind="ITEM")],
                            presentation_kind="ANCESTRY_RECOGNITION_RATE_OBSERVED_PROFIT_NOT_TAX_EFFECT_INCOME",
                            equation_receipts=[], compiled_specs=compiled_specs, source_population_receipt=recognition_rate,
                        )
                        if descriptor is None:
                            if issues is not None:
                                issues.append("SUPPLEMENTAL_RECOGNITION_RATE_PRIVATE_PROJECTION_INCOMPLETE")
                        else:
                            descriptors.append(descriptor)
                            claimed.update(item["row_ordinal"] for item in all_source_rows
                                           if item["row_ordinal"] < recognition["current_source_row"]["row_ordinal"])

                deferred_frontier = _deferred_net_source_frontier(source_rows)
                if deferred_frontier is not None:
                    net_row = deferred_frontier["net_source_row"]
                    descriptor = _finalize_supplemental_descriptor(
                        record=record, page=page, section_ordinal=section_ordinal, table_ordinal=table_ordinal,
                        table=table, money_column_ordinals=money_ordinals, canonical_unit=canonical_unit,
                        unit_evidence=unit_evidence, unit_receipt=unit_receipt, source_rows=all_source_rows,
                        rows=[_projected_source_row(net_row, role="DEFERRED_TAX_NET", projected_row_kind="ITEM")],
                        presentation_kind="DEFERRED_TAX_SINGLE_NET_SOURCE_CHILD", equation_receipts=[],
                        compiled_specs=compiled_specs, source_population_receipt=deferred_frontier,
                    )
                    if descriptor is not None:
                        descriptors.append(descriptor)
                        claimed.update((deferred_frontier["group_source_row"]["row_ordinal"], net_row["row_ordinal"]))

                year_frontier = _current_year_source_frontier(
                    source_rows, compiled_specs=compiled_specs,
                )
                if year_frontier is not None:
                    components = [
                        _projected_source_row(
                            item, role=(year_frontier["source_component_role"] if index == 0
                                        else "PRIOR_PERIOD_TAX_ADJUSTMENT"),
                            projected_row_kind="ITEM",
                        ) for index, item in enumerate(year_frontier["component_source_rows"])
                    ]
                    parent = _projected_source_row(
                        year_frontier["parent_source_row"], role="CURRENT_TAX_PARENT",
                        projected_row_kind="TOTAL",
                    )
                    group = _projected_source_row(
                        year_frontier["group_source_row"], role="CURRENT_YEAR_EXPENSE_CONTEXT",
                        projected_row_kind="GROUP",
                    )
                    if (not _exact_sum(components, parent)
                            or not all(type(value) is str and re.search(r"[0-9]", value)
                                       for item in [*components, parent] for value in item["source_values_exact"])):
                        if issues is not None:
                            issues.append("SUPPLEMENTAL_CURRENT_YEAR_EQUATION_NOT_COMPLETE_OR_EXACT")
                    else:
                        equation = _supplemental_equation_receipt(
                            component_rows=components, parent_row=parent,
                            equation_kind=("CURRENT_PERIOD_PLUS_PRINTED_PRIOR_ADJUSTMENTS_EQUALS_CURRENT_TAX"
                                           if year_frontier["source_component_role"] == "CURRENT_PERIOD_TAX_EXPENSE_SOURCE_ONLY"
                                           else "CURRENT_YEAR_PLUS_PRINTED_PRIOR_ADJUSTMENTS_EQUALS_CURRENT_TAX"),
                        )
                        descriptor = _finalize_supplemental_descriptor(
                            record=record, page=page, section_ordinal=section_ordinal,
                            table_ordinal=table_ordinal, table=table,
                            money_column_ordinals=money_ordinals, canonical_unit=canonical_unit,
                            unit_evidence=unit_evidence, unit_receipt=unit_receipt,
                            source_rows=all_source_rows, rows=[group, *components, parent],
                            presentation_kind=("CURRENT_PERIOD_TAX_EXPENSE_EXACT_SUM"
                                               if year_frontier["source_component_role"] == "CURRENT_PERIOD_TAX_EXPENSE_SOURCE_ONLY"
                                               else "CURRENT_YEAR_TAX_EXPENSE_EXACT_SUM"),
                            equation_receipts=[equation], compiled_specs=compiled_specs,
                            source_population_receipt=year_frontier,
                        )
                        if descriptor is None:
                            if issues is not None:
                                issues.append("SUPPLEMENTAL_CURRENT_YEAR_PRIVATE_PROJECTION_NOT_READY")
                        else:
                            descriptors.append(descriptor)
                            claimed.update(item["row_ordinal"] for item in [group, *components, parent])
                            table_has_certified_equation = True
                            table_equation_receipts.append(equation)

                bank_surface_rows = [
                    item
                    for item in source_rows
                    if (
                        item["matched_role"] == "CURRENT_TAX_BANK"
                        or (
                            "ngan hang" in item["normalized_label"]
                            and "cong ty" not in item["normalized_label"]
                            and "thue" not in item["normalized_label"]
                        )
                    )
                    and item["row_kind"] not in {"SUBTOTAL", "TOTAL"}
                ]
                subsidiary_surface_rows = [
                    item
                    for item in source_rows
                    if (
                        item["matched_role"] == "SUBSIDIARY_TAX"
                        or (
                            "cong ty" in item["normalized_label"]
                            and "thue" not in item["normalized_label"]
                            and (
                                "quan ly no" in item["normalized_label"]
                                or "khai thac tai san" in item["normalized_label"]
                                or "amc" in item["normalized_label"]
                            )
                        )
                    )
                ]
                bank_rows = [
                    item
                    for item in bank_surface_rows
                    if item["values_usable"] and _all_observed(item["parsed_values"])
                ]
                subsidiary_rows = [
                    item
                    for item in subsidiary_surface_rows
                    if item["values_usable"] and _all_observed(item["parsed_values"])
                ]
                entity_parents = [
                    item
                    for item in source_rows
                    if item["row_kind"] in {"SUBTOTAL", "TOTAL"}
                    and (
                        item["normalized_label"] in {"cong", "tong cong"}
                        or item["matched_role"] == "CURRENT_TAX_PARENT"
                    )
                ]
                entity_shape_present = bool(bank_surface_rows and subsidiary_surface_rows)
                if entity_shape_present and not (
                    len(bank_surface_rows)
                    == len(subsidiary_surface_rows)
                    == len(bank_rows)
                    == len(subsidiary_rows)
                    == len(entity_parents)
                    == 1
                ):
                    if issues is not None:
                        issues.append("SUPPLEMENTAL_CURRENT_TAX_ENTITY_AXIS_NOT_UNIQUE")
                elif len(bank_rows) == len(subsidiary_rows) == len(entity_parents) == 1:
                    component_ordinals = {
                        bank_rows[0]["row_ordinal"],
                        subsidiary_rows[0]["row_ordinal"],
                    }
                    parent_ordinal = entity_parents[0]["row_ordinal"]
                    entity_frontier = [
                        item
                        for item in source_rows
                        if min(component_ordinals) <= item["row_ordinal"] < parent_ordinal
                    ]
                    if (
                        not all(ordinal < parent_ordinal for ordinal in component_ordinals)
                        or {item["row_ordinal"] for item in entity_frontier}
                        != component_ordinals
                    ):
                        if issues is not None:
                            issues.append(
                                "SUPPLEMENTAL_CURRENT_TAX_ENTITY_FRONTIER_NOT_COMPLETE"
                            )
                        continue
                    entity_rows = [
                        _projected_source_row(
                            bank_rows[0], role="CURRENT_TAX_BANK", projected_row_kind="ITEM"
                        ),
                        _projected_source_row(
                            subsidiary_rows[0],
                            role="SUBSIDIARY_TAX",
                            projected_row_kind="ITEM",
                        ),
                        _projected_source_row(
                            entity_parents[0],
                            role="CURRENT_TAX_PARENT",
                            projected_row_kind="TOTAL",
                        ),
                    ]
                    if _exact_sum(entity_rows[:2], entity_rows[2]):
                        equation = _supplemental_equation_receipt(
                            component_rows=entity_rows[:2],
                            parent_row=entity_rows[2],
                            equation_kind="BANK_PLUS_ASSET_MANAGEMENT_SUBSIDIARY_EQUALS_CURRENT_TAX",
                        )
                        table_equation_receipts.append(equation)
                        descriptor = _finalize_supplemental_descriptor(
                            record=record,
                            page=page,
                            section_ordinal=section_ordinal,
                            table_ordinal=table_ordinal,
                            table=table,
                            money_column_ordinals=money_ordinals,
                            canonical_unit=canonical_unit,
                            unit_evidence=unit_evidence,
                            unit_receipt=unit_receipt,
                            source_rows=all_source_rows,
                            rows=entity_rows,
                            presentation_kind="CURRENT_TAX_ENTITY_SPLIT_EXACT_SUM",
                            equation_receipts=[equation],
                            compiled_specs=compiled_specs,
                        )
                        if descriptor is not None:
                            descriptors.append(descriptor)
                            claimed.update(item["row_ordinal"] for item in entity_rows)
                            table_has_certified_equation = True
                    elif issues is not None:
                        issues.append("SUPPLEMENTAL_CURRENT_TAX_ENTITY_EQUATION_MISMATCH")

                rate_rows = [
                    item
                    for item in source_rows
                    if item["matched_role"] in {"CURRENT_TAX_AT_RATE", "STATUTORY_TAX_AMOUNT_SOURCE_ONLY"}
                ]
                rate_handled = ancestry_rate or (
                    record["page_json_version_id"], f"s{section_ordinal}", f"t{table_ordinal}") in authenticated_rate_table_axis
                if not rate_handled and len(rate_rows) > 1 and issues is not None:
                    issues.append("SUPPLEMENTAL_CURRENT_TAX_RATE_AXIS_NOT_UNIQUE")
                if not rate_handled and len(rate_rows) == 1:
                    parent_options = [
                        item
                        for item in source_rows
                        if item["row_ordinal"] > rate_rows[0]["row_ordinal"]
                        and item["row_kind"] in {"SUBTOTAL", "TOTAL"}
                    ]
                    if parent_options:
                        parent = parent_options[0]
                        if not _supplemental_rate_parent_matches(
                            parent, compiled_specs=compiled_specs
                        ):
                            if issues is not None:
                                issues.append("SUPPLEMENTAL_CURRENT_TAX_PARENT_SEMANTIC_CONFLICT")
                            continue
                        component_items = [
                            item
                            for item in source_rows
                            if rate_rows[0]["row_ordinal"] <= item["row_ordinal"]
                            < parent["row_ordinal"]
                        ]
                        frontier_complete = bool(
                            component_items
                            and component_items[0] is rate_rows[0]
                            and all(
                                item["row_kind"] not in {"GROUP", "SUBTOTAL", "TOTAL"}
                                for item in component_items
                            )
                            and parent["values_usable"]
                            and _all_observed(parent["parsed_values"])
                            and all(
                                item["values_usable"]
                                and _all_observed(item["parsed_values"])
                                for item in component_items
                            )
                        )
                        equation_components = [
                            _projected_source_row(
                                item,
                                role=(
                                    item["matched_role"]
                                    if item is rate_rows[0]
                                    else (
                                        item["matched_role"]
                                        if item["matched_role"]
                                        in _SUPPLEMENTAL_DIRECT_ROLES
                                        and item["matched_role"] not in {
                                            "NON_DEDUCTIBLE_EXPENSE",
                                            "CURRENT_YEAR_TAX_EXPENSE",
                                            "CURRENT_PERIOD_TAX_EXPENSE_SOURCE_ONLY",
                                        }
                                        else "SOURCE_ONLY_EQUATION_COMPONENT"
                                    )
                                ),
                                projected_row_kind="ITEM",
                            )
                            for item in component_items
                        ] if frontier_complete else []
                        equation_parent = _projected_source_row(
                            parent,
                            role="CURRENT_TAX_PARENT",
                            projected_row_kind="TOTAL",
                        )
                        if not frontier_complete:
                            if issues is not None:
                                issues.append(
                                    "SUPPLEMENTAL_CURRENT_TAX_FRONTIER_NOT_COMPLETE"
                                )
                        elif _exact_sum(equation_components, equation_parent):
                            equation = _supplemental_equation_receipt(
                                component_rows=equation_components,
                                parent_row=equation_parent,
                                equation_kind="CURRENT_RATE_PLUS_VISIBLE_ADJUSTMENTS_EQUALS_CURRENT_TAX",
                            )
                            equation_rows = [*equation_components, equation_parent]
                            table_equation_receipts.append(equation)
                            table_has_certified_equation = True
                            certified_adjustment_ordinals.update(
                                item["row_ordinal"]
                                for item in equation_components
                                if item["role"]
                                in {
                                    "NON_DEDUCTIBLE_EXPENSE",
                                    "PRIOR_PERIOD_TAX_ADJUSTMENT",
                                }
                            )
                            descriptor = _finalize_supplemental_descriptor(
                                record=record,
                                page=page,
                                section_ordinal=section_ordinal,
                                table_ordinal=table_ordinal,
                                table=table,
                                money_column_ordinals=money_ordinals,
                                canonical_unit=canonical_unit,
                                unit_evidence=unit_evidence,
                                unit_receipt=unit_receipt,
                                source_rows=all_source_rows,
                                rows=equation_rows,
                                presentation_kind="CURRENT_TAX_RECONCILIATION_EXACT_SUM",
                                equation_receipts=[equation],
                                compiled_specs=compiled_specs,
                            )
                            if descriptor is not None:
                                descriptors.append(descriptor)
                                claimed.update(item["row_ordinal"] for item in equation_rows)
                        elif issues is not None:
                            issues.append("SUPPLEMENTAL_CURRENT_TAX_EQUATION_MISMATCH")
                    elif issues is not None:
                        issues.append("SUPPLEMENTAL_CURRENT_TAX_FRONTIER_NOT_COMPLETE")

                nonblank_rows = [
                    item
                    for item in source_rows
                    if item["values_usable"]
                    and any(value is not None for value in item["parsed_values"])
                ]
                direct_parent_surface_rows = [
                    item
                    for item in source_rows
                    if item["matched_role"] == "CURRENT_TAX_PARENT"
                ]
                direct_parent_rows = [
                    item
                    for item in nonblank_rows
                    if item["matched_role"] == "CURRENT_TAX_PARENT"
                ]
                if len(direct_parent_surface_rows) > 1 and issues is not None:
                    issues.append("SUPPLEMENTAL_CURRENT_TAX_PARENT_AXIS_NOT_UNIQUE")
                if (
                    len(nonblank_rows) == 1
                    and len(direct_parent_rows) == 1
                ):
                    direct_parent = _projected_source_row(
                        nonblank_rows[0],
                        role="CURRENT_TAX_PARENT",
                        projected_row_kind="ITEM",
                    )
                    descriptor = _finalize_supplemental_descriptor(
                        record=record,
                        page=page,
                        section_ordinal=section_ordinal,
                        table_ordinal=table_ordinal,
                        table=table,
                        money_column_ordinals=money_ordinals,
                        canonical_unit=canonical_unit,
                        unit_evidence=unit_evidence,
                        unit_receipt=unit_receipt,
                        source_rows=all_source_rows,
                        rows=[direct_parent],
                        presentation_kind="DIRECT_CURRENT_TAX_SINGLETON",
                        equation_receipts=[],
                        compiled_specs=compiled_specs,
                    )
                    if descriptor is not None:
                        descriptors.append(descriptor)
                        claimed.add(direct_parent["row_ordinal"])
                elif (
                    len(direct_parent_surface_rows) == 1
                    and (
                        len(direct_parent_rows) != 1
                        or direct_parent_surface_rows[0]["row_ordinal"] not in claimed
                    )
                    and not table_has_certified_equation
                    and not rate_rows
                    and issues is not None
                ):
                    issues.append("SUPPLEMENTAL_CURRENT_TAX_SINGLETON_FRONTIER_NOT_COMPLETE")

                extra_roles = {
                    "PROFIT_BEFORE_TAX",
                    "CURRENT_TAX_BANK",
                    "SUBSIDIARY_TAX",
                    "DEFERRED_TAX_NET",
                }
                if table_has_certified_equation:
                    extra_roles.update(
                        {"NON_DEDUCTIBLE_EXPENSE", "PRIOR_PERIOD_TAX_ADJUSTMENT"}
                    )
                direct_extras = []
                for role in sorted(extra_roles):
                    surface_matches = [
                        item
                        for item in source_rows
                        if item["matched_role"] == role
                        and item["row_ordinal"] not in claimed
                        and (
                            role
                            not in {
                                "NON_DEDUCTIBLE_EXPENSE",
                                "PRIOR_PERIOD_TAX_ADJUSTMENT",
                            }
                            or item["row_ordinal"] in certified_adjustment_ordinals
                        )
                    ]
                    matches = [
                        item
                        for item in surface_matches
                        if item["values_usable"]
                        and any(value is not None for value in item["parsed_values"])
                    ]
                    if len(surface_matches) > 1 and issues is not None:
                        issues.append("SUPPLEMENTAL_DIRECT_ROLE_AXIS_NOT_UNIQUE:" + role)
                    elif len(surface_matches) == len(matches) == 1:
                        direct_extras.append(
                            _projected_source_row(
                                matches[0], role=role, projected_row_kind="ITEM"
                            )
                        )
                    elif len(surface_matches) == 1 and issues is not None:
                        issues.append("SUPPLEMENTAL_DIRECT_ROLE_FRONTIER_NOT_COMPLETE:" + role)
                if direct_extras:
                    descriptor = _finalize_supplemental_descriptor(
                        record=record,
                        page=page,
                        section_ordinal=section_ordinal,
                        table_ordinal=table_ordinal,
                        table=table,
                        money_column_ordinals=money_ordinals,
                        canonical_unit=canonical_unit,
                        unit_evidence=unit_evidence,
                        unit_receipt=unit_receipt,
                        source_rows=all_source_rows,
                        rows=direct_extras,
                        presentation_kind="DIRECT_SUPPLEMENTAL_TAX_ROLES",
                        equation_receipts=table_equation_receipts,
                        compiled_specs=compiled_specs,
                    )
                    if descriptor is not None:
                        descriptors.append(descriptor)
    if issues is not None:
        issues[:] = sorted(set(issues))
    return sorted(
        descriptors,
        key=lambda item: (
            item["locator"]["selected_page_ordinal"],
            item["locator"]["section_id"],
            item["locator"]["table_id"],
            item["presentation_kind"],
        ),
    )


def _project_primary_page(
    source_page: Mapping[str, Any], *, descriptor: Mapping[str, Any]
) -> dict[str, Any]:
    locator = descriptor["locator"]
    try:
        source_section, source_table = _source_table(
            source_page,
            section_id=locator["section_id"],
            table_id=locator["table_id"],
        )
        columns = source_table["columns"]
        source_rows = source_table["rows"]
    except (KeyError, TypeError, ValueError) as exc:
        raise _error("income-tax primary source locator drifted") from exc
    if (
        canonical_json_sha256_v1(source_page) != descriptor["original_page_json_sha256"]
        or canonical_json_sha256_v1(source_table) != descriptor["original_table_json_sha256"]
    ):
        raise _error("income-tax primary source image drifted")
    projected_rows = []
    root_label = _CANONICAL_LABEL["FAMILY_ROOT_TOTAL"]
    for projected_ordinal, item in enumerate(descriptor["rows"], start=1):
        try:
            source_row = source_rows[item["row_ordinal"] - 1]
            selected = [
                source_row["values_exact"][ordinal - 1]
                for ordinal in descriptor["money_column_ordinals"]
            ]
        except (IndexError, KeyError, TypeError) as exc:
            raise _error("income-tax primary source row drifted") from exc
        if (
            source_row.get("label_exact") != item["label_exact"]
            or source_row.get("row_kind") != item["row_kind"]
            or source_row.get("hierarchy_path_exact") != item["hierarchy_path_exact"]
            or not same_typed_json_v1(selected, item["source_values_exact"])
        ):
            raise _error("income-tax primary source row image drifted")
        role = item["role"]
        canonical = _CANONICAL_LABEL[role]
        ancestry = [root_label, canonical]
        if role in {"CURRENT_YEAR_TAX_EXPENSE", "CURRENT_PERIOD_TAX_EXPENSE_SOURCE_ONLY"}:
            ancestry = [root_label, _CANONICAL_LABEL["CURRENT_YEAR_EXPENSE_CONTEXT"], canonical]
        projected_rows.append(
            {
                "hierarchy_path_exact": (
                    [root_label] if role == "FAMILY_ROOT_TOTAL" else ancestry
                ),
                "label_exact": canonical,
                "row_kind": item.get(
                    "projected_row_kind",
                    "TOTAL" if role == "FAMILY_ROOT_TOTAL" else "ITEM",
                ),
                "values_exact": canonical_clone_v1(selected),
            }
        )
        if projected_ordinal <= 0:  # pragma: no cover - documents the one-based axis
            raise AssertionError
    projected_table = {
        "columns": [
            canonical_clone_v1(columns[ordinal - 1])
            for ordinal in descriptor["money_column_ordinals"]
        ],
        "continuation": "NONE",
        "rows": projected_rows,
        "title_exact": root_label,
        "unit_exact": descriptor["projected_unit_exact"],
    }
    return {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [projected_table],
                "title_exact": root_label,
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _economic_role_axis(presentation: Mapping[str, Any]) -> dict[str, tuple[int | None, ...]]:
    power = {"MILLION_VND": 6, "VND": 0}.get(presentation.get("canonical_unit"))
    if power is None:
        return {}
    return {
        item["role"]: tuple(
            None if value is None else value * (10**power) for value in item["parsed_values"]
        )
        for item in presentation["rows"]
    }


def _presentations_compatible(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_axis = _economic_role_axis(left)
    right_axis = _economic_role_axis(right)
    common = set(left_axis).intersection(right_axis)
    if not common:
        return False
    tolerance = (
        500_000
        if {left["canonical_unit"], right["canonical_unit"]}
        == {
            "MILLION_VND",
            "VND",
        }
        else 0
    )
    compared_lane_count = 0
    for role in common:
        left_observed = {
            ordinal for ordinal, value in enumerate(left_axis[role]) if value is not None
        }
        right_observed = {
            ordinal for ordinal, value in enumerate(right_axis[role]) if value is not None
        }
        if not (
            left_observed.issubset(right_observed)
            or right_observed.issubset(left_observed)
        ):
            return False
        for left_value, right_value in zip(left_axis[role], right_axis[role], strict=True):
            if left_value is None or right_value is None:
                continue
            compared_lane_count += 1
            if abs(left_value - right_value) > tolerance:
                return False
    return compared_lane_count > 0


def _presentation_evidence_contains(
    container: Mapping[str, Any], other: Mapping[str, Any]
) -> bool:
    """Return true only when selecting ``container`` cannot drop ``other`` evidence."""

    container_axis = _economic_role_axis(container)
    other_axis = _economic_role_axis(other)
    if not set(container_axis).issuperset(other_axis):
        return False
    for role, other_values in other_axis.items():
        container_observed = {
            ordinal
            for ordinal, value in enumerate(container_axis[role])
            if value is not None
        }
        other_observed = {
            ordinal for ordinal, value in enumerate(other_values) if value is not None
        }
        if not container_observed.issuperset(other_observed):
            return False
    return True


def _select_primary_presentation(
    page_records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]
) -> tuple[dict[str, Any] | None, list[str]]:
    if _primary_duplicate_source_role_rows(page_records):
        return None, ["DUPLICATE_PRIMARY_INCOME_TAX_SOURCE_ROLE"]
    invalid = _primary_invalid_source_role_rows(page_records, compiled_specs=compiled_specs)
    if invalid:
        reasons = []
        if any("INVALID_PRIMARY_SOURCE_MONEY_UNIT_CONFLICT" in item["reasons"] for item in invalid):
            reasons.append("INVALID_PRIMARY_INCOME_TAX_SOURCE_MONEY_UNIT")
        if any(reason != "INVALID_PRIMARY_SOURCE_MONEY_UNIT_CONFLICT" for item in invalid for reason in item["reasons"]):
            reasons.append("INVALID_PRIMARY_INCOME_TAX_SOURCE_MONEY_CELL")
        return None, reasons
    if _primary_equation_mismatch_axis(page_records, compiled_specs=compiled_specs):
        return None, ["MISMATCHED_PRIMARY_INCOME_TAX_SOURCE_EQUATION"]
    presentations = _primary_presentations(page_records, compiled_specs=compiled_specs)
    if not presentations:
        return None, ["PRIMARY_INCOME_TAX_SOURCE_ROWS_NOT_LOCALLY_USABLE"]
    candidates = []
    for item in presentations:
        source_page = next(
            record["page_json"]
            for record in page_records
            if record["page_json_version_id"] == item["locator"]["page_json_version_id"]
        )
        projected = _project_primary_page(source_page, descriptor=item)
        specs = compiled_specs[item["projected_specs_key"]]
        record = {
            key: canonical_clone_v1(item["locator"][key])
            for key in (
                "document_id",
                "document_ordinal",
                "page_json_version_id",
                "physical_page",
                "selected_page_ordinal",
                "source_logical_name",
                "source_sha256",
            )
        }
        record["page_json"] = projected
        cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
            page_records=[record], compiled_specs=specs
        )
        if cluster.get("status") != READY:
            continue
        regions = cluster["component_regions"]
        candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
            regions=regions,
            page_json_by_version={item["locator"]["page_json_version_id"]: projected},
            compiled_specs=specs,
            query_receipt=(
                build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
            ),
        )
        if candidate.get("status") == READY:
            candidates.append({"cluster": cluster, "descriptor": item})
    if not candidates:
        return None, ["PRIMARY_INCOME_TAX_SOURCE_ROWS_NOT_SCHEMA_MAPPABLE"]
    # A preferred high-precision VND presentation may still omit a direct role
    # or an observed lane carried by a compatible million-VND presentation.
    # Select only from presentations whose evidence frontier contains every
    # other usable presentation; otherwise fail closed rather than silently
    # discarding source-visible evidence.
    dominant = [
        item
        for item in candidates
        if all(
            _presentation_evidence_contains(item["descriptor"], other["descriptor"])
            for other in candidates
        )
    ]
    if not dominant:
        return None, ["CONFLICTING_PRIMARY_INCOME_TAX_SOURCE_PRESENTATIONS"]
    vnd = [item for item in dominant if item["descriptor"]["canonical_unit"] == "VND"]
    pool = vnd if len(vnd) == 1 else dominant
    if len(pool) != 1:
        first = pool[0]
        if not all(
            _presentations_compatible(first["descriptor"], item["descriptor"]) for item in pool[1:]
        ):
            return None, ["CONFLICTING_PRIMARY_INCOME_TAX_SOURCE_PRESENTATIONS"]
        return None, ["MULTIPLE_EQUIVALENT_PRIMARY_INCOME_TAX_SOURCE_PRESENTATIONS"]
    selected = pool[0]
    if not all(
        _presentations_compatible(selected["descriptor"], item["descriptor"])
        for item in candidates
        if item is not selected
    ):
        return None, ["CONFLICTING_PRIMARY_INCOME_TAX_SOURCE_PRESENTATIONS"]
    descriptor = canonical_clone_v1(selected["descriptor"])
    descriptor["corroborating_presentations"] = [
        {
            "canonical_unit": item["descriptor"]["canonical_unit"],
            "locator": canonical_clone_v1(item["descriptor"]["locator"]),
            "role_economic_axis": {
                role: list(values)
                for role, values in _economic_role_axis(item["descriptor"]).items()
            },
            "selected": item is selected,
        }
        for item in candidates
    ]
    descriptor["selection_rule"] = (
        "ROLE_AND_OBSERVED_LANE_EVIDENCE_FRONTIER_DOMINANT_THEN_UNIQUE_VND_"
        "IF_PRESENT_ELSE_UNIQUE_USABLE_PRESENTATION_ALL_OTHER_USABLE_"
        "PRESENTATIONS_EXACT_OR_HALF_MILLION_DISPLAY_COMPATIBLE"
    )
    return {"cluster": selected["cluster"], "descriptor": descriptor}, []


def _primary_selection_conflict_receipt(
    page_records: Sequence[Mapping[str, Any]],
    *,
    reasons: Sequence[str],
    repair_receipts: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    material = {
        "format_version": "INCOME_TAX_PRIMARY_SELECTION_CONFLICT_RECEIPT_V1",
        "adapter_spec_sha256": compiled_specs["income_tax_adapter_spec_sha256"],
        "invalid_source_rows": _primary_invalid_source_role_rows(
            page_records, compiled_specs=compiled_specs
        ),
        "duplicate_source_roles": _primary_duplicate_source_role_rows(page_records),
        "equation_mismatches": _primary_equation_mismatch_axis(
            page_records, compiled_specs=compiled_specs
        ),
        "presentations": _primary_presentations(
            page_records, compiled_specs=compiled_specs
        ),
        "reasons": list(reasons),
        "repair_receipt_ids": [item["receipt_id"] for item in repair_receipts],
        "rule": "VALID_NOTE_CANNOT_HIDE_CONFLICTING_DIRECT_PRIMARY_PRESENTATIONS",
    }
    return {
        **material,
        "receipt_id": "gjitfav1:primary-conflict:"
        + canonical_json_sha256_v1(material),
    }


def _query_adapter_receipt(
    descriptor: Mapping[str, Any],
    *,
    repair_receipts: Sequence[Mapping[str, Any]],
    supplemental_descriptors: Sequence[Mapping[str, Any]],
    strategy: str,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    if strategy not in _QUERY_ADAPTER_STRATEGIES:
        raise _error("income-tax query adapter strategy is invalid")
    material = {
        "adapter_spec_sha256": compiled_specs["income_tax_adapter_spec_sha256"],
        "adapter_format_version": ADAPTER_FORMAT_VERSION,
        "primary_projection_receipt": canonical_clone_v1(descriptor),
        "repair_receipt_ids": [item["receipt_id"] for item in repair_receipts],
        "rule": _QUERY_ADAPTER_RULE,
        "strategy": strategy,
        "supplemental_projection_receipts": canonical_clone_v1(
            list(supplemental_descriptors)
        ),
    }
    return {
        **material,
        "receipt_id": "gjitfav1:query:" + canonical_json_sha256_v1(material),
    }


def _candidate_source_row_axis(
    candidate: Mapping[str, Any] | None,
) -> frozenset[tuple[str, str, str, int]]:
    axis = set()
    for mapping in candidate.get("mappings", []) if type(candidate) is dict else []:
        for ref in mapping.get("source_refs", []):
            locator = ref.get("locator") if type(ref) is dict else None
            key = (
                locator.get("page_json_version_id"),
                locator.get("section_id"),
                locator.get("table_id"),
                ref.get("row_ordinal"),
            ) if type(locator) is dict else None
            if (
                type(key) is tuple
                and all(type(item) is str for item in key[:3])
                and type(key[3]) is int
            ):
                axis.add(key)
    closure = candidate.get("closure_receipt") if type(candidate) is dict else None
    source_only_rows = (
        closure.get("source_only_unmapped_rows", [])
        if type(closure) is dict
        else []
    )
    for item in source_only_rows:
        source_ref = item.get("source_ref") if type(item) is dict else None
        locator = source_ref.get("locator") if type(source_ref) is dict else None
        row_ordinal = (
            source_ref.get("row_ordinal")
            if type(source_ref) is dict
            else None
        )
        key = (
            locator.get("page_json_version_id"),
            locator.get("section_id"),
            locator.get("table_id"),
            row_ordinal,
        ) if type(locator) is dict else None
        if (
            type(key) is tuple
            and all(type(value) is str for value in key[:3])
            and type(key[3]) is int
        ):
            axis.add(key)
    return frozenset(axis)


def _semantic_spec_sha256(specs: Mapping[str, Any]) -> str:
    return canonical_json_sha256_v1({
        "topology": specs["topology"], "evaluation": specs["evaluation"], "schema": specs["schema"],
    })


def _original_basis_label_roles(table: Mapping[str, Any], specs: Mapping[str, Any]) -> list[list[str]]:
    # This is a literal surface inventory, not an ownership/role classifier.
    # The frozen classifier still authenticates path-scoped roles separately.
    aliases: dict[str, set[str]] = {}
    for child in specs["topology"]["children"]:
        for matcher in child["matchers"]:
            for alias in matcher["aliases"]:
                aliases.setdefault(_without_leading_ordinal(_normalized(alias)), set()).add(child["role"])
    return [sorted(aliases.get(_without_leading_ordinal(_normalized(row.get("label_exact"))), set()))
            for row in table["rows"]]


def _original_basis_frontier(
    table: Mapping[str, Any], *, basis: str, specs: Mapping[str, Any],
) -> dict[str, Any]:
    axis = _original_basis_label_roles(table, specs)
    profit = [ordinal for ordinal, roles in enumerate(axis, 1) if "PROFIT_BEFORE_TAX" in roles]
    income = [ordinal for ordinal, roles in enumerate(axis, 1) if "TAXABLE_INCOME" in roles]
    rate = [ordinal for ordinal, roles in enumerate(axis, 1)
            if set(roles) & {"CURRENT_TAX_AT_RATE", "STATUTORY_TAX_AMOUNT_SOURCE_ONLY"}]
    current = [ordinal for ordinal, roles in enumerate(axis, 1) if "CURRENT_TAX_PARENT" in roles]
    start = (rate[0] if len(rate) == 1 else None) if basis == "RATE" else profit[0] if len(profit) == 1 else None
    ends = current if basis == "RATE" else income
    end = ends[0] if len(ends) == 1 else None
    valid = bool(len(profit) == 1 and start is not None and end is not None
                 and profit[0] <= start < end
                 and table["rows"][end - 1].get("row_kind") in {"ITEM", "SUBTOTAL", "TOTAL"}
                 and (basis != "INCOME" or not rate or end < min(rate))
                 and (basis != "RATE" or not income or max(income) < start))
    return {
        "basis": basis, "literal_role_surface_axis": axis,
        "profit_before_tax_source_ordinals": profit,
        "taxable_income_source_ordinals": income, "monetary_rate_source_ordinals": rate,
        "current_tax_parent_source_ordinals": current,
        "start_row_ordinal": start, "terminal_row_ordinal": end,
        "source_boundary_supported": valid,
        "rule": "PRINTED_MEASUREMENT_BASIS_FRONTIER_BEFORE_PRIVATE_QUERY_NO_VALUE_INFERENCE",
    }


def _original_basis_source_coverage(
    table: Mapping[str, Any], *, candidate: Mapping[str, Any] | None,
    private_locator: Mapping[str, Any], money_ordinals: Sequence[int],
    basis: str, frontier: Mapping[str, Any],
    metric_role_axes: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, Any]:
    """Account for *every* original row, including omitted numeric subtotals.

    Source-only retention is not equation proof.  A total with no value-level
    proof is an explicit algorithm hold, not a control guessed from its amount.
    Private references stay in the private-view namespace throughout this audit.
    """
    dispositions: dict[int, set[str]] = {}
    proof_ids: dict[int, set[str]] = {}
    reasons: list[str] = []

    def retain(ref: Any, disposition: str, proof_id: str) -> None:
        if type(ref) is not dict:
            reasons.append("ORIGINAL_BASIS_PRIVATE_SOURCE_REF_INVALID")
            return
        ordinal, locator = ref.get("row_ordinal"), ref.get("locator")
        columns = ref.get("money_column_ordinals")
        if (type(ordinal) is not int or not 1 <= ordinal <= len(table["rows"])
                or type(locator) is not dict
                or any(not same_typed_json_v1(locator.get(key), value) for key, value in private_locator.items())
                or not same_typed_json_v1(columns, list(money_ordinals))):
            reasons.append("ORIGINAL_BASIS_PRIVATE_SOURCE_REF_AXIS_DRIFT")
            return
        row = table["rows"][ordinal - 1]
        if any(not same_typed_json_v1(ref.get(key), row.get(key))
               for key in ("label_exact", "row_kind", "hierarchy_path_exact")):
            reasons.append("ORIGINAL_BASIS_PRIVATE_SOURCE_REF_ROW_DRIFT")
            return
        dispositions.setdefault(ordinal, set()).add(disposition)
        proof_ids.setdefault(ordinal, set()).add(proof_id)

    mappings = candidate.get("mappings", []) if type(candidate) is dict else []
    closure = candidate.get("closure_receipt", {}) if type(candidate) is dict else {}
    for mapping in mappings:
        role, refs = mapping.get("role"), mapping.get("source_refs")
        if role not in _ORIGINAL_BASIS_ROLES[basis]:
            reasons.append("ORIGINAL_BASIS_PRIVATE_SCHEMA_ROLE_NOT_PERMITTED:" + str(role))
        if type(refs) is not list or len(refs) != 1:
            reasons.append("ORIGINAL_BASIS_MULTI_SOURCE_MAPPING_REQUIRES_POPULATION_PROOF")
            continue
        ref = refs[0]
        retain(ref, "SCHEMA_SOURCE_OBSERVATION", str(mapping.get("item_mapping_id")))
        ordinal = ref.get("row_ordinal") if type(ref) is dict else None
        if type(ordinal) is not int or not 1 <= ordinal <= len(table["rows"]):
            continue
        raw = [table["rows"][ordinal - 1]["values_exact"][column - 1] for column in money_ordinals]
        values = mapping.get("values")
        if type(values) is not list or len(values) != len(raw):
            reasons.append("ORIGINAL_BASIS_MAPPING_VALUE_AXIS_INVALID")
            continue
        for source, value in zip(raw, values, strict=True):
            if type(value) is not dict:
                reasons.append("ORIGINAL_BASIS_MAPPING_VALUE_INVALID")
                continue
            if source is None:
                if value.get("coefficient") is not None or value.get("source_text") is not None:
                    reasons.append("ORIGINAL_BASIS_MAPPING_BLANK_NUMERIC_INFERENCE")
            elif type(source) is str and re.search(r"\d", source):
                try:
                    parsed = _source_money(source)
                except (TypeError, ValueError):
                    parsed = {}
                if (parsed.get("state") != "RAW_SIGNED_INTEGER" or type(value.get("coefficient")) is not int
                        or value["coefficient"] != parsed.get("coefficient")
                        or value.get("source_text") != source or value.get("state") != parsed.get("state")):
                    reasons.append("ORIGINAL_BASIS_MAPPING_PRINTED_NUMBER_DRIFT")
            else:
                try:
                    parsed = _source_money(source)
                except (TypeError, ValueError):
                    parsed = {}
                # The operating contract allows printed accounting dashes as
                # zero, with lexical evidence intact.  A blank or continuation
                # marker never obtains that authority.
                if (parsed.get("state") != "DASH_ZERO" or type(value.get("coefficient")) is not int
                        or value["coefficient"] != 0 or value.get("source_text") != source
                        or value.get("state") != "DASH_ZERO"):
                    reasons.append("ORIGINAL_BASIS_MAPPING_NON_NUMERIC_SOURCE_MARKER")
        if (role != "PROFIT_BEFORE_TAX" and frontier["source_boundary_supported"]
                and not frontier["start_row_ordinal"] <= ordinal <= frontier["terminal_row_ordinal"]):
            reasons.append("ORIGINAL_BASIS_SCHEMA_MAPPING_OUTSIDE_PRINTED_FRONTIER")
    for equation in closure.get("equations", []):
        if equation.get("status") not in {"EXACT", "SOURCE_PRESENTATION_ROUNDING_INTERVAL_EXACT"}:
            reasons.append("ORIGINAL_BASIS_EQUATION_NOT_COMPLETE_EXACT_PROOF")
            continue
        equation_id = str(equation.get("equation_id"))
        for refs in equation.get("component_source_refs", []):
            for ref in refs:
                retain(ref, "EXACT_EQUATION_COMPONENT", equation_id)
        for ref in equation.get("result_source_refs", []):
            retain(ref, "EXACT_EQUATION_RESULT", equation_id)
    for item in closure.get("source_only_unmapped_rows", []):
        retain(item.get("source_ref"), "SOURCE_ONLY_UNMAPPED_RETAINED_NOT_EQUATION_PROOF",
               canonical_json_sha256_v1(item))
    for receipt in closure.get("table_receipts", []):
        for key in ("non_money_metric_source_rows", "ratio_metric_source_rows"):
            for item in receipt.get(key, []):
                ordinal = item.get("row_ordinal")
                region = receipt.get("region")
                hits = receipt.get("classification", {}).get("role_hits", [])
                expected_rule = ("DECLARED_VALIDATION_ONLY_NON_MONEY_METRIC_ROW" if key == "non_money_metric_source_rows"
                                 else "DECLARED_SOURCE_RATIO_ROW_PARSED_BY_TYPED_DECIMAL_RATIO_GATE")
                if (type(ordinal) is not int or not 1 <= ordinal <= len(table["rows"])
                        or not same_typed_json_v1(item.get("row"), table["rows"][ordinal - 1])
                        or type(region) is not dict
                        or any(not same_typed_json_v1(region.get(field), value) for field, value in private_locator.items())
                        or item.get("role") not in (metric_role_axes or {}).get(key, ())
                        or item.get("rule") != expected_rule
                        or not any(hit.get("role") == item.get("role")
                                   and type(hit.get("row_ordinal")) is int and hit["row_ordinal"] == ordinal
                                   and type(hit.get("source_order")) is int and hit["source_order"] == ordinal
                                   and hit.get("row_kind") == table["rows"][ordinal - 1]["row_kind"]
                                   for hit in hits)):
                    reasons.append("ORIGINAL_BASIS_NON_MONEY_ROW_AXIS_DRIFT")
                else:
                    dispositions.setdefault(ordinal, set()).add("NON_MONEY_SOURCE_METRIC")
                    proof_ids.setdefault(ordinal, set()).add(canonical_json_sha256_v1(item))
    rows = []
    for ordinal, row in enumerate(table["rows"], 1):
        raw = [row["values_exact"][column - 1] for column in money_ordinals]
        kinds = []
        for value in raw:
            try:
                parsed = _source_money(value)
            except (TypeError, ValueError):
                parsed = {}
            kinds.append("BLANK_SOURCE_CELL" if value is None else
                         "PRINTED_NUMERIC_SOURCE_CELL" if parsed.get("state") == "RAW_SIGNED_INTEGER" else
                         "PRINTED_ACCOUNTING_DASH_ZERO" if parsed.get("state") == "DASH_ZERO" else
                         "SOURCE_NON_NUMERIC_MARKER")
        types = dispositions.setdefault(ordinal, set())
        if not types:
            if all(value is None for value in raw):
                types.add("STRUCTURAL_BLANK_GROUP" if row["row_kind"] == "GROUP" else "BLANK_SOURCE_ROW_RETAINED")
            elif row["row_kind"] in {"TOTAL", "SUBTOTAL"}:
                types.add("UNPROVEN_NUMERIC_TOTAL_SOURCE_CONTROL")
                reasons.append("ORIGINAL_BASIS_UNPROVEN_NUMERIC_TOTAL:" + str(ordinal))
            else:
                types.add("UNCLASSIFIED_QUANTITATIVE_SOURCE_ROW")
                reasons.append("ORIGINAL_BASIS_UNCLASSIFIED_QUANTITATIVE_ROW:" + str(ordinal))
        if (row["row_kind"] in {"TOTAL", "SUBTOTAL"} and any(value is not None for value in raw)
                and not types & {"SCHEMA_SOURCE_OBSERVATION", "EXACT_EQUATION_RESULT", "NON_MONEY_SOURCE_METRIC"}):
            types.add("UNPROVEN_NUMERIC_TOTAL_SOURCE_CONTROL")
            reasons.append("ORIGINAL_BASIS_UNPROVEN_NUMERIC_TOTAL:" + str(ordinal))
        # Complete equations may use printed accounting dashes under the
        # declared numeric convention, but never blanks or layout markers.
        if types & {"EXACT_EQUATION_COMPONENT", "EXACT_EQUATION_RESULT"} and any(
            kind not in {"PRINTED_NUMERIC_SOURCE_CELL", "PRINTED_ACCOUNTING_DASH_ZERO"} for kind in kinds
        ):
            reasons.append("ORIGINAL_BASIS_EQUATION_HAS_UNOBSERVED_OPERAND:" + str(ordinal))
        rows.append({
            "row_ordinal": ordinal, "source_row_exact": canonical_clone_v1(row),
            "money_column_ordinals": list(money_ordinals), "source_values_exact": raw,
            "source_cell_kinds": kinds, "dispositions": sorted(types),
            "private_value_proof_ids": sorted(proof_ids.get(ordinal, set())),
        })
    material = {
        "format_version": "INCOME_TAX_ORIGINAL_BASIS_SOURCE_COVERAGE_RECEIPT_V1",
        "basis": basis, "source_rows": rows, "reasons": sorted(set(reasons)),
        "status": "PASS_ROW_ACCOUNTING_NOT_POPULATION_ACCEPTANCE" if not reasons else "ALGORITHM_HOLD",
        "rule": "FULL_ORIGINAL_ROW_AXIS_TYPED_DISPOSITION_NO_BLANK_ZERO_NO_TOTAL_OMISSION",
    }
    return {**material, "receipt_id": "gjitfav1:original-coverage:" + canonical_json_sha256_v1(material)}


def build_gemini_json_income_tax_original_basis_receipt_v1(
    *, page_records: Sequence[Mapping[str, Any]], locator: Mapping[str, Any],
    basis: str, compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a private original-table proof; NOT a production adapter/acceptance.

    The complete original section owns narrative/scope/unit authority.  The
    identity view changes only the section/table address, never cells, row kinds,
    hierarchy, headers or units.  Every raw row remains in the private evaluator.
    This standalone receipt cannot replace the strict outer query adapter.
    """
    if (type(basis) is not str or basis not in _ORIGINAL_BASIS_ROLES or type(locator) is not dict
            or type(locator.get("section_id")) is not str or not re.fullmatch(r"s[1-9]\d*", locator["section_id"])
            or type(locator.get("table_id")) is not str or not re.fullmatch(r"t[1-9]\d*", locator["table_id"])):
        raise _error("income-tax original basis receipt selector is invalid")
    matches = [record for record in page_records if record.get("page_json_version_id") == locator.get("page_json_version_id")]
    if len(matches) != 1:
        raise _error("income-tax original basis source identity is not unique")
    record = matches[0]
    if not same_typed_json_v1(locator, _record_locator(record, section_id=locator.get("section_id"), table_id=locator.get("table_id"))):
        raise _error("income-tax original basis locator drifted")
    if len({(item["document_id"], item["document_ordinal"], item["source_sha256"], item["source_logical_name"])
            for item in page_records}) != 1 or len({item["page_json_version_id"] for item in page_records}) != len(page_records):
        raise _error("income-tax original basis document/source axis is ambiguous")
    page = record["page_json"]
    section, table = _source_table(page, section_id=locator["section_id"], table_id=locator["table_id"])
    if section.get("content_kind") != "FINANCIAL_NOTE":
        raise _error("income-tax original basis has no original financial-note context")
    if any(type(row) is not dict or type(row.get("values_exact")) is not list
           or len(row["values_exact"]) != len(table["columns"]) for row in table["rows"]):
        raise _error("income-tax original basis raw cell axis is invalid")
    key = f"income_tax_original_{basis.lower()}_specs"
    raw_specs = compiled_specs.get("income_tax_original_basis_source_specs")
    if type(raw_specs) is not dict or set(raw_specs) != {"topology", "evaluation", "schema"}:
        raise _error("income-tax original basis raw source specs are absent")
    rebuilt_base = compile_gemini_json_multitable_hierarchical_family_specs_v1(
        raw_specs["topology"], raw_specs["evaluation"], raw_specs["schema"],
    )
    if any(not same_typed_json_v1(compiled_specs.get(name), rebuilt_base[name])
           for name in ("topology", "evaluation", "schema")):
        raise _error("income-tax original basis raw/base semantic specs drifted")
    specs = _original_note_basis_specs(raw_specs["topology"], raw_specs["evaluation"],
                                      raw_specs["schema"], basis=basis)
    if not same_typed_json_v1(compiled_specs.get(key), specs):
        raise _error("income-tax original basis private semantic specs drifted")
    lane = _multitable_lane_axis(section, table, compiled_specs=specs)
    ordinals = lane.get("money_column_ordinals")
    if not lane.get("complete") or type(ordinals) is not list or len(ordinals) != 2:
        raise _error("income-tax original basis original period axis is incomplete")
    frontier = _original_basis_frontier(table, basis=basis, specs=specs)
    classification = classify_gemini_json_multitable_hierarchical_table_v1(page, section, table, compiled_specs=specs)
    reasons = [] if frontier["source_boundary_supported"] else ["ORIGINAL_BASIS_PRINTED_FRONTIER_UNSUPPORTED"]
    if basis == "RATE" and frontier["source_boundary_supported"] and any(
        _without_leading_ordinal(_normalized(row.get("label_exact"))) in {"nam hien hanh", "ky hien hanh"}
        for row in table["rows"][frontier["start_row_ordinal"] - 1:frontier["terminal_row_ordinal"]]
    ):
        reasons.append("ORIGINAL_BASIS_YEAR_OR_PERIOD_INSIDE_RATE_REQUIRES_INDEPENDENT_POPULATION_PROOF")
    if classification.get("compound_row_projection_receipts"):
        reasons.append("ORIGINAL_BASIS_COMPOUND_ROWS_REQUIRE_BIJECTIVE_SOURCE_MAP")
    original_owner_cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=page_records, compiled_specs=specs,
    )
    original_owned_regions = [region for region in original_owner_cluster.get("component_regions", [])
                              if all(same_typed_json_v1(region.get(key), value) for key, value in locator.items())]
    if original_owner_cluster.get("status") != READY or len(original_owned_regions) != 1:
        reasons.append("ORIGINAL_BASIS_TABLE_NOT_IN_UNMODIFIED_OWNER_FENCED_QUERY")
    local_title_surfaces = [section.get("title_exact"), table.get("title_exact")]
    local_negative_aliases = set(specs["query_policy"].get("hard_negative_aliases", [])) | set(specs["query_policy"].get("reset_aliases", []))
    if any(alias in _normalized(surface) for surface in local_title_surfaces for alias in local_negative_aliases):
        reasons.append("ORIGINAL_BASIS_LOCAL_HARD_NEGATIVE_TITLE")
    reset_aliases = set(specs["query_policy"].get("hard_negative_aliases", [])) | set(specs["query_policy"].get("reset_aliases", []))
    narrative_reset_axis = [{"narrative_ordinal": ordinal, "source_exact": narrative}
                            for ordinal, narrative in enumerate(section.get("narratives_exact") or [], 1)
                            if type(narrative) is str and any(
                                _without_leading_ordinal(_normalized(surface)) in reset_aliases
                                for surface in [narrative, *narrative.splitlines()]
                            )]
    if narrative_reset_axis:
        reasons.append("ORIGINAL_BASIS_ORIGINAL_NARRATIVE_RESET_BOUNDARY")
    view = canonical_clone_v1(page)
    view_section = canonical_clone_v1(section)
    view_section["tables"] = [canonical_clone_v1(table)]
    # Narrowing cannot turn a multi-table narrative into a sole-table authority.
    # Original scope receipt below, not private-view prose, owns that decision.
    view_section["narratives_exact"] = []
    view["sections"] = [view_section]
    private_record = {**canonical_clone_v1(record), "page_json": view}
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(page_records=[private_record], compiled_specs=specs)
    candidate = None
    private_query = None
    if cluster.get("status") == READY:
        private_query = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(cluster["component_regions"])
        candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
            regions=cluster["component_regions"], page_json_by_version={record["page_json_version_id"]: view},
            compiled_specs=specs, query_receipt=private_query,
        )
    if candidate is None or candidate.get("status") != READY:
        reasons.append("ORIGINAL_BASIS_PRIVATE_EVALUATION_NOT_READY")
    private_locator = _record_locator(record, section_id="s1", table_id="t1")
    coverage = _original_basis_source_coverage(table, candidate=candidate, private_locator=private_locator,
                                              money_ordinals=ordinals, basis=basis, frontier=frontier,
                                              metric_role_axes={"non_money_metric_source_rows": specs["non_money_metric_roles"],
                                                                "ratio_metric_source_rows": specs.get("ratio_metric_roles", [])})
    reasons.extend(coverage["reasons"])
    participant_population_axis = [{
        "row_ordinal": item["row_ordinal"], "source_paths_exact": item["source_row_exact"]["hierarchy_path_exact"],
        "printed_population_qualifiers": _printed_population_qualifiers(item["source_row_exact"]["hierarchy_path_exact"] or []),
        "ancestor_population_qualifiers": _printed_population_qualifiers(
            (item["source_row_exact"]["hierarchy_path_exact"] or [])[:-1]
            if (item["source_row_exact"]["hierarchy_path_exact"] or [])[-1:] == [item["source_row_exact"]["label_exact"]]
            else item["source_row_exact"]["hierarchy_path_exact"] or []
        ),
        "dispositions": item["dispositions"],
    } for item in coverage["source_rows"]]
    if any(set(item["ancestor_population_qualifiers"]) & {"PARENT_ENTITY", "SUBSIDIARY_ENTITY"}
           and set(item["dispositions"]) & {"EXACT_EQUATION_COMPONENT", "EXACT_EQUATION_RESULT", "SOURCE_ONLY_UNMAPPED_RETAINED_NOT_EQUATION_PROOF"}
           and "SCHEMA_SOURCE_OBSERVATION" not in item["dispositions"]
           for item in participant_population_axis):
        reasons.append("ORIGINAL_BASIS_VALIDATION_OPERAND_ENTITY_SCOPE_REQUIRES_COMPONENT_PROOF")
    document_scope = _document_report_scope_receipt(page_records)
    scope = _note_report_scope_receipt(section, table, source_paths=[
        ref["hierarchy_path_exact"] for mapping in (candidate or {}).get("mappings", [])
        for ref in mapping.get("source_refs", [])
    ], document_scope=document_scope)
    if scope["conflict"]:
        reasons.append("ORIGINAL_BASIS_ORIGINAL_REPORT_SCOPE_CONFLICT")
    for participant in participant_population_axis:
        report_scopes = sorted(set(participant["ancestor_population_qualifiers"]) & {"CONSOLIDATED", "SEPARATE"})
        if (report_scopes and report_scopes != [scope["report_scope"]]
                and set(participant["dispositions"]) & {
                    "SCHEMA_SOURCE_OBSERVATION", "EXACT_EQUATION_COMPONENT", "EXACT_EQUATION_RESULT",
                    "SOURCE_ONLY_UNMAPPED_RETAINED_NOT_EQUATION_PROOF",
                }):
            reasons.append("ORIGINAL_BASIS_PARTICIPANT_REPORT_SCOPE_REQUIRES_POPULATION_PROOF")
    material = {
        "format_version": "INCOME_TAX_ORIGINAL_NOTE_BASIS_RECEIPT_V1", "basis": basis,
        "locator": canonical_clone_v1(locator), "private_specs_key": key,
        "private_semantic_spec_sha256": _semantic_spec_sha256(specs),
        "raw_source_spec_sha256": canonical_json_sha256_v1(raw_specs),
        "original_page_json_sha256": canonical_json_sha256_v1(page),
        "selected_original_page_axis": [{
            **{key: canonical_clone_v1(value) for key, value in item.items() if key != "page_json"},
            "original_page_json_sha256": canonical_json_sha256_v1(item["page_json"]),
        } for item in page_records],
        "original_section_json_sha256": canonical_json_sha256_v1(section),
        "original_table_json_sha256": canonical_json_sha256_v1(table),
        "original_section_exact": canonical_clone_v1(section),
        "original_lane_axis": lane, "original_unit_axis": _unit_axis(table, compiled_specs=specs),
        "original_printed_duration_lengths": _printed_duration_lengths(table, ordinals, section=section),
        "original_report_scope_receipt": scope, "document_report_scope_receipt": document_scope,
        "basis_frontier": frontier, "source_coverage_receipt": coverage,
        "original_participant_population_axis": participant_population_axis,
        "original_narrative_reset_axis": narrative_reset_axis,
        "identity_view_receipt": {
            "private_page_json_sha256": canonical_json_sha256_v1(view),
            "private_locator": private_locator, "original_locator": canonical_clone_v1(locator),
            "source_rows": [{"private_row_ordinal": ordinal, "original_row_ordinal": ordinal,
                             "row_exact": canonical_clone_v1(row)} for ordinal, row in enumerate(table["rows"], 1)],
            "source_columns_exact": canonical_clone_v1(table["columns"]),
            "money_column_ordinals": ordinals,
            "narrative_authority": "ORIGINAL_SECTION_ONLY_PRIVATE_VIEW_NARRATIVES_REMOVED",
            "rule": "BIJECTIVE_IDENTITY_ROW_COLUMN_VIEW_NO_CANONICAL_SOURCE_REWRITE",
        },
        "original_classification_receipt": classification,
        "original_owner_fenced_cluster": original_owner_cluster,
        "original_owned_region_axis": original_owned_regions,
        "private_cluster": cluster, "private_query_receipt": private_query,
        "private_candidate_proof": candidate,
        "reasons": sorted(set(reasons)),
        "status": "PASS_PRIVATE_ORIGINAL_BASIS_EVIDENCE_NOT_FAMILY_ACCEPTANCE" if not reasons else "ALGORITHM_HOLD",
        "production_adapter_integrated": False, "family_terminal_claimed": False,
        "rule": "INDEPENDENT_ORIGINAL_TABLE_REEVALUATION_KEEP_PRIVATE_PROOF_NAMESPACE_AND_ALL_SOURCE_ROWS",
    }
    return {**material, "receipt_id": "gjitfav1:original-basis:" + canonical_json_sha256_v1(material)}


def validate_gemini_json_income_tax_original_basis_receipt_v1(
    receipt: Any, *, page_records: Sequence[Mapping[str, Any]], compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Cold source rebuild rejects even a fully self-resealed invented receipt."""
    if type(receipt) is not dict:
        raise _error("income-tax original basis receipt is invalid")
    rebuilt = build_gemini_json_income_tax_original_basis_receipt_v1(
        page_records=page_records, locator=receipt.get("locator"), basis=receipt.get("basis"),
        compiled_specs=compiled_specs,
    )
    if not same_typed_json_v1(receipt, rebuilt):
        raise _error("income-tax original basis receipt source replay drifted")
    return rebuilt


def _current_year_source_frontier(
    source_rows: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Authenticate ownership before checking any arithmetic or consuming rows."""
    year = [item for item in source_rows if item["normalized_label"] in {"nam hien hanh", "ky hien hanh"}]
    context_aliases = {"chi phi thue hien hanh"}
    context_aliases.update(alias for child in compiled_specs["topology"]["children"]
                           if child["role"] == "CURRENT_TAX_PARENT"
                           for matcher in child["matchers"] for alias in matcher["aliases"])
    groups = [item for item in source_rows
              if item["normalized_label"] in context_aliases
              and item["row_kind"] == "GROUP"]
    if len(year) != 1 or len(groups) != 1:
        return None
    start, child = groups[0], year[0]
    closings = [item for item in source_rows
                if item["row_ordinal"] > start["row_ordinal"]
                and item["row_kind"] in {"GROUP", "SUBTOTAL", "TOTAL"}]
    if not closings or closings[0]["row_kind"] == "GROUP":
        return None
    parent = closings[0]
    components = [item for item in source_rows
                  if start["row_ordinal"] < item["row_ordinal"] < parent["row_ordinal"]]
    ancestry = start["hierarchy_path_exact"]
    if (ancestry != [start["label_exact"]]
            or not components or components[0] is not child
            or any(value is not None for value in start["source_values_exact"])):
        return None
    for item in components:
        path = item["hierarchy_path_exact"]
        if (item["row_kind"] != "ITEM" or type(path) is not list
                or path != [*ancestry, item["label_exact"]]
                or (item is not child and item["matched_role"] != "PRIOR_PERIOD_TAX_ADJUSTMENT"
                    and item["normalized_label"] != "du phong thieu trong nhung nam truoc")):
            return None
    anonymous = parent["normalized_label"] in {"", "cong", "tong cong"}
    if anonymous:
        if parent["hierarchy_path_exact"] not in ([], [None], ancestry, [*ancestry, None]):
            return None
    elif (parent["hierarchy_path_exact"] not in (
              [parent["label_exact"]], [*ancestry, parent["label_exact"]],
          ) or not _supplemental_rate_parent_matches(
              {**parent, "hierarchy_path_exact": [parent["label_exact"]]}, compiled_specs=compiled_specs,
          )):
        return None
    material = {
        "rule": "EXACT_PRINTED_CURRENT_YEAR_OR_PERIOD_GROUP_DESCENDANTS_FIRST_CLOSING_SOURCE_SUBTOTAL",
        "source_component_role": ("CURRENT_YEAR_TAX_EXPENSE" if child["normalized_label"] == "nam hien hanh"
                                  else "CURRENT_PERIOD_TAX_EXPENSE_SOURCE_ONLY"),
        "group_source_row": canonical_clone_v1(start),
        "component_source_rows": canonical_clone_v1(components),
        "parent_source_row": canonical_clone_v1(parent),
        "anonymous_parent_owned_by_ordered_group": anonymous,
        "ownership_inferred_from_values": False,
    }
    return {**material, "receipt_id": "gjitfav1:year-frontier:" + canonical_json_sha256_v1(material)}


def _recognition_printed_text(value: Any) -> str | None:
    """Fold Vietnamese letters, but never erase punctuation or annotations."""
    if type(value) is not str:
        return None
    folded = unicodedata.normalize("NFD", value.replace("đ", "d").replace("Đ", "D"))
    if any(unicodedata.combining(char) and char not in "\u0300\u0301\u0302\u0303\u0306\u0309\u031b\u0323"
           for char in folded):
        return None
    folded = "".join(char for char in folded if not unicodedata.combining(char))
    if not folded.isascii():
        return None
    return " ".join(folded.lower().split())


def _recognition_immediate_ancestor_owner_v1(
    rows: Sequence[Mapping[str, Any]], components: Sequence[Mapping[str, Any]], *,
    owner_pattern: str, relevance_pattern: str, allow_first_compound_label: bool = False,
) -> dict[str, Any] | None:
    """Prove a repeated printed owner without inventing a GROUP occurrence.

    The entire actual row axis is censused. A present owner row, another raw
    spelling, a deeper path, or a late descendant cannot be rescued by this
    representation. Layout equivalence applies only to the whole first
    owner/newline/leaf label; every original label/path/value is retained.
    """
    if len(components) < 2:
        return None
    first_path = components[0].get("hierarchy_path_exact")
    if type(first_path) is not list or len(first_path) != 2:
        return None
    owner = first_path[0]
    if type(owner) is not str or re.fullmatch(owner_pattern, _recognition_printed_text(owner) or "") is None:
        return None
    ordinals = [item["row_ordinal"] for item in components]
    if ordinals != list(range(ordinals[0], ordinals[0] + len(components))):
        return None
    occurrences, leaves = [], []
    for item in rows:
        label, path = item.get("label_exact"), item.get("hierarchy_path_exact")
        if _normalized(label) == _normalized(owner):
            return None
        if type(path) is not list:
            return None
        for path_ordinal, value in enumerate(path, 1):
            if re.search(relevance_pattern, _normalized(value)):
                if (item["row_ordinal"] not in ordinals or path_ordinal != 1
                        or len(path) != 2 or value != owner):
                    return None
                occurrences.append({"row_ordinal": item["row_ordinal"], "hierarchy_path_ordinal": path_ordinal,
                                    "source_exact": value, "source_sha256": canonical_json_sha256_v1(value),
                                    "source_row_exact": canonical_clone_v1(item)})
    if [item["row_ordinal"] for item in occurrences] != ordinals:
        return None
    for index, item in enumerate(components):
        path, label = item["hierarchy_path_exact"], item["label_exact"]
        if (item["row_kind"] != "ITEM" or len(path) != 2 or path[0] != owner
                or type(path[1]) is not str or not path[1] or _recognition_printed_text(path[1]) is None):
            return None
        compound = False
        if label != path[1]:
            if not allow_first_compound_label or index != 0 or type(label) is not str:
                return None
            lines = label.replace("\\n", "\n").split("\n")
            if (len(lines) != 2 or _recognition_printed_text(lines[0]) != _recognition_printed_text(owner)
                    or _recognition_printed_text(lines[1]) != _recognition_printed_text(path[1])):
                return None
            compound = True
        leaves.append({"row_ordinal": item["row_ordinal"], "label_exact": label,
                       "path_leaf_exact": path[1], "whole_owner_newline_leaf_label": compound})
    material = {
        "owner_representation": "REPEATED_EXACT_IMMEDIATE_ANCESTOR_NOT_A_ROW",
        "owner_source_row": None, "owner_exact": owner, "owner_occurrences": occurrences,
        "component_source_row_ordinals": ordinals, "raw_leaf_evidence": leaves,
        "source_table_row_axis_sha256": canonical_json_sha256_v1(list(rows)),
        "group_created": False, "source_values_changed": False,
        "scope_unit_period_or_amount_authority": False,
        "rule": "WHOLE_ACTUAL_AXIS_EXACT_REPEATED_IMMEDIATE_OWNER_AND_COMPLETE_CONSECUTIVE_CHILDREN",
    }
    return {**material, "receipt_id": "gjitfav1:recognition-ancestor-owner:" + canonical_json_sha256_v1(material)}


def _recognition_expense_source_frontier(
    section: Mapping[str, Any], table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Authenticate a *printed* recognition population, not document acceptance.

    A recognized but malformed surface is a hold, never an absent frontier.
    Deferred income may share the expense-zero representation only when every
    selected cell is independently observed zero.  No residual supplies a cell.
    """
    raw_rows = table.get("rows") or []
    surfaces = [ordinal for ordinal, row in enumerate(raw_rows, 1)
                if type(row) is dict and re.search(
                    r"chi phi thue (?:tndn|thu nhap doanh nghiep) ghi nhan trong bao cao ket qua hoat dong",
                    _normalized(row.get("label_exact")),
                )]
    ancestry_surfaces = [ordinal for ordinal, row in enumerate(raw_rows, 1)
                         if type(row) is dict and any(re.search(
                             r"chi phi thue (?:tndn|thu nhap doanh nghiep) ghi nhan trong bao cao ket qua hoat dong",
                             _normalized(value),
                         ) for value in row.get("hierarchy_path_exact") or [])]
    lane = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
    unit = _unit_axis(table, compiled_specs=compiled_specs)
    material: dict[str, Any] = {
        "format_version": "INCOME_TAX_PRINTED_RECOGNITION_FRONTIER_V1",
        "original_section_json_sha256": canonical_json_sha256_v1(section),
        "original_table_json_sha256": canonical_json_sha256_v1(table),
        "recognition_surface_ordinals": surfaces,
        "recognition_ancestry_surface_ordinals": ancestry_surfaces,
        "lane_axis": lane, "unit_axis": unit,
        "semantic_spec_sha256": _semantic_spec_sha256(compiled_specs),
        "source_values_changed": False, "ownership_inferred_from_values": False,
        "rule": "ACTUAL_BLANK_GROUP_EXACT_CURRENT_AND_OBSERVED_ZERO_DEFERRED_INCOME_FIRST_STANDALONE_ROOT",
    }
    reasons: list[str] = []

    def finish(status: str) -> dict[str, Any]:
        result = {**material, "status": status, "reasons": sorted(set(reasons))}
        return {**result, "receipt_id": "gjitfav1:recognition-frontier:" + canonical_json_sha256_v1(result)}

    if not surfaces and not ancestry_surfaces:
        return finish("NOT_APPLICABLE")
    ancestry_only = not surfaces and bool(ancestry_surfaces)
    if ((not ancestry_only and len(surfaces) != 1) or section.get("content_kind") != "FINANCIAL_NOTE"
            or not _supplemental_owner_matches(section, table, compiled_specs=compiled_specs)):
        reasons.append("RECOGNITION_GROUP_OR_POSITIVE_NOTE_OWNER_NOT_UNIQUE")
        return finish("ALGORITHM_HOLD")
    money = lane.get("money_column_ordinals")
    if not lane.get("complete") or type(money) is not list or len(money) != 2:
        reasons.append("RECOGNITION_MONEY_LANE_AXIS_INCOMPLETE")
    if not unit.get("complete") or unit.get("canonical_unit") not in {"MILLION_VND", "VND"}:
        reasons.append("RECOGNITION_EXPLICIT_LOCAL_UNIT_AXIS_INCOMPLETE")
    if reasons:
        return finish("ALGORITHM_HOLD")
    rows = _supplemental_source_rows(table, money_column_ordinals=money,
                                    role_alias_axis=_supplemental_role_alias_axis(compiled_specs))
    material["source_table_row_axis"] = rows
    start = ancestry_surfaces[0] if ancestry_only else surfaces[0]
    if start + (2 if ancestry_only else 3) > len(rows):
        reasons.append("RECOGNITION_CONTIGUOUS_FOUR_ROW_AXIS_ABSENT")
        return finish("ALGORITHM_HOLD")
    owner_receipt = None
    if ancestry_only:
        current, deferred, root = rows[start - 1:start + 2]
        group = None
        owner_receipt = _recognition_immediate_ancestor_owner_v1(
            rows, [current, deferred],
            owner_pattern=(r"chi phi thue (?:tndn|thu nhap doanh nghiep) ghi nhan trong bao cao ket qua hoat dong "
                           r"(?:rieng|hop nhat)(?: giua nien do)?\s*:?"),
            relevance_pattern=r"chi phi thue (?:tndn|thu nhap doanh nghiep) ghi nhan trong bao cao ket qua hoat dong",
        )
        owner_exact = None if owner_receipt is None else owner_receipt["owner_exact"]
        if owner_receipt is None or ancestry_surfaces != [current["row_ordinal"], deferred["row_ordinal"]]:
            reasons.append("RECOGNITION_COMPLETE_REPEATED_IMMEDIATE_ANCESTOR_OWNER_UNPROVEN")
        material.update({
            "owner_representation": "REPEATED_EXACT_IMMEDIATE_ANCESTOR_NOT_A_ROW",
            "owner_receipt": owner_receipt, "frontier_start_source_row_ordinal": start,
            "group_created": False,
            "rule": "EXACT_REPEATED_IMMEDIATE_ANCESTOR_CURRENT_AND_OBSERVED_ZERO_DEFERRED_FIRST_STANDALONE_ROOT",
        })
    else:
        group, current, deferred, root = rows[start - 1:start + 3]
        owner_exact = group["label_exact"]
    scope_rows = [current, deferred, root] if group is None else [group, current, deferred, root]
    material.update({"group_source_row": group, "current_source_row": current,
                     "deferred_source_row": deferred, "parent_source_row": root,
                     "component_source_rows": [current, deferred],
                     "printed_scope_source_paths_exact": [item["hierarchy_path_exact"]
                                                            for item in scope_rows]})
    group_text = _recognition_printed_text(owner_exact)
    match = re.fullmatch(
        r"chi phi thue (?:tndn|thu nhap doanh nghiep) ghi nhan trong bao cao ket qua hoat dong "
        r"(?P<scope>rieng|hop nhat)(?: giua nien do)?\s*:?", group_text or "",
    )
    if (match is None or (group is not None and (
            group["row_kind"] != "GROUP"
            or group["hierarchy_path_exact"] != [group["label_exact"]]
            or any(value is not None for value in group["source_values_exact"])))):
        reasons.append("RECOGNITION_ACTUAL_BLANK_SELF_OWNED_GROUP_UNPROVEN")
    for item, pattern in ((current, r"chi phi thue tndn\s*-\s*hien hanh"),
                          (deferred, r"thu nhap thue tndn\s*-\s*hoan lai")):
        if (item["row_kind"] != "ITEM"
                or re.fullmatch(pattern, _recognition_printed_text(item["label_exact"]) or "") is None
                or item["hierarchy_path_exact"] != [owner_exact, item["label_exact"]]):
            reasons.append("RECOGNITION_EXACT_ORDERED_DIRECT_CHILDREN_UNPROVEN")
    descendants = [item["row_ordinal"] for item in rows if type(item["hierarchy_path_exact"]) is list
                   and owner_exact in item["hierarchy_path_exact"][:-1]]
    if descendants != [current["row_ordinal"], deferred["row_ordinal"]]:
        reasons.append("RECOGNITION_COMPLETE_GROUP_DESCENDANT_AXIS_UNPROVEN")
    # A later convenient root, a duplicate role, or a differently annotated
    # surface cannot disappear through the shared punctuation normalizer.
    for label in ("chi phi thue tndn hien hanh", "thu nhap thue tndn hoan lai"):
        if sum(item["normalized_label"] == label for item in rows) != 1:
            reasons.append("RECOGNITION_CHILD_SURFACE_AXIS_NOT_UNIQUE")
    roots = [item for item in rows if item["normalized_label"] in _ROOT_LABELS]
    root_text = _recognition_printed_text(root["label_exact"])
    if (len(roots) != 1 or root["row_kind"] != "TOTAL" or root["row_ordinal"] != len(rows)
            or root["hierarchy_path_exact"] != [root["label_exact"]]
            or root_text not in {"chi phi thue tndn", "chi phi thue tndn (*)"}):
        reasons.append("RECOGNITION_FIRST_STANDALONE_EXACT_ROOT_UNPROVEN")
    annotation = None
    if root_text == "chi phi thue tndn (*)":
        expected = ("(*) chi phi thue tndn cho ky ke toan duoc uoc tinh dua vao thu nhap chiu thue "
                    "va co the co nhung dieu chinh tuy thuoc vao su kiem tra cua co quan thue.")
        marked = [(ordinal, raw) for ordinal, raw in enumerate(section.get("narratives_exact") or [], 1)
                  if type(raw) is str and "(*)" in raw]
        owned = section.get("tables") or []
        if (len(owned) != 1 or not same_typed_json_v1(owned[0], table) or len(marked) != 1
                or _recognition_printed_text(marked[0][1]) != expected):
            reasons.append("RECOGNITION_ROOT_ANNOTATION_OWNED_ESTIMATION_CONTEXT_UNPROVEN")
        else:
            ordinal, raw = marked[0]
            annotation = {"marker_exact": "(*)", "root_label_exact": root["label_exact"],
                          "narrative_ordinal": ordinal, "narrative_exact": raw,
                          "narrative_sha256": canonical_json_sha256_v1(raw),
                          "scope_unit_period_or_amount_authority": False,
                          "rule": "SOLE_OWNED_EXACT_ESTIMATION_CONTEXT_NOT_GENERIC_FOOTNOTE_REMOVAL"}
    material["root_annotation_receipt"] = annotation
    if any(not item["values_usable"] or not _all_observed(item["parsed_values"])
           for item in (current, deferred, root)):
        reasons.append("RECOGNITION_OPERAND_OR_RESULT_NOT_FULLY_OBSERVED")
    if deferred["parsed_values"] != [0, 0] or not deferred["values_usable"]:
        reasons.append("RECOGNITION_DEFERRED_INCOME_NOT_OBSERVED_ZERO_IN_EVERY_LANE")
    scopes = _printed_population_qualifiers([
        section.get("title_exact"), table.get("title_exact"),
        *[value for column in table.get("columns") or [] for value in column.get("header_path_exact") or []],
        *[item["source_exact"] for item in _owned_statement_scope_narratives(section)],
        *[value for item in scope_rows
          for value in (item["hierarchy_path_exact"] or [])],
    ])
    expected_scope = None if match is None else {"rieng": "SEPARATE", "hop nhat": "CONSOLIDATED"}[match["scope"]]
    material.update({"printed_report_scope": expected_scope, "local_population_qualifiers": scopes})
    if expected_scope is None or scopes != [expected_scope]:
        reasons.append("RECOGNITION_EXPLICIT_LOCAL_POPULATION_SCOPE_CONFLICT")
    negatives = {*compiled_specs.get("query_policy", {}).get("hard_negative_aliases", []),
                 *compiled_specs.get("query_policy", {}).get("reset_aliases", [])}
    if any(_supplemental_negative_surface(item, negatives) for item in rows[:root["row_ordinal"]]):
        reasons.append("RECOGNITION_SOURCE_POPULATION_AFTER_NEGATIVE_OR_RESET")
    equations = []
    if all(item["values_usable"] and _all_observed(item["parsed_values"]) for item in (current, deferred, root)):
        equations = [{"lane_ordinal": ordinal, "observed_current": c, "observed_deferred_income_zero": d,
                      "observed_root": r, "residual": r - c - d}
                     for ordinal, (c, d, r) in enumerate(zip(current["parsed_values"], deferred["parsed_values"],
                                                            root["parsed_values"], strict=True))]
        if any(item["residual"] for item in equations):
            reasons.append("RECOGNITION_OBSERVED_FORWARD_CLOSURE_NOT_EXACT")
    material["lane_equations"] = equations
    return finish("ALGORITHM_HOLD" if reasons else "PASS")


def _recognition_rate_effect_forward_control(
    section: Mapping[str, Any], table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Retain a finite printed tax-effect reconciliation, never income amounts."""
    recognition = _recognition_expense_source_frontier(section, table, compiled_specs=compiled_specs)
    material: dict[str, Any] = {
        "format_version": "INCOME_TAX_RECOGNITION_RATE_EFFECT_FORWARD_CONTROL_V1",
        "original_section_json_sha256": canonical_json_sha256_v1(section),
        "original_table_json_sha256": canonical_json_sha256_v1(table),
        "semantic_spec_sha256": _semantic_spec_sha256(compiled_specs),
        "recognition_frontier_receipt_id": recognition["receipt_id"],
        "recognition_frontier_status": recognition["status"],
        "lane_axis": canonical_clone_v1(recognition["lane_axis"]),
        "unit_axis": canonical_clone_v1(recognition["unit_axis"]),
        "source_table_rows_exact": canonical_clone_v1(table.get("rows") or []),
        "source_rows": canonical_clone_v1(recognition.get("source_table_row_axis") or []),
        "profit_source_row": None, "rate_source_row": None,
        "adjustment_group_source_row": None, "adjustment_source_rows": [],
        "calculation_source_row": None, "lane_equations": [],
        "measurement_basis": "TAX_EFFECT_NOT_TAXABLE_INCOME_ADJUSTMENT",
        "schema_mapping_authority": False, "source_values_changed": False,
        "ownership_inferred_from_values": False, "profit_times_rate_used": False,
        "rule": "PRINTED_RATE_PLUS_ALL_EXACT_GROUP_SIGNED_EFFECTS_EQUALS_CALCULATION_THEN_OBSERVED_CURRENT",
    }
    reasons: list[str] = []

    def finish(status: str) -> dict[str, Any]:
        result = {**material, "status": status, "reasons": sorted(set(reasons))}
        return {**result, "control_id": "gjitfav1:recognition-rate-effect:" + canonical_json_sha256_v1(result)}

    if recognition["status"] == "NOT_APPLICABLE":
        return finish("NOT_APPLICABLE")
    first_recognition = min(recognition["recognition_surface_ordinals"] or recognition["recognition_ancestry_surface_ordinals"])
    literal_roles = _original_basis_label_roles(table, compiled_specs)
    raw_rows = table.get("rows") or []
    prefix_evidence = [ordinal for ordinal, row in enumerate(raw_rows[:first_recognition - 1], 1)
                       if set(literal_roles[ordinal - 1]) & {"CURRENT_TAX_AT_RATE", "STATUTORY_TAX_AMOUNT_SOURCE_ONLY"}
                       or _normalized(row.get("label_exact")) == "dieu chinh"]
    material["rate_prefix_evidence_ordinals"] = prefix_evidence
    if not prefix_evidence:
        # A pure recognition population is independently meaningful; absence
        # of a RATE reconciliation does not make its recognition proof fail.
        return finish("NOT_APPLICABLE")
    if recognition["status"] != "PASS":
        reasons.append("RECOGNITION_RATE_REQUIRES_COMPLETE_AUTHENTICATED_RECOGNITION_FRONTIER")
        return finish("ALGORITHM_HOLD")
    rows = recognition["source_table_row_axis"]
    recognition_group = recognition["group_source_row"]
    group_ordinal = (recognition_group["row_ordinal"] if recognition_group is not None
                     else recognition["frontier_start_source_row_ordinal"])
    # Every row belongs to this finite source layout.  A later convenient
    # result, extra population or unknown trailing row cannot disappear.
    if group_ordinal < 6 or recognition["parent_source_row"]["row_ordinal"] != len(rows):
        reasons.append("RECOGNITION_RATE_COMPLETE_ORDERED_TABLE_FRONTIER_UNPROVEN")
        return finish("ALGORITHM_HOLD")
    profit, rate = rows[:2]
    calculation = rows[group_ordinal - 2]
    actual_adjustment_owner = _normalized(rows[2]["label_exact"]) == "dieu chinh"
    group = rows[2] if actual_adjustment_owner else None
    adjustments = rows[3 if actual_adjustment_owner else 2:group_ordinal - 2]
    adjustment_owner = None
    if group is None:
        adjustment_owner = _recognition_immediate_ancestor_owner_v1(
            rows, adjustments, owner_pattern=r"dieu chinh:", relevance_pattern=r"^dieu chinh\s*:?$",
            allow_first_compound_label=True,
        )
        material["adjustment_owner_receipt"] = adjustment_owner
        if adjustment_owner is None:
            reasons.append("RECOGNITION_RATE_COMPLETE_REPEATED_IMMEDIATE_ADJUSTMENT_OWNER_UNPROVEN")
    adjustment_owner_exact = group["label_exact"] if group is not None else (
        None if adjustment_owner is None else adjustment_owner["owner_exact"])
    material.update({"profit_source_row": canonical_clone_v1(profit),
                     "rate_source_row": canonical_clone_v1(rate),
                     "adjustment_group_source_row": canonical_clone_v1(group),
                     "adjustment_source_rows": canonical_clone_v1(adjustments),
                     "calculation_source_row": canonical_clone_v1(calculation)})
    for item, text in ((profit, "loi nhuan ke toan truoc thue tndn"),
                       (rate, "thue tinh o thue suat 20%")):
        if (item["row_kind"] != "ITEM" or _recognition_printed_text(item["label_exact"]) != text
                or item["hierarchy_path_exact"] != [item["label_exact"]]):
            reasons.append("RECOGNITION_RATE_EXACT_PROFIT_OR_MONETARY_RATE_SOURCE_UNPROVEN")
    if group is not None and (group["row_kind"] != "GROUP" or _recognition_printed_text(group["label_exact"]) != "dieu chinh:"
            or group["hierarchy_path_exact"] != [group["label_exact"]]
            or any(value is not None for value in group["source_values_exact"])):
        reasons.append("RECOGNITION_RATE_ACTUAL_BLANK_ADJUSTMENT_GROUP_UNPROVEN")
    labels = {
        "thu nhap khong chiu thue": 1,
        "chi phi khong duoc khau tru": 2,
        "dieu chinh so thue phai nop nam truoc": 3,
        "dieu chinh loi nhuan do hop nhat": 4,
        "khac": 5,
    }
    adjustment_labels = [
        _recognition_printed_text(item["hierarchy_path_exact"][-1])
        if group is None and adjustment_owner is not None else _recognition_printed_text(item["label_exact"])
        for item in adjustments
    ]
    ranks = [labels.get(label, 0) for label in adjustment_labels]
    if (not adjustments or adjustment_labels[:2] != ["thu nhap khong chiu thue", "chi phi khong duoc khau tru"]
            or any(rank == 0 for rank in ranks) or len(set(adjustment_labels)) != len(adjustment_labels)
            or ranks != sorted(ranks)
            or any(item["row_kind"] != "ITEM"
                   or item["hierarchy_path_exact"] != [adjustment_owner_exact,
                       item["hierarchy_path_exact"][-1] if group is None and adjustment_owner is not None else item["label_exact"]]
                   for item in adjustments)):
        reasons.append("RECOGNITION_RATE_FINITE_UNIQUE_ORDERED_SIGNED_DESCENDANTS_UNPROVEN")
    if group is not None:
        descendants = [item["row_ordinal"] for item in rows
                       if group["label_exact"] in (item["hierarchy_path_exact"] or [])[:-1]]
        if descendants != [item["row_ordinal"] for item in adjustments]:
            reasons.append("RECOGNITION_RATE_COMPLETE_ADJUSTMENT_DESCENDANT_AXIS_UNPROVEN")
    calculation_text = "chi phi thue tndn tinh tren thu nhap chiu thue ky hien hanh"
    if (calculation["row_kind"] not in {"SUBTOTAL", "TOTAL"}
            or _recognition_printed_text(calculation["label_exact"]) != calculation_text
            or calculation["hierarchy_path_exact"] != [calculation["label_exact"]]
            or sum(_recognition_printed_text(item["label_exact"]) == calculation_text for item in rows) != 1):
        reasons.append("RECOGNITION_RATE_FIRST_EXACT_STANDALONE_CALCULATION_UNPROVEN")
    operands = [profit, rate, *adjustments, calculation]
    if any(not item["values_usable"] or not _all_observed(item["parsed_values"]) for item in operands):
        reasons.append("RECOGNITION_RATE_OPERAND_OR_CALCULATION_NOT_FULLY_OBSERVED")
    if reasons:
        return finish("ALGORITHM_HOLD")
    current = recognition["current_source_row"]
    equations = []
    for ordinal in range(2):
        components = [{"row_ordinal": item["row_ordinal"],
                       "source_text_exact": item["source_values_exact"][ordinal],
                       "coefficient": item["parsed_values"][ordinal]}
                      for item in [rate, *adjustments]]
        total = sum(item["coefficient"] for item in components)
        observed = calculation["parsed_values"][ordinal]
        observed_current = current["parsed_values"][ordinal]
        equations.append({"lane_ordinal": ordinal, "component_source_cells": components,
                          "component_sum": total, "calculation_row_ordinal": calculation["row_ordinal"],
                          "calculation_source_text_exact": calculation["source_values_exact"][ordinal],
                          "observed_calculation": observed, "residual": observed - total,
                          "current_row_ordinal": current["row_ordinal"],
                          "current_source_text_exact": current["source_values_exact"][ordinal],
                          "observed_recognition_current": observed_current,
                          "calculation_current_residual": observed - observed_current})
    material["lane_equations"] = equations
    if any(item["residual"] or item["calculation_current_residual"] for item in equations):
        reasons.append("RECOGNITION_RATE_SIGNED_FORWARD_OR_PRINTED_CURRENT_CORRESPONDENCE_NOT_EXACT")
    return finish("ALGORITHM_HOLD" if reasons else "PASS")


def _competing_taxable_stage_control_v1(
    section: Mapping[str, Any], table: Mapping[str, Any], *, compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Veto competing printed bases only; never select a schema basis or value."""
    rows = table.get("rows") or []
    material = {
        "status": "NOT_APPLICABLE", "competing_stage_pairs": [],
        "independent_schema_basis_ownership_proven": False,
        "source_values_changed": False, "amounts_used_as_authority": False,
        "scope_unit_period_or_mapping_permission_granted": False,
        "rule": "SAME_PRINTED_ANCESTRY_TAXABLE_STAGES_SEPARATED_BY_EXPLICIT_EXEMPT_INCOME_VETO_ONLY",
    }
    if section.get("content_kind") == "FINANCIAL_NOTE":
        axis = _original_basis_label_roles(table, compiled_specs)
        taxable = [ordinal for ordinal, roles in enumerate(axis, 1) if "TAXABLE_INCOME" in roles]
        negative = [*compiled_specs["topology"].get("hard_negative_aliases", []),
                    *compiled_specs["topology"].get("structural_reset_aliases", [])]
        def ancestry(row):
            path, label = row.get("hierarchy_path_exact"), row.get("label_exact")
            return path[:-1] if type(path) is list and path and path[-1] == label else None
        def exempt(row):
            label = _without_leading_ordinal(_normalized(row.get("label_exact")))
            return any(label == cue or label.startswith(cue + " ") for cue in
                       ("thu nhap mien thue", "thu nhap khong chiu thue"))
        for first, later in zip(taxable, taxable[1:], strict=False):
            left, right = rows[first - 1], rows[later - 1]
            common = ancestry(left)
            if (common is None or not same_typed_json_v1(common, ancestry(right))
                    or _without_leading_ordinal(_normalized(left.get("label_exact")))
                    == _without_leading_ordinal(_normalized(right.get("label_exact")))):
                continue
            interval = rows[first - 1:later]
            if any(_supplemental_negative_surface(row, negative) for row in interval):
                continue
            adjustments = [ordinal for ordinal in range(first + 1, later)
                           if exempt(rows[ordinal - 1])
                           and same_typed_json_v1(ancestry(rows[ordinal - 1]), common)]
            if not adjustments:
                continue
            material["competing_stage_pairs"].append({
                "first_taxable_row_ordinal": first, "later_taxable_row_ordinal": later,
                "exempt_income_adjustment_row_ordinals": adjustments,
                "stage_source_rows_exact": [
                    {"row_ordinal": ordinal, "source_row_exact": canonical_clone_v1(rows[ordinal - 1])}
                    for ordinal in [first, *adjustments, later]],
                "common_printed_ancestry_exact": canonical_clone_v1(common),
                "row_ordinals_are_input_table_ordinals": True,
                "same_literal_header_axis_only_not_absolute_period_or_entity_authority": True,
            })
    if material["competing_stage_pairs"]:
        material["status"] = "ALGORITHM_HOLD"
        material["source_table_json_sha256"] = canonical_json_sha256_v1(table)
        material["columns_exact"] = canonical_clone_v1(table.get("columns") or [])
        material["owner_surfaces_exact"] = [section.get("title_exact"), table.get("title_exact")]
        material["reason"] = "SOURCE_VISIBLE_COMPETING_TAXABLE_BASES_WITHOUT_SCHEMA_BASIS_OWNERSHIP"
    return {**material, "receipt_id": "gjitfav1:competing-taxable-stages:" + canonical_json_sha256_v1(material)}


def _tax_population_inventory(
    page_records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Bind original tax populations even when generic evaluation consumed them."""
    aliases = _supplemental_role_alias_axis(compiled_specs)
    output = []
    for record in page_records:
        page = record["page_json"]
        for section_ordinal, section in enumerate(page.get("sections") or [], start=1):
            if section.get("content_kind") != "FINANCIAL_NOTE":
                continue
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                lane = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
                money_ordinals = lane.get("money_column_ordinals") or []
                source_rows = _supplemental_source_rows(
                    table, money_column_ordinals=money_ordinals, role_alias_axis=aliases,
                )
                recognition = _recognition_expense_source_frontier(section, table, compiled_specs=compiled_specs)
                competing_stages = _competing_taxable_stage_control_v1(section, table, compiled_specs=compiled_specs)
                if not (_supplemental_owner_matches(section, table, compiled_specs=compiled_specs)
                        or recognition["status"] != "NOT_APPLICABLE"
                        or competing_stages["status"] != "NOT_APPLICABLE"
                        or any(item["matched_role"] in {
                            "CURRENT_TAX_AT_RATE", "STATUTORY_TAX_AMOUNT_SOURCE_ONLY", "CURRENT_TAX_PARENT",
                        } or item["normalized_label"] == "chi phi thue hien hanh"
                               or "ghi nhan trong bao cao ket qua hoat dong" in item["normalized_label"]
                               for item in source_rows)):
                    continue
                years = [item["row_ordinal"] for item in source_rows
                         if item["normalized_label"] in {"nam hien hanh", "ky hien hanh"}]
                rates = [item["row_ordinal"] for item in source_rows
                         if item["matched_role"] in {"CURRENT_TAX_AT_RATE", "STATUTORY_TAX_AMOUNT_SOURCE_ONLY"}]
                rate_frontiers = []
                for start in rates:
                    closings = [item for item in source_rows if item["row_ordinal"] > start
                                and item["row_kind"] in {"GROUP", "SUBTOTAL", "TOTAL"}]
                    parent = closings[0] if closings and closings[0]["row_kind"] != "GROUP" else None
                    # An untyped GROUP is not evidence that the following
                    # adjustments changed from tax effects to income basis.
                    end = parent["row_ordinal"] if parent is not None else len(source_rows) + 1
                    rate_frontiers.append({
                        "start_row_ordinal": start,
                        "parent_source_row": canonical_clone_v1(parent),
                        "component_row_ordinals": [item["row_ordinal"] for item in source_rows
                                                   if start <= item["row_ordinal"] < end],
                        "source_boundary_status": "PRINTED_CLOSING_ROW" if parent is not None else "MISSING_OR_GROUP_RESET_CLOSURE",
                        "measurement_basis": "TAX_EFFECT_NOT_TAXABLE_INCOME_ADJUSTMENT",
                    })
                material = {
                    "locator": _record_locator(record, section_id=f"s{section_ordinal}", table_id=f"t{table_ordinal}"),
                    "original_page_json_sha256": canonical_json_sha256_v1(page),
                    "original_table_json_sha256": canonical_json_sha256_v1(table),
                    "source_table_row_axis": source_rows,
                    "source_table_rows_exact": canonical_clone_v1(table.get("rows") or []),
                    "owner_surfaces_exact": [section.get("title_exact"), table.get("title_exact")],
                    "owned_statement_scope_narratives": _owned_statement_scope_narratives(section),
                    "lane_axis": lane,
                    "unit_axis": _unit_axis(table, compiled_specs=compiled_specs),
                    "current_year_surface_ordinals": years,
                    "explicit_rate_surface_ordinals": rates,
                    "current_year_frontier": _current_year_source_frontier(source_rows, compiled_specs=compiled_specs),
                    "recognition_expense_frontier": recognition,
                    "competing_taxable_stage_control": competing_stages,
                    "recognition_rate_effect_control": _recognition_rate_effect_forward_control(section, table, compiled_specs=compiled_specs),
                    "rate_frontiers": rate_frontiers,
                    "rule": "ORIGINAL_TAX_POPULATION_BEFORE_GENERIC_CONSUMED_ROW_SUPPRESSION",
                }
                output.append({**material, "receipt_id": "gjitfav1:tax-population:" + canonical_json_sha256_v1(material)})
    return sorted(output, key=lambda item: (
        item["locator"]["selected_page_ordinal"],
        int(item["locator"]["section_id"][1:]),
        int(item["locator"]["table_id"][1:]),
    ))


def _source_context_receipt(
    *,
    compiled_specs: Mapping[str, Any],
    repair_receipts: Sequence[Mapping[str, Any]],
    root_controls: Sequence[Mapping[str, Any]],
    page_records: Sequence[Mapping[str, Any]],
    original_page_records: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    # Preserve unmodified fixture ergonomics. Repaired working records cannot
    # impersonate originals: replay below must reproduce the entire working
    # axis and exact old13 receipts. Active caption before-image is mandatory.
    original = page_records if original_page_records is None else original_page_records
    rebuilt, rebuilt_repairs, caption_projection = _prepare_income_tax_evaluation_records_v1(
        original, compiled_specs=compiled_specs)
    if (not same_typed_json_v1(rebuilt, list(page_records))
            or not same_typed_json_v1(rebuilt_repairs, list(repair_receipts))):
        raise _error("income-tax source context original/evaluation projection replay drifted")
    # Empty repair/control axes are meaningful, authenticated declarations too.
    material = {
        "adapter_spec_sha256": compiled_specs["income_tax_adapter_spec_sha256"],
        "source_repair_spec_sha256": compiled_specs["income_tax_source_repair_spec_sha256"],
        "repair_receipt_ids": [item["receipt_id"] for item in repair_receipts],
        "supplemental_root_controls": canonical_clone_v1(list(root_controls)),
        "tax_population_inventory": _tax_population_inventory(
            page_records, compiled_specs=compiled_specs,
        ),
        "semantic_spec_sha256": _semantic_spec_sha256(compiled_specs),
        "section_caption_projection_receipt": caption_projection,
        "document_report_scope_receipt": _document_report_scope_receipt(page_records),
        "document_statement_period_inventory": _document_statement_period_inventory(page_records, compiled_specs=compiled_specs),
        "rule": "EXACT_INCOME_TAX_SOURCE_CONTEXT_ALL_QUERY_STRATEGIES",
    }
    negative_axis = source_label_discrepancy.registered_negative_source_label_observation_axis_v1(page_records)
    if negative_axis:
        material["registered_source_label_discrepancy_observations"] = negative_axis
    return {**material, "receipt_id": "gjitfav1:source-context:" + canonical_json_sha256_v1(material)}


def _bind_source_context(
    cluster: Mapping[str, Any], *, context: Mapping[str, Any]
) -> dict[str, Any]:
    owner = canonical_clone_v1(cluster.get("owner_receipt"))
    if type(owner) is not dict:
        raise _error("income-tax ready query owner receipt is absent")
    owner["income_tax_source_context_receipt"] = canonical_clone_v1(context)
    return _reseal_cluster(cluster, owner_receipt=owner)


def _original_note_population_ancestry(
    table: Mapping[str, Any], section: Mapping[str, Any], *, row_ordinal: int,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Remove structural ancestry only through a fresh original frontier proof."""
    # The ownership helper requires original numeric operands too.
    lane = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
    rows = _supplemental_source_rows(table, money_column_ordinals=lane.get("money_column_ordinals") or [],
                                    role_alias_axis=_supplemental_role_alias_axis(compiled_specs))
    frontier = _current_year_source_frontier(rows, compiled_specs=compiled_specs)
    deferred_frontier = _deferred_net_source_frontier(rows)
    recognition = _recognition_expense_source_frontier(section, table, compiled_specs=compiled_specs)
    if recognition["status"] == "ALGORITHM_HOLD":
        return None
    if recognition["status"] == "PASS" and row_ordinal in {
        recognition["current_source_row"]["row_ordinal"], recognition["deferred_source_row"]["row_ordinal"],
        recognition["parent_source_row"]["row_ordinal"],
    }:
        material = {
            "rule": ("AUTHENTICATED_REPEATED_RECOGNITION_ANCESTOR_NOT_ENTITY_ANCESTRY_SCOPE_RETAINED"
                     if recognition.get("owner_representation") else
                     "AUTHENTICATED_PRINTED_RECOGNITION_GROUP_NOT_ENTITY_ANCESTRY_SCOPE_RETAINED"),
            "common_population_ancestry_exact": [], "source_rows": [rows[row_ordinal - 1]],
            "printed_scope_source_paths_exact": recognition["printed_scope_source_paths_exact"],
            "recognition_expense_frontier_receipt": recognition,
            "original_table_json_sha256": canonical_json_sha256_v1(table),
        }
        return {**material, "receipt_id": "gjitfav1:note-population:" + canonical_json_sha256_v1(material)}
    recognition_rate = _recognition_rate_effect_forward_control(section, table, compiled_specs=compiled_specs)
    if (recognition_rate["status"] == "PASS" and recognition_rate.get("adjustment_owner_receipt") is not None
            and row_ordinal in [item["row_ordinal"] for item in recognition_rate["adjustment_source_rows"]]):
        material = {
            "rule": "AUTHENTICATED_REPEATED_ADJUSTMENT_ANCESTOR_TAX_EFFECT_CONTROL_NOT_ENTITY_OR_INCOME_BASIS",
            "common_population_ancestry_exact": [], "source_rows": [rows[row_ordinal - 1]],
            "printed_scope_source_paths_exact": recognition["printed_scope_source_paths_exact"],
            "recognition_rate_effect_control": recognition_rate,
            "original_table_json_sha256": canonical_json_sha256_v1(table),
        }
        return {**material, "receipt_id": "gjitfav1:note-population:" + canonical_json_sha256_v1(material)}
    if deferred_frontier is not None and deferred_frontier["net_source_row"]["row_ordinal"] == row_ordinal:
        material = {"rule": "AUTHENTICATED_ORIGINAL_DEFERRED_NET_GROUP_FRONTIER_NOT_ENTITY_ANCESTRY",
                    "common_population_ancestry_exact": [], "source_rows": [deferred_frontier["net_source_row"]],
                    "deferred_net_frontier_receipt": deferred_frontier,
                    "original_table_json_sha256": canonical_json_sha256_v1(table)}
        return {**material, "receipt_id": "gjitfav1:note-population:" + canonical_json_sha256_v1(material)}
    if frontier is not None:
        members = [*frontier["component_source_rows"], frontier["parent_source_row"]]
        matches = [item for item in members if item["row_ordinal"] == row_ordinal]
        if matches:
            row = matches[0]
            material = {
                "rule": "AUTHENTICATED_ORIGINAL_CURRENT_EXPENSE_GROUP_FRONTIER_NOT_ENTITY_ANCESTRY",
                "common_population_ancestry_exact": [], "source_rows": [canonical_clone_v1(row)],
                "current_expense_frontier_receipt": frontier,
                "original_table_json_sha256": canonical_json_sha256_v1(table),
            }
            return {**material, "receipt_id": "gjitfav1:note-population:" + canonical_json_sha256_v1(material)}
    return _primary_bridge_population_ancestry(
        table, row_ordinals=[row_ordinal],
        structural_owner_surfaces=[section.get("title_exact"), table.get("title_exact")],
        structural_owner_aliases=[*compiled_specs["topology"]["parent"]["aliases"],
                                  *compiled_specs["evaluation"]["query_owner_aliases"]],
    )


def _original_note_restored_candidate(receipt: Mapping[str, Any], *, original_region: Mapping[str, Any]) -> dict[str, Any]:
    """Restore only output observations/equations, never private query proofs."""
    if not same_typed_json_v1(receipt["locator"], _record_locator(
            original_region, section_id=original_region["section_id"], table_id=original_region["table_id"])):
        raise _error("income-tax original-note carrier region locator drifted")
    private = receipt["private_candidate_proof"]
    descriptor = {"locator": original_region,
                  "money_column_ordinals": receipt["identity_view_receipt"]["money_column_ordinals"],
                  "rows": [{**item["row_exact"], "row_ordinal": item["original_row_ordinal"]}
                           for item in receipt["identity_view_receipt"]["source_rows"]]}
    output = {key: canonical_clone_v1(value) for key, value in private.items() if key != "closure_receipt"}
    output["component_regions"] = [canonical_clone_v1(original_region)]
    output["mappings"] = _restore_source_refs(private["mappings"], descriptor=descriptor)
    for mapping in output["mappings"]:
        if len(mapping.get("source_refs", [])) == 1:
            mapping["row_id"] = mapping["source_refs"][0]["row_id"]
        mapping["item_mapping_id"] = "gjmthfmv1:item:" + canonical_json_sha256_v1(
            {key: value for key, value in mapping.items() if key != "item_mapping_id"}
        )
    output["closure_receipt"] = {
        "equations": _restore_source_refs(private["closure_receipt"].get("equations", []), descriptor=descriptor),
        "source_only_unmapped_rows": _restore_source_refs(private["closure_receipt"].get("source_only_unmapped_rows", []), descriptor=descriptor),
        "original_basis_receipt_id": receipt["receipt_id"],
    }
    def assert_original_source_locator(value: Any) -> None:
        if type(value) is list:
            for child in value:
                assert_original_source_locator(child)
        elif type(value) is dict:
            if "locator" in value and "row_ordinal" in value and not same_typed_json_v1(value["locator"], original_region):
                raise _error("income-tax original-note output retains private source locator metadata")
            for child in value.values():
                assert_original_source_locator(child)
    assert_original_source_locator(output["mappings"])
    assert_original_source_locator(output["closure_receipt"])
    _reseal_equations(output)
    for key in ("page_json_version_id", "physical_page", "section_id", "table_id"):
        output[key] = receipt["locator"][key]
    output["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in output.items() if key != "candidate_id"}
    )
    return output


def _original_note_bind_supplemental_output_region(candidate: Mapping[str, Any], *, original_region: Mapping[str, Any]) -> dict[str, Any]:
    """Only output refs get carrier metadata; private projection proofs do not."""
    locator = _record_locator(original_region, section_id=original_region["section_id"], table_id=original_region["table_id"])

    def restore(value: Any) -> Any:
        if type(value) is list:
            return [restore(child) for child in value]
        if type(value) is not dict:
            return value
        output = {key: restore(child) for key, child in value.items()}
        if "locator" in output and "row_ordinal" in output:
            if (type(output["locator"]) is not dict
                    or any(not same_typed_json_v1(output["locator"].get(key), item) for key, item in locator.items())):
                raise _error("income-tax supplemental original output locator drifted")
            output["locator"] = canonical_clone_v1(original_region)
        return output

    output = canonical_clone_v1(candidate)
    output["component_regions"] = [canonical_clone_v1(original_region)]
    output["mappings"] = restore(output["mappings"])
    for mapping in output["mappings"]:
        mapping["item_mapping_id"] = "gjmthfmv1:item:" + canonical_json_sha256_v1({key: item for key, item in mapping.items() if key != "item_mapping_id"})
    for key in ("equations", "source_only_unmapped_rows"):
        if key in output["closure_receipt"]:
            output["closure_receipt"][key] = restore(output["closure_receipt"][key])
    _reseal_equations(output)
    output["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1({key: value for key, value in output.items() if key != "candidate_id"})
    return output


def _original_note_population_proofs(
    parts: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]], *,
    page_records: Sequence[Mapping[str, Any]], primary: Mapping[str, Any] | None,
    compiled_specs: Mapping[str, Any], issues: list[str], document_period_inventory: Mapping[str, Any],
) -> dict[str, Any]:
    pages = {item["page_json_version_id"]: item["page_json"] for item in page_records}
    document_scope = _document_report_scope_receipt(page_records)
    populations = []
    for descriptor, candidate in parts:
        locator = descriptor["locator"]
        section, table = _source_table(pages[locator["page_json_version_id"]], section_id=locator["section_id"], table_id=locator["table_id"])
        lane = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
        paths, ancestries = [], []
        for mapping in candidate["mappings"]:
            for ref in mapping.get("source_refs", []):
                if (not all(same_typed_json_v1(ref.get("locator", {}).get(key), value) for key, value in locator.items())
                        or not same_typed_json_v1(ref.get("money_column_ordinals"), descriptor["money_column_ordinals"])):
                    issues.append("ORIGINAL_NOTE_MAPPING_SOURCE_POPULATION_AXIS_DRIFT")
                    continue
                ancestry = _original_note_population_ancestry(table, section, row_ordinal=ref["row_ordinal"], compiled_specs=compiled_specs)
                if ancestry is None or ancestry["common_population_ancestry_exact"]:
                    issues.append("ORIGINAL_NOTE_MAPPING_POPULATION_ANCESTRY_UNPROVEN")
                ancestries.append(ancestry)
                raw_path = ref.get("hierarchy_path_exact") or []
                paths.append(raw_path[:-1] if raw_path[-1:] == [ref.get("label_exact")] else raw_path)
        scope = _note_report_scope_receipt(section, table, source_paths=paths, document_scope=document_scope)
        if scope["conflict"] or scope["report_scope"] is None or scope["local_entity_qualifiers"]:
            issues.append("ORIGINAL_NOTE_REPORT_ENTITY_POPULATION_NOT_PROVEN")
        unit = descriptor["canonical_unit"]
        if unit not in {"MILLION_VND", "VND"} or not same_typed_json_v1(lane.get("money_column_ordinals"), descriptor["money_column_ordinals"]):
            issues.append("ORIGINAL_NOTE_UNIT_OR_PERIOD_AXIS_NOT_PROVEN")
        populations.append({
            "descriptor_id": descriptor["descriptor_id"], "locator": canonical_clone_v1(locator),
            "lane_axis": lane, "canonical_unit": unit, "report_scope_receipt": scope,
            "mapping_ancestry_receipts": ancestries,
            "printed_duration_lengths": _printed_duration_lengths(table, descriptor["money_column_ordinals"], section=section),
            "original_table_json_sha256": canonical_json_sha256_v1(table),
        })
    counterparts = list(populations)
    if primary is not None:
        descriptor = primary["descriptor"]
        locator = descriptor["locator"]
        section, table = _source_table(pages[locator["page_json_version_id"]], section_id=locator["section_id"], table_id=locator["table_id"])
        scope = _note_report_scope_receipt(section, table, source_paths=[item["hierarchy_path_exact"][:-1] for item in descriptor["rows"]], document_scope=document_scope)
        if scope["conflict"] or scope["report_scope"] is None or scope["local_entity_qualifiers"]:
            issues.append("ORIGINAL_NOTE_PRIMARY_REPORT_ENTITY_POPULATION_NOT_PROVEN")
        primary_ancestry = _primary_bridge_population_ancestry(
            table, row_ordinals=[item["row_ordinal"] for item in descriptor["rows"]],
            primary_section=section,
        )
        if primary_ancestry is None or primary_ancestry["common_population_ancestry_exact"]:
            issues.append("ORIGINAL_NOTE_PRIMARY_POPULATION_ANCESTRY_UNPROVEN")
        counterparts.append({
            "descriptor_id": canonical_json_sha256_v1(descriptor), "locator": locator,
            "lane_axis": _multitable_lane_axis(section, table, compiled_specs=compiled_specs),
            "canonical_unit": descriptor["canonical_unit"], "report_scope_receipt": scope,
            "printed_duration_lengths": _printed_duration_lengths(table, descriptor["money_column_ordinals"], section=section),
            "original_table_json_sha256": canonical_json_sha256_v1(table),
            "primary_population_ancestry_receipt": primary_ancestry,
        })
    for population in counterparts:
        section, table = _source_table(pages[population["locator"]["page_json_version_id"]],
                                       section_id=population["locator"]["section_id"], table_id=population["locator"]["table_id"])
        period_proof = _source_period_correspondence_receipt(
            left_locator=population["locator"], right_locator=population["locator"],
            left_money_column_ordinals=population["lane_axis"].get("money_column_ordinals") or [],
            right_money_column_ordinals=population["lane_axis"].get("money_column_ordinals") or [],
            page_records=page_records, compiled_specs=compiled_specs, document_period_inventory=document_period_inventory,
        )
        complete = period_proof["complete"]
        population["source_period_correspondence_receipt"] = period_proof
        population["self_source_duration_proven"] = complete
        if not complete:
            issues.append("ORIGINAL_NOTE_INDIVIDUAL_SOURCE_DURATION_NOT_PROVEN")
    pairs = []
    for index, left in enumerate(counterparts):
        for right in counterparts[index + 1:]:
            left_section, left_table = _source_table(pages[left["locator"]["page_json_version_id"]], section_id=left["locator"]["section_id"], table_id=left["locator"]["table_id"])
            right_section, right_table = _source_table(pages[right["locator"]["page_json_version_id"]], section_id=right["locator"]["section_id"], table_id=right["locator"]["table_id"])
            period_proof = _source_period_correspondence_receipt(
                left_locator=left["locator"], right_locator=right["locator"],
                left_money_column_ordinals=left["lane_axis"].get("money_column_ordinals") or [],
                right_money_column_ordinals=right["lane_axis"].get("money_column_ordinals") or [],
                page_records=page_records, compiled_specs=compiled_specs, document_period_inventory=document_period_inventory,
            )
            same_period = period_proof["complete"]
            same_population = (left["report_scope_receipt"]["report_scope"] == right["report_scope_receipt"]["report_scope"]
                               and left["report_scope_receipt"]["report_scope"] is not None)
            if not same_period or not same_population:
                issues.append("ORIGINAL_NOTE_INDEPENDENT_POPULATION_PERIOD_OR_SCOPE_CONFLICT")
            pairs.append({"left_descriptor_id": left["descriptor_id"], "right_descriptor_id": right["descriptor_id"],
                          "same_source_period": same_period, "same_report_entity_population": same_population,
                          "source_period_correspondence_receipt": period_proof,
                          "amounts_used_as_population_authority": False})
    material = {"populations": counterparts, "pairwise_proofs": pairs,
                "rule": "ORIGINAL_SOURCE_PERIOD_SCOPE_BEFORE_DUPLICATE_AMOUNT_SELECTION_NO_POPULATION_SUM"}
    return {**material, "receipt_id": "gjitfav1:original-populations:" + canonical_json_sha256_v1(material)}


def _temporary_difference_rollforward_control(
    *, page: Mapping[str, Any], section: Mapping[str, Any], table: Mapping[str, Any],
    region: Mapping[str, Any], compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Retain a complete stock/movement/stock control, never an expense mapping."""
    caption = _normalized(re.sub(r"^\([a-zA-Z]\)\s*", "", str(section.get("title_exact") or "").strip()))
    annual = re.fullmatch(r"nam ket thuc ngay 31 thang 12 nam (\d{4})", _normalized(table.get("title_exact")))
    columns = table.get("columns") or []
    if (caption != "bien dong cac chenh lech tam thoi trong nam" or annual is None
            or len(columns) != 3 or any(column.get("value_kind") != "MONEY" for column in columns)):
        return None
    headers = [_normalized(" ".join(column["header_path_exact"])) for column in columns]
    unit_suffix = r"(?: (?:trieu vnd|trieu dong|vnd|dong))?"
    opening = re.fullmatch(r"31 12 (\d{4})" + unit_suffix, headers[0])
    closing = re.fullmatch(r"31 12 (\d{4})" + unit_suffix, headers[2])
    movement = re.fullmatch(r"duoc ghi nhan trong bao cao ket qua hoat dong (?:rieng|hop nhat)" + unit_suffix, headers[1])
    if (opening is None or closing is None or movement is None
            or int(closing[1]) != int(annual[1]) or int(opening[1]) + 1 != int(closing[1])):
        return None
    classifications = [classify_gemini_json_multitable_hierarchical_table_v1(page, section, table, compiled_specs=specs)
                       for specs in (compiled_specs, compiled_specs["income_tax_original_rate_specs"])]
    if (any(item["role_hits"] for item in classifications)
            or any(any(_original_basis_label_roles(table, specs)) for specs in (compiled_specs, compiled_specs["income_tax_original_rate_specs"]))
            or any(_legacy_primary_role_for_label(row.get("label_exact")) is not None for row in table["rows"])):
        return None
    # The frozen unit parser reads "hoạt động" as currency "đồng" after
    # normalization.  Only this exact non-unit semantic phrase is separated;
    # every explicitly printed unit suffix stays in the private unit-only view.
    unit_view = canonical_clone_v1(table)
    semantic_header_controls = []
    semantic_pattern = r"duoc ghi nhan trong bao cao ket qua hoat dong (?:rieng|hop nhat)(?: (?P<unit>trieu vnd|trieu dong|vnd|dong))?"
    for ordinal, header in enumerate(columns[1]["header_path_exact"]):
        semantic = re.fullmatch(semantic_pattern, _normalized(header))
        if semantic is not None:
            unit_view["columns"][1]["header_path_exact"][ordinal] = semantic.group("unit") or ""
            semantic_header_controls.append({"column_ordinal": 2, "header_ordinal": ordinal + 1,
                                             "source_exact": header, "explicit_unit_suffix": semantic.group("unit"),
                                             "rule": "EXACT_PNL_RECOGNITION_PHRASE_IS_NOT_CURRENCY_UNIT"})
    unit = _unit_axis(unit_view, compiled_specs=compiled_specs)
    if not unit.get("complete") or unit.get("canonical_unit") not in {"MILLION_VND", "VND"}:
        return None
    rows = _supplemental_source_rows(table, money_column_ordinals=[1, 2, 3], role_alias_axis=_supplemental_role_alias_axis(compiled_specs))
    if (len(rows) < 2 or rows[-1]["row_kind"] != "TOTAL" or any(row["row_kind"] != "ITEM" for row in rows[:-1])
            or any(not row["normalized_label"] for row in rows[:-1])
            or any(row["hierarchy_path_exact"] != [row["label_exact"]] for row in rows[:-1])
            or rows[-1]["hierarchy_path_exact"] not in ([rows[-1]["label_exact"]], [] if rows[-1]["label_exact"] is None else [rows[-1]["label_exact"]])
            or any(not row["values_usable"] or not _all_observed(row["parsed_values"]) for row in rows)):
        return None
    row_equations = [{"row_ordinal": row["row_ordinal"], "opening": row["parsed_values"][0],
                      "movement": row["parsed_values"][1], "closing": row["parsed_values"][2],
                      "residual": row["parsed_values"][2] - sum(row["parsed_values"][:2])} for row in rows]
    column_equations = [{"column_ordinal": ordinal + 1, "observed_total": rows[-1]["parsed_values"][ordinal],
                         "observed_items": [row["parsed_values"][ordinal] for row in rows[:-1]],
                         "residual": rows[-1]["parsed_values"][ordinal] - sum(row["parsed_values"][ordinal] for row in rows[:-1])}
                        for ordinal in range(3)]
    if any(equation["residual"] for equation in [*row_equations, *column_equations]):
        return None
    material = {"format_version": "ORIGINAL_TEMPORARY_DIFFERENCE_BALANCE_ROLLFORWARD_SOURCE_CONTROL_V1",
                "original_region": canonical_clone_v1(region), "original_page_json_sha256": canonical_json_sha256_v1(page),
                "original_section_json_sha256": canonical_json_sha256_v1(section), "original_table_json_sha256": canonical_json_sha256_v1(table),
                "source_table_exact": canonical_clone_v1(table), "source_row_axis": rows, "unit_axis": unit,
                "non_unit_semantic_header_controls": semantic_header_controls,
                "original_unfiltered_unit_axis": _unit_axis(table, compiled_specs=compiled_specs),
                "classification_receipts": classifications, "opening_year": int(opening[1]), "closing_year": int(closing[1]),
                "row_forward_equations": row_equations, "column_total_equations": column_equations,
                "movement_columns_exported_as_expense": False,
                "rule": "TEMPORARY_DIFFERENCE_BALANCE_MOVEMENT_NOT_TWO_PERIOD_TAX_EXPENSE_PRESENTATION"}
    return {**material, "control_id": "gjitfav1:temporary-difference-rollforward:" + canonical_json_sha256_v1(material)}


def _original_rate_business_transfer_forward_control(
    receipt: Mapping[str, Any], *, compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Prove the printed business/transfer tax chain, never solve a missing cell.

    This is additive evidence: the standalone private basis receipt, including
    its original coverage holds, remains unchanged.  An ITEM business result
    requires the same forward proof as a SUBTOTAL business result.
    """
    section = receipt["original_section_exact"]
    table = section["tables"][int(receipt["locator"]["table_id"][1:]) - 1]
    ordinals = receipt["identity_view_receipt"]["money_column_ordinals"]
    rows = _supplemental_source_rows(table, money_column_ordinals=ordinals,
                                     role_alias_axis=_supplemental_role_alias_axis(compiled_specs))
    business_label = "chi phi thue tndn tu hoat dong kinh doanh"
    transfer_income = r"thu nhap tu (?:hoat dong )?chuyen nhuong bat dong san"
    transfer_tax = r"chi phi thue tndn tu (?:hoat dong )?chuyen nhuong bat dong san"
    recognized = receipt["basis"] == "RATE" and any(
        item["normalized_label"] == business_label
        or re.fullmatch(transfer_income, item["normalized_label"])
        or re.fullmatch(transfer_tax, item["normalized_label"])
        for item in rows
    )
    material = {
        "format_version": "ORIGINAL_RATE_BUSINESS_TRANSFER_FORWARD_CONTROL_V1",
        "original_basis_receipt_id": receipt["receipt_id"],
        "locator": canonical_clone_v1(receipt["locator"]),
        "original_page_json_sha256": receipt["original_page_json_sha256"],
        "original_section_json_sha256": receipt["original_section_json_sha256"],
        "original_table_json_sha256": receipt["original_table_json_sha256"],
        "private_semantic_spec_sha256": receipt["private_semantic_spec_sha256"],
        "adapter_spec_sha256": compiled_specs["income_tax_adapter_spec_sha256"],
        "original_lane_axis": canonical_clone_v1(receipt["original_lane_axis"]),
        "original_unit_axis": canonical_clone_v1(receipt["original_unit_axis"]),
        "original_report_scope_receipt": canonical_clone_v1(receipt["original_report_scope_receipt"]),
        "source_table_exact": canonical_clone_v1(table), "source_row_axis": rows,
        "source_selection": {}, "forward_equations": [], "private_group_equation_proofs": [],
        "completion_proofs": [], "reasons": [],
        "status": "NOT_APPLICABLE" if not recognized else "ALGORITHM_HOLD",
        "source_values_changed": False, "transfer_income_used_as_tax_operand": False,
        "rule": "PRINTED_SOURCE_FRONTIER_BEFORE_FORWARD_SUM_NO_SIGN_SEARCH_RATE_INFERENCE_OR_BACKSOLVE",
    }

    def finish(reason: str | None = None) -> dict[str, Any]:
        if reason is not None:
            material["reasons"].append(reason)
        return {**material, "control_id": "gjitfav1:original-rate-forward:" + canonical_json_sha256_v1(material)}

    if not recognized:
        return finish()
    frontier = receipt["basis_frontier"]
    scope, lane, unit = (receipt[key] for key in (
        "original_report_scope_receipt", "original_lane_axis", "original_unit_axis"))
    if (not frontier["source_boundary_supported"] or not lane.get("complete") or len(ordinals) != 2
            or not same_typed_json_v1(lane.get("money_column_ordinals"), ordinals)
            or not unit.get("complete") or unit.get("canonical_unit") not in {"VND", "MILLION_VND"}
            or scope.get("conflict") or scope.get("local_entity_qualifiers")
            or scope.get("report_scope") not in {"CONSOLIDATED", "SEPARATE"}
            or type(receipt.get("private_candidate_proof")) is not dict
            or receipt["private_candidate_proof"].get("status") != READY
            or canonical_json_sha256_v1(table) != receipt["original_table_json_sha256"]
            or canonical_json_sha256_v1(section) != receipt["original_section_json_sha256"]
            or receipt["original_narrative_reset_axis"]):
        return finish("ORIGINAL_RATE_FORWARD_SOURCE_AXES_OR_PRIVATE_PROOF_INCOMPLETE")
    def path_matches(row: Mapping[str, Any], labels: Sequence[str]) -> bool:
        return (type(row["hierarchy_path_exact"]) is list
                and [_normalized(value) for value in row["hierarchy_path_exact"]] == [_normalized(value) for value in labels])

    business = [row for row in rows if row["normalized_label"] == business_label]
    increases = [row for row in rows if row["normalized_label"] == "dieu chinh tang"]
    decreases = [row for row in rows if row["normalized_label"] == "dieu chinh giam"]
    transfers = [row for row in rows if re.fullmatch(transfer_income, row["normalized_label"])
                 and path_matches(row, [row["label_exact"]])]
    taxes = [row for row in rows if re.fullmatch(transfer_tax, row["normalized_label"])]
    priors = [row for row in rows if row["normalized_label"] in {
        "thue tndn nop bo sung tu cac nam truoc", "nop thue bo sung tu cac nam truoc"}]
    if (any(len(axis) != 1 for axis in (business, increases, decreases, transfers, taxes))
            or len(priors) > 1 or frontier["profit_before_tax_source_ordinals"] != [1]
            or frontier["monetary_rate_source_ordinals"] != [2]
            or frontier["current_tax_parent_source_ordinals"] != [len(rows)]):
        return finish("ORIGINAL_RATE_FORWARD_NONUNIQUE_OR_UNSUPPORTED_SOURCE_FRONTIER")
    business, increase, decrease, transfer, tax = (axis[0] for axis in (business, increases, decreases, transfers, taxes))
    profit, rate, current = rows[0], rows[1], rows[-1]
    prior = priors[0] if priors else None
    increase_children = rows[increase["row_ordinal"]:decrease["row_ordinal"] - 1]
    decrease_children = rows[decrease["row_ordinal"]:business["row_ordinal"] - 1]
    expected_tail = [business, transfer, tax, *priors, current]
    if (increase["row_ordinal"] != 3 or not increase_children or not decrease_children
            or [row["row_ordinal"] for row in expected_tail] != list(range(business["row_ordinal"], len(rows) + 1))
            or business["row_kind"] not in {"ITEM", "SUBTOTAL"}
            or transfer["row_kind"] != "ITEM" or tax["row_kind"] not in {"ITEM", "SUBTOTAL"}
            or current["row_kind"] != "TOTAL" or (prior is not None and prior["row_kind"] != "ITEM")
            or profit["row_kind"] not in {"ITEM", "TOTAL"} or rate["row_kind"] != "ITEM"):
        return finish("ORIGINAL_RATE_FORWARD_UNKNOWN_INTERLEAVED_OR_UNSUPPORTED_SOURCE_ROW")

    if (any(not path_matches(row, [row["label_exact"]]) for row in [profit, rate, increase, decrease, *expected_tail])
            or any(group["row_kind"] != "GROUP" for group in (increase, decrease))
            or any(child["row_kind"] != "ITEM" or not path_matches(child, [group["label_exact"], child["label_exact"]])
                   for group, children in ((increase, increase_children), (decrease, decrease_children)) for child in children)
            or [row["normalized_label"] for row in increase_children] != ["chi phi khong duoc khau tru"]
            or len({row["normalized_label"] for row in decrease_children}) != len(decrease_children)
            or not {row["normalized_label"] for row in decrease_children} <= {
                "thu nhap tu chuyen nhuong bds", "thu nhap tu chuyen nhuong bat dong san", "chuyen lo tu cong ty con"}
            or sum(row["normalized_label"].startswith("thu nhap tu chuyen nhuong ") for row in decrease_children) != 1):
        return finish("ORIGINAL_RATE_FORWARD_GROUP_MEMBERSHIP_OR_SOURCE_POPULATION_UNPROVEN")
    # The complete source grammar is fixed above before any arithmetic.  All
    # original cells (including the nonadditive transfer-income observation)
    # must be observed.  A visible dash is typed DASH_ZERO, never a blank.
    if any(not row["values_usable"] or not _all_observed(row["parsed_values"]) for row in rows):
        return finish("ORIGINAL_RATE_FORWARD_UNOBSERVED_OR_INVALID_SOURCE_CELL")
    if (any(value < 0 for row in [increase, *increase_children] for value in row["parsed_values"])
            or any(value > 0 for row in [decrease, *decrease_children] for value in row["parsed_values"])):
        return finish("ORIGINAL_RATE_FORWARD_PRINTED_ADJUSTMENT_DIRECTION_UNSUPPORTED")
    source_rows = []
    for row in rows:
        source_rows.append({"locator": canonical_clone_v1(receipt["locator"]),
                            "money_column_ordinals": list(ordinals),
                            "source_row_exact": canonical_clone_v1(table["rows"][row["row_ordinal"] - 1]),
                            "row_ordinal": row["row_ordinal"],
                            "source_cells": [_source_money(value) for value in row["source_values_exact"]]})
    material["source_selection"] = {
        "source_rows": source_rows, "profit_row_ordinal": 1, "rate_row_ordinal": 2,
        "increase_group_row_ordinal": increase["row_ordinal"],
        "decrease_group_row_ordinal": decrease["row_ordinal"],
        "business_result_row_ordinal": business["row_ordinal"],
        "transfer_income_nonadditive_row_ordinal": transfer["row_ordinal"],
        "transfer_tax_observation_row_ordinal": tax["row_ordinal"],
        "prior_adjustment_row_ordinal": prior["row_ordinal"] if prior else None,
        "current_result_row_ordinal": current["row_ordinal"],
    }
    private_equations = receipt["private_candidate_proof"]["closure_receipt"].get("equations", [])
    for group, children in ((increase, increase_children), (decrease, decrease_children)):
        coverage = receipt["source_coverage_receipt"]["source_rows"][group["row_ordinal"] - 1]
        proofs = [equation for equation in private_equations
                  if equation.get("status") == "EXACT" and equation.get("equation_id") in coverage["private_value_proof_ids"]
                  and [ref.get("row_ordinal") for ref in equation.get("result_source_refs", [])] == [group["row_ordinal"]]
                  and sorted(ref.get("row_ordinal") for refs in equation.get("component_source_refs", []) for ref in refs)
                  == sorted(child["row_ordinal"] for child in children)]
        if len(proofs) != 1:
            return finish("ORIGINAL_RATE_FORWARD_INDEPENDENT_PRIVATE_GROUP_PROOF_ABSENT")
        material["private_group_equation_proofs"].append(canonical_clone_v1(proofs[0]))
    equations = [("INCREASE_GROUP", increase_children, increase), ("DECREASE_GROUP", decrease_children, decrease),
                 ("BUSINESS_TAX_FORWARD", [rate, increase, decrease], business),
                 ("CURRENT_TAX_FORWARD", [business, tax, *priors], current)]
    for kind, components, result in equations:
        material["forward_equations"].append({
            "equation_kind": kind, "component_row_ordinals": [row["row_ordinal"] for row in components],
            "result_row_ordinal": result["row_ordinal"], "component_coefficients": [row["parsed_values"] for row in components],
            "result_coefficients": result["parsed_values"],
            "residuals": [result["parsed_values"][lane] - sum(row["parsed_values"][lane] for row in components) for lane in range(2)],
            "status": "EXACT_ALL_OBSERVED_LANES" if _exact_sum(components, result) else "NONZERO_RESIDUAL",
        })
    if any(equation["status"] != "EXACT_ALL_OBSERVED_LANES" for equation in material["forward_equations"]):
        return finish("ORIGINAL_RATE_FORWARD_PRINTED_ACCOUNTING_EQUATION_MISMATCH")
    material["status"] = "PASS"
    material["completion_proofs"] = [
        {"original_row_ordinal": business["row_ordinal"], "proof_kind": "EXACT_FORWARD_RESULT"},
        {"original_row_ordinal": tax["row_ordinal"],
         "proof_kind": "OBSERVED_NESTED_TRANSFER_TAX_COMPONENT_IN_EXACT_CURRENT_FORWARD_CLOSURE"},
    ]
    return finish()


def _build_original_note_adapter_bundle(
    page_records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any],
    source_context: Mapping[str, Any], repair_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any] | None:
    """Fresh raw carrier and independent NOTE populations, never generic output."""
    if not any(item["explicit_rate_surface_ordinals"] for item in source_context["tax_population_inventory"]):
        rate_aliases = {alias for child in compiled_specs["topology"]["children"]
                        if child["role"] in {"CURRENT_TAX_AT_RATE", "STATUTORY_TAX_AMOUNT_SOURCE_ONLY"}
                        for matcher in child["matchers"] for alias in matcher["aliases"]}
        if not any(_without_leading_ordinal(_normalized(surface)) in rate_aliases
                   for record in page_records for section in record["page_json"].get("sections") or []
                   if section.get("content_kind") == "FINANCIAL_NOTE"
                   for table in section.get("tables") or [] for row in table.get("rows") or []
                   for surface in [row.get("label_exact"), *(row.get("hierarchy_path_exact") or [])]):
            # Retrieval shortcut only: any literal label/path anchor still
            # triggers a fresh owner-fenced query.  No cached candidate output
            # or amount is used as mapping authority.
            return None
    carrier = coalesce_gemini_json_multitable_hierarchical_document_v1(page_records=page_records, compiled_specs=compiled_specs)
    if carrier.get("status") != READY:
        return None
    pages = {item["page_json_version_id"]: item["page_json"] for item in page_records}
    basis_receipts, has_rate = [], False
    ancestry_rate_controls = []
    for region in carrier["component_regions"]:
        section, table = _source_table(pages[region["page_json_version_id"]], section_id=region["section_id"], table_id=region["table_id"])
        if section.get("content_kind") != "FINANCIAL_NOTE":
            continue
        recognition_rate = _recognition_rate_effect_forward_control(section, table, compiled_specs=compiled_specs)
        if recognition_rate["status"] == "PASS":
            recognition = _recognition_expense_source_frontier(section, table, compiled_specs=compiled_specs)
            if (recognition.get("owner_representation") == "REPEATED_EXACT_IMMEDIATE_ANCESTOR_NOT_A_ROW"
                    or recognition_rate.get("adjustment_owner_receipt") is not None):
                # This whole finite prefix has its own observed forward proof.
                # It is not a private RATE/INCOME basis receipt, and its tax
                # effects must never acquire income-basis schema meanings.
                ancestry_rate_controls.append({"locator": canonical_clone_v1(region),
                                               "recognition_frontier": recognition,
                                               "forward_control": recognition_rate})
                has_rate = True
                continue
        classification = classify_gemini_json_multitable_hierarchical_table_v1(
            pages[region["page_json_version_id"]], section, table, compiled_specs=compiled_specs["income_tax_original_rate_specs"],
        )
        roles = {hit["role"] for hit in classification["role_hits"]}
        bases = []
        rate_hits = [hit for hit in classification["role_hits"] if hit["role"] in {"CURRENT_TAX_AT_RATE", "STATUTORY_TAX_AMOUNT_SOURCE_ONLY"}]
        rate_ordinal = rate_hits[0]["row_ordinal"] if len(rate_hits) == 1 else None
        current_ordinals = [hit["row_ordinal"] for hit in classification["role_hits"] if hit["role"] == "CURRENT_TAX_PARENT"]
        literal_roles = _original_basis_label_roles(table, compiled_specs["income_tax_original_rate_specs"])
        independent_tax_effect = bool(rate_ordinal is not None and len(current_ordinals) == 1 and any(
            set(row_roles) & {"NON_DEDUCTIBLE_EXPENSE", "NON_TAXABLE_AGGREGATE"}
            and rate_ordinal < ordinal < current_ordinals[0] for ordinal, row_roles in enumerate(literal_roles, 1)
        ))
        taxable_base_calculation = bool(
            rate_ordinal is not None and not independent_tax_effect and any(
                hit["role"] == "TAXABLE_INCOME" and hit["row_ordinal"] < rate_ordinal for hit in classification["role_hits"])
        )
        # A printed tax calculation on TAXABLE income is not a second PBT
        # tax-effect reconciliation.  Keep its existing full INCOME evaluation;
        # matching a monetary rate alias alone must not reinterpret its basis.
        # This also applies to repeated printed taxable stages and payable
        # rollforwards.  A genuine mixed table has a separate post-rate income
        # adjustment frontier, evaluated privately rather than exported as income.
        if len(rate_hits) == 1 and {"PROFIT_BEFORE_TAX", "CURRENT_TAX_PARENT"} <= roles and not taxable_base_calculation:
            bases.append("RATE")
            has_rate = True
        if "TAXABLE_INCOME" in roles:
            bases.append("INCOME")
        record = next(item for item in page_records if item["page_json_version_id"] == region["page_json_version_id"])
        for basis in bases:
            basis_receipts.append(build_gemini_json_income_tax_original_basis_receipt_v1(
                page_records=page_records, locator=_record_locator(record, section_id=region["section_id"], table_id=region["table_id"]),
                basis=basis, compiled_specs=compiled_specs,
            ))
    if not has_rate:
        return None
    issues = []
    parts = []
    authenticated_rate_axis = set()
    authenticated_rate_axis.update(tuple(item["locator"][key] for key in ("page_json_version_id", "section_id", "table_id"))
                                   for item in ancestry_rate_controls)
    coverage_completions = []
    forward_controls = [_original_rate_business_transfer_forward_control(receipt, compiled_specs=compiled_specs)
                        for receipt in basis_receipts if receipt["basis"] == "RATE"]
    forward_controls = [control for control in forward_controls if control["status"] != "NOT_APPLICABLE"]
    for receipt in basis_receipts:
        completed = []
        controls = [control for control in forward_controls if control["original_basis_receipt_id"] == receipt["receipt_id"]]
        if any(control["status"] != "PASS" for control in controls):
            issues.append("ORIGINAL_NOTE_RATE_BUSINESS_TRANSFER_FORWARD_CONTROL_INCOMPLETE")
            continue
        if (receipt["status"] != "PASS_PRIVATE_ORIGINAL_BASIS_EVIDENCE_NOT_FAMILY_ACCEPTANCE"
                and type(receipt.get("private_candidate_proof")) is dict
                and receipt["private_candidate_proof"].get("status") == READY
                and receipt["basis_frontier"]["source_boundary_supported"]
                and receipt["reasons"] and all(re.fullmatch(r"ORIGINAL_BASIS_UNPROVEN_NUMERIC_TOTAL:\d+", reason) for reason in receipt["reasons"])):
            # A complete INCOME stage need not independently close the separate
            # RATE stage again.  Only an independently PASS, same-original-table
            # complementary basis can supply its exact missing total proof.
            for reason in receipt["reasons"]:
                ordinal = int(reason.rsplit(":", 1)[1])
                own = receipt["basis_frontier"]
                forward_proofs = [(control, proof) for control in controls for proof in control["completion_proofs"]
                                  if proof["original_row_ordinal"] == ordinal]
                if len(forward_proofs) == 1:
                    control, proof = forward_proofs[0]
                    completed.append({"receipt_id": receipt["receipt_id"], "original_row_ordinal": ordinal,
                                      "source_row_exact": receipt["source_coverage_receipt"]["source_rows"][ordinal - 1]["source_row_exact"],
                                      "independent_forward_control_id": control["control_id"], "proof_kind": proof["proof_kind"],
                                      "rule": "EXACT_ORIGINAL_ROW_HAS_INDEPENDENT_OBSERVED_FORWARD_ACCOUNTING_CONTROL"})
                    continue
                if own["start_row_ordinal"] <= ordinal <= own["terminal_row_ordinal"]:
                    break
                row = receipt["source_coverage_receipt"]["source_rows"][ordinal - 1]
                peers = [peer for peer in basis_receipts
                         if peer["basis"] != receipt["basis"]
                         and peer["status"] == "PASS_PRIVATE_ORIGINAL_BASIS_EVIDENCE_NOT_FAMILY_ACCEPTANCE"
                         and same_typed_json_v1(peer["locator"], receipt["locator"])
                         and peer["original_page_json_sha256"] == receipt["original_page_json_sha256"]
                         and peer["original_table_json_sha256"] == receipt["original_table_json_sha256"]
                         and same_typed_json_v1(peer["original_lane_axis"], receipt["original_lane_axis"])
                         and same_typed_json_v1(peer["original_unit_axis"], receipt["original_unit_axis"])
                         and (peer["basis_frontier"]["terminal_row_ordinal"] < own["start_row_ordinal"]
                              or own["terminal_row_ordinal"] < peer["basis_frontier"]["start_row_ordinal"])
                         and peer["basis_frontier"]["start_row_ordinal"] <= ordinal <= peer["basis_frontier"]["terminal_row_ordinal"]
                         and same_typed_json_v1(peer["source_coverage_receipt"]["source_rows"][ordinal - 1]["source_row_exact"], row["source_row_exact"])
                         and set(peer["source_coverage_receipt"]["source_rows"][ordinal - 1]["dispositions"]) & {"SCHEMA_SOURCE_OBSERVATION", "EXACT_EQUATION_RESULT"}]
                if len(peers) != 1:
                    break
                completed.append({"receipt_id": receipt["receipt_id"], "original_row_ordinal": ordinal,
                                  "independent_complementary_receipt_id": peers[0]["receipt_id"],
                                  "source_row_exact": row["source_row_exact"],
                                  "independent_value_proof_ids": peers[0]["source_coverage_receipt"]["source_rows"][ordinal - 1]["private_value_proof_ids"],
                                  "rule": "DISJOINT_PRINTED_STAGE_SAME_ORIGINAL_TABLE_TOTAL_HAS_INDEPENDENT_EXACT_VALUE_PROOF"})
        if (receipt["status"] != "PASS_PRIVATE_ORIGINAL_BASIS_EVIDENCE_NOT_FAMILY_ACCEPTANCE"
                and len(completed) != len(receipt["reasons"])):
            issues.append("ORIGINAL_NOTE_BASIS_EVIDENCE_INCOMPLETE:" + receipt["basis"])
            continue
        coverage_completions.extend(completed)
        descriptor = {"descriptor_id": receipt["receipt_id"], "locator": receipt["locator"],
                      "canonical_unit": receipt["original_unit_axis"].get("canonical_unit"),
                      "money_column_ordinals": receipt["identity_view_receipt"]["money_column_ordinals"]}
        original_regions = [region for region in carrier["component_regions"]
                            if all(same_typed_json_v1(region.get(key), value) for key, value in receipt["locator"].items())]
        if len(original_regions) != 1:
            raise _error("income-tax original-note output requires one original carrier region")
        parts.append((descriptor, _original_note_restored_candidate(receipt, original_region=original_regions[0])))
        if receipt["basis"] == "RATE":
            authenticated_rate_axis.add(tuple(receipt["locator"][key] for key in ("page_json_version_id", "section_id", "table_id")))
    supplemental_issues: list[str] = []
    supplemental = _supplemental_presentations(page_records, compiled_specs=compiled_specs, issues=supplemental_issues,
                                              authenticated_rate_table_axis=frozenset(authenticated_rate_axis))
    issues.extend(supplemental_issues)
    for descriptor in supplemental:
        original_regions = [region for region in carrier["component_regions"]
                            if all(same_typed_json_v1(region.get(key), value) for key, value in descriptor["locator"].items())]
        if len(original_regions) != 1:
            issues.append("ORIGINAL_NOTE_SUPPLEMENTAL_REGION_NOT_IN_ORIGINAL_CARRIER")
            continue
        part = _evaluate_supplemental_descriptor(descriptor, repaired_pages=pages, compiled_specs=compiled_specs)
        parts.append((descriptor, _original_note_bind_supplemental_output_region(part, original_region=original_regions[0])))
    primary, primary_reasons = _select_primary_presentation(page_records, compiled_specs=compiled_specs)
    if primary is None and any(reason.startswith(("CONFLICTING_PRIMARY_", "MULTIPLE_EQUIVALENT_PRIMARY_", "INVALID_PRIMARY_",
                                                  "DUPLICATE_PRIMARY_", "MISMATCHED_PRIMARY_")) for reason in primary_reasons):
        issues.extend(primary_reasons)
    # No original owned source table may disappear merely because a private
    # candidate contains enough other rows.  Basis receipts cover full raw axes;
    # other tables require explicit supplemental rows or root-control evidence.
    coverage = []
    for region in carrier["component_regions"]:
        locator_key = tuple(region[key] for key in ("page_json_version_id", "section_id", "table_id"))
        section, table = _source_table(pages[locator_key[0]], section_id=locator_key[1], table_id=locator_key[2])
        if section.get("content_kind") != "FINANCIAL_NOTE":
            issues.append("ORIGINAL_NOTE_CARRIER_CONTAINS_NON_NOTE_REGION")
            continue
        ancestry_controls = [item for item in ancestry_rate_controls
                             if tuple(item["locator"][key] for key in ("page_json_version_id", "section_id", "table_id")) == locator_key]
        if ancestry_controls:
            if len(ancestry_controls) != 1:
                raise _error("income-tax repeated ancestry forward control is not unique")
            control = ancestry_controls[0]
            coverage.append({"region": canonical_clone_v1(region), "original_table_json_sha256": canonical_json_sha256_v1(table),
                             "basis_receipt_ids": [], "supplemental_claimed_ordinals": sorted({
                                 row["row_ordinal"] for descriptor in supplemental
                                 if tuple(descriptor["locator"][key] for key in ("page_json_version_id", "section_id", "table_id")) == locator_key
                                 for row in descriptor["rows"]}),
                             "unaccounted_quantitative_row_ordinals": [],
                             "source_rows_exact": canonical_clone_v1(table["rows"]),
                             "source_only_table_control": canonical_clone_v1(control),
                             "rule": "COMPLETE_FINITE_RECOGNITION_AND_RATE_EFFECT_FORWARD_CONTROLS_NOT_PRIVATE_BASIS_WAIVER"})
            continue
        movement_control = _temporary_difference_rollforward_control(
            page=pages[locator_key[0]], section=section, table=table, region=region, compiled_specs=compiled_specs,
        )
        if movement_control is not None:
            coverage.append({"region": canonical_clone_v1(region), "original_table_json_sha256": canonical_json_sha256_v1(table),
                             "basis_receipt_ids": [], "supplemental_claimed_ordinals": [], "unaccounted_quantitative_row_ordinals": [],
                             "source_rows_exact": canonical_clone_v1(table["rows"]), "source_only_table_control": movement_control})
            continue
        basis_ids = [item["receipt_id"] for item in basis_receipts if tuple(item["locator"][key] for key in ("page_json_version_id", "section_id", "table_id")) == locator_key]
        claimed = {row["row_ordinal"] for descriptor in supplemental
                   if tuple(descriptor["locator"][key] for key in ("page_json_version_id", "section_id", "table_id")) == locator_key
                   for row in descriptor["rows"]}
        claimed.update(control["root_source_row"]["row_ordinal"] for control in source_context["supplemental_root_controls"]
                       if tuple(control["locator"][key] for key in ("page_json_version_id", "section_id", "table_id")) == locator_key)
        lane = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
        ordinals = lane.get("money_column_ordinals") or []
        if not lane.get("complete") or len(ordinals) != 2:
            issues.append("ORIGINAL_NOTE_CARRIER_SOURCE_PERIOD_AXIS_INCOMPLETE")
        uncovered = [ordinal for ordinal, row in enumerate(table["rows"], 1) if not basis_ids and ordinal not in claimed
                     and any(row["values_exact"][column - 1] is not None for column in ordinals)]
        if uncovered:
            issues.append("ORIGINAL_NOTE_UNACCOUNTED_SOURCE_POPULATION_ROWS")
        coverage.append({"region": canonical_clone_v1(region), "original_table_json_sha256": canonical_json_sha256_v1(table),
                         "basis_receipt_ids": basis_ids, "supplemental_claimed_ordinals": sorted(claimed),
                         "unaccounted_quantitative_row_ordinals": uncovered, "source_rows_exact": canonical_clone_v1(table["rows"])})
    population_proof = _original_note_population_proofs(parts, page_records=page_records, primary=primary,
                                                      compiled_specs=compiled_specs, issues=issues,
                                                      document_period_inventory=source_context["document_statement_period_inventory"])
    if not parts:
        issues.append("ORIGINAL_NOTE_POPULATION_PARTS_ABSENT")
    material = {
        "adapter_format_version": ORIGINAL_NOTE_ADAPTER_FORMAT_VERSION,
        "adapter_spec_sha256": compiled_specs["income_tax_adapter_spec_sha256"],
        "strategy": _ORIGINAL_NOTE_STRATEGY, "rule": "INDEPENDENT_ORIGINAL_NOTE_POPULATIONS_BEFORE_GENUINE_PRIMARY_COMPARISON",
        "repair_receipt_ids": [item["receipt_id"] for item in repair_receipts],
        "source_context_receipt_id": source_context["receipt_id"],
        "original_shared_query_receipt": build_gemini_json_multitable_hierarchical_region_query_receipt_v1(carrier["component_regions"]),
        "basis_table_receipts": basis_receipts, "supplemental_projection_receipts": supplemental,
        "independent_basis_coverage_completion_receipts": coverage_completions,
        "original_rate_forward_control_receipts": forward_controls,
        "primary_projection_receipt": primary["descriptor"] if primary is not None else None,
        "primary_selection_reasons": primary_reasons,
        "source_population_coverage": coverage, "independent_population_receipt": population_proof,
        "reasons": sorted(set(issues)),
    }
    if ancestry_rate_controls:
        material["ancestry_recognition_rate_source_controls"] = canonical_clone_v1(ancestry_rate_controls)
    if "INVALID_PRIMARY_INCOME_TAX_SOURCE_MONEY_UNIT" in primary_reasons:
        material["primary_selection_conflict_receipt"] = _primary_selection_conflict_receipt(
            page_records, reasons=primary_reasons, repair_receipts=repair_receipts, compiled_specs=compiled_specs,
        )
    adapter = {**material, "receipt_id": "gjitfav1:original-query:" + canonical_json_sha256_v1(material)}
    return {"carrier": carrier, "adapter": adapter, "parts": parts, "primary": primary,
            "status": READY if not issues else UNRESOLVED, "reasons": sorted(set(issues))}


def _evaluate_original_note_adapter(
    bundle: Mapping[str, Any], *, compiled_specs: Mapping[str, Any],
    repair_receipts: Sequence[Mapping[str, Any]], source_context: Mapping[str, Any],
    page_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if bundle["status"] != READY or not bundle["parts"]:
        first = bundle["carrier"]["component_regions"][0]
        material = {
            "claim_boundary": CLAIM_BOUNDARY, "component_regions": canonical_clone_v1(bundle["carrier"]["component_regions"]),
            **{key: first[key] for key in ("document_id", "page_json_version_id", "physical_page", "section_id", "table_id", "source_logical_name", "source_sha256")},
            "family_id": FAMILY_ID, "mappings": [], "reasons": bundle["reasons"], "status": UNRESOLVED,
            "closure_receipt": {"original_note_adapter_receipt": canonical_clone_v1(bundle["adapter"]),
                                "income_tax_source_context_receipt": canonical_clone_v1(source_context)},
        }
        return {**material, "candidate_id": "gjmthfcv1:candidate:" + canonical_json_sha256_v1(material)}
    selection_parts, identical_source_controls, seen_source = [], [], {}
    for descriptor, part in bundle["parts"]:
        unique = []
        for mapping in part["mappings"]:
            identity = canonical_json_sha256_v1({
                "role": mapping["role"], "report_norm_id": mapping["report_norm_id"], "unit": mapping["unit"],
                "source_refs": [{key: canonical_clone_v1(ref[key]) for key in (
                    "row_ordinal", "row_kind", "label_exact", "hierarchy_path_exact", "money_column_ordinals",
                )} | {"locator": {key: ref["locator"][key] for key in descriptor["locator"]}}
                                for ref in mapping["source_refs"]],
            })
            if identity in seen_source:
                if not same_typed_json_v1(mapping["values"], seen_source[identity]["values"]):
                    raise _error("income-tax same-original-source observation values drifted")
                identical_source_controls.append({"descriptor_id": descriptor["descriptor_id"],
                                                  "source_identity_sha256": identity, "mapping": canonical_clone_v1(mapping)})
            else:
                seen_source[identity] = mapping
                unique.append(mapping)
        selection_parts.append((descriptor, {"status": READY, "mappings": unique}))
    selected, suppressed, conflict = _select_supplemental_role_mappings(selection_parts)
    template = canonical_clone_v1(bundle["parts"][0][1])
    template["component_regions"] = canonical_clone_v1(bundle["carrier"]["component_regions"])
    if conflict:
        return _unresolved_from_candidate(template, reason=conflict, evidence=bundle["adapter"])
    note = {key: canonical_clone_v1(value) for key, value in template.items() if key != "closure_receipt"}
    note["component_regions"] = canonical_clone_v1(bundle["carrier"]["component_regions"])
    note["mappings"] = [selected[role][0] for role in sorted(selected)]
    note["closure_receipt"] = {
        "equations": [canonical_clone_v1(equation) for _, part in bundle["parts"] for equation in part["closure_receipt"].get("equations", [])],
        "source_only_unmapped_rows": [canonical_clone_v1(row) for _, part in bundle["parts"] for row in part["closure_receipt"].get("source_only_unmapped_rows", [])],
        "original_note_adapter_receipt": canonical_clone_v1(bundle["adapter"]),
        "suppressed_equivalent_note_mappings": suppressed,
        "identical_original_source_observation_controls": identical_source_controls,
        "rule": "INDEPENDENT_SOURCE_NOTE_POPULATIONS_UNION_NO_CROSS_POPULATION_ADDITION",
    }
    note["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1({key: value for key, value in note.items() if key != "candidate_id"})
    note = _recognition_rate_source_only_projection(note, source_context=source_context)
    if note.get("status") != READY:
        return note
    primary = bundle["primary"]
    if primary is not None:
        primary_candidate = _evaluate_selected_primary(primary, repaired_pages={item["page_json_version_id"]: item["page_json"] for item in page_records},
                                                       repair_receipts=repair_receipts, compiled_specs=compiled_specs)
        note = _merge_note_and_primary_candidates(note, primary_candidate, descriptor=primary["descriptor"],
                                                  repair_receipts=repair_receipts, compiled_specs=compiled_specs,
                                                  strategy=_ORIGINAL_NOTE_STRATEGY, page_records=page_records)
    else:
        note = _reseal_candidate(note, descriptor=None, repair_receipts=repair_receipts,
                                 strategy=_ORIGINAL_NOTE_STRATEGY, compiled_specs=compiled_specs)
    return _seal_income_tax_source_controls(note, source_context=source_context, repaired_records=page_records, compiled_specs=compiled_specs)


def _recover_income_tax_query_cluster_v1(
    *,
    page_records: Any,
    base_cluster: Mapping[str, Any],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Preserve a valid note; otherwise select one direct primary presentation."""

    if type(page_records) not in {list, tuple} or not page_records:
        raise _error("income-tax page-record axis is invalid")
    repaired_records, repair_receipts, caption_projection = _prepare_income_tax_evaluation_records_v1(
        page_records, compiled_specs=compiled_specs
    )
    selected_base = canonical_clone_v1(base_cluster)
    if repair_receipts or caption_projection["ordered_caption_repair_ids"]:
        # Source repairs are applied only to private page clones.  A row-level
        # repair can legitimately change the generic row classification, so
        # regions sealed against the unmodified selected JSON must never be
        # replayed against the repaired clone.  Re-coalesce the exact repaired
        # document and carry those freshly sealed regions through evaluation.
        selected_base = coalesce_gemini_json_multitable_hierarchical_document_v1(
            page_records=repaired_records, compiled_specs=compiled_specs
        )
    root_issues: list[str] = []
    root_controls = _supplemental_root_controls(
        repaired_records, compiled_specs=compiled_specs, issues=root_issues
    )
    context = _source_context_receipt(
        compiled_specs=compiled_specs,
        repair_receipts=repair_receipts,
        root_controls=root_controls,
        page_records=repaired_records,
        original_page_records=page_records,
    )
    if root_issues:
        owner = canonical_clone_v1(selected_base.get("owner_receipt"))
        if type(owner) is dict:
            owner["income_tax_source_context_receipt"] = context
        return _reseal_cluster(
            selected_base,
            component_regions=[],
            **({"owner_receipt": owner} if type(owner) is dict else {}),
            reasons=root_issues,
            status=UNRESOLVED,
        )
    original_bundle = _build_original_note_adapter_bundle(
        repaired_records, compiled_specs=compiled_specs, source_context=context, repair_receipts=repair_receipts,
    )
    if original_bundle is not None:
        carrier = original_bundle["carrier"]
        owner = canonical_clone_v1(carrier.get("owner_receipt")) or {}
        owner["income_tax_source_context_receipt"] = context
        owner["income_tax_query_adapter_receipt"] = original_bundle["adapter"]
        # READY here means the original query carrier is authenticated.  All
        # semantic holds are preserved in the adapter and final disposition.
        return _reseal_cluster(carrier, owner_receipt=owner, status=READY, reasons=[])
    note_candidate = None
    if selected_base.get("status") == READY:
        regions = selected_base["component_regions"]
        pages = {item["page_json_version_id"]: item["page_json"] for item in repaired_records}
        candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
            regions=regions,
            page_json_by_version=pages,
            compiled_specs=compiled_specs,
            query_receipt=(
                build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
            ),
        )
        if candidate.get("status") == READY:
            note_candidate = candidate
    primary, reasons = _select_primary_presentation(repaired_records, compiled_specs=compiled_specs)
    if note_candidate is not None and primary is None:
        if any(
            reason.startswith("CONFLICTING_PRIMARY_")
            or reason.startswith("MULTIPLE_EQUIVALENT_PRIMARY_")
            or reason.startswith("INVALID_PRIMARY_")
            or reason.startswith("DUPLICATE_PRIMARY_")
            or reason.startswith("MISMATCHED_PRIMARY_")
            for reason in reasons
        ):
            owner = canonical_clone_v1(selected_base.get("owner_receipt"))
            if type(owner) is not dict:
                raise _error("income-tax valid note owner receipt is absent")
            owner["income_tax_primary_selection_conflict_receipt"] = (
                _primary_selection_conflict_receipt(
                    repaired_records,
                    reasons=reasons,
                    repair_receipts=repair_receipts,
                    compiled_specs=compiled_specs,
                )
            )
            return _reseal_cluster(
                selected_base,
                component_regions=[],
                owner_receipt=owner,
                reasons=reasons,
                status=UNRESOLVED,
            )
        supplemental_issues: list[str] = []
        supplemental_descriptors = _supplemental_presentations(
            repaired_records,
            compiled_specs=compiled_specs,
            issues=supplemental_issues,
            consumed_source_rows=_candidate_source_row_axis(note_candidate),
        )
        if supplemental_issues or supplemental_descriptors:
            return _reseal_cluster(
                selected_base,
                component_regions=[],
                reasons=supplemental_issues or ["SUPPLEMENTAL_SOURCE_WITHOUT_PRIMARY_PRESENTATION"],
                status=UNRESOLVED,
            )
        return _bind_source_context(selected_base, context=context)
    if primary is None:
        owner = canonical_clone_v1(selected_base.get("owner_receipt"))
        if any(
            reason.startswith("INVALID_PRIMARY_")
            or reason.startswith("DUPLICATE_PRIMARY_")
            or reason.startswith("MISMATCHED_PRIMARY_")
            for reason in reasons
        ):
            receipt = _primary_selection_conflict_receipt(
                repaired_records,
                reasons=reasons,
                repair_receipts=repair_receipts,
                compiled_specs=compiled_specs,
            )
            if type(owner) is not dict:
                evidence = [
                    *receipt["invalid_source_rows"],
                    *receipt["duplicate_source_roles"],
                    *receipt["equation_mismatches"],
                    *receipt["presentations"],
                ]
                if not evidence:
                    raise _error("income-tax primary failure evidence is absent")
                locator = evidence[0]["locator"]
                owner = {
                    "alias": "INVALID_EXACT_PRIMARY_INCOME_STATEMENT_TAX_ROWS",
                    "leading_component_positions": [],
                    "leading_component_rule": "FAMILY_LOCAL_DIRECT_SOURCE_PROJECTION",
                    "outline_top_level_number": None,
                    "position": [
                        locator["selected_page_ordinal"],
                        int(locator["section_id"][1:]),
                        int(locator["table_id"][1:]),
                    ],
                    "source_exact": None,
                }
            owner["income_tax_primary_selection_conflict_receipt"] = receipt
        return _reseal_cluster(
            selected_base,
            component_regions=[],
            **({"owner_receipt": owner} if type(owner) is dict else {}),
            reasons=reasons or canonical_clone_v1(selected_base.get("reasons", [])),
            status=UNRESOLVED,
        )
    projected_cluster = primary["cluster"]
    supplemental_issues: list[str] = []
    supplemental_descriptors = _supplemental_presentations(
        repaired_records,
        compiled_specs=compiled_specs,
        issues=supplemental_issues,
        consumed_source_rows=_candidate_source_row_axis(note_candidate),
    )
    if supplemental_issues:
        return _reseal_cluster(
            selected_base,
            component_regions=[],
            reasons=supplemental_issues,
            status=UNRESOLVED,
        )
    strategy = (
        (
            "DIRECT_NOTE_PLUS_SUPPLEMENTAL_NOTE_PLUS_PRIMARY_INCOME_STATEMENT_"
            "SOURCE_PRESENTATION"
        )
        if note_candidate is not None and supplemental_descriptors
        else (
            "DIRECT_NOTE_PLUS_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION"
            if note_candidate is not None
            else "DIRECT_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION"
        )
    )
    adapter = _query_adapter_receipt(
        primary["descriptor"],
        repair_receipts=repair_receipts,
        supplemental_descriptors=supplemental_descriptors,
        strategy=strategy,
        compiled_specs=compiled_specs,
    )
    output_cluster = selected_base if note_candidate is not None else projected_cluster
    owner = canonical_clone_v1(output_cluster.get("owner_receipt"))
    if type(owner) is not dict:
        owner = {
            "alias": "EXACT_PRIMARY_INCOME_STATEMENT_TAX_ROWS",
            "leading_component_positions": [],
            "leading_component_rule": "FAMILY_LOCAL_DIRECT_SOURCE_PROJECTION",
            "outline_top_level_number": None,
            "position": [
                primary["descriptor"]["locator"]["selected_page_ordinal"],
                int(primary["descriptor"]["locator"]["section_id"][1:]),
                int(primary["descriptor"]["locator"]["table_id"][1:]),
            ],
            "source_exact": None,
        }
    owner["income_tax_query_adapter_receipt"] = adapter
    owner["income_tax_source_context_receipt"] = context
    return _reseal_cluster(
        output_cluster,
        owner_receipt=owner,
        reasons=[],
        status=READY,
    )


@_document_period_operation
def recover_gemini_json_income_tax_query_cluster_v1(
    *, page_records: Any, base_cluster: Mapping[str, Any], compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    result = _recover_income_tax_query_cluster_v1(
        page_records=page_records, base_cluster=base_cluster, compiled_specs=compiled_specs)
    _, _, projection = _prepare_income_tax_evaluation_records_v1(page_records, compiled_specs=compiled_specs)
    # A top-level family-local cluster field is supported by the frozen indexed
    # validator (no exact cluster-key set); no fake owner is invented for N/U.
    return _reseal_cluster(result, income_tax_section_caption_projection_receipt=projection)


def adapt_gemini_json_income_tax_indexed_query_evidence_v1(
    *,
    indexed_query_evidence: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    checked = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    cluster_by_ordinal = {
        item["document_ordinal"]: item["cluster"] for item in checked["candidate_dispositions"]
    }
    records_by_ordinal: dict[int, list[dict[str, Any]]] = {}
    for axis in checked["selected_page_axis"]:
        page = page_json_by_document.get(axis["document_ordinal"], {}).get(
            axis["page_json_version_id"]
        )
        if type(page) is not dict:
            raise _error("income-tax indexed replay page is absent")
        records_by_ordinal.setdefault(axis["document_ordinal"], []).append(
            {**canonical_clone_v1(axis), "page_json": page}
        )
    clusters = []
    for document in checked["selected_document_axis"]:
        ordinal = document["document_ordinal"]
        clusters.append(
            recover_gemini_json_income_tax_query_cluster_v1(
                page_records=records_by_ordinal[ordinal],
                base_cluster=cluster_by_ordinal[ordinal],
                compiled_specs=compiled_specs,
            )
        )
    rebuilt = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=checked["selected_document_axis"],
        selected_page_axis=checked["selected_page_axis"],
        document_clusters=clusters,
        query_policy_sha256=canonical_json_sha256_v1(compiled_specs["query_policy"]),
    )
    return validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        rebuilt, compiled_specs=compiled_specs
    )


def build_gemini_json_income_tax_region_query_receipt_v1(
    regions: Any, *, cluster: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    shared = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
    adapter = None
    context = None
    if cluster is not None and type(cluster.get("owner_receipt")) is dict:
        adapter = cluster["owner_receipt"].get("income_tax_query_adapter_receipt")
        context = cluster["owner_receipt"].get("income_tax_source_context_receipt")
    if type(context) is not dict:
        raise _error("income-tax query source context receipt is absent")
    if not same_typed_json_v1(cluster.get("income_tax_section_caption_projection_receipt"),
                              context.get("section_caption_projection_receipt")):
        raise _error("income-tax query caption source projection axis is absent or drifted")
    material = {
        "adapter_receipt": canonical_clone_v1(adapter),
        "format_version": QUERY_RECEIPT_FORMAT_VERSION,
        "source_context_receipt": canonical_clone_v1(context),
        "shared_query_receipt": shared,
    }
    return {
        **material,
        "query_receipt_id": "gjitfav1:query-receipt:" + canonical_json_sha256_v1(material),
    }


def _validate_query_receipt(value: Any, *, regions: Any) -> dict[str, Any]:
    expected_shared = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
    if (
        type(value) is not dict
        or set(value)
        != {
            "adapter_receipt",
            "format_version",
            "query_receipt_id",
            "source_context_receipt",
            "shared_query_receipt",
        }
        or value.get("format_version") != QUERY_RECEIPT_FORMAT_VERSION
        or not same_typed_json_v1(value.get("shared_query_receipt"), expected_shared)
    ):
        raise _error("income-tax query receipt does not bind exact fragments")
    material = {
        key: canonical_clone_v1(item) for key, item in value.items() if key != "query_receipt_id"
    }
    if value["query_receipt_id"] != "gjitfav1:query-receipt:" + canonical_json_sha256_v1(material):
        raise _error("income-tax query receipt identity drifted")
    return canonical_clone_v1(value)


def _restore_source_refs(value: Any, *, descriptor: Mapping[str, Any]) -> Any:
    row_by_projected = {ordinal: item for ordinal, item in enumerate(descriptor["rows"], start=1)}
    locator = descriptor["locator"]

    def visit(item: Any) -> Any:
        if type(item) is list:
            return [visit(child) for child in item]
        if type(item) is not dict:
            return item
        output = {key: visit(child) for key, child in item.items()}
        source_locator = output.get("locator")
        projected_ordinal = output.get("row_ordinal")
        if (
            type(source_locator) is dict
            and source_locator.get("page_json_version_id") == locator["page_json_version_id"]
            and source_locator.get("section_id") == "s1"
            and source_locator.get("table_id") == "t1"
            and type(projected_ordinal) is int
            and projected_ordinal in row_by_projected
        ):
            source = row_by_projected[projected_ordinal]
            for key, source_value in locator.items():
                if key in output["locator"]:
                    output["locator"][key] = canonical_clone_v1(source_value)
            output["hierarchy_path_exact"] = canonical_clone_v1(source["hierarchy_path_exact"])
            output["label_exact"] = source["label_exact"]
            output["money_column_ordinals"] = canonical_clone_v1(
                descriptor["money_column_ordinals"]
            )
            output["row_id"] = f"r{source['row_ordinal']}"
            output["row_kind"] = source["row_kind"]
            output["row_ordinal"] = source["row_ordinal"]
        return output

    return visit(canonical_clone_v1(value))


def _reseal_equations(candidate: dict[str, Any]) -> None:
    equations = candidate.get("closure_receipt", {}).get("equations", [])
    replacements = {}
    for equation in equations if type(equations) is list else []:
        old = equation.get("equation_id")
        if type(old) is not str:
            continue
        material = {key: item for key, item in equation.items() if key != "equation_id"}
        new = "gjitfav1:equation:" + canonical_json_sha256_v1(material)
        equation["equation_id"] = new
        replacements[old] = new

    def replace(value: Any) -> Any:
        if type(value) is str:
            return replacements.get(value, value)
        if type(value) is list:
            return [replace(item) for item in value]
        if type(value) is dict:
            return {key: replace(item) for key, item in value.items()}
        return value

    if replacements:
        replaced = replace(candidate["closure_receipt"])
        candidate["closure_receipt"] = replaced


def _reseal_candidate(
    candidate: Mapping[str, Any],
    *,
    descriptor: Mapping[str, Any] | None,
    repair_receipts: Sequence[Mapping[str, Any]],
    strategy: str,
    compiled_specs: Mapping[str, Any],
    restore_primary_source_refs: bool = True,
    primary_candidate_proof: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    output = canonical_clone_v1(candidate)
    if descriptor is not None and restore_primary_source_refs:
        output = _restore_source_refs(output, descriptor=descriptor)
        for mapping in output.get("mappings", []):
            refs = mapping.get("source_refs")
            if type(refs) is list and len(refs) == 1:
                mapping["row_id"] = refs[0]["row_id"]
            material = {key: item for key, item in mapping.items() if key != "item_mapping_id"}
            mapping["item_mapping_id"] = "gjmthfmv1:item:" + canonical_json_sha256_v1(material)
        _reseal_equations(output)
    output["claim_boundary"] = CLAIM_BOUNDARY
    material = {
        "adapter_spec_sha256": compiled_specs["income_tax_adapter_spec_sha256"],
        "adapter_format_version": ADAPTER_FORMAT_VERSION,
        "primary_projection_receipt": canonical_clone_v1(descriptor),
        "source_repair_receipts": canonical_clone_v1(list(repair_receipts)),
        "strategy": strategy,
    }
    if primary_candidate_proof is not None:
        material["primary_candidate_proof"] = canonical_clone_v1(primary_candidate_proof)
    output["closure_receipt"]["income_tax_adapter_receipt"] = {
        **material,
        "receipt_id": "gjitfav1:candidate:" + canonical_json_sha256_v1(material),
    }
    candidate_material = {key: item for key, item in output.items() if key != "candidate_id"}
    output["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(candidate_material)
    return output


def _printed_primary_root_mapping_evidence_v1(value: Any) -> dict[str, Any]:
    """Retain exact mapping images without granting active mapping grammar."""
    payload = canonical_json_bytes_v1(value)
    return {
        "format_version": "INCOME_TAX_PRINTED_PRIMARY_ROOT_MAPPING_EVIDENCE_V1",
        "canonical_json": payload.decode("utf-8"),
        "sha256": sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _bind_printed_primary_root_v1(
    candidate: Mapping[str, Any], *, source_page: Mapping[str, Any],
    descriptor: Mapping[str, Any], compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind a printed total by its source role, never by equal coefficients.

    This is deliberately before note/PRIMARY merging and signed-display
    receipts. The final source-control seal still owns document period proof.
    A total which is present but unusable cannot fall through to current tax.
    """
    if candidate.get("status") != READY:
        return canonical_clone_v1(candidate)
    locator = descriptor["locator"]
    section, table = _source_table(
        source_page, section_id=locator["section_id"], table_id=locator["table_id"],
    )
    if (canonical_json_sha256_v1(source_page) != descriptor["original_page_json_sha256"]
            or canonical_json_sha256_v1(table) != descriptor["original_table_json_sha256"]
            or source_page.get("status") != "PRIMARY_FINANCIAL_STATEMENT"
            or section.get("content_kind") != "PRIMARY_STATEMENT"
            or section.get("statement_type") != "INCOME_STATEMENT"):
        raise _error("income-tax printed PRIMARY total source identity drifted")
    roots = [(ordinal, row) for ordinal, row in enumerate(table.get("rows") or [], 1)
             if type(row) is dict
             and _role_for_primary_label(row.get("label_exact")) == "FAMILY_ROOT_TOTAL"]
    # No new printed-total authority is claimed in the absent case. The
    # existing private spec/frontier and final source controls remain required.
    if not roots:
        return canonical_clone_v1(candidate)
    lane = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
    unit = _unit_axis(table, compiled_specs=compiled_specs)
    columns = descriptor["money_column_ordinals"]
    material: dict[str, Any] = {
        "locator": canonical_clone_v1(locator),
        "original_page_json_sha256": descriptor["original_page_json_sha256"],
        "original_table_json_sha256": descriptor["original_table_json_sha256"],
        "printed_total_rows": [{"row_ordinal": ordinal, "source_row": canonical_clone_v1(row)}
                               for ordinal, row in roots],
        "lane_axis": canonical_clone_v1(lane),
        "unit_axis": canonical_clone_v1(unit),
        "primary_unit_corroboration_receipt": canonical_clone_v1(
            descriptor.get("primary_unit_corroboration_receipt")),
        "prior_root_mappings": _printed_primary_root_mapping_evidence_v1([
            item for item in candidate["mappings"] if item.get("role") == "FAMILY_ROOT_TOTAL"]),
        "authority": "SAME_AUTHENTICATED_STATEMENT_TABLE_PRINTED_TOTAL_LABEL_AND_SOURCE_CELLS",
        "amounts_used_as_role_authority": False,
        "source_values_changed": False,
        "final_document_period_source_control_still_required": True,
    }

    def hold(reason: str) -> dict[str, Any]:
        return _unresolved_from_candidate(
            candidate, reason="ALGORITHM_PRINTED_PRIMARY_ROOT_SOURCE_OWNERSHIP_UNPROVEN",
            evidence={**material, "ownership_failure": reason},
        )

    if len(roots) != 1:
        return hold("PRINTED_TOTAL_ROLE_NOT_UNIQUE")
    if (not lane.get("complete") or type(columns) is not list or len(columns) != 2
            or not same_typed_json_v1(lane.get("money_column_ordinals"), columns)):
        return hold("PRINTED_TOTAL_MONEY_AXIS_NOT_COMPLETE")
    corroboration = descriptor.get("primary_unit_corroboration_receipt")
    if not ((unit.get("complete") and unit.get("canonical_unit") == descriptor["canonical_unit"])
            or (_local_money_unit_is_truly_absent(unit) and type(corroboration) is dict
                and corroboration.get("canonical_unit") == descriptor["canonical_unit"])):
        return hold("PRINTED_TOTAL_UNIT_NOT_OWNED")
    root_ordinal, row = roots[0]
    if row.get("row_kind") not in {"ITEM", "TOTAL", "GROUP"}:
        return hold("PRINTED_TOTAL_IS_NOT_AN_OBSERVED_ITEM_OR_TOTAL_ROW")
    source_ordinals = [root_ordinal]
    for mapping in candidate["mappings"]:
        if mapping.get("role") not in {"CURRENT_TAX_PARENT", "DEFERRED_TAX_NET"}:
            continue
        if mapping.get("unit") != descriptor["canonical_unit"]:
            return hold("PRIMARY_COMPONENT_UNIT_DIFFERS")
        for ref in mapping.get("source_refs") or []:
            if (any(not same_typed_json_v1(ref.get("locator", {}).get(key), value)
                    for key, value in locator.items())
                    or not same_typed_json_v1(ref.get("money_column_ordinals"), columns)):
                return hold("PRIMARY_COMPONENT_HAS_DIFFERENT_TABLE_OR_LANE_OWNER")
            ordinal = ref.get("row_ordinal")
            if type(ordinal) is not int or not 1 <= ordinal <= len(table["rows"]):
                raise _error("income-tax printed PRIMARY component row selector drifted")
            actual = table["rows"][ordinal - 1]
            if (not same_typed_json_v1(ref.get("label_exact"), actual.get("label_exact"))
                    or not same_typed_json_v1(ref.get("hierarchy_path_exact"), actual.get("hierarchy_path_exact"))
                    or not same_typed_json_v1(ref.get("row_kind"), actual.get("row_kind"))
                    or ref.get("row_id") != f"r{ordinal}"):
                raise _error("income-tax printed PRIMARY component source citation drifted")
            source_ordinals.append(ordinal)
    lower, upper = min(source_ordinals), max(source_ordinals)
    if any(item.get("row_kind") == "GROUP" for item in table["rows"][lower:upper - 1]
           if type(item) is dict):
        return hold("PRINTED_GROUP_BOUNDARY_BETWEEN_TOTAL_AND_COMPONENT")
    ancestry = _primary_bridge_population_ancestry(
        table, row_ordinals=sorted(set(source_ordinals)), primary_section=section,
    )
    material["same_printed_population_receipt"] = canonical_clone_v1(ancestry)
    if ancestry is None:
        return hold("PRINTED_TOTAL_AND_COMPONENT_POPULATION_NOT_PROVEN")
    if row.get("row_kind") == "GROUP":
        # A GROUP label alone is not an observed total. Retain the existing
        # finite legacy permission only when this actual preceding tax GROUP
        # owns the cited components in the source ancestry proof. Quoted TNDN
        # spellings do not expand that structural GROUP vocabulary.
        component_ordinals = set(source_ordinals) - {root_ordinal}
        if (not component_ordinals or any(ordinal <= root_ordinal for ordinal in component_ordinals)
                or _legacy_primary_role_for_label(row.get("label_exact")) != "FAMILY_ROOT_TOTAL"
                or any(not same_typed_json_v1(
                    table["rows"][ordinal - 1]["hierarchy_path_exact"][:len(row["hierarchy_path_exact"])],
                    row["hierarchy_path_exact"],
                ) or len(table["rows"][ordinal - 1]["hierarchy_path_exact"]) <= len(row["hierarchy_path_exact"])
                       for ordinal in component_ordinals)
                or not any(item["row_ordinal"] == root_ordinal
                           and same_typed_json_v1(item["source_row"], row)
                           for item in ancestry["structural_tax_group_sources"])):
            return hold("PRINTED_TOTAL_GROUP_IS_NOT_A_PROVEN_PRECEDING_TAX_OWNER")
    raw_values = row.get("values_exact")
    if type(raw_values) is not list or any(type(column) is not int or not 1 <= column <= len(raw_values)
                                          for column in columns):
        return hold("PRINTED_TOTAL_SOURCE_MONEY_CELLS_MISSING")
    selected_values = [raw_values[column - 1] for column in columns]
    material["source_values_exact"] = canonical_clone_v1(selected_values)
    try:
        cells = [_source_money(value) for value in selected_values]
    except (TypeError, ValueError):
        return hold("PRINTED_TOTAL_SOURCE_MONEY_CELL_UNPARSEABLE")
    # A blank, colon or conditional punctuation placeholder is retained in
    # evidence; it is not rescued by a current-tax value or an equation.
    if any(cell.get("state") not in {"RAW_SIGNED_INTEGER", "DASH_ZERO"} for cell in cells):
        return hold("PRINTED_TOTAL_SOURCE_MONEY_LANE_NOT_DIRECTLY_OBSERVED")
    source_ref = {
        "hierarchy_path_exact": canonical_clone_v1(row.get("hierarchy_path_exact")),
        "label_exact": row.get("label_exact"), "locator": canonical_clone_v1(locator),
        "money_column_ordinals": canonical_clone_v1(columns), "row_id": f"r{root_ordinal}",
        "row_kind": row.get("row_kind"), "row_ordinal": root_ordinal,
    }
    mapping_material = {
        "report_norm_id": compiled_specs["schema"]["family_root_report_norm_id"],
        "role": "FAMILY_ROOT_TOTAL", "row_id": f"r{root_ordinal}",
        "source_refs": [source_ref], "state": "SOURCE_VISIBLE_PRINTED_PRIMARY_FAMILY_ROOT_TOTAL",
        "unit": descriptor["canonical_unit"], "values": canonical_clone_v1(cells),
    }
    mapping = {**mapping_material, "item_mapping_id": "gjmthfmv1:item:"
               + canonical_json_sha256_v1(mapping_material)}
    output = canonical_clone_v1(candidate)
    output["mappings"] = [item for item in output["mappings"] if item.get("role") != "FAMILY_ROOT_TOTAL"]
    output["mappings"].append(mapping)
    material["bound_root_mapping"] = _printed_primary_root_mapping_evidence_v1(mapping)
    output["closure_receipt"]["income_tax_printed_primary_root_receipt"] = {
        **material, "receipt_id": "gjitfav1:printed-primary-root:" + canonical_json_sha256_v1(material),
    }
    output["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in output.items() if key != "candidate_id"})
    return output


def _evaluate_selected_primary(
    selected: Mapping[str, Any],
    *,
    repaired_pages: Mapping[str, dict[str, Any]],
    repair_receipts: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    descriptor = selected["descriptor"]
    locator = descriptor["locator"]
    source_page = repaired_pages[locator["page_json_version_id"]]
    projected_page = _project_primary_page(source_page, descriptor=descriptor)
    if canonical_json_sha256_v1(projected_page) != descriptor["projected_page_json_sha256"]:
        raise _error("income-tax primary projection output drifted")
    specs = compiled_specs[descriptor["projected_specs_key"]]
    regions = selected["cluster"]["component_regions"]
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=regions,
        page_json_by_version={locator["page_json_version_id"]: projected_page},
        compiled_specs=specs,
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions),
    )
    candidate = _reseal_candidate(
        candidate,
        descriptor=descriptor,
        repair_receipts=repair_receipts,
        strategy="DIRECT_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION",
        compiled_specs=compiled_specs,
    )
    return _bind_printed_primary_root_v1(
        candidate, source_page=source_page, descriptor=descriptor, compiled_specs=compiled_specs,
    )


def _evaluate_supplemental_descriptor(
    descriptor: Mapping[str, Any],
    *,
    repaired_pages: Mapping[str, dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    locator = descriptor["locator"]
    source_page = repaired_pages[locator["page_json_version_id"]]
    projected_page = _project_primary_page(source_page, descriptor=descriptor)
    if canonical_json_sha256_v1(projected_page) != descriptor["projected_page_json_sha256"]:
        raise _error("income-tax supplemental projection output drifted")
    specs = compiled_specs["income_tax_supplemental_specs"]
    if (descriptor.get("projected_specs_key") != "income_tax_supplemental_specs"
            or descriptor.get("projected_semantic_spec_sha256") != _semantic_spec_sha256(specs)):
        raise _error("income-tax supplemental semantic spec replay drifted")
    projected_record = {
        key: canonical_clone_v1(locator[key])
        for key in (
            "document_id",
            "document_ordinal",
            "page_json_version_id",
            "physical_page",
            "selected_page_ordinal",
            "source_logical_name",
            "source_sha256",
        )
    } | {"page_json": projected_page}
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[projected_record], compiled_specs=specs
    )
    if cluster.get("status") != READY or not same_typed_json_v1(
        cluster.get("component_regions"), descriptor["projected_component_regions"]
    ):
        raise _error("income-tax supplemental projection query replay drifted")
    regions = cluster["component_regions"]
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=regions,
        page_json_by_version={locator["page_json_version_id"]: projected_page},
        compiled_specs=specs,
        query_receipt=(
            build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
        ),
    )
    if candidate.get("status") != READY:
        raise _error("income-tax supplemental projection candidate replay drifted")
    candidate = _restore_source_refs(candidate, descriptor=descriptor)
    for mapping in candidate.get("mappings", []):
        refs = mapping.get("source_refs")
        if type(refs) is list and len(refs) == 1:
            mapping["row_id"] = refs[0]["row_id"]
        material = {key: item for key, item in mapping.items() if key != "item_mapping_id"}
        mapping["item_mapping_id"] = "gjmthfmv1:item:" + canonical_json_sha256_v1(material)
    _reseal_equations(candidate)
    material = {key: item for key, item in candidate.items() if key != "candidate_id"}
    candidate["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(material)
    return candidate


def _post_merge_root_closure(
    candidate: Mapping[str, Any], *, comparison_orientations: Mapping[str, int] | None = None,
) -> tuple[dict[str, Any], bool]:
    """Veto complete observed-lane conflicts without imputing a missing operand."""

    from bctc_ai.evaluation.source_observation_lane_math_v1 import (
        SourceObservationLaneMathError,
        observed_source_coefficient_v1,
    )

    roles = ("CURRENT_TAX_PARENT", "DEFERRED_TAX_NET", "FAMILY_ROOT_TOTAL")
    orientations = dict(comparison_orientations or {})
    if any(role not in roles or type(sign) is not int or sign not in {-1, 1}
           for role, sign in orientations.items()):
        raise _error("income-tax root comparison orientation axis is invalid")
    by_role: dict[str, dict[str, Any]] = {}
    economic_values: dict[str, list[int | None]] = {}
    reasons: list[str] = []
    mappings = candidate.get("mappings")
    if type(mappings) is not list:
        reasons.append("POST_MERGE_MAPPING_AXIS_INVALID")
        mappings = []
    for mapping in mappings:
        if type(mapping) is not dict:
            reasons.append("POST_MERGE_MAPPING_AXIS_INVALID")
            continue
        role = mapping.get("role")
        if role not in roles:
            continue
        if role in by_role:
            reasons.append("POST_MERGE_ROOT_ROLE_AXIS_NOT_UNIQUE:" + role)
            continue
        by_role[role] = canonical_clone_v1(mapping)
        power = {"MILLION_VND": 6, "VND": 0}.get(mapping.get("unit"))
        cells = mapping.get("values")
        if power is None or type(cells) is not list or len(cells) != 2:
            reasons.append("POST_MERGE_ROOT_VALUE_AXIS_INVALID:" + role)
            continue
        try:
            coefficients = [observed_source_coefficient_v1(cell) for cell in cells]
        except SourceObservationLaneMathError:
            reasons.append("POST_MERGE_ROOT_SOURCE_CELL_INVALID:" + role)
            continue
        economic_values[role] = [
            None if value is None else value * (10**power) for value in coefficients
        ]
    lanes = []
    for lane in range(2):
        operands = {
            role: economic_values[role][lane] if role in economic_values else None
            for role in roles
        }
        complete = all(value is not None for value in operands.values())
        comparison_operands = {
            role: None if value is None else value * orientations.get(role, 1)
            for role, value in operands.items()
        }
        expected = (
            comparison_operands["CURRENT_TAX_PARENT"] + comparison_operands["DEFERRED_TAX_NET"]
            if complete else None
        )
        observed = comparison_operands["FAMILY_ROOT_TOTAL"]
        residual = observed - expected if complete else None
        lanes.append({
            "component_sum_vnd": expected,
            "lane_ordinal": lane,
            "operands_vnd": operands,
            "residual_vnd": residual,
            "status": (
                "EXACT_OBSERVED_SOURCE_LANE" if complete and residual == 0
                else "SOURCE_LANE_EQUATION_CONFLICT" if complete
                else "INCOMPLETE_DUE_TO_UNOBSERVED_SOURCE_LANE"
            ),
        })
        if orientations:
            lanes[-1]["comparison_operands_vnd"] = comparison_operands
    mismatch = bool(reasons) or any(
        lane["status"] == "SOURCE_LANE_EQUATION_CONFLICT" for lane in lanes
    )
    material = {
        "economic_unit": "VND",
        "lane_receipts": lanes,
        "mappings": [by_role[role] for role in roles if role in by_role],
        "missing_roles": [role for role in roles if role not in by_role],
        "reasons": sorted(set(reasons)),
        "rule": "POST_MERGE_OBSERVED_CURRENT_PLUS_DEFERRED_EQUALS_SOURCE_ROOT_NO_IMPUTATION",
        "status": (
            "MISMATCH" if mismatch else "EXACT_ALL_OBSERVED_LANES"
            if all(lane["status"] == "EXACT_OBSERVED_SOURCE_LANE" for lane in lanes)
            else "INCOMPLETE_SOURCE_LANES_PRESERVED"
        ),
    }
    if orientations:
        material["source_presentation_comparison_orientations"] = orientations
        material["source_mapping_values_unchanged"] = True
    return ({
        **material,
        "receipt_id": "gjitfav1:post-merge-root-closure:" + canonical_json_sha256_v1(material),
    }, mismatch)


def _mapping_economic_values(mapping: Mapping[str, Any]) -> tuple[int | None, ...] | None:
    power = {"MILLION_VND": 6, "VND": 0}.get(mapping.get("unit"))
    values = mapping.get("values")
    if power is None or type(values) is not list:
        return None
    output = []
    for item in values:
        coefficient = item.get("coefficient") if type(item) is dict else None
        if coefficient is not None and type(coefficient) is not int:
            return None
        output.append(None if coefficient is None else coefficient * (10**power))
    return tuple(output)


def _supplemental_mappings_compatible(
    left: Mapping[str, Any], right: Mapping[str, Any]
) -> bool:
    return _cross_source_mappings_compatible(left, right, allow_sign_inversion=False)


def _select_supplemental_role_mappings(
    supplemental: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]],
) -> tuple[
    dict[str, tuple[dict[str, Any], Mapping[str, Any]]], list[dict[str, Any]], str | None
]:
    """Select evidence-dominant roles, then a unique explicit VND presentation."""

    grouped: dict[str, list[tuple[Mapping[str, Any], Mapping[str, Any]]]] = {}
    for descriptor, candidate in supplemental:
        if candidate.get("status") != READY:
            raise _error("income-tax supplemental source candidate is not ready")
        for mapping in candidate["mappings"]:
            grouped.setdefault(mapping["role"], []).append((mapping, descriptor))
    selected = {}
    suppressed = []
    for role, occurrences in grouped.items():
        for ordinal, (mapping, _descriptor) in enumerate(occurrences):
            for other, _other_descriptor in occurrences[ordinal + 1:]:
                if not _supplemental_mappings_compatible(mapping, other):
                    return {}, [], "CONFLICTING_DIRECT_SUPPLEMENTAL_INCOME_TAX_PRESENTATIONS"
                left_lanes = _observed_mapping_lane_axis(mapping)
                right_lanes = _observed_mapping_lane_axis(other)
                if not (left_lanes.issubset(right_lanes) or right_lanes.issubset(left_lanes)):
                    return {}, [], "INCOMPARABLE_PARTIAL_DIRECT_SUPPLEMENTAL_PRESENTATIONS"
        if sum(occurrence[0].get("unit") == "VND" for occurrence in occurrences) > 1:
            return {}, [], "MULTIPLE_HIGH_PRECISION_DIRECT_SUPPLEMENTAL_PRESENTATIONS"
        dominant = [
            occurrence
            for occurrence in occurrences
            if all(
                _observed_mapping_lane_axis(occurrence[0]).issuperset(
                    _observed_mapping_lane_axis(other[0])
                )
                for other in occurrences
            )
        ]
        vnd = [occurrence for occurrence in dominant if occurrence[0].get("unit") == "VND"]
        pool = vnd or dominant
        # The locator order keeps the existing equivalent million-unit control
        # deterministic; it is not used to choose between economic interpretations.
        chosen = min(
            pool,
            key=lambda occurrence: (
                occurrence[1].get("locator", {}).get("selected_page_ordinal", 0),
                occurrence[1].get("locator", {}).get("section_id", ""),
                occurrence[1].get("locator", {}).get("table_id", ""),
                canonical_json_sha256_v1([occurrence[0], occurrence[1]]),
            ),
        )
        selected[role] = (canonical_clone_v1(chosen[0]), chosen[1])
        suppressed.extend(
            canonical_clone_v1(occurrence[0])
            for occurrence in occurrences
            if occurrence is not chosen
        )
    return selected, sorted(suppressed, key=canonical_json_sha256_v1), None


def _cross_source_mappings_compatible(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    *,
    allow_sign_inversion: bool,
) -> bool:
    return bool(
        _cross_source_mapping_signs(
            left, right, allow_sign_inversion=allow_sign_inversion
        )
    )


def _cross_source_mapping_signs(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    *,
    allow_sign_inversion: bool,
) -> frozenset[int]:
    left_values = _mapping_economic_values(left)
    right_values = _mapping_economic_values(right)
    if left_values is None or right_values is None or len(left_values) != len(right_values):
        return frozenset()
    tolerance = (
        500_000
        if {left.get("unit"), right.get("unit")} == {"MILLION_VND", "VND"}
        else 0
    )
    paired = [
        (left_value, right_value)
        for left_value, right_value in zip(left_values, right_values, strict=True)
        if left_value is not None and right_value is not None
    ]
    if not paired:
        return frozenset()
    signs = (1, -1) if allow_sign_inversion else (1,)
    return frozenset(
        sign
        for sign in signs
        if all(
            abs(left_value - sign * right_value) <= tolerance
            for left_value, right_value in paired
        )
    )


def _observed_mapping_lane_axis(mapping: Mapping[str, Any]) -> frozenset[int]:
    values = mapping.get("values")
    if type(values) is not list:
        return frozenset()
    return frozenset(
        ordinal
        for ordinal, item in enumerate(values)
        if type(item) is dict and item.get("coefficient") is not None
    )


def _cross_source_orientation(
    pairs: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]]
) -> int | None:
    allowed = {1, -1}
    for left, right in pairs:
        left_lanes = _observed_mapping_lane_axis(left)
        right_lanes = _observed_mapping_lane_axis(right)
        if not (left_lanes.issubset(right_lanes) or right_lanes.issubset(left_lanes)):
            return None
        allowed.intersection_update(
            _cross_source_mapping_signs(left, right, allow_sign_inversion=True)
        )
        if not allowed:
            return None
    if 1 in allowed:
        return 1
    return -1 if -1 in allowed else None


def _mapping_is_direct_source_observation(mapping: Mapping[str, Any]) -> bool:
    state = mapping.get("state")
    values = mapping.get("values")
    return bool(
        type(state) is str
        and "SOURCE_VISIBLE" in state
        and not state.startswith("DERIVED_")
        and type(values) is list
        and any(type(item) is dict and item.get("source_text") is not None for item in values)
    )


def _unresolved_from_candidate(
    candidate: Mapping[str, Any],
    *,
    reason: str,
    evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    output = canonical_clone_v1(candidate)
    output["mappings"] = []
    output["reasons"] = [reason]
    output["status"] = UNRESOLVED
    if evidence is not None:
        evidence_material = {
            "evidence": canonical_clone_v1(evidence),
            "reason": reason,
        }
        output["closure_receipt"]["income_tax_unresolved_evidence_receipt"] = {
            **evidence_material,
            "receipt_id": "gjitfav1:unresolved:"
            + canonical_json_sha256_v1(evidence_material),
        }
    material = {key: item for key, item in output.items() if key != "candidate_id"}
    output["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(material)
    return output


def _supplemental_merge_evidence(
    supplemental: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]],
    primary_candidate: Mapping[str, Any],
    *,
    descriptor: Mapping[str, Any],
    repair_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "primary_candidate_id": primary_candidate["candidate_id"],
        "primary_closure_receipt": canonical_clone_v1(primary_candidate["closure_receipt"]),
        "primary_projection_receipt": canonical_clone_v1(descriptor),
        "source_repair_receipts": canonical_clone_v1(list(repair_receipts)),
        "supplemental_candidates": [
            {
                "candidate_id": candidate["candidate_id"],
                "closure_receipt": canonical_clone_v1(candidate["closure_receipt"]),
                "descriptor": canonical_clone_v1(supplement_descriptor),
                "mappings": canonical_clone_v1(candidate["mappings"]),
            }
            for supplement_descriptor, candidate in supplemental
        ],
    }


def _merge_supplemental_and_primary_candidates(
    supplemental: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]],
    primary_candidate: Mapping[str, Any],
    *,
    descriptor: Mapping[str, Any],
    repair_receipts: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    if primary_candidate.get("reasons") == ["ALGORITHM_PRINTED_PRIMARY_ROOT_SOURCE_OWNERSHIP_UNPROVEN"]:
        return canonical_clone_v1(primary_candidate)
    supplemental_by_role, suppressed_supplemental, conflict = (
        _select_supplemental_role_mappings(supplemental)
    )
    if conflict is not None:
        return _unresolved_from_candidate(
            primary_candidate,
            reason=conflict,
            evidence=_supplemental_merge_evidence(
                supplemental,
                primary_candidate,
                descriptor=descriptor,
                repair_receipts=repair_receipts,
            ),
        )

    primary_by_role = {item["role"]: item for item in primary_candidate["mappings"]}
    if len(primary_by_role) != len(primary_candidate["mappings"]):
        raise _error("income-tax primary source role axis is duplicate")
    overlap_pairs = [
        (item[0], primary_by_role[role])
        for role, item in supplemental_by_role.items()
        if role in primary_by_role
    ]
    cross_source_orientation = _cross_source_orientation(overlap_pairs)
    if overlap_pairs and cross_source_orientation is None:
        return _unresolved_from_candidate(
            primary_candidate,
            reason="CONFLICTING_DIRECT_SUPPLEMENTAL_AND_PRIMARY_INCOME_TAX_PRESENTATIONS",
            evidence=_supplemental_merge_evidence(
                supplemental,
                primary_candidate,
                descriptor=descriptor,
                repair_receipts=repair_receipts,
            ),
        )
    suppress_entire_supplemental_axis = cross_source_orientation == -1
    merged_by_role = (
        {}
        if suppress_entire_supplemental_axis
        else {
            role: canonical_clone_v1(item[0])
            for role, item in supplemental_by_role.items()
        }
    )
    suppressed_primary = []
    suppressed_cross_source_supplemental = (
        [canonical_clone_v1(item[0]) for item in supplemental_by_role.values()]
        if suppress_entire_supplemental_axis
        else []
    )
    for role, mapping in primary_by_role.items():
        if role == "FAMILY_ROOT_TOTAL" or role not in merged_by_role:
            merged_by_role[role] = canonical_clone_v1(mapping)
        else:
            supplemental_lanes = _observed_mapping_lane_axis(merged_by_role[role])
            primary_lanes = _observed_mapping_lane_axis(mapping)
            if primary_lanes > supplemental_lanes:
                suppressed_cross_source_supplemental.append(
                    canonical_clone_v1(merged_by_role[role])
                )
                merged_by_role[role] = canonical_clone_v1(mapping)
            else:
                suppressed_primary.append(canonical_clone_v1(mapping))
    role_order = [item["role"] for item in compiled_specs["topology"]["children"]]
    role_order.append("FAMILY_ROOT_TOTAL")
    order = {role: ordinal for ordinal, role in enumerate(role_order)}
    merged = canonical_clone_v1(primary_candidate)
    merged["mappings"] = sorted(
        merged_by_role.values(),
        key=lambda item: (order.get(item["role"], len(order)), item["role"]),
    )
    supplemental_equations = []
    if not suppress_entire_supplemental_axis:
        for _supplement_descriptor, candidate in supplemental:
            supplemental_equations.extend(
                canonical_clone_v1(candidate.get("closure_receipt", {}).get("equations", []))
            )
    merged["closure_receipt"]["equations"] = [
        *canonical_clone_v1(merged["closure_receipt"].get("equations", [])),
        *supplemental_equations,
    ]
    proof = {
        "primary_candidate_id": primary_candidate["candidate_id"],
        "primary_closure_receipt": canonical_clone_v1(primary_candidate["closure_receipt"]),
        "rule": (
            "SUPPLEMENTAL_DIRECT_NOTE_ROLES_PRESERVED_PRIMARY_DIRECT_ROOT_AND_ONLY_"
            "SUPPLEMENT_ABSENT_ROLES_ADDED_EQUIVALENT_DUPLICATES_RETAINED_AS_CONTROLS"
        ),
        "supplemental_candidates": [
            {
                "candidate_id": candidate["candidate_id"],
                "closure_receipt": canonical_clone_v1(candidate["closure_receipt"]),
                "descriptor_id": supplement_descriptor["descriptor_id"],
            }
            for supplement_descriptor, candidate in supplemental
        ],
        "supplemental_projection_receipts": canonical_clone_v1(
            [item[0] for item in supplemental]
        ),
        "cross_source_sign_orientation": cross_source_orientation or 1,
        "suppressed_cross_source_supplemental_mappings": (
            suppressed_cross_source_supplemental
        ),
        "suppressed_duplicate_primary_mappings": suppressed_primary,
        "suppressed_equivalent_supplemental_mappings": suppressed_supplemental,
    }
    proof["post_merge_root_closure"], mismatch = _post_merge_root_closure(merged)
    if mismatch:
        return _unresolved_from_candidate(
            merged, reason="POST_MERGE_INCOME_TAX_ROOT_EQUATION_CONFLICT", evidence=proof
        )
    return _reseal_candidate(
        merged,
        descriptor=descriptor,
        repair_receipts=repair_receipts,
        strategy="DIRECT_SUPPLEMENTAL_NOTE_PLUS_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION",
        compiled_specs=compiled_specs,
        restore_primary_source_refs=False,
        primary_candidate_proof=proof,
    )


def _printed_population_qualifiers(surfaces: Sequence[Any]) -> list[str]:
    """Conservative veto of explicit population words, never infer absent scope."""
    aliases = {
        "CONSOLIDATED": "hop nhat", "SEPARATE": "rieng",
        "PARENT_ENTITY": "ngan hang me", "SUBSIDIARY_ENTITY": "cong ty con",
    }
    return sorted({
        role for surface in surfaces if type(surface) is str
        for role, alias in aliases.items()
        if " " + alias + " " in " " + _normalized(surface) + " "
    })


def _owned_statement_scope_narratives(section: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Only a direct recognition statement owns scope; arbitrary prose cannot."""
    if section.get("content_kind") != "FINANCIAL_NOTE" or len(section.get("tables") or []) != 1:
        return []
    return [{"narrative_ordinal": ordinal, "source_exact": narrative,
             "source_sha256": canonical_json_sha256_v1(narrative),
             "rule": "OWNED_NOTE_DIRECT_RECOGNITION_IN_INCOME_STATEMENT"}
            for ordinal, narrative in enumerate(section.get("narratives_exact") or [], start=1)
            if type(narrative) is str
            and re.fullmatch(
                r"(?:[a-z] )?ghi nhan trong bao cao ket qua hoat dong (?:hop nhat|rieng)(?: giua nien do)?",
                _normalized(narrative),
            ) is not None]


def _document_report_scope_receipt(
    page_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Bind every typed statement caption, not a majority or filename guess."""
    caption_aliases = {
        "INCOME_STATEMENT": ("bao cao ket qua hoat dong", "bao cao ket qua kinh doanh"),
        "CASH_FLOW": ("bao cao luu chuyen tien te",),
        "BALANCE_SHEET": ("bang can doi ke toan", "bao cao tinh hinh tai chinh"),
    }
    sources = []
    identities = {(record["document_id"], record["document_ordinal"], record["source_sha256"])
                  for record in page_records}
    for record in page_records:
        page = record["page_json"]
        if page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            continue
        for section_ordinal, section in enumerate(page.get("sections") or [], start=1):
            statement_type = section.get("statement_type")
            if section.get("content_kind") != "PRIMARY_STATEMENT" or statement_type not in caption_aliases:
                continue
            for table_ordinal, table in enumerate(section.get("tables") or [], start=1):
                captions = [section.get("title_exact"), table.get("title_exact")]
                eligible = [caption for caption in captions if type(caption) is str
                            and any(alias in _normalized(caption) for alias in caption_aliases[statement_type])]
                # A bare table caption such as RIÊNG still vetoes a qualified
                # section caption; eligibility is not permission to drop it.
                qualifiers = _printed_population_qualifiers(captions)
                sources.append({
                    "locator": _record_locator(record, section_id=f"s{section_ordinal}", table_id=f"t{table_ordinal}"),
                    "statement_type": statement_type,
                    "captions_exact": canonical_clone_v1(captions),
                    "eligible_captions_exact": eligible,
                    "qualifiers": qualifiers,
                    "ambiguous_scope_caption": _ambiguous_report_scope_surface(captions),
                    "original_page_json_sha256": canonical_json_sha256_v1(page),
                    "original_table_json_sha256": canonical_json_sha256_v1(table),
                })
    sources.sort(key=lambda item: (item["locator"]["selected_page_ordinal"],
                                  int(item["locator"]["section_id"][1:]), int(item["locator"]["table_id"][1:])))
    scopes = {qualifier for item in sources for qualifier in item["qualifiers"]
              if qualifier in {"CONSOLIDATED", "SEPARATE"}}
    qualified_types = {item["statement_type"] for item in sources
                       if item["eligible_captions_exact"] and len(item["qualifiers"]) == 1
                       and item["qualifiers"][0] in scopes}
    entity_overrides = any(set(item["qualifiers"]) & {"PARENT_ENTITY", "SUBSIDIARY_ENTITY"}
                           for item in sources)
    ambiguity = any(item["ambiguous_scope_caption"] for item in sources)
    scope = next(iter(scopes)) if len(identities) == 1 and len(scopes) == 1 and len(qualified_types) >= 2 and not entity_overrides and not ambiguity else None
    material = {
        "report_scope": scope, "all_printed_report_scopes": sorted(scopes),
        "qualified_statement_types": sorted(qualified_types), "sources": sources,
        "document_identity_unique": len(identities) == 1,
        "entity_override_present": entity_overrides,
        "ambiguous_scope_caption_present": ambiguity,
        "rule": "TWO_DISTINCT_TYPED_STATEMENT_TYPES_ONE_PRINTED_REPORT_SCOPE_NO_CONFLICT_NO_AMOUNT_INFERENCE",
    }
    return {**material, "receipt_id": "gjitfav1:document-report-scope:" + canonical_json_sha256_v1(material)}


def _note_report_scope_receipt(
    section: Mapping[str, Any], table: Mapping[str, Any], *,
    source_paths: Sequence[Sequence[Any]], document_scope: Mapping[str, Any],
) -> dict[str, Any]:
    narratives = _owned_statement_scope_narratives(section)
    surfaces = [section.get("title_exact"), table.get("title_exact"),
                *[item["source_exact"] for item in narratives],
                *[value for path in source_paths for value in path]]
    qualifiers = _printed_population_qualifiers(surfaces)
    local_scopes = sorted(set(qualifiers) & {"CONSOLIDATED", "SEPARATE"})
    local_entities = sorted(set(qualifiers) & {"PARENT_ENTITY", "SUBSIDIARY_ENTITY"})
    inherited = not qualifiers and document_scope.get("report_scope") is not None
    scope = (local_scopes[0] if len(local_scopes) == 1 and not local_entities
             else document_scope["report_scope"] if inherited else None)
    conflict = (len(local_scopes) > 1 or _ambiguous_report_scope_surface(surfaces)
                or len(document_scope["all_printed_report_scopes"]) > 1
                or not document_scope["document_identity_unique"]
                or document_scope["ambiguous_scope_caption_present"]
                or (scope is not None and document_scope.get("report_scope") is not None
                    and scope != document_scope["report_scope"]))
    material = {
        "report_scope": scope, "local_qualifiers": qualifiers,
        "local_entity_qualifiers": local_entities, "conflict": conflict,
        "origin": "INHERITED_UNIQUE_DOCUMENT_REPORT_SCOPE" if inherited else "LOCAL_PRINTED_SOURCE",
        "source_surfaces_exact": canonical_clone_v1(surfaces),
        "owned_statement_scope_narratives": narratives,
        "document_report_scope_receipt_id": document_scope["receipt_id"],
        "rule": "LOCAL_NOTE_STATEMENT_SCOPE_PRECEDENCE_WITH_ENTITY_OVERRIDE_VETO",
    }
    return {**material, "receipt_id": "gjitfav1:note-report-scope:" + canonical_json_sha256_v1(material)}


def _ambiguous_report_scope_surface(surfaces: Sequence[Any]) -> bool:
    return any(_printed_population_qualifiers([surface])
               and any(token in _normalized(surface).split() for token in ("khong", "not"))
               for surface in surfaces if type(surface) is str)


def _printed_duration_lengths(
    table: Mapping[str, Any], ordinals: Sequence[int], *, section: Mapping[str, Any],
) -> list[list[int]]:
    """Retain printed month lengths; an endpoint alone does not define duration."""
    written = {"mot": 1, "hai": 2, "ba": 3, "bon": 4, "nam": 5, "sau": 6,
               "bay": 7, "tam": 8, "chin": 9, "muoi": 10, "muoi mot": 11, "muoi hai": 12,
               "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
               "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}
    output = []
    for ordinal in ordinals:
        path = table["columns"][ordinal - 1].get("header_path_exact") or []
        surfaces = [*path, table.get("title_exact")]
        # Single-table statement captions are source-owned context.  A
        # multi-table section cannot silently lend duration to another table.
        if len(section.get("tables") or []) == 1:
            surfaces.append(section.get("title_exact"))
        lengths = set()
        for value in surfaces:
            surface = _normalized(value)
            lengths.update(int(number) for number in re.findall(r"\b(\d+) (?:thang|months?)\b(?! \d)", surface))
            for phrase in re.findall(
                r"\b((?:(?:mot|hai|ba|bon|tu|nam|sau|bay|tam|chin|muoi|tram|nghin|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand) )+)(?:thang|months?)\b",
                surface,
            ):
                lengths.add(written.get(phrase.strip(), -1))
        output.append(sorted(lengths))
    return output


def _source_duration_correspondence_complete(
    note_lane: Mapping[str, Any], primary_lane: Mapping[str, Any], *,
    note_table: Mapping[str, Any], primary_table: Mapping[str, Any],
    note_lengths: Sequence[Sequence[int]], primary_lengths: Sequence[Sequence[int]],
) -> bool:
    keys = note_lane.get("source_lane_keys")
    if (not note_lane.get("complete") or not primary_lane.get("complete")
            or not same_typed_json_v1(keys, primary_lane.get("source_lane_keys"))
            or len(keys or []) != 2 or len(note_lengths) != 2 or len(primary_lengths) != 2
            or any(len(lengths) > 1 or any(length < 1 or length > 12 for length in lengths)
                   for lengths in [*note_lengths, *primary_lengths])):
        return False
    for index, key in enumerate(keys):
        if key[0] == "DURATION_DATE_RANGE":
            for stated_lengths in (note_lengths[index], primary_lengths[index]):
                if not stated_lengths:
                    continue
                try:
                    start, end = date.fromisoformat(key[1]), date.fromisoformat(key[2])
                    end_exclusive = end + timedelta(days=1)
                except (ValueError, TypeError, IndexError, OverflowError):
                    return False
                printed_months = stated_lengths[0]
                if (start.day != end_exclusive.day or start > end
                        or (end_exclusive.year - start.year) * 12 + end_exclusive.month - start.month != printed_months):
                    return False
            continue
        if note_lengths[index] != primary_lengths[index]:
            return False
        if key[0] == "DURATION_END_DATE":
            if len(note_lengths[index]) != 1:
                return False
            continue
        if key[0] in {"BARE_YEAR", "DURATION_BARE_YEAR"}:
            # Printed annual years are not an authority to annualize a
            # year-to-date header whose actual endpoint remains unspecified.
            for lane, table in ((note_lane, note_table), (primary_lane, primary_table)):
                path = table["columns"][lane["money_column_ordinals"][index] - 1].get("header_path_exact") or []
                if any("luy ke" in _normalized(value) or "year to date" in _normalized(value)
                       or "quarter" in _normalized(value)
                       or re.search(r"\bquy (?:i|ii|iii|iv|1|2|3|4)\b", _normalized(value))
                       for value in [*path, table.get("title_exact")]):
                    return False
            if note_lengths[index] not in ([], [12]):
                return False
            continue
        return False
    return True


def _annual_source_context_ambiguous(section: Mapping[str, Any], table: Mapping[str, Any], lane: Mapping[str, Any]) -> bool:
    if not any(key[0] in {"BARE_YEAR", "DURATION_BARE_YEAR"} for key in lane.get("source_lane_keys") or []):
        return False
    surfaces = [section.get("title_exact"), table.get("title_exact"),
                *(value for ordinal in lane.get("money_column_ordinals") or [] for value in table["columns"][ordinal - 1]["header_path_exact"])]
    return any("luy ke" in _normalized(value) or "year to date" in _normalized(value) or "quarter" in _normalized(value)
               or re.search(r"\bquy (?:i|ii|iii|iv|1|2|3|4)\b", _normalized(value)) for value in surfaces)


def _owned_same_day_period_constraint(
    section: Mapping[str, Any], *, source_kind: str, source_exact: Any,
) -> dict[str, Any] | None:
    """Bind 'same day' only to the date in one complete printed NOTE caption.

    No search across titles/narratives, company dates or other source tables.
    A recognized but malformed assertion is a veto, not a fallback shortcut.
    """
    # Historical/signing prose keeps the existing start-anchored narrative
    # semantics below; this caption-only route cannot make it a veto.
    if source_kind == "OWNED_NARRATIVE":
        return None
    normalized = _normalized(source_exact)
    if not re.search(r"\bket thuc cung ngay\b", normalized):
        return None
    constraint = {"source_kind": source_kind, "source_exact": source_exact, "supported": False}
    if source_kind not in {"SECTION_TITLE", "TABLE_TITLE"} or section.get("content_kind") != "FINANCIAL_NOTE":
        return constraint
    source_lines = re.split(r"\r\n|\r|\n|\\n", source_exact)
    lines = [line for line in source_lines if line.strip()]
    printed = source_exact.replace("\\n", "\n")
    def reviewed_character(character: str) -> bool:
        if character.isspace() or character in ".,():;/-":
            return True
        folded = unicodedata.normalize("NFD", character).replace("\u0111", "d").replace("\u0110", "D")
        return all((part.isascii() and part.isalnum()) or part in "\u0300\u0301\u0302\u0303\u0306\u0309\u031b\u0323" for part in folded)

    depth = 0
    for character in printed:
        if character == "(":
            depth += 1
            if depth > 1:
                return constraint
        elif character == ")":
            depth -= 1
            if depth < 0:
                return constraint
    if (depth or any(not reviewed_character(character) for character in printed)
            or any(not _normalized(line) for line in lines)
            or any(_normalized(value) != "tiep theo" for value in re.findall(r"\(([^()]*)\)", printed))):
        # Normalization cannot erase an unreviewed footnote/qualifier marker,
        # either on the report clause or on the allowed trailing headings.
        return constraint
    caption_lines = list(lines)
    furniture = []
    # Only the reviewed pair of fiscal-obligation/tax headings can follow the
    # complete report caption.  The printed outline numbers are structural,
    # not a bank/document/note-number routing key.
    if len(lines) >= 3:
        parent = re.fullmatch(r"(?P<ordinal>\d+)\.?\s+(?P<title>.+)", lines[-2].strip())
        child = re.fullmatch(r"(?P<ordinal>\d+\.\d+)\.?\s+(?P<title>.+)", lines[-1].strip())
        if (parent is not None and child is not None and child["ordinal"].split(".")[0] == parent["ordinal"]
                and re.fullmatch(r"tinh hinh thuc hien nghia vu voi ngan sach nha nuoc(?: tiep theo)?", _normalized(parent["title"]))
                and re.fullmatch(r"thue thu nhap doanh nghiep(?: tiep theo)?", _normalized(child["title"]))):
            furniture = [{"source_exact": lines[-2], "outline_ordinal_exact": parent["ordinal"]},
                         {"source_exact": lines[-1], "outline_ordinal_exact": child["ordinal"]}]
            caption_lines = lines[:-2]
    months_pattern = r"\d+|mot|hai|ba|bon|nam|sau|bay|tam|chin|muoi|muoi mot|muoi hai"
    pattern = (
        r"thuyet minh bao cao tai chinh (?P<scope>rieng|hop nhat)(?P<interim> giua nien do)?(?: tiep theo)? "
        r"(?P<clause>vao ngay (?P<day>\d{1,2}) thang (?P<month>\d{1,2}) nam (?P<year>\d{4}) va cho "
        r"(?:(?P<annual>nam tai chinh)|ky ke toan (?P<months>" + months_pattern + r") thang) ket thuc cung ngay)"
    )
    matched = re.fullmatch(pattern, _normalized(" ".join(caption_lines)))
    if matched is None:
        return constraint
    annual = matched["annual"] is not None
    if annual == (matched["interim"] is not None):
        return constraint
    try:
        end = date(int(matched["year"]), int(matched["month"]), int(matched["day"]))
    except ValueError:
        return constraint
    months_by_word = {"mot": 1, "hai": 2, "ba": 3, "bon": 4, "nam": 5, "sau": 6,
                      "bay": 7, "tam": 8, "chin": 9, "muoi": 10, "muoi mot": 11, "muoi hai": 12}
    months = 12 if annual else int(matched["months"]) if matched["months"].isdigit() else months_by_word[matched["months"]]
    return {**constraint, "supported": 1 <= months <= 12, "printed_end_date": end.isoformat(),
            "printed_months": months, "annual_assertion": annual,
            "same_day_reference_evidence": {
                "binding_origin": "SAME_COMPLETE_SOURCE_CAPTION_EXPLICIT_DATE_ANTECEDENT",
                "source_lines_exact": source_lines, "caption_lines_exact": caption_lines,
                "date_reference_clause_normalized": matched["clause"],
                "antecedent_end_date": end.isoformat(), "printed_report_scope": matched["scope"],
                "recognized_trailing_furniture": furniture,
                "rule": "WHOLE_REVIEWED_NOTE_CAPTION_ONE_PRINTED_DATE_NO_DISCARDED_REMAINDER_OR_CROSS_SURFACE_BORROWING",
            }}


def _owned_absolute_flow_header_constraint(section: Mapping[str, Any], table: Mapping[str, Any]) -> dict[str, Any] | None:
    """Read both complete printed duration headers, without borrowing a caption.

    This finite source-owned route supplies no unit, scope or value permission.
    In particular, an endpoint alone, a quarter/YTD axis or a partly recognized
    header is not a complete duration assertion.
    """
    if (section.get("content_kind") != "PRIMARY_STATEMENT"
            or section.get("statement_type") not in {"INCOME_STATEMENT", "CASH_FLOW"}):
        return None
    columns = table.get("columns") or []
    money = [ordinal for ordinal, column in enumerate(columns, 1) if column.get("value_kind") == "MONEY"]
    if len(money) != 2 or any(column.get("value_kind") not in {"TEXT", "MONEY"} for column in columns):
        return None
    pattern = (r"ky (?P<months>3|6|9|12) thang ket thuc ngay "
               r"(?P<day>\d{1,2})\.(?P<month>\d{1,2})\.(?P<year>\d{4})"
               r"(?: (?P<unit>trieu dong|trieu vnd|vnd|dong))?")
    headers = []
    for ordinal in money:
        path = columns[ordinal - 1].get("header_path_exact")
        if type(path) is not list or not path or any(type(value) is not str or not value.strip() for value in path):
            return None
        raw = " ".join(path)
        printed = _recognition_printed_text(raw)
        match = re.fullmatch(pattern, printed) if printed is not None else None
        if match is None:
            return None
        try:
            end = date(int(match["year"]), int(match["month"]), int(match["day"]))
            months = int(match["months"])
            if end.month != months or (end + timedelta(days=1)).day != 1:
                return None
        except (ValueError, OverflowError):
            return None
        headers.append({"column_ordinal": ordinal, "source_path_exact": canonical_clone_v1(path),
                        "source_exact": raw, "source_sha256": sha256(raw.encode("utf-8")).hexdigest(),
                        "printed_months": months, "printed_end_date": end.isoformat(),
                        "parsed_unit_furniture": match["unit"]})
    current, comparative = headers
    if (current["printed_months"] != comparative["printed_months"]
            or current["printed_end_date"] <= comparative["printed_end_date"]):
        return None
    material = {"format_version": "F39_EXACT_DATED_DURATION_MONEY_HEADER_PAIR_V1",
                "statement_type": section["statement_type"], "money_column_ordinals": money,
                "header_paths_exact": [item["source_path_exact"] for item in headers], "headers": headers,
                "comparative_end_date": comparative["printed_end_date"],
                "comparative_year_origin": "EXPLICIT_PRINTED_HEADER", "amounts_used_as_authority": False,
                "source_period_keys_modified": False,
                "rule": "TWO_WHOLE_DOTTED_DATED_DURATION_HEADERS_SAME_YTD_LENGTH_EXPLICIT_ORDERED_YEARS_NO_CAPTION_BORROWING"}
    evidence = {**material, "receipt_id": "gjitfav1:owned-absolute-flow-header-pair:" + canonical_json_sha256_v1(material)}
    return {"source_kind": "OWNED_PRIMARY_FLOW_HEADER_PAIR", "source_exact": current["source_exact"],
            "supported": True, "printed_months": current["printed_months"],
            "printed_end_date": current["printed_end_date"], "annual_assertion": current["printed_months"] == 12,
            "source_header_pair_evidence": evidence}


def _owned_flow_date_range_caption_constraint(
    section: Mapping[str, Any], *, source_kind: str, source_exact: Any,
) -> dict[str, Any] | None:
    """Read a complete printed interim range, never join separate surfaces.

    Recognition is deliberately broader than permission: a malformed range is
    an assertion to retain and veto, not missing context for header fallback.
    This supplies current duration only, not comparative year, unit or scope.
    """
    if source_kind not in {"SECTION_TITLE", "TABLE_TITLE"} or type(source_exact) is not str:
        return None
    layout = source_exact.replace("\\n", "\n")
    relevant = _normalized(layout)
    if not re.search(r"\b(?:tu ngay|den ngay|from)\b", relevant):
        return None
    printed = _recognition_printed_text(layout)
    title = {"INCOME_STATEMENT": "ket qua hoat dong", "CASH_FLOW": "luu chuyen tien te"}.get(section.get("statement_type"))
    pattern = (
        r"bao cao " + (title or "UNSUPPORTED") + r"(?: (?P<scope>rieng|hop nhat))? giua nien do"
        r"(?: (?P<before>\(tiep theo\)))? cho giai doan "
        r"tu ngay (?P<sd>[0-9]{1,2})/(?P<sm>[0-9]{1,2})/(?P<sy>[0-9]{4}) "
        r"den ngay (?P<ed>[0-9]{1,2})/(?P<em>[0-9]{1,2})/(?P<ey>[0-9]{4})"
        r"(?: (?P<after>\(tiep theo\)))?"
        r"(?: \(phuong phap (?P<method>truc tiep|gian tiep)\))?"
    )
    match = re.fullmatch(pattern, printed) if printed is not None else None
    # Additive only: old full-match routes and their receipt bytes stay first.
    added_route = None
    if (match is None and section.get("content_kind") == "PRIMARY_STATEMENT"
            and section.get("statement_type") == "INCOME_STATEMENT"):
        bare = r"bao cao ket qua hoat dong(?: (?P<scope>rieng|hop nhat))? cho giai doan "
        slash = (r"tu ngay (?P<sd>[0-9]{1,2})/(?P<sm>[0-9]{1,2})/(?P<sy>[0-9]{4}) "
                 r"den ngay (?P<ed>[0-9]{1,2})/(?P<em>[0-9]{1,2})/(?P<ey>[0-9]{4})")
        written = (r"tu ngay (?P<sd>[0-9]{1,2}) thang (?P<sm>[0-9]{1,2}) nam (?P<sy>[0-9]{4}) "
                   r"den ngay (?P<ed>[0-9]{1,2}) thang (?P<em>[0-9]{1,2}) nam (?P<ey>[0-9]{4})")
        # Fold declared layout only for the new routes; raw faults remain vetoes.
        new_printed = _recognition_printed_text(" ".join(layout.split()))
        for route, dates_pattern in (("BARE_INCOME_EXPLICIT_SLASH_RANGE", slash),
                                     ("BARE_INCOME_EXPLICIT_WRITTEN_RANGE", written)):
            candidate = re.fullmatch(bare + dates_pattern, new_printed or "")
            if candidate is not None:
                match, added_route = candidate, route
                break
    reasons = []
    if section.get("content_kind") != "PRIMARY_STATEMENT" or title is None:
        reasons.append("RANGE_NOT_OWNED_BY_TYPED_PRIMARY_FLOW_CAPTION")
    if match is None:
        reasons.append("WHOLE_FINITE_PRINTED_FLOW_RANGE_NOT_RECOGNIZED")
    evidence = {
        "format_version": "F39_WHOLE_OWNED_FLOW_DATE_RANGE_CAPTION_V1",
        "source_kind": source_kind, "source_exact": source_exact,
        "source_sha256": sha256(source_exact.encode("utf-8")).hexdigest(),
        "source_lines_exact": source_exact.split("\n"),
        "content_kind": section.get("content_kind"), "statement_type": section.get("statement_type"),
        "amounts_used_as_authority": False, "source_period_keys_modified": False,
        "start_dates_inferred": False, "comparative_year_permission_granted": False,
        "unit_permission_granted": False, "report_scope_permission_granted": False,
        "sibling_or_other_surface_used": False,
    }
    if added_route is not None:
        evidence["added_lexical_rule"] = added_route
        if any(unicodedata.category(char) in {"Cf", "Cs"}
               or unicodedata.category(char) == "Cc" and char not in "\t\r\n"
               for char in source_exact):
            reasons.append("UNSUPPORTED_RAW_EXPLICIT_RANGE_CHARACTER")
        nfd_raw = unicodedata.normalize("NFD", source_exact)
        if any(char in "0123456789" and index + 1 < len(nfd_raw)
               and unicodedata.category(nfd_raw[index + 1]).startswith("M")
               for index, char in enumerate(nfd_raw)):
            reasons.append("RAW_PRINTED_DATE_NUMERIC_ANNOTATION")
    dates = {}
    if match is not None:
        # Vietnamese accent folding must not erase annotations attached to a
        # date digit. Both raw tokens must already be literal ASCII dates.
        raw_dates = re.findall(r"(?<!\S)([0-9]{1,2})/([0-9]{1,2})/([0-9]{4})(?=\s|$)", layout)
        if added_route == "BARE_INCOME_EXPLICIT_WRITTEN_RANGE":
            raw_dates = re.findall(
                r"(?<!\S)([0-9]{1,2})\s+(?:tháng|thang)\s+([0-9]{1,2})\s+"
                r"(?:năm|nam)\s+([0-9]{4})(?=\s|$)",
                unicodedata.normalize("NFC", layout), flags=re.IGNORECASE,
            )
        if raw_dates != [(match["sd"], match["sm"], match["sy"]), (match["ed"], match["em"], match["ey"])]:
            reasons.append("RAW_PRINTED_DATE_TOKENS_NOT_LITERAL_ASCII_DATES")
        if match.groupdict().get("before") and match.groupdict().get("after"):
            reasons.append("DUPLICATE_PRINTED_CONTINUATION_ASSERTION")
        if match.groupdict().get("method") and section.get("statement_type") != "CASH_FLOW":
            reasons.append("PRINTED_METHOD_NOT_OWNED_BY_CASH_FLOW")
        try:
            start = date(int(match["sy"]), int(match["sm"]), int(match["sd"]))
            end = date(int(match["ey"]), int(match["em"]), int(match["ed"]))
        except ValueError:
            reasons.append("INVALID_PRINTED_RANGE_CALENDAR_DATE")
        else:
            dates = {"printed_start_date": start.isoformat(), "printed_end_date": end.isoformat(),
                     "printed_months": end.month, "annual_assertion": False}
            if (start.year != end.year or (start.month, start.day) != (1, 1)
                    or end.month not in {3, 6, 9} or end.day != {3: 31, 6: 30, 9: 30}.get(end.month)):
                reasons.append("PRINTED_RANGE_NOT_COMPLETE_CALENDAR_INTERIM_YTD")
            if added_route is not None and end.month == 12:
                reasons.append("PRINTED_ANNUAL_RANGE_NOT_GRANTED_BY_INTERIM_ROUTE")
        evidence.update(printed_scope_furniture=match["scope"], printed_method_furniture=match.groupdict().get("method"),
                        continuation_furniture_present=bool(match.groupdict().get("before") or match.groupdict().get("after")))
    material = {**evidence, **dates, "supported": not reasons, "reasons": sorted(set(reasons)),
                "rule": "WHOLE_TYPED_INTERIM_CAPTION_EXPLICIT_SAME_YEAR_JANUARY_FIRST_TO_QUARTER_END_NO_OTHER_SURFACE_AUTHORITY"}
    receipt = {**material, "receipt_id": "gjitfav1:owned-flow-date-range-caption:" + canonical_json_sha256_v1(material)}
    return {"source_kind": source_kind, "source_exact": source_exact, "supported": not reasons,
            **dates, "source_date_range_evidence": receipt}


def _owned_flow_report_quarter_constraint(
    section: Mapping[str, Any], *, source_kind: str, source_exact: Any,
) -> dict[str, Any] | None:
    """Read an entire report-quarter caption, not a separate-quarter duration.

    This is only a current reporting-endpoint assertion. It supplies neither
    a start date nor the meaning/year of a comparative column. Finite legal
    bank/address/form furniture stays in the receipt and grants no entity,
    scope, unit or value permission.
    """
    if (source_kind not in {"SECTION_TITLE", "TABLE_TITLE"} or type(source_exact) is not str
            or section.get("content_kind") != "PRIMARY_STATEMENT"
            or section.get("statement_type") not in {"INCOME_STATEMENT", "CASH_FLOW"}):
        return None
    layout = source_exact.replace("\\n", "\n")
    relevant = _normalized(layout)
    title = (r"(?:ket qua hoat dong|ket qua kinh doanh)" if section["statement_type"] == "INCOME_STATEMENT"
             else "luu chuyen tien te")
    if re.search(r"bao cao " + title + r"\b.*\bquy\b", relevant) is None:
        return None
    # Preserve the existing finite 'Cho quý' route and its receipt bytes.
    # Only a whole typed caption may defer; a substring cannot discard an
    # unsupported prologue, control character or additional assertion.
    legacy = _recognition_printed_text(layout)
    if (legacy is not None and re.fullmatch(
            r"bao cao " + title + r"(?: rieng| hop nhat)? cho quy (?:iii|ii|iv|i|[1-4]) nam [0-9]{4}(?: \(tiep theo\))?",
            legacy) is not None
            and not any(unicodedata.category(char) == "Cc" and char not in "\t\r\n" for char in source_exact)):
        return None
    reasons = []
    if any(unicodedata.category(char) == "Cc" and char not in "\t\r\n" for char in source_exact):
        reasons.append("UNSUPPORTED_RAW_REPORT_QUARTER_CONTROL_CHARACTER")
    # Exact three classes of address furniture, never an arbitrary prefix.
    lines = [line for line in re.split(r"\r\n|\r|\n", layout) if line.strip()]
    prefix, core = [], layout
    start = next((index for index, line in enumerate(lines)
                  if re.match(r"bao cao " + title + r"\b", _recognition_printed_text(line) or "")), None)
    if start is not None and start:
        prefix, core = lines[:start], "\n".join(lines[start:])
        folded_prefix = [_recognition_printed_text(" ".join(line.split())) for line in prefix]
        bank = r"ngan hang (?:tmcp|thuong mai co phan) [a-z]+(?: [a-z]+)*"
        street = r"(?:so )?[0-9]{1,3}(?:-[0-9]{1,3}){0,2} [a-z]+(?: [a-z]+)*(?:, [a-z]+(?: [a-z]+)*)*"
        locality = r"(?:phuong|tinh|thanh pho) [a-z]+(?: [a-z]+)*(?:, [a-z]+(?: [a-z]+)*)*"
        form = r"mau so b0[34]a?/tctd(?:-hn)?"
        permitted = (len(prefix) in {3, 4} and folded_prefix[0] is not None
                     and re.fullmatch(bank, folded_prefix[0]) is not None
                     and re.fullmatch(street, folded_prefix[1] or "") is not None
                     and re.fullmatch(locality, folded_prefix[2] or "") is not None
                     and (len(prefix) == 3 or re.fullmatch(form, folded_prefix[3] or "") is not None))
        assertions = r"\b(?:khong|not|ngoai tru|bao gom|rieng|hop nhat|ngan hang me|cong ty|chi nhanh|don vi|bo phan|bao cao|quy|ky|ngay|thang|nien do|tai khoa|giai doan|ket thuc|year|period)\b"
        if (not permitted or any(re.search(assertions, line or "") for line in folded_prefix[:3])
                or re.search(r"(?<![0-9])[0-9]{4}(?![0-9])", " ".join(prefix))):
            reasons.append("UNRECOGNIZED_OR_ASSERTIVE_REPORT_QUARTER_PROLOGUE")
    printed = _recognition_printed_text(" ".join(core.split()))
    pattern = (r"bao cao " + title + r"(?: (?P<scope>rieng|hop nhat))?(?: giua nien do)? "
               r"quy (?P<quarter>iii|ii|iv|i|[1-4]) nam (?P<year>[0-9]{4})(?: \(tiep theo\))?")
    match = re.fullmatch(pattern, printed or "")
    ended_match = None
    # A distinct whole INC scaffold: a printed quarter endpoint plus its
    # calendar date. Do not widen existing legal-prefix or CF grammars.
    if match is None and not prefix and section["statement_type"] == "INCOME_STATEMENT":
        ended_pattern = (
            r"bao cao " + title + r"(?: (?P<scope>rieng|hop nhat))? cho quy "
            r"(?P<quarter>iii|ii|iv|i|[1-4]) ket thuc ngay (?P<day>[0-9]{1,2}) "
            r"thang (?P<month>[0-9]{1,2}) nam (?P<year>[0-9]{4})(?: \(tiep theo\))?"
        )
        ended_match = re.fullmatch(ended_pattern, printed or "")
        match = ended_match
    if match is None:
        reasons.append("WHOLE_PRINTED_REPORT_QUARTER_NOT_RECOGNIZED")
    raw_tokens = re.findall(
        r"(?i)(?:^|\s)qu(?:ý|y)\s+([iIvV1-4]+)\s+n(?:ă|a)m\s+([0-9]{4})(?=\s|$)", unicodedata.normalize("NFC", core),
    )
    endpoint_evidence = {}
    if ended_match is not None:
        raw_core = unicodedata.normalize("NFC", core)
        raw_quarters = re.findall(r"(?i)(?:^|\s)qu(?:ý|y)\s+(\S+)", raw_core)
        raw_dates = re.findall(
            r"(?i)(?<!\S)([0-9]{1,2})\s+th(?:á|a)ng\s+([0-9]{1,2})\s+n(?:ă|a)m\s+([0-9]{4})(?=\s|$)",
            raw_core,
        )
        raw_tokens = [(quarter, ended_match["year"]) for quarter in raw_quarters]
        if (raw_dates != [(ended_match["day"], ended_match["month"], ended_match["year"])]
                or any(not quarter.isascii() for quarter in raw_quarters)):
            reasons.append("REPORT_QUARTER_END_RAW_ASCII_DATE_NOT_PROVEN")
        try:
            endpoint = date(int(ended_match["year"]), int(ended_match["month"]), int(ended_match["day"]))
        except ValueError:
            reasons.append("INVALID_REPORT_QUARTER_END_CALENDAR_DATE")
        else:
            quarter = {"i": 1, "ii": 2, "iii": 3, "iv": 4,
                       "1": 1, "2": 2, "3": 3, "4": 4}[ended_match["quarter"]]
            if (endpoint.month, endpoint.day) != (quarter * 3, {1: 31, 2: 30, 3: 30, 4: 31}[quarter]):
                reasons.append("REPORT_QUARTER_AND_PRINTED_END_DATE_CONFLICT")
            # Nested evidence only: top-level printed_end_date would be read
            # elsewhere as a duration assertion requiring printed_months.
            endpoint_evidence["printed_reporting_end_date"] = endpoint.isoformat()
    if match is not None and (len(raw_tokens) != 1 or raw_tokens[0][1] != match["year"]
                              or raw_tokens[0][0].lower() != match["quarter"]
                              or not 1 <= int(match["year"]) <= 9999):
        reasons.append("REPORT_QUARTER_RAW_ASCII_TOKENS_NOT_PROVEN")
    fields = ({"printed_reporting_quarter": {"i": 1, "ii": 2, "iii": 3, "iv": 4,
                                            "1": 1, "2": 2, "3": 3, "4": 4}[match["quarter"]],
               "printed_year": int(match["year"])} if match is not None and not reasons else {})
    evidence = {
        "source_kind": source_kind, "source_exact": source_exact,
        "source_sha256": sha256(source_exact.encode("utf-8")).hexdigest(),
        "recognized_prefix_lines_exact": prefix, "report_caption_exact": core,
        **endpoint_evidence,
        "supported": not reasons, "reasons": sorted(set(reasons)), **fields,
        "report_scope_permission_granted": False, "entity_permission_granted": False,
        "unit_permission_granted": False, "comparative_year_permission_granted": False,
        "start_dates_inferred": False, "source_period_keys_modified": False,
        "rule": "WHOLE_TYPED_REPORT_QUARTER_ENDPOINT_ONLY_WITH_FINITE_NONASSERTIVE_FURNITURE",
    }
    return {"source_kind": source_kind, "source_exact": source_exact, "supported": not reasons, **fields,
            "source_report_quarter_evidence": {
                **evidence, "receipt_id": "gjitfav1:owned-report-quarter:" + canonical_json_sha256_v1(evidence),
            }}


def _owned_note_report_quarter_constraint_v1(
    section: Mapping[str, Any], *, source_kind: str, source_exact: Any,
) -> dict[str, Any] | None:
    """Read one whole NOTE report endpoint, never a three-month duration.

    Only actual FINANCIAL_NOTE / NOT_APPLICABLE title carriers participate.
    The scope word is retained, not granted as scope authority here. Relevant
    malformed assertions remain vetoes. A finite legacy 'cho quý' caption is
    left to its existing parser, without this endpoint-furniture exemption.
    """
    if (source_kind not in {"SECTION_TITLE", "TABLE_TITLE"} or type(source_exact) is not str
            or section.get("content_kind") != "FINANCIAL_NOTE"
            or section.get("statement_type") != "NOT_APPLICABLE"):
        return None
    if any(unicodedata.category(char) == "Cs" for char in source_exact):
        raise _error("income-tax NOTE report-quarter source contains a noncanonical surrogate")
    layout = source_exact.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\r", "\n")
    relevant = _normalized(layout)
    if (re.search(r"\bthuyet minh bao cao tai chinh\b", relevant) is None
            or re.search(r"\bquy\b", relevant) is None):
        return None
    reasons = []
    if any(unicodedata.category(char) == "Cf"
           or unicodedata.category(char) == "Cc" and char not in "\t\r\n"
           for char in source_exact):
        reasons.append("UNSUPPORTED_RAW_NOTE_REPORT_QUARTER_CHARACTER")
    if re.search(r"[0-9][\u0300-\u036f]", unicodedata.normalize("NFD", source_exact)):
        reasons.append("NOTE_REPORT_QUARTER_RAW_NUMERIC_ANNOTATION")
    printed = _recognition_printed_text(" ".join(layout.split()))
    pattern = (
        r"thuyet minh bao cao tai chinh(?: (?P<scope>rieng|hop nhat))?"
        r"(?: giua nien do)? quy (?P<quarter>iii|ii|iv|i|[1-4]) nam "
        r"(?P<year>[0-9]{4})(?: \(tiep theo\))?"
    )
    raw_tokens = re.findall(
        r"(?i)(?:^|\s)qu(?:ý|y)\s+([iIvV1-4]+)\s+n(?:ă|a)m\s+([0-9]{4})(?=\s|$)",
        unicodedata.normalize("NFC", layout),
    )
    legacy = re.fullmatch(pattern.replace(" quy ", " cho quy "), printed or "")
    if (legacy is not None and not reasons and len(raw_tokens) == 1
            and raw_tokens[0][0].lower() == legacy["quarter"]
            and raw_tokens[0][1] == legacy["year"] and 1 <= int(legacy["year"]) <= 9999):
        return None
    match = re.fullmatch(pattern, printed or "")
    if match is None:
        reasons.append("WHOLE_PRINTED_NOTE_REPORT_QUARTER_NOT_RECOGNIZED")
    if match is not None and (
        len(raw_tokens) != 1 or raw_tokens[0][0].lower() != match["quarter"]
        or raw_tokens[0][1] != match["year"] or not 1 <= int(match["year"]) <= 9999
    ):
        reasons.append("NOTE_REPORT_QUARTER_RAW_ASCII_TOKENS_NOT_PROVEN")
    fields = ({
        "printed_reporting_quarter": {"i": 1, "ii": 2, "iii": 3, "iv": 4,
                                      "1": 1, "2": 2, "3": 3, "4": 4}[match["quarter"]],
        "printed_year": int(match["year"]),
    } if match is not None and not reasons else {})
    evidence = {
        "format_version": "F39_WHOLE_NOTE_REPORT_QUARTER_ENDPOINT_V1",
        "source_kind": source_kind, "source_exact": source_exact,
        "source_sha256": sha256(source_exact.encode("utf-8")).hexdigest(),
        "source_lines_exact": source_exact.splitlines(),
        "supported": not reasons, "reasons": sorted(set(reasons)), **fields,
        "endpoint_only": True, "duration_permission_granted": False,
        "report_scope_permission_granted": False, "entity_permission_granted": False,
        "unit_permission_granted": False, "comparative_year_permission_granted": False,
        "registry_permission_granted": False, "source_values_modified": False,
        "amounts_used_as_authority": False, "start_dates_inferred": False,
        "source_period_keys_modified": False,
        "rule": "WHOLE_TYPED_NOTE_REPORT_QUARTER_ENDPOINT_ONLY_NO_PREFIX_OR_OTHER_SURFACE_WAIVER",
    }
    return {
        "source_kind": source_kind, "source_exact": source_exact,
        "supported": not reasons, **fields,
        "source_note_report_quarter_evidence": {
            **evidence, "receipt_id": "gjitfav1:owned-note-report-quarter:"
            + canonical_json_sha256_v1(evidence),
        },
    }


def _owned_current_period_constraints(section: Mapping[str, Any], table: Mapping[str, Any]) -> list[dict[str, Any]]:
    surfaces = [("SECTION_TITLE", section.get("title_exact")), ("TABLE_TITLE", table.get("title_exact"))]
    if len(section.get("tables") or []) == 1:
        surfaces.extend(("OWNED_NARRATIVE", value) for value in section.get("narratives_exact") or [])
    months_by_word = {"mot": 1, "hai": 2, "ba": 3, "bon": 4, "nam": 5, "sau": 6,
                      "bay": 7, "tam": 8, "chin": 9, "muoi": 10, "muoi mot": 11, "muoi hai": 12}
    prefix = r"(?:(?:bao cao|bang can doi) .+ )?"
    ending = r"(?P<day>\d{1,2}) (?:thang )?(?P<month>\d{1,2}) (?:nam )?(?P<year>\d{4})(?: tiep theo)?"
    output = []
    for kind, raw in surfaces:
        # FIRST N CALENDAR MONTHS is a duration assertion, not a literal
        # printed date/quarter or authority for the comparative column.
        if (kind == "OWNED_NARRATIVE" and type(raw) is str
                and section.get("content_kind") == "PRIMARY_STATEMENT"
                and section.get("statement_type") == "INCOME_STATEMENT"
                and len(section.get("tables") or []) == 1
                and same_typed_json_v1(section["tables"][0], table)):
            layout = raw.replace("\\n", "\n")
            printed = _recognition_printed_text(" ".join(layout.split()))
            first_months = re.fullmatch(
                r"cho ky ke toan (?P<months>3|6|9|12) thang dau nam (?P<year>[0-9]{4})",
                printed or "",
            )
            if first_months is not None:
                months, year = int(first_months["months"]), int(first_months["year"])
                faults = []
                if any(unicodedata.category(char) in {"Cf", "Cs"}
                       or unicodedata.category(char) == "Cc" and char not in "\t\r\n" for char in raw):
                    faults.append("FIRST_MONTHS_RAW_CHARACTER_NOT_SUPPORTED")
                if re.findall(r"(?<!\S)[0-9]+(?!\S)", layout) != [first_months["months"], first_months["year"]]:
                    faults.append("FIRST_MONTHS_RAW_ASCII_DIGITS_NOT_PROVEN")
                occurrences = [ordinal for ordinal, text in enumerate(section.get("narratives_exact") or [], 1)
                               if type(text) is str and text == raw]
                if len(occurrences) != 1:
                    faults.append("FIRST_MONTHS_OWNED_NARRATIVE_OCCURRENCE_NOT_UNIQUE")
                try:
                    endpoint = date(year, months, {3: 31, 6: 30, 9: 30, 12: 31}[months]).isoformat()
                except ValueError:
                    endpoint = None
                    faults.append("FIRST_MONTHS_PRINTED_YEAR_NOT_CALENDAR_VALID")
                evidence = {
                    "source_kind": kind, "source_exact": raw,
                    "source_sha256": sha256(raw.encode("utf-8")).hexdigest(),
                    "owned_table_object_canonical_sha256": canonical_json_sha256_v1(table),
                    "narrative_ordinals": occurrences, "supported": not faults,
                    "reasons": sorted(set(faults)), "semantic_origin": "FIRST_N_CALENDAR_MONTHS_OF_YEAR",
                    "raw_month_token": first_months["months"], "raw_year_token": first_months["year"],
                    "printed_months": months, "printed_year": year,
                    "calendar_endpoint_derived_from_printed_first_months": endpoint,
                    "literal_quarter_printed": False, "literal_endpoint_date_printed": False,
                    "comparative_period_authority_granted": False, "source_period_keys_modified": False,
                    "source_values_modified": False, "amounts_used_as_authority": False,
                    "rule": "WHOLE_SINGLE_TABLE_PRIMARY_INCOME_FIRST_CALENDAR_MONTHS_ASSERTION_ONLY",
                }
                output.append({
                    "source_kind": kind, "source_exact": raw, "supported": not faults,
                    **({"printed_reporting_quarter": months // 3, "printed_year": year,
                        "printed_months": months} if not faults else {}),
                    "source_first_calendar_months_evidence": {
                        **evidence, "receipt_id": "gjitfav1:owned-first-calendar-months:" + canonical_json_sha256_v1(evidence),
                    },
                })
                continue
        note_report_quarter = _owned_note_report_quarter_constraint_v1(section, source_kind=kind, source_exact=raw)
        if note_report_quarter is not None:
            output.append(note_report_quarter)
            continue
        date_range = _owned_flow_date_range_caption_constraint(section, source_kind=kind, source_exact=raw)
        if date_range is not None:
            output.append(date_range)
            continue
        report_quarter = _owned_flow_report_quarter_constraint(section, source_kind=kind, source_exact=raw)
        if report_quarter is not None:
            output.append(report_quarter)
            continue
        same_day = _owned_same_day_period_constraint(section, source_kind=kind, source_exact=raw)
        if same_day is not None:
            output.append(same_day)
            continue
        surface = _normalized(raw)
        # A company/report prefix in an owned caption is not permission to
        # discard its affirmative reporting-period clause.  Narratives stay
        # start-anchored so historical discussion cannot relabel the report.
        if kind in {"SECTION_TITLE", "TABLE_TITLE"}:
            marker = re.search(r"\bcho (?:ky|giai doan|nam|quy)\b", surface)
            if marker is not None:
                earlier = surface[:marker.start()]
                affirmative_prefix = (
                    r"\b(?:nam(?: tai chinh)? ket thuc|"
                    r"(?:ky(?: hoat dong| ke toan)?|giai doan) (?:\d+|mot|hai|ba|bon|nam|sau|bay|tam|chin|muoi(?: mot| hai)?) thang ket thuc|"
                    r"quy (?:i|ii|iii|iv|1|2|3|4) nam \d{4}|"
                    r"tu ngay \d{1,2} (?:thang )?\d{1,2} (?:nam )?\d{4} (?:den|toi)|"
                    r"from \d{1,2} \d{1,2} \d{4} (?:to|through))\b"
                )
                bare_annual_caption = re.search(
                    r"\b(?:bao cao (?:ket qua hoat dong|luu chuyen tien te)|thuyet minh bao cao tai chinh)\b.+\bnam(?: tai chinh)? \d{4}\s*$",
                    earlier,
                ) or re.fullmatch(r"nam(?: tai chinh)? \d{4}\s*", earlier.strip())
                if re.search(affirmative_prefix, earlier) or bare_annual_caption:
                    output.append({"source_kind": kind, "source_exact": raw, "supported": False,
                                   "unsupported_affirmative_prefix_normalized": earlier})
                    continue
                surface = surface[marker.start():]
        # Finite report furniture is retained raw in the receipt.  Do not
        # discard arbitrary text following a reporting-period assertion.
        surface = re.sub(r" (?:theo )?phuong phap (?:truc|gian) tiep(?: tiep theo)?$", "", surface)
        furniture_evidence = {}
        if re.search(r" b04a tctd hn$", surface):
            literal_form = re.search(r"(?:^|\s|\\n)(?P<form>B04a/TCTD-HN)\s*$", raw, re.IGNORECASE)
            if literal_form is None:
                output.append({"source_kind": kind, "source_exact": raw, "supported": False})
                continue
            furniture_evidence["recognized_terminal_report_furniture_exact"] = literal_form["form"]
            surface = re.sub(r" b04a tctd hn$", "", surface)
        surface = re.sub(r" b03 tctd$", "", surface)
        # A bare typed annual caption is an affirmative assertion, not absent
        # context that an interim header pair may replace. Preserve malformed
        # or annotated versions as vetoes rather than normalizing them away.
        bare_annual_prefix = r"bao cao (?:ket qua hoat dong|luu chuyen tien te)(?: rieng| hop nhat)? nam(?: tai chinh)? "
        if (kind in {"SECTION_TITLE", "TABLE_TITLE"} and section.get("content_kind") == "PRIMARY_STATEMENT"
                and re.match(bare_annual_prefix + r"\d{4}\b", surface)):
            printed = _recognition_printed_text(raw)
            bare_annual = re.fullmatch(bare_annual_prefix + r"(?P<year>\d{4})(?: \(tiep theo\))?", printed) if printed is not None else None
            output.append({"source_kind": kind, "source_exact": raw, "supported": bare_annual is not None,
                           **({"printed_annual_year": int(bare_annual["year"])} if bare_annual is not None else {})})
            continue
        annual_year = re.fullmatch(prefix + r"cho nam(?: tai chinh)? (\d{4})(?: tiep theo)?", surface)
        quarter_year = re.fullmatch(prefix + r"cho quy (i|ii|iii|iv|1|2|3|4) nam (\d{4})(?: tiep theo)?", surface)
        if annual_year is not None:
            output.append({"source_kind": kind, "source_exact": raw, "supported": True, "printed_annual_year": int(annual_year[1]), **furniture_evidence})
            continue
        if quarter_year is not None:
            quarter = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "1": 1, "2": 2, "3": 3, "4": 4}[quarter_year[1]]
            output.append({"source_kind": kind, "source_exact": raw, "supported": True,
                           "printed_reporting_quarter": quarter, "printed_year": int(quarter_year[2]), **furniture_evidence})
            continue
        # A whole explicitly reporting, uniquely owned narrative can omit
        # 'Cho'. Historical discussion and multi-table ambiguous narratives
        # are not included in this source-owned assertion axis.
        duration_prefix = r"(?:cho )?" if kind == "OWNED_NARRATIVE" else r"cho "
        duration = re.fullmatch(prefix + duration_prefix + r"(?:ky(?: hoat dong| ke toan)?|giai doan) (?P<months>\d+|mot|hai|ba|bon|nam|sau|bay|tam|chin|muoi|muoi mot|muoi hai) thang ket thuc(?: vao)? ngay " + ending, surface)
        annual = re.fullmatch(prefix + r"(?:cho )?nam(?: tai chinh)? ket thuc(?: vao)? ngay " + ending, surface)
        match = duration or annual
        if kind == "OWNED_NARRATIVE" and match is not None:
            raw_character_fault = (any(unicodedata.category(char) in {"Cf", "Cs"}
                                       or unicodedata.category(char) == "Cc" and char not in "\t\r\n" for char in raw)
                                   or re.search(r"[0-9][\u0300-\u036f]", unicodedata.normalize("NFD", raw)) is not None)
            if raw_character_fault or _recognition_printed_text(raw.replace("\\n", "\n")) is None:
                output.append({"source_kind": kind, "source_exact": raw, "supported": False})
                continue
        if match is None:
            caption_assertion = kind in {"SECTION_TITLE", "TABLE_TITLE"} and re.search(
                r"\b(?:quy (?:i|ii|iii|iv|1|2|3|4) nam \d{4}|"
                r"(?:ky(?: hoat dong| ke toan)?|giai doan) (?:\d+|mot|hai|ba|bon|nam|sau|bay|tam|chin|muoi(?: mot| hai)?) thang ket thuc|"
                r"tu ngay\b.+\b(?:den|toi)\b|from\b.+\b(?:to|through)\b|"
                r"for (?:the )?(?:period|year|quarter)\b|(?:reporting|accounting) period (?:ended|ending)\b|"
                r"(?:fiscal|financial) year (?:ended|ending)\b)", surface,
            )
            if caption_assertion or re.fullmatch(prefix + r"(?:cho (?:ky|giai doan|nam|quy)\b.+|nam(?: tai chinh)? ket thuc\b.*)", surface):
                output.append({"source_kind": kind, "source_exact": raw, "supported": False})
            continue
        try:
            end = date(int(match["year"]), int(match["month"]), int(match["day"]))
        except ValueError:
            output.append({"source_kind": kind, "source_exact": raw, "supported": False})
            continue
        months = 12 if annual is not None else int(duration["months"]) if duration["months"].isdigit() else months_by_word[duration["months"]]
        output.append({"source_kind": kind, "source_exact": raw, "supported": 1 <= months <= 12,
                       "printed_end_date": end.isoformat(), "printed_months": months, "annual_assertion": annual is not None,
                       **furniture_evidence})
    # A header pair may fill an absent caption assertion, never replace an
    # unsupported or conflicting assertion already present in the source.
    if not output:
        header_constraint = _owned_absolute_flow_header_constraint(section, table)
        if header_constraint is not None:
            output.append(header_constraint)
    return output


def _owned_current_period_constraints_match(section: Mapping[str, Any], table: Mapping[str, Any], lane: Mapping[str, Any], periods: Sequence[Sequence[Any]] | None = None) -> bool:
    constraints = _owned_current_period_constraints(section, table)
    if not constraints:
        return True
    if periods:
        current = periods[0]
        year = current[1]
        months = 12 if current[0] == "ANNUAL_YEAR" else current[2] * 3
        ending_parts = (year, months, {3: 31, 6: 30, 9: 30, 12: 31}[months])
    else:
        keys = lane.get("source_lane_keys") or []
        if not keys:
            return False
        key = keys[0]
        lengths = _printed_duration_lengths(table, lane.get("money_column_ordinals") or [], section=section)
        if key[0] in {"BARE_YEAR", "DURATION_BARE_YEAR"}:
            year, months = int(key[1]), 12
            ending_parts = (year, 12, 31)
        elif key[0] in {"DURATION_END_DATE", "DURATION_DATE_RANGE"}:
            end = date.fromisoformat(key[-1])
            ending_parts = (end.year, end.month, end.day)
            months = lengths[0][0] if lengths and len(lengths[0]) == 1 else None
            if months is None and key[0] == "DURATION_DATE_RANGE":
                start = date.fromisoformat(key[1])
                exclusive = end + timedelta(days=1)
                if start.day == exclusive.day == 1:
                    months = (exclusive.year - start.year) * 12 + exclusive.month - start.month
        else:
            return False
    for item in constraints:
        if not item["supported"]:
            return False
        if "printed_start_date" in item and item["printed_start_date"] != date(ending_parts[0], 1, 1).isoformat():
            return False
        if "printed_annual_year" in item:
            if months != 12 or ending_parts != (item["printed_annual_year"], 12, 31):
                return False
        elif "printed_reporting_quarter" in item:
            quarter_month = item["printed_reporting_quarter"] * 3
            if ending_parts != (item["printed_year"], quarter_month, {3: 31, 6: 30, 9: 30, 12: 31}[quarter_month]):
                return False
            if "source_first_calendar_months_evidence" in item and months != item["printed_months"]:
                return False
        elif item["printed_months"] != months or tuple(map(int, item["printed_end_date"].split("-"))) != ending_parts:
            return False
    return True


def _relative_year_column_paths(table: Mapping[str, Any], lane: Mapping[str, Any]) -> list[list[str]] | None:
    """Literal label syntax only; this supplies no reporting-period authority."""
    if not lane.get("complete") or lane.get("source_lane_keys") != [["SEMANTIC_ALIAS", "CURRENT_PERIOD"], ["SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"]]:
        return None
    ordinals = lane.get("money_column_ordinals") or []
    if len(ordinals) != 2:
        return None
    headers = [" ".join(table["columns"][ordinal - 1]["header_path_exact"]) for ordinal in ordinals]
    for header, token in zip(headers, ("nay", "truoc"), strict=True):
        if re.fullmatch(r"nam " + token + r"(?: trinh bay lai)?(?: (?:trieu dong|trieu vnd|vnd|dong))?(?: trinh bay lai)?", _normalized(header)) is None:
            return None
    return [canonical_clone_v1(table["columns"][ordinal - 1]["header_path_exact"]) for ordinal in ordinals]


def _owned_relative_year_duration_evidence(section: Mapping[str, Any], table: Mapping[str, Any], lane: Mapping[str, Any]) -> dict[str, Any] | None:
    paths = _relative_year_column_paths(table, lane)
    if paths is None:
        return None
    ordinals = lane["money_column_ordinals"]
    constraints = _owned_current_period_constraints(section, table)
    if not constraints or any(not item["supported"] for item in constraints):
        return None
    resolutions = []
    for item in constraints:
        if "printed_annual_year" in item:
            resolutions.append(["ANNUAL_YEAR", item["printed_annual_year"]])
        elif "printed_end_date" in item:
            end = date.fromisoformat(item["printed_end_date"])
            months = item["printed_months"]
            if months not in {3, 6, 9, 12} or months != end.month or (end + timedelta(days=1)).day != 1:
                return None
            resolutions.append(["ANNUAL_YEAR", end.year] if months == 12 else ["SOURCE_YTD_QUARTER", end.year, months // 3])
        else:
            return None
    if any(not same_typed_json_v1(item, resolutions[0]) for item in resolutions[1:]) or resolutions[0][1] <= 1:
        return None
    current = resolutions[0]
    periods = [current, [current[0], current[1] - 1, *current[2:]]]
    material = {"money_column_ordinals": list(ordinals), "header_paths_exact": paths,
                "owned_current_period_constraints": constraints, "resolved_source_duration_semantics": periods,
                "comparative_year_origin": "DERIVED_RELATIVE_YEAR_SEMANTICS_NOT_PRINTED_ABSOLUTE_YEAR",
                "rule": "EXACT_ORDERED_NAM_NAY_NAM_TRUOC_WITH_INDEPENDENT_OWNED_CURRENT_DURATION_NO_GENERIC_PERIOD_ALIAS_INFERENCE"}
    return {**material, "receipt_id": "gjitfav1:owned-relative-year-duration:" + canonical_json_sha256_v1(material)}


def _absolute_source_duration_semantics(section: Mapping[str, Any], table: Mapping[str, Any], lane: Mapping[str, Any]) -> list[list[Any]] | None:
    relative = _owned_relative_year_duration_evidence(section, table, lane)
    if relative is not None:
        return relative["resolved_source_duration_semantics"]
    ytd = _printed_ytd_sibling_period_evidence(section, table, lane)
    if ytd is not None and ytd["intrinsic_absolute_periods"] is not None:
        periods = ytd["intrinsic_absolute_periods"]
        return periods if _owned_current_period_constraints_match(section, table, lane, periods) else None
    lengths = _printed_duration_lengths(table, lane.get("money_column_ordinals") or [], section=section)
    if (_annual_source_context_ambiguous(section, table, lane)
            or not _source_duration_correspondence_complete(lane, lane, note_table=table, primary_table=table,
                                                          note_lengths=lengths, primary_lengths=lengths)):
        return None
    periods = []
    for index, key in enumerate(lane["source_lane_keys"]):
        if key[0] in {"BARE_YEAR", "DURATION_BARE_YEAR"}:
            periods.append(["ANNUAL_YEAR", int(key[1])])
            continue
        if key[0] == "DURATION_END_DATE":
            end = date.fromisoformat(key[1])
            months = lengths[index][0]
        elif key[0] == "DURATION_DATE_RANGE":
            start, end = date.fromisoformat(key[1]), date.fromisoformat(key[2])
            if (start.year, start.month, start.day) != (end.year, 1, 1):
                return None
            months = end.month
        else:
            return None
        if months not in {3, 6, 9, 12} or end.month != months or (end + timedelta(days=1)).day != 1:
            return None
        periods.append(["ANNUAL_YEAR", end.year] if months == 12 else ["SOURCE_YTD_QUARTER", end.year, months // 3])
    if len(periods) != 2 or periods[0][0] != periods[1][0] or periods[0][1] <= periods[1][1] or periods[0][2:] != periods[1][2:]:
        return None
    return periods if _owned_current_period_constraints_match(section, table, lane, periods) else None


def _printed_ytd_sibling_period_evidence(section: Mapping[str, Any], table: Mapping[str, Any], lane: Mapping[str, Any]) -> dict[str, Any] | None:
    if section.get("content_kind") != "PRIMARY_STATEMENT" or section.get("statement_type") not in {"INCOME_STATEMENT", "CASH_FLOW"}:
        return None
    money = [ordinal for ordinal, column in enumerate(table["columns"], 1) if column["value_kind"] == "MONEY"]
    if (not lane.get("complete") or len(money) != 4 or lane.get("money_column_ordinals") != money[2:]
            or lane.get("excluded_parallel_duration_money_column_ordinals") != money[:2]
            or any(column["value_kind"] not in {"TEXT", "MONEY"} for column in table["columns"])):
        return None
    quarter_numbers = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "1": 1, "2": 2, "3": 3, "4": 4}
    suffix = r"(?: (?:trieu dong|trieu vnd|vnd|dong))?"
    paths = [table["columns"][ordinal - 1].get("header_path_exact") for ordinal in money]
    if any(type(path) is not list or not path or any(type(part) is not str or not part.strip() for part in path)
           for path in paths):
        return None
    # Recognize only complete printed headers. Vietnamese letter folding must
    # not erase punctuation, digit annotations or marks on Roman quarter codes.
    layouts = [" ".join(path).replace("\\n", "\n") for path in paths]
    # Whitespace is layout only. Preserve the original layouts below so this
    # view cannot join split digits/codes or erase annotations on raw tokens.
    headers = [_recognition_printed_text(" ".join(layout.split())) for layout in layouts]
    year_suffix = r"(?:nam (?P<relative>nay|truoc)|(?:nam )?(?P<absolute>[0-9]{4}))"
    quarters = [re.fullmatch(r"quy (?P<quarter>i|ii|iii|iv|1|2|3|4) " + year_suffix + suffix, header or "")
                for header in headers[:2]]
    cumulative = [re.fullmatch(r"luy ke tu dau nam(?: den cuoi quy nay)? " + year_suffix + suffix, header or "")
                  for header in headers[2:]]
    # This exact common reporting frame occurs on BOTH cumulative columns.
    # Its internal 'nam nay' is not the comparative column's year suffix.
    current_frame = [re.fullmatch(r"luy ke tu dau nam nay den cuoi quy nay " + year_suffix + suffix, header or "")
                     for header in headers[2:]]
    if any(match is not None for match in current_frame):
        if any(match is None for match in current_frame):
            return None
        cumulative = current_frame
    # A second, distinct frame prints the SAME named quarter on both YTD
    # headers. Only explicit per-column years are admitted by this new route.
    named_frame = [re.fullmatch(
        r"luy ke tu dau nam den cuoi quy (?P<quarter>i|ii|iii|iv|1|2|3|4) " + year_suffix + suffix,
        header or "",
    ) for header in headers[2:]]
    named_frame_active = any(match is not None for match in named_frame)
    if named_frame_active:
        if any(match is None for match in named_frame):
            return None
        cumulative = named_frame
    matches = [*quarters, *cumulative]
    if any(match is None for match in matches):
        return None
    if named_frame_active and any(match["absolute"] is None for match in matches):
        return None
    for index, (layout, match) in enumerate(zip(layouts, matches, strict=True)):
        if index < 2:
            raw_quarter = layout.split()[1]
            if not raw_quarter.isascii() or raw_quarter.lower() != match["quarter"]:
                return None
        elif named_frame_active:
            raw_quarters = re.findall(r"(?i)(?:^|\s)qu(?:ý|y)\s+(\S+)", unicodedata.normalize("NFC", layout))
            if (len(raw_quarters) != 1 or not raw_quarters[0].isascii()
                    or raw_quarters[0].lower() != match["quarter"]):
                return None
        if match["absolute"] is not None:
            raw_years = re.findall(r"(?<!\S)[0-9]{4}(?!\S)", layout)
            if raw_years != [match["absolute"]] or not 1 <= int(match["absolute"]) <= 9999:
                return None
    quarter = quarter_numbers[quarters[0]["quarter"]]
    if named_frame_active and any(quarter_numbers[match["quarter"]] != quarter for match in cumulative):
        return None
    tokens = [match["relative"] or match["absolute"] for match in quarters]
    if (quarter_numbers[quarters[1]["quarter"]] != quarter
            or tokens != [match["relative"] or match["absolute"] for match in cumulative]):
        return None
    relative = tokens == ["nay", "truoc"]
    if not relative and not (all(token.isdigit() for token in tokens) and int(tokens[0]) > int(tokens[1])):
        return None
    for surface in (section.get("title_exact"), table.get("title_exact")):
        if any(quarter_numbers[value] != quarter for value in re.findall(r"\bquy (i|ii|iii|iv|1|2|3|4)\b", _normalized(surface))):
            return None
    periods = None if relative else [["ANNUAL_YEAR", int(token)] if quarter == 4 else ["SOURCE_YTD_QUARTER", int(token), quarter] for token in tokens]
    material = {"quarter": quarter, "relative_year_tokens": tokens if relative else None,
                "printed_absolute_year_tokens": None if relative else tokens,
                "intrinsic_absolute_periods": periods, "money_column_ordinals": money,
                "quarter_columns_exact": [canonical_clone_v1(table["columns"][ordinal - 1]) for ordinal in money[:2]],
                "cumulative_columns_exact": [canonical_clone_v1(table["columns"][ordinal - 1]) for ordinal in money[2:]],
                "original_table_json_sha256": canonical_json_sha256_v1(table),
                "rule": "EXACT_FOUR_MONEY_PARALLEL_QUARTER_YTD_SOURCE_AXIS_MATCHED_YEAR_SUFFIXES_NO_AMOUNT_INFERENCE"}
    return {**material, "receipt_id": "gjitfav1:printed-ytd-siblings:" + canonical_json_sha256_v1(material)}


def _unsupported_english_comparative_flow_assertion(source_exact: Any) -> bool:
    search = _normalized(source_exact)
    return bool(
        re.search(r"\b(?:comparative|prior (?:year|period))\b", search)
        and re.search(r"\b(?:income statement|statement of (?:cash flows?|profit|income)|cash flow statement)\b", search)
    )


def _parse_printed_comparative_flow_policy(source_exact: Any) -> dict[str, Any]:
    """Read finite printed comparative FLOW prose, never supply its missing year."""
    folded = _recognition_printed_text(source_exact)
    search = _normalized(source_exact)
    comparative_assertion = ("so sanh" in search or re.search(r"\bso lieu (?:cua )?(?:ky|nam) truoc\b", search) is not None)
    relevant = (comparative_assertion and any(surface in search for surface in (
        "bao cao ket qua hoat dong", "bao cao ket qua kinh doanh", "bao cao luu chuyen tien te")))
    # English comparative assertions are relevance-only: unsupported wording
    # must veto a competing policy, never silently disappear or supply dates.
    relevant = relevant or _unsupported_english_comparative_flow_assertion(source_exact)
    clauses, periods, reasons = [], [], []
    ending = r"(?P<months>\d{1,2}) thang ket thuc ngay (?P<day>\d{1,2}) thang (?P<month>\d{1,2}) nam (?P<year>\d{4})"
    scope = r"(?P<scope> rieng| hop nhat|)"
    flow_head = (r"bao cao ket qua hoat dong" + scope + r" giua nien do, "
                 r"bao cao luu chuyen tien te(?P=scope) giua nien do va cac thuyet minh tuong ung la so lieu ")
    flow_patterns = (
        ("TREN_REVIEW_BEFORE_DURATION", r"so lieu so sanh tren " + flow_head
         + r"tren bao cao tai chinh(?P=scope) giua nien do da duoc soat xet cho ky hoat dong " + ending + r"\."),
        ("CUA_CUA_REVIEW_BEFORE_INTERIM", r"so lieu so sanh cua cua " + flow_head
         + r"cua bao cao tai chinh(?P=scope) da duoc soat xet giua nien do cho ky hoat dong " + ending + r"\."),
        ("CUA_REVIEW_AFTER_DURATION", r"so lieu so sanh cua " + flow_head
         + r"cua bao cao tai chinh(?P=scope) giua nien do cho ky hoat dong " + ending + r" da duoc soat xet\."),
        ("TREN_RELATED_NOTES_WRITTEN_NINE_MONTHS", r"so lieu so sanh tren bao cao ket qua hoat dong" + scope
         + r" giua nien do, bao cao luu chuyen tien te(?P=scope) giua nien do va cac thuyet minh lien quan "
         + r"la so lieu cua bao cao tai chinh(?P=scope) giua nien do cho ky (?P<months>chin) thang ket thuc ngay "
         + r"(?P<day>\d{1,2}) thang (?P<month>\d{1,2}) nam (?P<year>\d{4}) da duoc soat xet\."),
        ("TREN_RELATED_NOTES_WRITTEN_NINE_MONTHS_NO_REVIEW_ASSERTION", r"so lieu so sanh tren bao cao ket qua hoat dong" + scope
         + r" giua nien do, bao cao luu chuyen tien te(?P=scope) giua nien do va cac thuyet minh lien quan "
         + r"la so lieu cua bao cao tai chinh(?P=scope) giua nien do cho ky (?P<months>chin) thang ket thuc ngay "
         + r"(?P<day>[0-9]{1,2}) thang (?P<month>[0-9]{1,2}) nam (?P<year>[0-9]{4})\."),
        ("TREN_RELATED_NOTES_WRITTEN_SIX_MONTHS", r"so lieu so sanh tren bao cao ket qua hoat dong" + scope
         + r" giua nien do, bao cao luu chuyen tien te(?P=scope) giua nien do va cac thuyet minh lien quan "
         + r"la so lieu cua bao cao tai chinh(?P=scope) giua nien do cho ky (?P<months>sau) thang ket thuc ngay "
         + r"(?P<day>\d{1,2}) thang (?P<month>\d{1,2}) nam (?P<year>\d{4}) da duoc soat xet\."),
        ("TREN_ANNUAL_ALL_STATEMENTS_RELATED_NOTES", r"so lieu so sanh tren bao cao tinh hinh tai chinh" + scope
         + r", bao cao ket qua hoat dong(?P=scope), bao cao luu chuyen tien te(?P=scope) va cac thuyet minh lien quan "
         + r"la so lieu cua bao cao tai chinh(?P=scope) cho nam tai chinh ket thuc ngay "
         + r"(?P<day>\d{1,2}) thang (?P<month>\d{1,2}) nam (?P<year>\d{4}) da duoc kiem toan\."),
    )
    stock_pattern = (
        r"so lieu so sanh (?:cua|tren) bao cao tinh hinh tai chinh" + scope
        + r" giua nien do va cac thuyet minh (?:tuong ung|lien quan) la so lieu cua bao cao tai chinh(?P=scope) "
        r"cho nam tai chinh ket thuc ngay (?P<day>\d{1,2}) thang (?P<month>\d{1,2}) nam (?P<year>\d{4}) da duoc kiem toan\."
    )
    if relevant:
        if folded is None:
            reasons.append("COMPARATIVE_FLOW_POLICY_UNSUPPORTED_PRINTED_CHARACTERS")
        else:
            for sentence in re.finditer(r"\S[^.!?]*(?:[.!?]|$)", source_exact):
                raw = sentence.group()
                surface = _recognition_printed_text(raw)
                matched = next(((name, match) for name, pattern in flow_patterns
                                if (match := re.fullmatch(pattern, surface or "")) is not None), None)
                clause = {"start": sentence.start(), "end": sentence.end(), "source_exact": raw,
                          "source_sha256": canonical_json_sha256_v1(raw)}
                if matched is not None:
                    name, match = matched
                    try:
                        if name == "TREN_RELATED_NOTES_WRITTEN_NINE_MONTHS_NO_REVIEW_ASSERTION":
                            # New source scaffold only: accent folding must not
                            # turn annotated numerals into printed calendar tokens.
                            numeric_tokens = [token for token in raw.split()
                                              if any(char.isdecimal() for char in token)]
                            if numeric_tokens != [match["day"], match["month"], match["year"] + "."]:
                                raise ValueError("calendar tokens are not plain printed ASCII")
                            base = None
                            for char in unicodedata.normalize("NFD", raw):
                                if unicodedata.combining(char):
                                    if base is None or not base.isascii() or not base.isalpha():
                                        raise ValueError("combining annotation outside a printed letter")
                                else:
                                    base = char
                                if unicodedata.category(char) in {"Cc", "Cf", "Cs"} and char not in "\t\r\n":
                                    raise ValueError("unsupported raw policy control character")
                        end = date(int(match["year"]), int(match["month"]), int(match["day"]))
                        if name == "TREN_ANNUAL_ALL_STATEMENTS_RELATED_NOTES":
                            months = 12
                        else:
                            printed_months = match["months"]
                            written_months = {"sau": 6, "chin": 9}
                            months = (written_months[printed_months] if printed_months in written_months
                                      else int(printed_months))
                        if not 1 <= months <= 12:
                            raise ValueError("unsupported printed month count")
                    except ValueError:
                        reasons.append("COMPARATIVE_FLOW_POLICY_INVALID_PRINTED_DURATION")
                        clause.update({"kind": "UNRECOGNIZED_FLOW_ASSERTION", "scaffold": name})
                    else:
                        period = {"printed_months": months, "printed_end_date": end.isoformat(),
                                  "report_scope": {" rieng": "SEPARATE", " hop nhat": "CONSOLIDATED", "": None}[match["scope"]]}
                        periods.append(period)
                        clause.update({"kind": "COMPARATIVE_FLOW_POLICY", "scaffold": name,
                                       "comparative_period": period,
                                       "applies_to": ["INCOME_STATEMENT", "CASH_FLOW", "CORRESPONDING_NOTES"]})
                else:
                    stock = re.fullmatch(stock_pattern, surface or "")
                    if stock is not None:
                        try:
                            stock_end = date(int(stock["year"]), int(stock["month"]), int(stock["day"]))
                        except ValueError:
                            reasons.append("RETAINED_STOCK_POLICY_INVALID_PRINTED_DATE")
                            clause.update({"kind": "UNRECOGNIZED_NON_FLOW_SENTENCE"})
                        else:
                            clause.update({"kind": "RETAINED_NON_FLOW_SENTENCE", "applies_to": ["BALANCE_SHEET"],
                                           "printed_snapshot_date": stock_end.isoformat(),
                                           "report_scope": {" rieng": "SEPARATE", " hop nhat": "CONSOLIDATED", "": None}[stock["scope"]],
                                           "used_as_flow_period_authority": False})
                    else:
                        clause.update({"kind": "UNRECOGNIZED_FLOW_ASSERTION"})
                        reasons.append("COMPARATIVE_FLOW_POLICY_UNRECOGNIZED_SENTENCE_OR_SUFFIX")
                clauses.append(clause)
            if len(periods) != 1:
                reasons.append("EXACTLY_ONE_PRINTED_COMPARATIVE_FLOW_CLAUSE_REQUIRED")
    material = {"complete": relevant and not reasons, "status": "ALGORITHM_HOLD" if relevant and reasons else "PASS" if relevant else "NOT_APPLICABLE",
                "source_exact": source_exact, "source_sha256": canonical_json_sha256_v1(source_exact),
                "clause_receipts": clauses, "comparative_period": periods[0] if relevant and not reasons else None,
                "applies_to": ["INCOME_STATEMENT", "CASH_FLOW", "CORRESPONDING_NOTES"] if relevant and not reasons else [],
                "reasons": sorted(set(reasons)), "rule": "FINITE_FULL_PRINTED_FLOW_COMPARATIVE_CLAUSE_WITH_SEPARATELY_RETAINED_STOCK_SENTENCE"}
    return {**material, "receipt_id": "gjitfav1:printed-comparative-flow-policy:" + canonical_json_sha256_v1(material)}


def _document_comparative_flow_policy_receipt(
    page_records: Sequence[Mapping[str, Any]], sources: Sequence[Mapping[str, Any]], document_scope: Mapping[str, Any],
    *, compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Independent printed comparative policy plus every owned current FLOW anchor."""
    if not same_typed_json_v1(document_scope, _document_report_scope_receipt(page_records)):
        raise _error("income-tax comparative flow document scope source replay drifted")
    page_axis, policies, reasons, period_reasons, scope_reasons = [], [], [], [], []
    records = {record["page_json_version_id"]: record for record in page_records}
    for record in page_records:
        page = record["page_json"]
        page_axis.append({**{key: canonical_clone_v1(record[key]) for key in (
            "document_id", "document_ordinal", "page_json_version_id", "physical_page", "selected_page_ordinal", "source_logical_name", "source_sha256")},
                          "original_page_json_sha256": canonical_json_sha256_v1(page)})
        for section_ordinal, section in enumerate(page.get("sections") or [], 1):
            for narrative_ordinal, narrative in enumerate(section.get("narratives_exact") or [], 1):
                parsed = _parse_printed_comparative_flow_policy(narrative)
                if parsed["status"] == "NOT_APPLICABLE":
                    continue
                note_owner = (page.get("status") == "FINANCIAL_NOTE_CONTENT"
                              and section.get("content_kind") == "FINANCIAL_NOTE"
                              and section.get("statement_type") == "NOT_APPLICABLE")
                # A comparability paragraph owns its exact original SECTION,
                # not sibling tables/narratives or a borrowed page heading.
                title = _recognition_printed_text(section.get("title_exact"))
                title_match = re.fullmatch(
                    r"trinh bay ve kha nang so sanh thong tin tren bao cao tai chinh "
                    r"(?P<scope>rieng|hop nhat) giua nien do", title or "",
                )
                title_scope = ({"rieng": "SEPARATE", "hop nhat": "CONSOLIDATED"}[title_match["scope"]]
                               if title_match is not None else None)
                qualifiers = _printed_population_qualifiers([section.get("title_exact"), narrative])
                local_scopes = sorted(set(qualifiers) & {"SEPARATE", "CONSOLIDATED"})
                entities = sorted(set(qualifiers) & {"PARENT_ENTITY", "SUBSIDIARY_ENTITY"})
                ambiguous_scope = _ambiguous_report_scope_surface([section.get("title_exact"), narrative])
                parsed_scope = parsed["comparative_period"]["report_scope"] if parsed["complete"] else None
                caption_scope_coherent = (title_scope is not None and parsed_scope == title_scope
                                          and local_scopes == [title_scope] and not entities
                                          and not ambiguous_scope)
                narrative_context = (
                    page.get("status") == "FINANCIAL_NOTE_CONTENT"
                    and section.get("content_kind") == "FINANCIAL_NARRATIVE"
                    and section.get("statement_type") == "NOT_APPLICABLE"
                    and type(section.get("tables")) is list and not section["tables"]
                    and type(section.get("narratives_exact")) is list
                    and len(section["narratives_exact"]) == 1 and narrative_ordinal == 1
                    and title_match is not None
                )
                narrative_owner = narrative_context and parsed["complete"] and caption_scope_coherent
                owner = note_owner or narrative_owner
                policy_reasons = list(parsed["reasons"])
                if not owner:
                    policy_reasons.append("PRINTED_FLOW_POLICY_NOT_OWNED_BY_ORIGINAL_FINANCIAL_NOTE_SECTION")
                if entities or len(local_scopes) > 1 or _ambiguous_report_scope_surface([section.get("title_exact"), narrative]):
                    scope_reasons.append("COMPARATIVE_FLOW_POLICY_LOCAL_REPORT_POPULATION_CONFLICT")
                if (local_scopes and document_scope.get("report_scope") is not None
                        and local_scopes != [document_scope["report_scope"]]):
                    scope_reasons.append("COMPARATIVE_FLOW_POLICY_DOCUMENT_SCOPE_CONFLICT")
                policies.append({"locator": _record_locator(record, section_id=f"s{section_ordinal}", table_id="NONE"),
                                 "page_status": page.get("status"), "section_content_kind": section.get("content_kind"),
                                 "section_statement_type": section.get("statement_type"), "section_title_exact": section.get("title_exact"),
                                 "section_table_count": len(section.get("tables") or []), "narrative_ordinal": narrative_ordinal,
                                 "original_page_json_sha256": canonical_json_sha256_v1(page),
                                 "original_section_json_sha256": canonical_json_sha256_v1(section),
                                 "original_narrative_sha256": canonical_json_sha256_v1(narrative),
                                 "source_exact": narrative, "parser_receipt": parsed, "owned": owner,
                                 **({"financial_narrative_ownership": {
                                     "rule": "EXACT_TYPED_COMPARABILITY_SECTION_FULL_PARAGRAPH_SCOPE_COHERENCE",
                                     "context_complete": narrative_context,
                                     "complete": narrative_owner,
                                     "title_exact": section.get("title_exact"),
                                     "title_scope": title_scope, "parsed_flow_scope": parsed_scope,
                                     "caption_scope_coherent": caption_scope_coherent,
                                     "section_narrative_count": len(section.get("narratives_exact") or []),
                                     "sibling_section_context_used": False,
                                 }} if section.get("content_kind") == "FINANCIAL_NARRATIVE" else {}),
                                 "local_qualifiers": qualifiers, "reasons": sorted(set(policy_reasons))})
                period_reasons.extend(policy_reasons)
    page_axis.sort(key=lambda item: item["selected_page_ordinal"])
    common = {"comparative_origin": "PRINTED_DOCUMENT_COMPARATIVE_FLOW_POLICY", "source_period_keys_modified": False,
              "amounts_used_as_authority": False, "start_dates_inferred": False,
              "selected_page_axis_sha256": canonical_json_sha256_v1(page_axis),
              "document_report_scope_receipt_id": document_scope["receipt_id"]}
    if not policies:
        material = {**common, "complete": False, "status": "NOT_APPLICABLE", "period_evidence_complete": False,
                    "scope_complete": False, "resolved_source_duration_semantics": None,
                    "policy_source_receipts": [], "anchor_source_receipts": [],
                    "reasons": ["NO_PRINTED_COMPARATIVE_FLOW_POLICY"],
                    "rule": "NO_FLOW_POLICY_PRESENT_NO_DOCUMENT_PERIOD_AUTHORITY"}
        return {**material, "receipt_id": "gjitfav1:document-comparative-flow-policy:" + canonical_json_sha256_v1(material)}
    identities = {(record["document_id"], record["document_ordinal"], record["source_sha256"], record["source_logical_name"]) for record in page_records}
    if (len(identities) != 1 or len(records) != len(page_records) or not document_scope["document_identity_unique"]
            or len({record["physical_page"] for record in page_records}) != len(page_records)
            or len({record["selected_page_ordinal"] for record in page_records}) != len(page_records)):
        period_reasons.append("DOCUMENT_COMPARATIVE_FLOW_SOURCE_IDENTITY_NOT_UNIQUE")
    if (document_scope.get("report_scope") is None or document_scope["entity_override_present"]
            or document_scope["ambiguous_scope_caption_present"] or len(document_scope["all_printed_report_scopes"]) != 1):
        scope_reasons.append("DOCUMENT_COMPARATIVE_FLOW_REPORT_POPULATION_NOT_PROVEN")
    comparative = [item["parser_receipt"]["comparative_period"] for item in policies if item["parser_receipt"]["complete"] and item["owned"]]
    if not comparative or any(not same_typed_json_v1(item, comparative[0]) for item in comparative[1:]):
        period_reasons.append("DOCUMENT_PRINTED_COMPARATIVE_FLOW_POLICY_NOT_UNIQUE")
    comparative_period = comparative[0] if comparative else None
    anchors, current_periods = [], []
    scope_sources = {canonical_json_sha256_v1(item["locator"]): item for item in document_scope["sources"]}
    expected_locators = []
    for record in page_records:
        if record["page_json"].get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            continue
        for si, section in enumerate(record["page_json"].get("sections") or [], 1):
            if section.get("content_kind") != "PRIMARY_STATEMENT" or section.get("statement_type") not in {"INCOME_STATEMENT", "CASH_FLOW"}:
                continue
            expected_locators.extend(_record_locator(record, section_id=f"s{si}", table_id=f"t{ti}")
                                     for ti, _ in enumerate(section.get("tables") or [], 1))
    if sorted(canonical_json_sha256_v1(item) for item in expected_locators) != sorted(canonical_json_sha256_v1(item["locator"]) for item in sources):
        period_reasons.append("ALL_ORIGINAL_TYPED_FLOW_TABLES_AND_CONTINUATIONS_REQUIRED")
    for source in sorted(sources, key=lambda item: (item["locator"]["selected_page_ordinal"], int(item["locator"]["section_id"][1:]), int(item["locator"]["table_id"][1:]))):
        locator, failures = source["locator"], []
        record = records.get(locator["page_json_version_id"])
        if record is None:
            raise _error("income-tax comparative flow anchor selected source page drifted")
        section, table = _source_table(record["page_json"], section_id=locator["section_id"], table_id=locator["table_id"])
        if (not same_typed_json_v1(locator, _record_locator(record, section_id=locator["section_id"], table_id=locator["table_id"]))
                or source["original_page_json_sha256"] != canonical_json_sha256_v1(record["page_json"])
                or source["original_section_json_sha256"] != canonical_json_sha256_v1(section)
                or source["original_table_json_sha256"] != canonical_json_sha256_v1(table)
                or not same_typed_json_v1(source["columns_exact"], table["columns"])
                or not same_typed_json_v1(source["owned_current_period_constraints"], _owned_current_period_constraints(section, table))):
            raise _error("income-tax comparative flow anchor original source binding drifted")
        caption = scope_sources.get(canonical_json_sha256_v1(locator))
        eligible = caption["eligible_captions_exact"] if caption is not None else []
        if not eligible:
            failures.append("FLOW_ANCHOR_STATEMENT_TYPE_NOT_AUTHENTICATED_BY_OWNED_CAPTION")
        anchor_scope = source["scope_receipt"]
        constraints = source["owned_current_period_constraints"]
        current = []
        quarter_header_evidence = None
        if not constraints or any(not item["supported"] for item in constraints):
            failures.append("FLOW_ANCHOR_INDEPENDENT_OWNED_CURRENT_DURATION_REQUIRED")
        for constraint in constraints:
            if not constraint["supported"]:
                continue
            if "printed_end_date" in constraint:
                current.append({"printed_months": constraint["printed_months"], "printed_end_date": constraint["printed_end_date"]})
            elif "printed_annual_year" in constraint:
                current.append({"printed_months": 12, "printed_end_date": f"{constraint['printed_annual_year']:04d}-12-31"})
            elif "printed_reporting_quarter" in constraint:
                # A report-quarter caption is an endpoint, not a duration.
                # Only the same table's independent absolute selected headers
                # can supply duration here; relative-year resolution cannot.
                lane = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
                if not same_typed_json_v1(source["lane_axis"], lane):
                    raise _error("income-tax quarter-caption original header lane source replay drifted")
                absolute = _absolute_source_duration_semantics(section, table, lane)
                if not same_typed_json_v1(source["absolute_duration_semantics"], absolute):
                    raise _error("income-tax quarter-caption absolute header duration source replay drifted")
                keys = lane.get("source_lane_keys") or []
                dated_pair = (len(keys) == 2 and all(
                    key[0] in {"DURATION_END_DATE", "DURATION_DATE_RANGE"} for key in keys
                ))
                sibling = _printed_ytd_sibling_period_evidence(section, table, lane)
                intrinsic_sibling = (sibling is not None and absolute is not None
                                     and same_typed_json_v1(sibling["intrinsic_absolute_periods"], absolute))
                if (absolute is None or not lane.get("complete") or not (dated_pair or intrinsic_sibling)
                        or not _owned_current_period_constraints_match(section, table, lane, absolute)):
                    failures.append("FLOW_ANCHOR_QUARTER_CAPTION_ALONE_DOES_NOT_PROVE_DURATION")
                    continue
                current_period = absolute[0]
                months = 12 if current_period[0] == "ANNUAL_YEAR" else current_period[2] * 3
                endpoint = date(current_period[1], months, {3: 31, 6: 30, 9: 30, 12: 31}[months])
                current.append({"printed_months": months, "printed_end_date": endpoint.isoformat()})
                evidence = {
                    "source_lane_keys": canonical_clone_v1(keys),
                    "money_column_ordinals": canonical_clone_v1(lane["money_column_ordinals"]),
                    "columns_exact": canonical_clone_v1(table["columns"]),
                    "printed_duration_lengths": _printed_duration_lengths(
                        table, lane["money_column_ordinals"], section=section),
                    "intrinsic_absolute_sibling_evidence": canonical_clone_v1(sibling) if intrinsic_sibling else None,
                    "resolved_source_duration_semantics": canonical_clone_v1(absolute),
                    "duration_origin": "INDEPENDENT_SAME_TABLE_ABSOLUTE_HEADERS_NOT_REPORT_QUARTER",
                    "relative_year_inference_used": False,
                    "rule": "OWNED_REPORT_ENDPOINT_CORROBORATES_INDEPENDENT_ABSOLUTE_SELECTED_HEADER_PAIR",
                }
                quarter_header_evidence = {**evidence, "receipt_id":
                    "gjitfav1:quarter-caption-absolute-header-duration:" + canonical_json_sha256_v1(evidence)}
            else:
                failures.append("FLOW_ANCHOR_QUARTER_CAPTION_ALONE_DOES_NOT_PROVE_DURATION")
        if not current or any(not same_typed_json_v1(item, current[0]) for item in current[1:]):
            failures.append("FLOW_ANCHOR_CURRENT_DURATION_ASSERTIONS_NOT_UNIQUE")
        owned_current = current[0] if current else None
        periods = None
        if owned_current is not None and comparative_period is not None:
            resolved = []
            for printed in (owned_current, comparative_period):
                end = date.fromisoformat(printed["printed_end_date"])
                months = printed["printed_months"]
                if months not in {3, 6, 9, 12} or months != end.month or (end + timedelta(days=1)).day != 1:
                    failures.append("FLOW_POLICY_PRINTED_PERIOD_NOT_COMPLETE_SUPPORTED_YTD_DURATION")
                else:
                    resolved.append(["ANNUAL_YEAR", end.year] if months == 12 else ["SOURCE_YTD_QUARTER", end.year, months // 3])
            if len(resolved) == 2:
                if resolved[0][0] != resolved[1][0] or resolved[0][2:] != resolved[1][2:] or resolved[0][1] <= resolved[1][1]:
                    failures.append("FLOW_POLICY_CURRENT_COMPARATIVE_DURATION_NOT_COMPATIBLE")
                else:
                    periods = resolved
        lane = source["lane_axis"]
        ordinals = lane.get("money_column_ordinals") or []
        if (not lane.get("complete") or len(ordinals) != 2 or len(set(ordinals)) != 2
                or any(type(ordinal) is not int or ordinal < 1 or ordinal > len(table["columns"])
                       or table["columns"][ordinal - 1]["value_kind"] != "MONEY" for ordinal in ordinals)):
            failures.append("FLOW_ANCHOR_MONEY_AXIS_NOT_COMPLETE")
            headers = None
        else:
            headers = [_recognition_printed_text(" ".join(table["columns"][ordinal - 1]["header_path_exact"])) for ordinal in ordinals]
            suffix = r"(?: (?:trieu dong|trieu vnd|vnd|dong))?"
            literal_ky = _relative_flow_column_paths(table, lane) is not None
            literal_nam = all(re.fullmatch(r"nam " + token + r"(?: trinh bay lai)?" + suffix + r"(?: trinh bay lai)?", header or "") is not None
                              for token, header in zip(("nay", "truoc"), headers, strict=True))
            absolute = source["absolute_duration_semantics"]
            if not (literal_ky or (literal_nam and periods is not None and periods[0][1] == periods[1][1] + 1)
                    or (absolute is not None and same_typed_json_v1(absolute, periods))):
                failures.append("FLOW_ANCHOR_LITERAL_RELATIVE_OR_EXACT_ABSOLUTE_AXIS_REQUIRED")
            if absolute is not None and not same_typed_json_v1(absolute, periods):
                failures.append("FLOW_ANCHOR_ABSOLUTE_AXIS_CONTRADICTS_PRINTED_POLICY")
        local_surfaces, ancestors, local_failures = [], [], []
        if periods is not None and headers is not None:
            local_surfaces, ancestors, local_failures = _comparative_flow_local_surface_census(section, table, lane, periods)
            failures.extend(local_failures)
            anchor_scope = _note_report_scope_receipt(
                section, table, source_paths=[*[column["header_path_exact"] for column in table["columns"]],
                                               *ancestors, [item["source_exact"] for item in local_surfaces],
                                               _comparative_flow_scope_row_labels(table)],
                document_scope=document_scope,
            )
        anchor_scope_reasons = []
        if (anchor_scope["conflict"] or anchor_scope["local_entity_qualifiers"] or anchor_scope["report_scope"] is None
                or anchor_scope["report_scope"] != document_scope.get("report_scope")
                or document_scope["entity_override_present"] or document_scope["ambiguous_scope_caption_present"]):
            anchor_scope_reasons.append("FLOW_ANCHOR_REPORT_POPULATION_NOT_PROVEN")
            scope_reasons.extend(anchor_scope_reasons)
        if periods is not None and not failures:
            current_periods.append(periods)
        anchors.append({"locator": canonical_clone_v1(locator), "statement_type": source["statement_type"],
                        "source_inventory_entry_sha256": canonical_json_sha256_v1(source),
                        "original_page_json_sha256": source["original_page_json_sha256"],
                        "original_section_json_sha256": source["original_section_json_sha256"],
                        "original_table_json_sha256": source["original_table_json_sha256"],
                        "captions_exact": canonical_clone_v1(source["captions_exact"]), "eligible_captions_exact": canonical_clone_v1(eligible),
                        "owned_current_period_constraints": canonical_clone_v1(constraints), "columns_exact": canonical_clone_v1(source["columns_exact"]),
                        "raw_lane_axis": canonical_clone_v1(lane), "header_surfaces_printed": headers,
                        "scope_receipt": canonical_clone_v1(anchor_scope), "owned_current_duration": owned_current,
                        **({"quarter_caption_absolute_header_duration_evidence": quarter_header_evidence}
                           if quarter_header_evidence is not None else {}),
                        "local_period_surface_census": local_surfaces,
                        "resolved_source_duration_semantics": periods, "period_complete": not failures,
                        "complete": not failures and not anchor_scope_reasons,
                        "reasons": sorted(set([*failures, *anchor_scope_reasons]))})
        period_reasons.extend(failures)
    if {source["statement_type"] for source in sources} != {"INCOME_STATEMENT", "CASH_FLOW"}:
        period_reasons.append("INDEPENDENT_CURRENT_INCOME_AND_CASH_FLOW_ANCHORS_REQUIRED")
    if not current_periods or any(not same_typed_json_v1(item, current_periods[0]) for item in current_periods[1:]):
        period_reasons.append("ALL_CURRENT_FLOW_ANCHORS_MUST_OWN_THE_SAME_PRINTED_DURATION")
    period_complete, scope_complete = not period_reasons, not scope_reasons
    reasons.extend(period_reasons)
    reasons.extend(scope_reasons)
    material = {**common, "complete": not reasons, "status": "ALGORITHM_HOLD" if reasons else "PASS_AUTHENTICATED_PRINTED_DOCUMENT_COMPARATIVE_FLOW_POLICY",
                "period_evidence_complete": period_complete, "scope_complete": scope_complete,
                "resolved_source_duration_semantics": canonical_clone_v1(current_periods[0]) if not reasons else None,
                "printed_period_evidence": canonical_clone_v1(current_periods[0]) if period_complete else None,
                "selected_page_axis": page_axis, "policy_source_receipts": policies, "anchor_source_receipts": anchors,
                "all_typed_period_sources_included": True, "continuations_used_as_votes": False,
                "reasons": sorted(set(reasons)),
                "rule": "EXPLICIT_PRINTED_COMPARATIVE_FLOW_POLICY_AND_EVERY_INDEPENDENT_OWNED_CURRENT_TYPED_FLOW_ANCHOR_NO_YEAR_MINUS_ONE"}
    return {**material, "receipt_id": "gjitfav1:document-comparative-flow-policy:" + canonical_json_sha256_v1(material)}


def _document_annual_period_receipt(sources: Sequence[Mapping[str, Any]], document_scope: Mapping[str, Any]) -> dict[str, Any]:
    """Independent owned annual anchors; continuations cannot vote away gaps."""
    scope_sources = {canonical_json_sha256_v1(source["locator"]): source for source in document_scope["sources"]}
    anchors, reasons = [], []
    if (not document_scope["document_identity_unique"] or document_scope["report_scope"] is None
            or document_scope["entity_override_present"] or document_scope["ambiguous_scope_caption_present"]):
        reasons.append("DOCUMENT_ANNUAL_REPORT_POPULATION_NOT_PROVEN")
    for source in sorted(sources, key=lambda item: (item["locator"]["selected_page_ordinal"],
                                                  int(item["locator"]["section_id"][1:]), int(item["locator"]["table_id"][1:]))):
        caption_source = scope_sources.get(canonical_json_sha256_v1(source["locator"]))
        eligible = caption_source["eligible_captions_exact"] if caption_source is not None else []
        relative = source["owned_relative_year_duration_evidence"]
        periods = relative["resolved_source_duration_semantics"] if relative is not None else None
        scope = source["scope_receipt"]
        failures = []
        if not eligible:
            failures.append("STATEMENT_TYPE_NOT_AUTHENTICATED_BY_OWNED_CAPTION")
        if (scope["conflict"] or scope["local_entity_qualifiers"] or scope["report_scope"] is None
                or scope["report_scope"] != document_scope["report_scope"]):
            failures.append("ANNUAL_ANCHOR_REPORT_POPULATION_NOT_PROVEN")
        if (periods is None or any(period[0] != "ANNUAL_YEAR" for period in periods)
                or periods[0][1] != periods[1][1] + 1):
            failures.append("ANNUAL_ANCHOR_INDEPENDENT_OWNED_YEAR_DURATION_NOT_PROVEN")
        anchors.append({"locator": canonical_clone_v1(source["locator"]), "statement_type": source["statement_type"],
                        "eligible_captions_exact": canonical_clone_v1(eligible), "captions_exact": canonical_clone_v1(source["captions_exact"]),
                        "original_page_json_sha256": source["original_page_json_sha256"],
                        "original_table_json_sha256": source["original_table_json_sha256"],
                        "source_inventory_entry_sha256": canonical_json_sha256_v1(source),
                        "owned_relative_year_duration_evidence": canonical_clone_v1(relative),
                        "scope_receipt": canonical_clone_v1(scope), "complete": not failures, "reasons": failures})
        reasons.extend(failures)
    if {source["statement_type"] for source in sources} != {"INCOME_STATEMENT", "CASH_FLOW"}:
        reasons.append("INDEPENDENT_INCOME_AND_CASH_FLOW_ANNUAL_ANCHORS_REQUIRED")
    complete_periods = [item["owned_relative_year_duration_evidence"]["resolved_source_duration_semantics"]
                        for item in anchors if item["complete"]]
    if not complete_periods or any(not same_typed_json_v1(periods, complete_periods[0]) for periods in complete_periods[1:]):
        reasons.append("DOCUMENT_ANNUAL_SOURCE_PERIOD_CONSENSUS_NOT_PROVEN")
    material = {"complete": not reasons, "status": "ALGORITHM_HOLD" if reasons else "PASS_INDEPENDENT_OWNED_DOCUMENT_ANNUAL_PERIOD",
                "origin": "INDEPENDENT_OWNED_INCOME_AND_CASH_FLOW_ANNUAL_CONSENSUS",
                "resolved_source_duration_semantics": canonical_clone_v1(complete_periods[0]) if not reasons else None,
                "anchor_source_receipts": anchors, "document_report_scope_receipt_id": document_scope["receipt_id"],
                "all_typed_period_sources_included": True, "continuations_used_as_votes": False,
                "reasons": sorted(set(reasons)), "rule": "EVERY_CAPTION_AUTHENTICATED_INCOME_AND_CASH_FLOW_SOURCE_OWNS_THE_SAME_ANNUAL_YEAR_PAIR_AND_REPORT_SCOPE"}
    return {**material, "receipt_id": "gjitfav1:document-annual-period:" + canonical_json_sha256_v1(material)}


def _note_annual_period_inheritance_receipt(
    section: Mapping[str, Any], table: Mapping[str, Any], lane: Mapping[str, Any], *,
    locator: Mapping[str, Any], document_period_inventory: Mapping[str, Any], compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Source-visible NOTE veto census, never an authority from matching values."""
    document = document_period_inventory["document_annual_period_receipt"]
    reasons = []
    if not document["complete"]:
        reasons.append("AUTHENTICATED_DOCUMENT_ANNUAL_PERIOD_ABSENT")
    paths = _relative_year_column_paths(table, lane)
    if paths is None:
        reasons.append("NOTE_LITERAL_ORDERED_RELATIVE_YEAR_LABELS_REQUIRED")
    owner = section.get("content_kind") == "FINANCIAL_NOTE" and _supplemental_owner_matches(section, table, compiled_specs=compiled_specs)
    if not owner:
        reasons.append("NOTE_EXPLICIT_TAX_OWNER_NOT_PROVEN_FOR_ANNUAL_INHERITANCE")
    surfaces = [{"kind": "SECTION_TITLE", "ordinal": 1, "source_exact": section.get("title_exact")},
                {"kind": "TABLE_TITLE", "ordinal": 1, "source_exact": table.get("title_exact")}]
    for ordinal in lane.get("money_column_ordinals") or []:
        surfaces.extend({"kind": "MONEY_HEADER", "column_ordinal": ordinal, "ordinal": index, "source_exact": value}
                        for index, value in enumerate(table["columns"][ordinal - 1]["header_path_exact"], 1))
    if len(section.get("tables") or []) == 1:
        surfaces.extend({"kind": "OWNED_NARRATIVE", "ordinal": index, "source_exact": value}
                        for index, value in enumerate(section.get("narratives_exact") or [], 1))
    ancestors = [row.get("hierarchy_path_exact", [])[:-1]
                 if row.get("hierarchy_path_exact") and _without_leading_ordinal(_normalized(row["hierarchy_path_exact"][-1])) == _without_leading_ordinal(_normalized(row.get("label_exact")))
                 else row.get("hierarchy_path_exact", []) for row in table["rows"]]
    for ordinal, values in enumerate(ancestors, 1):
        surfaces.extend({"kind": "SOURCE_ROW_ANCESTOR", "row_ordinal": ordinal, "ordinal": index, "source_exact": value}
                        for index, value in enumerate(values, 1))
    months = r"(?:\d+|mot|hai|ba|bon|nam|sau|bay|tam|chin|muoi|muoi mot|muoi hai) thang\b(?! \d)"
    periods = document["resolved_source_duration_semantics"]
    constraints = _owned_current_period_constraints(section, table)
    for surface in surfaces:
        normalized = _normalized(surface["source_exact"])
        without_calendar_dates = re.sub(r"\b(?:ngay )?\d{1,2} thang (?:0?[1-9]|1[0-2])(?: nam)? \d{4}\b", "", normalized)
        nonannual = (re.search(r"\b(?:(?:quy|qui) (?:i|ii|iii|iv|1|2|3|4|nay|truoc)|trong quy|quarter|q ?(?:i|ii|iii|iv|1|2|3|4)|giua nien do|interim)\b", normalized) is not None
                     or "luy ke" in normalized or "year to date" in normalized or "cumulative" in normalized
                     or re.search(r"\b" + months, normalized) is not None
                     or re.search(r"\b(?:0?[1-9]|1[0-2]) thang (?=\d{4}\b)", normalized) is not None
                     or re.search(r"\bthang (?:0?[1-9]|1[0-2])(?: nam)? \d{4}\b", without_calendar_dates) is not None
                     or re.search(r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve) months?\b", normalized) is not None
                     or re.search(r"\btu ngay\b.*\bden\b", normalized) is not None
                     or re.search(r"\btu(?: ngay)? \d{1,2}(?: thang)? \d{1,2}(?: nam)? \d{4}\b.*\bden(?: ngay)? \d{1,2}(?: thang)? \d{1,2}(?: nam)? \d{4}\b", normalized) is not None
                     or re.search(r"\btu(?: ngay)? \d{4} \d{1,2} \d{1,2}\b.*\bden(?: ngay)? \d{4} \d{1,2} \d{1,2}\b", normalized) is not None
                     or re.search(r"\bfor (?:the )?(?:year|period|quarter)(?: ended| ending| \d{4})\b", normalized) is not None)
        local_years = re.findall(r"\b(?:cho |trong )?nam(?: tai chinh)? (\d{4})\b", normalized) if surface["kind"] != "OWNED_NARRATIVE" else []
        conflicting_year = bool(periods and any(int(year) != periods[0][1] for year in local_years))
        veto = nonannual or conflicting_year
        surface["non_annual_or_ambiguous_period_present"] = nonannual
        surface["conflicting_local_year_present"] = conflicting_year
        surface["disposition"] = "LOCAL_PERIOD_CONTEXT_VETO" if veto else "RETAINED_SOURCE_SURFACE_NOT_PERIOD_AUTHORITY"
        if veto:
            reasons.append("NOTE_LOCAL_NON_ANNUAL_OR_CONFLICTING_PERIOD_CONTEXT")
    if constraints and (periods is None or not _owned_current_period_constraints_match(section, table, lane, periods)):
        reasons.append("NOTE_OWNED_CURRENT_PERIOD_ASSERTION_NOT_COMPATIBLE_WITH_DOCUMENT_ANNUAL_PERIOD")
    scope = _note_report_scope_receipt(section, table, source_paths=[*(paths or []), *ancestors],
                                      document_scope=document_period_inventory["document_report_scope_receipt"])
    if (scope["conflict"] or scope["local_entity_qualifiers"] or scope["report_scope"] is None
            or scope["report_scope"] != document_period_inventory["document_report_scope_receipt"]["report_scope"]):
        reasons.append("NOTE_DOCUMENT_ANNUAL_REPORT_POPULATION_NOT_PROVEN")
    material = {"complete": not reasons, "status": "ALGORITHM_HOLD" if reasons else "PASS_AUTHENTICATED_DOCUMENT_ANNUAL_PERIOD",
                "origin": "INHERITED_AUTHENTICATED_DOCUMENT_ANNUAL_PERIOD", "locator": canonical_clone_v1(locator),
                "original_section_json_sha256": canonical_json_sha256_v1(section), "original_table_json_sha256": canonical_json_sha256_v1(table),
                "money_column_ordinals": canonical_clone_v1(lane.get("money_column_ordinals")), "header_paths_exact": paths,
                "explicit_tax_owner_caption_matches": owner, "local_period_surface_census": surfaces,
                "owned_current_period_constraints": constraints, "scope_receipt": scope,
                "document_annual_period_receipt": canonical_clone_v1(document),
                "resolved_source_duration_semantics": canonical_clone_v1(periods) if not reasons else None,
                "comparative_year_origin": "DERIVED_RELATIVE_YEAR_SEMANTICS_NOT_PRINTED_ABSOLUTE_YEAR",
                "amounts_used_as_authority": False, "source_period_keys_modified": False, "start_dates_inferred": False,
                "reasons": sorted(set(reasons)), "rule": "EXPLICIT_TAX_NOTE_RELATIVE_YEAR_LABELS_WITH_COMPLETE_INDEPENDENT_DOCUMENT_ANNUAL_PERIOD_AND_EXHAUSTIVE_LOCAL_VETO_CENSUS"}
    return {**material, "receipt_id": "gjitfav1:note-inherited-annual-period:" + canonical_json_sha256_v1(material)}


def _relative_flow_column_paths(table: Mapping[str, Any], lane: Mapping[str, Any]) -> list[list[str]] | None:
    """Recognize literal Kỳ labels without assigning a date or subtracting a year."""
    if (not lane.get("complete") or lane.get("source_lane_keys") != [
            ["SEMANTIC_ALIAS", "CURRENT_PERIOD"], ["SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"]]):
        return None
    ordinals = lane.get("money_column_ordinals") or []
    if len(ordinals) != 2:
        return None
    paths = [table["columns"][ordinal - 1]["header_path_exact"] for ordinal in ordinals]
    for path, token in zip(paths, ("nay", "truoc"), strict=True):
        if not path or any(type(value) is not str for value in path):
            return None
        printed = _recognition_printed_text(" ".join(path))
        if printed is None or re.fullmatch(
            r"ky " + token + r"(?: \(trinh bay lai\))?(?: (?:trieu dong|trieu vnd|vnd|dong))?(?: \(trinh bay lai\))?",
            printed,
        ) is None or printed.count("trinh bay lai") > 1:
            return None
    return canonical_clone_v1(paths)


def _comparative_flow_local_surface_census(
    section: Mapping[str, Any], table: Mapping[str, Any], lane: Mapping[str, Any], periods: Any,
) -> tuple[list[dict[str, Any]], list[list[Any]], list[str]]:
    """Veto local contrary assertions, including ancestors of unmapped source rows.

    This census supplies no period authority. The independent document receipt
    must already own both printed durations. Unknown period syntax is a hold.
    """
    surfaces = [{"kind": "SECTION_TITLE", "ordinal": 1, "source_exact": section.get("title_exact")},
                {"kind": "TABLE_TITLE", "ordinal": 1, "source_exact": table.get("title_exact")}]
    for ordinal in lane.get("money_column_ordinals") or []:
        surfaces.extend({"kind": "MONEY_HEADER", "column_ordinal": ordinal, "ordinal": index, "source_exact": value}
                        for index, value in enumerate(table["columns"][ordinal - 1]["header_path_exact"], 1))
    surfaces.extend({"kind": "OWNED_NARRATIVE" if len(section.get("tables") or []) == 1 else "AMBIGUOUSLY_OWNED_NARRATIVE",
                     "ordinal": index, "source_exact": value}
                    for index, value in enumerate(section.get("narratives_exact") or [], 1))
    ancestors = [row.get("hierarchy_path_exact", [])[:-1]
                 if row.get("hierarchy_path_exact") and _without_leading_ordinal(_normalized(row["hierarchy_path_exact"][-1])) == _without_leading_ordinal(_normalized(row.get("label_exact")))
                 else row.get("hierarchy_path_exact", []) for row in table["rows"]]
    for ordinal, values in enumerate(ancestors, 1):
        surfaces.extend({"kind": "SOURCE_ROW_ANCESTOR", "row_ordinal": ordinal, "ordinal": index, "source_exact": value}
                        for index, value in enumerate(values, 1))
    surfaces.extend({"kind": "STRUCTURAL_OR_BLANK_ROW_LABEL", "row_ordinal": ordinal,
                     "ordinal": 1, "source_exact": row.get("label_exact")}
                    for ordinal, row in enumerate(table["rows"], 1)
                    if row.get("row_kind") == "GROUP"
                    or not any(row["values_exact"][column - 1] is not None and row["values_exact"][column - 1] != ""
                               for column in lane.get("money_column_ordinals") or []))
    current = periods[0] if periods else None
    year = current[1] if current else None
    months = (12 if current[0] == "ANNUAL_YEAR" else current[2] * 3) if current else None
    end = date(year, months, {3: 31, 6: 30, 9: 30, 12: 31}[months]) if current else None
    month_words = {"mot": 1, "hai": 2, "ba": 3, "bon": 4, "nam": 5, "sau": 6,
                   "bay": 7, "tam": 8, "chin": 9, "muoi": 10, "muoi mot": 11, "muoi hai": 12}
    month_pattern = r"\b(\d+|muoi mot|muoi hai|mot|hai|ba|bon|nam|sau|bay|tam|chin|muoi) thang\b"
    quarter_numbers = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "1": 1, "2": 2, "3": 3, "4": 4}
    reasons = []
    header_constraint = _owned_absolute_flow_header_constraint(section, table)
    header_pair = header_constraint["source_header_pair_evidence"] if header_constraint is not None else None
    if header_pair is not None and not same_typed_json_v1(header_pair["money_column_ordinals"], lane.get("money_column_ordinals")):
        header_constraint, header_pair = None, None
    ytd_siblings = _printed_ytd_sibling_period_evidence(section, table, lane)
    if ytd_siblings is not None:
        quarter = ytd_siblings["quarter"]
        absolute = ytd_siblings["intrinsic_absolute_periods"]
        if (type(periods) is not list or len(periods) != 2
                or any(type(period) is not list or len(period) not in {2, 3}
                       or type(period[1]) is not int or not 1 <= period[1] <= 9999 for period in periods)
                or periods[0][1] <= periods[1][1]
                or any(not same_typed_json_v1(period, ["ANNUAL_YEAR", period[1]] if quarter == 4
                                             else ["SOURCE_YTD_QUARTER", period[1], quarter]) for period in periods)
                or (absolute is not None and not same_typed_json_v1(absolute, periods))):
            ytd_siblings = None
    for surface in surfaces:
        selected = (lane.get("money_column_ordinals") or []).index(surface["column_ordinal"]) if surface["kind"] == "MONEY_HEADER" else 0
        expected = periods[selected] if periods else None
        year = expected[1] if expected else None
        months = (12 if expected[0] == "ANNUAL_YEAR" else expected[2] * 3) if expected else None
        end = date(year, months, {3: 31, 6: 30, 9: 30, 12: 31}[months]) if expected else None
        raw = surface["source_exact"]
        normalized = _normalized(raw)
        printed = _recognition_printed_text(raw)
        owned_ytd_header = False
        if ytd_siblings is not None and surface["kind"] == "MONEY_HEADER" and expected is not None:
            quarter = ytd_siblings["quarter"]
            expected_shape = ["ANNUAL_YEAR", year] if quarter == 4 else ["SOURCE_YTD_QUARTER", year, quarter]
            absolute = ytd_siblings["intrinsic_absolute_periods"]
            column = ytd_siblings["cumulative_columns_exact"][selected]
            path = column["header_path_exact"]
            owned_ytd_header = bool(
                same_typed_json_v1(expected, expected_shape)
                and (absolute is None or same_typed_json_v1(absolute[selected], expected))
                and ytd_siblings["money_column_ordinals"][selected + 2] == surface["column_ordinal"]
                and path[surface["ordinal"] - 1] == raw
            )
            if owned_ytd_header:
                printed = _recognition_printed_text(" ".join(raw.replace("\\n", "\n").split()))
                surface["owned_ytd_sibling_header_evidence"] = {
                    "printed_ytd_sibling_receipt_id": ytd_siblings["receipt_id"],
                    "column_ordinal": surface["column_ordinal"], "header_path_ordinal": surface["ordinal"],
                    "source_path_exact": canonical_clone_v1(path), "source_exact": raw,
                    "source_sha256": sha256(raw.encode("utf-8")).hexdigest(),
                    "independently_resolved_source_period": canonical_clone_v1(expected),
                    "printed_absolute_year": None if absolute is None else absolute[selected][1],
                }
                surface["year_consumed_from_owned_header"] = bool(
                    absolute is not None and re.search(r"(?<!\S)[0-9]{4}(?!\S)", raw.replace("\\n", "\n"))
                )
        range_constraint = _owned_flow_date_range_caption_constraint(section, source_kind=surface["kind"], source_exact=raw)
        range_caption = bool(
            range_constraint is not None and range_constraint["supported"] and end is not None
            and range_constraint["printed_start_date"] == date(year, 1, 1).isoformat()
            and range_constraint["printed_end_date"] == end.isoformat()
            and range_constraint["printed_months"] == months
        )
        surface["finite_owned_date_range_flow_caption"] = range_caption
        if range_caption:
            # Normalize serialized line breaks only after the same whole raw
            # caption has passed the finite source-owned range parser.
            printed = _recognition_printed_text(raw.replace("\\n", "\n"))
            surface["owned_date_range_caption_evidence"] = canonical_clone_v1(range_constraint["source_date_range_evidence"])
        report_quarter = _owned_flow_report_quarter_constraint(section, source_kind=surface["kind"], source_exact=raw)
        endpoint_caption = bool(
            report_quarter is not None and report_quarter["supported"] and end is not None
            and report_quarter["printed_year"] == year
            and report_quarter["printed_reporting_quarter"] * 3 == months
        )
        surface["finite_owned_reporting_quarter_endpoint_caption"] = endpoint_caption
        if endpoint_caption:
            surface["owned_report_quarter_caption_evidence"] = canonical_clone_v1(report_quarter["source_report_quarter_evidence"])
        note_report_quarter = _owned_note_report_quarter_constraint_v1(
            section, source_kind=surface["kind"], source_exact=raw,
        )
        if note_report_quarter is not None:
            note_endpoint_caption = bool(
                note_report_quarter["supported"] and end is not None
                and note_report_quarter["printed_year"] == year
                and note_report_quarter["printed_reporting_quarter"] * 3 == months
            )
            surface["finite_owned_note_reporting_quarter_endpoint_caption"] = note_endpoint_caption
            if note_endpoint_caption:
                # Only the exact whole accepted title owns this layout. No
                # ancestor, narrative, unknown suffix or duration is waived.
                printed = _recognition_printed_text(" ".join(
                    raw.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\r", "\n").split(),
                ))
                endpoint_caption = True
                surface["owned_note_report_quarter_caption_evidence"] = canonical_clone_v1(
                    note_report_quarter["source_note_report_quarter_evidence"],
                )
        header_pair_interim_caption = False
        if (header_constraint is not None and surface["kind"] in {"SECTION_TITLE", "TABLE_TITLE"}
                and months in {3, 6, 9} and header_constraint["printed_months"] == months
                and header_constraint["printed_end_date"] == end.isoformat()):
            # Serialized line breaks are finite caption furniture, not a
            # general-purpose removal of unknown characters or assertions.
            caption_printed = _recognition_printed_text(raw.replace("\\n", "\n")) if type(raw) is str else None
            title = {"INCOME_STATEMENT": "ket qua hoat dong", "CASH_FLOW": "luu chuyen tien te"}[section["statement_type"]]
            method = r"(?: \(phuong phap (?:truc|gian) tiep\))?" if section["statement_type"] == "CASH_FLOW" else ""
            bare_caption = r"bao cao " + title + r"(?: rieng| hop nhat)? giua nien do(?: \(tiep theo\))?" + method
            header_pair_interim_caption = bool(caption_printed is not None and re.fullmatch(bare_caption, caption_printed))
            if header_pair_interim_caption:
                printed = caption_printed
                surface["owned_header_pair_caption_evidence"] = {
                    "header_pair_receipt_id": header_pair["receipt_id"], "source_exact": raw,
                    "printed_months": months, "printed_end_date": end.isoformat(),
                    "rule": "WHOLE_TYPED_INTERIM_CAPTION_WITH_SAME_TABLE_COMPLETE_DATED_DURATION_HEADER_PAIR",
                }
        failures, dates = [], []
        temporal = bool(re.search(r"\b(?:quy|qui|quarter|months?|ended|ending|thang|ngay|nien do|tai khoa|ban nien|nua (?:dau|cuoi) nam|\d{4})\b", normalized)
                        or re.search(r"\b(?:cho|trong) (?:nam|ky|giai doan)\b", normalized)
                        or re.match(r"(?:\d+(?:\.\d+)*[.)]?\s+)?(?:nam|ky|giai doan)\b", printed or normalized))
        narrative_starter = (
            r"(?:cho |trong |ky\b|quy\b|giai doan\b|nam\b|nien do\b|tai khoa\b|ban nien\b|nua (?:dau|cuoi) nam\b|"
            r"luy ke|tu ngay |bao cao |thuyet minh bao cao |"
            r"(?:\d+|muoi mot|muoi hai|mot|hai|ba|bon|nam|sau|bay|tam|chin|muoi) thang\b|"
            r"for (?:the )?(?:period|year|quarter|(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve) months?)\b|"
            r"(?:(?:reporting|accounting) )?period (?:ended|ending)\b|(?:fiscal|financial) year\b|"
            r"year (?:ended|ending|to date|\d{4})\b|quarter\b|q(?:iii|ii|iv|i|[1-4])\b|ytd\b)"
        )
        reporting_narrative = any(re.match(narrative_starter, _normalized(line))
                                  for line in re.split(r"\r\n|\r|\n|\\n", raw or ""))
        explicit_history = bool(re.match(r"thong tin lich su\b", normalized))
        historical_narrative = surface["kind"].endswith("NARRATIVE") and (explicit_history or not reporting_narrative)
        if historical_narrative:
            surface["printed_dates"] = []
            surface["reasons"] = []
            surface["disposition"] = "RETAINED_NARRATIVE_NOT_OWNED_REPORTING_PERIOD_AUTHORITY"
            continue
        if temporal and surface["kind"] == "AMBIGUOUSLY_OWNED_NARRATIVE":
            failures.append("LOCAL_REPORTING_ASSERTION_OWNERSHIP_AMBIGUOUS")
        if temporal and (printed is None or re.search(r"\b(?:khong|not|ngoai tru|except)\b", normalized)):
            failures.append("UNREVIEWED_OR_NEGATED_LOCAL_PERIOD_ASSERTION")
        if temporal and printed is not None:
            if any(not (character.isalnum() or character.isspace() or character in ".,:/()-") for character in printed):
                failures.append("UNREVIEWED_LOCAL_PERIOD_ANNOTATION")
            allowed_parentheticals = {"tiep theo", "trinh bay lai"}
            if (header_pair_interim_caption or range_caption) and section["statement_type"] == "CASH_FLOW":
                allowed_parentheticals.update({"phuong phap truc tiep", "phuong phap gian tiep"})
            if any(value not in allowed_parentheticals for value in re.findall(r"\(([^()]*)\)", printed)):
                failures.append("UNREVIEWED_LOCAL_PERIOD_PARENTHETICAL")
            without_parentheticals = re.sub(r"\((?:" + "|".join(sorted(allowed_parentheticals)) + r")\)", "", printed)
            if "(" in without_parentheticals or ")" in without_parentheticals:
                failures.append("UNBALANCED_OR_UNREVIEWED_LOCAL_PERIOD_PARENTHETICAL")
        # Every component of this exact selected header is owned by the fresh
        # whole-four-header finite grammar and matches an independently supplied
        # period. This consumes only its known YTD/year/currency furniture, even
        # when split across path components; never a caption, row or narrative.
        # Relative labels supply no absolute year, scope, unit or amount authority.
        # A whole verified report-quarter caption owns only this surface's
        # endpoint/year/furniture. It is not a three-month-duration assertion
        # and grants no waiver to a NOTE ancestor or any other source surface.
        remainder = "" if owned_ytd_header or endpoint_caption else printed or ""
        # Whole printed dates are removed before looking for month counts;
        # '30 tháng 6 năm ...' must not become a 30-month duration.
        date_pattern = r"\b(?:ngay )?(\d{1,2}) (?:thang )?(\d{1,2}) nam (\d{4})\b|\b(\d{1,2})/(\d{1,2})/(\d{4})\b|\b(\d{4})-(\d{2})-(\d{2})\b"
        if header_pair is not None and surface["kind"] == "MONEY_HEADER":
            header = header_pair["headers"][selected]
            if (header["column_ordinal"] == surface["column_ordinal"]
                    and header["source_path_exact"][surface["ordinal"] - 1] == raw):
                # Dotted dates are recognized only inside the exact whole
                # header already parsed above, never on arbitrary source rows.
                dotted = r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b"
                date_pattern += "|" + dotted
                if re.search(dotted, remainder):
                    surface["owned_header_pair_date_evidence"] = {
                        "header_pair_receipt_id": header_pair["receipt_id"],
                        "column_ordinal": header["column_ordinal"], "header_path_ordinal": surface["ordinal"],
                        "source_path_exact": canonical_clone_v1(header["source_path_exact"]),
                        "printed_end_date": header["printed_end_date"],
                    }
        for matched in re.finditer(date_pattern, remainder):
            try:
                if matched[1] is not None:
                    observed = date(int(matched[3]), int(matched[2]), int(matched[1]))
                elif matched[4] is not None:
                    observed = date(int(matched[6]), int(matched[5]), int(matched[4]))
                elif matched[7] is not None:
                    observed = date(int(matched[7]), int(matched[8]), int(matched[9]))
                else:
                    observed = date(int(matched[12]), int(matched[11]), int(matched[10]))
                dates.append(observed)
            except ValueError:
                failures.append("INVALID_LOCAL_PRINTED_DATE")
        remainder = re.sub(date_pattern, " ", remainder)
        range_asserted = not owned_ytd_header and bool(re.search(
            r"\btu(?: ngay)?\b.+\b(?:den|toi)\b|\bfrom\b.+\b(?:to|through)\b", printed or ""))
        if range_asserted:
            if end is None or dates != [date(year, 1, 1), end]:
                failures.append("LOCAL_PRINTED_DATE_RANGE_NOT_COMPATIBLE")
        elif len(dates) > 1 or any(observed != end for observed in dates):
            failures.append("LOCAL_PRINTED_DATE_NOT_CURRENT_ENDPOINT")
        for matched in re.finditer(month_pattern, remainder):
            count = int(matched[1]) if matched[1].isdigit() else month_words[matched[1]]
            if count != months:
                failures.append("LOCAL_PRINTED_DURATION_NOT_COMPATIBLE")
        quarters = re.findall(r"\b(?:quy|qui|q) (i|ii|iii|iv|1|2|3|4)\b", remainder)
        if quarters and (months != 3 or any(quarter_numbers[value] * 3 != months for value in quarters)):
            failures.append("LOCAL_QUARTER_CANNOT_RELABEL_CUMULATIVE_FLOW")
        if re.search(r"\b(?:quarter|months?|for (?:the )?(?:year|period)|trong quy|quy (?:nay|truoc)|qui (?:nay|truoc))\b", remainder):
            failures.append("UNREVIEWED_LOCAL_PERIOD_SYNTAX")
        if re.search(r"\bthang (?:0?[1-9]|1[0-2])(?: nam)? \d{4}\b", remainder):
            failures.append("PARTIAL_LOCAL_CALENDAR_DATE_NOT_DURATION")
        if any(int(value) != year for value in re.findall(r"\b\d{4}\b", remainder)):
            failures.append("LOCAL_PRINTED_YEAR_NOT_CURRENT_PERIOD")
        if months != 12 and re.search(r"\b(?:cho nam|nam tai chinh)\b", remainder):
            failures.append("LOCAL_ANNUAL_ASSERTION_CANNOT_RELABEL_INTERIM_FLOW")
        # Consume finite temporal fragments. A matching endpoint/year cannot
        # hide an additional unknown period or partial date in the same source.
        unconsumed = re.sub(month_pattern, " ", remainder)
        unconsumed = re.sub(r"\b(?:quy|qui|q) (?:i|ii|iii|iv|1|2|3|4)\b", " ", unconsumed)
        unconsumed = re.sub(r"\bnam(?: tai chinh)? \d{4}\b", " ", unconsumed)
        unconsumed = re.sub(r"\bky (?:nay|truoc)\b", " ", unconsumed)
        unconsumed = re.sub(r"\bluy ke tu dau nam(?: den cuoi ky nay)?\b", " ", unconsumed)
        unconsumed = re.sub(r"\b(?:cho )?(?:ky(?: hoat dong| ke toan)?|giai doan)\s+ket thuc(?: vao)?(?: ngay)?\b", " ", unconsumed)
        unconsumed = re.sub(r"\b(?:cho )?nam tai chinh ket thuc(?: vao)?(?: ngay)?\b", " ", unconsumed)
        # 'Same day' is admitted only by the independently parsed complete
        # caption, never by this surface census searching for a nearby date.
        same_day = _owned_same_day_period_constraint(section, source_kind=surface["kind"], source_exact=raw)
        if same_day is not None and same_day["supported"]:
            unconsumed = re.sub(r"\b(?:cho )?ky ke toan\s+ket thuc cung ngay\b", " ", unconsumed)
        unconsumed = re.sub(r"\b(?:tai|vao) ngay\b", " ", unconsumed)
        if range_asserted and end is not None and dates == [date(year, 1, 1), end]:
            unconsumed = re.sub(r"\b(?:tu ngay|tu|den ngay|den|toi)\b", " ", unconsumed)
        if range_caption:
            # The whole finite caption proof owns exactly this furniture;
            # arbitrary ranges/narratives/ancestors receive no such waiver.
            unconsumed = re.sub(r"\bcho giai doan\b", " ", unconsumed, count=1)
        # Interim furniture belongs only to a whole finite, typed FLOW report
        # caption with its own matching current-duration clause. Never erase
        # bare 'niên độ' assertions on NOTE rows or unrelated narratives.
        interim_caption = header_pair_interim_caption or range_caption
        if (surface["kind"] in {"SECTION_TITLE", "TABLE_TITLE"} and printed is not None
                and section.get("content_kind") == "PRIMARY_STATEMENT" and months in {3, 6, 9}):
            title = {"INCOME_STATEMENT": "ket qua hoat dong", "CASH_FLOW": "luu chuyen tien te"}.get(section.get("statement_type"))
            counts = r"(?:\d+|muoi mot|muoi hai|mot|hai|ba|bon|nam|sau|bay|tam|chin|muoi)"
            printed_date = r"(?:\d{1,2} thang \d{1,2} nam \d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})"
            whole_caption = (r"bao cao " + (title or "UNSUPPORTED")
                             + r"(?: rieng| hop nhat)? giua nien do(?: \(tiep theo\))? "
                             + r"cho ky hoat dong " + counts + r" thang ket thuc(?: vao)? ngay " + printed_date
                             + r"(?: \(tiep theo\))?\.?")
            owned_constraints = _owned_current_period_constraints(section, table)
            interim_caption = interim_caption or bool(title and re.fullmatch(whole_caption, printed) and any(
                item["source_kind"] == surface["kind"] and item["source_exact"] == raw and item["supported"]
                and item.get("printed_months") == months and item.get("printed_end_date") == end.isoformat()
                for item in owned_constraints
            ))
        surface["finite_owned_interim_flow_caption"] = interim_caption
        if interim_caption:
            unconsumed = re.sub(r"\bgiua nien do\b", " ", unconsumed, count=1)
        if re.search(r"\b(?:ky|quy|qui|ngay|thang|giai doan|nien do|tai khoa|ban nien|nua (?:dau|cuoi)(?: nam)?|quarter|months?|ended|ending|year|period|q(?:iii|ii|iv|i|[1-4])|ytd)\b", unconsumed):
            failures.append("UNCONSUMED_LOCAL_PERIOD_ASSERTION")
        if re.search(r"\b\d{4}\b", unconsumed):
            failures.append("UNCONSUMED_LOCAL_PRINTED_YEAR")
        numbered_tax_caption = bool(
            surface["kind"] in {"SECTION_TITLE", "TABLE_TITLE"} and not temporal and printed is not None
            and re.fullmatch(
                r"[1-9][0-9]*(?:\.[1-9][0-9]*)*\.?\s+chi phi thue thu nhap doanh nghiep(?: \(tndn\))?",
                printed,
            )
        )
        # A complete, finite tax caption can own a dotted outline such as
        # '7.1.'. This is not permission to erase numeric ancestors, dates,
        # unknown annotations or extra assertions from any source surface.
        surface["finite_numbered_tax_caption_not_period_assertion"] = numbered_tax_caption
        if not numbered_tax_caption and re.search(r"\b\d{1,4}[./-]\d{1,2}(?:[./-]\d{1,4})?\b", unconsumed):
            failures.append("UNREVIEWED_LOCAL_DATE_SYNTAX")
        # Direct assertions without an owned report-caption parser must match
        # a whole finite clause, not just have removable familiar tokens.
        direct = bool(re.match(r"(?:(?:cho|trong) )?(?:ky\b|giai doan\b|nam\b|quy\b|tai ngay\b|vao ngay\b|tu ngay\b|\d)", normalized))
        direct = direct or bool(re.match(r"(?:mot|hai|ba|bon|nam|sau|bay|tam|chin|muoi)\b.*\bthang\b", normalized))
        # A numbered tax caption is not a reporting-period assertion. Keep
        # date/year/duration cues mandatory; never discard its outline number
        # or an actual numeric date to make a source period pass.
        direct = temporal and direct
        if direct and surface["kind"] != "MONEY_HEADER":
            counts = r"(?:\d+|muoi mot|muoi hai|mot|hai|ba|bon|nam|sau|bay|tam|chin|muoi)"
            printed_date = r"(?:\d{1,2} thang \d{1,2} nam \d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})"
            finite = (
                r"(?:(?:cho|trong) )?(?:(?:ky(?: hoat dong| ke toan)?|giai doan) )?" + counts + r" thang ket thuc(?: vao)? ngay " + printed_date
                + r"|nam(?: tai chinh)? \d{4}"
                + r"|(?:tai |vao )?ngay " + printed_date
                + r"|" + printed_date
                + r"|(?:cho )?quy (?:i|ii|iii|iv|1|2|3|4) nam \d{4}"
                + r"|(?:cho )?nam(?: tai chinh)? ket thuc(?: vao)? ngay " + printed_date
                + r"|tu ngay " + printed_date + r" (?:den|toi)(?: ngay)? " + printed_date
            )
            if printed is None or re.fullmatch(r"(?:" + finite + r")(?: \(tiep theo\))?\.?", printed) is None:
                failures.append("DIRECT_LOCAL_REPORTING_CLAUSE_NOT_FULLY_RECOGNIZED")
        surface["printed_dates"] = [value.isoformat() for value in dates]
        surface["reasons"] = sorted(set(failures))
        surface["disposition"] = "LOCAL_PERIOD_CONTEXT_VETO" if failures else "RETAINED_COMPATIBLE_SURFACE_NOT_PERIOD_AUTHORITY"
        reasons.extend(failures)
    return surfaces, ancestors, sorted(set(reasons))


def _comparative_flow_scope_row_labels(table: Mapping[str, Any]) -> list[Any]:
    """Include standalone/structural scope labels even when their self path is stripped.

    A populated tax component mentioning a subsidiary is not a blanket report
    override. A blank or structural entity heading, irrespective of row_kind,
    remains a veto on inheriting one unqualified period population.
    """
    return [row.get("label_exact") for row in table["rows"]
            if row.get("row_kind") == "GROUP"
            or not any(value is not None and value != "" for value in row.get("values_exact") or [])
            or _normalized(row.get("label_exact")) in {"ngan hang me", "cong ty con", "rieng", "hop nhat"}]


def _comparative_flow_period_inheritance_receipt(
    section: Mapping[str, Any], table: Mapping[str, Any], lane: Mapping[str, Any], *,
    locator: Mapping[str, Any], document_period_inventory: Mapping[str, Any],
    compiled_specs: Mapping[str, Any] | None,
) -> dict[str, Any]:
    document = document_period_inventory["document_comparative_flow_policy_receipt"]
    periods = document["resolved_source_duration_semantics"]
    paths = _relative_flow_column_paths(table, lane)
    note = section.get("content_kind") == "FINANCIAL_NOTE"
    primary = section.get("content_kind") == "PRIMARY_STATEMENT" and section.get("statement_type") in {"INCOME_STATEMENT", "CASH_FLOW"}
    reasons = []
    if not document["complete"]:
        reasons.append("AUTHENTICATED_PRINTED_DOCUMENT_COMPARATIVE_FLOW_POLICY_ABSENT")
    if paths is None:
        reasons.append("LITERAL_ORDERED_KY_NAY_KY_TRUOC_LABELS_REQUIRED")
    owner = bool(note and compiled_specs is not None and _supplemental_owner_matches(section, table, compiled_specs=compiled_specs))
    if not owner and not primary:
        reasons.append("SOURCE_OWNER_NOT_PROVEN_FOR_COMPARATIVE_FLOW_POLICY")
    if primary:
        matches = [anchor for anchor in document["anchor_source_receipts"]
                   if same_typed_json_v1(anchor["locator"], locator)
                   and anchor["original_table_json_sha256"] == canonical_json_sha256_v1(table)]
        if len(matches) != 1 or not matches[0]["complete"]:
            reasons.append("PRIMARY_SAME_TABLE_INDEPENDENT_CURRENT_DURATION_NOT_PROVEN")
    surfaces, ancestors, failures = _comparative_flow_local_surface_census(section, table, lane, periods)
    reasons.extend(failures)
    constraints = _owned_current_period_constraints(section, table)
    if constraints and (periods is None or not _owned_current_period_constraints_match(section, table, lane, periods)):
        reasons.append("OWNED_CURRENT_PERIOD_ASSERTION_NOT_COMPATIBLE_WITH_COMPARATIVE_FLOW_POLICY")
    scope = _note_report_scope_receipt(
        section, table, source_paths=[*(paths or []), *ancestors, [item["source_exact"] for item in surfaces],
                                     _comparative_flow_scope_row_labels(table)],
        document_scope=document_period_inventory["document_report_scope_receipt"],
    )
    if (scope["conflict"] or scope["local_entity_qualifiers"] or scope["report_scope"] is None
            or scope["report_scope"] != document_period_inventory["document_report_scope_receipt"]["report_scope"]):
        reasons.append("COMPARATIVE_FLOW_REPORT_POPULATION_NOT_PROVEN")
    material = {"complete": not reasons, "status": "ALGORITHM_HOLD" if reasons else "PASS_AUTHENTICATED_PRINTED_COMPARATIVE_FLOW_POLICY",
                "locator": canonical_clone_v1(locator), "original_section_json_sha256": canonical_json_sha256_v1(section),
                "original_table_json_sha256": canonical_json_sha256_v1(table), "money_column_ordinals": canonical_clone_v1(lane.get("money_column_ordinals")),
                "header_paths_exact": paths, "explicit_tax_owner_caption_matches": owner,
                "local_period_surface_census": surfaces, "owned_current_period_constraints": constraints, "scope_receipt": scope,
                "structural_scope_row_labels_exact": _comparative_flow_scope_row_labels(table),
                "document_comparative_flow_policy_receipt": canonical_clone_v1(document),
                "resolved_source_duration_semantics": canonical_clone_v1(periods) if not reasons else None,
                "comparative_origin": "PRINTED_DOCUMENT_COMPARATIVE_FLOW_POLICY", "amounts_used_as_authority": False,
                "source_period_keys_modified": False, "start_dates_inferred": False, "reasons": sorted(set(reasons)),
                "rule": "LITERAL_RELATIVE_FLOW_COLUMNS_WITH_PRINTED_COMPARATIVE_POLICY_ALL_OWNED_CURRENT_ANCHORS_AND_EXHAUSTIVE_LOCAL_VETOES"}
    return {**material, "receipt_id": "gjitfav1:inherited-comparative-flow-period:" + canonical_json_sha256_v1(material)}


def _note_comparative_flow_inheritance_receipt(
    section: Mapping[str, Any], table: Mapping[str, Any], lane: Mapping[str, Any], *,
    locator: Mapping[str, Any], document_period_inventory: Mapping[str, Any], compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    return _comparative_flow_period_inheritance_receipt(section, table, lane, locator=locator,
        document_period_inventory=document_period_inventory, compiled_specs=compiled_specs)


def _registered_part_period_receipt(
    section: Mapping[str, Any], table: Mapping[str, Any], lane: Mapping[str, Any], *,
    locator: Mapping[str, Any], page_records: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any], document_period_inventory: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Resolve only an independently registered target's literal period pair.

    Dates are not written into headers and no UNKNOWN column becomes MONEY.
    A pinned source-context approval is different from a new transcription or
    a caller's self-sealed receipt. Actual PDF byte/render authentication is a
    separate warm/cold runner boundary before accepted persistence.
    """
    # No context denies this additional authority; it is not a positive
    # result. The caller has freshly replayed the whole inventory already.
    if not document_period_inventory.get("registered_part_period_contexts"):
        return None
    view = _registered_part_period_source_view_v1(page_records, compiled_specs=compiled_specs)
    contexts = view["contexts"]
    if (not same_typed_json_v1(contexts, document_period_inventory.get("registered_part_period_contexts", []))
            or not same_typed_json_v1(view["registry_ref"], document_period_inventory.get("registered_part_period_registry_ref"))
            or not same_typed_json_v1(view["source_variant_selection"], document_period_inventory.get("registered_part_period_source_variant_selection"))):
        raise _error("income-tax registered part-period inventory source replay drifted")
    matches = [item for item in contexts if same_typed_json_v1(item["target_locator"], locator)]
    if not matches:
        return None
    if len(matches) != 1:
        raise _error("income-tax registered part-period target is ambiguous")
    context = matches[0]
    periods = context["resolved_source_duration_semantics"]
    reasons = []
    if section.get("content_kind") != "FINANCIAL_NOTE":
        reasons.append("REGISTERED_PART_PERIOD_TARGET_NOT_FINANCIAL_NOTE")
    if not _supplemental_owner_matches(section, table, compiled_specs=compiled_specs):
        reasons.append("REGISTERED_PART_PERIOD_TAX_OWNER_NOT_PROVEN")
    columns = context["raw_column_ordinals"]
    # The existing family config accepts MONEY and UNKNOWN source metadata.
    # Strict core replay has already retained/bound those exact raw kinds.
    # A period proof neither promotes them nor replaces the independent
    # unit/role/numeric/equation gates used by the mapping evaluator.
    if not lane.get("complete") or not same_typed_json_v1(lane.get("money_column_ordinals"), columns):
        reasons.append("REGISTERED_PART_PERIOD_ORIGINAL_VALUE_AXIS_NOT_PROVEN")
    paths = _relative_flow_column_paths(table, lane)
    if paths is None or not same_typed_json_v1(paths, context["header_paths_exact"]):
        reasons.append("REGISTERED_PART_PERIOD_LITERAL_COLUMN_ORIENTATION_NOT_PROVEN")
    surfaces, ancestors, failures = _comparative_flow_local_surface_census(section, table, lane, periods)
    reasons.extend(failures)
    constraints = _owned_current_period_constraints(section, table)
    if not _owned_current_period_constraints_match(section, table, lane, periods):
        reasons.append("REGISTERED_PART_PERIOD_OWNED_CURRENT_ASSERTION_CONFLICT")
    scope = _note_report_scope_receipt(
        section, table,
        source_paths=[*(paths or []), *ancestors, [item["source_exact"] for item in surfaces],
                      _comparative_flow_scope_row_labels(table)],
        document_scope=document_period_inventory["document_report_scope_receipt"],
    )
    if scope["conflict"] or scope["report_scope"] is None or scope["local_entity_qualifiers"]:
        reasons.append("REGISTERED_PART_PERIOD_LOCAL_REPORT_POPULATION_CONFLICT")
    material = {
        "complete": not reasons,
        "status": "ALGORITHM_HOLD" if reasons else "PASS_REGISTERED_PART_SOURCE_PERIOD_PAIR",
        "locator": canonical_clone_v1(locator), "registered_source_context": canonical_clone_v1(context),
        "registry_ref": canonical_clone_v1(view["registry_ref"]),
        "source_variant_selection": canonical_clone_v1(view["source_variant_selection"]),
        "evaluation_section_json_sha256": canonical_json_sha256_v1(section),
        "evaluation_table_json_sha256": canonical_json_sha256_v1(table),
        "raw_lane_axis": canonical_clone_v1(lane), "header_paths_exact": paths,
        "scope_receipt": scope, "local_period_surface_census": surfaces,
        "owned_current_period_constraints": constraints,
        "resolved_source_duration_semantics": canonical_clone_v1(periods) if not reasons else None,
        "comparative_origin": "REGISTERED_TARGET_ONLY_PRINTED_PART_DATE_PAIR",
        "cash_flow_used_as_period_authority": False, "report_scope_permission_granted": False,
        "unit_permission_granted": False, "source_values_modified": False,
        "source_period_keys_modified": False, "start_dates_inferred": False,
        "amounts_used_as_authority": False, "reasons": sorted(set(reasons)),
        "rule": "FRESH_PINNED_SOURCE_CONTEXT_TARGET_AND_WHOLE_LITERAL_DATES_WITH_ALL_LOCAL_VETOES_NO_SOURCE_EDIT",
    }
    return {**material, "receipt_id": "gjitfav1:registered-part-period:" + canonical_json_sha256_v1(material)}


def _primary_comparative_flow_period_receipt(
    section: Mapping[str, Any], table: Mapping[str, Any], lane: Mapping[str, Any], *,
    locator: Mapping[str, Any], document_period_inventory: Mapping[str, Any],
) -> dict[str, Any]:
    return _comparative_flow_period_inheritance_receipt(section, table, lane, locator=locator,
        document_period_inventory=document_period_inventory, compiled_specs=None)


def _document_statement_period_inventory(page_records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]) -> dict[str, Any]:
    state = _DOCUMENT_PERIOD_OPERATION.get()
    if state is None:
        return _build_document_statement_period_inventory_uncached_v1(page_records, compiled_specs=compiled_specs)
    if state["closed"] or state["invalidated"]:
        raise _error("income-tax period inventory operation is closed or invalidated")
    if state["execution_owner"] != _period_inventory_execution_owner_v1():
        raise _error("income-tax period inventory operation cannot cross tasks or threads")
    metrics = state["metrics"]
    metrics["requests"] += 1
    if not state["enabled"]:
        metrics["disabled_requests"] += 1
        started = perf_counter()
        value = _build_document_statement_period_inventory_uncached_v1(page_records, compiled_specs=compiled_specs)
        metrics["build_seconds"] += perf_counter() - started
        metrics["builds"] += 1
        return value
    started = perf_counter()
    key = _period_inventory_key_v1(page_records, compiled_specs)
    fence = _period_inventory_callable_fence_v1()
    if state["callable_fence"] is None:
        state["callable_fence"] = fence
    elif not all(left is right for left, right in zip(state["callable_fence"], fence, strict=True)):
        state["invalidated"] = True
        raise _error("income-tax period inventory callable changed during operation")
    metrics["key_seconds"] += perf_counter() - started
    entry = state["entries"].get(key)
    if entry is not None and all(left is right for left, right in zip(entry[1], fence, strict=True)):
        metrics["hits"] += 1
        started = perf_counter()
        value = decode_canonical_json_bytes_v1(entry[0])
        metrics["clone_seconds"] += perf_counter() - started
        return value
    started = perf_counter()
    value = _build_document_statement_period_inventory_uncached_v1(page_records, compiled_specs=compiled_specs)
    metrics["build_seconds"] += perf_counter() - started
    metrics["builds"] += 1
    raw = canonical_json_bytes_v1(value)
    started = perf_counter()
    unchanged = (key == _period_inventory_key_v1(page_records, compiled_specs)
                 and all(left is right for left, right in zip(fence, _period_inventory_callable_fence_v1(), strict=True)))
    metrics["key_seconds"] += perf_counter() - started
    if not unchanged:
        state["invalidated"] = True
        raise _error("income-tax period inventory input changed during construction")
    # Bound memory even when a caller evaluates more than one private clone.
    # Eviction is a recomputation, never a reason to omit a source dependency.
    if key not in state["entries"] and len(state["entries"]) >= 2:
        state["entries"].clear()
    state["entries"][key] = (raw, fence)
    metrics["peak_entries"] = max(metrics["peak_entries"], len(state["entries"]))
    metrics["peak_stored_bytes"] = max(metrics["peak_stored_bytes"], sum(len(item[0]) for item in state["entries"].values()))
    started = perf_counter()
    value = decode_canonical_json_bytes_v1(raw)
    metrics["clone_seconds"] += perf_counter() - started
    return value


def _build_document_statement_period_inventory_uncached_v1(page_records: Sequence[Mapping[str, Any]], *, compiled_specs: Mapping[str, Any]) -> dict[str, Any]:
    scope = _document_report_scope_receipt(page_records)
    sources, page_axis = [], []
    for record in page_records:
        page = record["page_json"]
        page_axis.append({**{key: canonical_clone_v1(record[key]) for key in ("document_id", "document_ordinal", "page_json_version_id", "physical_page", "selected_page_ordinal", "source_logical_name", "source_sha256")},
                          "original_page_json_sha256": canonical_json_sha256_v1(page)})
        if page.get("status") != "PRIMARY_FINANCIAL_STATEMENT":
            continue
        for section_ordinal, section in enumerate(page.get("sections") or [], 1):
            if section.get("content_kind") != "PRIMARY_STATEMENT" or section.get("statement_type") not in {"INCOME_STATEMENT", "CASH_FLOW"}:
                continue
            for table_ordinal, table in enumerate(section.get("tables") or [], 1):
                lane = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
                sources.append({
                    "locator": _record_locator(record, section_id=f"s{section_ordinal}", table_id=f"t{table_ordinal}"),
                    "statement_type": section["statement_type"], "captions_exact": [section.get("title_exact"), table.get("title_exact")],
                    "owned_narratives_exact": canonical_clone_v1(section.get("narratives_exact") or []) if len(section["tables"]) == 1 else [],
                    "owned_current_period_constraints": _owned_current_period_constraints(section, table),
                    "columns_exact": canonical_clone_v1(table["columns"]), "lane_axis": lane,
                    "tax_expense_source_rows": [{"row_ordinal": ordinal, "role": _role_for_primary_label(row.get("label_exact"))}
                                                for ordinal, row in enumerate(table["rows"], 1) if _role_for_primary_label(row.get("label_exact")) is not None],
                    "printed_duration_lengths": _printed_duration_lengths(table, lane.get("money_column_ordinals") or [], section=section),
                    "scope_receipt": _note_report_scope_receipt(section, table, source_paths=[column["header_path_exact"] for column in table["columns"]], document_scope=scope),
                    "absolute_duration_semantics": _absolute_source_duration_semantics(section, table, lane),
                    "owned_relative_year_duration_evidence": _owned_relative_year_duration_evidence(section, table, lane),
                    "ytd_sibling_evidence": _printed_ytd_sibling_period_evidence(section, table, lane),
                    "original_page_json_sha256": canonical_json_sha256_v1(page), "original_section_json_sha256": canonical_json_sha256_v1(section),
                    "original_table_json_sha256": canonical_json_sha256_v1(table),
                })
    material = {"selected_page_axis": sorted(page_axis, key=lambda item: item["selected_page_ordinal"]),
                "sources": sorted(sources, key=lambda item: (item["locator"]["selected_page_ordinal"], int(item["locator"]["section_id"][1:]), int(item["locator"]["table_id"][1:]))),
                "document_report_scope_receipt": scope,
                "document_annual_period_receipt": _document_annual_period_receipt(sources, scope),
                "document_comparative_flow_policy_receipt": _document_comparative_flow_policy_receipt(
                    page_records, sources, scope, compiled_specs=compiled_specs),
                "rule": "ALL_ORIGINAL_TYPED_INCOME_AND_CASH_FLOW_PERIOD_SOURCES_NO_FILENAME_OR_AMOUNT_AUTHORITY"}
    view = _registered_part_period_source_view_v1(page_records, compiled_specs=compiled_specs)
    if view["contexts"]:
        material["registered_part_period_contexts"] = view["contexts"]
        material["registered_part_period_registry_ref"] = canonical_clone_v1(view["registry_ref"])
        material["registered_part_period_source_variant_selection"] = canonical_clone_v1(view["source_variant_selection"])
    return {**material, "receipt_id": "gjitfav1:document-statement-periods:" + canonical_json_sha256_v1(material)}


def _selector_flow_window_for_policy_veto(
    selector: Mapping[str, Any], periods: Any, *, literal: bool, column_index: int,
) -> dict[str, Any] | None:
    if periods is not None:
        period = periods[column_index]
        months = 12 if period[0] == "ANNUAL_YEAR" else period[2] * 3
        return {"printed_months": months, "printed_end_date": date(period[1], months, {3: 31, 6: 30, 9: 30, 12: 31}[months]).isoformat()}
    if not literal:
        return None
    key = selector["raw_lane_axis"]["source_lane_keys"][column_index]
    if key[0] in {"BARE_YEAR", "DURATION_BARE_YEAR"}:
        return {"printed_months": 12, "printed_end_date": f"{int(key[1]):04d}-12-31"}
    if key[0] in {"DURATION_END_DATE", "DURATION_DATE_RANGE"}:
        lengths = selector["printed_duration_lengths"][column_index]
        end = date.fromisoformat(key[-1])
        months = lengths[0] if len(lengths) == 1 else None
        if months is None and key[0] == "DURATION_DATE_RANGE":
            start, exclusive = date.fromisoformat(key[1]), end + timedelta(days=1)
            if start.day == exclusive.day == 1:
                months = (exclusive.year - start.year) * 12 + exclusive.month - start.month
        if months is not None:
            return {"printed_months": months, "printed_end_date": end.isoformat()}
    return None


def _printed_comparative_flow_policy_consistency_receipt(
    selectors: Sequence[Mapping[str, Any]], resolutions: Sequence[Mapping[str, Any]], *,
    literal: bool, document_period_inventory: Mapping[str, Any],
) -> dict[str, Any]:
    """An explicit printed policy can veto an otherwise successful older route.

    Absence of new-route anchors is not a contradiction and cannot invalidate
    an independently printed absolute pair. This is veto-only, never authority
    to supply a missing date, duration or source value.
    """
    document = document_period_inventory["document_comparative_flow_policy_receipt"]
    policies = [item for item in document["policy_source_receipts"] if item["owned"]]
    def affirmative_policy(policy):
        return (re.match(r"so lieu (?:so sanh|(?:cua )?(?:ky|nam) truoc)\b", _normalized(policy["source_exact"])) is not None
                or _unsupported_english_comparative_flow_assertion(policy["source_exact"]))
    reasons, checks, current_anchor_checks = [], [], []
    applicability_holds = []
    for policy in document["policy_source_receipts"]:
        if not policy["owned"] and (policy["parser_receipt"]["complete"] or affirmative_policy(policy)):
            applicability_holds.append({
                "locator": canonical_clone_v1(policy["locator"]),
                "original_narrative_sha256": policy["original_narrative_sha256"],
                "policy_parser_receipt_id": policy["parser_receipt"]["receipt_id"],
                "page_status": policy["page_status"], "section_content_kind": policy["section_content_kind"],
                "section_statement_type": policy["section_statement_type"],
                "section_title_exact": policy["section_title_exact"], "source_exact": policy["source_exact"],
                "positive_period_authority_eligible": False,
                "classification": "AFFIRMATIVE_POLICY_APPLICABILITY_UNPROVEN_NO_POSITIVE_AUTHORITY",
            })
            reasons.append("SOURCE_PERIOD_AFFIRMATIVE_UNOWNED_FLOW_POLICY_APPLICABILITY_NOT_PROVEN")
    owned_active = any(item["parser_receipt"]["complete"] or affirmative_policy(item) for item in policies)
    active = bool(applicability_holds) or owned_active
    for policy in policies if active else []:
        parser = policy["parser_receipt"]
        affirmative = affirmative_policy(policy)
        if not parser["complete"]:
            if affirmative:
                reasons.append("SOURCE_PERIOD_COMPETING_PRINTED_FLOW_POLICY_NOT_RECOGNIZED")
            continue
        printed = parser["comparative_period"]
        scope = document_period_inventory["document_report_scope_receipt"]["report_scope"]
        qualifiers = set(policy["local_qualifiers"])
        if ((scope is not None and printed["report_scope"] is not None and scope != printed["report_scope"])
                or qualifiers & {"PARENT_ENTITY", "SUBSIDIARY_ENTITY"}
                or len(qualifiers & {"SEPARATE", "CONSOLIDATED"}) > 1):
            reasons.append("SOURCE_PERIOD_PRINTED_FLOW_POLICY_POPULATION_CONFLICT")
        for index, selector in enumerate(selectors):
            periods = (resolutions[index]["resolved_source_duration_semantics"] if resolutions else None)
            observed = _selector_flow_window_for_policy_veto(selector, periods, literal=literal, column_index=1)
            expected = {name: printed[name] for name in ("printed_months", "printed_end_date")}
            compatible = observed is not None and same_typed_json_v1(expected, observed)
            checks.append({"policy_locator": canonical_clone_v1(policy["locator"]),
                           "original_narrative_sha256": policy["original_narrative_sha256"],
                           "policy_parser_receipt_id": parser["receipt_id"], "source_locator": canonical_clone_v1(selector["locator"]),
                           "printed_policy_comparative_window": expected, "selected_comparative_window": observed,
                           "compatible": compatible})
            # A failed underlying correspondence remains a hold for its own
            # reasons; an unknown window is never used as a positive proof.
            if observed is not None and not compatible:
                reasons.append("SOURCE_PERIOD_CONTRADICTS_EXPLICIT_PRINTED_COMPARATIVE_FLOW_POLICY")
            current = _selector_flow_window_for_policy_veto(selector, periods, literal=literal, column_index=0)
            if current is not None:
                for anchor in document["anchor_source_receipts"]:
                    # Missing/undated anchors cannot supply a contradiction.
                    # Every *printed* duration assertion is checked, including
                    # conflicting captions on an unselected continuation.
                    for constraint in anchor["owned_current_period_constraints"]:
                        if not constraint["supported"]:
                            continue
                        if "printed_end_date" in constraint:
                            window = {name: constraint[name] for name in ("printed_months", "printed_end_date")}
                        elif "printed_annual_year" in constraint:
                            window = {"printed_months": 12, "printed_end_date": f"{constraint['printed_annual_year']:04d}-12-31"}
                        else:
                            continue
                        compatible_current = same_typed_json_v1(current, window)
                        current_anchor_checks.append({"source_locator": canonical_clone_v1(selector["locator"]),
                            "anchor_locator": canonical_clone_v1(anchor["locator"]), "printed_constraint": canonical_clone_v1(constraint),
                            "selected_current_window": current, "compatible": compatible_current})
                        if not compatible_current:
                            reasons.append("SOURCE_PERIOD_CONTRADICTED_BY_EXPLICIT_CURRENT_FLOW_ANCHOR")
    material = {"complete": not reasons, "status": "ALGORITHM_HOLD" if reasons else "PASS_VETO_ONLY_PRINTED_POLICY_CONSISTENCY" if active else "NOT_APPLICABLE",
                "finite_owned_policy_present": any(item["parser_receipt"]["complete"] for item in policies),
                "affirmative_owned_policy_veto_active": owned_active, "policy_veto_active": active,
                "checks": checks, "current_anchor_checks": current_anchor_checks,
                "unowned_affirmative_policy_applicability_holds": applicability_holds,
                "document_comparative_flow_policy_receipt_id": document["receipt_id"], "reasons": sorted(set(reasons)),
                "amounts_used_as_authority": False, "source_period_keys_modified": False, "start_dates_inferred": False,
                "rule": "PRINTED_COMPARATIVE_POLICY_CANNOT_BE_BYPASSED_BY_LITERAL_ABSOLUTE_OR_RELATIVE_YEAR_ROUTES_NO_MISSING_ANCHOR_VETO"}
    return {**material, "receipt_id": "gjitfav1:printed-comparative-flow-consistency:" + canonical_json_sha256_v1(material)}


def _cash_flow_partial_current_header_assertion_v1(source: Mapping[str, Any]) -> dict[str, Any] | None:
    """One fully dated current header beside an explicit relative PRIOR.

    This deliberately cannot supply the missing comparative period. Neither
    a bare first-column date nor a guessed previous year is accepted.
    """
    columns = source["columns_exact"]
    money = [ordinal for ordinal, column in enumerate(columns, 1) if column.get("value_kind") == "MONEY"]
    if len(money) != 2 or any(column.get("value_kind") not in {"TEXT", "MONEY"} for column in columns):
        return None
    paths = [columns[ordinal - 1].get("header_path_exact") for ordinal in money]
    if any(type(path) is not list or not path or any(type(value) is not str or not value.strip() for value in path) for path in paths):
        return None
    layouts = [" ".join(path).replace("\\n", "\n") for path in paths]
    printed = [_recognition_printed_text(" ".join(raw.split())) for raw in layouts]
    unit = r"(?: (?:trieu dong|trieu vnd|vnd|dong))?"
    prior = printed[1] or ""
    if re.match(r"(?:ky|nam) truoc\b", _normalized(layouts[1])) is None:
        return None
    # Distinguish an absent assertion from recognized-but-unsupported source.
    # Invalid dates/counts/annotations must not disappear into UNKNOWN and
    # allow an otherwise compatible report caption to conceal them.
    if re.match(r"ky .+ thang ket thuc ngay\b", _normalized(layouts[0])) is None:
        return None
    base = {"source_kind": "EXACT_DATED_CURRENT_HEADER_WITH_LITERAL_RELATIVE_PRIOR_COMPANION",
            "current_column_ordinal": money[0], "comparative_column_ordinal": money[1],
            "header_paths_exact": canonical_clone_v1(paths),
            "comparative_period_proven": False, "used_as_positive_period_authority": False,
            "comparative_year_inferred": False, "source_period_keys_modified": False}

    def unsupported(reason):
        return {**base, "complete": False, "reasons": [reason]}

    prior_pattern = (r"(?:ky|nam) truoc(?:(?: \(trinh bay lai\))?" + unit
                     + r"|" + unit + r" \(trinh bay lai\))")
    if re.fullmatch(prior_pattern, prior) is None:
        return unsupported("RELATIVE_PRIOR_COMPANION_HAS_UNSUPPORTED_ASSERTION")
    if any(any(unicodedata.category(char) in {"Cf", "Cs"}
               or unicodedata.category(char) == "Cc" and char not in "\t\r\n" for char in raw) for raw in layouts):
        return unsupported("UNSUPPORTED_RAW_CURRENT_HEADER_CHARACTER")
    pattern = (r"ky (?P<months>[0-9]{1,2}) thang ket thuc ngay "
               r"(?P<day>[0-9]{1,2})/(?P<month>[0-9]{1,2})/(?P<year>[0-9]{4})" + unit)
    match = re.fullmatch(pattern, printed[0] or "")
    if match is None:
        return unsupported("WHOLE_DATED_CURRENT_HEADER_NOT_RECOGNIZED")
    dates = re.findall(r"(?<!\S)([0-9]{1,2})/([0-9]{1,2})/([0-9]{4})(?=\s|$)", layouts[0])
    lengths = re.findall(r"(?i)(?:^|\s)k(?:ỳ|y)\s+([0-9]{1,2})(?=\s+th(?:á|a)ng\b)", layouts[0])
    if dates != [(match["day"], match["month"], match["year"])] or lengths != [match["months"]]:
        return unsupported("CURRENT_HEADER_RAW_ASCII_TOKENS_NOT_PROVEN")
    try:
        end = date(int(match["year"]), int(match["month"]), int(match["day"]))
    except ValueError:
        return unsupported("INVALID_PRINTED_CURRENT_HEADER_CALENDAR_DATE")
    months = int(match["months"])
    if not 1 <= months <= 12:
        return unsupported("UNSUPPORTED_PRINTED_CURRENT_HEADER_MONTH_COUNT")
    return {**base, "complete": True, "reasons": [], "printed_months": months, "printed_end_date": end.isoformat()}


def _cash_flow_printed_period_control_v1(
    selector: Mapping[str, Any], periods: Sequence[Sequence[Any]], source: Mapping[str, Any],
) -> dict[str, Any]:
    """Tri-state printed evidence: unknown is not a printed contradiction.

    All source assertions remain visible. A positive same population is needed
    even for a veto; two unknown scopes do not establish that relation. This
    control never completes a selector's missing period or comparative year.
    """
    scope, other = selector["scope_receipt"], source["scope_receipt"]
    compatible_population = (scope["report_scope"] in {"SEPARATE", "CONSOLIDATED"}
                             and scope["report_scope"] == other["report_scope"]
                             and not scope["conflict"] and not other["conflict"]
                             and not scope["local_entity_qualifiers"] and not other["local_entity_qualifiers"])
    current = periods[0]
    months = 12 if current[0] == "ANNUAL_YEAR" else current[2] * 3
    end = date(current[1], months, {3: 31, 6: 30, 9: 30, 12: 31}[months]).isoformat()
    checks, unsupported = [], []
    full = source["absolute_duration_semantics"]
    if full is not None:
        checks.append({"source_kind": "COMPLETE_CASH_FLOW_PERIOD_PAIR", "printed_periods": canonical_clone_v1(full),
                       "compatible": same_typed_json_v1(full[0], current),
                       "comparative_pair_equal": same_typed_json_v1(full, periods),
                       "comparative_used_as_cross_statement_veto": False})
    constraints = list(source["owned_current_period_constraints"])
    # These raw narratives are retained only when the original section has
    # exactly one table. Parse their whole reporting clauses independently;
    # never let historical prose or a borrowed narrative relabel a period.
    owned_narratives = source.get("owned_narratives_exact") or []
    if owned_narratives:
        narrative_constraints = _owned_current_period_constraints(
            {"content_kind": "PRIMARY_STATEMENT", "statement_type": "CASH_FLOW", "title_exact": None,
             "narratives_exact": owned_narratives, "tables": [None]},
            {"title_exact": None, "columns": source["columns_exact"]},
        )
        for assertion in narrative_constraints:
            if (assertion["source_kind"] == "OWNED_NARRATIVE"
                    and assertion not in constraints):
                constraints.append(assertion)
    for constraint in constraints:
        if not constraint["supported"]:
            unsupported.append(canonical_clone_v1(constraint))
            continue
        check = None
        if "printed_end_date" in constraint:
            check = (constraint["printed_end_date"] == end
                     and ("printed_months" not in constraint or constraint["printed_months"] == months)
                     and ("printed_start_date" not in constraint
                          or constraint["printed_start_date"] == date(current[1], 1, 1).isoformat()))
        elif "printed_annual_year" in constraint:
            check = months == 12 and constraint["printed_annual_year"] == current[1]
        elif "printed_reporting_quarter" in constraint:
            # A report-quarter caption asserts its endpoint, not a separate
            # three-month duration, especially for a cumulative CASH_FLOW.
            check = constraint["printed_year"] == current[1] and constraint["printed_reporting_quarter"] * 3 == months
        if check is not None:
            checks.append({"source_kind": "OWNED_CURRENT_CAPTION_ASSERTION",
                           "source_constraint": canonical_clone_v1(constraint), "compatible": check})
    partial = _cash_flow_partial_current_header_assertion_v1(source)
    if partial is not None:
        if partial["complete"]:
            checks.append({**partial, "compatible": partial["printed_months"] == months and partial["printed_end_date"] == end})
        else:
            unsupported.append(partial)
    contradiction = compatible_population and any(not check["compatible"] for check in checks)
    # An unsupported unselected caption is not a positive contradiction. Its
    # selected self-pair still has to pass its own mandatory caption checks.
    # Recognized malformed current headers are a distinct source-axis hold,
    # never missing evidence that a valid caption may silently replace.
    unsupported_current = compatible_population and partial is not None and not partial["complete"]
    status = ("PROVEN_CONTRADICTORY_PRINTED_PERIOD" if contradiction else
              "UNRESOLVED_PERIOD_OR_POPULATION_NOT_AUTHORITY" if not compatible_population or not checks or unsupported else
              "PROVEN_COMPATIBLE_PRINTED_PERIOD")
    material = {"status": status, "selector_locator": canonical_clone_v1(selector["locator"]),
                "cash_flow_locator": canonical_clone_v1(source["locator"]),
                "cash_flow_original_page_json_sha256": source["original_page_json_sha256"],
                "cash_flow_original_table_json_sha256": source["original_table_json_sha256"],
                "selector_periods": canonical_clone_v1(periods),
                "selector_scope_receipt": canonical_clone_v1(scope), "cash_flow_scope_receipt": canonical_clone_v1(other),
                "compatible_report_population_proven": compatible_population,
                "printed_assertion_checks": checks, "unsupported_owned_current_assertions": unsupported,
                "unsupported_compatible_current_assertion_requires_hold": unsupported_current,
                "complete_cash_flow_period_pair_proven": full is not None,
                "used_as_positive_period_authority": False, "comparative_year_inferred": False,
                "source_period_keys_modified": False, "amounts_used_as_authority": False}
    return {**material, "receipt_id": "gjitfav1:cash-flow-printed-period-control:" + canonical_json_sha256_v1(material)}


def _source_period_correspondence_receipt(
    *, left_locator: Mapping[str, Any], left_money_column_ordinals: Sequence[int],
    right_locator: Mapping[str, Any], right_money_column_ordinals: Sequence[int],
    page_records: Sequence[Mapping[str, Any]], compiled_specs: Mapping[str, Any], document_period_inventory: Mapping[str, Any],
) -> dict[str, Any]:
    fresh = _document_statement_period_inventory(page_records, compiled_specs=compiled_specs)
    if not same_typed_json_v1(fresh, document_period_inventory):
        raise _error("income-tax document period inventory source replay drifted")
    records = {record["page_json_version_id"]: record for record in page_records}
    selectors, reasons = [], []
    for locator, columns in ((left_locator, left_money_column_ordinals), (right_locator, right_money_column_ordinals)):
        record = records.get(locator.get("page_json_version_id"))
        if record is None:
            raise _error("income-tax period source selector page drifted")
        section, table = _source_table(record["page_json"], section_id=locator["section_id"], table_id=locator["table_id"])
        original = _record_locator(record, section_id=locator["section_id"], table_id=locator["table_id"])
        if any(not same_typed_json_v1(locator.get(key), value) for key, value in original.items()):
            raise _error("income-tax period source selector identity drifted")
        lane = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
        if not lane.get("complete") or not same_typed_json_v1(lane.get("money_column_ordinals"), list(columns)):
            reasons.append("SOURCE_PERIOD_SELECTOR_MONEY_AXIS_NOT_COMPLETE")
        scope = _note_report_scope_receipt(section, table, source_paths=[column["header_path_exact"] for column in table["columns"]], document_scope=fresh["document_report_scope_receipt"])
        selectors.append({"locator": original, "requested_money_column_ordinals": list(columns), "raw_lane_axis": lane,
                          "original_page_json_sha256": canonical_json_sha256_v1(record["page_json"]), "original_table_json_sha256": canonical_json_sha256_v1(table),
                          "printed_duration_lengths": _printed_duration_lengths(table, lane.get("money_column_ordinals") or [], section=section),
                          "scope_receipt": scope, "section": section, "table": table})
    left, right = selectors
    if (not fresh["document_report_scope_receipt"]["document_identity_unique"]
            or any(not same_typed_json_v1(left["locator"][key], right["locator"][key])
                   for key in ("document_id", "document_ordinal", "source_sha256"))):
        reasons.append("SOURCE_PERIOD_DOCUMENT_IDENTITY_NOT_UNIQUE")
    literal = not reasons and not any(_annual_source_context_ambiguous(item["section"], item["table"], item["raw_lane_axis"])
                                    or not _owned_current_period_constraints_match(item["section"], item["table"], item["raw_lane_axis"]) for item in selectors) and _source_duration_correspondence_complete(
        left["raw_lane_axis"], right["raw_lane_axis"], note_table=left["table"], primary_table=right["table"],
        note_lengths=left["printed_duration_lengths"], primary_lengths=right["printed_duration_lengths"],
    )
    # Applicable registered targets are replayed even on self-pairs. A failed
    # local target proof cannot be rescued through a different inheritance.
    part_receipts = [_registered_part_period_receipt(
        item["section"], item["table"], item["raw_lane_axis"], locator=item["locator"],
        page_records=page_records, compiled_specs=compiled_specs, document_period_inventory=fresh,
    ) for item in selectors]
    for proof in part_receipts:
        if proof is not None and not proof["complete"]:
            reasons.extend(proof["reasons"])
    if any(proof is not None for proof in part_receipts):
        literal = False
    resolutions = []
    if not literal and not reasons:
        for item, part_receipt in zip(selectors, part_receipts, strict=True):
            absolute = _absolute_source_duration_semantics(item["section"], item["table"], item["raw_lane_axis"])
            ytd = _printed_ytd_sibling_period_evidence(item["section"], item["table"], item["raw_lane_axis"])
            relative = _owned_relative_year_duration_evidence(item["section"], item["table"], item["raw_lane_axis"])
            inheritance = None
            flow_inheritance = None
            anchors = []
            uses_cf_authority = False
            resolved = absolute if absolute is not None else ytd["intrinsic_absolute_periods"] if ytd is not None else None
            if part_receipt is not None:
                part_periods = part_receipt["resolved_source_duration_semantics"]
                if resolved is not None and not same_typed_json_v1(resolved, part_periods):
                    reasons.append("SOURCE_PERIOD_REGISTERED_PART_CONTRADICTS_LOCAL_ABSOLUTE_PERIOD")
                    resolved = None
                else:
                    resolved = part_periods
            if resolved is None and item["section"].get("content_kind") == "FINANCIAL_NOTE" and _relative_year_column_paths(item["table"], item["raw_lane_axis"]) is not None:
                inheritance = _note_annual_period_inheritance_receipt(
                    item["section"], item["table"], item["raw_lane_axis"], locator=item["locator"],
                    document_period_inventory=fresh, compiled_specs=compiled_specs,
                )
                resolved = inheritance["resolved_source_duration_semantics"]
            if ytd is not None:
                scope = item["scope_receipt"]
                compatible_scope_anchors = [source for source in fresh["sources"] if source["statement_type"] == "CASH_FLOW"
                                            and scope["report_scope"] in {"SEPARATE", "CONSOLIDATED"}
                                            and source["scope_receipt"]["report_scope"] == scope["report_scope"]]
                anchors = compatible_scope_anchors
                if (not scope["conflict"] and scope["report_scope"] is not None and not scope["local_entity_qualifiers"]
                        and scope["report_scope"] == fresh["document_report_scope_receipt"]["report_scope"]
                        and ytd["relative_year_tokens"] is not None):
                    anchors = compatible_scope_anchors
                    if anchors and all(not anchor["scope_receipt"]["conflict"] and not anchor["scope_receipt"]["local_entity_qualifiers"]
                                       and anchor["absolute_duration_semantics"] is not None for anchor in anchors):
                        unique = {canonical_json_sha256_v1(anchor["absolute_duration_semantics"]) for anchor in anchors}
                        candidate = anchors[0]["absolute_duration_semantics"]
                        if len(unique) == 1 and candidate[0][1] == candidate[1][1] + 1 and all((period[0] == "ANNUAL_YEAR" and ytd["quarter"] == 4)
                                                   or (period[0] == "SOURCE_YTD_QUARTER" and period[2] == ytd["quarter"]) for period in candidate):
                            resolved = canonical_clone_v1(candidate)
                            uses_cf_authority = True
            if resolved is None and _relative_flow_column_paths(item["table"], item["raw_lane_axis"]) is not None:
                if item["section"].get("content_kind") == "FINANCIAL_NOTE":
                    flow_inheritance = _note_comparative_flow_inheritance_receipt(
                        item["section"], item["table"], item["raw_lane_axis"], locator=item["locator"],
                        document_period_inventory=fresh, compiled_specs=compiled_specs,
                    )
                elif item["section"].get("content_kind") == "PRIMARY_STATEMENT":
                    flow_inheritance = _primary_comparative_flow_period_receipt(
                        item["section"], item["table"], item["raw_lane_axis"], locator=item["locator"],
                        document_period_inventory=fresh,
                    )
                if flow_inheritance is not None:
                    resolved = flow_inheritance["resolved_source_duration_semantics"]
            if resolved is not None and not _owned_current_period_constraints_match(item["section"], item["table"], item["raw_lane_axis"], resolved):
                resolved = None
                reasons.append("SOURCE_PERIOD_OWNED_CURRENT_CAPTION_CONFLICT")
            resolutions.append({"resolved_source_duration_semantics": resolved, "ytd_sibling_evidence": ytd,
                                "registered_part_period_receipt": part_receipt,
                                "owned_relative_year_duration_evidence": relative,
                                "inherited_document_annual_period_receipt": inheritance,
                                "inherited_document_comparative_flow_policy_receipt": flow_inheritance,
                                "owned_current_period_constraints": _owned_current_period_constraints(item["section"], item["table"]),
                                "cash_flow_used_as_period_authority": uses_cf_authority,
                                "cash_flow_anchor_sources": anchors, "intrinsic_absolute_source_semantics": absolute})
        if any(item["resolved_source_duration_semantics"] is None for item in resolutions) or not same_typed_json_v1(
                resolutions[0]["resolved_source_duration_semantics"], resolutions[1]["resolved_source_duration_semantics"]):
            reasons.append("SOURCE_PERIOD_CONTEXTUAL_CORRESPONDENCE_NOT_PROVEN")
        if any(resolution["cash_flow_used_as_period_authority"] or resolution["inherited_document_annual_period_receipt"] is not None
               or resolution["inherited_document_comparative_flow_policy_receipt"] is not None for resolution in resolutions):
            scopes = [item["scope_receipt"] for item in selectors]
            if any(item["conflict"] or item["report_scope"] is None or item["local_entity_qualifiers"] for item in scopes) or scopes[0]["report_scope"] != scopes[1]["report_scope"]:
                reasons.append("SOURCE_PERIOD_CONTEXTUAL_REPORT_POPULATION_NOT_PROVEN")
    # Veto-only controls are applied on every independently proved route,
    # including literal/self pairs and each continuation. Missing comparative
    # evidence is retained as unknown, never treated as a printed conflict or
    # used to authorize a guessed period.
    cash_flow_controls = []
    for index, item in enumerate(selectors):
        periods = (resolutions[index]["resolved_source_duration_semantics"] if resolutions else
                   _absolute_source_duration_semantics(item["section"], item["table"], item["raw_lane_axis"]))
        if periods is None:
            continue
        for source in fresh["sources"]:
            if source["statement_type"] != "CASH_FLOW":
                continue
            control = _cash_flow_printed_period_control_v1(item, periods, source)
            cash_flow_controls.append(control)
            if control["status"] == "PROVEN_CONTRADICTORY_PRINTED_PERIOD":
                reasons.append("SOURCE_PERIOD_CONTRADICTED_BY_PRINTED_CASH_FLOW_ASSERTION")
            if control["unsupported_compatible_current_assertion_requires_hold"]:
                reasons.append("SOURCE_PERIOD_COMPATIBLE_CASH_FLOW_ASSERTION_UNSUPPORTED")
    policy_consistency = _printed_comparative_flow_policy_consistency_receipt(
        selectors, resolutions, literal=literal, document_period_inventory=fresh,
    )
    reasons.extend(policy_consistency["reasons"])
    material = {"complete": not reasons, "status": "ALGORITHM_HOLD" if reasons else "PASS_LITERAL_SOURCE_DURATION" if literal else
                "PASS_REGISTERED_PART_SOURCE_PERIOD_PAIR" if any(proof is not None for proof in part_receipts) else
                "PASS_AUTHENTICATED_PRINTED_COMPARATIVE_FLOW_POLICY" if any(item["inherited_document_comparative_flow_policy_receipt"] is not None for item in resolutions) else
                "PASS_AUTHENTICATED_DOCUMENT_ANNUAL_PERIOD" if any(item["inherited_document_annual_period_receipt"] is not None for item in resolutions) else
                "PASS_AUTHENTICATED_OWNED_RELATIVE_YEAR_DURATION" if any(item["owned_relative_year_duration_evidence"] is not None for item in resolutions) else
                "PASS_AUTHENTICATED_SOURCE_YTD_CORRESPONDENCE",
                "source_selectors": [{key: canonical_clone_v1(value) for key, value in item.items() if key not in {"section", "table"}} for item in selectors],
                "period_resolution_evidence": resolutions, "document_period_inventory_receipt_id": fresh["receipt_id"],
                "cash_flow_printed_period_controls": cash_flow_controls,
                "printed_comparative_flow_policy_consistency_receipt": policy_consistency,
                "amounts_used_as_authority": False, "source_period_keys_modified": False, "start_dates_inferred": False,
                "reasons": sorted(set(reasons)), "rule": "ORIGINAL_SOURCE_DURATION_CORRESPONDENCE_LITERAL_OR_PRINTED_YTD_SIBLINGS_AND_SAME_SCOPE_CF"}
    return {**material, "receipt_id": "gjitfav1:source-period-correspondence:" + canonical_json_sha256_v1(material)}


def _note_primary_signed_display_proof(
    note_candidate: Mapping[str, Any], primary_candidate: Mapping[str, Any], *,
    descriptor: Mapping[str, Any], page_records: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Bind opposite tax display to printed profit bridge and exact source lanes."""
    display = descriptor.get("expense_display_receipt")
    if type(display) is not dict:
        return None
    material = {key: value for key, value in display.items() if key != "receipt_id"}
    if display.get("receipt_id") != "gjitfav1:expense-display:" + canonical_json_sha256_v1(material):
        raise _error("income-tax signed expense display receipt drifted")
    pages = {record["page_json_version_id"]: record["page_json"] for record in page_records}
    primary_section, primary_table = _source_table(
        pages[descriptor["locator"]["page_json_version_id"]],
        section_id=descriptor["locator"]["section_id"], table_id=descriptor["locator"]["table_id"],
    )
    primary_scope_surfaces = [
        primary_section.get("title_exact"), primary_table.get("title_exact"),
        *display["population_ancestry_receipt"]["common_population_ancestry_exact"],
    ]
    primary_scope = _printed_population_qualifiers(primary_scope_surfaces)
    document_scope = _document_report_scope_receipt(page_records)
    document_period_inventory = _document_statement_period_inventory(page_records, compiled_specs=compiled_specs)
    if not primary_scope and document_scope["report_scope"] is not None:
        primary_scope = [document_scope["report_scope"]]
    primary_by_role = {mapping["role"]: mapping for mapping in primary_candidate["mappings"]}
    overlaps, tables, neutral_zero_controls = [], {}, []
    tax_roles = {"CURRENT_TAX_PARENT", "DEFERRED_TAX_NET", "FAMILY_ROOT_TOTAL"}
    for mapping in note_candidate["mappings"]:
        role = mapping["role"]
        if role == "PROFIT_BEFORE_TAX":
            primary_profit = {
                "unit": descriptor["canonical_unit"],
                "values": display["before_source_row"]["parsed_values"],
            }
            if not _cross_source_mapping_signs(mapping, primary_profit, allow_sign_inversion=False):
                return None
        if role not in tax_roles:
            continue
        # An equation-derived root has no independent printed sign authority.
        if role == "FAMILY_ROOT_TOTAL" and not _mapping_is_direct_source_observation(mapping):
            continue
        refs = mapping.get("source_refs")
        if not refs:
            return None
        for ref in refs:
            locator = ref["locator"]
            page = pages.get(locator["page_json_version_id"])
            if page is None or any(locator.get(key) != descriptor["locator"].get(key)
                                   for key in ("document_id", "document_ordinal", "source_sha256")):
                return None
            try:
                section = page["sections"][int(locator["section_id"][1:]) - 1]
                table = section["tables"][int(locator["table_id"][1:]) - 1]
            except (KeyError, IndexError, TypeError, ValueError):
                return None
            lane = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
            period_proof = _source_period_correspondence_receipt(
                left_locator=locator, right_locator=descriptor["locator"],
                left_money_column_ordinals=ref.get("money_column_ordinals") or [],
                right_money_column_ordinals=descriptor["money_column_ordinals"],
                page_records=page_records, compiled_specs=compiled_specs, document_period_inventory=document_period_inventory,
            )
            if (
                not lane.get("complete")
                or not period_proof["complete"]
                or not same_typed_json_v1(lane.get("money_column_ordinals"), ref.get("money_column_ordinals"))
            ):
                return None
            population = _original_note_population_ancestry(
                table, section, row_ordinal=ref["row_ordinal"], compiled_specs=compiled_specs,
            )
            if population is None or not same_typed_json_v1(
                population["common_population_ancestry_exact"],
                display["population_ancestry_receipt"]["common_population_ancestry_exact"],
            ):
                return None
            note_scope_receipt = _note_report_scope_receipt(
                section, table, source_paths=[population["common_population_ancestry_exact"],
                                             *population.get("printed_scope_source_paths_exact", [])],
                document_scope=document_scope,
            )
            note_scope_surfaces = note_scope_receipt["source_surfaces_exact"]
            note_scope = ([note_scope_receipt["report_scope"]] if note_scope_receipt["report_scope"] is not None
                          else note_scope_receipt["local_qualifiers"])
            if note_scope_receipt["conflict"] or (note_scope and note_scope != primary_scope):
                return None
            scope_material = {
                "rule": "EXPLICIT_NOTE_POPULATION_QUALIFIERS_MUST_MATCH_PRINTED_PRIMARY_NO_AMOUNT_INFERENCE",
                "primary_source_surfaces": canonical_clone_v1(primary_scope_surfaces),
                "note_source_surfaces": canonical_clone_v1(note_scope_surfaces),
                "primary_scope": primary_scope, "note_scope": note_scope,
                "note_report_scope_receipt": note_scope_receipt,
                "document_report_scope_receipt": document_scope,
                "absent_scope_inferred": note_scope_receipt["origin"] == "INHERITED_UNIQUE_DOCUMENT_REPORT_SCOPE",
            }
            table_material = {
                "locator": {key: canonical_clone_v1(locator[key]) for key in descriptor["locator"]},
                "canonical_unit": mapping["unit"],
                "original_page_json_sha256": canonical_json_sha256_v1(page),
                "original_table_json_sha256": canonical_json_sha256_v1(table),
                "money_column_ordinals": canonical_clone_v1(ref["money_column_ordinals"]),
                "lane_axis": lane,
                "source_period_correspondence_receipt": period_proof,
                "population_ancestry_receipt": population,
                "printed_population_scope_receipt": {
                    **scope_material, "receipt_id": "gjitfav1:printed-scope:" + canonical_json_sha256_v1(scope_material),
                },
            }
            tables[canonical_json_sha256_v1(table_material)] = table_material
        primary = primary_by_role.get(role)
        if primary is None or role == "FAMILY_ROOT_TOTAL":
            continue
        if not primary.get("source_refs") or not all(
            all(ref["locator"].get(key) == value for key, value in descriptor["locator"].items())
            and same_typed_json_v1(ref.get("money_column_ordinals"), descriptor["money_column_ordinals"])
            for ref in primary["source_refs"]
        ):
            return None
        signs = _cross_source_mapping_signs(mapping, primary, allow_sign_inversion=True)
        if signs == frozenset({-1, 1}):
            neutral_zero_controls.append({"note_mapping": canonical_clone_v1(mapping),
                                          "primary_mapping": canonical_clone_v1(primary),
                                          "rule": "OBSERVED_ZERO_OVERLAP_HAS_NO_SIGN_ORIENTATION_AUTHORITY"})
            continue
        if signs != frozenset({-1}):
            return None
        overlaps.append({"note_mapping": canonical_clone_v1(mapping),
                         "primary_mapping": canonical_clone_v1(primary), "orientation": -1})
    if not overlaps:
        return None
    proof_material = {
        "rule": "PRINTED_PROFIT_BRIDGE_AND_INDEPENDENT_NONROOT_TAX_OVERLAP_EXACT_SOURCE_PERIODS_NO_VALUE_CHANGE",
        "primary_expense_display_receipt": canonical_clone_v1(display),
        "independent_nonroot_overlaps": overlaps,
        "neutral_observed_zero_controls": neutral_zero_controls,
        "note_source_tables": [tables[key] for key in sorted(tables)],
        "note_candidate_id": note_candidate["candidate_id"],
        "primary_candidate_id": primary_candidate["candidate_id"],
        "cross_source_orientation": -1, "source_values_changed": False,
    }
    return {**proof_material, "receipt_id": "gjitfav1:signed-display:" + canonical_json_sha256_v1(proof_material)}


def _at_rate_cross_presentation_conflicts(
    candidate: Mapping[str, Any], *, compiled_specs: Mapping[str, Any],
    source_context: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Never sum a generic current-year expense with explicitly rate-based tax."""
    role = next(child for child in compiled_specs["topology"]["children"]
                if child["role"] == "CURRENT_TAX_AT_RATE")
    strong_aliases = {
        _without_leading_ordinal(_normalized(alias))
        for matcher in role["matchers"] if matcher.get("presence_anchor", True)
        for alias in matcher["aliases"]
    }
    weak_aliases = {"nam hien hanh", "ky hien hanh"}
    conflicts = []
    for mapping in candidate.get("mappings", []):
        if mapping.get("role") != "CURRENT_TAX_AT_RATE":
            continue
        strong, weak = [], []
        for ref in mapping.get("source_refs", []):
            label = _without_leading_ordinal(_normalized(ref.get("label_exact")))
            if label in strong_aliases:
                strong.append(canonical_clone_v1(ref))
            if label in weak_aliases:
                weak.append(canonical_clone_v1(ref))
        if not strong or not weak:
            continue
        material = {
            "rule": "CURRENT_YEAR_EXPENSE_AND_EXPLICIT_RATE_BASE_ARE_NOT_AN_ADDITIVE_TAX_POPULATION",
            "mapping": canonical_clone_v1(mapping),
            "explicit_rate_source_refs": strong, "generic_current_year_source_refs": weak,
            "source_values_changed": False,
            "classification": "ALGORITHM_ROLE_POPULATION_AMBIGUITY_NOT_GENUINE_SOURCE_CONFLICT",
        }
        conflicts.append({**material, "receipt_id": "gjitfav1:at-rate-population:" + canonical_json_sha256_v1(material)})
    for inventory in (source_context or {}).get("tax_population_inventory", []):
        years = inventory["current_year_surface_ordinals"]
        if not years:
            continue
        boundary = inventory["current_year_frontier"]
        covered_years = {item["row_ordinal"] for item in boundary["component_source_rows"]
                         if item["normalized_label"] in {"nam hien hanh", "ky hien hanh"}} if boundary is not None else set()
        if set(years) <= covered_years:
            continue
        material = {
            "rule": "CURRENT_YEAR_EXPENSE_REQUIRES_INDEPENDENT_SOURCE_OWNERSHIP_NOT_RATE_ADDITIVE_CONSUMPTION",
            "population_inventory": canonical_clone_v1(inventory),
            "classification": "ALGORITHM_ROLE_POPULATION_AMBIGUITY_NOT_GENUINE_SOURCE_CONFLICT",
            "source_values_changed": False,
        }
        conflicts.append({**material, "receipt_id": "gjitfav1:at-rate-population:" + canonical_json_sha256_v1(material)})
    return conflicts


def _tax_effect_basis_conflicts(
    candidate: Mapping[str, Any], *, source_context: Mapping[str, Any],
) -> list[dict[str, Any]]:
    conflicts = []
    for inventory in source_context["tax_population_inventory"]:
        locator = inventory["locator"]
        rate_rows = {ordinal for frontier in inventory["rate_frontiers"]
                     for ordinal in frontier["component_row_ordinals"]}
        for mapping in candidate.get("mappings", []):
            if mapping.get("role") not in {"NON_DEDUCTIBLE_EXPENSE", "NON_TAXABLE_AGGREGATE"}:
                continue
            refs = [ref for ref in mapping.get("source_refs", [])
                    if all(ref.get("locator", {}).get(key) == locator[key]
                           for key in ("page_json_version_id", "section_id", "table_id"))
                    and ref.get("row_ordinal") in rate_rows]
            if refs:
                conflicts.append({
                    "mapping": canonical_clone_v1(mapping),
                    "source_refs": canonical_clone_v1(refs),
                    "population_inventory_id": inventory["receipt_id"],
                    "classification": "ALGORITHM_MEASUREMENT_BASIS_AMBIGUITY_NOT_GENUINE_SOURCE_CONFLICT",
                    "rule": "RATE_RECONCILIATION_TAX_EFFECT_MUST_NOT_EXPORT_INCOME_BASIS_SCHEMA_TARGET",
                })
    return conflicts


def _recognition_rate_source_only_projection(
    candidate: Mapping[str, Any], *, source_context: Mapping[str, Any],
) -> dict[str, Any]:
    """Retain exact RATE effects as controls, never export them as income.

    This is an additive source-semantic projection, not an edit to the frozen
    evaluator, the original candidate proof, or a private basis receipt.
    """
    if candidate.get("status") != READY:
        return canonical_clone_v1(candidate)
    inventories = [item for item in source_context["tax_population_inventory"]
                   if item.get("recognition_rate_effect_control", {}).get("status") == "PASS"]
    if not inventories:
        return canonical_clone_v1(candidate)
    suppressed, retained = [], []
    for mapping in candidate["mappings"]:
        refs = mapping.get("source_refs") or []
        matches = []
        if mapping.get("role") in {"NON_TAXABLE_AGGREGATE", "NON_DEDUCTIBLE_EXPENSE"}:
            for inventory in inventories:
                control = inventory["recognition_rate_effect_control"]
                for source in control["adjustment_source_rows"]:
                    for ref in refs:
                        if (type(ref.get("locator")) is dict
                                and all(same_typed_json_v1(ref["locator"].get(key), value)
                                        for key, value in inventory["locator"].items())
                                and ref.get("row_ordinal") == source["row_ordinal"]):
                            matches.append((inventory, source, ref))
        if not matches:
            retained.append(canonical_clone_v1(mapping))
            continue
        direct_observation = (mapping.get("state") == "SOURCE_OBSERVED_ROLE_ROW"
                              or _mapping_is_direct_source_observation(mapping))
        if len(refs) != 1 or len(matches) != 1 or not direct_observation:
            return _unresolved_from_candidate(candidate, reason="RECOGNITION_RATE_SOURCE_ONLY_MAPPING_IDENTITY_AMBIGUOUS",
                                              evidence={"mapping": mapping, "source_context_receipt": source_context})
        inventory, source, ref = matches[0]
        def touches_source(value: Any, *, source_row_ordinal: int = ref["row_ordinal"],
                           source_locator: Mapping[str, Any] = inventory["locator"]) -> bool:
            if type(value) is list:
                return any(touches_source(item) for item in value)
            if type(value) is not dict:
                return False
            if (value.get("row_ordinal") == source_row_ordinal and type(value.get("locator")) is dict
                    and all(same_typed_json_v1(value["locator"].get(key), item)
                            for key, item in source_locator.items())):
                return True
            return any(touches_source(item) for item in value.values())

        values = mapping.get("values")
        if (mapping.get("unit") != inventory["unit_axis"].get("canonical_unit")
                or not same_typed_json_v1(ref.get("money_column_ordinals"), inventory["lane_axis"]["money_column_ordinals"])
                or any(not same_typed_json_v1(ref.get(key), source[key])
                       for key in ("row_kind", "label_exact", "hierarchy_path_exact"))
                or type(values) is not list or len(values) != 2
                or any(type(value) is not dict or value.get("source_text") != raw
                       or not same_typed_json_v1(value.get("coefficient"), coefficient)
                       or value.get("state") != _source_money(raw).get("state")
                       for value, raw, coefficient in zip(values, source["source_values_exact"], source["parsed_values"], strict=True))):
            return _unresolved_from_candidate(candidate, reason="RECOGNITION_RATE_SOURCE_ONLY_OBSERVATION_DRIFT",
                                              evidence={"mapping": mapping, "source_context_receipt": source_context})
        # Do not detach a value-level income equation from its operands and
        # then pretend that equation still certifies an income mapping.
        if any(mapping["role"] in equation.get("component_roles", [])
               or mapping["role"] == equation.get("result_role")
               or touches_source(equation)
               for equation in candidate.get("closure_receipt", {}).get("equations", [])):
            return _unresolved_from_candidate(candidate, reason="RECOGNITION_RATE_INCOME_EQUATION_REQUIRES_SEPARATE_PROOF",
                                              evidence={"mapping": mapping, "source_context_receipt": source_context})
        if (touches_source(candidate.get("closure_receipt", {}).get("derived_role_receipts", []))
                or any(other is not mapping and not _mapping_is_direct_source_observation(other)
                       and touches_source(other.get("source_refs") or []) for other in candidate["mappings"])):
            return _unresolved_from_candidate(candidate, reason="RECOGNITION_RATE_DERIVED_INCOME_REQUIRES_SEPARATE_PROOF",
                                              evidence={"mapping": mapping, "source_context_receipt": source_context})
        suppressed.append({"mapping": canonical_clone_v1(mapping),
                           "population_inventory_id": inventory["receipt_id"],
                           "independent_forward_control_id": inventory["recognition_rate_effect_control"]["control_id"],
                           "source_row_exact": canonical_clone_v1(source),
                           "measurement_basis": "TAX_EFFECT_NOT_TAXABLE_INCOME_ADJUSTMENT",
                           "schema_exported": False})
    if not suppressed:
        return canonical_clone_v1(candidate)
    material = {
        "original_candidate_id": candidate["candidate_id"],
        "source_context_receipt_id": source_context["receipt_id"],
        "suppressed_income_basis_mappings": suppressed,
        "independent_source_controls": [canonical_clone_v1(item) for item in inventories],
        "source_values_changed": False,
        "rule": "ONLY_COMPLETE_EXACT_AUTHENTICATED_RATE_EFFECT_SOURCE_IDENTITIES_RETAINED_NOT_INCOME_SCHEMA",
    }
    output = canonical_clone_v1(candidate)
    output["mappings"] = retained
    output["closure_receipt"]["recognition_rate_source_only_receipt"] = {
        **material, "receipt_id": "gjitfav1:recognition-rate-source-only:" + canonical_json_sha256_v1(material),
    }
    output["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1({key: value for key, value in output.items() if key != "candidate_id"})
    return output


def _merge_note_and_primary_candidates(
    note_candidate: Mapping[str, Any],
    primary_candidate: Mapping[str, Any],
    *,
    descriptor: Mapping[str, Any],
    repair_receipts: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    strategy: str,
    page_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if primary_candidate.get("reasons") == ["ALGORITHM_PRINTED_PRIMARY_ROOT_SOURCE_OWNERSHIP_UNPROVEN"]:
        return canonical_clone_v1(primary_candidate)
    if note_candidate.get("status") != READY or primary_candidate.get("status") != READY:
        raise _error("income-tax independent source candidate is not ready")
    note_by_role = {item["role"]: item for item in note_candidate["mappings"]}
    primary_by_role = {item["role"]: item for item in primary_candidate["mappings"]}
    if len(note_by_role) != len(note_candidate["mappings"]) or len(primary_by_role) != len(
        primary_candidate["mappings"]
    ):
        raise _error("income-tax independent source role axis is duplicate")
    conflict_evidence = {
        "note_candidate_id": note_candidate["candidate_id"],
        "note_closure_receipt": canonical_clone_v1(note_candidate["closure_receipt"]),
        "note_mappings": canonical_clone_v1(note_candidate["mappings"]),
        "primary_candidate_id": primary_candidate["candidate_id"],
        "primary_closure_receipt": canonical_clone_v1(primary_candidate["closure_receipt"]),
        "primary_mappings": canonical_clone_v1(primary_candidate["mappings"]),
        "primary_projection_receipt": canonical_clone_v1(descriptor),
        "source_repair_receipts": canonical_clone_v1(list(repair_receipts)),
    }
    population_conflicts = _at_rate_cross_presentation_conflicts(
        note_candidate, compiled_specs=compiled_specs,
    )
    if population_conflicts:
        return _unresolved_from_candidate(
            note_candidate,
            reason="CURRENT_TAX_AT_RATE_CROSS_PRESENTATION_POPULATION_AMBIGUITY",
            evidence={**conflict_evidence, "at_rate_population_conflicts": population_conflicts},
        )
    overlap_pairs = []
    for role, note_mapping in note_by_role.items():
        primary_mapping = primary_by_role.get(role)
        if primary_mapping is None:
            continue
        if role != "FAMILY_ROOT_TOTAL" or _mapping_is_direct_source_observation(
            note_mapping
        ):
            overlap_pairs.append((note_mapping, primary_mapping))
    cross_source_orientation = _cross_source_orientation(overlap_pairs)
    if overlap_pairs and cross_source_orientation is None:
        return _unresolved_from_candidate(
            note_candidate,
            reason="CONFLICTING_DIRECT_NOTE_AND_PRIMARY_INCOME_TAX_PRESENTATIONS",
            evidence=conflict_evidence,
        )
    signed_display_proof = None
    if cross_source_orientation == -1:
        signed_display_proof = _note_primary_signed_display_proof(
            note_candidate, primary_candidate, descriptor=descriptor,
            page_records=page_records, compiled_specs=compiled_specs,
        )
    if cross_source_orientation == -1 and signed_display_proof is None:
        return _unresolved_from_candidate(
            note_candidate,
            reason="SIGN_INVERTED_DIRECT_NOTE_AND_PRIMARY_INCOME_TAX_PRESENTATIONS",
            evidence=conflict_evidence,
        )
    merged_by_role = canonical_clone_v1(note_by_role)
    suppressed_primary = []
    suppressed_note_roots = []
    suppressed_cross_source_note = []
    for role, mapping in primary_by_role.items():
        if role == "FAMILY_ROOT_TOTAL":
            note_root = merged_by_role.get(role)
            if note_root is None:
                merged_by_role[role] = canonical_clone_v1(mapping)
            elif not _mapping_is_direct_source_observation(note_root):
                suppressed_note_roots.append(canonical_clone_v1(note_root))
                merged_by_role[role] = canonical_clone_v1(mapping)
            else:
                note_lanes = _observed_mapping_lane_axis(note_root)
                primary_lanes = _observed_mapping_lane_axis(mapping)
                if primary_lanes > note_lanes:
                    suppressed_note_roots.append(canonical_clone_v1(note_root))
                    merged_by_role[role] = canonical_clone_v1(mapping)
                else:
                    suppressed_primary.append(canonical_clone_v1(mapping))
        elif role not in merged_by_role:
            merged_by_role[role] = canonical_clone_v1(mapping)
        else:
            note_lanes = _observed_mapping_lane_axis(merged_by_role[role])
            primary_lanes = _observed_mapping_lane_axis(mapping)
            if primary_lanes > note_lanes:
                suppressed_cross_source_note.append(
                    canonical_clone_v1(merged_by_role[role])
                )
                merged_by_role[role] = canonical_clone_v1(mapping)
            else:
                suppressed_primary.append(canonical_clone_v1(mapping))
    role_order = [item["role"] for item in compiled_specs["topology"]["children"]]
    role_order.append("FAMILY_ROOT_TOTAL")
    order = {role: ordinal for ordinal, role in enumerate(role_order)}
    merged = canonical_clone_v1(note_candidate)
    merged["mappings"] = sorted(
        merged_by_role.values(),
        key=lambda item: (order.get(item["role"], len(order)), item["role"]),
    )
    proof = {
        "primary_candidate_id": primary_candidate["candidate_id"],
        "primary_closure_receipt": canonical_clone_v1(primary_candidate["closure_receipt"]),
        "rule": (
            "NOTE_DIRECT_ROLES_PRESERVED_PRIMARY_DIRECT_ROOT_AND_ONLY_NOTE_ABSENT_"
            "ROLES_ADDED_DUPLICATE_PRIMARY_ROLES_RETAINED_AS_SOURCE_CONTROL"
        ),
        "cross_source_sign_orientation": cross_source_orientation or 1,
        "suppressed_cross_source_note_mappings": suppressed_cross_source_note,
        "suppressed_note_root_mappings": suppressed_note_roots,
        "suppressed_duplicate_primary_mappings": suppressed_primary,
    }
    comparison_orientations = {}
    if signed_display_proof is not None:
        note_ids = {mapping["item_mapping_id"] for mapping in note_candidate["mappings"]}
        root = merged_by_role.get("FAMILY_ROOT_TOTAL")
        root_from_note = root is not None and root["item_mapping_id"] in note_ids
        comparison_orientations = {
            role: 1 if (mapping["item_mapping_id"] in note_ids) == root_from_note else -1
            for role, mapping in merged_by_role.items()
            if role in {"CURRENT_TAX_PARENT", "DEFERRED_TAX_NET", "FAMILY_ROOT_TOTAL"}
        }
        proof["signed_display_proof"] = signed_display_proof
        proof["source_presentation_comparison_orientations"] = comparison_orientations
    proof["post_merge_root_closure"], mismatch = _post_merge_root_closure(
        merged, comparison_orientations=comparison_orientations,
    )
    if mismatch:
        return _unresolved_from_candidate(
            merged, reason="POST_MERGE_INCOME_TAX_ROOT_EQUATION_CONFLICT", evidence=proof
        )
    return _reseal_candidate(
        merged,
        descriptor=descriptor,
        repair_receipts=repair_receipts,
        strategy=strategy,
        compiled_specs=compiled_specs,
        restore_primary_source_refs=False,
        primary_candidate_proof=proof,
    )


def _root_control_orientation_receipt(
    candidate: Mapping[str, Any], control: Mapping[str, Any], root_mapping: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Reuse an independently proven same-table orientation, never infer it from a root."""
    matched = []
    adapter = candidate.get("closure_receipt", {}).get("income_tax_adapter_receipt")
    seen = set()
    while type(adapter) is dict:
        material = {key: value for key, value in adapter.items() if key != "receipt_id"}
        if adapter.get("receipt_id") != "gjitfav1:candidate:" + canonical_json_sha256_v1(material):
            raise _error("income-tax root-control presentation proof drifted")
        if adapter["receipt_id"] in seen:
            raise _error("income-tax root-control presentation proof is cyclic")
        seen.add(adapter["receipt_id"])
        proof = adapter.get("primary_candidate_proof", {})
        primary = adapter.get("primary_projection_receipt")
        primary_matches_target = (
            type(primary) is dict and type(root_mapping) is dict
            and bool(root_mapping.get("source_refs"))
            and root_mapping.get("unit") == primary["canonical_unit"]
            and all(
                all(ref["locator"].get(key) == value for key, value in primary["locator"].items())
                and same_typed_json_v1(ref.get("money_column_ordinals"), primary["money_column_ordinals"])
                for ref in root_mapping["source_refs"]
            )
        )
        signed_display = proof.get("signed_display_proof")
        if type(signed_display) is dict and primary_matches_target:
            signed_material = {key: value for key, value in signed_display.items() if key != "receipt_id"}
            if signed_display.get("receipt_id") != "gjitfav1:signed-display:" + canonical_json_sha256_v1(signed_material):
                raise _error("income-tax signed display control proof drifted")
            if not same_typed_json_v1(
                signed_display.get("primary_expense_display_receipt"), primary.get("expense_display_receipt")
            ):
                raise _error("income-tax signed display primary bridge binding drifted")
            for source_table in signed_display["note_source_tables"]:
                if not all(same_typed_json_v1(source_table.get(key), control.get(key)) for key in (
                    "locator", "original_page_json_sha256", "original_table_json_sha256",
                    "canonical_unit", "money_column_ordinals",
                )):
                    continue
                overlaps = [item for item in signed_display["independent_nonroot_overlaps"]
                            if item["note_mapping"].get("source_refs") and all(
                                all(same_typed_json_v1(ref["locator"].get(key), value)
                                    for key, value in source_table["locator"].items())
                                and same_typed_json_v1(ref.get("money_column_ordinals"), source_table["money_column_ordinals"])
                                for ref in item["note_mapping"]["source_refs"]
                            ) and _cross_source_mapping_signs(
                                item["note_mapping"], item["primary_mapping"], allow_sign_inversion=True
                            ) == frozenset({-1})]
                if overlaps:
                    matched.append({
                        "adapter_receipt_id": adapter["receipt_id"],
                        "signed_display_receipt_id": signed_display["receipt_id"],
                        "independent_overlap_orientation": -1,
                        "primary_projection_sha256": canonical_json_sha256_v1(primary),
                        "independent_same_table_nonroot_overlap_receipts": canonical_clone_v1(overlaps),
                    })
        if (
            adapter.get("strategy") == "DIRECT_SUPPLEMENTAL_NOTE_PLUS_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION"
            and proof.get("cross_source_sign_orientation") == -1 and primary_matches_target
        ):
            for descriptor in proof.get("supplemental_projection_receipts", []):
                if (
                    same_typed_json_v1(descriptor["locator"], control["locator"])
                    and descriptor["original_page_json_sha256"] == control["original_page_json_sha256"]
                    and descriptor["original_table_json_sha256"] == control["original_table_json_sha256"]
                    and descriptor["canonical_unit"] == control["canonical_unit"]
                    and same_typed_json_v1(descriptor["money_column_ordinals"], control["money_column_ordinals"])
                ):
                    primary_rows = {row["role"]: row for row in primary["rows"]}
                    overlaps = []
                    for mapping in proof.get("suppressed_cross_source_supplemental_mappings", []):
                        role = mapping["role"]
                        if role == "FAMILY_ROOT_TOTAL" or role not in primary_rows:
                            continue
                        if not mapping.get("source_refs") or not all(
                            all(ref["locator"].get(key) == value for key, value in descriptor["locator"].items())
                            and same_typed_json_v1(ref.get("money_column_ordinals"), descriptor["money_column_ordinals"])
                            for ref in mapping["source_refs"]
                        ):
                            continue
                        primary_row = primary_rows[role]
                        primary_mapping = {
                            "unit": primary["canonical_unit"],
                            "values": [_source_money(value) for value in primary_row["source_values_exact"]],
                        }
                        if _cross_source_mapping_signs(mapping, primary_mapping, allow_sign_inversion=True) == frozenset({-1}):
                            overlaps.append({
                                "supplemental_source_mapping": canonical_clone_v1(mapping),
                                "primary_source_row": canonical_clone_v1(primary_row),
                                "primary_source_unit": primary["canonical_unit"],
                                "orientation_signs": [-1],
                            })
                    if not overlaps:
                        continue
                    matched.append({
                        "adapter_receipt_id": adapter["receipt_id"],
                        "descriptor_id": descriptor["descriptor_id"],
                        "independent_overlap_orientation": -1,
                        "primary_projection_sha256": canonical_json_sha256_v1(primary),
                        "independent_same_table_nonroot_overlap_receipts": overlaps,
                    })
        adapter = proof.get("primary_closure_receipt", {}).get("income_tax_adapter_receipt")
    material = {
        "control_id": control["control_id"],
        "matched_same_source_table_proofs": matched,
        "orientation": -1 if matched else 1,
        "rule": "ONLY_REPLAYED_SAME_TABLE_INDEPENDENT_ROLE_OVERLAP_ORIENTATION_NO_ROOT_SIGN_INFERENCE_NO_SOURCE_VALUE_CHANGE",
    }
    return {**material, "receipt_id": "gjitfav1:root-presentation:" + canonical_json_sha256_v1(material)}


def _authenticated_root_comparison_orientations(candidate: Mapping[str, Any]) -> dict[str, int]:
    adapter = candidate.get("closure_receipt", {}).get("income_tax_adapter_receipt", {})
    proof = adapter.get("primary_candidate_proof", {})
    signed = proof.get("signed_display_proof")
    if signed is None:
        return {}
    for receipt, prefix in (
        (adapter, "gjitfav1:candidate:"), (signed, "gjitfav1:signed-display:"),
        (proof.get("post_merge_root_closure"), "gjitfav1:post-merge-root-closure:"),
    ):
        if type(receipt) is not dict:
            raise _error("income-tax signed comparison receipt missing")
        material = {key: value for key, value in receipt.items() if key != "receipt_id"}
        if receipt.get("receipt_id") != prefix + canonical_json_sha256_v1(material):
            raise _error("income-tax signed comparison receipt drifted")
    closure = proof["post_merge_root_closure"]
    roles = ("CURRENT_TAX_PARENT", "DEFERRED_TAX_NET", "FAMILY_ROOT_TOTAL")
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    if not same_typed_json_v1(closure["mappings"], [by_role[role] for role in roles if role in by_role]):
        raise _error("income-tax signed comparison source mapping axis drifted")
    orientations = proof.get("source_presentation_comparison_orientations")
    if type(orientations) is not dict or not same_typed_json_v1(
        orientations, closure.get("source_presentation_comparison_orientations")
    ):
        raise _error("income-tax signed comparison orientation receipt drifted")
    return canonical_clone_v1(orientations)


def _current_tax_payable_subtotal_conflicts_v1(
    candidate: Mapping[str, Any], *, source_context: Mapping[str, Any],
    repaired_records: Sequence[Mapping[str, Any]], compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Withhold a weak payable subtotal's expense role from its printed row sequence.

    A computed tax row followed by a prior-year payable adjustment and the weak
    subtotal is source evidence of an unproved role. Values, ROOT and equations
    cannot supply the missing role, including when every displayed value is zero.
    """
    conflicts = []
    for mapping in candidate.get("mappings", []):
        if mapping.get("role") != "CURRENT_TAX_PARENT":
            continue
        for ref in mapping.get("source_refs", []):
            if _without_leading_ordinal(_normalized(ref.get("label_exact"))) != "thue tndn trong nam":
                continue
            locator = _record_locator(ref["locator"], section_id=ref["locator"]["section_id"],
                                      table_id=ref["locator"]["table_id"])
            records = [record for record in repaired_records
                       if record["page_json_version_id"] == locator["page_json_version_id"]]
            if len(records) != 1 or not same_typed_json_v1(
                _record_locator(records[0], section_id=locator["section_id"], table_id=locator["table_id"]), locator
            ):
                raise _error("income-tax payable-subtotal source locator drifted")
            page = records[0]["page_json"]
            section, table = _source_table(page, section_id=locator["section_id"], table_id=locator["table_id"])
            if section.get("content_kind") != "FINANCIAL_NOTE":
                continue
            context_material = {key: value for key, value in source_context.items() if key != "receipt_id"}
            if source_context.get("receipt_id") != "gjitfav1:source-context:" + canonical_json_sha256_v1(context_material):
                raise _error("income-tax payable-subtotal source context receipt drifted")
            populations = [item for item in source_context["tax_population_inventory"]
                           if same_typed_json_v1(item["locator"], locator)]
            if len(populations) != 1:
                raise _error("income-tax payable-subtotal source population join is not unique")
            population = populations[0]
            material = {key: value for key, value in population.items() if key != "receipt_id"}
            if (population.get("receipt_id") != "gjitfav1:tax-population:" + canonical_json_sha256_v1(material)
                    or population["original_page_json_sha256"] != canonical_json_sha256_v1(page)
                    or population["original_table_json_sha256"] != canonical_json_sha256_v1(table)
                    or not same_typed_json_v1(population["source_table_rows_exact"], table.get("rows") or [])):
                raise _error("income-tax payable-subtotal original source hashes drifted")
            money = population["lane_axis"]["money_column_ordinals"]
            rows = _supplemental_source_rows(table, money_column_ordinals=money,
                                            role_alias_axis=_supplemental_role_alias_axis(compiled_specs))
            if not same_typed_json_v1(rows, population["source_table_row_axis"]):
                raise _error("income-tax payable-subtotal source row axis drifted")
            ordinal = ref.get("row_ordinal")
            if type(ordinal) is not int or not 1 <= ordinal <= len(rows):
                raise _error("income-tax payable-subtotal source row ordinal drifted")
            selected = rows[ordinal - 1]
            if (not same_typed_json_v1(ref.get("money_column_ordinals"), money)
                    or ref.get("row_id") != f"r{ordinal}"
                    or any(not same_typed_json_v1(ref.get(key), selected[key])
                           for key in ("label_exact", "row_kind", "hierarchy_path_exact"))):
                raise _error("income-tax payable-subtotal selected source row drifted")
            computed = [row for row in rows[:ordinal - 1]
                        if row["matched_role"] in {"CURRENT_TAX_AT_RATE", "STATUTORY_TAX_AMOUNT_SOURCE_ONLY"}]
            if not computed:
                continue
            start = computed[-1]
            interval = rows[start["row_ordinal"]:ordinal - 1]
            if any(row["row_kind"] == "GROUP" for row in interval):
                continue
            def same_printed_scope(
                row: Mapping[str, Any], *, selected_row: Mapping[str, Any] = selected,
            ) -> bool:
                path, target = row["hierarchy_path_exact"], selected_row["hierarchy_path_exact"]
                return (type(path) is list and bool(path) and type(target) is list and bool(target)
                        and same_typed_json_v1(path[:-1], target[:-1]))
            if not same_printed_scope(start):
                continue
            prior = [row for row in interval if same_printed_scope(row) and (
                row["matched_role"] == "PRIOR_PERIOD_TAX_ADJUSTMENT" or (
                    re.match(r"dieu chinh\b", row["normalized_label"]) is not None
                    and re.search(r"\bthue (?:tndn|thu nhap doanh nghiep)\b", row["normalized_label"]) is not None
                    and re.search(r"\bphai nop\b", row["normalized_label"]) is not None
                    and re.search(r"\b(?:cac )?nam truoc\b", row["normalized_label"]) is not None
                ))]
            if not prior:
                continue
            proof = {
                "status": "ALGORITHM_HOLD", "classification": "ALGORITHM_ROLE_UNPROVEN",
                "candidate_id_before_hold": candidate["candidate_id"],
                "selected_mapping": canonical_clone_v1(mapping), "selected_source_ref": canonical_clone_v1(ref),
                "source_population_receipt_id": population["receipt_id"],
                "source_population_sha256": canonical_json_sha256_v1(population),
                "source_locator": canonical_clone_v1(locator),
                "original_page_json_sha256": population["original_page_json_sha256"],
                "original_table_json_sha256": population["original_table_json_sha256"],
                "computed_tax_source_row": canonical_clone_v1(start),
                "intervening_prior_year_adjustment_rows": canonical_clone_v1(prior),
                "weak_subtotal_source_row": canonical_clone_v1(selected),
                "source_values_changed": False,
                "rule": "SOURCE_OWNED_COMPUTED_TAX_PRIOR_YEAR_PAYABLE_ADJUSTMENT_WEAK_SUBTOTAL_CANNOT_PROVE_CURRENT_EXPENSE_ROLE",
            }
            conflicts.append({**proof, "receipt_id": "gjitfav1:payable-subtotal-role:" + canonical_json_sha256_v1(proof)})
    return conflicts


def _registered_negative_source_label_conflicts_v1(
    candidate: Mapping[str, Any], *, source_context: Mapping[str, Any],
    repaired_records: Sequence[Mapping[str, Any]], compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    try:
        observed = source_label_discrepancy.registered_negative_source_label_observation_axis_v1(repaired_records)
        if any(item["classification"] == source_label_discrepancy.PRINTED_DASH_CLASSIFICATION
               and item["source_section_kind"] == "FINANCIAL_NOTE" for item in observed):
            # The note source uses the actual tax population, never PRIMARY
            # statement ownership. Recompute its complete source row inventory;
            # resealing caller-provided population hashes cannot replace it.
            if not same_typed_json_v1(
                source_context.get("tax_population_inventory"),
                _tax_population_inventory(repaired_records, compiled_specs=compiled_specs),
            ):
                raise _error("income-tax printed-dash NOTE population replay drifted")
        return source_label_discrepancy.registered_negative_source_label_conflicts_v1(
            candidate, source_context=source_context, repaired_records=repaired_records, compiled_specs=compiled_specs,
        )
    except source_label_discrepancy.IncomeTaxSourceLabelDiscrepancyV1Error as error:
        raise _error(str(error)) from error


def _non_taxable_net_semantic_conflicts_v1(candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Withhold a NON_TAXABLE_AGGREGATE whose printed source is not a non-taxable deduction.

    A positive stored coefficient (an add-back) or a cited row printed as a mixed
    "tăng/(giảm)" adjustment is a net adjustment, not proven non-taxable income.
    Printed signs are kept; nothing is relabelled, flipped or recomputed.
    """
    conflicts = []
    for mapping in candidate.get("mappings", []):
        if mapping.get("role") != "NON_TAXABLE_AGGREGATE":
            continue
        positive = [index for index, value in enumerate(mapping.get("values") or [])
                    if type(value.get("coefficient")) is int and value["coefficient"] > 0]
        mixed = [ref.get("label_exact") for ref in mapping.get("source_refs") or []
                 if re.search(r"\btang\b.*\bgiam\b", _normalized(ref.get("label_exact") or ""))]
        if positive or mixed:
            conflicts.append({"mapping": canonical_clone_v1(mapping), "positive_lane_indexes": positive,
                              "mixed_increase_decrease_labels": mixed,
                              "classification": "ALGORITHM_NON_TAXABLE_NET_SEMANTICS_UNPROVEN"})
    return conflicts


def _seal_income_tax_source_controls(
    candidate: Mapping[str, Any], *, source_context: Mapping[str, Any],
    repaired_records: Sequence[Mapping[str, Any]], compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    if candidate.get("status") != READY:
        return canonical_clone_v1(candidate)
    negative_source_labels = _registered_negative_source_label_conflicts_v1(
        candidate, source_context=source_context, repaired_records=repaired_records, compiled_specs=compiled_specs,
    )
    if negative_source_labels:
        printed_dash = any(item["classification"] == source_label_discrepancy.PRINTED_DASH_CLASSIFICATION
                           for item in negative_source_labels)
        reason = "SOURCE_PRINTED_DASH_VS_JSON_NUMERIC_DISCREPANCY" if printed_dash else "SOURCE_TRANSCRIPTION_DISCREPANCY"
        return _unresolved_from_candidate(
            candidate, reason=reason,
            evidence={"classification": source_label_discrepancy.PRINTED_DASH_CLASSIFICATION if printed_dash else "SOURCE_TRANSCRIPTION_DISCREPANCY",
                      "registered_negative_source_label_observations": negative_source_labels,
                      "source_context_receipt": canonical_clone_v1(source_context)},
        )
    payable_subtotal_conflicts = _current_tax_payable_subtotal_conflicts_v1(
        candidate, source_context=source_context, repaired_records=repaired_records, compiled_specs=compiled_specs,
    )
    if payable_subtotal_conflicts:
        return _unresolved_from_candidate(
            candidate, reason="ALGORITHM_CURRENT_TAX_PARENT_PAYABLE_SUBTOTAL_ROLE_UNPROVEN",
            evidence={"classification": "ALGORITHM_ROLE_UNPROVEN",
                      "payable_subtotal_role_conflicts": payable_subtotal_conflicts,
                      "source_context_receipt": canonical_clone_v1(source_context)},
        )
    non_taxable_conflicts = _non_taxable_net_semantic_conflicts_v1(candidate)
    if non_taxable_conflicts:
        return _unresolved_from_candidate(
            candidate, reason="ALGORITHM_NON_TAXABLE_AGGREGATE_NET_SEMANTICS_UNPROVEN",
            evidence={"classification": "ALGORITHM_ROLE_UNPROVEN",
                      "non_taxable_net_semantic_conflicts": non_taxable_conflicts,
                      "source_context_receipt": canonical_clone_v1(source_context)},
        )
    competing_stages = [item for item in source_context["tax_population_inventory"]
                        if item["competing_taxable_stage_control"]["status"] == "ALGORITHM_HOLD"]
    if competing_stages:
        return _unresolved_from_candidate(
            candidate, reason="ALGORITHM_TAXABLE_INCOME_STAGE_BASIS_AMBIGUITY",
            evidence={"source_context_receipt": canonical_clone_v1(source_context),
                      "competing_taxable_stage_populations": canonical_clone_v1(competing_stages),
                      "classification": "ALGORITHM_SCHEMA_BASIS_OWNERSHIP_UNPROVEN_NOT_ISSUER_CONFLICT"},
        )
    invalid_recognition = [item for item in source_context["tax_population_inventory"]
                           if item.get("recognition_expense_frontier", {}).get("status") == "ALGORITHM_HOLD"
                           or item.get("recognition_rate_effect_control", {}).get("status") == "ALGORITHM_HOLD"]
    if invalid_recognition:
        return _unresolved_from_candidate(
            candidate, reason="INCOME_TAX_PRINTED_RECOGNITION_POPULATION_INCOMPLETE",
            evidence={"source_context_receipt": canonical_clone_v1(source_context),
                      "invalid_recognition_populations": invalid_recognition},
        )
    invalid_primary_periods = [source for source in source_context["document_statement_period_inventory"]["sources"]
                               if source["statement_type"] == "INCOME_STATEMENT" and source["tax_expense_source_rows"]
                               and not source["lane_axis"].get("complete")]
    if invalid_primary_periods:
        return _unresolved_from_candidate(
            candidate, reason="TYPED_PRIMARY_TAX_SOURCE_PERIOD_AXIS_INCOMPLETE",
            evidence={"source_context_receipt": canonical_clone_v1(source_context), "invalid_primary_period_sources": invalid_primary_periods},
        )
    primary_source_period_receipts = [
        _source_period_correspondence_receipt(
            left_locator=source["locator"], right_locator=source["locator"],
            left_money_column_ordinals=source["lane_axis"]["money_column_ordinals"],
            right_money_column_ordinals=source["lane_axis"]["money_column_ordinals"],
            page_records=repaired_records, compiled_specs=compiled_specs,
            document_period_inventory=source_context["document_statement_period_inventory"],
        )
        for source in source_context["document_statement_period_inventory"]["sources"]
        if source["statement_type"] == "INCOME_STATEMENT" and source["tax_expense_source_rows"]
    ]
    year_domain_conflicts = []
    expense_population_scope_receipts = []
    expense_population_period_receipts = []
    expense_population_period_conflicts = []
    cross_source_mapping_period_receipts = []
    # A direct NOTE fallback cannot bypass a printed policy merely because
    # its independent PRIMARY counterpart is absent. Legacy no-policy routes
    # retain their own independently validated period contracts.
    period_inventory = source_context["document_statement_period_inventory"]
    if (period_inventory["document_comparative_flow_policy_receipt"]["status"] != "NOT_APPLICABLE"
            or period_inventory.get("registered_part_period_contexts")):
        source_pages = {item["page_json_version_id"]: item["page_json"] for item in repaired_records}
        for population in source_context["tax_population_inventory"]:
            locator = population["locator"]
            note_section, note_table = _source_table(source_pages[locator["page_json_version_id"]],
                                                   section_id=locator["section_id"], table_id=locator["table_id"])
            note_lane = population["lane_axis"]
            if _relative_flow_column_paths(note_table, note_lane) is not None:
                cross_source_mapping_period_receipts.append(_source_period_correspondence_receipt(
                    left_locator=locator, right_locator=locator,
                    left_money_column_ordinals=note_lane["money_column_ordinals"],
                    right_money_column_ordinals=note_lane["money_column_ordinals"],
                    page_records=repaired_records, compiled_specs=compiled_specs,
                    document_period_inventory=period_inventory,
                ))
    primary = candidate.get("closure_receipt", {}).get("income_tax_adapter_receipt", {}).get("primary_projection_receipt")
    if type(primary) is not dict and any(item["current_year_frontier"] is not None
                                       or item.get("recognition_expense_frontier", {}).get("status") == "PASS"
                                       for item in source_context["tax_population_inventory"]):
        return _unresolved_from_candidate(
            candidate, reason="CURRENT_TAX_EXPENSE_SOURCE_POPULATION_WITHOUT_AUTHENTICATED_COUNTERPART",
            evidence={"source_context_receipt": canonical_clone_v1(source_context),
                      "classification": "ALGORITHM_NOTE_ONLY_POPULATION_ROUTE_NOT_YET_AUTHENTICATED"},
        )
    if type(primary) is dict:
        pages = {item["page_json_version_id"]: item["page_json"] for item in repaired_records}
        section, table = _source_table(pages[primary["locator"]["page_json_version_id"]],
                                       section_id=primary["locator"]["section_id"], table_id=primary["locator"]["table_id"])
        primary_surfaces = [section.get("title_exact"), table.get("title_exact")]
        primary_ancestries = [item["hierarchy_path_exact"][:-1] for item in primary["rows"]
                             if type(item.get("hierarchy_path_exact")) is list]
        primary_surfaces.extend(value for ancestry in primary_ancestries for value in ancestry)
        primary_scope = _printed_population_qualifiers(primary_surfaces)
        primary_lane = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
        primary_duration_lengths = _printed_duration_lengths(table, primary["money_column_ordinals"], section=section)
        document_scope = source_context["document_report_scope_receipt"]
        if not primary_scope and document_scope["report_scope"] is not None:
            primary_scope = [document_scope["report_scope"]]
        selectors = []
        for mapping in candidate["mappings"]:
            for ref in mapping.get("source_refs") or []:
                selectors.append({"locator": ref["locator"], "money_column_ordinals": ref["money_column_ordinals"]})
        primary_proof = candidate.get("closure_receipt", {}).get("income_tax_adapter_receipt", {}).get("primary_candidate_proof")
        if type(primary_proof) is dict:
            selectors.extend(primary_proof.get("supplemental_projection_receipts") or [])
        # Corroborating PRIMARY presentations retain source authority even
        # when precision selection means their cells are not exported.
        selectors.extend({"locator": source["locator"], "money_column_ordinals": source["lane_axis"]["money_column_ordinals"]}
                         for source in source_context["document_statement_period_inventory"]["sources"]
                         if source["statement_type"] == "INCOME_STATEMENT" and source["tax_expense_source_rows"])
        seen_selectors = set()
        for selector in selectors:
            original_selector = {"locator": _record_locator(selector["locator"], section_id=selector["locator"]["section_id"], table_id=selector["locator"]["table_id"]),
                                 "money_column_ordinals": selector["money_column_ordinals"]}
            identity = canonical_json_sha256_v1(original_selector)
            if identity in seen_selectors or (same_typed_json_v1(original_selector["locator"], primary["locator"])
                                              and same_typed_json_v1(original_selector["money_column_ordinals"], primary["money_column_ordinals"])):
                continue
            seen_selectors.add(identity)
            cross_source_mapping_period_receipts.append(_source_period_correspondence_receipt(
                left_locator=original_selector["locator"], right_locator=primary["locator"],
                left_money_column_ordinals=original_selector["money_column_ordinals"], right_money_column_ordinals=primary["money_column_ordinals"],
                page_records=repaired_records, compiled_specs=compiled_specs,
                document_period_inventory=source_context["document_statement_period_inventory"],
            ))
        primary_outline = _primary_printed_outline_frontier_receipt_v1(section, table)
        permitted_outline_tokens = {
            (item["row_ordinal"], item["hierarchy_path_ordinal"] - 1, item["source_token_exact"])
            for item in (primary_outline or {}).get("permitted_frontier_tokens", [])
        }
        unknown_primary_ancestry = []
        used_primary_outline = False
        for item in primary["rows"]:
            path, ordinal = item.get("hierarchy_path_exact"), item.get("row_ordinal")
            if type(path) is not list:
                continue
            for index, value in enumerate(path[:-1]):
                exact_source_row = (type(ordinal) is int and 1 <= ordinal <= len(table["rows"])
                                    and same_typed_json_v1(path, table["rows"][ordinal - 1].get("hierarchy_path_exact")))
                if exact_source_row and (ordinal, index, value) in permitted_outline_tokens:
                    used_primary_outline = True
                    continue
                if _without_leading_ordinal(_normalized(value)) not in _ROOT_LABELS:
                    unknown_primary_ancestry.append(value)
        # Validation-only PERIOD has no mapping.  Authenticate the source
        # population itself, including its parent and adjustment rows.
        expense_boundaries = [(inventory, inventory["current_year_frontier"], "YEAR_OR_PERIOD")
                              for inventory in source_context["tax_population_inventory"]
                              if inventory["current_year_frontier"] is not None]
        expense_boundaries.extend((inventory, inventory["recognition_expense_frontier"], "PRINTED_RECOGNITION")
                                  for inventory in source_context["tax_population_inventory"]
                                  if inventory.get("recognition_expense_frontier", {}).get("status") == "PASS")
        for inventory, boundary, boundary_kind in expense_boundaries:
            locator = inventory["locator"]
            note_section, note_table = _source_table(pages[locator["page_json_version_id"]],
                                                   section_id=locator["section_id"], table_id=locator["table_id"])
            note_lane = inventory["lane_axis"]
            note_duration_lengths = _printed_duration_lengths(note_table, note_lane["money_column_ordinals"], section=note_section)
            period_proof = _source_period_correspondence_receipt(
                left_locator=locator, right_locator=primary["locator"],
                left_money_column_ordinals=note_lane["money_column_ordinals"],
                right_money_column_ordinals=primary["money_column_ordinals"],
                page_records=repaired_records, compiled_specs=compiled_specs,
                document_period_inventory=source_context["document_statement_period_inventory"],
            )
            period_material = {
                "source_locator": canonical_clone_v1(locator),
                "source_population_receipt_id": boundary["receipt_id"],
                "source_population_kind": boundary_kind,
                "note_lane_axis": canonical_clone_v1(note_lane),
                "primary_lane_axis": canonical_clone_v1(primary_lane),
                "primary_locator": canonical_clone_v1(primary["locator"]),
                "note_printed_duration_lengths": note_duration_lengths,
                "primary_printed_duration_lengths": primary_duration_lengths,
                "source_period_correspondence_receipt": period_proof,
                "rule": "EXACT_SOURCE_PERIOD_KEYS_AND_PRINTED_DURATION_LENGTHS_FOR_ALL_EXPENSE_POPULATIONS",
            }
            expense_population_period_receipts.append(period_material)
            if (not same_typed_json_v1(primary_lane.get("money_column_ordinals"), primary["money_column_ordinals"])
                    or not period_proof["complete"]):
                expense_population_period_conflicts.append(period_material)
            scope_receipt = _note_report_scope_receipt(
                note_section, note_table,
                source_paths=[item["hierarchy_path_exact"] for item in [
                    boundary["group_source_row"], *boundary["component_source_rows"], boundary["parent_source_row"],
                ] if item is not None], document_scope=document_scope,
            )
            note_scope = ([scope_receipt["report_scope"]] if scope_receipt["report_scope"] is not None
                          else scope_receipt["local_qualifiers"])
            material = {
                "source_population_receipt": canonical_clone_v1(boundary),
                "source_locator": canonical_clone_v1(locator),
                "note_report_scope_receipt": scope_receipt,
                "primary_surfaces_exact": primary_surfaces, "note_scope": note_scope,
                "primary_scope": primary_scope,
                "primary_ancestries_exact": canonical_clone_v1(primary_ancestries),
                "unknown_primary_ancestry_exact": canonical_clone_v1(unknown_primary_ancestry),
                "source_population_kind": boundary_kind,
                "rule": "PRINTED_EXPENSE_POPULATION_MUST_MATCH_PRIMARY_NOT_JUST_TOTAL_AMOUNT",
            }
            if used_primary_outline:
                material["printed_primary_outline_receipt"] = primary_outline
            expense_population_scope_receipts.append(material)
            if scope_receipt["conflict"] or note_scope != primary_scope or unknown_primary_ancestry:
                year_domain_conflicts.append(material)
    if year_domain_conflicts:
        return _unresolved_from_candidate(candidate, reason="CURRENT_YEAR_TAX_EXPENSE_SOURCE_POPULATION_AMBIGUITY",
                                          evidence={"year_domain_conflicts": year_domain_conflicts,
                                                    "source_context_receipt": canonical_clone_v1(source_context)})
    if expense_population_period_conflicts:
        return _unresolved_from_candidate(
            candidate, reason="CURRENT_TAX_EXPENSE_SOURCE_PERIOD_AMBIGUITY",
            evidence={"expense_population_period_conflicts": expense_population_period_conflicts,
                      "source_context_receipt": canonical_clone_v1(source_context)},
        )
    # Preserve the specific YEAR/PERIOD population failure above, while still
    # requiring every typed tax PRIMARY to pass before any READY seal.
    if any(not proof["complete"] for proof in primary_source_period_receipts):
        return _unresolved_from_candidate(
            candidate, reason="TYPED_PRIMARY_TAX_SOURCE_PERIOD_AMBIGUITY",
            evidence={"source_context_receipt": canonical_clone_v1(source_context),
                      "primary_source_period_receipts": primary_source_period_receipts},
        )
    if any(not proof["complete"] for proof in cross_source_mapping_period_receipts):
        return _unresolved_from_candidate(
            candidate, reason="INCOME_TAX_CROSS_SOURCE_PERIOD_AMBIGUITY",
            evidence={"source_context_receipt": canonical_clone_v1(source_context),
                      "cross_source_mapping_period_receipts": cross_source_mapping_period_receipts},
        )
    population_conflicts = _at_rate_cross_presentation_conflicts(
        candidate, compiled_specs=compiled_specs, source_context=source_context,
    )
    if population_conflicts:
        return _unresolved_from_candidate(
            candidate,
            reason="CURRENT_TAX_AT_RATE_CROSS_PRESENTATION_POPULATION_AMBIGUITY",
            evidence={
                "source_context_receipt": canonical_clone_v1(source_context),
                "at_rate_population_conflicts": population_conflicts,
            },
        )
    basis_conflicts = _tax_effect_basis_conflicts(candidate, source_context=source_context)
    if basis_conflicts:
        return _unresolved_from_candidate(
            candidate, reason="INCOME_TAX_RATE_RECONCILIATION_MEASUREMENT_BASIS_AMBIGUITY",
            evidence={"source_context_receipt": canonical_clone_v1(source_context),
                      "tax_effect_basis_conflicts": basis_conflicts},
        )
    closure, mismatch = _post_merge_root_closure(
        candidate, comparison_orientations=_authenticated_root_comparison_orientations(candidate),
    )
    root_mappings = [
        item for item in candidate["mappings"] if item.get("role") == "FAMILY_ROOT_TOTAL"
    ]
    root_mapping = root_mappings[0] if len(root_mappings) == 1 else None
    root_period_proofs = []
    if root_mapping is not None and source_context["supplemental_root_controls"]:
        pages = {item["page_json_version_id"]: item["page_json"] for item in repaired_records}
        for ref in root_mapping["source_refs"]:
            locator = ref["locator"]
            section, table = _source_table(
                pages[locator["page_json_version_id"]],
                section_id=locator["section_id"], table_id=locator["table_id"],
            )
            axis = _multitable_lane_axis(section, table, compiled_specs=compiled_specs)
            root_period_proofs.append({
                "source_ref": canonical_clone_v1(ref),
                "source_table_json_sha256": canonical_json_sha256_v1(table),
                "lane_axis": axis,
                "matches_exact_mapping_columns": same_typed_json_v1(
                    axis.get("money_column_ordinals"), ref.get("money_column_ordinals")
                ),
            })
    comparisons = []
    for control in source_context["supplemental_root_controls"]:
        power = {"MILLION_VND": 6, "VND": 0}[control["canonical_unit"]]
        orientation_receipt = _root_control_orientation_receipt(candidate, control, root_mapping)
        orientation = orientation_receipt["orientation"]
        period_correspondences = [_source_period_correspondence_receipt(
            left_locator=proof["source_ref"]["locator"], right_locator=control["locator"],
            left_money_column_ordinals=proof["source_ref"]["money_column_ordinals"],
            right_money_column_ordinals=control["money_column_ordinals"],
            page_records=repaired_records, compiled_specs=compiled_specs,
            document_period_inventory=source_context["document_statement_period_inventory"],
        ) for proof in root_period_proofs]
        same_period = bool(root_period_proofs) and all(
            proof["matches_exact_mapping_columns"] and proof["lane_axis"].get("complete")
            and period["complete"] for proof, period in zip(root_period_proofs, period_correspondences, strict=True)
        )
        lanes = []
        for lane, coefficient in enumerate(control["root_source_row"]["coefficients"]):
            source_value = None if coefficient is None else coefficient * (10**power)
            final_value = closure["lane_receipts"][lane]["operands_vnd"]["FAMILY_ROOT_TOTAL"]
            if root_mapping is None:
                status = "NO_FINAL_ROOT_MAPPING_CONTROL_RETAINED_NOT_EXPORTED"
            elif not same_period:
                status = "SOURCE_ROOT_CONTROL_PERIOD_CONFLICT"
            elif final_value is None:
                status = "UNOBSERVED_FINAL_ROOT_LANE_CONTROL_RETAINED_NOT_COMPARED"
            else:
                compatible = source_value is not None and source_value * orientation == final_value
                status = (
                    "EXACT_AUTHENTICATED_OPPOSITE_SIGN_PRESENTATION_CONTROL" if compatible and orientation == -1
                    else "EXACT_OBSERVED_SOURCE_LANE" if compatible
                    else "SOURCE_ROOT_CONTROL_CONFLICT"
                )
            lanes.append({
                "lane_ordinal": lane,
                "source_root_vnd": source_value,
                "final_root_vnd": final_value,
                "status": status,
            })
        comparisons.append({
            "control_id": control["control_id"],
            "root_mapping": canonical_clone_v1(root_mapping),
            "root_period_proofs": canonical_clone_v1(root_period_proofs),
            "source_period_correspondence_receipts": period_correspondences,
            "presentation_orientation_receipt": orientation_receipt,
            "lanes": lanes,
        })
    material = {
        "source_context_receipt": canonical_clone_v1(source_context),
        "primary_source_period_receipts": primary_source_period_receipts,
        "cross_source_mapping_period_receipts": cross_source_mapping_period_receipts,
        "expense_population_scope_receipts": expense_population_scope_receipts,
        "expense_population_period_receipts": expense_population_period_receipts,
        "post_merge_root_closure": closure,
        "supplemental_root_lane_receipts": comparisons,
        "rule": "ALL_SOURCE_ROOT_CONTROLS_REPLAYED_AGAINST_FINAL_SOURCE_MAPPING_NO_BACKSOLVE",
    }
    if type(primary) is dict and used_primary_outline:
        material["printed_primary_outline_receipt"] = primary_outline
    if mismatch or any(
        lane["status"] in {"SOURCE_ROOT_CONTROL_CONFLICT", "SOURCE_ROOT_CONTROL_PERIOD_CONFLICT"}
        for item in comparisons for lane in item["lanes"]
    ):
        return _unresolved_from_candidate(
            candidate,
            reason=("POST_MERGE_INCOME_TAX_ROOT_EQUATION_CONFLICT" if mismatch
                    else "CONFLICTING_SUPPLEMENTAL_INCOME_TAX_ROOT_CONTROL"),
            evidence=material,
        )
    output = canonical_clone_v1(candidate)
    output["closure_receipt"]["income_tax_source_control_receipt"] = {
        **material,
        "receipt_id": "gjitfav1:source-controls:" + canonical_json_sha256_v1(material),
    }
    candidate_material = {key: value for key, value in output.items() if key != "candidate_id"}
    output["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(candidate_material)
    return output


@_document_period_operation
def evaluate_gemini_json_income_tax_family_cluster_v1(
    *,
    regions: Any,
    page_json_by_version: Mapping[str, dict[str, Any]],
    selected_page_axis: Sequence[Mapping[str, Any]],
    compiled_specs: Mapping[str, Any],
    query_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    checked = _validate_query_receipt(query_receipt, regions=regions)
    source_axis = {
        (item.get("document_id"), item.get("document_ordinal"), item.get("source_sha256"))
        for item in regions
    }
    if len(source_axis) != 1:
        raise _error("income-tax region document axis is invalid")
    document_id, document_ordinal, source_sha256 = next(iter(source_axis))
    page_records = []
    seen_versions = set()
    for axis in selected_page_axis:
        if (
            type(axis) is not dict
            or axis.get("document_id") != document_id
            or axis.get("document_ordinal") != document_ordinal
            or axis.get("source_sha256") != source_sha256
        ):
            continue
        page_version_id = axis.get("page_json_version_id")
        page = page_json_by_version.get(page_version_id)
        if type(page_version_id) is not str or type(page) is not dict:
            raise _error("income-tax selected page image is absent")
        if page_version_id in seen_versions:
            raise _error("income-tax selected page axis is duplicate")
        seen_versions.add(page_version_id)
        page_records.append({**canonical_clone_v1(axis), "page_json": page})
    if not page_records or set(page_json_by_version) != seen_versions:
        raise _error("income-tax selected page axis does not bind supplied pages")
    repaired_records, repair_receipts, _ = _prepare_income_tax_evaluation_records_v1(
        page_records, compiled_specs=compiled_specs
    )
    root_issues: list[str] = []
    root_controls = _supplemental_root_controls(
        repaired_records, compiled_specs=compiled_specs, issues=root_issues
    )
    expected_context = _source_context_receipt(
        compiled_specs=compiled_specs,
        repair_receipts=repair_receipts,
        root_controls=root_controls,
        page_records=repaired_records,
        original_page_records=page_records,
    )
    if root_issues or not same_typed_json_v1(checked["source_context_receipt"], expected_context):
        raise _error("income-tax source context query replay drifted")
    repaired_pages = {item["page_json_version_id"]: item["page_json"] for item in repaired_records}
    adapter = checked["adapter_receipt"]
    original_bundle = _build_original_note_adapter_bundle(
        repaired_records, compiled_specs=compiled_specs, source_context=expected_context, repair_receipts=repair_receipts,
    )
    if original_bundle is not None:
        if (type(adapter) is not dict or adapter.get("adapter_format_version") != ORIGINAL_NOTE_ADAPTER_FORMAT_VERSION
                or not same_typed_json_v1(adapter, original_bundle["adapter"])
                or not same_typed_json_v1(checked["shared_query_receipt"], original_bundle["adapter"]["original_shared_query_receipt"])):
            raise _error("income-tax original-note adapter source query replay drifted")
        return _evaluate_original_note_adapter(original_bundle, compiled_specs=compiled_specs, repair_receipts=repair_receipts,
                                               source_context=expected_context, page_records=repaired_records)
    if type(adapter) is dict and adapter.get("adapter_format_version") == ORIGINAL_NOTE_ADAPTER_FORMAT_VERSION:
        raise _error("income-tax original-note adapter has no original source populations")
    if adapter is None:
        selected_primary, primary_reasons = _select_primary_presentation(
            repaired_records, compiled_specs=compiled_specs
        )
        if selected_primary is not None or any(
            reason.startswith("CONFLICTING_PRIMARY_")
            or reason.startswith("MULTIPLE_EQUIVALENT_PRIMARY_")
            or reason.startswith("INVALID_PRIMARY_")
            or reason.startswith("DUPLICATE_PRIMARY_")
            or reason.startswith("MISMATCHED_PRIMARY_")
            for reason in primary_reasons
        ):
            raise _error("income-tax adapter receipt is absent for usable primary source")
        candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
            regions=checked["shared_query_receipt"]["region_axis"],
            page_json_by_version=repaired_pages,
            compiled_specs=compiled_specs,
            query_receipt=checked["shared_query_receipt"],
        )
        supplemental_issues: list[str] = []
        supplemental_descriptors = _supplemental_presentations(
            repaired_records,
            compiled_specs=compiled_specs,
            issues=supplemental_issues,
            consumed_source_rows=_candidate_source_row_axis(candidate),
        )
        if supplemental_issues or supplemental_descriptors:
            raise _error("income-tax adapter receipt is absent for supplemental source")
        return _seal_income_tax_source_controls(
            _reseal_candidate(
                candidate,
                descriptor=None,
                repair_receipts=repair_receipts,
                strategy="DIRECT_NOTE_SOURCE_PRESENTATION",
                compiled_specs=compiled_specs,
            ),
            source_context=expected_context,
            repaired_records=repaired_records, compiled_specs=compiled_specs,
        )
    if (
        type(adapter) is not dict
        or set(adapter)
        != {
            "adapter_spec_sha256",
            "adapter_format_version",
            "primary_projection_receipt",
            "receipt_id",
            "repair_receipt_ids",
            "rule",
            "strategy",
            "supplemental_projection_receipts",
        }
        or adapter.get("adapter_spec_sha256")
        != compiled_specs["income_tax_adapter_spec_sha256"]
        or adapter.get("adapter_format_version") != ADAPTER_FORMAT_VERSION
        or adapter.get("rule") != _QUERY_ADAPTER_RULE
        or adapter.get("strategy") not in _QUERY_ADAPTER_STRATEGIES
        or type(adapter.get("primary_projection_receipt")) is not dict
        or type(adapter.get("supplemental_projection_receipts")) is not list
        or adapter.get("repair_receipt_ids")
        != [item["receipt_id"] for item in repair_receipts]
    ):
        raise _error("income-tax adapter query receipt schema drifted")
    material = {
        key: canonical_clone_v1(item) for key, item in adapter.items() if key != "receipt_id"
    }
    if adapter.get("receipt_id") != "gjitfav1:query:" + canonical_json_sha256_v1(material):
        raise _error("income-tax adapter query receipt drifted")
    selected, reasons = _select_primary_presentation(
        repaired_records, compiled_specs=compiled_specs
    )
    descriptor = adapter["primary_projection_receipt"]
    if selected is None or reasons or not same_typed_json_v1(selected["descriptor"], descriptor):
        raise _error("income-tax primary projection query replay drifted")
    primary_candidate = _evaluate_selected_primary(
        selected,
        repaired_pages=repaired_pages,
        repair_receipts=repair_receipts,
        compiled_specs=compiled_specs,
    )
    strategy = adapter.get("strategy")
    if strategy == "DIRECT_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION":
        if not same_typed_json_v1(
            selected["cluster"]["component_regions"],
            checked["shared_query_receipt"]["region_axis"],
        ):
            raise _error("income-tax primary query region replay drifted")
        supplemental_issues: list[str] = []
        supplemental_descriptors = _supplemental_presentations(
            repaired_records,
            compiled_specs=compiled_specs,
            issues=supplemental_issues,
        )
        if supplemental_issues:
            raise _error("income-tax supplemental projection issue axis drifted")
        if not same_typed_json_v1(
            supplemental_descriptors,
            adapter.get("supplemental_projection_receipts"),
        ):
            raise _error("income-tax supplemental projection query replay drifted")
        if supplemental_descriptors:
            supplemental_candidates = [
                (
                    item,
                    _evaluate_supplemental_descriptor(
                        item,
                        repaired_pages=repaired_pages,
                        compiled_specs=compiled_specs,
                    ),
                )
                for item in supplemental_descriptors
            ]
            return _seal_income_tax_source_controls(
                _merge_supplemental_and_primary_candidates(
                    supplemental_candidates,
                    primary_candidate,
                    descriptor=descriptor,
                    repair_receipts=repair_receipts,
                    compiled_specs=compiled_specs,
                ),
                source_context=expected_context,
                repaired_records=repaired_records, compiled_specs=compiled_specs,
            )
        return _seal_income_tax_source_controls(
            primary_candidate, source_context=expected_context,
            repaired_records=repaired_records, compiled_specs=compiled_specs,
        )
    note_strategies = {
        "DIRECT_NOTE_PLUS_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION",
        (
            "DIRECT_NOTE_PLUS_SUPPLEMENTAL_NOTE_PLUS_PRIMARY_INCOME_STATEMENT_"
            "SOURCE_PRESENTATION"
        ),
    }
    if strategy not in note_strategies:
        raise _error("income-tax adapter evaluation strategy drifted")
    note_candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=checked["shared_query_receipt"]["region_axis"],
        page_json_by_version=repaired_pages,
        compiled_specs=compiled_specs,
        query_receipt=checked["shared_query_receipt"],
    )
    supplemental_issues = []
    supplemental_descriptors = _supplemental_presentations(
        repaired_records,
        compiled_specs=compiled_specs,
        issues=supplemental_issues,
        consumed_source_rows=_candidate_source_row_axis(note_candidate),
    )
    if supplemental_issues:
        raise _error("income-tax supplemental projection issue axis drifted")
    if not same_typed_json_v1(
        supplemental_descriptors, adapter.get("supplemental_projection_receipts")
    ):
        raise _error("income-tax supplemental projection query replay drifted")
    if strategy == "DIRECT_NOTE_PLUS_PRIMARY_INCOME_STATEMENT_SOURCE_PRESENTATION":
        if supplemental_descriptors:
            raise _error("income-tax direct-note strategy omits supplemental projections")
        merged_primary = primary_candidate
    else:
        if not supplemental_descriptors:
            raise _error("income-tax triple-source strategy lacks supplemental projection")
        supplemental_candidates = [
            (
                item,
                _evaluate_supplemental_descriptor(
                    item,
                    repaired_pages=repaired_pages,
                    compiled_specs=compiled_specs,
                ),
            )
            for item in supplemental_descriptors
        ]
        merged_primary = _merge_supplemental_and_primary_candidates(
            supplemental_candidates,
            primary_candidate,
            descriptor=descriptor,
            repair_receipts=repair_receipts,
            compiled_specs=compiled_specs,
        )
        if merged_primary.get("status") != READY:
            return _unresolved_from_candidate(
                note_candidate,
                reason="UNRESOLVED_SUPPLEMENTAL_AND_PRIMARY_INCOME_TAX_PRESENTATIONS",
                evidence={
                    "rule": "RETAIN_QUERIED_NOTE_REGION_AND_AUTHENTICATED_REJECTED_PRIMARY_CANDIDATE",
                    "rejected_primary_candidate": canonical_clone_v1(merged_primary),
                    "source_context_receipt": canonical_clone_v1(expected_context),
                },
            )
    note_candidate = _recognition_rate_source_only_projection(note_candidate, source_context=expected_context)
    if note_candidate.get("status") != READY:
        return note_candidate
    return _seal_income_tax_source_controls(
        _merge_note_and_primary_candidates(
            note_candidate,
            merged_primary,
            descriptor=descriptor,
            repair_receipts=repair_receipts,
            compiled_specs=compiled_specs,
            strategy=strategy,
            page_records=repaired_records,
        ),
        source_context=expected_context,
        repaired_records=repaired_records, compiled_specs=compiled_specs,
    )


def build_gemini_json_income_tax_trials_v1(
    *,
    indexed_query_evidence: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    evidence = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        indexed_query_evidence, compiled_specs=compiled_specs
    )
    page_axis_by_document: dict[int, list[dict[str, Any]]] = {}
    for item in evidence["selected_page_axis"]:
        page_axis_by_document.setdefault(item["document_ordinal"], []).append(item)
    trials = []
    for disposition in evidence["candidate_dispositions"]:
        cluster = disposition["cluster"]
        ordinal = disposition["document_ordinal"]
        original_records = [{**canonical_clone_v1(axis), "page_json": page_json_by_document[ordinal][axis["page_json_version_id"]]}
                            for axis in page_axis_by_document[ordinal]]
        _, _, projection = _prepare_income_tax_evaluation_records_v1(original_records, compiled_specs=compiled_specs)
        if not same_typed_json_v1(cluster.get("income_tax_section_caption_projection_receipt"), projection):
            raise _error("income-tax indexed caption axis original-source replay drifted")
        candidates = []
        mappings = []
        reasons = []
        selected_candidate_id = None
        status = disposition["disposition"]
        if status == READY:
            regions = cluster["component_regions"]
            candidate = evaluate_gemini_json_income_tax_family_cluster_v1(
                regions=regions,
                page_json_by_version=page_json_by_document[ordinal],
                selected_page_axis=page_axis_by_document[ordinal],
                compiled_specs=compiled_specs,
                query_receipt=build_gemini_json_income_tax_region_query_receipt_v1(
                    regions, cluster=cluster
                ),
            )
            candidates = [candidate]
            status = candidate["status"]
            if status == READY:
                mappings = candidate["mappings"]
                selected_candidate_id = candidate["candidate_id"]
            else:
                reasons = candidate["reasons"]
        elif status == UNRESOLVED:
            reasons = cluster["reasons"]
        elif status != NOT_OBSERVED:
            raise _error("income-tax query disposition is invalid")
        trials.append(
            {
                "candidate_count": len(candidates),
                "candidates": candidates,
                "document_ordinal": ordinal,
                "mappings": mappings,
                "reasons": reasons,
                "selected_candidate_id": selected_candidate_id,
                "source_logical_name": disposition["source_logical_name"],
                "source_sha256": disposition["source_sha256"],
                "status": status,
            }
        )
    return validate_gemini_json_multitable_hierarchical_sweep_query_bindings_v1(
        trials=trials,
        indexed_query_evidence=evidence,
        compiled_specs=compiled_specs,
    )


def validate_gemini_json_income_tax_replay_v1(
    *,
    base_indexed_query_evidence: Any,
    indexed_query_evidence: Any,
    trials: Any,
    page_json_by_document: Mapping[int, Mapping[str, dict[str, Any]]],
    compiled_specs: Mapping[str, Any],
) -> list[dict[str, Any]]:
    expected_indexed = adapt_gemini_json_income_tax_indexed_query_evidence_v1(
        indexed_query_evidence=base_indexed_query_evidence,
        page_json_by_document=page_json_by_document,
        compiled_specs=compiled_specs,
    )
    if not same_typed_json_v1(expected_indexed, indexed_query_evidence):
        raise _error("income-tax indexed query replay drifted")
    expected_trials = build_gemini_json_income_tax_trials_v1(
        indexed_query_evidence=expected_indexed,
        page_json_by_document=page_json_by_document,
        compiled_specs=compiled_specs,
    )
    if type(trials) is not list or not same_typed_json_v1(expected_trials, trials):
        raise _error("income-tax trial replay drifted")
    return expected_trials
