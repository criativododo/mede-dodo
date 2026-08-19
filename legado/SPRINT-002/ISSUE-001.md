# ISSUE-001: Consolidação Canônica do Benchmark e da Arquitetura de Avaliação de Influenciadoras

| Campo | Valor |
|---|---|
| **Projeto** | métricaDODÔ |
| **Sprint** | Sprint 002 |
| **Tipo** | Issue de consolidação documental, benchmark funcional e arquitetura de referência |
| **Status** | **Concluída no escopo documental; implementação da funcionalidade permanece pendente** |
| **Fonte canônica** | Este arquivo `SPRINT-002/ISSUE-001.md` |
| **Método** | Framework Criativo Dodô / Metodologia Spark / ciclo PRVVC |
| **Objetivo de negócio** | Definir, com rastreabilidade, o que a funcionalidade de avaliação de influenciadoras de moda feminina deve medir, como deve calcular, como deve exibir e quais limites não pode ultrapassar |

> **Definição de ISSUE:** este documento registra o escopo atômico, o estado herdado, as obrigações, as decisões, as evidências, os desvios, as pendências e os próximos passos de uma entrega. O benchmark não é uma promessa de que todos os componentes já estejam implementados; ele é o contrato que orientará a implementação e a validação.

## 1. Objetivo, escopo e definição de pronto

Esta ISSUE consolida todo o trabalho realizado na preparação da Sprint 002 para que exista **um único documento de referência operacional**. O conteúdo reúne a pesquisa de fórmulas de taxa de engajamento, benchmarks por porte, diagnóstico do código existente, arquitetura de dados, taxonomia de comentários, intenção de compra, sentimento líquido, Top 3 posts, clusterização temática, proxy de Stories, regras do Gemini, segurança, tratamento de exceções e critérios de aceite.

O escopo desta ISSUE é documental e arquitetural. Não foi solicitado nesta entrega implementar os novos módulos de métricas, migrar o schema SQLite, alterar o exportador ou publicar o dashboard. A conclusão significa que a equipe agora possui um contrato consolidado, uma matriz de qualidade e uma lista explícita de débitos para executar sem Vibe Coding.

A ISSUE será considerada pronta quando: o arquivo canônico estiver gravado; todas as decisões relevantes estiverem vinculadas a evidências; fórmulas e fontes estiverem explícitas; as restrições negativas estiverem documentadas; a arquitetura respeitar separação de responsabilidades; os critérios de sucesso forem verificáveis; e as pendências estiverem classificadas por criticidade.

## 2. Estado herdado do início

### 2.1 Papel dos documentos no Framework Dodô

Os arquivos **MK-xx / Foundational Specs** registram premissas de alto nível e pilares de valor que não podem ser diluídos — por exemplo, baixo overhead, privacidade, latência mínima e custo de API controlado. O **FINDER** é o repositório de soluções técnicas pesquisadas, fórmulas, documentação oficial, benchmarks e padrões de reuso. A **SPEC** é o blueprint técnico ativo que lista arquivos físicos, contratos e obrigações que serão criados ou modificados. A ISSUE transforma esse conjunto em uma entrega atômica com estado, evidências, desvios e próximos passos.

Na transição para a Fase 2, esta ISSUE deve ser lida como fonte de contexto para a SPEC. A SPEC futura deverá herdar as restrições e decisões aqui registradas, aplicar Separation of Concerns, manter as Views livres de redes e regras de negócio e decompor a implementação em microentregas idempotentes.

### 2.2 Fontes locais consultadas

| Fonte | Papel | Estado observado |
|---|---|---|
| `DUMMY.md` | Safety Shield e restrições negativas | Lido; define background thread, filtragem antes do Gemini, throttling, dependências gratuitas e proteção do cache |
| `SPRINT-002/FINDER-001.md` | Pesquisa, benchmark e arquitetura de métricas | Consolidado anteriormente como base canônica de métricas e arquitetura |
| `SPRINT-002/FINDER-VIBECODE-001.md` | Governança Spark/Dodô, local-first, cache, segurança e Skills | Lido durante a pesquisa; na verificação final do diretório, o arquivo não estava presente no caminho esperado e seu conteúdo previamente absorvido foi preservado nesta ISSUE |
| `SPRINT-002/ISSUE-NOTEBOOKLM-001.md` | Checklist de Go Live, SDK Gemini, Instaloader, dados locais e sanity checks | Lido integralmente; usado como fonte de requisitos e evidências de estado |
| `SPRINT-002/referencias/modash.io` | Benchmark visual da experiência Modash | 44 PNGs processados por OCR, organizados em seis conjuntos de influenciadoras e uma tela de descoberta |
| `SPRINT-002/referencias/somente para referencia, dados ficticios.pdf` | Referência visual vertical adicional | Encontrado e tratado como material de referência; não é fonte de dados produtivos |
| `data/names_seed.json` | Base local para estimativa de gênero | Presente no repositório |
| `data/ddd_uf.json` | Mapeamento nacional de DDD para UF/região | Presente no repositório |
| `data/cache.db` | Persistência local e fallback | Presente no repositório |

O prompt inicial descrevia seis “prints”, mas a inspeção do diretório encontrou **44 arquivos PNG**: oito de `@silviabraz`, quatro de `@barbarastudart`, oito de `@manurefosco`, oito de `@robertapfranco`, oito de `@caroline_tanaka`, sete de `@juuchika` e uma tela geral de descoberta. A contagem real foi preservada para impedir que a implementação trate um conjunto de telas como se fosse uma única imagem.

### 2.3 Estado técnico validado

A estrutura atual possui `app.py`, módulos em `src/`, `data/cache.db`, `requirements.txt` e testes em `tests/`. O `src/scraper.py` possui coleta local, sessão, janela de posts, throttling e fallback de cache. O `src/metrics.py` já calcula uma taxa básica de engajamento e `pod_index`. O `src/scoring.py` possui pesos, tiers e score DODÔ heurístico. O `src/gemini_analyzer.py` usa `google-genai`, JSON estruturado, lotes e tratamento de quota. O `src/exporter.py` gera HTML autocontido e PDF via `fpdf2`.

