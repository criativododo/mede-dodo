# FINDER-PLATAFORMA-COMPLETA

## Manual de Engenharia de Produto, Auditoria Metodológica e Reconstrução da Plataforma

**Projeto:** métricaDODÔ — v2.0.0  
**Status:** documento de investigação e especificação de conhecimento  
**Escopo:** plataforma de descoberta e análise de influenciadoras/criadoras de conteúdo, com foco em moda, beleza, lifestyle e categorias adjacentes  
**Regra de governança:** este Finder documenta o funcionamento observado e as hipóteses de engenharia. Ele **não aprova automaticamente** as métricas da plataforma e não altera as regras autorais do métricaDODÔ sem validação explícita do Dani.

> **Princípio soberano:** primeiro reconstruir a lógica; depois discutir a validade editorial; somente após aprovação formal transformar qualquer regra observada em decisão de negócio do métricaDODÔ.

## Sumário

1. [Roteamento rápido](#1-roteamento-rápido)  
2. [Objetivo e limites deste Finder](#2-objetivo-e-limites-deste-finder)  
3. [Mapa funcional da plataforma](#3-mapa-funcional-da-plataforma)  
4. [Acesso, cota e segurança operacional](#4-acesso-cota-e-segurança-operacional)  
5. [Camadas de dados e contratos observados](#5-camadas-de-dados-e-contratos-observados)  
6. [Métricas visíveis e semântica conhecida](#6-métricas-visíveis-e-semântica-conhecida)  
7. [Escopos de conteúdo e amostragem](#7-escopos-de-conteúdo-e-amostragem)  
8. [Porte, benchmark e coorte de referência](#8-porte-benchmark-e-coorte-de-referência)  
9. [Reconstrução matemática](#9-reconstrução-matemática)  
10. [Fluxo operacional completo](#10-fluxo-operacional-completo)  
11. [Especificação de um projeto equivalente](#11-especificação-de-um-projeto-equivalente)  
12. [Regras de negócio observadas](#12-regras-de-negócio-observadas)  
13. [Como investigar e buscar documentação](#13-como-investigar-e-buscar-documentação)  
14. [Lacunas, riscos e hipóteses pendentes](#14-lacunas-riscos-e-hipóteses-pendentes)  
15. [Backlog de investigação](#15-backlog-de-investigação)  
16. [Portões de aprovação do métricaDODÔ](#16-portões-de-aprovação-do-métricadodô)  
17. [Rastreabilidade](#17-rastreabilidade)

## 1. Roteamento rápido

| Pergunta | Onde procurar primeiro |
|---|---|
| Como a plataforma encontra perfis? | Seção 3, modos `AI Search` e `Search`, filtros de Creator, Followers, ER, Views, Location e Brand collaborations. |
| O que aparece no resultado de descoberta? | Seção 6.1, cards com seguidores, ER, posts recentes, collabs e ações. |
| O que aparece no relatório de um perfil? | Seções 6.2, 6.3 e 7, com ER, impressões, alcance, médias, autenticidade, demografia e conteúdo por escopo. |
| Qual é a fórmula exata do ER? | Seção 9. A fórmula textual não foi exposta na interface observada; as hipóteses devem permanecer marcadas como não confirmadas. |
| Como a plataforma trata portes? | Seção 8. O texto observado compara a conta com “creators this size”; os cortes exatos de porte não foram expostos na UI capturada. |
| Como separar patrocinado de orgânico? | Seção 6.4, `Paid engagement` e `Paid views`, com interpretação relativa a conteúdo patrocinado versus orgânico. |
| Como repetir a investigação? | Seção 13, usando relatórios do legado, interface autenticada, bundles carregados e comparação por escopo. |
| O que pode ser incorporado ao métricaDODÔ? | Somente o que passar pelos portões da Seção 16 e for aprovado pelo Dani. |

## 2. Objetivo e limites deste Finder

Este documento funciona como um **projeto de conhecimento da plataforma**. Ele organiza o que foi observado, o que foi reconstruído a partir dos relatórios históricos, quais componentes devem existir em uma implementação equivalente e quais perguntas ainda precisam de evidência. O objetivo não é clonar visualmente ou juridicamente a plataforma, tampouco reproduzir suas decisões como se fossem verdades de mercado.

O Finder serve para três finalidades. A primeira é permitir que qualquer pessoa da equipe entenda a jornada de descoberta até o relatório detalhado. A segunda é separar **valor observado**, **valor derivado**, **estimativa**, **proveniência**, **cobertura** e **hipótese**. A terceira é criar uma base auditável para que o métricaDODÔ construa suas próprias métricas autorais, aproveitando apenas ideias que façam sentido para seu contexto editorial.

As observações deste documento foram feitas em relatórios arquivados no projeto, em screenshots históricos da plataforma e em uma sessão autenticada do Modash consultada em 15 de agosto de 2026. Snapshots de seguidores, posts e métricas são temporais; eles não devem ser tratados como séries históricas sem captura repetida.

## 3. Mapa funcional da plataforma

### 3.1 Navegação principal

A interface observada apresenta módulos de navegação equivalentes a **Discover**, **Manage**, **Email**, **Track** e **Pay**. Para o objetivo desta auditoria, o núcleo está em Discover e no relatório lateral de cada perfil.

A área de descoberta oferece os canais Instagram, TikTok e YouTube. No Instagram, existem dois modos visíveis: `AI Search` e `Search`. A busca estruturada permite informar um Creator ou e-mail e combinar filtros. A busca por linguagem natural aparece como campo de orientação, com exemplo relacionado a criadores de lifestyle, moda e beleza.

### 3.2 Descoberta e filtros

Os filtros observados foram:

| Grupo | Controles observados |
|---|---|
| Identidade | Creator, e-mail e modo Creator. |
| Tamanho e performance | Followers, Engagement rate e Views. |
| Contexto geográfico | Location. |
| Relação comercial | Brand collaborations. |
| Perfil | Bio, Gender, Age e Language. |
| Disponibilidade | Email available e Active creators only. |
| Atividade | Posting frequency e Posted within. |
| Conteúdo | Captions, Hashtags e Mentions, com inclusão e exclusão. |
| Qualidade | Fake followers e Account type. |

A página exibiu uma base declarada de **11 milhões de perfis** no modo Instagram. Também foram observadas ações de `View hidden profiles`, `Bulk save`, `Find lookalikes`, `View profile` e `Save`.

### 3.3 Card de descoberta

O card resumido de um perfil contém, conforme observado, nome, handle, seguidores, taxa de engajamento, miniaturas de posts recentes, marcas de colaborações recentes e ações para abrir o perfil, salvar e encontrar semelhantes. A presença de quatro posts recentes com contadores visíveis funciona como uma amostra visual rápida, mas não revela por si só a janela completa, o denominador ou a fórmula da taxa.

### 3.4 Relatório lateral

Ao abrir o perfil, a plataforma mantém a busca e adiciona um painel lateral. O painel observado contém identidade, handle, seguidores, taxa de engajamento, categorias de conteúdo, links sociais, e-mail comercial quando disponível, colaborações, posts populares, lookalikes, demografia, interesses, audiência, sinais de autenticidade e métricas de conteúdo.

O painel oferece `Open full report`, mas esta etapa da auditoria prioriza o painel lateral para economizar a cota de perfis abertos. A atividade registra o usuário e o horário da visualização do perfil.

## 4. Acesso, cota e segurança operacional

A sessão autenticada da plataforma exibiu a conta/área `DP` e os limites operacionais:

| Controle | Estado observado |
|---|---:|
| Tempo restante | 12 dias |
| Perfis abertos | 6 de 20 |
| Buscas utilizadas | 6% |
| Aberturas ainda disponíveis no snapshot | 14, sujeitas a atualização da conta |

Esses limites são parte do protocolo de auditoria. Não se deve abrir perfis aleatórios, repetir perfis já auditados sem finalidade clara ou consumir buscas para exploração sem hipótese. A ordem recomendada é: reaproveitar relatórios do legado; acessar perfis já pertencentes à coorte; só então abrir novos perfis de moda/lifestyle quando houver uma pergunta comparativa específica.

A sessão não deve ser usada para publicar, enviar mensagens, contratar planos, efetuar pagamentos, salvar listas de produção ou disparar e-mails. A auditoria limita-se à leitura, comparação e registro de métricas públicas/relatórios autorizados pelo usuário.

## 5. Camadas de dados e contratos observados

A plataforma aparenta separar pelo menos cinco camadas de informação:

1. **Identidade do perfil:** nome, handle, avatar, seguidores, categoria, localização, bio, links e e-mail comercial.
2. **Descoberta:** resultado de busca, filtros, relevância, porte, ER resumido, posts recentes, collabs e lookalikes.
3. **Conteúdo:** posts, Reels, Stories, views/plays, curtidas, comentários, compartilhamentos, impressões estimadas e alcance estimado.
4. **Audiência:** autenticidade, gênero, idade, países, cidades, idiomas, interesses e alcance potencial.
5. **Operação comercial:** colaborações, marcas, histórico de posts patrocinados, e-mail, tracking, listas, notas, rate e campanhas.

A existência dessas camadas não autoriza assumir que todos os campos são provenientes da mesma fonte. Um dado pode ser uma informação pública do perfil, uma estatística estimada, um campo comercial de terceiros ou uma classificação inferida pela plataforma. Toda implementação equivalente deve carregar `source`, `kind`, `coverage`, `window`, `scope`, `confidence` e `status`.

### 5.1 Contrato mínimo recomendado

```json
{
  "profile": {
    "handle": "@exemplo",
    "followers": 0,
    "account_type": "unknown",
    "observed_at": "ISO-8601"
  },
  "metric": {
    "name": "engagement_rate",
    "value": null,
    "unit": "percent",
    "source": "platform_report",
    "kind": "observed|derived|estimated|classified",
    "scope": "all_content|reels|stories",
    "window": null,
    "sample_size": null,
    "denominator": null,
    "coverage": null,
    "confidence": "unknown",
    "status": "ok|unavailable|estimated|blocked",
    "notes": []
  }
}
```

Esse contrato evita misturar um ER observado com um ER recalculado localmente, ou uma estimativa de impressões com alcance efetivamente medido pelo Instagram Insights.

## 6. Métricas visíveis e semântica conhecida

### 6.1 Taxa de engajamento

A interface de descoberta e o relatório mostram `Engagement rate`. Em perfis, a taxa vem acompanhada de uma comparação textual, como **“above average for creators this size”**. Isso indica a existência de um benchmark interno por porte ou por grupo comparável, mas não revela os cortes exatos nem a fórmula de normalização.

A taxa não deve ser interpretada sem o escopo. Os relatórios históricos mostram casos em que a conta aparece com uma taxa no resumo e outra quando o recorte de Reels é aplicado. Portanto, cada ER deve registrar explicitamente `content_scope`, janela, quantidade de posts e método de cálculo.

### 6.2 Impressões e alcance estimados

O relatório de Silvia Braz exibiu `Estimated impressions = 724,4k` e `Estimated reach = 483k`. O rótulo **estimated** é essencial: esses campos não devem ser tratados como Insights oficiais da conta. A diferença entre impressões e alcance sugere que impressões representam exposições totais estimadas e alcance representa contas alcançadas estimadas, mas a constante ou modelo da estimativa não foi exposto.

### 6.3 Médias de interações

O relatório exibiu `Average likes = 23,8k` e `Average comments = 299` para Silvia Braz. Nos relatórios históricos também aparecem `Average shares`, `Average reel plays` e outros campos dependendo do escopo. A média deve sempre ser acompanhada da quantidade de posts e do escopo; uma média de Reels não pode ser comparada diretamente com a média de todos os conteúdos sem a mesma janela ou sem um ajuste explícito.

### 6.4 Conteúdo pago e orgânico

Foram observados `Paid engagement` e `Paid views`. A inspeção do bundle do relatório revelou tooltips com semântica relativa: `100%` significa que o conteúdo patrocinado possui o mesmo engajamento ou as mesmas visualizações do conteúdo orgânico, conforme o indicador. Isso sugere uma comparação patrocinado-versus-orgânico, não uma simples fração de posts pagos.

A semântica exata do denominador, a definição de “paid”, a janela e a regra para amostras sem posts patrocinados ainda precisam de confirmação. Nenhum desses indicadores deve ser rebatizado como “percentual de publis” sem evidência.

### 6.5 Seguidores falsos e autenticidade

O relatório exibe `Fake followers`, e os benchmarks históricos registram valores como 23,90% para Silvia Braz, 37,92% para Bárbara Studart, 20,46% para Manu Fosco, 35,58% para Roberta Franco, 21,52% para Caroline Tanaka e 16,28% para Juuchika.

A plataforma não expôs no painel resumido a fórmula, os sinais, o limiar ou a confiança desse percentual. No métricaDODÔ, esse campo deve ser tratado como sinal de autenticidade de origem externa ou como estimativa classificada, nunca como fato provado. A interpretação precisa separar “seguidores falsos”, “contas suspeitas”, “audiência inautêntica” e “audiência não demonstrada”.

### 6.6 Demografia e afinidade

O relatório detalhado de Silvia mostrou gênero, idade, países, cidades, idiomas e interesses. A soma das categorias demográficas pode não representar necessariamente 100% da base total, porque a cobertura disponível pode ser parcial. Todo gráfico deve exibir cobertura, período, fonte e eventuais desconhecidos.

Interesses observados em Silvia incluíram Clothes, Shoes, Handbags & Accessories; Friends, Family & Relationships; Beauty & Cosmetics; Toys, Children & Baby; Restaurants, Food & Grocery; Travel, Tourism & Aviation; Camera & Photography; Fitness & Yoga. Essas categorias podem apoiar classificação temática, mas não provam intenção de compra nem qualidade da audiência.

### 6.7 Colaborações e posts populares

A área de colaborações de Silvia exibiu marcas como Bynv, FERRAGAMO, Riachuelo, Valentino, THE ATTICO, Belmond La Residencia, Vix Paula Hermanny Brasil, LA GEA e TIG Oficial. Cada item apresentou um post e contadores de interações, por exemplo `15,9k / 247`, `13,6k / 279`, `71,9k / 847` e `27,2k / 299`.

A plataforma separa colaboração, marca, post popular e lookalike como objetos de interface diferentes. Uma menção a uma marca não deve ser automaticamente classificada como publicidade confirmada. O registro recomendado é: marca, perfil, data, URL do post, formato, evidência textual/visual, escopo e confiança.

## 7. Escopos de conteúdo e amostragem

O painel de conteúdo observado oferece três tabs principais: `All content`, `Reels` e `Stories`. A existência dos tabs é uma regra de produto importante: a plataforma não trata todos os formatos como um único conjunto indiferenciado.

O relatório histórico indica que Reels podem aparecer com ER, plays médios, curtidas médias, comentários médios e compartilhamentos médios; Stories podem aparecer principalmente com alcance e impressões estimadas; All content concentra a visão geral. A ausência de um campo em um escopo deve ser `unavailable`, não zero.

A interface não revelou de forma textual o tamanho exato da amostra nem a janela completa no primeiro painel. Os relatórios históricos exibem números de posts e recortes, mas alguns valores foram extraídos por OCR e devem ser tratados como evidência observada com ressalva. Para reproduzir a metodologia, é necessário abrir o detalhe, identificar o período, contar os itens e salvar o escopo com cada métrica.

### 7.1 Regra de amostragem para auditoria do métricaDODÔ

Até a fórmula oficial ser confirmada, a auditoria deve manter uma tabela por perfil com `n_all_content`, `n_reels`, `n_stories`, `window_start`, `window_end`, `content_scope`, `content_type`, `visible_count`, `hidden_count` e `coverage`. Qualquer cálculo de média ou ER deve apontar para essa amostra, não para uma afirmação genérica sobre a conta.

## 8. Porte, benchmark e coorte de referência

A plataforma usa comparações textuais como “above average for creators this size”. Isso é evidência de benchmark relativo por porte, mas não autoriza deduzir os cortes exatos. O projeto deve distinguir **rótulo observado pela plataforma**, **faixa reconstruída pelo legado** e **faixa autoral do métricaDODÔ**.

### 8.1 Coorte de seis perfis já documentados

| Perfil | Snapshot Instagram em 15/08/2026 | Classe observada no legado | ER histórico Modash | Outros dados históricos legíveis |
|---|---:|---|---:|---|
| `@silviabraz` | 2,2M seguidores; 11.708 posts | Macro | 1,12% | Fake followers 23,90%; impressões 724,4k; alcance 483k; likes médios 23,8k; comentários médios 299; paid engagement 78,74%; paid views 78,71%. |
| `@barbarastudart` | 56,1k seguidores; 1.723 posts | Micro | 1,03% | Snapshot histórico de 55,3k; fake followers 37,92%; fake likers 11,77%; alcance estimado 2,2k; likes médios 572; comentários médios 59. |
| `@manurefosco` | 22,2k seguidores; 686 posts | Micro | 1,12% geral; 0,77% em Reels | Fake followers 20,46%; comentários médios 24; plays médios de Reel aproximadamente 8,9k; paid engagement 56,28%; paid views 124,32% no relatório histórico. |
| `@robertapfranco` | 50,1k seguidores; 1.874 posts | Micro | 1,24% geral; 0,83% em Reels | Snapshot histórico de 49,5k; fake followers 35,58%; fake likers 7,86%; likes médios 610; plays médios 495k; comentários médios 77; compartilhamentos médios 273; paid engagement 53,90%; paid views 100,60%. |
| `@caroline_tanaka` | 4.049 seguidores; 516 posts | Nano | 1,12% geral; 1,34% recorte analítico | Fake followers 21,52%; categorias de audiência reais/notáveis/massa/suspeitas; diferenças de ER reforçam a necessidade de escopo explícito. |
| `@juuchika` | 6.757 seguidores; 399 posts | Nano | 1,60% | Fake followers 16,28%; impressões 423; alcance 282; likes médios 84,2; comentários médios 21; paid engagement 2,84%; paid views 45,58%. |

Os valores históricos acima são referências observadas em relatórios e não devem ser convertidos automaticamente em fixtures de produção. Os snapshots atuais de seguidores e posts podem ter mudado; a comparação correta exige registrar a data.

### 8.2 Sétimo perfil

O inventário textual e as pastas de evidência do legado localizados até aqui mostram seis perfis reais e uma pasta `plataforma`, não um sétimo perfil. A coorte de produto permanece com uma lacuna aberta: o sétimo handle precisa ser identificado antes de uma análise formal de sete perfis.

### 8.3 Novos perfis de comparação

Novos perfis de moda/lifestyle podem ser escolhidos somente quando responderem a uma pergunta específica: completar uma faixa de porte, testar um formato dominante, comparar uma conta com alta presença de publis ou preencher uma lacuna de conteúdo. Cada abertura deve registrar motivo, porte, handle, data e o que se pretende aprender.

## 9. Reconstrução matemática

### 9.1 O que foi observado diretamente

Foi observado que o Modash apresenta um ER e uma comparação textual relativa ao porte. Também foi observado que o relatório separa All content, Reels e Stories e oferece médias e estimativas diferentes conforme o painel. A plataforma não mostrou no painel lateral a fórmula algébrica completa do ER, o tamanho da amostra ou o algoritmo de benchmark.

### 9.2 O que o legado calculava localmente

O código arquivado do projeto contém fórmulas locais que não devem ser confundidas com a fórmula proprietária do Modash. Entre elas estão:

```text
ER por seguidores = média por post de ((likes + comments) / followers) × 100
ER por alcance = total_interactions / total_estimated_reach × 100
ER por views = total_interactions / total_video_views × 100
ER por formato = (likes_format + comments_format) / (followers × post_count_format) × 100
```

O legado também calcula médias de likes e comentários por post, `pod_index`, taxa de resposta da criadora e uma heurística local de risco de audiência baseada em déficit de ER versus benchmark de porte e repetição de comentaristas. Essas fórmulas são material histórico do métricaDODÔ e não prova da matemática do Modash.

### 9.3 Hipóteses de investigação

As hipóteses a verificar são: se o ER geral usa interações sobre seguidores; se Reels usam likes, comentários e views; se Stories usam impressões/alcance estimados; se o benchmark por porte é uma média, mediana ou distribuição; se o valor “above average” compara uma mesma categoria geográfica ou temática; e se os números pagos são razões patrocinado-versus-orgânico. Nenhuma hipótese deve ser incorporada à regra de negócio antes de evidência suficiente.

### 9.4 Requisitos para considerar uma fórmula confirmada

Uma fórmula somente será considerada confirmada se houver, no mínimo, uma combinação de: tooltip explícito; valor de entrada e saída que permitam replicação; duas ou mais contas de portes diferentes; recorte de conteúdo conhecido; ou evidência consistente em relatório e código de interface. Um único número de OCR nunca é suficiente para provar a equação.

## 10. Fluxo operacional completo

1. Autenticar na plataforma e verificar a cota antes de qualquer busca.
2. Escolher Instagram, TikTok ou YouTube e registrar o canal.
3. Definir se a descoberta será por linguagem natural ou filtros estruturados.
4. Informar handle ou critérios de porte, localização, conteúdo e atividade.
5. Registrar o resultado de busca, o ER resumido e os posts recentes visíveis.
6. Abrir o perfil somente se ele pertence à coorte ou responde a uma hipótese.
7. Registrar o identificador do perfil, data, porte e status da abertura.
8. Ler o painel lateral e separar identidade, collabs, conteúdo, audiência e autenticidade.
9. Comparar `All content`, `Reels` e `Stories` sem misturar denominadores.
10. Registrar estimativas com o rótulo `estimated` e dados indisponíveis como `unavailable`.
11. Cruzar os valores com o relatório histórico correspondente, quando houver.
12. Produzir uma ficha de evidência antes de propor qualquer regra autoral.
13. Encerrar a sessão sem salvar listas, disparar contatos, contratar ou alterar dados comerciais.

## 11. Especificação de um projeto equivalente

Esta seção descreve como um projeto de software poderia ser organizado para reproduzir a **jornada de investigação**, não para copiar a plataforma ou seu algoritmo privado.

### 11.1 Módulos

| Módulo | Responsabilidade |
|---|---|
| `discovery` | Receber critérios, aplicar filtros, ordenar resultados e mostrar a cota. |
| `profile` | Resolver identidade, handle, porte, categoria e links. |
| `report` | Orquestrar o painel lateral e o relatório completo. |
| `content` | Separar All content, Reels, Stories e formatos derivados. |
| `audience` | Organizar demografia, localização, idioma, interesses e cobertura. |
| `authenticity` | Exibir seguidores suspeitos, fake likers e confiança sem afirmar fraude. |
| `collaborations` | Registrar marcas, posts populares, evidências e histórico comercial. |
| `benchmark` | Comparar contas com coorte equivalente e informar a regra de comparação. |
| `provenance` | Guardar fonte, timestamp, amostra, denominador, escopo e ressalvas. |

### 11.2 Estrutura de diretórios sugerida

```text
platform-finder/
├── specs/
│   └── platform-spec.md
├── decisions/
│   └── adr-platform-metric-semantics.md
├── docs/
│   ├── methodology.md
│   ├── evidence-protocol.md
│   └── source-map.md
├── src/
│   ├── discovery/
│   ├── profile/
│   ├── reports/
│   ├── content/
│   ├── audience/
│   ├── collaborations/
│   ├── benchmark/
│   └── provenance/
└── tests/
    ├── test_contracts.py
    ├── test_scopes.py
    └── test_metrics.py
```

### 11.3 Requisitos funcionais

O sistema equivalente deve permitir buscar por handle, aplicar filtros, abrir um relatório, alternar escopos, visualizar métricas com unidade e denominador, comparar portes, registrar a cobertura e exportar uma ficha de auditoria. Deve permitir que uma métrica seja indisponível, estimada ou bloqueada sem convertê-la em zero.

### 11.4 Requisitos não funcionais

O sistema deve ser auditável, determinístico quando operar sobre o mesmo snapshot, econômico em chamadas, protegido contra coleta excessiva, explícito sobre limitações e separado entre UI, coleta, normalização, análise e exportação. A View não deve conter fórmula de negócio escondida.

## 12. Regras de negócio observadas

| Regra | Estado |
|---|---|
| O ER é apresentado com benchmark relativo ao porte. | Observado; fórmula e cortes não confirmados. |
| A busca permite filtrar por seguidores, ER, views, localização e colaborações. | Observado. |
| A plataforma separa All content, Reels e Stories. | Observado. |
| Alcance e impressões podem aparecer como estimados. | Observado. |
| Paid engagement e Paid views são comparações de patrocinado com orgânico. | Semântica indicada pelo tooltip; denominador ainda pendente. |
| Fake followers é apresentado como percentual. | Observado; algoritmo e confiança pendentes. |
| Demografia possui distribuição por gênero, idade, países, cidades e idiomas. | Observado; cobertura deve ser explicitada. |
| Collab, post popular, menção e marca são objetos distintos na UI. | Observado; regra de classificação comercial ainda requer validação. |
| A conta pode ser comparada com criadores “deste porte”. | Observado; corte e universo comparável pendentes. |
| Valores faltantes podem ser ocultados ou aparecer como Hidden. | Observado nos cards; semântica deve ser preservada como indisponível. |
| A cota de perfis e buscas limita a auditoria. | Observado; deve ser tratada como requisito operacional. |

## 13. Como investigar e buscar documentação

A investigação deve começar pelos artefatos do próprio projeto, porque eles preservam contexto, datas e decisões já tomadas. A ordem recomendada é a seguinte.

Primeiro, consultar `BENCHMARK-001.md`, `BENCHMARK-METRICS-001.md`, `FINDER-003.md`, `FINDER-005.md` e `FINDER-006.md` para mapear campos, layouts, fórmulas antigas e diferenças de escopo. Em seguida, consultar `legado/docs/finders/evidencias/BENCHMARK-003/modash.io/`, onde estão organizadas as capturas por porte e handle. Depois, conferir `legado/src/metrics.py`, `legado/src/scoring.py`, `legado/src/scraper.py` e os issues de métricas para separar cálculo local de valor observado em plataforma.

Na sessão autenticada, a busca deve ser feita por handle exato. Depois de abrir um relatório, deve-se registrar o HTML textual, a URL com o identificador do influenciador, os tabs ativos, os tooltips, o texto de cobertura e os valores. A inspeção do DOM e dos bundles deve procurar componentes com termos como `engagementRate`, `averageLikes`, `averageComments`, `averageShares`, `averageReelsPlays`, `estimatedImpressions`, `estimatedReach`, `paidEngagement`, `paidViews`, `fakeFollowers`, `contentScope`, `all`, `reels` e `stories`.

A documentação a ser procurada não precisa ser copiada para este Finder. Basta registrar a trilha de investigação e o que a consulta deve responder: definição da métrica, denominador, janela, amostra, escopo, cobertura, tratamento de ausência, benchmark, confiança e atualização temporal.

## 14. Lacunas, riscos e hipóteses pendentes

A principal lacuna é a fórmula proprietária do ER e sua relação com o benchmark “creators this size”. Também permanecem pendentes os cortes exatos de Nano, Micro, Macro e Mega, a população de referência, a janela temporal, a regra de arredondamento e a política de outliers.

A segunda lacuna é a amostragem. Os relatórios históricos permitem observar valores, mas nem sempre mostram claramente quantos posts foram incluídos. Sem `n`, janela e escopo, médias e taxas não são plenamente comparáveis.

A terceira lacuna é o modelo de estimativas. Alcance e impressões são rotulados como estimados, mas a constante, as variáveis e o tratamento por formato não aparecem na UI observada.

A quarta lacuna é a classificação de autenticidade. “Fake followers” pode combinar sinais de qualidade, comportamento e anomalias; não é seguro tratá-lo como contagem factual de pessoas falsas.

A quinta lacuna é o conteúdo pago. Paid engagement e Paid views parecem ser índices relativos a orgânico, mas um valor acima de 100% mostra que não devem ser lidos como porcentagem de posts patrocinados.

A sexta lacuna é a sétima influenciadora. Os seis perfis documentados no legado são Silvia Braz, Bárbara Studart, Manu Fosco, Roberta Franco, Caroline Tanaka e Juuchika. O sétimo handle ainda não foi localizado nas pastas de evidência e precisa ser identificado antes do benchmark de sete perfis.

## 15. Backlog de investigação

| ID | Investigação | Evidência mínima | Consumo de cota |
|---|---|---|---:|
| PF-001 | Confirmar a fórmula do ER no relatório de Silvia. | Tooltip, DOM ou replicação por valores conhecidos. | Já iniciado. |
| PF-002 | Abrir Manu Fosco e comparar ER geral versus Reels. | Painel lateral completo e recortes. | 1 perfil. |
| PF-003 | Abrir Bárbara Studart e comparar Micro com Silvia. | ER, autenticidade, collabs e conteúdo. | 1 perfil. |
| PF-004 | Abrir Roberta Franco e verificar a divergência geral/Reels. | Dois escopos e amostras. | 1 perfil. |
| PF-005 | Abrir Caroline Tanaka e Juuchika para testar Nano. | ER, amostra, fake followers e formatos. | 2 perfis. |
| PF-006 | Identificar o sétimo perfil da coorte. | Handle confirmado pelo documento ou pelo Dani. | 1 perfil após confirmação. |
| PF-007 | Comparar uma nova conta Mega de moda/lifestyle. | Perfil escolhido por hipótese, não aleatoriamente. | 1 perfil. |
| PF-008 | Comparar paid engagement e paid views em dois portes. | Tooltip e valores em dois relatórios. | Sem nova abertura se relatórios existentes bastarem. |
| PF-009 | Confirmar a janela e o número de posts. | Relatório completo ou evidência de amostra. | Depende do acesso. |
| PF-010 | Mapear a regra de fake followers. | Tooltip/metodologia ou documentação da plataforma. | Sem abertura adicional se houver fonte textual. |

Com a cota observada de 14 aberturas restantes, a ordem racional é PF-002 a PF-005, depois PF-006, e apenas então PF-007. Não se deve executar PF-007 antes de completar a coorte conhecida.

## 16. Portões de aprovação do métricaDODÔ

Nenhuma alteração em `SPEC-001.md`, `BENCHMARK-METRICS-001.md`, ADRs, manifest ou ISSUE-004 deve ser feita com base apenas neste Finder. O processo de aprovação deve seguir quatro portões.

**Portão 1 — Evidência.** O valor precisa estar associado a perfil, data, fonte, escopo e amostra.

**Portão 2 — Reprodução.** A equipe precisa conseguir explicar como o valor foi obtido ou, quando isso não for possível, classificá-lo honestamente como indicador proprietário/estimado.

**Portão 3 — Comparabilidade.** O valor precisa ser comparável entre portes, formatos e janelas equivalentes, sem misturar seguidores com alcance ou All content com Reels.

**Portão 4 — Decisão editorial.** O Dani decide se a métrica é coerente com a visão do métricaDODÔ, com o mercado de moda/lifestyle e com o crivo autoral. Somente após essa decisão a regra pode entrar em SPEC, ADR, ISSUE ou código.

## 17. Rastreabilidade

| Fonte | Papel na investigação |
|---|---|
| `FINDER-001.md` | Certezas técnicas, contratos locais, sessões, datasets e princípios de rastreabilidade. |
| `BENCHMARK-METRICS-001.md` | Modelo autoral atual, fórmulas propostas e equiparação por porte que ainda dependem de aprovação. |
| `legado/SPRINT-002/BENCHMARK-001.md` | Relatório histórico com seis perfis, ERs observados, médias, alcance, impressões, autenticidade e diferenças de escopo. |
| `legado/docs/finders/evidencias/BENCHMARK-003/modash.io/` | Capturas agrupadas por Macro, Micro e Nano e evidências visuais da plataforma. |
| `legado/src/metrics.py` | Fórmulas locais históricas de ER por seguidores, alcance, views e formato; não confundir com fórmula do Modash. |
| `legado/src/scoring.py` | Tiers históricos e Score DODÔ local; heurísticas antigas, não regras soberanas da v2.0.0. |
| `legado/docs/issues/ISSUE-0005.md` | Contratos locais de ER, Score, pod index e ressalvas de engenharia. |
| `modash-audit.md` | Notas de auditoria autenticada, interface, cota, bundles, Silvia e metodologia observada. |
| `coorte-instagram-notes.md` | Snapshots dos seis perfis acessados no Instagram e lacuna do sétimo handle. |

### Estado desta versão

Este Finder consolida o que foi observado e o que permanece em investigação. Ele não é uma aprovação das métricas do Modash, não é uma autorização para copiar fórmulas privadas e não substitui a decisão editorial do Dani. O próximo passo é concluir PF-002 a PF-006 dentro da cota disponível e então apresentar uma matriz comparativa para aprovação.
