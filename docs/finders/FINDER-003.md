# FINDER-003: Benchmarks de Dashboards Analíticos e Open Source

**Sprint:** 003  
**Objetivo:** registrar os padrões aproveitáveis para reorganizar a tela de resultados do mede-Dodô.  
**Princípio:** usar o benchmark para aprender ordem, densidade e interação, não para copiar a complexidade de uma ferramenta de mercado.

## 1. Síntese da pasta local `SPRINT-003/BENCHMARK`

A pasta contém **44 prints PNG** e um PDF vertical de referência. Os prints estão organizados em seis perfis/áreas: macro `@silviabraz`, micro `@barbarastudart`, `@manurefosco` e `@robertapfranco`, nano `@caroline_tanaka` e `@juuchika`, além de `plataforma`. O conjunto serve para observar a densidade e a ordem dos módulos de uma ferramenta de análise de influenciadoras, não para importar seus cálculos ou identidade visual.

| Grupo local | O que foi observado/aproveitado | Aplicação no mede-Dodô |
|---|---|---|
| Macro `@silviabraz` | Densidade de perfil grande, visão agregada, filtros e leitura de audiência | Separar escala de interpretação e manter o resumo independente da tabela |
| Micro `@barbarastudart` | Perfil compacto e leitura de qualidade/conteúdo | Priorizar poucos sinais com contexto em vez de inventário extenso |
| Micro `@manurefosco` | Variabilidade de cards e rankings | Usar blocos comparáveis e critério explícito de ranking |
| Micro `@robertapfranco` | Relação entre público, conteúdo e performance | Agrupar métricas por pergunta de decisão |
| Nano `@caroline_tanaka` | Escala menor e limites de cobertura | Mostrar `cobertura` e `indisponível` próximo ao valor |
| Nano `@juuchika` | Necessidade de leitura compacta para amostra pequena | Não transformar ausência de amostra em diagnóstico forte |
| `plataforma` | Navegação, contexto de produto e organização de módulos | Usar uma página linear de relatório, sem replicar navegação extensa |
| PDF de referência | Exemplo de relatório vertical com dados fictícios | Usar como comparação de densidade e não como fonte de verdade matemática |

### 1.1 Padrões aproveitáveis

O benchmark indica uma família de módulos recorrentes: cabeçalho do perfil, escala/audiência, engagement, formatos, qualidade da audiência, conteúdo/rankings, demografia, brand suitability, parcerias e detalhes. O ganho não está em expor todos esses módulos simultaneamente. Está em ordenar cada camada e mostrar cobertura quando o dado é inferencial.

Os prints também evidenciam a utilidade de badges de procedência, estados de qualidade e filtros contextuais. O produto local deve adotar a ideia de procedência `observado`, `derivado`, `estimado`, `modelo`, `parcial` e `indisponível`, mas manter o vocabulário e a simplicidade do Dodô.

### 1.2 Problemas confirmados na versão atual

O OCR da SPRINT 2.1 mostra que o primeiro fluxo já começa com `Score DODÔ` e parecer, mas depois percorre blocos sucessivos de KPIs, conteúdo, hashtags, parcerias, audiência, comentários e auditoria. A versão anterior possuía uma lista ainda mais longa de menções e comentários. Em ambos os casos, o usuário é obrigado a atravessar detalhe antes de formar uma leitura de contratação. O problema é hierárquico: o conteúdo existe, mas não possui uma sequência de decisão suficientemente explícita.

## 2. Pesquisa de padrões externos

### 2.1 Tremor

O Tremor se posiciona como biblioteca de componentes React open-source e acessíveis para dashboards e charts, construída com Tailwind CSS e Radix UI. A página pública destaca componentes modulares, KPI cards, filtros, charts, `BarList`, `Tracker` e templates de report/insights [1].

**Padrão aproveitado:** um KPI deve ser uma unidade semântica com valor, label, comparação/estado e contexto, não apenas um número. Charts e listas devem ser escolhidos conforme a pergunta, sem criar uma galeria de gráficos.

**Aplicação:** usar o padrão de `Card`/metric para os quatro hero metrics e reservar gráficos para formatos, audiência e tendência quando houver dados suficientes.

### 2.2 PostHog

