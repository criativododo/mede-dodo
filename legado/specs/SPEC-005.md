# SPEC-005: Layout, métricas e inteligência do relatório métricaDODÔ

**Sprint:** 004  
**Status:** especificação soberana para implementação aprovada  
**Runtime:** Streamlit/Python local  
**Objetivo:** alinhar o relatório local ao benchmark de mercado sem copiar ruído, corrigir demografia, criar performance por formato, calibrar autenticidade e remover a conclusão artificial do topo.

> Regra principal: o relatório deve mostrar dados concretos antes de qualquer síntese. Nenhum valor de benchmark pode ser copiado como dado da influenciadora analisada. Nenhum dado ausente pode virar zero.

## 1. Escopo e não escopo

### 1.1 Escopo

A Sprint 004 altera a arquitetura visual do relatório e os contratos de cálculo necessários para que o usuário veja: identidade, escala, likes médios, engajamento, categorias, performance por formato, qualidade da audiência, demografia amostral, posts, parcerias, comentários e brand suitability.

A sprint corrige o denominador de gênero, adiciona média e ER por formato, revisa a autenticidade para separar base real e suspeita sem punição excessiva, confirma resposta da criadora em threads e reorganiza a camada de apresentação.

### 1.2 Não escopo

Não alterar coleta, scraping, sessão, rate limiting, schemas legados sem migração explícita, Gemini, taxonomias de comentário, fórmula do ER global, fórmula do PostScore ou exportadores. Não instalar React/shadcn para reconstruir a tela Streamlit. Não importar o score do Modash. Não inventar avatar, bio, categoria, cidade, idade ou views ausentes.

## 2. Diagnóstico técnico do estado atual

| Área | Evidência no código atual | Risco | Decisão |
|---|---|---|---|
| Demografia | `app.py` lê `demografia["genero_pct"]`; o cálculo deve ser auditado em `src/metrics.py`/`src/demographics.py` | Percentual pode usar total bruto de comentários, produzindo `6.2%` em vez de composição da amostra reconhecida | Normalizar pelo denominador válido de gênero |
| Formatos | `_render_format_performance` mostra geral e views de Reels | Não há cartão comparável Reels/Carrossel/Estático com likes, comentários e ER | Adicionar agregação por formato com estados de dados |
| Autenticidade | `estimate_fake_followers_risk` é heurística e o app exibe sinal de audiência | Percentual de risco pode parecer acusação e ficar excessivamente punitivo | Separar base real/massa real, suspeito e indisponível; expor confiança e amostra |
| Respostas | `creator_response_rate` usa `respondido` nos comentários coletados | Se `respondido` vier só do nível 1, a taxa subestima respostas em threads | Validar replies/threaded comments e contar cada comentário raiz uma vez |
| Topo | `_render_decision_summary` mostra Score DODÔ e parecer antes dos KPIs | Nota artificial cria conclusão antes da evidência | Remover do topo; preservar em auditoria/exportação se compatível |
| Formatação | `_format_compact_number` e `_format_pct` já existem | Labels e precisão devem ser uniformes nos novos cards | Reutilizar formatadores; adicionar somente os necessários |

## 3. Arquitetura de informação aprovada

```text
header
  avatar opcional · @handle · bio opcional · categorias observadas
  seguidores · média de likes · ER global · janela · data · procedência

performance por formato
  reels:     likes médios · comentários médios · ER por formato
  carrossel: likes médios · comentários médios · ER por formato
  estático:  likes médios · comentários médios · ER por formato

qualidade e audiência
  autenticidade estimada · sinal coordenado · confiança · cobertura
  demografia: gênero · idade · cidades, com barras horizontais

conteúdo e relacionamento
  top posts com thumbnail/link limpo · colaborações/parcerias

comentários
  comentários úteis · intenção · sentimento · brand suitability, se disponível

auditoria recolhida
  score legado · parecer legado · fórmulas · IDs · provenance · warnings · export
```

### 3.1 Header e hero

