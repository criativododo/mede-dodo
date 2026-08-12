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
- **Pendência (à época)**: a chamada real a `Profile.from_username` contra o Instagram (ex.
  `@silviabraz`, `@caroline_tanaka`) não havia sido disparada naquela sessão — evitado
  deliberadamente por ser uma ação de rede contra o Instagram usando a sessão real e
  autenticada do usuário (`criativododo`), fora do escopo de uma correção de código
  automatizada sem supervisão ao vivo.

## Validação real (2026-08-12, autorizada explicitamente pelo usuário) — resultado parcial
Executada por pedido explícito do usuário: `scraper.scrape_profile("silviabraz", ...)` e
`scraper.scrape_profile("caroline_tanaka", ...)`, ambos com `cookies=None` (autodetecção),
`window_days=90`, `fetch_fn=scraper.instaloader_fetch_fn`, `throttle_fn=scraper.throttle`
(script `validate_scraper.py`, fora do repositório).

**Confirmado funcionando (os dois bugs desta issue estão corrigidos):**
- Sidebar do Streamlit, sem nenhum mock, mostrou corretamente `"Sessão ativa: criativododo"`.
- `scraper.detect_available_session_username()` encontrou o arquivo real
  `~/.config/instaloader/session-criativododo` (390 bytes) nesta máquina.
- A autodetecção de sessão em `instaloader_fetch_fn` carregou e usou a sessão correta (a
  requisição real saiu autenticada como `criativododo`, não anônima, e não houve nenhum erro
  de "identidade trocada"/sessão não encontrada).

**Descoberta nova, que revisa a hipótese original sobre o Erro HTTP 400:**
Lendo o código-fonte da lib instalada (`.venv/lib/python3.14/site-packages/instaloader/
structures.py`, `Profile.from_username`, linhas ~993-1017), o comentário do próprio mantenedor
diz: *"Resolve the profile through the web_profile_info endpoint, which works both anonymously
and when logged in [...] The GraphQL fbsearch query previously used here started responding
with HTTP 400."* — ou seja, na versão `4.15.3` (a mais recente publicada no PyPI hoje),
`Profile.from_username` usa **sempre** `api/v1/users/web_profile_info/`, autenticado ou não;
não existe nesta versão uma rota GraphQL alternativa acionada por sessão logada (a hipótese
registrada anteriormente neste documento — "sessão autenticada usa GraphQL, mais estável" —
não se confirmou nesta versão da lib e foi corrigida aqui).

- `@silviabraz`: falhou com **exatamente** o erro original relatado pelo usuário: `400 Bad
  Request - "fail" status, message "Asset asset://laser.provider/
  ig_business_category_subvertical has been deleted. You cannot use this schema"`. Isso é
  um **bug atual no backend do próprio Instagram** dentro do endpoint `web_profile_info`
  (um campo de schema interno do Instagram foi removido do lado deles, quebrando a resposta
  para certas contas — aparentemente as que têm uma subcategoria de negócio configurada).
  Ocorreu de forma idêntica com sessão autenticada carregada corretamente, confirmando que
  não é um problema de autenticação/identidade — é externo ao nosso código e à correção
  desta sessão.
- `@caroline_tanaka`: **passou** pela etapa de perfil (sem 400 — nem toda conta business é
  afetada pelo bug de schema acima), mas falhou depois, ao buscar comentários de um post
  específico via `i.instagram.com/api/v1/media/<id>/comments/`, com uma resposta genérica
  `"fail" — "We're sorry, but something went wrong. Please try again."`. Padrão típico de
  limitação/anti-automação no endpoint de comentários do app iPhone; não reproduzido o
  suficiente nesta sessão (uma única tentativa) para afirmar se é permanente ou transitório.

**Conclusão**: os dois bugs de sessão/identidade que motivaram esta issue estão corrigidos e
confirmados em ambiente real. O "Erro HTTP 400" mencionado no pedido original tem uma causa
mais específica do que "falta de autenticação" — é um bug atual do backend do Instagram no
endpoint `web_profile_info`, fora do controle deste código e sem contorno disponível na API
pública do Instaloader `4.15.3` (`Profile.from_username` não oferece endpoint alternativo).
Não convém tentar novos contornos (ex. reimplementar a resolução de perfil via GraphQL bruto,
contornando a lib) sem alinhamento explícito do usuário, dado o risco de manutenção
(Instagram já quebrou a rota GraphQL anterior, motivando a lib a migrar para
`web_profile_info` em primeiro lugar) e de tráfego adicional contra a conta real do usuário.
- **Pendência real, atualizada**: acompanhar se o bug de schema do Instagram
  (`ig_business_category_subvertical`) se resolve nas próximas versões/dias, e decidir se
  vale a pena investir em um contorno próprio para o endpoint de comentários (possível
  rate-limit) e/ou para perfis afetados pelo bug de schema.

## Tratamento de erro resiliente (2026-08-12)
Como o bug de schema do Instagram e a instabilidade do endpoint de comentários não têm
contorno no lado do cliente, `src/scraper.py` foi endurecido para que essas falhas reais
(observadas ao vivo acima) não derrubem a coleta inteira nem a interface:

1. **`Profile.from_username()`** (`instaloader_fetch_fn`) agora está em um `try/except` com
   dois blocos: um específico para `instaloader.exceptions.ConnectionException` (a família de
   exceção realmente levantada pelo Instaloader para falhas HTTP/JSON — a versão instalada
   não expõe uma classe `HTTPException`) e um genérico para `Exception`. Quando a mensagem
   bate com a assinatura do bug de schema removido (`"has been deleted. you cannot use this
   schema"`), registra um log de `ERROR` identificando o perfil afetado e levanta
   `ScraperUnavailableError` com uma mensagem clara de que é um bug do backend do Instagram
   (não uma falha de sessão local) — evita a mensagem genérica e enganosa de "verifique o
   arquivo de sessão". Outros erros de conexão continuam propagando sem reclassificação, para
   que `scrape_profile()` aplique o fallback de cache já existente.
2. **Busca de comentários** (`_fetch_real_comments`) também ganhou dois blocos de exceção
   (`ConnectionException` e `Exception` genérica) ao redor da iteração de
   `post.get_comments()`. Se a busca falhar no meio da paginação de UM post (reproduzido ao
   vivo em `@caroline_tanaka`), os comentários já obtidos até ali são mantidos (dados
   parciais), um log de `WARNING` identifica o post e o perfil afetados, e a função retorna
   normalmente — o post problemático fica com comentários parciais/vazios, mas o loop de
   `instaloader_fetch_fn` sobre os demais posts do perfil continua normalmente (não aborta a
   coleta inteira por causa de um post).
3. Validado via TDD: 4 testes novos em `tests/test_scraper.py` — reprodução exata do erro
   400 de schema removido (assert que vira `ScraperUnavailableError` com mensagem clara,
   sem sugerir problema de sessão), regressão confirmando que outros erros de conexão
   continuam propagando sem reclassificação, e dois testes provando que uma falha na busca
   de comentários de um post não interrompe a coleta dos demais posts do mesmo perfil.
   Suíte completa: 131 → 135 testes, sempre verde.
