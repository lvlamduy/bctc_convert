from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "data/registered/family_first_accounting_checkpoints_v1.json"
COMPLETED = ROOT / "docs/experiments/COMPLETED_TM_FAMILIES.md"
LEDGER = ROOT / "docs/experiments/UNRESOLVED_MAPPING_LEDGER.md"
INTERBANK_EVIDENCE = (
    ROOT
    / "output/calibration/family-first-accounting-evidence-sweeps-v1"
    / "interbank-deposits-and-loans.json"
)
INTERBANK_MAPPING = (
    ROOT
    / "output/calibration/family-first-accounting-schema-mappings-v1"
    / "interbank-deposits-and-loans.json"
)

INTERBANK_UNRESOLVED_TRIALS = {
    1,
    3,
    5,
    6,
    11,
    12,
    17,
    18,
    25,
    26,
    27,
    28,
    37,
    38,
    39,
    40,
    41,
    42,
    43,
    44,
    45,
    46,
    62,
    64,
    65,
    75,
    86,
    87,
    88,
    89,
    90,
    92,
    93,
    94,
    95,
    96,
    99,
    100,
    101,
    102,
    139,
    140,
}

INTERBANK_PRIMARY_CAUSE_COUNTS = {
    "ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE": 16,
    "MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES": 15,
    "VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM": 6,
    "TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM": 4,
    "CROSS_PAGE_PERIOD_UNIT_INHERITANCE_NOT_PROVEN": 1,
}


def _trading_metrics() -> dict[str, int]:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    checkpoint = next(
        item for item in registry["checkpoints"] if item["family_id"] == "TRADING_SECURITIES"
    )
    return checkpoint["metrics"]


def test_current_trading_summary_and_open_ledger_share_one_denominator() -> None:
    metrics = _trading_metrics()
    completed = COMPLETED.read_text(encoding="utf-8")
    ledger = LEDGER.read_text(encoding="utf-8")
    start = ledger.index("<!-- TRADING_SECURITIES_OPEN_FILINGS_BEGIN -->")
    stop = ledger.index("<!-- TRADING_SECURITIES_OPEN_FILINGS_END -->")
    current = ledger[start:stop]

    assert f"{metrics['verified_document_count']}/140 filing" in completed
    assert f"{metrics['verified_mapping_count']} mapping" in completed
    assert f"{metrics['not_observed_proposal_count']} filing" in completed
    if metrics["unresolved_document_count"] == 0:
        assert "Không còn filing nào; số unresolved là 0" in completed
        assert "0 `UNRESOLVED`" in current
    else:
        assert f"{metrics['unresolved_document_count']} filing" in completed
    assert current.count("\n| TS-") == metrics["unresolved_document_count"]
    assert (
        len(set(re.findall(r"\| (TS-[0-9]{3}) \|", current)))
        == metrics["unresolved_document_count"]
    )


def test_every_current_trading_open_row_names_one_exact_filing_scope_and_review_status() -> None:
    metrics = _trading_metrics()
    ledger = LEDGER.read_text(encoding="utf-8")
    current = ledger[
        ledger.index("<!-- TRADING_SECURITIES_OPEN_FILINGS_BEGIN -->") : ledger.index(
            "<!-- TRADING_SECURITIES_OPEN_FILINGS_END -->"
        )
    ]
    rows = [line for line in current.splitlines() if line.startswith("| TS-")]
    assert len(rows) == metrics["unresolved_document_count"]
    if not rows:
        assert metrics["unresolved_document_count"] == 0
        return
    assert all(re.search(r"\| (?:Năm [0-9]{4}|(?:H1|Q[1-4])/[0-9]{4}) — ", row) for row in rows)
    assert all(" — hợp nhất — " in row or " — công ty mẹ/riêng lẻ — " in row for row in rows)
    assert all(
        " — kiểm toán |" in row or " — soát xét |" in row or " — không kiểm toán |" in row
        for row in rows
    )
    assert all(
        re.search(r"\| p[0-9]+(?:–[0-9]+)?(?:, p[0-9]+(?:–[0-9]+)?)* \|", row) for row in rows
    )
    assert "annual/H1/Q1" not in current


