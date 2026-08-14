# FINDER-002: Benchmark Técnico — Modash & Soluções Open Source de Influência

> **Escopo:** pesquisa complementar ao `FINDER-001.md`, orientada a benchmark funcional, engenharia reversa pública do Modash, repositórios open-source e adaptação local-first para o métricaDODÔ.
>
> **Limite metodológico:** o Modash é uma plataforma proprietária. As páginas públicas descrevem funcionalidades, fontes e alguns sinais de cálculo, mas não expõem todos os pesos, limiares, datasets ou modelos proprietários. Onde a fórmula não é pública, este documento registra a observação e propõe uma alternativa determinística e auditável; não afirma equivalência com o produto comercial.

## 1. Engenharia Reversa do Modash

### 1.1 Mapa funcional público

A superfície pública do Modash apresenta uma base aberta de criadores, descoberta por filtros, busca semântica/visual, vetting, relatórios de perfil, lookalikes, histórico de colaborações, gestão de listas, tracking e pagamentos. O site descreve mais de 380 milhões de perfis públicos pesquisáveis em Instagram, TikTok e YouTube e informa que o conjunto é atualizado várias vezes por mês [1] [2]. A rota autenticada `https://marketer.modash.io/discovery/instagram` foi tratada como interface de produto sujeita a sessão; a análise deste FINDER usa páginas públicas oficiais, documentação e os prints locais do projeto, sem simular autenticação.

| Módulo | Capacidade observada/documentada | Dado de entrada | Saída que o métricaDODÔ pode replicar |
|---|---|---|---|
| **Discovery** | Busca por plataforma, faixa de seguidores, localização da criadora e da audiência, demografia, engajamento, views, crescimento, atividade, palavras-chave, hashtags, menções, tópicos, marcas e colaborações | Query, filtros, perfil público e histórico local | Busca local, filtros explicáveis, shortlist e snapshot de parâmetros |
| **AI Search / Content Search** | Busca por linguagem natural, imagem e “vibe” visual; retorna criadores e conteúdo relevante em uma mesma visão | Texto, imagem de referência, captions, imagens e vídeos públicos | Fallback por regras/termos; Gemini opcional para expansão de intenção; sem dependência paga |
| **Profile Report** | Perfil, audiência, demografia, interesses, ER, views, qualidade da audiência, conteúdo, publis e histórico de marcas | Handle e conteúdo público/Insights quando disponíveis | Relatório canônico com `source`, `status`, `confidence`, janela e evidências |
| **Fake Followers / Audience Quality** | Percentual total de seguidores suspeitos e sinais de comportamento anormal | Amostra de seguidores, perfil e histórico de crescimento | Estimativa explicável por sinais; nunca classificação definitiva |
| **Lookalikes** | Criadores semelhantes por conteúdo/tópicos e semelhantes por audiência/demografia; refinamento por filtros | Perfil-semente e filtros adicionais | Similaridade determinística por atributos e/ou embeddings locais opcionais |
| **Content Search** | Busca por temas, hashtags, mentions, formatos e histórico de conteúdo patrocinado | Posts, captions, media type e marcas | Índice de cobertura temática, Top 3, clusters e conflitos de marca |
| **Brand collaborations** | Linha do tempo de colaborações, formato, marca, data, desempenho e disclosure | Legendas, menções, hashtags e posts públicos | Registro de indício de publi com nível de evidência, sem converter menção em prova |
| **Lists / Workflow** | Salvar resultados, organizar listas, notas e documentos | Perfis e campanhas | Futuro módulo de shortlist; não é necessário para o primeiro slice |
| **Tracking / Campaigns** | Monitorar conteúdo, views, engajamentos, cliques e promo codes em campanhas | Integração/conta autorizada | Fora do escopo público; somente com dados autenticados e consentimento |

O valor de produto não está somente em descobrir perfis. O fluxo conecta **descoberta → vetting → shortlist → outreach → tracking**, mas o núcleo replicável gratuitamente é descoberta local, relatório de perfil, qualidade da audiência, conteúdo e explicabilidade.

### 1.2 Dados originais, derivados e estimados