O header deve ter uma superfície visual limpa e imponente, sem repetir o formulário de entrada. Avatar e bio só aparecem se os campos existirem. A linha principal exibe `@handle`, categoria(s) observada(s), seguidores, likes médios e ER global. O valor de seguidores segue o compactador: `2.218.990` vira `2.2M`.

**Remoção do topo:** retirar a faixa `Leitura para contratação`, `Score DODÔ` e `Parecer de adequação comercial` do topo do relatório. O dataset e o exportador podem continuar carregando esses campos por compatibilidade, mas a UI não deve apresentar a nota como primeira conclusão. Se mantidos, devem aparecer no expander `Detalhes da auditoria`, explicitamente rotulados como `score legado/derivado`.

### 3.2 Formatos

Substituir o bloco genérico `Formatos e Reels` por três cards equivalentes:

| Card | Filtro de inclusão | Métricas |
|---|---|---|
| Reels | `is_video=True` ou `media_type=VIDEO` | média de likes, média de comentários, ER por formato |
| Carrossel | `media_type=CAROUSEL` ou `typename=GraphSidecar` com múltiplos itens | média de likes, média de comentários, ER por formato |
| Estático | `media_type=IMAGE`/single image | média de likes, média de comentários, ER por formato |

Cada card mostra `n posts`. Se não houver campo suficiente para classificar o post, o item não entra silenciosamente em uma categoria: fica `formato indisponível` e aparece em auditoria. Se a categoria não tiver posts, o card mostra `Sem posts suficientes nesta janela`, não três zeros.

## 4. Especificação matemática

### 4.1 Denominador de gênero

O percentual de gênero deve ser composição da amostra **válida e reconhecida**, não do total bruto de comentários.

```text
feminino_pct = feminino_validado / (feminino_validado + masculino_validado) × 100
masculino_pct = masculino_validado / (feminino_validado + masculino_validado) × 100
```

Definições:

| Campo | Definição |
|---|---|
| `feminino_validado` | Quantidade de nomes classificados como feminino pela fonte local aprovada |
| `masculino_validado` | Quantidade de nomes classificados como masculino pela fonte local aprovada |
| `genero_validado_n` | Soma dos dois campos |
| `genero_unknown_n` | Nomes não reconhecidos ou ambíguos, fora do denominador |
| `coverage_gender` | `genero_validado_n / nomes_identificados` quando `nomes_identificados > 0` |

Exemplo de auditoria: se 89 nomes são femininos e 11 masculinos, o resultado é 89.0% feminino e 11.0% masculino. Se 10 nomes femininos foram reconhecidos em 160 comentários brutos, não exibir 6.2% como “gênero predominante”; exibir a composição válida e `coverage_gender` separadamente.

O benchmark da @silviabraz sugere audiência aproximadamente 89% feminina e concentrada em grandes centros como SP, RJ e MG. Esse valor é referência de comparação visual/mercado, não valor a copiar para nenhuma execução local.

### 4.2 Regiões e cidades

Para cidades/regiões, o denominador deve ser a amostra de localidades válidas:

```text
cidade_pct = cidade_n / Σ(cidade_n para cidades reconhecidas) × 100
```

A UI deve mostrar no máximo cinco barras no resumo, agrupando o restante em `outras`. Exibir `coverage_region` e a ressalva: “estimativa derivada de comentários públicos, não representa todos os seguidores”. Não inferir SP/RJ/MG se os dados locais não os reconhecem.

### 4.3 Performance por formato

Para cada formato `f` em `{reels, carrossel, estatico}`:

```text
n_f = quantidade de posts classificados como f
avg_likes_f = Σ likes_i / n_f
avg_comments_f = Σ comments_i / n_f
interactions_f = Σ (likes_i + comments_i)
ER_f = interactions_f / (followers_count × n_f) × 100
```

Se o contrato canônico considerar outras ações além de likes e comentários, reutilizar exatamente o conjunto de ações de `engagement_rate_by_followers`; não criar uma fórmula paralela. O campo `denominator` deve ser `followers_count × n_f` e o campo `kind` deve ser `derived`.

