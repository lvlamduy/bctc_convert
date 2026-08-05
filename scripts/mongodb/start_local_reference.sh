#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
server_version="7.0.34"
server_bin="${project_root}/.tools/mongodb-linux-x86_64-ubuntu2204-${server_version}/bin/mongod"
database_path="${project_root}/.local-mongodb/data"
log_path="${project_root}/.local-mongodb/log/mongod.log"

mkdir -p "${database_path}" "$(dirname "${log_path}")"
"${server_bin}" \
    --dbpath "${database_path}" \
    --bind_ip 127.0.0.1 \
    --port 27018 \
    --logpath "${log_path}" \
    --fork \
    --setParameter diagnosticDataCollectionEnabled=false

echo "MONGODB_URI=mongodb://127.0.0.1:27018"
