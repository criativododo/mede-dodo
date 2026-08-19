# FINDER-001: Referências simples e componentes reutilizáveis para o MVP

**Sprint:** 003  
**Função:** complemento visual e técnico do `FINDER-003.md`  
**Público:** Claude Code e agente conectado ao MCP do projeto  
**Escopo:** referências de estrutura, componentes shadcn/ui prontos para adaptação e sequência de implementação  
**Não é:** um layout final, um novo Design System ou autorização para alterar métricas e pipeline

> O objetivo deste Finder é reduzir o trabalho de decisão do agente de código. Cada referência abaixo responde a uma necessidade concreta do MVP: resumir métricas, revelar evidência sob demanda, organizar tabelas e tratar estados vazios/parciais. Usar apenas a estrutura necessária; não importar templates inteiros.

## 1. Decisão do MVP

A tela de resultado deve ser uma página simples em três camadas:

```text
[Perfil + janela + estado]
[Resumo para contratação]
[4 hero metrics em 2×2]
[Qualidade da audiência] [Perfil da audiência]
[Posts e temas]          [Parcerias e comentários]
[Detalhes da auditoria ▾]
[Exportação]
```

O padrão de composição é inspirado em dashboards de analytics, mas a implementação deve permanecer menor que um dashboard administrativo completo. O agente deve copiar/adaptar componentes individuais, não clonar sidebar, navegação, billing, autenticação ou páginas de marketing.

## 2. Referências selecionadas

