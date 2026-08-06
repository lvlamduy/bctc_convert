from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import tomllib
import urllib.request
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bctc_ai.core.atomic import atomic_write_json  # noqa: E402
from bctc_ai.core.hashing import sha256_file  # noqa: E402


class VietOCRInstallError(RuntimeError):
    pass


def _verify(path: Path, record: dict[str, object]) -> bool:
    return (
        path.is_file()
        and path.stat().st_size == int(record["size_bytes"])
        and sha256_file(path) == str(record["sha256"])
    )


def _download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "bctc-ai-vietocr-bootstrap/1"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as stream:
        shutil.copyfileobj(response, stream, length=1024 * 1024)


def _verify_overlay(wheel: Path, site_packages: Path) -> bool:
    if not site_packages.is_dir():
        return False
    with zipfile.ZipFile(wheel) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            installed = site_packages / member.filename
            if not installed.is_file():
                return False
            if sha256_file(installed) != hashlib.sha256(archive.read(member)).hexdigest():
                return False
    return True


def install(config_path: Path, runtime_root: Path) -> dict[str, object]:
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    if (
        config.get("version") != 1
        or config.get("status") != "CALIBRATION_ONLY_VIETNAMESE_SEMANTIC_LINE_PROPOSAL"
    ):
        raise VietOCRInstallError("VietOCR runtime config identity drifted")
    runtime_root = runtime_root.resolve()
    runtime_root.mkdir(parents=True, exist_ok=True)
    artifacts = config.get("artifacts")
    if not isinstance(artifacts, dict):
        raise VietOCRInstallError("VietOCR artifact registry is missing")
    installed_records = []
    for key, raw_record in artifacts.items():
        if not isinstance(raw_record, dict):
            raise VietOCRInstallError(f"invalid artifact record: {key}")
        destination = (runtime_root / str(raw_record["path"])).resolve()
        try:
            destination.relative_to(runtime_root)
        except ValueError as exc:
            raise VietOCRInstallError(f"artifact escapes runtime root: {key}") from exc
        if destination.exists() and not _verify(destination, raw_record):
            raise VietOCRInstallError(f"refusing to overwrite mismatched artifact: {destination}")
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(
                prefix=f".{destination.name}.", dir=destination.parent
            ) as temporary:
                download = Path(temporary) / destination.name
                _download(str(raw_record["url"]), download)
                if not _verify(download, raw_record):
                    raise VietOCRInstallError(f"downloaded artifact failed verification: {key}")
                os.replace(download, destination)
        installed_records.append(
            {
                "key": key,
                "path": destination.relative_to(runtime_root).as_posix(),
                "size_bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
                "url": raw_record["url"],
            }
        )

    wheel = runtime_root / str(artifacts["wheel"]["path"])
    site_packages = runtime_root / str(config["runtime"]["site_packages"])
    if site_packages.exists() and not _verify_overlay(wheel, site_packages):
        raise VietOCRInstallError(f"refusing to replace mismatched overlay: {site_packages}")
    if not site_packages.exists():
        with tempfile.TemporaryDirectory(
            prefix=f".{site_packages.name}.", dir=runtime_root
        ) as temporary:
            extracted = Path(temporary) / site_packages.name
            extracted.mkdir()
            with zipfile.ZipFile(wheel) as archive:
                archive.extractall(extracted)
            if not _verify_overlay(wheel, extracted):
                raise VietOCRInstallError("extracted VietOCR overlay failed verification")
            os.replace(extracted, site_packages)

    payload: dict[str, object] = {
        "format_version": 1,
        "state": "VIETOCR_LINE_RUNTIME_INSTALLED_NO_MODEL_ACCEPTANCE",
        "runtime_root": runtime_root.as_posix(),
        "configuration": {
            "path": config_path.resolve().relative_to(PROJECT_ROOT).as_posix(),
            "sha256": sha256_file(config_path),
        },
        "artifacts": installed_records,
        "site_packages": site_packages.relative_to(runtime_root).as_posix(),
        "site_packages_verified_against_wheel": _verify_overlay(wheel, site_packages),
    }
    atomic_write_json(runtime_root / "install_manifest.json", payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Install the hash-pinned VietOCR overlay")
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "config/models/vietocr-0.3.13.toml",
    )
    parser.add_argument(
        "--runtime-root",
        type=Path,
        default=Path("/workspace/bctc-ai-runtime/vietocr-0.3.13"),
    )
    args = parser.parse_args()
    result = install(args.config.resolve(), args.runtime_root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
