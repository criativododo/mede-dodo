## Objetivo

Criar um plano de ação e documentação consolidados para a estruturação da API/App de avaliação de influenciadores (projeto mede-dodo, Sprint 2).

## Papel

Atue como Agente Autônomo de Engenharia de Produto e Análise de Dados. Não atribua autoridades fictícias, mas aja com autonomia para consolidar requisitos técnicos.

## Contexto e Entradas

Utilize obrigatoriamente os seguintes caminhos locais como fonte primária de verdade:

- Imagens de referência (6 prints de influenciadores nanos, micros e macros via Modash): `/Users/danielperrut/0. PROJETO/mede-dodo/SPRINT-002/modash.io`

- Documentação absorvida: `/Users/danielperrut/0. PROJETO/mede-dodo/SPRINT-002/referencias`

- Visão 360 do Projeto (todas as respostas e contexto global): `/Users/danielperrut/0. PROJETO/mede-dodo/DUMMY.md`

- Documentos base da Sprint 002: `/Users/danielperrut/0. PROJETO/mede-dodo/SPRINT-002/FINDER-VIBECODE-001.md` e `/Users/danielperrut/0. PROJETO/mede-dodo/SPRINT-002/ISSUE-NOTEBOOKLM-001.md`

## Escopo

Ler, impreterivelmente, **cada linha** dos documentos Markdown fornecidos e executar OCR/Visão Computacional detalhada em **cada print** da pasta `modash.io`. O que estiver fora destas pastas não faz parte do escopo inicial de leitura.

## Restrições

- **Cota de execução (MUITO IMPORTANTE):** Seu ambiente possui limite de ações. Otimize os comandos; agrupe a leitura de todos os arquivos e imagens em um único bloco operacional antes de passar para a etapa de raciocínio.

- Preserve a nomenclatura técnica original dos documentos.

- Não simule resultados de OCR; extraia exatamente as métricas apresentadas nos prints.

## Método (Fases de Execução)

Siga este fluxo obrigatoriamente nesta ordem:

1. **Mapear e Explorar (Local):** Acesse e leia integralmente `DUMMY.md`, `FINDER-VIBECODE-001.md`, `ISSUE-NOTEBOOKLM-001.md` e a pasta de `referencias`. Inspecione todas as 6 imagens de `modash.io`, extraindo quais métricas exatas são apresentadas.

1. **Pesquisar (Perplexity):** Formule consultas orientadas à decisão baseadas nas métricas extraídas no passo 1. Busque validação técnica sobre o cálculo de taxa de engajamento e detecção de seguidores para estruturação da nossa API.

1. **Consultar (NotebookLM):** Acesse os cadernos do projeto no NotebookLM para cruzar os achados externos com as regras de negócio internas do projeto mede-dodo.

1. **Planejar e Redigir:** Crie a documentação final do plano da SPRINT-002 consolidando todos os achados.

## Ferramentas autorizadas

- Acesso de leitura ao sistema de arquivos (somente nos caminhos indicados).

- Leitura de imagens (Visão Computacional/OCR).

- Navegação Web / Execução de busca para acessar Perplexity e NotebookLM.

## Critérios de qualidade

Verificações objetivas: todas as 6 imagens foram lidas? O plano cobre a visão do `DUMMY.md`? Os achados do Perplexity estão devidamente citados?

## Saída

Entregue o arquivo final salvo no sistema, contendo:

- Conclusões visuais extraídas dos prints.

- Resumo do cruzamento de dados com a documentação local.

- Insights extraídos das buscas (Perplexity/NotebookLM).

- Próximos passos e arquitetura sugerida para a API de métricas.

## Conclusão

A tarefa estará concluída quando o plano estratégico completo estiver consolidado, as métricas dos prints estiverem devidamente listadas e o relatório de execução e limitações for apresentado na resposta final.

# Benchmark funcional e técnico — Avaliação de influenciadores

**Projeto:** métricaDODÔ**Objetivo do documento:** estabelecer uma referência funcional e técnica, inspirada na experiência observada no Modash, para definir o que a funcionalidade de avaliação de influenciadores deve medir, exibir, explicar e disponibilizar para integração.**Data da análise:** 13 de agosto de 2026**Autor:** Manus AI

> **Decisão de enquadramento:** este documento não é um plano de execução da Sprint 002. Ele é um **benchmark de produto**: uma especificação comparativa do comportamento, da superfície de métricas, da experiência de uso e dos contratos de dados que a funcionalidade do métricaDODÔ deve alcançar ou superar.

## 1. Resumo executivo

O Modash apresenta uma experiência de avaliação composta por quatro camadas: descoberta de perfis, resumo rápido do criador, análise da audiência e histórico de conteúdo/colaborações. A referência não se limita a uma taxa de engajamento. Ela combina tamanho da audiência, autenticidade estimada, desempenho de conteúdo, alcance, demografia, interesses, sinais de publicidade e histórico de marcas. Essa composição deve ser tratada como o benchmark da funcionalidade, enquanto cada número precisa conservar sua origem, seu período, seu filtro de conteúdo e seu grau de certeza.