| Referência | O que aproveitar | O que não trazer para o MVP | Licença/uso |
|---|---|---|---|
| [shadcn/ui Blocks](https://ui.shadcn.com/blocks) | Sequência `SectionCards → Chart → DataTable`, cards de resumo, tabela abaixo da evidência e composição responsiva | Sidebar administrativa, navegação de produto e grade genérica de três cards | Open source/open code na documentação; revisar arquivos copiados |
| [shadcn/ui Dashboard Example](https://ui.shadcn.com/examples/dashboard) | Shell simples, header, separator, colapso de navegação e content area | Não copiar o dashboard inteiro nem seu tema | Referência oficial de composição; usar componentes do registry |
| [shadcn/ui Data Table](https://ui.shadcn.com/docs/components/base/data-table) | Table + TanStack Table, colunas, sorting, filtering, pagination, visibility e row actions | Não usar tabela para todo o relatório; não abrir 2.668 comentários no primeiro viewport | Documentação oficial; validar versão e licença das dependências |
| [Tremor Insights](https://blocks.tremor.so/templates#template-insights) | Página de insights, filtros simples, tabelas com TanStack, estados de análise e composição headless | Não trazer dark mode, charts avançados ou todos os templates | Referência open source; verificar licença do código adotado |
| [Tremor Overview/Dashboard](https://tremor.so/) | KPI cards, charts somente quando respondem uma pergunta e blocos modulares | Não substituir shadcn nem adicionar uma segunda linguagem visual | Usar como referência estrutural, não como dependência obrigatória |
| [Origin UI](https://originui.com/) | Accordion, Alert, Collapsible, Empty, Progress, Skeleton, Tabs, Tooltip e estados de formulário | Não importar catálogo inteiro nem novo sistema visual | Referência de componentes; revisar licença antes de copiar código |
| [PostHog Insights](https://posthog.com/docs/product-analytics/insights) | Separação por pergunta: Trends, Funnels, Retention, Paths e Lifecycle | Não implementar esses tipos analíticos; usar somente a ideia de uma pergunta por bloco | Referência de arquitetura analítica |
| [Vercel Analytics](https://vercel.com/docs/analytics) | Agregação inicial e dimensões secundárias como páginas, referrers e demografia | Não copiar navegação ou terminologia de produto | Referência de hierarquia |
| [Plausible](https://plausible.io/docs/) | Dashboard essencial, escaneável e sem submenus excessivos | Não trocar o relatório por navegação profunda | Referência de simplicidade |
| [Supabase Metrics](https://supabase.com/docs/guides/monitoring-and-debugging/metrics) | Separar visão de saúde/estado dos gráficos e detalhes operacionais | Não incluir logs técnicos acima do resumo | Referência de estados e investigação |

### 2.1 Escolha recomendada

Para o MVP, a composição recomendada é **shadcn/ui Blocks + shadcn Data Table + componentes de estado do shadcn/ui**. Tremor entra apenas como referência de KPI/chart caso o agente precise de um padrão pronto de visualização. Origin UI serve como catálogo de estados, não como dependência obrigatória.

## 3. Catálogo de componentes shadcn/ui para utilizar

A tabela é uma receita de implementação. O agente pode adicionar apenas os componentes necessários ao projeto, preservando os tokens do Design System Dodô já documentados em `SPEC-001.md`.

| Componente | Zona do relatório | Implementação sugerida |
|---|---|---|
| `Card` | Resumo, hero metrics e seções | Um card por pergunta; não um card por campo |
| `Badge` | `observado`, `derivado`, `estimado`, `modelo`, `parcial`, `indisponível` | Badge junto do label e não apenas em auditoria |
| `Tooltip` | Denominador, cobertura, confiança e termos técnicos | Texto curto; acessível por foco |
| `Alert` | Parecer, risco, estado parcial e ação necessária | Sempre com título textual, não somente cor |
| `Separator` | Separar header, resumo, evidência e detalhe | Usar como ritmo de leitura |
| `Tabs` | Posts/Reels e dimensões equivalentes | Não usar Tabs para esconder o resumo principal |
| `Accordion` | Comentários, Gemini e detalhes de auditoria | Começar recolhido para listas extensas |
| `Collapsible` | `Detalhes da auditoria` e tabelas secundárias | Manter o conteúdo disponível sem empurrar o primeiro viewport |
| `Table` | Resumos de três a cinco linhas | Para listas pequenas e estáticas |
| `Data Table` | Top posts, parcerias, comentários e menções longas | Usar TanStack Table com filtro, sorting, pagination e visibility |
| `Chart` | Tendência, formatos, audiência quando houver dados | Gráfico somente quando existe série ou comparação válida |
| `Progress` | Cobertura, confiança ou progresso de análise | Não usar para dar aparência de precisão a uma estimativa |
| `Empty` | Sem Reels, sem views, sem comentários classificados | Mensagem explica ausência; nunca renderizar zero silencioso |
| `Skeleton` | Carregamento de cards e tabelas | Reservar espaço para evitar layout shift |
| `Button` | Gerar, Ver Relatório, exportar, novo relatório | Uma ação primária por zona |
| `Dropdown Menu` | Exportações e ações secundárias | Não esconder a decisão principal |
| `Toast` | Confirmação de exportação, cache e ação concluída | Não usar para warnings que precisam permanecer visíveis |

## 4. Implementações prontas para adaptação

### 4.1 Hero metric

Adaptar o padrão de `SectionCards` dos Blocks para quatro cards em 2×2. O contrato mínimo de cada card é:

```ts
type HeroMetric = {
  label: string
  value: string
  kind: "observed" | "derived" | "estimated" | "model_output" | "unavailable"
  source?: string
  coverage?: string
  confidence?: string
  helper?: string
}
```

O card não deve recalcular o valor. Ele recebe o `analysis` existente, escolhe a formatação conforme `status` e renderiza badge, valor e microcopy.

### 4.2 Data Table de evidência

Adaptar o guia oficial do shadcn Data Table com tipos específicos do relatório:

```ts
type EvidenceRow = {
  id: string
  label: string
  value: string
  kind: "observed" | "derived" | "estimated" | "model_output"
  coverage?: number
  confidence?: string
  source?: string
}
```

Ativar somente as features necessárias: ordenação, filtro, paginação e visibilidade de colunas. Para comentários, começar com uma página pequena e deixar colunas técnicas ocultas por padrão. Para parcerias, mostrar perfil, ocorrências e tipo; manter o aviso de que menção isolada não comprova publicidade.

### 4.3 Audit Accordion

Compor `Accordion` ou `Collapsible` com estes itens, nesta ordem:

```text
Detalhes da auditoria
├── Metodologia e fórmulas
├── Procedência, janela e cobertura
├── Itens classificados pelo modelo
├── Warnings e dados parciais
├── IDs, shortcodes e logs resumidos
└── Exportar HTML, PDF e JSON
```

O conteúdo técnico não deve ser removido do relatório; apenas sai da camada de decisão.

### 4.4 Estado vazio e parcial

Usar `Empty` para `sem views de Reels`, `sem dados demográficos`, `sem comentários classificados` e `sem série temporal`. O texto obrigatório é: **“A fonte não forneceu dados suficientes. Indisponível não significa zero.”** Para dados parciais, usar `Alert` com causa, cobertura e ação seguinte.

### 4.5 Filtros e tabs

Usar `Tabs` somente para grupos equivalentes: `Todos`, `Posts`, `Reels` ou `Resumo`, `Detalhes`. Não transformar cada seção em uma aba independente. Quando houver filtro de período ou conteúdo, manter o filtro visível no cabeçalho da seção e refletir a janela no label do resultado.

## 5. Receita de uso para Claude Code/MCP

O agente conectado ao MCP deve seguir a sequência abaixo:

```text
1. Ler SPEC-003.md e FINDER-001.md.
2. Inspecionar a árvore do projeto e o package manager já existente.
3. Verificar se shadcn/ui e Tailwind já estão configurados.
4. Adicionar somente Card, Badge, Tooltip, Alert, Separator,
   Tabs, Accordion/Collapsible, Table, Chart, Progress, Empty,
   Skeleton, Button e Dropdown Menu necessários.
5. Implementar um shell estático com dados fictícios.
6. Validar a hierarquia visual em 1440px e viewport estreito.
7. Ligar os componentes ao analysis existente, sem mudar cálculo.
8. Abrir detalhes e exportação apenas por ação explícita.
9. Rodar lint, typecheck e testes existentes.
10. Comparar a tela com SPEC-003, não com uma cópia do benchmark.
```

O comando de adição deve ser adaptado ao package manager e à versão já instalada. Exemplo orientativo, não execução automática:

```bash
pnpm dlx shadcn@latest add card badge tooltip alert separator tabs accordion collapsible table chart progress skeleton button dropdown-menu
```

Não adicionar todos os componentes por conveniência. Se o projeto atual não for React/Tailwind, mapear cada componente para o equivalente já existente ou registrar a migração como decisão separada. O Finder não autoriza trocar o framework nesta sprint.

## 6. Como decidir se uma referência entra no MVP

| Pergunta | Se sim | Se não |
|---|---|---|
| Resolve uma pergunta do tomador de decisão? | Considerar | Não priorizar |
| Tem componente pequeno e isolável? | Adaptar | Evitar template completo |
| Funciona sem alterar o `analysis`? | Priorizar | Deixar para outra sprint |
| Possui licença clara ou documentação oficial? | Registrar e revisar | Não copiar código |
| Preserva estados de indisponível/parcial? | Priorizar | Não usar como padrão |
| Mantém o primeiro viewport escaneável? | Priorizar | Rejeitar |

## 7. Guardrails

O agente **não deve** importar sidebar, login, billing, autenticação, dark mode, charts decorativos, ícones de negócio ou navegação de um template externo. Não deve substituir o Design System Criativo Dodô, alterar cores nesta sprint, criar métricas novas, mudar fórmulas, recalibrar heurísticas, mudar scraping, remover exportações ou esconder dados sem expor `Detalhes da auditoria`.

Os componentes são referências de implementação, não dependências obrigatórias. Toda cópia de código exige revisão de licença, versão, segurança e bundle. O MCP pode acelerar a adaptação, mas a decisão de qual componente entra continua limitada por `SPEC-003.md`.

## 8. Referências

[1]: https://ui.shadcn.com/blocks — shadcn/ui Blocks: building blocks open source, Section Cards, Chart e Data Table.

[2]: https://ui.shadcn.com/examples/dashboard — shadcn/ui Dashboard Example: shell, header, sidebar e content area.

[3]: https://ui.shadcn.com/docs/components/base/data-table — shadcn/ui Data Table: TanStack Table, sorting, filtering, pagination, visibility e row actions.

[4]: https://tremor.so/ — Tremor: componentes React para dashboards, charts e KPI cards.

[5]: https://blocks.tremor.so/templates#template-insights — Tremor Insights: reporting tool, filtros e composição com TanStack Table.

[6]: https://originui.com/ — Origin UI: catálogo de componentes de estado, formulário, collapsible, empty, progress, skeleton e tooltip.

[7]: https://posthog.com/docs/product-analytics/insights — PostHog Insights: organização por pergunta analítica.

[8]: https://vercel.com/docs/analytics — Vercel Analytics: agregação e dimensões secundárias.

[9]: https://plausible.io/docs/ — Plausible: dashboard essencial e escaneável.

[10]: https://supabase.com/docs/guides/monitoring-and-debugging/metrics — Supabase Metrics: saúde, saturação, dashboards e alertas.

[11]: https://github.com/Kiranism/next-shadcn-dashboard-starter — Starter open source de dashboard Next/shadcn com licença MIT observada na pesquisa.

[12]: https://github.com/shadcnstore/shadcn-dashboard-landing-template — Template open source shadcn com licença MIT observada na pesquisa.

[13]: https://github.com/shadcndashboard/next-shadcn-dashboard — Starter Next/shadcn com licença MIT observada na pesquisa.