A página de dados do Modash descreve três etapas: coleta de informações públicas de about sections, captions/descriptions, imagens, vídeos e demais informações públicas; organização desses dados; e análise por modelos de machine learning para gerar crescimento, ER e número de seguidores falsos [2]. A separação abaixo deve ser obrigatória no métricaDODÔ.

| Camada | Exemplos | Tratamento canônico |
|---|---|---|
| **Original/bruto** | handle, nome, bio, localização declarada, foto, captions, hashtags, mentions, data do post, likes, comments, seguidores, views públicas, tipo de mídia, URL | Persistir valor bruto, timestamp, fonte e cobertura |
| **Derivado determinístico** | ER, média/mediana de interações, frequência, Top 3, taxa de comentários qualificados, clusters por regras, score de palavras | Fórmula versionada, fixtures e teste unitário |
| **Estimado por algoritmo** | taxa de seguidores suspeitos, crescimento, reachability, audiência real, similaridade, idade/gênero/localização de audiência | Exibir método, confiança, janela e limitações |
| **Model output** | intenção de compra, sentimento, classe de comentário, expansão semântica e tópicos | JSON estruturado, modelo, prompt, hash e amostra |
| **Autenticado/Insights** | reach, impressions, saves, shares, navigation, link clicks, profile activity, promo codes | `source=verified_insights`; não misturar com proxy público |

O Modash informa que dados de audiência são pseudonimizados/anonymizados e que criadores podem solicitar acesso ou remoção dos dados públicos armazenados [2]. O métricaDODÔ deve adotar a mesma prudência: não persistir uma lista completa de seguidores se uma amostra agregada for suficiente, não inferir identidade individual e suportar remoção por `audit_id`/perfil.

### 1.3 Audience Quality / Fake Followers

A documentação pública do Modash descreve um score de qualidade de audiência baseado em análise de bilhões de contas e em sinais como ausência de foto, relação following/followers, idade da conta, número de posts, ausência de bio e padrões incomuns de crescimento. A página do checker também cita perfis sem posts, nomes genéricos, comentários repetitivos e picos de crescimento como sinais de risco [1] [3]. A plataforma apresenta um percentual total que combina seguidores suspeitos em massa e bots óbvios; os pesos proprietários não são publicados.

No métricaDODÔ, o proxy deve manter os sinais separadamente:

```text
risk_profile =
  0.20*missing_photo
+ 0.15*missing_bio
+ 0.15*following_ratio_anomaly
+ 0.15*account_age_anomaly
+ 0.15*low_post_count
+ 0.20*growth_spike
```

Os pesos acima são um **prior de engenharia**, não uma cópia do Modash. O resultado deve ser `audience_risk_estimate` com intervalo, amostra e confiança. Um perfil somente pode ser classificado como “sinal de risco”; nunca como “fraude confirmada” a partir de uma feature isolada.

A detecção textual complementa a audiência. Comentários genéricos (“Great post”, “Awesome”, “Nice picture”), repetitivos, irrelevantes ou automatizados devem alimentar `comment_authenticity_index`, mas não podem ser simplesmente removidos do volume bruto. O produto deve manter contagens `observed_comments`, `qualified_comments`, `spam_noise_comments` e `repeated_comment_signals`.

### 1.4 Engagement Rate, popularidade e score

O material anterior do projeto referencia a fórmula pública do Modash no Instagram como mediana de curtidas dividida por seguidores [4]. Como a plataforma também comunica filtros de ER e views, o benchmark externo deve ser modelado como uma família de métricas:

```text
ER_F_med = median(likes_i [+ comments_i, se formula_version declarar]) / followers * 100
ER_R      = Σ(likes + comments + saves + shares) / Σ(reach) * 100
ER_V      = Σ(interactions) / Σ(views) * 100
```

O métricaDODÔ não deve alegar que conhece a fórmula completa de popularidade ou de score proprietário do Modash. A alternativa auditável é:

```text
PostPopularity_i =
  percentile(median_adjusted_interactions_i)
+ percentile(views_i)
+ percentile(engagement_rate_i)
- risk_penalty_i
```

