"""Run PRIMARY_ONLY digitization over one pinned corpus into a new result store.

Stages (each timed and counted): authenticate corpus and selections, census,
authenticated page hydration, assembly/mapping/validation, document results,
write-once SQLite store, store reload, independent rebuild in a fresh process
(exact result-id comparison), PRIMARY_ONLY workbooks with exact readback, and
a run manifest binding every input, code and config hash. No provider is
called and no source artifact is written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.primary_statements.catalog_v1 import load_primary_catalog_v1  # noqa: E402
from bctc_ai.primary_statements.excel_v1 import build_workbook_v1, template_rows_v1, verify_workbook_v1  # noqa: E402
from bctc_ai.primary_statements.pipeline_v1 import PIPELINE_VERSION, run_corpus_v1  # noqa: E402
from bctc_ai.primary_statements.result_v1 import build_document_result_v1  # noqa: E402
from bctc_ai.primary_statements.source_v1 import SourceMetrics, load_corpus_selection_v1, sha256_file  # noqa: E402
from bctc_ai.primary_statements.store_v1 import reload_result_store_v1, write_result_store_v1  # noqa: E402
from bctc_ai.primary_statements.validation_v1 import load_equation_config_v1  # noqa: E402

CORPORA = {
    "full271": {
        "root": "/srv/bctc-restore/dev-shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts",
        "index": "current-corpus-manifest-indexes/8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a.json",
        "index_sha256": "969ff5f80732c39e4b7543ca1f5c1e5b5b827260f19981ed02945fe0c7379219",
        "db_sha256": "ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7",
    },
    "common204": {
        "root": "/srv/bctc-restore/dev-shm/bctc-ai-27-bank-family-live-v1",
        "index": "current-corpus-manifest-indexes/32c474f657f9484244e9675a0ca4801cb49b4923971dfb7bea17081904154747.json",
        "index_sha256": "acc1d08e45e5a05925c434ae1c96fd6bc481a0e6ca61fc9f78e155efca7365b1",
        "db_sha256": "a14904a492e6beae165b81f7aa1738352a9824e113f1b163a46ee277d37e0220",
    },
}
FROZEN = {
    "src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py": "bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2",
    "scripts/experiments/run_gemini_json_multitable_hierarchical_accounting_family_v1.py": "d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5",
}


def code_pins() -> dict:
    files = sorted(
        [*(ROOT / "src/bctc_ai/primary_statements").glob("*.py"), *(ROOT / "config/primary_statements").glob("*.yaml"),
         ROOT / "scripts/primary_statements/run_primary_statements_v1.py",
         ROOT / "config/mapping/lctt-v2.yaml", ROOT / "config/schemas/sources.yaml"],
        key=str,
    )
    pins = {str(path.relative_to(ROOT)): sha256_file(path) for path in files if path.exists()}
    pins["src/bctc_ai/storage/gemini_income_tax_source_page_loader_v1.py"] = sha256_file(
        ROOT / "src/bctc_ai/storage/gemini_income_tax_source_page_loader_v1.py")
    frozen = {path: sha256_file(ROOT / path) for path in FROZEN}
    if frozen != FROZEN:
        raise SystemExit("frozen shared file drifted: " + json.dumps(frozen))
    return {"files": pins, "frozen_shared_files": frozen,
            "code_closure_sha256": hashlib.sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest()}


def run_results(corpus_name: str, documents: set[int] | None, verify_db: bool):
    spec = CORPORA[corpus_name]
    metrics = SourceMetrics()
    started = time.perf_counter()
    catalog = load_primary_catalog_v1(ROOT)
    equations = load_equation_config_v1(ROOT)
    corpus = load_corpus_selection_v1(
        name=corpus_name, root=Path(spec["root"]), index_relative_path=spec["index"],
        expected_index_sha256=spec["index_sha256"], expected_db_sha256=spec["db_sha256"],
        verify_db_bytes=verify_db, metrics=metrics,
    )
    runs = run_corpus_v1(corpus, catalog, project_root=ROOT, metrics=metrics, document_ordinals=documents)
    pins = {
        "pipeline_version": PIPELINE_VERSION,
        "catalog": catalog.identity(),
        "equations_sha256": equations.raw_sha256,
        "code": code_pins(),
    }
    with metrics.timed("document_results"):
        results = [build_document_result_v1(run, catalog, corpus_identity=corpus.identity(), pins=pins) for run in runs]
    metrics.stage_seconds["total_results"] = time.perf_counter() - started
    return catalog, corpus, results, pins, metrics


def summarize(results: list[dict]) -> dict:
    summary = {"documents": len(results), "statements": {}}
    for statement in ("CDKT", "KQKD", "LCTT"):
        found = sum(1 for r in results if r["statement_status"][statement]["status"] == "FOUND")
        dispositions = Counter(row["disposition"] for r in results for i in r["instances"] if i["statement"] == statement
                               for row in i["source_rows"])
        acceptance = Counter(c["acceptance"] for r in results for c in r["cells"] if c["statement"] == statement)
        holds = Counter(reason.split(":")[0] for r in results for c in r["cells"] if c["statement"] == statement
                        for reason in c["hold_reasons"])
        items = Counter(i["status"] for r in results for i in r["item_status"] if i["statement"] == statement)
        checks = Counter(v["status"] for r in results for i in r["instances"] if i["statement"] == statement
                         for v in i["validations"])
        summary["statements"][statement] = {
            "documents_with_statement": found, "source_row_dispositions": dict(sorted(dispositions.items())),
            "cell_acceptance": dict(sorted(acceptance.items())), "hold_reason_heads": dict(holds.most_common()),
            "item_status": dict(sorted(items.items())), "validation_status": dict(sorted(checks.items())),
        }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", choices=sorted(CORPORA), required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--documents", help="comma-separated document ordinals (bounded panel)")
    parser.add_argument("--git-head", required=False)
    parser.add_argument("--verify-db-bytes", action="store_true")
    parser.add_argument("--no-excel", action="store_true")
    parser.add_argument("--no-rebuild", action="store_true")
    parser.add_argument("--emit-result-ids", type=Path, help="rebuild mode: write {ordinal: result_id} and exit")
    args = parser.parse_args()
    documents = {int(item) for item in args.documents.split(",")} if args.documents else None
    catalog, corpus, results, pins, metrics = run_results(args.corpus, documents, args.verify_db_bytes)
    if args.emit_result_ids:
        args.emit_result_ids.write_text(json.dumps(
            {str(r["document"]["document_ordinal"]): r["result_id"] for r in results}, sort_keys=True))
        return 0
    if args.output_dir is None:
        raise SystemExit("--output-dir is required")
    if args.output_dir.exists():
        raise SystemExit("output directory already exists; every run uses a new directory")
    args.output_dir.mkdir(parents=True)
    manifest = {
        "format_version": "PRIMARY_ONLY_RUN_MANIFEST_V1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "git_head": args.git_head,
        "corpus": corpus.identity(),
        "documents_requested": sorted(documents) if documents else "ALL",
        "pins": pins,
        "provider_calls_performed": False,
        "source_mutations_performed": False,
        "product_label": "PRIMARY_ONLY",
    }
    store_path = args.output_dir / "primary-results.sqlite3"
    with metrics.timed("store_write"):
        store_receipt = write_result_store_v1(store_path, run_manifest=manifest, results=results)
    with metrics.timed("store_reload"):
        reloaded_manifest, reloaded = reload_result_store_v1(store_path)
    if reloaded_manifest != json.loads(json.dumps(manifest)) or [r["result_id"] for r in reloaded] != [r["result_id"] for r in results]:
        raise SystemExit("store reload differs from the in-memory results")
    rebuild = {"status": "SKIPPED"}
    if not args.no_rebuild:
        with metrics.timed("independent_rebuild"):
            ids_path = args.output_dir / "rebuild-result-ids.json"
            command = [sys.executable, "-B", str(Path(__file__)), "--corpus", args.corpus, "--emit-result-ids", str(ids_path)]
            if args.documents:
                command += ["--documents", args.documents]
            subprocess.run(command, check=True)
            rebuilt = json.loads(ids_path.read_text())
            original = {str(r["document"]["document_ordinal"]): r["result_id"] for r in results}
            differing = sorted(key for key in original if rebuilt.get(key) != original[key])
            rebuild = {"status": "PASS_EXACT_RESULT_IDS" if not differing and set(rebuilt) == set(original) else "FAIL",
                       "documents": len(original), "differing": differing,
                       "rebuild_ids_sha256": hashlib.sha256(ids_path.read_bytes()).hexdigest()}
        if rebuild["status"] != "PASS_EXACT_RESULT_IDS":
            raise SystemExit("independent rebuild differs: " + json.dumps(rebuild))
    workbooks = []
    if not args.no_excel:
        template = template_rows_v1(ROOT, catalog)
        (args.output_dir / "workbooks").mkdir()
        with metrics.timed("excel_export_and_readback"):
            for result in reloaded:
                payload, _ = build_workbook_v1(result, template)
                receipt = verify_workbook_v1(payload, result, template)
                document = result["document"]
                name = f"{document['document_ordinal']:03d}_{document['document_plan_id'].split(':')[1][:16]}_PRIMARY_ONLY.xlsx"
                (args.output_dir / "workbooks" / name).write_bytes(payload)
                workbooks.append({"document_ordinal": document["document_ordinal"], "file": name, **receipt})
    final = {
        **manifest,
        "store": store_receipt,
        "store_reload": {"status": "PASS_EXACT", "documents": len(reloaded)},
        "independent_rebuild": rebuild,
        "workbooks": workbooks,
        "metrics": metrics.to_dict(),
        "summary": summarize(results),
    }
    (args.output_dir / "run-manifest.json").write_text(json.dumps(final, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(args.output_dir), "store_sha256": store_receipt["sha256"],
                      "rebuild": rebuild["status"], "workbooks": len(workbooks), "metrics": metrics.to_dict()}, indent=1))
    print(json.dumps(final["summary"], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
