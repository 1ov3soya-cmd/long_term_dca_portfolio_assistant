#!/usr/bin/env bash
set -euo pipefail

END_DATE="${1:-2025-12-31}"
BASE_PATH="${2:-/}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"
python -m src.main build-frontend-snapshot --end-date "${END_DATE}"

cd "${REPO_ROOT}/frontend"
npm install
VITE_BASE_PATH="${BASE_PATH}" npm run build
