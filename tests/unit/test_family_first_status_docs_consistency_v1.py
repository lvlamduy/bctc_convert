from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "data/registered/family_first_accounting_checkpoints_v1.json"
COMPLETED = ROOT / "docs/experiments/COMPLETED_TM_FAMILIES.md"
LEDGER = ROOT / "docs/experiments/UNRESOLVED_MAPPING_LEDGER.md"


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
