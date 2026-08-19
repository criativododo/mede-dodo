# FINDER-006: Benchmark Modash e referências de UI para o relatório métricaDODÔ

**Sprint:** 004  
**Função:** catálogo de referências visuais, padrões de componente e decisões de síntese para o MVP  
**Fontes centrais:** benchmark `relatorio completo.pdf`, `relatorio de parcerias.png`, capturas `1.jpeg` a `5.jpeg`, código atual e Design System Criativo Dodô  
**Leitura:** benchmark é evidência de estrutura e vocabulário; não é contrato para copiar excesso, métricas indisponíveis ou identidade de terceiros.

## 1. Resumo executivo

O benchmark Modash apresenta um relatório de perfil com header forte, avatar, bio, seguidores, likes médios e engajamento médio; mini-cards de posts com thumbnail; bloco visual de colaborações/parcerias; barras horizontais para gênero, idade e cidades; filtros e histórico de colaborações. A tela atual do métricaDODÔ já possui boas decisões semânticas, como procedência, estado `indisponível`, cobertura amostral e `Detalhes da auditoria`, mas ainda exibe a estrutura em fluxo vertical cru, com dados importantes sem compactação e uma seção de parcerias desproporcionalmente longa.

A síntese para o MVP é deliberadamente menor: identidade e resumo no topo, dados concretos antes de score, três cards de formato, evidências visuais em duas colunas e auditoria recolhida. Não importar grades gigantes, afinidades de marca redundantes, crescimento diário ou inventário integral de posts para o primeiro viewport.

## 2. Matriz de comparação

| Área | Benchmark observado | Estado atual métricaDODÔ | Decisão para Sprint 004 |
|---|---|---|---|
| Header | Avatar, bio, seguidores, likes médios e ER médio | Handle, porte, janela, data e modo; avatar/bio não estão garantidos | Adicionar somente quando disponíveis; nunca inventar. Exibir seguidores, média de likes e ER de forma compacta |
| Hero | Resumo de perfil e números de escala antes da navegação profunda | `Score DODÔ` e `Leitura para contratação` dominam a abertura | Remover score e parecer do topo; priorizar dados concretos e categorias |
| Posts | Mini-cards com thumbnails, likes e comentários | Tabelas com shortcode e contagens | Cards limitados, thumbnail se disponível, `Ver post ↗`, likes e comentários |
| Formato | Mercado permite separar mídia e performance | Atual mostra “todos os formatos” e “views de Reels” | Reels, Carrossel e Estático, cada um com três métricas comparáveis |
| Parcerias | Bloco visual de colaborações, busca/filtro e marcas | URLs completas ocupam dezenas de linhas | Mini-cards/lista, até cinco no resumo, tipo e link limpo; inventário em auditoria |
| Demografia | Barras horizontais para gênero, idade e cidades | Texto linear com cobertura e ressalva | Barras horizontais simples, percentuais da amostra válida e ressalva próxima |
| Histórico | Benchmark mostra atividade e colaborações por período | Aplicação não precisa de crescimento diário | Não implementar histórico diário nesta sprint |
| Afinidade | Benchmark contém grades extensas de categorias/marcas | Não é essencial para a contratação inicial | Descartar no MVP; manter apenas categorias com origem clara |
| Auditoria | Módulos extensos podem ficar em camadas secundárias | `Detalhes da auditoria` já existe | Preservar recolhido com fórmulas, IDs, warnings, procedência e exportação |

## 3. Referências visuais catalogadas

### 3.1 `relatorio completo.pdf`

O PDF é uma composição vertical de painéis de relatório e serve como referência de **hierarquia**, não como autorização para reproduzir a densidade completa. Os padrões aproveitáveis são: header com identidade e escala; separação entre resumo e evidências; números grandes com labels curtos; miniaturas de posts; agrupamento de conteúdo por pergunta; e demografia representada por barras horizontais em vez de parágrafos longos.

Os elementos a descartar são: dezenas de tabelas de afinidade, crescimento diário redundante, grades gigantes de conteúdo e qualquer score ou classificação cuja origem não seja explicável no pipeline local.

### 3.2 `relatorio de parcerias.png`

A captura de parcerias do benchmark mostra uma área de relacionamento com perfil `@silviabraz`, 2.2M seguidores, ER exibido como 1.17%, lista de marcas e contagem de colaborações por marca. O padrão aproveitável é o **inventário compacto e filtrável de relações**, com marca, quantidade, categoria e período. Para o métricaDODÔ, a versão MVP deve usar mini-cards e limite de cinco itens no resumo, sem importar busca, e-mail, assignee ou setup de campanha.

