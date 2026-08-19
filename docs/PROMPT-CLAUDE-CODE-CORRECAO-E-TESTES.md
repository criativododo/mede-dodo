# Prompt para o Claude Code — correção final, testes e atalho

Trabalhe até concluir. O app ainda falha no uso real. A captura mostra `http://localhost:8501`, perfil `https://www.instagram.com/gardeniacavalcanti` e a mensagem `A coleta foi pausada para proteger a sessão. Dados parciais foram salvos...`. Descubra a causa no código, corrija e prove o resultado.

## Código correto

Antes de editar, leia `DUMMY.md`, `CLAUDE.md`, `README.md` e `PROGRESS.md`. Verifique branch, worktrees, `ps`, `lsof` e a porta 8501. Não confunda a `main` reorganizada com a versão que contém `app.py` na raiz, `src/scraper.py` e 370 testes. Trabalhe no checkout realmente servido. Não faça reset, checkout destrutivo, merge cego, descarte de alterações nem varra `legado/`.

## Correção

Reproduza pela UI e por testes com `https://www.instagram.com/gardeniacavalcanti`. Normalize qualquer URL, `@handle` ou username uma única vez antes de cache, Instaloader, thread, logs, erro, relatório e exportação. A UI deve mostrar o username normalizado, nunca a URL inteira, `perfilexemplo` ou estado de tentativa anterior. Atualize por tentativa `username_tentativa`, `erro_categoria`, `erro` e relatório anterior.

Diferencie `login_required`, `checkpoint/challenge`, `rate_limit`, `connection_error`, `bad_request`, `schema_error`, `profile_not_found` e `instagram_generic_block`. Em SafeStop/403/429/challenge, preserve a proteção: sem bypass, endpoint alternativo evasivo, loop ou mudança de pacing. Mostre causa, perfil correto, ação recomendada e que o relatório não foi concluído. Nunca declare sucesso com dados não coletados.

## Validação obrigatória

Execute no checkout correto e corrija falhas: `PYTHONPATH=. .venv/bin/pytest -q`; `bash -n iniciar_app.command`; compilação/import do app; smoke test Streamlit/AppTest; `git diff --check`. Adicione regressões para URL/handle, mensagem, estado stale, relatório anterior e SafeStop se faltarem.

Faça no máximo três smoke tests reais, um por vez, com perfis públicos ainda não usados, cache e throttling de 2–5 s. Pare no primeiro SafeStop, checkpoint, 403 ou 429; não burle o Instagram. Registre perfil, horário, resultado, categoria e evidência. Não exponha nem substitua `~/.config/instaloader/session-elafashiomkt`.

## Atalho no projeto

Corrija ou substitua `/Users/danielperrut/0. PROJETO/mede-dodo/iniciar_app.command`. Se o código correto estiver em worktree, salve o atalho no diretório desse checkout e informe a origem. Ele deve resolver seu diretório via `$0`, usar `.venv/bin/python -m streamlit run` com o entrypoint correto, detectar `.venv` ausente com mensagem clara, iniciar o servidor, aguardar `/_stcore/health` e abrir `http://localhost:8501` no Chrome. Crie, se necessário, `MétricaDODÔ.command` dentro do projeto. Teste com `bash -n` e execute; não deixe apenas cópia no Desktop.

## Conclusão

O erro deve estar reproduzido e explicado; normalização e UI devem estar corretas; testes, compilação, import, health check e regressões devem passar; SafeStop deve continuar seguro; smoke tests devem ter evidência ou justificativa de parada; o atalho deve abrir a instância correta. Atualize `docs/VALIDACAO-2026-08-19.md` com comandos, resultados, limites e checkout. Informe arquivos, porta/entrypoint e bloqueios externos. Não termine com “parece funcionar”.
