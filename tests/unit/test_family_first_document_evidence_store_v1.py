from __future__ import annotations

import copy
import hashlib
import json
import pickle
import sqlite3
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from bctc_ai.evaluation import family_first_document_evidence_store_v1 as store_v1
from bctc_ai.evaluation import family_first_ocr_query_cache_v1 as cache_v1


def _ref(path: str, payload: bytes) -> dict:
    return {
        "path": path,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _packet(*, document_id: str = "document-1", evidence_root: str = "1" * 64) -> dict:
    material = {
        "assurance": "AUDITED",
        "bank_provenance": "ACB",
        "document_evidence_root_sha256": evidence_root,
        "document_id": document_id,
        "document_ordinal": 1,
        "line_count": 1,
        "page_count": 1,
        "period": "ANNUAL",
        "scope": "CONSOLIDATED",
        "source_pdf_ref": {"path": "vietstock_bctc/a.pdf", "sha256": "2" * 64, "size_bytes": 1},
        "year": 2025,
    }
    return {
        **material,
        "packet_id": "ffdesv1:document:" + store_v1.canonical_json_sha256_v1(material),
    }


def _selected_cache_projection(packet: dict) -> dict:
    material = {
        "document_id": packet["document_id"],
        "document_ordinal": packet["document_ordinal"],
        "joined_pages": [
            {
                "lines": [
                    {
                        "bbox": [1, 2, 20, 10],
                        "crop_ref": {
                            "path": "crop.png",
                            "sha256": "6" * 64,
                            "size_bytes": 1,
                        },
                        "line_ordinal": 0,
                        "numeric_recognition": {
                            "raw_prediction": "123",
                            "reader_score": 0.8,
                        },
                        "sample_id": "sample-1",
                        "vietocr_text": "Tiền mặt",
                    }
                ],
                "page_sequence": 1,
                "page_width": 100,
            }
        ],
        "selected_page_dimensions": [
            {
                "physical_page": 1,
                "pixel_height": 200,
                "pixel_width": 100,
                "render_sha256": "4" * 64,
                "render_size_bytes": 1,
            }
        ],
    }
    return {
        **material,
        "selection_id": "ffoqcv1:selection:" + store_v1.canonical_json_sha256_v1(material),
    }


def _legacy_selected_snapshot(state: SimpleNamespace, selected: dict) -> dict:
    selected_material = store_v1.canonical_clone_v1(selected)
    selected_identity = selected_material.pop("selection_id")
    material = {
        "document_packet": store_v1.canonical_clone_v1(state.manifest["documents"][0]),
        "joined_pages": store_v1.canonical_clone_v1(selected["joined_pages"]),
        "manifest_id": state.manifest["manifest_id"],
        "query_selection_id": selected_identity,
        "selected_page_dimensions": store_v1.canonical_clone_v1(
            selected["selected_page_dimensions"]
        ),
        "state": "AUTHENTICATED_IMMUTABLE_SQLITE_SELECTED_PAGE_EVIDENCE",
    }
    return store_v1.canonical_clone_v1(
        {
            **material,
            "snapshot_id": "ffdesv1:selected:" + store_v1.canonical_json_sha256_v1(material),
        }
    )


def _reverse_object_keys(value: object) -> object:
    if type(value) is dict:
        return {key: _reverse_object_keys(value[key]) for key in reversed(tuple(value))}
    if type(value) is list:
        return [_reverse_object_keys(item) for item in value]
    return value


def _manifest(root: Path, audit_commit: str) -> dict:
    database = (root / "data/local/store.sqlite3").read_bytes()
    inventory = (root / "docs/inventory.md").read_bytes()
    document_store = (root / "src/document_store.py").read_bytes()
    query_cache = (root / "src/query_cache.py").read_bytes()
    material = {
        "audit_commit": audit_commit,
        "authority": copy.deepcopy(store_v1._AUTHORITY),
        "claim_boundary": store_v1.CLAIM_BOUNDARY,
        "database_ref": _ref("data/local/store.sqlite3", database),
        "documents": [_packet()],
        "format_version": store_v1.FORMAT_VERSION,
        "implementation_refs": {
            "document_store": _ref("src/document_store.py", document_store),
            "query_cache_builder": _ref("src/query_cache.py", query_cache),
        },
        "input_indices": {
            "numeric_axis_sha256": "3" * 64,
            "numeric_receipt_id": "numeric-1",
            "semantic_index_id": "semantic-1",
        },
        "inventory_ref": _ref("docs/inventory.md", inventory),
        "metrics": {"document_count": 1, "line_count": 1, "page_count": 1},
        "state": "FULL_AUDIT_DOCUMENT_EVIDENCE_ROOTS_SEALED",
    }
    return {
        **material,
        "manifest_id": "ffdesv1:manifest:" + store_v1.canonical_json_sha256_v1(material),
    }


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", root, *args], check=True, capture_output=True)


def test_tracked_document_store_is_opaque_and_rejects_live_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for relative, payload in {
        ".gitignore": b"data/local/store.sqlite3\n",
        "data/local/store.sqlite3": b"immutable database",
        "docs/inventory.md": b"inventory",
        "src/document_store.py": b"store",
        "src/query_cache.py": b"cache",
    }.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "audit implementation")
    audit_commit = subprocess.run(
        ["git", "-C", tmp_path, "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    manifest = _manifest(tmp_path, audit_commit)
    registry = tmp_path / store_v1.REGISTRY_PATH
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_bytes(store_v1.canonical_json_bytes_v1(manifest) + b"\n")
    _git(tmp_path, "add", store_v1.REGISTRY_PATH.as_posix())
    _git(tmp_path, "commit", "-m", "register store")
    monkeypatch.setattr(
        store_v1.cache_v1,
        "project_family_first_ocr_query_cache_v1",
        lambda _path: {
            "document_count": 1,
            "line_count": 1,
            "page_count": 1,
            "sources": {
                "numeric_axis_sha256": "3" * 64,
                "numeric_receipt_id": "numeric-1",
                "semantic_index_id": "semantic-1",
            },
        },
    )

    capability = store_v1.authenticate_family_first_document_evidence_store_v1(tmp_path)
    assert (
        store_v1.project_authenticated_family_first_document_evidence_store_v1(capability)[
            "manifest_id"
        ]
        == manifest["manifest_id"]
    )
    assert (
        store_v1.read_authenticated_family_first_document_packet_v1(capability, document_ordinal=1)[
            "assurance"
        ]
        == "AUDITED"
    )
    with pytest.raises(TypeError):
        copy.copy(capability)
    with pytest.raises(TypeError):
        pickle.dumps(capability)
    with pytest.raises(TypeError):
        store_v1.AuthenticatedFamilyFirstDocumentEvidenceStoreV1()

    database = tmp_path / "data/local/store.sqlite3"
    database.write_bytes(b"tampered database")
    with pytest.raises(store_v1.FamilyFirstDocumentEvidenceStoreV1Error):
        store_v1.read_authenticated_family_first_document_packet_v1(capability, document_ordinal=1)


def _database(path: Path, *, transport: int, numeric_text: str) -> None:
    connection = sqlite3.connect(path)
    cache_v1._create_schema(connection)
    connection.executemany(
        "INSERT INTO metadata(key, value) VALUES (?, ?)",
        [
            ("cache_id", json.dumps("cache")),
            ("document_count", "1"),
            ("format_version", json.dumps(cache_v1.CACHE_FORMAT_VERSION)),
            ("line_count", "1"),
            ("page_count", "1"),
            ("schema_version", "1"),
            ("sources", "{}"),
            ("authority", "{}"),
        ],
    )
    connection.execute(
        "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            1,
            f"semantic-document-{transport}",
            "ACB",
            2025,
            "ANNUAL",
            "CONSOLIDATED",
            "vietstock_bctc/a.pdf",
            "2" * 64,
            1,
            1,
            1,
        ),
    )
    connection.execute(
        "INSERT INTO pages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (1, 1, 1, 100, 200, "4" * 64, 1, "page.json", "5" * 64, 1),
    )
    connection.execute(
        "INSERT INTO lines VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            transport,
            1,
            1,
            0,
            f"global-sample-{transport}",
            1,
            2,
            20,
            10,
            f"global-crop-{transport}.png",
            "6" * 64,
            1,
            "Tiền mặt",
            "Tiền mặt",
            "tien mat",
            0.9,
            20,
            32,
            numeric_text,
            0.8,
        ),
    )
    connection.commit()
    connection.close()


