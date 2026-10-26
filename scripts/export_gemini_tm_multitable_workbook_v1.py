"""Export one authenticated stored MULTITABLE document; no provider/DB writes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from bctc_ai.export.gemini_tm_multitable_bridge_v1 import (
    authenticate_ref_v1,
    export_tm_multitable_store_document_v1,
    pinned_bytes_v1,
    strict_json_v1,
)


def main() -> int:
    if sys.version_info[:2] != (3, 12):
        print("FAIL_CLOSED: project export requires Python 3.12", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--request-sha256", required=True)
    parser.add_argument("--request-size-bytes", type=int, required=True)
    args = parser.parse_args()
    try:
        reference = authenticate_ref_v1({"path": str(args.request), "sha256": args.request_sha256,
                                         "size_bytes": args.request_size_bytes})
        payload = pinned_bytes_v1(reference)
        # Reauthenticate after the read; no guessed JSON receipt fields.
        authenticate_ref_v1(reference)
        request = strict_json_v1(payload)
        result = export_tm_multitable_store_document_v1(request=request)
    except (ValueError, RuntimeError, OSError, KeyError, TypeError, IndexError) as exc:
        print(f"FAIL_CLOSED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
