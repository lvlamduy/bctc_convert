from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT / "scripts/experiments/"
    "build_annual_2025_entrusted_investment_risk_capital_8bank_codex_verified_mapping_v1.py"
)
_SPEC = importlib.util.spec_from_file_location("annual_2025_entrusted_capital_builder", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = builder
_SPEC.loader.exec_module(builder)


def test_review_covers_eight_unique_annual_regions_and_generic_variants() -> None:
    review = builder.build_annual_2025_entrusted_investment_risk_capital_pixel_review_blueprint_v1()
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
    assert all(item["disposition"] == "VERIFIED_BY_CODEX" for item in review["documents"])
    assert sum(len(item["mappings"]) for item in review["documents"]) == 20
    assert sum(len(item["equations"]) for item in review["documents"]) == 8


def test_vcb_visible_dash_is_bound_before_zero_normalization() -> None:
    review = builder.build_annual_2025_entrusted_investment_risk_capital_pixel_review_blueprint_v1()
    vcb = next(item for item in review["documents"] if item["bank_code"] == "VCB")
    current = [mapping["values"]["CURRENT"][0] for mapping in vcb["mappings"]]
    assert (
        current
        == [
            {
                "bbox": [1148, 1587, 1176, 1609],
                "kind": "AUTHENTICATED_RENDER_PIXEL_DASH",
                "multiplier": 1,
                "page_sequence": 53,
                "pixel_rgb_sha256": (
                    "0c4389692e0d96850eefbbeb97804015cec29dabbd3c6472db69f3bae39a1e0a"
                ),
                "pixel_transcription": "-",
            }
        ]
        * 2
    )


def test_persisted_result_matches_exact_live_replay() -> None:
    persisted = json.loads((builder.PROJECT_ROOT / builder.RESULT_PATH).read_text())
    rebuilt = builder.build_live_annual_2025_entrusted_investment_risk_capital_8bank_codex_verified_mapping_v1()
    assert rebuilt == persisted
    assert rebuilt["result_id"] == (
        "annual2025eirc8bcv1:result:388eceadf881c7acd2df43177958f2262c0d08004f000dc45a3eb0b87c9654d3"
    )
    assert rebuilt["metrics"] == builder._EXPECTED_METRICS
    assert all(trial["status"] == "VERIFIED_BY_CODEX" for trial in rebuilt["trials"])
