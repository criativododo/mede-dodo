# ISSUE-0010: Sprint 004 — UI/UX e Engenharia de Produto do Relatório métricaDODÔ

**Status:** CONCLUÍDA — implementação completa (Fases A→D), suíte 337/337 verde, validação
visual manual concluída. Ver PROGRESS.md ("Sprint 004 — SPEC-005/ISSUE-0010", 2026-08-15)
para o detalhamento técnico completo. Nenhum commit foi feito — aprovação do usuário
pendente antes de incorporar ao histórico Git (regra de governança abaixo).  
**Sprint de origem:** 004, usada apenas como contexto histórico; não criar pasta `SPRINT-004/`.  
**Tipo:** unidade atômica de execução para Claude Code e agentes futuros.  
**Escopo:** implementação da `SPEC-005` com acabamento visual ancorado no `FINDER-006`.  
**Regra de entrada:** ler `DUMMY.md`, `README.md` e esta Issue antes de editar código.

> **Nota de nomenclatura:** o material do Notebook LM usa “ISUL” como sinônimo de unidade atômica de execução. A convenção canônica deste repositório é `ISSUE-NNNN`; portanto, este documento é a `ISSUE-0010`, não um arquivo `ISUL-0002.md` nem um novo documento dentro de uma pasta de Sprint.

## 1. Objetivo da tarefa

Implementar no relatório Streamlit a arquitetura de informação, os contratos de métricas e os estados de apresentação definidos na `SPEC-005`. A entrega deve mostrar fatos concretos antes de qualquer síntese, corrigir a interpretação de demografia e performance por formato, reduzir ruído visual e preservar a identidade Criativo Dodô com uma linguagem limpa, silenciosa e editorial.

A Issue cobre a camada de produto necessária para uma decisão confiável: header factual, KPIs, Reels/Carrossel/Estático, qualidade da audiência, demografia com cobertura, evidências, comentários, auditoria recolhida e exportação sem regressão. Nenhum benchmark de mercado pode ser apresentado como dado observado da influenciadora analisada.

## 2. Documentos de referência e ancoragem

| Documento | Papel nesta Issue |
|---|---|
| [`specs/SPEC-005.md`](../../specs/SPEC-005.md) | Contrato soberano da Sprint 004: escopo, não escopo, fórmulas, schema, hierarquia visual e critérios adicionais de aceite. [1] |
| [`docs/finders/FINDER-006.md`](../finders/FINDER-006.md) | Benchmark visual e de produto: Modash, ferramenta brasileira, Perplexity, Apple-like sem copiar Apple, Bento controlado, cards e impressão. [2] |
| [`docs/finders/FINDER-004.md`](../finders/FINDER-004.md) | Componentes e receitas MVP para Streamlit, cards, estados vazios, tabelas e adaptação local. [3] |
| [`docs/finders/FINDER-005.md`](../finders/FINDER-005.md) | Benchmark de dashboards e padrões de densidade, hierarquia e leitura analítica. [4] |
| [`DUMMY.md`](../../DUMMY.md) | Safety Shield obrigatório: custo zero, cache, scraping, Gemini, limites de alteração, ausência de zeros silenciosos e proibição de commit automático. [5] |
| [`README.md`](../../README.md) | Fluxo de leitura, estrutura canônica e convenções de documentação. [6] |
| [`docs/design-reference/modash/`](../design-reference/modash/) | Referências visuais de relatório, parcerias e captura atual; somente benchmark visual, nunca fonte de valores locais. |
| [`docs/design-reference/dodo/`](../design-reference/dodo/) | Referências de marca e portal Criativo Dodô; manter linguagem visual local. |
| `pasted_content_9.txt` — anexo da solicitação | Orientação do Notebook LM sobre Issue atômica, slicing, idempotência, manifest e proteção de contexto. Fonte de processo, não de runtime. [7] |

## 3. Estado técnico de partida

A aplicação já possui funções de renderização separadas em `app.py`, métricas determinísticas em `src/metrics.py`, heurísticas demográficas em `src/demographics.py`, exportação em `src/exporter.py` e testes com `pytest`/`AppTest`. A implementação deve ser incremental e aditiva: primeiro fixtures e contratos, depois métricas, então View e por fim validação visual/exportação.