Contrato mínimo:

```json
{
  "format": "reels|carrossel|estatic  "format": "reels|carrossel|estatic  "format": "reels|carrossel|es: 0.0,
  "engagement_rate": null,
  "status": "ok|indisponivel",
  "kind": "derived",
  "denominator": "followers_count * post_count",
  "source": "local_posts",
  "coverage": 0.0,
  "ressalvas": []
}
```

`engagement_rate=null` quando `post_count=0` ou seguidores não estão disponíveis. Nunca retornar `0.0%` para uma categoria que não possui dados.

### 4.4 Autenticidade e calibragem

O produto não deve exibir “percentual de fraude” como fato. O contrato recomendado separa composição estimada:

```text
base_real_pct = 100 - suspeito_pct - desconhecido_pct
```

Com `0 ≤ base_real_pct ≤ 100`, `0 ≤ suspeito_pct ≤ 100`, `0 ≤ desconhecido_pct ≤ 100` e a soma igual a 100 quando o status é `ok`.

A heurística pode continuar usando ER, pod index, shallow ratio e sinais de repetição, mas deve:

1. expor `confidence`, `sample_n`, `method_version` e `ressalvas`;
2. distinguir `suspeito` de `fraude confirmada`;
3. aplicar um piso de `desconhecido` quando a amostra for pequena;
4. evitar transformar um único sinal em penalidade dominante;
5. permitir calibração em fixtures do benchmark sem copiar percentual de mercado;
6. manter o estado `indisponível` quando não houver comentários/ações suficientes.

A meta de validação indicada pelo benchmark é verificar se o caso atual, antes marcado como aproximadamente 89% inautêntico, pode ser explicado por uma distribuição menos punitiva, próxima de 70% base real/massa real e 24% suspeito, com a diferença explicitamente classificada como desconhecida ou arredondamento. Esses valores são **fixtures de calibração**, não regra universal.

### 4.5 Respostas da criadora

A taxa deve ser calculada sobre comentários raiz avaliados:

```text
creator_response_rate = root_comments_with_creator_reply / root_comments_evaluable × 100
```

A implementação deve preferir evidência de thread:

- `comment.respondido=True` quando o coletor confirmou reply do proprietário;
- `comment.replies` ou `edge_threaded_comments` quando a fonte fornece respostas;
- `owner_username`/ID do perfil analisado para confirmar que a resposta é da criadora;
- não contar uma resposta da criadora duas vezes;
- comentários sem campo de reply ficam `unknown`, não automaticamente `false`, se a fonte não permitiu verificar a thread.

O contrato deve guardar `root_comments_evaluable`, `root_comments_with_creator_reply`, `reply_detection_method`, `coverage` e `status`. Um teste mínimo precisa diferenciar comentário raiz respondido em thread de comentário de nível 1 sem resposta.

## 5. Camada de dados e tratamento de ausência

A normalização de posts deve preservar campos brutos e derivados:

```json
{
  "post_id": "...",
  "shortcode": "...",
  "url": "...",
  "media_type": "VIDEO|CAROUSEL|IMAGE|UNKNOWN",
  "is_video": true,
  "likes_count": 0,
  "comments_count": 0,
  "video_view_count": null,
  "thumbnail_url": null,
  "published_at": null,
  "raw": {}
}
```

A regra de precedência é `media_type` explícito, depois `is_video`, depois heurística segura de estrutura. `UNKNOWN` não pode ser forçado para Estático.

Todo card deve distinguir:

| Estado | Exibição | Persistência |
|---|---|---|
| `ok` | valor + procedência + cobertura | valor derivado |
| `partial` | valor + ressalva + cobertura | valor parcial |
| `indisponivel` | motivo curto, sem zero | `null` e warning |
| `error` | falha operacional e ação | erro estruturado |

## 6. Layout e componentes

### 6.1 Ordem visual