A implementação do métricaDODÔ já possui uma base compatível com parte desse benchmark. O módulo `src/metrics.py` calcula a média de `(curtidas + comentários) / seguidores` por publicação; o `src/database.py` mantém perfis e publicações em SQLite; o `src/scraper.py` implementa cache, janela temporal, throttling e fallback; e o `src/gemini_analyzer.py` faz classificação estruturada de comentários em lotes. A suíte existente foi executada e apresentou **145 testes aprovados e um aviso de depreciação**, o que demonstra estabilidade do estado atual, mas não significa que o benchmark esteja integralmente implementado.

A principal decisão de produto é separar **métricas determinísticas** de **enriquecimentos por IA**. A taxa de engajamento, seguidores, curtidas, comentários, alcance, impressões, demografia e proveniência devem ser calculados ou armazenados como dados verificáveis. O Gemini pode classificar comentários, estimar intenção de compra ou apoiar explicações, mas não deve inventar, substituir ou “corrigir” números observados na fonte.

## 2. Base de evidências e escopo

A análise local utilizou `DUMMY.md`, `SPRINT-002/FINDER-VIBECODE-001.md`, `SPRINT-002/ISSUE-NOTEBOOKLM-001.md`, a pasta `SPRINT-002/referencias`, 44 arquivos PNG da referência Modash e o PDF vertical de referência com dados fictícios. A pasta visual contém seis conjuntos de perfis — dois nano, três micro e um macro — além de uma tela de descoberta da plataforma. A contagem real dos arquivos é importante porque o prompt descrevia “seis prints”, mas a evidência disponível é composta por **44 capturas organizadas em seis conjuntos de influenciadores e uma tela geral da plataforma**.

| Conjunto de referência | Porte observado | Capturas | Índices do manifesto OCR | Função principal observada |
| --- | --- | --- | --- | --- |
| `@silviabraz` | Macro | 8 | 001–008 | Resumo, crescimento, qualidade da audiência, demografia, interesses, tags e menções |
| `@barbarastudart` | Micro | 4 | 009–012 | Resumo, curtidas falsas, desempenho e audiência |
| `@manurefosco` | Micro | 8 | 013–020 | Resumo, desempenho, Reels, demografia e colaborações |
| `@robertapfranco` | Micro | 8 | 021–028 | Resumo, Reels, distribuição de engajamento, reachability e demografia |
| `@caroline_tanaka` | Nano | 8 | 029–036 | Resumo, crescimento, qualidade da audiência, demografia e colaborações |
| `@juuchika` | Nano | 7 | 037–043 | Resumo, qualidade da audiência, demografia e colaborações |
| Tela de descoberta da plataforma | — | 1 | 044 | Busca, filtros, canais, perfis salvos e cards comparáveis |
| **Total** | — | **44** | **001–044** | — |

A extração visual foi feita por OCR em todos os PNGs. Quando uma leitura numérica ficou ambígua por escala, compressão ou recorte, ela não foi transformada em requisito. Os valores abaixo distinguem métricas legíveis de forma confiável de sinais que devem ser confirmados manualmente antes de se tornarem dados de teste.

## 3. O que o benchmark precisa representar

A experiência de referência pode ser reduzida ao seguinte modelo mental:

> **Perfil → qualidade da audiência → desempenho do conteúdo → demografia e afinidade → histórico comercial → decisão de contratação.**

O benchmark deve permitir que uma pessoa responda, em poucos minutos, a cinco perguntas. Primeiro, quem é o criador e qual é o tamanho real da audiência? Segundo, a audiência parece autêntica ou existem sinais de seguidores falsos e comportamento suspeito? Terceiro, o conteúdo gera interação, alcance e visualizações compatíveis com o porte? Quarto, a audiência está no país, cidade, idade, gênero, idioma e interesses desejados? Quinto, o histórico de colaborações e os sinais de publicidade fazem sentido para a marca?

A resposta não deve ser um score opaco. O produto deve apresentar um resumo acionável, permitir abrir o detalhe de cada componente e informar se o valor é **observado**, **derivado**, **estimado**, **proveniente da plataforma** ou **indisponível**.

## 4. Catálogo de métricas do benchmark

### 4.1 Identidade e descoberta do perfil

| Grupo | Métrica ou elemento | Exibição de referência | Regra de benchmark para o métricaDODÔ | Prioridade |
| --- | --- | --- | --- | --- |
| Identidade | Nome, username, avatar e localização | Card e cabeçalho do perfil | Exibir valor bruto, origem e data de coleta | P0 |
| Identidade | Bio, categorias e nichos | “Moda”, “Beleza”, “Bem-estar”, “Modelo”, entre outros | Armazenar texto bruto e categorias normalizadas separadamente | P0 |
| Tamanho | Seguidores | `2,2 milhões`, `55,3 mil`, `49,5 mil`, `6,7 mil` | Guardar inteiro canônico e string formatada; nunca usar a string como dado numérico | P0 |
| Conteúdo | Filtro de escopo | “Todo o conteúdo”, “Carretel/Reels”, “Histórias/Stories” | Todo resultado deve declarar `content_scope` | P0 |
| Descoberta | Busca, filtros, canais e perfis salvos | Instagram, TikTok, YouTube, busca e filtros salvos | Benchmark futuro de descoberta; não misturar com auditoria de um único perfil | P1 |
| Relacionamento | Links sociais e e-mail | Links sociais e e-mail bloqueado/desbloqueado | Tratar disponibilidade e permissão como estado, não como texto inventado | P1 |

