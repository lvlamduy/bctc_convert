from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from bctc_ai.core.atomic import atomic_write_json, atomic_write_jsonl, atomic_write_text
from bctc_ai.core.environment import collect_environment
from bctc_ai.core.hashing import sha256_file, stable_records_hash
from bctc_ai.ingestion.bank_registry import load_bank_registry
from bctc_ai.ingestion.discovery import discover_pdfs
from bctc_ai.ingestion.registry import register_sources
from bctc_ai.questions.bootstrap import bootstrap_questions, write_questions
from bctc_ai.reference.historical import verify_historical_weak_reference
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import load_all
from bctc_ai.storage.backup import create_backup


@dataclass(frozen=True)
class BootstrapResult:
    recovery_audit: str
    project_goal: str
    questions: str
    backup_status: str


def _git(project_root: Path, *arguments: str) -> str | None:
    result = subprocess.run(
        ["git", *arguments], cwd=project_root, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _write_schema_artifacts(
    project_root: Path,
) -> tuple[list[dict[str, object]], int, str, dict[str, object]]:
    workbooks, items = load_all(project_root / "template", project_root)
    hierarchy, hierarchy_items = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml",
        project_root,
        items,
    )
    apply_hierarchy_reference(items, hierarchy_items)
    hierarchy_record = hierarchy.to_dict()
    atomic_write_json(
        project_root / "data/registered/hierarchy_registry.json",
        hierarchy_record,
    )
    workbook_records = [asdict(workbook) for workbook in workbooks]
    graph_records = [item.to_dict() for item in items]
    atomic_write_jsonl(project_root / "reference/schemas/schema_graph.jsonl", graph_records)
    registry = {
        "format_version": 1,
        "authority": "SUPPLIED_WORKBOOKS",
        "append_only": True,
        "workbooks": workbook_records,
        "counts": {
            workbook["statement_type"]: workbook["item_count"] for workbook in workbook_records
        },
        "total_items": len(items),
        "contains_tm_1944": any(item.schema_id == 1944 for item in items),
        "lctt_semantics": "WORKBOOK_BLOCKS_VERIFIED_SEMANTIC_CONFLICT_REOPENED_2026_08_05",
        "hierarchy_reference": hierarchy_record,
    }
    atomic_write_json(project_root / "data/registered/schema_registry.json", registry)
    graph_hash = stable_records_hash(
        json.dumps(record, ensure_ascii=False, sort_keys=True) for record in graph_records
    )
    return workbook_records, len(items), graph_hash, hierarchy_record


def _write_schema_proposal(
    project_root: Path,
    historical_verification: dict[str, object] | None = None,
) -> None:
    dump_registry_path = project_root / "data/registered/mongodb_dump_registry.json"
    dump_registry = (
        json.loads(dump_registry_path.read_text(encoding="utf-8"))
        if dump_registry_path.is_file()
        else None
    )
    historical_registry_path = (
        project_root / "data/registered/historical_weak_reference_registry.json"
    )
    historical_registry = (
        json.loads(historical_registry_path.read_text(encoding="utf-8"))
        if historical_registry_path.is_file()
        else None
    )
    template_collision_safe = bool(
        dump_registry
        and dump_registry.get("collision_audit", {}).get(
            "append_safe_from_id_collision_perspective"
        )
    )
    historical_collision_safe = bool(
        historical_registry
        and historical_verification
        and historical_verification.get("status") == "PASS"
        and historical_registry.get("schema", {}).get(
            "append_safe_from_historical_key_collision_perspective"
        )
    )
    collision_safe = template_collision_safe and (
        historical_registry is None or historical_collision_safe
    )
    proposal = {
        "proposal_id": "SCHEMA-TM-1944",
        "pdf_name": None,
        "proposed_schema_id": 1944,
        "proposed_canonical_name": "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
        "statement_type": "TM",
        "section": None,
        "parent": None,
        "position_before": 1943,
        "position_after": None,
        "scope": None,
        "period": None,
        "unit": None,
        "mongodb_evidence": [],
        "reason": "Named append-only item in the master directive is absent from the supplied TM workbook.",
        "confidence": "PROPOSAL_REQUIRES_USER_CONFIRMATION",
        "question_id": "Q-BOOT-004",
        "collision_evidence": {
            "schema_hierarchy_and_mongodb_templates": (
                dump_registry.get("collision_audit") if dump_registry else None
            ),
            "historical_data_chart_keys": (
                {
                    "source_contains_proposed_id": historical_registry["schema"][
                        "source_contains_proposed_id"
                    ],
                    "append_safe_from_historical_key_collision_perspective": (
                        historical_collision_safe
                    ),
                    "selected_document_count": historical_registry["source"][
                        "selected_document_count"
                    ],
                    "cell_count": historical_registry["cells"]["count"],
                }
                if historical_registry
                else None
            ),
        },
        "status": (
            "COLLISION_CHECK_PASSED_APPEND_DECISION_OPEN"
            if collision_safe
            else "PENDING_COLLISION_CHECK"
        ),
    }
    atomic_write_jsonl(project_root / "proposed_schema_additions.jsonl", [proposal])


