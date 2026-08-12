from __future__ import annotations

import ast
import os
import stat
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from test_source_structure_adjacent_page_table_geometry_relations_v1 import (
    _narrative_rows,
    _ocr_page_graph,
    _ocr_terminal_page_graph,
)

from bctc_ai.source_structure import (
    adjacent_page_table_geometry_candidate_gate_v1 as gate_v1,
)
from bctc_ai.source_structure import (
    wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1 as inventory_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    decode_canonical_json_bytes_v1,
)
from bctc_ai.source_structure.finalized_v3_survey_stream_v1 import (
    FinalizedV3SurveyAuthority,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    PROJECT_ROOT / "src/bctc_ai/source_structure/"
    "wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1.py"
)
DOCUMENT_ID = "sha256:" + "a" * 64


def _rows(y_values: tuple[int, ...], *, axis_count: int) -> list[tuple[int, list[tuple[int, int]]]]:
    boxes = [(100 + 250 * index, 180 + 250 * index) for index in range(axis_count)]
    return [(y, boxes) for y in y_values]


def _synthetic_page_triples() -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]:
    return [
        _ocr_page_graph(1, _rows((1_240, 1_320, 1_400, 1_480), axis_count=3)),
        _ocr_page_graph(2, _rows((20, 100, 180, 260), axis_count=2)),
        _ocr_page_graph(3, _narrative_rows()),
        _ocr_terminal_page_graph(4),
    ]


def _context(
    triple: tuple[dict[str, Any], dict[str, Any], dict[str, Any]], ordinal: int
) -> dict[str, Any]:
    projection, proposal, graph = triple
    record = projection["page_record_v2"]
    return {
        "record": {
            "request_ordinal": record["request_ordinal"],
            "document_id": record["document_id"],
            "physical_page": record["physical_page"],
        },
        "projection": projection,
        "proposal": proposal,
        "graph": graph,
        "source_page": {"page_inventory_identity_sha256": f"{ordinal:x}" * 64},
        "prestructural_page": {"page_inventory_identity_sha256": f"{ordinal + 8:x}" * 64},
        "graph_sha256": canonical_json_sha256_v1(graph),
    }


def _authority() -> FinalizedV3SurveyAuthority:
    return FinalizedV3SurveyAuthority(
        aggregate_artifact_sha256="1" * 64,
        aggregate_size_bytes=101,
        aggregate_identity_sha256="2" * 64,
        control_artifact_sha256="3" * 64,
        control_size_bytes=202,
        control_identity_sha256="4" * 64,
        sealed_plan_sha256="5" * 64,
        document_ids=(DOCUMENT_ID,),
        document_count=1,
        request_count=4,
        referenced_object_count=12,
    )


def _producer() -> dict[str, Any]:
    records = []
    for path in sorted(set(inventory_v1._IMPLEMENTATION_PATHS)):
        if path == inventory_v1._RELATION_MODULE_PATH:
            digest = inventory_v1._RELATION_MODULE_SHA256
            size = inventory_v1._RELATION_MODULE_SIZE_BYTES
        elif path == inventory_v1._GATE_MODULE_PATH:
            digest = inventory_v1._GATE_MODULE_SHA256
            size = inventory_v1._GATE_MODULE_SIZE_BYTES
        else:
            digest = "f" * 64
            size = 1
        records.append(
            {
                "phase": "READ",
                "kind": "IMPLEMENTATION",
                "path": path.as_posix(),
                "sha256": digest,
                "size_bytes": size,
            }
        )
    return {
        "git": {"commit": "e" * 40, "dirty": False},
        "implementation_ledger": {
            "records": records,
            "sha256": canonical_json_sha256_v1(records),
        },
    }


class _FakeStream:
    def __init__(self, authority: FinalizedV3SurveyAuthority) -> None:
        self.authority = authority

    def __iter__(self):
        return iter(SimpleNamespace(page_record={}, page_result={}) for _ in range(4))


def _synthetic_denominators(contexts: list[dict[str, Any]]) -> dict[str, int]:
    pairs = [
        inventory_v1._optimized_pair(left, right, pair_ordinal=index)[0]
        for index, (left, right) in enumerate(zip(contexts, contexts[1:], strict=False), 1)
    ]
    counts = inventory_v1._rollup_pair_counts(pairs)
    pages = inventory_v1._document_pages_from_pairs(DOCUMENT_ID, pairs)
    return {
        "document_count": 1,
        "page_count": 4,
        "page_pair_count": 3,
        "excluded_cross_document_boundary_count": 0,
        "terminal_page_count": sum(page["terminal"] for page in pages),
        **{
            field: counts[field]
            for field in (
                "relation_occurrence_count",
                "axis_distance_occurrence_count",
                "fragment_occurrence_count",
                "physical_axis_occurrence_count",
                "distinct_fragment_count",
                "distinct_physical_axis_count",
                "distinct_relation_count",
                "distinct_axis_distance_count",
            )
        },
    }


