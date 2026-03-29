#!/usr/bin/env bash
set -euo pipefail

API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8000}"
SPACE_PORT="${PORT:-7860}"

export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"
export CMSVS_API_URL="${CMSVS_API_URL:-http://127.0.0.1:${API_PORT}}"
export API_RELOAD="${API_RELOAD:-false}"

python3 -m api.main &
api_pid=$!

python3 -m streamlit run streamlit_app/app.py \
  --server.address=0.0.0.0 \
  --server.port="${SPACE_PORT}" \
  --server.headless=true \
  --server.enableCORS=false \
  --server.enableXsrfProtection=false \
  --server.fileWatcherType=none \
  --browser.gatherUsageStats=false &
streamlit_pid=$!

cleanup() {
  kill "${api_pid}" "${streamlit_pid}" 2>/dev/null || true
  wait "${api_pid}" "${streamlit_pid}" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

wait -n "${api_pid}" "${streamlit_pid}"