### 4.2 Desempenho de conteúdo

| Métrica | Definição recomendada | Evidência visual | Regra de implementação |
| --- | --- | --- | --- |
| Taxa de engajamento por seguidores | Média, por publicação, de `(curtidas + comentários) / seguidores × 100` | Valores observados de 0,77%, 0,83%, 1,03%, 1,12%, 1,24%, 1,34% e 1,60% | É o cálculo atualmente existente em `src/metrics.py`; declarar janela, número de posts e ações incluídas |
| Taxa de engajamento por alcance | `interações / alcance × 100` | A interface mostra alcance estimado em conjunto com a taxa | Implementar como métrica distinta; não substituir silenciosamente a taxa por seguidores |
| Taxa de engajamento por visualizações | `interações / visualizações × 100` | Necessária para Reels e vídeos | Usar apenas quando visualizações e interações tiverem a mesma janela e o mesmo objeto |
| Curtidas médias | Média de curtidas por publicação | 23,8 mil em `@silviabraz`, 572 em `@barbarastudart`, 610 em `@robertapfranco`, 84,2 em `@juuchika` | Guardar soma, quantidade de posts e média; evitar arredondar o valor persistido |
| Comentários médios | Média de comentários por publicação | 299 em `@silviabraz`, 59 em `@barbarastudart`, 49 em `@robertapfranco`, 21 em `@juuchika` | Manter separado de curtidas para medir profundidade de interação |
| Compartilhamentos e salvamentos | Ações de intenção ou distribuição | Aparecem como sinais de conteúdo em plataformas de analytics; a referência visual mostra compartilhamentos em Reels | Armazenar quando a origem fornecer; não inferir a partir de curtidas |
| Visualizações médias de Reels | Média de plays por Reel | 495 mil em `@robertapfranco` e aproximadamente 8,9 mil no recorte de Reels de `@manurefosco` | Declarar `media_product_type=REELS` e a janela de posts |
| Alcance estimado | Contas alcançadas | 483 mil em `@silviabraz`, 2,2 mil em `@barbarastudart` e 282 em `@juuchika` | É uma estimativa de plataforma; apresentar como estimativa, não como medição própria |
| Impressões estimadas | Exibições totais | 724,4 mil em `@silviabraz` e 423 no recorte visual de `@juuchika` | Diferenciar impressões de alcance; preservar o timestamp e a fonte |
| Engajamento pago | Fração ou sinal de interação associada a mídia paga | 72,74% em `@silviabraz`, 56,28% em `@manurefosco`, 53,90% em `@robertapfranco` e 2,84% em `@juuchika` | A semântica exata do denominador da interface ainda precisa de validação; armazenar como métrica de origem e não recalcular por aproximação |
| Visualizações pagas | Fração ou sinal de views associadas a mídia paga | Mostrada junto ao engajamento pago | Exigir definição de origem antes de usar em score comparativo |

A documentação pública do Modash descreve a fórmula de taxa de engajamento por seguidores como o total de engajamentos dividido pelo número de seguidores, multiplicado por 100.[4] A documentação independente da Hootsuite confirma que não existe um único denominador universal: alcance, seguidores, impressões e visualizações respondem a perguntas diferentes.[7] Portanto, o benchmark exige que a API devolva não apenas `engagement_rate`, mas também `engagement_rate_type`, `denominator`, `included_actions`, `window` e `source`.

### 4.3 Qualidade e autenticidade da audiência

| Métrica | Exibição observada | Benchmark funcional |
| --- | --- | --- |
| Seguidores falsos | Percentual no resumo do perfil | Exibir como estimativa de um detector, com modelo, data, confiança e explicação de que não é uma classificação individual definitiva |
| Curtidas falsas | Percentual de likes suspeitos | Separar de seguidores falsos; `@barbarastudart` exibe 11,77% e `@robertapfranco` 7,86% |
| Pessoas reais | Categoria da composição da audiência | Exibir dentro de uma distribuição que fecha em 100%, quando a fonte permitir |
| Seguidores notáveis | Categoria de perfis com relevância ou autoridade | Preservar o nome da categoria da fonte |
| Seguidores de massa | Categoria de perfis que seguem grande quantidade de contas | Não converter automaticamente em “falso” |
| Massa suspeita | Categoria de comportamento anômalo | Exibir como sinal, não como acusação |
| Contas suspeitas | Categoria de risco ou inautenticidade | Exibir o critério e o nível de confiança |
| Distribuição de seguidores falsos | Histograma ou distribuição comparativa | Usar para benchmarking entre criadores; não reduzir toda a análise a um único percentual |
| Reachability | Faixas de contas alcançáveis | `@robertapfranco` mostra faixas `<500`, `500–1k`, `1k–1,5k` e `>1,5k` |
| Índice de pod | Repetição de comentaristas entre posts | Já existe como `pod_index` em `src/metrics.py` |

