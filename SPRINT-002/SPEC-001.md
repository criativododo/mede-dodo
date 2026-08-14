# SPEC-001: Refatoração editorial da tela de relatório do métricaDODÔ

**Status:** proposta para aprovação  
**Fase:** UI, UX e apresentação  
**Projeto:** Médio Dodô / métricaDODÔ  
**Escopo de implementação:** `app.py`, somente após aprovação desta SPEC  
**Fora desta fase:** fórmulas matemáticas, heurísticas de coleta, scraping, recalibração estatística e contratos de dados

> **Decisão central:** reduzir a competição visual sem reduzir a informação. A primeira leitura deve responder quem é o perfil, qual é a qualidade do sinal e se vale aprofundar a contratação. A segunda camada explica origem, cobertura, confiança e limites de cada indicador.

## 1. Diagnóstico do estado atual

A tela atual tem cobertura funcional ampla, porém organiza a leitura em grades de densidade desigual. O código observado no `app.py` renderiza os KPIs em uma sequência de **3, 2 e 4 colunas**. Depois, distribui o corpo do relatório em duas colunas com pesos equivalentes: a esquerda reúne demografia, publis e posts; a direita reúne antifraude, comentários, hashtags e menções. Essa composição faz métricas de decisão, diagnóstico técnico e dados brutos competirem pelo mesmo espaço visual [2].

O fluxo atual permanece preservado nesta fase: input de perfil, seleção da janela, modo demonstração, análise, progresso, estados de erro, relatório concluído, botão `Ver Relatório`, exportação e geração de novo relatório. A mudança proposta é editorial e espacial, não algorítmica.

| Área atual | Evidência no código | Problema de leitura | Direção SPEC-001 |
|---|---|---|---|
| Entrada | `Perfil do Instagram`, `Janela de análise`, `Modo demonstração` | A ação principal aparece como `Analisar`, menos específica que o resultado esperado | Usar `Gerar relatório`; manter a janela e demo como controles secundários |
| KPI superior | `st.columns(3)` com seguidores, engajamento e inautenticidade | Primeira linha é clara, mas o card de inautenticidade usa linguagem acusatória | Renomear para `Autenticidade da audiência (estimativa)` e exibir procedência |
| KPI intermediário | `st.columns(2)` com curtidas e comentários médios | Números brutos recebem peso semelhante aos sinais de decisão | Mover para performance e detalhes da auditoria |
| KPI inferior | `st.columns(4)` com Score, pods, resposta e comentários qualificados | Quatro indicadores heterogêneos formam uma faixa comprimida | Reduzir para dois pares de decisão e contextualizar os demais |
| Corpo | `st.columns(2)` com muitos cards empilhados | A coluna direita fica mais longa e técnica | Usar duas colunas com papéis definidos e blocos de decisão |
| Comentários | Parecer, intenção, sentimento, faixa etária e tabela Gemini | A densidade é alta para a primeira leitura | Mostrar resumo; recolher itens classificados e dados brutos |
| Procedência | Renderizada em seção própria | O significado de observado, derivado e estimado não acompanha sempre o KPI | Adicionar badge junto ao valor e microcopy contextual |

## 2. Objetivo, escopo e não objetivos

### 2.1 Objetivos

1. Tornar o relatório legível para quem decide contratação de influenciadoras de moda.
2. Organizar os dados por perguntas de decisão: escala, qualidade do engajamento, adequação, conteúdo e risco.
3. Substituir jargões por nomenclaturas compreensíveis em português.
4. Preservar evidência, cobertura, confiança, procedência e ressalvas.
5. Aplicar o Design System Criativo Dodô sem inventar cores, tipografias, raios ou sombras.

### 2.2 Fora do escopo

Não alterar ER, TER, NSS, PostScore, Score DODÔ, intenção de compra, clusterização, regras de sentimento, heurísticas de pods, estimativa de inautenticidade, coleta, pacing, sessão, cache, Gemini, schemas ou exportadores. Não alterar a ordem da execução do pipeline. Não remover dados do `analysis`; apenas mudar sua prioridade visual e sua forma de apresentação.

## 3. Arquitetura de informação da tela

A página deve seguir a ordem abaixo. Em desktop, as áreas de decisão usam duas colunas com proporção `1.35fr 1fr`; em viewport estreito, todas as áreas colapsam para uma coluna, mantendo a ordem.

