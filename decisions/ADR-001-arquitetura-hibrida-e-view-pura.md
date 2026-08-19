# ADR-001: Arquitetura de Inteligência Híbrida e View Pura no Streamlit (v2.0.0)

* **Status:** Aprovado; seleção de provedores supersedida pela ADR-003
* **Data:** 2026-08-15
* **Autor:** Dani Perrut (Criativo Dodô)
* **Fase do Framework:** Fase 1 — Início (Fundação v2.0.0)

---

## 1. Contexto e Problema
A versão 1.0.0 sofria com acoplamento excessivo na camada de interface do Streamlit (código de scraping, banco SQLite e chamadas de IA misturados na View) e alto custo/latência se toda a triagem semântica fosse direcionada a um único modelo proprietário. A v2.0.0 exige custo zero de infraestrutura na triagem volumosa, alta precisão editorial e desacoplamento físico total (Feature-Based Folders).

## 2. Alternativas Consideradas
* **Alternativa A (Monolito Claude 3.5 Sonnet):** Usar Claude para todas as etapas (triagem de comentários brutos + análise semântica). *Contra:* Custo proibitivo e risco de rate limit frequente.
* **Alternativa B (Monolito Heurístico Local):** Sem IA, apenas regex e contagem de palavras. *Contra:* Incapaz de detectar sarcasmo, nuances de pods de engajamento e intenção de compra real em moda feminina.
* **Alternativa C (Arquitetura Híbrida Gemini Flash + Claude Sonnet com View Pura):** Gemini 2.5 Flash para volume/triagem JSON e Claude 3.5 Sonnet para semântica profunda e parecer editorial, com Streamlit restrito à renderização reativa. *(Escolhida)*

## 3. Decisão Tomada
1. **Inteligência Híbrida**:
   - **Google Gemini 2.5 Flash (Tier Custo Zero)**: Triagem primária em lotes de comentários brutos, extração JSON de intenção de compra e estimativa etária.
   - **Anthropic Claude 3.5 Sonnet**: Interpretação de sentimento contextual, detecção de ironia/pods e elaboração do parecer editorial final de contratação.
   - **Fallback & Modo Convidado**: Fallback automático para Gemini em caso de limite no Claude, e execução heurística local se não houver chaves ativas.
2. **View Pura / Burra (`src/app.py`)**:
   - O Streamlit atua exclusivamente como renderizador de interface e estado reativo. É terminantemente proibido conter chamadas HTTP diretas, comandos SQLite ou manipulação de disco dentro da View.

## 4. Consequências e Impactos
* **Positivos:** Custo minimizado, resiliência contra rate-limits, código testável unitariamente fora do Streamlit e conformidade estrita com o Design System Dodô no Paper Desktop.
* **Trade-offs históricos:** A arquitetura originalmente exigia dois clientes de SDK (`google.genai` e `anthropic`). A seleção de provedores foi supersedida pela ADR-003, que mantém somente heurística local + `google.genai`, reduzindo custo e superfície operacional.

## 5. Evidência Física
* **Arquivos Afetados:** `src/app.py`, `src/features/analise/`, `DUMMY.md`, `FINDER-001.md`.
* **Critério de Validação:** `src/app.py` sem imports de `sqlite3`, `requests` ou `urllib3`.
