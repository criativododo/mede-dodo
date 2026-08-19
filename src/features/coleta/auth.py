"""Helper de segredos (ISSUE-002): st.secrets com fallback para os.environ/.env."""

import os

import streamlit as st

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def get_secret(key_name: str, default: str | None = None) -> str | None:
    """Lê `key_name` de `st.secrets`; se ausente ou indisponível (sem
    secrets.toml configurado), cai para `os.environ` (populado também a
    partir de `.env` via python-dotenv)."""
    try:
        if key_name in st.secrets:
            return st.secrets[key_name]
    except Exception:
        pass
    return os.environ.get(key_name, default)
