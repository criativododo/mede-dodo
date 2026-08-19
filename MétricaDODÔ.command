#!/bin/bash
# Atalho raiz do métricaDODÔ.
# Encaminha o duplo clique para o worktree operacional do Sprint 003,
# sem executar o código da main.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
WORKTREE="$ROOT/.claude/worktrees/mede-dodo-sprint003"
LAUNCHER="$WORKTREE/MétricaDODÔ.command"

if [ ! -x "$LAUNCHER" ]; then
    echo "métricaDODÔ: launcher do worktree não encontrado em: $LAUNCHER"
    echo "Pressione Enter para fechar esta janela."
    read -r _
    exit 1
fi

exec "$LAUNCHER" "$@"
