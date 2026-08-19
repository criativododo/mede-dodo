#!/usr/bin/env bash
set -Eeuo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
exec .venv/bin/python -m streamlit run app.py
