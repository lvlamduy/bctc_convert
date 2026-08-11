from __future__ import annotations

import ast
import inspect
from copy import deepcopy
from pathlib import Path
from statistics import fmean

import pytest
from test_source_structure_evidence_projection_v1 import (
    _refresh_ocr_axis_accounting,
    _refresh_result_ref,
)
from test_source_structure_evidence_projection_v2 import (
    _synthetic_native_pair,
    _synthetic_ocr_pair,
)
from test_source_structure_page_geometry_proposals_v1 import _line

from bctc_ai.document_phase.statement_locator import (
    PageDecision,
    StatementPageType,
    StatementScope,
)
from bctc_ai.document_phase.statement_locator_v2 import load_statement_locator_v2_config
from bctc_ai.source_structure import document_statement_hypotheses_v1 as hypotheses_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.source_structure.document_statement_hypotheses_v1 import (
    DocumentStatementHypothesesV1Error,
    build_document_statement_block_hypotheses_v1,
    validate_document_statement_block_hypotheses_v1,
)
from bctc_ai.source_structure.evidence_projection_v2 import project_authenticated_page_v2

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "src/bctc_ai/source_structure/document_statement_hypotheses_v1.py"


def _policy() -> dict:
    return load_statement_locator_v2_config(
        PROJECT_ROOT / "config/document_phase/statement-locator-v2.yaml"
    )


def _bind_ocr_page(record: dict, result: dict, *, physical_page: int) -> None:
    record["request_ordinal"] = physical_page
    record["physical_page"] = physical_page
    result["physical_page"] = physical_page
    request = deepcopy(record["request"])
    request["physical_page"] = physical_page
    record["request"] = deepcopy(request)
    result["request"] = deepcopy(request)
    request_sha = canonical_json_sha256_v1(request)
    record["request_sha256"] = request_sha
    result["request_sha256"] = request_sha


def _ocr_projection(physical_page: int, *texts: str) -> dict:
    record, result = _synthetic_ocr_pair()
    _bind_ocr_page(record, result, physical_page=physical_page)
    result["lines"] = [
        _line(40 + index * 70, [(100, 1_000, text)]) for index, text in enumerate(texts)
    ]
    _refresh_ocr_axis_accounting(record, result)
    result["metrics"]["mean_line_score"] = (
        fmean(line["score"] for line in result["lines"]) if result["lines"] else None
    )
    _refresh_result_ref(record, result)
    record.pop("line_count", None)
    line_count = len(result["lines"])
    record["line_axis_count"] = line_count
    record["nonempty_line_axis_count"] = line_count
    record["exact_empty_line_axis_count"] = 0
    record["accepted_line_count"] = line_count
    record["upstream_v2_adoption"]["source_refs"]["result_ref"] = deepcopy(record["result_ref"])
    return project_authenticated_page_v2(page_record=record, page_result=result)


def _ocr_terminal_projection(physical_page: int) -> dict:
    record, result = _synthetic_ocr_pair()
    _bind_ocr_page(record, result, physical_page=physical_page)
    result.pop("word_box_normalization_ledger")
    result.update(
        format_version="BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V3",
        status="UNRESOLVED_OCR_WORD_BOX_GEOMETRY",
        claim_boundary="SOURCE_VISIBLE_PAGE_RAW_OCR_EVIDENCE_WITH_UNRESOLVED_GEOMETRY",
        lines=[],
        words=[],
        metrics={"line_count": 0, "word_token_count": 0},
        ocr_fallback_used=False,
        normalization_failure={
            "format_version": "BANK_CORPUS_WAVE_1_PPOCRV6_NORMALIZATION_FAILURE_V1",
            "status": "UNRESOLVED_OCR_WORD_BOX_GEOMETRY",
            "reason": "BOUNDED_WORD_BOX_NORMALIZATION_INVARIANT_FAILED",
            "policy_sha256": "3" * 64,
            "control_identity_sha256": "4" * 64,
            "normalization_producer_implementation_ledger_sha256": "5" * 64,
            "pixel_dimensions": result["coordinate_authority"]["pixel_dimensions"],
            "raw_payload_sha256": "6" * 64,
        },
    )
    record.update(
        status=result["status"],
        upstream_status=result["status"],
        upstream_unresolved=True,
        line_axis_count=0,
        nonempty_line_axis_count=0,
        exact_empty_line_axis_count=0,
        accepted_line_count=0,
        word_token_count=0,
        word_box_correction_count=0,
        word_box_corrected_edge_count=0,
        unresolved=True,
    )
    adoption = record["upstream_v2_adoption"]
    adoption["source_status"] = result["status"]
    adoption["source_unresolved"] = True
    _refresh_result_ref(record, result)
    adoption["source_refs"]["result_ref"] = deepcopy(record["result_ref"])
    return project_authenticated_page_v2(page_record=record, page_result=result)