A suíte foi executada com:

```bash
.venv/bin/python -m pytest tests/ -q
```

Resultado auditável da verificação: **145 passed, 1 warning**. O aviso está relacionado à depreciação interna de um alias de tipo no pacote `google.genai`; não houve falha de teste.

As dependências observadas incluem `streamlit==1.61.1`, `fpdf2==2.8.8`, `pytest==9.1.1`, `google-genai==2.17.0`, `python-dotenv==1.2.2` e `instaloader==4.15.3`. A configuração `.gitignore` protege `.env`, `.venv`, bytecode e `data/*.db`.

## 3. Exigências da SPEC para a Fase 2

A SPEC que suceder esta ISSUE deverá transformar as exigências abaixo em arquivos, funções, schemas e testes explícitos.

| Exigência | Obrigação herdada |
|---|---|
| Local-first | Processar e consultar `data/cache.db` antes de chamar serviços externos; manter fallback offline |
| View estrita | `app.py` atua como renderizador de estado; regras de negócio ficam em módulos e Skills |
| Background | Coleta e Gemini rodam fora da thread principal; a UI faz polling/rerun sem `thread.join()` |
| Determinismo | Fórmulas, filtros, pesos e classificações devem ter versão e teste |
| Caching | Toda chamada de IA deve consultar hash de input, modelo, prompt e versão antes de consumir cota |
| JSON estruturado | Gemini responde apenas ao schema definido; parser rejeita texto livre ou campos obrigatórios ausentes |
| Resiliência | 429, 503, timeout e falhas transitórias usam retry limitado, backoff exponencial, jitter e fallback |
| Segurança | Segredos somente no `.env`; consultas SQLite parametrizadas; acesso deny-by-default |
| Privacidade | Dados públicos e dados autenticados devem possuir fontes e permissões diferentes |
| Custo | Nenhuma biblioteca ou SDK pago; modelos e lotes devem respeitar a cota configurada |
| Rastreabilidade | Cada alteração possui ticket, teste, evidência e atualização de progresso |
| Correção de bugs | Diagnosticar linha e causa raiz antes da ação corretiva; adicionar teste de regressão |

### 3.1 Saneamento de contexto e idempotência

Antes de iniciar a implementação da SPEC, o agente deve limpar ou compactar o contexto conforme a governança do projeto e carregar apenas os documentos necessários: SPEC, DUMMY, esta ISSUE e as Skills relevantes. Microissues futuras devem ser coordenadas por `manifest.json`, com hash SHA-256 por bloco ou tarefa, para impedir que um agente reescreva trabalho já validado.

O escopo não deve ser implementado como bloco monolítico. A primeira microentrega deve fechar o schema e as fórmulas determinísticas; depois vêm a audiência, o NLP, o exportador e o score. Cada fatia precisa ser idempotente, testável e revisada antes da próxima.

## 4. Benchmark funcional de avaliação de influenciadoras

O benchmark inspirado no Modash não é apenas uma taxa de engajamento. Ele é uma sequência decisória:

> **Perfil → qualidade da audiência → desempenho do conteúdo → demografia e afinidade → histórico comercial → decisão de contratação.**

A tela e a API devem permitir responder: quem é a criadora e qual é o porte; a audiência parece autêntica; o conteúdo gera interação proporcional; a audiência coincide com o mercado; e o histórico é adequado para a marca.

### 4.1 Catálogo de métricas

| Grupo | Métrica | Tipo | Requisito |
|---|---|---|---|
| Perfil | nome, handle, avatar, localização, bio e categoria | Observada | Preservar valor bruto, origem e data |
| Volume | seguidores, posts na janela, frequência, média e mediana de interações | Observada/derivada | Persistir snapshot e tamanho da amostra |
| Engajamento | ER por seguidores, alcance, impressões, views e ponderada | Derivada | Sempre informar fórmula, denominador e ações |
| Audiência | seguidores potencialmente inautênticos, curtidas suspeitas, pessoas reais, notáveis, massa e suspeitas | Estimada | Separar sinal, modelo, confiança e data |
| Demografia | gênero, idade, país, cidade e idioma | Observada/estimada | Preservar período, cobertura e ausência de dados |
| Afinidade | interesses, hashtags, menções e categorias | Derivada | Manter evidências e termos representativos |
| Conversa | volume qualificado, intenção, sentimento, NSS e taxonomia | Modelada | Filtrar localmente antes do Gemini |
| Conteúdo | Top 3 por volume e por qualidade | Derivada | Exibir métricas e motivos do ranking |
| Comercial | publis, marcas, colaborações e mix de categorias | Inferida/observada | Menção não é prova de publicidade |
| Stories | views estimados por Highlights | Proxy | Exibir intervalo e confiança, nunca como alcance real |

### 4.2 Porte, objetivo e benchmark

A classificação inicial pode usar: nano de 1–20 mil; micro de 20–150 mil; mid-tier de 50–500 mil; macro de 150 mil–1 milhão; mega acima de 1 milhão. Como as faixas se sobrepõem em diferentes fornecedores, o sistema deve guardar a taxonomia usada no cálculo.

Os benchmarks devem ser segmentados por plataforma, nicho, país, período e fórmula. O material pesquisado registra uma linha Modash mais conservadora, com medianas aproximadas de 0,57%–1,00% para nano de 1–10 mil, 0,38% para micro de 10–50 mil, 0,41%–0,45% em mid-tier, 0,51% em 500 mil–1 milhão e 0,45% acima de 1 milhão. Também registra referências editoriais mais altas, incluindo o padrão operacional de aproximadamente **5%–8% em nano/micro** em alguns contextos. As séries não podem ser misturadas sem `benchmark_source` e `formula_version`.