def test_document_evidence_root_ignores_global_transport_but_not_numeric_change(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first.sqlite3"
    shifted = tmp_path / "shifted.sqlite3"
    changed = tmp_path / "changed.sqlite3"
    _database(first, transport=1, numeric_text="123")
    _database(shifted, transport=999, numeric_text="123")
    _database(changed, transport=999, numeric_text="124")
    inventory = {
        "filings": [
            {
                "assurance": "AUDITED",
                "bank_provenance": "ACB",
                "content_ref": {
                    "path": "vietstock_bctc/a.pdf",
                    "sha256": "2" * 64,
                    "size_bytes": 1,
                },
                "period": "ANNUAL",
                "scope": "CONSOLIDATED",
                "year": 2025,
            }
        ]
    }

    first_packet = store_v1._document_packets(first, inventory)[0]
    shifted_packet = store_v1._document_packets(shifted, inventory)[0]
    changed_packet = store_v1._document_packets(changed, inventory)[0]
    assert (
        first_packet["document_evidence_root_sha256"]
        == shifted_packet["document_evidence_root_sha256"]
    )
    assert (
        first_packet["document_evidence_root_sha256"]
        != changed_packet["document_evidence_root_sha256"]
    )


def test_authenticated_document_snapshot_recomputes_one_packet_and_reads_joined_axis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = tmp_path / "store.sqlite3"
    _database(database, transport=7, numeric_text="1.460,873")
    inventory = {
        "filings": [
            {
                "assurance": "AUDITED",
                "bank_provenance": "ACB",
                "content_ref": {
                    "path": "vietstock_bctc/a.pdf",
                    "sha256": "2" * 64,
                    "size_bytes": 1,
                },
                "period": "ANNUAL",
                "scope": "CONSOLIDATED",
                "year": 2025,
            }
        ]
    }
    packet = store_v1._document_packets(database, inventory)[0]
    manifest = {
        "documents": [packet],
        "manifest_id": "ffdesv1:manifest:" + "9" * 64,
        "metrics": {"document_count": 1},
    }
    state = store_v1._StoreState(
        tmp_path,
        manifest,
        b"manifest",
        database,
        (0, 0, 0, 0),
    )
    monkeypatch.setattr(store_v1, "_live_store", lambda _capability: state)

    snapshot = store_v1.read_authenticated_family_first_document_evidence_snapshot_v1(
        object(), document_ordinal=1, selected_pages=(1,)
    )
    assert snapshot["document_packet"] == packet
    assert snapshot["joined_pages"][0]["lines"][0]["numeric_recognition"] == {
        "raw_prediction": "1.460,873",
        "reader_score": 0.8,
    }
    assert snapshot["joined_pages"][0]["page_width"] == 100
    assert snapshot["selected_page_dimensions"] == [
        {
            "physical_page": 1,
            "pixel_height": 200,
            "pixel_width": 100,
            "render_sha256": "4" * 64,
            "render_size_bytes": 1,
        }
    ]
    material = copy.deepcopy(snapshot)
    identity = material.pop("snapshot_id")
    assert identity == "ffdesv1:snapshot:" + store_v1.canonical_json_sha256_v1(material)

    connection = sqlite3.connect(database)
    connection.execute("UPDATE lines SET numeric_text = '1.460.874'")
    connection.commit()
    connection.close()
    with pytest.raises(
        store_v1.FamilyFirstDocumentEvidenceStoreV1Error,
        match="authenticated packet root",
    ):
        store_v1.read_authenticated_family_first_document_evidence_snapshot_v1(
            object(), document_ordinal=1, selected_pages=(1,)
        )


@pytest.mark.parametrize("reverse_provider_keys", [False, True])
def test_selected_page_hydration_matches_legacy_bytes_and_detaches_mutations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reverse_provider_keys: bool,
) -> None:
    packet = _packet()
    state = SimpleNamespace(
        database_path=tmp_path / "evidence.sqlite3",
        manifest={
            "documents": [packet],
            "manifest_id": "ffdesv1:manifest:" + "9" * 64,
            "metrics": {"document_count": 1},
        },
    )
    selected = _selected_cache_projection(packet)
    if reverse_provider_keys:
        selected = _reverse_object_keys(selected)
        assert type(selected) is dict
    selected_before = copy.deepcopy(selected)
    expected = _legacy_selected_snapshot(state, selected)
    monkeypatch.setattr(store_v1, "_live_store", lambda _capability: state)
    monkeypatch.setattr(
        store_v1.cache_v1,
        "read_cached_selected_joined_pages_v1",
        lambda _database, _ordinal, *, selected_pages: selected,
    )

    snapshot = store_v1.read_authenticated_family_first_document_selected_pages_v1(
        object(), document_ordinal=1, selected_pages=(1,)
    )

    assert store_v1.canonical_json_bytes_v1(snapshot) == store_v1.canonical_json_bytes_v1(expected)
    assert store_v1.same_typed_json_v1(selected, selected_before)

    selected["joined_pages"][0]["lines"][0]["bbox"][0] = 999
    state.manifest["documents"][0]["source_pdf_ref"]["path"] = "provider-mutated.pdf"
    assert snapshot["joined_pages"][0]["lines"][0]["bbox"][0] == 1
    assert snapshot["document_packet"]["source_pdf_ref"]["path"] == "vietstock_bctc/a.pdf"

    snapshot["joined_pages"][0]["lines"][0]["bbox"][1] = 888
    snapshot["document_packet"]["source_pdf_ref"]["path"] = "caller-mutated.pdf"
    assert selected["joined_pages"][0]["lines"][0]["bbox"][1] == 2
    assert state.manifest["documents"][0]["source_pdf_ref"]["path"] == "provider-mutated.pdf"


