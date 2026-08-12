# DUMMY.md — Safety Shield e Restrições Negativas

## O que NÃO fazer sob pena de quebra:

1. **NUNCA realizar requisições síncronas de longa duração na thread principal da UI:** A raspagem e chamadas de API devem rodar de forma assíncrona/background com `st.session_state` no Streamlit para não travar a interface.
2. **NUNCA enviar comentários não-filtrados para o Gemini:** Todo comentário deve passar pelo filtro de Regex/Python local. Enviar emojis ou comentários rasos para a LLM é considerado falha grave de consumo de cota.
3. **NUNCA fazer scraping sem throttling/delays:** É proibido fazer requisições em loop contínuo sem pausas aleatórias (jitter de 2s a 5s).
4. **NUNCA utilizar bibliotecas ou SDKs pagos:** Todas as soluções devem ser 100% integradas via ferramentas e bases gratuitas/open-source.
5. **NUNCA apagar o cache local sem autorização do usuário:** As análises salvas no SQLite `data/cache.db` devem ser mantidas para consulta offline.

## Verificação (2026-08-12)
Regras conferidas contra a implementação atual:
- Regra 1: `app.py` roda o pipeline em `threading.Thread` de background; a UI só faz polling/rerun, nunca `thread.join()` bloqueante.
- Regra 2: `app.py` só envia `qualified_comments` (pós `filters.is_shallow_comment`) para `gemini_analyzer.analyze_comments`.
- Regra 3: `scraper.throttle` (jitter 2-5s) roda antes de qualquer `fetch_fn`; nenhum código faz raspagem em loop sem essa chamada.
- Regra 4: nenhuma dependência paga em `requirements.txt` (`streamlit`, `fpdf2`, `pytest` — todas open-source).
- Regra 5: nenhuma rotina do projeto apaga `data/cache.db`; não há função de limpeza de cache implementada.