A regra de negócio é normalizar por percentil dentro do próprio grupo, evitando comparar diretamente uma nano e uma macro por taxa nominal. Nanos e micros tendem a ser mais adequadas a conversão e co-criação; macros e megas tendem a ser mais adequadas a awareness, distribuição e validação social.

## 5. Fórmulas matemáticas canônicas

### 5.1 Convenções

Para uma janela com `n` publicações:

- `L_i`: curtidas; `C_i`: comentários; `S_i`: salvamentos; `H_i`: compartilhamentos.
- `R_i`: alcance único; `I_i`: impressões; `V_i`: visualizações.
- `F`: seguidores no snapshot; `w_L`, `w_C`, `w_S`, `w_H`: pesos do objetivo.

Toda métrica deve possuir `value`, `unit`, `metric_type`, `source`, `collected_at`, `window`, `content_scope`, `formula_version`, `confidence` e `status`.

### 5.2 Volume

```text
GrossInteractions = Σ(L_i + C_i + S_i + H_i)
MeanInteractions   = GrossInteractions / n
MedianInteractions = median(L_i + C_i + S_i + H_i)
FrequencyPerWeek   = posts_observed / weeks_in_window
```

A janela recomendada é de 12 publicações recentes, ou configurável entre 12 e 20. A mediana deve ser usada para reduzir impacto de posts virais. A média é útil para volume absoluto e a mediana para capacidade típica.

### 5.3 Taxa de engajamento por seguidores

```text
ER_F_avg = (1/n) * Σ[((L_i + C_i) / F) * 100]
ER_F_med = median_i(L_i + C_i) / F * 100
```

É a métrica mais viável para ranking público, mas mede a base potencial, não as pessoas expostas. A fórmula deve registrar se comentários entram no numerador. HypeAuditor é citado como referência pública de `(curtidas + comentários) / seguidores * 100`; Modash é citado como referência de mediana de curtidas dividida por seguidores no Instagram.

### 5.4 Taxa por alcance/impressões e views

```text
E_i   = L_i + C_i + S_i + H_i
ER_R  = Σ(E_i) / Σ(R_i) * 100
ER_I  = Σ(E_i) / Σ(I_i) * 100
ER_V  = Σ(E_i) / Σ(V_i) * 100
```

Alcance é distinto de impressões; views podem conter repetições. Essas métricas são superiores para campanha e post-buy, mas geralmente exigem Insights autenticados. Dados públicos estimados não podem ser apresentados como `verified_insights`.

### 5.5 Taxa ponderada e qualidade de interação

```text
ER_W = (1/n) * Σ[((w_L*L_i) + (w_C*C_i) + (w_S*S_i) + (w_H*H_i)) / F * 100]
```

Pesos iniciais: curtida 1; comentário 3; salvamento 4; compartilhamento 4. Para conversão, uma variante pode usar 1, 4, 5 e 3. A pesquisa também registra uma variante pesada de infraestrutura `Likes*1 + Comments*3 + Shares*5 + Saves*5`. Pesos são decisão de modelagem e devem ficar visíveis.

```text
q_i   = median_p[(L_p + 3*C_p + 4*S_p + 4*H_p) / F_i]
S_QI  = 100 * Percentil(q_i)
```

Comentários repetitivos, genéricos ou automatizados devem reduzir `text_authenticity_index`, sem apagar o volume bruto.

### 5.6 Assiduidade, consistência e audiência

```text
S_freq       = 100 * clip(f_i / f_target, 0, 1)
CV           = sigma(delta_t_i) / mu(delta_t_i)
S_regularity  = 100 * exp(-lambda * CV)
S_consistency = 0.6*S_freq + 0.4*S_regularity
S_stability   = 100 * (1 - clip(MAD(ER_p)/(ER_median + epsilon), 0, 1))
S_A           = 0.5*S_freq + 0.3*S_regularity + 0.2*S_stability
```

```text
S_aud = 0.60*A + 0.20*G + 0.10*D + 0.10*(100 - B)
```

`A` é autenticidade estimada; `G`, estabilidade do crescimento; `D`, adequação demográfica; `B`, comportamento suspeito. Sem afinidade confiável, usar `S_aud = 0.70*A + 0.20*G + 0.10*(100-B)`. Sinais incluem picos súbitos, follow/unfollow, perfis sem foto/posts, relação atípica entre seguidores e interações, comentários repetitivos e geografia incompatível. Nenhum sinal isolado confirma fraude.

### 5.7 Intenção de compra e taxonomia de comentários

| Classe | Sinais | Tratamento |
|---|---|---|
| `comercial` | preço, cupom, link, onde comprar, estoque, tamanho, entrega, intenção explícita | Entra no indicador de intenção |
| `afetivo` | elogio, identificação, apoio, marcação de amiga e vínculo | Mede comunidade, não é compra automaticamente |
| `critica` | reclamação de produto, preço, entrega, qualidade, publi ou atendimento | Entra no sentimento e em brand suitability |
| `spam_ruido` | emoji isolado, texto raso, repetição, sorteio irrelevante, link suspeito, autopromoção | Filtrar antes do Gemini |
| `neutro` | pergunta factual ou observação sem direção clara | Manter como neutro |

```text
PurchaseIntentRate  = commercial_comments / qualified_comments * 100
PurchaseIntentScore = (1*N0 + 2*N1 + 3*N2) / (3*qualified_comments) * 100
```

`N0`, `N1` e `N2` representam nenhuma/baixa, média e alta intenção. O painel deve exibir amostra e confiança. A classificação textual não pode ser confundida com venda realizada.

### 5.8 Sentimento líquido / NSS

```text
NSS          = (positive_comments - negative_comments) / qualified_comments * 100
PositiveRate = positive_comments / qualified_comments * 100
NegativeRate = negative_comments / qualified_comments * 100
NeutralRate  = neutral_comments  / qualified_comments * 100
```