def test_historical_trading_section_cannot_be_mistaken_for_current_queue() -> None:
    ledger = LEDGER.read_text(encoding="utf-8")
    historical = ledger[ledger.index("## Trading securities (`TRADING_SECURITIES`)") :]
    assert "Historical fixed-eight checkpoint only" in historical
    assert "authoritative current queue" in historical


def _interbank_unresolved_rows() -> list[list[str]]:
    ledger = LEDGER.read_text(encoding="utf-8")
    start = ledger.index("<!-- INTERBANK_575_UNRESOLVED_FILINGS_BEGIN -->")
    stop = ledger.index("<!-- INTERBANK_575_UNRESOLVED_FILINGS_END -->")
    block = ledger[start:stop]
    return [
        [cell.strip() for cell in line.split("|")[1:-1]]
        for line in block.splitlines()
        if line.startswith("| IDL-575-")
    ]


def test_interbank_575_open_ledger_has_one_auditable_row_per_trial() -> None:
    rows = _interbank_unresolved_rows()

    assert len(rows) == 42
    assert len({row[0] for row in rows}) == 42
    assert {int(row[1]) for row in rows} == INTERBANK_UNRESOLVED_TRIALS
    assert Counter(row[2].split(" / ", 1)[0] for row in rows) == {
        "ACB": 10,
        "MBB": 2,
        "VPB": 4,
        "HDB": 10,
        "CTG": 3,
        "BID": 1,
        "VIB": 12,
    }
    assert Counter(row[5].strip("`") for row in rows) == (INTERBANK_PRIMARY_CAUSE_COUNTS)


def test_every_interbank_575_open_row_keeps_source_region_and_machine_reason() -> None:
    rows = _interbank_unresolved_rows()

    for row in rows:
        bank_period_scope = row[2]
        pdf_identity = row[3]
        selected_region = row[4]
        exact_reasons = row[6]

        assert re.fullmatch(
            r"(?:ACB|MBB|VPB|HDB|CTG|BID|VIB) / "
            r"(?:Năm|H1|Q[1-4]) 20(?:25|26) / "
            r"(?:hợp nhất|công ty mẹ/riêng lẻ)",
            bank_period_scope,
        )
        assert re.search(r"`vietstock_bctc/.+\.pdf`<br>", pdf_identity)
        assert re.search(r"`sha256:[0-9a-f]{64}`$", pdf_identity)
        assert re.search(r"(?:^|<br>)(?:candidate [12]: )?p[0-9]+", selected_region)
        assert re.search(r"doc-line [0-9]+–[0-9]+", selected_region)
        assert exact_reasons.startswith("`") and exact_reasons.endswith("`")
        assert any(
            token in exact_reasons
            for token in (
                "VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE",
                "NOT_EXACT_COMPONENT_SUM",
                "NOT_ONE_EXACT_COMPONENT_SUM",
                "INHERITANCE_NOT_PROVEN",
            )
        )


def _primary_interbank_cause(trial: dict[str, object]) -> str:
    topology = trial["topology_scan"]
    assert isinstance(topology, dict)
    regions = topology["regions"]
    reasons = trial["unresolved_reasons"]
    assert isinstance(regions, list)
    assert isinstance(reasons, list)

    if len(regions) > 1:
        return "MULTI_REGION_CANDIDATES_FAIL_DISTINCT_EVIDENCE_GATES"
    if reasons == ["COLUMN_CONTEXT:CROSS_PAGE_PERIOD_UNIT_INHERITANCE_NOT_PROVEN"]:
        return "CROSS_PAGE_PERIOD_UNIT_INHERITANCE_NOT_PROVEN"
    if any("TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM" in reason for reason in reasons):
        return "TRAILING_RESULT_NOT_ONE_EXACT_COMPONENT_SUM"
    if any("VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM" in reason for reason in reasons):
        return "VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM"
    assert any("VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE" in reason for reason in reasons)
    return "ROLE_LANE_OR_HEADER_AXIS_INCOMPLETE"


