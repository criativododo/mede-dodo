# FINDER-001: Base Canônica de Métricas, Pesquisa e Arquitetura (Sprint 2)

> **Status:** base canônica consolidada para orientar a implementação do métricaDODÔ. Este arquivo funde a pesquisa de métricas e benchmarks com as decisões de engenharia do Framework Criativo Dodô / Metodologia Spark. O documento define contratos, fórmulas, limites de interpretação e muros de contenção; não substitui tickets de implementação nem testes de regressão.

## 1. Visão Geral e Contexto de Negócio (Moda Feminina 2026)

O métricaDODÔ deve avaliar influenciadoras de moda feminina como ativos de comunidade, distribuição e reputação, e não apenas como inventário de seguidores. Em 2026, a decisão de contratação precisa conciliar volume, qualidade da interação, consistência editorial, adequação de audiência, intenção de compra e segurança de marca. O benchmark funcional do produto deve responder, para cada perfil, cinco perguntas: qual é o tamanho e o porte da criadora; a audiência apresenta sinais de autenticidade; o conteúdo gera interação proporcional ao porte; a comunidade coincide com o público-alvo; e o histórico de conteúdo é comercialmente adequado?

A referência de mercado possui duas leituras que não podem ser misturadas sem preservar a origem. A primeira é a linha estatística observada pelo Modash, baseada em medianas por faixa de seguidores, com valores consideravelmente mais baixos que benchmarks editoriais. A segunda é a expectativa de mercado frequentemente publicada em guias de vetting, com faixas de aproximadamente **5% a 8% para nano/micro em determinados contextos**, cerca de 2% a 4% para micros em referências mais conservadoras e valores próximos de 1% ou menos para perfis acima de 500 mil seguidores. A plataforma deve armazenar `benchmark_source`, `formula_version`, `platform`, `niche`, `period` e `sample_definition`; nunca apresentar uma dessas séries como verdade universal.

### 1.1 Taxonomia operacional de portes

| Tier | Faixa operacional | Objetivo dominante | Leitura de qualidade | Benchmark estatístico/operacional inicial |
|---|---:|---|---|---:|
| Nano | 1 mil–20 mil seguidores | Conversão, comunidade e co-criação | Proximidade, comentários contextuais, confiança e nicho | Modash: aproximadamente 0,57%–1,00% de mediana para faixas de 1–10 mil; referência editorial: 5%–8% em contextos de alta densidade; usar percentis por nicho |
| Micro | 20 mil–150 mil seguidores | Autoridade temática e escala controlável | Equilíbrio entre comunidade e alcance | Modash: aproximadamente 0,38%–0,45% nas faixas públicas próximas; referência editorial: aproximadamente 5%–8% ou 2%–4%, conforme fórmula e fonte |
| Mid-tier | 50 mil–500 mil seguidores | Profissionalização e alcance relevante | Capacidade de ampliar campanhas sem perder contexto | Modash: aproximadamente 0,41%–0,45%; recalibrar por plataforma e amostra |
| Macro | 150 mil–1 milhão de seguidores | Awareness, validação social e universo narrativo | Volume absoluto, brand lift e distribuição | Modash: aproximadamente 0,51% em 500 mil–1 milhão; benchmark editorial brasileiro citado: cerca de 3,2% para macro de alta performance |
| Mega/celebridade | Acima de 1 milhão | Awareness massivo, memória e associação de marca | Escala, reputação e social proof | Modash: aproximadamente 0,45% em 1 milhão+; HypeAuditor citado: aproximadamente 0,68%; interpretar com origem explícita |

A categorização deve ser configurável porque as faixas variam entre fornecedores. A classificação não pode ser usada para penalizar automaticamente uma macro por ter taxa nominal menor que uma nano. O algoritmo deve normalizar dentro do próprio tier, nicho, plataforma e formato, preferencialmente por percentil ou desvio padrão, e deve manter separado o volume absoluto de interações.

### 1.2 Estratégia de negócio por porte

Nanos e micros são prioritárias para conversão, co-criação e “branding antropomórfico”: possuem comunidades menores, mas tendem a oferecer maior proximidade, autoridade temática e comentários mais contextuais. Macros e megas são prioritárias para awareness, brand lift, universo narrativo e distribuição. O produto deve permitir objetivos de campanha distintos — `conversion`, `community`, `consideration`, `awareness` e `balanced` — porque o mesmo perfil pode ser excelente para uma finalidade e inadequado para outra.

A maturidade do marketing de influência exige priorizar a natureza da interação sobre o volume bruto. Comentários, salvamentos e compartilhamentos possuem sinais de esforço e intenção diferentes de curtidas; ao mesmo tempo, uma interação negativa ou automatizada pode inflar o numerador e prejudicar a marca. Por isso, o score deve ser decomponível em métricas brutas, qualidade textual, autenticidade da audiência e adequação de marca.

### 1.3 Princípios Spark/Dodô

O Framework Spark/Dodô é a antítese do Vibe Coding. A execução segue o ciclo **PRVVC — Planejamento, Revisão, Execução, Validação e Confirmação**: a decisão humana define o contrato e revisa o plano; a IA executa ordens estritas, produz evidências e não inventa regra de negócio.

