# ISSUE-0001: Módulo de Coleta Local e Cache SQLite

## Objetivo
Implementar a camada de raspagem de dados públicos do Instagram com suporte a cookies de sessão, throttling dinâmico e persistência em banco SQLite local (`data/cache.db`).

## Tarefas de Implementação
1. **Banco de Dados Local (`src/database.py`):**
   - Criar o banco SQLite em `data/cache.db`.
   - Estruturar as tabelas `profiles` e `posts_cache` para armazenar username, payload bruto em JSON, estatísticas básicas (curtidas, comentários) e timestamp da coleta.
   - Criar função `get_cached_data(username, window_days)` para checar se há dados salvos dentro da janela temporal antes de disparar nova raspagem.

2. **Scraper Local (`src/scraper.py`):**
   - Implementar a função de raspagem com suporte a carregamento de cookies de sessão do navegador.
   - Configurar o throttling com delays aleatórios entre requisições (2s a 5s com jitter) para evitar bloqueios da plataforma.
   - Salvar o resultado da raspagem na tabela SQLite.

3. **Validação e Testes (`tests/test_scraper.py`):**
   - Criar um script de teste simples para validar a gravação e a leitura dos dados em cache.

## Critérios de Aceite (Definition of Done)
- [x] Banco de dados SQLite inicializado automaticamente em `data/cache.db`.
- [x] Leitura e escrita do cache funcionando corretamente.
- [ ] Raspagem efetuada com delays de segurança respeitados. **Parcial**: `throttle()` (jitter 2-5s) é chamado antes de qualquer coleta em `scrape_profile`, mas a implementação real de rede ao Instagram (`fetch_fn`) ainda não existe — ver Notas de Implementação.
- [x] Script de teste executado com sucesso (`tests/test_scraper.py`, 6/6 via pytest).

## Notas de Implementação
- A implementação real de chamada de rede ao Instagram (`fetch_fn`) é injetada por parâmetro em `scrape_profile`, mantendo `src/scraper.py` testável sem depender de rede/sessão real. A biblioteca/estratégia concreta de raspagem (ex: cookies de sessão do navegador) fica como ponto em aberto para uma issue de integração subsequente — este ISSUE-0001 entrega a camada de cache, throttling e orquestração.
- Ambiente: venv local em `.venv/` (Python do Homebrew é "externally managed", não aceita `pip install` direto) com `pytest` instalado. Rodar testes com `.venv/bin/python -m pytest tests/`.

## Reparo (2026-08-12) — Sessão automática e Erro HTTP 400 em perfis business/creator
Investigação via pesquisa na documentação/issues oficiais do Instaloader (não havia
disponível um MCP de busca geral neste ambiente — só um MCP de docs do próprio produto
Perplexity, escopo diferente do pedido; a pesquisa foi feita via WebSearch) confirmou dois
bugs reais em `instaloader_fetch_fn` (`src/scraper.py`), ambos coerentes com a causa raiz
documentada publicamente para Erro HTTP 400 em perfis business/creator do Instaloader:
requisições anônimas (sem sessão autenticada) caem no endpoint público `web_profile_info`,
que é instável e retorna 400 para contas business/creator; contas autenticadas usam a rota
GraphQL, mais estável.

1. **Sessão nunca era autodetectada**: sem `INSTAGRAM_SESSION_FILE` definida no ambiente,
   `instaloader_fetch_fn` seguia 100% anônimo, mesmo havendo um arquivo de sessão salvo em
   `~/.config/instaloader/session-<usuario>`. Corrigido com `load_any_available_session(L)`
   (varre `SESSION_DIR` e carrega o primeiro arquivo `session-*` que funcionar) chamada
   automaticamente quando `cookies` não é fornecido.
2. **Identidade da sessão trocada pelo perfil-alvo**: quando `cookies` (caminho do arquivo)
   era fornecido, o código chamava `load_session_from_file(username=<perfil analisado>,
   filename=cookies)` — usando o username do perfil sendo AUDITADO (ex.: `silviabraz`) como
   dono da sessão, em vez do dono real dos cookies (ex.: `criativododo`). Corrigido
   derivando o username correto do próprio nome do arquivo (`session-<usuario>`) via
   `_session_username_from_path`.
3. `app.py` ganhou feedback de sessão na sidebar (`_render_session_status_sidebar`, via
   `scraper.detect_available_session_username`) — "Sessão ativa: <usuario>" ou aviso
   explícito quando nenhum arquivo de sessão é encontrado.
4. `instaloader` estava ausente de `requirements.txt` apesar de importado em
   `src/scraper.py` (drift real de dependência, encontrado ao recriar o venv do zero nesta
   sessão) — adicionado (`instaloader==4.15.3`, já a versão mais recente no PyPI).
5. Validado via TDD (7 testes novos em `tests/test_scraper.py`, 2 em `tests/test_app.py`,
   todos com Instaloader/contexto simulados, sem rede real) e por uma checagem real (não
   mockada) de que `scraper.detect_available_session_username()` encontra de fato o arquivo
   `~/.config/instaloader/session-criativododo` presente nesta máquina — confirmando que a
   autodetecção funciona no ambiente real.
- **Pendência explícita**: a chamada real a `Profile.from_username` contra o Instagram (ex.
  `@silviabraz`, `@caroline_tanaka`) não foi disparada nesta sessão — evitado
  deliberadamente por ser uma ação de rede contra o Instagram usando a sessão real e
  autenticada do usuário (`criativododo`), fora do escopo de uma correção de código
  automatizada sem supervisão ao vivo. Recomenda-se validar rodando
  `.venv/bin/python -m streamlit run app.py` e analisando esses perfis manualmente.