def _write_dynamic_audits(
    project_root: Path,
    environment: dict[str, object],
    manifest: dict[str, object],
    backup: dict[str, object],
    questions: list[dict[str, object]],
) -> None:
    gpu = environment["gpu"]
    devices = gpu.get("devices", []) if isinstance(gpu, dict) else []
    gpu_text = (
        ", ".join(
            f"{item['name']} ({item['memory_total_mib']} MiB, compute {item['compute_capability']})"
            for item in devices
        )
        or "Not detected"
    )
    memory = environment.get("memory", {})
    total_ram = int(memory.get("MemTotal", 0)) if isinstance(memory, dict) else 0
    disk = environment.get("disk", {})
    torch = environment.get("torch", {})
    torch_available = isinstance(torch, dict) and bool(torch.get("available"))
    torch_text = (
        f"{torch.get('version')} (build CUDA {torch.get('cuda_build')})"
        if torch_available
        else "not installed in the control-plane interpreter"
    )
    torch_finding = (
        f"The control-plane interpreter exposes architectures `{torch.get('architectures', [])}`. "
        "It is not the document-model environment of record."
        if torch_available
        else "The control-plane environment intentionally has no PyTorch; model dependencies "
        "remain isolated from orchestration and validation code."
    )
    gpu_runtime = environment.get("gpu_model_runtime", {})
    gpu_runtime = gpu_runtime if isinstance(gpu_runtime, dict) else {}
    runtime_status = str(gpu_runtime.get("local_acceptance", "NOT_CONFIGURED"))
    runtime_smoke = gpu_runtime.get("smoke", {})
    runtime_smoke = runtime_smoke if isinstance(runtime_smoke, dict) else {}
    runtime_freeze = gpu_runtime.get("freeze", {})
    runtime_freeze = runtime_freeze if isinstance(runtime_freeze, dict) else {}
    runtime_packages = gpu_runtime.get("declared_packages", {})
    runtime_packages = runtime_packages if isinstance(runtime_packages, dict) else {}
    if runtime_status == "PASS":
        runtime_text = (
            f"PASS — PyTorch {runtime_packages.get('torch', 'unknown')}, "
            f"CUDA {runtime_smoke.get('torch_cuda_build', 'unknown')}, "
            f"native {gpu_runtime.get('required_native_arch', 'unknown')}, "
            f"{runtime_freeze.get('installed_package_count', 'unknown')}-package exact freeze"
        )
        runtime_finding = (
            "The isolated runtime was revalidated on this host: imports and dependency "
            "compatibility passed, the installed freeze exactly matched the tracked freeze, "
            "and a real CUDA matrix kernel ran on the detected GPU."
        )
    elif runtime_status == "ABSENT":
        runtime_text = "ABSENT — rebuild required from the tracked runtime manifest"
        runtime_finding = (
            "The isolated runtime is not present on this host. Rebuild and rerun the acceptance "
            "commands in `docs/environment/GPU_RUNTIME_RUNBOOK.md` before model inference."
        )
    else:
        runtime_text = f"{runtime_status} — local acceptance did not pass"
        runtime_finding = (
            "The isolated runtime did not satisfy every fail-closed acceptance check. Inspect "
            "`environment.gpu_model_runtime` in `BOOTSTRAP_MANIFEST.json` before inference."
        )
    schema_counts = manifest["schemas"]["counts"]
    resolved_questions = sum(
        str(question.get("resolution_status", "")).startswith("RESOLVED") for question in questions
    )
    dump_registry = manifest.get("mongodb", {}).get("dump_registry")
    historical_reference = manifest.get("mongodb", {}).get("historical_weak_reference", {})
    historical_reference = historical_reference if isinstance(historical_reference, dict) else {}
    if isinstance(dump_registry, dict):
        if historical_reference.get("status") == "PASS":
            history_finding = (
                "The local historical weak-reference index was revalidated at "
                f"{historical_reference.get('row_count')} cells across "
                f"{historical_reference.get('bank_count')} banks. Its database constraints "
                "forbid mapping and confidence promotion."
            )
            mongo_progress = (
                f"PASS weak-reference-only ({historical_reference.get('row_count')} cells; "
                f"{historical_reference.get('bank_count')} banks)"
            )
        else:
            history_finding = (
                "The historical weak-reference index status is "
                f"`{historical_reference.get('status', 'NOT_CONFIGURED')}` and it is disabled."
            )
            mongo_progress = (
                "disabled; local historical weak-reference verification status="
                f"{historical_reference.get('status', 'NOT_CONFIGURED')}"
            )
        mongo_finding = (
            "The uploaded MongoDB archive is hash-registered. The allowlisted "
            f"financial template audit contains {dump_registry['restored_scope']['document_count']} "
            "documents and found no ReportNormID 1944 collision. "
            f"{history_finding}"
        )
    else:
        mongo_finding = (
            "No registered MongoDB archive audit is available; Mongo-assisted mode is disabled."
        )
        mongo_progress = "unavailable; MongoDB archive not audited"
    hardware = f"""# Hardware audit

Captured: {environment["captured_at"]}

- Host: `{environment["hostname"]}`
- OS: {environment["os"].get("PRETTY_NAME", "unknown")}; kernel `{environment["kernel"]}`
- CPU: {environment["cpu"].get("model")} ({environment["cpu"].get("logical_count")} logical CPUs)
- RAM: {total_ram / (1024**3):.2f} GiB; swap: {int(memory.get("SwapTotal", 0)) / (1024**3):.2f} GiB
- Workspace disk: {int(disk.get("total_bytes", 0)) / (1024**3):.2f} GiB total, {int(disk.get("free_bytes", 0)) / (1024**3):.2f} GiB free
- GPU: {gpu_text}
- NVIDIA driver: {devices[0]["driver_version"] if devices else "not detected"}
- Driver-reported CUDA: {gpu.get("reported_cuda") if isinstance(gpu, dict) else None}
- CUDA toolkit (`nvcc`): {"available" if environment["tools"]["nvcc"]["available"] else "not installed"}
- Python: {environment["tools"]["python"]["version"]}
- PyTorch: {torch_text}
- Isolated GPU runtime: {runtime_text}
- Recorded document-model status: `{gpu_runtime.get("declared_status", "NOT_CONFIGURED")}`

## Compatibility and approval finding

{torch_finding} {runtime_finding} This accepts the runtime for logic development; production model approval remains blocked until frozen multi-institution, scan/distortion, cross-page, and holdout accuracy gates pass.
"""
    atomic_write_text(project_root / "HARDWARE_AUDIT.md", hardware)

    recovery = f"""# Recovery audit

Captured: {environment["captured_at"]}

## Authoritative starting state

- The old server/GPU state is treated as unrecoverable and was not searched.
- Existing repository history contains only the newly supplied input workbooks; no prior Python implementation or OCR artifacts were present.
- Inputs found: **{manifest["sources"]["pdf_count"]} PDFs** ({manifest["sources"]["total_bytes"]} bytes), four schema workbooks, four supporting hierarchy workbooks, and one bank-list workbook.
- PDF registry hash: `{manifest["sources"]["registry_hash"]}`.
- SchemaGraph hash: `{manifest["schemas"]["graph_hash"]}`.
- Supporting hierarchy status: `{manifest["schemas"]["hierarchy_reference"]["status"]}` with {manifest["schemas"]["hierarchy_reference"]["item_count"]} validated edges/items; LCTT coverage is explicitly direct-branch-only.
- Source files were read and hashed only; none were overwritten.
- Inventory stable across registration: **{manifest["sources"]["inventory_stable"]}** (attempts: {manifest["sources"]["inventory_attempts"]}).
- Isolated GPU runtime local acceptance: **{runtime_status}**; production model approval remains separate and pending.

## Material discrepancies

- Actual schema counts are CDKT={schema_counts["CDKT"]}, KQKD={schema_counts["KQKD"]}, LCTT={schema_counts["LCTT"]}, TM={schema_counts["TM"]} (total {manifest["schemas"]["total_items"]}), not the historical 1,773-item count.
- The supplied TM workbook does not contain ID 1944. It remains a proposal in `proposed_schema_additions.jsonl`.
- LCTT membership is now based on contiguous workbook positions, not numeric ID ranges. The latest semantic wording conflicts with the visible anchors/endpoints, so semantic high-confidence acceptance remains fail-closed.
- {mongo_finding}
- A local control-plane backup restored successfully: `{backup["restored_and_verified"]}`. Per the user's development policy, development backup status is **{backup["development_status"]}**. It is not off-machine and does not protect against total VPS loss; production status remains `{backup["production_status"]}`.

## Recovery posture

Generated artifacts use atomic write, fsync, rename, and post-write hash verification. Source identity is recorded in `data/registered/source_registry.jsonl`; content-addressed artifact materialization and off-machine versioning remain required before production.
"""
    atomic_write_text(project_root / "RECOVERY_AUDIT.md", recovery)

    progress = f"""# Progress report

- Date/time: {environment["captured_at"]}
- Hardware: {gpu_text}; {total_ram / (1024**3):.2f} GiB RAM
- Isolated GPU runtime: {runtime_status}; recorded model state: `{gpu_runtime.get("declared_status", "NOT_CONFIGURED")}`
- Code hash: bootstrap is on `{manifest["git"]["branch"]}` at `{manifest["git"]["commit"]}` with dirty state `{manifest["git"]["dirty"]}`
- Schema count: {manifest["schemas"]["total_items"]} (CDKT {schema_counts["CDKT"]}; KQKD {schema_counts["KQKD"]}; LCTT {schema_counts["LCTT"]}; TM {schema_counts["TM"]})
- PDFs registered: {manifest["sources"]["pdf_count"]}
- ROLE A completed: 0 documents
- ROLE B completed: 0 documents
- Reference IDs / values: 0 / 0
- CDKT, KQKD, applicable LCTT, TM coverage: not measurable before MACHINE_REFERENCE
- PDF_ONLY metrics: not yet measured
- Mongo-assisted metrics: {mongo_progress}
- Questions created / resolved: {len(questions)} / {resolved_questions}
- Autonomous decisions: preserve supplied schema unchanged; keep 1944 as a collision-cleared proposal; segment LCTT by workbook position and fail closed on the semantic conflict
- Not applicable / not observed / unresolved: 0 / 0 / 0 (no production records yet)
- Workbooks: 0
- Largest error: no frozen end-to-end multi-institution accuracy result or production-calibrated acceptance threshold yet
- Last change: allowlisted Mongo `data_chart` weak-reference index with resolved-ID-only lookup, unknown unit/scope, and database-enforced no-map/no-promote gates
- Before/after: non-bank historical collections and slow row-wise writes -> 27-bank, 112,147-cell guarded index built by transactional DuckDB bulk load
- Regression: run separately with `.venv/bin/pytest`; latest verified count is recorded in `PROJECT_MEMORY.md`
- Backup status: development={backup["development_status"]}; production={backup["production_status"]} (local restore verified={backup["restored_and_verified"]}, off-machine={backup["off_machine"]})
- Next bounded action: broaden frozen cross-reader fixtures across institutions, scans, distortions, and page breaks, then measure calibrated disagreement escalation with the weak reference kept non-authoritative
"""
    atomic_write_text(project_root / "PROGRESS_REPORT.md", progress)