def _patch_synthetic_build(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    triples = _synthetic_page_triples()
    contexts = [_context(triple, index) for index, triple in enumerate(triples, 1)]
    authority = _authority()
    authority_payload = inventory_v1._authority_payload(authority)
    node_counts = {
        key: sum(context["graph"]["metrics"]["node_counts"][key] for context in contexts)
        for key in inventory_v1._FROZEN_PRESTRUCTURAL_NODE_COUNTS
    }
    source = {
        "authority": authority_payload,
        "pages": [{"synthetic": index} for index in range(1, 5)],
    }
    prestructural = {
        "authority": {
            "finalized_v3": authority_payload,
            "source_inventory": inventory_v1._source_authority(),
        },
        "pages": [{"synthetic": index} for index in range(1, 5)],
        "corpus_metrics": {"node_counts": node_counts},
    }
    producer = _producer()
    calls = {
        "page": 0,
        "optimized_pair": 0,
        "public_builder": 0,
        "public_validator": 0,
        "raw_receipt": 0,
    }

    @contextmanager
    def open_stream(_root: Path):
        yield _FakeStream(authority)

    def page_context(**kwargs: Any) -> dict[str, Any]:
        delivered = kwargs["delivered"]
        calls["page"] += 1
        return contexts[delivered - 1]

    original_optimized = inventory_v1._optimized_pair

    def optimized(*args: Any, **kwargs: Any):
        calls["optimized_pair"] += 1
        return original_optimized(*args, **kwargs)

    original_builder = gate_v1.build_adjacent_page_table_geometry_candidate_gate_v1
    original_validator = gate_v1.validate_adjacent_page_table_geometry_candidate_gate_v1

    def public_builder(*args: Any, **kwargs: Any):
        calls["public_builder"] += 1
        return original_builder(*args, **kwargs)

    def public_validator(*args: Any, **kwargs: Any):
        calls["public_validator"] += 1
        return original_validator(*args, **kwargs)

    def raw_receipts(_root: Path) -> dict[str, tuple[int, str]]:
        calls["raw_receipt"] += 1
        return {"source": (1, "1" * 64), "prestructural": (2, "2" * 64)}

    monkeypatch.setattr(inventory_v1, "FINALIZED_V3_SURVEY_AUTHORITY_V1", authority)
    monkeypatch.setattr(inventory_v1, "_FROZEN_PRESTRUCTURAL_NODE_COUNTS", node_counts)
    monkeypatch.setattr(
        inventory_v1, "_FROZEN_CORPUS_DENOMINATORS", _synthetic_denominators(contexts)
    )
    monkeypatch.setattr(inventory_v1, "open_finalized_v3_survey_stream_v1", open_stream)
    monkeypatch.setattr(inventory_v1, "_page_context", page_context)
    monkeypatch.setattr(inventory_v1, "_optimized_pair", optimized)
    monkeypatch.setattr(inventory_v1, "_load_source_inventory", lambda _root: deepcopy(source))
    monkeypatch.setattr(
        inventory_v1,
        "_load_prestructural_inventory",
        lambda _root, *, source_inventory: deepcopy(prestructural),
    )
    monkeypatch.setattr(inventory_v1, "_producer_receipt", lambda _root: deepcopy(producer))
    monkeypatch.setattr(inventory_v1, "_validate_build_authorities", lambda **_kwargs: None)
    monkeypatch.setattr(inventory_v1, "_input_raw_receipts", raw_receipts)
    monkeypatch.setattr(
        gate_v1, "build_adjacent_page_table_geometry_candidate_gate_v1", public_builder
    )
    monkeypatch.setattr(
        gate_v1, "validate_adjacent_page_table_geometry_candidate_gate_v1", public_validator
    )
    return contexts, calls


def _build_synthetic(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, int]]:
    contexts, calls = _patch_synthetic_build(monkeypatch)
    inventory = inventory_v1.build_wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1(
        tmp_path
    )
    return inventory, contexts, calls


