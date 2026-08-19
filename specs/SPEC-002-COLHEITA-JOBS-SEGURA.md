# SPEC-002 — Jobs de coleta segura e longa

## Objetivo

A coleta do métricaDODÔ pode durar muitos minutos. A interface não deve esperar uma requisição síncrona nem mascarar o estado da sessão do Instagram. O sistema deve persistir o job, o progresso e os dados parciais no SQLite e permitir que a View seja recarregada sem perder o trabalho.

## Regras de segurança

A coleta usa concorrência máxima de um job por sessão e pacing conservador configurável. Cache válido deve ser consultado antes de qualquer requisição externa. O worker pode aplicar backoff limitado e jitter operacional, mas nunca tenta simular comportamento humano para burlar proteção, trocar endpoint para contornar bloqueio ou repetir uma chamada indefinidamente.

Ao detectar checkpoint, challenge, `403`, `429`, `LoginRequiredException`, `TooManyRequestsException` ou `SafeStop`, o worker deve salvar o progresso parcial, mudar o job para `falha_sessao`, registrar uma causa legível e encerrar. A UI deve exibir o estado e a ação recomendada, sem declarar auditoria concluída.

## Modelo de job

A tabela `audit_jobs` em `data/cache.db` guarda `job_id`, username normalizado, marca, status, etapa, progresso atual/total, mensagem, snapshots parciais de perfil/posts/comentários, resultado, erro, timestamps e heartbeat do worker. Os estados mínimos são `queued`, `running`, `coleta_concluida`, `analisando`, `concluido`, `falha_sessao` e `falha`.

## Contrato da View

`src/app.py` é View pura: o botão cria um job através de `features/coleta/database.py`, inicia um único worker e retorna imediatamente. Enquanto houver job ativo, a View consulta o SQLite, mostra progresso e usa `st.rerun` com intervalo curto. Nenhum SQL, HTTP, Instaloader ou escrita direta em disco fica em `src/app.py`.

## Análise e conclusão

A análise de demografia, IA e métricas só pode iniciar depois de a coleta terminar com status `coleta_concluida`. Falhas de sessão nunca alimentam um relatório real com dados incompletos como se estivesse concluído. Dados parciais permanecem disponíveis para diagnóstico e retomada explícita, sem apagar o cache existente.

## Testes mínimos

A suíte deve cobrir criação/consulta/atualização de job, progresso parcial, concorrência, retomada visual após rerun, conclusão pós-coleta, erro de sessão, `403`, `429`, checkpoint, preservação do relatório anterior e ausência de chamadas de análise antes da coleta concluída.