A arquitetura deve obedecer a quatro diretrizes: engenharia sobre intuição; rastreabilidade atômica; soberania dos dados locais; e gestão rigorosa da janela de contexto. Toda lógica nova deve ser descrita em uma Skill ou Playbook Markdown determinístico, toda alteração deve ser rastreada em um ticket e todo merge deve depender de testes aprovados.

O desenho é **local-first**. `data/names_seed.json` e `data/ddd_uf.json` são fontes locais para gênero estimado e geografia; `data/cache.db` é a persistência obrigatória para evitar chamadas redundantes; `Instaloader==4.15.3` deve ser fixado para reduzir drift; e sessões do Instagram devem permanecer em configuração local. A futura evolução é um Company Brain conectado por MCP a planilhas, CRM e relatórios, mas nenhuma integração externa deve substituir a fonte de verdade local sem registrar origem e validade.

## 2. Catálogo Canônico de Métricas e Fórmulas Matemáticas

### 2.1 Convenções de dados

Considere uma janela com `n` publicações comparáveis:

- `L_i`: curtidas da publicação `i`.
- `C_i`: comentários da publicação `i`.
- `S_i`: salvamentos da publicação `i`.
- `H_i`: compartilhamentos da publicação `i`.
- `R_i`: alcance único da publicação `i`.
- `I_i`: impressões da publicação `i`.
- `V_i`: visualizações da publicação `i`.
- `F`: seguidores no snapshot da coleta.
- `w_L, w_C, w_S, w_H`: pesos configuráveis pelo objetivo.
- `m`Content scope`: `all`, `feed`, `reels`, `stories`, `highlights`.

Toda métrica deve possuir, no mínimo, `value`, `unit`, `metric_type`, `source`, `collected_at`, `window`, `content_scope`, `formula_version`, `confidence` e `status`. O contrato deve distinguir `observed`, `derived`, `estimated`, `platform_estimate`, `model_output` e `unavailable`. `null` ou conjunto vazio significa “não disponível”; não deve ser convertido silenciosamente em zero.

### 2.2 Volume e escala

O volume de uma conta deve ser apresentado em três níveis:

| Métrica | Fórmula/definição | Uso |
|---|---|---|
| Volume de seguidores | `F` no snapshot da coleta | Porte, alcance potencial e normalização |
| Volume de posts | `n` na janela válida | Cobertura estatística e frequência |
| Volume bruto de interações | `Σ(L_i + C_i + S_i + H_i)` quando disponível | Distribuição e capacidade absoluta |
| Média de interações | `Σ interações / n` | Resumo de conteúdo |
| Mediana de interações | `median(interações_i)` | Ranking resistente a viralidade |
| Frequência semanal | `posts_observed / weeks_in_window` | Assiduidade |
| Alcance/impressões | `R_i`, `I_i` por conteúdo | Performance de exposição autenticada |

O produto deve mostrar média e mediana quando a amostra comportar as duas. Uma publicação viral não deve definir sozinha a capacidade típica da criadora. Para ranking público, a janela recomendada é de 12 publicações recentes ou, quando necessário, uma janela configurável entre 12 e 20; conteúdo sem métricas comparáveis deve ser excluído com motivo registrado.

### 2.3 Taxa de engajamento

Não existe uma taxa universal. O backend deve manter fórmulas distintas e devolver o tipo explicitamente.

#### ER por seguidores — triagem e ranking público

A fórmula média é:

```text
ER_F_avg = (1/n) * Σ[(L_i + C_i) / F] * 100
```

A fórmula robusta recomendada para ranking é:

```text
ER_F_med = median_i(L_i + C_i) / F * 100
```

O padrão é compatível com auditoria pública e comparação de grandes volumes, mas mede interação em relação à base potencial, não em relação às pessoas que efetivamente viram o conteúdo. A mediana reduz distorção de posts virais, campanhas atípicas e conteúdo excepcional. O denominador deve ser o snapshot de seguidores mais próximo da data da coleta; quando o produto tiver histórico por publicação, deve registrar também `followers_at_post_time`.

HypeAuditor é citado como referência de fórmula pública baseada em `(curtidas + comentários) / seguidores * 100`, usando aproximadamente 12 posts recentes e tratamento de extremos. Modash é citado como referência de mediana de curtidas dividida por seguidores no Instagram. Como os numeradores não são idênticos, o métricaDODÔ deve declarar se comentários entram no ER e nunca chamar ambas de `engagement_rate` sem `formula_id`.

#### ER por alcance ou impressões — Insights autenticados

```text
E_i = L_i + C_i + S_i + H_i
ER_R = Σ(E_i) / Σ(R_i) * 100
ER_I = Σ(E_i) / Σ(I_i) * 100
```

Alcance representa contas únicas; impressões podem contar várias exibições da mesma conta. Esse método é semanticamente superior para avaliar exposição real e campanhas pós-compra, mas normalmente requer consentimento, autenticação OAuth ou relatório de Insights fornecido pela criadora. O resultado deve receber `source=verified_insights` quando vier de acesso autorizado.

A documentação da Meta diferencia alcance, impressões, visualizações, likes, comments, saves, shares e `total_interactions`. Para mídia elegível, a API pode devolver interações orgânicas e, em certas configurações, métricas agregadas de mídia promovida. O sistema não deve tratar uma métrica pública estimada como equivalente a um Insight autenticado.

#### ER ponderado — qualidade e intenção

```text
ER_W = (1/n) * Σ[((w_L*L_i) + (w_C*C_i) + (w_S*S_i) + (w_H*H_i)) / F * 100]
```

Pesos iniciais recomendados:

| Objetivo | Curtida | Comentário | Salvamento | Compartilhamento |
|---|---:|---:|---:|---:|
| Awareness | 1 | 2 | 2 | 4 |
| Consideração | 1 | 3 | 4 | 4 |
| Conversão | 1 | 4 | 5 | 3 |
| Referência editorial pesada | 1 | 3 | 5 | 5 |

A variante de referência de infraestrutura é `Likes*1 + Comments*3 + Shares*5 + Saves*5`, dividida pela base. Esses pesos são decisão de produto, não lei matemática nem benchmark universal. Salvamentos e compartilhamentos frequentemente não estão disponíveis para perfis públicos. Expor `ER_W` sem expor pesos, eventos disponíveis e fonte cria falsa precisão.

#### Metodologias e prioridade

| Metodologia | Precisão analítica | Captura | Atualização | Uso canônico |
|---|---:|---:|---:|---|
| Seguidores | Baixa a média | Alta via público/scraping | Diária ou D-1 | Descoberta, triagem e ranking público |
| Alcance | Alta | Média/baixa, exige API privada | Horária ou conforme Insights | Post-buy, campanha e performance real |
| Ponderada | Alta, se dados completos | Média | Próxima de tempo real quando autenticada | Qualidade, intenção e score adicional |

O Modelo Ponderado pode ser o padrão interpretativo do sistema, mas as Metodologias I e II devem permanecer disponíveis como filtros de visualização. O ER público por seguidores continua sendo o comparador de mercado mais operacional; o ER por alcance continua sendo a melhor leitura para campanha autenticada.

### 2.4 Intenção de compra

A intenção de compra deve ser uma métrica de **volume e proporção de sinais textuais**, não uma promessa de conversão. O pipeline trabalha apenas sobre comentários qualificados após filtragem local de ruído.

#### Taxonomia canônica de comentários

| Classe | Sinais principais | Tratamento |
|---|---|---|
| Comercial | Pergunta de preço, disponibilidade, link, cupom, onde comprar, entrega, tamanho, compra explícita | Sinal positivo de intenção; alta prioridade para o relatório |
| Afetivo/comunidade | Elogio, identificação pessoal, apoio, desejo não comercial, marcação de amiga | Mede vínculo e afinidade; não é intenção de compra por si só |
| Crítica/risco | Reclamação de produto, preço, entrega, qualidade, publicidade ou atendimento | Não deve ser descartado; alimenta sentimento e brand suitability |
| Spam/ruído | Emojis isolados, comentários rasos, repetição, sorteios irrelevantes, links suspeitos, autopromoção | Filtrar localmente antes de chamar o Gemini |
| Neutro/informativo | Pergunta factual sem decisão, observação descritiva, resposta ambígua | Manter como neutro ou baixa intenção |

O Gemini deve devolver JSON estrito por comentário qualificado, com `comentario`, `classe_comentario`, `intencao_compra`, `sentimento`, `faixa_etaria_estimada` quando pertinente e `confidence`. O sistema deve preservar o texto original, a versão do prompt e a data do modelo.

A taxa básica é:

```text
PurchaseIntentRate = commercial_comments / qualified_comments * 100
```

Uma versão ponderada por intensidade é:

```text
PurchaseIntentScore = (1*N0 + 2*N1 + 3*N2) / (3*qualified_comments) * 100
```

Onde `N0` é nenhuma/baixa intenção, `N1` é intenção média e `N2` é intenção alta. O painel deve mostrar também o tamanho da amostra, porque uma taxa de 40% baseada em cinco comentários não é comparável a 40% baseada em 500.

### 2.5 Sentimento líquido / NSS

O sentimento deve ser apresentado como qualidade da conversa, não como soma cega de comentários. O **Net Sentiment Score (NSS)** recomendado é:

```text
NSS = (positive_comments - negative_comments) / qualified_comments * 100
```

A escala vai de `-100` a `+100`. Para permitir um indicador de distribuição, mostrar também:

```text
PositiveRate = positive_comments / qualified_comments * 100
NegativeRate = negative_comments / qualified_comments * 100
NeutralRate  = neutral_comments / qualified_comments * 100
```

O NSS não deve incluir spam/ruído no denominador principal. Uma segunda leitura opcional, `NSS_all_comments`, pode existir para transparência, mas deve deixar claro que o ruído altera a composição. Comentários críticos não devem ser removidos por serem negativos; eles são essenciais para proteger brand equity.

O sentimento precisa ser acompanhado por `sentiment_confidence`, `sample_size`, `language_coverage`, `model_version` e `manual_review_required`. Se o volume for insuficiente, o produto exibe “amostra insuficiente” em vez de um NSS numericamente instável.

### 2.6 Top 3 posts

O Top 3 deve representar desempenho típico e não apenas posts virais. O ranking deve ser configurável por objetivo:

```text
PostScore_i =
  ER_component_i * w_er
  + WeightedInteraction_component_i * w_quality
  + PurchaseIntent_component_i * w_intent
  + Sentiment_component_i * w_sentiment
  - RiskPenalty_i
