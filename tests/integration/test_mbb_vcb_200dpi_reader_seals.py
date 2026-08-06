from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file


def test_mbb_vcb_200dpi_reader_acquisition_is_sealed_and_fail_closed(project_root):
    artifact_path = project_root / "docs/experiments/E-0014-mbb-vcb-200dpi-reader-seals.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact["format_version"] == 1
    assert artifact["experiment_id"] == "E-0014"
    assert artifact["design"] == "SELECTED_PAGE_200_DPI_INDEPENDENT_READER_ACQUISITION"
    assert artifact["dataset_role"] == "CALIBRATION"
    assert artifact["status"] == "PASS_FOUR_READER_SEALS_PENDING_FUSION"
    assert artifact["code"] == {
        "git_commit": "116c1879cef7f3f63b2bf1e7d71561d8c7ef78c8",
        "git_dirty": False,
    }
    assert "/workspace/" not in json.dumps(artifact)

    for relative_path, digest in artifact["algorithm_files_sha256"].items():
        assert sha256_file(project_root / relative_path) == digest
    for record in (
        artifact["runtime"]["manifest"],
        artifact["runtime"]["package_freeze"],
        artifact["runtime"]["role_b_configuration"],
        artifact["runtime"]["role_c_configuration"],
    ):
        assert sha256_file(project_root / record["path"]) == record["sha256"]

    expected = {
        "MBB_2025_CONSOLIDATED": {
            "pages": [10, 11, 12, 13, 14, 15],
            "eligible": {"CDKT": [10, 11], "KQKD": [13], "LCTT": [14, 15]},
            "excluded": [12],
            "role_b_wall": 109.028548,
            "role_c_lines": 656,
            "role_c_words": 5365,
        },
        "VCB_2025_CONSOLIDATED": {
            "pages": [8, 9, 10, 11, 12, 13, 14],
            "eligible": {"CDKT": [8, 9], "KQKD": [11, 12], "LCTT": [13, 14]},
            "excluded": [10],
            "role_b_wall": 197.196731,
            "role_c_lines": 779,
            "role_c_words": 5411,
        },
    }
    assert {document["key"] for document in artifact["documents"]} == set(expected)
    for document in artifact["documents"]:
        contract = expected[document["key"]]
        page_contract = document["page_contract"]
        assert page_contract["selected_pages"] == contract["pages"]
        assert page_contract["mapping_eligible_pages_by_statement_type"] == contract["eligible"]
        assert page_contract["off_balance_exclusion_pages"] == contract["excluded"]
        quality = document["preprocess"]["quality"]
        assert quality["clean_pages"] == len(contract["pages"])
        assert quality["selected_pages"] == len(contract["pages"])
        assert quality["perspective_candidates"] == 0
        assert quality["difficult_regions"] == 0
        assert quality["selected_input"] == "ORIGINAL_RENDER"
        assert document["role_b"]["metrics"] == {
            "page_count": len(contract["pages"]),
            "total_wall_seconds_sequential_processes": contract["role_b_wall"],
            "peak_memory_used_mib": 3241.0,
        }
        role_c_metrics = document["role_c"]["metrics"]
        assert role_c_metrics["page_count"] == len(contract["pages"])
        assert role_c_metrics["line_count"] == contract["role_c_lines"]
        assert role_c_metrics["word_token_count"] == contract["role_c_words"]
        assert role_c_metrics["model_load_session_count"] == 1

        source_path = project_root / document["source"]["path"]
        if source_path.is_file():
            assert source_path.stat().st_size == document["source"]["size_bytes"]
            assert sha256_file(source_path) == document["source"]["sha256"]
        for name in ("manifest", "run_manifest"):
            identity = document["preprocess"][name]
            path = project_root / identity["path"]
            if path.is_file():
                assert path.stat().st_size == identity["size_bytes"]
                assert sha256_file(path) == identity["sha256"]

        role_b_identity = document["role_b"]["seal"]
        role_b_path = project_root / role_b_identity["path"]
        if role_b_path.is_file():
            assert role_b_path.stat().st_size == role_b_identity["size_bytes"]
            assert sha256_file(role_b_path) == role_b_identity["sha256"]
            role_b = json.loads(role_b_path.read_text(encoding="utf-8"))
            assert role_b["state"] == "OCR_COMPLETE"
            assert role_b["dataset_role"] == "CALIBRATION"
            assert role_b["source_sha256"] == document["source"]["sha256"]
            assert [record["page"] for record in role_b["pages"]] == contract["pages"]
            assert all(record["render"]["dpi"] == 200 for record in role_b["pages"])
            assert role_b["artifact_set_sha256"] == document["role_b"]["artifact_set_sha256"]

        batch_identity = document["role_c"]["batch_manifest"]
        batch_path = project_root / batch_identity["path"]
        if batch_path.is_file():
            assert batch_path.stat().st_size == batch_identity["size_bytes"]
            assert sha256_file(batch_path) == batch_identity["sha256"]
            batch = json.loads(batch_path.read_text(encoding="utf-8"))
            assert batch["state"] == "OCR_COMPLETE"
            assert batch["dataset_role"] == "CALIBRATION"
            assert batch["requested_pages"] == contract["pages"]
            assert batch["batch_identity"] == document["role_c"]["batch_identity"]
            assert batch["code"] == {
                "commit": artifact["code"]["git_commit"],
                "dirty": False,
            }

        role_c_identity = document["role_c"]["seal"]
        role_c_path = project_root / role_c_identity["path"]
        if role_c_path.is_file():
            assert role_c_path.stat().st_size == role_c_identity["size_bytes"]
            assert sha256_file(role_c_path) == role_c_identity["sha256"]
            role_c = json.loads(role_c_path.read_text(encoding="utf-8"))
            assert role_c["state"] == "GEOMETRY_OCR_COMPLETE"
            assert role_c["dataset_role"] == "CALIBRATION"
            assert role_c["source_sha256"] == document["source"]["sha256"]
            assert [record["page"] for record in role_c["pages"]] == contract["pages"]
            assert role_c["artifact_set_sha256"] == document["role_c"]["artifact_set_sha256"]
            assert role_c["upstream_role_b_seal"]["sha256"] == role_b_identity["sha256"]
            assert role_c["acceptance"]["automatic_truth_promotion"] is False
            assert role_c["acceptance"]["automatic_schema_promotion"] is False
            assert role_c["acceptance"]["automatic_pdf_confidence_promotion"] is False

    totals = artifact["cross_document_metrics"]
    assert totals["selected_page_count"] == 13
    assert totals["quality_clean_page_count"] == 13
    assert totals["reader_seal_count"] == 4
    assert totals["role_c_line_count"] == 1435
    assert totals["role_c_word_token_count"] == 10776
    failure = artifact["retained_failure_observations"][0]
    assert failure["document"] == "VCB_2025_CONSOLIDATED"
    assert failure["page"] == 9
    assert failure["generated_table_tr_count_including_header"] == 7
    assert artifact["software_or_model_change"] is False
    assert artifact["report_norm_id"]["ids_proposed_or_added"] == 0
    assert all(value is False for value in artifact["safety"].values())
    assert artifact["acceptance"]["row_or_cell_accuracy_evaluated"] is False
    assert artifact["acceptance"]["human_gold_evaluated"] is False
    assert artifact["acceptance"]["production_accuracy_approved"] is False
