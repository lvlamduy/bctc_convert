"""DRAFT integration protocol tests; no actual-PDF/family acceptance claim.

Synthetic authority loaders below replace ONLY pinned registry fixtures. Real
SQLite/manifest/selection source contexts remain owned in runner tests. No source
capability, classifier, period gate or evaluator admission is monkeypatched.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest
from test_gemini_json_income_tax_family_v1 import _adapter_compiled
from test_gemini_json_income_tax_registered_part_period_integration_v1 import (
    _fixture_records,
    _period,
    _public,
    _registry,
)
from test_run_gemini_json_income_tax_accounting_family_v1 import (
    _authenticated_raw_cold_adapter,
    _invoke_authenticated_raw_cold,
    _raw_census_authority_fixture,
    runner,
)

from bctc_ai.evaluation import gemini_json_income_tax_family_v1 as family
from bctc_ai.evaluation.gemini_json_income_tax_part_period_context_v1 import (
    validate_registered_part_period_registry_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

ERROR = family.GeminiJsonIncomeTaxFamilyV1Error


def _variants(monkeypatch):
    original = _fixture_records()
    alternative = deepcopy(original)
    alternative[1]["page_json_version_id"] = "gfpstorev1:json:" + sha256(b"separately-selected-note-source").hexdigest()
    alternative[1]["page_json"]["sections"][0]["narratives_exact"].append("Thông tin bổ sung được trình bày nguyên văn.")
    for column in alternative[1]["page_json"]["sections"][0]["tables"][0]["columns"]:
        column["value_kind"] = "UNKNOWN"
    registries = [_registry(original), _registry(alternative)]
    registries[1]["contexts"][0]["context_id"] += ":alternate"
    paths = (family.DEFAULT_PART_PERIOD_CONTEXT_REGISTRY_PATH, family.DEFAULT_PART_PERIOD_COMMON204_REGISTRY_PATH)
    calls = [0, 0]

    def loader(position):
        def fresh():
            calls[position] += 1
            value = validate_registered_part_period_registry_v1(deepcopy(registries[position]))
            raw = canonical_json_bytes_v1(value)
            return value, {"path": paths[position], "sha256": sha256(raw).hexdigest(), "size_bytes": len(raw)}
        return fresh

    loaders = (loader(0), loader(1))
    monkeypatch.setattr(family, "_load_registered_part_period_registry_v1", loaders[0])
    monkeypatch.setattr(family, "_load_registered_part_period_common204_registry_v1", loaders[1])
    return original, alternative, registries, _adapter_compiled(), loaders, calls


@pytest.mark.parametrize("variant", [0, 1])
@pytest.mark.parametrize("reverse", [False, True])
def test_catalog_selects_one_whole_source_representation_order_invariant_and_immutable(monkeypatch, variant, reverse):
    first, other, registries, compiled, _, calls = _variants(monkeypatch)
    records = deepcopy((first, other)[variant])
    if reverse:
        records.reverse()
    before = canonical_json_bytes_v1([records, compiled])
    view = family._registered_part_period_source_view_v1(records, compiled_specs=compiled)
    assert view["registry_ref"] == compiled["income_tax_part_period_registry_catalog"][variant]["registry_ref"]
    assert view["source_variant_selection"]["declared_span_selection"]["selected_registry_position"] == variant
    assert {item["context_id"] for item in view["contexts"]} == {registries[variant]["contexts"][0]["context_id"]}
    assert view["source_variant_selection"]["original_identity_stage"]["private_clone_alone_authenticated_as_original"] is False
    assert family._registered_part_period_contexts_v1(records, compiled_specs=compiled) == view["contexts"]
    assert canonical_json_bytes_v1([records, compiled]) == before
    assert min(calls) >= 3


@pytest.mark.parametrize("variant", [0, 1])
def test_selected_actual_registry_ref_is_consistent_inventory_source_period_and_public_query(monkeypatch, variant):
    first, other, _, compiled, _, _ = _variants(monkeypatch)
    records = deepcopy((first, other)[variant])
    before = canonical_json_bytes_v1(records)
    inventory = family._document_statement_period_inventory(records, compiled_specs=compiled)
    expected = compiled["income_tax_part_period_registry_catalog"][variant]["registry_ref"]
    assert inventory["registered_part_period_registry_ref"] == expected
    assert inventory["registered_part_period_source_variant_selection"]["registry_ref"] == expected
    proof = _period(records, compiled, inventory=inventory)
    assert proof["complete"] is True
    assert any(item.get("registered_part_period_receipt", {}).get("registry_ref") == expected
               for item in proof["period_resolution_evidence"] if item.get("registered_part_period_receipt") is not None)
    _, _, candidate = _public(records, compiled)
    assert candidate["status"] == family.READY and candidate["mappings"]
    assert canonical_json_bytes_v1(records) == before
    assert records[1]["page_json"]["sections"][0]["tables"][0]["columns"][0]["value_kind"] == ("MONEY", "UNKNOWN")[variant]


@pytest.mark.parametrize("surface", ["catalog_object", "catalog_ref", "legacy_object", "legacy_ref", "catalog_order"])
def test_caller_self_reseal_cannot_replace_any_fresh_catalog_or_legacy_authority_axis(monkeypatch, surface):
    first, _, _, compiled, _, _ = _variants(monkeypatch)
    changed = deepcopy(compiled)
    if surface == "catalog_object":
        changed["income_tax_part_period_registry_catalog"][1]["registry"]["contexts"][0]["review_evidence"]["no_reset_observation_exact"] += " changed"
    elif surface == "catalog_ref":
        changed["income_tax_part_period_registry_catalog"][1]["registry_ref"]["sha256"] = "0" * 64
    elif surface == "legacy_object":
        changed["income_tax_part_period_registry"]["contexts"][0]["provenance_document_ordinal"] += 1
    elif surface == "legacy_ref":
        changed["income_tax_part_period_registry_ref"]["size_bytes"] += 1
    else:
        changed["income_tax_part_period_registry_catalog"].reverse()
    with pytest.raises(ERROR, match="compiled part-period authority drifted"):
        family._registered_part_period_source_view_v1(first, compiled_specs=changed)


@pytest.mark.parametrize("mutation", ["VID", "unique_VID", "body", "missing", "hybrid", "foreign_source", "selected", "duplicate"])
def test_no_partial_hybrid_alias_or_body_mutation_can_choose_a_fallback_registry(monkeypatch, mutation):
    first, other, _, compiled, _, _ = _variants(monkeypatch)
    changed = deepcopy(first)
    if mutation == "VID":
        changed[1]["page_json_version_id"] = "gfpstorev1:json:" + "d" * 64
    elif mutation == "unique_VID":
        # Isolate VID drift; existing VID/duplicate cases remain unchanged.
        unregistered = "gfpstorev1:json:" + sha256(b"isolated-unregistered-note-version-only").hexdigest()
        assert unregistered not in {record["page_json_version_id"] for record in [*first, *other]}
        changed[1]["page_json_version_id"] = unregistered
    elif mutation == "body":
        changed[1]["page_json"]["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "1000001"
    elif mutation == "missing":
        changed.pop(0)
    elif mutation == "hybrid":
        changed[1]["page_json_version_id"] = other[1]["page_json_version_id"]
    elif mutation == "foreign_source":
        changed[0]["source_sha256"] = "d" * 64
    elif mutation == "selected":
        changed[1]["selected_page_ordinal"] += 20
    else:
        changed.append(deepcopy(changed[1]))
    with pytest.raises(ERROR, match="source binding drifted"):
        family._registered_part_period_contexts_v1(changed, compiled_specs=compiled)


def test_unrelated_legacy_early_short_circuit_stays_before_deep_core_validation(monkeypatch):
    _, _, _, compiled, _, _ = _variants(monkeypatch)
    incomplete_legacy = [{"document_id": "legacy-unrelated", "source_logical_name": "elsewhere.pdf", "source_sha256": "0" * 64}]
    assert family._registered_part_period_contexts_v1(incomplete_legacy, compiled_specs=compiled) == []
    changed = deepcopy(incomplete_legacy)
    changed[0]["source_sha256"] = compiled["income_tax_part_period_registry_catalog"][0]["registry"]["contexts"][0]["pdf_source"]["sha256"]
    with pytest.raises(ERROR):
        family._registered_part_period_contexts_v1(changed, compiled_specs=compiled)


def test_inventory_self_reseal_cannot_switch_selected_registry_ref_or_span_proof(monkeypatch):
    first, _, _, compiled, _, _ = _variants(monkeypatch)
    inventory = family._document_statement_period_inventory(first, compiled_specs=compiled)
    inventory["registered_part_period_registry_ref"] = deepcopy(compiled["income_tax_part_period_registry_catalog"][1]["registry_ref"])
    inventory["registered_part_period_source_variant_selection"]["registry_ref"] = deepcopy(inventory["registered_part_period_registry_ref"])
    inventory["receipt_id"] = "gjitfav1:document-statement-periods:" + canonical_json_sha256_v1(
        {key: value for key, value in inventory.items() if key != "receipt_id"})
    with pytest.raises(ERROR, match="drifted"):
        _period(first, compiled, inventory=inventory)


def test_changed_evaluation_hash_domain_requires_new_explicit_original_replay_not_private_clone(monkeypatch):
    first, _, registries, _, _, _ = _variants(monkeypatch)
    registries[0]["contexts"][0]["span_pages"][0]["evaluation_page_json_sha256"] = "d" * 64
    compiled = _adapter_compiled()
    with pytest.raises(ERROR, match="explicit original-to-evaluation replay"):
        family._registered_part_period_contexts_v1(first, compiled_specs=compiled)


@pytest.mark.parametrize("mutation", ["omit", "resealed_intersection", "resealed_nonintersecting"])
def test_caller_cannot_omit_or_reseal_compiled_old13_repair_axis(monkeypatch, mutation):
    first, _, _, compiled, _, _ = _variants(monkeypatch)
    changed = deepcopy(compiled)
    repair = deepcopy(changed["income_tax_source_repairs"][0])
    repair["pdf_source"]["sha256"] = first[0]["source_sha256"] if mutation == "resealed_intersection" else "d" * 64
    repair["repair_id"] = "gjitfav1:repair:" + canonical_json_sha256_v1(
        {key: value for key, value in repair.items() if key != "repair_id"})
    changed["income_tax_source_repairs"].append(repair)
    changed["income_tax_source_repairs"].sort(key=lambda item: (
        item["pdf_source"]["sha256"], item["locator"]["physical_page"], item["locator"]["section_id"],
        item["locator"]["table_id"], item["locator"]["row_ordinal"], item.get("column_ordinal", 0),
    ))
    if mutation == "omit":
        changed["income_tax_source_repairs"] = []
    with pytest.raises(ERROR, match="compiled old13 repair axis differs"):
        family._registered_part_period_contexts_v1(first, compiled_specs=changed)


def test_approved_loader_resolution_is_exact_fixed_origin_not_caller_path_or_hash(monkeypatch):
    _, _, _, compiled, loaders, _ = _variants(monkeypatch)
    for position, expected in enumerate(loaders):
        reference = compiled["income_tax_part_period_registry_catalog"][position]["registry_ref"]
        assert family._approved_registered_part_period_loader_v1(reference) is expected
        forged = deepcopy(reference)
        forged["path"] += ".caller-resealed"
        with pytest.raises(ERROR, match="one unique approved authority"):
            family._approved_registered_part_period_loader_v1(forged)


@pytest.mark.parametrize("mutation", ["record", "loaded", "document"])
def test_actual_three_argument_callback_cannot_mutate_real_original_source_bundle(tmp_path, monkeypatch, mutation):
    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch)
    def poison(document, loaded, records):
        if mutation == "record":
            records[0]["document_ordinal"] += 1
        elif mutation == "loaded":
            loaded[0]["source_sha256"] = "0" * 64
        else:
            document["ids"].append("forged")
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="changed in a document callback"):
        with fixture.census_module.open_income_tax_original_census_source_v1(**fixture.options) as source:
            runner._evaluate_stream_v1(fixture.options["database"], fixture.documents, fixture.compiled,
                original_census_source=source, raw_census_sink=lambda _value: None,
                original_document_records_callback=poison)


def test_three_argument_callback_uses_same_original_load_and_actual_sparse_run_ordinal(tmp_path, monkeypatch):
    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch, documents=2)
    loads, callbacks = [], []
    actual = fixture.census_module.load_income_tax_source_page_json_versions_v1
    def counted(*args, **kwargs):
        loads.append(tuple(kwargs["page_json_version_ids"]))
        return actual(*args, **kwargs)
    monkeypatch.setattr(fixture.census_module, "load_income_tax_source_page_json_versions_v1", counted)
    with fixture.census_module.open_income_tax_original_census_source_v1(**fixture.options) as source:
        runner._evaluate_stream_v1(fixture.options["database"], fixture.documents[1:], fixture.compiled,
            original_census_source=source, raw_census_sink=lambda _value: None,
            original_document_records_callback=lambda document, loaded, records: callbacks.append(
                (document["ids"], [item["page_json_version_id"] for item in loaded],
                 [item["page_json_version_id"] for item in records], [item["document_ordinal"] for item in records])))
    assert loads == [tuple(fixture.documents[1]["ids"])]
    ids, loaded_ids, record_ids, ordinals = callbacks[0]
    assert ids == loaded_ids == record_ids and set(ordinals) == {1}


@pytest.mark.parametrize("mode", ["owner_absent", "both_callbacks"])
def test_three_argument_callback_requires_owner_and_is_mutually_exclusive(tmp_path, monkeypatch, mode):
    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch)
    if mode == "owner_absent":
        with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="requires an authenticated source"):
            runner._evaluate_stream_v1(fixture.options["database"], fixture.documents, fixture.compiled,
                original_document_records_callback=lambda *_args: None)
    else:
        with fixture.census_module.open_income_tax_original_census_source_v1(**fixture.options) as source:
            with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="mutually exclusive"):
                runner._evaluate_stream_v1(fixture.options["database"], fixture.documents, fixture.compiled,
                    original_census_source=source, raw_census_sink=lambda _value: None,
                    original_document_callback=lambda *_args: None, original_document_records_callback=lambda *_args: None)


def _protocol_document(records, registry):
    context = registry["contexts"][0]
    return {"manifest": {"document": {
        "document_id": context["document_id"], "source_logical_name": context["pdf_source"]["logical_name"],
        "source_sha256": context["pdf_source"]["sha256"], "source_size_bytes": context["pdf_source"]["size_bytes"],
    }}, "ids": [record["page_json_version_id"] for record in records]}


def test_selected_private_part_auth_view_and_fixed_loader_never_mutate_global_compiled(monkeypatch):
    first, other, registries, compiled, loaders, _ = _variants(monkeypatch)
    # Explicit mocked pixel protocol only. This does not claim a real PDF proof.
    seen = []
    def pixel_protocol(document, loaded, private_compiled, pdf_root, *, registry_loader):
        seen.append((registry_loader, deepcopy(private_compiled)))
        registry, reference = registry_loader()
        assert private_compiled["income_tax_part_period_registry"] == registry
        assert private_compiled["income_tax_part_period_registry_ref"] == reference
        return [{"context_id": registry["contexts"][0]["context_id"]}]
    monkeypatch.setattr(runner, "authenticate_registered_part_period_pdf_v1", pixel_protocol)
    before = canonical_json_bytes_v1(compiled)
    bundles, documents = [], []
    for records, registry in zip((first, other), registries, strict=True):
        document = _protocol_document(records, registry)
        documents.append(document)
        bundles.append(runner._authenticate_registered_part_catalog_pdf_v1(document, [], records, compiled, None))
    assert [item[0] for item in seen] == list(loaders)
    assert canonical_json_bytes_v1(compiled) == before
    assert bundles[1]["registry_ref"] == compiled["income_tax_part_period_registry_catalog"][1]["registry_ref"]
    # Same-source two variants are intentionally not a valid production doc
    # axis together; use each independently to inspect the per-registry barrier.
    calls = []
    def recheck(receipts, *, registry_loader):
        calls.append((registry_loader, deepcopy(receipts)))
        registry_loader()
    monkeypatch.setattr(runner, "recheck_registered_part_period_pdf_v1", recheck)
    for bundle, document in zip(bundles, documents, strict=True):
        runner._recheck_registered_part_catalog_pdf_v1([bundle], [document], compiled)
    assert [item[0] for item in calls] == [*loaders, *loaders]


@pytest.mark.parametrize("change", ["omit", "duplicate", "foreign_ref", "erase_applicable", "run_ordinal"])
def test_late_part_catalog_axis_rejects_forgery_before_pixel_protocol(monkeypatch, change):
    first, _, registries, compiled, _, _ = _variants(monkeypatch)
    document = _protocol_document(first, registries[0])
    def pixel_protocol(*_args, registry_loader, **_kwargs):
        registry, _ = registry_loader()
        return [{"context_id": registry["contexts"][0]["context_id"]}]
    monkeypatch.setattr(runner, "authenticate_registered_part_period_pdf_v1", pixel_protocol)
    bundle = runner._authenticate_registered_part_catalog_pdf_v1(document, [], first, compiled, None)
    if change == "omit":
        bundles = []
    else:
        if change == "duplicate":
            bundle["receipts"].append(deepcopy(bundle["receipts"][0]))
        elif change == "foreign_ref":
            bundle["registry_ref"]["path"] += ".forged"
        elif change == "erase_applicable":
            bundle.update(registry_ref=None, source_variant_selection=None, context_ids=[], receipts=[])
        else:
            bundle["runtime_document_ordinal"] = 66
        bundles = [bundle]
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Forged axis reached pixel recheck")
    monkeypatch.setattr(runner, "recheck_registered_part_period_pdf_v1", forbidden)
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error):
        runner._recheck_registered_part_catalog_pdf_v1(bundles, [document], compiled)


def test_late_part_recheck_rejects_callback_global_compiled_poison(monkeypatch):
    first, _, registries, compiled, _, _ = _variants(monkeypatch)
    document = _protocol_document(first, registries[0])
    monkeypatch.setattr(runner, "authenticate_registered_part_period_pdf_v1",
        lambda *_args, registry_loader, **_kwargs: [{"context_id": registry_loader()[0]["contexts"][0]["context_id"]}])
    bundle = runner._authenticate_registered_part_catalog_pdf_v1(document, [], first, compiled, None)
    def poison(_receipts, *, registry_loader):
        registry_loader()
        compiled["income_tax_adapter_spec"]["caller_marker"] = True
    monkeypatch.setattr(runner, "recheck_registered_part_period_pdf_v1", poison)
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="changed during late callback"):
        runner._recheck_registered_part_catalog_pdf_v1([bundle], [document], compiled)


def test_real_owned_cold_reselects_unrelated_empty_axis_and_does_not_borrow_warm_receipts(tmp_path, monkeypatch):
    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch)
    output = tmp_path / "warm"
    output.mkdir()
    refs, warm_bundles, auth_calls = [], [], []
    actual_auth = runner._authenticate_registered_part_catalog_pdf_v1
    def observe(*args, **kwargs):
        auth_calls.append(args[2][0]["document_ordinal"])
        return actual_auth(*args, **kwargs)
    monkeypatch.setattr(runner, "_authenticate_registered_part_catalog_pdf_v1", observe)
    with fixture.census_module.open_income_tax_original_census_source_v1(**fixture.options) as source:
        indexed, trials, _ = runner._evaluate_stream_v1(
            fixture.options["database"], fixture.documents, fixture.compiled,
            original_census_source=source,
            raw_census_sink=lambda census: refs.append(runner._write_raw_census_document_v1(output, census)),
            original_document_records_callback=lambda document, loaded, records: warm_bundles.append(
                runner._authenticate_registered_part_catalog_pdf_v1(document, loaded, records, fixture.compiled, None)),
        )
    runner._recheck_registered_part_catalog_pdf_v1(warm_bundles, fixture.documents, fixture.compiled)
    assert warm_bundles[0]["registry_ref"] is None and warm_bundles[0]["receipts"] == []
    cold = _invoke_authenticated_raw_cold(fixture, _authenticated_raw_cold_adapter(fixture, refs), indexed)
    assert same_typed_json_v1(cold, trials)
    assert auth_calls == [1, 1]


def test_production_catalog_has_two_actual_independent_file_pins_and_does_not_merge_contexts():
    catalog = family._load_registered_part_period_catalog_v1()
    assert [item["registry_ref"]["sha256"] for item in catalog] == [
        "c98624ac7822b44fa53c055ad094968a7fb11f3e96751a1c06e875b4999c140b",
        "7ba529e7878c1fd5d6af27abe4b5a7d2937bd395b40e3ea1160ee261448adaeb",
    ]
    assert [len(item["registry"]["contexts"]) for item in catalog] == [6, 1]
    root = Path(family.__file__).resolve().parents[3]
    for item in catalog:
        reference = item["registry_ref"]
        raw = (root / reference["path"]).read_bytes()
        assert len(raw) == reference["size_bytes"]
        assert sha256(raw).hexdigest() == reference["sha256"]


@pytest.mark.parametrize("failure", ["bytes", "missing"])
def test_alternative_loader_never_accepts_caller_resealed_or_missing_actual_registry(monkeypatch, failure):
    target = Path(family.__file__).resolve().parents[3] / family.DEFAULT_PART_PERIOD_COMMON204_REGISTRY_PATH
    actual = Path.read_bytes
    def changed(path):
        if path == target:
            if failure == "missing":
                raise FileNotFoundError("synthetic missing approved ALT")
            return actual(path) + b" "
        return actual(path)
    monkeypatch.setattr(Path, "read_bytes", changed)
    with pytest.raises(ERROR, match="alternative part-period authority"):
        family._load_registered_part_period_common204_registry_v1()


@pytest.mark.parametrize("drift", ["database", "implementation", "authority", "census"])
def test_last_cold_catalog_callback_cannot_escape_real_source_and_file_barriers(tmp_path, monkeypatch, drift):
    import sqlite3

    from test_run_gemini_json_income_tax_accounting_family_v1 import (
        _raw_census_generic_ingest,
        _raw_census_sweep,
        _written_authenticated_raw_census_stream,
    )

    from bctc_ai.storage.gemini_accounting_family_store_v1 import (
        GeminiAccountingFamilyStoreV1Error,
    )

    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch)
    (indexed, trials, _), references, _ = _written_authenticated_raw_census_stream(fixture, tmp_path / "warm")
    retained = {ref["census_ref"]["path"]: Path(ref["census_ref"]["path"]).read_bytes() for ref in references}
    dependency = tmp_path / "actual-external-pinned-dependency.py"
    dependency.write_bytes(b"# Synthetic immutable dependency, never imported.\n")
    root = fixture.options["artifact_root"]
    authority_paths = [root / fixture.options["corpus_index_ref"]["path"]]
    authority_paths.extend(root / document[name]["path"] for document in fixture.index["documents"]
                           for name in ("document_manifest_ref", "selection_ref"))
    adapter = runner._make_authenticated_source_replay_adapter_v1(
        database=fixture.options["database"], database_ref=fixture.options["database_ref"],
        artifact_root=root, corpus_index_ref=fixture.options["corpus_index_ref"], documents=fixture.documents,
        expected_census_refs=references, implementation_refs=[runner.generic._file_ref(dependency)],
        authority_refs=[runner.generic._file_ref(path) for path in authority_paths],
    )
    calls = []
    actual_recheck = runner.recheck_registered_part_period_pdf_v1

    def recheck_then_change_actual_bytes(receipts, *, registry_loader):
        # Call through the real fresh loader/lower recheck. This fixture is
        # genuinely nonapplicable, not a forged positive PDF-auth receipt.
        actual_recheck(receipts, registry_loader=registry_loader)
        assert receipts == []
        calls.append(True)
        if len(calls) != 4:  # Two fixed registry groups, inside then after owned exit.
            return
        if drift == "database":
            # Valid SQLite header edit; actual held-FD SHA/identity must catch it.
            with sqlite3.connect(fixture.options["database"]) as connection:
                connection.execute("PRAGMA user_version=7")
        else:
            target = {"implementation": dependency, "authority": authority_paths[-1],
                      "census": Path(references[0]["census_ref"]["path"])}[drift]
            target.write_bytes(target.read_bytes() + b" ")

    monkeypatch.setattr(runner, "recheck_registered_part_period_pdf_v1", recheck_then_change_actual_bytes)
    results = tmp_path / "must-not-persist.sqlite3"
    handoff = tmp_path / "must-not-handoff.json"
    with pytest.raises(GeminiAccountingFamilyStoreV1Error) as failed:
        _raw_census_generic_ingest(fixture, results, _raw_census_sweep(fixture, indexed, trials), adapter)
        handoff.write_bytes(b"must not reach accepted output")
    cause = failed.value.__cause__
    assert type(cause) is runner.RunGeminiJsonIncomeTaxV1Error
    expected = {
        "database": "Source SQLite bytes/identity changed",
        "implementation": "Cold replay implementation bytes changed during final PDF callbacks",
        "authority": "Cold replay immutable authority bytes changed during final PDF callbacks",
    }
    if drift in expected:
        assert str(cause) == expected[drift]
    else:
        # Re-read the retained file against its original byte pin; a caller
        # cannot extend/reseal the expected denominator through the callback.
        assert "census" in str(cause).lower()
    assert len(calls) == 4 and not results.exists() and not handoff.exists()
    if drift != "census":
        assert all(Path(path).read_bytes() == raw for path, raw in retained.items())


def test_cold_catalog_dependency_drift_is_checked_before_opening_source_or_callbacks(tmp_path, monkeypatch):
    from test_run_gemini_json_income_tax_accounting_family_v1 import (
        _written_authenticated_raw_census_stream,
    )

    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch)
    (indexed, _trials, _), references, _ = _written_authenticated_raw_census_stream(fixture, tmp_path / "warm")
    dependency = tmp_path / "actual-external-dependency.py"
    dependency.write_bytes(b"# Initial immutable bytes.\n")
    adapter = runner._make_authenticated_source_replay_adapter_v1(
        database=fixture.options["database"], database_ref=fixture.options["database_ref"],
        artifact_root=fixture.options["artifact_root"], corpus_index_ref=fixture.options["corpus_index_ref"],
        documents=fixture.documents, expected_census_refs=references,
        implementation_refs=[runner.generic._file_ref(dependency)],
    )
    dependency.write_bytes(dependency.read_bytes() + b"# Drift before cold entry.\n")
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Changed implementation reached source or authentication callbacks")
    monkeypatch.setattr(runner, "open_income_tax_original_census_source_v1", forbidden)
    monkeypatch.setattr(runner, "recheck_registered_part_period_pdf_v1", forbidden)
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match="implementation bytes changed before source open"):
        _invoke_authenticated_raw_cold(fixture, adapter, indexed)


@pytest.mark.parametrize("phase,last_lower_call", [("warm", 4), ("output", 6)])
@pytest.mark.parametrize("drift", ["database", "schema_copy", "pdf"])
def test_negative_only_pdf_dispatch_bounded_run_blocks_last_callback_disk_drift(
    tmp_path, monkeypatch, phase, last_lower_call, drift,
):
    """Negative dispatch isolation, NOT a real-PDF/positive E2E witness.

    This legacy fixture declares a synthetic b*64 PDF identity and 123 bytes.
    ONLY that exact initial synthetic PDF's hash/open dispatch is spied below.
    The real selected-source SQLite capability, immutable manifest/index,
    original loader, public evaluator, PART registry/recheck and DB FD barriers
    run unchanged. Every case MUST fail before diagnostic/results handoff.
    Actual COMMON204 clean-PDF warm/cold validation remains a separate gate.
    """
    import sqlite3
    from types import SimpleNamespace

    import fitz

    fixture = _raw_census_authority_fixture(tmp_path, monkeypatch)
    source = fixture.documents[0]["manifest"]["document"]
    assert source["source_sha256"] == "b" * 64 and source["source_size_bytes"] == 123
    assert len(fixture.documents[0]["ids"]) == 1
    pdf_root = tmp_path / "negative-only-synthetic-pdf-dispatch"
    pdf = pdf_root / source["source_logical_name"]
    pdf.parent.mkdir(parents=True)
    initial_pdf = b"%PDF NEGATIVE DISPATCH ONLY; NOT A PDF AUTHORITY".ljust(123, b" ")
    assert len(initial_pdf) == 123
    pdf.write_bytes(initial_pdf)
    actual_sha, actual_open = runner.generic._sha256, fitz.open
    dispatch = {"sha": 0, "open": 0}

    def negative_pdf_hash_only(path):
        if Path(path) == pdf and pdf.read_bytes() == initial_pdf:
            dispatch["sha"] += 1
            return "b" * 64
        return actual_sha(path)

    class NegativePdfLengthDispatchOnly:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def __len__(self):
            return 1

    def negative_pdf_open_only(path, *args, **kwargs):
        if Path(path) == pdf and pdf.read_bytes() == initial_pdf:
            dispatch["open"] += 1
            return NegativePdfLengthDispatchOnly()
        return actual_open(path, *args, **kwargs)

    monkeypatch.setattr(runner.generic, "_sha256", negative_pdf_hash_only)
    monkeypatch.setattr(fitz, "open", negative_pdf_open_only)
    # Real contents, real schema compiler, real bytes in implementation_refs;
    # only this TMP copy is changed. Never modify a repository/config source.
    schema_copy = tmp_path / "actual-schema-bytes-negative-dependency.json"
    schema_copy.write_bytes(runner.SPEC_PATHS["schema"].read_bytes())
    paths = dict(runner.SPEC_PATHS)
    paths["schema"] = schema_copy
    monkeypatch.setattr(runner, "SPEC_PATHS", paths)
    actual_load = fixture.census_module.load_income_tax_source_page_json_versions_v1
    loaded_axes = []

    def counted_actual_source_load(*args, **kwargs):
        loaded_axes.append(tuple(kwargs["page_json_version_ids"]))
        return actual_load(*args, **kwargs)

    monkeypatch.setattr(fixture.census_module, "load_income_tax_source_page_json_versions_v1", counted_actual_source_load)
    calls = []
    actual_recheck = runner.recheck_registered_part_period_pdf_v1

    def actual_lower_then_late_disk_drift(receipts, *, registry_loader):
        actual_recheck(receipts, registry_loader=registry_loader)
        # This original source is genuinely unrelated to BOTH PART registries.
        # No mock receipt, positive renderer result or approval is supplied.
        assert receipts == []
        calls.append(True)
        if len(calls) != last_lower_call:
            return
        if drift == "database":
            with sqlite3.connect(fixture.options["database"]) as connection:
                connection.execute("PRAGMA user_version=7")
        else:
            target = schema_copy if drift == "schema_copy" else pdf
            target.write_bytes(target.read_bytes() + b" ")

    monkeypatch.setattr(runner, "recheck_registered_part_period_pdf_v1", actual_lower_then_late_disk_drift)
    output = tmp_path / "must-not-hand-off-bounded-run"
    args = SimpleNamespace(
        repo_root=runner.ROOT,
        corpus_index=fixture.options["artifact_root"] / fixture.options["corpus_index_ref"]["path"],
        artifact_root=fixture.options["artifact_root"], source_page_database=fixture.options["database"],
        source_pdf_root=pdf_root, output_dir=output, results_database=output / "results.sqlite3",
        base_cluster_cache=None, source_page_scope=runner.PAGE_SCOPE_PATH,
        document_limit=None, document_ordinals=[1],
    )
    expected = {
        "database": "Source SQLite bytes/identity changed",
        "schema_copy": ("Implementation bytes changed during warm final PDF callbacks" if phase == "warm"
                        else "Implementation/immutable authority bytes changed during output PDF callbacks"),
        "pdf": ("Source PDF changed during warm final PDF callbacks" if phase == "warm"
                else "Source PDF changed during output PDF callbacks"),
    }
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error, match=expected[drift]):
        runner.run(args)
    assert len(calls) == last_lower_call
    assert loaded_axes == [tuple(fixture.documents[0]["ids"])]
    assert dispatch["sha"] > 0 and dispatch["open"] == 1
    assert not args.results_database.exists()
    assert not (output / "income-tax-bounded-diagnostic.json").exists()
    assert not (output / "income-tax-sweep.json").exists()
    assert not (output / "income-tax-audit.json").exists()
    # Keep actual provisional raw-census artifacts: failure is not cleanup.
    assert len(list((output / "raw-census").glob("*.json"))) == 1


def test_catalog_two_complete_distinct_approved_variants_are_ambiguous_not_priority(monkeypatch):
    # Synthetic loader protocol only: no real PDF or registry approval claim.
    first, _, registries, _, _, _ = _variants(monkeypatch)
    registries[1] = deepcopy(registries[0])
    registries[1]["contexts"][0]["context_id"] += ":second-complete-declared-variant"
    compiled = _adapter_compiled()
    assert (compiled["income_tax_part_period_registry_catalog"][0]["registry"]
            != compiled["income_tax_part_period_registry_catalog"][1]["registry"])
    assert (compiled["income_tax_part_period_registry_catalog"][0]["registry_ref"]["path"]
            != compiled["income_tax_part_period_registry_catalog"][1]["registry_ref"]["path"])
    before = canonical_json_bytes_v1([first, compiled])
    with pytest.raises(ERROR, match="source binding drifted"):
        family._registered_part_period_source_view_v1(first, compiled_specs=compiled)
    assert canonical_json_bytes_v1([first, compiled]) == before