```

O padrão de desempate é: escopo de conteúdo, data mais recente, maior número de interações comparáveis. Cada item do Top 3 deve mostrar `post_id`, URL quando disponível, data, tipo de mídia, legenda resumida, curtidas, comentários, salvamentos, compartilhamentos, views, alcance, `post_score`, sinais comerciais, sentimento e motivos de risco.

O sistema deve guardar duas listas quando possível: `top3_by_volume` e `top3_by_quality`. A primeira privilegia interações absolutas; a segunda privilegia ER ponderado, comentários qualificados, NSS e intenção. Isso evita que uma conta macro domine o ranking de qualidade apenas por escala.

### 2.7 Clusterização temática

A clusterização temática deve transformar legendas, hashtags, comentários qualificados e categorias em grupos interpretáveis para moda feminina. O pipeline recomendado é híbrido:

1. normalizar idioma, hashtags, entidades e 1. normalizar idioma, hashtags, entidad determinístico de categorias;
3. gerar embeddings somente quando necessário;
4. agrupar por similaridade e nomear os clusters com regras ou revisão humana;
5. armazenar evidências e exemplos, não somente o nome do cluster.

Taxonomia inicial:

| Cluster | Exemplos de sinais |
|---|---|
| Moda e vestuário | roupas, look, styling, lingerie, acessórios, calçados |
| Beleza e autocuidado | maquiagem, skincare, cabelo, cosméticos |
| Bem-estar e fitness | academia, yoga, saúde, rotina, alimentação |
| Viagens e lifestyle | viagem, turismo, hotel, experiências |
| Família e maternidade | filhos, maternidade, casa e relacionamentos |
| Consumo e varejo | preço, loja, cupom, compra, lançamento |
| Sustentabilidade e valores | moda consciente, reciclagem, ética, inclusão |
| Conteúdo comercial | publi, parceria, campanha, embaixadora, código |
| Ruído/fora de escopo | spam, sorteios não relacionados, autopromoção |

A saída mínima é:

```json
{
  "cluster_id": "moda_vestuário",
  "label": "Moda e vestuário",
  "weight": 0.42,
  "evidence_count": 38,
  "representative_terms": ["look", "vestido", "lingerie"],
  "representative_posts": ["post_id_1", "post_id_2"],
  "confidence": 0.88,
  "method": "rules_plus_embeddings_v1"
}
```

A clusterização não deve servir como verdade sobre identidade, gênero ou intenção. Ela é um resumo de conteúdo observado e deve possuir período e cobertura.

### 2.8 Stories e Highlights — proxy com contenção

O Instagram não disponibiliza publicamente o alcance real de Stories de terceiros. Highlights podem ser usados como âncora observável, mas não equivalem diretamente a Stories de 24 horas. O produto deve exibir intervalo e confiança, nunca “alcance real” ou “views garantidos”.

Dados necessários:

```text
followers
highlight_id
highlight_view_count
highlight_age_days
highlight_slide_cohighlight_slide_cohighlight_slide_cohighlight_slide_cohighlight_slide_cohed_video_views
collection_timestamp
```

Pipeline:

```text
1. Coletar 3–5 Highlights elegíveis.
2. Remover Highlights institucionais ou claramente antigos.
3. Corrigir idade e quantidade de slides.
4. Calcular a mediana dos valores corrigidos.
5. Comparar com Reels e Feed públicos.
6. Aplicar fator por faixa de seguidores.
7. Gerar intervalo e nível de confiança.
8. Recalibrar quando a criadora fornecer Insights reais.
```

Fórmula:

```text
F_age = ((age_days + 7) / 7)^(-0.25)
F_slides = 1 / (1 + 0.10 * log1p(slide_count))
HighlightProxy = median(view_count * F_age * F_slides)
ProfileFactor = clip(median_reel_views / followers / story_benchmark_ratio, 0.5, 2.0)
EstimatedStoryViews = HighlightProxy * ProfileFactor
```

Faixas iniciais de views por Story devem ser tratadas como prior: 8%–15% para 1–10 mil seguidores; 4%–10% para 10–50 mil; 2%–6% para 50–100 mil; 1%–4% para 100–500 mil; e 0,5%–3% acima de 500 mil. São referências de engenharia, não observações públicas do perfil.

Confiança:

```text
Confidence =
  0.30*C_age
  + 0.25*C_sample
  + 0.20*C_recency
  + 0.15*C_consistency
  + 0.10*C_crossformat