@pytest.mark.skipif(
    not INTERBANK_EVIDENCE.exists() or not INTERBANK_MAPPING.exists(),
    reason="ignored family-first artifacts are not restored in this checkout",
)
def test_interbank_575_ledger_rows_exact_match_both_replayed_artifacts() -> None:
    evidence = json.loads(INTERBANK_EVIDENCE.read_text(encoding="utf-8"))
    mapping = json.loads(INTERBANK_MAPPING.read_text(encoding="utf-8"))
    ledger = LEDGER.read_text(encoding="utf-8")
    evidence_trials = {
        trial["document_ordinal"]: trial
        for trial in evidence["trials"]
        if trial["evidence_status"] == "UNRESOLVED_EVIDENCE_GATES"
    }
    mapping_trials = {
        trial["document_ordinal"]: trial
        for trial in mapping["trials"]
        if trial["mapping_status"] == "UNRESOLVED"
    }
    rows = _interbank_unresolved_rows()

    assert f"`{hashlib.sha256(INTERBANK_EVIDENCE.read_bytes()).hexdigest()}`" in ledger
    assert f"`{hashlib.sha256(INTERBANK_MAPPING.read_bytes()).hexdigest()}`" in ledger
    assert len(rows) == len(evidence_trials) == len(mapping_trials) == 42
    assert set(evidence_trials) == set(mapping_trials) == {int(row[1]) for row in rows}
    for row in rows:
        trial = evidence_trials[int(row[1])]
        mapping_trial = mapping_trials[int(row[1])]
        provenance = trial["private_provenance"]
        source = trial["source_pdf_ref"]
        regions = trial["topology_scan"]["regions"]

        assert source == mapping_trial["source_pdf_ref"]
        assert provenance == mapping_trial["private_provenance"]
        assert trial["unresolved_reasons"] == mapping_trial["unresolved_reasons"]

        period = "Năm" if provenance["period"] == "ANNUAL" else provenance["period"]
        scope = "hợp nhất" if provenance["scope"] == "CONSOLIDATED" else "công ty mẹ/riêng lẻ"
        assert row[2] == (f"{provenance['bank']} / {period} {provenance['year']} / {scope}")
        assert row[3] == (f"`{source['path']}`<br>`sha256:{source['sha256']}`")

        expected_regions = []
        for candidate_ordinal, region in enumerate(regions, start=1):
            page_start = region["page_sequence"]
            page_end = region["cluster_end_page_sequence_inclusive"]
            pages = f"p{page_start}" if page_start == page_end else f"p{page_start}–{page_end}"
            candidate = f"candidate {candidate_ordinal}: " if len(regions) > 1 else ""
            expected_regions.append(
                f"{candidate}{pages}, doc-line "
                f"{region['cluster_start_document_line_ordinal']}–"
                f"{region['cluster_end_document_line_ordinal_exclusive'] - 1}"
            )
        assert row[4] == "<br>".join(expected_regions)
        assert row[5] == f"`{_primary_interbank_cause(trial)}`"
        assert row[6] == "<br>".join(f"`{reason}`" for reason in trial["unresolved_reasons"])


def test_family_completion_rule_and_interbank_summary_are_in_both_status_docs() -> None:
    completed = COMPLETED.read_text(encoding="utf-8")
    ledger = LEDGER.read_text(encoding="utf-8")

    assert "cập nhật cả" in completed
    assert "UNRESOLVED_MAPPING_LEDGER.md" in completed
    assert "every family checkpoint must update both" in ledger
    assert "COMPLETED_TM_FAMILIES.md" in ledger
    assert "UNRESOLVED_MAPPING_LEDGER.md#family-3-rnid-575-unresolved" in completed
    assert "tổng đúng 42" in completed
    for cause, count in INTERBANK_PRIMARY_CAUSE_COUNTS.items():
        assert f"{count}\n  `{cause}`" in completed or f"{count} `{cause}`" in completed


def test_family11_zero_unresolved_is_recorded_in_both_status_docs() -> None:
    completed = COMPLETED.read_text(encoding="utf-8")
    ledger = LEDGER.read_text(encoding="utf-8")

    assert "## 11. Phân tích dư nợ cho vay theo khu vực địa lý" in completed
    assert "Không còn trial unresolved trong denominator này" in completed
    assert (
        "## CLOSED — family-first 140-filing "
        "`Phân tích dư nợ cho vay theo khu vực địa lý`" in ledger
    )
    assert "**0 filing `UNRESOLVED`**" in ledger
    assert "E-0175-family-first-loan-geography-140-filing-schema-sweep-seal-v1.json" in ledger
