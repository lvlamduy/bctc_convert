from __future__ import annotations

import gzip
import struct

from bctc_ai.ingestion.mongodb_dump import read_mongodb_archive_header


def _bson_string(key: str, value: str) -> bytes:
    encoded = value.encode() + b"\x00"
    return b"\x02" + key.encode() + b"\x00" + struct.pack("<i", len(encoded)) + encoded


def test_mongodb_archive_header_metadata_is_read_without_restoring(tmp_path):
    path = tmp_path / "dump.gz"
    payload = b"prefix" + b"".join(
        [
            _bson_string("server_version", "7.0.28"),
            _bson_string("tool_version", "100.14.0"),
            _bson_string("db", "financial"),
            _bson_string("collection", "templates"),
        ]
    )
    with gzip.open(path, "wb") as stream:
        stream.write(payload)
    header = read_mongodb_archive_header(path)
    assert header.database == "financial"
    assert header.first_collection == "templates"
    assert header.server_version == "7.0.28"
    assert header.tool_version == "100.14.0"