O PostHog trata “insights” como blocos principais de análise e separa Trends, Funnels, Retention, Paths, Stickiness, Lifecycle e SQL [2]. Essa divisão reduz a mistura entre perguntas diferentes: evolução temporal, conversão, retorno, caminho, intensidade, ciclo e consulta ad hoc.

**Padrão aproveitado:** cada visualização deve responder uma pergunta única e ter um tipo de evidência reconhecível. O mede-Dodô não precisa implementar todos esses tipos, mas deve separar formato/performance, qualidade/audiência e detalhamento.

### 2.3 Vercel Analytics

A documentação de Vercel Analytics agrupa métricas por visitantes, páginas, referrers e demografia [3]. A organização parte do que o usuário quer comparar e só depois expõe dimensões.

**Padrão aproveitado:** primeiro mostrar o resultado agregado e permitir que o usuário desça para dimensões e tabelas. No mede-Dodô, isso se traduz em hero metrics no topo e detalhes de posts, temas e comentários abaixo.

### 2.4 Supabase

A documentação de métricas do Supabase descreve dashboards e charts voltados a saúde, saturação, alertas e capacidade operacional [4]. O padrão é usar indicadores de estado e detalhamento para investigar anomalias, sem misturar cada log na visão geral.

**Padrão aproveitado:** warnings, estado parcial e detalhes de auditoria devem ser acessíveis, mas não ocupar o primeiro viewport. A tela precisa indicar quando uma leitura exige revisão.

### 2.5 Plausible

A documentação do Plausible posiciona o produto como analytics simples e privacy-friendly, com as estatísticas essenciais em um dashboard sem submenus excessivos [5].

**Padrão aproveitado:** uma página de resultados deve ser escaneável sem navegação profunda. Para o mede-Dodô, a arquitetura linear em níveis é preferível a uma árvore de tabs que esconda o resultado principal.

## 3. Componentes e repositórios open source

A lista abaixo é uma referência de arquitetura e não autoriza copiar código sem análise de licença, dependências, segurança e compatibilidade.

