#!/usr/bin/env python3
"""Re-OCR exact Gemini JSON rows and append one source-bound page version."""

from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

import fitz

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.gemini_json_first_page_render_v1 import (  # noqa: E402
    render_full_pdf_page_v1,
)
from bctc_ai.evaluation.gemini_json_first_provider_v1 import (  # noqa: E402
    GOOGLE_MODEL,
    OPENROUTER_SERVICE_TIER,
    call_gemini_json_first_v1,
    load_openrouter_api_key_v1,
)
from bctc_ai.evaluation.gemini_json_region_repair_v1 import (  # noqa: E402
    build_region_repair_prompt_v1,
    build_section_narrative_repair_prompt_v1,
    build_table_axis_repair_prompt_v1,
    decode_region_repair_text_v1,
    decode_section_narrative_repair_text_v1,
    decode_table_axis_repair_text_v1,
    merge_region_repair_v1,
    merge_section_narrative_repair_v1,
    merge_table_axis_repair_v1,
    region_repair_response_schema_v1,
    region_repair_targets_v1,
    repair_prompt_sha256_v1,
    section_narrative_repair_response_schema_v1,
    section_narrative_repair_targets_v1,
    table_axis_repair_response_schema_v1,
    table_axis_repair_targets_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    extraction_cache_key_v1,
    ingest_financial_page_extraction_v1,
    load_page_json_versions_v1,
    lookup_cached_page_extraction_v1,
    record_page_json_region_repair_v1,
)


class RunGeminiJsonRegionRepairV1Error(RuntimeError):
    pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--source-logical-name", required=True)
    parser.add_argument("--physical-page", type=int, required=True)
    parser.add_argument("--base-page-json-version-id", required=True)
    parser.add_argument("--target-id", action="append")
    parser.add_argument("--target-table-ref", action="append")
    parser.add_argument(
        "--repair-scope",
        choices=(
            "ROW_VALUES",
            "ROW_LABEL_AND_VALUES",
            "SECTION_NARRATIVES",
            "TABLE_PERIOD_AXIS",
            "TABLE_TITLE_AND_COLUMNS",
        ),
        default="ROW_VALUES",
    )
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--dpi", type=int, choices=(200, 300), default=300)
    parser.add_argument(
        "--openrouter-key-file",
        type=Path,
        default=ROOT / "docs/experiments/openrouter",
    )
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument(
        "--thinking-level",
        choices=("low", "medium", "high"),
        default="low",
    )
    parser.add_argument("--openrouter-retries", type=int, default=3)
    parser.add_argument("--retry-delay-seconds", type=float, default=5.0)
    return parser


def _write(path: Path, value: bytes) -> None:
    if path.exists():
        raise RunGeminiJsonRegionRepairV1Error(f"refusing to overwrite {path}")
    path.write_bytes(value)


def _render(args: argparse.Namespace) -> tuple[bytes, dict[str, Any], dict[str, Any]]:
    source = args.pdf.read_bytes()
    source_sha = sha256(source).hexdigest()
    with fitz.open(args.pdf) as document:
        if args.physical_page <= 0 or args.physical_page > document.page_count:
            raise RunGeminiJsonRegionRepairV1Error("physical page lies outside PDF")
        rendered = render_full_pdf_page_v1(
            document.load_page(args.physical_page - 1),
            physical_page=args.physical_page,
            dpi=args.dpi,
            source_sha256=source_sha,
        )
    document_record = {
        "source_logical_name": args.source_logical_name,
        "source_sha256": source_sha,
        "source_size_bytes": len(source),
    }
    return rendered.image, document_record, rendered.page


