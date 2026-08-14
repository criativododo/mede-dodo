#!/usr/bin/env bash
set -Eeuo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

if [ ! -d ".venv" ]; then
    echo "Criando ambiente virtual (.venv)..."
    python3 -m venv .venv
    echo "Instalando dependências..."
    .venv/bin/python -m pip install -r requirements.txt -q
fi

echo "Iniciando o métricaDODÔ no navegador..."
exec .venv/bin/streamlit run app.py