| Projeto | Link | Evidência/padrão | Licença observada |
|---|---|---|---|
| Tremor | [tremorlabs/tremor](https://github.com/tremorlabs/tremor) | 35+ componentes React de dashboard, charts, cards e filtros | Verificar licença no commit de adoção |
| shadcn/ui | [shadcn-ui/ui](https://github.com/shadcn-ui/ui) | Primitivas copiáveis, Card, Tabs, Accordion, Badge, Tooltip, Table, Chart | Verificar licença do componente e dependências |
| shadcn Data Table | [documentação oficial](https://ui.shadcn.com/docs/components/base/data-table) | TanStack Table, colunas, sorting, filtering, visibility, pagination e actions | Código/documentação oficial; revisar versão adotada |
| Next shadcn dashboard starter | [Kiranism/next-shadcn-dashboard-starter](https://github.com/Kiranism/next-shadcn-dashboard-starter) | Shell, layout responsivo, tabelas e componentes administrativos | MIT observada na busca GitHub |
| shadcn dashboard landing template | [shadcnstore/shadcn-dashboard-landing-template](https://github.com/shadcnstore/shadcn-dashboard-landing-template) | Dashboard open source com Next, Vite/React, Tailwind e shadcn | MIT observada na busca GitHub |
| Next shadcn dashboard | [shadcndashboard/next-shadcn-dashboard](https://github.com/shadcndashboard/next-shadcn-dashboard) | Starter de dashboard Next/shadcn/Tailwind | MIT observada na busca GitHub |
| Vite React shadcn starter | [hariadiarief/react-vite-shadcn-dashboard-starter-kit](https://github.com/hariadiarief/react-vite-shadcn-dashboard-starter-kit) | Estrutura Vite/React para adaptação de dashboard | Licença não informada na busca; não adotar sem revisão |
| Social analytics demo | [clawb-ai/demo-social-analytics](https://github.com/clawb-ai/demo-social-analytics) | Exemplo de analytics social em React/Tailwind | Licença não informada; referência visual somente |
| Flowly dashboard | [Dishain/flowly-dashboard](https://github.com/Dishain/flowly-dashboard) | Product analytics com React, Tailwind e Recharts | Licença não informada; referência visual somente |

### 3.1 Regra de adoção

O projeto deve preferir componentes do shadcn/ui adicionados de forma explícita e pequenos padrões locais. Tremor pode inspirar composição de KPI/chart, mas não deve introduzir um segundo sistema de identidade nem aumentar a complexidade do produto. Repositórios sem licença clara não devem fornecer código incorporado.

## 4. Padrões recomendados para dados densos

| Problema | Padrão recomendado | Anti-padrão a evitar |
|---|---|---|
| Muitos KPIs | Quatro hero metrics 2×2 com unidade, fonte e contexto | Grade de 3/4 cards heterogêneos |
| Dado inferencial | Badge de tipo + coverage + confidence | Valor com aparência de fato observado |
| Grande tabela | Data Table com paginação, filtro e visibilidade de colunas | Lista inteira empurrando o relatório para baixo |
| Dimensões equivalentes | Tabs ou cards comparáveis | Misturar Reels, audiência e auditoria no mesmo bloco |
| Detalhe técnico | Accordion/Collapsible | Logs abertos no primeiro viewport |
| Indisponibilidade | Estado `indisponível` e explicação | Zero silencioso |
| Anomalia | Alert com próximo passo | Vermelho sem texto ou acusação |
| Ranking | Critério explícito e janela | “Top” sem explicar métrica |
| Tendência | Chart apenas quando há série comparável | Gráfico decorativo sem período |
| Ação | Botão principal limitado a uma ação | Muitos CTAs concorrentes |

## 5. Decisão de arquitetura para o mede-Dodô

A solução recomendada é uma **página de resultado em três camadas**, com duas colunas estruturais em desktop e uma em viewport estreito:

1. **Resumo:** header, parecer e quatro hero metrics.
2. **Evidência:** formatos, audiência, qualidade, conteúdo e comentários.
3. **Detalhe:** tabelas, logs, Gemini, fórmulas, coverage, warnings e exportações.

O benchmark foi usado para reconhecer módulos e padrões de escaneabilidade. Não foi usado para copiar micro-estilo, alterar fórmulas ou replicar a complexidade da navegação de ferramentas de mercado.

## 6. Limitação da pesquisa

A pesquisa externa foi conduzida por fontes web oficiais e pela CLI do GitHub. O conector Perplexity existe na configuração da sessão, porém estava desabilitado; ele não foi habilitado ou alterado nesta execução. A ausência do Perplexity não impede a triangulação feita com documentação oficial de Tremor, shadcn/ui, PostHog, Vercel, Supabase e Plausible, além dos metadados públicos do GitHub.

## 7. Referências

[1]: https://tremor.so/ — Tremor, componentes React open-source e acessíveis para dashboards e charts.

[2]: https://posthog.com/docs/product-analytics/insights — PostHog, tipos de insights para tendências, funis, retenção, caminhos, stickiness, lifecycle e SQL.

[3]: https://vercel.com/docs/analytics — Vercel Web Analytics, visitantes, páginas, referrers e demografia.

[4]: https://supabase.com/docs/guides/monitoring-and-debugging/metrics — Supabase Metrics, dashboards e charts para saúde e operação.

[5]: https://plausible.io/docs/ — Plausible Analytics, dashboard simples e privacy-friendly.

[6]: https://ui.shadcn.com/docs/components/base/data-table — shadcn/ui Data Table e padrões TanStack Table.

[7]: https://github.com/tremorlabs/tremor — Repositório GitHub do Tremor.

[8]: https://github.com/shadcn-ui/ui — Repositório GitHub do shadcn/ui.

[9]: https://github.com/Kiranism/next-shadcn-dashboard-starter — Starter Next/shadcn com licença MIT observada na pesquisa.

[10]: https://github.com/shadcnstore/shadcn-dashboard-landing-template — Template shadcn com licença MIT observada na pesquisa.

[11]: https://github.com/shadcndashboard/next-shadcn-dashboard — Starter Next/shadcn com licença MIT observada na pesquisa.

[12]: `SPRINT-003/BENCHMARK` — Pasta local com 44 prints Modash e PDF de referência.

[13]: `SPRINT-003/SPRINT 2.pdf` — Versão anterior analisada.

[14]: `SPRINT-003/SPRINT 2.1.pdf` — Última iteração analisada.

## 8. Complemento visual e operacional

O catálogo de componentes prontos e referências simples para adaptação no MVP está em [`FINDER-001.md`](./FINDER-001.md). Este Finder permanece como catálogo de benchmarks e pesquisa; o Finder complementar concentra a receita de implementação e os guardrails para o agente conectado ao MCP.
