from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT / "scripts/experiments/"
    "build_annual_2025_issued_valuable_papers_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location("annual_2025_issued_papers_builder", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def test_review_covers_eight_unique_annual_regions_and_adjacent_continuation() -> None:
    review = builder.build_annual_2025_issued_valuable_papers_pixel_review_blueprint_v1()
    assert [item["bank_code"] for item in review["documents"]] == [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
    ]
    assert sum(len(item["mappings"]) for item in review["documents"]) == 70
    assert sum(len(item["equations"]) for item in review["documents"]) == 34
    assert sum(len(item["unmapped_source_rows"]) for item in review["documents"]) == 5
    assert next(item for item in review["documents"] if item["bank_code"] == "CTG")[
        "page_span"
    ] == [53, 54]


def test_project_owner_tenor_decisions_and_visible_dash_zero_are_explicit() -> None:
    review = builder.build_annual_2025_issued_valuable_papers_pixel_review_blueprint_v1()
    by_bank = {item["bank_code"]: item for item in review["documents"]}
    assert {item["report_norm_id"] for item in by_bank["ACB"]["mappings"]} >= {1103, 1111}
    assert {item["report_norm_id"] for item in by_bank["MBB"]["mappings"]} >= {6009, 6010}
    assert {item["report_norm_id"] for item in by_bank["BID"]["mappings"]} >= {1117}
    assert {
        item["item_id"] for item in by_bank["VPB"]["unmapped_source_rows"]
    } == builder._EXPECTED_OPEN_IDS["VPB"]

    dash_refs = []
    for document in review["documents"]:
        for mapping in document["mappings"]:
            for refs in mapping["values"].values():
                dash_refs.extend(
                    ref for ref in refs if ref["kind"] == "AUTHENTICATED_RENDER_PIXEL_DASH"
                )
    assert len({(ref["page_sequence"], tuple(ref["bbox"])) for ref in dash_refs}) == 11
    assert all(ref["pixel_transcription"] == "-" for ref in dash_refs)


def test_persisted_result_matches_exact_live_replay() -> None:
    persisted = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())
    rebuilt = (
        builder.build_live_annual_2025_issued_valuable_papers_8bank_codex_verified_mapping_v1()
    )
    assert rebuilt == persisted
    assert rebuilt["result_id"] == (
        "annual2025ivp8bcv1:result:3bd9ebd6bcae541522f7fc86d4ced810d509e659908ca01566adef9ceb805e9f"
    )
    assert rebuilt["metrics"] == builder._EXPECTED_METRICS
    assert [trial["page_span"] for trial in rebuilt["trials"]] == [
        [63, 63],
        [66, 66],
        [62, 62],
        [46, 46],
        [54, 54],
        [53, 54],
        [52, 52],
        [47, 47],
    ]