def _repair_projection_from_cached_page(
    cached_page: dict[str, Any], *, targets: list[dict[str, Any]], repair_scope: str
) -> dict[str, Any]:
    if repair_scope == "SECTION_NARRATIVES":
        return {
            "all_targets_transcribed": True,
            "sections": [
                {
                    "narratives_exact": cached_page["sections"][int(target["target_id"][1:]) - 1][
                        "narratives_exact"
                    ],
                    "target_id": target["target_id"],
                }
                for target in targets
            ],
            "uncertainty_exact": [],
        }
    if repair_scope in {"TABLE_PERIOD_AXIS", "TABLE_TITLE_AND_COLUMNS"}:
        tables = []
        for target in targets:
            section_id, table_id = target["target_id"].split(":")
            table = cached_page["sections"][int(section_id[1:]) - 1]["tables"][
                int(table_id[1:]) - 1
            ]
            tables.append(
                {
                    "columns_header_path_exact": [
                        column["header_path_exact"] for column in table["columns"]
                    ],
                    "table_title_exact": table["title_exact"],
                    "target_id": target["target_id"],
                }
            )
        return {
            "all_targets_transcribed": True,
            "tables": tables,
            "uncertainty_exact": [],
        }
    rows = []
    for target in targets:
        section_id, table_id, row_id = target["target_id"].split(":")
        row = cached_page["sections"][int(section_id[1:]) - 1]["tables"][int(table_id[1:]) - 1][
            "rows"
        ][int(row_id[1:]) - 1]
        rows.append(
            {
                "label_exact": row["label_exact"],
                "target_id": target["target_id"],
                "values_exact": row["values_exact"],
            }
        )
    return {
        "all_targets_transcribed": True,
        "rows": rows,
        "uncertainty_exact": [],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Execute one immutable row repair request and return its observation."""

    if not args.database.is_file():
        raise RunGeminiJsonRegionRepairV1Error("Gemini page database is absent")
    if args.artifact_dir.exists():
        if any(args.artifact_dir.iterdir()):
            raise RunGeminiJsonRegionRepairV1Error("artifact directory must be empty")
    else:
        args.artifact_dir.mkdir(parents=True)

    selected = load_page_json_versions_v1(
        args.database,
        page_json_version_ids=[args.base_page_json_version_id],
    )[0]
    image, document, page = _render(args)
    if (
        selected["source_sha256"] != document["source_sha256"]
        or selected["source_logical_name"] != document["source_logical_name"]
        or selected["physical_page"] != args.physical_page
        or selected["render_dpi"] != args.dpi
        or selected["image_sha256"] != page["image_sha256"]
    ):
        raise RunGeminiJsonRegionRepairV1Error(
            "base page version does not bind the rendered source page"
        )

    if args.repair_scope in {
        "SECTION_NARRATIVES",
        "TABLE_PERIOD_AXIS",
        "TABLE_TITLE_AND_COLUMNS",
    }:
        if not args.target_table_ref:
            raise RunGeminiJsonRegionRepairV1Error("table/section target frontier is empty")
        table_refs = []
        for value in args.target_table_ref:
            parts = value.split(":")
            if len(parts) != 2:
                raise RunGeminiJsonRegionRepairV1Error("table-axis target ref is invalid")
            table_refs.append({"section_id": parts[0], "table_id": parts[1]})
        if args.repair_scope == "SECTION_NARRATIVES":
            targets = section_narrative_repair_targets_v1(
                selected["page_json"], table_refs=table_refs
            )
            prompt = build_section_narrative_repair_prompt_v1(
                base_page_json_version_id=args.base_page_json_version_id,
                targets=targets,
            )
            schema = section_narrative_repair_response_schema_v1()
        else:
            targets = table_axis_repair_targets_v1(selected["page_json"], table_refs=table_refs)
            prompt = build_table_axis_repair_prompt_v1(
                base_page_json_version_id=args.base_page_json_version_id,
                targets=targets,
            )
            schema = table_axis_repair_response_schema_v1()
    else:
        if not args.target_id:
            raise RunGeminiJsonRegionRepairV1Error("row repair target frontier is empty")
        targets = region_repair_targets_v1(
            selected["page_json"],
            target_ids=args.target_id,
            context_radius={"low": 1, "medium": 2, "high": 3}[args.thinking_level],
            allow_label_change=args.repair_scope == "ROW_LABEL_AND_VALUES",
        )
        prompt = build_region_repair_prompt_v1(
            base_page_json_version_id=args.base_page_json_version_id,
            targets=targets,
        )
        schema = region_repair_response_schema_v1()
    prompt_sha = repair_prompt_sha256_v1(prompt)
    schema_sha = canonical_json_sha256_v1(schema)
    prompt_variant = {
        "ROW_LABEL_AND_VALUES": "region-repair-row-label-and-values",
        "ROW_VALUES": "region-repair-row-values",
        "SECTION_NARRATIVES": "region-repair-section-narratives",
        "TABLE_PERIOD_AXIS": "region-repair-table-period-axis",
        "TABLE_TITLE_AND_COLUMNS": "region-repair-table-title-and-columns",
    }[args.repair_scope]
    _write(args.artifact_dir / "prompt.txt", prompt.encode("utf-8"))
    _write(
        args.artifact_dir / "response-schema.json",
        canonical_json_bytes_v1(schema) + b"\n",
    )
    _write(args.artifact_dir / "targets.json", canonical_json_bytes_v1(targets) + b"\n")

    cache_key = extraction_cache_key_v1(
        source_sha256=document["source_sha256"],
        source_logical_name=document["source_logical_name"],
        image_sha256=page["image_sha256"],
        prompt_sha256=prompt_sha,
        response_schema_sha256=schema_sha,
        requested_model=GOOGLE_MODEL,
        requested_service_tier=OPENROUTER_SERVICE_TIER,
        thinking_level=args.thinking_level,
        prompt_variant=prompt_variant,
        output_contract_mode="JSON_SCHEMA",
    )
    cached = lookup_cached_page_extraction_v1(args.database, cache_key)
    result = None
    if cached is None:
        result = call_gemini_json_first_v1(
            google_api_keys=None,
            openrouter_api_key=load_openrouter_api_key_v1(args.openrouter_key_file),
            image=image,
            media_type="image/png",
            prompt=prompt,
            response_schema=schema,
            output_contract_mode="JSON_SCHEMA",
            execution_policy="OPENROUTER_PILOT",
            timeout_seconds=args.timeout_seconds,
            openrouter_retries=args.openrouter_retries,
            retry_delay_seconds=args.retry_delay_seconds,
            thinking_level=args.thinking_level,
        )
        response_text = result.output_text
    else:
        response_text = canonical_json_bytes_v1(
            _repair_projection_from_cached_page(
                cached["page_json"], targets=targets, repair_scope=args.repair_scope
            )
        ).decode("utf-8")
    if args.repair_scope == "SECTION_NARRATIVES":
        repair = decode_section_narrative_repair_text_v1(response_text, targets=targets)
        merged, repair_receipt = merge_section_narrative_repair_v1(
            selected["page_json"],
            base_page_json_version_id=args.base_page_json_version_id,
            targets=targets,
            repair=repair,
        )
    elif args.repair_scope in {"TABLE_PERIOD_AXIS", "TABLE_TITLE_AND_COLUMNS"}:
        repair = decode_table_axis_repair_text_v1(response_text, targets=targets)
        merged, repair_receipt = merge_table_axis_repair_v1(
            selected["page_json"],
            base_page_json_version_id=args.base_page_json_version_id,
            targets=targets,
            repair=repair,
        )
    else:
        repair = decode_region_repair_text_v1(response_text, targets=targets)
        merged, repair_receipt = merge_region_repair_v1(
            selected["page_json"],
            base_page_json_version_id=args.base_page_json_version_id,
            targets=targets,
            repair=repair,
        )
    if cached is None:
        assert result is not None
        identities = ingest_financial_page_extraction_v1(
            args.database,
            document=document,
            page=page,
            prompt_variant=prompt_variant,
            output_contract_mode="JSON_SCHEMA",
            prompt_sha256=prompt_sha,
            response_schema_sha256=schema_sha,
            requested_model=GOOGLE_MODEL,
            requested_service_tier=OPENROUTER_SERVICE_TIER,
            thinking_level=args.thinking_level,
            provider_result=result,
            page_json=merged,
        )
        provider = {
            "model": result.provider_model,
            "name": result.provider_name,
            "response_id_sha256": result.response_id_sha256,
            "service_tier": result.service_tier,
        }
        usage = result.usage
        attempts = list(result.attempts)
    else:
        if cached["page_json"] != merged:
            raise RunGeminiJsonRegionRepairV1Error("cached repair projection does not replay")
        identities = cached["database_identities"]
        provider = cached["provider"]
        usage = {
            "actual_cost_usd": "0",
            "cache_hit": True,
            "cached_input_tokens": 0,
            "cost_disposition": "CACHE_REUSE_ZERO_INCREMENTAL_COST",
            "input_tokens": 0,
            "output_tokens": 0,
            "source_extraction_run_id": identities["extraction_run_id"],
            "source_usage": cached["source_usage"],
            "thought_tokens": 0,
            "total_tokens": 0,
        }
        attempts = []
    lineage = record_page_json_region_repair_v1(
        args.database,
        merged_page_json_version_id=identities["page_json_version_id"],
        receipt=repair_receipt,
    )
    if result is not None:
        raw = result.raw_response_bytes
        if not raw.endswith(b"\n"):
            raw += b"\n"
        _write(args.artifact_dir / "raw-response.json", raw)
    _write(args.artifact_dir / "repair.json", canonical_json_bytes_v1(repair) + b"\n")
    _write(args.artifact_dir / "merged-page.json", canonical_json_bytes_v1(merged) + b"\n")
    _write(
        args.artifact_dir / "repair-receipt.json",
        canonical_json_bytes_v1(repair_receipt) + b"\n",
    )
    observation = {
        "attempts": attempts,
        "cache_hit": cached is not None,
        "database_identities": identities,
        "format_version": "GEMINI_JSON_REGION_REPAIR_RUN_V1",
        "lineage": lineage,
        "provider": provider,
        "source": {
            **document,
            "image_sha256": page["image_sha256"],
            "physical_page": args.physical_page,
            "render_dpi": args.dpi,
            "thinking_level": args.thinking_level,
        },
        "usage": usage,
    }
    observation["observation_id"] = "gjfrrunv1:observation:" + canonical_json_sha256_v1(observation)
    _write(
        args.artifact_dir / "observation.json",
        canonical_json_bytes_v1(observation) + b"\n",
    )
    return observation


def main() -> int:
    print(json.dumps(run(_parser().parse_args()), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
