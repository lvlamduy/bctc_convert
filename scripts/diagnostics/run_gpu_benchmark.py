from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

GPU_QUERY = (
    "index,name,uuid,memory.used,memory.total,utilization.gpu,power.draw"
)


def _query_gpu(gpu_index: int) -> dict[str, object]:
    completed = subprocess.run(
        [
            "nvidia-smi",
            f"--id={gpu_index}",
            f"--query-gpu={GPU_QUERY}",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    fields = [field.strip() for field in completed.stdout.strip().split(",")]
    if len(fields) != 7:
        raise RuntimeError(f"unexpected nvidia-smi output: {completed.stdout!r}")
    return {
        "index": int(fields[0]),
        "name": fields[1],
        "uuid": fields[2],
        "memory_used_mib": float(fields[3]),
        "memory_total_mib": float(fields[4]),
        "utilization_percent": float(fields[5]),
        "power_watts": None if fields[6] == "[N/A]" else float(fields[6]),
    }


def _process_memory_kib(pid: int) -> tuple[int | None, int | None]:
    try:
        status = Path(f"/proc/{pid}/status").read_text(encoding="utf-8")
    except (FileNotFoundError, PermissionError):
        return None, None
    values: dict[str, int] = {}
    for line in status.splitlines():
        if line.startswith(("VmRSS:", "VmHWM:")):
            key, value, _unit = line.split()
            values[key.removesuffix(":")] = int(value)
    return values.get("VmRSS"), values.get("VmHWM")


def _atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite benchmark record: {path}")
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    ) as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
        temporary_path = Path(stream.name)
    os.replace(temporary_path, path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a command and sample NVIDIA GPU usage")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gpu-index", type=int, default=0)
    parser.add_argument("--interval-ms", type=int, default=250)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("a command is required after --")
    if args.interval_ms < 100 or args.interval_ms > 10_000:
        parser.error("--interval-ms must be between 100 and 10000")
    return args


def main() -> int:
    args = parse_args()
    if args.output.exists():
        print(f"refusing to overwrite benchmark record: {args.output}", file=sys.stderr)
        return 2

    started_at = datetime.now(UTC)
    baseline = _query_gpu(args.gpu_index)
    process = subprocess.Popen(args.command)
    samples: list[dict[str, object]] = []
    peak_rss_kib = 0
    try:
        while process.poll() is None:
            try:
                samples.append(_query_gpu(args.gpu_index))
            except (OSError, subprocess.SubprocessError, ValueError, RuntimeError):
                pass
            _rss_kib, high_water_kib = _process_memory_kib(process.pid)
            if high_water_kib is not None:
                peak_rss_kib = max(peak_rss_kib, high_water_kib)
            time.sleep(args.interval_ms / 1000)
    except KeyboardInterrupt:
        process.terminate()
        process.wait()
        raise
    return_code = process.wait()
    try:
        samples.append(_query_gpu(args.gpu_index))
    except (OSError, subprocess.SubprocessError, ValueError, RuntimeError):
        pass
    finished_at = datetime.now(UTC)

    observed = samples or [baseline]
    peak_memory = max(float(sample["memory_used_mib"]) for sample in observed)
    power_values = [
        float(sample["power_watts"])
        for sample in observed
        if sample["power_watts"] is not None
    ]
    payload: dict[str, object] = {
        "format_version": 1,
        "status": "PASS" if return_code == 0 else "FAIL",
        "return_code": return_code,
        "command": args.command,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "wall_seconds": (finished_at - started_at).total_seconds(),
        "sample_interval_ms": args.interval_ms,
        "sample_count": len(samples),
        "gpu": {
            "index": baseline["index"],
            "name": baseline["name"],
            "uuid": baseline["uuid"],
            "memory_total_mib": baseline["memory_total_mib"],
            "baseline_memory_used_mib": baseline["memory_used_mib"],
            "peak_memory_used_mib": peak_memory,
            "peak_memory_delta_mib": peak_memory - float(baseline["memory_used_mib"]),
            "peak_utilization_percent": max(
                float(sample["utilization_percent"]) for sample in observed
            ),
            "peak_power_watts": max(power_values) if power_values else None,
        },
        "process_peak_rss_kib": peak_rss_kib or None,
    }
    _atomic_write_json(args.output, payload)
    print(json.dumps(payload, sort_keys=True))
    return return_code


if __name__ == "__main__":
    sys.exit(main())