O NSS varia de -100 a +100. Spam/ruído fica fora do denominador principal. Comentários críticos não devem ser removidos para melhorar o score, pois negatividade relevante protege o brand equity. O resultado exige `sample_size`, `sentiment_confidence`, `language_coverage` e `model_version`; com amostra insuficiente, exibir “amostra insuficiente”.

### 5.9 Top 3 posts

```text
PostScore_i = ER_component_i*w_er
            + WeightedInteraction_component_i*w_quality
            + PurchaseIntent_component_i*w_intent
            + Sentiment_component_i*w_sentiment
            - RiskPenalty_i
```

Manter duas listas: `top3_by_volume` e `top3_by_quality`. Cada post deve guardar ID/URL, data, tipo, legenda resumida, likes, comments, saves, shares, views, alcance, score, sinais comerciais, sentimento e riscos. O desempate usa escopo, recência e maior volume comparável.

### 5.10 Clusterização temática

A clusterização combina dicionário determinístico, hashtags, entidades de marca, comentários qualificados e embeddings somente quando necessário. Taxonomia inicial: moda/vestuário; beleza/autocuidado; bem-estar/fitness; viagens/lifestyle; família/maternidade; consumo/varejo; sustentabilidade/valores; conteúdo comercial; ruído/fora de escopo.

```json
{
  "cluster_id": "moda_vestuario",
  "label": "Moda e vestuário",
  "weight": 0.42,
  "evidence_count": 38,
  "representative_terms": ["look", "vestido", "lingerie"],
  "representative_posts": ["post_id_1", "post_id_2"],
  "confidence": 0.88,
  "method": "rules_plus_embeddings_v1"
}
```

Um cluster é resumo de conteúdo observado, não inferência sobre identidade, gênero ou intenção. Deve conservar período, cobertura e evidências.

### 5.11 Stories e Highlights

Sem Insights autenticados, Stories devem ser exibidos como proxy com intervalo e confiança. A fórmula de engenharia é:

```text
F_age       = ((age_days + 7) / 7)^(-0.25)
F_slides    = 1 / (1 + 0.10 * log1p(slide_count))
Highlight   = median(view_count * F_age * F_slides)
Profile     = clip(median_reel_views / followers / story_benchmark_ratio, 0.5, 2.0)
StoryViews  = Highlight * Profile
```

A confiança usa:

```text
Confidence = 0.30*C_age + 0.25*C_sample + 0.20*C_recency
           + 0.15*C_consistency + 0.10*C_crossformat
```

Faixas iniciais de views por Story, tratadas como prior, são 8%–15% para 1–10 mil seguidores; 4%–10% para 10–50 mil; 2%–6% para 50–100 mil; 1%–4% para 100–500 mil; e 0,5%–3% acima de 500 mil. Nunca exibir “alcance real”, “views garantidos” ou retenção observada quando houver apenas Highlights públicos.

### 5.12 Score DODÔ

```text
Q_i    = 0.40*S_ER + 0.20*S_QI + 0.15*S_A + 0.25*S_aud
Nota_i = 1 + 9*(Q_i / 100)
```

`Q=0` produz 1,0; `Q=50`, 5,5; `Q=90`, 9,1; `Q=100`, 10,0. Arredondar somente na interface e armazenar pelo menos quatro casas decimais. Pesos por objetivo podem ser: conversão/comunidade 35/30/25/10; equilíbrio 35/25/25/15; awareness 25/15/20/40. A parametrização alternativa do benchmark brasileiro — ER normalizado 70%, consistência 15%, storytelling 15% — deve ser registrada como perfil separado.

## 6. Arquitetura de dados e contratos

### 6.1 Separação de camadas

```text
[Streamlit app.py / View]
          |
          v
[Pipeline assíncrono + estado]
    |          |          |
 [scraper] [metrics] [Gemini/NLP]
    |          |          |
    +------ [SQLite cache.db] ------+
                   |
                   v
        [HTML / PDF / JSON / MCP]
```

`app.py` inicia e acompanha o pipeline. `scraper.py` coleta. `metrics.py`, `scoring.py`, `demographics.py` e novos módulos calculam. `database.py` persiste. `filters.py` remove ruído. `gemini_analyzer.py` enriquece comentários. `exporter.py` serializa. Skills/Playbooks Markdown descrevem regras de negócio determinísticas.

### 6.2 Schema de auditoria

```json
{
  "audit_id": "uuid",
  "user_id": "authenticated-user-id",
  "platform": "instagram",
  "handle": "creator_handle",
  "profile": {
    "display_name": "Nome",
    "followers_count": 2200000,
    "bio": "...",
    "location": "São Paulo, Brasil",
    "categories": ["moda", "beleza"]
  },
  "collection": {
    "collected_at": "2026-08-13T18:00:00Z",
    "window_days": 90,
    "post_count": 12,
    "content_scope": "all",
    "source": "local_public_collection",
    "source_version": "instaloader-4.15.3",
    "status": "complete|partial|stale|failed",
    "warnings": []
  },
  "metrics": {
    "engagement_rate": {
      "value": 0.032,
      "unit": "percent",
      "formula_id": "er_followers_median_likes_comments_v1",
      "denominator": "followers_snapshot",
      "included_actions": ["likes", "comments"],
      "post_count": 12,
      "kind": "derived",
      "confidence": "high"
    },
    "volume": {
      "followers": 2200000,
      "posts": 12,
      "median_interactions": 48000,
      "mean_interactions": 52000,
      "frequency_per_week": 2.1,
      "kind": "derived"
    },
    "purchase_intent": {
      "rate": 0.18,
      "score": 0.24,
      "qualified_comments": 100,
      "commercial_comments": 18,
      "kind": "model_output",
      "confidence": "medium"
    },
    "sentiment": {
      "nss": 32.0,
      "positive_rate": 0.55,
      "negative_rate": 0.23,
      "neutral_rate": 0.22,
      "sample_size": 100,
      "kind": "model_output",
      "confidence": "medium"
    }
  },
  "quality": {
    "fake_followers_rate": {
      "value": 0.239,
      "kind": "estimated",
      "model": "audience_quality_v1",
      "confidence": "medium"
    },
    "pod_index": 0.12,
    "text_authenticity_index": null
  },
  "top_posts": {"by_volume": [], "by_quality": []},
  "clusters": [],
  "stories_proxy": {"estimated_views_low": null, "estimated_views_high": null, "confidence": "insufficient"},
  "gemini": {"status": "not_configured|ok|quota_exceeded|failed", "model": null, "prompt_version": null, "input_hash": null, "items": []},
  "provenance": [],
  "formula_versions": {},
  "created_at": "2026-08-13T18:00:00Z"
}
```

