#!/usr/bin/env python3
"""Build or replay the fixed 140-filing derivative schema sweep."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))
sys.path.insert(0, os.fspath(PROJECT_ROOT / "src"))

from bctc_ai.evaluation import (  # noqa: E402
    family_first_accounting_schema_mapping_v1 as accounting_mapping_v1,
)
from bctc_ai.evaluation import (  # noqa: E402
    family_first_document_evidence_store_v1 as document_store_v1,
)
from bctc_ai.evaluation import (  # noqa: E402
    family_first_stacked_period_schema_sweep_v1 as sweep_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_json_bytes_v1,
    same_typed_json_v1,
)
from scripts.experiments import run_family_first_accounting_pipeline_v1 as pipeline_v1  # noqa: E402
from scripts.experiments import run_family_first_topology_sweep_v1 as topology_cli  # noqa: E402

TOPOLOGY_PATH = Path("config/families/tm-derivative-financial-instruments-topology-v1.json")
LAYOUT_PATH = Path("config/families/tm-derivative-financial-instruments-layout-v1.json")
SCHEMA_BINDING_PATH = Path(
    "config/families/tm-derivative-financial-instruments-schema-binding-v1.json"
)
CHALLENGER_PATH = Path(
    "docs/experiments/E-0162-family-first-derivative-hosted-gemma4-numeric-challenger-v1.json"
)
OUTPUT_PATH = Path(
    "output/calibration/family-first-derivative-140-filing-schema-sweep-v1/result.json"
)


def _inputs(root: Path) -> tuple[dict[str, object], ...]:
    topology = topology_cli._family_spec(root, TOPOLOGY_PATH)
    layout = topology_cli._family_spec(root, LAYOUT_PATH)
    binding = topology_cli._family_spec(root, SCHEMA_BINDING_PATH)
    challenger = topology_cli._family_spec(root, CHALLENGER_PATH)
    family_id = "DERIVATIVE_FINANCIAL_INSTRUMENTS"
    if any(value.get("family_id", family_id) != family_id for value in (topology, layout, binding)):
        raise ValueError("fixed derivative specifications identify another family")
    nodes, _reference = accounting_mapping_v1._schema_graph(root)
    return topology, layout, binding, list(nodes.values()), challenger


def run_family_first_derivative_140_filing_schema_sweep_v1(
    project_root: Path,
    *,
    command: str,
    jobs: int = 12,
) -> dict[str, object]:
    """Build once or exact-replay the fixed all-filing derivative result."""

    if command not in {"build", "verify"} or type(jobs) is not int or jobs <= 0:
        raise ValueError("derivative sweep command or worker count drifted")
    root = project_root.resolve()
    topology, layout, binding, schema_graph, challenger = _inputs(root)
    output = root / OUTPUT_PATH
    persisted = None
    if command == "verify":
        persisted = pipeline_v1._read_canonical_object(output, "derivative 140-filing sweep")
    elif output.exists():
        raise ValueError("derivative 140-filing sweep destination already exists")
    capability = document_store_v1.authenticate_family_first_document_evidence_store_v1(root)
    result = sweep_v1.build_authenticated_family_first_stacked_period_schema_sweep_v1(
        capability,
        topology,
        layout,
        binding,
        schema_graph,
        challenger,
        jobs=jobs,
    )
    if command == "build":
        topology_cli._write_exclusive(output, canonical_json_bytes_v1(result) + b"\n")
    elif not same_typed_json_v1(persisted, result):
        raise ValueError("derivative 140-filing sweep exact replay differs")
    return {
        "metrics": result["metrics"],
        "output_path": OUTPUT_PATH.as_posix(),
        "sweep_id": result["sweep_id"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--jobs", default=12, type=int)
    args = parser.parse_args()
    result = run_family_first_derivative_140_filing_schema_sweep_v1(
        PROJECT_ROOT,
        command=args.command,
        jobs=args.jobs,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
