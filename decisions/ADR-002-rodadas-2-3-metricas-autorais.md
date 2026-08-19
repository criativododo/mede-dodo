# ADR-002: Aprovação das Rodadas 2 e 3 do Motor de Métricas Autorais (Tipologia/P1, BQI, CI, SD, Parecer Editorial)

* **Status:** Aprovado
* **Data:** 2026-08-15
* **Autor:** Dani / Criativo Dodô
* **Fase do Framework:** Fase 3 - Fim (Integração & Homologação do MVP)

---

## 1. Contexto e Problema

A ISSUE-004 (`docs/issues/issue-004-motor-metricas-autorais.md`) implementou o núcleo Rodada 1 (ER Branding, ver ADR anterior/§3 da issue) e deixou explicitamente pendentes as Rodadas 2 e 3: tipologia de comentários A/B/C/D e `V_AB`, os três pilares do BQI, a Consistência (`CI`), a Saturação de Publis (`SD`) e o parecer editorial combinado. `docs/issues/manifest.json` chegou a marcar a `ISSUE-005` (heurística local + Gemini) como `"done"` antes de qualquer um dos seus arquivos-alvo existir — a divergência foi descoberta durante a homologação da ISSUE-007 e corrigida com a implementação real da ISSUE-005 na mesma sessão. Resolvida essa dependência, o Dani autorizou destravar as Rodadas 2/3 usando a proposta já registrada em `BENCHMARK-METRICS-001.md §6-9`.

Durante a implementação, identificou-se uma limitação física relevante: o Pilar 2 do BQI (retenção visual e alcance qualificado) depende de `save_rate`, `share_rate`, `VTR` e `alcance_qualificado` — nenhum desses sinais é exposto pela API pública do Instagram via Instaloader (o coletor da ISSUE-002 só obtém `likes`, `comentários`, formato e legenda). Expandir o coletor para obter esses sinais está fora do escopo declarado da ISSUE-004 (§13 "Fora de escopo": "não inclui... implementação do scraper Instaloader").

## 2. Alternativas Consideradas

* **Alternativa A — Aprovar e implementar a fórmula completa do BENCHMARK-METRICS-001.md como matemática pura testada, mesmo sabendo que P2/BQI/CI ficarão `indisponivel` em auditorias reais até uma futura expansão do coletor.** Prós: entrega o motor completo, testável e auditável; SD e tipologia/P1 já produzem valor real hoje; não bloqueia o fechamento das Rodadas 2/3 por uma limitação de coleta que pertence a outra issue. Contras: BQI/CI continuam não visíveis em produção até uma issue futura de expansão do coletor.
* **Alternativa B — Implementar só o que já é alimentável com dado real hoje (SD e tipologia/P1), adiando P2/BQI/CI/CI/parecer completo para uma issue futura junto da expansão do coletor.** Prós: escopo menor, sem código "adiantado". Contras: deixa a ISSUE-004 permanentemente parcial e obriga reabrir `metrics.py` quando o coletor for expandido, sem ganho de auditabilidade imediato.
* **Alternativa C — Não implementar nada agora, manter ISSUE-004 parcial indefinidamente.** Descartada pelo Dani nesta sessão.

## 3. Decisão Tomada

Adotar a **Alternativa A**. `src/features/analise/metrics.py` implementa a fórmula completa do `BENCHMARK-METRICS-001.md §6-9` (Pilares 1/2/3, BQI, CI, SD, parecer editorial combinado) como funções puras, determinísticas e testadas via TDD, versionadas sob `METHOD_VERSION = "BMQ-001-v2.0.0-r1"`. `metrics.py` nunca classifica comentário bruto — recebe `comment_labels` já resolvido pela ISSUE-005 (`ai_local.py`/`ai_gemini.py`), preservando a separação de responsabilidades da ADR-001/ADR-003.

Cada bloco declara `indisponivel` explícito, nunca zero silencioso ou aproximação por outro sinal, quando os insumos não estão disponíveis:
* **Tipologia/`V_AB`/Pilar 1 (P1):** calculável com dado real hoje (rótulos A/B/C/D da ISSUE-005).
* **Densidade de Patrocínio (SD):** calculável com dado real hoje (`is_sponsored` por post, ISSUE-002).
* **Pilar 2 (P2) e, por consequência, o BQI completo:** `indisponivel` em auditorias reais — `save_rate`/`share_rate`/`VTR`/`alcance_qualificado` não são coletáveis via Instaloader.
* **Consistência (CI):** exige um `floor` (piso) explícito e ao menos duas semanas de observação; o valor numérico do piso permanece uma decisão editorial em aberto, não fabricada por este ADR — `indisponivel` sem esses insumos.
* **Parecer editorial combinado:** `indisponivel` sempre que `BQI`/`V_AB`/`CI`/`SD` não estiverem todos resolvidos simultaneamente.

`src/app.py` (ISSUE-007) conecta SD e tipologia/P1 reais ao pipeline de auditoria; BQI/CI e o veredito do parecer aparecem como "Indisponível" na View até uma issue futura expandir o coletor.

## 4. Consequências e Impactos

* **Impactos Positivos:** ISSUE-004 sai do estado permanentemente bloqueado; `metrics.py` fica auditável e pronto para produzir BQI/CI reais assim que uma fonte de dado (expansão do coletor, API de negócios do Instagram, ou entrada manual) fornecer os sinais do Pilar 2 e o piso do CI, sem precisar reescrever a matemática. SD e V_AB/P1 já entregam valor real imediato.
* **Impactos Negativos / Trade-offs:** BQI e CI completos, e por consequência boa parte do parecer editorial combinado, não aparecem em auditorias reais nesta versão — apenas em payloads de teste com os sinais já resolvidos. O piso (`floor`) do CI segue como decisão editorial em aberto. Existe duplicação pequena e deliberada das faixas de banda (`_bqi_band`/`_ci_band`/`_sd_band`) entre `metrics.py` (fonte de verdade) e o template de fallback local em `ai_local.py` (ISSUE-005, já testado antes desta decisão) — não refatorada nesta sessão por não alterar comportamento observável.

## 5. Evidência Física

* **Arquivos Afetados:** `src/features/analise/metrics.py`, `tests/test_metrics.py`, `src/app.py`, `tests/test_integration_e2e.py`, `specs/SPEC-001.md §4.2/§4.4`, `docs/issues/issue-004-motor-metricas-autorais.md`, `docs/issues/manifest.json`, `PROGRESS.md`.
* **Testes/Validações:** `pytest tests/test_metrics.py` (50/50, cobrindo Pilares 1/2/3, BQI, CI, SD e parecer combinado, incluindo os casos `indisponivel`/divisão por zero/bloqueador). Suíte completa do projeto: `pytest tests/` (129/129).
