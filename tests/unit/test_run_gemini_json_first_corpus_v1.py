from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import fitz
import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "scripts/experiments/run_gemini_json_first_corpus_v1.py"
_SPEC = importlib.util.spec_from_file_location("run_gemini_json_first_corpus_v1", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
target = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(target)


def _pdf(path: Path, pages: int) -> None:
    document = fitz.open()
    for _ in range(pages):
        document.new_page()
    document.save(path)
    document.close()


def test_inventory_binds_exact_selected_pdf_source_and_pages(tmp_path, monkeypatch) -> None:
    root = tmp_path / "project"
    (root / "vietstock_bctc" / "MBB").mkdir(parents=True)
    first = root / "vietstock_bctc" / "MBB" / "a.pdf"
    second = root / "vietstock_bctc" / "MBB" / "b.pdf"
    _pdf(first, 2)
    _pdf(second, 3)
    filings = []
    for path in (first, second):
        payload = path.read_bytes()
        filings.append(
            {
                "content_ref": {
                    "path": path.relative_to(root).as_posix(),
                    "sha256": __import__("hashlib").sha256(payload).hexdigest(),
                    "size_bytes": len(payload),
                }
            }
        )
    monkeypatch.setattr(
        target,
        "read_family_first_filing_inventory_v1",
        lambda project_root: {
            "filings": filings,
            "metrics": {"selected_filing_count": 2},
        },
    )
    inventory = target._inventory(root)
    assert [item["relative_path"] for item in inventory] == [
        "vietstock_bctc/MBB/a.pdf",
        "vietstock_bctc/MBB/b.pdf",
    ]
    assert [item["page_count"] for item in inventory] == [2, 3]
    assert all(len(item["source_sha256"]) == 64 for item in inventory)


def test_main_writes_one_read_only_canonical_plan(tmp_path, monkeypatch, capsys) -> None:
    root = tmp_path / "pdfs"
    root.mkdir()
    _pdf(root / "a.pdf", 2)
    output = tmp_path / "plan.json"
    monkeypatch.setattr(
        target,
        "_parser",
        lambda: type(
            "Parser",
            (),
            {
                "parse_args": lambda self: type(
                    "Args",
                    (),
                    {
                        "dpi": 300,
                        "google_batch_chunk_pages": 30,
                        "openrouter_page_fraction": "0.0",
                        "openrouter_workers": 5,
                        "output": output,
                        "project_root": root,
                    },
                )()
            },
        )(),
    )
    monkeypatch.setattr(
        target,
        "read_family_first_filing_inventory_v1",
        lambda project_root: {
            "filings": [
                {
                    "content_ref": {
                        "path": "a.pdf",
                        "sha256": __import__("hashlib")
                        .sha256((root / "a.pdf").read_bytes())
                        .hexdigest(),
                        "size_bytes": (root / "a.pdf").stat().st_size,
                    }
                }
            ],
            "metrics": {"selected_filing_count": 1},
        },
    )
    assert target.main() == 0
    plan = json.loads(output.read_bytes())
    assert plan["summary"]["page_count"] == 2
    assert output.stat().st_mode & 0o777 == 0o444
    assert json.loads(capsys.readouterr().out)["corpus_plan_id"] == plan["corpus_plan_id"]
    with pytest.raises(target.RunGeminiJsonFirstCorpusV1Error, match="overwrite"):
        target.main()