### 6.3 Schema do Gemini

O contrato duck-typed atual é `client.generate_content(prompt)` retornando objeto com `.text`. Isso permite `RealGeminiClient`, fake de testes e adaptadores futuros sem acoplar a View ao SDK.

```json
{
  "items": [
    {
      "comentario": "texto original",
      "classe_comentario": "comercial|afetivo|critica|spam_ruido|neutro",
      "intencao_compra": "alta|media|baixa|nenhuma|desconhecida",
      "sentimento": "positivo|negativo|neutro|ambivalente|desconhecido",
      "faixa_etaria_estimada": "desconhecida",
      "confidence": 0.0
    }
  ],
  "meta": {
    "model": "gemini-flash-latest",
    "prompt_version": "comment_analysis_v1",
    "input_hash": "sha256",
    "status": "ok|partial|quota_exceeded|failed"
  }
}
```

O pipeline já limita a análise a dois lotes de até 100 comentários. Antes do prompt, `filters.is_shallow_comment` deve eliminar emojis isolados, comentários rasos e ruído. A ausência de `GEMINI_API_KEY` deve causar degradação graciosa, sem bloquear a auditoria determinística.

### 6.4 Persistência e cache

O SQLite deve conservar `profiles`, `posts_cache`, `metric_snapshots`, `comment_analysis_cache`, `audience_snapshots`, `formula_versions` e `audit_events`, ou estruturas equivalentes. O hash estável deve combinar input, modelo, prompt, janela e versão da Skill. O fallback deve marcar `cache_fallback` e `stale`; não pode apresentar dado antigo como atual.

## 7. Diagnóstico do código e muros de contenção

### 7.1 `app.py` como View

A UI deve iniciar uma `threading.Thread`, atualizar um dicionário em `st.session_state` e usar polling/rerun. Não deve chamar rede, Gemini ou SQL complexo diretamente, nem usar `thread.join()` bloqueante.

A ordem da tela deve ser: cabeçalho; resumo decisório; seletor de escopo; qualidade da audiência; demografia; conteúdo; conversa; afinidade; Stories/Highlights; exportação. Cada valor deve mostrar origem, período, amostra e confiança.

### 7.2 Limites de `src/exporter.py`

O exportador atual recebe `analysis` e devolve HTML autocontido ou bytes PDF, sem tocar em disco, rede ou `st.session_state`. O HTML/PDF atual cobre score DODÔ, ER básico, janela, gênero, regiões, `pod_index`, taxa de resposta, top repetidores, publis e itens do Gemini.

Ele ainda não cobre o catálogo completo: volume e mediana, fórmula/denominador do ER, intenção de compra, NSS, taxonomia, Top 3, clusters, proveniência, warnings, confiança, audiência estimada explicável, Stories por intervalo e versão de score. A evolução deve ser aditiva, com schema primeiro, renderização depois e testes de conteúdo/codificação por último. Nunca preencher ausência com zero nem chamar proxy de dado observado.

### 7.3 Segurança e negative constraints

As proibições abaixo são muros de contenção obrigatórios:

1. Não executar coleta ou API de forma síncrona na thread principal.
2. Não enviar comentários não filtrados ao Gemini.
3. Não fazer scraping em loop sem throttle/jitter de 2–5 segundos.
4. Não introduzir bibliotecas ou SDKs pagos.
5. Não apagar `data/cache.db` sem autorização explícita.
6. Não expor `GEMINI_API_KEY`, `INSTAGRAM_SESSION_FILE` ou qualquer segredo no frontend ou no Git.
7. Não permitir acesso entre usuários sem `user_id` e regra deny-by-default.
8. Não concatenar SQL; usar consultas parametrizadas.
9. Não tratar saída do Gemini como fonte de verdade numérica.
10. Não chamar proxy de Stories de alcance real.
11. Não classificar uma conta como fraudulenta por um sinal isolado.
12. Não fazer refatoração ampla sem diagnóstico, linha de falha e teste de regressão.

A divergência conhecida é que `DUMMY.md` proíbe apagar cache sem autorização, enquanto `database.clear_profile_cache` existe como ação de UI. A implementação deverá exigir confirmação, registrar evento e testar que apenas o perfil selecionado é removido.

### 7.4 Erros 429/503 e backoff

```text
base_delay = 1.0 segundo
max_retries = 4
retry_delay_k = min(base_delay * 2^k, 30 segundos) + jitter(0, 0.5)
```

| Erro | Ação |
|---|---|
| 429 / quota ou rate limit | Respeitar `Retry-After`, aplicar backoff, limitar lotes e usar cache/fallback |
| 503 / indisponibilidade | Até quatro tentativas com backoff e jitter; depois degradação graciosa |
| 500 transitório | Retry limitado e registro do evento |
| 400/401/403 | Não repetir cegamente; corrigir payload, chave ou permissão |
| timeout/conexão | Retry limitado e fallback para último dado válido |
| JSON inválido | Marcar lote falho, preservar demais resultados e registrar resposta |
| erro de schema do Instagram | Diagnosticar assinatura e executar apenas fallback aprovado |

