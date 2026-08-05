#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
tools_root="${project_root}/.tools"
temporary_root="$(mktemp -d -t bctc-ai-mongodb-install-XXXXXX)"
trap 'rm -rf -- "${temporary_root}"' EXIT

tools_version="100.14.0"
tools_archive="mongodb-database-tools-ubuntu2204-x86_64-${tools_version}.tgz"
tools_url="https://fastdl.mongodb.org/tools/db/${tools_archive}"
tools_sha256="4104998bda784a0cb16fc2e06d9c21645516d72c4fb481c9b103f1e0a8458fc0"

server_version="7.0.34"
server_archive="mongodb-linux-x86_64-ubuntu2204-${server_version}.tgz"
server_url="https://fastdl.mongodb.org/linux/${server_archive}"
server_sha256="ca1ff8067a219b1dccb50a95305c7bba412c8a98787e4e51dbd3d2222817c8b8"

download_and_extract() {
    local url="$1"
    local archive_name="$2"
    local expected_sha256="$3"
    local destination="${temporary_root}/${archive_name}"
    curl -fL --retry 3 --output "${destination}" "${url}"
    local actual_sha256
    actual_sha256="$(sha256sum "${destination}" | awk '{print $1}')"
    if [[ "${actual_sha256}" != "${expected_sha256}" ]]; then
        echo "SHA-256 mismatch for ${archive_name}" >&2
        exit 1
    fi
    tar -xzf "${destination}" -C "${tools_root}"
}

mkdir -p "${tools_root}"
if [[ ! -x "${tools_root}/mongodb-database-tools-ubuntu2204-x86_64-${tools_version}/bin/mongorestore" ]]; then
    download_and_extract "${tools_url}" "${tools_archive}" "${tools_sha256}"
fi
if [[ ! -x "${tools_root}/mongodb-linux-x86_64-ubuntu2204-${server_version}/bin/mongod" ]]; then
    download_and_extract "${server_url}" "${server_archive}" "${server_sha256}"
fi

"${tools_root}/mongodb-database-tools-ubuntu2204-x86_64-${tools_version}/bin/mongorestore" --version
"${tools_root}/mongodb-linux-x86_64-ubuntu2204-${server_version}/bin/mongod" --version
