from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from bctc_ai.core.hashing import sha256_file

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_REAL_PANEL = [
    {
        "source_locator": ("SHB", 24),
        "line_count": 53,
        "result_ref": {
            "path": "output/development/bank-corpus-wave-1-role-b-page-reader-v1/full-v3/objects/sha256/f6/f66ec66cf70b85c07c877881daf7d207dec7b754efbcafc1c88507962b77a82b.json",
            "sha256": "f66ec66cf70b85c07c877881daf7d207dec7b754efbcafc1c88507962b77a82b",
            "size_bytes": 264475,
        },
        "render_ref": {
            "path": "output/development/bank-corpus-wave-1-role-b-page-reader-v1/full-v3/objects/sha256/43/43067bf4cb05b4ea8c7b526111bc170a3ef969f7aa79fd59a4f036201947772e.png",
            "sha256": "43067bf4cb05b4ea8c7b526111bc170a3ef969f7aa79fd59a4f036201947772e",
            "size_bytes": 932776,
        },
    },
    {
        "source_locator": ("NVB", 32),
        "line_count": 62,
        "result_ref": {
            "path": "output/development/bank-corpus-wave-1-role-b-page-reader-v1/full-v3/objects/sha256/67/67da86feb9886f8e5809065463595032ff5396b2dbdf118870830f4aa8720a5d.json",
            "sha256": "67da86feb9886f8e5809065463595032ff5396b2dbdf118870830f4aa8720a5d",
            "size_bytes": 219093,
        },
        "render_ref": {
            "path": "output/development/bank-corpus-wave-1-role-b-page-reader-v1/full-v3/objects/sha256/ce/ce1ffec996bb927bf2ce4b8a00b30202f189b05008de1914c2227508a2f05294.png",
            "sha256": "ce1ffec996bb927bf2ce4b8a00b30202f189b05008de1914c2227508a2f05294",
            "size_bytes": 58209,
        },
    },
    {
        "source_locator": ("NVB", 31),
        "line_count": 99,
        "result_ref": {
            "path": "output/development/bank-corpus-wave-1-role-b-page-reader-v1/full-v3/objects/sha256/5d/5d4d6463594591be053cdae6eae8aa1c0bcf3b1b8b8194acb399bfc4af6714f7.json",
            "sha256": "5d4d6463594591be053cdae6eae8aa1c0bcf3b1b8b8194acb399bfc4af6714f7",
            "size_bytes": 356248,
        },
        "render_ref": {
            "path": "output/development/bank-corpus-wave-1-role-b-page-reader-v1/full-v3/objects/sha256/f0/f08330fe0a4b654620e3e826bf3fbb288dfeeaf78a4a709a4b32663a19390b00.png",
            "sha256": "f08330fe0a4b654620e3e826bf3fbb288dfeeaf78a4a709a4b32663a19390b00",
            "size_bytes": 78858,
        },
    },
    {
        "source_locator": ("BVB", 27),
        "line_count": 48,
        "result_ref": {
            "path": "output/development/bank-corpus-wave-1-role-b-page-reader-v1/full-v3/objects/sha256/e1/e110fa22e5fdc6d023bc1a447c63d9ddd3e8dacc6fcfd4844a235ae4066332f7.json",
            "sha256": "e110fa22e5fdc6d023bc1a447c63d9ddd3e8dacc6fcfd4844a235ae4066332f7",
            "size_bytes": 191215,
        },
        "render_ref": {
            "path": "output/development/bank-corpus-wave-1-role-b-page-reader-v1/full-v3/objects/sha256/f2/f2f9da5138c26763a144b9f0907b6456604a91623a97806074a10a26ce2fdf3f.png",
            "sha256": "f2f9da5138c26763a144b9f0907b6456604a91623a97806074a10a26ce2fdf3f",
            "size_bytes": 1147722,
        },
    },
    {
        "source_locator": ("BAB", 44),
        "line_count": 125,
        "result_ref": {
            "path": "output/development/bank-corpus-wave-1-role-b-page-reader-v1/full-v3/objects/sha256/ee/ee9428ce59f9eab94e5f4dda22e987efd22a6a08b8df4bec025f95d0908df131.json",
            "sha256": "ee9428ce59f9eab94e5f4dda22e987efd22a6a08b8df4bec025f95d0908df131",
            "size_bytes": 398673,
        },
        "render_ref": {
            "path": "output/development/bank-corpus-wave-1-role-b-page-reader-v1/full-v3/objects/sha256/64/64165a44555ff64543880632dc2106b498517f3382550a25541a07914133aad5.png",
            "sha256": "64165a44555ff64543880632dc2106b498517f3382550a25541a07914133aad5",
            "size_bytes": 1804451,
        },
    },
]


