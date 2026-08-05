from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import statistics
import tempfile
import time
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from .run_ppocrv6_word_boxes import (
        PROJECT_ROOT,
        RUNTIME_MANIFEST,
        _deny_network_connections,
        _git_state,
        _model_records,
        _sha256,
        _validate_payload,
        _write_artifacts,
    )
except ImportError:
    from run_ppocrv6_word_boxes import (  # type: ignore[no-redef]
        PROJECT_ROOT,
        RUNTIME_MANIFEST,
        _deny_network_connections,
        _git_state,
        _model_records,
        _sha256,
        _validate_payload,
        _write_artifacts,
    )


DATASET_ROLE_REGISTRY = PROJECT_ROOT / "data/registered/dataset_roles.jsonl"
ALLOWED_DATASET_ROLES = ("CALIBRATION", "VALIDATION", "UNTOUCHED_HOLDOUT")


class BatchWordBoxError(RuntimeError):
    pass


def _parse_pages(value: str | None) -> tuple[int, ...] | None:
    if value is None:
        return None
    pages: set[int] = set()
    for raw_token in value.split(","):
        token = raw_token.strip()
        if not token:
            raise argparse.ArgumentTypeError("empty page token")
        if "-" in token:
            start_text, end_text = token.split("-", 1)
            try:
                start, end = int(start_text), int(end_text)
            except ValueError as exc:
                raise argparse.ArgumentTypeError(f"invalid page range: {token}") from exc
            if start < 1 or end < start:
                raise argparse.ArgumentTypeError(f"invalid page range: {token}")
            pages.update(range(start, end + 1))
        else:
            try:
                page = int(token)
            except ValueError as exc:
                raise argparse.ArgumentTypeError(f"invalid page: {token}") from exc
            if page < 1:
                raise argparse.ArgumentTypeError(f"invalid page: {token}")
            pages.add(page)
    if not pages:
        raise argparse.ArgumentTypeError("at least one page is required")
    return tuple(sorted(pages))


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise BatchWordBoxError(f"cannot read JSON object: {path}") from exc
    if not isinstance(payload, dict):
        raise BatchWordBoxError(f"JSON artifact is not an object: {path}")
    return payload


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if temporary.exists():
            temporary.unlink()


def _portable_path(path: Path) -> str:
    path = path.resolve()
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _stable_json_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def _candidate_paths(manifest_path: Path, value: str, *, render: bool) -> tuple[Path, ...]:
    raw_path = Path(value)
    candidates: list[Path] = []
    if raw_path.is_absolute():
        candidates.append(raw_path)
    else:
        candidates.extend((PROJECT_ROOT / raw_path, manifest_path.parent / raw_path))
    if render:
        candidates.extend(
            (
                manifest_path.parent / "renders" / raw_path.name,
                manifest_path.parent / raw_path.name,
            )
        )
    unique: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)
    return tuple(unique)


def _resolve_hashed_path(
    manifest_path: Path,
    values: tuple[str, ...],
    expected_digest: str,
    *,
    label: str,
    render: bool = False,
) -> Path:
    if len(expected_digest) != 64:
        raise BatchWordBoxError(f"{label} has no valid SHA-256 identity")
    examined: list[str] = []
    for value in values:
        for candidate in _candidate_paths(manifest_path, value, render=render):
            examined.append(candidate.as_posix())
            if candidate.is_file() and _sha256(candidate) == expected_digest:
                return candidate
    raise BatchWordBoxError(f"{label} is absent or hash-drifted; examined {examined}")