def _refresh_gate_receipt(receipt: dict[str, Any]) -> None:
    full = inventory_v1._reconstruct_full_gate(inventory_v1._EXPECTED_GATE_COMMON, receipt)
    full["artifact_identity"] = inventory_v1._content_identity(
        "apgcv1:artifact:", full, "artifact_identity"
    )
    receipt["gate_artifact_identity"] = full["artifact_identity"]
    full = inventory_v1._reconstruct_full_gate(inventory_v1._EXPECTED_GATE_COMMON, receipt)
    receipt["gate_canonical_sha256"] = canonical_json_sha256_v1(full)


def _refresh_inventory(value: dict[str, Any]) -> None:
    value["inventory_identity_sha256"] = canonical_json_sha256_v1(
        {key: item for key, item in value.items() if key != "inventory_identity_sha256"}
    )


def test_public_builder_is_one_pass_compact_reconstructable_and_truthful_about_parity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    inventory, contexts, calls = _build_synthetic(monkeypatch, tmp_path)

    assert calls == {
        "page": 4,
        "optimized_pair": 3,
        "public_builder": 6,
        "public_validator": 3,
        "raw_receipt": 2,
    }
    assert inventory["corpus_metrics"]["document_count"] == 1
    assert inventory["corpus_metrics"]["page_count"] == 4
    assert inventory["corpus_metrics"]["page_pair_count"] == 3
    assert inventory["corpus_metrics"]["terminal_page_count"] == 1
    assert (
        inventory["corpus_metrics"]["fragment_occurrence_count"]
        > (inventory["corpus_metrics"]["distinct_fragment_count"])
    )
    assert (
        inventory["corpus_metrics"]["physical_axis_occurrence_count"]
        > (inventory["corpus_metrics"]["distinct_physical_axis_count"])
    )
    parity = inventory["public_fused_parity"]
    assert parity["required_observed_categories"] == list(inventory_v1._REQUIRED_PARITY_CATEGORIES)
    assert parity["covered_categories"] == list(inventory_v1._REQUIRED_PARITY_CATEGORIES)
    assert parity["call_count"] == {
        "distinct_sentinel_pair_count": 3,
        "direct_public_builder_api_call_count": 3,
        "public_validator_api_call_count": 3,
        "total_public_builder_api_invocation_count": 6,
    }
    assert [item["covered_categories"] for item in parity["pair_receipts"]] == [
        ["MEASURED_FRAGMENT_PAIR", "UNEQUAL_AXIS_COUNT_RELATION"],
        ["ZERO_COUNTERPART_PAIR"],
        ["TERMINAL_BARRIER_PAIR"],
    ]
    for pair in inventory["page_pairs"]:
        full = inventory_v1._reconstruct_full_gate(
            inventory["gate_common_contract"], pair["gate_receipt"]
        )
        assert canonical_json_sha256_v1(full) == pair["gate_receipt"]["gate_canonical_sha256"]
        assert full["artifact_identity"] == pair["gate_receipt"]["gate_artifact_identity"]
        assert "policy" not in pair["gate_receipt"]
        assert "safety" not in pair["gate_receipt"]
    upstream = gate_v1.build_adjacent_page_table_geometry_candidate_gate_v1(
        contexts[0]["projection"],
        contexts[0]["proposal"],
        contexts[0]["graph"],
        contexts[1]["projection"],
        contexts[1]["proposal"],
        contexts[1]["graph"],
    )
    relation = gate_v1.build_adjacent_page_table_geometry_relations_v1(
        contexts[0]["projection"],
        contexts[0]["proposal"],
        contexts[0]["graph"],
        contexts[1]["projection"],
        contexts[1]["proposal"],
        contexts[1]["graph"],
    )
    assert (
        upstream["artifact_identity"]
        == inventory["page_pairs"][0]["gate_receipt"]["gate_artifact_identity"]
    )
    assert (
        inventory["page_pairs"][0]["previous_page"]["relation_page_binding_id"]
        == relation["ordered_page_pair"]["previous_page_binding"]["page_binding_id"]
    )
    assert (
        inventory["page_pairs"][0]["following_page"]["relation_page_binding_id"]
        == relation["ordered_page_pair"]["following_page_binding"]["page_binding_id"]
    )
    assert inventory["safety"]["accepted_relation_claimed"] is False
    assert inventory["safety"]["continuation_claimed"] is False
    assert inventory["safety"]["downstream_exact_raw_artifact_sha256_pin_required"] is True