O ranking deve existir em duas vistas: por volume absoluto e por qualidade normalizada dentro de tier, nicho, plataforma e formato. A página pública do Modash informa que o report/API pode incluir views, ER, EMV e número de posts em histórico de colaborações [5]. EMV, quando utilizado, deve ser tratado como estimativa comercial de terceiro e não como receita ou ROI observado.

### 1.5 Hierarquia visual e UX

Os prints locais da referência Modash e as páginas públicas indicam uma hierarquia consistente:

1. **Descoberta:** barra de busca, filtros, contagem de resultados, cards de criadores e ações de salvar.
2. **Vetting rápido:** seguidores, ER, views, qualidade da audiência e localização aparecem antes do detalhe textual.
3. **Relatório:** bloco de audiência e demografia, conteúdo recente, Top posts, marcas, interesses/tópicos e alertas.
4. **Comparação:** listas/shortlists, lookalikes e filtros reutilizáveis reduzem o custo de voltar à descoberta.
5. **Ação:** contato público, salvar, exportar, iniciar outreach ou acompanhar campanha — sempre separado da evidência analítica.

O Streamlit do métricaDODÔ deve reproduzir a **priorização**, não o visual proprietário: cards compactos, tabelas ordenáveis, filtros persistentes, tooltips com fórmula e origem, estados de `observed/estimated/unavailable` e warnings visíveis. A interface não deve esconder a incerteza para parecer mais “pronta”.

## 2. Varredura de Projetos Open Source & Repositórios GitHub

A pesquisa foi feita com `gh search repos` e confirmação por `gh repo view`/API de conteúdo. Os resultados de pesquisa literal para “social media bot detection” retornaram principalmente ferramentas de automação ou bypass de bot detection; elas foram excluídas da recomendação por serem incompatíveis com os muros do projeto. O critério de seleção foi: relação com o problema, licença visível quando disponível, código/fonte reprodutível e utilidade como referência — não copiar código automaticamente.

### 2.1 Coleta e monitoramento Instagram

