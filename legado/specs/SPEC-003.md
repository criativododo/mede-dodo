# SPEC-003: Arquitetura de Informação e UX da Tela de Resultados

**Projeto:** mede-Dodô  
**Sprint:** 003  
**Status:** proposta estrutural para implementação  
**Escopo:** arquitetura de informação, hierarquia, espacialização e componentes funcionais  
**Fora do escopo:** cores hexadecimais, raios, sombras, ícones decorativos, fórmulas, scraping, heurísticas e recalibração estatística

> A tela de resultados deve permitir que uma pessoa responsável por contratar uma influenciadora entenda, em poucos segundos, escala, qualidade do sinal, adequação e próximos pontos de investigação. Os dados continuam completos, porém são revelados por camadas de decisão, evidência e detalhe.

## 1. Visão geral e perfil de leitura

A versão SPRINT 2.1 apresenta boa quantidade de dados, mas mistura resumo, diagnóstico e inventário. O OCR dos painéis atuais mostra, no mesmo fluxo, `Score DODÔ`, parecer de adequação, cinco faixas de KPI, posts, hashtags, parcerias, demografia, comentários, intenção, sentimento e detalhes de auditoria. A versão anterior também expunha longas tabelas de menções e comentários antes do usuário concluir a leitura principal. O problema é de **ordem e escala cognitiva**, não de ausência de dados.

O leitor primário é uma pessoa de marketing ou direção de marca que quer decidir se o perfil merece investigação ou contratação. Ela precisa responder, nesta ordem: quem é o perfil; qual é a dimensão da audiência; o engajamento parece útil; há sinais de risco; o conteúdo combina com a necessidade; que evidências sustentam a leitura. A UI não deve exigir que essa pessoa percorra tabelas técnicas para chegar às respostas.

## 2. Hierarquia de informação

| Nível | Pergunta | Conteúdo | Comportamento |
|---:|---|---|---|
| **1. Resumo imediato** | “O que preciso saber agora?” | Identidade, janela, quatro KPIs hero, Score DODÔ e parecer curto | Sempre aberto no carregamento do resultado |
| **2. Evidência visual** | “Por que essa leitura faz sentido?” | Formatos, Reels, audiência, qualidade, posts e temas | Aberto, porém organizado em dois eixos de decisão |
| **3. Detalhamento** | “Como o dado foi produzido?” | Tabelas, comentários classificados, cobertura, confidence, IDs, warnings e exportações | Recolhido por padrão em `Detalhes da auditoria` |

### 2.1 Nível 1: hero metrics

A primeira zona deve conter quatro hero metrics, organizados em dois pares, sem uma grade de três ou quatro cards:

1. **Seguidores**, escala observada.
2. **Engajamento por seguidores**, valor derivado e denominador explícito.
3. **Autenticidade da audiência**, estimativa com confiança e não acusação.
4. **Respostas da criadora**, percentual da amostra com resposta observada.

O **Score DODÔ** e o parecer de adequação entram em uma faixa de síntese logo após a identidade, sem substituir os componentes que explicam o score. Curtidas médias, comentários médios, comentários qualificados e índice de interação coordenada não entram como hero metrics.

## 3. Macro-wireframe estrutural

