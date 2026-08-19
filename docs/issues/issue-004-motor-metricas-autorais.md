# ISSUE-004 — Motor de Métricas Autorais

**Projeto:** métricaDODÔ v2.0.0  
**Tipo:** Feature de domínio / motor analítico  
**Status:** `implemented` — núcleo Rodada 1 (Seção 3) e Rodadas 2/3 (Seção 4, aprovadas 2026-08-15 via ADR-002) implementados em `metrics.py`. Ressalva física: BQI completo e CI dependem de sinais (`save_rate`/`share_rate`/`VTR`/`alcance_qualificado` para o Pilar 2; piso aprovado para o CI) que a coleta pública via Instaloader não expõe — retornam `indisponivel` em auditorias reais até uma expansão futura do coletor (fora de escopo desta issue). Tipologia/`V_AB`/Pilar 1 e Saturação de Publis (SD) já são reais hoje.  
**Prioridade:** Alta  
**Dependências:** ISSUE-002, ISSUE-003, Rodadas 1/2/3 da consultoria aprovadas  
**Bloqueios:** Nenhum bloqueio de aprovação restante. Limitação física registrada: expansão do coletor para `save_rate`/`share_rate`/`VTR`/`alcance_qualificado` fica para uma issue futura.  
**Implementação:** `src/features/analise/metrics.py` (Rodada 1 — ER Branding; Rodadas 2/3 — tipologia/P1, P2, P3, BQI, CI, SD, parecer editorial combinado)  
**Testes:** `tests/test_metrics.py` (50/50 passando)

## Sumário

