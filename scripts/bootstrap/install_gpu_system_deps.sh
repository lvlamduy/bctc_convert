#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "run this script as root; it installs Ubuntu runtime libraries" >&2
  exit 2
fi

apt-get update
apt-get install -y --no-install-recommends libgl1 libglib2.0-0
dpkg-query -W -f='${Package}\t${Version}\n' libgl1 libglib2.0-0
