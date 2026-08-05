from __future__ import annotations

import json

import pytest

from bctc_ai.core.hashing import sha256_file
from bctc_ai.evaluation.frozen_suite import load_frozen_suite
from bctc_ai.evaluation.page_pairing import align_pdf_pages, pairing_config_from_dict


def test_registered_tcb_scan_searchable_pair(project_root):
    result_path = project_root / "docs/experiments/E-0009-frozen-paired-calibration.json"
    if not result_path.is_file():
        pytest.skip("E-0009 fixture has not been generated")
    expected = json.loads(result_path.read_text(encoding="utf-8"))
    config_path = project_root / expected["config"]["path"]
    assert sha256_file(config_path) == expected["config"]["sha256"]
    for relative_path, digest in expected["algorithm_files_sha256"].items():
        assert sha256_file(project_root / relative_path) == digest

    suite = load_frozen_suite(project_root, config_path)
    reference = suite.source(str(suite.pairing["reference_fixture_id"]))
    candidate = suite.source(str(suite.pairing["candidate_fixture_id"]))
    reference_path = project_root / reference.path
    candidate_path = project_root / candidate.path
    if not reference_path.is_file() or not candidate_path.is_file():
        pytest.skip("external registered TCB pair is not present")

    pairing = align_pdf_pages(
        reference_path,
        candidate_path,
        pairing_config_from_dict(suite.pairing["visual_fingerprint"]),
    )
    accepted = {
        step.reference_page: step.candidate_page
        for step in pairing.accepted
        if step.reference_page is not None
    }

    assert expected["status"] == "PASS_FROZEN_PAIRING_FOUND"
    assert all(page in accepted for page in suite.pairing["target_reference_pages"])
    assert [accepted[page] for page in suite.pairing["target_reference_pages"]] == [
        step["candidate_page"] for step in expected["pairing"]["target_pairs"]
    ]