def _native_projection(
    monkeypatch: pytest.MonkeyPatch,
    *,
    terminal: bool,
) -> dict:
    record, result = _synthetic_native_pair(
        monkeypatch,
        contiguity_terminal=terminal,
    )
    return project_authenticated_page_v2(page_record=record, page_result=result)


def _complete_block(*, first_page: int = 1, repeated: bool = False) -> list[dict]:
    pages = [
        _ocr_projection(first_page, "Mẫu B02a/TCTD-HN", "100"),
    ]
    next_page = first_page + 1
    if repeated:
        pages.append(_ocr_projection(next_page, "Mẫu B02b/TCTD-HN", "101"))
        next_page += 1
    pages.extend(
        [
            _ocr_projection(next_page, "Mẫu B03a/TCTD-HN", "200"),
            _ocr_projection(next_page + 1, "Mẫu B04a/TCTD-HN", "300"),
            _ocr_projection(next_page + 2, "Mẫu B05a/TCTD-HN"),
        ]
    )
    return pages


def _structural_signature(value: dict) -> tuple:
    return (
        value["status"],
        tuple(
            (
                item["input_ordinal"],
                item["family_hypothesis"],
                item["diagnostic_score"],
                tuple(item["evidence_codes"]),
                item["continuation_marker_hypothesis"],
            )
            for item in value["page_hypotheses"]
        ),
        tuple(
            (
                item["rank"],
                item["start_input_ordinal"],
                item["end_input_ordinal"],
                tuple(item["family_sequence_hypothesis"]),
                item["diagnostic_score"],
                tuple(sorted(item["diagnostic_score_components"].items())),
            )
            for item in value["block_hypotheses"]
        ),
        tuple(item["primary_disposition"] for item in value["page_dispositions"]),
    )


def test_complete_four_family_sequence_is_candidate_only_and_no_drop() -> None:
    pages = _complete_block()
    policy = _policy()

    artifact = build_document_statement_block_hypotheses_v1(
        pages,
        locator_policy=policy,
    )

    assert (
        validate_document_statement_block_hypotheses_v1(
            artifact,
            pages,
            locator_policy=policy,
        )
        == artifact
    )
    assert artifact["status"] == "CANDIDATES_EMITTED"
    assert len(artifact["block_hypotheses"]) == 1
    block = artifact["block_hypotheses"][0]
    assert block["family_sequence_hypothesis"] == ["CDKT", "KQKD", "LCTT"]
    assert (
        block["tm_boundary_hypothesis_id"] == artifact["page_hypotheses"][3]["page_hypothesis_id"]
    )
    assert len(artifact["page_hypotheses"]) == len(pages)
    assert len(artifact["page_dispositions"]) == len(pages)
    assert [item["source_local_page_id"] for item in artifact["page_dispositions"]] == [
        page["source_local_page_id"] for page in pages
    ]
    assert {item["primary_disposition"] for item in artifact["page_dispositions"]} == {
        "SUPPORTS_STATEMENT_BLOCK_HYPOTHESIS"
    }
    assert artifact["safety"]["candidate_hypotheses_only"] is True
    assert all(
        value is False
        for key, value in artifact["safety"].items()
        if key != "candidate_hypotheses_only"
    )
    serialized = canonical_json_bytes_v1(artifact)
    for text in (
        b"M\xe1\xba\xabu B02",
        b"M\xe1\xba\xabu B03",
        b"M\xe1\xba\xabu B04",
        b"M\xe1\xba\xabu B05",
    ):
        assert text not in serialized


def test_repeated_family_pages_remain_one_ranked_hypothesis() -> None:
    pages = _complete_block(repeated=True)

    artifact = build_document_statement_block_hypotheses_v1(
        pages,
        locator_policy=_policy(),
    )

    block = artifact["block_hypotheses"][0]
    assert block["family_sequence_hypothesis"] == ["CDKT", "CDKT", "KQKD", "LCTT"]
    assert len(block["member_page_hypothesis_ids"]) == 4
    assert artifact["metrics"]["family_hypothesis_counts"]["CDKT"] == 2