O estado de retry não pode bloquear a View. Usar `retrying`, `fallback_cache`, `partial` ou `failed` e manter métricas determinísticas visíveis.

## 8. Matriz SPEC × Método Spark/Dodô

| Obrigação da SPEC | Implementação exigida | Evidência/validação |
|---|---|---|
| Isolamento de camadas | `app.py` View; lógica em `src/` e Skills | Busca estrutural sem chamadas de rede em renderizadores |
| Local-first | cache antes de API; fallback offline | Teste de cache hit e fallback stale |
| Determinismo | fórmulas versionadas e JSON estável | Fixtures matemáticos e snapshot de schema |
| Cota zero/controlada | filtro local, batches, cache e JSON conciso | Teste de comentários rasos não enviados |
| Idempotência | hash de bloco, input e prompt | `manifest.json` e hashes sem reprocessamento indevido |
| Segurança | `.env`, parametrização SQL e `user_id` | lint/regex e testes de acesso |
| Resiliência | backoff 429/503 e degradação | testes de retry, limite e fallback |
| Privacidade | separar público, Insights e modelo | campo `source` e `status` em cada métrica |
| Fatiamento | microentregas com testes | issue/manifest/plan atualizados |
| Qualidade visual | densidade informativa, labels e tooltips | teste manual do Streamlit e exportações |

## 9. Decisões técnicas com opções e impactos

### Decisão 1 — ER padrão de ranking

**Escolha:** usar `ER_F_med` como ranking público, com 12–20 posts e fórmula explícita; oferecer ER por alcance para contas conectadas e ER ponderado como camada de qualidade.

**Alternativas descartadas:** uma única média universal, porque é sensível a viralidade; ER por alcance para todos, porque requer acesso privado; score ponderado oculto, porque impede comparação e auditoria.

**Impacto:** maior comparabilidade pública, menor precisão de exposição real; essa limitação deve aparecer na UI.

### Decisão 2 — Percentis por tier

**Escolha:** normalizar por tier, nicho, plataforma, formato e período.

**Alternativas descartadas:** meta fixa de 5%–8% para todas; comparação direta entre nano e macro.

**Impacto:** reduz injustiça matemática e mantém benchmark editorial como referência contextual, sem convertê-lo em verdade universal.

### Decisão 3 — Gemini como enriquecimento

**Escolha:** Gemini classifica comentários, intenção e sentimento somente após filtragem local; fórmulas numéricas permanecem determinísticas.

**Alternativas descartadas:** pedir ao Gemini para calcular ER ou inventar dados demográficos; usar texto livre sem schema.

**Impacto:** maior auditabilidade, menor consumo e degradação graciosa sem chave.

### Decisão 4 — Stories como proxy

**Escolha:** usar Highlights, Reels e priors somente para intervalo de baixa/média confiança.

**Alternativa descartada:** apresentar um número pontual como views reais.

**Impacto:** preserva utilidade comercial sem falsa precisão.

### Decisão 5 — Score explicável

**Escolha:** nota opcional composta por ER, qualidade da interação, consistência e audiência, com pesos por objetivo.

**Alternativa descartada:** score único não decomponível.

**Impacto:** permite recalibrar sem perder métricas brutas e sustenta revisão humana.

## 10. Validações da fase

| Validação | Resultado |
|---|---|
| Leitura das fontes locais | `DUMMY.md`, `FINDER-001.md` e `ISSUE-NOTEBOOKLM-001.md` disponíveis e lidos; `FINDER-VIBECODE-001.md` foi absorvido anteriormente, mas não estava presente na verificação final |
| Inspeção visual | 44 PNGs Modash processados por OCR, organizados em seis perfis e uma tela de plataforma |
| Fórmulas | ER por seguidores, alcance/impressões, ponderada, volume, intenção, NSS, score e proxy Stories documentados |
| Taxonomia | Comercial, afetivo, crítica, spam/ruído e neutro documentados |
| Arquitetura | View, coleta, métricas, cache, NLP, exportação e MCP delimitados |
| Exceções | 429, 503, 500, 400/401/403, timeout, JSON inválido e erro de schema documentados |
| Dependências | `google-genai`, `instaloader==4.15.3`, Streamlit, fpdf2 e pytest presentes |
| Testes | 145 aprovados, 1 warning de depreciação |
| NotebookLM | Acesso direto bloqueado por autenticação Google; não declarar cruzamento concluído |
| Perplexity | Conector desabilitado na sessão; validação externa realizada por fontes públicas alternativas |

## 11. Encerramento factual da ISSUE

### 11.1 Status final

**CONCLUÍDA no escopo de consolidação documental e arquitetura.** O benchmark e as regras de implementação foram reunidos em uma única ISSUE. **Não concluída como implementação de produto:** os módulos de NSS, intenção, Top 3, clusterização, novos schemas e expansão do exportador ainda são pendências de código.

### 11.2 Cruzamento SPEC × Resultado

| Entrega prevista | Status | Evidência |
|---|---|---|
| Consolidar pesquisa e benchmark | Atendido | `SPRINT-002/FINDER-001.md` e este documento |
| Definir fórmulas canônicas | Atendido | Seção 5 |
| Definir arquitetura e schemas | Atendido | Seção 6 |
| Registrar muros de contenção | Atendido | Seção 7 |
| Definir interface Streamlit | Atendido | Seção 7.1 e critérios abaixo |
| Implementar novos módulos | Não atendido nesta ISSUE | Pendência crítica de código |
| Expandir HTML/PDF | Parcial | `src/exporter.py` atual funciona, catálogo completo ainda não |
| Integrar plenamente NotebookLM/Perplexity | Não atendido | Autenticação/conector indisponíveis |
| Validar regressão existente | Atendido | 145 testes aprovados |

