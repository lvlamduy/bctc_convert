from __future__ import annotations

import hashlib
import importlib.util
import stat
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

import fitz
import pytest

from bctc_ai.core.coordinates import (
    points_to_millipoints,
    round_fraction_half_away_from_zero,
)
from bctc_ai.corpus.wave1_role_b_page_reader import (
    POLICY_RELATIVE_PATH,
    WaveOneRoleBPageReaderError,
    _route,
    build_wave_one_role_b_route_plan,
    canonical_json_bytes,
    load_wave_one_role_b_page_reader_policy,
)
from bctc_ai.ocr.ppocrv6_page_session import (
    PPOCRV6PageSessionError,
    _plain_json,
    model_neutral_page_result,
    validate_ppocrv6_payload,
)
from bctc_ai.rendering.page_reader import (
    apply_rational_matrix,
    coordinate_authority,
    public_coordinate_authority,
    render_composited_displayed_page,
)
from bctc_ai.storage.content_store import (
    ContentStoreIntegrityError,
    content_path,
    materialize_immutable_bytes,
)


def _load_cli_runner(project_root: Path):
    path = project_root / "scripts/corpus/run_wave1_role_b_page_reader.py"
    specification = importlib.util.spec_from_file_location("wave1_role_b_cli_test", path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def real_route_plan(project_root: Path) -> dict[str, object]:
    return build_wave_one_role_b_route_plan(project_root)


def test_real_route_plan_has_exact_corpus_accounting_and_sentinel(
    real_route_plan: dict[str, object],
) -> None:
    assert real_route_plan["accounting"] == {
        "selected_document_count": 27,
        "total_physical_page_count": 1_449,
        "route_page_counts": {
            "DOMINANT_RASTER_OCR": 1_356,
            "CAUSAL_NATIVE_TEXT": 93,
            "UNRESOLVED_PAGE_ROUTE": 0,
        },
        "ocr_render_dpi_page_counts": {"200": 1_250, "300": 106},
        "ocr_structural_stratum_count": 20,
        "structural_sentinel_page_count": 24,
        "statement_page_classification_count": 0,
        "table_classification_count": 0,
        "logical_row_reconstruction_count": 0,
        "financial_cell_interpretation_count": 0,
        "absence_declaration_count": 0,
    }
    assert [(record["bank"], record["page"]) for record in real_route_plan["sentinel"]] == [
        ("OCB", 27),
        ("OCB", 12),
        ("BID", 1),
        ("MBB", 53),
        ("MBB", 6),
        ("TCB", 60),
        ("MBB", 14),
        ("VBB", 2),
        ("MBB", 1),
        ("EIB", 40),
        ("HDB", 33),
        ("BID", 20),
        ("SSB", 26),
        ("HDB", 26),
        ("ACB", 1),
        ("BAB", 31),
        ("CTG", 58),
        ("CTG", 14),
        ("LPB", 18),
        ("LPB", 1),
        ("NVB", 16),
        ("VCB", 22),
        ("SSB", 63),
        ("CTG", 44),
    ]
    assert real_route_plan["selection_receipt_sha256"] == (
        "832cea1bee22f0bb08c422490dd2afe4e23bc91c56cdee6db382b1bfdc744d28"
    )
    assert real_route_plan["route_plan_sha256"] == (
        "82b4b387754060419da37a1616336bf32d6a9248945cfc3974b936dbeace609d"
    )


def test_routes_and_300_dpi_are_structural_not_bank_rules(
    real_route_plan: dict[str, object],
) -> None:
    pages = [page for document in real_route_plan["documents"] for page in document["pages"]]
    assert all(
        (page["render_dpi"] == 300) == (page["source_effective_dpi_band"] == "300")
        for page in pages
        if page["route"] == "DOMINANT_RASTER_OCR"
    )
    assert all(
        page["render_dpi"] is None for page in pages if page["route"] != "DOMINANT_RASTER_OCR"
    )
    assert all(
        "bank" not in document_projection and "relative_path" not in document_projection
        for document_projection in real_route_plan["route_plan_projection"]
    )
    assert (
        _route(
            {
                "has_dominant_displayed_raster": False,
                "substantive_nonzero_alpha_text_layer": True,
                "source_route_quadrant": "TEXT_LAYER_AND_NONDOMINANT_RASTER",
            }
        )
        == "CAUSAL_NATIVE_TEXT"
    )
    assert (
        _route(
            {
                "has_dominant_displayed_raster": False,
                "substantive_nonzero_alpha_text_layer": False,
                "source_route_quadrant": "NO_TEXT_LAYER_AND_NONDOMINANT_RASTER",
            }
        )
        == "UNRESOLVED_PAGE_ROUTE"
    )


def test_policy_has_dynamic_receipt_and_fails_closed_on_safety_drift(
    project_root: Path, tmp_path: Path
) -> None:
    policy = load_wave_one_role_b_page_reader_policy(
        project_root / POLICY_RELATIVE_PATH, project_root
    )
    assert policy["upstream"]["selection_receipt_binding"] == ("DERIVE_AND_RECONCILE_AT_RUNTIME")
    assert "selection_receipt_sha256" not in policy["upstream"]
    drifted_root = tmp_path / "root"
    target = drifted_root / POLICY_RELATIVE_PATH
    target.parent.mkdir(parents=True)
    text = (project_root / POLICY_RELATIVE_PATH).read_text(encoding="utf-8")
    target.write_text(
        text.replace("role_a_inputs_allowed: false", "role_a_inputs_allowed: true"),
        encoding="utf-8",
    )
    with pytest.raises(WaveOneRoleBPageReaderError, match="safety"):
        load_wave_one_role_b_page_reader_policy(target, drifted_root)


def test_policy_rejects_intermediate_config_symlink(project_root: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    policy_outside = outside / "corpus" / POLICY_RELATIVE_PATH.name
    policy_outside.parent.mkdir(parents=True)
    policy_outside.write_bytes((project_root / POLICY_RELATIVE_PATH).read_bytes())
    root = tmp_path / "root"
    root.mkdir()
    (root / "config").symlink_to(outside, target_is_directory=True)

    with pytest.raises(WaveOneRoleBPageReaderError, match="symlink"):
        load_wave_one_role_b_page_reader_policy(root / POLICY_RELATIVE_PATH, root)


@pytest.mark.parametrize(
    ("rotation", "first", "last"),
    [
        (0, (0, 0), (612_000, 792_000)),
        (90, (0, 792_000), (612_000, 0)),
        (180, (612_000, 792_000), (0, 0)),
        (270, (612_000, 0), (0, 792_000)),
    ],
)
def test_coordinate_authority_maps_corners_and_roundtrips_within_one_pixel(
    rotation: int,
    first: tuple[int, int],
    last: tuple[int, int],
) -> None:
    document = fitz.open()
    page = document.new_page(width=612, height=792)
    page.set_rotation(rotation)
    pixel_width = round(page.rect.width * 200 / 72)
    pixel_height = round(page.rect.height * 200 / 72)
    authority = coordinate_authority(page, pixel_width=pixel_width, pixel_height=pixel_height)
    forward = authority["_pixel_to_unrotated_matrix"]
    inverse = authority["_unrotated_to_pixel_matrix"]
    assert (
        tuple(
            round_fraction_half_away_from_zero(value)
            for value in apply_rational_matrix(forward, 0, 0)
        )
        == first
    )
    assert (
        tuple(
            round_fraction_half_away_from_zero(value)
            for value in apply_rational_matrix(forward, pixel_width, pixel_height)
        )
        == last
    )
    for pixel in (
        (0, 0),
        (pixel_width, 0),
        (0, pixel_height),
        (pixel_width, pixel_height),
        (37, 91),
    ):
        canonical = apply_rational_matrix(forward, *pixel)
        replayed = apply_rational_matrix(inverse, *canonical)
        assert abs(float(replayed[0]) - pixel[0]) <= 1
        assert abs(float(replayed[1]) - pixel[1]) <= 1
    public = public_coordinate_authority(authority)
    assert all(not key.startswith("_") for key in public)
    assert public["canonical_origin"] == "UNROTATED_CROP_BOX_TOP_LEFT_RELATIVE"
    document.close()


def test_shared_rounding_and_opaque_rgb_composite_render() -> None:
    assert round_fraction_half_away_from_zero(Fraction(1, 2)) == 1
    assert round_fraction_half_away_from_zero(Fraction(-1, 2)) == -1
    assert points_to_millipoints(0.0005) == 1
    document = fitz.open()
    page = document.new_page(width=72, height=72)
    page.insert_text((10, 20), "visible")
    rendered = render_composited_displayed_page(page, dpi=200)
    pixmap = fitz.Pixmap(rendered.payload)
    assert pixmap.n == 3 and not pixmap.alpha
    assert (rendered.pixel_width, rendered.pixel_height) == (200, 200)
    assert rendered.coordinate_authority["_pixel_to_unrotated_matrix"]
    document.close()


def _valid_ocr_payload() -> dict[str, object]:
    return {
        "return_word_box": True,
        "rec_texts": ["100"],
        "rec_scores": [0.95],
        "rec_polys": [[[1, 1], [20, 1], [20, 10], [1, 10]]],
        "rec_boxes": [[1, 1, 20, 10]],
        "text_word_boxes": [[[1, 1, 20, 10]]],
        "text_word": [["100"]],
    }


def test_ppocr_payload_validation_and_model_neutral_geometry() -> None:
    payload = _valid_ocr_payload()
    assert validate_ppocrv6_payload(payload, pixel_width=100, pixel_height=200) == {
        "line_count": 1,
        "word_token_count": 1,
    }
    document = fitz.open()
    page = document.new_page(width=36, height=72)
    authority = coordinate_authority(page, pixel_width=100, pixel_height=200)
    result = model_neutral_page_result(payload, coordinate_authority=authority)
    assert result["status"] == "OCR_WORD_BOX_READ_COMPLETE"
    assert result["lines"][0]["raw_text"] == "100"
    assert result["source_blank_claimed"] is False
    assert "_pixel_to_unrotated_matrix" not in result["coordinate_authority"]
    document.close()


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload.clear(),
        lambda payload: payload["rec_scores"].__setitem__(0, float("nan")),
        lambda payload: payload["rec_polys"][0][0].__setitem__(0, float("inf")),
        lambda payload: payload["rec_boxes"].__setitem__(0, [1, 2, 3]),
        lambda payload: payload["rec_scores"].__setitem__(0, True),
        lambda payload: payload["text_word"].__setitem__(0, []),
        lambda payload: payload["rec_polys"].__setitem__(0, [[1, 1], [2, 2], [3, 3]]),
        lambda payload: payload["rec_boxes"].__setitem__(0, [-1, 1, 20, 10]),
        lambda payload: payload["rec_boxes"].__setitem__(0, [1, 1, 1, 10]),
        lambda payload: payload["rec_polys"].__setitem__(0, [[1, 1], [2, 2], [3, 3], [4, 4]]),
    ],
)
def test_ppocr_payload_rejects_adversarial_shapes_and_numbers(mutation) -> None:
    payload = deepcopy(_valid_ocr_payload())
    mutation(payload)
    with pytest.raises(PPOCRV6PageSessionError):
        validate_ppocrv6_payload(payload, pixel_width=100, pixel_height=200)