O diagnóstico de `SPEC-005` identifica quatro riscos principais: o denominador de gênero pode usar comentários brutos em vez da amostra reconhecida; a performance atual não apresenta três categorias comparáveis; o sinal de autenticidade pode parecer acusação; e a taxa de resposta da criadora pode subcontar respostas em threads. O topo atual também contém conclusões legadas antes dos KPIs e precisa ser reorganizado sem apagar os campos de auditoria.

## 4. Escopo físico

### 4.1 Arquivos de implementação

| Arquivo | Ação | Escopo físico obrigatório |
|---|---|---|
| `app.py` | Modificar | Reorganizar `_render_report_page` e os renderizadores de header, decisão, KPIs, formatos, qualidade, posts, parcerias, comentários, brand suitability, proveniência, auditoria e ações de exportação. Remover Score DODÔ/parecer do primeiro viewport e mantê-los apenas como legado explicitamente rotulado em `Detalhes da auditoria`. |
| `src/metrics.py` | Modificar | Corrigir composição demográfica por denominador válido; criar ou ajustar agregação independente por `Reels`, `Carrossel` e `Estático`; preservar a fórmula global de ER; calibrar o sinal de autenticidade com base real, suspeita, cobertura, confiança e estado; contar respostas de threads conforme o contrato. |
| `src/demographics.py` | Modificar somente se necessário | Expor ou normalizar `coverage_gender`, `genero_validado_n`, `genero_unknown_n` e cobertura regional sem trocar as bases locais aprovadas nem inferir dados ausentes. |
| `tests/test_app.py` | Modificar | Cobrir ordem factual do relatório, ausência de Score DODÔ no topo, cards de formato, estados vazios/indisponíveis, duas colunas de evidência, links acessíveis, auditoria recolhida e fluxo de demo/exportação. |
| `tests/test_metrics.py` | Modificar | Cobrir denominadores, ER por formato, classificação de mídia, amostras vazias, autenticidade calibrada e invariantes de fórmula. |
| `tests/test_demographics.py` | Modificar somente se necessário | Cobrir amostra reconhecida versus desconhecida, porcentagens que somam 100% dentro do denominador válido e `coverage_gender`/`coverage_region` separados. |
| `tests/fixtures/` ou fixtures locais nos testes | Criar/Modificar | Registrar dados determinísticos mínimos para vídeo, carrossel, imagem, comentários raiz, respostas em thread, nomes reconhecidos, nomes desconhecidos, ausência de views e campos legados. Não usar dados reais ou valores do benchmark como se fossem observados. |

### 4.2 Arquivos de documentação e estado

| Arquivo | Ação nesta abertura da Issue | Ação no encerramento da implementação |
|---|---|---|
| `docs/issues/ISSUE-0010.md` | Criar este contrato atômico | Atualizar status, checklist, evidências, testes, desvios e decisão final. |
| `docs/issues/manifest.json` | Registrar `ISSUE-0010` como `pendente`/`todo` | Atualizar para o estado real de conclusão e incluir notas verificáveis. |
| `PROGRESS.md` | Não alterar nesta abertura | Atualizar somente após a implementação e validação desta Issue. |
| `DUMMY.md` e `README.md` | Atualizar o mapa para reconhecer `ISSUE-0010` e o próximo nome `ISSUE-0011` | Não criar nova pasta de Sprint nem `SAIDA-MANUS.md`. |

### 4.3 Arquivos que devem permanecer fora da alteração

`src/scraper.py`, `src/session.py`, `src/rate_controller.py`, `src/gemini_analyzer.py`, `src/filters.py`, `src/database.py` e os schemas legados não devem ser alterados nesta Issue. `src/exporter.py` deve ser tratado como superfície de regressão: não trocar a stack nem reescrever o exportador; somente ajustar se um teste demonstrar que a apresentação nova quebra uma saída já contratada e a correção for estritamente compatível.

## 5. Contrato de produto e comportamento esperado

### 5.1 Hierarquia do relatório

A página deve seguir esta ordem, com carregamento e estado visual previsíveis:

```text
header factual em largura total
  identidade disponível · @handle · localização/categorias observadas · janela · data · procedência
resumo factual em largura total
  seguidores · likes médios · ER global · média de views se disponível
performance por formato em linha comparável
  Reels · Carrossel · Estático, cada um com n, likes médios, comentários médios e ER do formato
qualidade e audiência em duas colunas
  autenticidade/base real/suspeita/cobertura | demografia e regiões válidas
conteúdo e relacionamento em duas colunas
  Top 3 posts | parcerias/menções com links acessíveis
comentários e brand suitability em largura suficiente
  intenção, sentimento, evidências e ressalvas sem linguagem acusatória
expander `Detalhes da auditoria`
  score legado, fórmulas, IDs, provenance, warnings, gaps e ações de exportação
```

