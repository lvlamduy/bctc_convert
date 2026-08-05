from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _run(command: list[str]) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)
    return completed.returncode, completed.stdout.strip() or completed.stderr.strip()


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
        "tools": tools,
        "mongodb": {
            "environment_variable_names": mongo_environment_names,
            "client_available": tools["mongorestore"]["available"],
            "local_loopback_connection_verified": local_mongo_verified,
            "local_template_document_count": local_mongo_template_count,
            "external_connection_verified": False,
        },
    }
