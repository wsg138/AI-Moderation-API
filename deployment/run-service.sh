#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${AI_MOD_VENV_PATH:-${ROOT_DIR}/.venv}"
BIND_HOST="${AI_MOD_BIND_HOST:-127.0.0.1}"
PORT="${AI_MOD_PORT:-8787}"
ALLOW_NONLOCAL="${AI_MOD_ALLOW_NONLOCAL_BIND:-false}"

case "${BIND_HOST}" in
  127.0.0.1|localhost|::1)
    ;;
  *)
    if [[ "${ALLOW_NONLOCAL}" != "true" ]]; then
      echo "[ai-moderation] Refusing non-local bind ${BIND_HOST}; set AI_MOD_ALLOW_NONLOCAL_BIND=true only for an approved private network." >&2
      exit 64
    fi
    ;;
esac

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  echo "[ai-moderation] Runtime venv is missing. Run deployment/install-runtime.sh first." >&2
  exit 66
fi

export AI_MOD_DATABASE_PATH="${AI_MOD_DATABASE_PATH:-${ROOT_DIR}/runtime-data/moderation.sqlite3}"
export PYTHONUNBUFFERED=1

cd "${ROOT_DIR}"
exec "${VENV_DIR}/bin/python" -m uvicorn moderation_api.app:app   --host "${BIND_HOST}"   --port "${PORT}"   --no-access-log