Os prints apresentam, entre outros valores, 23,90% de seguidores falsos para `@silviabraz`, 37,92% para `@barbarastudart`, 20,46% para `@manurefosco`, 35,58% para `@robertapfranco`, 21,52% para `@caroline_tanaka` e 16,28% para `@juuchika`. Esses valores são **observações da referência visual**, não ground truth sobre as contas. O benchmark deve reproduzir o tipo de métrica e sua explicabilidade, não alegar que um detector local possui a mesma precisão do Modash.

A HypeAuditor descreve a detecção de audiência falsa como uma análise multifatorial que pode considerar proporção de seguidores/seguidos, posts, curtidas, comentários, relação curtidas-comentários, crescimento e autenticidade do engajamento.[5] Isso reforça a decisão de tratar `fake_followers_rate` como uma saída probabilística composta por evidências, e não como simples `100% - pessoas_reais`.

### 4.4 Demografia e afinidade

| Dimensão | Exemplos observados | Requisito do benchmark |
| --- | --- | --- |
| Gênero | Distribuições por feminino e masculino em todos os conjuntos | Armazenar categorias e percentuais; permitir “desconhecido” e não assumir binariedade como verdade universal |
| Idade | Faixas `13–17`, `18–24`, `25–34`, `35–44`, `45–64` | Manter faixa, percentual, período e cobertura amostral |
| País | Brasil, Estados Unidos, Portugal, Itália, México, Espanha, entre outros | Normalizar para código ISO quando possível e manter o rótulo original |
| Cidade | São Paulo, Rio de Janeiro, Belo Horizonte, Porto Alegre, Curitiba, Campinas, entre outras | Preservar cidade e país; evitar geocodificação obrigatória para usar a métrica |
| Idioma | Português, inglês, espanhol, italiano, árabe, russo, alemão, japonês | Guardar código normalizado e rótulo de origem |
| Interesses | Roupas, beleza, viagens, fotografia, fitness, alimentação, família, esportes, pets e carros | Modelar como lista ordenada com peso, posição ou frequência quando a fonte fornecer |
| Tags populares | Hashtags como `#tiffanyandco`, `#publicidade`, `#alphavilleeregiao` e `#mentepositiva` | Guardar texto, frequência e data da observação |
| Menções | Marcas e perfis mencionados, como `@tiffanyandco`, `@balenciaga`, `@jescrilingerie` e `@caroline_tanaka` | Separar menções de colaborações pagas ou confirmadas |

Os dados de audiência não devem ser tratados como soma obrigatoriamente igual ao total de seguidores. A documentação oficial da Meta informa que métricas demográficas usam somente as pessoas para as quais há dados demográficos disponíveis e podem retornar soma menor que a base total.[8] Essa regra precisa aparecer no produto como cobertura, ressalva ou tooltip.

### 4.5 Colaborações e histórico comercial

A referência mostra uma área de atividade de colaboração com busca por marca, filtro de categoria, ordenação temporal, mix de categorias e uma linha do tempo de marcas. Também há cards de posts populares e marcas associadas. O benchmark deve separar quatro conceitos: **menção**, **conteúdo com marca**, **colaboração identificada** e **classificação comercial inferida**. Uma menção não é prova suficiente de publicidade.

| Objeto de histórico | Campos mínimos |
| --- | --- |
| Colaboração | marca, perfil, data ou mês, mídia, evidência, confiança |
| Categoria | categoria original, categoria normalizada, percentual ou contagem, período |
| Post comercial | URL ou ID, legenda, sinal de publicidade, marca detectada, método de detecção |
| Mix de categorias | categorias, proporção, total de eventos e cobertura da amostra |
| Linha do tempo | eventos ordenados, data de coleta e intervalo observado |

## 5. Benchmark visual e de experiência

### 5.1 Tela de descoberta

A tela geral de descoberta exibe canais Instagram, TikTok e YouTube, busca por criadores, filtros salvos, contagem de perfis, limite de pesquisas, cards com seguidores, taxa de engajamento, descrição, posts e ações como salvar, abrir perfil e encontrar semelhantes. Esse é um benchmark de **descoberta e comparação**, não deve ser confundido com o benchmark da página de auditoria.

A referência mostra também uma restrição de uso do produto — “14 days left”, `0/20 profiles` e `0% searches` — além de filtros de localização, colaborações e criadores salvos. Para o métricaDODÔ, essa parte deve ser implementada somente depois da auditoria unitária estar confiável, pois busca em escala aumenta custo de coleta, risco de bloqueio e necessidade de cache.

### 5.2 Página de resumo do influenciador

O cabeçalho deve concentrar identidade, porte, localização, categorias, links sociais, estado de e-mail e ações para abrir relatório completo. O resumo precisa ser legível sem abrir todas as abas: seguidores, taxa de engajamento, seguidores falsos, curtidas médias, comentários médios, alcance e impressões.

