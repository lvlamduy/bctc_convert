from __future__ import annotations

import argparse
import ctypes
import os
import select
import signal


def _pidfd_open(pid: int) -> int:
    if hasattr(os, "pidfd_open"):
        return os.pidfd_open(pid)
    libc = ctypes.CDLL(None, use_errno=True)
    file_descriptor = int(libc.syscall(434, ctypes.c_int(pid), ctypes.c_uint(0)))
    if file_descriptor < 0:
        error_number = ctypes.get_errno()
        raise OSError(error_number, os.strerror(error_number))
    return file_descriptor


def main() -> int:
    parser = argparse.ArgumentParser(description="Hard watchdog for one Qwen inference call")
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--timeout-seconds", type=int, required=True)
    args = parser.parse_args()
    if args.pid <= 1 or args.timeout_seconds < 1:
        return 2
    try:
        pidfd = _pidfd_open(args.pid)
    except OSError:
        return 3
    try:
        print("READY", flush=True)
        exited, _, _ = select.select([pidfd], [], [], args.timeout_seconds)
        if exited:
            return 0
        try:
            os.kill(args.pid, signal.SIGKILL)
        except ProcessLookupError:
            return 0
        return 124
    finally:
        os.close(pidfd)


if __name__ == "__main__":
    raise SystemExit(main())
