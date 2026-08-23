from __future__ import annotations

import copy
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from bctc_ai.evaluation import family_first_document_evidence_store_v1 as store_v1
from bctc_ai.evaluation import family_first_ocr_query_cache_v1 as cache_v1
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _database(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    cache_v1._create_schema(connection)
    connection.execute(
        "INSERT INTO metadata(key, value) VALUES ('format_version', ?)",
        ('"FAMILY_FIRST_OCR_QUERY_CACHE_V1"',),
    )
    connection.execute(
        "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (1, "document-1", "ACB", 2025, "ANNUAL", "CONSOLIDATED", "a.pdf", "a" * 64, 1, 3, 3),
    )
    for page in range(1, 4):
        connection.execute(
            "INSERT INTO pages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (1, page, 1, 100, 200, f"{page}" * 64, page, f"p{page}.json", "b" * 64, 1),
        )
        connection.execute(
            "INSERT INTO lines VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                page,
                1,
                page,
                0,
                f"sample-{page}",
                1,
                2,
                20,
                10,
                f"crop-{page}.png",
                "c" * 64,
                1,
                f"Trang {page}",
                f"Trang {page}",
                f"trang {page}",
                0.9,
                20,
                32,
                str(page),
                0.8,
            ),
        )
    connection.commit()
    connection.close()


def _packet() -> dict:
    material = {
        "assurance": "AUDITED",
        "bank_provenance": "ACB",
        "document_evidence_root_sha256": "d" * 64,
        "document_id": "document-1",
        "document_ordinal": 1,
        "line_count": 3,
        "page_count": 3,
        "period": "ANNUAL",
        "scope": "CONSOLIDATED",
        "source_pdf_ref": {"path": "a.pdf", "sha256": "a" * 64, "size_bytes": 1},
        "year": 2025,
    }
    return {**material, "packet_id": "ffdesv1:document:" + canonical_json_sha256_v1(material)}


def test_cache_selected_page_reader_pushes_filter_into_sqlite(tmp_path: Path) -> None:
    database = tmp_path / "cache.sqlite3"
    _database(database)

    selected = cache_v1.read_cached_selected_joined_pages_v1(database, 1, selected_pages=(2,))

    assert [page["page_sequence"] for page in selected["joined_pages"]] == [2]
    assert selected["joined_pages"][0]["lines"][0]["sample_id"] == "sample-2"
    assert selected["selected_page_dimensions"][0]["render_sha256"] == "2" * 64
    assert selected["selection_id"].startswith("ffoqcv1:selection:")


def test_cache_selected_page_reader_preserves_registered_zero_line_page(
    tmp_path: Path,
) -> None:
    database = tmp_path / "cache.sqlite3"
    _database(database)
    connection = sqlite3.connect(database)
    connection.execute("DELETE FROM lines WHERE document_ordinal = 1 AND physical_page = 3")
    connection.execute(
        "UPDATE pages SET line_count = 0 WHERE document_ordinal = 1 AND physical_page = 3"
    )
    connection.execute("UPDATE documents SET line_count = 2 WHERE document_ordinal = 1")
    connection.commit()
    connection.close()

    selected = cache_v1.read_cached_selected_joined_pages_v1(
        database,
        1,
        selected_pages=(3,),
    )

    assert selected["joined_pages"] == [{"lines": [], "page_sequence": 3, "page_width": 100}]
    assert selected["selected_page_dimensions"] == [
        {
            "physical_page": 3,
            "pixel_height": 200,
            "pixel_width": 100,
            "render_sha256": "3" * 64,
            "render_size_bytes": 3,
        }
    ]


def test_authenticated_selected_page_reader_binds_packet_and_rejects_bad_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "cache.sqlite3"
    _database(database)
    packet = _packet()
    state = SimpleNamespace(
        database_path=database,
        manifest={
            "documents": [packet],
            "manifest_id": "ffdesv1:manifest:" + "e" * 64,
            "metrics": {"document_count": 1},
        },
    )
    monkeypatch.setattr(store_v1, "_live_store", lambda _capability: state)

    selected = store_v1.read_authenticated_family_first_document_selected_pages_v1(
        object(), document_ordinal=1, selected_pages=(1, 3)
    )

    assert selected["document_packet"] == packet
    assert [page["page_sequence"] for page in selected["joined_pages"]] == [1, 3]
    assert selected["state"] == "AUTHENTICATED_IMMUTABLE_SQLITE_SELECTED_PAGE_EVIDENCE"
    material = dict(selected)
    identity = material.pop("snapshot_id")
    assert identity == "ffdesv1:selected:" + canonical_json_sha256_v1(material)

    with pytest.raises(
        store_v1.FamilyFirstDocumentEvidenceStoreV1Error,
        match="selected-page identity",
    ):
        store_v1.read_authenticated_family_first_document_selected_pages_v1(
            object(), document_ordinal=1, selected_pages=(3, 1)
        )


