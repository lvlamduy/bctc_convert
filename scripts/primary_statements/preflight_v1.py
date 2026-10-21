"""Evidence-producing preflight for the PRIMARY_STATEMENTS worktree.

Every gate is recomputed from the actual inputs of this run. Nothing is copied
from an older receipt. Source databases are opened read-only; PDFs are only
hashed and counted, never rendered or re-extracted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

MIGRATION_BASE = "8efd618b6c77f0cdbb402a440e7ba3b3549184f1"
FROZEN = {
    "src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py": (
        "bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2"
    ),
    "scripts/experiments/run_gemini_json_multitable_hierarchical_accounting_family_v1.py": (
        "d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5"
    ),
}
CORPORA = {
    "full271": {
        "root": "/srv/bctc-restore/dev-shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts",
        "index": "current-corpus-manifest-indexes/"
        "8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a.json",
        "index_sha256": "969ff5f80732c39e4b7543ca1f5c1e5b5b827260f19981ed02945fe0c7379219",
        "db": "current-corpus-freeze-inputs/"
        "store-ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7.sqlite3",
        "db_sha256": "ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7",
        "db_size": 573145088,
        "documents": 271,
    },
    "common204": {
        "root": "/srv/bctc-restore/dev-shm/bctc-ai-27-bank-family-live-v1",
        "index": "current-corpus-manifest-indexes/"
        "32c474f657f9484244e9675a0ca4801cb49b4923971dfb7bea17081904154747.json",
        "index_sha256": "acc1d08e45e5a05925c434ae1c96fd6bc481a0e6ca61fc9f78e155efca7365b1",
        "db": "current-corpus-freeze-inputs/"
        "store-a14904a492e6beae165b81f7aa1738352a9824e113f1b163a46ee277d37e0220.sqlite3",
        "db_sha256": "a14904a492e6beae165b81f7aa1738352a9824e113f1b163a46ee277d37e0220",
        "db_size": 553984000,
        "documents": 204,
    },
}
PDF_ROOT = Path("/mnt/d/bctc_bank/restore-20260905T014806Z/source")
PDF_INVENTORY = Path("/srv/bctc-receipts/pdf-inventory-v2/SOURCE_PDF_BYTE_PAGE_INVENTORY_2026-09-05.json")
PDF_INVENTORY_SHA256 = "f8f619280c712c872599730958012f56a115a6ea328f268c587ac6120493fc15"
TEMPLATES = ("CDKT", "KQKD", "LCTT")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(4 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _git_command() -> list[str]:
    # A Windows-created worktree stores a Windows gitdir; use Windows git via WSL interop.
    if (ROOT / ".git").is_file() and ":" in (ROOT / ".git").read_text(encoding="utf-8"):
        windows_root = subprocess.check_output(["wslpath", "-w", str(ROOT)], text=True).strip()
        return ["git.exe", "-C", windows_root]
    return ["git", "-C", str(ROOT)]


def _git(*parts: str) -> str:
    return subprocess.check_output([*_git_command(), *parts], text=True).strip()


def _gate(results: dict, name: str, passed: bool, evidence: dict) -> None:
    results[name] = {"status": "PASS" if passed else "FAIL", "evidence": evidence}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-commit", required=True)
    parser.add_argument("--allowed-dirty-prefix", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--skip-pdf-hash", action="store_true")
    args = parser.parse_args()
    gates: dict[str, dict] = {}

    head = _git("rev-parse", "HEAD")
    ancestor = subprocess.run(
        [*_git_command(), "merge-base", "--is-ancestor", MIGRATION_BASE, head]
    ).returncode == 0
    status = [line for line in _git("status", "--porcelain").splitlines() if line]
    dirty_outside = [
        line for line in status
        if not any(line[3:].startswith(prefix) for prefix in args.allowed_dirty_prefix)
    ]
    _gate(gates, "git_base_worktree", head == args.base_commit and ancestor and not dirty_outside, {
        "head": head, "base_commit": args.base_commit, "migration_base_is_ancestor": ancestor,
        "branch": _git("branch", "--show-current"), "status_porcelain": status,
        "dirty_outside_allowed_prefixes": dirty_outside,
    })

    import bctc_ai

    origin = Path(bctc_ai.__file__).resolve()
    _gate(gates, "runtime_import_origin", sys.version_info[:2] == (3, 12) and ROOT / "src" in origin.parents, {
        "python": sys.version, "executable": sys.executable, "platform": platform.platform(),
        "bctc_ai_origin": str(origin), "dont_write_bytecode": sys.dont_write_bytecode,
    })

    from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
    from bctc_ai.schema.registry import load_all

    try:
        workbooks, items = load_all(ROOT / "template", ROOT)
        _, hierarchy = load_hierarchy_reference(ROOT / "config/schemas/hierarchy_reference.yaml", ROOT, items)
        apply_hierarchy_reference(items, hierarchy)
        counts = {st: sum(item.statement_type == st for item in items) for st in ("CDKT", "KQKD", "LCTT", "TM")}
        template_hashes = {wb.statement_type: wb.sha256 for wb in workbooks}
        ok = counts == {"CDKT": 99, "KQKD": 25, "LCTT": 110, "TM": 1721} and len(items) == 1955
        _gate(gates, "schema_template_pins", ok, {
            "revision": "UNIVERSAL_BANK_BCTC_SCHEMA@6076", "counts": counts, "item_count": len(items),
            "template_sha256": template_hashes,
            "sources_yaml_sha256": _sha256(ROOT / "config/schemas/sources.yaml"),
            "lctt_rules_sha256": _sha256(ROOT / "config/mapping/lctt-v2.yaml"),
        })
    except Exception as exc:  # noqa: BLE001 - recorded as a failed gate
        _gate(gates, "schema_template_pins", False, {"error": repr(exc)})

    _gate(gates, "frozen_shared_files", all(_sha256(ROOT / p) == d for p, d in FROZEN.items()), {
        p: {"expected": d, "actual": _sha256(ROOT / p)} for p, d in FROZEN.items()
    })

    from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import (
        validate_current_corpus_manifest_index_v1,
    )

    inventory_raw = PDF_INVENTORY.read_bytes()
    inventory = json.loads(inventory_raw)
    by_path = {record["logical_path"]: record for record in inventory["records"]}
    for name, corpus in CORPORA.items():
        root = Path(corpus["root"])
        index_path = root / corpus["index"]
        db_path = root / corpus["db"]
        index_sha = _sha256(index_path)
        index = validate_current_corpus_manifest_index_v1(json.loads(index_path.read_bytes()))
        db_sha = _sha256(db_path)
        connection = sqlite3.connect(f"file:{db_path}?mode=ro&immutable=1", uri=True)
        try:
            quick = connection.execute("PRAGMA quick_check").fetchall()
            fk = connection.execute("PRAGMA foreign_key_check").fetchall()
            store_pages = connection.execute("SELECT count(*) FROM page_json_version").fetchone()[0]
        finally:
            connection.close()
        _gate(gates, f"corpus_{name}", (
            index_sha == corpus["index_sha256"] and db_sha == corpus["db_sha256"]
            and db_path.stat().st_size == corpus["db_size"]
            and len(index["documents"]) == corpus["documents"]
            and index["database_ref"]["sha256"] == corpus["db_sha256"]
        ), {
            "index_path": str(index_path), "index_sha256": index_sha,
            "corpus_manifest_index_id": index["corpus_manifest_index_id"],
            "documents": len(index["documents"]), "pages": index["summary"]["page_count"],
            "db_path": str(db_path), "db_sha256": db_sha, "db_size": db_path.stat().st_size,
            "store_page_json_versions": store_pages,
        })
        _gate(gates, f"sqlite_integrity_{name}", quick == [("ok",)] and not fk, {
            "quick_check": [row[0] for row in quick][:5], "foreign_key_violations": len(fk),
        })
        plan_ref = index["corpus_plan_ref"]
        plan_raw = (root / plan_ref["path"]).read_bytes()
        plan_ok = hashlib.sha256(plan_raw).hexdigest() == plan_ref["sha256"] and len(plan_raw) == plan_ref["size_bytes"]
        plan_by_path = {item["document"]["relative_path"]: item["document"] for item in json.loads(plan_raw)["documents"]}
        missing, mismatched, out_of_scope, hashed = [], [], [], 0
        page_selections = []
        for document in index["documents"]:
            record = by_path.get(document["relative_path"])
            planned = plan_by_path.get(document["relative_path"])
            pdf = PDF_ROOT / document["relative_path"]
            if record is None or planned is None or not pdf.is_file():
                missing.append(document["relative_path"])
                continue
            if not record.get("production_scope_2025_current"):
                out_of_scope.append(document["relative_path"])
            selection = planned.get("page_selection")
            # The selected page frontier is the plan's, which may exclude a reviewed
            # non-Vietnamese appendix; the physical PDF page count must still match.
            selected_ok = planned["page_count"] == document["page_count"] and (
                planned.get("source_page_count", planned["page_count"]) == planned["page_count"] if selection is None else (
                    selection["included_first_physical_page"] == 1
                    and selection["included_last_physical_page"] == planned["page_count"]
                )
            )
            if selection is not None:
                page_selections.append({"path": document["relative_path"], **selection,
                                        "source_page_count": planned["source_page_count"]})
            ok = (
                plan_ok and selected_ok
                and record["sha256"] == document["source_sha256"] == planned["source_sha256"]
                and record["size_bytes"] == document["source_size_bytes"] == pdf.stat().st_size
                and record["page_count"] == planned.get("source_page_count", planned["page_count"])
            )
            if ok and not args.skip_pdf_hash:
                ok = _sha256(pdf) == document["source_sha256"]
                hashed += 1
            if not ok:
                mismatched.append(document["relative_path"])
        _gate(gates, f"pdf_coverage_{name}", not missing and not mismatched and not out_of_scope, {
            "documents": len(index["documents"]), "missing": missing, "mismatched": mismatched,
            "outside_2025_current_scope": out_of_scope, "pdf_bytes_rehashed": hashed,
            "corpus_plan_sha256_verified": plan_ok, "reviewed_page_selections": page_selections,
        })
    _gate(gates, "pdf_inventory_pin", hashlib.sha256(inventory_raw).hexdigest() == PDF_INVENTORY_SHA256, {
        "path": str(PDF_INVENTORY), "sha256": hashlib.sha256(inventory_raw).hexdigest(),
    })

    processes = subprocess.run(["ps", "-eo", "pid,args"], capture_output=True, text=True).stdout
    provider_like = [
        line.strip() for line in processes.splitlines()
        if any(token in line.lower() for token in ("openrouter", "gemini_json_first_provider", "agy", "vertex"))
        and "preflight_v1" not in line
    ]
    _gate(gates, "no_provider_job", not provider_like, {"provider_like_processes": provider_like})

    receipt = {
        "schema": "bctc-ai-primary-statements-preflight-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "worktree": str(ROOT),
        "script_sha256": _sha256(Path(__file__)),
        "gates": gates,
        "overall": "PASS" if all(g["status"] == "PASS" for g in gates.values()) else "FAIL",
        "provider_calls_performed": False,
        "source_mutations_performed": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({name: gate["status"] for name, gate in gates.items()} | {"overall": receipt["overall"]}, indent=1))
    return 0 if receipt["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
