from __future__ import annotations

import copy
import importlib.util
import os
import sys
from pathlib import Path

import pytest

from bctc_ai.evaluation import family_first_document_evidence_store_v1 as store_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_family_first_loan_currency_140_filing_schema_sweep_v1.py"
_SPEC = importlib.util.spec_from_file_location("loan_currency_140_sweep_test", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
sweep_v1 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = sweep_v1
_SPEC.loader.exec_module(sweep_v1)


def _packet(
    ordinal: int,
    bank: str,
    *,
    page_count: int = 1,
    line_count: int = 1,
) -> dict:
    material = {
        "assurance": "AUDITED",
        "bank_provenance": bank,
        "document_evidence_root_sha256": f"{ordinal + 1000:064x}",
        "document_id": f"synthetic-{ordinal}",
        "document_ordinal": ordinal,
        "line_count": line_count,
        "page_count": page_count,
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


def _absence(packet: dict, scan_id: str) -> dict:
    return {
        "column_context": None,
        "document": packet,
        "hierarchical_closure": None,
        "mapped_children": [],
        "numeric_evidence": None,
        "numeric_input": None,
        "owner_binding": None,
        "pixel_dash_evidence": None,
        "row_axis": None,
        "source_hydration": None,
        "status": "VERIFIED_BOUNDED_ABSENCE",
        "topology_scan_id": scan_id,
        "unresolved_reasons": [],
    }


def _presence(
    packet: dict,
    scan_id: str,
    *,
    presence_index: int,
    bank: str,
    rescue_classes: tuple[str, ...],
    pair_id: str | None,
) -> dict:
    additional = bank == "HDB"
    direct_count = rescue_classes.count("DIRECT_VISIBLE_HORIZONTAL_DASH")
    paired_count = rescue_classes.count("BOUNDED_CENTERED_HIGH_FILL_HORIZONTAL_MARK_CANDIDATE")
    checks = [
        {"status": "CORROBORATED_EXACT_OBSERVED_EQUATION"} for _ in range(6 if additional else 2)
    ]
    numeric = {
        "accounting_checks": checks,
        "additional_population": {} if additional else None,
        "bounded_dash_pair_evidence_refs": (
            [] if pair_id is None else [{"pair_binding": {"pair_binding_id": pair_id}}]
        ),
        "metrics": {
            "bounded_paired_dash_zero_cell_count": paired_count,
            "direct_visible_dash_zero_cell_count": direct_count,
            "ppocrv6_vietocr_numeric_disagreement_count": (1 if presence_index == 7 else 0),
            "ppocrv6_vietocr_raw_surface_disagreement_count": (
                1 if presence_index in {7, 9} else 0
            ),
            "source_only_additional_money_cell_count": 6 if additional else 0,
            "source_only_additional_row_count": 3 if additional else 0,
            "source_control_money_cell_count": 4 if additional else 2,
            "source_control_row_count": 2 if additional else 1,
        },
    }
    mappings = [
        {"report_norm_id": identifier, "value_cells": [{}, {}]} for identifier in (757, 758)
    ]
    zero_pages = 1 if presence_index < 4 else 0
    rescue_cells = [{"admission_class": admission} for admission in rescue_classes]
    overlay = None if not rescue_cells else {"rescue_cells": rescue_cells}
    return {
        "column_context": {},
        "document": packet,
        "hierarchical_closure": {},
        "mapped_children": mappings,
        "numeric_evidence": numeric,
        "numeric_input": {},
        "owner_binding": {
            "mode": (
                "PRECEDING_SECTION_OWNER" if bank == "ACB" else "POST_BRANCH_VISIBLE_CORE_OWNER"
            )
        },
        "period_mode": (
            "LOCAL_EXACT_DATES"
            if bank == "ACB"
            else "LOCAL_RELATIVE_YEAR_END_ROLES"
            if presence_index < 8
            else "LOCAL_RELATIVE_PERIOD_ROLES"
        ),
        "pixel_dash_evidence": overlay,
        "row_axis": {"topology_region": {"minimal_unique_anchor": {"combination_size": 2}}},
        "source_hydration": {
            "full_joined_axis_line_count": packet["line_count"],
            "full_joined_axis_nonempty_page_count": packet["page_count"] - zero_pages,
            "packet_page_count": packet["page_count"],
            "registered_zero_line_page_count": zero_pages,
            "render_ids": [] if overlay is None else [f"render-{presence_index}"],
            "selected_region_page": 1,
            "snapshot_id": f"snapshot-{presence_index}",
        },
        "status": "VERIFIED_BY_CODEX",
        "topology_scan_id": scan_id,
        "unit_mode": "LOCAL_MILLION_VND",
        "unresolved_reasons": [],
    }


def _terminal_fixture(monkeypatch: pytest.MonkeyPatch) -> tuple[list[dict], dict]:
    monkeypatch.setattr(
        sweep_v1,
        "_validate_presence_trial",
        lambda trial, _schema: copy.deepcopy(trial),
    )
    monkeypatch.setattr(
        sweep_v1.schema_v1,
        "validate_loan_currency_bounded_schema_projection_v1",
        lambda value: copy.deepcopy(value),
    )
    banks = [
        bank for bank, count in sweep_v1._TARGET_BANK_DOCUMENT_COUNTS.items() for _ in range(count)
    ]
    presence_remaining = copy.deepcopy(sweep_v1._TARGET_BANK_PRESENCE_COUNTS)
    presence_specs = iter(
        (
            (),
            (),
            (),
            (),
            (),
            (),
            (
                "DIRECT_VISIBLE_HORIZONTAL_DASH",
                "DIRECT_VISIBLE_HORIZONTAL_DASH",
                "BOUNDED_CENTERED_HIGH_FILL_HORIZONTAL_MARK_CANDIDATE",
            ),
            (
                "DIRECT_VISIBLE_HORIZONTAL_DASH",
                "DIRECT_VISIBLE_HORIZONTAL_DASH",
                "DIRECT_VISIBLE_HORIZONTAL_DASH",
            ),
            ("BOUNDED_CENTERED_HIGH_FILL_HORIZONTAL_MARK_CANDIDATE",),
            ("DIRECT_VISIBLE_HORIZONTAL_DASH",),
        )
    )
    pair_ids = ["lcdashv1:pair:a", "lcdashv1:pair:b"]
    trials = []
    presence_index = 0
    for ordinal, bank in enumerate(banks, 1):
        is_presence = presence_remaining[bank] > 0
        if is_presence:
            presence_remaining[bank] -= 1
            page_count = 84 if presence_index == 9 else 82
            line_count = 6310 if presence_index == 9 else 6302
        else:
            page_count = line_count = 1
        packet = _packet(
            ordinal,
            bank,
            page_count=page_count,
            line_count=line_count,
        )
        scan_id = f"aftv1:scan:{ordinal}"
        if not is_presence:
            trials.append(_absence(packet, scan_id))
            continue
        rescue = next(presence_specs)
        pair_id = pair_ids.pop(0) if any("CANDIDATE" in item for item in rescue) else None
        trials.append(
            _presence(
                packet,
                scan_id,
                presence_index=presence_index,
                bank=bank,
                rescue_classes=rescue,
                pair_id=pair_id,
            )
        )
        presence_index += 1
    inputs = {
        "bounded_dash_peer_binding_ids": ["lcdashv1:pair:a", "lcdashv1:pair:b"],
        "bounded_schema_projection": {"projection_id": "synthetic-schema"},
        "document_evidence_store": {
            "authority": copy.deepcopy(store_v1._AUTHORITY),
            "format_version": store_v1.FORMAT_VERSION,
            "input_indices": {
                "numeric_axis_sha256": "1" * 64,
                "numeric_receipt_id": "numeric-receipt",
                "semantic_index_id": "semantic-index",
            },
            "manifest_id": "ffdesv1:manifest:synthetic",
            "metrics": {
                "document_count": 140,
                "line_count": 667_224,
                "page_count": 8_947,
            },
            "state": "FULL_AUDIT_DOCUMENT_EVIDENCE_ROOTS_SEALED",
        },
        "evaluation_spec_sha256": canonical_json_sha256_v1(
            sweep_v1.graph_v2.LOAN_CURRENCY_EVALUATION_SPEC_V2
        ),
        "hierarchy_spec_sha256": canonical_json_sha256_v1(
            sweep_v1.graph_v2.LOAN_CURRENCY_HIERARCHY_SPEC_V2
        ),
        "implementation_refs": sweep_v1._implementation_refs(_ROOT),
        "positive_document_packet_ids": [
            trial["document"]["packet_id"]
            for trial in trials
            if trial["status"] == "VERIFIED_BY_CODEX"
        ],
        "topology_scan_ids": [trial["topology_scan_id"] for trial in trials],
        "topology_spec_sha256": canonical_json_sha256_v1(
            sweep_v1.graph_v2.LOAN_CURRENCY_TOPOLOGY_SPEC_V2
        ),
    }
    return trials, inputs


def test_preceding_owner_uses_visual_geometry_not_provider_order() -> None:
    row_axis = {
        "rows": [],
        "topology_region": {"parent_match": {"_bbox": [10, 100, 300, 120], "page_sequence": 1}},
    }
    page = {
        "lines": [
            {
                "bbox": [10, 65, 280, 80],
                "line_ordinal": 900,
                "sample_id": "nearest-owner",
                "vietocr_text": "Cho vay khách hàng (tiếp theo)",
            },
            {
                "bbox": [10, 10, 280, 25],
                "line_ordinal": 2,
                "sample_id": "far-owner",
                "vietocr_text": "Cho vay khách hàng",
            },
        ],
        "page_sequence": 1,
    }
    result = sweep_v1._owner_binding(row_axis, [page])
    assert result["sample_ids"] == ["nearest-owner"]
    assert result["source_line_indices"] == [900]


def test_period_location_bool_cannot_alias_integer_source_line() -> None:
    context = {
        "period_axis": [
            {
                "evidence_locations": [{"page_sequence": True, "source_line_index": True}],
                "projection_status": "LOCAL_EXACT_DATES_PROJECTED_TO_BODY_COLUMN",
            },
            {
                "evidence_locations": [{"page_sequence": 1, "source_line_index": 1}],
                "projection_status": "LOCAL_EXACT_DATES_PROJECTED_TO_BODY_COLUMN",
            },
        ]
    }
    with pytest.raises(sweep_v1.LoanCurrencyTrialUnresolvedV1Error, match="PDF evidence"):
        sweep_v1._period_mode(context, {(1, 1): {"vietocr_text": "31/12/2025"}})


@pytest.mark.parametrize("reader_score", [True, "0.99", 1])
def test_observed_cell_requires_raw_typed_numeric_receipt(reader_score: object) -> None:
    line = {
        "bbox": [10, 10, 50, 20],
        "crop_ref": {"sha256": "1" * 64},
        "line_ordinal": 3,
        "numeric_recognition": {"raw_prediction": "100", "reader_score": reader_score},
        "sample_id": "sample-1",
        "vietocr_text": "100",
    }
    value = {
        "bbox": [10, 10, 50, 20],
        "line_ordinal": 3,
        "page_sequence": 1,
        "raw_prediction": "100",
        "sample_id": "sample-1",
    }
    with pytest.raises(sweep_v1.LoanCurrencyTrialUnresolvedV1Error, match="authenticated"):
        sweep_v1._observed_cell(
            value,
            role="VND_LOANS",
            lane=0,
            lookup={(1, 3): line},
            packet_id="packet",
        )


def test_mapping_rows_retain_observed_ocr_labels_not_internal_roles() -> None:
    evidence = {
        "mapped_rows": [
            {
                "cells": [
                    {"selected_value": 100, "status": "RESOLVED_OBSERVED_VALUE"},
                    {"selected_value": 90, "status": "RESOLVED_OBSERVED_VALUE"},
                ],
                "label_surface": "Cho vay bằng đồng Việt Nam",
                "role": "VND_LOANS",
            },
            {
                "cells": [
                    {"selected_value": 20, "status": "RESOLVED_OBSERVED_VALUE"},
                    {"selected_value": 10, "status": "RESOLVED_OBSERVED_VALUE"},
                ],
                "label_surface": "Cho vay bằng ngoại tệ và vàng",
                "role": "FOREIGN_CURRENCY_AND_GOLD_LOANS",
            },
        ],
        "period_axis": {"periods": ["31/12/2025", "31/12/2024"]},
    }
    schema = {
        "mapped_roles": [
            {
                "canonical_name": "VND schema",
                "report_norm_id": 757,
                "role": "VND_LOANS",
            },
            {
                "canonical_name": "FX schema",
                "report_norm_id": 758,
                "role": "FOREIGN_CURRENCY_AND_GOLD_LOANS",
            },
        ],
        "projection_id": "projection",
    }
    mappings = sweep_v1._mapping_rows(evidence, schema)
    assert [item["source_label"] for item in mappings] == [
        "Cho vay bằng đồng Việt Nam",
        "Cho vay bằng ngoại tệ và vàng",
    ]
    assert all(item["source_label"] != item["role"] for item in mappings)


def test_terminal_contract_reports_exact_family10_denominators(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trials, inputs = _terminal_fixture(monkeypatch)
    result = sweep_v1._terminal_material(trials, inputs)
    metrics = result["metrics"]
    assert result["state"] == "COMPLETE"
    assert metrics["bank_presence_counts"] == sweep_v1._TARGET_BANK_PRESENCE_COUNTS
    assert metrics["bank_bounded_absence_counts"] == sweep_v1._TARGET_BANK_ABSENCE_COUNTS
    assert metrics["mapped_record_count"] == 20
    assert metrics["mapped_money_cell_count"] == 40
    assert metrics["observed_accounting_equation_count"] == 36
    assert metrics["visible_dash_zero_cell_count"] == 8
    assert metrics["direct_visible_dash_zero_cell_count"] == 6
    assert metrics["bounded_paired_dash_zero_cell_count"] == 2
    assert metrics["ppocrv6_vietocr_raw_surface_disagreement_count"] == 2
    assert metrics["ppocrv6_vietocr_numeric_disagreement_count"] == 1
    assert metrics["full_axis_positive_joined_line_count"] == 63_028


def test_terminal_semantics_reject_self_rehashed_metric_tamper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trials, inputs = _terminal_fixture(monkeypatch)
    result = sweep_v1._terminal_material(trials, inputs)
    tampered = copy.deepcopy(result)
    tampered["metrics"]["visible_dash_zero_cell_count"] = 9
    material = copy.deepcopy(tampered)
    material.pop("sweep_id")
    tampered["sweep_id"] = "lc140v1:sweep:" + canonical_json_sha256_v1(material)
    with pytest.raises(
        sweep_v1.FamilyFirstLoanCurrency140FilingSchemaSweepV1Error,
        match="terminal semantics",
    ):
        sweep_v1.validate_authenticated_family_first_loan_currency_140_filing_schema_sweep_v1(
            tampered
        )


def test_terminal_rejects_absence_numeric_hydration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trials, inputs = _terminal_fixture(monkeypatch)
    absence = next(trial for trial in trials if trial["status"] == "VERIFIED_BOUNDED_ABSENCE")
    absence["source_hydration"] = {"line_count": 1}
    with pytest.raises(
        sweep_v1.FamilyFirstLoanCurrency140FilingSchemaSweepV1Error,
        match="bounded absence",
    ):
        sweep_v1._terminal_material(trials, inputs)


def test_exclusive_writer_never_overwrites_existing_result(tmp_path: Path) -> None:
    path = tmp_path / "result.json"
    sweep_v1._write_exclusive(path, b"first\n")
    assert path.stat().st_mode & 0o777 == 0o444
    with pytest.raises(
        sweep_v1.FamilyFirstLoanCurrency140FilingSchemaSweepV1Error,
        match="already exists",
    ):
        sweep_v1._write_exclusive(path, b"second\n")
    assert path.read_bytes() == b"first\n"


def test_strict_result_rejects_symlink_before_following_target(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_text("{}\n", encoding="utf-8")
    link = tmp_path / "result.json"
    os.symlink(target, link)
    with pytest.raises(
        sweep_v1.FamilyFirstLoanCurrency140FilingSchemaSweepV1Error,
        match="regular nofollow",
    ):
        sweep_v1._strict_result(link)


def test_strict_result_requires_exactly_one_canonical_trailing_lf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        sweep_v1,
        "validate_authenticated_family_first_loan_currency_140_filing_schema_sweep_v1",
        lambda value: value,
    )
    value = {"format": "synthetic"}
    payload = canonical_json_bytes_v1(value)
    assert payload.endswith(b"\n") and not payload.endswith(b"\n\n")
    exact = tmp_path / "exact.json"
    sweep_v1._write_exclusive(exact, payload)
    assert sweep_v1._strict_result(exact) == value

    doubled = tmp_path / "double.json"
    sweep_v1._write_exclusive(doubled, payload + b"\n")
    with pytest.raises(
        sweep_v1.FamilyFirstLoanCurrency140FilingSchemaSweepV1Error,
        match="exactly one LF",
    ):
        sweep_v1._strict_result(doubled)