1. Header de perfil, categoria, seguidores, likes médios e ER.
2. Três cards de formatos.
3. Qualidade da audiência e demografia em duas colunas.
4. Top posts e parcerias em duas colunas.
5. Comentários, intenção e brand suitability.
6. Auditoria recolhida e exportações.

### 6.2 Componentes Streamlit

| Componente | Função | Regra |
|---|---|---|
| `_render_profile_header` | Header e identidade | Não repetir Score no topo |
| `_render_format_cards` | Reels/Carrossel/Estático | Reutilizar formatadores e estados |
| `_render_audience_quality` | Autenticidade e interação coordenada | Não acusar fraude |
| `_render_audience_profile` | Gênero, idade e cidades | Barras da amostra válida |
| `_render_top_posts` | Cards com thumbnails e links | Máximo de três no resumo |
| `_render_partnerships` | Lista de colaborações | Máximo de cinco no resumo |
| `_render_comment_reading` | Intenção/sentimento/brand | Estado vazio sem zeros |
| `_render_audit_details` | Dados técnicos e score legado | Recolhido |

Desktop usa duas colunas de evidência com `st.columns([1.35, 1], gap="large")`. Viewport estreito usa uma coluna. O header e os formatos ocupam largura total.

### 6.3 Design System

Usar Cannoli `#EDEBDD`, Haute Cherry `#810100`, Ônix `#1B1717`, superfície `#F5F4EC`, texto de contraste `#FFFFFF` e borda `#E5E0D8`. Cards têm raio 12px, interiores 8px, controles 999px, sombra suave `0 10px 24px rgba(27,23,23,.07)`. Work Sans em títulos, Elms Sans no corpo e IBM Plex Mono apenas no técnico.

## 7. Plano de implementação para Claude Code

### Fase A, fixtures e contratos

Criar fixtures determinísticas com post types, nomes reconhecidos/desconhecidos, comentários raiz e replies. Atualizar testes de `src/metrics.py` e `src/demographics.py` antes de mudar a UI. Testar denominadores e `null` em amostras vazias.

### Fase B, métricas

Implementar normalização de formato, `calculate_format_metrics(posts, followers_count)`, correção do denominador de gênero, cobertura de região, contrato de autenticidade calibrável e detecção de replies da criadora. Manter funções existentes como wrappers quando possível para reduzir regressão.

### Fase C, app

Trocar o render do topo, adicionar formatos, reorganizar demografia e posts, converter parcerias para mini-cards, retirar Score/parecer do topo e manter auditoria/exportação. Não fazer refatoração total de `app.py`; modificar somente funções de render e chamadas explícitas aos novos contratos.

### Fase D, validação visual e regressão

Executar `pytest`, validar o caso @silviabraz e uma fixture sem dados Gemini, conferir HTML/PDF/JSON, comparar screenshots em desktop e viewport estreito e registrar limitações. Não fazer commit automático.

## 8. Critérios de aceite, DoD da Sprint 004

### Métricas

- [ ] Gênero usa `feminino_validado + masculino_validado` como denominador.
- [ ] `coverage_gender` é exibida separadamente.
- [ ] O caso da Silvia não exibe 6.2% como composição de gênero quando a amostra reconhecida tem outra composição.
- [ ] Regiões/cidades usam apenas localidades válidas e mostram coverage.
- [ ] Existem cards independentes de Reels, Carrossel e Estático.
- [ ] Cada card mostra média de likes, média de comentários, ER e `n posts`.
- [ ] Categorias sem posts exibem indisponível/sem dados, não zero enganoso.
- [ ] Autenticidade expõe base real, suspeito, desconhecido, confiança, amostra e versão do método.
- [ ] Nenhum card chama estimativa de fraude confirmada.
- [ ] Respostas usam replies/threads quando disponíveis e não contam duplicado.

### Layout