Uma diferença fundamental em relação a um painel genérico é que o filtro de conteúdo precisa permanecer visível. `@robertapfranco`, por exemplo, aparece com 1,24% no recorte geral e 0,83% em um recorte de Reels. `@manurefosco` aparece com 1,12% no resumo e 0,77% no recorte que exibe plays, curtidas, comentários e compartilhamentos. Isso não deve ser tratado como inconsistência de dados sem antes verificar `content_scope`, janela, número de posts e método de cálculo.

### 5.3 Página de audiência

A página deve começar com a distribuição de qualidade da audiência e seguir para gênero, idade, países, cidades e idiomas. O layout de referência usa gráficos, percentuais e rankings curtos. Para uma primeira versão, tabelas ordenadas e barras horizontais são suficientes, desde que o usuário veja a cobertura, o período e a origem.

### 5.4 Página de afinidade e histórico

Interesses, tags, menções e colaborações formam a camada de adequação comercial. A referência usa listas compactas e visualizações de histórico. O benchmark não exige reproduzir a estética pixel a pixel; exige preservar a pergunta que a tela responde: “a audiência e o histórico deste criador são adequados para a marca?”

## 6. Contrato de dados recomendado

O objeto principal deve ser uma auditoria versionada, e não apenas um registro de perfil. O contrato mínimo abaixo é suficiente para separar identidade, observações brutas, métricas derivadas e estimativas externas.

```json
{
  "audit_id": "uuid",
  "platform": "instagram",
  "handle": "silviabraz",
  "profile": {
    "display_name": "Silvia Bussade Braz",
    "followers_count": 2200000,
    "bio": "...",
    "location": "São Paulo, Brasil",
    "categories": ["Moda", "Viagens", "Estilo de Vida", "Maternidade"]
  },
  "collection": {
    "collected_at": "2026-08-13T18:00:00Z",
    "window_days": 90,
    "content_scope": "all_content",
    "source": "local_scraper",
    "source_version": "instaloader-4.15.3",
    "status": "complete|partial|stale|failed"
  },
  "metrics": {
    "engagement_rate": {
      "value": 0.0112,
      "unit": "ratio",
      "type": "by_followers",
      "denominator": "followers_count",
      "included_actions": ["likes", "comments"],
      "post_count": 12,
      "kind": "derived",
      "confidence": "high"
    },
    "followers_count": {"value": 2200000, "kind": "observed"},
    "fake_followers_rate": {
      "value": 0.239,
      "kind": "estimated",
      "model": "audience_quality_v1",
      "confidence": "medium"
    },
    "average_likes": {"value": 23800, "kind": "derived"},
    "average_comments": {"value": 299, "kind": "derived"},
    "estimated_reach": {"value": 483000, "kind": "source_estimate"},
    "estimated_impressions": {"value": 724400, "kind": "source_estimate"}
  },
  "audience": {
    "gender": [],
    "age": [],
    "countries": [],
    "cities": [],
    "languages": [],
    "interests": [],
    "quality_distribution": []
  },
  "provenance": [],
  "warnings": []
}
```

Os valores monetários, e-mails, links e dados de contato devem possuir controles de permissão independentes. O contrato também precisa distinguir `null` de zero: a Meta documenta que uma métrica ausente ou indisponível pode retornar conjunto vazio, e não necessariamente `0`.[6] A interface deve mostrar “indisponível” ou “sem dados” nesses casos.

## 7. Regras de cálculo e proveniência

### 7.1 Taxas de engajamento

A funcionalidade deve suportar, no mínimo, três taxas:

| Nome | Fórmula | Uso |
| --- | --- | --- |
| `engagement_rate_by_followers` | média de `(likes + comments) / followers × 100` por post | Comparação estável entre criadores |
| `engagement_rate_by_reach` | `total_interactions / reach × 100` | Eficiência entre pessoas que efetivamente viram o conteúdo |
| `engagement_rate_by_views` | `total_interactions / views × 100` | Reels e vídeos |

A API nunca deve retornar `engagement_rate` sem indicar qual destas fórmulas foi aplicada. A documentação da Meta define `total_interactions` como likes, saves, comments e shares, com ajustes de ações removidas, para tipos de mídia compatíveis.[6] A implementação atual do métricaDODÔ usa apenas likes e comments, portanto está alinhada a uma taxa de perfil simples, mas ainda não é equivalente a uma taxa baseada em `total_interactions` da API oficial.

### 7.2 Seguidores falsos e autenticidade

O benchmark exige três camadas de saída: o percentual estimado, a decomposição dos sinais e a confiança. Sinais possíveis incluem proporção follower/following, atividade do perfil, foto, número de posts, padrões de comentários, repetição entre posts, crescimento anômalo e discrepância entre visualizações, alcance e seguidores. O produto deve evitar linguagem acusatória. O texto recomendado é “estimativa de audiência potencialmente inautêntica” ou “sinal de risco”, sempre com método e data.

