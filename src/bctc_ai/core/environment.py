from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _run(command: list[str], *, timeout: int = 20) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)
    return completed.returncode, completed.stdout.strip() or completed.stderr.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _last_json_object(output: str) -> dict[str, Any] | None:
    for line in reversed(output.splitlines()):
        try:
            candidate = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict):
            return candidate
    return None


def collect_gpu_model_runtime(project_root: Path) -> dict[str, Any]:
    """Revalidate the isolated GPU runtime without downloading models or running OCR."""

    manifest_path = project_root / "config/models/gpu-runtime.toml"
    relative_manifest = manifest_path.relative_to(project_root).as_posix()
    if not manifest_path.is_file():
        return {
            "configured": False,
            "manifest": relative_manifest,
            "local_acceptance": "NOT_CONFIGURED",
        }
    try:
        manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
        isolation_directory = str(manifest["isolation_directory"])
        freeze_relative = str(manifest["freeze_path"])
        expected_freeze_hash = str(manifest["freeze_sha256"])
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError) as error:
        return {
            "configured": False,
            "manifest": relative_manifest,
            "local_acceptance": "INVALID_MANIFEST",
            "error": str(error),
        }

    runtime_python = project_root / isolation_directory / "bin/python"
    freeze_path = project_root / freeze_relative
    freeze_exists = freeze_path.is_file()
    tracked_freeze_hash = _sha256(freeze_path) if freeze_exists else None
    expected_lines = freeze_path.read_text(encoding="utf-8").splitlines() if freeze_exists else []
    freeze_record: dict[str, Any] = {
        "path": freeze_relative,
        "expected_sha256": expected_freeze_hash,
        "tracked_sha256": tracked_freeze_hash,
        "manifest_hash_matches": tracked_freeze_hash == expected_freeze_hash,
        "expected_package_count": len(expected_lines),
        "installed_package_count": None,
        "installed_matches_expected": False,
    }
    result: dict[str, Any] = {
        "configured": True,
        "manifest": relative_manifest,
        "manifest_sha256": _sha256(manifest_path),
        "declared_status": manifest.get("status"),
        "runtime_path": isolation_directory,
        "runtime_present": runtime_python.is_file(),
        "required_compute_capability": manifest.get("required_compute_capability"),
        "required_native_arch": manifest.get("required_native_arch"),
        "declared_packages": manifest.get("packages", {}),
        "freeze": freeze_record,
        "smoke": {"status": "NOT_RUN"},
        "compatibility": {"status": "NOT_RUN"},
        "local_acceptance": "ABSENT",
    }
    if not runtime_python.is_file():
        return result

    smoke_script = project_root / "scripts/diagnostics/gpu_model_runtime_smoke.py"
    smoke_code, smoke_output = _run(
        [str(runtime_python), str(smoke_script)],
        timeout=120,
    )
    smoke_payload = _last_json_object(smoke_output)
    if smoke_payload is None:
        smoke_record: dict[str, Any] = {
            "status": "FAIL",
            "return_code": smoke_code,
            "error": smoke_output[-1000:] or "smoke emitted no JSON object",
        }
    else:
        smoke_record = {**smoke_payload, "return_code": smoke_code}
    result["smoke"] = smoke_record
    smoke_verification = {
        "return_code_pass": smoke_code == 0,
        "reported_status_pass": smoke_record.get("status") == "PASS",
        "capability_matches": (
            smoke_record.get("capability") == manifest.get("required_compute_capability")
        ),
        "native_arch_present": manifest.get("required_native_arch")
        in smoke_record.get("architectures", []),
        "cuda_build_matches": smoke_record.get("torch_cuda_build") == manifest.get("cuda_runtime"),
        "package_versions_match": smoke_record.get("packages") == manifest.get("packages", {}),
    }
    result["smoke_verification"] = smoke_verification
    smoke_pass = all(smoke_verification.values())

    uv = project_root / ".venv/bin/uv"
    uv_command = str(uv) if uv.is_file() else shutil.which("uv")
    if uv_command is None:
        result["compatibility"] = {"status": "FAIL", "error": "uv executable not found"}
    else:
        check_code, check_output = _run(
            [uv_command, "pip", "check", "--python", str(runtime_python)],
            timeout=120,
        )
        result["compatibility"] = {
            "status": "PASS" if check_code == 0 else "FAIL",
            "return_code": check_code,
            "detail": check_output[-1000:],
        }
        freeze_code, freeze_output = _run(
            [uv_command, "pip", "freeze", "--python", str(runtime_python)],
            timeout=120,
        )
        installed_lines = freeze_output.splitlines() if freeze_code == 0 else []
        freeze_record.update(
            installed_package_count=len(installed_lines) if freeze_code == 0 else None,
            installed_matches_expected=freeze_code == 0 and installed_lines == expected_lines,
            installed_freeze_return_code=freeze_code,
        )

    compatibility_pass = result["compatibility"].get("status") == "PASS"
    freeze_pass = bool(
        freeze_record["manifest_hash_matches"] and freeze_record["installed_matches_expected"]
    )
    result["local_acceptance"] = (
        "PASS" if smoke_pass and compatibility_pass and freeze_pass else "FAIL"
    )
    return result