@pytest.mark.parametrize("pages", [(2, 2), (3, 1), (4,)])
def test_cache_selected_page_reader_rejects_duplicate_unordered_or_oob_pages(
    tmp_path: Path, pages: tuple[int, ...]
) -> None:
    database = tmp_path / "cache.sqlite3"
    _database(database)
    with pytest.raises(cache_v1.FamilyFirstOcrQueryCacheV1Error):
        cache_v1.read_cached_selected_joined_pages_v1(database, 1, selected_pages=pages)


def test_cache_selected_page_reader_rejects_a_line_ordinal_gap(tmp_path: Path) -> None:
    database = tmp_path / "cache.sqlite3"
    _database(database)
    connection = sqlite3.connect(database)
    connection.execute(
        "UPDATE lines SET line_ordinal = 2 WHERE document_ordinal = 1 AND physical_page = 2"
    )
    connection.commit()
    connection.close()

    with pytest.raises(
        cache_v1.FamilyFirstOcrQueryCacheV1Error,
        match="line order",
    ):
        cache_v1.read_cached_selected_joined_pages_v1(database, 1, selected_pages=(2,))


def test_authenticated_selected_page_reader_rejects_crosslink_and_selection_hash_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "cache.sqlite3"
    _database(database)
    packet = _packet()
    state = SimpleNamespace(
        database_path=database,
        manifest={
            "documents": [packet],
            "manifest_id": "ffdesv1:manifest:" + "e" * 64,
            "metrics": {"document_count": 1},
        },
    )
    monkeypatch.setattr(store_v1, "_live_store", lambda _capability: state)
    genuine = cache_v1.read_cached_selected_joined_pages_v1(database, 1, selected_pages=(2,))

    digest_drift = copy.deepcopy(genuine)
    digest_drift["joined_pages"][0]["lines"][0]["vietocr_text"] = "forged"
    monkeypatch.setattr(
        store_v1.cache_v1,
        "read_cached_selected_joined_pages_v1",
        lambda *_args, **_kwargs: digest_drift,
    )
    with pytest.raises(
        store_v1.FamilyFirstDocumentEvidenceStoreV1Error,
        match="differs from its authenticated document packet",
    ):
        store_v1.read_authenticated_family_first_document_selected_pages_v1(
            object(), document_ordinal=1, selected_pages=(2,)
        )

    crosslinked = copy.deepcopy(genuine)
    crosslinked["document_id"] = "another-document"
    crosslinked_material = copy.deepcopy(crosslinked)
    crosslinked_material.pop("selection_id")
    crosslinked["selection_id"] = "ffoqcv1:selection:" + canonical_json_sha256_v1(
        crosslinked_material
    )
    monkeypatch.setattr(
        store_v1.cache_v1,
        "read_cached_selected_joined_pages_v1",
        lambda *_args, **_kwargs: crosslinked,
    )
    with pytest.raises(
        store_v1.FamilyFirstDocumentEvidenceStoreV1Error,
        match="differs from its authenticated document packet",
    ):
        store_v1.read_authenticated_family_first_document_selected_pages_v1(
            object(), document_ordinal=1, selected_pages=(2,)
        )


def test_formal_topology_recompute_bypasses_disposable_self_rehashed_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = SimpleNamespace(
        database_path=tmp_path / "authenticated.sqlite3",
        manifest={"metrics": {"document_count": 2}},
    )
    calls = []
    monkeypatch.setattr(store_v1, "_live_store", lambda _capability: state)
    monkeypatch.setattr(
        store_v1.cache_v1,
        "scan_cached_accounting_family_topology_v1",
        lambda database, spec, *, document_ordinals, jobs: (
            calls.append((database, spec, document_ordinals, jobs))
            or ({"scan_id": "direct-1"}, {"scan_id": "direct-2"})
        ),
    )
    # A forged but internally self-rehashed disposable cache must be irrelevant
    # to the formal source-row recomputation path.
    monkeypatch.setattr(
        store_v1.cache_v1,
        "read_cached_topology_results_v1",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("disposable topology cache was consulted")
        ),
    )
    monkeypatch.setattr(
        store_v1.cache_v1,
        "refresh_cached_topology_results_v1",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("disposable topology cache was refreshed")
        ),
    )

    scans = store_v1.recompute_authenticated_family_first_topology_scans_v1(
        object(), {"family_id": "TEST"}, jobs=7
    )

    assert scans == ({"scan_id": "direct-1"}, {"scan_id": "direct-2"})
    assert calls == [
        (
            state.database_path,
            {"family_id": "TEST"},
            (1, 2),
            7,
        )
    ]