O dado de 1.17% é referência visual do benchmark, não valor a copiar para o app. Qualquer valor do perfil deve ser calculado pelo pipeline local e mostrar procedência.

### 3.3 `1.jpeg` a `5.jpeg`

As cinco imagens apresentam referências do portal Criativo Dodô: login, mesa de entregas, upload de material, confirmação de recebimento e revisão de conteúdo. Elas não são benchmark de métricas de influencer, mas orientam o tratamento de produto:

| Referência | Padrão aproveitável | Tradução para o relatório |
|---|---|---|
| `1.jpeg` | Entrada simples, foco em uma ação | Header e resumo sem competir com controles |
| `2.jpeg` | Lista de atividade com status curto | Lista de parcerias e posts com estado sem URL crua |
| `3.jpeg` | Upload por etapas e feedback operacional | Estados de coleta e dados parciais claros |
| `4.jpeg` | Confirmação e segurança | Proveniência e freshness próximos do dado |
| `5.jpeg` | Revisão humana e feedback | Ressalvas de estimativa e brand suitability explícitas |

## 4. Arquitetura visual recomendada

```text
header: avatar opcional | @handle | bio opcional | seguidores | likes médios | ER médio
hero:   categoria(s) observada(s) | janela | data | procedência
formatos: [reels] [carrossel] [estático]
provas:  [top posts com thumbnail] [colaborações/parcerias]
audiencia:[gênero] [idade] [cidades principais]
comentarios: intenção | sentimento | brand suitability, somente se houver dados
auditoria: fórmulas | origem | cobertura | confiança | IDs | exportações
```

O score e o parecer não são apagados do dataset nesta decisão; são removidos do topo da UI porque criam uma conclusão artificial antes que o usuário veja a evidência. Se permanecerem por compatibilidade histórica, devem ficar em auditoria ou exportação e ser rotulados como derivação do pipeline atual.

## 5. Padrões de componente aplicáveis ao Streamlit

| Padrão de mercado | Componente local | Uso aprovado |
|---|---|---|
| Profile header | `st.container(border=True)` + colunas | Avatar, bio, handle e escala; sem novo cálculo |
| Metric card | `st.metric` dentro de card | Seguidores, likes médios, ER e métricas de formato |
| Post mini-card | `st.container` + `st.image` opcional + `st.link_button` | Máximo de três posts no resumo |
| Collaboration list | `st.container` repetido ou tabela compacta | Perfil, tipo, quantidade e `Ver post ↗` |
| Horizontal bar | `st.progress` com label textual ou HTML/CSS escopado | Gênero, idade e cidades da amostra válida |
| Empty state | `_render_empty_state` | Sem comentários classificados, views, posts ou demografia |
| Disclosure | `st.expander` | Fórmulas, IDs, logs e inventário completo |
| Provenance badge | `_badge_caption` ou equivalente | `observado`, `derivado`, `estimado`, `indisponível` |
| Export action | `_render_export_actions` | HTML, PDF e JSON, sem remover funções atuais |

As referências de shadcn/ui e dashboards são padrões conceituais. O projeto atual é Streamlit/Python; não instalar React, shadcn ou uma biblioteca visual apenas para copiar a aparência. A equivalência deve ser feita com componentes nativos ou HTML/CSS escopado e já existente.

## 6. Regras de leitura e densidade

O primeiro viewport deve responder, nesta ordem, quem é o perfil, qual a escala, quais formatos performam, qual a qualidade da audiência e quais evidências sustentam a leitura. O usuário não deve atravessar dezenas de linhas de parcerias para encontrar demografia ou comentários.

No hero, usar `2.2M`, `150.7K` e uma casa decimal em percentuais. Em tabelas de auditoria, manter separador de milhar e precisão necessária. `indisponível` representa ausência de fonte; não é zero.

Mini-cards de posts devem preservar `post_id` e URL no dado técnico, mas exibir `Post 01`, thumbnail opcional, likes, comentários, formato e `Ver post ↗`. Parcerias devem exibir `@handle`, marca, tipo, ocorrência e link limpo. Shortcode e URL completa ficam no expander.

## 7. Guardrails de benchmark