def _os_release() -> dict[str, str]:
    result: dict[str, str] = {}
    path = Path("/etc/os-release")
    if not path.is_file():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key] = value.strip().strip('"')
    return result


def _memory() -> dict[str, int]:
    values: dict[str, int] = {}
    path = Path("/proc/meminfo")
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        key, _, remainder = line.partition(":")
        token = remainder.strip().split()[0] if remainder.strip() else ""
        if token.isdigit():
            values[key] = int(token) * 1024
    return values


def _cpu_model() -> str | None:
    path = Path("/proc/cpuinfo")
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.casefold().startswith("model name"):
            return line.partition(":")[2].strip()
    return None


def _gpu() -> dict[str, Any]:
    if shutil.which("nvidia-smi") is None:
        return {"available": False, "reason": "nvidia-smi not found"}
    code, output = _run(
        [
            "nvidia-smi",
            "--query-gpu=index,name,uuid,memory.total,memory.free,driver_version,compute_cap",
            "--format=csv,noheader,nounits",
        ]
    )
    if code != 0:
        return {"available": False, "reason": output}
    devices = []
    for line in output.splitlines():
        fields = [part.strip() for part in line.split(",")]
        if len(fields) != 7:
            continue
        devices.append(
            {
                "index": int(fields[0]),
                "name": fields[1],
                "uuid": fields[2],
                "memory_total_mib": int(fields[3]),
                "memory_free_mib": int(fields[4]),
                "driver_version": fields[5],
                "compute_capability": fields[6],
            }
        )
    _, full_output = _run(["nvidia-smi"])
    cuda_version = None
    marker = "CUDA Version:"
    if marker in full_output:
        cuda_version = full_output.split(marker, 1)[1].split()[0]
    return {"available": bool(devices), "devices": devices, "reported_cuda": cuda_version}


def _torch() -> dict[str, Any]:
    code, output = _run(
        [
            sys.executable,
            "-c",
            (
                "import json,torch; print(json.dumps({"
                "'version':torch.__version__,'cuda_build':torch.version.cuda,"
                "'cuda_available':torch.cuda.is_available(),"
                "'architectures':torch.cuda.get_arch_list() if torch.cuda.is_available() else []}))"
            ),
        ]
    )
    if code != 0:
        return {"available": False, "reason": output[-1000:]}
    try:
        result = json.loads(output.splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return {"available": False, "reason": output[-1000:]}
    result["available"] = True
    return result


def collect_environment(project_root: Path) -> dict[str, Any]:
    disk = shutil.disk_usage(project_root)
    tools: dict[str, dict[str, Any]] = {}
    local_uv = project_root / ".venv/bin/uv"
    local_mongorestore = (
        project_root / ".tools/mongodb-database-tools-ubuntu2204-x86_64-100.14.0/bin/mongorestore"
    )
    local_mongod = project_root / ".tools/mongodb-linux-x86_64-ubuntu2204-7.0.34/bin/mongod"
    version_commands = {
        "python": [sys.executable, "--version"],
        "git": ["git", "--version"],
        "uv": [str(local_uv) if local_uv.is_file() else "uv", "--version"],
        "docker": ["docker", "--version"],
        "mongosh": ["mongosh", "--version"],
        "mongorestore": [
            str(local_mongorestore) if local_mongorestore.is_file() else "mongorestore",
            "--version",
        ],
        "mongod": [str(local_mongod) if local_mongod.is_file() else "mongod", "--version"],
        "nvcc": ["nvcc", "--version"],
        "pdfinfo": ["pdfinfo", "-v"],
        "tesseract": ["tesseract", "--version"],
    }
    for name, command in version_commands.items():
        code, output = _run(command)
        tools[name] = {
            "available": code == 0,
            "version": output.splitlines()[0] if output else None,
        }

    mongo_environment_names = sorted(
        key
        for key in os.environ
        if "mongo" in key.casefold() or key.casefold() in {"database_url", "db_uri"}
    )
    local_mongo_verified = False
    local_mongo_template_count: int | None = None
    try:
        from pymongo import MongoClient

        client = MongoClient("mongodb://127.0.0.1:27018", serverSelectionTimeoutMS=500)
        client.admin.command("ping")
        local_mongo_template_count = client["financial_20_02_2022"][
            "financial_report_templates"
        ].count_documents({})
        local_mongo_verified = True
        client.close()
    except Exception:
        pass
    return {
        "captured_at": datetime.now(UTC).isoformat(),
        "hostname": platform.node(),
        "os": _os_release(),
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "cpu": {"logical_count": os.cpu_count(), "model": _cpu_model()},
        "memory": _memory(),
        "disk": {"total_bytes": disk.total, "used_bytes": disk.used, "free_bytes": disk.free},
        "gpu": _gpu(),
        "torch": _torch(),
        "gpu_model_runtime": collect_gpu_model_runtime(project_root),
        "tools": tools,
        "mongodb": {
            "environment_variable_names": mongo_environment_names,
            "client_available": tools["mongorestore"]["available"],
            "local_loopback_connection_verified": local_mongo_verified,
            "local_template_document_count": local_mongo_template_count,
            "external_connection_verified": False,
        },
    }
