# ISSUE-0003: Módulo de Processamento Gemini em Lote (Batching)

## Objetivo
Enviar apenas os comentários já filtrados localmente (ISSUE-0002) para a API Gemini, em no máximo 2 requisições por perfil (RNF-03), com saída estruturada em JSON, e tratar graciosamente erros de limite de cota.

## Tarefas de Implementação
1. **Batching (`src/gemini_analyzer.py`):**
   - Receber a lista de comentários qualificados (saída de `filters.filter_comments`/`isolate_high_intent`).
   - Dividir em no máximo 2 lotes por perfil (RNF-03), cada um com até 100 comentários (RF-07: "1 a 2 requisições em lote").
   - Se o total de comentários exceder a capacidade de 2 lotes, o excedente é descartado (não gerado um 3º lote) e reportado explicitamente no resultado — nunca estourar a cota de chamadas.
2. **Schema de saída estruturada:** por comentário, `{"comentario": str, "intencao_compra": enum, "faixa_etaria_estimada": enum}`.
3. **Tratamento de erro de cota:** captura de `GeminiRateLimitError` por lote, com fallback gracioso (o lote falho é reportado como não analisado, sem derrubar os demais lotes nem lançar exceção para o chamador).
4. **Testes TDD (`tests/test_gemini_analyzer.py`)** com mock do cliente Gemini (sem chamada de rede real).

## Critérios de Aceite (Definition of Done)
- [x] `chunk_into_batches` nunca gera mais de 2 lotes por perfil e reporta comentários descartados por excesso.
- [x] `analyze_comments` percorre os lotes, agrega o resultado estruturado e nunca excede 2 chamadas ao cliente por execução.
- [x] Erro de cota (`GeminiRateLimitError`) em um lote não interrompe os demais nem propaga exceção — fica registrado no resultado (`failed_batches`).
- [x] Testes executados com sucesso via pytest, usando um cliente Gemini mockado (sem rede) — 10/10.

## Notas de Implementação e Desvio Consciente do Escopo
- **Índice de repetição/pods NÃO faz parte do schema por-comentário do Gemini.** A tarefa original pedia esse campo na saída estruturada, mas o índice de repetição de comentaristas (RF-08, "pods") é uma métrica estatística que depende de correlacionar o autor do comentário através de múltiplos posts — não é algo que um LLM possa inferir de forma confiável a partir de um lote de comentários isolados (ele não tem acesso a "quem comentou o quê em quais outros posts"). Pedir esse número ao Gemini seria abrir espaço para alucinação em vez de dado real.
  Decisão: o índice de pods fica para uma issue própria de cálculo **local** (contagem de usernames repetidos entre posts, usando os dados já persistidos por `src/database.py`/RF-08), fora do escopo desta issue. Documentado aqui para não passar a falsa impressão de que "schema completo" foi entregue conforme o pedido original.
- **Cliente Gemini real não integrado.** `analyze_comments`/`call_gemini_batch` recebem um `client` injetável (interface `client.generate_content(prompt) -> objeto com atributo .text`, mesmo formato do SDK `google-generativeai`), testado exclusivamente com mocks. A integração real com a API paga/gratuita do Gemini (autenticação, chamada de rede) fica para uma issue de integração subsequente — mesma lógica de "interface pronta, implementação de rede pendente" já usada no `fetch_fn` da ISSUE-0001.

## Reparo (2026-08-13): retry com backoff para 429/503 "High Demand"
Ao rodar a análise real no app Streamlit, a API do Gemini retornou
`503 UNAVAILABLE. This model is currently experiencing high demand. Spikes in demand are
usually temporary. Please try again later.` — indisponibilidade temporária do lado do
Google, não um erro do prompt/dados. Antes desse reparo, `RealGeminiClient.generate_content`
só tratava `code == 429` (cota), convertendo direto para `GeminiRateLimitError` sem
nenhuma tentativa de retry; qualquer outro `APIError` (incluindo 503) subia cru para o
chamador, derrubando o lote inteiro na primeira oscilação passageira do backend do Gemini.

Corrigido em `src/gemini_analyzer.py`:
- `_is_retryable_gemini_error(exc)`: considera retry quando `exc.code` é `429` ou `503`, **ou**
  quando a mensagem do erro contém "unavailable"/"high demand" (case-insensitive) — cobertura
  extra caso o SDK não preencha `code` de forma confiável em alguma variação de erro.
- `RealGeminiClient.generate_content` agora tenta até 4 vezes no total (1 tentativa inicial +
  até 3 retries), com backoff exponencial `time.sleep(2)`, `time.sleep(4)`, `time.sleep(8)`
  entre as tentativas que falharem com erro retryable. Erros não retryable (ex.: `400
  INVALID_ARGUMENT`) continuam subindo imediatamente, sem retry nem espera — preserva o
  comportamento anterior para esse caso.
- Se as tentativas se esgotarem ainda em 429/503, relança `GeminiRateLimitError` (mesma
  exceção que `analyze_batch` já sabia tratar graciosamente, reportando o lote como
  `quota_exceeded` em vez de derrubar `analyze_comments` inteiro) — nenhuma mudança de
  contrato foi necessária no restante do pipeline.
- Testes novos em `tests/test_gemini_analyzer.py`: retry que recupera na 3ª tentativa
  (mockando `time.sleep` para não esperar de verdade nos testes), retry que se esgota e
  relança `GeminiRateLimitError` após os backoffs `[2, 4, 8]`, e confirmação de que um erro
  não retryable (400) não aciona nenhum retry nem `time.sleep`. Suíte completa: 145 → 148
  testes, sempre verde (`.venv/bin/python -m pytest tests/`).
