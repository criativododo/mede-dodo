# SPEC-004: Direção de Arte e UX do relatório métricaDODÔ

**Produto:** métricaDODÔ, auditoria local de perfis do Instagram  
**Sprint:** 004  
**Status:** especificação soberana para aprovação antes da implementação  
**Runtime:** Streamlit/Python, execução local em `localhost:8501`  
**Escopo:** direção de arte, layout, hierarquia, formatação, microcopy, acessibilidade e critérios de aceite da tela de relatório  
**Fora do escopo:** alteração de fórmulas, coleta, scoring, scraping, Gemini, schemas, sessão, exportadores ou recalibração estatística

> A tela deve parecer um instrumento editorial de decisão, não uma sequência crua de widgets Streamlit. A informação continua completa, mas o caminho principal mostra primeiro o que orienta uma contratação e só depois a evidência técnica.

## 1. Diagnóstico crítico baseado na captura real

A captura `FireShot Capture 021`, analisada em 14 tiles verticais, mede aproximadamente 944 px por 9072 px na renderização usada para leitura. O relatório apresenta dados relevantes, porém o acabamento e a hierarquia ainda não correspondem ao padrão Criativo Dodô.

| Problema observado | Evidência visual | Correção mandatória |
|---|---|---|
| Acabamento cru | Fundo contínuo, containers pouco destacados e muita área sem ritmo editorial | Criar superfícies de card, borda sutil, padding consistente, hierarquia e espaçamento |
| Contraste dos botões | `Analisar`, `Limpar Cache e Re-analisar Perfil` e `Ver Relatório` têm fundo vermelho/vinho com texto escuro quase ilegível | Forçar texto `#FFFFFF` no primário, hover, foco e disabled conforme estado |
| Parcerias quebradas | URLs completas `https://www.instagram.com/...` ocupam dezenas de linhas em coluna estreita | Mostrar perfil/handle, tipo e ação `Ver post ↗`; manter URL apenas no href e na auditoria |
| Poluição numérica | `2.218.990` no hero, percentuais com excesso de detalhe e tabelas muito altas | Compactar hero para `2.2M`, manter tabelas auditáveis com separador e fixar uma casa decimal em percentuais |
| Estados vazios ruidosos | Intenção e sentimento exibem linhas inteiras de `0.0%` quando não há classificação | Trocar por card `Indisponível`, com motivo e ressalva, sem zero silencioso |
| Shortcodes expostos | `DanGXxQo_pf`, `Db6L-okqZAo` e similares aparecem como labels | Exibir `Ver post ↗` ou `Post 01`; preservar shortcode no tooltip/detalhe |
| Tabelas truncadas | `Engajamento ... (por...)`, `Autenticidade da audiência (estima...)`, coluna de ocorrências e tipo de menção cortadas | Definir larguras mínimas, labels quebráveis e conteúdo completo em tooltip ou card |
| Hierarquia vertical longa | A lista de parcerias domina a página e empurra demografia e comentários para baixo | Resumir no nível 2, limitar itens visíveis e mover inventário completo para expander |
| Ressalvas fora do contexto | A regra de menção não provar publicidade aparece após a lista | Posicionar ressalva junto do título `Parcerias identificadas` e do badge de tipo |

A captura também confirma partes que devem ser preservadas: a matriz 2×2 de KPIs, o expander `Detalhes da auditoria`, a distinção de procedência, a ressalva demográfica e o texto `indisponível não significa zero`. A SPEC-004 melhora a apresentação sem alterar esses contratos semânticos.

## 2. Princípios de direção de arte

A interface deve ser sóbria, editorial, legível e orientada a decisão. O layout organiza por posição, peso e espaço, não por colorização de categorias. Cor é usada para ação, contraste, estado e acento controlado, nunca para pintar cada card por assunto.

A caixa baixa é o padrão textual, inclusive em títulos. Caixa alta fica restrita a rótulos funcionais. Não usar travessão ou reticências na cópia de produto. Não desenhar pássaro Dodô, não criar lockup horizontal, não aplicar gradiente, contorno ou sombra em logos e grafismos. A tela deve usar a tipografia e os tokens reais do Design System, sem inventar cor intermediária.

### 2.1 Tradução dos tokens Criativo Dodô