```text
┌─────────────────────────────────────────────────────────────────────┐
│ HEADER DO PERFIL                                                    │
│ @handle · porte · janela · data · modo · procedência                 │
├─────────────────────────────────────────────────────────────────────┤
│ RESUMO PARA CONTRATAÇÃO                                              │
│ Score DODÔ | parecer curto | 2–3 sinais que sustentam a leitura       │
├───────────────────────────────┬─────────────────────────────────────┤
│ KPI HERO A                     │ KPI HERO B                         │
│ Seguidores                     │ Engajamento por seguidores         │
├───────────────────────────────┼─────────────────────────────────────┤
│ KPI HERO C                     │ KPI HERO D                         │
│ Autenticidade estimada         │ Respostas da criadora              │
├───────────────────────────────┴─────────────────────────────────────┤
│ FORMATOS E REELS                                                     │
│ Post estático · Reel · views disponíveis · tendência/limite          │
├───────────────────────────────┬─────────────────────────────────────┤
│ QUALIDADE DA AUDIÊNCIA         │ PERFIL DA AUDIÊNCIA                 │
│ interação coordenada, amostra  │ gênero, região, idade, cobertura    │
├───────────────────────────────┴─────────────────────────────────────┤
│ QUALIDADE E CONTEÚDO                                               │
│ Posts de repercussão | Posts de conversão | temas | parcerias        │
├───────────────────────────────┬──────├──────────────────────────────┤
│ COMENTÁRIOS E INTENÇÃO          │ BRAND SUITABILITY                  │
│ intenção, sentimento, amostra   │ parecer, alertas, revisão humana   │
├───────────────────────────────┴─────────────────────────────────────┤
│ [Detalhes da auditoria ▾]                                            │
│ tabelas, logs, fórmulas, IDs, Gemini, warnings, exportações           │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.1 Espacialização

Em desktop, usar uma largura de conteúdo única e duas colunas estruturais, com proporções aproximadas `1.35fr 1fr` quando houver assimetria de evidência. Em áreas simétricas, usar duas colunas iguais. Em viewport estreito, colapsar para uma coluna preservando a ordem vertical. A decisão não é “preencher a tela”, mas criar **respiro entre perguntas diferentes**.

A página deve ter uma sequência linear previsível: identidade, síntese, KPIs, evidências, detalhe. Não inserir uma tabela longa entre os hero metrics e a explicação dos sinais. Não deixar uma coluna crescer muito mais que a outra sem converter o conteúdo em seção de largura total.

## 4. Modelo de componentes

A implementação deve usar componentes canônicos do shadcn/ui ou equivalentes internos, sem adicionar microestilo nesta sprint.

| Zona | Componentes | Uso |
|---|---|---|
| Cabeçalho | `Card`, `Avatar`, `Badge`, `Separator`, `Tooltip` | Identidade, porte, janela, modo e procedência |
| Resumo | `Card`, `Badge`, `Tooltip`, `Alert` | Score, parecer, sinais e ressalvas |
| Hero metrics | `Card`, `Metric/Stats` pattern, `Badge`, `Tooltip` | Valor, unidade, tendência/estado, fonte e cobertura |
| Formatos | `Card`, `Tabs`, `Chart` ou `Progress` | Alternar post/Reels sem duplicar blocos |
| Qualidade | `Card`, `Badge`, `Alert`, `Tooltip`, `Progress` | Sinal coordenado, confiança, amostra e warning |
| Audiência | `Card`, `Chart`, `Tabs`, `Tooltip`, `Empty` | Demografia com cobertura e estado indisponível |
| Conteúdo | `Card`, `Tabs`, `Table`, `Badge` | Rankings, temas, hashtags e parcerias |
| Comentários | `Card`, `Tabs`, `Accordion`, `Table`, `Tooltip` | Resumo aberto, classificações em detalhe |
| Auditoria | `Accordion`, `Collapsible`, `Data Table`, `Badge`, `Alert` | Logs, IDs, fórmulas, warnings e proveniência |
| Ações | `Button`, `Dropdown Menu`, `Toast` | Exportar, ver relatório e gerar novo relatório |

### 4.1 Regras de composição

`Card` representa uma pergunta ou decisão, não cada campo individual. `Badge` comunica procedência ou estado, nunca decoração. `Tooltip` explica denominador, cobertura e limites. `Tabs` separa dimensões equivalentes, como estático e Reels. `Accordion` esconde profundidade sem apagar informação. `Data Table` é reservado a datasets que realmente exigem comparação, ordenação ou paginação.

## 5. Mapeamento para a tela atual

| Estado SPRINT 2.1 | Nova zona | Ação |
|---|---|---|
| Título e formulário | Header/entrada do produto | Manter fluxo; a arquitetura desta SPEC começa após a consulta concluída |
| Score e parecer no topo | Resumo para contratação | Manter, reduzir ruído e conectar sinais ao parecer |
| Faixas de 3, 2 e 4 KPIs | Hero metrics 2×2 | Reagrupar; não recalcular |
| Posts e hashtags em sequência | Qualidade e conteúdo | Colocar em blocos comparáveis, com rankings prioritários |
| Lista longa de parcerias | Qualidade e conteúdo | Mostrar resumo e mover a lista completa para detalhe |
| Demografia | Perfil da audiência | Manter, sempre com cobertura e ressalva adjacentes |
| Comentários e classificação Gemini | Comentários e intenção | Resumo no nível 2; rows em accordion/data table |
| `Detalhes da auditoria` | Detalhamento nível 3 | Manter recolhido e ampliar conteúdo técnico |
| `Ver Relatório`/exportação | Ações finais | Manter depois da confirmação de estado completo |

## 6. Dados ausentes, confiança e procedência

A arquitetura não deve converter indisponibilidade em zero. Todo KPI que chega à camada de apresentação deve carregar ou receber, quando disponível, `kind`, `source`, `confidence`, `coverage`, `freshness` e `status`.

| Estado | Label | Apresentação |
|---|---|---|
| `observed` | observado | Valor lido da fonte |
| `derived` | derivado | Cálculo local sobre observados |
| `estimated` | estimado | Inferência; exige cobertura e confiança |
| `model_output` | modelo | Resultado do Gemini/modelo; exige versão no detalhe |
| `unavailable` | indisponível | Fonte sem dados suficientes; não exibir zero |
| `partial` | parcial | Amostra incompleta; warning visível |

## 7. Conteúdo prioritário versus detalhe

### Sempre visível

Identidade do perfil, janela, data da coleta, quatro hero metrics, Score DODÔ, parecer curto, sinais de suporte, qualidade da audiência, cobertura relevante e status de disponibilidade.

### Visível no segundo nível

Comparação de formatos, posts de maior repercussão, posts com melhor sinal de conversão, temas, hashtags, parcerias resumidas, perfil da audiência, intenção de compra, sentimento e brand suitability.

### Recolhido por padrão

Lista completa de comentários classificados, linhas Gemini, shortcodes, IDs, logs, headers, versões de fórmula, distribuição inteira de tokens, detalhes de cache, warnings históricos e tabela integral de menções. Recolher não significa apagar: os dados seguem exportáveis e consultáveis.

## 8. Critérios de aceite estrutural

| ID | Critério | ID | Critério | ID | Critério | ID | Critério | ID | Critério | ID | Crite detalhamento. |
| SPEC-02 | Os quatro hero metrics aparecem em 2×2, sem grade de três ou quatro cards. |
| SPEC-03 | O resumo de contratação aparece antes de tabelas e inventários. |
| SPEC-04 | A ordem vertical segue identidade → síntese → KPIs → evidências → detalhe. |
| SPEC-05 | Cada componente de decisão informa procedência e, quando aplicável, cobertura/confiança. |
| SPEC-06 | Dados indisponíveis aparecem como `indisponível`, nunca como zero implícito. |
| SPEC-07 | O layout de desktop usa duas colunas estruturais e o estreito colapsa para uma. |
| SPEC-08 | Tabelas longas são recolhidas ou paginadas e não dominam o primeiro viewport. |
| SPEC-09 | As métricas e fórmulas existentes não são alteradas nesta sprint. |
| SPEC-10 | Nenhuma cor, raio, sombra ou pacote de ícones é definido por esta SPEC. |

## 9. Referências

[1]: https://ui.shadcn.com/docs/components/base/data-table — shadcn/ui, guia de Data Table, TanStack Table, sorting, filtering, visibility, pagination e row actions.

[2]: https://tremor.so/ — Tremor, componentes React open-source acessíveis para dashboards e charts, construídos com Tailwind CSS e Radix UI.

[3]: https://posthog.com/docs/product-analytics/insights — PostHog, insights de Trends, Funnels, Retention, Paths, Stickiness, Lifecycle e SQL.

[4]: https://vercel.com/docs/analytics — Vercel Web Analytics, métricas de visitantes, páginas, referrers e demografia.

[5]: https://supabase.com/docs/guides/monitoring-and-debugging/metrics — Supabase Metrics, dashboards e charts para saúde, saturação e operação.

[6]: https://plausible.io/docs/ — Plausible Analytics, dashboard simples e privacy-friendly com estatísticas essenciais.

<<<<<<< HEAD
[7]: `SPRINT-003/SPRINT 2.pdf` — Estado anterior da tela, uma página vertical com 15 painéis de imagem.

[8]: `SPRINT-003/SPRINT 2.1.pdf` — Estado atual analisado, uma página vertical com 7 painéis de imagem.

[9]: `SPRINT-003/BENCHMARK` — 44 prints Modash organizados em macro, micro, nano e plataforma, além do PDF de referência com dados fictícios.
=======
[7]: `docs/finders/evidencias/SPRINT-2.pdf` — Estado anterior da tela, uma página vertical com 15 painéis de imagem.

[8]: `docs/finders/evidencias/SPRINT-2.1.pdf` — Estado atual analisado, uma página vertical com 7 painéis de imagem.

[9]: `docs/finders/evidencias/BENCHMARK-003` — 44 prints Modash organizados em macro, micro, nano e plataforma, além do PDF de referência com dados fictícios.
>>>>>>> worktree-mede-dodo-sprint003

## 10. Complemento de implementação

Para referências simples, componentes shadcn/ui reutilizáveis, receitas de `Card`, `Data Table`, `Accordion`, estados vazios e sequência de adaptação via MCP, consultar [`FINDER-001.md`](./FINDER-001.md). Este complemento não altera a arquitetura definida nesta SPEC; ele reduz a pesquisa necessária para a implementação.
