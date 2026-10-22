#!/usr/bin/env bash
# One command for a local demo without Docker.
set -euo pipefail
cd "$(dirname "$0")"

python3 -m pip install -q -r requirements.txt

if [[ ! -d frontend/node_modules ]]; then
  npm install --prefix frontend
fi
npm run build --prefix frontend

mkdir -p data
exec python3 -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 43123
