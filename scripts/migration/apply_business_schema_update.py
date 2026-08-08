from __future__ import annotations

import argparse
from pathlib import Path

from bctc_ai.schema.business_update import (
    BUSINESS_UPDATE_AUDIT,
    apply_business_schema_update,
    verify_business_schema_update,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create or verify the authorized CDKT/KQKD/LCTT/TM v2 schema workbooks"
    )
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--audit", type=Path, default=Path(BUSINESS_UPDATE_AUDIT))
    parser.add_argument("--verify-only", action="store_true")
    arguments = parser.parse_args()
    root = arguments.project_root.resolve()
    audit = arguments.audit if arguments.audit.is_absolute() else root / arguments.audit
    if arguments.verify_only:
        record = verify_business_schema_update(root, audit)
        print("BUSINESS_SCHEMA_UPDATE_STATUS=PASS")
        for statement, workbook in record["workbooks"].items():
            print(f"{statement}_V2_SHA256={workbook['after_sha256']}")
        return
    result = apply_business_schema_update(root, audit_path=audit)
    print(f"BUSINESS_SCHEMA_UPDATE_STATUS={result.status}")
    for statement, digest in result.workbook_sha256.items():
        print(f"{statement}_V2_SHA256={digest}")
    print(f"BUSINESS_SCHEMA_UPDATE_AUDIT={result.audit_path}")


if __name__ == "__main__":
    main()