Não copiar score visual, cores do Modash, tabelas de afinidade, filtros de campanha, e-mail, assignee, busca de marca ou gráficos de crescimento diário. Não tratar a estimativa do benchmark como ground truth. Não substituir a procedência local por valores observados no PDF.

A identidade visual do produto segue o Design System Dodô: Cannoli `#EDEBDD`, Haute Cherry `#810100`, Ônix `#1B1717`, superfície `#F5F4EC`, texto de contraste `#FFFFFF`, borda `#E5E0D8`, raio editorial 12px, raio interno 8px, Work Sans para títulos, Elms Sans para corpo e IBM Plex Mono somente em técnico.

## 8. Referências de trabalho

[1]: `../../docs/design-reference/modash/relatorio-completo.pdf` — benchmark visual Modash da @silviabraz.

[2]: `../../docs/design-reference/modash/relatorio-parcerias.png` — referência de inventário de colaborações.

[3]: `../../docs/design-reference/dodo/1.jpeg` — referência de login e acesso ao portal Criativo Dodô.

[4]: `../../docs/design-reference/dodo/2.jpeg` — referência de mesa e atividade recente.

[5]: `../../docs/design-reference/dodo/3.jpeg` — referência de envio de material.

[6]: `../../docs/design-reference/dodo/4.jpeg` — referência de recebimento e revisão.

[7]: `../../docs/design-reference/dodo/5.jpeg` — referência de revisão humana.

[8]: `../../specs/SPEC-004.md` — direção de arte e UX do relatório atual.

[9]: `./FINDER-004.md` — componentes reutilizáveis e receitas de MVP.

[10]: `./FINDER-003.md` — workflow, sessão e coleta responsável.

[11]: `../docs/issues/ISSUE-0009.md` — semântica, procedência, scoring e custo zero.

## 9. Referência brasileira adicional

A captura anexada nesta execução documenta uma ferramenta brasileira de análise de influenciadores. Ela entra como **referência complementar**, sem remover Modash, Criativo Dodô ou qualquer fonte anterior. Seu valor principal está no fluxo de leitura: uma coluna lateral de identidade, um header de perfil, cards de uma pergunta por vez, valor grande, interpretação textual, badge de nível, escala horizontal, alertas contextuais, checklist do que foi verificado e camada avançada recolhida.

### 9.1 Padrões absorvidos

| Padrão observado | Tradução para o métricaDODÔ | Limite |
|---|---|---|
| Perfil lateral com avatar, nome, país/cidade e ações | Header de perfil com avatar/bio quando disponíveis, `@handle`, localização e janela | Não adicionar rede, e-mail, favoritos ou lookalikes ao MVP |
| Card de média de visualizações | Card de alcance/views somente quando `video_view_count` ou fonte equivalente existir | Não estimar views sem dado local |
|||||||||||||||||||||||||||||||||||vo + submétricas | Manter nos cards de ER, formatos, audiência e demografia | Texto curto; evitar parágrafos de marketing |
| Badge `Bom nível`/`Excelente nível` | Badge textual de faixa interpretativa derivada de benchmark documentado | Nunca substituir valor, fórmula ou procedência |
| Escala horizontal com marcador | Usar para composição de gênero, regiões e faixas relativas quando denominador válido existir | Não usar cor como único significado |
| `Conta analisada` + `problemas exigem atenção` | Adicionar bloco `O que foi verificado?` e bloco de `Pontos de atenção` | Somente sinais realmente calculados pelo pipeline local |
| Checklist em duas colunas | Resumo de cobertura de localização, demografia, ER, pods, replies e sentimento | Não declarar “40 parâmetros” sem inventário auditável |
| Menções à marca por período | Card de `Menções à marca` com janela explícita, count, tipo e até cinco marcas + `+N` | Menção não equivale a publi confirmada |
| Mais informações avançadas em duas colunas | `Detalhes da auditoria` recolhido com métricas, origem, warnings e gaps | Sem paywall, bloqueio ou lock visual |

### 9.2 Valores observados, apenas como referência

A captura mostra, no caso de `@silviabraz`, 2.2M de seguidores, média de visualizações de 448.4K, média de likes de 20K, ER de 4.62%, alcance estimado de 170K–510K, média de comentários de 575, média de cinco posts por semana, crescimento anual de 13.52%, CPE de $0.45 e 165 menções à marca nos últimos 180 dias. Esses valores são **observações da ferramenta de referência**, não fixtures obrigatórias nem dados a copiar para o relatório local.

