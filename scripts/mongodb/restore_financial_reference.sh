#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
archive_path="${1:-${project_root}/financial_20_02_2022.gz}"
restore_mode="${2:-templates-only}"
restore_bin="${project_root}/.tools/mongodb-database-tools-ubuntu2204-x86_64-100.14.0/bin/mongorestore"
restore_uri="mongodb://127.0.0.1:27018"

namespace_arguments=()
if [[ "${restore_mode}" == "templates-only" ]]; then
    namespace_arguments+=(
        --nsInclude=financial_20_02_2022.financial_report_templates
    )
elif [[ "${restore_mode}" == "financial-history" ]]; then
    namespace_arguments+=(
        --nsInclude=financial_20_02_2022.financial_report_templates
        --nsInclude=financial_20_02_2022.report_yearly
        --nsInclude=financial_20_02_2022.report_quaterly
    )
elif [[ "${restore_mode}" == "bank-weak-reference" ]]; then
    namespace_arguments+=(
        --nsInclude=financial_20_02_2022.data_chart
    )
else
    echo "restore mode must be templates-only, financial-history, or bank-weak-reference" >&2
    exit 2
fi

"${restore_bin}" \
    --uri="${restore_uri}" \
    --gzip \
    --archive="${archive_path}" \
    --stopOnError \
    "${namespace_arguments[@]}"
