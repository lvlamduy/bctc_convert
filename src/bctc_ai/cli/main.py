from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path


def _project_root(value: str | None) -> Path:
    return Path(value or ".").resolve()


def _run_audit(args: argparse.Namespace) -> int:
    from bctc_ai.reporting.bootstrap import run_bootstrap

    result = run_bootstrap(_project_root(args.project_root), workers=args.workers)
    # This output contract is intentionally exact; automation consumes it.
    print(f"BOOTSTRAP_COMPLETE={result.recovery_audit}")
    print(f"PROJECT_GOAL={result.project_goal}")
    print(f"QUESTIONS={result.questions}")
    print(f"BACKUP_STATUS={result.backup_status}")
    return 0


def _not_ready(args: argparse.Namespace) -> int:
    print(
        f"{args.command}: fail-closed placeholder; this phase has not passed its acceptance tests",
        file=sys.stderr,
    )
    return 2


def _run_backup(args: argparse.Namespace) -> int:
    from bctc_ai.storage.backup import create_backup

    root = _project_root(args.project_root)
    result = create_backup(root, Path(args.destination), off_machine=args.off_machine)
    print(f"BACKUP_ARCHIVE={result.archive}")
    print(f"RESTORE_TEST={'PASS' if result.restored_and_verified else 'FAIL'}")
    print(f"BACKUP_STATUS={result.development_status}_DEVELOPMENT")
    print(f"BACKUP_PRODUCTION_STATUS={result.production_status}")
    return 0 if result.restored_and_verified else 1


