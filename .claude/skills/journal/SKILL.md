---
name: journal
description: Lista, pesquisa ou abre journals históricos deste projeto por data, sprint, fase ou palavra-chave. Use somente por invocação explícita.
argument-hint: [--date AAAA-MM-DD] [--sprint nome] [--phase nome] [--search texto] [--open arquivo]
disable-model-invocation: true
allowed-tools: Bash(node .claude/session-memory/bin/session-memory.mjs:*) Read
---

Passe os filtros informados pelo usuário diretamente ao CLI, sem inventar filtros:

```bash
node .claude/session-memory/bin/session-memory.mjs journal $ARGUMENTS
```

Sem argumentos, liste os journals. Com `--open`, apresente o conteúdo do journal encontrado. Não resuma um arquivo que não foi retornado pelo comando.