| Ordem | Seção visível | Conteúdo | Prioridade |
|---:|---|---|---|
| 1 | Cabeçalho do perfil | Handle, identidade, porte, janela, data da coleta e modo da análise | P0 |
| 2 | Leitura para contratação | Score DODÔ, parecer de adequação comercial e sinais que sustentam a leitura | P0 |
| 3 | KPIs principais | Seguidores, engajamento por seguidores, autenticidade estimada e respostas da criadora | P0 |
| 4 | Formatos e Reels | Comparação de posts estáticos e Reels; views somente quando disponíveis | P1 |
| 5 | Qualidade da audiência | Sinal de interação coordenada, cobertura, confiança e ressalvas | P0 |
| 6 | Qualidade e conteúdo | Posts de maior repercussão, posts com melhor sinal de conversão, temas e parcerias | P1 |
| 7 | Perfil da audiência | Gênero, região e faixa etária, sempre com cobertura amostral | P1 |
| 8 | Comentários e intenção | Intenção de compra, sentimento, brand suitability e resumo dos comentários | P1 |
| 9 | Detalhes da auditoria | Números brutos, itens Gemini, fórmulas, IDs, warnings e metadados | P2 |
| 10 | Exportação | HTML, PDF e JSON com a mesma proveniência do relatório | P2 |

## 4. Nomenclatura canônica e contrato de exibição

A alteração é de apresentação. As chaves internas atuais permanecem compatíveis nesta fase.