### 11.3 Entregas realizadas

1. `SPRINT-002/ISSUE-001.md`, este documento canônico.
2. `SPRINT-002/FINDER-001.md`, base de benchmark e arquitetura consolidada anteriormente.
3. OCR e inventário das 44 imagens da referência Modash, utilizados como evidência de benchmark.
4. Validação local da suíte com 145 testes aprovados.
5. Consolidação do conteúdo histórico de `ISSUE-NOTEBOOKLM-001.md` sem apagar o arquivo legado.

### 11.4 Resultados e evidências

O resultado documental preserva a distinção entre métricas observadas, derivadas, estimadas, provenientes de Insights e geradas por modelo. A fórmula pública de ER não é misturada com reach rate; benchmarks de 5%–8% não são tratados como universais; Stories são proxy; comentários negativos permanecem relevantes para brand suitability; e o Gemini não é autoridade numérica.

A evidência quantitativa mais forte do estado do código é a suíte: **145 passed, 1 warning, 5,21 segundos** na última execução. A evidência de infraestrutura é a presença de `data/names_seed.json`, `data/ddd_uf.json`, `data/cache.db` e dependências fixadas. A evidência visual é o processamento dos 44 PNGs. A evidência de limitação é a tela de autenticação do Google para os cadernos NotebookLM e o conector Perplexity desabilitado.

### 11.5 Desvios mapeados e correções

| Desvio | Correção aplicada |
|---|---|
| O primeiro documento produzido foi enquadrado como plano de Sprint, quando o objetivo era benchmark | Reenquadramento explícito como base funcional/técnica e consolidação nesta ISSUE |
| A pasta inicialmente não estava acessível no sandbox | Uso do computador conectado e leitura direta do diretório físico |
| O prompt falava em seis prints, mas havia 44 PNGs | Inventário completo por perfil e contagem real preservada |
| O primeiro arquivo canônico gravado foi um FINDER, não uma ISSUE | Criação desta `ISSUE-001.md` como documento único de consolidação |
| O NotebookLM exigiu login | Limitação registrada; não simular resultados |
| `FINDER-VIBECODE-001.md` não estava presente na verificação final | Conteúdo previamente absorvido foi incorporado; ausência física registrada como pendência de rastreabilidade |
| Há conflito entre proibição de apagar cache e função `clear_profile_cache` | Exigir confirmação, auditoria, escopo por perfil e teste de regressão |

### 11.6 Decisões finais

A fonte canônica de execução passa a ser `ISSUE-001.md`. O FINDER permanece como repositório de benchmark e pesquisa; a SPEC futura deverá transformar esta ISSUE em arquivos físicos. O ER por seguidores com mediana é o padrão de ranking público; ER por alcance é exclusivo de dados autenticados; ER ponderado, NSS, intenção e score são camadas adicionais. O Gemini é opcional e subordinado ao filtro local, ao cache e ao JSON estruturado. Nenhuma métrica estimada será apresentada como observada.

### 11.7 Aprendizados técnicos

A taxa de engajamento precisa declarar numerador, denominador, amostra, escopo e fonte. Mediana é mais resistente a viralidade que média, mas não resolve seguidores falsos. Alcance e impressões são semanticamente diferentes. A qualidade textual precisa ser separada do volume. Um schema com `source`, `status`, `confidence` e `formula_version` evita interpretações retroativas. Fallback de cache deve ser visível como stale. Exportação e UI devem consumir o mesmo objeto canônico para evitar divergência.

### 11.8 Aprendizados metodológicos

O benchmark não deve ser confundido com uma implementação. A primeira pergunta de cada nova tarefa deve ser “qual documento governa esta decisão?”. O agente deve ler as fontes disponíveis, mapear o estado, propor uma microentrega e registrar o resultado antes de modificar código. Quando uma fonte está indisponível, isso deve aparecer como limitação, não ser preenchido por inferência. A contagem de evidências — como 44 imagens em vez de seis — precisa ser confirmada antes de planejar esforço.

### 11.9 Documentação final atualizada

| Documento | Papel após esta ISSUE |
|---|---|
| `SPRINT-002/ISSUE-001.md` | Fonte canônica desta consolidação |
| `SPRINT-002/FINDER-001.md` | Pesquisa, benchmark, fórmulas e arquitetura de referência |
| `SPRINT-002/ISSUE-NOTEBOOKLM-001.md` | Documento legado de checklist; preservado para rastreabilidade |
| `DUMMY.md` | Restrições negativas e Safety Shield |
| `README.md` | Instruções gerais do projeto; deve ser atualizado na próxima microentrega se o estado de produção mudar |
| `PROGRESS.md` | Deve receber a confirmação desta ISSUE quando a equipe registrar o progresso do repositório |

### 11.10 Pendências abertas classificadas

| Criticidade | Pendência | Impacto | Condição de encerramento |
|---|---|---|---|
| Crítica | Implementar schema de auditoria e snapshots de métricas | Sem contrato único, UI/exporter podem divergir | Testes de schema, ausência, fonte e escopo aprovados |
| Crítica | Implementar ER por mediana, reach, weighted, volume, NSS e intenção | Benchmark ainda não é funcional no produto | Fixtures determinísticos e documentação de fórmula |
| Crítica | Expandir `src/exporter.py` para o catálogo canônico | Relatório atual não entrega o benchmark completo | HTML/PDF/JSON com warnings e proveniência |
| Crítica | Implementar retry 429/503 com backoff e fallback | Risco de falha e desperdício de cota | Testes de retry, limite e degradação |
| Importante | Implementar taxonomia, Top 3 e clusterização | Reduz capacidade de decisão de marca | Saídas explicáveis, amostra e confiança |
| Importante | Resolver divergência de limpeza do cache | Risco de violar DUMMY | Confirmação e auditoria de exclusão |
| Importante | Confirmar presença/restauração do `FINDER-VIBECODE-001.md` | Rastreabilidade incompleta | Arquivo físico ou registro formal de arquivamento |
| Importante | Atualizar README/PROGRESS/manifest | Governança pode ficar desatualizada | Documentos guardiões alinhados ao estado real |
| Futuro | Benchmark próprio por país, nicho e objetivo | Melhor calibração de score | Dataset histórico validado |
| Futuro | Integração MCP com Sheets/CRM | Exportação e automação sem intervenção | Connector, permissões e testes de integração |
| Futuro | Acesso autenticado a Insights Meta/NotebookLM/Perplexity | Maior precisão e cruzamento de fontes | Credenciais, permissões e evidência auditável |