@pytest.mark.parametrize("tamper", ["boolean_document_ordinal", "stale_line_content"])
def test_selected_page_hydration_rejects_exact_type_and_content_tamper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tamper: str,
) -> None:
    packet = _packet()
    state = SimpleNamespace(
        database_path=tmp_path / "evidence.sqlite3",
        manifest={
            "documents": [packet],
            "manifest_id": "ffdesv1:manifest:" + "9" * 64,
            "metrics": {"document_count": 1},
        },
    )
    selected = _selected_cache_projection(packet)
    if tamper == "boolean_document_ordinal":
        selected["document_ordinal"] = True
        material = copy.deepcopy(selected)
        material.pop("selection_id")
        selected["selection_id"] = "ffoqcv1:selection:" + store_v1.canonical_json_sha256_v1(
            material
        )
    else:
        selected["joined_pages"][0]["lines"][0]["vietocr_text"] = "tampered"
    monkeypatch.setattr(
        store_v1.cache_v1,
        "read_cached_selected_joined_pages_v1",
        lambda _database, _ordinal, *, selected_pages: selected,
    )

    with pytest.raises(
        store_v1.FamilyFirstDocumentEvidenceStoreV1Error,
        match="differs from its authenticated document packet",
    ):
        store_v1._selected_pages_snapshot_from_state(state, document_ordinal=1, selected_pages=(1,))