| Label atual | Label canônico | Badge padrão | Regra de exibição |
|---|---|---|---|
| `Taxa de engajamento` | **Engajamento por seguidores** | `derivado` | Exibir o denominador no tooltip |
| `Por views de Reels` | **Engajamento por visualizações** | `derivado` | Exibir apenas quando views estiverem disponíveis |
| `Seguidores potencialmente inautênticos (estimativa)` | **Autenticidade da audiência (estimativa)** | `estimado` | Mostrar confiança e nota de que não é prova isolada |
| `Índice de pods` | **Sinal de interação coordenada** | `estimado` | Não usar `pod` no título; explicar no tooltip |
| `Taxa de resposta da criadora` | **Respostas da criadora** | `derivado` | Exibir percentual e cobertura da amostra |
| `Taxa de comentários qualificados` | **Comentários com sinal útil** | `derivado` | Mover para a seção de comentários |
| `Demografia da audiência` | **Perfil da audiência (estimativa)** | `estimado` | A cobertura aparece no mesmo card |
| `Publis` | **Parcerias identificadas** | `observado` ou `derivado` | Separar publi confirmada e menção orgânica |
| `Antifraude — possíveis pods` | **Qualidade da audiência** | `estimado` | Usar alerta de sinal, nunca acusação de fraude |
| `Insights acionáveis de campanha` | **Leitura para contratação** | `derivado`/`model_output` | Abrir como síntese, sem substituir evidências |
| `Score DODÔ (0-10)` | **Score DODÔ** | `derivado` | Intervalo e fórmula em tooltip técnico |
| `Top 3 por alcance/volume` | **Posts de maior repercussão** | `derivado` | Informar janela e critério de ranking |
| `Top 3 por qualidade/conversão` | **P| `Top 3 por qualidade/conversão` | **P| `Top 3 por qualidade/conversão` | **P| `Top 3 por qualidade/conversãoda |
| `Top 3 pilares temáticos` | **Temas que mais aparecem** | `derived`/`model_output` | Exibir cobertura do corpus |
| `Comentários analisados` | **Leitura dos comentários** | `observado`/`derivado` | Separar total coletado de qualificados |

Para a interface em português, `derived` deve ser renderizado como `derivado`. O valor interno pode permanecer em inglês para compatibilidade com schemas existentes.

## 5. Microcopy obrigatória

Os textos abaixo são contrato de produto. Podem receber ajustes de pontuação, mas não devem perder significado nem transformar estimativa em fato.

| Elemento | Texto exato |
|---|---|
| Engajamento por seguidores | “Interações médias por conteúdo divididas pelo número de seguidores. É um sinal comparável entre perfis, não uma garantia de conversão.” |
| Engajamento por visualizações | “Calculado somente para Reels com visualizações disponíveis. Quando a plataforma não fornece views, o resultado aparece como indisponível.” |
| Autenticidade da audiência | “Estimativa heurística baseada nos sinais observados nesta amostra. Não equivale a uma auditoria comercial externa e não deve ser lida como prova isolada.” |
| Sinal de interação coordenada | “Um pod é um grupo de contas que interage de forma repetida e concentrada para elevar artificialmente os sinais de engajamento. Este card mostra um alerta de padrão, não uma acusação.” |
| Cobertura amostral | “Percentual dos comentários analisados que permitiu estimar este indicador. A cobertura não representa automaticamente toda a base de seguidores.” |
| Respostas da criadora | “Percentual de comentários da amostra que receberam resposta da autora no período analisado.” |
| Intenção de compra | “Proporção estimada de comentários que demonstram interesse, dúvida ou intenção relacionada ao produto ou serviço.” |
| Brand suitability | “Leitura de adequação comercial do conteúdo e dos comentários para o contexto informado. Alertas exigem revisão humana.” |
| Observado | “Valor lido diretamente da fonte ou do conteúdo coletado.” |
| Derivado | “Valor calculado localmente a partir de dados observados.” |
| Estimado | “Inferência com amostra, heurística ou modelo. Confira cobertura e confiança.” |
| Model output | “Resultado produzido pelo modelo a partir dos dados e instruções registrados nesta auditoria.” |
| Indisponível | “A fonte não forneceu dados suficientes. Indisponível não significa zero.” |
| Dados fictícios | “Resultado gerado em modo demonstração. Os dados servem para validar a interface e não representam uma conta real.” |
| Cobertura insuficiente | “A amostra não contém dados suficientes para sustentar esta leitura.” |
| Warning de parcialidade | “Este indicador usa uma amostra parcial. Leia junto com cobertura, janela e procedência.” |

## 6. Layout e composição visual

### 6.1 Cabeçalho do perfil

O cabeçalho ocupa toda a largura. À esquerda ficam handle e identidade; ao lado, porte do perfil e janela. No rodapé do cabeçalho entram data de coleta, modo `real` ou `demonstração`, e badges de procedência. Nenhum número bruto deve aparecer antes da identidade.

### 6.2 Leitura para contratação

A seção usa uma faixa de superfície `Branco Brilhante` com acento vertical de 6px em `Vermelho Haute`. Ela contém Score DODÔ, parecer de adequação comercial, resumo e até três sinais de suporte. O texto não pode sugerir aprovação automática, garantia de conversão ou decisão sem revisão humana.

### 6.3 KPIs principais

Os quatro KPIs principais formam uma grade de duas colunas em desktop, com duas linhas e espaçamento de decisão de 40px entre blocos. A sequência é: `Seguidores`, `Engajamento por seguidores`, `Autenticidade da audiência (estimativa)` e `Respostas da criadora`. Curtidas médias, comentários médios, pods e comentários qualificados deixam de ocupar esta faixa.

### 6.4 Formatos e Reels

O bloco compara conteúdo estático e Reels quando ambos têm dados. O valor por views é exibido como card secundário, com cobertura e badge. Se não houver views, o card permanece no lugar com estado `indisponível` e a microcopy correspondente. Nenhum dado ausente deve ser formatado como `0,00%`.

### 6.5 Qualidade da audiência

O card mostra o sinal de interação coordenada, confiança, número de itens observados, cobertura e ressalva. O termo `pod` aparece apenas no tooltip. O card não pode usar vermelho como prova de fraude; vermelho indica atenção ou estado de revisão.

### 6.6 Qualidade e conteúdo

Em duas colunas, a área esquerda mostra `Posts de maior repercussão` e `Posts com melhor sinal de conversão`. A área direita mostra `Temas que mais aparecem`, `Hashtags populares` e `Parcerias identificadas`. A tabela técnica completa fica recolhida quando exceder o primeiro nível de leitura.

### 6.7 Perfil da audiência

O card apresenta gênero, região e faixa etária como estimativas da amostra. Cada visualização recebe cobertura no próprio título ou legenda. A seção deve informar explicitamente que a cobertura não representa automaticamente todos os seguidores.

### 6.8 Comentários e intenção

A primeira camada mostra total coletado, comentários com sinal útil, intençãoA primeira camada mostra totad suitability. A tabela de itens Gemini, textos classificados, regras e campos de depuração entra no expander `Detalhes da auditoria`.

### 6.9 Detalhes e exportação

`Detalhes da auditoria` contém fonte, janela, `audit_id`, data, fórmula, cobertura, confiança, warnings, dados brutos, itens Gemini e estados `indisponível`/`partial`. HTML, PDF e JSON preservam os mesmos badges e metadados. A exportação permanece fora do caminho de decisão, mas não é removida.

## 7. Estrutura de componentes para Streamlit

A implementação futura deve manter as funções de cálculo existentes e reorganizar apenas a camada de renderização. A nomenclatura abaixo é uma proposta de decomposição, não uma ordem para implementação imediata.

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

A composição de desktop usa `st.columns([1.35, 1], gap="large")` nas áreas assimétricas e `st.columns(2, gap="large")` nos pares de decisão. O topo não deve usar `st.columns(3)` ou `st.columns(4)` para os KPIs principais. O Streamlit deve colapsar naturalmente para uma coluna em viewport estreito.

Os componentes visuais devem mapear para as primitivas do Design System: `Card` para superfícies e blocos; `Tag` para procedência e estado; `Input` para o perfil; `Button` para gerar, ver e exportar; `Quote` somente para pareceres canônicos ou destaque editorial. Ícones, quando necessários, devem vir de um set de sistema de traço fino, sem emojis decorativos.

## 8. Tokens do Design System

Os valores abaixo são canônicos e não devem ser substituídos por hex, fonte, raio ou sombra novos [1].

| Token | Valor | Uso no relatório |
|---|---|---|
| Creme Cannoli | `#EDEBDD` | Fundo principal e estados de respiro |
| Branco Brilhante | `#F5F4EC` | Superfícies de cards e campos |
| Ônix | `#1B1717` | Texto, nunca preto puro |
| Vermelho Haute | `#810100` | Ação primária, acento e foco |
| Dália Vermelha | `#630000` | Estado pressionado, alerta e revisão |
| Vermelho Pompeia | `#8E1D1B` | Uso secundário aprovado |
| Cinza Espuma | `#E4D8CB` | Superfície ou separador aprovado |
| Cinza Sílex | `#9E9C97` | Texto secundário com contraste verificado |
| Display | Work Sans 600/700/800 | Títulos, abertura e labels |
| Corpo | Elms Sans 300/400/600/700 | Texto, interface e microcopy |
| Mono | IBM Plex Mono 400 | Números brutos, tokens, IDs e procedência técnica |
| Escala | 12, 15, 19, 24, 30, 37, 46px | Hierarquia tipográfica |
| Espaço leitura | 12px | Relação interna de label, valor e microcopy |
| Espaço decisão | 40px | Separação entre blocos de decisão |
| Raio controle | 999px | Botões, tags e campos de uma linha |
| Raio superfície | 8px | Cards, miniaturas e campos múltiplos |
| Sombra neutra | `0 10px 24px rgba(27,23,23,.07)` | Elevação de card |
| Sombra ação | `0 6px 14px rgba(129,1,0,.18)` | Contexto de ação |