O que pode ser reaproveitado é a forma de explicar. O que depende de fonte externa, preço, crescimento histórico, audiência total ou comparação percentílica deve aparecer como `indisponível` até que o pipeline local possua o dado e a fórmula aprovados.

### 9.3 Padrões deliberadamente não absorvidos

Não importar trial/upgrade, paywall, desbloqueio de relatório, mensagem comercial, preço, EMV, CPE, crescimento anual, percentis de “criadores similares”, filtros de negócio, rede de favoritos, assignee, e-mail ou claim de “seguidores falsos”. Esses elementos ficam registrados para comparação, mas não entram na arquitetura do MVP.

## 10. Fusão do FINDER-005: UI/UX limpa e acabamento Apple-like

O `FINDER-005.md` foi lido como um catálogo adicional de pesquisa Perplexity sobre dashboards, Bento Grid, shadcn/ui, Streamlit, CSS responsivo, tabelas sem overflow, microinterações e exportação editorial. Seus padrões úteis entram aqui como complemento do Modash e da referência brasileira. Não é uma instrução para instalar React/shadcn nem para copiar templates inteiros.

### 10.1 Direção visual comum

A referência Perplexity aproxima a tela de uma linguagem Apple/Linear/Vercel: fundo neutro, uma superfície clara por card, borda fina, sombra quase imperceptível, números grandes, labels curtos, bastante espaço negativo e uma pergunta por componente. O resultado deve parecer calmo antes de parecer completo.

| Princípio | Tradução para o métricaDODÔ |
|---|---|
| Hierarquia antes de decoração | Header, hero factual, evidências, auditoria; sem colorir cada categoria |
| Uma pergunta por card | `Qual é a escala?`, `Como performa por formato?`, `O que foi verificado?` |
| Superfície neutra | Cannoli no fundo, `#F5F4EC` nos cards, borda `#E5E0D8`, sombra baixa |
| Tipografia com contraste | Work Sans nos números/títulos, Elms Sans no corpo, Mono em técnico |
| Densidade progressiva | Primeiro viewport escaneável; detalhe em expander ou página de auditoria |
| Feedback discreto | Hover/focus, badge textual e estado de carregamento, sem animação ornamental |
| Clareza de origem | Cada estimativa mostra procedência, cobertura e confiança |
| Apple-like sem copiar Apple | Limpeza e ritmo são referência; paleta, texto e marca continuam Dodô |

### 10.2 Bento Grid traduzido para Streamlit

O Finder005 sugere uma grade conceitual de 12 colunas com tiles de tamanhos diferentes. Para o MVP Streamlit, a decisão é reduzir a liberdade do Bento para preservar leitura: header e formatos em largura total; evidências em duas colunas; cards de métrica dentro de cada coluna. Não usar quatro colunas de hero nem uma colagem de tiles que force o usuário a descobrir a ordem.

```text
largura total: header + resumo factual + formatos
2 colunas:     qualidade da audiência | demografia
2 colunas:     top posts              | parcerias
largura total: comentários/brand suitability
expander:      auditoria e exportação
```

Se a camada HTML de exportação precisar de grid, usar 12 colunas apenas no documento impresso, com `break-inside: avoid` nos cards e `@media print` para não separar título e conteúdo. A versão Streamlit permanece em duas colunas sem overflow.

### 10.3 Componentes prontos e equivalentes locais

| Receita Finder005 | Equivalente local aprovado | Aplicação |
|---|---|---|
| Hero KPI com badge | `st.container(border=True)` + `st.metric` + `st.caption` | Seguidores, likes médios, ER e média de views |
| Card de diagnóstico | container com valor, interpretação e alerta | Autenticidade, alcance, coverage e pontos de atenção |
| Bento feature tile | duas colunas Streamlit com largura definida | Qualidade/demografia e posts/parcerias |
| Partnership list | `st.dataframe` com `st.column_config.LinkColumn` ou mini-cards | `Marca`, tipo, posts e `Ver post ↗` |
| Badge de status | `_badge_caption`/HTML escopado | `observado`, `derivado`, `estimado`, `indisponível` |
| Progress/range bar | `st.progress` com label textual | Demografia e faixas relativas com denominador válido |
| Accordion | `st.expander` | Auditoria, formulas, IDs e inventário |
| Empty state | `_render_empty_state` | Fonte sem dados, sem zeros silenciosos |
| Area chart | gráfico local apenas se houver série real | Crescimento/alcance somente com fonte e escopo aprovados |