def test_json_boundaries_reject_nonfinite_values() -> None:
    with pytest.raises(ValueError):
        canonical_json_bytes({"score": float("nan")})
    with pytest.raises(PPOCRV6PageSessionError):
        _plain_json({"score": float("inf")})


def test_generated_content_objects_are_immutable_and_reusable(tmp_path: Path) -> None:
    store = tmp_path / "objects"
    first, digest = materialize_immutable_bytes(b"evidence", store, suffix=".json")
    second, repeated = materialize_immutable_bytes(b"evidence", store, suffix=".json")
    assert first == second == content_path(store.resolve(), digest, ".json")
    assert repeated == digest
    assert first.read_bytes() == b"evidence"
    first.chmod(0o644)
    first.write_bytes(b"drift")
    with pytest.raises(ContentStoreIntegrityError, match="wrong hash"):
        materialize_immutable_bytes(b"evidence", store, suffix=".json")


def test_content_store_rejects_intermediate_symlink(tmp_path: Path) -> None:
    store = tmp_path / "objects"
    outside = tmp_path / "outside"
    store.mkdir()
    outside.mkdir()
    (store / "sha256").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ContentStoreIntegrityError, match="hierarchy"):
        materialize_immutable_bytes(b"evidence", store, suffix=".json")
    assert list(outside.iterdir()) == []