def test_selected_page_hydration_has_one_final_clone_and_two_identity_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    packet = _packet()
    state = SimpleNamespace(
        database_path=tmp_path / "evidence.sqlite3",
        manifest={
            "documents": [packet],
            "manifest_id": "ffdesv1:manifest:" + "9" * 64,
            "metrics": {"document_count": 1},
        },
    )
    selected = _selected_cache_projection(packet)
    monkeypatch.setattr(
        store_v1.cache_v1,
        "read_cached_selected_joined_pages_v1",
        lambda _database, _ordinal, *, selected_pages: selected,
    )
    original_clone = store_v1.canonical_clone_v1
    original_hash = store_v1.canonical_json_sha256_v1
    clone_calls: list[set[str]] = []
    hash_calls: list[set[str]] = []

    def counted_clone(value: dict) -> dict:
        clone_calls.append(set(value))
        return original_clone(value)

    def counted_hash(value: dict) -> str:
        hash_calls.append(set(value))
        return original_hash(value)

    monkeypatch.setattr(store_v1, "canonical_clone_v1", counted_clone)
    monkeypatch.setattr(store_v1, "canonical_json_sha256_v1", counted_hash)

    snapshot = store_v1._selected_pages_snapshot_from_state(
        state, document_ordinal=1, selected_pages=(1,)
    )

    assert snapshot["snapshot_id"].startswith("ffdesv1:selected:")
    assert len(clone_calls) == 1
    assert clone_calls[0] == set(snapshot)
    assert len(hash_calls) == 2
    assert "selection_id" not in hash_calls[0]
    assert "snapshot_id" not in hash_calls[1]