| Token | Valor | Uso na tela | Restrição |
|---|---|---|---|
| Cannoli | `#EDEBDD` | Fundo principal do relatório | Não usar como texto |
| Vermelho haute, cherry | `#810100` | Botão primário, acento, foco e destaque editorial | Não usar como fundo de tela inteira |
| Ônix | `#1B1717` | Texto principal, títulos e números | Não usar preto puro |
| Branco brilhante | `#F5F4EC` | Superfície de card e campo | Substitui branco puro como superfície conforme o Design System |
| Branco de contraste | `#FFFFFF` | Texto sobre `#810100`, estados primários e ícones de ação | Não usar como superfície de card |
| Borda de card | `#E5E0D8` | `1px solid` em superfícies | Token funcional de borda, sem uso como preenchimento de categoria |

O briefing desta SPEC solicita `#FFFFFF` como branco. A aplicação correta é **texto e contraste**, não superfície. O Design System local determina que branco puro não seja usado como superfície contínua; por isso cards usam `#F5F4EC`.

### 2.2 Tipografia, raio e espaçamento

| Elemento | Especificação |
|---|---|
| Display e títulos | Work Sans, peso 700 |
| Corpo e microcopy | Elms Sans, pesos regulares e 600 |
| Técnico | IBM Plex Mono somente para badges de procedência, IDs e valores de auditoria |
| Título da página | Work Sans 700, escala dominante, sem caixa alta automática |
| Card title | Work Sans 700, uma linha quando possível |
| Valor hero | Work Sans 700, número grande e compacto |
| Corpo | Elms Sans, linha confortável e largura limitada |
| Controle | `border-radius: 999px` |
| Card editorial | `border-radius: 12px` conforme esta SPEC |
| Superfície interna/tabela | `border-radius: 8px` conforme token medido do Design System |
| Espaços | `8, 12, 16, 24, 40, 64, 80, 140px` |
| Espaço de leitura | `12px` |
| Espaço entre decisões | `40px` |
| Sombra suave | `0 10px 24px rgba(27,23,23,.07)` |
| Sombra de ação | `0 6px 14px rgba(129,1,0,.18)` |

O raio de 12px é uma exceção editorial desta tela para cards de decisão. Componentes internos seguem 8px para não contradizer a escala medida. Não adicionar outros raios.

## 3. Wireframe soberano em três níveis

```text
┌──────────────────────────────────────────────────────────────────────┐
│ nível 1, header do relatório                                         │
│ @handle · port│ @handle · port│ @handle · port│ @handle · po      │
├──────────────────────────────────────────────────────────────────────┤
│ nível 1, leitura para contratação                                    │
│ score dodô · parecer curto · 2 ou 3 sinais · ressalva                 │
├──────────────────────────────┬───────────────────────────────────────┤
│ seguidores                   │ engajamento por seguidores             │
│ autenticidade estimada      │ respostas da criadora                   │
├──────────────────────────────┴───────────────────────────────────────┤
│ nível 2, formatos e reels                                            │
│ engajamento geral · views disponíveis · estado indisponível           │
├──────────────────────────────┬───────────────────────────────────────┤
│ qualidade da audiência       │ perfil demográfico                      │
│ pods/interação coordenada    │ gênero · região · idade · cobertura     │
├──────────────────────────────┴───────────────────────────────────────┤
│ top posts e evidências          │ parcerias identificadas                │
│ links limpos · postscore       │ mini-cards · tipo · ver post            │
├──────────────────────────────┴───────────────────────────────────────┤
│ comentários, intenção e brand suitability                              │
│ resumo útil ou card de estado vazio                                   │
├──────────────────────────────────────────────────────────────────────┤
│ nível 3, detalhes da auditoria ▾                                     │
│ fórmulas · ids · gemini · logs · warnings · html/pdf/json              │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.1 Nível 1, resumo imediato

O header deve ter uma linha de identidade com `@handle`, porte, janela de análise, data da coleta e modo. Não repetir o formulário de consulta dentro do relatório. O `Score DODÔ` aparece em faixa de leitura para contratação, acompanhado de parecer, confiança quando aplicável e uma ressalva humana.

Os quatro hero metrics devem permanecer em matriz 2×2. A ordem é:

1. `Seguidores`, observado e compactado no hero.
2. `Engajamento por seguidores`, derivado e com denominador em microcopy.
3. `Autenticidade da audiência (estimativa)`, estimado com confiança e cobertura.
4. `Respostas da criadora`, derivado com tamanho da amostra.

### 3.2 Nível 2, evidências

A primeira linha de evidência deve colocar lado a lado `Qualidade da audiência` e `Perfil demográfico`. A segunda deve colocar lado a lado `Top Posts` e `Parcerias identificadas`. A terceira é uma superfície única para `Comentários, intenção e brand suitability`.

A seção de parcerias mostra no máximo cinco itens no resumo. Cada item tem `@handle` ou nome curto, tipo (`publi_confirmada` ou `menção orgânica`), ocorrências quando disponíveis e ação `Ver post ↗`. URLs completas não são labels. O inventário integral fica em `Detalhes da auditoria` ou em exportação.

A seção demográfica deve manter a ressalva junto dos números: os dados são inferidos da amostra de comentários públicos e não representam o universo total de seguidores. Cobertura de gênero, região e idade deve aparecer no card, não escondida em auditoria.

### 3.3 Nível 3, auditoria e exportação

`Detalhes da auditoria` começa recolhido. Dentro dele ficam comentários classificados, distribuição completa, fórmulas, cobertura, confiança, source, freshness, IDs, shortcodes, warnings e dados de modelo. Os botões de exportação HTML, PDF e JSON ficam ao final do expander ou em uma faixa de ação posterior ao estado `Relatório pronto`.
## 4. Especificação de cards e CSS nativo do Streamlit

### 4.1 Card editorial

Cada card responde a uma pergunta. Ele usa fundo `#F5F4EC`, borda `1px solid #E5E0D8`, raio 12px, sombra suave e padding horizontal mínimo de 24px, vertical mínimo de 20px. O título fica acima do valor, a microcopy fica próxima do valor e badges de procedência não podem ser separados do KPI.