- [ ] Header mostra avatar/bio apenas quando disponíveis, mais seguidores, likes médios e ER.
- [ ] Score DODÔ e Leitura para contratação não aparecem no topo.
- [ ] Top posts usam mini-cards, thumbnails quando disponíveis e links limpos.
- [ ] Parcerias usam mini-cards/lista, sem URLs cruas na camada principal.
- [ ] Demografia usa barras horizontais e ressalva de amostra.
- [ ] Não há grades gigantes de posts, crescimento diário ou afinidades redundantes.
- [ ] Identidade Dodô segue tokens aprovados, sem hex novo.

### Robustez

- [ ] Estado sem dados Gemini é curto e não mostra tabelas de zeros.
- [ ] Dados parciais exibem motivo, coverage e procedência.
- [ ] Exportações HTML, PDF e JSON continuam funcionando.
- [ ] Funções de coleta, sessão, cache e scoring não sofrem alteração incidental.
- [ ] `pytest` passa sem regressão nos módulos existentes.
- [ ] A implementação não instala dependências desnecessárias nem copia código sem licença revisada.

## 9. Referências

[1]: `../docs/design-reference/modash/relatorio-completo.pdf` — benchmark visual Modash da @silviabraz.

[2]: `../docs/design-reference/modash/relatorio-parcerias.png` — referência de colaborações e marcas.

[3]: `../docs/design-reference/dodo/1.jpeg` a `5.jpeg` — referências do portal Criativo Dodô.

[4]: `../src/metrics.py` — métricas atuais, autenticidade, replies e contrato de auditoria.

[5]: `../src/demographics.py` — inferência de gênero, região e cobertura.

[6]: `../app.py` — render atual, labels, ordem visual e chamadas de dados.

[7]: `../tests/test_metrics.py` e `../tests/test_scraper.py` — fixtures e testes de métricas e replies.

[8]: `SPEC-004.md` — direção de arte anterior e tokens do relatório.

[9]: `../docs/issues/ISSUE-0009.md` — regras de procedência, custo zero e semântica de dados.

## 10. Extensão de referência brasileira

A captura anexada de uma ferramenta brasileira de análise de influenciadores é uma referência adicional de **composição editorial e explicação de métricas**. Ela não substitui o benchmark Modash e não altera os dados locais observados no código.

### 10.1 Novo fluxo de leitura

A tela deve adotar uma sequência mais legível:

```text
identidade do perfil
  avatar opcional · @handle · localização · categorias · seguidores

resumo de performance
  média de visualizações se disponível · média de likes · ER global
  interpretação curta · badge de faixa · alerta de limitação

formatos e alcance
  reels · carrossel · estático, cada qual com likes, comentários e ER
  alcance/views somente se observados · publicação/story apenas se houver fonte

o que foi verificado
  checklist compacto de métricas realmente calculadas

pontos de atenção
  sinais com risco, cobertura insuficiente ou revisão humana necessária

conteúdo e relacionamento
  top posts · parcerias/menções com janela e `+N`

auditoria avançada
  fórmulas · procedência · warnings · campos indisponíveis · exportações
```

O header e o resumo devem aparecer como cards com uma pergunta por superfície. Uma métrica grande deve vir acompanhada de unidade, janela, procedência e interpretação. A interpretação não pode afirmar causalidade ou benchmark externo quando a fonte não estiver disponível.

### 10.2 Contratos de alcance e visualizações

A nova referência mostra média de visualizações e alcance estimado, mas o código local só deve exibir esses campos com dados verificáveis:

```text
average_views = Σ(video_view_count_i) / n_reels_with_views

reach_estimated = null
  quando a fonte não fornecer alcance ou quando não houver modelo local aprovado
```

`average_views` é `derived`, tem `n_reels_with_views`, `coverage`, `source` e `status`. `reach_estimated` não pode ser inferido a partir de seguidores, likes ou ER sem modelo documentado. `Publicação` e `Story` devem ser abas ou filtros somente se a coleta distinguir os formatos; caso contrário, não criar uma falsa separação.

### 10.3 Checklist de cobertura

Adicionar, na camada de auditoria ou em um card compacto, uma checklist derivada de contratos existentes:

