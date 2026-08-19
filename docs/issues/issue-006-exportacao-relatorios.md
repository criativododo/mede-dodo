# ISSUE-006: Módulo de Exportação de Relatórios (PDF Editorial fpdf2 + CSV Tabular) (v2.0.0)

* **Status:** Done — `pdf_exporter.py` e `csv_exporter.py` implementados via TDD (13/13 testes em `tests/test_relatorios.py`), conectados aos botões de download em `src/app.py` e validados end-to-end no navegador (Playwright): download real de PDF e CSV sem reload nem erro de console.
* **Responsável:** Claude Code
* **Fase:** Fase 2 — Meio (Execução de Micro-Issue)
* **Arquivos-Alvo:**
  - `src/features/relatorios/pdf_exporter.py` (Gerador de PDF editorial via fpdf2)
  - `src/features/relatorios/csv_exporter.py` (Gerador de CSV tabular UTF-8)
  - `src/app.py` (Conexão com st.download_button para PDF e CSV)
  - `tests/test_relatorios.py`
* **Dependências:** ISSUE-004 concluída

---

## 1. Objetivo da Issue

Implementar os geradores de relatório editorial em PDF (autocontido, estético e alinhado ao Design System Dodô via `fpdf2`) e CSV tabular limpo para auditoria e LLMs, conectando-os aos botões de download da interface do Streamlit (`src/app.py`).

---

## 2. Requisitos Técnicos e Implementação

### 2.1 Gerador de PDF Editorial (`src/features/relatorios/pdf_exporter.py`):
- **Biblioteca:** `fpdf2` (`from fpdf import FPDF`).
- **Design System Dodô no PDF:**
  * Paleta de Cores RGB:
    - Fundo Cannoli: `(245, 244, 236)`
    - Vermelho Haute: `(129, 1, 0)`
    - Bordas/Divisores: `(229, 224, 216)`
    - Texto Principal: `(26, 26, 26)` e Secundário: `(100, 100, 100)`
  * Formato: A4 retrato (1 a 2 páginas limpas e autoexplicativas).
- **Estrutura Editorial do PDF:**
  1. *Header:* Logo/Título "métricaDODÔ — Dossiê Editorial de Influência", `@username`, marca contratante, data de emissão e badge "Janela Trimestral (90 dias)".
  2. *Grid de Métricas Principais:* Cards com ER Branding (%), BQI (0–100), Consistência (CI %) e Saturação de Publis (SD %).
  3. *Distribuições & Demografia:* Tabela/barras com Formatos (Reels/Carrossel/Foto), Tipologia de Comentários (A/B/C/D), Gênero estimado (% F / % M) e Top Estados por DDD.
  4. *Parecer Editorial:* Caixa em destaque com borda refinada contendo o parecer consolidado (Veredito, Pontos Fortes e Ressalvas para o Briefing).
  5. *Rodapé de Auditoria:* Carimbo de proveniência (método, versão de fórmula, total de posts analisados e timestamp UTC).
- **Retorno:** Função `generate_pdf_report(data_dict) -> bytes` retornando `bytes(pdf.output())`.

### 2.2 Gerador de CSV Tabular (`src/features/relatorios/csv_exporter.py`):
- **Formato:** CSV codificado em `utf-8-sig` (compatibilidade direta com Excel e Google Sheets).
- **Estrutura:**
  * Bloco 1: Metadados da Auditoria (Perfil, Marca, Janela, Data, Versão da Fórmula).
  * Bloco 2: Métricas Consolidadas (ER Branding, BQI, CI, SD, V_AB, Cobertura).
  * Bloco 3: Tabela de Posts Analisados (`post_id`, `format`, `published_at`, `likes`, `comments`, `shares`, `saves`, `reach`, `is_sponsored`).
- **Retorno:** Função `generate_csv_report(data_dict) -> str` (ou `bytes`).

### 2.3 Integração na View (`src/app.py`):
- Conectar os botões da barra de ações do rodapé usando `st.download_button`:
  * Botão "Exportar Relatório PDF" -> baixa `metricaDODO_{username}_{data}.pdf` (`mime="application/pdf"`).
  * Botão "Download CSV" -> baixa `metricaDODO_{username}_{data}.csv` (`mime="text/csv"`).

---

## 3. Restrições Negativas (DUMMY.md)
- **PROIBIDO** fazer chamadas de rede ou queries de banco de dados dentro de `pdf_exporter.py` ou `csv_exporter.py`. Ambos recebem o dicionário de dados já resolvido.
- **PROIBIDO** gerar arquivos físicos persistidos no disco durante o download (geração pura em memória via streams/bytes).

---

## 4. Critérios de Aceite & Validação
1. **Geração PDF:** O PDF gerado deve ser visualmente harmonioso, sem sobreposição de textos, respeitando as cores Cannoli e Vermelho Haute.
2. **Download Streamlit:** Os botões de download no `src/app.py` devem baixar os arquivos reais sem recarregar ou travar a página.
3. **Testes Unitários:** `pytest tests/test_relatorios.py` validando geração de bytes válidos para PDF e formato de texto para CSV com 100% de sucesso.

---

## 5. Governança de Implementação

A implementação deverá aguardar a conclusão da ISSUE-004 e receber um payload já resolvido pelo motor de métricas. Os exportadores não poderão recalcular ER Branding, BQI, CI, SD ou qualquer outra métrica, nem acessar diretamente Instaloader, cache SQLite, APIs externas ou segredos.

A geração deve permanecer em memória, ser idempotente para o mesmo payload e preservar a proveniência, a versão da fórmula, a janela, a amostra, a cobertura, os estados `indisponivel` e as ressalvas editoriais. A View apenas conecta os bytes/strings devolvidos aos controles de download; a composição editorial pertence aos módulos de relatório.

## 6. Rastreabilidade

| Artefato | Relação |
|---|---|
| [`SPEC-001.md`](../../specs/SPEC-001.md) | Contrato visual, fronteira da View Pura e módulo de relatórios. |
| [`FINDER-001.md`](../../FINDER-001.md) | Design System Dodô, contratos de exportação e proveniência. |
| [`DUMMY.md`](../../DUMMY.md) | Restrições negativas, ausência de rede e proteção da View. |
| [`issue-004-motor-metricas-autorais.md`](issue-004-motor-metricas-autorais.md) | Dependência do payload de métricas resolvido. |
| `docs/issues/manifest.json` | ISSUE-006 permanece `todo` até a implementação e os testes. |
