#!/usr/bin/env python3
"""Build the authenticated 27-bank, Q1/2025-current Gemini input universe."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.bank_filing_universe_publication_v1 import (  # noqa: E402
    authenticate_bank_filing_universe_sources_v1,
    render_bank_filing_universe_markdown_v1,
)
from bctc_ai.evaluation.bank_filing_universe_v1 import (  # noqa: E402
    build_bank_filing_universe_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1  # noqa: E402

SNAPSHOT_MANIFEST_URI = (
    "s3://test-s3-duylv/bctc-ai/snapshots/"
    "20260806T050030130746Z-4a469fab2334/"
    "manifest-74be9ea09905f0c7842d5a0b46bfe44f3fc5f32cc2c15b5040efcc4e99e8981b.json"
)
ALREADY_PROCESSED_BANK_CODES = ("ACB", "BID", "CTG", "HDB", "MBB", "VCB", "VIB", "VPB")
ALREADY_PROCESSED_CORPUS_REF = {
    "bank_codes": list(ALREADY_PROCESSED_BANK_CODES),
    "document_count": 140,
    "manifest_index_id": (
        "gjfccmiv1:index:61be9e5dc44a261d2dbf3f396b9624e29cb4ae591ea0a7fdb83051352e7b60e3"
    ),
    "page_count": 8_947,
}


class BuildBankFilingUniverse27BankV1Error(RuntimeError):
    pass


def _write_once(path: Path, payload: bytes) -> None:
    if path.exists():
        raise BuildBankFilingUniverse27BankV1Error(f"refusing to overwrite output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o444)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-project-root", type=Path, default=ROOT)
    parser.add_argument(
        "--source-inventory",
        type=Path,
        default=Path("output/development/bank-corpus-survey-v1/corpus-inventory.json"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=ROOT / "data/registered/bank_filing_universe_27bank_2025_current_v1.json",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=ROOT / "docs/experiments/FINANCIAL_REPORT_INVENTORY_27BANK_2025_CURRENT.md",
    )
    parser.add_argument("--from-year", type=int, default=2025)
    parser.add_argument("--as-of-date", default="2026-09-01")
    args = parser.parse_args()

    source_root = args.source_project_root.resolve()
    inventory_path = (
        args.source_inventory
        if args.source_inventory.is_absolute()
        else source_root / args.source_inventory
    )
    raw = inventory_path.read_bytes()
    inventory = json.loads(raw)
    registry = json.loads((source_root / "data/registered/bank_registry.json").read_bytes())
    banks = tuple(
        sorted(
            entity["code"] for entity in registry["entities"] if entity.get("category") == "BANK"
        )
    )
    universe = build_bank_filing_universe_v1(
        inventory,
        bank_codes=banks,
        from_year=args.from_year,
        as_of_date=args.as_of_date,
        source_inventory_ref={
            "path": inventory_path.relative_to(source_root).as_posix(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw),
        },
        source_snapshot_manifest_uri=SNAPSHOT_MANIFEST_URI,
        already_processed_bank_codes=ALREADY_PROCESSED_BANK_CODES,
        already_processed_corpus_ref=ALREADY_PROCESSED_CORPUS_REF,
    )
    authenticated = authenticate_bank_filing_universe_sources_v1(universe, source_root=source_root)
    markdown = render_bank_filing_universe_markdown_v1(authenticated)
    _write_once(args.json_output, canonical_json_bytes_v1(authenticated))
    _write_once(args.markdown_output, markdown.encode("utf-8"))
    print(
        json.dumps(
            {
                "authenticated_universe_id": authenticated["authenticated_universe_id"],
                "bank_count": authenticated["summary"]["bank_count"],
                "candidate_filing_count": authenticated["summary"]["candidate_filing_count"],
                "candidate_page_count": authenticated["summary"]["candidate_page_count"],
                "json_output": str(args.json_output),
                "markdown_output": str(args.markdown_output),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
