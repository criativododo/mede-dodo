# SAIDA-MANUS: Handoff Executivo para Claude Code

**Sprint:** 003  
**Objetivo:** reorganizar a tela de resultados do mede-Dodô por arquitetura de informação, sem mexer no motor de dados.  
**Documento de execução:** `SPEC-003.md`  
**Catálogo de referências:** `FINDER-003.md`

## 1. Resumo executivo

A SPRINT 2.1 já apresenta dados suficientes, mas o usuário precisa atravessar muitas camadas para entender o resultado. A tela mistura hero metrics, score, parecer, rankings, hashtags, parcerias, demografia, comentários e auditoria em uma sequência vertical densa. A versão anterior tinha ainda mais tabelas abertas. O problema principal é a falta de ordem cognitiva.

A SPRINT-003 define uma tela de resultado em três níveis:

1. **Resumo imediato:** identidade, janela, Score DODÔ, parecer e quatro hero metrics.
2. **Evidência:** formatos, qualidade da audiência, perfil de audiência, conteúdo, comentários e adequação.
3. **Detalhamento:** tabelas, logs, itens Gemini, fórmulas, IDs, warnings e exportações.

O eixo estrutural é uma página linear com duas colunas em desktop e uma coluna em viewport estreito. O objetivo é aumentar escaneabilidade, não reduzir o catálogo de dados.

## 2. Diretrizes de implementação

### 2.1 Preparação

Leia `SPEC-003.md` e `FINDER-003.md` antes de alterar código. Inspecione o estado atual do `app.py`, preserve as funções de cálculo e altere somente a camada de renderização. Não implemente enquanto a SPEC não estiver aprovada.

### 2.2 Estrutura de renderização

Mapeie a tela para funções equivalentes às seguintes, reutilizando os dados já presentes no `analysis`:

```text
_render_report_page(analysis, state)
├── _render_profile_header(analysis, state)
├── _render_decision_summary(analysis)
├── _render_primary_kpis(analysis)
├── _render_format_performance(analysis)
├── _render_audience_quality(analysis)
├── _render_content_quality(analysis)
├── _render_audience_profile(analysis)
├── _render_comment_reading(analysis, gemini_configurado)
├── _render_audit_details(analysis, state)
└── _render_export_actions(analysis)
```

A função de página deve substituir a dispersão atual de `st.columns(3)`, `st.columns(2)` e `st.columns(4)` no topo por quatro hero metrics em uma matriz 2×2. A composição pode usar duas colunas com pesos iguais ou `1.35fr 1fr` em blocos assimétricos. O layout deve colapsar para uma coluna em telas estreitas.

### 2.3 Ordem de montagem

Implemente na ordem abaixo, validando a tela a cada bloco:

| Passo | Bloco | Componentes funcionais |
|---:|---|---|
| 1 | Header do perfil | Card, Avatar se disponível, Badge, Separator, Tooltip |
| 2 | Resumo para contratação | Card, Alert, Bad| 2 | Resumo para contratação | Card, Aard/Metric, Badge, Tooltip |
| 4 | Formatos e Reels | Card, Tabs, Chart/Progress, Empty |
| 5 | Qualidade da audiência | Card, Alert, Badge, Progress, Tooltip |
| 6 | Perfil da audiência | Card, Chart, Tabs, Empty |
| 7 | Conteúdo e rankings | Card, Tabs, Table/Data Table, Badge |
| 8 | Comentários e intenção | Card, Accordion, Table/Data Table, Tooltip |
| 9 | Auditoria | Accordion/Collapsible, Data Table, Alert |
| 10 | Exportação | Button, Dropdown Menu, Toast |

### 2.4 Labels obrigatórios

Use estes labels na camada visível, preservando as chaves internas:

- `Seguidores`
- `Engajamento por seguidores`
- `Autenticidade da audiência (estimativa)`
- `Respostas da criadora`
- `Score DODÔ`
- `Sinal de interação coordenada`
- `Perfil da audiência (estimativa)`
- `Posts de maior repercussão`
- `Posts com melhor sinal de conversão`
- `Temas que mais aparecem`
- `Parcerias identificadas`
- `Comentários e intenção`
- `Detalhes da auditoria`

