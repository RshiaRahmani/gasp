#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
source .venv/bin/activate
echo "Starting SHARP 3DGS Studio at http://127.0.0.1:8765"
open "http://127.0.0.1:8765" || true
exec uvicorn app:app --host 127.0.0.1 --port 8765
