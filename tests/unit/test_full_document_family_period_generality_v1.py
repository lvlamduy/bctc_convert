from __future__ import annotations

import ast
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_ROOT = PROJECT_ROOT / "scripts" / "experiments"
LITERAL_REPORTING_YEAR = re.compile(r"(?<!\d)20\d{2}(?!\d)")


def test_family_scanners_and_variant_graphs_do_not_pin_one_reporting_year() -> None:
    paths = sorted(EXPERIMENT_ROOT.glob("scan_*_full_document_vietocr_v1.py")) + sorted(
        EXPERIMENT_ROOT.glob("*_variant_graph_v1.py")
    )
    assert len(list(EXPERIMENT_ROOT.glob("scan_*_full_document_vietocr_v1.py"))) == 51
    assert paths

    violations: list[str] = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and type(node.value) is str
                and LITERAL_REPORTING_YEAR.search(node.value) is not None
            ):
                violations.append(f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}:{node.value!r}")

    assert violations == []