Cards internos de tabela usam raio 8px e não recebem cor por categoria. O card de estado vazio usa a mesma superfície, uma mensagem curta, motivo, próxima ação e sem tabela vazia.

### 4.2 Botões

O botão primário tem altura mínima de 48px, padding horizontal de 28px, Work Sans 700 a 15px, fundo `#810100` e texto `#FFFFFF`. Hover inverte fundo e texto dentro da paleta permitida, preservando contraste. Focus deve ter indicador visível sem depender apenas de mudança de cor. Disabled reduz ênfase sem tornar o texto ilegível.

O CSS de referência abaixo deve ser centralizado em uma função de estilo. Ele é uma especificação, não uma instrução para alterar o `app.py` antes da aprovação:

```css
:root {
  --dodo-cannoli: #EDEBDD;
  --dodo-cherry: #810100;
  --dodo-onyx: #1B1717;
  --dodo-surface: #F5F4EC;
  --dodo-white: #FFFFFF;
  --dodo-border: #E5E0D8;
  --dodo-radius-card: 12px;
  --dodo-radius-inner: 8px;
  --dodo-radius-control: 999px;
  --dodo-shadow-soft: 0 10px 24px rgba(27,23,23,.07);
  --dodo-shadow-action: 0 6px 14px rgba(129,1,0,.18);
}

.report-card {
  background: var(--dodo-surface);
  border: 1px solid var(--dodo-border);
  border-radius: var(--dodo-radius-card);
  box-shadow: var(--dodo-shadow-soft);
  padding: 20px 24px;
}

.primary-action button,
.primary-action button:hover,
.primary-action button:focus {
  min-height: 48px;
  padding: 0 28px;
  border-radius: var(--dodo-radius-control);
  background: var(--dodo-cherry);
  color: var(--dodo-white) !important;
  font-family: "Work Sans", sans-serif;
  font-size: 15px;
  font-weight: 700;
  box-shadow: var(--dodo-shadow-action);
}

.data-empty {
  background: var(--dodo-surface);
  border: 1px solid var(--dodo-border);
  border-radius: var(--dodo-radius-card);
  padding: 20px 24px;
  color: var(--dodo-onyx);
}
```

A implementação deve preferir classes e seletores com escopo da página, evitando CSS global que possa quebrar widgets nativos. A cor de texto do botão deve ser declarada com prioridade suficiente para corrigir o bug observado, mas sem alterar todo o tema do Streamlit.

## 5. Formatação numérica e de links

### 5.1 Números públicos

| Tipo | Regra | Exemplo |
|---|---|---|
| Milhões no hero | Uma casa decimal e sufixo `M`; remover `.0` | `2.218.990` → `2.2M` |
| Milhares no hero | Uma casa decimal e sufixo `K`; remover `.0` | `150.689` → `150.7K` |
| Absoluto em tabela | Separador de milhar, sem compactar evidência auditável | `2.218.990` |
| Percentual | Uma casa decimal fixa | `1.3%`, `0.1%`, `62.2%` |
| Score DODÔ | Duas casas decimais | `6.43` |
| Cobertura | Uma casa decimal e label de amostra | `8.2% da amostra` |
| Valor indisponível | Label textual | `indisponível` |
| Valor ausente | Não usar zero como substituto | `Sem dados suficientes` |