def _dataset_registration(source_digest: str, dataset_role: str) -> dict[str, Any]:
    try:
        records = [
            json.loads(line)
            for line in DATASET_ROLE_REGISTRY.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise BatchWordBoxError("dataset-role registry is absent or invalid") from exc
    matches = [
        record
        for record in records
        if isinstance(record, dict) and record.get("document_id") == f"sha256:{source_digest}"
    ]
    if len(matches) != 1:
        raise BatchWordBoxError(
            f"source must have exactly one frozen dataset role; found {len(matches)}"
        )
    record = matches[0]
    if record.get("immutable") is not True or record.get("dataset_role") != dataset_role:
        raise BatchWordBoxError(
            "requested dataset role differs from the immutable source registration"
        )
    return {
        "document_id": record["document_id"],
        "dataset_role": record["dataset_role"],
        "source_path": str(record["source_path"]),
        "assigned_at": record["assigned_at"],
        "immutable": True,
    }


def _verify_preprocess_envelope(manifest_path: Path, payload: dict[str, Any]) -> None:
    envelope_path = manifest_path.with_name("run_manifest.json")
    envelope = _load_json(envelope_path)
    expected = {
        "manifest": manifest_path.name,
        "manifest_sha256": _sha256(manifest_path),
        "source_sha256": payload.get("source_sha256"),
        "state": "PREPROCESSED",
    }
    if any(envelope.get(key) != value for key, value in expected.items()):
        raise BatchWordBoxError("preprocess run envelope does not bind the input manifest")


def _render_records(
    manifest_path: Path,
    requested_pages: tuple[int, ...] | None,
    dataset_role: str,
) -> tuple[dict[str, Any], dict[str, Any], tuple[dict[str, Any], ...]]:
    payload = _load_json(manifest_path)
    if payload.get("state") != "PREPROCESSED":
        raise BatchWordBoxError("batch OCR requires the top-level PREPROCESSED manifest")
    if payload.get("dataset_role") != dataset_role:
        raise BatchWordBoxError("requested role differs from the preprocess manifest role")
    upstream_code = payload.get("code")
    if not isinstance(upstream_code, dict) or upstream_code.get("git_dirty") is not False:
        raise BatchWordBoxError("preprocess evidence did not start from clean code")
    _verify_preprocess_envelope(manifest_path, payload)

    source_digest = str(payload.get("source_sha256", ""))
    registration = _dataset_registration(source_digest, dataset_role)
    source_path = _resolve_hashed_path(
        manifest_path,
        (str(payload.get("source", "")), registration["source_path"]),
        source_digest,
        label="source PDF",
    )
    source = {
        "path": _portable_path(source_path),
        "size_bytes": source_path.stat().st_size,
        "sha256": source_digest,
    }

    raw_pages = payload.get("pages")
    if not isinstance(raw_pages, list) or not raw_pages:
        raise BatchWordBoxError("preprocess manifest contains no pages")
    records_by_page: dict[int, dict[str, Any]] = {}
    for raw_page in raw_pages:
        if not isinstance(raw_page, dict):
            raise BatchWordBoxError("invalid page record in preprocess manifest")
        raw_render = raw_page.get("render")
        if not isinstance(raw_render, dict):
            raise BatchWordBoxError("preprocess page contains no render record")
        try:
            page = int(raw_page.get("page", raw_render["page"]))
            dpi = int(raw_render["dpi"])
        except (KeyError, TypeError, ValueError) as exc:
            raise BatchWordBoxError("render record has no valid page or DPI") from exc
        if page < 1 or dpi < 72 or page in records_by_page:
            raise BatchWordBoxError(f"duplicate or invalid render page: {page}")
        if raw_render.get("source_sha256") not in {None, source_digest}:
            raise BatchWordBoxError(f"render source identity differs on page {page}")
        expected_digest = str(raw_render.get("sha256", ""))
        render_path = _resolve_hashed_path(
            manifest_path,
            (str(raw_render.get("path", "")),),
            expected_digest,
            label=f"render page {page}",
            render=True,
        )
        records_by_page[page] = {
            "page": page,
            "path": _portable_path(render_path),
            "sha256": expected_digest,
            "size_bytes": render_path.stat().st_size,
            "dpi": dpi,
            "rotation": raw_render.get("rotation"),
            "width_pixels": raw_render.get("width_pixels"),
            "height_pixels": raw_render.get("height_pixels"),
        }
    selected_pages = requested_pages or tuple(sorted(records_by_page))
    missing = [page for page in selected_pages if page not in records_by_page]
    if missing:
        raise BatchWordBoxError(f"requested pages are absent from the manifest: {missing}")
    return (
        source,
        registration,
        tuple(records_by_page[page] for page in selected_pages),
    )


def _configuration_identity(
    *,
    config_path: Path,
    helper_path: Path,
    cpu_threads: int,
) -> dict[str, Any]:
    return {
        "path": config_path.relative_to(PROJECT_ROOT).as_posix(),
        "sha256": _sha256(config_path),
        "runner_path": Path(__file__).relative_to(PROJECT_ROOT).as_posix(),
        "runner_sha256": _sha256(Path(__file__)),
        "single_page_helper_path": helper_path.relative_to(PROJECT_ROOT).as_posix(),
        "single_page_helper_sha256": _sha256(helper_path),
        "implicit_orientation_or_unwarp": False,
        "network_policy": "PROCESS_SOCKET_CONNECT_DENIED",
        "mkldnn": False,
        "precision": "fp32",
        "cpu_threads": cpu_threads,
    }


def _runtime_identity(runtime: dict[str, Any], models: list[dict[str, Any]]) -> dict[str, Any]:
    stable_models = [
        {key: value for key, value in model.items() if key != "weights_path"} for model in models
    ]
    installed = {
        name: importlib.metadata.version(name) for name in ("paddlepaddle", "paddleocr", "paddlex")
    }
    declared = {name: runtime["packages"][name] for name in installed}
    if installed != declared:
        raise BatchWordBoxError(
            f"installed PP-OCRv6 runtime differs from the frozen manifest: {installed}"
        )
    return {
        "manifest_path": RUNTIME_MANIFEST.relative_to(PROJECT_ROOT).as_posix(),
        "manifest_sha256": _sha256(RUNTIME_MANIFEST),
        "models": stable_models,
        "packages": installed,
        "device": "cpu",
        "compiled_with_cuda": False,
    }


def _resolve_project_path(value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def _expected_page_identity(
    *,
    page: int,
    dataset_role: str,
    batch_identity: str,
    render: dict[str, Any],
    git: dict[str, Any],
    configuration: dict[str, Any],
    runtime_identity: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "state": "OCR_COMPLETE",
        "page": page,
        "dataset_role": dataset_role,
        "evidence_role": "INDEPENDENT_GEOMETRY_PROPOSAL_ONLY",
        "confidence_policy": "NO_AUTOMATIC_TRUTH_OR_SCHEMA_PROMOTION",
        "batch_identity": batch_identity,
        "input": render,
        "code": git,
        "configuration": configuration,
        "runtime": runtime_identity,
    }


def _page_output_record(
    output_directory: Path,
    page: int,
    expected_identity: dict[str, Any],
) -> dict[str, Any]:
    page_directory = output_directory / f"ppocrv6-page-{page:04d}"
    result_path = page_directory / "ocr_result.json"
    manifest_path = page_directory / "run_manifest.json"
    result = _load_json(result_path)
    manifest = _load_json(manifest_path)
    mismatches = {
        key: {"expected": value, "actual": manifest.get(key)}
        for key, value in expected_identity.items()
        if manifest.get(key) != value
    }
    if mismatches:
        raise BatchWordBoxError(f"page output identity mismatch on page {page}: {mismatches}")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        raise BatchWordBoxError(f"page output manifest has no artifacts: {page}")
    artifact = artifacts.get("ocr_result")
    if not isinstance(artifact, dict) or artifact.get("sha256") != _sha256(result_path):
        raise BatchWordBoxError(f"page result hash differs from page manifest: {page}")
    _validate_payload(result)
    metrics = manifest.get("metrics")
    if not isinstance(metrics, dict):
        raise BatchWordBoxError(f"page output manifest has no metrics: {page}")
    return {
        "page": page,
        "output_directory": page_directory.relative_to(output_directory).as_posix(),
        "ocr_result": {
            "path": result_path.relative_to(output_directory).as_posix(),
            "size_bytes": result_path.stat().st_size,
            "sha256": _sha256(result_path),
        },
        "run_manifest": {
            "path": manifest_path.relative_to(output_directory).as_posix(),
            "size_bytes": manifest_path.stat().st_size,
            "sha256": _sha256(manifest_path),
        },
        "metrics": metrics,
    }


def _aggregate(records: list[dict[str, Any]], sessions: list[dict[str, Any]]) -> dict[str, Any]:
    line_count = sum(int(record["metrics"]["line_count"]) for record in records)
    weighted_score = sum(
        float(record["metrics"]["mean_line_score"] or 0) * int(record["metrics"]["line_count"])
        for record in records
    )
    minimum_scores = [
        float(record["metrics"]["minimum_line_score"])
        for record in records
        if record["metrics"].get("minimum_line_score") is not None
    ]
    load_seconds = [float(session["model_load_wall_seconds"]) for session in sessions]
    return {
        "completed_page_count": len(records),
        "line_count": line_count,
        "word_token_count": sum(int(record["metrics"]["word_token_count"]) for record in records),
        "page_inference_wall_seconds": round(
            sum(float(record["metrics"]["wall_seconds"]) for record in records), 6
        ),
        "model_load_session_count": len(sessions),
        "model_load_wall_seconds_total": round(sum(load_seconds), 6),
        "minimum_line_score": min(minimum_scores) if minimum_scores else None,
        "mean_line_score": weighted_score / line_count if line_count else None,
        "lines_below_0_8": sum(int(record["metrics"]["lines_below_0_8"]) for record in records),
        "lines_below_0_9": sum(int(record["metrics"]["lines_below_0_9"]) for record in records),
    }


def _validate_resume(state: dict[str, Any], expected_identity: dict[str, Any]) -> None:
    mismatches = {
        key: {"expected": value, "actual": state.get(key)}
        for key, value in expected_identity.items()
        if state.get(key) != value
    }
    if mismatches:
        raise BatchWordBoxError(f"batch resume identity mismatch: {mismatches}")
    if state.get("state") not in {"INITIALIZED", "PARTIAL", "OCR_COMPLETE"}:
        raise BatchWordBoxError("batch state is not resumable")
    if not isinstance(state.get("pages"), list) or not isinstance(state.get("sessions"), list):
        raise BatchWordBoxError("batch checkpoint has invalid page/session collections")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run pinned PP-OCRv6 once and checkpoint many preprocessed pages"
    )
    parser.add_argument("--preprocess-manifest", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--model-cache", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dataset-role", choices=ALLOWED_DATASET_ROLES, required=True)
    parser.add_argument("--pages", type=_parse_pages)
    parser.add_argument("--cpu-threads", type=int, default=8)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = args.preprocess_manifest.resolve()
    output_directory = args.output_directory.resolve()
    model_cache = args.model_cache.resolve()
    config_path = args.config.resolve()
    helper_path = Path(__file__).with_name("run_ppocrv6_word_boxes.py").resolve()
    if not config_path.is_file():
        raise FileNotFoundError(f"PP-OCRv6 config does not exist: {config_path}")
    if args.cpu_threads < 1:
        raise ValueError("cpu_threads must be positive")
    if output_directory.exists() and not args.resume:
        raise FileExistsError(f"refusing to overwrite batch output: {output_directory}")
    if not output_directory.exists() and args.resume:
        raise FileNotFoundError(f"batch output does not exist for resume: {output_directory}")

    git = _git_state()
    if git["dirty"] and not args.allow_dirty:
        raise RuntimeError("refusing evidence OCR from a dirty Git worktree")
    source, registration, render_records = _render_records(
        manifest_path, args.pages, args.dataset_role
    )
    input_manifest = {
        "path": _portable_path(manifest_path),
        "size_bytes": manifest_path.stat().st_size,
        "sha256": _sha256(manifest_path),
    }
    runtime = tomllib.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    models = _model_records(model_cache, runtime)
    configuration = _configuration_identity(
        config_path=config_path, helper_path=helper_path, cpu_threads=args.cpu_threads
    )
    runtime_identity = _runtime_identity(runtime, models)
    immutable_identity = {
        "schema_version": 1,
        "dataset_role": args.dataset_role,
        "evidence_role": "INDEPENDENT_GEOMETRY_PROPOSAL_ONLY",
        "input_manifest": input_manifest,
        "source": source,
        "dataset_registration": registration,
        "requested_pages": [record["page"] for record in render_records],
        "renders": list(render_records),
        "code": git,
        "configuration": configuration,
        "runtime_identity": runtime_identity,
    }
    batch_identity = _stable_json_sha256(immutable_identity)
    expected_batch_identity = {**immutable_identity, "batch_identity": batch_identity}
    state_path = output_directory / "batch_manifest.json"
    if args.resume:
        state = _load_json(state_path)
        _validate_resume(state, expected_batch_identity)
    else:
        output_directory.mkdir(parents=True)
        now = datetime.now(UTC).isoformat()
        state = {
            **expected_batch_identity,
            "state": "INITIALIZED",
            "confidence_policy": "NO_AUTOMATIC_TRUTH_OR_SCHEMA_PROMOTION",
            "pages": [],
            "sessions": [],
            "metrics": _aggregate([], []),
            "started_at": now,
            "updated_at": now,
            "completed_at": None,
        }
        _atomic_json(state_path, state)

    recorded_pages: dict[int, dict[str, Any]] = {}
    for record in state["pages"]:
        if not isinstance(record, dict) or not isinstance(record.get("page"), int):
            raise BatchWordBoxError("batch checkpoint has an invalid page record")
        page = int(record["page"])
        if page in recorded_pages:
            raise BatchWordBoxError(f"batch checkpoint repeats page {page}")
        recorded_pages[page] = record
    renders_by_page = {int(render["page"]): render for render in render_records}
    if any(page not in renders_by_page for page in recorded_pages):
        raise BatchWordBoxError("batch checkpoint includes an unrequested page")
    for page, record in recorded_pages.items():
        expected_page = _expected_page_identity(
            page=page,
            dataset_role=args.dataset_role,
            batch_identity=batch_identity,
            render=renders_by_page[page],
            git=git,
            configuration=configuration,
            runtime_identity=runtime_identity,
        )
        verified = _page_output_record(output_directory, page, expected_page)
        if verified != record:
            raise BatchWordBoxError(f"recorded page output identity drift: {page}")
    for page, render in renders_by_page.items():
        page_directory = output_directory / f"ppocrv6-page-{page:04d}"
        if page not in recorded_pages and page_directory.exists():
            expected_page = _expected_page_identity(
                page=page,
                dataset_role=args.dataset_role,
                batch_identity=batch_identity,
                render=render,
                git=git,
                configuration=configuration,
                runtime_identity=runtime_identity,
            )
            recorded_pages[page] = _page_output_record(output_directory, page, expected_page)
    missing = [record for record in render_records if record["page"] not in recorded_pages]
    if not missing:
        ordered = [recorded_pages[record["page"]] for record in render_records]
        state.update(
            state="OCR_COMPLETE",
            pages=ordered,
            metrics=_aggregate(ordered, state["sessions"]),
            updated_at=datetime.now(UTC).isoformat(),
            completed_at=state.get("completed_at") or datetime.now(UTC).isoformat(),
        )
        _atomic_json(state_path, state)
        print(
            json.dumps(
                {"status": "PASS_ALREADY_COMPLETE", "metrics": state["metrics"]},
                sort_keys=True,
            )
        )
        return 0

    _deny_network_connections()
    import paddle
    from paddleocr import PaddleOCR

    session_started_at = datetime.now(UTC).isoformat()
    load_started = time.perf_counter()
    pipeline = PaddleOCR(
        paddlex_config=config_path.as_posix(),
        text_detection_model_dir=str(Path(models[0]["weights_path"]).parent),
        text_recognition_model_dir=str(Path(models[1]["weights_path"]).parent),
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        return_word_box=True,
        device="cpu",
        engine="paddle",
        enable_hpi=False,
        precision="fp32",
        enable_mkldnn=False,
        cpu_threads=args.cpu_threads,
    )
    load_seconds = time.perf_counter() - load_started
    if paddle.device.get_device() != "cpu" or paddle.device.is_compiled_with_cuda():
        raise BatchWordBoxError("PP-OCRv6 batch runtime device drift")
    session = {
        "started_at": session_started_at,
        "model_load_wall_seconds": load_seconds,
    }
    state["sessions"].append(session)
    state.update(
        state="PARTIAL",
        metrics=_aggregate(list(recorded_pages.values()), state["sessions"]),
        updated_at=datetime.now(UTC).isoformat(),
    )
    _atomic_json(state_path, state)

    for render in missing:
        page = int(render["page"])
        page_started_at = datetime.now(UTC)
        page_started = time.perf_counter()
        results = pipeline.predict(
            _resolve_project_path(render["path"]).as_posix(),
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            return_word_box=True,
        )
        if len(results) != 1:
            raise BatchWordBoxError(
                f"expected one PP-OCRv6 result on page {page}, received {len(results)}"
            )
        payload = results[0].json["res"]
        geometry = _validate_payload(payload)
        scores = [float(score) for score in payload["rec_scores"]]
        expected_page = _expected_page_identity(
            page=page,
            dataset_role=args.dataset_role,
            batch_identity=batch_identity,
            render=render,
            git=git,
            configuration=configuration,
            runtime_identity=runtime_identity,
        )
        page_manifest = {
            **expected_page,
            "metrics": {
                **geometry,
                "wall_seconds": time.perf_counter() - page_started,
                "minimum_line_score": min(scores) if scores else None,
                "mean_line_score": statistics.fmean(scores) if scores else None,
                "lines_below_0_8": sum(score < 0.8 for score in scores),
                "lines_below_0_9": sum(score < 0.9 for score in scores),
            },
            "started_at": page_started_at.isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
        }
        _write_artifacts(output_directory / f"ppocrv6-page-{page:04d}", payload, page_manifest)
        recorded_pages[page] = _page_output_record(output_directory, page, expected_page)
        ordered_completed = [
            recorded_pages[record["page"]]
            for record in render_records
            if record["page"] in recorded_pages
        ]
        complete = len(ordered_completed) == len(render_records)
        state.update(
            state="OCR_COMPLETE" if complete else "PARTIAL",
            pages=ordered_completed,
            metrics=_aggregate(ordered_completed, state["sessions"]),
            updated_at=datetime.now(UTC).isoformat(),
            completed_at=datetime.now(UTC).isoformat() if complete else None,
        )
        _atomic_json(state_path, state)
        print(
            json.dumps(
                {
                    "status": "PAGE_COMPLETE",
                    "page": page,
                    "completed_pages": len(ordered_completed),
                    "requested_pages": len(render_records),
                    "metrics": page_manifest["metrics"],
                },
                sort_keys=True,
            ),
            flush=True,
        )
    print(json.dumps({"status": "PASS", "metrics": state["metrics"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
