# ISSUE-005 — Inteligência Analítica Econômica: Heurística Local + Gemini

**Projeto:** métricaDODÔ v2.0.0  
**Tipo:** Integração de IA / análise de comentários e parecer editorial  
**Status:** `done` — `ai_local.py`/`ai_gemini.py` implementados via TDD (33/33 testes em `tests/test_ai_integration.py`), sem acoplamento a Streamlit/rede no import; ver `docs/issues/manifest.json`.  
**Prioridade:** Alta  
**Dependência:** ISSUE-004 — Motor de Métricas Autorais  
**Implementação prevista:** `src/features/analise/ai_gemini.py` e `src/features/analise/ai_local.py`  
**Testes previstos:** `tests/test_ai_integration.py`  
**Decisão de custo:** usar o processamento local sempre que a regra for determinística; usar Gemini 2.5 Flash como único provedor de IA; não integrar Claude nesta versão.

## Sumário

1. [Objetivo](#1-objetivo)  
2. [Decisão arquitetural](#2-decisão-arquitetural)  
3. [Divisão de responsabilidades](#3-divisão-de-responsabilidades)  
4. [Pré-triagem heurística local](#4-pré-triagem-heurística-local)  
5. [Gemini 2.5 Flash — triagem A/B/C/D](#5-gemini-25-flash--triagem-abcd)  
6. [Gemini 2.5 Flash — parecer editorial](#6-gemini-25-flash--parecer-editorial)  
7. [Fallback e modo convidado](#7-fallback-e-modo-convidado)  
8. [Contratos JSON](#8-contratos-json)  
9. [Prompts de sistema](#9-prompts-de-sistema)  
10. [Implementação prevista](#10-implementação-prevista)  
11. [Testes](#11-testes)  
12. [Segurança, custo e proveniência](#12-segurança-custo-e-proveniência)  
13. [Critérios de aceite](#13-critérios-de-aceite)  
14. [Fora de escopo](#14-fora-de-escopo)  
15. [Rastreabilidade](#15-rastreabilidade)

## 1. Objetivo

Implementar uma camada de análise de comentários e geração de parecer editorial que privilegie **baixo custo, determinismo e auditabilidade**. A camada deverá resolver localmente o que puder ser resolvido por regras seguras, encaminhar para o Gemini apenas o que exige interpretação e produzir uma saída estruturada que alimente o `metrics.py` sem recalcular métricas matemáticas.

O termo “híbrida” nesta issue significa **heurística local + Gemini**, e não uma arquitetura com múltiplos provedores de IA. O Claude 3.5 Sonnet foi retirado do escopo por decisão do Dani. Não deverá existir `ai_claude.py`, dependência `anthropic`, chave Anthropic ou fallback para Claude na v2.0.0.

## 2. Decisão arquitetural

A ordem de processamento será:

```text
comentário bruto
    ↓
heurística local segura
    ├── classificado com alta certeza → resultado local, custo zero de IA
    └── ambíguo ou não coberto → lote Gemini 2.5 Flash
                                      ↓
                           JSON estrito validado
                                      ↓
                             metrics.py / parecer
                                      ↓
                    falha do Gemini → fallback local explícito
```

A escolha é orientada por custo, não por substituição cega de qualidade. O código local continua responsável por métricas, pesos, denominadores, BQI, CI, SD e bloqueadores. O Gemini é usado para interpretação linguística delimitada, classificação A/B/C/D e redação baseada em dados já resolvidos.

| Camada | Responsabilidade | Custo esperado | Pode inventar métrica? |
|---|---|---:|---|
| Heurística local | Casos óbvios, validação, fallback e parecer templateado | Zero chamada de IA | Não |
| `metrics.py` | ER, BQI, CI, SD e normalizações aprovadas | Computacional local | Não |
| Gemini 2.5 Flash | Comentários ambíguos e parecer editorial estruturado | Chamada de IA por lote | Não; só pode usar o contexto recebido |
| Claude/Anthropic | Fora do escopo | Zero | Não se aplica |

A integração deverá usar o SDK `google.genai` validado no projeto. A chave será obtida pelo mecanismo de segredos existente; nunca será escrita em código, issue, fixture ou log versionável.

## 3. Divisão de responsabilidades

| Pergunta | Responsável |
|---|---|
| Este comentário é um caso óbvio de ruído/emoji/spam? | Heurística local, somente quando a regra tiver alta precisão. |
| Este comentário representa A, B, C ou D? | Heurística local quando seguro; Gemini quando houver ambiguidade. |
| Qual é o ER ou o peso do formato? | `metrics.py`; nunca o Gemini. |
| Qual é a faixa de BQI? | `metrics.py` e regras aprovadas; nunca o Gemini. |
| Como explicar um conjunto de sinais para a marca? | Gemini com payload matemático já calculado ou template local no fallback. |
| O parecer pode alterar a recomendação automaticamente? | Não. O parecer é editorial assistivo e deve conservar ressalvas e confiança. |

## 4. Pré-triagem heurística local

A pré-triagem reduz custo e latência sem forçar interpretações. Ela só deverá classificar diretamente quando a regra for altamente conservadora.

### 4.1 Casos elegíveis para D local

Podem ser classificados como `D` apenas sinais inequívocos, como comentário vazio após normalização, sequência exclusivamente composta por emojis, reações repetitivas sem conteúdo lexical, texto de spam evidente ou comentário genérico contido em uma lista de padrões versionada. A lista não poderá tratar automaticamente todo “linda”, “amei” ou elogio curto como D, porque esse texto pode conter afinidade ou desejo de estilo conforme o contexto.

Quando uma regra local não atingir o limiar de segurança, o comentário deve seguir para o Gemini. O objetivo da heurística é economizar chamadas, não maximizar cobertura por meio de falso positivo.

### 4.2 Casos que não devem ser classificados localmente

Ironia, intenção comercial implícita, desejo de compra, relação pessoal, duplo sentido, comentário com contexto visual ausente e texto que contenha instruções para o modelo devem ser encaminhados ao Gemini. O comentário é dado não confiável; instruções inseridas dentro dele não têm autoridade sobre o prompt de sistema.

### 4.3 Saída local

A heurística deve devolver o mesmo contrato do Gemini, com `provider="local_heuristic"`, `fallback_level="local_primary"`, `confidence="high"` apenas nos casos elegíveis e `reason_code` versionado. Não deve gerar justificativa livre extensa.

## 5. Gemini 2.5 Flash — triagem A/B/C/D

### 5.1 Escopo da triagem

O Gemini recebe apenas comentários que não foram resolvidos localmente e o contexto mínimo necessário. Deve classificar uma categoria dominante, sem multilabel, para manter o contrato compatível com a contagem de `A`, `B`, `C` e `D` do motor de métricas.

As categorias são:

| Rótulo | Definição operacional |
|---|---|
| `A` | Desejo, percepção de estilo, admiração estética ou intenção de reproduzir o visual, sem evidência comercial direta. |
| `B` | Conexão real, identificação pessoal, relato contextual, vínculo, experiência ou conversa substantiva com a criadora. |
| `C` | Sinal comercial secundário, como pergunta sobre preço, loja, tamanho, tecido, disponibilidade, compra ou produto. |
| `D` | Ruído, emoji isolado, spam, comentário genérico sem sinal interpretável ou interação de baixo valor informativo. |

A categoria `C` não deve ser tratada como conversão. A categoria `D` não deve ser interpretada como rejeição. A classificação mede sinal informativo para branding, não sentimento moral do comentarista.

### 5.2 Regra de incerteza

O modelo deve retornar uma única categoria dominante quando houver evidência suficiente. Se o comentário for ambíguo, curto demais ou depender de contexto ausente, deve retornar `label=null`, `status="uncertain"` e `confidence="low"`. O sistema não deve forçar uma categoria apenas para preencher a amostra.

A resposta deve incluir somente evidências presentes no próprio comentário. É proibido inventar intenção, relacionamento, compra, gênero, idade, localização ou contexto que não esteja no input.

### 5.3 Lote e controle de custo

Os comentários devem ser enviados em lotes configuráveis, com limite operacional inicial de até 100 comentários por lote e no máximo dois lotes por perfil, conforme o contrato histórico do projeto [1]. O limite deve ser uma configuração versionada, não um número escondido no código.

Antes de chamar o Gemini, o sistema deve remover duplicatas por hash, reutilizar resultados válidos de cache e excluir casos já resolvidos pela heurística. A chamada deve usar JSON estrito e validação local posterior.

## 6. Gemini 2.5 Flash — parecer editorial

O parecer recebe um resumo estruturado, não a base inteira de comentários. O payload deve conter métricas já calculadas, proveniência, sinais A/B/C/D agregados, cobertura, limitações e formato disponível. O Gemini não pode recalcular ER, BQI, CI, SD, porte ou denominadores.

### 6.1 Estrutura obrigatória

O parecer deverá conter exatamente:

1. `veredito`: uma frase com uma das opções `recomendada`, `recomendada_com_ressalvas` ou `nao_recomendada`;
2. `pontos_fortes`: exatamente três pontos de branding, cada um ancorado em dado recebido;
3. `alertas`: exatamente dois alertas ou ressalvas de briefing;
4. `formato_ideal`: um formato ou combinação entre `carrossel`, `foto`, `reel`, `stories` e `combinacao`;
5. `confianca`: `alta`, `media` ou `baixa`;
6. `lacunas_de_dados`: lista de dados ausentes, amostra insuficiente ou limitações relevantes;
7. `provider_used` e `fallback_level`.

O tom será **editorial, direto e profissional**. O texto não deve prometer conversão, declarar fraude como fato, ocultar incerteza, inventar informações sobre a criadora ou contradizer o resultado matemático sem explicar a limitação.

### 6.2 Limite de autoridade

O Gemini redige e organiza o parecer; não decide sozinho a contratação. O status final deve continuar sujeito à revisão humana, aos bloqueadores e às regras documentadas na SPEC-001.md. Um parecer gerado não substitui a auditoria da fonte nem transforma dados estimados em dados observados.

## 7. Fallback e modo convidado

### 7.1 Ordem oficial

| Nível | Condição | Comportamento |
|---|---|---|
| `local_primary` | Regra local segura ou métrica determinística | Usa heurística/`metrics.py`; nenhuma chamada de IA. |
| `gemini_primary` | Caso ambíguo ou parecer padrão com chave disponível | Usa Gemini 2.5 Flash e valida JSON. |
| `local_fallback` | Gemini indisponível, rate limit, timeout, erro de schema ou sem chave | Retorna classificação heurística possível e parecer templateado com dados matemáticos. |
| `indisponivel` | Nem a regra local nem os dados mínimos permitem conclusão | Retorna estado explícito, sem texto inventado. |

Não haverá fallback para Claude, outro provedor ou chamada silenciosa a um modelo diferente. Se o Gemini falhar parcialmente em um lote, os itens válidos podem ser preservados e os demais devem ser marcados como `uncertain` ou encaminhados ao fallback local.

### 7.2 Parecer local de fallback

O parecer local deverá usar apenas regras determinísticas e o resumo do `metrics.py`. Ele poderá preencher o veredito quando houver faixas aprovadas e dados suficientes; caso contrário, deverá retornar `indisponivel` ou `recomendada_com_ressalvas` com lacuna explícita. Os pontos fortes e alertas devem ser templates associados a sinais existentes, nunca frases criadas a partir de fatos ausentes.

### 7.3 Rastreamento do fallback

Toda saída deverá informar `provider_used`, `fallback_level`, `model_version`, `prompt_version`, `status`, `confidence`, `warnings` e `data_gaps`. A interface deverá exibir quando o parecer foi local, Gemini ou indisponível.

## 8. Contratos JSON

### 8.1 Classificação de comentário

```json
{
  "comment_id": "comentario-001",
  "label": "A|B|C|D|null",
  "status": "classified|uncertain|invalid",
  "confidence": "high|medium|low",
  "evidence": "trecho literal presente no comentário",
  "reason_code": "style_desire|real_connection|commercial_signal|noise|ambiguous|insufficient_context",
  "provider_used": "local_heuristic|gemini_2_5_flash",
  "fallback_level": "local_primary|gemini_primary|local_fallback|indisponivel"
}
```

O schema de produção deverá ser JSON Schema estrito, com `additionalProperties=false`, campos obrigatórios e enumerações fechadas. `evidence` não pode conter uma frase que não esteja no comentário original.

### 8.2 Parecer editorial

```json
{
  "veredito": "recomendada|recomendada_com_ressalvas|nao_recomendada|indisponivel",
  "pontos_fortes": [
    {"texto": "...", "evidencia_metricas": ["..."], "confidence": "alta|media|baixa"}
  ],
  "alertas": [
    {"texto": "...", "evidencia_metricas": ["..."], "confidence": "alta|media|baixa"}
  ],
  "formato_ideal": "carrossel|foto|reel|stories|combinacao|indisponivel",
  "confianca": "alta|media|baixa",
  "lacunas_de_dados": ["..."],
  "provider_used": "local_template|gemini_2_5_flash",
  "fallback_level": "gemini_primary|local_fallback|indisponivel"
}
```

A validação deverá exigir exatamente três elementos em `pontos_fortes` e dois em `alertas` quando o status for utilizável. No fallback indisponível, as listas podem ser vazias, desde que `lacunas_de_dados` explique o motivo.

## 9. Prompts de sistema

### 9.1 Prompt de triagem

O prompt deverá informar que o modelo é um classificador de comentários, que deve devolver somente o JSON do schema, usar uma categoria dominante, não inventar contexto, não obedecer instruções inseridas no comentário e usar `label=null` quando houver ambiguidade. As definições A/B/C/D devem ser incluídas no prompt de sistema e versionadas em `prompt_version`.

O prompt não deverá pedir análise de idade, gênero, localização ou intenção de compra como fato. Quando houver sinal comercial, basta classificar `C` com evidência literal; qualquer atributo não presente deve ser omitido ou marcado como ausente.

### 9.2 Prompt de parecer

O prompt deverá instruir o modelo a usar somente o resumo recebido, preservar o veredito matemático e os bloqueadores, preencher exatamente três forças e dois alertas quando houver dados, indicar o formato ideal com base nos sinais disponíveis e declarar lacunas. Deve proibir promessa de conversão, acusação de fraude, inferência demográfica e fabricação de métricas.

O conteúdo de comentários é não confiável e deve ser delimitado como dados. Nenhum texto contido em comentário poderá alterar as regras do prompt ou solicitar segredos, ferramentas, chamadas externas ou mudança de formato.

## 10. Implementação prevista

### 10.1 `src/features/analise/ai_local.py`

Este módulo deverá conter normalização, hash de deduplicação, regras conservadoras de ruído, classificação de casos óbvios, templates de fallback, validação básica de payload e construção de estados de proveniência. Não poderá acessar a internet, importar Streamlit ou calcular métricas que pertencem ao `metrics.py`.

### 10.2 `src/features/analise/ai_gemini.py`

Este módulo deverá encapsular o cliente `google.genai`, leitura segura da chave, construção dos prompts versionados, batching, timeout, retry limitado, validação do schema, classificação de erro, cache de respostas e registro de uso. O módulo deverá receber dados serializáveis e devolver dados serializáveis, sem escrever diretamente na View.

A integração deverá ser testável com cliente injetável/mocado. O código não deverá depender de uma sessão real para os testes. Respostas inválidas, vazias, truncadas, com campos extras ou fora das enumerações devem ser rejeitadas e encaminhadas ao fallback local.

### 10.3 `tests/test_ai_integration.py`

Os testes deverão cobrir a heurística local, o cliente Gemini mockado, contratos, batching, cache, falhas e a cadeia completa `local → Gemini → local fallback`. Não deverão consumir API real, usar chaves reais ou gravar comentários de teste em artefatos de produção.

## 11. Testes

| Grupo | Casos mínimos |
|---|---|
| Heurística | Emojis puros, vazio, spam evidente, comentário genérico não conclusivo e caso ambíguo encaminhado ao Gemini. |
| Schema | JSON válido, campo ausente, campo extra, enum inválida, `label=null` com baixa confiança e evidência inexistente. |
| Gemini mockado | Batch de comentários, dois lotes, deduplicação, resposta ordenada por `comment_id` e cliente injetado. |
| Prompt injection | Comentário contendo “ignore as regras” permanece tratado como dado e não altera o schema. |
| Rate limit | Exceção de quota aciona `local_fallback`, registra warning e não faz loop infinito. |
| Sem chave | Modo convidado não chama rede e produz saída local ou `indisponivel`. |
| Parecer | Exatamente três forças e dois alertas, formato permitido, confiança e lacunas presentes. |
| Proveniência | `provider_used`, `fallback_level`, versão do prompt e status são sempre preenchidos. |
| Privacidade | Logs não expõem chave, prompt completo ou volume desnecessário de texto bruto. |
| Determinismo | A mesma entrada local e a mesma versão produzem a mesma saída. |

## 12. Segurança, custo e proveniência

As chaves devem ser lidas por segredo existente e nunca aparecer em logs, mensagens de erro, fixtures ou documentação operacional. O cliente deve ter timeout, retry limitado com backoff e circuit breaker simples para não insistir durante rate limit.

O cache deve ser indexado por hash do comentário ou do resumo, versão do prompt, versão do modelo e contexto relevante. Uma resposta antiga não pode ser reutilizada quando a definição A/B/C/D ou o contrato mudar sem compatibilidade declarada.

O custo deve ser reduzido por quatro mecanismos: heurística antes da IA, deduplicação, batching e parecer sobre resumo em vez de corpus inteiro. A contabilidade deverá registrar quantidade de itens locais, quantidade enviada ao Gemini, quantidade recuperada do cache, falhas e fallback. O sistema não deve apresentar estimativa de custo como fato se o provedor não devolver uso de tokens.

## 13. Critérios de aceite

A ISSUE-005 somente poderá ser marcada como concluída quando:

1. a decisão Gemini-only estiver registrada na ADR correspondente e na SPEC-001.md;
2. `ai_local.py` e `ai_gemini.py` estiverem implementados sem acoplamento ao Streamlit;
3. não existir dependência ativa de `anthropic`, `ai_claude.py` ou chave Claude;
4. o schema de classificação for estrito, validado e resistente a campos extras;
5. a heurística local resolver casos óbvios sem forçar casos ambíguos;
6. o Gemini receber somente itens não resolvidos ou o resumo autorizado;
7. o fallback local funcionar sem chave e durante rate limit;
8. cada saída registrar provedor, fallback, versão, confiança, cobertura e lacunas;
9. o parecer tiver estrutura fixa e não inventar dados;
10. `tests/test_ai_integration.py` passar completamente com mocks;
11. a SPEC, ADR, Finder, PROGRESS e manifesto refletirem o mesmo desenho;
12. os arquivos forem sincronizados conforme a whitelist de governança do projeto.

## 14. Fora de escopo

Esta issue não inclui integração Anthropic/Claude, múltiplos provedores, treinamento de modelo, fine-tuning, classificação de gênero/idade como fato, coleta adicional no Instagram, alteração das fórmulas do `metrics.py`, decisão automática de contratação, envio de e-mails, publicação de conteúdo ou armazenamento indiscriminado de comentários brutos.

Também não inclui usar Gemini para recalcular ER, BQI, CI, SD ou qualquer denominador. Esses valores pertencem ao motor matemático e devem entrar no prompt como dados já resolvidos.

## 15. Rastreabilidade

| Artefato | Relação |
|---|---|
| [`SPEC-001.md`](../../specs/SPEC-001.md) | Arquitetura, fluxo, schemas e definição oficial de módulos. |
| [`ADR-001-arquitetura-hibrida-e-view-pura.md`](../../decisions/ADR-001-arquitetura-hibrida-e-view-pura.md) | Registra a separação View/domínio; a seleção de provedores é supersedida pela ADR-003. |
| [`ADR-003-gemini-only-e-fallback-local.md`](../../decisions/ADR-003-gemini-only-e-fallback-local.md) | Decisão de custo, papéis, exclusão do Claude e fallback. |
| [`BENCHMARK-METRICS-001.md`](../../BENCHMARK-METRICS-001.md) | Contratos de métricas que o Gemini não pode recalcular. |
| [`FINDER-001.md`](../../FINDER-001.md) | Stack, SDK `google.genai`, proveniência e regras técnicas. |
| [`FINDER-PLATAFORMA-COMPLETA.md`](../../FINDER-PLATAFORMA-COMPLETA.md) | Distinção entre dados observados, estimados, derivados e hipóteses. |
| [`issue-004-motor-metricas-autorais.md`](issue-004-motor-metricas-autorais.md) | Dependência do motor matemático e dos contratos de saída. |
| `docs/issues/manifest.json` | Mantém ISSUE-005 pendente até implementação e testes físicos. |

### Referências internas

[1]: ../../FINDER-001.md "Manual Canônico de Certezas Técnicas"  
[2]: ../../BENCHMARK-METRICS-001.md "Modelo Matemático de Métricas Autorais"  
[3]: ../../decisions/ADR-001-arquitetura-hibrida-e-view-pura.md "Arquitetura híbrida original e View Pura"  
[4]: ../../decisions/ADR-003-gemini-only-e-fallback-local.md "Decisão Gemini-only e fallback local"
