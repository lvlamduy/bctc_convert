#!/usr/bin/env python3
"""Run every current accounting family over the 19-bank paid JSON corpus.

The eight previously processed banks are deliberately outside this runner. Their
immutable family results are combined only at the reporting layer after this
19-bank sweep has completed.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, NamedTuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    compile_gemini_json_flat_family_specs_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1  # noqa: E402
from bctc_ai.storage.gemini_accounting_family_store_v1 import (  # noqa: E402
    load_gemini_accounting_family_sweep_v1,
)
from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import (  # noqa: E402
    validate_current_corpus_manifest_index_v1,
)


class RunGeminiJsonAllAccountingFamiliesV1Error(RuntimeError):
    """The all-family execution frontier is incomplete or drifted."""


class FamilyJob(NamedTuple):
    schema_order: int
    family_id: str
    vietnamese_name: str
    stem: str
    runner: str | None = None
    topology: str | None = None
    evaluation: str | None = None
    schema: str | None = None


REUSE_ONLY_BANKS = frozenset({"ACB", "BID", "CTG", "HDB", "MBB", "VCB", "VIB", "VPB"})
PAID_BANKS = frozenset(
    {
        "ABB",
        "BAB",
        "BVB",
        "EIB",
        "KLB",
        "LPB",
        "MSB",
        "NAB",
        "NVB",
        "OCB",
        "PGB",
        "SGB",
        "SHB",
        "SSB",
        "STB",
        "TCB",
        "TPB",
        "VAB",
        "VBB",
    }
)
EXPECTED_DOCUMENT_COUNT = 279
EXPECTED_PAGE_COUNT = 15_968


FAMILY_JOBS = (
    FamilyJob(1, "CASH_PRECIOUS_METALS", "Tiền, kim loại quý và đá quý", "cash-precious-metals"),
    FamilyJob(
        2,
        "CENTRAL_BANK_DEPOSITS",
        "Tiền gửi tại Ngân hàng Nhà nước",
        "central-bank-deposits",
        topology="tm-central-bank-deposits-topology-v2.json",
        schema="tm-central-bank-deposits-schema-binding-v2.json",
    ),
    FamilyJob(
        3,
        "INTERBANK_DEPOSITS_AND_LOANS",
        "Tiền gửi tại và cho vay các TCTD khác — tài sản",
        "interbank-deposits-loans",
        topology="tm-interbank-deposits-loans-topology-v4.json",
        evaluation="tm-interbank-deposits-loans-evaluation-v4.json",
        schema="tm-interbank-deposits-loans-schema-binding-v4.json",
    ),
    FamilyJob(4, "TRADING_SECURITIES", "Chứng khoán kinh doanh", "trading-securities"),
    FamilyJob(
        5,
        "DERIVATIVE_FINANCIAL_INSTRUMENTS",
        "Công cụ tài chính phái sinh",
        "derivative-financial-instruments",
    ),
    FamilyJob(6, "LOAN_TYPE_CLASSIFICATION", "Cho vay theo loại hình", "loan-type-classification"),
    FamilyJob(
        7,
        "LOAN_INDUSTRY_CLASSIFICATION",
        "Cho vay theo ngành nghề kinh doanh",
        "loan-industry-classification",
    ),
    FamilyJob(
        8,
        "LOAN_QUALITY_CLASSIFICATION",
        "Chất lượng cho vay",
        "loan-quality-classification",
    ),
    FamilyJob(
        9,
        "LOAN_MATURITY_BUCKETS",
        "Dư nợ theo thời gian/thời hạn gốc",
        "loan-maturity-buckets",
    ),
    FamilyJob(
        10,
        "LOAN_CURRENCY_CLASSIFICATION",
        "Cho vay theo loại tiền tệ",
        "loan-currency-classification",
    ),
    FamilyJob(
        11,
        "LOAN_GEOGRAPHIC_CLASSIFICATION",
        "Cho vay theo khu vực địa lý",
        "loan-geographic-classification",
    ),
    FamilyJob(
        12,
        "LOAN_ENTERPRISE_FAMILY12",
        "Cho vay theo loại hình doanh nghiệp/đối tượng khách hàng",
        "loan-enterprise-family12",
        topology="tm-loan-enterprise-family12-topology-v4.json",
        evaluation="tm-loan-enterprise-family12-evaluation-v5.json",
        schema="tm-loan-enterprise-family12-schema-binding-v6.json",
    ),
    FamilyJob(
        13,
        "PROVISION_MOVEMENT_ROLLFORWARD",
        "Biến động dự phòng rủi ro cho vay",
        "provision-movement-rollforward",
    ),
    FamilyJob(14, "PURCHASED_DEBT_ACTIVITY", "Hoạt động mua nợ", "purchased-debt-activity"),
    FamilyJob(
        15,
        "CUSTOMER_DEPOSIT_CLASSIFICATION",
        "Tiền gửi khách hàng theo loại/kỳ hạn/đối tượng",
        "customer-deposit-classification",
    ),
    FamilyJob(16, "INVESTMENT_SECURITIES", "Chứng khoán đầu tư", "investment-securities"),
    FamilyJob(
        17,
        "OTHER_LONG_TERM_INVESTMENTS",
        "Các khoản đầu tư dài hạn khác",
        "other-long-term-investments",
    ),
    FamilyJob(
        18,
        "TANGIBLE_FIXED_ASSETS_ROLLFORWARD",
        "Tăng, giảm tài sản cố định hữu hình",
        "tangible-fixed-assets",
    ),
    FamilyJob(
        19,
        "LEASED_FIXED_ASSETS_ROLLFORWARD",
        "Tăng, giảm tài sản cố định thuê tài chính",
        "leased-fixed-assets",
    ),
    FamilyJob(
        20,
        "INTANGIBLE_FIXED_ASSETS_ROLLFORWARD",
        "Tăng, giảm tài sản cố định vô hình",
        "intangible-fixed-assets",
    ),
    FamilyJob(
        21,
        "INVESTMENT_PROPERTY_ROLLFORWARD",
        "Tăng, giảm bất động sản đầu tư",
        "investment-property",
    ),
    FamilyJob(22, "OTHER_ASSETS", "Tài sản Có khác", "other-assets"),
    FamilyJob(
        23,
        "GOVERNMENT_SBV_LIABILITIES",
        "Nợ Chính phủ và Ngân hàng Nhà nước",
        "government-sbv-liabilities",
    ),
    FamilyJob(
        24,
        "ENTRUSTED_INVESTMENT_RISK_CAPITAL",
        "Vốn nhận tài trợ, ủy thác đầu tư và cho vay chịu rủi ro",
        "entrusted-investment-risk-capital",
    ),
    FamilyJob(25, "ISSUED_VALUABLE_PAPERS", "Phát hành giấy tờ có giá", "issued-valuable-papers"),
    FamilyJob(
        26,
        "OTHER_PAYABLES_LIABILITIES",
        "Các khoản phải trả và công nợ khác",
        "other-payables-liabilities",
    ),
    FamilyJob(27, "CAPITAL_AND_FUNDS", "Vốn và các quỹ", "capital-and-funds"),
    FamilyJob(
        28,
        "INTEREST_INCOME",
        "Thu nhập lãi và các khoản tương tự",
        "interest-income",
    ),
    FamilyJob(
        29,
        "INTEREST_EXPENSE",
        "Chi phí lãi và các khoản tương tự",
        "interest-expense",
    ),
    FamilyJob(30, "NET_INTEREST_INCOME", "Thu nhập từ lãi thuần", "net-interest-income"),
    FamilyJob(31, "SERVICE_ACTIVITY", "Thu nhập, chi phí và lãi thuần dịch vụ", "service-activity"),
    FamilyJob(
        32,
        "FX_GOLD_ACTIVITY",
        "Lãi/lỗ thuần kinh doanh vàng và ngoại hối",
        "fx-gold-activity",
    ),
    FamilyJob(
        33,
        "TRADING_SECURITIES_ACTIVITY",
        "Lãi/lỗ thuần mua bán chứng khoán kinh doanh",
        "trading-securities-activity",
    ),
    FamilyJob(
        34,
        "INVESTMENT_SECURITIES_ACTIVITY",
        "Lãi/lỗ thuần mua bán chứng khoán đầu tư",
        "investment-securities-activity",
    ),
    FamilyJob(
        35,
        "COMBINED_SECURITIES_NET",
        "Lãi thuần chứng khoán kinh doanh và đầu tư gộp",
        "combined-securities-net",
    ),
    FamilyJob(
        36,
        "CAPITAL_CONTRIBUTION_DIVIDEND_INCOME",
        "Thu nhập góp vốn, mua cổ phần và cổ tức",
        "capital-contribution-dividend-income",
    ),
    FamilyJob(
        37,
        "OPERATING_EXPENSE",
        "Chi phí quản lý chung/chi phí hoạt động",
        "operating-expense",
    ),
    FamilyJob(
        38,
        "CREDIT_RISK_PROVISION_EXPENSE",
        "Chi phí dự phòng rủi ro tín dụng",
        "credit-risk-provision-expense",
    ),
    FamilyJob(
        39,
        "OTHER_ACTIVITY",
        "Thu nhập, chi phí và lãi thuần hoạt động khác",
        "other-activity",
    ),
    FamilyJob(40, "INCOME_TAX", "Chi phí thuế thu nhập doanh nghiệp", "income-tax"),
    FamilyJob(41, "CASH_EQUIVALENTS", "Tiền và các khoản tương đương tiền", "cash-equivalents"),
    FamilyJob(
        42,
        "SUBSIDIARY_ACQUISITION_DISPOSAL",
        "Mua mới và thanh lý công ty con",
        "subsidiary-acquisition-disposal",
    ),
    FamilyJob(43, "EMPLOYEE_INCOME", "Thu nhập nhân viên ngân hàng", "employee-income"),
    FamilyJob(
        44,
        "STATE_BUDGET_OBLIGATIONS",
        "Nghĩa vụ với ngân sách Nhà nước",
        "state-budget-obligations",
    ),
    FamilyJob(
        45,
        "CUSTOMER_COLLATERAL_HELD",
        "Tài sản thế chấp của khách hàng ngân hàng đang nắm giữ",
        "customer-collateral-held",
    ),
    FamilyJob(
        46,
        "BANK_PLEDGED_OR_DISCOUNTED_ASSETS",
        "Tài sản/GTCG ngân hàng đem thế chấp, cầm cố, chiết khấu",
        "bank-pledged-discounted-assets",
    ),
    FamilyJob(
        47,
        "CONTINGENT_LIABILITIES_AND_COMMITMENTS",
        "Nghĩa vụ nợ tiềm ẩn và các cam kết",
        "contingent-liabilities-commitments",
    ),
    FamilyJob(
        48,
        "FINANCIAL_INSTRUMENTS",
        "Công cụ tài chính — giá trị ghi sổ và giá trị hợp lý",
        "financial-instruments",
        runner="run_gemini_json_financial_instruments_family_v1.py",
    ),
    FamilyJob(
        49,
        "CURRENCY_RISK",
        "Rủi ro tiền tệ",
        "currency-risk",
        runner="run_gemini_json_currency_risk_family_v1.py",
    ),
    FamilyJob(
        50,
        "INTEREST_RATE_RISK",
        "Rủi ro lãi suất",
        "interest-rate-risk",
        runner="run_gemini_json_interest_rate_risk_family_v1.py",
    ),
    FamilyJob(
        51,
        "LIQUIDITY_RISK",
        "Rủi ro thanh khoản",
        "liquidity-risk",
        runner="run_gemini_json_liquidity_risk_family_v1.py",
    ),
    FamilyJob(
        52,
        "EXCHANGE_RATE",
        "Tỷ giá ngoại tệ cuối kỳ",
        "exchange-rate",
        runner="run_gemini_json_exchange_rate_family_v1.py",
    ),
    FamilyJob(
        53,
        "INTERBANK_FUNDING",
        "Tiền gửi và vay các TCTD khác — nguồn vốn",
        "interbank-funding",
    ),
    FamilyJob(
        54,
        "SECURITIES_GEOGRAPHY",
        "Kinh doanh và đầu tư chứng khoán theo khu vực địa lý",
        "securities-geography",
    ),
    FamilyJob(
        55,
        "CONSOLIDATED_SEGMENT_REPORT",
        "Báo cáo bộ phận hợp nhất",
        "consolidated-segment-report",
        runner="run_gemini_json_segment_report_accounting_family_v1.py",
    ),
)


RUNNER_BY_FORMAT = {
    "ACCOUNTING_CUSTOMER_DEPOSIT_FAMILY_EVALUATION_SPEC_V1": "run_gemini_json_customer_deposit_accounting_family_v1.py",
    "ACCOUNTING_DUAL_COMPONENT_FAMILY_EVALUATION_SPEC_V1": "run_gemini_json_dual_component_accounting_family_v1.py",
    "ACCOUNTING_EQUITY_MATRIX_FAMILY_EVALUATION_SPEC_V1": "run_gemini_json_equity_matrix_accounting_family_v1.py",
    "ACCOUNTING_FIXED_ASSET_ROLLFORWARD_FAMILY_EVALUATION_SPEC_V1": "run_gemini_json_fixed_asset_rollforward_accounting_family_v1.py",
    "ACCOUNTING_INVESTMENT_SECURITIES_FAMILY_EVALUATION_SPEC_V1": "run_gemini_json_investment_securities_accounting_family_v1.py",
    "ACCOUNTING_MULTITABLE_HIERARCHICAL_FAMILY_EVALUATION_SPEC_V1": "run_gemini_json_multitable_hierarchical_accounting_family_v1.py",
    "ACCOUNTING_OTHER_LONG_TERM_INVESTMENTS_FAMILY_EVALUATION_SPEC_V1": "run_gemini_json_other_long_term_investments_accounting_family_v1.py",
}
GENERIC_FORMATS = frozenset(
    {
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V1",
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V2",
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V3",
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V4",
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V5",
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V6",
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V7",
        "ACCOUNTING_FAMILY_EVALUATION_SPEC_V8",
        "ACCOUNTING_ROLLFORWARD_FAMILY_EVALUATION_SPEC_V1",
        "ACCOUNTING_STACKED_PERIOD_FAMILY_EVALUATION_SPEC_V1",
    }
)


def _spec_paths(job: FamilyJob) -> tuple[Path, Path, Path] | None:
    root = ROOT / "config/families"
    topology = job.topology or f"tm-{job.stem}-topology-v1.json"
    evaluation = job.evaluation or f"tm-{job.stem}-evaluation-v1.json"
    schema = job.schema or f"tm-{job.stem}-schema-binding-v1.json"
    return root / topology, root / evaluation, root / schema


def _load_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RunGeminiJsonAllAccountingFamiliesV1Error(f"required file is absent: {path}")
    try:
        value = json.loads(path.read_bytes())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunGeminiJsonAllAccountingFamiliesV1Error(f"JSON is invalid: {path}") from exc
    if type(value) is not dict:
        raise RunGeminiJsonAllAccountingFamiliesV1Error(f"JSON root is invalid: {path}")
    return value


def _compiled_jobs() -> list[dict[str, Any]]:
    if [job.schema_order for job in FAMILY_JOBS] != list(range(1, 56)):
        raise RunGeminiJsonAllAccountingFamiliesV1Error("family schema order is not exhaustive")
    if len({job.family_id for job in FAMILY_JOBS}) != len(FAMILY_JOBS):
        raise RunGeminiJsonAllAccountingFamiliesV1Error("family identifiers are duplicate")
    compiled_jobs = []
    for job in FAMILY_JOBS:
        paths = _spec_paths(job)
        if paths is None:
            compiled_jobs.append(
                {
                    "execution_kind": "DERIVED_VISIBLE_STATEMENT_LINE",
                    "family_id": job.family_id,
                    "schema_order": job.schema_order,
                    "vietnamese_name": job.vietnamese_name,
                }
            )
            continue
        topology_path, evaluation_path, schema_path = paths
        topology = _load_json(topology_path)
        evaluation = _load_json(evaluation_path)
        schema = _load_json(schema_path)
        compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
        compiled_family_id = compiled.get("family_id")
        if compiled_family_id is None and type(compiled.get("topology")) is dict:
            compiled_family_id = compiled["topology"].get("family_id")
        if compiled_family_id != job.family_id:
            raise RunGeminiJsonAllAccountingFamiliesV1Error(
                f"compiled family identity drifted at schema order {job.schema_order}"
            )
        format_version = evaluation.get("format_version")
        runner = job.runner
        if runner is None:
            if format_version in GENERIC_FORMATS:
                runner = "run_gemini_json_first_accounting_family_v1.py"
            else:
                runner = RUNNER_BY_FORMAT.get(format_version)
        runner_path = ROOT / "scripts/experiments" / str(runner)
        if runner is None or runner_path.is_symlink() or not runner_path.is_file():
            raise RunGeminiJsonAllAccountingFamiliesV1Error(
                f"no executable runner for family {job.family_id}"
            )
        compiled_jobs.append(
            {
                "evaluation_spec": str(evaluation_path.relative_to(ROOT)),
                "execution_kind": "ACCOUNTING_FAMILY_RUNNER",
                "family_id": job.family_id,
                "runner": str(runner_path.relative_to(ROOT)),
                "schema_binding_spec": str(schema_path.relative_to(ROOT)),
                "schema_order": job.schema_order,
                "topology_spec": str(topology_path.relative_to(ROOT)),
                "vietnamese_name": job.vietnamese_name,
            }
        )
    return compiled_jobs


def _plan() -> dict[str, Any]:
    jobs = _compiled_jobs()
    return {
        "execution_scope": {
            "document_count": EXPECTED_DOCUMENT_COUNT,
            "excluded_reuse_only_bank_codes": sorted(REUSE_ONLY_BANKS),
            "page_count": EXPECTED_PAGE_COUNT,
            "paid_bank_codes": sorted(PAID_BANKS),
            "period_start": "2025-Q1",
        },
        "family_count": len(jobs),
        "format_version": "GEMINI_JSON_ALL_ACCOUNTING_FAMILIES_PLAN_V1",
        "jobs": jobs,
    }


def _checked_corpus(path: Path) -> dict[str, Any]:
    index = validate_current_corpus_manifest_index_v1(_load_json(path))
    documents = index["documents"]
    banks = {document["relative_path"].split("/")[1] for document in documents}
    years = {document["relative_path"].split("/")[2] for document in documents}
    if (
        index["summary"]["document_count"] != EXPECTED_DOCUMENT_COUNT
        or index["summary"]["page_count"] != EXPECTED_PAGE_COUNT
        or banks != PAID_BANKS
        or banks & REUSE_ONLY_BANKS
        or not years
        or any(year not in {"2025", "2026"} for year in years)
    ):
        raise RunGeminiJsonAllAccountingFamiliesV1Error(
            "corpus is not the exact 19-bank 2025-current paid frontier"
        )
    return index


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan")
    plan.add_argument("--output", type=Path)
    run = commands.add_parser("run")
    run.add_argument("--corpus-index", type=Path, required=True)
    run.add_argument("--artifact-root", type=Path, required=True)
    run.add_argument("--results-database", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--family", action="append", default=[])
    run.add_argument("--run-kind", choices=("EXPERIMENTAL",), default="EXPERIMENTAL")
    return parser


def _write_or_verify(path: Path, payload: bytes) -> None:
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
            raise RunGeminiJsonAllAccountingFamiliesV1Error(
                f"write-once all-family artifact drifted: {path}"
            )
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _selected_jobs(plan: dict[str, Any], selectors: list[str]) -> list[dict[str, Any]]:
    if not selectors:
        return list(plan["jobs"])
    wanted = set(selectors)
    selected = [
        job
        for job in plan["jobs"]
        if job["family_id"] in wanted or str(job["schema_order"]) in wanted
    ]
    if len(selected) != len(wanted):
        found = {job["family_id"] for job in selected} | {
            str(job["schema_order"]) for job in selected
        }
        missing = sorted(wanted - found)
        raise RunGeminiJsonAllAccountingFamiliesV1Error(
            f"unknown or duplicate family selector: {missing}"
        )
    return selected


def _child_receipt(
    completed_process: subprocess.CompletedProcess[str],
    *,
    job: dict[str, Any],
    output: Path,
    results_database: Path,
    run_kind: str,
) -> dict[str, Any]:
    if completed_process.returncode != 0 or output.is_symlink() or not output.is_file():
        raise RunGeminiJsonAllAccountingFamiliesV1Error(
            f"family runner failed at schema order {job['schema_order']}"
        )
    lines = [line for line in completed_process.stdout.splitlines() if line.strip()]
    try:
        receipt = json.loads(lines[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise RunGeminiJsonAllAccountingFamiliesV1Error(
            f"family runner returned no valid receipt at schema order {job['schema_order']}"
        ) from exc
    if (
        type(receipt) is not dict
        or receipt.get("disposition") != "SUCCEEDED"
        or receipt.get("run_kind") != run_kind
        or receipt.get("output") != str(output)
        or receipt.get("results_database") != str(results_database)
        or type(receipt.get("family_run_id")) is not str
        or not receipt["family_run_id"].startswith("gjfafstorev1:run:")
        or type(receipt.get("sweep_id")) is not str
    ):
        raise RunGeminiJsonAllAccountingFamiliesV1Error(
            f"family runner receipt drifted at schema order {job['schema_order']}"
        )
    stored = load_gemini_accounting_family_sweep_v1(results_database, receipt["family_run_id"])
    materialized = _load_json(output)
    if (
        stored != materialized
        or stored.get("sweep_id") != receipt["sweep_id"]
        or stored.get("family_id") != job["family_id"]
        or stored.get("metrics") != receipt.get("metrics")
    ):
        raise RunGeminiJsonAllAccountingFamiliesV1Error(
            f"stored family sweep drifted at schema order {job['schema_order']}"
        )
    return receipt


def _run(args: argparse.Namespace) -> dict[str, Any]:
    index = _checked_corpus(args.corpus_index)
    plan = _plan()
    selected = _selected_jobs(plan, args.family)
    completed = []
    deferred = []
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for job in selected:
        if job["execution_kind"] != "ACCOUNTING_FAMILY_RUNNER":
            deferred.append(
                {
                    "family_id": job["family_id"],
                    "reason": "DERIVED_VISIBLE_STATEMENT_LINE_REQUIRES_DEDICATED_PROJECTION",
                    "schema_order": job["schema_order"],
                }
            )
            continue
        output = args.output_dir / f"{job['schema_order']:02d}-{job['family_id'].lower()}.json"
        command = [
            sys.executable,
            str(ROOT / job["runner"]),
            "--corpus-index",
            str(args.corpus_index),
            "--artifact-root",
            str(args.artifact_root),
            "--topology-spec",
            str(ROOT / job["topology_spec"]),
            "--evaluation-spec",
            str(ROOT / job["evaluation_spec"]),
            "--schema-binding-spec",
            str(ROOT / job["schema_binding_spec"]),
            "--results-database",
            str(args.results_database),
            "--run-kind",
            args.run_kind,
            "--output",
            str(output),
        ]
        completed_process = subprocess.run(
            command, cwd=ROOT, check=False, capture_output=True, text=True
        )
        child = _child_receipt(
            completed_process,
            job=job,
            output=output,
            results_database=args.results_database,
            run_kind=args.run_kind,
        )
        completed.append(
            {
                "family_id": job["family_id"],
                "family_run_id": child["family_run_id"],
                "metrics": child["metrics"],
                "output": str(output),
                "schema_order": job["schema_order"],
                "sweep_id": child["sweep_id"],
            }
        )
    receipt = {
        "completed": completed,
        "corpus_manifest_index_id": index["corpus_manifest_index_id"],
        "deferred": deferred,
        "disposition": "NEEDS_DERIVED_PROJECTION" if deferred else "SUCCEEDED",
        "format_version": "GEMINI_JSON_ALL_ACCOUNTING_FAMILIES_RUN_RECEIPT_V1",
        "selected_family_count": len(selected),
    }
    _write_or_verify(args.output_dir / "run-receipt.json", canonical_json_bytes_v1(receipt) + b"\n")
    return receipt


def main() -> int:
    args = _parser().parse_args()
    if args.command == "plan":
        payload = canonical_json_bytes_v1(_plan()) + b"\n"
        if args.output is None:
            sys.stdout.buffer.write(payload)
        else:
            _write_or_verify(args.output, payload)
        return 0
    result = _run(args)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["disposition"] == "SUCCEEDED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
