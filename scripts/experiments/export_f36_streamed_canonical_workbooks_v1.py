"""Publish experimental F36 workbooks from a real checked streamed store.

The small pinned request contains store_ref, output_directory, spool_report,
compiled_specs, implementation_refs and producer_refs. It contains no whole
sweep/trial BLOB. No provider calls or SQL writes are made.
"""
from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

from bctc_ai.notes.f36_streamed_workbooks_v1 import export_f36_streamed_canonical_workbooks_v1

MAX_REQUEST_BYTES = 16 * 1024 * 1024


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--expected-request-sha256", required=True)
    args = parser.parse_args(argv)
    with args.request.open("rb") as handle:
        raw = handle.read(MAX_REQUEST_BYTES + 1)
    if len(raw) > MAX_REQUEST_BYTES or sha256(raw).hexdigest() != args.expected_request_sha256:
        raise ValueError("bounded exact request SHA-256 required")
    request = json.loads(raw)
    if type(request) is not dict or set(request) != {"store_ref", "output_directory", "spool_report", "compiled_specs",
                                                   "implementation_refs", "producer_refs"}:
        raise ValueError("exact streamed workbook request fields required")
    result = export_f36_streamed_canonical_workbooks_v1(**request)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