def test_authenticated_topology_accessor_reuses_exact_engine_keyed_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = SimpleNamespace(
        database_path=tmp_path / "evidence.sqlite3",
        manifest={"metrics": {"document_count": 2}},
        root=tmp_path,
    )
    scans = ({"scan_id": "scan-1"}, {"scan_id": "scan-2"})
    calls = []
    monkeypatch.setattr(store_v1, "_live_store", lambda _cap: state)
    monkeypatch.setattr(
        store_v1.cache_v1,
        "refresh_cached_topology_results_v1",
        lambda database, topology, family, *, jobs: calls.append(
            (database, topology, family, jobs)
        ),
    )
    monkeypatch.setattr(
        store_v1.cache_v1,
        "read_cached_topology_results_v1",
        lambda _database, _topology, _family: scans,
    )

    result = store_v1.read_authenticated_family_first_topology_scans_v1(
        object(), {"family_id": "FAMILY"}, jobs=7
    )

    assert result == scans
    assert calls == [
        (
            state.database_path,
            tmp_path / store_v1.cache_v1.DEFAULT_TOPOLOGY_DATABASE_PATH,
            {"family_id": "FAMILY"},
            7,
        )
    ]


def test_authenticated_selected_page_batch_uses_one_outer_live_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _packet(document_id="document-1")
    second_material = {
        **{key: copy.deepcopy(value) for key, value in first.items() if key != "packet_id"},
        "document_id": "document-2",
        "document_ordinal": 2,
    }
    second = {
        **second_material,
        "packet_id": "ffdesv1:document:" + store_v1.canonical_json_sha256_v1(second_material),
    }
    state = SimpleNamespace(
        database_path=tmp_path / "evidence.sqlite3",
        manifest={
            "documents": [first, second],
            "manifest_id": "ffdesv1:manifest:" + "9" * 64,
            "metrics": {"document_count": 2},
        },
    )
    live_calls = []
    cache_calls = []

    def live(_capability: object) -> SimpleNamespace:
        live_calls.append(True)
        return state

    def selected(
        _database: Path, document_ordinal: int, *, selected_pages: tuple[int, ...]
    ) -> dict:
        cache_calls.append((document_ordinal, selected_pages))
        packet = state.manifest["documents"][document_ordinal - 1]
        material = {
            "document_id": packet["document_id"],
            "document_ordinal": document_ordinal,
            "joined_pages": [
                {
                    "lines": [
                        {
                            "bbox": [1, 2, 20, 10],
                            "crop_ref": {
                                "path": "crop.png",
                                "sha256": "6" * 64,
                                "size_bytes": 1,
                            },
                            "line_ordinal": 0,
                            "numeric_recognition": {
                                "raw_prediction": "123",
                                "reader_score": 0.8,
                            },
                            "sample_id": f"sample-{document_ordinal}",
                            "vietocr_text": "Tiền mặt",
                        }
                    ],
                    "page_sequence": 1,
                    "page_width": 100,
                }
            ],
            "selected_page_dimensions": [
                {
                    "physical_page": 1,
                    "pixel_height": 200,
                    "pixel_width": 100,
                    "render_sha256": "4" * 64,
                    "render_size_bytes": 1,
                }
            ],
        }
        return {
            **material,
            "selection_id": "ffoqcv1:selection:" + store_v1.canonical_json_sha256_v1(material),
        }

    monkeypatch.setattr(store_v1, "_live_store", live)
    monkeypatch.setattr(
        store_v1.cache_v1,
        "read_cached_selected_joined_pages_v1",
        selected,
    )

    individual = tuple(
        store_v1.read_authenticated_family_first_document_selected_pages_v1(
            object(),
            document_ordinal=document_ordinal,
            selected_pages=(1,),
        )
        for document_ordinal in (1, 2)
    )
    snapshots = store_v1.read_authenticated_family_first_documents_selected_pages_v1(
        object(),
        document_page_selections=((1, (1,)), (2, (1,))),
    )

    assert store_v1.same_typed_json_v1(snapshots, individual)
    assert len(snapshots) == 2
    assert [item["document_packet"]["document_ordinal"] for item in snapshots] == [1, 2]
    assert cache_calls == [(1, (1,)), (2, (1,)), (1, (1,)), (2, (1,))]
    # Two guards per individual read, versus two guards for the whole batch.
    assert len(live_calls) == 6
    for snapshot in snapshots:
        material = copy.deepcopy(snapshot)
        identity = material.pop("snapshot_id")
        assert identity == "ffdesv1:selected:" + store_v1.canonical_json_sha256_v1(material)


