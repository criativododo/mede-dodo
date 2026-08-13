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

## Refinamento de qualidade (2026-08-13)
Pedido explícito do usuário: aprimorar a QUALIDADE/RELEVÂNCIA/PROFUNDIDADE dos dados exibidos
no app (o que o Gemini analisa, quais métricas são calculadas, como são apresentadas), sem
tocar no layout Streamlit de `app.py` (colunas/containers/sidebar/ordem dos blocos
inalterados). O documento originalmente citado como diretriz canônica
(`FINDER-0001.md`) acabou sendo só sobre a migração de SDK já concluída (ver seção acima) —
sem conteúdo sobre relevância de auditoria; o usuário forneceu os critérios diretamente
(engajamento qualitativo vs. ruído de emojis, intenção de compra, sentimento comercial vs.
afetivo, aderência comercial). Antes de implementar, pesquisa de mercado via `WebSearch`
confirmou/refinou esses critérios: (1) qualidade de comentário pesa mais que volume — uma
pergunta de preço/tamanho vale mais como sinal de conversão do que dezenas de comentários de
uma palavra; (2) engajamento saudável para nano/micro-influenciadoras de moda/lifestyle varia
bastante entre fontes (~1,2% a ~5%, dependendo do porte e do estudo) — usado só como
referência textual, não como corte rígido; (3) padrões reais de spam/bot (`"confira meu
perfil"`, `"chama no direct pra parceria"`, `"sigo de volta"/"s4s"`, link externo em
comentário) validam a necessidade de reforçar o filtro local além de emoji-only/elogio de uma
palavra.

Implementado:
1. **`src/filters.py`** — `is_generic_praise` passou a detectar elogio genérico também
   decorado (ex.: `"vc é linda"`, `"que gata"`), removendo palavras de preenchimento
   (`_FILLER_WORDS`) antes de comparar o restante contra o vocabulário de elogio
   (`GENERIC_PRAISE_WORDS`, agora com variantes masculinas/femininas); sem falso positivo em
   comentário genuíno mais longo que só contém uma palavra de elogio no meio (testado). Nova
   `is_bot_like_comment` filtra link externo em comentário e frases típicas de troca de
   engajamento/autopromoção validadas pela pesquisa (`_BOT_SPAM_PATTERNS`).
   `is_shallow_comment` passou a considerar as três frentes (emoji-only, elogio genérico,
   bot-like).
2. **`src/gemini_analyzer.py`** — `PROMPT_TEMPLATE` reescrito para pedir, por comentário, além
   de `intencao_compra`/`faixa_etaria_estimada`: `categoria_sentimento`
   (`interesse_comercial|validacao_pessoal|duvida_critica|spam_ruido`) e `sinais_compra` (lista
   de sinais concretos: `preco|tamanho|caimento|tecido|onde_comprar|estoque|depoimento_compra`).
   `REQUIRED_RESPONSE_FIELDS` **não** foi expandido com os novos campos — continuam opcionais/
   enriquecimento, nunca exigidos para o item ser aceito por `parse_batch_response` — decisão
   deliberada para preservar retrocompatibilidade total com mocks/testes no schema antigo de 3
   campos, conforme pedido explícito do usuário. Nova função pura
   `summarize_brand_suitability(items, pod_index=None)`: parecer agregado de aderência
   comercial (indicador alto/médio/baixo/sem_dados, percentuais por categoria de sentimento,
   contagem de comentários de alta intenção, alertas quando `pod_index` ou proporção de
   spam/ruído estão elevados) — calculado **localmente** a partir da classificação já feita
   pelo Gemini, sem nenhuma chamada extra de API (o projeto tem teto de 2 requisições Gemini
   por perfil, RNF-03).
3. **`app.py`** — `_run_pipeline` chama `summarize_brand_suitability` após `analyze_comments` e
   guarda o resultado em `comentarios_analisados.parecer_comercial`. `_render_comentarios_card`
   passou a exibir esse parecer (indicador + resumo + alertas via `st.warning`) dentro do mesmo
   subheader já existente, e `_render_metric_cards` ganhou uma `st.caption` de referência de
   mercado sob a métrica de engajamento — nenhuma coluna/container/sidebar foi adicionada,
   removida ou reordenada.
4. **`src/exporter.py`** — HTML e PDF passaram a mostrar a coluna de sentimento/sinais de
   compra na tabela de comentários e uma seção/parágrafo de parecer de aderência comercial
   (aditivo via `.get()`, sem quebrar os fixtures antigos de teste que não têm esses campos).
5. Validação real (fora dos testes automatizados, via scripts descartáveis): pipeline completo
   simulando um `RealGeminiClient` com o novo schema, fim a fim, incluindo geração de
   HTML/PDF; e renderização real via `streamlit.testing.v1.AppTest` (equivalente headless de
   `streamlit run app.py` neste ambiente sem navegador) confirmando ausência de exceções e o
   texto renderizado como esperado.
6. Suíte completa: 148 → 162 testes, sempre verde (`.venv/bin/python -m pytest tests/`).
