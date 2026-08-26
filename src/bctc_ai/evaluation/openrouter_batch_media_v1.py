"""Immutable S3 media bridge for OpenRouter Batch public-HTTPS image inputs."""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from bctc_ai.storage.s3_snapshot import AwsCli, S3SnapshotError, load_settings

DEFAULT_PRESIGNED_TTL_SECONDS = 48 * 60 * 60


class OpenRouterBatchMediaV1Error(RuntimeError):
    """The immutable object or its bounded presigned URL failed authentication."""


@dataclass(frozen=True)
class PresignedBatchMediaV1:
    object_key: str
    payload_sha256: str
    size_bytes: int
    media_type: str
    upload_disposition: str
    expires_at: str
    url: str
    url_sha256: str

    def public_receipt(self) -> dict[str, object]:
        """Return the safe receipt; the credential-bearing URL is deliberately absent."""

        return {
            "expires_at": self.expires_at,
            "media_type": self.media_type,
            "object_key": self.object_key,
            "payload_sha256": self.payload_sha256,
            "size_bytes": self.size_bytes,
            "upload_disposition": self.upload_disposition,
            "url_sha256": self.url_sha256,
        }


def _presign(*, bucket: str, key: str, profile: str, region: str, ttl_seconds: int) -> str:
    environment = dict(os.environ)
    environment.update({"AWS_PAGER": "", "AWS_RETRY_MODE": "standard"})
    completed = subprocess.run(
        [
            "aws",
            "s3",
            "presign",
            f"s3://{bucket}/{key}",
            "--expires-in",
            str(ttl_seconds),
            "--profile",
            profile,
            "--region",
            region,
            "--no-cli-pager",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    if completed.returncode != 0:
        raise OpenRouterBatchMediaV1Error("S3 presign command failed")
    return completed.stdout.strip()


def materialize_openrouter_batch_media_v1(
    *,
    payload: bytes,
    media_type: str,
    s3_config_path: Path,
    ttl_seconds: int = DEFAULT_PRESIGNED_TTL_SECONDS,
) -> PresignedBatchMediaV1:
    """Upload exact bytes once and issue a bounded URL without persisting the URL itself."""

    if not payload or media_type not in {"image/png", "image/jpeg"}:
        raise OpenRouterBatchMediaV1Error("batch media must be one nonempty PNG or JPEG")
    if ttl_seconds < 3600 or ttl_seconds > DEFAULT_PRESIGNED_TTL_SECONDS:
        raise OpenRouterBatchMediaV1Error("presigned URL TTL must lie within 1h..48h")
    digest = sha256(payload).hexdigest()
    settings = load_settings(s3_config_path)
    key = f"{settings.prefix}/{settings.content_prefix}/{digest[:2]}/{digest}"
    client = AwsCli(settings)
    client.preflight()
    suffix = ".png" if media_type == "image/png" else ".jpg"
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix="openrouter-batch-", suffix=suffix, delete=False
        ) as f:
            temporary_name = f.name
            os.fchmod(f.fileno(), 0o600)
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        upload = client.put_content(Path(temporary_name), key=key, digest=digest)
    except S3SnapshotError as exc:
        raise OpenRouterBatchMediaV1Error("immutable S3 media publication failed") from exc
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)
    url = _presign(
        bucket=settings.bucket,
        key=key,
        profile=settings.profile,
        region=settings.region,
        ttl_seconds=ttl_seconds,
    )
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or not parsed.path.endswith("/" + digest)
        or not {"X-Amz-Credential", "X-Amz-Signature"} <= set(query)
    ):
        raise OpenRouterBatchMediaV1Error("presigned URL contract drifted")
    expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
    return PresignedBatchMediaV1(
        object_key=key,
        payload_sha256=digest,
        size_bytes=len(payload),
        media_type=media_type,
        upload_disposition=upload.disposition,
        expires_at=expires_at.isoformat().replace("+00:00", "Z"),
        url=url,
        url_sha256=sha256(url.encode()).hexdigest(),
    )