def test_off_balance_and_continuation_signals_remain_nontruth_hypotheses() -> None:
    pages = [
        _ocr_projection(
            1,
            "Mẫu B02a/TCTD-HN",
            "Các chỉ tiêu ngoài báo cáo tình hình tài chính",
            "Bảo lãnh vay vốn",
            "Cam kết giao dịch hối đoái",
        ),
        _ocr_projection(2, "Mẫu B03a/TCTD-HN (tiếp theo)", "200"),
    ]

    artifact = build_document_statement_block_hypotheses_v1(
        pages,
        locator_policy=_policy(),
    )

    first, second = artifact["page_hypotheses"]
    assert first["family_hypothesis"] == "CDKT"
    assert "OFF_BALANCE_SIGNAL_HYPOTHESIS" in first["evidence_codes"]
    assert second["continuation_marker_hypothesis"] is True
    assert "CONTINUATION_MARKER_SIGNAL_HYPOTHESIS" in second["evidence_codes"]
    assert artifact["block_hypotheses"] == []
    assert {item["primary_disposition"] for item in artifact["page_dispositions"]} == {
        "RETAINED_UNRESOLVED"
    }
    assert artifact["safety"]["scope_truth_claimed"] is False


@pytest.mark.parametrize(
    "pages",
    [
        [_ocr_projection(1, "Mục lục")],
        [_ocr_projection(1, "Báo cáo kiểm toán độc lập")],
        [_ocr_projection(1, "Phạm vi công việc và thông tin tổng quát")],
        [
            _ocr_projection(1, "Mẫu B02a/TCTD-HN", "100"),
            _ocr_projection(2, "Mẫu B03a/TCTD-HN", "200"),
            _ocr_projection(3, "Mẫu B04a/TCTD-HN", "300"),
        ],
        [
            _ocr_projection(1, "Mẫu B02a/TCTD-HN", "100"),
            _ocr_projection(2, "Mẫu B04a/TCTD-HN", "300"),
            _ocr_projection(3, "Mẫu B03a/TCTD-HN", "200"),
            _ocr_projection(4, "Mẫu B05a/TCTD-HN"),
        ],
    ],
    ids=("contents", "audit", "narrative", "missing-boundary", "reordered"),
)
def test_noncomplete_sequences_retain_every_page_hypothesis(pages: list[dict]) -> None:
    artifact = build_document_statement_block_hypotheses_v1(
        pages,
        locator_policy=_policy(),
    )

    assert artifact["status"] == "UNRESOLVED_NO_COMPLETE_ORDERED_HYPOTHESIS"
    assert artifact["block_hypotheses"] == []
    assert len(artifact["page_hypotheses"]) == len(pages)
    assert [item["input_ordinal"] for item in artifact["page_hypotheses"]] == list(
        range(1, len(pages) + 1)
    )
    assert {item["primary_disposition"] for item in artifact["page_dispositions"]} == {
        "RETAINED_UNRESOLVED"
    }


def test_equal_diagnostic_candidates_are_both_retained_without_acceptance() -> None:
    pages = [*_complete_block(first_page=1), *_complete_block(first_page=5)]

    artifact = build_document_statement_block_hypotheses_v1(
        pages,
        locator_policy=_policy(),
    )

    assert [item["rank"] for item in artifact["block_hypotheses"]] == [1, 2]
    assert [item["diagnostic_score"] for item in artifact["block_hypotheses"]] == [12.0, 12.0]
    assert [item["start_input_ordinal"] for item in artifact["block_hypotheses"]] == [1, 5]
    assert len({item["block_hypothesis_id"] for item in artifact["block_hypotheses"]}) == 2
    assert artifact["safety"]["statement_block_accepted"] is False
    assert artifact["safety"]["statement_family_accepted"] is False


def test_ocr_and_native_terminal_pages_are_explicit_empty_barriers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for projection in (
        _ocr_terminal_projection(1),
        _native_projection(monkeypatch, terminal=True),
    ):
        artifact = build_document_statement_block_hypotheses_v1(
            [projection],
            locator_policy=_policy(),
        )
        hypothesis = artifact["page_hypotheses"][0]
        assert hypothesis["family_hypothesis"] == "UPSTREAM_TERMINAL"
        assert hypothesis["diagnostic_score"] == 0.0
        assert hypothesis["evidence_codes"] == ["UPSTREAM_TERMINAL_BARRIER"]
        assert hypothesis["continuation_marker_hypothesis"] is False
        assert artifact["block_hypotheses"] == []
        assert artifact["page_dispositions"][0]["primary_disposition"] == (
            "UPSTREAM_TERMINAL_UNRESOLVED"
        )