def test_content_store_does_not_delete_foreign_temp_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = tmp_path / "objects"
    payload = b"evidence"
    digest = hashlib.sha256(payload).hexdigest()
    shard = store / "sha256" / digest[:2]
    shard.mkdir(parents=True)
    foreign = shard / f".{digest}.json.fixed.tmp"
    foreign.write_bytes(b"foreign")
    monkeypatch.setattr("bctc_ai.storage.content_store.secrets.token_hex", lambda _size: "fixed")
    with pytest.raises(FileExistsError):
        materialize_immutable_bytes(payload, store, suffix=".json")
    assert foreign.read_bytes() == b"foreign"


def test_content_store_rejects_equal_but_writable_object(tmp_path: Path) -> None:
    store = tmp_path / "objects"
    path, _digest = materialize_immutable_bytes(b"evidence", store, suffix=".json")
    path.chmod(0o666)
    with pytest.raises(ContentStoreIntegrityError, match="wrong hash"):
        materialize_immutable_bytes(b"evidence", store, suffix=".json")


def test_content_store_links_only_read_only_owned_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import bctc_ai.storage.content_store as store_module

    observed_modes: list[int] = []
    real_link = store_module.os.link

    def checked_link(source, destination, **kwargs):
        identity = store_module.os.stat(
            source,
            dir_fd=kwargs["src_dir_fd"],
            follow_symlinks=False,
        )
        observed_modes.append(stat.S_IMODE(identity.st_mode))
        return real_link(source, destination, **kwargs)

    monkeypatch.setattr(store_module.os, "link", checked_link)
    materialize_immutable_bytes(b"evidence", tmp_path / "objects", suffix=".json")
    assert observed_modes == [0o444]