Não usar `#FFFFFF`, preto puro, gradientes, glassmorphism, raio diferente dos três valores, sombra azulada ou animação de bounce/rotação/escala. Estados de interação devem usar alteração de opacidade, borda ou tom.

## 9. Procedência, estados e visibilidade

Cada valor apresentado em card deve possuir, no mínimo, `kind`, `source`, `confidence`, `coverage`, `freshness` e `status` quando disponíveis no contrato atual. O badge deve ser pequeno, legível e próximo do label, nunca escondido apenas em um painel técnico.

| Estado interno | Label visível | Cor/ênfase | Comportamento |
|---|---|---|---|
| `observed` | `observado` | Ônix ou neutro | Valor vem da fonte |
| `derived` | `derivado` | Ônix ou Vermelho Haute | Valor calculado localmente |
| `estimated` | `estimado` | Dália Vermelha com texto legível | Exigir cobertura/confiança |
| `model_output` | `modelo` | Neutro com microcopy | Exigir modelo e versão no detalhe |
| `unavailable` | `indisponível` | Neutro, sem alerta alarmista | Não exibir zero |
| `partial` | `parcial` | Dália Vermelha | Mostrar warning e cobertura |
| `warning` | `revisar` | Dália Vermelha | Pedir revisão humana |

A ocultação é hierárquica, nunca destrutiva. Um valor técnico pode sair do primeiro viewport e continuar disponível em `Detalhes da auditoria`. Em qualquer estado indisponível, a tela deve preservar o motivo, a cobertura e o próximo passo possível.