def test_terminal_inside_a_family_sequence_eliminates_the_block_hypothesis() -> None:
    pages = [
        _ocr_projection(1, "Mẫu B02a/TCTD-HN", "100"),
        _ocr_terminal_projection(2),
        _ocr_projection(3, "Mẫu B03a/TCTD-HN", "200"),
        _ocr_projection(4, "Mẫu B04a/TCTD-HN", "300"),
        _ocr_projection(5, "Mẫu B05a/TCTD-HN"),
    ]

    artifact = build_document_statement_block_hypotheses_v1(
        pages,
        locator_policy=_policy(),
    )

    assert artifact["block_hypotheses"] == []
    assert artifact["page_hypotheses"][1]["family_hypothesis"] == "UPSTREAM_TERMINAL"
    assert artifact["page_dispositions"][1] == {
        "input_ordinal": 2,
        "source_local_page_id": pages[1]["source_local_page_id"],
        "page_hypothesis_id": artifact["page_hypotheses"][1]["page_hypothesis_id"],
        "primary_disposition": "UPSTREAM_TERMINAL_UNRESOLVED",
        "block_hypothesis_ids": [],
    }


def test_terminal_before_a_later_complete_block_is_never_inferred_into_it() -> None:
    pages = [_ocr_terminal_projection(1), *_complete_block(first_page=2)]

    artifact = build_document_statement_block_hypotheses_v1(
        pages,
        locator_policy=_policy(),
    )

    assert len(artifact["block_hypotheses"]) == 1
    block = artifact["block_hypotheses"][0]
    terminal_id = artifact["page_hypotheses"][0]["page_hypothesis_id"]
    assert block["start_input_ordinal"] == 2
    assert terminal_id not in block["member_page_hypothesis_ids"]
    assert terminal_id != block["tm_boundary_hypothesis_id"]
    assert artifact["page_dispositions"][0]["primary_disposition"] == (
        "UPSTREAM_TERMINAL_UNRESOLVED"
    )
    assert artifact["page_dispositions"][0]["block_hypothesis_ids"] == []


def test_ocr_and_native_adapters_preserve_primary_line_order_and_dimensions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ocr = _ocr_projection(101, "first visible line", "second visible line")
    native = _native_projection(monkeypatch, terminal=False)
    observed = []

    def classify(page, _policy):
        observed.append(page)
        return PageDecision(
            page=page.page,
            page_type=StatementPageType.OTHER,
            scope=StatementScope.NOT_APPLICABLE,
            mapping_eligible=False,
            confidence=0.0,
            form_hits=(),
            title_scores={family: 0.0 for family in ("CDKT", "KQKD", "LCTT", "TM")},
            title_discriminator_scores={family: 0.0 for family in ("CDKT", "KQKD", "LCTT", "TM")},
            evidence=(),
            off_balance_item_hits=(),
            numeric_line_fraction=0.0,
            is_continuation=False,
        )

    monkeypatch.setattr(hypotheses_v1, "classify_statement_page_v2", classify)
    build_document_statement_block_hypotheses_v1([ocr], locator_policy=_policy())
    build_document_statement_block_hypotheses_v1([native], locator_policy=_policy())

    ocr_page, native_page = observed[0], observed[2]
    assert ocr_page.page == native_page.page == 1
    assert [line.text for line in ocr_page.lines] == ["first visible line", "second visible line"]
    assert [line.text for line in native_page.lines] == [
        atom["raw_text"]
        for atom in native["neutral_page_v1"]["atoms"]
        if atom["kind"] == "LINE" and atom["authority"] == "AUTHENTICATED_PRIMARY"
    ]
    assert (ocr_page.width, ocr_page.height) == tuple(
        ocr["coordinate_authority"]["unrotated_dimensions_mpt"]
    )
    native_bounds = native["coordinate_authority"]["canonical_cropbox_bounds_mpt"]
    assert (native_page.width, native_page.height) == (
        native_bounds[2] - native_bounds[0],
        native_bounds[3] - native_bounds[1],
    )
    assert all(line.score == 0.0 for line in native_page.lines)


