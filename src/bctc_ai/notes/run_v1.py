"""End-to-end notes pilot run: authenticate -> evaluate families -> store -> reload -> fresh-process rebuild -> workbooks.

    python -B -m bctc_ai.notes.run_v1 --corpus full271 --output-dir NEW \
        --primary-store PATH --primary-store-sha256 SHA --git-head SHA [--families A,B] [--documents 1,2]

The rebuild runs the same evaluation in a fresh interpreter (``--rebuild-only``)
and must produce the identical cell projection hash. Metrics record SQL
queries, rows read, stage seconds and peak RSS so speed is measured with the
work done, not estimated.
"""

from __future__ import annotations

import argparse
import json
import resource
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from bctc_ai.notes.config_v1 import load_notes_config_v1
from bctc_ai.notes.engine_v1 import dispositions_v1, run_family_v1, summarize_v1
from bctc_ai.notes.export_v1 import build_notes_workbook_v1, tm_template_rows_v1
from bctc_ai.notes.kernel_v1 import NotesSource, load_primary_context_v1
from bctc_ai.notes.store_v1 import cells_projection_sha256_v1, reload_notes_store_v1, write_notes_store_v1
from bctc_ai.primary_statements.source_v1 import SourceMetrics, load_corpus_selection_v1

PROJECT_ROOT = Path(__file__).resolve().parents[3]
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
DEFAULT_FAMILIES = ("CREDIT_QUALITY", "DEPOSITS_BY_TYPE", "BY_CUSTOMER_ENTITY_TYPE")


def evaluate_v1(args, metrics: SourceMetrics, *, verify_db_bytes: bool) -> tuple[list[dict[str, Any]], dict[str, Any], Any, Any]:
    spec = CORPORA[args.corpus]
    corpus = load_corpus_selection_v1(name=args.corpus, root=Path(spec["root"]), index_relative_path=spec["index"],
                                      expected_index_sha256=spec["index_sha256"], expected_db_sha256=spec["db_sha256"],
                                      verify_db_bytes=verify_db_bytes, metrics=metrics)
    contexts = load_primary_context_v1(Path(args.primary_store), args.primary_store_sha256)
    config = load_notes_config_v1(PROJECT_ROOT)
    source = NotesSource(corpus, metrics)
    documents = set(map(int, args.documents.split(","))) if args.documents else None
    cells, summaries, dispositions = [], {}, []
    for family in args.families.split(","):
        started = time.perf_counter()
        run = run_family_v1(family, config, source, contexts, document_ordinals=documents)
        summaries[family] = {**summarize_v1(run), "seconds": round(time.perf_counter() - started, 3)}
        cells += run.cells
        dispositions += dispositions_v1(run)
    args.dispositions = dispositions
    return cells, summaries, corpus, config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", choices=sorted(CORPORA), required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--primary-store", required=True)
    parser.add_argument("--primary-store-sha256", required=True)
    parser.add_argument("--git-head", required=True)
    parser.add_argument("--families", default=",".join(DEFAULT_FAMILIES))
    parser.add_argument("--documents")
    parser.add_argument("--rebuild-only", action="store_true")
    args = parser.parse_args()
    started = time.perf_counter()
    metrics = SourceMetrics()
    if args.rebuild_only:
        cells, _summaries, _corpus, _config = evaluate_v1(args, metrics, verify_db_bytes=False)
        print(json.dumps({"cells": len(cells), "cells_sha256": cells_projection_sha256_v1(cells)}))
        return 0
    if args.output_dir is None or args.output_dir.exists():
        raise SystemExit("--output-dir must be a new directory")
    cells, summaries, corpus, config = evaluate_v1(args, metrics, verify_db_bytes=True)
    evaluated = time.perf_counter()
    manifest = {"format_version": "NOTES_PILOT_RUN_V1", "product_label": "NOTES_PILOT_EXPERIMENTAL", "git_head": args.git_head,
                "corpus": corpus.identity(), "primary_store": {"path": args.primary_store, "sha256": args.primary_store_sha256},
                "families": args.families.split(","), "documents_requested": args.documents, "config_pins": config.pins,
                "provider_calls_performed": False, "source_mutations_performed": False, "summaries": summaries}
    store = write_notes_store_v1(args.output_dir / "notes-results.sqlite3", manifest=manifest, cells=cells)
    # Denominator artifact (every retrieved table and row disposition), written once beside the store.
    with open(args.output_dir / "dispositions.json", "x", encoding="utf-8") as handle:
        json.dump(args.dispositions, handle, ensure_ascii=False, sort_keys=True, default=str)
    _manifest, reloaded = reload_notes_store_v1(args.output_dir / "notes-results.sqlite3")
    reload_status = "PASS_EXACT" if reloaded == cells else "FAIL"
    command = [sys.executable, "-B", "-m", "bctc_ai.notes.run_v1", "--corpus", args.corpus, "--primary-store", args.primary_store,
               "--primary-store-sha256", args.primary_store_sha256, "--git-head", args.git_head, "--families", args.families,
               "--rebuild-only"] + (["--documents", args.documents] if args.documents else [])
    rebuilt = json.loads(subprocess.run(command, check=True, capture_output=True, text=True).stdout.strip().splitlines()[-1])
    rebuild_status = "PASS_EXACT_CELLS" if rebuilt["cells_sha256"] == store["cells_sha256"] else "FAIL"
    template = tm_template_rows_v1(PROJECT_ROOT)
    documents = {d.ordinal: d for d in corpus.documents}
    workbooks = []
    (args.output_dir / "workbooks").mkdir()
    for ordinal in sorted({c["document_ordinal"] for c in cells}):
        document = documents[ordinal]
        doc_cells = [c for c in cells if c["document_ordinal"] == ordinal]
        payload, receipt = build_notes_workbook_v1(
            {"document_plan_id": document.document_plan_id, "relative_path": document.relative_path,
             "source_sha256": document.source_sha256}, doc_cells, template, config.pins)
        name = f"{ordinal:03d}_{document.document_plan_id.split(':')[-1][:16]}_NOTES_PILOT.xlsx"
        (args.output_dir / "workbooks" / name).write_bytes(payload)
        workbooks.append({"document_ordinal": ordinal, "file": name, **receipt})
    manifest.update({"store": store, "store_reload": reload_status, "independent_rebuild": {**rebuilt, "status": rebuild_status},
                     "workbooks": workbooks,
                     "metrics": {**metrics.to_dict(), "evaluate_seconds": round(evaluated - started, 3),
                                 "total_seconds": round(time.perf_counter() - started, 3),
                                 "peak_rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}})
    (args.output_dir / "run-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                                                       encoding="utf-8")
    print(json.dumps({"store_sha256": store["sha256"], "cells": len(cells), "reload": reload_status, "rebuild": rebuild_status,
                      "workbooks": len(workbooks), "metrics": manifest["metrics"]}, indent=1))
    return 0 if reload_status == "PASS_EXACT" and rebuild_status == "PASS_EXACT_CELLS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
