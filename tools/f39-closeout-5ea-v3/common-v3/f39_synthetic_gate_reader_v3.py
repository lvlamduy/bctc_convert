"""Pinned F39 full nonlegacy synthetic gate reader. Standard library only.

This verifies approved owner-reported execution metadata and exact source/Git
equivalence. It does not independently attest tests, financial truth or corpus
acceptance. Historical producer receipts and commits are never rewritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from contextlib import ExitStack, contextmanager
from pathlib import Path

EXPECTED_RUNTIME_HEAD = "5ea0499e8745366c8a9cc11246484fabde78ee6c"
TESTED_COMMIT = "53b6b16a6818b5f71ccb7285e55ed730c4ae14ae"
APPROVED_RECEIPT_SHA256 = "7acbb5d786678af256db1847f2276031b5c180069c42e4fc607680e11188386a"
APPROVED_RECEIPT_BYTES = 8392
VERIFIED_STATUS = "VERIFIED_53B_SOURCE_EQUIVALENT_TO_5EA"
DOC_ONLY_DELTA = "docs/operations/F39_SOURCE_LABEL_T5_UNSEALED_CHECKPOINT_2026-10-26.md"
EXPECTED_SOURCE_SHA256 = {
  "config/families/tm-income-tax-source-label-discrepancies-v1.json": "c8788461c2e3aed5068c9ba3c329f39bfd13d2cf8dea7aede724bbff6b017bcf",
  "scripts/experiments/run_gemini_json_income_tax_accounting_family_v1.py": "f94b6c6b732cf259eed04b6a07ca57124f2ae84076111c5429b6e81f2af462fe",
  "src/bctc_ai/evaluation/gemini_json_income_tax_family_v1.py": "370236b18345bea95315e9e41492ea4306dce35b5da0a2fb7dad6b54cdf26d88",
  "src/bctc_ai/evaluation/gemini_json_income_tax_source_label_discrepancy_v1.py": "96f72e7343e20b888414bd1ff9fb62719acf85d6743a27c4e5ba2e0e9aa879f4",
  "tests/unit/test_gemini_income_tax_raw_money_census_v1.py": "e729d294b6aa4104f2b46786b28be2d8b930ca82a1e642c2dc472b1266317da6",
  "tests/unit/test_gemini_income_tax_source_page_loader_v1.py": "3babfd905e5d1dd0636d032c9794da850c13d67fffe01b687fba2db9cf7b4d19",
  "tests/unit/test_gemini_json_income_tax_ancestry_recognition_frontier_v1.py": "489a25960765a065c5716480a75bf59303660d653cb80ed018b478942ba9218b",
  "tests/unit/test_gemini_json_income_tax_comparative_flow_policy_v1.py": "9f4e3a8ff68106d0fc7274c2bea3215e610ca261c219ba28f4dc674902c5b8ac",
  "tests/unit/test_gemini_json_income_tax_competing_taxable_stages_v1.py": "7eeb5f60dfe324289dc3af16576a3018a2024705962e1ff79cbe26c7d75c69df",
  "tests/unit/test_gemini_json_income_tax_document_period_cache_v1.py": "4702e84d8a4e59f1c07ef0eb49e73ecb562aeb80507f4d6b30b0cdbce9e632e3",
  "tests/unit/test_gemini_json_income_tax_family_v1.py": "e48076ce609e0b56b9f8e0f45ef9bc6b4c1677db6ac6d0f47b3e5ea74de306bc",
  "tests/unit/test_gemini_json_income_tax_first_months_narrative_v1.py": "e1ea0840a3408c66879266844c8450b39a366293ad7a76774490f52de733267d",
  "tests/unit/test_gemini_json_income_tax_flow_period_controls_v1.py": "da4ea1c4141c80f480788a46befe8e815025a37de854ce83af61d1ba8e4d112c",
  "tests/unit/test_gemini_json_income_tax_frontier_guards_v1.py": "ee20a6f0b562fe287bdf3769980261043540e07117bd00eff07351c22f5def84",
  "tests/unit/test_gemini_json_income_tax_named_quarter_ytd_scaffold_v2.py": "2aba0e60fa396ce517625072140b38502ba67d57ebcced63597a870744150d5f",
  "tests/unit/test_gemini_json_income_tax_owned_explicit_range_caption_v1.py": "e9ce061a5d5069080e8dd1ba43b461c65eeee86e945ec388d3a36b087ab5ac0a",
  "tests/unit/test_gemini_json_income_tax_part_period_catalog_v1.py": "1d293b3104fe72306c791c2f7650747898ab34b28c30779c1e469dfa61062b59",
  "tests/unit/test_gemini_json_income_tax_part_period_context_v1.py": "c5dcbe916c6e74c22bc93aa18c0e843b051fd8707013e401e88ebebe2af58b17",
  "tests/unit/test_gemini_json_income_tax_payable_subtotal_role_v1.py": "b030f4a1ad516723a5239110d452d648e8c3f394faa33cd25593bc25d63aa0b1",
  "tests/unit/test_gemini_json_income_tax_printed_outline_v1.py": "6880b90395095b0c6eb1f8fd166b4777dcf9c218ad44be92eed4a98588dcb615",
  "tests/unit/test_gemini_json_income_tax_quarter_endpoint_ytd_scaffold_v1.py": "6dd525ed00686212f413475db7b6b223755bee6f65c72644a3f22129d636d92a",
  "tests/unit/test_gemini_json_income_tax_recognition_frontier_v1.py": "0b9a09eebd4cdd4a8301f501fc642fda684b7d19b493db7a794965ada4123305",
  "tests/unit/test_gemini_json_income_tax_recognition_rate_effect_v1.py": "9ec9de9aa4bed7430a2e719c35f044bfceb8ca138b45a2a057c3ba998a6212eb",
  "tests/unit/test_gemini_json_income_tax_registered_part_period_integration_v1.py": "8101a1ecb1123aeead41a99f74e1c6013aa6078cc7d65364c2da789a44e3fc7c",
  "tests/unit/test_gemini_json_income_tax_registered_section_caption_integration_v1.py": "b66478ca34497722e3f4c845f01648f09c1e2a212b56d3621ecf994f1442d7e5",
  "tests/unit/test_gemini_json_income_tax_root_controls_v1.py": "26d73b4c2e94af03b13662dfb8a6e34b1e0577ec92b4d5093f216aa528db1e4c",
  "tests/unit/test_gemini_json_income_tax_section_caption_repair_v1.py": "606b366aba0e4153867eea2b3274aaa3ebb0dae5c6d9358c5512ed7640895e35",
  "tests/unit/test_gemini_json_income_tax_signed_display_v1.py": "bcf3770f56dc2fdea214819ee3ec2ad9ffc481e97e9f7d43e87eb3c54774d38d",
  "tests/unit/test_gemini_json_income_tax_source_context_v1.py": "825e10a031c51a5cc4b0bd89bd48120e2d0065aabc84055243bd1ae33eb64960",
  "tests/unit/test_gemini_json_income_tax_source_label_discrepancy_v1.py": "2a374de600efec800461b5a71e6db3e38af6f86dc4c1891f15f5c4279e64156e",
  "tests/unit/test_income_tax_variant_graph_v1.py": "aa6e92f28fd55b21a70586d22c6675aac731158015b978368c74bc24ede3cebf",
  "tests/unit/test_run_gemini_json_income_tax_accounting_family_v1.py": "e76ac65ff34592227fa35100ac19498e332d1d19754528893df475276abbc9c5"
}
EXPECTED_SOURCE_BYTES = {
  "config/families/tm-income-tax-source-label-discrepancies-v1.json": 2004,
  "scripts/experiments/run_gemini_json_income_tax_accounting_family_v1.py": 93811,
  "scripts/experiments/run_gemini_json_multitable_hierarchical_accounting_family_v1.py": 149733,
  "src/bctc_ai/evaluation/gemini_json_income_tax_family_v1.py": 606504,
  "src/bctc_ai/evaluation/gemini_json_income_tax_source_label_discrepancy_v1.py": 15735,
  "src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py": 608721,
  "tests/unit/test_gemini_income_tax_raw_money_census_v1.py": 38033,
  "tests/unit/test_gemini_income_tax_source_page_loader_v1.py": 11804,
  "tests/unit/test_gemini_json_income_tax_ancestry_recognition_frontier_v1.py": 18258,
  "tests/unit/test_gemini_json_income_tax_comparative_flow_policy_v1.py": 188677,
  "tests/unit/test_gemini_json_income_tax_competing_taxable_stages_v1.py": 9570,
  "tests/unit/test_gemini_json_income_tax_document_period_cache_v1.py": 43891,
  "tests/unit/test_gemini_json_income_tax_family_v1.py": 200764,
  "tests/unit/test_gemini_json_income_tax_first_months_narrative_v1.py": 8437,
  "tests/unit/test_gemini_json_income_tax_flow_period_controls_v1.py": 20086,
  "tests/unit/test_gemini_json_income_tax_frontier_guards_v1.py": 12762,
  "tests/unit/test_gemini_json_income_tax_named_quarter_ytd_scaffold_v2.py": 8198,
  "tests/unit/test_gemini_json_income_tax_owned_explicit_range_caption_v1.py": 10862,
  "tests/unit/test_gemini_json_income_tax_part_period_catalog_v1.py": 35149,
  "tests/unit/test_gemini_json_income_tax_part_period_context_v1.py": 26759,
  "tests/unit/test_gemini_json_income_tax_payable_subtotal_role_v1.py": 15289,
  "tests/unit/test_gemini_json_income_tax_printed_outline_v1.py": 11206,
  "tests/unit/test_gemini_json_income_tax_quarter_endpoint_ytd_scaffold_v1.py": 14297,
  "tests/unit/test_gemini_json_income_tax_recognition_frontier_v1.py": 23163,
  "tests/unit/test_gemini_json_income_tax_recognition_rate_effect_v1.py": 27343,
  "tests/unit/test_gemini_json_income_tax_registered_part_period_integration_v1.py": 45755,
  "tests/unit/test_gemini_json_income_tax_registered_section_caption_integration_v1.py": 34191,
  "tests/unit/test_gemini_json_income_tax_root_controls_v1.py": 20424,
  "tests/unit/test_gemini_json_income_tax_section_caption_repair_v1.py": 24482,
  "tests/unit/test_gemini_json_income_tax_signed_display_v1.py": 109421,
  "tests/unit/test_gemini_json_income_tax_source_context_v1.py": 13125,
  "tests/unit/test_gemini_json_income_tax_source_label_discrepancy_v1.py": 22215,
  "tests/unit/test_income_tax_variant_graph_v1.py": 6355,
  "tests/unit/test_run_gemini_json_income_tax_accounting_family_v1.py": 64505
}
EXPECTED_FROZEN_SHA256 = {
  "scripts/experiments/run_gemini_json_multitable_hierarchical_accounting_family_v1.py": "d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5",
  "src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py": "bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2"
}
EXPECTED_TEST_MODULES = [
  "tests/unit/test_gemini_income_tax_raw_money_census_v1.py",
  "tests/unit/test_gemini_income_tax_source_page_loader_v1.py",
  "tests/unit/test_gemini_json_income_tax_ancestry_recognition_frontier_v1.py",
  "tests/unit/test_gemini_json_income_tax_comparative_flow_policy_v1.py",
  "tests/unit/test_gemini_json_income_tax_competing_taxable_stages_v1.py",
  "tests/unit/test_gemini_json_income_tax_document_period_cache_v1.py",
  "tests/unit/test_gemini_json_income_tax_family_v1.py",
  "tests/unit/test_gemini_json_income_tax_first_months_narrative_v1.py",
  "tests/unit/test_gemini_json_income_tax_flow_period_controls_v1.py",
  "tests/unit/test_gemini_json_income_tax_frontier_guards_v1.py",
  "tests/unit/test_gemini_json_income_tax_named_quarter_ytd_scaffold_v2.py",
  "tests/unit/test_gemini_json_income_tax_owned_explicit_range_caption_v1.py",
  "tests/unit/test_gemini_json_income_tax_part_period_catalog_v1.py",
  "tests/unit/test_gemini_json_income_tax_part_period_context_v1.py",
  "tests/unit/test_gemini_json_income_tax_payable_subtotal_role_v1.py",
  "tests/unit/test_gemini_json_income_tax_printed_outline_v1.py",
  "tests/unit/test_gemini_json_income_tax_quarter_endpoint_ytd_scaffold_v1.py",
  "tests/unit/test_gemini_json_income_tax_recognition_frontier_v1.py",
  "tests/unit/test_gemini_json_income_tax_recognition_rate_effect_v1.py",
  "tests/unit/test_gemini_json_income_tax_registered_part_period_integration_v1.py",
  "tests/unit/test_gemini_json_income_tax_registered_section_caption_integration_v1.py",
  "tests/unit/test_gemini_json_income_tax_root_controls_v1.py",
  "tests/unit/test_gemini_json_income_tax_section_caption_repair_v1.py",
  "tests/unit/test_gemini_json_income_tax_signed_display_v1.py",
  "tests/unit/test_gemini_json_income_tax_source_context_v1.py",
  "tests/unit/test_gemini_json_income_tax_source_label_discrepancy_v1.py",
  "tests/unit/test_income_tax_variant_graph_v1.py",
  "tests/unit/test_run_gemini_json_income_tax_accounting_family_v1.py"
]
EXPECTED_EXCLUDED_MODULES = [
  "test_build_annual_2025_income_tax_8bank_codex_verified_mapping_v1.py",
  "test_build_income_tax_8bank_codex_verified_mapping_v1.py"
]
EXPECTED_IMPORT_ORIGINS = {
  "bctc_ai": "/home/bctc/codex-runs/f39-t5-nonlegacy-20261026-v2/repo/src/bctc_ai/__init__.py",
  "bctc_ai.evaluation.gemini_json_income_tax_family_v1": "/home/bctc/codex-runs/f39-t5-nonlegacy-20261026-v2/repo/src/bctc_ai/evaluation/gemini_json_income_tax_family_v1.py",
  "bctc_ai.evaluation.gemini_json_income_tax_source_label_discrepancy_v1": "/home/bctc/codex-runs/f39-t5-nonlegacy-20261026-v2/repo/src/bctc_ai/evaluation/gemini_json_income_tax_source_label_discrepancy_v1.py"
}
EXPECTED_DRIVER_SHA256 = {
  "/mnt/d/bctc_bank/restore-tools/runtime/codex_t5_test_driver_20261026_v2.py": "3edfad8e9c5229c77d6e9474d0c77512dd12559d402d4ce1014d83eb25aff220",
  "/mnt/d/bctc_bank/restore-tools/runtime/run_codex_t5_tests_20261026_v2.sh": "df1bbb2af6bb5b8d0098b1177e9cfff7cea0e16f4f152c738fbfa5cc3709f35c"
}
EXPECTED_REPORT_KEYS = frozenset([
  "address_space_limit",
  "commit",
  "elapsed_seconds",
  "excluded_legacy_modules",
  "exit_code",
  "financial_acceptance",
  "finished_unix",
  "format_version",
  "frozen_sha256",
  "import_origins",
  "junit_sha256",
  "memavailable_kib_before",
  "mode",
  "nice",
  "pytest_exit_code",
  "python",
  "real_corpus_pdf_store_jobs",
  "ruff_exit_code",
  "ruff_log_sha256",
  "run_root",
  "runner_scripts_sha256",
  "selected_test_modules",
  "source_test_sha256",
  "started_unix",
  "status",
  "systemd_unit",
  "unit"
])
EXTRA_IMPORT_SOURCE = {
  "src/bctc_ai/__init__.py": {
    "sha256": "64493c2a975d7a185a1c3e43d9f2d1c9bac3a3d01eda9caf33c2b3e38a33df74",
    "size_bytes": 46
  }
}
HISTORICAL_RUN_ROOT = "/home/bctc/codex-runs/f39-t5-nonlegacy-20261026-v2"


class F39SyntheticGateError(ValueError):
    """A fixed approved gate or tested source equivalence did not authenticate."""


def _need(condition, message):
    if not condition:
        raise F39SyntheticGateError(message)


def _strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            _need(key not in result, "duplicate gate JSON key")
            result[key] = value
        return result

    def nonfinite(token):
        raise F39SyntheticGateError("nonfinite gate JSON token: " + token)

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=nonfinite)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise F39SyntheticGateError("gate is not strict UTF-8 JSON") from exc


def _regular_absolute(path):
    _need(isinstance(path, Path) and path.is_absolute() and ".." not in path.parts,
          "absolute canonical file path required")
    for member in (path, *path.parents):
        _need(not member.is_symlink()
              and not getattr(member, "is_junction", lambda: False)(),
              "file authority crosses symlink/junction")
    return path


def _identity(info):
    return tuple(getattr(info, key) for key in
                 ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns"))


@contextmanager
def _held_file(path, expected_sha, expected_size):
    path = _regular_absolute(path)
    _need(re.fullmatch(r"[0-9a-f]{64}", expected_sha) is not None
          and type(expected_size) is int and 0 < expected_size <= 16 * 1024 * 1024,
          "invalid fixed source/file pin")
    with path.open("rb") as source:
        before = os.fstat(source.fileno())
        _need(stat.S_ISREG(before.st_mode) and before.st_size == expected_size,
              "gate/source file type or byte count differs: " + str(path))
        raw = source.read(expected_size + 1)
        _need(len(raw) == expected_size and hashlib.sha256(raw).hexdigest() == expected_sha,
              "gate/source SHA differs: " + str(path))
        _need(_identity(before) == _identity(os.fstat(source.fileno()))
              == _identity(path.stat()), "gate/source identity changed while reading")
        yield {"path": str(path), "sha256": expected_sha, "size_bytes": expected_size, "raw": raw}
        source.seek(0)
        final_raw = source.read(expected_size + 1)
        _regular_absolute(path)
        _need(_identity(before) == _identity(os.fstat(source.fileno()))
              == _identity(path.stat()) and final_raw == raw,
              "gate/source file drifted during validation: " + str(path))


def _git(repo, *args):
    try:
        return subprocess.check_output(
            ["git", "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false",
             "-C", str(repo), *args],
            stderr=subprocess.PIPE, timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise F39SyntheticGateError("Git metadata/source proof failed") from exc


def _validate_reported_gate(receipt):
    """Fixed report semantics; never a replacement for immutable raw-byte pin."""
    _need(type(receipt) is dict and set(receipt) == EXPECTED_REPORT_KEYS,
          "full nonlegacy gate field axis differs")
    expected = {
        "format_version": "CODEX_F39_T5_SYNTHETIC_TEST_RUN_V1",
        "commit": TESTED_COMMIT, "mode": "nonlegacy", "status": "PASS_SYNTHETIC_ONLY",
        "run_root": HISTORICAL_RUN_ROOT,
        "systemd_unit": "codex-f39-t5-nonlegacy-20261026-v2",
        "python": "3.12.3 (main, Aug 31 2026, 10:18:26) [GCC 13.3.0]",
        "junit_sha256": "7305c5a85a180a99b7c0d78239f7fe0a85bdf65759788c2b9c109c87346462fc",
        "ruff_log_sha256": "82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18",
    }
    for name, value in expected.items():
        _need(type(receipt.get(name)) is type(value) and receipt[name] == value,
              "approved full nonlegacy field differs: " + name)
    for name in ("exit_code", "pytest_exit_code", "ruff_exit_code"):
        _need(type(receipt.get(name)) is int and receipt[name] == 0,
              "approved actual Ruff/pytest/exit0 required: " + name)
    _need(receipt["financial_acceptance"] is False
          and receipt["real_corpus_pdf_store_jobs"] is False,
          "synthetic-only evidence boundary differs")
    _need(type(receipt["nice"]) is int and receipt["nice"] >= 19
          and receipt["address_space_limit"] == [2147483648, 2147483648]
          and all(type(x) is int for x in receipt["address_space_limit"]),
          "historical tested cap/nice differs")
    _need(type(receipt["memavailable_kib_before"]) is int
          and receipt["memavailable_kib_before"] > 0,
          "historical memory metadata absent")
    _need(receipt["selected_test_modules"] == EXPECTED_TEST_MODULES
          and len(EXPECTED_TEST_MODULES) == 28
          and len(set(EXPECTED_TEST_MODULES)) == 28,
          "all exact28 nonlegacy test modules required")
    _need(receipt["excluded_legacy_modules"] == EXPECTED_EXCLUDED_MODULES,
          "legacy exclusion axis differs")
    _need(receipt["source_test_sha256"] == EXPECTED_SOURCE_SHA256
          and receipt["frozen_sha256"] == EXPECTED_FROZEN_SHA256,
          "full tested source/test/frozen hash axis differs")
    _need(receipt["import_origins"] == EXPECTED_IMPORT_ORIGINS,
          "reported test import origins differ")
    _need(receipt["runner_scripts_sha256"] == EXPECTED_DRIVER_SHA256,
          "reported actual test-driver origins differ")
    _need(all(name in EXPECTED_SOURCE_SHA256 for name in EXPECTED_TEST_MODULES),
          "a selected test lacks a tested source-body pin")


def validate_f39_synthetic_gate_v1(*, repo: Path, receipt_ref: dict, expected_head: str) -> dict:
    """Verify only approved7ac full gate and explicit53b->5ea docs-only bridge.

    Runtime source bytes must be actual LF Git bytes. CRLF is never normalized.
    This function runs Git/file metadata checks only, no project/test/data job.
    """
    _need(sys.version_info[:2] == (3, 12), "reader requires Python3.12")
    _need(type(expected_head) is str and expected_head == EXPECTED_RUNTIME_HEAD,
          "runtime expected HEAD must be exact approved5ea")
    _need(type(receipt_ref) is dict and set(receipt_ref) == {"path", "sha256", "size_bytes"},
          "exact independent approved receipt path/SHA/bytes required")
    _need(type(receipt_ref["path"]) is str
          and type(receipt_ref["size_bytes"]) is int
          and receipt_ref["sha256"] == APPROVED_RECEIPT_SHA256
          and receipt_ref["size_bytes"] == APPROVED_RECEIPT_BYTES,
          "only immutable approved7ac full nonlegacy receipt is accepted; caller reseal forbidden")
    repo = _regular_absolute(repo)
    _need(repo.is_dir(), "runtime repository absent")
    receipt_path = _regular_absolute(Path(receipt_ref["path"]))
    _need(receipt_path.suffix == ".json", "approved gate must be JSON")

    def git_barrier():
        _need(_git(repo, "rev-parse", "HEAD").decode().strip() == EXPECTED_RUNTIME_HEAD,
              "runtime repository HEAD is not exact5ea")
        _need(not _git(repo, "status", "--porcelain", "--untracked-files=all").strip(),
              "runtime repository must be clean")
        _need(_git(repo, "rev-parse", EXPECTED_RUNTIME_HEAD + "^").decode().strip() == TESTED_COMMIT,
              "approved runtime parent is not exact tested53b")
        _need(_git(repo, "diff", "--name-status", "--no-renames", TESTED_COMMIT,
                   EXPECTED_RUNTIME_HEAD) == ("A\t" + DOC_ONLY_DELTA + "\n").encode(),
              "tested53b->runtime5ea is not the sole approved docs-only delta")

    with ExitStack() as held:
        approved = held.enter_context(_held_file(
            receipt_path, APPROVED_RECEIPT_SHA256, APPROVED_RECEIPT_BYTES))
        receipt = _strict_json(approved["raw"])
        _validate_reported_gate(receipt)
        git_barrier()
        pins = {**EXPECTED_SOURCE_SHA256, **EXPECTED_FROZEN_SHA256,
                **{name: value["sha256"] for name, value in EXTRA_IMPORT_SOURCE.items()}}
        proofs = []
        for name, digest in sorted(pins.items()):
            _need(not Path(name).is_absolute() and ".." not in Path(name).parts,
                  "unsafe fixed source path")
            tested = _git(repo, "cat-file", "blob", TESTED_COMMIT + ":" + name)
            runtime = _git(repo, "cat-file", "blob", EXPECTED_RUNTIME_HEAD + ":" + name)
            size = EXPECTED_SOURCE_BYTES.get(name, EXTRA_IMPORT_SOURCE.get(name, {}).get("size_bytes"))
            _need(tested == runtime and len(runtime) == size
                  and hashlib.sha256(runtime).hexdigest() == digest,
                  "tested/runtime Git blob body mismatch: " + name)
            actual = held.enter_context(_held_file(repo / name, digest, size))
            _need(actual["raw"] == runtime, "actual runtime source is not exact LF Git blob: " + name)
            proofs.append({"path": name, "sha256": digest, "size_bytes": size,
                           "tested_blob_equals_runtime_blob_equals_actual": True})
        git_barrier()
        result = {
            "status": VERIFIED_STATUS,
            "expected_runtime_head": EXPECTED_RUNTIME_HEAD, "tested_commit": TESTED_COMMIT,
            "receipt_ref": {key: approved[key] for key in ("path", "sha256", "size_bytes")},
            "approved_report_status": receipt["status"], "selected_test_module_count": 28,
            "receipt_source_test_file_count": len(EXPECTED_SOURCE_SHA256),
            "receipt_frozen_file_count": len(EXPECTED_FROZEN_SHA256),
            "actual_source_file_proofs": proofs, "docs_only_delta": [DOC_ONLY_DELTA],
            "test_execution_evidence": "PINNED_APPROVED_OWNER_REPORTED_EXECUTION_NOT_INDEPENDENT_ATTESTATION",
            "junit_ruff_hashes": {key: receipt[key] for key in ("junit_sha256", "ruff_log_sha256")},
            "junit_ruff_bodies_revalidated_by_this_reader": False,
            "financial_acceptance": False, "family_terminal": False,
            "common_or_full_corpus_execution_proven": False,
            "historical_test_caps_are_not_COMMON_resource_approval": True,
        }
    # All held file exit barriers completed before returning success.
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--receipt-sha256", required=True)
    parser.add_argument("--receipt-bytes", type=int, required=True)
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args(argv)
    try:
        _need(sys.flags.isolated and sys.dont_write_bytecode,
              "CLI requires isolated Python3.12 -I -B")
        result = validate_f39_synthetic_gate_v1(
            repo=args.repo,
            receipt_ref={"path": args.receipt, "sha256": args.receipt_sha256,
                         "size_bytes": args.receipt_bytes},
            expected_head=args.expected_head,
        )
    except (F39SyntheticGateError, OSError, ValueError) as exc:
        print("F39_SYNTHETIC_GATE_FAIL_CLOSED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
