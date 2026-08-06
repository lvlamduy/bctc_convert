from __future__ import annotations

import argparse
from pathlib import Path

from bctc_ai.schema.append_only import append_tm_1944, verify_tm_1944_append


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply or verify the Q-BOOT-004 append-only TM schema migration"
    )
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument(
        "--audit",
        type=Path,
        default=Path("data/registered/schema_append_1944.json"),
    )
    parser.add_argument("--verify-only", action="store_true")
    arguments = parser.parse_args()
    root = arguments.project_root.resolve()
    audit = arguments.audit if arguments.audit.is_absolute() else root / arguments.audit
    if arguments.verify_only:
        record = verify_tm_1944_append(root, audit)
        print("TM_1944_APPEND_STATUS=PASS")
        print(f"TM_1944_WORKBOOK_SHA256={record['workbook']['after_sha256']}")
        return
    result = append_tm_1944(root, audit_path=audit)
    print(f"TM_1944_APPEND_STATUS={result.status}")
    print(f"TM_1944_WORKBOOK_SHA256={result.workbook_sha256}")
    print(f"TM_1944_AUDIT={result.audit_path}")


if __name__ == "__main__":
    main()