O primeiro viewport não pode iniciar com `Leitura para contratação`, `Score DODÔ`, parecer comercial, paywall, alerta promocional ou tabela extensa. O usuário deve entender a escala e a qualidade do sinal antes de receber qualquer síntese derivada.

### 5.2 Cards e microcopy

Cada card responde a uma pergunta única e segue `label → valor → interpretação → procedência → ação/detalhe`. O texto deve ser curto e factual. Exemplos de perguntas: **“Qual é a escala?”**, **“Como performa por formato?”**, **“O que foi verificado?”**, **“Qual é a cobertura da amostra?”** e **“Quais evidências merecem atenção?”**.

Os badges devem explicitar estado epistemológico: `observado`, `derivado`, `estimado`, `modelo` ou `indisponível`. Nenhum badge substitui valor, fórmula, fonte, cobertura ou confiança. Ausência de amostra deve resultar em `Sem posts suficientes nesta janela`, `Amostra insuficiente` ou `indisponível`, nunca em três zeros silenciosos.

Links de posts e parcerias devem aparecer como `Ver post ↗`, `Post 01` ou `@handle`, mantendo URL e shortcode no dado técnico. Não exibir URL crua, shortcode isolado ou tabela inacessível em viewport estreito.

### 5.3 Layout e identidade

O Streamlit deve manter o Design System Criativo Dodô e usar a pesquisa Apple-like somente como referência de ritmo, clareza e espaço negativo. A superfície é neutra, com cards claros, borda fina, sombra baixa, tipografia aprovada e composição silenciosa. Evidências usam no máximo duas colunas; formatos podem usar cards comparáveis em linha responsiva. Não usar Bento livre como colagem, quatro colunas de hero, gradientes, parallax, carrossel automático, shimmer ornamental ou hover que desloque o conteúdo.

### 5.4 Métricas e proveniência

A composição de gênero deve usar exclusivamente a amostra reconhecida:

```text
feminino_pct = feminino_validado / (feminino_validado + masculino_validado) × 100
masculino_pct = masculino_validado / (feminino_validado + masculino_validado) × 100
coverage_gender = genero_validado_n / nomes_identificados, quando nomes_identificados > 0
```

Para cada formato `f` em `{reels, carrossel, estatico}`, a agregação deve preservar `n_f`, likes médios, comentários médios, interações, denominador `followers_count × n_f`, ER do formato e `kind = derived`. Posts sem campo suficiente para classificação não podem entrar silenciosamente numa categoria.

A autenticidade deve ser apresentada como **sinal calibrado**, não como acusação. Expor, quando disponível, base real, massa suspeita, amostra, método, confiança e limitações. Não chamar uma influenciadora de falsa, fraudulenta ou inautêntica; não converter heurística em fato observado.

A resposta da criadora deve considerar comentários raiz e replies disponíveis, contando cada comentário raiz uma vez e preservando a distinção entre resposta direta, thread incompleta e ausência de dados. A taxa não pode ser inflada por duplicação nem reduzida por ignorar respostas aninhadas que estejam no contrato coletado.

## 6. Restrições negativas

1. Não começar pela View sem criar ou atualizar fixtures e testes dos contratos.
2. Não alterar coleta, scraping, sessão, cookies, rate limiting, pacing, Gemini, taxonomias, fórmula do ER global, PostScore ou schemas legados sem migração explícita.
3. Não instalar React, shadcn, Node, Playwright ou qualquer dependência paga para reconstruir a tela Streamlit.
4. Não copiar benchmark de Modash, ferramenta brasileira, Perplexity ou assets visuais como valor, categoria, cidade, bio, idade, views ou audiência da pessoa analisada.
5. Não preencher ausência, erro, amostra insuficiente ou indisponibilidade com zero.
6. Não exibir Score DODÔ, parecer comercial ou linguagem de contratação como conclusão inicial; se mantidos, devem ser `score legado/derivado` na auditoria.
7. Não usar linguagem acusatória para autenticidade; o produto deve comunicar evidência, sinal, confiança e limitação.
8. Não criar mais de duas colunas para blocos de evidência no Streamlit e não permitir overflow sem alternativa legível.
9. Não criar cores, fontes, sombras ou tokens fora do Design System Dodô; não importar paletas Slate/Zinc, preto externo ou verde de templates.
10. Não alterar `data/cache.db`, apagar cache ou trocar o exportador por estética.
11. Não criar pastas `SPRINT-*`, não recriar numeração de Finder/Spec e não criar `SAIDA-MANUS.md`.
12. Não fazer commit automático. Toda alteração deve permanecer disponível para revisão do usuário.