def test_authenticated_page_axis_is_required_but_constant_shift_does_not_route() -> None:
    first = _complete_block(first_page=1)
    shifted = _complete_block(first_page=101)
    first_artifact = build_document_statement_block_hypotheses_v1(
        first,
        locator_policy=_policy(),
    )
    shifted_artifact = build_document_statement_block_hypotheses_v1(
        shifted,
        locator_policy=_policy(),
    )

    assert _structural_signature(first_artifact) == _structural_signature(shifted_artifact)
    shuffled = [first[1], first[0], *first[2:]]
    with pytest.raises(DocumentStatementHypothesesV1Error, match="contiguous"):
        build_document_statement_block_hypotheses_v1(shuffled, locator_policy=_policy())
    missing = [first[0], first[2], first[3]]
    with pytest.raises(DocumentStatementHypothesesV1Error, match="contiguous"):
        build_document_statement_block_hypotheses_v1(missing, locator_policy=_policy())


def test_source_identity_uniqueness_and_tamper_are_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = _ocr_projection(1, "Mẫu B02a/TCTD-HN", "100")
    with pytest.raises(DocumentStatementHypothesesV1Error, match="unique"):
        build_document_statement_block_hypotheses_v1([page, page], locator_policy=_policy())
    native = _native_projection(monkeypatch, terminal=False)
    with pytest.raises(DocumentStatementHypothesesV1Error, match="source identity"):
        build_document_statement_block_hypotheses_v1([page, native], locator_policy=_policy())

    pages = _complete_block()
    artifact = build_document_statement_block_hypotheses_v1(pages, locator_policy=_policy())
    tampered = deepcopy(artifact)
    tampered["page_hypotheses"][0]["diagnostic_score"] = 0.25
    with pytest.raises(DocumentStatementHypothesesV1Error, match="drifted"):
        validate_document_statement_block_hypotheses_v1(
            tampered,
            pages,
            locator_policy=_policy(),
        )
    detached = deepcopy(pages)
    detached[0]["source_local_page_id"] = "ssv2:page:" + "0" * 64
    with pytest.raises(DocumentStatementHypothesesV1Error, match="authority"):
        build_document_statement_block_hypotheses_v1(detached, locator_policy=_policy())


def test_policy_receipt_binds_only_the_classifier_and_block_scorer_contract() -> None:
    pages = _complete_block()
    policy = _policy()
    artifact = build_document_statement_block_hypotheses_v1(pages, locator_policy=policy)
    irrelevant = deepcopy(policy)
    irrelevant["minimum_candidate_margin"] = 999.0
    irrelevant["cash_flow_method"]["schema_reason"] = "unconsumed external branch reason"
    repeated = build_document_statement_block_hypotheses_v1(
        pages,
        locator_policy=irrelevant,
    )

    assert artifact == repeated
    receipt = artifact["locator_policy_receipt"]
    assert "minimum_candidate_margin" not in receipt["used_keys"]
    assert "cash_flow_method" not in receipt["used_keys"]
    assert "policy" in receipt["used_keys"]
    drifted_identity = deepcopy(policy)
    drifted_identity["v2"]["forbidden_inputs"] = drifted_identity["v2"]["forbidden_inputs"][:-1]
    with pytest.raises(DocumentStatementHypothesesV1Error, match="classifier contract"):
        build_document_statement_block_hypotheses_v1(
            pages,
            locator_policy=drifted_identity,
        )

    for field, replacement in (
        ("title_anchors", {**policy["title_anchors"], "CDKT": ["MBB"]}),
        ("title_min_similarity", 0.01),
    ):
        drifted_used_policy = deepcopy(policy)
        drifted_used_policy[field] = replacement
        with pytest.raises(DocumentStatementHypothesesV1Error, match="used by statement"):
            build_document_statement_block_hypotheses_v1(
                pages,
                locator_policy=drifted_used_policy,
            )