def _module():
    path = (
        Path(__file__).resolve().parents[2]
        / "scripts/experiments/build_multibank_all_line_vietocr_request_v2.py"
    )
    specification = importlib.util.spec_from_file_location(
        "build_multibank_all_line_vietocr_request_v2", path
    )
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _object_ref(root: Path, path: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _page(root: Path, name: str, boxes: list[list[int]]) -> dict[str, Any]:
    render = root / f"objects/{name}.png"
    render.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (40, 30), "white")
    for index, (x0, y0, x1, y1) in enumerate(boxes):
        for x in range(x0, x1):
            for y in range(y0, y1):
                image.putpixel((x, y), (20 + index, 40 + index, 60 + index))
    image.save(render, format="PNG", optimize=False, compress_level=6)
    render_ref = _object_ref(root, render)

    result = root / f"objects/{name}.json"
    _write_json(
        result,
        {
            "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V2",
            "input_render_ref": render_ref,
            "lines": [
                {
                    "raw_pixel_bbox": box,
                    "raw_text": f"must-not-be-consulted-{name}-{index}",
                }
                for index, box in enumerate(boxes)
            ],
        },
    )
    return {"render_ref": render_ref, "result_ref": _object_ref(root, result)}


def _input(root: Path, pages: list[dict[str, Any]]) -> Path:
    path = root / "inputs/batch.json"
    _write_json(
        path,
        {
            "dataset_role": "DEVELOPMENT_REPLAY",
            "format_version": "V3_AUTHENTICATED_LINE_MULTIPAGE_BATCH_INPUT_V1",
            "pages": pages,
        },
    )
    return path


def _clean_git(*args: str) -> str:
    if args == ("status", "--porcelain"):
        return ""
    if args == ("rev-parse", "HEAD"):
        return "0123456789abcdef0123456789abcdef01234567"
    raise AssertionError(args)


def test_freezes_every_line_with_opaque_page_ids_and_existing_reader_allowlist(
    tmp_path, monkeypatch
):
    module = _module()
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(module, "_git", _clean_git)
    first = _page(tmp_path, "render-one", [[0, 0, 5, 4], [8, 6, 18, 11]])
    second = _page(tmp_path, "render-two", [[35, 26, 40, 30]])
    input_path = _input(tmp_path, [first, second])

    summary = module.build_request(
        input_spec_path=input_path.relative_to(tmp_path),
        output_root=Path("generated/batch"),
    )

    assert summary == {
        "crop_manifest": "generated/batch/frozen/crop_manifest.json",
        "page_count": 2,
        "reader_request": "generated/batch/frozen/reader_request.json",
        "sample_count": 3,
    }
    manifest = json.loads((tmp_path / summary["crop_manifest"]).read_bytes())
    request = json.loads((tmp_path / summary["reader_request"]).read_bytes())
    assert manifest["format_version"] == module.MANIFEST_FORMAT
    assert manifest["sample_count"] == sum(
        page["authenticated_line_count"] for page in manifest["pages"]
    )
    assert [page["page_id"] for page in manifest["pages"]] == ["page-0001", "page-0002"]
    assert all(
        page["selected_line_count"] == page["authenticated_line_count"]
        for page in manifest["pages"]
    )
    assert manifest["selection_rule"] == module.SELECTION_RULE
    assert manifest["selection_rule"]["unions"] is False
    assert {sample["grouping"] for sample in manifest["samples"]} == {"LINE"}
    assert [sample["source_line_index"] for sample in manifest["samples"]] == [0, 1, 0]
    assert [sample["page_id"] for sample in manifest["samples"]] == [
        "page-0001",
        "page-0001",
        "page-0002",
    ]

    assert request["format_version"] == 2
    assert request["experiment_id"] == "VIETOCR_MULTI_BANK_FAMILY_OCR_BENCHMARK_V1"
    assert request["sample_count"] == 3
    assert all(
        set(sample) == {"category", "crop_path", "crop_sha256", "sample_id"}
        for sample in request["samples"]
    )
    serialized_request = json.dumps(request, ensure_ascii=False)
    for forbidden in (
        "bank",
        "family",
        "physical_page",
        "control_role",
        "raw_text",
        "must-not-be-consulted",
    ):
        assert forbidden not in serialized_request

    first_crop = Image.open(tmp_path / manifest["samples"][0]["crop_path"]).convert("RGB")
    # A source bbox clipped at the page edge is 13x8 after source padding, then +24x16 border.
    assert first_crop.size == (37, 24)
    assert first_crop.getpixel((0, 0)) == (255, 255, 255)
    assert first_crop.getpixel((12, 8)) == (20, 40, 60)
    final_crop = Image.open(tmp_path / manifest["samples"][2]["crop_path"]).convert("RGB")
    assert final_crop.size == (37, 24)
    assert final_crop.getpixel((24, 15)) == (20, 40, 60)