Não usar `Antifraude` como título de decisão, `Índice de pods` como KPI principal ou `Seguidores potencialmente inautênticos` como acusação. Esses significados aparecem como explicação, sinal e estimativa.

### 2.5 Procedência e ausência

Cada card de decisão deve mostrar badge de tipo quando o campo estiver disponível: `observado`, `derivado`, `estimado`, `modelo`, `parcial` ou `indisponível`. O texto `indisponível` deve explicar ausência de dado e nunca ser formatado como zero. `coverage`, `confidence`, `freshness` e `source` devem ficar no card ou em tooltip, com cópia integral em `Detalhes da auditoria`.

### 2.6 Microcopy de produto

Use os textos abaixo sem encurtar a ponto de perder a ressalva:

> “Um pod é um grupo de contas que interage de forma repetida e concentrada para elevar artificialmente os sinais de engajamento. Este card mostra um alerta de padrão, não uma acusação.”

> “Percentual dos comentários analisados que permitiu estimar este indicador. A cobertura não representa automaticamente toda a base de seguidores.”

> “Estimativa heurística baseada nos sinais observados nesta amostra. Não equivale a uma auditoria comercial externa e não deve ser lida como prova isola> “Estimativa heurística bneceu dados suficientes. Indisponível não significa zero.”

### 2.7 Tabelas e detalhe

Use `Data Table` quando houver lista longa com necessidade de paginação, filtro, ordenação ou visibilidade de colunas. Use `Table` simples para três a cinco linhas de resumo. Use `Accordion`/`Collapsible` para comentários classificados, IDs, logs, fórmulas, dados Gemini e warnings. O primeiro viewport não deve ser dominado por menções, linhas de comentários ou shortcodes.

## 3. Restrições negativas, Safety Shield

Claude Code **não deve**:

1. Alterar fórmulas de ER, TER, NSS, Score DODÔ, PostScore, intenção, sentimento ou clusterização.
2. Alterar heurísticas de scraping, pacing, sessão, cache, Gemini, schemas ou exportadores.
3. Criar métricas novas porque um benchmark externo as apresenta.
4. Copiar a aparência do Modash, Tremor, PostHog, Vercel ou Supabase.
5. Introduzir uma grade de três ou quatro hero metrics.
6. Deixar tabelas técnicas abertas acima dos hero metrics.
7. Transformar `indisponível` em zero ou ocultar a falta de cobertura.
8. Tratar estimativa de autenticidade ou sinal de interação coordenada como prova de fraude.
9. Colocar todos os dados em tabs sem um resumo inicial escaneável.
10. Adicionar cores, tokens, raios, sombras ou ícones decorativos nesta sprint.
11. Instalar uma biblioteca ou copiar um repositório sem revisar licença, dependências e necessidade.
12. Remover exportação HTML/PDF/JSON, estado de erro, modo demonstração12. Remover exportação HTML/PDF/JSON, eterar `app.py` antes de a SPEC ser aprovada.
14. Criar novas chamadas de rede ou mudar a camada de coleta durante a implementação visual.

## 4. Critérios de pronto

A implementação só pode ser considerada pronta quando:

- os quatro hero metrics estão em 2×2;
- a sequência de leitura é identidade → síntese → KPIs → evidências → detalhe;
- o primeiro viewport não contém tabelas longas;
- cada inferência mostra tipo, cobertura e confiança quando disponíveis;
- `indisponível` não aparece como zero;
- o detalhe continua acessível e exportável;
- o desktop usa duas colunas e a versão estreita usa uma;
- a fórmula e o pipeline continuam iguais;
- os estados de erro, demo, progresso, exportação e novo relatório continuam funcionais;
- a validação visual é feita em dados fictícios antes de consultar uma conta real.

## 5. Referências de trabalho

