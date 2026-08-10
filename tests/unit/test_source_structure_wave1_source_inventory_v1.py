from __future__ import annotations

import ast
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from bctc_ai.source_structure import wave1_source_inventory_v1 as inventory_v1
from bctc_ai.source_structure.contracts_v1 import (
    PrimaryDisposition,
    ProposalKind,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.source_structure.finalized_v3_survey_stream_v1 import (
    AuthenticatedV3SurveyPage,
    FinalizedV3SurveyAuthority,
)

_DOCUMENT_IDS = ("sha256:" + "a" * 64, "sha256:" + "b" * 64)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _authority() -> FinalizedV3SurveyAuthority:
    return FinalizedV3SurveyAuthority(
        aggregate_artifact_sha256="1" * 64,
        aggregate_size_bytes=101,
        aggregate_identity_sha256="2" * 64,
        control_artifact_sha256="3" * 64,
        control_size_bytes=202,
        control_identity_sha256="4" * 64,
        sealed_plan_sha256="5" * 64,
        document_ids=_DOCUMENT_IDS,
        document_count=2,
        request_count=2,
        referenced_object_count=7,
    )


def _pages() -> list[AuthenticatedV3SurveyPage]:
    return [
        AuthenticatedV3SurveyPage(
            page_record={
                "request_ordinal": 1,
                "document_id": _DOCUMENT_IDS[0],
                "physical_page": 1,
            },
            page_result={"synthetic": 1},
        ),
        AuthenticatedV3SurveyPage(
            page_record={
                "request_ordinal": 2,
                "document_id": _DOCUMENT_IDS[1],
                "physical_page": 1,
            },
            page_result={"synthetic": 2},
        ),
    ]


class _FakeStream:
    def __init__(self) -> None:
        self.authority = _authority()
        self._pages = _pages()

    def __iter__(self):
        return iter(self._pages)


def _projection(page_record: dict[str, Any], _page_result: dict[str, Any]) -> dict[str, Any]:
    ordinal = page_record["request_ordinal"]
    terminal = ordinal == 2
    route = "CAUSAL_NATIVE_TEXT" if terminal else "DOMINANT_RASTER_OCR"
    status = "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY" if terminal else "OCR_WORD_BOX_READ_COMPLETE"
    metrics = {
        "atom_count": 1 if terminal else 3,
        "upstream_line_axis_count": 0 if terminal else 1,
        "upstream_word_axis_count": 0 if terminal else 2,
        "upstream_quarantined_span_axis_count": 1 if terminal else 0,
        "primary_line_count": 0 if terminal else 1,
        "primary_word_count": 0 if terminal else 2,
        "excluded_empty_line_axis_count": 0,
        "excluded_empty_word_axis_count": 0,
        "supplemental_line_count": 0,
        "quarantined_atom_count": 1 if terminal else 0,
    }
    coordinate_authority = (
        {
            "canonical_cropbox_bounds_mpt": [0, 0, 900, 600],
        }
        if terminal
        else {"unrotated_dimensions_mpt": [600, 900]}
    )
    return {
        "source_local_page_id": f"ssv2:page:{ordinal:064x}",
        "route": route,
        "upstream_status": status,
        "terminal": terminal,
        "coordinate_authority": coordinate_authority,
        "neutral_page_v1": {
            "source_local_page_id": f"ssv1:page:{ordinal:064x}",
            "metrics": metrics,
        },
    }


def _proposals(projection: dict[str, Any]) -> dict[str, Any]:
    if projection["terminal"]:
        proposals: list[dict[str, Any]] = []
        dispositions = [{"primary_disposition": PrimaryDisposition.UPSTREAM_QUARANTINED.value}]
    else:
        proposals = [
            {
                "kind": ProposalKind.TABULAR_GEOMETRY_CANDIDATE.value,
                "evidence_codes": [
                    "DENSE_TABULAR_ALIGNMENT",
                    "HORIZONTAL_ALIGNMENT",
                    "VERTICAL_GAP_COHERENCE",
                ],
            }
        ]
        dispositions = [
            {"primary_disposition": PrimaryDisposition.OWNED_BY_SOURCE_OBJECT.value},
            {"primary_disposition": PrimaryDisposition.OWNED_BY_SOURCE_OBJECT.value},
            {"primary_disposition": PrimaryDisposition.RETAINED_UNOWNED.value},
        ]
    return {
        "source_local_page_id": projection["neutral_page_v1"]["source_local_page_id"],
        "proposals": proposals,
        "dispositions": dispositions,
    }


def _patch_pipeline(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    calls = {"projection": 0, "proposal": 0, "v2_wrapper": 0}

    @contextmanager
    def open_stream(_project_root: Path):
        yield _FakeStream()

    def projection(*, page_record: dict[str, Any], page_result: dict[str, Any]):
        calls["projection"] += 1
        return _projection(page_record, page_result)

    def proposals(value: dict[str, Any]):
        calls["proposal"] += 1
        return _proposals(value)

    def wrap_v2(
        projection: dict[str, Any],
        *,
        proposal_set_v1: dict[str, Any],
    ) -> dict[str, Any]:
        calls["v2_wrapper"] += 1
        return {
            "source_local_page_id": projection["source_local_page_id"],
            "source_projection_sha256": canonical_json_sha256_v1(projection),
            "proposal_set_v1": proposal_set_v1,
        }

    records = [
        {
            "phase": "READ",
            "kind": "IMPLEMENTATION",
            "path": path.as_posix(),
            "sha256": f"{index + 6:x}" * 64,
            "size_bytes": index + 1,
        }
        for index, path in enumerate(sorted(inventory_v1._SOURCE_STRUCTURE_IMPLEMENTATION_PATHS))
    ]
    producer = {
        "git": {"commit": "f" * 40, "dirty": False},
        "implementation_ledger": {
            "records": records,
            "sha256": canonical_json_sha256_v1(records),
        },
    }

    monkeypatch.setattr(inventory_v1, "open_finalized_v3_survey_stream_v1", open_stream)
    monkeypatch.setattr(inventory_v1, "project_authenticated_page_v2", projection)
    monkeypatch.setattr(inventory_v1, "generate_page_geometry_proposals_v1", proposals)
    monkeypatch.setattr(inventory_v1, "make_page_proposal_set_v2", wrap_v2)
    monkeypatch.setattr(inventory_v1, "FINALIZED_V3_SURVEY_AUTHORITY_V1", _authority())
    monkeypatch.setattr(
        inventory_v1,
        "_source_structure_producer_receipt",
        lambda _project_root: deepcopy(producer),
    )
    return calls


def test_builder_composes_pages_into_one_compact_no_drop_inventory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls = _patch_pipeline(monkeypatch)

    inventory = inventory_v1.build_wave1_source_inventory_v1(tmp_path)

    assert calls == {"projection": 2, "proposal": 2, "v2_wrapper": 2}
    assert inventory["authority"]["document_ids"] == list(_DOCUMENT_IDS)
    assert len(inventory["documents"]) == 2
    assert len(inventory["pages"]) == 2
    assert inventory["corpus_metrics"] == {
        "document_count": 2,
        "page_count": 2,
        "source_accounted_page_count": 2,
        "complete_page_count": 1,
        "terminal_page_count": 1,
        "route_counts": {"CAUSAL_NATIVE_TEXT": 1, "DOMINANT_RASTER_OCR": 1},
        "status_counts": {
            "CAUSAL_NATIVE_TEXT_READ_COMPLETE": 0,
            "OCR_WORD_BOX_READ_COMPLETE": 1,
            "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY": 1,
            "UNRESOLVED_OCR_WORD_BOX_GEOMETRY": 0,
        },
        "atom_count": 4,
        "upstream_line_axis_count": 1,
        "upstream_word_axis_count": 2,
        "upstream_quarantined_span_axis_count": 1,
        "primary_line_count": 1,
        "primary_word_count": 2,
        "excluded_empty_line_axis_count": 0,
        "excluded_empty_word_axis_count": 0,
        "supplemental_line_count": 0,
        "quarantined_atom_count": 1,
        "proposal_count": 1,
        "source_accounted_atom_count": 4,
        "proposal_kind_counts": {
            "CONTINUATION_GEOMETRY_CANDIDATE": 0,
            "SOURCE_BLOCK_CANDIDATE": 0,
            "TABULAR_GEOMETRY_CANDIDATE": 1,
        },
        "disposition_counts": {
            "OWNED_BY_SOURCE_OBJECT": 2,
            "RETAINED_UNOWNED": 1,
            "UPSTREAM_QUARANTINED": 1,
            "UPSTREAM_TERMINAL_UNRESOLVED": 0,
        },
        "distinct_topology_fingerprint_count": 2,
    }
    assert all(
        page["metrics"]["source_accounted_atom_count"] == page["metrics"]["atom_count"]
        for page in inventory["pages"]
    )
    payload = canonical_json_bytes_v1(inventory)
    assert b"raw_text" not in payload
    assert b"canonical_bbox" not in payload
    assert b"evidence_codes" not in payload


def test_builder_is_deterministic_and_identity_bound(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_pipeline(monkeypatch)

    first = inventory_v1.build_wave1_source_inventory_v1(tmp_path)
    second = inventory_v1.build_wave1_source_inventory_v1(tmp_path)

    assert first == second
    corrupted = deepcopy(first)
    corrupted["pages"][0]["metrics"]["source_accounted_atom_count"] -= 1
    with pytest.raises(inventory_v1.Wave1SourceInventoryError, match="source accounting"):
        inventory_v1.validate_wave1_source_inventory_v1(corrupted)


def test_validator_rejects_duplicate_projection_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_pipeline(monkeypatch)
    inventory = inventory_v1.build_wave1_source_inventory_v1(tmp_path)
    inventory["pages"][1]["projection_identity"] = inventory["pages"][0]["projection_identity"]

    with pytest.raises(
        inventory_v1.Wave1SourceInventoryError,
        match="binding|coverage/identity",
    ):
        inventory_v1.validate_wave1_source_inventory_v1(inventory)


def test_validator_requires_the_exact_authenticated_stream_authority(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_pipeline(monkeypatch)
    inventory = inventory_v1.build_wave1_source_inventory_v1(tmp_path)
    inventory["authority"]["aggregate_identity_sha256"] = "0" * 64
    inventory["inventory_identity_sha256"] = canonical_json_sha256_v1(
        {key: value for key, value in inventory.items() if key != "inventory_identity_sha256"}
    )

    with pytest.raises(inventory_v1.Wave1SourceInventoryError, match="exact finalized V3 pin"):
        inventory_v1.validate_wave1_source_inventory_v1(inventory)


def test_page_validator_rejects_cross_route_status_even_with_refreshed_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_pipeline(monkeypatch)
    inventory = inventory_v1.build_wave1_source_inventory_v1(tmp_path)
    page = deepcopy(inventory["pages"][0])
    page["route"] = "CAUSAL_NATIVE_TEXT"
    page["page_inventory_identity_sha256"] = canonical_json_sha256_v1(
        {key: value for key, value in page.items() if key != "page_inventory_identity_sha256"}
    )

    with pytest.raises(inventory_v1.Wave1SourceInventoryError, match="route/status"):
        inventory_v1._validate_page(page, expected_ordinal=1)


def test_page_validator_counts_empty_axis_once_in_quarantine_authority_partition(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_pipeline(monkeypatch)
    inventory = inventory_v1.build_wave1_source_inventory_v1(tmp_path)
    page = deepcopy(inventory["pages"][0])
    metrics = page["metrics"]
    metrics.update(
        {
            "atom_count": 4,
            "upstream_line_axis_count": 2,
            "excluded_empty_line_axis_count": 1,
            "quarantined_atom_count": 1,
            "source_accounted_atom_count": 4,
            "disposition_counts": {
                "OWNED_BY_SOURCE_OBJECT": 2,
                "RETAINED_UNOWNED": 1,
                "UPSTREAM_QUARANTINED": 1,
                "UPSTREAM_TERMINAL_UNRESOLVED": 0,
            },
        }
    )
    page["page_inventory_identity_sha256"] = canonical_json_sha256_v1(
        {key: value for key, value in page.items() if key != "page_inventory_identity_sha256"}
    )

    assert inventory_v1._validate_page(page, expected_ordinal=1) == page


def test_page_validator_rejects_terminal_primary_candidate_promotion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_pipeline(monkeypatch)
    inventory = inventory_v1.build_wave1_source_inventory_v1(tmp_path)
    page = deepcopy(inventory["pages"][1])
    metrics = page["metrics"]
    metrics.update(
        {
            "upstream_line_axis_count": 1,
            "upstream_quarantined_span_axis_count": 0,
            "primary_line_count": 1,
            "quarantined_atom_count": 0,
            "proposal_count": 1,
            "proposal_kind_counts": {
                "CONTINUATION_GEOMETRY_CANDIDATE": 0,
                "SOURCE_BLOCK_CANDIDATE": 1,
                "TABULAR_GEOMETRY_CANDIDATE": 0,
            },
            "disposition_counts": {
                "OWNED_BY_SOURCE_OBJECT": 1,
                "RETAINED_UNOWNED": 0,
                "UPSTREAM_QUARANTINED": 0,
                "UPSTREAM_TERMINAL_UNRESOLVED": 0,
            },
        }
    )
    page["page_inventory_identity_sha256"] = canonical_json_sha256_v1(
        {key: value for key, value in page.items() if key != "page_inventory_identity_sha256"}
    )

    with pytest.raises(inventory_v1.Wave1SourceInventoryError, match="terminal page promoted"):
        inventory_v1._validate_page(page, expected_ordinal=2)


def test_source_structure_producer_ledger_covers_recursive_local_import_closure() -> None:
    package_prefix = "bctc_ai.source_structure"
    package_root = Path("src/bctc_ai/source_structure")
    initializer = package_root / "__init__.py"
    entrypoint = package_root / "wave1_source_inventory_v1.py"
    closure = {initializer, entrypoint}
    pending = [entrypoint]

    def local_module_path(module: str) -> Path | None:
        if module == package_prefix:
            return initializer
        if not module.startswith(package_prefix + "."):
            return None
        relative = Path("src", *module.split(".")).with_suffix(".py")
        return relative if (_PROJECT_ROOT / relative).is_file() else None

    while pending:
        relative = pending.pop()
        tree = ast.parse((_PROJECT_ROOT / relative).read_text(encoding="utf-8"))
        discovered: set[Path] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                discovered.update(
                    candidate
                    for alias in node.names
                    if (candidate := local_module_path(alias.name)) is not None
                )
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                parent = local_module_path(node.module)
                if parent is not None:
                    discovered.add(parent)
                if node.module == package_prefix:
                    discovered.update(
                        candidate
                        for alias in node.names
                        if (candidate := local_module_path(f"{package_prefix}.{alias.name}"))
                        is not None
                    )
        for candidate in discovered - closure:
            closure.add(candidate)
            pending.append(candidate)

    assert closure == set(inventory_v1._SOURCE_STRUCTURE_IMPLEMENTATION_PATHS)