### 7.3 Demografia

Toda distribuição demográfica deve carregar `period`, `coverage`, `source` e `is_estimated`. A Meta informa que seus insights de conta podem ter atraso de até 48 horas, que alguns dados não estão disponíveis para contas com menos de 100 seguidores e que demografia retorna apenas os principais resultados.[8] Esses limites devem ser refletidos no estado da métrica.

### 7.4 Conteúdo pago

As capturas mostram “engajamento pago” e “visualizações pagas”, mas a semântica do denominador não foi confirmada na documentação pública consultada. Consequentemente, o benchmark define a presença visual e o armazenamento da métrica, mas não autoriza usá-la em score até que sua fórmula seja documentada por fonte ou por experimento controlado.

## 8. Separação entre dados do benchmark e Gemini

O Gemini deve ocupar uma posição complementar. Ele é adequado para classificar comentários já coletados, detectar intenção de compra, estimar faixa etária textual com ressalvas, resumir padrões e gerar explicações legíveis. Ele não deve ser usado para calcular seguidores, taxa de engajamento, alcance, impressões ou porcentagens demográficas quando esses dados podem ser obtidos da coleta ou da fonte oficial.

O projeto já possui um contrato estruturado para classificação de comentários e um limite de dois lotes de até 100 comentários. O fluxo benchmarkeado deve ser: coletar → filtrar localmente → consultar cache → enviar apenas comentários qualificados → validar JSON → guardar modelo, prompt versionado, timestamp e falhas. A regra de `DUMMY.md` de não enviar comentários rasos ao Gemini é coerente com essa separação.[1]

## 9. Confronto com o estado atual do projeto

| Capacidade | Estado observado no repositório | Relação com o benchmark | Lacuna principal |
| --- | --- | --- | --- |
| Coleta local | `src/scraper.py` usa sessão, janela de posts, throttling e fallback de cache | Compatível com a camada de ingestão | Falta contrato único de auditoria e status de completude |
| Cache | `data/cache.db` possui `profiles` e `posts_cache` | Compatível com persistência local | Precisa guardar versão do cálculo, origem, filtro e validade da métrica |
| Taxa de engajamento | `src/metrics.py` calcula likes + comments por seguidores | Cobre o ER básico do benchmark | Falta suporte explícito a alcance, views, shares, saves e escopo de conteúdo |
| Qualidade da audiência | `pod_index` sinaliza repetição de comentaristas | Complementar ao detector de audiência | Não equivale a seguidores falsos; precisa de modelo e explicabilidade próprios |
| Score | `src/scoring.py` usa pesos e benchmarks heurísticos por porte | Pode ser camada de decisão posterior | Pesos ainda não são benchmark validado; não devem ocultar métricas brutas |
| Gemini | `src/gemini_analyzer.py` usa JSON, lotes e tratamento de quota | Adequado como enriquecimento | Deve permanecer fora da fonte de verdade das métricas |
| Segurança | `.env` ignorado, SQLite parametrizado e regras deny-by-default documentadas | Compatível | Há uma divergência: `DUMMY.md` proíbe apagar cache sem autorização, mas `clear_profile_cache` implementa exclusão; a UX precisa exigir confirmação explícita |
| Validação | 145 testes aprovados | Base confiável para evolução | Ainda não há testes de contrato para cada métrica do benchmark e para `metric_source` |
| Dependências | `google-genai==2.17.0`, `instaloader==4.15.3`, Streamlit, fpdf2 e pytest | Alinhado ao documento de referência | Validar compatibilidade do SDK e manter o aviso de depreciação sob acompanhamento |

## 10. Priorização funcional do benchmark

### P0 — Núcleo mínimo de avaliação

O núcleo deve permitir informar um perfil, coletar os dados em background, exibir o cabeçalho, seguidores, taxa de engajamento por seguidores, curtidas médias, comentários médios, janela de análise, número de publicações, seguidores potencialmente inautênticos com ressalva, status da coleta e data da última atualização. Deve haver filtros explícitos para todo conteúdo, Reels e Stories quando houver dados suficientes.

O núcleo também precisa expor a origem de cada número. Sem isso, o usuário não saberá se o sistema observou a métrica, calculou a partir de posts, recebeu uma estimativa ou não encontrou dados. A presença da proveniência é parte do benchmark, não um detalhe de engenharia.

### P1 — Análise de audiência e adequação

A segunda camada deve incluir qualidade da audiência, distribuição de seguidores, gênero, idade, países, cidades, idiomas, interesses, tags e menções. A interface pode começar com tabelas e barras simples; o critério de aceite é a consistência semântica, não a reprodução visual exata do Modash.

### P2 — Histórico comercial e descoberta

A terceira camada deve incluir colaborações, marcas, mix de categorias, linha do tempo, busca de perfis, filtros salvos, perfis semelhantes e comparação em lote. Essa camada exige maior volume de coleta e deve ser construída somente depois de a auditoria unitária fechar seus contratos e testes.

## 11. Critérios de aceitação do benchmark