def test_cli_plan_publication_is_fixed_atomic_and_read_only(
    project_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _load_cli_runner(project_root)
    monkeypatch.setattr(runner, "PROJECT_ROOT", tmp_path)
    output = (
        tmp_path / "output/development/bank-corpus-wave-1-role-b-page-reader-v1/"
        "wave-1-role-b-page-read-plan.json"
    )
    runner._exclusive_write(output, b"sealed-plan")
    assert output.read_bytes() == b"sealed-plan"
    assert stat.S_IMODE(output.stat().st_mode) == 0o444
    with pytest.raises(FileExistsError):
        runner._exclusive_write(output, b"replacement")


def test_cli_plan_publication_rejects_intermediate_symlink(
    project_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _load_cli_runner(project_root)
    monkeypatch.setattr(runner, "PROJECT_ROOT", tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "output").mkdir()
    (tmp_path / "output/development").symlink_to(outside, target_is_directory=True)
    output = (
        tmp_path / "output/development/bank-corpus-wave-1-role-b-page-reader-v1/"
        "wave-1-role-b-page-read-plan.json"
    )
    with pytest.raises(OSError):
        runner._exclusive_write(output, b"sealed-plan")
    assert list(outside.iterdir()) == []


def test_cli_plan_publication_preserves_foreign_temp_collision(
    project_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = _load_cli_runner(project_root)
    monkeypatch.setattr(runner, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(runner.secrets, "token_hex", lambda _size: "fixed")
    parent = tmp_path / "output/development/bank-corpus-wave-1-role-b-page-reader-v1"
    parent.mkdir(parents=True)
    output = parent / "wave-1-role-b-page-read-plan.json"
    foreign = parent / f".{output.name}.fixed.tmp"
    foreign.write_bytes(b"foreign")
    with pytest.raises(FileExistsError):
        runner._exclusive_write(output, b"sealed-plan")
    assert foreign.read_bytes() == b"foreign"