```

A interface deve escrever, por exemplo: “Views estimados por Story: 4,2 mil–6,8 mil; base: quatro Destaques públicos, Reels e benchmark por porte; confiança: baixa”.

### 2.9 Score de qualidade e normalização

O score é uma camada derivada, nunca substitui o catálogo bruto. Os subíndices iniciais são:

#### Score de ER

```text
q_ER_i = ER_i / ER_benchmark_tier_i
S_ER_i = 100 * percentile_or_logistic(q_ER_i)
```

A função logística deve suavizar extremos e impedir que poucos pontos percentuais acima do benchmark produzam nota artificialmente perfeita. O benchmark do tier deve ser escolhido por `platform`, `niche`, `format`, `period` e `source`.

#### Qualidade da interação

```text
q_i = median_p[(L_p + 3*C_p + 4*S_p + 4*H_p) / F_i]
S_QI_i = 100 * Percentil(q_i)
```

Pesos iniciais: curtida 1; comentário 3; salvamento 4; compartilhamento 4. A variante editorial pesada usa 1, 3, 5 e 5. O score deve ser reduzido por comentários repetitivos, genéricos ou automatizados mediante `text_authenticity_index`.

#### Assiduidade e consistência

```text
S_freq = 100 * clip(f_i / f_target, 0, 1)
CV = sigma(delta_t_i) / mu(delta_t_i)
S_regularity = 100 * exp(-lambda * CV)
S_consistency = 0.6*S_freq + 0.4*S_regularity
S_stability = 100 * (1 - clip(MAD(ER_p) / (ER_median + epsilon), 0, 1))
S_A = 0.5*S_freq + 0.3*S_regularity + 0.2*S_stability
```

#### Qualidade da audiência

```text
S_aud = 0.60*A + 0.20*G + 0.10*D + 0.10*(100 - B)
```

Onde `A` é autenticidade estimada; `G`, estabilidade de crescimento; `D`, adequação demográfica; e `B`, comportamento suspeito/bots. Sem dados confiáveis de afinidade:

```text
S_aud = 0.70*A + 0.20*G + 0.10*(100 - B)
```

Os sinais podem incluir ausência de foto/posts, picos repentinos, relação atípica entre seguidores e interações, follow/unfollow, comentários repetitivos, geografia incompatível e crescimento sem alcance correspondente. O produto deve chamar isso de estimativa, não de classificação definitiva de indivíduos.

#### Nota final

```text
Q_i = 0.40*S_ER_i + 0.20*S_QI_i + 0.15*S_A_i + 0.25*S_aud_i
Nota_i = 1 + 9*(Q_i / 100)
```

Exemplos de calibração: `Q=0` produz nota 1,0; `Q=50`, nota 5,5; `Q=90`, nota 9,1; `Q=100`, nota 10,0. Arredondar apenas na interface; armazenar pelo menos quatro casas decimais. Para objetivos diferentes, pesos iniciais podem ser:

| Objetivo | ER | Qualidade interação | Consistência | Audiência |
|---|---:|---:|---:|---:|
| Conversão/comunidade | 35% | 30% | 25% | 10% |
| Equilíbrio geral | 35% | 25% | 25% | 15% |
| Awareness | 25% | 15% | 20% | 40% |
| Score institucional | 30% | 20% | 20% | 30% |

A parametrização alternativa citada para o benchmark brasileiro é: engajamento normalizado 70%, consistência de frequência 15% e qualidade de storytelling 15%. Essa versão deve ser mantida como perfil de score configurável, não misturada silenciosamente com o score de quatro subíndices.

## 3. Diagnóstico do Estado Atual do Código & Muros de Contenção

### 3.1 Status atual

| Área | Implementação observada | Estado em relação ao benchmark |
|---|---|---|
| View | `app.py` em Streamlit | A UI e o pipeline já estão separados em boa medida; o arquivo deve permanecer View |
| Coleta | `src/scraper.py`, Instaloader fixado, sessão, janela de posts, throttle e fallback | Base compatível; falta contrato de auditoria versionado |
| Cache | `data/cache.db` com `profiles` e `posts_cache` | Base compatível; faltam hash do input, versão de fórmula e validade por métrica |
| Métricas | `src/metrics.py` calcula ER simples e `pod_index` | Cobre base; falta ER por alcance/views, NSS, intenção, Top 3 e clusters |
| Score | `src/scoring.py` calcula score DODÔ com pesos e tiers heurísticos | Deve ser tratado como camada configurável e não como benchmark validado |
| Filtros | `src/filters.py` remove comentários rasos e sinais de publis | Compatível com o muro de contenção do Gemini; deve evoluir para taxonomia completa |
| Gemini | `src/gemini_analyzer.py` classifica comentários em JSON e lotes | Adequado como enriquecimento textual; falta retry 503/backoff e cache por hash |
| Exportação | `src/exporter.py` gera HTML autocontido e PDF via fpdf2 | Funcional para relatório atual, ainda não cobre catálogo canônico |
| Testes | Suíte existente validada com 145 testes aprovados | Manter verde e adicionar fixtures por métrica, fonte, escopo e ausência |

### 3.2 Limites do `src/exporter.py`

O exportador é uma função pura: recebe um dicionário `analysis` e devolve HTML ou bytes de PDF, sem tocar em disco, rede ou `st.session_state`. Essa separação deve ser preservada.

O HTML atual exibe `score_dodo`, `engagement_rate`, janela, gênero predominante, regiões, `pod_index`, taxa de resposta, top repetidores, publis e comentários analisados. O PDF reproduz o mesmo conjunto, usando fonte core Helvetica e `_pdf_safe` para normalizar travessões, aspas curvas, reticências e caracteres fora de Latin-1. O exportador ainda não possui componentes para:

- ER por fórmula e denominador;
- volume, mediana e amostra;
- intenção de compra e taxonomia de comentários;
- NSS e distribuição positiva/negativa/neutra;
- Top 3 posts por volume e qualidade;
- clusterização temática;
- fonte, timestamp, confiança, status parcial e warnings;
- audiência falsa como estimativa explicável;
- Stories/Highlights como intervalo com confiança;
- pesos, versão de score e benchmark de tier.

A evolução deve ser aditiva e orientada por schema. Primeiro, ampliar o objeto canônico `analysis`; depois, adicionar renderizadores HTML/PDF com seções explícitas; por fim, criar testes de conteúdo e regressão de codificação. Não ocultar indisponibilidade preenchendo “0” e não afirmar que um proxy é um dado observado.

### 3.3 Duck-typing do `RealGeminiClient`

O `RealGeminiClient` não precisa implementar uma interface formal para ser usado pelo pipeline. O contrato atual é duck-typed:

```python
response = client.generate_content(prompt)
raw_text = response.text
```

`analyze_batch` recebe qualquer objeto que exponha `generate_content(prompt)` e devolva um objeto com `.text`. Isso permite usar `RealGeminiClient`, cliente fake de testes ou um adaptador futuro sem acoplar a View ao SDK.

O cliente real usa `google-genai`, `types.GenerateContentConfig(response_mime_type="application/json")` e `GEMINI_API_KEY`. A ausência da chave produz degradação graciosa: o painel informa que o serviço de IA não está configurado, mas a auditoria determinística não trava. O limite atual é de até dois lotes de 100 comentários, coerente com a necessidade de controlar cota.

O pipeline deve manter as seguintes invariantes:

1. `app.py` nunca chama o Gemini na thread principal.
2. `filters.is_shallow_comment` roda antes de qualquer prompt.
3. Nenhum comentário raso, emoji isolado ou ruído é enviado.
4. O prompt exige JSON estrito e o parser rejeita respostas fora do contrato.
5. Falhas de quota não podem apagar métricas determinísticas.
6. Resultados do modelo devem possuir `model`, `prompt_version`, `input_hash`, `created_at` e `status`.

### 3.4 Muros de contenção de engenharia

A coleta e as chamadas de API devem rodar em background. `app.py` deve iniciar `threading.Thread`, atualizar um dicionário de estado e fazer polling com `st.rerun()`; nunca deve executar `thread.join()` bloqueante na UI.

Nenhuma chamada de rede deve ocorrer sem consulta prévia ao cache. O cache deve ser mantido para consulta offline; qualquer limpeza precisa de autorização explícita. O documento de segurança local registra que não há rotina autorizada de limpeza automática, embora o código atual exponha `clear_profile_cache` como ação de UI: essa divergência deve ser resolvida com confirmação explícita, auditoria e testes.

Nenhuma dependência paga deve ser introduzida. Segredos como `GEMINI_API_KEY` e `INSTAGRAM_SESSION_FILE` permanecem apenas no `.env`, nunca no frontend nem no Git. Consultas SQLite devem ser parametrizadas. O acesso futuro deve seguir deny-by-default e, quando houver multiusuário, liberar apenas registros associados ao `user_id` autenticado.

A depuração segue diagnóstico de causa raiz: linha exata, causa, teste de regressão e ação corretiva cirúrgica. Não reescrever grandes blocos para contornar um bug sem evidência.

## 4. Arquitetura de Dados, Schemas e Tratamentos de Exceção

### 4.1 Camadas de arquitetura

```text
[Streamlit app.py / View]
          |
          v