## 10. Acessibilidade e comportamento

Todos os labels devem acompanhar visualmente o controle correspondente. Tooltips devem estar disponíveis por foco de teclado e não depender exclusivamente de hover. Cores nunca são o único indicador de estado; cada badge combina texto e, se houver ícone, ícone de sistema com `aria-label`. O corpo usa entrelinha 1,5, o texto secundário deve manter contraste verificável e a ordem de leitura deve permanecer correta quando as colunas colapsarem.

Botões seguem 48px de altura, 28px de recuo lateral, Work Sans 700 em 15px, fundo `Vermelho Haute` e texto `Creme Cannoli`. No hover, o botão pode inverter fundo, borda e texto, sem crescer. O foco usa borda `Vermelho Haute`. A interface não deve usar animação de carregamento para esconder mudança de conteúdo; fade e slide são os únicos movimentos permitidos pelo sistema.

## 11. Critérios de aceite

| ID | Critério verificável |
|---|---|
| UI-01 | A tela não usa sequência de 3 e 4 colunas para os quatro KPIs principais. |
| UI-02 | O desktop usa duas colunas com respiro e o layout colapsa para uma coluna em viewport estreito. |
| UI-03 | O primeiro nível contém cabeçalho, leitura para contratação e quatro KPIs principais. |
| UI-04 | Os labels canônicos desta SPEC aparecem na interface sem alterar as chaves internas do `analysis`. |
| UI-05 | `Sinal de interação coordenada` possui a tooltip exata da seção 5 e não chama o perfil de fraudador. |
| UI-06 | `Cobertura amostral` aparece junto de demografia, audiência, comentários e rankings quando aplicável. |
| UI-07 | Badges de procedência aparecem junto do indicador ou no mesmo cabeçalho do card. |
| UI-08 | `indisponível` não é renderizado como zero, percentual zero ou string ambígua. |
| UI-09 | Números brutos, itens Gemini, fórmulas e IDs ficam disponíveis em `Detalhes da auditoria`. |
| UI-10 | O resumo de contratação informa que estimativas e alertas ex| UI-revisão humana. |
| UI-11 | A paleta, tipografia, escala, raio e sombra usadas pertencem aos tokens do Design System. |
| UI-12 | O fluxo atual de análise, progresso, erro, `Ver Relatório`, exportação e novo relatório continua funcional. |
| UI-13 | Nenhuma fórmula, heurística, coleta, sessão, cache, Gemini ou exportador é modificado nesta fase. |
| UI-14 | HTML, PDF e JSON continuam acessíveis e preservam procedência, cobertura e warnings. |
| UI-15 | A SPEC é implementada somente após aprovação explícita; esta entrega não altera `app.py`. |

## 12. Ordem de implementação posterior

A implementação futura deve ocorrer em três passes, sem misturar apresentação com cálculo. Primeiro, aplicar tokens, nomenclaturas, badges e microcopy. Depois, reorganizar os containers e os cards na ordem de informação desta SPEC. Por fim, mover detalhes técnicos para expander, revisar estados indisponíveis/parciais e validA implementação futura deve ocorrer em três passes, sem misturar apresentação com cáeferências

[1]: https://claude.ai/design/p/7006ab20-60bd-4dba-af52-261412856dbd?via=share — Design System Criativo Dodô, brand book canônico e tokens visuais.

[2]: `app.py` e `SPRINT-002/BENCHMARK/somente para referencia, dados ficticios.pdf` — Estado atual da tela, fluxo do relatório e estrutura de apresentação observados no projeto.

[3]: `SPRINT-002/BENCHMARK-001.md` — Benchmark de relatório e ordem de métricas observadas.
[3]: `SPRINT-002/BENCHMARK-001.md` — Benchmark de relatório e ordem de métricas observadas.
tuaRINT-002/FINDER-002.md` — Benchmark Modash, soluções open source e proveniência.

[6]: `SPRINT-002/FINDER-003.md` — Workflow, sessão, pacing, estados e exportação do relatório.

[7]: `pasted_content_5.txt` — Diretrizes de fase, objetivo de UI/UX e entregáveis solicitados.
