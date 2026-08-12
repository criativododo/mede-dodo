# DUMMY.md — Safety Shield e Restrições Negativas

## O que NÃO fazer sob pena de quebra:

1. **NUNCA realizar requisições síncronas de longa duração na thread principal da UI:** A raspagem e chamadas de API devem rodar de forma assíncrona/background com `st.session_state` no Streamlit para não travar a interface.
2. **NUNCA enviar comentários não-filtrados para o Gemini:** Todo comentário deve passar pelo filtro de Regex/Python local. Enviar emojis ou comentários rasos para a LLM é considerado falha grave de consumo de cota.
3. **NUNCA fazer scraping sem throttling/delays:** É proibido fazer requisições em loop contínuo sem pausas aleatórias (jitter de 2s a 5s).
4. **NUNCA utilizar bibliotecas ou SDKs pagos:** Todas as soluções devem ser 100% integradas via ferramentas e bases gratuitas/open-source.
5. **NUNCA apagar o cache local sem autorização do usuário:** As análises salvas no SQLite `data/cache.db` devem ser mantidas para consulta offline.

## Verificação (2026-08-12)
Regras reconferidas após a integração dos conectores reais (`instaloader_fetch_fn` e
`RealGeminiClient`) ao pipeline de `app.py`:
- Regra 1: `app.py` continua rodando o pipeline em `threading.Thread` de background; a UI
  só faz polling/rerun (`time.sleep(0.3)` + `st.rerun()`), nunca `thread.join()` bloqueante.
  A troca do `fetch_fn` de demonstração pelo `scraper.instaloader_fetch_fn` real não mudou
  essa arquitetura — a chamada de rede real também roda dentro da mesma thread de fundo.
- Regra 2: `app.py` continua só enviando `qualified_comments` (pós
  `filters.is_shallow_comment`) para `gemini_analyzer.analyze_comments`, agora com o
  `RealGeminiClient` real como `client` quando `GEMINI_API_KEY` está configurada — nenhum
  comentário raso chega a ser formatado no prompt do Gemini.
- Regra 3: `scraper.throttle` (jitter 2-5s) roda antes de qualquer `fetch_fn` real; em Modo
  Demonstração o throttle é substituído por um no-op (`lambda: None`), correto, pois não há
  requisição de rede a proteger nesse modo.
- Regra 4: nenhuma dependência paga em `requirements.txt` (`streamlit`, `fpdf2`, `pytest`,
  `instaloader`, `google-generativeai` — todas open-source/SDK gratuito). O uso do
  `google-generativeai` depende de uma `GEMINI_API_KEY` do plano gratuito do Google AI
  Studio, nunca de um plano pago.
- Regra 5: nenhuma rotina do projeto apaga `data/cache.db`; não há função de limpeza de
  cache implementada. O novo fallback de `scraper.scrape_profile` (cache sem filtro de
  janela quando a coleta real falha) só *lê* o cache, nunca apaga ou sobrescreve dados.
