# ISSUE-0005: Métricas de Antifraude (Pods) e Score DODÔ

## Objetivo
Calcular localmente o índice de repetição de comentaristas ("pods", RF-08) a partir dos
dados já persistidos, a taxa de engajamento por post, e consolidar tudo em uma nota única
de 0 a 10 (Score DODÔ, RF-10) que resuma engajamento, qualidade dos comentários, taxa de
resposta da criadora e indício de fraude — sem depender de nenhuma chamada externa (LLM
ou rede).

## Tarefas de Implementação
1. **Índice de Pods (`src/metrics.py`):**
   - `calc_pod_index(posts)` recebe `posts: list[{"post_id": str, "commenters": list[str]}]`
     e identifica comentaristas que aparecem em 2 ou mais posts **distintos** do mesmo
     perfil (indício de "pod" de engajamento combinado).
   - Retorna total de comentários, comentaristas únicos, `pod_index` (proporção de
     comentários feitos por repetidores) e `top_repetidores` ordenado desc por contagem.
   - Nunca lança exceção: lista vazia ou posts sem `commenters` retornam zeros/estruturas
     vazias.
2. **Score DODÔ (`src/scoring.py`):**
   - `calc_engagement_rate(posts, followers_count)`: média de
     `(likes_count + comments_count) / followers_count` por post; `followers_count <= 0`
     ou lista vazia retornam `0.0` sem dividir por zero.
   - `calc_dodo_score(engagement_rate, qualified_ratio, response_rate, pod_index)`:
     combina os quatro sinais em uma nota 0.0–10.0, clampando `engagement_rate` a no
     máximo 1.0 antes de ponderar (perfis pequenos/virais podem passar de 100% de
     engajamento) e penalizando o score quando `pod_index` é alto.
3. **Testes TDD (`tests/test_metrics.py`, `tests/test_scoring.py`)** cobrindo casos vazios,
   sem repetição, com repetição entre posts distintos, clamp de engajamento acima de 1.0 e
   os extremos (0.0 e 10.0) do Score DODÔ.

## Critérios de Aceite (Definition of Done)
- [x] `calc_pod_index` calcula `pod_index` corretamente a partir de comentaristas
      repetidos entre posts distintos do mesmo perfil, nunca lança exceção.
- [x] `top_repetidores` inclui apenas comentaristas com `count >= 2`, ordenado desc.
- [x] `calc_engagement_rate` nunca divide por zero (`followers_count <= 0` ou posts vazio
      -> `0.0`).
- [x] `calc_dodo_score` clampa `engagement_rate` a 1.0 antes de ponderar e retorna sempre
      um valor no intervalo 0.0–10.0.
- [x] Testes executados com sucesso via pytest, sem mocks de rede (funções 100% locais,
      determinísticas) — 15/15.

## Notas de Implementação
- **Definição de "repetidor" adotada:** um comentarista só conta como indício de pod
  quando aparece em **2 ou mais `post_id` distintos** do mesmo perfil — comentar duas
  vezes dentro do *mesmo* post não configura repetição entre posts (coberto pelo teste
  `test_calc_pod_index_same_commenter_appearing_only_once_is_not_a_repetidor`). O `count`
  reportado em `top_repetidores` é o total de comentários feitos por esse usuário (soma de
  ocorrências em todos os posts em que ele aparece), não o número de posts distintos — essa
  interpretação não estava 100% explícita no contrato original e foi uma decisão de
  engenharia tomada para manter `pod_index` (proporção de *comentários* feitos por
  repetidores) e `top_repetidores` consistentes entre si.
- **Os pesos do Score DODÔ são uma heurística de engenharia, NÃO uma fórmula validada com
  dados reais de campanha.** Foram definidos por julgamento de produto (engajamento pesa
  mais porque é o sinal mais direto de alcance real; pod_index pesa menos porque é um
  indício, não uma prova definitiva de fraude), exatamente nos mesmos moldes de honestidade
  já registrados em ISSUE-0001.md (fetch_fn real pendente) e ISSUE-0003.md (índice de pods
  fora do schema do Gemini por não ser algo que um LLM possa inferir com confiança). Pesos
  atuais: engagement_rate clampado a 1.0 = 40%, qualified_ratio = 25%, response_rate = 20%,
  (1 - pod_index) = 15%. Nenhuma calibração com dados reais de campanha foi feita — isso
  fica como trabalho futuro explícito, quando houver histórico suficiente de campanhas
  reais para validar (ou refutar) esses pesos.
- **`qualified_ratio` e `response_rate` não são calculados por este módulo.** Ambos são
  recebidos como floats prontos (0.0–1.0) vindos de outras camadas do pipeline (filtragem
  de comentários qualificados da ISSUE-0002/RF-05 e mapeamento de resposta da criadora da
  RF-08, respectivamente) — `src/scoring.py` apenas consome esses números, não os produz.
- `calc_pod_index` e `calc_dodo_score`/`calc_engagement_rate` são 100% locais e
  determinísticos, sem parâmetro injetável de dependência externa (diferente de
  `fetch_fn`/`client` em `scraper.py`/`gemini_analyzer.py`), porque não há nenhuma
  chamada de rede ou I/O envolvida — só agregação matemática sobre estruturas já em
  memória.