@pytest.mark.parametrize(
    (
        "previous_y_values",
        "following_y_values",
        "following_boxes",
        "expected_table_mask",
        "expected_page_mask",
    ),
    [
        pytest.param(
            (900, 980, 1_060, 1_140),
            (20, 100, 180, 260),
            ((300, 380), (450, 530)),
            [False, False, False],
            [False, True],
            id="pair-50-like-previous-bottom-outside",
        ),
        pytest.param(
            (1_240, 1_320, 1_400, 1_480),
            (200, 280, 360, 440),
            ((100, 180), (350, 430), (600, 680)),
            [True, True, True],
            [True, False],
            id="inverse-following-top-outside",
        ),
    ],
)
def test_compact_canonical_roundtrip_preserves_asymmetric_page_mask_order(
    previous_y_values: tuple[int, ...],
    following_y_values: tuple[int, ...],
    following_boxes: tuple[tuple[int, int], ...],
    expected_table_mask: list[bool],
    expected_page_mask: list[bool],
) -> None:
    previous_boxes = ((100, 180), (350, 430), (600, 680))
    previous = _ocr_page_graph(
        1,
        [(y, list(previous_boxes)) for y in previous_y_values],
    )
    following = _ocr_page_graph(
        2,
        [(y, list(following_boxes)) for y in following_y_values],
    )
    gate = gate_v1.build_adjacent_page_table_geometry_candidate_gate_v1(
        *previous,
        *following,
    )

    assert len(gate["relation_dispositions"]) == 1
    relation = gate["relation_dispositions"][0]
    expected_joint_mask = [*expected_table_mask, *expected_page_mask]
    assert list(relation["page_boundary_envelope_checks"]) == [
        "following_top_within_cap",
        "previous_bottom_within_cap",
    ]
    assert relation["page_boundary_envelope_checks"] == {
        "following_top_within_cap": expected_page_mask[1],
        "previous_bottom_within_cap": expected_page_mask[0],
    }
    assert relation["table_shape_envelope_mask"] == expected_table_mask
    assert relation["page_boundary_envelope_mask"] == expected_page_mask
    assert relation["table_page_joint_envelope_mask"] == expected_joint_mask

    receipt = inventory_v1._compact_gate_receipt(gate)
    round_tripped = decode_canonical_json_bytes_v1(canonical_json_bytes_v1(receipt))
    validated = inventory_v1._validate_gate_receipt(
        round_tripped,
        common=inventory_v1._EXPECTED_GATE_COMMON,
        expected_page_pair_id=gate["upstream_binding"]["page_pair_id"],
    )
    reconstructed = inventory_v1._reconstruct_full_gate(
        inventory_v1._EXPECTED_GATE_COMMON,
        validated,
    )

    assert validated["relation_dispositions"][0]["page_boundary_envelope_mask"] == (
        expected_page_mask
    )
    assert validated["relation_dispositions"][0]["table_page_joint_envelope_mask"] == (
        expected_joint_mask
    )
    assert canonical_json_bytes_v1(reconstructed) == canonical_json_bytes_v1(gate)


