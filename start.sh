#!/usr/bin/env bash
# One command for a local demo without Docker. Creates a venv so PEP 668 Pythons work.
set -euo pipefail
cd "$(dirname "$0")"

python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt -r requirements-dev.txt

if [[ ! -d frontend/node_modules ]]; then
  npm install --prefix frontend
fi
npm run build --prefix frontend

mkdir -p data
export DEMO_MODE="${DEMO_MODE:-1}"
exec .venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 43123