@pytest.mark.parametrize(
    "selection",
    [
        (),
        ((2, (1,)), (1, (1,))),
        ((1, (1,)), (1, (1,))),
        ((True, (1,)),),
        ((1, (True,)),),
    ],
)
def test_authenticated_selected_page_batch_rejects_ambiguous_axes(
    selection: tuple[tuple[int, tuple[int, ...]], ...],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = SimpleNamespace(
        database_path=Path("unused.sqlite3"),
        manifest={"documents": [_packet()], "metrics": {"document_count": 1}},
    )
    monkeypatch.setattr(store_v1, "_live_store", lambda _capability: state)

    with pytest.raises(store_v1.FamilyFirstDocumentEvidenceStoreV1Error):
        store_v1.read_authenticated_family_first_documents_selected_pages_v1(
            object(),
            document_page_selections=selection,
        )


def test_authenticated_selected_page_batch_rejects_mid_read_store_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    packet = _packet()
    first = SimpleNamespace(
        database_path=tmp_path / "first.sqlite3",
        manifest={
            "documents": [packet],
            "manifest_id": "ffdesv1:manifest:" + "8" * 64,
            "metrics": {"document_count": 1},
        },
    )
    second = SimpleNamespace(
        database_path=tmp_path / "second.sqlite3",
        manifest={
            "documents": [packet],
            "manifest_id": "ffdesv1:manifest:" + "9" * 64,
            "metrics": {"document_count": 1},
        },
    )
    states = iter((first, second))
    monkeypatch.setattr(store_v1, "_live_store", lambda _capability: next(states))

    def selected(_database: Path, _ordinal: int, *, selected_pages: tuple[int, ...]) -> dict:
        material = {
            "document_id": packet["document_id"],
            "document_ordinal": 1,
            "joined_pages": [{"lines": [], "page_sequence": selected_pages[0], "page_width": 100}],
            "selected_page_dimensions": [
                {
                    "physical_page": selected_pages[0],
                    "pixel_height": 200,
                    "pixel_width": 100,
                    "render_sha256": "4" * 64,
                    "render_size_bytes": 1,
                }
            ],
        }
        return {
            **material,
            "selection_id": "ffoqcv1:selection:" + store_v1.canonical_json_sha256_v1(material),
        }

    monkeypatch.setattr(
        store_v1.cache_v1,
        "read_cached_selected_joined_pages_v1",
        selected,
    )

    with pytest.raises(
        store_v1.FamilyFirstDocumentEvidenceStoreV1Error,
        match="changed during batch selected-page hydration",
    ):
        store_v1.read_authenticated_family_first_documents_selected_pages_v1(
            object(),
            document_page_selections=((1, (1,)),),
        )