def test_standalone_validator_is_deterministic_and_does_not_replay_inputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    inventory, _contexts, _calls = _build_synthetic(monkeypatch, tmp_path)
    monkeypatch.setattr(
        inventory_v1,
        "_load_source_inventory",
        lambda _root: (_ for _ in ()).throw(AssertionError("source replay forbidden")),
    )
    monkeypatch.setattr(
        inventory_v1,
        "_load_prestructural_inventory",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("graph replay forbidden")),
    )
    monkeypatch.setattr(
        gate_v1,
        "build_adjacent_page_table_geometry_candidate_gate_v1",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("gate replay forbidden")),
    )

    first = inventory_v1.validate_wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1(
        inventory
    )
    second = inventory_v1.validate_wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1(
        first
    )

    assert canonical_json_bytes_v1(first) == canonical_json_bytes_v1(second)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda value: value["page_pairs"][0]["gate_receipt"]["axis_distance_dispositions"][
                0
            ].update(
                {
                    "bidirectionally_singleton_axis_seed_link": False,
                    "primary_disposition": "WITHIN_AXIS_ENVELOPE_AMBIGUOUS_SEED_LINK",
                }
            ),
            "axis-distance mask/disposition",
        ),
        (
            lambda value: value["page_pairs"][0]["gate_receipt"]["fragment_dispositions"][0].update(
                {"upstream_primary_disposition": ("RETAINED_WITHOUT_CROSS_PAGE_COUNTERPART")}
            ),
            "fragment occurrence incidence",
        ),
        (
            lambda value: value["public_fused_parity"]["pair_receipts"][0].update(
                {"covered_categories": ["MEASURED_FRAGMENT_PAIR"]}
            ),
            "parity pair categories",
        ),
    ],
)
def test_validator_rejects_rehashed_disposition_and_parity_forgery(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mutation,
    message: str,
) -> None:
    inventory, _contexts, _calls = _build_synthetic(monkeypatch, tmp_path)
    broken = deepcopy(inventory)
    mutation(broken)
    receipt = broken["page_pairs"][0]["gate_receipt"]
    if "axis-distance" in message:
        item = receipt["axis_distance_dispositions"][0]
        item["axis_distance_disposition_id"] = inventory_v1._disposition_identity(
            item,
            field="axis_distance_disposition_id",
            namespace="axis_distance_disposition",
        )
        _refresh_gate_receipt(receipt)
    elif "fragment" in message:
        item = receipt["fragment_dispositions"][0]
        item["fragment_disposition_id"] = inventory_v1._disposition_identity(
            item,
            field="fragment_disposition_id",
            namespace="fragment_disposition",
        )
        _refresh_gate_receipt(receipt)
    _refresh_inventory(broken)

    with pytest.raises(
        inventory_v1.Wave1AdjacentPageTableGeometryCandidateGateInventoryV1Error,
        match=message,
    ):
        inventory_v1.validate_wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1(broken)