def test_crop_bytes_are_deterministic_for_same_authenticated_geometry(tmp_path, monkeypatch):
    module = _module()
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(module, "_git", _clean_git)
    input_path = _input(tmp_path, [_page(tmp_path, "same-page", [[2, 3, 20, 12]])])

    module.build_request(input_spec_path=input_path, output_root=Path("generated/first"))
    module.build_request(input_spec_path=input_path, output_root=Path("generated/second"))

    first = json.loads((tmp_path / "generated/first/frozen/crop_manifest.json").read_bytes())
    second = json.loads((tmp_path / "generated/second/frozen/crop_manifest.json").read_bytes())
    assert first["samples"][0]["crop_sha256"] == second["samples"][0]["crop_sha256"]
    assert first["samples"][0]["source_bbox_raw_pixels"] == [2, 3, 20, 12]
    assert first["samples"][0]["padded_source_bbox_raw_pixels"] == [0, 0, 28, 16]


def test_geometry_projection_does_not_consult_transcript_fields():
    module = _module()

    class GeometryOnlyLine(dict):
        def get(self, key, default=None):
            if key != "raw_pixel_bbox":
                raise AssertionError(f"forbidden transcript/semantic access: {key}")
            return super().get(key, default)

    lines = [
        GeometryOnlyLine(raw_pixel_bbox=[1, 2, 3, 4], raw_text="không được đọc"),
        GeometryOnlyLine(raw_pixel_bbox=[5, 6, 8, 9], raw_text="cũng không được đọc"),
    ]
    assert module._line_boxes(lines, width=10, height=10) == [(1, 2, 3, 4), (5, 6, 8, 9)]


def test_fails_on_dirty_tree_before_reading_input(tmp_path, monkeypatch):
    module = _module()
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(module, "_git", lambda *_args: " M tracked-file")

    with pytest.raises(module.MultibankAllLineRequestError, match="clean Git worktree"):
        module.build_request(
            input_spec_path=Path("does-not-exist.json"),
            output_root=Path("generated/batch"),
        )


@pytest.mark.parametrize("drift_field", ["sha256", "size_bytes"])
def test_rejects_exact_v3_result_or_render_ref_drift(tmp_path, monkeypatch, drift_field):
    module = _module()
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(module, "_git", _clean_git)
    page = _page(tmp_path, "drift-page", [[2, 3, 20, 12]])
    if drift_field == "sha256":
        page["render_ref"][drift_field] = "0" * 64
    else:
        page["result_ref"][drift_field] += 1
    input_path = _input(tmp_path, [page])

    with pytest.raises(module.MultibankAllLineRequestError, match="hash-drifted"):
        module.build_request(input_spec_path=input_path, output_root=Path("generated/batch"))


def test_rejects_bank_or_family_metadata_in_batch_input(tmp_path, monkeypatch):
    module = _module()
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(module, "_git", _clean_git)
    page = _page(tmp_path, "hidden-identity", [[2, 3, 20, 12]])
    page["bank"] = "FORBIDDEN"
    input_path = _input(tmp_path, [page])

    with pytest.raises(module.MultibankAllLineRequestError, match="non-allowlisted"):
        module.build_request(input_spec_path=input_path, output_root=Path("generated/batch"))


def test_exact_five_page_tier1_panel_is_hash_bound_with_387_authenticated_lines():
    module = _module()
    fixture_path = (
        PROJECT_ROOT / "tests/fixtures/source_structure/local_accounting_graph_v1_tier1_cases.json"
    )
    fixture = json.loads(fixture_path.read_bytes())
    cases_by_locator = {
        (
            case["provenance_only_not_inference"]["bank"],
            case["provenance_only_not_inference"]["physical_page"],
        ): case
        for case in fixture["cases"]
    }
    pages = []
    for expected in EXPECTED_REAL_PANEL:
        case = cases_by_locator[expected["source_locator"]]
        target = next(
            page
            for page in case["provenance_only_not_inference"]["page_inputs"]
            if page["relation"] == "TARGET"
        )
        assert target["result_ref"] == expected["result_ref"]
        assert target["render_ref"] == expected["render_ref"]
        pages.append(
            {
                "result_ref": target["result_ref"],
                "render_ref": target["render_ref"],
            }
        )

    missing = [
        reference["path"]
        for page in pages
        for reference in page.values()
        if not (PROJECT_ROOT / reference["path"]).is_file()
    ]
    if missing:
        pytest.skip(f"frozen V3 panel is not hydrated: {missing[0]}")

    validated = module._validated_input_pages(
        {
            "dataset_role": "DEVELOPMENT_REPLAY",
            "format_version": "V3_AUTHENTICATED_LINE_MULTIPAGE_BATCH_INPUT_V1",
            "pages": pages,
        }
    )
    line_counts = [len(result["lines"]) for result, *_ in validated]
    assert line_counts == [53, 62, 99, 48, 125]
    assert sum(line_counts) == 387
