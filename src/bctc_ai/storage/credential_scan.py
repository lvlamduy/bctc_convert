from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import BinaryIO

SECRET_SCAN_POLICY = "FAIL_CLOSED_KNOWN_CREDENTIAL_FORMATS_V2"
SECRET_SCAN_BLOCK_BYTES = 1024 * 1024
SECRET_SCAN_OVERLAP_BYTES = 1024
SECRET_DETECTORS: tuple[tuple[str, re.Pattern[bytes]], ...] = (
    (
        "github_classic_token",
        re.compile(rb"(?<![A-Za-z0-9])gh[pousr]_[A-Za-z0-9]{20,255}(?![A-Za-z0-9])"),
    ),
    (
        "github_fine_grained_token",
        re.compile(rb"(?<![A-Za-z0-9_])github_pat_[A-Za-z0-9_]{20,255}(?![A-Za-z0-9_])"),
    ),
    (
        "openai_project_key",
        re.compile(rb"(?<![A-Za-z0-9_-])sk-proj-[A-Za-z0-9_-]{20,255}(?![A-Za-z0-9_-])"),
    ),
    (
        "google_api_key",
        re.compile(rb"(?<![A-Za-z0-9_-])AIza[A-Za-z0-9_-]{35}(?![A-Za-z0-9_-])"),
    ),
    (
        "aws_access_key_id",
        re.compile(rb"(?<![A-Z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])"),
    ),
    (
        "aws_secret_assignment",
        re.compile(
            rb"(?i)(?:aws_secret_access_key|aws_session_token|secretaccesskey|sessiontoken)"
            rb"(?:\\+[\"']|[\x20\t\"']){0,8}[:=]"
            rb"(?:\\+[\"']|[\x20\t\"']){0,8}[A-Za-z0-9/+=]{20,255}"
        ),
    ),
    (
        "private_key_header",
        re.compile(rb"-----BEGIN (?:(?:RSA|EC|DSA|OPENSSH|ENCRYPTED) )?PRIVATE KEY-----"),
    ),
)
SECRET_DETECTOR_NAMES = tuple(name for name, _pattern in SECRET_DETECTORS)


@dataclass(frozen=True)
class StreamScan:
    counts: dict[str, int]
    size_bytes: int
    sha256: str


def scan_stream(stream: BinaryIO) -> StreamScan:
    counts = {name: 0 for name, _pattern in SECRET_DETECTORS}
    digest = hashlib.sha256()
    size_bytes = 0
    overlap = b""
    for block in iter(lambda: stream.read(SECRET_SCAN_BLOCK_BYTES), b""):
        digest.update(block)
        size_bytes += len(block)
        payload = overlap + block
        overlap_size = len(overlap)
        for name, pattern in SECRET_DETECTORS:
            counts[name] += sum(match.end() > overlap_size for match in pattern.finditer(payload))
        overlap = payload[-SECRET_SCAN_OVERLAP_BYTES:]
    return StreamScan(
        counts={name: count for name, count in counts.items() if count},
        size_bytes=size_bytes,
        sha256=digest.hexdigest(),
    )
