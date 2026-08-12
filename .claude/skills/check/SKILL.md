---
name: check
description: Executa e registra as verificações reais configuradas para a sessão atual deste projeto. Use somente por invocação explícita.
argument-hint: [escopo configurado em config.json, se houver]
disable-model-invocation: true
allowed-tools: Bash(node .claude/session-memory/bin/session-memory.mjs:*) Read
---

Sem argumento, execute toda a matriz. Com argumento, use exatamente um dos escopos configurados em `checks` no `config.json` deste projeto. O resultado não persiste em runtime.

```bash
node .claude/session-memory/bin/session-memory.mjs check --scope "$ARGUMENTS"
```

Se não houver argumento, remova `--scope`. Registre e apresente resultados reais, inclusive falhas e verificações não configuradas. Não corrija código nem repita a verificação automaticamente.
