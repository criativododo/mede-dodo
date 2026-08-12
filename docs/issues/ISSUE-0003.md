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