[Pipeline assíncrono e estado de auditoria]
          |
  +-------+---------+----------------+
  |                 |                |
  v                 v                v
[Coleta]       [Métricas]       [NLP/Gemini]
  |                 |                |
  +---------> [SQLite cache.db] <---+
                    |
                    v
        [Relatório HTML/PDF / MCP]
```

`app.py` apresenta estado e dispara ações. Skills/Playbooks Markdown definem regras de negócio. `scraper.py` coleta. `metrics.py`, `scoring.py`, `demographics.py` e futuros módulos derivados calculam. `database.py` persiste. `gemini_analyzer.py` enriquece texto somente após filtragem. `exporter.py` serializa a visão final.

### 4.2 Schema de auditoria

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
    "audience_score": null,
    "pod_index": 0.12,
    "text_authenticity_index": null
  },
  "top_posts": {
    "by_volume": [],
    "by_quality": []
  },
  "clusters": [],
  "stories_proxy": {
    "estimated_views_low": null,
    "estimated_views_high": null,
    "confidence": "insufficient"
  },
  "gemini": {
    "status": "not_configured|ok|quota_exceeded|failed",
    "model": null,
    "prompt_version": null,
    "input_hash": null,
    "items": []
  },
  "provenance": [],
  "formula_versions": {},
  "created_at": "2026-08-13T18:00:00Z"
}
```

