#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
server_bin="${project_root}/.tools/mongodb-linux-x86_64-ubuntu2204-7.0.34/bin/mongod"
database_path="${project_root}/.local-mongodb/data"
"${server_bin}" --shutdown --dbpath "${database_path}"
