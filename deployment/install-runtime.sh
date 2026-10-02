#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
VENV_DIR="${AI_MOD_VENV_PATH:-${ROOT_DIR}/.venv}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "[ai-moderation] Python 3.12 executable not found: ${PYTHON_BIN}" >&2
  exit 65
fi

"${PYTHON_BIN}" -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/python" -m pip install --disable-pip-version-check   -r "${ROOT_DIR}/deployment/requirements-runtime.lock"
"${VENV_DIR}/bin/python" -m pip install --disable-pip-version-check   --no-build-isolation --no-deps "${ROOT_DIR}"

mkdir -p "${ROOT_DIR}/runtime-data"
echo "[ai-moderation] Runtime installed in ${VENV_DIR}."