def _run_restore_test(args: argparse.Namespace) -> int:
    from bctc_ai.storage.backup import restore_test

    passed = restore_test(Path(args.archive).resolve(), Path(args.manifest).resolve())
    print(f"RESTORE_TEST={'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


def _run_s3_backup(args: argparse.Namespace) -> int:
    from bctc_ai.storage.s3_snapshot import create_s3_snapshot

    root = _project_root(args.project_root)
    result = create_s3_snapshot(
        root,
        config_path=(root / args.config).resolve(),
        staging_root=Path(args.staging),
        restore_temp_root=Path(args.restore_temp_root) if args.restore_temp_root else None,
        full_content_stream_restore=args.full_content_restore,
        workers=args.workers,
        progress=print,
    )
    print(f"S3_SNAPSHOT_ID={result.snapshot_id}")
    print(f"S3_MANIFEST_KEY={result.manifest_key}")
    print(f"S3_MANIFEST_SHA256={result.manifest_sha256}")
    print(f"S3_RUN_RECORD={result.run_record_path}")
    print(f"S3_OFF_MACHINE_STATUS={result.off_machine_status}")
    print(f"S3_RESTORE_STATUS={result.restore_status}")
    print(f"S3_PRODUCTION_STATUS={result.production_status}")
    return 0 if result.off_machine_status == "PASS" else 1


def _run_s3_offload(args: argparse.Namespace) -> int:
    from bctc_ai.storage.s3_snapshot import OffloadResult, offload_local_assets

    root = _project_root(args.project_root)
    result = offload_local_assets(
        root,
        config_path=(root / args.config).resolve(),
        manifest_path=Path(args.manifest),
        run_record_path=Path(args.run_record),
        asset_classes=args.asset_class,
        apply=args.apply,
        progress=print,
    )
    if isinstance(result, OffloadResult):
        print("S3_OFFLOAD_STATUS=PASS")
        print(f"S3_OFFLOAD_REMOVED_FILES={result.removed_file_count}")
        print(f"S3_OFFLOAD_REMOVED_BYTES={result.removed_bytes}")
        print(f"S3_OFFLOAD_RECORD={result.record_path}")
        print(f"S3_OFFLOAD_RECORD_KEY={result.record_key}")
    else:
        print("S3_OFFLOAD_STATUS=DRY_RUN_PASS")
        print(f"S3_OFFLOAD_PLANNED_FILES={result['file_count']}")
        print(f"S3_OFFLOAD_PLANNED_BYTES={result['bytes']}")
    return 0


def _run_s3_hydrate(args: argparse.Namespace) -> int:
    from bctc_ai.storage.s3_snapshot import hydrate_from_snapshot

    root = _project_root(args.project_root)
    result = hydrate_from_snapshot(
        root,
        config_path=(root / args.config).resolve(),
        manifest_key=args.manifest_key,
        manifest_sha256=args.manifest_sha256,
        logical_paths=args.logical_path,
        asset_classes=args.asset_class,
        progress=print,
    )
    print("S3_HYDRATE_STATUS=PASS")
    print(f"S3_HYDRATE_RESTORED_FILES={result.restored_file_count}")
    print(f"S3_HYDRATE_REUSED_FILES={result.reused_file_count}")
    print(f"S3_HYDRATE_RESTORED_BYTES={result.restored_bytes}")
    return 0


def _run_history_index(args: argparse.Namespace) -> int:
    from bctc_ai.reference.historical import build_historical_weak_reference

    mongo_uri = os.environ.get(args.mongo_uri_env)
    if not mongo_uri:
        print(
            f"history-index: environment variable {args.mongo_uri_env!r} is not set",
            file=sys.stderr,
        )
        return 2
    result = build_historical_weak_reference(
        _project_root(args.project_root),
        mongo_uri=mongo_uri,
        output_path=Path(args.output),
        registry_path=Path(args.registry),
        replace=args.replace,
    )
    print(f"HISTORICAL_REFERENCE_STATUS={result['status']}")
    print(f"HISTORICAL_REFERENCE_DATABASE={result['database']['path']}")
    print(f"HISTORICAL_REFERENCE_ROWS={result['cells']['count']}")
    return 0


def _run_review_audit(args: argparse.Namespace) -> int:
    from bctc_ai.reference.human_review import (
        load_human_review_registry,
        verify_human_review_source_files,
    )

    root = _project_root(args.project_root)
    policy_path = Path(args.policy)
    if not policy_path.is_absolute():
        policy_path = root / policy_path
    registry = load_human_review_registry(policy_path, root)
    sources = verify_human_review_source_files(
        registry,
        root,
        require_present=not args.allow_missing_sources,
    )
    print("HUMAN_REVIEW_STATUS=PASS")
    print(f"HUMAN_REVIEW_ID={registry.review_id}")
    print(f"HUMAN_REVIEW_DOCUMENTS={len(registry.documents)}")
    print(f"HUMAN_REVIEW_DECISIONS={len(registry.decisions)}")
    print(f"HUMAN_REVIEW_SOURCES_PRESENT={sum(source.present for source in sources)}")
    return 0


def _parse_pages(value: str | None) -> set[int] | None:
    if not value:
        return None
    result: set[int] = set()
    for token in value.split(","):
        token = token.strip()
        if "-" in token:
            start_text, end_text = token.split("-", 1)
            start, end = int(start_text), int(end_text)
            if end < start:
                raise ValueError(f"invalid page range: {token}")
            result.update(range(start, end + 1))
        else:
            result.add(int(token))
    return result


def _run_preprocess(args: argparse.Namespace) -> int:
    from bctc_ai.preprocessing.pipeline import preprocess_document

    run_id = args.run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_root = preprocess_document(
        _project_root(args.project_root),
        Path(args.pdf),
        run_id=run_id,
        dataset_role=args.dataset_role,
        dpi=args.dpi,
        page_numbers=_parse_pages(args.pages),
    )
    print(f"PREPROCESS_COMPLETE={run_root}")
    return 0


def _run_register(args: argparse.Namespace) -> int:
    from bctc_ai.core.contracts import DatasetRole
    from bctc_ai.core.hashing import sha256_file
    from bctc_ai.ingestion.dataset_roles import assign_dataset_role
    from bctc_ai.storage.content_store import materialize_immutable

    root = _project_root(args.project_root)
    source = Path(args.pdf).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    digest = sha256_file(source)
    relative = source.relative_to(root).as_posix() if root in source.parents else str(source)
    role = DatasetRole(args.dataset_role)
    record = assign_dataset_role(
        root / "data" / "registered" / "dataset_roles.jsonl",
        document_id=f"sha256:{digest}",
        role=role,
        source_path=relative,
    )
    immutable = None
    if args.materialize:
        immutable, _ = materialize_immutable(source, root / "data" / "immutable")
    print(f"DOCUMENT_ID={record['document_id']}")
    print(f"DATASET_ROLE={record['dataset_role']}")
    print(f"IMMUTABLE_COPY={immutable or 'NOT_MATERIALIZED'}")
    return 0


def _run_discover_statements(args: argparse.Namespace) -> int:
    from bctc_ai.document_phase.native_statement_discovery import (
        publish_registered_native_statement_discovery,
    )

    root = _project_root(args.project_root)

    def resolve(raw: str) -> Path:
        path = Path(raw)
        return path.resolve() if path.is_absolute() else (root / path).resolve()

    result = publish_registered_native_statement_discovery(
        root,
        resolve(args.pdf),
        resolve(args.policy),
        args.run_id,
        resolve(args.output),
    )
    print(f"STATEMENT_DISCOVERY_STATUS={result.payload['status']}")
    print(f"STATEMENT_DISCOVERY_ARTIFACT={result.path.relative_to(root)}")
    print(f"STATEMENT_DISCOVERY_SHA256={result.sha256}")
    print(f"STATEMENT_DISCOVERY_BYTES={result.size_bytes}")
    return 0 if result.payload["status"] == "ACCEPTED_NATIVE_TEXT_STATEMENT_DISCOVERY" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bctc-ai")
    parser.add_argument("--project-root", help="repository root; defaults to current directory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="audit environment and register supplied inputs")
    audit.add_argument("--workers", type=int, default=4)
    audit.set_defaults(handler=_run_audit)

    # Commands are registered from day one so orchestration has a stable surface.
    # Each unavailable phase fails closed instead of pretending to have succeeded.
    for command in (
        "ocr",
        "parse",
        "map",
        "validate",
        "export",
        "reference",
        "compare",
        "questions",
        "batch",
        "report",
    ):
        item = subparsers.add_parser(command)
        item.set_defaults(handler=_not_ready)

    register = subparsers.add_parser("register")
    register.add_argument("--pdf", required=True)
    register.add_argument(
        "--dataset-role",
        default="LOGIC_DEVELOPMENT",
        choices=[
            "LOGIC_DEVELOPMENT",
            "CALIBRATION",
            "UNTOUCHED_HOLDOUT",
            "VALIDATION",
            "PRODUCTION_INPUT",
        ],
    )
    register.add_argument("--materialize", action="store_true")
    register.set_defaults(handler=_run_register)

    preprocess = subparsers.add_parser("preprocess")
    preprocess.add_argument("--pdf", required=True)
    preprocess.add_argument("--run-id")
    preprocess.add_argument(
        "--dataset-role",
        default="LOGIC_DEVELOPMENT",
        choices=[
            "LOGIC_DEVELOPMENT",
            "CALIBRATION",
            "UNTOUCHED_HOLDOUT",
            "VALIDATION",
            "PRODUCTION_INPUT",
        ],
    )
    preprocess.add_argument("--dpi", type=int, default=300)
    preprocess.add_argument("--pages", help="comma-separated pages/ranges, for example 1,3-5")
    preprocess.set_defaults(handler=_run_preprocess)

    discover = subparsers.add_parser(
        "discover-statements",
        help="discover statement pages from a registered native-text PDF",
    )
    discover.add_argument("--pdf", required=True)
    discover.add_argument("--output", required=True)
    discover.add_argument("--run-id", default="registered-native-statement-discovery-v1")
    discover.add_argument(
        "--policy",
        default="config/document_phase/native-statement-discovery-v1.yaml",
    )
    discover.set_defaults(handler=_run_discover_statements)

    backup = subparsers.add_parser("backup")
    backup.add_argument("--destination", required=True)
    backup.add_argument("--off-machine", action="store_true")
    backup.set_defaults(handler=_run_backup)

    restore = subparsers.add_parser("restore-test")
    restore.add_argument("--archive", required=True)
    restore.add_argument("--manifest", required=True)
    restore.set_defaults(handler=_run_restore_test)

    s3_backup = subparsers.add_parser(
        "s3-backup", help="publish a content-addressed immutable S3 snapshot"
    )
    s3_backup.add_argument("--config", default="config/backup/s3-v1.toml")
    s3_backup.add_argument("--staging", required=True)
    s3_backup.add_argument("--restore-temp-root")
    s3_backup.add_argument("--workers", type=int)
    s3_backup.add_argument("--full-content-restore", action="store_true", default=None)
    s3_backup.set_defaults(handler=_run_s3_backup)

    s3_offload = subparsers.add_parser(
        "s3-offload", help="remove verified large local inputs after an S3 snapshot"
    )
    s3_offload.add_argument("--config", default="config/backup/s3-v1.toml")
    s3_offload.add_argument("--manifest", required=True)
    s3_offload.add_argument("--run-record", required=True)
    s3_offload.add_argument("--asset-class", action="append", required=True)
    s3_offload.add_argument("--apply", action="store_true")
    s3_offload.set_defaults(handler=_run_s3_offload)

    s3_hydrate = subparsers.add_parser(
        "s3-hydrate", help="restore selected files from an immutable S3 manifest"
    )
    s3_hydrate.add_argument("--config", default="config/backup/s3-v1.toml")
    s3_hydrate.add_argument("--manifest-key", required=True)
    s3_hydrate.add_argument("--manifest-sha256", required=True)
    s3_hydrate.add_argument("--logical-path", action="append", default=[])
    s3_hydrate.add_argument("--asset-class", action="append", default=[])
    s3_hydrate.set_defaults(handler=_run_s3_hydrate)

    history = subparsers.add_parser(
        "history-index", help="build the resolved-ID-only historical weak reference"
    )
    history.add_argument("--mongo-uri-env", default="BCTC_HISTORY_MONGO_URI")
    history.add_argument("--output", default="data/local/historical_weak_reference.duckdb")
    history.add_argument(
        "--registry",
        default="data/registered/historical_weak_reference_registry.json",
    )
    history.add_argument("--replace", action="store_true")
    history.set_defaults(handler=_run_history_index)

    review = subparsers.add_parser(
        "review-audit", help="verify the immutable hash-bound human-review calibration registry"
    )
    review.add_argument(
        "--policy",
        default="config/reference/human-review-v1.yaml",
    )
    review.add_argument(
        "--allow-missing-sources",
        action="store_true",
        help="validate tracked identities while permitting PDFs absent from a Git-only clone",
    )
    review.set_defaults(handler=_run_review_audit)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    raise SystemExit(args.handler(args))
