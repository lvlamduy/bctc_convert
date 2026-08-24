from __future__ import annotations

import copy
import importlib.util
import os
import sys
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT / "scripts/experiments/build_family_first_loan_geography_140_filing_schema_sweep_v1.py"
)
_SPEC = importlib.util.spec_from_file_location("loan_geography_140_sweep_test", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
sweep_v1 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = sweep_v1
_SPEC.loader.exec_module(sweep_v1)


def _packet(ordinal: int, bank: str, *, pages: int, lines: int) -> dict:
    material = {
        "assurance": "AUDITED",
        "bank_provenance": bank,
        "document_evidence_root_sha256": f"{ordinal + 1000:064x}",
        "document_id": f"synthetic-{ordinal}",
        "document_ordinal": ordinal,
        "line_count": lines,
        "page_count": pages,
        "period": "ANNUAL",
        "scope": "CONSOLIDATED",
        "source_pdf_ref": {
            "path": f"opaque/source-{ordinal}.pdf",
            "sha256": f"{ordinal + 2000:064x}",
            "size_bytes": 1000 + ordinal,
        },
        "year": 2025,
    }
    return {
        **material,
        "packet_id": "ffdesv1:document:" + canonical_json_sha256_v1(material),
    }


def _graph(
    ordinal: int,
    disposition: str = "NOT_OBSERVED",
    *,
    packet: dict | None = None,
    receipt_id: str = "receipt",
    continuation_mode: str | None = None,
) -> dict:
    document_id = packet["document_id"] if packet is not None else f"synthetic-{ordinal}"
    packet_id = packet["packet_id"] if packet is not None else f"packet-{ordinal}"
    fingerprint = {
        "disposition": disposition,
        "partial": False,
        "regions": (
            [{"continuation": {"mode": continuation_mode}}] if continuation_mode is not None else []
        ),
        "semantic_region": ordinal,
    }
    material = {
        "disposition": disposition,
        "document_id": document_id,
        "document_ordinal": ordinal,
        "evidence_binding": {
            "document_packet_id": packet_id,
            "outcome_id": f"outcome-{ordinal}",
            "receipt_id": receipt_id,
        },
        "family_id": "LOAN_GEOGRAPHIC_CLASSIFICATION",
        "format_version": sweep_v1.graph_v1.DOCUMENT_FORMAT_VERSION,
        "ordinal": ordinal,
        "region_fingerprint": fingerprint,
        "spec_id": "synthetic-spec",
        "uniqueness": {
            "exact_logical_graph_count": 0,
            "multiple_identical_region_count": 0,
            "partial_nonterminal_graph_count": 0,
            "physical_region_count": 0,
        },
    }
    return {
        **material,
        "result_id": "lgstv1:document:" + canonical_json_sha256_v1(material),
    }


def _coverage(ordinal: int, receipt_id: str) -> dict:
    return {
        "coverage_status": "PROVEN_COMPLETE_FOR_DECLARED_SPEC",
        "outcome_id": f"outcome-{ordinal}",
        "receipt_id": receipt_id,
        "requires_full_document_review": False,
        "selected_line_count": 1,
        "selected_page_count": 1,
        "selection_mode": "EXHAUSTIVE_NECESSARY_SEED_UNION",
    }


def _context(packet: dict, *, snapshot_id: str = "snapshot") -> dict:
    material = {
        "claim_boundary": "synthetic",
        "document_evidence_root_sha256": packet["document_evidence_root_sha256"],
        "document_id": packet["document_id"],
        "document_packet_id": packet["packet_id"],
        "format_version": sweep_v1.graph_v1.DOCUMENT_CONTEXT_FORMAT_VERSION,
        "period_context": {},
        "snapshot_id": snapshot_id,
        "state": "FULL_DOCUMENT_PDF_INTERNAL_CONTEXT_PROPOSAL",
        "unit_context": {},
    }
    return {
        **material,
        "result_id": "lgstv1:document-context:" + canonical_json_sha256_v1(material),
    }


def _bound_graph(
    packet: dict,
    *,
    snapshot_id: str,
    receipt_id: str = "receipt",
    outcome_id: str | None = None,
    disposition: str = "NOT_OBSERVED",
) -> dict:
    value = _graph(
        packet["document_ordinal"],
        disposition,
        packet=packet,
        receipt_id=receipt_id,
    )
    value["evidence_binding"] = {
        "document_evidence_root_sha256": packet["document_evidence_root_sha256"],
        "document_id": packet["document_id"],
        "document_ordinal": packet["document_ordinal"],
        "document_packet_id": packet["packet_id"],
        "outcome_id": outcome_id or f"outcome-{packet['document_ordinal']}",
        "receipt_id": receipt_id,
        "snapshot_id": snapshot_id,
    }
    material = copy.deepcopy(value)
    material.pop("result_id")
    value["result_id"] = "lgstv1:document:" + canonical_json_sha256_v1(material)
    return value


def _worker_inputs(
    count: int = 2,
    *,
    disposition: str = "NOT_OBSERVED",
) -> tuple[dict, tuple[dict, ...], tuple[dict, ...]]:
    packets = tuple(_packet(ordinal, "ACB", pages=1, lines=1) for ordinal in range(1, count + 1))
    snapshots = tuple(
        {
            "document_packet": packet,
            "joined_pages": [
                {
                    "lines": [
                        {
                            "bbox": [10, 20, 100, 40],
                            "crop_ref": {
                                "path": "crop.png",
                                "sha256": f"{packet['document_ordinal'] + 10000:064x}",
                                "size_bytes": 5,
                            },
                            "line_ordinal": 0,
                            "numeric_recognition": {
                                "raw_prediction": "120",
                                "reader_score": 0.99,
                            },
                            "sample_id": f"sample-{packet['document_ordinal']}",
                            "vietocr_text": "120",
                        }
                    ],
                    "page_sequence": 1,
                    "page_width": 300,
                }
            ],
            "manifest_id": "ffdesv1:manifest:" + f"{packet['document_ordinal'] + 7000:064x}",
            "query_selection_id": "ffoqcv1:selection:"
            + f"{packet['document_ordinal'] + 8000:064x}",
            "selected_page_dimensions": [
                {
                    "physical_page": 1,
                    "pixel_height": 200,
                    "pixel_width": 300,
                    "render_sha256": f"{packet['document_ordinal'] + 9000:064x}",
                    "render_size_bytes": 10,
                }
            ],
            "snapshot_id": f"snapshot-{packet['document_ordinal']}",
        }
        for packet in packets
    )
    receipt = {
        "documents": [
            {
                "coverage_status": "PROVEN_COMPLETE_FOR_DECLARED_SPEC",
                "document_ordinal": ordinal,
                "outcome_id": f"outcome-{ordinal}",
                "requires_full_document_review": False,
                "selected_pages": [1],
                "selection_mode": "EXHAUSTIVE_NECESSARY_SEED_UNION",
            }
            for ordinal in range(1, count + 1)
        ],
        "receipt_id": "receipt",
    }
    sparse = tuple(
        _bound_graph(
            packet,
            snapshot_id=f"sparse-snapshot-{packet['document_ordinal']}",
            disposition=disposition,
        )
        for packet in packets
    )
    return receipt, snapshots, sparse


def _install_worker_graph_stubs(
    monkeypatch: pytest.MonkeyPatch,
    *,
    context_replay_calls: list[str] | None = None,
    control_replay_calls: list[str] | None = None,
    request_replay_calls: list[str] | None = None,
    whole_replay_calls: list[str] | None = None,
    disposition: str = "NOT_OBSERVED",
    upstream_control: bool = False,
) -> None:
    monkeypatch.setattr(
        sweep_v1.graph_v1,
        "_prepare_loan_geography_receipt_v1",
        lambda receipt: receipt,
    )
    monkeypatch.setattr(
        sweep_v1.graph_v1,
        "_prepare_loan_geography_snapshot_v1",
        lambda snapshot: snapshot,
    )

    def whole(_receipt: dict, snapshot: dict) -> dict:
        packet = snapshot["document_packet"]
        return _bound_graph(
            packet,
            snapshot_id=snapshot["snapshot_id"],
            disposition=disposition,
        )

    def context(snapshot: dict) -> dict:
        return _context(snapshot["document_packet"], snapshot_id=snapshot["snapshot_id"])

    def replay_whole(value: dict, _receipt: dict, snapshot: dict) -> dict:
        if whole_replay_calls is not None:
            whole_replay_calls.append(snapshot["snapshot_id"])
        return value

    def replay_context(value: dict, snapshot: dict) -> dict:
        if context_replay_calls is not None:
            context_replay_calls.append(snapshot["snapshot_id"])
        return value

    def requests(
        whole_document: dict,
        packet: dict,
        snapshot: dict,
        *,
        document_context: dict,
    ) -> dict:
        assert document_context["snapshot_id"] == snapshot["snapshot_id"]
        graph_id = f"graph-{packet['document_ordinal']}"
        return {
            "document_binding": {
                "document_evidence_root_sha256": packet["document_evidence_root_sha256"],
                "document_id": packet["document_id"],
                "document_ordinal": packet["document_ordinal"],
                "document_packet_id": packet["packet_id"],
                "source_locator_axis_sha256": "1" * 64,
                "source_snapshot_id": snapshot["snapshot_id"],
                "source_whole_document_graph_result_id": whole_document["result_id"],
            },
            "graph_binding": {
                "graph_id": graph_id,
                "region_fingerprint_sha256": canonical_json_sha256_v1(
                    whole_document["region_fingerprint"]
                ),
                "segment_count": 1,
            },
            "lane_requests": [
                {
                    "classification": (
                        "STRUCTURALLY_ABSENT" if upstream_control else "LOCAL_LABELED_TOTAL"
                    ),
                    "control_request_id": (
                        f"control-request-{packet['document_ordinal']}"
                        if upstream_control
                        else None
                    ),
                    "lane_index": 0,
                    "period_end": "2025-12-31",
                }
            ],
            "request_set_id": f"request-set-{packet['document_ordinal']}",
            "source_page_render_bindings": copy.deepcopy(snapshot["selected_page_dimensions"]),
        }

    def replay_requests(
        value: dict,
        _whole_document: dict,
        _packet: dict,
        snapshot: dict,
        *,
        document_context: dict,
    ) -> dict:
        assert document_context["snapshot_id"] == snapshot["snapshot_id"]
        if request_replay_calls is not None:
            request_replay_calls.append(snapshot["snapshot_id"])
        return value

    def control(snapshot: dict, requested_period_end: str) -> dict:
        packet = snapshot["document_packet"]
        line = snapshot["joined_pages"][0]["lines"][0]
        dimension = snapshot["selected_page_dimensions"][0]
        locator = {
            "bbox": copy.deepcopy(line["bbox"]),
            "crop_ref": copy.deepcopy(line["crop_ref"]),
            "page_render": copy.deepcopy(dimension),
            "page_sequence": 1,
            "ppocrv6_reader_score": 0.99,
            "ppocrv6_surface": "120",
            "sample_id": line["sample_id"],
            "source_line_index": 0,
            "vietocr_transformer_surface": "120",
        }
        return {
            "document_binding": {
                "document_evidence_root_sha256": packet["document_evidence_root_sha256"],
                "document_id": packet["document_id"],
                "document_ordinal": packet["document_ordinal"],
                "document_packet_id": packet["packet_id"],
                "line_count": packet["line_count"],
                "manifest_id": snapshot["manifest_id"],
                "page_count": packet["page_count"],
                "query_selection_id": snapshot["query_selection_id"],
                "snapshot_id": snapshot["snapshot_id"],
                "source_pdf_ref": copy.deepcopy(packet["source_pdf_ref"]),
            },
            "owner_evidence": {"evidence": [copy.deepcopy(locator)]},
            "period_lane": {"evidence": [copy.deepcopy(locator)]},
            "requested_period_end": requested_period_end,
            "result_id": f"control-{packet['document_ordinal']}",
            "total_control": {"source": copy.deepcopy(locator)},
            "unit_evidence": {"source": copy.deepcopy(locator)},
        }

    def replay_control(value: dict, snapshot: dict, _period: str) -> dict:
        if control_replay_calls is not None:
            control_replay_calls.append(snapshot["snapshot_id"])
        return value

    def numeric_input(
        _document: dict,
        _packet: dict,
        **kwargs: object,
    ) -> dict:
        request_set = kwargs["upstream_total_control_requests"]
        controls = kwargs["upstream_total_controls"]
        if upstream_control:
            assert len(controls) == 1
            replay_control(
                controls[0],
                kwargs["upstream_total_control_source_snapshot"],
                controls[0]["requested_period_end"],
            )
            control_evidence = {
                "control_request_id": request_set["lane_requests"][0]["control_request_id"],
                "control_result_id": controls[0]["result_id"],
                "lane_index": 0,
                "request_set_id": request_set["request_set_id"],
                "resolution_mode": "UPSTREAM_AUTHENTICATED_CUSTOMER_LOAN_TOTAL_CONTROL",
                "source_document_graph_result_id": request_set["document_binding"][
                    "source_whole_document_graph_result_id"
                ],
                "source_locator": copy.deepcopy(controls[0]["total_control"]["source"]),
                "source_snapshot_id": controls[0]["document_binding"]["snapshot_id"],
            }
        else:
            control_evidence = {
                "lane_index": 0,
                "resolution_mode": "LOCAL_LABELED_TOTAL",
            }
        return {
            "printed_customer_loan_total": {"control_evidence": [control_evidence]},
            "region_id": request_set["graph_binding"]["graph_id"],
            "source_id": "synthetic-overlay",
        }

    def compare(sparse_document: dict, whole_document: dict, **kwargs: int) -> dict:
        result = _equivalence(
            sparse_document,
            sparse_document["disposition"],
            pages=kwargs["whole_document_page_count"],
            lines=kwargs["whole_document_line_count"],
        )
        result["whole_document_graph_result_id"] = whole_document["result_id"]
        return result

    def sparse_batch(_receipt: dict, snapshots: tuple[dict, ...]) -> dict:
        assert len(snapshots) == 1
        snapshot = snapshots[0]
        packet = snapshot["document_packet"]
        document = _bound_graph(
            packet,
            snapshot_id=snapshot["snapshot_id"],
            disposition=disposition,
        )
        material = {"documents": [document], "synthetic": True}
        return {
            **material,
            "result_id": "lgstv1:batch:" + canonical_json_sha256_v1(material),
        }

    monkeypatch.setattr(
        sweep_v1.graph_v1,
        "build_loan_geography_whole_document_scoped_graph_v1",
        whole,
    )
    monkeypatch.setattr(
        sweep_v1.graph_v1,
        "build_loan_geography_document_context_v1",
        context,
    )
    monkeypatch.setattr(
        sweep_v1.graph_v1,
        "validate_loan_geography_whole_document_scoped_graph_replay_v1",
        replay_whole,
    )
    monkeypatch.setattr(
        sweep_v1.graph_v1,
        "validate_loan_geography_document_context_replay_v1",
        replay_context,
    )
    monkeypatch.setattr(
        sweep_v1.graph_v1,
        "build_loan_geography_customer_loan_total_control_requests_v1",
        requests,
    )
    monkeypatch.setattr(
        sweep_v1.graph_v1,
        "validate_loan_geography_customer_loan_total_control_requests_replay_v1",
        replay_requests,
    )
    monkeypatch.setattr(
        sweep_v1.graph_v1,
        "validate_loan_geography_customer_loan_total_control_requests_v1",
        lambda value: copy.deepcopy(value),
    )
    monkeypatch.setattr(
        sweep_v1.graph_v1,
        "project_loan_geography_numeric_input_v1",
        numeric_input,
    )
    monkeypatch.setattr(
        sweep_v1.total_control_v1,
        "build_customer_loan_total_control_v1",
        control,
    )
    monkeypatch.setattr(
        sweep_v1.total_control_v1,
        "validate_customer_loan_total_control_replay_v1",
        replay_control,
    )
    monkeypatch.setattr(
        sweep_v1.total_control_v1,
        "validate_customer_loan_total_control_v1",
        lambda value: copy.deepcopy(value),
    )
    monkeypatch.setattr(
        sweep_v1.graph_v1,
        "compare_loan_geography_sparse_full_graphs_v1",
        compare,
    )
    monkeypatch.setattr(
        sweep_v1.graph_v1,
        "build_loan_geography_scoped_graphs_v1",
        sparse_batch,
    )
    monkeypatch.setattr(
        sweep_v1.graph_v1,
        "validate_loan_geography_scoped_graphs_replay_v1",
        lambda value, _receipt, _snapshots: value,
    )


def _equivalence(graph: dict, disposition: str, *, pages: int, lines: int) -> dict:
    fingerprint = copy.deepcopy(graph["region_fingerprint"])
    return {
        "disposition": disposition,
        "sparse_graph_result_id": graph["result_id"],
        "sparse_region_fingerprint": fingerprint,
        "status": "EXACT_SPARSE_TO_WHOLE_DOCUMENT_STRUCTURE_EQUIVALENCE",
        "whole_document_graph_result_id": f"whole-{graph['ordinal']}",
        "whole_document_line_count": lines,
        "whole_document_page_count": pages,
        "whole_document_region_fingerprint": copy.deepcopy(fingerprint),
    }


def _numeric(
    period_count: int,
    dash_count: int,
    control_modes: list[str] | None = None,
) -> dict:
    if control_modes is None:
        control_modes = ["LOCAL_LABELED_TOTAL"] * period_count
    assert len(control_modes) == period_count
    periods = [
        {
            "lane_index": lane,
            "period_end": f"{2025 - lane}-12-31",
            "period_role": "CURRENT" if lane == 0 else "COMPARATIVE",
        }
        for lane in range(period_count)
    ]
    foreign_dash_lanes = set(range(dash_count))

    def row(role: str, report_norm_id: int) -> tuple[dict, dict]:
        cells = []
        value_cells = []
        for lane, _period in enumerate(periods):
            dash = role == "FOREIGN_TOTAL" and lane in foreign_dash_lanes
            cell = {
                "lane_index": lane,
                "selected_value": 0 if dash else 100 + lane,
                "selection_mode": (
                    "TYPED_VISIBLE_DASH_PIXEL_EVIDENCE_ZERO" if dash else "READER_CONSENSUS"
                ),
            }
            cells.append(cell)
            value_cells.append({"lane_index": lane, "value": cell["selected_value"]})
        return (
            {"cells": cells, "label_surface": role, "role": role},
            {
                "report_norm_id": report_norm_id,
                "role": role,
                "value_cells": value_cells,
            },
        )

    domestic, domestic_mapping = row("DOMESTIC_TOTAL", 5752)
    foreign, foreign_mapping = row("FOREIGN_TOTAL", 765)
    return {
        "accounting_checks": [
            {"status": "EXACT_OBSERVED_EQUATION"} for _lane in range(period_count)
        ],
        "mapped_rows": [domestic, foreign],
        "metrics": {
            "accounting_backsolved_or_invented_value_count": 0,
            "gemma_numeric_authority_count": 0,
            "ppocrv6_vietocr_numeric_disagreement_count": 0,
            "source_control_money_cell_count": period_count,
            "unresolved_observed_cell_count": 0,
            "vetoed_equation_count": 0,
            "visible_dash_zero_cell_count": dash_count,
        },
        "period_axis": periods,
        "printed_customer_loan_total": {
            "control_evidence": [
                {"lane_index": lane, "resolution_mode": mode}
                for lane, mode in enumerate(control_modes)
            ]
        },
        "synthetic_mappings": [domestic_mapping, foreign_mapping],
        "unit_context": {"resolution_mode": "LOCAL_EXACT_UNIT"},
    }


def _trial(
    packet: dict,
    disposition: str,
    receipt_id: str,
    *,
    periods: int = 0,
    dashes: int = 0,
) -> dict:
    continuation_mode = (
        "ADJACENT_REPEATED_FULL_SEGMENTS_PERIOD_COMPLEMENT"
        if disposition == "EXACT_CUSTOMER_LOAN_GEOGRAPHY" and packet["bank_provenance"] == "VIB"
        else "SINGLE_PAGE_MULTI_PERIOD_COMPLETE_SEGMENTS"
        if disposition == "EXACT_CUSTOMER_LOAN_GEOGRAPHY" and periods > 1
        else "SINGLE_PAGE_COMPLETE_SEGMENTS"
        if disposition == "EXACT_CUSTOMER_LOAN_GEOGRAPHY"
        else None
    )
    graph = _graph(
        packet["document_ordinal"],
        disposition,
        packet=packet,
        receipt_id=receipt_id,
        continuation_mode=continuation_mode,
    )
    common = {
        "customer_loan_total_control_request_set": None,
        "customer_loan_total_controls": [],
        "document": packet,
        "document_context_evidence": None,
        "gemma_challenger_refs": [],
        "pixel_dash_evidence": None,
        "pixel_dash_hole_manifest": None,
        "pixel_graph_projection": None,
        "pixel_render_ids": [],
        "region_coverage": _coverage(packet["document_ordinal"], receipt_id),
        "sparse_graph": sweep_v1._sparse_graph_binding_from_document(graph),
        "structural_disposition": disposition,
        "structural_equivalence": _equivalence(
            graph,
            disposition,
            pages=packet["page_count"],
            lines=packet["line_count"],
        ),
        "unresolved_reasons": [],
    }
    if disposition == "EXACT_CUSTOMER_LOAN_GEOGRAPHY":
        control_modes = (
            ["LOCAL_LABELED_TOTAL"] * periods
            if packet["bank_provenance"] == "VIB"
            else ["UPSTREAM_AUTHENTICATED_CUSTOMER_LOAN_TOTAL_CONTROL"] * periods
            if packet["bank_provenance"] == "MBB" and periods == 1
            else ["LOCAL_UNLABELED_TOTAL_ROW"] * periods
        )
        numeric = _numeric(periods, dashes, control_modes)
        lane_requests = [
            {
                "classification": (
                    "STRUCTURALLY_ABSENT"
                    if mode == "UPSTREAM_AUTHENTICATED_CUSTOMER_LOAN_TOTAL_CONTROL"
                    else mode
                ),
                "control_request_id": (
                    f"request-{packet['document_ordinal']}-{lane}"
                    if mode == "UPSTREAM_AUTHENTICATED_CUSTOMER_LOAN_TOTAL_CONTROL"
                    else None
                ),
                "lane_index": lane,
                "period_end": numeric["period_axis"][lane]["period_end"],
            }
            for lane, mode in enumerate(control_modes)
        ]
        controls = [
            {
                "requested_period_end": "31/12/2025",
                "result_id": f"control-{packet['document_ordinal']}-{lane}",
            }
            for lane, mode in enumerate(control_modes)
            if mode == "UPSTREAM_AUTHENTICATED_CUSTOMER_LOAN_TOTAL_CONTROL"
        ]
        return {
            **common,
            "absence_evidence": None,
            "customer_loan_total_control_request_set": {
                "lane_requests": lane_requests,
                "request_set_id": f"request-set-{packet['document_ordinal']}",
            },
            "customer_loan_total_controls": controls,
            "disposition": disposition,
            "mapped_children": numeric.pop("synthetic_mappings"),
            "numeric_evidence": numeric,
            "numeric_input": {"synthetic": True},
            "presentation_mode": (
                "REPEATED_FULL_SEGMENT_ONE_PERIOD_PER_PAGE"
                if packet["bank_provenance"] == "VIB"
                else "SINGLE_PAGE_GEOGRAPHY_ROWS_ACCOUNTING_COLUMNS"
            ),
            "status": "VERIFIED_BY_CODEX",
        }
    if disposition == "BROAD_POPULATION_BOUNDED_ABSENCE":
        scope = (
            "BROAD_MIXED_LOAN_POPULATION"
            if packet["bank_provenance"] == "VPB"
            else "BROAD_TOTAL_LOANS"
        )
        absence = {
            "bounded_absence_ids": [f"absence-{packet['document_ordinal']}"],
            "kind": "VISIBLE_BROAD_OR_MIXED_GEOGRAPHY_POPULATION",
            "population_scopes": [scope],
            "terminal_reason": "VISIBLE_GEOGRAPHY_POPULATION_IS_BROADER_THAN_CUSTOMER_LOANS",
        }
    else:
        absence = {
            "bounded_absence_ids": [],
            "kind": "NO_CUSTOMER_LOAN_GEOGRAPHY_STRUCTURE_OBSERVED",
            "population_scopes": [],
            "terminal_reason": "NO_EXACT_OR_BROAD_CUSTOMER_LOAN_GEOGRAPHY_CANDIDATE",
        }
    return {
        **common,
        "absence_evidence": absence,
        "disposition": disposition,
        "mapped_children": [],
        "numeric_evidence": None,
        "numeric_input": None,
        "presentation_mode": None,
        "status": "VERIFIED_BOUNDED_ABSENCE",
    }


def _terminal_fixture(monkeypatch: pytest.MonkeyPatch) -> tuple[list[dict], dict]:
    receipt_id = "fffrrv1:receipt:synthetic"
    monkeypatch.setattr(sweep_v1, "_validate_inputs", lambda value: copy.deepcopy(value))
    monkeypatch.setattr(
        sweep_v1,
        "_validate_trial",
        lambda value, **_kwargs: copy.deepcopy(value),
    )
    banks = [
        bank
        for bank, count in sweep_v1._TARGET_BANK_DOCUMENT_COUNTS.items()
        for _item in range(count)
    ]
    exact_remaining = copy.deepcopy(sweep_v1._TARGET_BANK_EXACT_COUNTS)
    broad_remaining = copy.deepcopy(sweep_v1._TARGET_BANK_BROAD_COUNTS)
    trials = []
    mbb_exact = 0
    for ordinal, bank in enumerate(banks, 1):
        pages = 64 if ordinal <= 127 else 63
        lines = 4766 if ordinal <= 124 else 4765
        packet = _packet(ordinal, bank, pages=pages, lines=lines)
        if exact_remaining[bank]:
            exact_remaining[bank] -= 1
            if bank == "ACB":
                periods, dashes = 2, 2
            elif bank == "MBB":
                periods, dashes = (2 if mbb_exact < 6 else 1), 0
                mbb_exact += 1
            else:
                periods, dashes = 2, 2
            disposition = "EXACT_CUSTOMER_LOAN_GEOGRAPHY"
            trials.append(_trial(packet, disposition, receipt_id, periods=periods, dashes=dashes))
        elif broad_remaining[bank]:
            broad_remaining[bank] -= 1
            trials.append(_trial(packet, "BROAD_POPULATION_BOUNDED_ABSENCE", receipt_id))
        else:
            trials.append(_trial(packet, "NOT_OBSERVED", receipt_id))
    for index, trial in enumerate(trials):
        trial["region_coverage"]["selected_page_count"] = 15 if index < 35 else 14
        trial["region_coverage"]["selected_line_count"] = 1095 if index < 79 else 1094
    inputs = {
        "bounded_schema_projection": {"projection_id": "synthetic"},
        "document_evidence_store": {
            "metrics": {"document_count": 140, "line_count": 667_224, "page_count": 8_947}
        },
        "implementation_refs": {"builder": {}},
        "region_query_spec": {"family_id": "LOAN_GEOGRAPHY"},
        "region_retrieval_receipt": {
            "documents": [
                {
                    "coverage_status": "PROVEN_COMPLETE_FOR_DECLARED_SPEC",
                    "document_ordinal": ordinal,
                    "outcome_id": f"outcome-{ordinal}",
                }
                for ordinal in range(1, 141)
            ],
            "receipt_id": receipt_id,
        },
        "schema_source_refs": {"schema": {}},
        "tracked_git_head": "a" * 40,
    }
    return trials, inputs


def test_terminal_contract_closes_exact_family11_denominators(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trials, inputs = _terminal_fixture(monkeypatch)
    result = sweep_v1._terminal_material(trials, inputs)
    metrics = result["metrics"]
    assert result["state"] == "COMPLETE"
    assert metrics["exact_customer_loan_geography_trial_count"] == 38
    assert metrics["broad_bounded_absence_trial_count"] == 78
    assert metrics["not_observed_trial_count"] == 24
    assert metrics["mapped_record_count"] == 76
    assert metrics["mapped_money_cell_count"] == 130
    assert metrics["observed_numeric_mapped_cell_count"] == 88
    assert metrics["visible_dash_zero_cell_count"] == 42
    assert metrics["exact_accounting_equation_count"] == 65
    assert metrics["printed_customer_loan_total_control_source_mode_counts"] == {
        "LOCAL_LABELED_TOTAL": 36,
        "LOCAL_UNLABELED_TOTAL_ROW": 18,
        "UPSTREAM_AUTHENTICATED_CUSTOMER_LOAN_TOTAL_CONTROL": 11,
    }
    assert metrics["customer_loan_total_control_request_set_count"] == 38
    assert metrics["customer_loan_total_control_request_count"] == 11
    assert metrics["customer_loan_total_control_public_replay_count"] == 11
    assert metrics["upstream_customer_loan_total_control_lane_count"] == 11
    assert metrics["upstream_customer_loan_total_control_document_count"] == 11
    assert metrics["local_upstream_total_control_conflict_count"] == 0
    assert metrics["absence_numeric_pixel_or_total_control_hydration_count"] == 0
    assert metrics["continuation_mode_trial_counts"] == {
        "ADJACENT_REPEATED_FULL_SEGMENTS_PERIOD_COMPLEMENT": 18,
        "SINGLE_PAGE_MULTI_PERIOD_COMPLETE_SEGMENTS": 9,
        "SINGLE_PAGE_COMPLETE_SEGMENTS": 11,
    }
    assert metrics["row_layout_trial_count"] == 20
    assert metrics["column_layout_trial_count"] == 18
    assert metrics["repeated_full_segment_trial_count"] == 18
    assert metrics["direct_whole_document_page_count"] == 8_947
    assert metrics["direct_whole_document_line_count"] == 667_224
    assert metrics["sparse_hydrated_page_count"] == 1_995
    assert metrics["sparse_hydrated_line_count"] == 153_239
    assert metrics["sparse_page_reduction_ppm"] > 0
    assert metrics["sparse_line_reduction_ppm"] > 0


def test_terminal_contract_rejects_singular_continuation_enum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trials, inputs = _terminal_fixture(monkeypatch)
    exact = next(item for item in trials if item["disposition"] == "EXACT_CUSTOMER_LOAN_GEOGRAPHY")
    exact["sparse_graph"]["region_fingerprint"]["regions"][0]["continuation"]["mode"] = (
        "ADJACENT_REPEATED_FULL_SEGMENT_PERIOD_COMPLEMENT"
    )
    with pytest.raises(
        sweep_v1.FamilyFirstLoanGeography140FilingSchemaSweepV1Error,
        match="continuation mode counts drifted",
    ):
        sweep_v1._terminal_material(trials, inputs)


def test_sparse_whole_document_equivalence_rejects_fingerprint_tamper() -> None:
    value = _equivalence(_graph(1), "NOT_OBSERVED", pages=2, lines=3)
    value["whole_document_region_fingerprint"]["semantic_region"] = 2
    with pytest.raises(
        sweep_v1.FamilyFirstLoanGeography140FilingSchemaSweepV1Error,
        match="equivalence",
    ):
        sweep_v1._equivalence(value, disposition="NOT_OBSERVED")


def test_retrieval_coverage_rejects_bool_as_page_count() -> None:
    value = _coverage(1, "receipt")
    value["selected_page_count"] = True
    with pytest.raises(
        sweep_v1.FamilyFirstLoanGeography140FilingSchemaSweepV1Error,
        match="exact integer",
    ):
        sweep_v1._coverage(value, receipt_id="receipt", outcome_id="outcome-1")


def test_selected_page_batch_hydration_preserves_axis_and_bounds_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def read(_capability: object, *, document_page_selections: tuple) -> tuple:
        calls.append(document_page_selections)
        return tuple(
            {"document_packet": {"document_ordinal": ordinal}}
            for ordinal, _pages in document_page_selections
        )

    monkeypatch.setattr(
        sweep_v1.store_v1,
        "read_authenticated_family_first_documents_selected_pages_v1",
        read,
    )
    selections = tuple((ordinal, (1, 2)) for ordinal in range(1, 8))
    result = sweep_v1._read_selected_pages_in_batches(object(), selections, batch_size=3)
    assert [item["document_packet"]["document_ordinal"] for item in result] == list(range(1, 8))
    assert [len(item) for item in calls] == [3, 3, 1]


def test_parent_cheap_total_control_gate_binds_every_locator_to_authenticated_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _packet(1, "ACB", pages=1, lines=1)
    dimension = {
        "physical_page": 1,
        "pixel_height": 200,
        "pixel_width": 300,
        "render_sha256": "4" * 64,
        "render_size_bytes": 10,
    }
    line = {
        "bbox": [10, 20, 100, 40],
        "crop_ref": {"path": "crop.png", "sha256": "5" * 64, "size_bytes": 5},
        "line_ordinal": 0,
        "numeric_recognition": {"raw_prediction": "120", "reader_score": 0.99},
        "sample_id": "sample-1",
        "vietocr_text": "120",
    }
    snapshot = {
        "document_packet": packet,
        "joined_pages": [{"lines": [line], "page_sequence": 1, "page_width": 300}],
        "manifest_id": "ffdesv1:manifest:" + "6" * 64,
        "query_selection_id": "ffoqcv1:selection:" + "7" * 64,
        "selected_page_dimensions": [dimension],
        "snapshot_id": "ffdesv1:selected:" + "8" * 64,
    }
    locator = {
        "bbox": line["bbox"],
        "crop_ref": line["crop_ref"],
        "page_render": dimension,
        "page_sequence": 1,
        "ppocrv6_reader_score": 0.99,
        "ppocrv6_surface": "120",
        "sample_id": "sample-1",
        "source_line_index": 0,
        "vietocr_transformer_surface": "120",
    }
    control = {
        "document_binding": {
            "document_evidence_root_sha256": packet["document_evidence_root_sha256"],
            "document_id": packet["document_id"],
            "document_ordinal": 1,
            "document_packet_id": packet["packet_id"],
            "line_count": 1,
            "manifest_id": snapshot["manifest_id"],
            "page_count": 1,
            "query_selection_id": snapshot["query_selection_id"],
            "snapshot_id": snapshot["snapshot_id"],
            "source_pdf_ref": packet["source_pdf_ref"],
        },
        "owner_evidence": {"evidence": [locator]},
        "period_lane": {"evidence": [locator]},
        "requested_period_end": "31/12/2025",
        "result_id": "cltcv1:result:" + "9" * 64,
        "total_control": {"source": locator},
        "unit_evidence": {"source": locator},
    }
    monkeypatch.setattr(
        sweep_v1.total_control_v1,
        "validate_customer_loan_total_control_v1",
        lambda value: copy.deepcopy(value),
    )

    assert sweep_v1._customer_loan_total_controls(
        [control], packet=packet, source_snapshot=snapshot
    ) == [control]

    tampered = copy.deepcopy(control)
    tampered["total_control"]["source"]["crop_ref"]["sha256"] = "a" * 64
    with pytest.raises(
        sweep_v1.FamilyFirstLoanGeography140FilingSchemaSweepV1Error,
        match="authenticated locator binding drifted",
    ):
        sweep_v1._customer_loan_total_controls([tampered], packet=packet, source_snapshot=snapshot)


def test_direct_oracle_checks_actual_zero_line_page_and_line_denominators(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sweep_v1, "_TARGET_DOCUMENT_COUNT", 1)
    packet = _packet(1, "ACB", pages=2, lines=1)
    receipt = {
        "documents": [{"outcome_id": "outcome-1"}],
        "receipt_id": "receipt",
    }
    snapshot = {
        "document_packet": packet,
        "joined_pages": [
            {"lines": [{"line": 1}], "page_sequence": 1},
            {"lines": [], "page_sequence": 2},
        ],
        "snapshot_id": "snapshot-1",
    }
    sparse = {
        "disposition": "NOT_OBSERVED",
        "document_ordinal": 1,
        "ordinal": 1,
        "region_fingerprint": {
            "disposition": "NOT_OBSERVED",
            "partial": False,
        },
        "result_id": "lgstv1:document:" + "1" * 64,
    }
    monkeypatch.setattr(
        sweep_v1,
        "_selected_page_batches",
        lambda *_args, **_kwargs: iter(((snapshot,),)),
    )
    monkeypatch.setattr(
        sweep_v1.graph_v1,
        "_prepare_loan_geography_receipt_v1",
        lambda value: value,
    )
    monkeypatch.setattr(
        sweep_v1.graph_v1,
        "_prepare_loan_geography_snapshot_v1",
        lambda value: value,
    )
    monkeypatch.setattr(
        sweep_v1.graph_v1,
        "build_loan_geography_whole_document_scoped_graph_v1",
        lambda *_args: _bound_graph(packet, snapshot_id="snapshot-1"),
    )
    monkeypatch.setattr(
        sweep_v1.graph_v1,
        "build_loan_geography_document_context_v1",
        lambda *_args: _context(packet, snapshot_id="snapshot-1"),
    )
    monkeypatch.setattr(
        sweep_v1.graph_v1,
        "validate_loan_geography_whole_document_scoped_graph_replay_v1",
        lambda value, _receipt, _snapshot: value,
    )
    monkeypatch.setattr(
        sweep_v1.graph_v1,
        "validate_loan_geography_document_context_replay_v1",
        lambda value, _snapshot: value,
    )
    monkeypatch.setattr(
        sweep_v1.graph_v1,
        "compare_loan_geography_sparse_full_graphs_v1",
        lambda sparse_document, _whole_document, **_kwargs: _equivalence(
            sparse_document,
            sparse_document["disposition"],
            pages=2,
            lines=1,
        ),
    )
    equivalences, contexts, request_sets, controls, numeric_inputs = (
        sweep_v1._whole_document_equivalences(
            object(),
            receipt,
            (sparse,),
            (packet,),
            batch_size=1,
        )
    )
    assert equivalences[0]["whole_document_page_count"] == 2
    assert equivalences[0]["whole_document_line_count"] == 1
    assert contexts == (None,)
    assert request_sets == (None,)
    assert controls == ([],)
    assert numeric_inputs == (None,)

    bad = copy.deepcopy(snapshot)
    bad["joined_pages"][1]["lines"] = [{"unexpected": True}]
    monkeypatch.setattr(
        sweep_v1,
        "_selected_page_batches",
        lambda *_args, **_kwargs: iter(((bad,),)),
    )
    with pytest.raises(
        sweep_v1.FamilyFirstLoanGeography140FilingSchemaSweepV1Error,
        match="physical page/line denominator",
    ):
        sweep_v1._whole_document_equivalences(
            object(),
            receipt,
            (sparse,),
            (packet,),
            batch_size=1,
        )


class _ReverseProcessPool:
    max_workers_seen: int | None = None

    def __init__(
        self,
        *,
        max_workers: int,
        initializer: object,
        initargs: tuple,
    ) -> None:
        type(self).max_workers_seen = max_workers
        self.initializer = initializer
        self.initargs = initargs

    def __enter__(self) -> _ReverseProcessPool:
        self.initializer(*self.initargs)
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def map(self, function: object, work: tuple, *, chunksize: int) -> list[dict]:
        assert chunksize == 1
        return list(reversed([function(item) for item in work]))


def test_direct_pool_restores_out_of_order_results_and_matches_jobs_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt, snapshots, sparse = _worker_inputs(disposition="EXACT_CUSTOMER_LOAN_GEOGRAPHY")
    packets = tuple(snapshot["document_packet"] for snapshot in snapshots)
    context_replay_calls: list[str] = []
    request_replay_calls: list[str] = []
    whole_replay_calls: list[str] = []
    _install_worker_graph_stubs(
        monkeypatch,
        context_replay_calls=context_replay_calls,
        request_replay_calls=request_replay_calls,
        whole_replay_calls=whole_replay_calls,
        disposition="EXACT_CUSTOMER_LOAN_GEOGRAPHY",
    )
    monkeypatch.setattr(sweep_v1, "_TARGET_DOCUMENT_COUNT", 2)
    monkeypatch.setattr(
        sweep_v1,
        "_selected_page_batches",
        lambda *_args, **_kwargs: iter((snapshots,)),
    )
    sequential = sweep_v1._whole_document_equivalences(
        object(),
        receipt,
        sparse,
        packets,
        batch_size=2,
        jobs=1,
    )
    monkeypatch.setattr(sweep_v1, "ProcessPoolExecutor", _ReverseProcessPool)
    parallel = sweep_v1._whole_document_equivalences(
        object(),
        receipt,
        sparse,
        packets,
        batch_size=2,
        jobs=2,
    )
    assert parallel == sequential
    assert _ReverseProcessPool.max_workers_seen == 2
    assert [item["document_packet_id"] for item in parallel[1]] == [
        packet["packet_id"] for packet in packets
    ]
    # Each worker build performs the public replay once; the parent does not rebuild it.
    assert context_replay_calls == [
        "snapshot-1",
        "snapshot-2",
        "snapshot-1",
        "snapshot-2",
    ]
    assert whole_replay_calls == [
        "snapshot-1",
        "snapshot-2",
        "snapshot-1",
        "snapshot-2",
    ]
    assert request_replay_calls == [
        "snapshot-1",
        "snapshot-2",
        "snapshot-1",
        "snapshot-2",
    ]
    assert all(item is not None for item in parallel[2])
    assert parallel[3] == ([], [])
    assert all(item is not None for item in parallel[4])


def test_direct_worker_rejects_self_rehashed_source_binding_tamper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt, snapshots, sparse = _worker_inputs(
        1,
        disposition="EXACT_CUSTOMER_LOAN_GEOGRAPHY",
    )
    _install_worker_graph_stubs(
        monkeypatch,
        disposition="EXACT_CUSTOMER_LOAN_GEOGRAPHY",
    )
    record = sweep_v1._direct_full_worker_material(receipt, 0, snapshots[0])
    record["snapshot_id"] = "tampered-snapshot"
    material = copy.deepcopy(record)
    material.pop("worker_output_id")
    record["worker_output_id"] = "lg140v1:direct-full-worker:" + canonical_json_sha256_v1(material)
    with pytest.raises(
        sweep_v1.FamilyFirstLoanGeography140FilingSchemaSweepV1Error,
        match="source binding",
    ):
        sweep_v1._validate_direct_full_worker_batch(
            receipt,
            {1: sparse[0]},
            snapshots,
            (record,),
            source_start=0,
        )


def test_upstream_control_replays_in_worker_and_parent_projects_before_snapshot_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt, snapshots, sparse = _worker_inputs(
        1,
        disposition="EXACT_CUSTOMER_LOAN_GEOGRAPHY",
    )
    calls: list[str] = []
    _install_worker_graph_stubs(
        monkeypatch,
        control_replay_calls=calls,
        disposition="EXACT_CUSTOMER_LOAN_GEOGRAPHY",
        upstream_control=True,
    )
    monkeypatch.setattr(sweep_v1, "_TARGET_DOCUMENT_COUNT", 1)
    monkeypatch.setattr(
        sweep_v1,
        "_selected_page_batches",
        lambda *_args, **_kwargs: iter((snapshots,)),
    )

    result = sweep_v1._whole_document_equivalences(
        object(),
        receipt,
        sparse,
        (snapshots[0]["document_packet"],),
        batch_size=1,
        jobs=1,
    )

    assert calls == ["snapshot-1", "snapshot-1"]
    assert result[2][0]["lane_requests"][0]["control_request_id"] == "control-request-1"
    assert [item["result_id"] for item in result[3][0]] == ["control-1"]
    assert (
        result[4][0]["printed_customer_loan_total"]["control_evidence"][0]["resolution_mode"]
        == "UPSTREAM_AUTHENTICATED_CUSTOMER_LOAN_TOTAL_CONTROL"
    )


def test_parent_rejects_rehashed_worker_control_locator_tamper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt, snapshots, sparse = _worker_inputs(
        1,
        disposition="EXACT_CUSTOMER_LOAN_GEOGRAPHY",
    )
    _install_worker_graph_stubs(
        monkeypatch,
        disposition="EXACT_CUSTOMER_LOAN_GEOGRAPHY",
        upstream_control=True,
    )
    record = sweep_v1._direct_full_worker_material(receipt, 0, snapshots[0])
    record["customer_loan_total_controls"][0]["total_control"]["source"]["crop_ref"]["sha256"] = (
        "a" * 64
    )
    material = copy.deepcopy(record)
    material.pop("worker_output_id")
    record["worker_output_id"] = "lg140v1:direct-full-worker:" + canonical_json_sha256_v1(material)

    with pytest.raises(
        sweep_v1.FamilyFirstLoanGeography140FilingSchemaSweepV1Error,
        match="authenticated locator binding drifted",
    ):
        sweep_v1._validate_direct_full_worker_batch(
            receipt,
            {1: sparse[0]},
            snapshots,
            (record,),
            source_start=0,
        )


def test_absence_path_never_builds_or_replays_total_control(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt, snapshots, sparse = _worker_inputs(1, disposition="NOT_OBSERVED")
    _install_worker_graph_stubs(monkeypatch, disposition="NOT_OBSERVED")
    monkeypatch.setattr(sweep_v1, "_TARGET_DOCUMENT_COUNT", 1)
    monkeypatch.setattr(
        sweep_v1,
        "_selected_page_batches",
        lambda *_args, **_kwargs: iter((snapshots,)),
    )
    monkeypatch.setattr(
        sweep_v1.total_control_v1,
        "build_customer_loan_total_control_v1",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("forbidden hydration")),
    )

    result = sweep_v1._whole_document_equivalences(
        object(),
        receipt,
        sparse,
        (snapshots[0]["document_packet"],),
        batch_size=1,
        jobs=1,
    )

    assert result[1:] == ((None,), (None,), ([],), (None,))


def test_direct_pool_surfaces_worker_failure_deterministically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt, snapshots, sparse = _worker_inputs(1)
    packet = snapshots[0]["document_packet"]
    monkeypatch.setattr(sweep_v1, "_TARGET_DOCUMENT_COUNT", 1)
    monkeypatch.setattr(
        sweep_v1,
        "_selected_page_batches",
        lambda *_args, **_kwargs: iter((snapshots,)),
    )
    monkeypatch.setattr(
        sweep_v1.graph_v1,
        "_prepare_loan_geography_receipt_v1",
        lambda value: value,
    )

    class FailingProcessPool(_ReverseProcessPool):
        def map(self, _function: object, _work: tuple, *, chunksize: int) -> list[dict]:
            assert chunksize == 1
            raise RuntimeError("synthetic worker failure")

    monkeypatch.setattr(sweep_v1, "ProcessPoolExecutor", FailingProcessPool)
    with pytest.raises(
        sweep_v1.FamilyFirstLoanGeography140FilingSchemaSweepV1Error,
        match="worker execution failed",
    ):
        sweep_v1._whole_document_equivalences(
            object(),
            receipt,
            sparse,
            (packet,),
            batch_size=1,
            jobs=2,
        )


def test_sparse_pool_restores_out_of_order_results_and_matches_jobs_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt, snapshots, _sparse = _worker_inputs()
    _install_worker_graph_stubs(monkeypatch)
    monkeypatch.setattr(sweep_v1, "_TARGET_DOCUMENT_COUNT", 2)
    monkeypatch.setattr(
        sweep_v1,
        "_selected_page_batches",
        lambda *_args, **_kwargs: iter((snapshots,)),
    )
    sequential = sweep_v1._sparse_graph_path(
        object(),
        receipt,
        batch_size=2,
        jobs=1,
    )
    monkeypatch.setattr(sweep_v1, "ProcessPoolExecutor", _ReverseProcessPool)
    parallel = sweep_v1._sparse_graph_path(
        object(),
        receipt,
        batch_size=2,
        jobs=2,
    )
    assert parallel == sequential
    assert [item["document_ordinal"] for item in parallel[0]] == [1, 2]
    assert [item["outcome_id"] for item in parallel[2]] == ["outcome-1", "outcome-2"]


def test_jobs_one_prepares_receipt_once_per_sparse_or_direct_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt, snapshots, sparse = _worker_inputs()
    packets = tuple(snapshot["document_packet"] for snapshot in snapshots)
    _install_worker_graph_stubs(monkeypatch)
    calls: list[str] = []
    snapshot_calls: list[str] = []

    def prepare(value: dict) -> dict:
        calls.append(value["receipt_id"])
        return value

    monkeypatch.setattr(sweep_v1.graph_v1, "_prepare_loan_geography_receipt_v1", prepare)
    monkeypatch.setattr(
        sweep_v1.graph_v1,
        "_prepare_loan_geography_snapshot_v1",
        lambda value: snapshot_calls.append(value["snapshot_id"]) or value,
    )
    monkeypatch.setattr(sweep_v1, "_TARGET_DOCUMENT_COUNT", 2)
    monkeypatch.setattr(
        sweep_v1,
        "_selected_page_batches",
        lambda *_args, **_kwargs: iter((snapshots,)),
    )

    sweep_v1._sparse_graph_path(object(), receipt, batch_size=2, jobs=1)
    assert calls == ["receipt"]
    assert snapshot_calls == ["snapshot-1", "snapshot-2"]
    sweep_v1._whole_document_equivalences(
        object(),
        receipt,
        sparse,
        packets,
        batch_size=2,
        jobs=1,
    )
    assert calls == ["receipt", "receipt"]
    assert snapshot_calls == ["snapshot-1", "snapshot-2", "snapshot-1", "snapshot-2"]


def test_pool_prepares_once_in_parent_and_once_in_initialized_worker_not_per_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt, snapshots, _sparse = _worker_inputs()
    _install_worker_graph_stubs(monkeypatch)
    calls: list[str] = []
    snapshot_calls: list[str] = []

    def prepare(value: dict) -> dict:
        calls.append(value["receipt_id"])
        return value

    monkeypatch.setattr(sweep_v1.graph_v1, "_prepare_loan_geography_receipt_v1", prepare)
    monkeypatch.setattr(
        sweep_v1.graph_v1,
        "_prepare_loan_geography_snapshot_v1",
        lambda value: snapshot_calls.append(value["snapshot_id"]) or value,
    )
    monkeypatch.setattr(sweep_v1, "_TARGET_DOCUMENT_COUNT", 2)
    monkeypatch.setattr(sweep_v1, "ProcessPoolExecutor", _ReverseProcessPool)
    monkeypatch.setattr(
        sweep_v1,
        "_selected_page_batches",
        lambda *_args, **_kwargs: iter((snapshots,)),
    )

    sweep_v1._sparse_graph_path(object(), receipt, batch_size=2, jobs=2)

    # The fake pool models one initialized worker.  Its two tasks reuse the
    # prepared object; only the parent and initializer validate raw receipt.
    assert calls == ["receipt", "receipt"]
    assert snapshot_calls == ["snapshot-1", "snapshot-2"]


def test_worker_parent_order_gates_reject_boolean_source_indices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt, snapshots, sparse = _worker_inputs(1)
    _install_worker_graph_stubs(monkeypatch)

    sparse_record = sweep_v1._sparse_graph_worker_material(receipt, 0, snapshots[0])
    sparse_record["source_index"] = False
    sparse_material = copy.deepcopy(sparse_record)
    sparse_material.pop("worker_output_id")
    sparse_record["worker_output_id"] = "lg140v1:sparse-worker:" + canonical_json_sha256_v1(
        sparse_material
    )
    with pytest.raises(
        sweep_v1.FamilyFirstLoanGeography140FilingSchemaSweepV1Error,
        match="sparse worker source order binding drifted",
    ):
        sweep_v1._validate_sparse_graph_worker_batch(
            receipt,
            snapshots,
            (sparse_record,),
            source_start=0,
        )

    direct_record = sweep_v1._direct_full_worker_material(receipt, 0, snapshots[0])
    direct_record["source_index"] = False
    direct_material = copy.deepcopy(direct_record)
    direct_material.pop("worker_output_id")
    direct_record["worker_output_id"] = "lg140v1:direct-full-worker:" + canonical_json_sha256_v1(
        direct_material
    )
    with pytest.raises(
        sweep_v1.FamilyFirstLoanGeography140FilingSchemaSweepV1Error,
        match="direct-full worker source order binding drifted",
    ):
        sweep_v1._validate_direct_full_worker_batch(
            receipt,
            {1: sparse[0]},
            snapshots,
            (direct_record,),
            source_start=0,
        )


@pytest.mark.parametrize("keyword", ("sparse_jobs", "direct_full_jobs"))
def test_parallel_job_counts_reject_bool(
    tmp_path: Path,
    keyword: str,
) -> None:
    with pytest.raises(
        sweep_v1.FamilyFirstLoanGeography140FilingSchemaSweepV1Error,
        match="positive exact integers",
    ):
        sweep_v1.build_authenticated_family_first_loan_geography_140_filing_schema_sweep_v1(
            object(),
            tmp_path,
            **{keyword: True},
        )


def test_frozen_retrieval_contract_pins_final_adapter_query_receipt_and_engine() -> None:
    assert sweep_v1._EXPECTED_REGION_QUERY_SPEC_ID == (
        "fffrrv2:query:aa2700a3a54bf9a6ff79bbd4c51d8b3f1e55c7e2f16688a4f75b190673641cc9"
    )
    assert sweep_v1._EXPECTED_REGION_RECEIPT_ID == (
        "fffrrv2:receipt:4f27e3af157654bb4b5d8442a8b6c008a2d18b8da3646cfb67fcf4bae677198f"
    )
    assert sweep_v1._EXPECTED_REGION_IMPLEMENTATION_REFS[
        "src/bctc_ai/evaluation/loan_geography_scoped_table_adapter_v1.py"
    ] == {
        "path": "src/bctc_ai/evaluation/loan_geography_scoped_table_adapter_v1.py",
        "sha256": "892cd2584429e232767ed840a641460c1c08baa97715e0728129fe2101f9921e",
        "size_bytes": 123_674,
    }
    query = sweep_v1._adapter_region_query_spec(_ROOT)
    implementation_refs = {
        path: sweep_v1._stable_ref(_ROOT, Path(path))
        for path in sweep_v1._EXPECTED_REGION_IMPLEMENTATION_REFS
    }
    receipt = {
        "receipt_id": sweep_v1._EXPECTED_REGION_RECEIPT_ID,
        "source_binding": {
            "engine_ref": implementation_refs[
                "src/bctc_ai/evaluation/family_first_region_retrieval_v1.py"
            ],
            "query_spec_id": sweep_v1._EXPECTED_REGION_QUERY_SPEC_ID,
        },
    }
    sweep_v1._assert_frozen_region_retrieval_contract(
        implementation_refs=implementation_refs,
        query_spec=query,
        receipt=receipt,
    )
    tampered = copy.deepcopy(receipt)
    tampered["receipt_id"] = "fffrrv2:receipt:" + "0" * 64
    with pytest.raises(
        sweep_v1.FamilyFirstLoanGeography140FilingSchemaSweepV1Error,
        match="frozen retrieval",
    ):
        sweep_v1._assert_frozen_region_retrieval_contract(
            implementation_refs=implementation_refs,
            query_spec=query,
            receipt=tampered,
        )


def test_mapping_never_backsolves_a_missing_visible_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    numeric = _numeric(1, 0)
    numeric.pop("synthetic_mappings")
    numeric.update(
        {
            "status": "EXACT_OBSERVED_NUMERIC_RECONCILIATION",
            "unit_context": {},
        }
    )
    for lane, period in enumerate(numeric["period_axis"]):
        period.update(
            {
                "evidence_ref": "period",
                "lane_type": "MONEY",
                "resolution_mode": "LOCAL_EXACT_DATE",
                "source_surface": "31/12/2025",
            }
        )
        period["lane_index"] = lane
    for role_index, row in enumerate(numeric["mapped_rows"]):
        for lane, cell in enumerate(row["cells"]):
            cell.update(
                {
                    "bbox": [1, 1, 2, 2],
                    "cell_id": f"cell-{role_index}-{lane}",
                    "page_sequence": 1,
                    "selected_readers": [],
                    "source_line_index": None,
                    "status": "UNRESOLVED",
                }
            )
    numeric["mapped_rows"][0]["cells"][0]["selected_value"] = None
    schema = {
        "mapped_roles": [
            {
                "canonical_name": "+ Trong nước",
                "parent_report_norm_id": 759,
                "report_norm_id": 5752,
                "role": "DOMESTIC_TOTAL",
            },
            {
                "canonical_name": "+ Nước ngoài",
                "parent_report_norm_id": 759,
                "report_norm_id": 765,
                "role": "FOREIGN_TOTAL",
            },
        ],
        "projection_id": "projection",
    }
    monkeypatch.setattr(
        sweep_v1.numeric_v1,
        "validate_loan_geography_numeric_reconciliation_v1",
        lambda value: value,
    )
    monkeypatch.setattr(
        sweep_v1.schema_v1,
        "validate_loan_geography_bounded_schema_projection_v1",
        lambda value: value,
    )
    with pytest.raises(sweep_v1.LoanGeographyTrialUnresolvedV1Error, match="unresolved"):
        sweep_v1._mapping_rows(numeric, schema)


def test_document_local_numeric_failure_becomes_an_unresolved_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = _packet(1, "ACB", pages=2, lines=3)
    graph = _graph(
        1,
        "EXACT_CUSTOMER_LOAN_GEOGRAPHY",
        packet=packet,
        receipt_id="receipt",
    )
    equivalence = _equivalence(
        graph,
        "EXACT_CUSTOMER_LOAN_GEOGRAPHY",
        pages=2,
        lines=3,
    )
    monkeypatch.setattr(
        sweep_v1,
        "_exact_trial_evidence",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            sweep_v1._unresolved("no observed numeric assignment")
        ),
    )
    trial = sweep_v1._trial_from_graph(
        object(),
        graph,
        packet,
        _context(packet),
        {"synthetic": "request-set"},
        [],
        {"synthetic": "numeric-input"},
        _coverage(1, "receipt"),
        equivalence,
        "receipt",
        {},
    )
    assert trial["status"] == "UNRESOLVED"
    assert trial["disposition"] == "UNRESOLVED"
    assert trial["structural_disposition"] == "EXACT_CUSTOMER_LOAN_GEOGRAPHY"
    assert trial["mapped_children"] == []


def test_bounded_absence_rejects_numeric_or_pixel_hydration() -> None:
    packet = _packet(1, "VCB", pages=2, lines=3)
    trial = _trial(packet, "NOT_OBSERVED", "receipt")
    trial["numeric_input"] = {"forbidden": True}
    with pytest.raises(
        sweep_v1.FamilyFirstLoanGeography140FilingSchemaSweepV1Error,
        match="hydrated numeric, pixel, or total-control",
    ):
        sweep_v1._validate_trial(
            trial,
            expected_ordinal=1,
            receipt_id="receipt",
            outcome_id="outcome-1",
            schema={},
        )


def test_terminal_semantics_reject_self_rehashed_metric_tamper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trials, inputs = _terminal_fixture(monkeypatch)
    result = sweep_v1._terminal_material(trials, inputs)
    tampered = copy.deepcopy(result)
    tampered["metrics"]["visible_dash_zero_cell_count"] = 41
    material = copy.deepcopy(tampered)
    material.pop("sweep_id")
    tampered["sweep_id"] = "lg140v1:sweep:" + canonical_json_sha256_v1(material)
    with pytest.raises(
        sweep_v1.FamilyFirstLoanGeography140FilingSchemaSweepV1Error,
        match="terminal semantics",
    ):
        sweep_v1.validate_authenticated_family_first_loan_geography_140_filing_schema_sweep_v1(
            tampered
        )


def test_exclusive_writer_is_immutable_and_never_overwrites(tmp_path: Path) -> None:
    path = tmp_path / "result.json"
    sweep_v1._write_exclusive(path, b"first\n")
    assert stat_mode(path) == 0o444
    with pytest.raises(
        sweep_v1.FamilyFirstLoanGeography140FilingSchemaSweepV1Error,
        match="already exists",
    ):
        sweep_v1._write_exclusive(path, b"second\n")
    assert path.read_bytes() == b"first\n"


def stat_mode(path: Path) -> int:
    return path.stat().st_mode & 0o777


def test_strict_result_requires_one_canonical_lf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        sweep_v1,
        "validate_authenticated_family_first_loan_geography_140_filing_schema_sweep_v1",
        lambda value: value,
    )
    value = {"format": "synthetic"}
    payload = canonical_json_bytes_v1(value)
    exact = tmp_path / "exact.json"
    sweep_v1._write_exclusive(exact, payload)
    assert sweep_v1._strict_result(exact) == value
    doubled = tmp_path / "double.json"
    sweep_v1._write_exclusive(doubled, payload + b"\n")
    with pytest.raises(
        sweep_v1.FamilyFirstLoanGeography140FilingSchemaSweepV1Error,
        match="exactly one LF",
    ):
        sweep_v1._strict_result(doubled)


def test_strict_result_rejects_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_bytes(b"{}\n")
    link = tmp_path / "result.json"
    os.symlink(target, link)
    with pytest.raises(
        sweep_v1.FamilyFirstLoanGeography140FilingSchemaSweepV1Error,
        match="regular nofollow",
    ):
        sweep_v1._strict_result(link)


def test_strict_result_rejects_a_shared_hardlink_inode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        sweep_v1,
        "validate_authenticated_family_first_loan_geography_140_filing_schema_sweep_v1",
        lambda value: value,
    )
    original = tmp_path / "original.json"
    sweep_v1._write_exclusive(original, canonical_json_bytes_v1({"ok": True}))
    linked = tmp_path / "linked.json"
    os.link(original, linked)
    with pytest.raises(
        sweep_v1.FamilyFirstLoanGeography140FilingSchemaSweepV1Error,
        match="link-count-one",
    ):
        sweep_v1._strict_result(linked)