Não usar casas decimais desnecessárias em números absolutos. Não arredondar um valor ausente para zero. Para tabelas, preservar precisão de auditoria, mas dar largura suficiente para não truncar o label.

### 5.2 Posts, shortcodes e URLs

A camada principal exibe `Ver post ↗`, com `st.link_button` ou link HTML acessível e o URL completo como destino. Para tabelas, o texto pode ser `Post 01`, `Post 02` ou um shortcode curto com tooltip, nunca uma URL completa quebrando a coluna. O shortcode original segue no detalhe e no JSON.

### 5.3 Parcerias

O resumo usa mini-cards verticais ou lista com três colunas flexíveis: `perfil`, `tipo`, `ação`. O tipo deve ser um badge textual, não apenas cor. A ressalva deve aparecer imediatamente abaixo do título:

> Menção isolada não prova publicidade. `publi_confirmada` exige linguagem explícita de patrocínio na legenda, além da marcação.

## 6. Estados vazios, indisponíveis e parciais

Quando não houver comentários classificados pelo Gemini, não exibir quatro linhas de `0.0%` para intenção e quatro linhas de `0.0%` para sentimento. Exibir um card:

> **Sem dados suficientes nesta janela.** A fonte não forneceu comentários classificados para estimar intenção, sentimento ou brand suitability. Indisponível não significa zero.

O card deve informar se há ação possível, por exemplo `Ver comentários brutos` ou `Abrir detalhes da auditoria`. O mesmo tratamento vale para ausência de Reels/views, demografia insuficiente, temas sem frequência e posts sem ranking confiável.

Estados parciais mostram valor disponível, cobertura, confidence e ressalva. O componente não deve usar verde para dizer que um resultado é bom quando o dado apenas está completo. Cores não substituem texto.

## 7. Microcopy no tom Criativo Dodô

| Contexto | Microcopy aprovada |
|---|---|
| Score | `Leitura consolidada para apoiar uma decisão de contratação. Estimativas exigem revisão humana.` |
| Engajamento | `Interações médias divididas pelos seguidores no período analisado.` |
| Autenticidade | `Estimativa baseada nos sinais observados nesta amostra. Não é auditoria externa.` |
| Interação coordenada | `Alerta de padrão de interação concentrada. Não é prova isolada de fraude.` |
| Demografia | `Estimativa derivada da amostra de comentários públicos. Não representa todos os seguidores.` |
| Cobertura | `Percentual da amostra que permitiu estimar este indicador.` |
| Brand suitability | `Leitura de adequação comercial. Alertas exigem revisão humana antes da contratação.` |
| Parcerias | `Menção isolada não prova publicidade. Confira a legenda e a linguagem de patrocínio.` |
| Indisponível | `A fonte não forneceu dados suficientes. Indisponível não significa zero.` |
| Exportação | `Relatório pronto. Escolha um formato para exportar os dados desta análise.` |

Evitar linguagem acusatória, promessas de conversão e estados com `[revisar]`. Quando uma confirmação externa for necessária, dizer explicitamente onde ela é feita.

## 8. Componentes e ordem de implementação

| Ordem | Componente | Regra de implementação |
|---:|---|---|
| 1 | `report_header` | Identidade, janela, data, modo e fonte |
| 2 | `decision_summary` | Score, parecer, 2 ou 3 sinais e ressalva |
| 3 | `hero_metrics_grid` | Quatro cards em 2×2, sem novos cálculos |
| 4 | `format_cards` | Estático/Reels, views e estados vazios |
| 5 | `audience_quality_card` | Pods, confidence, coverage e microcopy |
| 6 | `audience_profile_card` | Demografia amostral e ressalva próxima |
| 7 | `top_posts_card` | PostScore, contagens e `Ver post ↗` |
| 8 | `partnerships_card` | Cinco itens, tipo, ação e expander |
| 9 | `comments_insight_card` | Resumo útil ou estado vazio, nunca zeros ruidosos |
| 10 | `audit_expander` | Fórmulas, Gemini, IDs, warnings e exportação |

A composição deve manter duas colunas de evidência em desktop e uma coluna em viewport estreito. O formulário de entrada não deve ser refeito nesta SPEC, salvo a correção de contraste dos botões já existentes.