### 4.3 Persistência e cache

O SQLite deve manter tabelas ou equivalentes para `profiles`, `posts_cache`, `metric_snapshots`, `comment_analysis_cache`, `audience_snapshots`, `formula_versions` e `audit_events`. O cache de cada enriquecimento deve usar hash estável de input, modelo, prompt, versão da Skill e janela. Nenhuma chamada ao Gemini deve ocorrer quando houver resposta válida compatível no cache.

A validade da métrica deve ser independente da validade do perfil: seguidores podem ser atuais e demografia pode estar stale; uma coleta parcial deve informar quais componentes foram atualizados. O fallback pode retornar o último dado válido, mas deve marcar `status=stale` ou `source=cache_fallback`.

### 4.4 Tratamento de erros 429/503 e backoff

Chamadas ao Gemini e a provedores externos devem ser encapsuladas em um adaptador com retry limitado, backoff exponencial e jitter. A regra canônica é:

```text
base_delay = 1.0 segundo
max_retries = 4
retry_delay_k = min(base_delay * 2^k, 30 segundos) + jitter(0, 0.5)
```

Repetir somente erros transitórios:

| Erro | Ação |
|---|---|
| 429 / quota ou rate limit | registrar evento, respeitar `Retry-After` se existir, aplicar backoff, limitar lotes e usar cache/fallback |
| 503 / serviço indisponível | backoff exponencial com jitter, até quatro tentativas, depois degradação graciosa |
| 500 transitório | tratar como potencialmente recuperável, com limite de tentativas |
| 400/401/403 | não repetir cegamente; validar payload, chave, permissão e configuração |
| Timeout/conexão | retry limitado e fallback para cache |
| JSON inválido | não repetir indefinidamente; registrar resposta, marcar lote falho e preservar demais resultados |
| Erro de schema do Instagram | diagnosticar assinatura, tentar fallback aprovado e registrar causa raiz |