### 11.11 Próximos passos imediatos

1. Criar a SPEC técnica da primeira microentrega a partir do schema e dos critérios desta ISSUE.
2. Implementar e testar primeiro as métricas determinísticas: volume, ER por seguidores e proveniência.
3. Em seguida, implementar o adaptador de retries/cache e expandir os testes antes de adicionar Gemini, NSS e intenção.
4. Atualizar `README.md`, `PROGRESS.md` e `manifest.json` somente após a primeira microentrega validada.

## Referências

[1]: ../DUMMY.md — Safety Shield e Restrições Negativas do projeto.

[2]: FINDER-001.md — Base Canônica de Métricas, Pesquisa e Arquitetura.

[3]: ISSUE-NOTEBOOKLM-001.md — Checklist técnico de Go Live e validação do SDK Gemini.

[4]: https://www.modash.io/engagement-rate-calculator — Modash, calculadora e benchmarks de taxa de engajamento.

[5]: https://help.modash.io/en/articles/6542471-understanding-engagement-rate-and-how-modash-calculates-it — Modash, cálculo de ER.

[6]: https://hypeauditor.com/pt/free-tools/instagram-engagement-calculator/ — HypeAuditor, fórmula pública de ER.

[7]: https://developers.facebook.com/docs/instagram-platform/reference/instagram-media/insights/ — Meta for Developers, métricas de mídia do Instagram.

[8]: https://developers.facebook.com/documentation/instagram-platform/overview — Meta for Developers, permissões e limites da plataforma.

[9]: https://notebook.google.com/notebook/424cafb4-25ad-4d15-bc2c-fd62196c7258 — Caderno NotebookLM citado no material Spark/Dodô.

[10]: https://notebook.google.com/notebook/62f4b450-72af-4b89-b32a-b05c91765b96 — Caderno NotebookLM citado no checklist de Go Live.

### Adendo técnico — requisitos derivados do FINDER-002

O `FINDER-002.md` foi criado como documento separado de pesquisa e benchmark. Seu conteúdo não substitui esta ISSUE. Apenas os requisitos verificáveis abaixo são incorporados ao contrato técnico da entrega; a pesquisa de mercado, a comparação de repositórios e os detalhes proprietários permanecem no FINDER.

| ID | Requisito incorporado | Critério de aceite |
|---|---|---|
| F2-01 | O contrato de dados deve distinguir `observed`, `derived`, `estimated`, `model_output`, `verified_insights` e `unavailable`. | Cada KPI exportado contém `kind`, `source`, `confidence`, `freshness` e, quando aplicável, `coverage`. |
| F2-02 | Discovery não pode aplicar bloqueio artificial a contas acima de 10.000 seguidores. | Perfis grandes continuam elegíveis; limites de paginação, lote ou coleta são transparentes e não confundidos com elegibilidade. |
| F2-03 | Uma busca reproduzível deve registrar query, filtros, ordenação, data e fonte. | A shortlist pode ser reconstituída a partir do snapshot de Discovery. |
| F2-04 | Audience Quality deve mostrar sinais individuais e amostra, sem declarar fraude por um sinal isolado. | A interface usa “sinal de risco”/“estimativa”, exibe confiança e preserva a evidência. |
| F2-05 | Lookalikes devem informar o perfil-semente e a base da similaridade. | Cada resultado apresenta os atributos que causaram o match; não usar API Modash paga. |
| F2-06 | Content Search deve operar sobre captions, hashtags, mentions e tópicos locais. | O relatório informa cobertura do corpus, período e método de indexação. |
| F2-07 | Gemini permanece opcional, cacheado, em JSON e subordinado às métricas determinísticas. | Sem chave, quota ou resposta válida, o pipeline continua com degradação graciosa e sem apagar resultados. |
| F2-08 | Qualquer repositório open-source incorporado exige revisão de licença, segurança e compatibilidade. | Nenhum código é copiado automaticamente; ferramentas de bypass de anti-bot são proibidas. |
| F2-09 | O Streamlit deve exibir freshness, coverage, source, confidence e warnings junto dos KPIs. | HTML, PDF e JSON preservam os mesmos metadados do `audit_id` exibido. |
| F2-10 | Ausência de dado deve retornar `unavailable` ou `insufficient`, nunca zero silencioso. | Testes cobrem conta sem Insights, Stories sem dados e falhas parciais de coleta. |

A pesquisa pública do Modash indica módulos de Discovery, busca natural/visual, Profile Report, Audience Quality, Lookalikes, Content Search e histórico de colaborações; esses módulos são **benchmark de experiência**, não dependências do produto. A arquitetura local-first deve replicar somente capacidades compatíveis com dados públicos, cache SQLite, Instaloader fixado, filtros determinísticos e Gemini Flash estruturado, sem mensalidades, APIs pagas ou limitação artificial por porte.

O FINDER-002 também registrou repositórios open-source de referência, incluindo Instaloader, BERTopic, botnet-detection e classificadores de spam. Eles não alteram a regra de custo zero: qualquer adoção futura depende de revisão de licença e não pode introduzir bypass de anti-bot, execução remota, API paga ou dependência de GPU obrigatória.