<<<<<<< HEAD
- [SPEC-003.md](./SPEC-003.md), contrato estrutural completo.
- [FINDER-003.md](./FINDER-003.md), benchmark local e pesquisa externa.
=======
- [SPEC-003.md](../../specs/SPEC-003.md), contrato estrutural completo.
- [FINDER-003.md](../finders/FINDER-003.md), benchmark local e pesquisa externa.
>>>>>>> worktree-mede-dodo-sprint003
- [shadcn/ui Data Table](https://ui.shadcn.com/docs/components/base/data-table), referência de tabela com sorting, filtering, pagination e column visibility.
- [Tremor](https://tremor.so/), referência de componentes de dashboard e charts.
- [PostHog Insights](https://posthog.com/docs/product-analytics/insights), referência de separação por tipo de pergunta analítica.
- [Vercel Analytics](https://vercel.com/docs/analytics), referência de agregação por dimensões.
- [Supabase Metrics](https://supabase.com/docs/guides/monitoring-and-debugging/metrics), referência de dashboards operacionais e alertas.
- [Plausible Analytics](https://plausible.io/docs/), referência de dashboard essencial e escaneável.

## 6. Nota de pesquisa

A pesquisa web e GitHub foi realizada nesta execução. O conector Perplexity estava configurado, porém desabilitado, e não foi alterado. As conclusões foram trianguladas com documentação oficial e metadados públicos de repositórios. Nenhuma implementação de código foi feita como parte deste handoff.

## 7. Complemento de implementação: FINDER-001

<<<<<<< HEAD
Antes de escolher uma biblioteca ou copiar um bloco, consulte [`FINDER-001.md`](./FINDER-001.md). Use primeiro os componentes shadcn/ui isolados e as receitas de MVP registradas ali. Não importe templates completos, sidebar, autenticação, billing ou uma segunda linguagem visual.
=======
Antes de escolher uma biblioteca ou copiar um bloco, consulte [`FINDER-001.md`](../finders/FINDER-001.md). Use primeiro os componentes shadcn/ui isolados e as receitas de MVP registradas ali. Não importe templates completos, sidebar, autenticação, billing ou uma segunda linguagem visual.
>>>>>>> worktree-mede-dodo-sprint003

## 8. SPEC-004, direção de arte soberana

A implementação visual da tela do relatório deve seguir `SPEC-004.md` antes de qualquer alteração no `app.py`. A SPEC-004 foi construída a partir da captura real `FireShot Capture 021`, do Brandbook e dos tokens do Design System Criativo Dodô.

### 8.1 Ordem obrigatória

1. Corrigir contraste dos botões: fundo `#810100`, texto `#FFFFFF`, estados hover/focus/disabled legíveis.
2. Criar superfícies de card com Cannoli, superfície `#F5F4EC`, borda `1px solid #E5E0D8`, raio editorial 12px e sombra suave.
3. Preservar a matriz 2×2 dos hero metrics e compactar `2.218.990` para `2.2M` no hero.
4. Trocar URLs cruas e shortcodes por `Ver post ↗`, `Post 01` ou handle, mantendo o href e o ID no detalhe.
5. Converter parcerias para lista/mini-cards com perfil, tipo e ação, limitando o resumo e recolhendo o inventário.
6. Trocar tabelas de `0.0%` por card `Indisponível` quando não houver classificação Gemini.
7. Manter `Detalhes da auditoria` recolhido, com fórmulas, IDs, logs, warnings e exportações.

### 8.2 Guardrails

Não alterar cálculo, coleta, score, schemas, Gemini, sessão ou exportadores. Não criar cor nova, não usar branco puro como superfície, não introduzir gradiente, não copiar um template inteiro e não redesenhar a marca. A implementação deve reutilizar os componentes indicados em `FINDER-001.md` e preservar a ordem de `SPEC-003.md`.

### 8.3 Critério de conclusão

A entrega visual está pronta somente quando os checklists da seção 9 de `SPEC-004.md` estiverem cumpridos em desktop, viewport estreito, dados fictícios e no caso `@silviabraz`. O estado sem comentários Gemini deve ser validado separadamente para confirmar que indisponibilidade não vira zero.