O backoff não pode bloquear a UI. O estado deve transitar por `retrying`, `fallback_cache`, `partial` ou `failed`, com mensagem legível. Ao esgotar retries, a View deve continuar exibindo métricas determinísticas e declarar a ausência do componente de IA.

### 4.5 Schema de resposta do Gemini

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

O parser deve rejeitar respostas que não sejam JSON válido, lista de itens ou que não contenham os campos obrigatórios. Itens inválidos podem ser descartados com contagem explícita; nunca devem contaminar o NSS ou a taxa de intenção.

### 4.6 Contrato de fontes e confiança

| `source` | Significado | Confiança padrão |
|---|---|---:|
| `local_public_collection` | Dados públicos coletados localmente | Alta para o que foi observado; limitada para alcance real |
| `verified_insights` | Insights autenticados da própria conta | Alta, sujeita a permissões e atraso |
| `platform_estimate` | Estimativa da ferramenta ou provedor | Média/baixa; mostrar como estimativa |
| `derived` | Cálculo determinístico a partir de dados observados | Depende da cobertura e da fórmula |
| `model_output` | Saída do Gemini ou modelo de qualidade | Média/baixa; explicar método |
| `cache_fallback` | Último valor válido em cache | Stale; exibir data e alerta |
| `unavailable` | Fonte sem dado ou sem permissão | N/A |

## 5. Diretrizes de Interface e Exibição no Streamlit (`app.py`)

### 5.1 Princípio de View estrita

`app.py` é estritamente a View. Não deve conter fórmulas de negócio, regras de filtro, chamadas diretas ao SDK do Gemini ou consultas SQL complexas. A View dispara o pipeline, observa `st.session_state`, mostra progresso, exibe warnings e entrega downloads. Skills e módulos `src/` concentram lógica determinística.

A análise inicia em background. O estado mínimo é:

```python
{
  "status": "ocioso|rodando|retrying|partial|concluido|falhou",
  "etapa": "coleta|metricas|audiencia|nlp|exportacao",
  "progresso": 0.0,
  "audit_id": None,
  "error_code": None,
  "warnings": [],
  "analysis": None
}
```

A UI faz polling/rerun sem `thread.join()`. O usuário deve conseguir cancelar ou aguardar, e uma falha do Gemini não deve esconder o resultado determinístico já calculado.

### 5.2 Ordem recomendada da tela

1. **Cabeçalho da criadora:** nome, handle, plataforma, localização, categorias, seguidores, data e status da coleta.
2. **Resumo decisório:** porte, ER padrão, mediana de interações, volume de posts, qualidade da audiência, NSS, intenção de compra e nota DODÔ — cada item com tooltip de fórmula e origem.
3. **Seletor de escopo:** todo conteúdo, Feed, Reels, Stories, Highlights. Toda mudança deve recalcular ou recuperar cache específico; não misturar séries.
4. **Qualidade da audiência:** seguidores potencialmente inautênticos, curtidas suspeitas, distribuição de pessoas reais/notáveis/massa/suspeitas, reachability e confiança.
5. **Demografia:** gênero, idade, países, cidades e idiomas, com cobertura e período; somas menores que 100% devem ser explicadas.
6. **Conteúdo:** Top 3 por volume e qualidade, ER, views, alcance, comentários, saves, shares e sinais de publi.
7. **Conversa:** volume total, comentários qualificados, intenção, taxonomia, sentimento, NSS e exemplos anonimizados quando permitido.
8. **Afinidade:** clusters temáticos, hashtags, menções, marcas e colaborações.
9. **Stories/Highlights:** intervalo estimado, base, nível de confiança e texto de limitação.
10. **Exportação:** HTML autocontido, PDF, JSON canônico e, futuramente, MCP/CSV para CRM.

### 5.3 Regras de exibição