| Item | Fonte local esperada | Estado permitido |
|---|---|---|
| Localização | perfil ou campo de perfil | `observed`, `indisponivel` |
| Qualidade do público ativo | métricas de comentários/audiência | `derived`, `estimated`, `indisponivel` |
| Likes e comentários | posts coletados | `observed`, `derived`, `partial` |
| Sinal de interação coordenada | pod index/shallow ratio | `estimated`, `indisponivel` |
| Tipo de conta | campo observado, se existir | `observed`, `indisponivel` |
| Demografia | nomes/regiões válidos | `derived`, `partial`, `indisponivel` |
| ER detalhado | métricas canônicas | `derived`, `indisponivel` |
| Respostas | threads/replies verificáveis | `derived`, `partial`, `indisponivel` |
| Sentimento | Gemini/classificador existente | `model_output`, `indisponivel` |

A checklist não deve dizer “conta verificada” quando significa apenas “pipeline executado”. O texto recomendado é `Dados coletados para esta análise` ou `Sinais verificados na amostra`.

### 10.4 Pontos de atenção sem linguagem acusatória

A referência brasileira usa blocos de problemas para orientar decisão. No métricaDODÔ, os pontos de atenção devem ser gerados por regras existentes e escritos assim:

- `Curtidas ocultas: a taxa de engajamento por likes não pode ser avaliada com precisão.`
- `Cobertura demográfica baixa: a estimativa não representa todos os seguidores.`
- `Sinal de interação concentrada: revisar a amostra antes de concluir.`
- `Respostas de criadora não verificáveis em parte das threads.`
- `Classificação Gemini indisponível nesta janela.`

Não usar `seguidores falsos`, `fraude`, `conta ruim` ou `escolha outro influenciador` sem evidência e revisão humana. A heurística continua explicável, não punitiva.

### 10.5 Menções à marca

A referência de 165 menções nos últimos 180 dias é um padrão de **janela explícita + count + interpretação + marcas compactadas**. Implementar somente se o pipeline local tiver menções identificadas:

```json
{
  "window_days": 180,
  "mention_count": null,
  "top_brands": [],
  "status": "ok|indisponivel",
  "kind": "observed|derived",
  "source": "local_comments_or_posts",
  "ressalvas": []
}
```

`publi_confirmada` exige evidência textual de patrocínio. Menção orgânica, marca citada e colaboração potencial ficam s`publi_confirmada` exige evidência textual de patrocínio. Menção orgânica,al fica na auditoria.

### 10.6 Métricas explicitamente fora desta SPEC

Preço esperado, EMV, CPE, crescimento anual, percentil de criadores similares e alcance estimado ficam como referências de pesquisa, não como novos requisitos de cálculo nesta sprint. Se um campo não existir no `app.py`, `src/metrics.py`, `src/demographics.py` ou coletor, mostrar `indisponível` e registrar o gap. Não preencher por extrapolação.

## 11. Referência visual adicional

[12]: `captura anexada nesta execução, ferramenta brasileira de análise de influenciadores` — referência de header, cards de média, ER, alcance, checklist, pontos de atenção, menções e camada avançada.

O conteúdo da captura foi incorporado como referência visual e de fluxo, não como fonte de valores do métricaDODÔ. O `SAIDA-MANUS.md` permanece inalterado conforme solicitado.

## 12. Camada de interface limpa, Apple-like e implementável

A fusão do Finder005 adiciona uma camada de acabamento sem substituir a direção Dodô. O objetivo é uma interface silenciosa, editorial e muito clara: menos ruído, mais espaço negativo, uma pergunta por card, números com peso e texto suficiente para explicar a decisão.

### 12.1 Hierarquia visual final