def test_validator_rejects_rehashed_pair_chain_rollup_and_authority_tampering(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    inventory, _contexts, _calls = _build_synthetic(monkeypatch, tmp_path)

    broken_chain = deepcopy(inventory)
    broken_chain["page_pairs"][1]["previous_page"]["graph_sha256"] = "0" * 64
    _refresh_inventory(broken_chain)
    with pytest.raises(
        inventory_v1.Wave1AdjacentPageTableGeometryCandidateGateInventoryV1Error,
        match="source-order chain",
    ):
        inventory_v1.validate_wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1(
            broken_chain
        )

    broken_rollup = deepcopy(inventory)
    broken_rollup["documents"][0]["fragment_occurrence_count"] += 1
    _refresh_inventory(broken_rollup)
    with pytest.raises(
        inventory_v1.Wave1AdjacentPageTableGeometryCandidateGateInventoryV1Error,
        match="document gate rollups",
    ):
        inventory_v1.validate_wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1(
            broken_rollup
        )

    broken_authority = deepcopy(inventory)
    broken_authority["authority"]["gate_contract"]["module_sha256"] = "0" * 64
    _refresh_inventory(broken_authority)
    with pytest.raises(
        inventory_v1.Wave1AdjacentPageTableGeometryCandidateGateInventoryV1Error,
        match="gate implementation authority",
    ):
        inventory_v1.validate_wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1(
            broken_authority
        )


def test_validator_rejects_rehashed_binding_and_graph_node_identity_forgery(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    inventory, _contexts, _calls = _build_synthetic(monkeypatch, tmp_path)

    broken_binding = deepcopy(inventory)
    broken_binding["page_pairs"][1]["previous_page"]["relation_page_binding_id"] = (
        "apgrv1:page_binding:" + "0" * 64
    )
    _refresh_inventory(broken_binding)
    with pytest.raises(
        inventory_v1.Wave1AdjacentPageTableGeometryCandidateGateInventoryV1Error,
        match="source-order chain",
    ):
        inventory_v1.validate_wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1(
            broken_binding
        )

    for collection, field in (
        ("fragment_dispositions", "table_node_id"),
        ("axis_dispositions", "axis_node_id"),
    ):
        broken_node = deepcopy(inventory)
        receipt = broken_node["page_pairs"][0]["gate_receipt"]
        item = receipt[collection][0]
        item[field] = "forged-node"
        identity_field = (
            "fragment_disposition_id"
            if collection == "fragment_dispositions"
            else "axis_disposition_id"
        )
        namespace = (
            "fragment_disposition" if collection == "fragment_dispositions" else "axis_disposition"
        )
        item[identity_field] = inventory_v1._disposition_identity(
            item,
            field=identity_field,
            namespace=namespace,
        )
        _refresh_gate_receipt(receipt)
        _refresh_inventory(broken_node)
        with pytest.raises(
            inventory_v1.Wave1AdjacentPageTableGeometryCandidateGateInventoryV1Error,
            match="occurrence disposition",
        ):
            inventory_v1.validate_wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1(
                broken_node
            )


def test_validator_rejects_rehashed_proposal_digest_reused_across_pages(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    inventory, _contexts, _calls = _build_synthetic(monkeypatch, tmp_path)
    broken = deepcopy(inventory)
    reused = broken["page_pairs"][0]["following_page"]["source_proposal_projection_sha256"]
    broken["page_pairs"][1]["following_page"]["source_proposal_projection_sha256"] = reused
    broken["page_pairs"][2]["previous_page"]["source_proposal_projection_sha256"] = reused
    _refresh_inventory(broken)

    with pytest.raises(
        inventory_v1.Wave1AdjacentPageTableGeometryCandidateGateInventoryV1Error,
        match="cover every finalized page exactly once",
    ):
        inventory_v1.validate_wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1(broken)


def test_validator_rejects_valid_typed_middle_page_candidate_signature_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    inventory, _contexts, _calls = _build_synthetic(monkeypatch, tmp_path)
    broken = deepcopy(inventory)
    receipt = broken["page_pairs"][1]["gate_receipt"]
    fragment = next(
        item for item in receipt["fragment_dispositions"] if item["side"] == "PREVIOUS_PAGE"
    )
    fragment["table_node_id"] = "ssgv1:node:" + "0" * 64
    fragment["fragment_disposition_id"] = inventory_v1._disposition_identity(
        fragment,
        field="fragment_disposition_id",
        namespace="fragment_disposition",
    )
    _refresh_gate_receipt(receipt)
    _refresh_inventory(broken)

    with pytest.raises(
        inventory_v1.Wave1AdjacentPageTableGeometryCandidateGateInventoryV1Error,
        match="candidate signature",
    ):
        inventory_v1.validate_wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1(broken)


def test_typed_validator_rejects_bool_for_integer_after_outer_rehash(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    inventory, _contexts, _calls = _build_synthetic(monkeypatch, tmp_path)
    broken = deepcopy(inventory)
    broken["page_pairs"][0]["pair_ordinal"] = True
    _refresh_inventory(broken)

    with pytest.raises(
        inventory_v1.Wave1AdjacentPageTableGeometryCandidateGateInventoryV1Error,
        match="positive integer",
    ):
        inventory_v1.validate_wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1(broken)


def test_optimized_path_rejects_public_adjacency_precondition_drift() -> None:
    triples = _synthetic_page_triples()
    contexts = [_context(triple, index) for index, triple in enumerate(triples[:2], 1)]
    broken = deepcopy(contexts[1])
    broken["projection"]["source_locator"]["source_size_bytes"] += 1

    with pytest.raises(
        inventory_v1.Wave1AdjacentPageTableGeometryCandidateGateInventoryV1Error,
        match="public adjacency preconditions",
    ):
        inventory_v1._relation_inputs_from_contexts(contexts[0], broken)


def test_producer_ledger_is_exactly_the_36_file_transitive_runtime_closure() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert all("role_a" not in name for name in imports)
    assert all("schema" not in name for name in imports)
    assert all("mapping" not in name for name in imports)
    assert all("model" not in name for name in imports)
    assert all("pdf" not in name for name in imports)

    implementation_paths = set(inventory_v1._IMPLEMENTATION_PATHS)
    package_root = Path("src/bctc_ai")

    def with_initializers(relative: Path) -> set[Path]:
        output = {relative}
        parent = relative.parent
        while parent == package_root or package_root in parent.parents:
            initializer = parent / "__init__.py"
            if (PROJECT_ROOT / initializer).is_file():
                output.add(initializer)
            if parent == package_root:
                break
            parent = parent.parent
        return output

    def local_module(module: str) -> Path | None:
        if not module.startswith("bctc_ai"):
            return None
        candidate = Path("src", *module.split(".")).with_suffix(".py")
        if (PROJECT_ROOT / candidate).is_file():
            return candidate
        initializer = Path("src", *module.split("."), "__init__.py")
        return initializer if (PROJECT_ROOT / initializer).is_file() else None

    start = Path(
        "src/bctc_ai/source_structure/"
        "wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1.py"
    )
    closure = with_initializers(start)
    pending = list(closure)
    while pending:
        relative = pending.pop()
        local_tree = ast.parse((PROJECT_ROOT / relative).read_text(encoding="utf-8"))
        for node in ast.walk(local_tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules = [
                    node.module,
                    *(f"{node.module}.{alias.name}" for alias in node.names),
                ]
            for module in modules:
                candidate = local_module(module)
                if candidate is None:
                    continue
                for discovered in with_initializers(candidate) - closure:
                    closure.add(discovered)
                    pending.append(discovered)
    closure.update(with_initializers(Path("src/bctc_ai/corpus/wave1_pre_ocr_structure.py")))

    assert closure == implementation_paths
    assert len(implementation_paths) == 36
    producer = _producer()
    inventory_v1._validate_producer_structure(producer)
    records = {item["path"]: item for item in producer["implementation_ledger"]["records"]}
    assert records[inventory_v1._RELATION_MODULE_PATH.as_posix()]["sha256"] == (
        inventory_v1._RELATION_MODULE_SHA256
    )
    assert records[inventory_v1._GATE_MODULE_PATH.as_posix()]["sha256"] == (
        inventory_v1._GATE_MODULE_SHA256
    )


def test_gate_authority_pins_exact_a157_module_and_focused_test_bytes() -> None:
    for path, digest, size in (
        (
            inventory_v1._GATE_MODULE_PATH,
            inventory_v1._GATE_MODULE_SHA256,
            inventory_v1._GATE_MODULE_SIZE_BYTES,
        ),
        (
            inventory_v1._GATE_TEST_PATH,
            inventory_v1._GATE_TEST_SHA256,
            inventory_v1._GATE_TEST_SIZE_BYTES,
        ),
    ):
        payload = inventory_v1.sentinel._git_blob(
            PROJECT_ROOT, inventory_v1._GATE_PRODUCER_COMMIT, path
        )
        assert len(payload) == size
        assert sha256(payload).hexdigest() == digest
    inventory_v1._verify_gate_commit_authority(
        PROJECT_ROOT,
        current_commit="1c422edc30a43adc7078a5603766d4b3f1ce1f54",
    )


def test_exclusive_publisher_seals_one_read_only_inode_and_refuses_overwrite(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    relative = Path("out/gate-inventory.json")
    (tmp_path / relative.parent).mkdir(parents=True)
    monkeypatch.setattr(
        inventory_v1,
        "WAVE1_ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_INVENTORY_OUTPUT_RELATIVE_PATH_V1",
        relative,
    )
    payload = canonical_json_bytes_v1({"candidate_only": True})

    path = inventory_v1._publish_canonical_exclusive(tmp_path, payload)

    identity = path.stat()
    assert path.read_bytes() == payload
    assert stat.S_IMODE(identity.st_mode) == 0o444
    assert identity.st_nlink == 1
    assert not list(path.parent.glob(f".{path.name}.*.tmp"))
    with pytest.raises(
        inventory_v1.Wave1AdjacentPageTableGeometryCandidateGateInventoryV1Error,
        match="destination already exists",
    ):
        inventory_v1._publish_canonical_exclusive(tmp_path, payload)


def test_exclusive_publisher_preserves_race_winner_and_cleans_owned_temporary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    relative = Path("out/gate-inventory.json")
    parent = tmp_path / relative.parent
    parent.mkdir(parents=True)
    monkeypatch.setattr(
        inventory_v1,
        "WAVE1_ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_INVENTORY_OUTPUT_RELATIVE_PATH_V1",
        relative,
    )
    competitor = b"competitor\n"
    real_link = os.link

    def race_link(
        src: str,
        dst: str,
        *,
        src_dir_fd: int,
        dst_dir_fd: int,
        follow_symlinks: bool,
    ) -> None:
        descriptor = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444, dir_fd=dst_dir_fd)
        try:
            os.write(descriptor, competitor)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        real_link(
            src,
            dst,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )

    monkeypatch.setattr(inventory_v1.os, "link", race_link)
    with pytest.raises(
        inventory_v1.Wave1AdjacentPageTableGeometryCandidateGateInventoryV1Error,
        match="exclusive race",
    ):
        inventory_v1._publish_canonical_exclusive(
            tmp_path, canonical_json_bytes_v1({"candidate_only": True})
        )

    assert (tmp_path / relative).read_bytes() == competitor
    assert sorted(item.name for item in parent.iterdir()) == [relative.name]


def test_postlink_precommit_failure_removes_owned_final_and_temporary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    relative = Path("out/gate-inventory.json")
    parent = tmp_path / relative.parent
    parent.mkdir(parents=True)
    monkeypatch.setattr(
        inventory_v1,
        "WAVE1_ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_INVENTORY_OUTPUT_RELATIVE_PATH_V1",
        relative,
    )
    real_fsync = os.fsync
    failed = False

    def fail_first_directory_fsync(descriptor: int) -> None:
        nonlocal failed
        if not failed and stat.S_ISDIR(os.fstat(descriptor).st_mode):
            failed = True
            raise OSError("injected post-link directory fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(inventory_v1.os, "fsync", fail_first_directory_fsync)
    with pytest.raises(
        inventory_v1.Wave1AdjacentPageTableGeometryCandidateGateInventoryV1Error,
        match="publication failed",
    ):
        inventory_v1._publish_canonical_exclusive(
            tmp_path, canonical_json_bytes_v1({"candidate_only": True})
        )

    assert failed is True
    assert list(parent.iterdir()) == []


def test_public_publisher_rechecks_inputs_producer_and_gate_before_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    inventory = {"producer": {"receipt": True}, "inventory_identity_sha256": "a" * 64}
    target = tmp_path / "published.json"
    calls: list[str] = []
    monkeypatch.setattr(
        inventory_v1, "_require_destination_absent", lambda _root: calls.append("absent")
    )
    monkeypatch.setattr(
        inventory_v1,
        "build_wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1",
        lambda _root: deepcopy(inventory),
    )
    monkeypatch.setattr(
        inventory_v1,
        "validate_wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1",
        lambda value: calls.append("validate") or value,
    )
    monkeypatch.setattr(
        inventory_v1, "_input_raw_receipts", lambda _root: calls.append("inputs") or {}
    )
    monkeypatch.setattr(
        inventory_v1,
        "_producer_receipt",
        lambda _root: calls.append("producer") or deepcopy(inventory["producer"]),
    )
    monkeypatch.setattr(
        inventory_v1,
        "_validate_build_authorities",
        lambda **_kwargs: calls.append("authority"),
    )
    monkeypatch.setattr(
        inventory_v1,
        "_publish_canonical_exclusive",
        lambda _root, _payload: calls.append("publish") or target,
    )

    result = inventory_v1.publish_wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1(
        tmp_path
    )
    payload = canonical_json_bytes_v1(inventory)

    assert calls == ["absent", "validate", "inputs", "producer", "authority", "publish"]
    assert result == (target, sha256(payload).hexdigest(), len(payload), "a" * 64)


def test_static_claim_boundary_output_and_standalone_limits_are_explicit() -> None:
    assert inventory_v1._GATE_COMMON_FIELDS == {
        "format_version",
        "claim_boundary",
        "status",
        "policy",
        "policy_identity",
        "safety",
        "safety_payload_sha256",
    }
    assert inventory_v1._EXPECTED_GATE_COMMON["policy_identity"] == (
        "apgcv1:policy:546be183185551b3eedad630c0f8a425a5f04f370661b5b2674f7e20ac7fbdb8"
    )
    assert inventory_v1._EXPECTED_GATE_COMMON["safety_payload_sha256"] == (
        "1cae3d0ce740ebcd0095de10bf69ff5e0eabaed99fea4e4c58475440d790287d"
    )
    assert inventory_v1._SAFETY["standalone_validator_is_structural_accounting_only"] is True
    assert inventory_v1._SAFETY["standalone_validator_replays_source_or_gate"] is False
    assert inventory_v1._SAFETY["physical_page_used_for_routing"] is False
    assert inventory_v1._SAFETY["role_a_used"] is False
    assert inventory_v1._SAFETY["schema_used"] is False
    assert inventory_v1._SAFETY["source_pdf_opened"] is False
    assert inventory_v1._SAFETY["model_or_reader_invoked"] is False
    assert inventory_v1._SAFETY["network_used"] is False
    assert "os.replace" not in MODULE_PATH.read_text(encoding="utf-8")
    assert (
        inventory_v1.WAVE1_ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_INVENTORY_OUTPUT_RELATIVE_PATH_V1
        == Path(
            "output/development/bank-corpus-survey-v1/"
            "wave-1-role-b-adjacent-page-table-geometry-candidate-gate-inventory-v1.json"
        )
    )


@pytest.mark.skip(reason="deliberate opt-in only: exhaustive real 1,449-page/1,422-pair replay")
def test_real_finalized_wave1_gate_inventory_replay_opt_in() -> None:
    inventory_v1.build_wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1(PROJECT_ROOT)
