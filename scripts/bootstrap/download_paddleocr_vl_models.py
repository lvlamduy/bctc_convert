from __future__ import annotations

import argparse
import json
import os
import tempfile
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_MANIFEST = PROJECT_ROOT / "config/models/gpu-runtime.toml"
MODEL_KEYS = (
    "pp_doclayout_v3_safetensors",
    "paddleocr_vl_1_6",
    "pp_ocrv6_medium_det",
    "pp_ocrv6_medium_rec",
)


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verify_model(directory: Path, config: dict[str, object]) -> dict[str, object]:
    weights = directory / str(config["weights_file"])
    if not weights.is_file():
        raise FileNotFoundError(f"missing model weights: {weights}")
    size = weights.stat().st_size
    expected_size = int(config["weights_size_bytes"])
    if size != expected_size:
        raise RuntimeError(f"model weight size mismatch at {weights}: {size} != {expected_size}")
    digest = _sha256(weights)
    expected_digest = str(config["weights_sha256"])
    if digest != expected_digest:
        raise RuntimeError(
            f"model weight SHA-256 mismatch at {weights}: {digest} != {expected_digest}"
        )
    return {
        "directory": directory.as_posix(),
        "repo_id": config["repo_id"],
        "revision": config["revision"],
        "weights_file": config["weights_file"],
        "weights_size_bytes": size,
        "weights_sha256": digest,
        "status": "VERIFIED",
    }


def _download_model(directory: Path, config: dict[str, object]) -> dict[str, object]:
    from huggingface_hub import snapshot_download

    directory.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{directory.name}.", dir=directory.parent) as temp:
        payload = Path(temp) / "payload"
        snapshot_download(
            repo_id=str(config["repo_id"]),
            revision=str(config["revision"]),
            local_dir=payload,
        )
        record = _verify_model(payload, config)
        os.replace(payload, directory)
    record["directory"] = directory.as_posix()
    record["status"] = "DOWNLOADED_AND_VERIFIED"
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch hash-pinned Paddle document models")
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--verify-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = tomllib.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    official_models = args.cache_root.resolve() / "official_models"
    records = []
    for key in MODEL_KEYS:
        config = manifest["models"][key]
        destination = official_models / config["cache_directory"]
        if destination.exists():
            if not destination.is_dir():
                raise RuntimeError(f"model destination is not a directory: {destination}")
            records.append(_verify_model(destination, config))
        elif args.verify_only:
            raise FileNotFoundError(f"model is absent in verify-only mode: {destination}")
        else:
            records.append(_download_model(destination, config))
    print(json.dumps({"status": "PASS", "models": records}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