def test_module_import_and_public_api_boundary_is_closed() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert not any(isinstance(node, ast.Import) for node in ast.walk(tree))
    imported_names = {
        (node.module or "", alias.name, alias.asname)
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert imported_names == {
        ("__future__", "annotations", None),
        ("collections", "Counter", None),
        ("collections.abc", "Mapping", None),
        ("collections.abc", "Sequence", None),
        ("itertools", "pairwise", None),
        ("math", "isfinite", None),
        ("typing", "Any", None),
        ("bctc_ai.document_phase.statement_locator", "OCRLine", None),
        ("bctc_ai.document_phase.statement_locator", "OCRPage", None),
        ("bctc_ai.document_phase.statement_locator", "PageDecision", None),
        ("bctc_ai.document_phase.statement_locator", "StatementLocatorError", None),
        ("bctc_ai.document_phase.statement_locator", "StatementPageType", None),
        ("bctc_ai.document_phase.statement_locator", "StatementScope", None),
        ("bctc_ai.document_phase.statement_locator", "_candidate_blocks", None),
        (
            "bctc_ai.document_phase.statement_locator_v2",
            "classify_statement_page_v2",
            None,
        ),
        ("bctc_ai.source_structure.contracts_v1", "canonical_clone_v1", None),
        (
            "bctc_ai.source_structure.contracts_v1",
            "canonical_json_sha256_v1",
            None,
        ),
        ("bctc_ai.source_structure.contracts_v1", "same_typed_json_v1", None),
        (
            "bctc_ai.source_structure.contracts_v2",
            "validate_source_evidence_projection_v2",
            None,
        ),
    }
    imports = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert imports <= {
        "__future__",
        "collections",
        "collections.abc",
        "itertools",
        "math",
        "typing",
        "bctc_ai.document_phase.statement_locator",
        "bctc_ai.document_phase.statement_locator_v2",
        "bctc_ai.source_structure.contracts_v1",
        "bctc_ai.source_structure.contracts_v2",
    }
    forbidden_import_fragments = (
        "multisignal",
        "native_tm_regions",
        "page_reader",
        "mapping",
        "registry",
        "source_structure.page_prestructural_graph",
    )
    assert not any(
        fragment in module for module in imports for fragment in forbidden_import_fragments
    )
    call_names = [
        (
            node.func.id
            if isinstance(node.func, ast.Name)
            else node.func.attr
            if isinstance(node.func, ast.Attribute)
            else ""
        )
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    ]
    assert set(call_names).isdisjoint(
        {
            "locate_statement_pages",
            "locate_statement_pages_v2",
            "detect_cash_flow_method",
            "discover_statement_pages_v4",
            "read_causal_native_text_page",
            "open",
            "read_text",
            "read_bytes",
            "glob",
            "rglob",
            "resolve",
            "is_file",
            "exists",
            "iterdir",
        }
    )
    assert call_names.count("classify_statement_page_v2") == 1
    assert call_names.count("_candidate_blocks") == 1
    runtime_keys = {
        node.slice.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Subscript)
        and isinstance(node.slice, ast.Constant)
        and isinstance(node.slice.value, str)
    }
    get_keys = {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    }
    assert (runtime_keys | get_keys).isdisjoint(
        {
            "bank",
            "bank_identity",
            "filename",
            "filename_identity",
            "path",
            "note_number",
            "page_number_rules",
            "numeric_values_for_page_type",
            "role_a",
            "schema",
            "history",
            "historical_values",
            "registry",
            "report_norm_id_numeric_order",
            "document_id",
            "request_ordinal",
            "page_result",
            "pdf_path",
            "mapping",
            "cash_flow_method",
            "minimum_candidate_margin",
            "ordered_statement_types",
        }
    )
    forbidden_runtime_name_fragments = (
        "bank",
        "filename",
        "role_a",
        "schema",
        "history",
        "registry",
        "pdf",
    )
    runtime_names = {node.id.lower() for node in ast.walk(tree) if isinstance(node, ast.Name)} | {
        node.attr.lower() for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }
    assert not any(
        fragment in name for name in runtime_names for fragment in forbidden_runtime_name_fragments
    )
    assert source.count('["physical_page"]') == 1
    assert {key for key in runtime_keys if "note" in key.lower()} == {"notes_boundary_page"}
    public_parameters = {
        parameter
        for function in (
            build_document_statement_block_hypotheses_v1,
            validate_document_statement_block_hypotheses_v1,
        )
        for parameter in inspect.signature(function).parameters
    }
    assert public_parameters == {"value", "page_projections", "locator_policy"}
    builder_signature = inspect.signature(build_document_statement_block_hypotheses_v1)
    assert list(builder_signature.parameters) == ["page_projections", "locator_policy"]
    assert builder_signature.parameters["locator_policy"].kind is inspect.Parameter.KEYWORD_ONLY
    validator_signature = inspect.signature(validate_document_statement_block_hypotheses_v1)
    assert list(validator_signature.parameters) == [
        "value",
        "page_projections",
        "locator_policy",
    ]
    assert validator_signature.parameters["locator_policy"].kind is inspect.Parameter.KEYWORD_ONLY