```text
1. identidade: avatar opcional, @handle, localização, categorias e janela
2. fatos principais: seguidores, likes médios, ER e média de views se disponível
3. formatos: Reels, Carrossel, Estático, cada um com n, likes, comentários e ER
4. leitura de qualidade: autenticidade, sinais coordenados, cobertura e confiança
5. evidências: demografia, top posts, parcerias e menções por janela
6. explicação: conta analisada, pontos de atenção, intenção/sentimento/brand
7. auditoria: score legado, fórmulas, IDs, gaps, warnings e exportações
```

O primeiro viewport não deve começar com Score DODÔ, paywall, alertas comerciais ou tabela. O topo deve permitir que um diretor criativo entenda a escala e a qualidade do sinal em poucos segundos.

### 12.2 Sistema de cards

Cada card deve responder a uma pergunta e seguir a sequência `label → valor → interpretação → procedência → ação/detalhe`. Cards de decisão usam superfície `#F5F4EC`, borda `#E5E0D8`, raio 12px, padding 20–24px e sombra baixa. O fundo Cannoli `#EDEBDD` cria respiro. Nenhum card recebe cor de categoria.

A composição visual pode usar o raciocínio Bento do Finder005, mas o Streamlit deve manter duas colunas de evidência. Tiles grandes são para fatos ou diagnóstico; tiles pequenos são para badges e ações, nunca para esconder dados críticos.

### 12.3 Comportamento e microinterações

Implementar apenas microinterações que aumentem compreensão: hover/focus que confirma clicabilidade, `Ver post ↗` com destino acessível, expander que preserva posição, estados de loading/progresso claros e feedback de exportação. Não usar movimento ornamental, parallax, auto-rotating carousel, shimmer excessivo ou mudança de layout ao hover.

Badges devem dizer `observado`, `derivado`, `estimado`, `modelo` ou `indisponível`. Um badge de nível (`baixo`, `médio`, `alto`) só aparece com método, referência, cobertura e explicação próximos. Não usar `Bom nível` ou `Excelente nível` como verdade sem benchmark local documentado.

### 12.4 Tabelas e links

Parcerias e posts devem usar `st.column_config.LinkColumn` ou mini-cards. A label visível é `Ver post ↗`, `Post 01` ou `@handle`; o destino mantém URL e shortcode no dado técnico. Colunas de tipo, posts e ER precisam de largura mínima; quando a largura não comportar, reduzir colunas no resumo, não truncar sem alternativa.

### 12.5 Exportação editorial

A camada de exportação deve, em futura revisão, preservar cards e títulos com `break-inside: avoid`, ocultar controles com `.no-print`, manter cores com `print-color-adjust: exact`, carregar fontes aprovadas e evitar quebrar tabelas entre páginas. A stack atual não deve ser trocada nesta alteração documental. Playwright e WeasyPrint permanecem referências para decisão posterior.

### 12.6 Critérios adicionais de aceite

- [ ] O usuário identifica a pergunta de cada card pelo título sem abrir código.
- [ ] O primeiro viewport mostra fatos concretos antes de score ou parecer.
- [ ] A interface não usa mais de duas colunas para evidências no Streamlit.
- [ ] Não há URL crua, shortcode isolado ou tabela com overflow sem link acessível.
- [ ] Hover, focus e loading não alteram a posição estrutural dos cards.
- [ ] Badges não substituem valores, fórmulas, procedência ou cobertura.
- [ ] Cards e tabelas possuem versão legível para impressão/exportação.
- [ ] Nenhuma referência Perplexity altera a paleta ou as regras do Design System Dodô.

## 13. Referências adicionais da fusão

[10]: `../docs/finders/FINDER-006.md` — catálogo único após fusão Modash, ferramenta brasileira e Finder005.

[11]: `../docs/archive/finder-sources/FINDER-005-perplexity-source.md` — fonte Perplexity original preservada no projeto para rastreabilidade.

[12]: `https://ui.shadcn.com/blocks` — blocos shadcn/ui.

[13]: `https://ui.shadcn.com/charts` — visualizações shadcn/ui.

[14]: `https://github.com/microsoft/Streamlit_UI_Template` — referência Streamlit.

[15]: `https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/page-break-inside` — impressão e quebra de página.