O código de exemplo do Finder005 é referência de composição. Nenhum exemplo com receita, usuários, churn, Nike, Adidas ou outros dados fictícios pode entrar no relatório. Dados do benchmark e do exemplo são substituídos por contratos locais ou por estado `indisponível`.

### 10.4 CSS e acessibilidade

A pesquisa recomenda CSS escopado com superfície clara, borda `1px`, raio 12px, sombra `0 1px 3px rgba(...)`, botões pílula e tabela com `overflow-x: auto`. No Dodô, manter os tokens aprovados e não importar `#1A1A1A`, `#333333`, Slate/Zinc ou verde externo como paleta de produto. A técnica entra como padrão, os hexes continuam os do Design System.

Regras obrigatórias:

- `color: #FFFFFF !important` no texto de botão sobre `#810100`;
- foco visível e labels acessíveis;
- `st.column_config.LinkColumn` para mostrar `Ver post ↗` sem URL crua;
- tabelas com largura e overflow controlados;
- tooltips não são a única fonte de informação essencial;
- estados diferenciam texto, ícone e estrutura, não apenas cor;
- hover não pode deslocar o conteúdo ou quebrar a leitura.

### 10.5 Exportação PDF e leitura impressa

O Finder005 compara Playwright, WeasyPrint, `@media print`, `@page`, fontes, SVG e `break-inside: avoid`. Para o projeto, isso é orientação de acabamento do exportador existente, não autorização para trocar a stack. Quando o exportador for revisado:

```css
@media print {
  .report-card, table, tr { break-inside: avoid; page-break-inside: avoid; }
  h1, h2, h3, h4 { break-after: avoid; page-break-after: avoid; }
  .no-print { display: none !important; }
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
```

O PDF deve preservar cards, títulos, fundos e gráficos vetoriais sem separar cabeçalho da evidência. Não adicionar Playwright ou Node apenas por estética; avaliar primeiro o exporter atual, custo, dependências e licença.

### 10.6 Referências Perplexity consolidadas

[13]: `https://ui.shadcn.com/blocks` — blocos de interface shadcn/ui.

[14]: `https://ui.shadcn.com/charts` — charts e padrões de visualização shadcn/ui.

[15]: `https://shadcnspace.com/blocks/dashboard-ui/statistics-component` — cards estatísticos e mudanças percentuais.

[16]: `https://21st.dev/community/components/s/bento` — exemplos de Bento Grid.

[17]: `https://tailgrids.com/blocks/bento-grids` — composição de Bento Grid.

[18]: `https://www.orbix.studio/blogs/bento-grid-dashboard-design-aesthetics` — princípios de estética e hierarquia Bento.

[19]: `https://github.com/microsoft/Streamlit_UI_Template` — template oficial/comunitário de UI para Streamlit.

[20]: `https://arnaudmiribel.github.io/streamlit-extras/extras/card/` — card reutilizável em Streamlit.

[21]: `https://discuss.streamlit.io/t/streamlit-facade-a-shadcn-inspired-themeable-component-library-i-built/121334` — referência de componentes tematizáveis inspirados em shadcn para Streamlit.

[22]: `https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/page-break-inside` — controle de quebra de página.

[23]: `https://pdf4.dev/blog/playwright-vs-weasyprint` — comparação de abordagens de HTML para PDF.

[24]: `https://pdf4.dev/blog/html-to-pdf-benchmark-2026` — referência de benchmark de renderização PDF.

[25]: `https://screenshotly.app/blog/html-to-pdf-generation-guide` — margens, header/footer e impressão CSS.

[26]: `https://protocol.mozilla.org/docs/fundamentals/design-tokens` — princípios de tokens e superfícies.

[27]: `https://v0.app/chat/shadcn-ui-design-ATcS4l0DBRU` — referência de composição visual shadcn-like.

### 10.7 Regra de síntese

O Finder004 agora é o catálogo único de referências da Sprint 004. Modash fornece benchmarks e módulos; a ferramenta brasileira fornece fluxo editorial, cards de diagnóstico e checklist; Finder005/Perplexity fornece acabamento, Bento controlado, componentes e impressão. A SPEC-005 decide o que é implementável. Nenhuma fonte individual é autoridade para dados locais.