1. [Objetivo](#1-objetivo)  
2. [Regra de governança](#2-regra-de-governança)  
3. [Decisões já aprovadas](#3-decisões-já-aprovadas)  
4. [Decisões ainda pendentes](#4-decisões-ainda-pendentes)  
5. [Escopo funcional](#5-escopo-funcional)  
6. [Contrato de entrada](#6-contrato-de-entrada)  
7. [Contrato de saída](#7-contrato-de-saída)  
8. [Arquitetura da implementação](#8-arquitetura-da-implementação)  
9. [Requisitos funcionais](#9-requisitos-funcionais)  
10. [Requisitos de qualidade](#10-requisitos-de-qualidade)  
11. [Plano de testes](#11-plano-de-testes)  
12. [Critérios de aceite](#12-critérios-de-aceite)  
13. [Fora de escopo](#13-fora-de-escopo)  
14. [Próximo portão](#14-próximo-portão)  
15. [Rastreabilidade](#15-rastreabilidade)

## 1. Objetivo

Construir o motor Python puro responsável por calcular, documentar e devolver as métricas autorais do métricaDODÔ a partir de um payload de posts, perfil, comentários classificados e dados de cobertura. O motor deverá ser determinístico, auditável e independente da camada visual, da coleta de dados e dos exportadores.

A ISSUE-004 não pretende reproduzir automaticamente a fórmula proprietária do Modash. Os relatórios da plataforma serão utilizados como referência de investigação e benchmarking, mas as fórmulas do métricaDODÔ continuarão sendo decisões editoriais próprias, co-criadas e aprovadas pelo Dani [1] [2].

## 2. Regra de governança

> **Atualização (2026-08-15, núcleo Rodada 1):** o Dani autorizou explicitamente a superação do bloqueio para o **núcleo da Rodada 1** (Seção 3 — ER Branding, pesos de ação/formato, denominador misto, isolamento de Stories). `metrics.py` e `tests/test_metrics.py` foram criados e a Seção 4.1 da SPEC-001.md foi atualizada para refletir esses pesos.
>
> **Atualização (2026-08-15, Rodadas 2/3):** durante a homologação da ISSUE-007, descobriu-se que `docs/issues/manifest.json` já marcava a ISSUE-005 como `"done"` sem os arquivos-alvo existirem — corrigido com a implementação real da ISSUE-005 na mesma sessão. Resolvida essa dependência, o Dani autorizou explicitamente destravar as Rodadas 2 e 3 (Seção 4 abaixo), usando a proposta do `BENCHMARK-METRICS-001.md §6-9` como fórmula final — ver **ADR-002**. `calculate_comment_typology`, `calculate_visual_retention`, `calculate_noise_reduction`, `calculate_bqi`, `calculate_sponsor_density`, `calculate_consistency` e `calculate_editorial_opinion` foram implementados em `metrics.py` via TDD (50/50 testes). Nenhum peso, corte, bloqueador, faixa ou fórmula foi inventado por inferência do assistente — tudo transcrito do documento já submetido à aprovação do Dani. A Seção 4 completa da SPEC-001.md foi atualizada.
>
> **Ressalva física que permanece em aberto:** o Pilar 2 do BQI (retenção visual/alcance qualificado) exige `save_rate`/`share_rate`/`VTR`/`alcance_qualificado`, sinais que a coleta pública via Instaloader (ISSUE-002) não expõe. `bqi` e, por consequência, boa parte do `editorial_opinion` retornam `indisponivel` em auditorias reais até uma expansão futura do coletor — explicitamente fora do escopo desta issue (§13). O piso (`floor`) do CI também segue como decisão editorial em aberto, não fabricada. Tipologia/`V_AB`/Pilar 1 e a Saturação de Publis (SD) já são reais hoje, via `src/app.py` (ISSUE-007).

O `docs/issues/manifest.json` foi atualizado após a entrega real e a validação dos testes (critério de aceite §12.9), refletindo o status desta issue — a ressalva física sobre o Pilar 2/BQI/CI em auditorias reais permanece documentada e não foi escondida.

## 3. Decisões já aprovadas

A Rodada 1 da consultoria foi aprovada pelo Dani e fornece o núcleo de ponderação do ER Branding.

### 3.1 Pesos das ações

| Ação | Peso aprovado | Observação editorial |
|---|---:|---|
| Comentários | 3 | Sinal relevante de interação e conversa. A eventual distinção entre tipos de comentário permanece na Rodada 2. |
| Compartilhamentos | 3 | Sinal de circulação e recomendação do conteúdo. |
| Salvamentos | 2 | Importante para moda, embora menos frequente; sinal de intenção futura e referência. |
| Curtidas | 3 | Reconhecida como métrica de vaidade, mas ainda considerada relevante para o contexto de marca. |

O peso de comentários nesta etapa se aplica à interação quantitativa. A classificação qualitativa A/B/C/D e o indicador `V_AB` continuam separados e pendentes da Rodada 2.

### 3.2 Denominador misto

O motor deverá privilegiar **alcance único** quando o dado estiver disponível e permitir o uso de **seguidores** como denominador alternativo para comparação histórica. O resultado deve declarar qual denominador foi utilizado, qual foi a cobertura e se houve mistura por post.

A implementação futura não poderá substituir silenciosamente alcance ausente por seguidores. A escolha deve aparecer em `denominator_mode`, em `provenance` e em `warnings` quando houver fallback.

### 3.3 Peso por formato

Os pesos aprovados para o ER Branding são:

| Formato canônico | Peso |
|---|---:|
| Carrossel | 1,20 |
| Foto | 1,00 |
| Reel | 0,80 |

O Reel recebe peso menor porque, no contexto discutido, tende a possuir maior entrega e retenção. O carrossel recebe o maior peso como formato de maior profundidade e potencial de permanência. O peso não representa uma verdade universal de performance; representa a preferência editorial aprovada para o motor autoral.

O peso será aplicado como fator de formato na agregação da janela, não como alteração retroativa dos dados brutos. A semântica exata para posts sem formato reconhecido deve ser decidida na implementação, com erro explícito ou classificação `unknown`; nunca com atribuição silenciosa de um peso arbitrário.

### 3.4 Stories

Stories constituem um **sinal contextual separado** e ficam fora do ER Branding principal. O motor poderá receber dados de Stories e devolvê-los em um bloco próprio, mas não poderá somá-los ao denominador ou numerador do ER principal sem uma nova decisão do Dani.

## 4. Decisões pendentes — resolvidas em 2026-08-15 (ADR-002)

> As tabelas abaixo registram as perguntas como estavam no rascunho original (histórico preservado). Todas foram respondidas pelo Dani em 2026-08-15 adotando a proposta do `BENCHMARK-METRICS-001.md §6-9` como fórmula final — ver **ADR-002** e `specs/SPEC-001.md §4.2/§4.4` para o texto congelado. A única pergunta que segue sem valor numérico definido é o piso (`floor`) do CI, que `calculate_consistency` exige como parâmetro explícito em vez de assumir um padrão.

### 4.1 Rodada 2 — Tipologia A/B/C/D e BQI

| Decisão | Pergunta a aprovar | Estado |
|---|---|---|
| Tipologia de comentários | Qual é a contribuição de A, B, C e D para o valor de marca? Comentários classificados devem substituir, complementar ou apenas contextualizar o volume bruto? | Pendente |
| Pilar P1 do BQI | Qual composição representa conversação e afinidade? | Pendente |
| Pilar P2 do BQI | Qual composição representa retenção visual, alcance qualificado e relevância de formato? | Pendente |
| Pilar P3 do BQI | P3 será pilar positivo ou redutor de ruído/integridade? Qual impacto máximo? | Pendente |
| Faixas do BQI | Quais intervalos correspondem a recomendada, recomendada com ressalvas, alerta e não recomendada? | Pendente |
| Bloqueadores | Quais condições suspendem o parecer independentemente do BQI? | Pendente |

O benchmark atual apresenta uma proposta preliminar de BQI com `P1=45%`, `P2=40%` e um redutor de até 15%, mas esses valores não devem ser tratados como aprovados nesta issue [2].

### 4.2 Rodada 3 — Consistência, saturação e parecer editorial

| Decisão | Pergunta a aprovar | Estado |
|---|---|---|
| Consistência | Qual janela, unidade de análise e medida de dispersão devem compor o índice `CI`? | Pendente |
| Saturação de publis | Qual é o denominador de unidades comparáveis e qual faixa de `SD` é tolerável para branding? | Pendente |
| Parecer editorial | Quais combinações de ER, BQI, CI, SD, audiência e risco geram recomendação, ressalva ou bloqueio? | Pendente |
| Dependência de viral | Como identificar e penalizar performance concentrada em poucos posts? | Pendente |
| Disclosure e risco | Quais sinais são bloqueadores absolutos e quais apenas geram ressalva? | Pendente |

As tabelas e cortes atualmente presentes no `BENCHMARK-METRICS-001.md` são propostas de trabalho e serão promovidas para a especificação somente após o aceite do Dani [2].

### 4.3 Matriz de proveniência e plataforma

A auditoria do Modash ainda precisa concluir a matriz comparativa dos perfis da coorte. Essa matriz poderá orientar nomenclatura, escopos e campos de proveniência, mas não determinará os pesos autorais. O FINDER-PLATAFORMA-COMPLETA.md registra as diferenças entre métrica observada, métrica estimada, métrica derivada e hipótese [3].

## 5. Escopo funcional

### 5.1 Incluído nesta issue

O motor futuro deverá:

1. receber um payload normalizado de perfil, janela e posts;
2. calcular a interação ponderada por ação;
3. aplicar os pesos de formato aprovados;
4. selecionar explicitamente o denominador disponível;
5. calcular ER Branding agregado e, quando solicitado, por formato;
6. manter Stories em sinal contextual separado;
7. calcular tipologia, BQI, consistência, saturação e parecer somente quando suas regras forem aprovadas;
8. devolver valores, versões, denominadores, coberturas, amostras, escopos e advertências;
9. retornar `insufficient_data` ou `indisponivel` quando não houver base suficiente;
10. preservar rastreabilidade para cada resultado.

### 5.2 Sequência futura de implementação

A implementação deverá ocorrer em duas camadas. A primeira camada será o núcleo quantitativo aprovado na Rodada 1: ER Branding, denominador misto, pesos de formato e isolamento de Stories. A segunda camada será ativada somente depois das Rodadas 2 e 3: tipologia A/B/C/D, BQI, CI, SD e parecer editorial.

Essa separação permite testar a parte já decidida sem fingir que as métricas qualitativas e os cortes editoriais já estão congelados.

## 6. Contrato de entrada

O contrato abaixo é provisório e será congelado na SPEC-001.md após as aprovações. Ele não constitui autorização para escrever o código.

```json
{
  "profile": {
    "username": "@exemplo",
    "followers_count": 0,
    "tier": "nano|micro|midi|macro|mega"
  },
  "window": {
    "days": 90,
    "from": "ISO-8601",
    "to": "ISO-8601"
  },
  "posts": [
    {
      "post_id": "...",
      "format": "reel|carrossel|foto",
      "published_at": "ISO-8601",
      "reach_unique": null,
      "likes": 0,
      "comments": 0,
      "shares": 0,
      "saves": 0,
      "sponsored": false
    }
  ],
  "stories": [],
  "comments": [],
  "coverage": {
    "reach_unique": 0.0,
    "comments": 0.0,
    "posts": 0.0
  },
  "options": {
    "denominator_preference": "reach_unique_then_followers",
    "include_stories_in_er": false
  }
}
```

### 6.1 Regras de validação da entrada

O motor deverá rejeitar ou sinalizar posts sem `post_id`, datas inválidas, contadores negativos, formatos desconhecidos, duplicidade de posts, seguidores ausentes quando o fallback histórico for necessário e alcance único inconsistente. Dados ausentes devem permanecer ausentes; não podem ser convertidos em zero sem uma justificativa de coleta.

A janela declarada precisa ser verificável a partir das datas. Se o payload declarar 90 dias mas contiver posts fora da janela, o motor deverá retornar advertência e indicar se filtrou, rejeitou ou preservou o item fora do escopo.

## 7. Contrato de saída

```json
{
  "status": "draft|ok|insufficient_data|indisponivel",
  "method_version": "BMQ-001-v2.0.0-draft",
  "metrics": {
    "er_branding": {
      "value": null,
      "unit": "pct",
      "status": "pending_approval",
      "denominator": "reach_unique|followers|mixed|unavailable",
      "content_scope": "all_content_without_stories",
      "format_weights": {
        "carrossel": 1.2,
        "foto": 1.0,
        "reel": 0.8
      }
    },
    "er_by_format": {},
    "stories_context": {
      "status": "separate_contextual_signal"
    },
    "comment_typology": {
      "status": "pending_round_2"
    },
    "bqi": {
      "status": "pending_round_2"
    },
    "ci": {
      "status": "pending_round_3"
    },
    "sponsor_density": {
      "status": "pending_round_3"
    },
    "editorial_opinion": {
      "status": "pending_round_3"
    }
  },
  "provenance": {
    "window_days": 90,
    "posts_n": 0,
    "sample_n": 0,
    "source": "local_scraper|manual|cache|platform_report",
    "denominator_mode": "reach_unique_then_followers",
    "formula_version": "BMQ-001-v2.0.0-draft",
    "coverage": {},
    "warnings": []
  }
}
```

A saída deverá distinguir `pending_approval` de `unavailable`. O primeiro significa que a regra ainda não foi congelada; o segundo significa que a fonte não possui o dado necessário. Essa distinção é necessária para que o sistema não apresente um resultado parcial como se fosse uma decisão de negócio.

## 8. Arquitetura da implementação

### 8.1 Módulo de domínio

`src/features/analise/metrics.py` deverá conter somente funções e estruturas de domínio. Não poderá importar Streamlit, acessar widgets, ler diretamente a sessão do Instagram, fazer chamadas de rede ou escrever arquivos. A View deverá receber o resultado resolvido e apenas renderizá-lo, conforme a arquitetura de View Pura definida na ADR-001 [4].

A divisão interna sugerida é:

| Componente | Responsabilidade futura |
|---|---|
| `validate_input` | Validar schema, tipos, janela, duplicidades e contadores. |
| `resolve_denominator` | Selecionar alcance único, seguidores ou estado indisponível. |
| `weighted_interactions` | Calcular comentários, compartilhamentos, salvamentos e curtidas com pesos aprovados. |
| `format_factor` | Resolver carrossel, foto e Reel; sinalizar formato desconhecido. |
| `calculate_er_branding` | Agregar o ER principal sem Stories. |
| `calculate_er_by_format` | Produzir cortes comparáveis por formato. |
| `calculate_stories_context` | Produzir sinal separado e explicitamente contextual. |
| `classify_comments` | A implementar somente após aprovação da Rodada 2. |
| `calculate_bqi` | A implementar somente após aprovação da Rodada 2. |
| `calculate_consistency` | A implementar somente após aprovação da Rodada 3. |
| `calculate_sponsor_density` | A implementar somente após aprovação da Rodada 3. |
| `build_editorial_opinion` | A implementar somente após aprovação da Rodada 3. |

### 8.2 Separação de dependências

O motor poderá receber dicionários ou dataclasses normalizados, mas não deverá conhecer a origem concreta. Coleta Instaloader, cache SQLite, classificação heurística local/Gemini, exportação PDF/CSV e Streamlit pertencem a camadas externas. A proveniência deve ser transportada no payload e devolvida na saída.

### 8.3 Versionamento

Qualquer mudança em peso, denominador, fórmula, tipologia, corte, bloqueador ou faixa editorial exige atualização conjunta da versão da metodologia, SPEC-001.md, ADR-002, issue, testes e changelog/progresso. Alterações silenciosas no módulo são proibidas.

## 9. Requisitos funcionais

| ID | Requisito | Estado |
|---|---|---|
| RF-001 | Calcular interações ponderadas com comentários 3, compartilhamentos 3, salvamentos 2 e curtidas 3. | Aprovado na Rodada 1; implementação bloqueada até congelamento documental. |
| RF-002 | Aplicar carrossel 1,20, foto 1,00 e Reel 0,80. | Aprovado na Rodada 1; implementação bloqueada até congelamento documental. |
| RF-003 | Priorizar alcance único quando disponível e permitir seguidores como alternativa histórica. | Aprovado na Rodada 1; semântica de mistura deve ser documentada. |
| RF-004 | Manter Stories fora do ER Branding principal. | Aprovado na Rodada 1. |
| RF-005 | Exibir denominador, escopo, janela, amostra e cobertura. | Obrigatório. |
| RF-006 | Não transformar dado ausente em zero silencioso. | Obrigatório. |
| RF-007 | Calcular tipologia A/B/C/D e BQI. | Bloqueado pela Rodada 2. |
| RF-008 | Calcular CI e SD. | Bloqueado pela Rodada 3. |
| RF-009 | Emitir parecer editorial e bloqueadores. | Bloqueado pela Rodada 3. |
| RF-010 | Manter a View sem lógica de negócio. | Obrigatório conforme ADR-001. |

## 10. Requisitos de qualidade

O motor deve ser determinístico para o mesmo payload e a mesma versão metodológica. Deve produzir resultados explicáveis, com arredondamento definido, sem efeitos colaterais e com cobertura de testes para casos normais, ausentes, inválidos e limítrofes.

A precisão numérica deverá ser preservada internamente em ponto flutuante suficiente para evitar erro acumulado; o arredondamento de apresentação deve ocorrer somente na camada de saída/renderização, salvo decisão explícita em contrário. Os valores brutos e os valores exibidos devem ser distinguíveis.

A implementação não deve depender de acesso à internet, login, Streamlit, arquivo `.env` ou estado global. Isso permite rodar os testes em ambiente isolado e auditar cada cálculo com fixtures controladas.

## 11. Plano de testes

Os testes abaixo formam o plano preliminar. Eles serão implementados somente após o congelamento da especificação.

### 11.1 Núcleo aprovado da Rodada 1

| Teste | Comportamento esperado |
|---|---|
| Pesos de ações | Comentários, compartilhamentos e curtidas contribuem com 3; salvamentos com 2. |
| Peso de carrossel | O mesmo post recebe fator 1,20 quando o formato é carrossel. |
| Peso de foto | O mesmo post recebe fator 1,00 quando o formato é foto. |
| Peso de Reel | O mesmo post recebe fator 0,80 quando o formato é Reel. |
| Alcance disponível | O denominador declarado é `reach_unique`. |
| Fallback histórico | Sem alcance, o denominador pode usar seguidores e emite proveniência/warning. |
| Mistura explícita | Posts com alcance e posts sem alcance não desaparecem nem recebem substituição silenciosa. |
| Stories isolados | Posts de Stories não alteram o ER Branding principal. |
| Formato desconhecido | O motor retorna erro ou estado indisponível conforme a decisão final, nunca peso implícito. |
| Denominador zero | O motor retorna `insufficient_data` ou `indisponivel`, nunca infinito ou zero enganoso. |

### 11.2 Rodada 2

Depois da aprovação, adicionar testes de classificação A/B/C/D, cobertura de comentários, cálculo de `V_AB`, normalização dos pilares P1/P2/P3, redutor, faixas do BQI e bloqueadores independentes da pontuação.

### 11.3 Rodada 3

Depois da aprovação, adicionar testes de mediana e dispersão para CI, unidades patrocinadas e comparáveis para SD, concentração/viralidade e todas as combinações do parecer editorial.

### 11.4 Invariantes

Os testes deverão garantir que adicionar um Story não altera o ER Branding; que reduzir a cobertura não aumenta silenciosamente a confiança; que um denominador ausente nunca retorna uma taxa numérica sem warning; que a mesma entrada e a mesma versão retornam a mesma saída; e que qualquer valor calculado possui proveniência suficiente para auditoria.

## 12. Critérios de aceite

A ISSUE-004 somente poderá ser marcada como concluída quando todas as condições forem satisfeitas:

1. Rodadas 2 e 3 respondidas e aprovadas pelo Dani.
2. Seção 4 da SPEC-001.md atualizada com fórmulas, pesos, cortes e bloqueadores finais.
3. ADR-002 criada e aprovada, registrando decisões, descartes e justificativas editoriais.
4. Este documento atualizado de `draft_blocked_for_approval` para o status correspondente à implementação.
5. `src/features/analise/metrics.py` implementado sem acoplamento ao Streamlit ou à rede.
6. `tests/test_metrics.py` cobrindo o núcleo aprovado, casos faltantes, fronteiras e regras das Rodadas 2 e 3.
7. Saída com fórmula, denominador, escopo, janela, amostra, cobertura, versão e warnings.
8. Nenhuma métrica de mercado antiga incorporada sem decisão explícita.
9. `docs/issues/manifest.json` atualizado somente após a entrega real e a validação dos testes.
10. Documentos autorizados sincronizados no Google Drive conforme a whitelist do CLAUDE.md.

## 13. Fora de escopo

Esta issue não inclui redesign de tela, implementação do scraper Instaloader, autenticação Instagram/Modash, classificação automática de todos os comentários, reprodução de algoritmo proprietário da plataforma, geração de PDF, criação de dashboards, decisão automática de contratação, alteração de fórmula sem aprovação, migração de código legado ou incorporação automática de benchmarks históricos.

Também não inclui a abertura aleatória de novos perfis no Modash. A auditoria da plataforma segue o backlog e a cota registrada no `FINDER-PLATAFORMA-COMPLETA.md` [3].

## 14. Próximo portão

O próximo passo é conduzir a **Rodada 2 da consultoria** com base na matriz comparativa da coorte Modash. As perguntas deverão decidir a tipologia A/B/C/D, os pilares P1/P2/P3, os pesos, os redutores, as faixas de BQI e os bloqueadores.

Depois da aprovação da Rodada 2, será conduzida a Rodada 3 sobre consistência, saturação de publis e parecer editorial. Somente após as duas rodadas a issue poderá sair do estado `draft_blocked_for_approval` e receber código.

## 15. Rastreabilidade

| Artefato | Relação com esta issue |
|---|---|
| [`BENCHMARK-METRICS-001.md`](../../BENCHMARK-METRICS-001.md) | Modelo autoral modular, contratos, propostas de BQI, CI, SD e parecer; valores pendentes até aprovação. |
| [`SPEC-001.md`](../../specs/SPEC-001.md) | Especificação soberana; Seção 4 será atualizada somente após as três rodadas. |
| [`ADR-001-arquitetura-hibrida-e-view-pura.md`](../../decisions/ADR-001-arquitetura-hibrida-e-view-pura.md) | Exige separação entre domínio e View. |
| [`FINDER-001.md`](../../FINDER-001.md) | Certezas técnicas, contratos de I/O, cache e stack validada. |
| [`FINDER-PLATAFORMA-COMPLETA.md`](../../FINDER-PLATAFORMA-COMPLETA.md) | Auditoria metodológica da plataforma e separação entre observação e regra autoral. |
| [`issue-002-coleta-e-cloud-prep.md`](issue-002-coleta-e-cloud-prep.md) | Contratos e preparação de coleta. |
| [`issue-003-refinamento-visual-e-demografia.md`](issue-003-refinamento-visual-e-demografia.md) | Heurísticas e integração da camada de demografia. |
| `docs/issues/manifest.json` | ISSUE-004 permanece `pending` enquanto este rascunho estiver bloqueado. |

### Referências internas

[1]: ../../README.md "Roteador de contexto do métricaDODÔ"  
[2]: ../../BENCHMARK-METRICS-001.md "Modelo Matemático Autoral Modular"  
[3]: ../../FINDER-PLATAFORMA-COMPLETA.md "Finder da plataforma e protocolo de auditoria"  
[4]: ../../decisions/ADR-001-arquitetura-hibrida-e-view-pura.md "ADR-001 — Arquitetura híbrida e View Pura"