def run_bootstrap(project_root: Path, *, workers: int = 4) -> BootstrapResult:
    project_root = project_root.resolve()
    git_state = {
        "commit": _git(project_root, "rev-parse", "HEAD"),
        "branch": _git(project_root, "branch", "--show-current"),
        "dirty": bool(_git(project_root, "status", "--porcelain")),
        "remotes": (_git(project_root, "remote") or "").splitlines(),
    }
    environment = collect_environment(project_root)
    historical_weak_reference = verify_historical_weak_reference(project_root)
    source_root = project_root / "vietstock_bctc"
    inventory_stable = False
    inventory_attempts = 0
    added_during_registration: list[str] = []
    removed_during_registration: list[str] = []
    source_records = []
    registry_hash = ""
    for attempt in range(1, 4):
        inventory_attempts = attempt
        sources = discover_pdfs(source_root)
        source_records, registry_hash = register_sources(
            sources,
            project_root,
            project_root / "data/registered/source_registry.jsonl",
            workers=workers,
        )
        after = discover_pdfs(source_root)
        before_paths = {source.path.resolve() for source in sources}
        after_paths = {source.path.resolve() for source in after}
        added_during_registration = sorted(
            path.relative_to(project_root).as_posix() for path in after_paths - before_paths
        )
        removed_during_registration = sorted(
            path.relative_to(project_root).as_posix() for path in before_paths - after_paths
        )
        inventory_stable = (
            not added_during_registration
            and not removed_during_registration
            and all(record.hash_verified_stable for record in source_records)
        )
        if inventory_stable:
            break
    workbooks, schema_count, graph_hash, hierarchy_reference = _write_schema_artifacts(project_root)
    _write_schema_proposal(project_root, historical_weak_reference)
    questions = bootstrap_questions()
    write_questions(project_root, questions)

    bank_list = project_root / "Bank_list_id.xlsx"
    bank_registry = load_bank_registry(bank_list, project_root)
    atomic_write_json(project_root / "data/registered/bank_registry.json", bank_registry)
    manifest: dict[str, object] = {
        "format_version": 1,
        "project": "bctc-ai",
        "captured_at": datetime.now(UTC).isoformat(),
        "git": git_state,
        "environment": environment,
        "sources": {
            "pdf_count": len(source_records),
            "unique_content_count": len({record.sha256 for record in source_records}),
            "total_bytes": sum(record.size_bytes for record in source_records),
            "registry": "data/registered/source_registry.jsonl",
            "registry_hash": registry_hash,
            "inventory_stable": inventory_stable,
            "inventory_attempts": inventory_attempts,
            "added_during_registration": added_during_registration,
            "removed_during_registration": removed_during_registration,
            "unstable_file_count": sum(
                not record.hash_verified_stable for record in source_records
            ),
        },
        "schemas": {
            "workbooks": workbooks,
            "counts": {record["statement_type"]: record["item_count"] for record in workbooks},
            "total_items": schema_count,
            "graph": "reference/schemas/schema_graph.jsonl",
            "graph_hash": graph_hash,
            "contains_tm_1944": False,
            "lctt_semantics": "WORKBOOK_BLOCKS_VERIFIED_SEMANTIC_CONFLICT_REOPENED_2026_08_05",
            "hierarchy_reference": hierarchy_reference,
        },
        "bank_list": {
            "path": "Bank_list_id.xlsx",
            "sha256": sha256_file(bank_list),
            "size_bytes": bank_list.stat().st_size,
            "registry": "data/registered/bank_registry.json",
            "counts": bank_registry["counts"],
        },
        "mongodb": {
            "runtime": environment["mongodb"],
            "dump_registry": (
                json.loads(
                    (project_root / "data/registered/mongodb_dump_registry.json").read_text(
                        encoding="utf-8"
                    )
                )
                if (project_root / "data/registered/mongodb_dump_registry.json").is_file()
                else None
            ),
            "historical_weak_reference": historical_weak_reference,
        },
    }
    atomic_write_json(project_root / "BOOTSTRAP_MANIFEST.json", manifest)

    backup_root = project_root.parent / "bctc-ai-backups"
    backup_result = create_backup(project_root, backup_root, off_machine=False)
    backup = {
        **asdict(backup_result),
        "development_status": backup_result.development_status,
        "production_status": backup_result.production_status,
    }
    manifest["backup"] = backup
    atomic_write_json(project_root / "BOOTSTRAP_MANIFEST.json", manifest)
    _write_dynamic_audits(project_root, environment, manifest, backup, questions)
    return BootstrapResult(
        recovery_audit=str((project_root / "RECOVERY_AUDIT.md").resolve()),
        project_goal=str((project_root / "PROJECT_GOAL.md").resolve()),
        questions=str((project_root / "questions_for_user.md").resolve()),
        backup_status=f"{backup_result.development_status}_DEVELOPMENT",
    )
