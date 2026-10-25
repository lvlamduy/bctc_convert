"""UNRUN companion: copy only with the reviewed front-door proposal, no financial mocks."""
from __future__ import annotations

import pytest
from test_f36_notes_core_adapter_v1 import example as example
from test_f36_notes_core_adapter_v1 import ref, sweep_of

from bctc_ai.evaluation.gemini_json_f36_notes_core_adapter_v1 import (
    replay_f36_notes_core_trials_from_source_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    build_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.storage.gemini_accounting_family_store_v1 import (
    ingest_gemini_accounting_family_sweep_v1,
)


def test_generic_builder_cannot_mint_new_engine_evidence_without_the_owned_builder(example):
    compiled, trial, index_id = example
    with pytest.raises(ValueError, match="family-owned frontier builder"):
        build_gemini_json_flat_family_sweep_v1(corpus_manifest_index_id=index_id,
            topology_spec=compiled["topology"], evaluation_spec=compiled["evaluation"],
            schema_binding_spec=compiled["schema"], trials=[trial])


@pytest.mark.parametrize("adapter,adapter_ref,why", [
    (None, None, "requires its checked source replay"),
    (replay_f36_notes_core_trials_from_source_v1, None, "supplied together"),
    (None, ref("adapter.py"), "supplied together"),
])
def test_missing_or_one_sided_replay_cannot_reach_sqlite(example, tmp_path, adapter, adapter_ref, why):
    compiled, trial, index_id = example
    destination = tmp_path / "must-not-exist.sqlite3"
    with pytest.raises(RuntimeError, match=why):
        ingest_gemini_accounting_family_sweep_v1(destination, sweep=sweep_of(compiled, trial, index_id),
            corpus_index_ref=compiled["topology"]["source"]["index_ref"],
            implementation_refs=[ref("adapter.py")], run_kind="EXPERIMENTAL",
            source_replay_adapter=adapter, source_replay_adapter_ref=adapter_ref)
    assert not destination.exists()


def test_new_engine_can_never_change_official_current_selection(example, tmp_path):
    compiled, trial, index_id = example
    destination = tmp_path / "no-official-selection.sqlite3"
    with pytest.raises(RuntimeError, match="cannot alter the OFFICIAL"):
        ingest_gemini_accounting_family_sweep_v1(destination, sweep=sweep_of(compiled, trial, index_id),
            corpus_index_ref=compiled["topology"]["source"]["index_ref"],
            implementation_refs=[ref("adapter.py")], run_kind="OFFICIAL")
    assert not destination.exists()
