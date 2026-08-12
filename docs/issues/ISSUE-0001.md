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