| Repositório | Abordagem | Linguagem/licença observada | Uso recomendado |
|---|---|---|---|
| [`instaloader/instaloader`](https://github.com/instaloader/instaloader) | Download de imagens/vídeos, captions e metadata; perfis, posts e sessão | Python; MIT; 13.119 stars na consulta | Dependência de coleta já fixada no projeto (`4.15.3`); estudar session, throttling, exceptions e testes |
| [`misiektoja/instagram_monitor`](https://github.com/misiektoja/instagram_monitor) | Monitor de atividade, mudanças de perfil, captura e dashboards/notificações | Python; GPLv3; 1.262 stars | Referência de monitoramento, estrutura de testes, Docker e configuração; não incorporar código GPL sem revisão de compatibilidade |
| [`superryeti/Instagram-Follower-Scraper`](https://github.com/superryeti/Instagram-Follower-Scraper) | Scraper de seguidores | Python; licença a revisar | Referência de risco/limites; não usar como base sem revisão de termos e impacto de privacidade |

`Instaloader` é a única recomendação de implementação imediata porque já está no projeto e possui licença MIT. A coleta deve respeitar rate limits, sessão autorizada, backoff, cache e as restrições locais; nenhum repositório é justificativa para contornar autenticação ou anti-bot.

### 2.2 Métricas de engajamento e topic modeling

| Repositório | Abordagem | Linguagem/licença observada | Utilidade |
|---|---|---|---|
| [`Asayesha/Instagram-Engagement-Analysis---NLP-and-topic-modeling`](https://github.com/Asayesha/Instagram-Engagement-Analysis---NLP-and-topic-modeling) | LDA em posts do NatGeo; captions/comments usados em análise de tópicos e previsão experimental | Notebook; licença não identificada; 3 stars | Exemplo de ligação entre tópico e engajamento; baixa maturidade, não usar como benchmark de produção |
| [`MaartenGr/BERTopic`](https://github.com/MaartenGr/BERTopic) | Embeddings, clustering e c-TF-IDF para tópicos interpretáveis | Python; MIT; 7.784 stars | Referência forte para clusters de conteúdo; avaliar custo/memória antes de adicionar dependência |
| [`MaartenGr/BERTopic_evaluation`](https://github.com/MaartenGr/BERTopic_evaluation) | Experimentos e avaliação de BERTopic | Python; MIT; 86 stars | Referência para medir estabilidade/coerência de tópicos |
| [`drob-xx/TopicTuner`](https://github.com/drob-xx/TopicTuner) | Ajuste de HDBSCAN para BERTopic | Python; licença a revisar | Referência de tuning; não necessário no MVP |

A conclusão é usar primeiro a taxonomia determinística do `FINDER-001.md` e somente depois embeddings/BERTopic em modo opcional. A clusterização precisa guardar termos, exemplos, peso, método, período e confiança; não deve depender de um serviço pago.

### 2.3 Bots, spam e qualidade textual

| Repositório | Abordagem | Linguagem/licença observada | Limite de aplicabilidade |
|---|---|---|---|
| [`harvardnlp/botnet-detection`](https://github.com/harvardnlp/botnet-detection) | Dados topológicos e aplicações de GNN para detecção de botnets | Python; MIT; 183 stars | Inspira features de grafo e análise de comportamento; não detecta seguidores Instagram diretamente |
| [`dinever/antispam`](https://github.com/dinever/antispam) | Classificador bayesiano simples de spam | Python; licença não identificada | Baseline textual; revisar licença antes de reutilizar |
| [`Savjee/yt-spam-classifier`](https://github.com/Savjee/yt-spam-classifier) | Pipeline de coleta, rotulagem, treinamento TensorFlow e inferência para spam de comentários | Notebook; MIT; 38 stars | Referência de pipeline e rotulagem; domínio YouTube, não Instagram |
| [`smontanaro/spambayes`](https://github.com/smontanaro/spambayes) | Classificação bayesiana histórica de spam | Python; licença a revisar | Referência conceitual, não dependência do produto |

Não recomendar `SeleniumBase`, `CloakBrowser`, `camofox-browser`, `invisible_playwright` ou repositórios de bypass encontrados na busca. Isso violaria o princípio de coleta responsável e poderia produzir banimento, risco legal ou dados não auditáveis. A análise antifraude do métricaDODÔ deve detectar sinais, não tentar escapar de detecção.

### 2.4 Avaliação de repositórios

| Critério | Pergunta obrigatória antes de reutilizar |
|---|---|
| Licença | A licença permite uso no projeto e distribuição do produto? |
| Segurança | Há secrets, coleta escondida, bypass ou execução remota? |
| Maturidade | Há testes, releases, commits recentes, documentação e issue tracker? |
| Domínio | O dado/rede é Instagram/influencer ou apenas uma analogia? |
| Custo | Introduz API paga, modelo fechado, GPU ou infraestrutura incompatível? |
| Reprodutibilidade | O resultado pode ser obtido localmente e versionado? |
| Compatibilidade | O código conflita com Python, Instaloader, cache e regras do projeto? |

Nenhum resultado GitHub autoriza copiar código ou adicionar dependência automaticamente. A função do FINDER é registrar opções e impactos para decisão posterior na SPEC.

## 3. Adaptação para Arquitetura de Custo Zero (MedeDodô)

### 3.1 Regra de custo e cobertura

A funcionalidade deve operar sem mensalidades, APIs pagas ou limites artificiais por tamanho de conta. **Não criar uma trava que exclua ou degrade perfis acima de 10.000 seguidores**; o que muda por porte é a estratégia estatística, o volume de coleta e a confiança, não a elegibilidade da conta.

A arquitetura de custo zero é:

```text
Dados públicos locais
  -> Instaloader/session/throttle
  -> SQLite cache.db e snapshots
  -> métricas determinísticas e filtros
  -> Gemini Flash opcional, JSON, lotes e cache
  -> Streamlit + HTML/PDF/JSON
```

O produto deve degradar por **disponibilidade de dados**, nunca por uma regra comercial escondida. Se não houver alcance, retorna `unavailable`; se houver apenas Highlights, retorna proxy; se o Gemini estiver sem chave ou quota, mantém ER, volume, score determinístico e exportação.

### 3.2 Substituição funcional do Modash

| Recurso Modash | Implementação sem custo | Nível de equivalência |
|---|---|---|
| Discovery | Coleta local de perfis/postagens, filtros por campos disponíveis, cache e shortlist | Parcial; cobertura depende de sessão e coleta |
| AI Search textual | Busca por campos/termos locais; expansão semântica opcional do Gemini | Parcial; sem índice global de centenas de milhões |
| Visual Search | Fora do MVP; pode usar classificação de imagem somente se o usuário fornecer asset e houver ferramenta local | Futuro |
| Profile Report | Schema canônico, métricas, audiência, conteúdo, publis e warnings | Alto para dados disponíveis |
| Fake Followers | Heurística de sinais + amostra + histórico | Parcial; não é o score proprietário |
| Lookalikes | Similaridade por tier, nicho, tópicos, idioma e audiência observada; embeddings opcionais | Parcial e explicável |
| Content Search | Índice local de captions, hashtags, mentions e clusters | Alto no corpus coletado; baixo fora dele |
| Brand collaborations | Regras de disclosure, mentions, hashtags e evidências de legenda | Parcial; menção não prova publi |
| Tracking | Somente dados autenticados/fornecidos pela criadora | Fora do público |

### 3.3 Camadas Gemini

O Gemini `gemini-flash-latest` é um enriquecedor, não a fonte de verdade. O pipeline deve enviar apenas comentários qualificados e lotes pequenos, exigir `response_mime_type=application/json`, salvar hash/prompt/modelo e usar cache.

O Gemini pode ser usado para: `classe_comentario`, `intencao_compra`, `sentimento`, expansão de query, resumo de tópicos e explicação de risco. Não deve ser usado para inventar alcance, seguidores, demografia ou score bruto. O JSON inválido, 429, 503 e ausência de chave devem gerar estado parcial sem derrubar a View.

### 3.4 Dados e precisão

Cada campo deve declarar:

```text
kind = observed | derived | estimated | model_output | unavailable
source = local_public | verified_insights | cache_fallback | model | platform_estimate
confidence = high | medium | low | insufficient
freshness = timestamp + age_seconds
coverage = sample_size / expected_size, quando aplicável
```

Esse contrato substitui a falsa promessa de “dados precisos” por precisão qualificada. A documentação do Modash afirma que dados são coletados várias vezes por mês; a API de Insights da Meta informa atraso de até 48 horas, retorno vazio quando uma métrica não existe e disponibilidade de Stories por apenas 24 horas em determinados fluxos [2] [6]. O métricaDODÔ deve tornar essas diferenças visíveis.

## 4. Recomendações de Schemas e Componentes para o Claude Code

### 4.1 Extensão de `analysis`

```json
{
  "discovery": {
    "query": "criadoras de moda sustentável no Brasil",
    "filters": {
      "platform": "instagram",
      "followers_min": 1000,
      "followers_max": null,
      "creator_location": ["BR"],
      "audience_location": ["BR"],
      "topics": ["moda sustentável"],
      "brands_include": [],
      "brands_exclude": [],
      "active_within_days": 90
    },
    "sort": "quality_score_desc",
    "saved_search_id": null,
    "collected_at": "2026-08-13T18:00:00Z"
  },
  "profile_report": {
    "handle": "creator_handle",
    "profile_source": "local_public",
    "data_freshness": "2026-08-13T18:00:00Z",
    "coverage": {"posts": 12, "followers_sample": 500},
    "audience_quality": {
      "risk_rate": 0.239,
      "signals": {
        "missing_photo": 0.12,
        "following_ratio_anomaly": 0.08,
        "growth_spike": 0.19
      },
      "confidence": "medium"
    }
  },
  "content_search": {
    "query": "looks terrosos e moda consciente",
    "matches": [],
    "topic_clusters": [],
    "method": "rules_v1",
    "confidence": "medium"
  },
  "lookalikes": {
    "seed_handle": "creator_handle",
    "basis": ["topics", "tier", "audience_location", "engagement_percentile"],
    "results": [],
    "explanations": []
  },
  "provenance": {
    "formula_versions": {},
    "model": "gemini-flash-latest",
    "prompt_version": "comment_analysis_v1",
    "input_hash": "sha256",
    "warnings": []
  }
}
```

Campos `followers_max=null` e ausência de threshold de 10k são intencionais. O backend pode aplicar paginação, budget de coleta e limites de lote, mas não pode transformar esses mecanismos em bloqueio de contas grandes.

### 4.2 Componentes Streamlit

| Componente | Comportamento | Evidência exibida |
|---|---|---|
| Discovery form | Query, plataforma, seguidores, creator/audience location, tópicos, marcas, atividade e sort | Snapshot completo dos filtros |
| Result card | Avatar, handle, seguidores, ER, views, tier, risco e status | Fonte, timestamp e confiança |
| Profile header | Perfil, categorias, localização, bio e freshness | Observado vs inferido |
| KPI row | ER por fórmula, mediana, volume, views, audiência e nota | Tooltip de fórmula/denominador |
| Audience quality | Risk rate, sinais e amostra | “Sinal de risco”, nunca “fraude confirmada” |
| Content tabs | Top 3 volume/qualidade, posts, topics, publis e conflicts | Post ID, data, evidências |
| Conversation | Comercial, afetivo, crítica, spam/ruído, intenção, NSS | Amostra, modelo e confidence |
| Lookalike panel | Seed, basis, results e explicação de similaridade | Campos que causaram o match |
| Provenance panel | Fonte, cache, data, fórmula, prompt, modelo e warnings | Auditoria completa |
| Export buttons | HTML, PDF e JSON do mesmo `audit_id` | Schema e versão preservados |

### 4.3 Critérios de aceite derivados do benchmark

Os critérios abaixo são novos para a evolução de Discovery/FINDER-002 e devem ser convertidos em testes na próxima SPEC:

| ID | Critério verificável |
|---|---|
| F2-01 | O schema distingue `observed`, `derived`, `estimated`, `model_output`, `verified_insights` e `unavailable`. |
| F2-02 | A busca não aplica bloqueio artificial para contas acima de 10.000 seguidores; limites de paginação/lote são transparentes. |
| F2-03 | Um resultado de Discovery guarda query, filtros, ordenação, data e fonte, permitindo reproduzir a shortlist. |
| F2-04 | Audience Quality mostra sinais individuais, amostra, modelo, confidence e não rotula fraude por sinal isolado. |
| F2-05 | Lookalike informa o perfil-semente, a base de similaridade e uma explicação por resultado. |
| F2-06 | Content Search trabalha com captions/hashtags/mentions/topics locais e informa cobertura do corpus. |
| F2-07 | O uso do Gemini é opcional, cacheado, em JSON e nunca substitui métrica determinística. |
| F2-08 | Qualquer dependência open-source incorporada passa por revisão de licença, segurança e compatibilidade com custo zero. |
| F2-09 | O Streamlit expõe freshness, coverage, source, confidence e warnings junto dos KPIs. |
| F2-10 | A ausência de dados retorna `unavailable`/`insufficient`, sem preencher silenciosamente com zero. |

### 4.4 Ordem de implementação recomendada

A primeira fatia deve adicionar o contrato de proveniência e o filtro de Discovery local sem IA. A segunda deve indexar conteúdo e criar Content Search determinístico. A terceira deve criar Audience Quality com sinais e amostra. A quarta deve criar Lookalikes explicáveis por atributos. A quinta pode adicionar embeddings/BERTopic e expansão Gemini, sempre atrás de cache e feature flag. A busca visual fica depois dessas fatias e depende de assets explícitos, sem introduzir serviço pago.

## 5. Matriz de decisão para o métricaDODÔ

| Capacidade | Fazer agora | Fazer depois | Não fazer |
|---|---|---|---|
| ER e volume | Sim, determinístico | Percentis por nicho/plataforma | Score opaco |
| Audience Quality | Heurística explicável | Grafo e histórico | “Fraude confirmada” |
| Topic modeling | Regras locais | BERTopic opcional | Dependência obrigatória de GPU/API |
| Spam | Filtro local + Gemini opcional | Classificador supervisionado próprio | Bypass de anti-bot |
| Lookalikes | Atributos e tópicos | Embeddings locais | API Modash paga |
| AI Search | Query/termos locais | Gemini/embeddings | Prometer cobertura global |
| Visual Search | Fora do MVP | Asset fornecido e pipeline local | Download não autorizado de imagens |
| Tracking | Dados autenticados | Webhooks/integração | Inferir cliques/promo codes |

## 6. Conclusões e decisão de arquitetura

O Modash deve ser tratado como benchmark de experiência e taxonomia, não como dependência. Os maiores diferenciais observados são: filtros por audiência real, busca de conteúdo por intenção visual, relatório de perfil com qualidade de audiência, lookalikes por conteúdo/audiência, histórico de marcas e explicação operacional para marcas.

A réplica de custo zero deve priorizar as partes que são possíveis com dados públicos e locais: coleta responsável, cache, ER, volume, conteúdo, taxonomia, intenção, NSS, clusters, sinais de audiência e exportação. A cobertura é menor que a de uma base comercial global; isso deve ser declarado em `coverage` e `confidence`.

O `FINDER-002.md` é uma fonte de pesquisa e benchmark. Os requisitos F2-01 a F2-10 são a única parte deste documento que deve ser refletida na ISSUE-001, por serem contratos técnicos e critérios verificáveis. A implementação física continuará dependente de SPEC e microissues atômicas.

## Referências

[1]: https://www.modash.io/features/influencer-discovery — Modash, Influencer Discovery: 380M+ perfis, filtros, dados de audiência, autenticidade, collabs e lookalikes.

[2]: https://www.modash.io/data — Modash, metodologia pública de coleta, organização, análise, privacidade e atualização.

[3]: https://www.modash.io/fake-follower-check — Modash, Fake Follower Checker e sinais de contas suspeitas.

[4]: https://help.modash.io/en/articles/6542471-understanding-engagement-rate-and-how-modash-calculates-it — Modash Help, entendimento e cálculo de engagement rate.

[5]: https://www.modash.io/influencer-marketing-api/discovery — Modash Discovery API: filtros, AI search, lookalikes, demographics, reports, collabs, views, ER e EMV.

[6]: https://developers.facebook.com/documentation/instagram-platform/reference/instagram-media/insights — Meta for Developers, Instagram Media Insights: métricas, atraso, Stories, permissões, breakdowns e resposta JSON.

[7]: https://www.modash.io/features/influencer-discovery/ai-search — Modash AI Search: linguagem natural, busca por imagem, conteúdo e filtros de refinamento.

[8]: https://help.modash.io/en/articles/5688853-find-the-perfect-match-using-search-filters — Modash Help, filtros por creator/audience location, demografia, atividade, growth, brands e conteúdo.

[9]: https://www.modash.io/blog/using-influencer-lookalikes-to-search-for-niche-creators — Modash, lookalikes por tópico e por demografia da audiência.

[10]: https://github.com/instaloader/instaloader — Instaloader, coleta de mídia/captions/metadata do Instagram; MIT.

[11]: https://github.com/misiektoja/instagram_monitor — Instagram Monitor; Python; GPLv3.

[12]: https://github.com/MaartenGr/BERTopic — BERTopic; embeddings, clustering e c-TF-IDF; Python; MIT.

[13]: https://github.com/MaartenGr/BERTopic_evaluation — Avaliação experimental do BERTopic; Python; MIT.

[14]: https://github.com/harvardnlp/botnet-detection — Botnet detection topológica/GNN; Python; MIT.

[15]: https://github.com/dinever/antispam — Classificador bayesiano antispam; Python; licença a revisar.

[16]: https://github.com/Savjee/yt-spam-classifier — Pipeline TensorFlow de spam em comentários; MIT.

[17]: https://github.com/Asayesha/Instagram-Engagement-Analysis---NLP-and-topic-modeling — Exemplo de LDA e análise de engajamento em Instagram; licença não identificada.
