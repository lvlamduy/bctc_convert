"""Closed, source-pinned family replay profiles; no caller plugins/callbacks.

F40 admission retains its exact historical 15-file producer axis. Consumer
implementation provenance is additive, not a rewrite of historical run IDs.
"""

from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.export import gemini_tm_multitable_bridge_v1 as base

REQUEST_FORMAT = "GEMINI_TM_FAMILY_REPLAY_REQUEST_V2"
F40_PROFILE = "F40_CASH_EQUIVALENTS_FULL_RESIDUAL_REPLAY_V1"
F37_PROFILE = "F37_CREDIT_RISK_PROVISION_EXPENSE_REPLAY_V1"
_V2_FIELDS = {"request_format_version", "source_replay_profile", "source_replay_runner_ref"}
_RUNNER = "scripts/experiments/run_gemini_json_cash_equivalents_accounting_family_v1.py"
_GENERIC_RUNNER = "scripts/experiments/run_gemini_json_multitable_hierarchical_accounting_family_v1.py"
_ADAPTER = "src/bctc_ai/evaluation/gemini_json_cash_equivalents_family_v1.py"
_MODULE_NAME = "_bctc_tm_f40_replay_ef3f9842_v2"
# Reviewed declaration at migration base8efd, unchanged in consumer0bcf.
# These are approved expected pins, not an assertion that a real DB was read.
_F40_PINS = (
    ("config/families/tm-cash-equivalents-evaluation-v1.json", "21a39306833729b3de3717e0bb556db5cc5b440ed89756330ba944eb6ecae7bf", 4281),
    ("config/families/tm-cash-equivalents-pdf-residual-audit-full271-v1.json", "9503b73c37bcb3fdd19fc8bb1106b7bad234fd4773f2761dabde699911d2aba4", 79674),
    ("config/families/tm-cash-equivalents-schema-binding-v1.json", "885d99d559918e86f3f575bf2978685ded101b507db6a2f6b5bd3bdbb698b295", 622),
    ("config/families/tm-cash-equivalents-topology-v1.json", "732e25090cf1592dc98b8e1e9b8e56ccb63a51b67c49dd1b6c04b28116469c07", 13552),
    ("data/registered/gemini_json_cash_equivalents_source_repairs_v1.json", "4217a3941e5d6dfc14938665f3878c852da485d835d37a1a637ebe92b9b6dcc6", 13357),
    (_RUNNER, "ef3f9842d4196f9393ce92395b73900f4976ed45ee2e0d9d8fb1bcdc1d4b3780", 47249),
    (_GENERIC_RUNNER, "d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5", 149733),
    ("src/bctc_ai/evaluation/accounting_family_topology_v1.py", "7d7846e1a8b15379a1489fce01e1f59a88b9ec0aa7e5ea54e506280fa90758ae", 82226),
    (_ADAPTER, "49ebacebed93c60c600034a203893050c92104bfe75feba084a2791a4ec4514e", 66615),
    ("src/bctc_ai/evaluation/gemini_json_first_page_render_v1.py", "db593f207cd5675de65cc67e660fcd673c60b37293751689ab3816342a92c791", 12306),
    ("src/bctc_ai/evaluation/gemini_json_flat_accounting_family_v1.py", "8201799cdaeec765fa338ce473d5ec865ffd10aba02547539d05b1d55ff5d925", 251891),
    ("src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py", "bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2", 608721),
    ("src/bctc_ai/evaluation/source_observation_mapping_contract_v1.py", "aeafa87f5d53c890d6a3640ca561946cfa5e68f9132b79d5f1fe0c741a2ede8a", 9134),
    ("src/bctc_ai/storage/gemini_accounting_family_store_v1.py", "6c6638bde3a1eea25c5382321a0a256323ea737bd691014c6e04d2308c8e8a17", 64710),
    ("src/bctc_ai/storage/gemini_financial_page_store_v1.py", "dbcf3381f526b3abf7cf234148cd7be17b758cc5cb43268feece74a5ba53e27c", 367215),
)


def approved_f40_producer_refs_v2() -> list[dict[str, Any]]:
    return [{"path": path, "sha256": digest, "size_bytes": size} for path, digest, size in _F40_PINS]


def approved_f40_runner_ref_v2() -> dict[str, Any]:
    return next(ref for ref in approved_f40_producer_refs_v2() if ref["path"] == _RUNNER)


