from __future__ import annotations

import argparse
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

    backup = subparsers.add_parser("backup")
    backup.add_argument("--destination", required=True)
    backup.add_argument("--off-machine", action="store_true")
    backup.set_defaults(handler=_run_backup)

    restore = subparsers.add_parser("restore-test")
    restore.add_argument("--archive", required=True)
    restore.add_argument("--manifest", required=True)
    restore.set_defaults(handler=_run_restore_test)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    raise SystemExit(args.handler(args))