## 9. Critérios formais de aceite, DoD da Sprint 004

### 9.1 Visual e acabamento

- [ ] Fundo principal usa Cannoli `#EDEBDD`.
- [ ] Cards usam superfície `#F5F4EC`, borda `1px solid #E5E0D8`, raio 12px e sombra suave.
- [ ] Superfícies internas usam raio 8px e não criam categorias por cor.
- [ ] Tipografia segue Work Sans em títulos, Elms Sans em corpo e Mono somente em técnico.
- [ ] Não há gradientes, hexes novos, logos redesenhados, pássaro Dodô ou branco puro como superfície.
- [ ] Existe respiro editorial entre blocos, com 12px para leitura e 40px entre decisões.

### 9.2 Contraste e acessibilidade

- [ ] Botões primários exibem texto `#FFFFFF` sobre `#810100` em normal, hover, focus e disabled legível.
- [ ] O foco de teclado é visível e não depende apenas de cor.
- [ ] Links `Ver post ↗` têm nome acessível e destino claro.
- [ ] Tooltips não são a única forma de acessar informação essencial.
- [ ] Tabelas e cards não dependem apenas de cor para diferenciar tipo ou estado.
- [ ] O conteúdo é legível sem overflow horizontal em viewport estreito.

### 9.3 Dados e layout

- [ ] Header, Score, parecer e quatro hero metrics aparecem antes das tabelas.
- [ ] Hero metrics são matriz 2×2.
- [ ] Seguidores no hero aparecem como `2.2M`, não `2.218.990`.
- [ ] Percentuais públicos usam uma casa decimal fixa.
- [ ] Shortcodes e URLs não aparecem como labels extensos na camada principal.
- [ ] A lista de parcerias não domina verticalmente a tela.
- [ ] A tabela de menções mantém `perfil`, tipo e ação sem truncamento.
- [ ] Não há linhas de `0.0%` quando a classificação está indisponível.
- [ ] `indisponível` não é convertido em zero.
- [ ] `Detalhes da auditoria` começa recolhido e conserva os dados técnicos.
- [ ] HTML, PDF e JSON continuam acessíveis após o relatório pronto.
- [ ] Fórmulas, score, coleta e schemas permanecem inalterados.

### 9.4 Validação visual

- [ ] Validar com o caso `@silviabraz`, janela de 90 dias e dados da captura.
- [ ] Validar com uma conta sem comentários Gemini para confirmar o estado vazio.
- [ ] Validar com um perfil que tenha Reels/views disponíveis.
- [ ] Validar em viewport desktop e estreito.
- [ ] Comparar o resultado com esta SPEC e com `metricadodo-pdf-findings.md`, não apenas com a aparência original.

## 10. Dependências e limites

A SPEC-004 não autoriza instalação automática de biblioteca, troca de framework ou alteração do pipeline. O agente deve reutilizar os componentes definidos em `FINDER-001.md`, manter a ordem de informação de `SPEC-003.md` e respeitar os dados e ressalvas de `FINDER-003.md`.

A regra de custo zero continua vigente. Nenhuma fonte paga, API paga ou serviço externo é necessário para a implementação visual. O relatório segue local e offline, com Gemini opcional conforme o pipeline atual.

## 11. Referências

[1]: `SPRINT-003/FireShot Capture 021 - métricaDODÔ - [localhost].pdf` — captura visual do estado atual, analisada em tiles verticais.

[2]: `/Users/danielperrut/1. PROJECTS/dodo-branding/01-BRANDING/00-LEIA-PRIMEIRO.md` — regras de marca, escrita, paleta, tipografia e restrições de uso.

[3]: `/Users/danielperrut/1. PROJECTS/dodo-branding/06-DESIGN-SYSTEM/TOKENS-MEDIDOS.md` — tokens medidos de raio, espaçamento e sombras.

[4]: `/Users/danielperrut/1. PROJECTS/dodo-branding/06-DESIGN-SYSTEM/skill-design-dodo/SKILL.md` — princípios de aplicação do Design System Criativo Dodô.

[5]: `SPRINT-003/SPEC-003.md` — arquitetura de informação e hierarquia em três níveis.

[6]: `SPRINT-003/FINDER-001.md` — componentes shadcn/ui e receitas de adaptação para MVP.

[7]: `SPRINT-003/FINDER-003.md` — benchmarks Modash e referências externas de dashboards.

[8]: `SPRINT-002/ISSUE-001.md` — regras semânticas, procedência, brand suitability e custo zero.