def _snapshot_v2(request: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    base.require(type(request) is dict, "V2 request must be a JSON object")
    request = base.strict_json_v1(base.json_bytes(request))
    base.require(set(request) == base._REQUEST_FIELDS | _V2_FIELDS, "V2 request fields drift")
    base.require(request["request_format_version"] == REQUEST_FORMAT, "V2 request format mismatch")
    if request["source_replay_profile"] == F37_PROFILE:
        raise ValueError("F37 profile UNSUPPORTED: reviewed7b metadata and combined fresh origin checkout required")
    base.require(request["source_replay_profile"] == F40_PROFILE, "unknown or unsupported closed V2 replay profile")
    base.require(request["expected_family_id"] == "CASH_EQUIVALENTS", "F40 profile/family mismatch")
    base.require(request["expected_run_kind"] == "EXPERIMENTAL", "approved F40 producer declares EXPERIMENTAL")
    base.require(base.json_bytes(request["source_replay_runner_ref"]) == base.json_bytes(approved_f40_runner_ref_v2()),
                 "F40 runner ref differs from approved fixed source")
    legacy = {key: request[key] for key in base._REQUEST_FIELDS}
    return request, legacy


def validate_f40_profile_axis_v2(
    *, request: dict[str, Any], profile: dict[str, Any],
    stored_refs: list[dict[str, Any]], stored_axis_bytes: bytes,
) -> None:
    base.require(profile["source_replay_profile"] == F40_PROFILE
                 and profile["expected_family_id"] == request["expected_family_id"] == "CASH_EQUIVALENTS",
                 "closed F40 profile binding drift")
    expected = base.json_bytes(approved_f40_producer_refs_v2())
    base.require(stored_axis_bytes == expected == base.json_bytes(stored_refs)
                 == base.json_bytes(request["producer_refs"]), "F40 exact stored15-file producer axis mismatch")
    base.require(base.json_bytes(profile["source_replay_runner_ref"]) == base.json_bytes(approved_f40_runner_ref_v2()),
                 "F40 callback runner ref mismatch")
    root = Path(request["producer_root"]).resolve()
    base.require(root == Path(__file__).resolve().parents[3]
                 == Path(base.__file__).resolve().parents[3], "F40 requires one combined producer/consumer source root")
    for reference in approved_f40_producer_refs_v2():
        base.authenticate_ref_v1({**reference, "path": str(root / reference["path"])})


def _check_origin(function: Any, path: Path) -> None:
    base.require(inspect.isfunction(function) and inspect.getsourcefile(function) is not None
                 and Path(inspect.getsourcefile(function)).resolve() == path.resolve(),
                 "F40 loaded callable origin differs from approved producer")


def _load_f40_runner_v2(root: Path) -> ModuleType:
    """Load exactly one preauthenticated fixed producer; never hot-switch roots."""
    base.require(root == Path(__file__).resolve().parents[3], "foreign F40 producer root")
    for ref in approved_f40_producer_refs_v2():
        base.authenticate_ref_v1({**ref, "path": str(root / ref["path"])})
    generic_name = "run_gemini_json_multitable_hierarchical_accounting_family_v1"
    existing = sys.modules.get(generic_name)
    if existing is not None:
        base.require(getattr(existing, "__file__", None) is not None
                     and Path(existing.__file__).resolve() == (root / _GENERIC_RUNNER).resolve(),
                     "foreign cached generic runner; fresh combined checkout required")
    module = sys.modules.get(_MODULE_NAME)
    if module is None:
        spec = importlib.util.spec_from_file_location(_MODULE_NAME, root / _RUNNER)
        base.require(spec is not None and spec.loader is not None, "fixed F40 runner loader absent")
        module = importlib.util.module_from_spec(spec)
        sys.modules[_MODULE_NAME] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(_MODULE_NAME, None)
            raise
    base.require(Path(module.__file__).resolve() == (root / _RUNNER).resolve()
                 and module.ROOT.resolve() == root and module.generic.ROOT.resolve() == root,
                 "cached F40 runner/root mismatch")
    for function in (module.replay_cash_equivalents_trials_from_source_v1,
                     module._authenticate_source_repairs_v1, module._build_trials_v1):
        _check_origin(function, root / _RUNNER)
    for function in (module.bind_gemini_json_cash_equivalents_source_repairs_v1,
                     module.adapt_gemini_json_cash_equivalents_indexed_query_evidence_v1,
                     module.evaluate_gemini_json_cash_equivalents_family_cluster_v1):
        _check_origin(function, root / _ADAPTER)
    _check_origin(module.generic._load_selected_pages_by_document, root / _GENERIC_RUNNER)
    _check_origin(module.query_selected_multitable_hierarchical_family_regions_v1,
                  root / "src/bctc_ai/storage/gemini_financial_page_store_v1.py")
    declared = module._implementation_refs(root / "config/families/tm-cash-equivalents-pdf-residual-audit-full271-v1.json")
    base.require(base.json_bytes(sorted(declared, key=lambda ref: ref["path"]))
                 == base.json_bytes(approved_f40_producer_refs_v2()), "loaded F40 declaration/axis mismatch")
    return module


def replay_f40_profile_v2(
    *, request: dict[str, Any], profile: dict[str, Any], sweep: dict[str, Any],
    compiled_specs: dict[str, Any], selected: list[str], source_page_database: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    root = Path(request["producer_root"]).resolve()
    runner = _load_f40_runner_v2(root)
    for kind, suffix in (("topology", "topology"), ("evaluation", "evaluation"), ("schema_binding", "schema-binding")):
        value = runner.generic._json(root / f"config/families/tm-cash-equivalents-{suffix}-v1.json")
        base.require(base.json_bytes(value) == base.json_bytes(sweep["specs"][kind]["value"]),
                     "F40 stored spec differs from approved source config")
    index = base.validate_current_corpus_manifest_index_v1(base.strict_json_v1(base.pinned_bytes_v1(request["corpus_index_ref"])))
    family_compiled = runner.bind_gemini_json_cash_equivalents_source_repairs_v1(
        compiled_specs, runner.generic._json(runner.SOURCE_REPAIR_PATH),
    )
    raw = runner.query_selected_multitable_hierarchical_family_regions_v1(
        source_page_database, selected_page_json_version_ids=selected, compiled_specs=family_compiled,
    )
    pages = runner.generic._load_selected_pages_by_document(
        source_page_database, selected_ids=selected, selected_page_axis=raw["selected_page_axis"],
    )
    source_shas = {document["source_sha256"] for document in index["documents"]}
    expected_repairs = [repair for repair in family_compiled["cash_equivalents_source_repairs"]
                        if repair["source"]["source_sha256"] in source_shas]
    extra_refs = []
    for repair in expected_repairs:
        source = repair["source"]
        path = Path(request["source_pdf_root"]) / source["source_logical_name"]
        base.require(path.resolve().is_relative_to(Path(request["source_pdf_root"]).resolve()),
                     "F40 registered repair PDF escapes source root")
        ref = base.authenticate_ref_v1({"path": str(path), "sha256": source["source_sha256"],
                                        "size_bytes": source["source_size_bytes"]})
        if ref not in extra_refs:
            extra_refs.append(ref)
    authenticated = runner._authenticate_source_repairs_v1(
        repairs=family_compiled["cash_equivalents_source_repairs"], index=index,
        selected_page_axis=raw["selected_page_axis"], page_json_by_document=pages,
        source_pdf_root=Path(request["source_pdf_root"]),
    )
    base.require(base.json_bytes(authenticated) == base.json_bytes(expected_repairs),
                 "F40 complete registered source-repair authentication axis mismatch")
    # The exact cold producer callback loads its own complete source pages.
    # Release the warm authentication view first; do not retain two full maps.
    del pages, raw, family_compiled
    replayed = runner.replay_cash_equivalents_trials_from_source_v1(
        source_page_database=source_page_database, selected_page_json_version_ids=tuple(selected),
        compiled_specs=compiled_specs, indexed_query_evidence=sweep["indexed_query_evidence"],
    )
    base.require(base.json_bytes(replayed) == base.json_bytes(sweep["trials"]),
                 "F40 full original trial axis differs from exact family replay")
    extra_refs.append(base.file_ref_v1(Path(__file__).resolve()))
    receipt = {
        "profile_id": F40_PROFILE, "runner_ref": profile["source_replay_runner_ref"],
        "producer_axis_sha256": base.sha256(base.json_bytes(approved_f40_producer_refs_v2())).hexdigest(),
        "full_trial_count": len(replayed), "selected_page_count": len(selected),
        "trial_axis_sha256": base.canonical_json_sha256_v1(replayed),
        "authenticated_repair_count": len(authenticated),
        "authenticated_repair_axis_sha256": base.canonical_json_sha256_v1(authenticated),
        "extra_input_refs": extra_refs,
        "status": "EXACT_F40_SOURCE_REPLAY_AND_REGISTERED_REPAIR_AUTHENTICATION_NOT_FINANCIAL_ACCEPTANCE",
        "pdf_residual_acceptance": "NOT_CLAIMED",
    }
    return replayed, receipt, extra_refs


def authenticate_family_store_run_v2(request: dict[str, Any]) -> dict[str, Any]:
    request, legacy = _snapshot_v2(request)
    bundle = base._authenticate_multitable_store_run_v1(legacy, replay_profile=request)
    bundle["request"] = request
    return bundle


def export_tm_family_store_document_v2(*, request: dict[str, Any]) -> dict[str, Any]:
    request, _legacy = _snapshot_v2(request)
    bundle = authenticate_family_store_run_v2(request)
    return base._export_authenticated_multitable_document_v1(request=request, bundle=bundle)