## 7. Passo a passo de execução — slicing A → B → C → D

### Fase A — Fixtures, contrato e testes de regressão

- [x] Criar fixtures determinísticas para os três formatos de mídia, posts sem classificação, amostra demográfica reconhecida/desconhecida, threads e campos ausentes.
- [x] Registrar no teste quais campos são `observed`, `derived`, `estimated`, `model` ou `unavailable`.
- [x] Congelar as invariantes existentes do ER global, PostScore, cache, exportação e Modo Demonstração (suíte preexistente revalidada 100% verde antes e depois).
- [x] Escrever testes que falhem antes da implementação para denominador de gênero, ER por formato, threads e remoção do score do topo (19 falhas confirmadas em estado "red" antes de qualquer código de produto).

### Fase B — Métricas e contratos determinísticos

- [x] Implementar a composição demográfica válida e a cobertura separada, sem alterar a fonte local de nomes/DDD.
- [x] Implementar ou ajustar agregação por Reels, Carrossel e Estático com estados de ausência e classificação auditável.
- [x] Calibrar a saída de autenticidade para base real/suspeita/indisponível, amostra, confiança e ressalva, sem acusação.
- [x] Corrigir a contagem de respostas em threads e garantir uma contagem única por comentário raiz (aliases de nomenclatura sobre o contrato já correto de `src/scraper.py`).
- [x] Rodar os testes de `src/metrics.py` e `src/demographics.py` antes de alterar a renderização.

### Fase C — Interface Streamlit e engenharia de produto

- [x] Reordenar `_render_report_page` conforme header → fatos → formatos → qualidade/demografia → evidências → comentários → auditoria.
- [x] Simplificar nomenclaturas, remover o Score DODÔ do topo e mover legado para `Detalhes da auditoria`.
- [x] Implementar cards com uma pergunta por componente, microcopy, procedência, cobertura e estados vazios/indisponíveis (cards de formato e barras de gênero).
- [x] Garantir duas colunas para evidências, links `Ver post ↗`, foco visível e comportamento responsivo sem deslocamento estrutural (parcerias/posts já usavam o padrão; não alterados nesta rodada).
- [x] Preservar HTML/PDF/JSON existentes e validar que a nova análise continua exportável sem URL crua ou perda de dados (suíte de `test_exporter.py` revalidada sem alteração).

### Fase D — Validação, evidência e encerramento

- [x] Executar a suíte completa de testes e registrar o resultado real; não substituir contagem por afirmação genérica (337/337, `.venv/bin/python -m pytest tests/`).
- [x] Validar o fluxo com `streamlit.testing.v1.AppTest` no Modo Demonstração, estado parcial, ausência de Gemini e exportações.
- [x] Fazer inspeção visual em desktop e viewport estreito, verificando primeiro viewport, duas colunas, microcopy, badges e ausência de overflow (Playwright, 1440×1000 e 390×844, console sem erros).
- [x] Comparar a implementação apenas com os princípios do `FINDER-006`; não avaliar por cópia literal dos benchmarks.
- [x] Atualizar `PROGRESS.md`, o checklist desta Issue e o `manifest.json` com status, testes, evidências, desvios e decisão final.

## 8. Critérios de aceite

### 8.1 Contratos e métricas

- [x] A porcentagem de gênero usa `feminino_validado + masculino_validado` como denominador; desconhecidos ficam fora do denominador e aparecem em cobertura.
- [x] As porcentagens válidas somam 100% dentro da amostra reconhecida, salvo estado explicitamente indisponível.
- [x] Reels, Carrossel e Estático possuem `n`, likes médios, comentários médios, ER por formato, denominador e estado de disponibilidade.
- [x] Post sem classificação suficiente não é incluído silenciosamente em Reels, Carrossel ou Estático.
- [x] A fórmula de ER global e as métricas existentes continuam passando nos testes de regressão.
- [x] Autenticidade apresenta método/sinal, base ou suspeita, amostra/cobertura e confiança quando disponíveis, sem linguagem acusatória.
- [x] Respostas em threads são consideradas conforme o contrato, sem duplicar comentário raiz.

### 8.2 Interface e experiência

