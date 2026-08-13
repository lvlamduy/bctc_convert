from __future__ import annotations

import argparse
import json
from pathlib import Path

from bctc_ai.core.hashing import sha256_file
from bctc_ai.evaluation.tatr_structure_calibration_v1 import (
    ArtifactPin,
    TatrRunPin,
    score_tatr_structure_panel,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PANEL_ROOT = Path("output/development/multibank-table-structure-calibration-v1")
DEFAULT_TRUTH = Path("docs/experiments/multibank-table-structure-calibration-truth-v1.json")
DEFAULT_OUTPUT = DEFAULT_PANEL_ROOT / "tatr-v1.1-all" / "calibration_score.json"


def _pin(path: Path) -> ArtifactPin:
    resolved = path.resolve() if path.is_absolute() else (PROJECT_ROOT / path).resolve()
    return ArtifactPin(path=resolved, sha256=sha256_file(resolved))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Authenticate and score the frozen multi-bank TATR structure panel"
    )
    parser.add_argument("--panel-root", type=Path, default=DEFAULT_PANEL_ROOT)
    parser.add_argument("--source-gold", type=Path, default=DEFAULT_TRUTH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    panel_root = (
        args.panel_root.resolve()
        if args.panel_root.is_absolute()
        else (PROJECT_ROOT / args.panel_root).resolve()
    )
    output = (
        args.output.resolve()
        if args.output.is_absolute()
        else (PROJECT_ROOT / args.output).resolve()
    )
    if output.exists():
        raise FileExistsError(f"refusing to overwrite score artifact: {output}")
    run_root = panel_root / "tatr-v1.1-all"
    run_pins = tuple(
        TatrRunPin(
            sample_id=f"table-{ordinal:04d}",
            result=_pin(run_root / f"table-{ordinal:04d}" / "structure_result.json"),
            run_manifest=_pin(run_root / f"table-{ordinal:04d}" / "run_manifest.json"),
        )
        for ordinal in range(1, 8)
    )
    scored = score_tatr_structure_panel(
        PROJECT_ROOT,
        crop_manifest=_pin(panel_root / "frozen" / "crop_manifest.json"),
        model_request=_pin(panel_root / "frozen" / "model_request.json"),
        source_gold=_pin(args.source_gold),
        tatr_runs=run_pins,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(scored, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": output.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256_file(output),
                "status": scored["status"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