A UI deve mostrar o valor e a qualificação no mesmo campo. Exemplos: “ER por seguidores — 3,20% — mediana de 12 posts — janela de 90 dias”; “Seguidores potencialmente inautênticos — 23,9% — estimativa — confiança média”; “Views por Story — 4,2–6,8 mil — proxy de Highlights — confiança baixa”.

Não usar “alcance real”, “views garantidos”, “sentimento definitivo”, “seguidor falso confirmado” ou “conversão prevista” quando o sistema possuir apenas proxy. O texto deve diferenciar “observado”, “estimado”, “inferido” e “indisponível”.

A cor nunca deve ser a única codificação de risco. Toda sinalização deve possuir rótulo e tooltip. Os componentes devem ser compactos e densos: tabelas ordenáveis, barras horizontais, cards com origem e links para detalhe. O objetivo é permitir uma decisão rápida sem sacrificar auditabilidade.

### 5.4 Ações e segurança

O botão “Analisar” inicia o pipeline. O botão “Limpar cache e reanalisar” exige confirmação explícita e registra evento; não deve apagar dados de outros perfis. O botão de exportação deve gerar o mesmo `audit_id` e `formula_versions` do relatório exibido.

A aplicação deve operar em deny-by-default. Segredos não aparecem no frontend, e-mail ou sessão são exibidos apenas quando permitidos. Em futura camada multiusuário, filtros por `user_id` devem ser aplicados antes de qualquer leitura.

### 5.5 Critérios de aceite

| ID | Critério |
|---|---|
| B-01 | Toda auditoria possui plataforma, handle, snapshot de seguidores, janela, escopo, fonte e status. |
| B-02 | Toda taxa de engajamento exibe fórmula, denominador, ações, amostra e data. |
| B-03 | ER público, ER por alcance e ER ponderado são campos distintos. |
| B-04 | O sistema apresenta benchmarks por tier com origem; não trata 5%–8% como verdade universal. |
| B-05 | Volume de comentários, intenção, NSS e taxonomia são calculados apenas sobre amostra qualificada. |
| B-06 | Top 3 possui lista por volume e por qualidade, com evidências. |
| B-07 | Clusterização possui termos, posts representativos, peso, método e confiança. |
| B-08 | Stories são intervalo/proxy quando não houver Insights autenticados. |
| B-09 | Exportador HTML/PDF não inventa dados ausentes e preserva warnings/proveniência. |
| B-10 | Gemini recebe somente comentários pós-filtro, responde JSON e usa cache por hash. |
| B-11 | Erros 429/503 usam retry limitado, backoff exponencial, jitter e fallback sem bloquear UI. |
| B-12 | O pipeline permanece resiliente sem `GEMINI_API_KEY`; a análise determinística continua disponível. |
| B-13 | As consultas SQLite são parametrizadas e o cache não é apagado sem autorização. |
| B-14 | Toda alteração passa por teste unitário; a suíte existente deve permanecer verde. |

### 5.6 Roadmap de evolução

A primeira entrega deve consolidar auditoria, ER por seguidores, volume, amostra, cache, proveniência e exportação. A segunda deve adicionar qualidade da audiência, taxonomia de comentários, intenção, NSS e Top 3. A terceira deve adicionar clusters, Stories/Highlights, benchmarks por percentil e score orientado a objetivo. A quarta deve adicionar descoberta, comparação em lote, perfis semelhantes e integração MCP com Sheets/CRM.

Cada fatia deve seguir: ticket; sessão isolada; Skill ou Playbook quando a regra for nova; implementação mínima; teste; relatório de causa raiz se houver bug; atualização de `plan.md`; validação e confirmação. O uso de `/init`, `/compact` e `/clear` é governança de contexto do trabalho, não lógica do produto.

## Referências

[1]: ../DUMMY.md — `DUMMY.md`, Safety Shield e Restrições Negativas do projeto.

[2]: FINDER-VIBECODE-001.md — Guia de Engenharia e Especificação Técnica: Projeto métricaDODÔ.

[3]: ../README.md — README e instruções operacionais do projeto.

[4]: https://www.modash.io/engagement-rate-calculator — Modash, calculadora e benchmarks de taxa de engajamento.

[5]: https://help.modash.io/en/articles/6542471-understanding-engagement-rate-and-how-modash-calculates-it — Modash, entendimento e cálculo de ER.

[6]: https://hypeauditor.com/pt/free-tools/instagram-engagement-calculator/ — HypeAuditor, fórmula e calculadora de ER.

[7]: https://hypeauditor.com/pt/how-calculate-influencer-rankings/ — HypeAuditor, sinais de ranking, autenticidade e consistência.

[8]: https://blog.hypeauditor.com/influencer-landscape-types-of-influencers-and-how-you-can-benefit-from-them/ — HypeAuditor, landscape e benchmarks por porte.

[9]: https://influencermarketinghub.com/influencer-vetting/ — Influencer Marketing Hub, referências editoriais de vetting.

[10]: https://developers.facebook.com/docs/instagram-platform/reference/instagram-media/insights/ — Meta for Developers, Instagram Media Insights.

[11]: https://developers.facebook.com/documentation/instagram-platform/overview — Meta for Developers, visão geral, permissões e limitações da plataforma.

[12]: https://notebook.google.com/notebook/424cafb4-25ad-4d15-bc2c-fd62196c7258 — Caderno NotebookLM citado no material técnico do projeto.