- [x] O header identifica o perfil e apresenta somente dados presentes, com janela, data e procedência.
- [x] O primeiro viewport mostra fatos concretos antes de score, parecer ou auditoria.
- [x] O Score DODÔ e o parecer legado não aparecem como conclusão inicial; quando preservados, estão em auditoria e rotulados como legados/derivados.
- [x] Cada card possui pergunta/título compreensível sem leitura do código e microcopy suficiente para interpretar o valor.
- [x] Evidências usam no máximo duas colunas; o layout não desloca conteúdo em hover/focus/loading (formatos usam 3 colunas próprias, exceção prevista na SPEC-005 §6.1/§12.2 para cards comparáveis).
- [x] Ausência de dados usa `indisponível`, `sem posts suficientes`, `amostra insuficiente` ou equivalente contextual, nunca zero silencioso.
- [x] Posts e parcerias possuem link acessível e label curta; nenhuma URL crua é apresentada no resumo (não alterados nesta rodada — já atendiam desde a Sprint 002/SPEC-002).
- [x] Badges não substituem valor, fórmula, procedência, cobertura ou confiança.
- [x] Os tokens visuais do Design System Dodô são preservados e nenhuma paleta externa entra no produto.
- [x] O relatório continua legível em desktop, viewport estreito e versão impressa/exportada (desktop/viewport estreito validados via Playwright; exportação HTML/PDF/JSON não sofreu alteração e a suíte de exportador segue verde).

### 8.3 Engenharia, segurança e documentação

- [x] A suíte completa e os novos testes da Issue passam de forma determinística (337/337).
- [x] O Modo Demonstração funciona sem rede e sem credenciais.
- [x] Nenhum teste exige conta real, chamada paga ou dependência paga.
- [x] `DUMMY.md`, `PROGRESS.md`, esta Issue e `docs/issues/manifest.json` refletem o estado real, sem afirmar validação não executada.
- [x] Não existem marcadores de conflito, referências a pastas `SPRINT-*` novas ou `SAIDA-MANUS.md` criado pela tarefa.

## 9. Definition of Done

A Issue só pode ser marcada como concluída quando o código, os testes e a validação visual atenderem aos critérios da seção 8; quando os resultados reais estiverem registrados; quando os estados de ausência e proveniência forem auditáveis; quando o exportador existente não regredir; e quando `PROGRESS.md` e `docs/issues/manifest.json` forem atualizados com evidências verificáveis.

A implementação deve permanecer idempotente: uma sessão reiniciada deve ler `DUMMY.md`, `README.md`, `ISSUE-0010.md` e o manifest, identificar o último checklist marcado e continuar sem reescrever uma etapa já homologada. O Issue não autoriza commit automático; a aprovação do usuário continua sendo necessária para incorporar o resultado ao histórico Git.

## 10. Estado de abertura

| Item | Estado na criação | Estado no encerramento (2026-08-15) |
|---|---|---|
| SPEC-005 e Finder-006 lidos | Atendido | Atendido |
| DUMMY/README consultados | Atendido | Atendido |
| Issue canônica criada | Atendido | Atendido |
| Manifest registrado | Atendido: `ISSUE-0010` entrou como `pendente` | Atualizado para `concluida` |
| Implementação de código | Não iniciada | Concluída (Fases A→D) |
| Aprovação para codificação | Aguardando usuário | Concedida via `/goal` ("Diagnóstico 100% aprovado. Pode iniciar a execução...") |
| Aprovação para commit | — | Ainda não concedida — nenhum commit foi feito nesta rodada (regra de governança, item 12 da seção 6) |

## Referências

[1]: ../../specs/SPEC-005.md — `SPEC-005`, layout, métricas, inteligência e critérios da Sprint 004.  
[2]: ../finders/FINDER-006.md — `FINDER-006`, benchmark Modash, ferramenta brasileira, Perplexity e UI/UX Apple-like controlada.  
[3]: ../finders/FINDER-004.md — componentes reutilizáveis e receitas MVP locais.  
[4]: ../finders/FINDER-005.md — benchmarks de dashboards e arquitetura de informação.  
[5]: ../../DUMMY.md — regras de segurança, custo zero, cache, scraping e governança documental.  
[6]: ../../README.md — estrutura canônica, fluxo de leitura e execução.  
[7]: `pasted_content_9.txt` — anexo da solicitação com o template de Issue atômica e o protocolo Notebook LM; não [7]: `pasted_content_9.txt` — anexo d
