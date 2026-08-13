#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

if [ ! -d ".venv" ]; then
    echo "Criando ambiente virtual (.venv)..."
    python3 -m venv .venv
fi

echo "Verificando dependências..."
.venv/bin/python -m pip install -r requirements.txt -q

echo "Iniciando o métricaDODÔ no navegador..."
.venv/bin/python -m streamlit run app.py