| ID | Critério verificável |
| --- | --- |
| B-01 | A auditoria identifica plataforma, handle, nome, seguidores, data e janela de coleta. |
| B-02 | Toda taxa de engajamento informa fórmula, denominador, ações incluídas, escopo e quantidade de posts. |
| B-03 | Um perfil pode apresentar taxas diferentes por escopo — por exemplo, geral e Reels — sem que a interface trate isso como erro automático. |
| B-04 | Métricas ausentes são retornadas como `null` ou estado “indisponível”, nunca como zero silencioso. |
| B-05 | Seguidores falsos, curtidas falsas e sinais de pod são campos distintos e carregam confiança, método e data. |
| B-06 | As distribuições demográficas registram cobertura e período, inclusive quando não fecham no total de seguidores. |
| B-07 | O usuário consegue abrir o detalhe que explica de onde cada métrica veio. |
| B-08 | O Gemini recebe apenas comentários filtrados e não altera métricas determinísticas. |
| B-09 | Cache, fallback e status parcial são visíveis; uma falha de coleta não produz um relatório aparentemente completo. |
| B-10 | Cada métrica do contrato possui pelo menos um teste com dado conhecido, um teste de ausência e um teste de escopo. |
| B-11 | A remoção de cache exige autorização explícita e não viola as regras de proteção do projeto. |
| B-12 | A suíte atual permanece verde; a execução observada foi de 145 testes aprovados. |

## 12. Limitações e pendências de validação

A consulta direta aos cadernos NotebookLM citados nos documentos não foi concluída porque a sessão do Google abriu a tela de autenticação e permaneceu sem login confirmado. O conector Perplexity também estava desabilitado na configuração da sessão. Por isso, as conclusões externas deste benchmark foram validadas com documentação pública do Modash, HypeAuditor, Hootsuite e Meta; elas não devem ser apresentadas como um cruzamento efetivamente realizado dentro do NotebookLM ou do Perplexity.

A inspeção visual foi complementada por OCR nos 44 PNGs. Alguns textos da interface estavam comprimidos, em inglês, parcialmente cortados ou com contraste insuficiente. Os valores expressamente listados como observações foram usados apenas quando legíveis ou consistentes com o fechamento da distribuição; os valores pagos, alguns valores de impressões e algumas categorias de colaboração precisam de confirmação manual antes de se tornarem fixtures de teste.

A API oficial da Meta é orientada a contas profissionais autorizadas, com permissões, tokens e níveis de acesso. A documentação da Meta informa que Advanced Access é necessário quando o aplicativo atende contas profissionais que não são próprias ou administradas pelo desenvolvedor, e que dados públicos fora da conta autorizada são limitados.[5] Portanto, a coleta estilo Modash e a integração oficial da Meta são fontes diferentes: o benchmark deve permitir `source=local_public_collection`, `source=meta_insights`, `source=platform_estimate` e `source=unavailable`, sem misturar seus níveis de autoridade.

A referência visual não fornece ground truth sobre seguidores falsos, alcance ou impressões. Ela fornece o que uma ferramenta madura escolhe mostrar. O benchmark mede a **superfície funcional e a qualidade do contrato**, não promete que o métricaDODÔ reproduzirá a precisão proprietária do Modash em sua primeira versão.

## 13. Decisão final de benchmark

A funcionalidade deve ser considerada benchmarkeada quando transformar uma coleta de perfil em um relatório auditável com quatro propriedades: **comparabilidade**, porque as fórmulas e filtros são explícitos; **contexto**, porque cada valor tem período, escopo e cobertura; **explicabilidade**, porque sinais de autenticidade e score podem ser abertos; e **resiliência**, porque cache, falha parcial e origem do dado são visíveis.

O maior erro a evitar é construir primeiro um “score de influenciador” e só depois tentar explicar seus componentes. A ordem correta é o contrário: implementar o inventário de métricas e a proveniência observados no Modash, validar os cálculos com fixtures, expor as diferenças entre fontes e somente então adicionar um score DODÔ como camada opcional de decisão. O Gemini entra depois da coleta e da filtragem, como mecanismo de interpretação textual e não como autoridade numérica.

## Referências

[1]: ../DUMMY.md — **DUMMY.md — Safety Shield e Restrições Negativas**, documentação local do projeto.

[2]: FINDER-VIBECODE-001.md — **Guia de Engenharia e Especificação Técnica: Projeto métricaDODÔ**, documentação local da Sprint 002.

[3]: ISSUE-NOTEBOOKLM-001.md — **Checklist técnico final para Go Live**, documentação local da Sprint 002.

