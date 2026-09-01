from __future__ import annotations

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path

from bctc_ai.evaluation.gemini_json_first_vertex_flex_expansion_v1 import (
    build_gemini_json_first_vertex_flex_expansion_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/experiments/run_gemini_json_first_27bank_vertex_flex_v1.py"
SPEC = importlib.util.spec_from_file_location("run_27bank_vertex_flex", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
target = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = target
SPEC.loader.exec_module(target)


def _files(tmp_path: Path) -> tuple[Path, Path]:
    processed = ["ACB", "BID", "CTG", "HDB", "MBB", "VCB", "VIB", "VPB"]
    new = [f"N{ordinal:02d}" for ordinal in range(1, 20)]
    filings = [
        {
            "bank": bank,
            "content_ref": {
                "path": f"vietstock_bctc/{bank}/2025/report.pdf",
                "sha256": f"{ordinal:064x}",
                "size_bytes": 100,
            },
            "filename_hints_non_authoritative": {},
            "page_count": 1,
            "provider_disposition": (
                "REUSE_EXISTING_GEMINI_JSON" if bank in processed else "NEW_VERTEX_FLEX_FRONTIER"
            ),
            "source_authentication_flags": [],
            "year": 2025,
        }
        for ordinal, bank in enumerate(sorted([*processed, *new]), start=1)
    ]
    universe = {
        "already_processed_bank_codes": processed,
        "already_processed_corpus_ref": {
            "bank_codes": processed,
            "document_count": 8,
            "manifest_index_id": "gjfccmiv1:index:" + "c" * 64,
            "page_count": 8,
        },
        "authenticated_universe_id": "bankfilingauthv1:" + "a" * 64,
        "filings": filings,
        "format_version": "BANK_FILING_UNIVERSE_27BANK_2025_CURRENT_V1",
        "local_source_authentication": {
            "all_content_sha256_verified": True,
            "all_pdf_signatures_verified": True,
            "all_sources_regular_nonsymlink_files": True,
            "page_count_engine": "PYMUPDF_DOCUMENT_PAGE_COUNT",
        },
        "new_bank_codes": new,
        "summary": {
            "already_processed_bank_count": 8,
            "bank_count": 27,
            "candidate_filing_count": 27,
            "candidate_page_count": 27,
            "new_bank_count": 19,
            "provider_call_candidate_filing_count": 19,
            "provider_call_candidate_page_count": 19,
        },
    }
    manifest = {
        "corpus_manifest_index_id": "gjfccmiv1:index:" + "c" * 64,
        "documents": [
            {
                "relative_path": f"vietstock_bctc/{bank}/2025/old-report.pdf",
                "source_sha256": f"{ordinal + 100:064x}",
            }
            for ordinal, bank in enumerate(processed, start=1)
        ],
        "format_version": "GEMINI_CURRENT_CORPUS_MANIFEST_INDEX_V1",
        "summary": {"document_count": 8, "page_count": 8},
    }
    bundle = build_gemini_json_first_vertex_flex_expansion_v1(
        universe,
        already_processed_corpus_manifest_index=manifest,
    )
    bundle_path = tmp_path / "bundle.json"
    plan_path = tmp_path / "plan.json"
    bundle_path.write_bytes(canonical_json_bytes_v1(bundle) + b"\n")
    plan_path.write_bytes(canonical_json_bytes_v1(bundle["corpus_plan"]) + b"\n")
    return bundle_path, plan_path


def test_run_command_always_includes_openrouter_only_and_no_provider_override(
    tmp_path: Path,
) -> None:
    bundle, plan = _files(tmp_path)
    args = Namespace(
        artifact_root=tmp_path / "artifacts",
        bundle=bundle,
        command="run",
        database=tmp_path / "store.sqlite3",
        ledger=tmp_path / "ledger.sqlite3",
        max_fallback_attempts=2,
        openrouter_key_file=tmp_path / "openrouter",
        openrouter_workers=20,
        plan=plan,
        provider_timeout_seconds=900,
        source_root=tmp_path / "sources",
    )

    command = target._supervisor_command(args)

    assert command[-1] == "--openrouter-only"
    assert "--google-key-file" not in command
    assert "--google-standard-mode" not in command
    assert command[command.index("--openrouter-key-file") + 1] == str(tmp_path / "openrouter")