[4]: [https://www.modash.io/blog/how-to-check-influencer-engagement-rate](https://www.modash.io/blog/how-to-check-influencer-engagement-rate) — Modash, **How To Check Influencer Engagement Rate In 30 Seconds**.

[5]: [https://www.modash.io/data](https://www.modash.io/data) — Modash, **Our Data**.

[6]: [https://hypeauditor.com/free-tools/instagram-fake-follower-check/](https://hypeauditor.com/free-tools/instagram-fake-follower-check/) — HypeAuditor, **Free Instagram Fake Followers Checker**.

[7]: [https://blog.hootsuite.com/calculate-engagement-rate/](https://blog.hootsuite.com/calculate-engagement-rate/) — Hootsuite, **How to Calculate Engagement Rate: 2026 Formulas and Benchmarks**.

[8]: [https://developers.facebook.com/documentation/instagram-platform/overview](https://developers.facebook.com/documentation/instagram-platform/overview) — Meta for Developers, **Instagram Platform Overview**, atualizado em 30 de junho de 2026.

[9]: [https://developers.facebook.com/documentation/instagram-platform/insights](https://developers.facebook.com/documentation/instagram-platform/insights) — Meta for Developers, **Instagram Platform Insights**.

[10]: [https://developers.facebook.com/documentation/instagram-platform/reference/instagram-media/insights](https://developers.facebook.com/documentation/instagram-platform/reference/instagram-media/insights) — Meta for Developers, **Instagram Media Insights**, atualizado em 18 de junho de 2026.

[11]: [https://developers.facebook.com/documentation/instagram-platform/api-reference/instagram-user/insights](https://developers.facebook.com/documentation/instagram-platform/api-reference/instagram-user/insights) — Meta for Developers, **Instagram Account Insights**, atualizado em 16 de junho de 2026.

[12]: [https://notebook.google.com/notebook/424cafb4-25ad-4d15-bc2c-fd62196c7258](https://notebook.google.com/notebook/424cafb4-25ad-4d15-bc2c-fd62196c7258) — Caderno NotebookLM citado em `FINDER-VIBECODE-001.md`; acesso direto pendente de autenticação.

[13]: [https://notebook.google.com/notebook/62f4b450-72af-4b89-b32a-b05c91765b96](https://notebook.google.com/notebook/62f4b450-72af-4b89-b32a-b05c91765b96) — Caderno NotebookLM citado em `ISSUE-NOTEBOOKLM-001.md`; acesso direto pendente de autenticação.

## Anexo A — Resumo numérico dos seis perfis observados

| Perfil | Seguidores exibidos | ER observado no resumo | Outros sinais legíveis |
| --- | --- | --- | --- |
| `@silviabraz` | 2,2 milhões | 1,12% | Seguidores falsos 23,90%; impressões estimadas 724,4 mil; alcance estimado 483 mil; curtidas médias 23,8 mil; comentários médios 299 |
| `@barbarastudart` | 55,3 mil | 1,03% | Seguidores falsos 37,92%; curtidas falsas 11,77%; alcance estimado 2,2 mil; curtidas médias 572; comentários médios 59 |
| `@manurefosco` | 22,2 mil | 1,12% no resumo; 0,77% no recorte de Reels | Seguidores falsos 20,46%; comentários médios 24 no recorte geral; plays médios de Reel aproximadamente 8,9 mil no recorte visual |
| `@robertapfranco` | 49,5 mil | 1,24% no resumo; 0,83% no recorte de Reels | Seguidores falsos 35,58%; curtidas falsas 7,86%; curtidas médias 610; plays médios 495 mil; comentários médios 77; compartilhamentos médios 273 |
| `@caroline_tanaka` | 4 mil | 1,12% no resumo; 1,34% no recorte analítico | Seguidores falsos 21,52%; audiência com categorias de pessoas reais, notáveis, massa e suspeitas; a diferença de ER reforça a necessidade de escopo explícito |
| `@juuchika` | 6,7 mil | 1,60% | Seguidores falsos 16,28%; impressões estimadas 423; alcance estimado 282; curtidas médias 84,2; comentários médios 21; engajamento pago 2,84%; visualizações pagas 45,58% |

Os números deste anexo são **exemplos observados na referência**, não valores de produção nem dados de teste definitivos. Antes de transformá-los em fixtures, a equipe deve confirmar manualmente os recortes em que o OCR identificou texto parcial ou valores que dependem da semântica proprietária da plataforma.

## Anexo B — Checklist de implementação orientada pelo benchmark

| Ordem | Entrega de referência | Resultado esperado |
| --- | --- | --- |
| 1 | Auditoria unitária com proveniência | Um perfil gera relatório com estado, origem, janela, escopo e data |
| 2 | Métricas determinísticas | Seguidores, posts, likes, comments e ER por seguidores reproduzíveis |
| 3 | Escopos de conteúdo | Geral, Reels e Stories não são misturados |
| 4 | Audiência e demografia | Categorias ordenadas, cobertura e ressalvas de disponibilidade |
| 5 | Qualidade da audiência | Sinais probabilísticos separados de métricas observadas |
| 6 | Histórico e afinidade | Interesses, tags, menções e colaborações com evidência |
| 7 | Gemini opcional | Comentários filtrados, JSON validado, cache e falhas explícitas |
| 8 | Score opcional | Camada posterior, calibrável e sempre explicável pelos componentes |
| 9 | Descoberta e comparação | Busca em lote, filtros, perfis salvos e exportação |
| 10 | Validação contínua | Fixtures reais anonimizadas, testes de ausência, escopo e fonte |

